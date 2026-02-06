#!/bin/sh
# ==============================================================================
# ResearchFlow Stack Doctor - Stack health diagnosis (dev UX)
# ==============================================================================
# Usage: ./scripts/doctor.sh [COMPOSE_FILE]
#
# Prints a concise diagnosis:
#   - docker compose ps summary
#   - unhealthy services + last 100 log lines per unhealthy service
#   - duplicate/Created containers for chromadb, agent-policy-review, agent-stage2-lit
#   - Redis reachability from inside compose
#
# Exit: 0 if all required services healthy, nonzero otherwise.
# POSIX shell, minimal deps, safe (no destructive actions).
# ==============================================================================

set -e

# Optional: run from repo root or pass COMPOSE_FILE
COMPOSE_FILE="${1:-docker-compose.yml}"
if [ -n "${COMPOSE_FILE}" ] && ! [ -f "${COMPOSE_FILE}" ]; then
    # Try script dir / repo root
    SCRIPT_DIR="${0%/*}"
    if [ -z "${SCRIPT_DIR}" ] || [ "$SCRIPT_DIR" = "$0" ]; then
        SCRIPT_DIR="."
    fi
    ROOT="${SCRIPT_DIR}/.."
    if [ -f "${ROOT}/${COMPOSE_FILE}" ]; then
        cd "${ROOT}"
    fi
fi
if ! [ -f "${COMPOSE_FILE}" ]; then
    echo "doctor.sh: ${COMPOSE_FILE}: no such file. Run from repo root or pass path to compose file." 1>&2
    exit 2
fi

# Prefer docker compose (v2), fallback to docker-compose (v1)
COMPOSE_CMD="docker compose -f ${COMPOSE_FILE}"
if ! docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose -f ${COMPOSE_FILE}"
fi

REDIS_PASSWORD="${REDIS_PASSWORD:-redis-dev-password}"
LOG_TAIL="${LOG_TAIL:-100}"
EXIT_CODE=0
TMP_UNHEALTHY="/tmp/doctor_unhealthy_$$"
trap 'rm -f "${TMP_UNHEALTHY}"' EXIT
: > "${TMP_UNHEALTHY}"

# Key services we care about for duplicate/Created checks
KEY_SERVICES="chromadb agent-policy-review agent-stage2-lit"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
info() { printf '%s\n' "$*"; }
section() { printf '\n=== %s ===\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" 1>&2; }
err() { printf 'ERROR: %s\n' "$*" 1>&2; EXIT_CODE=1; }

# Get compose project name (directory name by default when using -f)
get_project_name() {
    ( docker compose -f "${COMPOSE_FILE}" config --services 2>/dev/null | head -1 ) || true
    # Fallback: use directory name
    basename "$(pwd)"
}

# -----------------------------------------------------------------------------
# 1. Docker Compose PS summary
# -----------------------------------------------------------------------------
section "Docker Compose PS summary"
$COMPOSE_CMD ps -a 2>/dev/null || err "docker compose ps failed"

# -----------------------------------------------------------------------------
# 2. Unhealthy services + last N log lines each
# -----------------------------------------------------------------------------
section "Unhealthy / Created / Exited services"

# Collect container IDs that are unhealthy, created, or exited (for compose project)
# We use docker ps -a with project label so we only see this stack's containers.
PROJECT_LABEL="com.docker.compose.project"
# Detect project name from first container we find
COMPOSE_PROJECT=""
for id in $(docker ps -a -q 2>/dev/null); do
    proj=$(docker inspect --format '{{index .Config.Labels "'"${PROJECT_LABEL}"'"}}' "$id" 2>/dev/null || true)
    if [ -n "$proj" ]; then
        COMPOSE_PROJECT="$proj"
        break
    fi
done
if [ -z "$COMPOSE_PROJECT" ]; then
    # Fallback: directory name (Docker Compose default project name)
    COMPOSE_PROJECT=$(basename "$(pwd)")
    if [ -z "$COMPOSE_PROJECT" ] || [ "$COMPOSE_PROJECT" = "." ]; then
        COMPOSE_PROJECT="researchflow"
    fi
fi

docker ps -a -q --filter "label=${PROJECT_LABEL}=${COMPOSE_PROJECT}" 2>/dev/null | while read -r id; do
    [ -z "$id" ] && continue
    status=$(docker inspect --format '{{.State.Status}}' "$id" 2>/dev/null || true)
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$id" 2>/dev/null || true)
    service=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id" 2>/dev/null || true)
    name=$(docker inspect --format '{{.Name}}' "$id" 2>/dev/null | sed 's/^\///' || true)

    is_bad=0
    case "${status}" in
        created) is_bad=1 ;;
        exited)  is_bad=1 ;;
        running)  [ "${health}" = "unhealthy" ] && is_bad=1 ;;
        *)       [ -z "${status}" ] && is_bad=0 || is_bad=1 ;;
    esac

    if [ "$is_bad" -eq 1 ]; then
        printf '  Service: %s  Container: %s  Status: %s  Health: %s\n' \
            "$service" "$name" "$status" "${health:-N/A}"
        echo 1 >> "${TMP_UNHEALTHY}"
        # Tail logs for this service (by container id)
        section "Last ${LOG_TAIL} log lines: $service ($name)"
        $COMPOSE_CMD logs --tail="${LOG_TAIL}" "$service" 2>/dev/null || docker logs --tail="${LOG_TAIL}" "$id" 2>/dev/null || true
    fi
