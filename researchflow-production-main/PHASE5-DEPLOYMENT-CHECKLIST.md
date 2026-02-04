# Phase 5A: VPS Deployment Planning Checklist

**Created:** January 29, 2026  
**Track:** Track 5A - VPS Deployment Planning for ResearchFlow  
**Status:** In Progress  
**Linear Issues:** ROS-26 (Phase 6 VPS Deployment), ROS-62 (Docker Production Config), ROS-50 (HIPAA Compliance)

---

## Executive Summary

ResearchFlow is ready for VPS production deployment with comprehensive Docker infrastructure, security hardening, and monitoring capabilities. This checklist documents all infrastructure requirements, deployment configurations, and pre-flight validation steps.

**Key Readiness:** 
- ✅ Docker Compose production configuration complete (ROS-62 DONE)
- ✅ All 7 microservices configured for production use
- ✅ TLS/SSL encryption and HIPAA compliance built-in
- ✅ Health checks, resource limits, and restart policies configured
- ⏳ VPS provisioning ready (Stream 6A)
- ⏳ DNS & SSL configuration pending (Stream 6B)

---

## Task 5A.1: Deployment Configuration Analysis

### Discovered Files

#### 1. Docker Compose Production Configuration
**File:** `/Users/ros/researchflow-production/docker-compose.prod.yml` (465 lines)

**Status:** ✅ COMPLETE - Production-ready configuration

**Services Configured:**
- `postgres:5432` - PostgreSQL 16 with pgvector + SSL
- `redis:6379` - Redis 7 Alpine with TLS + AUTH
- `orchestrator:3001` - Node.js API (Auth, RBAC, Job Queue)
- `worker:8000` - Python FastAPI (20-stage workflow)
- `guideline-engine:8001` - Clinical Guidelines Engine
- `collab:1234` - Real-time Collaboration (Yjs)
- `web:443/80` - React Frontend (Nginx reverse proxy)

**Resource Configuration:**
```
orchestrator: CPU 0.5-2, Memory 512M-2G
worker:       CPU 1-4, Memory 2G-8G (largest allocations)
postgres:     CPU 1-4, Memory 2G-8G (database intensive)
redis:        CPU 0.25-1, Memory 256M-1G
collab:       CPU 0.25-1, Memory 128M-512M
guideline-engine: CPU 0.25-1, Memory 256M-1G
web:          CPU 0.1-0.5, Memory 64M-256M
```

**Health Checks:** All services configured with health endpoints
- HTTP health endpoints for API services
- Database health checks (pg_isready, redis-cli ping)
- Interval: 30 seconds, Timeout: 10 seconds, Retries: 3-5

**Security Features:**
- PostgreSQL: SSL enforcement + scram-sha-256 authentication
- Redis: TLS encryption + password authentication
- Orchestrator: JWT authentication, rate limiting, CORS
- Worker: PHI scan enabled, fail-closed mode
- All services: Restart policies with exponential backoff

**Network Configuration:**
- Bridge network: 172.28.0.0/16
- Service-to-service communication via container names
- Explicit port mappings for external access

#### 2. Nginx Reverse Proxy Configuration
**File:** `/Users/ros/researchflow-production/infrastructure/docker/nginx/nginx.conf` (295 lines)

**Status:** ✅ COMPLETE - Production-ready proxy configuration

**Features Implemented:**
- HTTP/2 support over HTTPS
- Rate limiting zones configured:
  - API endpoints: 10 requests/second with burst
  - Login endpoints: 5 requests/minute
- Upstream definitions for load balancing
- WebSocket support for collaboration server
- Gzip compression for assets
- Security headers (HSTS, X-Content-Type-Options)
- Cache headers for static assets (31536000s for JS/CSS)
- Health check endpoint at `/health`

**Proxy Configuration:**
```
GET /health -> Health status
GET /api/* -> orchestrator:3001 (rate limited)
GET /api/auth -> orchestrator:3001 (stricter rate limit)
GET /collab -> collab:1234 (WebSocket with long timeouts)
GET /* -> web:80 (React frontend)
GET ~* \.(js|css)$ -> Cache: 31536000s (immutable)
GET ~* \.(png|jpg|etc)$ -> Cache: 2592000s
GET ~* \.html$ -> Cache: no-cache (fast rollouts)
```

