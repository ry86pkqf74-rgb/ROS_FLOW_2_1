# AGENT INVENTORY - ResearchFlow Production

**Generated:** 2025-02-06  
**Branch:** chore/inventory-capture  
**Milestone:** 03 - Agent Fleet Scaffold  

## Executive Summary

This inventory captures ALL agents, model integrations, prompt files, and LLM calls across the entire ResearchFlow codebase.

**Total Counts:**
- **Microservice Agents (Docker):** 25 (15 native + 10 LangSmith proxies)
- **Stage Agents (Workflow Engine):** 20
- **Specialized Agents (Worker):** 15+
- **LangGraph Agents:** 8
- **LangSmith Multi-Agent Systems:** 13 (Evidence Synthesis, Clinical Manuscript Writer, Literature Triage, Clinical Study Section Drafter, Results Interpretation, Peer Review Simulator, Clinical Bias Detection, Dissemination Formatter, Performance Optimizer, Journal Guidelines Cache, Compliance Auditor, Artifact Auditor, Multilingual Literature Processor)
- **LangSmith Proxy Services:** 14 (Results Interpretation, Clinical Manuscript Writer, Clinical Section Drafter, Peer Review Simulator, Clinical Bias Detection, Dissemination Formatter, Performance Optimizer, Journal Guidelines Cache, Compliance Auditor, Artifact Auditor, Resilience Architecture Advisor, Multilingual Literature Processor, Clinical Model Fine-Tuner, Hypothesis Refiner)
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
| `agent-compliance-auditor` | 8000 | ✅ Production | Regulatory compliance auditing across HIPAA, IRB, EU AI Act, GDPR, FDA SaMD (2026-02-08) |
| `agent-clinical-model-fine-tuner` | 8000 | ✅ Production | Clinical model fine-tuning with compliance tracking (2026-02-08) |

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

**NEW:** `agent-compliance-auditor` — Compliance Auditor Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Comprehensive regulatory compliance auditing system for health technology workflows. Continuously scans workflow logs, detects violations across multiple regulatory frameworks (HIPAA, IRB, EU AI Act, GDPR, FDA SaMD), assesses risks, and generates remediation action plans.
- **Architecture:** LangSmith multi-agent system with 1 coordinator + 3 specialized sub-workers
- **Main Agent (Compliance Auditor Coordinator):**
  - Three-phase workflow: SCAN (log ingestion) → AUDIT (risk assessment) → REMEDIATE (action planning)
  - Log intake: Google Sheets spreadsheets or direct chat paste
  - Multi-framework violation detection with regulatory provision mapping
  - Risk scoring: CRITICAL/HIGH/MEDIUM/LOW severity with timebound remediation
  - PHI event detection and handling guidance
  - Formal report generation via Google Docs
  - Remediation tracking via Google Sheets with regression detection
  - Code-level compliance scanning via GitHub API
- **Sub-Workers:**
  - `Audit_Report_Generator`: Generates formal, persistent compliance audit reports as Google Docs. Creates professionally formatted documents with executive summary, scan results, audit findings, remediation plan, regulatory updates, and audit metadata. Returns document URL and ID. Triggered when user requests formal report or CRITICAL findings detected.
  - `Codebase_Compliance_Scanner`: Source code compliance auditor for GitHub repositories. Scans for hardcoded PHI/PII, missing encryption configurations, insecure logging patterns, AI/ML compliance gaps, GDPR data governance issues, and documentation gaps. Auto-creates GitHub issues for CRITICAL findings. Returns structured list with file paths, line references, severity, and remediation guidance.
  - `Regulatory_Research_Worker`: Monitors and retrieves latest regulatory updates across all frameworks. Uses web search to find recent guidance documents, enforcement actions, and evolving requirements. Returns structured summary with effective dates, impact assessments, and action items. Prioritizes official government/regulatory sources (HHS.gov, FDA.gov, ec.europa.eu).
- **Regulatory Frameworks Covered:**
  - **HIPAA**: Privacy Rule, Security Rule, Breach Notification Rule (unauthorized PHI disclosures, missing encryption, inadequate access controls, absent audit trails)
  - **IRB**: Human subjects research protections (protocol deviations, missing informed consent, unapproved amendments, adverse event reporting gaps)
  - **EU AI Act**: High-risk health AI classification Article 6 Annex III (missing risk management, inadequate human oversight, insufficient transparency, conformity assessment gaps, missing CE marking)
  - **GDPR**: Article 9 health data processing (processing without legal basis, missing DPIAs, cross-border transfers without safeguards, data subject rights violations)
  - **FDA SaMD**: Software as Medical Device (missing regulatory classification, absent QMS documentation, post-market surveillance gaps, adverse event reporting failures)
- **Audit Workflow Phases:**
  1. **Phase 1 - SCAN**: Log ingestion, event extraction (PHI events, access control, system events, research events, AI/ML events), classification by regulatory domain
  2. **Phase 2 - AUDIT**: Violation detection (VIOLATION 🔴/WARNING 🟡/COMPLIANT 🟢), risk scoring (CRITICAL/HIGH/MEDIUM/LOW), evidence mapping with regulatory provision citations
  3. **Phase 3 - REMEDIATE**: Immediate actions, short-term fixes (30d), long-term improvements, auto-anonymization guidance for PHI leaks
