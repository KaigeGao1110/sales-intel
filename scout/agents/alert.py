"""Alert Subagent - evaluates changes and sends notifications."""

import json
import os
from typing import Optional
from rich.console import Console

from storage import alerts as alert_store
from services.hunter import HunterService
from services.apollo import ApolloService

console = Console()

# Significance scoring table (from PLAN.md)
SCORING_TABLE = {
    "layoffs": 10,
    "new_funding": 8,
    "rating_drop": 7,
    "sentiment_shift": 6,
    "news_volume_spike": 4,
    "minor_news": 1,
}

ALERT_THRESHOLD = 10


def _lookup_contacts(company_name: str, domain: str = "") -> list[dict]:
    """Look up company contacts via Apollo.io (preferred) with Hunter.io fallback.

    Returns up to 3 relevant contacts (prioritizing executives and sales).
    """
    contacts = []

    # Apollo.io first (more complete: has title + LinkedIn + email)
    apollo = ApolloService()
    if apollo.available:
        apollo_contacts = apollo.search_people(
            company_name=company_name,
            domain=domain,
            limit=3,
        )
        for c in apollo_contacts:
            contacts.append({
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "email": c.get("email", ""),
                "position": c.get("title", ""),
                "linkedin_url": c.get("linkedin_url", ""),
                "confidence": 100 if c.get("email_status") == "verified" else 50,
                "verification": {
                    "status": "valid" if c.get("email_status") == "verified" else "unknown",
                },
            })
        if contacts:
            return contacts[:3]

    # Hunter.io fallback
    hunter = HunterService()
    if not hunter.available:
        return []

    # If we have a domain, search by domain (executives first)
    if domain:
        all_contacts = hunter.domain_search(
            domain=domain,
            company=company_name,
            seniority="executive",
        )
        # Also try senior-level
        if len(all_contacts) < 3:
            senior = hunter.domain_search(
                domain=domain,
                company=company_name,
                seniority="senior",
            )
            for c in senior:
                if c not in all_contacts:
                    all_contacts.append(c)

        contacts = all_contacts[:3]

    return contacts


def _score_changes(changes: dict) -> tuple[int, list[str], str]:
    """Compute significance score for a set of changes.

    Args:
        changes: Dict describing what changed between snapshots.

    Returns:
        Tuple of (score, list_of_reasons, alert_type).
    """
    score = 0
    reasons: list[str] = []
    primary_type = "news"

    if changes.get("layoffs_detected"):
        score += SCORING_TABLE["layoffs"]
        reasons.append("Layoff signals detected")
        primary_type = "layoff"

    if changes.get("new_funding"):
        score += SCORING_TABLE["new_funding"]
        reasons.append(f"New funding: {changes.get('funding_details', 'Unknown round')}")
        primary_type = "funding"

    if changes.get("rating_drop", 0) > 0.3:
        score += SCORING_TABLE["rating_drop"]
        reasons.append(f"Review rating dropped by {changes.get('rating_drop'):.1f} stars")
        primary_type = "review"

    if changes.get("sentiment_shifted"):
        score += SCORING_TABLE["sentiment_shift"]
        reasons.append("Sentiment shifted from positive/neutral to negative")

    news_count = changes.get("new_news_count", 0)
    if news_count > 3:
        score += SCORING_TABLE["news_volume_spike"]
        reasons.append(f"News volume spike: {news_count} new articles in 24h")
        primary_type = "news"
    elif news_count > 0:
        score += SCORING_TABLE["minor_news"] * news_count
        reasons.append(f"{news_count} minor news item(s)")

    return score, reasons, primary_type


def _severity_from_score(score: int) -> str:
    if score >= 15:
        return "high"
    if score >= 10:
        return "medium"
    return "low"


