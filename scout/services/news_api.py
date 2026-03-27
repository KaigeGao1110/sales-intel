"""NewsAPI.org wrapper for fetching company news articles."""

import os
from datetime import datetime, timedelta
from typing import Optional
import requests
from rich.console import Console

console = Console()


class NewsAPIService:
    """Wrapper for the NewsAPI.org API."""

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[yellow]Warning: NEWS_API_KEY not set - NewsAPI disabled[/yellow]"
            )

    def get_company_news(
        self, company: str, days_back: int = 30
    ) -> list[dict]:
        """Fetch recent news articles about a company.

        Args:
            company: Company name to search for.
            days_back: How many days back to search.

        Returns:
            List of article dicts with keys: title, url, description,
            published_date, source.
        """
        if not self.available:
            console.print(
                f"[dim]Skipping NewsAPI for '{company}' (no API key)[/dim]"
            )
            return []

        from_date = (datetime.now() - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )

        params = {
            "q": company,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey": self.api_key,
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]NewsAPI HTTP error: {e}[/red]")
            return []
        except requests.exceptions.RequestException as e:
            console.print(f"[red]NewsAPI request failed: {e}[/red]")
            return []
        except ValueError:
            console.print("[red]NewsAPI returned invalid JSON[/red]")
            return []

        if data.get("status") != "ok":
            console.print(
                f"[red]NewsAPI error: {data.get('message', 'unknown error')}[/red]"
            )
            return []

        results = []
        for article in data.get("articles", []):
            results.append(
                {
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "description": article.get("description", ""),
                    "published_date": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", ""),
                }
            )
        return results