- **Event Types Monitored:**
  - **PHI Events**: Creation, access, modification, transmission, deletion of Protected Health Information
  - **Access Control Events**: Login attempts, permission changes, role assignments, data exports
  - **System Events**: Configuration changes, encryption status, backups, software deployments
  - **Research Events**: Study enrollments, consent captures, data collection, protocol modifications
  - **AI/ML Events**: Model training, inference operations, data pipelines, deployments
- **Output Artifacts:**
  - **Audit Report (Chat)**: Executive summary, scan results table, audit findings table, remediation plan table, tracker status, regulatory updates, audit trail metadata
  - **Formal Audit Report (Google Docs)**: Professional document with CONFIDENTIAL classification, report ID, comprehensive sections, timestamps, sign-off block
  - **Remediation Tracker (Google Sheets)**: Persistent tracking with columns (Finding ID, Date Found, Severity, Framework, Provision, Description, Status, Owner, Due Date, Resolution Notes). Features repeat finding detection and overdue flagging.
  - **GitHub Issues**: Auto-created for CRITICAL code-level findings with file path, line references, severity, remediation guidance
- **Tool Dependencies:**
  - `google_sheets_get_spreadsheet`, `google_sheets_read_range`: Log ingestion
  - `google_sheets_create_spreadsheet`, `google_sheets_append_rows`, `google_sheets_write_range`: Remediation tracker management
  - `google_docs_create_document`, `google_docs_append_text`: Formal report generation
  - `tavily_web_search`, `read_url_content`: Regulatory research
  - `github_list_directory`, `github_get_file`, `github_create_issue`: Code scanning (via Codebase_Compliance_Scanner)
- **Usage Patterns:**
  - **Pattern 1 - Log-Level Audit**: Ingest logs → Extract events → Assess violations → Generate remediation → [Auto-offer formal report if CRITICAL]
  - **Pattern 2 - Code-Level Audit**: Delegate to Codebase_Compliance_Scanner → Scan repo → Detect violations → Auto-create GitHub issues → Integrate findings
  - **Pattern 3 - Combined Audit**: Log + Code scanning → Cross-reference findings → Unified action plan → Formal report
  - **Pattern 4 - Regulatory Update Check**: Delegate to Regulatory_Research_Worker → Search updates → Return structured summary → Integrate into audit report
  - **Pattern 5 - Remediation Tracking**: Ingest existing tracker → Check for repeat findings → Append new findings → Report status (Open/Overdue/Repeat/Resolved)
- **Behavioral Guidelines:**
  - Cite specific regulatory provisions (e.g., "HIPAA §164.312(a)(1)")
  - Conservative risk assessment: flag as WARNING rather than compliant when ambiguous
  - Never display raw PHI: use `[PHI-REDACTED]` placeholders
  - Acknowledge limitations when logs are incomplete
  - Proactively suggest code scans when log findings hint at systemic issues
  - Proactively suggest regulatory research when findings are in evolving areas
  - Auto-offer formal report generation for CRITICAL findings
