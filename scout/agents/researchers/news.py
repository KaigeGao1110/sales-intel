"""News Researcher - fetches recent news from multiple sources via tool routing. Run-only, no state."""

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


def run(company_name: str) -> dict:
    """
    News Researcher - fetches recent news via SearchToolRegistry.

    Routing priority for news:
        1. tavily (AI-optimized news summaries)
        2. brave (real-time news)
        3. serpapi (Google News authority)
        4. exa (semantic news)

    Results are deduplicated by URL and merged.
    """
    registry = SearchToolRegistry()

    # Route news search to best available tool(s)
    news_results = registry.route("news", company_name)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    articles: list[dict] = []
    sentiments: list[str] = []

    for item in news_results:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sentiment = _detect_sentiment(
                item.get("title", "") + " " + item.get("description", "")
            )
            sentiments.append(sentiment)
            articles.append({
                "title": item.get("title", ""),
                "url": url,
                "description": item.get("description", ""),
                "published_date": item.get("published_date", ""),
                "source": item.get("source", ""),
                "sentiment": sentiment,
            })

    neg = sentiments.count("negative")
    pos = sentiments.count("positive")
    if neg > pos:
        sentiment_summary = "negative"
    elif pos > neg:
        sentiment_summary = "positive"
    else:
        sentiment_summary = "neutral"

    return {
        "articles": articles,
        "sentiment_summary": sentiment_summary,
    }
