"""Warm intro path storage."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

INTROS_FILE = Path(__file__).parent.parent / "data" / "intros.json"


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


def save_intro_request(company_name: str, target_contact: dict, intro_paths: list[dict]) -> dict:
    """Save a warm intro request for a company.

    Args:
        company_name: Name of the target company.
        target_contact: Dict with name, email, role of the target contact.
        intro_paths: List of intro path dicts.

    Returns:
        The saved intro request dict.
    """
    data = _load()
    entry = {
        "request_id": str(uuid.uuid4()),
        "company_name": company_name,
        "target_contact": target_contact,
        "intro_paths": intro_paths,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["intros"].append(entry)
    _save(data)
    return entry


def get_intro_request(company_name: str) -> Optional[dict]:
    """Get the most recent intro request for a company.

    Returns:
        The most recent intro request dict, or None if not found.
    """
    data = _load()
    matching = [
        e for e in reversed(data["intros"])
        if e["company_name"].lower() == company_name.lower()
    ]
    return matching[0] if matching else None


def get_all() -> list[dict]:
    """Return all stored intro requests."""
    return _load()["intros"]
