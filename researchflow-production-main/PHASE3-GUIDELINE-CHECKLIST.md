# Phase 3C: Guideline Engine Deployment Checklist

**Project:** ResearchFlow  
**Track:** 3C - Guideline Engine Analysis  
**Status:** Ready for Deployment  
**Generated:** 2026-01-29

---

## Executive Summary

The Guideline Engine is a comprehensive clinical scoring system and validation platform integrated into ResearchFlow. It provides:

- **System Cards**: Canonical abstractions for clinical scoring systems, staging, grading, and guidelines
- **Rule Specs**: Computable deterministic calculations (threshold, lookup tables, formulas)
- **Evidence Statements**: Anchored citations with evidence grading
- **Validation Blueprints**: AI-generated study plans for validating scoring systems
- **Calculator Results**: Audit trails for all score calculations

**Key Statistics:**
- 15 guideline-related files found
- 5 seed systems implemented (CHA2DS2-VASc, Child-Pugh, MELD, Wells DVT, CURB-65)
- 2 microservices integrated (Orchestrator, Worker)
- 2 Kubernetes manifests configured

---

## Database & Schema

### Migration File
- **Location**: `/Users/ros/researchflow-production/services/orchestrator/migrations/014_guidelines_engine.sql`
- **Status**: Ready to deploy
- **Tables Created**: 9 core tables

### Core Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `source_registry` | Track guideline sources and licensing | ✓ Implemented |
| `guideline_documents` | Source documents with URLs and metadata | ✓ Implemented |
| `system_cards` | Canonical abstraction for scoring systems | ✓ Implemented |
| `rule_specs` | Computable rule definitions | ✓ Implemented |
| `evidence_statements` | Evidence citations with grading | ✓ Implemented |
| `version_graph` | Track version relationships | ✓ Implemented |
| `validation_blueprints` | Generated study plans | ✓ Implemented |
| `calculator_results` | Audit trail for calculations | ✓ Implemented |

### Database Deployment Steps

- [ ] **Step 1**: Run migration `014_guidelines_engine.sql` against production database
  ```bash
  psql -U postgres -d researchflow < migrations/014_guidelines_engine.sql
  ```
- [ ] **Step 2**: Verify table creation and indexes
  ```bash
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' AND table_name LIKE '%guideline%';
  ```
- [ ] **Step 3**: Run optional migration `015_guideline_engine_v2.sql` for enhancements
- [ ] **Step 4**: Seed initial data using seed function
  ```bash
  npx ts-node services/orchestrator/src/seed/guidelines-seed.ts
  ```

---

## Kubernetes Deployment

### Deployment Manifests

#### 1. Guideline Engine Deployment
**File**: `/Users/ros/researchflow-production/infrastructure/kubernetes/base/guideline-engine-deployment.yaml`

**Configuration:**
- **Image**: `researchflow/guideline-engine:latest`
- **Replicas**: 2
- **Port**: 8001
- **CPU Request**: 250m | Limit: 1000m
- **Memory Request**: 256Mi | Limit: 1Gi
- **Health Checks**: ✓ Configured (liveness + readiness probes)

**Pre-Deployment Checklist:**
- [ ] Build and push Docker image: `researchflow/guideline-engine:latest`
- [ ] Verify image in registry
- [ ] Confirm resource limits are appropriate for your cluster
- [ ] Review environment variables from ConfigMap and Secrets

**Deployment Command:**
```bash
kubectl apply -f infrastructure/kubernetes/base/guideline-engine-deployment.yaml
kubectl apply -f infrastructure/kubernetes/base/guideline-engine-service.yaml
kubectl rollout status deployment/guideline-engine -n researchflow
```

#### 2. Guideline Engine Service
**File**: `/Users/ros/researchflow-production/infrastructure/kubernetes/base/guideline-engine-service.yaml`

**Configuration:**
- **Type**: ClusterIP
- **Port**: 8001
- **Selector**: `app.kubernetes.io/name=researchflow` and `app.kubernetes.io/component=guideline-engine`

