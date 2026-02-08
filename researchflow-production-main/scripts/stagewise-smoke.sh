#!/usr/bin/env bash
# Stagewise execution + accept AI suggestions — server-local smoke script
# All endpoints cited from: services/orchestrator/routes.ts and route files.
# Health: index.ts app.use("/api", healthRouter) + src/routes/health.ts router.get("/health", ...) → GET /api/health

set -e
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
CURL_OPTS=( -sS -w "\n%{http_code}" )
AUTH_HEADER="${AUTH_HEADER:-}"

fail() {
  echo "FAIL: $1" >&2
  exit 1
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
      fail "Expected HTTP $expect_code, got $LAST_CODE"
    fi
  else
    if [ "${LAST_CODE:0:1}" != "2" ]; then
      echo "Request: $method $url" >&2
      print_last
      fail "Unexpected HTTP $LAST_CODE"
    fi
  fi
  return 0
}

echo "Using ORCHESTRATOR_URL=$ORCHESTRATOR_URL"

# --- 1. Health (cited: index.ts app.use("/api", healthRouter); health.ts router.get("/health", ...))
echo "[1] GET /api/health"
req GET "/api/health"
echo "Health OK: $LAST_BODY"

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
  fail "AUTH_HEADER required for Stage 2 execute (requireAuth). Example: AUTH_HEADER=\"Authorization: Bearer <token>\""
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
echo "[5] GET /api/ai/feedback/pending/list"
if [ -z "$AUTH_HEADER" ]; then
  echo "Skipping (AUTH_HEADER required for ADMIN); set AUTH_HEADER to test."
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
    echo "Pending list response: $_pending_code (may need ADMIN role)"
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
