# Phase 3: Integration & Deployment Parallel Task Prompts

## Current State (Phase 2 Completed)
- ✅ All 20 Python stage agents implemented
- ✅ Unit tests for stages 1-20
- ✅ Integration test for full 20-stage workflow
- ✅ Workflow orchestrator (`orchestrator.py`)
- ✅ TypeScript bridge services (compliance-checker, final-phi-scan, archive-manager, impact-tracker, publication-prep)
- ✅ OpenAPI spec for bridge services
- ✅ Replit UI with design tokens, API endpoints, stage execution buttons
- ✅ STAGE_REGISTRY mapping all 20 stages

---

## 🖥️ CURSOR PROMPT - App Integration & Monitoring

```
# ResearchFlow Phase 3: App Integration & Monitoring

## Context
The workflow orchestrator and all 20 stage agents are complete. Now wire them into the main application with proper logging, monitoring, and error handling.

## Tasks

### 1. Main App Integration
Create `services/worker/src/main.py`:
- FastAPI application entry point
- Import and register orchestrator
- Health check endpoint at `/health`
- Workflow execution endpoint at `/api/workflow/execute`
- Stage status endpoint at `/api/workflow/stages/{stage_id}/status`

### 2. Logging Infrastructure
Create `services/worker/src/utils/logging.py`:
- Structured JSON logging with timestamps
- Log levels: DEBUG, INFO, WARNING, ERROR
- Stage execution logs with timing metrics
- Context propagation (project_id, stage_id, execution_id)

### 3. Metrics & Monitoring
Create `services/worker/src/utils/metrics.py`:
- Stage execution duration tracking
- Success/failure counters per stage
- Queue depth monitoring
- Memory usage tracking
- Export format compatible with Prometheus

### 4. Error Handling & Recovery
Create `services/worker/src/utils/error_handler.py`:
- Custom exception classes for each failure type
- Retry logic with exponential backoff
- Dead letter queue for failed stages
- Graceful degradation strategies

### 5. Configuration Management
Create `services/worker/src/config.py`:
- Environment-based configuration
- Stage-specific settings
- Bridge service URLs
- Timeout configurations
- Feature flags for stages

### 6. Update Orchestrator
Modify `services/worker/src/workflow_engine/orchestrator.py`:
- Add logging calls at each stage
- Emit metrics for monitoring
- Handle errors with proper recovery
- Support partial workflow execution (start from stage N)

## File Structure
```
services/worker/src/
├── main.py                    # FastAPI app entry
├── config.py                  # Configuration management
├── utils/
│   ├── __init__.py
│   ├── logging.py            # Structured logging
│   ├── metrics.py            # Prometheus metrics
│   └── error_handler.py      # Error handling
└── workflow_engine/
    └── orchestrator.py       # Updated with logging/metrics
```

## Requirements
- Use FastAPI for the web framework
- Use structlog for structured logging
- Use prometheus_client for metrics
- All endpoints should return JSON responses
- Include OpenAPI documentation
```

---

## 🔧 COMPOSIO PROMPT - Router Integration & Health Checks

```
# ResearchFlow Phase 3: Router Integration & Health Checks

## Context
Bridge services are implemented (compliance-checker, final-phi-scan, archive-manager, impact-tracker, publication-prep). Now wire them into the main router and add comprehensive health monitoring.

## Tasks

### 1. Update Main Router
Modify `services/orchestrator/src/routes/bridge.ts`:
- Import all 5 new bridge services
- Add routes for each service method
- Implement request validation using OpenAPI spec
- Add rate limiting per service

### 2. Service Registry
Create `services/orchestrator/src/services/registry.ts`:
- Central registry of all bridge services
- Service discovery pattern
- Lazy initialization
- Dependency injection support

### 3. Health Check System
Create `services/orchestrator/src/health/index.ts`:
- Aggregate health endpoint at `/health`
- Individual service health at `/health/services/{name}`
- Database connectivity check
- External API connectivity check
- Memory and CPU usage reporting

### 4. Circuit Breaker Pattern
Create `services/orchestrator/src/utils/circuit-breaker.ts`:
- Circuit breaker for each bridge service
- States: CLOSED, OPEN, HALF_OPEN
- Failure threshold configuration
- Recovery timeout settings
- Event emitter for state changes

### 5. Request Tracing
Create `services/orchestrator/src/utils/tracing.ts`:
- Correlation ID generation
- Request/response logging
- Timing metrics per service call
- Trace context propagation

### 6. Error Response Standardization
Create `services/orchestrator/src/utils/error-response.ts`:
- Standardized error format
- Error codes for each failure type
- Stack trace handling (dev vs prod)
- Client-friendly error messages

## Routes to Add
POST /api/services/compliance-checker/check
POST /api/services/compliance-checker/generate-report
POST /api/services/final-phi-scan/scan
POST /api/services/archive-manager/archive
GET  /api/services/archive-manager/retrieve
POST /api/services/impact-tracker/track
GET  /api/services/impact-tracker/metrics
POST /api/services/publication-prep/prepare
GET  /api/services/publication-prep/status

## Health Response Format
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "ISO8601",
  "services": {
    "compliance-checker": { "status": "up", "latency_ms": 45 },
    "final-phi-scan": { "status": "up", "latency_ms": 23 },
    ...
  },
  "database": { "status": "up", "connections": 5 },
  "memory": { "used_mb": 256, "total_mb": 512 }
}
```

