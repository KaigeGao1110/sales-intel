"""Hunter.io API wrapper for email discovery and verification."""

import os
import requests
from typing import Optional
from rich.console import Console

console = Console()


class HunterService:
    """Wrapper for Hunter.io API (https://hunter.io)."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        self.available = bool(self.api_key)
        self._quota: Optional[dict] = None
        if not self.available:
            console.print(
                "[yellow]Warning: HUNTER_API_KEY not set - email discovery disabled[/yellow]"
            )

    def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        """Make a GET request to Hunter API."""
        if not self.available:
            return None
        params["api_key"] = self.api_key
        try:
            resp = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                timeout=10,
            )
            if resp.status_code == 401:
                console.print("[red]Hunter.io: Invalid API key[/red]")
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]Hunter.io HTTP error: {e}[/red]")
            return None
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Hunter.io request failed: {e}[/red]")
            return None

    def quota(self) -> dict:
        """Return current API quota usage."""
        if self._quota is None:
            self._quota = self._get("account", {})
        return self._quota or {}

    def find_email(self, domain: str, first_name: str = "", last_name: str = "",
                   company: str = "", full_name: str = "") -> Optional[dict]:
        """Find email by domain and person name.

        Args:
            domain: Company domain (e.g. 'stripe.com').
            first_name: First name of person.
            last_name: Last name of person.
            company: Company name (improves accuracy).
            full_name: Full name (alternative to first/last).

        Returns:
            Dict with email, position, linkedin_url, confidence, or None.
        """
        params: dict = {"domain": domain}
        if full_name:
            params["full_name"] = full_name
        else:
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
        if company:
            params["company"] = company

        data = self._get("email-finder", params)
        if not data:
            return None

        result = data.get("data", {})
        if not result.get("email"):
            return None

        return {
            "email": result.get("email"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "position": result.get("position"),
            "confidence": result.get("score"),
            "linkedin_url": result.get("linkedin_url"),
            "twitter": result.get("twitter"),
            "phone": result.get("phone_number"),
            "verification": result.get("verification", {}),
            "accept_all": result.get("accept_all"),
        }

    def domain_search(self, domain: str, company: str = "",
                      seniority: str = "", department: str = "") -> list[dict]:
        """Find emails for a company domain.

        Args:
            domain: Company domain.
            company: Company name (improves results).
            seniority: Filter by seniority ('junior', 'senior', 'executive').
            department: Filter by department ('executive', 'it', 'finance', etc).

        Returns:
            List of contact dicts with email, name, position, linkedin.
        """
        params: dict = {"domain": domain}
        if company:
            params["company"] = company
        if seniority:
            params["seniority"] = seniority
        if department:
            params["department"] = department

        data = self._get("domain-search", params)
        if not data:
            return []

        contacts = []
        for item in data.get("data", {}).get("emails", []):
            contacts.append({
                "email": item.get("value"),
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "position": item.get("position"),
                "confidence": item.get("confidence"),
                "seniority": item.get("seniority"),
                "department": item.get("department"),
                "linkedin_url": item.get("linkedin"),
                "verification": item.get("verification", {}),
                "accept_all": item.get("accept_all"),
            })
        return contacts

    def verify(self, email: str) -> Optional[dict]:
        """Verify if an email address exists.

        Returns:
            Dict with status ('valid'/'invalid'/'accept_all'), or None on error.
        """
        data = self._get("email-verifier", {"email": email})
        if not data:
            return None
        result = data.get("data", {})
        return {
            "email": result.get("email"),
            "status": result.get("status"),
            "score": result.get("score"),
            "regexp": result.get("regexp"),
            "gibberish": result.get("gibberish"),
            "disposable": result.get("disposable"),
            "webmail": result.get("webmail"),
        }
