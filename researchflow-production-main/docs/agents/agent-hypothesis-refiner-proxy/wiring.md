# Hypothesis Refiner Agent - Integration Wiring

**Agent**: Hypothesis Refiner  
**Canonical agentKey**: `agent-hypothesis-refiner-proxy`  
**TaskType**: `HYPOTHESIS_REFINEMENT`  
**Backend**: LangSmith cloud-hosted agent  
**Integration Date**: 2026-02-08  
**Branch**: `feat/hypothesis-refiner`

---

## Overview

The Hypothesis Refiner agent generates, validates, and iteratively refines clinical research hypotheses using PICOT (Population, Intervention, Comparison, Outcome, Timeframe) and SMART (Specific, Measurable, Achievable, Relevant, Time-bound) frameworks. It ingests research questions, data summaries, and literature evidence to produce evidence-grounded, feasible, and unbiased hypotheses for all medical domains.

## Architecture

```
Orchestrator → agent-hypothesis-refiner-proxy (FastAPI) → LangSmith Cloud API
```

- **Proxy Service**: `agent-hypothesis-refiner-proxy` (FastAPI, Python 3.11)
- **LangSmith Agent**: Hypothesis refinement with evidence validation
- **Subagent**: Evidence_Retrieval_Validator (for hypothesis validation)
- **Port**: 8000 (internal)
- **Networks**: backend (orchestrator), frontend (LangSmith API)

## Files Created/Modified

### New Files
- `services/agents/agent-hypothesis-refiner/` - LangSmith config bundle
  - `AGENTS.md` - Agent instructions and workflow
  - `config.json` - Agent metadata
  - `tools.json` - Tool definitions (Tavily, Google Docs)
  - `subagents/Evidence_Retrieval_Validator/` - Evidence validation subagent
- `services/agents/agent-hypothesis-refiner-proxy/` - FastAPI proxy service
  - `app/main.py` - FastAPI endpoints
  - `app/config.py` - Configuration management
  - `app/__init__.py` - Package initialization
  - `Dockerfile` - Container build
  - `requirements.txt` - Python dependencies
  - `README.md` - Service documentation
- `docs/agents/agent-hypothesis-refiner-proxy/wiring.md` - This file

### Modified Files
- `docker-compose.yml`
  - Added `agent-hypothesis-refiner-proxy` service
  - Added entry to `AGENT_ENDPOINTS_JSON`: `"agent-hypothesis-refiner-proxy": "http://agent-hypothesis-refiner-proxy:8000"`
- `services/orchestrator/src/routes/ai-router.ts`
  - Added `HYPOTHESIS_REFINEMENT` → `agent-hypothesis-refiner-proxy` mapping
- `services/orchestrator/src/services/task-contract.ts`
  - Added `HYPOTHESIS_REFINEMENT` to `ALLOWED_TASK_TYPES`
  - Added input schema (all optional): `research_question`, `hypothesis`, `context`, `constraints`, `variables`, `population`, `intervention`, `comparison`, `outcomes`, `study_design`, `citations`, `output_format`
- `scripts/stagewise-smoke.sh`
  - Added `CHECK_HYPOTHESIS_REFINER=1` in `CHECK_ALL_AGENTS` section
  - Added `agent-hypothesis-refiner-proxy` to `AGENT_TASK_TYPES` mapping
  - Added dedicated validation section [17]
- `scripts/lib/agent_endpoints_required.txt`
  - Added `agent-hypothesis-refiner-proxy` to mandatory agents list

## Environment Variables

### Required (Names only - values in secrets management)
- `LANGSMITH_API_KEY` - LangSmith API key (shared across agents)
- `LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID` - LangSmith assistant ID for Hypothesis Refiner

