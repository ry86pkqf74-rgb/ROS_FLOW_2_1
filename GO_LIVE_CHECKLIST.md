# ResearchFlow Go-Live Checklist
**Purpose:** Repeatable validation checklist for Hetzner production deployments  
**Target:** Zero-ambiguity ship gate  
**Last Updated:** February 9, 2026

---

## Prerequisites (Before You Start)

- [ ] SSH access to Hetzner server: `root@178.156.139.210`
- [ ] Git commit SHA documented for deployment
- [ ] Production `.env` file prepared with real credentials (no placeholders)
- [ ] Docker and Docker Compose installed on server

---

## Part 1: Core Infrastructure Health

### 1.1 Docker Environment
```bash
ssh root@178.156.139.210
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
```

**Checks:**
- [ ] Docker daemon running: `docker ps` returns successfully
- [ ] Docker Compose available: `docker compose version`
- [ ] Disk space adequate: `df -h` shows < 80% usage on `/`
- [ ] Memory available: `free -h` shows sufficient free memory (> 2GB)

---

### 1.2 Git SHA Verification
```bash
cd /opt/researchflow/ROS_FLOW_2_1
git rev-parse HEAD
git log -1 --oneline
```

**Record:**
- [ ] Deployed SHA: `_______________`
- [ ] Commit message: `_______________`
- [ ] Matches intended deployment target: YES / NO

---

### 1.3 Environment Configuration
```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
```

**Critical Variables (must be set):**
- [ ] `WORKER_SERVICE_TOKEN` - Service authentication token
- [ ] `POSTGRES_PASSWORD` - Database password
- [ ] `POSTGRES_USER` - Database user
- [ ] `POSTGRES_DB` - Database name

**Verify (without exposing values):**
```bash
grep -q "^WORKER_SERVICE_TOKEN=" .env && echo "✓ WORKER_SERVICE_TOKEN set" || echo "✗ MISSING"
grep -q "^POSTGRES_PASSWORD=" .env && echo "✓ POSTGRES_PASSWORD set" || echo "✗ MISSING"
```

**Optional (for full functionality):**
- [ ] `LANGSMITH_API_KEY` - LangSmith integration (if using)
- [ ] `TAVILY_API_KEY` - Tavily search (if using)
- [ ] `GOOGLE_DOCS_API_KEY` - Google Docs integration (if using)

---

## Part 2: Container Health

### 2.1 All Services Running
```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
docker compose ps
```

**Core Services (must be healthy):**
- [ ] `orchestrator` - Up and healthy
- [ ] `worker` - Up and healthy
- [ ] `web` - Up and healthy
- [ ] `postgres` - Up and healthy
- [ ] `redis` - Up and healthy
- [ ] `collab` - Up and healthy
- [ ] `guideline-engine` - Up and healthy

**Agent Count:**
- [ ] Running agents: `docker compose ps | grep -c "agent-"` = **27+** expected

**Check for crash loops:**
```bash
docker compose ps | grep -i "restarting\|unhealthy"
```
- [ ] No services in restart loop or unhealthy state

---

### 2.2 Health Endpoints
```bash
# Orchestrator health
curl -f http://localhost:3001/health || echo "FAIL"

# Worker health (if exposed)
curl -f http://localhost:8000/health || echo "FAIL"
```

**Results:**
- [ ] Orchestrator health: HTTP 200
- [ ] Worker health: HTTP 200 or not exposed (OK)

---

## Part 3: Authentication & Routing

### 3.1 Service Token Authentication
```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
TOKEN=$(grep "^WORKER_SERVICE_TOKEN=" .env | cut -d= -f2)

curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"task_type": "LIT_RETRIEVAL", "mode": "DEMO", "risk_tier": "NON_SENSITIVE", "input": {"query": "test"}}' \
  -w "\nHTTP Status: %{http_code}\n"
```

**Result:**
- [ ] HTTP Status: **200** (authenticated dispatch successful)
- [ ] Response contains `agent_name` field
- [ ] Response contains `agent_url` field

---

### 3.2 Preflight Validation Artifacts
```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
./scripts/hetzner-preflight.sh
```

**Verify:**
- [ ] Script completes without errors
- [ ] Artifacts created: `find /data/artifacts/validation -name summary.json | wc -l` = **20+**
- [ ] Timestamp recent: `ls -lt /data/artifacts/validation/*/summary.json | head -1`

---

## Part 4: End-to-End Execution Sweep

### 4.1 Run Sweep from Inside Docker Network
```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

# Copy script into orchestrator container
docker compose cp hetzner-execution-sweep-v2.py orchestrator:/tmp/

# Get WORKER_SERVICE_TOKEN from .env
TOKEN=$(grep "^WORKER_SERVICE_TOKEN=" .env | cut -d= -f2)

# Run sweep from inside container
docker compose exec orchestrator sh -c "
export ORCHESTRATOR_URL='http://orchestrator:3001'
export MODE='DEMO'
export RISK_TIER='NON_SENSITIVE'
export TIMEOUT_SECS='120'
export WORKER_SERVICE_TOKEN='$TOKEN'
python3 /tmp/hetzner-execution-sweep-v2.py 2>&1
"
```

**Results:**
- [ ] Dispatch phase: **31/31 PASS** (100%)
- [ ] Run phase: **≥ 25/31 PASS** (≥ 80%)
- [ ] TSV file created: `/tmp/execution_sweep_v2_*.tsv`

