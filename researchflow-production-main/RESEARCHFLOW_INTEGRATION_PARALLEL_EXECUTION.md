# ResearchFlow Integration - Parallel Execution Plan
## Composio + Cursor Only (No CODEX)
### February 2, 2026

---

## Executive Summary

After comprehensive review of the current repository state versus the integration plan documents, the actual implementation status is **significantly better** than documented:

| Component | Documented State | Actual State |
|-----------|-----------------|--------------|
| Stage UI Components | 3/20 (15%) | **21/21 (100%)** |
| Quality.ts Route | Mocked | **Real Implementation** |
| Governance-simulate.ts | Mocked | **Real Implementation** |
| ChromaDB Integration | Incomplete | **Files Exist** |
| HTI-1 Transparency | Missing | **Routes & Pipeline Exist** |
| TRIPOD+AI/CONSORT-AI | Missing | **Checklist Files Exist** |
| Load Testing | Missing | **load_test.js + GitHub Actions Exist** |
| E2E Tests | ~5 | **25+ Test Files Exist** |

### True Remaining Gaps

1. **Manuscript Generators** - Only `evidence_bundle.py` exists, missing IMRaD generators
2. **docker-compose.test.yml** - Specific test environment config missing
3. **PHI Gate Integration** - Need verification in all stage components
4. **E2E Test Completeness** - Full 20-stage workflow tests need completion
5. **Load Test Enhancement** - k6 scripts need full workflow coverage

---

## Phase Breakdown (2 Agents)

### Agent Assignment Strategy

| Agent | Focus Area | Strength |
|-------|-----------|----------|
| **COMPOSIO** | Backend/Worker/Python | API, generators, compliance |
| **CURSOR** | Frontend/TypeScript/Tests | UI components, E2E tests, integration |

---

## PHASE 1: Foundation (Week 1)

### COMPOSIO TASK 1.1: docker-compose.test.yml
**Priority:** P1 | **Estimate:** 4 hours

### CURSOR TASK 1.1: E2E Test Infrastructure
**Priority:** P1 | **Estimate:** 4 hours

---

## PHASE 2: Manuscript Engine (Week 2-3)

### COMPOSIO TASK 2.1: Abstract Generator
**Priority:** P1 | **Estimate:** 6 hours

### COMPOSIO TASK 2.2: Methods Generator
**Priority:** P1 | **Estimate:** 6 hours

### COMPOSIO TASK 2.3: Results Generator
**Priority:** P1 | **Estimate:** 6 hours

### COMPOSIO TASK 2.4: Discussion Generator
**Priority:** P1 | **Estimate:** 6 hours

### COMPOSIO TASK 2.5: IMRaD Assembler
**Priority:** P1 | **Estimate:** 8 hours

### CURSOR TASK 2.1: Manuscript Editor Integration
**Priority:** P2 | **Estimate:** 8 hours

---

## PHASE 3: PHI & Compliance (Week 3-4)

### COMPOSIO TASK 3.1: PHI Scanner API Enhancement
**Priority:** P1 | **Estimate:** 6 hours

### CURSOR TASK 3.1: PHI Gates in Stage Components
**Priority:** P1 | **Estimate:** 8 hours

### CURSOR TASK 3.2: Compliance Dashboard UI
**Priority:** P2 | **Estimate:** 6 hours

---

## PHASE 4: Testing & Verification (Week 4-5)

### COMPOSIO TASK 4.1: API Integration Tests
**Priority:** P1 | **Estimate:** 8 hours

### CURSOR TASK 4.1: Full Workflow E2E Tests
**Priority:** P1 | **Estimate:** 10 hours

### CURSOR TASK 4.2: Load Testing Enhancement
**Priority:** P2 | **Estimate:** 6 hours

---

# DETAILED PROMPTS FOR EACH AGENT

---

## COMPOSIO PROMPTS

### COMPOSIO PROMPT 1.1: docker-compose.test.yml
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/docker-compose-test'

## TASK: Create docker-compose.test.yml for Isolated Testing

### CONTEXT
The repo has many docker-compose files (prod, minimal, monitoring, etc.) but lacks a dedicated test environment configuration.

### REQUIREMENTS

