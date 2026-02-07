#!/usr/bin/env bash
# Deploy ResearchFlow full stack to Hetzner. Requires IMAGE_TAG (e.g. sha-<gitsha>).
# Rollback: re-run with a previous SHA tag, e.g. IMAGE_TAG=sha-<oldsha> bash .../hetzner-fullstack-deploy.sh
set -euo pipefail

# Deploy log (create dir if needed for first run)
mkdir -p /opt/researchflow
exec > >(tee -a /opt/researchflow/deploy.log) 2>&1

REPO_DIR="/opt/researchflow/researchflow-production-main"
COMPOSE_FILE="docker-compose.prod.yml"

if [[ -z "${IMAGE_TAG:-}" ]]; then
  echo "ERROR: IMAGE_TAG is required (example: sha-<gitsha> or main)" >&2
  echo "" >&2
  echo "Usage (deploy):  IMAGE_TAG=sha-<commit-sha> bash $0" >&2
  echo "Usage (rollback): IMAGE_TAG=sha-<old-sha> bash $0" >&2
  echo "  Example: IMAGE_TAG=sha-abc123def bash $(basename "$0")" >&2
  exit 1
fi

export IMAGE_TAG="$IMAGE_TAG"
cd "$REPO_DIR"
echo "== Deploying ResearchFlow full stack =="
echo "IMAGE_TAG=$IMAGE_TAG"
git fetch --all --prune
git pull --ff-only
# Pull images for this tag (compose file uses image: ghcr.io/.../service:${IMAGE_TAG})
docker compose -f "$COMPOSE_FILE" pull
# Bring up stack
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
echo "== Waiting for orchestrator health =="
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1:3001/health" >/dev/null; then
    echo "OK: orchestrator healthy"
    exit 0
  fi
  sleep 2
done
echo "ERROR: orchestrator did not become healthy in time" >&2
docker compose -f "$COMPOSE_FILE" ps
docker compose -f "$COMPOSE_FILE" logs --tail=200 orchestrator || true
exit 1