- **Integration Points:**
  - **Workflow Logs**: Application logs, access logs, system logs, audit trails
  - **GitHub Repositories**: Source code compliance auditing
  - **Google Workspace**: Report generation and remediation tracking
  - **Monitoring Systems**: Can be triggered on-demand or scheduled
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-compliance-auditor-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `COMPLIANCE_AUDIT` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Ready for preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/agent-compliance-auditor-proxy/wiring.md` ⭐
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `LANGSMITH_COMPLIANCE_AUDITOR_TIMEOUT_SECONDS` - Request timeout (default: 300)
  - `GOOGLE_WORKSPACE_API_KEY` - For Sheets/Docs integration (tool-level requirement)
  - `GITHUB_TOKEN` - For code scanning (tool-level requirement)
  - `TAVILY_API_KEY` - For web research (optional)
- **Location:** `services/agents/agent-compliance-auditor/` (config, subagents), `services/agents/agent-compliance-auditor-proxy/` (proxy)
- **Documentation:** 
  - **Agent Briefing:** `AGENT_COMPLIANCE_AUDITOR_BRIEFING.md` ⭐ **PRIMARY REFERENCE**
  - **Wiring Guide:** `docs/agents/agent-compliance-auditor-proxy/wiring.md` ⭐
  - **Agent Definition:** `services/agents/agent-compliance-auditor/AGENTS.md`
  - **Configuration:** `services/agents/agent-compliance-auditor/config.json`
  - **Tools:** `services/agents/agent-compliance-auditor/tools.json`
  - **Sub-Workers:** `services/agents/agent-compliance-auditor/subagents/*/AGENTS.md`
  - **Proxy README:** `services/agents/agent-compliance-auditor-proxy/README.md`
- **Task Type:** `COMPLIANCE_AUDIT` → `agent-compliance-auditor-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-compliance-auditor-proxy:8000`

  - **Proxy README:** `services/agents/agent-bias-detection-proxy/README.md`
  - **Agent Prompt:** `agents/Clinical_Bias_Detection_Agent/AGENTS.md`
- **LangSmith Source:** Clinical Bias Detection Agent configuration
- **Communication Style:** Precise & quantitative, direct about findings, actionable recommendations, clinical terminology with explanations, patient equity focus, compliance-aware
- **Validation:** Preflight checks LANGSMITH_API_KEY + agent ID + task type registration; smoke test validates router dispatch + proxy health (CHECK_BIAS_DETECTION=1)

**NEW:** `agent-artifact-auditor` — Artifact Auditor Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Comprehensive compliance auditing system for dissemination artifacts (manuscripts, reports, formatted research outputs) against established reporting standards (CONSORT, PRISMA, STROBE, SPIRIT, CARE, ARRIVE, TIDieR, CHEERS, MOOSE). Ensures quality, consistency, and equitable reporting across all artifacts with persistent audit logging and cross-artifact trend analysis.
- **Architecture:** LangSmith multi-agent system with 1 coordinator + 3 specialized sub-workers

**NEW:** `agent-clinical-model-fine-tuner` — Clinical Model Fine-Tuner Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Model fine-tuning system for clinical AI models. Optimizes domain-specific model performance through supervised fine-tuning on validated clinical datasets with compliance tracking and model versioning.
- **Architecture:** LangSmith multi-agent system with 1 coordinator + specialized sub-workers
- **Main Agent Capabilities:**
  - Multi-phase workflow: Dataset Validation → Hyperparameter Tuning → Training Execution → Model Evaluation → Deployment Preparation
  - Training dataset intake: CSV, JSON, Google Sheets, or structured text formats
  - Model architecture support: Clinical BERT, BioClinicalBERT, PubMedBERT, GPT-based models
  - Hyperparameter optimization with grid search and Bayesian optimization
  - Training monitoring with early stopping and checkpoint management
  - Model evaluation with clinical metrics (accuracy, precision, recall, F1, AUROC)
  - Compliance tracking with audit trail and model cards
  - Model versioning and deployment artifacts
- **Tool Dependencies:**
  - Google Sheets: Dataset ingestion and results tracking
  - Google Docs: Model card and training report generation
  - Web search: Research best practices and hyperparameter recommendations
- **Integration Points:**
  - **Training Data Sources:** Stage 2 literature extraction, Stage 4 dataset validation, manual clinical annotations
  - **Downstream Consumers:** Stage 7 statistical models, Stage 9 interpretation agents, clinical prediction agents
  - **Standalone:** Independent model fine-tuning for externally curated datasets
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-clinical-model-fine-tuner-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `CLINICAL_MODEL_FINE_TUNING` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_CLINICAL_MODEL_FINE_TUNER_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `LANGSMITH_CLINICAL_MODEL_FINE_TUNER_TIMEOUT_SECONDS` - Request timeout (default: 600)
  - `GOOGLE_WORKSPACE_API_KEY` - For Sheets/Docs integration
- **Location:** `services/agents/agent-clinical-model-fine-tuner/` (config, subagents), `services/agents/agent-clinical-model-fine-tuner-proxy/` (proxy)
- **Task Type:** `CLINICAL_MODEL_FINE_TUNING` → `agent-clinical-model-fine-tuner-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-clinical-model-fine-tuner-proxy:8000`
- **Validation:** Preflight checks LANGSMITH_API_KEY + LANGSMITH_CLINICAL_MODEL_FINE_TUNER_AGENT_ID; smoke test validates router dispatch + proxy health (CHECK_CLINICAL_MODEL_FINE_TUNER=1)

**NEW:** `agent-hypothesis-refiner` — Hypothesis Refiner Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Clinical research hypothesis refinement system. Generates, validates, and iteratively refines research hypotheses using PICOT (Population, Intervention, Comparison, Outcome, Timeframe) and SMART (Specific, Measurable, Achievable, Relevant, Time-bound) frameworks. Produces evidence-grounded, feasible, and unbiased hypotheses for all medical domains with evidence synthesis and ethical validation.
- **Architecture:** LangSmith multi-agent system with 1 coordinator + 1 evidence validation sub-worker
- **Main Agent Capabilities:**
  - Multi-phase workflow: Intake & Context Gathering → Generate Hypotheses (3-5 candidates) → Validate with Evidence → Refine (Iterative) → Output & Documentation
  - Hypothesis intake: Vague statements, well-formed hypotheses, or research questions (chat or Google Docs)
  - PICOT framework structuring: Population, Intervention, Comparison, Outcome, Timeframe
  - SMART criteria compliance: Specific, Measurable, Achievable, Relevant, Time-bound
  - Multi-dimensional hypothesis scoring (1-10 scale): Evidence Strength (25%), Novelty (20%), Statistical Feasibility (20%), Ethical Soundness (15%), Clinical Relevance (20%)
  - Iterative refinement loop (up to 3 iterations) with target score ≥7
  - Evidence-based validation via delegated evidence retrieval worker
  - Ethical and bias assessments (population diversity, health equity, vulnerable groups)
  - Dual-output delivery: chat summaries + formal Google Doc refinement reports
  - Domain-agnostic design: Handles all medical specialties with domain-specific PICOT framing
- **Sub-Workers:**
  - `Evidence_Retrieval_Validator`: Performs deep evidence retrieval for each hypothesis candidate. Called once per hypothesis. Searches PubMed, Google Scholar, clinical registries for supporting/conflicting evidence. Returns evidence strength rating, literature citations, and gap analysis.
- **Tool Dependencies:**
  - Tavily Web Search: Literature search (PubMed, clinical databases)
  - Read URL Content: Extract evidence from papers and registries
  - Google Docs: `google_docs_create_document`, `google_docs_append_text`, `google_docs_read_document` (intake and output)
- **Integration Points:**
  - **Upstream Sources:** Stage 1 research question formulation, Stage 2 literature review outputs, manual hypothesis drafts
  - **Downstream Consumers:** Stage 3 protocol design, Stage 4 study design selection, hypothesis-driven data analysis
  - **Standalone:** Independent hypothesis refinement for externally provided research questions
- **Hypothesis Scoring Dimensions:**
  - **Evidence Strength (25%):** How well-supported by existing literature
  - **Novelty (20%):** Degree of originality vs. existing research
  - **Statistical Feasibility (20%):** Likelihood of adequate power given realistic sample sizes
  - **Ethical Soundness (15%):** Absence of bias concerns, diverse population coverage
  - **Clinical Relevance (20%):** Practical significance for patient outcomes or clinical practice
- **Ethical & Bias Guidelines:**
  - Flags underrepresentation of specific populations (age, sex, ethnicity, socioeconomic status)
  - Health equity implications assessment
  - No biological essentialism without evidence
  - Conflict of interest detection in cited literature
  - Diverse enrollment criteria by default
  - Regulatory compliance notes (FDA, pediatric, geriatric)
- **Supported Domains:** All medical specialties (oncology, cardiology, diabetes, neurology, rare diseases, etc.) with domain-specific adaptation
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-hypothesis-refiner-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `HYPOTHESIS_REFINEMENT` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/agent-hypothesis-refiner-proxy/wiring.md` ⭐
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `LANGSMITH_HYPOTHESIS_REFINER_TIMEOUT_SECONDS` - Request timeout (default: 300)
  - `TAVILY_API_KEY` - For Evidence_Retrieval_Validator sub-worker (optional)
- **Location:** `services/agents/agent-hypothesis-refiner/` (config, subagents), `services/agents/agent-hypothesis-refiner-proxy/` (proxy)
- **Documentation:** 
  - **Wiring Guide:** `docs/agents/agent-hypothesis-refiner-proxy/wiring.md` ⭐
  - **Agent Definition:** `services/agents/agent-hypothesis-refiner/AGENTS.md`
  - **Proxy README:** `services/agents/agent-hypothesis-refiner-proxy/README.md`
- **Task Type:** `HYPOTHESIS_REFINEMENT` → `agent-hypothesis-refiner-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-hypothesis-refiner-proxy:8000`
- **Validation:** Preflight checks LANGSMITH_API_KEY + LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID; smoke test validates router dispatch + proxy health + deterministic fixture hypothesis (CHECK_HYPOTHESIS_REFINER=1)

- **Main Agent (Artifact Auditor Coordinator):**
  - Six-step workflow: Parse Artifact → Determine Standard → Retrieve Guideline Checklist → Audit via Compliance Auditor → Generate Report → Log to Tracker
  - Artifact intake: GitHub files, Google Docs, URLs, direct text input
  - Multi-standard support (9 major standards) with automatic inference and user override
  - Item-by-item compliance checking with severity classification (CRITICAL/MAJOR/MINOR)
  - Equity & inclusivity gap detection (demographics, subgroups, limitations)
  - Dual-output delivery: chat summaries + formal Google Doc reports
  - Persistent audit logging via Google Sheets for trend analysis
  - Batch audit support for multi-artifact compliance monitoring
- **Sub-Workers:**
  - `Guideline_Researcher`: Retrieves and structures latest official checklists for any reporting standard. Always called first before auditing. Returns structured checklist with item numbers, descriptions, required/recommended status.
  - `Compliance_Auditor`: Performs deep item-by-item audit of artifact against checklist. Called once per artifact. Returns detailed compliance findings with severity ratings and actionable recommendations.
  - `Cross_Artifact_Tracker`: Analyzes audit findings across multiple past audits for trends and recurring gaps. Triggered when user requests trend analysis or compliance summary.
- **Supported Reporting Standards (9):**
  - CONSORT (25 items): Randomized controlled trials
  - PRISMA (27 items): Systematic reviews / meta-analyses
  - STROBE (22 items): Observational studies
  - SPIRIT (33 items): Clinical trial protocols
  - CARE (13 items): Case reports
  - ARRIVE (21 items): Animal research
  - TIDieR (12 items): Intervention descriptions
  - CHEERS (24 items): Health economic evaluations
  - MOOSE (35 items): Meta-analyses of observational studies
- **Tool Dependencies:**
  - GitHub: `github_get_file`, `github_list_directory`, `github_get_pull_request`
  - Google Docs: `google_docs_read_document`, `google_docs_create_document`, `google_docs_append_text`
  - Google Sheets: `google_sheets_create_spreadsheet`, `google_sheets_append_rows` (audit tracker)
  - Web: `read_url_content`, `tavily_web_search` (guideline research)
- **Integration Points:**
  - Stage 19 (DisseminationAgent): Pre-submission quality gate
  - Stage 13 (InternalReviewAgent): Compliance checking during internal review
  - Standalone: Independent artifact audits for externally generated outputs
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-artifact-auditor-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `ARTIFACT_AUDIT` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/agent-artifact-auditor-proxy/wiring.md` ⭐
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `LANGSMITH_ARTIFACT_AUDITOR_TIMEOUT_SECONDS` - Request timeout (default: 300)
  - `GITHUB_TOKEN` - For GitHub artifact retrieval
  - `GOOGLE_DOCS_API_KEY`, `GOOGLE_SHEETS_API_KEY` - For Google Workspace integration
- **Location:** `services/agents/agent-artifact-auditor/` (config, subagents), `services/agents/agent-artifact-auditor-proxy/` (proxy)
- **Documentation:** 
  - **Agent Briefing:** `AGENT_ARTIFACT_AUDITOR_BRIEFING.md` ⭐
  - **Wiring Guide:** `docs/agents/agent-artifact-auditor-proxy/wiring.md` ⭐
  - **Agent Definition:** `services/agents/agent-artifact-auditor/AGENTS.md`
  - **Proxy README:** `services/agents/agent-artifact-auditor-proxy/README.md`
- **Task Type:** `ARTIFACT_AUDIT` → `agent-artifact-auditor-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-artifact-auditor-proxy:8000`
- **Validation:** Preflight checks LANGSMITH_API_KEY + LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID; smoke test validates router dispatch + proxy health + deterministic fixture audit (CHECK_ARTIFACT_AUDITOR=1)

**NEW:** `agent-resilience-architecture-advisor` — Resilience Architecture Advisor Agent (Imported from LangSmith, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Advises on resilience architecture patterns, PR resilience review, and architecture documentation. LangSmith multi-agent system with 3 subagents (Architecture_Doc_Builder, PR_Resilience_Reviewer, Resilience_Research_Worker).
- **Deployment:** LangSmith cloud via local proxy adapter ✅ **WIRED**
  - Proxy service: `agent-resilience-architecture-advisor-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `RESILIENCE_ARCHITECTURE` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - **Wiring Guide:** `docs/agents/agent-resilience-architecture-advisor-proxy/wiring.md` ⭐
- **Environment Variables (Required):** `LANGSMITH_API_KEY`, `LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_AGENT_ID`
- **Task Type:** `RESILIENCE_ARCHITECTURE` → `agent-resilience-architecture-advisor-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-resilience-architecture-advisor-proxy:8000`
- **Validation:** Preflight + smoke test (CHECK_ALL_AGENTS=1)

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
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-dissemination-formatter-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `DISSEMINATION_FORMATTING` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/dissemination-formatter/wiring.md` ⭐

**NEW:** `agent-performance-optimizer` — Performance Optimizer Agent (Imported from LangSmith, 2026-02-08) ✅ **PRODUCTION READY**
- **Purpose:** Monitors and optimizes LLM/agent workflow metrics including latency, token costs, error rates. Provides actionable recommendations to reduce API costs by 20-30% and improve performance at enterprise scale.
- **Architecture:** LangSmith multi-agent system with 2 specialized sub-workers (Optimization_Researcher, Cost_Benchmarker)
- **Main Agent Capabilities:**
  - Performance metrics collection & analysis (Google Sheets integration)
  - Bottleneck identification across cost, latency, and error dimensions
  - Alert threshold monitoring (error rate, cost spikes, P99 latency)
  - Historical trend tracking and reporting
  - Cost benchmarking across AI providers (OpenAI, Anthropic, Google, open-source)
  - Automated report generation and archival to Google Docs
  - Supports scheduled (cron) and on-demand analysis
- **Sub-Workers:**
  - `Optimization_Researcher`: Researches LLM optimization strategies, best practices, latency reduction techniques, prompt efficiency, caching approaches
  - `Cost_Benchmarker`: Analyzes provider pricing, recommends cost-optimal model selections, calculates projected savings
- **Analysis Framework:**
  - **Cost Analysis**: Total API costs, cost per run, token usage breakdown, most expensive agents, cost trends
  - **Latency Analysis**: P50/P90/P99 latency, distribution, slowest workflows, correlation with models/tokens
  - **Error Analysis**: Error rates by type, retry patterns, cascading failures
  - **Performance Optimization**: Caching opportunities, batch processing, model tier optimization, prompt efficiency
- **Alert Thresholds:**
  - CRITICAL: Error rate >10%, Cost spike >50% day-over-day, P99 latency >30s
  - WARNING: Error rate >5%, Cost increase >20% week-over-week, Avg latency increase >30%
- **Tools:** Google Sheets (read/write/append/create), Google Docs (create/append/read), Web search (research)
- **Integration:** Cross-cutting monitoring for all agents and workflow stages; independent operation with metrics input
- **Output:** Performance reports (Google Docs), optimization tracking spreadsheet, chat summaries with recommendations
- **Location:** `services/agents/agent-performance-optimizer/` (config, tools, subagents)
- **Documentation:**
  - **Main README:** `services/agents/agent-performance-optimizer/README.md` ⭐ **PRIMARY REFERENCE**
  - **Agent Prompt:** `services/agents/agent-performance-optimizer/AGENTS.md`
  - **Config:** `services/agents/agent-performance-optimizer/config.json`
  - **Tools:** `services/agents/agent-performance-optimizer/tools.json`
  - **Sub-Workers:** `services/agents/agent-performance-optimizer/subagents/*/AGENTS.md`
- **LangSmith Source:** Performance Optimizer custom agent
- **Communication Style:** Data-driven, analytical, actionable recommendations with estimated impact, cost-benefit analysis focus
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-performance-optimizer-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `PERFORMANCE_OPTIMIZATION` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/performance-optimizer/wiring.md` ⭐
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `GOOGLE_SHEETS_API_KEY` - For metrics reading (disabled by default)
  - `GOOGLE_DOCS_API_KEY` - For report generation (disabled by default)
  - `LANGSMITH_PERFORMANCE_OPTIMIZER_TIMEOUT_SECONDS` - Request timeout (default: 300)

