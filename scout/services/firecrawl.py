"""Firecrawl API wrapper for deep web scraping and content extraction."""

import os
import time
from typing import Optional
import requests
from rich.console import Console

console = Console()


class FirecrawlService:
    """Wrapper for the Firecrawl API (https://firecrawl.dev).

    Firecrawl provides deep web scraping with full page content extraction.
    Best for: company websites, blogs, news article content, deep crawling.

    Requires: FIRECRAWL_API_KEY in environment.
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[dim]Firecrawl: FIRECRAWL_API_KEY not set - deep content scraping disabled[/dim]"
            )

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def scrape(self, url: str) -> dict:
        """Scrape a single URL and extract full page content.

        Args:
            url: URL to scrape.

        Returns:
            dict with keys: url, markdown (full page text), title.
            Returns empty dict on failure.
        """
        if not self.available:
            return {}

        try:
            resp = requests.post(
                f"{self.BASE_URL}/scrape",
                headers=self._headers(),
                json={"url": url, "page_options": {"only_main_content": False}},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "url": url,
                "markdown": data.get("data", {}).get("markdown", ""),
                "title": data.get("data", {}).get("title", ""),
            }
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Firecrawl scrape HTTP error: {e}[/red]")
            return {}
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Firecrawl scrape failed: {e}[/red]")
            return {}

    def crawl_site(self, url: str, limit: int = 5) -> list[dict]:
        """Crawl an entire site/domain and return all discovered pages.

        Args:
            url: Starting URL or root URL of the site.
            limit: Maximum number of pages to crawl (default 5).

        Returns:
            List of dicts, each with: url, markdown, title.
        """
        if not self.available:
            return []

        try:
            resp = requests.post(
                f"{self.BASE_URL}/crawl",
                headers=self._headers(),
                json={
                    "url": url,
                    "page_options": {"only_main_content": False},
                    "limit": limit,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            job_id = data.get("jobId")
            if not job_id:
                return []

            # Poll for completion (up to 30s)
            for _ in range(15):
                time.sleep(2)
                status_resp = requests.get(
                    f"{self.BASE_URL}/crawl/status/{job_id}",
                    headers=self._headers(),
                    timeout=10,
                )
                status_data = status_resp.json()
                if status_data.get("status") == "completed":
                    pages = status_data.get("data", [])
                    return [
                        {
                            "url": p.get("url", ""),
                            "markdown": p.get("markdown", ""),
                            "title": p.get("title", ""),
                        }
                        for p in pages
                    ]
                elif status_data.get("status") in ("failed", "cancelled"):
                    console.print(f"[red]Firecrawl crawl job {status_data.get('status')}: {url}[/red]")
                    return []
            console.print(f"[yellow]Firecrawl crawl timed out for: {url}[/yellow]")
            return []
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Firecrawl crawl HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Firecrawl crawl failed: {e}[/red]")
            return {}

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search the web and scrape content from top results.

        Args:
            query: Search query.
            limit: Number of results to scrape (default 5).

        Returns:
            List of dicts with keys: url, title, description, markdown.
        """
        if not self.available:
            return []

        try:
            resp = requests.post(
                f"{self.BASE_URL}/search",
                headers=self._headers(),
                json={"query": query, "limit": limit},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("data", []):
                url = item.get("url", "")
                if url:
                    scraped = self.scrape(url)
                    results.append({
                        "url": url,
                        "title": item.get("title", "") or scraped.get("title", ""),
                        "description": item.get("description", ""),
                        "markdown": scraped.get("markdown", ""),
                    })
            return results
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Firecrawl search HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Firecrawl search failed: {e}[/red]")
            return []
