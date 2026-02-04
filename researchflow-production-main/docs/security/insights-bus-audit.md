# InsightsBus Security Audit - HIPAA Compliance Review

**Audit Date:** January 29, 2026  
**Auditor:** Security Agent (Automated - ROS-60)  
**File:** `packages/core/src/services/insightsBus.ts`  
**Linear Issue:** ROS-60

---

## Executive Summary

The InsightsBus module implements a Redis Streams-based event bus for AI transparency logging. This audit evaluates HIPAA compliance for handling Protected Health Information (PHI) in event payloads.

**Overall Risk Level:** 🟡 MEDIUM - Requires configuration hardening for production

---

## 1. PHI in Event Payloads

### Current Implementation
```typescript
const fields: Record<string, string> = {
  type: AI_INVOCATION_EVENT_TYPE,
  data: JSON.stringify(event),  // ⚠️ Full event serialized
  timestamp: event.timestamp,
  governance_mode: event.governance_mode,
  project_id: event.project_id,
  tier: event.tier,
  status: event.status,
};
```

### Findings

| Field | PHI Risk | Recommendation |
|-------|----------|----------------|
| `data` (full JSON) | 🔴 HIGH | May contain PHI from AI responses |
| `project_id` | 🟡 MEDIUM | Could be linked to patient data |
| `user_id` | 🟢 LOW | Internal user identifier |
| `run_id` | 🟢 LOW | Execution identifier |

### Remediation Required
1. **Implement PHI scrubbing** before event serialization
2. **Add field-level encryption** for sensitive data
3. **Create allowlist** of safe-to-log fields

```typescript
// RECOMMENDED: Add PHI filter before publish
private scrubPHI(event: AIInvocationEvent): AIInvocationEvent {
  return {
    ...event,
    // Remove or hash potentially PHI-containing fields
    input: '[REDACTED]',
    output: this.hashIfContainsPHI(event.output),
  };
}
```

---

## 2. Redis TLS Configuration

### Current Implementation
```typescript
this.redis = new Redis(this.config.redisUrl, {
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  lazyConnect: true,
  // ⚠️ NO TLS CONFIGURATION
});
```

### Findings
- **TLS is NOT enforced** - data transmitted in plaintext
- **No certificate validation** configured
- Connection URL accepts `redis://` (insecure) or `rediss://` (TLS)

### Remediation Required
```typescript
// RECOMMENDED: Enforce TLS in production
this.redis = new Redis(this.config.redisUrl, {
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
  lazyConnect: true,
  // ADD: TLS configuration for HIPAA compliance
  tls: process.env.NODE_ENV === 'production' ? {
    rejectUnauthorized: true,
    ca: process.env.REDIS_CA_CERT,
  } : undefined,
});
```

**Environment Configuration:**
```bash
# Production .env
REDIS_URL=rediss://user:password@redis-host:6379
REDIS_CA_CERT=/path/to/ca-certificate.pem
```

---

## 3. Access Control

### Current Implementation
- ✅ Consumer groups provide isolation
- ✅ Stream trimming prevents unbounded growth
- ⚠️ No authentication beyond Redis password
- ⚠️ No role-based access to events

### Findings

| Control | Status | Notes |
|---------|--------|-------|
| Authentication | 🟡 Partial | Redis AUTH only |
| Authorization | 🔴 Missing | No RBAC on events |
| Audit Trail | ✅ Present | Entry IDs are timestamps |
| Data Retention | 🟡 Partial | MAXLEN trimming, no time-based |

### Remediation Required
1. **Add tenant isolation** - prefix streams by tenant_id
2. **Implement event-level ACL** - check permissions before consume
3. **Add retention policy** - time-based expiration for HIPAA

```typescript
// RECOMMENDED: Tenant-isolated stream names
private getStreamName(tenantId: string): string {
  return `ros:insights:${tenantId}`;
}

// RECOMMENDED: Permission check before consume
async consume(handler: EventHandler, options: ConsumeOptions): Promise<void> {
  if (!await this.checkPermission(options.userId, 'insights:read')) {
    throw new UnauthorizedError('No permission to consume insights');
  }
  // ... existing consume logic
}
```

---

## 4. Data Encryption

### Current Implementation
- ❌ No field-level encryption
- ❌ No encryption at rest (depends on Redis config)
- ⚠️ Relies on transport encryption only

### Remediation Required
```typescript
// RECOMMENDED: Encrypt sensitive fields
import { createCipheriv, createDecipheriv } from 'crypto';

private encryptField(value: string): string {
  const cipher = createCipheriv('aes-256-gcm', this.encryptionKey, this.iv);
  return cipher.update(value, 'utf8', 'base64') + cipher.final('base64');
}

async publish(event: AIInvocationEvent): Promise<string | null> {
  const encryptedEvent = {
    ...event,
    data: this.encryptField(JSON.stringify(event.data)),
  };
  // ... publish encrypted event
}
```

---

## 5. Compliance Checklist

| Requirement | Status | Action Required |
|-------------|--------|-----------------|
| PHI Minimum Necessary | 🔴 FAIL | Implement field filtering |
| Encryption in Transit | 🟡 PARTIAL | Enforce TLS in production |
| Encryption at Rest | 🔴 FAIL | Configure Redis encryption |
| Access Controls | 🟡 PARTIAL | Add RBAC layer |
| Audit Logging | ✅ PASS | Stream IDs provide audit trail |
| Data Retention | 🟡 PARTIAL | Add time-based expiration |
| Business Associate Agreement | N/A | Infrastructure-level |

---

## 6. Recommended Actions

### Immediate (P0)
1. [ ] Enable TLS for Redis connections in production
2. [ ] Add PHI scrubbing filter before event publish
3. [ ] Create environment variable `INSIGHTS_TLS_REQUIRED=true`

### Short-term (P1)
4. [ ] Implement field-level encryption for sensitive data
5. [ ] Add tenant isolation to stream names
6. [ ] Create RBAC middleware for consume operations

### Long-term (P2)
7. [ ] Implement time-based retention policy
8. [ ] Add automated PHI detection scanning
9. [ ] Create compliance dashboard for audit

---

## 7. Test Coverage Required

See: `tests/security/insights-phi-scan.test.ts`

```typescript
describe('InsightsBus HIPAA Compliance', () => {
  it('should not publish events containing PHI patterns');
  it('should enforce TLS in production environment');
  it('should isolate events by tenant');
  it('should require authentication for consume');
  it('should encrypt sensitive fields');
});
```

---

**Audit Complete**  
*Generated by ROS-60 Security Agent*
