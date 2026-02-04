"""
Orchestrator Multi-Agent Graph

This module implements the LangGraph governance orchestration graph,
coordinating multiple agents through design, compliance, review, and
release phases.

Linear Issues: ROS-30, ROS-103
"""

import logging
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import GovernanceState
from .routing import (
    route_by_task_type,
    route_by_faves_status,
    route_by_approval,
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

logger = logging.getLogger(__name__)


def create_governance_graph():
    """
    Create and compile the governance orchestration graph.

    Graph Structure:
    - router: Entry point, classifies task type
    - design_ops: Design operations for design tasks
    - spec_ops: Specification operations for spec tasks
    - compliance_check: FAVES compliance gate
    - human_review: Human review gate for failed compliance or complex issues
    - release_guardian: Final authorization gate
    - END: Workflow completion

    Routing Logic:
    - router -> route_by_task_type -> {design_ops, spec_ops, compliance_check, release_guardian}
    - design_ops/spec_ops -> compliance_check
    - compliance_check -> route_by_faves_status -> {release_guardian if pass, human_review if fail}
    - human_review -> route_by_approval -> {release_guardian if approved, END if rejected}
    - release_guardian -> END

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    # Initialize workflow graph with GovernanceState
    workflow = StateGraph(GovernanceState)

    # Add all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("design_ops", design_ops_node)
    workflow.add_node("spec_ops", spec_ops_node)
    workflow.add_node("compliance_check", compliance_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("release_guardian", release_guardian_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Router routes to appropriate agent based on task type
    workflow.add_conditional_edges(
        "router",
        route_by_task_type,
        {
            "design_ops": "design_ops",
            "spec_ops": "spec_ops",
            "compliance_check": "compliance_check",
            "release_guardian": "release_guardian",
        },
    )

    # Design and spec operations flow to compliance check
    workflow.add_edge("design_ops", "compliance_check")
    workflow.add_edge("spec_ops", "compliance_check")

    # Compliance check routes based on FAVES status
    workflow.add_conditional_edges(
        "compliance_check",
        route_by_faves_status,
        {
            "release_guardian": "release_guardian",
            "human_review": "human_review",
            "compliance_check": "compliance_check",  # Loop for pending
            "END": END,
        },
    )

    # Human review routes based on approval decision
    workflow.add_conditional_edges(
        "human_review",
        route_by_approval,
        {
            "release_guardian": "release_guardian",
            "design_ops": "design_ops",  # Revision cycle
            "spec_ops": "spec_ops",  # Revision cycle
            "compliance_check": "compliance_check",  # Revision cycle
            "human_review": "human_review",  # Loop for pending
            "END": END,
        },
    )

    # Release guardian leads to end
    workflow.add_edge("release_guardian", END)

    # Compile with memory checkpointer for persistence
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)

    logger.info("Governance orchestration graph created successfully")

    return graph


def create_governance_graph_with_config(
    config: Optional[Dict[str, Any]] = None,
):
    """
    Create governance graph with optional configuration.

    Args:
        config: Optional configuration dictionary with:
            - checkpointer_type: "memory" or "redis" (default: "memory")
            - enable_visualization: Enable graph visualization (default: True)
            - debug_mode: Enable debug logging (default: False)

    Returns:
        Compiled LangGraph StateGraph
    """
    if config is None:
        config = {}

    checkpointer_type = config.get("checkpointer_type", "memory")
    enable_visualization = config.get("enable_visualization", True)
    debug_mode = config.get("debug_mode", False)

    if debug_mode:
        logger.setLevel(logging.DEBUG)

    # Create base graph
    graph = create_governance_graph()

    # Add visualization if requested
    if enable_visualization:
        try:
            mermaid_str = graph.get_graph().draw_mermaid()
            logger.debug(f"Graph Mermaid:\n{mermaid_str}")
        except Exception as e:
            logger.warning(f"Could not generate graph visualization: {e}")

    logger.info(
        f"Governance graph initialized with config: "
        f"checkpointer={checkpointer_type}, "
        f"visualization={enable_visualization}, "
        f"debug={debug_mode}"
    )

    return graph


def visualize_graph(graph) -> str:
    """
    Generate Mermaid diagram of the governance graph.

    Args:
        graph: Compiled LangGraph StateGraph

    Returns:
        Mermaid diagram as string
    """
    try:
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.error(f"Failed to generate graph visualization: {e}")
        return f"Error generating visualization: {e}"


def get_graph_schema(graph) -> Dict[str, Any]:
    """
    Get schema information about the governance graph.

    Args:
        graph: Compiled LangGraph StateGraph

    Returns:
        Dictionary with graph schema details
    """
    try:
        graph_obj = graph.get_graph()

        schema = {
            "nodes": [],
            "edges": [],
            "entry_point": None,
            "exit_point": END,
        }

        # Extract nodes
        if hasattr(graph_obj, 'nodes') and hasattr(graph_obj.nodes, 'items'):
            for node_id, node in graph_obj.nodes.items():
                schema["nodes"].append({
                    "id": node_id,
                    "data": str(node),
                })

        # Extract edges - handle both dict and list formats
        if hasattr(graph_obj, 'edges'):
            if isinstance(graph_obj.edges, dict):
                for edge_start, edge_data in graph_obj.edges.items():
                    if isinstance(edge_data, dict):
                        for edge_end, edge_info in edge_data.items():
                            schema["edges"].append({
                                "from": edge_start,
                                "to": edge_end,
                                "conditional": isinstance(edge_info, dict) and edge_info.get("conditional", False),
                            })
            elif isinstance(graph_obj.edges, list):
                for edge in graph_obj.edges:
                    if isinstance(edge, (tuple, list)) and len(edge) >= 2:
                        schema["edges"].append({
                            "from": edge[0],
                            "to": edge[1],
                            "conditional": len(edge) > 2 and edge[2].get("conditional", False),
                        })

        return schema
    except Exception as e:
        logger.warning(f"Error extracting graph schema: {e}")
        return {
            "nodes": [],
            "edges": [],
            "error": str(e),
        }


class GovernanceOrchestrator:
    """
    High-level interface for orchestrating governance workflows.

    Wraps the LangGraph graph with convenience methods for common operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.graph = create_governance_graph_with_config(self.config)
        self.logger = get_logger()
        self.metrics = get_metrics_collector()

    def execute_task(
        self,
        task_id: str,
        task_type: str,
        task_description: str,
        created_by: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a governance task through the orchestration graph.

        Args:
            task_id: Unique task identifier
            task_type: Type of task (design, spec, compliance, release)
            task_description: Task description
            created_by: User ID of task creator
            config: Optional execution config (thread_id, etc.)

        Returns:
            Final state after graph execution
        """
        from .state import create_initial_state

        # Create initial state
        initial_state = create_initial_state(
            task_id=task_id,
            task_type=task_type,
            task_description=task_description,
            created_by=created_by,
        )

        logger.info(f"Executing governance task {task_id} ({task_type})")

        try:
            # Prepare execution config with default thread_id if not provided
            exec_config = config or {}
            if "configurable" not in exec_config:
                exec_config["configurable"] = {}
            if "thread_id" not in exec_config["configurable"]:
                exec_config["configurable"]["thread_id"] = task_id

            final_state = self.graph.invoke(initial_state, config=exec_config)

            logger.info(f"Task {task_id} completed successfully")
            return final_state

        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            raise

    def get_event_log(self):
        """Get the complete event log."""
        return self.logger.get_event_log()

    def get_metrics(self):
        """Get performance metrics."""
        return self.metrics.get_metrics()

    def visualize(self) -> str:
        """Get Mermaid visualization of the graph."""
        return visualize_graph(self.graph)

    def get_schema(self) -> Dict[str, Any]:
        """Get graph schema information."""
        return get_graph_schema(self.graph)

    def clear_logs(self) -> None:
        """Clear event logs."""
        self.logger.clear_log()

    def export_logs(self, filepath: str) -> None:
        """Export event logs to JSON file."""
        self.logger.export_log_as_json(filepath)


# Convenience function for quick graph creation
def get_orchestrator(config: Optional[Dict[str, Any]] = None) -> GovernanceOrchestrator:
    """
    Get a governance orchestrator instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        GovernanceOrchestrator instance
    """
    return GovernanceOrchestrator(config)
