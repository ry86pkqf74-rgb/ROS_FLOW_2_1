# Staging validation: dev-auth + stagewise smoke

## Track 2 – Dev-auth and stagewise smoke wiring

### dev-auth (`services/orchestrator/src/routes/devAuth.ts`)

| Item | Status |
|------|--------|
| **Mount path** | `/api/dev-auth` (confirmed in `routes.ts` and `src/index.ts`) |
| **Endpoint** | POST `/api/dev-auth/login` |
| **Guard** | `!process.env.REPL_ID && process.env.ENABLE_DEV_AUTH === "true"`; returns 404 when disabled |
| **Required header** | `X-Dev-User-Id` (400 if missing) |
| **Response** | `{ message, accessToken, user }` for web/Playwright |

Dev-auth is now mounted in the main app via `services/orchestrator/routes.ts` (used by `index.ts`), so POST `/api/dev-auth/login` is available when the server runs with `ENABLE_DEV_AUTH=true` and not on Replit.

### stagewise smoke (`scripts/stagewise-smoke.sh`)

| Step | Endpoint | Auth | Notes |
|------|----------|------|--------|
| 1 | GET /api/health | None | Always runs |
| 2 | POST /api/workflow/stages/2/approve-ai | Optional | optionalAuth; warning if no AUTH_HEADER |
| 3 | POST /api/workflow/stages/2/execute | **Required** | requireAuth; fails without token |
| 4 | GET /api/workflow/stages/2/jobs/:job_id/status | Required | Poll until completed/failed |
| 5 | GET /api/ai/feedback/pending/list | ADMIN | Skipped if no token or SKIP_ADMIN_CHECKS=1 |
| 6 | PUT /api/ai/feedback/:id/review | ADMIN | Only if step 5 returned items |
| 7 | PATCH /api/hub/workflow-runs/:runId/steps/:stepDbId | — | Optional; only if RUN_ID and STEP_DB_ID set |

**Improvements made**

- **Optional skip of admin checks**: `SKIP_ADMIN_CHECKS=1` (or `true`) skips steps 5–6 so staging can pass without an ADMIN token.
- **Clearer 401/403**: `auth_error()` prints “401 Unauthorized (missing or invalid token)” or “403 Forbidden (insufficient role, e.g. ADMIN required)” plus hint to set AUTH_HEADER or SKIP_ADMIN_CHECKS.
- **DEV_AUTH=true**: If set and `AUTH_HEADER` is unset, the script calls POST `/api/dev-auth/login` with `X-Dev-User-Id: stagewise-smoke-dev` and sets `AUTH_HEADER` from the response (only when the server has `ENABLE_DEV_AUTH=true`).

**Example (staging without touching server)**

```bash
# Server must have ENABLE_DEV_AUTH=true
export DEV_AUTH=true
export SKIP_ADMIN_CHECKS=1
./scripts/stagewise-smoke.sh
```

Or with an existing token:

```bash
export AUTH_HEADER="Authorization: Bearer <token>"
./scripts/stagewise-smoke.sh
```
