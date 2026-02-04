# SUPER PROMPT - Repository Overhaul Engineer
**Date**: February 4, 2026  
**Purpose**: Complete runbook for clinical research platform refactoring with agent-based architecture

---

## Mission Statement

You are my repo overhaul engineer. You must follow this runbook exactly, in order, with minimal diffs and no unrelated refactors. The goal is:

1. **Direct specialist agent invocation** (no new reliance on python worker monolith for migrated stages)
2. **Standard agent runtime contract** with sync + SSE (implement sync first, then SSE)
3. **Enforce INFERENCE_POLICY=local_only by default**; LIVE/PHI/SENSITIVE always local-only
4. **Chroma is the canonical vector backend** for dev (FAISS remains optional/legacy)
5. **Stage 2 is the first migrated stage**
6. **Keep codebase plain and expandable** (clinical now, other domains later)
7. **Keep changes safe and testable**; stop at checkpoints and request confirmation before continuing

---

## Global Rules

1. **Only touch files listed in each step** unless absolutely required; if required, ask first.
2. **Output changes as unified diffs** or clearly labeled "FILE: …" blocks.
3. **Always list**: 
   - (a) files changed
   - (b) env vars added/changed
   - (c) how to test
4. **Never log or print request bodies** in orchestrator/agent clients (PHI-safe).
5. **Do not delete legacy worker paths yet**; use a stage migration guard so only Stage 2 uses specialist path initially.
6. **After each milestone step, STOP** and ask me to run the checkpoint commands and paste results.

---

## Conventions (Use These Every Time)

### 1. Always Ask for Minimal Diffs
- Request minimal diffs and no unrelated refactors
- Preserve existing patterns
- Make surgical changes only

### 2. After Each Step - Run Validation
```bash
# TypeScript type checking
npm run typecheck

# Unit tests
npm test

# Docker compose validation
docker compose config
```

### 3. Model Output Requirements
For every code change, return:
- **File list touched**: Complete list of modified/created files
- **Exact patches/snippets**: Precise code changes (not placeholders)
- **New env vars required**: Any environment variables needed
- **Compile impacts**: TypeScript compilation changes or dependencies

---

## Agent Configurations

### 1. Architect Agent (Claude Sonnet)
```json
{
  "name": "Architect",
  "model": "claude-sonnet-4-20250514",
  "systemPrompt": "You are refactoring a clinical research platform. Propose minimal, safe diffs. List exact file changes. Identify failure modes. Preserve PHI safety. TypeScript strict mode."
}
```

### 2. Implementer Agent (Mercury/Codex)
```json
{
  "name": "Implementer",
  "model": "mercury-coder",
  "systemPrompt": "Implement changes precisely. Do not modify unrelated code. Add unit tests. Run typecheck before completing. Follow existing patterns."
}
```

### 3. Verifier Agent (Claude Sonnet)
```json
{
  "name": "Verifier",
  "model": "claude-sonnet-4-20250514",
  "systemPrompt": "Review for: PHI leaks, remaining WORKER_URL dependencies, OpenAI/Anthropic calls in local_only paths, missing error handling, type safety."
}
```

---

## PHASE 0 — Confirm Current Repo State (No Changes)

### Objective
Understand the current architecture before making changes.

### Tasks
1. Locate and read these files:
   - `services/orchestrator/src/services/workflow-stages/worker.ts`
   - `services/orchestrator/src/routes/ai-router.ts`
   - `services/orchestrator/src/routes/workflow/stages.ts`
   - `packages/ai-router/src/model-router.service.ts`
   - `packages/ai-router/src/dispatchers/custom-agent-dispatcher.ts`
   - `docker-compose.yml`

2. Summarize:
   - What currently calls WORKER_URL
   - What stage routes exist
   - Compose orchestrator service name

### Checkpoint
**STOP** and ask for confirmation to begin edits.

---

## MILESTONE 1 — Sync-only Stage 2 Direct Specialist Execution

### STEP 1 (ADD): Create AgentClient (Sync Only)

**File**: `services/orchestrator/src/clients/agentClient.ts`

**Requirements**:
1. **getAgentClient() singleton**
   - Thread-safe and reusable
   - Initialize once and return cached instance

