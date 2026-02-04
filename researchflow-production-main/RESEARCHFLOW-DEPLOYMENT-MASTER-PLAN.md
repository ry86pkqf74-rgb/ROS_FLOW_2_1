# ResearchFlow Deployment Master Plan

**Date:** January 29, 2026
**Status:** Ready for Execution
**Repository:** github.com/ry86pkqf74-rgb/researchflow-production

---

## EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Production Readiness | 94-100% |
| Estimated Deploy Time | 7-13 hours |
| P0 Blockers | 1 (ROS-51 Security) |
| Total Phases | 6 |
| Parallel Tracks per Phase | 2-3 |

---

## AI TOOLS & AGENTS INVENTORY

| Agent/Tool | Specialty | Access Method |
|------------|-----------|---------------|
| **Claude Coworker** | Orchestration, Multi-step reasoning | Direct (Primary) |
| **Claude Subagents** | Parallel task execution | Task tool |
| **GPT-4/Cursor** | Code generation, TypeScript | Cursor IDE |
| **Grok** | Security auditing | API |
| **Mercury/v0** | UI component generation | API |
| **LM Studio** | PHI-safe local processing | Local API |
| **Context7 MCP** | Library documentation | MCP |
| **Linear MCP** | Issue tracking | MCP |
| **Notion MCP** | Documentation sync | MCP |
| **GitHub (gh CLI)** | Repository operations | Bash |
| **Desktop Commander** | File/process management | MCP |
| **Chrome MCP** | Browser automation | MCP |
| **n8n** | Workflow automation | Webhook/MCP |

---

## PHASE 1: CRITICAL BLOCKERS RESOLUTION
**Duration:** 2-3 hours | **Parallel Tracks:** 2

### Track 1A: Security Resolution (ROS-51)
| Task | AI Agent | Tool |
|------|----------|------|
| Analyze GitGuardian alert | **Grok** (via Claude subagent) | Linear MCP |
| Search for exposed secrets | **Claude Subagent** | Desktop Commander search |
| Generate new credentials | **Claude Subagent** | Bash (openssl) |
| Update .env files | **Claude Subagent** | Desktop Commander edit |
| Clean git history | **Claude Subagent** | Bash (BFG/git-filter-repo) |
| Verify old creds invalidated | **Claude Subagent** | Bash |

### Track 1B: TypeScript Verification (ROS-59)
| Task | AI Agent | Tool |
|------|----------|------|
| Verify @types packages | **GPT-4/Cursor** (via Claude subagent) | Bash (npm ls) |
| Run type check | **Claude Subagent** | Bash (npx tsc) |
| Verify build succeeds | **Claude Subagent** | Bash (npm run build) |
| Run unit tests | **Claude Subagent** | Bash (npm test) |

**Sync Point:** Update Linear, Notion, create checkpoint

---

## PHASE 2: BACKEND SERVICES DEPLOYMENT
**Duration:** 3-4 hours | **Parallel Tracks:** 3

### Track 2A: Database & Cache Layer
| Task | AI Agent | Tool |
|------|----------|------|
| Validate environment vars | **Claude** (Primary) | Desktop Commander read |
| Start PostgreSQL container | **Claude Subagent** | Bash (docker compose) |
| Run database migrations | **Claude Subagent** | Bash |
| Start Redis container | **Claude Subagent** | Bash (docker compose) |
| Verify connectivity | **Claude Subagent** | Bash (pg_isready, redis-cli) |

### Track 2B: Node.js Orchestrator
| Task | AI Agent | Tool |
|------|----------|------|
| Build orchestrator image | **GPT-4/Cursor** (via Claude subagent) | Bash (docker build) |
| Start orchestrator service | **Claude Subagent** | Bash (docker compose) |
| Verify health endpoint | **Claude Subagent** | Bash (curl) |
| Test authentication | **Claude Subagent** | Bash (curl) |
| Verify AI Router | **Claude Subagent** | Bash |

