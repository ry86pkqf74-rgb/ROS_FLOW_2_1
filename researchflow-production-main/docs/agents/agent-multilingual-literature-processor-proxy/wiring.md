# Multilingual Literature Processor Agent - Wiring Documentation

**Agent Key:** `agent-multilingual-literature-processor-proxy`  
**Task Type:** `MULTILINGUAL_LITERATURE_PROCESSING`  
**Status:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)

---

## Overview

The Multilingual Literature Processor is a LangSmith cloud-hosted agent that discovers, translates, analyzes, and synthesizes scientific literature across 14+ languages. It bridges language barriers in academic research by making non-English scientific literature accessible and actionable.

This document describes how the agent is wired into the ResearchFlow production system.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    ResearchFlow Orchestrator                    │
│                   (services/orchestrator)                       │
│                                                                 │
│  ai-router.ts: MULTILINGUAL_LITERATURE_PROCESSING → agent key  │
│  task-contract.ts: Validates inputs (query required)           │
│  AGENT_ENDPOINTS_JSON: agent-multilingual-literature-          │
│                        processor-proxy → URL                    │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              │ HTTP POST /agents/run/sync
                              │ or /agents/run/stream
                              ↓
┌────────────────────────────────────────────────────────────────┐
│      Multilingual Literature Processor Proxy Service           │
│    (services/agents/agent-multilingual-literature-             │
│     processor-proxy)                                            │
│                                                                 │
│  - FastAPI app (Python 3.11)                                   │
│  - Port: 8000 (internal)                                       │
│  - Networks: backend + frontend                                │
│  - Health: /health, /health/ready                              │
│  - Adapts ResearchFlow contract → LangSmith API                │
│  - PHI-safe logging (no request/response bodies)               │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              │ HTTPS POST
                              │ x-api-key: LANGSMITH_API_KEY
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                   LangSmith Cloud API                           │
│          (api.smith.langchain.com/api/v1)                       │
│                                                                 │
│  - Cloud-hosted agent execution                                │
│  - Multi-language processing                                   │
│  - Google Workspace integration                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Locations

| Component | Path |
|-----------|------|
| **Config Bundle** | `services/agents/agent-multilingual-literature-processor/` |
| **Proxy Service** | `services/agents/agent-multilingual-literature-processor-proxy/` |
| **Orchestrator Router** | `services/orchestrator/src/routes/ai-router.ts` |
| **Task Contract** | `services/orchestrator/src/services/task-contract.ts` |
| **Docker Compose** | `researchflow-production-main/docker-compose.yml` |
| **Preflight Script** | `scripts/hetzner-preflight.sh` |
| **Smoke Test** | `scripts/stagewise-smoke.sh` |
| **Wiring Docs** | `docs/agents/agent-multilingual-literature-processor-proxy/wiring.md` (this file) |

---

## Configuration Bundle

The LangSmith agent configuration is stored separately from the proxy:

```
services/agents/agent-multilingual-literature-processor/
├── AGENTS.md        # Agent prompt and behavior specification
├── config.json      # Agent metadata and capabilities
└── tools.json       # Available tools for the agent
```

**Purpose**: This bundle defines the agent's behavior, capabilities, and tool access. It is imported from LangSmith and serves as documentation for what the agent can do.

**Note**: The proxy service does not read these files at runtime. They are for documentation and LangSmith configuration only.

---

## Proxy Service

The proxy service is a thin FastAPI adapter:

```
services/agents/agent-multilingual-literature-processor-proxy/
├── Dockerfile           # Multi-stage build (Python 3.11-slim)
├── requirements.txt     # Dependencies (FastAPI, httpx, pydantic)
├── README.md            # Service documentation
└── app/
    ├── __init__.py
    ├── config.py        # Settings (pydantic-settings)
    └── main.py          # FastAPI app with routes
```

**Build Context**: Repo root (`.` in docker-compose.yml)  
**Container Name**: `researchflow-agent-multilingual-literature-processor-proxy`  
**Internal URL**: `http://agent-multilingual-literature-processor-proxy:8000`

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness probe (always returns 200) |
| `/health/ready` | GET | Readiness probe (validates LangSmith connectivity) |
| `/agents/run/sync` | POST | Synchronous agent execution |
| `/agents/run/stream` | POST | Streaming agent execution (SSE) |

### Environment Variables

