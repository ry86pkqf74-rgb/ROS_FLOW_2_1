#!/usr/bin/env python3
"""
Timeout Protection for ResearchFlow Agents

Provides comprehensive timeout management:
- Function execution timeouts
- HTTP request timeouts
- Database operation timeouts
- Workflow step timeouts
- Graceful cancellation
- Resource cleanup

@author Claude
@created 2025-01-30
"""

import asyncio
import signal
import time
import threading
from typing import (
    Any, Callable, Optional, Union, TypeVar, Awaitable,
    Dict, List, ContextManager
)
from dataclasses import dataclass
from functools import wraps
from contextlib import asynccontextmanager, contextmanager
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
TimeoutFunc = Union[Callable[..., T], Callable[..., Awaitable[T]]]


class TimeoutError(Exception):
    """Custom timeout exception with context"""
    def __init__(self, message: str, timeout_seconds: float, function_name: str = "unknown"):
        self.timeout_seconds = timeout_seconds
        self.function_name = function_name
        super().__init__(message)


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior"""
    default_timeout: float = 30.0
    long_operation_timeout: float = 300.0  # 5 minutes
    database_timeout: float = 30.0
    api_timeout: float = 60.0
    workflow_step_timeout: float = 600.0  # 10 minutes
    file_operation_timeout: float = 10.0
    
    # Grace period for cleanup
    cleanup_timeout: float = 5.0
    
    # Whether to log timeout warnings
    log_timeouts: bool = True


class TimeoutManager:
    """
    Comprehensive timeout management for agent operations.
    
    Provides decorators and context managers for different types of operations.
    
    Example:
        >>> timeout_manager = TimeoutManager()
        >>> 
        >>> @timeout_manager.timeout(30.0)
        >>> async def slow_operation():
        ...     await asyncio.sleep(60)  # Will timeout after 30s
        >>> 
        >>> try:
        ...     result = await slow_operation()
        >>> except TimeoutError as e:
        ...     print(f"Operation timed out after {e.timeout_seconds}s")
    """
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._active_timeouts: Dict[str, asyncio.Task] = {}
        self.metrics = None
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize metrics collection"""
        try:
            from .metrics import get_metrics_collector
            self.metrics = get_metrics_collector()
        except ImportError:
            logger.debug("Metrics not available for timeout manager")
    
    def timeout(
        self,
        seconds: Optional[float] = None,
        operation_type: str = "general"
    ):
        """
        Decorator to add timeout protection to functions.
        
        Args:
            seconds: Timeout in seconds (uses default if None)
            operation_type: Type of operation for metrics/logging
        """
        timeout_duration = seconds or self.config.default_timeout
        
        def decorator(func: TimeoutFunc) -> TimeoutFunc:
            if asyncio.iscoroutinefunction(func):
                return self._async_timeout_wrapper(func, timeout_duration, operation_type)
            else:
                return self._sync_timeout_wrapper(func, timeout_duration, operation_type)
        
        return decorator
    
    def _async_timeout_wrapper(
        self, 
        func: Callable, 
        timeout_duration: float, 
        operation_type: str
    ) -> Callable:
        """Wrapper for async functions"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Use asyncio.wait_for for timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_duration
                )
                
                # Record success metrics
                duration = time.time() - start_time
                self._record_timeout_metrics(
                    func.__name__, 
                    operation_type, 
                    duration, 
                    timeout_duration, 
                    success=True
                )
                
                return result
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                
                # Record timeout metrics
                self._record_timeout_metrics(
                    func.__name__, 
                    operation_type, 
                    duration, 
                    timeout_duration, 
                    success=False
                )
                
                if self.config.log_timeouts:
                    logger.warning(
                        f"Function {func.__name__} timed out after {timeout_duration}s "
                        f"(operation_type: {operation_type})"
                    )
                
                raise TimeoutError(
                    f"Function {func.__name__} timed out after {timeout_duration} seconds",
                    timeout_duration,
                    func.__name__
                )
            
            except Exception as e:
                duration = time.time() - start_time
                self._record_timeout_metrics(
                    func.__name__, 
                    operation_type, 
                    duration, 
                    timeout_duration, 
                    success=False,
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    
    def _sync_timeout_wrapper(
        self, 
        func: Callable, 
        timeout_duration: float, 
        operation_type: str
    ) -> Callable:
        """Wrapper for sync functions using threading"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            result_container = {}
            exception_container = {}
            
            def target():
                try:
                    result_container['result'] = func(*args, **kwargs)
                except Exception as e:
                    exception_container['exception'] = e
            
            start_time = time.time()
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout_duration)
            
            duration = time.time() - start_time
            
            if thread.is_alive():
                # Timeout occurred
                self._record_timeout_metrics(
                    func.__name__, 
                    operation_type, 
                    duration, 
                    timeout_duration, 
                    success=False
                )
                
                if self.config.log_timeouts:
                    logger.warning(
                        f"Sync function {func.__name__} timed out after {timeout_duration}s"
                    )
                
                raise TimeoutError(
                    f"Function {func.__name__} timed out after {timeout_duration} seconds",
                    timeout_duration,
                    func.__name__
                )
            
            # Check for exceptions
            if 'exception' in exception_container:
                self._record_timeout_metrics(
                    func.__name__, 
                    operation_type, 
                    duration, 
                    timeout_duration, 
                    success=False,
                    error_type=type(exception_container['exception']).__name__
                )
                raise exception_container['exception']
            
            # Success
            self._record_timeout_metrics(
                func.__name__, 
                operation_type, 
                duration, 
                timeout_duration, 
                success=True
            )
            
            return result_container.get('result')
        
        return wrapper
    
    def _record_timeout_metrics(
        self,
        function_name: str,
        operation_type: str,
        duration: float,
        timeout_limit: float,
        success: bool,
        error_type: Optional[str] = None
    ):
        """Record timeout-related metrics"""
        if not self.metrics:
            return
        
        labels = {
            "function": function_name,
            "operation_type": operation_type,
            "success": str(success).lower()
        }
        
        if error_type:
            labels["error_type"] = error_type
        
        # Record execution time
        self.metrics.observe_histogram(
            "timeout_operation_duration_seconds",
            duration,
            labels
        )
        
        # Record timeout ratio (how close to timeout)
        timeout_ratio = duration / timeout_limit
        self.metrics.observe_histogram(
            "timeout_ratio",
            timeout_ratio,
            labels
        )
        
        # Count timeouts
        if not success and error_type != "TimeoutError":
            self.metrics.increment_counter(
                "timeout_errors_total",
                labels
            )
        elif not success:
            self.metrics.increment_counter(
                "timeouts_total",
                labels
            )
    
    @asynccontextmanager
    async def timeout_context(
        self, 
        seconds: float, 
        operation_name: str = "context_operation"
    ):
        """
        Async context manager for timeout protection.
        
        Example:
            >>> timeout_manager = TimeoutManager()
            >>> async with timeout_manager.timeout_context(30.0, "data_processing"):
            ...     await process_large_dataset()
        """
        start_time = time.time()
        
        try:
            async with asyncio.timeout(seconds):
                yield
            
            # Record success
            duration = time.time() - start_time
            self._record_timeout_metrics(
                operation_name, 
                "context", 
                duration, 
                seconds, 
                success=True
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            
            self._record_timeout_metrics(
                operation_name, 
                "context", 
                duration, 
                seconds, 
                success=False
            )
            
            if self.config.log_timeouts:
                logger.warning(f"Context operation '{operation_name}' timed out after {seconds}s")
            
            raise TimeoutError(
                f"Operation '{operation_name}' timed out after {seconds} seconds",
                seconds,
                operation_name
            )
    
    @contextmanager
    def timeout_context_sync(
        self, 
        seconds: float, 
        operation_name: str = "sync_context_operation"
    ):
        """
        Synchronous context manager for timeout protection using signals.
        
        Note: Only works on Unix systems and main thread.
        """
        def timeout_handler(signum, frame):
            raise TimeoutError(
                f"Operation '{operation_name}' timed out after {seconds} seconds",
                seconds,
                operation_name
            )
        
        start_time = time.time()
        
        # Set up signal handler (Unix only)
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds))
            
            try:
                yield
                
                # Success
                duration = time.time() - start_time
                self._record_timeout_metrics(
                    operation_name, 
                    "sync_context", 
                    duration, 
                    seconds, 
                    success=True
                )
                
            finally:
                # Clear alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                
        except (OSError, ValueError):
            # Signal not supported (Windows) or not main thread
            # Fall back to simple time tracking (no actual timeout)
            logger.warning(f"Signal-based timeout not available for {operation_name}")
            
            try:
                yield
                
                duration = time.time() - start_time
                if duration > seconds:
                    logger.warning(
                        f"Operation '{operation_name}' took {duration:.2f}s "
                        f"(exceeds timeout of {seconds}s)"
                    )
                
            except Exception as e:
                duration = time.time() - start_time
                self._record_timeout_metrics(
                    operation_name, 
                    "sync_context", 
                    duration, 
                    seconds, 
                    success=False,
                    error_type=type(e).__name__
                )
                raise


