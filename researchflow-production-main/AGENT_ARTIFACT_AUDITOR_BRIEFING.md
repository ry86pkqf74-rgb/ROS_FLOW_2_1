# 📋 ARTIFACT AUDITOR AGENT - MISSION BRIEFING

**Agent ID:** agent-artifact-auditor  
**Type:** LangSmith Multi-Agent System  
**Domain:** Research Artifact Compliance & Quality Assurance  
**Source:** LangSmith Custom Agent (Imported 2026-02-08)  
**Status:** ✅ Production Ready

---

## Executive Summary

The **Artifact Auditor Agent** is a specialized compliance auditing system that reviews dissemination artifacts (manuscripts, reports, formatted research outputs) against established reporting standards such as CONSORT, PRISMA, STROBE, and other guidelines. It ensures quality, consistency, and equitable reporting across all artifacts, and tracks compliance trends over time.

### Core Capabilities

- **Multi-Standard Auditing**: Compliance checking across major research reporting standards
- **Artifact Source Flexibility**: Supports GitHub, Google Docs, URLs, and direct text input
- **Item-by-Item Auditing**: Deep compliance checks against official checklists
- **Severity Classification**: CRITICAL/MAJOR/MINOR issue categorization with actionable recommendations
- **Equity & Inclusivity Flags**: Automated detection of bias and reporting gaps
- **Formal Report Generation**: Automated creation of shareable Google Docs audit reports
- **Audit Logging**: Persistent tracking for cross-artifact trend analysis
- **Trend Analysis**: Pattern detection across multiple audits to identify systematic gaps

---

## Architecture

### Main Agent: Artifact Auditor

**Primary Responsibilities:**
- Artifact ingestion from multiple sources (GitHub, Google Docs, URLs, direct input)
- Reporting standard identification and selection
- Workflow coordination across specialized sub-workers
- Audit result aggregation and presentation
- Report generation and artifact management
- Cross-artifact trend tracking

### Sub-Workers (LangSmith Cloud)

#### 1. Guideline_Researcher
**Purpose:** Retrieves and structures the latest official checklist for any reporting standard  
**Trigger:** **Always** called first before auditing  
**Output:** Structured, validated checklist with item numbers, descriptions, and required/recommended status  
**Key Features:**
- Authoritative checklist retrieval (latest versions)
- Structured format for audit consumption
- Version and extension support (e.g., CONSORT-PRO, PRISMA 2020)

#### 2. Compliance_Auditor
**Purpose:** Performs deep item-by-item audit of an artifact against a checklist  
**Trigger:** Called **once per artifact** for each audit request  
**Input:** Full artifact content + structured checklist from Guideline_Researcher  
**Output:** Detailed compliance findings with severity ratings  
**Key Features:**
- Line-by-line artifact review
- Evidence-based compliance assessment
- Severity classification (CRITICAL/MAJOR/MINOR)
- Actionable recommendations
- Equity and inclusivity gap detection

#### 3. Cross_Artifact_Tracker
**Purpose:** Analyzes audit findings across multiple past audits for trends and recurring gaps  
**Trigger:** User requests trend analysis, patterns, or compliance summary across artifacts  
**Output:** Trend analysis report with recurring issues and improvement recommendations  
**Key Features:**
- Multi-audit comparison
- Pattern detection (recurring gaps)
- Compliance score trends over time
- Team/project-level quality insights

---

## Supported Reporting Standards

### 1. CONSORT (Consolidated Standards of Reporting Trials)
**Scope:** Randomized controlled trials (RCTs)  
**Checklist Items:** 25 core items + extensions (e.g., CONSORT-PRO for patient-reported outcomes)  
**Key Requirements:**
- Trial design (parallel, crossover, cluster)
- Sample size calculation
- Randomization method
- Blinding procedures
- Primary and secondary outcomes
- Flow diagram (participant flow)
- Baseline characteristics table
- Statistical methods
- Results for primary/secondary outcomes
- Harms/adverse events