2. **postSync(agentBaseUrl, path, body, opts)** method returning:
   ```typescript
   {
     ok: boolean,
     status: number,
     data?: any,
     error?: string,
     duration_ms: number
   }
   ```

3. **Circuit breaker** behavior:
   - Similar to `workerClient.ts`
   - Track failure rates
   - Implement trip/reset logic
   - Configurable thresholds

4. **Enforce timeouts**:
   - Default timeout: 30 seconds (configurable)
   - Graceful timeout handling
   - No hanging requests

5. **PHI-safe logging** - CRITICAL:
   - NEVER log request bodies (may contain PHI)
   - NEVER log response bodies (may contain PHI)
   - Log only: URL paths, status codes, duration, error types

6. **TypeScript requirements**:
   - Strict mode compliant
   - No 'any' types unless absolutely unavoidable
   - Full type definitions

7. **Include stub postStream()** that yields a warning (do not implement SSE yet)

**After Changes**:
- Provide tests/commands: TypeScript build for orchestrator workspace (tsc or equivalent)
- **STOP for checkpoint**

---

### STEP 2 (EDIT): Add Router Dispatch Endpoint

**File**: `services/orchestrator/src/routes/ai-router.ts`

**Add**: `POST /api/ai/router/dispatch`

**Behavior**:
1. Accepts JSON with:
   - `task_type`
   - `request_id`
   - passthrough fields

2. For Milestone 1, route only:
   - `task_type == "STAGE_2_LITERATURE_REVIEW"` → `agent_name: "agent-stage2-lit"`

3. Resolve `agent_url` from `AGENT_ENDPOINTS_JSON` env var

4. Return:
   ```json
   {
     "dispatch_type": "agent",
     "agent_name": "agent-stage2-lit",
     "agent_url": "http://agent-stage2-lit:8010",
     "budgets": {},
     "rag_plan": {},
     "request_id": "..."
   }
   ```

5. Validate errors properly

**After Changes**:
- **STOP for checkpoint** (tsc + basic curl example)

---

### STEP 3 (EDIT): Patch BullMQ Stage Worker (Stage 2 Only)

**File**: `services/orchestrator/src/services/workflow-stages/worker.ts`

**Requirements**:
1. **Keep legacy behavior** for all stages except stage==2

2. **For stage==2**:
   - Build TaskContract with:
     - `request_id`
     - `task_type="STAGE_2_LITERATURE_REVIEW"`
     - `workflow_id`, `user_id`, `mode`, `risk_tier`, `domain_id`
     - `inputs`, `budgets`
   
   - Call `POST ${ORCHESTRATOR_INTERNAL_URL}/api/ai/router/dispatch`
     - Default: `ORCHESTRATOR_INTERNAL_URL=http://orchestrator:3001`
   
   - Call `AgentClient.postSync(dispatchPlan.agent_url, "/agents/run/sync", task)`
   
   - Keep progress updates: 10/20/80/100 and event emits

3. **Use isMigratedStage(stage) guard** (stage==2 returns true)

**After Changes**:
- **STOP for checkpoint**

---

### STEP 4 (EDIT): Make Stage 2 Queued Job Payload Deterministic

**File**: `services/orchestrator/src/routes/workflow/stages.ts`

**Extend Stage2ExecuteSchema**:
- `mode` (DEMO|LIVE)
- `risk_tier` (PHI|SENSITIVE|NON_SENSITIVE)
- `domain_id`
- `inputs` (validate via Stage2InputsSchema)

**Create Stage2InputsSchema** with defaults:
```typescript
{
  query?: string;
  databases: ['pubmed', 'semantic_scholar']; // default ['pubmed']
  max_results: number; // 1..200, default 25
  year_range?: {
    from?: number;
    to?: number;
  };
  study_types?: enum[];
  mesh_terms?: string[];
  include_keywords?: string[];
  exclude_keywords?: string[];
  language: string; // default 'en'
  dedupe: boolean; // default true
  require_abstract: boolean; // default true
}
```

**Implementation**:
1. Parse `inputs = Stage2InputsSchema.parse(body.inputs ?? {})`
2. Queue job including `mode`, `risk_tier`, `domain_id`, `inputs`
3. Return routing + normalized inputs in response

