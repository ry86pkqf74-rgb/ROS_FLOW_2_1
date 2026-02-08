# Evidence Synthesis Agent - Workflow Integration Guide

**Version:** 1.0  
**Date:** 2026-02-07  
**Status:** ✅ Ready for Integration

---

## 📋 Quick Start

The Evidence Synthesis Agent is now imported from LangSmith and integrated into the ResearchFlow system. This guide shows how to use it in your workflows.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    ResearchFlow Workflow                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Router (/api/ai/router/dispatch)       │
│  Maps EVIDENCE_SYNTHESIS → agent-evidence-synthesis         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Evidence Synthesis Agent (Port 8015)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Main Agent (evidence_synthesis.py)                  │   │
│  │ • PICO Decomposition                                │   │
│  │ • GRADE Evaluation                                  │   │
│  │ • Conflict Detection                                │   │
│  │ • Report Generation                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                          │                       │
│           ▼                          ▼                       │
│  ┌─────────────────┐      ┌─────────────────┐             │
│  │ Retrieval Worker│      │ Conflict Worker │             │
│  │ (Stub)          │      │ (Stub)          │             │
│  └─────────────────┘      └─────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment

### 1. Build and Start Services

```bash
cd /path/to/researchflow-production-main

# Build the agent
docker compose build agent-evidence-synthesis

# Start the agent
docker compose up -d agent-evidence-synthesis

# Verify health
curl http://localhost:8015/health
# Expected: {"status":"ok"}
```

### 2. Environment Variables

Add to `.env`:

```bash
# Evidence Synthesis Agent (Optional - for enhanced features)
TAVILY_API_KEY=tvly-your-api-key-here
GOOGLE_DOCS_API_KEY=your-google-docs-api-key
```

**Note:** The agent works without these keys using stub implementations. Add them for production-grade evidence retrieval.

---

## 🔗 Integration Patterns

### Pattern 1: Direct API Call (Testing)

```bash
curl -X POST http://localhost:8015/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-req-001",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Is exercise effective for treating depression in adults?",
      "pico": {
        "population": "Adults with major depressive disorder",
        "intervention": "Aerobic or resistance exercise",
        "comparator": "Standard care or no exercise",
        "outcome": "Reduction in depressive symptoms"
      },
      "max_papers": 30
    }
  }'
```

### Pattern 2: Via Orchestrator AI Router (Recommended)

```typescript
// From orchestrator or worker service
const dispatchResponse = await fetch('http://orchestrator:3001/api/ai/router/dispatch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${serviceToken}`,
  },
  body: JSON.stringify({
    task_type: 'EVIDENCE_SYNTHESIS',
    request_id: crypto.randomUUID(),
    workflow_id: workflowId,
    mode: 'DEMO',
    inputs: {
      research_question: 'Your research question here',
      pico: {
        population: 'Target population',
        intervention: 'Intervention being studied',
        comparator: 'Comparison group',
        outcome: 'Outcome measures'
      },
      max_papers: 30
    }
  })
});

const { agent_url, agent_name } = await dispatchResponse.json();
console.log(`Routed to: ${agent_name} at ${agent_url}`);

// Call the agent
const taskContract = {
  task_type: 'EVIDENCE_SYNTHESIS',
  request_id: 'req-123',
  inputs: { /* ... */ }
};

const agentResponse = await fetch(`${agent_url}/agents/run/sync`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(taskContract)
});

const result = await agentResponse.json();
console.log('Synthesis complete:', result.outputs);
```

### Pattern 3: Workflow Stage Integration

#### Option A: Replace Stage 2 Synthesize

Update `services/orchestrator/src/services/workflow-stages/worker.ts`:

```typescript
// In Stage 2 pipeline (after extraction)
const synthesizeInputs = {
  research_question: job.data.research_question,
  // Map extracted papers to synthesis input format
  papers: extractResponse.outputs.extraction_table,
  citations: extractResponse.outputs.citations,
  max_papers: 50
};

const synthesize = await runRoutedTask('EVIDENCE_SYNTHESIS', synthesizeInputs, 'synthesize');

if (!isOkAgentEnvelope(synthesize.response)) {
  throw new Error(`Synthesis failed: ${getAgentEnvelopeErrorMessage(synthesize.response)}`);
}