### 2. PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses)
**Scope:** Systematic reviews and meta-analyses  
**Checklist Items:** 27 items (PRISMA 2020)  
**Key Requirements:**
- Structured abstract
- Search strategy (all databases)
- Study selection process (PRISMA flow diagram)
- Data extraction process
- Risk of bias assessment
- Synthesis methods (meta-analysis, narrative)
- Publication bias assessment
- Certainty of evidence (GRADE)

### 3. STROBE (Strengthening the Reporting of Observational Studies in Epidemiology)
**Scope:** Observational studies (cohort, case-control, cross-sectional)  
**Checklist Items:** 22 items  
**Key Requirements:**
- Study design specification
- Setting and participants
- Variables (exposure, outcome, confounders)
- Data sources and measurement
- Bias management
- Statistical methods (confounding adjustments)
- Results (participant flow, descriptive, outcome, main results)
- Limitations

### 4. SPIRIT (Standard Protocol Items: Recommendations for Interventional Trials)
**Scope:** Clinical trial protocols  
**Checklist Items:** 33 items  
**Key Requirements:**
- Protocol version and amendments
- Eligibility criteria
- Intervention description (TIDieR)
- Outcomes (primary, secondary, timing)
- Sample size and power calculation
- Randomization and allocation
- Monitoring and safety plans

### 5. CARE (Case Reports)
**Scope:** Case reports  
**Checklist Items:** 13 items  
**Key Requirements:**
- Patient consent and anonymization
- Timeline of events
- Diagnostic assessments
- Therapeutic interventions
- Follow-up and outcomes
- Patient perspective (if available)

### 6. ARRIVE (Animal Research: Reporting of In Vivo Experiments)
**Scope:** Animal research studies  
**Checklist Items:** 20 items (ARRIVE 2.0)  
**Key Requirements:**
- Study design (sample size, randomization, blinding)
- Animal characteristics (species, strain, sex, age)
- Housing and husbandry
- Experimental procedures
- Humane endpoints
- Statistical methods

### 7. TIDieR (Template for Intervention Description and Replication)
**Scope:** Intervention descriptions (often used with CONSORT/SPIRIT)  
**Checklist Items:** 12 items  
**Key Requirements:**
- Intervention name
- Rationale (theory, goals)
- Materials (physical or informational)
- Procedures (dose, schedule, tailoring)
- Provider characteristics
- Delivery mode
- Location and timing
- Fidelity assessment

### 8. CHEERS (Consolidated Health Economic Evaluation Reporting Standards)
**Scope:** Health economic evaluations  
**Checklist Items:** 24 items  
**Key Requirements:**
- Study perspective (healthcare system, societal)
- Comparators
- Time horizon
- Discount rate
- Resource use measurement
- Cost valuation
- Health outcomes (QALYs, DALYs)
- Incremental analysis (ICER)
- Uncertainty analysis (sensitivity, probabilistic)

### 9. MOOSE (Meta-analysis Of Observational Studies in Epidemiology)
**Scope:** Meta-analyses of observational studies  
**Checklist Items:** 35 items  
**Key Requirements:**
- Search strategy for observational studies
- Study selection (inclusion/exclusion)
- Data abstraction and quality assessment
- Quantitative data synthesis
- Heterogeneity assessment
- Sensitivity analysis
- Publication bias

---

## Audit Workflow

### Step 1: Parse the Artifact

**Supported Sources:**
- **GitHub**: `github_get_file`, `github_list_directory`, `github_get_pull_request`
- **Google Docs**: `google_docs_read_document` (requires document ID)
- **URLs**: `read_url_content` (fetch from web)
- **Direct Input**: User-pasted text

**Chunking Strategy:**
For large artifacts, chunk by logical sections:
- Title and Abstract
- Introduction
- Methods
- Results
- Discussion
- References and Appendices

### Step 2: Determine the Applicable Standard

**Automatic Inference:**
Based on artifact type and content:
- RCT → CONSORT
- Systematic review → PRISMA
- Observational study → STROBE
- Trial protocol → SPIRIT
- Case report → CARE
- Animal study → ARRIVE
- Intervention description → TIDieR
- Health economics → CHEERS
- Meta-analysis of observational → MOOSE

