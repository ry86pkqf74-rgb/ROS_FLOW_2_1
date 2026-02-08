# AGENT BRIEFING: Clinical Bias Detection Agent

**Agent ID:** `agent-bias-detection`  
**Task Type:** `CLINICAL_BIAS_DETECTION`  
**Source:** LangSmith Custom Agent  
**Status:** ✅ Operational (Imported 2026-02-08)  
**Integration Date:** 2026-02-08

---

## 🎯 PURPOSE

The Clinical Bias Detection Agent is a specialized system for analyzing clinical research datasets to identify and mitigate demographic, selection, and algorithmic biases. It ensures fairness and equity in clinical analyses using a comprehensive workflow that scans, flags, analyzes, and recommends mitigations for detected biases.

## 🏗️ ARCHITECTURE

### Main Agent
- **Endpoint:** `http://agent-bias-detection-proxy:8000`
- **Sync:** `POST /agents/run/sync`
- **Stream:** `POST /agents/run/stream`
- **Execution Model:** LangSmith cloud via FastAPI proxy
- **Proxy Location:** `services/agents/agent-bias-detection-proxy/`
- **Config Bundle:** `agents/Clinical_Bias_Detection_Agent/`

### Sub-Workers (LangSmith Cloud)

#### 1. Bias_Scanner
- **File:** `subagents/Bias_Scanner/`
- **Function:** Deep bias scanning with quantitative metrics across sensitive attributes
- **Output:** Structured bias metrics report with disparity scores, distribution analysis, and identified bias patterns
- **Metrics:**
  - Representation analysis (% of expected population proportions)
  - Outcome disparity analysis (demographic parity difference)
  - Selection bias detection
  - Intersectional analysis
  - Statistical power assessment

#### 2. Bias_Mitigator
- **File:** `subagents/Bias_Mitigator/`
- **Function:** Generate actionable mitigation strategies
- **Output:** Prioritized mitigation plan with effectiveness ratings, trade-offs, post-mitigation quality scores
- **Strategies:** Resampling, stratified sampling, reweighting, targeted enrollment

#### 3. Compliance_Reviewer
- **File:** `subagents/Compliance_Reviewer/`
- **Function:** Regulatory risk assessment against FDA AI fairness guidelines, ICH E9, NIH, EMA, OECD, WHO
- **Output:** Compliance report with risk level, blocking issues, required actions, regulatory readiness score

#### 4. Red_Team_Validator
- **File:** `subagents/Red_Team_Validator/`
- **Function:** Adversarial stress-testing of bias findings
- **Output:** Validation report with challenges, robustness score, mitigation risk assessment

#### 5. Audit_Logger
- **File:** `subagents/Audit_Logger/`
- **Function:** Persistent audit trail management for regulatory traceability
- **Output:** Audit log with all analysis phases, timestamps, findings, and decisions

---

## 📋 WORKFLOW

### Phase 1: Data Ingestion & Preparation
1. Receive dataset via:
   - Pasted data (summary statistics, tabular data)
   - Google Sheets link (using `google_sheets_get_spreadsheet` + `google_sheets_read_range`)
   - Combination of both
2. Identify sensitive attributes (gender, ethnicity, age, geography, SES)
3. Identify outcome variables (treatment efficacy, diagnosis rates, enrollment)
4. Summarize dataset back to user for confirmation

### Phase 2: Scan & Flag (Bias_Scanner)
1. Delegate bias scanning to **Bias_Scanner** worker
2. Provide dataset, sensitive attributes, outcome variables
3. Review scan results:
   - Bias types detected (demographic, selection, algorithmic, geographic, intersectional)
   - Severity levels (Low/Medium/High/Critical)
   - Key metrics (disparity scores, representation %)
   - Statistical power warnings
4. Flag biases with reasoning:
   - Type and impact on clinical equity
   - Concrete examples from data
   - Compliance risk assessment

### Phase 3: Mitigation (Bias_Mitigator)
1. If biases detected, delegate to **Bias_Mitigator** worker
2. Provide bias flags + dataset context
3. Review mitigation plan:
   - Prioritized strategies
   - Effectiveness/difficulty ratings
   - Trade-offs
   - Post-mitigation quality score
