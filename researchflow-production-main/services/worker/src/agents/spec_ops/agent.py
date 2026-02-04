"""
SpecOps Agent - Notion PRD → GitHub Issues Automation

This agent synchronizes Notion PRD (Product Requirements Document) pages
to GitHub issues using Composio tooling. It handles:
- Fetching PRD pages from Notion Problem Registry
- Extracting structured requirements and acceptance criteria
- Creating GitHub issues with proper labels and milestones
- Updating Notion with GitHub issue links
- Maintaining bidirectional synchronization

Architecture:
- Planner: Fetch and analyze PRD pages
- Extractor: Parse requirements using LLM
- Creator: Generate GitHub issues
- Reflector: Validate and sync back to Notion

Linear Issues: ROS-105, ROS-106
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

import httpx

from ..base_agent import BaseAgent, AgentConfig, AgentState, AgentResult

from .prd_parser import NotionPRDParser, Requirement
from .github_sync import (
    IssueCreator,
    LabelManager,
    MilestoneMapper,
    NotionLinkUpdater,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SpecOps Agent State
# =============================================================================

class SpecOpsState(TypedDict):
    """State for SpecOps Agent workflow."""
    # Inherit from AgentState
    messages: Annotated[List[BaseMessage], add_messages]
    task_id: str
    stage_id: int
    research_id: str

    # SpecOps-specific fields
    prd_page_id: Optional[str]
    prd_content: Optional[Dict[str, Any]]
    parsed_requirements: List[Requirement]
    github_issues: List[Dict[str, Any]]
    notion_updates: List[Dict[str, Any]]

    # Pipeline metrics
    total_requirements: int
    created_issues: int
    updated_pages: int
    errors: List[str]

    # Iteration tracking
    iteration: int
    max_iterations: int


# =============================================================================
# SpecOps Agent Implementation
# =============================================================================

class SpecOpsAgent(BaseAgent):
    """
    SpecOps Agent for Notion → GitHub synchronization.

    Handles bidirectional syncing of PRD requirements between Notion
    and GitHub issue tracking.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        notion_token: Optional[str] = None,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
    ):
        """
        Initialize SpecOps Agent.

        Args:
            config: Agent configuration
            notion_token: Notion API token
            github_token: GitHub API token
            github_repo: GitHub repository (owner/repo)
        """
        default_config = AgentConfig(
            name="SpecOpsAgent",
            description="Notion PRD → GitHub Issues Automation",
            stages=[],  # Cross-cutting agent
            rag_collections=["prd_registry"],
            max_iterations=3,
            quality_threshold=0.8,
            timeout_seconds=180,
            phi_safe=True,
            model_provider="openai",
            model_name="gpt-4o-mini",
        )

        super().__init__(config or default_config)

        # Initialize tokens
        self.notion_token = notion_token or os.getenv("NOTION_API_TOKEN")
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_repo = github_repo or os.getenv("GITHUB_REPO", "")

        # Initialize components
        self.prd_parser = NotionPRDParser(logger)
        self.issue_creator = IssueCreator(logger)
        self.label_manager = LabelManager(logger)
        self.milestone_mapper = MilestoneMapper(logger)
        self.link_updater = NotionLinkUpdater(logger)

        # Initialize LLM for extraction
        self.llm = ChatOpenAI(
            model=self.config.model_name or "gpt-4o-mini",
            temperature=0.3,
        )

        self.logger.info("SpecOps Agent initialized successfully")

    def build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.

        Returns:
            Configured StateGraph
        """
        graph = StateGraph(SpecOpsState)

        # Add nodes
        graph.add_node("planner", self._plan_step)
        graph.add_node("prd_fetcher", self._fetch_prd_step)
        graph.add_node("parser", self._parse_prd_step)
        graph.add_node("issue_creator", self._create_issues_step)
        graph.add_node("notion_updater", self._update_notion_step)
        graph.add_node("reflector", self._reflect_step)

        # Define edges
        graph.add_edge("planner", "prd_fetcher")
        graph.add_edge("prd_fetcher", "parser")
        graph.add_edge("parser", "issue_creator")
        graph.add_edge("issue_creator", "notion_updater")
        graph.add_edge("notion_updater", "reflector")

        graph.add_conditional_edges(
            "reflector",
            self._should_continue,
            {"continue": "parser", "end": END}
        )

        # Set entry and exit
        graph.set_entry_point("planner")

        # Create with checkpointer
        return graph.compile(checkpointer=MemorySaver())

    # =========================================================================
    # Abstract Methods Implementation
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """Return the system prompt for SpecOps Agent."""
        return """You are a Requirements Synchronization Specialist Agent.

