# Hetzner Full-Stack Deployment Guide (IP-First)

**Server:** ROSflow2  
**Public IP:** 178.156.139.210  
**Last Updated:** February 7, 2026

---

## Overview

This guide covers deploying the complete ResearchFlow stack on a Hetzner VPS server using IP-only access (no domain/TLS configuration yet). This is suitable for initial deployment, testing, and internal use before configuring a domain and SSL certificates.

## Prerequisites

### Server Requirements

**Recommended Hetzner Server Specs:**
- **vCPU:** 8 cores minimum
- **RAM:** 16 GB minimum
- **Disk:** 240 GB SSD
- **OS:** Ubuntu 22.04 LTS or 24.04 LTS
- **Network:** Public IPv4 address

### Software Requirements

The following must be installed on the server:

- **Docker Engine:** 24.0+
- **Docker Compose:** v2.20+
- **Git:** 2.30+
- **curl:** For health checks

### Install Prerequisites on Ubuntu

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose v2
sudo apt-get install docker-compose-plugin -y

# Verify installations
docker --version
docker compose version
git --version
```

**Log out and back in** for Docker group membership to take effect.

---

## Firewall Configuration

### Required Ports

Configure Hetzner Cloud Firewall or UFW on the server:

**Open (Public Access):**
- **22** - SSH (required for server access)
- **80** - HTTP (Nginx reverse proxy)

**Private (Internal Docker Network Only):**
- **3001** - Orchestrator API (DO NOT expose publicly yet)
- **8000** - Worker service (internal)
- **8001** - Guideline engine (internal)
- **1235** - Collab service (internal)
- **5432** - PostgreSQL (internal)
- **6379** - Redis (internal)

### Configure UFW (Ubuntu Firewall)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH and HTTP only
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp

# Verify
sudo ufw status
```

**Security Note:** The orchestrator API (port 3001) contains sensitive endpoints and should remain internal-only until proper authentication and TLS are configured.

---

## Deployment Steps

### 1. Clone the Repository

```bash
# SSH into your Hetzner server
ssh root@178.156.139.210

# Create deployment directory
mkdir -p /opt/researchflow
cd /opt/researchflow

# Clone repository
git clone https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1.git .

# Navigate to production directory
cd researchflow-production-main
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit environment file
nano .env
```

**Required Variables for Basic Bring-Up:**

```bash
# ============================================
# Database (Change passwords in production!)
# ============================================
POSTGRES_USER=researchflow
POSTGRES_PASSWORD=CHANGE_ME_secure_db_password
POSTGRES_DB=researchflow_prod
DATABASE_URL=postgresql://researchflow:CHANGE_ME_secure_db_password@postgres:5432/researchflow_prod

# ============================================
# Redis (Change password in production!)
# ============================================
REDIS_PASSWORD=CHANGE_ME_secure_redis_password

# ============================================
# Service URLs (Docker internal networking)
# ============================================
WORKER_CALLBACK_URL=http://worker:8000
ORCHESTRATOR_URL=http://orchestrator:3001
WORKER_URL=http://worker:8000
WORKER_WS_URL=ws://worker:8000

# ============================================
# AI Providers (Required for AI features)
# ============================================
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
XAI_API_KEY=your-xai-key-here

# Optional AI providers
MERCURY_API_KEY=
INCEPTION_API_KEY=

# ============================================
# Optional Integrations
# ============================================
EXA_API_KEY=
FIGMA_API_KEY=
NCBI_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
NOTION_API_KEY=
SOURCEGRAPH_API_KEY=

# ============================================
# Application Settings
# ============================================
NODE_ENV=production
LOG_LEVEL=info
GOVERNANCE_MODE=LIVE

# ============================================
# Docker Image Tag
# ============================================
IMAGE_TAG=main
```

**Security Reminder:**
- Change all `CHANGE_ME` passwords before deployment
- Generate secure passwords: `openssl rand -base64 32`
- Keep `.env` file permissions restricted: `chmod 600 .env`
- Never commit `.env` to version control

### 3. Pin IMAGE_TAG (Required for Production)

**🔒 PRODUCTION REQUIREMENT:** Always pin `IMAGE_TAG` to a specific commit SHA or release tag. Never use `main` in production.

**Why this matters:**
- **Reproducibility:** Exact same images across all deployments
- **Rollback safety:** Easy revert to known-good versions
- **Change control:** No surprise updates from upstream
- **Audit compliance:** Clear tracking of deployed versions

#### Production IMAGE_TAG Workflow (Blessed Path)

This is the recommended approach for all production deployments using GHCR (GitHub Container Registry).

**Step 1: Pick a commit SHA or release tag**

