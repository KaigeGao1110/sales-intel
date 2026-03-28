"""CRUD operations for companies.json storage with GCS sync."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent.parent / "data" / "companies.json"
GCS_BUCKET = os.getenv("SCOUT_DATA_BUCKET", "")
GCS_OBJECT = "companies.json"


def _get_gcs_client():
    """Get a GCS client, returning None if unavailable."""
    try:
        from google.cloud import storage

        return storage.Client()
    except Exception:
        return None


def _load_from_gcs(client) -> Optional[dict]:
    """Try to load companies.json from GCS."""
    try:
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(GCS_OBJECT)
        if blob.exists():
            content = blob.download_as_text()
            return json.loads(content)
    except Exception as e:
        console.print(f"[yellow]GCS read failed: {e}[/yellow]")
    return None


def _save_to_gcs(client, data: dict) -> bool:
    """Save companies.json to GCS. Returns True on success."""
    try:
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(GCS_OBJECT)
        blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")
        return True
    except Exception as e:
        console.print(f"[yellow]GCS write failed: {e}[/yellow]")
        return False


def _load() -> dict:
    """Load companies.json, trying GCS first, then local file."""
    # Try GCS first
    if GCS_BUCKET:
        client = _get_gcs_client()
        if client:
            gcs_data = _load_from_gcs(client)
            if gcs_data is not None:
                # Sync to local file as backup
                DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(DATA_FILE, "w") as f:
                    json.dump(gcs_data, f, indent=2)
                return gcs_data

    # Fall back to local file
    if not DATA_FILE.exists():
        return {"companies": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist data to local file and optionally GCS."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Sync to GCS
    if GCS_BUCKET:
        client = _get_gcs_client()
        if client:
            _save_to_gcs(client, data)


def get_all() -> list[dict]:
    """Return all companies."""
    return _load()["companies"]


def get_active() -> list[dict]:
    """Return only active companies."""
    return [c for c in get_all() if c.get("status") == "active"]


def get_by_name(name: str) -> Optional[dict]:
    """Find a company by name (case-insensitive)."""
    name_lower = name.lower()
    for c in get_all():
        if c.get("name", "").lower() == name_lower:
            return c
    return None


def get_by_id(company_id: str) -> Optional[dict]:
    """Find a company by UUID."""
    for c in get_all():
        if c.get("id") == company_id:
            return c
    return None


def add(
    name: str,
    domain: str = "",
    alert_email: str = "",
    alert_channels: Optional[list[str]] = None,
) -> dict:
    """Add a new company to monitoring.

    Args:
        name: Company display name.
        domain: Company domain (optional).
        alert_email: Email address for alerts.
        alert_channels: List of channels ('email', 'slack', 'console').

    Returns:
        The newly created company dict.
    """
    data = _load()

    # Check for duplicate
    existing = get_by_name(name)
    if existing:
        return existing

    channels = alert_channels or (["email"] if alert_email else ["console"])
    company = {
        "id": str(uuid.uuid4()),
        "name": name,
        "domain": domain,
        "added_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_checked": None,
        "status": "active",
        "alert_channels": channels,
        "alert_email": alert_email,
    }
    data["companies"].append(company)
    _save(data)
    return company


def update_last_checked(company_id: str) -> None:
    """Update the last_checked timestamp for a company."""
    data = _load()
    for c in data["companies"]:
        if c["id"] == company_id:
            c["last_checked"] = datetime.now(timezone.utc).isoformat()
            break
    _save(data)


def set_status(company_id: str, status: str) -> None:
    """Set company status to 'active' or 'paused'."""
    data = _load()
    for c in data["companies"]:
        if c["id"] == company_id:
            c["status"] = status
            break
    _save(data)


def remove(company_id: str) -> bool:
    """Remove a company from monitoring.

    Returns:
        True if removed, False if not found.
    """
    data = _load()
    before = len(data["companies"])
    data["companies"] = [
        c for c in data["companies"] if c["id"] != company_id
    ]
    if len(data["companies"]) < before:
        _save(data)
        return True
    return False
