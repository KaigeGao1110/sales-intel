"""CRUD operations for accounts.

Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set,
falls back to JSON when not configured.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_FILE = Path(__file__).parent.parent / "data" / "accounts.json"

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
    """Load accounts.json from disk."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return {"accounts": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist data to disk."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create(
    name: str,
    email: str,
    company_name: str,
    plan_type: str = "free",
    max_companies: int = 5,
    notification_channels: Optional[list[str]] = None,
    alert_threshold: int = 10,
    webhook_url: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create a new account.

    Args:
        name: Account holder full name.
        email: Unique account email.
        company_name: Company name.
        plan_type: Plan type (free/pro/trial/enterprise).
        max_companies: Maximum monitored companies for this account.
        notification_channels: List of channels ('email', 'slack', 'console').
        alert_threshold: Score threshold to trigger alerts.
        webhook_url: Optional webhook URL for notifications.
        notes: Optional notes about the account.

    Returns:
        The created account dict.
    """
    if _use_supabase():
        return _get_supabase_storage().accounts.create(
            name=name,
            email=email,
            company_name=company_name,
            plan_type=plan_type,
            max_companies=max_companies,
            notification_channels=notification_channels,
            alert_threshold=alert_threshold,
            webhook_url=webhook_url,
            notes=notes,
        )

    data = _load()
    existing = get_by_email(email)
    if existing:
        return existing

    now = datetime.now(timezone.utc).isoformat()
    account = {
        "id": str(uuid.uuid4()),
        "created_at": now,
        "updated_at": now,
        "name": name,
        "email": email,
        "company_name": company_name,
        "plan_type": plan_type,
        "max_companies": max_companies,
        "is_active": True,
        "notification_channels": notification_channels or ["email"],
        "alert_threshold": alert_threshold,
        "webhook_url": webhook_url,
        "notes": notes,
    }
    data["accounts"].append(account)
    _save(data)
    return account


def get_by_id(account_id: str) -> Optional[dict]:
    """Find an account by UUID."""
    if _use_supabase():
        return _get_supabase_storage().accounts.get_by_id(account_id)
    data = _load()
    for a in data["accounts"]:
        if a["id"] == account_id:
            return a
    return None


def get_by_email(email: str) -> Optional[dict]:
    """Find an account by email address."""
    if _use_supabase():
        return _get_supabase_storage().accounts.get_by_email(email)
    data = _load()
    for a in data["accounts"]:
        if a.get("email", "").lower() == email.lower():
            return a
    return None


def get_all_active() -> list[dict]:
    """Return all active accounts."""
    if _use_supabase():
        return _get_supabase_storage().accounts.get_all_active()
    data = _load()
    return [a for a in data["accounts"] if a.get("is_active", True)]


def update(
    account_id: str,
    name: Optional[str] = None,
    company_name: Optional[str] = None,
    plan_type: Optional[str] = None,
    max_companies: Optional[int] = None,
    is_active: Optional[bool] = None,
    notification_channels: Optional[list[str]] = None,
    alert_threshold: Optional[int] = None,
    webhook_url: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update account fields. Only provided (non-None) fields are updated.

    Returns:
        Updated account dict, or None if not found.
    """
    if _use_supabase():
        return _get_supabase_storage().accounts.update(
            account_id=account_id,
            name=name,
            company_name=company_name,
            plan_type=plan_type,
            max_companies=max_companies,
            is_active=is_active,
            notification_channels=notification_channels,
            alert_threshold=alert_threshold,
            webhook_url=webhook_url,
            notes=notes,
        )

    data = _load()
    for i, a in enumerate(data["accounts"]):
        if a["id"] == account_id:
            if name is not None:
                a["name"] = name
            if company_name is not None:
                a["company_name"] = company_name
            if plan_type is not None:
                a["plan_type"] = plan_type
            if max_companies is not None:
                a["max_companies"] = max_companies
            if is_active is not None:
                a["is_active"] = is_active
            if notification_channels is not None:
                a["notification_channels"] = notification_channels
            if alert_threshold is not None:
                a["alert_threshold"] = alert_threshold
            if webhook_url is not None:
                a["webhook_url"] = webhook_url
            if notes is not None:
                a["notes"] = notes
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
            data["accounts"][i] = a
            _save(data)
            return a
    return None


def deactivate(account_id: str) -> bool:
    """Deactivate an account (soft-delete).

    Returns:
        True if deactivated, False if not found.
    """
    result = update(account_id, is_active=False)
    return result is not None


def delete(account_id: str) -> bool:
    """Permanently delete an account and all its data (CASCADE).

    Returns:
        True if deleted, False if not found.
    """
    if _use_supabase():
        return _get_supabase_storage().accounts.delete(account_id)

    data = _load()
    before = len(data["accounts"])
    data["accounts"] = [a for a in data["accounts"] if a["id"] != account_id]
    if len(data["accounts"]) < before:
        _save(data)
        return True
    return False
