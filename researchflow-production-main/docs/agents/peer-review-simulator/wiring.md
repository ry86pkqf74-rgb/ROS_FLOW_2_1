# Peer Review Simulator - Deployment Wiring Guide

**Agent:** agent-peer-review-simulator  
**Type:** LangSmith Cloud Proxy (Stage 13)  
**Status:** ✅ Wired for Deployment  
**Branch:** chore/inventory-capture  
**Date:** 2026-02-08

---

## Summary

The Peer Review Simulator agent has been wired for deployment as a FastAPI proxy service that wraps the LangSmith cloud-hosted agent. It is integrated into Stage 13 (Internal Review) with a feature flag and validated by preflight/smoke tests.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy

```
Orchestrator → AI Router → agent-peer-review-simulator-proxy → LangSmith API
                              (FastAPI container)                    ↓
                                                             Multi-Persona Review:
                                                             - Critique Worker
                                                             - Readability Reviewer
                                                             - Literature Checker
                                                             - Checklist Auditor
                                                             - Revision Worker
```

### Components

1. **Config Bundle** (reference only):
   - Path: `services/agents/agent-peer-review-simulator/`
   - Contents: `AGENTS.md`, `config.json`, `tools.json`, `subagents/`
   - Purpose: LangSmith agent definition (not executed locally)

2. **Proxy Service** (deployed):
   - Path: `services/agents/agent-peer-review-simulator-proxy/`
   - Type: FastAPI + Docker
   - Endpoints: `/health`, `/health/ready`, `/agents/run/sync`, `/agents/run/stream`

---

## Integration Points

### 1. Orchestrator Router

**File:** `services/orchestrator/src/routes/ai-router.ts`

**Change:**
```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ...
  PEER_REVIEW_SIMULATION: 'agent-peer-review-simulator',  // LangSmith-hosted peer review simulator (Stage 13)
};
```

**Effect:** Router can dispatch `PEER_REVIEW_SIMULATION` tasks to the proxy service

### 2. Stage 13 Integration

**File:** `services/worker/src/workflow_engine/stages/stage_13_internal_review.py`

**Feature Flag:** `ENABLE_PEER_REVIEW_SIMULATOR`

**Usage:**
```python
# In job config or stage context:
{
  "ENABLE_PEER_REVIEW_SIMULATOR": true,  # Enable LangSmith peer review
  "peer_review_personas": ["methodologist", "statistician", "ethics_reviewer"],
  "study_type": "RCT",
  "enable_peer_review_iteration": true,
  "max_peer_review_cycles": 3
}
```

**Behavior:**
- **When `true`**: Calls LangSmith Peer Review Simulator via AI router dispatch
- **When `false`** (default): Uses standard bridge service peer-review
- **On failure**: Falls back to standard review with warning

**Artifact Paths:**
```
/data/artifacts/{job_id}/stage_13/peer_review/
├── peer_review_report.json       # Full review report
├── checklists.json                # CONSORT/STROBE/etc compliance
└── response_letter.md             # Draft response to reviewers
```

### 3. Environment Variables

**Required:**
- `LANGSMITH_API_KEY` - LangSmith API key (starts with `lsv2_pt_`)
- `LANGSMITH_PEER_REVIEW_AGENT_ID` - LangSmith assistant UUID

**Optional:**
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: 600 (10 minutes)

**Location:** `researchflow-production-main/.env`

**Example:**
```bash
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PEER_REVIEW_AGENT_ID=550e8400-e29b-41d4-a716-446655440000
```

### 4. AGENT_ENDPOINTS_JSON

**Registration:**
```json
{
  "agent-peer-review-simulator": "http://agent-peer-review-simulator-proxy:8000"
}
```

**Set in orchestrator environment.**

---

## Deployment Steps

### Prerequisites

1. ✅ LangSmith account with API access
2. ✅ Peer Review Simulator agent deployed in LangSmith
3. ✅ LangSmith API key (`LANGSMITH_API_KEY`)
4. ✅ Agent ID from LangSmith dashboard

### Deploy on ROSflow2 (Hetzner)

