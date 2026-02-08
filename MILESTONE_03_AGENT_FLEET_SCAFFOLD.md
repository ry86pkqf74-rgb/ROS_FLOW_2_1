# Milestone 3 — Agent Fleet Template & Two Clones ✅ COMPLETE

**Status:** Inventory Capture Complete  
**Date Completed:** 2025-02-06  
**Branch:** chore/inventory-capture  
**Comprehensive Inventory:** See [AGENT_INVENTORY.md](researchflow-production-main/AGENT_INVENTORY.md)

## Directory Structure

```
services/agents/
├── _template/                          # Template for all agents
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       └── run.py
│   └── agent/
│       ├── __init__.py
│       ├── schemas.py
│       └── impl.py
├── agent-lit-retrieval/                # Clone 1 - Literature Retrieval
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       └── run.py
│   └── agent/
│       ├── __init__.py
│       ├── schemas.py
│       └── impl.py
└── agent-policy-review/                # Clone 2 - Policy Review
    ├── Dockerfile
    ├── requirements.txt
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   └── routes/
    │       ├── __init__.py
    │       ├── health.py
    │       └── run.py
    └── agent/
        ├── __init__.py
        ├── schemas.py
        └── impl.py
```

## Files Created

### Template Files

All three agents share the same structure. Differences are in:
1. Service names and titles in `app/main.py`
2. Health check response service name in `app/routes/health.py`
3. Agent-specific implementation logic in `agent/impl.py`

#### _template/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY services/agents/AGENT_NAME/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/agents/AGENT_NAME/app /app/app
COPY services/agents/AGENT_NAME/agent /app/agent

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### _template/requirements.txt
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
sse-starlette==2.1.3
orjson==3.10.12
httpx==0.27.2
aiohttp==3.10.11
python-dotenv==1.0.1
structlog==24.4.0
```

#### _template/app/main.py
```python
from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.run import router as run_router

app = FastAPI(title="ResearchFlow Agent Template", version="0.1.0")

app.include_router(health_router)
app.include_router(run_router)
```

#### _template/app/routes/health.py
```python
from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-template"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-template",
    }
```

#### _template/app/routes/run.py
```python
import time
import orjson
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import structlog

from agent.schemas import AgentRunRequest, AgentRunResponse
from agent.impl import run_sync, run_stream

logger = structlog.get_logger()

router = APIRouter()


@router.post("/agents/run/sync", response_model=AgentRunResponse)
async def agents_run_sync(req: AgentRunRequest):
    started = time.time()
    logger.info(
        "sync_request",
        request_id=req.request_id,
        task_type=req.task_type,
    )
    result = await run_sync(req.model_dump())
    result.setdefault("usage", {})
    result["usage"]["duration_ms"] = int((time.time() - started) * 1000)
    logger.info(
        "sync_complete",
        request_id=req.request_id,
        duration_ms=result["usage"]["duration_ms"],
    )
    return AgentRunResponse(**result)


@router.post("/agents/run/stream")
async def agents_run_stream(req: Request):
    payload = await req.json()
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    
    logger.info(
        "stream_request_start",
        request_id=request_id,
        task_type=task_type,
    )

    async def event_generator():
        async for evt in run_stream(payload):
            yield {
                "event": evt.get("type", "message"),
                "data": orjson.dumps(evt).decode("utf-8"),
            }

    return EventSourceResponse(event_generator())
```

#### _template/agent/schemas.py
```python
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List


class Budgets(BaseModel):
    max_output_tokens: int = 1200
    max_context_tokens: int = 6000
    max_escalations: int = 2
    timeout_ms: int = 600000


class AgentRunRequest(BaseModel):
    request_id: str = Field(..., description="Trace/request id")
    task_type: str
    workflow_id: Optional[str] = None
    stage_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: str = "DEMO"
    risk_tier: str = "NON_SENSITIVE"
    domain_id: str = "clinical"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    budgets: Budgets = Field(default_factory=Budgets)


class AgentRunResponse(BaseModel):
    status: str = "ok"
    request_id: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
```

#### _template/agent/impl.py
```python
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import structlog

