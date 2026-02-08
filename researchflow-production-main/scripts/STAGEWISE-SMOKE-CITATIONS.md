# Stagewise Execution + Accept AI Suggestions — Strict Citations

**Repo:** ry86pkqf74-rgb/ROS_FLOW_2_1 (main)

---

## Step 0 — Docker entrypoint

**Source:** `researchflow-production-main/services/orchestrator/Dockerfile`

- **Production stage** runs compiled JavaScript:
  - **CMD (verbatim):** `CMD ["node", "dist/index.js"]`
- Build compiles from root `index.ts` (line 127):  
  `RUN npx tsc --project tsconfig.json || npx tsc --skipLibCheck --outDir dist --rootDir . index.ts`
- **Conclusion:** Container starts from **`services/orchestrator/index.ts`** (compiled to `dist/index.js`).  
- **Canonical mount file:** `services/orchestrator/routes.ts` — because `index.ts` does `import { registerRoutes } from "./routes";` and `await registerRoutes(httpServer, app);` (lines 9, 354). All `app.use(...)` for the routers below live inside `registerRoutes()` in **`routes.ts`**.

---

## Step 1 — Prove mounts (verbatim)

**File:** `services/orchestrator/routes.ts`

**Imports (verbatim):**
```ts
import aiFeedbackRouter from "./src/routes/ai-feedback";
import manuscriptGenerationRouter from "./src/routes/manuscript-generation";
import hubRouter from "./src/routes/hub";
import workflowStagesRouter from "./src/routes/workflow-stages";
import workflowStagesExecuteRouter from "./src/routes/workflow/stages";
```
(Lines 85, 105, 129, 144–145.)

**Mount lines (verbatim):**
```ts
app.use("/api/ai/feedback", aiFeedbackRouter);
app.use("/api/manuscript", manuscriptGenerationRouter);
app.use("/api/hub", hubRouter);
app.use("/api/workflow", workflowStagesRouter);
app.use("/api/workflow/stages", workflowStagesExecuteRouter);  // BullMQ stage execution (Stage 2+)
```
(Lines 996, 1040, 1086, 1100, 1101.)

---

## Step 2 — Hub submounts

**File:** `services/orchestrator/src/routes/hub/index.ts`

**Verbatim:**
```ts
router.use('/workflow-runs', workflowRunsRoutes);
```
(Line 32.)  
Import: `import workflowRunsRoutes from './workflow-runs';` (line 19).

---

## Step 3 — Endpoints (cited only)