**NEW:** `agent-multilingual-literature-processor` — Multilingual Literature Processor Agent (Imported, 2026-02-08) ✅ **WIRED FOR PRODUCTION**
- **Purpose:** Discovers, translates, analyzes, and synthesizes scientific literature across multiple languages. Bridges language barriers in academic research by making non-English scientific literature accessible and actionable for global research teams.
- **Architecture:** LangSmith cloud-hosted agent accessed via local FastAPI proxy
- **Main Agent Capabilities:**
  - Multilingual literature discovery (14+ languages supported)
  - Scientific translation with terminology preservation
  - Cross-language synthesis and comparative analysis
  - Regional database access (CNKI, CiNii, SciELO, HAL, LIVIVO, etc.)
  - Annotated bibliography generation with language labels
  - Citation management and export (BibTeX, RIS)
  - Google Docs report generation
- **Supported Languages:**
  - English, Chinese (Simplified/Traditional), Japanese, Spanish, French, German, Portuguese, Korean, Russian, Arabic, Italian, Dutch, Polish
- **Search Coverage:**
  - **Global**: PubMed, PubMed Central, Semantic Scholar, Google Scholar
  - **Chinese**: CNKI (中国知网), Wanfang Data (万方数据)
  - **Japanese**: CiNii, J-STAGE
  - **Spanish/Portuguese**: SciELO, Redalyc
  - **French**: HAL, Persée
  - **German**: LIVIVO
  - **Korean**: RISS
  - **Russian**: eLibrary.ru