### Track 2C: Python Worker
| Task | AI Agent | Tool |
|------|----------|------|
| Build worker image | **Claude Subagent** | Bash (docker build) |
| Start worker service | **Claude Subagent** | Bash (docker compose) |
| Verify health endpoint | **Claude Subagent** | Bash (curl) |
| Test agent registration | **Claude Subagent** | Bash |
| Verify 20-stage workflow | **Claude Subagent** | Bash |

**Sync Point:** Update Linear, Notion, create checkpoint

---

## PHASE 3: FRONTEND & INTEGRATION SERVICES
**Duration:** 2-3 hours | **Parallel Tracks:** 3

### Track 3A: React Web Application
| Task | AI Agent | Tool |
|------|----------|------|
| Build web image | **Mercury/v0** (via Claude subagent) | Bash (docker build) |
| Start web service | **Claude Subagent** | Bash (docker compose) |
| Verify static files | **Claude Subagent** | Chrome MCP |
| Test API connectivity | **Claude Subagent** | Chrome MCP |
| Verify auth flow | **Claude Subagent** | Chrome MCP |

### Track 3B: Collaboration Service
| Task | AI Agent | Tool |
|------|----------|------|
| Build collab image | **Claude Subagent** | Bash (docker build) |
| Start collab service | **Claude Subagent** | Bash (docker compose) |
| Test WebSocket | **Claude Subagent** | Bash |
| Verify Yjs sync | **Claude Subagent** | Bash |

### Track 3C: Guideline Engine
| Task | AI Agent | Tool |
|------|----------|------|
| Build guideline-engine | **GPT-4/Cursor** (via Claude subagent) | Bash (docker build) |
| Start service | **Claude Subagent** | Bash (docker compose) |
| Verify clinical API | **Claude Subagent** | Bash (curl) |
| Test worker integration | **Claude Subagent** | Bash |

**Sync Point:** Update Linear, Notion, create checkpoint

---

## PHASE 4: INTEGRATION TESTING & HIPAA COMPLIANCE
**Duration:** 2-3 hours | **Parallel Tracks:** 2

### Track 4A: End-to-End Testing
| Task | AI Agent | Tool |
|------|----------|------|
| Run Playwright E2E tests | **Claude** (Primary) | Bash (npx playwright) |
| Test 20-stage workflow | **Claude Subagent** | Chrome MCP |
| Verify multi-agent hub | **Claude Subagent** | Bash |
| Test Claude orchestrator | **Claude Subagent** | Bash |
| Document test results | **Claude Subagent** | Desktop Commander write |

### Track 4B: HIPAA Compliance Verification
| Task | AI Agent | Tool |
|------|----------|------|
| Verify PHI detection | **Grok** (via Claude subagent) | Desktop Commander search |
| Confirm audit logging | **Claude Subagent** | Bash (docker logs) |
| Test LLM egress policy | **LM Studio** (via Claude subagent) | Bash |
| Document data flow | **Claude Subagent** | Desktop Commander write |
| Create compliance checklist | **Claude Subagent** | Notion MCP |

**Sync Point:** Update Linear, Notion, create checkpoint

---

## PHASE 5: PRODUCTION GO-LIVE & MONITORING
**Duration:** 2-3 hours | **Parallel Tracks:** 2

### Track 5A: VPS Deployment
| Task | AI Agent | Tool |
|------|----------|------|
| Provision Hetzner CX52 | **Claude** (Primary) | Bash (SSH) |
| Configure firewall | **Claude Subagent** | Bash (ufw) |
| Install Docker | **Claude Subagent** | Bash |
| Deploy production stack | **Claude Subagent** | Bash (docker compose) |
| Configure SSL/TLS | **Claude Subagent** | Bash (certbot) |
| Set up Nginx | **Claude Subagent** | Desktop Commander |
| Configure DNS | **Claude Subagent** | Bash |

### Track 5B: Monitoring & Observability
| Task | AI Agent | Tool |
|------|----------|------|
| Set up Prometheus | **GPT-4/Cursor** (via Claude subagent) | Bash |
| Configure Grafana | **Claude Subagent** | Bash |
| Set up alerting | **Claude Subagent** | Bash |
| Configure log aggregation | **Claude Subagent** | Bash |
| Test rollback procedures | **Claude Subagent** | Bash |

