# Journal Guidelines Cache Agent - LangSmith Proxy

## Purpose

Thin FastAPI adapter that proxies ResearchFlow agent requests to the LangSmith cloud-hosted Journal Guidelines Cache Agent.

## Architecture

```
Orchestrator → agent-journal-guidelines-cache-proxy:8000 → LangSmith Cloud API
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
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `180` (3 minutes for cache operations)
- `LOG_LEVEL` - Default: `INFO`
- `LANGCHAIN_PROJECT` - Default: `researchflow-journal-guidelines-cache`
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
docker build -t agent-journal-guidelines-cache-proxy:latest .
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/health/ready

# Test single journal lookup
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "action": "get_guidelines",
      "journal_name": "Nature"
    }
  }'

# Test batch lookup
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-002",
    "mode": "DEMO",
    "inputs": {
      "action": "batch_lookup",
      "journal_names": ["Nature", "Science", "NEJM"]
    }
  }'

# Test journal comparison
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-003",
    "mode": "DEMO",
    "inputs": {
      "action": "compare_journals",
      "journal_names": ["Nature", "Science"]
    }
  }'

# Test cache stats
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-004",
    "mode": "DEMO",
    "inputs": {
      "action": "cache_stats"
    }
  }'
```

## Integration

This service is registered in `docker-compose.yml` as `agent-journal-guidelines-cache-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-journal-guidelines-cache": "http://agent-journal-guidelines-cache-proxy:8000"
}
```

## Input Schema

```json
{
  "task_type": "JOURNAL_GUIDELINES_CACHE",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "action": "get_guidelines",          // or "batch_lookup", "compare_journals", "cache_stats", "list_cached", "force_refresh"
    "journal_name": "Nature",            // for single journal operations
    "journal_names": ["Nature", "Science"], // for batch/comparison operations
    "force_refresh": false,              // optional: force refresh even if fresh
    "spreadsheet_id": "optional-id"      // optional: use specific cache spreadsheet
  }
}
```

## Output Schema

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "guidelines": "Full structured guidelines text...",
    "cache_status": "cached (as of 2026-02-07)" or "freshly fetched",
    "last_updated": "2026-02-07",
    "aliases": ["NEJM", "N Engl J Med"],
    "source_urls": ["https://www.nejm.org/author-center/..."],
    "changelog": {                       // Only present if changes detected during refresh
      "severity": "critical",
      "summary": "Changed word limit from 3000 to 3500..."
    },
    "comparison_table": "...",           // Only for compare_journals action
    "cache_stats": {                     // Only for cache_stats action
      "total_entries": 45,
      "fresh_count": 42,
      "stale_count": 3,
      "oldest_entry": "2025-12-15",
      "newest_entry": "2026-02-07"
    },
    "langsmith_run_id": "..."
  }
}
```

## Error Handling

- **503**: LangSmith API not configured or unreachable
- **500**: Unexpected proxy error
- **200 with ok=false**: LangSmith agent execution error (see `error` field)

## Actions

| Action | Description | Required Inputs |
|--------|-------------|----------------|
| `get_guidelines` | Get guidelines for single journal | `journal_name` |
| `batch_lookup` | Get guidelines for multiple journals | `journal_names` |
| `compare_journals` | Compare 2+ journals side-by-side | `journal_names` |
| `force_refresh` | Force refresh single journal | `journal_name` |
| `cache_stats` | Get cache statistics | None |
| `list_cached` | List all cached journals | None |
| `show_changelog` | Show changelog for journal | `journal_name` (optional) |

## Cache Operations

### Staleness Detection
- Guidelines > 30 days old are marked as "stale"
- Stale entries are automatically refreshed with change detection

### Change Tracking
- All refreshes run through Changelog Detector worker
- Changes classified as: critical, notable, or minor
- Audit trail maintained in Google Sheets "Changelog" tab

### Daily Refresh (Scheduled)
- Daily cron trigger refreshes all stale entries
- Change notifications generated for critical updates
- Summary report includes success/failure metrics

## Notes

- Cache operations typically complete in < 1 second for cache hits
- Fresh fetches require web search and may take 5-15 seconds
- Batch operations run in parallel for efficiency
- All operations are logged for audit compliance