**Required:**
- `LANGSMITH_API_KEY` - LangSmith API authentication
- `LANGSMITH_AGENT_ID` - Set via `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID`

**Optional:**
- `LANGSMITH_API_URL` (default: `https://api.smith.langchain.com/api/v1`)
- `LANGSMITH_TIMEOUT_SECONDS` (default: `300`)
- `LANGCHAIN_PROJECT` (default: `researchflow-multilingual-literature-processor`)
- `LANGCHAIN_TRACING_V2` (default: `false`)
- `LOG_LEVEL` (default: `INFO`)

---

## Docker Compose Wiring

### Service Definition

Located in `docker-compose.yml` after `agent-artifact-auditor-proxy`:

```yaml
agent-multilingual-literature-processor-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-multilingual-literature-processor-proxy/Dockerfile
  container_name: researchflow-agent-multilingual-literature-processor-proxy
  restart: unless-stopped
  stop_grace_period: 30s
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
    - LANGSMITH_AGENT_ID=${LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID:-}
    - LANGSMITH_API_URL=${LANGSMITH_API_URL:-https://api.smith.langchain.com/api/v1}
    - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_TIMEOUT_SECONDS:-300}
    - LOG_LEVEL=${AGENT_LOG_LEVEL:-INFO}
    - LANGCHAIN_PROJECT=${LANGCHAIN_PROJECT:-researchflow-multilingual-literature-processor}
    - LANGCHAIN_TRACING_V2=${LANGCHAIN_TRACING_V2:-false}
    - PYTHONUNBUFFERED=1
  expose:
    - "8000"
  networks:
    - backend   # Internal orchestrator communication
    - frontend  # External LangSmith API access
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
        memory: 256M
```

### Endpoint Registry

Added to `AGENT_ENDPOINTS_JSON` in orchestrator environment:

```json
{
  "agent-multilingual-literature-processor-proxy": "http://agent-multilingual-literature-processor-proxy:8000"
}
```

**Location in docker-compose.yml**: Line ~195 (orchestrator environment)

---

## Orchestrator Wiring

### 1. Router Mapping (`ai-router.ts`)

