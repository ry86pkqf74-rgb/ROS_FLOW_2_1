#!/usr/bin/env bash
set -euo pipefail

#############################################
# Post-Merge Truth Check
# Fast validation that contract + smoke + key agents are coherent after merges.
# Run this locally and/or on staging after merging branches.
#
# Runs:
#   1. Contract checker (all agents)
#   2. Stage 2 smoke test (lit-review E2E)
#   3. RAG smoke test (ingest → retrieve → verify)
#   4. AI bridge smoke endpoint (optional invoke if keys set)
#
# Exit code: 0 = PASS, 1 = FAIL
#############################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Base URL: default local compose; set BASE_URL for staging
BASE_URL="${BASE_URL:-http://localhost:3001}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_section() { echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}\n"; }

# GitHub Actions: emit error annotation so failures are visible
ci_fail() {
  local msg="$1"
  log_error "$msg"
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "::error::[postmerge-check] $msg"
  fi
}

# Tracking results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

#############################################
# Helper: run test and track result
#############################################
run_test() {
  local test_name="$1"
  local test_command="$2"
  
  TESTS_RUN=$((TESTS_RUN + 1))
  log_section "$test_name"
  
  if eval "$test_command"; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    log_info "✓ $test_name PASSED"
    return 0
  else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$test_name")
    log_error "✗ $test_name FAILED"
    return 1
  fi
}

#############################################
# Helper: dump docker compose logs on failure
#############################################
dump_logs_on_failure() {
  local service="$1"
  local lines="${2:-100}"
  
  if command -v docker &> /dev/null && docker compose ps "$service" &> /dev/null; then
    log_error "=== Docker logs for $service (last $lines lines) ==="
    docker compose logs --tail="$lines" "$service" 2>&1 || echo "(failed to fetch logs)"
  fi
}

#############################################
# 1. Contract Checker
#############################################
contract_check() {
  log_info "Running contract checker against all agents..."
  
  # Build agent contract targets from docker-compose.yml agent services
  # Format: baseUrl=task_type
  AGENT_TARGETS=(
    "http://agent-stage2-lit:8000=LIT_RETRIEVAL"
    "http://agent-stage2-screen:8000=STAGE2_SCREEN"
    "http://agent-stage2-extract:8000=STAGE2_EXTRACT"
    "http://agent-lit-retrieval:8000=LIT_RETRIEVAL"
    "http://agent-rag-ingest:8000=RAG_INGEST"
    "http://agent-rag-retrieve:8000=RAG_RETRIEVE"
    "http://agent-policy-review:8000=POLICY_REVIEW"
    "http://agent-verify:8000=CLAIM_VERIFY"
    "http://agent-intro-writer:8000=SECTION_WRITER"
    "http://agent-methods-writer:8000=SECTION_WRITER"
  )
  
  # Join with commas
  export AGENT_CONTRACT_TARGETS=$(IFS=,; echo "${AGENT_TARGETS[*]}")
  
  # Set test queries for specific agents if needed
  export RESEARCH_QUESTION="Post-merge contract check: systematic reviews in clinical decision support"
  export RAG_RETRIEVE_QUERY="contract-check query"
  export RAG_RETRIEVE_KB="default"
  
  if python3 scripts/check-agent-contract.py; then
    return 0
  else
    log_error "Contract checker failed"
    # Dump logs for key agents
    dump_logs_on_failure "agent-stage2-lit" 50
    dump_logs_on_failure "agent-rag-retrieve" 50
    return 1
  fi
}

#############################################
# 2. Stage 2 Smoke Test (E2E)
#############################################
stage2_smoke() {
  log_info "Running Stage 2 smoke test (literature review E2E)..."
  
  # Set BASE_URL for smoke script
  export BASE_URL="$BASE_URL"
  export SMOKE_STAGE2_TIMEOUT="${SMOKE_STAGE2_TIMEOUT:-120}"
  
  if bash tools/dev/smoke-stage2.sh; then
    return 0
  else
    log_error "Stage 2 smoke test failed"
    dump_logs_on_failure "orchestrator" 50
    dump_logs_on_failure "worker" 50
    dump_logs_on_failure "agent-stage2-lit" 50
    return 1
  fi
}

#############################################
# 3. RAG Smoke Test (E2E)
#############################################
rag_smoke() {
  log_info "Running RAG smoke test (ingest → retrieve → verify)..."
  
  # Set BASE_URL for smoke script
  export BASE_URL="$BASE_URL"
  
  if bash tools/dev/smoke-rag.sh; then
    return 0
  else
    log_error "RAG smoke test failed"
    dump_logs_on_failure "agent-rag-ingest" 50
    dump_logs_on_failure "agent-rag-retrieve" 50
    dump_logs_on_failure "agent-verify" 50
    dump_logs_on_failure "chromadb" 50
    return 1
  fi
}