done

if [ -s "${TMP_UNHEALTHY}" ]; then
    EXIT_CODE=1
fi

# -----------------------------------------------------------------------------
# 3. Duplicate / Created containers for key services
# -----------------------------------------------------------------------------
section "Duplicate or Created containers (chromadb, agent-policy-review, agent-stage2-lit)"

for svc in $KEY_SERVICES; do
    output=$(docker ps -a -q --filter "label=${PROJECT_LABEL}=${COMPOSE_PROJECT}" 2>/dev/null | while read -r id; do
        [ -z "$id" ] && continue
        s=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id" 2>/dev/null || true)
        [ "$s" != "$svc" ] && continue
        status=$(docker inspect --format '{{.State.Status}}' "$id" 2>/dev/null || true)
        name=$(docker inspect --format '{{.Name}}' "$id" 2>/dev/null | sed 's/^\///' || true)
        printf '  %s: %s (status=%s)\n' "$svc" "$name" "$status"
        if [ "$status" = "created" ]; then
            warn "Container in 'Created' state (never started or stale): $name"
        fi
    done)
    if [ -z "$output" ]; then
        printf '  %s: no container found\n' "$svc"
    else
        printf '%s\n' "$output"
    fi

    cnt=$(docker ps -a -q --filter "label=${PROJECT_LABEL}=${COMPOSE_PROJECT}" 2>/dev/null | while read -r id; do
        [ -z "$id" ] && continue
        s=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$id" 2>/dev/null || true)
        [ "$s" = "$svc" ] && echo 1
    done | wc -l | tr -d ' ')
    if [ -n "$cnt" ] && [ "$cnt" -gt 1 ]; then
        warn "Duplicate containers for service '$svc': $cnt found."
        EXIT_CODE=1
    fi
done

# -----------------------------------------------------------------------------
# 4. Redis reachability from inside compose
# -----------------------------------------------------------------------------
section "Redis reachability (from inside compose)"

if $COMPOSE_CMD exec -T redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
    info "  Redis: PONG (reachable)"
else
    err "Redis not reachable (exec redis-cli ping failed). Set REDIS_PASSWORD if not using default."
fi

# -----------------------------------------------------------------------------
# 5. Summary and exit
# -----------------------------------------------------------------------------
section "Summary"
if [ "$EXIT_CODE" -eq 0 ]; then
    info "Stack health: OK (no required service unhealthy)."
else
    info "Stack health: ISSUES (see above). Fix unhealthy/duplicate/Created services or Redis."
fi

exit "$EXIT_CODE"
