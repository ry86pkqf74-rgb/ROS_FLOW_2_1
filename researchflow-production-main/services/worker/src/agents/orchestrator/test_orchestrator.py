"""
Test and Demonstration of LangGraph Governance Orchestration

This script demonstrates:
- Creating an orchestrator instance
- Executing governance tasks
- Visualizing the graph structure
- Monitoring metrics and events
- Handling different task types

Linear Issues: ROS-30, ROS-103
"""

import sys
import json
from datetime import datetime


def test_orchestrator_creation():
    """Test orchestrator creation and graph visualization."""
    from agents.orchestrator import get_orchestrator

    print("\n" + "=" * 70)
    print("TEST 1: Orchestrator Creation and Graph Visualization")
    print("=" * 70)

    orchestrator = get_orchestrator()
    print("✓ Orchestrator created successfully")

    # Get visualization
    viz = orchestrator.visualize()
    print(f"✓ Graph visualization generated ({len(viz)} characters)")
    print("\nMermaid Diagram:")
    print("-" * 70)
    print(viz)
    print("-" * 70)


def test_design_task_execution():
    """Test design task execution."""
    from agents.orchestrator import get_orchestrator

    print("\n" + "=" * 70)
    print("TEST 2: Design Task Execution")
    print("=" * 70)

    orchestrator = get_orchestrator()

    final_state = orchestrator.execute_task(
        task_id="design_task_001",
        task_type="design",
        task_description="Create microservices architecture design",
        created_by="architect_user",
    )

    print(f"✓ Task {final_state['task_id']} executed")
    print(f"  Stage: {final_state['stage']}")
    print(f"  Review Status: {final_state['review_status']}")
    print(f"  FAVES Status: {final_state['faves_status']}")
    print(f"  Is Compliant: {final_state['is_compliant']}")
    print(f"  Can Proceed: {final_state['can_proceed']}")


def test_spec_task_execution():
    """Test specification task execution."""
    from agents.orchestrator import get_orchestrator

    print("\n" + "=" * 70)
    print("TEST 3: Specification Task Execution")
    print("=" * 70)

    orchestrator = get_orchestrator()

    final_state = orchestrator.execute_task(
        task_id="spec_task_001",
        task_type="spec",
        task_description="Create technical specification document",
        created_by="spec_writer",
    )

    print(f"✓ Task {final_state['task_id']} executed")
    print(f"  Stage: {final_state['stage']}")
    print(f"  FAVES Details: {final_state['faves_details']}")


def test_metrics_collection():
    """Test metrics collection."""
    from agents.orchestrator import get_orchestrator

    print("\n" + "=" * 70)
    print("TEST 4: Metrics Collection")
    print("=" * 70)

    orchestrator = get_orchestrator()

    # Execute multiple tasks
    for i in range(2):
        orchestrator.execute_task(
            task_id=f"metrics_task_{i:03d}",
            task_type="design",
            task_description=f"Test task {i}",
            created_by="tester",
        )

    metrics = orchestrator.get_metrics()
    print("✓ Metrics collected:")
    print(f"  Tasks Processed: {metrics['tasks_processed']}")
    print(f"  Tasks Completed: {metrics['tasks_completed']}")
    print(f"  Tasks Failed: {metrics['tasks_failed']}")
    print(f"  Avg Processing Time: {metrics['avg_processing_time']:.3f}s")
    print(f"  Node Timings: {len(metrics['node_timings'])} nodes tracked")


def test_event_logging():
    """Test event logging."""
    from agents.orchestrator import get_orchestrator

    print("\n" + "=" * 70)
    print("TEST 5: Event Logging")
    print("=" * 70)

    orchestrator = get_orchestrator()

    orchestrator.execute_task(
        task_id="logging_task_001",
        task_type="design",
        task_description="Test event logging",
        created_by="logger_test",
    )

    event_log = orchestrator.get_event_log()
    print(f"✓ Event log captured {len(event_log)} events")

    # Show sample events
    print("\nSample Events:")
    for i, event in enumerate(event_log[:5]):
        print(f"  {i+1}. {event['event_type']} - {event.get('node_name', 'N/A')}")

    if len(event_log) > 5:
        print(f"  ... and {len(event_log) - 5} more events")


def test_routing_logic():
    """Test routing logic for different task types."""
    from agents.orchestrator import (
        route_by_task_type,
        route_by_faves_status,
        route_by_approval,
    )
    from agents.orchestrator.state import create_initial_state

    print("\n" + "=" * 70)
    print("TEST 6: Routing Logic")
    print("=" * 70)

    # Test task type routing
    test_cases = [
        ("design", "design_ops"),
        ("spec", "spec_ops"),
        ("compliance", "compliance_check"),
        ("release", "release_guardian"),
    ]

    print("Task Type Routing:")
    for task_type, expected_node in test_cases:
        state = create_initial_state(
            task_id="route_test",
            task_type=task_type,
            task_description="Test routing",
            created_by="router_test",
        )
        result = route_by_task_type(state)
        status = "✓" if result == expected_node else "✗"
        print(f"  {status} {task_type} -> {result} (expected: {expected_node})")

    # Test FAVES routing
    print("\nFAVES Status Routing:")
    faves_cases = [
        ("pass", "release_guardian"),
        ("fail", "human_review"),
        ("error", "human_review"),
        ("pending", "compliance_check"),
    ]

    for faves_status, expected_node in faves_cases:
        state = create_initial_state(
            task_id="faves_test",
            task_type="design",
            task_description="Test FAVES routing",
            created_by="faves_test",
        )
        state["faves_status"] = faves_status
        result = route_by_faves_status(state)
        status = "✓" if result == expected_node else "✗"
        print(f"  {status} {faves_status} -> {result} (expected: {expected_node})")

    # Test approval routing
    print("\nApproval Status Routing:")
    approval_cases = [
        ("approved", "release_guardian"),
        ("rejected", "END"),
        ("pending", "human_review"),
    ]

    for review_status, expected_node in approval_cases:
        state = create_initial_state(
            task_id="approval_test",
            task_type="design",
            task_description="Test approval routing",
            created_by="approval_test",
        )
        state["review_status"] = review_status
        result = route_by_approval(state)
        status = "✓" if result == expected_node else "✗"
        print(f"  {status} {review_status} -> {result} (expected: {expected_node})")


def test_state_management():
    """Test state management utilities."""
    from agents.orchestrator.state import (
        create_initial_state,
        add_message,
        add_error,
        add_agent_output,
    )

    print("\n" + "=" * 70)
    print("TEST 7: State Management")
    print("=" * 70)

    state = create_initial_state(
        task_id="state_test",
        task_type="design",
        task_description="Test state management",
        created_by="state_tester",
    )

    print("✓ Initial state created")

    # Add message
    state = add_message(state, "test_agent", "Test message", "status")
    print(f"✓ Message added: {len(state['messages'])} message(s)")

    # Add error
    state = add_error(state, "test_agent", "Test error", "test_error")
    print(f"✓ Error added: {len(state['errors'])} error(s)")

    # Add agent output
    state = add_agent_output(state, "test_agent", {"result": "test_output"})
    print(f"✓ Agent output added: {len(state['agent_outputs'])} agent(s)")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("LangGraph Governance Orchestration - Test Suite")
    print("=" * 70)

    try:
        test_orchestrator_creation()
        test_design_task_execution()
        test_spec_task_execution()
        test_metrics_collection()
        test_event_logging()
        test_routing_logic()
        test_state_management()

        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