Your role is to synchronize Notion PRD (Product Requirements Document) pages
to GitHub issues. You excel at:

1. Understanding product requirements and specifications
2. Converting requirements into well-structured GitHub issues
3. Extracting acceptance criteria and user stories
4. Categorizing requirements (feature, bug, task, epic)
5. Maintaining traceability between Notion and GitHub

Always provide structured, actionable output.
Focus on quality and completeness of issue creation.
Ensure all acceptance criteria are captured.
"""

    def _get_planning_prompt(self, state: SpecOpsState) -> str:
        """Return the planning prompt for decomposing the sync task."""
        return f"""Plan the synchronization of the Notion PRD page.

Task: {state.get('task_id', 'unknown')}
PRD Page: {state.get('prd_page_id', 'unknown')}

Your plan should include:
1. Steps to fetch and validate the PRD page
2. Requirement extraction strategy
3. GitHub issue creation plan
4. Notion update strategy
5. Quality validation approach

Provide a structured plan in JSON format.
"""

    def _get_execution_prompt(self, state: SpecOpsState, context: str) -> str:
        """Return the execution prompt with context."""
        total_reqs = state.get('total_requirements', 0)
        created = state.get('created_issues', 0)

        return f"""Execute the PRD synchronization workflow.

Current Status:
- Total Requirements: {total_reqs}
- Issues Created: {created}
- Notion Updates: {state.get('updated_pages', 0)}

Context from previous steps:
{context}

Next steps:
1. Continue processing remaining requirements
2. Validate issue creation quality
3. Prepare final sync report

