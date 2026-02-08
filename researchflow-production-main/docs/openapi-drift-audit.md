# OpenAPI drift audit (preflight + stagewise smoke)

Comparison of `services/orchestrator/openapi.json` vs mounted routes in `services/orchestrator/routes.ts` (and `index.ts`), scoped to endpoints used by preflight and stagewise smoke.

## Mismatch table

| Endpoint | In OpenAPI | Mounted | Notes |
|----------|------------|---------|--------|
| GET /api/health | Yes | Yes (index.ts + routes.ts) | OK |
| POST /api/auth/login | Yes | Yes (/api/auth) | OK |
| POST /api/dev-auth/login | No | Yes (/api/dev-auth, when ENABLE_DEV_AUTH=true) | **Missing from OpenAPI** |
| POST /api/workflow/stages/:stageId/approve-ai | No | Yes (/api/workflow) | **Missing from OpenAPI** |
| POST /api/workflow/stages/2/execute | No | Yes (/api/workflow/stages) | **Missing from OpenAPI** |
| GET /api/workflow/stages/:stage/jobs/:job_id/status | No | Yes (/api/workflow/stages) | **Missing from OpenAPI** |
| GET /api/ai/feedback/pending/list | No | Yes (/api/ai/feedback, ADMIN) | **Missing from OpenAPI** |
| PUT /api/ai/feedback/:id/review | No | Yes (/api/ai/feedback, ADMIN) | **Missing from OpenAPI** |
| PATCH /api/hub/workflow-runs/:runId/steps/:stepDbId | No | Yes (/api/hub) | **Missing from OpenAPI** |
| POST /api/export/manifest | Yes | No (bundle manifest is GET /api/ros/export/manifest/:requestId) | **In OpenAPI but not mounted**; real API differs |

## Plan

- **Fix OpenAPI manually** for the critical stagewise/preflight endpoints (small scope): add the missing paths above so docs match reality.
- **Optional later**: add a generation step (e.g. from route metadata or tests) to keep OpenAPI in sync; out of scope for this audit.

## Minimal patch

Apply the suggested additions in the repo (see openapi.json patch) for:

- `/api/dev-auth/login` (POST)
- `/api/workflow/stages/{stageId}/approve-ai` (POST)
- `/api/workflow/stages/{stage}/execute` (POST)
- `/api/workflow/stages/{stage}/jobs/{job_id}/status` (GET)
- `/api/ai/feedback/pending/list` (GET)
- `/api/ai/feedback/{id}/review` (PUT)
- `/api/hub/workflow-runs/{runId}/steps/{stepDbId}` (PATCH)

Either remove or relabel `POST /api/export/manifest` in OpenAPI (e.g. deprecate or point to `/api/ros/export` bundle flow) to avoid confusion.
