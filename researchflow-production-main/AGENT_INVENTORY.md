# AGENT INVENTORY - ResearchFlow Production

**Generated:** 2025-02-06  
**Branch:** chore/inventory-capture  
**Milestone:** 03 - Agent Fleet Scaffold  

## Executive Summary

This inventory captures ALL agents, model integrations, prompt files, and LLM calls across the entire ResearchFlow codebase.

**Total Counts:**
- **Microservice Agents (Docker):** 14
- **Stage Agents (Workflow Engine):** 20
- **Specialized Agents (Worker):** 15+
- **LangGraph Agents:** 8
- **LangSmith Multi-Agent Systems:** 2 (Evidence Synthesis, Clinical Manuscript Writer)
- **Model Providers:** 6
- **Prompt Files:** 15+

---

## 1. MICROSERVICE AGENTS (Docker Compose)

These are standalone FastAPI services running in Docker containers with health checks and internal APIs.


### 1.1 Stage 2 Pipeline Agents

| Agent | Port | Status | Purpose | LLM Calls |
|-------|------|--------|---------|-----------|
| `agent-stage2-lit` | 8000 | ✅ Production | Literature search via PubMed/SemanticScholar | Via AI Bridge |
| `agent-stage2-screen` | 8000 | ✅ Production | Deduplication, inclusion/exclusion criteria | Via AI Bridge |
| `agent-stage2-extract` | 8000 | ✅ Production | PICO extraction from papers | Via AI Bridge |
| `agent-stage2-synthesize` | 8000 | 🚧 Stub | Synthesize evidence (not implemented) | Via AI Bridge |
| `agent-evidence-synthesis` | 8015 | ✅ Production | GRADE-based evidence synthesis with conflict analysis | Via AI Bridge |

**Location:** `services/agents/agent-stage2-*`, `agent-evidence-synthesis`  
**Integration:** All call orchestrator's AI Bridge for LLM inference  
**Environment:** `AGENT_ENDPOINTS_JSON` in orchestrator

**NEW:** `agent-evidence-synthesis` — Imported from LangSmith (2026-02-07)
- PICO-based question decomposition
- Systematic evidence retrieval (PubMed, Google Scholar, clinical registries)
- GRADE quality evaluation (High/Moderate/Low/Very Low)
- Conflict detection and multi-perspective analysis
- Structured synthesis reports with methodology notes
- Sub-workers: Evidence Retrieval Worker, Conflict Analysis Worker
- Source: LangSmith Agent e22b2945-be8b-4745-9233-5b2651914483


### 1.2 RAG Pipeline Agents

| Agent | Port | Status | Purpose | Dependencies |
|-------|------|--------|---------|--------------|
| `agent-rag-ingest` | 8000 | ✅ Production | Chunk + embed documents → ChromaDB | ChromaDB, OpenAI embeddings |
| `agent-rag-retrieve` | 8000 | ✅ Production | Vector search → GroundingPack | ChromaDB |
| `agent-lit-retrieval` | 8000 | ✅ Production | Deterministic PubMed search | NCBI E-utilities |

**Location:** `services/agents/agent-rag-*`, `agent-lit-retrieval`  
**Vector DB:** ChromaDB (docker service)  
**Embeddings:** OpenAI text-embedding-3-small


### 1.3 Writing & Verification Agents

| Agent | Port | Status | Purpose | LLM Calls |
|-------|------|--------|---------|-----------|
| `agent-verify` | 8000 | ✅ Production | Claim verification vs evidence | Via AI Bridge |
| `agent-intro-writer` | 8000 | ✅ Production | Generate Introduction sections | Via AI Bridge |
| `agent-methods-writer` | 8000 | ✅ Production | Generate Methods sections | Via AI Bridge |
| `agent-results-writer` | 8000 | 🚧 Stub | Generate Results sections | Via AI Bridge |
| `agent-discussion-writer` | 8000 | 🚧 Stub | Generate Discussion sections | Via AI Bridge |

**Location:** `services/agents/agent-*-writer`, `agent-verify`  
**Shared Library:** `services/agents/shared/section_writer/`  
**Evidence System:** All writers attach `chunk_id` and `doc_id` references