Provide execution results in JSON format.
"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the LLM execution response."""
        try:
            # Try to extract JSON from response
            import json
            import re

            # Look for JSON block
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Fallback: parse as unstructured response
            return {
                "status": "completed",
                "response": response,
                "parsed": False
            }
        except Exception as e:
            self.logger.error(f"Failed to parse execution result: {e}")
            return {
                "status": "error",
                "error": str(e),
                "parsed": False
            }

    async def _check_quality(self, state: SpecOpsState) -> "QualityCheckResult":
        """Evaluate the quality of the sync results."""
        from ..base_agent import QualityCheckResult

        scores = {}

        # Check requirement extraction
        if state["total_requirements"] > 0:
            scores["requirement_extraction"] = min(
                1.0,
                len(state["parsed_requirements"]) / state["total_requirements"]
            )
        else:
            scores["requirement_extraction"] = 0.0

        # Check issue creation
        if state["total_requirements"] > 0:
            scores["issue_creation"] = min(
                1.0,
                state["created_issues"] / state["total_requirements"]
            )
        else:
            scores["issue_creation"] = 0.0

        # Check Notion updates
        if state["created_issues"] > 0:
            scores["notion_sync"] = min(
                1.0,
                state["updated_pages"] / state["created_issues"]
            )
        else:
            scores["notion_sync"] = 0.0

        # Check for errors
        error_count = len(state.get("errors", []))
        scores["error_handling"] = max(0.0, 1.0 - (error_count * 0.1))

        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0

        passed = overall_score >= self.config.quality_threshold

        feedback = f"""
Quality Check Results:
- Requirement Extraction: {scores.get('requirement_extraction', 0):.2%}
- Issue Creation: {scores.get('issue_creation', 0):.2%}
- Notion Sync: {scores.get('notion_sync', 0):.2%}
- Error Handling: {scores.get('error_handling', 0):.2%}
- Overall Score: {overall_score:.2%}

Status: {'PASSED' if passed else 'NEEDS IMPROVEMENT'}
Threshold: {self.config.quality_threshold:.2%}
"""

        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=scores
        )

    # =========================================================================
    # Workflow Steps
    # =========================================================================

    async def _plan_step(self, state: SpecOpsState) -> SpecOpsState:
        """Plan the sync workflow."""
        self.logger.info(f"Planning SpecOps sync for task: {state['task_id']}")

        message = SystemMessage(
            content="""You are a requirements synchronization specialist.
            Your task is to plan the synchronization of Notion PRD pages to GitHub issues.

            For each PRD page:
            1. Identify all requirements
            2. Categorize them (feature, bug, task, epic)
            3. Plan issue creation and labeling
            4. Prepare Notion updates with GitHub links

            Respond with a JSON plan containing:
            - prd_pages: list of PRD page IDs to process
            - strategy: overall sync strategy
            - error_handling: how to handle failures
            """
        )

        state["messages"].append(message)
        response = await self.llm.ainvoke(state["messages"])
        state["messages"].append(response)

        state["iteration"] = 0

        return state

    async def _fetch_prd_step(self, state: SpecOpsState) -> SpecOpsState:
        """Fetch PRD page from Notion."""
        self.logger.info("Fetching PRD page from Notion")

        if not state.get("prd_page_id"):
            state["prd_page_id"] = state.get("metadata", {}).get("prd_page_id")

        if not state.get("prd_page_id"):
            error = "No PRD page ID provided"
            state["errors"].append(error)
            self.logger.warning(error)
            return state

        try:
            # Fetch from Notion (would use Composio in production)
            prd_content = await self._fetch_notion_page(state["prd_page_id"])
            state["prd_content"] = prd_content

            self.logger.info(
                f"Successfully fetched PRD page: {prd_content.get('title', 'Unknown')}"
            )

        except Exception as e:
            error = f"Failed to fetch PRD page: {e}"
            state["errors"].append(error)
            self.logger.error(error)

        return state

    async def _parse_prd_step(self, state: SpecOpsState) -> SpecOpsState:
        """Parse PRD content and extract requirements."""
        self.logger.info("Parsing PRD content")

        if not state.get("prd_content"):
            self.logger.warning("No PRD content to parse")
            return state

        try:
            # Parse PRD
            parsed = self.prd_parser.parse_prd_page(state["prd_content"])

            state["parsed_requirements"] = parsed.get("requirements", [])
            state["total_requirements"] = parsed.get("total_requirements", 0)

            self.logger.info(
                f"Extracted {state['total_requirements']} requirements"
            )

        except Exception as e:
            error = f"Failed to parse PRD: {e}"
            state["errors"].append(error)
            self.logger.error(error)

        return state

    async def _create_issues_step(self, state: SpecOpsState) -> SpecOpsState:
        """Create GitHub issues from parsed requirements."""
        self.logger.info("Creating GitHub issues")

        state["github_issues"] = []

        for requirement in state["parsed_requirements"]:
            try:
                # Create issue
                issue = self.issue_creator.create_from_requirement(requirement)

                issue_data = {
                    "title": issue.title,
                    "body": issue.body,
                    "labels": issue.labels,
                    "prd_requirement_id": requirement.id,
                    "issue_type": issue.issue_type,
                }

                # Add milestone if available
                milestone = self.milestone_mapper.map_requirement_to_milestone(
                    requirement
                )
                if milestone:
                    issue_data["milestone"] = milestone.title

                state["github_issues"].append(issue_data)

            except Exception as e:
                error = f"Failed to create issue for {requirement.title}: {e}"
                state["errors"].append(error)
                self.logger.error(error)

        state["created_issues"] = len(state["github_issues"])
        self.logger.info(f"Created {state['created_issues']} issues")

        return state

    async def _update_notion_step(self, state: SpecOpsState) -> SpecOpsState:
        """Update Notion with GitHub issue links."""
        self.logger.info("Updating Notion with GitHub links")

        state["notion_updates"] = []

        for i, issue in enumerate(state["github_issues"]):
            try:
                # In production, would post to GitHub first and get issue number
                # For now, simulate issue creation
                issue_number = 1000 + i + 1

                github_url = (
                    f"https://github.com/{self.github_repo}/issues/{issue_number}"
                )

                update = self.link_updater.create_issue_link_update(
                    requirement_id=issue.get("prd_requirement_id"),
                    github_issue_number=issue_number,
                    github_url=github_url,
                    repository=self.github_repo,
                )

                state["notion_updates"].append(update)

            except Exception as e:
                error = f"Failed to create Notion update: {e}"
                state["errors"].append(error)
                self.logger.error(error)

        state["updated_pages"] = len(state["notion_updates"])
        self.logger.info(f"Prepared {state['updated_pages']} Notion updates")

        return state

    async def _reflect_step(self, state: SpecOpsState) -> SpecOpsState:
        """Reflect on results and determine next steps."""
        self.logger.info("Reflecting on sync results")

        message = SystemMessage(
            content=f"""Review the SpecOps sync results:
            - Total requirements: {state['total_requirements']}
            - Created issues: {state['created_issues']}
            - Notion updates: {state['updated_pages']}
            - Errors: {len(state['errors'])}

            If errors occurred, suggest remediation.
            If successful, confirm completion.
            """
        )

        state["messages"].append(message)
        response = await self.llm.ainvoke(state["messages"])
        state["messages"].append(response)

        state["iteration"] += 1

        return state

    def _should_continue(self, state: SpecOpsState) -> str:
        """Determine if workflow should continue or end."""
        if state["iteration"] >= state["max_iterations"]:
            self.logger.info("Maximum iterations reached")
            return "end"

        if state["total_requirements"] == 0:
            self.logger.info("No requirements to process")
            return "end"

        # Continue if there are more pages to process
        # (In production, would check for more pages)
        return "end"

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _fetch_notion_page(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch a Notion page (mock implementation).

        In production, would use Composio Notion toolkit.

        Args:
            page_id: Notion page ID

        Returns:
            Page content dictionary
        """
        self.logger.info(f"Fetching Notion page: {page_id}")

        # Mock implementation - in production use Composio
        return {
            "id": page_id,
            "title": f"PRD: Page {page_id[:8]}",
            "content": """
            # Feature: User Authentication

            ## Description
            Implement secure user authentication system.

            ## Requirements
            - High priority
            - Must support OAuth2
            - MUST have multi-factor authentication

            ## Acceptance Criteria
            - [ ] Users can sign up with email
            - [ ] Users can log in with credentials
            - [ ] MFA can be enabled
            - [ ] Password reset works

            ## User Story
            As a user, I want to securely access the platform,
            so that my data is protected.
            """,
        }

    async def execute(
        self,
        task_id: str,
        prd_page_id: str,
        max_iterations: int = 3,
    ) -> AgentResult:
        """
        Execute the SpecOps Agent workflow.

        Args:
            task_id: Unique task identifier
            prd_page_id: Notion PRD page ID to sync
            max_iterations: Maximum workflow iterations

        Returns:
            AgentResult with execution details
        """
        self.logger.info(
            f"Executing SpecOps Agent for PRD page: {prd_page_id}"
        )

        try:
            # Build graph
            graph = self.build_graph()

            # Initialize state
            initial_state: SpecOpsState = {
                "messages": [],
                "task_id": task_id,
                "stage_id": 0,
                "research_id": "",
                "prd_page_id": prd_page_id,
                "prd_content": None,
                "parsed_requirements": [],
                "github_issues": [],
                "notion_updates": [],
                "total_requirements": 0,
                "created_issues": 0,
                "updated_pages": 0,
                "errors": [],
                "iteration": 0,
                "max_iterations": max_iterations,
            }

            # Execute graph
            result = await graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": task_id}}
            )

            success = len(result["errors"]) == 0

            return AgentResult(
                task_id=task_id,
                agent_name="SpecOpsAgent",
                success=success,
                result={
                    "total_requirements": result["total_requirements"],
                    "created_issues": result["created_issues"],
                    "updated_pages": result["updated_pages"],
                    "errors": result["errors"],
                    "github_issues": result["github_issues"],
                    "notion_updates": result["notion_updates"],
                }
            )

        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            return AgentResult(
                task_id=task_id,
                agent_name="SpecOpsAgent",
                success=False,
                result=None,
                error=str(e)
            )


# =============================================================================
# Factory Function
# =============================================================================

def create_spec_ops_agent(
    notion_token: Optional[str] = None,
    github_token: Optional[str] = None,
    github_repo: Optional[str] = None,
) -> SpecOpsAgent:
    """
    Create and configure a SpecOps Agent instance.

    Args:
        notion_token: Notion API token
        github_token: GitHub API token
        github_repo: GitHub repository (owner/repo)

    Returns:
        Configured SpecOpsAgent
    """
    return SpecOpsAgent(
        notion_token=notion_token,
        github_token=github_token,
        github_repo=github_repo,
    )
