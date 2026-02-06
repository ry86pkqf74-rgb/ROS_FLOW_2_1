#!/bin/bash
# Test script for audit log FK violation fix

set -e

cd researchflow-production-main

echo "=== Building and restarting orchestrator ==="
docker compose -f docker-compose.yml up -d --build orchestrator

echo ""
echo "=== Waiting for orchestrator to be ready ==="
sleep 5

echo ""
echo "=== Testing /api/ai/router/dispatch endpoint ==="

WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2-)"

HTTP_CODE="$(
  curl -sS -o /tmp/dispatch_response.json -w "%{http_code}" \
    -X POST http://localhost:3001/api/ai/router/dispatch \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}" \
    -d '{
      "task_type": "STAGE_2_LITERATURE_REVIEW",
      "request_id": "rf-stage2-smoke-002",
      "mode": "DEMO",
      "risk_tier": "NON_SENSITIVE",
      "inputs": {
        "query": "statins reduce cardiovascular mortality meta-analysis",
        "max_results": 5,
        "databases": ["pubmed"]
      }
    }'
)"

echo "HTTP Status: ${HTTP_CODE}"
echo ""
echo "Response:"
cat /tmp/dispatch_response.json
echo ""
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ SUCCESS: Dispatch endpoint returned 200"
  exit 0
else
  echo "❌ FAILED: Expected 200, got ${HTTP_CODE}"
  exit 1
fi
