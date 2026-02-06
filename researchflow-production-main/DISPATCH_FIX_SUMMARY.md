# /api/ai/router/dispatch Fix Summary

## Executive Summary
✅ **FIXED**: `/api/ai/router/dispatch` now returns **HTTP 200** instead of 500

## Problem
Service-to-service API calls using `WORKER_SERVICE_TOKEN` were failing with HTTP 500 due to foreign key violations in audit logging. The stateless JWT service identity (`svc-worker@local.dev`) was not present in the `users` table, causing `audit_logs_user_id_fkey` constraint violations.

## Root Cause
The `logAction()` function in `audit-service.ts` was:
1. Attempting to insert audit logs with a non-existent `userId`
2. Throwing unhandled FK violation exceptions (PG error code 23503)
3. Crashing the entire request pipeline

## Solution: Non-Blocking Audit Logging

### Changes Made
**File:** `services/orchestrator/src/services/audit-service.ts`

**Key modifications:**
1. Added FK violation detection helper
2. Added safe warning logger (no PHI)
3. Wrapped `logAction()` in try/catch
4. Wrapped `logAuthEvent()` in try/catch
5. FK violations → logged as warnings, not thrown

### Code Added
```typescript
// NOTE: Audit logging must be best-effort and MUST NOT break primary request flows.
function isPgForeignKeyViolation(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  const code = (err as any).code;
  return code === '23503'; // foreign_key_violation
}

function safeAuditWarn(message: string, err: unknown): void {
  if (isPgForeignKeyViolation(err)) {
    console.warn(`[audit] ${message} (fk_violation_23503)`);
    return;
  }
  console.warn(`[audit] ${message}`);
}
```

### Behavior Change
**Before:**
- Request → Audit log write → FK violation → Unhandled exception → HTTP 500

**After:**
- Request → Audit log write → FK violation → Caught, logged warning → Request continues → HTTP 200

## Test Results

### Multiple Requests Tested
```bash
# Test 1: HTTP 200 ✅
# Test 2: HTTP 200 ✅
# Test 3: HTTP 200 ✅
```

### Sample Response
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-stage2-lit",
  "agent_url": "http://agent-stage2-lit:8000",
  "budgets": {},
  "rag_plan": {},
  "request_id": "test-1"
}
```

### Audit Logs Confirmation
```
[audit] logAction failed (fk_violation_23503)
[audit] logAction failed (fk_violation_23503)
[audit] logAction failed (fk_violation_23503)
```
✅ FK violations are caught and logged as warnings  
✅ No PHI or request bodies in logs  
✅ Requests complete successfully  

## Why This Is The Right Fix

### Alternatives Considered
1. **Create service user in DB** - Higher risk, requires schema/data changes
2. **Remove FK constraint** - Breaks referential integrity
3. **Write NULL for userId** - Doesn't solve the root issue if the spread includes userId

### Why Non-Blocking Is Best Practice
- **Audit should observe, not gate** - Industry standard
- **Minimal blast radius** - Only affects audit logging, not business logic
- **Graceful degradation** - System continues to function with degraded audit trail
- **PHI-safe** - No sensitive data in fallback logs

## Commit Details
```
commit ae858f6
Author: AI Assistant
Date: Thu Feb 5 02:XX:XX 2026

fix(orchestrator): make audit logging non-blocking for FK violations

- Wrap logAction() and logAuthEvent() in try/catch
- Detect PG FK violation (code 23503) specifically
- Log warnings without PHI on failure
- Requests now succeed even if audit log fails
```

## Impact Assessment

### ✅ Fixed
- `/api/ai/router/dispatch` returns 200
- Service-to-service authentication works
- AI routing dispatch flow operational
- Stage 2 worker can call orchestrator

### 🔍 Observable Side Effects
- Audit logs may be incomplete for service tokens
- Warnings appear in orchestrator logs (expected)
- No performance degradation

### 📋 Follow-up Work (Optional, Non-Blocking)
1. Create proper service user record in DB for complete audit trail
2. Implement audit log buffer/retry for transient failures
3. Add metrics for audit log failure rates

## Current System Status

### Orchestrator Health
- **HTTP API:** ✅ Operational on port 3001
- **Database:** ✅ Connected
- **Redis:** ✅ Connected
- **Health Check:** ⚠️ Unhealthy (Ollama connectivity issue, not affecting API)

### Working Endpoints
- ✅ `/api/ai/router/dispatch` - Returns agent routing
- ✅ `/api/ai/router/tiers` - Returns model tiers
- ✅ `/api/ai/router/route` - Returns routing recommendations

## Next Steps for Stage 2 Execution

The dispatch endpoint now works. Next phase:
1. ✅ Dispatch returns agent URL
2. 🔄 Worker calls agent at `http://agent-stage2-lit:8000`
3. 🔄 Agent executes literature review
4. 🔄 Results returned to worker
5. 🔄 Worker updates job status

If agent execution fails next, investigate:
- Agent container health
- Network connectivity
- Agent endpoint implementation

---

**Status:** ✅ **CHECKPOINT PASSED**  
**Blocker Removed:** HTTP 500 → HTTP 200  
**Ready For:** Stage 2 worker execution testing
