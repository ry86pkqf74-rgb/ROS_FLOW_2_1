#!/usr/bin/env bash
# =============================================================================
# Run execution sweep V2 INSIDE the Docker Compose network (orchestrator).
# Use on Hetzner host so agent_url (e.g. http://agent-*:8000) resolves.
# No destructive actions (no restart/down/up/pull/redeploy).
# =============================================================================
set -euo pipefail

# Compose project: repo root (or set COMPOSE_DIR / COMPOSE_FILE).
# On Hetzner: COMPOSE_DIR=/opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
# If the full stack (orchestrator) is started with docker-compose.prod.yml, set COMPOSE_FILE.
COMPOSE_DIR="${COMPOSE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-}"
cd "$COMPOSE_DIR"

COMPOSE_CMD="docker compose"
[[ -n "$COMPOSE_FILE" ]] && COMPOSE_CMD="docker compose -f $COMPOSE_FILE"

echo "=== 1. Compose project & orchestrator ==="
echo "COMPOSE_DIR=$COMPOSE_DIR"
$COMPOSE_CMD ps

ORCHESTRATOR_CONTAINER="$($COMPOSE_CMD ps -q orchestrator 2>/dev/null || true)"
if [[ -z "$ORCHESTRATOR_CONTAINER" ]]; then
  echo "ERROR: No orchestrator container found. Try: $COMPOSE_CMD -f docker-compose.prod.yml ps"
  exit 1
fi
echo "Orchestrator container: $ORCHESTRATOR_CONTAINER"

echo ""
echo "=== 2. Probe shell/python inside orchestrator ==="
$COMPOSE_CMD exec -T orchestrator bash -lc 'cd /app 2>/dev/null || cd /workspace 2>/dev/null || true; pwd; ls -la; python3 --version' || {
  echo "WARNING: bash failed, trying sh..."
  $COMPOSE_CMD exec -T orchestrator sh -lc 'pwd; python3 --version'
}

SWEEP_SCRIPT="$COMPOSE_DIR/hetzner-execution-sweep-v2.py"
if [[ ! -f "$SWEEP_SCRIPT" ]]; then
  echo "ERROR: Sweep script not found: $SWEEP_SCRIPT"
  exit 1
fi

echo ""
echo "=== 3. Copy sweep script into orchestrator /tmp ==="
docker cp "$SWEEP_SCRIPT" "$ORCHESTRATOR_CONTAINER:/tmp/hetzner-execution-sweep-v2.py"

# WORKER_SERVICE_TOKEN: from env or .env in repo root
if [[ -z "${WORKER_SERVICE_TOKEN:-}" ]] && [[ -f "$COMPOSE_DIR/.env" ]]; then
  export WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' "$COMPOSE_DIR/.env" | cut -d= -f2- | tr -d '"'"')"
fi
if [[ -z "${WORKER_SERVICE_TOKEN:-}" ]] && [[ -f "$COMPOSE_DIR/.env.production" ]]; then
  export WORKER_SERVICE_TOKEN="$(grep -E '^WORKER_SERVICE_TOKEN=' "$COMPOSE_DIR/.env.production" | cut -d= -f2- | tr -d '"'"')"
fi
if [[ -z "${WORKER_SERVICE_TOKEN:-}" ]]; then
  echo "ERROR: WORKER_SERVICE_TOKEN not set and not found in .env / .env.production"
  exit 1
fi

echo ""
echo "=== 4. Run V2 sweep inside orchestrator (ORCHESTRATOR_URL=http://127.0.0.1:3001) ==="
$COMPOSE_CMD exec -T -e ORCHESTRATOR_URL=http://127.0.0.1:3001 -e WORKER_SERVICE_TOKEN -e MODE="${MODE:-DEMO}" -e RISK_TIER="${RISK_TIER:-NON_SENSITIVE}" orchestrator \
  python3 /tmp/hetzner-execution-sweep-v2.py

echo ""
echo "=== 5. TSV output path and tail (last 40 lines) ==="
$COMPOSE_CMD exec -T orchestrator sh -c 'ls -la /tmp/execution_sweep_v2_*.tsv 2>/dev/null || true'
$COMPOSE_CMD exec -T orchestrator sh -c 'tail -n 40 /tmp/execution_sweep_v2_*.tsv 2>/dev/null || true'

echo ""
echo "=== 6. Summary artifacts under /data/artifacts/validation (if volume present) ==="
# Try host path first (common volume mount)
if [[ -d /data/artifacts/validation ]]; then
  find /data/artifacts/validation -type f -name 'summary.json' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -20
else
  echo "Host path /data/artifacts/validation not found; checking worker container..."
  WORKER_CONTAINER="$($COMPOSE_CMD ps -q worker 2>/dev/null || true)"
  if [[ -n "$WORKER_CONTAINER" ]]; then
    $COMPOSE_CMD exec -T worker find /data/artifacts/validation -type f -name 'summary.json' 2>/dev/null | head -20
  else
    echo "No worker container or path; skip artifact check."
  fi
fi

echo ""
echo "=== Done. Execution gate: PASS only if 31/31 run/sync returned non-empty output. ==="