4. Flag if quality score < 8/10

### Phase 4: Validation (Parallel Execution)
**CRITICAL:** Run these two workers **simultaneously**

1. Delegate to **Compliance_Reviewer**:
   - Input: bias scan + mitigation plan + dataset context
   - Output: Regulatory risk level, blocking issues, required actions, readiness score

2. Delegate to **Red_Team_Validator**:
   - Input: bias scan + mitigation plan + dataset context
   - Output: Validated/challenged findings, mitigation risks, robustness score

3. Synthesize both results:
   - Present compliance assessment
   - Present red-team findings
   - Reconcile discrepancies
   - Escalate blocking issues

### Phase 5: Report Generation & Distribution
1. **Chat Summary:**
   - Verdict: "Unbiased" (≤2/10) or "Biased" (>2/10)
   - Key findings (top 3-5 biases)
   - Compliance risk level + readiness score
   - Red-team confidence + robustness score
   - Recommended next steps

2. **Google Doc Report** (via `google_docs_create_document`):
   - Title: "Bias Detection Report - [Dataset] - [Date]"
   - Sections:
     1. Executive Summary
     2. Dataset Overview
     3. Bias Scan Results
     4. Bias Flags
     5. Mitigation Plan
     6. Compliance Risk Assessment
     7. Red-Team Validation Report
     8. Reconciled Recommendations
     9. Appendix: Methodology & Limitations

3. **Mitigated Data Output** (when applicable):
   - Create new Google Sheets spreadsheet with adjusted dataset
   - Title: "Mitigated Dataset - [Dataset] - [Date]"
   - Include Notes sheet documenting transformations

4. **Email Distribution** (optional via `gmail_send_email`):
   - Send report link with summary to specified recipients

### Phase 6: Audit Logging (Audit_Logger — ALWAYS)
1. **Always** delegate to **Audit_Logger** at analysis end
2. Provide:
   - All analysis results (scan, flags, mitigation, compliance, red-team)
   - Report link
   - Existing audit spreadsheet ID (if provided)
3. Share audit log link with user
4. **Store spreadsheet ID** for multi-analysis sessions

---

## 📥 INPUT SCHEMA

```json
{
  "task_type": "CLINICAL_BIAS_DETECTION",
  "request_id": "unique-request-id",
  "workflow_id": "workflow-id",
  "inputs": {
    "dataset_summary": "Description with key statistics (required)",
    "dataset_url": "https://docs.google.com/spreadsheets/... (optional)",
    "pasted_data": "CSV or tabular data as string (optional)",
    "sensitive_attributes": ["gender", "ethnicity", "age", "geography", "ses"],
    "outcome_variables": ["treatment_efficacy", "diagnosis_rate", "enrollment"],
    "sample_size": 1500,
    "few_shot_examples": ["example1", "example2"],
    "audit_spreadsheet_id": "existing-audit-sheet-id (optional)",
    "generate_report": true,
    "output_email": "recipient@example.com (optional)"
  }
}
```

**Example:**
```json
{
  "task_type": "CLINICAL_BIAS_DETECTION",
  "request_id": "bias-001",
  "inputs": {
    "dataset_summary": "Phase III diabetes trial, N=1200, 5 sites (US, Europe)",
    "sensitive_attributes": ["gender", "ethnicity", "age", "geography"],
    "outcome_variables": ["hba1c_reduction", "adverse_events"],
    "sample_size": 1200
  }
}
```

---

## 📤 OUTPUT SCHEMA