**File**: `services/orchestrator/src/routes/ai-router.ts`  
**Location**: Lines ~318-352

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ...existing mappings...
  MULTILINGUAL_LITERATURE_PROCESSING: 'agent-multilingual-literature-processor-proxy',
};
```

**Effect**: When a request with `task_type: "MULTILINGUAL_LITERATURE_PROCESSING"` is dispatched, the orchestrator resolves the agent key to the URL from `AGENT_ENDPOINTS_JSON`.

### 2. Task Contract (`task-contract.ts`)

**File**: `services/orchestrator/src/services/task-contract.ts`

#### Allowed Task Types (Lines ~7-19)

```typescript
export const ALLOWED_TASK_TYPES = [
  // ...existing types...
  'MULTILINGUAL_LITERATURE_PROCESSING',
] as const;
```

#### Input Requirements (Lines ~46-76)

```typescript
const INPUT_REQUIREMENTS: Record<AllowedTaskType, { required: string[]; optional?: string[] }> = {
  // ...existing requirements...
  MULTILINGUAL_LITERATURE_PROCESSING: {
    required: ['query'],
    optional: [
      'language',
      'languages',
      'output_language',
      'date_range',
      'citations',
      'abstracts',
      'full_text',
      'context',
      'output_format'
    ],
  },
};
```

**Validation Behavior**:
- `query` field is mandatory (throws `INVALID_INPUTS` if missing)
- All other fields are optional and permissive
- Empty `inputs: {}` is rejected (query required)

---

## Validation & Testing

### Preflight Check (`hetzner-preflight.sh`)

**What it validates:**
1. `AGENT_ENDPOINTS_JSON` contains `agent-multilingual-literature-processor-proxy` key
2. Container `researchflow-agent-multilingual-literature-processor-proxy` is running
3. Health endpoint returns 200 OK
4. Required environment variables are set:
   - `LANGSMITH_API_KEY`
   - `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID`

**Run command:**
```bash
cd researchflow-production-main
./scripts/hetzner-preflight.sh
```

**Expected output:**
```
✓ agent-multilingual-literature-processor-proxy [Registry] http://agent-multilingual-literature-processor-proxy:8000
✓ agent-multilingual-literature-processor-proxy [Container] running
✓ agent-multilingual-literature-processor-proxy [Health] responding
✓ LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID configured
```

### Smoke Test (`stagewise-smoke.sh`)

**What it tests:**
1. Router dispatch routes `MULTILINGUAL_LITERATURE_PROCESSING` to correct agent
2. Proxy container is running and healthy
3. Deterministic fixture test with minimal query (DEMO mode, no external calls)
4. Artifact validation directory creation
5. Writes summary.json to `/data/artifacts/validation/agent-multilingual-literature-processor-proxy/<timestamp>/`

**Run command:**
```bash
cd researchflow-production-main
CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 ./scripts/stagewise-smoke.sh
```

or to test all agents:

```bash
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
```

**Expected output:**
```
[16] Multilingual Literature Processor Agent Check (optional - LangSmith-based)
[16a] Checking LANGSMITH_API_KEY and agent ID configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
✓ LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID is configured
[16b] POST /api/ai/router/dispatch (MULTILINGUAL_LITERATURE_PROCESSING)
Router dispatch OK: routed to agent-multilingual-literature-processor-proxy
✓ Correctly routed to agent-multilingual-literature-processor-proxy
[16c] Checking proxy container health
✓ agent-multilingual-literature-processor-proxy container is running
✓ Proxy health endpoint responding
[16d] Deterministic multilingual processing test (fixture-based)
✓ Multilingual processing completed (ok: true)
✓ Response contains papers field
✓ Response contains processing results
[16e] Checking artifacts directory structure
✓ /data/artifacts exists
✓ Wrote validation artifact to /data/artifacts/validation/agent-multilingual-literature-processor-proxy/20260208T123456Z/summary.json
Multilingual Literature Processor Agent check complete (optional - does not block)
```

---

## Request/Response Contracts

### Request Schema (ResearchFlow → Proxy)

```json
{
  "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
  "request_id": "req-123",
  "workflow_id": "wf-456",
  "user_id": "user-789",
  "mode": "DEMO",
  "risk_tier": "NON_SENSITIVE",
  "domain_id": "clinical",
  "inputs": {
    "query": "diabetes treatment",
    "language": "Spanish",
    "languages": ["Spanish", "Portuguese", "English"],
    "output_language": "English",
    "date_range": "2020-2024",
    "citations": true,
    "abstracts": true,
    "full_text": false,
    "context": {},
    "output_format": "structured"
  }
}
```

### Response Schema (Proxy → ResearchFlow)

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "papers": [
      {
        "title": "Tratamiento de la diabetes...",
        "title_en": "Diabetes treatment...",
        "authors": ["García, M.", "López, J."],
        "journal": "Revista Médica",
        "year": 2023,
        "language": "Spanish",
        "abstract": "...",
        "abstract_en": "...",
        "doi": "10.1234/...",
        "citations": 15
      }
    ],
    "translations": {
      "abstracts": 12,
      "full_text": 0
    },
    "synthesis": {
      "key_findings": "...",
      "regional_variations": "...",
      "consensus": "..."
    },
    "google_doc_url": "https://docs.google.com/document/d/...",
    "citation_export": "BibTeX format...",
    "language_distribution": {
      "Spanish": 8,
      "Portuguese": 4,
      "English": 12
    },
    "quality_notes": [
      "3 papers required manual term disambiguation",
      "All citations verified via DOI"
    ],
    "metadata": {
      "search_duration_ms": 45000,
      "databases_searched": ["PubMed", "SciELO", "Semantic Scholar"]
    },
    "langsmith_run_id": "run-abc123"
  }
}
```

---

## Environment Setup

### Required Variables (in `.env`)

```bash
# LangSmith API Authentication (required for all LangSmith proxies)
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here

# Agent-specific UUID (get from LangSmith UI)
LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID=your-agent-uuid-here
```

### Optional Variables

```bash
# Timeout configuration (default: 300 seconds / 5 minutes)
LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_TIMEOUT_SECONDS=300

# LangSmith project name for tracing
LANGCHAIN_PROJECT=researchflow-multilingual-literature-processor

# Enable LangSmith tracing (for debugging)
LANGCHAIN_TRACING_V2=false

# Agent log level
AGENT_LOG_LEVEL=INFO
```

### Obtaining LangSmith Agent ID

