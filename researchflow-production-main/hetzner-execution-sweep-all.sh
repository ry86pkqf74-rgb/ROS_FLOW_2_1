#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
DISPATCH_URL="${ORCHESTRATOR_URL}/api/ai/router/dispatch"
MODE="${MODE:-DEMO}"
RISK_TIER="${RISK_TIER:-NON_SENSITIVE}"
TIMEOUT_SECS="${TIMEOUT_SECS:-120}"

if [ -z "${WORKER_SERVICE_TOKEN:-}" ]; then
  echo "ERROR: WORKER_SERVICE_TOKEN not set"
  exit 1
fi

# Task types (keep in sync with ai-router.ts TASK_TYPE_TO_AGENT)
TASKS=(
ARTIFACT_AUDIT
CLAIM_VERIFY
CLINICAL_BIAS_DETECTION
CLINICAL_MANUSCRIPT_WRITE
CLINICAL_MODEL_FINE_TUNING
CLINICAL_SECTION_DRAFT
COMPLIANCE_AUDIT
DISSEMINATION_FORMATTING
EVIDENCE_SYNTHESIS
HYPOTHESIS_REFINEMENT
JOURNAL_GUIDELINES_CACHE
LIT_RETRIEVAL
LIT_TRIAGE
MULTILINGUAL_LITERATURE_PROCESSING
PEER_REVIEW_SIMULATION
PERFORMANCE_OPTIMIZATION
POLICY_REVIEW
RAG_INGEST
RAG_RETRIEVE
RESILIENCE_ARCHITECTURE
RESULTS_INTERPRETATION
SECTION_WRITE_DISCUSSION
SECTION_WRITE_INTRO
SECTION_WRITE_METHODS
SECTION_WRITE_RESULTS
STATISTICAL_ANALYSIS
STAGE2_EXTRACT
STAGE2_SCREEN
STAGE2_SYNTHESIZE
STAGE_2_EXTRACT
STAGE_2_LITERATURE_REVIEW
)

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out="/tmp/execution_sweep_${ts}.tsv"

echo -e "task_type\tdispatch_http\tagent_name\tagent_url\trun_http\tlatency_ms\tpass_fail\terror_preview" | tee "$out" >/dev/null

curl_json () {
  # args: url json_body auth_header(optional)
  local url="$1"
  local body="$2"
  local auth="${3:-}"
  
  if [ -n "$auth" ]; then
    curl -sS --max-time "$TIMEOUT_SECS" -w '\n%{http_code}\n%{time_total}' \
      -H "Content-Type: application/json" -H "$auth" \
      -d "$body" "$url"
  else
    curl -sS --max-time "$TIMEOUT_SECS" -w '\n%{http_code}\n%{time_total}' \
      -H "Content-Type: application/json" \
      -d "$body" "$url"
  fi
}

for t in "${TASKS[@]}"; do
  req_id="exec-sweep-${t}-${ts}"
  dispatch_body="{\"task_type\":\"$t\",\"request_id\":\"$req_id\",\"mode\":\"$MODE\",\"risk_tier\":\"$RISK_TIER\",\"inputs\":{},\"budgets\":{}}"
  
  dispatch_resp="$(curl_json "$DISPATCH_URL" "$dispatch_body" "Authorization: Bearer $WORKER_SERVICE_TOKEN")"
  dispatch_time="$(echo "$dispatch_resp" | tail -n 1)"
  dispatch_code="$(echo "$dispatch_resp" | tail -n 2 | head -n 1)"
  dispatch_json="$(echo "$dispatch_resp" | sed '$d' | sed '$d')"
  
  agent_name="$(echo "$dispatch_json" | sed -n 's/.*"agent_name"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n 1)"
  agent_url="$(echo "$dispatch_json" | sed -n 's/.*"agent_url"[ ]*:[ ]*"\([^"]*\)".*/\1/p' | head -n 1)"
  
  if [ "$dispatch_code" != "200" ] || [ -z "$agent_url" ]; then
    err="$(echo "$dispatch_json" | tr '\n' ' ' | head -c 220)"
    echo -e "$t\t$dispatch_code\t$agent_name\t$agent_url\t\t\tFAIL\tDISPATCH_FAIL $err" | tee -a "$out" >/dev/null
    continue
  fi
  
  run_url="${agent_url%/}/agents/run/sync"
  run_body="{\"request_id\":\"$req_id\",\"task_type\":\"$t\",\"mode\":\"$MODE\",\"risk_tier\":\"$RISK_TIER\",\"inputs\":{},\"budgets\":{}}"
  
  run_resp="$(curl_json "$run_url" "$run_body")"
  run_time="$(echo "$run_resp" | tail -n 1)"
  run_code="$(echo "$run_resp" | tail -n 2 | head -n 1)"
  run_json="$(echo "$run_resp" | sed '$d' | sed '$d')"
  
  latency_ms="$(python3 - <<PY
import sys
try:
  print(int(float(sys.argv[1])*1000))
except:
  print("")
PY
"$run_time")"
  
  # "non-empty synthesized output" heuristic:
  # pass if HTTP 200 and response is non-trivial length
  if [ "$run_code" = "200" ] && [ "$(echo -n "$run_json" | wc -c | tr -d ' ')" -gt 50 ]; then
    echo -e "$t\t$dispatch_code\t$agent_name\t$agent_url\t$run_code\t$latency_ms\tPASS\t" | tee -a "$out" >/dev/null
  else
    err="$(echo "$run_json" | tr '\n' ' ' | head -c 220)"
    echo -e "$t\t$dispatch_code\t$agent_name\t$agent_url\t$run_code\t$latency_ms\tFAIL\tRUN_FAIL $err" | tee -a "$out" >/dev/null
  fi
done

echo ""
echo "Saved results: $out"
echo "Failures:"
awk -F'\t' 'NR>1 && $7=="FAIL"{print "-",$1,"=>",$8}' "$out" || true
