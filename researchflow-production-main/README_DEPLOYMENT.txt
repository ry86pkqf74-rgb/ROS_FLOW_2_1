================================================================================
ResearchFlow Production Docker Deployment
Complete, Production-Ready Deployment Package
================================================================================

OVERVIEW
--------
This package contains a comprehensive Docker deployment system for ResearchFlow,
a multi-service architecture with 7 interdependent services including databases,
APIs, compute workers, and a React frontend.

WHAT'S INCLUDED
---------------

EXECUTABLE SCRIPTS:
  * deploy-docker-stack.sh (18 KB)
    - Main deployment orchestrator
    - Validates environment, checks prerequisites
    - Deploys services in dependency order
    - Runs health checks with automatic retries
    - Provides comprehensive logging
    - 6 main commands: deploy, start, stop, status, logs, health, diagnose, clean

  * troubleshoot.sh (9.1 KB)
    - Comprehensive diagnostic utility
    - 8 diagnostic checks
    - Service connectivity testing
    - Resource monitoring
    - Error analysis
    - Automatic recovery procedures

CONFIGURATION FILES:
  * docker-compose.yml (7.5 KB)
    - Defines all 7 services with health checks
    - Configured for production use
    - Includes volumes and networking
    - Service dependencies defined
    
  * .env.example (3.5 KB)
    - Environment variables template
    - Copy to .env and customize
    - Contains all required settings

DOCUMENTATION:
  * QUICKSTART.md
    - 5-minute setup guide
    - Minimal steps to get running
    - Quick verification checks
    
  * DEPLOYMENT.md (13 KB)
    - Complete technical reference
    - Service descriptions
    - Health checks and monitoring
    - Backup and recovery
    - Troubleshooting guide
    - Production considerations
    
  * IMPLEMENTATION_GUIDE.md
    - Step-by-step setup instructions
    - Pre-deployment checklist
    - Configuration details
    - Troubleshooting procedures
    - Maintenance tasks
    
  * FILES_MANIFEST.md
    - Complete file inventory
    - Purpose of each file
    - Service architecture details
    
  * SUMMARY.txt
    - Quick reference summary
    - All commands in one place
    - Troubleshooting quick ref

SERVICES DEPLOYED
-----------------

The deployment includes 7 production-ready services:

1. PostgreSQL (port 5432) - Primary database
   - Health check: pg_isready command
   - Data volume: postgres_data
   
2. Redis (port 6379) - Cache and job queue
   - Health check: redis-cli ping
   - Data volume: redis_data
   
3. Orchestrator (port 3001) - Node.js API
   - Authentication, RBAC, AI routing
   - Health check: GET /health
   - Dependencies: PostgreSQL, Redis
   
4. Worker (port 8000) - Python FastAPI
   - 20-stage workflow processing
   - Health check: GET /health
   - Dependencies: PostgreSQL, Redis
   
5. Guideline Engine (port 8001) - Clinical guidelines
   - Guideline evaluation service
   - Health check: GET /health
   - Dependencies: PostgreSQL
   
6. Collaboration (port 1234) - Real-time sync (Yjs)
   - Multi-user editing
   - Health check: GET /health
   - Dependencies: Redis, Orchestrator
   
7. Web Frontend (port 5173) - React + Vite
   - User interface
   - Health check: HTTP 200
   - Dependencies: Orchestrator, Collaboration

QUICK START (5 MINUTES)
-----------------------

1. Copy environment template:
   cp .env.example .env

2. Edit environment file with secure passwords:
   nano .env
   (Set POSTGRES_PASSWORD, REDIS_PASSWORD, JWT_SECRET)

3. Make scripts executable:
   chmod +x deploy-docker-stack.sh troubleshoot.sh

4. Run deployment:
   ./deploy-docker-stack.sh deploy

5. Verify success:
   ./deploy-docker-stack.sh health

6. Access web UI:
   http://localhost:5173

MAIN COMMANDS
-------------

DEPLOYMENT:
  ./deploy-docker-stack.sh deploy        Full deployment with validation
  ./deploy-docker-stack.sh start         Start existing services
  ./deploy-docker-stack.sh stop          Stop services (keep containers)
  ./deploy-docker-stack.sh status        Show service status
  ./deploy-docker-stack.sh logs [svc]    View logs for service
  ./deploy-docker-stack.sh health        Run health checks
  ./deploy-docker-stack.sh diagnose      Run full diagnostics
  ./deploy-docker-stack.sh clean         Stop and remove containers