**Copy results back:**
```bash
docker compose cp orchestrator:/tmp/execution_sweep_v2_*.tsv /tmp/
```

**Record:**
- [ ] Total PASS count: `___/31`
- [ ] Pass rate: `___%`
- [ ] TSV path: `_______________`

---

### 4.2 Analyze Common Failures (if any)
```bash
# Get failing task types
docker compose exec orchestrator sh -c \
  'awk -F"\t" "NR>1 && \$7==\"FAIL\"{print \$1}" /tmp/execution_sweep_v2_*.tsv'
```

**Common acceptable failures:**
- [ ] LangSmith-dependent agents (if `LANGSMITH_API_KEY` not configured)
  - `RESILIENCE_ARCHITECTURE`
- [ ] Transient DNS resolution errors ("Try again") - rerun if > 3 failures

**Record failing agents:**
```
1. _______________
2. _______________
3. _______________
```

---

## Part 5: Ship Gate Decision

### 5.1 Required Gates (All Must Pass)

- [ ] **Infrastructure:** All core services healthy (orchestrator, worker, postgres, redis)
- [ ] **Authentication:** Dispatch with WORKER_SERVICE_TOKEN returns HTTP 200
- [ ] **Artifacts:** Preflight validation created ≥ 20 summary.json files
- [ ] **Dispatch:** 31/31 task types route correctly (100%)
- [ ] **Execution:** ≥ 25/31 tasks complete successfully (≥ 80%)
- [ ] **Stability:** No crash loops or unhealthy containers

### 5.2 Optional (Nice to Have)

- [ ] **SHA alignment:** Hetzner SHA matches GitHub main HEAD
- [ ] **LangSmith:** All LangSmith agents passing (requires API key)
- [ ] **100% sweep:** 31/31 execution sweep passing

---

## Part 6: Post-Deployment Verification

### 6.1 Quick Smoke Tests
```bash
# Check orchestrator logs for errors
docker compose logs orchestrator --tail 50 | grep -i error

# Check worker logs for errors
docker compose logs worker --tail 50 | grep -i error

# Verify agent routing table loaded
docker compose logs orchestrator | grep "Agent routing initialized"
```

**Results:**
- [ ] No critical errors in orchestrator logs
- [ ] No critical errors in worker logs
- [ ] Agent routing table loaded successfully

---

### 6.2 Document Deployment
```bash
cat > /opt/researchflow/ROS_FLOW_2_1/DEPLOYMENT_$(date +%Y%m%d).txt << EOF
Deployment Date: $(date -u)
Git SHA: $(cd /opt/researchflow/ROS_FLOW_2_1 && git rev-parse HEAD)
Execution Sweep: [PASS_COUNT]/31 PASS
Environment: Production (Hetzner)
Deployed By: [YOUR_NAME]
Notes: [ANY_SPECIAL_NOTES]
EOF
```

- [ ] Deployment record created

---

## Part 7: Rollback Plan (If Needed)

### 7.1 Quick Rollback Steps
```bash
cd /opt/researchflow/ROS_FLOW_2_1

# 1. Checkout previous working commit
git checkout [PREVIOUS_SHA]

# 2. Pull updated images (if image changes)
cd researchflow-production-main
docker compose pull

# 3. Restart services
docker compose down
docker compose up -d

# 4. Verify health
docker compose ps
```

---

## Ship Decision

**Date:** _______________  
**Deployed SHA:** _______________  
**Deployer:** _______________

**Status:** ✅ SHIP / ⚠️ HOLD / ❌ ROLLBACK

**Notes:**
```




```

---

## Quick Reference Commands

### Health Check One-Liner
```bash
ssh root@178.156.139.210 'cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main && docker compose ps | grep -E "(orchestrator|worker|postgres|redis)" | grep -c healthy' | xargs -I {} echo "Healthy core services: {}/4+ expected"
```

### Full Validation One-Liner
```bash
ssh root@178.156.139.210 'cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main && \
docker compose ps | grep -c healthy && \
curl -sf http://localhost:3001/health && echo "✓ Health OK" && \
TOKEN=$(grep WORKER_SERVICE_TOKEN .env | cut -d= -f2) && \
curl -sf -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '\''{"task_type":"LIT_RETRIEVAL","mode":"DEMO","risk_tier":"NON_SENSITIVE","input":{"query":"test"}}'\'' \
  -o /dev/null && echo "✓ Auth OK"'
```

---

## Success Criteria Summary

**Minimum viable deployment:**
- ✅ 4+ core services healthy
- ✅ Orchestrator health endpoint OK
- ✅ Authenticated dispatch returns HTTP 200
- ✅ Execution sweep ≥ 25/31 PASS (80%)

**Production-ready deployment:**
- ✅ All minimum criteria
- ✅ Preflight artifacts present (20+ summary.json)
- ✅ No crash loops or unhealthy containers
- ✅ Execution sweep 31/31 PASS (100%) OR failures documented and acceptable

---

## Maintenance Tasks

### Weekly Health Check
```bash
# Run every Monday
ssh root@178.156.139.210 'cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main && \
  docker compose ps && \
  df -h && \
  free -h'
```

### Monthly Full Validation
```bash
# Run execution sweep + preflight every month
# See Part 4 for commands
```

### Log Rotation
```bash
# Check log sizes
docker system df

# Prune old logs if needed
docker system prune -a --volumes -f
```

---

**Last validated:** February 9, 2026  
**Next validation due:** March 9, 2026
