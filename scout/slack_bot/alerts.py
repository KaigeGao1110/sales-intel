"""Alert pusher for Scout Slack Bot.

Sends formatted Block Kit alert messages to the configured Slack channel
when MonitorAgent detects high-significance events.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")


def _get_slack_client():
    """Get a Slack WebClient, returning None if token is not configured."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        return None
    try:
        from slack_sdk import WebClient
        return WebClient(token=token)
    except ImportError:
        return None


def _build_alert_blocks(
    company_name: str,
    score: int,
    severity: str,
    signal: str,
    action: str,
) -> list[dict]:
    """Build Slack Block Kit message for an alert."""
    severity_color = {"high": "#ff0000", "medium": "#ffaa00", "low": "#00aa00"}.get(
        severity.lower(), "#888888"
    )
    severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        severity.lower(), "⚪"
    )

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{severity_emoji} Scout Alert: {company_name}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{severity.capitalize()}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Signal Score:*\n{score}",
                },
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Signal:*\n{signal}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action:*\n{action}",
            },
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Sent by Scout Sales Intelligence",
                },
            ],
        },
    ]

    return blocks


def push_alert(
    company_name: str,
    score: int,
    severity: str,
    signal: str,
    action: str,
) -> bool:
    """Send an alert message to the configured Slack channel.

    Uses SLACK_WEBHOOK_URL if set, otherwise falls back to the Slack Web API
    via the bot token.

    Args:
        company_name: Name of the company that triggered the alert.
        score: Signal significance score.
        severity: 'high', 'medium', or 'low'.
        signal: Brief description of the top signal.
        action: Recommended next step.

    Returns:
        True if the alert was sent successfully, False otherwise.
    """
    blocks = _build_alert_blocks(company_name, score, severity, signal, action)

    # Try webhook first
    if SLACK_WEBHOOK_URL:
        return _send_via_webhook(blocks)

    # Fall back to Web API
    client = _get_slack_client()
    if client:
        return _send_via_client(client, blocks)

    logger.warning("No Slack webhook URL or bot token configured — alert not sent")
    return False


def _send_via_webhook(blocks: list[dict]) -> bool:
    """Send message via incoming webhook."""
    try:
        import json
        import urllib.request

        payload = {"blocks": blocks}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Failed to send Slack webhook alert: {e}")
        return False


def _send_via_client(client, blocks: list[dict]) -> bool:
    """Send message via Slack Web API using bot token."""
    try:
        channel_id = SLACK_CHANNEL_ID
        if not channel_id:
            # Try to find the bot's DM channel
            logger.warning("SLACK_CHANNEL_ID not set — cannot send via client")
            return False

        response = client.chat_postMessage(channel=channel_id, blocks=blocks, text="Scout Alert")
        return response["ok"]
    except Exception as e:
        logger.error(f"Failed to send Slack client alert: {e}")
        return False


def send_test_alert() -> bool:
    """Send a test alert to verify Slack configuration.

    Returns:
        True if sent successfully, False otherwise.
    """
    return push_alert(
        company_name="Acme Corp",
        score=15,
        severity="high",
        signal="Recent Series B funding closed",
        action="Reach out this week — new capital just closed. Act fast before competitors do.",
    )
