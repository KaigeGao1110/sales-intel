"""
Supabase-backed storage client for Scout.

Mirrors the interface of the existing JSON-file storage modules
(companies, scores, snapshots, alerts, outreach, pipeline,
 meeting_prep, intros) so that callers can switch storage backends
 by importing this module instead.

Environment variables required:
    SUPABASE_URL   -- e.g. https://<project>.supabase.co
    SUPABASE_KEY   -- service_role or anon key (anon is sufficient for reads)

All methods raise ``SupabaseStorageError`` on connection or constraint errors.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client, create_client


class SupabaseStorageError(Exception):
    """Raised when a Supabase storage operation fails."""


def _utc_now() -> str:
    """Return current UTC ISO timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def _make_client() -> Client:
    """Create a Supabase client from environment variables."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise SupabaseStorageError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set."
        )
    return create_client(url, key)


# ─────────────────────────────────────────────
# Companies
# ─────────────────────────────────────────────

class CompaniesClient:
    """Supabase-backed companies CRUD."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def get_all(self) -> list[dict]:
        """Return all companies."""
        try:
            result = self._sb.table("companies").select("*").execute()
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_all failed: {exc}") from exc

    def get_active(self) -> list[dict]:
        """Return only companies with status='active'."""
        try:
            result = (
                self._sb.table("companies")
                .select("*")
                .eq("status", "active")
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_active failed: {exc}") from exc

    def get_by_name(self, name: str) -> Optional[dict]:
        """Find a company by name (case-insensitive)."""
        try:
            result = (
                self._sb.table("companies")
                .select("*")
                .ilike("name", name)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_by_name failed: {exc}") from exc

    def get_by_id(self, company_id: str) -> Optional[dict]:
        """Find a company by UUID."""
        try:
            result = (
                self._sb.table("companies")
                .select("*")
                .eq("id", company_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_by_id failed: {exc}") from exc

    def add(
        self,
        name: str,
        domain: str = "",
        alert_email: str = "",
        alert_channels: Optional[list[str]] = None,
    ) -> dict:
        """Insert a new company. Returns existing record if name is a duplicate.

        Args:
            name: Company display name.
            domain: Company domain.
            alert_email: Email address for alerts.
            alert_channels: List of channels (default ['email'] if alert_email else ['console']).

        Returns:
            The created (or existing) company dict.
        """
        existing = self.get_by_name(name)
        if existing:
            return existing

        channels = alert_channels or ((["email"] if alert_email else ["console"]))
        row = {
            "id": str(uuid.uuid4()),
            "name": name,
            "domain": domain,
            "added_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "last_checked": None,
            "status": "active",
            "alert_channels": channels,
            "alert_email": alert_email,
        }
        try:
            result = self._sb.table("companies").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"add failed: {exc}") from exc

    def update_last_checked(self, company_id: str) -> None:
        """Update last_checked timestamp for a company."""
        try:
            self._sb.table("companies").update(
                {"last_checked": _utc_now()}
            ).eq("id", company_id).execute()
        except Exception as exc:
            raise SupabaseStorageError(f"update_last_checked failed: {exc}") from exc

    def set_status(self, company_id: str, status: str) -> None:
        """Set company status ('active' or 'paused')."""
        try:
            self._sb.table("companies").update(
                {"status": status}
            ).eq("id", company_id).execute()
        except Exception as exc:
            raise SupabaseStorageError(f"set_status failed: {exc}") from exc

    def remove(self, company_id: str) -> bool:
        """Delete a company by UUID. Returns True if deleted, False if not found."""
        try:
            self._sb.table("companies").delete().eq("id", company_id).execute()
            return True
        except Exception as exc:
            # Row not found is not an error — treat as False
            if "rows affected: 0" in str(exc).lower() or "empty reply" in str(exc).lower():
                return False
            raise SupabaseStorageError(f"remove failed: {exc}") from exc


# ─────────────────────────────────────────────
# Scores
# ─────────────────────────────────────────────

class ScoresClient:
    """Supabase-backed lead scoring storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save(
        self,
        company_id: str,
        company_name: str,
        score: int,
        grade: str,
        reasons: list,
        recommended_action: str,
    ) -> dict:
        """Save or replace the score for a company.

        Args:
            company_id: Company UUID.
            company_name: Company display name.
            score: Numeric score 0-100.
            grade: Letter grade (A/B/C/D).
            reasons: List of scoring reason strings.
            recommended_action: Actionable next-step string.

        Returns:
            The saved score entry dict.
        """
        # Delete existing score for this company first (upsert pattern)
        try:
            self._sb.table("scores").delete().eq("company_id", company_id).execute()
        except Exception:
            pass

        row = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "company_name": company_name,
            "score": score,
            "grade": grade,
            "factors": {
                "reasons": reasons,
                "recommended_action": recommended_action,
            },
        }
        try:
            result = self._sb.table("scores").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save failed: {exc}") from exc

    def get_latest(self, company_id: str) -> Optional[dict]:
        """Return the most recent score for a company, or None."""
        try:
            result = (
                self._sb.table("scores")
                .select("*")
                .eq("company_id", company_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_latest failed: {exc}") from exc

    def get_all_latest(self) -> list[dict]:
        """Return one score dict per company (the most recent for each)."""
        try:
            result = (
                self._sb.table("scores")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            seen: dict[str, dict] = {}
            for row in result.data:
                cid = row.get("company_id", "")
                if cid not in seen:
                    seen[cid] = row
            return list(seen.values())
        except Exception as exc:
            raise SupabaseStorageError(f"get_all_latest failed: {exc}") from exc

    def get_scores(self, company_id: str) -> list[dict]:
        """Return all scores for a company (all time)."""
        try:
            result = (
                self._sb.table("scores")
                .select("*")
                .eq("company_id", company_id)
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_scores failed: {exc}") from exc


# ─────────────────────────────────────────────
# Snapshots
# ─────────────────────────────────────────────

class SnapshotsClient:
    """Supabase-backed company research snapshot storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_snapshot(
        self,
        company_id: str,
        company_name: str,
        research_data: dict,
        source: str = "AM",
    ) -> dict:
        """Save a research snapshot for a company.

        Args:
            company_id: Company UUID.
            company_name: Company display name.
            research_data: Structured dict with news, jobs_signal, reviews_signal,
                           funding, raw_signals.
            source: Daily slot — 'AM' or 'PM'.

        Returns:
            The saved snapshot dict.
        """
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        row = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "company_name": company_name,
            "source": source,
            "check_date": date_str,
            "data": {
                "news": research_data.get("news", []),
                "jobs_signal": research_data.get("jobs_signal", {}),
                "reviews_signal": research_data.get("reviews_signal", {}),
                "funding": research_data.get("funding", {}),
                "raw_signals": research_data.get("raw_signals", []),
            },
        }
        try:
            result = self._sb.table("snapshots").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_snapshot failed: {exc}") from exc

    def get_latest(self, company_id: str) -> Optional[dict]:
        """Return the most recent snapshot for a company, or None."""
        try:
            result = (
                self._sb.table("snapshots")
                .select("*")
                .eq("company_id", company_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_latest failed: {exc}") from exc

    def get_previous(self, company_id: str) -> Optional[dict]:
        """Return the snapshot before the most recent one, or None."""
        try:
            result = (
                self._sb.table("snapshots")
                .select("*")
                .eq("company_id", company_id)
                .order("created_at", desc=True)
                .limit(2)
                .execute()
            )
            return result.data[1] if len(result.data) > 1 else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_previous failed: {exc}") from exc

    def list_snapshots(self, company_id: str) -> list[dict]:
        """Return all snapshots for a company, oldest first."""
        try:
            result = (
                self._sb.table("snapshots")
                .select("*")
                .eq("company_id", company_id)
                .order("created_at", asc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"list_snapshots failed: {exc}") from exc


# ─────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────

class AlertsClient:
    """Supabase-backed alert log storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_alert(
        self,
        company_id: str,
        company_name: str,
        alert_type: str,
        severity: str,
        title: str,
        summary: str,
        score: int,
        channels: list[str],
        notified: bool = False,
    ) -> dict:
        """Insert an alert entry.

        Args:
            company_id: Company UUID.
            company_name: Display name.
            alert_type: One of 'news', 'layoff', 'funding', 'review', 'jobs'.
            severity: 'high', 'medium', or 'low'.
            title: Short alert title.
            summary: Longer description.
            score: Significance score that triggered the alert.
            channels: List of notification channels used.
            notified: Whether notification was sent.

        Returns:
            The created alert dict.
        """
        now = _utc_now()
        row = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "company_name": company_name,
            "alert_date": now,
            "type": alert_type,
            "severity": severity,
            "title": title,
            "summary": summary,
            "score": score,
            "notified": notified,
            "notification_date": now if notified else None,
            "channels": channels,
        }
        try:
            result = self._sb.table("alerts").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_alert failed: {exc}") from exc

    def get_recent(self, company_id: str, hours: int = 24) -> list[dict]:
        """Return alerts for a company within the last N hours."""
        try:
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            result = (
                self._sb.table("alerts")
                .select("*")
                .eq("company_id", company_id)
                .gte("alert_date", cutoff.isoformat())
                .order("alert_date", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_recent failed: {exc}") from exc

    def get_all(self) -> list[dict]:
        """Return all logged alerts."""
        try:
            result = (
                self._sb.table("alerts")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_all failed: {exc}") from exc

    def mark_notified(self, alert_id: str) -> None:
        """Mark an alert as notified."""
        try:
            self._sb.table("alerts").update(
                {
                    "notified": True,
                    "notification_date": _utc_now(),
                }
            ).eq("id", alert_id).execute()
        except Exception as exc:
            raise SupabaseStorageError(f"mark_notified failed: {exc}") from exc


# ─────────────────────────────────────────────
# Outreach
# ─────────────────────────────────────────────

class OutreachClient:
    """Supabase-backed outreach log storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_outreach(
        self,
        company_id: str,
        company_name: str,
        contacts: list[dict],
        variants: dict,
    ) -> dict:
        """Insert an outreach record.

        Args:
            company_id: Company UUID.
            company_name: Display name.
            contacts: List of contact dicts (sanitised).
            variants: Dict with cold_emails, linkedin_messages, subject_lines.

        Returns:
            The created outreach record dict.
        """
        sanitized_contacts = [
            {
                "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                "position": c.get("position", ""),
                "email": c.get("email", ""),
            }
            for c in contacts
        ]
        row = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "company_name": company_name,
            "created_date": _utc_now(),
            "contacts": sanitized_contacts,
            "cold_emails": variants.get("cold_emails", []),
            "linkedin_messages": variants.get("linkedin_messages", []),
            "subject_lines": variants.get("subject_lines", []),
        }
        try:
            result = self._sb.table("outreach").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_outreach failed: {exc}") from exc

    def get_by_company(self, company_id: str) -> list[dict]:
        """Return all outreach records for a company, newest first."""
        try:
            result = (
                self._sb.table("outreach")
                .select("*")
                .eq("company_id", company_id)
                .order("created_date", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_by_company failed: {exc}") from exc

    def get_all(self) -> list[dict]:
        """Return all outreach records, newest first."""
        try:
            result = (
                self._sb.table("outreach")
                .select("*")
                .order("created_date", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_all failed: {exc}") from exc


# ─────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────

STAGES = ["discovery", "qualification", "proposal", "negotiation", "poc", "closed_won", "closed_lost"]


class PipelineClient:
    """Supabase-backed sales pipeline storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def track_opportunity(
        self,
        company_name: str,
        stage: str,
        expected_close: Optional[str] = None,
        champion_contact: Optional[str] = None,
    ) -> dict:
        """Track a new opportunity, or return existing one for the company.

        Args:
            company_name: Company name.
            stage: Pipeline stage.
            expected_close: Expected close date string.
            champion_contact: Champion contact string.

        Returns:
            The opportunity dict.
        """
        existing = self.get_opportunity(company_name)
        if existing:
            return existing

        row = {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "stage": stage,
            "expected_close": expected_close,
            "champion_contact": champion_contact,
            "health_score": 50,
            "signals": [],
            "last_assessed": None,
            "status": "active",
        }
        try:
            result = self._sb.table("pipeline").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"track_opportunity failed: {exc}") from exc

    def untrack(self, company_name: str) -> bool:
        """Delete an opportunity by company name. Returns True if deleted."""
        try:
            self._sb.table("pipeline").delete().eq(
                "company_name", company_name
            ).execute()
            return True
        except Exception as exc:
            if "rows affected: 0" in str(exc).lower() or "empty reply" in str(exc).lower():
                return False
            raise SupabaseStorageError(f"untrack failed: {exc}") from exc

    def get_opportunity(self, company_name: str) -> Optional[dict]:
        """Return an opportunity by company name (case-insensitive)."""
        try:
            result = (
                self._sb.table("pipeline")
                .select("*")
                .ilike("company_name", company_name)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_opportunity failed: {exc}") from exc

    def update_health_score(
        self,
        company_name: str,
        score: int,
        signals: Optional[list] = None,
    ) -> Optional[dict]:
        """Update health score and signals for an opportunity.

        Returns:
            Updated opportunity dict, or None if not found.
        """
        update: dict[str, Any] = {
            "health_score": score,
            "last_assessed": _utc_now(),
            "updated_at": _utc_now(),
        }
        if signals is not None:
            update["signals"] = signals

        try:
            result = (
                self._sb.table("pipeline")
                .update(update)
                .ilike("company_name", company_name)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"update_health_score failed: {exc}") from exc

    def get_unhealthy(self, threshold: int = 50) -> list[dict]:
        """Return active opportunities with health_score below threshold."""
        try:
            result = (
                self._sb.table("pipeline")
                .select("*")
                .eq("status", "active")
                .lt("health_score", threshold)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_unhealthy failed: {exc}") from exc

    def get_all_opportunities(self) -> list[dict]:
        """Return all tracked opportunities."""
        try:
            result = (
                self._sb.table("pipeline")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_all_opportunities failed: {exc}") from exc

    def update_stage(self, company_name: str, new_stage: str) -> Optional[dict]:
        """Update the pipeline stage for an opportunity.

        Returns:
            Updated opportunity dict, or None if not found / invalid stage.
        """
        if new_stage not in STAGES:
            return None
        try:
            result = (
                self._sb.table("pipeline")
                .update({
                    "stage": new_stage,
                    "updated_at": _utc_now(),
                })
                .ilike("company_name", company_name)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"update_stage failed: {exc}") from exc


# ─────────────────────────────────────────────
# Meeting Prep
# ─────────────────────────────────────────────

class MeetingPrepClient:
    """Supabase-backed meeting preparation storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_meeting_prep(self, meeting_id: str, prep_data: dict) -> dict:
        """Store or update a meeting prep entry (upsert by meeting_id).

        Args:
            meeting_id: Unique meeting UUID.
            prep_data: Dict with meeting_id, company_name, company_id, etc.

        Returns:
            The upserted meeting prep dict.
        """
        row = dict(prep_data)
        row["id"] = meeting_id
        try:
            # Upsert: insert or replace
            result = (
                self._sb.table("meeting_prep")
                .upsert(row, on_conflict="id")
                .execute()
            )
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_meeting_prep failed: {exc}") from exc

    def get_meeting_prep(self, meeting_id: str) -> Optional[dict]:
        """Return a single meeting prep by meeting_id, or None."""
        try:
            result = (
                self._sb.table("meeting_prep")
                .select("*")
                .eq("id", meeting_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_meeting_prep failed: {exc}") from exc

    def get_by_company(self, company_name: str) -> list[dict]:
        """Return all meeting preps for a company (case-insensitive)."""
        try:
            result = (
                self._sb.table("meeting_prep")
                .select("*")
                .ilike("company_name", company_name)
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_by_company failed: {exc}") from exc

    def get_upcoming_meetings(self, hours_ahead: int = 24) -> list[dict]:
        """Return meetings scheduled within the next N hours."""
        try:
            from datetime import timedelta

            now = datetime.now(timezone.utc)
            future = now + timedelta(hours=hours_ahead)
            result = (
                self._sb.table("meeting_prep")
                .select("*")
                .gte("meeting_time", now.isoformat())
                .lte("meeting_time", future.isoformat())
                .order("meeting_time", asc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_upcoming_meetings failed: {exc}") from exc

    def mark_complete(self, meeting_id: str) -> bool:
        """Set status='completed' for a meeting. Returns True if updated."""
        try:
            self._sb.table("meeting_prep").update(
                {"status": "completed"}
            ).eq("id", meeting_id).execute()
            return True
        except Exception as exc:
            raise SupabaseStorageError(f"mark_complete failed: {exc}") from exc

    def list_all(self) -> list[dict]:
        """Return all meeting preps."""
        try:
            result = (
                self._sb.table("meeting_prep")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"list_all failed: {exc}") from exc


# ─────────────────────────────────────────────
# Intros
# ─────────────────────────────────────────────

class IntrosClient:
    """Supabase-backed warm intro request storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_intro(
        self,
        company_name: str,
        target_contact: dict,
        intro_paths: list[dict],
    ) -> dict:
        """Save a warm intro request for a company.

        Args:
            company_name: Target company name.
            target_contact: Dict with name, email, role of the target contact.
            intro_paths: List of intro path dicts.

        Returns:
            The saved intro request dict.
        """
        row = {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "target_contact": target_contact,
            "intro_paths": intro_paths,
        }
        try:
            result = self._sb.table("intros").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_intro failed: {exc}") from exc

    def get_intro(self, company_name: str) -> Optional[dict]:
        """Return the most recent intro request for a company, or None."""
        try:
            result = (
                self._sb.table("intros")
                .select("*")
                .ilike("company_name", company_name)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_intro failed: {exc}") from exc

    def get_all_intros(self) -> list[dict]:
        """Return all intro requests."""
        try:
            result = (
                self._sb.table("intros")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return list(result.data)
        except Exception as exc:
            raise SupabaseStorageError(f"get_all_intros failed: {exc}") from exc


# ─────────────────────────────────────────────
# Digests
# ─────────────────────────────────────────────

class DigestsClient:
    """Supabase-backed digest storage."""

    def __init__(self, client: Optional[Client] = None) -> None:
        self._client = client

    @property
    def _sb(self) -> Client:
        if self._client is None:
            self._client = _make_client()
        return self._client

    def save_digest(self, digest_type: str, content: dict) -> dict:
        """Insert a digest entry.

        Args:
            digest_type: Type of digest (e.g. 'daily', 'weekly').
            content: Digest content as a dict.

        Returns:
            The saved digest dict.
        """
        row = {
            "id": str(uuid.uuid4()),
            "type": digest_type,
            "content": content,
        }
        try:
            result = self._sb.table("digests").insert(row).execute()
            return result.data[0]
        except Exception as exc:
            raise SupabaseStorageError(f"save_digest failed: {exc}") from exc

    def get_latest(self, digest_type: Optional[str] = None) -> Optional[dict]:
        """Return the most recent digest, optionally filtered by type."""
        try:
            q = self._sb.table("digests").select("*").order("created_at", desc=True).limit(1)
            if digest_type:
                q = q.eq("type", digest_type)
            result = q.execute()
            return result.data[0] if result.data else None
        except Exception as exc:
            raise SupabaseStorageError(f"get_latest failed: {exc}") from exc


# ─────────────────────────────────────────────
# Unified SupabaseStorage facade
# ─────────────────────────────────────────────

class SupabaseStorage:
    """
    Unified Supabase storage facade that exposes all table clients.

    Instantiate with::

        store = SupabaseStorage()

    Then use sub-clients::

        companies   = store.companies
        scores      = store.scores
        snapshots   = store.snapshots
        alerts      = store.alerts
        outreach    = store.outreach
        pipeline    = store.pipeline
        meeting_prep = store.meeting_prep
        intros      = store.intros
        digests     = store.digests
    """

    def __init__(self, client: Optional[Client] = None) -> None:
        sb = client or _make_client()
        self.companies    = CompaniesClient(sb)
        self.scores       = ScoresClient(sb)
        self.snapshots    = SnapshotsClient(sb)
        self.alerts       = AlertsClient(sb)
        self.outreach     = OutreachClient(sb)
        self.pipeline     = PipelineClient(sb)
        self.meeting_prep = MeetingPrepClient(sb)
        self.intros       = IntrosClient(sb)
        self.digests      = DigestsClient(sb)