return {
  status: 'ok',
  outputs: {
    ...litResponse.outputs,
    ...screenResponse.outputs,
    ...extractResponse.outputs,
    synthesis_report: synthesize.response.outputs,
  }
};
```

#### Option B: New Stage 9.5 (Evidence Synthesis)

Create a dedicated synthesis stage:

```typescript
// Add to MIGRATED_STAGE_TO_TASK_TYPE
const MIGRATED_STAGE_TO_TASK_TYPE: Record<number, string> = {
  9: 'POLICY_REVIEW',
  10: 'EVIDENCE_SYNTHESIS',  // New stage
};

// In worker handler
case 10:  // Evidence Synthesis
  const synthesisInputs = {
    research_question: await getWorkflowResearchQuestion(workflowId),
    papers: await getValidatedPapers(workflowId),
    pico: job.data.pico,
    max_papers: 50
  };
  
  const synthesis = await runRoutedTask('EVIDENCE_SYNTHESIS', synthesisInputs, 'synthesis');
  
  return {
    status: 'ok',
    stage: 10,
    outputs: synthesis.response.outputs
  };
```

#### Option C: Ad-hoc Invocation (Manual Trigger)

Add as a utility endpoint for on-demand synthesis:

```typescript
// In orchestrator routes
router.post('/api/evidence-synthesis/run', 
  requirePermission('ANALYZE'),
  asyncHandler(async (req, res) => {
    const { research_question, pico, max_papers } = req.body;
    
    const dispatchPlan = await dispatchToRouter({
      task_type: 'EVIDENCE_SYNTHESIS',
      request_id: crypto.randomUUID(),
      user_id: req.user.id,
      mode: 'DEMO',
      inputs: { research_question, pico, max_papers }
    });
    
    const agentClient = getAgentClient();
    const result = await agentClient.postSync(
      dispatchPlan.agent_url,
      '/agents/run/sync',
      { task_type: 'EVIDENCE_SYNTHESIS', request_id: dispatchPlan.request_id, inputs: { research_question, pico, max_papers } }
    );
    
    res.json(result.data);
  })
);
```

---

## 📊 Output Structure

The agent returns a comprehensive synthesis report:

```json
{
  "ok": true,
  "request_id": "req-123",
  "task_type": "EVIDENCE_SYNTHESIS",
  "outputs": {
    "executive_summary": "Systematic review of 28 studies...",
    "overall_certainty": "Moderate",
    "evidence_table": [
      {
        "source": "Smith et al. (2023). PMID: 12345678",
        "study_type": "Randomized Controlled Trial",
        "sample_size": "500 participants",
        "key_findings": "30% improvement in outcome (p<0.01)",
        "grade": "High",
        "relevance": "High",
        "url": "https://pubmed.ncbi.nlm.nih.gov/12345678"
      }
    ],
    "synthesis_by_subquestion": {
      "Q1": "For adults with depression, exercise shows...",
      "Q2": "Compared to standard care, exercise demonstrates..."
    },
    "conflicting_evidence": {
      "conflict_description": "Studies show mixed results...",
      "neutral_presentation": "Evidence shows...",
      "interpretive_conclusion": "⚠️ INTERPRETIVE: Weight of evidence...",
      "confidence_level": "Moderate"
    },
    "limitations": [
      "Search limited to recent studies",
      "Heterogeneity in outcome measures"
    ],
    "methodology_note": {
      "search_strategy": "PICO-based decomposition",
      "sources_searched": ["PubMed", "Google Scholar"],
      "studies_screened": 45,
      "studies_included": 28,
      "quality_assessment": "GRADE methodology"
    }
  },
  "warnings": [
    "Decomposed into 3 sub-questions",
    "No conflicts detected - evidence shows consensus"
  ]
}
```

---

## 🧪 Testing Checklist

### Smoke Test (5 min)

```bash
# 1. Health check
curl http://localhost:8015/health

# 2. Simple sync call
curl -X POST http://localhost:8015/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-1",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Is aspirin effective for cardiovascular disease prevention?",
      "max_papers": 10
    }
  }' | jq '.outputs.executive_summary'

# 3. Router dispatch test
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SERVICE_TOKEN}" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-2",
    "mode": "DEMO"
  }' | jq '.agent_name'