def _send_email_alert(
    to_email: str,
    company_name: str,
    title: str,
    body: str,
) -> bool:
    """Send alert via Gmail API.

    Returns True if sent successfully, False otherwise.
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import base64
        from email.mime.text import MIMEText

        creds_file = os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")
        if not os.path.exists(creds_file):
            console.print(
                f"[yellow]Gmail credentials not found at '{creds_file}'. "
                "Falling back to console output.[/yellow]"
            )
            return False

        creds = Credentials.from_authorized_user_file(creds_file)
        service = build("gmail", "v1", credentials=creds)

        message = MIMEText(body, "html")
        message["to"] = to_email
        message["subject"] = f"[Scout Alert] {title}"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        console.print(f"[green]Email alert sent to {to_email}[/green]")
        return True

    except ImportError:
        console.print(
            "[yellow]google-api-python-client not installed. Falling back to console.[/yellow]"
        )
        return False
    except Exception as e:
        console.print(f"[red]Email send failed: {e}[/red]")
        return False


def _send_slack_alert(
    webhook_url: str,
    company_name: str,
    title: str,
    body: str,
    contacts: Optional[list[dict]] = None,
    company_domain: str = "",
) -> bool:
    """Send alert via Slack webhook with optional Hunter.io contact info.

    Returns True if sent successfully.
    """
    import requests

    # Build contact section
    contact_blocks = []
    if contacts:
        for c in contacts[:3]:
            position = c.get("position", "Unknown")
            confidence = c.get("confidence", 0)
            email = c.get("email", "")
            linkedin = c.get("linkedin_url", "")
            verified = c.get("verification", {}).get("status") == "valid"
            verified_emoji = "✅" if verified else "⚠️"
            contact_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"• *{c.get('first_name', '')} {c.get('last_name', '')}* "
                        f"({position}) {verified_emoji}\n"
                        f"  📧 `{email}`" + (f" | 🔗 [LinkedIn]({linkedin})" if linkedin else "")
                    ),
                },
            })

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":rotating_light: *Scout Alert: {company_name}*\n*{title}*\n{body}"},
        }
    ]

    if contact_blocks:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_👤 *Potential contacts (via Hunter.io):*_"},
        })
        blocks.extend(contact_blocks)

    payload = {"text": f"Scout Alert: {company_name}", "blocks": blocks}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        console.print("[green]Slack alert sent[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Slack webhook failed: {e}[/red]")
        return False


class AlertAgent:
    """Evaluates change significance and dispatches notifications."""

    def evaluate_and_alert(
        self,
        company: dict,
        changes: dict,
    ) -> Optional[dict]:
        """Score changes and send alert if threshold is met.

        Args:
            company: Company dict from companies.json.
            changes: Dict describing what changed vs previous snapshot.

        Returns:
            The logged alert dict if alert was triggered, else None.
        """
        score, reasons, alert_type = _score_changes(changes)

        if score < ALERT_THRESHOLD:
            console.print(
                f"[dim]  Score {score} < threshold {ALERT_THRESHOLD} for "
                f"{company['name']} — no alert[/dim]"
            )
            return None

        # Deduplication: don't re-alert same company within 6h
        recent = alert_store.get_recent(company["id"], hours=6)
        if recent:
            console.print(
                f"[dim]  Dedup: alert already sent for {company['name']} "
                f"within 6h — skipping[/dim]"
            )
            return None

        severity = _severity_from_score(score)
        title = f"{company['name']}: {', '.join(reasons[:2])}"
        summary = "\n".join(f"• {r}" for r in reasons)

        console.print(
            f"\n[bold red]ALERT[/bold red] [{severity.upper()}] "
            f"{company['name']} — score {score}\n{summary}"
        )

        channels = company.get("alert_channels", ["console"])
        notified = False

        # Look up contacts via Hunter.io when alert fires
        contacts = _lookup_contacts(
            company_name=company["name"],
            domain=company.get("domain", ""),
        )
        if contacts:
            console.print(f"[dim]  Hunter.io found {len(contacts)} contact(s)[/dim]")

        for channel in channels:
            if channel == "email" and company.get("alert_email"):
                html_body = f"<h2>{company['name']} — Scout Alert</h2><p>{summary.replace(chr(10), '<br>')}</p>"
                if _send_email_alert(company["alert_email"], company["name"], title, html_body):
                    notified = True

            elif channel == "slack":
                slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
                if slack_url:
                    if _send_slack_alert(
                        slack_url,
                        company["name"],
                        title,
                        summary,
                        contacts=contacts,
                        company_domain=company.get("domain", ""),
                    ):
                        notified = True

            elif channel == "console":
                console.print(
                    f"[bold yellow]Console Alert:[/bold yellow] {summary}"
                )
                if contacts:
                    for c in contacts[:3]:
                        email = c.get("email", "")
                        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                        pos = c.get("position", "")
                        verified = c.get("verification", {}).get("status")
                        console.print(
                            f"  👤 {name} ({pos}) — {email} "
                            f"{'[valid]' if verified == 'valid' else '[unverified]'}"
                        )
                notified = True

        alert = alert_store.log_alert(
            company_id=company["id"],
            company_name=company["name"],
            alert_type=alert_type,
            severity=severity,
            title=title,
            summary=summary,
            score=score,
            channels=channels,
            notified=notified,
        )
        return alert

    def send_test_alert(self, email: str) -> None:
        """Send a test alert to verify email configuration."""
        console.print(f"\n[bold]Sending test alert to {email}...[/bold]")
        test_body = (
            "<h2>Scout Test Alert</h2>"
            "<p>If you received this, Scout email alerts are working correctly.</p>"
        )
        success = _send_email_alert(email, "Test Company", "Scout Test Alert", test_body)
        if not success:
            console.print(
                "[yellow]Email not sent — printing test alert to console instead:[/yellow]\n"
                "Subject: [Scout Alert] Scout Test Alert\n"
                "Body: Scout email alerts would appear here.\n"
                "To enable email: set up Gmail API credentials (see README)."
            )
