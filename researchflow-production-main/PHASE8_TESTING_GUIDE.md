# Phase 8: Testing & Validation Guide

## Overview

Phase 8 introduces comprehensive testing for ResearchFlow's AI workflow engine:

- **Agent Testing** (`services/worker/tests/test_agents.py`) - LangGraph agent execution, state management, PHI detection
- **RAG Testing** (`services/worker/tests/test_rag.py`) - Hybrid retriever, semantic search, BM25 keyword matching
- **Dispatcher Testing** (`packages/ai-router/src/__tests__/custom-dispatcher.test.ts`) - Custom tier routing, fallback behavior, metrics
- **E2E Testing** (`tests/e2e/ai-workflow.spec.ts`) - Full workflow execution, WebSocket updates, Copilot responses

## Test Structure

```
services/worker/tests/
├── __init__.py                 # Test module initialization
├── conftest.py                 # Pytest configuration and fixtures
├── pytest.ini                  # Pytest settings
├── test_agents.py             # Agent tests (799 lines)
└── test_rag.py                # RAG system tests (617 lines)

packages/ai-router/
├── vitest.config.ts           # Vitest configuration
└── src/__tests__/
    ├── __init__.ts            # Test module initialization
    └── custom-dispatcher.test.ts  # Dispatcher tests (611 lines)

tests/e2e/
├── playwright.config.ts       # Playwright configuration
└── ai-workflow.spec.ts        # E2E workflow tests (544 lines)
```

## Running Tests

### Python Tests (pytest)

```bash
# Run all worker service tests
cd services/worker
pytest tests/ -v

# Run specific test file
pytest tests/test_agents.py -v
pytest tests/test_rag.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test class
pytest tests/test_agents.py::TestAgentInitialization -v

# Run async tests only
pytest tests/ -m asyncio -v

# Run with detailed output
pytest tests/ -vv -s

# Run with markers
pytest tests/ -m "unit or integration" -v
```

### TypeScript Tests (Vitest)

```bash
# Run all dispatcher tests
cd packages/ai-router
npm test

# Run with watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test custom-dispatcher.test.ts

# Run specific test suite
npm test -- -t "Agent Selection"
```

### E2E Tests (Playwright)

```bash
# Run all E2E tests
cd /root/researchflow-production
npx playwright test tests/e2e/ai-workflow.spec.ts

# Run with specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox

# Run with UI mode (visual debugging)
npx playwright test --ui

# Run with trace
npx playwright test --trace on

# Run specific test suite
npx playwright test --grep "AI Workflow - Full Execution"

# Generate HTML report
npx playwright show-report
```

## Test Coverage

### Agent Tests (services/worker/tests/test_agents.py)

**Fixtures:**
- `mock_llm_bridge` - Mock AI Router bridge
- `test_project_id`, `test_run_id`, `test_thread_id` - Test IDs
- `initial_agent_state` - Pre-configured agent state
- `phi_containing_text`, `clean_text` - PHI test data

**Test Classes:**

1. **TestAgentInitialization** (3 tests)
   - Agent initialization with defaults
   - Custom checkpointer setup
   - Lazy graph initialization

2. **TestAgentExecution** (3 async tests)
   - Basic agent invocation
   - Invocation with initial message
   - Invocation with input artifacts

3. **TestQualityGateEvaluation** (3 tests)
   - Quality gate passing
   - Quality gate requiring human review
   - LIVE mode IRB requirement

4. **TestAgentSelectionLogic** (2 tests)
   - Stage-based agent selection
   - Stage coverage verification

5. **TestPHIDetection** (3 tests)
   - PHI pattern detection
   - Clean text validation
   - IRB agent PHI scanning

6. **TestAgentStateManagement** (3 tests)
   - Initial state creation
   - State with input artifacts
   - Message tracking

7. **TestTokenTracking** (2 async tests)
   - Token count updates
   - LLM usage recording

8. **Agent-Specific Tests**
   - DataPrepAgentFunctionality (2 tests)
   - ManuscriptAgentFunctionality (2 tests)

9. **TestAgentIntegration** (1 async test)
   - Multi-agent workflow execution

**Total: 26 tests**

### RAG Tests (services/worker/tests/test_rag.py)

**Fixtures:**
- `hybrid_config` - HybridRetriever configuration
- `retriever` - Retriever instance
- `sample_documents` - Test documents
- `embeddings` - Test embeddings
- `populated_retriever` - Pre-indexed retriever
- `query_embedding` - Test query embedding

**Test Classes:**

1. **TestBM25Scorer** (5 tests)
   - BM25 initialization
   - Document indexing
   - Score calculation
   - Multiple documents
   - Average document length

