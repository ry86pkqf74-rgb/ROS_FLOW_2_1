#!/usr/bin/env python3
"""
Model Timeout Configuration

Provides configurable timeout limits for different LLM providers and operations.
Prevents hung requests and ensures graceful degradation.

Usage:
    from agents.utils import get_model_timeout, ModelTimeoutConfig

    # Get timeout for specific provider and operation
    timeout = get_model_timeout("openai", "completion")

    # Use with API calls
    response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[...],
        timeout=timeout
    )
"""

import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    TRITON = "triton"
    HUGGINGFACE = "huggingface"


class OperationType(str, Enum):
    """Types of model operations"""
    COMPLETION = "completion"
    CHAT = "chat"
    EMBEDDING = "embedding"
    STREAMING = "streaming"
    FUNCTION_CALL = "function_call"


@dataclass
class TimeoutSettings:
    """Timeout settings for a specific operation"""
    connect_timeout: float = 10.0      # Connection establishment
    read_timeout: float = 60.0         # Reading response
    write_timeout: float = 30.0        # Writing request
    total_timeout: float = 120.0       # Total operation timeout


@dataclass
class ModelTimeoutConfig:
    """
    Comprehensive timeout configuration for model operations.

    Attributes:
        provider: LLM provider name
        operation_timeouts: Timeout settings per operation type
        max_retries: Maximum retry attempts
        retry_backoff: Base backoff time between retries
    """
    provider: str
    operation_timeouts: Dict[str, TimeoutSettings] = field(default_factory=dict)
    max_retries: int = 3
    retry_backoff: float = 1.0

    def get_timeout(self, operation: str) -> TimeoutSettings:
        """Get timeout settings for an operation"""
        return self.operation_timeouts.get(
            operation,
            self.operation_timeouts.get("default", TimeoutSettings())
        )


# =============================================================================
# Default Timeout Configurations
# =============================================================================

DEFAULT_TIMEOUTS: Dict[str, ModelTimeoutConfig] = {
    # OpenAI - Generally fast, but can be slow during high load
    "openai": ModelTimeoutConfig(
        provider="openai",
        operation_timeouts={
            "default": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=60.0,
                write_timeout=30.0,
                total_timeout=120.0,
            ),
            "completion": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=90.0,
                write_timeout=30.0,
                total_timeout=150.0,
            ),
            "chat": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=90.0,
                write_timeout=30.0,
                total_timeout=150.0,
            ),
            "embedding": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=30.0,
                write_timeout=30.0,
                total_timeout=60.0,
            ),
            "streaming": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=300.0,  # Longer for streaming
                write_timeout=30.0,
                total_timeout=600.0,
            ),
            "function_call": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=120.0,
                write_timeout=30.0,
                total_timeout=180.0,
            ),
        },
        max_retries=3,
        retry_backoff=1.0,
    ),

    # Anthropic - Similar to OpenAI
    "anthropic": ModelTimeoutConfig(
        provider="anthropic",
        operation_timeouts={
            "default": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=60.0,
                write_timeout=30.0,
                total_timeout=120.0,
            ),
            "completion": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=90.0,
                write_timeout=30.0,
                total_timeout=150.0,
            ),
            "chat": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=90.0,
                write_timeout=30.0,
                total_timeout=150.0,
            ),
            "streaming": TimeoutSettings(
                connect_timeout=10.0,
                read_timeout=300.0,
                write_timeout=30.0,
                total_timeout=600.0,
            ),
        },
        max_retries=3,
        retry_backoff=1.0,
    ),

    # Ollama - Local, can be slower for large models
    "ollama": ModelTimeoutConfig(
        provider="ollama",
        operation_timeouts={
            "default": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=120.0,  # Longer for local inference
                write_timeout=30.0,
                total_timeout=180.0,
            ),
            "completion": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=180.0,
                write_timeout=30.0,
                total_timeout=240.0,
            ),
            "chat": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=180.0,
                write_timeout=30.0,
                total_timeout=240.0,
            ),
            "embedding": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=60.0,
                write_timeout=30.0,
                total_timeout=90.0,
            ),
            "streaming": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=600.0,
                write_timeout=30.0,
                total_timeout=900.0,
            ),
        },
        max_retries=2,  # Fewer retries for local service
        retry_backoff=0.5,
    ),

    # Triton - High-performance inference server
    "triton": ModelTimeoutConfig(
        provider="triton",
        operation_timeouts={
            "default": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=30.0,
                write_timeout=15.0,
                total_timeout=60.0,
            ),
            "inference": TimeoutSettings(
                connect_timeout=5.0,
                read_timeout=45.0,
                write_timeout=15.0,
                total_timeout=90.0,
            ),
        },
        max_retries=2,
        retry_backoff=0.5,
    ),

    # HuggingFace - Can vary based on model size
    "huggingface": ModelTimeoutConfig(
        provider="huggingface",
        operation_timeouts={
            "default": TimeoutSettings(
                connect_timeout=15.0,
                read_timeout=90.0,
                write_timeout=30.0,
                total_timeout=150.0,
            ),
            "inference": TimeoutSettings(
                connect_timeout=15.0,
                read_timeout=120.0,
                write_timeout=30.0,
                total_timeout=180.0,
            ),
            "embedding": TimeoutSettings(
                connect_timeout=15.0,
                read_timeout=60.0,
                write_timeout=30.0,
                total_timeout=90.0,
            ),
        },
        max_retries=3,
        retry_backoff=2.0,
    ),
}