```json
{
  "ok": true,
  "request_id": "unique-request-id",
  "outputs": {
    "bias_verdict": "Biased | Unbiased",
    "bias_score": 6.5,
    "bias_flags": [
      {
        "type": "demographic | selection | algorithmic | geographic | intersectional",
        "severity": "Low | Medium | High | Critical",
        "attribute": "gender",
        "description": "80% male participants, expected 50%",
        "impact": "Underrepresentation may limit generalizability to female patients",
        "metrics": {
          "disparity_score": 0.30,
          "representation_ratio": 0.625
        },
        "compliance_risk": "Medium - FDA AI fairness concern"
      }
    ],
    "mitigation_plan": {
      "strategies": [
        {
          "name": "Stratified oversample female participants",
          "effectiveness": 8.5,
          "difficulty": 6.0,
          "trade_offs": ["May introduce selection bias if not randomized"]
        }
      ],
      "post_mitigation_quality_score": 8.5
    },
    "compliance_risk": {
      "risk_level": "Medium | High | Low",
      "blocking_issues": ["Issue 1", "Issue 2"],
      "required_actions": ["Action 1", "Action 2"],
      "regulatory_readiness_score": 7.2
    },
    "red_team_validation": {
      "validated_findings": ["Finding 1", "Finding 2"],
      "challenged_findings": ["Finding 3"],
      "mitigation_risks": ["Risk 1"],
      "robustness_score": 7.8
    },
    "report_url": "https://docs.google.com/document/...",
    "audit_log_url": "https://docs.google.com/spreadsheets/...",
    "mitigated_data_url": "https://docs.google.com/spreadsheets/..."
  }
}
```

---

## 🔧 INTEGRATION

### Orchestrator Configuration

Add to `AGENT_ENDPOINTS_JSON`:
```json
{
  "agent-bias-detection": "http://agent-bias-detection-proxy:8000"
}
```

### Task Type Registration

Register task type in orchestrator ai-router:
```python
TASK_TYPE_ROUTES = {
    "CLINICAL_BIAS_DETECTION": "agent-bias-detection",
    # ... other routes
}
```

### Artifact Paths

```
/data/artifacts/bias-analysis/{workflow_id}/
├── bias_report.json
├── bias_report.md
├── mitigation_plan.json
└── audit_log_reference.txt
```

---

## 🎨 EDGE CASES

### Small Datasets (N < 100 or subgroup < 30)
- Always flag low statistical power
- Warn unreliable bias conclusions
- Recommend larger data collection

### Rare/Intersectional Biases
- Perform multi-attribute analysis (e.g., elderly women of specific ethnicity)
- These are often the most critical biases

### No Biases Detected
- Still provide full metrics report as evidence
- Output verdict: "Unbiased" with supporting data
- Still run Compliance_Reviewer + Red_Team_Validator
- Still log to audit trail

### Incomplete Data
- State what additional data is needed before proceeding
- Do not proceed with insufficient data

### Red-Team Rejects Finding
- Present both original finding and challenge
- Let user decide acceptance/rejection
- Document both perspectives in report

### Compliance Blocking Issues
- Escalate prominently in chat + report
- Takes priority over other findings

---

## 📊 FAIRNESS METRICS

### Demographic Parity
- Definition: Equal outcome rates across groups
- Formula: |P(outcome=1|group=A) - P(outcome=1|group=B)|
- Flag: >0.1 = potentially biased, >0.2 = significantly biased

### Representation Ratios
- Compare observed vs expected population proportions
- Flag: <20% of expected = severely underrepresented

### Equalized Odds
- Equal true positive and false positive rates across groups

### Disparate Impact
- Ratio of outcome rates between groups
- Flag: <0.8 or >1.25 = disparate impact

---

## 🛡️ COMPLIANCE FRAMEWORKS

| Framework | Scope | Key Requirements |
|-----------|-------|------------------|
| **FDA AI Fairness** | AI/ML medical devices | Software validation, bias assessment, representative data |
| **ICH E9** | Clinical trials | Complete reporting, stratification factors |
| **NIH Inclusion Policy** | NIH-funded research | Women and minorities in clinical research |
| **EMA Guidelines** | EU trials | Inclusion/exclusion criteria transparency |
| **OECD AI Principles** | Ethical AI | Fairness, transparency, accountability |
| **WHO Guidelines** | Global health equity | Equitable access, representation |

---

## 🧪 TOOLS & INTEGRATIONS

