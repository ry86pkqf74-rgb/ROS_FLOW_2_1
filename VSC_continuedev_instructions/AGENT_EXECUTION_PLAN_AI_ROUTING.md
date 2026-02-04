# 🚀 AI Routing & Agent Fleet Buildout - Execution Plan

**Project**: ResearchFlow AI Routing Architecture Implementation  
**Duration**: 14 Days  
**Executor**: Continue.dev AI Agents  
**Date**: February 4, 2026  

---

## 📋 Executive Summary

**Objective**: Implement comprehensive AI model routing system with local inference enforcement, agent fleet architecture, and streaming support across 25+ specialized agents.

**Key Deliverables**:
- ✅ Policy-enforced model routing (local-only for LIVE/PHI/SENSITIVE)
- ✅ Agent dispatcher with dynamic endpoint resolution
- ✅ 25+ specialist FastAPI agents with SSE streaming
- ✅ Complete Docker orchestration
- ✅ CI/CD with AI evals and automated improvements
- ✅ Domain-specific agent packs (clinical, generic)

**Architecture Impact**:
- Centralized model routing with policy enforcement
- Decoupled agent services with circuit breaker patterns
- SSE streaming for real-time progress
- HIPAA-compliant local inference for PHI

---

## 🎯 Phase Overview

| Phase | Duration | Focus | Models to Use |
|-------|----------|-------|---------------|
| **Phase 1** | Days 1-3 | Foundation (routing, dispatcher) | Claude Opus + Sonnet |
| **Phase 2** | Days 4-6 | Stage 2 E2E + SSE streaming | Claude Sonnet + Codestral |
| **Phase 3** | Days 7-10 | Agent fleet (25+ services) | Mercury + Codestral |
| **Phase 4** | Days 11-14 | CI/CD & polish | Claude Sonnet + GPT-4o |

---

## 📁 Repository Structure Context

```
Current Architecture:
services/
├── orchestrator/          # Main Express API
│   ├── src/
│   │   ├── routes/ai-router.ts          # AI endpoint router
│   │   ├── services/model-router.service.ts  # Model selection
│   │   ├── services/custom-agent-dispatcher.ts  # Agent dispatch
│   │   └── clients/                     # External service clients
├── worker/               # Python ML worker
└── web/                  # React frontend

Target Architecture (Post-Implementation):
services/
├── orchestrator/         # Routing & orchestration
├── agents/              # NEW: 25+ FastAPI specialist agents
│   ├── _template/       # Base agent template
│   ├── agent-stage2-lit/
│   ├── agent-clinical-screener/
│   └── ... (25+ more)
├── agents/common/       # Shared utilities
└── domains/            # Domain-specific packs
    ├── clinical/
    └── generic/
```

---

## 🔐 Critical Context & Constraints

### HIPAA Compliance Requirements
```yaml
PHI Data Handling:
  - LIVE mode: ALWAYS use local inference (Ollama)
  - PHI detected: FORCE local-only routing
  - SENSITIVE classification: Block external APIs
  - Audit logging: All model routing decisions
```

### Technology Stack
```yaml
Backend:
  - Orchestrator: Node.js/Express/TypeScript
  - Agents: Python/FastAPI
  - Local Inference: Ollama
  - Vector DB: ChromaDB
  
Infrastructure:
  - Docker Compose for local dev
  - GitHub Actions for CI/CD
  - SSE for streaming
```

### Key Files to Understand First
```bash
# Read these before starting ANY task
@codebase services/orchestrator/src/services/model-router.service.ts
@codebase services/orchestrator/src/services/custom-agent-dispatcher.ts
@codebase services/orchestrator/src/routes/ai-router.ts
@codebase docker-compose.ai.yml
```

---

## 🎭 Agent Task Assignments

### Model Selection by Task Type

| Task Type | Primary Model | Secondary | Reasoning |
|-----------|--------------|-----------|-----------|
| **Architecture & Security** | Claude Opus 4.5 | - | HIPAA compliance critical |
| **Core Implementation** | Claude Sonnet 4.5 | Codestral | Complex TypeScript/Python |
| **Template Generation** | Mercury Coder | Codestral | Repetitive structure |
| **Testing** | Codestral | Sonnet | Fast test generation |
| **Documentation** | GPT-4o | - | Clear technical writing |
| **Config/YAML** | GPT-4o Mini | - | Simple structured data |

---

## 📅 PHASE 1: Foundation (Days 1-3)

### 🎯 Phase 1 Objectives
- Implement policy-enforced model routing
- Refactor agent dispatcher for dynamic endpoints
- Wire agent client with circuit breaker

---

### **DAY 1: Policy Enforcement** ⚡ CRITICAL

**Agent**: 🔐 Security Specialist (Claude Opus 4.5)  
**Priority**: CRITICAL - HIPAA Compliance

#### Task 1.1: Add Inference Policy Enum

**Context**: Need to enforce local-only inference for PHI data

**Prompt for Continue.dev**:
```
Model: Claude Opus 4.5

@codebase Review services/orchestrator/src/services/model-router.service.ts

Task: Add inference policy enforcement to model router

Requirements:
1. Add InferencePolicy enum:
   - 'local_only': Force Ollama, block all external APIs
   - 'prefer_local': Try Ollama first, fallback to external
   - 'prefer_external': Try external first, fallback to Ollama
   - 'external_only': Use only external APIs (testing only)

2. Add policy selection logic:
   - LIVE mode → FORCE local_only
   - PHI detected in context → FORCE local_only
   - SENSITIVE classification → FORCE local_only
   - DEMO mode with no PHI → prefer_external

3. Update routeModel() method:
   - Check policy before provider selection
   - Throw error if policy violated
   - Add audit logging for policy decisions

4. Environment variable:
   - INFERENCE_POLICY override (default: prefer_local)

Security Requirements:
- /phi-check all routing logic
- Never allow PHI to reach external APIs
- Audit log all policy decisions
- Include policy in error messages

Code style:
- TypeScript strict mode
- Comprehensive JSDoc comments
- Error handling with custom PolicyViolationError
- Unit test stubs

Deliverable: Modified model-router.service.ts with policy enforcement
```

#### Task 1.2: Block External APIs in Local-Only Mode

**Agent**: 🔐 Security Specialist (Claude Opus 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Opus 4.5

Context: Building on Task 1.1 policy enforcement

Task: Implement provider blocking for local-only mode

Files to edit:
- services/orchestrator/src/services/model-router.service.ts

Requirements:
1. Add provider validation:
   - If policy === 'local_only':
     * Block OpenAI initialization
     * Block Anthropic initialization
     * Block any external API clients
     * Only allow Ollama provider

2. Add pre-flight checks:
   - validateProviderForPolicy(provider, policy)
   - Throw PolicyViolationError with clear message
   - Include requested provider, active policy, reason

3. Update provider initialization:
   - Check policy before creating any provider client
   - Log blocked attempts with reason
   - Suggest Ollama alternatives in error message

4. Add audit events:
   - policy_enforced: { policy, provider, blocked, reason }
   - phi_protection: { context_summary, action_taken }

Security verification:
- /phi-check the provider blocking logic
- Verify no PHI can leak through error messages
- Test all policy combinations
- /rbac-audit provider initialization code

Deliverable: Provider blocking logic + audit trail
```

#### Task 1.3: Verification & Testing

**Agent**: 🧪 Test Engineer (Codestral)

**Prompt for Continue.dev**:
```
Model: Codestral

Task: Generate comprehensive tests for policy enforcement

Files to create:
- services/orchestrator/src/services/__tests__/model-router.policy.test.ts

Test scenarios:
1. Local-only enforcement:
   - ✅ Allows Ollama in local_only mode
   - ❌ Blocks OpenAI in local_only mode
   - ❌ Blocks Anthropic in local_only mode

2. PHI detection:
   - ✅ Forces local_only when PHI detected
   - ✅ Logs PHI protection event
   - ❌ Never routes PHI to external APIs

3. Mode-based policies:
   - LIVE mode → local_only (enforced)
   - DEMO mode → prefer_external (allowed)
   - SENSITIVE → local_only (enforced)

4. Policy violations:
   - Throws PolicyViolationError with details
   - Includes audit trail
   - Suggests local alternatives

5. Environment override:
   - INFERENCE_POLICY=local_only works
   - Invalid policy values rejected

Generate:
- Jest test suite with >90% coverage
- Mock Ollama/OpenAI/Anthropic providers
- Test fixtures for PHI/non-PHI contexts
- Integration test for full routing flow

Run tests: npm test -- model-router.policy.test.ts
```

#### Task 1.4: Codebase Audit

**Agent**: 🔍 Code Reviewer (Claude Opus 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Opus 4.5

Task: Audit codebase for hardcoded provider usage

@codebase Search for remaining provider initializations that bypass routing

Search patterns:
1. Direct OpenAI imports:
   grep -r "import.*openai" services/orchestrator/src/
   
2. Direct Anthropic imports:
   grep -r "import.*anthropic" services/orchestrator/src/
   
3. Hardcoded API calls:
   grep -r "api.openai.com" services/
   grep -r "api.anthropic.com" services/

Analysis needed:
- Identify all locations initializing AI providers
- Check if they use model-router.service.ts
- Flag any that bypass policy enforcement
- Recommend refactoring for centralized routing

Deliverables:
1. Audit report listing all provider usage
2. Risk assessment (HIPAA implications)
3. Refactoring recommendations
4. Priority fixes (critical path only)

Output format: Markdown table with file, line, issue, priority
```

**Success Criteria for Day 1**:
- [ ] InferencePolicy enum implemented
- [ ] Provider blocking works in local_only mode
- [ ] PHI detection forces local routing
- [ ] Tests pass with >90% coverage
- [ ] Audit report shows no policy bypasses
- [ ] Zero external API calls in LIVE mode

---

### **DAY 2: Dispatcher Refactor** 🔧

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)  
**Priority**: HIGH