- **Workflow Phases:**
  1. **Discovery**: Multi-language search with query translation
  2. **Translation**: Abstract and full-text translation with quality validation
  3. **Extraction**: Structured data extraction (design, outcomes, statistics)
  4. **Synthesis**: Cross-language integration and regional trend analysis
  5. **Reporting**: Formal reports with annotated bibliographies
- **Output Artifacts:**
  - **Chat Summary**: Key findings by language, synthesis, quality notes
  - **Google Doc Report**: Formal literature review with translations
  - **Structured JSON**: Machine-readable output with metadata
  - **Citation Export**: BibTeX/RIS for reference managers
- **Quality Assurance:**
  - Terminology consistency checking (MeSH multilingual thesaurus)
  - Back-translation validation for critical claims
  - Statistical value preservation
  - Citation integrity verification
- **Tool Dependencies:**
  - `tavily_web_search`, `exa_web_search`: Multi-language literature discovery
  - `read_url_content`: Full-text extraction
  - `google_docs_*`: Report generation
  - `google_sheets_*`: Structured data management
  - `gmail_send_email`: Report distribution
- **Integration Points:**
  - **Stage 2 (Literature Review)**: Enhanced multilingual literature discovery
  - **Evidence Synthesis**: Cross-language evidence integration
  - **Systematic Reviews**: Non-English paper screening and extraction
  - **Standalone**: Independent multilingual literature queries
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-multilingual-literature-processor-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `MULTILINGUAL_LITERATURE_PROCESSING` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Preflight + smoke test hooks ✅
  - **Wiring Guide:** `docs/agents/agent-multilingual-literature-processor-proxy/wiring.md` ⭐
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_TIMEOUT_SECONDS` - Request timeout (default: 300)
  - `TAVILY_API_KEY` - For web search (optional)
  - `EXA_API_KEY` - For academic search (optional)
  - `GOOGLE_DOCS_API_KEY`, `GOOGLE_SHEETS_API_KEY` - For Google Workspace integration (optional)
- **Location:** `services/agents/agent-multilingual-literature-processor/` (config), `services/agents/agent-multilingual-literature-processor-proxy/` (proxy)
- **Documentation:** 
  - **Agent Definition:** `services/agents/agent-multilingual-literature-processor/AGENTS.md`
  - **Configuration:** `services/agents/agent-multilingual-literature-processor/config.json`
  - **Tools:** `services/agents/agent-multilingual-literature-processor/tools.json`
  - **Proxy README:** `services/agents/agent-multilingual-literature-processor-proxy/README.md`
  - **Wiring Guide:** `docs/agents/agent-multilingual-literature-processor-proxy/wiring.md` ⭐
- **Task Type:** `MULTILINGUAL_LITERATURE_PROCESSING` → `agent-multilingual-literature-processor-proxy` ✅ **REGISTERED** in orchestrator ai-router
- **Internal URL:** `http://agent-multilingual-literature-processor-proxy:8000`
- **Validation:** Preflight checks LANGSMITH_API_KEY + LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID; smoke test validates router dispatch + proxy health + deterministic fixture (CHECK_MULTILINGUAL_LITERATURE_PROCESSOR=1)
- **Use Cases:**
  - Global evidence synthesis requiring non-English literature
  - Regional practice comparison across languages
  - Systematic reviews with multilingual inclusion criteria
  - Citation discovery for non-English sources
  - Translation for PRISMA reviews