**Post-Deployment Verification:**
- [ ] Service is accessible from orchestrator pod: `kubectl exec -it <orchestrator-pod> -- curl http://guideline-engine:8001/health`

---

## Microservice Integration

### 1. Orchestrator Service
**Location**: `/Users/ros/researchflow-production/services/orchestrator/`

**Components:**
- **Type Definitions**: `src/types/guidelines.ts` (378 lines)
- **Business Logic**: `src/services/guidelines.service.ts` (705 lines)
- **Data Layer**: `src/repositories/guidelines.repository.ts`
- **API Routes**: `src/routes/guidelines.routes.ts` (468 lines)
- **Seed Data**: `src/seed/guidelines-seed.ts` (703 lines)

**Key Features:**
- System card management (CRUD)
- Score calculation with validation
- Version comparison and diffing
- Validation blueprint generation
- Evidence statement management
- Guideline summarization

**API Endpoints:**
```
GET    /api/guidelines/search              - Search system cards
GET    /api/guidelines/:id                 - Get system card with details
GET    /api/guidelines/by-name/:name       - Get by name
GET    /api/guidelines/:id/versions        - Version history
GET    /api/guidelines/:id/evidence        - Evidence statements
GET    /api/guidelines/:id/rules           - Rule specifications
POST   /api/guidelines/calculate           - Calculate score
POST   /api/guidelines/compare             - Compare versions
POST   /api/guidelines/:id/summarize       - Generate summary
POST   /api/guidelines/ideate              - Generate validation blueprint
GET    /api/guidelines/blueprints/mine     - User's blueprints
PATCH  /api/guidelines/blueprints/:id      - Update blueprint
POST   /api/guidelines/blueprints/:id/export - Export to manuscript
```

**Pre-Deployment:**
- [ ] All type definitions are imported and compiled
- [ ] Database connection pool is configured
- [ ] Repository initialized with connection pool
- [ ] Routes registered with Express router
- [ ] Error handling middleware in place

### 2. Worker Service
**Location**: `/Users/ros/researchflow-production/services/worker/`

**Components:**
- **API Routes**: `src/api/guidelines.py` (295 lines)
- **Conference Prep Integration**: `src/conference_prep/guidelines.py`

**API Endpoints (FastAPI):**
```
GET  /guidelines/process                   - Process guideline query
GET  /guidelines/sources                   - List sources (with filters)
GET  /guidelines/fields                    - List medical fields
GET  /guidelines/categories                - List categories
GET  /guidelines/cache/health              - Cache health check
POST /guidelines/cache/invalidate          - Invalidate cache
GET  /guidelines/discover                  - Discover URL for query
```

**Features:**
- Guideline content fetching and parsing
- Structured extraction of sections, tables, lists, stages
- AI-powered suggestion generation
- Manuscript ideas
- Validation study recommendations
- Reporting checklist generation
- Redis/memory-based caching

**Pre-Deployment:**
- [ ] FastAPI router registered with main app
- [ ] Guideline-engine package available at: `packages/guideline-engine/`
- [ ] Cache backend configured (Redis or memory)
- [ ] Known guideline sources configured
- [ ] Test import: `from guideline_engine import process_query`

---

## Seed Data

### Included Clinical Systems

5 comprehensive systems pre-configured:

#### 1. CHA2DS2-VASc Score
- **Use**: Stroke risk in atrial fibrillation
- **Type**: Scoring system (0-9 points)
- **Inputs**: Age, sex, CHF, hypertension, stroke history, vascular disease, diabetes
- **Evidence**: 50+ validation studies
- **Test Cases**: 3 scenarios included

#### 2. Child-Pugh Score
- **Use**: Liver disease severity and surgical risk
- **Type**: Classification (Class A-C)
- **Inputs**: Bilirubin, albumin, INR, ascites, encephalopathy
- **Evidence**: 100+ validation studies
- **Test Cases**: 3 scenarios (well-compensated to decompensated)

