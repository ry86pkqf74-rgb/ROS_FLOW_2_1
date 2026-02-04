# 🎯 ResearchFlow Master Execution Plan
## Comprehensive AI Customization + Kubernetes Scaling + Parallel Agent Deployment

**Generated:** January 30, 2026
**Orchestrator:** Claude Cowork (This Session)
**Linear Project:** ROS (ResearchFlow OS)
**GitHub:** github.com/ry86pkqf74-rgb/researchflow-production

---

## 📊 Executive Summary

This plan synthesizes the ResearchFlow_Execution_Plan.docx with current repo state, Notion AI Tools Command Center, and Linear issue tracking to create a comprehensive, tool-aware execution strategy.

### Current State
- **Integration Progress:** ~60% complete (up from 40% documented)
- **Completed Today:** Phases 1-2.1, 4.1, 5.1, 6.2, 7.1 (ROS-80 through ROS-85)
- **Active AI Tools:** 22/22 configured and operational
- **Parallel Agents Available:** 15+ via MCP connectors

### Key Achievements (Jan 30, 2026)
| Issue | Deliverable | Lines |
|-------|-------------|-------|
| ROS-80 | AI Endpoint Inventory & Master Plan | 800+ |
| ROS-81 | Vector Database Package | 500+ |
| ROS-84 | Hybrid RAG Retrieval Pipeline | 727 |
| ROS-83 | Feature Flags for Custom Agents | 306 |
| ROS-82 | Fine-tuning Data Pipeline | 400+ |
| ROS-85 | AI Dashboard Components | 600+ |

---

## 🛠️ AI Tools & Deployment Matrix

### Tool Assignment by Task Type

| Task Category | Primary Tool | Secondary | MCP Server | CLI Command |
|--------------|--------------|-----------|------------|-------------|
| **Orchestration** | Claude Cowork | Linear MCP | ✅ | `claude` |
| **Code Generation** | GPT-4/Cursor | Continue.dev | ✅ | `cn -p "task"` |
| **Security Audit** | Grok | Claude | ❌ | `grok.com` |
| **UI Components** | v0.dev | Figma MCP | ✅ | Manual |
| **Infrastructure** | Replit Agent | Docker MCP | ✅ | `replit` |
| **Documentation** | Context7 | Notion MCP | ✅ | MCP query |
| **Code Search** | Sourcegraph | Grep | ✅ | `cody` |
| **Local Inference** | LM Studio | Ollama | ❌ | `ollama` |
| **Workflow Automation** | n8n | GitHub Actions | ✅ | Webhook |
| **Issue Tracking** | Linear MCP | Notion | ✅ | API |
| **Communication** | Slack MCP | Email | ✅ | API |
| **Model Hub** | Hugging Face MCP | - | ✅ | API |

### MCP Servers Active
```bash
# Verified active MCP servers for this session:
✅ Linear MCP      - Issue tracking, sprint management
✅ Notion MCP      - Documentation, databases
✅ Slack MCP       - Team notifications
✅ GitHub MCP      - PR/Issue management
✅ Figma MCP       - Design system, Code Connect
✅ Hugging Face MCP - Model search, docs
✅ Context7 MCP    - Library documentation
✅ n8n Workflows   - Automation (4 active workflows)
```

---

## 📋 Phase Execution Plan

### Phase 2: Infrastructure Setup (IN PROGRESS → COMPLETING)

**Linear:** ROS-81 ✅ DONE | **Duration:** Completed Jan 30, 2026

#### 2.1 Vector Database ✅ COMPLETE
- **Tool:** Claude Cowork
- **Deliverables:**
  - `packages/vector-store/` (TypeScript package)
  - `docker-compose.yml` updated with vector-db service
  - Hybrid retrieval (semantic + BM25)
- **Commit:** `14f28c5`

