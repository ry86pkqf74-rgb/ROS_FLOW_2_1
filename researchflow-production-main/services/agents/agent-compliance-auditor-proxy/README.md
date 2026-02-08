# Compliance Auditor Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Compliance Auditor Agent.

## Architecture

```
Orchestrator → agent-compliance-auditor-proxy:8000 → LangSmith Cloud API
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
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `300` (5 minutes for audits)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-compliance-auditor`
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
docker build -t agent-compliance-auditor-proxy:latest .
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
    "task_type": "COMPLIANCE_AUDIT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "log_source": "google_sheets",
      "log_data": "spreadsheet_id_here",
      "frameworks": ["HIPAA", "GDPR", "EU AI Act"],
      "include_code_scan": false
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-compliance-auditor-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-compliance-auditor-proxy": "http://agent-compliance-auditor-proxy:8000"
}
```

## Input Schema

```json
{
  "task_type": "COMPLIANCE_AUDIT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "log_source": "string (required) - 'google_sheets' or 'direct'",
    "log_data": "string (required) - spreadsheet ID or raw log text",
    "frameworks": "array (optional) - regulatory frameworks to audit against",
    "include_code_scan": "boolean (optional, default: false) - run codebase scanner",
    "repository": "string (optional) - GitHub repo in owner/repo format",
    "tracker_spreadsheet_id": "string (optional) - existing remediation tracker"
  }
}
```

## Output Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "executive_summary": {
      "total_events_scanned": "number",
      "findings_by_severity": {},
      "top_risk_areas": []
    },
    "scan_results": [],
    "audit_findings": [],
    "remediation_plan": [],
    "remediation_tracker_status": {},
    "regulatory_updates": [],
    "audit_trail_metadata": {},
    "generated_artifacts": {
      "audit_report_url": "string (Google Doc)",
      "tracker_url": "string (Google Sheets)",
      "github_issues": []
    },
    "langsmith_run_id": "string"
  }
}
```

## Failure Modes

1. **503 on /health/ready** - `LANGSMITH_API_KEY` not set or LangSmith API unreachable
2. **HTTP 4xx from LangSmith** - Invalid API key or agent ID
3. **Timeout** - Increase `LANGSMITH_TIMEOUT_SECONDS` for large audits
4. **Empty outputs** - Check LangSmith agent configuration and input schema

## Related Documentation

- **Agent Config:** `services/agents/agent-compliance-auditor/`
- **Wiring Guide:** `docs/agents/agent-compliance-auditor-proxy/wiring.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
