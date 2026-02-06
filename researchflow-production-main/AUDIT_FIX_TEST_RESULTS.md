# Audit Log FK Violation Fix - Test Results

## Date: 2026-02-05

## Problem
`/api/ai/router/dispatch` endpoint was returning **HTTP 500** due to `audit_logs_user_id_fkey` FK violation when service tokens (stateless JWT) tried to log audit events.

## Solution Applied
Made audit logging non-blocking by:
1. Added `isPgForeignKeyViolation()` helper to detect PG error code 23503
2. Added `safeAuditWarn()` helper to log warnings without PHI
3. Wrapped `logAction()` and `logAuthEvent()` in try/catch blocks
4. FK violations are caught, logged as warnings, and do NOT crash requests

## Files Changed
- `services/orchestrator/src/services/audit-service.ts` (101 insertions, 69 deletions)

## Git Commit
```
ae858f6 - fix(orchestrator): make audit logging non-blocking for FK violations
```

## Test Results

### Test Command
```bash
cd researchflow-production-main
WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2-)"
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "rf-stage2-smoke-003",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "inputs": {
      "query": "statins reduce cardiovascular mortality meta-analysis",
      "max_results": 5,
      "databases": ["pubmed"]
    }
  }'
```

### ✅ Result: SUCCESS

**HTTP Status:** `200 OK`

**Response Body:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-stage2-lit",
  "agent_url": "http://agent-stage2-lit:8000",
  "budgets": {},
  "rag_plan": {},
  "request_id": "rf-stage2-smoke-003"
}
```

**Response Headers:**
- `RateLimit-Limit: 100`
- `RateLimit-Remaining: 98`
- Security headers applied (CSP, HSTS, X-Frame-Options, etc.)

### Orchestrator Logs Confirm Fix
```
[audit] logAction failed (fk_violation_23503)
[audit] logAction failed (fk_violation_23503)
```

**Observations:**
- FK violations are caught and logged as warnings
- Request completes successfully with HTTP 200
- No PHI or request bodies in warning logs
- Audit logging is now **best-effort** and **non-blocking**

## Why This Is The Minimal Fix

Alternative approaches (creating service user in DB, modifying FK constraints) are higher risk and require schema changes. Making audit logging non-blocking follows security best practices:

> **Audit should observe, not gate.**

## Next Steps

✅ **CURRENT STATUS:** Dispatch endpoint returns 200 and provides agent routing information

**Potential Next Work:**
1. If Stage 2 worker execution fails, investigate agent connectivity
2. If auth issues appear elsewhere, review middleware order
3. Consider creating a proper service user record for audit trail completeness (non-blocking)

## Test Environment
- Orchestrator: Running (marked unhealthy due to Ollama connectivity, but HTTP API functional)
- Database: Connected
- Redis: Connected
- Service Token: Valid JWT with ADMIN role