**User Override:**
If user specifies a guideline (including extensions like CONSORT-PRO, PRISMA 2020, STROBE-Vet), use that.

### Step 3: Retrieve the Guideline Checklist

**Delegate to Guideline_Researcher worker:**
- Input: Standard name (and version/extension if applicable)
- Output: Structured, validated checklist

**Important:** Always run this step before auditing. Do NOT rely on the Compliance_Auditor to look up its own checklist.

### Step 4: Audit via Compliance_Auditor Worker

**Delegate to Compliance_Auditor worker:**
- Input: Full artifact content (or chunked sections) + structured checklist from Guideline_Researcher + custom guidelines (optional)
- Output: Item-by-item compliance findings with severity ratings

**Important:** Call the Compliance_Auditor worker **once per artifact**.

### Step 5: Generate and Deliver the Report

**Dual Delivery:**

#### A. Chat Summary
Present structured summary in chat:
```
## Audit Report: [Artifact Name]
**Standard**: [CONSORT/PRISMA/STROBE/etc.]
**Compliance Score**: X/Y items (Z%)

### Critical Issues (Must Fix)
- [Item #] [Issue]: [Brief description and recommendation]

### Major Issues (Should Fix)
- [Item #] [Issue]: [Brief description and recommendation]

### Minor Issues (Consider)
- [Item #] [Issue]: [Brief description]

### Equity & Inclusivity Flags
- [Any equity-related findings]
```

#### B. Google Docs Report
Create formal audit report using `google_docs_create_document` and `google_docs_append_text`:
- Executive Summary
- Compliance Score
- Detailed Findings (by checklist item)
- Recommendations
- Audit Trail Metadata

**Return URL to user.**

### Step 6: Log Audit to Tracker

**Persistent Audit Log:**
Use `google_sheets_append_rows` to log audit metadata:
- Audit timestamp
- Artifact name/ID
- Reporting standard
- Compliance score
- Critical/Major/Minor issue counts
- Audit report URL
- Auditor (agent) version

**Purpose:** Enables cross-artifact trend analysis via Cross_Artifact_Tracker worker.

---

## Multi-Artifact Trend Analysis

**When to Use:**
User requests patterns, trends, or compliance summary across multiple artifacts.

**Workflow:**
1. User provides audit log spreadsheet ID or specific audit report URLs
2. Delegate to **Cross_Artifact_Tracker** worker
3. Worker analyzes:
   - Compliance score trends over time
   - Recurring issues (which checklist items consistently fail)
   - Team/project-level quality insights
   - Improvement recommendations

**Output:**
Trend analysis report with:
- Overall compliance trend chart (conceptual)
- Top recurring gaps (by frequency)
- Recommendations for systematic improvements

---

## Input Schema (Orchestrator Contract)

```json
{
  "task_type": "ARTIFACT_AUDIT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "artifact_source": "github | google_docs | url | direct",
    "artifact_location": "repo/path | doc_id | url",
    "reporting_standard": "CONSORT | PRISMA | STROBE | ...",
    "standard_version": "optional version/extension",
    "custom_guidelines": "optional additional guidelines",
    "github_repository": "owner/repo",
    "github_file_path": "path/to/artifact.md",
    "google_doc_id": "document_id",
    "artifact_content": "direct text input"
  }
}
```

---