**NEW:** `agent-clinical-manuscript` — Clinical Manuscript Writer (Imported from LangSmith, 2026-02-07)
- **Purpose:** Full IMRaD format manuscript generation with multi-guideline compliance (CONSORT, SPIRIT, STROBE, PRISMA)
- **Architecture:** LangSmith multi-agent system with 4 specialized sub-agents
- **Main Agent Capabilities:**
  - IMRaD section drafting (Introduction, Methods, Results, Discussion)
  - Automated audit loop (Statistical + Compliance review)
  - Evidence traceability system with Evidence IDs
  - PHI protection (mandatory pre-scan)
  - Google Docs/Sheets integration
  - Self-revision workflow
- **Sub-Agents:**
  - `Literature_Research_Agent`: Medical literature search via Tavily/Exa (PubMed, ClinicalTrials.gov, Cochrane)
  - `Statistical_Review_Agent`: Statistical accuracy validation (test appropriateness, text-table concordance)
  - `CONSORT_SPIRIT_Compliance_Agent`: Systematic guideline evaluation (25+ checklists)
  - `Data_Extraction_Agent`: Clinical data parsing, Table 1 generation, PHI screening
- **Tools:** Google Docs, Google Sheets, Tavily Search, Exa Search, Gmail
- **Integration:** Receives structured evidence from `agent-evidence-synthesis`; outputs publication-ready manuscripts
- **Evidence Ledger:** Maintains Google Sheets with Evidence Log, Data Quality, Compliance Audit
- **Deployment:** Currently LangSmith-hosted (containerization planned)
- **Source:** LangSmith Agent "Clinical Manuscript Writer" (see `services/agents/agent-clinical-manuscript/`)


### 1.4 Governance & Policy Agents

| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| `agent-policy-review` | 8000 | ✅ Production | Governance compliance checks |
| `agent-lit-triage` | 8000 | ✅ Production | AI-powered literature triage & prioritization |
| `agent-evidence-synth` | 8000 | 🚧 Stub | Evidence synthesis |

**Location:** `services/agents/agent-policy-review`, etc.  
**Environment:** `GOVERNANCE_MODE=LIVE` or `DEMO`

**NEW:** `agent-lit-triage` — AI-Powered Literature Triage (Imported from LangSmith, 2026-02-07)
- **Purpose:** Comprehensive medical literature discovery, ranking, and prioritization
- **Architecture:** Three-phase pipeline (SEARCH → RANK → PRIORITIZE)
- **Workers:**
  - `LiteratureSearchWorker`: Semantic search with query expansion (Exa API integration)
  - `LiteratureRankingWorker`: Multi-criteria scoring (recency, relevance, journal impact, author reputation, citations)
- **Scoring Model:**
  - Recency (20%): Publication date scoring (1-10)
  - Keyword Relevance (30%): Query match scoring
  - Journal Impact (20%): Venue reputation (NEJM, Lancet, JAMA = 10)
  - Author Reputation (15%): Institutional credentials
  - Citation Count (15%): Citation impact adjusted for recency
  - Composite Score: 0-100 scale
- **Tiering:**
  - Tier 1 (Must Read 🔴): Score ≥ 75
  - Tier 2 (Should Read 🟡): Score 50-74
  - Tier 3 (Optional 🟢): Score < 50
- **Output:** Structured markdown reports with executive summary and prioritized papers
- **API:** Supports both sync (`/agents/run/sync`) and streaming (`/agents/run/stream`) endpoints
- **LangSmith Source:** Literature_Triage_Agent configuration
- **Environment Variables:**
  - `EXA_API_KEY`: For semantic search (optional, mocks if not set)
  - `LANGCHAIN_API_KEY`: For LangSmith tracing
- **Legacy Mode:** Maintains backward compatibility with rule-based triage (`use_ai: false`)
- **Integration:** Feeds Stage 2 Literature Pipeline and Evidence Synthesis agents

---

## 2. WORKFLOW STAGE AGENTS (Worker Service)

These are Python classes registered in the workflow engine, each handling one of the 20 research workflow stages.

**Location:** `services/worker/src/workflow_engine/stages/stage_*.py`  
**Base Class:** `BaseStageAgent`  
**Registration:** `@register_stage` decorator


### 2.1 Complete Stage Agent List

