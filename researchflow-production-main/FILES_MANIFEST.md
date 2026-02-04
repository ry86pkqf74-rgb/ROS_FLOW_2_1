# ResearchFlow Docker Deployment - Files Manifest

## Created Files

This document lists all created files for the ResearchFlow production Docker deployment.

### Core Deployment Scripts

#### deploy-docker-stack.sh (18 KB)
**Purpose:** Primary deployment orchestration script
**Features:**
- Environment variable validation
- Docker and docker-compose verification
- Port availability checking
- Service startup in dependency order
- Health checks with retries
- Comprehensive logging
- Diagnostic and troubleshooting capabilities

**Commands:**
```bash
./deploy-docker-stack.sh deploy       # Full deployment
./deploy-docker-stack.sh status       # Service status
./deploy-docker-stack.sh health       # Health checks
./deploy-docker-stack.sh logs [svc]   # View logs
./deploy-docker-stack.sh diagnose     # Diagnostics
./deploy-docker-stack.sh clean        # Cleanup
```

#### troubleshoot.sh (8 KB)
**Purpose:** Comprehensive troubleshooting and recovery utility
**Features:**
- Docker status verification
- Service connectivity checks
- Resource usage monitoring
- Error log analysis
- Automatic recovery procedures
- Database connectivity testing

**Commands:**
```bash
./troubleshoot.sh all          # All diagnostics
./troubleshoot.sh connectivity # Service connectivity
./troubleshoot.sh resources    # Resource usage
./troubleshoot.sh restart      # Restart services
./troubleshoot.sh reset-volumes # Reset data
```

### Configuration Files

#### docker-compose.yml
**Purpose:** Docker Compose service definitions
**Services (7 total):**
1. **postgres** - PostgreSQL 16 Alpine
   - Port: 5432
   - Volume: postgres_data
   - Health check: pg_isready

2. **redis** - Redis 7 Alpine
   - Port: 6379
   - Volume: redis_data
   - Health check: redis-cli ping
   - Memory: 2GB limit with LRU eviction

3. **orchestrator** - Node.js API
   - Port: 3001
   - Build: ./services/orchestrator
   - Dependencies: postgres, redis
   - Health check: GET /health

4. **worker** - Python FastAPI
   - Port: 8000
   - Build: ./services/worker
   - Dependencies: postgres, redis
   - Health check: GET /health
   - Configurable concurrency

5. **guideline-engine** - Clinical Guidelines
   - Port: 8001
   - Build: ./services/guideline-engine
   - Dependencies: postgres
   - Health check: GET /health

6. **collab** - Real-time Collaboration
   - Port: 1234
   - Build: ./services/collab
   - Dependencies: redis, orchestrator
   - Health check: GET /health

7. **web** - React Frontend
   - Port: 5173
   - Build: ./services/web
   - Dependencies: orchestrator, collab
   - Health check: HTTP 200

**Features:**
- Isolated bridge network (172.28.0.0/16)
- Named volumes for persistence
- Health checks for all services
- Restart policies
- JSON file logging with rotation

#### .env.example
**Purpose:** Environment variables template
**Included Variables:**
- PostgreSQL credentials
- Redis password
- Node environment
- API URLs
- JWT secret
- Worker concurrency
- Log level

**Usage:**
```bash
cp .env.example .env
# Edit with your values
```

### Documentation Files

#### DEPLOYMENT.md (15+ KB)
**Comprehensive deployment guide covering:**
- Architecture overview
- Prerequisites and requirements
- Installation steps
- Service details and endpoints
- Command reference
- Health check procedures
- Configuration and tuning
- Backup and recovery procedures
- Monitoring and alerts
- Troubleshooting common issues
- Production considerations
- Security checklist

#### QUICKSTART.md (2 KB)
**Quick start guide:**
- 5-minute setup steps
- Prerequisites check
- Configuration
- Deployment verification
- Service access URLs
- Common tasks
- Next steps

#### FILES_MANIFEST.md (This file)
**Documentation of all created files and their purposes**

### Network and Storage

**Docker Bridge Network:**
- Name: researchflow-net
- Subnet: 172.28.0.0/16
- Driver: bridge

