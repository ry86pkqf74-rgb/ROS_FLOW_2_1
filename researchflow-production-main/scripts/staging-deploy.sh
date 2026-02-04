#!/bin/bash
# ============================================
# ResearchFlow - Stage 1 Staging Deployment
# ============================================
# Deploys Stage 1 Protocol Design Agent to staging environment
# for feature flag testing and PICO pipeline validation
# ============================================

set -e

# Colors for output
BLUE='\033[34m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
CYAN='\033[36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STAGING_ENV_FILE="$PROJECT_ROOT/.env.staging"
ENABLE_NEW_STAGE_1=${1:-true}
TEST_MODE=${2:-false}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ResearchFlow Staging Deployment                 ║${NC}"
echo -e "${BLUE}║         Stage 1 Protocol Design Agent Testing               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  - ENABLE_NEW_STAGE_1: $ENABLE_NEW_STAGE_1"
echo "  - Test Mode: $TEST_MODE"
echo "  - Environment File: $STAGING_ENV_FILE"
echo ""

# Check prerequisites
echo -e "${BLUE}🔍 Checking Prerequisites...${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$STAGING_ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Creating staging environment file from example...${NC}"
    cp "$PROJECT_ROOT/.env.staging.example" "$STAGING_ENV_FILE"
    echo -e "${YELLOW}📝 Please edit $STAGING_ENV_FILE with your actual API keys before continuing.${NC}"
    read -p "Press Enter when ready to continue..." 
fi

# Validate required environment variables
source "$STAGING_ENV_FILE"
MISSING_VARS=()

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_key_here" ]; then
    MISSING_VARS+=("OPENAI_API_KEY")
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo -e "${YELLOW}Please configure these in $STAGING_ENV_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites satisfied${NC}"
echo ""

# Set feature flag environment variable
echo -e "${BLUE}🚩 Configuring Feature Flags...${NC}"
export ENABLE_NEW_STAGE_1="$ENABLE_NEW_STAGE_1"
sed -i.bak "s/ENABLE_NEW_STAGE_1=.*/ENABLE_NEW_STAGE_1=$ENABLE_NEW_STAGE_1/" "$STAGING_ENV_FILE"
echo -e "  - ENABLE_NEW_STAGE_1 set to: ${CYAN}$ENABLE_NEW_STAGE_1${NC}"
echo ""

# Clean up previous deployment
echo -e "${BLUE}🧹 Cleaning Up Previous Deployment...${NC}"
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.staging.yml down --volumes --remove-orphans || true
docker system prune -f || true
echo ""

# Build and start services
echo -e "${BLUE}🔨 Building Services...${NC}"
docker-compose -f docker-compose.staging.yml build --parallel

echo ""
echo -e "${BLUE}🚀 Starting Staging Environment...${NC}"
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be healthy
echo ""
echo -e "${BLUE}⏳ Waiting for Services to Start...${NC}"

services=("postgres" "redis" "ollama" "worker" "orchestrator")
for service in "${services[@]}"; do
    echo -n "  - $service: "
    
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.staging.yml ps "$service" | grep -q "healthy\|Up"; then
            echo -e "${GREEN}✅ Ready${NC}"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}❌ Failed to start${NC}"
            echo -e "${RED}Service logs:${NC}"
            docker-compose -f docker-compose.staging.yml logs "$service" | tail -20
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
done

# Download Ollama model if needed
echo ""
echo -e "${BLUE}🤖 Preparing Local LLM (Ollama)...${NC}"
echo "  - Pulling qwen2.5-coder:7b model..."
docker-compose -f docker-compose.staging.yml exec -T ollama ollama pull qwen2.5-coder:7b

# Validate feature flag configuration
echo ""
echo -e "${BLUE}🧪 Validating Feature Flag Configuration...${NC}"

# Test feature flag API
API_URL="http://localhost:3002"
FF_TEST_RESPONSE=$(curl -s "$API_URL/api/feature-flags" | jq -r '.["ENABLE_NEW_STAGE_1"] // "not_found"')

if [ "$FF_TEST_RESPONSE" == "true" ] && [ "$ENABLE_NEW_STAGE_1" == "true" ]; then
    echo -e "  - Feature Flag API: ${GREEN}✅ ENABLE_NEW_STAGE_1 = true${NC}"
elif [ "$FF_TEST_RESPONSE" == "false" ] && [ "$ENABLE_NEW_STAGE_1" == "false" ]; then
    echo -e "  - Feature Flag API: ${GREEN}✅ ENABLE_NEW_STAGE_1 = false${NC}"
else
    echo -e "  - Feature Flag API: ${YELLOW}⚠️  Inconsistent state (API: $FF_TEST_RESPONSE, Env: $ENABLE_NEW_STAGE_1)${NC}"
fi

# Display service URLs
echo ""
echo -e "${GREEN}🎉 Staging Environment Successfully Deployed!${NC}"
echo ""
echo -e "${CYAN}📊 Service URLs:${NC}"
echo "  - Frontend:      http://localhost:3000"
echo "  - API:          http://localhost:3002"
echo "  - Worker:       http://localhost:8001"
echo "  - PostgreSQL:   localhost:5434"
echo "  - Redis:        localhost:6381"
echo "  - Ollama:       http://localhost:11435"
echo "  - Grafana:      http://localhost:3003 (admin/staging123)"
echo "  - Prometheus:   http://localhost:9090"
echo ""
echo -e "${CYAN}🧪 Testing Commands:${NC}"
echo "  - Run Stage 1 tests:    ./scripts/test-stage-1.sh"
echo "  - Toggle feature flag:  ./scripts/staging-feature-toggle.sh"
echo "  - View logs:            docker-compose -f docker-compose.staging.yml logs -f"
echo "  - Stop environment:     docker-compose -f docker-compose.staging.yml down"
echo ""

# Run basic health checks
if [ "$TEST_MODE" = "true" ]; then
    echo -e "${BLUE}🔍 Running Basic Health Checks...${NC}"
    
    # Test API health
    health_response=$(curl -s "$API_URL/health" | jq -r '.status // "error"')
    if [ "$health_response" = "ok" ]; then
        echo -e "  - API Health: ${GREEN}✅ OK${NC}"
    else
        echo -e "  - API Health: ${RED}❌ Error${NC}"
    fi
    
    # Test worker health
    worker_health=$(curl -s "http://localhost:8001/health" | jq -r '.status // "error"')
    if [ "$worker_health" = "ok" ]; then
        echo -e "  - Worker Health: ${GREEN}✅ OK${NC}"
    else
        echo -e "  - Worker Health: ${RED}❌ Error${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Basic health checks completed${NC}"
fi

# Show next steps
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "  1. Access the frontend at http://localhost:3000"
echo "  2. Create a test project to validate Stage 1"
echo "  3. Monitor the PICO pipeline flow through Stages 1→2→3"
echo "  4. Check performance metrics in Grafana"
echo "  5. Test feature flag toggling"
echo ""
echo -e "${CYAN}Happy testing! 🧪${NC}"