| Module | METHOD | Full path | Auth | Purpose | Citation (router line) |
|--------|--------|-----------|------|---------|------------------------|
| **hub/workflow-runs.ts** | GET | `/api/hub/workflow-runs` | none | List workflow runs | `router.get('/', async ...)` (57) |
| | GET | `/api/hub/workflow-runs/stats` | none | Run statistics | `router.get('/stats', ...)` (136) |
| | POST | `/api/hub/workflow-runs` | none | Create run | `router.post('/', ...)` (216), CreateRunSchema |
| | GET | `/api/hub/workflow-runs/:runId` | none | Get run + steps | `router.get('/:runId', ...)` (256) |
| | PATCH | `/api/hub/workflow-runs/:runId` | none | Update run | `router.patch('/:runId', ...)` (301), UpdateRunSchema |
| | POST | `/api/hub/workflow-runs/:runId/start` | none | Start run | `router.post('/:runId/start', ...)` (374) |
| | POST | `/api/hub/workflow-runs/:runId/cancel` | none | Cancel run | `router.post('/:runId/cancel', ...)` (404) |
| | POST | `/api/hub/workflow-runs/:runId/steps` | none | Add step | `router.post('/:runId/steps', ...)` (435), CreateStepSchema |
| | PATCH | `/api/hub/workflow-runs/:runId/steps/:stepDbId` | none | Update step (persist outputs) | `router.patch('/:runId/steps/:stepDbId', ...)` (471), UpdateStepSchema |
| **ai-feedback.ts** | POST | `/api/ai/feedback` | requirePermission('ANALYZE') | Submit feedback | `router.post('/', requirePermission('ANALYZE'), ...)` (27) |
| | GET | `/api/ai/feedback/stats` | requireRole('STEWARD') | Aggregated stats | `router.get('/stats', requireRole('STEWARD'), ...)` (160) |
| | GET | `/api/ai/feedback/:invocationId` | requireRole('STEWARD') | Feedback for invocation | `router.get('/:invocationId', requireRole('STEWARD'), ...)` (252) |
| | PUT | `/api/ai/feedback/:id/review` | requireRole('ADMIN') | Mark feedback reviewed | `router.put('/:id/review', requireRole('ADMIN'), ...)` (318) |
| | GET | `/api/ai/feedback/pending/list` | requireRole('ADMIN') | Pending feedback list | `router.get('/pending/list', requireRole('ADMIN'), ...)` (386) |
| | POST | `/api/ai/feedback/rag/rebuild` | requireRole('STEWARD') | Rebuild RAG | `router.post('/rag/rebuild', requireRole('STEWARD'), ...)` (436) |
| **manuscript-generation.ts** | POST | `/api/manuscript/generate/results` | none | Results scaffold | `router.post('/generate/results', ...)` (40) |
| | POST | `/api/manuscript/generate/discussion` | none | Discussion | `router.post('/generate/discussion', ...)` (114) |
| | POST | `/api/manuscript/generate/title-keywords` | none | Title/keywords | `router.post('/generate/title-keywords', ...)` (185) |
| | POST | `/api/manuscript/generate/full` | none | Full manuscript | `router.post('/generate/full', ...)` (262) |
| | POST | `/api/manuscript/validate/section` | none | Validate section | `router.post('/validate/section', ...)` (384) |
| | POST | `/api/manuscript/generate/gated-full` | requireAuth | Gated full | `router.post('/generate/gated-full', requireAuth, ...)` (432) |
| | POST | `/api/manuscript/generate/gated-section` | requireAuth | Gated section | `router.post('/generate/gated-section', requireAuth, ...)` (527) |
| | GET | `/api/manuscript/budgets` | none | Word budgets | `router.get('/budgets', ...)` (590) |
| **workflow-stages.ts** | GET | `/api/workflow/stages` | none | All stage groups | `router.get('/stages', ...)` (74) |
| | GET | `/api/workflow/stages/:stageId` | none | One stage | `router.get('/stages/:stageId', ...)` (107) |
| | POST | `/api/workflow/stages/:stageId/approve-ai` | none | Approve AI for stage | `router.post('/stages/:stageId/approve-ai', ...)` (145) |
| | POST | `/api/workflow/stages/:stageId/revoke-ai` | none | Revoke AI | `router.post('/stages/:stageId/revoke-ai', ...)` (180) |
| | POST | `/api/workflow/stages/:stageId/attest` | none | Attest gate | `router.post('/stages/:stageId/attest', ...)` (211) |
| | POST | `/api/workflow/stages/:stageId/complete` | none | Mark stage complete | `router.post('/stages/:stageId/complete', ...)` (247) |
| | GET | `/api/workflow/lifecycle` | none | Lifecycle state | `router.get('/lifecycle', ...)` (289) |
| | POST | `/api/workflow/lifecycle/transition` | none | Transition state | `router.post('/lifecycle/transition', ...)` (310) |
| | GET | `/api/workflow/audit-log` | none | Audit log | `router.get('/audit-log', ...)` (344) |
| | POST | `/api/workflow/reset` | none | Reset session | `router.post('/reset', ...)` (365) |
| | GET | `/api/workflow/stages/:id/requirements` | none | Stage requirements | `router.get('/stages/:id/requirements', ...)` (385) |
| | POST | `/api/workflow/stages/:id/validate` | none | Validate stage | `router.post('/stages/:id/validate', ...)` (408) |
| | POST | `/api/workflow/stages/:id/complete` | none | Complete (alt) | `router.post('/stages/:id/complete', ...)` (429) |
| **workflow/stages.ts** | POST | `/api/workflow/stages/2/execute` | requireAuth | Queue Stage 2 job | `router.post('/2/execute', requireAuth, ...)` (124), Stage2ExecuteSchema |
| | GET | `/api/workflow/stages/:stage/jobs/:job_id/status` | requireAuth | Job status (poll) | `router.get('/:stage/jobs/:job_id/status', requireAuth, ...)` (199) |
| | GET | `/api/workflow/stages/:stage/jobs/:job_id/stream` | requireAuth | SSE stream | `router.get('/:stage/jobs/:job_id/stream', requireAuth, ...)` (247) |

**Health (used by smoke script):**  
- `index.ts`: `app.use(healthRouter);` and `app.use("/api", healthRouter);`  
- `src/routes/health.ts`: `router.get("/health", ...)`  
→ **GET /health** and **GET /api/health** (Dockerfile HEALTHCHECK: `curl -fsS http://localhost:3001/health`).

---

## Step 4 — Dispatch points

**queue.add (workflow/stages.ts):**
```ts
const job = await queue.add(
  'stage-2-execute',
  {
    stage: 2,
    job_id,
    workflow_id,
    research_question,
    mode,
    risk_tier,
    domain_id,
    inputs,
    user_id: userId,
    timestamp: new Date().toISOString(),
  },
  {
    jobId: job_id,
    priority: 5,
  }
);
```
(Lines 147–166.)

