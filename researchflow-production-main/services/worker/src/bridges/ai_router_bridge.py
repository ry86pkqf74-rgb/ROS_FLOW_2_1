"""
AI Router Bridge - Python Client

Python wrapper for communicating with the TypeScript AI Router Bridge.
This allows LangGraph agents to make LLM calls through the orchestrator.

Features:
- Async HTTP client for bridge communication
- Automatic model tier selection
- PHI compliance enforcement
- Cost tracking and budget management
- Error handling with retries
- Streaming support (future)
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from httpx import AsyncClient, TimeoutException, HTTPStatusError

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tier options"""
    ECONOMY = "ECONOMY"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class GovernanceMode(Enum):
    """Governance mode options"""
    DEMO = "DEMO"
    LIVE = "LIVE"
    STANDBY = "STANDBY"


@dataclass
class ModelOptions:
    """Options for LLM model selection"""
    task_type: str
    stage_id: Optional[int] = None
    model_tier: Optional[ModelTier] = None
    governance_mode: Optional[GovernanceMode] = None
    require_phi_compliance: Optional[bool] = None
    budget_limit: Optional[float] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream_response: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling enums"""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                if isinstance(value, Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        return result


@dataclass
class TokenUsage:
    """Token usage statistics"""
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


@dataclass
class CostBreakdown:
    """Cost breakdown"""
    total: float
    input: float
    output: float


@dataclass
class LLMResponse:
    """Response from LLM call"""
    content: str
    usage: TokenUsage
    cost: CostBreakdown
    model: str
    tier: str
    finish_reason: str
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMResponse':
        """Create from dictionary response"""
        return cls(
            content=data['content'],
            usage=TokenUsage(**data['usage']),
            cost=CostBreakdown(**data['cost']),
            model=data['model'],
            tier=data['tier'],
            finish_reason=data['finishReason'],
            metadata=data.get('metadata')
        )


@dataclass
class BridgeConfig:
    """Configuration for AI Router Bridge"""
    orchestrator_url: str = "http://localhost:3001"
    default_tier: ModelTier = ModelTier.STANDARD
    phi_compliant_only: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    cost_tracking_enabled: bool = True
    streaming_enabled: bool = False


class AIRouterBridgeError(Exception):
    """Base exception for bridge errors"""
    def __init__(self, message: str, code: str = None, details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


class RoutingError(AIRouterBridgeError):
    """Error in model routing"""
    pass


class LLMCallError(AIRouterBridgeError):
    """Error in LLM call"""
    pass


class BudgetExceededError(AIRouterBridgeError):
    """Budget limit exceeded"""
    pass


class PHIComplianceError(AIRouterBridgeError):
    """PHI compliance violation"""
    pass


class AIRouterBridge:
    """
    Python client for AI Router Bridge
    
    Handles communication between LangGraph agents and the
    TypeScript AI Router service.
    """
    
    def __init__(self, config: Optional[BridgeConfig] = None):
        """Initialize bridge with configuration"""
        self.config = config or BridgeConfig()
        self.client: Optional[AsyncClient] = None
        self.total_cost = 0.0
        self.request_count = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP client"""
        if self.client is None:
            timeout = httpx.Timeout(self.config.timeout_seconds)
            self.client = AsyncClient(timeout=timeout)
            
    async def close(self):
        """Close HTTP client"""
        if self.client is not None:
            await self.client.aclose()
            self.client = None
    
    async def invoke(
        self, 
        prompt: str, 
        options: Optional[ModelOptions] = None
    ) -> LLMResponse:
        """
        Single LLM invocation
        
        Args:
            prompt: The prompt to send to the LLM
            options: Model options (defaults to general task)
            
        Returns:
            LLM response with content, usage, and cost
        """
        if options is None:
            options = ModelOptions(task_type="general")
            
        await self.connect()
        
        # Convert options to request format
        request_data = {
            "prompt": prompt,
            "options": options.to_dict()
        }
        
        last_error = None
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = await self.client.post(
                    f"{self.config.orchestrator_url}/api/ai-bridge/invoke",
                    json=request_data
                )
                response.raise_for_status()
                
                # Parse response
                response_data = response.json()
                llm_response = LLMResponse.from_dict(response_data)
                
                # Track costs
                if self.config.cost_tracking_enabled:
                    self.total_cost += llm_response.cost.total
                    self.request_count += 1
                
                logger.info(
                    f"LLM call successful",
                    extra={
                        "task_type": options.task_type,
                        "model": llm_response.model,
                        "tier": llm_response.tier,
                        "tokens": llm_response.usage.total_tokens,
                        "cost": llm_response.cost.total,
                        "attempt": attempt
                    }
                )
                
                return llm_response
                
            except HTTPStatusError as e:
                last_error = e
                
                if e.response.status_code == 400:
                    error_data = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else {}
                    error_code = error_data.get('error', 'VALIDATION_ERROR')
                    
                    if error_code == 'BUDGET_INSUFFICIENT':
                        raise BudgetExceededError(
                            error_data.get('message', 'Budget exceeded'),
                            details=error_data
                        )
                    elif error_code == 'PHI_COMPLIANCE_VIOLATION':
                        raise PHIComplianceError(
                            error_data.get('message', 'PHI compliance violation'),
                            details=error_data
                        )
                    else:
                        raise LLMCallError(
                            f"LLM call failed: {error_data.get('message', str(e))}",
                            code=error_code,
                            details=error_data
                        )
                        
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise LLMCallError(f"Client error: {e}", details=e.response.text)
                
                # Server errors (5xx) - retry with backoff
                if attempt < self.config.max_retries:
                    wait_time = min(2 ** attempt, 60)  # Exponential backoff, max 60s
                    logger.warning(
                        f"LLM call attempt {attempt} failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    
            except (TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                last_error = e
                
                if attempt < self.config.max_retries:
                    wait_time = min(2 ** attempt, 60)
                    logger.warning(
                        f"LLM call attempt {attempt} failed, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                # Unexpected errors - don't retry
                raise LLMCallError(f"Unexpected error: {e}", details=str(e))
        
        # All retries exhausted
        raise LLMCallError(
            f"Max retries ({self.config.max_retries}) exceeded",
            details=str(last_error)
        )
    
    async def batch_invoke(
        self, 
        prompts: List[str], 
        options: Optional[ModelOptions] = None
    ) -> List[LLMResponse]:
        """
        Batch LLM invocation
        
        Args:
            prompts: List of prompts to process
            options: Model options for all prompts
            
        Returns:
            List of LLM responses
        """
        if options is None:
            options = ModelOptions(task_type="general")
            
        await self.connect()
        
        request_data = {
            "prompts": prompts,
            "options": options.to_dict()
        }
        
        response = await self.client.post(
            f"{self.config.orchestrator_url}/api/ai-bridge/batch",
            json=request_data
        )
        response.raise_for_status()
        
        # Parse batch response
        response_data = response.json()
        results = []
        
        for item in response_data.get('responses', []):
            try:
                results.append(LLMResponse.from_dict(item))
            except Exception as e:
                logger.warning(f"Failed to parse batch response item: {e}")
                # Add error response
                results.append(LLMResponse(
                    content="Error: Failed to parse response",
                    usage=TokenUsage(0, 0, 0),
                    cost=CostBreakdown(0, 0, 0),
                    model="unknown",
                    tier="unknown",
                    finish_reason="error",
                    metadata={"parse_error": str(e)}
                ))
        
        # Update cost tracking
        if self.config.cost_tracking_enabled:
            batch_cost = sum(r.cost.total for r in results)
            self.total_cost += batch_cost
            self.request_count += len(prompts)
        
        return results
    
    async def stream_invoke(
        self, 
        prompt: str, 
        options: Optional[ModelOptions] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming LLM invocation
        
        Args:
            prompt: The prompt to send
            options: Model options
            
        Yields:
            Streaming content chunks
        """
        if not self.config.streaming_enabled:
            raise AIRouterBridgeError("Streaming is not enabled")
            
        if options is None:
            options = ModelOptions(task_type="general", stream_response=True)
        else:
            options.stream_response = True
            
        await self.connect()
        
        request_data = {
            "prompt": prompt,
            "options": options.to_dict()
        }
        
        async with self.client.stream(
            "POST",
            f"{self.config.orchestrator_url}/api/ai-bridge/stream",
            json=request_data
        ) as response:
            response.raise_for_status()
            
            content_chunks = []
            
            async for chunk in response.aiter_text():
                if chunk.startswith("data: "):
                    data_str = chunk[6:]  # Remove "data: " prefix
                    
                    if data_str.strip() == "[DONE]":
                        break
                        
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            yield data["content"]
                    except json.JSONDecodeError:
                        # Skip invalid JSON chunks
                        continue
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check bridge and orchestrator health
        
        Returns:
            Health status dictionary
        """
        await self.connect()
        
        try:
            response = await self.client.get(
                f"{self.config.orchestrator_url}/health",
                timeout=5.0
            )
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "orchestrator_reachable": True,
                    "ai_router_available": health_data.get("services", {}).get("ai_router") == "healthy",
                    "latency_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "status": "unhealthy",
                    "orchestrator_reachable": True,
                    "ai_router_available": False,
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "orchestrator_reachable": False,
                "ai_router_available": False,
                "latency_ms": None,
                "error": str(e)
            }
    
    def get_cost_stats(self) -> Dict[str, float]:
        """
        Get cost tracking statistics
        
        Returns:
            Dictionary with cost statistics
        """
        return {
            "total_cost": self.total_cost,
            "request_count": self.request_count,
            "average_cost_per_request": (
                self.total_cost / self.request_count 
                if self.request_count > 0 
                else 0.0
            )
        }
    
    def reset_cost_tracking(self) -> None:
        """Reset cost tracking counters"""
        self.total_cost = 0.0
        self.request_count = 0


# Factory function
def create_ai_router_bridge(
    orchestrator_url: str = None,
    **kwargs
) -> AIRouterBridge:
    """
    Factory function to create AI Router Bridge
    
    Args:
        orchestrator_url: URL of the orchestrator service
        **kwargs: Additional config options
        
    Returns:
        Configured AIRouterBridge instance
    """
    import os
    
    config = BridgeConfig(
        orchestrator_url=orchestrator_url or os.getenv("AI_ROUTER_URL", "http://localhost:3001"),
        default_tier=ModelTier(os.getenv("AI_DEFAULT_TIER", "STANDARD")),
        phi_compliant_only=os.getenv("PHI_COMPLIANT_ONLY", "true").lower() == "true",
        max_retries=int(os.getenv("AI_MAX_RETRIES", "3")),
        timeout_seconds=int(os.getenv("AI_TIMEOUT_SECONDS", "30")),
        cost_tracking_enabled=os.getenv("AI_COST_TRACKING", "true").lower() == "true",
        streaming_enabled=os.getenv("AI_STREAMING_ENABLED", "false").lower() == "true",
        **kwargs
    )
    
    return AIRouterBridge(config)


# Context manager for easy usage
class AIRouterBridgeContext:
    """Context manager for AI Router Bridge"""
    
    def __init__(self, **kwargs):
        self.bridge = create_ai_router_bridge(**kwargs)
    
    async def __aenter__(self) -> AIRouterBridge:
        await self.bridge.connect()
        return self.bridge
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.bridge.close()


# Convenience function
async def invoke_llm(
    prompt: str,
    task_type: str = "general",
    model_tier: ModelTier = None,
    governance_mode: GovernanceMode = None,
    **kwargs
) -> LLMResponse:
    """
    Convenience function for single LLM calls
    
    Args:
        prompt: The prompt to send
        task_type: Type of task
        model_tier: Model tier to use
        governance_mode: Governance mode
        **kwargs: Additional options
        
    Returns:
        LLM response
    """
    options = ModelOptions(
        task_type=task_type,
        model_tier=model_tier,
        governance_mode=governance_mode,
        **kwargs
    )
    
    async with AIRouterBridgeContext() as bridge:
        return await bridge.invoke(prompt, options)


if __name__ == "__main__":
    # Test the bridge
    async def test_bridge():
        async with AIRouterBridgeContext() as bridge:
            # Health check
            health = await bridge.health_check()
            print(f"Health check: {health}")
            
            # Simple test call
            if health["status"] == "healthy":
                try:
                    response = await bridge.invoke(
                        "What is the capital of France?",
                        ModelOptions(task_type="general")
                    )
                    print(f"Response: {response.content[:100]}...")
                    print(f"Cost: ${response.cost.total:.4f}")
                except Exception as e:
                    print(f"Test call failed: {e}")
            else:
                print("Orchestrator not healthy, skipping test call")
    
    asyncio.run(test_bridge())