# Phase 4A: End-to-End Testing Setup - Comprehensive Checklist

**Date Generated:** January 29, 2026
**Repository:** ResearchFlow Production
**Test Framework:** Playwright + Vitest
**Status:** ✅ Configuration Found & Documented

---

## Executive Summary

ResearchFlow has a **mature, multi-layered testing infrastructure** with:
- **64 total test files** across 5 test categories
- **Playwright configuration** for E2E testing (120s timeout, Chrome focus)
- **Vitest configuration** for unit & integration tests
- **Comprehensive test coverage** including visual regression, load testing, and security testing
- **CI/CD integration** via GitHub Actions

### Test Statistics
| Category | Files | Status |
|----------|-------|--------|
| E2E Tests | 20 spec files | ✅ Configured |
| Governance Tests | 9 test files | ✅ Security-critical |
| Integration Tests | 15 test files | ✅ Multi-service |
| Unit Tests | 13 test files | ✅ Package-level |
| Visual Tests | 2 spec files | ✅ Regression coverage |
| Security Tests | 1 test file | ✅ PHI scanning |
| Support Files | 4 files | ✅ Utilities & setup |
| **TOTAL** | **64 test files** | ✅ Complete |

---

## Task 4A.1: Test Configuration - Search Results

### Playwright Configuration ✅

**File:** `playwright.config.ts`

Key Configuration:
- Test Directory: `./tests/e2e`
- Timeout: 120 seconds (AI operations)
- Parallel Execution: Fully enabled
- CI Mode: Retries=2, Single worker, forbidOnly enabled
- Browsers: Chromium (Firefox/WebKit disabled)
- Reporting: HTML, JSON, List format
- Base URL: localhost:5173 (development)
- Artifacts: Screenshots & video on failure
- Viewport: 1280x720

### Vitest Configuration ✅

**File:** `vitest.config.ts`

Key Configuration:
- Environment: Node.js
- Test Include Patterns:
  - `packages/**/*.test.ts`
  - `tests/unit/**/*.test.ts`
  - `tests/integration/**/*.test.ts`
  - `tests/governance/**/*.test.ts`
- Test Exclusions: E2E, web services, some integration tests
- Global Mode: Enabled
- Timeout: 10 seconds
- Path Aliases: Configured for all packages

---

## Task 4A.2: Linear Issues - Test-Related Findings

### High-Priority Testing Issues

| ID | Title | Status | Priority |
|----|----|--------|----------|
| ROS-32 | Playwright Tests + Browser Confirmation | Done ✅ | High |
| ROS-22 | E2E Validation - User Journey Tests | Done ✅ | High |
| ROS-25 | E2E Test Execution & Validation | Done ✅ | High |
| ROS-9 | Testing/QA - E2E Validation | Done ✅ | Medium |
| ROS-45 | Grok: Security Audit + Test Suite | Backlog ⏳ | Urgent |

### Key Milestones
- ROS-32: 22 Playwright test files verified
- ROS-22: User journey E2E validation suite completed
- ROS-25: Full E2E test execution workflow established
- ROS-9: Smoke test + auth flow tests verified (95% complete)

---

## Task 4A.3: Test Coverage Documentation

### Test File Inventory (64 Total)

#### E2E Tests (20 files)
- auth.spec.ts - Login/logout, sessions
- critical-journeys.spec.ts - Key user flows
- artifact-browser.spec.ts - Artifact management UI
- manuscript-journey.spec.ts - Manuscript workflow
- governance-modes.spec.ts - DEMO/LIVE mode switching (2 files)
- phi-redaction.spec.ts - PHI protection
- workflow-navigation.spec.ts - UI navigation (2 files)
- run-lifecycle.spec.ts - Run state transitions
- system-smoke.spec.ts - Health checks
- user-journey.spec.ts - Full user paths
- guideline-engine.spec.ts - Guidelines integration
- policy-enforcement.spec.ts - Policy checks
- ros-integration-workflow.spec.ts - ROS integration
- interactive-elements.spec.ts - UI element interaction
- cumulative-workflow.spec.ts - Multi-stage workflow
- full-workflow-journey.spec.ts - End-to-end flow
- full-ai-workflow.spec.ts - AI agent workflows
- Plus: fixtures, helpers, mocks, pages, screenshots directories

#### Governance Tests (9 files)
- rbac.test.ts - Role-based access control
- phi-scanner.test.ts - PHI detection
- fail-closed.test.ts - Secure defaults
- mode-enforcement.test.ts - DEMO vs LIVE modes
- app-mode-invariants.test.ts - State consistency
- hash-chain.test.ts - Audit trail integrity
- audit-integration.test.ts - Audit logging
- export-approval.test.ts - Export workflows
- standby-external-calls.test.ts - Standby operation

