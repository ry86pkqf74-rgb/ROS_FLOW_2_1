#!/usr/bin/env bash
set -euo pipefail

#############################################
# RAG / Vector DB Smoke Test (E2E: ingest → retrieve → verify)
# Works against local compose (default) or staging via BASE_URL.
# Optional: set RAG_INGEST_URL, RAG_RETRIEVE_URL, VERIFY_URL to call
# agents directly instead of orchestrator proxy (e.g. when proxy is unavailable).
#############################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Base URL: default local compose; set BASE_URL for staging or CI
BASE_URL="${BASE_URL:-http://localhost:3001}"

# Optional direct agent URLs (if set, script POSTs to {URL}/agents/run/sync instead of BASE_URL/api/ros/rag/*)
RAG_INGEST_URL="${RAG_INGEST_URL:-}"
RAG_RETRIEVE_URL="${RAG_RETRIEVE_URL:-}"
VERIFY_URL="${VERIFY_URL:-}"

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

# Resolve ingest/retrieve/verify endpoint (orchestrator proxy or direct agent)
ingest_endpoint() {
  if [[ -n "$RAG_INGEST_URL" ]]; then
    echo "${RAG_INGEST_URL%/}/agents/run/sync"
  else
    echo "${BASE_URL}/api/ros/rag/ingest"
  fi
}
retrieve_endpoint() {
  if [[ -n "$RAG_RETRIEVE_URL" ]]; then
    echo "${RAG_RETRIEVE_URL%/}/agents/run/sync"
  else
    echo "${BASE_URL}/api/ros/rag/retrieve"
  fi
}
verify_endpoint() {
  if [[ -n "$VERIFY_URL" ]]; then
    echo "${VERIFY_URL%/}/agents/run/sync"
  else
    echo "${BASE_URL}/api/ros/rag/verify"
  fi
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
# 4. E2E RAG loop: ingest → retrieve → verify
#############################################
KNOWLEDGE_BASE="smoke-e2e-$(date +%s)"
REQUEST_ID="smoke-e2e-$$-$(date +%s)"

# --- Step 1: Ingest 2–3 tiny docs ---
log_info "E2E step 1: Ingest documents into knowledge base $KNOWLEDGE_BASE"

INGEST_BODY=$(jq -n \
  --arg req_id "$REQUEST_ID" \
  --arg kb "$KNOWLEDGE_BASE" \
  '{
    request_id: $req_id,
    task_type: "RAG_INGEST",
    inputs: {
      knowledgeBase: $kb,
      documents: [
        { docId: "doc1", text: "The capital of France is Paris." },
        { docId: "doc2", text: "Water boils at 100 degrees Celsius at sea level." },
        { docId: "doc3", text: "The sky is blue." }
      ]
    },
    mode: "DEMO"
  }')

INGEST_RESP=$(curl -sf -w "\n%{http_code}" -X POST "$(ingest_endpoint)" \
  -H "Content-Type: application/json" \
  -d "$INGEST_BODY" 2>/dev/null || true)
INGEST_HTTP=$(echo "$INGEST_RESP" | tail -1)
INGEST_JSON=$(echo "$INGEST_RESP" | sed '$d')

if [[ ! "$INGEST_HTTP" =~ ^2[0-9][0-9]$ ]]; then
  log_error "Ingest response (last 500 chars): ${INGEST_JSON: -500}"
  ci_fail "E2E failed: ingest returned HTTP $INGEST_HTTP (expected 2xx)."
fi

STATUS=$(echo "$INGEST_JSON" | jq -r '.status // empty')
if [[ "$STATUS" != "ok" ]]; then
  log_error "Ingest response body: $INGEST_JSON"
  ci_fail "E2E failed: ingest returned status \"$STATUS\" (expected \"ok\")."
fi

INGESTED_COUNT=$(echo "$INGEST_JSON" | jq -r '.outputs.ingestedCount // .outputs.ingested_count // 0')
if [[ "$INGESTED_COUNT" == "null" ]] || [[ "$INGESTED_COUNT" == "" ]]; then
  INGESTED_COUNT=0
fi
if [[ "$INGESTED_COUNT" -eq 0 ]]; then
  log_error "Ingest response body: $INGEST_JSON"
  ci_fail "E2E failed: ingest returned ingestedCount==0 (expected >= 1)."
fi

CHUNK_COUNT=$(echo "$INGEST_JSON" | jq -r '.outputs.chunkCount // .outputs.chunk_count // 0')
if [[ "$CHUNK_COUNT" == "null" ]] || [[ "$CHUNK_COUNT" == "" ]]; then
  log_error "Ingest response missing outputs.chunkCount"
  ci_fail "E2E failed: ingest response schema missing required keys (outputs.chunkCount / ingestedCount)."
fi

log_info "Ingest passed ✓ (ingestedCount=$INGESTED_COUNT, chunkCount=$CHUNK_COUNT)"

# --- Step 2: Retrieve ---
log_info "E2E step 2: Retrieve from knowledge base"

RETRIEVE_BODY=$(jq -n \
  --arg req_id "${REQUEST_ID}-retrieve" \
  --arg kb "$KNOWLEDGE_BASE" \
  '{
    request_id: $req_id,
    task_type: "RAG_RETRIEVE",
    inputs: { query: "What is the capital of France?", knowledgeBase: $kb },
    mode: "DEMO"
  }')

RETRIEVE_RESP=$(curl -sf -w "\n%{http_code}" -X POST "$(retrieve_endpoint)" \
  -H "Content-Type: application/json" \
  -d "$RETRIEVE_BODY" 2>/dev/null || true)
RETRIEVE_HTTP=$(echo "$RETRIEVE_RESP" | tail -1)
RETRIEVE_JSON=$(echo "$RETRIEVE_RESP" | sed '$d')

if [[ ! "$RETRIEVE_HTTP" =~ ^2[0-9][0-9]$ ]]; then
  log_error "Retrieve response (last 500 chars): ${RETRIEVE_JSON: -500}"
  ci_fail "E2E failed: retrieve returned HTTP $RETRIEVE_HTTP (expected 2xx)."
fi

STATUS=$(echo "$RETRIEVE_JSON" | jq -r '.status // empty')
if [[ "$STATUS" != "ok" ]]; then
  log_error "Retrieve response body: $RETRIEVE_JSON"
  ci_fail "E2E failed: retrieve returned status \"$STATUS\" (expected \"ok\")."
fi

# Chunks may be in .grounding.chunks or .outputs.groundingPack.chunks; count either way
CHUNKS_LEN=$(echo "$RETRIEVE_JSON" | jq '[.grounding.chunks[]? // .outputs.groundingPack.chunks[]?] | length')
NUM_CHUNKS=$(echo "$RETRIEVE_JSON" | jq -r '.outputs.chunk_count // .outputs.chunkCount // 0')
if [[ "$CHUNKS_LEN" == "null" ]] || [[ "$CHUNKS_LEN" -lt 1 ]]; then
  if [[ "$NUM_CHUNKS" == "null" ]] || [[ "$NUM_CHUNKS" == "" ]] || [[ "$NUM_CHUNKS" -lt 1 ]]; then
    log_error "Retrieve response body: $RETRIEVE_JSON"
    ci_fail "E2E failed: retrieve returned 0 chunks (expected >= 1)."
  fi
fi

# Grounding for verify: prefer outputs.groundingPack then grounding
GROUNDING_PACK=$(echo "$RETRIEVE_JSON" | jq -c '.outputs.groundingPack // .grounding // {}')
if [[ "$GROUNDING_PACK" == "{}" ]] || [[ "$GROUNDING_PACK" == "null" ]]; then
  log_error "Retrieve response missing grounding/groundingPack"
  ci_fail "E2E failed: retrieve response schema missing required keys (grounding or outputs.groundingPack)."
fi

log_info "Retrieve passed ✓"

# --- Step 3: Verify (one claim supported, one unsupported => overallPass false) ---
log_info "E2E step 3: Verify claims against grounding"

VERIFY_BODY=$(jq -n \
  --arg req_id "${REQUEST_ID}-verify" \
  --argjson gp "$GROUNDING_PACK" \
  '{
    request_id: $req_id,
    task_type: "CLAIM_VERIFY",
    inputs: {
      claims: [
        "The capital of France is Paris.",
        "The capital of France is London."
      ],
      groundingPack: $gp,
      governanceMode: "DEMO"
    },
    mode: "DEMO"
  }')

VERIFY_RESP=$(curl -sf -w "\n%{http_code}" -X POST "$(verify_endpoint)" \
  -H "Content-Type: application/json" \
  -d "$VERIFY_BODY" 2>/dev/null || true)
VERIFY_HTTP=$(echo "$VERIFY_RESP" | tail -1)
VERIFY_JSON=$(echo "$VERIFY_RESP" | sed '$d')

if [[ ! "$VERIFY_HTTP" =~ ^2[0-9][0-9]$ ]]; then
  log_error "Verify response (last 500 chars): ${VERIFY_JSON: -500}"
  ci_fail "E2E failed: verify returned HTTP $VERIFY_HTTP (expected 2xx)."
fi

STATUS=$(echo "$VERIFY_JSON" | jq -r '.status // empty')
if [[ "$STATUS" != "ok" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify returned status \"$STATUS\" (expected \"ok\")."
fi

OVERALL_PASS=$(echo "$VERIFY_JSON" | jq -r '.outputs.overallPass // .outputs.overall_pass // "missing"')
if [[ "$OVERALL_PASS" == "missing" ]] || [[ "$OVERALL_PASS" == "null" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify response schema missing required key (outputs.overallPass)."
fi

# We expect overallPass == false (one claim pass, one fail)
if [[ "$OVERALL_PASS" != "false" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify returned overallPass=$OVERALL_PASS (expected false for one pass + one fail)."
fi

CLAIM_VERDICTS=$(echo "$VERIFY_JSON" | jq -r '.outputs.claim_verdicts // empty')
if [[ -z "$CLAIM_VERDICTS" ]] || [[ "$CLAIM_VERDICTS" == "null" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify response schema missing required key (outputs.claim_verdicts)."
fi

log_info "Verify passed ✓ (overallPass=false as expected)"

#############################################
# 5. Summary
#############################################
echo ""
log_info "========================================="
log_info "RAG smoke test PASSED (E2E: ingest → retrieve → verify)"
log_info "  base_url: $BASE_URL"
log_info "========================================="