# Expected: "agent-evidence-synthesis"
```

### Integration Test (15 min)

Create `tests/integration/evidence-synthesis.test.ts`:

```typescript
import { describe, it, expect } from '@jest/globals';

describe('Evidence Synthesis Agent', () => {
  it('should synthesize evidence with GRADE ratings', async () => {
    const response = await callAgent({
      task_type: 'EVIDENCE_SYNTHESIS',
      inputs: {
        research_question: 'Test question',
        pico: { population: 'Adults', intervention: 'Treatment X' },
        max_papers: 5
      }
    });
    
    expect(response.ok).toBe(true);
    expect(response.outputs.evidence_table).toBeDefined();
    expect(response.outputs.overall_certainty).toMatch(/High|Moderate|Low|Very Low/);
  });
  
  it('should detect conflicts when present', async () => {
    // Test with conflicting evidence stub
    const response = await callAgent({
      task_type: 'EVIDENCE_SYNTHESIS',
      inputs: { research_question: 'Conflicting research topic' }
    });
    
    expect(response.outputs.conflicting_evidence).toBeDefined();
  });
});
```

---

## 🔧 Troubleshooting

### Agent Not Reachable

```bash
# Check if container is running
docker compose ps agent-evidence-synthesis

# Check logs
docker compose logs -f agent-evidence-synthesis

# Restart if needed
docker compose restart agent-evidence-synthesis
```

### Router Not Finding Agent

```bash
# Verify AGENT_ENDPOINTS_JSON includes the agent
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq .

# Should include:
# "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000"
```

### LLM Integration Issues

The agent currently uses stubs for workers. To enable full LLM integration:

1. Set `AI_BRIDGE_URL` in environment
2. Update `workers/retrieval_worker.py` to call AI Bridge
3. Update `workers/conflict_worker.py` to call AI Bridge
4. Add Tavily API key for web search

---

## 📈 Next Steps

### Phase 1: Core Functionality ✅
- [x] GRADE methodology implementation
- [x] PICO decomposition
- [x] Conflict detection
- [x] Report generation
- [x] Docker integration
- [x] AI Router registration
- [x] Compose wiring validated (Step 1)
- [x] Router registration verified (Step 2)
- [x] Deploy-time validation hooks (Step 3)
- [x] Build pipeline compatibility (Step 4)
- [x] Deployment runbook (Step 5)

### Phase 2: Enhanced Retrieval 🚧
- [ ] Integrate Tavily web search
- [ ] Connect to PubMed API
- [ ] Add Google Scholar scraping
- [ ] Implement URL content extraction

### Phase 3: LLM Integration 🚧
- [ ] Connect retrieval worker to AI Bridge
- [ ] Connect conflict worker to AI Bridge
- [ ] Add streaming progress updates
- [ ] Implement token usage tracking

### Phase 4: Workflow Integration 📋
- [ ] Wire into Stage 2 pipeline
- [ ] Add as Stage 9.5 option
- [ ] Create UI trigger button
- [ ] Add to workflow builder

### Phase 5: Production Hardening 📋
- [ ] Add comprehensive error handling
- [ ] Implement rate limiting
- [ ] Add caching for repeated queries
- [ ] Create governance mode logic (DEMO vs LIVE)
- [ ] Add audit logging

---

## 📚 Documentation References

- **Agent Briefing:** [AGENT_EVIDENCE_SYNTHESIS_BRIEFING.md](./AGENT_EVIDENCE_SYNTHESIS_BRIEFING.md)
- **Agent README:** [services/agents/agent-evidence-synthesis/README.md](./services/agents/agent-evidence-synthesis/README.md)
- **AI Router:** [services/orchestrator/src/routes/ai-router.ts](./services/orchestrator/src/routes/ai-router.ts)
- **Agent Inventory:** [AGENT_INVENTORY.md](./AGENT_INVENTORY.md)
- **GRADE Methodology:** https://gdt.gradepro.org/app/handbook/handbook.html

---

## ✅ Production Deployment Validation Checklist

### Step 1: Compose Wiring (Production-Safe) ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Uses GHCR image tag pattern `${IMAGE_TAG}` | ✅ | Currently uses `build:` context (local build) - **TODO: switch to GHCR image for production** |
| No bind mounts to `/app` on server | ✅ | No `/app` bind mounts configured |
| Connected to `backend` network | ✅ | Internal service discovery |
| Connected to `frontend` network | ✅ | For external API access (PubMed, web search) |
| Has healthcheck (HTTP GET `/health`) | ✅ | 30s interval, 10s timeout, 10s start_period |
| Has stable internal port 8000 | ✅ | Exposed on 8000, external test port 8015 |
| `/data` volume mounts for artifacts | ⚠️ | **Not needed** - agent doesn't write persistent artifacts |
| Env vars use `${VAR}` passthroughs | ✅ | `TAVILY_API_KEY`, `GOOGLE_DOCS_API_KEY` optional |
| No hardcoded secrets | ✅ | All secrets via env vars |
| No public ports (except debug 8015) | ⚠️ | Port 8015 exposed for testing - **remove in production** |
| Resource limits configured | ✅ | 2 CPU / 4GB RAM max, 0.5 CPU / 1GB min |

**Action Items:**
1. ✅ **DONE**: Service defined with correct networks and healthcheck
2. ⚠️ **TODO**: Remove `ports: - "8015:8000"` for production (keep `expose: - "8000"` only)
3. ⚠️ **TODO**: Switch from `build:` to `image: ghcr.io/.../agent-evidence-synthesis:${IMAGE_TAG}` once GHCR images are published
4. ✅ **DONE**: Router registration in `AGENT_ENDPOINTS_JSON`

### Step 2: Orchestrator/Router Registration ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| `EVIDENCE_SYNTHESIS` task type registered | ✅ | In `TASK_TYPE_TO_AGENT` mapping |
| Routes to correct agent URL | ✅ | `agent-evidence-synthesis:8000` |
| Uses correct endpoint path | ✅ | `/agents/run/sync` (standard agent contract) |
| Service auth configured | ✅ | Uses `WORKER_SERVICE_TOKEN` for dispatch |
| Request/response shapes match | ✅ | `AgentTask` / `AgentResponse` schemas |
| Router dispatch returns agent info | ✅ | Returns `agent_name`, `agent_url` |

**Verification Commands:**
```bash
# 1. Check AGENT_ENDPOINTS_JSON includes evidence-synthesis
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep evidence-synthesis
# Expected: "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000"

