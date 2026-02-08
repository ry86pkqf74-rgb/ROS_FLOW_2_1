# Compliance Auditor - Quick Deployment Reference

**Status:** ✅ Fully Wired - Ready for Production  
**Date:** 2026-02-08

---

## Pre-Deployment Checklist

### Required Environment Variables

Add to `.env` on ROSflow2:

```bash
# LangSmith credentials (required)
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID=<uuid-from-langsmith>

# Tool credentials (for agent capabilities)
GOOGLE_WORKSPACE_API_KEY=...  # Google Sheets/Docs
GITHUB_TOKEN=...              # Code scanning
TAVILY_API_KEY=...            # Regulatory research (optional)
```

---

## One-Command Deploy

```bash
cd /opt/researchflow && \
git fetch --all --prune && \
git pull --ff-only && \
docker compose build agent-compliance-auditor-proxy && \
docker compose up -d agent-compliance-auditor-proxy && \
sleep 15 && \
docker compose exec agent-compliance-auditor-proxy curl -f http://localhost:8000/health && \
docker compose up -d --force-recreate orchestrator && \
./scripts/hetzner-preflight.sh
```

---

## Validation (30 seconds)

```bash
# 1. Container running?
docker compose ps agent-compliance-auditor-proxy

# 2. Health check
docker compose exec agent-compliance-auditor-proxy curl http://localhost:8000/health

# 3. LangSmith connectivity
docker compose exec agent-compliance-auditor-proxy curl http://localhost:8000/health/ready

# 4. Router knows about it?
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep compliance

# 5. Preflight passes?
./scripts/hetzner-preflight.sh

# 6. Optional: Full smoke test
CHECK_COMPLIANCE_AUDITOR=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

---

## Test Request

```bash
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "task_type": "COMPLIANCE_AUDIT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "log_source": "direct",
      "log_data": "2026-02-08 INFO: User accessed PHI",
      "frameworks": ["HIPAA"]
    }
  }'
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Container won't start | `docker compose logs agent-compliance-auditor-proxy` |
| 503 on /health/ready | Verify `LANGSMITH_API_KEY` is set |
| Router error | Restart orchestrator: `docker compose up -d --force-recreate orchestrator` |
| Preflight fails | Check logs, verify all env vars set |

---

## What Was Wired

1. ✅ Docker service: `agent-compliance-auditor-proxy`
2. ✅ Router mapping: `COMPLIANCE_AUDIT` → `agent-compliance-auditor-proxy`
3. ✅ Endpoint registry: Added to `AGENT_ENDPOINTS_JSON`
4. ✅ Mandatory list: Added to `agent_endpoints_required.txt`
5. ✅ Validation: Preflight + smoke test scripts updated
6. ✅ Documentation: AGENT_INVENTORY.md updated

---

## Regulatory Frameworks Covered

- HIPAA (Privacy, Security, Breach Notification)
- IRB (Human Subjects Research)
- EU AI Act (High-Risk Health AI)
- GDPR (Health Data Processing)
- FDA SaMD (Software as Medical Device)

---

## Key Capabilities

- **Log Audits**: Scan workflow logs for compliance violations
- **Code Scans**: GitHub repository compliance checking
- **Risk Scoring**: CRITICAL/HIGH/MEDIUM/LOW severity
- **Remediation Plans**: Immediate + short-term + long-term actions
- **Formal Reports**: Google Docs audit reports
- **Tracking**: Google Sheets remediation tracker
- **GitHub Integration**: Auto-create issues for CRITICAL findings

---

**Full Documentation:** See `COMPLIANCE_AUDITOR_WIRING_COMPLETE.md`
