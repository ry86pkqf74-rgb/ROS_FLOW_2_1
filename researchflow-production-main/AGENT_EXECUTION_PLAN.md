# Agent Execution Plan: ResearchFlow Production Fixes
**Date:** 2026-02-03
**Phases:** 6 total, parallel execution where possible

---

## PHASE 1: Docker Production Fix (COMPOSIO)

### Prompt for Composio:

```
TASK: Fix Docker Production Configuration - CRITICAL BLOCKING ISSUES

Repository: researchflow-production
Branch: main (commit directly after each fix)

FIXES REQUIRED:

1. FILE: docker-compose.prod.yml

   a) Line ~333 - Fix nginx config mount:
   CHANGE: ./services/web/nginx.conf:/etc/nginx/nginx.conf:ro
   TO: ./infrastructure/docker/nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro

   b) Line ~337-338 - Add web service to backend network:
   ADD under web service networks:
     - backend

   c) Lines ~110-111, 331-332 - Fix SSL cert paths:
   ENSURE paths match:
     - ./infrastructure/docker/nginx/ssl/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
     - ./infrastructure/docker/nginx/ssl/privkey.pem:/etc/nginx/ssl/privkey.pem:ro

   d) Lines ~112-148 - Add orchestrator environment variables:
   ADD:
     - WORKER_URL=http://worker:8000
     - ROS_API_URL=http://worker:8000
     - WORKER_CALLBACK_URL=http://worker:8000

   e) Lines ~149-157 - Add orchestrator depends_on:
   ADD:
     depends_on:
       - worker
       - redis
       - postgres

   f) Lines ~204-224 - Add worker environment variables:
   ADD:
     - ORCHESTRATOR_URL=http://orchestrator:3001
     - AI_ROUTER_URL=http://orchestrator:3001/api/ai/extraction/generate

COMMIT MESSAGE: fix(docker): resolve production configuration blocking issues
```

---

## PHASE 2: Route Registration Fix (COMPOSIO)

### Prompt for Composio:

```
TASK: Fix Route Registration Issues

Repository: researchflow-production
Branch: main

FIXES REQUIRED:

1. FILE: services/orchestrator/src/routes/notifications.ts
   
   ISSUE: Exports factory function, not Router instance
   
   ADD at end of file (before final closing brace if inside module):
   
   // Default export for direct route registration
   import { pool } from '../db';
   export default createNotificationsRouter({ pool });

2. FILE: services/worker/api_server.py

   ISSUE: manuscript_generate router not registered
   
   ADD import near top with other router imports:
   from src.api.routes.manuscript_generate import router as manuscript_generate_router
   
   ADD registration after other app.include_router calls:
   app.include_router(manuscript_generate_router, prefix="/api")

3. FILE: services/orchestrator/src/services/embeddingService.ts
   
   LINE 24 - CHANGE:
   FROM: const WORKER_URL = process.env.WORKER_URL || 'http://worker:8001';
   TO: const WORKER_URL = process.env.WORKER_URL || 'http://worker:8000';

4. FILE: services/orchestrator/src/services/semanticSearchService.ts
   
   LINE 32 - CHANGE:
   FROM: const WORKER_URL = process.env.WORKER_URL || 'http://worker:8001';
   TO: const WORKER_URL = process.env.WORKER_URL || 'http://worker:8000';

COMMIT MESSAGE: fix(routes): resolve route registration and port mismatch issues
```

---

## PHASE 3: Security Hardening (COMPOSIO)

### Prompt for Composio:

```
TASK: Fix Authentication Security Issues

Repository: researchflow-production
Branch: main

FIXES REQUIRED:

1. FILE: services/orchestrator/src/services/authService.ts

   a) Lines 188, 239 - Remove hardcoded dev secret:
   FIND: any hardcoded JWT secret like 'development-secret' or similar
   CHANGE TO: throw new Error('JWT_SECRET must be set in environment')
   
   b) Lines 661-681 - Hash password reset tokens before storing:
   ADD import: import crypto from 'crypto';
   
   BEFORE storing reset token:
   const hashedToken = crypto.createHash('sha256').update(token).digest('hex');
   // Store hashedToken instead of plain token

2. FILE: services/orchestrator/src/routes/auth.ts

   a) Line 517 - Remove token from logs:
   FIND: any console.log or logger call that includes the reset token
   REMOVE or replace token value with '[REDACTED]'
   
   b) Add rate limiting to auth endpoints:
   ADD import: import rateLimit from 'express-rate-limit';
   
   ADD before auth routes:
   const authLimiter = rateLimit({
     windowMs: 15 * 60 * 1000, // 15 minutes
     max: 5, // 5 attempts per window
     message: { error: 'Too many attempts, please try again later' }
   });
   
   APPLY to: /login, /register, /forgot-password, /reset-password routes

3. FILE: services/orchestrator/src/services/sessionService.ts

   Lines 22-23 - Add TODO comment for Redis migration:
   ADD COMMENT:
   // TODO: Replace in-memory store with Redis for production
   // Use: import { createClient } from 'redis';

COMMIT MESSAGE: fix(security): harden authentication and remove sensitive data exposure
```

