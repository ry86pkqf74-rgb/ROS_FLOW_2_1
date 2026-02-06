#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="/opt/researchflow/researchflow-production-main"
if [[ -z "${IMAGE_TAG:-}" ]]; then
  echo "ERROR: IMAGE_TAG is required (example: sha-<gitsha> or main)" >&2
  exit 1
fi
cd "$REPO_DIR"
echo "== Deploying ResearchFlow full stack =="
echo "IMAGE_TAG=$IMAGE_TAG"
git fetch --all --prune
git pull --ff-only
# Pull images for this tag
docker compose pull
# Bring up stack (no ollama by default)
docker compose up -d --remove-orphans
echo "== Waiting for orchestrator health =="
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1:3001/health" >/dev/null; then
    echo "OK: orchestrator healthy"
    exit 0
  fi
  sleep 2
done
echo "ERROR: orchestrator did not become healthy in time" >&2
docker compose ps
docker compose logs --tail=200 orchestrator || true
exit 1