**After Changes**:
- **STOP for checkpoint**

---

### STEP 5 (EDIT): Merge AI Services into docker-compose.yml

**File**: `docker-compose.yml`

**Add Services** (on backend network):

1. **chromadb**:
   - Persistent volume: `chromadb-data`
   - Token auth via `CHROMADB_AUTH_TOKEN`

2. **agent-stage2-lit**:
   - Build from `services/agents/agent-stage2-lit/Dockerfile`
   - depends_on: ollama + chromadb

**Add Volume**:
```yaml
volumes:
  chromadb-data:
```

**Add Orchestrator Env Vars**:
```yaml
INFERENCE_POLICY=local_only  # default
ORCHESTRATOR_INTERNAL_URL=http://orchestrator:3001
AGENT_ENDPOINTS_JSON=...  # includes agent-stage2-lit URL
VECTOR_BACKEND=chroma
CHROMADB_URL=http://chromadb:8000
CHROMADB_AUTH_TOKEN=...
```

**Important**: Do not remove vector-db or other services (legacy ok)

**After Changes**:
- **STOP for checkpoint** (`docker compose config`)

---

### STEP 6 (ADD): Scaffold agent-stage2-lit Microservice

**Create**: `services/agents/agent-stage2-lit/`

**Structure**:
```
agent-stage2-lit/
├── Dockerfile
├── requirements.txt
├── app.py  # FastAPI application
└── README.md
```

**Endpoints**:
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - SSE streaming (minimal stub for now)
- `GET /health` - Health check
- `GET /health/ready` - Readiness check

**Implementation Notes**:
1. Dockerfile copies `services/worker/agents` into image as `/app/worker_agents`
2. Import: `from worker_agents.analysis.lit_search_agent import LitSearchAgent`
3. `run_sync` uses `LitSearchAgent.search_pubmed(query, max_results)`
4. Normalize Paper objects
5. `run_stream` yields a few status events + final (minimal)

**Provide**: curl example to test `/agents/run/sync`

**After Changes**:
- **STOP for checkpoint** (docker build + curl /health)

---

### STEP 7 (EDIT): Implement Entrez PubMed in LitSearchAgent

**File**: `services/worker/agents/analysis/lit_search_agent.py`

**Task**: Replace async `search_pubmed()` with real Entrez implementation

**Requirements**:
1. Use Entrez ESearch + EFetch XML parsing
2. Use `NCBI_API_KEY` environment variable
3. Parse from XML:
   - title
   - abstract
   - authors
   - year
   - journal
   - doi
   - pmid
4. Return `Paper(source="pubmed", url=<pubmed_link>)`
5. Add minimal imports only

**After Changes**:
- **STOP for checkpoint** (agent-stage2-lit returns non-empty papers)

---

## MILESTONE 2 — SSE End-to-End for Stage 2

**Prerequisites**: Milestone 1 must pass all checkpoints

### STEP 8 (EDIT+ADD): Implement SSE Job Stream

**Tasks**:

1. **Add AgentClient.postStream()** SSE parser
   - Parse Server-Sent Events
   - Handle reconnection
   - Error handling

2. **Update stage worker** (stage==2):
   - Call agent `/agents/run/stream`
   - Store events in Redis keyed by `job_id`

3. **Add endpoint**: `GET /api/workflow/stages/:stage/jobs/:job_id/stream`
   - SSE endpoint
   - Replay events from Redis

4. **Keep polling endpoint intact** (backward compatibility)

**After Changes**:
- **STOP for checkpoint**

---

## MILESTONE 3 — Full Agent Fleet + Multi-Stage Routing

**Prerequisites**: Milestone 2 must pass all checkpoints

### Overview
Maximum decomposition - create specialist agents for all stages.

### Tasks

1. **Create services/agents/_template**
   - Base template for all agents
   - Standard structure, Dockerfile, FastAPI setup

2. **Clone Many Agents**:
   - agent-governance
   - agent-rag
   - agent-data-extraction
   - agent-stats-analysis
   - agent-visualization
   - agent-writing-synthesis
   - agent-verification
   - agent-export
   - (+ 17 more)

3. **Expand packages/ai-router Roster**:
   - Mapping: `task_types` → `agent_name`
   - Enforce PHI-safe routing
   - Policy enforcement

