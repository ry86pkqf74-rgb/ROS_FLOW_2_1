FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY services/agents/agent-stage2-lit/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/agents/agent-stage2-lit/app /app/app
COPY services/agents/agent-stage2-lit/agent /app/agent

# Pull in existing worker agent logic (Milestone 1 shortcut)
COPY services/worker/agents /app/worker_agents

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