**TLS Configuration:**
- TLS 1.2 and 1.3 only
- Modern cipher suite (ECDHE-ECDSA-AES128-GCM, etc.)
- HSTS header with 63072000 second max-age
- Certificate path: `/etc/nginx/ssl/fullchain.pem`
- Key path: `/etc/nginx/ssl/privkey.pem`

**WebSocket Support:**
- Upgrade headers configured
- Connection upgrade handling
- 7-day timeout for persistent connections (collab)

#### 3. Deployment Script
**File:** `/Users/ros/researchflow-production/deploy-docker-stack.sh` (622 lines)

**Status:** ✅ COMPLETE - Full deployment automation

**Capabilities:**
- Pre-deployment validation (8 checks):
  1. Environment variables validation
  2. Required tools check (docker, docker-compose, curl, grep)
  3. Docker daemon status
  4. Docker Compose file syntax
  5. Port availability check
  6. System resource verification
  7. Network connectivity check
  8. Disk space verification

- Deployment phases:
  1. Pull latest images from registry
  2. Start database services
  3. Wait for database readiness
  4. Run migrations
  5. Start all services
  6. Health checks on each service

- Health check functions:
  - PostgreSQL: `pg_isready` command
  - Redis: `redis-cli ping`
  - HTTP services: HTTP GET to `/health` endpoint
  - Timeout: 300 seconds (5 minutes)
  - Interval: 5 seconds between checks

- Commands:
  - `deploy` - Full deployment with validation
  - `start` - Start existing services
  - `stop` - Stop all services
  - `status` - Show service status
  - `logs [service]` - View service logs
  - `health` - Run health checks only
  - `diagnose` - Troubleshooting diagnostics
  - `clean` - Remove all containers and volumes

**Output:**
- Timestamped log file: `deploy-YYYYMMDD-HHMMSS.log`
- Color-coded console output
- Detailed validation report
- Final access URLs

#### 4. Production Environment Template
**File:** `/Users/ros/researchflow-production/.env.production.template` (147 lines)

**Status:** ✅ COMPLETE - Comprehensive environment configuration

**Sections Defined:**

1. **Domain & Node Configuration**
   - DOMAIN=researchflow.app
   - NODE_ENV=production

2. **Database (PostgreSQL)**
   - POSTGRES_USER=ros_prod
   - POSTGRES_PASSWORD (32-char minimum)
   - POSTGRES_DB=researchflow
   - DATABASE_URL with SSL mode

3. **Redis Cache**
   - REDIS_PASSWORD (32-char minimum)

4. **Authentication (JWT)**
   - JWT_SECRET (256-bit)
   - JWT_EXPIRES_IN=24h
   - JWT_REFRESH_EXPIRES_IN=7d
   - AUTH_ALLOW_STATELESS_JWT=false

5. **AI API Keys**
   - OpenAI, Anthropic, Claude, XAI, Mercury, InceptionLabs, Codex

6. **Integrations**
   - Notion (with database IDs)
   - Figma
   - Sourcegraph
   - NCBI (PubMed)
   - Semantic Scholar

7. **PHI Governance (HIPAA)**
   - PHI_SCAN_ENABLED=true
   - PHI_FAIL_CLOSED=true
   - STRICT_PHI_ON_UPLOAD=true

8. **Mode Configuration**
   - GOVERNANCE_MODE=LIVE
   - ALLOW_UPLOADS=true
   - MOCK_ONLY=false

9. **Monitoring & Analytics**
   - Sentry DSN for error tracking
   - Analytics IP salt
   - Worker configuration (4 workers, timeouts)

---

## Task 5A.2: Linear Issue Review - Deployment & VPS

### Issue ROS-26: Phase 6 VPS Production Deployment
**Status:** Backlog (Urgent Priority)  
**Created:** Jan 28, 2026

**Recommended Infrastructure:**
- **Provider:** Hetzner
- **Server:** CX52
- **Specs:** 16 vCPU, 32 GB RAM, 320 GB SSD
- **Cost:** €32.40/month (~$35 USD)
- **Justification:** Best value for Docker production workloads

**Planned Streams:**
- [ ] Stream 6A: VPS Provisioning
- [ ] Stream 6B: DNS & SSL Configuration
- [ ] Stream 6C: GitHub Actions CI/CD
- [ ] Stream 6D: Production Environment
- [ ] Stream 6E: Monitoring & Alerts

