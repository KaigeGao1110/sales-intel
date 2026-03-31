# Scout API Deployment Guide

## Prerequisites

1. Google Cloud SDK installed (`gcloud`)
2. Docker installed (for local testing)
3. GCP project with Cloud Run API enabled
4. Container Registry enabled in your project

## Local Development

```bash
cd scout
pip install -r requirements.txt
uvicorn scout.api:app --reload --port 8080
```

API docs available at: http://localhost:8080/docs

## Deploy to Cloud Run

### Option 1: Using Cloud Build (recommended)

```bash
# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Deploy (from project root)
gcloud builds submit --config=cloudbuild.yaml --substitutions=_SCOUT_DATA_BUCKET=your-bucket-name
```

### Option 2: Manual Docker deploy

```bash
# Build
docker build -t gcr.io/PROJECT_ID/scout-api:latest -f scout/Dockerfile .

# Push
docker push gcr.io/PROJECT_ID/scout-api:latest

# Deploy to Cloud Run
gcloud run deploy scout-api \
    --image gcr.io/PROJECT_ID/scout-api:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT` | HTTP port (default: 8080) | No |
| `SCOUT_DATA_BUCKET` | GCS bucket for companies.json sync | No |
| `GCP_PROJECT` | GCP project ID for Pub/Sub | No |
| `PUBSUB_TOPIC` | Pub/Sub topic for monitor triggers | No |
| `OPENAI_API_KEY` | For AI-powered brief generation | No |
| `ANTHROPIC_API_KEY` | Alternative for brief generation | No |
| `BRAVE_API_KEY` | For web search | No |
| `NEWS_API_KEY` | For news search | No |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/companies` | List all monitored companies |
| `POST` | `/companies` | Add a company to monitoring |
| `DELETE` | `/companies/{id}` | Remove a company |
| `POST` | `/companies/{id}/research` | Trigger on-demand research |
| `GET` | `/companies/{id}/alerts` | Get alerts for a company |

## Example API Usage

```bash
# Add a company
curl -X POST http://localhost:8080/companies \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "domain": "acme.com", "alert_email": "you@example.com"}'

# List companies
curl http://localhost:8080/companies

# Trigger research
curl -X POST http://localhost:8080/companies/COMPANY_ID/research

# Get alerts
curl http://localhost:8080/companies/COMPANY_ID/alerts

# Delete a company
curl -X DELETE http://localhost:8080/companies/COMPANY_ID
```

## Data Storage

The API uses the existing storage layer:
- `scout/data/companies.json` - Company records
- `scout/data/alerts_log.json` - Alert history
- `scout/data/snapshots/` - Research snapshots

For production, set `SCOUT_DATA_BUCKET` to enable GCS sync.

## IAM & Permissions

The Cloud Run service needs these roles:
- `roles/storage.objectViewer` (if using GCS sync)
- `roles/pubsub.publisher` (for Pub/Sub triggers)
