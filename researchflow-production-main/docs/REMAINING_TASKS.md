# ResearchFlow - Remaining Tasks

**Date**: February 2, 2026  
**Status**: Phase 6 Infrastructure ~80% Complete

---

## ✅ Completed Tasks

| Task | Commit | Description |
|------|--------|-------------|
| Auth Token Fix | `d54da85` | Standardized token storage key to `access_token` |
| Login Wiring | `34561ec` | Wired login form submit to auth service |
| Documents API | `67e4ce0` | Implemented `/api/documents` endpoint using artifacts table |
| DOCX Generation | `b4c58b0` | Implemented DOCX export service with python-docx |
| Stage Workers 6-11 | `8460b8c` | Implemented ANALYSIS phase agents |
| E2E Test Specs | `69cb6ef` | Created comprehensive test specifications |
| API Documentation | `15daf17` | Added OpenAPI specs for documents API |
| Integration Audit | `ac26b79` | Full-stack wiring verification |

---

## ⏳ Remaining Tasks

### P2: Stage Worker Implementations (WRITING + PUBLISH Phases)

**WRITING Phase (Stages 12-15)**
- [ ] `stage12_outline_generation.py` - Generate document outline from research
- [ ] `stage13_draft_writing.py` - Write initial draft content
- [ ] `stage14_revision.py` - Revise and improve draft
- [ ] `stage15_final_polish.py` - Final editing and polish

**PUBLISH Phase (Stages 16-20)**
- [ ] `stage16_formatting.py` - Apply output formatting
- [ ] `stage17_citation_generation.py` - Generate citations in specified style
- [ ] `stage18_quality_review.py` - Final quality assurance check
- [ ] `stage19_export_prep.py` - Prepare files for export
- [ ] `stage20_publish.py` - Final publish/delivery

### E2E Testing Infrastructure

**Blocked By**: Complex pnpm workspace configuration

**Issues to Resolve**:
1. Create `pnpm-workspace.yaml` with proper package paths
2. Fix workspace package references in orchestrator
3. Resolve TypeScript/ESLint version peer dependency warnings
4. Configure Docker build to work with workspace structure

**Workaround**: E2E testing can be done manually or via CI/CD pipeline once workspace is configured.

### CI/CD Pipeline

- [ ] GitHub Actions workflow for automated testing
- [ ] Docker image build and push to registry
- [ ] Automated E2E tests on PR
- [ ] Deployment to staging environment

---

## Environment Setup Notes

### Dependencies Fixed
- Aligned TypeScript version to `5.6.3` across all packages
- Root package.json, orchestrator, web, and collab services updated

### Docker Requirements
- PostgreSQL 16 (alpine)
- Redis 7 (alpine)
- Node.js 20 (alpine) for orchestrator
- Python 3.11 for worker service

### Required Environment Variables
```bash
POSTGRES_USER=ros
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=ros
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
REDIS_URL=redis://redis:6379
NODE_ENV=development|production
PORT=3001
```

---

## Next Session Quick Start

1. Fix pnpm workspace configuration
2. Run `pnpm install` from root
3. Start services: `docker-compose -f docker-compose.minimal.yml up -d`
4. Continue with Stage Workers 12-20
5. Run E2E verification tests

---

## Reference Documents

- `docs/INTEGRATION_AUDIT.md` - Full integration audit results
- `docs/SESSION_HANDOFF.md` - Previous session handoff
- `docs/testing/E2E_TEST_SPEC.md` - E2E test specifications
- `docs/testing/E2E_TEST_RESULTS.md` - Test results template
- `docs/stages/STAGE_WORKER_SPECS.md` - Stage worker requirements
- `docs/api/DOCUMENTS_API.md` - API documentation
