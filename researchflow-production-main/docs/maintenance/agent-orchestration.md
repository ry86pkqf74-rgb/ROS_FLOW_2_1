# Agent Orchestration - Single Source of Truth

**Last Updated:** 2026-02-08  
**Branch:** chore/inventory-capture  
**Status:** ✅ **Production Standard**

---

## Overview

All agent routing in ResearchFlow is controlled by a **single source of truth**: the `AGENT_ENDPOINTS_JSON` environment variable. This eliminates configuration drift and ensures all agents are validated at deployment time.

---

## Architecture Principles

### 1. Single Source of Truth

**AGENT_ENDPOINTS_JSON** is the ONLY place where agent endpoints are defined. No hardcoded URLs in application code.

```json
{
  "agent-stage2-lit": "http://agent-stage2-lit:8000",
  "agent-stage2-screen": "http://agent-stage2-screen:8000",
  "agent-results-interpretation": "http://agent-results-interpretation-proxy:8000"
}
```

### 2. Mandatory Validation

**All agents are mandatory.** Deployment fails if any agent is:
- Missing from AGENT_ENDPOINTS_JSON
- Container not running
- Health endpoint not responding

### 3. Standardized Contract

Every agent exposes the same interface:
- `GET /health` - Liveness probe (returns `{"status": "ok"}`)
- `GET /health/ready` - Readiness probe with dependency checks
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Streaming execution (SSE)

All agents listen on **port 8000** internally.

---

## Canonical Agent List

The definitive list of mandatory agents is maintained in:

```
scripts/lib/agent_endpoints_required.txt
```

This file is used by both preflight validation and smoke tests to ensure consistency.

**Current count:** 21 mandatory agents (15 native + 6 LangSmith proxies)

---

## Configuration

### docker-compose.yml

Every agent must be defined as a service:

```yaml
agent-example:
  build:
    context: .
    dockerfile: services/agents/agent-example/Dockerfile
  container_name: researchflow-agent-example
  restart: unless-stopped
  environment:
    - AI_BRIDGE_URL=http://orchestrator:3001
    - WORKER_SERVICE_TOKEN=${WORKER_SERVICE_TOKEN}
  expose:
    - "8000"
  networks:
    - backend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 2G
      reservations:
        cpus: '0.25'
        memory: 512M
```

**Key requirements:**
- ✅ Standard port 8000
- ✅ Backend network only (no public exposure)
- ✅ Health check at `/health`
- ✅ Resource limits defined
- ✅ No `/app` bind mounts in production

### AGENT_ENDPOINTS_JSON

Add to orchestrator environment in docker-compose.yml:

```yaml
orchestrator:
  environment:
    - 'AGENT_ENDPOINTS_JSON={"agent-example":"http://agent-example:8000",...}'
```

**Format rules:**
- JSON object (not array)
- Keys: agent logical names (e.g., `agent-stage2-lit`)
- Values: internal Docker network URLs (e.g., `http://agent-stage2-lit:8000`)
- All URLs must use `http://` protocol
- All services must be on backend network

---

## Orchestrator Routing

### Router Implementation

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
// Load AGENT_ENDPOINTS_JSON at startup
const AGENT_ENDPOINTS_STATE = {
  endpoints: JSON.parse(process.env.AGENT_ENDPOINTS_JSON),
  error: undefined
};

// Helper function (NO hardcoded URLs)
function getAgentBaseUrl(agentKey: string): string {
  const url = AGENT_ENDPOINTS_STATE.endpoints[agentKey];
  if (!url) {
    throw new Error(`Agent "${agentKey}" not in AGENT_ENDPOINTS_JSON`);
  }
  return url;
}

// Dispatch handler
const agent_name = TASK_TYPE_TO_AGENT[task_type];
const agent_url = getAgentBaseUrl(agent_name);  // ✅ Registry lookup
// ❌ NEVER: const agent_url = `http://agent-foo:8000`;  // Hardcoded
```

### Task Type Mapping

Define in `TASK_TYPE_TO_AGENT`:

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  EVIDENCE_SYNTHESIS: 'agent-evidence-synthesis',
  LIT_TRIAGE: 'agent-lit-triage',
  CLAIM_VERIFY: 'agent-verify',
  // ... etc
};
```

**Rules:**
- Map task types to agent **keys** (not URLs)
- Keys must match AGENT_ENDPOINTS_JSON keys exactly
- No hardcoded service names or ports

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**What it does:**
1. Loads mandatory agent list from `scripts/lib/agent_endpoints_required.txt`
2. Validates AGENT_ENDPOINTS_JSON is set and parseable
3. For each mandatory agent:
   - Verifies key exists in AGENT_ENDPOINTS_JSON
   - Checks container is running
   - Curls `/health` endpoint (via docker exec)
4. **Hard-fails** if any agent is missing or unhealthy

**Usage:**
```bash
./scripts/hetzner-preflight.sh

# Exit codes:
# 0 - All checks passed
# 1 - One or more agents failed (deployment blocked)
```

### Smoke Tests (Optional)

**Script:** `scripts/stagewise-smoke.sh`

**Flags:**
- `CHECK_ALL_AGENTS=1` - Test all agents via orchestrator dispatch
- Individual flags: `CHECK_EVIDENCE_SYNTH=1`, `CHECK_LIT_TRIAGE=1`, etc.

**What it does:**
1. For each agent, sends dispatch request via orchestrator
2. Validates response contains correct agent name
3. Writes validation artifact to `/data/artifacts/validation/`
4. Reports pass/fail counts (non-blocking)

