#!/usr/bin/env bash
# Run E2E tests against the Docker deployment.
# Usage:
#   ./scripts/run-docker-e2e.sh           # start Docker if needed, then run tests
#   ./scripts/run-docker-e2e.sh --no-up   # assume stack is already up

set -e

NO_UP=""
for arg in "$@"; do
  if [ "$arg" = "--no-up" ]; then
    NO_UP=1
  fi
done

BASE_URL="${PLAYWRIGHT_BASE_URL:-http://localhost:5173}"
API_URL="${API_URL:-http://localhost:3001}"

if [ -z "$NO_UP" ]; then
  echo "Starting Docker stack..."
  docker compose up -d
  echo "Waiting for services (orchestrator, worker, web)..."
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf "$API_URL/health" >/dev/null 2>&1; then
      echo "Orchestrator is up."
      break
    fi
    [ $i -eq 10 ] && { echo "Orchestrator did not become healthy."; exit 1; }
    sleep 3
  done
  if ! curl -sf "$BASE_URL" >/dev/null 2>&1; then
    echo "Waiting for web at $BASE_URL..."
    sleep 5
  fi
fi

export PLAYWRIGHT_BASE_URL="$BASE_URL"
export API_URL="$API_URL"
echo "Running E2E: docker-deployment-live.spec.ts (BASE_URL=$BASE_URL, API_URL=$API_URL)"
npx playwright test tests/e2e/docker-deployment-live.spec.ts "$@"
