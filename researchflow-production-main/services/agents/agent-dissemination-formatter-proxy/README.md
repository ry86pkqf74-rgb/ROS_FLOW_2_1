# Dissemination Formatter Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Dissemination Formatter Agent.

## Architecture

```
Orchestrator → agent-dissemination-formatter-proxy:8000 → LangSmith Cloud API
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
- `LANGSMITH_API_KEY` - LangSmith API key (format: `<your-langsmith-api-key>`)
- `LANGSMITH_AGENT_ID` - Assistant ID from LangSmith (format: UUID)

**Optional:**
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `240` (4 minutes for formatting)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-dissemination-formatter`
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
docker build -t agent-dissemination-formatter-proxy:latest .
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
    "task_type": "DISSEMINATION_FORMATTING",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "manuscript_text": "# Introduction\nThis is a test manuscript...",
      "target_journal": "Nature",
      "output_format": "text",
      "citation_style": "numbered",
      "include_cover_letter": true,
      "verify_references": true
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-dissemination-formatter-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-dissemination-formatter": "http://agent-dissemination-formatter-proxy:8000"
}
```

## Input Schema

```json
{
  "task_type": "DISSEMINATION_FORMATTING",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "manuscript_text": "string (required) or Google Doc ID",
    "target_journal": "string (required)",
    "output_format": "string (required) - 'latex', 'google_doc', 'text'",
    "citation_style": "string (optional) - override default for journal",
    "include_cover_letter": "boolean (optional, default: true)",
    "verify_references": "boolean (optional, default: true)"
  }
}
```

## Output Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "formatted_manuscript": "string or Google Doc link",
    "validation_report": {
      "compliance_checks": [],
      "issues": [],
      "warnings": []
    },
    "reference_verification_report": {
      "total_references": "number",
      "verified": "number",
      "issues": []
    },
    "cover_letter": "string or Google Doc link (optional)",
    "submission_email_draft": "string (optional)",
    "google_doc_url": "string (optional)",
    "langsmith_run_id": "string"
  }
}
```

## Failure Modes

1. **503 on /health/ready** - `LANGSMITH_API_KEY` not set or LangSmith API unreachable
2. **HTTP 4xx from LangSmith** - Invalid API key or agent ID
3. **Timeout** - Increase `LANGSMITH_TIMEOUT_SECONDS` for complex formatting tasks
4. **Empty outputs** - Check LangSmith agent configuration and input schema

## Related Documentation

- **Agent Config:** `services/agents/agent-dissemination-formatter/`
- **Wiring Guide:** `docs/agents/dissemination-formatter/wiring.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