# Singleton timeout manager
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get or create the global timeout manager"""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager


# Convenience decorators for common timeout patterns

def timeout_api_call(seconds: float = 60.0):
    """Decorator for API call timeouts"""
    return get_timeout_manager().timeout(seconds, "api_call")


def timeout_database_operation(seconds: float = 30.0):
    """Decorator for database operation timeouts"""
    return get_timeout_manager().timeout(seconds, "database")


def timeout_file_operation(seconds: float = 10.0):
    """Decorator for file operation timeouts"""
    return get_timeout_manager().timeout(seconds, "file_operation")


def timeout_workflow_step(seconds: float = 600.0):
    """Decorator for workflow step timeouts"""
    return get_timeout_manager().timeout(seconds, "workflow_step")


def timeout_long_operation(seconds: float = 300.0):
    """Decorator for long-running operations"""
    return get_timeout_manager().timeout(seconds, "long_operation")


# Context manager helpers

@asynccontextmanager
async def timeout_after(seconds: float, operation_name: str = "operation"):
    """
    Convenience async context manager for timeouts.
    
    Example:
        >>> async with timeout_after(30.0, "data_processing"):
        ...     await process_data()
    """
    async with get_timeout_manager().timeout_context(seconds, operation_name):
        yield


@contextmanager
def timeout_after_sync(seconds: float, operation_name: str = "operation"):
    """
    Convenience sync context manager for timeouts.
    
    Example:
        >>> with timeout_after_sync(30.0, "file_processing"):
        ...     process_file()
    """
    with get_timeout_manager().timeout_context_sync(seconds, operation_name):
        yield