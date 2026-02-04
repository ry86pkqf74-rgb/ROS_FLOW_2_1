"""
Performance Metrics Dashboard
============================

Interactive dashboard for visualizing optimization performance metrics,
system health, and operational statistics in real-time.

Features:
- Real-time performance graphs
- System health monitoring
- Operation statistics
- Historical trend analysis
- Interactive filtering and drilling down
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
import statistics
import numpy as np

from ..monitoring.real_time_monitor import get_monitor, RealTimeMonitor, SystemHealth


class MetricsDashboard:
    """Performance metrics dashboard with visualization support."""
    
    def __init__(self, monitor: Optional[RealTimeMonitor] = None):
        self.monitor = monitor or get_monitor()
        self.dashboard_config = self._default_dashboard_config()
    
    def _default_dashboard_config(self) -> Dict[str, Any]:
        """Default dashboard configuration."""
        return {
            "refresh_interval": 5,  # seconds
            "history_window": 3600,  # 1 hour in seconds
            "chart_types": {
                "system_health": "line",
                "operation_throughput": "bar",
                "compression_efficiency": "area",
                "error_rates": "gauge"
            },
            "alert_levels": {
                "low": {"color": "#28a745", "threshold": 0.7},
                "medium": {"color": "#ffc107", "threshold": 0.85},
                "high": {"color": "#dc3545", "threshold": 0.95}
            }
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data for frontend rendering."""
        current_time = datetime.now()
        
        return {
            "timestamp": current_time.isoformat(),
            "summary": self._get_summary_stats(),
            "system_health": self._get_system_health_data(),
            "operation_metrics": self._get_operation_metrics(),
            "performance_trends": self._get_performance_trends(),
            "alerts": self._get_active_alerts(),
            "charts": self._get_chart_configs()
        }
    
    def _get_summary_stats(self) -> Dict[str, Any]:
        """Get high-level summary statistics."""
        operation_stats = self.monitor.get_operation_stats()
        current_health = self.monitor.get_current_health()
        
        # Calculate uptime
        start_time = None
        if self.monitor.system_health_history:
            start_time = self.monitor.system_health_history[0].timestamp
        
        uptime_hours = 0
        if start_time:
            uptime_delta = datetime.now() - start_time
            uptime_hours = uptime_delta.total_seconds() / 3600
        
        # Calculate performance score
        performance_score = self._calculate_performance_score(current_health, operation_stats)
        
        return {
            "active_operations": operation_stats["active_operations"],
            "completed_operations": operation_stats["completed_operations"],
            "success_rate": round(operation_stats["success_rate"], 2),
            "avg_processing_time": round(operation_stats["avg_processing_time"], 3),
            "avg_compression_ratio": round(operation_stats["avg_compression_ratio"], 3),
            "system_health_score": performance_score,
            "uptime_hours": round(uptime_hours, 2),
            "total_operations_today": self._get_operations_count_today()
        }
    
    def _get_system_health_data(self) -> Dict[str, Any]:
        """Get system health metrics for visualization."""
        health_history = self.monitor.get_health_history(minutes=60)
        current_health = self.monitor.get_current_health()
        
        if not current_health:
            return {"status": "no_data"}
        
        # Prepare time series data
        timestamps = [h.timestamp.isoformat() for h in health_history]
        cpu_usage = [h.cpu_usage for h in health_history]
        memory_usage = [h.memory_usage for h in health_history]
        
        # Calculate trends
        cpu_trend = self._calculate_trend(cpu_usage)
        memory_trend = self._calculate_trend(memory_usage)
        
        return {
            "current": {
                "cpu_usage": round(current_health.cpu_usage, 2),
                "memory_usage": round(current_health.memory_usage, 2),
                "disk_usage": round(current_health.disk_usage, 2),
                "active_operations": current_health.active_operations,
                "queue_length": current_health.queue_length,
                "response_time_avg": round(current_health.response_time_avg, 3),
                "error_rate": round(current_health.error_rate, 2)
            },
            "trends": {
                "cpu_trend": cpu_trend,
                "memory_trend": memory_trend
            },
            "history": {
                "timestamps": timestamps[-20:],  # Last 20 points for chart
                "cpu_usage": cpu_usage[-20:],
                "memory_usage": memory_usage[-20:],
                "response_times": [h.response_time_avg for h in health_history[-20:]],
                "error_rates": [h.error_rate for h in health_history[-20:]]
            }
        }
    
    def _get_operation_metrics(self) -> Dict[str, Any]:
        """Get operation-specific metrics."""
        operation_stats = self.monitor.get_operation_stats()
        
        # Get operations by type breakdown
        ops_by_type = operation_stats["operations_by_type"]
        
        # Calculate throughput metrics
        throughput_data = self._calculate_throughput_metrics()
        
        # Get compression efficiency data
        compression_data = self._get_compression_efficiency_data()
        
        return {
            "by_type": ops_by_type,
            "throughput": throughput_data,
            "compression": compression_data,
            "quality_metrics": self._get_quality_metrics()
        }
    
    def _get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trend analysis."""
        health_history = self.monitor.get_health_history(minutes=1440)  # 24 hours
        
        if len(health_history) < 2:
            return {"status": "insufficient_data"}
        
        # Group by hour for trend analysis
        hourly_data = self._group_health_data_by_hour(health_history)
        
        trends = {}
        for metric in ["cpu_usage", "memory_usage", "response_time_avg", "error_rate"]:
            values = [hour_data[metric] for hour_data in hourly_data]
            trends[metric] = {
                "trend": self._calculate_trend(values),
                "values": values[-24:],  # Last 24 hours
                "average": round(statistics.mean(values), 2),
                "max": round(max(values), 2),
                "min": round(min(values), 2)
            }
        
        return {
            "hourly_trends": trends,
            "performance_score_trend": self._calculate_performance_score_trend(hourly_data),
            "operation_volume_trend": self._calculate_operation_volume_trend()
        }
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts."""
        current_health = self.monitor.get_current_health()
        if not current_health:
            return []
        
        alerts = []
        
        # Check alert conditions
        if current_health.cpu_usage > 80:
            alerts.append({
                "type": "cpu_high",
                "severity": "warning" if current_health.cpu_usage < 90 else "critical",
                "message": f"High CPU usage: {current_health.cpu_usage:.1f}%",
                "value": current_health.cpu_usage,
                "timestamp": current_health.timestamp.isoformat()
            })
        
        if current_health.memory_usage > 85:
            alerts.append({
                "type": "memory_high",
                "severity": "warning" if current_health.memory_usage < 95 else "critical",
                "message": f"High memory usage: {current_health.memory_usage:.1f}%",
                "value": current_health.memory_usage,
                "timestamp": current_health.timestamp.isoformat()
            })
        
        if current_health.error_rate > 5:
            alerts.append({
                "type": "error_rate_high",
                "severity": "critical",
                "message": f"High error rate: {current_health.error_rate:.1f}%",
                "value": current_health.error_rate,
                "timestamp": current_health.timestamp.isoformat()
            })
        
        if current_health.response_time_avg > 10:
            alerts.append({
                "type": "response_time_high",
                "severity": "warning",
                "message": f"High response time: {current_health.response_time_avg:.2f}s",
                "value": current_health.response_time_avg,
                "timestamp": current_health.timestamp.isoformat()
            })
        
        return alerts
    
    def _get_chart_configs(self) -> Dict[str, Any]:
        """Get chart configuration for frontend rendering."""
        return {
            "system_health_chart": {
                "type": "line",
                "title": "System Health Metrics",
                "y_axis": "Percentage",
                "x_axis": "Time",
                "series": ["CPU Usage", "Memory Usage"],
                "colors": ["#007bff", "#28a745"]
            },
            "operation_throughput_chart": {
                "type": "bar",
                "title": "Operation Throughput",
                "y_axis": "Operations/Hour",
                "x_axis": "Hour",
                "series": ["Completed", "Failed"],
                "colors": ["#28a745", "#dc3545"]
            },
            "compression_efficiency_chart": {
                "type": "area",
                "title": "Compression Efficiency",
                "y_axis": "Compression Ratio",
                "x_axis": "Time",
                "series": ["Compression Ratio"],
                "colors": ["#17a2b8"]
            },
            "response_time_chart": {
                "type": "line",
                "title": "Response Time Trends",
                "y_axis": "Time (seconds)",
                "x_axis": "Time",
                "series": ["Average Response Time"],
                "colors": ["#ffc107"]
            }
        }
    
    def _calculate_performance_score(self, 
                                   health: Optional[SystemHealth], 
                                   operation_stats: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        if not health:
            return 0.0
        
        # Weight different factors
        weights = {
            "cpu_efficiency": 0.2,      # Lower CPU usage is better
            "memory_efficiency": 0.2,   # Lower memory usage is better  
            "response_time": 0.3,       # Lower response time is better
            "success_rate": 0.2,        # Higher success rate is better
            "error_rate": 0.1           # Lower error rate is better
        }
        
        # Calculate individual scores (0-1 scale)
        cpu_score = max(0, (100 - health.cpu_usage) / 100)
        memory_score = max(0, (100 - health.memory_usage) / 100)
        response_score = max(0, 1 - min(health.response_time_avg / 10, 1))  # Cap at 10s
        success_score = operation_stats["success_rate"] / 100
        error_score = max(0, 1 - health.error_rate / 100)
        
        # Weighted average
        total_score = (
            weights["cpu_efficiency"] * cpu_score +
            weights["memory_efficiency"] * memory_score +
            weights["response_time"] * response_score +
            weights["success_rate"] * success_score +
            weights["error_rate"] * error_score
        )
        
        return round(total_score * 100, 2)
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from time series values."""
        if len(values) < 2:
            return "stable"
        
        # Use linear regression to determine trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_throughput_metrics(self) -> Dict[str, Any]:
        """Calculate operation throughput metrics."""
        # Get operations completed in last hour
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_operations = [
            op for op in self.monitor.completed_operations 
            if op.end_time and op.end_time > cutoff_time
        ]
        
        # Group by 5-minute intervals
        intervals = {}
        for op in recent_operations:
            if op.end_time:
                interval = op.end_time.replace(minute=(op.end_time.minute // 5) * 5, second=0, microsecond=0)
                if interval not in intervals:
                    intervals[interval] = {"completed": 0, "failed": 0}
                
                if op.status == "completed":
                    intervals[interval]["completed"] += 1
                else:
                    intervals[interval]["failed"] += 1
        
        # Convert to lists for charting
        timestamps = sorted(intervals.keys())
        completed_counts = [intervals[ts]["completed"] for ts in timestamps]
        failed_counts = [intervals[ts]["failed"] for ts in timestamps]
        
        return {
            "timestamps": [ts.isoformat() for ts in timestamps],
            "completed": completed_counts,
            "failed": failed_counts,
            "total_last_hour": len(recent_operations),
            "avg_per_minute": len(recent_operations) / 60 if recent_operations else 0
        }
    
    def _get_compression_efficiency_data(self) -> Dict[str, Any]:
        """Get compression efficiency metrics."""
        recent_operations = [
            op for op in self.monitor.completed_operations 
            if op.compression_ratio is not None and op.end_time
        ]
        
        if not recent_operations:
            return {"status": "no_data"}
        
        # Sort by completion time
        recent_operations.sort(key=lambda x: x.end_time)
        
        # Get last 50 operations for trending
        trending_ops = recent_operations[-50:]
        
        compression_ratios = [op.compression_ratio for op in trending_ops]
        timestamps = [op.end_time.isoformat() for op in trending_ops]
        
        return {
            "current_average": round(statistics.mean(compression_ratios), 3),
            "trend_data": {
                "timestamps": timestamps,
                "ratios": compression_ratios
            },
            "distribution": self._get_compression_ratio_distribution(compression_ratios),
            "efficiency_score": self._calculate_compression_efficiency_score(compression_ratios)
        }
    
    def _get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality-related metrics."""
        # Mock quality metrics - in real implementation, these would come from quality analyzers
        return {
            "content_preservation": 0.95,
            "processing_accuracy": 0.92,
            "output_consistency": 0.89,
            "user_satisfaction": 0.87,
            "overall_quality_score": 0.91
        }
    
    def _group_health_data_by_hour(self, health_history: List[SystemHealth]) -> List[Dict[str, float]]:
        """Group health data into hourly averages."""
        hourly_groups = {}
        
        for health in health_history:
            hour_key = health.timestamp.replace(minute=0, second=0, microsecond=0)
            
            if hour_key not in hourly_groups:
                hourly_groups[hour_key] = []
            
            hourly_groups[hour_key].append(health)
        
        # Calculate averages for each hour
        hourly_averages = []
        for hour, health_list in sorted(hourly_groups.items()):
            avg_data = {
                "timestamp": hour,
                "cpu_usage": statistics.mean([h.cpu_usage for h in health_list]),
                "memory_usage": statistics.mean([h.memory_usage for h in health_list]),
                "response_time_avg": statistics.mean([h.response_time_avg for h in health_list]),
                "error_rate": statistics.mean([h.error_rate for h in health_list])
            }
            hourly_averages.append(avg_data)
        
        return hourly_averages
    
    def _calculate_performance_score_trend(self, hourly_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance score trend over time."""
        if not hourly_data:
            return {"status": "no_data"}
        
        performance_scores = []
        for hour_data in hourly_data:
            # Mock operation stats for trending - in real implementation, calculate from actual data
            mock_operation_stats = {"success_rate": 95.0}
            
            # Create temporary health object
            temp_health = SystemHealth(
                timestamp=hour_data["timestamp"],
                cpu_usage=hour_data["cpu_usage"],
                memory_usage=hour_data["memory_usage"],
                disk_usage=50.0,  # Mock value
                active_operations=5,  # Mock value
                queue_length=2,  # Mock value
                response_time_avg=hour_data["response_time_avg"],
                error_rate=hour_data["error_rate"]
            )
            
            score = self._calculate_performance_score(temp_health, mock_operation_stats)
            performance_scores.append(score)
        
        return {
            "scores": performance_scores[-24:],  # Last 24 hours
            "trend": self._calculate_trend(performance_scores),
            "average": round(statistics.mean(performance_scores), 2),
            "current": performance_scores[-1] if performance_scores else 0
        }
    
    def _calculate_operation_volume_trend(self) -> Dict[str, Any]:
        """Calculate operation volume trends."""
        # Group completed operations by hour
        now = datetime.now()
        hourly_volumes = {}
        
        # Initialize last 24 hours
        for i in range(24):
            hour = now - timedelta(hours=i)
            hour_key = hour.replace(minute=0, second=0, microsecond=0)
            hourly_volumes[hour_key] = 0
        
        # Count operations per hour
        for op in self.monitor.completed_operations:
            if op.end_time:
                hour_key = op.end_time.replace(minute=0, second=0, microsecond=0)
                if hour_key in hourly_volumes:
                    hourly_volumes[hour_key] += 1
        
        # Convert to lists
        sorted_hours = sorted(hourly_volumes.keys())
        volumes = [hourly_volumes[hour] for hour in sorted_hours]
        
        return {
            "hourly_volumes": volumes,
            "timestamps": [hour.isoformat() for hour in sorted_hours],
            "trend": self._calculate_trend(volumes),
            "peak_hour_volume": max(volumes) if volumes else 0,
            "avg_hourly_volume": round(statistics.mean(volumes), 2) if volumes else 0
        }
    
    def _get_operations_count_today(self) -> int:
        """Get count of operations completed today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_operations = [
            op for op in self.monitor.completed_operations 
            if op.end_time and op.end_time >= today_start
        ]
        return len(today_operations)
    
    def _get_compression_ratio_distribution(self, ratios: List[float]) -> Dict[str, int]:
        """Get distribution of compression ratios."""
        if not ratios:
            return {}
        
        # Define buckets
        buckets = {
            "excellent": 0,  # < 0.5
            "good": 0,       # 0.5 - 0.7
            "fair": 0,       # 0.7 - 0.85
            "poor": 0        # > 0.85
        }
        
        for ratio in ratios:
            if ratio < 0.5:
                buckets["excellent"] += 1
            elif ratio < 0.7:
                buckets["good"] += 1
            elif ratio < 0.85:
                buckets["fair"] += 1
            else:
                buckets["poor"] += 1
        
        return buckets
    
    def _calculate_compression_efficiency_score(self, ratios: List[float]) -> float:
        """Calculate compression efficiency score."""
        if not ratios:
            return 0.0
        
        # Lower compression ratio is better (more compression)
        avg_ratio = statistics.mean(ratios)
        
        # Score based on average ratio (inverted, so lower ratio = higher score)
        if avg_ratio <= 0.5:
            return 1.0
        elif avg_ratio <= 0.7:
            return 0.8
        elif avg_ratio <= 0.85:
            return 0.6
        else:
            return 0.4
    
    def export_dashboard_data(self, format: str = "json") -> str:
        """Export dashboard data for external use."""
        dashboard_data = self.get_dashboard_data()
        
        if format.lower() == "json":
            return json.dumps(dashboard_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_custom_metrics(self, metric_names: List[str], time_range_hours: int = 1) -> Dict[str, List[Any]]:
        """Get custom metrics for specific analysis."""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        health_history = [h for h in self.monitor.system_health_history if h.timestamp > cutoff_time]
        
        custom_data = {}
        
        for metric_name in metric_names:
            if hasattr(SystemHealth, metric_name):
                custom_data[metric_name] = [
                    {
                        "timestamp": h.timestamp.isoformat(),
                        "value": getattr(h, metric_name)
                    }
                    for h in health_history
                ]
        
        return custom_data


# Dashboard API endpoints (for integration with web interface)
def create_dashboard_api_routes():
    """Create API routes for dashboard data (FastAPI integration)."""
    try:
        from fastapi import APIRouter, HTTPException
        from fastapi.responses import JSONResponse
        
        router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
        dashboard = MetricsDashboard()
        
        @router.get("/")
        async def get_dashboard_data():
            """Get complete dashboard data."""
            try:
                data = dashboard.get_dashboard_data()
                return JSONResponse(content=data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/summary")
        async def get_summary():
            """Get dashboard summary."""
            try:
                data = dashboard._get_summary_stats()
                return JSONResponse(content=data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/health")
        async def get_system_health():
            """Get system health data."""
            try:
                data = dashboard._get_system_health_data()
                return JSONResponse(content=data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/operations")
        async def get_operation_metrics():
            """Get operation metrics."""
            try:
                data = dashboard._get_operation_metrics()
                return JSONResponse(content=data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/alerts")
        async def get_active_alerts():
            """Get active alerts."""
            try:
                data = dashboard._get_active_alerts()
                return JSONResponse(content=data)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.get("/export")
        async def export_dashboard_data(format: str = "json"):
            """Export dashboard data."""
            try:
                data = dashboard.export_dashboard_data(format)
                return JSONResponse(content={"export_data": data})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return router
    
    except ImportError:
        # FastAPI not available, return None
        return None


if __name__ == "__main__":
    # Example usage
    dashboard = MetricsDashboard()
    
    # Get dashboard data
    data = dashboard.get_dashboard_data()
    print(json.dumps(data, indent=2, default=str))
    
    # Export dashboard data
    export = dashboard.export_dashboard_data()
    print("\nDashboard data exported successfully")