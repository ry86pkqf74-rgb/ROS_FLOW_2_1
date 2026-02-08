# Clinical Study Section Drafter - Integration Guide

**Import Date:** 2026-02-07  
**Source:** LangSmith Custom Agent  
**Status:** ✅ Imported & Integrated  
**Location:** `agents/Clinical_Study_Section_Drafter/`

---

## Executive Summary

The **Clinical Study Section Drafter** is a specialized LangSmith multi-agent system designed to produce publication-ready **Results** and **Discussion** sections for clinical research manuscripts. It automatically adapts to 5 major reporting guidelines (CONSORT, STROBE, STARD, PRISMA, CARE) and maintains rigorous standards for statistical accuracy, evidence traceability, and compliance validation.

This agent complements the existing `agent-clinical-manuscript` (full IMRaD generator) by providing deep expertise in the most challenging and data-intensive manuscript sections.

---

## Architecture

### Main Agent: Clinical Study Section Drafter

**Capabilities:**
- Drafts Results sections (participant flow, outcomes, subgroup analyses, adverse events)
- Drafts Discussion sections (interpretation, literature comparison, strengths/limitations, implications)
- Auto-detects study type and applies appropriate reporting guideline
- Mirrors writing style from few-shot examples
- Never fabricates statistics (strict data fidelity)
- Generates structured audit reports

### Sub-Workers

#### 1. Clinical_Evidence_Researcher
**Purpose:** Web-based literature search and evidence synthesis  
**Capabilities:**
- Searches PubMed, ClinicalTrials.gov, Cochrane Library, major journals
- Extracts comparable Results/Discussion sections from published studies
- Validates statistical claims against existing literature
- Returns structured reports with citations and example passages

**Output Format:**
```markdown
## Relevant Evidence
- [Finding 1 with citation]
- [Finding 2 with citation]

## Comparable Sections
[Example passage 1 from similar study]
[Example passage 2 from similar study]

## Supporting/Contradicting Data
[Statistical findings that corroborate or challenge results]

## Suggested Citations
[Formatted references]
```

#### 2. Reporting_Guideline_Checker
**Purpose:** Compliance validation against reporting guidelines  
**Capabilities:**
- Reviews drafted sections against applicable guideline checklists
- Identifies addressed and missing checklist items
- Provides actionable suggestions for compliance
- Supports 5 major guidelines with 150+ total checklist items

**Supported Guidelines:**
| Guideline | Study Type | Key Items Checked |
|-----------|------------|-------------------|
| **CONSORT** | RCTs | Participant flow, baseline characteristics, effect sizes with CIs, harms |
| **STROBE** | Observational | Descriptive data, unadjusted/adjusted estimates, missing data handling |
| **STARD** | Diagnostic accuracy | Test results cross-tabulation, diagnostic accuracy estimates with CIs |
| **PRISMA** | Systematic reviews | Study selection flow, synthesis results, certainty of evidence (GRADE) |
| **CARE** | Case reports | Timeline, diagnostic assessment, intervention details, outcomes |

**Output Format:**
```markdown
## Compliance Report

### Items Addressed ✅
- Item 13a: Participant flow described
- Item 17a: Primary outcome with effect size and CI

### Items Missing ⚠️
- Item 14a: Recruitment dates not mentioned
- Item 19: Adverse events not reported

### Actionable Suggestions
1. Add recruitment period dates in first paragraph
2. Include adverse events summary or state if none occurred
```

---

## Integration within ResearchFlow Workflow

### 1. Pipeline Position

```
Stage 2: Literature Search & Screening
         ↓
Stage 3-6: Evidence Extraction & Synthesis
         ↓
       [agent-evidence-synthesis]
         ↓
       [Clinical_Study_Section_Drafter] ← YOU ARE HERE
         ↓
       [agent-clinical-manuscript]
         ↓
Stage 9-10: Review & Publication
```

### 2. Input Sources

The agent receives structured inputs from:

