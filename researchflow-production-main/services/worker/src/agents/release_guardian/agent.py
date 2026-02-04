"""
Release Guardian Agent - Pre-deployment gate enforcement

Implements a LangGraph-based agent for orchestrating release gates,
validating deployment readiness, and managing pre-deploy decisions.

Uses Composio GITHUB and NOTION toolkits for integration.

Linear Issue: ROS-150
"""

import json
import logging
from typing import Any, Dict, List, Optional, Annotated
from dataclasses import dataclass, asdict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .gates import Gate, GateResult, CIStatusGate, EvidencePackGate, FAVESGate, RollbackGate, MonitoringGate
from .actions import Action, ActionResult, BlockDeployment, ApproveDeployment, RequestSignoff, GenerateReleaseReport
from .validators import DeploymentModeValidator

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class ReleaseGuardianState(dict):
    """State passed through the Release Guardian graph."""
    messages: List[BaseMessage]
    release_id: str
    deployment_mode: str
    release_context: Dict[str, Any]

    # Gate Results
    gate_results: List[Dict[str, Any]]
    passed_gates: List[str]
    failed_gates: List[str]

    # Decisions
    deployment_approved: bool
    deployment_blocked: bool
    blocking_reason: Optional[str]

    # Actions taken
    actions_executed: List[ActionResult]

    # Report
    release_report: Optional[Dict[str, Any]]

    # Metadata
    started_at: str
    completed_at: Optional[str]
    error: Optional[str]


@dataclass
class ReleaseGuardianConfig:
    """Configuration for Release Guardian Agent."""
    name: str = "ReleaseGuardianAgent"
    description: str = "Pre-deployment gate enforcement for ResearchFlow releases"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.3
    max_iterations: int = 3
    timeout_seconds: int = 300
    enable_composio_github: bool = True
    enable_composio_notion: bool = True


@dataclass
class ReleaseGuardianResult:
    """Final result from Release Guardian execution."""
    release_id: str
    deployment_approved: bool
    deployment_mode: str
    gates_passed: int
    gates_failed: int
    actions_taken: List[ActionResult]
    report: Optional[Dict[str, Any]]
    duration_seconds: float
    error: Optional[str] = None


# =============================================================================
# Release Guardian Agent
# =============================================================================

