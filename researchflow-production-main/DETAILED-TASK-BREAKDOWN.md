# ResearchFlow Detailed Task Breakdown

**Every task with specific steps, commands, and agent assignments**

---

## PHASE 1: CRITICAL BLOCKERS RESOLUTION

### Track 1A: Security Resolution (ROS-51)
**Agent:** Grok (Security) via Claude Subagent
**Duration:** 1-2 hours

#### Task 1A.1: Analyze GitGuardian Alert
```
Agent: Claude Subagent
Tool: Linear MCP (mcp__742c6b31__get_issue)
Steps:
  1. Fetch issue ROS-51 details from Linear
  2. Extract GitGuardian alert URL/reference
  3. Identify credential type (generic password, API key, etc.)
  4. Document exposure date (Jan 18, 2026)
  5. Identify affected file/commit
Output: Report with credential type, location, exposure window
```

#### Task 1A.2: Search Repository for Exposed Secrets
```
Agent: Claude Subagent
Tool: Desktop Commander (start_search)
Steps:
  1. Search for pattern "password=" in all files
     Command: start_search(searchType="content", pattern="password=", path="/repo")
  2. Search for pattern "secret="
  3. Search for pattern "api_key="
  4. Search for pattern "token="
  5. Check .env, .env.*, config/*.json, docker-compose*.yml
  6. List all files containing potential secrets
Output: List of files with line numbers containing secrets
```

#### Task 1A.3: Generate New Secure Credentials
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Generate new password:
     openssl rand -base64 32
  2. Generate new JWT secret:
     openssl rand -hex 64
  3. Generate new database password:
     openssl rand -base64 24
  4. Store new credentials securely (NOT in repo)
  5. Document credential mapping (old reference → new)
Output: New credential set (stored securely, not logged)
```

#### Task 1A.4: Update Environment Files
```
Agent: Claude Subagent
Tool: Desktop Commander (edit_block)
Steps:
  1. Read current .env.example
  2. Update placeholder values with new credential references
  3. Update docker-compose.yml environment sections
  4. Update any hardcoded values in config files
  5. Verify no actual secrets in committed files
Commands:
  edit_block(file_path=".env.example", old_string="OLD_SECRET", new_string="NEW_SECRET_REF")
Output: Updated config files with new credential references
```

#### Task 1A.5: Clean Git History
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Install BFG Repo Cleaner:
     brew install bfg
  2. Create passwords.txt with exposed secrets
  3. Run BFG to remove secrets:
     bfg --replace-text passwords.txt
  4. Clean repository:
     git reflog expire --expire=now --all
     git gc --prune=now --aggressive
  5. Force push cleaned history:
     git push origin --force --all
  6. Notify team to re-clone
Output: Clean git history, no secrets in any commit
```

#### Task 1A.6: Verify Old Credentials Invalidated
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Test old database password fails:
     PGPASSWORD=old_pass psql -h localhost -U researchflow -d researchflow -c "SELECT 1"
  2. Test old API keys return 401
  3. Check external services (if any) reject old creds
  4. Verify GitGuardian alert can be marked resolved
  5. Document verification results
Output: Confirmation all old credentials rejected
```

---

### Track 1B: TypeScript Verification (ROS-59)
**Agent:** GPT-4/Cursor via Claude Subagent
**Duration:** 1-2 hours

#### Task 1B.1: Verify Type Packages Installed
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Navigate to orchestrator:
     cd services/orchestrator
  2. Check installed type packages:
     npm ls @types/express @types/node typescript
  3. Verify versions match requirements:
     @types/express@4.17.17 or compatible
     @types/node@20.x
     typescript@5.x
  4. If missing, install:
     npm install @types/express@4.17.17 --save-dev
Output: Confirmation of correct type package versions
```

#### Task 1B.2: Run TypeScript Type Check
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Run type check:
     npx tsc --noEmit 2>&1 | tee typecheck.log
  2. Count errors:
     grep -c "error TS" typecheck.log
  3. If errors > 0, categorize by type:
     grep "error TS" typecheck.log | cut -d':' -f1 | sort | uniq -c
  4. Document top error files
  5. Compare against baseline (was 2199, should be <1200)
