#!/usr/bin/env bash
# Capture ROSflow inventory on a deploy host (e.g. ROSflow2).
# Run from: /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main
# Output: /tmp/rosflow-inventory-<timestamp>/ and /tmp/rosflow-inventory.zip
# No secrets are written (env vars redacted, only names).

set -e

DEPLOY_DIR="${DEPLOY_DIR:-/opt/researchflow/ROS_FLOW_2_1/researchflow-production-main}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="/tmp/rosflow-inventory-${TIMESTAMP}"

echo "Creating $OUT_DIR and capturing inventory..."
mkdir -p "$OUT_DIR"
cd "$DEPLOY_DIR"

# Rendered compose + live state
docker compose config > "$OUT_DIR/compose.rendered.yml"
docker compose ps --all > "$OUT_DIR/compose.ps.txt"
docker compose images > "$OUT_DIR/compose.images.txt"
docker compose logs --tail=200 orchestrator > "$OUT_DIR/logs.orchestrator.tail200.txt" 2>&1 || true
docker compose logs --tail=200 worker > "$OUT_DIR/logs.worker.tail200.txt" 2>&1 || true

# Containers + ports
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' > "$OUT_DIR/docker.ps.table.txt" 2>&1 || true

# Env var names only (values redacted)
for c in $(docker compose ps -q 2>/dev/null); do
  name=$(docker inspect -f '{{.Name}}' "$c" 2>/dev/null | sed 's#^/##')
  echo "## $name"
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" 2>/dev/null | sed 's/=.*$/=<redacted>/' | sort
  echo
done > "$OUT_DIR/env.redacted.by-container.txt" 2>/dev/null || true

# Health endpoints (from host)
curl -sS http://127.0.0.1:3001/api/health | tee "$OUT_DIR/orchestrator.health.json" >/dev/null || true
curl -sS http://127.0.0.1/api/health | tee "$OUT_DIR/web.health.txt" >/dev/null || true

# Optional OpenAPI
curl -sS http://127.0.0.1:3001/api/openapi.json > "$OUT_DIR/orchestrator.openapi.json" 2>/dev/null || true

# Zip for handoff
cd /tmp && zip -r rosflow-inventory.zip "rosflow-inventory-${TIMESTAMP}"

echo "Done. Artifacts: $OUT_DIR"
echo "Zip: /tmp/rosflow-inventory.zip"
echo "Copy to Cursor workspace or attach when asking for inventory report."
