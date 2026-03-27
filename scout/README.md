# Scout - Sales Intelligence Agent System

Scout monitors companies and generates AI-powered sales briefs to help your team understand prospects before outreach.

## Quick Start

```bash
cd scout
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Research a company and get a brief
python main.py scout "Acme Corp"

# Add a company to monitoring with email alerts
python main.py monitor add "Acme Corp" --email you@yourcompany.com

# Run all monitoring checks now
python main.py monitor run

# Test email alerts
python main.py alert test --email you@yourcompany.com
```

## CLI Commands

### `scout` — Research & Brief Generation

```bash
python main.py scout "Company Name"
python main.py scout "Company Name" --domain acme.com --email sales@co.com
python main.py scout "Company Name" --no-monitor   # brief only, don't add to monitoring
```

### `monitor` — Company Monitoring

```bash
python main.py monitor add "Company Name" --email you@email.com
python main.py monitor list                         # show all monitored companies
python main.py monitor run                          # run all checks
python main.py monitor check "Company Name"         # check one company now
python main.py monitor pause "Company Name"
python main.py monitor resume "Company Name"
python main.py monitor remove "Company Name"
```

### `alert` — Alert Management

```bash
python main.py alert test --email you@email.com     # send test alert
python main.py alert list                           # show recent alerts
```

## API Keys

Copy `.env.example` to `.env` and fill in the keys you have. Everything degrades gracefully if keys are missing:

| Key | Service | Effect if missing |
|-----|---------|-------------------|
| `BRAVE_API_KEY` | Brave Search | Web search skipped |
| `NEWS_API_KEY` | NewsAPI.org | News search skipped |
| `CLEARBIT_API_KEY` | Clearbit | Company enrichment skipped |
| `OPENAI_API_KEY` | OpenAI GPT | Rule-based brief used |
| `ANTHROPIC_API_KEY` | Claude | Rule-based brief used (OpenAI takes priority) |
| `ALERT_EMAIL` | Default email | Must set per-company |
| `SLACK_WEBHOOK_URL` | Slack | Slack alerts skipped |

Get free API keys at:
- Brave Search: https://brave.com/search/api/
- NewsAPI: https://newsapi.org/
- Clearbit: https://clearbit.com/

## Gmail API Setup (for email alerts)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the credentials JSON and run:

```bash
pip install google-auth-oauthlib
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/gmail.send'])
creds = flow.run_local_server(port=0)
with open('gmail_credentials.json', 'w') as f:
    f.write(creds.to_json())
"
```

5. Set `GMAIL_CREDENTIALS_FILE=gmail_credentials.json` in your `.env`

## Significance Scoring

Alerts fire when score ≥ 10:

| Signal | Points |
|--------|--------|
| Layoffs announced | +10 |
| New funding round | +8 |
| Rating drop > 0.3 stars | +7 |
| Sentiment shift (pos→neg) | +6 |
| News volume spike (>3 in 24h) | +4 |
| Minor news | +1 each |

## Cloud Run Deployment

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/scout

# Deploy as Cloud Run Job
gcloud run jobs replace cloudrun-job.yaml

# Create daily trigger
gcloud scheduler jobs create http scout-daily \
  --schedule="0 7 * * *" \
  --uri="https://...run.googleapis.com/.../jobs/scout-monitor:run" \
  --http-method=POST
```

## Project Structure

```
scout/
├── main.py              # CLI entry point
├── agents/
│   ├── scout.py         # Main orchestration agent
│   ├── research.py      # Research subagent
│   ├── monitor.py       # Daily monitoring subagent
│   └── alert.py         # Alert evaluation & dispatch
├── services/
│   ├── brave_search.py  # Brave Search API wrapper
│   ├── news_api.py      # NewsAPI wrapper
│   └── clearbit.py      # Clearbit enrichment wrapper
├── storage/
│   ├── companies.py     # companies.json CRUD
│   ├── snapshots.py     # snapshot storage
│   └── alerts.py        # alert log CRUD
├── prompts/
│   └── brief_template.py # LLM prompt templates
└── data/
    ├── companies.json   # monitored companies
    ├── alerts_log.json  # alert history
    └── snapshots/       # daily snapshots per company
```

## Test Companies (MVP Testing)

```bash
python main.py scout "Notion"
python main.py scout "Figma"
python main.py scout "Stripe"
python main.py scout "OpenAI"
```
