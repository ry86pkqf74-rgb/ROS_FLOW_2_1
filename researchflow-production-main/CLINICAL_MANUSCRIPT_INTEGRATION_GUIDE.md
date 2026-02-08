# Clinical Manuscript Writer - Integration Guide

**Date:** 2026-02-07  
**Agent:** Clinical Manuscript Writer (LangSmith Multi-Agent System)  
**Status:** ✅ Imported and Documented  
**Integration Status:** 🔄 Ready for Workflow Alignment

---

## 📋 Quick Reference

| Property | Value |
|---|---|
| **Agent Directory** | `services/agents/agent-clinical-manuscript/` |
| **Agent Type** | LangSmith Multi-Agent System |
| **Deployment** | LangSmith Cloud (containerization planned) |
| **Sub-Agents** | 4 (Literature Research, Statistical Review, Compliance, Data Extraction) |
| **Tools** | Google Docs, Google Sheets, Tavily, Exa, Gmail |
| **Integration Point** | Receives output from `agent-evidence-synthesis` |
| **Output Format** | Google Docs (manuscripts) + Google Sheets (Evidence Ledger) |

---

## 🏗️ Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                   ResearchFlow Production Pipeline                 │
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│         Stage 2: Evidence Pipeline (Existing)                     │
│  ├─ agent-stage2-lit (Literature Search)                          │
│  ├─ agent-stage2-screen (Deduplication)                           │
│  ├─ agent-stage2-extract (PICO Extraction)                        │
│  └─ agent-evidence-synthesis (GRADE Synthesis)                    │
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ [Structured Evidence Output]
┌───────────────────────────────────────────────────────────────────┐
│    Clinical Manuscript Writer (LangSmith - NEW)                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Main Agent: Clinical Manuscript Writer                      │ │
│  │  • Receives PICO questions + GRADE assessments              │ │
│  │  • Orchestrates sub-agents                                  │ │
│  │  • Drafts IMRaD sections                                    │ │
│  │  • Runs audit loop                                          │ │
│  │  • Writes to Google Docs                                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                           │                                        │
│       ┌───────────────────┼──────────────────┬──────────────────┐ │
│       ▼                   ▼                  ▼                  ▼ │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  │Literature│      │Statistical│      │Compliance│      │   Data   │
│  │ Research │      │  Review   │      │  Agent   │      │Extraction│
│  │  Agent   │      │  Agent    │      │(CONSORT) │      │  Agent   │
│  └──────────┘      └──────────┘      └──────────┘      └──────────┘
└───────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                     Output Artifacts                               │
│  • Google Doc: Publication-ready manuscript (IMRaD)               │
│  • Google Sheet: Evidence Ledger (3 sheets)                       │
│  • Compliance Scorecard (embedded in doc)                         │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Workflow Integration

### Integration Pattern: Sequential Evidence-to-Manuscript Pipeline

**Stage 2 → Clinical Manuscript Writer → Publication Output**

#### Phase 1: Evidence Synthesis (Existing)

**Agent:** `agent-evidence-synthesis`  
**Input:** PICO research questions  
**Process:**
1. Decompose research questions
2. Retrieve evidence from clinical databases
3. Apply GRADE quality evaluation
4. Detect conflicts and analyze perspectives
5. Generate structured synthesis report

**Output:** JSON with structured evidence:
```json
{
  "pico_questions": [...],
  "evidence_items": [
    {
      "source": "Study Name",
      "finding": "Effect observed",
      "grade_quality": "High",
      "confidence_interval": "95% CI [x, y]",
      "p_value": 0.032
    }
  ],
  "conflicts": [...],
  "methodology_notes": "..."
}
```

#### Phase 2: Manuscript Generation (NEW)

**Agent:** `agent-clinical-manuscript`  
**Input:** 
- Structured evidence from Phase 1 (JSON)
- Study protocol/design details (user-provided or extracted)
- Raw clinical data (optional - Google Sheets)