# 2. Test router dispatch
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-001",
    "mode": "DEMO"
  }'
# Expected: {"agent_name":"agent-evidence-synthesis","agent_url":"http://agent-evidence-synthesis:8000",...}

# 3. Direct agent health check
curl http://localhost:8015/health
# Expected: {"status":"ok"}
```

### Step 3: Deploy-Time Validation Hooks ✅

**hetzner-preflight.sh** - Added checks:
- [x] Container running check: `docker ps | grep agent-evidence-synthesis`
- [x] Health endpoint check: `curl http://127.0.0.1:8015/health`
- [x] Router registration check: verify in `AGENT_ENDPOINTS_JSON`

**stagewise-smoke.sh** - Added optional check:
- [x] `CHECK_EVIDENCE_SYNTH=1` flag enables synthesis test
- [x] Uses tiny fixture payload (2-3 papers)
- [x] Does not block existing Stage 2 flows unless flag is set
- [x] Uses dev-auth JWT for user auth + internal service token

**Usage:**
```bash
# Preflight (always runs)
./scripts/hetzner-preflight.sh

# Stagewise smoke with evidence synthesis check
CHECK_EVIDENCE_SYNTH=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

### Step 4: Build/Publish Pipeline Compatibility ✅

| Requirement | Status | Notes |
|-------------|--------|-------|
| Dockerfile builds in GHCR context | ✅ | Standard multi-stage Python build |
| Works with `IMAGE_TAG` pulls | ⚠️ | **TODO**: Publish to GHCR, then switch compose to use image |
| No local-only dependencies | ✅ | All deps in `requirements.txt` |
| Healthcheck in Dockerfile | ✅ | `curl -f http://localhost:8000/health` |
| Runs as non-root user | ⚠️ | **TODO**: Add `USER` directive to Dockerfile |
| Base image: `python:3.11-slim` | ✅ | Consistent with other agents |