**NEW:** `agent-journal-guidelines-cache` — Journal Guidelines Cache Agent (Imported from LangSmith, 2026-02-08) ✅ **PRODUCTION READY**
- **Purpose:** Intelligent caching layer for academic journal submission guidelines. Eliminates redundant web searches through persistent Google Sheets cache with automatic staleness detection (30-day threshold), proactive daily refresh, and change tracking with audit trails.
- **Architecture:** LangSmith multi-agent system with 3 specialized sub-workers (Guidelines_Researcher, Changelog_Detector, Guidelines_Comparator)
- **Main Agent Capabilities:**
  - Persistent cache management via Google Sheets (dual-sheet structure: Cache + Changelog)
  - Instant retrieval for cached journals (< 100ms response)
  - Automatic staleness detection and refresh scheduling
  - Journal name normalization and alias matching (e.g., "NEJM" → "New England Journal of Medicine")
  - Batch lookups with parallel processing (multiple journals at once)
  - Side-by-side journal comparison (requirements, costs, timelines)
  - Change detection with severity classification (critical/notable/minor)
  - Daily scheduled refresh of stale entries with audit trail
  - Cache management commands (stats, list, clear, force refresh)
- **Sub-Workers:**
  - `Guidelines_Researcher`: Fetches fresh journal submission guidelines from authoritative sources (author instructions pages, official websites). Returns structured summaries covering manuscript types, formatting requirements, submission process, review process, fees/charges, open access policies, ethical requirements.
  - `Changelog_Detector`: Compares old vs. new guidelines during refreshes to detect and document changes. Classifies changes by severity (critical: requires manuscript changes; notable: important to know; minor: cosmetic). Returns structured changelog with impact summary.
  - `Guidelines_Comparator`: Performs side-by-side comparison of multiple journals. Generates comparison tables across key dimensions (word limits, review timelines, APCs, citation styles, requirements). Provides recommendation notes without choosing a specific journal.
