#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation

Provides a circuit breaker for external API calls to prevent cascading failures.
The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service recovered

Usage:
    from agents.utils.circuit_breaker import CircuitBreaker, circuit_breaker

    # As decorator
    @circuit_breaker(failure_threshold=5, recovery_timeout=30)
    def call_external_api():
        return requests.get("https://api.example.com")

    # As context manager
    breaker = CircuitBreaker("api-name", failure_threshold=5)
    with breaker:
        response = requests.get("https://api.example.com")
"""

import time
import logging
import threading
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Any, Dict, TypeVar, Type
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5           # Failures before opening circuit
    success_threshold: int = 2           # Successes in half-open before closing
    recovery_timeout: float = 30.0       # Seconds before trying half-open
    timeout: float = 30.0                # Request timeout in seconds
    expected_exceptions: tuple = (Exception,)  # Exceptions to track


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    total_failures: int = 0
    total_successes: int = 0
    total_rejected: int = 0
    state_changes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation for external service calls.

    Prevents cascading failures by failing fast when a service is unavailable.

    Example:
        breaker = CircuitBreaker("openai-api")

        @breaker
        def call_openai():
            return openai.chat.completions.create(...)

        # Or as context manager
        with breaker:
            response = requests.get(url)
    """

    # Global registry of circuit breakers
    _registry: Dict[str, 'CircuitBreaker'] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: float = 30.0,
        timeout: float = 30.0,
        expected_exceptions: tuple = (Exception,),
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit
            failure_threshold: Number of failures before opening circuit
            success_threshold: Successes needed in half-open to close
            recovery_timeout: Seconds to wait before trying half-open
            timeout: Default timeout for wrapped calls
            expected_exceptions: Exception types to track as failures
        """
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            recovery_timeout=recovery_timeout,
            timeout=timeout,
            expected_exceptions=expected_exceptions,
        )
        self.stats = CircuitBreakerStats()
        self._state = CircuitState.CLOSED
        self._state_lock = threading.Lock()

        # Register this circuit breaker
        with CircuitBreaker._lock:
            CircuitBreaker._registry[name] = self

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, potentially transitioning to half-open"""
        with self._state_lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.stats.last_failure_time:
                    elapsed = time.time() - self.stats.last_failure_time
                    if elapsed >= self.config.recovery_timeout:
                        self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state"""
        old_state = self._state
        self._state = new_state
        self.stats.state_changes += 1

        if new_state == CircuitState.CLOSED:
            self.stats.failure_count = 0
            self.stats.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.stats.success_count = 0

        logger.info(
            f"[CircuitBreaker:{self.name}] State transition: {old_state.value} -> {new_state.value}"
        )

    def _record_success(self) -> None:
        """Record a successful call"""
        with self._state_lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(f"[CircuitBreaker:{self.name}] Circuit closed after successful recovery")

    def _record_failure(self, error: Exception) -> None:
        """Record a failed call"""
        with self._state_lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                self._transition_to(CircuitState.OPEN)
                logger.warning(f"[CircuitBreaker:{self.name}] Circuit reopened after failure in half-open")
            elif self._state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] Circuit opened after {self.stats.failure_count} failures"
                    )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator usage"""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def __enter__(self) -> 'CircuitBreaker':
        """Context manager entry"""
        state = self.state
        if state == CircuitState.OPEN:
            self.stats.total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable, try again in {self.config.recovery_timeout}s"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit"""
        if exc_type is None:
            self._record_success()
        elif isinstance(exc_val, self.config.expected_exceptions):
            self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        state = self.state

        if state == CircuitState.OPEN:
            self.stats.total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable, try again in {self.config.recovery_timeout}s"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exceptions as e:
            self._record_failure(e)
            raise

    def reset(self) -> None:
        """Manually reset circuit to closed state"""
        with self._state_lock:
            self._transition_to(CircuitState.CLOSED)
            self.stats.failure_count = 0
            self.stats.success_count = 0
            logger.info(f"[CircuitBreaker:{self.name}] Manually reset to closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "total_rejected": self.stats.total_rejected,
            "state_changes": self.stats.state_changes,
            "last_failure": self.stats.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            }
        }

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        with cls._lock:
            return {name: cb.get_stats() for name, cb in cls._registry.items()}

    @classmethod
    def get_breaker(cls, name: str) -> Optional['CircuitBreaker']:
        """Get a circuit breaker by name"""
        with cls._lock:
            return cls._registry.get(name)


def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    recovery_timeout: float = 30.0,
    expected_exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator factory for circuit breaker.

    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Failures before opening
        success_threshold: Successes in half-open before closing
        recovery_timeout: Seconds before trying half-open
        expected_exceptions: Exception types to track

    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker_name = name or f"{func.__module__}.{func.__qualname__}"
        breaker = CircuitBreaker(
            name=breaker_name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            recovery_timeout=recovery_timeout,
            expected_exceptions=expected_exceptions,
        )
        return breaker(func)
    return decorator


# =============================================================================
# Pre-configured Circuit Breakers for Common Services
# =============================================================================

# OpenAI API circuit breaker
openai_breaker = CircuitBreaker(
    name="openai-api",
    failure_threshold=3,
    success_threshold=2,
    recovery_timeout=60.0,
    expected_exceptions=(Exception,),
)

# Anthropic API circuit breaker
anthropic_breaker = CircuitBreaker(
    name="anthropic-api",
    failure_threshold=3,
    success_threshold=2,
    recovery_timeout=60.0,
    expected_exceptions=(Exception,),
)

# Composio API circuit breaker
composio_breaker = CircuitBreaker(
    name="composio-api",
    failure_threshold=5,
    success_threshold=2,
    recovery_timeout=30.0,
    expected_exceptions=(Exception,),
)

# FAISS/Vector DB circuit breaker
faiss_breaker = CircuitBreaker(
    name="faiss-vectordb",
    failure_threshold=5,
    success_threshold=2,
    recovery_timeout=15.0,
    expected_exceptions=(Exception,),
)

# GitHub API circuit breaker
github_breaker = CircuitBreaker(
    name="github-api",
    failure_threshold=5,
    success_threshold=2,
    recovery_timeout=30.0,
    expected_exceptions=(Exception,),
)

# Notion API circuit breaker
notion_breaker = CircuitBreaker(
    name="notion-api",
    failure_threshold=5,
    success_threshold=2,
    recovery_timeout=30.0,
    expected_exceptions=(Exception,),
)