| Stage | Agent Class | File | Status | LLM Usage |
|-------|-------------|------|--------|-----------|
| 1 | `DataPrepAgent` | `stage_01_dataprep.py` | ✅ | Via AI Router |
| 2 | `LiteratureScoutAgent` | `stage_02_literature.py` | ✅ | Via AI Router |
| 3 | `IRBDraftingAgent` | `stage_03_irb.py` | ✅ | Via AI Router |
| 4a | `HypothesisRefinerAgent` | `stage_04_hypothesis.py` | ✅ | Via AI Router |
| 4b | `DatasetValidationAgent` | `stage_04_validation.py` | ✅ | Pandera schemas |
| 5 | `PHIGuardAgent` | `stage_05_phi.py` | ✅ | PHI detection |
| 6 | `StudyDesignAgent` | `stage_06_study_design.py` | ✅ | Via AI Router |
| 7 | `StatisticalModelAgent` | `stage_07_stats.py` | ✅ | Via AI Router |
| 8 | `DataValidationAgent` | `stage_08_validation.py` | ✅ | Validation |
| 9 | `InterpretationAgent` | `stage_09_interpretation.py` | ✅ | Via AI Router |
| 10a | `ValidationAgent` | `stage_10_validation.py` | ✅ | Validation |
| 10b | `GapAnalysisStageAgent` | `stage_10_gap_analysis.py` | ✅ | Via AI Router |
| 11 | `IterationAgent` | `stage_11_iteration.py` | ✅ | Via AI Router |
| 12 | `ManuscriptDraftingAgent` | `stage_12_manuscript.py` | ✅ | Via Manuscript Engine |
| 13 | `InternalReviewAgent` | `stage_13_internal_review.py` | ✅ | Via AI Router |
| 14 | `EthicalReviewAgent` | `stage_14_ethical.py` | ✅ | Persona simulation |
| 15 | `FinalPolishAgent` | `stage_15_final_polish.py` | ✅ | Via AI Router |
| 16 | `CollaborationHandoffAgent` | `stage_16_handoff.py` | ✅ | Collaboration |
| 17 | `ArchivingAgent` | `stage_17_archiving.py` | ✅ | Archival |
| 18 | `ImpactAssessmentAgent` | `stage_18_impact.py` | ✅ | Via AI Router |
| 19 | `DisseminationAgent` | `stage_19_dissemination.py` | ✅ | Via AI Router |
| 20 | `ConferencePrepAgent` | `stage_20_conference.py` | ✅ | Via AI Router |

**Total:** 20 stage agents  
**Pattern:** All inherit from `BaseStageAgent` and implement `execute(context)` method


---

## 3. LANGGRAPH AGENTS (Advanced Agents)

These are sophisticated agents using LangGraph for stateful workflows, checkpointing, and human-in-the-loop.

**Framework:** LangGraph 0.2.60+  
**Base Class:** `LangGraphBaseAgent`  
**Location:** `services/worker/src/agents/` and `services/worker/agents/`

### 3.1 LangGraph Agent List

| Agent | Purpose | Nodes | Checkpointing | Status |
|-------|---------|-------|---------------|--------|
| `IRBAgent` | IRB submission (Stages 13-14) | 7 nodes | Redis | ✅ Production |
| `QualityAgent` | Quality review (Stages 10-12) | Multi-stage | Redis | ✅ Production |
| `DataPrepAgent` | Data preparation (Stages 1-5) | 5 nodes | Redis | ✅ Production |
| `SupplementaryMaterialAgent` | Supplementary content (Stage 16) | 11 criteria | Redis | ✅ Production |
| `ResultsInterpretationAgent` | Results interpretation | Multi-node | Redis | ✅ Production |
| `TableFigureLegendAgent` | Table/figure legends | 3 nodes | Redis | ✅ Production |
| `StatisticalAnalysisAgent` | Statistical analysis | PLAN→RETRIEVE→EXECUTE | Redis | ✅ Production |
| `GapAnalysisAgent` | Research gap analysis | Multi-node | Redis | ✅ Production |

**Integration:** All call orchestrator's AI Bridge (`/api/ai/bridge`)  
**Checkpointing:** Redis-backed state management  
**Human-in-the-Loop:** Supported via `human_loop/handler.py`


---

## 4. SPECIALIZED ANALYSIS AGENTS

These are domain-specific agents for literature analysis, statistical work, and visualization.

**Location:** `services/worker/agents/analysis/`

