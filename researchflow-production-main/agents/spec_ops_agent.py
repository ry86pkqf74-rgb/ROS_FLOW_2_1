#!/usr/bin/env python3
"""
SpecOps Agent - Notion PRD → GitHub Issues Synchronization

This agent synchronizes requirements from Notion PRDs to GitHub issues:
1. Fetches PRD pages from Notion Problem Registry
2. Extracts requirements and acceptance criteria
3. Creates GitHub issues with proper structure
4. Maintains bidirectional sync between Notion and GitHub
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
    warnings.warn(f"Composio not available: {e}. SpecOpsAgent will have limited functionality.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangChain Agent imports - lazy loading for compatibility
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    LANGCHAIN_AGENTS_AVAILABLE = True
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
        LANGCHAIN_AGENTS_AVAILABLE = True
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        LANGCHAIN_AGENTS_AVAILABLE = False
        import warnings
        warnings.warn("LangChain agent components not available.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SpecOps Agent Configuration
# Actions are only available if Composio is installed
_SPEC_OPS_ACTIONS = []
if COMPOSIO_AVAILABLE and Action is not None:
    _SPEC_OPS_ACTIONS = [
        # Notion Actions
        Action.NOTION_SEARCH_PAGES,
        Action.NOTION_GET_PAGE,
        Action.NOTION_GET_DATABASE,
        Action.NOTION_QUERY_A_DATABASE,
        Action.NOTION_CREATE_A_PAGE,
        Action.NOTION_UPDATE_A_PAGE,
        Action.NOTION_APPEND_BLOCK_CHILDREN,
        # GitHub Actions
        Action.GITHUB_CREATE_AN_ISSUE,
        Action.GITHUB_UPDATE_AN_ISSUE,
        Action.GITHUB_ADD_LABELS_TO_AN_ISSUE,
        Action.GITHUB_CREATE_A_MILESTONE,
        Action.GITHUB_GET_A_MILESTONE,
        Action.GITHUB_LIST_MILESTONES,
    ]

SPEC_OPS_CONFIG = {
    "name": "SpecOps Agent",
    "model": "gpt-4o-mini",
    "temperature": 0,
    "toolkits": ["NOTION", "GITHUB"] if COMPOSIO_AVAILABLE else [],
    "actions": _SPEC_OPS_ACTIONS,
    "system_prompt": """You are the SpecOps Agent for ResearchFlow.

Your responsibilities:
1. Fetch PRD pages from Notion Problem Registry database
2. Extract requirements and acceptance criteria
3. Parse user stories and technical specifications
4. Create GitHub issues with proper structure:
   - Clear title following convention
   - Detailed description with acceptance criteria
   - Appropriate labels (feature, bug, task, epic)
   - Milestone assignment
5. Update Notion with GitHub issue links
6. Maintain bidirectional sync between Notion and GitHub

Issue Template Format:
## Summary
[Brief description of the feature/task]

## User Story
As a [role], I want [feature] so that [benefit]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
[Implementation guidance if available]

## References
- Notion PRD: [link]
- Related Issues: #xxx

Labels to use:
- Type: feature, bug, enhancement, task, epic
- Priority: priority:critical, priority:high, priority:medium, priority:low
- Status: status:ready, status:blocked, status:in-progress
- Source: from-notion, from-prd

