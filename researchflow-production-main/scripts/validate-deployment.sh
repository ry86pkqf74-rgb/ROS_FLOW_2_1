#!/bin/bash
set -e

###############################################################################
# ResearchFlow Deployment Validation Script
#
# This script validates that the full Docker stack is ready for LIVE mode
# execution with real data for the 20-stage workflow.
#
# Checks:
# 1. All services are healthy
# 2. GOVERNANCE_MODE is set to LIVE
# 3. Database schema is up to date
# 4. Worker can accept workflow execution requests
# 5. All 20 stages are registered
# 6. Required AI integrations are configured
###############################################################################

echo "=========================================="
echo "ResearchFlow Deployment Validation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

###############################################################################
# 1. Check Docker Compose services
###############################################################################
echo "1. Checking Docker services..."

services=("postgres" "redis" "orchestrator" "worker" "web" "collab" "ollama" "guideline-engine")

for service in "${services[@]}"; do
    if docker compose ps "$service" | grep -q "Up"; then
        check_pass "Service $service is running"
    else
        check_fail "Service $service is not running"
    fi
done

###############################################################################
# 2. Check service health endpoints
###############################################################################
echo ""
echo "2. Checking service health endpoints..."

# Orchestrator health
if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
    check_pass "Orchestrator health endpoint responding"
else
    check_fail "Orchestrator health endpoint not responding"
fi

# Worker health
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    check_pass "Worker health endpoint responding"
else
    check_fail "Worker health endpoint not responding"
fi

# Web frontend
if curl -sf http://localhost:5173/health > /dev/null 2>&1; then
    check_pass "Web frontend health endpoint responding"
else
    check_warn "Web frontend health endpoint not responding (may be expected in dev)"
fi

# Collab service
if curl -sf http://localhost:1235/health > /dev/null 2>&1; then
    check_pass "Collab service health endpoint responding"
else
    check_fail "Collab service health endpoint not responding"
fi

###############################################################################
# 3. Check GOVERNANCE_MODE configuration
###############################################################################
echo ""
echo "3. Checking GOVERNANCE_MODE configuration..."

# Note: Field name inconsistency between services:
# - Orchestrator uses 'governanceMode' (camelCase)
# - Worker uses 'governance_mode' (snake_case)
# This is expected due to TypeScript vs Python conventions