1. Log in to LangSmith (https://smith.langchain.com/)
2. Navigate to your organization
3. Go to "Agents" or "Assistants"
4. Find or create "Multilingual Literature Processor" agent
5. Copy the Agent ID (UUID format)
6. Set `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID=<that-uuid>` in `.env`

---

## Deployment Commands

### Build Proxy Image

```bash
cd researchflow-production-main

# Build proxy image (build context is repo root)
docker compose build agent-multilingual-literature-processor-proxy
```

### Start Proxy Service

```bash
# Start proxy + dependencies
docker compose up -d agent-multilingual-literature-processor-proxy

# Or start entire stack
docker compose up -d
```

### Verify Deployment

```bash
# Check container status
docker compose ps agent-multilingual-literature-processor-proxy

# Check logs
docker compose logs -f agent-multilingual-literature-processor-proxy

# Test health endpoint
docker compose exec agent-multilingual-literature-processor-proxy curl -f http://localhost:8000/health

# Test readiness endpoint
docker compose exec agent-multilingual-literature-processor-proxy curl -f http://localhost:8000/health/ready
```

---

## Validation Commands

### Run Preflight Check

```bash
cd researchflow-production-main
./scripts/hetzner-preflight.sh
```

**What it checks:**
- All 25 mandatory agents (including multilingual processor) are healthy
- LANGSMITH_API_KEY is set
- LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID is set
- Container is running
- Health endpoint responds

**Expected**: Exit 0 with all checks passed

### Run Smoke Test (Multilingual Processor Only)

```bash
cd researchflow-production-main
CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 \
  DEV_AUTH=true \
  ./scripts/stagewise-smoke.sh
```

**What it tests:**
- Router dispatch routes to correct agent
- Proxy health check passes
- Deterministic fixture test (DEMO mode with minimal query)
- Artifact directory creation
- Summary JSON written to `/data/artifacts/validation/agent-multilingual-literature-processor-proxy/<timestamp>/summary.json`

### Run Smoke Test (All Agents)

```bash
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

**Effect**: Tests all 25 agents including multilingual processor via orchestrator dispatch

---

## Integration with Orchestrator

### Dispatch via Orchestrator Router

```bash
# Get auth token (dev mode)
export TOKEN=$(curl -sS -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -H "X-Dev-User-Id: test-user" | jq -r '.accessToken')

# Dispatch multilingual literature processing task
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "query": "hypertension treatment guidelines",
      "languages": ["English", "Spanish", "Chinese"],
      "output_language": "English",
      "abstracts": true
    }
  }'
```

**Expected response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-multilingual-literature-processor-proxy",
  "agent_url": "http://agent-multilingual-literature-processor-proxy:8000",
  "budgets": {},
  "rag_plan": {},
  "request_id": "test-001"
}
```

### Direct Proxy Call (Bypass Router)

```bash
# Direct call to proxy (inside backend network)
docker compose exec orchestrator curl -X POST \
  http://agent-multilingual-literature-processor-proxy:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "MULTILINGUAL_LITERATURE_PROCESSING",
    "request_id": "direct-001",
    "mode": "DEMO",
    "inputs": {
      "query": "cardiovascular disease prevention"
    }
  }'
```

---

## Troubleshooting

### Health Check Fails

**Symptoms:**
```bash
$ docker compose ps agent-multilingual-literature-processor-proxy
# Shows: unhealthy or restarting
```

**Diagnostics:**
```bash
# Check logs
docker compose logs --tail=50 agent-multilingual-literature-processor-proxy

# Check environment variables
docker compose exec agent-multilingual-literature-processor-proxy env | grep LANGSMITH

# Check build
docker compose build --no-cache agent-multilingual-literature-processor-proxy
```

**Common causes:**
- Missing `LANGSMITH_API_KEY` or `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID`
- Invalid LangSmith API URL
- Build failure (missing requirements.txt)
- Port 8000 already in use (unlikely in backend network)

### Readiness Check Fails

**Symptoms:**
```bash
$ curl http://localhost:8000/health/ready
# Returns: 503 Service Unavailable
```

**Diagnostics:**
```bash
# Test LangSmith API connectivity
docker compose exec agent-multilingual-literature-processor-proxy curl -v \
  https://api.smith.langchain.com/api/v1/info \
  -H "x-api-key: $LANGSMITH_API_KEY"
```

**Common causes:**
- LangSmith API unreachable (network/DNS issue)
- Invalid `LANGSMITH_API_KEY`
- LangSmith agent ID not set or incorrect
- LangSmith API outage (check status.langchain.com)