```bash
# 1. SSH to server
ssh user@rosflow2
cd /opt/researchflow/researchflow-production-main

# 2. Pull latest code (branch: chore/inventory-capture)
git fetch --all --prune
git checkout chore/inventory-capture
git pull --ff-only

# 3. Set environment variables
cat >> .env <<EOF
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_PEER_REVIEW_AGENT_ID=<uuid-from-langsmith>
EOF

# 4. Update AGENT_ENDPOINTS_JSON
# Add "agent-peer-review-simulator": "http://agent-peer-review-simulator-proxy:8000"

# 5. Build and start proxy service
docker compose build agent-peer-review-simulator-proxy
docker compose up -d agent-peer-review-simulator-proxy

# 6. Wait for healthy
sleep 15

# 7. Verify proxy health
docker compose ps agent-peer-review-simulator-proxy
docker compose exec agent-peer-review-simulator-proxy curl -f http://localhost:8000/health

# 8. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 9. Run validation
CHECK_PEER_REVIEW=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**Checks:**
- ✅ `LANGSMITH_API_KEY` present in orchestrator environment
- ✅ Task type `PEER_REVIEW_SIMULATION` registered in ai-router.ts

**Expected Output:**
```
  Peer Review Simulator            ✓ PASS - LANGSMITH_API_KEY configured
  Peer Review Router               ✓ PASS - task type registered
```

### Smoke Test (Optional: CHECK_PEER_REVIEW=1)

**Script:** `scripts/stagewise-smoke.sh`

**Checks:**
- LANGSMITH_API_KEY configuration
- Router dispatch to `agent-peer-review-simulator`
- Artifact directory structure

**Usage:**
```bash
CHECK_PEER_REVIEW=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 ./scripts/stagewise-smoke.sh
```

**Expected Output:**
```
[12] Peer Review Simulator Check (optional - LangSmith-based)
[12a] Checking LANGSMITH_API_KEY configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
[12b] POST /api/ai/router/dispatch (PEER_REVIEW_SIMULATION)
Router dispatch OK: routed to agent-peer-review-simulator
✓ Correctly routed to agent-peer-review-simulator
[12c] Checking artifacts directory structure
✓ /data/artifacts exists
✓ Created validation artifact directory
Peer Review Simulator check complete (optional - does not block)
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
    "task_type": "PEER_REVIEW_SIMULATION",
    "request_id": "test-peer-review-001",
    "mode": "DEMO",
    "inputs": {
      "manuscript": {
        "title": "Test Study Title",
        "abstract": "Background: ... Methods: ... Results: ... Conclusions: ...",
        "introduction": "...",
        "methods": "...",
        "results": "...",
        "discussion": "..."
      },
      "personas": ["methodologist", "statistician"],
      "study_type": "RCT",
      "max_cycles": 1
    }
  }'
```

**Expected Response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-peer-review-simulator",
  "agent_url": "http://agent-peer-review-simulator-proxy:8000",
  "budgets": {},
  "request_id": "test-peer-review-001"
}
```

---

## Common Failure Modes

### 1. 503 Service Unavailable

**Symptoms:**
- `/health/ready` returns 503
- "LANGSMITH_API_KEY not configured" error

**Cause:** Environment variable missing

**Fix:**
```bash
# Add to .env
echo "LANGSMITH_API_KEY=<your-langsmith-api-key>" >> .env
docker compose up -d --force-recreate agent-peer-review-simulator-proxy
```

### 2. AGENT_NOT_CONFIGURED

**Symptoms:**
- Router dispatch returns `AGENT_NOT_CONFIGURED`
- Agent name resolves but URL not found

**Cause:** `agent-peer-review-simulator` not in AGENT_ENDPOINTS_JSON

**Fix:**
```bash
# Update AGENT_ENDPOINTS_JSON in orchestrator .env
# Add: "agent-peer-review-simulator": "http://agent-peer-review-simulator-proxy:8000"
docker compose up -d --force-recreate orchestrator
```

### 3. UNSUPPORTED_TASK_TYPE

**Symptoms:**
- Router returns `UNSUPPORTED_TASK_TYPE`
- `PEER_REVIEW_SIMULATION` not recognized

**Cause:** Router not updated with task type mapping

