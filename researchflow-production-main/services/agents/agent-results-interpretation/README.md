# Results Interpretation Agent

**Version:** 1.0.0  
**Status:** ✅ LangSmith Import Complete | 🚧 Integration Pending  
**Source:** LangSmith Custom Agent  
**Import Date:** 2026-02-08

> **Canonical wiring/deploy reference:**
> [`docs/agents/results-interpretation/wiring.md`](../../../docs/agents/results-interpretation/wiring.md)
>
> For deployment, routing, auth, validation, and common failures, see the
> canonical doc above. This README covers agent capabilities and architecture.

---

## Overview

The **Results Interpretation Agent** is a multi-domain research results interpretation system that provides comprehensive analysis of scientific findings across clinical, social science, behavioral, and survey research domains. It combines rigorous statistical reasoning with domain-aware contextual understanding to produce structured, actionable interpretations.

### Key Capabilities

- **Multi-Domain Expertise**: Clinical trials, observational studies, surveys, behavioral research
- **Structured Analysis**: 4 core sections (Findings, Statistical Assessment, Bias & Limitations, Implications)
- **Worker Delegation**: 4 specialized sub-workers for deep analysis and quality assurance
- **Automated Reporting**: Google Docs integration with structured report generation
- **Quality Scoring**: 3-dimensional scoring (Clarity, Accuracy, Bias) with automatic refinement
- **Confidence Rating**: High/Moderate/Low confidence assessment with rationale

---

## Architecture

### Main Agent: Results Interpretation Agent

**Core Responsibilities:**
1. Data ingestion from multiple sources (chat, Google Sheets, URLs, Google Docs)
2. Study classification (type, domain, data types)
3. Comprehensive interpretation analysis
4. Strategic worker delegation for deep analysis
5. Report assembly and delivery
6. Google Docs documentation

### Sub-Workers

#### 1. Literature_Research_Worker
**Purpose:** Deep literature search and benchmarking

**Capabilities:**
- Searches PubMed, meta-analyses, established norms
- Compares study findings against published benchmarks
- Contextualizes results within broader research landscape

**When to Use:**
- Study claims should be validated against prior research
- Published benchmarks exist for measured metrics
- Study is in well-researched domain

---

#### 2. Methodology_Audit_Worker
**Purpose:** Study design and statistical methods audit

**Capabilities:**
- Evaluates study design appropriateness
- Audits statistical methods
- Validates reporting standards compliance (CONSORT, STROBE, PRISMA)

**When to Use:**
- Clinical or observational studies with reporting standards
- Complex statistical methods requiring expert review
- Healthcare/clinical research requiring rigor assessment

---

#### 3. Section_Draft_Worker
**Purpose:** Polished narrative section generation

**Capabilities:**
- Produces 300-500 word evidence-grounded sections
- Maintains neutral academic tone
- Includes proper citations and evidence references

**Usage:**
- Called once for each report section
- Parallel processing for efficiency
- Feeds into Draft_Refinement_Worker

---

#### 4. Draft_Refinement_Worker
**Purpose:** Quality assurance and section refinement

**Capabilities:**
- Scores sections on 3 dimensions (Clarity, Accuracy, Bias, each 1-10)
- Automatically revises if any score below 8
- Up to 3 iteration cycles
- Incorporates user feedback

**Quality Gates:**
- Minimum score 8/10 on all dimensions
- Final quality scores reported in output

---

## Domain Skills

### Clinical Trials Skill
**Location:** `skills/clinical-trials/SKILL.md`

**Triggered By:** RCT, clinical trial, Phase I-IV, randomized controlled trial

**Provides:**
- Clinical trial methodology guidance
- CONSORT checklist compliance
- Efficacy metrics interpretation (HR, OR, RR, ARR, NNT, NNH)
- Clinical vs. statistical significance assessment
- Regulatory context understanding

---

### Survey Analysis Skill
**Location:** `skills/survey-analysis/SKILL.md`

**Triggered By:** survey, questionnaire, poll

