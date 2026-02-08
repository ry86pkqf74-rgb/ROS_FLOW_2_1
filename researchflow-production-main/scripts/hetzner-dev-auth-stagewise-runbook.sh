#!/usr/bin/env bash
# Runbook: enable dev-auth on Hetzner (staging only), mint JWT, run stagewise smoke.
# Run from host in the directory containing the compose file (e.g. ROS_FLOW_2_1/researchflow-production-main).
# Guardrail: do not use in production.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
COMPOSE_DIR="$(pwd)"

# --- Step 1 — Confirm whether dev-auth is currently enabled
step1() {
  echo "=== Step 1 — Confirm dev-auth status ==="
  docker compose exec -T orchestrator sh -lc 'echo ENABLE_DEV_AUTH=$ENABLE_DEV_AUTH; node -e "console.log(\"NODE_ENV=\"+process.env.NODE_ENV)"'
  echo "GET /api/dev-auth/login (expect 404):"
  curl -i -sS "http://127.0.0.1:3001/api/dev-auth/login" || true
  echo ""
}

# --- Step 2 — Temporarily enable dev-auth (staging only)
step2() {
  echo "=== Step 2 — Enable dev-auth and restart orchestrator ==="
  if [ -n "${PRODUCTION_GUARD:-}" ]; then
    echo "PRODUCTION_GUARD set — refusing to enable dev-auth. Unset or run manually."
    exit 1
  fi
  if [ ! -f .env ]; then
    echo "No .env found in $COMPOSE_DIR. Create .env and set ENABLE_DEV_AUTH=true, then run:"
    echo "  docker compose up -d --force-recreate orchestrator"
    exit 1
  fi
  if ! grep -q 'ENABLE_DEV_AUTH=true' .env 2>/dev/null; then
    echo "Ensure .env contains: ENABLE_DEV_AUTH=true"
    echo "Then run: docker compose up -d --force-recreate orchestrator"
    read -r -p "Have you set ENABLE_DEV_AUTH=true and want to restart orchestrator? [y/N] " ans
    case "$ans" in
      [yY]*) ;;
      *) echo "Skipping restart. Run manually when ready."; return 0 ;;
    esac
  fi
  docker compose up -d --force-recreate orchestrator
  docker compose ps orchestrator
  docker compose logs --tail=80 --timestamps orchestrator
}

# --- Step 3 — Mint JWT using dev-auth
step3() {
  echo "=== Step 3 — Mint JWT via dev-auth ==="
  DEV_USER_ID="${DEV_USER_ID:-e2e-test-user-00000000-0000-0000-0000-000000000001}"
  TOKEN_JSON=$(curl -fsS -X POST "http://127.0.0.1:3001/api/dev-auth/login" -H "X-Dev-User-Id: $DEV_USER_ID")
  echo "$TOKEN_JSON"
  if command -v jq &>/dev/null; then
    ACCESS_TOKEN=$(echo "$TOKEN_JSON" | jq -r .accessToken)
  else
    ACCESS_TOKEN=$(python3 -c 'import sys,json; print(json.load(sys.stdin).get("accessToken",""))' <<< "$TOKEN_JSON")
  fi
  if [ -z "$ACCESS_TOKEN" ]; then
    echo "Failed to get accessToken. Is dev-auth enabled and orchestrator up?" >&2
    exit 1
  fi
  echo "Minted access token OK"
  export ACCESS_TOKEN
}

# --- Step 4 — Run stagewise smoke test
step4() {
  echo "=== Step 4 — Stagewise smoke test ==="
  export ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
  export AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"
  if ! ./scripts/stagewise-smoke.sh; then
    echo "--- Smoke failed: recent orchestrator logs ---"
    docker compose logs --tail=200 --timestamps orchestrator
    echo "--- Worker logs ---"
    docker compose logs --tail=200 --timestamps worker
    exit 1
  fi
}

# --- Step 5 — (Optional) Disable dev-auth again
step5() {
  echo "=== Step 5 — Disable dev-auth (optional) ==="
  echo "To disable: set ENABLE_DEV_AUTH=false in .env then run:"
  echo "  docker compose up -d --force-recreate orchestrator"
}

# Main
main() {
  echo "Compose dir: $COMPOSE_DIR"
  step1
  echo ""
  read -r -p "Enable dev-auth and restart orchestrator? [y/N] " ans
  case "$ans" in
    [yY]*) step2 ;;
    *)     echo "Skipping Step 2. Ensure ENABLE_DEV_AUTH=true and orchestrator restarted before Step 3." ;;
  esac
  echo ""
  step3
  echo ""
  step4
  echo ""
  step5
}

# Allow running a single step: ./hetzner-dev-auth-stagewise-runbook.sh 3
if [ $# -ge 1 ]; then
  case "$1" in
    1) step1 ;;
    2) step2 ;;
    3) step3; export ACCESS_TOKEN ;;
    4) [ -z "$ACCESS_TOKEN" ] && step3; step4 ;;
    5) step5 ;;
    *) echo "Usage: $0 [1|2|3|4|5]" >&2; exit 1 ;;
  esac
else
  main
fi
