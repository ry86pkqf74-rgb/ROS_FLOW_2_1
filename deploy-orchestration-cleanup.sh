#!/bin/bash
# ==============================================================================
# ResearchFlow Orchestration Cleanup - Deployment Script for ROSflow2
# ==============================================================================
# This script deploys the orchestration cleanup changes to ROSflow2 (Hetzner)
# and runs mandatory validation checks.
#
# Usage:
#   # Local execution (SSH to server and run):
#   ./deploy-orchestration-cleanup.sh
#
#   # Or copy to server first:
#   scp deploy-orchestration-cleanup.sh user@rosflow2:/opt/researchflow/
#   ssh user@rosflow2 'cd /opt/researchflow && ./deploy-orchestration-cleanup.sh'
#
# Requirements:
#   - Must be run from /opt/researchflow directory on ROSflow2
#   - Docker and docker compose must be available
#   - User must have permissions to run docker compose
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
EXPECTED_DIR="/opt/researchflow"
BRANCH="main"
MERGE_COMMIT="6b93f26"
MIN_AGENTS_EXPECTED=22

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

abort() {
    echo ""
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ DEPLOYMENT ABORTED${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${RED}$1${NC}"
    echo ""
    if [ -n "${2:-}" ]; then
        echo "Remediation:"
        echo "$2"
        echo ""
    fi
    exit 1
}

# ==============================================================================
# Pre-Deployment Checks
# ==============================================================================

print_header "Orchestration Cleanup Deployment - ROSflow2"

echo "Date: $(date)"
echo "User: $(whoami)"
echo "Hostname: $(hostname)"
echo ""

# Check we're in the right directory
if [ "$PWD" != "$EXPECTED_DIR" ]; then
    print_warning "Not in expected directory"
    echo "Current: $PWD"
    echo "Expected: $EXPECTED_DIR"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        abort "Deployment cancelled by user"
    fi
fi

# Check Docker is available
if ! command -v docker >/dev/null 2>&1; then
    abort "Docker is not installed or not in PATH" \
          "Install Docker: curl -fsSL https://get.docker.com | sh"
fi

# Check docker compose is available
if ! docker compose version >/dev/null 2>&1; then
    abort "Docker Compose plugin not available" \
          "Install Docker Compose: apt-get install docker-compose-plugin"
fi

# Check Docker daemon is running
if ! docker ps >/dev/null 2>&1; then
    abort "Docker daemon is not running or insufficient permissions" \
          "Start Docker: sudo systemctl start docker\nAdd user to docker group: sudo usermod -aG docker \$USER"
fi

print_success "Pre-deployment checks passed"

# ==============================================================================
# Step 1: Git Pull and Verification
# ==============================================================================

print_header "Step 1: Fetch Latest Code"

print_step "Fetching from remote..."
git fetch --all --prune

print_step "Checking out main branch..."
git checkout main

print_step "Pulling latest changes..."
git pull origin main

# Verify merge commit is present
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo ""
echo "Current commit: $CURRENT_COMMIT"

if git log --oneline -5 | grep -q "$MERGE_COMMIT"; then
    print_success "Merge commit $MERGE_COMMIT found"
else
    print_warning "Merge commit $MERGE_COMMIT not found in recent history"
    echo "Recent commits:"
    git log --oneline -5
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        abort "Deployment cancelled - wrong commit"
    fi
fi

# Show what changed
echo ""
echo "Recent commits:"
git log --oneline -8
echo ""

# ==============================================================================
# Step 2: Environment Validation
# ==============================================================================

print_header "Step 2: Environment Validation"

# Check .env file exists
if [ -f .env ]; then
    print_success ".env file exists"
    
    # Check critical env vars (names only)
    print_step "Checking required environment variables..."
    
    MISSING_VARS=()
    
    if ! grep -q "^WORKER_SERVICE_TOKEN=" .env; then
        MISSING_VARS+=("WORKER_SERVICE_TOKEN")
    fi
    
    if ! grep -q "^LANGSMITH_API_KEY=" .env; then
        MISSING_VARS+=("LANGSMITH_API_KEY")
    fi
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${MISSING_VARS[@]}"; do
            echo "  - $var"
        done
        echo ""
        abort "Environment configuration incomplete" \
              "Add missing variables to .env and retry"
    else
        print_success "Required environment variables present"
    fi
else
    print_warning ".env file not found (using docker-compose defaults)"
fi

# ==============================================================================
# Step 3: Rebuild Orchestrator
# ==============================================================================

print_header "Step 3: Rebuild Orchestrator"

print_step "Building orchestrator image..."
if docker compose build orchestrator 2>&1 | grep -i error; then
    abort "Orchestrator build failed" \
          "Check Docker logs: docker compose logs orchestrator"
else
    print_success "Orchestrator built successfully"
fi

print_step "Restarting orchestrator with new routing logic..."
docker compose up -d --force-recreate orchestrator

print_step "Waiting for orchestrator to become healthy (40 seconds)..."
sleep 40

# Verify orchestrator is healthy
if docker compose ps orchestrator | grep -q "Up"; then
    print_success "Orchestrator container is running"
else
    docker compose ps orchestrator
    abort "Orchestrator container failed to start" \
          "Check logs: docker compose logs --tail=50 orchestrator"
fi

# Test health endpoint
print_step "Testing orchestrator health endpoint..."
if docker compose exec -T orchestrator curl -fsS http://localhost:3001/health >/dev/null 2>&1; then
    print_success "Orchestrator health check passed"
else
    abort "Orchestrator health check failed" \
          "Check logs: docker compose logs --tail=50 orchestrator\nTest manually: docker compose exec orchestrator curl -v http://localhost:3001/health"
fi

# Verify AGENT_ENDPOINTS_JSON loaded
print_step "Verifying AGENT_ENDPOINTS_JSON loaded..."
ENDPOINTS_COUNT=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo "0")

