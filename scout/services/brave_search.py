"""Brave Search API wrapper for web and news search."""

import os
from typing import Optional
import requests
from rich.console import Console

console = Console()


class BraveSearchService:
    """Wrapper for the Brave Search API."""

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[yellow]Warning: BRAVE_API_KEY not set - web search disabled[/yellow]"
            )

    def search(self, query: str, count: int = 10) -> list[dict]:
        """Search the web using Brave Search API.

        Args:
            query: Search query string.
            count: Number of results to return (max 20).

        Returns:
            List of result dicts with keys: title, url, description, published_date.
        """
        if not self.available:
            console.print(
                f"[dim]Skipping Brave search for '{query}' (no API key)[/dim]"
            )
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": min(count, 20),
            "search_lang": "en",
            "safesearch": "moderate",
        }

        try:
            resp = requests.get(
                self.BASE_URL, headers=headers, params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Brave Search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Brave Search request failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]Brave Search returned invalid JSON[/red]")
            return []

        results = []
        web_results = data.get("web", {}).get("results", [])
        for item in web_results:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "published_date": item.get("page_age", ""),
                }
            )
        return results

    def search_news(self, company: str) -> list[dict]:
        """Search for company news articles."""
        return self.search(f'"{company}" news', count=10)

    def search_funding(self, company: str) -> list[dict]:
        """Search for company funding news."""
        return self.search(f'"{company}" funding investment round', count=5)

    def search_hiring_signals(self, company: str) -> list[dict]:
        """Search for hiring and workforce signals."""
        return self.search(
            f'"{company}" layoffs OR hiring OR expansion OR restructuring', count=10
        )

    def search_reviews(self, company: str) -> list[dict]:
        """Search for company reviews and sentiment."""
        return self.search(f'"{company}" reviews customers complaints', count=5)
