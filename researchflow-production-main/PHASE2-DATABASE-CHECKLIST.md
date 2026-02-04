# Phase 2: Database & Cache Layer Setup - Deployment Checklist

**Project:** ResearchFlow Production Deployment  
**Phase:** 2 - Database & Cache Layer Setup  
**Date:** January 29, 2026  
**Status:** READY FOR DEPLOYMENT

---

## Overview

Phase 2 establishes the foundational database and caching infrastructure for ResearchFlow. This checklist ensures all PostgreSQL and Redis configurations are properly validated before proceeding to Phase 3 (Service Deployment).

**Key Components:**
- PostgreSQL 16 (with pgvector extension)
- Redis 7 (with TLS and authentication)
- Database migrations
- Health checks and resource allocation

---

## Section 1: Configuration Files Found

### Identified Configuration Files

| File Path | Purpose | Status |
|-----------|---------|--------|
| `/Users/ros/researchflow-production/.env` | Current environment variables (production) | ✓ Found |
| `/Users/ros/researchflow-production/.env.example` | Development template | ✓ Found |
| `/Users/ros/researchflow-production/.env.production.template` | Production deployment template | ✓ Found |
| `/Users/ros/researchflow-production/docker-compose.yml` | Development/test docker setup | ✓ Found |
| `/Users/ros/researchflow-production/docker-compose.prod.yml` | Production-hardened docker setup | ✓ Found |
| `/Users/ros/researchflow-production/docker-compose.backend.yml` | Backend services only | ✓ Found |
| `/Users/ros/researchflow-production/docker-compose.minimal.yml` | Minimal test configuration | ✓ Found |

---

## Section 2: PostgreSQL Configuration Requirements

### Required Environment Variables

#### Basic Configuration (REQUIRED)
- [ ] `POSTGRES_USER` - Database user account (default: researchflow_user)
- [ ] `POSTGRES_PASSWORD` - Database password (minimum 12 characters, mixed case recommended)
- [ ] `POSTGRES_DB` - Database name (default: researchflow)
- [ ] `POSTGRES_HOST` - Database hostname/IP (default: localhost for dev, postgres for docker)
- [ ] `POSTGRES_PORT` - Database port (default: 5432)

#### Connection String (DERIVED)
- [ ] `DATABASE_URL` - Full connection string (format: postgresql://user:password@host:port/dbname)

#### Production-Specific (REQUIRED for Prod)
- [ ] Database SSL mode enabled (`sslmode=require`)
- [ ] Database SSL certificate configured
- [ ] Database SSL key configured
- [ ] Max connections tuned (default: 200)
- [ ] Shared buffers configured (default: 256MB)
- [ ] Effective cache size set (default: 768MB)

### PostgreSQL Service Configuration (docker-compose)

#### Standard Configuration (docker-compose.yml)
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: ${POSTGRES_USER:-researchflow}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secure-password}
    POSTGRES_DB: ${POSTGRES_DB:-researchflow_db}
    POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=en_US.UTF-8"
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-researchflow}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### Production Configuration (docker-compose.prod.yml)
```yaml
postgres:
  image: pgvector/pgvector:pg16  # Note: pgvector version for vector search
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
  command:
    - "postgres"
    - "-c"
    - "ssl=on"
    - "-c"
    - "ssl_cert_file=/var/lib/postgresql/ssl/server.crt"
    - "-c"
    - "ssl_key_file=/var/lib/postgresql/ssl/server.key"
    - "-c"
    - "max_connections=200"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "effective_cache_size=768MB"
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./infrastructure/docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    - ./certs/postgres:/var/lib/postgresql/ssl:ro
```

**Deployment Tasks:**