**Process:**
1. **PHI Pre-Scan** (if raw data provided)
2. **Data Extraction** (if needed): Parse raw data → Table 1, descriptive stats
3. **Literature Contextualization** (parallel): Search for comparable studies
4. **Section Drafting**:
   - Introduction: Background + rationale + study objectives
   - Methods: Study design + analysis plan (from protocol)
   - Results: Evidence findings + statistics (from Phase 1 + raw data)
   - Discussion: Interpretation + comparison + implications
5. **Automated Audit Loop**:
   - Statistical Review Agent → Validate all statistics
   - Compliance Agent → CONSORT/SPIRIT checklist
6. **Self-Revision**: Fix issues identified by audits
7. **Google Doc Writing**: 
   - Create or append to manuscript document
   - Add version log entry
8. **Evidence Ledger Update**:
   - Append Evidence IDs to Evidence Log sheet
   - Update Data Quality sheet
   - Update Compliance Audit sheet

**Output:**
- Google Doc URL (manuscript)
- Google Sheet URL (Evidence Ledger)
- Compliance scorecard summary

---

## 🚀 Deployment Options

### Current State: LangSmith Cloud

**Pros:**
- No infrastructure management
- Immediate availability
- Built-in prompt versioning and monitoring
- Sub-agent orchestration handled by LangSmith

**Cons:**
- External dependency
- Requires API authentication
- Latency for external calls

**Access Method:**
```python
from langsmith import Client

client = Client(api_key="lsv2_pt_...")
response = client.invoke_agent(
    agent_id="clinical-manuscript-writer",
    input={
        "evidence": structured_evidence_json,
        "study_type": "RCT",
        "reporting_guideline": "CONSORT",
        "target_doc_id": "google_doc_id"
    }
)
```

### Future: Containerized Microservice

**Architecture Pattern:** FastAPI + LangGraph (following `agent-evidence-synthesis` pattern)

**Suggested Structure:**
```
agent-clinical-manuscript/
├── Dockerfile
├── requirements.txt
├── app/
│   └── main.py                    # FastAPI app
├── agent/
│   ├── __init__.py
│   ├── clinical_manuscript.py    # Main LangGraph agent
│   └── schemas.py                # Pydantic models
├── subagents/
│   ├── literature_research.py
│   ├── statistical_review.py
│   ├── compliance_audit.py
│   └── data_extraction.py
└── workers/
    ├── google_docs_worker.py
    ├── google_sheets_worker.py
    └── web_search_worker.py
```

**Dockerfile Template:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Expose port
EXPOSE 8016

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD curl -f http://localhost:8016/health || exit 1

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8016"]
```

**docker-compose.yml Addition:**
```yaml
agent-clinical-manuscript:
  build: ./services/agents/agent-clinical-manuscript
  container_name: agent-clinical-manuscript
  ports:
    - "8016:8016"
  environment:
    - TAVILY_API_KEY=${TAVILY_API_KEY}
    - EXA_API_KEY=${EXA_API_KEY}
    - GOOGLE_DOCS_API_KEY=${GOOGLE_DOCS_API_KEY}
    - GOOGLE_SHEETS_API_KEY=${GOOGLE_SHEETS_API_KEY}
    - GMAIL_API_KEY=${GMAIL_API_KEY}
    - WORKER_SERVICE_TOKEN=${WORKER_SERVICE_TOKEN}
    - ORCHESTRATOR_URL=http://orchestrator:3000
  networks:
    - researchflow-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8016/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**API Endpoints:**
```
POST   /api/manuscript/draft          # Draft section or full manuscript
POST   /api/manuscript/audit           # Run compliance/statistical audit
POST   /api/manuscript/evidence-ledger # Generate/update evidence ledger
GET    /api/manuscript/status/:task_id # Get drafting progress
GET    /health                         # Health check
```

---

## 🔗 Orchestrator Integration

### Option 1: Direct LangSmith API Call (Current)

