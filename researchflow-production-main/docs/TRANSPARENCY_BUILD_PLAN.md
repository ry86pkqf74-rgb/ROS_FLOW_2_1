# Transparency & Compliance Build Plan

## Executive Summary
Implementation of Phases 8-14 from ResearchFlow Transparency Execution Plan.
Covers: HTI-1, TRIPOD+AI, CONSORT-AI, FAVES, NIST AI RMF compliance.

**Start Date:** January 30, 2026
**Status:** IN PROGRESS

---

## Phase Checklist

### Phase 8: Evidence Bundle System
- [x] Database Schema (model_registry, evidence_bundles, performance_metrics)
- [ ] Worker: evidence_bundle.py generator
- [ ] Orchestrator: /api/models/:id/evidence-bundle routes
- [ ] Web: ModelTransparency.tsx page

### Phase 9: HTI-1 Source Attributes
- [x] Shared schema: source_attributes.ts
- [ ] Database Schema (predictive_dsi, source_attributes, source_attributes_audit)
- [ ] Orchestrator: /api/dsi/:id/source-attributes routes
- [ ] Web: SourceAttributesViewer.tsx component

### Phase 10: FAVES Compliance Gates
- [x] Shared schema: faves_result.ts
- [x] Worker: faves_evaluator.py
- [x] CI/CD: .github/workflows/faves-gate.yml
- [x] Web: FAVESDashboard.tsx
- [x] Orchestrator: /api/faves routes registered
- [x] Documentation: docs/faves/README.md
- [x] Tests: Python (test_faves_evaluator.py)
- [x] Tests: TypeScript (faves.test.ts)

### Phase 11: TRIPOD+AI / CONSORT-AI Checklists
- [ ] Schema: docs/reporting/schemas/checklist_item.schema.json
- [ ] TRIPOD+AI: docs/reporting/tripod_ai.yaml (27 items)
- [ ] CONSORT-AI: docs/reporting/consort_ai.yaml
- [ ] CI/CD: .github/workflows/checklist-validation.yml
- [ ] Web: ChecklistViewer.tsx

### Phase 12: Supply Chain Hardening
- [ ] CI/CD: .github/workflows/sbom.yml (syft)
- [ ] CI/CD: .github/workflows/container-signing.yml (cosign)
- [ ] Python: requirements.lock with pip-tools
- [ ] Node: pnpm-lock.yaml integrity

### Phase 13: Regulatory-Grade Audit Logging
- [x] Shared schema: audit_event_v2.ts
- [ ] Orchestrator: audit-enhanced.ts middleware
- [ ] Hash-chain implementation
- [ ] GET /api/audit/verify-chain endpoint

### Phase 14: Post-Deployment Monitoring
- [ ] Worker: drift_detector.py
- [ ] Worker: bias_monitor.py
- [ ] n8n: Safety event workflow
- [ ] Web: MonitoringDashboard.tsx

---

## File Inventory

### Shared Schemas (packages/shared/src/schemas/)
| File | Status | Purpose |
|------|--------|---------|
| evidence_bundle.ts | ✅ DONE | Evidence Bundle Zod schemas |
| source_attributes.ts | ✅ DONE | HTI-1 Source Attributes schemas |
| faves_result.ts | ✅ DONE | FAVES evaluation result schemas |
| audit_event_v2.ts | ⏳ TODO | Enhanced audit event schemas |

### Worker Python Modules (services/worker/src/)
| File | Status | Purpose |
|------|--------|---------|
| generators/evidence_bundle.py | ⏳ TODO | Bundle generation |
| generators/plain_language_renderer.py | ⏳ TODO | Plain language HTI-1 |
| evaluators/faves_evaluator.py | ✅ DONE | FAVES compliance |
| evaluators/test_faves_evaluator.py | ✅ DONE | FAVES unit tests |
| evaluators/fairness_metrics.py | ⏳ TODO | Fairness calculations |
| monitoring/drift_detector.py | ⏳ TODO | Input/output drift |
| monitoring/bias_monitor.py | ⏳ TODO | Bias drift |
| validation/checklist_validator.py | ⏳ TODO | TRIPOD/CONSORT |

### Orchestrator Routes (services/orchestrator/src/routes/)
| File | Status | Purpose |
|------|--------|---------|
| transparency.ts | ⏳ TODO | Evidence Bundle API |
| source-attributes.ts | ⏳ TODO | HTI-1 CRUD |
| faves.ts | ✅ DONE | FAVES endpoints |
| __tests__/faves.test.ts | ✅ DONE | FAVES API tests |
| checklists.ts | ⏳ TODO | Checklist API |
| monitoring.ts | ⏳ TODO | Drift/bias API |

