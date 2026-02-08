# Artifact Auditor Agent - Wiring Documentation

**Date:** 2026-02-08  
**Branch:** feat/import-dissemination-formatter  
**Status:** ✅ **Wired for Production Deployment**

---

## Summary

The Artifact Auditor agent reviews dissemination artifacts (manuscripts, reports, formatted research outputs) against established reporting standards (CONSORT, PRISMA, STROBE, etc.) to ensure quality, consistency, and equitable reporting. This LangSmith cloud-hosted agent is accessible via an HTTP proxy service and integrated with the orchestrator router.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy ✅

```
User/UI Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓ [task_type: ARTIFACT_AUDIT]
TASK_TYPE_TO_AGENT mapping
    ↓ [resolves to: agent-artifact-auditor-proxy]
    ↓ [agent URL: http://agent-artifact-auditor-proxy:8000]
FastAPI Proxy (agent-artifact-auditor-proxy)
    ↓ [transform ResearchFlow → LangSmith format]
LangSmith API (https://api.smith.langchain.com)
    ↓ [executes agent + 3 worker sub-agents]
    ↓ [returns audit results + reports]
FastAPI Proxy
    ↓ [transform LangSmith → ResearchFlow format]
Response (JSON: audit_summary, compliance_score, issues, report_url)
    ↓
Artifact Writer (optional: /data/artifacts/validation/)
    ↓
Return to caller
```

---

## Components

### 1. Proxy Service: `agent-artifact-auditor-proxy`

**Location:** `services/agents/agent-artifact-auditor-proxy/`

**Docker Service:** `agent-artifact-auditor-proxy` (compose service)

**Endpoints:**
- `GET /health` - Health check
- `GET /health/ready` - LangSmith connectivity validation
- `POST /agents/run/sync` - Synchronous audit execution
- `POST /agents/run/stream` - Streaming audit execution (SSE)

**Container Details:**
- Port: 8000 (internal)
- Networks: backend (internal), frontend (LangSmith API access)
- Health check: `/health` every 30s
- Resources: 0.5 CPU / 512MB memory (max)

### 2. Agent Configuration: `agent-artifact-auditor`

**Location:** `services/agents/agent-artifact-auditor/`

**Type:** LangSmith custom agent (cloud-hosted, not containerized)

**Worker Sub-Agents:**
1. **Guideline_Researcher** - Retrieves and structures official reporting standard checklists
2. **Compliance_Auditor** - Performs deep item-by-item audit against checklists
3. **Cross_Artifact_Tracker** - Analyzes audit findings across multiple audits for trends

---

## Router Registration

### Task Type Mapping

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ... other agents ...
  ARTIFACT_AUDIT: 'agent-artifact-auditor-proxy',  // LangSmith-backed artifact auditor
};
```

### Endpoint Registration

**Environment Variable:** `AGENT_ENDPOINTS_JSON`

**File:** `docker-compose.yml` (orchestrator service)

```json
{
  "agent-artifact-auditor-proxy": "http://agent-artifact-auditor-proxy:8000"
}
```

---

## Environment Variables

### Required

```bash
# LangSmith API credentials
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID=<uuid-from-langsmith>
```

### Optional

```bash
# LangSmith configuration
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1
LANGSMITH_ARTIFACT_AUDITOR_TIMEOUT_SECONDS=300  # 5 minutes

# Logging
LOG_LEVEL=INFO
AGENT_LOG_LEVEL=INFO

# LangChain tracing
LANGCHAIN_PROJECT=researchflow-artifact-auditor
LANGCHAIN_TRACING_V2=false

