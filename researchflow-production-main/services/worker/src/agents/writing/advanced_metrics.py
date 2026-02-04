"""
Advanced Metrics Collection System for AI Bridge

Comprehensive performance, cost, and usage metrics with:
- Real-time performance tracking
- Cost analysis and budgeting
- User behavior analytics
- System health monitoring
- Predictive analytics for capacity planning

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, deque
import time
import psutil

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics tracked."""
    PERFORMANCE = "performance"
    COST = "cost"
    USAGE = "usage"
    ERROR = "error"
    SYSTEM = "system"
    USER = "user"
    BUSINESS = "business"

class MetricSeverity(Enum):
    """Metric severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error" 
    CRITICAL = "critical"

@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: datetime
    metric_name: str
    value: Union[int, float, str, Dict]
    metric_type: MetricType
    severity: MetricSeverity = MetricSeverity.INFO
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "severity": self.severity.value,
            "tags": self.tags,
            "metadata": self.metadata
        }

@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    request_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    error_count: int = 0
    
    # Response time percentiles
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_request(self, duration_ms: float, error: bool = False):
        """Add a request performance measurement."""
        self.request_count += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        if error:
            self.error_count += 1
        
        self.response_times.append(duration_ms)
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        if self.request_count == 0:
            return {
                "request_count": 0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
                "error_rate": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0
            }
        
        times = list(self.response_times)
        
        return {
            "request_count": self.request_count,
            "avg_duration_ms": self.total_duration_ms / self.request_count,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else 0.0,
            "max_duration_ms": self.max_duration_ms,
            "error_rate": self.error_count / self.request_count,
            "p50_ms": statistics.median(times) if times else 0.0,
            "p95_ms": statistics.quantiles(times, n=20)[18] if len(times) > 20 else (times[-1] if times else 0.0),
            "p99_ms": statistics.quantiles(times, n=100)[98] if len(times) > 100 else (times[-1] if times else 0.0)
        }

@dataclass
class CostMetrics:
    """Cost tracking metrics."""
    total_cost_usd: float = 0.0
    token_usage: int = 0
    api_calls: int = 0
    compute_time_minutes: float = 0.0
    storage_gb_hours: float = 0.0
    
    # Cost breakdown by service
    service_costs: Dict[str, float] = field(default_factory=dict)
    
    def add_cost(self, cost_usd: float, service: str = "general", 
                 tokens: int = 0, compute_minutes: float = 0.0):
        """Add cost data."""
        self.total_cost_usd += cost_usd
        self.token_usage += tokens
        self.api_calls += 1
        self.compute_time_minutes += compute_minutes
        
        if service not in self.service_costs:
            self.service_costs[service] = 0.0
        self.service_costs[service] += cost_usd
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown."""
        return {
            "total_cost_usd": self.total_cost_usd,
            "cost_per_api_call": self.total_cost_usd / max(self.api_calls, 1),
            "cost_per_token": self.total_cost_usd / max(self.token_usage, 1),
            "cost_per_minute": self.total_cost_usd / max(self.compute_time_minutes, 1),
            "service_breakdown": self.service_costs,
            "usage_stats": {
                "total_api_calls": self.api_calls,
                "total_tokens": self.token_usage,
                "total_compute_minutes": self.compute_time_minutes,
                "total_storage_gb_hours": self.storage_gb_hours
            }
        }

