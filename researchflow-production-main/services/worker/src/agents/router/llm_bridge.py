"""
AI Router Bridge

Routes all LLM calls from Python worker agents through the TypeScript
orchestrator's AI Router for PHI compliance, audit logging, and cost tracking.

This bridge ensures that:
1. All prompts are PHI-scanned before reaching the LLM
2. Model tier routing is consistent with governance policies
3. Usage is logged for cost tracking and compliance
4. DEMO/LIVE mode restrictions are enforced

See: Linear ROS-64 (Phase A: Foundation - AI Router Bridge)
"""

import os
import logging
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Type aliases
ModelTier = Literal['NANO', 'MINI', 'STANDARD', 'FRONTIER']
GovernanceMode = Literal['DEMO', 'LIVE', 'STANDBY']


@dataclass
class LLMResponse:
    """Response from AI Router."""
    content: str
    model: str
    usage: Dict[str, int]
    phi_detected: bool
    phi_redacted: bool
    cost_usd: float
    latency_ms: int


class AIRouterBridge:
    """
    Bridge to orchestrator's AI Router for LLM calls.

    All agent LLM calls should go through this bridge to ensure
    PHI compliance and proper governance enforcement.

    Usage:
        bridge = AIRouterBridge()
        response = await bridge.invoke(
            prompt="Analyze this clinical data...",
            task_type="data_analysis",
            stage_id=6,
            model_tier="STANDARD",
        )
    """

    def __init__(
        self,
        orchestrator_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        """
        Initialize the AI Router bridge.

        Args:
            orchestrator_url: URL of the orchestrator service
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on failure
        """
        self.orchestrator_url = orchestrator_url or os.getenv(
            'ORCHESTRATOR_URL',
            'http://orchestrator:3001'
        )
        self.base_url = f"{self.orchestrator_url}/api/ai/agent-proxy"
        self.timeout = timeout
        self.max_retries = max_retries

        # Service token for inter-service auth
        self.service_token = os.getenv('WORKER_SERVICE_TOKEN', '')

        logger.info(f"AIRouterBridge initialized with URL: {self.orchestrator_url}")

    async def invoke(
        self,
        prompt: str,
        task_type: str,
        stage_id: int,
        model_tier: ModelTier = 'STANDARD',
        governance_mode: GovernanceMode = 'DEMO',
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invoke LLM through the AI Router.

        Args:
            prompt: The user prompt to send
            task_type: Type of task for routing/logging
            stage_id: Current workflow stage (1-20)
            model_tier: Model tier to use
            governance_mode: Current governance mode
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum response tokens
            metadata: Additional metadata for logging

        Returns:
            Dict with 'content', 'usage', 'model', etc.

        Raises:
            AIRouterError: On routing or LLM errors
            httpx.TimeoutException: On request timeout
        """
        payload = {
            'prompt': prompt,
            'taskType': task_type,
            'stageId': stage_id,
            'modelTier': model_tier,
            'governanceMode': governance_mode,
            'temperature': temperature,
        }

        if system_prompt:
            payload['systemPrompt'] = system_prompt

        if max_tokens:
            payload['maxTokens'] = max_tokens

        if metadata:
            payload['metadata'] = metadata

        headers = {
            'Content-Type': 'application/json',
            'X-Service-Name': 'worker',
        }

        if self.service_token:
            headers['Authorization'] = f'Bearer {self.service_token}'

        # Retry loop
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        json=payload,
                        headers=headers,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        logger.debug(
                            f"LLM call successful",
                            extra={
                                'task_type': task_type,
                                'stage_id': stage_id,
                                'model': result.get('model'),
                                'tokens': result.get('usage', {}).get('total_tokens'),
                            }
                        )
                        return result

                    # Handle specific error codes
                    if response.status_code == 403:
                        error_data = response.json()
                        raise AIRouterError(
                            f"PHI detected and blocked: {error_data.get('message')}",
                            code='PHI_BLOCKED',
                            details=error_data,
                        )

                    if response.status_code == 429:
                        raise AIRouterError(
                            "Rate limit exceeded",
                            code='RATE_LIMITED',
                        )

                    if response.status_code == 503:
                        # Service unavailable, retry
                        logger.warning(f"AI Router unavailable, attempt {attempt + 1}")
                        last_error = AIRouterError(
                            "AI Router temporarily unavailable",
                            code='SERVICE_UNAVAILABLE',
                        )
                        continue

                    # Other errors
                    error_data = response.json() if response.content else {}
                    raise AIRouterError(
                        f"AI Router error: {response.status_code}",
                        code='ROUTER_ERROR',
                        details=error_data,
                    )

            except httpx.TimeoutException:
                logger.warning(f"Request timeout, attempt {attempt + 1}")
                last_error = AIRouterError(
                    f"Request timeout after {self.timeout}s",
                    code='TIMEOUT',
                )
                continue

            except httpx.ConnectError as e:
                logger.warning(f"Connection error, attempt {attempt + 1}: {e}")
                last_error = AIRouterError(
                    f"Cannot connect to AI Router: {e}",
                    code='CONNECTION_ERROR',
                )
                continue

        # All retries exhausted
        raise last_error or AIRouterError("Unknown error", code='UNKNOWN')

    async def invoke_streaming(
        self,
        prompt: str,
        task_type: str,
        stage_id: int,
        model_tier: ModelTier = 'STANDARD',
        governance_mode: GovernanceMode = 'DEMO',
        **kwargs,
    ):
        """
        Invoke LLM with streaming response.

        Yields chunks of the response as they arrive.

        Args:
            Same as invoke()

        Yields:
            Dict chunks with 'content' and 'done' fields
        """
        payload = {
            'prompt': prompt,
            'taskType': task_type,
            'stageId': stage_id,
            'modelTier': model_tier,
            'governanceMode': governance_mode,
            'stream': True,
            **kwargs,
        }

        headers = {
            'Content-Type': 'application/json',
            'X-Service-Name': 'worker',
            'Accept': 'text/event-stream',
        }

        if self.service_token:
            headers['Authorization'] = f'Bearer {self.service_token}'

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                'POST',
                f"{self.base_url}/stream",
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise AIRouterError(
                        f"Streaming error: {error_text.decode()}",
                        code='STREAM_ERROR',
                    )

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        import json
                        chunk = json.loads(line[6:])
                        yield chunk
                        if chunk.get('done'):
                            break

    async def health_check(self) -> bool:
        """
        Check if AI Router is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.orchestrator_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


class AIRouterError(Exception):
    """Error from AI Router."""

    def __init__(
        self,
        message: str,
        code: str = 'UNKNOWN',
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


# Singleton instance for convenience
_default_bridge: Optional[AIRouterBridge] = None


def get_llm_bridge() -> AIRouterBridge:
    """Get the default AIRouterBridge instance."""
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = AIRouterBridge()
    return _default_bridge