logger = structlog.get_logger()


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous agent execution."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    
    logger.info(
        "agent_sync_start",
        request_id=request_id,
        task_type=task_type,
    )
    
    # Agent-specific implementation goes here
    outputs = await _execute_task(payload)
    
    logger.info(
        "agent_sync_complete",
        request_id=request_id,
        task_type=task_type,
    )
    
    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
        "artifacts": [],
        "provenance": {},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming agent execution with SSE events."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    
    logger.info(
        "agent_stream_start",
        request_id=request_id,
        task_type=task_type,
    )
    
    # Emit started event
    yield {
        "type": "started",
        "request_id": request_id,
        "task_type": task_type,
    }
    
    # Emit progress event
    yield {
        "type": "progress",
        "request_id": request_id,
        "progress": 50,
        "step": "processing",
    }
    
    # Execute agent task
    outputs = await _execute_task(payload)
    
    # Emit final event
    yield {
        "type": "final",
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
    }
    
    # Emit complete event
    yield {
        "type": "complete",
        "success": True,
        "duration_ms": 0,
    }
    
    logger.info(
        "agent_stream_complete",
        request_id=request_id,
        task_type=task_type,
    )


async def _execute_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent-specific task execution.
    This should be overridden in subclasses.
    """
    # Placeholder: return minimal stub output
    return {
        "status": "stub",
        "message": "Agent not yet implemented",
    }
```

---

### agent-lit-retrieval Agent

**Key customizations:**

#### app/main.py
```python
app = FastAPI(title="ResearchFlow Agent: Literature Retrieval", version="0.1.0")
```

#### app/routes/health.py
```python
@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-lit-retrieval"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-lit-retrieval",
        "retrieval_backend": os.getenv("RETRIEVAL_BACKEND", "pubmed"),
    }
```

#### agent/impl.py (stub implementation)
```python
async def _execute_retrieval(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Literature retrieval task execution.
    Stub implementation returns placeholder outputs.
    """
    query = inputs.get("query", "")
    max_results = inputs.get("max_results", 10)
    
    return {
        "query": query,
        "retrieved": [],
        "count": 0,
        "source": "pubmed_stub",
        "max_results_requested": max_results,
    }
```

---

### agent-policy-review Agent

**Key customizations:**

#### app/main.py
```python
app = FastAPI(title="ResearchFlow Agent: Policy Review", version="0.1.0")
```

#### app/routes/health.py
```python
@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-policy-review"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-policy-review",
        "governance_mode": os.getenv("GOVERNANCE_MODE", "DEMO"),
    }
