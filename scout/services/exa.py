"""Exa API wrapper for semantic/neural web search via api.exa.ai."""

import os
from typing import Optional
import requests
from rich.console import Console

console = Console()


class ExaService:
    """Wrapper for the Exa semantic search API (https://api.exa.ai).

    Exa provides neural/semantic web search, finding content by meaning
    rather than exact keyword matching.
    Best for: competitor analysis, finding similar companies, industry trends,
              semantic content discovery, "companies like X" queries.

    Requires: EXA_API_KEY in environment.
    """

    BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[dim]Exa: EXA_API_KEY not set - semantic search disabled[/dim]"
            )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def search(
        self,
        query: str,
        num_results: int = 10,
        use_autoprompt: bool = True,
    ) -> list[dict]:
        """Semantic/neural web search via Exa.

        Args:
            query: Natural language search query.
            num_results: Number of results to return.
            use_autoprompt: If True, Exa rewrites the query for better
                            semantic matching (recommended).

        Returns:
            List of result dicts with keys: title, url, description,
            published_date, score.
        """
        if not self.available:
            return []

        payload = {
            "query": query,
            "numResults": min(num_results, 100),
            "useAutoprompt": use_autoprompt,
            "contents": {"text": True},
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/search",
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Exa search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Exa search failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]Exa returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("published_date", ""),
                "score": item.get("score", 0),
                "source": "exa",
            })
        return results

    def find_similar(self, url: str, num_results: int = 5) -> list[dict]:
        """Find web pages similar to a given URL (semantic similarity).

        Args:
            url: Reference URL to find similar pages for.
            num_results: Number of similar results to return.

        Returns:
            List of result dicts with keys: title, url, description,
            published_date, score.
        """
        if not self.available:
            return []

        payload = {
            "url": url,
            "numResults": min(num_results, 20),
            "contents": {"text": True},
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/findSimilar",
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Exa findSimilar HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Exa findSimilar failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]Exa returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("published_date", ""),
                "score": item.get("score", 0),
                "source": "exa_similar",
            })
        return results

    def search_news(self, company: str) -> list[dict]:
        """Semantic news search for a company.

        Args:
            company: Company name.

        Returns:
            List of result dicts focused on recent news.
        """
        if not self.available:
            return []

        payload = {
            "query": f"{company} news recent events announcements",
            "numResults": 10,
            "useAutoprompt": True,
            "contents": {"text": True},
            "category": "news",
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/search",
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Exa news search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Exa news search failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]Exa returned invalid JSON[/red]")
            return []

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("snippet", ""),
                "published_date": item.get("published_date", ""),
                "score": item.get("score", 0),
                "source": "exa_news",
            })
        return results

    def search_competitors(self, company: str) -> list[dict]:
        """Find competitors and similar companies using semantic search.

        Args:
            company: Company name.

        Returns:
            List of result dicts about competitor companies.
        """
        return self.search(
            f"Companies similar to {company} competitors alternatives",
            num_results=10,
            use_autoprompt=True,
        )
