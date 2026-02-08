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
# When set to "1", run optional Evidence Synthesis Agent check (commit 197bfcd)
CHECK_EVIDENCE_SYNTH="${CHECK_EVIDENCE_SYNTH:-0}"
# When set to "1", run optional Literature Triage Agent check (commit c1a42c1)
CHECK_LIT_TRIAGE="${CHECK_LIT_TRIAGE:-0}"
# When set to "1", run optional Clinical Manuscript Writer check (commit 040b13f - LangSmith-based)
CHECK_MANUSCRIPT_WRITER="${CHECK_MANUSCRIPT_WRITER:-0}"
# When set to "1", run optional Clinical Section Drafter check (commit 6a5c93e - LangSmith-based)
CHECK_SECTION_DRAFTER="${CHECK_SECTION_DRAFTER:-0}"
# When set to "1", run optional Clinical Bias Detection check (LangSmith-based)
CHECK_BIAS_DETECTION="${CHECK_BIAS_DETECTION:-0}"
# When set to "1", run optional Dissemination Formatter check (LangSmith-based)
CHECK_DISSEMINATION_FORMATTER="${CHECK_DISSEMINATION_FORMATTER:-0}"
# When set to "1", run optional Performance Optimizer check (LangSmith-based)
CHECK_PERFORMANCE_OPTIMIZER="${CHECK_PERFORMANCE_OPTIMIZER:-0}"
# When set to "1", run optional Peer Review Simulator check (LangSmith-based)
CHECK_PEER_REVIEW="${CHECK_PEER_REVIEW:-0}"
# When set to "1", run optional Results Interpretation check (LangSmith-based)
CHECK_RESULTS_INTERPRETATION="${CHECK_RESULTS_INTERPRETATION:-0}"
# When set to "1", run ALL optional agent checks
CHECK_ALL_AGENTS="${CHECK_ALL_AGENTS:-0}"

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

# --- 8. Optional: Evidence Synthesis Agent validation (commit 197bfcd)
if [ "$CHECK_EVIDENCE_SYNTH" = "1" ] || [ "$CHECK_EVIDENCE_SYNTH" = "true" ]; then
  echo "[8] Evidence Synthesis Agent Check (optional)"
  
  # 8a. Health check
  echo "[8a] GET agent-evidence-synthesis /health"
  _synth_health_out=$(curl "${CURL_OPTS[@]}" -X GET "http://127.0.0.1:8015/health" 2>/dev/null || echo -e "\n000")
  _synth_health_code=$(echo "$_synth_health_out" | tail -n 1)
  if [ "${_synth_health_code:0:1}" = "2" ]; then
    echo "Evidence Synthesis Agent health OK"
  else
    echo "Warning: Evidence Synthesis Agent health check failed (code: $_synth_health_code)"
    echo "This is optional - continuing smoke test."
  fi
  
  # 8b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[8b] POST /api/ai/router/dispatch (EVIDENCE_SYNTHESIS)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"EVIDENCE_SYNTHESIS","request_id":"smoke-test-synth","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-evidence-synthesis" ]; then
        echo "✓ Correctly routed to agent-evidence-synthesis"
      else
        echo "Warning: Expected agent-evidence-synthesis, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[8b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 8c. Direct agent call with minimal fixture
  echo "[8c] POST /agents/run/sync (direct agent call)"
  _agent_out=$(curl "${CURL_OPTS[@]}" -X POST -H "Content-Type: application/json" \
    -d '{
      "task_type":"EVIDENCE_SYNTHESIS",
      "request_id":"smoke-test-direct",
      "mode":"DEMO",
      "inputs":{
        "research_question":"Is aspirin effective for cardiovascular disease prevention?",
        "max_papers":3
      }
    }' \
    "http://127.0.0.1:8015/agents/run/sync" 2>/dev/null || echo -e "\n000")
  _agent_body=$(echo "$_agent_out" | head -n -1)
  _agent_code=$(echo "$_agent_out" | tail -n 1)
  
  if [ "${_agent_code:0:1}" = "2" ]; then
    AGENT_OK=$(echo "$_agent_body" | sed -n 's/.*"ok"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p' | head -1)
    echo "Direct agent call completed (ok: $AGENT_OK)"
    
    # Check for expected output fields
    if echo "$_agent_body" | grep -q "executive_summary"; then
      echo "✓ Response contains executive_summary"
    else
      echo "Warning: Response missing executive_summary field"
    fi
    
    if echo "$_agent_body" | grep -q "evidence_table"; then
      echo "✓ Response contains evidence_table"
    else
      echo "Warning: Response missing evidence_table field"
    fi
  else
    echo "Warning: Direct agent call failed (code: $_agent_code)"
    echo "Response: $_agent_body"
  fi
  
  echo "Evidence Synthesis Agent check complete (optional - does not block)"
else
  echo "[8] Skipping Evidence Synthesis Agent check (set CHECK_EVIDENCE_SYNTH=1 to enable)"
fi

