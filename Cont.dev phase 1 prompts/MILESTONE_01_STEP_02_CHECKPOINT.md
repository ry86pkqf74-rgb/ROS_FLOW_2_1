# Milestone 1 - Step 2 Checkpoint

## Changes Applied

**File Modified**: `services/orchestrator/src/routes/ai-router.ts`

### 1. Added DispatchRequestSchema
```typescript
const DispatchRequestSchema = z.object({
  task_type: z.string(),
  request_id: z.string().min(1),
  workflow_id: z.string().optional(),
  user_id: z.string().optional(),
  mode: z.enum(['DEMO', 'LIVE']).optional(),
  risk_tier: z.enum(['PHI', 'SENSITIVE', 'NON_SENSITIVE']).optional(),
  domain_id: z.string().optional(),
  inputs: z.record(z.any()).optional(),
  budgets: z.record(z.any()).optional(),
});
```

### 2. Added AGENT_ENDPOINTS_JSON Parsing
- Parses at module initialization
- Format: `{"agent-stage2-lit": "http://agent-stage2-lit:8010"}`
- Logs warning if missing, error if invalid JSON
- Returns empty object on failure

### 3. Added POST /api/ai/router/dispatch Endpoint
- **Auth**: Uses `requirePermission('ANALYZE')` (consistent with `/route` endpoint)
- **Validation**: Validates request body with DispatchRequestSchema
- **Routing**: Milestone 1 only supports `task_type === "STAGE_2_LITERATURE_REVIEW"`
- **Agent Mapping**: Maps to `agent_name="agent-stage2-lit"`
- **URL Resolution**: Resolves from AGENT_ENDPOINTS_JSON
- **Audit Logging**: Logs dispatch decision with eventType='AI_ROUTING', action='DISPATCH_REQUESTED'
- **Response**: Returns dispatch plan with agent_name, agent_url, budgets, rag_plan, request_id

### Error Handling
- 401: Missing authentication
- 400: Invalid request body (VALIDATION_ERROR)
- 400: Unsupported task type (UNSUPPORTED_TASK_TYPE)
- 500: Agent not configured (AGENT_NOT_CONFIGURED)

## TypeScript Validation

```bash
cd services/orchestrator
npx tsc --noEmit
```

✅ **Status**: No TypeScript errors

## Environment Variable Required

Add to orchestrator `.env`:
```bash
AGENT_ENDPOINTS_JSON='{"agent-stage2-lit":"http://agent-stage2-lit:8010"}'
```

## Test Command (Inside Orchestrator Container)

```bash
# Assuming you have auth token
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "test-req-001",
    "workflow_id": "wf-123",
    "user_id": "user-456",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "domain_id": "clinical",
    "inputs": {
      "query": "COVID-19 treatments",
      "max_results": 25
    },
    "budgets": {
      "max_tokens": 10000
    }
  }'

# Expected Response:
{
  "dispatch_type": "agent",
  "agent_name": "agent-stage2-lit",
  "agent_url": "http://agent-stage2-lit:8010",
  "budgets": {
    "max_tokens": 10000
  },
  "rag_plan": {},
  "request_id": "test-req-001"
}
```

## Next Steps

- Step 3: Patch BullMQ Stage Worker (Stage 2 only)
- Add `isMigratedStage()` guard
- Call AgentClient.postSync() for stage 2
