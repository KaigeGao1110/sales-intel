"""Alert log CRUD for alerts_log.json."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ALERTS_FILE = Path(__file__).parent.parent / "data" / "alerts_log.json"


def _load() -> dict:
    if not ALERTS_FILE.exists():
        return {"alerts": []}
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


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

    Returns:
        The created alert dict.
    """
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    alert = {
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
    data["alerts"].append(alert)
    _save(data)
    return alert


def get_recent(company_id: str, hours: int = 24) -> list[dict]:
    """Return alerts for a company within the last N hours (for dedup)."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    results = []
    for a in _load()["alerts"]:
        if a["company_id"] != company_id:
            continue
        try:
            ts = datetime.fromisoformat(a["alert_date"]).timestamp()
            if ts >= cutoff:
                results.append(a)
        except (ValueError, KeyError):
            pass
    return results


def get_all() -> list[dict]:
    """Return all logged alerts."""
    return _load()["alerts"]


def mark_notified(alert_id: str) -> None:
    """Mark an alert as notified."""
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    for a in data["alerts"]:
        if a["id"] == alert_id:
            a["notified"] = True
            a["notification_date"] = now
            break
    _save(data)
