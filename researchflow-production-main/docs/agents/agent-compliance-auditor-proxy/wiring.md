# Compliance Auditor Agent - Wiring Documentation

**Date:** 2026-02-08  
**Branch:** feat/wire-compliance-auditor  
**Status:** ✅ **Wired for Production Deployment**

---

## Summary

The Compliance Auditor agent performs regulatory compliance audits on workflow logs and codebases. It audits against HIPAA, GDPR, EU AI Act, IRB, and FDA SaMD regulations. This LangSmith cloud-hosted agent is accessible via an HTTP proxy service and integrated with the orchestrator router.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy ✅

```
User/UI Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓ [task_type: COMPLIANCE_AUDIT]
TASK_TYPE_TO_AGENT mapping
    ↓ [resolves to: agent-compliance-auditor-proxy]
    ↓ [agent URL: http://agent-compliance-auditor-proxy:8000]
FastAPI Proxy (agent-compliance-auditor-proxy)
    ↓ [transform ResearchFlow → LangSmith format]
LangSmith API (https://api.smith.langchain.com)
    ↓ [executes agent + 3 worker sub-agents]
    ↓ [returns audit findings + remediation plan]
FastAPI Proxy
    ↓ [transform LangSmith → ResearchFlow format]
Response (JSON: executive_summary, audit_findings, remediation_plan)
    ↓
Artifact Writer (optional: /data/artifacts/compliance/)
    ↓
Return to caller
```

---

## Components

### 1. Proxy Service: `agent-compliance-auditor-proxy`

**Location:** `services/agents/agent-compliance-auditor-proxy/`

**Docker Service:** `agent-compliance-auditor-proxy` (compose service)

**Endpoints:**
- `GET /health` - Health check
- `GET /health/ready` - LangSmith connectivity validation
- `POST /agents/run/sync` - Synchronous audit
- `POST /agents/run/stream` - Streaming audit (SSE)

**Container Details:**
- Port: 8000 (internal)
- Networks: backend (internal), frontend (LangSmith API access)
- Health check: `/health` every 30s
- Resources: 0.5 CPU / 512MB memory (max)

### 2. Agent Configuration: `agent-compliance-auditor`

**Location:** `services/agents/agent-compliance-auditor/`

**Type:** LangSmith custom agent (cloud-hosted, not containerized)

**Worker Sub-Agents:**
1. Audit_Report_Generator - Generates formal audit reports (Google Docs)
2. Codebase_Compliance_Scanner - Scans GitHub repositories for compliance issues
3. Regulatory_Research_Worker - Researches latest regulatory updates

---

## Router Registration

### Task Type Mapping

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ... other agents ...
  COMPLIANCE_AUDIT: 'agent-compliance-auditor-proxy',  // LangSmith-hosted compliance auditor
};
```

### Endpoint Registration

**Environment Variable:** `AGENT_ENDPOINTS_JSON`

```json
{
  "agent-compliance-auditor-proxy": "http://agent-compliance-auditor-proxy:8000"
}
```

---

## Environment Variables

### Required

```bash
# LangSmith API credentials
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID=<uuid-from-langsmith>
```

### Optional

```bash
# LangSmith configuration
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1
LANGSMITH_COMPLIANCE_AUDITOR_TIMEOUT_SECONDS=300  # 5 minutes

# Logging
LOG_LEVEL=INFO
AGENT_LOG_LEVEL=INFO

# LangChain tracing
LANGCHAIN_PROJECT=researchflow-compliance-auditor
LANGCHAIN_TRACING_V2=false
```

---

## Input/Output Schema

### Input (POST `/api/ai/router/dispatch`)

```json
{
  "task_type": "COMPLIANCE_AUDIT",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "log_source": "google_sheets",
    "log_data": "1abc...xyz",
    "frameworks": ["HIPAA", "GDPR", "EU AI Act"],
    "include_code_scan": false,
    "repository": "owner/repo",
    "tracker_spreadsheet_id": "1xyz...abc"
  }
}
```

### Output

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "executive_summary": {
      "total_events_scanned": 1250,
      "findings_by_severity": {
        "CRITICAL": 2,
        "HIGH": 5,
        "MEDIUM": 12,
        "LOW": 8
      },
      "top_risk_areas": ["PHI Logging", "Missing Encryption"]
    },
    "scan_results": [...],
    "audit_findings": [...],
    "remediation_plan": [...],
    "remediation_tracker_status": {},
    "regulatory_updates": [],
    "audit_trail_metadata": {},
    "generated_artifacts": {
      "audit_report_url": "https://docs.google.com/...",
      "tracker_url": "https://docs.google.com/spreadsheets/...",
      "github_issues": []
    },
    "langsmith_run_id": "abc-123"
  }
}
```

