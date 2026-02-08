# Clinical Manuscript Writer Agent

**Agent Type:** LangSmith Multi-Agent System  
**Source:** Imported from LangSmith on 2026-02-07  
**Status:** ✅ Ready for Integration  
**Version:** 1.0.0

---

## 📋 Overview

The Clinical Manuscript Writer is a sophisticated multi-agent system specializing in drafting clinical research manuscripts in **IMRaD format** (Introduction, Methods, Results, Discussion). It adheres to **CONSORT**, **SPIRIT**, **STROBE**, **PRISMA**, and other evidence-based reporting guidelines.

### Key Capabilities

- **IMRaD Format Manuscript Generation** - Professional clinical writing for peer-reviewed journals
- **Multi-Guideline Compliance** - CONSORT, SPIRIT, STROBE, PRISMA, STARD, CARE, ARRIVE
- **Evidence-Based Writing** - Automated literature search and citation integration
- **Statistical Validation** - Built-in statistical review and accuracy checks
- **PHI Protection** - Mandatory PHI screening before processing any clinical data
- **Quality Assurance Loop** - Automated audit and revision workflow
- **Evidence Traceability** - Full citation tracking with Evidence ID system
- **Google Workspace Integration** - Direct Google Docs/Sheets read/write

---

## 🏗️ Architecture

### Main Agent: Clinical Manuscript Writer

**Role:** Orchestrator and primary manuscript drafter

**Workflow:**
1. Request analysis and section planning
2. PHI pre-scan (mandatory)
3. Data gathering and structuring
4. Literature search (parallel)
5. Section drafting (IMRaD)
6. Automated audit loop (Statistical + Compliance)
7. Self-revision and finalization
8. Google Doc writing
9. Evidence Ledger update

### Sub-Agents (4)

#### 1. Literature Research Agent
- **Purpose:** Medical literature search and evidence synthesis
- **Tools:** Tavily Web Search, Exa Web Search (neural/research paper mode), URL reading
- **Search Strategy:** Multi-query parallel searches across PubMed, ClinicalTrials.gov, Cochrane
- **Output:** Structured literature summaries with citations, relevance scores, evidence gaps

#### 2. Statistical Review Agent
- **Purpose:** Statistical accuracy and consistency validation
- **Checks:** 
  - Internal consistency of all statistics
  - Test appropriateness for data types
  - Text-table-figure concordance
  - Missing elements (effect sizes, CIs, multiple comparison corrections)
- **Output:** Statistical audit report with remediation list

#### 3. CONSORT/SPIRIT Compliance Agent
- **Purpose:** Systematic evaluation against reporting guidelines
- **Supported Guidelines:** CONSORT, SPIRIT, STROBE, PRISMA, STARD, CARE, ARRIVE (+ extensions)
- **Output:** Compliance scorecard with prioritized remediation checklist

#### 4. Data Extraction Agent
- **Purpose:** Raw clinical data parsing, structuring, and table generation
- **Capabilities:**
  - Data profiling (variable classification, dimensions, unit of analysis)
  - Data quality assessment (missing data, outliers, duplicates, integrity checks)
  - Descriptive statistics computation (appropriate to variable type)
  - Table 1 (Baseline Characteristics) generation
  - Adverse Events table generation
  - **PHI screening (mandatory first step)**
- **Input Sources:** Google Sheets, URLs, inline data
- **Output:** Analysis-ready data summaries, publication-ready tables

---

## 🛠️ Tools & Integrations

### Google Workspace Tools
- `google_docs_create_document` - Create new manuscripts
- `google_docs_append_text` - Add sections to existing documents
- `google_docs_read_document` - Read existing content for context
- `google_docs_replace_text` - Revise specific sections
- `google_sheets_get_spreadsheet` - Access clinical data
- `google_sheets_read_range` - Read data ranges
- `google_sheets_create_spreadsheet` - Create Evidence Ledgers
- `google_sheets_write_range` - Write structured data
- `google_sheets_append_rows` - Add evidence entries

### Web Search & Reading Tools
- `tavily_web_search` - General medical literature search
- `exa_web_search` - Neural search with "research paper" category filtering
- `read_url_content` - Extract content from clinical trial registries, PubMed, etc.