**Worker downstream call (worker.ts):**
```ts
const endpoint = `${workerUrl}/api/workflow/stages/${job.data.stage}/execute`;

const response = await fetch(endpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
  },
  body: JSON.stringify({
    workflow_id: job.data.workflow_id,
    research_question: job.data.research_question,
    user_id: job.data.user_id,
    job_id: job.data.job_id,
  }),
});
```
(Lines 925–942; `workerUrl = process.env.WORKER_URL || 'http://worker:8000'`.)

---

## Step 5 — “Accept AI suggestion” in code terms

1. **Does PUT /api/ai/feedback/:id/review modify workflow/stage outputs?**  
   **No.** It only updates the **AI feedback** row:
   - **DB update (verbatim):**  
     `services/orchestrator/src/routes/ai-feedback.ts` (336–347):
     ```ts
     const [updated] = await db
       .update(aiOutputFeedback)
       .set({
         reviewedByAdmin: true,
         reviewedAt: new Date(),
         isUsefulForTraining: isUsefulForTraining !== undefined ? isUsefulForTraining : undefined,
         reviewNotes: reviewNotes || null
       })
       .where(eq(aiOutputFeedback.id, id))
       .returning();
     ```
   So it does **not** touch workflow runs or stage outputs.

2. **Is there a dedicated “accept output” endpoint?**  
   There is no single endpoint named “accept output.” The **closest** is:

3. **Endpoint that persists chosen output (run step):**  
   **PATCH /api/hub/workflow-runs/:runId/steps/:stepDbId**  
   - **File:** `services/orchestrator/src/routes/hub/workflow-runs.ts`  
   - **Handler:** `router.patch('/:runId/steps/:stepDbId', async ...)` (471).  
   - **Schema:** UpdateStepSchema: `{ status?, outputs?, errorMessage? }`.  
   - **UPDATE (verbatim):**  
     ```ts
     const result = await pool.query(
       `UPDATE workflow_run_steps SET ${updates.join(', ')}
        WHERE id = $${paramIndex} AND run_id = $${paramIndex + 1}
        RETURNING *`,
       values
     );
     ```
     (Lines 437–441; `updates` includes `outputs = $n` when `input.outputs` is provided.)

So “accept AI suggestion” for **workflow run steps** = call this PATCH with the chosen `outputs` (and optionally `status: 'completed'`).

---

## Step 6 — Runnable script and how to run

- **Script:** `researchflow-production-main/scripts/stagewise-smoke.sh`
- Uses only endpoints cited above; prints request/response on failure and exits non-zero on failure.

**Required env vars:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_URL` | No | `http://127.0.0.1:3001` | Orchestrator base URL |
| `AUTH_HEADER` | Yes for execute/status/pending/review | (none) | e.g. `Authorization: Bearer <jwt>`; ADMIN for pending list + review |
| `RUN_ID` | No (for step 7) | (none) | Hub workflow run UUID to PATCH step |
| `STEP_DB_ID` | No (for step 7) | (none) | workflow_run_steps row id for PATCH |

**Example (server-local):**
```bash
cd researchflow-production-main
chmod +x scripts/stagewise-smoke.sh

# With auth (obtain token from login first)
export AUTH_HEADER="Authorization: Bearer YOUR_JWT"
./scripts/stagewise-smoke.sh

# Optional: override URL
ORCHESTRATOR_URL=http://127.0.0.1:3001 ./scripts/stagewise-smoke.sh
```

**On Hetzner (orchestrator on same host or reachable URL):**
```bash
# Orchestrator reachable at e.g. https://api.example.com
export ORCHESTRATOR_URL="https://api.example.com"
export AUTH_HEADER="Authorization: Bearer YOUR_JWT"
./scripts/stagewise-smoke.sh
```

If `AUTH_HEADER` is missing, the script fails with a clear message when it hits the Stage 2 execute step (requireAuth). For pending list and review, ADMIN role is required (requireRole('ADMIN')).

**Inferred request bodies (from handler validation):**
- **POST /api/workflow/stages/2/execute:** `Stage2ExecuteSchema` in `workflow/stages.ts` (75–82): `workflow_id` (uuid), `research_question` (min 10 chars), `mode`, `risk_tier`, `domain_id`, `inputs` optional.
- **PUT /api/ai/feedback/:id/review:** body optional; `isUsefulForTraining` (boolean), `reviewNotes` (string) per handler (334).
- **PATCH /api/hub/workflow-runs/:runId/steps/:stepDbId:** `UpdateStepSchema`: `status`, `outputs`, `errorMessage` optional (workflow-runs.ts 47–51).
