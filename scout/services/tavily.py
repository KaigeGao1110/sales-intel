"""Tavily AI-powered search API wrapper."""

import os
from typing import Optional
import requests
from rich.console import Console

console = Console()


class TavilyService:
    """Wrapper for the Tavily Search API (https://tavily.com)."""

    BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[yellow]Warning: TAVILY_API_KEY not set - Tavily search disabled[/yellow]"
            )

    def _post(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make a POST request to Tavily API."""
        if not self.available:
            return None
        headers = {"Content-Type": "application/json"}
        # Tavily requires API key in the JSON body, not URL params
        body = {**payload, "api_key": self.api_key}
        try:
            resp = requests.post(
                f"{self.BASE_URL}/{endpoint}",
                headers=headers,
                json=body,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Tavily HTTP error: {e}[/red]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Tavily request failed: {e}[/red]")
            return None
        except ValueError:
            console.print("[red]Tavily returned invalid JSON[/red]")
            return None

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """General web search via Tavily.

        Args:
            query: Search query string.
            max_results: Number of results to return (max 20).

        Returns:
            List of result dicts with keys: title, url, description, published_date.
        """
        data = self._post(
            "search",
            {
                "query": query,
                "max_results": min(max_results, 20),
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            },
        )
        if not data:
            return []
        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("content", ""),
                    "published_date": item.get("published_date", ""),
                }
            )
        return results

    def search_news(self, company: str, max_results: int = 10) -> list[dict]:
        """News search via Tavily.

        Args:
            company: Company name.
            max_results: Number of results to return.

        Returns:
            List of result dicts.
        """
        data = self._post(
            "search",
            {
                "query": f"{company} recent news",
                "max_results": min(max_results, 20),
                "search_depth": "basic",
                "include_answer": False,
                "include_raw_content": False,
            },
        )
        if not data:
            return []
        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("content", ""),
                    "published_date": item.get("published_date", ""),
                    "source": "tavily",
                }
            )
        return results

    def search_funding(self, company: str) -> list[dict]:
        """Search for funding/investment news."""
        return self.search(f'"{company}" funding investment round series', max_results=5)

    def search_hiring_signals(self, company: str) -> list[dict]:
        """Search for hiring/layoff signals."""
        return self.search(
            f'"{company}" layoffs OR hiring OR restructuring OR workforce',
            max_results=10,
        )

    def search_reviews(self, company: str) -> list[dict]:
        """Search for reviews and sentiment."""
        return self.search(f'"{company}" reviews customer feedback complaints', max_results=5)