- [ ] Verify PostgreSQL 16 availability (use pgvector:pg16 for production)
- [ ] Create database user with secure password (minimum 32 characters for production)
- [ ] Initialize database with UTF8 encoding and en_US.UTF-8 locale
- [ ] Create init database script at `./init-db.sql` (if not exists)
- [ ] Configure SSL certificates for PostgreSQL (production only)
- [ ] Set max_connections to 200 (production)
- [ ] Set shared_buffers to 256MB (production)
- [ ] Set effective_cache_size to 768MB (production)
- [ ] Enable WAL (Write-Ahead Logging) for durability
- [ ] Configure checkpoint completion target to 0.9 (production)
- [ ] Set log_statement to ddl (production)
- [ ] Set log_min_duration_statement to 1000 (production)
- [ ] Create postgres_data volume for persistent storage
- [ ] Configure health check: `pg_isready` with 10s interval, 5s timeout, 5 retries

---

## Section 3: Redis Configuration Requirements

### Required Environment Variables

#### Basic Configuration (OPTIONAL for Dev, REQUIRED for Prod)
- [ ] `REDIS_HOST` - Redis hostname/IP (default: localhost for dev, redis for docker)
- [ ] `REDIS_PORT` - Redis port (default: 6379)
- [ ] `REDIS_PASSWORD` - Redis password (minimum 12 characters)

