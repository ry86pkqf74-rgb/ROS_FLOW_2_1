# AGENT BRIEFING: Evidence Synthesis Agent

**Agent ID:** `agent-evidence-synthesis`  
**Task Type:** `EVIDENCE_SYNTHESIS`  
**Source:** LangSmith Custom Agent (e22b2945-be8b-4745-9233-5b2651914483)  
**Status:** ✅ Operational (Core logic complete, workers stubbed)  
**Integration Date:** 2026-02-07

---

## 🎯 PURPOSE

The Evidence Synthesis Agent is a specialized biomedical and clinical research agent that performs systematic evidence synthesis using GRADE (Grading of Recommendations Assessment, Development and Evaluation) methodology. It retrieves evidence from academic and clinical sources, evaluates quality, identifies conflicts, and produces structured synthesis reports.

## 🏗️ ARCHITECTURE

### Main Agent
- **Endpoint:** `http://agent-evidence-synthesis:8000`
- **Sync:** `POST /agents/run/sync`
- **Stream:** `POST /agents/run/stream`
- **Implementation:** `agent/evidence_synthesis.py`

### Sub-Workers

#### 1. Evidence Retrieval Worker
- **File:** `workers/retrieval_worker.py`
- **Function:** Systematic search across PubMed, Google Scholar, clinical trial registries
- **Output:** Structured evidence chunks with metadata, study type, sample size
- **Status:** 🚧 Stub (needs LLM/search tool integration)

#### 2. Conflict Analysis Worker
- **File:** `workers/conflict_worker.py`
- **Function:** Analyze contradictory evidence with methodological assessment
- **Output:** Multi-perspective debate + neutral + interpretive conclusions
- **Status:** 🚧 Stub (needs LLM integration)

---

## 📋 WORKFLOW

### Step 1: Question Decomposition
- Parse research question into PICO components (Population, Intervention, Comparator, Outcome)
- Generate focused sub-questions for systematic retrieval
- Present decomposition for confirmation

### Step 2: Evidence Retrieval
- Dispatch `Evidence_Retrieval_Worker` once per sub-question
- Search academic sources (PubMed, Google Scholar)
- Search clinical sources (ClinicalTrials.gov, WHO, CDC, NICE)
- Extract full content from relevant URLs
- Consolidate evidence chunks

### Step 3: GRADE Quality Evaluation
Assign quality rating to each piece of evidence:

| Grade | Meaning |
|-------|---------|
| **High** | Further research very unlikely to change confidence |
| **Moderate** | Further research may have important impact |
| **Low** | Further research very likely to change estimate |
| **Very Low** | Any estimate is very uncertain |

**Factors Considered:**
- Study design (RCT > cohort > case-control > case series)
- Risk of bias
- Inconsistency across studies
- Indirectness
- Imprecision
- Publication bias

### Step 4: Conflict Detection
- Scan evidence for contradictory findings
- If conflicts detected, dispatch `Conflict_Analysis_Worker`
- Analyze methodological quality of each side
- Identify sources of heterogeneity
- Present multi-perspective debate

### Step 5: Synthesis & Report Generation
Generate structured report with:
- Executive summary
- Evidence table with GRADE ratings
- Synthesis by sub-question
- Conflict analysis (if applicable)
- Limitations and gaps
- Methodology note

---

## 📥 INPUT SCHEMA

```json
{
  "research_question": "string (required)",
  "inclusion_criteria": ["string", "..."],
  "exclusion_criteria": ["string", "..."],
  "pico": {
    "population": "string (optional)",
    "intervention": "string (optional)",
    "comparator": "string (optional)",
    "outcome": "string (optional)"
  },
  "sources": ["url1", "url2"],
  "max_papers": 30
}
```

**Example:**
```json
{
  "research_question": "What is the efficacy of metformin in treating type 2 diabetes?",
  "pico": {
    "population": "Adults with type 2 diabetes",
    "intervention": "Metformin",
    "comparator": "Placebo or other antidiabetic drugs",
    "outcome": "HbA1c reduction"
  },
  "max_papers": 50
}
```

---

## 📤 OUTPUT SCHEMA

```json
{
  "executive_summary": "3-5 sentence summary",
  "overall_certainty": "High | Moderate | Low | Very Low",
  "evidence_table": [
    {
      "source": "Citation with PMID/DOI",
      "study_type": "RCT | Systematic Review | Cohort | ...",
      "sample_size": "N participants",
      "population": "Description",
      "key_findings": "Main results",
      "limitations": "Noted limitations",
      "grade": "High | Moderate | Low | Very Low",
      "relevance": "High | Medium | Low",
      "url": "https://..."
    }
  ],
  "synthesis_by_subquestion": {
    "Q1": "Narrative synthesis for sub-question 1",
    "Q2": "Narrative synthesis for sub-question 2"
  },
  "conflicting_evidence": {
    "conflict_description": "Summary of conflict",
    "positions": [...],
    "methodological_assessment": {...},
    "heterogeneity_sources": [...],
    "neutral_presentation": "Neutral summary",
    "interpretive_conclusion": "⚠️ INTERPRETIVE: ...",
    "confidence_level": "Low to Moderate"
  },
  "limitations": ["Limitation 1", "Limitation 2"],
  "methodology_note": {
    "search_strategy": "PICO-based decomposition",
    "sources_searched": ["PubMed", "Google Scholar", "..."],
    "search_date": "2026-02-07",
    "studies_screened": 45,
    "studies_included": 30,
    "quality_assessment": "GRADE methodology"
  }
}
```

