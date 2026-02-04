#!/usr/bin/env python3
"""
Wiring Audit Agent - Documentation ↔ Code ↔ Runtime Alignment

This agent reviews documentation and code to identify what is wired end-to-end,
and where gaps exist between frontend, backend, and Docker runtime.
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


# Wiring Audit Agent Configuration
WIRING_AUDIT_CONFIG = {
    "name": "Wiring Audit Agent",
    "model": os.getenv("WIRING_AUDIT_MODEL", "gpt-4o-mini"),
    "temperature": _get_float_env("WIRING_AUDIT_TEMPERATURE", 0),
    "toolkits": ["GITHUB"],
    "actions": [
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
        Action.GITHUB_CREATE_AN_ISSUE,
        Action.GITHUB_CREATE_A_PULL_REQUEST,
    ],
    "system_prompt": """You are the Wiring Audit Agent for ResearchFlow.

Your responsibilities:
1. Review documentation and code to determine what is wired end-to-end.
2. Identify gaps between docs, backend routes, frontend API calls, and Docker runtime.
3. Produce a clear wiring report with severity and recommended fixes.
4. Update wiring docs when they are stale or inaccurate.

Primary sources to review:
- docs/audit/WIRING_TRUTH_TABLE.md
- docs/audit/GAP_MATRIX.md
- docs/MANUSCRIPT_STUDIO_WIRING_AUDIT.md
- docs/UI_WIRING_GUIDE.md
- docs/ROUTE_MOUNTING_GUIDE.md
- docs/DOCKER_EXTRACTION_WIRING.md
- docker-compose.yml
- services/orchestrator/src/index.ts
- services/orchestrator/src/routes/**
- services/web/src/**

Output format for reports:
1. Wired (✅): feature/component, doc, code path, runtime
2. Gaps (⚠️/❌): missing routes, env vars, mismatched endpoints, docs out of date
3. Fix plan: file-level edits and order of operations
4. Docker launch readiness checklist (web + orchestrator + worker)

Rules:
- Cite file paths and endpoints for every claim.
- Do not invent routes or env vars.
- If evidence is missing, mark as UNKNOWN and recommend verification.
""",
}


class WiringAuditAgent:
    """Agent to audit documentation-to-runtime wiring."""

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
            model=WIRING_AUDIT_CONFIG["model"],
            temperature=WIRING_AUDIT_CONFIG["temperature"],
            api_key=self.openai_api_key,
        )

        self.tools = self.toolset.get_tools(actions=WIRING_AUDIT_CONFIG["actions"])
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages([
            ("system", WIRING_AUDIT_CONFIG["system_prompt"]),
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
            return_intermediate_steps=True,
        )

    def audit_wiring(
        self,
        report_path: str = "docs/audit/WIRING_STATUS_REPORT.md",
        scope: str = "full",
    ) -> Dict[str, Any]:
        """Audit wiring and produce/update a report."""
        logger.info("Running wiring audit (%s)", scope)

        result = self.agent.invoke({
            "input": f"""Audit documentation ↔ code ↔ runtime wiring.

Scope: {scope}
Repository: {self.github_repo}

Steps:
1. Read the core wiring docs (WIRING_TRUTH_TABLE, GAP_MATRIX, MANUSCRIPT_STUDIO_WIRING_AUDIT, UI_WIRING_GUIDE).
2. Verify backend route mounts in services/orchestrator/src/index.ts.
3. Verify frontend API calls in services/web/src (manuscripts, workflows, extraction).
4. Verify docker-compose.yml env vars and web proxy configuration.
5. Produce a report at {report_path} with:
   - Wired ✅ components
   - Gaps ⚠️/❌ with severity
   - Recommended fixes with file paths
   - Docker launch readiness checklist
6. If any doc is outdated, update it or add notes in the report.
""",
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task."""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Wiring Audit agent."""
    print("🧭 Wiring Audit Agent - Docs ↔ Code ↔ Runtime")
    print("=" * 60)

    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = WiringAuditAgent()
    result = agent.audit_wiring()
    print(f"\n📋 Result: {result.get('output', result)}")


if __name__ == "__main__":
    main()
