"""Warm intro path storage.

Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

INTROS_FILE = Path(__file__).parent.parent / "data" / "intros.json"

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
    """Load intros data from disk."""
    INTROS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not INTROS_FILE.exists():
        return {"intros": []}
    with open(INTROS_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist intros data to disk."""
    INTROS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INTROS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _filter_by_account(intros: list[dict], account_id: Optional[str] = None) -> list[dict]:
    """Filter intros by account_id if provided. Returns all if account_id is None."""
    if account_id is None:
        return intros
    return [i for i in intros if i.get("account_id") == account_id]


def save_intro_request(
    company_name: str,
    target_contact: dict,
    intro_paths: list[dict],
    account_id: Optional[str] = None,
) -> dict:
    """Save a warm intro request for a company.

    Args:
        company_name: Name of the target company.
        target_contact: Dict with name, email, role of the target contact.
        intro_paths: List of intro path dicts.
        account_id: Account UUID.

    Returns:
        The saved intro request dict.
    """
    if _use_supabase():
        return _get_supabase_storage().intros.save_intro(
            company_name, target_contact, intro_paths, account_id
        )
    data = _load()
    entry = {
        "request_id": str(uuid.uuid4()),
        "account_id": account_id,
        "company_name": company_name,
        "target_contact": target_contact,
        "intro_paths": intro_paths,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["intros"].append(entry)
    _save(data)
    return entry


def get_intro_request(company_name: str, account_id: Optional[str] = None) -> Optional[dict]:
    """Get the most recent intro request for a company.

    Returns:
        The most recent intro request dict, or None if not found.
    """
    if _use_supabase():
        return _get_supabase_storage().intros.get_intro(company_name, account_id)
    matching = [
        e for e in reversed(_filter_by_account(_load()["intros"], account_id))
        if e["company_name"].lower() == company_name.lower()
    ]
    return matching[0] if matching else None


def get_all(account_id: Optional[str] = None) -> list[dict]:
    """Return all stored intro requests."""
    if _use_supabase():
        return _get_supabase_storage().intros.get_all_intros(account_id)
    return _filter_by_account(_load()["intros"], account_id)
