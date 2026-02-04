"""
Real-time Optimization Monitoring System
=======================================

Advanced monitoring system for tracking optimization operations,
performance metrics, and system health in real-time.

Features:
- Live performance tracking
- Resource utilization monitoring
- Operation status dashboards
- Alert system for anomalies
- Historical trend analysis
"""

import asyncio
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    operation_id: Optional[str] = None
    component: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class SystemHealth:
    """System health snapshot."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_operations: int
    queue_length: int
    response_time_avg: float
    error_rate: float


@dataclass
class OptimizationOperation:
    """Optimization operation tracking."""
    operation_id: str
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # 'running', 'completed', 'failed', 'queued'
    input_size: int
    output_size: Optional[int]
    compression_ratio: Optional[float]
    processing_time: Optional[float]
    resource_usage: Dict[str, float]
    error_message: Optional[str] = None


class RealTimeMonitor:
    """Real-time monitoring system for optimization operations."""
    
    def __init__(self, 
                 max_history_points: int = 1000,
                 metrics_interval: float = 1.0,
                 alert_thresholds: Optional[Dict[str, float]] = None):
        self.max_history_points = max_history_points
        self.metrics_interval = metrics_interval
        self.alert_thresholds = alert_thresholds or self._default_alert_thresholds()
        
        # Data storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_points))
        self.system_health_history: deque = deque(maxlen=max_history_points)
        self.active_operations: Dict[str, OptimizationOperation] = {}
        self.completed_operations: deque = deque(maxlen=max_history_points)
        
        # Monitoring control
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Event callbacks
        self.alert_callbacks: List[Callable] = []
        self.metric_callbacks: List[Callable] = []
        
    def _default_alert_thresholds(self) -> Dict[str, float]:
        """Default alert thresholds for system metrics."""
        return {
            "cpu_usage_high": 80.0,
            "memory_usage_high": 85.0,
            "disk_usage_high": 90.0,
            "error_rate_high": 5.0,
            "response_time_high": 10.0,
            "queue_length_high": 100
        }
    
    async def start_monitoring(self):
        """Start real-time monitoring."""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Real-time monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect system metrics
                health = self._collect_system_health()
                self.system_health_history.append(health)
                
                # Check for alerts
                await self._check_alerts(health)
                
                # Notify metric callbacks
                await self._notify_metric_callbacks(health)
                
                # Clean up completed operations
                self._cleanup_old_operations()
                
                await asyncio.sleep(self.metrics_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.metrics_interval)
    
    def _collect_system_health(self) -> SystemHealth:
        """Collect current system health metrics."""
        # CPU and memory usage
        cpu_usage = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Operation metrics
        active_ops = len(self.active_operations)
        queue_length = self._get_queue_length()
        
        # Performance metrics
        response_times = self._get_recent_response_times()
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        error_rate = self._calculate_error_rate()
        
        return SystemHealth(
            timestamp=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            active_operations=active_ops,
            queue_length=queue_length,
            response_time_avg=avg_response_time,
            error_rate=error_rate
        )
    
    def _get_queue_length(self) -> int:
        """Get current operation queue length."""
        # Count queued operations
        queued_count = sum(1 for op in self.active_operations.values() if op.status == 'queued')
        return queued_count
    
    def _get_recent_response_times(self) -> List[float]:
        """Get recent response times from completed operations."""
        cutoff_time = datetime.now() - timedelta(minutes=5)
        recent_ops = [op for op in self.completed_operations 
                     if op.end_time and op.end_time > cutoff_time and op.processing_time]
        return [op.processing_time for op in recent_ops]
    
    def _calculate_error_rate(self) -> float:
        """Calculate recent error rate percentage."""
        cutoff_time = datetime.now() - timedelta(minutes=5)
        recent_ops = [op for op in self.completed_operations 
                     if op.end_time and op.end_time > cutoff_time]
        
        if not recent_ops:
            return 0.0
        
        failed_ops = sum(1 for op in recent_ops if op.status == 'failed')
        return (failed_ops / len(recent_ops)) * 100
    
    async def _check_alerts(self, health: SystemHealth):
        """Check for alert conditions and notify callbacks."""
        alerts = []
        
        # CPU usage alert
        if health.cpu_usage > self.alert_thresholds["cpu_usage_high"]:
            alerts.append({
                "type": "cpu_high",
                "message": f"High CPU usage: {health.cpu_usage:.1f}%",
                "severity": "warning",
                "value": health.cpu_usage,
                "threshold": self.alert_thresholds["cpu_usage_high"]
            })
        
        # Memory usage alert
        if health.memory_usage > self.alert_thresholds["memory_usage_high"]:
            alerts.append({
                "type": "memory_high",
                "message": f"High memory usage: {health.memory_usage:.1f}%",
                "severity": "warning",
                "value": health.memory_usage,
                "threshold": self.alert_thresholds["memory_usage_high"]
            })
        
        # Disk usage alert
        if health.disk_usage > self.alert_thresholds["disk_usage_high"]:
            alerts.append({
                "type": "disk_high",
                "message": f"High disk usage: {health.disk_usage:.1f}%",
                "severity": "critical",
                "value": health.disk_usage,
                "threshold": self.alert_thresholds["disk_usage_high"]
            })
        
        # Error rate alert
        if health.error_rate > self.alert_thresholds["error_rate_high"]:
            alerts.append({
                "type": "error_rate_high",
                "message": f"High error rate: {health.error_rate:.1f}%",
                "severity": "critical",
                "value": health.error_rate,
                "threshold": self.alert_thresholds["error_rate_high"]
            })
        
        # Response time alert
        if health.response_time_avg > self.alert_thresholds["response_time_high"]:
            alerts.append({
                "type": "response_time_high",
                "message": f"High response time: {health.response_time_avg:.2f}s",
                "severity": "warning",
                "value": health.response_time_avg,
                "threshold": self.alert_thresholds["response_time_high"]
            })
        
        # Queue length alert
        if health.queue_length > self.alert_thresholds["queue_length_high"]:
            alerts.append({
                "type": "queue_length_high",
                "message": f"High queue length: {health.queue_length}",
                "severity": "warning",
                "value": health.queue_length,
                "threshold": self.alert_thresholds["queue_length_high"]
            })
        
        # Notify alert callbacks
        for alert in alerts:
            await self._notify_alert_callbacks(alert)
    
    async def _notify_alert_callbacks(self, alert: Dict[str, Any]):
        """Notify registered alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _notify_metric_callbacks(self, health: SystemHealth):
        """Notify registered metric callbacks."""
        for callback in self.metric_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(health)
                else:
                    callback(health)
            except Exception as e:
                logger.error(f"Error in metric callback: {e}")
    
    def _cleanup_old_operations(self):
        """Clean up old completed operations."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Remove old completed operations
        while (self.completed_operations and 
               self.completed_operations[0].end_time and 
               self.completed_operations[0].end_time < cutoff_time):
            self.completed_operations.popleft()
    
    def start_operation(self, 
                       operation_id: str, 
                       operation_type: str, 
                       input_size: int) -> OptimizationOperation:
        """Register start of optimization operation."""
        operation = OptimizationOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now(),
            end_time=None,
            status='running',
            input_size=input_size,
            output_size=None,
            compression_ratio=None,
            processing_time=None,
            resource_usage={}
        )
        
        self.active_operations[operation_id] = operation
        logger.info(f"Started monitoring operation {operation_id} ({operation_type})")
        return operation
    
    def update_operation(self, 
                        operation_id: str, 
                        status: Optional[str] = None,
                        output_size: Optional[int] = None,
                        resource_usage: Optional[Dict[str, float]] = None,
                        error_message: Optional[str] = None):
        """Update operation status and metrics."""
        if operation_id not in self.active_operations:
            logger.warning(f"Operation {operation_id} not found for update")
            return
        
        operation = self.active_operations[operation_id]
        
        if status:
            operation.status = status
        
        if output_size is not None:
            operation.output_size = output_size
            if operation.input_size > 0:
                operation.compression_ratio = output_size / operation.input_size
        
        if resource_usage:
            operation.resource_usage.update(resource_usage)
        
        if error_message:
            operation.error_message = error_message
    
    def complete_operation(self, operation_id: str, success: bool = True):
        """Mark operation as completed."""
        if operation_id not in self.active_operations:
            logger.warning(f"Operation {operation_id} not found for completion")
            return
        
        operation = self.active_operations[operation_id]
        operation.end_time = datetime.now()
        operation.status = 'completed' if success else 'failed'
        
        if operation.start_time:
            operation.processing_time = (operation.end_time - operation.start_time).total_seconds()
        
        # Move to completed operations
        self.completed_operations.append(operation)
        del self.active_operations[operation_id]
        
        logger.info(f"Completed operation {operation_id} (status: {operation.status})")
    
    def add_metric(self, metric: PerformanceMetric):
        """Add custom performance metric."""
        self.metrics_history[metric.metric_name].append(metric)
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health snapshot."""
        if self.system_health_history:
            return self.system_health_history[-1]
        return None
    
    def get_health_history(self, minutes: int = 60) -> List[SystemHealth]:
        """Get system health history for specified time period."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [h for h in self.system_health_history if h.timestamp > cutoff_time]
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """Get operation statistics."""
        active_ops = list(self.active_operations.values())
        completed_ops = list(self.completed_operations)
        
        # Calculate statistics
        total_operations = len(active_ops) + len(completed_ops)
        success_rate = 0.0
        avg_processing_time = 0.0
        avg_compression_ratio = 0.0
        
        if completed_ops:
            successful_ops = [op for op in completed_ops if op.status == 'completed']
            success_rate = len(successful_ops) / len(completed_ops) * 100
            
            processing_times = [op.processing_time for op in completed_ops if op.processing_time]
            if processing_times:
                avg_processing_time = sum(processing_times) / len(processing_times)
            
            compression_ratios = [op.compression_ratio for op in completed_ops if op.compression_ratio]
            if compression_ratios:
                avg_compression_ratio = sum(compression_ratios) / len(compression_ratios)
        
        return {
            "total_operations": total_operations,
            "active_operations": len(active_ops),
            "completed_operations": len(completed_ops),
            "success_rate": success_rate,
            "avg_processing_time": avg_processing_time,
            "avg_compression_ratio": avg_compression_ratio,
            "operations_by_type": self._get_operations_by_type()
        }
    
    def _get_operations_by_type(self) -> Dict[str, int]:
        """Get operation counts by type."""
        type_counts = defaultdict(int)
        
        for op in self.active_operations.values():
            type_counts[op.operation_type] += 1
        
        for op in self.completed_operations:
            type_counts[op.operation_type] += 1
        
        return dict(type_counts)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        current_health = self.get_current_health()
        operation_stats = self.get_operation_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": asdict(current_health) if current_health else None,
            "operation_stats": operation_stats,
            "alerts_active": len([h for h in self.system_health_history[-1:] if h.cpu_usage > 80]) > 0 if self.system_health_history else False,
            "monitoring_status": "active" if self.is_monitoring else "inactive"
        }
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts."""
        self.alert_callbacks.append(callback)
    
    def register_metric_callback(self, callback: Callable):
        """Register callback for metrics."""
        self.metric_callbacks.append(callback)
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "system_health_history": [asdict(h) for h in self.system_health_history],
            "active_operations": [asdict(op) for op in self.active_operations.values()],
            "completed_operations": [asdict(op) for op in self.completed_operations],
            "metrics_history": {
                name: [asdict(m) for m in metrics] 
                for name, metrics in self.metrics_history.items()
            }
        }
        
        if format.lower() == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global monitor instance
