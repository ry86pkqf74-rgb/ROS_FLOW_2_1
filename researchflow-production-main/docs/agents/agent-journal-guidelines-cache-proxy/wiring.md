# Journal Guidelines Cache Agent - Wiring Documentation

**Date:** 2026-02-08  
**Status:** ✅ **Wired for Production Deployment**

---

## Summary

The Journal Guidelines Cache agent provides intelligent caching for academic journal submission guidelines. It eliminates redundant web searches through a persistent Google Sheets cache with automatic staleness detection (30-day threshold), proactive daily refresh, and change tracking with audit trails. This LangSmith cloud-hosted agent is accessible via an HTTP proxy service and integrated with the orchestrator router.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy ✅

```
User/UI Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓ [task_type: JOURNAL_GUIDELINES_CACHE]
TASK_TYPE_TO_AGENT mapping
    ↓ [resolves to: agent-journal-guidelines-cache-proxy]
    ↓ [agent URL: http://agent-journal-guidelines-cache-proxy:8000]
FastAPI Proxy (agent-journal-guidelines-cache-proxy)
    ↓ [transform ResearchFlow → LangSmith format]
LangSmith API (https://api.smith.langchain.com)
    ↓ [executes agent + 3 worker sub-agents]
    ↓ [cache lookup → fresh fetch → change detection]
FastAPI Proxy
    ↓ [transform LangSmith → ResearchFlow format]
Response (JSON: guidelines, cache_status, last_updated, changelog)
    ↓
Artifact Writer (optional: /data/artifacts/journal-guidelines/)
    ↓
Return to caller
```

---

## Components

### 1. Proxy Service: `agent-journal-guidelines-cache-proxy`

**Location:** `services/agents/agent-journal-guidelines-cache-proxy/`

**Docker Service:** `agent-journal-guidelines-cache-proxy` (compose service)

**Endpoints:**
- `GET /health` - Health check
- `GET /health/ready` - LangSmith connectivity validation
- `POST /agents/run/sync` - Synchronous execution (cache lookup/refresh)
- `POST /agents/run/stream` - Streaming execution (SSE)

**Container Details:**
- Port: 8000 (internal)
- Networks: backend (internal), frontend (LangSmith API + Google Sheets access)
- Health check: `/health` every 30s
- Resources: 0.5 CPU / 512MB memory (max)

### 2. Agent Configuration: `agent-journal-guidelines-cache`

**Location:** `services/agents/agent-journal-guidelines-cache/` (if imported)

**Type:** LangSmith custom agent (cloud-hosted, not containerized)

**Worker Sub-Agents:**
1. Guidelines_Researcher - Fetches fresh journal submission guidelines from authoritative sources
2. Changelog_Detector - Compares old vs. new guidelines to detect and document changes
3. Guidelines_Comparator - Performs side-by-side comparison of multiple journals

**Cache Architecture:**
- **Sheet 1 (Cache)**: journal_name, aliases, last_updated, guidelines_summary, source_urls, status (fresh/stale)
- **Sheet 2 (Changelog)**: journal_name, change_date, change_summary, severity
- **Staleness Threshold**: 30 days
- **Initialization**: Auto-creates spreadsheet if not provided

---

## Router Registration

### Task Type Mapping

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ... other agents ...
  JOURNAL_GUIDELINES_CACHE: 'agent-journal-guidelines-cache-proxy',  // LangSmith-hosted cache agent
};
```

### Endpoint Registration

**Environment Variable:** `AGENT_ENDPOINTS_JSON`

```json
{
  "agent-journal-guidelines-cache-proxy": "http://agent-journal-guidelines-cache-proxy:8000"
}
```

---

## Environment Variables

### Required (Proxy Service)

| Variable | Description | Example |
|----------|-------------|---------|
| `LANGSMITH_API_KEY` | LangSmith API authentication | `<your-langsmith-api-key>` |
| `LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID` | Agent UUID from LangSmith | `12345678-90ab-cdef-1234-567890abcdef` |

### Optional (Proxy Service)

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGSMITH_API_URL` | `https://api.smith.langchain.com/api/v1` | LangSmith API base URL |
| `LANGSMITH_JOURNAL_GUIDELINES_CACHE_TIMEOUT_SECONDS` | `180` | Request timeout (3 minutes for cache ops) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LANGCHAIN_PROJECT` | `researchflow-journal-guidelines-cache` | LangSmith project name |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith tracing |

### Optional (Tool-Level)

| Variable | Description | Required By |
|----------|-------------|-------------|
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Pre-existing cache spreadsheet ID | Agent auto-creates if not provided |
| `GOOGLE_WORKSPACE_API_KEY` | Google Sheets API credentials | Agent tools (if not using service account) |

---

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

### Supported Actions

| Action | Description | Required Inputs |
|--------|-------------|----------------|
| `get_guidelines` | Get guidelines for single journal | `journal_name` |
| `batch_lookup` | Get guidelines for multiple journals | `journal_names` |
| `compare_journals` | Compare 2+ journals side-by-side | `journal_names` |
| `force_refresh` | Force refresh single journal | `journal_name` |
| `cache_stats` | Get cache statistics | None |
| `list_cached` | List all cached journals | None |
| `show_changelog` | Show changelog for journal | `journal_name` (optional) |

---

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

---

## Deployment Steps (Hetzner - ROSflow2)

### Prerequisites

1. **Access to ROSflow2:**
   ```bash
   ssh user@rosflow2
   cd /opt/researchflow/researchflow-production-main
   ```

2. **LangSmith Configuration:**
   - Ensure agent is deployed in LangSmith cloud
   - Obtain agent UUID from LangSmith UI (Settings → Agents)
   - Have `LANGSMITH_API_KEY` ready (format: `<your-langsmith-api-key>`)

### Step 1: Update Environment Variables

Add to `.env` file on ROSflow2:

```bash
# Journal Guidelines Cache Agent (LangSmith)
LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID=<uuid-from-langsmith>

