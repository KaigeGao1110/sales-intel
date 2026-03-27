"""Web Researcher - searches for hiring/funding signals. Run-only, no state."""

import re

from services.brave_search import BraveSearchService


LAYOFF_KEYWORDS = [
    "layoff", "layoffs", "laid off", "job cuts", "workforce reduction",
    "reductions in force", "rif", "restructuring", "downsizing",
]

HIRING_KEYWORDS = [
    "hiring", "we're growing", "join our team", "rapid expansion",
    "new offices", "headcount", "doubling team",
]

FUNDING_KEYWORDS = [
    "raised", "funding", "series a", "series b", "series c", "seed round",
    "investment", "venture capital", "vc backed", "valuation",
]


def _detect_jobs_signal(texts: list[str]) -> dict:
    combined = " ".join(texts).lower()
    layoff_hits = sum(1 for kw in LAYOFF_KEYWORDS if kw in combined)
    hiring_hits = sum(1 for kw in HIRING_KEYWORDS if kw in combined)

    if layoff_hits >= 2:
        signal = "layoffs"
    elif hiring_hits >= 3:
        signal = "rapid_hiring"
    elif hiring_hits >= 1:
        signal = "hiring"
    else:
        signal = "stable"

    keywords = []
    for kw in LAYOFF_KEYWORDS + HIRING_KEYWORDS:
        if kw in combined and kw not in keywords:
            keywords.append(kw)

    return {
        "signal": signal,
        "total_postings": hiring_hits * 5,
        "keywords": keywords[:8],
        "layoff_hits": layoff_hits,
        "hiring_hits": hiring_hits,
    }


def _detect_funding(texts: list[str]) -> dict:
    combined = " ".join(texts).lower()
    last_round = "Unknown"
    amount = "Unknown"

    for kw in ["series c", "series b", "series a", "seed round", "seed"]:
        if kw in combined:
            last_round = kw.title()
            break

    amount_match = re.search(r"\$[\d,.]+\s*[mb]illion?|\$[\d,.]+[mb]", combined)
    if amount_match:
        amount = amount_match.group(0).strip()

    return {
        "last_round": last_round,
        "amount": amount,
        "date": "Unknown",
        "valuation": "Unknown",
    }


def run(company_name: str) -> dict:
    """Web Researcher - searches for hiring/funding signals. Run-only."""
    brave = BraveSearchService()

    hiring_results: list[dict] = []
    funding_results: list[dict] = []

    if brave.available:
        hiring_results = brave.search_hiring_signals(company_name)
        funding_results = brave.search_funding(company_name)

    all_texts: list[str] = []
    raw_signals: list[str] = []

    for item in hiring_results + funding_results:
        text = f"{item.get('title', '')} {item.get('description', '')}"
        if text.strip():
            all_texts.append(text)
            raw_signals.append(text[:200])

    return {
        "jobs_signal": _detect_jobs_signal(all_texts),
        "funding": _detect_funding(all_texts),
        "raw_signals": raw_signals,
    }