**Provides:**
- Response rate benchmarks by mode
- Sampling methodology evaluation
- Margin of error tables
- Question design critique
- Survey-specific bias identification (non-response, social desirability)
- CHERRIES/CROSS reporting standards

---

## Workflow

### 8-Step Interpretation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: Data Ingestion                                  │
│ Parse from chat, Google Sheets, URLs, or Google Docs    │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Study Classification                            │
│ Identify study type, domain, data types                 │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Analysis                                        │
│ Perform comprehensive interpretation                    │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 4: Worker Delegation (Parallel, Conditional)       │
│ ├─→ Literature_Research_Worker                          │
│ └─→ Methodology_Audit_Worker                            │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 5: Section Drafting (Parallel)                     │
│ ├─→ Section_Draft_Worker (Findings)                     │
│ ├─→ Section_Draft_Worker (Statistical Assessment)       │
│ ├─→ Section_Draft_Worker (Bias & Limitations)           │
│ ├─→ Section_Draft_Worker (Implications)                 │
│ ├─→ Section_Draft_Worker (Literature Context)*          │
│ └─→ Section_Draft_Worker (Methodology Audit)*           │
│     (* if Step 4 workers used)                          │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 6: Refinement (Parallel)                           │
│ └─→ Draft_Refinement_Worker (for each section)          │
│     - Score: Clarity, Accuracy, Bias                    │
│     - Auto-revise if score < 8                          │
│     - Up to 3 iterations                                │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 7: Deliver in Chat                                 │
│ Structured report with quality scores                   │
└──────────────────┬──────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────┐
│ Step 8: Save to Google Docs                             │
│ Create shareable report document                        │
└─────────────────────────────────────────────────────────┘
```

### Performance Characteristics

| Scenario | Processing Time | Workers Used |
|----------|----------------|--------------|
| Simple interpretation (direct data) | 30-60s | Section_Draft, Draft_Refinement |
| Clinical trial (full pipeline) | 120-180s | All 4 workers |
| Survey data with literature context | 90-150s | Literature_Research, Section_Draft, Draft_Refinement |

---

## Input/Output

### Input Methods

1. **Direct Data in Chat**
   ```json
   {
     "results_data": "Raw data, tables, statistics...",
     "study_metadata": {
       "study_type": "RCT",
       "domain": "clinical",
       "data_types": "quantitative"
     }
   }
   ```

2. **Google Sheets**
   ```json
   {
     "spreadsheet_id": "1abc...",
     "range": "Sheet1!A1:Z100"
   }
   ```

3. **URL to Report/Paper**
   ```json
   {
     "url": "https://example.com/research-report.pdf"
   }
   ```

4. **Google Doc**
   ```json
   {
     "document_id": "1abc..."
   }
   ```

### Output Structure

```markdown
## Results Interpretation Report

### Study Overview
- **Study Type**: [type]
- **Domain**: [domain]
- **Data Types**: [quantitative/qualitative/mixed]

### Findings
[300-500 word refined narrative]

### Statistical Assessment
[300-500 word refined narrative]

### Bias & Limitations
[300-500 word refined narrative]

### Implications
[300-500 word refined narrative]

### Literature Context (if applicable)
[300-500 word refined narrative]

### Methodology Audit Summary (if applicable)
[300-500 word refined narrative]

### Quality Scores
| Section | Clarity | Accuracy | Bias |
|---------|---------|----------|------|
| ... | X/10 | X/10 | X/10 |