---

## 🎨 FIGMA PROMPT - Advanced UI States & Components

```
# ResearchFlow Phase 3: Advanced UI States & Components

## Context
Basic dashboard and stage workflow visualization complete. Now create detailed UI states for error handling, loading, and stage details.

## Design Tasks

### 1. Loading States
Create loading state components:
- Skeleton loaders for stage cards
- Progress indicators for workflow execution
- Shimmer effects for data loading
- Spinner variations (small, medium, large)

### 2. Error States
Design error UI components:
- Stage failure indicator (red border, error icon)
- Error message toast notifications
- Retry button styling
- Error detail modal with stack trace

### 3. Stage Detail View
Create detailed stage inspection screen:
- Stage header with status badge
- Input/output data preview
- Execution timeline with timestamps
- Logs viewer with filtering
- Action buttons (retry, skip, rollback)

### 4. Workflow Progress Tracker
Design workflow progress component:
- Horizontal timeline view
- Vertical list view (mobile)
- Stage status indicators (pending, running, success, failed, skipped)
- Estimated time remaining
- Current stage highlight

### 5. Settings & Configuration
Create settings screen designs:
- Stage toggle switches (enable/disable)
- Timeout configuration inputs
- Notification preferences
- API key management
- Theme switcher (light/dark)

### 6. Empty States
Design empty state illustrations:
- No projects yet
- No workflow runs
- No results found
- First-time user onboarding

## Color Usage
- Primary #4A7FC1: Action buttons, links
- Success #4CAF50: Completed stages, success messages
- Workflow #9575CD: Stage indicators, progress
- Error #E57373: Failed stages, error messages
- Warning #FFB74D: Warnings, degraded status
- Neutral #78909C: Secondary text, borders

## Component Library Additions
- Toast notification component
- Modal dialog component
- Dropdown menu component
- Toggle switch component
- Progress bar component
- Badge/chip component
- Tooltip component
```

---

## 🚀 REPLIT PROMPT - Production Deployment & Real API Connection

```
# ResearchFlow Phase 3: Production Deployment & Real API Connection

## Context
UI is complete with design tokens, mock API endpoints, and stage execution buttons. Now prepare for production deployment and real backend connection.

## Tasks

### 1. Environment Configuration
Create environment management:
- .env.example file with all variables
- Environment detection (dev/staging/prod)
- API base URL configuration
- Feature flags for experimental features

### 2. Real API Client
Create `src/api/client.ts`:
- Axios or fetch wrapper
- Base URL from environment
- Request/response interceptors
- Authentication header injection
- Error handling and retry logic

### 3. API Service Layer
Create `src/api/services/`:
- `workflow.ts`: Workflow execution, status polling
- `stages.ts`: Stage details, logs retrieval
- `health.ts`: Backend health checks
- `projects.ts`: Project CRUD operations

### 4. State Management
Implement proper state management:
- Workflow execution state
- Stage status polling (every 2 seconds during execution)
- Error state handling
- Loading state management
- Optimistic updates

### 5. Real-time Updates
Add WebSocket or polling for live updates:
- Stage status changes
- Log streaming during execution
- Progress percentage updates
- Completion notifications

### 6. Production Build
Prepare for deployment:
- Build optimization
- Asset minification
- Environment variable injection
- Error boundary components
- Analytics integration (optional)

### 7. Deployment Configuration
Create deployment configs:
- Vercel/Netlify configuration
- Docker file for containerized deployment
- Health check endpoint for load balancer
- CORS configuration

## API Endpoints to Connect
Base URL: Configure via VITE_API_BASE_URL

POST /api/workflow/execute
  Body: { project_id, start_stage?, end_stage? }
  Response: { execution_id, status }

GET /api/workflow/executions/{execution_id}
  Response: { status, current_stage, stages: [...] }

GET /api/workflow/stages/{stage_id}/logs
  Response: { logs: [...] }

GET /health
  Response: { status, services: {...} }

## Environment Variables
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENV=development
VITE_ENABLE_ANALYTICS=false
```

---

## Execution Order

All 4 prompts can be executed in parallel:

| Platform | Focus Area | Dependencies |
|----------|-----------|--------------|
| Cursor | App integration, logging, metrics | None |
| Composio | Router wiring, health checks | None |
| Figma | Advanced UI states | None |
| Replit | Deployment, real API connection | None |

After Phase 3, the system will be ready for:
- End-to-end testing
- Staging deployment
- User acceptance testing
