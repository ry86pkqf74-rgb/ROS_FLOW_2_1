"""
Orchestrator State Management

This module defines the shared state types for the governance orchestration graph,
including agent communication state, review tracking, and compliance status.

Linear Issues: ROS-30, ROS-103
"""

from typing import TypedDict, Literal, Annotated, List, Dict, Any, Optional
from operator import add
from dataclasses import dataclass, field
from datetime import datetime


class GovernanceState(TypedDict):
    """
    Shared state for the governance orchestration graph.

    Tracks task routing, agent outputs, review status, and compliance gates.
    """
    # Task Metadata
    task_id: str
    task_type: Literal["design", "spec", "compliance", "release"]
    task_description: str
    created_at: str
    created_by: str

    # Draft Content
    draft_output: str
    draft_metadata: Dict[str, Any]

    # Review Status
    review_status: Literal["pending", "approved", "rejected", "revising"]
    review_feedback: str
    reviewer_id: Optional[str]
    review_timestamp: Optional[str]

    # Compliance Gates
    faves_status: Literal["pass", "fail", "pending", "error"]
    faves_details: Dict[str, Any]
    faves_timestamp: Optional[str]

    # Agent Outputs
    agent_outputs: Dict[str, Dict[str, Any]]

    # Communication History
    messages: Annotated[List[Dict[str, str]], add]

    # Error Tracking
    errors: List[Dict[str, Any]]

    # Execution Metadata
    stage: str
    is_compliant: bool
    can_proceed: bool
    execution_metadata: Dict[str, Any]


@dataclass
class ReviewRequest:
    """Request for human review of an output."""
    task_id: str
    content: str
    reason: str
    priority: Literal["low", "medium", "high"] = "medium"
    deadline: Optional[str] = None
    required_expertise: List[str] = field(default_factory=list)


@dataclass
class ComplianceCheckResult:
    """Result of FAVES compliance check."""
    task_id: str
    passed: bool
    fidelity_score: float
    accessibility_score: float
    variability_score: float
    explainability_score: float
    safety_score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ReleaseApproval:
    """Release approval from governance gate."""
    task_id: str
    approved: bool
    approval_timestamp: str
    approved_by: str
    compliance_status: str
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """Message from an agent in the workflow."""
    sender: str
    content: str
    message_type: Literal["status", "error", "output", "question"] = "status"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


def create_initial_state(
    task_id: str,
    task_type: Literal["design", "spec", "compliance", "release"],
    task_description: str,
    created_by: str,
) -> GovernanceState:
    """
    Create an initial governance state.

    Args:
        task_id: Unique task identifier
        task_type: Type of governance task
        task_description: Description of the task
        created_by: User ID of task creator

    Returns:
        Initialized GovernanceState
    """
    return GovernanceState(
        task_id=task_id,
        task_type=task_type,
        task_description=task_description,
        created_at=datetime.utcnow().isoformat(),
        created_by=created_by,
        draft_output="",
        draft_metadata={},
        review_status="pending",
        review_feedback="",
        reviewer_id=None,
        review_timestamp=None,
        faves_status="pending",
        faves_details={},
        faves_timestamp=None,
        agent_outputs={},
        messages=[],
        errors=[],
        stage="initialize",
        is_compliant=False,
        can_proceed=False,
        execution_metadata={},
    )


def add_agent_output(
    state: GovernanceState,
    agent_name: str,
    output: Dict[str, Any],
) -> GovernanceState:
    """
    Add an agent's output to the state.

    Args:
        state: Current governance state
        agent_name: Name of the agent producing output
        output: Agent output dictionary

    Returns:
        Updated state with agent output
    """
    state["agent_outputs"][agent_name] = {
        **output,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return state


def add_message(
    state: GovernanceState,
    sender: str,
    content: str,
    message_type: str = "status",
) -> GovernanceState:
    """
    Add a message to the communication history.

    Args:
        state: Current governance state
        sender: Message sender identifier
        content: Message content
        message_type: Type of message (status, error, output, question)

    Returns:
        Updated state with new message
    """
    message = {
        "sender": sender,
        "content": content,
        "message_type": message_type,
        "timestamp": datetime.utcnow().isoformat(),
    }
    state["messages"].append(message)
    return state


def add_error(
    state: GovernanceState,
    agent: str,
    error_message: str,
    error_type: str = "unknown",
) -> GovernanceState:
    """
    Record an error in the state.

    Args:
        state: Current governance state
        agent: Agent where error occurred
        error_message: Error message
        error_type: Classification of error

    Returns:
        Updated state with error recorded
    """
    error = {
        "agent": agent,
        "message": error_message,
        "type": error_type,
        "timestamp": datetime.utcnow().isoformat(),
    }
    state["errors"].append(error)
    return state