#### Task 2.1: Agent Endpoint Resolution

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review services/orchestrator/src/services/custom-agent-dispatcher.ts

Context: Currently uses hardcoded WORKER_URL. Need dynamic agent endpoint resolution.

Task: Refactor dispatcher to support multiple agent endpoints

Requirements:
1. Add AGENT_ENDPOINTS_JSON environment variable:
   - Format: JSON mapping stage → {url, type, capabilities}
   - Example:
     {
       "stage2-lit": {
         "url": "http://agent-stage2-lit:8010",
         "type": "fastapi",
         "capabilities": ["sync", "stream"],
         "models": ["local-phi3", "local-qwen"]
       },
       "clinical-screener": {
         "url": "http://agent-clinical-screener:8011",
         "type": "fastapi",
         "capabilities": ["sync"],
         "models": ["local-llama3"]
       }
     }

2. Add AgentEndpoint interface:
   ```typescript
   interface AgentEndpoint {
     url: string;
     type: 'fastapi' | 'ollama' | 'custom';
     capabilities: ('sync' | 'stream' | 'batch')[];
     models: string[];
     timeout?: number;
     circuitBreaker?: CircuitBreakerConfig;
   }
   
   interface AgentRegistry {
     [stageName: string]: AgentEndpoint;
   }
   ```

3. Add resolveAgentEndpoint(stageName: string) method:
   - Parse AGENT_ENDPOINTS_JSON on initialization
   - Cache parsed registry
   - Return AgentEndpoint for requested stage
   - Throw AgentNotFoundError if stage not in registry
   - Fallback to WORKER_URL for backward compatibility

4. Update dispatch() method:
   - Replace hardcoded WORKER_URL
   - Use resolveAgentEndpoint(task.stage)
   - Pass endpoint.url to HTTP client
   - Include endpoint metadata in logs

5. Keep Ollama dispatch unchanged:
   - Ollama routing still works as-is
   - Only affects agent service dispatch

Error handling:
- Invalid JSON in AGENT_ENDPOINTS_JSON → log + use fallback
- Missing stage in registry → throw clear error
- Invalid URL format → validate on startup

Code requirements:
- TypeScript strict mode
- Zod schema for validation
- JSDoc documentation
- Backward compatible (WORKER_URL fallback)

Deliverable: Refactored custom-agent-dispatcher.ts with dynamic endpoint resolution
```

#### Task 2.2: Unit Tests for Dispatcher

**Agent**: 🧪 Test Engineer (Codestral)

**Prompt for Continue.dev**:
```
Model: Codestral

Task: Generate unit tests for agent endpoint resolution

File: services/orchestrator/src/services/__tests__/custom-agent-dispatcher.test.ts

Test scenarios:
1. Endpoint resolution:
   - ✅ Resolves valid stage from registry
   - ❌ Throws error for unknown stage
   - ✅ Returns correct URL, type, capabilities
   - ✅ Falls back to WORKER_URL if registry not set

