"""
Human-in-the-Loop Handler for LangGraph Agents.

Provides functionality for:
- Pausing agent execution for human review
- Emitting SSE events to frontend
- Waiting for approval callbacks
- Resuming or aborting based on human decision

All human-in-the-loop interactions are audited.

See: Linear ROS-66, ROS-67 (Phase C & D)
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
import json

import httpx

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of a human-in-the-loop approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class HumanLoopRequest:
    """
    A request for human review/approval.

    Attributes:
        request_id: Unique request identifier
        session_id: Chat session ID
        agent_id: Agent requesting review
        stage_id: Current workflow stage
        action_type: Type of action requiring review
        summary: Human-readable summary
        details: Detailed information for review
        required_permissions: Permissions needed to approve
        timeout_seconds: Timeout for approval (0 = no timeout)
        created_at: Request creation timestamp
        status: Current approval status
    """
    request_id: str
    session_id: str
    agent_id: str
    stage_id: int
    action_type: str
    summary: str
    details: Dict[str, Any]
    required_permissions: List[str] = field(default_factory=list)
    timeout_seconds: int = 300  # 5 minute default
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: ApprovalStatus = ApprovalStatus.PENDING


@dataclass
class HumanLoopResponse:
    """
    Response from a human reviewer.

    Attributes:
        request_id: Request this responds to
        approved: Whether the action was approved
        feedback: Optional feedback from reviewer
        reviewer_id: ID of the reviewer
        reviewed_at: Review timestamp
    """
    request_id: str
    approved: bool
    feedback: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class HumanLoopHandler:
    """
    Handler for human-in-the-loop interrupts in LangGraph agents.

    Provides:
    - Request creation and tracking
    - SSE event emission
    - Async waiting for approval
    - Timeout handling
    - Response processing
    """

    def __init__(
        self,
        orchestrator_url: str,
        auth_token: Optional[str] = None,
        default_timeout: int = 300,
    ):
        """
        Initialize the human loop handler.

        Args:
            orchestrator_url: URL of the orchestrator service
            auth_token: Optional authentication token
            default_timeout: Default timeout in seconds
        """
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.auth_token = auth_token
        self.default_timeout = default_timeout
        self._pending_requests: Dict[str, HumanLoopRequest] = {}
        self._response_events: Dict[str, asyncio.Event] = {}
        self._responses: Dict[str, HumanLoopResponse] = {}

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for orchestrator requests."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def request_approval(
        self,
        session_id: str,
        agent_id: str,
        stage_id: int,
        action_type: str,
        summary: str,
        details: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
        required_permissions: Optional[List[str]] = None,
    ) -> HumanLoopResponse:
        """
        Request human approval for an action.

        This method:
        1. Creates an approval request
        2. Sends SSE event to frontend
        3. Waits for response (with timeout)
        4. Returns the response

        Args:
            session_id: Chat session ID
            agent_id: Agent requesting approval
            stage_id: Current workflow stage
            action_type: Type of action (e.g., 'irb_submit', 'data_modify')
            summary: Human-readable summary of what needs approval
            details: Detailed information for reviewer
            timeout_seconds: Timeout for approval
            required_permissions: Permissions needed to approve

        Returns:
            HumanLoopResponse with approval decision
        """
        request_id = f"hlr_{session_id}_{datetime.utcnow().timestamp()}"
        timeout = timeout_seconds or self.default_timeout

        request = HumanLoopRequest(
            request_id=request_id,
            session_id=session_id,
            agent_id=agent_id,
            stage_id=stage_id,
            action_type=action_type,
            summary=summary,
            details=details,
            required_permissions=required_permissions or [],
            timeout_seconds=timeout,
        )

        # Store request and create wait event
        self._pending_requests[request_id] = request
        self._response_events[request_id] = asyncio.Event()

        logger.info(
            f"Human approval requested",
            extra={
                "request_id": request_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "action_type": action_type,
            }
        )

        # Send SSE event to frontend
        await self._send_approval_request(request)

        # Wait for response with timeout
        try:
            response = await self._wait_for_response(request_id, timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Approval request timed out: {request_id}")
            request.status = ApprovalStatus.TIMEOUT
            return HumanLoopResponse(
                request_id=request_id,
                approved=False,
                feedback="Request timed out waiting for human approval",
            )
        finally:
            # Cleanup
            self._pending_requests.pop(request_id, None)
            self._response_events.pop(request_id, None)
            self._responses.pop(request_id, None)

    async def handle_response(self, response: HumanLoopResponse) -> bool:
        """
        Handle a response from a human reviewer.

        Called by the API when a reviewer submits their decision.

        Args:
            response: The reviewer's response

        Returns:
            True if request was found and processed
        """
        request_id = response.request_id

        if request_id not in self._pending_requests:
            logger.warning(f"Response for unknown request: {request_id}")
            return False

        # Update request status
        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.APPROVED if response.approved else ApprovalStatus.REJECTED

        # Store response and signal waiting task
        self._responses[request_id] = response
        event = self._response_events.get(request_id)
        if event:
            event.set()

        logger.info(
            f"Human approval {'approved' if response.approved else 'rejected'}",
            extra={
                "request_id": request_id,
                "reviewer_id": response.reviewer_id,
                "has_feedback": bool(response.feedback),
            }
        )

        return True

    async def _send_approval_request(self, request: HumanLoopRequest) -> None:
        """Send approval request to frontend via SSE."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.orchestrator_url}/api/chat/stream/{request.session_id}/event",
                    headers=self._get_headers(),
                    json={
                        "event": "approval_required",
                        "data": {
                            "requestId": request.request_id,
                            "agentId": request.agent_id,
                            "stageId": request.stage_id,
                            "actionType": request.action_type,
                            "summary": request.summary,
                            "details": request.details,
                            "requiredPermissions": request.required_permissions,
                            "timeoutSeconds": request.timeout_seconds,
                            "createdAt": request.created_at,
                        },
                    },
                )
        except Exception as e:
            logger.error(f"Failed to send approval request to frontend: {e}")

    async def _wait_for_response(
        self,
        request_id: str,
        timeout_seconds: int,
    ) -> HumanLoopResponse:
        """Wait for a response with timeout."""
        event = self._response_events.get(request_id)
        if not event:
            raise ValueError(f"No event for request: {request_id}")

        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)

        response = self._responses.get(request_id)
        if not response:
            raise ValueError(f"No response stored for request: {request_id}")

        return response

    def get_pending_requests(
        self,
        session_id: Optional[str] = None,
    ) -> List[HumanLoopRequest]:
        """
        Get pending approval requests.

        Args:
            session_id: Optional filter by session

        Returns:
            List of pending requests
        """
        requests = list(self._pending_requests.values())
        if session_id:
            requests = [r for r in requests if r.session_id == session_id]
        return requests

    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending approval request.

        Args:
            request_id: Request to cancel

        Returns:
            True if request was found and cancelled
        """
        if request_id not in self._pending_requests:
            return False

        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.ERROR

        # Signal with rejection
        self._responses[request_id] = HumanLoopResponse(
            request_id=request_id,
            approved=False,
            feedback="Request cancelled",
        )
        event = self._response_events.get(request_id)
        if event:
            event.set()

        return True


def create_human_loop_handler(
    orchestrator_url: str = "http://localhost:4000",
    auth_token: Optional[str] = None,
    default_timeout: int = 300,
) -> HumanLoopHandler:
    """
    Factory function to create a human loop handler.

    Args:
        orchestrator_url: URL of the orchestrator service
        auth_token: Optional authentication token
        default_timeout: Default timeout in seconds

    Returns:
        Configured HumanLoopHandler instance
    """
    return HumanLoopHandler(
        orchestrator_url=orchestrator_url,
        auth_token=auth_token,
        default_timeout=default_timeout,
    )


# =============================================================================
# Action Types for Human Review
# =============================================================================

class HumanReviewActions:
    """Standard action types that require human review."""

    # IRB Actions (ALWAYS require review)
    IRB_PROTOCOL_SUBMIT = "irb_protocol_submit"
    IRB_CONSENT_APPROVE = "irb_consent_approve"
    IRB_AMENDMENT_SUBMIT = "irb_amendment_submit"

    # Data Actions (LIVE mode)
    DATA_MODIFY = "data_modify"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"

    # Analysis Actions (LIVE mode)
    ANALYSIS_PUBLISH = "analysis_publish"
    ANALYSIS_RERUN = "analysis_rerun"

    # Manuscript Actions
    MANUSCRIPT_SUBMIT = "manuscript_submit"
    MANUSCRIPT_PUBLISH = "manuscript_publish"

    # Quality Gate Actions
    QUALITY_GATE_OVERRIDE = "quality_gate_override"
    QUALITY_GATE_SKIP = "quality_gate_skip"


def requires_human_review(
    action_type: str,
    governance_mode: str,
    agent_id: str,
) -> bool:
    """
    Check if an action requires human review.

    Args:
        action_type: Type of action
        governance_mode: Current governance mode (DEMO/REVIEW/LIVE)
        agent_id: Agent performing the action

    Returns:
        True if human review is required
    """
    # IRB always requires review
    if agent_id == 'irb':
        return True

    # In DEMO mode, no human review required
    if governance_mode == 'DEMO':
        return False

    # In LIVE mode, specific actions require review
    live_review_actions = {
        HumanReviewActions.DATA_MODIFY,
        HumanReviewActions.DATA_DELETE,
        HumanReviewActions.ANALYSIS_PUBLISH,
        HumanReviewActions.MANUSCRIPT_SUBMIT,
        HumanReviewActions.MANUSCRIPT_PUBLISH,
        HumanReviewActions.QUALITY_GATE_OVERRIDE,
    }

    if governance_mode == 'LIVE' and action_type in live_review_actions:
        return True

    # In REVIEW mode, most modification actions require review
    if governance_mode == 'REVIEW':
        review_actions = live_review_actions | {
            HumanReviewActions.DATA_EXPORT,
            HumanReviewActions.ANALYSIS_RERUN,
        }
        return action_type in review_actions

    return False