**Sync Point:** Update Linear, Notion, create checkpoint

---

## PHASE 6: KUBERNETES SCALING (FUTURE)
**Duration:** 9-15 hours | **Parallel Tracks:** 2-3

### Track 6A: K8s Infrastructure
| Task | AI Agent | Tool |
|------|----------|------|
| Create base manifests | **GPT-4/Cursor** (via Claude subagent) | Desktop Commander |
| Configure HPA | **Claude Subagent** | Desktop Commander |
| Configure VPA | **Claude Subagent** | Desktop Commander |
| Set up Cluster Autoscaler | **Claude Subagent** | Bash (kubectl) |

### Track 6B: Migration & Testing
| Task | AI Agent | Tool |
|------|----------|------|
| Migrate from Docker Compose | **Claude Subagent** | Bash (kubectl) |
| Test autoscaling | **Claude Subagent** | Bash |
| Load testing | **Claude Subagent** | Bash (k6/artillery) |
| Document K8s ops | **Claude Subagent** | Notion MCP |

---

## CROSS-PHASE SYNC STRATEGY

After EVERY phase completion:

| Platform | Agent | Action |
|----------|-------|--------|
| GitHub | **Claude Subagent** | `git add -A && git commit && git push` |
| Linear | **Claude Subagent** | Update issues via Linear MCP |
| Notion | **Claude Subagent** | Update Mission Control via Notion MCP |
| Checkpoint | **Claude** (Primary) | Create checkpoint markdown file |

---

## PARALLEL EXECUTION ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│              CLAUDE COWORKER (Primary Orchestrator)              │
│         Task Distribution · Progress Tracking · Sync            │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Track A      │       │  Track B      │       │  Track C      │
│  Subagent     │       │  Subagent     │       │  Subagent     │
│  (Task tool)  │       │  (Task tool)  │       │  (Task tool)  │
└───────────────┘       └───────────────┘       └───────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Specialized   │       │ Specialized   │       │ Specialized   │
│ Agent:        │       │ Agent:        │       │ Agent:        │
│ GPT-4/Grok/   │       │ Mercury/      │       │ LM Studio/    │
│ Context7      │       │ Chrome MCP    │       │ Desktop Cmd   │
└───────────────┘       └───────────────┘       └───────────────┘
```

---

## CURRENT STATUS

| Phase | Status | Blocking Issue |
|-------|--------|----------------|
| Phase 1 | ⚠️ PARTIAL | ROS-51 still blocking |
| Phase 2 | ⏳ PENDING | Awaits ROS-51 resolution |
| Phase 3 | ⏳ PENDING | Awaits Phase 2 |
| Phase 4 | ⏳ PENDING | Awaits Phase 3 |
| Phase 5 | ⏳ PENDING | Awaits Phase 4 |
| Phase 6 | 📅 FUTURE | Post-production |

---

## QUICK REFERENCE - AI AGENT SPECIALIZATIONS

| Agent | Best For | When to Use |
|-------|----------|-------------|
| **Claude Coworker** | Orchestration, reasoning | Complex multi-step tasks |
| **Claude Subagents** | Parallel execution | Independent concurrent tasks |
| **GPT-4/Cursor** | Code generation | TypeScript, complex algorithms |
| **Grok** | Security analysis | Vulnerability scans, audits |
| **Mercury/v0** | UI generation | React components, styling |
| **LM Studio** | PHI-safe processing | HIPAA-compliant AI tasks |
| **Context7** | Documentation | Library/API reference |

---

## DOCUMENTS CREATED

1. `RESEARCHFLOW-DEPLOYMENT-MASTER-PLAN.md` - This file
2. `CHECKPOINT-PHASE1.md` - Phase 1 status (to be created)

---

*This plan enables parallel execution across multiple AI agents while maintaining sync points for coordination.*