| Agent | File | Purpose | Dependencies |
|-------|------|---------|--------------|
| `LitSearchAgent` | `lit_search_agent.py` | Literature search orchestration | PubMed, SemanticScholar |
| `StatisticalAnalysisAgent` | `statistical_analysis_agent.py` | Statistical modeling | scipy, statsmodels |
| `DataVisualizationAgent` | `data_visualization_agent.py` | Generate charts/figures | matplotlib, seaborn |
| `GapAnalysisAgent` | `gap_analysis_agent.py` | Identify research gaps | LangGraph |
| `PRISMAAgent` | `prisma_agent.py` | PRISMA flow diagrams | literature data |
| `MetaAnalysisAgent` | `meta_analysis_agent.py` | Meta-analysis | statistical tools |

**Total:** 6+ specialized agents  
**Factory Pattern:** `create_*_agent()` functions


---

## 5. MODEL PROVIDERS & LLM INTEGRATIONS

### 5.1 Primary Model Providers

| Provider | Environment Variable | Models Available | Usage |
|----------|---------------------|------------------|-------|
| **OpenAI** | `OPENAI_API_KEY` | GPT-4, GPT-4-turbo, GPT-3.5-turbo | Production inference |
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude 3.5 Sonnet, Claude Opus | Production inference |
| **xAI** | `XAI_API_KEY` | Grok | Experimental |
| **Mercury** | `MERCURY_API_KEY` | Mercury Coder | Code generation |
| **Inception** | `INCEPTION_API_KEY` / `INCEPTIONLABS_API_KEY` | Custom models | Specialized tasks |
| **Ollama (Local)** | `OLLAMA_URL` | Qwen2.5-coder:7b | Local inference |

### 5.2 Model Routing (AI Router)

**Location:** `packages/ai-router/`  
**Endpoint:** `http://orchestrator:3001/api/ai/`  
**Features:**
- PHI scanning (via `packages/phi-engine/`)
- Prompt caching
- Rate limiting
- Cost tracking
- Fallback routing

**Key Routes:**
- `/api/ai/chat/completions` - Chat completions
- `/api/ai/bridge` - LangGraph agent bridge
- `/api/ai/agent-proxy` - Python agent proxy
- `/api/ai/extraction/generate` - Data extraction


---

## 6. PROMPT FILES & TEMPLATES

### 6.1 Manuscript Engine Prompts

**Location:** `packages/manuscript-engine/src/prompts/`

| File | Purpose | Model |
|------|---------|-------|
| `abstract-generator.prompt.ts` | Abstract generation | GPT-4 |
| `section-prompts/introduction.prompt.ts` | Introduction section | GPT-4 |
| `section-prompts/methods.prompt.ts` | Methods section | GPT-4 |
| `section-prompts/results.prompt.ts` | Results section | GPT-4 |
| `section-prompts/discussion.prompt.ts` | Discussion section | GPT-4 |
| `section-prompts/abstract.prompt.ts` | Abstract variants | GPT-4 |
| `gap-analysis.prompt.ts` | Gap analysis | GPT-4 |

### 6.2 Section Writer Prompts (Python)

**Location:** `services/agents/shared/section_writer/prompts.py`

Contains prompts for:
- Introduction writing
- Methods writing
- Evidence citation formatting
- Section validation

### 6.3 Chat Agent Prompts

**Location:** `services/orchestrator/src/services/chat-agent/prompts.ts`

System prompts for conversational AI agent in frontend chat interface.


---

## 7. ORCHESTRATOR INTEGRATIONS

### 7.1 Agent Client (TypeScript)

**Location:** `services/orchestrator/src/clients/agentClient.ts`  
**Purpose:** Sync/async HTTP client for calling microservice agents  
**Features:**
- Circuit breaker pattern
- Timeout enforcement (30s default)
- PHI-safe logging
- Request/response tracking

### 7.2 Worker Client (TypeScript)

**Location:** `services/orchestrator/src/clients/workerClient.ts`  
**Purpose:** HTTP client for calling Python worker service  
**Features:**
- Similar to agentClient
- Legacy WORKER_URL support
- Job dispatch

### 7.3 Agent Routing Configuration

**Environment Variable:** `AGENT_ENDPOINTS_JSON`  
**Format:** JSON object mapping agent names to internal URLs