class AdvancedMetricsCollector:
    """Advanced metrics collection and analysis system."""
    
    def __init__(self, 
                 max_history_minutes: int = 60,
                 enable_predictive_analytics: bool = True,
                 cost_alert_threshold_usd: float = 10.0):
        self.max_history_minutes = max_history_minutes
        self.enable_predictive_analytics = enable_predictive_analytics
        self.cost_alert_threshold_usd = cost_alert_threshold_usd
        
        # Metric storage
        self.metrics_history: deque = deque(maxlen=10000)
        self.performance_metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.cost_metrics = CostMetrics()
        
        # System metrics
        self.system_start_time = datetime.utcnow()
        self._last_cleanup = datetime.utcnow()
        
        # Alerting
        self.alert_history: deque = deque(maxlen=1000)
        
        logger.info("Advanced Metrics Collector initialized")
    
    async def record_metric(self, 
                           metric_name: str,
                           value: Union[int, float, str, Dict],
                           metric_type: MetricType = MetricType.PERFORMANCE,
                           severity: MetricSeverity = MetricSeverity.INFO,
                           tags: Optional[Dict[str, str]] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """Record a metric data point."""
        try:
            metric_point = MetricPoint(
                timestamp=datetime.utcnow(),
                metric_name=metric_name,
                value=value,
                metric_type=metric_type,
                severity=severity,
                tags=tags or {},
                metadata=metadata or {}
            )
            
            self.metrics_history.append(metric_point)
            
            # Process special metric types
            if metric_type == MetricType.PERFORMANCE and isinstance(value, dict):
                await self._process_performance_metric(metric_name, value, tags or {})
            elif metric_type == MetricType.COST and isinstance(value, dict):
                await self._process_cost_metric(metric_name, value)
            
            # Check for alerts
            await self._check_alerts(metric_point)
            
            # Periodic cleanup
            await self._periodic_cleanup()
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    async def _process_performance_metric(self, metric_name: str, value: Dict, tags: Dict):
        """Process performance-specific metrics."""
        try:
            endpoint = tags.get("endpoint", "unknown")
            duration_ms = value.get("duration_ms", 0)
            error = value.get("error", False)
            
            self.performance_metrics[endpoint].add_request(duration_ms, error)
            
            # Record additional derived metrics
            if duration_ms > 5000:  # Slow request threshold
                await self.record_metric(
                    "slow_request_detected",
                    {"endpoint": endpoint, "duration_ms": duration_ms},
                    MetricType.PERFORMANCE,
                    MetricSeverity.WARNING,
                    tags
                )
            
        except Exception as e:
            logger.error(f"Error processing performance metric: {e}")
    
    async def _process_cost_metric(self, metric_name: str, value: Dict):
        """Process cost-specific metrics."""
        try:
            cost_usd = value.get("cost_usd", 0.0)
            service = value.get("service", "general")
            tokens = value.get("tokens", 0)
            compute_minutes = value.get("compute_minutes", 0.0)
            
            self.cost_metrics.add_cost(cost_usd, service, tokens, compute_minutes)
            
            # Check cost alerts
            if self.cost_metrics.total_cost_usd > self.cost_alert_threshold_usd:
                await self.record_metric(
                    "cost_threshold_exceeded",
                    {"total_cost": self.cost_metrics.total_cost_usd, "threshold": self.cost_alert_threshold_usd},
                    MetricType.COST,
                    MetricSeverity.WARNING
                )
            
        except Exception as e:
            logger.error(f"Error processing cost metric: {e}")
    
    async def _check_alerts(self, metric_point: MetricPoint):
        """Check for alert conditions."""
        try:
            # Error rate alerts
            if metric_point.metric_type == MetricType.ERROR:
                error_count = sum(1 for m in list(self.metrics_history)[-100:] if m.metric_type == MetricType.ERROR)
                if error_count > 10:  # High error rate
                    alert = {
                        "alert_type": "high_error_rate",
                        "timestamp": datetime.utcnow().isoformat(),
                        "details": {"error_count": error_count, "window_size": 100}
                    }
                    self.alert_history.append(alert)
            
            # Performance alerts
            endpoint_metrics = metric_point.tags.get("endpoint")
            if endpoint_metrics and endpoint_metrics in self.performance_metrics:
                perf_stats = self.performance_metrics[endpoint_metrics].get_stats()
                if perf_stats["error_rate"] > 0.1:  # 10% error rate
                    alert = {
                        "alert_type": "high_endpoint_error_rate",
                        "timestamp": datetime.utcnow().isoformat(),
                        "endpoint": endpoint_metrics,
                        "error_rate": perf_stats["error_rate"]
                    }
                    self.alert_history.append(alert)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _periodic_cleanup(self):
        """Perform periodic cleanup of old metrics."""
        try:
            now = datetime.utcnow()
            if (now - self._last_cleanup).total_seconds() > 300:  # Every 5 minutes
                cutoff_time = now - timedelta(minutes=self.max_history_minutes)
                
                # Clean old metrics
                self.metrics_history = deque(
                    [m for m in self.metrics_history if m.timestamp > cutoff_time],
                    maxlen=10000
                )
                
                self._last_cleanup = now
                
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network metrics (basic)
            network = psutil.net_io_counters()
            
            # Uptime
            uptime_seconds = (datetime.utcnow() - self.system_start_time).total_seconds()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": uptime_seconds,
                "system_resources": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_usage_percent": (disk.used / disk.total) * 100,
                    "disk_free_gb": disk.free / (1024**3)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "metrics_summary": {
                    "total_metrics_recorded": len(self.metrics_history),
                    "metrics_per_minute": self._calculate_metrics_rate(),
                    "active_endpoints": len(self.performance_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def _calculate_metrics_rate(self) -> float:
        """Calculate metrics recording rate per minute."""
        try:
            now = datetime.utcnow()
            one_minute_ago = now - timedelta(minutes=1)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > one_minute_ago]
            return len(recent_metrics)
        except:
            return 0.0
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            endpoint_summaries = {}
            for endpoint, metrics in self.performance_metrics.items():
                endpoint_summaries[endpoint] = metrics.get_stats()
            
            # Calculate overall statistics
            total_requests = sum(m.request_count for m in self.performance_metrics.values())
            total_errors = sum(m.error_count for m in self.performance_metrics.values())
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_stats": {
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "overall_error_rate": total_errors / max(total_requests, 1),
                    "active_endpoints": len(endpoint_summaries)
                },
                "endpoint_performance": endpoint_summaries,
                "alerts_count": len(self.alert_history),
                "recent_alerts": list(self.alert_history)[-10:]  # Last 10 alerts
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def get_cost_analysis(self) -> Dict[str, Any]:
        """Get detailed cost analysis."""
        try:
            cost_breakdown = self.cost_metrics.get_cost_breakdown()
            
            # Calculate projections
            uptime_hours = (datetime.utcnow() - self.system_start_time).total_seconds() / 3600
            hourly_rate = cost_breakdown["total_cost_usd"] / max(uptime_hours, 1)
            
            # Project costs
            daily_projection = hourly_rate * 24
            monthly_projection = daily_projection * 30
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "current_costs": cost_breakdown,
                "projections": {
                    "hourly_rate_usd": hourly_rate,
                    "daily_projection_usd": daily_projection,
                    "monthly_projection_usd": monthly_projection
                },
                "efficiency_metrics": {
                    "cost_per_request": cost_breakdown["cost_per_api_call"],
                    "requests_per_dollar": 1 / max(cost_breakdown["cost_per_api_call"], 0.001),
                    "tokens_per_dollar": 1 / max(cost_breakdown["cost_per_token"], 0.001)
                },
                "alerts": {
                    "approaching_threshold": self.cost_metrics.total_cost_usd > (self.cost_alert_threshold_usd * 0.8),
                    "threshold_exceeded": self.cost_metrics.total_cost_usd > self.cost_alert_threshold_usd
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cost analysis: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def get_predictive_insights(self) -> Dict[str, Any]:
        """Get predictive analytics insights (if enabled)."""
        if not self.enable_predictive_analytics:
            return {"predictive_analytics": "disabled"}
        
        try:
            # Simple trend analysis
            recent_metrics = list(self.metrics_history)[-100:]
            if len(recent_metrics) < 10:
                return {"predictive_analytics": "insufficient_data"}
            
            # Analyze request volume trends
            request_volumes = []
            time_windows = []
            
            for i in range(0, len(recent_metrics) - 10, 10):
                window_metrics = recent_metrics[i:i+10]
                request_count = sum(1 for m in window_metrics if m.metric_type == MetricType.PERFORMANCE)
                request_volumes.append(request_count)
                time_windows.append(window_metrics[0].timestamp)
            
            # Simple linear trend
            if len(request_volumes) > 3:
                trend_slope = (request_volumes[-1] - request_volumes[0]) / len(request_volumes)
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "trends": {
                        "request_volume_trend": "increasing" if trend_slope > 0 else "decreasing",
                        "trend_magnitude": abs(trend_slope),
                        "confidence": "low"  # Simple analysis has low confidence
                    },
                    "predictions": {
                        "next_hour_requests": max(0, request_volumes[-1] + (trend_slope * 6)),  # 6 windows per hour
                        "capacity_warning": trend_slope > 5,  # Rapid increase
                        "cost_projection_accuracy": "low"
                    }
                }
            
            return {"predictive_analytics": "trends_analysis_incomplete"}
            
        except Exception as e:
            logger.error(f"Error generating predictive insights: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

# Global metrics collector instance
_metrics_collector: Optional[AdvancedMetricsCollector] = None

async def get_metrics_collector() -> AdvancedMetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AdvancedMetricsCollector()
    return _metrics_collector

async def record_performance_metric(endpoint: str, duration_ms: float, error: bool = False, **kwargs):
    """Convenience function to record performance metrics."""
    collector = await get_metrics_collector()
    await collector.record_metric(
        metric_name="api_request",
        value={"duration_ms": duration_ms, "error": error, **kwargs},
        metric_type=MetricType.PERFORMANCE,
        tags={"endpoint": endpoint}
    )

async def record_cost_metric(cost_usd: float, service: str, tokens: int = 0, **kwargs):
    """Convenience function to record cost metrics."""
    collector = await get_metrics_collector()
    await collector.record_metric(
        metric_name="service_cost",
        value={"cost_usd": cost_usd, "service": service, "tokens": tokens, **kwargs},
        metric_type=MetricType.COST
    )

async def record_error_metric(error_type: str, error_message: str, **kwargs):
    """Convenience function to record error metrics."""
    collector = await get_metrics_collector()
    await collector.record_metric(
        metric_name="error_occurred",
        value={"error_type": error_type, "error_message": error_message, **kwargs},
        metric_type=MetricType.ERROR,
        severity=MetricSeverity.ERROR
    )