#### 3. MELD Score
- **Use**: End-stage liver disease and transplant prioritization
- **Type**: Scoring system (6-40)
- **Inputs**: Bilirubin, INR, creatinine, dialysis status, sodium (MELD-Na)
- **Evidence**: 200+ validation studies
- **Formula-based**: Logarithmic calculation

#### 4. Wells Criteria for DVT
- **Use**: Deep vein thrombosis pre-test probability
- **Type**: Diagnostic criteria
- **Inputs**: 10 clinical factors (cancer, immobilization, swelling, tenderness, etc.)
- **Evidence**: 50+ validation studies
- **Dichotomized**: Low/high probability classifications

#### 5. CURB-65 Score
- **Use**: Community-acquired pneumonia severity
- **Type**: Scoring system (0-5)
- **Inputs**: Confusion, BUN, respiratory rate, SBP/DBP, age
- **Evidence**: 30+ validation studies
- **Clinical Action**: Mortality estimates and treatment recommendations

**Seeding Process:**
```bash
cd services/orchestrator
npx ts-node src/seed/guidelines-seed.ts
```

**Verification:**
- [ ] Query system cards: `SELECT COUNT(*) FROM system_cards;` → Should be ≥5
- [ ] Query rule specs: `SELECT COUNT(*) FROM rule_specs;` → Should be ≥5
- [ ] Query evidence: `SELECT COUNT(*) FROM evidence_statements;` → Should be ≥10

---

## Feature Validation

### Score Calculation
- [ ] **CHA2DS2-VASc**: Test with sample patient (75-year-old female with HTN, DM)
- [ ] **MELD**: Test with low (all normal labs) and high (elevated bilirubin/INR/creatinine) cases
- [ ] **Wells DVT**: Test low-probability and high-probability scenarios
- [ ] **CURB-65**: Test mortality risk stratification
- [ ] **Child-Pugh**: Verify class boundaries (A: 5-6, B: 7-9, C: 10-15)

### Version Management
- [ ] Create second version of a system card
- [ ] Test version comparison endpoint
- [ ] Verify diff calculation shows major/moderate/minor changes

### Validation Blueprint Generation
- [ ] Generate external validation blueprint
- [ ] Generate temporal validation blueprint
- [ ] Generate head-to-head comparison blueprint
- [ ] Verify data dictionary, analysis plan, validation metrics populated

### Evidence & Documentation
- [ ] Verify evidence statements are searchable and retrievable
- [ ] Test summarization endpoint for markdown generation
- [ ] Confirm citation references are properly formatted

### Caching & Performance
- [ ] Test cache health endpoint (for Worker service)
- [ ] Verify cache invalidation works properly
- [ ] Monitor query response times with and without cache

---

## Integration with Worker Service (Pipeline)

### Conference Prep Integration

The Worker service integrates guidelines with conference preparation:

**File**: `/Users/ros/researchflow-production/services/worker/src/conference_prep/guidelines.py`

**Workflow:**
1. User provides guideline query (e.g., "TNM colorectal")
2. Worker fetches and parses guideline content
3. Guideline Engine extracts structured data
4. AI generates manuscript ideas, validation studies, and reporting checklist
5. Results used for conference abstract generation

**Pre-Deployment:**
- [ ] Worker service has network access to guideline sources
- [ ] PDF/HTML parsing libraries installed (PyPDF2, BeautifulSoup4, etc.)
- [ ] Cache backend accessible from Worker
- [ ] Error handling for missing or inaccessible sources

---

## Configuration & Environment

### Required Environment Variables

**Orchestrator:**
- `DATABASE_URL`: PostgreSQL connection string
- `NODE_ENV`: `production`
- `LOG_LEVEL`: `info` or `debug`

**Worker:**
- `REDIS_URL`: Redis connection for cache (optional, defaults to memory)
- `GUIDELINES_CACHE_TTL`: Cache time-to-live in seconds (default: 3600)

**Kubernetes:**
- ConfigMap: `researchflow-config` (shared across all services)
- Secret: `researchflow-secrets` (database credentials, JWT secrets)

### Deployment Environment Validation