**Files Referenced:**
- `PHASE6_VPS_DEPLOYMENT_PLAN.md`
- `.github/workflows/deploy.yml`
- `.env.production.template`

**Success Criteria:**
- [ ] VPS operational and accessible
- [ ] All 8 Docker services healthy
- [ ] HTTPS with valid SSL certificate
- [ ] CI/CD pipeline tested
- [ ] Monitoring configured and alerting

### Issue ROS-62: Docker Production Config + VPS Prep
**Status:** Done (Completed Jan 29, 2026)  
**Priority:** High

**Completed Deliverables:**
1. ✅ `docker-compose.prod.yml` - Production overlay with:
   - Resource limits (memory/CPU per service)
   - Health checks (all services configured)
   - Restart policies (on-failure with exponential backoff)
   - Network isolation (172.28.0.0/16)

2. ✅ Redis Hardening:
   - TLS enabled (--tls-port 6379)
   - Password authentication (--requirepass)
   - Data persistence (appendonly yes)
   - LRU eviction policy (maxmemory-policy)

3. ✅ PostgreSQL Security:
   - SSL enforcement (ssl=on)
   - scram-sha-256 authentication
   - Connection limits (max_connections=200)
   - Performance tuning parameters

4. ✅ Environment Files:
   - `.env.production.template` (fully populated)
   - Secret management structure defined

5. ✅ Documentation:
   - `DEPLOYMENT.md` - Complete deployment guide

### Issue ROS-50: Phase 7 HIPAA Compliance Enhancement
**Status:** Backlog (Critical/Urgent Priority)

**Existing HIPAA Work:**
- ✅ docker-compose.hipaa.yml
- ✅ RBAC middleware
- ✅ Audit logging middleware
- ✅ PHI scanning engine
- ✅ Encryption at rest (PostgreSQL with pgvector)
- ✅ TLS for data in transit
- ✅ ACL enforcement
- ✅ Session management

**Phase 7 Gaps (Next Track):**
- Data flow mapping
- Risk analysis documentation
- Incident response procedures
- Business associate agreements
- Data retention policies

---

## Task 5A.3: Infrastructure Requirements Documentation

### VPS Minimum Specifications

**Recommended: Hetzner CX52**
```
CPU:     16 vCPU (Intel/AMD equivalent)
Memory:  32 GB RAM
Storage: 320 GB SSD (NVMe preferred)
Network: 1 Gbps public bandwidth
Region:  EU or US (based on user location)
```

**Minimum (Cost-Optimized):**
```
CPU:     8 vCPU
Memory:  16 GB RAM
Storage: 160 GB SSD
Network: 1 Gbps
Cost:    ~$15-20/month
Note:    Limited headroom for peaks
```

**Recommended (Balanced):**
```
CPU:     16 vCPU
Memory:  32 GB RAM
Storage: 320 GB SSD
Network: 1 Gbps
Cost:    ~$35/month
Provides: 2-3x headroom for scaling
```

### Resource Allocation by Service

**Production Allocation:**
```
PostgreSQL    → 4 CPU, 8 GB RAM   (Primary workload)
Worker        → 4 CPU, 8 GB RAM   (Processing intensive)
Orchestrator  → 2 CPU, 2 GB RAM   (API/Routing)
Redis         → 1 CPU, 1 GB RAM   (Cache/Queue)
Collab        → 1 CPU, 512 MB RAM (WebSocket server)
Guideline-Engine → 1 CPU, 1 GB RAM
Web (Nginx)   → 0.5 CPU, 256 MB RAM
Migrations/OS → 2 CPU, 4 GB RAM   (Reserve)

Total: 15.5 CPU, 31.75 GB RAM (fits within 16CPU/32GB)
```

### Storage Requirements

**Persistent Volumes:**
1. **PostgreSQL Data** (`postgres-data`)
   - Size: 50-100 GB (depends on usage)
   - Growth: ~1-2 GB/month (typical)
   - Backup: Daily snapshots recommended

2. **Redis Data** (`redis-data`)
   - Size: 5-10 GB
   - Persistence: appendonly enabled
   - Growth: Depends on queue depth

3. **Shared Data** (`shared-data`)
   - Size: 20-50 GB (artifacts, projects)
   - Growth: Varies by research projects
   - Type: User-generated content

