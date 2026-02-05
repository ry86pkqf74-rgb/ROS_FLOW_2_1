#!/bin/bash

# Stage 2 End-to-End Test Script
# Run this in VSCode terminal while worker builds

set -e

echo "=== Waiting for worker to finish building ==="
echo "Check docker compose logs to see when worker is ready"
echo ""

echo "=== Step 1: Check container status ==="
docker compose ps
echo ""

echo "=== Step 2: Health check orchestrator ==="
curl -sS http://localhost:3001/health && echo
echo ""

echo "=== Step 3: Health check agent (via orchestrator) ==="
docker compose exec orchestrator curl -sS http://agent-stage2-lit:8000/health && echo
echo ""

echo "=== Step 4: Find Stage 2 execute route ==="
cd services/orchestrator
rg -n "stages.*2.*execute|/api/workflow/stages|Stage2ExecuteSchema|stage.*execute" src/routes/workflow/stages.ts || echo "Route search completed"
cd ../..
echo ""

echo "=== Step 5: Extract service token and test Stage 2 execution ==="
WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2-)"
echo "Using token: ${WORKER_SERVICE_TOKEN:0:20}..."
echo ""

# Generate a UUID for workflow_id
WORKFLOW_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "Generated workflow_id: ${WORKFLOW_ID}"
echo ""

curl -sS -X POST "http://localhost:3001/api/workflow/stages/2/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}" \
  -d "{
    \"workflow_id\": \"${WORKFLOW_ID}\",
    \"research_question\": \"What is the effect of statins on cardiovascular mortality?\",
    \"mode\": \"DEMO\",
    \"risk_tier\": \"NON_SENSITIVE\",
    \"domain_id\": \"clinical\",
    \"inputs\": {
      \"query\": \"statins reduce cardiovascular mortality meta-analysis\",
      \"max_results\": 5,
      \"databases\": [\"pubmed\"],
      \"language\": \"en\",
      \"dedupe\": true,
      \"require_abstract\": true
    }
  }" | tee /tmp/stage2_execute_response.json
echo ""
echo ""

echo "=== Step 6: Watch logs (last 200 lines) ==="
echo "--- Orchestrator logs ---"
docker compose logs --tail=200 orchestrator
echo ""
echo "--- Worker logs ---"
docker compose logs --tail=200 worker
echo ""
echo "--- Agent logs ---"
docker compose logs --tail=200 agent-stage2-lit
echo ""

echo "=== Test complete ==="
echo "Response saved to: /tmp/stage2_execute_response.json"
