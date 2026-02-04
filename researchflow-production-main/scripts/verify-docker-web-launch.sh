#!/bin/bash
# ============================================
# ResearchFlow Docker Web Stack Verification
# ============================================
# Usage:
#   ./scripts/verify-docker-web-launch.sh [host] [web_port] [api_port] [worker_port] [collab_health_port]
#
# Defaults:
#   host=localhost
#   web_port=5173
#   api_port=3001
#   worker_port=8000
#   collab_health_port=1235

set -e

HOST=${1:-localhost}
WEB_PORT=${2:-5173}
API_PORT=${3:-3001}
WORKER_PORT=${4:-8000}
COLLAB_PORT=${5:-1235}

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
  local name="$1"
  local url="$2"
  echo -n "Checking ${name}... "
  if curl -s -f "${url}" > /dev/null; then
    echo -e "${GREEN}OK${NC} (${url})"
  else
    echo -e "${RED}FAIL${NC} (${url})"
    exit 1
  fi
}

echo "========================================"
echo "ResearchFlow Docker Web Stack Check"
echo "========================================"
echo "Host: ${HOST}"
echo "Web:  http://${HOST}:${WEB_PORT}"
echo "API:  http://${HOST}:${API_PORT}"
echo "Worker: http://${HOST}:${WORKER_PORT}"
echo "Collab health: http://${HOST}:${COLLAB_PORT}"
echo ""

check "Web health" "http://${HOST}:${WEB_PORT}/health"
check "Orchestrator health" "http://${HOST}:${API_PORT}/health"
check "Orchestrator API health" "http://${HOST}:${API_PORT}/api/health"
check "Worker health" "http://${HOST}:${WORKER_PORT}/health"
check "Collab health" "http://${HOST}:${COLLAB_PORT}/health"

echo ""
echo "✅ Docker web stack health checks passed."