class ReleaseGuardianAgent:
    """
    Release Guardian Agent for pre-deployment gate enforcement.

    Orchestrates:
    1. Gate Evaluation - Run all deployment gates
    2. Analysis - Use LLM to reason about gate results
    3. Decision - Approve or block deployment
    4. Actions - Execute appropriate follow-up actions
    5. Reporting - Generate deployment readiness report
    """

    def __init__(self, config: Optional[ReleaseGuardianConfig] = None):
        """Initialize Release Guardian Agent."""
        self.config = config or ReleaseGuardianConfig()
        self.llm = self._create_llm()
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()

        # Initialize gates
        self.gates: Dict[str, Gate] = {
            "ci_status": CIStatusGate(),
            "evidence_pack": EvidencePackGate(),
            "faves": FAVESGate(),
            "rollback": RollbackGate(),
            "monitoring": MonitoringGate(),
        }

        # Initialize actions
        self.actions: Dict[str, Action] = {
            "block_deployment": BlockDeployment(),
            "approve_deployment": ApproveDeployment(),
            "request_signoff": RequestSignoff(),
            "generate_report": GenerateReleaseReport(),
        }

    def _create_llm(self):
        """Create LLM for policy reasoning."""
        return ChatOpenAI(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            max_tokens=2048,
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(ReleaseGuardianState)

        # Add nodes
        workflow.add_node("evaluate_gates", self._evaluate_gates_node)
        workflow.add_node("analyze_results", self._analyze_results_node)
        workflow.add_node("make_decision", self._make_decision_node)
        workflow.add_node("execute_actions", self._execute_actions_node)
        workflow.add_node("generate_report", self._generate_report_node)

        # Define edges
        workflow.set_entry_point("evaluate_gates")
        workflow.add_edge("evaluate_gates", "analyze_results")
        workflow.add_edge("analyze_results", "make_decision")
        workflow.add_edge("make_decision", "execute_actions")
        workflow.add_edge("execute_actions", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile(checkpointer=self.checkpointer)

    # =========================================================================
    # Graph Nodes
    # =========================================================================

    async def _evaluate_gates_node(
        self, state: ReleaseGuardianState
    ) -> ReleaseGuardianState:
        """Evaluate all deployment gates."""
        logger.info(f"[Release Guardian] Evaluating gates for release {state['release_id']}")

        try:
            gate_results: List[GateResult] = []

            # Run each gate
            for gate_name, gate in self.gates.items():
                logger.info(f"[Release Guardian] Running gate: {gate_name}")
                try:
                    result = await gate.check(state.get("release_context", {}))
                    gate_results.append(result)
                except Exception as e:
                    logger.error(f"Gate {gate_name} failed with error: {e}")
                    # Create failed gate result
                    gate_results.append(
                        GateResult(
                            gate_name=gate_name,
                            passed=False,
                            message=f"Gate execution error: {str(e)}",
                            details={"error": str(e)},
                        )
                    )

            # Categorize results
            passed_gates = [r.gate_name for r in gate_results if r.passed]
            failed_gates = [r.gate_name for r in gate_results if not r.passed]

            return {
                **state,
                "gate_results": [asdict(r) for r in gate_results],
                "passed_gates": passed_gates,
                "failed_gates": failed_gates,
            }

        except Exception as e:
            logger.error(f"Gate evaluation error: {e}")
            return {
                **state,
                "error": f"Gate evaluation failed: {str(e)}",
                "gate_results": [],
                "passed_gates": [],
                "failed_gates": [],
            }

    async def _analyze_results_node(
        self, state: ReleaseGuardianState
    ) -> ReleaseGuardianState:
        """Use LLM to analyze gate results and reason about deployment readiness."""
        logger.info(f"[Release Guardian] Analyzing gate results for {state['release_id']}")

        try:
            deployment_mode = state.get("deployment_mode", "DEMO")
            gate_results = state.get("gate_results", [])
            failed_gates = state.get("failed_gates", [])

            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(
                deployment_mode, gate_results, failed_gates
            )

            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=analysis_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Store LLM analysis in messages
            state["messages"].append(response)

            logger.info(f"[Release Guardian] Analysis complete: {response.content[:100]}...")

            return state

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {
                **state,
                "error": f"Analysis failed: {str(e)}",
            }

    async def _make_decision_node(
        self, state: ReleaseGuardianState
    ) -> ReleaseGuardianState:
        """Make deployment approval/blocking decision."""
        logger.info(f"[Release Guardian] Making decision for {state['release_id']}")

        try:
            failed_gates = state.get("failed_gates", [])
            deployment_mode = state.get("deployment_mode", "DEMO")

            # Get mode requirements
            mode_reqs = DeploymentModeValidator.get_mode_requirements(deployment_mode)

            # Decision logic:
            # 1. All gates must pass for deployment
            # 2. In LIVE mode, all required gates must pass

            if not failed_gates:
                logger.info(f"[Release Guardian] All gates passed - deployment approved")
                return {
                    **state,
                    "deployment_approved": True,
                    "deployment_blocked": False,
                    "blocking_reason": None,
                }
            else:
                # Check if failed gates are critical
                critical_gates = ["ci_status", "rollback", "monitoring"]
                critical_failed = [g for g in failed_gates if g in critical_gates]

                if critical_failed:
                    blocking_reason = (
                        f"Critical gates failed: {', '.join(critical_failed)}"
                    )
                    logger.warning(f"[Release Guardian] {blocking_reason}")
                    return {
                        **state,
                        "deployment_approved": False,
                        "deployment_blocked": True,
                        "blocking_reason": blocking_reason,
                    }
                else:
                    # Non-critical gates failed - manual approval needed
                    logger.warning(
                        f"[Release Guardian] Non-critical gates failed: {failed_gates}"
                    )
                    return {
                        **state,
                        "deployment_approved": False,
                        "deployment_blocked": False,  # Not automatically blocked
                        "blocking_reason": f"Manual approval needed: {', '.join(failed_gates)}",
                    }

        except Exception as e:
            logger.error(f"Decision error: {e}")
            return {
                **state,
                "deployment_approved": False,
                "deployment_blocked": True,
                "blocking_reason": f"Decision logic error: {str(e)}",
                "error": str(e),
            }

    async def _execute_actions_node(
        self, state: ReleaseGuardianState
    ) -> ReleaseGuardianState:
        """Execute appropriate actions based on decision."""
        logger.info(f"[Release Guardian] Executing actions for {state['release_id']}")

        try:
            actions_executed: List[ActionResult] = []

            release_id = state.get("release_id")
            deployment_approved = state.get("deployment_approved", False)
            deployment_blocked = state.get("deployment_blocked", False)
            failed_gates = state.get("failed_gates", [])
            gate_results = state.get("gate_results", [])

            # Always generate report
            report_action = self.actions["generate_report"]
            report_result = await report_action.execute({
                "release_id": release_id,
                "gate_results": gate_results,
                "deployment_mode": state.get("deployment_mode"),
                "deployment_target": state.get("release_context", {}).get("target"),
            })
            actions_executed.append(report_result)

            # Execute deployment decision action
            if deployment_blocked:
                block_action = self.actions["block_deployment"]
                block_result = await block_action.execute({
                    "release_id": release_id,
                    "reason": state.get("blocking_reason"),
                    "blocking_gates": failed_gates,
                })
                actions_executed.append(block_result)

            elif deployment_approved:
                approve_action = self.actions["approve_deployment"]
                approve_result = await approve_action.execute({
                    "release_id": release_id,
                    "approval_reason": "All gates passed",
                    "gate_results": gate_results,
                })
                actions_executed.append(approve_result)
            else:
                # Request signoffs for manual approval
                signoff_action = self.actions["request_signoff"]
                signoff_result = await signoff_action.execute({
                    "release_id": release_id,
                    "missing_signoffs": failed_gates,
                    "stakeholder_emails": state.get("release_context", {}).get("stakeholder_emails", []),
                })
                actions_executed.append(signoff_result)

            return {
                **state,
                "actions_executed": actions_executed,
            }

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return {
                **state,
                "error": f"Action execution failed: {str(e)}",
                "actions_executed": [],
            }

    async def _generate_report_node(
        self, state: ReleaseGuardianState
    ) -> ReleaseGuardianState:
        """Generate and store release report."""
        logger.info(f"[Release Guardian] Generating report for {state['release_id']}")

        try:
            completed_at = datetime.utcnow().isoformat()

            # Report already generated in execute_actions
            # Just store completion time
            return {
                **state,
                "completed_at": completed_at,
            }

        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return {
                **state,
                "error": f"Report generation failed: {str(e)}",
                "completed_at": datetime.utcnow().isoformat(),
            }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """Get system prompt for policy reasoning."""
        return """You are a deployment policy expert and release guardian for ResearchFlow.

Your role is to:
1. Analyze gate results to understand deployment readiness
2. Consider deployment mode (DEMO vs LIVE) when making decisions
3. Reason about the impact of failed gates
4. Provide clear policy justifications for approval/blocking decisions

Deployment Policy:
- All gates must pass for automated deployment approval
- LIVE deployments require FAVES compliance and full monitoring
- DEMO deployments are more lenient but still require CI to pass
- Rollback plan is always required
- Evidence pack must be present and hashed for audit trail

Provide concise policy analysis focusing on:
1. Gate status summary
2. Critical vs non-critical failures
3. Deployment readiness assessment
4. Recommended next steps"""

    def _build_analysis_prompt(
        self,
        deployment_mode: str,
        gate_results: List[Dict[str, Any]],
        failed_gates: List[str],
    ) -> str:
        """Build analysis prompt for LLM."""
        gate_summary = "\n".join([
            f"- {g['gate_name']}: {'PASSED' if g['passed'] else 'FAILED'} - {g['message']}"
            for g in gate_results
        ])

        return f"""Analyze deployment readiness for release.

Deployment Mode: {deployment_mode}

Gate Results:
{gate_summary}

Failed Gates: {failed_gates if failed_gates else 'None'}

Provide:
1. Summary of deployment readiness
2. Assessment of failed gates (critical vs non-critical)
3. Policy-based recommendation for deployment approval/blocking"""

    async def run(
        self,
        release_id: str,
        release_context: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> ReleaseGuardianResult:
        """
        Run the Release Guardian Agent.

        Args:
            release_id: Release identifier
            release_context: Context dict with deployment info
            thread_id: Optional thread ID for checkpointing

        Returns:
            ReleaseGuardianResult with decision and actions taken
        """
        try:
            import time
            start_time = time.time()

            logger.info(f"[Release Guardian] Starting evaluation for {release_id}")

            # Determine deployment mode
            deployment_mode = DeploymentModeValidator.determine_mode(release_context)
            logger.info(f"[Release Guardian] Deployment mode: {deployment_mode}")

            # Initialize state
            initial_state: ReleaseGuardianState = {
                "messages": [
                    HumanMessage(content=f"Evaluate release {release_id} for deployment")
                ],
                "release_id": release_id,
                "deployment_mode": deployment_mode,
                "release_context": release_context,
                "gate_results": [],
                "passed_gates": [],
                "failed_gates": [],
                "deployment_approved": False,
                "deployment_blocked": False,
                "blocking_reason": None,
                "actions_executed": [],
                "release_report": None,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "error": None,
            }

            # Run graph
            config = {"configurable": {"thread_id": thread_id}} if thread_id else None
            final_state = await self.graph.ainvoke(initial_state, config=config)

            duration = time.time() - start_time

            # Build result
            result = ReleaseGuardianResult(
                release_id=release_id,
                deployment_approved=final_state.get("deployment_approved", False),
                deployment_mode=deployment_mode,
                gates_passed=len(final_state.get("passed_gates", [])),
                gates_failed=len(final_state.get("failed_gates", [])),
                actions_taken=final_state.get("actions_executed", []),
                report=final_state.get("release_report"),
                duration_seconds=duration,
                error=final_state.get("error"),
            )

            logger.info(
                f"[Release Guardian] Evaluation complete for {release_id}: "
                f"approved={result.deployment_approved}, "
                f"gates_passed={result.gates_passed}, "
                f"gates_failed={result.gates_failed}"
            )

            return result

        except Exception as e:
            logger.error(f"[Release Guardian] Evaluation error: {e}")
            return ReleaseGuardianResult(
                release_id=release_id,
                deployment_approved=False,
                deployment_mode="DEMO",
                gates_passed=0,
                gates_failed=0,
                actions_taken=[],
                report=None,
                duration_seconds=0,
                error=str(e),
            )