---

## Deployment Steps

### On ROSflow2 (Hetzner)

```bash
# 1. Navigate to deployment directory
cd /opt/researchflow

# 2. Pull latest code (branch: feat/wire-compliance-auditor)
git fetch --all --prune
git checkout feat/wire-compliance-auditor
git pull --ff-only

# 3. Set environment variables
cat >> .env << 'ENV_EOF'
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID=<uuid-from-langsmith>
ENV_EOF

# 4. Build proxy service
docker compose build agent-compliance-auditor-proxy

# 5. Start proxy
docker compose up -d agent-compliance-auditor-proxy

# 6. Wait for healthy
sleep 15

# 7. Verify proxy health
docker compose ps agent-compliance-auditor-proxy
docker compose exec agent-compliance-auditor-proxy curl -f http://localhost:8000/health

# 8. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 9. Run preflight checks
./researchflow-production-main/scripts/hetzner-preflight.sh

# 10. Optional: Run smoke test
CHECK_COMPLIANCE_AUDITOR=1 DEV_AUTH=true ./researchflow-production-main/scripts/stagewise-smoke.sh
```

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**Checks:**
- ✅ `agent-compliance-auditor-proxy` in AGENT_ENDPOINTS_JSON
- ✅ Container running and healthy
- ✅ `LANGSMITH_API_KEY` present in orchestrator environment
- ✅ Task type `COMPLIANCE_AUDIT` registered in ai-router.ts

**Expected Output:**
```
✓ agent-compliance-auditor-proxy [Registry] http://agent-compliance-auditor-proxy:8000
✓ agent-compliance-auditor-proxy [Container] running
✓ agent-compliance-auditor-proxy [Health] responding
```

### Smoke Test (Optional)

**Flag:** `CHECK_COMPLIANCE_AUDITOR=1`

**Script:** `scripts/stagewise-smoke.sh`

**Tests:**
- LANGSMITH_API_KEY configured
- LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID configured
- Router dispatch returns correct agent name
- Proxy container running and healthy
- Artifact directory structure created

**Run:**
```bash
CHECK_COMPLIANCE_AUDITOR=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

---

## Troubleshooting

### Issue: 503 on /health/ready

**Cause:** `LANGSMITH_API_KEY` not set or LangSmith API unreachable

**Fix:**
```bash
echo "LANGSMITH_API_KEY=lsv2_pt_..." >> .env
docker compose up -d --force-recreate agent-compliance-auditor-proxy orchestrator
```

### Issue: Routing failures

**Symptom:** `UNSUPPORTED_TASK_TYPE` error

**Fix:** Verify task type in ai-router.ts
```bash
docker compose exec orchestrator grep "COMPLIANCE_AUDIT" /app/src/routes/ai-router.ts
```

### Issue: Proxy container not running

**Check:**
```bash
docker compose ps agent-compliance-auditor-proxy
docker compose logs agent-compliance-auditor-proxy
```

**Restart:**
```bash
docker compose up -d --force-recreate agent-compliance-auditor-proxy
```

---

## Related Documentation

- **Agent Config:** `services/agents/agent-compliance-auditor/AGENTS.md`
- **Proxy README:** `services/agents/agent-compliance-auditor-proxy/README.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`

---

**Wiring Date:** 2026-02-08  
**Status:** ✅ **COMPLETE**  
**Branch:** feat/wire-compliance-auditor  
**Next Action:** Deploy to ROSflow2 and run validation
