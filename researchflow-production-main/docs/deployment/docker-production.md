# Docker Production Deployment Guide

**Linear Issue:** ROS-62  
**Last Updated:** January 29, 2026

---

## Overview

This guide covers deploying ResearchFlow in a production environment using Docker Compose with security hardening for HIPAA compliance.

## Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- Valid TLS certificates
- Production environment variables configured

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/ry86pkqf74-rgb/researchflow-production.git
cd researchflow-production

# 2. Set up environment
cp .env.example .env.production
# Edit .env.production with production values

# 3. Set up TLS certificates (see Certificates section)
./scripts/setup-certs.sh

# 4. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify deployment
docker-compose -f docker-compose.prod.yml ps
curl https://localhost/health
```

---

## Configuration

### Environment Variables (.env.production)

```bash
# ============================================
# Database
# ============================================
POSTGRES_USER=ros_prod
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=researchflow

# ============================================
# Redis
# ============================================
REDIS_PASSWORD=<strong-random-password>

# ============================================
# Security
# ============================================
JWT_SECRET=<256-bit-random-hex>
SESSION_SECRET=<256-bit-random-hex>
CORS_ORIGIN=https://your-domain.com

# ============================================
# AI Providers
# ============================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ============================================
# URLs
# ============================================
VITE_API_BASE_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com
VITE_COLLAB_URL=wss://collab.your-domain.com

# ============================================
# Monitoring (Optional)
# ============================================
VITE_SENTRY_DSN=https://...@sentry.io/...
```

### Generating Secure Secrets

```bash
# Generate JWT_SECRET (256-bit hex)
openssl rand -hex 32

# Generate SESSION_SECRET
openssl rand -hex 32

# Generate database password
openssl rand -base64 24
```

---

## TLS Certificates

### Directory Structure

```
certs/
├── fullchain.pem      # Web server (nginx)
├── privkey.pem        # Web server private key
├── postgres/
│   ├── server.crt     # PostgreSQL server cert
│   └── server.key     # PostgreSQL private key
└── redis/
    ├── redis.crt      # Redis server cert
    ├── redis.key      # Redis private key
    └── ca.crt         # Certificate authority
```

### Using Let's Encrypt

```bash
# Install certbot
apt-get install certbot

# Generate certificates
certbot certonly --standalone -d your-domain.com -d api.your-domain.com

# Copy to project
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./certs/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./certs/
```

### Self-Signed (Development/Testing Only)

```bash
# Generate CA
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout certs/ca.key -out certs/ca.crt \
  -subj "/CN=ResearchFlow-CA"

# Generate PostgreSQL cert
openssl req -nodes -newkey rsa:4096 \
  -keyout certs/postgres/server.key -out certs/postgres/server.csr \
  -subj "/CN=postgres"
openssl x509 -req -in certs/postgres/server.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/postgres/server.crt -days 365

# Generate Redis cert
openssl req -nodes -newkey rsa:4096 \
  -keyout certs/redis/redis.key -out certs/redis/redis.csr \
  -subj "/CN=redis"
openssl x509 -req -in certs/redis/redis.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/redis/redis.crt -days 365
cp certs/ca.crt certs/redis/
```

---

## Security Hardening

### Network Isolation

The production compose file uses a dedicated bridge network with a custom subnet:

```yaml
networks:
  researchflow-prod:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Resource Limits

All services have CPU and memory limits to prevent resource exhaustion:

| Service | CPU Limit | Memory Limit |
|---------|-----------|--------------|
| orchestrator | 2 cores | 2GB |
| worker | 4 cores | 8GB |
| postgres | 4 cores | 8GB |
| redis | 1 core | 1GB |
| web | 0.5 core | 256MB |

### Health Checks

All services include health checks with appropriate intervals:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 60s
```

### Restart Policies

Production services use `restart: always` with failure limits:

```yaml
deploy:
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
    window: 120s
```

---

## HIPAA Compliance

### PHI Protection

```yaml
environment:
  - PHI_SCAN_ENABLED=true
  - PHI_FAIL_CLOSED=true
  - GOVERNANCE_MODE=LIVE
```

### Audit Logging

```yaml
environment:
  - AUDIT_LOG_ENABLED=true
  - AUDIT_LOG_LEVEL=info
```

### Encryption

- **At Rest:** PostgreSQL data encrypted via volume encryption
- **In Transit:** TLS for all service communication
  - Redis: TLS on port 6379
  - PostgreSQL: SSL required
  - Web: HTTPS only

---

## Monitoring

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f orchestrator

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 worker
```

### Health Status

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Detailed health
docker inspect --format='{{json .State.Health}}' researchflow-orchestrator-1
```

### Resource Usage

```bash
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Maintenance

### Backup Database

```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U ros_prod researchflow > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20260129.sql | docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U ros_prod researchflow
```

### Update Deployment

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Remove old images
docker image prune -f
```

### Scaling Workers

```bash
# Scale worker service
docker-compose -f docker-compose.prod.yml up -d --scale worker=3
```

---

## Troubleshooting

### Common Issues

**Connection Refused to Redis**
```bash
# Check Redis TLS
docker-compose -f docker-compose.prod.yml exec redis redis-cli --tls \
  --cert /tls/redis.crt --key /tls/redis.key --cacert /tls/ca.crt ping
```

**PostgreSQL SSL Error**
```bash
# Verify SSL is enabled
docker-compose -f docker-compose.prod.yml exec postgres psql -U ros_prod -c "SHOW ssl"
```

**Service Won't Start**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs orchestrator

# Check health
docker inspect --format='{{json .State.Health}}' researchflow-orchestrator-1
```

---

## Support

- **Documentation:** https://docs.researchflow.dev
- **Issues:** https://github.com/ry86pkqf74-rgb/researchflow-production/issues
- **Linear:** ROS project board
