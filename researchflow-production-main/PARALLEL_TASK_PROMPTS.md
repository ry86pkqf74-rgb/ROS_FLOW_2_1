# ResearchFlow - Parallel Execution Task Prompts

## Current State Summary
- ✅ All 20 Python stage agents implemented (GitHub synced)
- ✅ TypeScript bridge services wired
- ✅ UI mockups/design system created in Replit
- 🔄 Next: Integration, testing, and production readiness

---

## 1. CURSOR - Python Backend Tasks

### Prompt for Cursor:

```
ResearchFlow 20-Stage Agent Architecture - Phase 2: Testing & Integration

CONTEXT:
All 20 stage agents are implemented in services/worker/src/workflow_engine/stages/
Each agent inherits from BaseStageAgent and implements execute(), get_tools(), get_prompt_template()

TASKS:
1. Create comprehensive unit tests for stages 14-20:
   - tests/unit/workflow_engine/stages/test_stage_14_ethical.py
   - tests/unit/workflow_engine/stages/test_stage_16_handoff.py
   - tests/unit/workflow_engine/stages/test_stage_17_archiving.py
   - tests/unit/workflow_engine/stages/test_stage_18_impact.py
   - tests/unit/workflow_engine/stages/test_stage_19_dissemination.py
   - tests/unit/workflow_engine/stages/test_stage_20_conference.py

2. Create integration test for full 20-stage workflow:
   - tests/integration/test_full_workflow_pipeline.py
   - Mock bridge service calls
   - Test stage transitions and data flow
   - Verify StageResult serialization through pipeline

3. Add stage registration in __init__.py:
   - Update services/worker/src/workflow_engine/stages/__init__.py
   - Export all 20 stage agent classes
   - Create STAGE_REGISTRY dict mapping stage_id to agent class

4. Create workflow orchestrator:
   - services/worker/src/workflow_engine/orchestrator.py
   - Sequential stage execution with context passing
   - Error handling and retry logic
   - Stage skip/resume capability

PATTERNS TO FOLLOW:
- See existing test_stage_13_internal_review.py for test patterns
- Use pytest fixtures and mocks
- Test both success and failure paths
```

---

## 2. COMPOSIO - TypeScript Bridge Services

### Prompt for Composio:

```
ResearchFlow Bridge Services - Phase 2: Complete Service Implementation

REPO: ry86pkqf74-rgb/researchflow-production
PATH: services/orchestrator/src/services/

CONTEXT:
Bridge router exists at /api/services/{serviceName}/{methodName}
Several service stubs exist, need full implementation

TASKS:
1. Complete these bridge services with actual logic:
   - compliance-checker/index.ts - HIPAA/IRB/GDPR compliance scanning
   - final-phi-scan/index.ts - Protected Health Information detection
   - archive-manager/index.ts - Project archival and retrieval
   - impact-tracker/index.ts - Citation and impact metrics
   - publication-prep/index.ts - Journal submission preparation

2. Add OpenAPI documentation:
   - Create services/orchestrator/src/openapi/bridge-services.yaml
   - Document all service endpoints
   - Include request/response schemas

3. Create service health checks:
   - services/orchestrator/src/services/health/index.ts
   - Aggregate health status for all bridge services
   - Add /api/services/health endpoint

4. Wire remaining services in bridge router:
   - Update services/orchestrator/src/routes/bridge.ts
   - Import and register new services
   - Add error handling middleware

EXISTING PATTERNS:
- See clarity-analyzer, claim-verifier for service structure
- Services export singleton instances
- Methods return typed promises
```

---

## 3. FIGMA - Design System & Components

### Prompt for Figma MCP:

```
ResearchFlow Design System - Component Library

CONTEXT:
Replit created UI mockups at research-flow-design.replit.app
Need to formalize as Figma design system

TASKS:
1. Create design tokens file:
   - Colors: Primary (indigo), Secondary (amber), Semantic (success/warning/error)
   - Typography: Inter font family, size scale, line heights
   - Spacing: 4px base unit scale
   - Border radius: sm/md/lg/xl
   - Shadows: sm/md/lg for elevation

2. Create component library:
   - StageCard: Shows stage number, name, status, progress
   - ProjectCard: Project overview with phase progress bars
   - PipelineVisualization: 20-stage horizontal timeline
   - ActivityFeed: Recent updates list
   - StatsCard: Metric with label and delta
   - PhaseIndicator: Colored badge for SETUP/ANALYSIS/WRITING/PUBLISH

3. Create page templates:
   - Dashboard: Stats row, active projects grid, activity feed
   - Project Detail: Pipeline view, current stage detail, team
   - Stage Detail: Inputs, outputs, AI agent status, logs

4. Export as:
   - CSS variables file
   - Tailwind config
   - React component specs
```

---

## 4. REPLIT - Production Deployment

### Prompt for Replit:

```
ResearchFlow Design App - Production Deployment & API Integration

CURRENT STATE:
- Design system and dashboard mockups complete
- Running on port 5000
- Primary URL: research-flow-design.replit.app

TASKS:
1. Publish the application:
   - Click "Publish now" for autoscale deployment
   - Configure production database settings if needed
   - Set up environment variables

2. Add API integration layer:
   - Create /api routes for mock data
   - GET /api/projects - list projects with stages
   - GET /api/projects/:id - project detail
   - GET /api/stages/:id - stage detail with AI agent status
   - POST /api/projects/:id/stages/:stageId/execute - trigger stage

3. Add interactive features:
   - Stage click navigation from pipeline view
   - Real-time progress updates (WebSocket or polling)
   - Stage execution trigger buttons
   - Activity feed auto-refresh

4. Add authentication placeholder:
   - Login/logout UI
   - User profile dropdown
   - Role-based navigation (researcher, admin, reviewer)

5. Export design tokens:
   - Create /design-tokens.json endpoint
   - Export CSS variables file
   - Create Tailwind config export
```

---

## Execution Order

**Parallel Group 1** (Can run simultaneously):
- Cursor: Unit tests for stages 14-20
- Composio: Complete bridge services
- Replit: Publish app + add API routes

**Parallel Group 2** (After Group 1):
- Cursor: Integration tests + orchestrator
- Figma: Formalize design system
- Replit: Interactive features

**Final Integration**:
- Connect Replit frontend to real backend APIs
- End-to-end testing
- Production deployment