| Input | Source | Format |
|-------|--------|--------|
| `section_type` | User request | "Results" or "Discussion" |
| `study_summary` | Project metadata | Study design, population, intervention, outcomes |
| `results_data` | Statistical analysis outputs | Endpoints, p-values, CIs, effect sizes |
| `evidence_chunks` | `agent-evidence-synthesis` | RAG-retrieved evidence with chunk IDs |
| `key_hypotheses` | Research question definition | Testable hypotheses |
| `few_shot_examples` | Template library or user-provided | 2-3 example passages |

### 3. Output Consumers

The agent's outputs feed into:

| Consumer | Purpose | Interface |
|----------|---------|-----------|
| `agent-clinical-manuscript` | Full manuscript assembly | Receives polished section drafts |
| `Reporting_Guideline_Checker` | Compliance validation | Receives draft text for audit |
| Human reviewers | Final review & editing | Google Docs or markdown export |
| Version control | Iterative refinement | Git-tracked manuscript files |

### 4. Workflow Integration Points

#### Point A: Direct Invocation (Standalone)
```bash
# User provides all inputs manually
POST /agents/run/sync
{
  "section_type": "Results",
  "study_summary": "...",
  "results_data": {...},
  "evidence_chunks": [...],
  "key_hypotheses": [...],
  "few_shot_examples": [...]
}
```

#### Point B: Orchestrated Invocation (Automated)
```python
# Orchestrator calls agent as part of Stage 7-8 (Writing)
from agents.Clinical_Study_Section_Drafter import draft_section

context = workflow_engine.get_context(stage=8)
draft = await draft_section(
    section_type="Results",
    study_data=context.study_metadata,
    results=context.statistical_outputs,
    evidence=context.evidence_synthesis,
    style_examples=context.template_library
)
```

#### Point C: Evidence Synthesis → Section Drafter Pipeline
```python
# agent-evidence-synthesis feeds directly into section drafter
synthesis_report = await evidence_synthesis_agent.synthesize(
    research_question="...",
    pico_elements={...}
)

results_draft = await clinical_section_drafter.draft(
    section_type="Results",
    evidence_chunks=synthesis_report.evidence_chunks,
    study_summary=synthesis_report.study_context,
    results_data=synthesis_report.grade_evaluations
)
```

---

## API Reference

### Main Agent Endpoint

**POST** `/agents/run/sync`

**Request Body:**
```json
{
  "section_type": "Results",
  "study_summary": "A randomized, double-blind, placebo-controlled trial of Drug X in 300 patients with Type 2 Diabetes. Primary outcome: HbA1c reduction at 12 weeks.",
  "results_data": {
    "primary_outcome": {
      "metric": "HbA1c reduction",
      "treatment_arm": {
        "mean": -1.2,
        "std": 0.4,
        "n": 150
      },
      "control_arm": {
        "mean": -0.3,
        "std": 0.5,
        "n": 150
      },
      "effect_size": -0.9,
      "ci_95": [-1.1, -0.7],
      "p_value": 0.001
    },
    "secondary_outcomes": [...]
  },
  "evidence_chunks": [
    {
      "chunk_id": "chunk_123",
      "text": "Previous studies have shown...",
      "source": "Smith et al., JAMA 2023"
    }
  ],
  "key_hypotheses": [
    "Drug X reduces HbA1c more than placebo in T2DM patients"
  ],
  "few_shot_examples": [
    "In the DCCT trial, mean HbA1c reduction was -1.5% (95% CI: -1.8 to -1.2, p<0.001) in the intensive therapy group compared to -0.6% in the standard therapy group..."
  ]
}
```

**Response:**
```json
{
  "section_draft": "## Results\n\n### Participant Characteristics\nOf 320 participants screened, 300 were randomized (150 to Drug X, 150 to placebo)...",
  "guideline_compliance_report": {
    "guideline": "CONSORT",
    "items_addressed": ["13a", "15", "17a"],
    "items_missing": ["14a", "19"],
    "suggestions": [...]
  },
  "evidence_citations": [
    {"ref_id": "REF1", "citation": "Smith et al., JAMA 2023"}
  ],
  "audit_log": {
    "worker_calls": [
      {
        "worker": "Clinical_Evidence_Researcher",
        "query": "HbA1c reduction trials Type 2 Diabetes",
        "results_count": 12
      }
    ]
  }
}
```