#### Connection String (DERIVED)
- [ ] `REDIS_URL` - Full connection string (format: redis://:password@host:port/0)

#### Production-Specific (REQUIRED for Prod)
- [ ] Redis TLS enabled (`REDIS_TLS_ENABLED=true`)
- [ ] Redis SSL certificate configured
- [ ] Redis SSL key configured
- [ ] CA certificate configured
- [ ] Max memory set (default: 1-2GB)
- [ ] Max memory policy configured (default: allkeys-lru)

### Redis Service Configuration (docker-compose)

#### Standard Configuration (docker-compose.yml)
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --requirepass ${REDIS_PASSWORD:-redis-secure-password} --maxmemory 2gb --maxmemory-policy allkeys-lru
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### Production Configuration (docker-compose.prod.yml)
```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --requirepass ${REDIS_PASSWORD}
    --tls-port 6379
    --port 0
    --tls-cert-file /tls/redis.crt
    --tls-key-file /tls/redis.key
    --tls-ca-cert-file /tls/ca.crt
    --tls-auth-clients no
    --maxmemory 1gb
    --maxmemory-policy allkeys-lru
  volumes:
    - redis-data:/data
    - ./certs/redis:/tls:ro
  healthcheck:
    test: ["CMD", "redis-cli", "--tls", "--cert", "/tls/redis.crt", "--key", "/tls/redis.key", "--cacert", "/tls/ca.crt", "-a", "${REDIS_PASSWORD}", "ping"]
```

**Deployment Tasks:**

- [ ] Verify Redis 7-alpine availability
- [ ] Create Redis password with secure value (minimum 32 characters for production)
- [ ] Set maxmemory to 2GB (dev) or 1GB (production minimum)
- [ ] Set maxmemory-policy to allkeys-lru
- [ ] Enable AOF (Append-Only File) for persistence in production
- [ ] Configure SSL certificates for Redis (production only)
- [ ] Create redis_data volume for persistent storage
- [ ] Configure health check: `redis-cli` with 10s interval, 5s timeout, 5 retries
- [ ] Enable TLS on port 6379 (production only)
- [ ] Disable unencrypted port 0 (production only)
- [ ] Configure database 0 for cache, database 1 for collab service (if needed)

---

## Section 4: Database Migrations & Initialization

### Migration Setup

- [ ] Create `/migrations` directory in project root
- [ ] Create migration scripts for:
  - [ ] Initial schema setup
  - [ ] User/RBAC tables
  - [ ] Research workflow tables
  - [ ] Audit logging tables
  - [ ] Session management tables
  - [ ] pgvector extension installation (production)

### Migration Service Configuration (Production)

```yaml
migrate:
  image: postgres:16-alpine
  environment:
    - PGHOST=postgres
    - PGUSER=${POSTGRES_USER}
    - PGPASSWORD=${POSTGRES_PASSWORD}
    - PGDATABASE=${POSTGRES_DB}
    - PGSSLMODE=require
  volumes:
    - ./migrations:/migrations:ro
  depends_on:
    postgres:
      condition: service_healthy
  restart: "no"
  command: >
    sh -c '
      for f in /migrations/*.sql; do
        psql -f "$f"
      done
    '
```

**Deployment Tasks:**

- [ ] Review all SQL migration files
- [ ] Verify migration ordering (by timestamp or sequence number)
- [ ] Test migrations on staging environment
- [ ] Backup database before running migrations
- [ ] Set migration service to run once (`restart: "no"`)
- [ ] Ensure migrations complete successfully before dependent services start
- [ ] Document rollback procedures for each migration

---

## Section 5: Service Dependencies & Health Checks

### Dependency Chain

**Development (docker-compose.yml):**
```
postgres (healthy) --> orchestrator, worker, guideline-engine
redis (healthy)    --> orchestrator, worker, collab
```

**Production (docker-compose.prod.yml):**
```
postgres (healthy) --> migrate --> orchestrator, worker, collab, guideline-engine
redis (healthy)    --> orchestrator, worker, collab
```

### Health Check Configuration

#### PostgreSQL Health Check
- [ ] Command: `pg_isready -U ${POSTGRES_USER}`
- [ ] Interval: 10 seconds
- [ ] Timeout: 5 seconds
- [ ] Retries: 5
- [ ] Start period: 10-30 seconds

#### Redis Health Check
- [ ] Command: `redis-cli -a ${REDIS_PASSWORD} ping` (with TLS flags in production)
- [ ] Interval: 10 seconds
- [ ] Timeout: 5 seconds
- [ ] Retries: 5
- [ ] Start period: 10 seconds

**Deployment Tasks:**

- [ ] Verify health check commands execute successfully
- [ ] Test dependency conditions (`service_healthy`)
- [ ] Verify services wait for dependencies before starting
- [ ] Monitor logs during startup for health check failures
- [ ] Document troubleshooting for common health check issues

---

## Section 6: Volume Management

### Required Volumes

| Volume Name | Mount Point | Purpose | Persistence |
|------------|------------|---------|-------------|
| `postgres_data` | `/var/lib/postgresql/data` | Database files | Yes |
| `redis_data` | `/data` | Redis persistence (AOF) | Yes (prod) |
| `shared-data` | `/data` | Shared artifacts (prod) | Yes |
| `projects-data` | `/data/projects` | Project data (prod) | Yes |

**Deployment Tasks:**

- [ ] Create volume directories with appropriate permissions (chmod 700)
- [ ] Verify volume mount points in docker-compose files
- [ ] Set up backup strategy for postgres_data volume
- [ ] Configure automated backups for production database
- [ ] Implement disaster recovery plan
- [ ] Test volume restoration procedures
- [ ] Monitor disk space usage for volumes
- [ ] Set up alerts for low disk space

---

## Section 7: Network Configuration

### Network Setup

**Network Name:** `researchflow-net` (dev) or `researchflow-prod` (production)

**Network Type:** Bridge driver

**Subnet:** 172.28.0.0/16

**Deployment Tasks:**

- [ ] Create custom bridge network
- [ ] Verify all services attached to network
- [ ] Test inter-service connectivity (postgres, redis)
- [ ] Document service hostnames:
  - [ ] `postgres:5432` (database)
  - [ ] `redis:6379` (cache)
- [ ] Verify DNS resolution within network
- [ ] Test network isolation from external systems

---

## Section 8: Resource Allocation

### Production Resource Limits

| Service | CPU Limit | Memory Limit | CPU Reserve | Memory Reserve |
|---------|-----------|--------------|-------------|----------------|
| PostgreSQL | 4 CPU | 8GB | 1 CPU | 2GB |
| Redis | 1 CPU | 1GB | 0.25 CPU | 256MB |
| Migrate | 0.5 CPU | 256MB | N/A | N/A |
| Orchestrator | 2 CPU | 2GB | 0.5 CPU | 512MB |
| Worker | 4 CPU | 8GB | 1 CPU | 2GB |

**Deployment Tasks:**

- [ ] Set PostgreSQL CPU limit to 4 cores (production)
- [ ] Set PostgreSQL memory limit to 8GB (production)
- [ ] Set PostgreSQL memory reservation to 2GB
- [ ] Set Redis CPU limit to 1 core (production)
- [ ] Set Redis memory limit to 1GB (production)
- [ ] Set Redis memory reservation to 256MB
- [ ] Monitor actual resource usage during testing
- [ ] Adjust limits based on workload testing

---

## Section 9: Security Configuration

### PostgreSQL Security

- [ ] Enable scram-sha-256 authentication (`POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"`)
- [ ] Configure SSL mode (`ssl=on`)
- [ ] Generate SSL certificate for PostgreSQL
- [ ] Generate SSL key for PostgreSQL
- [ ] Set certificate permissions (chmod 600)
- [ ] Restrict database access to internal network only
- [ ] Disable remote connections unless necessary
- [ ] Enable connection logging (`log_statement=ddl`)
- [ ] Enable slow query logging (`log_min_duration_statement=1000`)

### Redis Security

- [ ] Set strong password (minimum 32 characters for production)
- [ ] Enable requirepass authentication
- [ ] Configure TLS encryption (production only)
- [ ] Generate TLS certificate for Redis
- [ ] Generate TLS key for Redis
- [ ] Generate CA certificate for Redis
- [ ] Set certificate permissions (chmod 600)
- [ ] Disable unencrypted port in production
- [ ] Restrict Redis access to internal network only
- [ ] Enable AOF persistence with fsync always (for critical data)

### Environment Variable Security

- [ ] Store `.env` with `chmod 600` (read-only for owner)
- [ ] Never commit `.env` to version control
- [ ] Use `.env.example` template for documentation
- [ ] Separate development and production environment files
- [ ] Rotate secrets regularly (passwords, keys)
- [ ] Use strong password generation (minimum entropy)
- [ ] Store secrets in secure secret management system (not version control)

**Deployment Tasks:**

- [ ] Review and update all security configurations
- [ ] Generate new certificates if expired
- [ ] Verify file permissions for keys and secrets
- [ ] Implement secret rotation schedule
- [ ] Document secret management procedures
- [ ] Set up monitoring for security events

---

## Section 10: Logging & Monitoring

### PostgreSQL Logging

- [ ] `log_statement=ddl` - Log DDL statements (production)
- [ ] `log_min_duration_statement=1000` - Log queries over 1 second
- [ ] Enable query logging in docker-compose (json-file driver)
- [ ] Configure max log file size (50MB for production)
- [ ] Configure max log file count (5 files for production)

### Redis Logging

- [ ] Enable AOF (Append-Only File) logging
- [ ] Configure logging driver (json-file)
- [ ] Configure max log file size (20MB for production)
- [ ] Configure max log file count (3 files for production)

### Docker Logging Configuration

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"      # PostgreSQL
    max-file: "5"
```

**Deployment Tasks:**

- [ ] Configure centralized log aggregation (if using)
- [ ] Set up log rotation policies
- [ ] Configure monitoring alerts for errors
- [ ] Implement health check monitoring
- [ ] Set up performance metrics collection
- [ ] Create dashboards for database metrics
- [ ] Configure backup monitoring

---

## Section 11: Backup & Disaster Recovery

### Backup Strategy

- [ ] Daily automated database backups
- [ ] Backup location: Separate from production data
- [ ] Backup retention: Minimum 30 days
- [ ] Test restore procedures monthly
- [ ] Verify backup integrity
- [ ] Document recovery time objective (RTO)
- [ ] Document recovery point objective (RPO)

### Backup Tools

- [ ] PostgreSQL `pg_dump` for logical backups
- [ ] WAL archiving for point-in-time recovery
- [ ] Redis `BGSAVE` for snapshots
- [ ] Redis AOF for durability

**Deployment Tasks:**

- [ ] Create backup script for PostgreSQL
- [ ] Create backup script for Redis
- [ ] Schedule backups (e.g., daily 2 AM UTC)
- [ ] Test restore from backup
- [ ] Document backup/restore procedures
- [ ] Set up backup monitoring and alerts

---

## Section 12: Pre-Deployment Verification

### Configuration Checklist

- [ ] All environment variables defined in `.env`
- [ ] Docker Compose syntax valid (`docker-compose config`)
- [ ] All images available or buildable
- [ ] All volumes can be created
- [ ] Network configuration correct
- [ ] Health checks configured for both services
- [ ] Resource limits set appropriately
- [ ] Logging configuration enabled
- [ ] Security configurations applied

### Testing Checklist

- [ ] PostgreSQL connectivity test: `psql -U user -d database -h host -p 5432`
- [ ] Redis connectivity test: `redis-cli -h host -p 6379 -a password ping`
- [ ] Database migration test (if running separately)
- [ ] Health check endpoints responding
- [ ] Service inter-connectivity verified
- [ ] Load test with expected concurrent connections
- [ ] Failover test (restart services, verify recovery)
- [ ] Backup/restore test

### Documentation Checklist

- [ ] Environment configuration documented
- [ ] Database schema documented
- [ ] API documentation updated
- [ ] Troubleshooting guide created
- [ ] Runbooks for common issues documented
- [ ] Secret management procedures documented
- [ ] Monitoring/alerting setup documented

---

## Section 13: Deployment Steps

### Step 1: Pre-Deployment (Before docker-compose up)

1. [ ] Verify all environment variables in `.env`
2. [ ] Create SSL certificates (production):
   ```bash
   mkdir -p ./certs/postgres ./certs/redis
   # Generate certificates...
   ```
3. [ ] Create migration directory and scripts:
   ```bash
   mkdir -p ./migrations
   # Copy migration SQL files...
   ```
4. [ ] Create necessary volumes (if not auto-created):
   ```bash
   docker volume create postgres_data
   docker volume create redis_data
   ```
5. [ ] Verify docker-compose syntax:
   ```bash
   docker-compose config > /dev/null && echo "Valid"
   ```

### Step 2: Start Database Services

**Development:**
```bash
docker-compose up -d postgres redis
```

**Production:**
```bash
docker-compose -f docker-compose.prod.yml up -d postgres redis
```

- [ ] Wait for PostgreSQL health check to pass (10-30 seconds)
- [ ] Wait for Redis health check to pass (10 seconds)
- [ ] Verify service logs: `docker-compose logs postgres redis`

### Step 3: Run Database Migrations (Production)

**Production Only:**
```bash
docker-compose -f docker-compose.prod.yml up migrate
docker-compose -f docker-compose.prod.yml logs migrate
```

- [ ] Verify all migrations completed successfully
- [ ] Check for migration errors in logs
- [ ] Verify database schema created: `psql -U user -d database -c "\dt"`

### Step 4: Verify Connectivity

```bash
# Test PostgreSQL
docker-compose exec postgres pg_isready -U researchflow

# Test Redis
docker-compose exec redis redis-cli -a password ping

# Test from application service
docker-compose exec orchestrator psql -U researchflow -d researchflow_db -c "SELECT 1"
```

- [ ] PostgreSQL responds with "accepting connections"
- [ ] Redis responds with "PONG"
- [ ] Application can connect successfully

### Step 5: Post-Deployment Verification

- [ ] Check all service health statuses: `docker-compose ps`
- [ ] Verify logs for errors: `docker-compose logs`
- [ ] Test application endpoints
- [ ] Test database queries through application
- [ ] Verify backup processes running
- [ ] Monitor resource usage

---

## Section 14: Known Issues & Troubleshooting

### PostgreSQL Issues

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Health check failing | "pg_isready: could not connect" | Wait longer start period, check password |
| Connection refused | "could not connect to server" | Verify POSTGRES_HOST and port, check firewall |
| Authentication failed | "password authentication failed" | Verify POSTGRES_PASSWORD, check character encoding |
| Disk space full | "could not write block" | Increase volume size, implement retention policy |
| Slow queries | High query latency | Increase shared_buffers, check indexes, analyze workload |

### Redis Issues

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Health check failing | "redis-cli: Could not connect" | Wait longer start period, check password |
| Out of memory | "OOM command not allowed" | Increase maxmemory, check memory usage |
| Connection refused | "Connection refused" | Verify REDIS_HOST and port, check firewall |
| Authentication failed | "WRONGPASS invalid username-password pair" | Verify REDIS_PASSWORD |
| Slow performance | High latency on operations | Check network, monitor CPU usage |

### Common Solutions

- [ ] Verify environment variables are set correctly
- [ ] Check Docker daemon is running
- [ ] Ensure sufficient disk space for volumes
- [ ] Check network connectivity between services
- [ ] Review logs: `docker-compose logs [service_name]`
- [ ] Restart services: `docker-compose restart postgres redis`
- [ ] Rebuild images if base image changes: `docker-compose build --no-cache`

---

## Section 15: Rollback Procedures

### Rollback if Database Deployment Fails

1. [ ] Stop services: `docker-compose down`
2. [ ] Restore backup: Database dump or snapshot
3. [ ] Verify backup integrity
4. [ ] Remove problematic volumes (if needed)
5. [ ] Revert `.env` changes to previous known-good state
6. [ ] Start services: `docker-compose up -d postgres redis`
7. [ ] Verify connectivity
8. [ ] Run post-deployment verification

### Rollback if Migrations Fail

1. [ ] Document the error and migration step that failed
2. [ ] Restore database from pre-migration backup
3. [ ] Fix the problematic migration SQL
4. [ ] Test migration on staging environment
5. [ ] Run migration again on production

---

## Section 16: Sign-Off & Approval

### Phase 2 Completion Criteria

- [ ] All configuration files identified and reviewed
- [ ] PostgreSQL service deployed and healthy
- [ ] Redis service deployed and healthy
- [ ] Database migrations completed successfully
- [ ] All environment variables configured
- [ ] Security hardening applied (certificates, auth)
- [ ] Health checks passing
- [ ] Resource allocation verified
- [ ] Logging enabled
- [ ] Backup procedures established
- [ ] Disaster recovery tested
- [ ] Documentation complete
- [ ] Pre-deployment verification passed
- [ ] All tests passed

### Sign-Off

**Phase 2 Manager:** _________________________  Date: __________

**QA Lead:** _________________________  Date: __________

**Security Lead:** _________________________  Date: __________

---

## Appendix: Quick Reference

### Essential Commands

```bash
# View service status
docker-compose ps

# View service logs
docker-compose logs [service_name]
docker-compose logs -f postgres  # Follow logs

# Connect to PostgreSQL
docker-compose exec postgres psql -U researchflow -d researchflow_db

# Connect to Redis
docker-compose exec redis redis-cli -a password

# Start/stop services
docker-compose up -d postgres redis
docker-compose down

# Rebuild services
docker-compose build --no-cache

# View resource usage
docker stats

# Backup database
docker-compose exec postgres pg_dump -U researchflow -d researchflow_db > backup.sql

# Restore database
docker-compose exec postgres psql -U researchflow -d researchflow_db < backup.sql
```

### Important File Paths

- Configuration: `/Users/ros/researchflow-production/.env`
- Docker Compose (Dev): `/Users/ros/researchflow-production/docker-compose.yml`
- Docker Compose (Prod): `/Users/ros/researchflow-production/docker-compose.prod.yml`
- Migrations: `/Users/ros/researchflow-production/migrations/`
- Certificates (Prod): `/Users/ros/researchflow-production/certs/`

---

**End of Phase 2 Checklist**

Generated: January 29, 2026
Version: 1.0