4. **Expand Migrated Stages List**:
   - Beyond stage 2
   - Update `isMigratedStage()` logic

**Execution Strategy**:
- **STOP after each batch of 3–5 agents**
- Ensure compose builds successfully
- Validate health endpoints

---

## MILESTONE 4 — CI + RAG Improvement Loops + Always Improving + Domain Packs

**Prerequisites**: Milestone 3 must pass all checkpoints

### CI/CD Workflows

1. **Add ai-evals.yml**:
   - Policy validation
   - Budget checks
   - Schema validation
   - RAG regression tests

2. **Add ai-improvement-pr.yml**:
   - Nightly tuning PRs
   - No auto-merge (require review)
   - Performance optimization suggestions

### Domain Packs

3. **Add domains/clinical**:
   - Clinical-specific assets
   - Medical ontologies
   - Specialized prompts

4. **Add domains/generic**:
   - Generic research assets
   - Cross-domain utilities

5. **Agents Load Assets by domain_id**:
   - Dynamic asset loading
   - Domain-specific behavior

### Code Refactoring

6. **Refactor Shared Agent Code**:
   - Create `services/agents/common/`
   - Shared utilities
   - Common interfaces
   - Reduce duplication

**Execution Strategy**:
- **STOP after each workflow addition**
- Validate CI runs
- Test domain switching

---

## Checkpoint Protocol

At the end of each step:

1. **Print**:
   - Files changed
   - Env vars added/changed
   - How to test
   - Next step

2. **STOP and ask**: "Proceed to next step? (yes/no)"

3. **Wait for user confirmation** before continuing

---

## Testing Commands Reference

### TypeScript Validation
```bash
cd services/orchestrator
npm run typecheck
npm test
```

### Docker Validation
```bash
docker compose config
docker compose build agent-stage2-lit
docker compose up -d agent-stage2-lit
docker compose logs -f agent-stage2-lit
```

### Health Checks
```bash
curl http://localhost:8010/health
curl http://localhost:8010/health/ready
```

### Agent Testing
```bash
curl -X POST http://localhost:8010/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-123",
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "inputs": {
      "query": "diabetes treatment",
      "max_results": 10
    }
  }'
```

---

## PHI Safety Checklist

Before each commit, verify:

- [ ] No request bodies logged
- [ ] No response bodies logged
- [ ] Error messages sanitized
- [ ] Only status codes, URLs, durations logged
- [ ] Circuit breaker patterns implemented
- [ ] Timeout enforcement in place
- [ ] INFERENCE_POLICY=local_only enforced for PHI data

---

## Rollback Procedures

### If Step Fails

1. **Identify failure point**
2. **Revert changes**:
   ```bash
   git checkout -- <file>
   ```
3. **Restore dependencies**:
   ```bash
   npm install
   ```
4. **Validate**:
   ```bash
   npm test
   docker compose config
   ```

### If Build Fails

1. **Check Docker logs**:
   ```bash
   docker compose logs <service>
   ```
2. **Rebuild from scratch**:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up
   ```

---

## Success Criteria

### Milestone 1 Complete When:
- ✅ AgentClient exists with sync support
- ✅ Router dispatch endpoint functional
- ✅ Stage 2 routes through agent
- ✅ Docker compose includes agent-stage2-lit
- ✅ Entrez PubMed returns real results
- ✅ All tests pass
- ✅ No PHI leaks in logs

### Milestone 2 Complete When:
- ✅ SSE streaming implemented
- ✅ Events stored in Redis
- ✅ Stream endpoint functional
- ✅ Backward compatible polling works

### Milestone 3 Complete When:
- ✅ 25+ agents deployed
- ✅ All agents have health endpoints
- ✅ Router maps all task types
- ✅ All stages migrated

### Milestone 4 Complete When:
- ✅ CI workflows operational
- ✅ Domain packs functional
- ✅ Common agent code refactored
- ✅ Improvement loops running

---

## End of Runbook

**Remember**: 
- Minimal diffs only
- PHI safety always
- Stop at checkpoints
- Test after each change
- No unrelated refactors

**START**: Begin with Phase 0 - Confirm current repo state