Output: Type check results with error count and categorization
```

#### Task 1B.3: Verify Build Succeeds
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Clean previous build:
     rm -rf dist/
  2. Run production build:
     npm run build
  3. Verify dist/ directory created:
     ls -la dist/
  4. Check for build errors in output
  5. Verify main entry point exists:
     ls dist/index.js
Output: Successful build with dist/ directory populated
```

#### Task 1B.4: Run Unit Tests
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Run test suite:
     npm test 2>&1 | tee test.log
  2. Check test results:
     grep -E "(passed|failed|pending)" test.log
  3. If failures, document failing tests
  4. Verify coverage threshold met (if configured)
  5. Document test summary
Output: Test results with pass/fail counts
```

---

## PHASE 2: BACKEND SERVICES DEPLOYMENT

### Track 2A: Database & Cache Layer
**Agent:** Claude (Primary)
**Duration:** 1 hour

#### Task 2A.1: Validate Environment Variables
```
Agent: Claude Subagent
Tool: Desktop Commander (read_file)
Steps:
  1. Read .env file:
     read_file(path=".env")
  2. Verify required variables present:
     - DATABASE_URL=postgresql://user:pass@postgres:5432/researchflow
     - REDIS_URL=redis://redis:6379
     - NODE_ENV=production
     - JWT_SECRET=<set>
     - ENCRYPTION_KEY=<set>
  3. Check no placeholder values remain
  4. Verify secrets are not exposed
  5. Document any missing variables
Output: Environment validation report
```

#### Task 2A.2: Start PostgreSQL Container
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Pull latest postgres image:
     docker pull postgres:15-alpine
  2. Start PostgreSQL:
     docker compose up -d postgres
  3. Wait for startup (30 seconds):
     sleep 30
  4. Check container running:
     docker compose ps postgres
  5. Verify ready:
     docker compose exec postgres pg_isready -U researchflow
Output: PostgreSQL container running and ready
```

#### Task 2A.3: Run Database Migrations
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check migration status:
     docker compose exec orchestrator npx drizzle-kit status
  2. Run pending migrations:
     docker compose exec orchestrator npx drizzle-kit migrate
  3. Verify tables created:
     docker compose exec postgres psql -U researchflow -c "\dt"
  4. Check for migration errors
  5. Document applied migrations
Output: Database schema up to date
```

#### Task 2A.4: Start Redis Container
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Pull latest redis image:
     docker pull redis:7-alpine
  2. Start Redis:
     docker compose up -d redis
  3. Wait for startup:
     sleep 10
  4. Verify running:
     docker compose ps redis
  5. Test connectivity:
     docker compose exec redis redis-cli ping
     Expected: PONG
Output: Redis container running and responding
```

#### Task 2A.5: Verify Database Connectivity
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Test from orchestrator network:
     docker compose exec orchestrator node -e "
       const { Pool } = require('pg');
       const pool = new Pool({connectionString: process.env.DATABASE_URL});
       pool.query('SELECT NOW()').then(r => console.log('DB OK:', r.rows[0]));
     "
  2. Test Redis from orchestrator:
     docker compose exec orchestrator node -e "
       const Redis = require('ioredis');
       const redis = new Redis(process.env.REDIS_URL);
       redis.ping().then(r => console.log('Redis OK:', r));
     "
  3. Document connection times
Output: Both database connections verified from orchestrator
```

---

### Track 2B: Node.js Orchestrator Service
**Agent:** GPT-4/Cursor via Claude Subagent
**Duration:** 1.5 hours

#### Task 2B.1: Build Orchestrator Image
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check Dockerfile exists:
     ls services/orchestrator/Dockerfile
  2. Build image with no cache:
     docker compose build --no-cache orchestrator
  3. Verify image created:
     docker images | grep orchestrator
  4. Check image size (should be < 500MB)
  5. Document build time
Output: Orchestrator Docker image built successfully
```

#### Task 2B.2: Start Orchestrator Service
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Start service:
     docker compose up -d orchestrator
  2. Wait for startup:
     sleep 20
  3. Check container status:
     docker compose ps orchestrator
  4. View startup logs:
     docker compose logs --tail=50 orchestrator
  5. Verify no error messages in logs
