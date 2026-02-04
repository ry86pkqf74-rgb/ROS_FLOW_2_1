# 🎯 ResearchFlow Next Phase Execution Plan
## Phases 8-14 Completion + LangChain Integration

**Generated:** January 30, 2026
**Status:** Ready for Parallel Execution
**Estimated Completion:** 2-3 hours with parallel agents

---

## 📊 Current State Analysis

### ✅ Completed Phases
| Phase | Description | Status | Issues |
|-------|-------------|--------|--------|
| Phase 2 | Infrastructure (ChromaDB, Ollama) | ✅ Done | ROS-81, ROS-95, ROS-99 |
| Phase 3 | Custom LangGraph Agents | ✅ Done | ROS-67 |
| Phase 4 | Fine-Tuning Pipeline | ✅ Done | ROS-82, ROS-100 |
| Phase 5 | AI Router CUSTOM Tier | ✅ Done | ROS-83, ROS-96 |
| Phase 6 | K8s Scaling (VPA, HPA) | ✅ Done | ROS-97, ROS-102 |
| Phase 7 | Frontend Components | ✅ Done | ROS-85 |
| Phase 8-14 | Transparency Build | ✅ Done | Commit 34ffbdd |

### 🔄 In Progress
| Issue | Title | Blocker |
|-------|-------|---------|
| ROS-75 | n8n Monitoring Notion Dashboard | Needs workflow creation |
| ROS-90 | Figma Dev Mode + Code Connect | Needs Figma file mapping |

### 📋 Backlog (Priority Order)
| Issue | Title | Phase | Priority | Agent |
|-------|-------|-------|----------|-------|
| ROS-107 | LangChain Node.js Orchestrator | LC-5 | High | Explore Agent |
| ROS-108 | Docker & Deployment Updates | LC-6 | High | Bash Agent |
| ROS-109 | Evidence Bundle System | 8 | Medium | General Agent |
| ROS-110 | HTI-1 Source Attributes | 9 | Medium | General Agent |
| ROS-111 | FAVES Compliance Gates | 10 | Medium | General Agent |
| ROS-112 | TRIPOD+AI Checklists | 11 | Medium | General Agent |
| ROS-113 | Supply Chain Hardening | 12 | Medium | Bash Agent |
| ROS-114 | Regulatory Audit Logging | 13 | Low | General Agent |
| ROS-115 | Post-Deployment Monitoring | 14 | Low | General Agent |
| ROS-116 | Drift Monitoring Dashboard | -- | Low | General Agent |

---

## 🚀 Parallel Execution Strategy

### Track A: LangChain Integration (ROS-107, ROS-108)
**Agent:** Explore + Bash
**Duration:** 30 min

1. Create `services/orchestrator/src/langchain-bridge.ts`
2. Update `services/worker/Dockerfile` with Python dependencies
3. Update `docker-compose.yml` with environment variables
4. Test integration endpoints

### Track B: Evidence & Compliance (ROS-109, ROS-110, ROS-111)
**Agent:** General Purpose
**Duration:** 45 min

1. Implement evidence bundle generator enhancements
2. Add HTI-1 source attribute tracking
3. Create FAVES gate CI workflow triggers

### Track C: Documentation & Checklists (ROS-112)
**Agent:** General Purpose
**Duration:** 30 min

1. Complete TRIPOD+AI checklist validation
2. Add CONSORT-AI items
3. Create checklist API endpoints

### Track D: Security & Supply Chain (ROS-113)
**Agent:** Bash
**Duration:** 20 min

1. Configure SBOM generation workflow
2. Add Grype vulnerability scanning
3. Create dependency audit script

### Track E: Monitoring & Audit (ROS-114, ROS-115)
**Agent:** General Purpose
**Duration:** 30 min

1. Implement hash chain audit logging
2. Add drift detection scheduling
3. Create safety event tracking

---

## 📁 Files to Create/Update

### Track A Files
```
services/orchestrator/src/langchain-bridge.ts    # NEW
services/worker/requirements.txt                  # UPDATE
docker-compose.yml                                # UPDATE
```

### Track B Files
```
services/worker/src/export/evidence_bundle_v2.py # UPDATE
services/orchestrator/src/routes/source-attributes.ts # UPDATE
.github/workflows/faves-gate.yml                 # UPDATE
```

### Track C Files
```
config/tripod-ai-checklist.yaml                  # UPDATE
config/consort-ai-checklist.yaml                 # NEW
services/orchestrator/src/routes/checklists.ts   # NEW
```

### Track D Files
```
.github/workflows/sbom-generation.yml            # UPDATE
scripts/security-audit.sh                        # NEW
```

### Track E Files
```
services/worker/src/audit/hash_chain.py          # NEW
services/worker/src/monitoring/drift_scheduler.py # NEW
```

---

## 🔧 Tool & Agent Assignments

| Task | Tool/Agent | MCP Server | Command |
|------|------------|------------|---------|
| Code exploration | Explore Agent | - | Task tool |
| File creation | General Agent | - | Task tool |
| Docker updates | Bash Agent | - | Task tool |
| Linear updates | Linear MCP | ✅ | Direct |
| Slack notifications | Slack MCP | ✅ | Direct |
| n8n workflows | n8n MCP | ✅ | Direct |
| GitHub PRs | GitHub CLI | ✅ | Bash |

---

## 📋 Linear Issues to Update

After completion, update these issues to Done:
- [ ] ROS-107 → Done (LangChain Node.js Integration)
- [ ] ROS-108 → Done (Docker Updates)
- [ ] ROS-109 → Done (Evidence Bundle)
- [ ] ROS-110 → Done (HTI-1 Attributes)
- [ ] ROS-111 → Done (FAVES Gates)
- [ ] ROS-112 → Done (TRIPOD+AI)
- [ ] ROS-113 → Done (Supply Chain)
- [ ] ROS-114 → Done (Audit Logging)
- [ ] ROS-115 → Done (Monitoring)
- [ ] ROS-75 → Done (n8n Dashboard)

---

## 🎯 Success Criteria

1. All backlog issues moved to Done
2. LangChain bridge functional
3. CI/CD workflows updated
4. Security scanning active
5. Monitoring dashboards deployed
6. Git commit with all changes pushed

---

## 📝 Execution Commands

### Start Parallel Agents
```bash
# Track A: LangChain Integration
claude task --agent explore "Implement ROS-107 LangChain Node.js integration"

# Track B: Evidence & Compliance
claude task --agent general "Implement ROS-109, ROS-110, ROS-111"

# Track D: Security
claude task --agent bash "Implement ROS-113 SBOM and security scanning"
```

### Final Commit
```bash
git add -A
git commit -m "feat: Complete Phases 8-14 + LangChain integration

- ROS-107: LangChain Node.js orchestrator bridge
- ROS-108: Docker deployment updates
- ROS-109: Evidence bundle system v2
- ROS-110: HTI-1 source attributes
- ROS-111: FAVES compliance gates
- ROS-112: TRIPOD+AI checklists
- ROS-113: SBOM + vulnerability scanning
- ROS-114: Hash chain audit logging
- ROS-115: Drift monitoring scheduler

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push origin main
```

---

**Ready for execution. Launch parallel agents now.**
