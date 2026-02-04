"""
Error Tracking & APM Integration for ResearchFlow Agents

This module provides comprehensive error tracking, distributed tracing, and APM capabilities
for production monitoring and debugging.

Features:
- Sentry integration for error aggregation and alerting
- Distributed tracing spans for request flow visibility
- Error correlation with existing metrics
- Context capture for debugging
- Performance tracking integration
- Graceful degradation when APM backend unavailable

Usage:
    from agents.utils import track_error, create_span, get_error_stats
    
    @track_error(component="DesignOpsAgent")
    @create_span("token_extraction")
    async def extract_tokens():
        try:
            # Agent work
            pass
        except Exception as e:
            # Auto-captured with context
            raise
            
    # Error statistics for health checks
    error_stats = await get_error_stats(last_minutes=15)
    if error_stats.error_rate > 0.05:  # 5% threshold
        # Trigger alerts
        pass
"""

import asyncio
import functools
import inspect
import time
import traceback
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

try:
    import sentry_sdk
    from sentry_sdk import configure_scope, capture_exception, start_span
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from .structured_logging import get_logger

# Context variables for tracing
_current_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
_current_component: ContextVar[Optional[str]] = ContextVar('component', default=None)

logger = get_logger(__name__)


@dataclass
class ErrorStats:
    """Error statistics for monitoring"""
    total_errors: int = 0
    error_rate: float = 0.0
    avg_error_duration: float = 0.0
    error_types: Dict[str, int] = field(default_factory=dict)
    last_error_time: Optional[datetime] = None
    time_window_minutes: int = 15


@dataclass
class SpanContext:
    """Distributed tracing span context"""
    span_id: str
    trace_id: str
    component: str
    operation: str
    start_time: float
    parent_span_id: Optional[str] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    finished: bool = False


