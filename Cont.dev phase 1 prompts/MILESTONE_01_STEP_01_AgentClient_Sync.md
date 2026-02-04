# Milestone 1 - Step 1: Add AgentClient (Node) - Sync Only

## Overview
Create a new synchronous agent client service for direct specialist execution in Stage 2 of the clinical research platform refactoring.

---

## Pre-Execution Checklist
- [ ] Review existing `services/orchestrator/src/clients/workerClient.ts` for pattern reference
- [ ] Verify TypeScript configuration is set to strict mode
- [ ] Confirm PHI safety logging guidelines
- [ ] Check current orchestrator test suite structure

---

## Conventions (Apply to All Steps)

### 1. Minimal Changes Only
- Request minimal diffs from the model
- No unrelated refactors
- Preserve existing patterns and structures

### 2. After Each Step - Validation
Run the following commands:
```bash
# TypeScript type checking
cd services/orchestrator && npm run typecheck

# Unit tests
npm test

# Docker compose validation
docker compose config
```

### 3. Model Output Requirements
Every code change must return:
- **File list touched**: Complete list of modified/created files
- **Exact patches/snippets**: Precise code changes (not placeholders)
- **New env vars required**: Any environment variables needed
- **Compile impacts**: TypeScript compilation changes or dependencies

---

## Agent Configuration

### Primary Agent: Architect (Claude Sonnet)
```json
{
  "name": "Architect",
  "model": "claude-sonnet-4-20250514",
  "systemPrompt": "You are refactoring a clinical research platform. Propose minimal, safe diffs. List exact file changes. Identify failure modes. Preserve PHI safety. TypeScript strict mode."
}
```

### Secondary Agent: Implementer (Mercury/Codex)
```json
{
  "name": "Implementer",
  "model": "mercury-coder",
  "systemPrompt": "Implement changes precisely. Do not modify unrelated code. Add unit tests. Run typecheck before completing. Follow existing patterns."
}
```

### Verification Agent: Verifier (Claude Sonnet)
```json
{
  "name": "Verifier",
  "model": "claude-sonnet-4-20250514",
  "systemPrompt": "Review for: PHI leaks, remaining WORKER_URL dependencies, OpenAI/Anthropic calls in local_only paths, missing error handling, type safety."
}
```

---

## Step 1 Prompt: Create AgentClient Service

### Target File
`services/orchestrator/src/clients/agentClient.ts`

### Full Prompt for Architect Agent

```
Create a new file services/orchestrator/src/clients/agentClient.ts. 

REQUIREMENTS:

1. Provide getAgentClient() singleton.
   - Must be thread-safe and reusable
   - Initialize once and return cached instance
   - Follow existing singleton patterns in the codebase

2. Provide postSync(agentBaseUrl, path, body, opts) method returning:
   {
     ok: boolean,
     status: number,
     data?: any,
     error?: string,
     duration_ms: number
   }
   - Must be synchronous operation only (no async/await in return chain)
   - Include request timing metrics
   - Handle all HTTP status codes appropriately

3. Include circuit breaker behavior:
   - Copy approach from services/orchestrator/src/clients/workerClient.ts
   - Do not copy identical implementation, adapt pattern as needed
   - Track failure rates and implement trip/reset logic
   - Configurable thresholds

4. Enforce timeouts:
   - Default timeout: 30 seconds (configurable)
   - Graceful timeout handling with clear error messages
   - No hanging requests

5. PHI Safety - CRITICAL:
   - NEVER log request bodies (may contain PHI)
   - NEVER log response bodies (may contain PHI)
   - Log only: URL paths, status codes, duration, error types
   - Sanitize all error messages before logging

6. TypeScript Requirements:
   - Strict mode compliant
   - No 'any' types unless absolutely unavoidable
   - Full type definitions for all parameters and return values
   - Proper error types

OUTPUT REQUIREMENTS:
- Full file content (complete, ready to use)
- List of any dependencies to add to package.json
- Interface definitions used
- Example usage code snippet
```

---

## Planned Tool Usage

### Phase 1: Context Gathering
1. **read_file**: Read `services/orchestrator/src/clients/workerClient.ts`
   - Purpose: Understand existing client pattern
   - Extract circuit breaker implementation approach
   
2. **list_dir**: List `services/orchestrator/src/clients/`
   - Purpose: Identify existing client files and naming conventions
   
3. **read_file**: Read `services/orchestrator/tsconfig.json`
   - Purpose: Confirm TypeScript strict mode settings
   
4. **grep_search**: Search for "PHI" or "logging" patterns
   - Pattern: `PHI|logging|logger`
   - Purpose: Identify existing PHI-safe logging patterns

