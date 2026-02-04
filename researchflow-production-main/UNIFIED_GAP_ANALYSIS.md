# Unified Gap Analysis: ResearchFlow Production
**Date:** 2026-02-03
**Sources:** Grok Analysis, ChatGPT Analysis, Claude Code Review

---

## Executive Summary

| Category | Status | Blocking Issues | Priority |
|----------|--------|-----------------|----------|
| Docker/Production Wiring | 🔴 BLOCKING | 6 | P0 - Immediate |
| Workflow Engine/Runtime | 🔴 MISSING | Core architecture | P0 - Immediate |
| Route Registration | 🟡 PARTIAL | 5 orphaned, 5 duplicates | P1 - Critical |
| Authentication/RBAC | 🟡 PARTIAL | 7 security issues | P1 - Critical |
| Document Generation | 🟡 PARTIAL | Router not registered | P1 - Critical |
| Worker Integration | 🟡 PARTIAL | Port mismatches, missing endpoints | P1 - Critical |
| Testing/E2E Pipeline | 🟡 INCOMPLETE | No full 20-stage test | P2 - High |
| Frontend API Consistency | 🟡 INCONSISTENT | Multiple clients, env vars | P2 - High |

**Verdict:** Cannot run "real live inputs → full 20 stages → fully generated documents" until P0 and P1 issues resolved.

---

## BLOCKING ISSUES (P0 - Must Fix Before Any Testing)

### 1. Docker Production Configuration Broken
**Source:** Claude Code Review

| Issue | File:Line | Impact |
|-------|-----------|--------|
| Wrong nginx config mounted | docker-compose.prod.yml:333 | Can't proxy to worker/guideline |
| Web missing backend network | docker-compose.prod.yml:337-338 | Nginx isolated from services |
| SSL cert path mismatch | docker-compose.prod.yml:110-111,331-332 | HTTPS fails |
| Orchestrator missing WORKER_URL | docker-compose.prod.yml:112-148 | Falls back to localhost |
| Orchestrator missing depends_on worker | docker-compose.prod.yml:149-157 | Race condition |
| Worker missing ORCHESTRATOR_URL | docker-compose.prod.yml:204-224 | No callbacks |

### 2. No Central Workflow Engine
**Source:** ChatGPT Analysis

The platform has 20 stage implementations but lacks:
- **Stage Registry**: No `config/workflows/workflow_20_stage.yaml` defining prerequisites, gates, outputs
- **Workflow Runtime**: No `src/workflow_runtime/` that creates run_id, writes artifacts, emits manifests
- **State Machine**: No tracking of stage completion, dependencies, or gating
- **Artifact Store Abstraction**: Direct FS writes, no S3/Blob ready architecture

**Impact:** Can't run deterministic pipeline; each stage is isolated script, not orchestrated unit.

### 3. Service Communication Broken
**Source:** Claude Code Review + Grok

| Service | Issue | Fix |
|---------|-------|-----|
| embeddingService.ts:24 | Default port 8001, worker is 8000 | Change to 8000 |
| semanticSearchService.ts:32 | Default port 8001, worker is 8000 | Change to 8000 |
| notifications.ts:26-109 | Exports function, not Router | Add default export |

---

## CRITICAL ISSUES (P1 - Must Fix For Production)

### 4. Manuscript Generation Not Wired
**Source:** Claude Code Review

`services/worker/src/api/routes/manuscript_generate.py` exists but NOT registered in `api_server.py`.

**Missing Endpoints (404):**
- POST /api/manuscript/generate
- POST /api/manuscript/generate/section
- POST /api/manuscript/scaffold/results
- POST /api/manuscript/build/discussion
- POST /api/manuscript/generate/title
- POST /api/manuscript/generate/keywords

### 5. Authentication Security Gaps
**Source:** Claude Code Review + Grok

| Issue | File | Severity |
|-------|------|----------|
| Hardcoded dev secret | authService.ts:188,239 | CRITICAL |
| Password reset token not hashed | authService.ts:661-681 | HIGH |
| Reset token logged | auth.ts:517 | HIGH |
| In-memory session store | sessionService.ts:22-23 | HIGH |
| Refresh token in localStorage | web/lib/api/auth.ts:63,75-77 | MEDIUM |
| No rate limiting on auth | auth.ts | MEDIUM |
| Accepts refresh from body | auth.ts:227 | MEDIUM |

### 6. Orphaned Routes (Not Registered)
**Source:** Claude Code Review

| File | Purpose | Status |
|------|---------|--------|
| routes/bridge.ts | TypeScript-Python bridge | Not imported |
| routes/documents.ts | Document export | Not imported |
| routes/health.ts | Health endpoints | Hardcoded in index.ts |
| routes/monitoring.ts | Model monitoring | Not imported |
| routes/manuscript/data.routes.ts | Manuscript data | Not imported |

