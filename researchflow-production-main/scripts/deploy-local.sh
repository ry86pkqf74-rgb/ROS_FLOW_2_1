#!/bin/bash
# ============================================
# ResearchFlow - Local production-like deployment
# ============================================
# Builds and runs the prod stack locally, then verifies health.
# Prerequisites: .env.production (from .env.production.template), SSL certs.
# Usage: ./scripts/deploy-local.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

cd "$PROJECT_ROOT"
ENV_FILE="$PROJECT_ROOT/.env.production"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env.production not found. Copy .env.production.template to .env.production and configure."
    exit 1
fi

echo "Building images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo "Waiting for health checks..."
sleep 10

echo "Checking orchestrator health..."
curl -f http://localhost:3001/health || exit 1

echo "Checking worker health (internal)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T worker curl -f http://localhost:8000/health || exit 1

echo "✅ Deployment successful!"