**Usage:**
```bash
# Test all agents
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh

# Test specific agent
CHECK_EVIDENCE_SYNTH=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Adding a New Agent

Follow this checklist to add a new mandatory agent without breaking orchestration:

### Step 1: Create Agent Service

Create agent directory:
```
services/agents/agent-my-feature/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py         # FastAPI app
│   └── routes/
│       ├── health.py   # GET /health, /health/ready
│       └── run.py      # POST /agents/run/sync, /agents/run/stream
└── agent/
    └── impl.py         # Agent logic
```

**Requirements:**
- ✅ Expose port 8000
- ✅ Implement `/health` endpoint
- ✅ Return `{"status": "ok"}` when healthy
- ✅ Handle `DEMO` mode (work offline with fixtures)

### Step 2: Add to docker-compose.yml

```yaml
agent-my-feature:
  build:
    context: .
    dockerfile: services/agents/agent-my-feature/Dockerfile
  container_name: researchflow-agent-my-feature
  restart: unless-stopped
  environment:
    - AI_BRIDGE_URL=http://orchestrator:3001
    - WORKER_SERVICE_TOKEN=${WORKER_SERVICE_TOKEN}
    - GOVERNANCE_MODE=${GOVERNANCE_MODE:-DEMO}
  expose:
    - "8000"
  networks:
    - backend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 2G
      reservations:
        cpus: '0.25'
        memory: 512M
```

### Step 3: Add to AGENT_ENDPOINTS_JSON

In orchestrator environment, add to the JSON:

```yaml
orchestrator:
  environment:
    - 'AGENT_ENDPOINTS_JSON={
        ...existing agents...,
        "agent-my-feature":"http://agent-my-feature:8000"
      }'
```

**CRITICAL:** Preserve JSON syntax (quotes, commas, brackets)

### Step 4: Register Task Type

**File:** `services/orchestrator/src/routes/ai-router.ts`

Add to `TASK_TYPE_TO_AGENT`:

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ... existing ...
  MY_FEATURE: 'agent-my-feature',
};
```

### Step 5: Add to Mandatory List

**File:** `scripts/lib/agent_endpoints_required.txt`

Add agent key:
```
agent-my-feature
```

### Step 6: Validate

```bash
# Build and start
docker compose build agent-my-feature
docker compose up -d agent-my-feature

# Run preflight (will fail if agent unhealthy)
./scripts/hetzner-preflight.sh

# Test dispatch
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Troubleshooting

### "Agent not found in AGENT_ENDPOINTS_JSON"

**Cause:** Agent key missing from AGENT_ENDPOINTS_JSON

**Fix:**
1. Add to docker-compose.yml orchestrator environment
2. Restart orchestrator: `docker compose up -d --force-recreate orchestrator`

### "Agent container not running"

**Cause:** Service not started or crashed

**Fix:**
1. Check status: `docker compose ps agent-example`
2. View logs: `docker compose logs agent-example`
3. Start: `docker compose up -d agent-example`

### "Health endpoint not responding"

**Cause:** Agent started but health check failing

**Fix:**
1. Check logs: `docker compose logs agent-example`
2. Test health directly: `docker compose exec agent-example curl http://localhost:8000/health`
3. Verify dependencies (AI_BRIDGE_URL, tokens, etc.)

### "Preflight failed with agent validation errors"

**Cause:** One or more mandatory agents are unhealthy

**Fix:**
1. Identify failed agent from preflight output
2. Follow remediation steps printed by preflight
3. Re-run preflight until all pass

---

## Migration Notes

### Pre-2026-02-08 (Legacy)

❌ **Old approach:**
- Hardcoded URLs in router: `http://agent-example:8000`
- Mix of service discovery and env vars
- Optional agent checks (warnings only)
- Drift between compose, router, and validation scripts

✅ **New approach:**
- Single source of truth: AGENT_ENDPOINTS_JSON
- Mandatory validation with hard-fail
- Canonical agent list drives all validation
- Zero hardcoded URLs in application code

### Breaking Changes

If you have custom agent routing:
1. Remove all hardcoded agent URLs from TypeScript/Python code
2. Add agents to AGENT_ENDPOINTS_JSON
3. Use `getAgentBaseUrl(agentKey)` for lookups
4. Update preflight/smoke scripts to validate new agents

---

## Best Practices

### DO ✅
- Use AGENT_ENDPOINTS_JSON for all agent URLs
- Add all agents to `scripts/lib/agent_endpoints_required.txt`
- Implement `/health` endpoint on port 8000
- Test agents via orchestrator dispatch (not direct calls)
- Run preflight before every deployment

### DON'T ❌
- Hardcode agent URLs (e.g., `http://agent-foo:8000`)
- Skip preflight validation
- Make agents optional in production
- Use non-standard health paths
- Expose agent ports publicly (use `expose:` not `ports:`)

---

## Quick Reference

### Check Agent Status
```bash
# All agents
docker compose ps | grep agent-

# Specific agent
docker compose ps agent-example
docker compose logs -f agent-example
```

### Test Agent Health
```bash
# Via docker exec (internal network)
docker compose exec agent-example curl http://localhost:8000/health

# Via orchestrator dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"MY_FEATURE","request_id":"test-001","mode":"DEMO"}'
```

### View Agent Registry
```bash
# Show all registered agents
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool
```

---

## Related Documentation

- **Agent Inventory:** `AGENT_INVENTORY.md` - Complete list of all agents
- **Preflight Script:** `scripts/hetzner-preflight.sh` - Deployment validation
- **Smoke Tests:** `scripts/stagewise-smoke.sh` - Integration validation
- **Agent List:** `scripts/lib/agent_endpoints_required.txt` - Canonical mandatory agents
- **Router Implementation:** `services/orchestrator/src/routes/ai-router.ts` - Dispatch logic

---

**Maintained By:** ResearchFlow Platform Team  
**Review Cycle:** Every agent import/update