Always include:
- User story format where applicable
- Clear acceptance criteria as checkboxes
- Technical notes for implementation guidance
- Link back to the Notion PRD
"""
}


class SpecOpsAgent:
    """SpecOps Agent for Notion → GitHub synchronization"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
        notion_databases: Optional[Dict[str, str]] = None
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo
        self.notion_databases = notion_databases or {
            "problem_registry": os.getenv("NOTION_PROBLEM_REGISTRY_DB", ""),
            "dataset_registry": os.getenv("NOTION_DATASET_REGISTRY_DB", ""),
            "model_registry": os.getenv("NOTION_MODEL_REGISTRY_DB", ""),
        }

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=SPEC_OPS_CONFIG["model"],
            temperature=SPEC_OPS_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=SPEC_OPS_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", SPEC_OPS_CONFIG["system_prompt"]),
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

    def sync_prd_to_issues(self, prd_page_id: str) -> Dict[str, Any]:
        """Sync a single Notion PRD page to GitHub issues"""
        logger.info(f"Syncing PRD page {prd_page_id} to GitHub issues")

        result = self.agent.invoke({
            "input": f"""Sync Notion PRD to GitHub issues:

1. Fetch the Notion page with ID: {prd_page_id}
2. Extract all requirements and acceptance criteria
3. For each requirement, create a GitHub issue in {self.github_repo}:
   - Use the issue template format
   - Add appropriate labels
   - Link back to the Notion PRD
4. After creating each issue, update the Notion page with the GitHub issue link

Execute each step and report the created issues."""
        })

        return result

    def sync_all_prds(self, database_id: Optional[str] = None) -> Dict[str, Any]:
        """Sync all PRDs from the Problem Registry to GitHub"""
        db_id = database_id or self.notion_databases.get("problem_registry")

        if not db_id:
            return {"error": "No Problem Registry database ID configured"}

        logger.info(f"Syncing all PRDs from database {db_id}")

        result = self.agent.invoke({
            "input": f"""Sync all PRDs from Notion to GitHub:

1. Query the Notion database: {db_id}
2. Filter for PRDs that need syncing (status: "Ready for Dev" or similar)
3. For each PRD:
   - Extract requirements
   - Create GitHub issues
   - Update Notion with issue links
4. Create a summary of all synced items

Repository: {self.github_repo}"""
        })

        return result

    def create_milestone_from_prd(
        self,
        prd_page_id: str,
        milestone_title: str,
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a GitHub milestone from a PRD"""
        logger.info(f"Creating milestone '{milestone_title}' from PRD {prd_page_id}")

        due_clause = f"- Due date: {due_date}" if due_date else ""

        result = self.agent.invoke({
            "input": f"""Create a GitHub milestone from a Notion PRD:

1. Fetch the Notion page: {prd_page_id}
2. Create a GitHub milestone:
   - Title: {milestone_title}
   {due_clause}
   - Description: Extract from PRD summary
3. Create all related issues and assign to this milestone
4. Update Notion with the milestone link

Repository: {self.github_repo}"""
        })

        return result

    def update_notion_from_github(self, issue_number: int) -> Dict[str, Any]:
        """Update Notion when a GitHub issue changes"""
        logger.info(f"Updating Notion from GitHub issue #{issue_number}")

        result = self.agent.invoke({
            "input": f"""Update Notion from GitHub issue changes:

1. Get GitHub issue #{issue_number} from {self.github_repo}
2. Find the linked Notion page
3. Update the Notion page with:
   - Current issue status
   - Assignees
   - Any comments or updates
4. Confirm the sync was successful"""
        })

        return result

    def search_and_link(self, search_query: str) -> Dict[str, Any]:
        """Search Notion for PRDs and create GitHub issues"""
        result = self.agent.invoke({
            "input": f"""Search Notion and create GitHub issues:

1. Search Notion for pages matching: "{search_query}"
2. For each matching PRD page:
   - Extract requirements
   - Create a GitHub issue
   - Link the issue back to Notion
3. Return a summary of created issues"""
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task"""
        return self.agent.invoke({"input": task})


def main():
    """Demo the SpecOps agent"""
    print("📋 SpecOps Agent - Notion → GitHub Sync")
    print("=" * 50)

    # Check for required environment variables
    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = SpecOpsAgent()

    # List available tools
    print("\n📦 Available tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}")

    # Example: List Notion databases
    print("\n🚀 Running example task...")
    result = agent.run(
        "Search for pages in my Notion workspace related to 'requirements' or 'PRD'"
    )
    print(f"\n📋 Result: {result['output']}")


if __name__ == "__main__":
    main()
