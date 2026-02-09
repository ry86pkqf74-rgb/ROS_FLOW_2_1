#!/usr/bin/env bash
# ============================================================================
# EXECUTION SWEEP - Run on Hetzner Server
# ============================================================================
# This script validates end-to-end execution for all 31 task types
# Target: 31/31 PASS (dispatch → run for each agent)
# ============================================================================

set -euo pipefail

echo "🚀 Starting Execution Sweep Deployment..."
echo ""

# Step 1: Navigate to project directory
echo "📁 Step 1: Navigating to project directory..."
cd /opt/researchflow/ROS_FLOW_2_1 || {
  echo "❌ ERROR: Project directory not found at /opt/researchflow/ROS_FLOW_2_1"
  exit 1
}

# Step 2: Pull latest code
echo "⬇️  Step 2: Pulling latest code from main..."
git pull origin main || {
  echo "❌ ERROR: Git pull failed"
  exit 1
}

# Step 3: Verify script exists
echo "✅ Step 3: Verifying script exists..."
if [ ! -f "researchflow-production-main/hetzner-execution-sweep-all.sh" ]; then
  echo "❌ ERROR: hetzner-execution-sweep-all.sh not found"
  exit 1
fi

# Step 4: Copy script into orchestrator container
echo "📋 Step 4: Copying script into orchestrator container..."
cd researchflow-production-main
docker compose cp hetzner-execution-sweep-all.sh orchestrator:/tmp/ || {
  echo "❌ ERROR: Failed to copy script into container"
  exit 1
}

# Step 5: Prompt for WORKER_SERVICE_TOKEN
echo ""
echo "🔑 Step 5: Setting up environment..."
if [ -z "${WORKER_SERVICE_TOKEN:-}" ]; then
  echo ""
  echo "⚠️  WARNING: WORKER_SERVICE_TOKEN not set in environment"
  echo ""
  echo "Please set it before executing the sweep:"
  echo "  export WORKER_SERVICE_TOKEN='your-token-here'"
  echo ""
  echo "Or run the sweep manually with:"
  echo ""
  echo "  docker compose exec orchestrator sh -lc '"
  echo "    export ORCHESTRATOR_URL=\"http://orchestrator:3001\""
  echo "    export WORKER_SERVICE_TOKEN=\"YOUR_TOKEN\""
  echo "    export MODE=\"DEMO\""
  echo "    export RISK_TIER=\"NON_SENSITIVE\""
  echo "    export TIMEOUT_SECS=\"120\""
  echo "    chmod +x /tmp/hetzner-execution-sweep-all.sh"
  echo "    /tmp/hetzner-execution-sweep-all.sh"
  echo "  '"
  echo ""
  exit 1
fi

# Step 6: Execute the sweep
echo "🎯 Step 6: Executing sweep (this may take 5-10 minutes)..."
echo ""

docker compose exec orchestrator sh -lc "
  export ORCHESTRATOR_URL='http://orchestrator:3001'
  export WORKER_SERVICE_TOKEN='${WORKER_SERVICE_TOKEN}'
  export MODE='DEMO'
  export RISK_TIER='NON_SENSITIVE'
  export TIMEOUT_SECS='120'
  
  chmod +x /tmp/hetzner-execution-sweep-all.sh
  /tmp/hetzner-execution-sweep-all.sh
" || {
  echo "❌ ERROR: Sweep execution failed"
  exit 1
}

echo ""
echo "✅ Execution sweep completed!"
echo ""
echo "📊 Next steps:"
echo "  1. Review the pass/fail summary above"
echo "  2. Check the TSV file location printed above"
echo "  3. If any failures, check agent logs:"
echo "     docker compose logs --tail 200 <agent-name>"
echo ""
