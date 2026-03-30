# Scout Slack Bot — Setup Guide

This guide walks you through setting up the Scout Slack Bot from scratch.
No technical background required — just follow the steps.

---

## Step 1: Create a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**
2. Choose **From scratch**
3. Give it a name (e.g., "Scout Bot") and pick your workspace
4. Click **Create App**

---

## Step 2: Enable Socket Mode

Socket Mode lets the bot run on your machine without a public server.

1. In the left sidebar, click **Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. It will ask you to create an App-Level Token — name it anything (e.g., "scout-socket")
4. Click **Generate** and copy the token (starts with `xapp-`)
5. Save this as `SLACK_APP_TOKEN` in your `.env.slack` file

---

## Step 3: Add Slash Commands

1. In the left sidebar, click **Slash Commands**
2. Click **Create New Command**
3. Fill in each command:

### `/scout-rank`
- **Command:** `/scout-rank`
- **Request URL:** `https://your-server.com/slack/events` (not needed for Socket Mode — leave blank or use placeholder)
- **Short description:** View ranked lead pipeline
- **Usage hint:** `[optional: none]`

### `/scout-add`
- **Command:** `/scout-add`
- **Short description:** Add a company to monitoring
- **Usage hint:** `[company name]`

### `/scout-score`
- **Command:** `/scout-score`
- **Short description:** Show score breakdown for a company
- **Usage hint:** `[company name]`

### `/scout-outreach`
- **Command:** `/scout-outreach`
- **Short description:** Generate personalized outreach content
- **Usage hint:** `[company name]`

### `/scout-monitor`
- **Command:** `/scout-monitor`
- **Short description:** Run monitoring checks on all companies
- **Usage hint:** `[optional: none]`

### `/scout-help`
- **Command:** `/scout-help`
- **Short description:** Show available commands
- **Usage hint:** `[optional: none]`

4. Click **Save**

---

## Step 4: Get Your Bot Token

1. In the left sidebar, click **OAuth & Permissions**
2. Scroll down to **Bot Token Scopes** and add these scopes:
   - `chat:write`
   - `commands`
3. Click **Install to Workspace** (or **Reinstall to Workspace** if already installed)
4. Copy the **Bot Token** (starts with `xoxb-`)
5. Save this as `SLACK_BOT_TOKEN` in your `.env.slack` file

---

## Step 5: Get Your Signing Secret

1. In the left sidebar, click **Basic Information**
2. Scroll to **App Credentials**
3. Copy the **Signing Secret**
4. Save this as `SLACK_SIGNING_SECRET` in your `.env.slack` file

---

## Step 6: Set Up Environment Variables

Copy the example file and fill in your values:

```bash
cd /path/to/scout
cp .env.slack.example .env.slack
```

Edit `.env.slack` and paste in:
- `SLACK_BOT_TOKEN=xoxb-...` (from Step 4)
- `SLACK_APP_TOKEN=xapp-...` (from Step 2)
- `SLACK_SIGNING_SECRET=...` (from Step 5)
- `SLACK_CHANNEL_ID=C0XXXXXX` (see below)
- `SLACK_BOT_PORT=3000` (default)

### Getting Your Slack Channel ID

The bot will post alerts to a specific channel. To get the channel ID:

1. In Slack, click the **channel name** at the top
2. Click **Details** (three dots menu → **Details**)
3. Scroll to the bottom — you'll see the Channel ID (e.g., `C0123456789`)
4. Paste this as `SLACK_CHANNEL_ID` in your `.env.slack`

---

## Step 7: Install Python Dependencies

```bash
cd /path/to/scout
pip install -r requirements.slack.txt
```

---

## Step 8: Start the Bot

```bash
python main.py slack start
```

You should see:
```
Starting Scout Slack Bot on port 3000...
```

The bot is now running. Open Slack and try:
- Type `/scout-help` in any channel
- Type `/scout-rank` to see your lead pipeline

---

## Step 9: Test Your Alerts (Optional)

To verify the Slack integration is working:

```bash
python main.py slack alert-test
```

You should receive a test alert in your configured channel.

---

## Troubleshooting

### "Command not found" in Slack
- Make sure the app is installed in your workspace (OAuth & Permissions → Install to Workspace)
- Make sure you added all slash commands (Step 3)

### Bot not responding
- Check the terminal running `python main.py slack start` for errors
- Verify your `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, and `SLACK_APP_TOKEN` are all set correctly
- Make sure Socket Mode is enabled (Step 2)

### "Not posted to channel" errors
- Make sure `SLACK_CHANNEL_ID` is set to a valid channel ID (not the channel name)
- The bot needs `chat:write` permission (Step 4)

---

## Available Slash Commands

| Command | Description |
|---|---|
| `/scout-rank` | View all monitored companies ranked by score |
| `/scout-add [name]` | Add a company to monitoring and run initial research |
| `/scout-score [name]` | See score breakdown and ICP match for a company |
| `/scout-outreach [name]` | Generate personalized email and LinkedIn outreach |
| `/scout-monitor` | Run monitoring checks on all active companies |
| `/scout-help` | Show all available commands |

---

## Alert Integration

When MonitorAgent detects a high-significance event (score >= 15), it can automatically push an alert to Slack.

To enable this, call `push_alert()` from `slack_bot/alerts.py` in your monitoring pipeline:

```python
from slack_bot.alerts import push_alert

push_alert(
    company_name="Acme Corp",
    score=15,
    severity="high",
    signal="Recent Series B funding closed",
    action="Reach out this week — new capital just closed.",
)
```

The alert will be sent to the channel specified by `SLACK_CHANNEL_ID`.