## Output Schema (Orchestrator Contract)

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "audit_summary": {
      "artifact_name": "string",
      "standard": "string",
      "compliance_score": "X/Y items (Z%)"
    },
    "compliance_score": "X/Y items (Z%)",
    "critical_issues": [
      {
        "item_number": "string",
        "description": "string",
        "recommendation": "string"
      }
    ],
    "major_issues": [...],
    "minor_issues": [...],
    "equity_flags": [
      {
        "issue": "string",
        "recommendation": "string"
      }
    ],
    "audit_report_url": "string (Google Docs URL)",
    "audit_log_entry": {
      "timestamp": "ISO 8601",
      "artifact_name": "string",
      "standard": "string",
      "compliance_score": "string",
      "critical_count": 0,
      "major_count": 0,
      "minor_count": 0
    },
    "langsmith_run_id": "string"
  }
}
```

---

## Integration Points

### Orchestrator
- **Task Type:** `ARTIFACT_AUDIT`
- **Agent Proxy:** `agent-artifact-auditor-proxy`
- **Endpoint:** `POST /agents/run/sync` or `POST /agents/run/stream`

### Docker Compose
```yaml
agent-artifact-auditor-proxy:
  build:
    context: .
    dockerfile: services/agents/agent-artifact-auditor-proxy/Dockerfile
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY_ARTIFACT_AUDITOR}
    - LANGSMITH_AGENT_ID=${LANGSMITH_AGENT_ID_ARTIFACT_AUDITOR}
  ports:
    - "8019:8000"
```

### Environment Variables
- `LANGSMITH_API_KEY_ARTIFACT_AUDITOR`: LangSmith API key
- `LANGSMITH_AGENT_ID_ARTIFACT_AUDITOR`: LangSmith assistant ID for Artifact Auditor

---

## Use Cases

### 1. Pre-Submission Quality Gate
**Scenario:** Before submitting a manuscript to a journal, audit for compliance with the target journal's required reporting standard.  
**Workflow:** GitHub PR → Artifact Audit → Fix issues → Re-audit → Submit

### 2. Cross-Team Compliance Monitoring
**Scenario:** Track compliance trends across multiple manuscripts from different teams.  
**Workflow:** Periodic audits → Log to tracker spreadsheet → Trend analysis → Identify systematic gaps → Training/guidance

### 3. Journal Submission Preparation
**Scenario:** Journal requires CONSORT checklist submission alongside manuscript.  
**Workflow:** Audit manuscript → Generate Google Docs report with checklist completion status → Submit report with manuscript

### 4. Equity & Inclusivity Review
**Scenario:** Ensure fair representation in study populations and reporting.  
**Workflow:** Artifact audit → Review equity flags → Revise manuscript to address gaps → Re-audit

---

## Performance Characteristics

- **Audit Time:** ~2-5 minutes per artifact (depends on artifact length and standard complexity)
- **Accuracy:** High (uses authoritative checklists from Guideline_Researcher)
- **Scalability:** Supports batch audits (multiple artifacts for trend analysis)
- **Latency:** Asynchronous (LangSmith cloud execution)

---

## Error Handling

**Common Errors:**
- `LANGSMITH_API_KEY not configured`: Check environment variable
- `LangSmith API timeout`: Artifact too large, consider chunking
- `Artifact source not accessible`: Verify GitHub token, Google Doc permissions
- `Unsupported reporting standard`: Check standard name spelling

---

## Future Enhancements

- **Automated PR Comments**: Post audit results as GitHub PR comments
- **Custom Checklist Support**: Allow users to upload custom reporting checklists
- **Multi-Language Support**: Audit artifacts in languages other than English
- **Interactive Remediation**: Guide users step-by-step through fixing issues
- **Integration with Journal APIs**: Auto-submit checklists to journal portals

---

## Maintenance

**LangSmith Agent Updates:**
To update the LangSmith agent definition:
1. Edit agent in LangSmith Studio
2. Update `LANGSMITH_AGENT_ID` environment variable if assistant ID changes
3. Restart proxy service: `docker-compose restart agent-artifact-auditor-proxy`

**Checklist Updates:**
Guideline checklists are maintained in LangSmith. To add/update standards:
1. Update Guideline_Researcher worker in LangSmith Studio
2. Test retrieval via proxy `/agents/run/sync`
3. No proxy changes required

---

## Contact & Support

**Responsible Team:** ResearchFlow AI Team  
**LangSmith Project:** `researchflow-artifact-auditor`  
**Support:** File GitHub issues in `ROS_FLOW_2_1` repository with label `agent-artifact-auditor`

---

**Last Updated:** 2026-02-08  
**Version:** 1.0.0
