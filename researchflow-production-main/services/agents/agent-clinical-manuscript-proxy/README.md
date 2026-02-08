# Clinical Manuscript Writer Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Clinical Manuscript Writer Agent.

## Architecture

```
Orchestrator → agent-clinical-manuscript-proxy:8000 → LangSmith Cloud API
                     (this service)
```

This proxy provides a consistent HTTP interface for the LangSmith-hosted agent, making it behave like other containerized ResearchFlow agents.

## Endpoints

- `GET /health` - Health check
- `GET /health/ready` - Readiness check (validates LangSmith connectivity)
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Streaming execution (SSE)

## Environment Variables

**Required:**
- `LANGSMITH_API_KEY` - LangSmith API key (format: `lsv2_pt_...`)
- `LANGSMITH_AGENT_ID` - Assistant ID from LangSmith (format: UUID)

**Optional:**
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `300` (5 minutes for manuscript generation)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-clinical-manuscript`
- `LANGCHAIN_TRACING_V2` - Default: `false`

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_AGENT_ID="your-assistant-id"

# Run locally
uvicorn app.main:app --reload --port 8000
```

## Docker Build

```bash
docker build -t agent-clinical-manuscript-proxy:latest .
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
    "task_type": "CLINICAL_MANUSCRIPT_WRITE",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "study_data": {
        "title": "Efficacy of Drug X in Disease Y",
        "study_type": "RCT",
        "results": "..."
      },
      "evidence_log": [],
      "protocol_data": {}
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-clinical-manuscript-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000"
}
```

## Failure Modes

1. **503 on /health/ready** - `LANGSMITH_API_KEY` not set or LangSmith API unreachable
2. **HTTP 4xx from LangSmith** - Invalid API key or agent ID
3. **Timeout** - Increase `LANGSMITH_TIMEOUT_SECONDS` for complex manuscripts
4. **Empty outputs** - Check LangSmith agent configuration and input schema

## Monitoring

Logs include:
- Request ID for traceability
- LangSmith run ID (in response metadata)
- Error details for failed requests

Use LangSmith UI to debug agent execution: https://smith.langchain.com/

## Related Documentation

- LangSmith Agent Config: `services/agents/agent-clinical-manuscript/`
- Agent Inventory: `AGENT_INVENTORY.md`
- Deployment Guide: `docs/deployment/hetzner-fullstack.md`
