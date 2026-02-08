# Performance Optimizer Agent - LangSmith Proxy

FastAPI proxy service that adapts ResearchFlow's agent contract to LangSmith cloud-hosted Performance Optimizer agent.

## Architecture

```
ResearchFlow Orchestrator → This Proxy → LangSmith API → Performance Optimizer Agent
```

## Endpoints

### `GET /health`
Liveness check. Returns `{"status": "ok"}`.

### `GET /health/ready`
Readiness check. Validates:
- `LANGSMITH_API_KEY` is configured
- LangSmith API is reachable

### `POST /agents/run/sync`
Synchronous agent execution. Accepts ResearchFlow `AgentRunRequest`, returns `AgentRunResponse`.

**Request:**
```json
{
  "task_type": "PERFORMANCE_OPTIMIZATION",
  "request_id": "perf-001",
  "mode": "DEMO",
  "inputs": {
    "metrics_spreadsheet_id": "abc123...",
    "analysis_focus": "latency",
    "time_period": "last_7_days"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "request_id": "perf-001",
  "outputs": {
    "performance_report": "...",
    "optimization_recommendations": [...],
    "cost_analysis": {...},
    "bottleneck_identification": [...],
    "alert_summary": {...},
    "google_doc_url": "https://docs.google.com/...",
    "langsmith_run_id": "..."
  }
}
```

### `POST /agents/run/stream`
Streaming execution via Server-Sent Events (SSE).

## Environment Variables

### Required
- `LANGSMITH_API_KEY` - LangSmith API key (<your-langsmith-api-key>)
- `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` - Agent UUID from LangSmith

### Optional
- `LANGSMITH_API_URL` - LangSmith API base URL (default: https://api.smith.langchain.com)
- `LANGSMITH_TIMEOUT_SECONDS` - Request timeout (default: 300)
- `LOG_LEVEL` - Logging level (default: INFO)
- `GOOGLE_SHEETS_API_KEY` - For metrics reading (optional)
- `GOOGLE_DOCS_API_KEY` - For report writing (optional)

## Usage

### Local Development
```bash
cd services/agents/agent-performance-optimizer-proxy
pip install -r requirements.txt
export LANGSMITH_API_KEY=<your-langsmith-api-key>
export LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID=<uuid>
uvicorn app.main:app --reload
```

### Docker
```bash
docker compose build agent-performance-optimizer-proxy
docker compose up -d agent-performance-optimizer-proxy
```

### Test
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Integration

This proxy is registered in the orchestrator's `AGENT_ENDPOINTS_JSON` as:
```json
{
  "agent-performance-optimizer": "http://agent-performance-optimizer-proxy:8000"
}
```

Router task type: `PERFORMANCE_OPTIMIZATION`

## Notes

- **Mandatory service:** All agents in ResearchFlow are mandatory (preflight validation enforces this)
- **No offline mode:** Requires LangSmith API access (no stubs/fixtures)
- **PHI-safe:** No PHI in logs or error messages
- **Timeout:** Default 5 minutes (performance analysis can be slow)
- **Google integration:** Optional; disabled by default (requires API keys)

## Troubleshooting

### 503 Service Unavailable
- Check `LANGSMITH_API_KEY` is set
- Check `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` is set
- Verify LangSmith API is reachable: `curl https://api.smith.langchain.com/info`

### Timeout errors
- Increase `LANGSMITH_TIMEOUT_SECONDS` (default 300)
- Check LangSmith agent logs for sub-worker failures

### Google integration errors
- Set `GOOGLE_SHEETS_API_KEY` and `GOOGLE_DOCS_API_KEY` if using spreadsheet input/output
- Otherwise, pass `metrics_data` directly in request

## See Also

- Main agent: `services/agents/agent-performance-optimizer/`
- Router registration: `services/orchestrator/src/routes/ai-router.ts`
- Wiring guide: `docs/agents/performance-optimizer/wiring.md`
