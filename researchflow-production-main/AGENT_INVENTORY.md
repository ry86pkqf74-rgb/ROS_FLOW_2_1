# AGENT INVENTORY - ResearchFlow Production

**Generated:** 2025-02-06  
**Branch:** chore/inventory-capture  
**Milestone:** 03 - Agent Fleet Scaffold  

## Executive Summary

This inventory captures ALL agents, model integrations, prompt files, and LLM calls across the entire ResearchFlow codebase.

**Total Counts:**
- **Microservice Agents (Docker):** 21 (15 native + 6 LangSmith proxies)
- **Stage Agents (Workflow Engine):** 20
- **Specialized Agents (Worker):** 15+
- **LangGraph Agents:** 8
- **LangSmith Multi-Agent Systems:** 8 (Evidence Synthesis, Clinical Manuscript Writer, Literature Triage, Clinical Study Section Drafter, Results Interpretation, Peer Review Simulator, Clinical Bias Detection, Dissemination Formatter)
- **LangSmith Proxy Services:** 5 (Results Interpretation, Clinical Manuscript Writer, Clinical Section Drafter, Peer Review Simulator, Clinical Bias Detection)
- **Model Providers:** 6
- **Prompt Files:** 15+

---

## 1. MICROSERVICE AGENTS (Docker Compose)

These are standalone FastAPI services running in Docker containers with health checks and internal APIs.

**Architecture Patterns:**
- **Native Agents:** FastAPI + worker implementation (local execution)
- **Proxy Agents:** FastAPI adapter → LangSmith cloud API (remote execution)

All agents expose the same contract: `/health`, `/health/ready`, `/agents/run/sync`, `/agents/run/stream`


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

**NEW:** `Clinical_Study_Section_Drafter` — Clinical Results & Discussion Section Writer (Imported from LangSmith, 2026-02-07)
- **Purpose:** Specialized drafting of Results and Discussion sections for clinical studies with reporting guideline compliance
- **Architecture:** LangSmith multi-agent system with 2 specialized sub-workers
- **Main Agent Capabilities:**
  - Results section drafting (participant flow, outcomes, subgroup analyses, adverse events)
  - Discussion section drafting (key findings, interpretation, comparison with literature, limitations, implications)
  - Automatic guideline adaptation (CONSORT, STROBE, STARD, PRISMA, CARE)
  - Few-shot style matching from example passages
  - Statistical accuracy (never fabricates data)
  - Evidence-based writing with citation management
- **Sub-Workers:**
  - `Clinical_Evidence_Researcher`: Web-based literature search (PubMed, ClinicalTrials.gov, Cochrane), extracts comparable sections, validates claims
  - `Reporting_Guideline_Checker`: Compliance validation against 5 major guidelines, structured audit reports with missing items
- **Guideline Support:**
  - **CONSORT**: Randomized Controlled Trials (participant flow, baseline characteristics, effect sizes)
  - **STROBE**: Observational studies (descriptive data, unadjusted/adjusted estimates)
  - **STARD**: Diagnostic accuracy (test results, diagnostic accuracy estimates)
  - **PRISMA**: Systematic reviews/meta-analyses (study selection, synthesis results, certainty of evidence)
  - **CARE**: Case reports (timeline, diagnostic assessment, intervention, outcomes)
- **Required Inputs:**
  - `section_type`: "Results" or "Discussion"
  - `study_summary`: Study design, population, intervention, comparator, outcomes
  - `results_data`: Statistical outputs (endpoints, p-values, CIs, effect sizes)
  - `evidence_chunks`: Supporting evidence from literature or RAG retrieval
  - `key_hypotheses`: Hypotheses being tested or discussed
  - `few_shot_examples`: 2-3 example passages for style guidance
- **Tools:** Tavily Web Search, Read URL Content, Exa Search, Google Docs integration, Gmail (drafts/send)
- **Writing Standards:**
  - Formal clinical writing tone with appropriate hedging
  - ICMJE format compliance
  - Statistical precision (exact values, CIs, p-values)
  - Evidence traceability with placeholders ([Figure X], [Table X], [REF])
  - Plain language where appropriate
- **Quality Control:**
  - Automatic guideline compliance checking
  - Statistical claim verification
  - Literature alignment validation
  - Structured audit reports
