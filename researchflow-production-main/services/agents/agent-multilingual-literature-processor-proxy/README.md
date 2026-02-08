# Multilingual Literature Processor Agent - LangSmith Proxy

## Overview

This service is a **thin FastAPI proxy** that adapts ResearchFlow's agent contract to LangSmith cloud-hosted agents. It provides a standard ResearchFlow agent interface (`/agents/run/sync`, `/agents/run/stream`, `/health`) while proxying execution to a LangSmith cloud agent.

## Architecture

```
ResearchFlow Orchestrator
         ↓
    [This Proxy Service] (FastAPI, port 8000)
         ↓
    LangSmith Cloud API
         ↓
   Multilingual Literature Processor Agent (cloud-hosted)
```

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness probe - always returns 200 OK |
| `/health/ready` | GET | Readiness probe - validates LangSmith API connectivity and configuration |
| `/agents/run/sync` | POST | Synchronous agent execution |
| `/agents/run/stream` | POST | Streaming agent execution (SSE) |

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LANGSMITH_API_KEY` | LangSmith API authentication key | `lsv2_pt_...` |
| `LANGSMITH_AGENT_ID` | LangSmith assistant ID for this agent | Set via `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_API_URL` | `https://api.smith.langchain.com/api/v1` | LangSmith API base URL |
| `LANGSMITH_TIMEOUT_SECONDS` | `300` | Request timeout (5 minutes) |
| `LANGCHAIN_PROJECT` | `researchflow-multilingual-literature-processor` | LangSmith project name |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing |
| `LOG_LEVEL` | `INFO` | Logging level |

## Request Schema

```json
{
  "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
  "request_id": "req-123",
  "workflow_id": "wf-456",
  "user_id": "user-789",
  "mode": "DEMO",
  "inputs": {
    "query": "cardiovascular disease prevention",
    "language": "Spanish",
    "languages": ["Spanish", "Portuguese", "English"],
    "output_language": "English",
    "date_range": "2020-2024",
    "citations": true,
    "abstracts": true,
    "full_text": false,
    "context": {},
    "output_format": "structured"
  }
}
```

### Input Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Research question or topic |
| `language` | string | No | Primary target language |
| `languages` | array | No | List of languages to search |
| `output_language` | string | No | Language for output (default: English) |
| `date_range` | string | No | Publication date filter |
| `citations` | boolean | No | Include formatted citations (default: true) |
| `abstracts` | boolean | No | Include translated abstracts (default: true) |
| `full_text` | boolean | No | Process full text (default: false) |
| `context` | object | No | Additional context |
| `output_format` | string | No | Output format: "structured", "narrative", or "json" |

## Response Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "papers": [],
    "translations": {},
    "synthesis": {},
    "google_doc_url": "https://docs.google.com/...",
    "citation_export": "BibTeX format...",
    "language_distribution": {},
    "quality_notes": [],
    "metadata": {},
    "langsmith_run_id": "run-abc123"
  }
}
```

## Health Checks

### Basic Health Check
```bash
curl http://localhost:8000/health
```

Expected: `{"status": "ok", "service": "agent-multilingual-literature-processor-proxy"}`

### Readiness Check
```bash
curl http://localhost:8000/health/ready
```

Expected: `{"status": "ready", "langsmith": "reachable", "agent_id_configured": true}`

**Fails if:**
- `LANGSMITH_API_KEY` not set
- `LANGSMITH_AGENT_ID` not set
- LangSmith API unreachable (network error)
- LangSmith API returns 5xx errors

## Docker Compose Integration

```yaml
agent-multilingual-literature-processor-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-multilingual-literature-processor-proxy/Dockerfile
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
    - LANGSMITH_AGENT_ID=${LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID}
    - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_TIMEOUT_SECONDS:-300}
  expose:
    - "8000"
  networks:
    - backend   # For orchestrator communication
    - frontend  # For LangSmith API access
