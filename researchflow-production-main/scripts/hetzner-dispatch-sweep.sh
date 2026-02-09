#!/usr/bin/env bash
# Hetzner Deployment - Dispatch Routing Validation
# Tests dispatch routing for the 4 currently running dispatch-capable agents
# Run on Hetzner: ./scripts/hetzner-dispatch-sweep.sh
#
# Agents tested (from 10 running agents):
#   1. agent-lit-retrieval      → LIT_RETRIEVAL
#   2. agent-policy-review      → POLICY_REVIEW  
#   3. agent-stage2-lit         → STAGE_2_LITERATURE_REVIEW
#   4. agent-stage2-extract     → STAGE_2_EXTRACT

set -e

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Hetzner Dispatch Routing Validation - 4 Agents           ║${NC}"
echo -e "${BLUE}║     Target: ${ORCHESTRATOR_URL}                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for WORKER_SERVICE_TOKEN
if [ -z "$WORKER_SERVICE_TOKEN" ]; then
  echo -e "${RED}ERROR: WORKER_SERVICE_TOKEN not set${NC}"
  echo "The dispatch endpoint requires service token authentication."
  echo "Run: export WORKER_SERVICE_TOKEN=\$(grep WORKER_SERVICE_TOKEN .env | cut -d= -f2)"
  exit 1
fi

AUTH_HEADER="Authorization: Bearer $WORKER_SERVICE_TOKEN"

# Test counters
TOTAL_TESTS=4
PASSED=0
FAILED=0

# Test dispatch function
test_dispatch() {
  local task_type="$1"
  local expected_agent="$2"
  local test_num="$3"
  
  echo -e "${BLUE}[Test $test_num/$TOTAL_TESTS]${NC} Testing task_type: ${YELLOW}$task_type${NC}"
  echo -e "  Expected agent: ${YELLOW}$expected_agent${NC}"
  
  # Build request payload
  local payload=$(cat <<EOF
{
  "task_type": "$task_type",
  "request_id": "dispatch-test-$task_type-$(date +%s)",
  "workflow_id": "test-workflow-001",
  "user_id": "test-user-hetzner",
  "mode": "DEMO",
  "inputs": {
    "query": "Test dispatch routing for $task_type",
    "context": "Hetzner deployment validation"
  }
}
EOF
)
  
  # Call dispatch endpoint
  response=$(curl -sS -w "\n%{http_code}" \
    -X POST \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$ORCHESTRATOR_URL/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
  
  http_code=$(echo "$response" | tail -n 1)
  body=$(echo "$response" | head -n -1)
  
  # Parse response
  if [ "${http_code:0:1}" = "2" ]; then
    routed_agent=$(echo "$body" | grep -o '"agent_name":"[^"]*"' | cut -d'"' -f4)
    agent_url=$(echo "$body" | grep -o '"agent_url":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$routed_agent" = "$expected_agent" ]; then
      echo -e "  ${GREEN}✓ PASS${NC} - Routed to: $routed_agent"
      echo -e "  Agent URL: $agent_url"
      PASSED=$((PASSED + 1))
    else
      echo -e "  ${RED}✗ FAIL${NC} - Routed to: $routed_agent (expected: $expected_agent)"
      FAILED=$((FAILED + 1))
    fi
  else
    echo -e "  ${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "  Response: $body"
    FAILED=$((FAILED + 1))
  fi
  
  echo ""
}

# Run dispatch tests
echo -e "${BLUE}Starting dispatch routing tests...${NC}\n"

test_dispatch "LIT_RETRIEVAL" "agent-lit-retrieval" 1
test_dispatch "POLICY_REVIEW" "agent-policy-review" 2
test_dispatch "STAGE_2_LITERATURE_REVIEW" "agent-stage2-lit" 3
test_dispatch "STAGE_2_EXTRACT" "agent-stage2-extract" 4

# Summary
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     Test Summary                              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo -e "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "${RED}Failed:       $FAILED${NC}"
else
  echo -e "Failed:       $FAILED"
fi
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  ✓ ALL DISPATCH TESTS PASSED                                  ║${NC}"
  echo -e "${GREEN}║  Router is correctly routing to all 4 available agents        ║${NC}"
  echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
  exit 0
else
  echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}║  ✗ SOME TESTS FAILED                                          ║${NC}"
  echo -e "${RED}║  Check agent availability and AGENT_ENDPOINTS_JSON            ║${NC}"
  echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
  exit 1
fi