4. **Projects Data** (`projects-data`)
   - Size: 20-50 GB
   - Growth: Per-project basis
   - Retention: User-controlled

**Total Storage:** 95-210 GB (fits within 320 GB recommended)

### Network Requirements

**Port Mappings (External Access):**
```
443/tcp  → Nginx HTTPS (primary entry)
80/tcp   → Nginx HTTP (redirect to 443)
3001/tcp → Orchestrator API (internal only - proxied through Nginx)
8000/tcp → Worker (internal only)
8001/tcp → Guideline Engine (internal only)
1234/tcp → Collaboration (internal only - proxied through Nginx)
5432/tcp → PostgreSQL (internal only, no external)
6379/tcp → Redis (internal only, no external)
```

**Recommended Firewall Rules:**
```
Inbound:
  - 443/tcp from anywhere (HTTPS)
  - 80/tcp from anywhere (HTTP redirect)
  - 22/tcp from YOUR_IP (SSH admin)
  
Outbound:
  - Allow all (for Docker pulls, API calls, etc.)
  
Internal (Docker bridge 172.28.0.0/16):
  - All traffic allowed between containers
```

**Bandwidth Requirements:**
- Baseline: 50-100 Mbps peak
- Per 100 concurrent users: +10 Mbps
- Video streaming (future): +50 Mbps per user
- 1 Gbps connection provides 10x+ headroom

### Disk I/O Considerations

**Expected I/O Profile:**
- **Read-heavy:** HTML, CSS, JS assets
- **Write-heavy:** Database migrations, logs
- **Random I/O:** PostgreSQL queries, Redis operations

**SSD Recommended:** Yes
- NVMe preferred for optimal performance
- RAID 1 for redundancy (if available)
- EBS or cloud equivalent (for snapshots)

### SSL/TLS Requirements

**Certificate Management:**
1. **Certificate Type:** Wildcard or domain-specific
2. **Provider:** Let's Encrypt (free) or commercial
3. **Validity:** Minimum 1 year
4. **Auto-renewal:** Certbot recommended
5. **Storage:** `/certs/fullchain.pem` and `/certs/privkey.pem`

**Certificate Paths (in docker-compose.prod.yml):**
```yaml
volumes:
  - ./certs/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
  - ./certs/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
  - ./certs/postgres:/var/lib/postgresql/ssl:ro
  - ./certs/redis:/tls:ro
```

**Protocols:**
- TLS 1.2 minimum (TLS 1.3 preferred)
- Cipher suite: Modern only (no legacy support)
- HSTS enabled: max-age=63072000 (2 years)

### DNS Configuration Requirements

**Required DNS Records:**
```
A       researchflow.app            → VPS_IP_ADDRESS
AAAA    researchflow.app            → VPS_IPV6_ADDRESS (if available)
CNAME   www.researchflow.app        → researchflow.app
MX      mail.researchflow.app       → (if email needed)
TXT     v=spf1 -all                 → (SPF record)
TXT     acme-challenge              → (for Let's Encrypt)
```

**DNS Provider Options:**
- Cloudflare (free tier: DNS, DDoS protection)
- AWS Route53 (~$0.50/month)
- DigitalOcean DNS (free with VPS)
- Hetzner DNS (if using Hetzner VPS)

**DNSSEC:** Optional but recommended for security

### Backup & Recovery Requirements

**Database Backups:**
```bash
# Daily backup
docker-compose exec postgres pg_dump -U ros_prod researchflow_db > backup-$(date +%Y%m%d).sql

# Store in: /backups/ or cloud storage (AWS S3, etc.)
# Retention: 30 days minimum
# Verification: Weekly restore test
```

**Volume Backups:**
```bash
# Weekly snapshot of persistent volumes
tar -czf backup-volumes-$(date +%Y%m%d).tar.gz postgres-data/ redis-data/

# Store: Off-site (S3, Dropbox, etc.)
# Retention: 3 months
```

**Configuration Backups:**
```bash
# Daily backup of critical files
tar -czf backup-config-$(date +%Y%m%d).tar.gz \
  .env.production \
  docker-compose.prod.yml \
  infrastructure/

# Store: Version control (private repo) or off-site
```

---

## Task 5A.4: VPS Deployment Checklist

