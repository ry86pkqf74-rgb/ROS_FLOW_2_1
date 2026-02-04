# LangChain & LangSmith Setup and Configuration Guide

## ResearchFlow Production - AI Observability Platform

**Last Updated:** January 30, 2026  
**Status:** ✅ Production Ready  
**Linear Project:** LangChain + Composio Integration

---

## Overview

LangSmith is an observability platform from LangChain for tracing, evaluating, and deploying LLM applications. It logs every step (prompts, tool calls, outputs) in agent workflows, enabling debugging, performance metrics, and A/B testing.

### Why LangSmith for ResearchFlow

- **End-to-end Visibility**: Trace 20-stage runs to identify bottlenecks
- **Evaluation Loops**: Feedback → iteration for agent improvement
- **CI/CD Integration**: Test agents before deployment
- **Framework Agnostic**: Works with LangChain but also standalone
- **PHI Audit**: Track sensitive data handling for compliance

---

## Current Configuration

### Environment Variables (~/.zshrc)

\`\`\`bash
# LangSmith
export LANGSMITH_API_KEY='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'
export LANGSMITH_PROJECT='ROS FLOW'
export LANGSMITH_TRACING_V2='true'
export LANGCHAIN_TRACING_V2='true'
export LANGCHAIN_PROJECT='ROS FLOW'

# Optional: Self-hosted endpoint
# export LANGCHAIN_ENDPOINT='https://api.smith.langchain.com'
\`\`\`

### Dashboard

- **URL**: https://smith.langchain.com
- **Project**: ROS FLOW

---

## Installation

### Python

\`\`\`bash
pip install langsmith langchain langchain-openai langchain-anthropic langgraph
\`\`\`

### Node.js

\`\`\`bash
npm install langsmith
\`\`\`

---

## Code Integration

### Enable Tracing

\`\`\`python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGSMITH_API_KEY"] = "lsv2_pt_..."
os.environ["LANGSMITH_PROJECT"] = "ROS FLOW"
\`\`\`

### Instrument Code with @traceable

\`\`\`python
from langsmith import traceable
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

@traceable(name="run_stage")
def run_stage(input):
    return llm.invoke(input)  # Auto-logged to LangSmith

result = run_stage("Analyze this dataset")
\`\`\`

### Full Runs with RunTree API

\`\`\`python
from langsmith import Client

client = Client()

# Create custom run
with client.create_run(name="research_workflow", run_type="chain") as run:
    run.add_input({"task": "Literature review"})
    # ... perform work
    run.add_output({"papers_found": 15})
\`\`\`

---

## 8 Recommended Observability Tasks for ResearchFlow

Based on Grok analysis, these tasks leverage LangSmith for monitoring/evaluation:

### 1. Tracing Full Workflow Runs
- **Description**: Logs entire 20-stage agent chains
- **How**: Set env vars; view in dashboard
- **When**: All stages (real-time monitoring)
- **Why**: Route debugging, identify slow calls

### 2. Agent Evaluation Task
- **Description**: Runs offline evals on outputs (accuracy of drafts)
- **How**: Create dataset in UI; \`client.run_on_dataset(...)\`
- **When**: Post-stage (e.g., after refinement)
- **Why**: Custom evals for manuscript quality

### 3. Prompt Versioning Agent
- **Description**: Manages A/B tests for prompts
- **How**: Store prompts in LangSmith; pull via Client
- **When**: Prompt changes (dev cycle)
- **Why**: Iterate on CLAUDE_PROMPT_*.md files

### 4. Performance Monitoring Task
- **Description**: Tracks metrics (latency, tokens, errors)
- **How**: Use @traceable; generate reports
- **When**: Production (daily/weekly)
- **Why**: API cost optimization, anomaly detection

### 5. Feedback Loop Agent
- **Description**: Collects/analyzes user feedback on outputs
- **How**: Log interactions; run evals on feedback datasets
- **When**: Post-workflow (continuous improvement)
- **Why**: Human-in-the-loop refinement

### 6. Error Handling Debugger
- **Description**: Traces failures (tool call errors in LangGraph)
- **How**: @traceable on components; inspect runs
- **When**: Debugging sessions
- **Why**: Reduces troubleshooting time (days → hours)

### 7. Deployment CI/CD Task
- **Description**: Automates testing/deploy for agent updates
- **How**: GitHub Actions with LangSmith evals
- **When**: Code changes (PR merges)
- **Why**: Regression testing for agents

### 8. Compliance Audit Agent
- **Description**: Audits traces for PHI leaks or biases
- **How**: Custom evals on logs; report generation
- **When**: HIPAA mode (periodic)
- **Why**: Trust, external auditor integration

---

## Evaluation Setup

### Create Dataset in UI

1. Go to https://smith.langchain.com
2. Create new dataset: "manuscript_evals"
3. Add example inputs/expected outputs

### Run Evaluations Programmatically

\`\`\`python
from langsmith import Client

client = Client()

# Run evals on dataset
results = client.run_on_dataset(
    dataset_name="manuscript_evals",
    llm_or_chain=my_agent,
    evaluation=my_eval_function
)
\`\`\`

### CI/CD Integration

\`\`\`yaml
# .github/workflows/agent-eval.yml
name: Agent Evaluation
on: [push]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run LangSmith Evals
        env:
          LANGSMITH_API_KEY: \${{ secrets.LANGSMITH_API_KEY }}
        run: python scripts/run_evals.py
\`\`\`

---

## Best Practices

1. **Sample Traces**: 10% in production to reduce costs
2. **Disable for Sensitive Runs**: PHI processing
3. **Use @traceable**: On all agent components
4. **A/B Test Prompts**: Store versions in LangSmith
5. **Create Datasets**: For regression testing

---

## File Locations

| File | Purpose |
|------|---------|
| \`services/worker/src/orchestration/langgraph_workflows.py\` | StateGraph workflows |
| \`services/worker/src/orchestration/llm_router.py\` | Multi-LLM routing |
| \`~/.zshrc\` | Environment variables |

---

## Dashboard Navigation

1. **Traces**: View individual run traces
2. **Projects**: Organize by project (researchflow-production)
3. **Datasets**: Create eval datasets
4. **Monitoring**: View aggregate metrics
5. **Playground**: Test prompts interactively

---

## Debugging Workflow

\`\`\`python
# Find failed runs
from langsmith import Client

client = Client()
runs = client.list_runs(
    project_name="ROS FLOW",
    filter="status=error",
    limit=10
)

for run in runs:
    print(f"Run {run.id}: {run.error}")
\`\`\`

---

## Next Steps

- [ ] Create evaluation datasets for each stage
- [ ] Set up CI/CD integration with GitHub Actions
- [ ] Implement sampling for production traces
- [ ] Build compliance audit reports

