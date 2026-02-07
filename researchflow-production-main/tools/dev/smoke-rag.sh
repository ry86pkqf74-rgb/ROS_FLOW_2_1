#!/usr/bin/env bash
set -euo pipefail

#############################################
# RAG / Vector DB Smoke Test
# Works against local compose (default) or staging via BASE_URL.
#############################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Base URL: default local compose; set BASE_URL for staging or CI
BASE_URL="${BASE_URL:-http://localhost:3001}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# GitHub Actions: emit error annotation so failures are visible
ci_fail() {
  local msg="$1"
  log_error "$msg"
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "::error::[smoke-rag] $msg"
  fi
  exit 1
}

#############################################
# 1. Health check
#############################################
log_info "RAG smoke target: $BASE_URL"

HEALTH_RESP=$(curl -sf -w "\n%{http_code}" "$BASE_URL/health" 2>/dev/null || true)
HEALTH_HTTP=$(echo "$HEALTH_RESP" | tail -1)
HEALTH_BODY=$(echo "$HEALTH_RESP" | sed '$d')

if [[ "$HEALTH_HTTP" != "200" ]]; then
  ci_fail "Health check failed: HTTP $HEALTH_HTTP (expected 200). Is the orchestrator running at $BASE_URL?"
fi
log_info "Health check passed ✓"

#############################################
# 2. Analysis/capabilities (RAG pipeline readiness)
#############################################
CAP_RESP=$(curl -sf -w "\n%{http_code}" "$BASE_URL/api/ros/analysis/capabilities" 2>/dev/null || true)
CAP_HTTP=$(echo "$CAP_RESP" | tail -1)
CAP_BODY=$(echo "$CAP_RESP" | sed '$d')

if [[ "$CAP_HTTP" != "200" ]]; then
  ci_fail "Capabilities endpoint failed: HTTP $CAP_HTTP (expected 200). Response: $CAP_BODY"
fi
echo "$CAP_BODY" | jq . 2>/dev/null || echo "$CAP_BODY"
log_info "Capabilities check passed ✓"

#############################################
# 3. Vector DB health (optional; may not be exposed on all envs)
#############################################
VDB_RESP=$(curl -sf -w "\n%{http_code}" "$BASE_URL/api/ros/vectordb/health" 2>/dev/null || true)
VDB_HTTP=$(echo "$VDB_RESP" | tail -1)
VDB_BODY=$(echo "$VDB_RESP" | sed '$d')

if [[ "$VDB_HTTP" == "200" ]]; then
  echo "$VDB_BODY" | jq . 2>/dev/null || echo "$VDB_BODY"
  log_info "Vector DB health check passed ✓"
else
  log_warn "Vector DB health returned HTTP $VDB_HTTP (optional; may be internal-only)"
fi

#############################################
# 4. Summary
#############################################
echo ""
log_info "========================================="
log_info "RAG smoke test PASSED"
log_info "  base_url: $BASE_URL"
log_info "========================================="