1. Create `docker-compose.test.yml` with:
   - Isolated network for tests
   - Ephemeral volumes (tmpfs where possible)
   - Test database with seeded data
   - MockServer for external APIs
   - Health checks with shorter intervals
   - Resource limits appropriate for CI

2. Create `scripts/test-env.sh`:
   - Start test environment
   - Wait for healthy status
   - Run migrations
   - Seed test data
   - Return exit codes properly

3. Create `tests/fixtures/seed-data.sql`:
   - Test users (researcher, steward, admin)
   - Test projects in each governance mode
   - Sample datasets
   - Test workflow states

### FILE LOCATIONS
- docker-compose.test.yml (root)
- scripts/test-env.sh
- tests/fixtures/seed-data.sql
- tests/fixtures/test-config.json

### VERIFICATION STEPS
1. Run: docker compose -f docker-compose.test.yml up -d
2. Verify all services healthy
3. Run: ./scripts/test-env.sh
4. Verify test data seeded

### GIT REQUIREMENTS
After completing the task:
1. Stage files: git add docker-compose.test.yml scripts/test-env.sh tests/fixtures/
2. Commit: git commit -m "feat(infra): add docker-compose.test.yml for isolated testing

- Add dedicated test environment configuration
- Add test-env.sh startup script
- Add seed data fixtures
- Configure ephemeral volumes for CI

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/docker-compose-test
4. VERIFY push succeeded - if error, retry with: git push --force-with-lease origin feature/docker-compose-test
```

---

### COMPOSIO PROMPT 2.1: Abstract Generator
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/manuscript-abstract-generator'

## TASK: Implement Abstract Generator for Manuscript Engine

### CONTEXT
The manuscript engine needs IMRaD section generators. Currently only evidence_bundle.py exists in services/worker/src/generators/.

### REQUIREMENTS

1. Create `services/worker/src/generators/abstract_generator.py`:
   - AbstractGenerator class
   - Input: research question, hypothesis, key findings, methods summary
   - Output: structured abstract (Background, Methods, Results, Conclusions)
   - Support multiple abstract styles (structured, unstructured, graphical)
   - Word count constraints (150-350 words configurable)
   - AI-powered generation with quality scoring

2. Create `services/worker/src/generators/templates/abstract_templates.py`:
   - IMRAD template
   - BMJ structured template
   - CONSORT abstract template
   - Plain language summary template

3. Update `services/worker/src/generators/__init__.py`:
   - Export AbstractGenerator
   - Export template utilities

4. Create unit tests in `tests/unit/generators/test_abstract_generator.py`:
   - Test structured abstract generation
   - Test word count enforcement
   - Test template switching
   - Test AI integration

### FILE STRUCTURE
services/worker/src/generators/
├── __init__.py (update)
├── abstract_generator.py (new)
├── templates/
│   ├── __init__.py (new)
│   └── abstract_templates.py (new)

### TECHNICAL SPECS
- Use LangChain for AI generation
- Implement retry logic for AI calls
- Include transparency logging per HTI-1
- Support both Claude and GPT-4 backends

### GIT REQUIREMENTS
After completing the task:
1. Stage: git add services/worker/src/generators/
2. Commit: git commit -m "feat(manuscript): implement AbstractGenerator for IMRaD papers

- Add AbstractGenerator class with structured output
- Add abstract templates (IMRAD, BMJ, CONSORT)
- Support configurable word counts
- Include AI transparency logging

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/manuscript-abstract-generator
4. VERIFY: git log --oneline -1 && git status
```

---

### COMPOSIO PROMPT 2.2: Methods Generator
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/manuscript-methods-generator'

## TASK: Implement Methods Section Generator

### CONTEXT
Following the AbstractGenerator pattern, implement the Methods section generator.

### REQUIREMENTS

1. Create `services/worker/src/generators/methods_generator.py`:
   - MethodsGenerator class
   - Input: study design, population, intervention, outcomes, statistical plan
   - Output: complete Methods section with subsections
   - Subsections: Study Design, Participants, Intervention, Outcomes, Statistical Analysis
   - CONSORT/STROBE compliance checking
   - Reproducibility score calculation

2. Create `services/worker/src/generators/templates/methods_templates.py`:
   - RCT methods template
   - Cohort study template
   - Case-control template
   - Cross-sectional template
   - Systematic review template