- **Cache Architecture:**
  - **Sheet 1 (Cache)**: journal_name, aliases, last_updated, guidelines_summary, source_urls, status (fresh/stale)
  - **Sheet 2 (Changelog)**: journal_name, change_date, change_summary, severity
  - **Staleness Threshold**: 30 days
  - **Initialization**: Auto-creates spreadsheet if not provided
- **Operational Modes:**
  - **Mode 1 - Single Journal**: Check cache → Return immediately (if fresh) OR Refresh with change detection (if stale) OR Fetch fresh (if missing)
  - **Mode 2 - Batch Lookup**: Process multiple journals in parallel, return cache hits immediately, fetch/refresh missing/stale
  - **Mode 3 - Compare Journals**: Ensure all journals fresh, delegate to comparator, return analysis
  - **Mode 4 - Scheduled Refresh**: Daily cron trigger refreshes all stale entries with change notifications
- **Tools:** Google Sheets (create/read/write/append/clear), Web search, URL content extraction
- **Integration:** Directly supports Dissemination Formatter agent for instant guideline lookup. Can be invoked standalone for cache management or journal comparison.
- **Output:** Journal guidelines (cached or fresh), cache status metadata, changelogs, comparison tables, cache statistics
- **Location:** `services/agents/agent-journal-guidelines-cache/` (config, tools, workers)
- **Documentation:**
  - **Main README:** `services/agents/agent-journal-guidelines-cache/README.md` ⭐ **PRIMARY REFERENCE**
  - **Agent Prompt:** `services/agents/agent-journal-guidelines-cache/AGENTS.md`
  - **Config:** `services/agents/agent-journal-guidelines-cache/config.json`
  - **Tools:** `services/agents/agent-journal-guidelines-cache/tools.json`
  - **Sub-Workers:** `services/agents/agent-journal-guidelines-cache/workers/*/AGENTS.md`
- **LangSmith Source:** Journal Guidelines Cache Agent custom agent
- **Communication Style:** Efficient, responsive, transparent about freshness, proactive refresh management, audit-conscious
- **Deployment:** ✅ **WIRED FOR PRODUCTION** (2026-02-08)
  - Proxy service: `agent-journal-guidelines-cache-proxy/` ✅
  - Docker Compose: Service registered ✅
  - Router: `JOURNAL_GUIDELINES_CACHE` task type ✅
  - Endpoints: Added to AGENT_ENDPOINTS_JSON ✅
  - Validation: Ready for preflight + smoke test hooks ✅
- **Environment Variables (Required):**
  - `LANGSMITH_API_KEY` - LangSmith API authentication
  - `LANGSMITH_JOURNAL_GUIDELINES_CACHE_AGENT_ID` - Agent UUID from LangSmith
- **Environment Variables (Optional):**
  - `GOOGLE_SHEETS_SPREADSHEET_ID` - Pre-existing cache spreadsheet ID (auto-creates if not provided)
  - `LANGSMITH_JOURNAL_GUIDELINES_CACHE_TIMEOUT_SECONDS` - Request timeout (default: 180)
  - `CACHE_STALENESS_DAYS` - Cache staleness threshold (default: 30)
