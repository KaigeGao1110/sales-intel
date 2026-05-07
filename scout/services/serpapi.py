"""SerpAPI wrapper for Google search results via serpapi.com."""

import os
from typing import Optional
import requests
from rich.console import Console

console = Console()


class SerpAPIService:
    """Wrapper for the SerpAPI Google search API (https://serpapi.com).

    SerpAPI provides authoritative Google SERP data with rich snippets.
    Best for: precise Google search results, funding data, job postings,
              authoritative web search when you need exact SERP positioning.

    Requires: SERPAPI_KEY in environment.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[dim]SerpAPI: SERPAPI_KEY not set - authoritative Google search disabled[/dim]"
            )

    def search(self, query: str, num: int = 10) -> list[dict]:
        """General web search via Google SERP.

        Args:
            query: Search query string.
            num: Number of results to return (max 100).

        Returns:
            List of result dicts with keys: title, url, description, published_date.
        """
        if not self.available:
            return []

        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": min(num, 100),
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]SerpAPI search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]SerpAPI search failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]SerpAPI returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("cached_page_link", ""),
                "source": "serpapi",
            })
        return results

    def search_news(self, company: str) -> list[dict]:
        """News search for a company via Google News.

        Args:
            company: Company name.

        Returns:
            List of result dicts.
        """
        if not self.available:
            return []

        params = {
            "q": f'"{company}" news',
            "api_key": self.api_key,
            "engine": "google_news",
            "num": 10,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]SerpAPI news HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]SerpAPI news failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]SerpAPI returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("news_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("date", ""),
                "source": item.get("source", {}).get("name", ""),
            })
        return results

    def search_funding(self, company: str) -> list[dict]:
        """Search for company funding and investment news.

        Args:
            company: Company name.

        Returns:
            List of result dicts focused on funding rounds.
        """
        return self.search(f'"{company}" funding investment round series', num=10)

    def search_jobs(self, company: str) -> list[dict]:
        """Search for company job openings and hiring activity.

        Args:
            company: Company name.

        Returns:
            List of result dicts from Google Jobs.
        """
        if not self.available:
            return []

        params = {
            "q": f'"{company}" jobs hiring',
            "api_key": self.api_key,
            "engine": "google_jobs",
            "num": 10,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]SerpAPI jobs HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]SerpAPI jobs failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]SerpAPI returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("jobs_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", "") or item.get("apply_link", ""),
                "description": item.get("description", ""),
                "published_date": item.get("posted_date", ""),
                "source": "serpapi_jobs",
            })
        return results

    def search_with_date_range(
        self, query: str, after_date: str, before_date: Optional[str] = None
    ) -> list[dict]:
        """Search with a specific date range (for historical research).

        Args:
            query: Search query.
            after_date: Start date in "MM/DD/YYYY" format.
            before_date: End date in "MM/DD/YYYY" format (optional).

        Returns:
            List of result dicts with date filtering applied.
        """
        if not self.available:
            return []

        # Build tbs (tools button search) date filter for Google
        if before_date:
            tbs = f"cdr:1,cd_min:{after_date},cd_max:{before_date}"
        else:
            tbs = f"cdr:1,cd_min:{after_date}"

        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": 20,
            "tbs": tbs,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]SerpAPI date-range search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]SerpAPI date-range search failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]SerpAPI returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("cached_page_link", ""),
                "source": "serpapi_historical",
            })
        return results