3. Integrate with existing compliance checkers:
   - Link to services/worker/src/agents/compliance/checklists/consortai.py
   - Link to config/consort-ai-checklist.yaml

4. Create tests in `tests/unit/generators/test_methods_generator.py`

### TECHNICAL SPECS
- Parse protocol artifacts from Stage02
- Extract statistical plan from Stage07
- Generate reproducible methods text
- Include TRIPOD+AI items where applicable

### GIT REQUIREMENTS
After completing:
1. Stage: git add services/worker/src/generators/ tests/unit/generators/
2. Commit: git commit -m "feat(manuscript): implement MethodsGenerator with CONSORT compliance

- Add MethodsGenerator class with study-type templates
- Integrate CONSORT-AI and TRIPOD-AI compliance checking
- Add reproducibility scoring
- Support RCT, cohort, case-control, cross-sectional studies

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/manuscript-methods-generator
4. VERIFY push success
```

---

### COMPOSIO PROMPT 2.3: Results Generator
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/manuscript-results-generator'

## TASK: Implement Results Section Generator

### REQUIREMENTS

1. Create `services/worker/src/generators/results_generator.py`:
   - ResultsGenerator class
   - Input: statistical outputs, tables, figures, key findings
   - Output: narrative results with embedded references
   - Features:
     - Table/figure caption generation
     - Statistical result formatting (p-values, CIs, effect sizes)
     - Flow diagram text (CONSORT/PRISMA)
     - Sensitivity analysis summary

2. Create `services/worker/src/generators/templates/results_templates.py`:
   - Primary outcome template
   - Secondary outcomes template
   - Subgroup analysis template
   - Sensitivity analysis template

3. Create `services/worker/src/generators/utils/stat_formatter.py`:
   - Format p-values per journal style
   - Format confidence intervals
   - Format effect sizes
   - APA/Vancouver number formatting

4. Tests in `tests/unit/generators/test_results_generator.py`

### INTEGRATION POINTS
- Pull from Stage07 (Statistical Modeling) outputs
- Link to Stage08 (Visualization) figure references
- Connect to statistical audit trails

### GIT REQUIREMENTS
1. Stage: git add services/worker/src/generators/
2. Commit: git commit -m "feat(manuscript): implement ResultsGenerator with statistical formatting

- Add ResultsGenerator with table/figure integration
- Add statistical formatting utilities (p-values, CIs)
- Support CONSORT flow diagram text generation
- Include sensitivity analysis templates

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/manuscript-results-generator
```

---

### COMPOSIO PROMPT 2.4: Discussion Generator
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/manuscript-discussion-generator'

## TASK: Implement Discussion Section Generator

### REQUIREMENTS

1. Create `services/worker/src/generators/discussion_generator.py`:
   - DiscussionGenerator class
   - Input: key findings, literature context, limitations, implications
   - Output: structured discussion with:
     - Principal findings summary
     - Comparison with literature
     - Strengths and limitations
     - Clinical/policy implications
     - Future research directions
   - AI-powered synthesis with citation integration

2. Create `services/worker/src/generators/templates/discussion_templates.py`:
   - Standard discussion template
   - Brief report discussion
   - Systematic review discussion
   - Commentary discussion

3. Implement literature synthesis:
   - Pull from Stage03 (Literature Search) results
   - Compare findings with cited papers
   - Identify agreements/contradictions

4. Tests in `tests/unit/generators/test_discussion_generator.py`

### TECHNICAL SPECS
- Use RAG to retrieve relevant literature context
- Score discussion completeness against CONSORT items
- Generate limitation statements from methods

### GIT REQUIREMENTS
1. Stage: git add services/worker/src/generators/
2. Commit: git commit -m "feat(manuscript): implement DiscussionGenerator with literature synthesis