### Sub-Worker Endpoints

#### Clinical_Evidence_Researcher

**POST** `/workers/clinical-evidence-researcher/run`

**Request:**
```json
{
  "study_type": "RCT",
  "therapeutic_area": "Endocrinology/Diabetes",
  "key_hypotheses": ["Drug X reduces HbA1c..."],
  "search_queries": ["HbA1c reduction interventions Type 2 Diabetes"]
}
```

**Response:**
```json
{
  "relevant_evidence": [...],
  "comparable_sections": [...],
  "supporting_data": [...],
  "suggested_citations": [...]
}
```

#### Reporting_Guideline_Checker

**POST** `/workers/reporting-guideline-checker/run`

**Request:**
```json
{
  "draft_text": "## Results\n\n...",
  "section_type": "Results",
  "study_type": "RCT",
  "guideline_override": null
}
```

**Response:**
```json
{
  "guideline": "CONSORT",
  "items_addressed": [...],
  "items_missing": [...],
  "suggestions": [...]
}
```

---

## Configuration

### Environment Variables

**LangSmith Integration:**
```bash
LANGCHAIN_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ResearchFlow-Production
LANGSMITH_TRACING=true
```

**External API Keys (Required for sub-workers):**
```bash
# Clinical_Evidence_Researcher
TAVILY_API_KEY=tvly-...
EXA_API_KEY=exa_...

# Google Docs integration (optional)
GOOGLE_CLOUD_PROJECT_ID=...
GOOGLE_DOCS_API_KEY=...
GMAIL_API_KEY=...
```

### Agent Configuration

**File:** `agents/Clinical_Study_Section_Drafter/config.json`

```json
{
  "name": "Clinical Study Section Drafter",
  "description": "Drafts Results or Discussion sections...",
  "visibility_scope": "tenant",
  "triggers_paused": false
}
```

### Tool Configuration

**File:** `agents/Clinical_Study_Section_Drafter/tools.json`

Available tools:
- `tavily_web_search` - Medical literature search
- `read_url_content` - Extract content from URLs
- `exa_web_search` - Semantic search (PubMed, clinical registries)
- `google_docs_create_document` - Export to Google Docs
- `google_docs_append_text` - Update existing documents
- `google_docs_read_document` - Read draft documents
- `gmail_draft_email` - Prepare notifications
- `gmail_send_email` - Send drafts to collaborators

---

## Usage Examples

### Example 1: Draft Results Section for RCT

```python
from agents.Clinical_Study_Section_Drafter import draft_section

# Prepare inputs
rct_data = {
    'section_type': 'Results',
    'study_summary': 'Double-blind RCT of antihypertensive Drug Y in 400 patients with Stage 2 hypertension',
    'results_data': {
        'primary_outcome': {
            'metric': 'Mean SBP reduction at 8 weeks',
            'treatment': {'mean': -18.5, 'std': 6.2, 'n': 200},
            'control': {'mean': -6.3, 'std': 5.8, 'n': 200},
            'effect_size': -12.2,
            'ci_95': [-14.1, -10.3],
            'p_value': '<0.001'
        }
    },
    'evidence_chunks': [...],  # From agent-evidence-synthesis
    'key_hypotheses': ['Drug Y reduces SBP more than placebo'],
    'few_shot_examples': [
        'In the SPRINT trial, mean SBP reduction was...'
    ]
}

# Draft section
draft = await draft_section(**rct_data)

print(draft['section_draft'])
print(draft['guideline_compliance_report'])
```

### Example 2: Draft Discussion Section for Observational Study

```python
observational_data = {
    'section_type': 'Discussion',
    'study_summary': 'Retrospective cohort study of 5000 patients examining association between statin use and cardiovascular events',
    'results_data': {
        'primary_finding': {
            'metric': 'Adjusted hazard ratio for CV events',
            'hr': 0.72,
            'ci_95': [0.65, 0.80],
            'p_value': '<0.001'
        }
    },
    'evidence_chunks': [...],
    'key_hypotheses': ['Statin use is associated with reduced CV events'],
    'few_shot_examples': [...]
}

draft = await draft_section(**observational_data)
```