**Location:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
// Add to agent routing table
const AGENT_ROUTING: Record<string, AgentConfig> = {
  // ... existing agents
  CLINICAL_MANUSCRIPT: {
    type: 'langsmith',
    agentId: 'clinical-manuscript-writer',
    apiKey: process.env.LANGSMITH_API_KEY,
    endpoint: 'https://api.smith.langchain.com/v1/agents/invoke',
    timeout: 300000  // 5 min timeout for manuscript generation
  }
};

// Handler
async function dispatchToLangSmithAgent(config: LangSmithAgentConfig, payload: any) {
  const response = await fetch(config.endpoint, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      agent_id: config.agentId,
      input: payload
    })
  });
  
  if (!response.ok) {
    throw new Error(`LangSmith agent failed: ${response.statusText}`);
  }
  
  return await response.json();
}
```

**Usage from workflow:**
```typescript
const result = await dispatch({
  agentType: 'CLINICAL_MANUSCRIPT',
  payload: {
    evidence: synthesizerOutput,
    study_type: 'RCT',
    reporting_guideline: 'CONSORT',
    sections_requested: ['Introduction', 'Methods', 'Results', 'Discussion']
  }
});

// Result contains Google Doc URL + Evidence Ledger URL
console.log('Manuscript URL:', result.manuscript_url);
console.log('Evidence Ledger URL:', result.evidence_ledger_url);
```

### Option 2: Containerized Microservice (Future)

**After containerization, integrate like existing agents:**

```typescript
const AGENT_ROUTING: Record<string, AgentConfig> = {
  CLINICAL_MANUSCRIPT: {
    type: 'microservice',
    url: process.env.AGENT_CLINICAL_MANUSCRIPT_URL || 'http://agent-clinical-manuscript:8016',
    endpoint: '/api/manuscript/draft',
    healthCheck: '/health',
    timeout: 300000
  }
};
```

---

## 🧪 Testing Strategy

### Unit Tests (Future Containerization)

```python
# tests/test_clinical_manuscript.py
import pytest
from agent.clinical_manuscript import ClinicalManuscriptAgent

def test_imrad_section_generation():
    agent = ClinicalManuscriptAgent()
    evidence = {
        "pico_questions": ["Does intervention X reduce outcome Y?"],
        "evidence_items": [{"source": "Study A", "finding": "Significant reduction"}]
    }
    
    result = agent.draft_section(
        section="Results",
        evidence=evidence,
        study_type="RCT"
    )
    
    assert "Results" in result["section_title"]
    assert len(result["evidence_ids"]) > 0
    assert result["compliance_status"] == "Audited"

def test_phi_screening():
    agent = ClinicalManuscriptAgent()
    unsafe_data = "Patient John Doe, DOB: 1980-01-15, MRN: 123456"
    
    with pytest.raises(PHIDetectedError):
        agent.process_raw_data(unsafe_data)
```

### Integration Tests

```bash
# Test workflow: Evidence Synthesis → Manuscript Writer
cd /opt/researchflow/researchflow-production-main

# 1. Generate evidence (Stage 2)
curl -X POST http://localhost:8015/api/synthesize \
  -H "Content-Type: application/json" \
  -d @test/fixtures/pico_questions.json \
  > evidence_output.json

# 2. Send to Manuscript Writer (LangSmith API)
curl -X POST https://api.smith.langchain.com/v1/agents/invoke \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "clinical-manuscript-writer",
    "input": {
      "evidence": '$(cat evidence_output.json)',
      "study_type": "RCT",
      "reporting_guideline": "CONSORT"
    }
  }' \
  | jq '.manuscript_url, .evidence_ledger_url'
```

### End-to-End Test

```bash
# Full pipeline test
./scripts/test-manuscript-pipeline.sh
```

**Script Contents:**
```bash
#!/bin/bash
set -euo pipefail

echo "🧪 Testing Evidence-to-Manuscript Pipeline"

# 1. Start agent-evidence-synthesis
docker compose up -d agent-evidence-synthesis
sleep 5

