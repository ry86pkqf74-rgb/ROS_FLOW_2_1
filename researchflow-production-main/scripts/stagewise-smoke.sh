#!/usr/bin/env bash
# Stagewise execution + accept AI suggestions — server-local smoke script
# All endpoints cited from: services/orchestrator/routes.ts and route files.
# Health: index.ts app.use("/api", healthRouter) + src/routes/health.ts router.get("/health", ...) → GET /api/health

set -e
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
CURL_OPTS=( -sS -w "\n%{http_code}" )
AUTH_HEADER="${AUTH_HEADER:-}"
# Skip admin-only checks (steps 5–6: pending feedback list + review). Use for staging when no ADMIN token.
SKIP_ADMIN_CHECKS="${SKIP_ADMIN_CHECKS:-0}"
# When set to "true", mint a dev token via POST /api/dev-auth/login (requires server ENABLE_DEV_AUTH=true).
DEV_AUTH="${DEV_AUTH:-false}"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

# Emit clearer auth errors (401/403)
auth_error() {
  local code="$1" url="$2"
  if [ "$code" = "401" ]; then
    echo "401 Unauthorized: missing or invalid token for $url. Set AUTH_HEADER or use DEV_AUTH=true (if server has ENABLE_DEV_AUTH=true)." >&2
  elif [ "$code" = "403" ]; then
    echo "403 Forbidden: insufficient role for $url (e.g. ADMIN required). Set SKIP_ADMIN_CHECKS=1 to skip admin-only steps." >&2
  fi
}

# Optional: print last response body (assumes body and code were stored)
print_last() {
  if [ -n "$LAST_BODY" ]; then
    echo "Response body: $LAST_BODY" >&2
  fi
  if [ -n "$LAST_CODE" ]; then
    echo "HTTP status: $LAST_CODE" >&2
  fi
}