- [ ] Database connection verified
- [ ] Redis (if used) accessible and connected
- [ ] All required environment variables set
- [ ] Secrets properly mounted in Kubernetes
- [ ] Network policies allow service-to-service communication

---

## Testing & Validation

### Unit Tests
- [ ] `guidelines.service.ts`: Score calculation logic
- [ ] `guidelines.repository.ts`: Database queries
- [ ] Rule spec execution (threshold, lookup, formula)

**Run:**
```bash
npm test -- services/orchestrator/src/services/guidelines.service.ts
```

### E2E Tests
- [ ] `guideline-engine.spec.ts` - Full integration tests

**Run:**
```bash
npm run test:e2e tests/e2e/guideline-engine.spec.ts
```

### API Integration Tests
- [ ] Test all endpoints with curl or Postman
- [ ] Verify error handling (404, 400, 500)
- [ ] Test pagination and filtering
- [ ] Validate response formats

**Example:**
```bash
# Search system cards
curl -X GET "http://localhost:3000/api/guidelines/search?type=score&specialty=Cardiology"

# Calculate score
curl -X POST "http://localhost:3000/api/guidelines/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "systemCardId": "...",
    "inputs": {"age": 75, "sex": "female", ...}
  }'

# Generate blueprint
curl -X POST "http://localhost:3000/api/guidelines/ideate" \
  -H "Content-Type: application/json" \
  -d '{
    "systemCardId": "...",
    "studyIntent": "external_validation"
  }'
```

---

## Performance & Monitoring

### Expected Performance Metrics

| Operation | Expected Latency | Notes |
|-----------|------------------|-------|
| Search (no cache) | 200-500ms | Database query + pagination |
| Search (cached) | 10-50ms | Redis/memory lookup |
| Score calculation | 50-150ms | Rule execution |
| Version comparison | 100-300ms | Diff computation |
| Blueprint generation | 500-2000ms | AI processing, JSON building |

### Monitoring & Logging

- [ ] Enable structured logging in all services
- [ ] Log all calculator results for audit trail
- [ ] Monitor pod memory usage (target <1Gi)
- [ ] Monitor database query performance
- [ ] Alert on endpoint errors (5xx) or latency spikes (>5s)

### Health Checks

**Orchestrator:**
- Liveness: Endpoint responsive, no hangups
- Readiness: Database connection successful

**Worker:**
- Liveness: FastAPI server responding
- Readiness: Guideline engine module imports successfully, cache backend accessible

---

## Security Considerations

### Data Protection

- [ ] Evidence statements don't include full copyrighted text (only excerpts)
- [ ] Respect source registry `allow_show_excerpts` and `excerpt_max_length`
- [ ] Deep links required where `requireDeepLink=true`
- [ ] User IDs properly validated for blueprint ownership

### Access Control

