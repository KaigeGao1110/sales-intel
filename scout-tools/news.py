#!/usr/bin/env python3
"""
News Monitoring Module for Scout.

Tracks news articles, press releases, and media coverage
to identify buying signals and market activity.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional


NEWS_DATA_FILE = "news_data.json"


def load_news(path: str = NEWS_DATA_FILE) -> list[dict]:
    """Load news articles from JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f).get("articles", [])
    except FileNotFoundError:
        return []


def load_companies(path: str = "companies.json") -> list[dict]:
    """Load companies from JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f).get("companies", [])
    except FileNotFoundError:
        return []


def get_news_by_company(company_name: str, news: Optional[list[dict]] = None) -> list[dict]:
    """Get news articles for a specific company."""
    if news is None:
        news = load_news()

    return [
        {
            "title": article.get("title"),
            "source": article.get("source"),
            "date": article.get("date"),
            "summary": article.get("summary", "")[:200] + "..." if len(article.get("summary", "")) > 200 else article.get("summary", ""),
            "url": article.get("url"),
            "sentiment": article.get("sentiment", "neutral"),
            "category": article.get("category", "general"),
        }
        for article in news
        if company_name.lower() in article.get("company", "").lower()
    ]


def get_recent_news(news: Optional[list[dict]] = None, days: int = 30, limit: int = 20) -> list[dict]:
    """Get recent news articles from the last N days."""
    if news is None:
        news = load_news()

    cutoff = datetime.now() - timedelta(days=days)
    recent = []

    for article in news:
        try:
            article_date = datetime.strptime(article.get("date", ""), "%Y-%m-%d")
            if article_date >= cutoff:
                recent.append(article)
        except ValueError:
            continue

    return sorted(recent, key=lambda x: x.get("date", ""), reverse=True)[:limit]


def get_news_by_category(category: str, news: Optional[list[dict]] = None) -> list[dict]:
    """Get news articles by category."""
    if news is None:
        news = load_news()

    return [
        {
            "company": article.get("company"),
            "title": article.get("title"),
            "source": article.get("source"),
            "date": article.get("date"),
            "sentiment": article.get("sentiment", "neutral"),
        }
        for article in news
        if article.get("category", "").lower() == category.lower()
    ]


def get_positive_news(news: Optional[list[dict]] = None, days: int = 30) -> list[dict]:
    """Get positive news articles (expansion, hiring, product launches)."""
    if news is None:
        news = load_news()

    cutoff = datetime.now() - timedelta(days=days)
    positive_categories = {"expansion", "product_launch", "partnership", "leadership", "milestone"}

    results = []
    for article in news:
        try:
            article_date = datetime.strptime(article.get("date", ""), "%Y-%m-%d")
            if article_date >= cutoff and article.get("category", "").lower() in positive_categories:
                results.append(article)
        except ValueError:
            continue

    return sorted(results, key=lambda x: x.get("date", ""), reverse=True)


def get_news_by_sentiment(sentiment: str, news: Optional[list[dict]] = None) -> list[dict]:
    """Get news articles by sentiment."""
    if news is None:
        news = load_news()

    return [
        {
            "company": article.get("company"),
            "title": article.get("title"),
            "date": article.get("date"),
            "sentiment": article.get("sentiment", "neutral"),
            "category": article.get("category", "general"),
        }
        for article in news
        if article.get("sentiment", "neutral") == sentiment.lower()
    ]


def identify_buying_signals(companies: Optional[list[dict]] = None, news: Optional[list[dict]] = None) -> list[dict]:
    """Identify companies with positive buying signals."""
    if companies is None:
        companies = load_companies()
    if news is None:
        news = load_news()

    cutoff = datetime.now() - timedelta(days=90)
    signals = {}

    for article in news:
        try:
            article_date = datetime.strptime(article.get("date", ""), "%Y-%m-%d")
            if article_date < cutoff:
                continue
        except ValueError:
            continue

        company = article.get("company", "")
        category = article.get("category", "")
        sentiment = article.get("sentiment", "neutral")

        if company not in signals:
            signals[company] = {"company": company, "signal_count": 0, "signals": []}

        if category in {"expansion", "product_launch", "partnership", "milestone"}:
            signals[company]["signal_count"] += 2
            signals[company]["signals"].append(f"{category}: {article.get('title')[:60]}")
        elif sentiment == "positive" and category == "funding":
            signals[company]["signal_count"] += 1
            signals[company]["signals"].append(f"Positive funding news")
        elif category == "hiring":
            signals[company]["signal_count"] += 1
            signals[company]["signals"].append(f"Hiring spree: {article.get('title')[:60]}")

    return sorted(signals.values(), key=lambda x: x["signal_count"], reverse=True)


def generate_news_report(company_name: Optional[str] = None) -> str:
    """Generate a news intelligence report."""
    companies = load_companies()
    news = load_news()
    lines = ["=" * 60, "SCOUT NEWS INTELLIGENCE REPORT", "=" * 60, ""]

    if company_name:
        articles = get_news_by_company(company_name, news)
        if not articles:
            return f"No news found for: {company_name}"
        lines.append(f"Company: {company_name}")
        lines.append(f"Articles Found: {len(articles)}")
        lines.append("")
        for a in articles:
            lines.append(f"[{a['date']}] {a['source']}")
            lines.append(f"  {a['title']}")
            lines.append(f"  Sentiment: {a['sentiment']} | Category: {a['category']}")
            if a['summary']:
                lines.append(f"  Summary: {a['summary']}")
            lines.append("")
    else:
        lines.append(f"Total Articles Tracked: {len(news)}")
        lines.append("")

        recent = get_recent_news(news, days=30, limit=10)
        lines.append(f"Recent News (last 30 days): {len(recent)}")
        for r in recent[:5]:
            lines.append(f"  [{r['date']}] {r['company']} - {r['title'][:60]}")
        lines.append("")

        positive = get_positive_news(news, days=90)
        lines.append(f"Positive News (last 90 days): {len(positive)}")
        for p in positive[:5]:
            lines.append(f"  [{p['date']}] {p['company']} - {p['category']}: {p['title'][:50]}")
        lines.append("")

        signals = identify_buying_signals(companies, news)
        lines.append("Top Buying Signals:")
        for s in signals[:5]:
            lines.append(f"  {s['company']}: {s['signal_count']} signals")
            for sig in s['signals'][:2]:
                lines.append(f"    - {sig[:60]}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            company = sys.argv[2] if len(sys.argv) > 2 else None
            print(generate_news_report(company))
        elif sys.argv[1] == "--recent":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            recent = get_recent_news(days=days)
            for r in recent:
                print(f"{r['date']} | {r['company']} | {r['title'][:50]}")
        elif sys.argv[1] == "--signals":
            signals = identify_buying_signals()
            for s in signals:
                print(f"{s['company']}: {s['signal_count']} signals")
                for sig in s['signals'][:3]:
                    print(f"  - {sig[:70]}")
        elif sys.argv[1] == "--positive":
            positive = get_positive_news()
            for p in positive:
                print(f"{p['date']} | {p['company']} | {p['title'][:60]}")
        else:
            articles = get_news_by_company(sys.argv[1])
            if articles:
                for a in articles:
                    print(f"[{a['date']}] {a['title']}")
            else:
                print(f"No news found for: {sys.argv[1]}")
    else:
        print(generate_news_report())


if __name__ == "__main__":
    main()
