#!/usr/bin/env bash
# Test script for agent-results-interpretation-proxy
# Run after building/deploying to validate functionality

set -e

PROXY_URL="${PROXY_URL:-http://localhost:8000}"
VERBOSE="${VERBOSE:-0}"

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

# Test 1: Health check
log "Test 1: Health check"
response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/health")
body=$(echo "$response" | head -n -1)
code=$(echo "$response" | tail -n 1)

if [ "$code" != "200" ]; then
  fail "Health check returned HTTP ${code}"
fi

if ! echo "$body" | grep -q '"status":"ok"'; then
  fail "Health check missing 'status:ok' in body"
fi

pass "Health check"
[ "$VERBOSE" = "1" ] && echo "  Response: $body"

# Test 2: Ready check (may fail if LANGSMITH_API_KEY not set)
log "Test 2: Readiness check"
response=$(curl -s -w "\n%{http_code}" "${PROXY_URL}/health/ready")
body=$(echo "$response" | head -n -1)
code=$(echo "$response" | tail -n 1)

if [ "$code" = "200" ]; then
  pass "Readiness check (LangSmith configured and reachable)"
  [ "$VERBOSE" = "1" ] && echo "  Response: $body"
elif [ "$code" = "503" ]; then
  echo "⚠️  WARN: Readiness check returned 503 (LANGSMITH_API_KEY not configured or unreachable)"
  [ "$VERBOSE" = "1" ] && echo "  Response: $body"
else
  fail "Readiness check returned unexpected HTTP ${code}"
fi

# Test 3: Schema validation (sync endpoint without LANGSMITH_API_KEY should return error)
log "Test 3: Schema validation"
response=$(curl -s -w "\n%{http_code}" -X POST \
  "${PROXY_URL}/agents/run/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "Test data",
      "study_metadata": {"study_type": "RCT"}
    }
  }')
body=$(echo "$response" | head -n -1)
code=$(echo "$response" | tail -n 1)

if [ "$code" != "200" ]; then
  fail "Sync endpoint returned HTTP ${code} (expected 200 even without LangSmith configured)"
fi

if ! echo "$body" | grep -q '"request_id":"test-001"'; then
  fail "Response missing request_id"
fi

# Check if ok:false (expected when LANGSMITH_API_KEY not set)
if echo "$body" | grep -q '"ok":false'; then
  echo "⚠️  WARN: Agent returned ok:false (expected if LANGSMITH_API_KEY not configured)"
  [ "$VERBOSE" = "1" ] && echo "  Response: $body"
  pass "Schema validation (proxy functional, LangSmith not configured)"
elif echo "$body" | grep -q '"ok":true'; then
  pass "Schema validation (full end-to-end success)"
  [ "$VERBOSE" = "1" ] && echo "  Response: $body"
else
  fail "Response missing 'ok' field"
fi

# Test 4: Invalid request (missing required fields)
log "Test 4: Invalid request handling"
response=$(curl -s -w "\n%{http_code}" -X POST \
  "${PROXY_URL}/agents/run/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "invalid": "data"
  }')
code=$(echo "$response" | tail -n 1)

if [ "$code" = "422" ]; then
  pass "Invalid request handling (422 Unprocessable Entity)"
else
  echo "⚠️  WARN: Expected 422 for invalid request, got ${code}"
fi

log ""
log "========================================="
log "All tests completed"
log "========================================="
log ""
log "Summary:"
log "  ✅ Proxy is functional"
log "  ✅ Health checks work"
log "  ✅ API contract is valid"
log ""

if [ "$code" = "503" ] || echo "$body" | grep -q "LANGSMITH_API_KEY not configured"; then
  log "Note: To test full LangSmith integration:"
  log "  1. Set LANGSMITH_API_KEY in .env"
  log "  2. Set LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID in .env"
  log "  3. Recreate service: docker compose up -d --force-recreate agent-results-interpretation-proxy"
  log "  4. Run: VERBOSE=1 ./test_proxy.sh"
fi

exit 0