- Add DiscussionGenerator with RAG-powered synthesis
- Compare findings against literature automatically
- Generate structured limitations section
- Include clinical implications framework

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/manuscript-discussion-generator
```

---

### COMPOSIO PROMPT 2.5: IMRaD Assembler
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/manuscript-imrad-assembler'

## TASK: Implement IMRaD Manuscript Assembler

### REQUIREMENTS

1. Create `services/worker/src/generators/imrad_assembler.py`:
   - IMRaDAssembler class
   - Orchestrate all section generators
   - Assemble complete manuscript
   - Features:
     - Section ordering and formatting
     - Cross-reference resolution
     - Bibliography assembly
     - Supplementary materials bundling
     - Journal style application

2. Create `services/worker/src/generators/styles/`:
   - journal_styles.py (JAMA, NEJM, BMJ, Lancet, etc.)
   - citation_styles.py (Vancouver, APA, Chicago)

3. Create `services/worker/src/generators/validators/`:
   - manuscript_validator.py
   - word_count_checker.py
   - reference_validator.py

4. Create `services/worker/src/api/routes/manuscript_generate.py`:
   - POST /api/manuscript/generate
   - GET /api/manuscript/{id}/status
   - GET /api/manuscript/{id}/download

5. Integration tests in `tests/integration/test_manuscript_pipeline.py`

### TECHNICAL SPECS
- Async generation with progress tracking
- WebSocket progress updates
- Export formats: DOCX, PDF, LaTeX, Markdown
- Version tracking for manuscript iterations

### GIT REQUIREMENTS
1. Stage: git add services/worker/src/generators/ services/worker/src/api/routes/
2. Commit: git commit -m "feat(manuscript): implement IMRaD assembler and generation API

- Add IMRaDAssembler to orchestrate section generators
- Add journal style configurations (JAMA, NEJM, BMJ, etc.)
- Add manuscript validation and word count checking
- Create REST API for manuscript generation
- Support DOCX, PDF, LaTeX, Markdown export

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/manuscript-imrad-assembler
```

---

### COMPOSIO PROMPT 3.1: PHI Scanner API Enhancement
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/phi-scanner-enhancement'

## TASK: Enhance PHI Scanner API

### CONTEXT
PHI scanning exists but needs enhancement for all stage components.

### REQUIREMENTS

1. Enhance `services/worker/src/api/routes/phi_scan.py`:
   - Add batch scanning endpoint
   - Add streaming scan for large files
   - Add configurable sensitivity levels
   - Add pattern customization

2. Create `services/worker/src/phi/patterns/`:
   - hipaa_identifiers.py (18 HIPAA identifiers)
   - custom_patterns.py (institution-specific)
   - international_patterns.py (NHS, EU patterns)

3. Create `services/worker/src/phi/redaction/`:
   - redactor.py (safe value replacement)
   - deidentifier.py (k-anonymity support)
   - audit_logger.py (PHI access logging)

4. Add API endpoints:
   - POST /api/phi/scan/batch
   - POST /api/phi/scan/stream
   - GET /api/phi/patterns
   - POST /api/phi/redact

5. Tests in `tests/unit/phi/test_scanner.py`

### GIT REQUIREMENTS
1. Stage: git add services/worker/src/phi/ services/worker/src/api/routes/
2. Commit: git commit -m "feat(phi): enhance PHI scanner with batch/stream support

- Add batch scanning for multiple files
- Add streaming scan for large datasets
- Implement 18 HIPAA identifiers
- Add configurable sensitivity levels
- Include redaction and de-identification

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/phi-scanner-enhancement
```

---

### COMPOSIO PROMPT 4.1: API Integration Tests
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: Create new branch 'feature/api-integration-tests'

## TASK: Complete API Integration Test Suite

### REQUIREMENTS

1. Create `tests/integration/api/`:
   - test_workflow_api.py (all 20 stages)
   - test_manuscript_api.py (generation pipeline)
   - test_phi_api.py (scanning, redaction)
   - test_governance_api.py (mode transitions)
   - test_compliance_api.py (TRIPOD, CONSORT)

2. Create `tests/integration/conftest.py`:
   - Database fixtures
   - Auth fixtures
   - Project fixtures
   - Workflow state fixtures

3. Create `tests/integration/utils/`:
   - api_client.py (typed API client)
   - assertions.py (custom assertions)
   - factories.py (test data factories)

4. Add pytest configuration for integration tests

### TEST COVERAGE TARGETS
- Workflow API: 90%
- Manuscript API: 85%
- PHI API: 95%
- Governance API: 90%
- Compliance API: 85%

### GIT REQUIREMENTS
1. Stage: git add tests/integration/
2. Commit: git commit -m "test(integration): complete API integration test suite

- Add workflow API tests for all 20 stages
- Add manuscript generation pipeline tests
- Add PHI scanning and redaction tests
- Add governance mode transition tests
- Achieve 85%+ coverage targets

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin feature/api-integration-tests
```