2. Registry parsing:
   - ✅ Valid JSON parses correctly
   - ❌ Invalid JSON logs error + uses fallback
   - ✅ Cache works (doesn't re-parse every time)
   - ✅ Validates endpoint schema with Zod

3. Dispatch routing:
   - ✅ Uses resolved endpoint URL
   - ✅ Includes endpoint metadata in logs
   - ✅ Ollama dispatch unchanged
   - ✅ Backward compatible with WORKER_URL

4. Error cases:
   - Missing AGENT_ENDPOINTS_JSON env var
   - Malformed JSON
   - Stage not in registry
   - Invalid URL in endpoint

Test fixtures:
- Valid AGENT_ENDPOINTS_JSON examples
- Invalid JSON examples
- Edge cases (empty registry, null values)

Generate:
- Jest test suite
- Mock axios for HTTP calls
- Test coverage >85%
- Clear assertions with descriptive messages

Run: npm test -- custom-agent-dispatcher.test.ts
```

**Success Criteria for Day 2**:
- [ ] AGENT_ENDPOINTS_JSON parsing works
- [ ] resolveAgentEndpoint() returns correct URLs
- [ ] Backward compatible with WORKER_URL
- [ ] Tests pass with >85% coverage
- [ ] Zod validation prevents invalid configs
- [ ] Error messages are clear and actionable

---

### **DAY 3: Agent Client + Orchestrator Wiring** 🔌

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)  
**Priority**: HIGH

#### Task 3.1: Create Agent Client

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Create new agent client with circuit breaker pattern

File to create: services/orchestrator/src/clients/agentClient.ts

Requirements:
1. AgentClient class with methods:
   - postSync(endpoint, taskContract): Promise<AgentResponse>
   - runStream(endpoint, taskContract): AsyncIterator<SSEEvent>

2. Circuit breaker pattern:
   - Use opossum library (already in deps?)
   - Config: timeout=30s, errorThresholdPercentage=50, resetTimeout=30s
   - State: CLOSED → OPEN → HALF_OPEN
   - Log state transitions

3. TaskContract interface:
   ```typescript
   interface TaskContract {
     agent_id: string;
     task_type: string;
     input: {
       query?: string;
       context?: Record<string, any>;
       documents?: Array<{id: string, content: string}>;
     };
     config: {
       model?: string;
       temperature?: number;
       max_tokens?: number;
       stream?: boolean;
     };
     metadata: {
       workflow_id: string;
       stage: string;
       job_id: string;
       user_id: string;
       mode: 'LIVE' | 'DEMO';
     };
   }
   
   interface AgentResponse {
     status: 'success' | 'error' | 'partial';
     result?: any;
     artifacts?: Array<{
       name: string;
       type: string;
       content: string;
       metadata?: Record<string, any>;
     }>;
     error?: {
       code: string;
       message: string;
       details?: any;
     };
     metrics?: {
       duration_ms: number;
       tokens_used?: number;
       model_used?: string;
     };
   }
   ```

4. postSync() implementation:
   - POST to endpoint/agents/run/sync
   - Timeout: 30s (configurable)
   - Retry logic: 3 attempts with exponential backoff
   - Request/response logging
   - Error transformation (agent errors → orchestrator errors)
   - Metrics collection

5. Error handling:
   - Timeout errors → throw TimeoutError
   - Circuit open → throw ServiceUnavailableError
   - Agent 4xx → throw ValidationError
   - Agent 5xx → throw AgentExecutionError
   - Network errors → retry, then throw

6. Monitoring hooks:
   - onRequest(taskContract)
   - onResponse(response, duration)
   - onError(error, taskContract)
   - Emit metrics for observability

Dependencies:
- axios for HTTP
- opossum for circuit breaker
- zod for validation

Code quality:
- TypeScript strict mode
- Comprehensive error types
- JSDoc comments
- Structured logging
- /phi-check for PHI leakage prevention

Deliverable: services/orchestrator/src/clients/agentClient.ts
```

#### Task 3.2: Wire Agent Client to AI Router

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review services/orchestrator/src/routes/ai-router.ts

Task: Update AI router to return dispatch plans

Files to edit:
- services/orchestrator/src/routes/ai-router.ts

Requirements:
1. Add DispatchPlan schema:
   ```typescript
   interface DispatchPlan {
     strategy: 'agent' | 'ollama' | 'external';
     agent?: {
       stage: string;
       endpoint: string;
       capabilities: string[];
     };
     model: {
       provider: string;
       model: string;
       inference_policy: string;
     };
     contract: TaskContract;
     estimated_tokens?: number;
     estimated_duration_ms?: number;
   }
   ```

2. Update POST /api/ai/generate endpoint:
   - Build DispatchPlan from request
   - Use model-router.service to select model (with policy)
   - Use custom-agent-dispatcher to resolve endpoint
   - Build TaskContract with all metadata
   - Return DispatchPlan (don't execute yet)

3. Add POST /api/ai/execute endpoint:
   - Accepts DispatchPlan
   - Validates plan with Zod
   - Executes via agentClient.postSync()
   - Returns AgentResponse
   - Logs execution metrics

4. Add GET /api/ai/plan/:workflow_id/:stage endpoint:
   - Returns cached or newly generated plan
   - Useful for debugging

Integration:
- Import AgentClient
- Import updated dispatcher
- Wire to existing auth middleware
- /rbac-audit all new endpoints
- Add request validation

Error responses:
- 400: Invalid request / validation failed
- 401: Authentication required
- 403: Insufficient permissions
- 422: Policy violation (PHI routing blocked)
- 500: Agent execution failed
- 503: Service unavailable (circuit open)

Deliverable: Updated ai-router.ts with dispatch plan flow
```

#### Task 3.3: Integration Tests

**Agent**: 🧪 Test Engineer (Codestral)

**Prompt for Continue.dev**:
```
Model: Codestral

Task: Create integration tests for agent client → router flow

File: services/orchestrator/src/__tests__/integration/agent-dispatch.integration.test.ts

Test flow:
1. Request → AI Router → Dispatch Plan → Agent Client → Response

Test scenarios:
1. Happy path (sync execution):
   - POST /api/ai/generate → DispatchPlan
   - POST /api/ai/execute → AgentResponse
   - Verify correct endpoint called
   - Verify TaskContract structure
   - Verify response format

2. Policy enforcement:
   - LIVE mode forces local agent
   - PHI context forces local agent
   - Attempt external in local_only → 422 error

3. Circuit breaker:
   - Agent timeout → circuit opens
   - Subsequent requests fail fast
   - Circuit resets after timeout

4. Error handling:
   - Agent returns 400 → ValidationError
   - Agent returns 500 → retry + eventual error
   - Network failure → retry logic

5. Backward compatibility:
   - Ollama dispatch still works
   - WORKER_URL fallback works

Setup:
- Mock agent services with nock or msw
- Mock Ollama for local inference
- Test database with fixtures
- Clean state between tests

Run: npm test -- agent-dispatch.integration.test.ts

Coverage target: >80% for integration paths
```

**Success Criteria for Day 3**:
- [ ] AgentClient with circuit breaker works
- [ ] AI router returns DispatchPlan
- [ ] Execute endpoint calls agent correctly
- [ ] Integration tests pass
- [ ] Circuit breaker prevents cascading failures
- [ ] Error handling is robust

---

## 📊 Phase 1 Completion Checklist

Before moving to Phase 2, verify:

### Code Changes
- [ ] model-router.service.ts has policy enforcement
- [ ] custom-agent-dispatcher.ts uses dynamic endpoints
- [ ] agentClient.ts created with circuit breaker
- [ ] ai-router.ts returns DispatchPlan

### Tests
- [ ] Policy enforcement tests pass (>90% coverage)
- [ ] Dispatcher tests pass (>85% coverage)
- [ ] Integration tests pass (>80% coverage)
- [ ] No test failures in existing test suite

### Security
- [ ] /phi-check passed on all new code
- [ ] /rbac-audit passed on all endpoints
- [ ] Audit report shows no policy bypasses
- [ ] Local-only enforcement works for LIVE mode

### Documentation
- [ ] JSDoc comments on all public methods
- [ ] README updated with policy usage
- [ ] AGENT_ENDPOINTS_JSON example documented

### Verification Commands
```bash
# Run all tests
npm test

# Check TypeScript compilation
npm run type-check

# Run security audit
/phi-check services/orchestrator/src/

# Verify policy enforcement
INFERENCE_POLICY=local_only npm start
# Attempt external API call in LIVE mode → should fail
```

---

## 📅 PHASE 2: Stage 2 E2E + SSE Streaming (Days 4-6)

### 🎯 Phase 2 Objectives
- Wire Stage 2 to use agent routing
- Create minimal FastAPI agent
- Implement SSE streaming
- Docker orchestration

---

### **DAY 4: Stage 2 Sync Path** 🔄

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)  
**Priority**: HIGH

#### Task 4.1: Refactor Workflow Stage 2

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review services/worker/src/workflow_engine/stages/ (find Stage 2 implementation)

Task: Replace direct WORKER_URL calls with router → agent flow

Context: Stage 2 currently calls Python worker directly. Need to route through orchestrator's agent client.

Requirements:
1. Find Stage 2 handler (likely in stages/worker.ts or similar)

2. Replace direct HTTP call with agent routing:
   OLD:
   ```typescript
   const result = await axios.post(`${WORKER_URL}/some/endpoint`, payload);
   ```
   
   NEW:
   ```typescript
   // Build dispatch plan
   const plan: DispatchPlan = await aiRouter.generatePlan({
     stage: 'stage2-lit',
     task_type: 'literature_review',
     input: { query: researchQuery },
     workflow_id: this.workflowId,
     mode: this.mode
   });
   
   // Execute via agent client
   const result = await agentClient.postSync(plan.agent.endpoint, plan.contract);
   ```

3. Build TaskContract properly:
   ```typescript
   const taskContract: TaskContract = {
     agent_id: 'stage2-lit',
     task_type: 'literature_review',
     input: {
       query: stage2Input.query,
       context: {
         protocol_id: this.workflowId,
         previous_results: stage1Results
       },
       documents: relevantDocs
     },
     config: {
       model: plan.model.model,
       temperature: 0.7,
       max_tokens: 2000,
       stream: false
     },
     metadata: {
       workflow_id: this.workflowId,
       stage: 'stage2-lit',
       job_id: this.jobId,
       user_id: this.userId,
       mode: this.mode
     }
   };
   ```

4. Handle agent response:
   - Extract artifacts from response.artifacts
   - Map to stage output format
   - Update workflow state
   - Log metrics

5. Error handling:
   - Agent timeout → retry with backoff
   - Validation error → fail stage with details
   - Agent unavailable → queue for retry
   - Partial results → save + retry

Files to edit:
- services/orchestrator/src/workflow/stages/stage2.ts (or similar)
- May need to update workflow-executor.ts

Dependencies:
- Import agentClient from clients/
- Import DispatchPlan types

Testing:
- Unit test for TaskContract building
- Mock agent response
- Verify artifact extraction

Deliverable: Stage 2 using agent routing instead of direct worker calls
```

#### Task 4.2: Create Minimal FastAPI Agent (Stage 2)

**Agent**: ⚡ Rapid Code Generator (Mercury Coder)

**Prompt for Continue.dev**:
```
Model: Mercury Coder

Task: Generate minimal FastAPI agent service for Stage 2

Directory: services/agents/agent-stage2-lit/

Structure:
agent-stage2-lit/
├── main.py                 # FastAPI app
├── requirements.txt        # Dependencies
├── Dockerfile              # Container config
├── .env.example           # Environment template
└── README.md              # Usage instructions

Requirements:
1. main.py with FastAPI app:
   ```python
   from fastapi import FastAPI, HTTPException
   from pydantic import BaseModel
   from typing import Dict, List, Optional, Any
   import uvicorn
   
   app = FastAPI(title="Stage 2 Literature Review Agent")
   
   class TaskContract(BaseModel):
       agent_id: str
       task_type: str
       input: Dict[str, Any]
       config: Dict[str, Any]
       metadata: Dict[str, Any]
   
   class Artifact(BaseModel):
       name: str
       type: str
       content: str
       metadata: Optional[Dict[str, Any]] = None
   
   class AgentResponse(BaseModel):
       status: str  # 'success' | 'error' | 'partial'
       result: Optional[Any] = None
       artifacts: List[Artifact] = []
       error: Optional[Dict[str, Any]] = None
       metrics: Optional[Dict[str, Any]] = None
   
   @app.get("/health")
   async def health():
       return {"status": "healthy", "agent": "stage2-lit"}
   
   @app.post("/agents/run/sync")
   async def run_sync(contract: TaskContract) -> AgentResponse:
       # TODO: Implement actual logic
       # For now, return mock response
       return AgentResponse(
           status="success",
           result={"message": "Stage 2 literature review placeholder"},
           artifacts=[
               Artifact(
                   name="literature_summary",
                   type="markdown",
                   content="# Literature Review\n\nPlaceholder content",
                   metadata={"source": "stage2-lit"}
               )
           ],
           metrics={
               "duration_ms": 100,
               "model_used": "local-phi3"
           }
       )
   
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=8010)
   ```

2. requirements.txt:
   ```
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   pydantic==2.5.0
   httpx==0.25.0
   python-dotenv==1.0.0
   ```

3. Dockerfile:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY main.py .
   
   EXPOSE 8010
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
   ```

4. README.md with:
   - Purpose
   - API endpoints
   - Request/response examples
   - Local testing commands

Keep it MINIMAL - just enough to test routing. Real implementation comes later.

Deliverable: Working FastAPI service that responds to /agents/run/sync
```

#### Task 4.3: Docker Compose Integration

**Agent**: 🐳 DevOps Engineer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review docker-compose.ai.yml

Task: Add agent-stage2-lit service to Docker Compose

Requirements:
1. Add service definition:
   ```yaml
   agent-stage2-lit:
     build: ./services/agents/agent-stage2-lit
     container_name: researchflow-agent-stage2-lit
     ports:
       - "8010:8010"
     environment:
       - OLLAMA_BASE_URL=http://ollama:11434
       - CHROMADB_HOST=chromadb
       - CHROMADB_PORT=8000
       - LOG_LEVEL=info
     depends_on:
       - ollama
       - chromadb
     networks:
       - researchflow-network
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
       interval: 10s
       timeout: 5s
       retries: 3
   ```

2. Update orchestrator service:
   ```yaml
   orchestrator:
     environment:
       - AGENT_ENDPOINTS_JSON='{
           "stage2-lit": {
             "url": "http://agent-stage2-lit:8010",
             "type": "fastapi",
             "capabilities": ["sync"],
             "models": ["local-phi3"]
           }
         }'
     depends_on:
       - agent-stage2-lit
   ```

3. If ChromaDB not present, add it:
   ```yaml
   chromadb:
     image: chromadb/chroma:latest
     container_name: researchflow-chromadb
     ports:
       - "8000:8000"
     volumes:
       - chromadb-data:/chroma/chroma
     networks:
       - researchflow-network
   
   volumes:
     chromadb-data:
   ```

4. Verify network configuration:
   - All services on researchflow-network
   - Proper service discovery via container names
   - Health checks for all critical services

Testing:
/docker-check docker-compose.ai.yml

Commands to verify:
```bash
# Build and start
docker-compose -f docker-compose.ai.yml up --build