# 2. Submit PICO questions
EVIDENCE_OUTPUT=$(curl -s -X POST http://localhost:8015/api/synthesize \
  -H "Content-Type: application/json" \
  -d @test/fixtures/diabetes_rct.json)

echo "✅ Evidence synthesis complete"

# 3. Extract structured evidence
STRUCTURED_EVIDENCE=$(echo "$EVIDENCE_OUTPUT" | jq '.synthesis_report')

# 4. Call Clinical Manuscript Writer (LangSmith)
MANUSCRIPT_RESULT=$(curl -s -X POST https://api.smith.langchain.com/v1/agents/invoke \
  -H "Authorization: Bearer $LANGSMITH_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"agent_id\": \"clinical-manuscript-writer\",
    \"input\": {
      \"evidence\": $STRUCTURED_EVIDENCE,
      \"study_type\": \"RCT\",
      \"reporting_guideline\": \"CONSORT\",
      \"sections_requested\": [\"Introduction\", \"Methods\", \"Results\", \"Discussion\"]
    }
  }")

echo "✅ Manuscript generation complete"

# 5. Verify outputs
MANUSCRIPT_URL=$(echo "$MANUSCRIPT_RESULT" | jq -r '.manuscript_url')
LEDGER_URL=$(echo "$MANUSCRIPT_RESULT" | jq -r '.evidence_ledger_url')

if [[ "$MANUSCRIPT_URL" != "null" && "$LEDGER_URL" != "null" ]]; then
  echo "✅ Pipeline test PASSED"
  echo "📄 Manuscript: $MANUSCRIPT_URL"
  echo "📊 Evidence Ledger: $LEDGER_URL"
  exit 0
else
  echo "❌ Pipeline test FAILED"
  exit 1
fi
```

---

## 📊 Monitoring & Observability

### LangSmith Tracing (Current)

When hosted on LangSmith, all agent invocations are automatically traced:

- **LangSmith UI:** https://smith.langchain.com/
- **View traces:** Agent invocations → Clinical Manuscript Writer
- **Metrics tracked:**
  - Input tokens
  - Output tokens
  - Latency per sub-agent
  - Tool call success/failure rates
  - Error logs

### Containerized Monitoring (Future)

When containerized, integrate with existing observability stack:

**Prometheus Metrics:**
```python
# agent/clinical_manuscript.py
from prometheus_client import Counter, Histogram

manuscript_requests = Counter('manuscript_requests_total', 'Total manuscript requests', ['section', 'study_type'])
manuscript_duration = Histogram('manuscript_duration_seconds', 'Manuscript generation duration', ['section'])
phi_detections = Counter('phi_detections_total', 'PHI detection events')
compliance_scores = Histogram('compliance_scores', 'CONSORT compliance scores', ['guideline'])
```

**Logging:**
```python
import structlog

logger = structlog.get_logger()

logger.info("manuscript_draft_started",
            section="Results",
            study_type="RCT",
            evidence_items=len(evidence))

logger.warning("data_gap_detected",
               missing_field="sample_size_calculation",
               section="Methods")

logger.error("phi_detected",
              phi_types=["MRN", "DOB"],
              source="user_provided_data")
```

---

## 🔐 Security Considerations

### PHI Protection

**Mandatory PHI pre-scan** for all user-provided data:
- Implemented in `Data_Extraction_Agent`
- Runs before any data processing
- Blocks execution if PHI detected

**PHI Patterns Detected:**
- Patient names, initials
- MRNs, SSNs
- Dates more specific than year
- Phone numbers, emails
- Geographic data below state level

**Recommendation:** Add audit logging for PHI detection events

### API Key Management

**Required API Keys:**
- `LANGSMITH_API_KEY` - For agent invocation (current deployment)
- `TAVILY_API_KEY` - For literature search
- `EXA_API_KEY` - For enhanced literature search
- `GOOGLE_DOCS_API_KEY` - For manuscript writing
- `GOOGLE_SHEETS_API_KEY` - For Evidence Ledger
- `GMAIL_API_KEY` - For cover letter drafting

**Security Best Practices:**
- Store in `.env` file (never commit)
- Use secrets management (e.g., AWS Secrets Manager, Vault)
- Rotate keys regularly
- Audit key usage via LangSmith logs

### Google Workspace Access

**OAuth Scopes Required:**
- `https://www.googleapis.com/auth/documents` (read/write Google Docs)
- `https://www.googleapis.com/auth/spreadsheets` (read/write Google Sheets)
- `https://www.googleapis.com/auth/gmail.compose` (draft emails only)

