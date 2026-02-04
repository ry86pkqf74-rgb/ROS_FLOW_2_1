"""
Orchestrator Graph Nodes

This module implements all nodes in the governance orchestration graph,
including routers, task-specific agents, compliance checks, review gates,
and release guardians.

Linear Issues: ROS-30, ROS-103
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .state import (
    GovernanceState,
    add_message,
    add_error,
    ComplianceCheckResult,
)
from .callbacks import OrchestrationLogger, MetricsCollector

logger = logging.getLogger(__name__)


# Global instances for callbacks
_orchestration_logger = OrchestrationLogger()
_metrics_collector = MetricsCollector()


def get_logger() -> OrchestrationLogger:
    """Get the global orchestration logger."""
    return _orchestration_logger


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics_collector


def router_node(state: GovernanceState) -> GovernanceState:
    """
    Entry point node that classifies and routes tasks.

    Responsibilities:
    - Parse incoming task description
    - Extract task type and context
    - Initialize execution metadata
    - Log task entry

    Args:
        state: Governance state

    Returns:
        Updated state ready for task-specific processing
    """
    task_id = state["task_id"]
    logger.info(f"Router: Processing task {task_id} (type: {state['task_type']})")

    _orchestration_logger.log_node_entry("router", state)

    # Update execution metadata
    execution_metadata = state.get("execution_metadata", {})
    execution_metadata["router_timestamp"] = datetime.utcnow().isoformat()
    execution_metadata["router_processed"] = True
    state["execution_metadata"] = execution_metadata

    # Log task initiation
    state = add_message(
        state,
        "router",
        f"Task {task_id} classified as {state['task_type']}",
        "status",
    )

    state["stage"] = "routed"
    return state


def design_ops_node(state: GovernanceState) -> GovernanceState:
    """
    Design Operations Agent Node.

    Responsibilities:
    - Generate design specifications
    - Create design documents
    - Define design patterns and architecture
    - Populate draft output

    Args:
        state: Governance state

    Returns:
        Updated state with design output
    """
    task_id = state["task_id"]
    logger.info(f"DesignOps: Processing design task {task_id}")

    _orchestration_logger.log_node_entry("design_ops", state)

    try:
        # Simulate design operations (in production, call actual design agent)
        design_output = {
            "design_specs": f"Design specifications for {task_id}",
            "patterns": ["pattern_1", "pattern_2"],
            "architecture": "multi_layer_architecture",
        }

        state["draft_output"] = design_output.get("design_specs", "")
        state["draft_metadata"] = design_output
        state["agent_outputs"]["design_ops"] = design_output

        state = add_message(
            state,
            "design_ops",
            f"Design specifications created for task {task_id}",
            "output",
        )

        state["stage"] = "design_completed"
        _orchestration_logger.log_agent_output("design_ops", task_id, design_output)

    except Exception as e:
        logger.error(f"DesignOps error for task {task_id}: {str(e)}")
        state = add_error(state, "design_ops", str(e), "design_error")
        state["stage"] = "design_error"

    _orchestration_logger.log_node_exit("design_ops", state, "compliance_check")
    return state


def spec_ops_node(state: GovernanceState) -> GovernanceState:
    """
    Specification Operations Agent Node.

    Responsibilities:
    - Generate technical specifications
    - Create requirement documents
    - Define acceptance criteria
    - Document specifications

    Args:
        state: Governance state

    Returns:
        Updated state with specification output
    """
    task_id = state["task_id"]
    logger.info(f"SpecOps: Processing specification task {task_id}")

    _orchestration_logger.log_node_entry("spec_ops", state)

    try:
        # Simulate spec operations (in production, call actual spec agent)
        spec_output = {
            "requirements": [
                "req_1: Performance requirement",
                "req_2: Compliance requirement",
            ],
            "acceptance_criteria": [
                "criterion_1: Response time < 100ms",
                "criterion_2: 99.9% uptime SLA",
            ],
            "version": "1.0",
        }

        state["draft_output"] = "Technical specifications document"
        state["draft_metadata"] = spec_output
        state["agent_outputs"]["spec_ops"] = spec_output

        state = add_message(
            state,
            "spec_ops",
            f"Technical specifications created for task {task_id}",
            "output",
        )

        state["stage"] = "spec_completed"
        _orchestration_logger.log_agent_output("spec_ops", task_id, spec_output)

    except Exception as e:
        logger.error(f"SpecOps error for task {task_id}: {str(e)}")
        state = add_error(state, "spec_ops", str(e), "spec_error")
        state["stage"] = "spec_error"

    _orchestration_logger.log_node_exit("spec_ops", state, "compliance_check")
    return state


def compliance_node(state: GovernanceState) -> GovernanceState:
    """
    Compliance Check Node - FAVES Gate.

    Evaluates output against FAVES criteria:
    - Fidelity: Accuracy and correctness
    - Accessibility: Usability and clarity
    - Variability: Handling of edge cases
    - Explainability: Documentation and justification
    - Safety: Security and risk mitigation

    Args:
        state: Governance state with draft output

    Returns:
        Updated state with compliance results
    """
    task_id = state["task_id"]
    logger.info(f"Compliance: Checking task {task_id}")

    _orchestration_logger.log_node_entry("compliance_check", state)

    try:
        # Simulate FAVES compliance check
        fidelity_score = 0.92
        accessibility_score = 0.85
        variability_score = 0.88
        explainability_score = 0.90
        safety_score = 0.95

        scores = {
            "fidelity": fidelity_score,
            "accessibility": accessibility_score,
            "variability": variability_score,
            "explainability": explainability_score,
            "safety": safety_score,
        }

        # Determine pass/fail (all scores must be >= 0.80)
        passed = all(score >= 0.80 for score in scores.values())
        faves_status = "pass" if passed else "fail"

        # Build compliance result
        result = ComplianceCheckResult(
            task_id=task_id,
            passed=passed,
            fidelity_score=fidelity_score,
            accessibility_score=accessibility_score,
            variability_score=variability_score,
            explainability_score=explainability_score,
            safety_score=safety_score,
            issues=[
                "Minor accessibility concern in section 3",
            ] if not passed else [],
            recommendations=[
                "Consider additional documentation for edge cases",
            ],
        )

        state["faves_status"] = faves_status
        state["faves_details"] = scores
        state["faves_timestamp"] = datetime.utcnow().isoformat()
        state["is_compliant"] = passed

        state = add_message(
            state,
            "compliance_check",
            f"FAVES check {'passed' if passed else 'failed'} - "
            f"Avg score: {sum(scores.values()) / len(scores):.2f}",
            "status",
        )

        state["stage"] = "compliance_checked"
        _orchestration_logger.log_compliance_check(
            task_id, faves_status, scores, passed
        )

    except Exception as e:
        logger.error(f"Compliance check error for task {task_id}: {str(e)}")
        state = add_error(state, "compliance_check", str(e), "compliance_error")
        state["faves_status"] = "error"
        state["stage"] = "compliance_error"

    _orchestration_logger.log_node_exit(
        "compliance_check", state, "next_node_depends_on_faves"
    )
    return state


def human_review_node(state: GovernanceState) -> GovernanceState:
    """
    Human Review Gate Node.

    Responsibilities:
    - Flag output for human review
    - Collect reviewer feedback
    - Support revision cycles
    - Escalate complex issues

    Args:
        state: Governance state with flagged output

    Returns:
        Updated state with review decision
    """
    task_id = state["task_id"]
    logger.info(f"HumanReview: Reviewing task {task_id}")

    _orchestration_logger.log_node_entry("human_review", state)

    try:
        # Simulate human review request
        review_feedback = (
            "Output requires minor revisions. "
            "Please address accessibility concerns in section 3."
        )

        state["review_status"] = "approved"  # Simulated approval
        state["review_feedback"] = review_feedback
        state["reviewer_id"] = "reviewer_001"
        state["review_timestamp"] = datetime.utcnow().isoformat()

        state = add_message(
            state,
            "human_review",
            f"Human review completed: {review_feedback}",
            "status",
        )

        state["stage"] = "review_completed"
        _orchestration_logger.log_review_request(
            task_id,
            "Output requires compliance verification",
            "high",
            ["compliance", "design"],
        )

    except Exception as e:
        logger.error(f"Review error for task {task_id}: {str(e)}")
        state = add_error(state, "human_review", str(e), "review_error")
        state["stage"] = "review_error"

    _orchestration_logger.log_node_exit("human_review", state, "next_depends_on_approval")
    return state


def release_guardian_node(state: GovernanceState) -> GovernanceState:
    """
    Release Guardian Node - Final Governance Gate.

    Responsibilities:
    - Final compliance verification
    - Risk assessment
    - Conditional approval with requirements
    - Release authorization

    Args:
        state: Governance state with compliance and review

    Returns:
        Updated state with release decision
    """
    task_id = state["task_id"]
    logger.info(f"ReleaseGuardian: Authorizing task {task_id}")

    _orchestration_logger.log_node_entry("release_guardian", state)

    try:
        # Assess release readiness
        is_compliant = state.get("is_compliant", False)
        review_approved = state.get("review_status") == "approved"
        faves_passed = state.get("faves_status") == "pass"

        can_release = is_compliant and review_approved
        release_decision = "approved" if can_release else "blocked"

        # Build risk assessment
        risk_assessment = {
            "compliance_status": "compliant" if is_compliant else "non_compliant",
            "review_status": "approved" if review_approved else "pending",
            "faves_passed": faves_passed,
            "risk_level": "low" if can_release else "high",
        }

        # Add execution metadata
        execution_metadata = state.get("execution_metadata", {})
        execution_metadata["release_decision"] = release_decision
        execution_metadata["release_timestamp"] = datetime.utcnow().isoformat()
        execution_metadata["risk_assessment"] = risk_assessment
        state["execution_metadata"] = execution_metadata

        state["can_proceed"] = can_release

        decision_msg = f"Release {'authorized' if can_release else 'blocked'} - {release_decision}"
        state = add_message(
            state,
            "release_guardian",
            decision_msg,
            "status",
        )

        state["stage"] = "release_decision_made"

        logger.info(f"Release Guardian: Task {task_id} {release_decision.upper()}")

    except Exception as e:
        logger.error(f"Release guardian error for task {task_id}: {str(e)}")
        state = add_error(state, "release_guardian", str(e), "release_error")
        state["stage"] = "release_error"
        state["can_proceed"] = False

    _orchestration_logger.log_node_exit("release_guardian", state, "END")
    _metrics_collector.record_task_completion(
        task_id,
        state["can_proceed"],
        1.0,  # Simulated processing time
    )

    return state