### Pre-Deployment Phase (Stream 6A: VPS Provisioning)

- [ ] **VPS Selection & Provisioning**
  - [ ] Hetzner CX52 (or equivalent) selected
  - [ ] VPS created and accessible
  - [ ] SSH access verified from admin IP
  - [ ] Server specs: 16 vCPU, 32 GB RAM, 320 GB SSD
  - [ ] OS: Ubuntu 22.04 LTS or Debian 12

- [ ] **System Setup**
  - [ ] OS updated: `sudo apt update && apt upgrade`
  - [ ] Docker installed: `docker --version`
  - [ ] Docker Compose installed: `docker-compose --version`
  - [ ] Docker daemon running and enabled
  - [ ] Required tools: curl, wget, git, jq installed

- [ ] **System Configuration**
  - [ ] Hostname set to: `researchflow`
  - [ ] Timezone configured (UTC recommended)
  - [ ] NTP synchronization verified
  - [ ] Disk space checked (50+ GB free)
  - [ ] Memory verified (32 GB installed)
  - [ ] Network bandwidth verified

- [ ] **SSH & Security**
  - [ ] SSH key-based auth configured
  - [ ] Password auth disabled
  - [ ] UFW firewall enabled
  - [ ] SSH hardening applied
  - [ ] Fail2ban installed (optional but recommended)

- [ ] **User Setup**
  - [ ] Non-root user created: `deployer`
  - [ ] User added to docker group
  - [ ] SSH keys configured for deployment
  - [ ] Sudo access configured (if needed)

### Domain & DNS Phase (Stream 6B: DNS & SSL Configuration)

- [ ] **DNS Configuration**
  - [ ] Domain registered (e.g., researchflow.app)
  - [ ] DNS provider selected
  - [ ] A record: researchflow.app → VPS_IP
  - [ ] AAAA record: researchflow.app → VPS_IPV6 (if applicable)
  - [ ] CNAME: www.researchflow.app → researchflow.app
  - [ ] DNS propagation verified (typically 24-48 hours)
  - [ ] DNS TTL reduced to 300s (for faster updates)

- [ ] **SSL/TLS Certificate**
  - [ ] Certbot installed: `sudo apt install certbot`
  - [ ] Certificate obtained: `certbot certonly --standalone`
  - [ ] Certificate path: `/etc/letsencrypt/live/researchflow.app/`
  - [ ] Certificate symlinked to: `./certs/fullchain.pem` and `./certs/privkey.pem`
  - [ ] Auto-renewal configured (certbot renewal timer)
  - [ ] Certificate verified: `curl -vI https://researchflow.app`

- [ ] **Firewall Rules**
  - [ ] UFW rule: Allow 22 (SSH) from TRUSTED_IP
  - [ ] UFW rule: Allow 80 (HTTP) from anywhere
  - [ ] UFW rule: Allow 443 (HTTPS) from anywhere
  - [ ] UFW rule: Deny all inbound except above
  - [ ] UFW rule: Allow all outbound
  - [ ] Firewall status verified: `sudo ufw status`

### Repository Preparation Phase

- [ ] **Repository Setup**
  - [ ] Repository cloned: `git clone https://github.com/your-org/researchflow.git`
  - [ ] Branch: main checked out
  - [ ] Commits verified with git signatures
  - [ ] Deploy key configured (if private repo)
  - [ ] Repository ownership: `deployer` user

- [ ] **Directory Structure**
  - [ ] Created: `/home/deployer/researchflow/`
  - [ ] Created: `/home/deployer/researchflow/certs/`
  - [ ] Created: `/home/deployer/researchflow/data/`
  - [ ] Created: `/home/deployer/researchflow/logs/`
  - [ ] Created: `/home/deployer/researchflow/backups/`
  - [ ] Permissions: `deployer` owns all directories

- [ ] **Environment Configuration**
  - [ ] `.env.production.template` reviewed
  - [ ] `.env.production` created with secure values
  - [ ] POSTGRES_PASSWORD: Generated (32+ random chars)
  - [ ] REDIS_PASSWORD: Generated (32+ random chars)
  - [ ] JWT_SECRET: Generated (256+ random bits)
  - [ ] AI_API_KEYS: Populated from vault
  - [ ] DOMAIN: Set to researchflow.app
  - [ ] File permissions: `chmod 600 .env.production`

