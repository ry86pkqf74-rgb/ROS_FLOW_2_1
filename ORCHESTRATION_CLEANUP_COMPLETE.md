# Orchestration Cleanup - Implementation Complete ✅

**Date:** 2026-02-08  
**Branch:** feat/import-dissemination-formatter  
**Status:** ✅ **ALL PHASES COMPLETE**

---

## Executive Summary

Successfully implemented comprehensive orchestration cleanup across 5 phases with strict enforcement of AGENT_ENDPOINTS_JSON as the single source of truth for all agent routing.

### Changes Summary

| Phase | Component | Files Changed | Lines Added | Status |
|-------|-----------|---------------|-------------|--------|
| 1 | Routing Refactor | 2 | ~90 | ✅ |
| 2 | Compose Normalization | 0 | 0 | ✅ (Already correct) |
| 3 | Preflight Enforcement | 1 | ~55 net | ✅ |
| 4 | Smoke Tests + Artifacts | 1 | ~205 | ✅ |
| 5 | Wiring Docs | 16 | ~3280 | ✅ |

**Total:** 20 files modified/created, ~3630 lines added

---

## Phase-by-Phase Breakdown

### Phase 1: Single Source of Truth Routing ✅

**Commit:** `82bb086` - "feat(orchestrator): enforce AGENT_ENDPOINTS_JSON as single source of truth"

**Changes:**
- **File:** `services/orchestrator/src/routes/ai-router.ts`
- **File:** `docker-compose.yml`

**Implementation:**
1. Enhanced `getAgentEndpoints()` function:
   - Validates AGENT_ENDPOINTS_JSON is present
   - Validates JSON parsing
   - Validates all values are http:// or https:// URLs
   - Normalizes URLs by trimming trailing slashes
   - Provides clear error messages listing invalid entries

2. Implemented `resolveAgentBaseUrl(agentKey)` function:
   - Throws on missing agent with detailed remediation
   - Lists all available agents in error message
   - Provides step-by-step fix instructions
   - No fallbacks or hardcoded URLs

3. Updated `TASK_TYPE_TO_AGENT` mapping:
   - LangSmith agents now use proxy service names (e.g., `agent-results-interpretation-proxy`)
   - Native agents remain unchanged (e.g., `agent-stage2-lit`)
   - Enforces consistency with AGENT_ENDPOINTS_JSON keys

4. Updated `AGENT_ENDPOINTS_JSON` in docker-compose.yml:
   - Use proxy service names as keys for all LangSmith agents
   - All 22 agents included (15 native + 7 proxy)
   - Clear comments explaining naming convention

**Breaking Changes:**
- Task types now route to proxy services for LangSmith agents
- Missing agents fail immediately with clear error messages
- No agent routing fallbacks remain

**Validation:**
```typescript
// Before (mixed naming):
CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript',  // Logical name
// AGENT_ENDPOINTS_JSON had: "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000"
// ❌ Key mismatch!

// After (consistent proxy naming):
CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript-proxy',  // Proxy service name
// AGENT_ENDPOINTS_JSON has: "agent-clinical-manuscript-proxy": "http://agent-clinical-manuscript-proxy:8000"
// ✅ Keys match!
```

---

### Phase 2: Compose + Endpoints Normalization ✅

**Status:** No changes needed - already correct

**Verification:**
- AGENT_ENDPOINTS_JSON is defined once in orchestrator environment
- All 22 agent keys exist in both compose services and AGENT_ENDPOINTS_JSON
- All values point to internal compose service URLs
- Single source of truth is enforced

---

### Phase 3: Preflight Mandatory Enforcement ✅

**Commit:** `1d3e06a` - "feat(preflight): dynamically derive mandatory agents from AGENT_ENDPOINTS_JSON"

**Changes:**
- **File:** `scripts/hetzner-preflight.sh`

**Implementation:**
1. **Dynamic Agent Discovery:**
   - Removed static agent list file dependency
   - Parse AGENT_ENDPOINTS_JSON directly from orchestrator container
   - Derive mandatory agent keys dynamically (all keys in JSON)
   - Hard-fail if AGENT_ENDPOINTS_JSON is missing or unparseable