```

#### agent/impl.py (stub implementation)
```python
async def _execute_policy_check(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Policy review task execution.
    Stub implementation returns placeholder governance decision.
    """
    resource_id = inputs.get("resource_id", "")
    domain = inputs.get("domain", "clinical")
    
    return {
        "resource_id": resource_id,
        "domain": domain,
        "allowed": True,
        "reasons": ["stub_approval"],
        "risk_level": "low",
    }
```

---

## Docker Compose Changes

Added to `docker-compose.yml` after `agent-lit-retrieval` service:

```yaml
  # ===================
  # Agent Policy Review (governance & compliance)
  # ===================
  agent-policy-review:
    build:
      context: .
      dockerfile: services/agents/agent-policy-review/Dockerfile
    container_name: researchflow-agent-policy-review
    restart: unless-stopped
    environment:
      - GOVERNANCE_MODE=${GOVERNANCE_MODE:-DEMO}
      - PYTHONUNBUFFERED=1
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

Updated AGENT_ENDPOINTS_JSON in orchestrator environment:

**Before:**
```
'AGENT_ENDPOINTS_JSON={"agent-stage2-lit":"http://agent-stage2-lit:8000","agent-lit-retrieval":"http://agent-lit-retrieval:8000"}'
```

**After:**
```
'AGENT_ENDPOINTS_JSON={"agent-stage2-lit":"http://agent-stage2-lit:8000","agent-lit-retrieval":"http://agent-lit-retrieval:8000","agent-policy-review":"http://agent-policy-review:8000"}'
```

---

## How to Build & Run

### Build all agents (no rebuild on existing images):

```bash
cd /Users/ros/Desktop/ROS_FLOW_2_1/researchflow-production-main

# Build just the two new agents
docker compose build agent-lit-retrieval agent-policy-review

# Or rebuild everything
docker compose build
```

### Start agents (without dependencies):

```bash
docker compose up -d --no-deps agent-lit-retrieval agent-policy-review
```

### Health checks (run each in a separate terminal):

**Terminal A - agent-lit-retrieval:**
```bash
curl -v http://localhost:8000/health
curl -v http://localhost:8000/health/ready
```

**Terminal B - agent-policy-review:**
```bash
# Need to map port or access from within docker network
docker compose exec agent-policy-review curl -s http://localhost:8000/health
docker compose exec agent-policy-review curl -s http://localhost:8000/health/ready
```

Or use docker-compose service names from orchestrator:
```bash
docker compose exec orchestrator sh -lc 'curl -s http://agent-lit-retrieval:8000/health && echo && curl -s http://agent-policy-review:8000/health'
```

---

## ✅ MILESTONE 3 COMPLETION SUMMARY

### Deliverables Completed

1. **✅ AGENT_INVENTORY.md Created**
   - 572 lines of comprehensive documentation
   - Catalogued 48+ agents across all categories
   - Documented 6 model providers
   - Listed 15+ prompt files
   - Mapped all external integrations

2. **✅ Agent Categories Documented**
   - 13 Microservice Agents (Docker containers)
   - 20 Workflow Stage Agents
   - 8 LangGraph Agents
   - 15+ Specialized Analysis Agents

3. **✅ Integration Points Mapped**
   - AI Bridge architecture
   - Model routing patterns
   - External API integrations (NCBI, Semantic Scholar, Composio)
   - Health check procedures

4. **✅ Architecture Patterns Documented**
   - Microservice agent pattern (FastAPI)
   - Stage agent pattern (Workflow Engine)
   - LangGraph agent pattern (Stateful workflows)
   - Model call patterns (3 variants)

### Gap Analysis

**Stub Agents Identified (Not Implemented):**
- `agent-stage2-synthesize` - Evidence synthesis
- `agent-results-writer` - Results section writing
- `agent-discussion-writer` - Discussion section writing
- `agent-lit-triage` - Literature triage
- `agent-evidence-synth` - Evidence synthesis

**Missing Integrations:**
- GitHub Actions integration
- Slack notifications
- Email reports

**Enhancement Opportunities:**
- Agent performance metrics
- Per-agent cost tracking
- A/B testing framework
- Agent versioning system

### Files Modified/Created

```
✅ NEW: researchflow-production-main/AGENT_INVENTORY.md (572 lines)
📝 UPDATED: MILESTONE_03_AGENT_FLEET_SCAFFOLD.md (this file)
```

### Quick Start Commands

```bash
# View the complete inventory
cat researchflow-production-main/AGENT_INVENTORY.md

# Start all agents
cd researchflow-production-main
docker compose up -d

# Check agent health
docker compose ps | grep agent-

# Run health check script
bash /Users/ros/Desktop/ROS_FLOW_2_1/milestone3_healthcheck.sh
```

### Next Steps (Ready for Merge)

1. **Review AGENT_INVENTORY.md** - Comprehensive documentation ready
2. **Validate completeness** - All agents, prompts, and integrations catalogued
3. **Merge to main** - `chore/inventory-capture` branch ready
4. **Plan agent implementations** - Use gap analysis to prioritize stub agents

---

## Original Implementation Notes (Pre-Inventory)

Below is the original scaffold documentation for the two agent clones (agent-lit-retrieval and agent-policy-review).

### Next Steps (Step 11)

Once both agents are healthy:
1. Update orchestrator routing logic to route specific task types to these agents
2. Add integration tests for agent dispatch
3. Expand fleet with additional specialized agents

**Status:** Template and clones exist in codebase. Comprehensive inventory now available in AGENT_INVENTORY.md.
