"""
Performance Monitoring Dashboard for Literature Review System

This module provides real-time performance monitoring including:
- API response time tracking
- Cost analysis and optimization
- Usage pattern analysis  
- Alert system for performance degradation
- Resource utilization monitoring
- User activity analytics

Author: Performance Monitoring Team
"""

import logging
import asyncio
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    
    timestamp: datetime
    metric_name: str
    value: float
    
    # Context information
    endpoint: Optional[str] = None
    user_id: Optional[str] = None
    operation_type: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemHealth:
    """Current system health status."""
    
    timestamp: datetime
    overall_status: str  # "healthy", "warning", "critical"
    
    # Performance metrics
    avg_response_time: float
    error_rate: float
    throughput: float  # requests per second
    
    # Resource metrics
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    
    # Cost metrics
    daily_cost: float
    cost_per_request: float
    
    # User metrics
    active_users: int
    total_requests: int
    
    # Alerts
    active_alerts: List[str] = field(default_factory=list)

@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    
    alert_id: str
    name: str
    description: str
    
    # Alert conditions
    metric_name: str
    threshold: float
    operator: str  # "gt", "lt", "eq"
    duration_minutes: int  # How long threshold must be exceeded
    
    # Alert state
    is_active: bool = False
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions
    notification_channels: List[str] = field(default_factory=list)
    escalation_policy: Optional[str] = None

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    
    Tracks performance metrics, analyzes trends, and provides
    real-time alerts for system health monitoring.
    """
    
    def __init__(self, 
                 retention_days: int = 30,
                 max_metrics_in_memory: int = 100000):
        """Initialize performance monitor."""
        self.retention_days = retention_days
        self.max_metrics_in_memory = max_metrics_in_memory
        
        # Metric storage
        self.metrics: deque = deque(maxlen=max_metrics_in_memory)
        self.metrics_by_name: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        
        # Alert system
        self.alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[Dict[str, Any]] = []
        
        # Request tracking
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.request_counts: Dict[str, int] = defaultdict(int)
        
        # Cost tracking
        self.cost_tracking: Dict[str, float] = defaultdict(float)  # API costs by endpoint
        self.user_costs: Dict[str, float] = defaultdict(float)     # Costs by user
        
        # System monitoring
        self.system_metrics: deque = deque(maxlen=1440)  # 24 hours of minute-level data
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        self._setup_default_alerts()
        
        logger.info("Performance Monitor initialized")
    
    def _setup_default_alerts(self):
        """Setup default performance alerts."""
        default_alerts = [
            PerformanceAlert(
                alert_id="high_response_time",
                name="High Response Time",
                description="Average response time exceeds threshold",
                metric_name="response_time",
                threshold=5.0,  # 5 seconds
                operator="gt",
                duration_minutes=5,
                notification_channels=["email", "slack"]
            ),
            PerformanceAlert(
                alert_id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds acceptable threshold",
                metric_name="error_rate",
                threshold=0.05,  # 5%
                operator="gt",
                duration_minutes=3,
                notification_channels=["email", "slack", "pagerduty"]
            ),
            PerformanceAlert(
                alert_id="high_memory_usage",
                name="High Memory Usage",
                description="System memory usage is critically high",
                metric_name="memory_usage",
                threshold=0.90,  # 90%
                operator="gt",
                duration_minutes=2,
                notification_channels=["email", "slack"]
            ),
            PerformanceAlert(
                alert_id="high_daily_cost",
                name="High Daily Cost",
                description="Daily API costs exceed budget",
                metric_name="daily_cost",
                threshold=100.0,  # $100
                operator="gt",
                duration_minutes=1,
                notification_channels=["email"]
            )
        ]
        
        for alert in default_alerts:
            self.alerts[alert.alert_id] = alert
    
    @contextmanager
    def measure_operation(self, operation_name: str, 
                         endpoint: Optional[str] = None,
                         user_id: Optional[str] = None,
                         estimated_cost: float = 0.0):
        """Context manager to measure operation performance."""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            self.record_error(operation_name, str(e), endpoint=endpoint, user_id=user_id)
            raise
        finally:
            # Record performance metrics
            duration = time.time() - start_time
            
            self.record_metric(
                "response_time", 
                duration,
                endpoint=endpoint,
                user_id=user_id,
                operation_type=operation_name
            )
            
            # Track request
            self.request_counts[operation_name] += 1
            if endpoint:
                self.request_counts[f"endpoint_{endpoint}"] += 1
            
            # Track cost
            if estimated_cost > 0:
                self.cost_tracking[operation_name] += estimated_cost
                if user_id:
                    self.user_costs[user_id] += estimated_cost
            
            logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
    
    def record_metric(self, 
                     metric_name: str, 
                     value: float,
                     endpoint: Optional[str] = None,
                     user_id: Optional[str] = None,
                     operation_type: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric."""
        try:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=metric_name,
                value=value,
                endpoint=endpoint,
                user_id=user_id,
                operation_type=operation_type,
                metadata=metadata or {}
            )
            
            # Store in main queue
            self.metrics.append(metric)
            
            # Store by metric name
            self.metrics_by_name[metric_name].append(metric)
            
            # Check for alerts
            self._check_alerts(metric_name, value)
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    def record_error(self, 
                    operation_name: str, 
                    error_message: str,
                    endpoint: Optional[str] = None,
                    user_id: Optional[str] = None):
        """Record an error occurrence."""
        try:
            self.error_counts[operation_name] += 1
            if endpoint:
                self.error_counts[f"endpoint_{endpoint}"] += 1
            
            self.record_metric(
                "error",
                1.0,
                endpoint=endpoint,
                user_id=user_id,
                operation_type=operation_name,
                metadata={"error_message": error_message}
            )
            
            logger.warning(f"Error recorded for {operation_name}: {error_message}")
            
        except Exception as e:
            logger.error(f"Error recording error: {e}")
    
    def _check_alerts(self, metric_name: str, value: float):
        """Check if metric value triggers any alerts."""
        try:
            for alert in self.alerts.values():
                if alert.metric_name == metric_name:
                    should_trigger = False
                    
                    if alert.operator == "gt" and value > alert.threshold:
                        should_trigger = True
                    elif alert.operator == "lt" and value < alert.threshold:
                        should_trigger = True
                    elif alert.operator == "eq" and abs(value - alert.threshold) < 0.001:
                        should_trigger = True
                    
                    if should_trigger and not alert.is_active:
                        self._trigger_alert(alert)
                    elif not should_trigger and alert.is_active:
                        self._resolve_alert(alert)
                        
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _trigger_alert(self, alert: PerformanceAlert):
        """Trigger an alert."""
        try:
            alert.is_active = True
            alert.triggered_at = datetime.now()
            
            # Log alert
            logger.warning(f"ALERT TRIGGERED: {alert.name} - {alert.description}")
            
            # Record in history
            self.alert_history.append({
                "alert_id": alert.alert_id,
                "action": "triggered",
                "timestamp": datetime.now().isoformat(),
                "description": alert.description
            })
            
            # Send notifications (mock implementation)
            self._send_alert_notifications(alert, "triggered")
            
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
    
    def _resolve_alert(self, alert: PerformanceAlert):
        """Resolve an active alert."""
        try:
            alert.is_active = False
            alert.resolved_at = datetime.now()
            
            # Log resolution
            logger.info(f"ALERT RESOLVED: {alert.name}")
            
            # Record in history
            self.alert_history.append({
                "alert_id": alert.alert_id,
                "action": "resolved",
                "timestamp": datetime.now().isoformat(),
                "description": f"Alert resolved: {alert.description}"
            })
            
            # Send notifications (mock implementation)
            self._send_alert_notifications(alert, "resolved")
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
    
    def _send_alert_notifications(self, alert: PerformanceAlert, action: str):
        """Send alert notifications through configured channels."""
        try:
            message = f"Alert {action.upper()}: {alert.name}\n{alert.description}"
            
            # Mock notification implementation
            for channel in alert.notification_channels:
                logger.info(f"Sending {action} notification to {channel}: {message}")
                # In real implementation, integrate with actual notification services
            
        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")
    
    def get_current_system_health(self) -> SystemHealth:
        """Get current system health status."""
        try:
            now = datetime.now()
            
            # Calculate performance metrics (last 5 minutes)
            recent_cutoff = now - timedelta(minutes=5)
            recent_metrics = [m for m in self.metrics if m.timestamp >= recent_cutoff]
            
            # Response time metrics
            response_times = [m.value for m in recent_metrics if m.metric_name == "response_time"]
            avg_response_time = np.mean(response_times) if response_times else 0.0
            
            # Error rate
            total_requests = len([m for m in recent_metrics if m.metric_name == "response_time"])
            error_count = len([m for m in recent_metrics if m.metric_name == "error"])
            error_rate = error_count / max(total_requests, 1)
            
            # Throughput (requests per second)
            throughput = total_requests / 300.0  # 5 minutes = 300 seconds
            
            # System resource metrics
            cpu_usage = psutil.cpu_percent(interval=None) / 100.0
            memory = psutil.virtual_memory()
            memory_usage = memory.percent / 100.0
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent / 100.0
            
            # Cost metrics (daily)
            daily_cutoff = now - timedelta(days=1)
            daily_cost = sum(cost for cost in self.cost_tracking.values())
            cost_per_request = daily_cost / max(total_requests, 1)
            
            # User metrics
            active_users = len(set(m.user_id for m in recent_metrics if m.user_id))
            total_requests_today = len([m for m in self.metrics if m.timestamp >= daily_cutoff])
            
            # Determine overall status
            overall_status = "healthy"
            active_alerts = [alert.name for alert in self.alerts.values() if alert.is_active]
            
            if any(alert.is_active for alert in self.alerts.values()):
                if any("critical" in alert.name.lower() for alert in self.alerts.values() if alert.is_active):
                    overall_status = "critical"
                else:
                    overall_status = "warning"
            
            return SystemHealth(
                timestamp=now,
                overall_status=overall_status,
                avg_response_time=avg_response_time,
                error_rate=error_rate,
                throughput=throughput,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                daily_cost=daily_cost,
                cost_per_request=cost_per_request,
                active_users=active_users,
                total_requests=total_requests_today,
                active_alerts=active_alerts
            )
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return SystemHealth(
                timestamp=now,
                overall_status="unknown",
                avg_response_time=0.0,
                error_rate=0.0,
                throughput=0.0,
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                daily_cost=0.0,
                cost_per_request=0.0,
                active_users=0,
                total_requests=0
            )
    
    def generate_performance_dashboard(self) -> str:
        """Generate HTML performance dashboard."""
        try:
            # Get current health
            health = self.get_current_system_health()
            
            # Create dashboard with multiple subplots
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=[
                    'Response Time Trend',
                    'System Resource Usage',
                    'Error Rate Trend', 
                    'Cost Analysis',
                    'Request Volume',
                    'User Activity'
                ],
                specs=[
                    [{"secondary_y": True}, {"type": "indicator"}],
                    [{"secondary_y": True}, {"type": "pie"}],
                    [{"type": "bar"}, {"type": "scatter"}]
                ]
            )
            
            # Prepare data (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff]
            
            # Response time trend
            response_time_metrics = [m for m in recent_metrics if m.metric_name == "response_time"]
            if response_time_metrics:
                timestamps = [m.timestamp for m in response_time_metrics]
                values = [m.value for m in response_time_metrics]
                
                fig.add_trace(
                    go.Scatter(x=timestamps, y=values, name="Response Time", line=dict(color="blue")),
                    row=1, col=1
                )
            
            # System resource gauge
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=health.cpu_usage * 100,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "CPU Usage %"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ),
                row=1, col=2
            )
            
            # Error rate trend
            error_metrics = [m for m in recent_metrics if m.metric_name == "error"]
            if error_metrics:
                # Group by hour
                hourly_errors = defaultdict(int)
                for metric in error_metrics:
                    hour = metric.timestamp.replace(minute=0, second=0, microsecond=0)
                    hourly_errors[hour] += 1
                
                hours = sorted(hourly_errors.keys())
                error_counts = [hourly_errors[hour] for hour in hours]
                
                fig.add_trace(
                    go.Scatter(x=hours, y=error_counts, name="Errors/Hour", line=dict(color="red")),
                    row=2, col=1
                )
            
            # Cost breakdown pie chart
            if self.cost_tracking:
                operations = list(self.cost_tracking.keys())
                costs = list(self.cost_tracking.values())
                
                fig.add_trace(
                    go.Pie(labels=operations, values=costs, name="Cost Breakdown"),
                    row=2, col=2
                )
            
            # Request volume by operation
            operation_counts = defaultdict(int)
            for metric in recent_metrics:
                if metric.operation_type:
                    operation_counts[metric.operation_type] += 1
            
            if operation_counts:
                operations = list(operation_counts.keys())
                counts = list(operation_counts.values())
                
                fig.add_trace(
                    go.Bar(x=operations, y=counts, name="Request Volume"),
                    row=3, col=1
                )
            
            # User activity scatter
            user_activity = defaultdict(list)
            for metric in recent_metrics:
                if metric.user_id:
                    user_activity[metric.user_id].append(metric.timestamp)
            
            if user_activity:
                for user_id, timestamps in user_activity.items():
                    fig.add_trace(
                        go.Scatter(
                            x=timestamps, 
                            y=[user_id] * len(timestamps),
                            mode='markers',
                            name=f"User {user_id}",
                            showlegend=False
                        ),
                        row=3, col=2
                    )
            
            # Update layout
            fig.update_layout(
                height=1200,
                title_text="Literature Review System Performance Dashboard",
                title_x=0.5
            )
            
            # Generate HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Performance Dashboard</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .health-status {{ 
                        padding: 20px; margin: 20px 0; border-radius: 10px; 
                        background-color: {"#d4edda" if health.overall_status == "healthy" else "#f8d7da" if health.overall_status == "critical" else "#fff3cd"};
                        border: 1px solid {"#c3e6cb" if health.overall_status == "healthy" else "#f5c6cb" if health.overall_status == "critical" else "#ffeaa7"};
                    }}
                    .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
                    .alert {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; margin: 5px 0; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>Literature Review System Performance Dashboard</h1>
                
                <div class="health-status">
                    <h2>System Health: {health.overall_status.upper()}</h2>
                    <p>Last Updated: {health.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
                    
                    <div class="metric">
                        <strong>Avg Response Time:</strong> {health.avg_response_time:.3f}s
                    </div>
                    <div class="metric">
                        <strong>Error Rate:</strong> {health.error_rate:.2%}
                    </div>
                    <div class="metric">
                        <strong>Throughput:</strong> {health.throughput:.2f} req/s
                    </div>
                    <div class="metric">
                        <strong>CPU Usage:</strong> {health.cpu_usage:.1%}
                    </div>
                    <div class="metric">
                        <strong>Memory Usage:</strong> {health.memory_usage:.1%}
                    </div>
                    <div class="metric">
                        <strong>Daily Cost:</strong> ${health.daily_cost:.2f}
                    </div>
                    <div class="metric">
                        <strong>Active Users:</strong> {health.active_users}
                    </div>
                </div>
                
                {"".join(f'<div class="alert"><strong>ALERT:</strong> {alert}</div>' for alert in health.active_alerts)}
                
                <div id="dashboard-plots">
                    {fig.to_html(include_plotlyjs=False, div_id="dashboard-plots")}
                </div>
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating performance dashboard: {e}")
            return f"<html><body><h1>Error generating dashboard: {e}</h1></body></html>"
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                health = self.get_current_system_health()
                
                # Record system metrics
                self.record_metric("cpu_usage", health.cpu_usage)
                self.record_metric("memory_usage", health.memory_usage)
                self.record_metric("disk_usage", health.disk_usage)
                self.record_metric("error_rate", health.error_rate)
                self.record_metric("daily_cost", health.daily_cost)
                
                # Store system health snapshot
                self.system_metrics.append({
                    "timestamp": datetime.now(),
                    "health": health
                })
                
                # Cleanup old metrics
                self._cleanup_old_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Sleep for 60 seconds
            time.sleep(60)
    
    def _cleanup_old_metrics(self):
        """Remove old metrics to prevent memory issues."""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            # Clean main metrics
            self.metrics = deque(
                (m for m in self.metrics if m.timestamp >= cutoff),
                maxlen=self.max_metrics_in_memory
            )
            
            # Clean metrics by name
            for metric_name, metric_deque in self.metrics_by_name.items():
                metric_deque = deque(
                    (m for m in metric_deque if m.timestamp >= cutoff),
                    maxlen=10000
                )
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff]
            
            # Response time analysis
            response_times = [m.value for m in recent_metrics if m.metric_name == "response_time"]
            response_time_stats = {
                "count": len(response_times),
                "avg": np.mean(response_times) if response_times else 0,
                "median": np.median(response_times) if response_times else 0,
                "p95": np.percentile(response_times, 95) if response_times else 0,
                "p99": np.percentile(response_times, 99) if response_times else 0,
                "max": np.max(response_times) if response_times else 0
            }
            
            # Error analysis
            error_count = len([m for m in recent_metrics if m.metric_name == "error"])
            total_requests = len(response_times)
            error_rate = error_count / max(total_requests, 1)
            
            # Cost analysis
            total_cost = sum(self.cost_tracking.values())
            cost_by_operation = dict(self.cost_tracking)
            cost_by_user = dict(self.user_costs)
            
            # Usage patterns
            operations = defaultdict(int)
            for metric in recent_metrics:
                if metric.operation_type:
                    operations[metric.operation_type] += 1
            
            return {
                "report_period_hours": hours,
                "generated_at": datetime.now().isoformat(),
                "response_time_stats": response_time_stats,
                "error_analysis": {
                    "total_errors": error_count,
                    "error_rate": error_rate,
                    "total_requests": total_requests
                },
                "cost_analysis": {
                    "total_cost": total_cost,
                    "cost_by_operation": cost_by_operation,
                    "cost_by_user": cost_by_user
                },
                "usage_patterns": dict(operations),
                "active_alerts": [
                    {
                        "name": alert.name,
                        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                    }
                    for alert in self.alerts.values() if alert.is_active
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": str(e)}

# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
        _performance_monitor.start_monitoring()
    return _performance_monitor