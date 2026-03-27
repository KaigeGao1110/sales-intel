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

import os
import sys
from pathlib import Path

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
def scout(company_name: str, domain: str, email: str, no_monitor: bool) -> None:
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
def monitor_run() -> None:
    """Run monitoring checks for all active companies."""
    from agents.monitor import MonitorAgent

    agent = MonitorAgent()
    agent.run_all()


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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