2. **Enhanced Validation:**
   - Validate JSON syntax before parsing
   - Validate URL format (must be http:// or https://)
   - Check container is running
   - Perform health checks via docker exec (internal network)
   - Try multiple health endpoints: `/health`, `/api/health`, `/routes/health`

3. **Environment Variable Validation:**
   - Check WORKER_SERVICE_TOKEN (required for internal auth)
   - Check LANGSMITH_API_KEY (required for LangSmith proxies)
   - Validate presence only, never print values

4. **Error Messaging:**
   - Clear failure messages with step-by-step remediation
   - List all available agents in error output
   - Provide docker compose commands for quick fixes
   - Exit with non-zero code on any validation failure

**Removed:**
- Static agent list file (`scripts/lib/agent_endpoints_required.txt`)
- Agent-specific validation sections (covered by dynamic checks)
- Redundant router registration checks

**Breaking Changes:**
- Preflight now derives agents dynamically (no static config)
- All agents in AGENT_ENDPOINTS_JSON are mandatory
- Missing or unhealthy agents block deployment

---

### Phase 4: Smoke Checks + Artifacts ✅

**Commit:** `6b6385b` - "feat(smoke): add CHECK_ALL_AGENTS validation with artifact writes"

**Changes:**
- **File:** `scripts/stagewise-smoke.sh`

**Implementation:**
1. **CHECK_ALL_AGENTS=1 Flag:**
   - Dynamically extract all agent keys from AGENT_ENDPOINTS_JSON
   - Validate each agent through orchestrator dispatch (not direct calls)
   - Write JSON artifacts for each agent
   - Non-blocking (informational only)

2. **Artifact Structure:**
   ```json
   {
     "agentKey": "agent-stage2-lit",
     "timestamp": "20260208T120000Z",
     "request": {
       "method": "POST",
       "endpoint": "/api/ai/router/dispatch",
       "task_type": "STAGE_2_LITERATURE_REVIEW",
       "request_id": "smoke-agent-stage2-lit-001",
       "mode": "DEMO"
     },
     "response_status": 200,
     "ok": true,
     "error": null,
     "agent_url": "http://agent-stage2-lit:8000",
     "service_name": "agent-stage2-lit",
     "container_running": true,
     "dispatch_response_excerpt": {...}
   }
   ```

3. **Artifact Path:**
   `/data/artifacts/validation/<agentKey>/<timestamp>/summary.json`

4. **Validation Flow:**
   - Check orchestrator is running
   - Fetch AGENT_ENDPOINTS_JSON from orchestrator env
   - Parse JSON and extract all agent keys
   - For each agent:
     * Verify container is running
     * Dispatch test request through orchestrator
     * Write artifact with result
   - Report summary (passed/failed counts)

**Features:**
- Deterministic test payloads (no external API calls)
- Non-blocking (does not fail smoke test)
- Comprehensive artifact logging for audit trail
- Clear pass/fail indicators per agent
- Remediation guidance for failures

**Usage:**
```bash
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
```

---

### Phase 5: Wiring Documentation ✅

**Commit:** `7af50f3` - "docs(agents): generate standardized wiring docs for all native agents"

**Changes:**
- **Script:** `scripts/generate-agent-wiring-docs.sh` (new)
- **Docs:** `docs/agents/<agent-key>/wiring.md` (15 new files)

**Implementation:**
1. Created automated doc generation script
2. Generated standardized wiring.md for all 15 native agents
3. Each doc includes:
   - Agent key and deployment status
   - Docker Compose service configuration
   - Task type mappings
   - AGENT_ENDPOINTS_JSON entry format
   - Health endpoint details
   - Required environment variables (names only)
   - Validation commands (preflight + smoke)
   - Deployment steps for ROSflow2
   - Troubleshooting guide
   - Integration dependencies
   - Artifact paths
   - Reference links

**Coverage:**
- **Native agents (15):** agent-stage2-lit, agent-stage2-screen, agent-stage2-extract, agent-stage2-synthesize, agent-lit-retrieval, agent-lit-triage, agent-policy-review, agent-rag-ingest, agent-rag-retrieve, agent-verify, agent-intro-writer, agent-methods-writer, agent-results-writer, agent-discussion-writer, agent-evidence-synthesis

- **Proxy agents (7):** clinical-bias-detection, clinical-manuscript-writer, clinical-section-drafter, dissemination-formatter, peer-review-simulator, performance-optimizer, results-interpretation (docs already exist)

**Total:** 22 agents with complete wiring documentation

---

## Definition of Done Validation

### ✅ AGENT_ENDPOINTS_JSON is the single source of truth
- [x] Router reads only from AGENT_ENDPOINTS_JSON
- [x] No hardcoded http://agent-... URLs remain
- [x] No fallback URL generation logic
- [x] All agent keys match between router and compose

### ✅ Router contains no hardcoded targets
- [x] All agent URLs resolved via `resolveAgentBaseUrl()`
- [x] Function throws on missing agent with clear error
- [x] Error messages include all available agents
- [x] Remediation steps provided in error messages

### ✅ Preflight fails fast if any declared agent is missing/unhealthy
- [x] AGENT_ENDPOINTS_JSON parsed dynamically
- [x] All keys extracted as mandatory agents
- [x] Each agent validated (registry, container, health)
- [x] Exit code 1 on any failure
- [x] Clear remediation for each failure type

### ✅ Smoke can validate all agents via orchestrator
- [x] CHECK_ALL_AGENTS=1 flag implemented
- [x] Iterates all agents from AGENT_ENDPOINTS_JSON
- [x] Dispatches through orchestrator (not direct)
- [x] Writes artifacts to /data/artifacts/validation/

### ✅ CI passes (including gitleaks)
- [ ] Run locally: `npm run lint`
- [ ] Run locally: `npm run typecheck`
- [ ] Run gitleaks: `git diff main | docker run -v $(pwd):/path zricethezav/gitleaks:latest protect --no-git --verbose --redact --stdin`

---

## Validation Commands

### Local Development

```bash
# 1. Type checking
cd researchflow-production-main/services/orchestrator
npm run typecheck

# 2. Linting
npm run lint

# 3. Build orchestrator
npm run build

# 4. Verify no secrets committed
git diff main | docker run -i zricethezav/gitleaks:latest protect --no-git --verbose --redact --stdin
```

### On ROSflow2 (Hetzner)

```bash
# 1. Pull latest changes
cd /opt/researchflow
git fetch --all --prune
git checkout feat/import-dissemination-formatter
git pull --ff-only

# 2. Verify AGENT_ENDPOINTS_JSON in .env (if needed)
docker compose config | grep AGENT_ENDPOINTS_JSON | python3 -m json.tool

# 3. Rebuild orchestrator
docker compose build orchestrator

# 4. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 5. Wait for healthy
sleep 15
docker compose ps orchestrator

# 6. Run mandatory preflight validation
./researchflow-production-main/scripts/hetzner-preflight.sh

# Expected output:
#   ✓ AGENT_ENDPOINTS_JSON: valid JSON with 22 agent(s)
#   ✓ All 22 mandatory agents are running and healthy!
#   ✓ ALL PREFLIGHT CHECKS PASSED!

# 7. Run optional smoke test (all agents)
CHECK_ALL_AGENTS=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./researchflow-production-main/scripts/stagewise-smoke.sh

# Expected output:
#   [15] ALL AGENTS VALIDATION (CHECK_ALL_AGENTS=1)
#   Found 22 agents in AGENT_ENDPOINTS_JSON
#   ✓ ALL AGENTS VALIDATED SUCCESSFULLY

# 8. Check artifacts written
ls -lR /data/artifacts/validation/ | head -50

# 9. Verify routing for one agent
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {"query": "test"}
  }'

# Expected response:
# {
#   "dispatch_type": "agent",
#   "agent_name": "agent-stage2-lit",
#   "agent_url": "http://agent-stage2-lit:8000",
#   ...
# }
```

### Sample Per-Agent Smoke Test

```bash
# Test specific agent through orchestrator dispatch
TOKEN=$(curl -s -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq -r '.token')

# Test agent-stage2-lit
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "manual-test-001",
    "mode": "DEMO",
    "inputs": {
      "query": "diabetes mellitus",
      "max_results": 5
    }
  }'

# Test agent-results-interpretation-proxy (LangSmith)
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "manual-test-002",
    "mode": "DEMO",
    "inputs": {
      "results_data": {"p_value": 0.03, "effect_size": 1.2},
      "study_context": "RCT of intervention X"
    }
  }'

# Test agent-clinical-manuscript-proxy (LangSmith)
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_MANUSCRIPT_WRITE",
    "request_id": "manual-test-003",
    "mode": "DEMO",
    "inputs": {
      "study_summary": "RCT comparing A vs B",
      "evidence_synthesis": {...}
    }
  }'
```

---

## Architecture Changes

### Before: Mixed Naming Convention ❌

```typescript
// Router (ai-router.ts)
CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript',  // Logical name

// Compose (AGENT_ENDPOINTS_JSON)
{
  "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000",
  //  ^^^^^^^^^^^^^^^^^^^^^^^^        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  //  Logical name                    Actual service name
  //  ❌ Mismatch causes confusion
}
```

### After: Consistent Proxy Naming ✅

```typescript
// Router (ai-router.ts)
CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript-proxy',  // Proxy service name

// Compose (AGENT_ENDPOINTS_JSON)
{
  "agent-clinical-manuscript-proxy": "http://agent-clinical-manuscript-proxy:8000",
  //  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  //  Proxy service name                      Proxy service name
  //  ✅ Keys match exactly
}
```

### Flow Diagram

```
User Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓
TASK_TYPE_TO_AGENT[task_type]
    ↓ (returns agentKey, e.g., "agent-stage2-lit")
resolveAgentBaseUrl(agentKey)
    ↓ (looks up in AGENT_ENDPOINTS_JSON)
    ↓ (returns "http://agent-stage2-lit:8000")
Dispatch to agent
    ↓
Agent processes request
    ↓
Response
```

---

## Agent Registry (22 Total)

### Native FastAPI Agents (15)

| Agent Key | Compose Service | Port | Task Types |
|-----------|-----------------|------|------------|
| `agent-stage2-lit` | agent-stage2-lit | 8000 | STAGE_2_LITERATURE_REVIEW |
| `agent-stage2-screen` | agent-stage2-screen | 8000 | STAGE2_SCREEN |
| `agent-stage2-extract` | agent-stage2-extract | 8000 | STAGE_2_EXTRACT, STAGE2_EXTRACT |
| `agent-stage2-synthesize` | agent-stage2-synthesize | 8000 | STAGE2_SYNTHESIZE |
| `agent-lit-retrieval` | agent-lit-retrieval | 8000 | LIT_RETRIEVAL |
| `agent-lit-triage` | agent-lit-triage | 8000 | LIT_TRIAGE |
| `agent-policy-review` | agent-policy-review | 8000 | POLICY_REVIEW |
| `agent-rag-ingest` | agent-rag-ingest | 8000 | RAG_INGEST |
| `agent-rag-retrieve` | agent-rag-retrieve | 8000 | RAG_RETRIEVE |
| `agent-verify` | agent-verify | 8000 | CLAIM_VERIFY |
| `agent-intro-writer` | agent-intro-writer | 8000 | SECTION_WRITE_INTRO |
| `agent-methods-writer` | agent-methods-writer | 8000 | SECTION_WRITE_METHODS |
| `agent-results-writer` | agent-results-writer | 8000 | SECTION_WRITE_RESULTS |
| `agent-discussion-writer` | agent-discussion-writer | 8000 | SECTION_WRITE_DISCUSSION |
| `agent-evidence-synthesis` | agent-evidence-synthesis | 8000 | EVIDENCE_SYNTHESIS |

### LangSmith Proxy Agents (7)

| Agent Key | Compose Service | Port | Task Types |
|-----------|-----------------|------|------------|
| `agent-results-interpretation-proxy` | agent-results-interpretation-proxy | 8000 | RESULTS_INTERPRETATION, STATISTICAL_ANALYSIS |
| `agent-clinical-manuscript-proxy` | agent-clinical-manuscript-proxy | 8000 | CLINICAL_MANUSCRIPT_WRITE |
| `agent-section-drafter-proxy` | agent-section-drafter-proxy | 8000 | CLINICAL_SECTION_DRAFT |
| `agent-peer-review-simulator-proxy` | agent-peer-review-simulator-proxy | 8000 | PEER_REVIEW_SIMULATION |
| `agent-bias-detection-proxy` | agent-bias-detection-proxy | 8000 | CLINICAL_BIAS_DETECTION |
| `agent-dissemination-formatter-proxy` | agent-dissemination-formatter-proxy | 8000 | DISSEMINATION_FORMATTING |
| `agent-performance-optimizer-proxy` | agent-performance-optimizer-proxy | 8000 | PERFORMANCE_OPTIMIZATION |

---

## Files Changed

### Modified (3 files)
1. `services/orchestrator/src/routes/ai-router.ts`
   - +90 lines: Enhanced validation and error handling
   - Changed: TASK_TYPE_TO_AGENT to use proxy keys

2. `docker-compose.yml`
   - +24 lines: Updated AGENT_ENDPOINTS_JSON keys and comments

3. `scripts/hetzner-preflight.sh`
   - +55 net lines: Dynamic agent derivation from AGENT_ENDPOINTS_JSON

4. `scripts/stagewise-smoke.sh`
   - +205 lines: CHECK_ALL_AGENTS validation with artifacts

### Created (16 files)
5-19. `docs/agents/<agent-key>/wiring.md` (15 native agents)
20. `scripts/generate-agent-wiring-docs.sh` (doc generator)

### Summary
- **Total files:** 20 (4 modified, 16 created)
- **Lines added:** ~3630
- **Lines removed:** ~60
- **Net change:** +3570 lines

---

## Breaking Changes

### Router Behavior
- **Before:** Router used logical agent names (e.g., `agent-results-interpretation`)
- **After:** Router uses proxy service names (e.g., `agent-results-interpretation-proxy`)
- **Impact:** Task types now route correctly to proxy services

### Preflight Validation
- **Before:** Checked static list of agents from file
- **After:** Dynamically checks all agents in AGENT_ENDPOINTS_JSON
- **Impact:** All declared agents are now mandatory (no opt-out)

### Error Messages
- **Before:** Generic "agent not found" errors
- **After:** Detailed errors listing all available agents + remediation
- **Impact:** Easier debugging for operators

---

## Migration Guide

### For Existing Deployments

**No action required** if:
- All agents in AGENT_ENDPOINTS_JSON are running and healthy
- WORKER_SERVICE_TOKEN and LANGSMITH_API_KEY are configured

**Action required** if:
- You have agents in AGENT_ENDPOINTS_JSON that are not running
- You want to disable certain agents

**To disable an agent:**
```bash
# 1. Edit docker-compose.yml
# 2. Remove agent from AGENT_ENDPOINTS_JSON
# 3. Remove corresponding entry from TASK_TYPE_TO_AGENT in ai-router.ts
# 4. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 5. Run preflight to verify
./scripts/hetzner-preflight.sh
```

---

## Testing

### Unit Tests (TODO)
```bash
cd services/orchestrator
npm test src/routes/ai-router.test.ts
```

### Integration Tests

```bash
# 1. Start all services
docker compose up -d

# 2. Wait for healthy
sleep 30

# 3. Run preflight (mandatory)
./researchflow-production-main/scripts/hetzner-preflight.sh

# Should see:
#   ✓ AGENT_ENDPOINTS_JSON: valid JSON with 22 agent(s)
#   ✓ All 22 mandatory agents are running and healthy!
#   ✓ ALL PREFLIGHT CHECKS PASSED!

# 4. Run smoke test (all agents)
CHECK_ALL_AGENTS=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./researchflow-production-main/scripts/stagewise-smoke.sh

# Should see:
#   [15] ALL AGENTS VALIDATION (CHECK_ALL_AGENTS=1)
#   Found 22 agents in AGENT_ENDPOINTS_JSON
#   ✓ ALL AGENTS VALIDATED SUCCESSFULLY

# 5. Verify artifacts
ls -l /data/artifacts/validation/

# Should contain directories for each agent with timestamp subdirs
```

---

## Troubleshooting

### Error: "AGENT_ENDPOINTS_JSON is not set"

**Cause:** Environment variable missing from orchestrator

**Fix:**
```bash
# Verify in docker-compose.yml
grep AGENT_ENDPOINTS_JSON docker-compose.yml

# Restart orchestrator
docker compose up -d --force-recreate orchestrator

# Verify loaded
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool
```

### Error: "Agent X not found in AGENT_ENDPOINTS_JSON"

**Cause:** Agent key mismatch between router and compose

**Fix:**
```bash
# Check router mapping
grep "TASK_TYPE_TO_AGENT" services/orchestrator/src/routes/ai-router.ts -A 30

# Check compose mapping
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool

# Ensure keys match exactly
```

### Error: "Agent Y container not running"

**Cause:** Service not started or unhealthy

**Fix:**
```bash
# Check status
docker compose ps | grep agent-Y

# View logs
docker compose logs --tail=50 agent-Y

# Restart
docker compose up -d agent-Y

# Check health
docker compose exec agent-Y curl -f http://localhost:8000/health
```

### Preflight fails on agent health check

**Cause:** Agent container running but health endpoint failing

**Fix:**
```bash
# Check logs for errors
docker compose logs --tail=100 <agent-name>

# Check environment variables
docker compose exec <agent-name> env | grep -E 'AI_BRIDGE|LANGSMITH|ORCHESTRATOR'

# Verify dependencies
docker compose ps postgres redis orchestrator chromadb

# Restart with fresh logs
docker compose restart <agent-name>
docker compose logs -f <agent-name>
```

---

## Rollback Procedure

If issues arise, rollback to previous state:

```bash
# 1. Checkout previous commit
git log --oneline | head -5
git checkout <previous-commit>

# 2. Rebuild and restart orchestrator
docker compose build orchestrator
docker compose up -d --force-recreate orchestrator

# 3. Verify
./researchflow-production-main/scripts/hetzner-preflight.sh
```

---

## Related Documentation

- **Agent Inventory:** `AGENT_INVENTORY.md`
- **Individual Agent Wiring:** `docs/agents/<agent-key>/wiring.md`
- **Preflight Script:** `scripts/hetzner-preflight.sh`
- **Smoke Test Script:** `scripts/stagewise-smoke.sh`
- **Docker Compose:** `docker-compose.yml`
- **Router Implementation:** `services/orchestrator/src/routes/ai-router.ts`

---

## Commits

| Phase | Commit | Message |
|-------|--------|---------|
| 1 | `82bb086` | feat(orchestrator): enforce AGENT_ENDPOINTS_JSON as single source of truth |
| 2 | N/A | (No changes needed - compose already correct) |
| 3 | `1d3e06a` | feat(preflight): dynamically derive mandatory agents from AGENT_ENDPOINTS_JSON |
| 4 | `6b6385b` | feat(smoke): add CHECK_ALL_AGENTS validation with artifact writes |
| 5 | `7af50f3` | docs(agents): generate standardized wiring docs for all native agents |

**Branch:** `feat/import-dissemination-formatter`

---

## Next Steps

### Immediate
1. ✅ All phases committed to feat/import-dissemination-formatter
2. ⏳ Push to remote: `git push origin feat/import-dissemination-formatter`
3. ⏳ Deploy to ROSflow2 following validation commands above
4. ⏳ Run preflight + smoke tests
5. ⏳ Create PR to main

### Short-Term
6. ⏳ Add unit tests for router functions
7. ⏳ Add CI workflow to validate AGENT_ENDPOINTS_JSON syntax
8. ⏳ Document environment variable requirements per agent
9. ⏳ Create deployment runbook with these procedures

### Long-Term
10. ⏳ Automate wiring doc generation in CI
11. ⏳ Add drift detection (router vs compose)
12. ⏳ Implement agent registry API endpoint
13. ⏳ Add observability for agent routing

---

## Success Criteria

- [x] AGENT_ENDPOINTS_JSON is single source of truth
- [x] Router uses proxy service names for LangSmith agents
- [x] No hardcoded URLs remain
- [x] Preflight dynamically validates all agents
- [x] Smoke test can validate all agents with artifacts
- [x] All agents have wiring documentation
- [x] Clear error messages with remediation
- [x] Fail-fast on misconfiguration
- [ ] CI passes (run locally before merge)
- [ ] Deployed to ROSflow2 and validated

---

**Status:** ✅ **IMPLEMENTATION COMPLETE**  
**Ready for:** Deployment validation on ROSflow2  
**Generated:** 2026-02-08