# Check health
curl http://localhost:8010/health

# Test agent endpoint
curl -X POST http://localhost:8010/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{...TaskContract...}'
```

Deliverable: Updated docker-compose.ai.yml with agent service
```

**Success Criteria for Day 4**:
- [ ] Stage 2 uses agent routing (not direct worker calls)
- [ ] agent-stage2-lit service responds to /agents/run/sync
- [ ] Docker Compose starts all services
- [ ] Health checks pass
- [ ] E2E test: orchestrator → agent → response

---

### **DAY 5: Docker Wiring & Local Testing** 🐋

**Agent**: 🐳 DevOps Engineer (Claude Sonnet 4.5 + GPT-4o)  
**Priority**: HIGH

#### Task 5.1: Complete Docker Configuration

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Finalize Docker configuration for agent architecture

Files to review/edit:
- docker-compose.ai.yml
- services/orchestrator/.env.example
- services/agents/agent-stage2-lit/.env.example

Requirements:
1. Environment variable documentation:
   - Update orchestrator .env.example with AGENT_ENDPOINTS_JSON
   - Add INFERENCE_POLICY examples
   - Document all agent service env vars

2. Service dependencies:
   - Verify orchestrator waits for agents
   - Verify agents wait for ollama/chromadb
   - Add wait-for-it.sh scripts if needed

3. Volume mounts:
   - Ollama models: persist to host
   - ChromaDB data: persist to host
   - Agent logs: optionally mount for debugging

4. Port mappings:
   - Document all exposed ports
   - Ensure no conflicts
   - Add to README

5. Network configuration:
   - Single network for all services
   - DNS resolution between services
   - Verify service discovery works

Docker commands to generate:
```bash
# Start all AI services
docker-compose -f docker-compose.ai.yml up -d

# View logs
docker-compose -f docker-compose.ai.yml logs -f agent-stage2-lit

# Check service health
docker-compose -f docker-compose.ai.yml ps

# Restart specific service
docker-compose -f docker-compose.ai.yml restart agent-stage2-lit

# Stop all
docker-compose -f docker-compose.ai.yml down
```

Testing checklist:
- [ ] All services start successfully
- [ ] Health checks pass
- [ ] Service discovery works (ping between containers)
- [ ] Logs are accessible
- [ ] Volumes persist data across restarts

Deliverable: Production-ready docker-compose.ai.yml with documentation
```

#### Task 5.2: Local Integration Testing

**Agent**: 🧪 Test Engineer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Create local integration test script for agent architecture

File: scripts/test-agent-architecture.sh

Script should:
1. Start services with docker-compose
2. Wait for health checks to pass
3. Test agent routing flow
4. Verify responses
5. Clean up

Example structure:
```bash
#!/bin/bash
set -e

echo "🚀 Testing Agent Architecture..."

# Start services
echo "Starting services..."
docker-compose -f docker-compose.ai.yml up -d

# Wait for health
echo "Waiting for services..."
for i in {1..30}; do
  if curl -f http://localhost:8010/health > /dev/null 2>&1; then
    echo "✅ Agent service healthy"
    break
  fi
  sleep 2
done

# Test 1: Agent health
echo "Test 1: Agent health check"
curl -f http://localhost:8010/health || exit 1

# Test 2: Dispatch plan generation
echo "Test 2: Generate dispatch plan"
PLAN=$(curl -X POST http://localhost:3000/api/ai/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "stage": "stage2-lit",
    "task_type": "literature_review",
    "query": "test query",
    "mode": "DEMO"
  }')
echo "Plan: $PLAN"

# Test 3: Execute via agent
echo "Test 3: Execute agent task"
RESULT=$(curl -X POST http://localhost:3000/api/ai/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d "$PLAN")
echo "Result: $RESULT"

# Test 4: Policy enforcement
echo "Test 4: Test local-only policy"
POLICY_TEST=$(curl -X POST http://localhost:3000/api/ai/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{
    "stage": "stage2-lit",
    "query": "PATIENT: John Doe, DOB: 1980-01-01",
    "mode": "LIVE"
  }')
# Should force local-only routing
echo "$POLICY_TEST" | grep -q "local" || (echo "❌ Policy enforcement failed" && exit 1)

echo "✅ All tests passed!"

# Cleanup
docker-compose -f docker-compose.ai.yml down
```

Make executable:
chmod +x scripts/test-agent-architecture.sh

Run:
./scripts/test-agent-architecture.sh

Deliverable: Automated integration test script
```

**Success Criteria for Day 5**:
- [ ] Docker Compose config complete and documented
- [ ] All services start and pass health checks
- [ ] Integration test script passes
- [ ] Service discovery works
- [ ] Policy enforcement verified in Docker environment
- [ ] Documentation updated

---

### **DAY 6: SSE Streaming Implementation** 📡

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)  
**Priority**: MEDIUM (M2 milestone)

#### Task 6.1: Add Streaming to Agent Client

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review services/orchestrator/src/clients/agentClient.ts

Task: Add SSE streaming support to agent client

Requirements:
1. Add runStream() method:
   ```typescript
   async function* runStream(
     endpoint: string,
     taskContract: TaskContract
   ): AsyncIterableIterator<SSEEvent> {
     // POST to endpoint/agents/run/stream
     // Parse SSE events
     // Yield each event
     // Handle errors mid-stream
   }
   ```

2. SSEEvent interface:
   ```typescript
   interface SSEEvent {
     event: 'progress' | 'artifact' | 'complete' | 'error';
     data: {
       message?: string;
       progress?: number;
       artifact?: Artifact;
       error?: ErrorDetails;
       metrics?: Metrics;
     };
     id?: string;
     timestamp: string;
   }
   ```

