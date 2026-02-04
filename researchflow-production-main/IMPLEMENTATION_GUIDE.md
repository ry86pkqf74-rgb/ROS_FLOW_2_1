# ResearchFlow Docker Deployment - Implementation Guide

## Overview

This guide walks through implementing the complete ResearchFlow Docker deployment from scratch. The deployment includes 7 production-ready services with health checks, logging, and comprehensive error handling.

## What You Get

### Deployment Scripts
1. **deploy-docker-stack.sh** - Main deployment orchestrator with validation
2. **troubleshoot.sh** - Comprehensive diagnostics and recovery tools

### Configuration Files
1. **docker-compose.yml** - Complete service definitions
2. **.env.example** - Environment variables template

### Documentation
1. **DEPLOYMENT.md** - Complete technical reference
2. **QUICKSTART.md** - 5-minute setup guide
3. **FILES_MANIFEST.md** - File inventory and purposes
4. **IMPLEMENTATION_GUIDE.md** - This document

## Pre-Deployment Checklist

### System Requirements
- [ ] Docker 20.10+ installed (`docker --version`)
- [ ] Docker Compose 2.0+ installed (`docker-compose --version`)
- [ ] 8GB+ RAM (16GB+ recommended)
- [ ] 50GB+ free disk space
- [ ] Linux/macOS/Windows (WSL2)
- [ ] Internet connection for pulling images

### Network Requirements
- [ ] Ports 3001, 5173, 8000, 8001, 1234, 5432, 6379 available
- [ ] No firewall blocking internal container communication
- [ ] External service connectivity (if applicable)

### Prerequisites
- [ ] Read QUICKSTART.md for overview
- [ ] Read DEPLOYMENT.md for details
- [ ] Prepare secure passwords for PostgreSQL and Redis
- [ ] Prepare JWT secret key (minimum 32 characters)

## Step-by-Step Implementation

### Phase 1: Preparation (5 minutes)

#### 1.1 Install Docker (if needed)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in
```

**macOS:**
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Or use Homebrew:
brew install docker docker-compose
```

**Windows (WSL2):**
```powershell
# Enable WSL2
wsl --set-default-version 2

# Install Docker Desktop for Windows
# Download from https://www.docker.com/products/docker-desktop
```

#### 1.2 Verify Docker Installation
```bash
docker --version
docker-compose --version
docker ps  # Should work without errors
```

#### 1.3 Navigate to Deployment Directory
```bash
cd /path/to/researchflow-production
ls -la  # Should show deploy-docker-stack.sh, docker-compose.yml, etc.
```

### Phase 2: Configuration (5 minutes)

#### 2.1 Copy Environment Template
```bash
cp .env.example .env
chmod 600 .env  # Restrict permissions
```

#### 2.2 Generate Secure Credentials

**Generate PostgreSQL password:**
```bash
openssl rand -base64 32
# Example output: aB1c2D3e4F5g6H7i8J9k0L1m2N3o4P5q=
```

**Generate Redis password:**
```bash
openssl rand -base64 32
```

**Generate JWT secret:**
```bash
openssl rand -hex 32
# Example output: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

#### 2.3 Edit Environment File
```bash
nano .env
# Or your preferred editor: vim, code, etc.
```

**Required changes:**
```bash
POSTGRES_USER=researchflow              # Keep default or change
POSTGRES_PASSWORD=<paste-generated>     # REQUIRED
POSTGRES_DB=researchflow_db             # Keep default or change
REDIS_PASSWORD=<paste-generated>        # REQUIRED
NODE_ENV=production                     # Keep as production
REACT_API_URL=http://localhost:3001    # Adjust if needed
JWT_SECRET=<paste-generated-jwt>       # REQUIRED (32+ chars)
LOG_LEVEL=info                          # Keep as info (or debug)
WORKER_CONCURRENCY=4                    # Adjust based on CPU cores
```

#### 2.4 Verify Configuration
```bash
# Check syntax
cat .env | grep -v "^#" | grep -v "^$"