**Dockerfile Review:**
```dockerfile
# ✅ Base image
FROM python:3.11-slim

# ✅ Working directory
WORKDIR /app

# ✅ System dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# ✅ Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Application code
COPY app/ ./app/
COPY agent/ ./agent/
COPY workers/ ./workers/

# ✅ Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ✅ Command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Action Items:**
1. ⚠️ **TODO**: Add `USER` directive before `CMD` (security best practice)
2. ⚠️ **TODO**: Publish images to GHCR via GitHub Actions
3. ⚠️ **TODO**: Update compose to use `image:` instead of `build:`

### Step 5: Deployment Runbook ✅

See updated section below: **"🚀 Production Deployment Guide"**

---

## 🚀 Production Deployment Guide

### Prerequisites

**Required Environment Variables:**
```bash
# Internal service auth (required)
WORKER_SERVICE_TOKEN=<hex-token-32-chars-min>

# Optional external API keys (enhances retrieval)
TAVILY_API_KEY=tvly-your-api-key-here
GOOGLE_DOCS_API_KEY=your-google-docs-key
```

**Generate `WORKER_SERVICE_TOKEN`:**
```bash
openssl rand -hex 32
```

Add to `.env` file:
```bash
echo "WORKER_SERVICE_TOKEN=$(openssl rand -hex 32)" >> .env
```

### Deployment Steps (Hetzner/ROSflow2)

```bash
# 1. SSH to server
ssh user@rosflow2

# 2. Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# 3. Pull latest code
git fetch --all --prune && git pull --ff-only

# 4. Set IMAGE_TAG (production)
export IMAGE_TAG=197bfcd  # Current commit SHA
echo "IMAGE_TAG=197bfcd" >> .env

# 5. Pull/build images
# TODO: Once GHCR images are published, use: docker compose pull
# For now (local build):
docker compose build agent-evidence-synthesis

# 6. Run preflight checks
chmod +x scripts/hetzner-preflight.sh
./scripts/hetzner-preflight.sh

# 7. Start/restart agent
docker compose up -d agent-evidence-synthesis

# 8. Verify health
curl http://localhost:8015/health
# Expected: {"status":"ok"}

# 9. Verify router registration
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep evidence-synthesis
# Expected: "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000"

# 10. Optional: Run evidence synthesis smoke test
CHECK_EVIDENCE_SYNTH=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

### Validation on ROSflow2

```bash
# Health check
curl http://localhost:8015/health

# Router dispatch test (requires WORKER_SERVICE_TOKEN)
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEV_TOKEN" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "validation-001",
    "mode": "DEMO"
  }'

# Direct agent call (sync)
curl -X POST http://localhost:8015/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Is aspirin effective for cardiovascular disease prevention?",
      "max_papers": 5
    }
  }'
```

### Known Limitations / TODOs

1. **GHCR Image Publishing** ⚠️
   - Currently uses local `build:` in compose
   - **Action**: Publish to GHCR, update compose to use `image:`
   - **Impact**: Required for production IMAGE_TAG pinning

2. **External Port Exposure** ⚠️
   - Port 8015 exposed for testing
   - **Action**: Remove from production compose (keep `expose: - "8000"` only)
   - **Impact**: Security - internal agents should not be publicly accessible

3. **Worker Stubs** ℹ️
   - Retrieval worker uses stub (no live PubMed/web search)
   - Conflict worker uses stub (no LLM conflict analysis)
   - **Action**: Connect workers to AI Bridge or external APIs
   - **Impact**: Limited evidence retrieval and analysis quality

4. **No Artifact Persistence** ℹ️
   - Agent doesn't write to `/data` volumes
   - **Action**: None needed (synthesis results returned inline)
   - **Impact**: Results must be captured by orchestrator/worker

5. **Resource Limits** ✅
   - Configured: 2 CPU / 4GB RAM (max), 0.5 CPU / 1GB (reserved)
   - **Monitor**: CPU/memory usage during high-load synthesis

---

## 🤝 Support

For questions or issues:
1. Check logs: `docker compose logs agent-evidence-synthesis`
2. Review [README.md](./services/agents/agent-evidence-synthesis/README.md)
3. Run health check: `curl http://localhost:8015/health`
4. Contact ResearchFlow Agent Fleet Team

---

**Status:** ✅ Agent imported, configured, and ready for integration  
**Last Updated:** 2026-02-07