```

## Orchestrator Integration

### Router Mapping (ai-router.ts)
```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ...
  MULTILINGUAL_LITERATURE_PROCESSING: 'agent-multilingual-literature-processor-proxy',
};
```

### Endpoint Registry (docker-compose.yml)
```json
{
  "agent-multilingual-literature-processor-proxy": "http://agent-multilingual-literature-processor-proxy:8000"
}
```

## Testing

### Direct Proxy Test
```bash
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "query": "diabetes treatment",
      "languages": ["Spanish", "English"],
      "output_language": "English"
    }
  }'
```

### Via Orchestrator Router
```bash
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
    "request_id": "test-002",
    "mode": "DEMO",
    "inputs": {
      "query": "hypertension management"
    }
  }'
```

## Logging

**PHI-SAFE**: This proxy does NOT log request or response bodies to prevent PHI leakage. Only metadata is logged:
- Request ID
- Task type
- Mode
- Timestamp
- HTTP status codes
- Error types (without details)

## Error Handling

| Error | Status | Response |
|-------|--------|----------|
| Missing LANGSMITH_API_KEY | 503 | Service unavailable |
| Missing LANGSMITH_AGENT_ID | 503 | Service unavailable |
| LangSmith API error | 200 | `{"ok": false, "error": "..."}` |
| Network error | 200 | `{"ok": false, "error": "Network error"}` |
| Timeout | 200 | `{"ok": false, "error": "Timeout"}` |

**Note**: Agent errors return HTTP 200 with `ok: false` to maintain contract compatibility with orchestrator.

## Development

### Local Setup
```bash
cd services/agents/agent-multilingual-literature-processor-proxy
pip install -r requirements.txt

# Set environment variables
export LANGSMITH_API_KEY="your-key"
export LANGSMITH_AGENT_ID="your-agent-id"

# Run locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Build
```bash
# Build from repo root (build context is .)
docker build -f services/agents/agent-multilingual-literature-processor-proxy/Dockerfile -t multilingual-lit-proxy .

# Run
docker run -p 8000:8000 \
  -e LANGSMITH_API_KEY="..." \
  -e LANGSMITH_AGENT_ID="..." \
  multilingual-lit-proxy
```

## Troubleshooting

### Health check fails
```bash
# Check logs
docker compose logs agent-multilingual-literature-processor-proxy

# Check environment variables
docker compose exec agent-multilingual-literature-processor-proxy env | grep LANGSMITH

# Test LangSmith API directly
curl https://api.smith.langchain.com/api/v1/info \
  -H "x-api-key: YOUR_KEY"
```

### Readiness check fails
- Verify `LANGSMITH_API_KEY` is set and valid
- Verify `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID` is set
- Check network connectivity to `api.smith.langchain.com`
- Verify LangSmith agent exists and is published

### Agent returns empty results
- Check `mode`: In DEMO mode, agent may return mock data
- Verify input fields are properly formatted
- Check LangSmith agent logs in LangSmith UI
- Verify agent has required tools enabled

## Security Notes

- **No PHI Logging**: Request/response bodies are never logged
- **API Key Protection**: `LANGSMITH_API_KEY` never exposed in logs or responses
- **Network Isolation**: Runs in Docker backend network with controlled external access
- **Timeout Protection**: Hard timeout prevents indefinite hangs

## Performance

- **Typical latency**: 10-60 seconds (varies by language count and scope)
- **Timeout**: 300 seconds (configurable)
- **Concurrent requests**: Supports multiple parallel requests
- **Rate limiting**: Inherits LangSmith API rate limits

## Maintenance

### Updating the Agent
1. Update LangSmith agent configuration in LangSmith UI
2. No proxy code changes needed (unless contract changes)
3. Test with smoke script: `CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 ./scripts/stagewise-smoke.sh`

### Monitoring
```bash
# Check proxy health
docker compose ps agent-multilingual-literature-processor-proxy

# View proxy logs
docker compose logs -f agent-multilingual-literature-processor-proxy

# Check orchestrator routing
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq '.["agent-multilingual-literature-processor-proxy"]'
```

---

**Version**: 1.0.0  
**Created**: 2026-02-08  
**Maintained By**: ResearchFlow Platform Team
