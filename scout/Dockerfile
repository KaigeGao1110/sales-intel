# Cloud Run deployment for Scout API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY scout/requirements.txt /app/scout/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/scout/requirements.txt

# Copy application code
COPY scout/ /app/scout/
COPY .env* /app/ 2>/dev/null || true

# Create non-root user for Cloud Run
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env var, default 8080)
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "scout.api:app", "--host", "0.0.0.0", "--port", "8080"]
