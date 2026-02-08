# Resilience Architecture Advisor Agent - Wiring Documentation

**Date:** 2026-02-08  
**Status:** ✅ **Wired for Production Deployment**

---

## Summary

The Resilience Architecture Advisor agent provides resilience architecture guidance, PR resilience review, and architecture documentation. This LangSmith cloud-hosted agent is accessible via an HTTP proxy service and integrated with the orchestrator router.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy ✅

```
User/UI Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓ [task_type: RESILIENCE_ARCHITECTURE]
TASK_TYPE_TO_AGENT mapping
    ↓ [resolves to: agent-resilience-architecture-advisor-proxy]
    ↓ [agent URL from AGENT_ENDPOINTS_JSON]
FastAPI Proxy (agent-resilience-architecture-advisor-proxy)
    ↓ [transform ResearchFlow → LangSmith format]
LangSmith API (https://api.smith.langchain.com)
    ↓ [executes agent + 3 sub-agents]
    ↓ [returns results]
FastAPI Proxy
    ↓ [transform LangSmith → ResearchFlow format]
Response (JSON)
    ↓
Return to caller
```

---

## Components

### 1. Proxy Service: `agent-resilience-architecture-advisor-proxy`

**Location:** `services/agents/agent-resilience-architecture-advisor-proxy/`

**Docker Service:** `agent-resilience-architecture-advisor-proxy` (compose service)

**Endpoints:**
- `GET /health` - Health check
- `GET /health/ready` - LangSmith connectivity validation
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Streaming execution (SSE)

**Container Details:**
- Port: 8000 (internal)
- Networks: backend (internal), frontend (LangSmith API access)
- Health check: `/health` every 30s
- Resources: 0.5 CPU / 512MB memory (max)

### 2. Agent Configuration: `agent-resilience-architecture-advisor`

**Location:** `services/agents/agent-resilience-architecture-advisor/`

**Type:** LangSmith custom agent (cloud-hosted)

**Sub-Agents:**
1. **Architecture_Doc_Builder** - Generates architecture documentation
2. **PR_Resilience_Reviewer** - Reviews PRs for resilience patterns
3. **Resilience_Research_Worker** - Researches resilience best practices

---

## Router Registration

### Task Type Mapping

**File:** `services/orchestrator/src/routes/ai-router.ts`

- `RESILIENCE_ARCHITECTURE` → `agent-resilience-architecture-advisor-proxy`

### AGENT_ENDPOINTS_JSON

**Canonical agentKey:** `agent-resilience-architecture-advisor-proxy` (matches proxy service name)

**Internal URL:** `http://agent-resilience-architecture-advisor-proxy:8000`

Orchestrator resolves the agent URL only via `AGENT_ENDPOINTS_JSON`; no hardcoded routing.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGSMITH_API_KEY` | Yes | LangSmith API authentication |
| `LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_AGENT_ID` | Yes | Agent UUID from LangSmith |
| `LANGSMITH_API_URL` | No | Default: `https://api.smith.langchain.com/api/v1` |
| `LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_TIMEOUT_SECONDS` | No | Default: 300 |

---

## Validation

- **Preflight:** `scripts/hetzner-preflight.sh` validates `LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_AGENT_ID` and agent health when `CHECK_ALL_AGENTS=1`.
- **Smoke:** `scripts/stagewise-smoke.sh` with `CHECK_ALL_AGENTS=1` tests dispatch for task type `RESILIENCE_ARCHITECTURE` to `agent-resilience-architecture-advisor-proxy`.
- **Agent list:** `scripts/lib/agent_endpoints_required.txt` includes `agent-resilience-architecture-advisor-proxy`.

---

## Task Contract

**File:** `services/orchestrator/src/services/task-contract.ts`

- Task type `RESILIENCE_ARCHITECTURE` is in `ALLOWED_TASK_TYPES`.
- Input requirements: `required: []`, `optional: ['context', 'artifact_url', 'focus_area', 'output_format']`.