3. Implementation:
   - Use fetch() with ReadableStream
   - Parse SSE format (data: ... \n\n)
   - Yield parsed events
   - Handle connection errors
   - Timeout: 5 minutes for long-running tasks
   - Reconnect logic (retry 3 times)

4. Error handling:
   - Connection lost → yield error event, retry
   - Invalid SSE format → log warning, skip
   - Agent error event → yield, then throw
   - Timeout → yield timeout event, close stream

Example usage:
```typescript
for await (const event of agentClient.runStream(endpoint, contract)) {
  switch (event.event) {
    case 'progress':
      console.log(`Progress: ${event.data.progress}%`);
      break;
    case 'artifact':
      saveArtifact(event.data.artifact);
      break;
    case 'complete':
      console.log('Done!');
      break;
    case 'error':
      throw new Error(event.data.error.message);
  }
}
```

Dependencies:
- Use native fetch() (Node 18+)
- No external SSE libraries needed

Testing:
- Mock SSE responses
- Test event parsing
- Test error recovery
- Test timeout handling

Deliverable: agentClient.ts with runStream() method
```

#### Task 6.2: Add Streaming Endpoint to Agent Service

**Agent**: ⚡ Rapid Code Generator (Mercury Coder)

**Prompt for Continue.dev**:
```
Model: Mercury Coder

Task: Add SSE streaming endpoint to agent-stage2-lit

File: services/agents/agent-stage2-lit/main.py

Add endpoint:
```python
from fastapi.responses import StreamingResponse
import asyncio
import json

@app.post("/agents/run/stream")
async def run_stream(contract: TaskContract):
    async def event_generator():
        try:
            # Progress event
            yield f"event: progress\ndata: {json.dumps({'message': 'Starting', 'progress': 0})}\n\n"
            await asyncio.sleep(1)
            
            # More progress
            yield f"event: progress\ndata: {json.dumps({'message': 'Processing', 'progress': 50})}\n\n"
            await asyncio.sleep(1)
            
            # Artifact event
            artifact = {
                'name': 'literature_summary',
                'type': 'markdown',
                'content': '# Results\n\nSome content here'
            }
            yield f"event: artifact\ndata: {json.dumps({'artifact': artifact})}\n\n"
            await asyncio.sleep(1)
            
            # Complete event
            result = {
                'status': 'success',
                'metrics': {'duration_ms': 3000}
            }
            yield f"event: complete\ndata: {json.dumps(result)}\n\n"
            
        except Exception as e:
            error = {
                'code': 'AGENT_ERROR',
                'message': str(e)
            }
            yield f"event: error\ndata: {json.dumps({'error': error})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

Test with curl:
```bash
curl -N -X POST http://localhost:8010/agents/run/stream \
  -H "Content-Type: application/json" \
  -d '{...TaskContract...}'
```

Should see SSE events stream in real-time.

Deliverable: Agent with streaming support
```

#### Task 6.3: Add Streaming Endpoint to Orchestrator

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

@codebase Review services/orchestrator/src/routes/ai-router.ts

Task: Add SSE streaming endpoint to orchestrator

Add endpoint:
```typescript
// GET /api/workflow/stages/:stage/jobs/:job_id/stream
router.get('/workflow/stages/:stage/jobs/:job_id/stream', 
  authenticateToken,
  async (req, res) => {
    const { stage, job_id } = req.params;
    
    try {
      // Get job details
      const job = await jobService.getJob(job_id);
      
      // Generate dispatch plan
      const plan = await aiRouter.generatePlan({
        stage,
        task_type: job.task_type,
        input: job.input,
        workflow_id: job.workflow_id,
        mode: job.mode
      });
      
      // Set SSE headers
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      
      // Stream from agent
      for await (const event of agentClient.runStream(
        plan.agent.endpoint,
        plan.contract
      )) {
        // Forward event to client
        res.write(`event: ${event.event}\n`);
        res.write(`data: ${JSON.stringify(event.data)}\n\n`);
        
        // Update job status based on events
        if (event.event === 'artifact') {
          await jobService.saveArtifact(job_id, event.data.artifact);
        }
        
        if (event.event === 'complete') {
          await jobService.updateStatus(job_id, 'completed');
        }
        
        if (event.event === 'error') {
          await jobService.updateStatus(job_id, 'failed', event.data.error);
        }
      }
      
      res.end();
      
    } catch (error) {
      res.write(`event: error\ndata: ${JSON.stringify({
        code: 'STREAM_ERROR',
        message: error.message
      })}\n\n`);
      res.end();
    }
  }
);
```

Error handling:
- Client disconnect → close agent stream
- Agent error → forward to client, close gracefully
- Timeout → send timeout event, close

Security:
- /rbac-audit the endpoint
- Verify user has access to workflow/job
- Rate limit streaming requests

Deliverable: Orchestrator with SSE streaming support
```

**Success Criteria for Day 6**:
- [ ] agentClient.runStream() works
- [ ] Agent service streams SSE events
- [ ] Orchestrator forwards events to client
- [ ] Error handling mid-stream works
- [ ] Client can consume stream (test with curl)
- [ ] Job status updates from stream events

---

## 📊 Phase 2 Completion Checklist

### Code Changes
- [ ] Stage 2 uses agent routing
- [ ] agent-stage2-lit service created
- [ ] SSE streaming implemented (client + agent + orchestrator)
- [ ] Docker Compose configured

### Testing
- [ ] Integration test script passes
- [ ] Docker services start successfully
- [ ] SSE streaming works end-to-end
- [ ] Health checks pass

### Documentation
- [ ] Docker Compose documented
- [ ] Agent API documented
- [ ] SSE event schema documented
- [ ] Testing guide updated

---

## 📅 PHASE 3: Agent Fleet Buildout (Days 7-10)

### 🎯 Phase 3 Objectives
- Create reusable agent template
- Generate 25+ specialist agents
- Wire all agents in Docker Compose
- Update agent registry

**Note**: This phase is HIGHLY REPETITIVE - perfect for Mercury Coder and Codestral

---

### **DAY 7: Agent Template Creation** 📋

**Agent**: ⚡ Rapid Code Generator (Mercury Coder)  
**Priority**: HIGH

#### Task 7.1: Create Universal Agent Template

**Prompt for Continue.dev**:
```
Model: Mercury Coder

Task: Create reusable template for all agent services

Directory: services/agents/_template/

Structure:
_template/
├── main.py                # Base FastAPI app
├── agent_base.py          # Abstract base class
├── requirements.txt       # Common dependencies
├── Dockerfile             # Standard container config
├── .env.example          # Environment template
├── README.md             # Template usage guide
└── tests/
    └── test_agent_base.py # Base tests

Requirements:
1. agent_base.py:
   ```python
   from abc import ABC, abstractmethod
   from typing import Dict, Any, AsyncIterator
   
   class AgentBase(ABC):
       def __init__(self, agent_id: str, capabilities: list[str]):
           self.agent_id = agent_id
           self.capabilities = capabilities
       
       @abstractmethod
       async def process_sync(self, contract: TaskContract) -> AgentResponse:
           """Synchronous processing - must be implemented"""
           pass
       
       async def process_stream(self, contract: TaskContract) -> AsyncIterator[SSEEvent]:
           """Streaming processing - optional override"""
           # Default: convert sync to stream
           result = await self.process_sync(contract)
           yield SSEEvent(event='complete', data=result)
       
       def validate_contract(self, contract: TaskContract) -> bool:
           """Validate task contract"""
           # Check agent_id matches
           # Check task_type supported
           # Validate input schema
           pass
       
       async def health_check(self) -> Dict[str, Any]:
           """Health check with dependencies"""
           return {
               'status': 'healthy',
               'agent_id': self.agent_id,
               'capabilities': self.capabilities
           }
   ```

