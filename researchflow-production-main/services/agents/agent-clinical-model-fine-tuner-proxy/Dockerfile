# Clinical Model Fine-Tuner Agent - LangSmith Proxy
# Thin FastAPI adapter that proxies requests to LangSmith cloud-hosted agent

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (from service directory when building with context=.)
COPY services/agents/agent-clinical-model-fine-tuner-proxy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (from service directory when building with context=.)
COPY services/agents/agent-clinical-model-fine-tuner-proxy/app/ app/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
