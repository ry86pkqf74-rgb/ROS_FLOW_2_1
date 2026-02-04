#!/usr/bin/env python3
"""
Prometheus Metrics Integration for ResearchFlow Agents

Provides metrics collection and export for production monitoring:
- Agent execution metrics (duration, success/failure rates)
- API call metrics (latency, error rates)
- Circuit breaker metrics
- Health check metrics
- Resource utilization metrics

Integrates with Prometheus, Grafana, and other monitoring systems.

@author Claude
@created 2025-01-30
"""

import time
import os
import logging
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# Lazy import prometheus_client to avoid dependency issues
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
        start_http_server,
        generate_latest,
        CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not available - metrics will be logged only")


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    INFO = "info"


@dataclass
class MetricConfig:
    """Configuration for metrics collection"""
    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    log_metrics: bool = True
    namespace: str = "researchflow"
    subsystem: str = "agents"


class MetricsCollector:
    """
    Centralized metrics collector for ResearchFlow agents.
    
    Supports both Prometheus metrics and structured logging fallback.
    
    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.increment_counter("agent.tasks.completed", {"agent": "DesignOps"})
        >>> metrics.observe_histogram("agent.task.duration", 123.45, {"agent": "DesignOps"})
        >>> metrics.set_gauge("agent.active_connections", 5)
    """
    
    def __init__(self, config: Optional[MetricConfig] = None):
        self.config = config or MetricConfig()
        self._metrics: Dict[str, Any] = {}
        self._prometheus_started = False
        
        # Initialize if enabled
        if self.config.enabled:
            self._init_prometheus()
            self._init_default_metrics()
    
    def _init_prometheus(self):
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE or not self.config.prometheus_enabled:
            logger.info("Prometheus metrics disabled or unavailable")
            return
        
        logger.info(f"Initializing Prometheus metrics on port {self.config.prometheus_port}")
    
    def _init_default_metrics(self):
        """Initialize default agent metrics"""
        
        # Agent execution metrics
        self._register_counter(
            "agent_tasks_total",
            "Total number of agent tasks executed",
            ["agent_name", "task_type", "status"]
        )
        
        self._register_histogram(
            "agent_task_duration_seconds",
            "Time spent executing agent tasks",
            ["agent_name", "task_type"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
        )
        
        # API call metrics
        self._register_counter(
            "api_calls_total",
            "Total number of API calls made",
            ["service", "endpoint", "status_code"]
        )
        
        self._register_histogram(
            "api_call_duration_seconds",
            "API call duration",
            ["service", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        # Circuit breaker metrics
        self._register_counter(
            "circuit_breaker_state_transitions_total",
            "Circuit breaker state transitions",
            ["service", "from_state", "to_state"]
        )
        
        self._register_gauge(
            "circuit_breaker_state",
            "Current circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["service"]
        )
        
        # Health check metrics
        self._register_counter(
            "health_checks_total",
            "Total number of health checks",
            ["component", "status"]
        )
        
        self._register_histogram(
            "health_check_duration_seconds",
            "Health check duration",
            ["component"],
            buckets=[0.01, 0.1, 0.5, 1.0, 5.0, 10.0]
        )
        
        # Resource metrics
        self._register_gauge(
            "active_workflows",
            "Number of active workflows",
            ["workflow_type"]
        )
        
        self._register_gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            ["process"]
        )
        
        logger.info(f"Initialized {len(self._metrics)} default metrics")
    
    def _register_counter(self, name: str, description: str, labels: List[str]):
        """Register a counter metric"""
        full_name = f"{self.config.namespace}_{self.config.subsystem}_{name}"
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            self._metrics[name] = Counter(
                full_name,
                description,
                labels
            )
        else:
            self._metrics[name] = {
                "type": "counter",
                "name": full_name,
                "description": description,
                "labels": labels,
                "values": {}
            }
    
    def _register_histogram(
        self, 
        name: str, 
        description: str, 
        labels: List[str], 
        buckets: Optional[List[float]] = None
    ):
        """Register a histogram metric"""
        full_name = f"{self.config.namespace}_{self.config.subsystem}_{name}"
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            self._metrics[name] = Histogram(
                full_name,
                description,
                labels,
                buckets=buckets
            )
        else:
            self._metrics[name] = {
                "type": "histogram",
                "name": full_name,
                "description": description,
                "labels": labels,
                "buckets": buckets or [],
                "observations": []
            }
    
    def _register_gauge(self, name: str, description: str, labels: List[str]):
        """Register a gauge metric"""
        full_name = f"{self.config.namespace}_{self.config.subsystem}_{name}"
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            self._metrics[name] = Gauge(
                full_name,
                description,
                labels
            )
        else:
            self._metrics[name] = {
                "type": "gauge",
                "name": full_name,
                "description": description,
                "labels": labels,
                "value": 0
            }
    
    def increment_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None, amount: float = 1):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            labels: Label values
            amount: Amount to increment by
        """
        if not self.config.enabled or metric_name not in self._metrics:
            return
        
        labels = labels or {}
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            metric = self._metrics[metric_name]
            metric.labels(**labels).inc(amount)
        
        # Always log if enabled
        if self.config.log_metrics:
            logger.info(
                f"metric.counter.{metric_name}",
                extra={
                    "metric_type": "counter",
                    "metric_name": metric_name,
                    "value": amount,
                    "labels": labels
                }
            )
    
    def observe_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Observe a value in a histogram.
        
        Args:
            metric_name: Name of the metric
            value: Value to observe
            labels: Label values
        """
        if not self.config.enabled or metric_name not in self._metrics:
            return
        
        labels = labels or {}
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            metric = self._metrics[metric_name]
            metric.labels(**labels).observe(value)
        
        if self.config.log_metrics:
            logger.info(
                f"metric.histogram.{metric_name}",
                extra={
                    "metric_type": "histogram",
                    "metric_name": metric_name,
                    "value": value,
                    "labels": labels
                }
            )
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Set a gauge value.
        
        Args:
            metric_name: Name of the metric
            value: Value to set
            labels: Label values
        """
        if not self.config.enabled or metric_name not in self._metrics:
            return
        
        labels = labels or {}
        
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            metric = self._metrics[metric_name]
            metric.labels(**labels).set(value)
        
        if self.config.log_metrics:
            logger.info(
                f"metric.gauge.{metric_name}",
                extra={
                    "metric_type": "gauge",
                    "metric_name": metric_name,
                    "value": value,
                    "labels": labels
                }
            )
    
    def start_http_server(self, port: Optional[int] = None) -> bool:
        """
        Start Prometheus HTTP server.
        
        Args:
            port: Port to bind to (uses config default if None)
            
        Returns:
            True if server started successfully
        """
        if not PROMETHEUS_AVAILABLE or not self.config.prometheus_enabled:
            logger.warning("Prometheus not available or disabled")
            return False
        
        if self._prometheus_started:
            logger.warning("Prometheus server already started")
            return True
        
        port = port or self.config.prometheus_port
        
        try:
            start_http_server(port)
            self._prometheus_started = True
            logger.info(f"✅ Prometheus metrics server started on port {port}")
            logger.info(f"📊 Metrics available at http://localhost:{port}/metrics")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start Prometheus server: {e}")
            return False
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        if PROMETHEUS_AVAILABLE and self.config.prometheus_enabled:
            return generate_latest().decode('utf-8')
        else:
            # Simple text format for non-Prometheus mode
            lines = ["# ResearchFlow Agent Metrics", ""]
            for name, metric in self._metrics.items():
                if metric.get("type") == "counter":
                    lines.append(f"# TYPE {metric['name']} counter")
                    lines.append(f"{metric['name']} {metric.get('values', {}).get('', 0)}")
                elif metric.get("type") == "gauge":
                    lines.append(f"# TYPE {metric['name']} gauge")
                    lines.append(f"{metric['name']} {metric.get('value', 0)}")
            return "\n".join(lines)


# Singleton metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector"""
    global _metrics_collector
    
    if _metrics_collector is None:
        config = MetricConfig(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            prometheus_enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
            prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9090")),
            log_metrics=os.getenv("LOG_METRICS", "true").lower() == "true"
        )
        _metrics_collector = MetricsCollector(config)
    
    return _metrics_collector


# Convenience decorators for common metrics

def track_agent_task(agent_name: str, task_type: str = "general"):
    """
    Decorator to track agent task execution.
    
    Automatically increments counters and tracks duration.
    
    Example:
        >>> @track_agent_task("DesignOps", "token_extraction")
        ... def extract_tokens():
        ...     pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Record success
                duration = time.time() - start_time
                labels = {"agent_name": agent_name, "task_type": task_type}
                
                metrics.increment_counter(
                    "agent_tasks_total",
                    {**labels, "status": "success"}
                )
                metrics.observe_histogram(
                    "agent_task_duration_seconds",
                    duration,
                    labels
                )
                
                return result
                
            except Exception as e:
                # Record failure
                duration = time.time() - start_time
                labels = {"agent_name": agent_name, "task_type": task_type}
                
                metrics.increment_counter(
                    "agent_tasks_total",
                    {**labels, "status": "error"}
                )
                metrics.observe_histogram(
                    "agent_task_duration_seconds",
                    duration,
                    labels
                )
                
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                duration = time.time() - start_time
                labels = {"agent_name": agent_name, "task_type": task_type}
                
                metrics.increment_counter(
                    "agent_tasks_total",
                    {**labels, "status": "success"}
                )
                metrics.observe_histogram(
                    "agent_task_duration_seconds",
                    duration,
                    labels
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                labels = {"agent_name": agent_name, "task_type": task_type}
                
                metrics.increment_counter(
                    "agent_tasks_total",
                    {**labels, "status": "error"}
                )
                metrics.observe_histogram(
                    "agent_task_duration_seconds",
                    duration,
                    labels
                )
                
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def track_api_call(service: str, endpoint: str = "unknown"):
    """
    Decorator to track API calls.
    
    Example:
        >>> @track_api_call("openai", "chat/completions")
        ... async def call_openai():
        ...     pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            start_time = time.time()
            status_code = "unknown"
            
            try:
                result = func(*args, **kwargs)
                
                # Handle both sync and async functions
                if asyncio.iscoroutinefunction(func):
                    result = await result
                
                # Try to extract status code from result
                if hasattr(result, 'status_code'):
                    status_code = str(result.status_code)
                elif isinstance(result, dict) and 'status_code' in result:
                    status_code = str(result['status_code'])
                else:
                    status_code = "200"  # Assume success if no error
                
                duration = time.time() - start_time
                labels = {"service": service, "endpoint": endpoint}
                
                metrics.increment_counter(
                    "api_calls_total",
                    {**labels, "status_code": status_code}
                )
                metrics.observe_histogram(
                    "api_call_duration_seconds",
                    duration,
                    labels
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                status_code = getattr(e, 'status_code', '500')
                labels = {"service": service, "endpoint": endpoint}
                
                metrics.increment_counter(
                    "api_calls_total",
                    {**labels, "status_code": str(status_code)}
                )
                metrics.observe_histogram(
                    "api_call_duration_seconds",
                    duration,
                    labels
                )
                
                raise
        
        return wrapper
    return decorator


# FastAPI integration helper

def create_metrics_endpoint():
    """
    Create a metrics endpoint function for FastAPI.
    
    Example:
        from fastapi import FastAPI
        from agents.utils.metrics import create_metrics_endpoint
        
        app = FastAPI()
        metrics_endpoint = create_metrics_endpoint()
        
        @app.get("/metrics")
        async def metrics():
            return await metrics_endpoint()
    """
    async def metrics_endpoint():
        metrics = get_metrics_collector()
        content = metrics.get_metrics_text()
        
        if PROMETHEUS_AVAILABLE:
            from fastapi import Response
            return Response(
                content=content,
                media_type=CONTENT_TYPE_LATEST
            )
        else:
            return {"metrics": content}
    
    return metrics_endpoint