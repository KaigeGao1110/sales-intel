"""Snapshot storage for company monitoring state."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SNAPSHOTS_DIR = Path(__file__).parent.parent / "data" / "snapshots"

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

def _get_slot(dt: datetime) -> str:
    """Return 'AM' if hour < 12 UTC, 'PM' otherwise."""
    return "AM" if dt.hour < 12 else "PM"


def _snapshot_path(company_id: str, date_str: str, slot: str) -> Path:
    return SNAPSHOTS_DIR / f"{company_id}_{date_str}_{slot}.json"


def _parse_snapshot_filename(filename: str) -> tuple[str, str, str]:
    """Parse company_id, date_str, slot from a snapshot filename.

    Handles both old format (no slot, treated as AM) and new format.
    Returns (company_id, date_str, slot).
    """
    match = re.match(r"^(.+)_(\d{4}-\d{2}-\d{2})_(AM|PM)\.json$", filename)
    if match:
        return match.group(1), match.group(2), match.group(3)
    match = re.match(r"^(.+)_(\d{4}-\d{2}-\d{2})\.json$", filename)
    if match:
        return match.group(1), match.group(2), "AM"
    raise ValueError(f"Cannot parse snapshot filename: {filename}")


def save(company_id: str, company_name: str, research_data: dict) -> Path:
    """Save a research snapshot for a company.

    Args:
        company_id: Company UUID.
        company_name: Display name.
        research_data: Structured research dict from ResearchAgent.

    Returns:
        Path to the saved snapshot file.
    """
    if _use_supabase():
        result = _get_supabase_storage().snapshots.save_snapshot(
            company_id, company_name, research_data, source="AM"
        )
        # Supabase returns dict; return the id as a pseudo-path for compatibility
        return Path(result.get("id", str(company_id)))

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    slot = _get_slot(now)

    snapshot = {
        "company_id": company_id,
        "company_name": company_name,
        "check_date": date_str,
        "slot": slot,
        "news": research_data.get("news", []),
        "jobs": research_data.get("jobs_signal", {}),
        "reviews": research_data.get("reviews_signal", {}),
        "funding": research_data.get("funding", {}),
        "raw_signals": research_data.get("raw_signals", []),
    }

    path = _snapshot_path(company_id, date_str, slot)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return path


def get_latest(company_id: str) -> Optional[dict]:
    """Get the most recent snapshot for a company.

    Returns:
        Snapshot dict or None if no snapshots exist.
    """
    if _use_supabase():
        return _get_supabase_storage().snapshots.get_latest(company_id)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{company_id}_*.json"
    matches = sorted(SNAPSHOTS_DIR.glob(pattern), reverse=True)
    if not matches:
        return None
    with open(matches[0], "r") as f:
        return json.load(f)


def get_previous(company_id: str) -> Optional[dict]:
    """Get the most recent snapshot that is NOT the current one.

    If current slot is PM, returns AM of same day if it exists.
    If current slot is AM, returns PM of previous day if it exists.

    Returns:
        Snapshot dict or None if no previous snapshot exists.
    """
    if _use_supabase():
        return _get_supabase_storage().snapshots.get_previous(company_id)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    current_date = now.strftime("%Y-%m-%d")
    current_slot = _get_slot(now)
    current_filename = f"{company_id}_{current_date}_{current_slot}.json"
    pattern = f"{company_id}_*.json"
    matches = sorted(SNAPSHOTS_DIR.glob(pattern), reverse=True)
    for path in matches:
        if path.name == current_filename:
            continue
        with open(path, "r") as f:
            return json.load(f)
    return None


def list_snapshots(company_id: str) -> list[Path]:
    """List all snapshot files for a company, oldest first."""
    if _use_supabase():
        snapshots = _get_supabase_storage().snapshots.list_snapshots(company_id)
        # Supabase returns dicts; return list of paths for compatibility
        return [Path(s.get("id", company_id)) for s in snapshots]
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(SNAPSHOTS_DIR.glob(f"{company_id}_*.json"))
