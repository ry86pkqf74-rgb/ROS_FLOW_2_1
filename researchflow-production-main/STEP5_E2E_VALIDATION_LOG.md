# Step 5: E2E Validation & Compose Merge - Validation Log

**Date:** 2026-02-10  
**Purpose:** Execute full end-to-end validation of orchestrator → router → agent dispatch path, verify docker-compose integration, and complete Step 4 deferred tests.

---

## Overview

Step 5 combines:
1. **Compose Merge:** Ensure all agent services are defined in docker-compose.yml
2. **Service Integration:** Verify orchestrator can reach agents via internal network
3. **E2E Dispatch Test:** Test full path: API → orchestrator → router → agent → response
4. **Step 4 Deferred Tests:** Execute curl tests that were blocked in Step 4

---

## A) Pre-Flight: What "Step 5" Means in This Repo

Per MILESTONE1_STATUS.md and STEP4_TEST_COMMANDS.md, Step 5 includes:

### 1. Compose Merge (Primary Goal)
- ✅ All 29 agent services already defined in docker-compose.yml
- ✅ `AGENT_ENDPOINTS_JSON` environment variable already configured in orchestrator service
- ✅ Services are on correct networks (backend for inter-service communication)
- ✅ Health checks defined for all agents

**Status:** ✅ **Already Complete** - docker-compose.yml was reviewed and contains:
- All Stage 2 agents (lit, screen, extract, synthesize)
- All core agents (lit-retrieval, lit-triage, policy-review, rag-ingest, rag-retrieve, verify)
- All section writer agents (intro, methods, results, discussion)
- All LangSmith proxy agents (29 total services)
- Proper network configuration (backend + frontend as needed)
- Health checks for all services

### 2. Wiring Validation
- ⏳ Pending: Verify AGENT_ENDPOINTS_JSON keys match ai-router.ts TASK_TYPE_TO_AGENT mapping
- ⏳ Pending: Confirm agent URLs resolve to correct service names

### 3. E2E Smoke Test
- ⏳ Pending: Start orchestrator + agent-stage2-lit
- ⏳ Pending: Send Stage 2 execute request
- ⏳ Pending: Verify router dispatch succeeds
- ⏳ Pending: Verify agent returns structured response

---

## B) Service Startup & Health Validation

### 1. Start Core Services

**Commands:**
```bash
# From researchflow-production-main/
docker compose up postgres redis orchestrator -d
sleep 15
docker compose ps
```

**Expected Result:**
- postgres: Up (healthy)
- redis: Up (healthy)
- orchestrator: Up (healthy)

**Status:** ⏳ **Pending Execution**

**Blockers from Step 4:**
- Orchestrator image pull failed (GHCR authentication required)
- Alternative: Build locally with `docker compose build orchestrator`

### 2. Start Agent Services

**Commands:**
```bash
# Start one agent for minimal test
docker compose up agent-stage2-lit -d
sleep 10
docker compose ps agent-stage2-lit

# Verify health
docker compose exec agent-stage2-lit curl -f http://localhost:8000/health
```

**Expected Result:**
```json
{
  "status": "healthy",
  "service": "agent-stage2-lit"
}
```

**Status:** ⏳ **Pending Execution**

---

## C) Step 4 Deferred Tests (Now Executable)

### Test 1: Minimal Request (All Defaults)

**Command:**
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "job_id": "<uuid>",
  "stage": 2,
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Stage 2 execution job has been queued",
  "routing": {
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "domain_id": "clinical"
  },
  "normalized_inputs": {
    "databases": ["pubmed"],
    "max_results": 25,
    "language": "en",
    "dedupe": true,
    "require_abstract": true
  }
}
```

**Status:** ⏳ **Pending Execution**

### Test 2: Custom Inputs

**Command:**
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "mode": "LIVE",
    "risk_tier": "PHI",
    "domain_id": "clinical",
    "inputs": {
      "databases": ["pubmed", "semantic_scholar"],
      "max_results": 50
    }
  }'
```

**Expected:** `routing` object matches custom values, `normalized_inputs` contains custom values.

**Status:** ⏳ **Pending Execution**

### Test 3: Validation Error (max_results Too High)

**Command:**
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "max_results": 500
    }
  }'
```

**Expected:** 400 Bad Request with validation error mentioning `max_results`.

**Status:** ⏳ **Pending Execution**

### Test 4: Job Status Check

**Command:**
```bash
# Get job_id from Test 1 response
JOB_ID="<from-test-1>"

curl -X GET http://localhost:3001/api/workflow/stages/2/jobs/$JOB_ID/status \
  -H "Authorization: Bearer test-token"
```

**Expected:** Job data includes `mode`, `risk_tier`, `domain_id`, and `inputs` fields.

**Status:** ⏳ **Pending Execution**

---

## D) E2E Dispatch Path Validation

### Test 5: Router Dispatch to Agent

**Objective:** Verify full path: orchestrator → AI router → agent → response

**Commands:**
```bash
# 1. Check AGENT_ENDPOINTS_JSON configuration
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool

# 2. Verify agent-stage2-lit is reachable from orchestrator
docker compose exec orchestrator curl -f http://agent-stage2-lit:8000/health

# 3. Test router dispatch endpoint directly
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE"
  }'
```

**Expected Response:**
```json
{
  "agent_name": "agent-stage2-lit",
  "agent_url": "http://agent-stage2-lit:8000",
  "budgets": {},
  "rag_plan": null
}
```

**Status:** ⏳ **Pending Execution**

### Test 6: Full E2E Agent Call

**Objective:** Verify orchestrator can successfully call agent and receive response

**Command:**
```bash
# This tests the worker path that calls AgentClient.postSync
# Monitor logs to see routing logic
docker compose logs orchestrator -f &

# Execute Stage 2 job (from Test 1) and watch logs for:
# - "Stage 2 job dispatched"
# - "Calling agent at http://agent-stage2-lit:8000"
# - Agent response logged
```

**Expected Log Pattern:**
```
[Stage 2] Job <uuid> dispatched for workflow <uuid> (DEMO/NON_SENSITIVE/clinical)
[AgentClient] Calling agent-stage2-lit at http://agent-stage2-lit:8000/execute
[AgentClient] Agent responded with status: success
```

**Status:** ⏳ **Pending Execution**

---

## E) Preflight + Smoke Scripts

### 1. Run Hetzner Preflight Script (if applicable locally)

**Command:**
```bash
# From researchflow-production-main/
bash scripts/hetzner-preflight.sh
```

**Purpose:** Validates:
- AGENT_ENDPOINTS_JSON is valid JSON
- All expected agents are configured
- Environment variables are set

**Status:** ⏳ **Pending Execution** (may need adaptation for local environment)

### 2. Run Stagewise Smoke Test (if applicable)

**Command:**
```bash
# From researchflow-production-main/
bash scripts/stagewise-smoke.sh
```

**Purpose:** Basic smoke test of agent routing.

**Status:** ⏳ **Pending Execution** (may need adaptation for local environment)

---

## F) Known Issues & Workarounds

### Issue 1: Orchestrator Image Pull Unauthorized

**Problem:** Cannot pull `ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator:main` without authentication.

**Workaround:**
```bash
# Option A: Authenticate with GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Option B: Build locally
cd researchflow-production-main
docker compose build orchestrator
docker tag researchflow-production-main-orchestrator:latest ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator:main
```

**Status:** ⏳ **Resolution Pending**

### Issue 2: Migration 020 (edit_sessions) Blocked

**Problem:** Migration 020 requires `manuscript_branches` table which doesn't exist.

**Impact:** The two DB-backed tests for edit_sessions will fail/skip.

**Resolution:** This is a separate feature unrelated to Stage 2 routing. Migration 020 validation deferred to manuscript feature implementation.

**Status:** ⚠️ **Acknowledged - Not Blocking Step 5**

---

## G) Success Criteria for Step 5

### Minimum Success (Core Functionality)
- ✅ Orchestrator service starts successfully
- ✅ At least one agent service (agent-stage2-lit) starts successfully
- ✅ Step 4 Test 1 (minimal request) succeeds with correct response format
- ✅ Step 4 Test 3 (validation error) returns 400 as expected
- ✅ Router dispatch endpoint returns correct agent URL
- ✅ Orchestrator logs show successful agent routing

### Full Success (Complete Validation)
- ✅ All Step 4 curl tests pass
- ✅ Job status endpoint returns complete payload
- ✅ E2E agent call succeeds (orchestrator → agent → response)
- ✅ Logs show routing metadata in correct format
- ✅ No errors in orchestrator logs during tests

### Deferred (Not Required for Step 5)
- ⚠️ Migration 020 validation (blocked by missing prerequisite)
- ⚠️ DB-backed test execution (depends on edit_sessions table)
- ⚠️ All 29 agents running simultaneously (resource intensive, not required for routing validation)

---

## H) Next Steps After Step 5

1. **Document Results:** Update this log with actual test outputs
2. **Create Summary:** Consolidate findings into MILESTONE1_COMPLETION.md
3. **Plan Step 6:** If applicable, define next milestone (multi-agent orchestration, etc.)
4. **Update Status Docs:** Mark Step 5 as complete in MILESTONE1_STATUS.md

---

## I) Commands Quick Reference

```bash
# Start services
cd researchflow-production-main
docker compose up postgres redis orchestrator agent-stage2-lit -d

# Check status
docker compose ps

# Run Step 4 tests (paste commands from Section C)

# View logs
docker compose logs orchestrator --tail=100 -f

# Cleanup
docker compose down
```

---

**Status:** ⏳ **Awaiting Execution - Services Not Yet Started**  
**Last Updated:** 2026-02-10  
**Next Action:** Build/start orchestrator service and execute validation tests