### Email Tools
- `gmail_draft_email` - Draft journal cover letters and co-author correspondence

---

## 📖 Usage Patterns

### Pattern 1: Full Manuscript from Clinical Data

**User provides:** Raw clinical trial data (Google Sheet or CSV) + study protocol

**Agent workflow:**
1. Data Extraction Agent → PHI scan, data profiling, Table 1 generation
2. Literature Research Agent → Background evidence + comparable studies (parallel)
3. Main Agent → Draft Introduction
4. Main Agent → Draft Methods (based on protocol)
5. Main Agent → Draft Results (based on data)
6. Statistical Review Agent → Validate Results statistics
7. Main Agent → Draft Discussion
8. Literature Research Agent → Discussion context (parallel)
9. CONSORT Compliance Agent → Full manuscript audit
10. Main Agent → Self-revision based on audit findings
11. Write to Google Doc with version log
12. Update Evidence Ledger

**Output:** Complete manuscript + Evidence Ledger + Compliance scorecard

### Pattern 2: Section-by-Section Drafting

**User provides:** Section request + supporting data/context

**Agent workflow:**
1. Main Agent → Draft requested section
2. Statistical Review Agent (if Results/Methods)
3. CONSORT Compliance Agent (for all sections)
4. Main Agent → Self-revision
5. Append to Google Doc

### Pattern 3: Literature Review for Existing Manuscript

**User provides:** Google Doc with partial manuscript + research questions

**Agent workflow:**
1. Main Agent → Read existing content
2. Literature Research Agent → Multi-query parallel search for all questions
3. Main Agent → Synthesize findings into manuscript context
4. Append citations and evidence to existing doc
5. Update Evidence Ledger

---

## 🔒 PHI Protection

**Critical:** The agent implements mandatory PHI screening before processing any raw data.

### PHI Pre-Scan Process (Automatic)

When user provides Google Sheets, URLs, or inline data:
1. **Data Extraction Agent is delegated first** (never main agent)
2. Agent scans for PHI patterns:
   - Patient names, initials, or identifiers beyond study IDs
   - Dates more specific than year (DOB, admission dates, etc.)
   - Geographic data more specific than state level
   - MRNs, SSNs, or any unique identifiers
   - Phone numbers, email addresses, contact information
3. **If PHI detected:** Agent STOPS, alerts user, lists specific PHI found
4. User must confirm data is de-identified before processing continues

### PHI-Safe Language Guidelines

- Never include PHI in any output, draft, or intermediate step
- Use only aggregated statistics
- Use study IDs (not patient names/MRNs)
- Report dates as year only (or ranges)
- Use state-level (not city/ZIP) geographic data

---

## 📊 Evidence Traceability System

### Evidence ID Assignment

Every claim, statistic, or referenced finding receives an **Evidence ID**:

Format: `[EV-001]`, `[EV-002]`, etc.

### Evidence Ledger Spreadsheet

Maintained in Google Sheets with three sheets:

#### Sheet 1: Evidence Log
| Evidence ID | Source | Finding | Confidence | Section Used | Verified |
|---|---|---|---|---|---|
| EV-001 | Smith et al., 2023 | Primary endpoint met (p=0.003) | High | Results | Yes |
| EV-002 | Trial data, Table 3 | Adverse event rate: 12.4% | Medium | Results | Yes |
| EV-003 | [EV-UNVERIFIED] | Claim about prevalence | Low | Introduction | No |

#### Sheet 2: Data Quality
| Variable | N | Missing (%) | Outliers | Data Integrity Issues | Resolution |
|---|---|---|---|---|---|
| Age | 120 | 2.5% | 3 values > 90 | None | Values confirmed |

#### Sheet 3: Compliance Audit
| Guideline Item | Status | Evidence ID | Notes |
|---|---|---|---|
| CONSORT 2a: Trial design | Addressed | EV-012 | Parallel-group RCT stated |
| CONSORT 6a: Sample size | Partially Addressed | None | Calculation not shown |

### Evidence ID Workflow