### LangSmith Tools (via Agent Builder MCP)
- `tavily_web_search` - Research population demographics, FDA guidance
- `read_url_content` - Read full articles/guidelines
- `google_sheets_get_spreadsheet` - Get dataset metadata
- `google_sheets_read_range` - Read actual data
- `google_sheets_create_spreadsheet` - Output mitigated data
- `google_sheets_write_range` - Write data
- `google_sheets_append_rows` - Append audit log entries
- `google_docs_create_document` - Generate reports
- `google_docs_append_text` - Build report sections
- `google_docs_read_document` - Verify report content
- `gmail_send_email` - Distribute reports

### Required API Keys
- `LANGSMITH_API_KEY` (required)
- `TAVILY_API_KEY` (optional for web research)
- `GOOGLE_*_API_KEY` (optional for Google Workspace integration)

---

## 🚀 TESTING

### Health Check
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

### Run Bias Detection
```bash
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_BIAS_DETECTION",
    "request_id": "test-001",
    "inputs": {
      "dataset_summary": "Type 2 diabetes trial, N=800, 3 sites (US Northeast), 65% male, 78% white, age 45-75",
      "sensitive_attributes": ["gender", "ethnicity", "age", "geography"],
      "outcome_variables": ["hba1c_reduction", "weight_loss"],
      "sample_size": 800
    }
  }'
```

### Expected Response Time
- Phase 1-2 (Scan): ~30-60 seconds
- Phase 3 (Mitigation): ~20-40 seconds
- Phase 4 (Validation - parallel): ~40-60 seconds
- Phase 5 (Report): ~30-45 seconds
- Phase 6 (Audit): ~10-20 seconds
- **Total:** ~2.5-4 minutes for complete analysis

---

## 📚 COMMUNICATION STYLE

- **Precise & Quantitative:** Always provide numbers, percentages, scores
- **Direct:** Do not minimize or hedge on detected biases
- **Actionable:** Every finding has a clear recommendation
- **Clinical Terminology:** Use appropriate research language with explanations
- **Patient-Centric:** Frame findings in terms of patient equity and clinical impact
- **Compliance-Aware:** Reference FDA AI fairness guidelines where relevant
- **Balanced:** Present red-team challenges fairly alongside original findings

---

## ✅ DEPLOYMENT STATUS

- [x] Agent files imported to `agents/Clinical_Bias_Detection_Agent/`
- [x] Proxy service created at `services/agents/agent-bias-detection-proxy/`
- [x] Dockerfile and requirements configured
- [x] FastAPI endpoints implemented (/health, /health/ready, /agents/run/sync, /agents/run/stream)
- [x] Input/output schemas defined
- [x] README documentation created
- [x] Briefing documentation created
- [ ] Docker Compose integration (pending)
- [ ] AGENT_INVENTORY.md update (pending)
- [ ] Orchestrator task type registration (pending)
- [ ] Environment variables configuration (pending)
- [ ] Smoke test execution (pending)

---

## 🔗 RELATED DOCUMENTATION

- LangSmith Agent Config: `agents/Clinical_Bias_Detection_Agent/config.json`
- Worker Definitions: `agents/Clinical_Bias_Detection_Agent/subagents/`
- Proxy Implementation: `services/agents/agent-bias-detection-proxy/app/main.py`
- Evidence Synthesis Agent: [AGENT_EVIDENCE_SYNTHESIS_BRIEFING.md](./AGENT_EVIDENCE_SYNTHESIS_BRIEFING.md)
- Results Interpretation Agent: [AGENT_RESULTS_INTERPRETATION_BRIEFING.md](./AGENT_RESULTS_INTERPRETATION_BRIEFING.md)

---

## 📝 NOTES

- **Persistent Audit Trail:** Store `audit_spreadsheet_id` across sessions for cumulative logging
- **Parallel Phase 4:** Always run Compliance_Reviewer + Red_Team_Validator simultaneously
- **Statistical Power:** Always check sample sizes (N < 100 or subgroup < 30 is flagged)
- **No Skip Phases:** Always complete all 6 phases even if no biases detected
- **Conservative Verdicts:** Better to flag potential concern than miss real bias
- **Regulatory Focus:** FDA AI fairness, ICH E9, NIH inclusion, EMA, OECD, WHO guidelines

---

**Last Updated:** 2026-02-08  
**Maintainer:** ResearchFlow Agent Fleet Team
