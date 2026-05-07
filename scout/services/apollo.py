"""Apollo.io API wrapper for B2B company enrichment and people search."""

import os
import time
import requests
from typing import Optional
from rich.console import Console

console = Console()


class ApolloService:
    """Wrapper for Apollo.io API (https://apollo.io).

    Supports:
    - Organization enrichment (company details, tech stack, funding)
    - People search (contacts by company domain/name)
    - Organization search (competitor discovery by keyword)
    """

    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[yellow]Warning: APOLLO_API_KEY not set - Apollo enrichment disabled[/yellow]"
            )

    def _post(self, endpoint: str, body: dict, retries: int = 1) -> Optional[dict]:
        """Make a POST request to Apollo API with optional retry on 429."""
        if not self.available:
            return None
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Content-Type": "application/json", "X-Api-Key": self.api_key}
        for attempt in range(retries + 1):
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=15)
                if resp.status_code == 401:
                    console.print("[red]Apollo.io: Invalid API key[/red]")
                    self.available = False
                    return None
                if resp.status_code == 429:
                    if attempt < retries:
                        console.print("[yellow]Apollo.io rate limited, retrying in 1s...[/yellow]")
                        time.sleep(1)
                        continue
                    console.print("[red]Apollo.io rate limit exceeded[/red]")
                    return None
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                console.print(f"[red]Apollo.io HTTP error: {e}[/red]")
                return None
            except requests.exceptions.RequestException as e:
                console.print(f"[red]Apollo.io request failed: {e}[/red]")
                return None
        return None

    def _get(self, endpoint: str, params: dict, retries: int = 1) -> Optional[dict]:
        """Make a GET request to Apollo API."""
        if not self.available:
            return None
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"X-Api-Key": self.api_key}
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 401:
                    console.print("[red]Apollo.io: Invalid API key[/red]")
                    self.available = False
                    return None
                if resp.status_code == 429:
                    if attempt < retries:
                        console.print("[yellow]Apollo.io rate limited, retrying in 1s...[/yellow]")
                        time.sleep(1)
                        continue
                    console.print("[red]Apollo.io rate limit exceeded[/red]")
                    return None
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                console.print(f"[red]Apollo.io HTTP error: {e}[/red]")
                return None
            except requests.exceptions.RequestException as e:
                console.print(f"[red]Apollo.io request failed: {e}[/red]")
                return None
        return None

    def enrich_organization(self, domain: str) -> dict:
        """Enrich company data using domain.

        Args:
            domain: Company domain (e.g. 'stripe.com').

        Returns:
            Dict with company details:
            {name, industry, employee_count, founded_year,
             funding_total, technology_names, linkedin_url, ...}
            Empty dict if unavailable or not found.
        """
        data = self._get(
            "organizations/enrich",
            params={"domain": domain},  # api_key passed via X-Api-Key header in _get()
        )
        if not data:
            return {}

        org = data.get("organization", {})
        if not org:
            return {}

        return {
            "name": org.get("name", ""),
            "domain": org.get("domain", ""),
            "industry": org.get("industry", ""),
            "employee_count": org.get("estimated_num_employees"),
            "founded_year": org.get("founded_year"),
            "funding_total": org.get("total_funding"),
            "funding_stage": org.get("latest_funding_round"),
            "technology_names": org.get("technology_names", []),
            "linkedin_url": org.get("linkedin_url", ""),
            "description": org.get("description", ""),
            "city": org.get("city", ""),
            "country": org.get("country", ""),
            "phone": org.get("phone_number", ""),
            "employee_range": org.get("employee_count_range", ""),
            "alexa_ranking": org.get("alexa_ranking"),
            "seo_description": org.get("seo_description", ""),
        }

    def search_people(
        self,
        company_name: str,
        domain: str = "",
        titles: Optional[list[str]] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Search for contacts at a company.

        Args:
            company_name: Name of the company.
            domain: Company domain for precision.
            titles: List of title keywords to filter (default: exec/eng titles).
            limit: Max number of contacts to return.

        Returns:
            List of contact dicts:
            [{name, title, email, linkedin_url, organization_name}, ...]
        """
        if titles is None:
            titles = ["CEO", "CTO", "VP Sales", "Head of Engineering", "COO", "CMO"]

        body = {
            "q_organization_name": company_name,
            "person_titles": titles,
            "per_page": limit,
        }
        if domain:
            body["organization_domains"] = [domain]

        data = self._post("people/search", body)
        if not data:
            return []

        people = data.get("people", [])
        contacts = []
        for p in people:
            name = " ".join(filter(None, [p.get("first_name"), p.get("last_name")]))
            if not name:
                continue
            contacts.append({
                "name": name,
                "first_name": p.get("first_name", ""),
                "last_name": p.get("last_name", ""),
                "title": p.get("title", ""),
                "email": p.get("email", ""),
                "linkedin_url": p.get("linkedin_url", ""),
                "organization_name": p.get("organization_name", ""),
                "email_status": p.get("email_status", ""),
                "departments": p.get("departments", []),
            })
        return contacts

    def search_organizations(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search for organizations by keyword (competitor discovery).

        Args:
            keyword: Search keyword (company name, industry, etc.).
            limit: Max number of results.

        Returns:
            List of org dicts: [{name, domain, industry, employee_count}, ...]
        """
        body = {
            "q": keyword,
            "sort_by_field": "revealed_from_page_views",
            "per_page": limit,
        }
        data = self._post("mixed_companies/search", body)
        if not data:
            return []

        orgs = data.get("organizations", [])
        results = []
        for o in orgs:
            results.append({
                "name": o.get("name", ""),
                "domain": o.get("domain", ""),
                "industry": o.get("industry", ""),
                "employee_count": o.get("estimated_num_employees"),
                "linkedin_url": o.get("linkedin_url", ""),
                "city": o.get("city", ""),
                "country": o.get("country", ""),
            })
        return results
