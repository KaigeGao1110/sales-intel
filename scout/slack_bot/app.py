"""Slack Bolt Application for Scout Sales Intelligence Bot.

Registers all slash commands and event listeners.
"""

import os
import sys
import logging
from pathlib import Path

# Allow imports from parent package
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env file for local development
env_path = Path(__file__).parent.parent / ".env.slack"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_bot import commands, alerts

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
)


# ---------------------------------------------------------------------------
# Slash command registration
# ---------------------------------------------------------------------------

@app.command("/scout-rank")
def scout_rank(ack, respond):
    """Respond with ranked table of all monitored companies."""
    ack()
    result = commands.handle_rank()
    respond(**result)


@app.command("/scout-add")
def scout_add(ack, respond, command):
    """Add a company to monitoring and run initial scout."""
    ack()
    company_name = command.get("text", "").strip()
    result = commands.handle_add(company_name)
    respond(**result)


@app.command("/scout-score")
def scout_score(ack, respond, command):
    """Show score breakdown for a company."""
    ack()
    company_name = command.get("text", "").strip()
    result = commands.handle_score(company_name)
    respond(**result)


@app.command("/scout-outreach")
def scout_outreach(ack, respond, command):
    """Generate personalized outreach content for a company."""
    ack()
    company_name = command.get("text", "").strip()
    result = commands.handle_outreach(company_name)
    respond(**result)


@app.command("/scout-monitor")
def scout_monitor(ack, respond):
    """Run monitoring checks on all active companies."""
    ack()
    result = commands.handle_monitor()
    respond(**result)


@app.command("/scout-help")
def scout_help(ack, respond):
    """Show available commands."""
    ack()
    result = commands.handle_help()
    respond(**result)


@app.command("/scout-prep")
def scout_prep(ack, respond, command):
    """Generate meeting prep brief for a company."""
    ack()
    text = command.get("text", "").strip()
    parts = text.split(maxsplit=1)
    company_name = parts[0] if parts else ""
    emails = parts[1] if len(parts) > 1 else ""
    result = commands.handle_prep(company_name, emails)
    respond(**result)


@app.command("/scout-track")
def scout_track(ack, respond, command):
    """Track a company as a pipeline deal."""
    ack()
    text = command.get("text", "").strip()
    parts = text.split(maxsplit=1)
    company_name = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    result = commands.handle_track(company_name, args)
    respond(**result)


@app.command("/scout-pipeline")
def scout_pipeline(ack, respond):
    """View all pipeline deals with health scores."""
    ack()
    result = commands.handle_pipeline()
    respond(**result)


@app.command("/scout-warm-intro")
def scout_warm_intro(ack, respond, command):
    """Find warm intro paths to contacts at a company."""
    ack()
    company_name = command.get("text", "").strip()
    result = commands.handle_warm_intro(company_name)
    respond(**result)


# ---------------------------------------------------------------------------
# OAuth / installation (optional — for "Add to Slack" flow)
# ---------------------------------------------------------------------------

@app.event("app_mention")
def handle_app_mention(ack, event, say):
    """Handle mentions of the bot — respond with help."""
    ack()
    result = commands.handle_help()
    say(**result)


# ---------------------------------------------------------------------------
# Alert push helper — called by MonitorAgent after alert evaluation
# ---------------------------------------------------------------------------

def register_alert_push():
    """Integration point: MonitorAgent calls this after alert evaluation.

    Import this from slack_bot.app in your monitor.py to push alerts to Slack:

        from slack_bot.app import push_slack_alert
        push_slack_alert(company_name, score, "high", signal, action)

    Or call alerts.push_alert() directly from agents/monitor.py.
    """
    pass


# Expose push_alert for external callers (e.g. monitor.py)
def push_slack_alert(
    company_name: str,
    score: int,
    severity: str,
    signal: str,
    action: str,
) -> bool:
    """Push an alert to Slack. Convenience wrapper around alerts.push_alert()."""
    return alerts.push_alert(
        company_name=company_name,
        score=score,
        severity=severity,
        signal=signal,
        action=action,
    )
