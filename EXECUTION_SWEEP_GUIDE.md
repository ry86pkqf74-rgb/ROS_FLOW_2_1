# Execution Sweep: End-to-End Workflow Validation

## Purpose
This script validates that all 31 task types can complete full execution:
1. **Dispatch** → Router resolves task_type to agent_url  
2. **Run** → Agent executes and returns results

Previous validation (31/31) only tested routing. This validates actual execution.

## What It Catches
- Missing API keys / secrets
- Model connectivity failures  
- Runtime crashes masked by health checks
- Agent crashloops
- Unreachable agent services

## Script Location
```
researchflow-production-main/hetzner-execution-sweep-all.sh
```

## Execution Method 1: Inside Docker Network (RECOMMENDED)

Run from inside the orchestrator container where DNS resolution works:

```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

docker compose exec orchestrator sh -lc '
  export ORCHESTRATOR_URL="http://orchestrator:3001"
  export WORKER_SERVICE_TOKEN="<your-token>"
  export MODE="DEMO"
  export RISK_TIER="NON_SENSITIVE"
  
  /bin/sh /path/to/hetzner-execution-sweep-all.sh
'
```

### Copy Script into Container First (if needed)
```bash
docker compose cp hetzner-execution-sweep-all.sh orchestrator:/tmp/
docker compose exec orchestrator chmod +x /tmp/hetzner-execution-sweep-all.sh

docker compose exec orchestrator sh -lc '
  export ORCHESTRATOR_URL="http://orchestrator:3001"
  export WORKER_SERVICE_TOKEN="<your-token>"
  export MODE="DEMO"
  export RISK_TIER="NON_SENSITIVE"
  
  /tmp/hetzner-execution-sweep-all.sh
'
```

## Execution Method 2: From Host

Only if host can resolve agent DNS names (usually only works if you've configured dnsmasq or similar):

```bash
cd researchflow-production-main

export ORCHESTRATOR_URL="http://127.0.0.1:3001"
export WORKER_SERVICE_TOKEN="<your-token>"
export MODE="DEMO"
export RISK_TIER="NON_SENSITIVE"

./hetzner-execution-sweep-all.sh
```

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ORCHESTRATOR_URL` | `http://127.0.0.1:3001` | Yes | Orchestrator endpoint |
| `WORKER_SERVICE_TOKEN` | - | **YES** | Auth token for dispatch endpoint |
| `MODE` | `DEMO` | No | Execution mode |
| `RISK_TIER` | `NON_SENSITIVE` | No | Risk classification |
| `TIMEOUT_SECS` | `120` | No | Timeout per request |

## Output

The script produces:
1. **Live output** to terminal (one line per task)
2. **TSV file** at `/tmp/execution_sweep_<timestamp>.tsv`

### TSV Columns
```
task_type dispatch_http agent_name agent_url run_http latency_ms pass_fail error_preview
```

### Success Criteria
- `dispatch_http = 200` 
- Agent URL returned
- `run_http = 200`
- Response body > 50 characters (non-trivial output)

## Expected Results

### Pass (31/31)
```
ARTIFACT_AUDIT              200  artifact-auditor          http://artifact-auditor:3020  200  1234  PASS
CLAIM_VERIFY                200  claim-verifier            http://claim-verifier:3021    200  987   PASS
...
```

### Partial Failure Example
```
ARTIFACT_AUDIT              200  artifact-auditor          http://artifact-auditor:3020  500  -     FAIL  RUN_FAIL Internal server error...
CLAIM_VERIFY                500  -                         -                             -    -     FAIL  DISPATCH_FAIL Agent not found...
```

## Troubleshooting Failures

### 1. Check Orchestrator Logs
```bash
docker compose logs --tail 200 orchestrator | grep -i error
```

### 2. Check Failing Agent Logs
If `ARTIFACT_AUDIT` fails:
```bash
docker compose logs --tail 200 artifact-auditor
```

### 3. Test Individual Dispatch
```bash
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $WORKER_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "ARTIFACT_AUDIT",
    "request_id": "manual-test-001",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "inputs": {},
    "budgets": {}
  }'
```

### 4. Test Individual Agent Run
```bash
curl -X POST http://<agent-url>/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "ARTIFACT_AUDIT",
    "request_id": "manual-test-001",
    "mode": "DEMO",
    "risk_tier": "NON_SENSITIVE",
    "inputs": {},
    "budgets": {}
  }'
```

## Common Issues

### Issue: WORKER_SERVICE_TOKEN not set
**Solution**: Export the token before running
```bash
export WORKER_SERVICE_TOKEN="your-actual-token-here"
```

### Issue: Agent DNS not resolvable from host
**Solution**: Run from inside orchestrator container (Method 1)

### Issue: All agents return 500
**Likely causes**:
- Missing `ANTHROPIC_API_KEY` or other LLM credentials
- Database connection failures (check Redis/Postgres)
- Network isolation (agents can't reach external APIs)

Check:
```bash
docker compose exec orchestrator env | grep -i api_key
docker compose exec artifact-auditor env | grep -i api_key
```

### Issue: Specific agents timeout
**Likely causes**:
- Agent is crashlooping (check `docker compose ps`)
- Agent is healthy but slow (increase `TIMEOUT_SECS`)
- Agent stuck on startup (check logs for initialization errors)

Check health:
```bash
docker compose ps | grep artifact-auditor
curl http://127.0.0.1:3020/health  # if port mapped
```

## What to Report

After running the sweep, provide:

1. **Summary line**: e.g., "27/31 PASS, 4 FAIL"
2. **Failures section** (printed at end)
3. **TSV file location** (e.g., `/tmp/execution_sweep_20260208T143022Z.tsv`)
4. **Top 3 failing agent logs**:
   ```bash
   docker compose logs --tail 200 <agent-service-name>
   ```

## Next Steps After Success

Once you achieve **31/31 PASS**:
- ✅ Routing validated (previous step)
- ✅ Execution validated (this step)
- 🎯 **Ready for integration testing with real payloads**

Move to:
- End-to-end IMRAD workflow tests
- Performance benchmarking
- Load testing
- Production deployment

## Script Details

The script:
1. Iterates through all 31 task types
2. For each task:
   - POSTs to `/api/ai/router/dispatch` (with auth)
   - Parses response to extract `agent_url`
   - POSTs to `{agent_url}/agents/run/sync` (no auth)
   - Records HTTP codes, latency, pass/fail
3. Outputs live progress + saves TSV
4. Prints failure summary

**Security**: 
- Does NOT log `WORKER_SERVICE_TOKEN` 
- Uses internal Docker network URLs (not exposed to internet)
- Runs with DEMO mode (non-production data)
