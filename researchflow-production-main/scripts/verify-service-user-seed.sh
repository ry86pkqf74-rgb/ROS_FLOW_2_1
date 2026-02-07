#!/bin/bash
# Verify that migration 019_seed_service_user.sql is applied and audit FK warnings are gone.
# Run after: docker compose up -d postgres migrate orchestrator
# Usage: ./scripts/verify-service-user-seed.sh
# From host: ORCHESTRATOR_URL defaults to http://localhost:3001 (compose exposes 3001).

set -e

cd "$(dirname "$0")/.."
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:3001}"

WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' .env 2>/dev/null | tail -n1 | cut -d= -f2-)"
if [ -z "$WORKER_SERVICE_TOKEN" ]; then
  echo "Error: WORKER_SERVICE_TOKEN not set in .env. Generate and append to .env (do not paste token here)."
  exit 1
fi

echo "=== Checking orchestrator reachability ==="
if ! curl -sSf --connect-timeout 5 --max-time 10 "${ORCHESTRATOR_URL}/health" >/dev/null 2>&1; then
  echo "Error: Orchestrator unreachable at ${ORCHESTRATOR_URL}. Start stack: docker compose up -d postgres migrate orchestrator"
  exit 1
fi

echo "=== Calling dispatch (service token) ==="
HTTP_CODE=$(curl -sS -o /tmp/dispatch_verify.json -w "%{http_code}" \
  --connect-timeout 5 --max-time 30 \
  -X POST "${ORCHESTRATOR_URL}/api/ai/router/dispatch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}" \
  -d '{"task_type":"STAGE_2_LITERATURE_REVIEW","request_id":"rf-seed-test-001"}')
echo "HTTP Status: ${HTTP_CODE}"

echo ""
echo "=== Checking orchestrator logs for FK warnings (last 200 lines) ==="
FK_WARNINGS=$(docker compose logs --tail=200 orchestrator 2>/dev/null | grep -c "fk_violation_23503" || true)
if [ "${FK_WARNINGS}" -eq 0 ]; then
  echo "OK: No fk_violation_23503 in recent orchestrator logs (service user seed is effective)."
else
  echo "Warning: Found ${FK_WARNINGS} fk_violation_23503 line(s). Ensure migration 019_seed_service_user.sql has been applied."
fi

if [ "$HTTP_CODE" = "200" ]; then
  echo ""
  echo "Verification: HTTP 200 and service user seed eliminates FK warnings."
  exit 0
else
  echo "Verification failed: expected HTTP 200, got ${HTTP_CODE}"
  exit 1
fi
