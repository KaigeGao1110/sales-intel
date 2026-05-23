"""Funding Watcher (Level 2) - checks for new funding rounds. Run-only."""

import re

from services.brave_search import BraveSearchService

_ROUND_KEYWORDS = {
    "series a", "series b", "series c", "series d", "series e",
    "seed round", "pre-seed", "funding round", "raised", "investment",
    "venture capital", "vc funding", "secured funding",
}

_brave = BraveSearchService()


def _extract_round_label(text: str) -> str:
    """Extract a short round label from article text."""
    text_lower = text.lower()
    for kw in ("series e", "series d", "series c", "series b", "series a",
               "pre-seed", "seed round"):
        if kw in text_lower:
            return kw.title()
    # Try to find "$Xm" or "$XB" pattern
    match = re.search(r"\$[\d,.]+\s*[mb]illion", text_lower)
    if match:
        return match.group(0)
    return "new round"


def run(company_name: str, previous_snapshot: dict) -> dict:
    """Funding Watcher - checks for new funding rounds. Run-only.

    Args:
        company_name: Name of the company to check.
        previous_snapshot: Previous research snapshot dict.

    Returns:
        {"changed": bool, "score": int, "details": str, "type": "funding"}
    """
    results = _brave.search_funding(company_name)

    prev_round = previous_snapshot.get("funding", {}).get("last_round", "Unknown")

    funding_hits = []
    for r in results:
        text = (r.get("title", "") + " " + r.get("description", "")).lower()
        if any(kw in text for kw in _ROUND_KEYWORDS):
            funding_hits.append(r)

    score = 0
    details = "no new funding detected"
    new_funding = False
    funding_details = ""

    if funding_hits:
        # Try to see if this represents a round different from previous
        combined_text = " ".join(
            r.get("title", "") + " " + r.get("description", "")
            for r in funding_hits[:3]
        )
        round_label = _extract_round_label(combined_text)

        if round_label.lower() != prev_round.lower():
            score += 8
            new_funding = True
            funding_details = round_label
            details = f"new funding detected: {round_label}"

    return {
        "changed": new_funding,
        "score": score,
        "details": details,
        "type": "funding",
        # Extra fields used by monitor to build changes dict
        "new_funding": new_funding,
        "funding_details": funding_details,
    }
