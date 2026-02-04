# ResearchFlow Tool Integration Reference

## Quick Reference for AI Orchestration Tools

**Last Updated:** January 30, 2026

---

## 1. Composio Integration

### Project Info
- **Workspace:** `logan.glosser_workspace_first_project`
- **API Key:** Set in `COMPOSIO_API_KEY` env var
- **Config:** `~/.composio/config.yaml`

### Connected Apps
| App | Connection ID | Status |
|-----|---------------|--------|
| GitHub | edd744dd-21a6-4a71-9974-0523686e980e | ✅ |
| Linear | a4132e52-5603-4916-bcef-d262ad2093f7 | ✅ |
| Slack | 5069d701-0704-4723-82e9-ceb1eabbe7fb | ✅ |
| Notion | 001cf077-a6e3-44cf-a09d-4c5b2e3b38ac | ✅ |

### CLI Commands
```bash
composio connections              # List connections
composio add <app> -l logan.glosser_workspace_first_project
composio apps                     # List available apps
```

### Code Location
- `services/worker/src/orchestration/composio_tools.py`
- `services/worker/src/orchestration/composio_agents.py`

### 8 Agents Available
1. **Literature Retrieval** (Stages 1-3) - PubMed/papers
2. **Data Analysis** (Stages 4-8) - Statistical pipelines
3. **Manuscript Writer** (Stages 15-18) - Paper drafting
4. **Conference Prep** (Stage 20) - Submissions
5. **Code Generation** (Stages 9-11) - Python/R scripts
6. **Collaboration Notifier** (All) - Slack/Linear updates
7. **Feedback Analyzer** (Stages 17-19) - Review comments
8. **Deep Research** (Stages 1-5) - Extended lit search

---

## 2. LangSmith Integration

### Project Info
- **Project:** `ROS FLOW`
- **Dashboard:** https://smith.langchain.com
- **Tracing:** V2 Enabled

### Environment Variables
```bash
LANGSMITH_API_KEY=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
LANGSMITH_PROJECT="ROS FLOW"
LANGSMITH_TRACING_V2=true
```

### Code Location
- `services/worker/src/orchestration/langsmith_observability.py`

### 8 Observability Tasks
1. **Trace Workflow Runs** - 20-stage logging
2. **Agent Evaluation** - Gold dataset comparison
3. **Prompt Versioning** - Per-stage templates
4. **Performance Monitoring** - Latency/tokens/errors
5. **Feedback Loop** - User ratings
6. **Error Debugger** - Failed call context
7. **CI/CD Integration** - Pre-merge gates
8. **Compliance Audit** - PHI detection logs

### Usage
```python
from orchestration import LangSmithObservability, trace

obs = LangSmithObservability()

@trace("my_function")
def my_function(input):
    return process(input)

# Track workflow
with obs.trace_workflow("wf-123", ["stage1", "stage2"], inputs):
    result = run_workflow()
```

---

## 3. LangGraph Workflows

### Location
- `services/worker/src/orchestration/langgraph_workflows.py`

### Workflow Architecture
```
Planner → PHI Check → [Local | Generator] → Deployer
```

### LLM Routing
| Task Type | Provider | Model |
|-----------|----------|-------|
| Reasoning | Claude | claude-3-5-sonnet |
| Generation | GPT-4 | gpt-4o |
| Analysis | Grok | grok-beta |
| Coding/PHI | Ollama | qwen2.5-coder:7b |

---

## 4. Continue.dev Integration

### Notion Reference
- Page: [Continue.dev](https://www.notion.so/2f650439dcba8145af12f6f3ba2f4845)
- Docs: https://docs.continue.dev/

### Configuration
- Config location: `~/.continue/config.json`
- Models: Claude, GPT-4, local Ollama

### Use Cases
- Code completion
- Inline chat
- Multi-file editing
- Documentation generation

---

## 5. Cursor Integration

### Features
- AI-powered code editor
- Agent mode for complex tasks
- Multi-file refactoring
- Codebase Q&A

### Best For
- Large refactors
- New feature implementation
- Code review assistance

---

## 6. n8n Workflows

### Connection
- URL: Local or hosted instance
- Webhook triggers available

### Existing Workflows
- RAG Knowledge Ingestion (ROS-98)
- Safety event automation (planned)

---

## 7. Linear Integration

### Project
- **LangChain + Composio Integration** (Active)
- Issues: ROS-103 through ROS-108

### API Access
- Via Composio agent
- Direct: `LINEAR_API_KEY` env var

---

## 8. GitHub Integration

### Repository
- https://github.com/ry86pkqf74-rgb/researchflow-production

### Latest Commits
- `b73dce0` - feat(orchestration): 8 agents + 8 observability tasks
- `8167edf` - docs: Update project names
- `75a7083` - feat(orchestration): LangChain + Composio integration

### CI/CD
- GitHub Actions workflows in `.github/workflows/`
- Planned: FAVES gates, checklist validation, SBOM

---

## Quick Verification Commands

```bash
# Check Composio
composio connections

# Test LangSmith
python -c "from langsmith import Client; c=Client(); print(c.list_projects())"

# Verify Python modules
python -c "from orchestration import ResearchFlowAgents, LangSmithObservability; print('OK')"

# Check Linear issues
# (via MCP or curl to Linear API)
```

---

## File Locations Summary

| Tool | Primary File | Config |
|------|--------------|--------|
| Composio | composio_agents.py | ~/.composio/ |
| LangSmith | langsmith_observability.py | env vars |
| LangGraph | langgraph_workflows.py | - |
| Continue.dev | - | ~/.continue/ |
| n8n | - | n8n instance |

---

**Documentation:**
- `docs/COMPOSIO_SETUP.md`
- `docs/LANGCHAIN_LANGSMITH_SETUP.md`
- `docs/TRANSPARENCY_BUILD_PLAN.md`
