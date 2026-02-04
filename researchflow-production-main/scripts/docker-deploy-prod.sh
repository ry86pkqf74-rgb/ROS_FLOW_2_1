#!/bin/bash
# ============================================
# ResearchFlow - Production Docker Deployment
# ============================================
# This script deploys ResearchFlow in production mode.
#
# Prerequisites:
# 1. Valid SSL certificates in ./certs/
# 2. .env.production file with all required variables
# 3. Docker and Docker Compose installed
#
# Usage: ./scripts/docker-deploy-prod.sh [options]
#
# Options:
#   --build     Rebuild images before starting
#   --pull      Pull latest base images
#   --clean     Remove old images after deployment
#   --dry-run   Show what would be done without executing
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
BUILD=false
PULL=false
CLEAN=false
DRY_RUN=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build) BUILD=true ;;
        --pull) PULL=true ;;
        --clean) CLEAN=true ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ===================
# Pre-flight checks
# ===================
echo ""
echo "============================================"
echo "ResearchFlow Production Deployment"
echo "============================================"
echo ""

# Check for production environment file
if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
    log_error ".env.production file not found!"
    log_info "Copy .env.production.template to .env.production and fill in the values."
    exit 1
fi

# Check for SSL certificates
if [ ! -f "$PROJECT_ROOT/certs/fullchain.pem" ] || [ ! -f "$PROJECT_ROOT/certs/privkey.pem" ]; then
    log_error "SSL certificates not found in ./certs/"
    log_info "Required files:"
    log_info "  - certs/fullchain.pem (public certificate)"
    log_info "  - certs/privkey.pem (private key)"
    log_info ""
    log_info "For Let's Encrypt, run:"
    log_info "  certbot certonly --standalone -d yourdomain.com"
    log_info "  cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/"
    log_info "  cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/"
    exit 1
fi

# Check for Redis TLS certificates (optional but recommended)
if [ ! -d "$PROJECT_ROOT/certs/redis" ]; then
    log_warn "Redis TLS certificates not found. Creating self-signed certificates..."
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$PROJECT_ROOT/certs/redis"
        openssl genrsa -out "$PROJECT_ROOT/certs/redis/redis.key" 2048
        openssl req -new -x509 -days 365 \
            -key "$PROJECT_ROOT/certs/redis/redis.key" \
            -out "$PROJECT_ROOT/certs/redis/redis.crt" \
            -subj "/CN=redis"
        cp "$PROJECT_ROOT/certs/fullchain.pem" "$PROJECT_ROOT/certs/redis/ca.crt"
    fi
fi

# Check for PostgreSQL SSL certificates (optional)
if [ ! -d "$PROJECT_ROOT/certs/postgres" ]; then
    log_warn "PostgreSQL SSL certificates not found. Creating self-signed certificates..."
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$PROJECT_ROOT/certs/postgres"
        openssl genrsa -out "$PROJECT_ROOT/certs/postgres/server.key" 2048
        chmod 600 "$PROJECT_ROOT/certs/postgres/server.key"
        openssl req -new -x509 -days 365 \
            -key "$PROJECT_ROOT/certs/postgres/server.key" \
            -out "$PROJECT_ROOT/certs/postgres/server.crt" \
            -subj "/CN=postgres"
    fi
fi

log_info "Pre-flight checks passed"

# ===================
# Load environment
# ===================
cd "$PROJECT_ROOT"

log_info "Loading production environment..."
export $(grep -v '^#' .env.production | xargs)

# ===================
# Pull latest images
# ===================
if [ "$PULL" = true ]; then
    log_info "Pulling latest base images..."
    if [ "$DRY_RUN" = false ]; then
        docker-compose -f docker-compose.prod.yml pull postgres redis
    else
        echo "  [DRY-RUN] docker-compose -f docker-compose.prod.yml pull postgres redis"
    fi
fi

# ===================
# Build images
# ===================
if [ "$BUILD" = true ]; then
    log_info "Building production images..."
    if [ "$DRY_RUN" = false ]; then
        docker-compose -f docker-compose.prod.yml build --no-cache
    else
        echo "  [DRY-RUN] docker-compose -f docker-compose.prod.yml build --no-cache"
    fi
fi

# ===================
# Stop existing services
# ===================
log_info "Stopping existing services..."
if [ "$DRY_RUN" = false ]; then
    docker-compose -f docker-compose.prod.yml down --remove-orphans
else
    echo "  [DRY-RUN] docker-compose -f docker-compose.prod.yml down --remove-orphans"
fi

# ===================
# Start services
# ===================
log_info "Starting production services..."
if [ "$DRY_RUN" = false ]; then
    docker-compose -f docker-compose.prod.yml up -d
else
    echo "  [DRY-RUN] docker-compose -f docker-compose.prod.yml up -d"
fi

# ===================
# Wait for health checks
# ===================
log_info "Waiting for services to become healthy..."
if [ "$DRY_RUN" = false ]; then
    sleep 10
    
    # Check health of each service
    SERVICES=("postgres" "redis" "orchestrator" "worker" "guideline-engine" "web" "collab")
    ALL_HEALTHY=true
    
    for service in "${SERVICES[@]}"; do
        if docker-compose -f docker-compose.prod.yml ps "$service" 2>/dev/null | grep -q "Up"; then
            if docker-compose -f docker-compose.prod.yml ps "$service" 2>/dev/null | grep -q "(healthy)"; then
                log_info "  ✓ $service is healthy"
            else
                log_warn "  ⚠ $service is running but not yet healthy"
            fi
        else
            log_error "  ✗ $service is not running"
            ALL_HEALTHY=false
        fi
    done
    
    if [ "$ALL_HEALTHY" = false ]; then
        log_warn "Some services are not running. Check logs with: docker-compose -f docker-compose.prod.yml logs"
    fi
fi

# ===================
# Clean old images
# ===================
if [ "$CLEAN" = true ]; then
    log_info "Cleaning old unused images..."
    if [ "$DRY_RUN" = false ]; then
        docker image prune -f --filter "until=24h"
    else
        echo "  [DRY-RUN] docker image prune -f --filter until=24h"
    fi
fi

# ===================
# Summary
# ===================
echo ""
echo "============================================"
echo "Deployment Complete"
echo "============================================"
echo ""

if [ "$DRY_RUN" = false ]; then
    log_info "Services status:"
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    log_info "Access URLs:"
    echo "  Web UI:      https://localhost (or your domain)"
    echo "  API:         https://localhost/api"
    echo "  API Health:  https://localhost/api/health"
    echo ""
    
    log_info "Useful commands:"
    echo "  Logs:        docker-compose -f docker-compose.prod.yml logs -f"
    echo "  Stop:        docker-compose -f docker-compose.prod.yml down"
    echo "  Restart:     docker-compose -f docker-compose.prod.yml restart"
    echo "  Status:      docker-compose -f docker-compose.prod.yml ps"
else
    echo "[DRY-RUN] No changes were made"
fi