TROUBLESHOOTING:
  ./troubleshoot.sh all                  All diagnostics
  ./troubleshoot.sh docker               Docker status
  ./troubleshoot.sh connectivity         Service connectivity
  ./troubleshoot.sh resources            Resource usage
  ./troubleshoot.sh errors               Recent errors
  ./troubleshoot.sh restart              Restart services
  ./troubleshoot.sh reset-volumes        Reset all data

NATIVE DOCKER:
  docker-compose ps                      Service status
  docker-compose logs -f                 Stream all logs
  docker-compose logs orchestrator       Logs for specific service
  docker-compose down                    Stop all services
  docker-compose up -d                   Start all services

SYSTEM REQUIREMENTS
-------------------

HARDWARE:
  - 8GB RAM minimum (16GB+ recommended)
  - 50GB+ free disk space
  - Multi-core CPU (4+ cores recommended)

SOFTWARE:
  - Docker 20.10 or higher
  - Docker Compose 2.0 or higher
  - curl (for health checks)
  - grep, netstat (standard utilities)
  - Linux/macOS/Windows with WSL2

NETWORK:
  - Ports 3001, 5173, 8000, 8001, 1234, 5432, 6379 must be available
  - Internet access for pulling Docker images
  - No firewall blocking internal container communication

ESSENTIAL ENVIRONMENT VARIABLES
--------------------------------

These MUST be set in .env before deployment:

  POSTGRES_PASSWORD        PostgreSQL password (required)
  REDIS_PASSWORD          Redis password (required)
  JWT_SECRET              JWT secret key (required, 32+ characters)
  NODE_ENV               production (required)

Recommended settings:

  POSTGRES_USER           researchflow (default)
  POSTGRES_DB             researchflow_db (default)
  LOG_LEVEL               info (default) or debug for troubleshooting
  WORKER_CONCURRENCY      4 (default, adjust based on CPU cores)
  REACT_API_URL          http://localhost:3001 (default)

DEPLOYMENT VALIDATION STEPS
----------------------------

The deployment script automatically validates:

1. Environment Variables
   - Checks all required variables are set
   - Reports missing variables

2. Required Tools
   - Verifies docker, docker-compose, curl, grep are installed
   - Reports version information

3. Docker Daemon
   - Confirms Docker is running
   - Checks Docker daemon status

4. Docker Compose File
   - Validates docker-compose.yml syntax
   - Reports configuration errors

5. Port Availability
   - Ensures all service ports are free
   - Reports ports in use with conflicting services

6. Services Startup
   - Starts PostgreSQL and Redis first
   - Waits for database readiness
   - Starts remaining services in dependency order

7. Health Checks
   - Tests database connectivity
   - Checks HTTP health endpoints
   - Retries with exponential backoff

HEALTH CHECKS
-------------

The deployment includes comprehensive health checks:

PostgreSQL:
  - Command: pg_isready -U $POSTGRES_USER
  - Interval: 10 seconds
  - Timeout: 5 seconds
  - Retries: 5 attempts

Redis:
  - Command: redis-cli ping
  - Interval: 10 seconds
  - Timeout: 5 seconds
  - Retries: 5 attempts

API Services (Orchestrator, Worker, Guidelines, Collab):
  - Endpoint: GET /health
  - Timeout: Configurable (default 5 seconds)
  - Retries: Up to 60 attempts over 5 minutes

Web UI:
  - Endpoint: GET http://localhost:5173
  - Timeout: 5 seconds
  - Retries: 5 attempts

LOGGING
-------

All services write logs to:

Docker Compose Logs:
  docker-compose logs              All services
  docker-compose logs orchestrator Service-specific
  docker-compose logs -f [svc]     Stream in real-time

Deployment Log:
  Each deployment creates: deploy-YYYYMMDD-HHMMSS.log

Docker Logs:
  docker logs [container-id]       Container logs
  docker logs -f [container-id]    Stream container logs

Log Rotation:
  - Driver: json-file
  - Max file size: 10MB
  - Max files: 3 per container

TROUBLESHOOTING
---------------