---

## CURSOR PROMPTS

### CURSOR PROMPT 1.1: E2E Test Infrastructure
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/e2e-test-infrastructure'

## TASK: Enhance E2E Test Infrastructure

### CONTEXT
Many E2E tests exist in tests/e2e/ but need infrastructure improvements for full workflow testing.

### REQUIREMENTS

1. Enhance `tests/e2e/fixtures/`:
   - TestUser class with role-based creation
   - TestProject class with governance modes
   - TestDataset class with PHI/synthetic variants
   - TestWorkflow class with state management

2. Create `tests/e2e/helpers/`:
   - navigation.ts (stage navigation helpers)
   - assertions.ts (custom Playwright assertions)
   - api.ts (API helpers for setup/teardown)
   - wait.ts (smart waiting utilities)

3. Enhance `tests/e2e/pages/`:
   - StagePage base class
   - Stage01Page through Stage20Page
   - WorkflowDashboardPage
   - ManuscriptEditorPage

4. Update `tests/e2e/playwright.config.ts`:
   - Add test environment detection
   - Add screenshot on failure
   - Add video recording for failures
   - Add parallel test configuration

### FILE STRUCTURE
tests/e2e/
├── fixtures/
│   ├── TestUser.ts
│   ├── TestProject.ts
│   ├── TestDataset.ts
│   └── TestWorkflow.ts
├── helpers/
│   ├── navigation.ts
│   ├── assertions.ts
│   └── wait.ts
├── pages/
│   ├── StagePage.ts
│   └── stages/Stage01Page.ts ... Stage20Page.ts

### GIT REQUIREMENTS
1. Stage: git add tests/e2e/
2. Commit: git commit -m "test(e2e): enhance E2E test infrastructure

- Add TestUser, TestProject, TestDataset fixtures
- Add navigation and assertion helpers
- Add page objects for all 20 stages
- Configure parallel test execution

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/e2e-test-infrastructure
```

---

### CURSOR PROMPT 2.1: Manuscript Editor Integration
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/manuscript-editor-integration'

## TASK: Integrate Manuscript Editor with Generator API

### CONTEXT
The manuscript editor UI exists but needs integration with the new generator APIs.

### REQUIREMENTS

1. Create `services/web/src/components/manuscript/`:
   - GenerationPanel.tsx (trigger generation)
   - ProgressTracker.tsx (WebSocket progress)
   - SectionPreview.tsx (preview generated sections)
   - StyleSelector.tsx (journal style selection)
   - ExportOptions.tsx (format selection)

2. Create `services/web/src/hooks/`:
   - useManuscriptGeneration.ts
   - useGenerationProgress.ts
   - useManuscriptExport.ts

3. Create `services/web/src/api/`:
   - manuscript.ts (API client for generation)
   - types/manuscript.ts (TypeScript types)

4. Update `services/web/src/components/stages/Stage12Documentation.tsx`:
   - Add "Generate Manuscript" button
   - Add section selection
   - Add generation progress display

### TECHNICAL SPECS
- WebSocket for real-time progress
- Optimistic UI updates
- Error boundary for generation failures
- Retry logic for failed sections

### GIT REQUIREMENTS
1. Stage: git add services/web/src/
2. Commit: git commit -m "feat(ui): integrate manuscript editor with generation API

- Add GenerationPanel for triggering manuscript creation
- Add real-time progress tracking via WebSocket
- Add journal style selector
- Add export options for DOCX/PDF/LaTeX

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/manuscript-editor-integration
```

---

### CURSOR PROMPT 3.1: PHI Gates in Stage Components
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/phi-gates-stages'

## TASK: Add PHI Gates to All Stage Components

### CONTEXT
Stage components exist but need consistent PHI gate integration for governance compliance.

### REQUIREMENTS

1. Create `services/web/src/components/common/PHIGate.tsx`:
   - Wrapper component for PHI-sensitive content
   - Governance mode detection
   - Steward approval workflow
   - PHI warning banner
   - Audit logging integration

2. Create `services/web/src/hooks/usePHIGate.ts`:
   - Check governance mode
   - Check user permissions
   - Request steward approval
   - Log PHI access

