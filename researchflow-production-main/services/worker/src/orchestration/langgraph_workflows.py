"""
LangGraph Workflows for ResearchFlow
Implements stateful, multi-step research workflows with LLM orchestration.
"""

import os
import logging
import uuid
from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime

logger = logging.getLogger(__name__)

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    StateGraph = None
    END = None
    MemorySaver = None
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not installed")

# Local imports
from .llm_router import get_router, PHIDetector
from .composio_tools import get_toolset


class WorkflowState(TypedDict):
    """State for research workflows."""
    task: str
    plan: Optional[str]
    artifacts: Dict[str, Any]
    messages: List[Dict[str, str]]
    phi_detected: bool
    stage: str
    error: Optional[str]
    metadata: Dict[str, Any]
    run_id: str
    trace_id: str
    manuscript_id: Optional[str]
    branch_id: Optional[str]


class ResearchWorkflow:
    """
    Multi-stage research workflow using LangGraph.
    
    Stages: planner -> generator -> deployer
    With conditional PHI routing for safety.
    """
    
    def __init__(self):
        self.router = get_router()
        self.toolset = get_toolset()
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        if not LANGGRAPH_AVAILABLE:
            logger.error("LangGraph not available")
            return
        
        # Create graph
        graph = StateGraph(WorkflowState)
        
        # Add nodes
        graph.add_node("planner", self._planner_node)
        graph.add_node("phi_check", self._phi_check_node)
        graph.add_node("generator", self._generator_node)
        graph.add_node("deployer", self._deployer_node)
        graph.add_node("local_handler", self._local_handler_node)
        
        # Add edges
        graph.set_entry_point("planner")
        graph.add_edge("planner", "phi_check")
        
        # Conditional routing based on PHI
        graph.add_conditional_edges(
            "phi_check",
            self._route_on_phi,
            {
                "safe": "generator",
                "phi_detected": "local_handler"
            }
        )
        
        graph.add_edge("generator", "deployer")
        graph.add_edge("local_handler", "deployer")
        graph.add_edge("deployer", END)
        
        # Compile with checkpointing
        self.graph = graph.compile(checkpointer=MemorySaver())
    
    def _planner_node(self, state: WorkflowState) -> WorkflowState:
        """Create execution plan for the task."""
        logger.info(f"Planner: Creating plan for task")
        
        try:
            plan_prompt = f"""Create a detailed execution plan for this task:
            
Task: {state['task']}

Provide:
1. Step-by-step breakdown
2. Required tools/integrations
3. Expected outputs
4. Potential risks"""
            
            plan = self.router.invoke(plan_prompt, task_type="reasoning")
            
            return {
                **state,
                "plan": plan,
                "stage": "planned",
                "messages": state["messages"] + [{
                    "role": "planner",
                    "content": plan,
                    "timestamp": datetime.now().isoformat()
                }]
            }
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return {**state, "error": str(e), "stage": "error"}
    
    def _phi_check_node(self, state: WorkflowState) -> WorkflowState:
        """Check for PHI in task and plan."""
        content = f"{state['task']} {state.get('plan', '')}"
        phi_detected = PHIDetector.detect(content)
        
        if phi_detected:
            logger.warning("PHI detected - routing to local handler")
        
        return {**state, "phi_detected": phi_detected}
    
    def _route_on_phi(self, state: WorkflowState) -> str:
        """Route based on PHI detection."""
        return "phi_detected" if state["phi_detected"] else "safe"
    
    def _generator_node(self, state: WorkflowState) -> WorkflowState:
        """Generate artifacts based on plan."""
        logger.info("Generator: Creating artifacts")
        
        try:
            gen_prompt = f"""Based on this plan, generate the required artifacts:
            
Plan: {state['plan']}

Generate high-quality outputs for each step."""
            
            artifacts_text = self.router.invoke(gen_prompt, task_type="generation")
            
            return {
                **state,
                "artifacts": {
                    "generated_content": artifacts_text,
                    "timestamp": datetime.now().isoformat()
                },
                "stage": "generated",
                "messages": state["messages"] + [{
                    "role": "generator",
                    "content": artifacts_text[:500] + "...",
                    "timestamp": datetime.now().isoformat()
                }]
            }
        except Exception as e:
            logger.error(f"Generator error: {e}")
            return {**state, "error": str(e), "stage": "error"}
    
    def _local_handler_node(self, state: WorkflowState) -> WorkflowState:
        """Handle PHI-sensitive tasks locally."""
        logger.info("Local Handler: Processing with local LLM")
        
        try:
            result = self.router.invoke(
                state["task"],
                force_local=True
            )
            
            return {
                **state,
                "artifacts": {
                    "local_result": result,
                    "phi_safe": True,
                    "timestamp": datetime.now().isoformat()
                },
                "stage": "local_processed"
            }
        except Exception as e:
            logger.error(f"Local handler error: {e}")
            return {**state, "error": str(e), "stage": "error"}
    
    def _deployer_node(self, state: WorkflowState) -> WorkflowState:
        """Deploy artifacts using Composio tools."""
        logger.info("Deployer: Executing deployment actions")
        
        try:
            # Use Composio tools if available
            tools = self.toolset.get_tools()
            
            deployment_actions = []
            
            # Log completion
            deployment_actions.append({
                "action": "workflow_complete",
                "timestamp": datetime.now().isoformat(),
                "artifacts_count": len(state.get("artifacts", {}))
            })
            
            return {
                **state,
                "stage": "deployed",
                "metadata": {
                    **state.get("metadata", {}),
                    "deployment_actions": deployment_actions
                },
                "messages": state["messages"] + [{
                    "role": "deployer",
                    "content": "Workflow completed successfully",
                    "timestamp": datetime.now().isoformat()
                }]
            }
        except Exception as e:
            logger.error(f"Deployer error: {e}")
            return {**state, "error": str(e), "stage": "error"}
    
    def invoke(self, task: str, config: Optional[Dict] = None) -> WorkflowState:
        """Execute the workflow for a given task."""
        if self.graph is None:
            raise RuntimeError("Workflow graph not built - LangGraph may not be installed")
        
        config = config or {}
        run_id = config.get("run_id") or uuid.uuid4().hex
        trace_id = config.get("trace_id") or run_id
        manuscript_id = config.get("manuscript_id")
        branch_id = config.get("branch_id")
        
        initial_state: WorkflowState = {
            "task": task,
            "plan": None,
            "artifacts": {},
            "messages": [],
            "phi_detected": False,
            "stage": "started",
            "error": None,
            "metadata": {"started_at": datetime.now().isoformat()},
            "run_id": run_id,
            "trace_id": trace_id,
            "manuscript_id": manuscript_id,
            "branch_id": branch_id,
        }
        
        thread_config = {"configurable": {"thread_id": config.get("thread_id", "default")}}
        
        result = self.graph.invoke(initial_state, thread_config)
        return result


# Singleton workflow instance
_workflow: Optional[ResearchWorkflow] = None

def get_workflow() -> ResearchWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = ResearchWorkflow()
    return _workflow


def run_research_task(task: str, **kwargs) -> WorkflowState:
    """Convenience function to run a research workflow."""
    return get_workflow().invoke(task, kwargs)