# Verify no sensitive data exposed
grep -E "PASSWORD|SECRET" .env | grep -v "^#"
```

### Phase 3: Pre-Deployment Validation (2 minutes)

#### 3.1 Make Scripts Executable
```bash
chmod +x deploy-docker-stack.sh troubleshoot.sh
ls -l *.sh  # Should show -rwx permissions
```

#### 3.2 Validate docker-compose.yml
```bash
docker-compose config -q
# Should complete without errors
```

#### 3.3 Run Pre-checks
```bash
# Manually check prerequisites
docker --version
docker-compose --version
curl --version
grep --version

# Check ports
netstat -tuln | grep -E ":(3001|5173|8000|8001|1234|5432|6379)"
# Should show no results (ports are free)
```

### Phase 4: Deployment (5-10 minutes)

#### 4.1 Source Environment Variables
```bash
export $(cat .env | grep -v '^#' | xargs)
```

#### 4.2 Run Deployment Script
```bash
# Full deployment with all checks
./deploy-docker-stack.sh deploy

# Monitor output for:
# - "Validating Environment" ✓
# - "Checking Required Tools" ✓
# - "Docker daemon is running" ✓
# - "All required ports are available" ✓
# - "Database services started" ✓
# - "All services passed health checks" ✓
# - "Deployment Successful" ✓
```

#### 4.3 Verify Deployment Success
```bash
# Should show all services running
./deploy-docker-stack.sh status

# Example output:
# SERVICE              STATUS
# postgres             Up 30s (healthy)
# redis               Up 25s (healthy)
# orchestrator        Up 20s (healthy)
# worker              Up 15s (healthy)
# guideline-engine    Up 10s (healthy)
# collab              Up 5s (healthy)
# web                 Up 2s (healthy)
```

### Phase 5: Post-Deployment Testing (5 minutes)

#### 5.1 Run Health Checks
```bash
./deploy-docker-stack.sh health

# Expected output:
# ✓ postgres is healthy
# ✓ redis is healthy
# ✓ orchestrator is healthy
# ✓ worker is healthy
# ✓ guideline-engine is healthy
# ✓ collab is healthy
# ✓ web is healthy
```

#### 5.2 Test Service Connectivity
```bash
# Orchestrator API
curl http://localhost:3001/health

# Worker service
curl http://localhost:8000/health

# Guideline Engine
curl http://localhost:8001/health

# Collaboration service
curl http://localhost:1234/health

# Web UI (should return HTML)
curl http://localhost:5173 | head -20

# PostgreSQL (should show accessible)
docker-compose exec -T postgres pg_isready

# Redis (should return PONG)
docker-compose exec -T redis redis-cli ping
```

#### 5.3 Access Web UI
```bash
# Open browser to:
http://localhost:5173

# Should see:
# - ResearchFlow login page or dashboard
# - No console errors
# - Connected to API (check network tab)
```

#### 5.4 View Logs
```bash
# Check for any errors
docker-compose logs | grep -i error

# View recent logs
docker-compose logs --tail=50

# View specific service
docker-compose logs orchestrator
```

### Phase 6: Configuration (Optional)

#### 6.1 Custom Port Mappings

Edit docker-compose.yml if needed:
```yaml
services:
  orchestrator:
    ports:
      - "3001:3001"  # Change first number for external port
```

#### 6.2 Resource Limits

Adjust if needed (in docker-compose.yml):
```yaml
services:
  worker:
    environment:
      WORKER_CONCURRENCY: 8  # Increase for more parallel processing
```

#### 6.3 Logging Configuration

Set LOG_LEVEL in .env:
```bash
LOG_LEVEL=debug  # For verbose logging during development
LOG_LEVEL=info   # For production
LOG_LEVEL=warn   # For minimal logging
```

## Troubleshooting

### Deployment Failures

#### Port Already in Use
```bash
# Identify which process
lsof -i :3001

# Stop the service
kill -9 <PID>

# Or change port in docker-compose.yml
```

#### Docker Daemon Not Running
```bash
# Linux
sudo systemctl start docker

# macOS
open -a Docker

# Windows
# Start Docker Desktop application
```

#### Insufficient Disk Space
```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a --volumes

