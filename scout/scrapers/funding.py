#!/usr/bin/env python3
"""
Funding & Basic Info Scraper for Scout.

PUBLIC companies: Yahoo Finance API (no key needed)
PRIVATE companies: web search with date filtering

NEVER guess. If not found, return "unknown".
"""

import json
import os
import random
import time as time_mod
from datetime import datetime, timedelta
from typing import Optional

import requests

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
CACHE_TTL_HOURS = 24

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(company_name: str) -> str:
    """Get cache file path for a company."""
    safe_name = company_name.lower().replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"funding_{safe_name}.json")


def _read_cache(company_name: str) -> Optional[dict]:
    """Read cached data if exists and not expired."""
    cache_path = _get_cache_path(company_name)
    if not os.path.exists(cache_path):
        return None

    try:
        with open(cache_path, "r") as f:
            cached = json.load(f)

        # Check TTL
        cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
        if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
            return None

        return cached.get("data")
    except Exception:
        return None


def _write_cache(company_name: str, data: dict) -> None:
    """Write data to cache."""
    cache_path = _get_cache_path(company_name)
    try:
        with open(cache_path, "w") as f:
            json.dump({
                "cached_at": datetime.now().isoformat(),
                "company": company_name,
                "data": data,
            }, f, indent=2, default=str)
    except Exception:
        pass  # Cache write failures are non-fatal

# Timeout for HTTP requests
TIMEOUT = 10

# Ticker map for common tech companies (symbol -> {name, domain})
TICKER_MAP = {
    "STRIPE": {"name": "Stripe", "domain": "stripe.com"},
    "SQ": {"name": "Block", "domain": "block.xyz"},
    "ABNB": {"name": "Airbnb", "domain": "airbnb.com"},
    "SHOP": {"name": "Shopify", "domain": "shopify.com"},
    "CRM": {"name": "Salesforce", "domain": "salesforce.com"},
    "NOW": {"name": "ServiceNow", "domain": "servicenow.com"},
    "TEAM": {"name": "Atlassian", "domain": "atlassian.com"},
    "DDOG": {"name": "Datadog", "domain": "datadoghq.com"},
    "NET": {"name": "Cloudflare", "domain": "cloudflare.com"},
    "MNDY": {"name": "Monday.com", "domain": "monday.com"},
    "SNOW": {"name": "Snowflake", "domain": "snowflake.com"},
    "U": {"name": "Unity Software", "domain": "unity.com"},
    "PLTR": {"name": "Palantir", "domain": "palantir.com"},
    "AI": {"name": "C3.ai", "domain": "c3.ai"},
    "PATH": {"name": "UiPath", "domain": "uipath.com"},
    "APPH": {"name": "AppHarmony", "domain": "appharbor.com"},
    "DOCU": {"name": "DocuSign", "domain": "docusign.com"},
    "ZM": {"name": "Zoom", "domain": "zoom.us"},
    "TWLO": {"name": "Twilio", "domain": "twilio.com"},
    "OKTA": {"name": "Okta", "domain": "okta.com"},
    "PAGERDUTY": {"name": "PagerDuty", "domain": "pagerduty.com"},
    "SPLK": {"name": "Splunk", "domain": "splunk.com"},
    "ANTHROPIC": {"name": "Anthropic", "domain": "anthropic.com"},
    "OPENAI": {"name": "OpenAI", "domain": "openai.com"},
    "DATABRICKS": {"name": "Databricks", "domain": "databricks.com"},
    "AIRECAST": {"name": "Aircast", "domain": "aircast.io"},
    "Figma": {"name": "Figma", "domain": "figma.com"},
    "NOTION": {"name": "Notion", "domain": "notion.so"},
    "LOOM": {"name": "Loom", "domain": "loom.com"},
    "CALENDLY": {"name": "Calendly", "domain": "calendly.com"},
}


