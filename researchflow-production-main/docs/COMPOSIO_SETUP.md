# Composio Setup and Configuration Guide

## ResearchFlow Production - AI Tool Integration Platform

**Last Updated:** January 30, 2026  
**Status:** ✅ Production Ready  
**Linear Project:** LangChain + Composio Integration

---

## Overview

Composio is an AI-native integration platform connecting AI agents to 500+ external tools (GitHub, Notion, Slack, PubMed, Google Docs). It abstracts OAuth, API keys, error handling, and maintenance, allowing agents to focus on tasks.

### Why Composio for ResearchFlow

- **Agentic Autonomy**: Agents act independently on external services
- **Multi-user Auth**: AgentAuth handles per-user OAuth flows
- **Security**: Managed OAuth prevents key leaks
- **Framework Agnostic**: Works with LangChain/LangGraph, CrewAI, AutoGen
- **HIPAA Ready**: Scoped auth for PHI-safe operations

---

## Current Configuration

### Connected Apps (via OAuth)

| App | Connection ID | Label | Status |
|-----|---------------|-------|--------|
| GitHub | edd744dd-21a6-4a71-9974-0523686e980e | logan.glosser_workspace_first_project | ✅ |
| Linear | a4132e52-5603-4916-bcef-d262ad2093f7 | logan.glosser_workspace_first_project | ✅ |
| Slack | 5069d701-0704-4723-82e9-ceb1eabbe7fb | logan.glosser_workspace_first_project | ✅ |
| Notion | 001cf077-a6e3-44cf-a09d-4c5b2e3b38ac | logan.glosser_workspace_first_project | ✅ |

### Environment Variables

\`\`\`bash
# Required
COMPOSIO_API_KEY=ak_YhbOJal4TkAsNUR0NX2j

# Optional (for direct API access)
GITHUB_TOKEN=your_github_token
LINEAR_API_KEY=your_linear_key
SLACK_WEBHOOK=your_slack_webhook
NOTION_API_KEY=your_notion_key
\`\`\`

---

## Installation

### Python (services/worker)

\`\`\`bash
pip install composio-langchain composio-core langchain langchain-openai langgraph python-dotenv
\`\`\`

### Node.js (services/orchestrator)

\`\`\`bash
npm install composio-js
\`\`\`

### CLI Setup

\`\`\`bash
# Install CLI
pip install composio-core

# Login with API key
export COMPOSIO_API_KEY=ak_YhbOJal4TkAsNUR0NX2j

# Add integrations
composio add github -l logan.glosser_workspace_first_project
composio add linear -l logan.glosser_workspace_first_project -a OAUTH2
composio add slack -l logan.glosser_workspace_first_project
composio add notion -l logan.glosser_workspace_first_project -a OAUTH2

# Verify connections
composio connections
\`\`\`

---

## Code Integration

### Initialize Composio Client (Python)

\`\`\`python
# services/worker/src/agent_init.py
import os
from composio_langchain import ComposioToolSet, App
from langchain_openai import ChatOpenAI
from langgraph import Agent

os.environ["COMPOSIO_API_KEY"] = os.getenv("COMPOSIO_API_KEY")
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Initialize toolset (filters tools by app)
toolset = ComposioToolSet()
tools = toolset.get_tools(apps=[App.GOOGLEDOCS, App.NOTION, App.GITHUB, App.SLACK])
\`\`\`

### Connect Tools Programmatically

\`\`\`python
from composio.client import Composio

composio_client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
composio_client.connect_app(App.GOOGLEDOCS, auth_params={"client_id": "your-id"})
\`\`\`

### Wrap in LangGraph Agent

\`\`\`python
agent = Agent(tools=tools, llm=llm, planner="zero-shot-react")
result = agent.run("Fetch latest papers on AI ethics from PubMed and summarize in a Google Doc.")
\`\`\`

---

## 8 Recommended Agents for ResearchFlow 20-Stage Workflow

Based on Grok analysis, these agents leverage Composio for external integrations:

### 1. Literature Retrieval Agent
- **Description**: Searches/fetches papers from PubMed/Semantic Scholar
- **Tools**: \`toolset.get_tools(apps=[App.PUBMED])\`
- **When**: Stage 1-3 (Proposal/Lit Review)
- **Why**: Automates citation gathering, downloads PDFs

### 2. Data Analysis Agent
- **Description**: Analyzes datasets from Excel, generates plots
- **Tools**: Google Sheets/Notion
- **Code**: \`agent.run("Analyze CSV and plot in Sheets")\`
- **When**: Stage 10-12 (Stats/Data Viz)

### 3. Manuscript Writer Agent
- **Description**: Generates/refines proposals and manuscripts
- **Tools**: \`[App.GOOGLEDOCS]\`
- **When**: Stage 4-8 (Refinement/Generation)
- **Why**: Iterates drafts with feedback

### 4. Conference Prep Task
- **Description**: Discovers conferences, parses guidelines, generates abstracts
- **Tools**: Google Calendar/Slack for scheduling
- **Code**: \`agent.run("Find AI conferences and draft abstract")\`
- **When**: Stage 20 (Conference) - Monthly trigger

### 5. Code Generation Agent
- **Description**: Generates/optimizes code for stats pipelines
- **Tools**: \`[App.GITHUB]\`
- **When**: Stage 9-11 (Code/Execution)
- **Why**: Integrates with LOCAL tier for analysis

### 6. Collaboration Notifier Agent
- **Description**: Updates team via Slack/Notion on workflow progress
- **Tools**: Slack/Notion
- **Code**: \`agent.run("Post summary to Slack")\`
- **When**: Any stage (event-triggered)

### 7. Feedback Analyzer Task
- **Description**: Reads feedback from CSVs/Google Forms, summarizes
- **Tools**: Google Forms/Sheets
- **When**: Post-workflow (iteration loop)

### 8. Deep Research Sub-Agent
- **Description**: Multi-step research (web scrape, synthesize)
- **Tools**: ExaAI/Browser with DeepRAG verification
- **When**: Complex queries (lit gaps) as sub-task

---

## Testing and Best Practices

### Local Testing

\`\`\`bash
# Run agent locally
python -c "
from composio_langchain import ComposioToolSet
toolset = ComposioToolSet()
print('Available apps:', [app.name for app in toolset.get_apps()[:10]])
"
\`\`\`

### Best Practices

1. **Scope Tools**: Use per-stage tool subsets to reduce prompt bloat
2. **Error Handling**: Composio SDK includes retries
3. **Triggers**: Use for event-driven agents (new GitHub issue → analysis)
4. **PHI Safety**: Pair with redaction engine for sensitive data
5. **Rate Limits**: Monitor usage to avoid API limits

---

## File Locations

| File | Purpose |
|------|---------|
| \`services/worker/src/orchestration/composio_tools.py\` | Toolset wrapper |
| \`services/worker/requirements.txt\` | Python deps |
| \`~/.composio/\` | CLI config |
| \`~/.zshrc\` | Env vars |

---

## CLI Reference

\`\`\`bash
composio apps                    # List all available apps
composio connections             # List connected apps
composio add <app> -l <label>    # Add integration
composio add <app> -a OAUTH2     # Specify auth mode
composio whoami                  # Check API key status
\`\`\`

---

## Next Steps

- [ ] ROS-107: Node.js Orchestrator Integration
- [ ] ROS-108: Docker & Deployment Updates
- [ ] Add PubMed/Google Docs integrations
- [ ] Implement per-stage tool routing