#### Integration Tests (15 files)
- api-endpoints.test.ts - REST API validation
- artifacts.test.ts - Artifact CRUD
- artifact-graph.test.ts - Dependency tracking
- collab.test.ts - Real-time collaboration
- org-isolation.test.ts - Multi-tenant isolation
- workflow-stages.test.ts - Stage transitions
- webhooks.test.ts - Webhook delivery
- imrad-ai.test.ts - AI manuscript generation
- conference-endpoints.test.ts - Conference API
- standby-mode.test.ts - Standby operation
- manuscript-engine/ (5 files):
  - structure.test.ts
  - compliance-export.test.ts
  - data-integration.test.ts
  - literature.test.ts
  - writing-tools.test.ts
- multiproject-dashboard.spec.ts - Multi-project UI

#### Unit Tests (13 files)
- phi-scanner.test.ts - PHI detection logic
- hash-determinism.test.ts - Hash consistency
- org-rbac.test.ts - RBAC utilities
- artifact-schema.test.ts - Schema validation
- fhir-connector.test.ts, fhir-transforms.test.ts
- run-manifest.test.ts - Manifest structure
- validation-suites.test.ts - Pandera validators
- services/orchestrator/ (7 files):
  - artifactGraph.test.ts
  - comments.test.ts
  - orcid.test.ts
  - phi-protection.test.ts
  - phi-scanner.test.ts
  - shares.test.ts
  - submissions.test.ts
- phi-scanner-healthcheck.test.ts

#### Visual Tests (2 files)
- baseline.spec.ts - Component visual tests
- key-screens.spec.ts - Screen capture tests

#### Security Tests (1 file)
- insights-phi-scan.test.ts - EventBus PHI leakage

#### Support Files (4 files)
- setup.ts - Global test setup
- audit-auth-events.test.ts - Auth audit events
- fixtures/ - Shared test data
- utils/ - Test utilities

---

## Task 4A.4: E2E Testing Checklist

### Phase 1: Environment Preparation

#### Local Environment Setup
- [ ] Node.js 20+ installed (`node --version`)
- [ ] npm 10+ installed (`npm --version`)
- [ ] Docker & Docker Compose installed
- [ ] Playwright browsers installed (`npx playwright install`)
- [ ] K6 installed (`brew install k6` or package manager)
- [ ] PostgreSQL running or via docker-compose
- [ ] Redis running or via docker-compose
- [ ] All env variables configured (`.env` file)

#### Code Repository
- [ ] Repository cloned from GitHub
- [ ] Main branch checked out
- [ ] Dependencies installed (`npm install`)
- [ ] TypeScript validates (`npm run typecheck`)
- [ ] Linting passes (`npm run lint`)
- [ ] Config files verified:
  - [ ] playwright.config.ts exists
  - [ ] vitest.config.ts exists
  - [ ] package.json has test scripts

#### Docker Stack
- [ ] docker-compose.yml configured
- [ ] No port conflicts (5173, 3000, 3001, 6379, 5432)
- [ ] Docker services build (`docker compose build`)
- [ ] Services start (`docker compose up -d`)
- [ ] Health checks pass:
  - [ ] Web: http://localhost:5173
  - [ ] API: http://localhost:3000
  - [ ] Database: Port 5432
  - [ ] Redis: Port 6379

### Phase 2: Unit Tests (30 seconds)

#### Execution
```bash
npm run test:unit
```

- [ ] All 13 unit test files execute
- [ ] Exit code 0 (success)
- [ ] No TypeScript errors
- [ ] Coverage report generated
- [ ] Coverage > 80% for critical paths

#### Verification
- [ ] PHI Scanner unit tests pass
- [ ] RBAC utility tests pass
- [ ] Hash determinism tests pass
- [ ] Artifact schema tests pass
- [ ] FHIR transformation tests pass
- [ ] Run manifest tests pass

### Phase 3: Integration Tests (3-5 minutes)

#### Execution
```bash
npm run test:integration
```

- [ ] All 15 integration test files execute
- [ ] Database connection works
- [ ] API service responsive
- [ ] Redis operations succeed
- [ ] No timeout errors