Output: Orchestrator container running
```

#### Task 2B.3: Verify Health Endpoint
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Wait for service ready:
     sleep 10
  2. Test health endpoint:
     curl -s http://localhost:3001/health
  3. Expected response:
     {"status":"healthy","version":"x.x.x","uptime":...}
  4. Test readiness:
     curl -s http://localhost:3001/ready
  5. Document response times
Output: Health endpoint returning 200 OK
```

#### Task 2B.4: Test Authentication Endpoints
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Test login endpoint exists:
     curl -s -X POST http://localhost:3001/api/auth/login \
       -H "Content-Type: application/json" \
       -d '{"email":"test@test.com","password":"test"}'
  2. Verify returns 401 (unauthorized) not 404
  3. Test register endpoint:
     curl -s -X POST http://localhost:3001/api/auth/register \
       -H "Content-Type: application/json" \
       -d '{"email":"test@test.com","password":"test","name":"Test"}'
  4. Document endpoint responses
Output: Auth endpoints responding correctly
```

#### Task 2B.5: Verify AI Router Connectivity
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check AI router health:
     curl -s http://localhost:3001/api/ai/health
  2. Verify configured providers:
     curl -s http://localhost:3001/api/ai/providers
  3. Test routing (dry run):
     curl -s -X POST http://localhost:3001/api/ai/route \
       -H "Content-Type: application/json" \
       -d '{"task":"test","dryRun":true}'
  4. Document available AI providers
Output: AI Router operational with configured providers
```

---

### Track 2C: Python Worker Service
**Agent:** Claude Subagent
**Duration:** 1.5 hours

#### Task 2C.1: Build Worker Image
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check Dockerfile:
     ls services/worker/Dockerfile
  2. Build image:
     docker compose build --no-cache worker
  3. Verify image:
     docker images | grep worker
  4. Check Python dependencies included
  5. Document build time
Output: Worker Docker image built successfully
```

#### Task 2C.2: Start Worker Service
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Start service:
     docker compose up -d worker
  2. Wait for startup:
     sleep 30
  3. Check status:
     docker compose ps worker
  4. View logs:
     docker compose logs --tail=50 worker
  5. Verify FastAPI startup complete
Output: Worker container running
```

#### Task 2C.3: Verify Health Endpoint
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Test health:
     curl -s http://localhost:8000/health
  2. Expected: {"status":"healthy"}
  3. Test OpenAPI docs available:
     curl -s http://localhost:8000/docs
  4. Document response
Output: Worker health endpoint returning 200 OK
```

#### Task 2C.4: Test Agent Registration
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check registered agents:
     curl -s http://localhost:8000/api/agents
  2. Verify DataPrep agent present (ROS-65 completed)
  3. Check agent capabilities:
     curl -s http://localhost:8000/api/agents/dataprep/capabilities
  4. Test agent health:
     curl -s http://localhost:8000/api/agents/dataprep/health
  5. Document registered agents
Output: Agents registered and responding
```

#### Task 2C.5: Verify 20-Stage Workflow
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Get workflow schema:
     curl -s http://localhost:8000/api/workflow/schema
  2. Verify all 20 stages defined:
     curl -s http://localhost:8000/api/workflow/stages | jq '. | length'
  3. Test stage 1 (Data Collection):
     curl -s http://localhost:8000/api/workflow/stages/1
  4. Verify Pandera validation active:
     curl -s http://localhost:8000/api/workflow/validation/status
  5. Document workflow configuration
Output: 20-stage workflow configured and validated
```

---

## PHASE 3: FRONTEND & INTEGRATION SERVICES

### Track 3A: React Web Application
**Agent:** Mercury/v0 via Claude Subagent
**Duration:** 1 hour

#### Task 3A.1: Build Web Image
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check Vite config:
     ls services/web/vite.config.ts
  2. Build production image:
     docker compose build --no-cache web
  3. Verify image:
     docker images | grep web
  4. Check build output size
  5. Verify static assets included
Output: Web Docker image built
```

#### Task 3A.2: Start Web Service
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Start service:
     docker compose up -d web
  2. Wait for startup:
     sleep 15
  3. Check status:
     docker compose ps web
  4. View logs:
     docker compose logs --tail=30 web