_global_monitor: Optional[RealTimeMonitor] = None


def get_monitor() -> RealTimeMonitor:
    """Get global monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = RealTimeMonitor()
    return _global_monitor


async def start_global_monitoring():
    """Start global monitoring."""
    monitor = get_monitor()
    await monitor.start_monitoring()


async def stop_global_monitoring():
    """Stop global monitoring."""
    global _global_monitor
    if _global_monitor:
        await _global_monitor.stop_monitoring()


# Context manager for operation monitoring
class MonitorOperation:
    """Context manager for monitoring optimization operations."""
    
    def __init__(self, operation_type: str, input_size: int, monitor: Optional[RealTimeMonitor] = None):
        self.operation_type = operation_type
        self.input_size = input_size
        self.monitor = monitor or get_monitor()
        self.operation_id = f"{operation_type}_{int(time.time() * 1000)}"
        self.operation = None
    
    def __enter__(self):
        self.operation = self.monitor.start_operation(
            self.operation_id, 
            self.operation_type, 
            self.input_size
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        if not success and exc_val:
            self.monitor.update_operation(
                self.operation_id, 
                error_message=str(exc_val)
            )
        
        self.monitor.complete_operation(self.operation_id, success)
    
    def update(self, **kwargs):
        """Update operation metrics."""
        self.monitor.update_operation(self.operation_id, **kwargs)


if __name__ == "__main__":
    # Example usage
    async def main():
        monitor = RealTimeMonitor()
        
        # Register alert callback
        async def alert_handler(alert):
            print(f"ALERT: {alert['message']}")
        
        monitor.register_alert_callback(alert_handler)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Simulate operation
        with MonitorOperation("compression", 1024000, monitor) as op:
            await asyncio.sleep(2)
            op.update(output_size=819200)
        
        # Get metrics
        print(json.dumps(monitor.get_metrics_summary(), indent=2))
        
        await monitor.stop_monitoring()
    
    asyncio.run(main())