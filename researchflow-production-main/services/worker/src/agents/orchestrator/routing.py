"""
Orchestrator Routing Functions

This module contains the conditional routing logic for the governance orchestration
graph, directing tasks through appropriate agents based on task type, compliance
status, and review decisions.

Linear Issues: ROS-30, ROS-103
"""

import logging
from typing import Literal
from .state import GovernanceState

logger = logging.getLogger(__name__)


def route_by_task_type(state: GovernanceState) -> str:
    """
    Route task to appropriate agent based on task type.

    Routing Logic:
    - "design": Design operations agent
    - "spec": Specification operations agent
    - "compliance": Compliance check agent
    - "release": Release guardian agent

    Args:
        state: Current governance state

    Returns:
        Next node name (design_ops, spec_ops, compliance_check, or release_guardian)
    """
    task_type = state.get("task_type", "design")
    logger.info(f"Routing task {state['task_id']} by type: {task_type}")

    routing_map = {
        "design": "design_ops",
        "spec": "spec_ops",
        "compliance": "compliance_check",
        "release": "release_guardian",
    }

    next_node = routing_map.get(task_type, "design_ops")
    logger.debug(f"Task {state['task_id']} routed to {next_node}")

    return next_node


def route_by_faves_status(state: GovernanceState) -> str:
    """
    Route based on FAVES (Fidelity, Accessibility, Variability, Explainability, Safety)
    compliance check results.

    Routing Logic:
    - "pass": Proceed to release guardian for approval
    - "fail": Escalate to human review for remediation
    - "error": Route to human review with error details
    - "pending": Continue with compliance check (loop)

    Args:
        state: Current governance state with FAVES results

    Returns:
        Next node name (release_guardian, human_review, or compliance_check)

    Raises:
        ValueError: If FAVES status is invalid
    """
    faves_status = state.get("faves_status", "pending")
    task_id = state["task_id"]

    logger.info(f"Routing task {task_id} by FAVES status: {faves_status}")

    if faves_status == "pass":
        logger.info(f"Task {task_id} passed FAVES check, proceeding to release")
        return "release_guardian"

    elif faves_status == "fail":
        logger.warning(f"Task {task_id} failed FAVES check, escalating to review")
        return "human_review"

    elif faves_status == "error":
        logger.error(f"Task {task_id} FAVES check encountered error")
        return "human_review"

    elif faves_status == "pending":
        logger.debug(f"Task {task_id} FAVES check still pending")
        return "compliance_check"

    else:
        logger.error(f"Unknown FAVES status: {faves_status}")
        raise ValueError(f"Invalid FAVES status: {faves_status}")


def route_by_approval(state: GovernanceState) -> str:
    """
    Route based on human review approval decision.

    Routing Logic:
    - "approved": Proceed to release guardian for final approval
    - "rejected": End workflow, return to task creator for revision
    - "revising": Return to appropriate agent for revision
    - "pending": Continue with human review (loop)

    Args:
        state: Current governance state with review decision

    Returns:
        Next node name or END signal (release_guardian or END)

    Raises:
        ValueError: If review status is invalid
    """
    review_status = state.get("review_status", "pending")
    task_id = state["task_id"]

    logger.info(f"Routing task {task_id} by approval status: {review_status}")

    if review_status == "approved":
        logger.info(f"Task {task_id} approved by reviewer, proceeding to release")
        return "release_guardian"

    elif review_status == "rejected":
        logger.warning(f"Task {task_id} rejected by reviewer, ending workflow")
        return "END"

    elif review_status == "revising":
        logger.info(f"Task {task_id} requires revision, returning to design")
        # Route back to the original agent based on task type
        task_type = state.get("task_type", "design")
        routing_map = {
            "design": "design_ops",
            "spec": "spec_ops",
            "compliance": "compliance_check",
        }
        return routing_map.get(task_type, "design_ops")

    elif review_status == "pending":
        logger.debug(f"Task {task_id} review still pending")
        return "human_review"

    else:
        logger.error(f"Unknown review status: {review_status}")
        raise ValueError(f"Invalid review status: {review_status}")


def route_by_release_decision(state: GovernanceState) -> str:
    """
    Route based on release guardian approval decision.

    Routing Logic:
    - "approved": Workflow complete, proceed to END
    - "blocked": Escalate to stakeholder review
    - "conditional": Proceed with conditions attached
    - "pending": Continue with release guardian (loop)

    Args:
        state: Current governance state with release decision

    Returns:
        Next node name or END signal

    Raises:
        ValueError: If release decision is invalid
    """
    task_id = state["task_id"]
    execution_metadata = state.get("execution_metadata", {})
    release_decision = execution_metadata.get("release_decision", "pending")

    logger.info(f"Routing task {task_id} by release decision: {release_decision}")

    if release_decision == "approved":
        logger.info(f"Task {task_id} approved for release")
        return "END"

    elif release_decision == "blocked":
        logger.error(f"Task {task_id} blocked from release, requires stakeholder review")
        return "END"

    elif release_decision == "conditional":
        logger.info(f"Task {task_id} approved with conditions")
        return "END"

    elif release_decision == "pending":
        logger.debug(f"Task {task_id} release decision pending")
        return "release_guardian"

    else:
        logger.error(f"Unknown release decision: {release_decision}")
        raise ValueError(f"Invalid release decision: {release_decision}")


def should_escalate_to_stakeholder(state: GovernanceState) -> bool:
    """
    Determine if task should escalate to stakeholder review based on risk factors.

    Escalation triggers:
    - Critical compliance failures
    - High-risk design decisions
    - Multiple review cycles
    - Conflicting feedback

    Args:
        state: Current governance state

    Returns:
        True if escalation is recommended
    """
    task_id = state["task_id"]

    # Check for critical compliance failures
    faves_details = state.get("faves_details", {})
    critical_scores = [
        v for k, v in faves_details.items()
        if k.endswith("_score") and v < 0.3
    ]

    if critical_scores:
        logger.warning(f"Task {task_id} has critical compliance failures")
        return True

    # Check for multiple review cycles
    errors = state.get("errors", [])
    review_errors = [e for e in errors if e.get("type") == "review_conflict"]

    if len(review_errors) > 2:
        logger.warning(f"Task {task_id} has multiple review conflicts")
        return True

    # Check for high-risk flags in metadata
    execution_metadata = state.get("execution_metadata", {})
    if execution_metadata.get("high_risk_flag"):
        logger.warning(f"Task {task_id} marked as high-risk")
        return True

    return False


def get_next_agent(state: GovernanceState, current_agent: str) -> str:
    """
    Determine the next agent in the workflow sequence.

    Provides a routing mechanism for sequential agent execution if needed.

    Args:
        state: Current governance state
        current_agent: Current agent identifier

    Returns:
        Next agent identifier or END if workflow complete
    """
    task_type = state.get("task_type", "design")

    # Define agent sequence by task type
    sequences = {
        "design": ["design_ops", "compliance_check", "human_review", "release_guardian"],
        "spec": ["spec_ops", "compliance_check", "human_review", "release_guardian"],
        "compliance": ["compliance_check", "human_review", "release_guardian"],
        "release": ["release_guardian"],
    }

    agent_sequence = sequences.get(task_type, [])

    try:
        current_index = agent_sequence.index(current_agent)
        if current_index + 1 < len(agent_sequence):
            return agent_sequence[current_index + 1]
        else:
            return "END"
    except ValueError:
        logger.error(f"Current agent {current_agent} not found in sequence")
        return "END"
