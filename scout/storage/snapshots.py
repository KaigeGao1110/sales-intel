"""Snapshot storage for company monitoring state."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SNAPSHOTS_DIR = Path(__file__).parent.parent / "data" / "snapshots"


def _snapshot_path(company_id: str, date_str: str) -> Path:
    return SNAPSHOTS_DIR / f"{company_id}_{date_str}.json"


def save(company_id: str, company_name: str, research_data: dict) -> Path:
    """Save a research snapshot for a company.

    Args:
        company_id: Company UUID.
        company_name: Display name.
        research_data: Structured research dict from ResearchAgent.

    Returns:
        Path to the saved snapshot file.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    snapshot = {
        "company_id": company_id,
        "company_name": company_name,
        "check_date": date_str,
        "news": research_data.get("news", []),
        "jobs": research_data.get("jobs_signal", {}),
        "reviews": research_data.get("reviews_signal", {}),
        "funding": research_data.get("funding", {}),
        "raw_signals": research_data.get("raw_signals", []),
    }

    path = _snapshot_path(company_id, date_str)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    return path


def get_latest(company_id: str) -> Optional[dict]:
    """Get the most recent snapshot for a company.

    Returns:
        Snapshot dict or None if no snapshots exist.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{company_id}_*.json"
    matches = sorted(SNAPSHOTS_DIR.glob(pattern))
    if not matches:
        return None
    with open(matches[-1], "r") as f:
        return json.load(f)


def get_previous(company_id: str) -> Optional[dict]:
    """Get the second-most-recent snapshot (for diff comparison).

    Returns:
        Snapshot dict or None if fewer than 2 snapshots exist.
    """
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{company_id}_*.json"
    matches = sorted(SNAPSHOTS_DIR.glob(pattern))
    if len(matches) < 2:
        return None
    with open(matches[-2], "r") as f:
        return json.load(f)


def list_snapshots(company_id: str) -> list[Path]:
    """List all snapshot files for a company, oldest first."""
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(SNAPSHOTS_DIR.glob(f"{company_id}_*.json"))