Output: Web container running
```

#### Task 3A.3: Verify Static Files Served
```
Agent: Claude Subagent
Tool: Chrome MCP / Bash
Steps:
  1. Test main page:
     curl -s http://localhost:5173 | head -20
  2. Verify HTML returned
  3. Test static assets:
     curl -s http://localhost:5173/assets/index.js | head -5
  4. Check for 404 errors
  5. Verify Vite dev server or production build
Output: Static files serving correctly
```

#### Task 3A.4: Test API Connectivity
```
Agent: Claude Subagent
Tool: Chrome MCP
Steps:
  1. Open browser to http://localhost:5173
  2. Open DevTools Network tab
  3. Check API calls to localhost:3001
  4. Verify CORS headers present
  5. Check for connection errors
  6. Document any failed requests
Output: Frontend connecting to backend API
```

#### Task 3A.5: Verify Authentication Flow
```
Agent: Claude Subagent
Tool: Chrome MCP
Steps:
  1. Navigate to login page
  2. Enter test credentials
  3. Submit login form
  4. Verify redirect to dashboard
  5. Check JWT token stored
  6. Verify protected routes accessible
  7. Test logout flow
Output: Authentication flow working end-to-end
```

---

### Track 3B: Collaboration Service
**Agent:** Claude Subagent
**Duration:** 45 minutes

#### Task 3B.1: Build Collab Image
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Build image:
     docker compose build --no-cache collab
  2. Verify image:
     docker images | grep collab
Output: Collab Docker image built
```

#### Task 3B.2: Start Collab Service
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Start service:
     docker compose up -d collab
  2. Wait:
     sleep 10
  3. Check status:
     docker compose ps collab
  4. View logs:
     docker compose logs --tail=30 collab
Output: Collab container running
```

#### Task 3B.3: Test WebSocket Connectivity
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Install wscat if needed:
     npm install -g wscat
  2. Test WebSocket connection:
     wscat -c ws://localhost:1234 --execute "ping"
  3. Verify connection established
  4. Check for upgrade headers
  5. Document connection time
Output: WebSocket connections working
```

#### Task 3B.4: Verify Yjs Document Sync
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Create test document via API
  2. Connect two WebSocket clients
  3. Make change from client 1
  4. Verify change appears in client 2
  5. Check sync latency < 100ms
  6. Document sync behavior
Output: Real-time collaboration syncing correctly
```

---

### Track 3C: Guideline Engine Service
**Agent:** GPT-4/Cursor via Claude Subagent
**Duration:** 45 minutes

#### Task 3C.1: Build Guideline Engine Image
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Build image:
     docker compose build --no-cache guideline-engine
  2. Verify:
     docker images | grep guideline-engine
Output: Guideline engine image built
```

#### Task 3C.2: Start Guideline Engine
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Start:
     docker compose up -d guideline-engine
  2. Wait:
     sleep 15
  3. Check:
     docker compose ps guideline-engine
  4. Logs:
     docker compose logs --tail=30 guideline-engine
Output: Guideline engine running
```

#### Task 3C.3: Verify Clinical Guidelines API
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Test health:
     curl -s http://localhost:8001/health
  2. Get available guidelines:
     curl -s http://localhost:8001/api/guidelines
  3. Test specific guideline lookup:
     curl -s http://localhost:8001/api/guidelines/fda-cfr-21
  4. Verify response format
  5. Document available guidelines
Output: Guidelines API responding with clinical data
```

#### Task 3C.4: Test Worker Integration
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. From worker, call guideline engine:
     curl -s http://localhost:8000/api/guidelines/check \
       -H "Content-Type: application/json" \
       -d '{"stage":1,"data":{"test":"value"}}'
  2. Verify worker can reach guideline engine
  3. Check response includes guideline validation
  4. Document integration status
Output: Worker successfully calling guideline engine
```

---

## PHASE 4: INTEGRATION TESTING & HIPAA

### Track 4A: End-to-End Testing
**Agent:** Claude (Primary)
**Duration:** 1.5 hours

#### Task 4A.1: Run Playwright E2E Tests
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Install Playwright browsers:
     npx playwright install
  2. Run full E2E suite:
     npx playwright test 2>&1 | tee e2e-results.log
  3. Check results:
     grep -E "(passed|failed|skipped)" e2e-results.log
  4. Generate HTML report:
     npx playwright show-report
  5. Document failures
Output: E2E test results with HTML report
```