---

## PHASE 4: Frontend Consolidation (CURSOR)

### Prompt for Cursor:

```
TASK: Consolidate Frontend API Clients and Fix Environment Variables

Repository: researchflow-production
Focus: services/web/src/

FIXES REQUIRED:

1. STANDARDIZE ENVIRONMENT VARIABLES

   Search all files in services/web/src/ for VITE_API_URL
   REPLACE ALL occurrences with VITE_API_BASE_URL
   
   Files known to need fixing:
   - components/hub/HubTaskBoard.tsx
   - components/hub/HubDashboard.tsx
   - components/hub/HubTimeline.tsx
   - components/hub/HubGoalTracker.tsx

2. CONSOLIDATE API CLIENTS

   KEEP: services/web/src/lib/api/client.ts (class-based with retry)
   
   UPDATE: services/web/src/api/client.ts
   ADD at top: 
   // DEPRECATED: Use @/lib/api/client instead
   // This file maintained for backward compatibility
   import { apiClient } from '@/lib/api/client';
   export { apiClient };
   
   UPDATE: services/web/src/lib/api-client.ts
   ADD at top:
   // DEPRECATED: Use @/lib/api/client instead
   export * from './api/client';

3. ADD WEBSOCKET AUTHENTICATION

   FILE: services/web/src/hooks/use-collaborative-editing.ts
   
   Line ~112 - Find getToken parameter and USE it:
   
   ADD authentication to WebSocket connection:
   const token = await getToken?.();
   // Add token to connection params or headers

COMMIT MESSAGE: fix(web): standardize API client usage and environment variables
```

---

## PHASE 5: Workflow Engine Foundation (BOTH)

### Prompt for Composio (Backend):

```
TASK: Create Workflow Engine Foundation - Backend

Repository: researchflow-production
Branch: main

CREATE NEW FILES:

1. FILE: config/workflows/workflow_20_stage.yaml

   Create workflow definition with this structure:
   
   workflow:
     name: "ResearchFlow 20-Stage Pipeline"
     version: "1.0.0"
     
   stages:
     - id: "stage_01"
       name: "Upload Intake"
       phase: 1
       inputs: ["file", "config"]
       outputs: ["metadata", "artifacts"]
       gates: []
       allowed_modes: ["STANDBY", "SANDBOX", "ACTIVE"]
       runner: "services/worker/src/workflow_engine/stages/stage_01_upload.py"
       deterministic: true
       
     # Add entries for stages 02-20 following same pattern
     # Use STAGES.md as reference for each stage's purpose

2. FILE: services/orchestrator/src/workflow/engine.ts

   Create workflow runtime with:
   - loadWorkflowDefinition(yamlPath): Load and parse YAML
   - createRun(userId, workflowId): Create run_id, workspace
   - executeStage(runId, stageId): Run stage, emit artifacts
   - getRunStatus(runId): Return current state
   - Artifact storage under: .tmp/workspaces/<user_id>/<run_id>/
   - Manifest generation: manifests/<stage_id>.json

3. FILE: services/orchestrator/src/routes/workflow.ts

   Create API routes:
   - POST /api/workflow/runs - Create new run
   - GET /api/workflow/runs/:runId - Get run status
   - POST /api/workflow/runs/:runId/stages/:stageId/execute - Execute stage
   - GET /api/workflow/runs/:runId/artifacts - List artifacts

COMMIT MESSAGE: feat(workflow): add workflow engine foundation with stage registry
```

### Prompt for Cursor (Frontend):

