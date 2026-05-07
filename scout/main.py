#!/usr/bin/env python3
"""Scout CLI - Sales Intelligence Agent System.

Usage:
    python main.py scout "Company Name"
    python main.py monitor add "Company Name" --email you@email.com
    python main.py monitor list
    python main.py monitor run
    python main.py monitor check "Company Name"
    python main.py alert test --email you@email.com
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli() -> None:
    """Scout - Sales Intelligence Agent System."""
    pass


# ---------------------------------------------------------------------------
# scout command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
@click.option("--domain", default="", help="Company domain for enrichment (e.g. acme.com)")
@click.option("--email", default="", help="Email for monitoring alerts")
@click.option("--no-monitor", is_flag=True, default=False,
              help="Don't add company to monitoring list")
@click.option("--month", default="", help="Historical month to research (e.g. 2026-01)")
def scout(company_name: str, domain: str, email: str, no_monitor: bool, month: str) -> None:
    """Research a company and generate a sales brief.

    COMPANY_NAME: Name of the company to scout (e.g. "Acme Corp")
    """
    from agents.scout import ScoutAgent

    agent = ScoutAgent()
    brief = agent.scout(
        company_name=company_name,
        domain=domain,
        alert_email=email,
        add_to_monitoring=not no_monitor,
        historical_month=month or None,
    )
    agent.print_brief(brief)


# ---------------------------------------------------------------------------
# monitor commands
# ---------------------------------------------------------------------------

@cli.group()
def monitor() -> None:
    """Manage company monitoring."""
    pass


@monitor.command("add")
@click.argument("company_name")
@click.option("--email", default="", help="Email for alerts")
@click.option("--domain", default="", help="Company domain")
def monitor_add(company_name: str, email: str, domain: str) -> None:
    """Add a company to the monitoring list."""
    from storage import companies as company_store

    existing = company_store.get_by_name(company_name)
    if existing:
        console.print(
            f"[yellow]'{company_name}' is already being monitored "
            f"(id={existing['id']})[/yellow]"
        )
        return

    channels = ["email"] if email else ["console"]
    company = company_store.add(
        name=company_name,
        domain=domain,
        alert_email=email,
        alert_channels=channels,
    )
    console.print(
        f"[green]Added '{company_name}' to monitoring[/green]\n"
        f"  ID: {company['id']}\n"
        f"  Alert channels: {', '.join(company['alert_channels'])}"
    )
    if not email:
        console.print(
            "[dim]  Tip: use --email to receive email alerts[/dim]"
        )


@monitor.command("list")
def monitor_list() -> None:
    """List all monitored companies."""
    from storage import companies as company_store

    companies = company_store.get_all()
    if not companies:
        console.print("[yellow]No companies in monitoring list.[/yellow]")
        console.print("Add one with: python main.py monitor add 'Company Name'")
        return

    table = Table(title="Monitored Companies", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Added")
    table.add_column("Last Checked")
    table.add_column("Alert Email")

    for c in companies:
        status_color = "green" if c.get("status") == "active" else "yellow"
        table.add_row(
            c.get("name", ""),
            f"[{status_color}]{c.get('status', 'unknown')}[/{status_color}]",
            c.get("added_date", ""),
            c.get("last_checked", "Never") or "Never",
            c.get("alert_email", "") or "[dim]none[/dim]",
        )
    console.print(table)


@monitor.command("run")
@click.option("--company-id", "company_id", default=None, help="UUID of a specific company to check")
def monitor_run(company_id: Optional[str]) -> None:
    """Run monitoring checks for all active companies, or a single company via --company-id."""
    from agents.monitor import MonitorAgent
    from storage import companies as company_store

    agent = MonitorAgent()

    if company_id:
        company = company_store.get_by_id(company_id)
        if not company:
            console.print(f"[red]Company not found with id='{company_id}'[/red]")
            return
        result = agent.check_company(company)
        console.print(
            f"\n[green]Check complete[/green] for {result['company_name']}\n"
            f"  Snapshot: {result.get('snapshot_path', 'N/A')}\n"
            f"  Alert triggered: {result.get('alert_triggered', False)}"
        )
    else:
        agent.run_all()


def _enqueue_cloud_task(queue_name: str, task_name: str, payload: dict) -> bool:
    """Enqueue a single task to Google Cloud Tasks.

    Returns True if enqueued successfully, False otherwise.
    """
    try:
        from google.cloud import tasks_v2
    except ImportError:
        console.print("[yellow]google-cloud-tasks not installed. Install with: pip install google-cloud-tasks[/yellow]")
        return False

    project = os.getenv("CLOUD_TASKS_PROJECT", "")
    location = os.getenv("CLOUD_TASKS_LOCATION", "")
    handler_url = os.getenv("MONITOR_HANDLER_URL", "")

    if not all([project, location, handler_url]):
        console.print(
            "[yellow]Cloud Tasks env vars not fully configured. Set:\n"
            "  CLOUD_TASKS_PROJECT  (e.g. my-gcp-project)\n"
            "  CLOUD_TASKS_LOCATION (e.g. us-central1)\n"
            "  MONITOR_HANDLER_URL  (e.g. https://my-app.run.app/monitor/handle)[/yellow]"
        )
        return False

    try:
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(project, location, queue_name)
        task_v2 = tasks_v2.Task()
        task_v2.http_request.http_method = tasks_v2.HttpMethod.POST
        task_v2.http_request.url = handler_url
        task_v2.http_request.headers["Content-Type"] = "application/json"
        task_v2.http_request.body = json.dumps(payload).encode()
        client.create_task(request={"parent": parent, "task": task_v2})
        return True
    except Exception as e:
        console.print(f"[red]Cloud Tasks enqueue failed: {e}[/red]")
        return False


@monitor.command("enqueue")
@click.option("--queue", "queue_name", default="scout-monitor", help="Cloud Tasks queue name")
def monitor_enqueue(queue_name: str) -> None:
    """Enqueue all active companies to Cloud Tasks for processing.

    Queries all active companies (optionally filtered by account_id) and creates
    a Cloud Tasks task for each one targeting the MONITOR_HANDLER_URL.
    """
    from agents.monitor import MonitorAgent
    from storage import companies as company_store

    active = company_store.get_active()
    if not active:
        console.print("[yellow]No active companies to enqueue.[/yellow]")
        return

    console.print(f"[bold]Enqueuing {len(active)} active company(ies) to Cloud Tasks queue '{queue_name}'...[/bold]")

    enqueued = 0
    failed = 0
    for company in active:
        task_name = f"monitor-{company['id']}"
        payload = {"company_id": company["id"], "action": "check"}
        if _enqueue_cloud_task(queue_name, task_name, payload):
            enqueued += 1
            console.print(f"  [green]+[/green] {company['name']} ({company['id']})")
        else:
            failed += 1
            console.print(f"  [red]-[/red] {company['name']} ({company['id']}) — FAILED")

    console.print(f"\n[bold]Enqueue complete:[/bold] {enqueued} enqueued, {failed} failed")


@monitor.command("check")
@click.argument("company_name")
def monitor_check(company_name: str) -> None:
    """Run an immediate check for a specific company.

    COMPANY_NAME: Name of the company to check.
    """
    from agents.monitor import MonitorAgent

    agent = MonitorAgent()
    result = agent.check_by_name(company_name)
    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
    else:
        console.print(
            f"\n[green]Check complete[/green] for {result['company_name']}\n"
            f"  Snapshot: {result.get('snapshot_path', 'N/A')}\n"
            f"  Alert triggered: {result.get('alert_triggered', False)}"
        )


@monitor.command("pause")
@click.argument("company_name")
def monitor_pause(company_name: str) -> None:
    """Pause monitoring for a company."""
    from storage import companies as company_store

    company = company_store.get_by_name(company_name)
    if not company:
        console.print(f"[red]Company not found: '{company_name}'[/red]")
        return
    company_store.set_status(company["id"], "paused")
    console.print(f"[yellow]Paused monitoring for '{company_name}'[/yellow]")


@monitor.command("resume")
@click.argument("company_name")
def monitor_resume(company_name: str) -> None:
    """Resume monitoring for a paused company."""
    from storage import companies as company_store

    company = company_store.get_by_name(company_name)
    if not company:
        console.print(f"[red]Company not found: '{company_name}'[/red]")
        return
    company_store.set_status(company["id"], "active")
    console.print(f"[green]Resumed monitoring for '{company_name}'[/green]")


@monitor.command("remove")
@click.argument("company_name")
def monitor_remove(company_name: str) -> None:
    """Remove a company from monitoring."""
    from storage import companies as company_store

    company = company_store.get_by_name(company_name)
    if not company:
        console.print(f"[red]Company not found: '{company_name}'[/red]")
        return
    company_store.remove(company["id"])
    console.print(f"[yellow]Removed '{company_name}' from monitoring[/yellow]")


# ---------------------------------------------------------------------------
# alert commands
# ---------------------------------------------------------------------------

@cli.group()
def alert() -> None:
    """Alert management commands."""
    pass


@alert.command("test")
@click.option("--email", required=True, help="Email address to send test alert to")
def alert_test(email: str) -> None:
    """Send a test alert to verify notification configuration."""
    from agents.alert import AlertAgent

    agent = AlertAgent()
    agent.send_test_alert(email)


# ---------------------------------------------------------------------------
# score commands
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
def score(company_name: str) -> None:
    """Score a single company against ICP and intent signals.

    COMPANY_NAME: Name of the company to score.
    """
    from agents.scoring import LeadScoringAgent
    from agents.research import ResearchAgent
    from storage import companies as company_store

    company = company_store.get_by_name(company_name)
    if not company:
        console.print(f"[red]Company not found: '{company_name}'[/red]")
        return

    # Run fresh research
    agent = ResearchAgent()
    research_data = agent.research(company_name, domain=company.get("domain", ""))

    # Score
    scorer = LeadScoringAgent()
    result = scorer.score(company_name, research_data)

    # Save score
    from storage import scores as score_store
    score_store.save(
        company_id=company["id"],
        company_name=company_name,
        score=result["score"],
        grade=result["grade"],
        reasons=result["reasons"],
        recommended_action=result["recommended_action"],
    )

    # Print breakdown
    console.print(f"\n[bold cyan]Score for {company_name}[/bold cyan]")
    console.print(f"  Total Score: [bold]{result['score']}[/bold] — Grade [bold]{result['grade']}[/bold]\n")
    console.print("[bold]Breakdown:[/bold]")
    for reason in result["reasons"]:
        console.print(f"  • {reason}")
    console.print(f"\n[bold green]Recommended Action:[/bold green] {result['recommended_action']}")


@cli.command()
def rank() -> None:
    """Score and rank all monitored companies."""
    from agents.scoring import LeadScoringAgent
    from storage import scores as score_store
    from storage import companies as company_store

    companies = company_store.get_active()
    if not companies:
        console.print("[yellow]No active companies to rank.[/yellow]")
        return

    # Run scoring
    scorer = LeadScoringAgent()
    scorer.print_rank_table()

    # Save all scores
    results = scorer.rank_all()
    for r in results:
        company = company_store.get_by_name(r["company_name"])
        if company:
            score_store.save(
                company_id=company["id"],
                company_name=r["company_name"],
                score=r["score"],
                grade=r["grade"],
                reasons=r["reasons"],
                recommended_action=r["recommended_action"],
            )


# ---------------------------------------------------------------------------
# alert commands
# ---------------------------------------------------------------------------

@alert.command("list")
def alert_list() -> None:
    """List recent alerts."""
    from storage import alerts as alert_store

    all_alerts = alert_store.get_all()
    if not all_alerts:
        console.print("[yellow]No alerts logged yet.[/yellow]")
        return

    table = Table(title="Alert Log", show_header=True, header_style="bold red")
    table.add_column("Company")
    table.add_column("Date")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Score")
    table.add_column("Notified")

    for a in reversed(all_alerts[-20:]):  # show last 20
        sev = a.get("severity", "")
        sev_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(sev, "")
        table.add_row(
            a.get("company_name", ""),
            a.get("alert_date", "")[:10],
            a.get("type", ""),
            f"[{sev_color}]{sev}[/{sev_color}]" if sev_color else sev,
            str(a.get("score", 0)),
            "[green]yes[/green]" if a.get("notified") else "[red]no[/red]",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# outreach command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
@click.option("--domain", default="", help="Company domain for contact lookup")
@click.option("--variants", default=2, help="Number of variants to generate (default 2)")
def outreach(company_name: str, domain: str, variants: int) -> None:
    """Generate personalized outreach for a company.

    COMPANY_NAME: Name of the company to generate outreach for.
    """
    from agents.scout import ScoutAgent
    from agents.research import ResearchAgent
    from agents.outreach import OutreachAgent, print_outreach_result
    from agents.alert import _lookup_contacts
    from storage import companies as company_store
    from storage import snapshots
    from storage import outreach as outreach_store

    # Step 1: Look up company
    company = company_store.get_by_name(company_name)
    if company:
        console.print(f"[dim]  Found '{company_name}' in monitoring (id={company['id']})[/dim]")
        domain = domain or company.get("domain", "")
    else:
        console.print(f"[yellow]  '{company_name}' not in monitoring — will generate fresh research[/yellow]")
        scout = ScoutAgent()
        brief = scout.scout(company_name=company_name, domain=domain, add_to_monitoring=False)
        console.print("\n[bold cyan]Brief generated:[/bold cyan]")
        scout.print_brief(brief)
        # Reload company after scout
        company = company_store.get_by_name(company_name)

    # Step 2: Load research data from latest snapshot
    research_data = None
    if company:
        snapshot = snapshots.get_latest(company["id"])
        if snapshot:
            research_data = {
                "company_name": company_name,
                "news": snapshot.get("news", []),
                "jobs_signal": snapshot.get("jobs", {}),
                "funding": snapshot.get("funding", {}),
                "reviews_signal": snapshot.get("reviews", {}),
                "raw_signals": snapshot.get("raw_signals", []),
                "enrichment": {},
            }
            console.print(f"[dim]  Loaded latest snapshot from {snapshot.get('check_date', 'unknown')}[/dim]")
        else:
            console.print("[yellow]  No snapshot found — running fresh research[/yellow]")
            research_agent = ResearchAgent()
            research_data = research_agent.research(company_name, domain=domain)

    if not research_data:
        console.print("[red]  Could not obtain research data for outreach generation[/red]")
        return

    # Step 3: Look up contacts
    contacts = _lookup_contacts(company_name, domain=domain)
    if contacts:
        console.print(f"[dim]  Found {len(contacts)} contact(s) via Hunter.io[/dim]")
    else:
        console.print("[yellow]  No contacts found via Hunter.io[/yellow]")

    # Step 4: Generate outreach
    console.print("\n[bold cyan]Generating outreach...[/bold cyan]")
    agent = OutreachAgent()
    brief_text = ""
    result = agent.generate(
        company_name=company_name,
        brief=brief_text,
        research_data=research_data,
        contacts=contacts,
        variants=variants,
    )

    # Step 5: Print results
    print_outreach_result(result, company_name, contacts)

    # Step 6: Log to outreach.json
    company_id = company["id"] if company else "unknown"
    outreach_store.log(
        company_id=company_id,
        company_name=company_name,
        contacts=contacts,
        variants=result,
    )
    console.print(f"\n[dim]  Logged to ~/.scout/outreach.json[/dim]")


# ---------------------------------------------------------------------------
# warm-intro command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
@click.option("--domain", default="", help="Company domain")
@click.option("--role", default="decision maker", help="Target role to find")
def warm_intro(company_name: str, domain: str, role: str) -> None:
    """Find warm introduction paths to key contacts at a company.

    COMPANY_NAME: Name of the target company.
    """
    from agents.warm_intro import find_intro_paths, print_intro_result

    with console.status(f"[bold cyan]Finding warm intro paths for {company_name}...[/bold cyan]"):
        result = find_intro_paths(
            company_name=company_name,
            target_role=role,
            domain=domain,
        )
    print_intro_result(result)


# ---------------------------------------------------------------------------
# prep command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
@click.option("--attendees", default="", help="Comma-separated attendee emails")
@click.option("--time", "meeting_time", default=None, help="Meeting time (ISO format)")
def prep(company_name: str, attendees: str, meeting_time: str) -> None:
    """Generate a meeting prep brief for a company.

    COMPANY_NAME: Name of the company for the meeting.
    """
    from agents.prep import MeetingPrepAgent

    attendee_emails = [e.strip() for e in attendees.split(",") if e.strip()] if attendees else []
    if not attendee_emails:
        console.print("[yellow]No attendees specified. Use --attendees to add emails.[/yellow]")

    agent = MeetingPrepAgent()
    with console.status(f"[bold cyan]Generating prep brief for {company_name}...[/bold cyan]"):
        prep_data = agent.generate_prep(company_name, attendee_emails, meeting_time)

    if "error" in prep_data:
        console.print(f"[red]Error: {prep_data['error']}[/red]")
        return

    content = prep_data.get("prep_content", {})

    console.print(f"\n[bold cyan]Meeting Prep: {company_name}[/bold cyan]")
    if meeting_time:
        console.print(f"  Time: {meeting_time}")
    if attendee_emails:
        console.print(f"  Attendees: {', '.join(attendee_emails)}")

    console.print(f"\n[bold]Context:[/bold]")
    console.print(f"  {content.get('context', 'N/A')}")

    if content.get("pain_points"):
        console.print(f"\n[bold red]Pain Points:[/bold red]")
        for pp in content["pain_points"]:
            console.print(f"  • {pp}")

    if content.get("questions"):
        console.print(f"\n[bold green]Opening Questions:[/bold green]")
        for q in content["questions"]:
            console.print(f"  • {q}")

    if content.get("topics_to_avoid"):
        console.print(f"\n[bold yellow]Topics to Avoid:[/bold yellow]")
        for t in content["topics_to_avoid"]:
            console.print(f"  • {t}")

    if content.get("key_facts"):
        console.print(f"\n[bold]Key Facts:[/bold]")
        for f in content["key_facts"]:
            console.print(f"  • {f}")

    console.print(f"\n[dim]Prep ID: {prep_data.get('meeting_id', 'N/A')}[/dim]")


@cli.command()
@click.option("--hours", default=24, help="Hours ahead to check (default 24)")
@click.option("--auto", is_flag=True, default=False, help="Auto-generate prep for all meetings")
def prep_calendar(hours: int, auto: bool) -> None:
    """Pull upcoming calendar meetings and optionally auto-prep them."""
    from integrations.calendar import get_upcoming_prep_candidates
    from agents.prep import MeetingPrepAgent

    with console.status(f"[bold cyan]Fetching calendar events (next {hours}h)...[/bold cyan]"):
        candidates = get_upcoming_prep_candidates(hours)

    if not candidates:
        console.print("[yellow]No upcoming meetings found in calendar.[/yellow]")
        return

    console.print(f"[green]Found {len(candidates)} upcoming meeting(s):[/green]\n")

    table = Table(title="Upcoming Meetings", show_header=True, header_style="bold cyan")
    table.add_column("Company", style="bold")
    table.add_column("Title")
    table.add_column("Time")
    table.add_column("Attendees")

    for c in candidates:
        table.add_row(
            c["company_name"],
            c["title"],
            c["meeting_time"][:16] if c["meeting_time"] else "—",
            str(len(c["attendee_emails"])),
        )
    console.print(table)

    if not auto:
        console.print("\n[dim]Use --auto to auto-generate prep briefs for all meetings[/dim]")
        return

    # Auto-prep all meetings
    console.print(f"\n[bold cyan]Generating prep briefs...[/bold cyan]\n")
    agent = MeetingPrepAgent()

    for c in candidates:
        console.print(f"[bold]→ {c['company_name']}[/bold] ({c['title']})")
        try:
            prep_data = agent.generate_prep(
                c["company_name"],
                c["attendee_emails"],
                c["meeting_time"],
            )
            if "error" in prep_data:
                console.print(f"  [red]Error: {prep_data['error']}[/red]")
                continue

            content = prep_data.get("prep_content", {})
            if content.get("pain_points"):
                console.print(f"  Pain points: {', '.join(content['pain_points'][:3])}")
            if content.get("questions"):
                console.print(f"  Top question: {content['questions'][0]}")
            console.print(f"  [dim]Prep ID: {prep_data.get('meeting_id', 'N/A')}[/dim]\n")
        except Exception as e:
            console.print(f"  [red]Failed: {e}[/red]\n")


# ---------------------------------------------------------------------------
# pipeline commands
# ---------------------------------------------------------------------------

@cli.group()
def pipeline() -> None:
    """Pipeline intelligence and deal tracking."""
    pass


@pipeline.command("track")
@click.argument("company_name")
@click.option("--stage", default="discovery", help="Pipeline stage",
              type=click.Choice(["discovery", "qualification", "proposal",
                                 "negotiation", "poc", "closed_won", "closed_lost"]))
@click.option("--close", "expected_close", default=None, help="Expected close date (YYYY-MM-DD)")
@click.option("--champion", default=None, help="Champion contact email")
def pipeline_track(company_name: str, stage: str, expected_close: str, champion: str) -> None:
    """Start tracking a company as a pipeline opportunity."""
    from storage import pipeline as pipeline_store

    opp = pipeline_store.track_opportunity(
        company_name=company_name,
        stage=stage,
        expected_close=expected_close,
        champion_contact=champion,
    )
    console.print(
        f"[green]Tracking '{company_name}' as opportunity[/green]\n"
        f"  ID: {opp['opportunity_id']}\n"
        f"  Stage: {opp['stage']}\n"
        f"  Health: {opp['health_score']}"
    )


@pipeline.command("untrack")
@click.argument("company_name")
def pipeline_untrack(company_name: str) -> None:
    """Stop tracking a pipeline opportunity."""
    from storage import pipeline as pipeline_store

    if pipeline_store.untrack(company_name):
        console.print(f"[yellow]Stopped tracking '{company_name}'[/yellow]")
    else:
        console.print(f"[red]Opportunity not found: '{company_name}'[/red]")


@pipeline.command("list")
def pipeline_list() -> None:
    """List all tracked pipeline opportunities with health scores."""
    from agents.pipeline import PipelineIntelligenceAgent

    agent = PipelineIntelligenceAgent()
    summary = agent.get_pipeline_summary()

    if summary["total_count"] == 0:
        console.print("[yellow]No pipeline opportunities tracked.[/yellow]")
        console.print("Add one with: python main.py pipeline track 'Company Name' --stage proposal")
        return

    table = Table(title="Pipeline", show_header=True, header_style="bold cyan")
    table.add_column("Company", style="bold")
    table.add_column("Stage")
    table.add_column("Health")
    table.add_column("Expected Close")
    table.add_column("Champion")

    from storage import pipeline as pipeline_store
    opps = pipeline_store.get_all_opportunities()
    for opp in opps:
        if opp.get("status") != "active":
            continue
        health = opp.get("health_score", 0)
        health_color = "green" if health >= 70 else "yellow" if health >= 40 else "red"
        table.add_row(
            opp["company_name"],
            opp.get("stage", "—"),
            f"[{health_color}]{health}/100[/{health_color}]",
            opp.get("expected_close") or "—",
            opp.get("champion_contact") or "—",
        )

    console.print(table)
    if summary["unhealthy_count"] > 0:
        console.print(
            f"\n[red]⚠️ {summary['unhealthy_count']} deal(s) below health threshold[/red]"
        )


@pipeline.command("assess")
@click.argument("company_name")
def pipeline_assess(company_name: str) -> None:
    """Assess deal health for a tracked opportunity."""
    from agents.pipeline import PipelineIntelligenceAgent

    agent = PipelineIntelligenceAgent()
    result = agent.assess_deal_health(company_name)

    if "error" in result.get("breakdown", {}):
        console.print(f"[red]{result['breakdown']['error']}[/red]")
        return

    breakdown = result["breakdown"]
    console.print(f"\n[bold cyan]Deal Health: {company_name}[/bold cyan]")
    console.print(f"  Overall Score: [bold]{result['health_score']}/100[/bold]")
    console.print(f"  Stage: {result['stage']}")
    console.print(f"\n[bold]Breakdown:[/bold]")
    console.print(f"  • Stage: {breakdown['stage']}/20")
    console.print(f"  • Champion Stability: {breakdown['champion_stability']}/20")
    console.print(f"  • No Danger Signals: {breakdown['no_danger_signals']}/40")
    console.print(f"  • Momentum: {breakdown['momentum']}/20")

    signals = result.get("signals", {})
    if signals.get("danger_signals"):
        console.print(f"\n[bold red]⚠️ Danger Signals:[/bold red]")
        for s in signals["danger_signals"]:
            console.print(f"  • {s}")
    if signals.get("momentum_signals"):
        console.print(f"\n[bold green]Positive Signals:[/bold green]")
        for s in signals["momentum_signals"]:
            console.print(f"  • {s}")


# ---------------------------------------------------------------------------
# warm-intro command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("company_name")
@click.option("--domain", default="", help="Company domain (e.g. acme.com)")
@click.option("--role", default="decision maker", help="Target role to find")
def warm_intro(company_name: str, domain: str, role: str) -> None:
    """Find warm introduction paths to key contacts at a company.

    COMPANY_NAME: Name of the target company.
    """
    from agents.warm_intro import find_intro_paths, print_intro_result

    with console.status(f"[bold cyan]Finding warm intro paths for {company_name}...[/bold cyan]"):
        result = find_intro_paths(
            company_name=company_name,
            target_role=role,
            domain=domain,
        )

    print_intro_result(result)


# ---------------------------------------------------------------------------
# slack commands
# ---------------------------------------------------------------------------

@cli.group()
def slack() -> None:
    """Slack bot management commands."""
    pass


@slack.command("start")
def slack_start() -> None:
    """Start the Scout Slack bot (runs run_slack.py)."""
    import subprocess
    import os
    from pathlib import Path

    env_file = Path(__file__).parent / ".env.slack"
    env_args = ["--env-file", str(env_file)] if env_file.exists() else []

    # Check required env vars
    if not os.getenv("SLACK_BOT_TOKEN"):
        # Try loading .env.slack
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)

    if not os.getenv("SLACK_BOT_TOKEN"):
        console.print("[red]SLACK_BOT_TOKEN not set. See .env.slack.example[/red]")
        return
    if not os.getenv("SLACK_SIGNING_SECRET"):
        console.print("[red]SLACK_SIGNING_SECRET not set. See .env.slack.example[/red]")
        return
    if not os.getenv("SLACK_APP_TOKEN"):
        console.print("[red]SLACK_APP_TOKEN not set. See .env.slack.example[/red]")
        return

    console.print("[green]Starting Scout Slack Bot...[/green]")
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "run_slack.py")] + env_args,
        check=False,
    )


@slack.command("alert-test")
def slack_alert_test() -> None:
    """Send a test alert to the configured Slack channel."""
    try:
        from slack_bot import alerts
        success = alerts.send_test_alert()
        if success:
            console.print("[green]Test alert sent successfully![/green]")
        else:
            console.print("[red]Failed to send test alert. Check your SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN + SLACK_CHANNEL_ID[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
