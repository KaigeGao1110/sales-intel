"""Alert log CRUD for alerts_log.json.

Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ALERTS_FILE = Path(__file__).parent.parent / "data" / "alerts_log.json"

# ── Supabase delegation ───────────────────────────────────────────────────────

def _use_supabase() -> bool:
    """Return True when SUPABASE_URL and SUPABASE_KEY are both set."""
    return bool(os.getenv("SUPABASE_URL", "").strip() and os.getenv("SUPABASE_KEY", "").strip())

_supabase_storage = None

def _get_supabase_storage():
    """Lazily create and return a SupabaseStorage instance."""
    global _supabase_storage
    if _supabase_storage is None:
        from storage.supabase_client import SupabaseStorage
        _supabase_storage = SupabaseStorage()
    return _supabase_storage

# ── JSON helpers ─────────────────────────────────────────────────────────────

def _load() -> dict:
    if not ALERTS_FILE.exists():
        return {"alerts": []}
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _filter_by_account(alerts: list[dict], account_id: Optional[str] = None) -> list[dict]:
    """Filter alerts by account_id if provided. Returns all if account_id is None."""
    if account_id is None:
        return alerts
    return [a for a in alerts if a.get("account_id") == account_id]


def log_alert(
    company_id: str,
    company_name: str,
    alert_type: str,
    severity: str,
    title: str,
    summary: str,
    score: int,
    channels: list[str],
    notified: bool = False,
    account_id: Optional[str] = None,
) -> dict:
    """Append an alert entry to alerts_log.json.

    Args:
        company_id: Company UUID.
        company_name: Display name.
        alert_type: One of 'news', 'layoff', 'funding', 'review', 'jobs'.
        severity: 'high', 'medium', or 'low'.
        title: Short alert title.
        summary: Longer description of what changed.
        score: Significance score used to trigger this alert.
        channels: Notification channels used.
        notified: Whether notification was sent.
        account_id: Account UUID.

    Returns:
        The created alert dict.
    """
    if _use_supabase():
        return _get_supabase_storage().alerts.save_alert(
            company_id, company_name, alert_type, severity,
            title, summary, score, channels, notified, account_id,
        )
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    alert = {
        "id": str(uuid.uuid4()),
        "account_id": account_id,
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
    data["alerts"].append(alert)
    _save(data)
    return alert


def get_recent(company_id: str, hours: int = 24, account_id: Optional[str] = None) -> list[dict]:
    """Return alerts for a company within the last N hours (for dedup)."""
    if _use_supabase():
        return _get_supabase_storage().alerts.get_recent(company_id, hours, account_id)
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    results = []
    for a in _filter_by_account(_load()["alerts"], account_id):
        if a["company_id"] != company_id:
            continue
        try:
            ts = datetime.fromisoformat(a["alert_date"]).timestamp()
            if ts >= cutoff:
                results.append(a)
        except (ValueError, KeyError):
            pass
    return results


def get_all(account_id: Optional[str] = None) -> list[dict]:
    """Return all logged alerts, optionally filtered by account_id."""
    if _use_supabase():
        return _get_supabase_storage().alerts.get_all(account_id)
    return _filter_by_account(_load()["alerts"], account_id)


def mark_notified(alert_id: str) -> None:
    """Mark an alert as notified."""
    if _use_supabase():
        _get_supabase_storage().alerts.mark_notified(alert_id)
        return
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for a in data["alerts"]:
        if a["id"] == alert_id:
            a["notified"] = True
            a["notification_date"] = now
            break
    _save(data)