#### 2.2 Ollama Enhancement (REMAINING)
- **Tool:** Replit Agent / Docker MCP
- **Task:** Update Ollama config with GPU support, create model pull script
- **Files:**
  - `docker-compose.yml` - Add GPU reservations
  - `scripts/setup-ollama-models.sh` - Model initialization

**Deployment Command:**
```bash
# Deploy to Replit Agent
# Prompt: "Update Ollama service in docker-compose.yml with GPU support
# and create scripts/setup-ollama-models.sh to pull qwen2.5-coder:7b,
# llama3.1:8b, and nomic-embed-text models"
```

---

### Phase 3: Custom Agents + RAG Expansion

**Linear:** ROS-67 ✅, ROS-68, ROS-84 ✅ | **Duration:** 1-2 weeks remaining

#### 3.1 LangGraph Agents ✅ VERIFIED COMPLETE
All 5 phase-specific agents already implemented:
- DataPrep Agent (612 lines) - `services/worker/src/agents/dataprep/`
- Analysis Agent (487 lines) - `services/worker/src/agents/analysis/`
- Quality Agent (489 lines) - `services/worker/src/agents/quality/`
- IRB Agent (478 lines) - `services/worker/src/agents/irb/`
- Manuscript Agent (523 lines) - `services/worker/src/agents/manuscript/`

#### 3.2 RAG Pipeline ✅ COMPLETE
- **Tool:** Claude Cowork
- **Deliverables:**
  - `services/worker/src/rag/hybrid_retriever.py`
  - `services/worker/src/rag/copilot_rag.py`
- **Commit:** `134f7db`

#### 3.3 Knowledge Base Population (REMAINING)
- **Tool:** n8n Workflow + Context7 MCP
- **Task:** Ingest clinical guidelines, IRB protocols, statistical methods

**n8n Workflow to Create:**
```yaml
Name: "RAG Knowledge Ingestion"
Trigger: Manual or Webhook
Steps:
  1. Fetch documents from Notion/GitHub
  2. Process with document_processor.py
  3. Embed via vector-store package
  4. Log to Notion Deployment Execution Log
```

---

### Phase 4: Fine-Tuning Pipeline

**Linear:** ROS-82 ✅ DONE | **Duration:** Completed Jan 30, 2026

#### 4.1 Training Data Preparation ✅ COMPLETE
- **Tool:** Claude Cowork
- **Deliverables:**
  - `scripts/prepare_training_data.py`
  - PHI redaction integration with phi-engine
- **Status:** Ready for training data collection

#### 4.2 LoRA Fine-Tuning (REMAINING)
- **Tool:** Hugging Face MCP + LM Studio
- **Task:** Execute fine-tuning on collected manuscripts
- **Files to Create:**
  - `scripts/train_lora.py`
  - `scripts/export_to_ollama.sh`

**Deployment Command:**
```bash
# Deploy to Hugging Face MCP for model search
# Query: "Find best base model for medical manuscript refinement
# supporting LoRA fine-tuning, 8B parameters or less"
```

---

### Phase 5: AI Router Integration

**Linear:** ROS-83 ✅ DONE | **Duration:** Completed Jan 30, 2026

#### 5.1 CUSTOM Tier ✅ COMPLETE
- **Tool:** Claude Cowork
- **Deliverables:**
  - `packages/ai-router/src/feature-flags.ts` (306 lines)
  - A/B testing infrastructure
  - Gradual rollout percentages (5-60%)
- **Commit:** `6fb67a2`

#### 5.2 Custom Agent Dispatcher (REMAINING)
- **Tool:** GPT-4/Cursor
- **Task:** Implement CustomAgentDispatcher class for CUSTOM tier routing

**Continue.dev Prompt:**
```
cn -p "Create packages/ai-router/src/dispatchers/custom.ts implementing
CustomAgentDispatcher that routes to LangGraph agents at
http://worker:8000/agents/{agentName}. Include metrics recording
with Prometheus client and fallback to FRONTIER tier on errors."
```

