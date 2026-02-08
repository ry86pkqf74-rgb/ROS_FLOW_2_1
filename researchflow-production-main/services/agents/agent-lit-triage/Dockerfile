FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY services/agents/agent-lit-triage/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/agents/agent-lit-triage/app /app/app
COPY services/agents/agent-lit-triage/agent /app/agent
COPY services/agents/agent-lit-triage/workers /app/workers
COPY services/agents/agent-lit-triage/langsmith_export /app/langsmith_export

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
