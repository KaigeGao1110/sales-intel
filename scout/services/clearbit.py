"""Clearbit company enrichment API wrapper."""

import os
from typing import Optional
import requests
from rich.console import Console

console = Console()


class ClearbitService:
    """Wrapper for Clearbit company enrichment API."""

    COMPANY_URL = "https://company.clearbit.com/v2/companies/find"
    LOGO_URL = "https://logo.clearbit.com"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("CLEARBIT_API_KEY")
        self.available = bool(self.api_key)
        if not self.available:
            console.print(
                "[yellow]Warning: CLEARBIT_API_KEY not set - company enrichment disabled[/yellow]"
            )

    def enrich_by_domain(self, domain: str) -> Optional[dict]:
        """Enrich company data using domain name.

        Args:
            domain: Company domain (e.g. 'acme.com').

        Returns:
            Dict with company info or None if not found/unavailable.
        """
        if not self.available:
            return None

        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"domain": domain}

        try:
            resp = requests.get(
                self.COMPANY_URL, headers=headers, params=params, timeout=10
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Clearbit HTTP error: {e}[/red]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Clearbit request failed: {e}[/red]")
            return None
        except ValueError:
            console.print("[red]Clearbit returned invalid JSON[/red]")
            return None

        return self._parse_company(data)

    def enrich_by_name(self, company_name: str) -> Optional[dict]:
        """Enrich company data using company name.

        Args:
            company_name: Name of the company.

        Returns:
            Dict with company info or None if not found/unavailable.
        """
        if not self.available:
            return None

        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"name": company_name}

        try:
            resp = requests.get(
                self.COMPANY_URL, headers=headers, params=params, timeout=10
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Clearbit HTTP error: {e}[/red]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Clearbit request failed: {e}[/red]")
            return None
        except ValueError:
            console.print("[red]Clearbit returned invalid JSON[/red]")
            return None

        return self._parse_company(data)

    def _parse_company(self, data: dict) -> dict:
        """Extract relevant fields from Clearbit company response."""
        metrics = data.get("metrics", {})
        return {
            "name": data.get("name", ""),
            "domain": data.get("domain", ""),
            "description": data.get("description", ""),
            "industry": data.get("category", {}).get("industry", ""),
            "sector": data.get("category", {}).get("sector", ""),
            "employee_count": metrics.get("employees"),
            "annual_revenue": metrics.get("annualRevenue"),
            "location": data.get("location", ""),
            "country": data.get("geo", {}).get("countryCode", ""),
            "founded_year": data.get("foundedYear"),
            "type": data.get("type", ""),
            "tags": data.get("tags", []),
            "tech_stack": [
                t.get("name", "") for t in data.get("tech", [])
            ],
        }