- **Integration:** Complements `agent-clinical-manuscript` for specialized section drafting; can receive evidence from `agent-evidence-synthesis`
- **Deployment:** LangSmith cloud via local proxy adapter ✅ **DEPLOYED**
  - **Execution model:** LangSmith cloud via local FastAPI proxy
  - **Compose service:** `agent-section-drafter-proxy` (FastAPI proxy to LangSmith API)
  - **Proxy location:** `services/agents/agent-section-drafter-proxy/`
  - **Config bundle:** `agents/Clinical_Study_Section_Drafter/` (AGENTS.md, config.json, tools.json)
  - **Invocation:** Orchestrator → proxy:8000 → LangSmith API
  - **Task Type:** `CLINICAL_SECTION_DRAFT` (registered in orchestrator ai-router)
  - **Authentication:** Requires `LANGSMITH_API_KEY` + `LANGSMITH_SECTION_DRAFTER_AGENT_ID` environment variables
  - **Health Check:** `/health`, `/health/ready` endpoints on proxy
  - **Artifact Paths:** `/data/artifacts/manuscripts/{workflow_id}/sections/{section_type}.md`
- **Required Environment Variables:**
  - `LANGSMITH_API_KEY` - LangSmith API access (required)
  - `TAVILY_API_KEY` - For Clinical_Evidence_Researcher sub-worker (optional)
  - `EXA_API_KEY` - For enhanced literature search (optional)
  - `GOOGLE_DOCS_API_KEY` - For Google Docs output (optional)
- **Deployment:** LangSmith cloud via local proxy adapter ✅ **DEPLOYED**
  - **Execution model:** LangSmith cloud via local FastAPI proxy
  - **Compose service:** `agent-section-drafter-proxy` (FastAPI proxy to LangSmith API)
  - **Proxy location:** `services/agents/agent-section-drafter-proxy/`
  - **Config bundle:** `agents/Clinical_Study_Section_Drafter/` (AGENTS.md, config.json, tools.json)
  - **Internal URL:** `http://agent-section-drafter-proxy:8000`
  - **AGENT_ENDPOINTS_JSON:** ✅ Included as `"agent-clinical-section-drafter":"http://agent-section-drafter-proxy:8000"`
  - **Health endpoints:** ✅ `/health`, `/health/ready` (validates LangSmith connectivity)
- **Validation:** Preflight checks LANGSMITH_API_KEY + task type registration; smoke test validates router dispatch
- **Source:** LangSmith Agent (see `agents/Clinical_Study_Section_Drafter/`)

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
- **Deployment:** LangSmith cloud via local proxy adapter ✅ **DEPLOYED**
  - **Execution model:** LangSmith cloud via local FastAPI proxy
  - **Compose service:** `agent-clinical-manuscript-proxy` (FastAPI proxy to LangSmith API)
  - **Proxy location:** `services/agents/agent-clinical-manuscript-proxy/`
  - **Config bundle:** `services/agents/agent-clinical-manuscript/` (AGENTS.md, config.json, tools.json)
  - **Internal URL:** `http://agent-clinical-manuscript-proxy:8000`
  - **Invocation:** Orchestrator → proxy:8000 → LangSmith API
  - **Task Type:** `CLINICAL_MANUSCRIPT_WRITE` (registered in orchestrator ai-router)
  - **AGENT_ENDPOINTS_JSON:** ✅ Included as `"agent-clinical-manuscript":"http://agent-clinical-manuscript-proxy:8000"`
  - **Authentication:** Requires `LANGSMITH_API_KEY` + `LANGSMITH_MANUSCRIPT_AGENT_ID` environment variables
  - **Health Check:** `/health`, `/health/ready` endpoints on proxy
- **Source:** LangSmith Agent "Clinical Manuscript Writer" (see `services/agents/agent-clinical-manuscript/`)


`agent-results-interpretation` — Results Interpretation Agent (Imported from LangSmith, 2026-02-08) ✅ **DEPLOYED**
- **Execution model:** LangSmith cloud via local proxy adapter
- **Compose service:** `agent-results-interpretation-proxy` (FastAPI proxy to LangSmith API)
- **Proxy location:** `services/agents/agent-results-interpretation-proxy/`
- **Internal URL:** `http://agent-results-interpretation-proxy:8000`
- **Router task types:** `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS` (alias) — registered in `ai-router.ts`
- **AGENT_ENDPOINTS_JSON:** ✅ Included as `"agent-results-interpretation":"http://agent-results-interpretation-proxy:8000"`
- **Health endpoints:** ✅ `/health`, `/health/ready` (validates LangSmith connectivity)
- **Required env vars:** `LANGSMITH_API_KEY`, `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID`
- **Optional env vars:** `LANGSMITH_API_URL`, `LANGSMITH_TIMEOUT_SECONDS`, `LANGCHAIN_PROJECT`, `GOOGLE_DOCS_API_KEY`
- **Purpose:** Multi-domain research results interpretation (clinical, social science, behavioral, survey)
- **Architecture:** LangSmith multi-agent system with 4 sub-workers (Literature Research, Methodology Audit, Section Draft, Draft Refinement)
- **Canonical wiring doc:** [`docs/agents/results-interpretation/wiring.md`](docs/agents/results-interpretation/wiring.md)
- **Environment setup:** [`docs/agents/results-interpretation/ENVIRONMENT.md`](docs/agents/results-interpretation/ENVIRONMENT.md)
- **Source (cloud agent):** `services/agents/agent-results-interpretation/`
- **Networks:** `backend` (orchestrator), `frontend` (LangSmith API)


