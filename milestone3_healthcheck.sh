#!/bin/bash
# Milestone 3 - Agent Fleet Health Check

cd /Users/ros/Desktop/ROS_FLOW_2_1/researchflow-production-main

echo "====================================="
echo "Agent Health Check - Milestone 3"
echo "====================================="
echo ""

echo "1. Checking docker-compose service status..."
docker compose ps | grep -E "agent-lit-retrieval|agent-policy-review"

echo ""
echo "2. Testing agent-lit-retrieval health via docker exec..."
docker compose exec -T agent-lit-retrieval curl -s http://localhost:8000/health || echo "Failed to reach agent-lit-retrieval"

echo ""
echo "3. Testing agent-policy-review health via docker exec..."
docker compose exec -T agent-policy-review curl -s http://localhost:8000/health || echo "Failed to reach agent-policy-review"

echo ""
echo "4. Testing readiness endpoints..."
echo "   agent-lit-retrieval /health/ready:"
docker compose exec -T agent-lit-retrieval curl -s http://localhost:8000/health/ready || echo "Failed"

echo ""
echo "   agent-policy-review /health/ready:"
docker compose exec -T agent-policy-review curl -s http://localhost:8000/health/ready || echo "Failed"

echo ""
echo "5. Verifying AGENT_ENDPOINTS_JSON in orchestrator..."
docker compose exec -T orchestrator sh -lc 'echo "AGENT_ENDPOINTS_JSON="$AGENT_ENDPOINTS_JSON'

echo ""
echo "====================================="
echo "Health Check Complete"
echo "====================================="