Common Issues and Solutions:

Port Already in Use:
  lsof -i :3001
  kill -9 [PID]

Docker Daemon Not Running:
  Linux:   sudo systemctl start docker
  macOS:   open -a Docker
  Windows: Start Docker Desktop

Service Fails to Start:
  ./deploy-docker-stack.sh logs [service]
  ./troubleshoot.sh errors

Database Connection Failed:
  docker-compose exec postgres pg_isready
  docker-compose exec redis redis-cli ping

Out of Memory:
  Reduce WORKER_CONCURRENCY in .env
  Check: docker stats

High Resource Usage:
  docker stats --no-stream
  ./troubleshoot.sh resources

For more help:
  ./deploy-docker-stack.sh diagnose
  ./troubleshoot.sh all

BACKUP AND RECOVERY
-------------------

Backup Database:
  docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

Backup Redis:
  docker-compose exec redis redis-cli --rdb /tmp/redis-backup.rdb

Backup Volumes:
  tar -czf volumes_backup.tar.gz postgres_data/ redis_data/

Restore Database:
  docker-compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql

PRODUCTION DEPLOYMENT CHECKLIST
--------------------------------

BEFORE DEPLOYMENT:
  [ ] Read IMPLEMENTATION_GUIDE.md
  [ ] Generate secure passwords (32+ characters)
  [ ] Verify system meets requirements
  [ ] Check all required ports are available
  [ ] Allocate sufficient disk space (50GB+)
  [ ] Have .env configured with secure values

DURING DEPLOYMENT:
  [ ] Monitor script output for errors
  [ ] Verify all health checks pass
  [ ] Test each service endpoint
  [ ] Check logs for warnings
  [ ] Access web UI and login

AFTER DEPLOYMENT:
  [ ] Create database backup
  [ ] Set up monitoring/alerts
  [ ] Configure automated backups
  [ ] Test recovery procedures
  [ ] Document deployment configuration
  [ ] Review security settings
  [ ] Implement HTTPS/TLS at reverse proxy

SECURITY CONSIDERATIONS
-----------------------

Critical:
  - Change all default passwords
  - Use strong JWT secret (32+ characters)
  - Keep .env file secure (chmod 600)
  - Do not commit .env to version control
  - Use HTTPS/TLS at reverse proxy

Important:
  - Implement firewall rules
  - Set up database access controls
  - Enable authentication on all services
  - Regular security updates for base images
  - Monitor and log all access

FURTHER DOCUMENTATION
---------------------

For detailed information, see:

  QUICKSTART.md               5-minute setup
  DEPLOYMENT.md               Complete technical guide
  IMPLEMENTATION_GUIDE.md     Step-by-step instructions
  FILES_MANIFEST.md           File inventory
  
For remote server deployment:
  docs/deployment/hetzner-fullstack.md  Hetzner VPS deployment guide
  scripts/hetzner-preflight.sh          Preflight check script
  scripts/health-check.sh               Enhanced health check with URL flags
  
For Docker basics:
  https://docs.docker.com
  https://docs.docker.com/compose

For service documentation:
  PostgreSQL:  https://www.postgresql.org/docs
  Redis:       https://redis.io/documentation
  Node.js:     https://nodejs.org/docs
  FastAPI:     https://fastapi.tiangolo.com
  React/Vite:  https://vitejs.dev

SUPPORT
-------

If you encounter issues:

1. Check logs:
   ./deploy-docker-stack.sh logs [service]

2. Run diagnostics:
   ./deploy-docker-stack.sh diagnose
   ./troubleshoot.sh all

3. Review documentation:
   See DEPLOYMENT.md for common issues

4. Check resources:
   docker stats
   df -h
   free -h

SUMMARY
-------

This package provides everything needed for a production-ready ResearchFlow
deployment with:

  - Automated validation and error checking
  - Comprehensive health monitoring
  - Detailed logging for troubleshooting
  - Recovery procedures for common issues
  - Complete documentation
  - Production security recommendations

All scripts are production-tested and include error handling, timeouts,
and automatic recovery procedures.

For questions or issues, refer to the documentation files included.

================================================================================
Version: 1.0
Created: 2025-01-29
Status: Production Ready
License: Proprietary - All Rights Reserved
================================================================================
