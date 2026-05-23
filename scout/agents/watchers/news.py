"""News Watcher (Level 2) - checks for new significant news. Run-only."""

from services.brave_search import BraveSearchService

_NEGATIVE_KEYWORDS = {
    "lawsuit", "scandal", "breach", "hack", "fraud", "fail", "bankrupt",
    "crisis", "controversy", "fine", "penalty", "recall", "defect",
}

_brave = BraveSearchService()


def run(company_name: str, previous_snapshot: dict) -> dict:
    """News Watcher - checks for new significant news. Run-only.

    Args:
        company_name: Name of the company to check.
        previous_snapshot: Previous research snapshot dict.

    Returns:
        {"changed": bool, "score": int, "details": str, "type": "news"}
    """
    results = _brave.search_news(company_name)

    prev_urls = {n.get("url", "") for n in previous_snapshot.get("news", [])}
    new_articles = [r for r in results if r.get("url", "") not in prev_urls]

    score = 0
    details_parts = []

    # Volume spike: more than 3 new articles
    if len(new_articles) > 3:
        score += 4
        details_parts.append(f"news volume spike: {len(new_articles)} new articles")

    # Sentiment shift: check new article titles/descriptions for negative keywords
    negative_count = 0
    for article in new_articles:
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        if any(kw in text for kw in _NEGATIVE_KEYWORDS):
            negative_count += 1

    prev_sentiment = previous_snapshot.get("reviews", {}).get("sentiment", "neutral")
    if negative_count >= 2 and prev_sentiment in {"positive", "neutral"}:
        score += 6
        details_parts.append(f"sentiment shift: {negative_count} negative articles detected")

    changed = score > 0
    details = "; ".join(details_parts) if details_parts else "no significant news changes"

    return {
        "changed": changed,
        "score": score,
        "details": details,
        "type": "news",
        # Extra fields used by monitor to build changes dict
        "new_news_count": len(new_articles),
        "sentiment_shifted": negative_count >= 2 and prev_sentiment in {"positive", "neutral"},
    }
