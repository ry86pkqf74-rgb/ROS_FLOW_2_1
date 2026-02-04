#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.test.yml"

TIMEOUT_SECONDS="${TEST_ENV_TIMEOUT_SECONDS:-180}"
POLL_INTERVAL_SECONDS="${TEST_ENV_POLL_INTERVAL_SECONDS:-2}"

log() {
  printf '[test-env] %s\n' "$*" >&2
}

die() {
  log "ERROR: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    docker-compose -f "$COMPOSE_FILE" "$@"
  fi
}

wait_for_healthy() {
  local start_ts now_ts elapsed unhealthy
  start_ts="$(date +%s)"

  while true; do
    unhealthy="$(compose ps --format json 2>/dev/null | jq -r '.[] | select(.Health != "healthy") | .Service' | tr '\n' ' ' || true)"

    if [[ -z "${unhealthy// }" ]]; then
      log "all services healthy"
      return 0
    fi

    now_ts="$(date +%s)"
    elapsed="$((now_ts - start_ts))"

    if (( elapsed >= TIMEOUT_SECONDS )); then
      log "timeout waiting for healthy services (${TIMEOUT_SECONDS}s). Unhealthy: ${unhealthy}"
      compose ps || true
      compose logs --no-color || true
      return 1
    fi

    log "waiting for healthy services... unhealthy: ${unhealthy}"
    sleep "$POLL_INTERVAL_SECONDS"
  done
}

run_migrations_and_seed() {
  # Prefer repo-provided migration/seed scripts if present.
  if [[ -x "$ROOT_DIR/scripts/migrate.sh" ]]; then
    log "running migrations via scripts/migrate.sh"
    (cd "$ROOT_DIR" && DATABASE_URL="postgres://researchflow:researchflow@localhost:5433/researchflow_test" ./scripts/migrate.sh)
  elif [[ -x "$ROOT_DIR/scripts/db-migrate.sh" ]]; then
    log "running migrations via scripts/db-migrate.sh"
    (cd "$ROOT_DIR" && DATABASE_URL="postgres://researchflow:researchflow@localhost:5433/researchflow_test" ./scripts/db-migrate.sh)
  else
    log "no migration script found; skipping migrations"
  fi

  log "seeding test data via seed-data.sql"
  compose exec -T postgres-test sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' < "$ROOT_DIR/tests/fixtures/seed-data.sql"
}

main() {
  require_cmd docker
  require_cmd jq

  log "starting test environment"
  compose up -d --remove-orphans

  log "waiting for health checks"
  wait_for_healthy

  run_migrations_and_seed

  log "test environment ready"
}

main "$@"