### 1.4 Governance & Policy Agents

| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| `agent-policy-review` | 8000 | ✅ Production | Governance compliance checks |
| `agent-lit-triage` | 8000 | ✅ Production | AI-powered literature triage & prioritization (2026-02-07) |
| `agent-evidence-synth` | 8000 | 🚧 Stub | Evidence synthesis (deprecated, use agent-evidence-synthesis) |
| `agent-bias-detection` | 8000 | ✅ Production | Clinical bias detection & fairness assessment (2026-02-08) |

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

**NEW:** `agent-peer-review-simulator` — Comprehensive Peer Review Simulation (Imported from LangSmith, 2026-02-08)
- **Purpose:** Rigorous academic manuscript peer review simulation with multi-persona critiques, iterative revision cycles, and comprehensive reporting
- **Architecture:** LangSmith multi-agent system with 1 coordinator + 5 specialized sub-workers
- **Main Agent (Peer Review Coordinator):**
  - Orchestrates full peer review lifecycle: intake → critique → revision → approval
  - Manuscript intake: pasted text, Google Docs, preprint URLs (arXiv, bioRxiv, medRxiv)
  - Multi-cycle review iteration (up to 3 cycles recommended)
  - Comprehensive output delivery: Google Doc reports, critique tracking spreadsheets, email distribution
  - Default focus: Biomedical/clinical research (adaptable to any discipline)
- **Sub-Workers:**
  - `Critique_Worker`: Generates adversarial peer review critiques from specific reviewer personas (methodologist, statistician, ethics reviewer, domain expert). Invoked once per persona. Returns 3-5 structured critiques with severity ratings (Minor/Major/Critical), recommendations, and checklist references.
  - `Revision_Worker`: Produces revised manuscripts and point-by-point response letters addressing all critiques. Maintains academic quality and voice.
  - `Literature_Checker`: Verifies references, citations, novelty claims, literature coverage. Uses web search (Tavily/Exa) to validate citations, identify missing key references, assess novelty claims.
  - `Readability_Reviewer`: Assesses writing quality, clarity, logical flow, abstract/title effectiveness, figure/table descriptions, terminology consistency.
  - `Checklist_Auditor`: Item-by-item audit against appropriate reporting checklists (CONSORT, STROBE, PRISMA, STARD, SQUIRE, ARRIVE, CARE). Returns pass/partial/fail compliance table.
- **Default Reviewer Personas:**
  - **Methodologist**: Study design, statistical methods, power analysis, randomization, blinding, reproducibility
  - **Domain Expert**: Scientific merit, novelty, relevance, accuracy of claims, literature context
  - **Ethics Reviewer**: IRB/ethics approval, informed consent, COI, data privacy, responsible conduct
  - **Statistician**: Statistical analyses, effect sizes, confidence intervals, p-values, multiple comparisons
- **Reporting Checklist Support:**
  - **CONSORT**: Randomized Controlled Trials
  - **STROBE**: Observational Studies
  - **PRISMA**: Systematic Reviews/Meta-analyses
  - **STARD**: Diagnostic Accuracy Studies
  - **SQUIRE**: Quality Improvement Studies
  - **ARRIVE**: Animal Research
  - **CARE**: Case Reports
- **Workflow Phases:**
  1. **Intake**: Manuscript reception and field/study type confirmation
  2. **Persona Selection**: Reviewer persona configuration (default or custom)
  3. **Critique Phase**: Parallel execution of all workers (Critique_Workers × N, Literature_Checker, Readability_Reviewer, Checklist_Auditor)
  4. **Revision Phase**: Revision_Worker generates revised draft + response letter
  5. **Approval Decision**: User approves or triggers another review cycle (max 3 recommended)
  6. **Output Delivery**: Google Doc report, critique tracking spreadsheet, optional email distribution