2. main.py template:
   ```python
   from fastapi import FastAPI, HTTPException
   from agent_base import AgentBase
   import uvicorn
   import os
   
   # Import your specific agent implementation
   from my_agent import MySpecialistAgent
   
   # Configuration
   AGENT_ID = os.getenv('AGENT_ID', 'my-agent')
   PORT = int(os.getenv('PORT', 8010))
   
   # Initialize agent
   agent = MySpecialistAgent(agent_id=AGENT_ID)
   
   # FastAPI app
   app = FastAPI(title=f"Agent: {AGENT_ID}")
   
   @app.get("/health")
   async def health():
       return await agent.health_check()
   
   @app.post("/agents/run/sync")
   async def run_sync(contract: TaskContract) -> AgentResponse:
       if not agent.validate_contract(contract):
           raise HTTPException(400, "Invalid contract")
       return await agent.process_sync(contract)
   
   @app.post("/agents/run/stream")
   async def run_stream(contract: TaskContract):
       if not agent.validate_contract(contract):
           raise HTTPException(400, "Invalid contract")
       return StreamingResponse(
           agent.process_stream(contract),
           media_type="text/event-stream"
       )
   
   if __name__ == "__main__":
       uvicorn.run(app, host="0.0.0.0", port=PORT)
   ```

3. Standard Dockerfile:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Copy common dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy agent code
   COPY . .
   
   # Expose port (configurable via ENV)
   EXPOSE ${PORT:-8010}
   
   CMD ["python", "main.py"]
   ```

4. README.md with:
   - How to use template
   - How to implement new agent
   - Standard endpoints
   - Testing guidelines
   - Deployment checklist

Deliverable: Reusable template for all future agents
```

#### Task 7.2: Document Agent Roster

**Agent**: 📚 Documentation Writer (GPT-4o)

**Prompt for Continue.dev**:
```
Model: GPT-4o

Task: Create comprehensive agent roster documentation

File: docs/AGENT_ROSTER.md

Document 25+ specialist agents with:

Categories:
1. Clinical Agents (5-7):
   - clinical-screener: Patient eligibility screening
   - adverse-event-analyzer: Adverse event assessment
   - protocol-validator: Protocol compliance checking
   - consent-generator: Informed consent document generation
   - safety-monitor: Real-time safety monitoring

2. Literature Agents (4-6):
   - literature-reviewer (stage2-lit): Systematic review
   - citation-validator: Reference validation
   - evidence-synthesizer: Evidence synthesis
   - meta-analyzer: Meta-analysis support

3. Statistical Agents (3-5):
   - power-calculator: Sample size calculation
   - statistical-analyzer: Statistical analysis
   - data-validator: Data quality checks
   - regression-modeler: Regression analysis

4. Regulatory Agents (3-4):
   - irb-checker: IRB compliance verification
   - regulatory-mapper: Regulatory requirement mapping
   - audit-trail-generator: Audit documentation

5. Document Agents (4-6):
   - protocol-writer: Protocol generation
   - manuscript-drafter: Manuscript drafting
   - report-generator: Study report generation
   - abstract-writer: Abstract creation

6. Generic Agents (4-6):
   - summarizer: Text summarization
   - translator: Multi-language translation
   - classifier: Document classification
   - entity-extractor: Named entity extraction

For EACH agent, document:
- Agent ID
- Purpose
- Capabilities (sync/stream/batch)
- Input schema
- Output schema
- Models used (local vs external)
- Estimated duration
- Token budget
- Dependencies
- Port assignment
- Docker service name

Format as markdown table for easy reference.

Also include:
- Agent lifecycle (initialization, execution, cleanup)
- Monitoring and metrics
- Error handling patterns
- Scaling considerations

Deliverable: docs/AGENT_ROSTER.md with full fleet specification
```

**Success Criteria for Day 7**:
- [ ] Template structure created and documented
- [ ] AgentBase abstract class implemented
- [ ] Standard endpoints defined
- [ ] Agent roster fully documented (25+ agents)
- [ ] Port assignments planned (8010-8035)
- [ ] Template tested with example agent

---

### **DAYS 8-10: Fleet Generation** 🏭

**Agent**: ⚡ Rapid Code Generator (Mercury Coder + Codestral in parallel)  
**Priority**: HIGH  
**Strategy**: Use AI to generate repetitive agent services

#### Master Prompt for Fleet Generation

**Prompt for Continue.dev** (repeat for each agent):
```
Model: Mercury Coder (for speed) or Codestral

Task: Generate specialist agent from template

Target: Agent #{N} - {AGENT_NAME}

Based on: services/agents/_template/
Create: services/agents/{AGENT_NAME}/

Steps:
1. Copy template structure
2. Implement {AGENT_NAME}Agent class extending AgentBase
3. Implement process_sync() with agent-specific logic
4. Update agent_id, port, and metadata
5. Create Dockerfile
6. Add to docker-compose.ai.yml
7. Update AGENT_ROSTER
8. Add to AGENT_ENDPOINTS_JSON

Agent Spec (from AGENT_ROSTER.md):
- Agent ID: {AGENT_ID}
- Purpose: {PURPOSE}
- Capabilities: {CAPABILITIES}
- Port: {PORT}
- Models: {MODELS}

Implementation:
```python
# services/agents/{AGENT_NAME}/my_agent.py
from agent_base import AgentBase, TaskContract, AgentResponse, Artifact

class {AgentClassName}(AgentBase):
    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            capabilities=['sync']  # Add 'stream' if needed
        )
        # Initialize agent-specific resources
        # - Load models
        # - Connect to databases
        # - Set up config
    
    async def process_sync(self, contract: TaskContract) -> AgentResponse:
        # 1. Extract input
        query = contract.input.get('query')
        context = contract.input.get('context', {})
        
        # 2. Validate input
        if not query:
            return AgentResponse(
                status='error',
                error={'code': 'MISSING_INPUT', 'message': 'Query required'}
            )
        
        # 3. Process (AGENT-SPECIFIC LOGIC HERE)
        # - Call local model
        # - Query databases
        # - Apply algorithms
        # TODO: Implement actual logic
        result = f"Processed by {self.agent_id}: {query}"
        
        # 4. Create artifacts
        artifacts = [
            Artifact(
                name=f'{self.agent_id}_output',
                type='text',
                content=result,
                metadata={'agent': self.agent_id}
            )
        ]
        
        # 5. Return response
        return AgentResponse(
            status='success',
            result={'message': result},
            artifacts=artifacts,
            metrics={'duration_ms': 100}  # Add actual metrics
        )
```

Docker Compose addition:
```yaml
{AGENT_NAME}:
  build: ./services/agents/{AGENT_NAME}
  container_name: researchflow-{AGENT_NAME}
  ports:
    - "{PORT}:{PORT}"
  environment:
    - AGENT_ID={AGENT_ID}
    - PORT={PORT}
    - OLLAMA_BASE_URL=http://ollama:11434
  depends_on:
    - ollama
  networks:
    - researchflow-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:{PORT}/health"]
    interval: 10s
    timeout: 5s
    retries: 3
```

AGENT_ENDPOINTS_JSON addition:
```json
"{AGENT_ID}": {
  "url": "http://{AGENT_NAME}:{PORT}",
  "type": "fastapi",
  "capabilities": ["sync"],
  "models": ["{MODEL}"]
}
```

Generate ALL files for this agent, then move to next agent.

Use PARALLEL execution: Generate 5-10 agents simultaneously with different AI models.
```

#### Parallel Generation Strategy

**Day 8**: Agents 1-10
- Mercury Coder: Agents 1-5
- Codestral: Agents 6-10

**Day 9**: Agents 11-20
- Mercury Coder: Agents 11-15
- Codestral: Agents 16-20

**Day 10**: Agents 21-25+ & Integration
- Mercury Coder: Agents 21-25
- Codestral: Integration testing
- Claude Sonnet: Docker Compose finalization

---

## 📊 Phase 3 Completion Checklist

### Agent Services
- [ ] Template created and tested
- [ ] 25+ agent services generated
- [ ] All agents extend AgentBase
- [ ] Health checks work for all agents

### Docker Integration
- [ ] All agents in docker-compose.ai.yml
- [ ] Port assignments (8010-8035+)
- [ ] AGENT_ENDPOINTS_JSON complete
- [ ] All services start successfully

### Documentation
- [ ] AGENT_ROSTER.md complete
- [ ] Each agent has README
- [ ] Template usage guide created
- [ ] Port mapping documented

### Testing
- [ ] Template tests pass
- [ ] Sample agent tests pass
- [ ] Docker health checks pass
- [ ] Integration smoke tests pass

---

## 📅 PHASE 4: CI & Polish (Days 11-14)

### 🎯 Phase 4 Objectives
- Set up CI/CD workflows
- Add AI evaluation tests
- Create automated improvement PRs
- Organize domain packs
- Final documentation

---

### **DAY 11: CI Workflows (Part 1)** 🔧

**Agent**: 🐳 DevOps Engineer (Claude Sonnet 4.5)

