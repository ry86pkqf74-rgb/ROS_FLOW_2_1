#!/usr/bin/env python3
"""
DesignOps Agent - Figma → Design Tokens → PR Automation

This agent monitors Figma for design changes and automatically:
1. Extracts design tokens from Figma components
2. Transforms tokens to Tailwind CSS configuration
3. Creates GitHub branches and PRs with the changes
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Composio imports - lazy loading with graceful fallback for LangGraph Cloud
try:
    from composio_langchain import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError as e:
    ComposioToolSet = None
    Action = None
    COMPOSIO_AVAILABLE = False
    import warnings
    warnings.warn(f"Composio not available: {e}. DesignOpsAgent will have limited functionality.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage

# LangChain Agent imports - lazy loading for compatibility
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    LANGCHAIN_AGENTS_AVAILABLE = True
except ImportError:
    try:
        # Fallback: try importing from langchain_core
        from langchain_core.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
        LANGCHAIN_AGENTS_AVAILABLE = True
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        LANGCHAIN_AGENTS_AVAILABLE = False
        import warnings
        warnings.warn("LangChain agent components not available. Agent functionality will be limited.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DesignOps Agent Configuration
# Actions are only available if Composio is installed
_COMPOSIO_ACTIONS = []
if COMPOSIO_AVAILABLE and Action is not None:
    _COMPOSIO_ACTIONS = [
        # Figma Actions
        Action.FIGMA_GET_FILE_COMPONENTS,
        Action.FIGMA_GET_FILE_STYLES,
        Action.FIGMA_GET_FILE_VERSIONS,
        Action.FIGMA_EXPORT_COMPONENT_ASSETS,
        Action.FIGMA_CREATE_WEBHOOK,
        # GitHub Actions
        Action.GITHUB_CREATE_A_BRANCH,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
        Action.GITHUB_CREATE_A_PULL_REQUEST,
        Action.GITHUB_REQUEST_REVIEWERS_FOR_A_PULL_REQUEST,
        Action.GITHUB_ADD_LABELS_TO_AN_ISSUE,
    ]

DESIGN_OPS_CONFIG = {
    "name": "DesignOps Agent",
    "model": "gpt-4o",
    "temperature": 0,
    "toolkits": ["FIGMA", "GITHUB"] if COMPOSIO_AVAILABLE else [],
    "actions": _COMPOSIO_ACTIONS,
    "system_prompt": """You are the DesignOps Agent for ResearchFlow.

Your responsibilities:
1. Monitor Figma for design changes via webhooks
2. Extract design tokens from Figma components (colors, typography, spacing, shadows)
3. Transform tokens to Tailwind CSS configuration
4. Generate/update packages/design-tokens/tokens.json
5. Generate/update tailwind.config.ts
6. Open PRs with comprehensive change summaries
7. Add appropriate reviewers from the design team

Token Extraction Format:
{
  "colors": {
    "primary": {"50": "#...", "100": "#...", ...},
    "secondary": {...}
  },
  "typography": {
    "fontFamily": {"sans": [...], "mono": [...]},
    "fontSize": {"xs": "0.75rem", ...}
  },
  "spacing": {"0": "0", "1": "0.25rem", ...},
  "shadows": {"sm": "...", "md": "..."}
}

Always:
- Ensure design token changes maintain backward compatibility
- Document all breaking changes clearly in PR descriptions
- Use conventional commit format: "feat(design-tokens): ..."
- Add labels: "design-tokens", "automated"
"""
}


class DesignOpsAgent:
    """DesignOps Agent for Figma → PR automation"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production"
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=DESIGN_OPS_CONFIG["model"],
            temperature=DESIGN_OPS_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=DESIGN_OPS_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", DESIGN_OPS_CONFIG["system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15,
            return_intermediate_steps=True
        )

    def extract_design_tokens(self, figma_file_key: str) -> Dict[str, Any]:
        """Extract design tokens from a Figma file"""
        logger.info(f"Extracting design tokens from Figma file: {figma_file_key}")

        result = self.agent.invoke({
            "input": f"""Extract all design tokens from Figma file with key: {figma_file_key}

Steps:
1. Get file components using FIGMA_GET_FILE_COMPONENTS
2. Get file styles using FIGMA_GET_FILE_STYLES
3. Extract and categorize tokens:
   - Colors (primary, secondary, neutral, semantic)
   - Typography (font families, sizes, weights, line heights)
   - Spacing (consistent spacing scale)
   - Border radius
   - Shadows
4. Return the tokens in the standard JSON format

Output the extracted tokens as a JSON object."""
        })

        return result

    def create_design_tokens_pr(
        self,
        figma_file_key: str,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Full workflow: Extract tokens and create a PR"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch = branch_name or f"design-tokens/update-{timestamp}"

        logger.info(f"Creating design tokens PR from Figma file: {figma_file_key}")

        result = self.agent.invoke({
            "input": f"""Complete the full DesignOps workflow:

1. Extract design tokens from Figma file: {figma_file_key}
2. Transform tokens to Tailwind CSS format
3. Create a new branch: {branch}
4. Commit the updated tokens to packages/design-tokens/tokens.json
5. Create a PR with title: "feat(design-tokens): Update design tokens from Figma"
6. Add labels: "design-tokens", "automated"
7. Request review from design-team

Repository: {self.github_repo}

Execute each step and report the results."""
        })

        return result

    def setup_figma_webhook(
        self,
        figma_file_key: str,
        webhook_url: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """Set up a Figma webhook for automatic token updates"""
        events = events or ["FILE_VERSION_UPDATE", "LIBRARY_PUBLISH"]

        result = self.agent.invoke({
            "input": f"""Set up a Figma webhook:
- File key: {figma_file_key}
- Webhook URL: {webhook_url}
- Events: {', '.join(events)}

Use FIGMA_CREATE_WEBHOOK to create the webhook and confirm it's active."""
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task"""
        return self.agent.invoke({"input": task})


def main():
    """Demo the DesignOps agent"""
    print("🎨 DesignOps Agent - Figma → PR Automation")
    print("=" * 50)

    # Check for required environment variables
    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = DesignOpsAgent()

    # List available tools
    print("\n📦 Available tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}")

    # Example: Run a simple task
    print("\n🚀 Running example task...")
    result = agent.run(
        "List my connected Figma files and their latest versions"
    )
    print(f"\n📋 Result: {result['output']}")


if __name__ == "__main__":
    main()