### Confidence Rating
- **Overall Confidence in Findings**: High / Moderate / Low
- **Rationale**: [explanation]
```

**Google Docs Output:**
- Title: `Results Interpretation — [Topic] — [Date]`
- Shareable link provided in response
- Full structured report with formatting

---

## Integration

### Workflow Stage Alignment

| Stage | Name | Agent Role |
|-------|------|-----------|
| **7** | Results Analysis | Primary: Analyze quantitative/qualitative results |
| **8** | Results Synthesis | Secondary: Interpret synthesized findings |
| **9** | Results Refinement | Validation: Review and refine interpretations |

### Upstream Dependencies
- **Input Sources**: Orchestrator, user uploads, Google Workspace
- **Data Sources**: Stage 7-9 results, `agent-evidence-synthesis` output

### Downstream Consumers
- **Manuscript Agents**: `agent-clinical-manuscript`, `Clinical_Study_Section_Drafter`
- **Evidence Validation**: Validates findings from `agent-evidence-synthesis`
- **User Dashboards**: Google Docs reports accessible to researchers

---

## Configuration

### Agent Configuration
**File:** `config.json`

```json
{
  "name": "Results Interpretation Agent",
  "description": "Multi-domain research results interpretation",
  "visibility_scope": "tenant",
  "triggers_paused": false
}
```

### Tools Configuration
**File:** `tools.json`

Tools used:
- `google_docs_create_document`
- `google_docs_append_text`
- `google_docs_read_document`
- `google_docs_replace_text`
- `google_sheets_get_spreadsheet`
- `google_sheets_read_range`
- `tavily_web_search`
- `read_url_content`

All tools provided by LangSmith Agent Builder MCP server.

---

## Environment Setup

### Required Environment Variables

```bash
# LangSmith API
LANGSMITH_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=researchflow-results-interpretation
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Google Workspace
GOOGLE_DOCS_API_KEY=your_google_docs_api_key
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key

# Tavily Search (for Literature_Research_Worker)
TAVILY_API_KEY=your_tavily_api_key
```

### Development Mode (Optional)

```bash
# Use mock interpretation for testing
USE_MOCK_INTERPRETATION=true
```

---

## Testing

### Unit Tests
```bash
pytest tests/agents/test_results_interpretation.py -v
```

### Integration Tests
```bash
pytest tests/integration/test_results_interpretation.py -v
```

### Test Scenarios

1. **Clinical Trial Results**
   - Input: RCT with N=500, p=0.023, 18% attrition
   - Expected: Significant findings, attrition bias flagged

2. **Survey Data**
   - Input: N=1,200, response rate 12%, 65% support
   - Expected: Non-response bias identified, limited generalizability

3. **Observational Study**
   - Input: Cohort N=10,000, adjusted HR=1.45
   - Expected: Association confirmed, causation not established

---

## Documentation

- **Briefing**: [AGENT_RESULTS_INTERPRETATION_BRIEFING.md](../../AGENT_RESULTS_INTERPRETATION_BRIEFING.md)
- **Integration Guide**: [WORKFLOW_INTEGRATION.md](WORKFLOW_INTEGRATION.md)
- **Agent Inventory**: [AGENT_INVENTORY.md](../../AGENT_INVENTORY.md)
- **Main Agent Prompt**: [AGENTS.md](AGENTS.md)
- **Skills**: `skills/clinical-trials/`, `skills/survey-analysis/`
- **Sub-Workers**: `subagents/`

---

## Development Roadmap

### ✅ Phase 1: Import (Complete)
- [x] Import from LangSmith
- [x] Create directory structure
- [x] Copy agent files and workers
- [x] Documentation creation

### 🚧 Phase 2: Integration (In Progress)
- [ ] Orchestration router configuration
- [ ] API endpoint creation
- [ ] Environment setup
- [ ] Integration testing

### 📋 Phase 3: Containerization (Planned)
- [ ] Dockerfile creation
- [ ] Docker Compose integration
- [ ] Health check endpoints
- [ ] Local deployment option

### 📋 Phase 4: Optimization (Future)
- [ ] Literature search caching
- [ ] Worker delegation optimization
- [ ] Performance benchmarking
- [ ] Parallel processing improvements

---

## Support & Contribution

- **Issues**: GitHub Issues with label `agent:results-interpretation`
- **Documentation**: See files listed above
- **Maintainer**: ResearchFlow AI Team

---

## License

Part of ResearchFlow Production system. See main repository LICENSE.

---

**Last Updated:** 2026-02-08  
**Status:** ✅ Import Complete | 🚧 Integration Pending