class ErrorTracker:
    """Centralized error tracking and distributed tracing"""
    
    def __init__(self):
        self.enabled = False
        self.sentry_initialized = False
        self.error_history: List[Dict[str, Any]] = []
        self.active_spans: Dict[str, SpanContext] = {}
        self._lock = asyncio.Lock()
        
    def initialize_sentry(
        self,
        dsn: Optional[str] = None,
        environment: str = "development",
        release: Optional[str] = None,
        sample_rate: float = 1.0,
        traces_sample_rate: float = 0.1
    ):
        """Initialize Sentry integration"""
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry SDK not available, error tracking will use fallback logging")
            self.enabled = True
            return
            
        if not dsn:
            logger.info("Sentry DSN not provided, error tracking will use local logging")
            self.enabled = True
            return
            
        try:
            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                sample_rate=sample_rate,
                traces_sample_rate=traces_sample_rate,
                integrations=[
                    AsyncioIntegration(),
                    LoggingIntegration(level=None, event_level=None)
                ],
                attach_stacktrace=True,
                send_default_pii=False,
                max_breadcrumbs=100
            )
            
            self.sentry_initialized = True
            self.enabled = True
            logger.info(f"Sentry initialized for environment: {environment}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry: {e}, using fallback logging")
            self.enabled = True
            
    def create_trace_id(self) -> str:
        """Create a new trace ID"""
        return str(uuid4())
        
    def create_span_id(self) -> str:
        """Create a new span ID"""
        return str(uuid4())[:16]
        
    async def start_span(
        self,
        operation: str,
        component: str,
        tags: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None
    ) -> str:
        """Start a new distributed tracing span"""
        if not self.enabled:
            return ""
            
        span_id = self.create_span_id()
        trace_id = _current_trace_id.get() or self.create_trace_id()
        
        if not parent_span_id:
            parent_span_id = _current_span_id.get()
            
        span_context = SpanContext(
            span_id=span_id,
            trace_id=trace_id,
            component=component,
            operation=operation,
            start_time=time.time(),
            parent_span_id=parent_span_id,
            tags=tags or {}
        )
        
        async with self._lock:
            self.active_spans[span_id] = span_context
            
        # Set context for child spans
        _current_trace_id.set(trace_id)
        _current_span_id.set(span_id)
        _current_component.set(component)
        
        logger.debug(f"Started span {span_id} for {component}.{operation}")
        
        if self.sentry_initialized:
            with configure_scope() as scope:
                scope.set_tag("component", component)
                scope.set_tag("trace_id", trace_id)
                scope.set_tag("span_id", span_id)
                if parent_span_id:
                    scope.set_tag("parent_span_id", parent_span_id)
                    
        return span_id
        
    async def finish_span(
        self,
        span_id: str,
        tags: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """Finish a distributed tracing span"""
        if not self.enabled or not span_id:
            return
            
        async with self._lock:
            span = self.active_spans.get(span_id)
            if not span:
                logger.warning(f"Attempted to finish unknown span: {span_id}")
                return
                
            span.finished = True
            duration = time.time() - span.start_time
            
            if tags:
                span.tags.update(tags)
                
            if error:
                span.tags["error"] = True
                span.tags["error_type"] = type(error).__name__
                span.tags["error_message"] = str(error)
                
            # Log span completion
            logger.debug(
                f"Finished span {span_id} for {span.component}.{span.operation}",
                extra={
                    "span_id": span_id,
                    "trace_id": span.trace_id,
                    "component": span.component,
                    "operation": span.operation,
                    "duration_ms": duration * 1000,
                    "tags": span.tags,
                    "error": error is not None
                }
            )
            
            # Clean up
            del self.active_spans[span_id]
            
    async def track_error(
        self,
        error: Exception,
        component: str,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error"
    ):
        """Track an error with context"""
        if not self.enabled:
            return
            
        error_data = {
            "timestamp": datetime.utcnow(),
            "component": component,
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
            "trace_id": _current_trace_id.get(),
            "span_id": _current_span_id.get(),
            "context": context or {}
        }
        
        # Add to local history
        async with self._lock:
            self.error_history.append(error_data)
            # Keep only last 1000 errors
            if len(self.error_history) > 1000:
                self.error_history = self.error_history[-1000:]
                
        # Log error with structured data
        logger.error(
            f"Error in {component}.{operation or 'unknown'}",
            extra={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "trace_id": error_data["trace_id"],
                "span_id": error_data["span_id"],
                "component": component,
                "operation": operation,
                "context": context,
                "severity": severity
            },
            exc_info=error
        )
        
        # Send to Sentry if available
        if self.sentry_initialized:
            with configure_scope() as scope:
                scope.set_tag("component", component)
                if operation:
                    scope.set_tag("operation", operation)
                scope.set_level(severity)
                
                # Add context
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                        
                # Add trace info
                if error_data["trace_id"]:
                    scope.set_tag("trace_id", error_data["trace_id"])
                if error_data["span_id"]:
                    scope.set_tag("span_id", error_data["span_id"])
                    
                capture_exception(error)
                
    async def get_error_stats(self, last_minutes: int = 15) -> ErrorStats:
        """Get error statistics for the last N minutes"""
        if not self.enabled:
            return ErrorStats()
            
        cutoff_time = datetime.utcnow() - timedelta(minutes=last_minutes)
        
        async with self._lock:
            recent_errors = [
                error for error in self.error_history
                if error["timestamp"] >= cutoff_time
            ]
            
        total_errors = len(recent_errors)
        error_types = {}
        total_duration = 0
        last_error_time = None
        
        for error in recent_errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if not last_error_time or error["timestamp"] > last_error_time:
                last_error_time = error["timestamp"]
                
        # Calculate error rate (errors per minute)
        error_rate = total_errors / last_minutes if last_minutes > 0 else 0
        
        return ErrorStats(
            total_errors=total_errors,
            error_rate=error_rate,
            avg_error_duration=0.0,  # Could be enhanced with timing data
            error_types=error_types,
            last_error_time=last_error_time,
            time_window_minutes=last_minutes
        )
        
    async def clear_old_errors(self, hours: int = 24):
        """Clean up old error history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self._lock:
            self.error_history = [
                error for error in self.error_history
                if error["timestamp"] >= cutoff_time
            ]
            
        logger.debug(f"Cleaned error history older than {hours} hours")
        
    def get_active_traces(self) -> List[Dict[str, Any]]:
        """Get currently active traces"""
        return [
            {
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "component": span.component,
                "operation": span.operation,
                "duration_ms": (time.time() - span.start_time) * 1000,
                "tags": span.tags
            }
            for span in self.active_spans.values()
        ]


# Global error tracker instance
_error_tracker = ErrorTracker()


def initialize_error_tracking(
    dsn: Optional[str] = None,
    environment: str = "development", 
    release: Optional[str] = None,
    sample_rate: float = 1.0,
    traces_sample_rate: float = 0.1
):
    """Initialize error tracking with Sentry"""
    _error_tracker.initialize_sentry(
        dsn=dsn,
        environment=environment,
        release=release,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate
    )


def track_error(component: str, operation: Optional[str] = None):
    """Decorator to track errors in functions"""
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    await _error_tracker.track_error(
                        error=e,
                        component=component,
                        operation=operation or func.__name__,
                        context={
                            "function": func.__name__,
                            "args_count": len(args),
                            "kwargs_keys": list(kwargs.keys())
                        }
                    )
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Convert to async for tracking
                    asyncio.create_task(_error_tracker.track_error(
                        error=e,
                        component=component,
                        operation=operation or func.__name__,
                        context={
                            "function": func.__name__,
                            "args_count": len(args),
                            "kwargs_keys": list(kwargs.keys())
                        }
                    ))
                    raise
            return sync_wrapper
    return decorator


def create_span(operation: str, component: Optional[str] = None):
    """Decorator to create distributed tracing spans"""
    def decorator(func: Callable) -> Callable:
        span_component = component or _current_component.get() or "Unknown"
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                span_id = await _error_tracker.start_span(
                    operation=operation,
                    component=span_component,
                    tags={"function": func.__name__}
                )
                
                try:
                    result = await func(*args, **kwargs)
                    await _error_tracker.finish_span(span_id)
                    return result
                except Exception as e:
                    await _error_tracker.finish_span(span_id, error=e)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Note: Sync functions get basic logging only
                logger.debug(f"Starting {span_component}.{operation}")
                try:
                    result = func(*args, **kwargs)
                    logger.debug(f"Completed {span_component}.{operation}")
                    return result
                except Exception as e:
                    logger.error(f"Error in {span_component}.{operation}: {e}")
                    raise
            return sync_wrapper
    return decorator


class TraceContext:
    """Context manager for distributed tracing spans"""
    
    def __init__(self, operation: str, component: str, tags: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.component = component
        self.tags = tags
        self.span_id: Optional[str] = None
        
    async def __aenter__(self):
        self.span_id = await _error_tracker.start_span(
            operation=self.operation,
            component=self.component,
            tags=self.tags
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.span_id:
            await _error_tracker.finish_span(
                self.span_id,
                error=exc_val if exc_type else None
            )


# Convenience functions
async def get_error_stats(last_minutes: int = 15) -> ErrorStats:
    """Get error statistics for health checks"""
    return await _error_tracker.get_error_stats(last_minutes)


async def manual_track_error(
    error: Exception,
    component: str,
    operation: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """Manually track an error"""
    await _error_tracker.track_error(error, component, operation, context)


def get_active_traces() -> List[Dict[str, Any]]:
    """Get currently active traces"""
    return _error_tracker.get_active_traces()


async def clear_old_errors(hours: int = 24):
    """Clean up old error history"""
    await _error_tracker.clear_old_errors(hours)


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker instance"""
    return _error_tracker


# Health check integration
async def check_error_health(error_rate_threshold: float = 0.05) -> Dict[str, Any]:
    """Check error health for monitoring integration"""
    stats = await get_error_stats(last_minutes=15)
    
    is_healthy = stats.error_rate <= error_rate_threshold
    
    return {
        "healthy": is_healthy,
        "error_rate": stats.error_rate,
        "total_errors": stats.total_errors,
        "error_types": stats.error_types,
        "last_error": stats.last_error_time.isoformat() if stats.last_error_time else None,
        "threshold": error_rate_threshold,
        "time_window_minutes": stats.time_window_minutes
    }