#### Critical Tests
- [ ] api-endpoints.test.ts passes (REST API)
- [ ] artifacts.test.ts passes (CRUD)
- [ ] collab.test.ts passes (WebSocket)
- [ ] org-isolation.test.ts passes (multi-tenant)
- [ ] workflow-stages.test.ts passes (state)
- [ ] Manuscript engine tests (5 files) all pass

### Phase 4: Governance Tests (5 seconds)

#### Execution
```bash
npm run test:rbac
npm run test:phi
npm run test:fail-closed
npm run test:mode-enforcement
npm run test:invariants
```

- [ ] All 9 governance tests pass
- [ ] No PHI leakage detected
- [ ] RBAC enforcement verified
- [ ] Secure defaults validated
- [ ] Mode switching works

### Phase 5: E2E Tests (15 minutes)

#### Pre-Test Setup
- [ ] docker-compose services running
- [ ] Web service at http://localhost:5173
- [ ] API service at http://localhost:3000
- [ ] Test database ready
- [ ] No stale browser processes

#### Execution
```bash
npm run test:e2e
# or for debugging:
npx playwright test --headed
npx playwright test --debug
```

- [ ] All 20 E2E test files execute
- [ ] No timeout errors (120s limit)
- [ ] Screenshots captured on failure
- [ ] Videos recorded (on-first-retry)
- [ ] Traces available

#### Critical User Journeys
- [ ] **Authentication** (auth.spec.ts)
  - [ ] Login succeeds with valid credentials
  - [ ] Invalid credentials rejected
  - [ ] Session persists across pages
  - [ ] Logout clears session

- [ ] **User Journey** (user-journey.spec.ts)
  - [ ] Complete workflow executable
  - [ ] All UI elements functional
  - [ ] No console errors
  - [ ] Navigation works smoothly

- [ ] **Artifact Management** (artifact-browser.spec.ts)
  - [ ] Browse artifacts list
  - [ ] Upload new artifact
  - [ ] Delete artifact
  - [ ] Search functionality works

- [ ] **Workflow Navigation** (workflow-navigation.spec.ts)
  - [ ] Navigate between stages
  - [ ] PHI indicators visible
  - [ ] State transitions correct
  - [ ] Back/forward navigation works

- [ ] **Governance Modes** (governance-modes.spec.ts)
  - [ ] Switch to DEMO mode
  - [ ] Switch to LIVE mode
  - [ ] DEMO restrictions enforced
  - [ ] LIVE permissions correct

- [ ] **Governance Flow** (governance-flow.spec.ts)
  - [ ] Submit for approval
  - [ ] Approval workflow proceeds
  - [ ] Audit trail recorded
  - [ ] Rejection handled

- [ ] **Manuscript Workflow** (manuscript-journey.spec.ts)
  - [ ] Create new manuscript
  - [ ] Edit content
  - [ ] Validate structure
  - [ ] Export in formats

- [ ] **Data Protection** (phi-redaction.spec.ts)
  - [ ] PHI detected automatically
  - [ ] Redaction applied
  - [ ] Redacted shown in export
  - [ ] Original preserved in audit

- [ ] **System Health** (system-smoke.spec.ts)
  - [ ] Health endpoints respond
  - [ ] Services responsive
  - [ ] Database accessible
  - [ ] No critical errors

### Phase 6: Visual Regression Tests (20 minutes)

#### Setup
- [ ] Baseline screenshots exist in repo
- [ ] Consistent test environment
- [ ] Standard viewport (1280x720)
- [ ] No animations or flashing content

#### Execution
```bash
npm run test:visual
# After UI intentional changes:
npm run test:visual:update
```

- [ ] baseline.spec.ts passes
- [ ] key-screens.spec.ts passes
- [ ] No unexpected visual changes
- [ ] Report generated in playwright-report/

#### If Baselines Need Update
```bash
npm run test:visual:update
git diff tests/visual/__screenshots__/
git add tests/visual/__screenshots__/
git commit -m "test: update visual regression baselines"
```

### Phase 7: Load Testing (25 minutes)

#### Prerequisites
- [ ] K6 installed and functional
- [ ] API service fully warmed up
- [ ] Database with test data
- [ ] Clean state (no lingering connections)

#### Execution
```bash
# Full load test
npm run test:load

# Specific endpoints
npm run test:load:auth
npm run test:load:projects
npm run test:load:governance

# Stress test (if configured)
npm run test:load:stress
```

#### Performance Targets
| Endpoint | P95 Latency | Max Error Rate |
|----------|-------------|----------------|
| Auth | < 200ms | < 1% |
| Projects | < 200ms | < 1% |
| Governance | < 300ms | < 1% |