- [ ] **Certificate Setup**
  - [ ] Certbot certificates ready
  - [ ] Fullchain cert: `certs/fullchain.pem`
  - [ ] Private key: `certs/privkey.pem`
  - [ ] Permissions: `chmod 644 certs/*.pem`
  - [ ] Nginx volume mount verified

### Docker Deployment Phase (Stream 6D: Production Environment)

- [ ] **Docker Validation**
  - [ ] `docker-compose config` validation passes
  - [ ] All services defined correctly
  - [ ] Port mappings verified
  - [ ] Volume mounts verified
  - [ ] Network configuration checked
  - [ ] Health checks configured

- [ ] **Pre-Deployment Checks**
  - [ ] Run: `./deploy-docker-stack.sh` (dry-run mode)
  - [ ] Environment variables validated
  - [ ] Required tools available
  - [ ] Docker daemon running
  - [ ] Ports available (80, 443, 3001, 8000, etc.)
  - [ ] Disk space: 100+ GB free

- [ ] **Service Deployment**
  - [ ] Run: `./deploy-docker-stack.sh deploy`
  - [ ] Database services start (postgres, redis)
  - [ ] Migrations run successfully
  - [ ] API services start (orchestrator, worker)
  - [ ] Support services start (collab, guideline-engine)
  - [ ] Frontend service starts (web/nginx)
  - [ ] All services healthy (health checks pass)

- [ ] **Health Verification**
  - [ ] `./deploy-docker-stack.sh health` passes
  - [ ] Orchestrator: GET http://localhost:3001/health → 200
  - [ ] Worker: GET http://localhost:8000/health → 200
  - [ ] Collab: GET http://localhost:1234/health → 200
  - [ ] Guideline Engine: GET http://localhost:8001/health → 200
  - [ ] PostgreSQL: `pg_isready` → accepting connections
  - [ ] Redis: `redis-cli ping` → PONG
  - [ ] Nginx: GET http://localhost/health → healthy

### Production Access Verification Phase

- [ ] **HTTPS Access**
  - [ ] HTTPS enabled: `https://researchflow.app`
  - [ ] Certificate valid (check certificate chain)
  - [ ] No SSL errors or warnings
  - [ ] HSTS header present
  - [ ] HTTP redirects to HTTPS: `http://researchflow.app` → `https://researchflow.app`

- [ ] **API Endpoints**
  - [ ] `/api/health` returns healthy
  - [ ] `/api/auth/login` accessible (test login)
  - [ ] `/api/` routes proxied correctly through Nginx
  - [ ] Rate limiting active (test with rapid requests)

- [ ] **Frontend Access**
  - [ ] React app loads: `https://researchflow.app`
  - [ ] Static assets load (JS, CSS, images)
  - [ ] WebSocket collaboration works: `/collab`
  - [ ] API calls from frontend succeed
  - [ ] User login flow works end-to-end

- [ ] **Service-to-Service Communication**
  - [ ] Orchestrator can reach PostgreSQL
  - [ ] Worker can reach PostgreSQL
  - [ ] All services can reach Redis
  - [ ] Collab can reach Redis
  - [ ] Internal network isolation verified

### Monitoring & Logging Phase (Stream 6E: Monitoring & Alerts)

- [ ] **Log Configuration**
  - [ ] Log directory: `/home/deployer/researchflow/logs/`
  - [ ] Docker logs accessible: `docker-compose logs`
  - [ ] Service logs populated
  - [ ] Log rotation configured (json-file driver)
  - [ ] Log viewing: `docker-compose logs -f [service]`

- [ ] **Resource Monitoring**
  - [ ] Docker stats available: `docker stats`
  - [ ] CPU usage monitored per service
  - [ ] Memory usage monitored per service
  - [ ] Disk usage monitored
  - [ ] Network traffic monitored

- [ ] **Health Checks**
  - [ ] Liveness checks working (services restart if unhealthy)
  - [ ] Readiness checks working (services wait before accepting traffic)
  - [ ] Health check intervals appropriate
  - [ ] False positives monitored/minimized

- [ ] **Backup Configuration**
  - [ ] Daily database backup scheduled (cron job)
  - [ ] Weekly volume backup scheduled
  - [ ] Configuration backup automated
  - [ ] Backup storage location: `/home/deployer/researchflow/backups/`
  - [ ] Off-site backup (cloud storage) configured
  - [ ] Restore test completed successfully

