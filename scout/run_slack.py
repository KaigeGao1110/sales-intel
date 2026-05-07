#!/usr/bin/env python3
"""Start the Scout Slack Bot.

Usage:
    python run_slack.py

Requires environment variables (see .env.slack.example):
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_SIGNING_SECRET=...
    SLACK_WEBHOOK_URL=...     # optional, for incoming webhooks/alerts
    SLACK_CHANNEL_ID=...       # default channel for alerts
"""

import os
import sys
import logging
from pathlib import Path
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load .env.slack for local development
env_path = Path(__file__).parent / ".env.slack"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def start_health_server():
    """Simple HTTP health check server for Cloud Run."""
    class HealthHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()
        def log_message(self, format, *args):
            pass  # suppress logs

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    """Start the Slack bot using Socket Mode."""
    # Start health check server in background thread
    Thread(target=start_health_server, daemon=True, name="health-server").start()
    from slack_bot.app import app
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    if not slack_app_token:
        logger.error(
            "SLACK_APP_TOKEN is not set. "
            "Enable Socket Mode in your Slack app settings and set this token."
        )
        sys.exit(1)

    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        logger.error("SLACK_BOT_TOKEN is not set. See .env.slack.example")
        sys.exit(1)

    handler = SocketModeHandler(app, slack_app_token)
    port = int(os.getenv("SLACK_BOT_PORT", "3000"))

    logger.info(f"Starting Scout Slack Bot...")
    handler.start()


if __name__ == "__main__":
    main()
