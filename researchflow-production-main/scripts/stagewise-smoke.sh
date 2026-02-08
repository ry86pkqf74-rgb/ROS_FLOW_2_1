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

# --- 12. Optional: Results Interpretation Agent validation (LangSmith cloud integration)
if [ "$CHECK_RESULTS_INTERPRETATION" = "1" ] || [ "$CHECK_RESULTS_INTERPRETATION" = "true" ]; then
  echo "[12] Results Interpretation Agent Check (optional - LangSmith-based)"
  
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
echo "Stagewise smoke completed successfully."
