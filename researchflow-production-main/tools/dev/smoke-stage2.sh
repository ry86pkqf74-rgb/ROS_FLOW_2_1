#!/usr/bin/env bash
set -euo pipefail

#############################################
# Stage 2 Smoke Test - Literature Review E2E
# Full path: execute -> BullMQ -> worker -> router -> agent
# Use BASE_URL for staging; unset = local compose (starts services).
#############################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Base URL: default local compose; set BASE_URL for staging or CI
BASE_URL="${BASE_URL:-http://localhost:3001}"
# When targeting a remote URL we skip starting docker compose
RUN_LOCAL_COMPOSE=0
if [[ -z "${BASE_URL}" ]] || [[ "$BASE_URL" == "http://localhost"* ]] || [[ "$BASE_URL" == "http://127.0.0.1"* ]]; then
  RUN_LOCAL_COMPOSE=1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# GitHub Actions: emit error annotation so failures are visible
ci_fail() {
  local msg="$1"
  log_error "$msg"
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "::error::[smoke-stage2] $msg"
  fi
  exit 1
}

# Timeout for polling job completion (seconds)
SMOKE_TIMEOUT="${SMOKE_STAGE2_TIMEOUT:-120}"

#############################################
# 1. Verify required environment variables
#############################################
log_info "Checking environment (BASE_URL=$BASE_URL, RUN_LOCAL_COMPOSE=$RUN_LOCAL_COMPOSE)..."

if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
  REQUIRED_VARS=("WORKER_SERVICE_TOKEN" "DATABASE_URL" "REDIS_URL")
  MISSING_VARS=()
  for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]] && ! grep -qE "^${var}=" .env 2>/dev/null; then
      MISSING_VARS+=("$var")
    fi
  done
  if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required environment variables:"
    printf '  - %s\n' "${MISSING_VARS[@]}"
    ci_fail "Missing: ${MISSING_VARS[*]}"
  fi
else
  # Staging: auth may be required
  if [[ -z "${WORKER_SERVICE_TOKEN:-}" ]] && ! grep -qE "^WORKER_SERVICE_TOKEN=" .env 2>/dev/null; then
    log_warn "WORKER_SERVICE_TOKEN not set; staging may require auth"
  fi
fi

# Load .env if present
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

log_info "Environment check passed ✓"

#############################################
# 2. Restart required services (local compose only)
#############################################
if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
  log_info "Restarting services (orchestrator, worker, agent)..."

  docker compose down orchestrator worker agent-stage2-lit 2>/dev/null || true
  docker compose up -d --build postgres redis migrate
  sleep 3

  docker compose up -d --build orchestrator worker agent-stage2-lit
  log_info "Waiting for services to be healthy..."
  sleep 10

  for service in orchestrator worker; do
    if ! docker compose ps "$service" | grep -q "Up"; then
      log_error "Service $service failed to start"
      docker compose logs --tail=50 "$service"
      ci_fail "Service $service failed to start"
    fi
  done

  log_info "Services started ✓"
else
  log_info "Skipping compose (targeting $BASE_URL)"
fi

#############################################
# 3. Call Stage 2 execute (full E2E path)
#############################################
WORKFLOW_ID="$({ uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())'; } 2>/dev/null)"
RESEARCH_QUESTION="Smoke test: effectiveness of systematic reviews in clinical decision support (E2E)"
log_info "Calling POST /api/workflow/stages/2/execute (workflow_id: $WORKFLOW_ID)..."

# requireAuth: with ALLOW_MOCK_AUTH=true no header needed; with auth required use Bearer (never echo token)
CURL_AUTH=()
if [[ -n "${WORKER_SERVICE_TOKEN:-}" ]]; then
  CURL_AUTH=(-H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}")
fi
EXECUTE_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/workflow/stages/2/execute" \
    -H "Content-Type: application/json" \
    "${CURL_AUTH[@]}" \
    -d "{
      \"workflow_id\": \"${WORKFLOW_ID}\",
      \"research_question\": \"${RESEARCH_QUESTION}\",
      \"mode\": \"DEMO\",
      \"risk_tier\": \"NON_SENSITIVE\",
      \"domain_id\": \"clinical\",
      \"inputs\": {
        \"query\": \"systematic review clinical decision support\",
        \"max_results\": 25,
        \"databases\": [\"pubmed\"],
        \"language\": \"en\",
        \"dedupe\": true,
        \"require_abstract\": true
      }
    }" \
    -w "\n%{http_code}" 2>&1)

