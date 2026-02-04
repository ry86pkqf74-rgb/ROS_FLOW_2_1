# File Comparison Analysis: PR Extracted Files vs Current Repository

## Executive Summary
Four `.new` files have been extracted from PR branches. These represent enhanced configurations and scripts for production deployment. All target directories exist and are properly structured.

---

## Detailed File-by-File Analysis

### 1. .env.docker.new vs .env.example

#### Target File Status
- **Current .env.example exists?** YES (4,255 bytes, 114 lines)
- **Current .env file exists?** YES (1,019 bytes)
- **New file size:** 3,943 bytes, 173 lines

#### Key Differences

| Aspect | .env.example | .env.docker.new |
|--------|--------------|-----------------|
| **Purpose** | Production reference | Docker dev environment |
| **Focus** | ML/AI infrastructure (Ollama, Triton, FAISS) | Application stack (DB, Redis, Auth, APIs) |
| **Environment Type** | `production` | `development` (implied Docker setup) |
| **Config Sections** | 12 major sections | 20+ structured sections |
| **Variable Count** | ~56 variables | ~66 variables |
| **Unique in .docker.new** | API Keys (OpenAI, Anthropic, Claude, Grok, etc.), Chat agent, Dashboard settings, Integrations (Slack, Figma, GitHub) |
| **Unique in .example** | Ollama/Triton/FAISS settings, Prometheus/Grafana, AWS deployment settings, Resource limits |

#### Key New Variables in .env.docker.new
- `AI_INTEGRATIONS_*` (OpenAI, Anthropic, XAI, Mercury)
- `AUTH_ALLOW_STATELESS_JWT`
- `CHAT_AGENT_*` configuration
- `DASHBOARD_*` settings
- Integration API keys (Figma, GitHub, Slack, Notion)
- `LOCAL_MODEL_*` for Ollama
- `SOURCEGRAPH_API_KEY`

#### Recommendation: **MERGE (Create as .env.docker-example)**

**Rationale:**
- Both files serve different purposes (.example is production/ML-focused, .docker.new is development/app-focused)
- They complement rather than replace each other
- Action: Keep .env.example as-is, create new .env.docker-example from .env.docker.new
- This allows developers to use appropriate templates: `cp .env.docker-example .env` for Docker dev or `cp .env.example .env` for production setup

---

### 2. infrastructure/nginx/nginx.prod.conf.new vs infrastructure/docker/nginx/nginx.conf