- **Output Artifacts:**
  - **Chat Summary**: Immediate feedback with severity counts, top critiques, recommendations
  - **Google Doc Report**: Executive summary, full critiques, literature audit, readability review, checklist compliance, revised manuscript, response letter, metadata
  - **Critique Tracking Spreadsheet**: Living record with columns (Cycle | Source | Persona/Auditor | # | Severity | Issue | Recommendation | Status)
  - **Email Delivery**: Optional distribution to co-authors
- **Tool Dependencies:**
  - `google_docs_read_document`, `google_docs_create_document`, `google_docs_append_text`, `google_docs_replace_text`
  - `read_url_content` (preprint servers)
  - `tavily_web_search` (general), `exa_web_search` (academic, use `category="research paper"`)
  - `google_sheets_create_spreadsheet`, `google_sheets_write_range`, `google_sheets_append_rows`
  - `gmail_send_email`
- **Integration Points:**
  - **Stage 13 (InternalReviewAgent)**: Enhanced review option via `use_langsmith_peer_review: true` config
  - **Stage 11 (Iteration)**: Comprehensive feedback during refinement cycles
  - **Standalone**: Independent invocation for externally generated manuscripts
- **Differentiation from peer-review.service.ts:**
  - **peer-review.service.ts**: Quick automated scoring, basic comments, in-pipeline validation, single-pass
  - **agent-peer-review-simulator**: Deep multi-persona critiques, iterative cycles, comprehensive reports, checklist audits, literature verification, pre-submission refinement
- **Configuration Options:**
  - `personas`: Array of reviewer personas (default: ["methodologist", "statistician", "ethics_reviewer", "domain_expert"])
  - `max_review_cycles`: Integer, 1-3 (default: 1)
  - `enable_google_docs_output`: Boolean (default: false)
  - `study_type`: String (e.g., "RCT", "observational", "systematic_review")
- **Environment Variables:**
  - `LANGSMITH_PEER_REVIEW_URL`: LangSmith API endpoint
  - `LANGSMITH_PEER_REVIEW_AGENT_ID`: Agent ID from LangSmith
  - `LANGSMITH_API_KEY`: LangSmith API key
  - `GOOGLE_DOCS_API_KEY`, `GOOGLE_SHEETS_API_KEY`: Google API credentials
- **Status:** ✅ **Wired for Deployment** (2026-02-08) | ✅ **Proxy Service Created** | ✅ **Stage 13 Integrated**
- **Location:** `services/agents/agent-peer-review-simulator/` (config), `services/agents/agent-peer-review-simulator-proxy/` (proxy)
- **Documentation:** `README.md`, `INTEGRATION_GUIDE.md`, `AGENTS.md`, `subagents/*/AGENTS.md`
- **Wiring Guide:** `docs/agents/peer-review-simulator/wiring.md` ⭐
- **LangSmith Source:** Peer Review Simulator agent configuration
- **Router Task Type:** `PEER_REVIEW_SIMULATION` → `agent-peer-review-simulator`
- **Feature Flag:** `ENABLE_PEER_REVIEW_SIMULATOR` (Stage 13)
- **Validation:** Preflight + Smoke (CHECK_PEER_REVIEW=1)

**NEW:** `agent-bias-detection` — Clinical Bias Detection Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED**
- **Purpose:** Comprehensive bias detection and fairness assessment for clinical research datasets. Identifies and mitigates demographic, selection, and algorithmic biases ensuring equity and compliance with FDA AI fairness guidelines.
- **Architecture:** LangSmith multi-agent system with 1 coordinator + 5 specialized sub-workers
- **Main Agent (Clinical Bias Detection Coordinator):**
  - Six-phase workflow: Data Ingestion → Scan & Flag → Mitigation → Validation → Report → Audit Logging
  - Dataset intake: Pasted data, Google Sheets, or summary statistics
  - Bias scanning across sensitive attributes (gender, ethnicity, age, geography, SES)
  - Regulatory compliance assessment (FDA, ICH E9, NIH, EMA, OECD, WHO)
  - Adversarial validation and red-teaming
  - Comprehensive reporting: Google Docs, chat summaries, mitigated datasets
  - Persistent audit trail for regulatory traceability
- **Sub-Workers:**
  - `Bias_Scanner`: Deep quantitative bias analysis with metrics (representation analysis, outcome disparity, selection bias, intersectional analysis, statistical power assessment). Returns structured bias metrics report with severity levels and disparity scores.
  - `Bias_Mitigator`: Generates actionable mitigation strategies (resampling, stratified sampling, reweighting). Returns prioritized plan with effectiveness ratings, trade-offs, and post-mitigation quality scores.
  - `Compliance_Reviewer`: Regulatory risk assessment against FDA AI fairness guidelines, ICH E9, NIH inclusion policy, EMA, OECD AI principles, WHO equity guidelines. Returns compliance report with risk level, blocking issues, and regulatory readiness score.
  - `Red_Team_Validator`: Adversarial stress-testing of bias findings. Challenges findings, identifies mitigation risks, validates robustness. Returns validation report with robustness score.
  - `Audit_Logger`: Persistent audit trail management. Logs all analysis phases, findings, and decisions to Google Sheets for regulatory traceability. Maintains cumulative audit across sessions.
- **Bias Types Detected:**
  - **Demographic Bias**: Imbalances across gender, ethnicity, age groups
  - **Selection Bias**: Geographic, socioeconomic, access-based exclusions
  - **Algorithmic Bias**: Model outcome disparities across sensitive attributes
  - **Intersectional Bias**: Compounding disparities (e.g., elderly women of specific ethnicity)
- **Fairness Metrics:**
  - Demographic Parity: |P(outcome=1|group=A) - P(outcome=1|group=B)|
  - Representation Ratios: Observed vs expected population proportions
  - Equalized Odds: Equal TPR/FPR across groups
  - Disparate Impact: Outcome rate ratios (flag if <0.8 or >1.25)
- **Compliance Frameworks Supported:**
  - FDA AI/ML Fairness Guidelines
  - ICH E9 (Clinical Trials)
  - NIH Inclusion Policy (Women & Minorities)
  - EMA Guidelines (EU Trials)
  - OECD AI Principles (Ethical AI)
  - WHO Guidelines (Global Health Equity)
- **Workflow Phases:**
  1. **Data Ingestion**: Parse dataset, identify sensitive attributes and outcomes
  2. **Scan & Flag**: Bias_Scanner performs quantitative analysis, flags biases with reasoning
  3. **Mitigation**: Bias_Mitigator generates actionable strategies
  4. **Validation (Parallel)**: Compliance_Reviewer + Red_Team_Validator execute simultaneously
  5. **Report Generation**: Chat summary, Google Doc report, mitigated dataset output, optional email
  6. **Audit Logging**: Audit_Logger persists all findings for regulatory traceability
- **Output Artifacts:**
  - **Bias Verdict**: "Biased" (>2/10) or "Unbiased" (≤2/10) with bias score
  - **Bias Flags**: Structured list with type, severity, metrics, impact, compliance risk
  - **Mitigation Plan**: Prioritized strategies with effectiveness/difficulty ratings
  - **Compliance Risk Report**: Risk level, blocking issues, regulatory readiness score
  - **Red-Team Validation**: Robustness score, validated/challenged findings
  - **Google Doc Report**: Comprehensive report with all sections
  - **Mitigated Dataset**: Google Sheets with adjusted data and notes
  - **Audit Log**: Persistent trail in Google Sheets
- **Tool Dependencies:**
  - `tavily_web_search`: Research population demographics, FDA guidance
  - `read_url_content`: Read full articles/guidelines
  - `google_sheets_get_spreadsheet`, `google_sheets_read_range`: Dataset input
  - `google_sheets_create_spreadsheet`, `google_sheets_write_range`, `google_sheets_append_rows`: Output
  - `google_docs_create_document`, `google_docs_append_text`: Reports
  - `gmail_send_email`: Distribution
- **Edge Case Handling:**
  - Small datasets (N<100 or subgroup<30): Flag low statistical power
  - Rare/intersectional biases: Multi-attribute analysis
  - No biases detected: Full metrics report as evidence, still run validation
  - Incomplete data: Request additional data before proceeding
  - Red-team rejects finding: Present both perspectives, user decides
  - Compliance blocking issues: Escalate prominently
- **Integration Points:**
  - **Stage 4b (DatasetValidationAgent)**: Pre-analysis bias screening
  - **Stage 7 (StatisticalModelAgent)**: Fairness metrics in model evaluation
  - **Stage 9 (InterpretationAgent)**: Bias consideration in results interpretation
  - **Stage 14 (EthicalReviewAgent)**: Ethics compliance validation
  - **Standalone**: Independent bias audits for externally generated datasets
- **Deployment:** LangSmith cloud via local proxy adapter ✅ **FULLY WIRED**
  - **Execution model:** LangSmith cloud via local FastAPI proxy
  - **Compose service:** `agent-bias-detection-proxy` (FastAPI proxy to LangSmith API)
  - **Proxy location:** `services/agents/agent-bias-detection-proxy/`
  - **Config bundle:** `agents/Clinical_Bias_Detection_Agent/` (AGENTS.md, config.json, tools.json, subagents/)
  - **Internal URL:** `http://agent-bias-detection-proxy:8000`
  - **Task Type:** `CLINICAL_BIAS_DETECTION` ✅ **REGISTERED** in orchestrator ai-router
  - **AGENT_ENDPOINTS_JSON:** ✅ Included as `"agent-bias-detection":"http://agent-bias-detection-proxy:8000"`
  - **Health Check:** `/health`, `/health/ready` endpoints on proxy
  - **Artifact Paths:** `/data/artifacts/<run>/bias_detection/<stage>/`
- **Required Environment Variables:**
  - `LANGSMITH_API_KEY` - LangSmith API access (required)
  - `LANGSMITH_BIAS_DETECTION_AGENT_ID` - Agent ID from LangSmith (required)
  - `LANGSMITH_BIAS_DETECTION_TIMEOUT_SECONDS` - Default: 300 (optional)
  - `TAVILY_API_KEY` - For web research (optional)
  - `GOOGLE_DOCS_API_KEY`, `GOOGLE_SHEETS_API_KEY` - For Google Workspace integration (optional)
- **Status:** ✅ **WIRED** (2026-02-08) | ✅ **Proxy Service Operational** | ✅ **Orchestrator Integrated** | ✅ **Validation Complete**
- **Location:** `agents/Clinical_Bias_Detection_Agent/` (config), `services/agents/agent-bias-detection-proxy/` (proxy)
- **Documentation:** 
  - **Canonical Wiring Guide:** [`docs/agents/clinical-bias-detection/wiring.md`](docs/agents/clinical-bias-detection/wiring.md) ⭐ **PRIMARY REFERENCE**
  - **Agent Briefing:** `AGENT_BIAS_DETECTION_BRIEFING.md`
  - **Proxy README:** `services/agents/agent-bias-detection-proxy/README.md`
  - **Agent Prompt:** `agents/Clinical_Bias_Detection_Agent/AGENTS.md`
- **LangSmith Source:** Clinical Bias Detection Agent configuration
- **Communication Style:** Precise & quantitative, direct about findings, actionable recommendations, clinical terminology with explanations, patient equity focus, compliance-aware
- **Validation:** Preflight checks LANGSMITH_API_KEY + agent ID + task type registration; smoke test validates router dispatch + proxy health (CHECK_BIAS_DETECTION=1)

**NEW:** `agent-dissemination-formatter` — Dissemination Formatter Agent (Imported from LangSmith, 2026-02-08) ✅ **IMPORTED**
- **Purpose:** Publication formatting agent that converts academic manuscripts into journal-specific, submission-ready formats. Handles LaTeX/Word formatting, citation style conversion, reference verification, cover letter drafting, and reviewer response formatting.
- **Architecture:** LangSmith multi-agent system with 1 main agent + 5 specialized worker subagents
- **Main Agent (Dissemination Formatter):**
  - Seven-phase workflow: Input Gathering → Journal Research → Manuscript Formatting → Reference Verification → Cover Letter Drafting → Output Delivery → Submission Email Draft
  - Manuscript intake: Pasted text, Google Docs, email triggers
  - Multi-format output: LaTeX, Google Docs, structured text
  - IMRaD structure parsing and journal template application
  - Citation style conversion (APA, Vancouver, IEEE, numbered, author-year)
  - Comprehensive validation and compliance checking
  - Automated cover letter generation with journal-specific tailoring
  - Reviewer response document formatting for revisions
- **Worker Subagents:**
  - `Journal_Guidelines_Researcher`: Researches journal-specific formatting requirements (margins, fonts, citation styles, word limits, submission requirements). Uses web search and URL content extraction to compile comprehensive formatting guidelines.
  - `Manuscript_Formatter`: Core formatting engine. Parses IMRaD structure, applies journal templates, generates LaTeX/Word output, reformats citations, validates compliance. Returns formatted manuscript with validation checklist.
  - `Reference_Verifier`: Cross-checks bibliographic references for accuracy and completeness. Verifies DOIs, author names, publication years, journal titles, flags retractions, identifies missing fields. Returns detailed verification report with suggested corrections.
  - `Cover_Letter_Drafter`: Drafts professional submission cover letters. Researches journal editorial scope, identifies editor names, analyzes manuscript contributions, produces tailored cover letter. Returns letter as Google Doc and text.
  - `Reviewer_Response_Formatter`: Formats point-by-point responses to peer reviewer comments. Parses reviewer feedback, structures rebuttal document, tracks revisions with page/line references. Returns formatted response-to-reviewers document.
- **Supported Journals & Templates:**
  - **arXiv**: Standard LaTeX article class, flexible citation style
  - **Nature**: Word preferred, numbered superscript citations, ~3,000 words
  - **Science**: Word/LaTeX, numbered citations, ~2,500 words
  - **NEJM**: Word, Vancouver style, ~2,500 words
  - **IEEE**: LaTeX IEEEtran class, two-column, numbered [1]
  - **ACM**: LaTeX acmart class, numbered [1]
  - **PLOS ONE**: Word/LaTeX, Vancouver style, unlimited length
  - **APA Journals**: Word, APA 7th edition, author-year citations
  - Plus any journal via Journal_Guidelines_Researcher
- **Formatting Capabilities:**
  - **IMRaD Parsing**: Automatic section identification (Title, Authors, Abstract, Keywords, Introduction, Methods, Results, Discussion, Conclusions, Acknowledgments, References, Figures, Tables)
  - **LaTeX Generation**: Complete compilable .tex files with proper document class, packages, formatting
  - **Citation Conversion**: Automatic reformatting between APA, Vancouver, IEEE, numbered, author-year styles
  - **Compliance Validation**: 11-point checklist (sections, word limits, citations, references, figures/tables, title page, declarations, headings, fonts, spacing)
  - **Reference Quality**: DOI verification, author name checking, retraction detection, completeness validation
  - **Figure/Table Handling**: Placeholder environments, caption formatting, cross-reference preservation
- **Workflow Phases:**
  1. **Input Gathering**: Read manuscript (chat/Google Doc/email), identify target journal and output format
  2. **Journal Research**: Journal_Guidelines_Researcher fetches formatting requirements
  3. **Manuscript Formatting**: Manuscript_Formatter applies journal template and citations
  4. **Reference Verification**: Reference_Verifier validates bibliography (optional)
  5. **Cover Letter Drafting**: Cover_Letter_Drafter generates submission letter (optional)
  6. **Output Delivery**: Present formatted manuscript, validation report, reference report in chat/Google Docs
  7. **Submission Email**: Optional email draft for submission
- **Revision Workflow:**
  - Handles peer review feedback and revision formatting
  - Reviewer_Response_Formatter creates point-by-point rebuttals
  - Re-formats revised manuscripts for resubmission
  - Tracks changes with page/line references
- **Output Artifacts:**
  - **Formatted Manuscript**: LaTeX code or Google Doc with journal formatting applied
  - **Validation Report**: Compliance checklist with pass/fail for each requirement
  - **Reference Verification Report**: Bibliography accuracy assessment with flagged issues
  - **Cover Letter**: Professional submission letter (Google Doc + text)
  - **Reviewer Response Document**: Structured rebuttal with numbered comments and responses (for revisions)
  - **Submission Email Draft**: Pre-filled email for journal submission
- **Tool Dependencies:**
  - `google_docs_read_document`: Read manuscripts from Google Docs
  - `google_docs_create_document`: Create formatted output documents
  - `google_docs_append_text`: Add content to documents
  - `google_docs_replace_text`: Make targeted edits
  - `gmail_read_emails`: Process email triggers
  - `gmail_draft_email`: Draft submission emails
  - `tavily_web_search`: Search journal requirements and research guidelines
  - `read_url_content`: Extract content from journal websites
- **Quality Standards:**
  - LaTeX output must be compilable without errors
  - 100% citation style consistency
  - No content loss during formatting
  - Honest validation (never mark passing if failing)
  - Never alter scientific content
  - Never fabricate references or data
- **Edge Case Handling:**
  - Non-IMRaD manuscripts (reviews, letters): Identifies actual structure
  - Large reference lists (50+): Prioritizes verification, notes limitations
  - Missing journal information: Explicit user prompts rather than guessing
  - Figure/table references: Preserves all cross-references and captions
  - Multiple journal targets: Formats once per journal
  - Iterative edits: Uses targeted replace for corrections
- **Integration Points:**
  - **Stage 19 (DisseminationAgent)**: Publication formatting for manuscript submission
  - **Stage 13 + Revision Workflow**: Reviewer response formatting for revisions
  - **Standalone**: Independent manuscript formatting and cover letter drafting
- **Status:** ✅ **IMPORTED** (2026-02-08) | 📋 **Config Available** | ⏳ **Proxy Not Yet Deployed**
- **Location:** `services/agents/agent-dissemination-formatter/` (config + workers)
  - Main agent: `README.md`, `config.json`, `tools.json`
  - Workers: `workers/journal_guidelines_researcher/`, `workers/manuscript_formatter/`, `workers/reference_verifier/`, `workers/cover_letter_drafter/`, `workers/reviewer_response_formatter/`
- **Documentation:**
  - **Main README:** `services/agents/agent-dissemination-formatter/README.md` ⭐ **PRIMARY REFERENCE**
  - **Worker Specs:** `services/agents/agent-dissemination-formatter/workers/*/AGENTS.md`
  - **Config:** `services/agents/agent-dissemination-formatter/config.json`
  - **Tools:** `services/agents/agent-dissemination-formatter/tools.json`
- **LangSmith Source:** Dissemination Formatter custom agent
- **Communication Style:** Meticulous, precise, thorough, professional academic tone, concise but explanatory, explicit about uncertainties
- **Next Steps:** 
  - Create proxy service structure (`agent-dissemination-formatter-proxy/`)
  - Add to docker-compose.yml
  - Register task type `DISSEMINATION_FORMATTING` in ai-router
  - Add to AGENT_ENDPOINTS_JSON
  - Create wiring documentation

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
  "agent-lit-triage": "http://agent-lit-triage:8000",
  "agent-policy-review": "http://agent-policy-review:8000",
  "agent-rag-ingest": "http://agent-rag-ingest:8000",
  "agent-rag-retrieve": "http://agent-rag-retrieve:8000",
  "agent-verify": "http://agent-verify:8000",
  "agent-intro-writer": "http://agent-intro-writer:8000",
  "agent-methods-writer": "http://agent-methods-writer:8000",
  "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000",
  "agent-results-interpretation": "http://agent-results-interpretation-proxy:8000",
  "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000",
  "agent-clinical-section-drafter": "http://agent-section-drafter-proxy:8000"
}
```

**Note:** LangSmith-hosted agents use `-proxy` suffix in their service names but are accessed via their logical names (without `-proxy`) in routing.


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

- `agent-stage2-synthesize` - Evidence synthesis (deprecated, use agent-evidence-synthesis)
- `agent-results-writer` - Results section writing
- `agent-discussion-writer` - Discussion section writing
- `agent-evidence-synth` - Evidence synthesis (deprecated, use agent-evidence-synthesis)

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

**LangSmith Proxy Variables (for cloud-hosted agents):**
- `LANGSMITH_API_KEY` - LangSmith API access (required for all proxies)
- `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` - Results Interpretation agent UUID
- `LANGSMITH_MANUSCRIPT_AGENT_ID` - Clinical Manuscript Writer agent UUID
- `LANGSMITH_SECTION_DRAFTER_AGENT_ID` - Clinical Section Drafter agent UUID
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: 180-300 (agent-specific)

**Optional Variables:**
- `GOVERNANCE_MODE` - LIVE or DEMO
- `LOCAL_MODEL_ENABLED` - Enable Ollama
- `PHI_SCAN_ENABLED` - PHI scanning toggle
- `COMPOSIO_API_KEY` - Composio integration
- `LANGCHAIN_PROJECT` - LangSmith project name
- `LANGCHAIN_TRACING_V2` - Enable LangSmith tracing (true/false)
- `EXA_API_KEY` - Exa semantic search (for agent-lit-triage)
- `TAVILY_API_KEY` - Tavily web search (for agent-evidence-synthesis, LangSmith agents)

---

**Document Version:** 1.1  
**Last Updated:** 2025-02-07  
**Maintained By:** ResearchFlow Platform Team

---

## APPENDIX C: Agent-Lit-Triage Quick Reference

### Service Details
- **Name:** `agent-lit-triage`
- **Container:** `researchflow-agent-lit-triage`
- **Internal URL:** `http://agent-lit-triage:8000`
- **Health Endpoint:** `GET /health`
- **Task Type:** `LIT_TRIAGE`

