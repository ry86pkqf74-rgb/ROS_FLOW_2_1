# 🎬 Continue.dev Workflow Examples

**Real-world scenarios for delegating tasks to AI agents**

---

## Table of Contents
1. [Security Workflows](#security-workflows)
2. [Feature Development](#feature-development)
3. [Bug Fixing](#bug-fixing)
4. [Testing Workflows](#testing-workflows)
5. [DevOps & Deployment](#devops--deployment)
6. [Code Review](#code-review)
7. [Refactoring](#refactoring)

---

## 🔐 Security Workflows

### Workflow: HIPAA Compliance Audit

**Scenario**: Need to audit all patient data handling for HIPAA compliance

**Steps**:

1. **Find PHI Handling Code** (Claude Opus 4.5)
   ```
   Cmd+L
   "@codebase Find all code that handles patient identifiable information. 
   Look for: name, DOB, SSN, medical records, email, phone"
   ```

2. **Audit Each File** (Claude Opus 4.5)
   ```
   "/phi-check services/worker/src/api/patients.ts"
   "/phi-check services/orchestrator/src/models/patient.ts"
   "/phi-check services/web/src/stores/patient-store.ts"
   ```

3. **Check Encryption** (Claude Opus 4.5)
   ```
   "Review encryption implementation for patient data:
   - At rest (database)
   - In transit (API calls)
   - In logs (audit trails)"
   ```

4. **Access Control Audit** (Claude Opus 4.5)
   ```
   "/rbac-audit all endpoints in services/orchestrator/src/routes/patients.ts"
   ```

5. **Generate Report** (GPT-4o)
   ```
   "Create a HIPAA compliance audit report summarizing:
   - PHI exposure risks found
   - Encryption status
   - Access control gaps
   - Remediation recommendations"
   ```

**Time Saved**: ~4 hours manual audit → ~30 minutes with AI

---

### Workflow: Security Vulnerability Fix

**Scenario**: Security scanner found auth bypass vulnerability

**Steps**:

1. **Analyze Vulnerability** (Claude Opus 4.5)
   ```
   Cmd+L
   "Analyze this security vulnerability in auth.ts line 73-90:
   [paste code]
   
   Identify:
   - Attack vectors
   - Impact severity  
   - Root cause"
   ```

2. **Review Similar Code** (Claude Opus 4.5)
   ```
   "@codebase Find all similar auth bypass patterns in the codebase"
   ```

3. **Generate Fix** (Claude Opus 4.5)
   ```
   "Generate a secure fix for the auth bypass:
   - Close the vulnerability
   - Maintain backward compatibility
   - Add input validation
   - Include security tests"
   ```

4. **Security Test** (Codestral)
   ```
   "/test-route for auth endpoints with:
   - SQL injection attempts
   - XSS payloads
   - JWT manipulation
   - Privilege escalation"
   ```

5. **Peer Review** (Claude Opus 4.5)
   ```
   "Review this security fix for:
   - Complete vulnerability closure
   - No new vulnerabilities introduced
   - Performance impact
   - Edge cases covered"
   ```

**Time Saved**: ~6 hours → ~1 hour

---

## 💻 Feature Development

### Workflow: New REST API Endpoint

**Scenario**: Add endpoint for PDF export of protocols

**Steps**:

1. **Design API** (Claude Opus 4.5)
   ```
   Cmd+L
   "Design REST API endpoint for protocol PDF export:
   
   Requirements:
   - GET /api/protocols/:id/export/pdf
   - Supports custom templates
   - Includes metadata
   - Streams large PDFs
   - HIPAA compliant (no PHI in logs)
   
   Provide:
   - API spec (OpenAPI)
   - Request/response schemas
   - Error codes
   - Security considerations"
   ```

2. **Implement Backend** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [Select file: services/orchestrator/src/routes/protocols.ts]
   
   "Add PDF export endpoint:
   - TypeScript with strict types
   - Zod validation
   - RBAC middleware (researcher+ only)
   - Error handling
   - Audit logging
   - PHI compliance"
   ```

3. **Generate Tests** (Codestral)
   ```
   "/test-route for PDF export endpoint:
   - Auth required
   - Permission checks
   - Valid protocol ID
   - Invalid ID returns 404
   - Template selection
   - Large file handling"
   ```

4. **Add Frontend Hook** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [Select file: services/web/src/hooks/use-protocol-export.ts]
   
   "Create React hook for PDF export:
   - usePDFExport(protocolId)
   - Loading state
   - Error handling
   - Download trigger
   - Progress indicator"
   ```

5. **Documentation** (GPT-4o)
   ```
   "Generate API documentation for PDF export:
   - Endpoint description
   - Request parameters
   - Response format
   - Code examples (curl, JavaScript)
   - Error codes"
   ```

6. **Security Check** (Claude Opus 4.5)
   ```
   "/phi-check the entire PDF export implementation"
   ```

**Time Saved**: ~2 days → ~4 hours

---

### Workflow: React Component with State Management

**Scenario**: Create protocol editor component

**Steps**:

1. **Design Component** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Review existing protocol components for patterns
   
   Design ProtocolEditor component:
   - Edit protocol fields
   - Auto-save
   - Validation
   - Optimistic updates
   - Error boundaries"
   ```

2. **Create Store** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [New file: services/web/src/stores/protocol-editor-store.ts]
   
   "Create Zustand store for protocol editor:
   - State: protocol, isDirty, isSaving, errors
   - Actions: updateField, save, reset, validate
   - Persistence (localStorage)
   - TypeScript types"
   ```

3. **Generate Component** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [New file: services/web/src/components/ProtocolEditor.tsx]
   
   "Create ProtocolEditor component:
   - TypeScript + strict mode
   - Functional with hooks
   - TailwindCSS styling
   - Form validation
   - Auto-save every 30s
   - Loading states
   - Error handling"
   ```

4. **Add Tests** (Codestral)
   ```
   "Generate Vitest tests for ProtocolEditor:
   - Renders correctly
   - Field updates work
   - Validation triggers
   - Auto-save fires
   - Error display"
   ```

5. **Storybook Story** (GPT-4o Mini)
   ```
   "Create Storybook story for ProtocolEditor:
   - Default state
   - With data
   - Loading state
   - Error state
   - Dirty state"
   ```

**Time Saved**: ~1.5 days → ~3 hours

---

## 🐛 Bug Fixing

### Workflow: Auth Flow Not Working

**Scenario**: Login succeeds but mode stays in DEMO instead of LIVE

**Steps**:

1. **Investigate Issue** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Why doesn't login set mode to LIVE?
   
   Check:
   - services/web/src/stores/mode-store.ts
   - services/web/src/hooks/use-auth.ts
   - services/orchestrator/src/routes/auth.ts
   
   Trace the flow from login → mode change"
   ```

2. **Analyze Response** (Claude Sonnet 4.5)
   ```
   "@terminal show recent auth requests
   
   Analyze:
   - Does backend return mode in login response?
   - Does frontend update mode-store?
   - Is there a race condition?"
   ```

3. **Implement Fix** (Claude Sonnet 4.5 or Codestral)
   ```
   Cmd+I
   [Select problematic code]
   
   "Fix the mode switching:
   - Update mode-store after successful login
   - Add loading state
   - Handle errors
   - Persist mode to localStorage"
   ```

4. **Add Test** (Codestral)
   ```
   "Create Playwright E2E test:
   - Login as test user
   - Verify mode changes to LIVE
   - Check mode persists on refresh
   - Test logout resets to DEMO"
   ```

5. **Verify Fix** (Claude Sonnet 4.5)
   ```
   "Review the fix for:
   - Correct mode switching logic
   - No race conditions
   - Proper error handling
   - No side effects"
   ```

**Time Saved**: ~4 hours debugging → ~45 minutes

---

### Workflow: Performance Issue

**Scenario**: API endpoint is slow (5+ seconds)

**Steps**:

1. **Profile Performance** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Analyze performance of /api/protocols/generate endpoint
   
   Look for:
   - Database N+1 queries
   - Missing indexes
   - Synchronous operations
   - Large data transfers
   - Inefficient algorithms"
   ```

2. **Alternative Approach** (Grok)
   ```
   "Suggest 3 different approaches to optimize protocol generation:
   - Caching strategy
   - Background processing
   - Incremental generation
   
   Include pros/cons for each"
   ```

3. **Implement Caching** (Claude Sonnet 4.5)
   ```
   Cmd+I
   "Add Redis caching layer:
   - Cache generated protocols (1 hour TTL)
   - Cache key: protocol_id + template_version
   - Invalidate on protocol update
   - Handle cache misses gracefully"
   ```

4. **Add Benchmarks** (Codestral)
   ```
   "Generate performance benchmark tests:
   - Measure response time
   - Track cache hit rate
   - Monitor memory usage
   - Test with 100 concurrent requests"
   ```

5. **Verify Improvement** (Claude Sonnet 4.5)
   ```
   "@terminal show benchmark results
   
   Verify:
   - Response time improved
   - No regression in accuracy
   - Cache invalidation works
   - Error handling robust"
   ```

**Time Saved**: ~1 day → ~3 hours

---

## 🧪 Testing Workflows

### Workflow: Increase Test Coverage

**Scenario**: New module has only 40% test coverage, need >80%

**Steps**:

1. **Analyze Coverage** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Show test coverage for services/worker/src/protocol-generator.ts
   
   Identify:
   - Untested functions
   - Untested branches
   - Missing edge cases
   - Error scenarios"
   ```

2. **Generate Unit Tests** (Codestral)
   ```
   "/test-route for protocol-generator.ts:
   - Test all public methods
   - Test error cases
   - Test edge cases (empty input, null, invalid data)
   - Mock dependencies
   - Use fixtures"
   ```

3. **Integration Tests** (Claude Sonnet 4.5)
   ```
   "Create integration tests:
   - End-to-end protocol generation
   - Database interactions
   - External API calls
   - File system operations"
   ```

4. **Run Coverage** (Codestral)
   ```
   "@terminal run npm test -- --coverage
   
   Generate report showing:
   - Line coverage
   - Branch coverage
   - Function coverage
   - Uncovered lines"
   ```

5. **Fill Gaps** (Codestral)
   ```
   "Add tests for uncovered lines:
   [paste coverage report]
   
   Focus on:
   - Error handlers
   - Validation logic
   - Edge cases"
   ```

**Time Saved**: ~1 day → ~2 hours

---

### Workflow: E2E Testing Critical Path

**Scenario**: Create E2E tests for user journey

**Steps**:

1. **Define Journey** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "Design E2E test for critical user journey:
   
   Journey: Create and Publish Protocol
   1. Login
   2. Create new protocol
   3. Fill in details
   4. Generate sections
   5. Review
   6. Publish
   
   Include:
   - Happy path
   - Error scenarios
   - Validation failures
   - Permission checks"
   ```

2. **Generate Playwright Tests** (Codestral)
   ```
   "Create Playwright E2E tests for protocol creation journey:
   - Use fixtures for auth
   - Use page objects pattern
   - Include screenshots on failure
   - Test on mobile viewport too
   - Handle async operations"
   ```

3. **Add Test Data** (GPT-4o Mini)
   ```
   "Create test fixtures:
   - Valid protocol data
   - Invalid protocol data
   - Edge cases (empty, very long, special characters)
   - Different user roles"
   ```

4. **Run Tests** (Codestral)
   ```
   "@terminal run npm test:e2e
   
   Generate test report showing:
   - Pass/fail for each scenario
   - Screenshots
   - Execution time
   - Browser compatibility"
   ```

**Time Saved**: ~2 days → ~4 hours

---

## 🐳 DevOps & Deployment

### Workflow: Docker Production Setup

**Scenario**: Prepare Docker setup for production

**Steps**:

1. **Audit Config** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "/docker-check docker-compose.prod.yml
   
   Verify:
   - Resource limits set
   - Health checks configured
   - Secrets not hardcoded
   - Restart policies
   - Logging configured
   - Networks isolated"
   ```

2. **Security Hardening** (Claude Opus 4.5)
   ```
   "Review Docker security:
   - Non-root users
   - Read-only filesystems where possible
   - Drop unnecessary capabilities
   - Scan for vulnerabilities
   - Use minimal base images"
   ```

3. **Health Checks** (Codestral)
   ```
   "Generate health check endpoints for all services:
   - /health/ready (app ready)
   - /health/live (app alive)
   - Include dependency checks
   - Return proper status codes"
   ```

4. **Monitoring Setup** (GPT-4o)
   ```
   "Create monitoring configuration:
   - Prometheus metrics
   - Grafana dashboards
   - Alert rules (CPU, memory, errors)
   - Log aggregation
   - APM tracing"
   ```

5. **Deployment Script** (Claude Sonnet 4.5)
   ```
   "Create deployment script:
   - Pre-flight checks
   - Database migrations
   - Zero-downtime deployment
   - Rollback capability
   - Health check validation
   - Smoke tests"
   ```

6. **Documentation** (GPT-4o)
   ```
   "Create deployment runbook:
   - Prerequisites
   - Step-by-step deployment
   - Rollback procedure
   - Troubleshooting guide
   - Monitoring checks
   - Emergency contacts"
   ```

**Time Saved**: ~3 days → ~6 hours

---

### Workflow: CI/CD Pipeline

**Scenario**: Set up GitHub Actions pipeline

**Steps**:

1. **Design Pipeline** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "Design CI/CD pipeline for:
   
   Stages:
   - Lint & format
   - Type check
   - Unit tests
   - Integration tests
   - Security scan
   - Build Docker images
   - Deploy to staging
   - E2E tests on staging
   - Deploy to production
   
   Include:
   - Branch protection
   - Required approvals
   - Automated rollback"
   ```

2. **Generate Workflow** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [New file: .github/workflows/ci-cd.yml]
   
   "Create GitHub Actions workflow:
   - Multi-stage pipeline
   - Parallel jobs where possible
   - Cache dependencies
   - Matrix testing (Node 18, 20)
   - Secrets from GitHub
   - Slack notifications"
   ```

3. **Add Quality Gates** (Codestral)
   ```
   "Add quality gates:
   - Test coverage >80%
   - No critical security issues
   - Bundle size limit
   - Lighthouse score >90
   - Zero TypeScript errors"
   ```

4. **Documentation** (GPT-4o)
   ```
   "Document CI/CD pipeline:
   - How it works
   - Required secrets
   - How to debug failures
   - How to deploy manually
   - Monitoring and alerts"
   ```

**Time Saved**: ~2 days → ~4 hours

---

## 🔍 Code Review

### Workflow: PR Review

**Scenario**: Review a large PR (500+ lines changed)

**Steps**:

1. **Overview Analysis** (Claude Opus 4.5)
   ```
   Cmd+L
   "@git show diff for current PR
   
   Provide high-level analysis:
   - What changed
   - Impact areas
   - Potential risks
   - Architecture implications"
   ```

2. **Security Review** (Claude Opus 4.5)
   ```
   "Review PR for security issues:
   - Input validation
   - Authentication/authorization
   - PHI handling
   - SQL injection risks
   - XSS vulnerabilities
   - CSRF protection"
   ```

3. **Code Quality** (Claude Sonnet 4.5)
   ```
   "Review code quality:
   - TypeScript best practices
   - Error handling
   - Edge cases covered
   - Proper logging
   - Performance considerations
   - Code duplication"
   ```

4. **Test Coverage** (Codestral)
   ```
   "Review test coverage:
   - Are new features tested?
   - Are edge cases covered?
   - Are error paths tested?
   - Integration tests included?"
   ```

5. **Generate Review Comments** (Claude Sonnet 4.5)
   ```
   "Generate PR review comments:
   - Actionable feedback
   - Specific line numbers
   - Suggested improvements
   - Praise for good patterns
   - Required changes vs. suggestions"
   ```

**Time Saved**: ~3 hours → ~30 minutes

---

## 🔄 Refactoring

### Workflow: Migrate to TypeScript Strict Mode

**Scenario**: Enable TypeScript strict mode across codebase

**Steps**:

1. **Analyze Impact** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Analyze impact of enabling TypeScript strict mode:
   - How many files will have errors?
   - Common error types
   - Migration effort estimate"
   ```

2. **Enable Gradually** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [Select: tsconfig.json]
   
   "Enable strict mode incrementally:
   - Add strict flags one at a time
   - Start with noImplicitAny
   - Then strictNullChecks
   - Then others
   - Allow list files to migrate"
   ```

3. **Fix Type Errors** (Codestral)
   ```
   "Fix TypeScript errors in [filename]:
   - Add proper types
   - Handle null/undefined
   - Type function parameters
   - Type return values
   - Add type guards where needed"
   ```

4. **Validate** (Codestral)
   ```
   "@terminal run npm run type-check
   
   Verify:
   - No type errors
   - All files passing
   - No any types (or documented)"
   ```

5. **Update Tests** (Codestral)
   ```
   "Update tests for strict types:
   - Type test data
   - Type mocks
   - Type assertions
   - Remove type casts"
   ```

**Time Saved**: ~1 week → ~1 day

---

### Workflow: Refactor Class to Hooks

**Scenario**: Convert class component to functional with hooks

**Steps**:

1. **Analyze Component** (Claude Sonnet 4.5)
   ```
   Cmd+L
   "@codebase Analyze this class component:
   [paste component code]
   
   Identify:
   - State variables
   - Lifecycle methods
   - Methods to extract
   - Props usage
   - Context usage"
   ```

2. **Plan Migration** (Claude Sonnet 4.5)
   ```
   "Create migration plan:
   - useState for state
   - useEffect for lifecycle
   - Custom hooks to extract
   - useMemo/useCallback for optimization
   - Testing strategy"
   ```

3. **Refactor** (Claude Sonnet 4.5)
   ```
   Cmd+I
   [Select component]
   
   "Refactor to functional component:
   - Convert to function
   - Use hooks for state/effects
   - Extract logic to custom hooks
   - Add TypeScript types
   - Maintain same behavior"
   ```

4. **Test Equivalence** (Codestral)
   ```
   "Update tests to verify:
   - Same props interface
   - Same behavior
   - Same render output
   - Same event handling
   - Same lifecycle behavior"
   ```

5. **Verify** (Claude Sonnet 4.5)
   ```
   "Verify refactoring:
   - No behavior changes
   - Tests pass
   - Performance similar or better
   - Type safety improved
   - Code more readable"
   ```

**Time Saved**: ~4 hours → ~1 hour

---

## 📊 Summary

### Time Savings by Workflow Type

| Workflow Type | Manual Time | With AI | Time Saved | Efficiency Gain |
|---------------|-------------|---------|------------|-----------------|
| Security Audit | 4 hours | 30 min | 3.5 hrs | 87% |
| Feature Dev | 2 days | 4 hrs | 12 hrs | 75% |
| Bug Fix | 4 hours | 45 min | 3.25 hrs | 81% |
| Testing | 1 day | 2 hrs | 6 hrs | 75% |
| DevOps Setup | 3 days | 6 hrs | 18 hrs | 75% |
| Code Review | 3 hours | 30 min | 2.5 hrs | 83% |
| Refactoring | 1 week | 1 day | 32 hrs | 80% |

### Key Success Factors

1. **Right Model for Task** - Use Claude Opus for security, Codestral for speed
2. **Good Context** - Use @codebase, provide specific files, include errors
3. **Iterative Approach** - Break complex tasks into steps
4. **Always Review** - Never commit AI code without review
5. **Learn & Adapt** - Track what works, build your prompt library

---

**Ready to 5x your development speed with AI agents! 🚀**

*See [AI_AGENT_TASK_DELEGATION_GUIDE.md](AI_AGENT_TASK_DELEGATION_GUIDE.md) for complete reference*
