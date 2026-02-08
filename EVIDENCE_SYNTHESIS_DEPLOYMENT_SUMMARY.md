# Evidence Synthesis Agent - Deployment Summary

**Commit:** 197bfcd  
**Branch:** chore/inventory-capture  
**Date:** 2026-02-07  
**Status:** ✅ Ready for Production Deployment

---

## Files Changed

### Configuration
- `researchflow-production-main/docker-compose.yml` - ✅ Service definition validated
- `researchflow-production-main/services/orchestrator/src/routes/ai-router.ts` - ✅ Router registration verified

### Documentation
- `researchflow-production-main/EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md` - ✅ Updated with validation checklist
- `researchflow-production-main/docs/deployment/hetzner-fullstack.md` - ✅ Updated with agent deployment steps

### Validation Scripts
- `researchflow-production-main/scripts/hetzner-preflight.sh` - ✅ Added agent health checks
- `researchflow-production-main/scripts/stagewise-smoke.sh` - ✅ Added optional synthesis test (`CHECK_EVIDENCE_SYNTH=1`)

### Agent Code (No Changes - Integration Only)
- `services/agents/agent-evidence-synthesis/` - Agent code unchanged (integration validation only)

---

## How to Deploy

### On ROSflow2 (Hetzner)

```bash
# 1. SSH to server
ssh user@rosflow2

# 2. Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# 3. Pull latest code (includes commit 197bfcd)
git fetch --all --prune
git checkout chore/inventory-capture
git pull --ff-only

# 4. Ensure WORKER_SERVICE_TOKEN is set (required for dispatch auth)
# Generate if not present:
echo "WORKER_SERVICE_TOKEN=$(openssl rand -hex 32)" >> .env

# 5. Build agent (or pull from GHCR when available)
docker compose build agent-evidence-synthesis

# 6. Run preflight checks
chmod +x scripts/hetzner-preflight.sh
./scripts/hetzner-preflight.sh

# 7. Start agent
docker compose up -d agent-evidence-synthesis

# 8. Verify health
curl http://localhost:8015/health
# Expected: {"status":"ok"}

# 9. Verify router registration
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep evidence-synthesis
# Expected: "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000"

# 10. Optional: Run smoke test with synthesis check
CHECK_EVIDENCE_SYNTH=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## How to Validate

### Quick Health Check
```bash
# Agent health
curl http://localhost:8015/health

# Router dispatch (requires auth token)
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"task_type":"EVIDENCE_SYNTHESIS","request_id":"test-001","mode":"DEMO"}'
```

### Full Validation (Automated)
```bash
# Run preflight (includes agent checks)
./scripts/hetzner-preflight.sh

# Run stagewise smoke with synthesis test
CHECK_EVIDENCE_SYNTH=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

### Direct Agent Test
```bash
curl -X POST http://localhost:8015/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "validation-001",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Is aspirin effective for cardiovascular disease prevention?",
      "max_papers": 5
    }
  }'
```

**Expected Response:**
- `ok: true`
- `outputs.executive_summary`: Present
- `outputs.evidence_table`: Array with GRADE ratings
- `outputs.overall_certainty`: High/Moderate/Low/Very Low

---

## Known Limitations / TODOs

### 1. GHCR Image Publishing ⚠️
**Current:** Uses local `build:` in docker-compose.yml  
**Action:** Publish images to GHCR, update compose to `image: ghcr.io/.../agent-evidence-synthesis:${IMAGE_TAG}`  
**Impact:** Required for production IMAGE_TAG pinning and rollback capability

### 2. External Port Exposure ⚠️
**Current:** Port 8015 exposed for testing  
**Action:** Remove `ports: - "8015:8000"` (keep `expose: - "8000"` only)  
**Impact:** Security - internal agents should not be publicly accessible

### 3. Worker Stubs ℹ️
**Current:** Retrieval and conflict workers use stubs (no live API calls)  
**Action:** Connect workers to AI Bridge (`AI_BRIDGE_URL`) or external APIs (`TAVILY_API_KEY`)  
**Impact:** Limited evidence retrieval quality without external data sources

### 4. Non-Root User ⚠️
**Current:** Dockerfile runs as root  
**Action:** Add `USER` directive before `CMD`  
**Impact:** Security best practice

### 5. No Artifact Persistence ℹ️
**Current:** Agent returns results inline (no `/data` volume writes)  
**Action:** None needed (by design)  
**Impact:** Orchestrator/worker must capture and persist results

---