# Optional: Pre-existing Google Sheets cache ID (auto-creates if not provided)
# GOOGLE_SHEETS_SPREADSHEET_ID=<spreadsheet-id>

# If not already present, add LangSmith API key
LANGSMITH_API_KEY=<your-langsmith-api-key>
```

### Step 2: Build and Deploy Proxy Service

```bash
# Pull latest code (if using Git deployment)
git fetch --all --prune
git checkout main
git pull --ff-only

# Build and start proxy service
docker compose build agent-journal-guidelines-cache-proxy
docker compose up -d agent-journal-guidelines-cache-proxy

# Verify service is running
docker compose ps | grep journal-guidelines-cache
```

### Step 3: Restart Orchestrator (if AGENT_ENDPOINTS_JSON changed)

```bash
# Only needed if AGENT_ENDPOINTS_JSON was updated in docker-compose.yml
docker compose up -d --force-recreate orchestrator
```

### Step 4: Validate Deployment

```bash
# Run preflight checks (validates all agents including journal-guidelines-cache-proxy)
./scripts/hetzner-preflight.sh

# Run targeted smoke test
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Validation Procedures

### Preflight Validation (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**What it checks:**
- ✅ Container running: `agent-journal-guidelines-cache-proxy`
- ✅ Health endpoint responding: `GET /health`
- ✅ Registry entry: Key in `AGENT_ENDPOINTS_JSON`
- ✅ Environment variables: `LANGSMITH_API_KEY`, `LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID`

**Run:**
```bash
./scripts/hetzner-preflight.sh
```

**Expected output:**
```
✓ agent-journal-guidelines-cache-proxy [Registry] http://agent-journal-guidelines-cache-proxy:8000
✓ agent-journal-guidelines-cache-proxy [Container] running
✓ agent-journal-guidelines-cache-proxy [Health] responding
```

### Smoke Test (All Agents)

**Script:** `scripts/stagewise-smoke.sh`

**Flags:**
- `CHECK_ALL_AGENTS=1` - Validates all agents in AGENT_ENDPOINTS_JSON
- `DEV_AUTH=true` - Auto-mints dev token for testing

**Run:**
```bash
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

**What it tests:**
1. Router dispatch: `POST /api/ai/router/dispatch` with `task_type=JOURNAL_GUIDELINES_CACHE`
2. Agent routing: Verifies orchestrator routes to `agent-journal-guidelines-cache-proxy`
3. Fixture test: Cache stats action (doesn't require external API calls)

**Artifact Output:**
```
/data/artifacts/validation/agent-journal-guidelines-cache-proxy/<timestamp>/summary.json
```

### Targeted Smoke Test (Journal Guidelines Cache Only)

For quick validation of just the journal guidelines cache agent:

```bash
# Test cache stats (lightweight, no external API calls)
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "JOURNAL_GUIDELINES_CACHE",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "action": "cache_stats"
    }
  }'
```

---

## Troubleshooting

### Issue: Container not starting

**Symptoms:**
```
agent-journal-guidelines-cache-proxy    Exit 1
```

**Diagnosis:**
```bash
# Check logs
docker compose logs agent-journal-guidelines-cache-proxy --tail=50

# Common causes:
# - Missing LANGSMITH_API_KEY
# - Invalid LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID
# - Python dependency issues
```

**Fix:**
```bash
# Verify environment variables
docker compose exec orchestrator env | grep LANGSMITH

# Rebuild if dependencies changed
docker compose build --no-cache agent-journal-guidelines-cache-proxy
docker compose up -d agent-journal-guidelines-cache-proxy
```

### Issue: Health check failing

**Symptoms:**
```
✗ agent-journal-guidelines-cache-proxy [Health] not responding or unhealthy
```

**Diagnosis:**
```bash
# Test health endpoint directly
docker compose exec agent-journal-guidelines-cache-proxy curl -v http://localhost:8000/health