### Environment Variables
- `EXA_API_KEY` - Optional, for semantic search (mocks if not set)
- `LANGCHAIN_API_KEY` - Optional, for LangSmith tracing
- `LANGCHAIN_PROJECT` - Default: `researchflow-lit-triage`
- `LANGCHAIN_TRACING_V2` - Default: `false`
- `GOVERNANCE_MODE` - Default: `DEMO`
- `LOG_LEVEL` - Default: `INFO`

### API Endpoints
1. **POST /agents/run/sync** - Synchronous triage execution
   ```json
   {
     "request_id": "req-123",
     "task_type": "LIT_TRIAGE",
     "inputs": {
       "query": "CAR-T therapy efficacy in lymphoma",
       "date_range_days": 730,
       "min_results": 15
     }
   }
   ```

2. **POST /agents/run/stream** - Streaming triage execution (SSE)

3. **GET /health** - Health check
   ```json
   {"status": "ok"}
   ```

4. **GET /health/ready** - Readiness check
   ```json
   {"status": "ready"}
   ```

### Integration with Stage 2
To enable triage in Stage 2 Literature Pipeline:
1. Set `ENABLE_LIT_TRIAGE=true` in orchestrator environment
2. Agent will be automatically called via router dispatch
3. Results feed into screening/extraction pipeline

### Validation Commands
```bash
# Check container health
docker compose ps agent-lit-triage

# View logs
docker compose logs -f agent-lit-triage

# Test health endpoint (internal network)
docker compose exec agent-lit-triage curl -f http://localhost:8000/health

# Test via orchestrator router
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "LIT_TRIAGE",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "query": "cancer immunotherapy"
    }
  }'
```

### Output Schema
See `docs/schemas/agent-lit-triage-io.json` for complete input/output schemas.

