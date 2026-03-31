"""CRUD operations for meeting_preps.json storage."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DATA_FILE = Path(__file__).parent.parent / "data" / "meeting_preps.json"


def _load() -> dict:
    """Load meeting_preps.json from disk."""
    if not DATA_FILE.exists():
        return {"meeting_preps": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist data to disk."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def store(meeting_id: str, prep_data: dict) -> None:
    """Store or update a meeting prep entry.

    Args:
        meeting_id: Unique identifier for the meeting.
        prep_data: Dict containing meeting prep fields.
    """
    data = _load()

    # Check for existing entry and update, or append new
    existing_indices = [
        i for i, m in enumerate(data["meeting_preps"]) if m["meeting_id"] == meeting_id
    ]
    if existing_indices:
        data["meeting_preps"][existing_indices[0]] = prep_data
    else:
        data["meeting_preps"].append(prep_data)

    _save(data)


def get(meeting_id: str) -> Optional[dict]:
    """Get a single meeting prep by ID.

    Args:
        meeting_id: The meeting UUID.

    Returns:
        The meeting prep dict or None if not found.
    """
    data = _load()
    for m in data["meeting_preps"]:
        if m["meeting_id"] == meeting_id:
            return m
    return None


def get_by_company(company_name: str) -> list[dict]:
    """Get all meeting preps for a company (case-insensitive).

    Args:
        company_name: Company name to search for.

    Returns:
        List of matching meeting prep dicts.
    """
    data = _load()
    name_lower = company_name.lower()
    return [
        m for m in data["meeting_preps"]
        if m.get("company_name", "").lower() == name_lower
    ]


def get_upcoming(hours_ahead: int = 24) -> list[dict]:
    """Get meetings scheduled within the next N hours.

    Args:
        hours_ahead: Number of hours to look ahead.

    Returns:
        List of upcoming meeting prep dicts.
    """
    data = _load()
    now = datetime.now(timezone.utc)
    upcoming: list[dict] = []

    for m in data["meeting_preps"]:
        meeting_time_str = m.get("meeting_time")
        if not meeting_time_str:
            continue
        try:
            meeting_time = datetime.fromisoformat(meeting_time_str.replace("Z", "+00:00"))
            delta = meeting_time - now
            if 0 <= delta.total_seconds() <= hours_ahead * 3600:
                upcoming.append(m)
        except Exception:
            continue

    return upcoming


def mark_complete(meeting_id: str) -> bool:
    """Set status to 'completed' for a meeting.

    Args:
        meeting_id: The meeting UUID.

    Returns:
        True if updated, False if not found.
    """
    data = _load()
    for m in data["meeting_preps"]:
        if m["meeting_id"] == meeting_id:
            m["status"] = "completed"
            _save(data)
            return True
    return False


def list_all() -> list[dict]:
    """Return all meeting preps.

    Returns:
        List of all meeting prep dicts.
    """
    return _load()["meeting_preps"]