# Curl helper: req METHOD PATH [EXPECT_CODE] [BODY]
# e.g. req GET /api/health
#      req POST /api/path 202 '{"key":"value"}'
req() {
  local method="$1" path="$2" expect_code="" body=""
  shift 2
  if [ $# -ge 1 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
    expect_code="$1"
    shift
  fi
  if [ $# -ge 1 ]; then
    body="$1"
  fi
  local url="${ORCHESTRATOR_URL}${path}"
  local extra=()
  if [ -n "$AUTH_HEADER" ]; then
    extra+=( -H "$AUTH_HEADER" )
  fi
  local out
  if [ -n "$body" ]; then
    out=$(curl "${CURL_OPTS[@]}" -X "$method" "${extra[@]}" -H "Content-Type: application/json" -d "$body" "$url")
  else
    out=$(curl "${CURL_OPTS[@]}" -X "$method" "${extra[@]}" "$url")
  fi
  LAST_BODY=$(echo "$out" | head -n -1)
  LAST_CODE=$(echo "$out" | tail -n 1)
  if [ -n "$expect_code" ]; then
    if [ "$LAST_CODE" != "$expect_code" ]; then
      echo "Request: $method $url" >&2
      print_last
      auth_error "$LAST_CODE" "$url"
      fail "Expected HTTP $expect_code, got $LAST_CODE"
    fi
  else
    if [ "${LAST_CODE:0:1}" != "2" ]; then
      echo "Request: $method $url" >&2
      print_last
      auth_error "$LAST_CODE" "$url"
      fail "Unexpected HTTP $LAST_CODE"
    fi
  fi
  return 0
}

echo "Using ORCHESTRATOR_URL=$ORCHESTRATOR_URL"

# --- 0. Optional: auto-mint dev token when DEV_AUTH=true and AUTH_HEADER unset (server must have ENABLE_DEV_AUTH=true)
if [ "$DEV_AUTH" = "true" ] && [ -z "$AUTH_HEADER" ]; then
  echo "[0] POST /api/dev-auth/login (DEV_AUTH=true)"
  _login_out=$(curl "${CURL_OPTS[@]}" -X POST -H "Content-Type: application/json" -H "X-Dev-User-Id: stagewise-smoke-dev" "${ORCHESTRATOR_URL}/api/dev-auth/login")
  _login_body=$(echo "$_login_out" | head -n -1)
  _login_code=$(echo "$_login_out" | tail -n 1)
  if [ "$_login_code" = "200" ]; then
    _token=$(echo "$_login_body" | sed -n 's/.*"accessToken"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    if [ -n "$_token" ]; then
      AUTH_HEADER="Authorization: Bearer $_token"
      echo "Dev token minted; AUTH_HEADER set."
    else
      echo "Warning: dev login 200 but no accessToken in response" >&2
    fi
  else
    echo "Warning: dev-auth login returned $_login_code (is ENABLE_DEV_AUTH=true on server?). Proceeding without token." >&2
  fi
fi

# --- 1. Health (cited: index.ts app.use("/api", healthRouter); health.ts router.get("/health", ...))
echo "[1] GET /api/health"
req GET "/api/health"
echo "Health OK: $LAST_BODY"

# --- 1.5. Assert WORKER_SERVICE_TOKEN is set (required for stage 2 internal dispatch auth)
echo "[1.5] Checking WORKER_SERVICE_TOKEN (required for stage 2 dispatch)"
WORKER_TOKEN_VERIFIED=false
if [ -f .env ] && grep -qE '^WORKER_SERVICE_TOKEN=.+' .env 2>/dev/null; then
  WORKER_TOKEN_VERIFIED=true
fi
if [ "$WORKER_TOKEN_VERIFIED" = false ] && command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  TOKEN_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${WORKER_SERVICE_TOKEN:+SET}' 2>/dev/null || echo "")
  if [ "$TOKEN_CHECK" = "SET" ]; then
    WORKER_TOKEN_VERIFIED=true
  fi
fi
if [ "$WORKER_TOKEN_VERIFIED" = true ]; then
  echo "✓ WORKER_SERVICE_TOKEN is configured"
else
  echo "✗ WORKER_SERVICE_TOKEN is NOT set or could not be verified." >&2
  echo "" >&2
  echo "Stage 2 execution requires WORKER_SERVICE_TOKEN for internal dispatch (POST /api/ai/router/dispatch)." >&2
  echo "Remediation:" >&2
  echo "  1. Generate token: openssl rand -hex 32" >&2
  echo "  2. Add to .env: WORKER_SERVICE_TOKEN=<generated-token>" >&2
  echo "  3. Recreate orchestrator: docker compose up -d --force-recreate orchestrator" >&2
  echo "" >&2
  echo "Run this script from the server deploy directory (e.g. /opt/researchflow/.../researchflow-production-main) so .env or orchestrator env can be checked." >&2
  fail "WORKER_SERVICE_TOKEN not configured - stage execution will fail with 403"
fi

# --- 2. Approve AI for stage 2 (cited: routes.ts app.use("/api/workflow", workflowStagesRouter); workflow-stages.ts router.post('/stages/:stageId/approve-ai', ...))
# No requireAuth on this route; optionalAuth sets user. AUTH_HEADER recommended for session.
echo "[2] POST /api/workflow/stages/2/approve-ai"
if [ -z "$AUTH_HEADER" ]; then
  echo "Warning: AUTH_HEADER not set; approve-ai may use anonymous session"
fi
_approve_out=$(curl "${CURL_OPTS[@]}" -X POST ${AUTH_HEADER:+-H "$AUTH_HEADER"} -H "Content-Type: application/json" -d '{}' "${ORCHESTRATOR_URL}/api/workflow/stages/2/approve-ai")
_approve_body=$(echo "$_approve_out" | head -n -1)
_approve_code=$(echo "$_approve_out" | tail -n 1)
if [ "${_approve_code:0:1}" = "2" ]; then
  echo "Approve AI OK"
else
  echo "Approve AI response (may be acceptable): $_approve_code — $_approve_body"
fi

# --- 3. Execute Stage 2 (cited: routes.ts app.use("/api/workflow/stages", workflowStagesExecuteRouter); workflow/stages.ts router.post('/2/execute', requireAuth, ...))
# Stage2ExecuteSchema: workflow_id (uuid), research_question (min 10), mode, risk_tier, domain_id, inputs optional
echo "[3] POST /api/workflow/stages/2/execute"
if [ -z "$AUTH_HEADER" ]; then
  fail "AUTH_HEADER required for Stage 2 execute (requireAuth). Set AUTH_HEADER or DEV_AUTH=true (with server ENABLE_DEV_AUTH=true)."
fi
EXEC_BODY='{"workflow_id":"00000000-0000-0000-0000-000000000001","research_question":"Do GLP-1 agonists improve cardiovascular outcomes in type 2 diabetes?","mode":"DEMO","risk_tier":"NON_SENSITIVE","domain_id":"clinical"}'
req POST "/api/workflow/stages/2/execute" 202 "$EXEC_BODY"
JOB_ID=$(echo "$LAST_BODY" | sed -n 's/.*"job_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
if [ -z "$JOB_ID" ]; then
  echo "Response: $LAST_BODY" >&2
  fail "Could not parse job_id from execute response"
fi
echo "Job queued: job_id=$JOB_ID"

# --- 4. Poll job status until completed/failed or timeout (cited: workflow/stages.ts router.get('/:stage/jobs/:job_id/status', requireAuth, ...))
echo "[4] Polling GET /api/workflow/stages/2/jobs/$JOB_ID/status"
POLL_MAX=60
POLL_INTERVAL=3
for i in $(seq 1 "$POLL_MAX"); do
  req GET "/api/workflow/stages/2/jobs/$JOB_ID/status"
  STATUS=$(echo "$LAST_BODY" | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
  echo "  Poll $i: status=$STATUS"
  case "$STATUS" in
    completed) echo "Job completed."; break ;;
    failed)     echo "Job failed: $LAST_BODY"; fail "Stage 2 job failed" ;;
    *)         [ "$i" -eq "$POLL_MAX" ] && fail "Timeout waiting for job completion"; sleep "$POLL_INTERVAL" ;;
  esac
done

# --- 5. Pending AI feedback list (cited: ai-feedback.ts router.get('/pending/list', requireRole('ADMIN'), ...))
# Optional: set SKIP_ADMIN_CHECKS=1 to skip steps 5–6 when no ADMIN token is available.
echo "[5] GET /api/ai/feedback/pending/list"
if [ "$SKIP_ADMIN_CHECKS" = "1" ] || [ "$SKIP_ADMIN_CHECKS" = "true" ]; then
  echo "Skipping (SKIP_ADMIN_CHECKS=1)."
elif [ -z "$AUTH_HEADER" ]; then
  echo "Skipping (AUTH_HEADER required for ADMIN). Set AUTH_HEADER or DEV_AUTH=true, or SKIP_ADMIN_CHECKS=1 to skip."
else
  _pending_out=$(curl "${CURL_OPTS[@]}" -X GET -H "$AUTH_HEADER" "${ORCHESTRATOR_URL}/api/ai/feedback/pending/list")
  _pending_body=$(echo "$_pending_out" | head -n -1)
  _pending_code=$(echo "$_pending_out" | tail -n 1)
  if [ "${_pending_code:0:1}" = "2" ]; then
    PENDING_IDS=$(echo "$_pending_body" | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
    echo "Pending feedback (first id): $PENDING_IDS"
    # --- 6. Submit review (cited: ai-feedback.ts router.put('/:id/review', requireRole('ADMIN'), ...)); body: isUsefulForTraining, reviewNotes optional
    if [ -n "$PENDING_IDS" ]; then
      echo "[6] PUT /api/ai/feedback/$PENDING_IDS/review"
      req PUT "/api/ai/feedback/$PENDING_IDS/review" '{"isUsefulForTraining":true}'
      echo "Review submitted."
    else
      echo "[6] No pending feedback to review."
    fi
  else
    auth_error "$_pending_code" "/api/ai/feedback/pending/list"
    echo "Pending list response: $_pending_code — $_pending_body"
  fi
fi

# --- 7. Persist/accept output into run step (cited: hub/workflow-runs.ts router.patch('/:runId/steps/:stepDbId', ...); UpdateStepSchema: status, outputs, errorMessage)
# Requires an existing run and step (runId, stepDbId). Skip if not available; script does not create runs.
if [ -n "${RUN_ID:-}" ] && [ -n "${STEP_DB_ID:-}" ]; then
  echo "[7] PATCH /api/hub/workflow-runs/$RUN_ID/steps/$STEP_DB_ID"
  req PATCH "/api/hub/workflow-runs/$RUN_ID/steps/$STEP_DB_ID" '{"status":"completed","outputs":{"accepted":true}}'
  echo "Step output updated."
else
  echo "[7] Skip PATCH workflow-runs step (set RUN_ID and STEP_DB_ID to test)"
fi

echo "Stagewise smoke completed successfully."