def get_model_timeout(
    provider: str,
    operation: str = "default",
    override_config: Optional[Dict[str, Any]] = None,
) -> TimeoutSettings:
    """
    Get timeout settings for a specific provider and operation.

    Args:
        provider: LLM provider name (openai, anthropic, ollama, etc.)
        operation: Operation type (completion, chat, embedding, etc.)
        override_config: Optional overrides for specific timeout values

    Returns:
        TimeoutSettings for the specified provider/operation

    Example:
        timeout = get_model_timeout("openai", "chat")
        # Use timeout.total_timeout for httpx/aiohttp timeout
    """
    provider_lower = provider.lower()

    # Get provider config or use default
    config = DEFAULT_TIMEOUTS.get(provider_lower)
    if config is None:
        logger.warning(f"Unknown provider '{provider}', using default timeouts")
        config = ModelTimeoutConfig(provider=provider_lower)

    # Get operation timeout
    timeout = config.get_timeout(operation)

    # Apply environment variable overrides
    env_prefix = f"{provider_lower.upper()}_TIMEOUT"
    if os.getenv(f"{env_prefix}_TOTAL"):
        timeout.total_timeout = float(os.getenv(f"{env_prefix}_TOTAL"))
    if os.getenv(f"{env_prefix}_READ"):
        timeout.read_timeout = float(os.getenv(f"{env_prefix}_READ"))
    if os.getenv(f"{env_prefix}_CONNECT"):
        timeout.connect_timeout = float(os.getenv(f"{env_prefix}_CONNECT"))

    # Apply explicit overrides
    if override_config:
        if "total_timeout" in override_config:
            timeout.total_timeout = override_config["total_timeout"]
        if "read_timeout" in override_config:
            timeout.read_timeout = override_config["read_timeout"]
        if "connect_timeout" in override_config:
            timeout.connect_timeout = override_config["connect_timeout"]
        if "write_timeout" in override_config:
            timeout.write_timeout = override_config["write_timeout"]

    return timeout


def get_httpx_timeout(
    provider: str,
    operation: str = "default",
) -> Dict[str, float]:
    """
    Get timeout configuration formatted for httpx.

    Args:
        provider: LLM provider name
        operation: Operation type

    Returns:
        Dict suitable for httpx.Timeout(**result)

    Example:
        import httpx
        timeout_config = get_httpx_timeout("openai", "chat")
        client = httpx.AsyncClient(timeout=httpx.Timeout(**timeout_config))
    """
    settings = get_model_timeout(provider, operation)
    return {
        "connect": settings.connect_timeout,
        "read": settings.read_timeout,
        "write": settings.write_timeout,
        "pool": settings.connect_timeout,
    }


def get_retry_config(provider: str) -> Dict[str, Any]:
    """
    Get retry configuration for a provider.

    Args:
        provider: LLM provider name

    Returns:
        Dict with max_retries and retry_backoff
    """
    provider_lower = provider.lower()
    config = DEFAULT_TIMEOUTS.get(provider_lower)

    if config is None:
        return {"max_retries": 3, "retry_backoff": 1.0}

    return {
        "max_retries": config.max_retries,
        "retry_backoff": config.retry_backoff,
    }
