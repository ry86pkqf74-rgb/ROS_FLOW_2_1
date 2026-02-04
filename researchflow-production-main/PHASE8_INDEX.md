# Phase 8: Testing & Validation - Complete Index

## Quick Links

### Main Documentation
- **[PHASE8_COMPLETION_SUMMARY.txt](./PHASE8_COMPLETION_SUMMARY.txt)** - Executive summary and completion checklist
- **[PHASE8_DELIVERABLES.md](./PHASE8_DELIVERABLES.md)** - Detailed deliverables and specifications
- **[PHASE8_TESTING_GUIDE.md](./PHASE8_TESTING_GUIDE.md)** - Comprehensive testing guide and reference

## Test Files

### Python Tests

#### Agent Tests
**Location:** `services/worker/tests/test_agents.py`
**Lines:** 799 | **Tests:** 26
**Coverage:**
- LangGraph agent initialization and compilation
- Agent execution with mock LLM bridge
- Quality gate evaluation
- PHI detection and validation
- Agent state management
- Multi-agent integration

```bash
# Run agent tests
cd services/worker
pytest tests/test_agents.py -v
```

#### RAG Tests
**Location:** `services/worker/tests/test_rag.py`
**Lines:** 617 | **Tests:** 35
**Coverage:**
- BM25 keyword scoring
- Document indexing and retrieval
- Semantic search with cosine similarity
- Hybrid retrieval with RRF
- Metadata filtering
- Edge case handling

```bash
# Run RAG tests
cd services/worker
pytest tests/test_rag.py -v
```

#### Test Configuration
**Location:** `services/worker/tests/pytest.ini`
**Lines:** 46
**Configuration:**
- Test discovery patterns
- Asyncio plugin setup
- Test markers and organization
- Coverage settings

**Location:** `services/worker/tests/__init__.py`
**Lines:** 29
**Configuration:**
- Test environment variables
- Module initialization

### TypeScript Tests

#### Dispatcher Tests
**Location:** `packages/ai-router/src/__tests__/custom-dispatcher.test.ts`
**Lines:** 611 | **Tests:** 40
**Coverage:**
- Dispatcher initialization
- Agent selection (by stage and task type)
- Request/response routing
- Fallback escalation
- Metrics tracking
- Caching mechanism
- Error handling

```bash
# Run dispatcher tests
cd packages/ai-router
npm test
```

#### Test Configuration
**Location:** `packages/ai-router/vitest.config.ts`
**Lines:** 77
**Configuration:**
- Test environment (Node)
- Coverage thresholds (80%)
- Reporter setup
- Mock configuration

**Location:** `packages/ai-router/src/__tests__/__init__.ts`
**Lines:** 37
**Configuration:**
- Test constants
- Mock data definitions

### E2E Tests

#### Workflow Tests
**Location:** `tests/e2e/ai-workflow.spec.ts`
**Lines:** 544 | **Test Suites:** 7
**Coverage:**
- Full AI workflow execution
- WebSocket real-time updates
- Copilot chat responses
- Agent status monitoring
- Quality gate feedback
- Error recovery
- Data persistence

```bash
# Run E2E tests
cd /root/researchflow-production
npx playwright test tests/e2e/ai-workflow.spec.ts
```

#### Test Configuration
**Location:** `tests/e2e/playwright.config.ts`
**Lines:** 106
**Configuration:**
- Browser project setup
- Timeout and retry settings
- Screenshot/video capture
- Reporter configuration
- WebServer settings

## Test Statistics

| Category | Tests | Lines | Framework |
|----------|-------|-------|-----------|
| Agents | 26 | 799 | pytest |
| RAG | 35 | 617 | pytest |
| Dispatcher | 40 | 611 | Vitest |
| E2E | 7 suites | 544 | Playwright |
| **Total** | **108** | **2,571** | **Mixed** |

## Running Tests

### All Tests
```bash
npm run test:all
```

### Individual Test Suites
```bash
# Python tests
cd services/worker
pytest tests/ -v --cov=src

# TypeScript tests
cd packages/ai-router
npm test

# E2E tests
npx playwright test tests/e2e/ai-workflow.spec.ts
```

### With Options
```bash
# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# Run with parallel execution
pytest tests/ -n auto

# Run specific markers
pytest tests/ -m "not slow" -v

# Run E2E with UI
npx playwright test --ui

# Run E2E with specific browser
npx playwright test --project=chromium
```

## Test Frameworks

### pytest (Python)
- **Version:** 8.0.0
- **Plugins:** asyncio, xdist
- **Configuration:** `services/worker/tests/pytest.ini`
- **Features:**
  - Async/await support
  - Fixtures for setup
  - Markers for organization
  - Coverage reporting

### Vitest (TypeScript)
- **Version:** 2.1.9+
- **Configuration:** `packages/ai-router/vitest.config.ts`
- **Features:**
  - TypeScript support
  - ESM modules
  - Coverage reporting
  - Watch mode

### Playwright (E2E)
- **Version:** 1.58.0+
- **Configuration:** `tests/e2e/playwright.config.ts`
- **Features:**
  - Multi-browser testing
  - Screenshot/video capture
  - Trace collection
  - HTML reporting

## Environment Setup

### Required Environment Variables
```bash
# For all tests
export GOVERNANCE_MODE=DEMO
export OCR_ENABLED=false
export EMBEDDINGS_PROVIDER=mock

# For E2E tests
export BASE_URL=http://localhost:5173
export API_URL=http://localhost:3001
export WS_URL=ws://localhost:3001
```

### Python Setup
```bash
cd services/worker
pip install -e ".[dev]"
pytest tests/ -v
```

### TypeScript Setup
```bash
cd packages/ai-router
npm install
npm test
```

