"""LeadScoringAgent - scores companies against ICP and intent signals."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from storage import companies as company_store
from storage import snapshots as snapshot_store
from storage import scores as score_store

console = Console()

ICP_PATH = Path(__file__).parent.parent / "config" / "icp.json"


def _load_icp() -> Optional[dict]:
    """Load ICP config from config/icp.json."""
    if not ICP_PATH.exists():
        return None
    try:
        with open(ICP_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _grade_from_score(score: int) -> str:
    """Return letter grade from numeric score."""
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def _is_recent(dt_str: str, months: int = 12) -> bool:
    """Check if a date string is within the last N months."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        return delta.days < months * 30
    except Exception:
        return False


def _score_funding(research_data: dict) -> tuple[int, str]:
    """Score funding signal (25pts max)."""
    funding = research_data.get("funding", {})
    last_round = funding.get("last_round", "")
    closed_date = funding.get("closed_date", "")

    if not last_round:
        return 0, "No funding info"

    is_recent = _is_recent(closed_date, months=12) if closed_date else False
    if is_recent:
        reason = f"Recent {last_round} funding (within 12 months)"
        return 25, reason
    else:
        reason = f"Known {last_round} funding (older)"
        return 10, reason


def _score_hiring(research_data: dict) -> tuple[int, str]:
    """Score hiring signal (20pts max, -10 penalty for layoffs)."""
    jobs = research_data.get("jobs_signal", {})
    signal = jobs.get("signal", "")

    if signal == "hiring":
        return 20, "Actively hiring"
    if signal == "layoffs":
        return -10, "Layoffs signal detected"
    return 0, "No hiring signal"


def _score_news(research_data: dict) -> tuple[int, str]:
    """Score news activity (15pts max)."""
    news = research_data.get("news", [])
    count = len(news)

    if count >= 5:
        return 15, f"High news activity ({count} items)"
    if count >= 2:
        return 8, f"Moderate news activity ({count} items)"
    return 0, "Low news activity"


def _score_reviews(research_data: dict) -> tuple[int, str]:
    """Score review health (15pts max)."""
    reviews = research_data.get("reviews_signal", {})
    avg_rating = reviews.get("avg_rating", 0.0)

    if avg_rating == 0.0:
        return 0, "No review data"

    if avg_rating >= 4.0:
        return 15, f"Healthy reviews (avg {avg_rating:.1f} stars) — stable team"
    if avg_rating >= 3.0:
        return 5, f"Moderate reviews (avg {avg_rating:.1f} stars)"
    return 15, f"Low reviews (avg {avg_rating:.1f} stars) — pain signal"


def _score_icp_match(research_data: dict, icp: Optional[dict]) -> tuple[int, str]:
    """Score ICP match (25pts max)."""
    if icp is None:
        return 12, "No ICP configured"

    enrichment = research_data.get("enrichment", {})
    funding = research_data.get("funding", {})

    points = 0
    reasons: list[str] = []

    # Employee count match
    emp_count = enrichment.get("employees") or enrichment.get("metrics", {}).get("employees")
    if emp_count:
        min_emp = icp.get("min_employees", 0)
        max_emp = icp.get("max_employees", float("inf"))
        if min_emp <= emp_count <= max_emp:
            points += 10
            reasons.append(f"Headcount {emp_count} in range {min_emp}-{max_emp}")

    # Industry match
    company_industry = (
        enrichment.get("industry", "") or enrichment.get("category", "")
    ).lower()
    industries = [i.lower() for i in icp.get("industries", [])]
    if company_industry and company_industry in industries:
        points += 10
        reasons.append(f"Industry '{company_industry}' matches ICP")
    elif company_industry:
        reasons.append(f"Industry '{company_industry}' not in ICP")

    # Funding stage match
    last_round = funding.get("last_round", "")
    stages = icp.get("funding_stages", [])
    if last_round and last_round in stages:
        points += 5
        reasons.append(f"Funding stage '{last_round}' matches ICP")

    if not reasons:
        reasons.append("No ICP dimensions matched")
    return points, "; ".join(reasons)


def _build_recommended_action(
    score: int,
    grade: str,
    reasons: list[str],
    research_data: dict,
) -> str:
    """Generate a specific, actionable recommended action."""
    funding = research_data.get("funding", {})
    jobs = research_data.get("jobs_signal", {})
    reviews = research_data.get("reviews_signal", {})
    news_count = len(research_data.get("news", []))

    last_round = funding.get("last_round", "")
    closed_date = funding.get("closed_date", "")
    is_recent = _is_recent(closed_date, months=12) if closed_date else False

    signal_parts: list[str] = []

    # Funding signal
    if last_round and is_recent:
        signal_parts.append(f"New {last_round} just closed")
        if closed_date:
            try:
                dt = datetime.fromisoformat(closed_date.replace("Z", "+00:00"))
                months_ago = (datetime.now(timezone.utc) - dt).days // 30
                if months_ago < 2:
                    signal_parts.append("closed just weeks ago — budget likely approved")
            except Exception:
                pass

    # Hiring signal
    if jobs.get("signal") == "hiring":
        signal_parts.append("actively hiring")

    # Review pain signal
    avg_rating = reviews.get("avg_rating", 0.0)
    if avg_rating > 0 and avg_rating < 3.0:
        signal_parts.append(f"low Glassdoor rating ({avg_rating:.1f} stars) — unhappy team")

    # High news volume
    if news_count >= 5:
        signal_parts.append(f"{news_count} news items in dataset")

    # Layoffs
    if jobs.get("signal") == "layoffs":
        signal_parts.append("recent layoffs — tread carefully")

    # Build the action string
    if grade == "A":
        if signal_parts:
            subject = ", ".join(signal_parts[:2])
            return f"Reach out this week — {subject}. Act fast before competitors do."
        return "High-priority lead. Reach out this week."
    if grade == "B":
        if signal_parts:
            subject = ", ".join(signal_parts[:2])
            return f"Reach out this week — {subject}. Good timing window."
        return "Solid lead. Follow up within 2 weeks."
    if grade == "C":
        if signal_parts:
            subject = signal_parts[0]
            return f"Low urgency — {subject}. Nurture for later."
        return "Lower priority. Add to nurture sequence."
    # grade D
    if signal_parts:
        subject = signal_parts[0]
        return f"Low priority — {subject}. Nurture for later."
    return "Score too low for immediate outreach. Re-evaluate next quarter."


