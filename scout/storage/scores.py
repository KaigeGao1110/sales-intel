"""Score storage for lead scoring results.

Stores scoring data in ~/.scout/scores.json.
"""

import json
import os
from pathlib import Path
from typing import Optional

SCORES_FILE = Path.home() / ".scout" / "scores.json"


def _load() -> dict:
    """Load scores data from disk."""
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SCORES_FILE.exists():
        return {"scores": []}
    with open(SCORES_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist scores data to disk."""
    SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save(
    company_id: str,
    company_name: str,
    score: int,
    grade: str,
    reasons: list,
    recommended_action: str,
) -> dict:
    """Save a scoring result.

    Args:
        company_id: Company UUID.
        company_name: Company display name.
        score: Numeric score (0-100).
        grade: Letter grade (A/B/C/D).
        reasons: List of scoring reasons.
        recommended_action: Actionable next step string.

    Returns:
        The saved score entry dict.
    """
    data = _load()
    entry = {
        "company_id": company_id,
        "company_name": company_name,
        "score": score,
        "grade": grade,
        "reasons": reasons,
        "recommended_action": recommended_action,
    }
    # Replace any existing score for this company
    data["scores"] = [s for s in data["scores"] if s.get("company_id") != company_id]
    data["scores"].append(entry)
    _save(data)
    return entry


def get_latest(company_id: str) -> Optional[dict]:
    """Get the most recent score for a company.

    Args:
        company_id: Company UUID.

    Returns:
        Score dict or None if not found.
    """
    data = _load()
    for entry in reversed(data.get("scores", [])):
        if entry.get("company_id") == company_id:
            return entry
    return None


def get_all_latest() -> list[dict]:
    """Get the most recent score for each company.

    Returns:
        List of score dicts, one per company.
    """
    data = _load()
    seen: dict[str, dict] = {}
    for entry in data.get("scores", []):
        cid = entry.get("company_id", "")
        seen[cid] = entry
    return list(seen.values())