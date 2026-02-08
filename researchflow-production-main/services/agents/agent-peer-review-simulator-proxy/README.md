# Peer Review Simulator Agent Proxy

**Type:** LangSmith Cloud Proxy  
**Agent:** agent-peer-review-simulator  
**Purpose:** Simulates rigorous journal peer reviews with multiple reviewer personas

---

## Overview

This FastAPI proxy service wraps the LangSmith cloud-hosted Peer Review Simulator agent, adapting it to the ResearchFlow agent contract. The agent simulates comprehensive peer reviews using multiple reviewer personas (methodologist, statistician, ethics reviewer, domain expert) with iterative critique-revise cycles.

## Endpoints

### Health Checks

- **`GET /health`** - Liveness check (container running)
- **`GET /health/ready`** - Readiness check (validates LangSmith connectivity)

### Agent Execution

- **`POST /agents/run/sync`** - Synchronous peer review simulation
- **`POST /agents/run/stream`** - Streaming peer review with SSE

## Request Schema

```json
{
  "task_type": "PEER_REVIEW_SIMULATION",
  "request_id": "req-123",
  "workflow_id": "wf-456",
  "user_id": "user-789",
  "mode": "DEMO",
  "inputs": {
    "manuscript": {
      "title": "Study Title",
      "abstract": "...",
      "introduction": "...",
      "methods": "...",
      "results": "...",
      "discussion": "...",
      "references": [...]
    },
    "personas": ["methodologist", "statistician", "ethics_reviewer", "domain_expert"],
    "study_type": "RCT",
    "enable_iteration": true,
    "max_cycles": 3
  }
}
```

## Response Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "peer_review_report": {
      "summary": "...",
      "critiques": [...],
      "severity_ratings": {...},
      "recommendations": [...]
    },
    "checklists": [
      {
        "guideline": "CONSORT",
        "items_addressed": [...],
        "items_missing": [...]
      }
    ],
    "response_letter": "...",
    "google_doc_url": "https://docs.google.com/...",
    "iterations": 2,
    "approved": true,
    "metadata": {...},
    "langsmith_run_id": "..."
  }
}
```

## Environment Variables

Required:
- `LANGSMITH_API_KEY` - LangSmith API key (starts with `lsv2_pt_`)
- `LANGSMITH_AGENT_ID` - LangSmith assistant UUID

Optional:
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: 600 (10 minutes)
- `LOG_LEVEL` - Default: `INFO`

## Local Development

```bash
cd services/agents/agent-peer-review-simulator-proxy

# Set environment variables
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_AGENT_ID="uuid-from-langsmith"

# Run locally
uvicorn app.main:app --reload

# Test health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Docker Build

```bash
docker build -t agent-peer-review-simulator-proxy .
docker run -p 8000:8000 \
  -e LANGSMITH_API_KEY="lsv2_pt_..." \
  -e LANGSMITH_AGENT_ID="uuid" \
  agent-peer-review-simulator-proxy
```

## Integration with ResearchFlow

### Docker Compose

```yaml
agent-peer-review-simulator-proxy:
  build:
    context: services/agents/agent-peer-review-simulator-proxy
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
    - LANGSMITH_AGENT_ID=${LANGSMITH_PEER_REVIEW_AGENT_ID}
    - LANGSMITH_TIMEOUT_SECONDS=600
  expose:
    - "8000"
  networks:
    - backend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Router Registration

In `ai-router.ts`:

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  PEER_REVIEW_SIMULATION: 'agent-peer-review-simulator',
  // ...
};
```

In `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-peer-review-simulator": "http://agent-peer-review-simulator-proxy:8000"
}
```

### Stage 13 Integration

```python
# services/worker/src/workflow_engine/stages/stage_13_internal_review.py
use_peer_review_sim = context.config.get("ENABLE_PEER_REVIEW_SIMULATOR", False)

if use_peer_review_sim:
    result = await self.call_agent_dispatch(
        task_type="PEER_REVIEW_SIMULATION",
        inputs={
            "manuscript": manuscript_payload,
            "personas": ["methodologist", "statistician"],
            "study_type": "RCT",
            "max_cycles": 2
        }
    )
```

## Testing

### Unit Tests

```bash
pytest tests/unit/test_peer_review_proxy.py
```

### Integration Tests (Mocked LangSmith)

```python
@pytest.mark.asyncio
async def test_proxy_with_mock_langsmith(mocker):
    mock_post = mocker.patch('httpx.AsyncClient.post')
    mock_post.return_value.json.return_value = {
        "output": {"peer_review_report": {...}}
    }
    
    response = await client.post("/agents/run/sync", json={...})
    assert response.status_code == 200
    assert response.json()["ok"] is True
```

### End-to-End (Real LangSmith)

```bash
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_AGENT_ID="uuid"
pytest tests/e2e/test_peer_review_e2e.py
```

## Monitoring

### Health Checks

```bash
# Liveness
curl http://agent-peer-review-simulator-proxy:8000/health

# Readiness (validates LangSmith connectivity)
curl http://agent-peer-review-simulator-proxy:8000/health/ready
```

### Logs

```bash
docker compose logs -f agent-peer-review-simulator-proxy

# Expected log entries:
# - "Received request: req-123 (task_type=PEER_REVIEW_SIMULATION)"
# - "Calling LangSmith agent uuid"
# - "LangSmith response received for req-123"
```

### LangSmith Dashboard

- **URL:** https://smith.langchain.com/
- Filter by `thread_id` (matches `request_id`)
- View sub-agent traces (Critique Worker, Readability Reviewer, etc.)
- Check tool calls and costs

## Troubleshooting

### 503 Service Unavailable

**Cause:** LANGSMITH_API_KEY not configured  
**Fix:** Set environment variable in `.env` or docker-compose.yml

### 503 Cannot Reach LangSmith

**Cause:** Network connectivity issue or LangSmith API down  
**Fix:** Check network, verify API key is valid, check LangSmith status page

### Timeout Errors

**Cause:** Peer review takes longer than timeout (default 10 minutes)  
**Fix:** Increase `LANGSMITH_TIMEOUT_SECONDS` or reduce `max_cycles`

### 400 Invalid Request

**Cause:** Missing required inputs (manuscript, personas)  
**Fix:** Ensure `inputs.manuscript` is provided with all sections

## Architecture

```
Orchestrator → AI Router → Agent Peer Review Simulator Proxy → LangSmith API
                                                                    ↓
                                                            Critique Worker
                                                            Readability Reviewer
                                                            Literature Checker
                                                            Checklist Auditor
                                                            Revision Worker
```

## Related Files

- **Agent Config:** `services/agents/agent-peer-review-simulator/`
- **Router:** `services/orchestrator/src/routes/ai-router.ts`
- **Stage 13:** `services/worker/src/workflow_engine/stages/stage_13_internal_review.py`
- **Wiring Docs:** `docs/agents/peer-review-simulator/wiring.md`

## References

- [LangSmith Proxy Architecture](../../../LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md)
- [Agent Integration Guide](../agent-peer-review-simulator/INTEGRATION_GUIDE.md)
- [Stage 13 Documentation](../../../docs/stages/stage_13_internal_review.md)