#### Task 4A.2: Test Complete 20-Stage Workflow
```
Agent: Claude Subagent
Tool: Chrome MCP
Steps:
  1. Login to web application
  2. Create new research project
  3. Navigate to workflow view
  4. Complete Stage 1: Data Collection
     - Upload test dataset
     - Verify validation passes
  5. Progress through stages 2-5 (DataPrep agent)
  6. Verify each stage transition
  7. Check data persists between stages
  8. Document any errors
Output: Workflow stages 1-5 completing successfully
```

#### Task 4A.3: Verify Multi-Agent Execution Hub (ROS-63)
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check hub status:
     curl -s http://localhost:3001/api/agents/hub/status
  2. List registered agents:
     curl -s http://localhost:3001/api/agents/hub/agents
  3. Test concurrent agent dispatch:
     curl -s -X POST http://localhost:3001/api/agents/hub/dispatch \
       -H "Content-Type: application/json" \
       -d '{"agents":["dataprep","analysis"],"task":"test"}'
  4. Verify parallel execution
  5. Check result aggregation
Output: Multi-agent hub coordinating agents correctly
```

#### Task 4A.4: Test Claude Orchestrator Session (ROS-70)
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Create orchestrator session:
     curl -s -X POST http://localhost:3001/api/claude/session/create
  2. Send test message:
     curl -s -X POST http://localhost:3001/api/claude/session/{id}/message \
       -d '{"message":"Analyze this test data"}'
  3. Verify response received
  4. Check session state persisted
  5. Test session cleanup
Output: Claude orchestrator sessions working
```

---

### Track 4B: HIPAA Compliance Verification
**Agent:** Grok (Security) via Claude Subagent
**Duration:** 1.5 hours

#### Task 4B.1: Verify PHI Detection
```
Agent: Claude Subagent
Tool: Desktop Commander (start_search)
Steps:
  1. Search for PHI detection code:
     start_search(searchType="content", pattern="detectPHI|PHIDetector", path=".")
  2. Verify PHI engine exists:
     ls packages/phi-engine/
  3. Test PHI detection API:
     curl -s -X POST http://localhost:3001/api/phi/detect \
       -d '{"text":"Patient John Doe SSN 123-45-6789"}'
  4. Verify SSN detected
  5. Check detection before LLM calls
Output: PHI detection working before any LLM egress
```

#### Task 4B.2: Confirm Audit Logging Active
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Check audit log table:
     docker compose exec postgres psql -U researchflow \
       -c "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 5"
  2. Perform auditable action (login)
  3. Verify audit entry created
  4. Check log includes:
     - User ID
     - Action type
     - Timestamp
     - IP address
  5. Verify PHI access logged
Output: Audit logging capturing all required events
```

#### Task 4B.3: Test LLM Egress Policy (ROS-50)
```
Agent: LM Studio via Claude Subagent
Tool: Bash
Steps:
  1. Test LLM call with PHI:
     curl -s -X POST http://localhost:3001/api/ai/complete \
       -d '{"prompt":"Patient John Doe needs treatment","checkPHI":true}'
  2. Verify PHI blocked before LLM
  3. Test with sanitized data:
     curl -s -X POST http://localhost:3001/api/ai/complete \
       -d '{"prompt":"Patient [REDACTED] needs treatment","checkPHI":true}'
  4. Verify allowed through
  5. Check local LM Studio used for PHI-containing requests
Output: LLM egress policy blocking PHI correctly
```

#### Task 4B.4: Document Data Flow
```
Agent: Claude Subagent
Tool: Desktop Commander (write_file)
Steps:
  1. Map data flow from input to storage
  2. Document all external API calls
  3. Identify PHI touchpoints
  4. Create data flow diagram
  5. Save to compliance documentation
Output: HIPAA data flow documentation
```

#### Task 4B.5: Create Compliance Checklist
```
Agent: Claude Subagent
Tool: Notion MCP
Steps:
  1. Create new Notion page: "HIPAA Compliance Checklist"
  2. Add checklist items:
     - [ ] PHI detection enabled
     - [ ] Audit logging active
     - [ ] Encryption at rest
     - [ ] Encryption in transit
     - [ ] Access controls implemented
     - [ ] Backup procedures documented
  3. Link to Mission Control