#############################################
# 4. AI Bridge Smoke Check
#############################################
ai_bridge_smoke() {
  log_info "Running AI bridge smoke check..."
  
  # First check without invoke (just config check)
  SMOKE_RESP=$(curl -sf -w "\n%{http_code}" "$BASE_URL/api/ai-bridge/smoke" 2>&1 || true)
  SMOKE_HTTP=$(echo "$SMOKE_RESP" | tail -1)
  SMOKE_BODY=$(echo "$SMOKE_RESP" | sed '$d')
  
  if [[ "$SMOKE_HTTP" != "200" ]]; then
    log_error "AI bridge smoke endpoint returned HTTP $SMOKE_HTTP (expected 200)"
    echo "$SMOKE_BODY"
    dump_logs_on_failure "orchestrator" 50
    return 1
  fi
  
  REAL_PROVIDER=$(echo "$SMOKE_BODY" | jq -r '.realProvider // false')
  log_info "AI bridge smoke: realProvider=$REAL_PROVIDER"
  echo "$SMOKE_BODY" | jq . 2>/dev/null || echo "$SMOKE_BODY"
  
  # Optional: if real provider is configured, do live invoke check
  # Only if AI_BRIDGE_INVOKE=1 (defaults to 0 for speed)
  if [[ "${AI_BRIDGE_INVOKE:-0}" == "1" ]] && [[ "$REAL_PROVIDER" == "true" ]]; then
    log_info "Performing live AI bridge invoke (AI_BRIDGE_INVOKE=1)..."
    
    INVOKE_RESP=$(curl -sf -w "\n%{http_code}" "$BASE_URL/api/ai-bridge/smoke?invoke=1" 2>&1 || true)
    INVOKE_HTTP=$(echo "$INVOKE_RESP" | tail -1)
    INVOKE_BODY=$(echo "$INVOKE_RESP" | sed '$d')
    
    if [[ "$INVOKE_HTTP" != "200" ]]; then
      log_error "AI bridge smoke invoke returned HTTP $INVOKE_HTTP (expected 200)"
      echo "$INVOKE_BODY"
      return 1
    fi
    
    INVOKED=$(echo "$INVOKE_BODY" | jq -r '.invoked // false')
    if [[ "$INVOKED" != "true" ]]; then
      log_error "AI bridge smoke invoke did not complete successfully"
      echo "$INVOKE_BODY"
      return 1
    fi
    
    log_info "AI bridge live invoke succeeded ✓"
    echo "$INVOKE_BODY" | jq . 2>/dev/null || echo "$INVOKE_BODY"
  fi
  
  return 0
}

#############################################
# Main Execution
#############################################
main() {
  log_section "Post-Merge Truth Check"
  log_info "Target: $BASE_URL"
  log_info "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo ""
  
  # Check if we're running against local compose or remote staging
  RUN_LOCAL=0
  if [[ "$BASE_URL" == "http://localhost"* ]] || [[ "$BASE_URL" == "http://127.0.0.1"* ]]; then
    RUN_LOCAL=1
    log_info "Detected local environment (BASE_URL=$BASE_URL)"
    
    # Quick pre-check: are services up?
    if ! docker compose ps orchestrator | grep -q "Up"; then
      log_error "Orchestrator service not running. Start with: docker compose up -d"
      exit 1
    fi
  else
    log_info "Detected remote environment (BASE_URL=$BASE_URL)"
  fi
  
  # Run all checks (continue even if one fails, to get full picture)
  run_test "Contract Checker" "contract_check" || true
  run_test "Stage 2 Smoke Test" "stage2_smoke" || true
  run_test "RAG Smoke Test" "rag_smoke" || true
  run_test "AI Bridge Smoke" "ai_bridge_smoke" || true
  
  #############################################
  # Summary
  #############################################
  echo ""
  log_section "Post-Merge Check Summary"
  echo ""
  
  if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "  Total tests:  $TESTS_RUN"
    echo "  Passed:       $TESTS_PASSED"
    echo "  Failed:       $TESTS_FAILED"
    echo ""
    log_info "Post-merge verification complete. System is coherent."
    exit 0
  else
    echo -e "${RED}${BOLD}✗ SOME CHECKS FAILED${NC}"
    echo ""
    echo "  Total tests:  $TESTS_RUN"
    echo "  Passed:       $TESTS_PASSED"
    echo "  Failed:       $TESTS_FAILED"
    echo ""
    echo -e "${RED}Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
      echo "  - $test"
    done
    echo ""
    
    if [[ $RUN_LOCAL -eq 1 ]]; then
      log_info "Local debugging commands:"
      echo "  View all logs:        docker compose logs -f"
      echo "  View orchestrator:    docker compose logs -f orchestrator"
      echo "  View worker:          docker compose logs -f worker"
      echo "  View agents:          docker compose logs -f agent-stage2-lit agent-rag-retrieve"
      echo "  Restart services:     docker compose restart"
      echo "  Check DB:             docker compose exec postgres psql -U ros -d ros"
    fi
    
    ci_fail "Post-merge check failed: $TESTS_FAILED/$TESTS_RUN tests failed"
    exit 1
  fi
}

# Handle script arguments
case "${1:-}" in
  --help|-h)
    cat <<EOF
Post-Merge Truth Check
Fast validation that contract + smoke + key agents are coherent after merges.

Usage:
  $0 [options]

Options:
  --help, -h              Show this help message

Environment Variables:
  BASE_URL                Target URL (default: http://localhost:3001)
  AI_BRIDGE_INVOKE        Set to 1 to perform live AI bridge invoke (default: 0)
  SMOKE_STAGE2_TIMEOUT    Stage 2 smoke test timeout in seconds (default: 120)

Examples:
  # Local (default)
  $0

  # Staging
  BASE_URL=https://staging.researchflow.example.com $0

  # With live AI bridge invoke
  AI_BRIDGE_INVOKE=1 $0

  # CI mode (GitHub Actions sets GITHUB_ACTIONS automatically)
  GITHUB_ACTIONS=true $0
EOF
    exit 0
    ;;
  *)
    main "$@"
    ;;
esac
