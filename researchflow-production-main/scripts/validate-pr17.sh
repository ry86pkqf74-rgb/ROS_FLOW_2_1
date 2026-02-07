#!/bin/bash
# PR17 Validation Script: Enforce offline unit tests and deterministic integration tests
# This script validates that:
# 1. Unit tests run ONLY unit/governance tests (no integration)
# 2. Integration tests require services and run separately

set -e

echo "==================================================="
echo "PR17 Validation: Offline Unit + Deterministic Integration Tests"
echo "==================================================="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to project root
cd "$(dirname "$0")/.."

echo "Step 1: Verify vitest.config.ts excludes integration tests"
echo "---------------------------------------------------"
if grep -q "exclude:.*tests/integration/\*\*" vitest.config.ts; then
    echo -e "${GREEN}✓${NC} vitest.config.ts correctly excludes tests/integration/**"
else
    echo -e "${RED}✗${NC} vitest.config.ts missing integration exclusion"
    exit 1
fi

if grep -q "include:.*tests/unit/\*\*/\*.test.ts" vitest.config.ts; then
    echo -e "${GREEN}✓${NC} vitest.config.ts includes tests/unit/**/*.test.ts"
else
    echo -e "${RED}✗${NC} vitest.config.ts missing unit test inclusion"
    exit 1
fi

if grep -q "include:.*tests/governance/\*\*/\*.test.ts" vitest.config.ts; then
    echo -e "${GREEN}✓${NC} vitest.config.ts includes tests/governance/**/*.test.ts"
else
    echo -e "${RED}✗${NC} vitest.config.ts missing governance test inclusion"
    exit 1
fi

if grep -q "packages/\*\*/src/\*\*/\__tests__/\*\*/\*.test.ts" vitest.config.ts; then
    echo -e "${GREEN}✓${NC} vitest.config.ts includes packages/**/src/**/__tests__/**/*.test.ts"
else
    echo -e "${RED}✗${NC} vitest.config.ts missing package __tests__ inclusion"
    exit 1
fi
echo

echo "Step 2: Check CI workflow has integration test job"
echo "---------------------------------------------------"
if grep -q "integration-tests:" .github/workflows/ci.yml; then
    echo -e "${GREEN}✓${NC} CI workflow has integration-tests job"
else
    echo -e "${RED}✗${NC} CI workflow missing integration-tests job"
    exit 1
fi

if grep -q "docker compose -f docker-compose.test.yml" .github/workflows/ci.yml; then
    echo -e "${GREEN}✓${NC} Integration job uses docker-compose.test.yml"
else
    echo -e "${RED}✗${NC} Integration job missing docker-compose setup"
    exit 1
fi

if grep -q "ORCHESTRATOR_URL=http://localhost:3001" .github/workflows/ci.yml; then
    echo -e "${GREEN}✓${NC} Integration job sets ORCHESTRATOR_URL"
else
    echo -e "${RED}✗${NC} Integration job missing ORCHESTRATOR_URL"
    exit 1
fi

if grep -q "WORKER_URL=http://localhost:8000" .github/workflows/ci.yml; then
    echo -e "${GREEN}✓${NC} Integration job sets WORKER_URL"
else
    echo -e "${RED}✗${NC} Integration job missing WORKER_URL"
    exit 1
fi

if grep -q "NO_NETWORK=true" .github/workflows/ci.yml; then
    echo -e "${GREEN}✓${NC} Integration job sets NO_NETWORK=true"
else
    echo -e "${YELLOW}⚠${NC} Integration job missing NO_NETWORK flag (optional)"
fi
echo

echo "Step 3: List collected test files (dry run)"
echo "---------------------------------------------------"
echo "Unit tests pattern (should NOT include integration/):"
pnpm exec vitest list --config vitest.config.ts 2>&1 | grep -E "(tests/unit|tests/governance|packages/.+/__tests__)" | head -10
INTEGRATION_COUNT=$(pnpm exec vitest list --config vitest.config.ts 2>&1 | grep -c "tests/integration" || echo "0")
if [ "$INTEGRATION_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✓${NC} No integration tests found in unit suite"
else
    echo -e "${RED}✗${NC} Found $INTEGRATION_COUNT integration test files in unit suite"
    exit 1
fi
echo

echo "Integration tests pattern (should ONLY be integration/):"
pnpm exec vitest list --config vitest.integration.config.ts 2>&1 | grep "tests/integration" | head -10
INTEGRATION_FOUND=$(pnpm exec vitest list --config vitest.integration.config.ts 2>&1 | grep -c "tests/integration" || echo "0")
if [ "$INTEGRATION_FOUND" -gt "0" ]; then
    echo -e "${GREEN}✓${NC} Found $INTEGRATION_FOUND integration test files"
else
    echo -e "${RED}✗${NC} No integration tests found in integration suite"
    exit 1
fi
echo

echo "Step 4: Verify docker-compose.test.yml services"
echo "---------------------------------------------------"
if grep -q "postgres-test:" docker-compose.test.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.test.yml has postgres-test (port 5433)"
else
    echo -e "${RED}✗${NC} Missing postgres-test service"
    exit 1
fi

if grep -q "redis-test:" docker-compose.test.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.test.yml has redis-test (port 6380)"
else
    echo -e "${RED}✗${NC} Missing redis-test service"
    exit 1
fi

if grep -q "mockserver:" docker-compose.test.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.test.yml has mockserver (port 1080)"
else
    echo -e "${RED}✗${NC} Missing mockserver service"
    exit 1
fi
echo

echo "==================================================="
echo -e "${GREEN}All PR17 validations passed!${NC}"
echo "==================================================="
echo
echo "Next steps:"
echo "1. Run unit tests locally: pnpm run test:unit"
echo "2. Start services: docker compose -f docker-compose.test.yml up -d"
echo "3. Run integration tests: pnpm run test:integration"
echo "4. Push branch and open PR"
echo
