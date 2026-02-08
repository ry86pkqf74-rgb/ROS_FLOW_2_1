# Results Interpretation Agent - LangSmith Proxy

**Canonical Reference**: See [`docs/agents/results-interpretation/wiring.md`](../../../docs/agents/results-interpretation/wiring.md) for complete deployment and routing documentation.

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Results Interpretation Agent.

## Architecture

```
Orchestrator → agent-results-interpretation-proxy:8000 → LangSmith Cloud API
                     (this service)
```

## Endpoints

- `GET /health` - Health check
- `GET /health/ready` - Readiness check (validates LangSmith connectivity)
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Streaming execution (SSE)

## Environment Variables

**Required:**
- `LANGSMITH_API_KEY` - LangSmith API key (format: `<your-langsmith-api-key>`)
- `LANGSMITH_AGENT_ID` - Assistant ID from LangSmith (format: UUID)

**Optional:**
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `180` (3 minutes)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-results-interpretation`
- `LANGCHAIN_TRACING_V2` - Default: `false`

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LANGSMITH_API_KEY="<your-langsmith-api-key>"
export LANGSMITH_AGENT_ID="your-assistant-id"

# Run locally
uvicorn app.main:app --reload --port 8000
```

## Docker Build

```bash
docker build -t agent-results-interpretation-proxy:latest .
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Test agent execution
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "RCT N=200, HR=0.72 (95% CI 0.58-0.89, p=0.003)",
      "study_metadata": {
        "study_type": "RCT",
        "domain": "clinical"
      }
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-results-interpretation-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-results-interpretation": "http://agent-results-interpretation-proxy:8000"
}
```

## Failure Modes

1. **503 on /health/ready** - `LANGSMITH_API_KEY` not set or LangSmith API unreachable
2. **HTTP 4xx from LangSmith** - Invalid API key or agent ID
3. **Timeout** - Increase `LANGSMITH_TIMEOUT_SECONDS` for complex analyses
4. **Empty outputs** - Check LangSmith agent configuration and input schema

## Monitoring

Logs include:
- Request ID for traceability
- LangSmith run ID (in response metadata)
- Error details for failed requests

Use LangSmith UI to debug agent execution: https://smith.langchain.com/