# Check if LangSmith API is reachable
docker compose exec agent-journal-guidelines-cache-proxy curl -v https://api.smith.langchain.com/api/v1/info
```

**Fix:**
1. Verify `LANGSMITH_API_KEY` is valid (not expired)
2. Check firewall/network allows outbound HTTPS to LangSmith
3. Restart service: `docker compose restart agent-journal-guidelines-cache-proxy`

### Issue: Router dispatch fails (HTTP 500)

**Symptoms:**
```
{
  "error": "AGENT_NOT_CONFIGURED",
  "message": "Missing agent endpoint for key: agent-journal-guidelines-cache-proxy"
}
```

**Diagnosis:**
```bash
# Check AGENT_ENDPOINTS_JSON
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep journal-guidelines
```

**Fix:**
1. Verify `AGENT_ENDPOINTS_JSON` in `docker-compose.yml` includes:
   ```json
   "agent-journal-guidelines-cache-proxy":"http://agent-journal-guidelines-cache-proxy:8000"
   ```
2. Restart orchestrator: `docker compose up -d --force-recreate orchestrator`

### Issue: LangSmith agent execution timeout

**Symptoms:**
```json
{
  "ok": false,
  "error": "LangSmith API timeout - cache operation took too long"
}
```

**Fix:**
1. Increase timeout in `.env`:
   ```bash
   LANGSMITH_JOURNAL_GUIDELINES_CACHE_TIMEOUT_SECONDS=300
   ```
2. Restart proxy: `docker compose restart agent-journal-guidelines-cache-proxy`

### Issue: Google Sheets access denied

**Symptoms:**
```json
{
  "ok": false,
  "error": "Google Sheets API error: 403 Forbidden"
}
```

**Fix:**
1. Verify Google Sheets credentials are configured in LangSmith agent
2. If using `GOOGLE_SHEETS_SPREADSHEET_ID`, ensure the spreadsheet is accessible by the service account
3. Alternatively, let agent auto-create new spreadsheet (remove `GOOGLE_SHEETS_SPREADSHEET_ID`)

---

## Operational Modes

### Mode 1 - Single Journal Lookup
- **Action:** `get_guidelines`
- **Flow:** Check cache → Return immediately (if fresh) OR Refresh with change detection (if stale) OR Fetch fresh (if missing)
- **Response Time:** < 100ms (cache hit), 5-15s (fresh fetch)

### Mode 2 - Batch Lookup
- **Action:** `batch_lookup`
- **Flow:** Process multiple journals in parallel, return cache hits immediately, fetch/refresh missing/stale
- **Response Time:** Varies by cache hit rate (target >80%)

### Mode 3 - Compare Journals
- **Action:** `compare_journals`
- **Flow:** Ensure all journals fresh, delegate to comparator, return side-by-side analysis
- **Response Time:** 10-30s depending on freshness

### Mode 4 - Scheduled Refresh (Future)
- **Trigger:** Daily cron job
- **Flow:** Refresh all stale entries with change notifications
- **Target:** Stale entries after daily refresh = 0

---

## Quality Metrics

| Metric | Target | How to Check |
|--------|--------|--------------|
| Cache hit rate | >80% | Call `cache_stats` action |
| Response time (cache hits) | <100ms | Monitor LangSmith traces |
| Daily refresh success rate | >95% | Check changelog for refresh errors |
| Stale entries after refresh | 0 | Call `cache_stats` action daily |

---

## Related Documentation

- **Proxy README:** `services/agents/agent-journal-guidelines-cache-proxy/README.md`
- **Agent Inventory:** `AGENT_INVENTORY.md` (search for "Journal Guidelines Cache")
- **Agent Briefing:** `AGENT_JOURNAL_GUIDELINES_CACHE_BRIEFING.md` (if available)
- **Router Implementation:** `services/orchestrator/src/routes/ai-router.ts`
- **Preflight Script:** `scripts/hetzner-preflight.sh`
- **Smoke Test Script:** `scripts/stagewise-smoke.sh`

---

## Quick Reference Commands

```bash
# Deployment
docker compose build agent-journal-guidelines-cache-proxy
docker compose up -d agent-journal-guidelines-cache-proxy

# Validation
./scripts/hetzner-preflight.sh
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh

# Monitoring
docker compose logs -f agent-journal-guidelines-cache-proxy
docker compose ps | grep journal-guidelines-cache

# Testing
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"JOURNAL_GUIDELINES_CACHE","request_id":"test","mode":"DEMO","inputs":{"action":"cache_stats"}}'

# Troubleshooting
docker compose exec agent-journal-guidelines-cache-proxy curl http://localhost:8000/health
docker compose exec orchestrator env | grep LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID
docker compose restart agent-journal-guidelines-cache-proxy
```

---

**Status:** ✅ **Production Ready** (2026-02-08)  
**Last Updated:** 2026-02-08  
**Maintained By:** ResearchFlow Platform Team