1. Agent assigns Evidence ID during drafting
2. Inline citation in manuscript: `"...primary endpoint was met (p=0.003) [EV-001]."`
3. Append to Evidence Ledger via `google_sheets_append_rows`
4. If claim cannot be traced → mark as `[EV-UNVERIFIED]` and flag for user

---

## 📐 Reporting Guideline Compliance

### Supported Guidelines

| Guideline | Study Type | Checklist Items |
|---|---|---|
| **CONSORT** | Randomized Controlled Trials | 25 items + extensions |
| **SPIRIT** | Trial Protocols | 33 items |
| **STROBE** | Observational Studies | 22 items |
| **PRISMA** | Systematic Reviews | 27 items |
| **STARD** | Diagnostic Accuracy Studies | 30 items |
| **CARE** | Case Reports | 13 items |
| **ARRIVE** | Animal Research | 20 items |

### Compliance Audit Process

**CONSORT/SPIRIT Compliance Agent** systematically evaluates every item:

1. **Addressed** - Item fully reported with evidence
2. **Partially Addressed** - Item mentioned but incomplete
3. **Missing** - Item not present

**Output:** 
- Compliance percentage score
- Prioritized remediation list
- Specific suggestions for each missing/partial item

**When to Run:**
- After drafting any section (automated)
- Before final manuscript submission (user-triggered)

---

## 🧪 Statistical Review Workflow

### Automated Checks (Statistical Review Agent)

After drafting Results or Methods sections:

1. **Internal Consistency**
   - Verify all N values sum correctly
   - Check percentages add to 100%
   - Validate degrees of freedom
   - Confirm baseline vs. outcome sample sizes

2. **Test Appropriateness**
   - Continuous data: t-test vs. Mann-Whitney (based on normality)
   - Categorical data: chi-square vs. Fisher's exact (based on cell counts)
   - Paired vs. unpaired tests
   - One-tailed vs. two-tailed tests

3. **Text-Table-Figure Concordance**
   - All statistics in text match tables
   - All statistics in tables match figures
   - Effect directions consistent

4. **Completeness Checks**
   - All p-values reported with exact values (not just "p < 0.05")
   - All effect sizes reported with confidence intervals
   - Multiple comparison corrections documented
   - Missing data handling described

**Output:** Statistical audit report with remediation list

---

## 🗂️ Special Handling: Rare Diseases & Low Sample Sizes

When N < 30 or working with rare disease data:

1. **Flag prominently:** `⚠️ LOW SAMPLE SIZE (N=[X]) — Interpret findings with caution.`
2. **Recommend appropriate methods:**
   - Exact tests instead of asymptotic tests
   - Bayesian approaches for probability statements
   - Confidence intervals over p-values
3. **Note limitation explicitly** in Discussion section
4. **Search for comparable rare disease studies** (Literature Research Agent) to contextualize findings
5. **Suggest visualizations** appropriate for small samples (dot plots, individual data points)

---

## 📝 Section-Specific Guidelines

### Introduction
- Establish clinical problem and significance
- Summarize current evidence (Literature Research Agent)
- State study objective and hypothesis
- End with statement of the study's contribution

### Methods
- Study design, setting, participants, interventions, outcomes, statistical analysis
- Precise enough for replication
- Ethical approval statements and consent procedures
- Trial registration number (if applicable)

### Results
- Present findings aligned with stated objectives
- Primary outcomes → Secondary outcomes → Exploratory analyses
- Exact statistics for all comparisons
- **Do NOT interpret** — only report
- Suggest tables/figures for complex data
- **Always run Statistical Review Agent after drafting**

### Discussion
- Interpret results in context of existing literature
- Compare findings with previous studies (Literature Research Agent)
- Address clinical significance (not just statistical)
- Address all limitations honestly
- Conclude with implications and future research

---

## 🚀 Integration with ResearchFlow

### Workflow Alignment

This agent integrates with the existing ResearchFlow pipeline as a **specialized manuscript generation module**:

```
┌─────────────────────────────────────────────────────────────┐
│         ResearchFlow Stage 2: Evidence Synthesis            │
│  (agent-evidence-synthesis: GRADE evaluation)               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│      Clinical Manuscript Writer (LangSmith Agent)           │
│  • Receives structured evidence from Stage 2                │
│  • Drafts publication-ready manuscript sections             │
│  • Maintains evidence traceability                          │
│  • Generates compliance reports                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│          Output: Google Doc Manuscript + Evidence Ledger    │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Input from ResearchFlow:**
- Structured evidence summaries from `agent-evidence-synthesis`
- PICO-decomposed research questions
- GRADE quality assessments
- Conflict analysis reports

**Output to ResearchFlow:**
- Publication-ready manuscript sections (Google Docs)
- Evidence Ledger (Google Sheets)
- Compliance scorecard
- Version history log

### API Integration Points (Future)

**Potential endpoints for containerization:**
- `POST /api/manuscript/draft` - Draft section or full manuscript
- `POST /api/manuscript/audit` - Run compliance/statistical audit
- `POST /api/manuscript/evidence-ledger` - Generate evidence tracking
- `GET /api/manuscript/status` - Get drafting progress

---

## 🧰 Environment Variables (for Future Containerization)

When containerizing this agent (currently LangSmith-hosted):

```bash
# Required for Literature Search
TAVILY_API_KEY=tvly-your-api-key-here

# Required for Google Workspace Integration
GOOGLE_DOCS_API_KEY=your-google-docs-api-key
GOOGLE_SHEETS_API_KEY=your-google-sheets-api-key
GMAIL_API_KEY=your-gmail-api-key

# Required for Agent Communication (if converting to microservice)
WORKER_SERVICE_TOKEN=<shared-secret-token>
ORCHESTRATOR_URL=http://orchestrator:3000

# Optional: Enhanced Literature Search
EXA_API_KEY=your-exa-api-key-here
```

---

## 📦 Files & Structure

```
agent-clinical-manuscript/
├── README.md                          # This file
├── AGENTS.md                          # Main agent prompt/instructions
├── config.json                        # Agent configuration
├── tools.json                         # Tool definitions and interrupt config
└── subagents/
    ├── Literature_Research_Agent/
    │   ├── AGENTS.md                  # Subagent prompt
    │   └── tools.json                 # Tool configuration
    ├── Statistical_Review_Agent/
    │   ├── AGENTS.md                  # Subagent prompt
    │   └── tools.json                 # Tool configuration
    ├── CONSORT_SPIRIT_Compliance_Agent/
    │   ├── AGENTS.md                  # Subagent prompt
    │   └── tools.json                 # Tool configuration
    └── Data_Extraction_Agent/
        ├── AGENTS.md                  # Subagent prompt
        └── tools.json                 # Tool configuration
```

---

## 🔄 Future Work: Containerization

This agent is currently hosted on **LangSmith** (cloud-based). To fully integrate with the containerized ResearchFlow architecture, consider:

### Option 1: LangSmith API Integration
- Call LangSmith agent via REST API
- Pass structured inputs from `agent-evidence-synthesis`
- Receive outputs via webhook or polling

### Option 2: Migrate to Local Microservice
- Convert LangSmith agent to LangGraph-based Python service
- Follow `agent-evidence-synthesis` architecture pattern
- Deploy as Docker container with FastAPI endpoint
- Integrate with orchestrator's AI Bridge

### Option 3: Hybrid Approach
- Keep main agent on LangSmith for rapid iteration
- Containerize subagents for local execution
- Use LangSmith as orchestration layer

---

## 📚 References

- **CONSORT 2010:** http://www.consort-statement.org/
- **SPIRIT 2013:** https://www.spirit-statement.org/
- **STROBE:** https://www.strobe-statement.org/
- **PRISMA:** http://www.prisma-statement.org/
- **LangSmith Documentation:** https://docs.smith.langchain.com/

---

## 🏷️ Tags

`#clinical-manuscript` `#imrad` `#consort` `#spirit` `#evidence-synthesis` `#langsmith` `#multi-agent` `#manuscript-writing` `#clinical-research` `#phi-protection`

---

**Imported:** 2026-02-07  
**Status:** ✅ Ready for Integration Testing  
**Next Steps:** Add to AGENT_INVENTORY.md, update workflow coordination docs, test with Stage 2 pipeline outputs