---

## 🔗 INTEGRATION POINTS

### Orchestrator Integration
The agent can be invoked from the orchestrator via AI Router:

```typescript
const dispatchResponse = await fetch(`${orchestratorUrl}/api/ai/router/dispatch`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${serviceToken}`,
  },
  body: JSON.stringify({
    task_type: 'EVIDENCE_SYNTHESIS',
    request_id: 'req-123',
    workflow_id: 'workflow-456',
    mode: 'DEMO',
    inputs: {
      research_question: 'Your research question',
      pico: { ... },
      max_papers: 30
    }
  })
});

const { agent_url } = await dispatchResponse.json();

const agentResponse = await fetch(`${agent_url}/agents/run/sync`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(taskContract)
});
```

### Workflow Stage Integration

#### Option 1: Stage 2 (Literature Review)
Replace or augment `agent-stage2-synthesize` with Evidence Synthesis Agent for comprehensive GRADE-based synthesis.

#### Option 2: Stage 9 (Synthesis)
Use as final synthesis step after validation, providing structured evidence report.

#### Option 3: Ad-hoc via API
Direct invocation for on-demand evidence synthesis queries.

---

## 🚀 DEPLOYMENT

### Docker Compose

Add to `docker-compose.yml`:

```yaml
agent-evidence-synthesis:
  build:
    context: services/agents/agent-evidence-synthesis
    dockerfile: Dockerfile
  container_name: agent-evidence-synthesis
  ports:
    - "8015:8000"
  environment:
    - AI_BRIDGE_URL=http://orchestrator:3001/api/ai/bridge/inference
    - TAVILY_API_KEY=${TAVILY_API_KEY}
    - GOOGLE_DOCS_API_KEY=${GOOGLE_DOCS_API_KEY}
  networks:
    - researchflow-net
  restart: unless-stopped
```

### Environment Variables

Add to `.env`:

```bash
# Evidence Synthesis Agent
TAVILY_API_KEY=tvly-...  # For web search
GOOGLE_DOCS_API_KEY=...  # Optional, for report delivery
```

### Agent Endpoints Registry

Update orchestrator `.env` to include:

```json
{
  "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000"
}
```

---

## 🧪 TESTING

### Health Check
```bash
curl http://localhost:8015/health
# Expected: {"status":"ok"}
```

### Sync Execution Test
```bash
curl -X POST http://localhost:8015/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "EVIDENCE_SYNTHESIS",
    "request_id": "test-123",
    "mode": "DEMO",
    "inputs": {
      "research_question": "Is exercise beneficial for depression?",
      "pico": {
        "population": "Adults with major depressive disorder",
        "intervention": "Exercise (aerobic or resistance)",
        "comparator": "Standard care or no exercise",
        "outcome": "Depressive symptom reduction"
      },
      "max_papers": 20
    }
  }'
```

### Stream Execution Test
```bash
curl -X POST http://localhost:8015/agents/run/stream \
  -H "Content-Type: application/json" \
  -d '{ ... }' \
  --no-buffer
```

---

## 📊 CURRENT STATUS

### ✅ Complete
- [x] Core agent logic with GRADE methodology
- [x] PICO-based question decomposition
- [x] Evidence quality grading algorithm
- [x] Conflict detection heuristics
- [x] Structured report generation
- [x] FastAPI service endpoints (sync + stream)
- [x] Docker containerization
- [x] AI Router registration

### 🚧 In Progress (Stubbed)
- [ ] Evidence Retrieval Worker (needs Tavily/web search integration)
- [ ] Conflict Analysis Worker (needs LLM integration)
- [ ] Full URL content extraction (needs read_url_content tool)
- [ ] Google Docs report delivery (optional)

### 🎯 Next Steps
1. Integrate Tavily API for web search in retrieval worker
2. Connect AI Bridge for LLM calls in conflict analysis
3. Add integration tests with real PubMed queries
4. Wire into Stage 2 or Stage 9 workflow
5. Add governance mode logic (DEMO vs LIVE)

---

## 🔐 SECURITY & COMPLIANCE

- **PHI Handling:** No PHI in research questions (aggregate data only)
- **API Keys:** Store in environment variables, never commit
- **Rate Limiting:** Implement for external API calls (PubMed, Tavily)
- **Citation Integrity:** Never fabricate citations, always verify URLs
- **Transparency:** Always disclose evidence limitations and uncertainties

---

## 📚 REFERENCES

- **GRADE Handbook:** https://gdt.gradepro.org/app/handbook/handbook.html
- **LangSmith Agent:** https://smith.langchain.com/o/.../agents/editor?agentId=e22b2945-be8b-4745-9233-5b2651914483
- **ResearchFlow Agent Pattern:** `services/agents/_template/`
- **Stage 2 Pipeline Contract:** `services/agents/STAGE2_PIPELINE_CONTRACT.md`

---

## 🤝 MAINTAINERS

- **Primary:** ResearchFlow Agent Fleet Team
- **Contact:** See [AGENT_INVENTORY.md](../../AGENT_INVENTORY.md)