```
TASK: Create Workflow Engine UI Components

Repository: researchflow-production
Focus: services/web/src/

CREATE NEW FILES:

1. FILE: services/web/src/components/workflow/WorkflowRunner.tsx

   Create component that:
   - Loads workflow definition from API
   - Shows all 20 stages as cards with status
   - Displays prerequisites/dependencies between stages
   - "Run Stage" button calls workflow API
   - Shows stage outputs from artifacts
   - Progress indicator for running stages

2. FILE: services/web/src/components/workflow/StageCard.tsx

   Create reusable stage card with:
   - Stage name, number, phase
   - Status indicator (pending, running, completed, failed)
   - Prerequisites list
   - Input/output summary
   - Run/view buttons

3. FILE: services/web/src/hooks/useWorkflow.ts

   Create hook for workflow state:
   - createRun(): Start new workflow run
   - executeStage(stageId): Run specific stage
   - getRunStatus(): Poll for updates
   - getArtifacts(): Fetch stage outputs

4. FILE: services/web/src/stores/workflowStore.ts

   Create Zustand store for:
   - Current run ID
   - Stage statuses
   - Artifacts by stage
   - Error states

COMMIT MESSAGE: feat(web): add workflow runner UI components
```

---

## PHASE 6: E2E Pipeline Test (CURSOR)

### Prompt for Cursor:

```
TASK: Create End-to-End 20-Stage Pipeline Test

Repository: researchflow-production
Focus: tests/e2e/

CREATE NEW FILES:

1. FILE: tests/e2e/fixtures/synthetic-study-data.json

   Create synthetic research data for testing:
   {
     "study": {
       "title": "Test Clinical Study",
       "type": "randomized_controlled_trial",
       "hypothesis": "Treatment X improves outcome Y"
     },
     "data": {
       "participants": 100,
       "variables": ["age", "treatment", "outcome"],
       "synthetic_rows": [/* 100 rows of fake data */]
     },
     "config": {
       "phi_mode": "DEMO",
       "seed": 42
     }
   }

2. FILE: tests/e2e/full-pipeline.spec.ts

   Create Playwright test that:
   
   test.describe('Full 20-Stage Pipeline', () => {
     test.describe.configure({ timeout: 300000 }); // 5 min timeout
     
     test('completes all stages with synthetic data', async ({ request }) => {
       // 1. Create workflow run
       const run = await request.post('/api/workflow/runs', {
         data: syntheticStudyData
       });
       const runId = run.runId;
       
       // 2. Execute each stage in order
       for (const stageId of stages_01_to_20) {
         const result = await request.post(
           `/api/workflow/runs/${runId}/stages/${stageId}/execute`
         );
         expect(result.status).toBe('completed');
         
         // 3. Verify artifacts created
         const artifacts = await request.get(
           `/api/workflow/runs/${runId}/stages/${stageId}/artifacts`
         );
         expect(artifacts.files.length).toBeGreaterThan(0);
       }
       
       // 4. Verify final outputs exist
       const finalArtifacts = await request.get(
         `/api/workflow/runs/${runId}/artifacts`
       );
       expect(finalArtifacts).toHaveProperty('irb_document');
       expect(finalArtifacts).toHaveProperty('manuscript_draft');
       expect(finalArtifacts).toHaveProperty('conference_materials');
     });
   });

3. FILE: tests/e2e/stage-isolation.spec.ts

   Test each stage can run independently:
   - Stage prerequisites enforced
   - Artifacts properly isolated
   - PHI gates working in DEMO mode

COMMIT MESSAGE: test(e2e): add full 20-stage pipeline integration test
```

---

## Execution Order

### Parallel Execution Group 1 (Immediate):
- **Composio:** Phase 1 (Docker) + Phase 2 (Routes)
- **Cursor:** Phase 4 (Frontend consolidation)

### Parallel Execution Group 2 (After Group 1):
- **Composio:** Phase 3 (Security)
- **Cursor:** Start Phase 6 (E2E test fixtures)

### Sequential (After Group 2):
- **Both:** Phase 5 (Workflow Engine) - coordinate on API contract first

---

## Verification Checklist

After all phases complete:

- [ ] `docker-compose -f docker-compose.prod.yml up` starts all services
- [ ] All services can communicate (orchestrator ↔ worker ↔ web)
- [ ] `/api/manuscript/generate` returns 200 (not 404)
- [ ] `/api/notifications` routes work
- [ ] No hardcoded secrets in auth code
- [ ] Single API client pattern in frontend
- [ ] Workflow API endpoints respond
- [ ] E2E pipeline test passes in CI
