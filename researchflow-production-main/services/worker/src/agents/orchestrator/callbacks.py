"""
Orchestrator Callbacks and Event Handlers

This module provides callback handlers for graph events including logging,
metrics collection, notifications, and error handling.

Linear Issues: ROS-30, ROS-103
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import asdict

logger = logging.getLogger(__name__)


class OrchestrationLogger:
    """Handles logging for orchestration graph events."""

    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize orchestration logger.

        Args:
            log_level: Python logging level
        """
        self.log_level = log_level
        self.event_log: List[Dict[str, Any]] = []

    def log_node_entry(self, node_name: str, state: Dict[str, Any]) -> None:
        """
        Log when a node is entered.

        Args:
            node_name: Name of the node being entered
            state: Current state at node entry
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "node_entry",
            "node_name": node_name,
            "task_id": state.get("task_id", "unknown"),
            "stage": state.get("stage", "unknown"),
        }
        self.event_log.append(event)
        logger.info(f"Entered node: {node_name} (Task: {state.get('task_id')})")

    def log_node_exit(
        self,
        node_name: str,
        state: Dict[str, Any],
        next_node: Optional[str] = None,
    ) -> None:
        """
        Log when a node is exited.

        Args:
            node_name: Name of the node being exited
            state: Current state at node exit
            next_node: Next node in the graph
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "node_exit",
            "node_name": node_name,
            "task_id": state.get("task_id", "unknown"),
            "next_node": next_node,
            "can_proceed": state.get("can_proceed", False),
        }
        self.event_log.append(event)
        logger.info(
            f"Exiting node: {node_name} -> {next_node} "
            f"(Task: {state.get('task_id')})"
        )

    def log_routing_decision(
        self,
        current_node: str,
        decision_type: str,
        decision_value: str,
        next_node: str,
        state: Dict[str, Any],
    ) -> None:
        """
        Log routing decisions made by conditional edges.

        Args:
            current_node: Node making the decision
            decision_type: Type of routing decision (task_type, faves_status, etc.)
            decision_value: Value that triggered the routing
            next_node: Resulting next node
            state: Current state
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "routing_decision",
            "current_node": current_node,
            "decision_type": decision_type,
            "decision_value": decision_value,
            "next_node": next_node,
            "task_id": state.get("task_id", "unknown"),
        }
        self.event_log.append(event)
        logger.debug(
            f"Routing: {current_node} -> {next_node} "
            f"({decision_type}={decision_value})"
        )

    def log_agent_output(
        self,
        agent_name: str,
        task_id: str,
        output: Dict[str, Any],
    ) -> None:
        """
        Log agent output.

        Args:
            agent_name: Name of the agent
            task_id: Task ID
            output: Agent output dictionary
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "agent_output",
            "agent_name": agent_name,
            "task_id": task_id,
            "output_keys": list(output.keys()),
        }
        self.event_log.append(event)
        logger.info(f"Agent {agent_name} produced output for task {task_id}")

    def log_compliance_check(
        self,
        task_id: str,
        faves_status: str,
        scores: Dict[str, float],
        passed: bool,
    ) -> None:
        """
        Log compliance check results.

        Args:
            task_id: Task ID
            faves_status: Overall FAVES status
            scores: Individual FAVES scores
            passed: Whether compliance check passed
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "compliance_check",
            "task_id": task_id,
            "faves_status": faves_status,
            "scores": scores,
            "passed": passed,
        }
        self.event_log.append(event)
        status_str = "PASSED" if passed else "FAILED"
        logger.info(f"Compliance check {status_str} for task {task_id}")

    def log_review_request(
        self,
        task_id: str,
        reason: str,
        priority: str,
        required_expertise: List[str],
    ) -> None:
        """
        Log human review request.

        Args:
            task_id: Task ID
            reason: Reason for review request
            priority: Review priority level
            required_expertise: Required reviewer expertise areas
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "review_request",
            "task_id": task_id,
            "reason": reason,
            "priority": priority,
            "required_expertise": required_expertise,
        }
        self.event_log.append(event)
        logger.info(
            f"Review requested for task {task_id} "
            f"(Priority: {priority}, Expertise: {', '.join(required_expertise)})"
        )

    def log_error(
        self,
        task_id: str,
        agent_name: str,
        error_message: str,
        error_type: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log errors during orchestration.

        Args:
            task_id: Task ID
            agent_name: Name of agent where error occurred
            error_message: Error message
            error_type: Error classification
            context: Additional context about the error
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "task_id": task_id,
            "agent_name": agent_name,
            "error_message": error_message,
            "error_type": error_type,
            "context": context or {},
        }
        self.event_log.append(event)
        logger.error(
            f"Error in {agent_name} for task {task_id}: {error_message}"
        )

    def get_event_log(self) -> List[Dict[str, Any]]:
        """
        Get the complete event log.

        Returns:
            List of logged events
        """
        return self.event_log.copy()

    def export_log_as_json(self, filepath: Optional[str] = None) -> str:
        """
        Export event log as JSON.

        Args:
            filepath: Optional file path to save log

        Returns:
            JSON string of event log
        """
        json_str = json.dumps(self.event_log, indent=2, default=str)

        if filepath:
            with open(filepath, "w") as f:
                f.write(json_str)
            logger.info(f"Event log exported to {filepath}")

        return json_str

    def clear_log(self) -> None:
        """Clear the event log."""
        self.event_log.clear()
        logger.debug("Event log cleared")