### Router Dispatch Fails

**Symptoms:**
```bash
# Router returns: "AGENT_NOT_CONFIGURED"
```

**Diagnostics:**
```bash
# Verify AGENT_ENDPOINTS_JSON contains the key
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | \
  python3 -c 'import json,sys; print(json.load(sys.stdin).get("agent-multilingual-literature-processor-proxy"))'

# Expected: http://agent-multilingual-literature-processor-proxy:8000
```

**Remediation:**
1. Verify AGENT_ENDPOINTS_JSON in docker-compose.yml includes the agent
2. Restart orchestrator: `docker compose up -d --force-recreate orchestrator`
3. Re-run preflight: `./scripts/hetzner-preflight.sh`

### Agent Returns Empty Results

**Symptoms:**
```json
{
  "ok": true,
  "outputs": {
    "papers": []
  }
}
```

**Common causes:**
- Running in DEMO mode (may return mock data)
- LangSmith agent not configured with tools
- Query too narrow (no matching papers)
- Language combination has limited coverage

**Diagnostics:**
1. Check LangSmith agent configuration in LangSmith UI
2. Verify agent has required tools enabled (Tavily, Exa, Google Workspace)
3. Test with broader query
4. Check LangSmith run logs in LangSmith UI (use `langsmith_run_id` from response)

---

## CI/CD Integration

### GitHub Actions

When this agent is merged:

1. **Image Build**: Proxy image built and pushed to GHCR
   ```yaml
   - name: Build Multilingual Literature Processor Proxy
     run: |
       docker build -t ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/agent-multilingual-literature-processor-proxy:${{ github.sha }} \
         -f services/agents/agent-multilingual-literature-processor-proxy/Dockerfile .
   ```

2. **Preflight Validation**: `hetzner-preflight.sh` must pass
   - Validates agent is in AGENT_ENDPOINTS_JSON
   - Checks container health
   - Verifies required env vars (names only, no secrets)

3. **Smoke Test**: Optional agent check can be added to CI pipeline
   ```bash
   CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 ./scripts/stagewise-smoke.sh
   ```

### Gitleaks

**No secrets committed**: All configuration uses environment variable references only.

**Validation:**
```bash
cd researchflow-production-main
gitleaks detect --no-git --verbose
```

**Expected**: No leaks detected

---

## Production Deployment

### Step 1: Set Environment Variables

On production server (e.g., Hetzner ROSflow2):

```bash
cd /opt/researchflow/researchflow-production-main

# Edit .env
nano .env

# Add:
LANGSMITH_API_KEY=lsv2_pt_your_production_key
LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID=your-agent-uuid
```

### Step 2: Pull Images

```bash
# Set IMAGE_TAG to specific commit or release
export IMAGE_TAG=abc1234

# Pull all images (including new proxy)
docker compose pull

# Or build locally if needed
docker compose build agent-multilingual-literature-processor-proxy
```

### Step 3: Run Preflight

```bash
./scripts/hetzner-preflight.sh
```

**Must exit 0 before proceeding.**

### Step 4: Deploy

```bash
# Start all services (including new agent)
docker compose up -d

# Or start agent only
docker compose up -d agent-multilingual-literature-processor-proxy

# Restart orchestrator to pick up new AGENT_ENDPOINTS_JSON
docker compose up -d --force-recreate orchestrator
```

### Step 5: Validate

```bash
# Run smoke test
CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh

# Check logs
docker compose logs -f agent-multilingual-literature-processor-proxy
```

---

## Monitoring

### Logs

```bash
# Tail proxy logs
docker compose logs -f agent-multilingual-literature-processor-proxy

# Check for errors
docker compose logs agent-multilingual-literature-processor-proxy | grep -i error

# Check LangSmith API calls
docker compose logs agent-multilingual-literature-processor-proxy | grep "Calling LangSmith"
```

### Health Metrics

```bash
# Container status
docker compose ps agent-multilingual-literature-processor-proxy

# Health endpoint
curl -f http://127.0.0.1:8000/health  # If proxy port is exposed

# Via orchestrator (internal network)
docker compose exec orchestrator curl -f http://agent-multilingual-literature-processor-proxy:8000/health

# Readiness
docker compose exec orchestrator curl -f http://agent-multilingual-literature-processor-proxy:8000/health/ready
```