---

### Phase 6: Kubernetes Scaling

**Linear:** ROS-86 (Backlog) | **Duration:** 2 weeks

#### 6.1 Resource Configuration
- **Tool:** Replit Agent / Docker MCP
- **Files:**
  - `infrastructure/kubernetes/base/*/deployment.yaml`
  - Resource requests/limits for all services

#### 6.2 Horizontal Pod Autoscaler
- **Tool:** GPT-4/Cursor
- **Files:**
  - `infrastructure/kubernetes/base/worker/hpa.yaml`
  - `infrastructure/kubernetes/base/orchestrator/hpa.yaml`

**Deployment Command:**
```bash
# Deploy to GPT-4 via Cursor
# Prompt: "Create HPA configurations for worker (CPU 70%, 2-10 replicas)
# and orchestrator (CPU 60%, 2-10 replicas) with stabilization windows"
```

---

### Phase 7: Frontend Integration

**Linear:** ROS-85 ✅ DONE | **Duration:** Completed Jan 30, 2026

#### 7.1 Agent Dashboard Components ✅ COMPLETE
- **Tool:** Claude Cowork + v0.dev
- **Deliverables:**
  - `services/web/src/components/ai/AgentStatus.tsx`
  - `services/web/src/components/ai/AgentProgress.tsx`
  - `services/web/src/hooks/useAgentProgress.ts`
- **Commit:** `eda9ef0`

---

### Phase 8: Production Deployment

**Linear:** ROS-86 (Part of Master) | **Duration:** 1 week

#### 8.1 Docker Compose Production
- **Tool:** Replit Agent
- **File:** `docker-compose.prod.yml`

#### 8.2 Deployment Automation
- **Tool:** n8n + GitHub Actions
- **Workflow:** Automated deployment with health checks

---

## 🚀 Parallel Deployment Commands

### Immediate Parallel Tasks (Execute Now)

#### Task 1: Ollama GPU Configuration
**Tool:** Replit Agent
**Linear:** Create ROS-95
```
Update docker-compose.yml Ollama service with:
1. GPU reservations (nvidia driver)
2. Model volume mounting
3. Health check endpoint
Create scripts/setup-ollama-models.sh
```

#### Task 2: Custom Agent Dispatcher
**Tool:** Continue.dev CLI
**Linear:** Create ROS-96
```bash
cn -p "Implement CustomAgentDispatcher in packages/ai-router/src/dispatchers/custom.ts"
```

#### Task 3: Kubernetes HPA
**Tool:** GPT-4/Cursor
**Linear:** Create ROS-97
```
Create HPA configurations:
- infrastructure/kubernetes/base/worker/hpa.yaml
- infrastructure/kubernetes/base/orchestrator/hpa.yaml
```

#### Task 4: RAG Knowledge Ingestion Workflow
**Tool:** n8n
**Linear:** Create ROS-98
```
Create n8n workflow for document ingestion:
- Webhook trigger
- Document processing
- Vector embedding
- Status logging to Notion
```

#### Task 5: Design System Setup
**Tool:** Figma MCP + v0.dev
**Linear:** ROS-88, ROS-89 (Already created)
```
Execute design-tokens pipeline and UI component library
```

---

## 📊 Linear Issue Tracking

### Issues to Create
| ID | Title | Priority | Assignee Tool |
|----|-------|----------|---------------|
| ROS-95 | [INFRA] Ollama GPU Configuration | P1 | Replit Agent |
| ROS-96 | [ROUTER] Custom Agent Dispatcher | P1 | Continue.dev |
| ROS-97 | [K8S] HPA Configuration | P2 | GPT-4/Cursor |
| ROS-98 | [N8N] RAG Ingestion Workflow | P2 | n8n |

### Existing Issues to Update
- ROS-86: Update with execution progress
- ROS-68: Link to RAG implementation
- ROS-87: Track compliance phases

