# Artifact Auditor Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Artifact Auditor Agent.

## Architecture

```
Orchestrator → agent-artifact-auditor-proxy:8000 → LangSmith Cloud API
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
- `LANGCHAIN_PROJECT` - Default: `researchflow-artifact-auditor`
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
docker build -t agent-artifact-auditor-proxy:latest .
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
    "task_type": "ARTIFACT_AUDIT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "artifact_source": "github",
      "github_repository": "owner/repo",
      "github_file_path": "manuscripts/draft.md",
      "reporting_standard": "CONSORT"
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-artifact-auditor-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-artifact-auditor-proxy": "http://agent-artifact-auditor-proxy:8000"
}
```

## Input Schema

```json
{
  "task_type": "ARTIFACT_AUDIT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "artifact_source": "string (required) - 'github', 'google_docs', 'url', or 'direct'",
    "artifact_location": "string - location identifier (repo/path, doc ID, URL)",
    "reporting_standard": "string - 'CONSORT', 'PRISMA', 'STROBE', etc.",
    "standard_version": "string (optional) - version or extension",
    "custom_guidelines": "string (optional) - additional guidelines",
    "github_repository": "string (optional) - GitHub owner/repo",
    "github_file_path": "string (optional) - path to artifact in repo",
    "google_doc_id": "string (optional) - Google Docs document ID",
    "artifact_content": "string (optional) - direct artifact text"
  }
}
```

## Output Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "audit_summary": {
      "artifact_name": "string",
      "standard": "string",
      "compliance_score": "string"
    },
    "compliance_score": "string",
    "critical_issues": [],
    "major_issues": [],
    "minor_issues": [],
    "equity_flags": [],
    "audit_report_url": "string (Google Docs URL)",
    "audit_log_entry": {},
    "langsmith_run_id": "string"
  }
}
```

## Workflow

1. **Parse Artifact**: Retrieve artifact from GitHub, Google Docs, URL, or direct input
2. **Determine Standard**: Identify applicable reporting standard (CONSORT, PRISMA, STROBE, etc.)
3. **Retrieve Checklist**: Guideline_Researcher worker fetches structured checklist
4. **Audit**: Compliance_Auditor worker performs item-by-item audit
5. **Report**: Generate chat summary and Google Docs audit report
6. **Track**: Cross_Artifact_Tracker logs findings for trend analysis

## Sub-Workers

- **Guideline_Researcher**: Retrieves authoritative checklists for reporting standards
- **Compliance_Auditor**: Performs deep item-by-item compliance audits
- **Cross_Artifact_Tracker**: Analyzes trends across multiple audit findings

## Supported Standards

- CONSORT (RCT trials)
- PRISMA (Systematic reviews)
- STROBE (Observational studies)
- SPIRIT (Trial protocols)
- CARE (Case reports)
- ARRIVE (Animal research)
- TIDieR (Intervention descriptions)
- CHEERS (Health economics)
- MOOSE (Meta-analysis of observational studies)
