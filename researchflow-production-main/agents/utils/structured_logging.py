#!/usr/bin/env python3
"""
Structured Logging for ResearchFlow Agents

Provides structured logging with:
- JSON formatting for log aggregation
- Contextual information (agent, workflow, task)
- Performance metrics
- Correlation IDs for tracing
- Integration with monitoring systems

@author Claude
@created 2025-01-30
"""

import logging
import json
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
agent_name_var: ContextVar[Optional[str]] = ContextVar('agent_name', default=None)
workflow_id_var: ContextVar[Optional[str]] = ContextVar('workflow_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logs.
    
    Outputs logs in JSON format with standard fields:
    - timestamp
    - level
    - message
    - logger
    - correlation_id (if available)
    - agent_name (if available)
    - workflow_id (if available)
    - extra fields
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add context from ContextVars
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        agent_name = agent_name_var.get()
        if agent_name:
            log_data["agent_name"] = agent_name
        
        workflow_id = workflow_id_var.get()
        if workflow_id:
            log_data["workflow_id"] = workflow_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName',
                'relativeCreated', 'thread', 'threadName', 'exc_info',
                'exc_text', 'stack_info'
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Add source location in development
        if os.getenv("LOG_LEVEL", "INFO") == "DEBUG":
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
        
        return json.dumps(log_data, default=str)


def setup_structured_logging(
    level: str = "INFO",
    json_format: bool = True
) -> logging.Logger:
    """
    Setup structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or plain text (False)
        
    Returns:
        Configured root logger
        
    Example:
        >>> from agents.utils.structured_logging import setup_structured_logging
        >>> logger = setup_structured_logging(level="INFO")
        >>> logger.info("Application started")
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Set formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with structured logging enabled.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
        
    Example:
        >>> from agents.utils.structured_logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Task completed", extra={"duration_ms": 123})
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding context to logs.
    
    Example:
        >>> with LogContext(agent_name="DesignOps", workflow_id="wf-123"):
        ...     logger.info("Processing task")
    """
    
    def __init__(
        self,
        correlation_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        workflow_id: Optional[str] = None
    ):
        self.correlation_id = correlation_id
        self.agent_name = agent_name
        self.workflow_id = workflow_id
        
        self._old_correlation_id = None
        self._old_agent_name = None
        self._old_workflow_id = None
    
    def __enter__(self):
        """Set context variables"""
        self._old_correlation_id = correlation_id_var.get()
        self._old_agent_name = agent_name_var.get()
        self._old_workflow_id = workflow_id_var.get()
        
        if self.correlation_id:
            correlation_id_var.set(self.correlation_id)
        if self.agent_name:
            agent_name_var.set(self.agent_name)
        if self.workflow_id:
            workflow_id_var.set(self.workflow_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore old context variables"""
        correlation_id_var.set(self._old_correlation_id)
        agent_name_var.set(self._old_agent_name)
        workflow_id_var.set(self._old_workflow_id)


def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log function execution time.
    
    Example:
        >>> @log_execution_time()
        ... def process_data():
        ...     time.sleep(1)
        >>> process_data()  # Logs execution time
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                _logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "status": "success"
                    }
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                _logger.error(
                    f"{func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "status": "error",
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_async_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log async function execution time.
    
    Example:
        >>> @log_async_execution_time()
        ... async def fetch_data():
        ...     await asyncio.sleep(1)
        >>> await fetch_data()  # Logs execution time
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                _logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "status": "success"
                    }
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                _logger.error(
                    f"{func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                        "status": "error",
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


class MetricsLogger:
    """
    Logger for performance metrics.
    
    Example:
        >>> metrics = MetricsLogger()
        >>> metrics.record_counter("api_calls", 1, {"endpoint": "/health"})
        >>> metrics.record_histogram("response_time_ms", 123.45, {"endpoint": "/health"})
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("metrics")
    
    def record_counter(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a counter metric"""
        self.logger.info(
            f"metric.counter: {metric_name}",
            extra={
                "metric_type": "counter",
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {}
            }
        )
    
    def record_histogram(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a histogram metric"""
        self.logger.info(
            f"metric.histogram: {metric_name}",
            extra={
                "metric_type": "histogram",
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {}
            }
        )
    
    def record_gauge(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a gauge metric"""
        self.logger.info(
            f"metric.gauge: {metric_name}",
            extra={
                "metric_type": "gauge",
                "metric_name": metric_name,
                "value": value,
                "tags": tags or {}
            }
        )


# Convenience function for agent logging

def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a logger configured for a specific agent.
    
    Args:
        agent_name: Name of the agent (e.g., "DesignOps")
        
    Returns:
        Logger with agent context
        
    Example:
        >>> logger = get_agent_logger("DesignOps")
        >>> logger.info("Task started", extra={"task_id": "123"})
    """
    logger = logging.getLogger(f"agents.{agent_name}")
    
    # Set agent name in context
    agent_name_var.set(agent_name)
    
    return logger