---

## 🔄 n8n Workflow Integration

### Active Workflows (4)
1. **ResearchFlow: GitHub → Notion Sync** - PR/Issue sync
2. **ResearchFlow: Stage Completion** - Milestone tracking
3. **ResearchFlow: Deployment Notify** - Slack alerts
4. **ResearchFlow: Notion → CI Trigger** - Deployment automation

### Workflows to Create
1. **RAG Knowledge Ingestion** - Document processing pipeline
2. **AI Usage Tracking** - Log all AI tool invocations
3. **Agent Health Monitor** - Check LangGraph agent status

---

## ✅ Execution Checklist

### Phase 2 (Completing)
- [x] Vector database package created
- [ ] Ollama GPU configuration
- [ ] Model pull script created

### Phase 3 (Completing)
- [x] LangGraph agents verified
- [x] RAG hybrid retrieval implemented
- [ ] Knowledge base population workflow

### Phase 4 (Completing)
- [x] Training data preparation script
- [ ] LoRA fine-tuning execution
- [ ] Model export to Ollama

### Phase 5 (Completing)
- [x] CUSTOM tier feature flags
- [ ] CustomAgentDispatcher class
- [ ] A/B testing validation

### Phase 6 (Starting)
- [ ] Metrics Server installation
- [ ] Resource limits configuration
- [ ] HPA for all services
- [ ] Load testing validation

### Phase 7 (Complete)
- [x] Agent progress components
- [x] WebSocket hooks
- [x] Dashboard integration

### Phase 8 (Pending)
- [ ] docker-compose.prod.yml finalization
- [ ] Deployment script
- [ ] Monitoring setup
- [ ] Production deployment

---

## 📝 Quick Reference Commands

### Continue.dev CLI
```bash
cn                        # Interactive mode
cn -p "task description"  # Headless execution
/model                    # Switch models (Mercury, Claude 4, Grok 4, GPT-5)
```

### Linear MCP
```bash
# Create issue
mcp__linear__create_issue --title "[TASK] Description" --team "ROS" --priority 1

# Update issue
mcp__linear__update_issue --id "ROS-XX" --state "Done"
```

### n8n Workflow Execution
```bash
# Via webhook
curl -X POST https://n8n.instance/webhook/workflow-id -d '{"data": "payload"}'
```

### Docker Commands
```bash
docker-compose up -d chromadb ollama  # Start AI services
docker-compose logs -f worker         # Monitor agents
```

---

## 🎯 Success Metrics

| Metric | Target | Current | Measurement |
|--------|--------|---------|-------------|
| Custom agent coverage | 90%+ stages | 100% | Agents verified |
| API call reduction | 80% fewer | TBD | Monitor after deployment |
| Average latency | <60s/agent | TBD | Prometheus metrics |
| Quality gate pass | >60% first try | TBD | Agent logs |
| K8s auto-scaling | 2-10 pods | TBD | HPA events |
| Cost savings | 30-50% | TBD | Cloud billing |

---

## 📚 Related Documentation

- [Notion: AI Tools Command Center](https://notion.so/2f650439dcba819aa9c8e9138609ddb9)
- [Notion: Parallel Agent Execution Tracker](https://notion.so/2f750439dcba8180a6dde30fdfa5e15c)
- [Notion: Mission Control](https://notion.so/2f650439dcba81b290fce90627585cc4)
- [GitHub: AI Ecosystem Guide](docs/AI_ECOSYSTEM_GUIDE.md)
- [GitHub: AI Endpoint Inventory](docs/AI_ENDPOINT_INVENTORY.md)
- [GitHub: AI Customization Master Plan](docs/RESEARCHFLOW_AI_CUSTOMIZATION_MASTER_PLAN.md)

---

**Generated by Claude Cowork Orchestrator**
**Session:** January 30, 2026
**Next Steps:** Execute parallel deployments via Linear issues and agent dispatch
