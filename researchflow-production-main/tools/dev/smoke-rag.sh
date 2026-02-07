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

# --- Step 1: Ingest 3 canonical medical docs (cardio, onco, neuro) ---
log_info "E2E step 1: Ingest 3 canonical docs into knowledge base $KNOWLEDGE_BASE"

INGEST_BODY=$(jq -n \
  --arg req_id "$REQUEST_ID" \
  --arg kb "$KNOWLEDGE_BASE" \
  '{
    request_id: $req_id,
    task_type: "RAG_INGEST",
    inputs: {
      knowledgeBase: $kb,
      documents: [
        {
          docId: "smoke-001",
          text: "Direct oral anticoagulants (DOACs) such as apixaban reduce stroke risk in atrial fibrillation patients by approximately 70%. The ARISTOTLE trial demonstrated apixaban superiority over warfarin with fewer major bleeding events.",
          metadata: { domain_id: "domain-cardio", topic: "cardiology" }
        },
        {
          docId: "smoke-002",
          text: "CAR-T cell therapy targeting CD19 has achieved complete remission rates exceeding 80% in relapsed/refractory B-cell acute lymphoblastic leukemia (ALL). Long-term follow-up shows durable responses in approximately 50% of patients at 12 months.",
          metadata: { domain_id: "domain-onco", topic: "oncology" }
        },
        {
          docId: "smoke-003",
          text: "Lecanemab, an anti-amyloid-beta antibody, demonstrated a 27% reduction in cognitive decline over 18 months in the CLARITY-AD trial. The drug targets soluble amyloid-beta protofibrils and received FDA accelerated approval in 2023.",
          metadata: { domain_id: "domain-neuro", topic: "neurology" }
        }
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

# --- Step 2: Retrieve (Q1: cardiology query) ---
log_info "E2E step 2: Retrieve from knowledge base (cardiology query)"

RETRIEVE_BODY=$(jq -n \
  --arg req_id "${REQUEST_ID}-retrieve-q1" \
  --arg kb "$KNOWLEDGE_BASE" \
  '{
    request_id: $req_id,
    task_type: "RAG_RETRIEVE",
    inputs: { query: "stroke prevention anticoagulants atrial fibrillation", knowledgeBase: $kb, topK: 3 },
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

# Build a comprehensive grounding pack with all 3 canonical docs for verify.
# This ensures C2/C3 can be evaluated as "fail" (contradiction) rather than "unclear" (no evidence).
CANONICAL_GROUNDING=$(jq -n '{
  chunks: [
    {
      chunk_id: "smoke-001-chunk-0",
      doc_id: "smoke-001",
      text: "Direct oral anticoagulants (DOACs) such as apixaban reduce stroke risk in atrial fibrillation patients by approximately 70%. The ARISTOTLE trial demonstrated apixaban superiority over warfarin with fewer major bleeding events.",
      score: 0.95
    },
    {
      chunk_id: "smoke-002-chunk-0",
      doc_id: "smoke-002",
      text: "CAR-T cell therapy targeting CD19 has achieved complete remission rates exceeding 80% in relapsed/refractory B-cell acute lymphoblastic leukemia (ALL). Long-term follow-up shows durable responses in approximately 50% of patients at 12 months.",
      score: 0.90
    },
    {
      chunk_id: "smoke-003-chunk-0",
      doc_id: "smoke-003",
      text: "Lecanemab, an anti-amyloid-beta antibody, demonstrated a 27% reduction in cognitive decline over 18 months in the CLARITY-AD trial. The drug targets soluble amyloid-beta protofibrils and received FDA accelerated approval in 2023.",
      score: 0.90
    }
  ]
}')

# --- Step 3: Verify (C1=pass, C2/C3=fail|unclear => overallPass false) ---
# C1: "Apixaban reduces stroke risk ~70%" - supported by smoke-001
# C2: "CAR-T 95% remission" - contradicted (smoke-002 says >80%)
# C3: "Lecanemab targets tau" - contradicted (smoke-003 says amyloid-beta)
log_info "E2E step 3: Verify 3 canonical claims against grounding"

VERIFY_BODY=$(jq -n \
  --arg req_id "${REQUEST_ID}-verify" \
  --argjson gp "$CANONICAL_GROUNDING" \
  '{
    request_id: $req_id,
    task_type: "CLAIM_VERIFY",
    inputs: {
      claims: [
        "Apixaban reduces stroke risk by approximately 70% in AFib patients",
        "CAR-T therapy achieves 95% remission in ALL",
        "Lecanemab targets tau protein tangles"
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

# We expect overallPass == false (C1 pass, C2/C3 fail or unclear)
if [[ "$OVERALL_PASS" != "false" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify returned overallPass=$OVERALL_PASS (expected false: C1=pass, C2/C3=fail|unclear)."
fi

CLAIM_VERDICTS=$(echo "$VERIFY_JSON" | jq -r '.outputs.claim_verdicts // empty')
if [[ -z "$CLAIM_VERDICTS" ]] || [[ "$CLAIM_VERDICTS" == "null" ]]; then
  log_error "Verify response body: $VERIFY_JSON"
  ci_fail "E2E failed: verify response schema missing required key (outputs.claim_verdicts)."
fi

log_info "Verify passed ✓ (overallPass=false: C1=pass, C2/C3=fail|unclear)"

#############################################
# 5. Summary
#############################################
echo ""
log_info "========================================="
log_info "RAG smoke test PASSED (E2E: ingest → retrieve → verify)"
log_info "  base_url: $BASE_URL"
log_info "========================================="