### E2E Setup
```bash
cd /root/researchflow-production
npm install
npx playwright install
npx playwright test
```

## CI/CD Integration

### GitHub Actions
Tests automatically run on:
- Push to main/develop branches
- Pull requests

**Workflow Files:**
- `.github/workflows/ci.yml` - Unit tests (pytest + vitest)
- `.github/workflows/e2e-tests.yml` - E2E tests (Playwright)

### Local CI
```bash
# Run full CI pipeline locally
npm run ci
```

## Test Coverage

### Agent Tests Coverage
```
Agent Initialization:
  ├── Default initialization
  ├── Custom checkpointer
  └── Lazy graph loading

Agent Execution:
  ├── Basic invocation
  ├── With initial message
  ├── With input artifacts
  └── Token tracking

Quality Gates:
  ├── Pass evaluation
  ├── Needs human review
  └── LIVE mode requirements

PHI Detection:
  ├── Pattern matching
  ├── Clean text validation
  └── IRB scanning
```

### RAG Tests Coverage
```
Document Management:
  ├── Single document add
  ├── Multiple documents
  ├── Metadata preservation
  └── Embedding storage

Search Methods:
  ├── BM25 keyword search
  ├── Semantic search
  ├── Hybrid search
  └── RRF combination

Filtering:
  ├── Metadata filters
  ├── Score thresholds
  └── Ranking
```

### Dispatcher Tests Coverage
```
Agent Selection:
  ├── By workflow stage
  ├── By task type
  ├── By PHI requirements
  └── Default fallback

Dispatch:
  ├── Request routing
  ├── Response building
  ├── Fallback escalation
  └── Metrics tracking

Quality:
  ├── Input validation
  ├── Output validation
  └── Health checks
```

### E2E Tests Coverage
```
Workflow Execution:
  ├── Navigation
  ├── Project creation
  ├── Workflow initiation
  └── Completion

Real-time Updates:
  ├── WebSocket connection
  ├── Agent status messages
  ├── Progress tracking
  └── Error notifications

UI Components:
  ├── Copilot responses
  ├── Status indicators
  ├── Quality gates
  └── Error messages
```

## Debugging

### Python Tests
```bash
# With verbose output
pytest tests/ -vv -s

# With debugger
pytest tests/ --pdb

# With coverage
pytest tests/ --cov=src --cov-report=html

# Generate HTML report
pytest tests/ --html=report.html
```

### TypeScript Tests
```bash
# With verbose output
npm test -- --reporter=verbose

# With debugging
node --inspect-brk ./node_modules/vitest/vitest.mjs run

# With coverage
npm test -- --coverage
```

### E2E Tests
```bash
# In headed mode (see browser)
npx playwright test --headed

# With UI mode (interactive)
npx playwright test --ui

# With trace (for debugging)
npx playwright test --trace on

# Show trace viewer
npx playwright show-trace trace.zip

# Generate report
npx playwright show-report
```

## Performance Benchmarks

| Test Suite | Expected Time | Actual Time |
|-----------|---------------|------------|
| test_agents.py | 15-20s | - |
| test_rag.py | 10-15s | - |
| custom-dispatcher.test.ts | 5-10s | - |
| ai-workflow.spec.ts | 60-180s | - |
| **Total** | **2-4 min** | **- ** |

## Best Practices

1. **Use Fixtures** - Share setup code
2. **Mock Dependencies** - Don't rely on external services
3. **Test Behavior** - Focus on what, not how
4. **Keep Tests Focused** - One behavior per test
5. **Use Meaningful Assertions** - Be specific
6. **Document Complex Tests** - Explain setup
7. **Avoid Interdependence** - Tests should run independently
8. **Use Markers** - Tag tests for selective execution

## Common Issues & Solutions

### Python Tests
**Issue:** ModuleNotFoundError
**Solution:** Add worker src to path in conftest.py

**Issue:** Async test failures
**Solution:** Use `@pytest.mark.asyncio` decorator

**Issue:** Fixture not found
**Solution:** Check conftest.py in same directory

### TypeScript Tests
**Issue:** Module resolution errors
**Solution:** Check vitest.config.ts aliases

**Issue:** Type errors in tests
**Solution:** Verify TypeScript configuration

**Issue:** Mock not working
**Solution:** Ensure mocks set up before imports

### E2E Tests
**Issue:** Timeout errors
**Solution:** Increase timeout in playwright.config.ts

**Issue:** Element not found
**Solution:** Check selector and wait conditions

**Issue:** WebSocket not connecting
**Solution:** Verify API_URL and WS_URL environment variables

## Next Steps

1. **Run all tests** to validate setup
2. **Check coverage** with: `pytest tests/ --cov`
3. **Add to CI/CD** pipeline
4. **Monitor metrics** over time
5. **Expand coverage** as code evolves
6. **Add performance benchmarks**
7. **Implement visual regression tests**

## Resources

- **Testing Guide:** [PHASE8_TESTING_GUIDE.md](./PHASE8_TESTING_GUIDE.md)
- **Deliverables:** [PHASE8_DELIVERABLES.md](./PHASE8_DELIVERABLES.md)
- **Summary:** [PHASE8_COMPLETION_SUMMARY.txt](./PHASE8_COMPLETION_SUMMARY.txt)

## Support

For questions or issues:
1. Check the [PHASE8_TESTING_GUIDE.md](./PHASE8_TESTING_GUIDE.md) troubleshooting section
2. Review relevant test file docstrings
3. Check framework documentation (pytest, vitest, playwright)

---

**Phase 8 Version:** 8.0.0
**Status:** Complete and Ready for Integration
**Last Updated:** 2026-01-30