### Example 3: Compliance Check Only

```python
# Draft already written, just need compliance check
from agents.Clinical_Study_Section_Drafter.subagents.Reporting_Guideline_Checker import check_compliance

audit = await check_compliance(
    draft_text=existing_results_section,
    section_type='Results',
    study_type='RCT'
)

print(f"Guideline: {audit['guideline']}")
print(f"Items addressed: {audit['items_addressed']}")
print(f"Items missing: {audit['items_missing']}")
print(f"Suggestions: {audit['suggestions']}")
```

---

## Integration with Existing Agents

### 1. Evidence Synthesis → Section Drafter Pipeline

```python
# Stage 6: Evidence Synthesis
synthesis = await agent_evidence_synthesis.synthesize(
    research_question="What is the efficacy of Drug X in Type 2 Diabetes?",
    pico={
        'population': 'Adults with Type 2 Diabetes',
        'intervention': 'Drug X',
        'comparator': 'Placebo',
        'outcome': 'HbA1c reduction'
    }
)

# Stage 8: Section Drafting
results_draft = await clinical_section_drafter.draft(
    section_type='Results',
    study_summary=synthesis.study_context,
    results_data=synthesis.statistical_summary,
    evidence_chunks=synthesis.evidence_chunks,  # Already formatted
    key_hypotheses=synthesis.research_questions,
    few_shot_examples=template_library.get_examples('results', 'rct')
)

# Stage 9: Full Manuscript Assembly
manuscript = await agent_clinical_manuscript.assemble(
    results_section=results_draft['section_draft'],
    evidence_ledger=synthesis.evidence_log
)
```

### 2. Section Drafter → Clinical Manuscript Writer

```python
# Use Section Drafter for specialized Results/Discussion
specialized_sections = {}
for section_type in ['Results', 'Discussion']:
    draft = await clinical_section_drafter.draft(
        section_type=section_type,
        study_summary=study_metadata,
        results_data=statistical_outputs,
        evidence_chunks=evidence_database,
        key_hypotheses=hypotheses,
        few_shot_examples=examples[section_type]
    )
    specialized_sections[section_type.lower()] = draft['section_draft']

# Use Clinical Manuscript Writer for full IMRaD assembly
manuscript = await agent_clinical_manuscript.generate(
    study_id=study_id,
    custom_sections=specialized_sections  # Inject specialized sections
)
```

### 3. Literature Triage → Evidence Researcher → Section Drafter

```python
# Stage 2: Literature Triage
triage_report = await agent_lit_triage.prioritize(
    query="Type 2 Diabetes HbA1c interventions",
    filters={'study_type': 'RCT', 'recency': '5y'}
)

tier1_papers = triage_report.get_tier(1)  # Must Read papers

# Stage 5-6: Evidence Research
evidence_search = await clinical_evidence_researcher.search(
    study_type='RCT',
    therapeutic_area='Endocrinology',
    key_hypotheses=['Drug X reduces HbA1c'],
    search_queries=[f"title:{paper.title}" for paper in tier1_papers]
)

# Stage 8: Section Drafting
discussion_draft = await clinical_section_drafter.draft(
    section_type='Discussion',
    evidence_chunks=evidence_search.relevant_evidence,
    few_shot_examples=evidence_search.comparable_sections,
    ...
)
```

---

## Quality Assurance

### Built-in Quality Controls

1. **Statistical Fidelity**
   - Never fabricates or rounds statistics
   - Exact values from `results_data` preserved
   - Placeholders for missing data ([TBD], [Not Reported])

2. **Evidence Traceability**
   - Every claim linked to evidence chunk ID or citation
   - Audit log of all worker calls
   - Suggested citations formatted consistently

3. **Guideline Compliance**
   - Automatic checklist validation
   - Structured compliance reports
   - Actionable suggestions for missing items

4. **Style Consistency**
   - Few-shot style matching
   - Formal clinical writing tone
   - Hedging language (e.g., "suggests", "may indicate")

### Manual Review Checkpoints

After agent drafting, human reviewers should verify:

