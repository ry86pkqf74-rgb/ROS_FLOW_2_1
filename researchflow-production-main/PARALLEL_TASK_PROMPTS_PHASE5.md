# Phase 5: Parallel Task Prompts - Final Integration & Polish

## Overview
Phase 5 focuses on final integration testing, documentation, monitoring dashboards, and production polish.

---

## 🖥️ CURSOR: Documentation & API Docs

### Task: Generate Comprehensive Documentation

```markdown
## Context
ResearchFlow is a 20-stage research workflow automation platform. We have:
- 20 Python stage agents in services/worker/src/stages/
- TypeScript bridge services in services/orchestrator/src/services/
- FastAPI backend with health, metrics, and workflow endpoints
- React dashboard with real-time updates

## Requirements

### 1. API Documentation (OpenAPI/Swagger)
Generate comprehensive API docs:
- Add FastAPI automatic docs at /docs and /redoc
- Document all endpoints with examples
- Add request/response schemas

### 2. README Enhancement
Update README.md with:
- Project overview and architecture diagram
- Quick start guide
- Environment setup instructions
- API reference links
- Deployment guide

### 3. Stage Agent Documentation
Create docs/STAGES.md with:
- Description of all 20 stages
- Input/output specifications for each
- Configuration options
- Error handling patterns

### 4. Developer Guide
Create docs/DEVELOPER.md with:
- How to add new stages
- Testing guidelines
- Code style guide
- PR workflow

### 5. Inline Code Documentation
Add docstrings to:
- All stage agent classes
- Bridge service methods
- API endpoints
```

---

## 🔗 COMPOSIO: Monitoring Dashboard Integration

### Task: Add Observability Stack

```markdown
## Context
ResearchFlow needs production monitoring. Build on the health system from Phase 4.

## Requirements

### 1. Prometheus Metrics Endpoint
Enhance /metrics endpoint:
- Stage execution duration histogram
- Active workflow count gauge
- Error rate by stage counter
- Queue depth metrics

### 2. Grafana Dashboard Config
Create monitoring/grafana-dashboard.json:
- Workflow execution overview
- Stage performance heatmap
- Error rate trends
- Resource utilization

### 3. Alert Rules
Create monitoring/alert-rules.yml:
- High error rate alerts
- Slow stage execution alerts
- Queue backlog alerts
- Health check failure alerts

### 4. Logging Enhancement
Add structured logging:
- Correlation IDs across services
- Log aggregation configuration
- Error tracking integration
```

---

## 🎨 FIGMA: Final UI Polish & Accessibility

### Task: Accessibility Review & Dark Mode

Create diagrams for:

1. **Accessibility Audit Checklist**
   - WCAG 2.1 compliance items
   - Keyboard navigation flows
   - Screen reader compatibility
   - Color contrast requirements

2. **Dark Mode Design System**
   - Dark theme color palette
   - Component appearance in dark mode
   - Toggle mechanism UI
   - System preference detection

3. **Responsive Breakpoints**
   - Mobile (320px-767px)
   - Tablet (768px-1023px)
   - Desktop (1024px+)
   - Component behavior at each

4. **Micro-interactions**
   - Button hover/active states
   - Loading animations
   - Success/error feedback
   - Transition timings

---

## 🚀 REPLIT: Performance Optimization & Caching

### Task: Optimize Dashboard Performance

```markdown
## Context
Optimize the ResearchFlow dashboard for production performance.

## Requirements

### 1. Code Splitting
- Lazy load stage detail views
- Split dashboard routes
- Dynamic imports for heavy components

### 2. Caching Strategy
- Implement SWR/React Query caching
- Cache stage configurations
- Invalidation on updates

### 3. Bundle Optimization
- Analyze bundle size
- Tree shake unused code
- Optimize images and assets

### 4. Performance Metrics
- Add Core Web Vitals tracking
- First Contentful Paint optimization
- Time to Interactive improvement

### 5. PWA Features
- Add service worker
- Offline capability for dashboard
- Install prompt
```

---

## Execution Order
All tasks can run in parallel. Each platform works independently.

## Success Criteria
- [ ] Cursor: Full API documentation at /docs
- [ ] Composio: Grafana dashboard JSON created
- [ ] Figma: Accessibility and dark mode diagrams
- [ ] Replit: Bundle size reduced by 20%+

## Git Sync After Completion
```bash
git add -A
git commit -m "feat: Phase 5 - documentation, monitoring, and optimization"
git push origin main
```