2. **TestHybridRetrieverDocumentManagement** (4 tests)
   - Add single document
   - Add multiple documents
   - Metadata preservation
   - Embedding storage

3. **TestSemanticSearch** (4 tests)
   - Cosine similarity (identical, orthogonal, opposite vectors)
   - Basic semantic search
   - Semantic ranking

4. **TestBM25KeywordSearch** (3 tests)
   - Basic keyword search
   - Exact match ranking
   - Keyword ranking

5. **TestReciprocalRankFusion** (3 tests)
   - Identical results
   - RRF score calculation
   - Result combination

6. **TestHybridSearch** (4 tests)
   - Hybrid search returns results
   - Top-k limit respect
   - Min-score threshold
   - Semantic weight influence

7. **TestMetadataFiltering** (4 tests)
   - Exact metadata match
   - Multiple criteria filtering
   - No matches handling
   - Filter function correctness

8. **TestRetrievalResult** (2 tests)
   - RetrievalResult creation
   - Result with ranking info

9. **TestHybridConfig** (2 tests)
   - Default configuration
   - Custom configuration

10. **TestEdgeCases** (4 tests)
    - Empty query
    - Empty retriever
    - Zero embeddings
    - Single document search

**Total: 35 tests**

### Dispatcher Tests (packages/ai-router/src/__tests__/custom-dispatcher.test.ts)

**Test Suites:**

1. **CustomDispatcher - Initialization** (4 tests)
   - Default config initialization
   - Custom fallback tier
   - Agent registry setup
   - Metrics initialization

2. **CustomDispatcher - Agent Selection** (8 tests)
   - Stage-based selection (1-5, 6-10, 11-15, 16-20)
   - Task type selection
   - Default agent selection
   - PHI requirement respect
   - Dispatch decision structure

3. **CustomDispatcher - Dispatch Execution** (6 tests)
   - Successful dispatch
   - Routing information
   - Metrics tracking
   - Token usage estimation
   - Cost estimation
   - Quality gate results

4. **CustomDispatcher - Caching** (3 tests)
   - Cache decision storage
   - Cache clearing
   - Cache key consistency

5. **CustomDispatcher - Metrics & Health** (4 tests)
   - Total dispatch tracking
   - Success rate calculation
   - Fallback rate calculation
   - Health status reporting

6. **CustomDispatcher - Request/Response Transformation** (4 tests)
   - Agent input building
   - Response routing info
   - JSON parsing
   - Non-JSON handling

7. **CustomDispatcher - Agent Registry** (3 tests)
   - Registry entry validation
   - Stage coverage
   - PHI handling requirements

8. **CustomDispatcher - Factory Function** (3 tests)
   - Factory creation
   - Factory with config
   - Instance independence

9. **CustomDispatcher - Error Handling** (3 tests)
   - Invalid task type handling
   - Null/undefined context
   - Empty prompt handling

10. **CustomDispatcher - Feature Flag Integration** (2 tests)
    - Feature flag support
    - Metrics flag support

**Total: 40 tests**

### E2E Tests (tests/e2e/ai-workflow.spec.ts)

**Test Suites:**

1. **AI Workflow - Full Execution** (1 test)
   - Complete workflow: navigation → project creation → WebSocket → workflow execution → agent status → quality gate → copilot response → completion

2. **AI Workflow - WebSocket Agent Status** (1 test)
   - Real-time status updates via WebSocket

3. **AI Workflow - Copilot Response Rendering** (1 test)
   - Copilot chat interface and response rendering

4. **AI Workflow - Error Handling** (1 test)
   - Workflow error detection and recovery

5. **AI Workflow - Agent Selection** (1 test)
   - Agent selection validation by workflow stage

6. **AI Workflow - Quality Gate Feedback** (1 test)
   - Quality gate evaluation display

7. **AI Workflow - Data Persistence** (1 test)
   - Workflow state persistence across page reloads

**Total: 7 test suites**

## Test Execution Flow

### Agent Tests
```
Agent Initialization
    ↓
Graph Building
    ↓
Agent Invocation
    ↓
Quality Gate Evaluation
    ↓
Token Tracking
    ↓
Completion
```

### RAG Tests
```
Document Indexing
    ↓
Semantic Search
    ↓
Keyword Search (BM25)
    ↓
Reciprocal Rank Fusion
    ↓
Result Ranking & Filtering
    ↓
Completion
```

### Dispatcher Tests
```
Dispatcher Initialization
    ↓
Agent Selection
    ↓
Request Dispatch
    ↓
Metrics Tracking
    ↓
Fallback Handling
    ↓
Completion
```

### E2E Tests
```
Application Navigation
    ↓
Project/Workflow Creation
    ↓
WebSocket Connection
    ↓
Agent Execution
    ↓
Status Updates
    ↓
Response Rendering
    ↓
Completion
```