**Access Control:**
- Agent should use a dedicated service account
- Grant minimum necessary permissions
- Enable audit logging on Google Workspace side

---

## 📚 Documentation Updates

### Files Updated

✅ **AGENT_INVENTORY.md**
- Added Clinical Manuscript Writer to Writing & Verification Agents section
- Updated total agent counts
- Documented sub-agent architecture

✅ **agent-clinical-manuscript/README.md**
- Comprehensive agent documentation (this file)
- Usage patterns
- PHI protection workflow
- Evidence traceability system

✅ **CLINICAL_MANUSCRIPT_INTEGRATION_GUIDE.md** (this file)
- Workflow integration patterns
- Deployment options
- Testing strategy
- Security considerations

### Files to Update Next

⏳ **AGENT_COORDINATION_DASHBOARD.md**
- Add Clinical Manuscript Writer to agent fleet overview
- Document dependencies: Evidence Synthesis → Manuscript Writer
- Add to agent communication matrix

⏳ **docker-compose.yml** (when containerizing)
- Add service definition for agent-clinical-manuscript

⏳ **orchestrator/src/routes/ai-router.ts** (when integrating)
- Add CLINICAL_MANUSCRIPT routing
- Add LangSmith API client

⏳ **EVIDENCE_SYNTHESIS_INTEGRATION_GUIDE.md**
- Update "Next Steps" to include manuscript generation
- Add example of evidence → manuscript workflow

---

## 🎯 Next Steps

### Immediate (Current Sprint)

1. ✅ **Import agent files from LangSmith** - COMPLETE
2. ✅ **Create comprehensive README** - COMPLETE
3. ✅ **Update AGENT_INVENTORY.md** - COMPLETE
4. ⏳ **Update AGENT_COORDINATION_DASHBOARD.md**
5. ⏳ **Test LangSmith API integration** (manual test)

### Short-Term (Next Sprint)

6. **Add orchestrator routing** for LangSmith agent calls
7. **Create test fixtures** (sample evidence JSON from Stage 2)
8. **Write integration test script** (evidence → manuscript pipeline)
9. **Document API key setup** for team (LangSmith + Google APIs)
10. **Create example workflow** in ResearchFlow UI

### Medium-Term (Q1 2026)

11. **Evaluate containerization feasibility** (migrate from LangSmith to self-hosted)
12. **Design FastAPI + LangGraph architecture** (if containerizing)
13. **Implement Prometheus metrics** for monitoring
14. **Add PHI audit logging** with alerting
15. **Create UI components** for manuscript preview in ResearchFlow

### Long-Term (Q2+ 2026)

16. **Multi-guideline support expansion** (add CARE, ARRIVE, STARD extensions)
17. **Journal-specific formatting** (NEJM, Lancet, JAMA styles)
18. **Automated figure generation** from data (integration with plotting libraries)
19. **Real-time collaborative editing** (integrate with Google Docs realtime API)
20. **AI-powered peer review** simulation (add Peer Review Agent)

---

## 🏷️ Tags

`#clinical-manuscript` `#langsmith` `#multi-agent` `#imrad` `#consort` `#spirit` `#evidence-synthesis` `#workflow-integration` `#phi-protection` `#manuscript-writing`

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-07  
**Author:** ResearchFlow Integration Team  
**Status:** ✅ Ready for Review
