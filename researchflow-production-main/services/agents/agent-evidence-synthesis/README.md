# Evidence Synthesis Agent

**Source:** LangSmith Custom Agent (ID: e22b2945-be8b-4745-9233-5b2651914483)  
**Type:** Biomedical & Clinical Research Evidence Synthesis  
**Task Type:** `EVIDENCE_SYNTHESIS`

## Overview

Expert evidence synthesis agent specializing in biomedical and clinical research. Retrieves evidence from academic and clinical sources, evaluates quality using GRADE methodology, synthesizes findings, and handles conflicting studies with multi-perspective analysis.

## Core Capabilities

1. **Evidence Retrieval** — Systematic gathering from PubMed, Google Scholar, clinical trial registries
2. **Quality Evaluation** — GRADE-style evidence grading (High/Moderate/Low/Very Low)
3. **Evidence Synthesis** — Structured reports with evidence tables and quality assessments
4. **Conflict Resolution** — Multi-perspective analysis of contradictory findings
5. **Report Delivery** — Structured markdown reports with citations and methodology notes

## Architecture

### Main Agent
- **File:** `agent/evidence_synthesis.py`
- **Workflow:** PICO decomposition → retrieval → GRADE evaluation → conflict analysis → synthesis
- **Output:** Structured evidence synthesis report with executive summary, evidence table, and limitations

### Sub-Workers

#### Evidence Retrieval Worker
- **File:** `workers/retrieval_worker.py`
- **Purpose:** Deep evidence retrieval for specific research questions
- **Sources:** PubMed, Google Scholar, ClinicalTrials.gov, WHO, CDC, NICE
- **Tools:** Web search, URL content extraction
- **Output:** Structured evidence chunks with metadata, study type, sample size, findings

#### Conflict Analysis Worker
- **File:** `workers/conflict_worker.py`
- **Purpose:** Analyze conflicting or contradictory evidence
- **Process:** Methodological assessment → heterogeneity analysis → multi-perspective debate → weighted conclusion
- **Output:** Conflict report with neutral presentation + marked interpretive conclusion

## Integration Points

### Input Schema
```json
{
  "research_question": "string (required)",
  "inclusion_criteria": "string[] (optional)",
  "exclusion_criteria": "string[] (optional)",
  "pico": {
    "population": "string (optional)",
    "intervention": "string (optional)",
    "comparator": "string (optional)",
    "outcome": "string (optional)"
  },
  "sources": "string[] (optional, user-provided URLs)",
  "max_papers": "number (optional, default 30)"
}
```

### Output Schema
```json
{
  "executive_summary": "string",
  "overall_certainty": "High | Moderate | Low | Very Low",
  "evidence_table": [
    {
      "source": "string (citation)",
      "study_type": "string",
      "sample_size": "string",
      "key_findings": "string",
      "grade": "High | Moderate | Low | Very Low",
      "relevance": "High | Medium | Low"
    }
  ],
  "synthesis_by_subquestion": "object",
  "conflicting_evidence": "object (if applicable)",
  "limitations": "string[]",
  "methodology_note": "object"
}
```

## API Endpoints

- `POST /agents/run/sync` — Synchronous execution
- `POST /agents/run/stream` — Streaming execution with progress updates
- `GET /health` — Health check
- `GET /health/ready` — Readiness check

## Environment Variables

```bash
# LLM Configuration
AI_BRIDGE_URL=http://orchestrator:3001/api/ai/bridge/inference
OPENAI_API_KEY=<key>  # or other LLM provider

# Search Tools
TAVILY_API_KEY=<key>  # For web search capability

# Google Docs (optional, for report delivery)
GOOGLE_DOCS_API_KEY=<key>
```

## Usage in Workflow

The Evidence Synthesis Agent can be invoked at multiple stages:

1. **Stage 2 (Literature Review)** — Comprehensive evidence synthesis after initial screening
2. **Stage 9 (Synthesis)** — Final thematic synthesis of validated research
3. **Ad-hoc Analysis** — On-demand evidence synthesis for specific research questions

## GRADE Methodology

Evidence quality grading follows standard GRADE approach:

- **High**: Further research very unlikely to change confidence
- **Moderate**: Further research may have important impact
- **Low**: Further research very likely to change the estimate
- **Very Low**: Any estimate is very uncertain

Factors considered:
- Study design (RCTs > cohort > case-control > case series)
- Risk of bias
- Inconsistency across studies
- Indirectness
- Imprecision
- Publication bias

## Notes

- Always dispatches Evidence_Retrieval_Worker separately for each sub-question
- Conflict analysis triggered only when contradictions detected
- Citations always traceable with URLs
- Transparent about limitations and evidence gaps
- Never fabricates evidence or citations