```json
{
  "agent-stage2-lit": "http://agent-stage2-lit:8000",
  "agent-stage2-screen": "http://agent-stage2-screen:8000",
  "agent-stage2-extract": "http://agent-stage2-extract:8000",
  "agent-stage2-synthesize": "http://agent-stage2-synthesize:8000",
  "agent-lit-retrieval": "http://agent-lit-retrieval:8000",
  "agent-policy-review": "http://agent-policy-review:8000",
  "agent-rag-ingest": "http://agent-rag-ingest:8000",
  "agent-rag-retrieve": "http://agent-rag-retrieve:8000",
  "agent-verify": "http://agent-verify:8000",
  "agent-intro-writer": "http://agent-intro-writer:8000",
  "agent-methods-writer": "http://agent-methods-writer:8000"
}
```


---

## 8. EXTERNAL INTEGRATIONS

### 8.1 Literature & Research APIs

| Integration | Environment Variable | Purpose | Agents Using |
|-------------|---------------------|---------|--------------|
| **NCBI E-utilities** | `NCBI_API_KEY`, `NCBI_EMAIL` | PubMed search | agent-lit-retrieval, agent-stage2-lit |
| **Semantic Scholar** | `SEMANTIC_SCHOLAR_API_KEY` | Academic paper metadata | agent-stage2-lit |
| **NLM MeSH** | `NCBI_API_KEY` | Medical subject headings | Literature agents |

### 8.2 AI & ML Services

| Integration | Environment Variable | Purpose |
|-------------|---------------------|---------|
| **Composio** | `COMPOSIO_API_KEY` | Tool execution platform |
| **LangSmith** | `LANGSMITH_API_KEY` | LangChain tracing/debugging |
| **Sourcegraph** | `SOURCEGRAPH_API_KEY` | Code intelligence |

### 8.3 Collaboration Tools

| Integration | Environment Variable | Purpose |
|-------------|---------------------|---------|
| **Notion** | `NOTION_API_KEY` | Documentation sync |
| **Figma** | `FIGMA_API_KEY` | Design handoff |
| **Zoom** | `ZOOM_WEBHOOK_SECRET_TOKEN` | Meeting integration |

### 8.4 Monitoring & Analytics

| Integration | Environment Variable | Purpose |
|-------------|---------------------|---------|
| **Sentry** | `VITE_SENTRY_DSN` | Error tracking |
| **Stripe** | `STRIPE_WEBHOOK_SECRET` | Payment webhooks |


---

## 9. DEPENDENCIES & FRAMEWORKS

### 9.1 Python Dependencies (Worker)

**File:** `services/worker/requirements-langchain.txt`

Key frameworks:
- `langchain>=0.3.19` - LangChain core framework
- `langgraph>=0.2.60` - Stateful agent workflows
- `langchain-anthropic>=0.3.0` - Anthropic integration
- `langchain-openai>=0.2.14` - OpenAI integration
- `langchain-community>=0.3.19` - Community components
- `composio-langchain>=0.7.0` - Composio integration
- `chromadb>=0.4.22` - Vector database

### 9.2 TypeScript Dependencies (Orchestrator)

**File:** `services/orchestrator/package.json`

Key frameworks:
- `@langchain/core` - LangChain TypeScript core
- `@langchain/langgraph` - LangGraph TypeScript
- `@langchain/openai` - OpenAI integration
- `@langchain/anthropic` - Anthropic integration
- `@anthropic-ai/sdk` - Direct Anthropic SDK
- `openai` - Direct OpenAI SDK


---

## 10. AGENT ARCHITECTURE PATTERNS

### 10.1 Microservice Agent Pattern (FastAPI)

```
services/agents/agent-{name}/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py              # FastAPI app
│   └── routes/
│       ├── health.py        # /health, /health/ready
│       └── run.py           # /agents/run/sync, /agents/run/stream
└── agent/
    ├── schemas.py           # Pydantic models
    └── impl.py              # Agent implementation
```

**Contract:**
- POST `/agents/run/sync` - Synchronous execution
- POST `/agents/run/stream` - Streaming execution (SSE)
- GET `/health` - Liveness probe
- GET `/health/ready` - Readiness probe

### 10.2 Stage Agent Pattern (Workflow Engine)

```python
@register_stage
class MyStageAgent(BaseStageAgent):
    stage_id = 10
    stage_name = "My Stage"
    
    async def execute(self, context: StageContext) -> StageResult:
        # Implementation
        pass
```

**Registration:** Automatic via `@register_stage` decorator  
**Discovery:** `workflow_engine/stages/registry.py`

### 10.3 LangGraph Agent Pattern