- [ ] Public endpoints (search, get) - no auth required
- [ ] User-specific endpoints (blueprints/mine) - require auth
- [ ] Admin endpoints (/admin/*) - require admin role

### Compliance

- [ ] Source licensing tracked in `source_registry`
- [ ] User consent for data usage in calculations
- [ ] HIPAA-compliant logging (no PHI in logs unless necessary)

---

## Deployment Timeline

### Phase 1: Database & Seed (30 mins)
- [ ] Run migration SQL
- [ ] Verify tables and indexes
- [ ] Run seed script
- [ ] Validate 5 core systems present

### Phase 2: Kubernetes Rollout (15 mins)
- [ ] Deploy guideline-engine pods
- [ ] Deploy service
- [ ] Verify pod health and readiness
- [ ] Test inter-service networking

### Phase 3: Integration Testing (45 mins)
- [ ] Test all API endpoints
- [ ] Verify database connectivity
- [ ] Run E2E test suite
- [ ] Validate score calculations

### Phase 4: Load Testing & Monitoring (30 mins)
- [ ] Run load test (100+ concurrent requests)
- [ ] Monitor CPU/memory usage
- [ ] Verify cache effectiveness
- [ ] Set up alerts

**Total Estimated Time**: ~2 hours

---

## Rollback Plan

If deployment issues occur:

1. **Immediate Rollback** (K8s):
   ```bash
   kubectl rollout undo deployment/guideline-engine -n researchflow
   ```

2. **Database Rollback** (if issues with migration):
   ```bash
   # Save backup before migration
   pg_dump researchflow > backup_pre_guidelines.sql
   
   # Rollback if needed
   psql -d researchflow < backup_pre_guidelines.sql
   ```

3. **Verify Previous State**:
   ```bash
   kubectl get deployment guideline-engine -n researchflow
   psql -c "SELECT COUNT(*) FROM system_cards;" -d researchflow
   ```

---

## Post-Deployment Verification

### Smoke Tests (Run Immediately)

```bash
# 1. Check K8s deployment
kubectl get pods -n researchflow | grep guideline

# 2. Check database connectivity
psql -d researchflow -c "SELECT name, type, specialty FROM system_cards LIMIT 5;"

# 3. Test API endpoint
curl -s http://orchestrator:3000/api/guidelines/search?type=score | jq '.systems | length'

# 4. Test calculation
curl -X POST http://orchestrator:3000/api/guidelines/calculate \
  -H "Content-Type: application/json" \
  -d '{"systemCardId":"cha2ds2vasc","inputs":{"age":72,"sex":"female",...}}'
```

### Day 1 Verification

- [ ] All pods running and healthy (`kubectl get pods -n researchflow`)
- [ ] Logs show no errors in guideline-engine pod
- [ ] Database connections stable
- [ ] Cache hits increasing (if applicable)
- [ ] Search queries returning results
- [ ] Score calculations producing expected outputs

### Week 1 Monitoring

- [ ] No unexpected spikes in error rates
- [ ] Average response time stable
- [ ] Database query performance within SLAs
- [ ] All health checks passing
- [ ] Users successfully using guidelines for research

---

## Known Limitations & Future Enhancements

### Current Limitations

1. **Score Validation**: Test cases included but no automated validation runner
2. **Evidence Coverage**: Only 5 systems seeded; more can be added
3. **Licensing Compliance**: Manual enforcement of source registry rules
4. **Natural Language Processing**: Structured extraction only; no semantic analysis
5. **Complex Calculations**: Limited to threshold, lookup, formula; no decision trees yet

### Planned Enhancements

- [ ] Decision tree rule type implementation
- [ ] Bayesian network support for complex predictions
- [ ] Natural language extraction from PDFs
- [ ] Automated version tracking from source updates
- [ ] User-contributed guidelines and crowdsourced validation
- [ ] Integration with EHR systems for real-time calculations
- [ ] Mobile-friendly calculator UI

---

## Support & Escalation

### Troubleshooting

**Pod not starting?**
- Check logs: `kubectl logs -f deployment/guideline-engine -n researchflow`
- Verify image exists: `docker images | grep guideline-engine`
- Check resources: `kubectl top pods -n researchflow`

**Database connection errors?**
- Verify `DATABASE_URL` in ConfigMap
- Test connection: `psql $DATABASE_URL -c "SELECT 1"`
- Check firewall/network policies

**API returning 503 (unavailable)?**
- Check pod readiness: `kubectl get pods -n researchflow`
- Verify database is accessible from pod
- Check logs for import errors

### Escalation Matrix

| Issue | Owner | Response Time |
|-------|-------|----------------|
| Pod crash/not starting | DevOps/SRE | 15 min |
| Database error | DBA | 30 min |
| API errors (5xx) | Backend Team | 30 min |
| Slow queries | DBA | 1 hour |
| Data integrity | DBA/Backend | 2 hours |

---

## Sign-Off

- [ ] Database team: Migration approved and tested
- [ ] DevOps: Kubernetes manifests reviewed
- [ ] Backend team: Code reviewed and tested
- [ ] QA: E2E tests passing
- [ ] Security: HIPAA compliance verified
- [ ] Product: Feature requirements met

---

**Checklist Complete?** → Ready for Production Deployment ✓

Last Updated: 2026-01-29
Next Review: Post-deployment (2026-02-05)
