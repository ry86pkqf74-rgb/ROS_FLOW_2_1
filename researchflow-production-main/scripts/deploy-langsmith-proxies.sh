#!/bin/bash
# ============================================================================
# Deploy LangSmith Proxy Services
# ============================================================================
# Deploys all three LangSmith cloud-hosted agents as FastAPI proxy services:
#   - agent-results-interpretation-proxy
#   - agent-clinical-manuscript-proxy
#   - agent-section-drafter-proxy
#
# Prerequisites:
#   - LANGSMITH_API_KEY set in .env
#   - Agent IDs set in .env (LANGSMITH_*_AGENT_ID)
#   - AGENT_ENDPOINTS_JSON updated with proxy URLs
#
# Usage:
#   ./scripts/deploy-langsmith-proxies.sh
# ============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}  LangSmith Proxy Services Deployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Validate prerequisites
echo -e "${BLUE}📋 Validating prerequisites...${NC}"

if ! grep -q "LANGSMITH_API_KEY=" .env 2>/dev/null; then
  echo -e "${RED}✗ LANGSMITH_API_KEY not found in .env${NC}"
  echo "  Add: LANGSMITH_API_KEY=lsv2_pt_..."
  exit 1
fi

REQUIRED_IDS=(
  "LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID"
  "LANGSMITH_MANUSCRIPT_AGENT_ID"
  "LANGSMITH_SECTION_DRAFTER_AGENT_ID"
)

for id_var in "${REQUIRED_IDS[@]}"; do
  if ! grep -q "$id_var=" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠ $id_var not found in .env${NC}"
    echo "  This proxy may fail to start. Add: $id_var=uuid"
  fi
done

echo -e "${GREEN}✓ Prerequisites validated${NC}"
echo ""

# Build proxy services
echo -e "${BLUE}📦 Building LangSmith proxy services...${NC}"

PROXIES=(
  "agent-results-interpretation-proxy"
  "agent-clinical-manuscript-proxy"
  "agent-section-drafter-proxy"
)

for proxy in "${PROXIES[@]}"; do
  echo "  Building $proxy..."
  if docker compose build "$proxy" 2>&1 | grep -q "ERROR"; then
    echo -e "${RED}✗ Build failed for $proxy${NC}"
    exit 1
  fi
done

echo -e "${GREEN}✓ All proxies built successfully${NC}"
echo ""

# Start proxy services
echo -e "${BLUE}🚀 Starting proxy services...${NC}"

for proxy in "${PROXIES[@]}"; do
  echo "  Starting $proxy..."
  docker compose up -d "$proxy"
done

echo -e "${GREEN}✓ All proxies started${NC}"
echo ""

# Wait for startup
echo -e "${BLUE}⏳ Waiting for services to become healthy (15s)...${NC}"
sleep 15

# Check health
echo -e "${BLUE}🔍 Checking health status...${NC}"

SUCCESS=true

for proxy in "${PROXIES[@]}"; do
  # Check container is running
  if ! docker compose ps "$proxy" | grep -q "Up"; then
    echo -e "${RED}  ✗ $proxy: Container not running${NC}"
    SUCCESS=false
    continue
  fi
  
  # Check health endpoint
  if docker compose exec "$proxy" curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ $proxy: Healthy${NC}"
  else
    echo -e "${RED}  ✗ $proxy: Health check failed${NC}"
    SUCCESS=false
  fi
  
  # Check readiness (LangSmith connectivity)
  if docker compose exec "$proxy" curl -sf http://localhost:8000/health/ready > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ $proxy: Ready (LangSmith reachable)${NC}"
  else
    echo -e "${YELLOW}  ⚠ $proxy: Not ready (check LANGSMITH_API_KEY)${NC}"
  fi
done

echo ""

if [ "$SUCCESS" = false ]; then
  echo -e "${RED}✗ Some proxies failed health checks. Check logs:${NC}"
  echo "  docker compose logs agent-clinical-manuscript-proxy"
  exit 1
fi

# Restart orchestrator
echo -e "${BLUE}🔄 Restarting orchestrator to load new endpoints...${NC}"
docker compose up -d --force-recreate orchestrator
sleep 5
echo -e "${GREEN}✓ Orchestrator restarted${NC}"
echo ""

# Verify AGENT_ENDPOINTS_JSON
echo -e "${BLUE}🔍 Verifying AGENT_ENDPOINTS_JSON registration...${NC}"

if docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | jq -e '.["agent-clinical-manuscript"]' > /dev/null 2>&1; then
  echo -e "${GREEN}  ✓ agent-clinical-manuscript registered${NC}"
else
  echo -e "${YELLOW}  ⚠ agent-clinical-manuscript not in AGENT_ENDPOINTS_JSON${NC}"
fi

if docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | jq -e '.["agent-clinical-section-drafter"]' > /dev/null 2>&1; then
  echo -e "${GREEN}  ✓ agent-clinical-section-drafter registered${NC}"
else
  echo -e "${YELLOW}  ⚠ agent-clinical-section-drafter not in AGENT_ENDPOINTS_JSON${NC}"
fi

if docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | jq -e '.["agent-results-interpretation"]' > /dev/null 2>&1; then
  echo -e "${GREEN}  ✓ agent-results-interpretation registered${NC}"
else
  echo -e "${YELLOW}  ⚠ agent-results-interpretation not in AGENT_ENDPOINTS_JSON${NC}"
fi

echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}  ✅ LangSmith proxy services deployed successfully!${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test dispatch:"
echo "     curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \\"
echo "       -H 'Authorization: Bearer \$TOKEN' \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"task_type\":\"CLINICAL_MANUSCRIPT_WRITE\",\"request_id\":\"test-1\",\"mode\":\"DEMO\"}'"
echo ""
echo "  2. View logs:"
echo "     docker compose logs -f agent-clinical-manuscript-proxy"
echo ""
echo "  3. Monitor in LangSmith:"
echo "     https://smith.langchain.com/"
echo ""
echo "Documentation:"
echo "  - Full guide: docs/deployment/langsmith-proxy-deployment.md"
echo "  - Architecture: LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md"
echo "  - Quick start: LANGSMITH_PROXY_QUICKSTART.md"
echo ""
