"""CRUD operations for meeting_preps.json storage.

Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_FILE = Path(__file__).parent.parent / "data" / "meeting_preps.json"

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
    if _use_supabase():
        _get_supabase_storage().meeting_prep.save_meeting_prep(meeting_id, prep_data)
        return
    data = _load()
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
    if _use_supabase():
        return _get_supabase_storage().meeting_prep.get_meeting_prep(meeting_id)
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
    if _use_supabase():
        return _get_supabase_storage().meeting_prep.get_by_company(company_name)
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
    if _use_supabase():
        return _get_supabase_storage().meeting_prep.get_upcoming_meetings(hours_ahead)
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
    if _use_supabase():
        return _get_supabase_storage().meeting_prep.mark_complete(meeting_id)
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
    if _use_supabase():
        return _get_supabase_storage().meeting_prep.list_all()
    return _load()["meeting_preps"]