Output: HIPAA checklist in Notion
```

---

## PHASE 5: PRODUCTION GO-LIVE

### Track 5A: VPS Deployment
**Agent:** Claude (Primary)
**Duration:** 1.5 hours

#### Task 5A.1: Provision Hetzner VPS
```
Agent: Claude Subagent
Tool: Bash (SSH)
Steps:
  1. Create CX52 instance via Hetzner API/Console:
     - 8 vCPU AMD
     - 16 GB RAM
     - 160 GB SSD
     - Ubuntu 22.04
  2. Note IP address
  3. Add SSH key
  4. Verify SSH access:
     ssh root@<IP> "hostname"
Output: VPS provisioned with SSH access
```

#### Task 5A.2: Configure Firewall
```
Agent: Claude Subagent
Tool: Bash (SSH)
Steps:
  1. SSH to server
  2. Configure UFW:
     ufw default deny incoming
     ufw default allow outgoing
     ufw allow ssh
     ufw allow 80/tcp
     ufw allow 443/tcp
  3. Enable firewall:
     ufw enable
  4. Verify rules:
     ufw status verbose
Output: Firewall configured with only needed ports
```

#### Task 5A.3: Install Docker
```
Agent: Claude Subagent
Tool: Bash (SSH)
Steps:
  1. Update system:
     apt update && apt upgrade -y
  2. Install Docker:
     curl -fsSL https://get.docker.com | sh
  3. Install Docker Compose:
     apt install docker-compose-plugin
  4. Verify installation:
     docker --version
     docker compose version
  5. Add user to docker group:
     usermod -aG docker $USER
Output: Docker and Compose installed
```

#### Task 5A.4: Deploy Production Stack
```
Agent: Claude Subagent
Tool: Bash (SSH)
Steps:
  1. Clone repository:
     git clone https://github.com/ry86pkqf74-rgb/researchflow-production.git
  2. Navigate to project:
     cd researchflow-production
  3. Copy production environment:
     cp .env.production .env
  4. Deploy stack:
     docker compose -f docker-compose.prod.yml up -d
  5. Verify all services running:
     docker compose ps
Output: Production stack deployed and running
```

#### Task 5A.5: Configure SSL/TLS
```
Agent: Claude Subagent
Tool: Bash (SSH)
Steps:
  1. Install Certbot:
     apt install certbot python3-certbot-nginx
  2. Obtain certificate:
     certbot --nginx -d researchflow.yourdomain.com
  3. Verify certificate:
     openssl s_client -connect researchflow.yourdomain.com:443
  4. Set up auto-renewal:
     systemctl enable certbot.timer
Output: SSL certificate installed and auto-renewing
```

#### Task 5A.6: Configure Nginx
```
Agent: Claude Subagent
Tool: Desktop Commander (write_file)
Steps:
  1. Create Nginx config:
     /etc/nginx/sites-available/researchflow
  2. Configure reverse proxy:
     - / → web:5173
     - /api → orchestrator:3001
     - /ws → collab:1234
  3. Enable site:
     ln -s /etc/nginx/sites-available/researchflow /etc/nginx/sites-enabled/
  4. Test config:
     nginx -t
  5. Reload Nginx:
     systemctl reload nginx
Output: Nginx configured as reverse proxy
```

#### Task 5A.7: Configure DNS
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Add A record: researchflow.domain.com → <VPS_IP>
  2. Add CNAME: www → researchflow.domain.com
  3. Verify propagation:
     dig researchflow.domain.com
  4. Test HTTPS access:
     curl -I https://researchflow.domain.com
Output: DNS configured and resolving
```

---

### Track 5B: Monitoring & Observability
**Agent:** GPT-4/Cursor via Claude Subagent
**Duration:** 1.5 hours

#### Task 5B.1: Set Up Prometheus
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Add Prometheus to docker-compose:
     prometheus:
       image: prom/prometheus
       ports: ["9090:9090"]
       volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
  2. Create prometheus.yml with scrape configs:
     - orchestrator:3001/metrics
     - worker:8000/metrics
  3. Start Prometheus:
     docker compose up -d prometheus
  4. Verify targets:
     curl http://localhost:9090/api/v1/targets