```bash
# Option A: Use a specific commit SHA from GitHub (RECOMMENDED)
# Visit: https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/commits/main
# Copy the short commit SHA (e.g., abc1234)

# Option B: Use a release tag (if releases are published)
# Visit: https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/releases
# Use the tag name (e.g., v1.2.3)

# Set IMAGE_TAG in your environment
export IMAGE_TAG=abc1234

# IMPORTANT: Also add to .env file for persistence
echo "IMAGE_TAG=abc1234" >> .env
# Or manually edit .env and set: IMAGE_TAG=abc1234
```

**Step 2: Pull images with the specified tag**

```bash
# Log in to GitHub Container Registry (if using private images)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull all required images with the specified IMAGE_TAG
docker compose pull
```

**Step 3: Verify the pulled images**

```bash
# List all images used by docker compose
docker compose images

# Inspect a specific image to verify the tag
docker image inspect ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator:abc1234

# Check image creation date and labels
docker image inspect ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator:abc1234 \
  --format '{{.Created}} {{.Config.Labels}}'
```

**Benefits of explicit IMAGE_TAG:**
- **Reproducibility:** Exact same images across deployments
- **Rollback:** Easy to revert to a known-good version
- **Auditing:** Clear tracking of what version is running
- **Safety:** Prevents unintended updates from `main` branch

### 4. Run Preflight Checks

Before starting the stack, run preflight checks to verify the server is ready:

```bash
# Make script executable
chmod +x scripts/hetzner-preflight.sh

# Run preflight checks
./scripts/hetzner-preflight.sh
```

Expected output: All checks should PASS. If any checks fail, review the diagnostics and fix issues before proceeding.

**Note:** The preflight script checks:
- Docker and Docker Compose installation and versions
- Disk space (20GB+ recommended) and memory (4GB+ available)
- Docker containers status
- Service health endpoints (after services are started)

### 5. Start the Stack

```bash
# Start all services in detached mode
docker compose up -d

# Monitor startup logs
docker compose logs -f

# Wait for all services to become healthy (2-3 minutes)
```

### 6. Verify Deployment

Check that all containers are running:

```bash
docker compose ps
```

Expected output: All services should show "Up" status with "(healthy)" for services with health checks.

#### Verify Running Image Tags

Confirm that the correct IMAGE_TAG is running:

```bash
# List all running images with their tags
docker compose images

# Expected output should show your IMAGE_TAG (e.g., abc1234) for all services:
# CONTAINER                    IMAGE                                                       TAG
# researchflow-orchestrator-1  ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator          abc1234
# researchflow-worker-1        ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/worker                abc1234
# researchflow-web-1           ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/web                   abc1234
# ...

# Inspect a specific running container to see its image details
docker inspect researchflow-orchestrator-1 --format '{{.Config.Image}}'

# Check image digest for exact version tracking
docker inspect ghcr.io/ry86pkqf74-rgb/ros_flow_2_1/orchestrator:abc1234 \
  --format '{{.RepoDigests}}'
```

**Tip:** Save the IMAGE_TAG and image digests for audit logs and rollback procedures.

---

## Health Checks

### Automated Health Check Script

Run the included health check script:

```bash
cd /opt/researchflow/researchflow-production-main
./scripts/health-check.sh
```

Expected output: All services should show green checkmarks (✓).

### Manual Health Checks

Test each service individually using curl:

#### Core Services

```bash
# Nginx reverse proxy (public endpoint)
curl http://127.0.0.1/health
# Expected: 200 OK with health status JSON

# Orchestrator API (internal endpoint)
curl http://127.0.0.1:3001/api/health
# Expected: {"status":"ok","timestamp":"...","version":"..."}

# Worker service (internal)
curl http://127.0.0.1:8000/health
# Expected: {"status":"healthy"}

# Guideline engine (internal)
curl http://127.0.0.1:8001/health
# Expected: {"status":"ok"}

# Collab service (internal)
curl http://127.0.0.1:1235/health
# Expected: {"status":"healthy"}
```

#### API Endpoints

```bash
# List workflows
curl http://127.0.0.1:3001/api/workflows
# Expected: JSON array of workflows (may be empty initially)

# Export manifest
curl http://127.0.0.1:3001/api/export/manifest
# Expected: JSON manifest object
```

#### Database Services

```bash
# PostgreSQL
docker exec researchflow-postgres-1 pg_isready -U researchflow -d researchflow_prod
# Expected: "accepting connections"

# Redis
docker exec researchflow-redis-1 redis-cli -a "$REDIS_PASSWORD" ping
# Expected: "PONG"
```

---

## Common Failure Modes & Fixes

### 1. Services Not Starting

**Symptom:** `docker compose ps` shows services as "Exit 1" or "Restarting"