# Worker tools (optional - enhances functionality)
GITHUB_TOKEN=<your-github-token>   # GitHub artifact retrieval
GOOGLE_DOCS_API_KEY=...                # Google Docs integration
GOOGLE_SHEETS_API_KEY=...              # Audit tracker spreadsheet
```

---

## Input/Output Schema

### Input (POST `/api/ai/router/dispatch`)

```json
{
  "task_type": "ARTIFACT_AUDIT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "artifact_source": "github",
    "artifact_location": "owner/repo/path/to/manuscript.md",
    "reporting_standard": "CONSORT",
    "standard_version": "2010",
    "custom_guidelines": "optional custom checklist text",
    "github_repository": "owner/repo",
    "github_file_path": "path/to/manuscript.md",
    "google_doc_id": "optional-doc-id",
    "artifact_content": "direct text input (optional)"
  }
}
```

### Output

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "audit_summary": {
      "artifact_name": "Manuscript Title",
      "standard": "CONSORT",
      "compliance_score": "22/25 items (88%)"
    },
    "compliance_score": "22/25 items (88%)",
    "critical_issues": [
      {
        "item_number": "7a",
        "description": "Sample size calculation not reported",
        "recommendation": "Add sample size calculation with power, alpha, effect size"
      }
    ],
    "major_issues": [...],
    "minor_issues": [...],
    "equity_flags": [
      {
        "issue": "No subgroup analysis by race/ethnicity reported",
        "recommendation": "Add subgroup analyses or justify exclusion"
      }
    ],
    "audit_report_url": "https://docs.google.com/document/d/...",
    "audit_log_entry": {
      "timestamp": "2026-02-08T12:00:00Z",
      "artifact_name": "Manuscript Title",
      "standard": "CONSORT",
      "compliance_score": "22/25 items (88%)",
      "critical_count": 1,
      "major_count": 2,
      "minor_count": 5
    },
    "langsmith_run_id": "abc-123"
  }
}
```

### Artifact Paths (Optional)

```
/data/artifacts/validation/agent-artifact-auditor-proxy/
├── <timestamp>/
│   ├── summary.json
│   ├── audit_report.json
│   └── compliance_checklist.json
```

---

## Supported Reporting Standards

| Standard | Checklist Items | Study Type |
|----------|----------------|------------|
| CONSORT | 25 | Randomized controlled trials |
| PRISMA | 27 | Systematic reviews / meta-analyses |
| STROBE | 22 | Observational studies |
| SPIRIT | 33 | Trial protocols |
| CARE | 13 | Case reports |
| ARRIVE | 21 | Animal research |
| TIDieR | 12 | Intervention descriptions |
| CHEERS | 24 | Health economic evaluations |
| MOOSE | 35 | Meta-analyses of observational studies |

---

## Deployment Steps

### On ROSflow2 (Hetzner)

```bash
# 1. Navigate to deployment directory
cd /opt/researchflow

# 2. Pull latest code (branch: feat/import-dissemination-formatter)
git fetch --all --prune
git checkout feat/import-dissemination-formatter
git pull --ff-only

# 3. Set environment variables
cat >> .env << 'ENV_EOF'
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID=<uuid-from-langsmith>
ENV_EOF

# 4. Build proxy service
docker compose build agent-artifact-auditor-proxy

# 5. Start proxy
docker compose up -d agent-artifact-auditor-proxy

# 6. Wait for healthy
sleep 15

# 7. Verify proxy health
docker compose ps agent-artifact-auditor-proxy
docker compose exec agent-artifact-auditor-proxy curl -f http://localhost:8000/health

# 8. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 9. Run preflight checks
./researchflow-production-main/scripts/hetzner-preflight.sh

# 10. Optional: Run smoke test
CHECK_ARTIFACT_AUDITOR=1 DEV_AUTH=true ./researchflow-production-main/scripts/stagewise-smoke.sh
```

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**Checks:**
- ✅ `LANGSMITH_API_KEY` present in orchestrator environment
- ✅ `LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID` present in orchestrator environment
- ✅ `agent-artifact-auditor-proxy` in AGENT_ENDPOINTS_JSON
- ✅ Container running and healthy
- ✅ Health endpoint responding

**Expected Output:**
```
Checking: agent-artifact-auditor-proxy
  agent-artifact-auditor-proxy [Registry]  ✓ PASS
  agent-artifact-auditor-proxy [Container] ✓ PASS
  agent-artifact-auditor-proxy [Health]    ✓ PASS
```

### Smoke Test (Optional)

**Flag:** `CHECK_ARTIFACT_AUDITOR=1`

