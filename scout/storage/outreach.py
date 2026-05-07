"""Outreach log CRUD for outreach.json.

Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OUTREACH_FILE = Path.home() / ".scout" / "outreach.json"

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
    """Load the outreach log from disk."""
    if not OUTREACH_FILE.exists():
        return {"outreach_records": []}
    with open(OUTREACH_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Save the outreach log to disk."""
    OUTREACH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTREACH_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _filter_by_account(records: list[dict], account_id: Optional[str] = None) -> list[dict]:
    """Filter records by account_id if provided. Returns all if account_id is None."""
    if account_id is None:
        return records
    return [r for r in records if r.get("account_id") == account_id]


def log(
    company_id: str,
    company_name: str,
    contacts: list[dict],
    variants: dict,
    account_id: Optional[str] = None,
) -> dict:
    """Append an outreach record to outreach.json.

    Args:
        company_id: Company UUID.
        company_name: Display name.
        contacts: List of contact dicts used (may be empty).
        variants: Dict with cold_emails, linkedin_messages, subject_lines.
        account_id: Account UUID.

    Returns:
        The created outreach record dict.
    """
    if _use_supabase():
        return _get_supabase_storage().outreach.save_outreach(
            company_id, company_name, contacts, variants, account_id
        )
    data = _load()
    now = datetime.now(timezone.utc).isoformat()
    sanitized_contacts = [
        {
            "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
            "position": c.get("position", ""),
            "email": c.get("email", ""),
        }
        for c in contacts
    ]
    record = {
        "id": str(uuid.uuid4()),
        "account_id": account_id,
        "company_id": company_id,
        "company_name": company_name,
        "created_date": now,
        "contacts": sanitized_contacts,
        "cold_emails": variants.get("cold_emails", []),
        "linkedin_messages": variants.get("linkedin_messages", []),
        "subject_lines": variants.get("subject_lines", []),
    }
    data["outreach_records"].append(record)
    _save(data)
    return record


def get_by_company(company_id: str, account_id: Optional[str] = None) -> list[dict]:
    """Return all outreach records for a company, newest first."""
    if _use_supabase():
        return _get_supabase_storage().outreach.get_by_company(company_id, account_id)
    records = _filter_by_account(_load().get("outreach_records", []), account_id)
    return [r for r in reversed(records) if r.get("company_id") == company_id]


def get_all(account_id: Optional[str] = None) -> list[dict]:
    """Return all outreach records, newest first."""
    if _use_supabase():
        return _get_supabase_storage().outreach.get_all(account_id)
    records = _filter_by_account(_load().get("outreach_records", []), account_id)
    return list(reversed(records))