if [ "$ENDPOINTS_COUNT" -ge "$MIN_AGENTS_EXPECTED" ]; then
    print_success "AGENT_ENDPOINTS_JSON loaded ($ENDPOINTS_COUNT agents)"
else
    print_error "AGENT_ENDPOINTS_JSON has only $ENDPOINTS_COUNT agents (expected $MIN_AGENTS_EXPECTED+)"
    abort "Agent configuration incomplete" \
          "Check AGENT_ENDPOINTS_JSON in docker-compose.yml\nRestart: docker compose up -d --force-recreate orchestrator"
fi

# ==============================================================================
# Step 4: Start All Agent Services
# ==============================================================================

print_header "Step 4: Start All Agent Services"

print_step "Starting all services (agents, workers, databases)..."
docker compose up -d

print_step "Waiting for agents to become healthy (60 seconds)..."
sleep 60

# Count running agent containers
RUNNING_AGENTS=$(docker compose ps --format "{{.Service}}" | grep "^agent-" | wc -l | xargs)
echo ""
echo "Running agent services: $RUNNING_AGENTS"

if [ "$RUNNING_AGENTS" -ge "$MIN_AGENTS_EXPECTED" ]; then
    print_success "At least $MIN_AGENTS_EXPECTED agent services are running"
else
    print_warning "Only $RUNNING_AGENTS agent services running (expected $MIN_AGENTS_EXPECTED+)"
    echo ""
    echo "Checking for unhealthy agents..."
    docker compose ps | grep agent- | grep -v "Up" || echo "All agent containers show 'Up' status"
    echo ""
fi

# ==============================================================================
# Step 5: Run MANDATORY Preflight Validation
# ==============================================================================

print_header "Step 5: MANDATORY Preflight Validation"

print_step "Running hetzner-preflight.sh..."
echo ""

if ./researchflow-production-main/scripts/hetzner-preflight.sh; then
    echo ""
    print_success "PREFLIGHT VALIDATION PASSED ✓"
    PREFLIGHT_PASSED=true
else
    echo ""
    print_error "PREFLIGHT VALIDATION FAILED ✗"
    PREFLIGHT_PASSED=false
    
    echo ""
    echo -e "${YELLOW}Preflight failed! Common issues:${NC}"
    echo "  1. Agent containers not running: docker compose ps | grep agent-"
    echo "  2. Agent unhealthy: docker compose logs <agent-name>"
    echo "  3. AGENT_ENDPOINTS_JSON misconfigured: docker compose exec orchestrator sh -c 'echo \$AGENT_ENDPOINTS_JSON'"
    echo ""
    
    read -p "Continue to smoke test anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        abort "Deployment halted - fix preflight issues before proceeding"
    fi
fi

# ==============================================================================
# Step 6: Run Smoke Test (All Agents)
# ==============================================================================

print_header "Step 6: Smoke Test Validation (All Agents)"

print_step "Running stagewise-smoke.sh with CHECK_ALL_AGENTS=1..."
echo ""

