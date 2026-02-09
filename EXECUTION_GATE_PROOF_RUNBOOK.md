# Execution Gate Proof — Run Sweep Inside Compose Network

**Goal:** Re-run the execution sweep so `{agent_url}/agents/run/sync` is called from **inside** the Docker Compose network (orchestrator or attached container).  
**Gate rule:** Execution gate = **PASS** only if **31/31** run/sync return non-empty output (HTTP 200 + response size > 50).

---

## Quick run on Hetzner (one script)

```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
# Set WORKER_SERVICE_TOKEN if not in .env / .env.production (script reads those if present)
./scripts/run-execution-sweep-inside-compose.sh
```

Then fill the **Final gate table** (section 6) from the script output and TSV.

---

## 1. Identify compose project and orchestrator (on Hetzner)

```bash
# Full stack lives at repo root; tools/Docker-Compose-Prod is a different minimal stack.
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

docker compose ps
# or, if you use prod file:
# docker compose -f docker-compose.prod.yml ps
```

Note the **orchestrator** container name (e.g. `orchestrator` or project-prefixed).

---

## 2. Probe orchestrator (shell + Python)

```bash
docker compose exec orchestrator bash -lc 'cd /app || cd /workspace || pwd; ls -la; python3 --version'
```

If `docker compose exec` or shell/python is unavailable, **stop** and use the fallback: a one-off container attached to the same network (see **Fallback** below).

---

## 3. Run the V2 sweep inside the orchestrator

**Option A — Use the runbook script (recommended)**

```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
export WORKER_SERVICE_TOKEN='<from .env or .env.production>'
./scripts/run-execution-sweep-inside-compose.sh
```

**Option B — Manual steps**

```bash
cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

# Copy script into container
docker cp hetzner-execution-sweep-v2.py $(docker compose ps -q orchestrator):/tmp/hetzner-execution-sweep-v2.py

# Run inside orchestrator (ORCHESTRATOR_URL so dispatch hits localhost; agent_url stays Docker DNS)
docker compose exec -e ORCHESTRATOR_URL=http://127.0.0.1:3001 -e WORKER_SERVICE_TOKEN -e MODE=DEMO -e RISK_TIER=NON_SENSITIVE orchestrator \
  python3 /tmp/hetzner-execution-sweep-v2.py
```

---

## 4. Evidence: TSV path and tail

From **inside** the orchestrator container:

```bash
docker compose exec orchestrator sh -c 'ls -la /tmp/execution_sweep_v2_*.tsv'
docker compose exec orchestrator sh -c 'tail -n 40 /tmp/execution_sweep_v2_*.tsv'
```

Or copy TSV out and inspect:

```bash
docker compose cp orchestrator:/tmp/execution_sweep_v2_$(date -u +%Y%m%d)*.tsv ./execution_sweep_v2_latest.tsv
# then: cat execution_sweep_v2_latest.tsv
```

---

## 5. Summary artifacts (optional)

```bash
# If /data/artifacts is on the host
find /data/artifacts/validation -type f -name summary.json -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -20

# If only in worker container
docker compose exec worker find /data/artifacts/validation -type f -name 'summary.json' 2>/dev/null | head -20
```

---

## 6. Final gate table (deliverable)

Fill after the run. **Execution gate = PASS only if 31/31 run/sync returned non-empty output.**

| Gate        | Condition                          | Result | Evidence |
|------------|-------------------------------------|--------|----------|
| **Dispatch** | 31/31 dispatch return agent_url   | —      | TSV column `dispatch_http` = 200, `agent_url` non-empty |
| **Execution** | 31/31 run/sync HTTP 200, response &gt; 50 chars | **PASS** / **FAIL** | TSV columns `run_http`, `latency_ms`, `pass_fail`; summary line: `SUMMARY: X/31 PASS` |

### TSV → Markdown table (example)

From the TSV (header + rows):

```
task_type	dispatch_http	agent_name	agent_url	run_http	latency_ms	pass_fail	error_preview
ARTIFACT_AUDIT	200	artifact-auditor	http://...	200	245	PASS	
...
```

Produce a table:

| task_type | dispatch_http | agent_name | run_http | latency_ms | pass_fail | error_preview |
|-----------|---------------|------------|----------|------------|-----------|----------------|
| ARTIFACT_AUDIT | 200 | artifact-auditor | 200 | 245 | PASS | |
| ... | ... | ... | ... | ... | ... | ... |

**Execution gate:** **PASS** if and only if the TSV summary line shows `31/31 PASS` and every row has `pass_fail=PASS`.

---

## Fallback: one-off container on compose network

If `docker compose exec orchestrator` is unavailable or the orchestrator has no shell/python:

1. Get the compose network name:  
   `docker network ls` and find the network used by the stack (e.g. `researchflow-production-main_backend`).
2. Run a temporary container with the script and env, attached to that network:

   ```bash
   docker run --rm -it --network researchflow-production-main_backend \
     -e ORCHESTRATOR_URL=http://orchestrator:3001 \
     -e WORKER_SERVICE_TOKEN="$WORKER_SERVICE_TOKEN" \
     -v /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main/hetzner-execution-sweep-v2.py:/tmp/hetzner-execution-sweep-v2.py \
     python:3.11-alpine python3 /tmp/hetzner-execution-sweep-v2.py
   ```

3. **Requires explicit approval** (as per guardrails: no destructive actions without approval; one-off run is non-destructive but creates a temporary container).

---

## Guardrails (reminder)

- No destructive actions (restart/down/up/pull/redeploy/delete/prune/volume removal) without explicit approval.
- No pasting secrets (tokens, env files).
- Minimal changes; prefer read-only checks.