class NotificationHandler:
    """Handles notifications for workflow events."""

    def __init__(self):
        """Initialize notification handler."""
        self.notifications: List[Dict[str, Any]] = []

    def notify_task_created(
        self,
        task_id: str,
        task_type: str,
        created_by: str,
    ) -> None:
        """
        Send notification that task was created.

        Args:
            task_id: Task ID
            task_type: Type of task
            created_by: Creator user ID
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "task_created",
            "task_id": task_id,
            "task_type": task_type,
            "created_by": created_by,
        }
        self.notifications.append(notification)
        logger.info(f"Notification: Task {task_id} created by {created_by}")

    def notify_compliance_failure(
        self,
        task_id: str,
        issues: List[str],
    ) -> None:
        """
        Send notification of compliance check failure.

        Args:
            task_id: Task ID
            issues: List of compliance issues
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "compliance_failure",
            "task_id": task_id,
            "issues": issues,
            "severity": "high",
        }
        self.notifications.append(notification)
        logger.warning(f"Notification: Task {task_id} compliance failure")

    def notify_review_required(
        self,
        task_id: str,
        reason: str,
        priority: str,
    ) -> None:
        """
        Send notification that review is required.

        Args:
            task_id: Task ID
            reason: Reason for review
            priority: Priority level
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "review_required",
            "task_id": task_id,
            "reason": reason,
            "priority": priority,
        }
        self.notifications.append(notification)
        logger.info(f"Notification: Review required for task {task_id}")

    def notify_task_complete(
        self,
        task_id: str,
        status: str,
    ) -> None:
        """
        Send notification that task is complete.

        Args:
            task_id: Task ID
            status: Final status (approved, rejected, etc.)
        """
        notification = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "task_complete",
            "task_id": task_id,
            "status": status,
        }
        self.notifications.append(notification)
        logger.info(f"Notification: Task {task_id} complete ({status})")

    def get_notifications(self) -> List[Dict[str, Any]]:
        """
        Get all notifications.

        Returns:
            List of notifications
        """
        return self.notifications.copy()

    def clear_notifications(self) -> None:
        """Clear notification queue."""
        self.notifications.clear()


class MetricsCollector:
    """Collects metrics for orchestration performance."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_processing_time": 0,
            "node_timings": {},
            "routing_decisions": {},
        }

    def record_task_completion(
        self,
        task_id: str,
        success: bool,
        processing_time: float,
    ) -> None:
        """
        Record task completion metrics.

        Args:
            task_id: Task ID
            success: Whether task succeeded
            processing_time: Processing time in seconds
        """
        self.metrics["tasks_processed"] += 1

        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1

        # Update average processing time
        avg = self.metrics["avg_processing_time"]
        completed = self.metrics["tasks_completed"]
        self.metrics["avg_processing_time"] = (
            (avg * (completed - 1) + processing_time) / completed
            if completed > 0
            else processing_time
        )

    def record_node_timing(
        self,
        node_name: str,
        execution_time: float,
    ) -> None:
        """
        Record node execution timing.

        Args:
            node_name: Name of the node
            execution_time: Execution time in seconds
        """
        if node_name not in self.metrics["node_timings"]:
            self.metrics["node_timings"][node_name] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
            }

        timing = self.metrics["node_timings"][node_name]
        timing["count"] += 1
        timing["total_time"] += execution_time
        timing["avg_time"] = timing["total_time"] / timing["count"]

    def record_routing_decision(
        self,
        decision_type: str,
        decision_value: str,
    ) -> None:
        """
        Record routing decision statistics.

        Args:
            decision_type: Type of routing decision
            decision_value: Value of the decision
        """
        key = f"{decision_type}:{decision_value}"

        if key not in self.metrics["routing_decisions"]:
            self.metrics["routing_decisions"][key] = 0

        self.metrics["routing_decisions"][key] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics.

        Returns:
            Metrics dictionary
        """
        return self.metrics.copy()