Output: Prometheus collecting metrics from all services
```

#### Task 5B.2: Configure Grafana
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Add Grafana to docker-compose:
     grafana:
       image: grafana/grafana
       ports: ["3000:3000"]
       environment:
         - GF_SECURITY_ADMIN_PASSWORD=<secure>
  2. Start Grafana:
     docker compose up -d grafana
  3. Add Prometheus data source
  4. Import dashboard templates:
     - Node Exporter Full
     - Docker containers
  5. Create ResearchFlow custom dashboard
Output: Grafana dashboards configured
```

#### Task 5B.3: Set Up Alerting
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Create alerting rules in Prometheus:
     - Service down for > 1 minute
     - Error rate > 1%
     - Response time > 2 seconds
     - Disk usage > 80%
  2. Configure Alertmanager:
     - Email notifications
     - Slack webhook (optional)
  3. Test alert firing:
     docker stop orchestrator
     (wait for alert)
     docker start orchestrator
Output: Alerting configured and tested
```

#### Task 5B.4: Configure Log Aggregation
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Add Loki to docker-compose:
     loki:
       image: grafana/loki
       ports: ["3100:3100"]
  2. Add Promtail for log collection
  3. Configure Docker logging driver
  4. Add Loki data source to Grafana
  5. Create log exploration dashboard
Output: Centralized logging with Loki
```

#### Task 5B.5: Test Rollback Procedures
```
Agent: Claude Subagent
Tool: Bash
Steps:
  1. Tag current deployment:
     docker tag researchflow/orchestrator:latest researchflow/orchestrator:v1.0.0
  2. Simulate failed deployment
  3. Execute rollback:
     docker compose down
     docker compose -f docker-compose.prod.yml up -d --pull never
  4. Verify services restored
  5. Document rollback time (target < 5 minutes)
Output: Rollback procedure tested and documented
```

---

## PHASE 6: KUBERNETES SCALING (FUTURE)

### Track 6A: K8s Infrastructure Setup
**Duration:** 4-6 hours

#### Task 6A.1: Create Base Kubernetes Manifests
```
Agent: GPT-4/Cursor via Claude Subagent
Tool: Desktop Commander
Files to create:
  infrastructure/kubernetes/base/
  ├── namespace.yaml
  ├── configmap.yaml
  ├── secrets.yaml (template)
  ├── orchestrator/
  │   ├── deployment.yaml
  │   ├── service.yaml
  │   └── hpa.yaml
  ├── worker/
  │   ├── deployment.yaml
  │   ├── service.yaml
  │   └── hpa.yaml
  └── web/
      ├── deployment.yaml
      ├── service.yaml
      └── hpa.yaml
Output: Base K8s manifests created
```

#### Task 6A.2: Configure Horizontal Pod Autoscaler
```
Agent: Claude Subagent
Tool: Desktop Commander
HPA Configuration:
  orchestrator:
    minReplicas: 2
    maxReplicas: 10
    metrics:
      - cpu: 70%
      - memory: 80%
  worker:
    minReplicas: 1
    maxReplicas: 20
    metrics:
      - cpu: 80%
      - custom: queue_depth > 100
  web:
    minReplicas: 2
    maxReplicas: 8
    metrics:
      - cpu: 70%
Output: HPA configured for all services
```

#### Task 6A.3: Configure Vertical Pod Autoscaler
```
Agent: Claude Subagent
Tool: Desktop Commander
VPA Configuration:
  - Install VPA controller
  - Create VPA resources for each deployment
  - Set updateMode: "Auto" or "Off" (recommendation only)
  - Configure resource policies
Output: VPA configured for resource right-sizing
```

---

## SYNC POINTS (After Each Phase)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL SYNC AGENTS                          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ GitHub Sync     │  │ Linear Sync     │  │ Notion Sync     │
│ Agent           │  │ Agent           │  │ Agent           │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ git add -A      │  │ Update ROS-XX   │  │ Update Mission  │
│ git commit -m   │  │ status → Done   │  │ Control page    │
│ "[Phase X]..."  │  │ Add completion  │  │ Update phase    │
│ git push origin │  │ comment         │  │ status          │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ Create          │
                    │ Checkpoint File │
                    │ CHECKPOINT-     │
                    │ PHASE-X.md      │
                    └─────────────────┘
```

---

*This document contains the complete detailed task breakdown for all phases.*