### Resource Usage

```bash
# CPU and memory
docker stats researchflow-agent-multilingual-literature-processor-proxy

# Resource limits (from compose)
# Limits: 0.5 CPU, 512M RAM
# Reservations: 0.25 CPU, 256M RAM
```

---

## Security Notes

### PHI Protection

- **No request/response body logging**: Proxy uses PHI-safe logging (only metadata)
- **No local PHI storage**: All data passes through to LangSmith cloud
- **Audit trail**: Request IDs, task types, and timestamps logged for compliance

### Network Isolation

- **Backend network**: Internal communication with orchestrator
- **Frontend network**: External LangSmith API access only
- **No public ports**: Service exposed only within Docker networks

### API Key Management

- `LANGSMITH_API_KEY` loaded from `.env` (not committed)
- Never logged or exposed in responses
- Validated at startup (readiness check)

---

## Maintenance

### Updating the Agent

To update the LangSmith agent configuration:

1. **LangSmith UI**: Update agent prompt, tools, or settings in LangSmith
2. **No proxy changes needed**: Proxy is a thin adapter (unless contract changes)
3. **Test**: Run smoke test to verify updated behavior
4. **No redeployment needed**: Changes take effect immediately

### Updating the Proxy

To update proxy code (rare):

1. Edit files in `services/agents/agent-multilingual-literature-processor-proxy/`
2. Rebuild: `docker compose build agent-multilingual-literature-processor-proxy`
3. Deploy: `docker compose up -d agent-multilingual-literature-processor-proxy`
4. Test: Run smoke test

### Scaling

Current resource allocation is sufficient for:
- ~10-20 concurrent requests
- 5-minute timeout per request
- Mixed sync/stream usage

To scale up:
1. Increase resource limits in docker-compose.yml
2. Monitor LangSmith API rate limits
3. Consider multiple replicas (not currently supported in compose)

---

## Related Documentation

- **Agent Definition**: `services/agents/agent-multilingual-literature-processor/AGENTS.md`
- **Proxy README**: `services/agents/agent-multilingual-literature-processor-proxy/README.md`
- **Config**: `services/agents/agent-multilingual-literature-processor/config.json`
- **Tools**: `services/agents/agent-multilingual-literature-processor/tools.json`
- **Agent Inventory**: `AGENT_INVENTORY.md` (Section 1.4)
- **Orchestration Guide**: `docs/maintenance/agent-orchestration.md`

---

## Quick Reference

### Validation Command Summary

```bash
# Preflight (all agents)
./scripts/hetzner-preflight.sh

# Smoke test (this agent only)
CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh

# Smoke test (all agents)
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

### Key Configuration Points

| Component | File | Line(s) | Key |
|-----------|------|---------|-----|
| **Compose Service** | `docker-compose.yml` | ~1405-1440 | `agent-multilingual-literature-processor-proxy:` |
| **Endpoint Registry** | `docker-compose.yml` | ~195 | `AGENT_ENDPOINTS_JSON` |
| **Router Mapping** | `ai-router.ts` | ~351 | `MULTILINGUAL_LITERATURE_PROCESSING:` |
| **Task Allowlist** | `task-contract.ts` | ~19 | `ALLOWED_TASK_TYPES` |
| **Input Schema** | `task-contract.ts` | ~76-78 | `MULTILINGUAL_LITERATURE_PROCESSING:` |
| **Preflight Env Vars** | `hetzner-preflight.sh` | ~407 | `REQUIRED_ENV_VARS` |
| **Smoke Test Flag** | `stagewise-smoke.sh` | ~36 | `CHECK_MULTILINGUAL_LITERATURE_PROCESSOR` |
| **Smoke Test Mapping** | `stagewise-smoke.sh` | ~908 | `AGENT_TASK_TYPES` |

### Environment Variables Summary

**Required** (names only, no values committed):
- `LANGSMITH_API_KEY`
- `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID`

**Optional** (with defaults):
- `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_TIMEOUT_SECONDS` (300)
- `LANGCHAIN_PROJECT` (researchflow-multilingual-literature-processor)
- `LANGCHAIN_TRACING_V2` (false)
- `AGENT_LOG_LEVEL` (INFO)

---

**Version**: 1.0.0  
**Created**: 2026-02-08  
**Maintained By**: ResearchFlow Platform Team
