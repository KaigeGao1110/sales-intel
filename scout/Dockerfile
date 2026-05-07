# Scout Slack Bot — Cloud Run deployment
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run needs PORT; we serve a health endpoint alongside the bot
ENV PORT=8080
EXPOSE 8080

CMD ["python", "run_slack.py"]
