#!/usr/bin/env python3
"""
Retry Logic with Exponential Backoff for ResearchFlow Agents

Provides robust retry mechanisms for:
- API calls to external services
- Database operations
- File system operations
- Circuit breaker integration
- Custom retry strategies

Features:
- Exponential backoff with jitter
- Configurable retry policies
- Error classification (retry vs fail fast)
- Metrics integration
- Circuit breaker integration

@author Claude
@created 2025-01-30
"""

import asyncio
import random
import time
import logging
from typing import (
    Any, Callable, Optional, Union, Type, List, Tuple, Dict,
    Awaitable, TypeVar, Generic
)
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import inspect

logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')
RetryableFunc = Union[Callable[..., T], Callable[..., Awaitable[T]]]


class BackoffStrategy(Enum):
    """Backoff strategies for retries"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class RetryableError(Exception):
    """Wrapper for retryable errors"""
    def __init__(self, original_error: Exception, retry_count: int):
        self.original_error = original_error
        self.retry_count = retry_count
        super().__init__(str(original_error))


@dataclass
class RetryPolicy:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    
    # Error handling
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (KeyboardInterrupt, SystemExit)
    
    # Circuit breaker integration
    circuit_breaker_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate policy configuration"""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= self.jitter_range <= 1:
            raise ValueError("jitter_range must be between 0 and 1")


@dataclass
class RetryResult(Generic[T]):
    """Result of a retry operation"""
    value: T
    attempts: int
    total_duration: float
    exceptions: List[Exception]
    success: bool


