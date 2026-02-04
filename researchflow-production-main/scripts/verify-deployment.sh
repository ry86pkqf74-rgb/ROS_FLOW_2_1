#!/bin/bash
set -e

echo "Verifying ResearchFlow deployment..."

# Health checks
curl -f http://localhost:3001/health || exit 1
curl -f http://localhost:8000/health || exit 1

# API verification
curl -f http://localhost:3001/api/auth/status || exit 1

# Database connectivity
docker-compose exec -T postgres pg_isready || exit 1

# Redis connectivity
docker-compose exec -T redis redis-cli ping || exit 1

echo "All deployment checks passed!"