3. Update all data-handling stages (4, 5, 6, 7, 9, 10):
   - Stage04DataCollection.tsx - wrap data upload
   - Stage05DataPreprocessing.tsx - wrap data display
   - Stage06Analysis.tsx - wrap analysis results
   - Stage07StatisticalModeling.tsx - wrap model outputs
   - Stage09Interpretation.tsx - wrap interpretations
   - Stage10Validation.tsx - wrap validation results

4. Create `services/web/src/components/common/PHIBanner.tsx`:
   - DEMO mode indicator
   - LIVE mode warnings
   - STANDBY mode blocks

5. Add E2E tests in `tests/e2e/phi-gates.spec.ts`

### GOVERNANCE RULES
- DEMO: Block real PHI, allow synthetic
- LIVE: Require steward approval for exports
- STANDBY: Block all PHI operations

### GIT REQUIREMENTS
1. Stage: git add services/web/src/components/ services/web/src/hooks/
2. Commit: git commit -m "feat(ui): add PHI gates to all stage components

- Add PHIGate wrapper component
- Add usePHIGate hook for governance checks
- Update Stages 4-10 with PHI protection
- Add PHI banner for mode indication
- Include E2E tests for PHI flows

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/phi-gates-stages
```

---

### CURSOR PROMPT 3.2: Compliance Dashboard UI
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/compliance-dashboard'

## TASK: Create Compliance Dashboard UI

### REQUIREMENTS

1. Create `services/web/src/pages/ComplianceDashboard.tsx`:
   - Overall compliance score
   - TRIPOD+AI checklist progress
   - CONSORT-AI checklist progress
   - HTI-1 transparency status
   - Audit trail summary

2. Create `services/web/src/components/compliance/`:
   - TRIPODChecklist.tsx (interactive checklist)
   - CONSORTChecklist.tsx (interactive checklist)
   - TransparencyReport.tsx (HTI-1 report)
   - ComplianceScore.tsx (visual score)
   - AuditTimeline.tsx (audit events)

3. Create `services/web/src/api/compliance.ts`:
   - API client for compliance endpoints
   - Types for compliance data

4. Add route in `services/web/src/App.tsx`:
   - /project/:id/compliance

5. Add E2E tests in `tests/e2e/compliance-dashboard.spec.ts`

### TECHNICAL SPECS
- Real-time checklist updates
- Export compliance report as PDF
- Link checklist items to manuscript sections
- Show remediation suggestions

### GIT REQUIREMENTS
1. Stage: git add services/web/src/
2. Commit: git commit -m "feat(ui): add compliance dashboard with TRIPOD/CONSORT checklists

- Add ComplianceDashboard page
- Add interactive TRIPOD+AI checklist
- Add interactive CONSORT-AI checklist
- Add HTI-1 transparency report
- Add compliance score visualization

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/compliance-dashboard
```

---

### CURSOR PROMPT 4.1: Full Workflow E2E Tests
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/full-workflow-e2e'

## TASK: Complete Full 20-Stage Workflow E2E Tests

### CONTEXT
Tests exist in tests/e2e/ but need complete 20-stage workflow coverage.

### REQUIREMENTS

1. Create `tests/e2e/complete-workflow.spec.ts`:
   - Test all 20 stages sequentially
   - Test stage transitions
   - Test artifact creation at each stage
   - Test final manuscript generation

2. Create `tests/e2e/workflow-variations.spec.ts`:
   - Test DEMO mode workflow
   - Test LIVE mode workflow (with approvals)
   - Test different study types (RCT, cohort, etc.)

3. Create `tests/e2e/error-handling.spec.ts`:
   - Test validation failures
   - Test network errors
   - Test timeout handling
   - Test recovery flows

4. Create `tests/e2e/accessibility.spec.ts`:
   - Keyboard navigation
   - Screen reader compatibility
   - Color contrast
   - Focus management

5. Update GitHub Actions workflow:
   - Add E2E test job
   - Configure test parallelization
   - Add test reporting

### TEST MATRIX
| Study Type | Governance Mode | Expected Duration |
|------------|-----------------|-------------------|
| RCT | DEMO | ~10 min |
| Cohort | DEMO | ~8 min |
| RCT | LIVE | ~15 min |