- [ ] **Monitoring Tools (Optional)**
  - [ ] Prometheus scraping metrics (if configured)
  - [ ] Grafana dashboards viewing (if configured)
  - [ ] Alert rules configured (if using AlertManager)
  - [ ] Email alerts configured (if using Alertmanager)
  - [ ] Slack notifications (optional)

### Security Hardening Phase

- [ ] **Database Security**
  - [ ] PostgreSQL password: Strong (32+ chars, random)
  - [ ] PostgreSQL user: Limited to researchflow DB
  - [ ] PostgreSQL SSL: Enforced (sslmode=require)
  - [ ] PostgreSQL backup: Encrypted/secured
  - [ ] PostgreSQL connections: Limited to authenticated only

- [ ] **Redis Security**
  - [ ] Redis password: Strong (32+ chars, random)
  - [ ] Redis TLS: Enabled (--tls-port 6379)
  - [ ] Redis auth: Required for all connections
  - [ ] Redis persistence: Appendonly enabled
  - [ ] Redis data: No public network access

- [ ] **API Security**
  - [ ] JWT secrets: Unique per environment
  - [ ] Rate limiting: Configured at Nginx level
  - [ ] CORS: Restricted to known origins
  - [ ] Session management: Secure & isolated
  - [ ] HTTPS/TLS: Enforced for all traffic

- [ ] **Network Security**
  - [ ] Firewall rules: Only required ports open
  - [ ] Internal services: No external network access
  - [ ] SSH: Key-based only, password disabled
  - [ ] VPC/Network isolation: If applicable
  - [ ] DDoS protection: Cloudflare/similar (optional)

- [ ] **Secrets Management**
  - [ ] `.env.production`: Not in version control
  - [ ] AI API keys: In environment only (not logs)
  - [ ] Database passwords: Rotated if necessary
  - [ ] JWT secrets: Unique and secure
  - [ ] Backup encryption: Enabled where possible

### Performance Tuning Phase

- [ ] **PostgreSQL Tuning**
  - [ ] shared_buffers: Set to 25% of RAM (8 GB)
  - [ ] effective_cache_size: Set to 75% of RAM (24 GB)
  - [ ] maintenance_work_mem: Set appropriately (512 MB)
  - [ ] max_connections: Set to 200 (default)
  - [ ] Query performance: Slow queries identified

- [ ] **Redis Tuning**
  - [ ] maxmemory: Set to 1 GB
  - [ ] maxmemory-policy: Set to allkeys-lru (eviction)
  - [ ] Persistence: AOF enabled, fsync strategy optimized
  - [ ] Connection pooling: Configured in services

- [ ] **Nginx Tuning**
  - [ ] worker_processes: Set to auto (16 processes)
  - [ ] worker_connections: Set to 1024 per process
  - [ ] Gzip compression: Enabled for text assets
  - [ ] Buffer sizes: Optimized for upstream
  - [ ] Timeout values: Appropriate for long-running ops

- [ ] **Docker Resource Limits**
  - [ ] CPU limits: Enforced per service
  - [ ] Memory limits: Enforced per service
  - [ ] Swap disabled (recommended for databases)
  - [ ] Overcommit ratio: Monitored

### Testing & Validation Phase

- [ ] **Functional Testing**
  - [ ] User registration flow works
  - [ ] User login flow works
  - [ ] Dashboard loads and is interactive
  - [ ] Create new research project (workflow)
  - [ ] Upload research data/files
  - [ ] AI analysis features work
  - [ ] Collaboration features work
  - [ ] Export functionality works

- [ ] **Load Testing**
  - [ ] Concurrent users: Test 10 users
  - [ ] API response times: < 200ms (p95)
  - [ ] Database query times: < 100ms (p95)
  - [ ] Memory usage stable (no leaks)
  - [ ] CPU usage: < 80% at 10 concurrent users

- [ ] **Failure Recovery Testing**
  - [ ] Service restart: Services recover automatically
  - [ ] Database restart: Data persists correctly
  - [ ] Network interruption: Services timeout gracefully
  - [ ] Disk full: Services handle gracefully
  - [ ] Log rotation: Old logs archived