class RetryManager:
    """
    Advanced retry manager with multiple backoff strategies.
    
    Example:
        >>> retry_manager = RetryManager()
        >>> 
        >>> @retry_manager.retry(max_attempts=3, backoff_strategy=BackoffStrategy.EXPONENTIAL)
        >>> async def unreliable_api_call():
        ...     # Simulate API call that may fail
        ...     if random.random() < 0.7:
        ...         raise ConnectionError("API temporarily unavailable")
        ...     return "Success"
        >>> 
        >>> result = await unreliable_api_call()
    """
    
    def __init__(self):
        self.metrics = None
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize metrics collection"""
        try:
            from .metrics import get_metrics_collector
            self.metrics = get_metrics_collector()
        except ImportError:
            logger.debug("Metrics not available for retry manager")
    
    def calculate_delay(
        self, 
        attempt: int, 
        policy: RetryPolicy
    ) -> float:
        """
        Calculate delay for the given attempt using the specified strategy.
        
        Args:
            attempt: Current attempt number (0-based)
            policy: Retry policy configuration
            
        Returns:
            Delay in seconds
        """
        if policy.backoff_strategy == BackoffStrategy.FIXED:
            delay = policy.base_delay
        
        elif policy.backoff_strategy == BackoffStrategy.LINEAR:
            delay = policy.base_delay * (attempt + 1)
        
        elif policy.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = policy.base_delay * (policy.backoff_multiplier ** attempt)
        
        elif policy.backoff_strategy == BackoffStrategy.FIBONACCI:
            # Generate Fibonacci sequence for delays
            if attempt == 0:
                delay = policy.base_delay
            elif attempt == 1:
                delay = policy.base_delay
            else:
                # Calculate Fibonacci number for this attempt
                a, b = 1, 1
                for _ in range(attempt - 1):
                    a, b = b, a + b
                delay = policy.base_delay * b
        
        else:
            delay = policy.base_delay
        
        # Apply maximum delay cap
        delay = min(delay, policy.max_delay)
        
        # Add jitter to prevent thundering herd
        if policy.jitter:
            jitter_amount = delay * policy.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)
        
        return delay
    
    def is_retryable_error(self, exception: Exception, policy: RetryPolicy) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception that occurred
            policy: Retry policy configuration
            
        Returns:
            True if the error should be retried
        """
        # Check non-retryable exceptions first (higher priority)
        if isinstance(exception, policy.non_retryable_exceptions):
            return False
        
        # Check if it matches retryable exceptions
        if isinstance(exception, policy.retryable_exceptions):
            return True
        
        return False
    
    def retry(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        non_retryable_exceptions: Tuple[Type[Exception], ...] = (KeyboardInterrupt, SystemExit),
        circuit_breaker_name: Optional[str] = None
    ):
        """
        Decorator for adding retry logic to functions.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            backoff_strategy: Strategy for calculating backoff delays
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Exceptions that should trigger retries
            non_retryable_exceptions: Exceptions that should never be retried
            circuit_breaker_name: Name of circuit breaker to use
        """
        policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            backoff_multiplier=backoff_multiplier,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            circuit_breaker_name=circuit_breaker_name
        )
        
        def decorator(func: RetryableFunc) -> RetryableFunc:
            if inspect.iscoroutinefunction(func):
                return self._async_retry_wrapper(func, policy)
            else:
                return self._sync_retry_wrapper(func, policy)
        
        return decorator
    
    def _sync_retry_wrapper(self, func: Callable, policy: RetryPolicy) -> Callable:
        """Wrapper for synchronous functions"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute_with_retry(func, args, kwargs, policy, is_async=False)
        return wrapper
    
    def _async_retry_wrapper(self, func: Callable, policy: RetryPolicy) -> Callable:
        """Wrapper for asynchronous functions"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self._execute_with_retry(func, args, kwargs, policy, is_async=True)
        return wrapper
    
    async def _execute_with_retry(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        policy: RetryPolicy,
        is_async: bool
    ) -> Any:
        """Execute function with retry logic"""
        start_time = time.time()
        exceptions = []
        
        # Get circuit breaker if specified
        circuit_breaker = None
        if policy.circuit_breaker_name:
            try:
                from .circuit_breaker import get_circuit_breaker
                circuit_breaker = get_circuit_breaker(policy.circuit_breaker_name)
            except ImportError:
                logger.debug("Circuit breaker not available")
        
        for attempt in range(policy.max_attempts):
            try:
                # Record attempt
                if self.metrics:
                    self.metrics.increment_counter(
                        "retry_attempts_total",
                        {
                            "function": func.__name__,
                            "attempt": str(attempt + 1)
                        }
                    )
                
                # Execute function
                if circuit_breaker:
                    if is_async:
                        result = await circuit_breaker.call_async(func, *args, **kwargs)
                    else:
                        result = circuit_breaker.call(func, *args, **kwargs)
                else:
                    if is_async:
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                
                # Success - record metrics and return
                total_duration = time.time() - start_time
                
                if self.metrics:
                    self.metrics.increment_counter(
                        "retry_success_total",
                        {
                            "function": func.__name__,
                            "attempts": str(attempt + 1)
                        }
                    )
                    self.metrics.observe_histogram(
                        "retry_duration_seconds",
                        total_duration,
                        {
                            "function": func.__name__,
                            "success": "true"
                        }
                    )
                
                logger.debug(
                    f"Function {func.__name__} succeeded after {attempt + 1} attempts "
                    f"in {total_duration:.2f}s"
                )
                
                return result
            
            except Exception as e:
                exceptions.append(e)
                
                # Check if error is retryable
                if not self.is_retryable_error(e, policy):
                    logger.debug(f"Non-retryable error in {func.__name__}: {e}")
                    break
                
                # Check if we have attempts remaining
                if attempt >= policy.max_attempts - 1:
                    logger.debug(f"Max attempts reached for {func.__name__}")
                    break
                
                # Calculate delay for next attempt
                delay = self.calculate_delay(attempt, policy)
                
                logger.debug(
                    f"Attempt {attempt + 1} of {policy.max_attempts} failed for "
                    f"{func.__name__}: {e}. Retrying in {delay:.2f}s"
                )
                
                # Record failure metrics
                if self.metrics:
                    self.metrics.increment_counter(
                        "retry_failures_total",
                        {
                            "function": func.__name__,
                            "attempt": str(attempt + 1),
                            "error_type": type(e).__name__
                        }
                    )
                
                # Wait before next attempt
                if is_async:
                    await asyncio.sleep(delay)
                else:
                    time.sleep(delay)
        
        # All attempts failed
        total_duration = time.time() - start_time
        
        if self.metrics:
            self.metrics.increment_counter(
                "retry_exhausted_total",
                {"function": func.__name__}
            )
            self.metrics.observe_histogram(
                "retry_duration_seconds",
                total_duration,
                {
                    "function": func.__name__,
                    "success": "false"
                }
            )
        
        # Raise the last exception wrapped with retry context
        last_exception = exceptions[-1] if exceptions else Exception("Unknown error")
        raise RetryableError(last_exception, len(exceptions))
    
    async def execute_with_policy(
        self,
        func: Callable,
        policy: RetryPolicy,
        *args,
        **kwargs
    ) -> RetryResult[T]:
        """
        Execute a function with explicit retry policy.
        
        Returns detailed result information including all attempts.
        """
        start_time = time.time()
        exceptions = []
        
        for attempt in range(policy.max_attempts):
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                return RetryResult(
                    value=result,
                    attempts=attempt + 1,
                    total_duration=time.time() - start_time,
                    exceptions=exceptions,
                    success=True
                )
            
            except Exception as e:
                exceptions.append(e)
                
                if not self.is_retryable_error(e, policy) or attempt >= policy.max_attempts - 1:
                    break
                
                delay = self.calculate_delay(attempt, policy)
                await asyncio.sleep(delay)
        
        # All attempts failed
        return RetryResult(
            value=None,
            attempts=policy.max_attempts,
            total_duration=time.time() - start_time,
            exceptions=exceptions,
            success=False
        )


# Singleton retry manager
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get or create the global retry manager"""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


# Convenience decorators for common retry patterns

def retry_api_call(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """
    Decorator for retrying API calls with exponential backoff.
    
    Suitable for external API calls that may have transient failures.
    """
    import httpx
    import aiohttp
    
    return get_retry_manager().retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            httpx.TimeoutException,
            httpx.ConnectError,
            aiohttp.ClientError,
            OSError
        ),
        non_retryable_exceptions=(
            KeyboardInterrupt,
            SystemExit,
            ValueError,  # Bad request parameters
            TypeError    # Programming errors
        )
    )


def retry_database_operation(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0
):
    """
    Decorator for retrying database operations.
    
    Suitable for database operations that may fail due to deadlocks,
    connection issues, or temporary unavailability.
    """
    return get_retry_manager().retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            # Add database-specific exceptions here
            # psycopg2.OperationalError,
            # sqlalchemy.exc.DisconnectionError,
        )
    )


def retry_file_operation(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 5.0
):
    """
    Decorator for retrying file system operations.
    
    Suitable for file operations that may fail due to temporary
    file locking or filesystem issues.
    """
    return get_retry_manager().retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.LINEAR,
        retryable_exceptions=(
            FileNotFoundError,
            PermissionError,
            OSError,
            IOError
        ),
        non_retryable_exceptions=(
            KeyboardInterrupt,
            SystemExit,
            IsADirectoryError,  # Programming error
            NotADirectoryError  # Programming error
        )
    )