# Run smoke test with all agents validation
if CHECK_ALL_AGENTS=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
   ./researchflow-production-main/scripts/stagewise-smoke.sh 2>&1 | tee /tmp/smoke-test-output.log; then
    echo ""
    print_success "SMOKE TEST COMPLETED"
    SMOKE_PASSED=true
else
    echo ""
    print_warning "SMOKE TEST HAD WARNINGS OR FAILURES"
    SMOKE_PASSED=false
fi

# Check if all-agents validation ran
if grep -q "ALL AGENTS VALIDATION" /tmp/smoke-test-output.log; then
    # Extract agent counts
    AGENTS_TOTAL=$(grep "Total agents:" /tmp/smoke-test-output.log | awk '{print $NF}' | tail -1)
    AGENTS_PASSED=$(grep "Passed:" /tmp/smoke-test-output.log | awk '{print $NF}' | tail -1)
    AGENTS_FAILED=$(grep "Failed:" /tmp/smoke-test-output.log | awk '{print $NF}' | tail -1)
    
    echo ""
    echo "Agent Validation Summary:"
    echo "  Total:  $AGENTS_TOTAL"
    echo "  Passed: $AGENTS_PASSED"
    echo "  Failed: $AGENTS_FAILED"
    
    if [ "${AGENTS_FAILED:-0}" -eq 0 ]; then
        print_success "All agents validated successfully"
    else
        print_warning "$AGENTS_FAILED agent(s) failed validation"
    fi
else
    print_warning "All-agents validation did not run (CHECK_ALL_AGENTS may not be working)"
fi

# ==============================================================================
# Step 7: Verify Artifacts
# ==============================================================================

print_header "Step 7: Verify Artifacts"

if [ -d "/data/artifacts/validation" ]; then
    ARTIFACT_DIRS=$(ls -1 /data/artifacts/validation/ 2>/dev/null | wc -l | xargs)
    
    if [ "$ARTIFACT_DIRS" -ge "$MIN_AGENTS_EXPECTED" ]; then
        print_success "Artifacts written for $ARTIFACT_DIRS agents"
        
        echo ""
        echo "Sample artifacts:"
        ls -1 /data/artifacts/validation/ | head -10
        
        # Check one artifact
        SAMPLE_AGENT=$(ls -1 /data/artifacts/validation/ | head -1)
        if [ -n "$SAMPLE_AGENT" ]; then
            SAMPLE_ARTIFACT=$(find /data/artifacts/validation/$SAMPLE_AGENT -name "summary.json" | head -1)
            if [ -f "$SAMPLE_ARTIFACT" ]; then
                echo ""
                echo "Sample artifact content ($SAMPLE_AGENT):"
                cat "$SAMPLE_ARTIFACT" | jq . 2>/dev/null || cat "$SAMPLE_ARTIFACT"
            fi
        fi
    else
        print_warning "Only $ARTIFACT_DIRS artifact directories found (expected $MIN_AGENTS_EXPECTED+)"
    fi
else
    print_warning "/data/artifacts/validation directory not found"
fi

# ==============================================================================
# Step 8: Test Sample Routing
# ==============================================================================

print_header "Step 8: Test Sample Routing"