def _get_public_company_info(ticker: str, retries: int = 4, delay_range: tuple = (2, 3)) -> dict:
    """
    Fetch public company info from Yahoo Finance API.

    Args:
        ticker: Stock ticker symbol
        retries: Number of retry attempts on rate limiting
        delay_range: Tuple of (min_delay, max_delay) seconds to wait before request

    Returns:
        Dict with market_cap, revenue, employees, sector, 52_week_range, price
        or empty dict if not found.
    """
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    params = {"modules": "financialData,defaultKeyStatistics,profile,price"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for attempt in range(retries + 1):
        # Add delay before each request (2-3 seconds)
        time_mod.sleep(random.uniform(delay_range[0], delay_range[1]))

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 429:
                # Rate limited - wait and retry with longer backoff
                if attempt < retries:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time_mod.sleep(wait_time)
                    continue
                return {}
            if resp.status_code != 200:
                return {}

            data = resp.json()
            result = data.get("quoteSummary", {}).get("result", [])
            if not result:
                return {}

            info = result[0]
            profile = info.get("profile", {}) or {}
            financial = info.get("financialData", {}) or {}
            key_stats = info.get("defaultKeyStatistics", {}) or {}
            price_info = info.get("price", {}) or {}

            # Check if company is public (has market cap)
            market_cap = financial.get("marketCap", {}).get("raw")
            if not market_cap:
                # Company might not be publicly traded
                return {}

            return {
                "ticker": ticker,
                "company_name": profile.get("longName") or price_info.get("shortName") or ticker,
                "market_cap": _format_market_cap(market_cap),
                "market_cap_raw": market_cap,
                "revenue": financial.get("totalRevenue", {}).get("raw") or 0,
                "employees": profile.get("employeeCount", {}).get("raw") or 0,
                "sector": profile.get("sector") or "unknown",
                "industry": profile.get("industry") or "unknown",
                "price": price_info.get("regularMarketPrice", {}).get("raw") or 0,
                "52_week_high": key_stats.get("fiftyTwoWeekHigh", {}).get("raw") or 0,
                "52_week_low": key_stats.get("fiftyTwoWeekLow", {}).get("raw") or 0,
                "is_public": True,
                "source": "Yahoo Finance",
            }
        except Exception:
            if attempt < retries:
                time_mod.sleep(1)
                continue
            return {}


def _format_market_cap(market_cap: int) -> str:
    """Format market cap in billions or millions."""
    if market_cap >= 1_000_000_000_000:
        return f"${market_cap / 1_000_000_000_000:.2f}T"
    elif market_cap >= 1_000_000_000:
        return f"${market_cap / 1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        return f"${market_cap / 1_000_000:.2f}M"
    return f"${market_cap:,}"


def _search_private_company(query: str) -> dict:
    """
    Search for private company info via web search.

    Args:
        query: Company name to search

    Returns:
        Dict with funding info or "unknown" values.
    """
    import re

    result = {
        "total_raised": "unknown",
        "last_round": "unknown",
        "last_round_amount": "unknown",
        "valuation": "unknown",
        "investors": [],
        "stage": "unknown",
        "source": "unknown",
    }

    # Try using BraveSearch service if available
    try:
        import sys as sys_mod
        sys_mod.path.insert(0, "/home/kaige/.openclaw/.openclaw/workspace/projects/ScoutAI/scout")
        from services.brave_search import BraveSearch
        search = BraveSearch()
        results = search.search(query=f"{query} funding round 2024 2025", count=5)
        if results and not results.get("error"):
            # Extract funding info from snippets
            for r in results.get("results", [])[:3]:
                snippet = r.get("snippet", "")
                # Try to find dollar amounts
                amounts = re.findall(r'\$[\d,]+(?:\.\d+)?[BM]?', snippet)
                if amounts:
                    result["last_round_amount"] = amounts[0]
                if "Series" in snippet:
                    stage_match = re.search(r'Series\s+[A-Z]', snippet)
                    if stage_match:
                        result["last_round"] = stage_match.group()
                result["source"] = r.get("url", "unknown")
            return result
    except Exception:
        pass

    # Try using Exa or other search services
    try:
        sys_mod.path.insert(0, "/home/kaige/.openclaw/.openclaw/workspace/projects/ScoutAI/scout")
        from services.exa import ExaSearch
        exa = ExaSearch()
        results = exa.search(query=f"{query} funding round", num_results=5)
        if results:
            for r in results[:3]:
                snippet = r.get("text", "")
                amounts = re.findall(r'\$[\d,]+(?:\.\d+)?[BM]?', snippet)
                if amounts and result["last_round_amount"] == "unknown":
                    result["last_round_amount"] = amounts[0]
                if "Series" in snippet and result["last_round"] == "unknown":
                    stage_match = re.search(r'Series\s+[A-Z]', snippet)
                    if stage_match:
                        result["last_round"] = stage_match.group()
            if results:
                result["source"] = "Exa Search"
            return result
    except Exception:
        pass

    result["source"] = "web search (no results)"
    return result


def get_funding_info(company_name: str, domain: Optional[str] = None, ticker: Optional[str] = None, company_type: str = "auto") -> dict:
    """
    Get funding and basic company info.

    Args:
        company_name: Company name (e.g., "Stripe", "Anthropic")
        domain: Company domain (e.g., "stripe.com")
        ticker: Stock ticker if public (e.g., "STRIPE")
        company_type: "public", "private", or "auto" (detect automatically)

    Returns:
        Dict with keys:
        - name, domain, ticker
        - market_cap, revenue, employees, sector, industry
        - total_raised, last_round, last_round_amount, valuation
        - investors, stage
        - is_public, confidence (HIGH/MEDIUM/LOW), source
    """
    # Check cache first for any company type
    cached = _read_cache(company_name)
    if cached:
        cached["_cache_hit"] = True
        return cached

    result = {
        "name": company_name,
        "domain": domain or "unknown",
        "ticker": ticker,
        "company_type": company_type,
        "market_cap": "unknown",
        "revenue": "unknown",
        "employees": "unknown",
        "sector": "unknown",
        "industry": "unknown",
        "price": "unknown",
        "52_week_range": "unknown",
        "total_raised": "unknown",
        "last_round": "unknown",
        "last_round_amount": "unknown",
        "valuation": "unknown",
        "investors": [],
        "stage": "unknown",
        "is_public": False,
        "confidence": "LOW",
        "source": "unknown",
    }

    # Try public company first if ticker provided or can be inferred
    if company_type == "public" or (company_type == "auto" and ticker):
        if ticker:
            info = _get_public_company_info(ticker.upper())
            if info:
                result.update(info)
                if info.get("52_week_high") and info.get("52_week_low"):
                    result["52_week_range"] = f"${info['52_week_low']:.2f} - ${info['52_week_high']:.2f}"
                result["company_type"] = "public"
                result["confidence"] = "HIGH"
                _write_cache(company_name, result)
                return result

    # Check ticker map if company_name matches (only for auto or public mode)
    if company_type in ("public", "auto"):
        for ticker_sym, ticker_info in TICKER_MAP.items():
            if ticker_info["name"].lower() == company_name.lower():
                info = _get_public_company_info(ticker_sym)
                if info and info.get("is_public"):
                    result.update(info)
                    if info.get("52_week_high") and info.get("52_week_low"):
                        result["52_week_range"] = f"${info['52_week_low']:.2f} - ${info['52_week_high']:.2f}"
                    result["company_type"] = "public"
                    result["confidence"] = "HIGH"
                    _write_cache(company_name, result)
                    return result

    # Try to detect if company is public via Yahoo Finance search
    if company_type == "auto":
        search_url = "https://query1.finance.yahoo.com/v1/finance/search"
        # Add delay before Yahoo Finance search API call
        time_mod.sleep(random.uniform(2, 3))
        try:
            resp = requests.get(
                search_url,
                params={"q": company_name, "quotesCount": 1, "newsCount": 0},
                timeout=TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                if quotes:
                    sym = quotes[0].get("symbol")
                    if sym:
                        info = _get_public_company_info(sym)
                        if info and info.get("is_public"):
                            result.update(info)
                            result["ticker"] = sym
                            if info.get("52_week_high") and info.get("52_week_low"):
                                result["52_week_range"] = f"${info['52_week_low']:.2f} - ${info['52_week_high']:.2f}"
                            result["company_type"] = "public"
                            result["confidence"] = "HIGH"
                            _write_cache(company_name, result)
                            return result
        except Exception:
            pass

    # Private company - use web search
    if company_type == "private" or company_type == "auto":
        search_result = _search_private_company(company_name)
        result.update(search_result)
        result["company_type"] = "private"
        result["confidence"] = "MEDIUM" if search_result.get("source") != "unknown" else "LOW"

    _write_cache(company_name, result)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        company = sys.argv[1]
        ticker = sys.argv[2] if len(sys.argv) > 2 else None
        result = get_funding_info(company, ticker=ticker)
        print(json.dumps(result, indent=2))
    else:
        # Test with Stripe
        print("Testing Stripe (public):")
        print(json.dumps(get_funding_info("Stripe", ticker="STRIPE", company_type="public"), indent=2))
