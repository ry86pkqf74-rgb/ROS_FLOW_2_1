# PR17: Enforce Offline Unit Tests and Deterministic Integration Tests in CI

## Summary

This PR implements strict separation between unit tests (offline, fast) and integration tests (with services, deterministic) in the CI pipeline.

## Changes

### Part 1: Unit Test Scope (`vitest.config.ts`)

**Modified:** `researchflow-production-main/vitest.config.ts`

- **ONLY includes:**
  - `tests/unit/**/*.test.ts`
  - `tests/unit/**/*.spec.ts`
  - `tests/governance/**/*.test.ts`
  - `tests/governance/**/*.spec.ts`
  - `packages/**/src/**/__tests__/**/*.test.ts`
  - `packages/**/src/**/__tests__/**/*.spec.ts`

- **Explicitly excludes:**
  - `tests/integration/**`
  - `packages/**/tests/integration/**`
  - `tests/e2e/**`
  - `services/web/**`

### Part 2: Integration CI Job (`.github/workflows/ci.yml`)

**Modified:** `.github/workflows/ci.yml`

Added new `integration-tests` job that:

1. **Starts required services** using `docker-compose.test.yml`:
   - Postgres on port 5433
   - Redis on port 6380
   - Mockserver on port 1080

2. **Waits for service health checks**:
   - Postgres, Redis, Mockserver health checks with 60s timeout
   - Worker health check: `http://localhost:8000/health`
   - Orchestrator health check: `http://localhost:3001/health`

3. **Starts application services**:
   - Worker (Python FastAPI) on port 8000
   - Orchestrator (Node.js Express) on port 3001

4. **Sets environment variables** for deterministic testing:
   ```bash
   DATABASE_URL=postgres://researchflow:researchflow@localhost:5433/researchflow_test
   REDIS_URL=redis://localhost:6380/0
   ORCHESTRATOR_URL=http://localhost:3001
   WORKER_URL=http://localhost:8000
   MOCKSERVER_URL=http://localhost:1080
   NO_NETWORK=true  # Forces use of fixtures/mocks for external APIs
   NODE_ENV=test
   ENV=test
   CI=true
   ```

5. **Runs integration tests**: `pnpm run test:integration`

6. **Cleanup** (always runs):
   - Kills worker and orchestrator processes
   - Stops and removes Docker services with `docker compose down -v`

## Validation

### Automated Validation Script

Run the validation script to verify all changes:

```bash
cd researchflow-production-main
bash scripts/validate-pr17.sh
```

The script checks:
- ✓ vitest.config.ts excludes integration tests
- ✓ vitest.config.ts includes unit/governance/package tests
- ✓ CI workflow has integration-tests job
- ✓ Integration job uses docker-compose.test.yml
- ✓ Integration job sets required env vars (ORCHESTRATOR_URL, WORKER_URL, NO_NETWORK)
- ✓ docker-compose.test.yml has required services

### Manual Validation

**Step 1: Unit tests (offline, no services needed)**
```bash
cd researchflow-production-main
pnpm run test:unit
```

Expected:
- Should run ONLY tests from:
  - `tests/unit/`
  - `tests/governance/`
  - `packages/**/src/**/__tests__/`
- Should NOT include any files from `tests/integration/`
- Should complete successfully (existing test failures are pre-existing)

**Step 2: Integration tests (with services)**
```bash
cd researchflow-production-main

# Start test services
docker compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
docker compose -f docker-compose.test.yml ps

# Build packages
pnpm run build:packages

# Start worker (in separate terminal or background)
cd services/worker
DATABASE_URL=postgres://researchflow:researchflow@localhost:5433/researchflow_test \
REDIS_URL=redis://localhost:6380/0 \
NO_NETWORK=true \
python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Start orchestrator (in separate terminal or background)
cd services/orchestrator
DATABASE_URL=postgres://researchflow:researchflow@localhost:5433/researchflow_test \
REDIS_URL=redis://localhost:6380/0 \
NO_NETWORK=true \
PORT=3001 \
node dist/index.js

# Run integration tests
cd ../..
pnpm run test:integration

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

Expected:
- Integration tests should start (may have failures, but should at least collect and run)
- Tests should use localhost services (not external APIs due to NO_NETWORK=true)
- Tests should be deterministic (same results on repeated runs)

## Key Benefits

1. **Fast Unit Tests**: Unit tests run offline in ~10-30 seconds without waiting for Docker services
2. **Isolated Concerns**: Unit tests focus on logic, integration tests focus on service interactions
3. **Deterministic Integration**: Integration tests use controlled services, not external APIs
4. **CI Efficiency**: Jobs run in parallel (unit tests while integration services start)
5. **Clear Separation**: Developers know exactly which tests need services vs. which are pure unit tests

## Parallel-Safety

This PR only modifies:
- `researchflow-production-main/vitest.config.ts`
- `.github/workflows/ci.yml`

No overlap with:
- Zod validation PRs
- UI component PRs
- API route PRs
- Schema/model PRs

## Files Changed

1. `researchflow-production-main/vitest.config.ts` - Unit test scope
2. `.github/workflows/ci.yml` - Integration test job
3. `researchflow-production-main/scripts/validate-pr17.sh` - Validation script (new)
4. `PR17_SUMMARY.md` - This document (new)

## Next Steps

1. ✓ Configuration complete
2. Run validation script: `bash researchflow-production-main/scripts/validate-pr17.sh`
3. Commit changes
4. Push branch
5. Open PR with this summary

## Notes

- The `NO_NETWORK=true` flag is set but may not be fully implemented in all tests yet
- Some integration tests may fail until they're updated to respect NO_NETWORK
- Unit test job in CI remains unchanged (now properly scoped to unit tests only)
- Existing test failures are pre-existing and not introduced by this PR