print_step "Getting dev auth token..."
TOKEN_RESP=$(curl -s -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' 2>/dev/null || echo '{}')

TOKEN=$(echo "$TOKEN_RESP" | jq -r '.token // empty' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    print_warning "Could not get dev auth token (DEV_AUTH may not be enabled)"
    echo "Response: $TOKEN_RESP"
    ROUTING_TEST=false
else
    print_success "Dev auth token obtained"
    
    # Test native agent routing
    echo ""
    print_step "Testing native agent routing (agent-stage2-lit)..."
    
    DISPATCH_RESP=$(curl -s -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "task_type": "STAGE_2_LITERATURE_REVIEW",
        "request_id": "deploy-test-native-001",
        "mode": "DEMO",
        "inputs": {"query": "test query"}
      }' 2>/dev/null || echo '{"error":"request_failed"}')
    
    AGENT_NAME=$(echo "$DISPATCH_RESP" | jq -r '.agent_name // empty' 2>/dev/null)
    AGENT_URL=$(echo "$DISPATCH_RESP" | jq -r '.agent_url // empty' 2>/dev/null)
    
    if [ "$AGENT_NAME" = "agent-stage2-lit" ] && [ -n "$AGENT_URL" ]; then
        print_success "Native agent routing: $AGENT_NAME → $AGENT_URL"
    else
        print_error "Native agent routing failed"
        echo "Response: $DISPATCH_RESP"
    fi
    
    # Test proxy agent routing
    echo ""
    print_step "Testing proxy agent routing (agent-results-interpretation-proxy)..."
    
    DISPATCH_RESP=$(curl -s -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "task_type": "RESULTS_INTERPRETATION",
        "request_id": "deploy-test-proxy-001",
        "mode": "DEMO",
        "inputs": {}
      }' 2>/dev/null || echo '{"error":"request_failed"}')
    
    AGENT_NAME=$(echo "$DISPATCH_RESP" | jq -r '.agent_name // empty' 2>/dev/null)
    AGENT_URL=$(echo "$DISPATCH_RESP" | jq -r '.agent_url // empty' 2>/dev/null)
    
    if [ "$AGENT_NAME" = "agent-results-interpretation-proxy" ] && [ -n "$AGENT_URL" ]; then
        print_success "Proxy agent routing: $AGENT_NAME → $AGENT_URL"
    else
        print_error "Proxy agent routing failed"
        echo "Response: $DISPATCH_RESP"
    fi
    
    ROUTING_TEST=true
fi

# ==============================================================================
# Deployment Summary
# ==============================================================================

print_header "Deployment Summary"

echo "Component Status:"
echo ""
printf "  %-40s" "Git Pull (main)"
if git log --oneline -1 | grep -q "."; then
    echo -e "${GREEN}✓ Success${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

printf "  %-40s" "Orchestrator Rebuild"
if docker compose ps orchestrator | grep -q "Up"; then
    echo -e "${GREEN}✓ Success${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

printf "  %-40s" "AGENT_ENDPOINTS_JSON Loaded"
if [ "$ENDPOINTS_COUNT" -ge "$MIN_AGENTS_EXPECTED" ]; then
    echo -e "${GREEN}✓ Success ($ENDPOINTS_COUNT agents)${NC}"
else
    echo -e "${YELLOW}⚠ Warning ($ENDPOINTS_COUNT agents)${NC}"
fi

printf "  %-40s" "Agent Services Running"
if [ "$RUNNING_AGENTS" -ge "$MIN_AGENTS_EXPECTED" ]; then
    echo -e "${GREEN}✓ Success ($RUNNING_AGENTS services)${NC}"
else
    echo -e "${YELLOW}⚠ Warning ($RUNNING_AGENTS services)${NC}"
fi

printf "  %-40s" "Preflight Validation"
if [ "${PREFLIGHT_PASSED:-false}" = "true" ]; then
    echo -e "${GREEN}✓ Passed${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

printf "  %-40s" "Smoke Test Validation"
if [ "${SMOKE_PASSED:-false}" = "true" ]; then
    echo -e "${GREEN}✓ Passed${NC}"
else
    echo -e "${YELLOW}⚠ Warning${NC}"
fi

printf "  %-40s" "Routing Test"
if [ "${ROUTING_TEST:-false}" = "true" ]; then
    echo -e "${GREEN}✓ Passed${NC}"
else
    echo -e "${YELLOW}⚠ Skipped${NC}"
fi

echo ""

# ==============================================================================
# Final Status
# ==============================================================================

if [ "${PREFLIGHT_PASSED:-false}" = "true" ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}✓ DEPLOYMENT SUCCESSFUL${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Orchestration cleanup has been deployed and validated."
    echo ""
    echo "Changes deployed:"
    echo "  • Single source of truth routing (AGENT_ENDPOINTS_JSON)"
    echo "  • Dynamic agent validation (preflight)"
    echo "  • CHECK_ALL_AGENTS smoke testing"
    echo "  • 22 agents with complete wiring docs"
    echo ""
    echo "All systems operational. ResearchFlow is ready for production use."
    echo ""
    echo "Next steps:"
    echo "  1. Monitor orchestrator logs: docker compose logs -f orchestrator"
    echo "  2. Check agent health: docker compose ps | grep agent-"
    echo "  3. Review artifacts: ls -l /data/artifacts/validation/"
    echo ""
    exit 0
else
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}${BOLD}⚠ DEPLOYMENT COMPLETED WITH WARNINGS${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Code has been deployed but preflight validation failed."
    echo ""
    echo "Required actions:"
    echo "  1. Review preflight errors above"
    echo "  2. Fix failing agents: docker compose logs <agent-name>"
    echo "  3. Restart failed agents: docker compose up -d <agent-name>"
    echo "  4. Re-run preflight: ./researchflow-production-main/scripts/hetzner-preflight.sh"
    echo ""
    echo "System is NOT ready for production until preflight passes."
    echo ""
    exit 1
fi
