# Performance Optimizer Agent - Wiring Guide ✅

**Agent Key:** `agent-performance-optimizer`  
**Compose Service:** `agent-performance-optimizer-proxy`  
**Task Type:** `PERFORMANCE_OPTIMIZATION`  
**Deployment:** LangSmith cloud + Local FastAPI proxy  
**Status:** ✅ **PRODUCTION READY**

---

## Architecture

```
User/UI → Orchestrator → Proxy → LangSmith Cloud → 2 Workers → Response
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Main Agent** | LangSmith cloud | Performance analysis orchestration |
| **Optimization_Researcher** | LangSmith cloud | Research LLM optimization strategies |
| **Cost_Benchmarker** | LangSmith cloud | Analyze provider pricing |
| **Proxy Service** | `services/agents/agent-performance-optimizer-proxy/` | HTTP adapter (ResearchFlow ↔ LangSmith) |
| **Agent Config** | `services/agents/agent-performance-optimizer/` | Prompts, tools, subagents |

---

## Router Registration

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
PERFORMANCE_OPTIMIZATION: 'agent-performance-optimizer',  // LangSmith-hosted performance monitoring & optimization (cross-cutting)
```

**Agent Endpoint (AGENT_ENDPOINTS_JSON):**
```json
{
  "agent-performance-optimizer": "http://agent-performance-optimizer-proxy:8000"
}
```

---

## Environment Variables

### Required

| Variable | Example | Purpose |
|----------|---------|---------|
| `LANGSMITH_API_KEY` | `<your-langsmith-api-key>` | LangSmith API authentication |
| `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` | `<uuid>` | Agent ID from LangSmith |

### Optional

| Variable | Default | Purpose |
|----------|---------|---------|
| `LANGSMITH_API_URL` | `https://api.smith.langchain.com/api/v1` | LangSmith API base URL |
| `LANGSMITH_PERFORMANCE_OPTIMIZER_TIMEOUT_SECONDS` | `300` | Request timeout (5 minutes) |
| `GOOGLE_SHEETS_API_KEY` | - | Read metrics from spreadsheets |
| `GOOGLE_DOCS_API_KEY` | - | Write reports to Google Docs |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Input/Output Schema

### Input (POST `/api/ai/router/dispatch`)

```json
{
  "task_type": "PERFORMANCE_OPTIMIZATION",
  "request_id": "perf-001",
  "mode": "DEMO",
  "inputs": {
    "metrics_spreadsheet_id": "abc123...",
    "metrics_data": {
      "last_24h": {
        "p50_latency_ms": 150,
        "p95_latency_ms": 450,
        "p99_latency_ms": 800,
        "error_rate": 0.02,
        "total_requests": 5000,
        "token_cost_usd": 12.50
      }
    },
    "analysis_focus": "latency",
    "time_period": "last_7_days",
    "question": "Why is my latency so high?"
  }
}
```

**Input Fields:**
- `metrics_spreadsheet_id` (optional): Google Sheets ID containing metrics
- `metrics_data` (optional): Direct metrics data (if not using spreadsheet)
- `analysis_focus` (optional): Specific area to analyze (latency, cost, errors)
- `time_period` (optional): Time range for analysis (last_7_days, last_30_days, custom)
- `question` (optional): Specific question or concern

### Output

```json
{
  "ok": true,
  "request_id": "perf-001",
  "outputs": {
    "performance_report": "## Performance Analysis Report\n\n...",
    "optimization_recommendations": [
      {
        "issue": "High P99 latency on /api/search",
        "recommendation": "Implement request coalescing",
        "estimated_impact": "30% latency reduction",
        "implementation_effort": "medium"
      }
    ],
    "cost_analysis": {
      "current_provider": "openai",
      "current_cost_per_day": 12.50,
      "alternative_recommendations": [
        {
          "provider": "anthropic",
          "model": "claude-3-5-sonnet",
          "projected_cost_per_day": 8.75,
          "estimated_savings": "30%"
        }
      ]
    },
    "bottleneck_identification": [
      {
        "component": "agent-stage2-screen",
        "metric": "p99_latency_ms",
        "current_value": 2500,
        "threshold": 1000,
        "severity": "high"
      }
    ],
    "alert_summary": {
      "critical_alerts": 0,
      "warning_alerts": 2,
      "info_alerts": 5
    },
    "google_doc_url": "https://docs.google.com/...",
    "langsmith_run_id": "..."
  }
}
```

---

## Deployment on ROSflow2

### Prerequisites

1. **Get Agent ID from LangSmith:**
   - Visit https://smith.langchain.com/
   - Navigate to your Performance Optimizer agent
   - Copy the UUID from the URL or agent settings

2. **Update `.env`:**
```bash
# Required
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID=<uuid-from-langsmith>

# Optional
GOOGLE_SHEETS_API_KEY=...
GOOGLE_DOCS_API_KEY=...
```

### Deploy Steps

