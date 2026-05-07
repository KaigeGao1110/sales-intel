"""Research Agent (Level 1) - orchestrates sub-researchers for company intelligence."""

from typing import Optional

from rich.console import Console

from services.clearbit import ClearbitService
from services.apollo import ApolloService
from services.search_registry import SearchToolRegistry
from agents.researchers import news as news_researcher
from agents.researchers import web as web_researcher
from agents.researchers import reviews as reviews_researcher

console = Console()


class ResearchAgent:
    """Fetches and aggregates company intelligence via Level 2 sub-researchers.

    Uses SearchToolRegistry for intelligent tool routing instead of hardcoded
    service calls, enabling automatic fallback and best-tool selection.
    """

    def __init__(self) -> None:
        self.registry = SearchToolRegistry()
        self.clearbit = ClearbitService()
        self.apollo = ApolloService()

    def research(
        self,
        company_name: str,
        domain: str = "",
        historical_month: Optional[str] = None,
    ) -> dict:
        """Run full research pipeline for a company.

        Args:
            company_name: Name of the company to research.
            domain: Optional domain for Clearbit enrichment.
            historical_month: Optional month in "YYYY-MM" format.
                              When provided, searches are date-filtered to that month
                              for historical reconstruction.

        Returns:
            Structured dict with keys:
                news, jobs_signal, funding, reviews_signal,
                enrichment, raw_signals.
        """
        console.print(f"\n[bold cyan]Researching:[/bold cyan] {company_name}")
        if historical_month:
            console.print(f"[dim]  Historical mode: {historical_month}[/dim]")

        # --- Tool routing info ---
        available = self.registry.get_available_tools()
        console.print(f"[dim]  Available search tools: {', '.join(available) or 'none'}[/dim]")

        # --- Level 2 Sub-Researchers (still use their own signal logic) ---
        console.print("[dim]  Running NewsResearcher...[/dim]")
        news_data = news_researcher.run(company_name)

        console.print("[dim]  Running WebResearcher (hiring/funding)...[/dim]")
        web_data = web_researcher.run(company_name)

        console.print("[dim]  Running ReviewResearcher...[/dim]")
        reviews_data = reviews_researcher.run(company_name)

        # --- Historical mode: supplement with date-filtered search ---
        if historical_month:
            console.print(f"[dim]  Running historical search for {historical_month}...[/dim]")
            historical_results = self._run_historical_search(company_name, historical_month)
            web_data["historical"] = historical_results
        else:
            web_data["historical"] = []

        # --- Merge results ---
        merged_news = news_data["articles"]
        jobs_signal = web_data["jobs_signal"]
        funding_signal = web_data["funding"]
        raw_signals = web_data["raw_signals"]
        reviews_signal = reviews_data["reviews_signal"]

        # Supplement raw_signals with news text
        for item in merged_news:
            text = f"{item.get('title', '')} {item.get('description', '')}".strip()
            if text:
                raw_signals.append(text[:200])

        # Supplement with historical signals if available
        for item in web_data.get("historical", []):
            text = f"{item.get('title', '')} {item.get('description', '')}".strip()
            if text and text[:200] not in raw_signals:
                raw_signals.append(text[:200])

        # --- Apollo Enrichment (preferred, more complete than Clearbit) ---
        enrichment: dict = {}
        if self.apollo.available:
            console.print("[dim]  Enriching via Apollo.io...[/dim]")
            if domain:
                enrichment = self.apollo.enrich_organization(domain) or {}
            if enrichment:
                console.print(f"[dim]  Apollo enrichment: {enrichment.get('name', 'N/A')} — "
                              f"{enrichment.get('employee_count', 'N/A')} employees[/dim]")

        # --- Clearbit Enrichment (fallback if Apollo unavailable) ---
        if not enrichment and self.clearbit.available:
            console.print("[dim]  Enriching via Clearbit...[/dim]")
            if domain:
                enrichment = self.clearbit.enrich_by_domain(domain) or {}
            if not enrichment:
                enrichment = self.clearbit.enrich_by_name(company_name) or {}

        if not raw_signals and not merged_news:
            console.print(
                f"[yellow]  Warning: No data found for '{company_name}'. "
                "Try adding BRAVE_API_KEY or NEWS_API_KEY.[/yellow]"
            )

        console.print(
            f"[green]  Research complete:[/green] "
            f"{len(merged_news)} news items, "
            f"hiring={jobs_signal['signal']}, "
            f"funding={funding_signal['last_round']}"
        )

        return {
            "company_name": company_name,
            "news": merged_news,
            "jobs_signal": jobs_signal,
            "funding": funding_signal,
            "reviews_signal": reviews_signal,
            "enrichment": enrichment,
            "raw_signals": raw_signals,
            "historical_month": historical_month,
        }

    def _run_historical_search(
        self, company_name: str, historical_month: str
    ) -> list[dict]:
        """
        Run date-filtered searches for a specific historical month.

        Args:
            company_name: Company to search for.
            historical_month: Month in "YYYY-MM" format (e.g. "2026-01").

        Returns:
            List of result dicts from historical searches.
        """
        try:
            year, month = historical_month.split("-")
            after_date = f"{year}-{month}-01"

            # Calculate last day of month
            from datetime import datetime
            month_int = int(month)
            year_int = int(year)
            if month_int == 12:
                next_month = f"{year_int + 1}-01-01"
            else:
                next_month = f"{year_int}-{month_int + 1:02d}-01"
            before_date = next_month
        except (ValueError, IndexError):
            console.print(f"[yellow]  Invalid historical_month format: {historical_month}, skipping[/yellow]")
            return []

        # Use registry's date-filtered search
        results = self.registry.search_with_date(
            f'"{company_name}"',
            after_date=after_date,
            before_date=before_date,
        )
        return results