```python
class MyAgent(LangGraphBaseAgent):
    def build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("plan", self.plan_node)
        graph.add_node("execute", self.execute_node)
        graph.add_edge("plan", "execute")
        return graph.compile(checkpointer=RedisCheckpointSaver())
    
    async def execute(self, inputs):
        return await self.graph.ainvoke(inputs)
```

**Features:**
- Redis checkpointing for resume/retry
- Human-in-the-loop support
- Structured state management

---

## 11. MODEL CALL PATTERNS

### 11.1 Python → Orchestrator AI Bridge

```python
# In worker agents
response = await llm_bridge.chat_completion(
    messages=[{"role": "user", "content": "..."}],
    model="gpt-4",
    temperature=0.7
)
```

**Endpoint:** `http://orchestrator:3001/api/ai/bridge`  
**PHI Scanning:** Automatic  
**Authentication:** `WORKER_SERVICE_TOKEN`

### 11.2 Direct Model Calls (TypeScript)

```typescript
// In orchestrator
import { ChatOpenAI } from '@langchain/openai';

const model = new ChatOpenAI({
  modelName: 'gpt-4',
  temperature: 0.7
});

const response = await model.invoke([
  { role: 'user', content: '...' }
]);
```

### 11.3 Microservice Agent → AI Bridge

```python
# In FastAPI agents
import httpx

response = await httpx.post(
    f"{AI_BRIDGE_URL}/api/ai/chat/completions",
    json={
        "messages": [...],
        "model": "gpt-4"
    },
    headers={"Authorization": f"Bearer {AI_BRIDGE_TOKEN}"}
)
```

---

## 12. HEALTH CHECK & MONITORING

### 12.1 Agent Health Endpoints

All microservice agents expose:
- `GET /health` - Returns `{"status": "ok", "service": "agent-name"}`
- `GET /health/ready` - Returns readiness with dependency checks

### 12.2 Health Check Script

**File:** `milestone3_healthcheck.sh`  
**Purpose:** Validate all agents are running and responding  
**Usage:**
```bash
./milestone3_healthcheck.sh
```

### 12.3 Docker Healthchecks

All agents in `docker-compose.yml` have:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

---

## 13. GAPS & NEXT STEPS

### 13.1 Stub Agents (Not Implemented)

- `agent-stage2-synthesize` - Evidence synthesis
- `agent-results-writer` - Results section writing
- `agent-discussion-writer` - Discussion section writing
- `agent-lit-triage` - Literature triage
- `agent-evidence-synth` - Evidence synthesis

### 13.2 Missing Integrations

- **GitHub Actions Integration** - Automated workflow triggers
- **Slack Integration** - Team notifications
- **Email Integration** - Automated reports

### 13.3 Enhancement Opportunities

- **Agent Performance Metrics** - Track execution times, success rates
- **Cost Tracking** - Per-agent LLM cost monitoring
- **A/B Testing** - Model comparison framework
- **Agent Versioning** - Track agent code versions

---

## APPENDIX A: Quick Reference

### Start All Agents
```bash
cd researchflow-production-main
docker compose up -d
```

### Check Agent Status
```bash
docker compose ps | grep agent-
```

### View Agent Logs
```bash
docker compose logs -f agent-stage2-lit
```

### Test Agent Health
```bash
curl http://localhost:3001/api/agent-health/agent-stage2-lit
```

### Run Health Check
```bash
./milestone3_healthcheck.sh
```

---

## APPENDIX B: Environment Variables Reference

**Critical Variables:**
- `OPENAI_API_KEY` - OpenAI models
- `ANTHROPIC_API_KEY` - Claude models
- `NCBI_API_KEY` - PubMed access
- `CHROMADB_AUTH_TOKEN` - Vector DB authentication
- `WORKER_SERVICE_TOKEN` - Inter-service authentication
- `AGENT_ENDPOINTS_JSON` - Agent routing configuration

**Optional Variables:**
- `GOVERNANCE_MODE` - LIVE or DEMO
- `LOCAL_MODEL_ENABLED` - Enable Ollama
- `PHI_SCAN_ENABLED` - PHI scanning toggle
- `COMPOSIO_API_KEY` - Composio integration
- `LANGSMITH_API_KEY` - LangChain tracing

---

**Document Version:** 1.0  
**Last Updated:** 2025-02-06  
**Maintained By:** ResearchFlow Platform Team