**Fix:**
```bash
# Verify ai-router.ts contains PEER_REVIEW_SIMULATION mapping
grep "PEER_REVIEW_SIMULATION" services/orchestrator/src/routes/ai-router.ts

# If missing, pull latest code
git pull origin chore/inventory-capture
docker compose build orchestrator
docker compose up -d orchestrator
```

### 4. Timeout Errors

**Symptoms:**
- Request times out after 10 minutes
- LangSmith agent still processing

**Cause:** Comprehensive review with multiple iterations exceeds timeout

**Fix:**
```bash
# Increase timeout in proxy
# Edit services/agents/agent-peer-review-simulator-proxy/app/config.py
# Set: langsmith_timeout_seconds: int = 1200  # 20 minutes

# Or reduce iteration cycles in job config
# "max_peer_review_cycles": 1
```

### 5. Stage 13 Fallback

**Symptoms:**
- Stage 13 completes but uses standard review instead of simulator
- Warning: "LangSmith peer review failed: ..."

**Cause:** Simulator call failed, fallback activated

**Diagnosis:**
```bash
# Check worker logs
docker compose logs worker | grep "Peer Review Simulator"

# Check orchestrator logs for dispatch errors
docker compose logs orchestrator | grep "PEER_REVIEW_SIMULATION"

# Verify proxy is healthy
curl http://agent-peer-review-simulator-proxy:8000/health/ready
```

---

## Files Changed

### Created (6 files):
1. `services/agents/agent-peer-review-simulator-proxy/Dockerfile`
2. `services/agents/agent-peer-review-simulator-proxy/requirements.txt`
3. `services/agents/agent-peer-review-simulator-proxy/app/__init__.py`
4. `services/agents/agent-peer-review-simulator-proxy/app/config.py`
5. `services/agents/agent-peer-review-simulator-proxy/app/main.py`
6. `services/agents/agent-peer-review-simulator-proxy/README.md`

### Modified (4 files):
1. `services/orchestrator/src/routes/ai-router.ts` (+1 line)
   - Added `PEER_REVIEW_SIMULATION` task type mapping
2. `services/worker/src/workflow_engine/stages/stage_13_internal_review.py` (+80 lines)
   - Added feature flag integration and artifact saving
3. `scripts/hetzner-preflight.sh` (+15 lines)
   - Added Peer Review Simulator health checks
4. `scripts/stagewise-smoke.sh` (+60 lines)
   - Added optional peer review validation (CHECK_PEER_REVIEW=1)

### Documentation (1 file):
5. `docs/agents/peer-review-simulator/wiring.md` (this file)

**Total Changes:**
- Lines added: ~350
- Files created: 7
- Files modified: 4
- No secrets committed: ✅

---

## Related Documentation

- **Proxy README:** `services/agents/agent-peer-review-simulator-proxy/README.md`
- **Agent Config:** `services/agents/agent-peer-review-simulator/INTEGRATION_GUIDE.md`
- **LangSmith Architecture:** `LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
- **Stage 13 Docs:** `docs/stages/stage_13_internal_review.md` (if exists)

---

## Next Steps

### Immediate (Deploy):
1. ⏳ Deploy proxy to ROSflow2
2. ⏳ Run preflight validation
3. ⏳ Optional: Run smoke test with CHECK_PEER_REVIEW=1

### Short-Term (Testing):
4. ⏳ Test Stage 13 with feature flag enabled
5. ⏳ Validate artifact generation
6. ⏳ Review LangSmith execution traces
7. ⏳ Compare output quality vs standard review

### Long-Term (Production):
8. ⏳ Monitor LangSmith API costs
9. ⏳ Add retry logic for transient failures
10. ⏳ Create integration test: Manuscript → Peer Review → Revisions
11. ⏳ Document best practices for persona selection
12. ⏳ Add caching for duplicate manuscripts

---

## Support

**Issues:** Report in GitHub Issues with `peer-review-simulator` label  
**Logs:** `docker compose logs agent-peer-review-simulator-proxy`  
**LangSmith Dashboard:** https://smith.langchain.com/  
**Contact:** Agent fleet coordination team

---

**Status:** ✅ **WIRING COMPLETE - READY FOR DEPLOYMENT**  
**Date:** 2026-02-08  
**Branch:** chore/inventory-capture
