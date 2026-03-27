"""Research Agent (Level 1) - orchestrates sub-researchers for company intelligence."""

from rich.console import Console

from services.clearbit import ClearbitService
from agents.researchers import news as news_researcher
from agents.researchers import web as web_researcher
from agents.researchers import reviews as reviews_researcher

console = Console()


class ResearchAgent:
    """Fetches and aggregates company intelligence via Level 2 sub-researchers."""

    def __init__(self) -> None:
        self.clearbit = ClearbitService()

    def research(self, company_name: str, domain: str = "") -> dict:
        """Run full research pipeline for a company.

        Args:
            company_name: Name of the company to research.
            domain: Optional domain for Clearbit enrichment.

        Returns:
            Structured dict with keys:
                news, jobs_signal, funding, reviews_signal,
                enrichment, raw_signals.
        """
        console.print(f"\n[bold cyan]Researching:[/bold cyan] {company_name}")

        # --- Level 2 Sub-Researchers ---
        console.print("[dim]  Running NewsResearcher...[/dim]")
        news_data = news_researcher.run(company_name)

        console.print("[dim]  Running WebResearcher...[/dim]")
        web_data = web_researcher.run(company_name)

        console.print("[dim]  Running ReviewResearcher...[/dim]")
        reviews_data = reviews_researcher.run(company_name)

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

        # --- Clearbit Enrichment (optional) ---
        enrichment: dict = {}
        if self.clearbit.available:
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
        }
