#!/usr/bin/env bash
# Test script for all 3 LangSmith proxy services
# Run after deployment to validate functionality

set -e

VERBOSE="${VERBOSE:-0}"
PROXY_URLS=(
  "http://localhost:8000"  # Will be accessed via docker exec
)

PROXY_SERVICES=(
  "agent-results-interpretation-proxy"
  "agent-clinical-manuscript-proxy"
  "agent-section-drafter-proxy"
)

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

fail() {
  echo "❌ FAIL: $*" >&2
  exit 1
}

pass() {
  echo "✅ PASS: $*"
}

warn() {
  echo "⚠️  WARN: $*"
}

test_proxy() {
  local service="$1"
  local test_name="$2"
  
  log "Testing ${service}: ${test_name}"
  
  # Test 1: Container running
  if ! docker compose ps "$service" | grep -q "Up"; then
    fail "${service}: Container not running"
  fi
  pass "${service}: Container is running"
  
  # Test 2: Health check
  response=$(docker compose exec -T "$service" curl -s -w "\n%{http_code}" "http://localhost:8000/health" 2>/dev/null || echo -e "\n000")
  body=$(echo "$response" | head -n -1)
  code=$(echo "$response" | tail -n 1)
  
  if [ "$code" != "200" ]; then
    fail "${service}: Health check returned HTTP ${code}"
  fi
  
  if ! echo "$body" | grep -q '"status":"ok"'; then
    fail "${service}: Health check missing 'status:ok'"
  fi
  pass "${service}: Health check OK"
  [ "$VERBOSE" = "1" ] && echo "  Response: $body"
  
  # Test 3: Readiness check
  response=$(docker compose exec -T "$service" curl -s -w "\n%{http_code}" "http://localhost:8000/health/ready" 2>/dev/null || echo -e "\n000")
  body=$(echo "$response" | head -n -1)
  code=$(echo "$response" | tail -n 1)
  
  if [ "$code" = "200" ]; then
    pass "${service}: Readiness check OK (LangSmith configured)"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
  elif [ "$code" = "503" ]; then
    warn "${service}: Readiness 503 (LANGSMITH_API_KEY not configured or unreachable)"
    [ "$VERBOSE" = "1" ] && echo "  Response: $body"
  else
    fail "${service}: Readiness returned unexpected HTTP ${code}"
  fi
  
  # Test 4: Check environment variables
  langsmith_key=$(docker compose exec -T "$service" sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
  agent_id=$(docker compose exec -T "$service" sh -c 'echo ${LANGSMITH_AGENT_ID:+SET}' 2>/dev/null || echo "")
  
  if [ "$langsmith_key" = "SET" ]; then
    pass "${service}: LANGSMITH_API_KEY is set"
  else
    warn "${service}: LANGSMITH_API_KEY is NOT set"
  fi
  
  if [ "$agent_id" = "SET" ]; then
    pass "${service}: LANGSMITH_AGENT_ID is set"
  else
    warn "${service}: LANGSMITH_AGENT_ID is NOT set"
  fi
  
  echo ""
}

# Main execution
log "========================================="
log "LangSmith Proxy Services Test Suite"
log "========================================="
log ""

# Check docker compose is available
if ! command -v docker >/dev/null 2>&1; then
  fail "docker command not found"
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose not available"
fi

# Test each proxy service
for service in "${PROXY_SERVICES[@]}"; do
  test_proxy "$service" "All checks"
done

# Summary
log "========================================="
log "Test Summary"
log "========================================="
log ""
log "Results:"
log "  ✅ All containers running"
log "  ✅ Health endpoints responding"
log ""

# Check if any warnings
has_warnings=false
for service in "${PROXY_SERVICES[@]}"; do
  langsmith_key=$(docker compose exec -T "$service" sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
  agent_id=$(docker compose exec -T "$service" sh -c 'echo ${LANGSMITH_AGENT_ID:+SET}' 2>/dev/null || echo "")
  
  if [ "$langsmith_key" != "SET" ] || [ "$agent_id" != "SET" ]; then
    has_warnings=true
    break
  fi
done

if [ "$has_warnings" = true ]; then
  log "⚠️  Configuration incomplete:"
  log "  - Some services missing LANGSMITH_API_KEY or LANGSMITH_AGENT_ID"
  log "  - Add missing env vars to .env"
  log "  - Restart services: docker compose up -d --force-recreate"
  log ""
  log "Required environment variables:"
  log "  LANGSMITH_API_KEY=lsv2_pt_..."
  log "  LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=<uuid>"
  log "  LANGSMITH_MANUSCRIPT_AGENT_ID=<uuid>"
  log "  LANGSMITH_SECTION_DRAFTER_AGENT_ID=<uuid>"
  log ""
else
  log "✅ All services fully configured"
fi

log "Next steps:"
log "  1. Configure missing environment variables (if any)"
log "  2. Test router dispatch: curl POST /api/ai/router/dispatch"
log "  3. Run full smoke test: CHECK_RESULTS_INTERPRETATION=1 ./scripts/stagewise-smoke.sh"
log "  4. Monitor LangSmith UI: https://smith.langchain.com/"

exit 0
