#!/bin/bash
set -e

# Hetzner Deployment Script
# Run this after successfully SSH'd into the server

echo "🚀 Starting Hetzner deployment..."

# Configuration
SERVER="root@178.156.139.210"
DEPLOY_DIR="/opt/researchflow/researchflow-production-main"
IMAGE_TAG="${IMAGE_TAG:-58a3eab}"

echo "📦 Deploying IMAGE_TAG: $IMAGE_TAG"

# Execute deployment commands on remote server
ssh "$SERVER" << ENDSSH
set -e

echo "📂 Navigating to deployment directory..."
cd $DEPLOY_DIR

echo "🔄 Pulling latest changes from git..."
git pull origin main

echo "🏷️  Setting IMAGE_TAG to $IMAGE_TAG..."
export IMAGE_TAG=$IMAGE_TAG
echo "IMAGE_TAG=$IMAGE_TAG" >> .env

echo "📥 Pulling Docker images from GHCR..."
docker compose pull

echo "🔍 Verifying pulled images..."
docker compose images

echo "✅ Running preflight checks..."
chmod +x scripts/hetzner-preflight.sh
./scripts/hetzner-preflight.sh

echo "🚀 Starting the Docker stack..."
docker compose up -d

echo "📊 Verifying deployment..."
docker compose ps
echo ""
docker compose images

echo "🏥 Final health check..."
./scripts/hetzner-preflight.sh

ENDSSH

echo "✅ Deployment complete!"