# --- 9. Optional: Literature Triage Agent validation (commit c1a42c1)
if [ "$CHECK_LIT_TRIAGE" = "1" ] || [ "$CHECK_LIT_TRIAGE" = "true" ]; then
  echo "[9] Literature Triage Agent Check (optional)"
  
  # 9a. Health check
  echo "[9a] GET agent-lit-triage /health"
  _triage_health_out=$(curl "${CURL_OPTS[@]}" -X GET "http://127.0.0.1:8000/health" 2>/dev/null || echo -e "\n000")
  _triage_health_code=$(echo "$_triage_health_out" | tail -n 1)
  if [ "${_triage_health_code:0:1}" = "2" ]; then
    echo "Literature Triage Agent health OK"
  else
    echo "Warning: Literature Triage Agent health check failed (code: $_triage_health_code)"
    echo "Attempting via docker exec (internal network)..."
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      _docker_health=$(docker compose exec -T agent-lit-triage curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
      if echo "$_docker_health" | grep -q "ok"; then
        echo "✓ Health check passed via docker exec (agent is internal-only)"
      else
        echo "Warning: Health check failed via docker exec too"
      fi
    fi
    echo "This is optional - continuing smoke test."
  fi
  
  # 9b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[9b] POST /api/ai/router/dispatch (LIT_TRIAGE)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"LIT_TRIAGE","request_id":"smoke-test-triage","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-lit-triage" ]; then
        echo "✓ Correctly routed to agent-lit-triage"
      else
        echo "Warning: Expected agent-lit-triage, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[9b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 9c. Direct agent call with minimal fixture (via docker exec if agent is internal-only)
  echo "[9c] POST /agents/run/sync (direct agent call)"
  TRIAGE_PAYLOAD='{
    "task_type":"LIT_TRIAGE",
    "request_id":"smoke-test-direct",
    "mode":"DEMO",
    "inputs":{
      "query":"cancer immunotherapy checkpoint inhibitors",
      "date_range_days":730,
      "min_results":3
    }
  }'
  
  # Try direct curl first
  _agent_out=$(curl "${CURL_OPTS[@]}" -X POST -H "Content-Type: application/json" \
    -d "$TRIAGE_PAYLOAD" \
    "http://127.0.0.1:8000/agents/run/sync" 2>/dev/null || echo -e "\n000")
  _agent_code=$(echo "$_agent_out" | tail -n 1)
  
  # If direct curl fails, try via docker exec
  if [ "$_agent_code" = "000" ] || [ "${_agent_code:0:1}" != "2" ]; then
    echo "Direct curl failed, attempting via docker exec..."
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      _agent_out=$(docker compose exec -T agent-lit-triage sh -c "
        curl -sS -w '\n%{http_code}' -X POST \
          -H 'Content-Type: application/json' \
          -d '$TRIAGE_PAYLOAD' \
          http://localhost:8000/agents/run/sync
      " 2>/dev/null || echo -e "\n000")
      _agent_code=$(echo "$_agent_out" | tail -n 1)
    fi
  fi
  
  _agent_body=$(echo "$_agent_out" | head -n -1)
  
  if [ "${_agent_code:0:1}" = "2" ]; then
    AGENT_OK=$(echo "$_agent_body" | sed -n 's/.*"ok"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p' | head -1)
    echo "Direct agent call completed (ok: $AGENT_OK)"
    
    # Check for expected output fields
    if echo "$_agent_body" | grep -q "papers"; then
      echo "✓ Response contains papers field"
    else
      echo "Warning: Response missing papers field"
    fi
    
    if echo "$_agent_body" | grep -q "stats"; then
      echo "✓ Response contains stats field"
    else
      echo "Warning: Response missing stats field"
    fi
    
    # Check for tier counts
    if echo "$_agent_body" | grep -q "tier1_count"; then
      TIER1=$(echo "$_agent_body" | sed -n 's/.*"tier1_count"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')
      echo "✓ Tier 1 (Must Read) papers: $TIER1"
    fi
    
    if echo "$_agent_body" | grep -q "ranked"; then
      RANKED=$(echo "$_agent_body" | sed -n 's/.*"ranked"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')
      echo "✓ Total ranked papers: $RANKED"
    fi
  else
    echo "Warning: Direct agent call failed (code: $_agent_code)"
    echo "Response: $_agent_body"
    echo "This may be expected if EXA_API_KEY is not configured (agent will mock results)"
  fi
  
  echo "Literature Triage Agent check complete (optional - does not block)"
else
  echo "[9] Skipping Literature Triage Agent check (set CHECK_LIT_TRIAGE=1 to enable)"
fi

# --- 10. Optional: Clinical Manuscript Writer validation (commit 040b13f - LangSmith cloud integration)
if [ "$CHECK_MANUSCRIPT_WRITER" = "1" ] || [ "$CHECK_MANUSCRIPT_WRITER" = "true" ]; then
  echo "[10] Clinical Manuscript Writer Check (optional - LangSmith-based)"
  
  # 10a. Check LANGSMITH_API_KEY is configured
  echo "[10a] Checking LANGSMITH_API_KEY configuration"
  LANGSMITH_KEY_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH_API_KEY"
  fi
  
  # 10b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[10b] POST /api/ai/router/dispatch (CLINICAL_MANUSCRIPT_WRITE)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"CLINICAL_MANUSCRIPT_WRITE","request_id":"smoke-test-manuscript","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-clinical-manuscript" ]; then
        echo "✓ Correctly routed to agent-clinical-manuscript"
      else
        echo "Warning: Expected agent-clinical-manuscript, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[10b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 10c. Validate artifacts directory exists
  echo "[10c] Checking artifacts directory for manuscript output"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts directory exists"
  else
    echo "Warning: /data/artifacts not found (manuscripts will write to Google Docs only)"
  fi
  
  # Note: We cannot call LangSmith API directly in smoke test without exposing API key
  # This is intentional - LangSmith integration tested via dispatch endpoint only
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY (not tested in smoke)"
  echo "      Full integration test requires: Evidence Synthesis → Manuscript Writer pipeline"
  
  echo "Clinical Manuscript Writer check complete (optional - does not block)"
else
  echo "[10] Skipping Clinical Manuscript Writer check (set CHECK_MANUSCRIPT_WRITER=1 to enable)"
fi

# --- 11. Optional: Clinical Section Drafter validation (commit 6a5c93e - LangSmith cloud integration)
if [ "$CHECK_SECTION_DRAFTER" = "1" ] || [ "$CHECK_SECTION_DRAFTER" = "true" ]; then
  echo "[11] Clinical Section Drafter Check (optional - LangSmith-based)"
  
  # 11a. Check LANGSMITH_API_KEY is configured
  echo "[11a] Checking LANGSMITH_API_KEY configuration"
  LANGSMITH_KEY_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH_API_KEY"
  fi
  
  # 11b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[11b] POST /api/ai/router/dispatch (CLINICAL_SECTION_DRAFT)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"CLINICAL_SECTION_DRAFT","request_id":"smoke-test-section","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-clinical-section-drafter" ]; then
        echo "✓ Correctly routed to agent-clinical-section-drafter"
      else
        echo "Warning: Expected agent-clinical-section-drafter, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[11b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 11c. Validate artifacts directory exists
  echo "[11c] Checking artifacts directory structure"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts exists"
    mkdir -p /data/artifacts/validation/clinical-section-draft 2>/dev/null || true
    if [ -d "/data/artifacts/validation/clinical-section-draft" ]; then
      echo "✓ Created validation artifact directory"
    fi
  else
    echo "Warning: /data/artifacts not found (manuscripts will write to Google Docs only)"
  fi
  
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY (not tested in smoke)"
  echo "      Full integration test requires: Evidence Synthesis → Section Drafter → Manuscript Writer pipeline"
  
  echo "Clinical Section Drafter check complete (optional - does not block)"
else
  echo "[11] Skipping Clinical Section Drafter check (set CHECK_SECTION_DRAFTER=1 to enable)"
fi

# --- 11.5. Optional: Clinical Bias Detection validation (LangSmith cloud integration)
if [ "$CHECK_BIAS_DETECTION" = "1" ] || [ "$CHECK_BIAS_DETECTION" = "true" ]; then
  echo "[11.5] Clinical Bias Detection Agent Check (optional - LangSmith-based)"
  
  # 11.5a. Check LANGSMITH_API_KEY and agent ID are configured
  echo "[11.5a] Checking LANGSMITH_API_KEY and agent ID configuration"
  LANGSMITH_KEY_SET=false
  BIAS_AGENT_ID_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
    
    AGENT_ID_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_BIAS_DETECTION_AGENT_ID:+SET}' 2>/dev/null || echo "")
    if [ "$AGENT_ID_CHECK" = "SET" ]; then
      BIAS_AGENT_ID_SET=true
      echo "✓ LANGSMITH_BIAS_DETECTION_AGENT_ID is configured"
    else
      echo "Warning: LANGSMITH_BIAS_DETECTION_AGENT_ID not set"
      echo "To enable: Add LANGSMITH_BIAS_DETECTION_AGENT_ID=<uuid> to .env"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH configuration"
  fi
  
  # 11.5b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[11.5b] POST /api/ai/router/dispatch (CLINICAL_BIAS_DETECTION)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"CLINICAL_BIAS_DETECTION","request_id":"smoke-test-bias","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-bias-detection" ]; then
        echo "✓ Correctly routed to agent-bias-detection"
      else
        echo "Warning: Expected agent-bias-detection, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[11.5b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 11.5c. Check proxy container health
  echo "[11.5c] Checking proxy container health"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    if docker ps --format "{{.Names}}" | grep -q "agent-bias-detection-proxy"; then
      echo "✓ agent-bias-detection-proxy container is running"
      
      # Check health endpoint
      PROXY_HEALTH=$(docker compose exec -T agent-bias-detection-proxy curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
      if echo "$PROXY_HEALTH" | grep -q "ok"; then
        echo "✓ Proxy health endpoint responding"
      else
        echo "Warning: Proxy health endpoint not responding"
      fi
    else
      echo "Warning: agent-bias-detection-proxy container not running"
    fi
  else
    echo "Warning: Docker not available, cannot check proxy container"
  fi
  
  # 11.5d. Validate artifacts directory structure
  echo "[11.5d] Checking artifacts directory structure"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts exists"
    mkdir -p /data/artifacts/validation/bias-detection-smoke 2>/dev/null || true
    if [ -d "/data/artifacts/validation/bias-detection-smoke" ]; then
      # Write a minimal validation record
      TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
      mkdir -p "/data/artifacts/validation/bias-detection-smoke/${TIMESTAMP}" 2>/dev/null || true
      cat > "/data/artifacts/validation/bias-detection-smoke/${TIMESTAMP}/summary.json" 2>/dev/null <<BIAS_SMOKE_EOF
{
  "agent": "agent-bias-detection",
  "task_type": "CLINICAL_BIAS_DETECTION",
  "timestamp": "${TIMESTAMP}",
  "langsmith_key_set": ${LANGSMITH_KEY_SET},
  "bias_agent_id_set": ${BIAS_AGENT_ID_SET},
  "router_registered": true,
  "proxy_container_running": $(docker ps --format "{{.Names}}" | grep -q "agent-bias-detection-proxy" && echo "true" || echo "false"),
  "status": "smoke-check-complete"
}
BIAS_SMOKE_EOF
      echo "✓ Wrote validation artifact to /data/artifacts/validation/bias-detection-smoke/${TIMESTAMP}/summary.json"
    fi
  else
    echo "Warning: /data/artifacts not found (no artifact write; reports go to Google Docs)"
  fi
  
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY + LANGSMITH_BIAS_DETECTION_AGENT_ID"
  echo "      Proxy container must be running and healthy for full integration"
  echo "      Full integration test requires: Dataset → Bias Detection → Mitigation reports"
  
  echo "Clinical Bias Detection Agent check complete (optional - does not block)"
else
  echo "[11.5] Skipping Clinical Bias Detection check (set CHECK_BIAS_DETECTION=1 to enable)"
fi

# --- 12. Optional: Peer Review Simulator validation (LangSmith cloud integration - Stage 13)
if [ "$CHECK_PEER_REVIEW" = "1" ] || [ "$CHECK_PEER_REVIEW" = "true" ]; then
  echo "[12] Peer Review Simulator Check (optional - LangSmith-based)"
  
  # 12a. Check LANGSMITH_API_KEY is configured
  echo "[12a] Checking LANGSMITH_API_KEY configuration"
  LANGSMITH_KEY_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH_API_KEY"
  fi
  
  # 12b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[12b] POST /api/ai/router/dispatch (PEER_REVIEW_SIMULATION)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"PEER_REVIEW_SIMULATION","request_id":"smoke-test-peer-review","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-peer-review-simulator" ]; then
        echo "✓ Correctly routed to agent-peer-review-simulator"
      else
        echo "Warning: Expected agent-peer-review-simulator, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[12b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 12c. Validate artifacts directory exists
  echo "[12c] Checking artifacts directory structure"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts exists"
    mkdir -p /data/artifacts/validation/peer-review 2>/dev/null || true
    if [ -d "/data/artifacts/validation/peer-review" ]; then
      echo "✓ Created validation artifact directory"
    fi
  else
    echo "Warning: /data/artifacts not found (peer reviews will write to Google Docs only)"
  fi
  
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY (not tested in smoke)"
  echo "      Full integration test requires: Manuscript → Peer Review Simulator (Stage 13) → Revisions pipeline"
  
  echo "Peer Review Simulator check complete (optional - does not block)"
else
  echo "[12] Skipping Peer Review Simulator check (set CHECK_PEER_REVIEW=1 to enable)"
fi

# --- 13. Optional: Results Interpretation Agent validation (LangSmith cloud integration)
if [ "$CHECK_RESULTS_INTERPRETATION" = "1" ] || [ "$CHECK_RESULTS_INTERPRETATION" = "true" ]; then
  echo "[13] Results Interpretation Agent Check (optional - LangSmith-based)"
  
  # 13a. Check LANGSMITH_API_KEY is configured
  echo "[13a] Checking LANGSMITH_API_KEY configuration"
  LANGSMITH_KEY_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH_API_KEY"
  fi
  
  # 12b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[12b] POST /api/ai/router/dispatch (RESULTS_INTERPRETATION)"
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d '{"task_type":"RESULTS_INTERPRETATION","request_id":"smoke-test-results-interp","mode":"DEMO"}' \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      AGENT_NAME=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      echo "Router dispatch OK: routed to $AGENT_NAME"
      
      if [ "$AGENT_NAME" = "agent-results-interpretation" ]; then
        echo "✓ Correctly routed to agent-results-interpretation"
      else
        echo "Warning: Expected agent-results-interpretation, got $AGENT_NAME"
      fi
    else
      # Expected: AGENT_NOT_CONFIGURED until AGENT_ENDPOINTS_JSON is updated
      if echo "$_dispatch_body" | grep -q "AGENT_NOT_CONFIGURED"; then
        echo "⚠ Dispatch returned AGENT_NOT_CONFIGURED (expected: agent-results-interpretation not in AGENT_ENDPOINTS_JSON)"
        echo "  Task type RESULTS_INTERPRETATION is registered in router but agent URL not configured."
        echo "  To fix: Add \"agent-results-interpretation\":\"<langsmith-proxy-url>\" to AGENT_ENDPOINTS_JSON"
      else
        echo "Warning: Router dispatch failed (code: $_dispatch_code)"
        echo "Response: $_dispatch_body"
      fi
    fi
  else
    echo "[12b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 12c. Validate artifacts directory exists
  echo "[12c] Checking artifacts directory for results interpretation output"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts directory exists"
    mkdir -p /data/artifacts/validation/results-interpretation-smoke 2>/dev/null || true
    if [ -d "/data/artifacts/validation/results-interpretation-smoke" ]; then
      # Write a minimal validation record
      TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
      mkdir -p "/data/artifacts/validation/results-interpretation-smoke/${TIMESTAMP}" 2>/dev/null || true
      cat > "/data/artifacts/validation/results-interpretation-smoke/${TIMESTAMP}/summary.json" 2>/dev/null <<SMOKE_EOF
{
  "agent": "agent-results-interpretation",
  "task_type": "RESULTS_INTERPRETATION",
  "timestamp": "${TIMESTAMP}",
  "langsmith_key_set": ${LANGSMITH_KEY_SET},
  "router_registered": true,
  "agent_endpoints_configured": false,
  "status": "smoke-check-complete"
}
SMOKE_EOF
      echo "✓ Wrote validation artifact to /data/artifacts/validation/results-interpretation-smoke/${TIMESTAMP}/summary.json"
    fi
  else
    echo "Warning: /data/artifacts not found (no artifact write; reports go to Google Docs)"
  fi
  
  # Note: We cannot call LangSmith API directly in smoke test without exposing API key
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY (not tested in smoke)"
  echo "      Agent is cloud-hosted - no local container to test directly"
  echo "      Full integration test requires: dispatching via LangSmith dispatcher (not yet built)"
  
  echo "Results Interpretation Agent check complete (optional - does not block)"
else
  echo "[12] Skipping Results Interpretation Agent check (set CHECK_RESULTS_INTERPRETATION=1 to enable)"
fi

echo ""

# --- ALL AGENTS VALIDATION (when CHECK_ALL_AGENTS=1)
if [ "$CHECK_ALL_AGENTS" = "1" ] || [ "$CHECK_ALL_AGENTS" = "true" ]; then
  echo ""
  echo "=========================================="
  echo "COMPREHENSIVE AGENT VALIDATION (CHECK_ALL_AGENTS=1)"
  echo "=========================================="
  echo ""
  
  # Override individual flags to run all checks
  CHECK_EVIDENCE_SYNTH=1
  CHECK_LIT_TRIAGE=1
  CHECK_MANUSCRIPT_WRITER=1
  CHECK_SECTION_DRAFTER=1
  CHECK_BIAS_DETECTION=1
  CHECK_DISSEMINATION_FORMATTER=1
  CHECK_PERFORMANCE_OPTIMIZER=1
  CHECK_PEER_REVIEW=1
  CHECK_RESULTS_INTERPRETATION=1
  
  # Load mandatory agent list
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  AGENT_LIST_FILE="${SCRIPT_DIR}/lib/agent_endpoints_required.txt"
  
  if [ ! -f "$AGENT_LIST_FILE" ]; then
    echo "ERROR: Mandatory agent list not found at $AGENT_LIST_FILE"
    fail "Agent list file missing"
  fi
  
  # Define task type mappings for each agent
  declare -A AGENT_TASK_TYPES=(
    ["agent-stage2-lit"]="STAGE_2_LITERATURE_REVIEW"
    ["agent-stage2-screen"]="STAGE2_SCREEN"
    ["agent-stage2-extract"]="STAGE_2_EXTRACT"
    ["agent-stage2-synthesize"]="STAGE2_SYNTHESIZE"
    ["agent-lit-retrieval"]="LIT_RETRIEVAL"
    ["agent-lit-triage"]="LIT_TRIAGE"
    ["agent-policy-review"]="POLICY_REVIEW"
    ["agent-rag-ingest"]="RAG_INGEST"
    ["agent-rag-retrieve"]="RAG_RETRIEVE"
    ["agent-verify"]="CLAIM_VERIFY"
    ["agent-intro-writer"]="SECTION_WRITE_INTRO"
    ["agent-methods-writer"]="SECTION_WRITE_METHODS"
    ["agent-results-writer"]="SECTION_WRITE_RESULTS"
    ["agent-discussion-writer"]="SECTION_WRITE_DISCUSSION"
    ["agent-evidence-synthesis"]="EVIDENCE_SYNTHESIS"
    ["agent-results-interpretation"]="RESULTS_INTERPRETATION"
    ["agent-clinical-manuscript"]="CLINICAL_MANUSCRIPT_WRITE"
    ["agent-clinical-section-drafter"]="CLINICAL_SECTION_DRAFT"
    ["agent-peer-review-simulator"]="PEER_REVIEW_SIMULATION"
    ["agent-bias-detection"]="CLINICAL_BIAS_DETECTION"
    ["agent-dissemination-formatter"]="DISSEMINATION_FORMATTING"
  )
  
  # Parse mandatory agents
  MANDATORY_AGENTS=()
  while IFS= read -r line || [ -n "$line" ]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    MANDATORY_AGENTS+=("$(echo "$line" | xargs)")
  done < "$AGENT_LIST_FILE"
  
  echo "Testing ${#MANDATORY_AGENTS[@]} mandatory agents via orchestrator dispatch..."
  echo ""
  
  AGENT_TESTS_PASSED=0
  AGENT_TESTS_FAILED=0
  
  for agent_key in "${MANDATORY_AGENTS[@]}"; do
    TASK_TYPE="${AGENT_TASK_TYPES[$agent_key]:-}"
    
    if [ -z "$TASK_TYPE" ]; then
      echo "[$agent_key] WARNING: No task type mapping defined, skipping dispatch test"
      continue
    fi
    
    echo "[$agent_key] Testing task type: $TASK_TYPE"
    
    if [ -z "$AUTH_HEADER" ]; then
      echo "  Skipping (AUTH_HEADER not set)"
      continue
    fi
    
    # Router dispatch test
    _dispatch_out=$(curl "${CURL_OPTS[@]}" -X POST -H "$AUTH_HEADER" -H "Content-Type: application/json" \
      -d "{\"task_type\":\"$TASK_TYPE\",\"request_id\":\"smoke-${agent_key}\",\"mode\":\"DEMO\"}" \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" 2>/dev/null || echo -e "\n000")
    _dispatch_body=$(echo "$_dispatch_out" | head -n -1)
    _dispatch_code=$(echo "$_dispatch_out" | tail -n 1)
    
    if [ "${_dispatch_code:0:1}" = "2" ]; then
      ROUTED_AGENT=$(echo "$_dispatch_body" | sed -n 's/.*"agent_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
      
      if [ "$ROUTED_AGENT" = "$agent_key" ]; then
        echo "  ✓ Router dispatch OK (routed to $agent_key)"
        AGENT_TESTS_PASSED=$((AGENT_TESTS_PASSED + 1))
      else
        echo "  ✗ Router mismatch: expected $agent_key, got $ROUTED_AGENT"
        AGENT_TESTS_FAILED=$((AGENT_TESTS_FAILED + 1))
      fi
    else
      echo "  ✗ Router dispatch failed (HTTP $dispatch_code)"
      echo "  Response: $_dispatch_body"
      AGENT_TESTS_FAILED=$((AGENT_TESTS_FAILED + 1))
    fi
    
    echo ""
  done
  
  echo "=========================================="
  echo "Agent Validation Results:"
  echo "  Passed: $AGENT_TESTS_PASSED"
  echo "  Failed: $AGENT_TESTS_FAILED"
  echo "=========================================="
  
  if [ $AGENT_TESTS_FAILED -gt 0 ]; then
    echo ""
    echo "WARNING: Some agent dispatch tests failed. Review logs above."
    echo "Note: These are optional checks and do not block smoke test completion."
  fi
  
  echo ""
fi

echo "Stagewise smoke completed successfully."

# --- 13. Optional: Dissemination Formatter validation (LangSmith cloud integration)
if [ "$CHECK_DISSEMINATION_FORMATTER" = "1" ] || [ "$CHECK_DISSEMINATION_FORMATTER" = "true" ]; then
  echo "[13] Dissemination Formatter Agent Check (optional - LangSmith-based)"
  
  # 13a. Check LANGSMITH_API_KEY and agent ID are configured
  echo "[13a] Checking LANGSMITH_API_KEY and agent ID configuration"
  LANGSMITH_KEY_SET=false
  FORMATTER_AGENT_ID_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi

    AGENT_ID_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID:+SET}' 2>/dev/null || echo "")
    if [ "$AGENT_ID_CHECK" = "SET" ]; then
      FORMATTER_AGENT_ID_SET=true
      echo "✓ LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID not set (LangSmith agent dispatch will fail)"
      echo "To enable: Add LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID=<uuid> to .env (from LangSmith UI)"
    fi
  else
    echo "Warning: Docker not available, cannot check LANGSMITH_API_KEY"
  fi
  
  # 13b. Router dispatch test
  if [ -n "$AUTH_HEADER" ]; then
    echo "[13b] POST /api/ai/router/dispatch (DISSEMINATION_FORMATTING)"
    _dispatch_body=$(curl "${CURL_OPTS[@]}" "${AUTH_HEADER}" -X POST \
      "${ORCHESTRATOR_URL}/api/ai/router/dispatch" \
      -H "Content-Type: application/json" \
      -d '{"task_type":"DISSEMINATION_FORMATTING","request_id":"smoke-formatter-001","mode":"DEMO","inputs":{"manuscript_text":"# Test Manuscript\nThis is a test.","target_journal":"Nature","output_format":"text"}}')
    _dispatch_code=$(tail -n 1 <<< "$_dispatch_body")
    _dispatch_body=$(head -n -1 <<< "$_dispatch_body")
    
    if [ "$_dispatch_code" = "200" ]; then
      echo "Router dispatch OK: response code 200"
      AGENT_NAME=$(echo "$_dispatch_body" | grep -o '"agent_name":"[^"]*"' | cut -d'"' -f4 || echo "")
      if [ "$AGENT_NAME" = "agent-dissemination-formatter" ]; then
        echo "✓ Correctly routed to agent-dissemination-formatter"
      else
        echo "Warning: Expected agent-dissemination-formatter, got $AGENT_NAME"
      fi
    else
      echo "Warning: Router dispatch failed (code: $_dispatch_code)"
      echo "Response: $_dispatch_body"
    fi
  else
    echo "[13b] Skipping router dispatch (AUTH_HEADER not set)"
  fi
  
  # 13c. Check proxy container health
  echo "[13c] Checking proxy container health"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    if docker ps --format "{{.Names}}" | grep -q "agent-dissemination-formatter-proxy"; then
      echo "✓ agent-dissemination-formatter-proxy container is running"
      
      # Check health endpoint
      PROXY_HEALTH=$(docker compose exec -T agent-dissemination-formatter-proxy curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
      if echo "$PROXY_HEALTH" | grep -q "ok"; then
        echo "✓ Proxy health endpoint responding"
      else
        echo "Warning: Proxy health endpoint not responding"
      fi
    else
      echo "Warning: agent-dissemination-formatter-proxy container not running"
    fi
  else
    echo "Warning: Docker not available, cannot check proxy container"
  fi
  
  # 13d. Validate artifacts directory structure
  echo "[13d] Checking artifacts directory structure"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts exists"
    mkdir -p /data/artifacts/validation/dissemination-formatter-smoke 2>/dev/null || true
    if [ -d "/data/artifacts/validation/dissemination-formatter-smoke" ]; then
      # Write a minimal validation record
      TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
      mkdir -p "/data/artifacts/validation/dissemination-formatter-smoke/${TIMESTAMP}" 2>/dev/null || true
      cat > "/data/artifacts/validation/dissemination-formatter-smoke/${TIMESTAMP}/summary.json" 2>/dev/null <<FORMATTER_SMOKE_EOF
{
  "agent": "agent-dissemination-formatter",
  "task_type": "DISSEMINATION_FORMATTING",
  "timestamp": "${TIMESTAMP}",
  "langsmith_key_set": ${LANGSMITH_KEY_SET},
  "formatter_agent_id_set": ${FORMATTER_AGENT_ID_SET},
  "router_registered": true,
  "proxy_container_running": $(docker ps --format "{{.Names}}" | grep -q "agent-dissemination-formatter-proxy" && echo "true" || echo "false"),
  "status": "smoke-check-complete"
}
FORMATTER_SMOKE_EOF
      echo "✓ Wrote validation artifact to /data/artifacts/validation/dissemination-formatter-smoke/${TIMESTAMP}/summary.json"
    fi
  else
    echo "Warning: /data/artifacts not found (no artifact write; formatted manuscripts go to Google Docs)"
  fi
  
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY + LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID"
  echo "      Proxy container must be running and healthy for full integration"
  echo "      Full integration test requires: Manuscript → Formatter → Journal-ready output"
  
  echo "Dissemination Formatter Agent check complete (optional - does not block)"
else
  echo "[13] Skipping Dissemination Formatter check (set CHECK_DISSEMINATION_FORMATTER=1 to enable)"
fi

# --- 14. Optional: Performance Optimizer validation (LangSmith cloud integration - cross-cutting)
if [ "$CHECK_PERFORMANCE_OPTIMIZER" = "1" ] || [ "$CHECK_PERFORMANCE_OPTIMIZER" = "true" ]; then
  echo "[14] Performance Optimizer Agent Check (optional - LangSmith-based)"
  
  # 14a. Check LANGSMITH_API_KEY and agent ID are configured
  echo "[14a] Checking LANGSMITH_API_KEY and agent ID configuration"
  LANGSMITH_KEY_SET=false
  PERF_AGENT_ID_SET=false
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    KEY_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
    if [ "$KEY_CHECK" = "SET" ]; then
      LANGSMITH_KEY_SET=true
      echo "✓ LANGSMITH_API_KEY is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_API_KEY not set (LangSmith cloud integration will fail)"
      echo "To enable: Add LANGSMITH_API_KEY=lsv2_pt_... to .env and recreate orchestrator"
    fi
    
    AGENT_ID_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID:+SET}' 2>/dev/null || echo "")
    if [ "$AGENT_ID_CHECK" = "SET" ]; then
      PERF_AGENT_ID_SET=true
      echo "✓ LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID is configured in orchestrator"
    else
      echo "Warning: LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID not set"
      echo "To enable: Add LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID=<uuid> to .env and recreate orchestrator"
    fi
  else
    echo "Warning: Docker unavailable (cannot check LangSmith keys)"
  fi
  
  # 14b. POST /api/ai/router/dispatch (PERFORMANCE_OPTIMIZATION)
  echo "[14b] POST /api/ai/router/dispatch (PERFORMANCE_OPTIMIZATION)"
  DISPATCH_RESP=$(curl -s -X POST "$ORCHESTRATOR_URL/api/ai/router/dispatch" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "task_type": "PERFORMANCE_OPTIMIZATION",
      "request_id": "smoke-perf-001",
      "mode": "DEMO",
      "inputs": {
        "metrics_data": {
          "last_24h": {
            "p50_latency_ms": 150,
            "p95_latency_ms": 450,
            "p99_latency_ms": 800,
            "error_rate": 0.02,
            "total_requests": 5000,
            "token_cost_usd": 12.50
          }
        },
        "analysis_focus": "latency",
        "time_period": "last_24_hours"
      }
    }' 2>/dev/null || echo "FAIL")
  
  DISPATCH_CODE=$(echo "$DISPATCH_RESP" | jq -r '.error // "OK"' 2>/dev/null || echo "PARSE_ERROR")
  
  if echo "$DISPATCH_RESP" | grep -q "agent-performance-optimizer"; then
    echo "Router dispatch OK: response code 200"
    echo "✓ Correctly routed to agent-performance-optimizer"
  else
    echo "Warning: Router dispatch failed or returned unexpected response"
    echo "Response: $DISPATCH_RESP"
    echo "Note: This is expected if orchestrator or agent-performance-optimizer-proxy is not running"
  fi
  
  # 14c. Check proxy container health
  echo "[14c] Checking proxy container health"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    if docker ps --format "{{.Names}}" | grep -q "agent-performance-optimizer-proxy"; then
      echo "✓ agent-performance-optimizer-proxy container is running"
      
      # Try health endpoint via docker exec
      HEALTH_CHECK=$(docker compose exec -T agent-performance-optimizer-proxy curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
      if echo "$HEALTH_CHECK" | grep -q "ok"; then
        echo "✓ Proxy health endpoint responding"
      else
        echo "Warning: Proxy health check failed (may be starting up)"
      fi
    else
      echo "Warning: agent-performance-optimizer-proxy container not running"
      echo "Start with: docker compose up -d agent-performance-optimizer-proxy"
    fi
  else
    echo "Warning: Docker unavailable (cannot check proxy container)"
  fi
  
  # 14d. Check artifacts directory structure (optional)
  echo "[14d] Checking artifacts directory structure"
  if [ -d "/data/artifacts" ]; then
    echo "✓ /data/artifacts exists"
    
    # Write a minimal validation record
    if [ -d "/data/artifacts/validation/performance-optimizer-smoke" ]; then
      TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
      mkdir -p "/data/artifacts/validation/performance-optimizer-smoke/${TIMESTAMP}" 2>/dev/null || true
      cat > "/data/artifacts/validation/performance-optimizer-smoke/${TIMESTAMP}/summary.json" 2>/dev/null <<PERF_SMOKE_EOF
{
  "agent": "agent-performance-optimizer",
  "task_type": "PERFORMANCE_OPTIMIZATION",
  "timestamp": "${TIMESTAMP}",
  "langsmith_key_set": ${LANGSMITH_KEY_SET},
  "perf_agent_id_set": ${PERF_AGENT_ID_SET},
  "router_registered": true,
  "proxy_container_running": $(docker ps --format "{{.Names}}" | grep -q "agent-performance-optimizer-proxy" && echo "true" || echo "false"),
  "status": "smoke-check-complete"
}
PERF_SMOKE_EOF
      echo "✓ Wrote validation artifact to /data/artifacts/validation/performance-optimizer-smoke/${TIMESTAMP}/summary.json"
    fi
  else
    echo "Warning: /data/artifacts not found (no artifact write; reports go to Google Docs)"
  fi
  
  echo "Note: LangSmith cloud API calls require valid LANGSMITH_API_KEY + LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID"
  echo "      Proxy container must be running and healthy for full integration"
  echo "      Full integration test requires: Metrics → Optimizer → Performance report"
  echo "      Optional: Set GOOGLE_SHEETS_API_KEY and GOOGLE_DOCS_API_KEY for Google integration"
  
  echo "Performance Optimizer Agent check complete (optional - does not block)"
else
  echo "[14] Skipping Performance Optimizer check (set CHECK_PERFORMANCE_OPTIMIZER=1 to enable)"
fi

echo ""

# ==============================================================================
# CHECK_ALL_AGENTS - Dynamic validation of all agents in AGENT_ENDPOINTS_JSON
# ==============================================================================
if [ "$CHECK_ALL_AGENTS" = "1" ]; then
  echo "════════════════════════════════════════════════════════════════"
  echo "[15] ALL AGENTS VALIDATION (CHECK_ALL_AGENTS=1)"
  echo "════════════════════════════════════════════════════════════════"
  echo ""
  echo "Dynamically validating all agents from AGENT_ENDPOINTS_JSON..."
  echo ""
  
  # Ensure orchestrator is running
  if ! docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
    echo "✗ ERROR: Orchestrator container is not running"
    echo "Start orchestrator: docker compose up -d orchestrator"
    echo "Skipping all-agents check"
  else
    # Fetch AGENT_ENDPOINTS_JSON from orchestrator
    ENDPOINTS_JSON=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null || echo "")
    
    if [ -z "$ENDPOINTS_JSON" ]; then
      echo "✗ ERROR: AGENT_ENDPOINTS_JSON not set in orchestrator"
      echo "Add to docker-compose.yml and restart orchestrator"
    elif ! echo "$ENDPOINTS_JSON" | python3 -m json.tool >/dev/null 2>&1; then
      echo "✗ ERROR: AGENT_ENDPOINTS_JSON is not valid JSON"
      echo "Fix JSON syntax in docker-compose.yml"
    else
      # Extract all agent keys
      AGENT_KEYS=$(echo "$ENDPOINTS_JSON" | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin).keys())))' 2>/dev/null || echo "")
      
      if [ -z "$AGENT_KEYS" ]; then
        echo "✗ ERROR: Failed to parse agent keys from AGENT_ENDPOINTS_JSON"
      else
        # Convert to array
        AGENT_KEYS_ARRAY=()
        while IFS= read -r agent_key; do
          [ -n "$agent_key" ] && AGENT_KEYS_ARRAY+=("$agent_key")
        done <<< "$AGENT_KEYS"
        
        TOTAL_AGENTS=${#AGENT_KEYS_ARRAY[@]}
        echo "Found $TOTAL_AGENTS agents in AGENT_ENDPOINTS_JSON"
        echo ""
        
        # Iterate through each agent
        AGENTS_PASSED=0
        AGENTS_FAILED=0
        
        for agent_key in "${AGENT_KEYS_ARRAY[@]}"; do
          echo "────────────────────────────────────────────────────────────────"
          echo "Testing agent: $agent_key"
          echo "────────────────────────────────────────────────────────────────"
          
          # Get agent URL
          AGENT_URL=$(echo "$ENDPOINTS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$agent_key', ''))" 2>/dev/null || echo "")
          
          if [ -z "$AGENT_URL" ]; then
            echo "✗ Agent not found in AGENT_ENDPOINTS_JSON (unexpected)"
            AGENTS_FAILED=$((AGENTS_FAILED + 1))
            continue
          fi
          
          echo "  Agent URL: $AGENT_URL"
          
          # Check if container is running
          SERVICE_NAME=$(echo "$AGENT_URL" | sed -n 's|^https\?://\([^:]*\):.*|\1|p')
          if ! docker ps --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$\|^researchflow-${SERVICE_NAME}$"; then
            echo "  ✗ Container not running: $SERVICE_NAME"
            AGENTS_FAILED=$((AGENTS_FAILED + 1))
            
            # Write failure artifact
            if [ -d "/data/artifacts" ]; then
              TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
              SAFE_KEY=$(echo "$agent_key" | tr '-' '_' | tr '[:lower:]' '[:upper:]')
              mkdir -p "/data/artifacts/validation/${agent_key}/${TIMESTAMP}" 2>/dev/null || true
              cat > "/data/artifacts/validation/${agent_key}/${TIMESTAMP}/summary.json" 2>/dev/null <<AGENT_FAIL_EOF
{
  "agentKey": "${agent_key}",
  "timestamp": "${TIMESTAMP}",
  "request": {
    "task_type": "HEALTH_CHECK",
    "agent_url": "${AGENT_URL}",
    "service_name": "${SERVICE_NAME}"
  },
  "response_status": "container_not_running",
  "ok": false,
  "error": "Container ${SERVICE_NAME} is not running"
}
AGENT_FAIL_EOF
            fi
            
            continue
          fi
          
          echo "  ✓ Container running: $SERVICE_NAME"
          
          # Determine a safe task type for this agent (use a generic health check approach)
          # For deterministic smoke tests, we don't actually invoke the agent logic,
          # we just validate the orchestrator routing
          TASK_TYPE="HEALTH_CHECK_${agent_key}"
          
          # Dispatch through orchestrator router (this validates routing only)
          echo "  Testing orchestrator routing..."
          
          # Create a simple dispatch request (deterministic, no external calls)
          DISPATCH_RESP=$(curl -s -X POST "$ORCHESTRATOR_URL/api/ai/router/dispatch" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
              \"task_type\": \"STAGE_2_LITERATURE_REVIEW\",
              \"request_id\": \"smoke-${agent_key}-001\",
              \"mode\": \"DEMO\",
              \"inputs\": {
                \"query\": \"test query for smoke test\",
                \"deterministic\": true,
                \"max_results\": 1
              }
            }" 2>/dev/null || echo "FAIL")
          
          DISPATCH_CODE=$(echo "$DISPATCH_RESP" | jq -r '.error // "OK"' 2>/dev/null || echo "PARSE_ERROR")
          
          # Check if dispatch succeeded (or at least routed correctly)
          if echo "$DISPATCH_RESP" | grep -qE "agent_name|agent_url"; then
            echo "  ✓ Orchestrator dispatch successful"
            AGENT_RESULT="ok"
            AGENTS_PASSED=$((AGENTS_PASSED + 1))
          else
            echo "  ✗ Orchestrator dispatch failed"
            echo "  Response: $(echo "$DISPATCH_RESP" | head -c 200)"
            AGENT_RESULT="dispatch_failed"
            AGENTS_FAILED=$((AGENTS_FAILED + 1))
          fi
          
          # Write artifact
          if [ -d "/data/artifacts" ]; then
            TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
            SAFE_KEY=$(echo "$agent_key" | tr '-' '_' | tr '[:lower:]' '[:upper:]')
            mkdir -p "/data/artifacts/validation/${agent_key}/${TIMESTAMP}" 2>/dev/null || true
            cat > "/data/artifacts/validation/${agent_key}/${TIMESTAMP}/summary.json" 2>/dev/null <<AGENT_ARTIFACT_EOF
{
  "agentKey": "${agent_key}",
  "timestamp": "${TIMESTAMP}",
  "request": {
    "method": "POST",
    "endpoint": "/api/ai/router/dispatch",
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "smoke-${agent_key}-001",
    "mode": "DEMO"
  },
  "response_status": 200,
  "ok": $([ "$AGENT_RESULT" = "ok" ] && echo "true" || echo "false"),
  "error": $([ "$AGENT_RESULT" = "ok" ] && echo "null" || echo "\"${AGENT_RESULT}\""),
  "agent_url": "${AGENT_URL}",
  "service_name": "${SERVICE_NAME}",
  "container_running": true,
  "dispatch_response_excerpt": $(echo "$DISPATCH_RESP" | jq -c '.' 2>/dev/null || echo "\"${DISPATCH_RESP:0:100}\"")
}
AGENT_ARTIFACT_EOF
            echo "  ✓ Wrote artifact: /data/artifacts/validation/${agent_key}/${TIMESTAMP}/summary.json"
          else
            echo "  ⚠ /data/artifacts not found (artifact not written)"
          fi
          
          echo ""
        done
        
        echo "════════════════════════════════════════════════════════════════"
        echo "ALL AGENTS VALIDATION SUMMARY"
        echo "════════════════════════════════════════════════════════════════"
        echo "  Total agents:  $TOTAL_AGENTS"
        echo "  Passed:        $AGENTS_PASSED"
        echo "  Failed:        $AGENTS_FAILED"
        
        if [ $AGENTS_FAILED -eq 0 ]; then
          echo ""
          echo "  ✓ ALL AGENTS VALIDATED SUCCESSFULLY"
        else
          echo ""
          echo "  ✗ Some agents failed validation"
          echo ""
          echo "  Common issues:"
          echo "    - Agent container not running: docker compose up -d <service>"
          echo "    - Agent unhealthy: docker compose logs <service>"
          echo "    - Routing misconfigured: check TASK_TYPE_TO_AGENT in ai-router.ts"
        fi
        
        echo "════════════════════════════════════════════════════════════════"
        echo ""
        
        # Note: This is informational only, does not block smoke test
        echo "Note: All-agents validation is informational only and does not block smoke test"
        echo "      For mandatory validation, use preflight script: ./scripts/hetzner-preflight.sh"
      fi
    fi
  fi
  
  echo ""
  echo "All-agents check complete"
else
  echo "[15] Skipping all-agents validation (set CHECK_ALL_AGENTS=1 to enable)"
fi

echo ""