### Phase 2: File Creation
5. **create_file**: Create `services/orchestrator/src/clients/agentClient.ts`
   - Full implementation based on architect's design
   - Includes all required methods and types

### Phase 3: Validation
6. **run_in_terminal**: Execute type checking
   ```bash
   cd services/orchestrator && npm run typecheck
   ```
   - Purpose: Verify TypeScript compilation
   
7. **run_in_terminal**: Run tests
   ```bash
   cd services/orchestrator && npm test
   ```
   - Purpose: Ensure no regressions
   
8. **run_in_terminal**: Validate Docker compose
   ```bash
   docker compose config
   ```
   - Purpose: Verify configuration integrity

### Phase 4: Verification Review
9. **Use Verifier Agent**: Review implementation for:
   - PHI leaks in logging
   - Proper error handling
   - Type safety compliance
   - Circuit breaker correctness
   - Timeout enforcement

---

## Expected Outputs

### 1. File List Touched
- `services/orchestrator/src/clients/agentClient.ts` (NEW)
- `services/orchestrator/package.json` (MODIFIED - if new dependencies)

### 2. Exact Implementation Structure
```typescript
// Expected interfaces
interface AgentClientOptions {
  timeout?: number;
  circuitBreakerThreshold?: number;
  circuitBreakerTimeout?: number;
}

interface PostSyncResponse {
  ok: boolean;
  status: number;
  data?: any;
  error?: string;
  duration_ms: number;
}

// Expected exports
export function getAgentClient(options?: AgentClientOptions): AgentClient;
export class AgentClient {
  postSync(agentBaseUrl: string, path: string, body: any, opts?: RequestOptions): PostSyncResponse;
}
```

### 3. New Environment Variables
Document any required:
- `AGENT_REQUEST_TIMEOUT` (optional, default: 30000)
- `AGENT_CIRCUIT_BREAKER_THRESHOLD` (optional, default: 5)
- `AGENT_CIRCUIT_BREAKER_TIMEOUT` (optional, default: 60000)

### 4. Compile Impacts
- New file added to `src/clients/`
- Exports added to module
- Potential new dependencies in package.json

---

## Success Criteria

✅ **Implementation Complete When:**
1. File `services/orchestrator/src/clients/agentClient.ts` exists
2. `npm run typecheck` passes with 0 errors
3. `npm test` passes (existing tests + any new tests)
4. `docker compose config` validates successfully
5. No PHI data appears in any log statements
6. All TypeScript types are properly defined
7. Circuit breaker logic is functional
8. Timeout enforcement works correctly

---

## Failure Modes to Identify

The Architect agent must identify these potential failure modes:

1. **Network Failures**
   - Timeout handling
   - Connection refused
   - DNS resolution failures

2. **Circuit Breaker Edge Cases**
   - State transitions during high load
   - Reset logic correctness
   - Thread safety in singleton

3. **PHI Exposure Risks**
   - Logging request/response bodies
   - Error messages containing PHI
   - Debug output

4. **Type Safety Issues**
   - Any type usage
   - Untyped external dependencies
   - Missing null checks

---

## Rollback Plan

If issues arise:
1. Remove `services/orchestrator/src/clients/agentClient.ts`
2. Revert any package.json changes
3. Run `npm install` to restore dependencies
4. Verify tests pass: `npm test`

---

## Next Steps (After Completion)

Once Step 1 is validated:
- Proceed to Milestone 1, Step 2: Integration with orchestrator service
- Add unit tests for AgentClient
- Document client usage in README
- Update architecture diagrams

---

## Notes

- **PHI Safety**: This is a clinical research platform. Protected Health Information (PHI) must never be logged.
- **Strict Mode**: All TypeScript must compile in strict mode with no errors.
- **Pattern Consistency**: Follow existing client patterns in the codebase.
- **No Over-Engineering**: Keep it simple and focused on sync-only operations for now.

---

## Command Summary

```bash
# Context gathering
cat services/orchestrator/src/clients/workerClient.ts
ls -la services/orchestrator/src/clients/
cat services/orchestrator/tsconfig.json

# Implementation (after creating file)
cd services/orchestrator

# Validation sequence
npm run typecheck
npm test
cd ../.. && docker compose config

# If successful
git add services/orchestrator/src/clients/agentClient.ts
git commit -m "feat(orchestrator): add sync AgentClient for direct specialist execution"
```

---

**STATUS**: Ready for execution
**AGENT**: Architect (Claude Sonnet 4)
**ESTIMATED TIME**: 15-20 minutes
**RISK LEVEL**: Low (new file, no existing code modified)