EXEC_HTTP_CODE=$(echo "$EXECUTE_RESPONSE" | tail -n1)
EXEC_BODY=$(echo "$EXECUTE_RESPONSE" | sed '$d')

if [[ "$EXEC_HTTP_CODE" != "202" ]]; then
    log_error "Stage 2 execute failed with HTTP $EXEC_HTTP_CODE"
    echo "$EXEC_BODY" | jq . 2>/dev/null || echo "$EXEC_BODY"
    if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
      log_error "=== Orchestrator logs (last 50) ==="
      docker compose logs --tail=50 orchestrator
      log_error "=== Worker logs (last 50) ==="
      docker compose logs --tail=50 worker
    fi
    ci_fail "Stage 2 execute failed: HTTP $EXEC_HTTP_CODE"
fi

JOB_ID=$(echo "$EXEC_BODY" | jq -r '.job_id')
if [[ -z "$JOB_ID" || "$JOB_ID" == "null" ]]; then
    log_error "Response did not contain job_id"
    echo "$EXEC_BODY" | jq . 2>/dev/null || echo "$EXEC_BODY"
    ci_fail "Response did not contain job_id"
fi

log_info "Job queued (HTTP 202) ✓ job_id=$JOB_ID"

#############################################
# 4. Poll job status until completed/failed or timeout
#############################################
log_info "Polling job status (timeout ${SMOKE_TIMEOUT}s)..."

POLL_INTERVAL=5
ELAPSED=0
FINAL_STATUS=""

while [[ $ELAPSED -lt $SMOKE_TIMEOUT ]]; do
    STATUS_RESPONSE=$(curl -sS -w "\n%{http_code}" "${CURL_AUTH[@]}" "$BASE_URL/api/workflow/stages/2/jobs/${JOB_ID}/status" 2>&1)
    STATUS_HTTP=$(echo "$STATUS_RESPONSE" | tail -n1)
    STATUS_BODY=$(echo "$STATUS_RESPONSE" | sed '$d')

    if [[ "$STATUS_HTTP" != "200" ]]; then
        log_warn "Status returned HTTP $STATUS_HTTP (elapsed ${ELAPSED}s)"
        sleep "$POLL_INTERVAL"
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        continue
    fi

    JOB_STATE=$(echo "$STATUS_BODY" | jq -r '.status // empty')
    PROGRESS=$(echo "$STATUS_BODY" | jq -r '.progress // 0')

    if [[ "$JOB_STATE" == "completed" ]]; then
        FINAL_STATUS="completed"
        log_info "Job completed ✓ (progress: $PROGRESS)"
        break
    fi
    if [[ "$JOB_STATE" == "failed" ]]; then
        FINAL_STATUS="failed"
        log_error "Job failed (job_id: $JOB_ID)"
        echo "$STATUS_BODY" | jq . 2>/dev/null || echo "$STATUS_BODY"
        if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
          log_error "=== Orchestrator logs (last 50) ==="
          docker compose logs --tail=50 orchestrator
          log_error "=== Worker logs (last 50) ==="
          docker compose logs --tail=50 worker
        fi
        ci_fail "Job failed: job_id=$JOB_ID"
    fi

    printf "."
    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done
echo ""

if [[ -z "$FINAL_STATUS" ]]; then
    log_error "Timeout (${SMOKE_TIMEOUT}s) waiting for job $JOB_ID"
    if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
      log_error "=== Orchestrator logs (last 50) ==="
      docker compose logs --tail=50 orchestrator
      log_error "=== Worker logs (last 50) ==="
      docker compose logs --tail=50 worker
    fi
    ci_fail "Timeout (${SMOKE_TIMEOUT}s) waiting for job $JOB_ID"
fi

#############################################
# 5. Show relevant logs (local compose only)
#############################################
if [[ $RUN_LOCAL_COMPOSE -eq 1 ]]; then
  log_info "=== Orchestrator logs (last 30 lines) ==="
  docker compose logs --tail=30 orchestrator
  log_info "=== Worker logs (last 30 lines) ==="
  docker compose logs --tail=30 worker
fi

#############################################
# 6. Summary
#############################################
echo ""
log_info "========================================="
log_info "Stage 2 E2E smoke test PASSED"
log_info "  workflow_id: $WORKFLOW_ID"
log_info "  job_id:      $JOB_ID"
log_info "  status:      $FINAL_STATUS"
log_info "========================================="
echo ""
echo "Quick commands:"
echo "  View full logs:  docker compose logs -f orchestrator worker"
echo "  Check DB:        docker compose exec postgres psql -U postgres -d researchflow"
echo "  Restart:         docker compose restart orchestrator worker"