- [ ] **Security Testing**
  - [ ] SQL injection attempts: Blocked
  - [ ] XSS attacks: Prevented
  - [ ] CSRF attacks: Prevented
  - [ ] Authentication bypass: Not possible
  - [ ] Authorization enforcement: Verified

### Documentation & Handoff Phase

- [ ] **Runbooks Created**
  - [ ] VPS deployment runbook
  - [ ] Service restart procedures
  - [ ] Database backup/restore procedures
  - [ ] Log analysis guide
  - [ ] Troubleshooting guide

- [ ] **Operation Procedures**
  - [ ] Daily monitoring checklist
  - [ ] Weekly backup verification
  - [ ] Monthly security review
  - [ ] Quarterly performance review
  - [ ] Incident response procedures

- [ ] **Access & Credentials**
  - [ ] Admin SSH access documented (secure handoff)
  - [ ] Database credentials documented (secure vault)
  - [ ] API keys documented (secure vault)
  - [ ] Backup locations documented
  - [ ] Emergency contacts listed

- [ ] **Knowledge Transfer**
  - [ ] Ops team trained on monitoring
  - [ ] Ops team trained on incident response
  - [ ] Support team trained on troubleshooting
  - [ ] Documentation reviewed for accuracy
  - [ ] Q&A session completed

---

## Summary Table

| Task | File/Component | Status | Details |
|------|---|---|---|
| 5A.1a | docker-compose.prod.yml | ✅ DONE | 465 lines, 7 services, all configs |
| 5A.1b | nginx.conf | ✅ DONE | 295 lines, SSL/rate limiting/caching |
| 5A.1c | deploy-docker-stack.sh | ✅ DONE | 622 lines, full automation + validation |
| 5A.1d | .env.production.template | ✅ DONE | 147 lines, all required variables |
| 5A.2a | ROS-26 (VPS Deployment) | ⏳ PENDING | Linear tracking issue, Urgent |
| 5A.2b | ROS-62 (Docker Config) | ✅ DONE | Completed Jan 29, all deliverables |
| 5A.2c | ROS-50 (HIPAA Compliance) | ⏳ PHASE 7 | Backlog, critical priority |
| 5A.3 | Infrastructure Specs | ✅ DONE | VPS specs, storage, network, DNS, SSL |
| 5A.4 | Deployment Checklist | ✅ COMPLETE | Comprehensive pre-flight checklist |

---

## Next Steps (Track 5A → Phase 6)

### Immediate (This Week)
1. **Stream 6A - VPS Provisioning**
   - Select Hetzner CX52 (or equivalent)
   - Provision VPS instance
   - Configure SSH access
   - Install Docker and dependencies

2. **Stream 6B - DNS & SSL**
   - Register domain (researchflow.app)
   - Configure DNS records
   - Obtain SSL certificate (Let's Encrypt via Certbot)
   - Setup auto-renewal

### Short-term (2-3 Weeks)
3. **Stream 6D - Deployment**
   - Deploy using `deploy-docker-stack.sh`
   - Verify all health checks pass
   - Test end-to-end functionality

4. **Stream 6E - Monitoring**
   - Configure logging and monitoring
   - Setup backups (daily PostgreSQL, weekly volumes)
   - Test restore procedures

### Post-Launch
5. **Stream 6C - CI/CD**
   - Setup GitHub Actions workflow
   - Automate builds and deployments
   - Configure staging vs production

6. **Phase 7 - HIPAA Compliance**
   - Complete data flow mapping
   - Document incident response
   - Business associate agreements
   - Compliance audit

---

## Key Deployment Information

**VPS Recommendation:** Hetzner CX52 (€32.40/month)
- 16 vCPU, 32 GB RAM, 320 GB SSD

**Docker Services:** 7 total
- PostgreSQL (database)
- Redis (cache)
- Orchestrator (API)
- Worker (processing)
- Guideline Engine (clinical)
- Collab (real-time)
- Web/Nginx (frontend)

**Domain:** researchflow.app (to be configured)

**SSL/TLS:** Let's Encrypt (automatic renewal)

**Backups:** Daily (PostgreSQL), Weekly (volumes)

**Monitoring:** Docker stats, health checks, logging

---

**Document Status:** Complete - Ready for Stream 6A (VPS Provisioning)
**Last Updated:** January 29, 2026
**Track:** Track 5A - VPS Deployment Planning