## Environment Variables

### For Agent Tests
```bash
GOVERNANCE_MODE=DEMO
OCR_ENABLED=false
SCISPACY_ENABLED=false
EMBEDDINGS_PROVIDER=mock
```

### For E2E Tests
```bash
BASE_URL=http://localhost:5173
API_URL=http://localhost:3001
WS_URL=ws://localhost:3001
```

## Debugging Tests

### Python Tests

```bash
# Run with verbose output
pytest tests/ -vv -s

# Run specific test with print output
pytest tests/test_agents.py::TestAgentExecution::test_agent_invoke_basic -vv -s

# Run with pdb debugger
pytest tests/ --pdb

# Run with breakpoint()
# Add breakpoint() in test code, then:
pytest tests/ -s

# Generate HTML report
pytest tests/ --html=report.html --self-contained-html
```

### TypeScript Tests

```bash
# Run with detailed output
npm test -- --reporter=verbose

# Run with debugging
node --inspect-brk ./node_modules/vitest/vitest.mjs run

# Run with coverage visualization
npm test -- --coverage
```

### E2E Tests

```bash
# Run in headed mode (see browser)
npx playwright test --headed

# Run with UI mode (interactive)
npx playwright test --ui

# Run with trace (for debugging)
npx playwright test --trace on

# View generated trace
npx playwright show-trace <trace-file>

# Generate full report
npx playwright show-report
```

## Continuous Integration

### GitHub Actions Configuration

Tests run automatically on:
- Push to main/develop branches
- Pull requests

Configuration in `.github/workflows/`:
- `ci.yml` - Runs pytest and vitest
- `e2e-tests.yml` - Runs Playwright tests

## Performance Benchmarks

Expected test execution times:

- `test_agents.py`: ~15-20 seconds
- `test_rag.py`: ~10-15 seconds
- `custom-dispatcher.test.ts`: ~5-10 seconds
- `ai-workflow.spec.ts`: ~60-180 seconds (depends on AI operations)

**Total: ~2-4 minutes for full test suite**

## Adding New Tests

### Python Tests

1. Create test method in appropriate class
2. Use fixtures for setup
3. Use pytest markers for organization
4. Add docstring explaining test

```python
@pytest.mark.asyncio
async def test_new_feature(self, mock_llm_bridge):
    """Test description."""
    # Arrange
    agent = TestDataPrepAgent(mock_llm_bridge, [1, 2, 3], 'data_prep')
    
    # Act
    result = await agent.invoke('test-proj')
    
    # Assert
    assert result is not None
    assert result['project_id'] == 'test-proj'
```

### TypeScript Tests

1. Create test case in describe block
2. Use mock helpers
3. Follow AAA pattern (Arrange, Act, Assert)

```typescript
it('should perform new behavior', async () => {
  // Arrange
  const dispatcher = new CustomDispatcher();
  const request = createMockRequest();
  
  // Act
  const response = await dispatcher.dispatch(request, context);
  
  // Assert
  expect(response.content).toBeDefined();
});
```

### E2E Tests

1. Follow existing test structure
2. Use helper functions (clickWithRetry, waitForLoadingComplete)
3. Add console logging for debugging
4. Take screenshots on failure

```typescript
test('should do something', async ({ page }) => {
  await page.goto(`${BASE_URL}/path`);
  await clickWithRetry(page, 'selector');
  await waitForLoadingComplete(page);
  
  const result = page.locator('.result');
  expect(await result.isVisible()).toBe(true);
});
```

## Best Practices

1. **Use fixtures** - Share setup code across tests
2. **Mock external dependencies** - Don't rely on external services
3. **Test behavior, not implementation** - Focus on what, not how
4. **Keep tests focused** - One behavior per test
5. **Use meaningful assertions** - Be specific about expectations
6. **Document complex tests** - Explain setup and expectations
7. **Avoid test interdependence** - Tests should run independently
8. **Use appropriate markers** - Tag tests for selective execution

## Troubleshooting

### Python Tests Fail

```bash
# Check Python version (3.11.5 required)
python3 --version

# Reinstall dependencies
pip install -e ".[dev]"

# Clear cache
rm -rf .pytest_cache
```

### TypeScript Tests Fail

```bash
# Clear node_modules
rm -rf node_modules
npm install

# Clear vitest cache
rm -rf node_modules/.vitest
npm test -- --no-cache
```

### E2E Tests Fail

```bash
# Ensure servers are running
# Check BASE_URL and API_URL environment variables
# Review screenshots/video in test-results/

# Update Playwright browsers
npx playwright install
```

## Next Steps

- Expand test coverage to >85%
- Add performance benchmarks
- Implement visual regression testing
- Add accessibility tests
- Create test data factories
