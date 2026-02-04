# Step 4 Testing Commands

## Current Status
✅ TypeScript syntax validated (all Step 3 & 4 files compile)
✅ Dependencies installed via pnpm
✅ Guideline-engine Dockerfile fixed (PIP_REQUIRE_HASHES=0)
⏳ Docker build in progress (orchestrator service had network timeout on npm install)

---

## A. Retry Docker Build (if previous build failed)

The previous build failed due to network timeout. Retry with:

```bash
cd researchflow-production-main
docker compose build orchestrator --no-cache
```

If that still times out, try building without cache and with retries:

```bash
docker compose build orchestrator
```

---

## B. Start Services

```bash
cd researchflow-production-main
docker compose up orchestrator redis -d
```

Wait for services to start (check every 5 seconds):

```bash
docker compose ps
```

Expected output:
```
NAME                    STATUS
orchestrator            Up (healthy)
redis                   Up (healthy)
```

If not healthy, check logs:

```bash
docker compose logs orchestrator --tail=100
```

---

## C. Test 1: Minimal Request (All Defaults)

```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "job_id": "<uuid>",
  "stage": 2,
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Stage 2 execution job has been queued",
  "routing": {
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "domain_id": "clinical"
  },
  "normalized_inputs": {
    "databases": ["pubmed"],
    "max_results": 25,
    "language": "en",
    "dedupe": true,
    "require_abstract": true
  }
}
```

✅ **Pass Criteria:**
- `success: true`
- `routing` object present with defaults
- `normalized_inputs` has all defaults filled in

---

## D. Test 2: Custom Inputs Request

```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "mode": "LIVE",
    "risk_tier": "PHI",
    "domain_id": "clinical",
    "inputs": {
      "databases": ["pubmed", "semantic_scholar"],
      "max_results": 50,
      "year_range": {
        "from": 2020,
        "to": 2024
      },
      "study_types": ["randomized_controlled_trial", "systematic_review"],
      "mesh_terms": ["Hypertension", "Antihypertensive Agents"],
      "language": "en",
      "dedupe": true,
      "require_abstract": true
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "job_id": "<uuid>",
  "stage": 2,
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Stage 2 execution job has been queued",
  "routing": {
    "mode": "LIVE",
    "risk_tier": "PHI",
    "domain_id": "clinical"
  },
  "normalized_inputs": {
    "databases": ["pubmed", "semantic_scholar"],
    "max_results": 50,
    "year_range": {
      "from": 2020,
      "to": 2024
    },
    "study_types": ["randomized_controlled_trial", "systematic_review"],
    "mesh_terms": ["Hypertension", "Antihypertensive Agents"],
    "language": "en",
    "dedupe": true,
    "require_abstract": true
  }
}
```

✅ **Pass Criteria:**
- `routing` matches your input (`LIVE`, `PHI`, `clinical`)
- `normalized_inputs` contains your custom values

---

## E. Test 3: Validation Error - max_results Too High

```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "max_results": 500
    }
  }'
```

**Expected Response:** `400 Bad Request`

```json
{
  "error": "Invalid request body",
  "details": [
    {
      "code": "too_big",
      "path": ["inputs", "max_results"],
      "message": "Number must be less than or equal to 200"
    }
  ]
}
```

✅ **Pass Criteria:** 400 status with validation error mentioning `max_results`

---

## F. Test 4: Validation Error - Invalid Database

```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "databases": ["invalid_db"]
    }
  }'
```

**Expected Response:** `400 Bad Request` with validation error

✅ **Pass Criteria:** 400 status with error about invalid enum value for `databases`

---

## G. Test 5: Validation Error - Invalid study_type

```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "study_types": ["invalid_study_type"]
    }
  }'
```

**Expected Response:** `400 Bad Request`

✅ **Pass Criteria:** 400 status with validation error about `study_types`

---

## H. Test 6: Check Job Status

Replace `<JOB_ID>` with the `job_id` returned from Test 1 or 2:

```bash
curl -X GET http://localhost:3001/api/workflow/stages/2/jobs/<JOB_ID>/status \
  -H "Authorization: Bearer test-token"
```

**Expected Response:**
```json
{
  "job_id": "<uuid>",
  "stage": 2,
  "status": "waiting",
  "progress": 0,
  "data": {
    "stage": 2,
    "job_id": "<uuid>",
    "workflow_id": "<uuid>",
    "research_question": "...",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "domain_id": "clinical",
    "inputs": { ... },
    "user_id": "...",
    "timestamp": "..."
  },
  "created_at": 1234567890
}
```

✅ **Pass Criteria:**
- Job exists (not 404)
- `data` object contains `mode`, `risk_tier`, `domain_id`, `inputs`

---

## I. View Orchestrator Logs

```bash
cd researchflow-production-main
docker compose logs orchestrator --tail=100 -f
```

Look for log lines like:
```
[Stage 2] Job <uuid> dispatched for workflow <uuid> (DEMO/NON_SENSITIVE/clinical)
```

✅ **Pass Criteria:** Log shows routing metadata in format `(mode/risk_tier/domain_id)`

---

## J. Check Environment (Optional)

If auth is failing, check if mock auth is enabled:

```bash
grep ALLOW_MOCK_AUTH researchflow-production-main/.env
```

If not set, you may need to:
1. Add `ALLOW_MOCK_AUTH=true` to `.env`
2. Restart: `docker compose restart orchestrator`

---

## K. Cleanup (After Testing)

```bash
cd researchflow-production-main
docker compose down
```

---

## Summary Checklist

After running all tests:

- [ ] Test 1 (minimal) returns `success: true` with routing & normalized_inputs
- [ ] Test 2 (custom) echoes custom routing values
- [ ] Test 3 (max_results=500) returns 400 validation error
- [ ] Test 4 (invalid_db) returns 400 validation error
- [ ] Test 5 (invalid_study_type) returns 400 validation error
- [ ] Test 6 (job status) returns job with deterministic payload
- [ ] Logs show `(mode/risk_tier/domain_id)` routing info

---

## If Build Still Fails

### Network Timeout on npm install

Try:
```bash
docker compose build orchestrator --build-arg NPM_REGISTRY=https://registry.npmjs.org
```

Or build with increased timeout:
```bash
COMPOSE_HTTP_TIMEOUT=600 docker compose build orchestrator
```

### Alternative: Run orchestrator locally (skip Docker for now)

```bash
cd researchflow-production-main/services/orchestrator
export REDIS_URL=redis://localhost:6379
export ALLOW_MOCK_AUTH=true
export NODE_ENV=development
pnpm dev
```

Then run the curl commands against `http://localhost:3001`.

---

## Next Step After Step 4 Passes

✅ **Step 5: Compose Merge** - Update docker-compose.yml to include agent services and environment variables.
