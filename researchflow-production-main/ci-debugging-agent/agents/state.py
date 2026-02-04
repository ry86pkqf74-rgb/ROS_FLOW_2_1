"""
CI Debugging Agent State Management
Defines the shared state structure used by all agents in the system.
"""
from typing import Annotated, Literal, TypedDict, Optional
from pydantic import BaseModel, Field
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class BugReport(BaseModel):
    """Represents a single bug or issue found during analysis."""
    id: str = Field(description="Unique identifier for the bug")
    category: Literal[
        "typescript_error",
        "docker_issue",
        "frontend_bug",
        "api_error",
        "security_vulnerability",
        "dependency_issue",
        "configuration_error",
        "performance_issue"
    ] = Field(description="Category of the bug")
    severity: Literal["critical", "high", "medium", "low"] = Field(description="Severity level")
    title: str = Field(description="Short title describing the bug")
    description: str = Field(description="Detailed description of the bug")
    file_path: Optional[str] = Field(default=None, description="File path where the bug was found")
    line_number: Optional[int] = Field(default=None, description="Line number if applicable")
    suggested_fix: Optional[str] = Field(default=None, description="Suggested code fix")
    root_cause: Optional[str] = Field(default=None, description="Root cause analysis")
    related_issues: list[str] = Field(default_factory=list, description="Related issue IDs")


class FixAttempt(BaseModel):
    """Represents an attempted fix for a bug."""
    bug_id: str = Field(description="ID of the bug being fixed")
    fix_type: Literal["code_change", "config_change", "dependency_update", "manual_action"] = Field(
        description="Type of fix applied"
    )
    changes: list[dict] = Field(description="List of changes made")
    status: Literal["pending", "applied", "verified", "failed"] = Field(description="Status of the fix")
    pr_url: Optional[str] = Field(default=None, description="URL of the PR if created")
    issue_url: Optional[str] = Field(default=None, description="URL of the GitHub issue if created")


class AnalysisPhase(BaseModel):
    """Represents a completed analysis phase."""
    phase_name: str = Field(description="Name of the analysis phase")
    agent_name: str = Field(description="Name of the agent that performed the analysis")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(description="Phase status")
    findings_count: int = Field(default=0, description="Number of issues found")
    summary: str = Field(default="", description="Summary of findings")


class CIDebugState(TypedDict):
    """
    Shared state for the CI Debugging Agent system.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    repo_owner: str
    repo_name: str
    target_branch: str
    commit_sha: Optional[str]
    bugs: list[BugReport]
    fix_attempts: list[FixAttempt]
    analysis_phases: list[AnalysisPhase]
    current_phase: str
    next_agent: Optional[str]
    should_continue: bool
    ci_run_id: Optional[str]
    ci_logs: Optional[str]
    workflow_status: Optional[str]
    final_report: Optional[str]


def create_initial_state(
    repo_owner: str,
    repo_name: str,
    target_branch: str = "main",
    commit_sha: Optional[str] = None,
    ci_run_id: Optional[str] = None
) -> CIDebugState:
    """Create an initial state for a new debugging session."""
    return CIDebugState(
        messages=[],
        repo_owner=repo_owner,
        repo_name=repo_name,
        target_branch=target_branch,
        commit_sha=commit_sha,
        bugs=[],
        fix_attempts=[],
        analysis_phases=[],
        current_phase="initialization",
        next_agent=None,
        should_continue=True,
        ci_run_id=ci_run_id,
        ci_logs=None,
        workflow_status=None,
        final_report=None
    )
