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


# Canonical gate status for HITL pause (worker pauses here, orchestrator/UI drives resume)
WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"


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
    # Phase 3: HITL gate — worker pauses at gate_status=WAITING_FOR_HUMAN; resume with human_decision
    gate_status: Optional[str]
    human_decision: Optional[str]


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
        # Phase 3: HITL gate — pause here until human resumes with human_decision
        graph.add_node("human_gate", self._human_gate_node)
        graph.add_node("resume_handler", self._resume_handler_node)
        graph.add_node("rejected_end", self._rejected_end_node)
        
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
        
        # Both generator and local_handler go through human gate, then resume_handler
        graph.add_edge("generator", "human_gate")
        graph.add_edge("local_handler", "human_gate")
        graph.add_edge("human_gate", "resume_handler")
        graph.add_conditional_edges(
            "resume_handler",
            self._route_after_resume,
            {"approved": "deployer", "rejected": "rejected_end"}
        )
        graph.add_edge("deployer", END)
        graph.add_edge("rejected_end", END)
        
        # Compile with checkpointing; interrupt_after enables HITL pause at human_gate (LangGraph 0.2+)
        try:
            self.graph = graph.compile(
                checkpointer=MemorySaver(),
                interrupt_after=["human_gate"],
            )
        except TypeError:
            # Older LangGraph: compile without interrupt (gate node still runs, no pause)
            self.graph = graph.compile(checkpointer=MemorySaver())
            logger.warning("LangGraph compile: interrupt_after not supported; HITL gate will not pause")
    
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

    def _human_gate_node(self, state: WorkflowState) -> WorkflowState:
        """Phase 3: Pause for human review. Sets gate_status=WAITING_FOR_HUMAN; resume via invoke with human_decision."""
        logger.info("Human gate: pausing for human review (WAITING_FOR_HUMAN)")
        return {
            **state,
            "gate_status": WAITING_FOR_HUMAN,
            "stage": "waiting_for_human",
            "messages": state["messages"] + [{
                "role": "system",
                "content": "Workflow paused for human review. Resume with human_decision=approved or human_decision=rejected.",
                "timestamp": datetime.now().isoformat(),
            }],
        }

    def _resume_handler_node(self, state: WorkflowState) -> WorkflowState:
        """Runs after resume; routes to deployer or rejected_end based on human_decision."""
        decision = (state.get("human_decision") or "").strip().lower()
        logger.info("Resume handler: human_decision=%s", decision)
        return {
            **state,
            "gate_status": None,
            "stage": "resumed",
            "metadata": {
                **state.get("metadata", {}),
                "human_decision": decision,
                "resumed_at": datetime.now().isoformat(),
            },
        }

    def _route_after_resume(self, state: WorkflowState) -> str:
        """Route to deployer if approved, else rejected_end."""
        decision = (state.get("human_decision") or "").strip().lower()
        return "approved" if decision == "approved" else "rejected"

    def _rejected_end_node(self, state: WorkflowState) -> WorkflowState:
        """Terminal node when human rejects at gate."""
        logger.info("Workflow ended: human rejected at gate")
        return {
            **state,
            "stage": "human_rejected",
            "messages": state["messages"] + [{
                "role": "system",
                "content": "Workflow rejected by human at review gate.",
                "timestamp": datetime.now().isoformat(),
            }],
        }

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
        """Execute the workflow for a given task, or resume from WAITING_FOR_HUMAN.
        To resume deterministically: pass same thread_id and config with human_decision='approved' or 'rejected'.
        """
        if self.graph is None:
            raise RuntimeError("Workflow graph not built - LangGraph may not be installed")
        
        config = config or {}
        thread_id = config.get("thread_id", "default")
        thread_config = {"configurable": {"thread_id": thread_id}}

        # Phase 3: Resume from human gate — pass only human_decision so graph continues from resume_handler
        if config.get("resume") and "human_decision" in config:
            human_decision = str(config.get("human_decision", "")).strip()
            resume_input: WorkflowState = {
                "task": "",
                "plan": None,
                "artifacts": {},
                "messages": [],
                "phi_detected": False,
                "stage": "resuming",
                "error": None,
                "metadata": {},
                "run_id": config.get("run_id", ""),
                "trace_id": config.get("trace_id", ""),
                "manuscript_id": config.get("manuscript_id"),
                "branch_id": config.get("branch_id"),
                "gate_status": None,
                "human_decision": human_decision,
            }
            result = self.graph.invoke(resume_input, thread_config)
            return result

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
            "gate_status": None,
            "human_decision": None,
        }
        
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
