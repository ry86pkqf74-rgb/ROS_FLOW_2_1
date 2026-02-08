# Deployment Scripts - Orchestration Cleanup

**Status:** ✅ Ready to execute  
**Target:** ROSflow2 (Hetzner)  
**Branch:** main (merged from feat/import-dissemination-formatter)

---

## 📦 Available Scripts

### 1. `deploy-orchestration-cleanup.sh` - On-Server Deployment

**Purpose:** Executes deployment directly on ROSflow2 server  
**Location:** Run on ROSflow2 at `/opt/researchflow`  
**Duration:** ~5-10 minutes

**What it does:**
- ✅ Pulls latest code from main branch
- ✅ Rebuilds orchestrator with new routing logic
- ✅ Starts all agent services
- ✅ Runs mandatory preflight validation
- ✅ Runs smoke test with CHECK_ALL_AGENTS=1
- ✅ Verifies artifact writes
- ✅ Tests sample routing (native + proxy agents)
- ✅ Provides deployment summary
- ✅ Auto-validates all 22 agents

**Usage on ROSflow2:**
```bash
# SSH to server
ssh user@rosflow2

# Navigate to repo
cd /opt/researchflow

# Copy script if needed
# (or git pull will get it from repo)

# Execute deployment
./deploy-orchestration-cleanup.sh

# Or with logging
./deploy-orchestration-cleanup.sh 2>&1 | tee deployment-$(date +%Y%m%d-%H%M%S).log
```

**Exit codes:**
- `0` - Deployment successful, all validations passed
- `1` - Deployment failed or validations failed

---

### 2. `deploy-remote.sh` - Remote Deployment from Local Machine

**Purpose:** Deploy to ROSflow2 from your local machine via SSH  
**Location:** Run locally from project root  
**Duration:** ~5-10 minutes + SSH time

**What it does:**
- ✅ Tests SSH connectivity
- ✅ Copies deployment script to server
- ✅ Executes deployment script remotely
- ✅ Streams output to your terminal
- ✅ Returns server exit code

**Usage locally:**
```bash
# From project root (/Users/ros/Desktop/ROS_FLOW_2_1)
./deploy-remote.sh user@rosflow2

# With custom environment
ROSFLOW2_HOST=root@192.168.1.100 \
ROSFLOW2_DIR=/opt/researchflow \
  ./deploy-remote.sh

# With logging
./deploy-remote.sh user@rosflow2 2>&1 | tee remote-deploy-$(date +%Y%m%d-%H%M%S).log
```

**Environment variables:**
- `ROSFLOW2_HOST` - SSH host (default: user@rosflow2)
- `ROSFLOW2_DIR` - Remote directory (default: /opt/researchflow)

---

## 🎯 Quick Start

### Option A: Deploy from Local Machine (Recommended)

```bash
# Navigate to project root
cd /Users/ros/Desktop/ROS_FLOW_2_1

# Execute remote deployment
./deploy-remote.sh user@rosflow2

# Wait for completion (~5-10 min)
# Script will show live output from server
```

### Option B: Deploy Directly on Server

```bash
# SSH to server
ssh user@rosflow2

# Navigate to repo
cd /opt/researchflow

# Pull latest (includes deployment scripts)
git pull origin main

# Execute deployment
./deploy-orchestration-cleanup.sh
```

---

## 📋 What Gets Validated

### Mandatory Validation (Preflight)

The `hetzner-preflight.sh` script validates:

1. **AGENT_ENDPOINTS_JSON Configuration**
   - Must be valid JSON
   - Must have 22+ agents
   - All URLs must be http:// or https://

2. **Environment Variables**
   - WORKER_SERVICE_TOKEN (required)
   - LANGSMITH_API_KEY (required for proxy agents)

3. **All 22 Agents** (dynamically from AGENT_ENDPOINTS_JSON)
   - Container is running
   - Health endpoint responds
   - URL format is valid

**Hard-fail if any check fails** - deployment is blocked.

---

### Optional Validation (Smoke Test)

The `stagewise-smoke.sh` with `CHECK_ALL_AGENTS=1` validates:

1. **Orchestrator Routing**
   - Dispatch requests route correctly
   - Agent names resolve to URLs
   - No routing errors

2. **Artifact Writes**
   - `/data/artifacts/validation/<agentKey>/` created
   - `summary.json` written per agent
   - Contains request/response/status

3. **End-to-End Flow**
   - Orchestrator → Agent routing works
   - All 22 agents accessible
   - Summary report (passed/failed counts)

**Non-blocking** - warnings only, provides visibility.

---

## 🔍 Monitoring Deployment

### During Deployment

```bash
# Watch logs in separate terminal
ssh user@rosflow2
cd /opt/researchflow
docker compose logs -f orchestrator
```

### After Deployment

```bash
# Check all services
docker compose ps

# View orchestrator logs
docker compose logs --tail=100 orchestrator

# Check agent health
for agent in $(docker compose ps --format "{{.Service}}" | grep "^agent-"); do
  echo "Testing $agent..."
  docker compose exec -T "$agent" curl -fsS http://localhost:8000/health || echo "  ✗ Failed"
done

# View artifacts
ls -lR /data/artifacts/validation/ | head -50
```

---

## 🚨 Rollback Procedure

If deployment fails, rollback to previous state:

