#!/bin/bash
# ==============================================================================
# Hetzner Deployment and Validation Script
# ==============================================================================
# Performs a complete deployment cycle:
# 1. Updates code to latest main branch commit
# 2. Rebuilds and restarts orchestrator
# 3. Validates service-token dispatch authentication
# 4. Runs preflight checks
# 5. Executes comprehensive 29-agent dispatch sweep
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
EXPECTED_COMMIT="c0d31c0371afab7a0227244e1a616684d14d38b4"
PROJECT_DIR="/opt/researchflow/ROS_FLOW_2_1"
COMPOSE_DIR="${PROJECT_DIR}/researchflow-production-main"

# Function to print section headers
print_header() {
  echo ""
  echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
  echo ""
}

# Function to print success messages
print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error messages
print_error() {
  echo -e "${RED}❌ $1${NC}"
}

# Function to print info messages
print_info() {
  echo -e "${CYAN}ℹ️  $1${NC}"
}

# ==============================================================================
# STEP 1: Update Code on Hetzner
# ==============================================================================
print_header "STEP 1: Updating Code on Hetzner"

print_info "Navigating to project directory: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

print_info "Fetching all branches and pruning deleted ones..."
git fetch --all --prune

print_info "Checking out main branch..."
git checkout main

print_info "Pulling latest changes..."
git pull

print_info "Verifying commit hash..."
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Current commit: ${CURRENT_COMMIT}"
echo "Expected commit: ${EXPECTED_COMMIT}"

if [ "${CURRENT_COMMIT}" = "${EXPECTED_COMMIT}" ]; then
  print_success "Commit hash verified!"
else
  print_error "Commit hash mismatch!"
  echo "Expected: ${EXPECTED_COMMIT}"
  echo "Got:      ${CURRENT_COMMIT}"
  exit 1
fi

# ==============================================================================
# STEP 2: Rebuild and Restart Orchestrator
# ==============================================================================
print_header "STEP 2: Rebuilding and Restarting Services"

print_info "Navigating to compose directory: ${COMPOSE_DIR}"
cd "${COMPOSE_DIR}"

print_info "Building and restarting services..."
docker compose up -d --build

print_info "Waiting for services to stabilize..."
sleep 10

print_info "Checking service status..."
docker compose ps

print_success "Services restarted successfully!"

# ==============================================================================
# STEP 3: Verify Service Token Dispatch Authentication
# ==============================================================================
print_header "STEP 3: Verifying Service Token Dispatch Auth"

print_info "Reading WORKER_SERVICE_TOKEN from .env file..."
WORKER_SERVICE_TOKEN=$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")

if [ -z "${WORKER_SERVICE_TOKEN}" ]; then
  print_error "WORKER_SERVICE_TOKEN not found in .env file!"
  exit 1
fi

print_info "Testing dispatch endpoint with service token authentication..."
HTTP_RESPONSE=$(docker compose exec -T orchestrator sh -c "
  curl -sS -i \
    -X POST 'http://orchestrator:3001/api/ai/router/dispatch' \
    -H 'Authorization: Bearer ${WORKER_SERVICE_TOKEN}' \
    -H 'Content-Type: application/json' \
    -d '{
      \"task_type\": \"CLAIM_VERIFY\",
      \"request_id\": \"auth-probe-claim-verify\",
      \"mode\": \"DEMO\",
      \"risk_tier\": \"NON_SENSITIVE\",
      \"inputs\": {},
      \"budgets\": {}
    }'
" | head -n 40)

echo "${HTTP_RESPONSE}"

if echo "${HTTP_RESPONSE}" | grep -q "HTTP/1.1 200\|HTTP/2 200"; then
  print_success "Service token authentication verified!"
else
  print_error "Service token authentication failed!"
  exit 1
fi

# ==============================================================================
# STEP 4: Run Preflight Checks
# ==============================================================================
print_header "STEP 4: Running Preflight Checks"

print_info "Executing hetzner-preflight.sh..."
cd "${COMPOSE_DIR}"
chmod +x scripts/hetzner-preflight.sh
./scripts/hetzner-preflight.sh

print_success "Preflight checks passed!"

# ==============================================================================
# STEP 5: Execute 29-Agent Dispatch Sweep
# ==============================================================================
print_header "STEP 5: Executing Comprehensive Dispatch Sweep"

print_info "Preparing to test all 29 agents via dispatch endpoint..."
print_info "This will validate routing, authentication, and agent availability"
echo ""

# Export environment variables for the stagewise-smoke script
export ORCHESTRATOR_URL="http://127.0.0.1:3001"
export AUTH_HEADER="Authorization: Bearer ${WORKER_SERVICE_TOKEN}"
export CHECK_ALL_AGENTS=1
export SKIP_ADMIN_CHECKS=0

print_info "Running stagewise-smoke.sh with full agent sweep..."
cd "${COMPOSE_DIR}"
chmod +x scripts/stagewise-smoke.sh
./scripts/stagewise-smoke.sh

print_success "Dispatch sweep completed!"

# ==============================================================================
# Summary
# ==============================================================================
print_header "DEPLOYMENT AND VALIDATION COMPLETE"

print_success "All steps completed successfully!"
echo ""
echo "Summary:"
echo "  ✅ Code updated to commit: ${EXPECTED_COMMIT}"
echo "  ✅ Services rebuilt and restarted"
echo "  ✅ Service token authentication validated"
echo "  ✅ Preflight checks passed"
echo "  ✅ Comprehensive dispatch sweep completed"
echo ""
print_info "Your ResearchFlow deployment is ready for production use!"
echo ""
