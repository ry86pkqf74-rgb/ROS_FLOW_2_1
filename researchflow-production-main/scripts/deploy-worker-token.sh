#!/bin/bash
# ==============================================================================
# Deploy WORKER_SERVICE_TOKEN to Hetzner Production Server
# ==============================================================================
# This script:
# 1. Generates a secure random token
# 2. Updates .env with WORKER_SERVICE_TOKEN
# 3. Recreates orchestrator and worker containers
# 4. Verifies the token is set  
# 5. Runs stagewise smoke test to confirm authentication works
#
# Usage:
#   ./scripts/deploy-worker-token.sh
#
# Prerequisites:
#   - SSH access configured as 'researchflow-hetzner'
#   - Server deployment directory: /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_header "Deploying WORKER_SERVICE_TOKEN to Production"

echo "This will:"
echo "  1. Generate a secure random token (64 hex chars)"
echo "  2. Update .env on researchflow-hetzner"
echo "  3. Recreate orchestrator and worker containers"
echo "  4. Verify the token is properly set"
echo "  5. Run stagewise smoke test to confirm"
echo ""
read -r -p "Continue? [y/N] " response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Aborted."
    exit 0
fi

print_header "Step 1: Generate Token"

# Generate token locally
TOKEN=$(openssl rand -hex 32)
print_success "Generated 64-character hex token: ${TOKEN:0:16}..."

print_header "Step 2-5: Deploy and Verify on Server"

# Execute all steps on remote server
ssh researchflow-hetzner bash << EOF
set -euo pipefail

# Colors for remote output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

echo -e "\${BLUE}[Server] Updating .env with WORKER_SERVICE_TOKEN\${NC}"

# Backup existing .env
if [ -f .env ]; then
    cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)
    echo -e "\${GREEN}✓ Backed up existing .env\${NC}"
fi

# Update or append WORKER_SERVICE_TOKEN
if grep -q '^WORKER_SERVICE_TOKEN=' .env 2>/dev/null; then
    # Token exists, replace it
    sed -i.tmp 's/^WORKER_SERVICE_TOKEN=.*/WORKER_SERVICE_TOKEN=$TOKEN/' .env
    rm -f .env.tmp
    echo -e "\${GREEN}✓ Updated existing WORKER_SERVICE_TOKEN in .env\${NC}"
else
    # Token doesn't exist, append it
    echo "" >> .env
    echo "# Worker service authentication token" >> .env
    echo "WORKER_SERVICE_TOKEN=$TOKEN" >> .env
    echo -e "\${GREEN}✓ Added WORKER_SERVICE_TOKEN to .env\${NC}"
fi

echo ""
echo -e "\${BLUE}[Server] Recreating containers\${NC}"

# Recreate orchestrator
docker compose up -d --force-recreate orchestrator
sleep 3
echo -e "\${GREEN}✓ Recreated orchestrator\${NC}"

# Recreate worker
docker compose up -d --force-recreate worker
sleep 3
echo -e "\${GREEN}✓ Recreated worker\${NC}"

echo ""
echo -e "\${BLUE}[Server] Verifying token is set in orchestrator\${NC}"

# Check if token is set
TOKEN_CHECK=\$(docker compose exec -T orchestrator sh -c 'echo \${WORKER_SERVICE_TOKEN:+SET}' 2>/dev/null || echo "")
TOKEN_LEN=\$(docker compose exec -T orchestrator sh -c 'echo \${WORKER_SERVICE_TOKEN} | wc -c' 2>/dev/null | tr -d ' ' || echo "0")

if [ "\$TOKEN_CHECK" = "SET" ] && [ "\$TOKEN_LEN" -gt 10 ]; then
    echo -e "\${GREEN}✓ WORKER_SERVICE_TOKEN is SET in orchestrator\${NC}"
    echo -e "\${GREEN}✓ Token length: \$TOKEN_LEN characters\${NC}"
else
    echo -e "\${RED}✗ WORKER_SERVICE_TOKEN is NOT properly set!\${NC}"
    echo "  TOKEN_CHECK: \$TOKEN_CHECK"
    echo "  TOKEN_LEN: \$TOKEN_LEN"
    exit 1
fi

echo ""
echo -e "\${BLUE}[Server] Container status\${NC}"
docker compose ps orchestrator worker

echo ""
echo -e "\${BLUE}[Server] Running stagewise smoke test\${NC}"
echo ""

# Run stagewise smoke test with dev auth
export DEV_AUTH=true
export SKIP_ADMIN_CHECKS=1

if bash scripts/stagewise-smoke.sh 2>&1 | tee /tmp/stagewise-smoke.out; then
    echo ""
    echo -e "\${GREEN}═══════════════════════════════════════════════════════════════\${NC}"
    echo -e "\${GREEN}✓✓✓ DEPLOYMENT SUCCESSFUL ✓✓✓\${NC}"
    echo -e "\${GREEN}═══════════════════════════════════════════════════════════════\${NC}"
    echo ""
    echo "Token deployment completed successfully!"
    echo "Stagewise smoke test PASSED."
    
    # Check for authentication status in logs
    echo ""
    echo -e "\${BLUE}Checking authentication status in recent logs...\${NC}"
    if docker compose logs --tail=100 orchestrator 2>/dev/null | grep -i "authenticated" | tail -5; then
        echo ""
        echo -e "\${GREEN}✓ Found authentication logs above\${NC}"
    else
        echo -e "\${YELLOW}⚠ No obvious authentication logs found (may be normal)\${NC}"
    fi
else
    echo ""
    echo -e "\${RED}═══════════════════════════════════════════════════════════════\${NC}"
    echo -e "\${RED}✗✗✗ DEPLOYMENT VERIFICATION FAILED ✗✗✗\${NC}"
    echo -e "\${RED}═══════════════════════════════════════════════════════════════\${NC}"
    echo ""
    echo "Stagewise smoke test FAILED. Checking logs for errors..."
    echo ""
    
    # Show recent orchestrator logs
    echo -e "\${YELLOW}Recent orchestrator logs:\${NC}"
    docker compose logs --tail=50 orchestrator | grep -E "(authenticated|403|401|WORKER_SERVICE_TOKEN|dispatch)" || true
    
    echo ""
    echo "Full smoke test output saved to: /tmp/stagewise-smoke.out"
    echo ""
    echo -e "\${RED}Please investigate the failure before proceeding.\${NC}"
    exit 1
fi
EOF

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    print_header "✓ All Steps Completed Successfully"
    print_success "WORKER_SERVICE_TOKEN deployed and verified"
    print_success "Containers recreated"
    print_success "Stagewise smoke test passed"
    echo ""
    echo "Next steps:"
    echo "  1. Review the authentication logs above"
    echo "  2. Commit the updated preflight and smoke scripts (see below)"
    echo "  3. Run: git push origin main"
else
    print_header "✗ Deployment Failed"
    print_error "Check the error messages above"
    print_warning "The .env was backed up before modification"
    echo ""
    echo "To restore:"
    echo "  ssh researchflow-hetzner 'cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main && cp .env.backup.* .env'"
    exit 1
fi