### GIT REQUIREMENTS
1. Stage: git add tests/e2e/ .github/workflows/
2. Commit: git commit -m "test(e2e): complete 20-stage workflow E2E test suite

- Add complete-workflow.spec.ts for full journey
- Add workflow variations for different modes
- Add error handling tests
- Add accessibility tests
- Configure GitHub Actions for E2E

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/full-workflow-e2e
```

---

### CURSOR PROMPT 4.2: Load Testing Enhancement
```
REPOSITORY: researchflow-production (local)
BRANCH: Create new branch 'feature/load-testing-enhancement'

## TASK: Enhance Load Testing with k6 Scripts

### CONTEXT
Basic load_test.js exists but needs full workflow coverage.

### REQUIREMENTS

1. Create `tests/perf/k6/`:
   - workflow-load.js (full workflow under load)
   - ai-endpoint-load.js (AI endpoints specifically)
   - concurrent-users.js (multi-user scenarios)
   - spike-test.js (traffic spike handling)

2. Create `tests/perf/k6/lib/`:
   - auth.js (authentication helpers)
   - workflow.js (workflow step helpers)
   - metrics.js (custom metrics)

3. Create `tests/perf/k6/scenarios/`:
   - normal-load.json (10 concurrent users)
   - peak-load.json (50 concurrent users)
   - stress-test.json (100 concurrent users)

4. Create `tests/perf/k6/thresholds.json`:
   - Response time thresholds
   - Error rate thresholds
   - AI latency thresholds

5. Update `package.json` with load test scripts:
   - npm run test:load:normal
   - npm run test:load:peak
   - npm run test:load:stress

### THRESHOLDS
- p95 response time < 5s
- Error rate < 1%
- AI response time p95 < 30s

### GIT REQUIREMENTS
1. Stage: git add tests/perf/k6/ package.json
2. Commit: git commit -m "test(perf): enhance load testing with k6 scripts

- Add full workflow load test
- Add AI endpoint specific load test
- Add concurrent user scenarios
- Add spike test for traffic bursts
- Configure thresholds for CI

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin feature/load-testing-enhancement
```

---

## Execution Timeline

### Week 1
| Day | Composio | Cursor |
|-----|----------|--------|
| Mon | Task 1.1: docker-compose.test.yml | Task 1.1: E2E Infrastructure |
| Tue | Task 2.1: Abstract Generator | Task 1.1 (continued) |
| Wed | Task 2.2: Methods Generator | Task 2.1: Manuscript Editor |
| Thu | Task 2.2 (continued) | Task 2.1 (continued) |
| Fri | Review & Merge PRs | Review & Merge PRs |

### Week 2
| Day | Composio | Cursor |
|-----|----------|--------|
| Mon | Task 2.3: Results Generator | Task 3.1: PHI Gates |
| Tue | Task 2.4: Discussion Generator | Task 3.1 (continued) |
| Wed | Task 2.5: IMRaD Assembler | Task 3.2: Compliance Dashboard |
| Thu | Task 2.5 (continued) | Task 3.2 (continued) |
| Fri | Review & Merge PRs | Review & Merge PRs |

### Week 3
| Day | Composio | Cursor |
|-----|----------|--------|
| Mon | Task 3.1: PHI Scanner | Task 4.1: Full Workflow E2E |
| Tue | Task 3.1 (continued) | Task 4.1 (continued) |
| Wed | Task 4.1: API Integration Tests | Task 4.1 (continued) |
| Thu | Task 4.1 (continued) | Task 4.2: Load Testing |
| Fri | Final Review & Release | Final Review & Release |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| All manuscript generators complete | 5/5 |
| PHI gates in all data stages | 6/6 |
| E2E tests for complete workflow | 1 passing |
| Load test thresholds met | 100% |
| API integration test coverage | 85%+ |
| Compliance dashboard functional | Yes |

---

## Risk Mitigation

1. **Composio Git Push Issues**: Include explicit retry logic in prompts
2. **Test Flakiness**: Use proper waits and retries in E2E tests
3. **AI Rate Limits**: Implement backoff in load tests
4. **Merge Conflicts**: Daily integration points scheduled

---

*Document Version 1.0 - February 2, 2026*
*For use with Composio and Cursor agents only*
