# ResearchFlow Code Review Report
**Date:** 2026-02-03
**Focus:** Backend-to-Frontend Deployment Wiring & Functionality

---

## Executive Summary

| Area | Status | Critical Issues | Warnings |
|------|--------|-----------------|----------|
| Backend Routes | PARTIAL | 1 | 6 |
| Frontend API | PARTIAL | 1 | 4 |
| Docker/Networking | BLOCKING | 6 | 2 |
| Authentication | PARTIAL | 7 | 8 |
| WebSocket/Collab | PARTIAL | 1 | 3 |
| Worker Integration | BLOCKING | 4 | 2 |

**Overall Verdict:** REQUEST_CHANGES - Multiple blocking issues must be resolved before production deployment.

---

## CRITICAL ISSUES (Must Fix)

### 1. Docker Production Configuration Broken

**File:** `docker-compose.prod.yml`

| Issue | Lines | Impact |
|-------|-------|--------|
| Wrong nginx config mounted | 333 | Uses dev config, missing worker/guideline upstreams |
| Web missing backend network | 337-338 | Nginx can't reach internal services |
| SSL cert path mismatch | 110-111, 331-332 | HTTPS will fail (expects fullchain.pem/privkey.pem) |
| Orchestrator missing WORKER_URL | 112-148 | Falls back to localhost:8000 (doesn't exist in Docker) |
| Orchestrator missing worker depends_on | 149-157 | Race condition on startup |
| Worker missing ORCHESTRATOR_URL | 204-224 | Can't callback to orchestrator |

**Fix Required:**
```yaml
# docker-compose.prod.yml - web service
volumes:
  - ./infrastructure/docker/nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro  # FIX LINE 333
  - ./infrastructure/docker/nginx/ssl/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
  - ./infrastructure/docker/nginx/ssl/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
networks:
  - frontend
  - backend  # ADD THIS

# orchestrator environment - ADD THESE:
- WORKER_URL=http://worker:8000
- ROS_API_URL=http://worker:8000
- WORKER_CALLBACK_URL=http://worker:8000

# worker environment - ADD THESE:
- ORCHESTRATOR_URL=http://orchestrator:3001
- AI_ROUTER_URL=http://orchestrator:3001/api/ai/extraction/generate
```

---

### 2. Notifications Route Will Crash

**File:** `services/orchestrator/src/routes/notifications.ts:26-109`

**Issue:** Exports a factory function, not a Router instance.
```typescript
// CURRENT (broken)
export function createNotificationsRouter(opts: { pool: Pool }) { ... }

// EXPECTED BY index.ts:129
import notificationsRoutes from './routes/notifications';
app.use('/api/notifications', notificationsRoutes);  // Crashes - function not Router
```

**Fix:** Add default export:
```typescript
export default createNotificationsRouter({ pool: db.pool });
```

---

### 3. Worker Manuscript Endpoints Missing

**File:** `services/worker/api_server.py`

**Issue:** `manuscript_generate.py` router exists but is NOT registered.

**Missing Endpoints (will return 404):**
- `POST /api/manuscript/generate`
- `POST /api/manuscript/generate/section`
- `POST /api/manuscript/scaffold/results`
- `POST /api/manuscript/build/discussion`
- `POST /api/manuscript/generate/title`
- `POST /api/manuscript/generate/keywords`

**Fix:** Add to api_server.py:
```python
from src.api.routes.manuscript_generate import router as manuscript_generate_router
app.include_router(manuscript_generate_router, prefix="/api")
```

---

### 4. Worker Port Mismatch in Services

**Files:**
- `services/orchestrator/src/services/embeddingService.ts:24`
- `services/orchestrator/src/services/semanticSearchService.ts:32`

**Issue:** Default port 8001, but worker runs on 8000.

**Fix:** Change `'http://worker:8001'` to `'http://worker:8000'`

---

### 5. Frontend Environment Variable Mismatch

**Issue:** Code uses both `VITE_API_URL` and `VITE_API_BASE_URL` inconsistently.

| File | Uses | Should Use |
|------|------|------------|
| `components/hub/HubTaskBoard.tsx` | VITE_API_URL | VITE_API_BASE_URL |
| `components/hub/HubDashboard.tsx` | VITE_API_URL | VITE_API_BASE_URL |
| `components/hub/HubTimeline.tsx` | VITE_API_URL | VITE_API_BASE_URL |
| `components/hub/HubGoalTracker.tsx` | VITE_API_URL | VITE_API_BASE_URL |

**Fix:** Standardize on `VITE_API_BASE_URL` throughout.

---

### 6. WebSocket Server Import Error

**File:** `services/orchestrator/src/index.ts:151,464-466`

**Issue:** Imports non-existent class:
```typescript
import { CollaborationWebSocketServer } from './collaboration/websocket-server';
// File only exports: createWebsocketServer(io: Server)
```

**Impact:** Will crash silently at startup due to try-catch.

---

### 7. Authentication Security Issues

| Issue | File | Line | Fix |
|-------|------|------|-----|
| Hardcoded dev secret | authService.ts | 188,239 | Remove hardcoded key |
| Password reset token not hashed | authService.ts | 661-681 | Hash before storing |
| Reset token logged | auth.ts | 517 | Remove token from logs |
| In-memory session store | sessionService.ts | 22-23 | Move to Redis |
| Refresh token in localStorage | web/lib/api/auth.ts | 63,75-77 | Use HTTP-only cookie |
| No rate limiting on auth | auth.ts | All | Add rate limiter |
| Accepts refresh from body | auth.ts | 227 | Cookie only |

---

## HIGH PRIORITY ISSUES (Should Fix)

### 8. Duplicate Route Registrations

**File:** `services/orchestrator/src/index.ts`

| Base Path | Registered At | Conflict |
|-----------|--------------|----------|
| `/api/search` | 325, 326 | searchRoutes + semanticSearchRoutes |
| `/api/manuscripts` | 306, 307 | manuscriptsRoutes + manuscriptBranchingRoutes |
| `/api/analysis` | 391, 392 | analysisPlanningRoutes + statisticalRecommendationsRoutes |
| `/api/ai` | 339, 419 | aiProvidersRoutes + aiInsightsRoutes |
| `/api` (root) | 350, 354, 404 | invitesRoutes + taskBoardsRoutes + variableSelectionRoutes |

**Recommendation:** Verify routes don't overlap or merge into single router.

---

### 9. Orphaned Route Files (Not Registered)

| File | Purpose | Status |
|------|---------|--------|
| `routes/bridge.ts` | TypeScript-Python bridge | Not imported |
| `routes/documents.ts` | Document export | Not imported (duplicate of export.ts?) |
| `routes/health.ts` | Health endpoints | Not imported (hardcoded in index.ts) |
| `routes/monitoring.ts` | Model monitoring | Not imported |
| `routes/manuscript/data.routes.ts` | Manuscript data | Not imported |

---

### 10. Missing Response Validation

**File:** `services/orchestrator/src/routes/manuscript-generation.ts:314-328`

```typescript
const [titleRes, keywordRes] = await Promise.all([...]);
results.titles = await titleRes.json();  // No .ok check - will fail on 404
```

---

### 11. Multiple API Client Implementations

**Files:**
- `services/web/src/api/client.ts` - Returns ApiResponse tuple
- `services/web/src/lib/api-client.ts` - Full-featured with timeout
- `services/web/src/lib/api/client.ts` - Class-based with retry

**Recommendation:** Consolidate to single implementation.

---

## MEDIUM PRIORITY ISSUES (Nice to Fix)

### 12. Admin Email Hardcoded
- **File:** `services/orchestrator/src/services/authService.ts:81`
- **Issue:** Fallback to `logan.glosser@gmail.com`

### 13. Missing WebSocket Authentication
- **File:** `services/web/src/hooks/use-collaborative-editing.ts:112`
- **Issue:** getToken parameter exists but not used

### 14. No Email Verification on Registration
- **File:** `services/orchestrator/src/routes/auth.ts:31-120`

### 15. Change Password Not Implemented
- **File:** `services/orchestrator/src/routes/auth.ts:668-699`
- Returns placeholder message

### 16. Missing Token Refresh on 401
- **File:** `services/web/src/lib/api/client.ts:101-107`
- Redirects to login instead of attempting refresh

---

## POSITIVE FINDINGS

### Backend Routes
- 109 route registrations total
- 34 route groups documented
- Comprehensive API coverage

### Authentication
- RS256 JWT in production
- bcrypt with 12 salt rounds
- Comprehensive RBAC middleware
- Audit logging with hash chaining
- HTTP-only cookies for refresh (backend)

### Worker Service
- All 20 stage workers implemented
- Stage agents for stages 6-20
- Proper agent registry
- Health check endpoints

### Docker Development
- Proper network isolation (frontend/backend)
- Health checks on all services
- Redis persistence configured
- Log rotation enabled

### WebSocket/Collab
- Hocuspocus server working
- Yjs persistence (Redis > Postgres > Memory)
- Nginx proxy configured
- Agent WebSocket proxy working

---

## Recommended Fix Order

### Phase 1: Docker Production (Blocking)
1. Fix nginx config mount in docker-compose.prod.yml
2. Add web service to backend network
3. Fix SSL certificate paths
4. Add missing environment variables

### Phase 2: Route Registration (Critical)
5. Fix notifications.ts export
6. Register manuscript_generate router in worker
7. Fix port 8001 → 8000 in embedding services

### Phase 3: Security (High)
8. Remove hardcoded auth secrets
9. Hash password reset tokens
10. Move session store to Redis
11. Add rate limiting to auth endpoints

### Phase 4: Frontend Cleanup (Medium)
12. Standardize environment variables
13. Consolidate API clients
14. Add response validation

---

## Files Modified/Created

This review analyzed:
- `services/orchestrator/src/index.ts`
- `services/orchestrator/src/routes/` (123 files)
- `services/orchestrator/src/services/authService.ts`
- `services/web/src/` (API, hooks, stores)
- `services/worker/api_server.py`
- `services/collab/src/`
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `infrastructure/docker/nginx/`

---

**Report Generated By:** Claude Code Review Agent
**Session:** https://claude.ai/code/session_01NdsM1BkbWhmzEbGrGpkWau
