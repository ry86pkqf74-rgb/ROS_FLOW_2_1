#!/bin/bash
# ==============================================================================
# Remote Deployment Wrapper - Execute on ROSflow2 from Local Machine
# ==============================================================================
# This script copies the deployment script to ROSflow2 and executes it remotely.
#
# Usage:
#   ./deploy-remote.sh [SSH_HOST]
#
# Example:
#   ./deploy-remote.sh user@rosflow2
#   ./deploy-remote.sh root@192.168.1.100
#
# Environment variables:
#   ROSFLOW2_HOST - SSH host (default: user@rosflow2)
#   ROSFLOW2_DIR  - Remote directory (default: /opt/researchflow)
# ==============================================================================

set -euo pipefail

# Configuration
ROSFLOW2_HOST="${1:-${ROSFLOW2_HOST:-user@rosflow2}}"
ROSFLOW2_DIR="${ROSFLOW2_DIR:-/opt/researchflow}"
LOCAL_SCRIPT="deploy-orchestration-cleanup.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Remote Deployment to ROSflow2${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Target Host:      $ROSFLOW2_HOST"
echo "Target Directory: $ROSFLOW2_DIR"
echo "Local Script:     $LOCAL_SCRIPT"
echo ""

# Verify local script exists
if [ ! -f "$LOCAL_SCRIPT" ]; then
          echo -e "${RED}✗ ERROR: $LOCAL_SCRIPT not found${NC}"
      echo ""
      echo "Run this script from the repository root directory"
      echo "  Hint: cd \$(git rev-parse --show-toplevel)"
      exit 1
  fi

# Test SSH connectivity
echo -e "${GREEN}▶ Testing SSH connectivity...${NC}"
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$ROSFLOW2_HOST" "echo 'SSH OK'" 2>/dev/null | grep -q "SSH OK"; then
    echo -e "${YELLOW}⚠ SSH connection test failed (may require password/key)${NC}"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
else
    echo -e "${GREEN}✓ SSH connection OK${NC}"
fi

# Copy deployment script to server
echo ""
echo -e "${GREEN}▶ Copying deployment script to server...${NC}"
if scp "$LOCAL_SCRIPT" "${ROSFLOW2_HOST}:${ROSFLOW2_DIR}/" 2>&1; then
    echo -e "${GREEN}✓ Deployment script copied${NC}"
else
    echo -e "${RED}✗ Failed to copy deployment script${NC}"
    exit 1
fi

# Execute deployment script on server
echo ""
echo -e "${GREEN}▶ Executing deployment on ROSflow2...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

ssh -t "$ROSFLOW2_HOST" "cd $ROSFLOW2_DIR && chmod +x $LOCAL_SCRIPT && ./$LOCAL_SCRIPT"
EXIT_CODE=$?

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Remote deployment completed successfully!${NC}"
    echo ""
    echo "ResearchFlow orchestration cleanup is now live on ROSflow2."
    echo ""
    echo "Next steps:"
    echo "  1. Monitor logs: ssh $ROSFLOW2_HOST 'cd $ROSFLOW2_DIR && docker compose logs -f orchestrator'"
    echo "  2. Check agents: ssh $ROSFLOW2_HOST 'cd $ROSFLOW2_DIR && docker compose ps | grep agent-'"
    echo "  3. View artifacts: ssh $ROSFLOW2_HOST 'ls -l /data/artifacts/validation/'"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Remote deployment failed (exit code: $EXIT_CODE)${NC}"
    echo ""
    echo "Check the output above for errors."
    echo ""
    echo "Manual intervention may be required:"
    echo "  ssh $ROSFLOW2_HOST"
    echo "  cd $ROSFLOW2_DIR"
    echo "  docker compose logs --tail=100 orchestrator"
    echo "  ./researchflow-production-main/scripts/hetzner-preflight.sh"
    echo ""
fi

exit $EXIT_CODE
