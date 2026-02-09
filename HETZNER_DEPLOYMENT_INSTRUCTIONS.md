# Hetzner Deployment Instructions

## Quick Deploy (Automated)

The fastest way to deploy and validate everything:

```bash
# SSH into Hetzner
ssh root@<hetzner-ip>

# Run the all-in-one deployment script
cd /root/ROS_FLOW_2_1
chmod +x scripts/hetzner-deploy-and-validate.sh
./scripts/hetzner-deploy-and-validate.sh
```

This script will:
1. ✅ Update code to commit `c0d31c0` on main branch
2. ✅ Rebuild and restart Docker services
3. ✅ Validate service-token dispatch authentication
4. ✅ Run preflight system checks
5. ✅ Execute comprehensive 29-agent dispatch sweep

---

## Manual Step-by-Step (Alternative)

If you prefer to run each step manually:

### Step 1: Update Code on Hetzner

```bash
cd /root/ROS_FLOW_2_1
git fetch --all --prune
git checkout main
git pull
git rev-parse HEAD   # Should output: c0d31c0371afab7a0227244e1a616684d14d38b4
```

### Step 2: Rebuild and Restart Services

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main
docker compose up -d --build
docker compose ps
```

Wait ~10 seconds for services to stabilize.

### Step 3: Verify Service Token Dispatch Auth

Test from inside the Docker network:

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main

# Extract WORKER_SERVICE_TOKEN from .env
WORKER_SERVICE_TOKEN=$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")

# Test dispatch endpoint
docker compose exec orchestrator sh -lc "
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
" | head -n 40
```

**Expected:** HTTP 200 response with dispatch confirmation.

### Step 4: Run Preflight Checks

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main
./scripts/hetzner-preflight.sh
```

This validates:
- Docker daemon and Compose availability
- System resources (disk, memory)
- Container health status
- Network connectivity between services
- Basic endpoint responsiveness

### Step 5: Execute Comprehensive Dispatch Sweep

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main

# Set environment variables
export ORCHESTRATOR_URL="http://127.0.0.1:3001"
WORKER_SERVICE_TOKEN=$(grep -E '^WORKER_SERVICE_TOKEN=' .env | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d "'")
export AUTH_HEADER="Authorization: Bearer ${WORKER_SERVICE_TOKEN}"
export CHECK_ALL_AGENTS=1

# Run the comprehensive sweep
./scripts/stagewise-smoke.sh
```

This tests all 29 agents by dispatching tasks through the orchestrator:

**Native Agents (15):**
- Stage 2 Pipeline: Literature Review, Screen, Extract, Synthesize
- Literature & Retrieval: Lit Retrieval, Lit Triage
- RAG: Ingest, Retrieve
- Writing: Intro, Methods, Results, Discussion
- Verification: Claim Verify
- Evidence Analysis: Evidence Synthesis
- Policy: Policy Review

**LangSmith Proxy Agents (14):**
- Results Interpretation
- Clinical Manuscript Writer
- Section Drafter
- Peer Review Simulator
- Bias Detection
- Dissemination Formatter
- Performance Optimizer
- Journal Guidelines Cache
- Compliance Auditor
- Artifact Auditor
- Resilience Architecture Advisor
- Multilingual Literature Processor
- Clinical Model Fine-Tuner
- Hypothesis Refiner

---

## Troubleshooting

### Service Token Not Found

If you get "WORKER_SERVICE_TOKEN not found in .env":

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main
cat .env | grep WORKER_SERVICE_TOKEN
```

Ensure the variable is set in your `.env` file.

### 401 Unauthorized on Dispatch

If dispatch returns 401:
- Verify WORKER_SERVICE_TOKEN is correctly set in `.env`
- Check that the serviceAuthMiddleware is enabled in the orchestrator
- Ensure you're using the Bearer token format: `Authorization: Bearer <token>`

### Docker Containers Not Starting

```bash
cd /root/ROS_FLOW_2_1/researchflow-production-main
docker compose logs orchestrator --tail=100
docker compose logs worker --tail=100
```

### Preflight Checks Failing

Common issues:
- **Disk space:** Check with `df -h`
- **Memory:** Check with `free -h`
- **Port conflicts:** Check with `netstat -tulpn | grep -E '3001|8000|8001'`

---

## Post-Deployment Verification

After successful deployment, verify:

✅ All containers are running:
```bash
docker compose ps
```

✅ Orchestrator is healthy:
```bash
curl http://127.0.0.1:3001/api/health
```

✅ Worker is healthy:
```bash
curl http://127.0.0.1:8000/health
```

✅ Dispatch routing works:
```bash
# Use the service token test from Step 3
```

---

## Next Steps

After validation:
1. Monitor Sentry for any runtime errors
2. Check LangSmith traces for agent execution quality
3. Review orchestrator logs for dispatch patterns
4. Test end-to-end research workflows

For production traffic, ensure:
- Rate limiting is configured
- Monitoring alerts are active
- Backup procedures are in place
- SSL/TLS is enabled for public endpoints