**Diagnosis:**
```bash
# Check service logs
docker compose logs orchestrator
docker compose logs worker
```

**Common Causes:**
- Missing or invalid environment variables in `.env`
- Database not ready before dependent services start
- Port conflicts with other services

**Fixes:**
```bash
# Restart specific service
docker compose restart orchestrator

# Full restart
docker compose down && docker compose up -d

# Check for port conflicts
sudo netstat -tlnp | grep -E ':(3001|8000|8001|1235|5432|6379)'
```

### 2. Database Connection Errors

**Symptom:** Services logs show "connection refused" or "authentication failed" for PostgreSQL

**Diagnosis:**
```bash
# Check PostgreSQL is running and healthy
docker compose ps postgres
docker compose logs postgres
```

**Fixes:**
```bash
# Verify DATABASE_URL matches POSTGRES_* variables in .env
# Check password escaping (special characters may need encoding)

# Restart migrations
docker compose restart migrate

# Reset database (WARNING: DATA LOSS)
docker compose down -v
docker compose up -d
```

### 3. Redis Connection Errors

**Symptom:** "NOAUTH Authentication required" or "Connection refused" for Redis

**Fixes:**
```bash
# Verify REDIS_PASSWORD is set in .env
# Ensure REDIS_URL format: redis://:password@redis:6379

# Check Redis logs
docker compose logs redis

# Test Redis manually
docker exec researchflow-redis-1 redis-cli -a "$REDIS_PASSWORD" ping
```

### 4. Health Checks Failing

**Symptom:** Health check endpoints return 5xx errors or timeout

**Diagnosis:**
```bash
# Check if services are still starting up
docker compose ps

# Check resource usage
docker stats

# Verify internal DNS resolution
docker compose exec orchestrator ping worker
```

**Fixes:**
```bash
# Wait 2-3 minutes for all services to initialize
# Check server resources (may need more RAM/CPU)
docker stats

# Restart unhealthy service
docker compose restart <service-name>
```

### 5. Missing Migrations

**Symptom:** Database tables not found, SQL errors in logs

**Fixes:**
```bash
# Check migration logs
docker compose logs migrate

# Re-run migrations manually
docker compose up migrate

# Verify migrations were applied
docker compose exec postgres psql -U researchflow -d researchflow_prod -c "\dt"
```

### 6. Image Tag Mismatch

**Symptom:** Services fail to start with "image not found" errors

**Fixes:**
```bash
# Check IMAGE_TAG in .env matches available tags
echo $IMAGE_TAG

# Use default 'main' tag for latest stable
echo "IMAGE_TAG=main" >> .env

# Pull specific tag
docker compose pull
```

### 7. Out of Memory / Disk Space

**Symptom:** Services killed, containers restarting, OOM errors in logs

**Diagnosis:**
```bash
# Check memory usage
free -h
docker stats

# Check disk space
df -h
```

**Fixes:**
```bash
# Clean up Docker resources
docker system prune -a --volumes

# Increase server resources (resize Hetzner instance)
# Restart services with resource limits
docker compose down && docker compose up -d
```

### 8. Firewall Blocking Traffic

**Symptom:** External access fails but localhost works

**Diagnosis:**
```bash
# Check UFW status
sudo ufw status

# Test from external machine
curl http://178.156.139.210/health
```

**Fixes:**
```bash
# Ensure port 80 is open
sudo ufw allow 80/tcp
sudo ufw reload

# Check Hetzner Cloud Firewall settings in web console
```

---

## Accessing Services

### From Localhost (SSH'd into Server)

```bash
# Web UI (when implemented)
curl http://localhost/

# API endpoints
curl http://localhost:3001/api/health
```

### From External Network (Public IP)

```bash
# HTTP only (no domain/TLS yet)
curl http://178.156.139.210/health
```

**Note:** Until a domain and TLS certificates are configured, accessing the API from external networks will use unencrypted HTTP. This is suitable for testing but not for production use with sensitive data.

---

## Maintenance Commands

### Basic Operations

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f orchestrator

# Restart a service
docker compose restart orchestrator

# Stop all services
docker compose down

# Full cleanup (removes all data - WARNING: DATA LOSS)
docker compose down -v
```

### Updating to a New Version

When updating to a new IMAGE_TAG:

```bash
# Step 1: Set new IMAGE_TAG
export IMAGE_TAG=def5678  # Replace with new commit SHA or tag
echo "IMAGE_TAG=def5678" >> .env

# Step 2: Pull new images
docker compose pull

# Step 3: Verify pulled images
docker compose images

# Step 4: Apply changes with zero-downtime (if possible)
docker compose up -d

