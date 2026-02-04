#!/usr/bin/env python3
"""
Orchestration Fix Agent - Backend ↔ Frontend Wiring Remediation

This agent applies fixes for wiring gaps identified in audits, ensuring
end-to-end orchestration between backend services, frontend UI, and docs.
"""

import os
import logging
from typing import Dict, Any, Optional

from composio_langchain import ComposioToolSet, Action
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


ORCHESTRATION_FIX_CONFIG = {
    "name": "Orchestration Fix Agent",
    "model": os.getenv("ORCHESTRATION_FIX_MODEL", "gpt-4o"),
    "temperature": _get_float_env("ORCHESTRATION_FIX_TEMPERATURE", 0),
    "toolkits": ["GITHUB"],
    "actions": [
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_A_BRANCH,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
        Action.GITHUB_CREATE_A_PULL_REQUEST,
        Action.GITHUB_CREATE_AN_ISSUE,
        Action.GITHUB_ADD_LABELS_TO_AN_ISSUE,
    ],
    "system_prompt": """You are the Orchestration Fix Agent for ResearchFlow.

Your responsibilities:
1. Read the latest wiring report and identify priority gaps.
2. Implement fixes to align frontend API calls with backend routes.
3. Ensure backend routes are mounted and documented.
4. Update Docker compose env vars and .env.example if required.
5. Add or update tests and verification scripts where gaps are fixed.
6. Summarize changes with file-level references.

Guidance:
- Prefer minimal, high-impact changes to close wiring gaps.
- Keep API contracts consistent; add backward-compatible handling.
- Update docs when behavior changes.

When applying fixes:
- Update services/web for API call alignment
- Update services/orchestrator routes or mounts as needed
- Update docker-compose.yml and .env.example for missing env vars
- Add verification steps (scripts or tests) when possible
""",
}


class OrchestrationFixAgent:
    """Agent to fix backend/frontend wiring gaps."""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo

        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id,
        )

        self.llm = ChatOpenAI(
            model=ORCHESTRATION_FIX_CONFIG["model"],
            temperature=ORCHESTRATION_FIX_CONFIG["temperature"],
            api_key=self.openai_api_key,
        )

        self.tools = self.toolset.get_tools(actions=ORCHESTRATION_FIX_CONFIG["actions"])
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages([
            ("system", ORCHESTRATION_FIX_CONFIG["system_prompt"]),
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
            max_iterations=20,
            return_intermediate_steps=True,
        )

    def fix_gaps(
        self,
        report_path: str = "docs/audit/WIRING_STATUS_REPORT.md",
        focus: str = "frontend-backend",
    ) -> Dict[str, Any]:
        """Apply fixes for wiring gaps described in a report."""
        logger.info("Applying orchestration fixes (%s)", focus)

        result = self.agent.invoke({
            "input": f"""Fix wiring gaps using the latest report.

Report: {report_path}
Focus: {focus}
Repository: {self.github_repo}

Steps:
1. Read the report and prioritize P0/P1 gaps.
2. Update frontend API calls to match backend routes.
3. Ensure backend routes are mounted and return expected payloads.
4. Update docker-compose.yml and .env.example for missing env vars.
5. Update docs that reference outdated wiring or endpoints.
6. Create a concise change summary and list of files touched.
""",
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task."""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Orchestration Fix agent."""
    print("🧩 Orchestration Fix Agent - Wiring Remediation")
    print("=" * 60)

    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = OrchestrationFixAgent()
    result = agent.fix_gaps()
    print(f"\n📋 Result: {result.get('output', result)}")


if __name__ == "__main__":
    main()
