# Orchestration Cleanup - Validation Commands Quick Reference

**Branch:** `feat/import-dissemination-formatter`  
**Status:** ✅ Ready for validation

---

## Local Development (Before Push)

### 1. TypeScript Syntax Check
```bash
cd researchflow-production-main/services/orchestrator
npm run lint -- src/routes/ai-router.ts
# Expect: Only pre-existing warnings, no new errors
```

### 2. Verify Git Status
```bash
git status
git log --oneline -6

# Should show 5 commits:
# 00ab019 docs: add orchestration cleanup summary
# 7af50f3 docs(agents): generate wiring docs
# 6b6385b feat(smoke): add CHECK_ALL_AGENTS validation
# 1d3e06a feat(preflight): dynamically derive mandatory agents
# 82bb086 feat(orchestrator): enforce AGENT_ENDPOINTS_JSON
```

### 3. Check for Secrets (Gitleaks)
```bash
# Run gitleaks on the diff
git diff main | docker run -i zricethezav/gitleaks:latest protect --no-git --verbose --redact --stdin

# Expect: No secrets found
```

### 4. Push to Remote
```bash
git push origin feat/import-dissemination-formatter
```

---

## On ROSflow2 (Hetzner) - Deployment Validation

### Pre-Deployment

```bash
# 1. SSH to server
ssh user@rosflow2

# 2. Navigate to repo
cd /opt/researchflow

# 3. Pull latest
git fetch --all --prune
git checkout feat/import-dissemination-formatter
git pull --ff-only

# 4. Check current status
docker compose ps | grep orchestrator
docker compose ps | grep agent- | wc -l
# Should show 22 agent services

# 5. Verify AGENT_ENDPOINTS_JSON in .env (if using .env file)
grep AGENT_ENDPOINTS_JSON .env 2>/dev/null || echo "Using docker-compose.yml default"
```

### Deployment Steps

```bash
# 1. Rebuild orchestrator
docker compose build orchestrator

# 2. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 3. Wait for healthy (30-40 seconds)
sleep 40

# 4. Verify orchestrator is healthy
docker compose ps orchestrator
docker compose exec orchestrator curl -f http://localhost:3001/health

# 5. Verify AGENT_ENDPOINTS_JSON loaded
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool | head -30
# Should show JSON with 22 agents
```

### Mandatory Validation (Preflight)

```bash
# Run preflight checks (MANDATORY before production use)
./researchflow-production-main/scripts/hetzner-preflight.sh

# Expected output:
# ════════════════════════════════════════════════════════════════
# Mandatory Agent Fleet Validation
# ════════════════════════════════════════════════════════════════
# 
# Fetching AGENT_ENDPOINTS_JSON from orchestrator...
#   AGENT_ENDPOINTS_JSON           ✓ PASS - valid JSON with 22 agent(s)
# 
# Dynamically derived 22 mandatory agents from AGENT_ENDPOINTS_JSON
# 
# Validating required environment variables...
#   WORKER_SERVICE_TOKEN           ✓ PASS - configured
#   LANGSMITH_API_KEY              ✓ PASS - configured
# 
# Validating 22 mandatory agents...
# 
# Checking: agent-bias-detection-proxy
#   agent-bias-detection-proxy [Registry]    ✓ PASS - http://agent-bias-detection-proxy:8000
#   agent-bias-detection-proxy [Container]   ✓ PASS - running
#   agent-bias-detection-proxy [Health]      ✓ PASS - responding
# 
# [... 21 more agents ...]
# 
# ✓ All 22 mandatory agents are running and healthy!
# 
# ════════════════════════════════════════════════════════════════
# Preflight Summary
# ════════════════════════════════════════════════════════════════
# Results: 65 passed, 0 warnings, 0 failed
# 
# ✓ ALL PREFLIGHT CHECKS PASSED!
# ✓ System is ready for ResearchFlow deployment.

# Exit code should be 0
echo $?
```

**If preflight fails:**
```bash
# Check which agents failed
docker compose ps | grep -E 'unhealthy|exited|restarting'

# View logs for failed agent
docker compose logs --tail=100 <failed-agent-name>

# Restart failed agent
docker compose up -d --force-recreate <failed-agent-name>

# Re-run preflight
./researchflow-production-main/scripts/hetzner-preflight.sh
```

### Optional Validation (Smoke Tests)

```bash
# Run smoke test with all agents validation
CHECK_ALL_AGENTS=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./researchflow-production-main/scripts/stagewise-smoke.sh

# Expected output:
# [15] ALL AGENTS VALIDATION (CHECK_ALL_AGENTS=1)
# 
# Dynamically validating all agents from AGENT_ENDPOINTS_JSON...
# Found 22 agents in AGENT_ENDPOINTS_JSON
# 
# ────────────────────────────────────────────────────────────────
# Testing agent: agent-stage2-lit
# ────────────────────────────────────────────────────────────────
#   Agent URL: http://agent-stage2-lit:8000
#   ✓ Container running: agent-stage2-lit
#   Testing orchestrator routing...
#   ✓ Orchestrator dispatch successful
#   ✓ Wrote artifact: /data/artifacts/validation/agent-stage2-lit/20260208T120000Z/summary.json
# 
# [... 21 more agents ...]
# 
# ════════════════════════════════════════════════════════════════
# ALL AGENTS VALIDATION SUMMARY
# ════════════════════════════════════════════════════════════════
#   Total agents:  22
#   Passed:        22
#   Failed:        0
# 
#   ✓ ALL AGENTS VALIDATED SUCCESSFULLY
```

### Verify Artifacts Written

