#!/usr/bin/env python3
"""
Recent News Scraper with Source Tier Ranking for Scout.

Uses Google News RSS with 7-day filtering and source credibility ranking.
Tier 1: TechCrunch, Bloomberg, Reuters, WSJ, The Verge, Axios
Tier 2: Forbes, BI, The Information
Tier 3: Everything else
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import requests

TIMEOUT = 10

# Source tier ranking
SOURCE_TIERS = {
    # Tier 1 - Highest credibility
    "techcrunch": 1,
    "bloomberg": 1,
    "reuters": 1,
    "wsj": 1,
    "the verge": 1,
    "axios": 1,
    "theinformation": 1,
    "wired": 1,
    "the economist": 1,
    "ft.com": 1,
    "financial times": 1,
    "barrons": 1,
    # Tier 2 - Medium credibility
    "forbes": 2,
    "business insider": 2,
    "businessinsider": 2,
    "the information": 2,
    "fortune": 2,
    "cnbc": 2,
    "sec.gov": 2,
    "uspto.gov": 2,
    # Tier 3 - Standard
}

# RSS feed URL template
RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def _get_source_tier(source: str) -> int:
    """Get tier for a news source (lower = more credible)."""
    source_lower = source.lower()
    for tier_source, tier in SOURCE_TIERS.items():
        if tier_source in source_lower:
            return tier
    return 3  # Default to Tier 3


def _tier_label(tier: int) -> str:
    """Convert tier number to label."""
    return {1: "TIER1", 2: "TIER2", 3: "TIER3"}.get(tier, "TIER3")


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from RSS feed."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d %b %Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _is_recent(pub_date: Optional[datetime], days: int = 7) -> bool:
    """Check if date is within the last N days."""
    if not pub_date:
        return False
    now = datetime.now(timezone.utc)
    if pub_date.tzinfo is None:
        pub_date = pub_date.replace(tzinfo=timezone.utc)
    return (now - pub_date) <= timedelta(days=days)


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    return text.strip()


def get_recent_news(
    company_name: str,
    domain: Optional[str] = None,
    days: int = 7,
    max_results: int = 20
) -> list[dict]:
    """
    Fetch recent news for a company from Google News RSS.

    Args:
        company_name: Company name to search
        domain: Optional company domain for disambiguation
        days: Only include news from last N days (default: 7)
        max_results: Maximum number of results to return (default: 20)

    Returns:
        List of dicts with keys:
        - title, url, source, tier, tier_label, date, snippet
        - source_link (for attribution)
    """
    # Build search query
    query = f'"{company_name}"'
    if domain:
        query = f'{company_name} {domain}'
    encoded_query = quote(query)

    url = RSS_URL.format(query=encoded_query)

    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code != 200:
            return [{"error": f"HTTP {resp.status_code}", "news": []}]

        # Parse RSS XML
        root = ET.fromstring(resp.content)
        channel = root.find("channel")

        if channel is None:
            return [{"error": "Invalid RSS feed", "news": []}]

        items = channel.findall("item")
        seen_urls = set()

        for item in items:
            # Extract fields
            title = _clean_html(item.findtext("title") or "")
            link = item.findtext("link") or ""
            pub_date_str = item.findtext("pubDate") or ""
            description = _clean_html(item.findtext("description") or "")
            source = item.findtext("source") or "unknown"

            # Skip duplicates
            if link in seen_urls:
                continue
            seen_urls.add(link)

            # Parse date
            pub_date = _parse_date(pub_date_str)

            # Filter to recent
            if pub_date:
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                if pub_date < cutoff:
                    continue

            # Get tier
            tier = _get_source_tier(source)

            results.append({
                "title": title,
                "url": link,
                "source": source,
                "tier": tier,
                "tier_label": _tier_label(tier),
                "date": pub_date.isoformat() if pub_date else "unknown",
                "snippet": description[:200] if len(description) > 200 else description,
                "source_link": f"https://news.google.com/rss?q={quote(source)}&hl=en-US",
            })

            if len(results) >= max_results:
                break

    except ET.ParseError:
        return [{"error": "Failed to parse RSS feed", "news": []}]
    except Exception as e:
        return [{"error": str(e), "news": []}]

    # Sort by tier (Tier 1 first) then by date (newest first)
    results.sort(key=lambda x: (x.get("tier", 3), x.get("date", "")), reverse=False)

    return results


def format_news_brief(news: list[dict], max_items: int = 5) -> str:
    """
    Format news list into a brief text summary.

    Args:
        news: List of news items from get_recent_news
        max_items: Maximum number of items to include

    Returns:
        Formatted string suitable for Slack/Telegram
    """
    if not news or (len(news) == 1 and "error" in news[0]):
        return "No recent news found."

    lines = ["📰 Recent News:"]
    count = 0

    for item in news:
        if "error" in item:
            continue
        tier_emoji = {"TIER1": "🟢", "TIER2": "🟡", "TIER3": "⚪"}.get(item.get("tier_label", ""), "⚪")
        date_str = item.get("date", "unknown")
        if date_str != "unknown":
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%b %d")
            except Exception:
                pass

        lines.append(f"{tier_emoji} [{item.get('tier_label', 'T3')}] {date_str}: {item.get('title', '')[:80]}")
        lines.append(f"   Source: {item.get('source', 'unknown')}")
        count += 1
        if count >= max_items:
            break

    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"

    print(f"Fetching news for: {company}")
    news = get_recent_news(company, days=7)
    print(json.dumps(news, indent=2))
