"""Score storage for lead scoring results.

Stores scoring data in ~/.scout/scores.json.
Delegates to Supabase when SUPABASE_URL and SUPABASE_KEY are set.
"""

import json
import os
from pathlib import Path
from typing import Optional

SCORES_FILE = Path.home() / ".scout" / "scores.json"

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


def _filter_by_account(scores: list[dict], account_id: Optional[str] = None) -> list[dict]:
    """Filter scores by account_id if provided. Returns all if account_id is None."""
    if account_id is None:
        return scores
    return [s for s in scores if s.get("account_id") == account_id]


def save(
    company_id: str,
    company_name: str,
    score: int,
    grade: str,
    reasons: list,
    recommended_action: str,
    account_id: Optional[str] = None,
) -> dict:
    """Save a scoring result.

    Args:
        company_id: Company UUID.
        company_name: Company display name.
        score: Numeric score (0-100).
        grade: Letter grade (A/B/C/D).
        reasons: List of scoring reasons.
        recommended_action: Actionable next step string.
        account_id: Account UUID.

    Returns:
        The saved score entry dict.
    """
    if _use_supabase():
        return _get_supabase_storage().scores.save(
            company_id, company_name, score, grade, reasons, recommended_action, account_id
        )
    data = _load()
    entry = {
        "company_id": company_id,
        "company_name": company_name,
        "account_id": account_id,
        "score": score,
        "grade": grade,
        "reasons": reasons,
        "recommended_action": recommended_action,
    }
    data["scores"] = [s for s in data["scores"] if s.get("company_id") != company_id
                      or (account_id is not None and s.get("account_id") != account_id)]
    data["scores"].append(entry)
    _save(data)
    return entry


def get_latest(company_id: str, account_id: Optional[str] = None) -> Optional[dict]:
    """Get the most recent score for a company.

    Args:
        company_id: Company UUID.
        account_id: Account UUID.

    Returns:
        Score dict or None if not found.
    """
    if _use_supabase():
        return _get_supabase_storage().scores.get_latest(company_id, account_id)
    data = _load()
    for entry in reversed(_filter_by_account(data.get("scores", []), account_id)):
        if entry.get("company_id") == company_id:
            return entry
    return None


def get_all_latest(account_id: Optional[str] = None) -> list[dict]:
    """Get the most recent score for each company.

    Args:
        account_id: Account UUID to filter by.

    Returns:
        List of score dicts, one per company.
    """
    if _use_supabase():
        return _get_supabase_storage().scores.get_all_latest(account_id)
    data = _load()
    seen: dict[str, dict] = {}
    for entry in _filter_by_account(data.get("scores", []), account_id):
        cid = entry.get("company_id", "")
        if cid not in seen:
            seen[cid] = entry
    return list(seen.values())


def get_scores(company_id: str, account_id: Optional[str] = None) -> list[dict]:
    """Return all scores for a company (all time).

    Note: Supabase only — JSON fallback returns a list with get_latest only.
    """
    if _use_supabase():
        return _get_supabase_storage().scores.get_scores(company_id, account_id)
    # JSON doesn't store full history; return latest as single-item list
    latest = get_latest(company_id, account_id)
    return [latest] if latest else []