```bash
# List validation artifacts
ls -l /data/artifacts/validation/

# Should show directories for all 22 agents:
# agent-bias-detection-proxy/
# agent-clinical-manuscript-proxy/
# agent-discussion-writer/
# agent-dissemination-formatter-proxy/
# agent-evidence-synthesis/
# [... etc ...]

# Check one agent's artifact
cat /data/artifacts/validation/agent-stage2-lit/*/summary.json | jq .

# Should show:
# {
#   "agentKey": "agent-stage2-lit",
#   "timestamp": "20260208T120000Z",
#   "ok": true,
#   ...
# }
```

---

## Sample Per-Agent Tests

### Test Native Agent (agent-stage2-lit)

```bash
# Get dev token
TOKEN=$(curl -s -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq -r '.token')

# Dispatch STAGE_2_LITERATURE_REVIEW task
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "STAGE_2_LITERATURE_REVIEW",
    "request_id": "manual-lit-001",
    "mode": "DEMO",
    "inputs": {
      "query": "diabetes mellitus type 2",
      "max_results": 5
    }
  }' | jq .

# Expected response:
# {
#   "dispatch_type": "agent",
#   "agent_name": "agent-stage2-lit",
#   "agent_url": "http://agent-stage2-lit:8000",
#   "budgets": {},
#   "rag_plan": {},
#   "request_id": "manual-lit-001"
# }
```

### Test LangSmith Proxy Agent (agent-results-interpretation-proxy)

```bash
# Dispatch RESULTS_INTERPRETATION task
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "manual-results-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": {
        "primary_outcome": {
          "variable": "blood_pressure_reduction",
          "intervention_mean": 142,
          "control_mean": 155,
          "p_value": 0.003,
          "effect_size": 1.2
        }
      },
      "study_context": "RCT comparing drug X vs placebo"
    }
  }' | jq .

# Expected response:
# {
#   "dispatch_type": "agent",
#   "agent_name": "agent-results-interpretation-proxy",
#   "agent_url": "http://agent-results-interpretation-proxy:8000",
#   "budgets": {},
#   "rag_plan": {},
#   "request_id": "manual-results-001"
# }
```

### Test Another LangSmith Proxy (agent-clinical-manuscript-proxy)

```bash
# Dispatch CLINICAL_MANUSCRIPT_WRITE task
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_MANUSCRIPT_WRITE",
    "request_id": "manual-manuscript-001",
    "mode": "DEMO",
    "inputs": {
      "study_summary": "Randomized controlled trial of 200 patients...",
      "evidence_synthesis": {
        "grade_assessment": "Moderate quality",
        "key_findings": [...]
      }
    }
  }' | jq .

# Expected response:
# {
#   "dispatch_type": "agent",
#   "agent_name": "agent-clinical-manuscript-proxy",
#   "agent_url": "http://agent-clinical-manuscript-proxy:8000",
#   ...
# }
```

---

## Troubleshooting

### Problem: Preflight fails with "AGENT_ENDPOINTS_JSON not set"

**Solution:**
```bash
# Check orchestrator environment
docker compose exec orchestrator env | grep AGENT_ENDPOINTS_JSON

# If missing, verify docker-compose.yml
grep AGENT_ENDPOINTS_JSON docker-compose.yml

# Restart orchestrator
docker compose up -d --force-recreate orchestrator
```

### Problem: Preflight fails on agent X health check

**Solution:**
```bash
# Check agent container
docker compose ps | grep agent-X

# View logs
docker compose logs --tail=50 agent-X

# Check health directly
docker compose exec agent-X curl -v http://localhost:8000/health

# Restart agent
docker compose restart agent-X
```

### Problem: Router returns "Agent X not found in AGENT_ENDPOINTS_JSON"

**Solution:**
```bash
# The error message will list all available agents
# Compare agent_name from error with keys in AGENT_ENDPOINTS_JSON

# If using proxy, ensure key includes "-proxy" suffix
# Example:
#   ❌ CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript'
#   ✅ CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript-proxy'

# Fix in services/orchestrator/src/routes/ai-router.ts
# Then rebuild and restart orchestrator
```

### Problem: Smoke test shows "Container not running"

**Solution:**
```bash
# Start all agents
docker compose up -d

# Verify all are running
docker compose ps | grep agent- | grep -v Up
# Should show nothing if all are Up

# If specific agent is down:
docker compose up -d <agent-name>
docker compose logs <agent-name>
```

---

## Quick Health Check

Run this one-liner to verify all agents are accessible:

```bash
# On ROSflow2
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | \
  python3 -c '
import json, sys, subprocess
endpoints = json.load(sys.stdin)
failed = []
for key, url in sorted(endpoints.items()):
    service = url.split("//")[1].split(":")[0]
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "curl", "-fsS", "http://localhost:8000/health"],
        capture_output=True, text=True
    )
    status = "✓" if result.returncode == 0 else "✗"
    print(f"{status} {key:45} {url}")
    if result.returncode != 0:
        failed.append(key)
if failed:
    print(f"\n✗ {len(failed)} agent(s) failed: {', '.join(failed)}")
    sys.exit(1)
else:
    print(f"\n✓ All {len(endpoints)} agents healthy!")
'
```

---

## Next Steps

1. ✅ All phases committed
2. ⏳ Push to remote: `git push origin feat/import-dissemination-formatter`
3. ⏳ Deploy to ROSflow2
4. ⏳ Run preflight (mandatory)
5. ⏳ Run smoke test (optional)
6. ⏳ Create PR to main

---

**Generated:** 2026-02-08  
**For questions:** See ORCHESTRATION_CLEANUP_COMPLETE.md
