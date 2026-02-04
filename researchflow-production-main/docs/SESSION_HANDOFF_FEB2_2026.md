# ResearchFlow Session Handoff - February 2, 2026

## CANONICAL REPOSITORY (USE THIS ONLY)
```
Path: /Users/lhglosser/researchflow-production
GitHub: https://github.com/ry86pkqf74-rgb/researchflow-production.git
Latest Commit: 8dec2c5
Branch: main
```

**IGNORE these outdated copies:**
- /Users/ros/Desktop/researchflow-production
- /Users/ros/Documents/ResearchFlow/researchflow-production
- /Users/ros/researchflow-old

## PROJECT CONTEXT
ResearchFlow is a 20-stage AI-powered research workflow platform with:
- **Frontend**: Next.js/React at `services/web/`
- **Backend**: Express orchestrator at `services/orchestrator/`
- **Worker**: Python/LangGraph at `services/worker/`
- **Packages**: `packages/core`, `phi-engine`, `ai-router`, `manuscript-engine`, `notion-integration`

### 20-Stage Workflow Architecture
| Phase | Stages | Status |
|-------|--------|--------|
| SETUP | 0-5 | ✅ Complete |
| ANALYSIS | 6-11 | ✅ Complete |
| WRITING | 12-15 | ✅ Complete |
| PUBLISH | 16-20 | ✅ Complete |

## COMPLETED WORK (This Session)
1. ✅ All 20 stage workers implemented (stages 6-20)
2. ✅ Auth token mismatch fixed (localStorage key alignment)
3. ✅ Login submit handler wired
4. ✅ Documents API endpoint (`/api/workflows/:id/documents`)
5. ✅ DOCX generation integration
6. ✅ LangChain/LangGraph versions pinned in `requirements.txt`
7. ✅ pnpm workspace configured (`pnpm-workspace.yaml`)
8. ✅ Docker workspace deps fixed (all 5 @researchflow/* packages)
9. ✅ Import verification script added
10. ✅ Repo location confusion resolved (REPO_INFO.md, CLAUDE.md updated)

## PENDING TASKS
1. **E2E Testing** - Docker environment ready, tests not yet run
2. **CI/CD Pipeline** - Future task
3. **Dependabot vulnerabilities** - 13 found (2 critical, 8 high, 3 moderate)

## INTEGRATED TOOLS (in repo)
```
tools/
├── Ollama-ResearchFlow/     # Ollama AI integration
├── Ollama-Setup-Script/     # Ollama setup automation
└── Docker-Compose-Prod/     # Production Docker configs
```

## KEY FILES
- `CLAUDE.md` - AI context (has canonical path at top)
- `REPO_INFO.md` - Repo pointer for sessions
- `docs/INTEGRATION_AUDIT.md` - Integration status
- `docs/REMAINING_TASKS.md` - Task checklist
- `pnpm-workspace.yaml` - Workspace config
- `services/worker/requirements.txt` - Pinned LangChain versions

## PACKAGE MANAGEMENT
```bash
# Use pnpm (NOT npm)
pnpm install

# Python deps
pip install -r services/worker/requirements.txt --break-system-packages
```

## DOCKER COMMANDS
```bash
cd /Users/lhglosser/researchflow-production
docker-compose up --build
```

## AI WIRING VERIFICATION (Feb 2026)
After `docker-compose up --build` (and optionally `docker-compose -f docker-compose.chromadb.yml up -d` for Chroma):

- **Orchestrator:** `GET http://localhost:3001/api/ai/stream/health` – JSON with `enabled`, `status`.
- **Orchestrator:** `POST http://localhost:3001/api/chat/...` – requires auth; use frontend or token.
- **Worker:** `GET http://localhost:8000/agents/` – list agents.
- **Worker:** `POST http://localhost:8000/agents/rag/index` – body `{ "collection": "ai_feedback_guidance", "documents": [{ "id": "test", "content": "test", "metadata": {} }] }`.
- **Worker:** `POST http://localhost:8000/agents/rag/search` – body `{ "collection": "ai_feedback_guidance", "query": "test", "top_k": 5 }`.
- **Feedback RAG rebuild (STEWARD):** `POST http://localhost:3001/api/ai/feedback/rag/rebuild?days=90` with auth.

## GIT WORKFLOW
```bash
# Always rebase before pushing (parallel work with Cursor/Composio)
git pull --rebase origin main && git push origin main
```

## ENVIRONMENT
- Node.js with pnpm
- Python 3.11+ with LangChain 0.3.7, LangGraph 0.2.60
- Docker Desktop
- PostgreSQL, Redis (via Docker)

## NEXT RECOMMENDED ACTIONS
1. Run E2E tests: `docker-compose up --build` then run test suite
2. Address Dependabot vulnerabilities
3. Complete CI/CD pipeline setup
