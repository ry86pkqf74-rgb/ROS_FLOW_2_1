# STEP 4 CHECKPOINT: Stage 2 Deterministic Payload

## Summary
Extended Stage 2 execution schema to support deterministic job payloads with mode, risk_tier, domain_id, and comprehensive search parameters.

---

## Files Changed

### 1. `services/orchestrator/src/routes/workflow/stages.ts`

#### Added: Stage2InputsSchema
```typescript
const Stage2InputsSchema = z.object({
  query: z.string().optional(),
  databases: z.array(z.enum(['pubmed', 'semantic_scholar'])).default(['pubmed']),
  max_results: z.number().int().min(1).max(200).default(25),
  year_range: z.object({
    from: z.number().int().optional(),
    to: z.number().int().optional(),
  }).optional(),
  study_types: z.array(z.enum([
    'clinical_trial',
    'randomized_controlled_trial',
    'cohort_study',
    'case_control_study',
    'cross_sectional_study',
    'systematic_review',
    'meta_analysis',
    'case_report',
    'observational_study',
    'review'
  ])).optional(),
  mesh_terms: z.array(z.string()).optional(),
  include_keywords: z.array(z.string()).optional(),
  exclude_keywords: z.array(z.string()).optional(),
  language: z.string().default('en'),
  dedupe: z.boolean().default(true),
  require_abstract: z.boolean().default(true),
});
```

#### Extended: Stage2ExecuteSchema
Added fields:
- `mode: z.enum(['DEMO', 'LIVE']).default('DEMO')`
- `risk_tier: z.enum(['PHI', 'SENSITIVE', 'NON_SENSITIVE']).default('NON_SENSITIVE')`
- `domain_id: z.string().default('clinical')`
- `inputs: z.record(z.any()).optional()`

#### Modified: POST /api/workflow/stages/2/execute
- Parses and validates `inputs` using `Stage2InputsSchema` with defaults
- Includes `mode`, `risk_tier`, `domain_id`, and normalized `inputs` in queued job payload
- Returns `routing` object and `normalized_inputs` in response

**Response format:**
```json
{
  "success": true,
  "job_id": "uuid",
  "stage": 2,
  "workflow_id": "uuid",
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

---

## Environment Variables

### No new environment variables required
All fields use safe defaults:
- `mode`: defaults to `'DEMO'`
- `risk_tier`: defaults to `'NON_SENSITIVE'`
- `domain_id`: defaults to `'clinical'`
- `inputs`: uses `Stage2InputsSchema` defaults

---

## How to Test

### 1. TypeScript Compilation
```bash
cd services/orchestrator
npm run build
```

**Expected:** No TypeScript errors, clean compilation.

---

### 2. Test Minimal Request (All Defaults)
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
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

---

### 3. Test Request with Custom Inputs
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
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

---

### 4. Test Validation Errors

#### Invalid max_results (too high)
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "max_results": 500
    }
  }'
```

**Expected:** 400 Bad Request with validation error

#### Invalid database
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "databases": ["invalid_db"]
    }
  }'
```

**Expected:** 400 Bad Request with validation error

#### Invalid study_type
```bash
curl -X POST http://localhost:3001/api/workflow/stages/2/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{
    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
    "research_question": "What are effective treatments for hypertension?",
    "inputs": {
      "study_types": ["invalid_study_type"]
    }
  }'
```

**Expected:** 400 Bad Request with validation error

---

### 5. Check Job Payload in Queue

```bash
# Connect to Redis
redis-cli

# List jobs
KEYS bull:workflow-stages:*

# Inspect a specific job
GET bull:workflow-stages:stage-2-execute:<job_id>
```

**Expected Job Data:**
```json
{
  "stage": 2,
  "job_id": "<uuid>",
  "workflow_id": "<uuid>",
  "research_question": "...",
  "mode": "DEMO",
  "risk_tier": "NON_SENSITIVE",
  "domain_id": "clinical",
  "inputs": {
    "databases": ["pubmed"],
    "max_results": 25,
    "language": "en",
    "dedupe": true,
    "require_abstract": true
  },
  "user_id": "<user_id>",
  "timestamp": "<iso_timestamp>"
}
```

---

### 6. Check Logs

```bash
docker compose logs orchestrator | grep "Stage 2"
```

**Expected Log:**
```
[Stage 2] Job <job_id> dispatched for workflow <workflow_id> (DEMO/NON_SENSITIVE/clinical)
```

---

## Validation Checklist

- [ ] TypeScript compiles without errors
- [ ] Minimal request works with all defaults
- [ ] Custom inputs are parsed and normalized
- [ ] Invalid `max_results` (>200) returns 400
- [ ] Invalid `databases` returns 400
- [ ] Invalid `study_types` returns 400
- [ ] Response includes `routing` object
- [ ] Response includes `normalized_inputs` object
- [ ] Job payload in Redis includes `mode`, `risk_tier`, `domain_id`, `inputs`
- [ ] Logs show routing info: `(mode/risk_tier/domain_id)`

---

## PHI Safety Notes

✅ **No PHI concerns in this step:**
- Request body is not logged (only metadata)
- `research_question` is user-provided, not PHI
- Validation schemas enforce data structure only
- No sensitive data in response

---

## Next Steps

After confirming all tests pass:
1. Proceed to **Step 5**: Implement worker routing guard for Stage 2
2. Update worker to use AI router dispatch for Stage 2 jobs
3. Keep legacy worker path for other stages (guarded migration)

---

## Rollback Plan

If issues arise:
```bash
cd researchflow-production-main
git checkout HEAD -- services/orchestrator/src/routes/workflow/stages.ts
cd services/orchestrator
npm run build
docker compose restart orchestrator
```
