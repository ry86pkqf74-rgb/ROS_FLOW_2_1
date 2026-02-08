# Clinical Section Drafter Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Clinical Section Drafter Agent (Results & Discussion sections).

## Architecture

```
Orchestrator → agent-section-drafter-proxy:8000 → LangSmith Cloud API
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
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `180` (3 minutes for section drafting)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-section-drafter`
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
docker build -t agent-section-drafter-proxy:latest .
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
    "task_type": "CLINICAL_SECTION_DRAFT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "section_type": "Results",
      "study_summary": "RCT of 100 patients...",
      "results_data": {
        "primary_outcome": "HR=0.72 (95% CI 0.58-0.89, p=0.003)"
      },
      "evidence_chunks": [],
      "key_hypotheses": ["Drug X reduces mortality"],
      "few_shot_examples": []
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-section-drafter-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-clinical-section-drafter": "http://agent-section-drafter-proxy:8000"
}
```

## Failure Modes

1. **503 on /health/ready** - `LANGSMITH_API_KEY` not set or LangSmith API unreachable
2. **HTTP 4xx from LangSmith** - Invalid API key or agent ID
3. **Timeout** - Increase `LANGSMITH_TIMEOUT_SECONDS` for complex sections
4. **Empty outputs** - Check LangSmith agent configuration and input schema

## Monitoring

Logs include:
- Request ID for traceability
- LangSmith run ID (in response metadata)
- Error details for failed requests

Use LangSmith UI to debug agent execution: https://smith.langchain.com/

## Related Documentation

- LangSmith Agent Config: `agents/Clinical_Study_Section_Drafter/`
- Agent Inventory: `AGENT_INVENTORY.md`
- Wiring Documentation: `CLINICAL_SECTION_DRAFTER_WIRING_COMPLETE.md`