**Script:** `scripts/stagewise-smoke.sh`

**Tests:**
- LANGSMITH_API_KEY configured
- LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID configured
- Router dispatch returns correct agent name
- Proxy container running and healthy
- Deterministic audit with built-in fixture (no external network calls)
- Artifact directory structure created

**Run:**
```bash
CHECK_ARTIFACT_AUDITOR=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

**Expected Output:**
```
[15] Artifact Auditor Agent Check (optional - LangSmith-based)
[15a] Checking LANGSMITH_API_KEY and agent ID configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
✓ LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID is configured
[15b] POST /api/ai/router/dispatch (ARTIFACT_AUDIT)
Router dispatch OK: routed to agent-artifact-auditor-proxy
✓ Correctly routed to agent-artifact-auditor-proxy
[15c] Checking proxy container health
✓ agent-artifact-auditor-proxy container is running
✓ Proxy health endpoint responding
[15d] Deterministic artifact audit test (fixture-based)
✓ Artifact audit completed (ok: true)
✓ Response contains audit_summary
✓ Response contains compliance_score
[15e] Checking artifacts directory structure
✓ /data/artifacts exists
✓ Wrote validation artifact to /data/artifacts/validation/agent-artifact-auditor-proxy/...
Artifact Auditor Agent check complete (optional - does not block)
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
    "task_type": "ARTIFACT_AUDIT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "artifact_source": "direct",
      "artifact_content": "This is a randomized controlled trial...",
      "reporting_standard": "CONSORT"
    }
  }'
```

**Expected Response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-artifact-auditor-proxy",
  "agent_url": "http://agent-artifact-auditor-proxy:8000",
  "request_id": "test-001"
}
```

---

## Files Changed

### Created (7 files)

1. `services/agents/agent-artifact-auditor-proxy/Dockerfile`
2. `services/agents/agent-artifact-auditor-proxy/requirements.txt`
3. `services/agents/agent-artifact-auditor-proxy/app/__init__.py`
4. `services/agents/agent-artifact-auditor-proxy/app/config.py`
5. `services/agents/agent-artifact-auditor-proxy/app/main.py`
6. `services/agents/agent-artifact-auditor-proxy/README.md`
7. `docs/agents/agent-artifact-auditor-proxy/wiring.md` (this file)

### Modified (4 files)

1. `services/orchestrator/src/routes/ai-router.ts` (+1 line)
   - Added `ARTIFACT_AUDIT: 'agent-artifact-auditor-proxy'` task type mapping
2. `docker-compose.yml` (+40 lines)
   - Added `agent-artifact-auditor-proxy` service
   - Updated `AGENT_ENDPOINTS_JSON` to include artifact auditor
3. `scripts/hetzner-preflight.sh` (+1 line)
   - Added `LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID` to required env vars
4. `scripts/stagewise-smoke.sh` (+120 lines)
   - Added optional artifact auditor validation (CHECK_ARTIFACT_AUDITOR=1)
   - Added deterministic fixture-based audit test
5. `scripts/lib/agent_endpoints_required.txt` (+1 line)
   - Added `agent-artifact-auditor-proxy` to mandatory agents list

**Total Changes:** 11 files, ~160 lines added

---

## Troubleshooting

### Issue: 503 on /health/ready

**Cause:** `LANGSMITH_API_KEY` not set or LangSmith API unreachable

**Fix:**
```bash
echo "LANGSMITH_API_KEY=<your-langsmith-api-key>" >> .env
docker compose up -d --force-recreate agent-artifact-auditor-proxy orchestrator
```

### Issue: Routing failures

**Symptom:** `UNSUPPORTED_TASK_TYPE` or `AGENT_NOT_CONFIGURED` error

**Fix:** Verify task type and endpoint registration
```bash
# Check router mapping
docker compose exec orchestrator grep "ARTIFACT_AUDIT" /app/src/routes/ai-router.ts

# Check AGENT_ENDPOINTS_JSON
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep artifact
```

### Issue: Proxy container not running

