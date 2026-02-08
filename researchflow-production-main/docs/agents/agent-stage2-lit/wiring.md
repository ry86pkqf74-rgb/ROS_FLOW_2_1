# agent-stage2-lit - Wiring Documentation

**Agent Key:** `agent-stage2-lit`  
**Type:** Native FastAPI Agent  
**Status:** ✅ Production

---

## Overview

Literature search via PubMed/SemanticScholar

## Deployment Configuration

### Docker Compose Service

**Service Name:** `agent-stage2-lit`  
**Container Name:** `researchflow-agent-stage2-lit`  
**Internal Port:** 8000  
**Networks:** `backend` (internal only)

### Task Types

This agent handles the following task types in the orchestrator router:

- `STAGE_2_LITERATURE_REVIEW`

**Router Mapping:** `TASK_TYPE_TO_AGENT` in `services/orchestrator/src/routes/ai-router.ts`

### Agent Endpoints Registry

**AGENT_ENDPOINTS_JSON Entry:**
```json
"agent-stage2-lit": "http://agent-stage2-lit:8000"
```

**Location:** `docker-compose.yml` orchestrator environment

## Health Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| `/health` | GET | `{"ok": true, "status": "healthy"}` |
| `/health/ready` | GET | `{"ready": true, "dependencies": {...}}` |

**Health Check Command:**
```bash
docker compose exec agent-stage2-lit curl -f http://localhost:8000/health
```

## Required Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `AI_BRIDGE_URL` | Yes | Orchestrator URL for LLM inference |
| `WORKER_SERVICE_TOKEN` | Yes | Internal service authentication |
| `GOVERNANCE_MODE` | No | Execution mode (DEMO/LIVE) |
| `ORCHESTRATOR_INTERNAL_URL` | No | Orchestrator callback URL |

**Note:** Actual environment variables may vary by agent. Check `docker-compose.yml` service definition for complete list.

## Validation Commands

### Preflight Validation (Mandatory)

```bash
# Runs automatically as part of dynamic agent validation
./scripts/hetzner-preflight.sh
```

Preflight validates:
- Agent is present in AGENT_ENDPOINTS_JSON
- Container is running
- Health endpoint responds
- URL format is valid

### Smoke Test (Optional)

```bash
# Test all agents including agent-stage2-lit
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
```

Smoke test:
- Dispatches test request through orchestrator
- Validates routing works correctly
- Writes artifact to `/data/artifacts/validation/agent-stage2-lit/<timestamp>/summary.json`
- Non-blocking (informational only)

## Deployment Steps

### On ROSflow2 (Hetzner)

```bash
# 1. Ensure service is defined in docker-compose.yml
grep -A 20 "agent-stage2-lit:" docker-compose.yml

# 2. Verify AGENT_ENDPOINTS_JSON includes this agent
docker compose config | grep AGENT_ENDPOINTS_JSON | grep "agent-stage2-lit"

# 3. Build and start
docker compose build agent-stage2-lit
docker compose up -d agent-stage2-lit

# 4. Wait for healthy
sleep 10

# 5. Verify health
docker compose exec agent-stage2-lit curl -f http://localhost:8000/health

# 6. Restart orchestrator to load routing
docker compose up -d --force-recreate orchestrator

# 7. Run preflight
./scripts/hetzner-preflight.sh

# 8. Optional: Run smoke test
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs --tail=50 agent-stage2-lit

# Check for build errors
docker compose build agent-stage2-lit

# Verify dependencies
docker compose ps postgres redis orchestrator
```

### Health check fails
```bash
# Check health directly
docker compose exec agent-stage2-lit curl -v http://localhost:8000/health

# Check environment
docker compose exec agent-stage2-lit env | grep -E 'AI_BRIDGE|ORCHESTRATOR'

# Restart service
docker compose restart agent-stage2-lit
```

### Routing failures
```bash
# Verify orchestrator has agent in registry
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep "agent-stage2-lit"

# Check router registration
grep "agent-stage2-lit" services/orchestrator/src/routes/ai-router.ts

# Test dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {}
  }'
```

## Integration

### Upstream Dependencies
- Orchestrator (routing and LLM inference)
- Redis (caching)
- PostgreSQL (persistence)

### Downstream Consumers
- Worker service (workflow engine)
- Frontend UI (direct API calls)
- Other agents (agent-to-agent calls)

## Artifacts

**Path:** `/data/artifacts/agent-stage2-lit/`

Artifacts are written when:
- Smoke tests run with `CHECK_ALL_AGENTS=1`
- Validation requests executed
- (Agent-specific artifact writes if implemented)

## References

- **Service Definition:** `docker-compose.yml` (search for `agent-stage2-lit:`)
- **Router Registration:** `services/orchestrator/src/routes/ai-router.ts`
- **Agent Implementation:** `services/agents/agent-stage2-lit/`
- **Agent Inventory:** `AGENT_INVENTORY.md`
- **Health Check Script:** `scripts/hetzner-preflight.sh`
- **Smoke Test Script:** `scripts/stagewise-smoke.sh`

---

**Last Updated:** 2026-02-08  
**Status:** ✅ Wired for Production