**Named Volumes (9 total):**
1. postgres_data - PostgreSQL data
2. redis_data - Redis persistence
3. orchestrator_logs - Orchestrator logs
4. worker_cache - Worker cache
5. worker_logs - Worker logs
6. guideline_data - Guideline data
7. guideline_logs - Guideline logs
8. collab_logs - Collaboration logs
9. web_logs - Web frontend logs

## File Structure

```
researchflow-production/
├── deploy-docker-stack.sh      # Main deployment script
├── troubleshoot.sh             # Troubleshooting utility
├── docker-compose.yml          # Service definitions
├── .env.example                # Environment template
├── DEPLOYMENT.md               # Detailed guide
├── QUICKSTART.md               # Quick start guide
└── FILES_MANIFEST.md           # This file
```

## Usage Workflow

### Initial Setup
```bash
1. cp .env.example .env
2. Edit .env with actual values
3. chmod +x deploy-docker-stack.sh
4. ./deploy-docker-stack.sh deploy
```

### Daily Operations
```bash
# Check status
./deploy-docker-stack.sh status

# View logs
./deploy-docker-stack.sh logs orchestrator

# Restart services
./deploy-docker-stack.sh stop
./deploy-docker-stack.sh start
```

### Troubleshooting
```bash
# Run diagnostics
./deploy-docker-stack.sh diagnose

# Detailed troubleshooting
./troubleshoot.sh all

# Fix specific issue
./troubleshoot.sh restart
```

## Service Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Orchestrator | http://localhost:3001 | API, Auth, Job Queue |
| Worker | http://localhost:8000 | Compute, Workflow Processing |
| Guidelines | http://localhost:8001 | Clinical Guidelines |
| Collaboration | http://localhost:1234 | Real-time Sync |
| Web | http://localhost:5173 | User Interface |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache/Queue |

## Environment Variables

**Required for deployment:**
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_DB
- REDIS_PASSWORD
- NODE_ENV
- REACT_API_URL
- JWT_SECRET
- LOG_LEVEL (optional)
- WORKER_CONCURRENCY (optional)

## Key Features

### Validation
- Environment variables check
- Tool availability verification
- Docker daemon status
- docker-compose.yml syntax validation
- Port availability checking

### Deployment
- Dependency-aware startup order
- Database readiness verification
- Health check retries with exponential backoff
- Atomic deployment or rollback
- Comprehensive logging

### Health Monitoring
- Database connectivity checks
- HTTP health endpoints
- Container status verification
- 5-minute timeout with 5-second intervals
- Automatic failure reporting

### Logging
- JSON-file driver with rotation
- Per-service log volumes
- Timestamped deployment logs
- Error highlighting and aggregation

### Troubleshooting
- Resource usage monitoring
- Port conflict detection
- Error log extraction
- Network connectivity testing
- Recovery procedures

## Security Considerations

Files to secure:
- .env - Contains sensitive credentials (mode 600)
- docker-compose.yml - Modify passwords before production use

Recommendations:
- Use strong passwords (minimum 16 characters)
- Rotate secrets regularly
- Implement HTTPS/TLS at reverse proxy
- Use secrets management system
- Regular security updates for base images

## Support and Maintenance

### Regular Checks
```bash
# Weekly
./deploy-docker-stack.sh health

# Daily
docker-compose logs | grep ERROR

# Monthly
./troubleshoot.sh resources
```

### Backup Procedures
```bash
# Database backup
docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Volume backup
tar -czf backup-volumes.tar.gz postgres_data/ redis_data/
```

### Update Procedure
```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose down
docker-compose up -d

# Verify deployment
./deploy-docker-stack.sh health
```

## Related Documentation

- DEPLOYMENT.md - Full deployment guide
- QUICKSTART.md - Quick start procedures
- Docker: https://docs.docker.com
- Docker Compose: https://docs.docker.com/compose

## Version Information

- Created: 2025-01-29
- Docker Version: 20.10+
- Docker Compose: 2.0+
- Base Images:
  - postgres:16-alpine
  - redis:7-alpine
  - Node.js: Latest LTS
  - Python: 3.10+

## License

ResearchFlow Production Deployment
Proprietary - All Rights Reserved