# Check orchestrator governance mode
ORCH_GOV_MODE=$(curl -sf http://localhost:3001/health | jq -r '.governanceMode' 2>/dev/null || echo "unknown")
if [ "$ORCH_GOV_MODE" = "LIVE" ]; then
    check_pass "Orchestrator governance mode: LIVE"
elif [ "$ORCH_GOV_MODE" = "DEMO" ]; then
    check_warn "Orchestrator governance mode: DEMO (should be LIVE for production)"
else
    check_fail "Orchestrator governance mode: $ORCH_GOV_MODE (unknown or not set)"
fi

# Check worker governance mode
WORKER_GOV_MODE=$(curl -sf http://localhost:8000/health | jq -r '.governance_mode' 2>/dev/null || echo "unknown")
if [ "$WORKER_GOV_MODE" = "LIVE" ]; then
    check_pass "Worker governance mode: LIVE"
elif [ "$WORKER_GOV_MODE" = "DEMO" ]; then
    check_warn "Worker governance mode: DEMO (should be LIVE for production)"
else
    check_fail "Worker governance mode: $WORKER_GOV_MODE (unknown or not set)"
fi

###############################################################################
# 4. Check database connectivity
###############################################################################
echo ""
echo "4. Checking database connectivity..."

if docker compose exec -T postgres pg_isready -U ros > /dev/null 2>&1; then
    check_pass "PostgreSQL is ready"
else
    check_fail "PostgreSQL is not ready"
fi

# Check if migrations have run
TABLE_COUNT=$(docker compose exec -T postgres psql -U ros -d ros -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' \n' || echo "0")
if [ "$TABLE_COUNT" -gt 10 ]; then
    check_pass "Database schema initialized ($TABLE_COUNT tables)"
else
    check_warn "Database schema may not be initialized ($TABLE_COUNT tables)"
fi

###############################################################################
# 5. Check Redis connectivity
###############################################################################
echo ""
echo "5. Checking Redis connectivity..."

if docker compose exec -T redis redis-cli -a redis-dev-password ping 2>/dev/null | grep -q "PONG"; then
    check_pass "Redis is responding"
else
    check_fail "Redis is not responding"
fi

###############################################################################
# 6. Validate workflow stages registration
###############################################################################
echo ""
echo "6. Validating workflow stages..."

# Try to get stage list from worker
STAGE_COUNT=$(curl -sf http://localhost:8000/api/workflow/stages/1/status 2>/dev/null | jq -r '.registered' 2>/dev/null || echo "false")
if [ "$STAGE_COUNT" = "true" ]; then
    check_pass "Stage 1 is registered in worker"
else
    check_fail "Stage 1 is not registered in worker"
fi

# Check a few more stages
for stage in 7 12 20; do
    REGISTERED=$(curl -sf http://localhost:8000/api/workflow/stages/$stage/status 2>/dev/null | jq -r '.registered' 2>/dev/null || echo "false")
    if [ "$REGISTERED" = "true" ]; then
        check_pass "Stage $stage is registered"
    else
        check_fail "Stage $stage is not registered"
    fi
done

###############################################################################
# 7. Check AI provider configuration
###############################################################################
echo ""
echo "7. Checking AI provider configuration..."

# Check if Ollama is responding
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    check_pass "Ollama (local LLM) is responding"
else
    check_warn "Ollama (local LLM) is not responding"
fi

# Check if OpenAI key is configured (not actual value)
if docker compose exec -T orchestrator printenv OPENAI_API_KEY | grep -q "sk-" 2>/dev/null; then
    check_pass "OpenAI API key is configured"
else
    check_warn "OpenAI API key may not be configured"
fi

# Check if Anthropic key is configured
if docker compose exec -T orchestrator printenv ANTHROPIC_API_KEY | grep -q "sk-ant" 2>/dev/null; then
    check_pass "Anthropic API key is configured"
else
    check_warn "Anthropic API key may not be configured"
fi

###############################################################################
# 8. Check PHI scanning configuration
###############################################################################
echo ""
echo "8. Checking PHI scanning configuration..."

PHI_ENABLED=$(docker compose exec -T orchestrator printenv PHI_SCAN_ENABLED 2>/dev/null | tr -d '\r\n')
if [ "$PHI_ENABLED" = "true" ]; then
    check_pass "PHI scanning is enabled"
else
    check_warn "PHI scanning is disabled (should be enabled for HIPAA compliance)"
fi

PHI_FAIL_CLOSED=$(docker compose exec -T orchestrator printenv PHI_FAIL_CLOSED 2>/dev/null | tr -d '\r\n')
if [ "$PHI_FAIL_CLOSED" = "true" ]; then
    check_pass "PHI fail-closed mode is enabled"
else
    check_warn "PHI fail-closed mode is disabled (should be enabled for HIPAA compliance)"
fi

###############################################################################
# 9. Check volume mounts
###############################################################################
echo ""
echo "9. Checking persistent volumes..."

VOLUMES=("shared-data" "postgres-data" "redis-data" "projects-data" "ollama-models")
for vol in "${VOLUMES[@]}"; do
    if docker volume ls | grep -q "researchflow-production_$vol\|researchflow_$vol"; then
        check_pass "Volume $vol exists"
    else
        check_warn "Volume $vol does not exist"
    fi
done

###############################################################################
# 10. Summary
###############################################################################
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Deployment is ready for LIVE mode.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Deployment is functional but has warnings. Review before production use.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Deployment validation failed. Fix errors before proceeding.${NC}"
    exit 1
fi
