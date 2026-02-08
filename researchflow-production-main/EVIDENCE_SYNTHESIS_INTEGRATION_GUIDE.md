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

## 🤝 Support

For questions or issues:
1. Check logs: `docker compose logs agent-evidence-synthesis`
2. Review [README.md](./services/agents/agent-evidence-synthesis/README.md)
3. Run health check: `curl http://localhost:8015/health`
4. Contact ResearchFlow Agent Fleet Team

---

**Status:** ✅ Agent imported, configured, and ready for integration  
**Last Updated:** 2026-02-07