```bash
# 1. Pull latest changes
cd /opt/researchflow
git fetch --all --prune
git checkout feat/import-dissemination-formatter
git pull --ff-only

# 2. Verify environment
cat .env | grep LANGSMITH

# 3. Build and start proxy service
docker compose build agent-performance-optimizer-proxy
docker compose up -d agent-performance-optimizer-proxy

# 4. Wait for healthy
sleep 15

# 5. Verify proxy health
docker compose ps agent-performance-optimizer-proxy
docker compose exec agent-performance-optimizer-proxy curl -f http://localhost:8000/health

# 6. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 7. Validate wiring
./scripts/hetzner-preflight.sh

# 8. Optional: Run smoke test
CHECK_PERFORMANCE_OPTIMIZER=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

Validates:
- ✅ `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` configured
- ✅ Task type `PERFORMANCE_OPTIMIZATION` registered in ai-router.ts
- ✅ Agent in `AGENT_ENDPOINTS_JSON`
- ✅ Proxy container running and healthy

**Expected Output:**
```
Performance Optimizer Agent (LangSmith Proxy)
✓ LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID configured
✓ Router Registration: PERFORMANCE_OPTIMIZATION -> agent-performance-optimizer
```

### Smoke Test (Optional)

**Script:** `scripts/stagewise-smoke.sh`

**Enable:** `CHECK_PERFORMANCE_OPTIMIZER=1`

Validates:
- ✅ Router dispatch returns correct agent name
- ✅ Proxy container running and healthy
- ✅ Artifact directory structure created
- ⚠️ Does not call LangSmith API (no live agent execution)

**Expected Output:**
```
[14] Performance Optimizer Agent Check (optional - LangSmith-based)
[14a] Checking LANGSMITH_API_KEY and agent ID configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
✓ LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID is configured in orchestrator
[14b] POST /api/ai/router/dispatch (PERFORMANCE_OPTIMIZATION)
Router dispatch OK: response code 200
✓ Correctly routed to agent-performance-optimizer
[14c] Checking proxy container health
✓ agent-performance-optimizer-proxy container is running
✓ Proxy health endpoint responding
[14d] Checking artifacts directory structure
✓ /data/artifacts exists
✓ Wrote validation artifact to /data/artifacts/validation/performance-optimizer-smoke/...
Performance Optimizer Agent check complete (optional - does not block)
```

### Manual Test

```bash
# Get auth token
TOKEN="Bearer <your-jwt>"

# Test dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "PERFORMANCE_OPTIMIZATION",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "metrics_data": {
        "last_24h": {
          "p50_latency_ms": 150,
          "p95_latency_ms": 450,
          "p99_latency_ms": 800,
          "error_rate": 0.02,
          "total_requests": 5000,
          "token_cost_usd": 12.50
        }
      },
      "analysis_focus": "latency",
      "time_period": "last_24_hours"
    }
  }'
```

**Expected Response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-performance-optimizer",
  "agent_url": "http://agent-performance-optimizer-proxy:8000",
  "request_id": "test-001"
}
```

---

## Files Changed

### Created (6 files)
1. `services/agents/agent-performance-optimizer-proxy/Dockerfile`
2. `services/agents/agent-performance-optimizer-proxy/requirements.txt`
3. `services/agents/agent-performance-optimizer-proxy/app/__init__.py`
4. `services/agents/agent-performance-optimizer-proxy/app/config.py`
5. `services/agents/agent-performance-optimizer-proxy/app/main.py`
6. `services/agents/agent-performance-optimizer-proxy/README.md`

### Modified (4 files)
1. `docker-compose.yml` (+35 lines)
   - Added proxy service definition
   - Updated `AGENT_ENDPOINTS_JSON`
   - Updated proxy list comment
2. `scripts/hetzner-preflight.sh` (+58 lines)
   - Added Performance Optimizer validation section
3. `scripts/stagewise-smoke.sh` (+121 lines + 2 flag declarations)
   - Added optional Performance Optimizer smoke test
4. `scripts/lib/agent_endpoints_required.txt` (+1 line)
   - Added `agent-performance-optimizer` to mandatory list

### Documentation (1 file)
5. `docs/agents/performance-optimizer/wiring.md` (this file)

---

## Alert Thresholds

### Critical
- Error rate > 10%
- Cost spike > 50% day-over-day
- P99 latency > 30 seconds

### Warning
- Error rate > 5%
- Cost increase > 20% week-over-week
- Avg latency increase > 30% week-over-week

---

## Use Cases

### Scheduled Analysis (Cron)
1. Reads latest metrics from Google Sheets
2. Compares against previous periods
3. Checks alert thresholds
4. Identifies top 3-5 performance issues
5. Delegates research to sub-workers
6. Generates and archives report to Google Docs
7. Updates tracking spreadsheet

### On-Demand Analysis
- Triggered manually with metrics data
- Targeted question (e.g., "Why is my latency so high?")
- Cost optimization recommendations
- Alternative provider pricing comparison

---

## Troubleshooting

### 503 Service Unavailable
- Check `LANGSMITH_API_KEY` is set
- Check `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` is set
- Verify LangSmith API is reachable: `curl https://api.smith.langchain.com/info`

### Timeout errors
- Increase `LANGSMITH_PERFORMANCE_OPTIMIZER_TIMEOUT_SECONDS` (default 300)
- Check LangSmith agent logs for sub-worker failures

### Google integration errors
- Set `GOOGLE_SHEETS_API_KEY` if reading from spreadsheets
- Set `GOOGLE_DOCS_API_KEY` if writing reports to Google Docs
- Otherwise, pass `metrics_data` directly in request

### Proxy not running
- Check docker compose logs: `docker compose logs agent-performance-optimizer-proxy`
- Restart: `docker compose restart agent-performance-optimizer-proxy`
- Rebuild: `docker compose build agent-performance-optimizer-proxy && docker compose up -d agent-performance-optimizer-proxy`

---

## References

- **Proxy README:** `services/agents/agent-performance-optimizer-proxy/README.md`
- **Agent README:** `services/agents/agent-performance-optimizer/README.md`
- **Agent Prompts:** `services/agents/agent-performance-optimizer/AGENTS.md`
- **Router:** `services/orchestrator/src/routes/ai-router.ts`
- **Preflight:** `scripts/hetzner-preflight.sh`
- **Smoke Test:** `scripts/stagewise-smoke.sh`

---

**Wiring Date:** 2026-02-08  
**Status:** ✅ **COMPLETE**  
**Branch:** feat/import-dissemination-formatter  
**Next Action:** Deploy to server and run validation
