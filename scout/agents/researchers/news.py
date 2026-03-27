"""News Researcher - fetches recent news. Run-only, no state."""

from services.brave_search import BraveSearchService
from services.news_api import NewsAPIService


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
    """News Researcher - fetches recent news. Run-only, no state."""
    brave = BraveSearchService()
    news_api = NewsAPIService()

    brave_results: list[dict] = []
    newsapi_results: list[dict] = []

    if brave.available:
        brave_results = brave.search_news(company_name)

    if news_api.available:
        newsapi_results = news_api.get_company_news(company_name)

    # Merge and deduplicate by URL
    seen_urls: set[str] = set()
    articles: list[dict] = []
    sentiments: list[str] = []

    for item in brave_results + newsapi_results:
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
