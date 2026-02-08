#!/bin/bash
# ==============================================================================
# Bias Detection Wiring Validation Script
# ==============================================================================
# Quick validation that bias detection is wired correctly per ResearchFlow policy.
#
# Policy:
# - Router dispatch resolves targets via AGENT_ENDPOINTS_JSON only
# - For LangSmith-backed agents, agentKey must equal proxy service name
# - Therefore bias detection must use "agent-bias-detection-proxy" consistently
#
# Usage: ./scripts/validate-bias-wiring.sh
# ==============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

check_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Bias Detection Wiring Validation${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check 1: AGENT_ENDPOINTS_JSON key (validate key exists, not hardcoded URL pattern)
echo -e "${BLUE}[1] AGENT_ENDPOINTS_JSON Configuration${NC}"
if docker compose config 2>/dev/null | grep -q '"agent-bias-detection-proxy"'; then
    check_pass "docker-compose.yml uses correct key: agent-bias-detection-proxy"
elif grep -q '"agent-bias-detection-proxy"' docker-compose.yml; then
    check_pass "docker-compose.yml uses correct key: agent-bias-detection-proxy"
else
    check_fail "docker-compose.yml missing or incorrect key (expected: agent-bias-detection-proxy)"
fi

# Check 2: Router mapping
echo ""
echo -e "${BLUE}[2] Orchestrator Router Mapping${NC}"
if grep -q "CLINICAL_BIAS_DETECTION: 'agent-bias-detection-proxy'" services/orchestrator/src/routes/ai-router.ts; then
    check_pass "ai-router.ts maps CLINICAL_BIAS_DETECTION → agent-bias-detection-proxy"
else
    check_fail "ai-router.ts mapping incorrect or missing"
fi

# Check 3: No legacy keys
echo ""
echo -e "${BLUE}[3] Legacy Key Check${NC}"
if ! grep -q '"agent-bias-detection":"' docker-compose.yml; then
    check_pass "No legacy 'agent-bias-detection' key in AGENT_ENDPOINTS_JSON"
else
    check_fail "Found legacy key 'agent-bias-detection' - should be removed"
fi

# Check 4: Mandatory agent list
echo ""
echo -e "${BLUE}[4] Mandatory Agent List${NC}"
if grep -q "^agent-bias-detection-proxy$" scripts/lib/agent_endpoints_required.txt; then
    check_pass "scripts/lib/agent_endpoints_required.txt includes agent-bias-detection-proxy"
else
    check_fail "Mandatory agent list missing or incorrect"
fi

# Check 5: Smoke test uses correct key
echo ""
echo -e "${BLUE}[5] Smoke Test Validation${NC}"
if grep -q '"agent-bias-detection-proxy"' scripts/stagewise-smoke.sh; then
    check_pass "stagewise-smoke.sh uses correct key in output"
else
    check_fail "stagewise-smoke.sh may reference incorrect key"
fi

# Check 6: Artifact path compliance
echo ""
echo -e "${BLUE}[6] Artifact Path Compliance${NC}"
if grep -q '/data/artifacts/validation/agent-bias-detection-proxy/' scripts/stagewise-smoke.sh; then
    check_pass "Smoke test writes to correct artifact path: /data/artifacts/validation/agent-bias-detection-proxy/"
else
    check_fail "Artifact path non-compliant (expected: /data/artifacts/validation/agent-bias-detection-proxy/)"
fi

# Check 7: Docker compose service definition
echo ""
echo -e "${BLUE}[7] Docker Compose Service${NC}"
if grep -q "^  agent-bias-detection-proxy:" docker-compose.yml; then
    check_pass "docker-compose.yml defines agent-bias-detection-proxy service"
else
    check_fail "Service definition missing or misnamed"
fi

# Check 8: Documentation consistency
echo ""
echo -e "${BLUE}[8] Documentation Consistency${NC}"
DOC_FILES=(
    "AGENT_INVENTORY.md"
    "AGENT_BIAS_DETECTION_BRIEFING.md"
    "docs/agents/clinical-bias-detection/wiring.md"
    "services/agents/agent-bias-detection-proxy/README.md"
)

DOC_PASS=0
DOC_FAIL=0

for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        # Check if doc uses correct key (allowing for both JSON and prose references)
        if grep -q "agent-bias-detection-proxy" "$doc"; then
            DOC_PASS=$((DOC_PASS + 1))
        else
            echo -e "  ${YELLOW}⚠${NC} $doc may not reference agent-bias-detection-proxy"
            DOC_FAIL=$((DOC_FAIL + 1))
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} $doc not found"
        DOC_FAIL=$((DOC_FAIL + 1))
    fi
done

if [ $DOC_FAIL -eq 0 ]; then
    check_pass "All $DOC_PASS documentation files reference correct key"
else
    check_fail "$DOC_FAIL documentation files may have inconsistencies"
fi

# Summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo -e "${GREEN}✓ Bias detection wiring is compliant with ResearchFlow policy${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start services: docker compose up -d"
    echo "  2. Run preflight: ./scripts/hetzner-preflight.sh"
    echo "  3. Run bias smoke: CHECK_BIAS_DETECTION=1 ./scripts/stagewise-smoke.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ VALIDATION FAILED${NC}"
    echo -e "${RED}✗ Fix issues above before deploying${NC}"
    echo ""
    exit 1
fi
