"""
LangGraph Governance Orchestration (Phase 4)

This package provides multi-agent orchestration for governance workflows,
coordinating design operations, specification management, compliance checking,
human review gates, and release authorization through a LangGraph state machine.

Key Components:
- GovernanceState: Shared state definition for all agents
- Nodes: Router, DesignOps, SpecOps, Compliance, HumanReview, ReleaseGuardian
- Routing: Conditional routing logic based on task type, compliance, and approvals
- Graph: LangGraph multi-agent orchestration with visualization support
- Callbacks: Event logging, notifications, and metrics collection

Architecture:
- Entry: Router classifies tasks
- Processing: Design/Spec agents generate content
- Validation: Compliance check evaluates against FAVES criteria
- Review: Human review gate for escalations
- Release: Release guardian provides final authorization

Visualization:
The graph can be visualized with graph.get_graph().draw_mermaid() for:
- Node dependencies
- Conditional routing paths
- Control flow

Linear Issues: ROS-30, ROS-103
"""

from .state import (
    GovernanceState,
    ReviewRequest,
    ComplianceCheckResult,
    ReleaseApproval,
    AgentMessage,
    create_initial_state,
    add_agent_output,
    add_message,
    add_error,
)

from .routing import (
    route_by_task_type,
    route_by_faves_status,
    route_by_approval,
    route_by_release_decision,
    should_escalate_to_stakeholder,
    get_next_agent,
)

from .nodes import (
    router_node,
    design_ops_node,
    spec_ops_node,
    compliance_node,
    human_review_node,
    release_guardian_node,
    get_logger,
    get_metrics_collector,
)

from .graph import (
    create_governance_graph,
    create_governance_graph_with_config,
    visualize_graph,
    get_graph_schema,
    GovernanceOrchestrator,
    get_orchestrator,
)

from .callbacks import (
    OrchestrationLogger,
    NotificationHandler,
    MetricsCollector,
)

__all__ = [
    # State Management
    "GovernanceState",
    "ReviewRequest",
    "ComplianceCheckResult",
    "ReleaseApproval",
    "AgentMessage",
    "create_initial_state",
    "add_agent_output",
    "add_message",
    "add_error",
    # Routing Functions
    "route_by_task_type",
    "route_by_faves_status",
    "route_by_approval",
    "route_by_release_decision",
    "should_escalate_to_stakeholder",
    "get_next_agent",
    # Node Functions
    "router_node",
    "design_ops_node",
    "spec_ops_node",
    "compliance_node",
    "human_review_node",
    "release_guardian_node",
    "get_logger",
    "get_metrics_collector",
    # Graph Functions
    "create_governance_graph",
    "create_governance_graph_with_config",
    "visualize_graph",
    "get_graph_schema",
    "GovernanceOrchestrator",
    "get_orchestrator",
    # Callbacks and Logging
    "OrchestrationLogger",
    "NotificationHandler",
    "MetricsCollector",
]

__version__ = "1.0.0"
__doc__ = """
LangGraph Governance Orchestration

Usage:
    from agents.orchestrator import get_orchestrator, create_initial_state

    # Create orchestrator
    orchestrator = get_orchestrator()

    # Execute a task
    final_state = orchestrator.execute_task(
        task_id="task_001",
        task_type="design",
        task_description="Create system design specification",
        created_by="user_123",
    )

    # Access results
    print(f"Task status: {final_state['review_status']}")
    print(f"Compliance: {final_state['is_compliant']}")
    print(f"Can proceed: {final_state['can_proceed']}")

    # Visualize the graph
    print(orchestrator.visualize())

    # Get metrics
    metrics = orchestrator.get_metrics()
    print(f"Tasks processed: {metrics['tasks_processed']}")

    # Export logs
    orchestrator.export_logs("governance_log.json")
"""