**Check:**
```bash
docker compose ps agent-artifact-auditor-proxy
docker compose logs agent-artifact-auditor-proxy
```

**Restart:**
```bash
docker compose up -d --force-recreate agent-artifact-auditor-proxy
```

### Issue: Empty outputs or audit failures

**Cause:** Invalid LangSmith agent ID or input schema mismatch

**Fix:**
1. Verify agent ID in LangSmith UI
2. Update `LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID` in .env
3. Check input schema matches agent expectations
4. Review proxy logs: `docker compose logs agent-artifact-auditor-proxy`

### Issue: Deterministic test fails in smoke

**Cause:** Agent requires external tools (GitHub, Google Docs) even in DEMO mode

**Fix:** Ensure fixture test uses `artifact_source: "direct"` and `artifact_content` with inline text

---

## Related Documentation

- **Agent Config:** `services/agents/agent-artifact-auditor/AGENTS.md`
- **Subagents:** `services/agents/agent-artifact-auditor/subagents/*/AGENTS.md`
- **Proxy README:** `services/agents/agent-artifact-auditor-proxy/README.md`
- **Agent Briefing:** `AGENT_ARTIFACT_AUDITOR_BRIEFING.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`

---

## agentKey Reference

**agentKey:** `agent-artifact-auditor-proxy`  
**Compose Service Name:** `agent-artifact-auditor-proxy`  
**TaskType(s):** `ARTIFACT_AUDIT`  
**Health Endpoint:** `/health`  
**Readiness Endpoint:** `/health/ready`

---

## Required Environment Variables (Names Only)

- `LANGSMITH_API_KEY` - LangSmith API access (required for all LangSmith proxies)
- `LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID` - Agent UUID from LangSmith (required)
- `WORKER_SERVICE_TOKEN` - Internal dispatch authentication (required for orchestrator)

**Optional (enhances functionality):**
- `GITHUB_TOKEN` - For GitHub artifact retrieval
- `GOOGLE_DOCS_API_KEY` - For Google Docs audit reports
- `GOOGLE_SHEETS_API_KEY` - For audit tracker logging

---

## Validation Commands

### Local

```bash
# Build and start
docker compose build agent-artifact-auditor-proxy
docker compose up -d agent-artifact-auditor-proxy orchestrator

# Verify health
docker compose exec agent-artifact-auditor-proxy curl -f http://localhost:8000/health
docker compose exec agent-artifact-auditor-proxy curl -f http://localhost:8000/health/ready

# Run preflight
./researchflow-production-main/scripts/hetzner-preflight.sh

# Run smoke test (targeted)
CHECK_ARTIFACT_AUDITOR=1 DEV_AUTH=true ./researchflow-production-main/scripts/stagewise-smoke.sh

# Run smoke test (all agents)
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./researchflow-production-main/scripts/stagewise-smoke.sh
```

### Hetzner (Production)

```bash
# On ROSflow2 server
cd /opt/researchflow/researchflow-production-main

# Same commands as local (use server paths)
./scripts/hetzner-preflight.sh
CHECK_ARTIFACT_AUDITOR=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Next Steps

### Immediate

1. ✅ **Proxy service created**
2. ✅ **Docker Compose wiring complete**
3. ✅ **Router registration complete**
4. ✅ **Validation hooks added**
5. ✅ **Mandatory agent list updated**
6. ✅ **Wiring documentation created**
7. ⏳ **Deploy to ROSflow2**
8. ⏳ **Run preflight validation**
9. ⏳ **Optional smoke test**
10. ⏳ **Update AGENT_INVENTORY.md**

### Future Enhancements

1. Add retry logic for LangSmith API timeouts
2. Implement caching for guideline checklists
3. Add rate limiting for LangSmith API
4. Create integration test: Manuscript Writer → Artifact Auditor
5. Add monitoring for audit success rate
6. Integrate with GitHub PR workflow (auto-comment on manuscripts)

---

**Wiring Date:** 2026-02-08  
**Status:** ✅ **COMPLETE**  
**Branch:** feat/import-dissemination-formatter  
**Next Action:** Deploy to ROSflow2 and run validation
