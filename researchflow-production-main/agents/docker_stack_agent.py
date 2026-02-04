#!/usr/bin/env python3
"""
Docker Stack Launch Agent - Web Stack Readiness & Verification

This agent validates Docker Compose wiring for the web stack and ensures
the ResearchFlow UI can launch and reach backend services.
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


DOCKER_STACK_CONFIG = {
    "name": "Docker Stack Launch Agent",
    "model": os.getenv("DOCKER_STACK_MODEL", "gpt-4o"),
    "temperature": _get_float_env("DOCKER_STACK_TEMPERATURE", 0),
    "toolkits": ["DOCKER", "GITHUB"],
    "actions": [
        Action.DOCKER_LIST_CONTAINERS,
        Action.DOCKER_INSPECT_CONTAINER,
        Action.DOCKER_GET_CONTAINER_LOGS,
        Action.DOCKER_LIST_IMAGES,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
        Action.GITHUB_CREATE_AN_ISSUE,
    ],
    "system_prompt": """You are the Docker Stack Launch Agent for ResearchFlow.

Your responsibilities:
1. Validate docker-compose.yml wiring for web/orchestrator/worker/collab.
2. Ensure Vite build args and Nginx proxy config align with API URLs.
3. Verify health endpoints for web and orchestrator.
4. Provide a docker stack launch checklist with clear pass/fail steps.
5. Update docs or scripts to make launch steps reproducible.

Artifacts to check:
- docker-compose.yml
- services/web/Dockerfile
- services/web/nginx.conf
- docs/LOCAL_DEV.md
- docs/deployment/docker-guide.md
- .env.example

Rules:
- Prefer adding a verification script when gaps are found.
- Record missing env vars and default values.
- If containers are running, inspect health and logs for errors.
""",
}


class DockerStackAgent:
    """Agent to validate Docker stack wiring and web launch readiness."""

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
            model=DOCKER_STACK_CONFIG["model"],
            temperature=DOCKER_STACK_CONFIG["temperature"],
            api_key=self.openai_api_key,
        )

        self.tools = self.toolset.get_tools(actions=DOCKER_STACK_CONFIG["actions"])
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        prompt = ChatPromptTemplate.from_messages([
            ("system", DOCKER_STACK_CONFIG["system_prompt"]),
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

    def verify_stack(self, checklist_path: str = "docs/operations/docker-stack-launch.md") -> Dict[str, Any]:
        """Verify docker stack launch readiness and update checklist."""
        logger.info("Verifying Docker stack launch readiness")

        result = self.agent.invoke({
            "input": f"""Verify Docker stack launch readiness.

Repository: {self.github_repo}
Checklist output: {checklist_path}

Steps:
1. Review docker-compose.yml for web/orchestrator/worker wiring and env vars.
2. Check Vite build args and Nginx proxy settings for /api routing.
3. Produce a launch checklist with health checks for:
   - web (/health)
   - orchestrator (/health)
   - worker (/health)
   - collab (/health)
4. If any wiring gaps are found, update docs or add a verification script.
5. Save/update {checklist_path}.
""",
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task."""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Docker Stack Launch agent."""
    print("🐳 Docker Stack Launch Agent - Web Launch Readiness")
    print("=" * 60)

    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = DockerStackAgent()
    result = agent.verify_stack()
    print(f"\n📋 Result: {result.get('output', result)}")


if __name__ == "__main__":
    main()