#### Target File Status
- **Existing nginx.conf location:** `/infrastructure/docker/nginx/nginx.conf` (294 lines)
- **New file location:** `/infrastructure/nginx/nginx.prod.conf.new` (281 lines)
- **Target directory exists?** YES (but nginx.prod.conf doesn't exist)

#### Key Differences

| Feature | docker/nginx.conf | nginx.prod.conf.new |
|---------|-------------------|---------------------|
| **Purpose** | Docker dev/general purpose | Production-hardened |
| **TLS/HTTPS** | Not configured | Full TLS 1.2/1.3 with certs |
| **Security Headers** | Basic | Enhanced (CSP, HSTS, X-Frame-Options, etc.) |
| **Logging Format** | Basic | Detailed with response times |
| **Rate Limiting Zones** | api, login | api, login, upload |
| **Upstreams** | orchestrator, web, collab, worker, guideline_engine | Same + health checks |
| **SSL Certificates** | Not referenced | `/etc/nginx/certs/server.crt/key` |
| **HTTP Redirect** | Not present | HTTP -> HTTPS (port 80 -> 443) |

#### Critical New Features in nginx.prod.conf.new
1. **SSL/TLS Configuration**
   - TLS 1.2 and 1.3 only
   - Certificate paths: `/etc/nginx/certs/`
   - HSTS header with 1-year max-age

2. **Security Headers**
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`

3. **Rate Limiting**
   - New upload rate limit zone
   - File upload timeouts: 600s (10 minutes)

4. **Cache Control**
   - JS/CSS: 1-year cache with immutable flag
   - Images/Fonts: 30-day cache
   - HTML: no-cache for fast rollouts

#### Comparison Output
```
docker/nginx.conf                nginx.prod.conf.new
[Basic dev config]        =>     [Production-hardened]
No TLS/HTTPS             =>     Full TLS 1.2/1.3
No security headers      =>     Comprehensive security headers
Basic logging            =>     Detailed metrics logging
Dev rate limits          =>     Production rate limiting
No cache headers         =>     Smart cache strategy
```

#### Recommendation: **ADD as separate file (nginx.prod.conf)**

**Rationale:**
- These are fundamentally different configurations for different environments
- Merging would require complex conditional logic
- Better to have environment-specific configs: 
  - `nginx.conf` for development (already in docker/)
  - `nginx.prod.conf` for production (new, in infrastructure/nginx/)
- Action: Move `nginx.prod.conf.new` to `infrastructure/nginx/nginx.prod.conf` (remove .new)

---

### 3. scripts/docker-deploy-prod.sh.new vs scripts/deploy.sh

#### Target File Status
- **scripts/ directory exists?** YES (with 48 files)
- **Existing deploy.sh exists?** YES (142 lines)
- **New docker-deploy-prod.sh.new:** 241 lines

#### Key Differences

| Aspect | deploy.sh | docker-deploy-prod.sh.new |
|--------|-----------|--------------------------|
| **Target** | Kubernetes deployment | Docker Compose deployment |
| **Required Tools** | kubectl, Docker registry | Docker, Docker Compose |
| **Environment** | Staging/Production via k8s | Docker Compose containers |
| **Config Source** | Kubernetes manifests | .env.production file |
| **Options** | (interactive confirmation) | --build, --pull, --clean, --dry-run flags |
| **Certificate Handling** | Not explicit | Checks ./certs/ for SSL |
| **Prerequisites Check** | kubectl context validation | Docker, certs, .env files |

#### Key Features in docker-deploy-prod.sh.new
1. **Command-line options**
   - `--build`: Rebuild images
   - `--pull`: Pull latest base images
   - `--clean`: Remove old images
   - `--dry-run`: Show without executing

2. **Validation**
   - Checks for required files (.env.production, certs/)
   - Verifies Docker/Docker Compose installation
   - Validates certificate files

3. **Deployment Steps**
   - Stops existing containers
   - Builds/pulls images (if requested)
   - Creates certs directory if needed
   - Starts with docker-compose
   - Performs health checks
   - Cleans old images (if requested)

#### Comparison Output
```
deploy.sh                     docker-deploy-prod.sh.new
[K8s deployment]       =>     [Docker Compose deployment]
kubectl context        =>     Docker/Docker Compose
Registry images        =>     Local Docker build
Manifests              =>     docker-compose.yml + .env
Interactive prompt     =>     Flexible CLI options
No cert validation     =>     Explicit cert checks
```

#### Recommendation: **ADD as new file (docker-deploy-prod.sh)**

**Rationale:**
- These serve different deployment paradigms (Kubernetes vs Docker Compose)
- Both may be needed in the project
- deploy.sh is for Kubernetes orchestration
- docker-deploy-prod.sh is for Docker Compose production
- Action: Keep deploy.sh, add docker-deploy-prod.sh as new file
- Make both executable: `chmod +x scripts/docker-deploy-prod.sh`

---

### 4. scripts/generate-dev-certs.sh.new vs (no existing cert script)

#### Target File Status
- **Existing certificate scripts in scripts/?** NO
- **generate-dev-certs.sh.new:** 234 lines, created Jan 30, 2026
- **Is this truly new?** YES - unique functionality not elsewhere

#### Functionality

**What generate-dev-certs.sh.new does:**

1. **Creates SSL Certificates**
   - CA certificate (self-signed)
   - Server certificate for HTTPS
   - Redis TLS certificates
   - PostgreSQL TLS certificates

2. **Directory Structure**
   - `./certs/` - nginx certificates
   - `./certs/redis/` - Redis certificates
   - `./certs/postgres/` - PostgreSQL certificates

3. **Configuration Options**
   - Validity period (default 365 days)
   - Common Name (default: localhost)
   - Organization name (default: ResearchFlow Development)

4. **Certificate Features**
   - Self-signed (suitable for development)
   - Proper key sizes (2048-bit RSA)
   - Certificate bundle generation
   - Clear instructions for production use

#### Key Script Sections
```bash
1. CA certificate generation (root signing certificate)
2. Server certificate signing request
3. Server certificate signing
4. Redis TLS certificates
5. PostgreSQL TLS certificates
6. Certificate verification
7. Ownership setup (for Docker)
```

#### Comparison with Missing Functionality
**What existed before:** Nothing for development certificate generation
**What this provides:** 
- Automated setup for all TLS certificates needed
- Replaces manual OpenSSL commands
- Developer-friendly with clear output

#### Recommendation: **ADD as new file (generate-dev-certs.sh)**

**Rationale:**
- Fills a critical gap in development setup
- No existing functionality to preserve
- Complements generate-dev-certs.sh.new requirements
- Action: Add as `scripts/generate-dev-certs.sh`
- Make executable: `chmod +x scripts/generate-dev-certs.sh`
- Document in setup instructions

---

## Directory Structure Status

### scripts/ Directory
**Status:** EXISTS - Contains 48 files
**Current structure:**
```
scripts/
├── Deployment scripts (deploy.sh, docker-build.sh, etc.)
├── Database scripts (db-migrate.sh)
├── Testing scripts (test-*.sh, smoke-test.sh)
├── Setup scripts (setup.sh, setup-github-secrets.sh)
├── Validation scripts (validate-environment.sh, health-check.sh)
├── Docker subdirectory (docker/)
├── subdirectories (governance/, lora/)
└── Python scripts (generate-test-data.py, propose_prompt_update.py)
```

**Files to add:**
- ✅ docker-deploy-prod.sh.new → docker-deploy-prod.sh
- ✅ generate-dev-certs.sh.new → generate-dev-certs.sh

### infrastructure/nginx/ Directory
**Status:** EXISTS - Currently contains only .new files
**Current structure:**
```
infrastructure/nginx/
└── nginx.prod.conf.new (281 lines)
```

**Files to add:**
- ✅ nginx.prod.conf.new → nginx.prod.conf (remove .new suffix)

**Related existing nginx config:**
- `infrastructure/docker/nginx/nginx.conf` (294 lines) - keep as dev config

### deploy/ Directory
**Status:** EXISTS - Contains deployment configs
**Current structure:**
```
deploy/
├── ai-monitoring.yml
├── alert-rules.yml
├── feature-flags.json
├── feature-rollout.sh
├── grafana-datasources.yml
└── prometheus.yml
```
**Note:** No changes needed for deploy/

---

## Consolidated Recommendations Summary

| File | Current Status | Action | Reason |
|------|---|--------|--------|
| **.env.docker.new** | No target exists | **MERGE** → Create `.env.docker-example` | Complements .env.example; different purpose (dev vs prod) |
| **nginx.prod.conf.new** | No .prod config exists | **ADD** → `infrastructure/nginx/nginx.prod.conf` | Production-hardened; different from dev docker/nginx.conf |
| **docker-deploy-prod.sh.new** | No Docker deploy script exists | **ADD** → `scripts/docker-deploy-prod.sh` | Complements K8s deploy.sh; different deployment method |
| **generate-dev-certs.sh.new** | No cert script exists | **ADD** → `scripts/generate-dev-certs.sh` | Fills critical gap in setup process |

---

## Implementation Steps

### Step 1: Handle Environment Files
```bash
# Copy new env file with clear naming
cp .env.docker.new .env.docker-example
# Verify both env templates exist
ls -la .env.example .env.docker-example
```

### Step 2: Add Production Nginx Config
```bash
# Move to production-specific location
mv infrastructure/nginx/nginx.prod.conf.new infrastructure/nginx/nginx.prod.conf
# Keep dev config in docker/
ls -la infrastructure/nginx/nginx.prod.conf infrastructure/docker/nginx/nginx.conf
```

### Step 3: Add Deployment Scripts
```bash
# Add Docker Compose deployment script
mv scripts/docker-deploy-prod.sh.new scripts/docker-deploy-prod.sh
chmod +x scripts/docker-deploy-prod.sh

# Add certificate generation script
mv scripts/generate-dev-certs.sh.new scripts/generate-dev-certs.sh
chmod +x scripts/generate-dev-certs.sh
```

### Step 4: Verify Structure
```bash
# Check all new files are in place
find scripts/ -name "docker-deploy-prod.sh" -o -name "generate-dev-certs.sh"
find infrastructure/nginx -name "nginx.prod.conf"
grep -l "docker-example" .env*
```

---

## Risk Assessment

### Low Risk Changes
- ✅ Adding .env.docker-example (no conflicts)
- ✅ Adding infrastructure/nginx/nginx.prod.conf (new location)
- ✅ Adding scripts/docker-deploy-prod.sh (no conflicts)
- ✅ Adding scripts/generate-dev-certs.sh (no conflicts)

### Validation Required
- [ ] Verify nginx.prod.conf syntax with `nginx -t`
- [ ] Test docker-deploy-prod.sh with --dry-run flag
- [ ] Verify generate-dev-certs.sh creates certificates in correct locations
- [ ] Test .env.docker-example loads without errors

---

## Documentation Updates Needed

After implementing these files, update:
1. **README.md** - Add Docker Compose deployment instructions
2. **SETUP.md** - Reference .env.docker-example for Docker dev
3. **DEPLOYMENT.md** - Document both K8s and Docker Compose deployment methods
4. **Infrastructure README** - Explain nginx.prod.conf usage
5. **CONTRIBUTING.md** - Add certificate generation step to setup

