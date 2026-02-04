# Phase 4: End-to-End Testing & Production Deployment

## Completed (Phases 1-3)
- ✅ All 20 Python stage agents with BaseStageAgent pattern
- ✅ Unit tests for all stages + integration test
- ✅ Workflow orchestrator with STAGE_REGISTRY
- ✅ TypeScript bridge services (5 services + OpenAPI spec)
- ✅ Logging, metrics, error handling, config management
- ✅ Replit UI with design tokens, API endpoints, stage execution

---

## 🖥️ CURSOR PROMPT - E2E Testing & CI/CD Pipeline

```
# ResearchFlow Phase 4: E2E Testing & CI/CD Pipeline

## Context
Phase 3 added logging, metrics, and error handling. Now set up comprehensive E2E testing and CI/CD pipeline.

## Tasks

### 1. E2E Test Suite
Create `tests/e2e/test_full_workflow.py`:
- Test complete 20-stage workflow execution
- Mock external services (LLM, databases)
- Verify stage transitions and context passing
- Test error recovery and retry logic
- Validate metrics emission

### 2. CI/CD Pipeline
Create `.github/workflows/ci.yml`:
- Run on push to main and PRs
- Python lint (ruff/flake8)
- TypeScript lint (eslint)
- Unit tests with pytest
- Integration tests
- Coverage report (>80% target)
- Build Docker images

### 3. Docker Configuration
Create `services/worker/Dockerfile`:
- Python 3.11 base image
- Install dependencies from requirements.txt
- Health check endpoint
- Non-root user for security

Create `docker-compose.yml`:
- Worker service
- Orchestrator service
- Redis for caching
- PostgreSQL for persistence

### 4. Environment Templates
Create `.env.example`:
- All required environment variables
- Documentation comments
- Development defaults

### 5. Pre-commit Hooks
Create `.pre-commit-config.yaml`:
- Python formatting (black)
- Import sorting (isort)
- Type checking (mypy)
- Security scanning (bandit)

## File Structure
```
.github/workflows/ci.yml
services/worker/Dockerfile
docker-compose.yml
.env.example
.pre-commit-config.yaml
tests/e2e/test_full_workflow.py
```
```

---

## 🔧 COMPOSIO PROMPT - Health System & Service Mesh

```
# ResearchFlow Phase 4: Health System & Service Mesh

## Context
Phase 3 started router integration. Now complete the health check system and service mesh configuration.

## Tasks

### 1. Complete Health Check System
Create `services/orchestrator/src/health/index.ts`:
- Aggregate health endpoint at `/health`
- Individual service health at `/health/services/{name}`
- Database connectivity check
- Redis connectivity check
- Memory and CPU usage reporting
- Graceful degradation status

### 2. Service Discovery
Create `services/orchestrator/src/services/discovery.ts`:
- Service registry with health status
- Automatic failover logic
- Load balancing between instances
- Service version tracking

### 3. Circuit Breaker Implementation
Create `services/orchestrator/src/utils/circuit-breaker.ts`:
- States: CLOSED, OPEN, HALF_OPEN
- Configurable failure threshold
- Recovery timeout
- Event emitter for state changes
- Per-service circuit breakers

### 4. Request Tracing
Create `services/orchestrator/src/utils/tracing.ts`:
- Correlation ID generation (UUID)
- Request/response logging
- Timing metrics per service call
- Trace context propagation headers

### 5. Finalize Router Wiring
Update `services/orchestrator/src/routes/bridge.ts`:
- Wire all 5 bridge services
- Add OpenAPI validation middleware
- Per-service rate limiting
- Request/response logging

### 6. Commit Changes
After completing all files, commit with message:
"feat(orchestrator): add health system, circuit breaker, and service mesh"
```

---

## 🎨 FIGMA PROMPT - Onboarding & Mobile Responsive

```
# ResearchFlow Phase 4: Onboarding & Mobile Responsive

## Context
Phase 3 created error states and loading components. Now design user onboarding and mobile responsive layouts.

## Tasks

### 1. User Onboarding Flow
Create onboarding screens:
- Welcome screen with product overview
- Step 1: Create first project
- Step 2: Configure workflow stages
- Step 3: Run first analysis
- Completion celebration screen
- Skip option for experienced users

### 2. Mobile Dashboard
Design mobile-responsive dashboard:
- Collapsible sidebar navigation
- Stacked project cards
- Touch-friendly stage controls
- Bottom navigation bar
- Pull-to-refresh gesture

### 3. Mobile Stage Detail
Design mobile stage detail view:
- Vertical layout for inputs/outputs
- Expandable log sections
- Sticky action buttons at bottom
- Swipe gestures for navigation

### 4. Empty State Illustrations
Create illustrations for:
- No projects yet (welcome illustration)
- No workflow runs (start illustration)
- Search no results (magnifying glass)
- Error state (broken connection)

### 5. Notification System
Design notification components:
- Push notification mockups
- In-app notification center
- Notification preferences screen
- Badge indicators

## Design Specs
- Mobile breakpoint: 768px
- Touch target: minimum 44x44px
- Onboarding: maximum 5 steps
- Use existing color palette
```

---

## 🚀 REPLIT PROMPT - Production Deploy & WebSocket

```
# ResearchFlow Phase 4: Production Deploy & WebSocket Updates

## Context
Phase 3 implemented API client and tested locally. Now deploy to production and add real-time updates.

## Tasks

### 1. Production Deployment
- Click "Publish now" to deploy
- Configure custom domain (if available)
- Set production environment variables
- Enable HTTPS

### 2. WebSocket Connection
Create `src/lib/websocket.ts`:
- WebSocket client singleton
- Auto-reconnect logic
- Message type handlers
- Connection state management

### 3. Real-time Stage Updates
Implement live updates:
- Stage status changes (pending → running → complete)
- Log streaming during execution
- Progress percentage updates
- Completion notifications with toast

### 4. Polling Fallback
Create `src/lib/polling.ts`:
- Fallback when WebSocket unavailable
- Configurable polling interval (2 seconds)
- Automatic switch between WebSocket/polling
- Battery-efficient polling on mobile

### 5. Error Boundary
Create `src/components/ErrorBoundary.tsx`:
- Catch React errors gracefully
- User-friendly error message
- Retry button
- Error reporting to console

### 6. Performance Optimization
- Lazy load stage detail components
- Memoize expensive computations
- Virtualize long log lists
- Image optimization

## Deployment Checklist
- [ ] All environment variables set
- [ ] CORS configured for production
- [ ] Error tracking enabled
- [ ] Analytics initialized
```

---

## Execution Order

All 4 prompts can run in parallel:

| Platform | Focus | Key Deliverables |
|----------|-------|------------------|
| Cursor | E2E tests, CI/CD | GitHub Actions, Docker, pre-commit |
| Composio | Health system, service mesh | Circuit breaker, tracing, discovery |
| Figma | Onboarding, mobile | User flows, responsive design |
| Replit | Production deploy, WebSocket | Live updates, error boundaries |

## After Phase 4
System will be ready for:
- Beta user testing
- Production traffic
- Monitoring and alerting
- Continuous deployment
