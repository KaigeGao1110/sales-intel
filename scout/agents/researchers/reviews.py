"""Review Researcher - searches for customer/employee reviews via tool routing. Run-only, no state."""

from services.search_registry import SearchToolRegistry


def _detect_sentiment(text: str) -> str:
    text_lower = text.lower()
    negative = ["problem", "issue", "complaint", "fail", "bad", "terrible",
                 "worst", "fraud", "scam", "disappointed", "lawsuit"]
    positive = ["great", "excellent", "amazing", "best", "love", "recommend",
                 "outstanding", "fantastic", "innovative"]
    neg_count = sum(1 for w in negative if w in text_lower)
    pos_count = sum(1 for w in positive if w in text_lower)
    if neg_count > pos_count:
        return "negative"
    if pos_count > neg_count:
        return "positive"
    return "neutral"


def _detect_reviews(texts: list[str]) -> dict:
    combined = " ".join(texts)
    sentiment = _detect_sentiment(combined)
    negative_words = ["complaint", "problem", "bad", "terrible", "awful", "issue"]
    recent_negative = sum(1 for w in negative_words if w in combined.lower())
    return {
        "sentiment": sentiment,
        "recent_negative": recent_negative,
        "g2_rating": None,
        "trustpilot_rating": None,
    }


def run(company_name: str) -> dict:
    """
    Review Researcher - searches for customer/employee reviews via tool routing.

    Routing priority for reviews:
        1. serpapi (Google reviews, G2, Trustpilot)
        2. brave (real-time reviews)
        3. tavily (AI summary)

    Falls back gracefully if tools are unavailable.
    """
    registry = SearchToolRegistry()

    # Route reviews search to best available tool(s)
    review_results = registry.route("reviews", company_name)

    texts = [
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in review_results
    ]

    return {
        "reviews_signal": _detect_reviews(texts),
    }
