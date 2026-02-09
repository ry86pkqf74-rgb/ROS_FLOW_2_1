# Quick Deploy: Execution Sweep (31/31)

## From Hetzner Host → Orchestrator Container

```bash
# 1. Navigate to project directory
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

# 2. Copy script into container
docker compose cp hetzner-execution-sweep-all.sh orchestrator:/tmp/
docker compose exec orchestrator chmod +x /tmp/hetzner-execution-sweep-all.sh

# 3. Run the sweep
docker compose exec orchestrator sh -lc '
  export ORCHESTRATOR_URL="http://orchestrator:3001"
  export WORKER_SERVICE_TOKEN="__REPLACE_WITH_YOUR_TOKEN__"
  export MODE="DEMO"
  export RISK_TIER="NON_SENSITIVE"
  export TIMEOUT_SECS="120"
  
  /tmp/hetzner-execution-sweep-all.sh
'

# 4. (Optional) If you need to check a specific failing agent
docker compose logs --tail 200 <agent-service-name>
```

## One-Liner (if script already on host)

```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main && \
docker compose cp hetzner-execution-sweep-all.sh orchestrator:/tmp/ && \
docker compose exec orchestrator sh -lc 'export ORCHESTRATOR_URL="http://orchestrator:3001" WORKER_SERVICE_TOKEN="__TOKEN__" MODE="DEMO" RISK_TIER="NON_SENSITIVE"; /tmp/hetzner-execution-sweep-all.sh'
```

## Expected Output

```
task_type                        dispatch_http  agent_name                    agent_url                                      run_http  latency_ms  pass_fail  error_preview
ARTIFACT_AUDIT                   200            artifact-auditor              http://artifact-auditor:3020                   200       1245        PASS       
CLAIM_VERIFY                     200            claim-verifier                http://claim-verifier:3021                     200       987         PASS       
CLINICAL_BIAS_DETECTION          200            clinical-bias-detector        http://clinical-bias-detector:3022             200       1532        PASS       
...

Saved results: /tmp/execution_sweep_20260208T143022Z.tsv
Failures:
- SOME_TASK => RUN_FAIL Connection refused
```

## Target: 31/31 PASS ✅

Count passes:
```bash
# Inside container after run
awk -F'\t' 'NR>1 && $7=="PASS"' /tmp/execution_sweep_*.tsv | wc -l
```

## Troubleshooting Top 3 Failures

```bash
# Get the 3 most common failure types
docker compose exec orchestrator sh -c 'awk -F"\t" "NR>1 && \$7==\"FAIL\"{print \$1}" /tmp/execution_sweep_*.tsv | head -3'

# Check their logs
docker compose logs --tail 200 artifact-auditor
docker compose logs --tail 200 claim-verifier  
docker compose logs --tail 200 clinical-bias-detector
```

## What to Share Back

1. Pass/Fail count: `X/31 PASS`
2. Output of "Failures:" section
3. TSV file path
4. Logs for top 3 failing agents (if any fail)