### Optional
- `LANGSMITH_HYPOTHESIS_REFINER_TIMEOUT_SECONDS` - Request timeout (default: 300)
- `LANGSMITH_API_URL` - LangSmith API URL (default: https://api.smith.langchain.com/api/v1)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LANGCHAIN_PROJECT` - LangChain project name (default: researchflow-hypothesis-refiner)
- `LANGCHAIN_TRACING_V2` - Enable tracing (default: false)

## docker-compose.yml Wiring

```yaml
agent-hypothesis-refiner-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-hypothesis-refiner-proxy/Dockerfile
  container_name: researchflow-agent-hypothesis-refiner-proxy
  restart: unless-stopped
  stop_grace_period: 30s
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGSMITH_AGENT_ID=${LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID:-}
    - LANGSMITH_API_URL=${LANGSMITH_API_URL:-https://api.smith.langchain.com/api/v1}
    - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_HYPOTHESIS_REFINER_TIMEOUT_SECONDS:-300}
    - LOG_LEVEL=${AGENT_LOG_LEVEL:-INFO}
    - LANGCHAIN_PROJECT=${LANGCHAIN_PROJECT:-researchflow-hypothesis-refiner}
    - LANGCHAIN_TRACING_V2=${LANGCHAIN_TRACING_V2:-false}
    - PYTHONUNBUFFERED=1
  expose:
    - "8000"
  networks:
    - backend
    - frontend
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 15s
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
      reservations:
        cpus: '0.25'
```

## Orchestrator Routing

### ai-router.ts Mapping
```typescript
HYPOTHESIS_REFINEMENT: 'agent-hypothesis-refiner-proxy',
```

### task-contract.ts Schema
```typescript
'HYPOTHESIS_REFINEMENT',  // In ALLOWED_TASK_TYPES

HYPOTHESIS_REFINEMENT: {
  required: [],
  optional: [
    'research_question', 'hypothesis', 'context', 'constraints',
    'variables', 'population', 'intervention', 'comparison',
    'outcomes', 'study_design', 'citations', 'output_format'
  ],
},
```

## Endpoints

### Health Checks
- `GET /health` - Basic status check (returns `{"status": "ok"}`)
- `GET /health/ready` - Validates LangSmith connectivity (checks `/info` endpoint)

### Agent Operations
- `POST /agents/run/sync` - Synchronous hypothesis refinement
- `POST /agents/run/stream` - Streaming hypothesis refinement (SSE, no double-framing)

## Request/Response Schema

### Request
```json
{
  "task_type": "HYPOTHESIS_REFINEMENT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "research_question": "Does exercise reduce diabetes risk?",
    "hypothesis": "Exercise reduces diabetes risk",
    "context": "Adults aged 40-60 with prediabetes",
    "population": "Adults aged 40-60 with prediabetes",
    "intervention": "Structured moderate aerobic exercise",
    "comparison": "Standard lifestyle counseling",
    "outcomes": "HbA1c reduction",
    "study_design": "RCT"
  }
}
```

### Response
```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "refined_hypotheses": [...],
    "evidence_summary": "...",
    "scoring_matrix": {...},
    "google_doc_url": "https://docs.google.com/...",
    "recommendations": "...",
    "metadata": {...},
    "langsmith_run_id": "..."
  }
}
```

## Validation Commands

### Preflight Check
```bash
# Validates all agents including hypothesis refiner
./scripts/hetzner-preflight.sh
```

### Hypothesis Refiner Smoke Test
```bash
# Specific check for hypothesis refiner
CHECK_HYPOTHESIS_REFINER=1 ./scripts/stagewise-smoke.sh

# All agents check (includes hypothesis refiner)
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
```

### Orchestrator Dispatch Test
```bash
# Via router
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "HYPOTHESIS_REFINEMENT",
    "request_id": "test-hr-001",
    "mode": "DEMO",
    "inputs": {
      "hypothesis": "Exercise improves diabetes outcomes"
    }
  }'
```

### Direct Proxy Test
```bash
# Health check
curl http://localhost:8000/health

# Readiness check (validates LangSmith connectivity)
curl http://localhost:8000/health/ready

# Direct sync call
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "HYPOTHESIS_REFINEMENT",
    "request_id": "test-hr-002",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Does exercise reduce diabetes risk?",
      "hypothesis": "Exercise reduces diabetes risk"
    }
  }'
```

## Local Build & Test

```bash
# Build the proxy image
docker build -t agent-hypothesis-refiner-proxy \
  -f services/agents/agent-hypothesis-refiner-proxy/Dockerfile .

# Start services (from docker-compose)
docker compose up -d agent-hypothesis-refiner-proxy orchestrator

# Check logs
docker compose logs -f agent-hypothesis-refiner-proxy

# Health check
docker compose exec agent-hypothesis-refiner-proxy curl -f http://localhost:8000/health

# Run smoke test
CHECK_HYPOTHESIS_REFINER=1 ./scripts/stagewise-smoke.sh
```

## Security & Compliance

### PHI-Safe Logging
- ✅ Only logs: `status_code`, `request_id`, `task_type`, `exception type`
- ✅ Never logs request/response bodies
- ✅ Exceptions logged as type names only (no stack traces with data)

### Secrets Management
- ✅ No secrets committed to repository
- ✅ Env var names documented (values in `.env` or secrets management)
- ✅ CI/gitleaks expected to pass

## Deployment Checklist

- [ ] Set `LANGSMITH_API_KEY` in `.env` or secrets management
- [ ] Set `LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID` in `.env`
- [ ] Build proxy image: `docker build -f services/agents/agent-hypothesis-refiner-proxy/Dockerfile .`
- [ ] Start proxy: `docker compose up -d agent-hypothesis-refiner-proxy`
- [ ] Verify health: `curl http://localhost:8000/health`
- [ ] Verify readiness: `curl http://localhost:8000/health/ready`
- [ ] Run preflight: `./scripts/hetzner-preflight.sh`
- [ ] Run smoke test: `CHECK_HYPOTHESIS_REFINER=1 ./scripts/stagewise-smoke.sh`
- [ ] Verify AGENT_ENDPOINTS_JSON includes: `"agent-hypothesis-refiner-proxy": "http://agent-hypothesis-refiner-proxy:8000"`
- [ ] Test dispatch via orchestrator
- [ ] Check validation artifacts: `/data/artifacts/validation/agent-hypothesis-refiner-proxy/`

## Troubleshooting

### Proxy container not starting
- Check `LANGSMITH_API_KEY` is set
- Check `LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID` is set
- Check logs: `docker compose logs agent-hypothesis-refiner-proxy`

### Health ready check fails (503)
- Verify `LANGSMITH_API_KEY` is valid
- Check network connectivity to LangSmith API
- Check proxy can reach `https://api.smith.langchain.com/api/v1/info`

### Router dispatch fails
- Verify `AGENT_ENDPOINTS_JSON` includes `agent-hypothesis-refiner-proxy`
- Check task type mapping in `ai-router.ts`
- Verify task type `HYPOTHESIS_REFINEMENT` in `ALLOWED_TASK_TYPES`

### Smoke test failures
- Ensure proxy container is running and healthy
- Check orchestrator can resolve agent URL
- Verify auth token is valid (if using AUTH_HEADER)

## References

- LangSmith config bundle: `services/agents/agent-hypothesis-refiner/`
- Proxy service: `services/agents/agent-hypothesis-refiner-proxy/`
- AGENT_INVENTORY.md - Full agent registry
- docker-compose.yml - Service definitions
- ai-router.ts - TaskType mappings
- task-contract.ts - Input schemas
