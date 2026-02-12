"""
LangGraph Base Agent

Abstract base class for all ResearchFlow LangGraph agents.
Provides common infrastructure for graph building, quality gates,
human-in-the-loop, and improvement loop support.

All LLM calls route through the orchestrator's AI Router for PHI compliance.

Node-level audit events (NODE_STARTED, NODE_FINISHED, NODE_FAILED) are emitted
via the orchestrator audit client when orchestrator env is configured.

See: Linear ROS-64 (Phase A: Foundation)
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any, Dict, List
import hashlib
import json
import logging
import socket
import time
import uuid
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# LangSmith tracing (graceful degradation — never blocks execution)
try:
    from ...tracing.langsmith_config import get_tracer, redact_for_trace, TRACING_ENABLED
except ImportError:
    def get_tracer():  # type: ignore[misc]
        return None
    def redact_for_trace(data):  # type: ignore[misc]
        return data
    TRACING_ENABLED = False

from .state import (
    AgentState,
    AgentId,
    GateStatus,
    QualityGateResult,
    VersionSnapshot,
    Message,
    create_initial_state,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Node-level audit emission (defensive: no crash if orchestrator env missing)
# -----------------------------------------------------------------------------

def _get_actor_id() -> str:
    """Worker identity for audit: hostname or WORKER_ID env."""
    import os
    return os.environ.get("WORKER_ID", "").strip() or socket.gethostname() or "worker"


def _state_minimal(state: AgentState) -> Dict[str, Any]:
    """Minimal state for hashing; no raw content (no messages, current_output)."""
    return {
        "run_id": state.get("run_id"),
        "thread_id": state.get("thread_id"),
        "agent_id": state.get("agent_id"),
        "project_id": state.get("project_id"),
        "current_stage": state.get("current_stage"),
        "iteration": state.get("iteration"),
    }


def _content_hash(obj: Any) -> str:
    """SHA256 of canonical JSON representation (minimized, no raw content)."""
    try:
        canonical = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    except Exception:
        return ""


def _safe_emit_audit(event: Dict[str, Any]) -> None:
    """Emit audit event to orchestrator; on missing config or failure, log at debug only."""
    try:
        from ...clients.orchestrator_audit_client import emit_audit_event
        emit_audit_event(event)
    except ValueError as e:
        logger.debug("Audit emit skipped (config missing): %s", e)
    except Exception as e:
        logger.debug("Audit emit failed: %s", e)


def _emit_node_audit(
    state: AgentState,
    node_id: str,
    action: str,
    attempt: int,
    *,
    started_at_ms: Optional[int] = None,
    duration_ms: Optional[int] = None,
    error_class: Optional[str] = None,
    error_message: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
) -> None:
    """Emit a node-level audit event (NODE_STARTED, NODE_FINISHED, NODE_FAILED)."""
    run_id = state.get("run_id") or ""
    trace_id = state.get("trace_id") or run_id
    stream_key = run_id
    dedupe_key = f"{run_id}:{node_id}:{action}:{attempt}"
    payload: Dict[str, Any] = {
        "node_name": node_id,
        "attempt": attempt,
    }
    if started_at_ms is not None:
        payload["started_at_ms"] = started_at_ms
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if error_class:
        payload["error_class"] = error_class
    if error_message is not None:
        payload["error_message"] = (error_message or "")[:500]
    if input_hash:
        payload["input_hash"] = input_hash
    if output_hash:
        payload["output_hash"] = output_hash
    event = {
        "stream_type": "RUN",
        "stream_key": stream_key,
        "run_id": run_id,
        "trace_id": trace_id,
        "node_id": node_id,
        "action": action,
        "actor_type": "WORKER",
        "actor_id": _get_actor_id(),
        "service": "worker",
        "resource_type": "LANGGRAPH_NODE",
        "resource_id": node_id,
        "payload_json": payload,
        "dedupe_key": dedupe_key,
    }
    _safe_emit_audit(event)


class LangGraphBaseAgent(ABC):
    """
    Abstract base class for LangGraph-based agents.

    Provides:
    - Graph building infrastructure
    - Quality gate evaluation
    - Human-in-the-loop interrupts (for LIVE mode)
    - Improvement loop support
    - Checkpointing integration

    Subclasses must implement:
    - build_graph(): Define the agent's node/edge structure
    - get_quality_criteria(): Return criteria for quality gate evaluation
    """

    def __init__(
        self,
        llm_bridge: Any,  # AIRouterBridge instance
        stages: List[int],
        agent_id: AgentId,
        checkpointer: Optional[Any] = None,
    ):
        """
        Initialize the base agent.

        Args:
            llm_bridge: Bridge to orchestrator AI Router for LLM calls
            stages: List of workflow stages this agent handles
            agent_id: Agent type identifier
            checkpointer: LangGraph checkpointer (defaults to MemorySaver)
        """
        self.llm = llm_bridge
        self.stages = stages
        self.agent_id = agent_id
        self.stage_range = (min(stages), max(stages))

        # Use memory saver by default, replaced with Redis in production
        self.checkpointer = checkpointer or MemorySaver()

        # Compiled graph (lazy initialization)
        self._graph: Optional[Any] = None

        # LangSmith tracer (None if disabled or unavailable)
        self._tracer: Optional[Any] = None
        if TRACING_ENABLED:
            try:
                self._tracer = get_tracer()
                if self._tracer:
                    logger.info("LangSmith tracing enabled for agent %s", agent_id)
            except Exception as exc:
                logger.debug("LangSmith tracer init skipped: %s", exc)

    @property
    def graph(self) -> Any:
        """Get the compiled graph, building it if necessary."""
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """
        Build and compile the LangGraph state graph.

        Subclasses must implement this to define their specific
        node/edge structure.

        Returns:
            Compiled StateGraph with checkpointer
        """
        pass

    @abstractmethod
    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Return quality criteria for this agent's gate evaluation.

        Returns:
            Dict with criteria keys and threshold values
        """
        pass

    async def invoke(
        self,
        project_id: str,
        run_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        input_artifact_ids: Optional[List[str]] = None,
        initial_message: Optional[str] = None,
        governance_mode: str = 'DEMO',
        max_iterations: int = 5,
    ) -> AgentState:
        """
        Execute the agent graph.

        Args:
            project_id: Research project ID
            run_id: Unique run ID (generated if not provided)
            thread_id: Thread ID for checkpointing (generated if not provided)
            input_artifact_ids: List of input artifact IDs
            initial_message: Optional initial user message
            governance_mode: Current governance mode
            max_iterations: Max improvement iterations

        Returns:
            Final AgentState after graph execution
        """
        run_id = run_id or str(uuid.uuid4())
        thread_id = thread_id or str(uuid.uuid4())

        # Create initial state
        state = create_initial_state(
            agent_id=self.agent_id,
            project_id=project_id,
            run_id=run_id,
            thread_id=thread_id,
            stage_range=self.stage_range,
            governance_mode=governance_mode,
            input_artifact_ids=input_artifact_ids,
            max_iterations=max_iterations,
        )

        # Add initial message if provided
        if initial_message:
            state['messages'].append(Message(
                id=str(uuid.uuid4()),
                role='user',
                content=initial_message,
                timestamp=datetime.utcnow().isoformat(),
                phi_detected=False,
            ))

        # Configure for checkpointing
        config = {
            'configurable': {
                'thread_id': thread_id,
            }
        }

        logger.info(
            f"Starting {self.agent_id} agent run",
            extra={
                'run_id': run_id,
                'project_id': project_id,
                'stages': self.stages,
                'governance_mode': governance_mode,
            }
        )

        # Emit RUN_STARTED audit event
        _invoke_started_ms = int(time.time() * 1000)
        _invoke_input_hash = _content_hash(_state_minimal(state))
        _emit_node_audit(
            state, "__invoke__", "RUN_STARTED", 0,
            started_at_ms=_invoke_started_ms, input_hash=_invoke_input_hash,
        )

        # Execute graph
        try:
            result = await self.graph.ainvoke(state, config)
            _invoke_duration = int(time.time() * 1000) - _invoke_started_ms
            _emit_node_audit(
                result, "__invoke__", "RUN_FINISHED", 0,
                started_at_ms=_invoke_started_ms,
                duration_ms=_invoke_duration,
                input_hash=_invoke_input_hash,
                output_hash=_content_hash(_state_minimal(result)),
            )
            return result
        except Exception as e:
            _invoke_duration = int(time.time() * 1000) - _invoke_started_ms
            _emit_node_audit(
                state, "__invoke__", "RUN_FAILED", 0,
                started_at_ms=_invoke_started_ms,
                duration_ms=_invoke_duration,
                input_hash=_invoke_input_hash,
                error_class=type(e).__name__,
                error_message=str(e),
            )
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            raise

    async def resume(
        self,
        thread_id: str,
        approval: Optional[bool] = None,
        feedback: Optional[str] = None,
    ) -> AgentState:
        """
        Resume a paused agent execution (e.g., after human approval).

        Args:
            thread_id: Thread ID to resume
            approval: Whether the human approved (for LIVE mode)
            feedback: Optional feedback from human reviewer

        Returns:
            Final AgentState after resumed execution
        """
        config = {
            'configurable': {
                'thread_id': thread_id,
            }
        }

        # Get current state from checkpoint
        state = await self.graph.aget_state(config)

        if approval is not None:
            state.values['awaiting_approval'] = False
            if not approval:
                state.values['gate_status'] = 'failed'
                state.values['gate_result'] = QualityGateResult(
                    passed=False,
                    score=0.0,
                    criteria_met=[],
                    criteria_failed=['human_approval'],
                    reason='Rejected by human reviewer',
                    needs_human_review=False,
                )
                return state.values

        if feedback:
            state.values['feedback'] = feedback

        # Emit RESUME_STARTED audit event
        _resume_started_ms = int(time.time() * 1000)
        _resume_input_hash = _content_hash(_state_minimal(state.values))
        _emit_node_audit(
            state.values, "__resume__", "RESUME_STARTED", 0,
            started_at_ms=_resume_started_ms, input_hash=_resume_input_hash,
        )

        # Resume execution
        try:
            result = await self.graph.ainvoke(None, config)
            _resume_duration = int(time.time() * 1000) - _resume_started_ms
            _emit_node_audit(
                result, "__resume__", "RESUME_FINISHED", 0,
                started_at_ms=_resume_started_ms,
                duration_ms=_resume_duration,
                input_hash=_resume_input_hash,
                output_hash=_content_hash(_state_minimal(result)),
            )
            return result
        except Exception as e:
            _resume_duration = int(time.time() * 1000) - _resume_started_ms
            _emit_node_audit(
                state.values, "__resume__", "RESUME_FAILED", 0,
                started_at_ms=_resume_started_ms,
                duration_ms=_resume_duration,
                input_hash=_resume_input_hash,
                error_class=type(e).__name__,
                error_message=str(e),
            )
            raise

    # =========================================================================
    # Common Node Implementations
    # =========================================================================

    def quality_gate_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluate output against quality criteria.

        This is a common node that can be added to any agent graph.
        It evaluates the current output and sets gate_status/gate_score.

        Args:
            state: Current agent state

        Returns:
            State updates with gate_status and gate_result
        """
        node_id = "quality_gate"
        attempt = 0
        started_at_ms = int(time.time() * 1000)
        input_hash = _content_hash(_state_minimal(state))
        _emit_node_audit(
            state, node_id, "NODE_STARTED", attempt,
            started_at_ms=started_at_ms, input_hash=input_hash,
        )
        try:
            criteria = self.get_quality_criteria()
            output = state.get('current_output', '')

            # Evaluate each criterion
            criteria_met = []
            criteria_failed = []
            total_score = 0.0
            max_score = len(criteria)

            for criterion, threshold in criteria.items():
                passed, score = self._evaluate_criterion(criterion, threshold, output, state)
                if passed:
                    criteria_met.append(criterion)
                    total_score += score
                else:
                    criteria_failed.append(criterion)

            # Calculate final score
            final_score = total_score / max_score if max_score > 0 else 0.0

            # Determine gate status
            if final_score >= 0.8:
                gate_status: GateStatus = 'passed'
                needs_human = False
            elif final_score >= 0.5:
                gate_status = 'needs_human'
                needs_human = True
            else:
                gate_status = 'failed'
                needs_human = False

            # In LIVE mode, require human review for certain criteria
            if state.get('governance_mode') == 'LIVE' and self.agent_id in ['irb', 'manuscript']:
                needs_human = True
                if gate_status == 'passed':
                    gate_status = 'needs_human'

            gate_result = QualityGateResult(
                passed=gate_status == 'passed',
                score=final_score,
                criteria_met=criteria_met,
                criteria_failed=criteria_failed,
                reason=f"Score: {final_score:.2f}, {len(criteria_met)}/{len(criteria)} criteria met",
                needs_human_review=needs_human,
            )

            logger.info(
                f"Quality gate evaluated: {gate_status}",
                extra={
                    'agent_id': state.get('agent_id'),
                    'run_id': state.get('run_id'),
                    'score': final_score,
                    'criteria_met': criteria_met,
                    'criteria_failed': criteria_failed,
                }
            )

            result = {
                'gate_status': gate_status,
                'gate_score': final_score,
                'gate_result': gate_result,
                'awaiting_approval': needs_human,
            }
            duration_ms = int(time.time() * 1000) - started_at_ms
            output_minimal = {
                "gate_status": gate_status,
                "score": final_score,
                "criteria_met_count": len(criteria_met),
                "criteria_failed_count": len(criteria_failed),
            }
            _emit_node_audit(
                state, node_id, "NODE_FINISHED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash, output_hash=_content_hash(output_minimal),
            )
            return result
        except Exception as e:
            duration_ms = int(time.time() * 1000) - started_at_ms
            _emit_node_audit(
                state, node_id, "NODE_FAILED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash,
                error_class=type(e).__name__,
                error_message=str(e),
            )
            raise

    def _evaluate_criterion(
        self,
        criterion: str,
        threshold: Any,
        output: str,
        state: AgentState,
    ) -> tuple[bool, float]:
        """
        Evaluate a single quality criterion.

        Override in subclasses for custom evaluation logic.

        Args:
            criterion: Criterion name
            threshold: Threshold value for passing
            output: Current output to evaluate
            state: Full agent state

        Returns:
            Tuple of (passed, score) where score is 0.0-1.0
        """
        # Default implementation - override in subclasses
        if criterion == 'min_length' and isinstance(threshold, int):
            actual = len(output)
            passed = actual >= threshold
            score = min(1.0, actual / threshold) if threshold > 0 else 1.0
            return passed, score

        if criterion == 'max_length' and isinstance(threshold, int):
            actual = len(output)
            passed = actual <= threshold
            score = 1.0 if passed else max(0.0, 1.0 - (actual - threshold) / threshold)
            return passed, score

        # Default: pass with full score
        return True, 1.0

    def human_review_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Prepare for human review (LIVE mode interrupt).

        This node sets up the state for human-in-the-loop approval.
        The graph will pause here until resume() is called.

        Args:
            state: Current agent state

        Returns:
            State updates for human review
        """
        node_id = "human_review"
        attempt = 0
        started_at_ms = int(time.time() * 1000)
        input_hash = _content_hash(_state_minimal(state))
        _emit_node_audit(
            state, node_id, "NODE_STARTED", attempt,
            started_at_ms=started_at_ms, input_hash=input_hash,
        )
        try:
            approval_request_id = str(uuid.uuid4())

            logger.info(
                f"Human review requested",
                extra={
                    'agent_id': state.get('agent_id'),
                    'run_id': state.get('run_id'),
                    'approval_request_id': approval_request_id,
                    'governance_mode': state.get('governance_mode'),
                }
            )

            result = {
                'awaiting_approval': True,
                'approval_request_id': approval_request_id,
            }
            duration_ms = int(time.time() * 1000) - started_at_ms
            output_minimal = {"approval_request_id": approval_request_id}
            _emit_node_audit(
                state, node_id, "NODE_FINISHED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash, output_hash=_content_hash(output_minimal),
            )
            return result
        except Exception as e:
            duration_ms = int(time.time() * 1000) - started_at_ms
            _emit_node_audit(
                state, node_id, "NODE_FAILED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash,
                error_class=type(e).__name__,
                error_message=str(e),
            )
            raise

    def save_version_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Save current output as a version snapshot for improvement tracking.

        Args:
            state: Current agent state

        Returns:
            State updates with new version in previous_versions
        """
        node_id = "save_version"
        attempt = 0
        started_at_ms = int(time.time() * 1000)
        input_hash = _content_hash(_state_minimal(state))
        _emit_node_audit(
            state, node_id, "NODE_STARTED", attempt,
            started_at_ms=started_at_ms, input_hash=input_hash,
        )
        try:
            version = VersionSnapshot(
                version_id=f"v{len(state.get('previous_versions', [])) + 1}",
                timestamp=datetime.utcnow().isoformat(),
                output=state.get('current_output', ''),
                quality_score=state.get('gate_score', 0.0),
                improvement_request=state.get('feedback'),
                changes=[],  # Populated by diff service
            )

            previous_versions = state.get('previous_versions', []).copy()
            previous_versions.append(version)
            new_iteration = state.get('iteration', 0) + 1

            result = {
                'previous_versions': previous_versions,
                'iteration': new_iteration,
                'feedback': None,  # Clear feedback after saving
            }
            duration_ms = int(time.time() * 1000) - started_at_ms
            output_minimal = {"version_id": version["version_id"], "iteration": new_iteration}
            _emit_node_audit(
                state, node_id, "NODE_FINISHED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash, output_hash=_content_hash(output_minimal),
            )
            return result
        except Exception as e:
            duration_ms = int(time.time() * 1000) - started_at_ms
            _emit_node_audit(
                state, node_id, "NODE_FAILED", attempt,
                started_at_ms=started_at_ms, duration_ms=duration_ms,
                input_hash=input_hash,
                error_class=type(e).__name__,
                error_message=str(e),
            )
            raise

    # =========================================================================
    # Routing Functions
    # =========================================================================

    def should_continue_improvement(self, state: AgentState) -> str:
        """
        Determine whether to continue improvement loop.

        Args:
            state: Current agent state

        Returns:
            'continue' to keep improving, 'complete' to finish
        """
        # Check if improvement is enabled
        if not state.get('improvement_enabled', True):
            return 'complete'

        # Check iteration limit
        if state.get('iteration', 0) >= state.get('max_iterations', 5):
            logger.info("Max iterations reached, completing")
            return 'complete'

        # Check quality gate
        if state.get('gate_status') == 'passed':
            return 'complete'

        # Check if there's feedback to apply
        if state.get('feedback'):
            return 'continue'

        return 'complete'

    def should_require_human_review(self, state: AgentState) -> str:
        """
        Determine if human review is required.

        Args:
            state: Current agent state

        Returns:
            'human_review' or 'continue'
        """
        # LIVE mode requires review for certain agents
        if state.get('governance_mode') == 'LIVE':
            if self.agent_id in ['irb', 'manuscript']:
                return 'human_review'

        # Quality gate requested human review
        gate_result = state.get('gate_result')
        if gate_result and gate_result.get('needs_human_review'):
            return 'human_review'

        return 'continue'

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _get_langsmith_callbacks(self) -> List[Any]:
        """Return LangSmith callback list (empty if tracing disabled)."""
        return [self._tracer] if self._tracer else []

    @staticmethod
    def _redact_for_trace(data: Any) -> Any:
        """Strip PHI patterns from data before sending to LangSmith traces."""
        return redact_for_trace(data)

    async def call_llm(
        self,
        prompt: str,
        task_type: str,
        state: AgentState,
        model_tier: str = 'STANDARD',
    ) -> str:
        """
        Call LLM through the AI Router bridge.

        All LLM calls should use this method to ensure PHI compliance.

        Args:
            prompt: The prompt to send
            task_type: Type of task (for routing/logging)
            state: Current agent state
            model_tier: Model tier to use (ECONOMY/STANDARD/PREMIUM)

        Returns:
            LLM response content
        """
        # Import here to avoid circular imports
        from ...bridges.ai_router_bridge import ModelOptions, ModelTier, GovernanceMode
        
        # Convert tier string to enum
        tier_map = {
            'ECONOMY': ModelTier.ECONOMY,
            'STANDARD': ModelTier.STANDARD, 
            'PREMIUM': ModelTier.PREMIUM,
            'MINI': ModelTier.ECONOMY,      # Legacy mapping
            'NANO': ModelTier.ECONOMY,      # Legacy mapping
            'FRONTIER': ModelTier.PREMIUM,  # Legacy mapping
        }
        
        tier = tier_map.get(model_tier.upper(), ModelTier.STANDARD)
        
        # Convert governance mode
        gov_mode_str = state.get('governance_mode', 'DEMO')
        governance_mode = GovernanceMode(gov_mode_str) if gov_mode_str in ['DEMO', 'LIVE', 'STANDBY'] else GovernanceMode.DEMO
        
        # Create model options
        options = ModelOptions(
            task_type=task_type,
            stage_id=state.get('current_stage', self.stages[0]),
            model_tier=tier,
            governance_mode=governance_mode,
            require_phi_compliance=governance_mode == GovernanceMode.LIVE,
        )
        
        # Make the call
        response = await self.llm.invoke(prompt, options)

        # Update token count in state
        current_tokens = state.get('token_count', 0)
        state['token_count'] = current_tokens + response.usage.total_tokens

        return response.content

    def add_assistant_message(self, state: AgentState, content: str) -> Message:
        """
        Create and add an assistant message to state.

        Args:
            state: Current agent state
            content: Message content

        Returns:
            The created Message
        """
        message = Message(
            id=str(uuid.uuid4()),
            role='assistant',
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            phi_detected=False,  # PHI scanning done by AI Router
        )
        return message