- **Cache Management Commands:**
  - `list_cached_journals` - Show all cached journals with freshness status
  - `cache_stats` - Total, fresh, stale counts, oldest/newest entries
  - `get_guidelines` - Retrieve guidelines for single journal
  - `batch_lookup` - Retrieve guidelines for multiple journals
  - `compare_journals` - Side-by-side comparison table
  - `force_refresh` - Force refresh regardless of staleness
  - `show_changelog` - Display guideline changes (filtered by journal or all)
- **Quality Metrics:**
  - Cache hit rate: Target >80%
  - Response time (cache hits): Target <100ms
  - Daily refresh success rate: Target >95%
  - Stale entries after daily refresh: Target 0

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

### 7.3 Agent Routing Configuration (MANDATORY)

**Status:** ✅ **Enforced as Single Source of Truth** (2026-02-08)

**Environment Variable:** `AGENT_ENDPOINTS_JSON`  
**Format:** JSON object mapping agent names to internal URLs  
**Validation:** Mandatory - preflight hard-fails if misconfigured  
**Documentation:** See [`docs/maintenance/agent-orchestration.md`](docs/maintenance/agent-orchestration.md)

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
  "agent-results-writer": "http://agent-results-writer:8000",
  "agent-discussion-writer": "http://agent-discussion-writer:8000",
  "agent-evidence-synthesis": "http://agent-evidence-synthesis:8000",
  "agent-results-interpretation-proxy": "http://agent-results-interpretation-proxy:8000",
  "agent-clinical-manuscript-proxy": "http://agent-clinical-manuscript-proxy:8000",
  "agent-section-drafter-proxy": "http://agent-section-drafter-proxy:8000",
  "agent-peer-review-simulator-proxy": "http://agent-peer-review-simulator-proxy:8000",
  "agent-bias-detection-proxy": "http://agent-bias-detection-proxy:8000",
  "agent-dissemination-formatter-proxy": "http://agent-dissemination-formatter-proxy:8000",
  "agent-journal-guidelines-cache-proxy": "http://agent-journal-guidelines-cache-proxy:8000",
      "agent-compliance-auditor-proxy": "http://agent-compliance-auditor-proxy:8000",
    "agent-artifact-auditor-proxy": "http://agent-artifact-auditor-proxy:8000",
    "agent-resilience-architecture-advisor-proxy": "http://agent-resilience-architecture-advisor-proxy:8000",
    "agent-clinical-model-fine-tuner-proxy": "http://agent-clinical-model-fine-tuner-proxy:8000",
    "agent-multilingual-literature-processor-proxy": "http://agent-multilingual-literature-processor-proxy:8000",
    "agent-hypothesis-refiner-proxy": "http://agent-hypothesis-refiner-proxy:8000"
  }
```

**Architecture:**
- **Native Agents:** All use port 8000, backend network only
- **Proxy Agents:** LangSmith-hosted agents use `-proxy` suffix in service names
- **Health Standard:** All agents must implement `GET /health` returning `{"status": "ok"}`
- **Mandatory Validation:** All agents in this registry are validated at deployment time
- **No Hardcoded URLs:** Orchestrator routing exclusively uses AGENT_ENDPOINTS_JSON

**Canonical List:** `scripts/lib/agent_endpoints_required.txt` (21 mandatory agents)

**Note:** LangSmith-hosted agents use `-proxy` suffix in their compose service names but are accessed via their logical names (without `-proxy`) in routing.


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

## 13. DEPLOYMENT & VALIDATION

### 13.1 Mandatory Agent Validation (2026-02-08)

**Status:** ✅ **Enforced**

All agents in AGENT_ENDPOINTS_JSON are now **mandatory**. Deployment fails if any agent is:
- Missing from AGENT_ENDPOINTS_JSON
- Container not running
- Health endpoint not responding

**Validation Tools:**
- **Preflight:** `scripts/hetzner-preflight.sh` - Hard-fails on missing/unhealthy agents
- **Smoke Test:** `scripts/stagewise-smoke.sh` - Validates dispatch routing
- **Agent List:** `scripts/lib/agent_endpoints_required.txt` - Canonical source of truth

**Documentation:** [`docs/maintenance/agent-orchestration.md`](docs/maintenance/agent-orchestration.md)

### 13.2 Deployment Checklist

Before deploying to production:

- [ ] All 21 mandatory agents defined in docker-compose.yml
- [ ] AGENT_ENDPOINTS_JSON contains all agent keys
- [ ] `./scripts/hetzner-preflight.sh` passes (exit 0)
- [ ] `CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh` passes
- [ ] No hardcoded agent URLs in orchestrator code
- [ ] All LangSmith proxy agents have required env vars set

### 13.3 Stub Agents (Included but Limited)

These agents are deployed but have limited functionality:
- `agent-stage2-synthesize` - Basic stub (deprecated, use agent-evidence-synthesis)
- `agent-results-writer` - Basic stub (use agent-clinical-section-drafter for clinical)
- `agent-discussion-writer` - Basic stub (use agent-clinical-section-drafter for clinical)

**Note:** Stub agents must still pass health checks and be included in AGENT_ENDPOINTS_JSON.

### 13.4 Future Enhancements

- **Agent Performance Metrics** - Track execution times, success rates, costs
- **A/B Testing** - Model comparison framework
- **Agent Versioning** - Track agent code versions via IMAGE_TAG
- **Circuit Breakers** - Automatic fallback for failing agents

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

**Document Version:** 1.2  
**Last Updated:** 2026-02-08  
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