```bash
# On ROSflow2
cd /opt/researchflow

# Find previous commit
git log --oneline -10

# Rollback to commit before merge
git checkout <previous-commit>

# Or rollback to a specific tag/branch
git checkout <stable-tag>

# Rebuild orchestrator
docker compose build orchestrator
docker compose up -d --force-recreate orchestrator

# Verify
./researchflow-production-main/scripts/hetzner-preflight.sh
```

---

## 📊 Expected Output

### Successful Deployment

```
════════════════════════════════════════════════════════════════
✓ DEPLOYMENT SUCCESSFUL
════════════════════════════════════════════════════════════════

Orchestration cleanup has been deployed and validated.

Changes deployed:
  • Single source of truth routing (AGENT_ENDPOINTS_JSON)
  • Dynamic agent validation (preflight)
  • CHECK_ALL_AGENTS smoke testing
  • 22 agents with complete wiring docs

All systems operational. ResearchFlow is ready for production use.

Next steps:
  1. Monitor orchestrator logs: docker compose logs -f orchestrator
  2. Check agent health: docker compose ps | grep agent-
  3. Review artifacts: ls -l /data/artifacts/validation/
```

### Preflight Summary

```
════════════════════════════════════════════════════════════════
Mandatory Agent Fleet Validation
════════════════════════════════════════════════════════════════

✓ AGENT_ENDPOINTS_JSON: valid JSON with 22 agent(s)

Validating required environment variables...
  WORKER_SERVICE_TOKEN           ✓ PASS - configured
  LANGSMITH_API_KEY              ✓ PASS - configured

Validating 22 mandatory agents...

Checking: agent-stage2-lit
  agent-stage2-lit [Registry]    ✓ PASS - http://agent-stage2-lit:8000
  agent-stage2-lit [Container]   ✓ PASS - running
  agent-stage2-lit [Health]      ✓ PASS - responding

[... 21 more agents ...]

✓ All 22 mandatory agents are running and healthy!

════════════════════════════════════════════════════════════════
Preflight Summary
════════════════════════════════════════════════════════════════
Results: 65 passed, 0 warnings, 0 failed

✓ ALL PREFLIGHT CHECKS PASSED!
✓ System is ready for ResearchFlow deployment.
```

### Smoke Test Summary

```
════════════════════════════════════════════════════════════════
[15] ALL AGENTS VALIDATION (CHECK_ALL_AGENTS=1)
════════════════════════════════════════════════════════════════

Found 22 agents in AGENT_ENDPOINTS_JSON

Testing agent: agent-stage2-lit
  Agent URL: http://agent-stage2-lit:8000
  ✓ Container running: agent-stage2-lit
  Testing orchestrator routing...
  ✓ Orchestrator dispatch successful
  ✓ Wrote artifact: /data/artifacts/validation/agent-stage2-lit/20260208T123456Z/summary.json

[... 21 more agents ...]

════════════════════════════════════════════════════════════════
ALL AGENTS VALIDATION SUMMARY
════════════════════════════════════════════════════════════════
  Total agents:  22
  Passed:        22
  Failed:        0

  ✓ ALL AGENTS VALIDATED SUCCESSFULLY
════════════════════════════════════════════════════════════════
```

---

## 🔧 Troubleshooting

### SSH Connection Failed

```bash
# Test SSH manually
ssh user@rosflow2 "echo 'Connection OK'"

# Check SSH config
cat ~/.ssh/config | grep rosflow2

# Use explicit key
ssh -i ~/.ssh/id_rsa user@rosflow2
```

### Deployment Script Fails on Server

```bash
# SSH to server manually
ssh user@rosflow2

# Navigate to directory
cd /opt/researchflow

# Check what went wrong
tail -100 deployment-*.log

# Run preflight manually
./researchflow-production-main/scripts/hetzner-preflight.sh

# Check specific agent
docker compose logs --tail=50 <failing-agent>
```

### Preflight Fails

**Most common issues:**

1. **Agent container not running**
   ```bash
   docker compose up -d <agent-name>
   docker compose logs <agent-name>
   ```

2. **Health endpoint not responding**
   ```bash
   docker compose exec <agent-name> curl -v http://localhost:8000/health
   docker compose restart <agent-name>
   ```

3. **AGENT_ENDPOINTS_JSON misconfigured**
   ```bash
   docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool
   ```

---

## 📈 Post-Deployment Verification

### Quick Health Check (One-Liner)

Run on ROSflow2:

```bash
cd /opt/researchflow && docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | \
  python3 -c '
import json, sys, subprocess
endpoints = json.load(sys.stdin)
failed = []
for key, url in sorted(endpoints.items()):
    service = url.split("//")[1].split(":")[0]
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "curl", "-fsS", "http://localhost:8000/health"],
        capture_output=True, text=True, timeout=5
    )
    status = "✓" if result.returncode == 0 else "✗"
    print(f"{status} {key:45} {url}")
    if result.returncode != 0:
        failed.append(key)
if failed:
    print(f"\n✗ {len(failed)} agent(s) unhealthy: {', '.join(failed)}")
    sys.exit(1)
else:
    print(f"\n✓ All {len(endpoints)} agents healthy!")
'
```

---

## 📚 Related Documentation

- **ORCHESTRATION_CLEANUP_COMPLETE.md** - Complete implementation guide
- **VALIDATION_COMMANDS_QUICK_REF.md** - Command reference
- **IMPLEMENTATION_SUMMARY.md** - Changes summary
- **docs/agents/<agent-key>/wiring.md** - Per-agent wiring guides

---

**Last Updated:** 2026-02-08  
**Status:** Ready for deployment to ROSflow2
