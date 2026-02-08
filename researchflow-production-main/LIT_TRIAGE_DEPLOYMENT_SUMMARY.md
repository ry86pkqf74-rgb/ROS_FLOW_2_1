# Literature Triage Agent - Deployment Summary

**Branch:** `chore/inventory-capture`  
**Commit:** c1a42c1  
**Date:** 2026-02-07  
**Status:** ✅ Ready for Deployment

---

## Executive Summary

The Literature Triage Agent (`agent-lit-triage`) has been fully integrated into the ResearchFlow production stack and is ready for deployment on Hetzner (ROSflow2). This document provides a complete deployment checklist and validation guide.

**Key Changes:**
1. ✅ Added agent service to `docker-compose.yml`
2. ✅ Registered `LIT_TRIAGE` task type in AI router
3. ✅ Updated `AGENT_ENDPOINTS_JSON` environment variable
4. ✅ Added preflight checks to `hetzner-preflight.sh`
5. ✅ Added smoke test to `stagewise-smoke.sh`
6. ✅ Created JSON schema (`docs/schemas/agent-lit-triage-io.json`)
7. ✅ Updated documentation (`AGENT_INVENTORY.md`, `hetzner-fullstack.md`)

---

## Files Changed

### Docker Compose Configuration
- **File:** `docker-compose.yml`
- **Changes:**
  - Added `agent-lit-triage` service definition (lines 827-854)
  - Updated `AGENT_ENDPOINTS_JSON` in orchestrator environment (line 184)
  - Service uses `build` context (Dockerfile at `services/agents/agent-lit-triage/Dockerfile`)
  - Internal networking only (`backend` + `frontend` for Exa API access)
  - Health check: `GET /health` on port 8000
  - Environment: `EXA_API_KEY`, `LANGCHAIN_API_KEY`, `GOVERNANCE_MODE`, etc.

### Orchestrator Router
- **File:** `services/orchestrator/src/routes/ai-router.ts`
- **Changes:**
  - Added `LIT_TRIAGE: 'agent-lit-triage'` to `TASK_TYPE_TO_AGENT` mapping (line 245)
  - Router now dispatches `LIT_TRIAGE` tasks to `http://agent-lit-triage:8000`

### Deployment Scripts
1. **Preflight Script:** `scripts/hetzner-preflight.sh`
   - Added Literature Triage Agent health check section (lines 268-298)
   - Validates container status, health endpoint, and router registration

2. **Smoke Test Script:** `scripts/stagewise-smoke.sh`
   - Added optional triage validation (step 9, lines 182-284)
   - Controlled by `CHECK_LIT_TRIAGE=1` environment variable
   - Tests: health, router dispatch, direct agent call

### Documentation
1. **Agent Inventory:** `AGENT_INVENTORY.md`
   - Updated agent count (14 → 15 microservice agents)
   - Added agent-lit-triage to Section 1.4 (Governance & Policy Agents)
   - Added Appendix C: Agent-Lit-Triage Quick Reference

2. **Deployment Guide:** `docs/deployment/hetzner-fullstack.md`
   - Added "Literature Triage Agent" section with health checks, validation, and integration guide

3. **JSON Schema:** `docs/schemas/agent-lit-triage-io.json`
   - Complete input/output schema for `LIT_TRIAGE` task type
   - Includes examples and validation rules

---

## Service Details

### Container Information
- **Service Name:** `agent-lit-triage`
- **Container Name:** `researchflow-agent-lit-triage`
- **Internal URL:** `http://agent-lit-triage:8000`
- **Exposed Ports:** None (internal-only via Docker networks)
- **Networks:** `backend` (internal), `frontend` (for Exa API calls)
- **Health Endpoint:** `GET /health` → `{"status": "ok"}`

### Environment Variables

**Required:** None (agent works with mocks by default)

**Optional (for enhanced functionality):**
```bash
EXA_API_KEY=                      # Exa semantic search (optional)
LANGCHAIN_API_KEY=                # LangSmith tracing (optional)
LANGCHAIN_PROJECT=researchflow-lit-triage
LANGCHAIN_TRACING_V2=false        # Enable/disable tracing
GOVERNANCE_MODE=DEMO              # DEMO or LIVE
LOG_LEVEL=INFO                    # Logging verbosity
```

### API Endpoints

1. **POST /agents/run/sync** - Synchronous triage execution
2. **POST /agents/run/stream** - Streaming triage (SSE)
3. **GET /health** - Health check
4. **GET /health/ready** - Readiness check

---

## Deployment Steps

### 1. Update Repository

```bash
# SSH into ROSflow2
ssh root@178.156.139.210

# Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# Pull latest code (chore/inventory-capture branch)
git fetch origin
git checkout chore/inventory-capture
git pull
```

### 2. Update Environment Variables

```bash
# Edit .env file
nano .env

# Add to AGENT_ENDPOINTS_JSON (ensure it's a single line):
AGENT_ENDPOINTS_JSON='{"agent-stage2-lit":"http://agent-stage2-lit:8000","agent-stage2-screen":"http://agent-stage2-screen:8000","agent-stage2-extract":"http://agent-stage2-extract:8000","agent-stage2-synthesize":"http://agent-stage2-synthesize:8000","agent-lit-retrieval":"http://agent-lit-retrieval:8000","agent-lit-triage":"http://agent-lit-triage:8000","agent-policy-review":"http://agent-policy-review:8000","agent-rag-ingest":"http://agent-rag-ingest:8000","agent-rag-retrieve":"http://agent-rag-retrieve:8000","agent-verify":"http://agent-verify:8000","agent-intro-writer":"http://agent-intro-writer:8000","agent-methods-writer":"http://agent-methods-writer:8000","agent-evidence-synthesis":"http://agent-evidence-synthesis:8000"}'

# Optional: Add Exa API key for real semantic search
EXA_API_KEY=your_exa_api_key_here

# Optional: Add LangSmith tracing
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_TRACING_V2=true
```