# Step 5: Verify all services are healthy
./scripts/hetzner-preflight.sh

# Step 6: Check logs for any issues
docker compose logs -f --tail=100
```

### Rolling Back to a Previous Version

If issues occur after an update:

```bash
# Step 1: Set IMAGE_TAG back to previous known-good version
export IMAGE_TAG=abc1234  # Replace with previous working tag
echo "IMAGE_TAG=abc1234" > .env.tmp && mv .env.tmp .env

# Step 2: Pull previous images
docker compose pull

# Step 3: Restart with previous version
docker compose up -d

# Step 4: Verify rollback succeeded
docker compose images
./scripts/hetzner-preflight.sh
```

### Checking Current Running Versions

```bash
# Show all running images and tags
docker compose images

# Show detailed image information
for service in orchestrator worker web guideline-engine collab; do
  echo "=== $service ==="
  docker compose ps $service --format json | jq -r '.[0].Image'
done

# Show image creation dates
docker compose images --format 'table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}'
```

---

## Persistent Data Storage

### Artifact Storage

The worker service stores generated artifacts (reports, exports, analysis results) in `/data/artifacts` inside the container. This path is mounted to a Docker volume for persistence across container restarts.

**Configuration:**
- **Environment variables**: `ARTIFACTS_PATH`, `ARTIFACT_PATH`, and `RESEARCHFLOW_ARTIFACTS_DIR` must be set to an **absolute path under `/data/*`** (e.g. `/data/artifacts`) in deployment runs. Do not use paths under `/app` or relative paths.
- **Volume Mount**: `shared-data:/data` (mounted to worker container)
- **Physical Location**: Docker volume `shared-data` (managed by Docker)

**Deployment:** Avoid bind-mounting `/app` on server deployments (e.g. `./services/worker:/app` or `./services/collab:/app`). Doing so overwrites built image contents and can break permissions and artifacts; use the published GHCR images as-is with only `/data` (and optionally `/data/projects`) volume-mounted.

**Key Benefits:**
- **Durability**: Artifacts survive container restarts and updates
- **Host-agnostic**: Works on any host without path dependencies
- **No root required**: Worker runs as non-root user with proper permissions

**Accessing Artifacts:**

```bash
# List artifacts
docker compose exec worker ls -lh /data/artifacts

# Copy artifact to host
docker compose cp worker:/data/artifacts/example.zip ./example.zip

# View volume location on host
docker volume inspect researchflow-production-main_shared-data
```

**Troubleshooting:**

If the worker fails to start with artifact path errors:

```bash
# Check volume exists
docker volume ls | grep shared-data

# Inspect volume permissions
docker compose exec worker ls -ld /data/artifacts

# Recreate volume if needed (WARNING: DATA LOSS)
docker compose down -v
docker compose up -d
```

### Other Persistent Data

| Path | Description | Volume |
|------|-------------|--------|
| `/data/artifacts` | Generated artifacts and reports | `shared-data` |
| `/data/logs` | Application logs | `shared-data` |
| `/data/manifests` | Data provenance manifests | `shared-data` |
| `/data/projects` | Version control projects | `shared-data` |
| PostgreSQL data | Database files | `postgres-data` |
| Redis data | Cache and queue data | `redis-data` |

**Note**: All `/data/*` paths are mounted to the `shared-data` volume, which is shared between orchestrator and worker services for artifact exchange.

---

## Next Steps

After successful deployment and health validation:

1. **Configure Domain & TLS**
   - Point domain DNS to 178.156.139.210
   - Set up Let's Encrypt certificates
   - Update Nginx configuration for HTTPS
   - See: [PRODUCTION_ENVIRONMENT_SETUP.md](./PRODUCTION_ENVIRONMENT_SETUP.md)

2. **Implement Authentication**
   - Configure JWT authentication
   - Set up user management
   - Restrict API access

3. **Enable Monitoring**
   - Set up log aggregation
   - Configure health monitoring
   - Enable alerting

4. **Production Hardening**
   - Review security settings
   - Enable rate limiting
   - Configure backups
   - See: [docker-production.md](./docker-production.md)

---

## Troubleshooting Resources

- **GitHub Issues:** https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/issues
- **Docker Compose Reference:** [docker-guide.md](./docker-guide.md)
- **OpenAPI Specification:** `/services/orchestrator/openapi.json`
- **Health Check Script:** `/scripts/health-check.sh`

---

## Reference Files

- **Docker Compose:** `researchflow-production-main/docker-compose.yml`
- **Environment Template:** `researchflow-production-main/.env.example`
- **Health Check Script:** `researchflow-production-main/scripts/health-check.sh`
- **OpenAPI Spec:** `researchflow-production-main/services/orchestrator/openapi.json`