# Or increase allocated disk space
```

#### Out of Memory
```bash
# Check memory usage
free -h
docker stats

# Reduce worker concurrency in .env
WORKER_CONCURRENCY=2
```

### Runtime Issues

#### Service Crashes
```bash
# Check logs
./deploy-docker-stack.sh logs [service]

# Run diagnostics
./troubleshoot.sh errors

# Restart service
./deploy-docker-stack.sh restart
```

#### Slow Response Times
```bash
# Check resource usage
./troubleshoot.sh resources

# Check network connectivity
./troubleshoot.sh connectivity

# Monitor in real-time
docker stats
```

#### Database Connection Errors
```bash
# Test PostgreSQL
docker-compose exec postgres pg_isready -U $POSTGRES_USER

# Test Redis
docker-compose exec redis redis-cli ping

# Check logs
./deploy-docker-stack.sh logs postgres
./deploy-docker-stack.sh logs redis
```

## Backup and Recovery

### Create Backups

```bash
# Backup database
docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > postgres_backup.sql

# Backup Redis
docker-compose exec redis redis-cli --rdb /tmp/redis-backup.rdb

# Backup volumes
tar -czf volumes_backup.tar.gz postgres_data/ redis_data/
```

### Restore from Backup

```bash
# Restore PostgreSQL
docker-compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < postgres_backup.sql

# Restore Redis
# (Stop Redis, copy backup to data volume, restart)
docker-compose down redis
cp redis-backup.rdb redis_data/
docker-compose up -d redis
```

## Ongoing Maintenance

### Daily Tasks
```bash
# Check health
./deploy-docker-stack.sh health

# Review errors
docker-compose logs | grep ERROR
```

### Weekly Tasks
```bash
# Run diagnostics
./troubleshoot.sh all

# Check resources
./troubleshoot.sh resources

# Review logs
docker-compose logs | tail -100
```

### Monthly Tasks
```bash
# Create backups
docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d).sql

# Update images
docker-compose pull
docker-compose down
docker-compose up -d

# Verify health
./deploy-docker-stack.sh health
```

## Performance Optimization

### Increase Worker Concurrency
```bash
# Edit .env
WORKER_CONCURRENCY=8

# Restart
./deploy-docker-stack.sh restart
```

### Increase Redis Memory
```bash
# Edit docker-compose.yml
redis:
  command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

### Enable Debug Logging
```bash
# Edit .env
LOG_LEVEL=debug

# Restart
./deploy-docker-stack.sh restart
```

## Production Deployment

### Pre-Production Checklist
- [ ] Change all default passwords
- [ ] Use strong JWT secret (32+ characters)
- [ ] Enable HTTPS/TLS at reverse proxy
- [ ] Configure firewall rules
- [ ] Set up monitoring and alerts
- [ ] Create backup schedule
- [ ] Document recovery procedures
- [ ] Test failover and recovery
- [ ] Review security settings
- [ ] Perform load testing

### Deploy to Production
```bash
# 1. Complete pre-production checklist
# 2. Use production .env file
cp .env.production .env

# 3. Deploy
./deploy-docker-stack.sh deploy

# 4. Monitor for 1 hour
./deploy-docker-stack.sh logs -f

# 5. Run load tests
# (Use appropriate load testing tool)
```

## Support

### Getting Help

1. Check logs: `./deploy-docker-stack.sh logs [service]`
2. Run diagnostics: `./deploy-docker-stack.sh diagnose`
3. Review DEPLOYMENT.md for details
4. Check FILES_MANIFEST.md for file descriptions

### Report Issues

Include:
- `./deploy-docker-stack.sh diagnose` output
- `docker-compose logs` output
- Environment details (OS, Docker version)
- Steps to reproduce

## Summary

Deployment should be complete in 15-20 minutes with:

1. ✓ All 7 services running
2. ✓ All health checks passing
3. ✓ Web UI accessible at http://localhost:5173
4. ✓ API endpoints responding at http://localhost:3001
5. ✓ Logs being collected and archived
6. ✓ Comprehensive monitoring in place

For detailed information, refer to DEPLOYMENT.md.