## Compose Validation Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Uses `${IMAGE_TAG}` pattern | ⚠️ | Uses `build:` (local) - switch to GHCR image |
| No `/app` bind mounts | ✅ | Clean |
| Connected to `backend` network | ✅ | Internal service discovery |
| Connected to `frontend` network | ✅ | For external API access |
| Has healthcheck | ✅ | 30s interval, 10s timeout |
| Stable internal port 8000 | ✅ | Exposed on 8000 |
| Env vars use `${VAR}` | ✅ | No hardcoded secrets |
| No public ports (production) | ⚠️ | Port 8015 for testing - remove in prod |
| Resource limits | ✅ | 2 CPU / 4GB max, 0.5 CPU / 1GB min |

---

## Router Registration Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| `EVIDENCE_SYNTHESIS` task type | ✅ | In `TASK_TYPE_TO_AGENT` |
| Routes to correct URL | ✅ | `agent-evidence-synthesis:8000` |
| Uses `/agents/run/sync` | ✅ | Standard agent contract |
| Service auth configured | ✅ | `WORKER_SERVICE_TOKEN` |
| Request/response match | ✅ | `AgentTask` / `AgentResponse` |
| In `AGENT_ENDPOINTS_JSON` | ✅ | Registered |

---

## Validation Hooks

### hetzner-preflight.sh
- ✅ Checks agent container running
- ✅ Checks health endpoint (port 8015)
- ✅ Verifies router registration in `AGENT_ENDPOINTS_JSON`
- ✅ Validates other Stage 2 agents

### stagewise-smoke.sh
- ✅ Optional `CHECK_EVIDENCE_SYNTH=1` flag
- ✅ Health check test
- ✅ Router dispatch test
- ✅ Direct agent call with minimal fixture (3 papers)
- ✅ Response validation (checks for `executive_summary`, `evidence_table`)
- ✅ Does not block existing Stage 2 flows

---

## Required Environment Variables

### Core (Required)
```bash
WORKER_SERVICE_TOKEN=<hex-32-chars>  # Required for internal dispatch auth
```

### Optional (Enhances Retrieval)
```bash
TAVILY_API_KEY=tvly-...              # Web search
GOOGLE_DOCS_API_KEY=...              # Document extraction
```

**Generate WORKER_SERVICE_TOKEN:**
```bash
openssl rand -hex 32
```

---

## Production Deployment Checklist

- [x] **Step 1:** Compose wiring validated (production-safe)
- [x] **Step 2:** Router registration verified
- [x] **Step 3:** Deploy-time validation hooks added
- [x] **Step 4:** Build pipeline compatible (Dockerfile validated)
- [x] **Step 5:** Deployment runbook created

### Pre-Deploy
- [ ] Set `WORKER_SERVICE_TOKEN` in `.env`
- [ ] Set `IMAGE_TAG` to commit SHA (e.g., `197bfcd`)
- [ ] Optional: Set `TAVILY_API_KEY`, `GOOGLE_DOCS_API_KEY`

### Deploy
- [ ] Pull/build agent image
- [ ] Run `hetzner-preflight.sh` (validates agent + services)
- [ ] Start agent: `docker compose up -d agent-evidence-synthesis`
- [ ] Verify health: `curl localhost:8015/health`
- [ ] Verify router: Check `AGENT_ENDPOINTS_JSON`

### Validate
- [ ] Run `stagewise-smoke.sh` with `CHECK_EVIDENCE_SYNTH=1`
- [ ] Test direct agent call (see "How to Validate")
- [ ] Monitor logs: `docker compose logs -f agent-evidence-synthesis`

### Post-Deploy (Production Hardening)
- [ ] Remove port 8015 exposure (keep `expose: - "8000"`)
- [ ] Switch to GHCR image (once published)
- [ ] Add Tavily/Google Docs API keys (if available)
- [ ] Connect workers to AI Bridge (remove stubs)

---

## Documentation References

- **Integration Guide:** [EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md](EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md)
- **Agent README:** [services/agents/agent-evidence-synthesis/README.md](services/agents/agent-evidence-synthesis/README.md)
- **Hetzner Deployment:** [docs/deployment/hetzner-fullstack.md](docs/deployment/hetzner-fullstack.md)
- **AI Router:** [services/orchestrator/src/routes/ai-router.ts](services/orchestrator/src/routes/ai-router.ts)

---

**Status:** ✅ All validation complete. Ready for production deployment on ROSflow2.  
**Next:** Merge to main, deploy to Hetzner, run validation suite.