### 3. Build and Deploy

```bash
# Build the new agent image
docker compose build agent-lit-triage

# Restart orchestrator to pick up new AGENT_ENDPOINTS_JSON
docker compose up -d --force-recreate orchestrator

# Start the triage agent
docker compose up -d agent-lit-triage

# Wait for services to become healthy
sleep 30
```

### 4. Run Preflight Checks

```bash
# Run preflight validation
chmod +x scripts/hetzner-preflight.sh
./scripts/hetzner-preflight.sh

# Expected output:
# ✓ Literature Triage Agent: container running
# ✓ Literature Triage Health: HTTP 200
# ✓ Literature Triage Router: registered in AGENT_ENDPOINTS_JSON
```

### 5. Run Smoke Tests

```bash
# Run smoke test with triage validation
CHECK_LIT_TRIAGE=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh

# Expected output:
# [9] Literature Triage Agent Check (optional)
# [9a] GET agent-lit-triage /health
# Literature Triage Agent health OK
# [9b] POST /api/ai/router/dispatch (LIT_TRIAGE)
# ✓ Correctly routed to agent-lit-triage
# [9c] POST /agents/run/sync (direct agent call)
# ✓ Response contains papers field
# ✓ Response contains stats field
# ✓ Tier 1 (Must Read) papers: N
# ✓ Total ranked papers: N
```

---

## Validation Commands

### Container Health
```bash
# Check container status
docker compose ps agent-lit-triage

# View logs
docker compose logs -f agent-lit-triage

# Exec into container
docker compose exec agent-lit-triage sh
```

### Health Endpoint
```bash
# Via docker exec (recommended - agent is internal-only)
docker compose exec agent-lit-triage curl -f http://localhost:8000/health

# Expected: {"status":"ok"}
```

### Router Registration
```bash
# Check AGENT_ENDPOINTS_JSON
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep lit-triage

# Expected: "agent-lit-triage": "http://agent-lit-triage:8000"
```

### Direct Agent Call
```bash
docker compose exec agent-lit-triage sh -c '
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '"'"'{
    "task_type": "LIT_TRIAGE",
    "request_id": "manual-test-001",
    "mode": "DEMO",
    "inputs": {
      "query": "cancer immunotherapy",
      "date_range_days": 730,
      "min_results": 5
    }
  }'"'"'
'

# Expected fields in response:
# - ok: true
# - outputs.papers: array of ranked papers
# - outputs.stats: {found, ranked}
# - outputs.tier1_count, tier2_count, tier3_count
```

### Router Dispatch
```bash
# Get dev token
TOKEN=$(curl -sS -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: test-user" | jq -r '.accessToken')

# Dispatch via router
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "LIT_TRIAGE",
    "request_id": "router-test-001",
    "mode": "DEMO",
    "inputs": {"query": "immunotherapy"}
  }'

# Expected: {"dispatch_type":"agent","agent_name":"agent-lit-triage",...}
```

---

## Known Limitations

1. **API Keys Optional:** Agent works with mock results when `EXA_API_KEY` is not configured
2. **Internal-Only:** No external port exposure (access via docker exec or orchestrator router)
3. **Stage 2 Integration:** Manual toggle required (`ENABLE_LIT_TRIAGE=true`)
4. **Mock Mode:** Without Exa API key, agent returns synthetic rankings

---

## Rollback Procedure

If issues occur after deployment:

```bash
# 1. Stop the agent
docker compose stop agent-lit-triage

# 2. Remove from AGENT_ENDPOINTS_JSON
nano .env
# Remove "agent-lit-triage":"http://agent-lit-triage:8000" from JSON

# 3. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 4. Optionally remove container
docker compose rm -f agent-lit-triage
```

---

## Success Criteria

✅ **Deployment is successful when:**
1. Container `agent-lit-triage` is running and healthy
2. Health endpoint returns `{"status": "ok"}`
3. Router recognizes `LIT_TRIAGE` task type
4. Direct agent call returns valid ranked papers
5. Router dispatch routes to `agent-lit-triage`
6. Preflight script reports all checks passing
7. Smoke test completes without errors

---

## Support Resources

- **Agent README:** `services/agents/agent-lit-triage/README.md`
- **Integration Guide:** `services/agents/agent-lit-triage/WORKFLOW_INTEGRATION.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
- **JSON Schema:** `docs/schemas/agent-lit-triage-io.json`
- **Deployment Guide:** `docs/deployment/hetzner-fullstack.md`
- **Commit:** c1a42c1 (feat(agent-lit-triage): import LangSmith Literature Triage Agent)

---

**Deployment Checklist:**
- [ ] Code pulled from `chore/inventory-capture` branch
- [ ] `.env` updated with `AGENT_ENDPOINTS_JSON` including `agent-lit-triage`
- [ ] Agent image built (`docker compose build agent-lit-triage`)
- [ ] Orchestrator restarted to load new endpoints
- [ ] Agent container started and healthy
- [ ] Preflight checks pass (all ✓)
- [ ] Smoke tests pass (optional `CHECK_LIT_TRIAGE=1`)
- [ ] Router dispatch test successful
- [ ] Direct agent call returns valid output

**Status:** ✅ Ready for Production Deployment