#### Task 11.1: Schema Validation Workflow

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Create GitHub Actions workflow for schema validation

File: .github/workflows/ai-schema-validation.yml

Workflow should:
1. Trigger on PR to main
2. Validate all agent schemas match standard
3. Check AGENT_ENDPOINTS_JSON syntax
4. Verify TaskContract/AgentResponse schemas
5. Validate Zod schemas compile
6. Check for schema drift

```yaml
name: AI Schema Validation

on:
  pull_request:
    branches: [main]
    paths:
      - 'services/agents/**'
      - 'services/orchestrator/src/**/*.ts'

jobs:
  validate-schemas:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd services/orchestrator
          npm ci
      
      - name: Validate TypeScript schemas
        run: |
          cd services/orchestrator
          npm run type-check
      
      - name: Validate Zod schemas
        run: |
          cd services/orchestrator
          npm test -- --testPathPattern=schema
      
      - name: Validate agent contracts
        run: |
          python scripts/validate-agent-schemas.py
      
      - name: Check AGENT_ENDPOINTS_JSON
        run: |
          python scripts/validate-agent-registry.py
```

Also create validation scripts:
- scripts/validate-agent-schemas.py
- scripts/validate-agent-registry.py

These should:
- Parse all agent main.py files
- Verify they implement required endpoints
- Check schema compatibility
- Report any drift

Deliverable: Schema validation workflow
```

#### Task 11.2: Policy Testing Workflow

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Create CI workflow for policy enforcement testing

File: .github/workflows/ai-policy-tests.yml

Test scenarios:
1. Local-only enforcement:
   - LIVE mode blocks external APIs ✅
   - PHI context blocks external APIs ✅
   - SENSITIVE classification blocks external APIs ✅

2. Policy violations:
   - Attempting external in local_only mode fails ❌
   - Error messages are clear
   - Audit logs are created

3. Agent routing:
   - Correct agent selected for each stage
   - Fallback logic works
   - Circuit breaker prevents cascading failures

```yaml
name: AI Policy Tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  policy-enforcement:
    runs-on: ubuntu-latest
    
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup services
        run: |
          docker-compose -f docker-compose.ai.yml up -d
          sleep 30  # Wait for services
      
      - name: Test local-only policy
        run: |
          npm test -- --testPathPattern=policy
        env:
          INFERENCE_POLICY: local_only
          MODE: LIVE
      
      - name: Test PHI protection
        run: |
          npm test -- --testPathPattern=phi-protection
      
      - name: Test circuit breaker
        run: |
          npm test -- --testPathPattern=circuit-breaker
      
      - name: Collect logs
        if: failure()
        run: |
          docker-compose -f docker-compose.ai.yml logs > ci-logs.txt
      
      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: ci-logs
          path: ci-logs.txt
```

Deliverable: Policy testing workflow
```

**Success Criteria for Day 11**:
- [ ] Schema validation workflow created
- [ ] Policy testing workflow created
- [ ] Validation scripts implemented
- [ ] Tests run in CI successfully
- [ ] Logs collected on failure

---

### **DAY 12: CI Workflows (Part 2)** 🔧

**Agent**: 🐳 DevOps Engineer (Claude Sonnet 4.5)

#### Task 12.1: Token Budget Monitoring

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Add token budget monitoring to CI

File: .github/workflows/ai-token-budget.yml

Purpose: Prevent runaway AI costs in production

Workflow should:
1. Track token usage per agent
2. Compare against budgets in AGENT_ROSTER
3. Alert if budget exceeded
4. Block merge if critical overrun

```yaml
name: AI Token Budget Check

on:
  pull_request:
    branches: [main]

jobs:
  check-budgets:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run token usage analysis
        run: |
          python scripts/analyze-token-usage.py
      
      - name: Compare to budgets
        run: |
          python scripts/check-token-budgets.py
      
      - name: Generate report
        run: |
          python scripts/generate-budget-report.py > budget-report.md
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('budget-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
      
      - name: Fail if budget exceeded
        run: |
          python scripts/check-token-budgets.py --fail-on-critical
```

Also create scripts:
- scripts/analyze-token-usage.py: Parse agent logs for token metrics
- scripts/check-token-budgets.py: Compare to AGENT_ROSTER budgets
- scripts/generate-budget-report.py: Create markdown report

Deliverable: Token budget monitoring workflow
```

#### Task 12.2: AI Improvement PR Workflow

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Create workflow that uses AI to suggest improvements

File: .github/workflows/ai-improvement-pr.yml

Concept: AI analyzes code, suggests improvements, creates PR

```yaml
name: AI Code Improvements

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:  # Manual trigger

jobs:
  ai-analysis:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Analyze agent code
        run: |
          python scripts/ai-code-analysis.py
      
      - name: Generate improvements
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/generate-improvements.py
      
      - name: Apply improvements
        run: |
          python scripts/apply-improvements.py
      
      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: 'AI: Automated code improvements'
          title: '🤖 AI-Suggested Improvements'
          body: |
            Automated improvements suggested by AI:
            
            - Code quality enhancements
            - Performance optimizations
            - Documentation updates
            
            Review carefully before merging.
          branch: ai-improvements
          labels: ai-generated, review-required
```

Scripts needed:
- scripts/ai-code-analysis.py: Use GPT-4o to analyze code
- scripts/generate-improvements.py: Generate improvement patches
- scripts/apply-improvements.py: Apply patches to codebase

Deliverable: AI-powered improvement workflow
```

**Success Criteria for Day 12**:
- [ ] Token budget workflow created
- [ ] Budget monitoring scripts work
- [ ] AI improvement workflow created
- [ ] Test PR generated successfully
- [ ] All CI workflows pass

---

### **DAY 13: Code Organization & Domain Packs** 📦

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)

#### Task 13.1: Create Common Utilities

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Refactor common code into shared utilities

Directory: services/agents/common/

Extract duplicated code from agents into:

common/
├── __init__.py
├── agent_base.py          # Move from _template
├── contracts.py           # TaskContract, AgentResponse schemas
├── streaming.py           # SSE utilities
├── circuit_breaker.py     # Circuit breaker implementation
├── ollama_client.py       # Shared Ollama client
├── chromadb_client.py     # Shared ChromaDB client
├── logging_config.py      # Standard logging setup
├── metrics.py             # Metrics collection
└── validation.py          # Input validation utilities

For each utility:
1. Extract from existing agents
2. Add comprehensive docstrings
3. Add type hints
4. Add unit tests
5. Update agents to import from common/

Update agent requirements.txt to include:
```
-e ../common  # Editable install for development
```

This allows: `from common.agent_base import AgentBase`

Benefit: Changes to base classes automatically propagate to all agents.

Deliverable: services/agents/common/ with shared utilities
```

#### Task 13.2: Domain Packs

**Agent**: 💻 Full-Stack Developer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Organize agents into domain-specific packs

Structure:
domains/
├── clinical/
│   ├── docker-compose.clinical.yml  # Only clinical agents
│   ├── README.md
│   └── agents/
│       ├── clinical-screener/
│       ├── adverse-event-analyzer/
│       └── protocol-validator/
├── generic/
│   ├── docker-compose.generic.yml
│   ├── README.md
│   └── agents/
│       ├── summarizer/
│       ├── translator/
│       └── classifier/
└── statistical/
    ├── docker-compose.statistical.yml
    ├── README.md
    └── agents/
        ├── power-calculator/
        └── statistical-analyzer/

Purpose:
- Deploy only needed agent sets
- Reduce resource usage
- Faster startup times
- Clear organization

Implementation:
1. Symlink agents to domains (don't duplicate code)
2. Create domain-specific docker-compose files
3. Update AGENT_ENDPOINTS_JSON for each domain
4. Document deployment scenarios

Example: docker-compose.clinical.yml
```yaml
version: '3.8'

services:
  clinical-screener:
    extends:
      file: ../../docker-compose.ai.yml
      service: clinical-screener
  
  adverse-event-analyzer:
    extends:
      file: ../../docker-compose.ai.yml
      service: adverse-event-analyzer
  
  # Include shared services
  ollama:
    extends:
      file: ../../docker-compose.ai.yml
      service: ollama
```

Deployment:
```bash
# Deploy only clinical agents
docker-compose -f domains/clinical/docker-compose.clinical.yml up

# Deploy full fleet
docker-compose -f docker-compose.ai.yml up
```

Deliverable: Domain-organized agent deployment configs
```