- [ ] All statistics match source data exactly
- [ ] Guideline compliance report reviewed and missing items addressed
- [ ] Citations are correctly formatted and complete
- [ ] Figures and tables referenced appropriately
- [ ] PHI/PII has been redacted (if applicable)
- [ ] Tone and style match journal requirements

---

## Deployment

### Current Status: LangSmith-Hosted

The agent runs on LangSmith infrastructure. Access via:

```bash
# LangSmith API endpoint
curl -X POST https://api.smith.langchain.com/agents/run/sync \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json" \
  -d @request.json
```

### Future: Containerization (Planned)

**Roadmap Item:** Package agent as Docker container for local deployment

```dockerfile
# Planned: Dockerfile.clinical-section-drafter
FROM python:3.11-slim

WORKDIR /app

COPY agents/Clinical_Study_Section_Drafter/ .
RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose integration:**
```yaml
# Planned: docker-compose.yml addition
services:
  agent-clinical-section-drafter:
    build:
      context: .
      dockerfile: agents/Clinical_Study_Section_Drafter/Dockerfile
    ports:
      - "8016:8000"
    environment:
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - EXA_API_KEY=${EXA_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Troubleshooting

### Common Issues

**Issue 1: Missing Required Inputs**
```
Error: "Missing required field: results_data"

Solution: Ensure all 6 required inputs are provided:
- section_type
- study_summary
- results_data
- evidence_chunks
- key_hypotheses
- few_shot_examples
```

**Issue 2: Guideline Mismatch**
```
Warning: "Study type 'RCT' but guideline 'STROBE' specified"

Solution: Let the agent auto-detect guideline, or verify study_type is correct
```

**Issue 3: Worker Call Failures**
```
Error: "Clinical_Evidence_Researcher worker failed: API rate limit"

Solution: Check TAVILY_API_KEY and EXA_API_KEY are valid and have quota
```

**Issue 4: Statistical Data Format Errors**
```
Error: "Cannot parse results_data: missing 'ci_95' field"

Solution: Ensure results_data follows expected schema:
{
  "metric": str,
  "treatment": {"mean": float, "std": float, "n": int},
  "control": {...},
  "effect_size": float,
  "ci_95": [lower, upper],
  "p_value": float | str
}
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

draft = await draft_section(..., debug=True)
# Logs will show:
# - Worker call details
# - Evidence search queries
# - Guideline checklist evaluation
# - Style matching analysis
```

---

## Changelog

### Version 1.0 (2026-02-07) - Initial Import

- ✅ Agent imported from LangSmith
- ✅ Integrated into ResearchFlow agent inventory
- ✅ Documentation created
- ✅ Workflow integration points defined
- 🔄 Containerization planned
- 🔄 FastAPI wrapper planned (for /health, /agents/run/sync compatibility)

---

## Related Documentation

- [AGENT_INVENTORY.md](./AGENT_INVENTORY.md) - Complete agent directory
- [CLINICAL_MANUSCRIPT_INTEGRATION_GUIDE.md](./CLINICAL_MANUSCRIPT_INTEGRATION_GUIDE.md) - Full IMRaD manuscript agent
- [EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md](./EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md) - Evidence synthesis agent
- [LIT_TRIAGE_DEPLOYMENT_SUMMARY.md](./LIT_TRIAGE_DEPLOYMENT_SUMMARY.md) - Literature triage agent
- [agents/Clinical_Study_Section_Drafter/AGENTS.md](./agents/Clinical_Study_Section_Drafter/AGENTS.md) - Agent prompt and instructions

---

## Support

**Questions or issues with the Clinical Study Section Drafter?**

1. Check [Troubleshooting](#troubleshooting) section
2. Review agent logs in LangSmith dashboard
3. Consult [AGENTS.md](./agents/Clinical_Study_Section_Drafter/AGENTS.md) for prompt engineering guidance
4. File issue in ResearchFlow repository with:
   - Request payload (redacted of PHI)
   - Error message
   - Agent execution logs
   - Expected vs. actual output

---

**Document Status:** ✅ Complete  
**Last Updated:** 2026-02-07  
**Maintained By:** ResearchFlow Engineering Team
