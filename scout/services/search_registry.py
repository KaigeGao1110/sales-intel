"""SearchToolRegistry - unified tool routing for all search backends.

This module provides a single entry point for all search operations,
automatically selecting the best available tool(s) based on task type.
Falls back gracefully when API keys are not configured.
"""

import re
from typing import Optional

from rich.console import Console

from services.brave_search import BraveSearchService
from services.tavily import TavilyService
from services.serpapi import SerpAPIService
from services.exa import ExaService
from services.firecrawl import FirecrawlService

console = Console()


class SearchToolRegistry:
    """
    Unified search tool registry with automatic tool routing.

    Tool characteristics (used by routing logic):
    ┌─────────────┬────────────────────────────────────────────────────────────┐
    │ Tool        │ Best for                                                 │
    ├─────────────┼────────────────────────────────────────────────────────────┤
    │ brave       │ Real-time web search, no API key needed for basic use     │
    │ tavily      │ AI-optimized summaries, news, answer-style results         │
    │ serpapi     │ Google SERP authority, precise results, date filtering    │
    │ exa         │ Semantic search, competitor analysis, "similar to X"       │
    │ firecrawl   │ Deep content extraction, full-page scraping, crawling     │
    └─────────────┴────────────────────────────────────────────────────────────┘

    Routing priority by task_type:
    ┌──────────────┬──────────────────────────────────────────────────────────┐
    │ task_type    │ Priority chain (first available wins)                    │
    ├──────────────┼──────────────────────────────────────────────────────────┤
    │ news         │ tavily → brave → serpapi                                │
    │ funding      │ serpapi → tavily → brave                                 │
    │ hiring       │ brave → serpapi → tavily                                │
    │ competitor   │ exa → tavily                                             │
    │ deep_content │ firecrawl → tavily                                       │
    │ reviews      │ serpapi → brave                                          │
    │ general      │ brave → tavily → serpapi                                 │
    │ historical   │ serpapi (date filter) + brave (freshness param)          │
    └──────────────┴──────────────────────────────────────────────────────────┘
    """

    # Routing priority: list of (tool_name, task_type) tuples, in priority order
    ROUTING_TABLE: dict[str, list[tuple[str, ...]]] = {
        "news": [
            ("tavily", "AI summary + news"),
            ("brave", "real-time news"),
            ("serpapi", "Google News authority"),
            ("exa", "semantic news"),
        ],
        "funding": [
            ("serpapi", "Google SERP precision"),
            ("tavily", "AI summary"),
            ("brave", "real-time"),
        ],
        "hiring": [
            ("brave", "real-time postings"),
            ("serpapi", "Google Jobs"),
            ("tavily", "AI summary"),
        ],
        "competitor": [
            ("exa", "semantic similarity"),
            ("tavily", "AI overview"),
            ("serpapi", "competitor pages"),
        ],
        "deep_content": [
            ("firecrawl", "full page extraction"),
            ("tavily", "AI summary"),
            ("brave", "basic"),
        ],
        "reviews": [
            ("serpapi", "Google reviews + G2"),
            ("brave", "real-time"),
            ("tavily", "AI summary"),
        ],
        "general": [
            ("brave", "real-time, free tier"),
            ("tavily", "AI optimized"),
            ("serpapi", "authoritative"),
        ],
    }

    def __init__(self) -> None:
        # Lazily instantiate services (only when needed / available)
        self._brave: Optional[BraveSearchService] = None
        self._tavily: Optional[TavilyService] = None
        self._serpapi: Optional[SerpAPIService] = None
        self._exa: Optional[ExaService] = None
        self._firecrawl: Optional[FirecrawlService] = None

    # --- Lazy service accessors ---

    @property
    def brave(self) -> BraveSearchService:
        if self._brave is None:
            self._brave = BraveSearchService()
        return self._brave

    @property
    def tavily(self) -> TavilyService:
        if self._tavily is None:
            self._tavily = TavilyService()
        return self._tavily

    @property
    def serpapi(self) -> SerpAPIService:
        if self._serpapi is None:
            self._serpapi = SerpAPIService()
        return self._serpapi

    @property
    def exa(self) -> ExaService:
        if self._exa is None:
            self._exa = ExaService()
        return self._exa

    @property
    def firecrawl(self) -> FirecrawlService:
        if self._firecrawl is None:
            self._firecrawl = FirecrawlService()
        return self._firecrawl

    # --- Public API ---

    def get_available_tools(self) -> list[str]:
        """Return a list of tool names that have valid API keys."""
        available = []
        if self.brave.available:
            available.append("brave")
        if self.tavily.available:
            available.append("tavily")
        if self.serpapi.available:
            available.append("serpapi")
        if self.exa.available:
            available.append("exa")
        if self.firecrawl.available:
            available.append("firecrawl")
        return available

    def route(self, task_type: str, company: str, **kwargs) -> list[dict]:
        """
        Route a search task to the best available tool.

        Args:
            task_type: One of "news", "funding", "hiring", "competitor",
                       "deep_content", "reviews", "general".
            company: Company name to search for.
            **kwargs: Additional args passed to the underlying search method
                      (e.g. num, limit, domain).

        Returns:
            Merged, deduplicated list of result dicts from all successful calls.
        """
        priority_chain = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["general"])

        all_results: list[dict] = []
        seen_urls: set[str] = set()

        for tool_name, reason in priority_chain:
            if not self._is_tool_available(tool_name):
                continue

            results = self._execute_tool(tool_name, task_type, company, **kwargs)
            if not results:
                continue

            # Deduplicate by URL
            for item in results:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(item)

            # If we got results from the primary tool, we could either:
            # (a) continue to secondary tools for more results, or
            # (b) stop after first successful. We choose (a) to maximize coverage.
            # Adjust this if you prefer speed over completeness.

        return all_results

    def search_with_date(
        self,
        query: str,
        after_date: str,
        before_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Perform a date-filtered historical search.

        Args:
            query: Search query string.
            after_date: Start date in "YYYY-MM-DD" format.
            before_date: End date in "YYYY-MM-DD" format (optional).

        Returns:
            Merged results from brave + serpapi with date filtering applied.
        """
        # Convert "YYYY-MM-DD" to "MM/DD/YYYY" for serpapi tbs format
        after_parts = after_date.split("-")
        after_mmddyyyy = f"{after_parts[1]}/{after_parts[2]}/{after_parts[0]}" if len(after_parts) == 3 else after_date

        before_mmddyyyy: Optional[str] = None
        if before_date:
            before_parts = before_date.split("-")
            before_mmddyyyy = f"{before_parts[1]}/{before_parts[2]}/{before_parts[0]}" if len(before_parts) == 3 else before_date

        all_results: list[dict] = []
        seen_urls: set[str] = set()

        # SerpAPI date filter
        if self.serpapi.available:
            results = self.serpapi.search_with_date_range(
                query, after_mmddyyyy, before_mmddyyyy
            )
            for item in results:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(item)

        # Brave freshness parameter
        if self.brave.available:
            # Map date to Brave freshness
            freshness = self._map_date_to_brave_freshness(after_date)
            results = self.brave.search(query)
            for item in results:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(item)

        return all_results

    def deep_scrape(self, url: str) -> dict:
        """
        Deep-scrape a single URL using Firecrawl (full page content).

        Args:
            url: URL to scrape.

        Returns:
            dict with url, markdown, title. Empty dict if unavailable.
        """
        if self.firecrawl.available:
            return self.firecrawl.scrape(url)
        # Fallback: try tavily basic
        if self.tavily.available:
            results = self.tavily.search(url)
            if results:
                return {
                    "url": url,
                    "markdown": results[0].get("description", ""),
                    "title": results[0].get("title", ""),
                }
        return {}

    # --- Internal helpers ---

    def _is_tool_available(self, tool_name: str) -> bool:
        """Check if a specific tool has a valid API key."""
        return getattr(self, tool_name).available

    def _execute_tool(
        self,
        tool_name: str,
        task_type: str,
        company: str,
        **kwargs,
    ) -> list[dict]:
        """Execute a search using the specified tool and task type."""
        tool = getattr(self, tool_name)
        query = kwargs.get("query", f'"{company}"')

        try:
            if tool_name == "brave":
                if task_type == "news":
                    return tool.search_news(company)
                elif task_type == "funding":
                    return tool.search_funding(company)
                elif task_type == "hiring":
                    return tool.search_hiring_signals(company)
                elif task_type == "reviews":
                    return tool.search_reviews(company)
                return tool.search(query)

            elif tool_name == "tavily":
                if task_type == "news":
                    return tool.search_news(company)
                elif task_type == "funding":
                    return tool.search_funding(company)
                elif task_type == "hiring":
                    return tool.search_hiring_signals(company)
                elif task_type == "reviews":
                    return tool.search_reviews(company)
                return tool.search(query)

            elif tool_name == "serpapi":
                if task_type == "news":
                    return tool.search_news(company)
                elif task_type == "funding":
                    return tool.search_funding(company)
                elif task_type == "hiring":
                    return tool.search_jobs(company)
                elif task_type == "reviews":
                    return tool.search(query, num=kwargs.get("num", 10))
                return tool.search(query)

            elif tool_name == "exa":
                if task_type == "news":
                    return tool.search_news(company)
                elif task_type == "competitor":
                    return tool.search_competitors(company)
                return tool.search(query, num_results=kwargs.get("num", 10))

            elif tool_name == "firecrawl":
                if task_type == "deep_content":
                    return tool.search(query, limit=kwargs.get("limit", 5))
                return tool.search(query, limit=kwargs.get("limit", 3))

            return []
        except Exception as e:
            console.print(f"[red]SearchToolRegistry: {tool_name} failed for {task_type}: {e}[/red]")
            return []

    @staticmethod
    def _map_date_to_brave_freshness(date_str: str) -> str:
        """
        Map a YYYY-MM-DD date string to Brave freshness parameter.
        This is an approximation - Brave freshness is: day, week, month, year.
        """
        from datetime import datetime, timedelta

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            days_ago = (datetime.now() - date).days

            if days_ago <= 1:
                return "day"
            elif days_ago <= 7:
                return "week"
            elif days_ago <= 30:
                return "month"
            else:
                return "year"
        except ValueError:
            return "month"