### 7. Duplicate Route Registrations
**Source:** Claude Code Review

| Base Path | Conflict |
|-----------|----------|
| /api/search | searchRoutes + semanticSearchRoutes |
| /api/manuscripts | manuscriptsRoutes + manuscriptBranchingRoutes |
| /api/analysis | analysisPlanningRoutes + statisticalRecommendationsRoutes |
| /api/ai | aiProvidersRoutes + aiInsightsRoutes |

---

## HIGH PRIORITY ISSUES (P2 - Should Fix)

### 8. No End-to-End 20-Stage Pipeline Test
**Source:** Grok + ChatGPT

No CI test that runs: Upload → 20 stages → Generated IRB/Manuscript/Conference docs

Required:
- Synthetic data fixtures for each stage
- Deterministic seeds for reproducibility
- Artifact validation at each stage
- Full pipeline completion assertion

### 9. Frontend API Client Chaos
**Source:** Claude Code Review

Three different API client implementations:
- `services/web/src/api/client.ts` - Returns ApiResponse tuple
- `services/web/src/lib/api-client.ts` - Full-featured with timeout
- `services/web/src/lib/api/client.ts` - Class-based with retry

Environment variable inconsistency:
- Some components use `VITE_API_URL`
- Others use `VITE_API_BASE_URL`

### 10. Live Mode Not Production-Ready
**Source:** ChatGPT Analysis

ACTIVE mode requirements not fully implemented:
- Workspace isolation per user
- PHI scan before any processing
- Raw values blocked from logs/UI
- Export blocking until de-ID proven

### 11. WebSocket Authentication Missing
**Source:** Claude Code Review

`services/web/src/hooks/use-collaborative-editing.ts:112` - getToken parameter exists but not used.

---

## MEDIUM PRIORITY ISSUES (P3 - Nice to Have)

### 12. Document Build System Incomplete
**Source:** ChatGPT Analysis

Need deterministic build steps for:
- Stage 3 (IRB): Template-driven docx from study spec
- Stage 14 (Drafting): Markdown → full draft → docx
- Stage 15 (Polish): Linting/claim-check + citation verify
- Stages 18-20: PPTX + poster PDF from templates

### 13. Missing Features
- Admin email hardcoded (authService.ts:81)
- No email verification on registration
- Change password not implemented (auth.ts:668-699)
- No token refresh on 401 (redirects to login)

---

## What's Working (Positive Findings)

### Backend
- ✅ 109 route registrations total
- ✅ 34 route groups documented
- ✅ All 20 stage workers implemented
- ✅ Stage agents for stages 6-20
- ✅ Health check endpoints

### Authentication (Partial)
- ✅ RS256 JWT in production
- ✅ bcrypt with 12 salt rounds
- ✅ RBAC middleware exists
- ✅ Audit logging with hash chaining

### Docker Development
- ✅ Proper network isolation
- ✅ Health checks on services
- ✅ Redis persistence
- ✅ Log rotation

### Collaboration
- ✅ Hocuspocus server working
- ✅ Yjs persistence chain
- ✅ Agent WebSocket proxy

---

## Execution Plan Summary

### Phase 1: Docker Production Fix (Composio - Backend)
Fix all docker-compose.prod.yml issues for services to communicate.

### Phase 2: Route Registration Fix (Composio - Backend)
- Fix notifications.ts export
- Register manuscript_generate router
- Fix port 8001→8000 mismatches
- Register orphaned routes or remove dead code

### Phase 3: Security Hardening (Composio - Backend)
- Remove hardcoded secrets
- Hash reset tokens
- Move sessions to Redis
- Add rate limiting

### Phase 4: Frontend Consolidation (Cursor - Frontend)
- Standardize on single API client
- Fix environment variable usage
- Add WebSocket authentication

### Phase 5: Workflow Engine (Both - Architecture)
- Create workflow definition YAML
- Build workflow runtime layer
- Wire UI to runtime

### Phase 6: E2E Pipeline Test (Cursor - Testing)
- Create synthetic data fixtures
- Build full 20-stage test
- Add to CI

---

## Files Referenced

### Critical Files to Modify
1. `docker-compose.prod.yml` - Production wiring
2. `services/orchestrator/src/index.ts` - Route registration
3. `services/orchestrator/src/routes/notifications.ts` - Export fix
4. `services/orchestrator/src/services/embeddingService.ts` - Port fix
5. `services/orchestrator/src/services/semanticSearchService.ts` - Port fix
6. `services/worker/api_server.py` - Register manuscript router
7. `services/orchestrator/src/services/authService.ts` - Security fixes
8. `services/orchestrator/src/routes/auth.ts` - Security fixes

### New Files Needed
1. `config/workflows/workflow_20_stage.yaml` - Stage definitions
2. `src/workflow_runtime/engine.ts` - Workflow execution
3. `tests/e2e/full-pipeline.spec.ts` - 20-stage E2E test
