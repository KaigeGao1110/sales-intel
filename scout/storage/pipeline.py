"""Pipeline storage for tracking sales opportunities and deal health."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PIPELINE_FILE = Path(__file__).parent.parent / "data" / "pipeline.json"

STAGES = ["discovery", "qualification", "proposal", "negotiation", "poc", "closed_won", "closed_lost"]


def _load() -> dict:
    """Load pipeline data from disk."""
    PIPELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PIPELINE_FILE.exists():
        return {"opportunities": []}
    with open(PIPELINE_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    """Persist pipeline data to disk."""
    PIPELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def track_opportunity(
    company_name: str,
    stage: str,
    expected_close: Optional[str] = None,
    champion_contact: Optional[str] = None,
) -> dict:
    """Track a new opportunity or return existing one.

    Args:
        company_name: Name of the company.
        stage: Current pipeline stage.
        expected_close: Expected close date string.
        champion_contact: Champion contact info.

    Returns:
        The opportunity dict.
    """
    data = _load()
    # Check if already tracked
    for opp in data["opportunities"]:
        if opp["company_name"].lower() == company_name.lower():
            return opp

    opp = {
        "opportunity_id": str(uuid.uuid4()),
        "company_name": company_name,
        "stage": stage,
        "expected_close": expected_close,
        "champion_contact": champion_contact,
        "health_score": 50,  # default
        "signals": [],
        "last_assessed": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    data["opportunities"].append(opp)
    _save(data)
    return opp


def untrack(company_name: str) -> bool:
    """Stop tracking an opportunity by company name.

    Returns:
        True if removed, False if not found.
    """
    data = _load()
    before = len(data["opportunities"])
    data["opportunities"] = [
        o for o in data["opportunities"]
        if o["company_name"].lower() != company_name.lower()
    ]
    if len(data["opportunities"]) < before:
        _save(data)
        return True
    return False


def get_opportunity(company_name: str) -> Optional[dict]:
    """Get an opportunity by company name."""
    data = _load()
    for opp in data["opportunities"]:
        if opp["company_name"].lower() == company_name.lower():
            return opp
    return None


def update_health_score(
    company_name: str,
    score: int,
    signals: Optional[list] = None,
) -> Optional[dict]:
    """Update health score and signals for an opportunity.

    Returns:
        Updated opportunity dict or None if not found.
    """
    data = _load()
    for opp in data["opportunities"]:
        if opp["company_name"].lower() == company_name.lower():
            opp["health_score"] = score
            if signals is not None:
                opp["signals"] = signals
            opp["last_assessed"] = datetime.now(timezone.utc).isoformat()
            _save(data)
            return opp
    return None


def get_unhealthy(threshold: int = 50) -> list[dict]:
    """Get opportunities with health score below threshold."""
    data = _load()
    return [
        o for o in data["opportunities"]
        if o.get("status") == "active" and o.get("health_score", 0) < threshold
    ]


def get_all_opportunities() -> list[dict]:
    """Get all tracked opportunities."""
    return _load()["opportunities"]


def update_stage(company_name: str, new_stage: str) -> Optional[dict]:
    """Update the pipeline stage for an opportunity.

    Returns:
        Updated opportunity dict or None if not found/invalid stage.
    """
    if new_stage not in STAGES:
        return None
    data = _load()
    for opp in data["opportunities"]:
        if opp["company_name"].lower() == company_name.lower():
            opp["stage"] = new_stage
            _save(data)
            return opp
    return None