"""
Agent State Definitions

TypedDict classes for LangGraph agent state management.
These types mirror the TypeScript definitions in packages/core/src/types/agent.ts.

See: Linear ROS-64 (Phase A: Foundation)
"""

from typing import TypedDict, List, Optional, Literal, Annotated
from datetime import datetime
import operator


# Agent type literals matching the 5 phase-specific agents
AgentId = Literal['dataprep', 'analysis', 'quality', 'irb', 'manuscript']

# Gate status for quality checks
GateStatus = Literal['pending', 'passed', 'failed', 'needs_human']

# Governance mode
GovernanceMode = Literal['DEMO', 'LIVE', 'STANDBY']


class Message(TypedDict):
    """Chat message structure."""
    id: str
    role: Literal['system', 'user', 'assistant']
    content: str
    timestamp: str
    phi_detected: bool


class VersionSnapshot(TypedDict):
    """Snapshot of agent output for improvement loop tracking."""
    version_id: str
    timestamp: str
    output: str
    quality_score: float
    improvement_request: Optional[str]
    changes: List[str]


class QualityGateResult(TypedDict):
    """Result of quality gate evaluation."""
    passed: bool
    score: float
    criteria_met: List[str]
    criteria_failed: List[str]
    reason: str
    needs_human_review: bool


class AgentState(TypedDict):
    """
    Core state for all LangGraph agents.

    This state is passed through the graph nodes and persisted
    via Redis checkpointing for conversation continuity.
    """
    # Identity
    agent_id: AgentId
    project_id: str
    run_id: str
    thread_id: str  # For checkpointing

    # Audit / tracing (optional; for later audit + tracing)
    trace_id: Optional[str]
    node_id: Optional[str]
    manuscript_id: Optional[str]
    branch_id: Optional[str]
    commit_id: Optional[str]

    # Workflow context
    current_stage: int
    stage_range: tuple[int, int]
    governance_mode: GovernanceMode

    # Messages (conversation history)
    # Using Annotated with operator.add for LangGraph message accumulation
    messages: Annotated[List[Message], operator.add]

    # Artifacts
    input_artifact_ids: List[str]
    output_artifact_ids: List[str]
    current_output: str

    # Iteration tracking for improvement loops
    iteration: int
    max_iterations: int

    # Version history for improvement loops
    previous_versions: List[VersionSnapshot]

    # Quality gate status
    gate_status: GateStatus
    gate_score: float
    gate_result: Optional[QualityGateResult]

    # Improvement loop
    improvement_enabled: bool
    feedback: Optional[str]

    # Metrics
    token_count: int
    tool_call_count: int
    start_time: str

    # Human-in-the-loop
    awaiting_approval: bool
    approval_request_id: Optional[str]
    edit_session_id: Optional[str]
    edit_session_attempt: Optional[int]
    edit_session_status: Optional[str]
    waiting_for_human_attempt: int
    edit_session_created_at: Optional[str]


class ImprovementState(TypedDict):
    """
    Extended state for improvement loop operations.

    Used when a user requests "improve this" on agent output.
    """
    # Reference to parent agent state
    agent_state_id: str
    artifact_id: str

    # Current improvement context
    current_version_id: str
    improvement_request: str

    # Diff tracking
    diff_summary: str
    changes_made: List[str]

    # Loop control
    loop_id: str
    loop_iteration: int
    max_loop_iterations: int
    loop_status: Literal['active', 'complete', 'reverted', 'max_reached']


class CheckpointMetadata(TypedDict):
    """Metadata stored with Redis checkpoints."""
    checkpoint_id: str
    thread_id: str
    agent_id: AgentId
    project_id: str
    created_at: str
    updated_at: str
    node_name: str
    iteration: int
    is_terminal: bool


def create_initial_state(
    agent_id: AgentId,
    project_id: str,
    run_id: str,
    thread_id: str,
    stage_range: tuple[int, int],
    governance_mode: GovernanceMode = 'DEMO',
    input_artifact_ids: Optional[List[str]] = None,
    max_iterations: int = 5,
) -> AgentState:
    """
    Factory function to create a properly initialized AgentState.

    Args:
        agent_id: The type of agent ('dataprep', 'analysis', etc.)
        project_id: The research project ID
        run_id: Unique ID for this agent run
        thread_id: Thread ID for checkpointing
        stage_range: Tuple of (start_stage, end_stage) this agent handles
        governance_mode: Current governance mode (DEMO/LIVE/STANDBY)
        input_artifact_ids: Optional list of input artifact IDs
        max_iterations: Maximum improvement iterations allowed

    Returns:
        Initialized AgentState dict
    """
    return AgentState(
        agent_id=agent_id,
        project_id=project_id,
        run_id=run_id,
        thread_id=thread_id,
        current_stage=stage_range[0],
        stage_range=stage_range,
        governance_mode=governance_mode,
        messages=[],
        input_artifact_ids=input_artifact_ids or [],
        output_artifact_ids=[],
        current_output='',
        iteration=0,
        max_iterations=max_iterations,
        previous_versions=[],
        gate_status='pending',
        gate_score=0.0,
        gate_result=None,
        improvement_enabled=True,
        feedback=None,
        token_count=0,
        tool_call_count=0,
        start_time=datetime.utcnow().isoformat(),
        awaiting_approval=False,
        approval_request_id=None,
        edit_session_id=None,
        edit_session_attempt=None,
        edit_session_status=None,
        waiting_for_human_attempt=0,
        edit_session_created_at=None,
        trace_id=None,
        node_id=None,
        manuscript_id=None,
        branch_id=None,
        commit_id=None,
    )