### CI/CD Workflows (.github/workflows/)
| File | Status | Purpose |
|------|--------|---------|
| faves-gate.yml | ✅ DONE | FAVES CI gate |
| checklist-validation.yml | ⏳ TODO | TRIPOD/CONSORT validation |
| sbom.yml | ⏳ TODO | SBOM generation |
| container-signing.yml | ⏳ TODO | Cosign integration |

### Documentation (docs/)
| File | Status | Purpose |
|------|--------|---------|
| faves/README.md | ✅ DONE | FAVES overview |
| reporting/tripod_ai.yaml | ⏳ TODO | 27-item checklist |
| reporting/consort_ai.yaml | ⏳ TODO | AI trial checklist |
| reporting/schemas/checklist_item.schema.json | ⏳ TODO | Item schema |

---

## Tool Integration Plan

### Composio Agents (Already Built)
- **Literature Retrieval Agent** → Use for gathering compliance docs
- **Manuscript Writer Agent** → Use for generating checklist content
- **Collaboration Notifier Agent** → Post updates to Slack/Linear

### LangSmith Observability (Already Built)
- **Trace Workflow Runs** → Log transparency generation
- **Compliance Audit** → Track PHI in audit logs

### Continue.dev Integration
- Use for rapid code completion in TypeScript/Python
- Leverage for schema generation

### Cursor Integration
- Use for multi-file refactoring
- Agent mode for complex implementations

---

## Environment Variables (New)
```bash
TRANSPARENCY_ENABLED=true
FAVES_GATES_ENABLED=true
EVIDENCE_BUNDLE_AUTO_GENERATE=true
DRIFT_MONITORING_INTERVAL="0 */6 * * *"
AUDIT_HASH_CHAIN_ENABLED=true
```

---

## Linear Issues to Create
- [ ] ROS-XXX: Phase 8 - Evidence Bundle System
- [ ] ROS-XXX: Phase 9 - HTI-1 Source Attributes
- [ ] ROS-XXX: Phase 10 - FAVES Compliance Gates
- [ ] ROS-XXX: Phase 11 - TRIPOD+AI / CONSORT-AI
- [ ] ROS-XXX: Phase 12 - Supply Chain Hardening
- [ ] ROS-XXX: Phase 13 - Audit Logging Enhancement
- [ ] ROS-XXX: Phase 14 - Post-Deployment Monitoring

---

## Quick Reference Commands

```bash
# Build shared schemas
cd packages/shared && pnpm build

# Run Worker locally
cd services/worker && python -m pytest

# Run Orchestrator locally
cd services/orchestrator && pnpm dev

# Generate Prisma client
cd services/orchestrator && pnpm prisma generate

# Run FAVES evaluation
make faves-report

# Validate checklists
make checklist-validate
```

---

---

## Phase 10 Completion Summary

**Status:** ✅ COMPLETE
**Completed:** February 3, 2026

### Deliverables
1. **Backend API** (`services/orchestrator/src/routes/faves.ts`)
   - 9 REST endpoints for FAVES evaluations
   - Deployment gate checking
   - Override request capability
   - Statistics and history tracking

2. **Python Evaluator** (`services/worker/src/evaluators/faves_evaluator.py`)
   - Full 5-dimension evaluation (Fair, Appropriate, Valid, Effective, Safe)
   - Artifact validation
   - Metrics evaluation with thresholds
   - CI/CD gate enforcement

3. **Frontend Dashboard** (`services/web/src/components/transparency/FAVESDashboard.tsx`)
   - Visual dimension cards
   - Evaluation history table
   - Deployment gate status
   - Filtering capabilities

4. **CI/CD Workflow** (`.github/workflows/faves-gate.yml`)
   - Individual dimension jobs
   - Gate decision logic
   - PR commenting
   - Artifact uploads

5. **Documentation** (`docs/faves/README.md`)
   - Dimension explanations
   - API reference
   - Threshold documentation
   - Example usage

6. **Tests**
   - Python: 50+ test cases covering all evaluator functionality
   - TypeScript: 15+ API endpoint tests with mocks

### Integration Points
- Routes registered in orchestrator index.ts
- Database schema in migration 015_transparency_compliance.sql
- TypeScript schemas in packages/shared/src/schemas/faves_result.ts
- Event bus integration for monitoring

### API Endpoints
- `GET /api/faves/evaluations` - List evaluations
- `GET /api/faves/evaluations/:id` - Get evaluation details
- `POST /api/faves/evaluations` - Create evaluation
- `POST /api/faves/evaluations/:id/dimensions` - Submit dimension results
- `POST /api/faves/evaluations/:id/artifacts` - Add artifacts
- `GET /api/faves/gate/:modelId` - Check deployment gate
- `POST /api/faves/gate/:modelId/override` - Request override
- `GET /api/faves/stats` - Get statistics
- `GET /api/faves/models/:modelId/history` - Get evaluation history

---

**Last Updated:** February 3, 2026 18:30 UTC
