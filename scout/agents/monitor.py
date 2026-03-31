"""Monitor Agent (Level 1) - daily checks and change detection via Level 2 Watchers."""

from rich.console import Console

from agents.research import ResearchAgent
from agents.alert import AlertAgent
from agents.scoring import LeadScoringAgent
from agents.watchers import news as news_watcher
from agents.watchers import jobs as jobs_watcher
from agents.watchers import funding as funding_watcher
from agents.pipeline_watcher import PipelineWatcher
from storage import companies as company_store
from storage import snapshots as snapshot_store
from storage import scores as score_store

console = Console()


def _run_watchers(company_name: str, previous_snapshot: dict) -> dict:
    """Run all Level 2 watchers and aggregate results into a changes dict.

    Args:
        company_name: Name of the company.
        previous_snapshot: Previous research snapshot.

    Returns:
        Aggregated changes dict compatible with AlertAgent.evaluate_and_alert().
    """
    watchers = [
        ("NewsWatcher", news_watcher),
        ("JobsWatcher", jobs_watcher),
        ("FundingWatcher", funding_watcher),
    ]

    results = []
    for watcher_name, watcher in watchers:
        console.print(f"[dim]    Running {watcher_name}...[/dim]", end="")
        result = watcher.run(company_name, previous_snapshot)
        console.print(f"[dim] score={result['score']} — {result['details']}[/dim]")
        results.append(result)

    news_result = results[0]
    jobs_result = results[1]
    funding_result = results[2]

    changes: dict = {
        "layoffs_detected": jobs_result.get("layoffs_detected", False),
        "new_funding": funding_result.get("new_funding", False),
        "funding_details": funding_result.get("funding_details", ""),
        "rating_drop": previous_snapshot.get("_rating_drop", 0.0),
        "sentiment_shifted": news_result.get("sentiment_shifted", False),
        "new_news_count": news_result.get("new_news_count", 0),
    }

    total_score = sum(r["score"] for r in results)
    console.print(
        f"[dim]    Watcher total score: {total_score} "
        f"(news={results[0]['score']}, "
        f"jobs={results[1]['score']}, "
        f"funding={results[2]['score']})[/dim]"
    )

    return changes


class MonitorAgent:
    """Runs periodic checks on monitored companies and triggers alerts."""

    def __init__(self) -> None:
        self.research_agent = ResearchAgent()
        self.alert_agent = AlertAgent()
        self.pipeline_watcher = PipelineWatcher()

    def check_company(self, company: dict) -> dict:
        """Run a full check for a single company.

        Args:
            company: Company dict from companies.json.

        Returns:
            Result dict with keys: company_name, snapshot_path,
            changes, alert_triggered.
        """
        name = company["name"]
        cid = company["id"]
        domain = company.get("domain", "")

        console.print(f"\n[bold]Checking:[/bold] {name}")

        # Research
        research_data = self.research_agent.research(name, domain=domain)

        # Save snapshot
        path = snapshot_store.save(cid, name, research_data)
        console.print(f"[dim]  Snapshot saved: {path}[/dim]")

        # Compare to previous via Level 2 watchers
        previous = snapshot_store.get_previous(cid)
        alert = None
        changes: dict = {}

        if previous:
            changes = _run_watchers(name, previous)
            changes["research_data"] = research_data  # for PipelineWatcher
            console.print(
                f"[dim]  Changes: layoffs={changes.get('layoffs_detected')}, "
                f"new_funding={changes.get('new_funding')}, "
                f"new_news={changes.get('new_news_count')}[/dim]"
            )
            alert = self.alert_agent.evaluate_and_alert(company, changes)
        else:
            console.print("[dim]  First snapshot — no comparison available[/dim]")

        # Pipeline health check (if tracked as opportunity)
        pipeline_result = self.pipeline_watcher.run(name, changes if previous else {"research_data": research_data})
        if pipeline_result.get("alert_triggered"):
            console.print(
                f"[bold red]  ⚠️ Pipeline alert: {name} health dropped "
                f"{pipeline_result.get('score_delta', 0)} pts "
                f"({pipeline_result.get('previous_score')} → {pipeline_result.get('score')})[/bold red]"
            )

        # Score the company
        scorer = LeadScoringAgent()
        score_result = scorer.score(name, research_data)
        score_store.save(
            company_id=cid,
            company_name=name,
            score=score_result["score"],
            grade=score_result["grade"],
            reasons=score_result["reasons"],
            recommended_action=score_result["recommended_action"],
        )
        console.print(f"[dim]  Score: [Score {score_result['score']}/{score_result['grade']}] {name}[/dim]")

        # Update last_checked
        company_store.update_last_checked(cid)

        return {
            "company_name": name,
            "snapshot_path": str(path),
            "changes": changes,
            "alert_triggered": alert is not None,
            "pipeline_alert": pipeline_result.get("alert_triggered", False),
            "pipeline_score": pipeline_result.get("score", 0),
        }

    def check_by_name(self, name: str) -> dict:
        """Check a single company by name.

        Args:
            name: Company name.

        Returns:
            Result dict or error dict if company not found.
        """
        company = company_store.get_by_name(name)
        if not company:
            console.print(f"[red]Company not found: '{name}'[/red]")
            return {"error": f"Company '{name}' not in monitoring list"}
        return self.check_company(company)

    def run_all(self) -> list[dict]:
        """Run checks for all active monitored companies.

        Returns:
            List of result dicts for each company checked.
        """
        active = company_store.get_active()
        if not active:
            console.print(
                "[yellow]No active companies in monitoring list.[/yellow]\n"
                "Add companies with: python main.py monitor add 'Company Name'"
            )
            return []

        console.print(
            f"\n[bold blue]Monitor Run[/bold blue] — checking {len(active)} companies"
        )
        results = []
        for company in active:
            try:
                result = self.check_company(company)
                results.append(result)
            except Exception as e:
                console.print(
                    f"[red]Error checking {company['name']}: {e}[/red]"
                )
                results.append({"company_name": company["name"], "error": str(e)})

        alerts_fired = sum(1 for r in results if r.get("alert_triggered"))
        console.print(
            f"\n[bold green]Monitor run complete[/bold green] — "
            f"{len(results)} checked, {alerts_fired} alert(s) fired"
        )
        return results
