"""Jobs Watcher (Level 2) - checks for hiring/layoff changes. Run-only."""

from services.brave_search import BraveSearchService

_LAYOFF_KEYWORDS = {
    "layoff", "laid off", "job cut", "redundanc", "retrench", "downsize",
    "workforce reduction", "let go", "terminated", "mass firing",
}

_HIRING_KEYWORDS = {
    "hiring spree", "rapid hire", "expanding team", "headcount growth",
    "mass hire", "aggressive hiring", "doubling headcount", "tripling headcount",
}

_brave = BraveSearchService()


def run(company_name: str, previous_snapshot: dict) -> dict:
    """Job Watcher - checks for hiring/layoff changes. Run-only.

    Args:
        company_name: Name of the company to check.
        previous_snapshot: Previous research snapshot dict.

    Returns:
        {"changed": bool, "score": int, "details": str, "type": "jobs"}
    """
    results = _brave.search_hiring_signals(company_name)

    prev_signal = previous_snapshot.get("jobs", {}).get("signal", "stable")

    layoff_hits = 0
    hiring_hits = 0

    for r in results:
        text = (r.get("title", "") + " " + r.get("description", "")).lower()
        if any(kw in text for kw in _LAYOFF_KEYWORDS):
            layoff_hits += 1
        if any(kw in text for kw in _HIRING_KEYWORDS):
            hiring_hits += 1

    score = 0
    details_parts = []
    layoffs_detected = False

    if layoff_hits >= 2 and prev_signal != "layoffs":
        score += 10
        layoffs_detected = True
        details_parts.append(f"layoff signals detected ({layoff_hits} articles)")

    if hiring_hits >= 2 and prev_signal != "hiring":
        score += 4
        details_parts.append(f"rapid hiring signals detected ({hiring_hits} articles)")

    changed = score > 0
    details = "; ".join(details_parts) if details_parts else "no significant jobs changes"

    return {
        "changed": changed,
        "score": score,
        "details": details,
        "type": "jobs",
        # Extra fields used by monitor to build changes dict
        "layoffs_detected": layoffs_detected,
    }