**Success Criteria for Day 13**:
- [ ] Common utilities extracted and working
- [ ] Agents import from common/
- [ ] Domain packs organized
- [ ] Domain-specific docker-compose files work
- [ ] Documentation updated

---

### **DAY 14: Final Polish & Documentation** 📝

**Agent**: 📚 Documentation Writer (GPT-4o)

#### Task 14.1: Master Documentation

**Prompt for Continue.dev**:
```
Model: GPT-4o

Task: Create comprehensive documentation for AI routing system

Files to create/update:

1. docs/AI_ROUTING_ARCHITECTURE.md:
   - System overview
   - Architecture diagrams
   - Component interaction
   - Data flow
   - Error handling
   - Monitoring

2. docs/AGENT_DEVELOPMENT_GUIDE.md:
   - How to create new agent
   - Using the template
   - Testing guidelines
   - Deployment checklist
   - Best practices

3. docs/DEPLOYMENT_GUIDE.md:
   - Full fleet deployment
   - Domain pack deployment
   - Environment configuration
   - Scaling considerations
   - Troubleshooting

4. docs/POLICY_ENFORCEMENT.md:
   - Inference policies explained
   - HIPAA compliance
   - PHI protection
   - Audit logging
   - Security best practices

5. docs/API_REFERENCE.md:
   - All endpoints documented
   - Request/response schemas
   - Error codes
   - Example requests (curl)
   - SDKs (if available)

6. UPDATE main README.md:
   - Quick start
   - Architecture overview
   - Link to detailed docs
   - Contributing guidelines

Requirements:
- Clear, concise writing
- Code examples
- Diagrams (mermaid.js)
- Screenshots where helpful
- Table of contents
- Cross-references

Deliverable: Complete documentation suite
```

#### Task 14.2: Final Testing & Cleanup

**Agent**: 🧪 Test Engineer (Claude Sonnet 4.5)

**Prompt for Continue.dev**:
```
Model: Claude Sonnet 4.5

Task: Final validation of entire system

Checklist:
1. All tests pass:
   - npm test (orchestrator)
   - pytest (agents)
   - Integration tests
   - E2E tests

2. Docker Compose works:
   - Full fleet starts successfully
   - Domain packs start successfully
   - Health checks pass
   - No port conflicts

3. CI/CD passes:
   - All workflows green
   - No schema drift
   - Policy tests pass
   - Token budgets within limits

4. Code quality:
   - No TypeScript errors
   - No linting errors
   - No security vulnerabilities (npm audit)
   - No hardcoded secrets

5. Documentation:
   - All docs exist
   - Links work
   - Code examples tested
   - READMEs complete

6. Cleanup:
   - Remove debug code
   - Remove unused dependencies
   - Remove TODO comments (or convert to issues)
   - Clean up console.logs

Create final test script:
scripts/final-validation.sh

This should run ALL tests and checks, providing a final go/no-go decision.

Deliverable: Clean, tested, production-ready system
```

**Success Criteria for Day 14**:
- [ ] All documentation complete and reviewed
- [ ] Final validation script passes
- [ ] All tests green
- [ ] No blockers for production
- [ ] Handoff documentation ready

---

## 📊 Phase 4 Completion Checklist

### CI/CD
- [ ] Schema validation workflow
- [ ] Policy testing workflow
- [ ] Token budget monitoring
- [ ] AI improvement PR workflow
- [ ] All workflows passing

### Code Organization
- [ ] Common utilities extracted
- [ ] Domain packs created
- [ ] Code cleanup complete
- [ ] No hardcoded secrets

### Documentation
- [ ] Architecture docs complete
- [ ] Development guide complete
- [ ] Deployment guide complete
- [ ] API reference complete
- [ ] README updated

### Final Validation
- [ ] All tests pass
- [ ] Docker deployment works
- [ ] Security audit passed
- [ ] Performance acceptable
- [ ] Production ready

---

## 🎯 Final Success Metrics

### Code Quality
- [ ] >80% test coverage
- [ ] 0 TypeScript errors
- [ ] 0 high/critical security issues
- [ ] All agents follow template
- [ ] Code style consistent

### Functionality
- [ ] Policy enforcement works 100%
- [ ] 25+ agents operational
- [ ] SSE streaming works
- [ ] Circuit breakers prevent cascades
- [ ] HIPAA compliance verified

### Performance
- [ ] Agent response time <2s avg
- [ ] Docker startup <5min
- [ ] Health checks respond <1s
- [ ] No memory leaks
- [ ] CPU usage acceptable

### Documentation
- [ ] All endpoints documented
- [ ] Deployment guide complete
- [ ] Troubleshooting guide complete
- [ ] Architecture diagrams clear
- [ ] Examples tested and working

---

## 🚀 Execution Strategy

### Model Usage Throughout Project

| Phase | Primary Model | Secondary | Reasoning |
|-------|--------------|-----------|-----------|
| 1: Foundation | Claude Opus 4.5 | Claude Sonnet 4.5 | Security critical |
| 2: E2E | Claude Sonnet 4.5 | Codestral | Complex integration |
| 3: Fleet | Mercury Coder | Codestral | Repetitive generation |
| 4: CI & Docs | Claude Sonnet 4.5 | GPT-4o | DevOps + writing |

### Parallelization Strategy

Execute these tasks in parallel:
- Days 8-10: Multiple agents simultaneously (different AI models)
- Day 11: Schema validation + policy tests (parallel CI jobs)
- Day 13: Common refactor + domain packs (independent work)

### Time Management

**Critical Path** (cannot be parallelized):
- Day 1 → Day 2 → Day 3 (foundation must be complete)
- Day 4 → Day 5 (agent wiring depends on foundation)

**Parallel Opportunities**:
- Days 8-10: Agent generation (5-10 at once)
- Day 11-12: Multiple CI workflows
- Day 13: Common utils + domain packs

---

## 💡 Tips for Continue.dev Execution

### Using Continue Effectively

1. **Start each day with context**:
   ```
   @codebase Review the current state of the AI routing implementation
   Read: docs/progress.md (if exists)
   Summarize: What's done, what's next
   ```

2. **Break large tasks into subtasks**:
   - Use Continue's task management
   - Mark completed subtasks
   - Track blockers

3. **Use appropriate models**:
   - Security: Claude Opus 4.5
   - Complex code: Claude Sonnet 4.5
   - Repetitive: Mercury/Codestral
   - Docs: GPT-4o

4. **Verify before moving on**:
   ```
   Run tests after each major change
   /phi-check security-sensitive code
   /docker-check compose files
   ```

5. **Save progress frequently**:
   - Commit after each task
   - Push daily
   - Update progress docs

### Handling Blockers

If stuck:
1. Use Grok for alternative approaches
2. Review existing code with semantic search
3. Check documentation
4. Ask for clarification in commit message
5. Create issue for later if non-blocking

---

## 📁 File Organization

Expected final structure:
```
services/
├── orchestrator/
│   ├── src/
│   │   ├── clients/
│   │   │   └── agentClient.ts
│   │   ├── routes/
│   │   │   └── ai-router.ts
│   │   └── services/
│   │       ├── model-router.service.ts
│   │       └── custom-agent-dispatcher.ts
│   └── __tests__/
├── agents/
│   ├── _template/
│   ├── common/
│   ├── agent-stage2-lit/
│   ├── clinical-screener/
│   └── ... (25+ more)
└── domains/
    ├── clinical/
    ├── generic/
    └── statistical/

docs/
├── AI_ROUTING_ARCHITECTURE.md
├── AGENT_ROSTER.md
├── AGENT_DEVELOPMENT_GUIDE.md
├── DEPLOYMENT_GUIDE.md
├── POLICY_ENFORCEMENT.md
└── API_REFERENCE.md

.github/
└── workflows/
    ├── ai-schema-validation.yml
    ├── ai-policy-tests.yml
    ├── ai-token-budget.yml
    └── ai-improvement-pr.yml

scripts/
├── test-agent-architecture.sh
├── validate-agent-schemas.py
├── validate-agent-registry.py
├── analyze-token-usage.py
└── final-validation.sh
```

---

## 🎉 Project Completion Criteria

Project is complete when:
- [ ] All 4 phases delivered
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Docker deployment working
- [ ] CI/CD pipelines green
- [ ] Security audit passed
- [ ] HIPAA compliance verified
- [ ] Performance benchmarks met
- [ ] Stakeholder demo successful

---

**Ready to execute! Start with Phase 1, Day 1. Good luck! 🚀**

*Use Continue.dev's task management to track progress through each phase.*