- [ ] Auth endpoint p95 < 200ms
- [ ] Projects endpoint p95 < 200ms
- [ ] Governance endpoint p95 < 300ms
- [ ] Error rate < 1% across all endpoints
- [ ] Peak load 100 VUs handled
- [ ] No performance regressions
- [ ] Reports available in tests/load/reports/

### Phase 8: Coverage Analysis

#### Code Coverage
```bash
npm run test:coverage
```

- [ ] Overall coverage > 80%
- [ ] Critical paths > 90%
- [ ] Coverage report generated
- [ ] Coverage HTML viewable

#### Coverage Targets
| Metric | Target | Status |
|--------|--------|--------|
| Statements | > 80% | [ ] |
| Branches | > 75% | [ ] |
| Functions | > 80% | [ ] |
| Lines | > 80% | [ ] |

### Phase 9: Report Generation & Review

#### Test Reports
- [ ] HTML report: `playwright-report/index.html`
- [ ] JSON results: `playwright-report/results.json`
- [ ] Screenshots folder: `test-results/`
- [ ] Video folder: `test-results/`
- [ ] Traces: Available for failures

#### Report Analysis
- [ ] Test names are clear and descriptive
- [ ] All failures have captured evidence
- [ ] Performance metrics recorded
- [ ] Visual diffs clear and meaningful
- [ ] Load test trends analyzed

### Phase 10: CI/CD Verification

#### GitHub Actions
- [ ] Workflows defined in `.github/workflows/`
- [ ] Tests run on pull requests
- [ ] Tests run on push to main
- [ ] Scheduled nightly runs configured
- [ ] Test artifacts retained for review

#### Branch Protection
- [ ] All tests must pass before merge
- [ ] At least 1 approval required
- [ ] Status checks blocking enabled
- [ ] No auto-dismiss of reviews

### Phase 11: Documentation

#### Test Documentation
- [ ] TESTING-GUIDE.md reviewed
- [ ] QUICK-REFERENCE.md available
- [ ] Fixture documentation clear
- [ ] Page object patterns documented
- [ ] Mock server setup explained

#### Team Knowledge
- [ ] Team trained on test execution
- [ ] Common debugging steps documented
- [ ] Troubleshooting guide available
- [ ] Code review guidelines established for tests

### Phase 12: Maintenance Routine

#### Monthly
- [ ] Review test coverage metrics
- [ ] Identify flaky tests
- [ ] Update dependencies (playwright, vitest, k6)
- [ ] Archive old test results

#### Quarterly
- [ ] Update performance baselines
- [ ] Refactor redundant tests
- [ ] Add new coverage for features
- [ ] Review test execution times

#### Annual
- [ ] Full test suite refactoring
- [ ] Update documentation
- [ ] Team training refresher
- [ ] Evaluate new testing tools

---

## Troubleshooting Guide

### Common Issues

| Problem | Solution |
|---------|----------|
| "Port already in use" | `lsof -i :PORT` then kill process or change port |
| Visual tests fail locally | `npm ci` to reinstall exact deps, clear node_modules |
| Playwright timeout (120s) | Check Docker services, increase if needed |
| Database connection refused | Verify postgres running: `docker ps` |
| "No golden file found" (visual) | Normal on first run, update: `npm run test:visual:update` |
| Load test errors | Check API health: `curl http://localhost:3000/health` |
| Flaky E2E test | Run multiple times: `--repeat 3` in Playwright |
| TypeScript errors | Run `npm run typecheck` and fix, retry tests |

---

## Quick Reference Commands

```bash
# Setup
npm install
npx playwright install
docker-compose up -d

# Run tests
npm test                       # All tests
npm run test:unit              # Unit only
npm run test:integration       # Integration only
npm run test:e2e               # E2E only
npm run test:visual            # Visual regression
npm run test:rbac              # Security
npm run test:coverage          # Coverage report

# E2E debugging
npx playwright test --headed   # See browser
npx playwright test --debug    # Step-through
npx playwright test -g "auth"  # Pattern match

# Validation
npm run typecheck              # TypeScript check
npm run lint                   # ESLint check
npm run format:check           # Format check
```

---

## Success Criteria

All checklist items completed indicates:
- ✅ Test infrastructure is fully functional
- ✅ All test suites pass consistently
- ✅ Code coverage meets targets
- ✅ Performance within acceptable ranges
- ✅ Security tests passing
- ✅ CI/CD properly configured
- ✅ Team ready for deployment

---

**Checklist Version:** 1.0
**Last Updated:** January 29, 2026
**Status:** Ready for Phase 4A Execution
