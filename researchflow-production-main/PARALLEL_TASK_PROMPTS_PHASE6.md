# Phase 6: Parallel Task Prompts - Production Deployment & Final Integration

## Overview
Phase 6 focuses on production deployment, monitoring dashboards, project tracking, and final polish.

---

## 🖥️ CURSOR: Docker & Kubernetes Configuration

### Task: Production Infrastructure Setup

```markdown
## Context
ResearchFlow needs production-ready container orchestration. We have:
- 20 Python stage agents in services/worker/src/stages/
- TypeScript bridge services in services/orchestrator/src/services/
- FastAPI backend with health, metrics, and workflow endpoints
- React dashboard ready for deployment

## Requirements

### 1. Docker Optimization
Update Dockerfile with:
- Multi-stage builds for smaller images
- Layer caching optimization
- Non-root user configuration
- Health check instructions

### 2. Docker Compose Production
Create docker-compose.prod.yml:
- Service definitions for worker, orchestrator, dashboard
- Redis for caching/queuing
- Prometheus + Grafana stack
- Network configuration
- Volume mounts for persistent data

### 3. Kubernetes Manifests
Create k8s/ directory with:
- Deployment manifests for each service
- Service definitions with proper selectors
- ConfigMaps for environment configuration
- Secrets management templates
- HorizontalPodAutoscaler configs
- Ingress configuration

### 4. Helm Chart (Optional)
Create helm/researchflow/:
- Chart.yaml with metadata
- values.yaml with defaults
- Templates for all resources
- README with installation instructions

### 5. Log Aggregation Setup
Add logging configuration:
- Fluentd/Fluent Bit sidecar config
- Log format standardization
- Elasticsearch integration (optional)
```

---

## 🔗 COMPOSIO: Grafana Dashboard & Alerts

### Task: Complete Monitoring Stack

```markdown
## Context
ResearchFlow has Prometheus metrics exposed. Build complete observability.

## Requirements

### 1. Grafana Dashboard JSON
Create monitoring/grafana-dashboard.json with panels:
- Workflow Overview (total, active, completed, failed)
- Stage Execution Heatmap (all 20 stages)
- Error Rate by Stage (counter visualization)
- Average Stage Duration (histogram)
- Queue Depth Over Time
- Resource Utilization (CPU, Memory)
- Request Rate & Latency (p50, p95, p99)

### 2. Alert Rules
Create monitoring/alert-rules.yml:
```yaml
groups:
  - name: researchflow
    rules:
      - alert: HighErrorRate
        expr: rate(stage_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
      - alert: SlowStageExecution
        expr: histogram_quantile(0.95, stage_duration_seconds_bucket) > 30
        for: 5m
        labels:
          severity: warning
      - alert: QueueBacklog
        expr: workflow_queue_depth > 100
        for: 10m
        labels:
          severity: warning
      - alert: ServiceUnhealthy
        expr: up{job="researchflow"} == 0
        for: 1m
        labels:
          severity: critical
```

### 3. Prometheus Configuration
Create monitoring/prometheus.yml:
- Scrape configs for all services
- Service discovery for Kubernetes
- Retention and storage settings

### 4. Alertmanager Configuration
Create monitoring/alertmanager.yml:
- Slack webhook integration
- Email notifications
- PagerDuty integration template
- Routing rules by severity
```

---

## 🎨 FIGMA: Handoff Documentation & Component Library

### Task: Design System Handoff

Create documentation diagrams for:

1. **Component Library Export**
   - All reusable components cataloged
   - Props documentation for each
   - Usage examples
   - Spacing and sizing specs

2. **Design Tokens**
   - Color tokens (light/dark)
   - Typography scale
   - Spacing scale
   - Border radius values
   - Shadow definitions

3. **Handoff Checklist**
   - Assets exported (SVG, PNG)
   - Responsive behavior documented
   - Interaction states defined
   - Accessibility notes included

4. **Developer Implementation Guide**
   - CSS variable mappings
   - Component hierarchy
   - State management patterns
   - Animation specifications

---

## 🚀 REPLIT: Production Publish & Dark Mode

### Task: Final Production Deployment

```markdown
## Context
ResearchFlow dashboard is ready. Complete production deployment.

## Requirements

### 1. Production Publish
- Configure production environment variables
- Set up custom domain (if available)
- Enable HTTPS
- Configure CORS for production API

### 2. Dark Mode Implementation
Add dark mode toggle:
- CSS custom properties for theming
- localStorage persistence
- System preference detection
- Smooth transition between modes

### 3. Accessibility Fixes
Implement from Figma audit:
- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader announcements
- Color contrast fixes

### 4. Performance Verification
Run Lighthouse audit:
- Target 90+ Performance score
- Target 100 Accessibility score
- Target 90+ Best Practices
- Target 90+ SEO

### 5. Error Boundary
Add React error boundaries:
- Graceful error display
- Error reporting to backend
- Recovery options
```

---

## 📋 LINEAR: Sprint Planning & Issue Tracking

### Task: Set Up Project Management

Create in Linear:

1. **Project: ResearchFlow Production**
   - Status: Active
   - Target: Q1 2026

2. **Epics:**
   - [EPIC] Infrastructure & Deployment
   - [EPIC] Monitoring & Observability
   - [EPIC] UI/UX Polish
   - [EPIC] Testing & QA
   - [EPIC] Documentation

3. **Issues for Current Sprint:**
   - [ ] Docker multi-stage build optimization
   - [ ] Kubernetes deployment manifests
   - [ ] Grafana dashboard implementation
   - [ ] Dark mode toggle
   - [ ] Accessibility audit fixes
   - [ ] Load testing setup
   - [ ] Security audit

4. **Labels:**
   - priority: critical, high, medium, low
   - type: feature, bug, chore, docs
   - platform: cursor, composio, replit, figma

---

## 📝 NOTION: Knowledge Base & Documentation Hub

### Task: Complete Documentation Workspace

Create in Notion:

1. **Architecture Decision Records (ADRs)**
   - ADR-001: 20-Stage Agent Pattern
   - ADR-002: TypeScript Bridge Services
   - ADR-003: WebSocket Real-time Updates
   - ADR-004: Circuit Breaker Pattern

2. **Runbooks**
   - Deployment Runbook
   - Incident Response Runbook
   - Scaling Runbook
   - Rollback Procedures

3. **Meeting Notes Template**
   - Sprint Planning
   - Retrospectives
   - Technical Design Reviews

4. **Decision Log**
   - Technology choices
   - Architecture decisions
   - Trade-off analyses

---

## Execution Order

All tasks can run in parallel:
- **Cursor**: Docker + Kubernetes (infrastructure)
- **Composio**: Grafana + Alerts (monitoring)
- **Replit**: Publish + Dark Mode (frontend)
- **Figma**: Handoff docs (design)
- **Linear**: Sprint setup (tracking)
- **Notion**: Knowledge base (documentation)

## Success Criteria
- [ ] Cursor: k8s/ directory with deployment manifests
- [ ] Composio: monitoring/ directory with Grafana JSON
- [ ] Replit: Dashboard published with dark mode
- [ ] Figma: Component library documented
- [ ] Linear: Sprint board with prioritized issues
- [ ] Notion: ADRs and runbooks created

## Git Sync After Completion
```bash
git add -A
git commit -m "feat: Phase 6 - production infrastructure and monitoring"
git push origin main
```
