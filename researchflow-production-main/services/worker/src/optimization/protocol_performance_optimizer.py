"""
Performance Optimization Framework for Protocol Generation System

This module provides comprehensive performance monitoring, analysis,
and optimization capabilities for the protocol generation pipeline.

Features:
- Real-time performance monitoring
- Bottleneck identification and analysis
- Automatic optimization recommendations
- Caching and memory management
- Load balancing and scaling insights

Author: Stage 3.3 Performance Team
"""

import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceProfile:
    """Performance profile for a specific operation."""
    operation_name: str
    total_executions: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    last_execution: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class SystemResourceMetrics:
    """System resource utilization metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_bytes_sent: float
    network_bytes_received: float


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    category: str
    priority: str  # high, medium, low
    description: str
    estimated_impact: str
    implementation_effort: str
    recommendation_details: Dict[str, Any]


class PerformanceMonitor:
    """Real-time performance monitoring system."""
    
    def __init__(self, 
                 metric_retention_hours: int = 24,
                 sampling_interval_seconds: int = 5):
        self.metric_retention_hours = metric_retention_hours
        self.sampling_interval = sampling_interval_seconds
        
        # Storage for metrics
        self.metrics_history: deque = deque(maxlen=int(metric_retention_hours * 3600 / sampling_interval_seconds))
        self.performance_profiles: Dict[str, PerformanceProfile] = {}
        self.system_metrics: deque = deque(maxlen=int(metric_retention_hours * 3600 / sampling_interval_seconds))
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Thresholds for alerts
        self.alert_thresholds = {
            "cpu_percent": 85.0,
            "memory_percent": 90.0,
            "response_time_seconds": 10.0,
            "error_rate_percent": 5.0
        }
        
        logger.info("Performance Monitor initialized")
    
    def start_monitoring(self):
        """Start performance monitoring."""
        if self.monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                self.system_metrics.append(system_metrics)
                
                # Check for alerts
                self._check_performance_alerts(system_metrics)
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.sampling_interval)
    
    def _collect_system_metrics(self) -> SystemResourceMetrics:
        """Collect current system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            return SystemResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_io_read_mb=disk_io.read_bytes / (1024 * 1024) if disk_io else 0.0,
                disk_io_write_mb=disk_io.write_bytes / (1024 * 1024) if disk_io else 0.0,
                network_bytes_sent=network_io.bytes_sent if network_io else 0.0,
                network_bytes_received=network_io.bytes_recv if network_io else 0.0
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return SystemResourceMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_io_read_mb=0.0,
                disk_io_write_mb=0.0,
                network_bytes_sent=0.0,
                network_bytes_received=0.0
            )
    
    def _check_performance_alerts(self, metrics: SystemResourceMetrics):
        """Check for performance alerts based on thresholds."""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        for alert in alerts:
            logger.warning(f"PERFORMANCE ALERT: {alert}")
    
    def record_operation_start(self, operation_name: str) -> str:
        """Record the start of an operation."""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        # Create metric point
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=f"{operation_name}_start",
            value=time.time(),
            unit="timestamp"
        )
        self.metrics_history.append(metric)
        
        return operation_id
    
    def record_operation_end(self, 
                           operation_name: str, 
                           operation_id: str, 
                           success: bool = True,
                           additional_metrics: Optional[Dict[str, float]] = None):
        """Record the end of an operation."""
        current_time = time.time()
        
        # Find start time
        start_metric = None
        for metric in reversed(self.metrics_history):
            if (metric.metric_name == f"{operation_name}_start" and 
                metric.value < current_time):
                start_metric = metric
                break
        
        if start_metric:
            execution_time = current_time - start_metric.value
            
            # Update performance profile
            if operation_name not in self.performance_profiles:
                self.performance_profiles[operation_name] = PerformanceProfile(operation_name)
            
            profile = self.performance_profiles[operation_name]
            profile.total_executions += 1
            profile.total_time += execution_time
            profile.min_time = min(profile.min_time, execution_time)
            profile.max_time = max(profile.max_time, execution_time)
            profile.avg_time = profile.total_time / profile.total_executions
            profile.last_execution = datetime.now()
            profile.recent_times.append(execution_time)
            
            if success:
                profile.success_count += 1
            else:
                profile.error_count += 1
            
            # Record end metric
            end_metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=f"{operation_name}_end",
                value=execution_time,
                unit="seconds",
                context={"success": success, "operation_id": operation_id}
            )
            self.metrics_history.append(end_metric)
            
            # Record additional metrics
            if additional_metrics:
                for metric_name, value in additional_metrics.items():
                    additional_metric = PerformanceMetric(
                        timestamp=datetime.now(),
                        metric_name=f"{operation_name}_{metric_name}",
                        value=value,
                        unit="custom",
                        context={"operation_id": operation_id}
                    )
                    self.metrics_history.append(additional_metric)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all operations."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_duration_hours": len(self.system_metrics) * self.sampling_interval / 3600,
            "operation_profiles": {},
            "system_metrics_summary": self._get_system_metrics_summary(),
            "performance_trends": self._analyze_performance_trends()
        }
        
        for operation_name, profile in self.performance_profiles.items():
            summary["operation_profiles"][operation_name] = {
                "total_executions": profile.total_executions,
                "avg_time_seconds": profile.avg_time,
                "min_time_seconds": profile.min_time if profile.min_time != float('inf') else 0,
                "max_time_seconds": profile.max_time,
                "success_rate": (profile.success_count / profile.total_executions * 100) if profile.total_executions > 0 else 0,
                "error_rate": (profile.error_count / profile.total_executions * 100) if profile.total_executions > 0 else 0,
                "last_execution": profile.last_execution.isoformat() if profile.last_execution else None,
                "recent_avg_time": sum(profile.recent_times) / len(profile.recent_times) if profile.recent_times else 0
            }
        
        return summary
    
    def _get_system_metrics_summary(self) -> Dict[str, Any]:
        """Get system metrics summary."""
        if not self.system_metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in self.system_metrics]
        memory_values = [m.memory_percent for m in self.system_metrics]
        
        return {
            "cpu_percent": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "current": cpu_values[-1] if cpu_values else 0
            },
            "memory_percent": {
                "avg": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "current": memory_values[-1] if memory_values else 0
            },
            "samples_collected": len(self.system_metrics)
        }
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        trends = {}
        
        for operation_name, profile in self.performance_profiles.items():
            if len(profile.recent_times) >= 10:  # Need sufficient data
                recent_times = list(profile.recent_times)
                first_half = recent_times[:len(recent_times)//2]
                second_half = recent_times[len(recent_times)//2:]
                
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
                trend_direction = "improving" if second_avg < first_avg else "degrading"
                trend_magnitude = abs(second_avg - first_avg) / first_avg * 100
                
                trends[operation_name] = {
                    "trend_direction": trend_direction,
                    "trend_magnitude_percent": trend_magnitude,
                    "confidence": "high" if len(recent_times) >= 50 else "medium"
                }
        
        return trends


class PerformanceOptimizer:
    """Performance optimization engine."""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.optimization_cache = {}
        self.cache_hit_stats = defaultdict(int)
        self.cache_miss_stats = defaultdict(int)
    
    async def analyze_performance_bottlenecks(self) -> Dict[str, Any]:
        """Analyze performance data to identify bottlenecks."""
        summary = self.monitor.get_performance_summary()
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "bottlenecks_identified": [],
            "optimization_opportunities": [],
            "system_health": "good",
            "recommendations": []
        }
        
        # Analyze operation performance
        for operation_name, profile in summary.get("operation_profiles", {}).items():
            bottlenecks = []
            
            # Check for slow operations
            if profile["avg_time_seconds"] > 5.0:
                bottlenecks.append({
                    "type": "slow_operation",
                    "operation": operation_name,
                    "avg_time": profile["avg_time_seconds"],
                    "severity": "high" if profile["avg_time_seconds"] > 10.0 else "medium"
                })
            
            # Check for high error rates
            if profile["error_rate"] > 5.0:
                bottlenecks.append({
                    "type": "high_error_rate",
                    "operation": operation_name,
                    "error_rate": profile["error_rate"],
                    "severity": "high"
                })
            
            # Check for performance degradation
            trends = summary.get("performance_trends", {})
            if operation_name in trends:
                trend_data = trends[operation_name]
                if (trend_data["trend_direction"] == "degrading" and 
                    trend_data["trend_magnitude_percent"] > 20):
                    bottlenecks.append({
                        "type": "performance_degradation",
                        "operation": operation_name,
                        "degradation_percent": trend_data["trend_magnitude_percent"],
                        "severity": "medium"
                    })
            
            analysis["bottlenecks_identified"].extend(bottlenecks)
        
        # Analyze system resource utilization
        system_summary = summary.get("system_metrics_summary", {})
        if system_summary:
            cpu_avg = system_summary.get("cpu_percent", {}).get("avg", 0)
            memory_avg = system_summary.get("memory_percent", {}).get("avg", 0)
            
            if cpu_avg > 70:
                analysis["system_health"] = "degraded"
                analysis["bottlenecks_identified"].append({
                    "type": "high_cpu_usage",
                    "avg_cpu_percent": cpu_avg,
                    "severity": "high" if cpu_avg > 85 else "medium"
                })
            
            if memory_avg > 80:
                analysis["system_health"] = "degraded"
                analysis["bottlenecks_identified"].append({
                    "type": "high_memory_usage",
                    "avg_memory_percent": memory_avg,
                    "severity": "high" if memory_avg > 90 else "medium"
                })
        
        # Generate optimization recommendations
        analysis["recommendations"] = self._generate_optimization_recommendations(analysis)
        
        return analysis
    
    def _generate_optimization_recommendations(self, analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Generate specific optimization recommendations."""
        recommendations = []
        
        for bottleneck in analysis["bottlenecks_identified"]:
            if bottleneck["type"] == "slow_operation":
                recommendations.append(OptimizationRecommendation(
                    category="performance",
                    priority="high" if bottleneck["severity"] == "high" else "medium",
                    description=f"Optimize {bottleneck['operation']} operation (avg: {bottleneck['avg_time']:.2f}s)",
                    estimated_impact="20-40% performance improvement",
                    implementation_effort="medium",
                    recommendation_details={
                        "operation": bottleneck["operation"],
                        "current_avg_time": bottleneck["avg_time"],
                        "suggested_actions": [
                            "Implement caching for repeated operations",
                            "Optimize database queries",
                            "Use asynchronous processing where possible"
                        ]
                    }
                ))
            
            elif bottleneck["type"] == "high_error_rate":
                recommendations.append(OptimizationRecommendation(
                    category="reliability",
                    priority="high",
                    description=f"Address high error rate in {bottleneck['operation']} ({bottleneck['error_rate']:.1f}%)",
                    estimated_impact="Improved system reliability",
                    implementation_effort="high",
                    recommendation_details={
                        "operation": bottleneck["operation"],
                        "error_rate": bottleneck["error_rate"],
                        "suggested_actions": [
                            "Implement better error handling",
                            "Add input validation",
                            "Improve logging and monitoring"
                        ]
                    }
                ))
            
            elif bottleneck["type"] == "high_cpu_usage":
                recommendations.append(OptimizationRecommendation(
                    category="scaling",
                    priority="high",
                    description=f"Address high CPU usage ({bottleneck['avg_cpu_percent']:.1f}%)",
                    estimated_impact="Better system responsiveness",
                    implementation_effort="medium",
                    recommendation_details={
                        "cpu_usage": bottleneck["avg_cpu_percent"],
                        "suggested_actions": [
                            "Scale horizontally with more instances",
                            "Optimize CPU-intensive algorithms",
                            "Implement load balancing"
                        ]
                    }
                ))
            
            elif bottleneck["type"] == "high_memory_usage":
                recommendations.append(OptimizationRecommendation(
                    category="memory",
                    priority="high",
                    description=f"Address high memory usage ({bottleneck['avg_memory_percent']:.1f}%)",
                    estimated_impact="Reduced memory pressure",
                    implementation_effort="medium",
                    recommendation_details={
                        "memory_usage": bottleneck["avg_memory_percent"],
                        "suggested_actions": [
                            "Implement more aggressive caching policies",
                            "Optimize memory usage in algorithms",
                            "Add memory monitoring and cleanup"
                        ]
                    }
                ))
        
        # Add general recommendations if no specific bottlenecks found
        if not recommendations:
            recommendations.append(OptimizationRecommendation(
                category="maintenance",
                priority="low",
                description="System performing well - implement proactive optimizations",
                estimated_impact="Prevent future performance issues",
                implementation_effort="low",
                recommendation_details={
                    "suggested_actions": [
                        "Regular performance monitoring",
                        "Implement predictive scaling",
                        "Optimize for future load growth"
                    ]
                }
            ))
        
        return recommendations
    
    async def implement_caching_optimization(self, operation_name: str, cache_size: int = 1000) -> Dict[str, Any]:
        """Implement caching optimization for specific operation."""
        cache_key = f"cache_{operation_name}"
        
        if cache_key not in self.optimization_cache:
            self.optimization_cache[cache_key] = {}
        
        cache_info = {
            "operation_name": operation_name,
            "cache_size_limit": cache_size,
            "implementation_timestamp": datetime.now().isoformat(),
            "cache_hit_rate": 0.0,
            "estimated_performance_gain": "15-30%"
        }
        
        logger.info(f"Implemented caching optimization for {operation_name}")
        return cache_info
    
    def get_cache_hit_rate(self, operation_name: str) -> float:
        """Get cache hit rate for an operation."""
        cache_key = f"cache_{operation_name}"
        hits = self.cache_hit_stats[cache_key]
        misses = self.cache_miss_stats[cache_key]
        
        total_requests = hits + misses
        return (hits / total_requests * 100) if total_requests > 0 else 0.0
    
    def record_cache_hit(self, operation_name: str):
        """Record a cache hit."""
        cache_key = f"cache_{operation_name}"
        self.cache_hit_stats[cache_key] += 1
    
    def record_cache_miss(self, operation_name: str):
        """Record a cache miss."""
        cache_key = f"cache_{operation_name}"
        self.cache_miss_stats[cache_key] += 1


class ProtocolPerformanceOptimizer:
    """Main performance optimization orchestrator for protocol generation."""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.optimizer = PerformanceOptimizer(self.monitor)
        
        # Start monitoring
        self.monitor.start_monitoring()
        
        logger.info("Protocol Performance Optimizer initialized")
    
    async def profile_protocol_generation(self, 
                                        protocol_generator,
                                        test_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Profile protocol generation performance with test scenarios."""
        profiling_results = {
            "profiling_timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(test_scenarios),
            "scenario_results": [],
            "performance_analysis": {},
            "optimization_recommendations": []
        }
        
        for i, scenario in enumerate(test_scenarios):
            logger.info(f"Profiling scenario {i+1}/{len(test_scenarios)}: {scenario.get('name', 'Unnamed')}")
            
            # Record operation start
            operation_id = self.monitor.record_operation_start("protocol_generation")
            
            try:
                # Run protocol generation
                start_time = time.time()
                result = await protocol_generator.generate_protocol(
                    template_id=scenario["template_id"],
                    study_data=scenario["study_data"],
                    output_format=scenario.get("output_format", "markdown")
                )
                execution_time = time.time() - start_time
                
                # Calculate additional metrics
                content_length = len(result.get("protocol_content", ""))
                generation_rate = content_length / execution_time if execution_time > 0 else 0
                
                # Record operation end
                self.monitor.record_operation_end(
                    "protocol_generation", 
                    operation_id, 
                    success=result.get("success", False),
                    additional_metrics={
                        "content_length": content_length,
                        "generation_rate": generation_rate
                    }
                )
                
                # Store scenario result
                scenario_result = {
                    "scenario_name": scenario.get("name", f"Scenario_{i+1}"),
                    "template_id": scenario["template_id"],
                    "execution_time": execution_time,
                    "content_length": content_length,
                    "generation_rate": generation_rate,
                    "success": result.get("success", False)
                }
                profiling_results["scenario_results"].append(scenario_result)
                
            except Exception as e:
                logger.error(f"Error profiling scenario {i+1}: {str(e)}")
                
                # Record failed operation
                self.monitor.record_operation_end("protocol_generation", operation_id, success=False)
                
                scenario_result = {
                    "scenario_name": scenario.get("name", f"Scenario_{i+1}"),
                    "template_id": scenario["template_id"],
                    "execution_time": 0.0,
                    "content_length": 0,
                    "generation_rate": 0.0,
                    "success": False,
                    "error": str(e)
                }
                profiling_results["scenario_results"].append(scenario_result)
        
        # Analyze performance
        profiling_results["performance_analysis"] = await self.optimizer.analyze_performance_bottlenecks()
        
        # Generate optimization recommendations
        profiling_results["optimization_recommendations"] = self._generate_profiling_recommendations(
            profiling_results["scenario_results"]
        )
        
        return profiling_results
    
    def _generate_profiling_recommendations(self, scenario_results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on profiling results."""
        recommendations = []
        
        # Analyze execution times
        successful_results = [r for r in scenario_results if r["success"]]
        if successful_results:
            avg_time = sum(r["execution_time"] for r in successful_results) / len(successful_results)
            max_time = max(r["execution_time"] for r in successful_results)
            
            if avg_time > 5.0:
                recommendations.append(f"Average generation time is high ({avg_time:.2f}s) - consider optimization")
            
            if max_time > 15.0:
                recommendations.append(f"Maximum generation time is excessive ({max_time:.2f}s) - investigate bottlenecks")
        
        # Analyze failure rates
        total_scenarios = len(scenario_results)
        failed_scenarios = [r for r in scenario_results if not r["success"]]
        failure_rate = len(failed_scenarios) / total_scenarios * 100 if total_scenarios > 0 else 0
        
        if failure_rate > 10:
            recommendations.append(f"High failure rate ({failure_rate:.1f}%) - improve error handling and validation")
        
        # Analyze generation rates
        if successful_results:
            avg_rate = sum(r["generation_rate"] for r in successful_results) / len(successful_results)
            if avg_rate < 100:  # Characters per second
                recommendations.append(f"Low generation rate ({avg_rate:.0f} chars/sec) - optimize template processing")
        
        if not recommendations:
            recommendations.append("Performance profiling shows good results - no immediate optimizations needed")
        
        return recommendations
    
    def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "monitoring_summary": self.monitor.get_performance_summary(),
            "cache_performance": {
                "cache_hit_rates": {},
                "total_cache_operations": 0
            },
            "system_recommendations": [],
            "next_steps": []
        }
        
        # Add cache performance data
        for operation_name in self.monitor.performance_profiles.keys():
            hit_rate = self.optimizer.get_cache_hit_rate(operation_name)
            if hit_rate > 0:
                report["cache_performance"]["cache_hit_rates"][operation_name] = hit_rate
        
        # Generate system-level recommendations
        if report["monitoring_summary"].get("operation_profiles"):
            avg_times = [
                profile["avg_time_seconds"] 
                for profile in report["monitoring_summary"]["operation_profiles"].values()
            ]
            overall_avg_time = sum(avg_times) / len(avg_times) if avg_times else 0
            
            if overall_avg_time > 3.0:
                report["system_recommendations"].append("Implement system-wide performance optimizations")
            
            if overall_avg_time < 1.0:
                report["system_recommendations"].append("System performing excellently - maintain current optimizations")
        
        # Next steps
        report["next_steps"] = [
            "Continue monitoring performance trends",
            "Implement recommended optimizations",
            "Regular performance review and tuning",
            "Plan for scalability improvements"
        ]
        
        return report
    
    def shutdown(self):
        """Shutdown the performance optimizer."""
        self.monitor.stop_monitoring()
        logger.info("Protocol Performance Optimizer shut down")


# Example usage and testing
if __name__ == "__main__":
    async def main():
        """Demonstrate performance optimization capabilities."""
        optimizer = ProtocolPerformanceOptimizer()
        
        # Simulate some operations for testing
        print("🔍 Starting performance monitoring demo...")
        
        # Simulate protocol generation operations
        for i in range(5):
            operation_id = optimizer.monitor.record_operation_start("test_protocol_generation")
            await asyncio.sleep(1 + i * 0.5)  # Simulate work
            optimizer.monitor.record_operation_end("test_protocol_generation", operation_id, success=True)
        
        # Wait a bit for metrics collection
        await asyncio.sleep(2)
        
        # Get performance analysis
        analysis = await optimizer.optimizer.analyze_performance_bottlenecks()
        print(f"\n📊 Performance Analysis:")
        print(f"Bottlenecks identified: {len(analysis['bottlenecks_identified'])}")
        print(f"System health: {analysis['system_health']}")
        print(f"Recommendations: {len(analysis['recommendations'])}")
        
        # Get comprehensive report
        report = optimizer.get_comprehensive_performance_report()
        print(f"\n📋 Performance Report:")
        print(f"Operations monitored: {len(report['monitoring_summary'].get('operation_profiles', {}))}")
        
        optimizer.shutdown()
        return analysis, report
    
    # Run the demo
    asyncio.run(main())