class LeadScoringAgent:
    """Scores companies against ICP and intent signals."""

    def __init__(self, icp: Optional[dict] = None) -> None:
        """Initialize with optional ICP dict.

        Args:
            icp: Ideal Customer Profile dict with keys like
                 min_employees, max_employees, industries, funding_stages.
        """
        self.icp = icp or _load_icp()

    def score(self, company_name: str, research_data: dict, icp: Optional[dict] = None) -> dict:
        """Score a single company.

        Args:
            company_name: Name of the company.
            research_data: Research dict from ResearchAgent.
            icp: Optional override ICP dict.

        Returns:
            Dict with keys: company_name, score, grade, reasons,
            priority_rank, recommended_action.
        """
        icp_to_use = icp or self.icp

        # Dimension scores
        funding_pts, funding_reason = _score_funding(research_data)
        hiring_pts, hiring_reason = _score_hiring(research_data)
        news_pts, news_reason = _score_news(research_data)
        reviews_pts, reviews_reason = _score_reviews(research_data)
        icp_pts, icp_reason = _score_icp_match(research_data, icp_to_use)

        # Total (clamp to 0)
        total = max(0, funding_pts + hiring_pts + news_pts + reviews_pts + icp_pts)
        grade = _grade_from_score(total)

        reasons = [
            f"Funding: {funding_reason} ({funding_pts}pts)",
            f"Hiring: {hiring_reason} ({hiring_pts}pts)",
            f"News: {news_reason} ({news_pts}pts)",
            f"Reviews: {reviews_reason} ({reviews_pts}pts)",
            f"ICP: {icp_reason} ({icp_pts}pts)",
        ]

        recommended_action = _build_recommended_action(total, grade, reasons, research_data)

        return {
            "company_name": company_name,
            "score": total,
            "grade": grade,
            "reasons": reasons,
            "priority_rank": 0,  # filled by rank_all
            "recommended_action": recommended_action,
        }

    def rank_all(self, icp: Optional[dict] = None) -> list[dict]:
        """Score and rank all active monitored companies.

        Args:
            icp: Optional ICP override.

        Returns:
            List of score dicts sorted by score descending.
        """
        companies = company_store.get_active()
        if not companies:
            console.print("[yellow]No active companies to rank.[/yellow]")
            return []

        results: list[dict] = []
        for company in companies:
            cid = company["id"]
            name = company["name"]

            # Get latest snapshot
            snapshot = snapshot_store.get_latest(cid)
            if snapshot:
                research_data = {
                    "news": snapshot.get("news", []),
                    "jobs_signal": snapshot.get("jobs", {}),
                    "reviews_signal": snapshot.get("reviews", {}),
                    "funding": snapshot.get("funding", {}),
                }
            else:
                research_data = {
                    "news": [],
                    "jobs_signal": {},
                    "reviews_signal": {},
                    "funding": {},
                }

            result = self.score(name, research_data, icp=icp)
            result["company_id"] = cid
            results.append(result)

        # Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)

        # Assign ranks
        for i, r in enumerate(results):
            r["priority_rank"] = i + 1

        return results

    def print_rank_table(self, icp: Optional[dict] = None) -> None:
        """Score all companies and print a Rich ranking table."""
        results = self.rank_all(icp=icp)

        if not results:
            return

        table = Table(
            title="Lead Rankings",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Rank", justify="right")
        table.add_column("Company", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Grade")
        table.add_column("Top Signal")
        table.add_column("Recommended Action")

        for r in results:
            grade = r["grade"]
            grade_color = {"A": "green", "B": "blue", "C": "yellow", "D": "red"}.get(grade, "")

            # Top signal = highest point contributor
            reasons = r["reasons"]
            max_pts = 0
            top_signal = ""
            for reason in reasons:
                # Parse "(NNpts)" suffix
                try:
                    pts = int(reason.split("(")[-1].replace("pts)", ""))
                    if pts > max_pts and pts > 0:
                        max_pts = pts
                        top_signal = reason.split(":")[1].split("(")[0].strip()
                except Exception:
                    pass

            score_str = f"[bold]{r['score']}[/bold]" if r["score"] >= 80 else str(r["score"])

            table.add_row(
                str(r["priority_rank"]),
                r["company_name"],
                score_str,
                f"[{grade_color}]{grade}[/{grade_color}]",
                top_signal[:40],
                r["recommended_action"][:60],
            )

        console.print(table)