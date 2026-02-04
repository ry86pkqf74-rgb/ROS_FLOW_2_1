"""
Production Monitoring and Health Checks

Comprehensive monitoring system for reference management with
performance tracking, alerting, and automated diagnostics.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import httpx

from .reference_management_service import get_reference_service
from .reference_cache import get_cache
from .api_management import get_api_manager

logger = logging.getLogger(__name__)

@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: datetime
    requests_per_second: float
    average_response_time_ms: float
    cache_hit_rate: float
    error_rate: float
    active_connections: int
    queue_depth: int
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

@dataclass
class Alert:
    """System alert."""
    alert_id: str
    severity: str  # 'info', 'warning', 'critical'
    component: str
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class ReferenceSystemMonitor:
    """Production monitoring for reference management system."""
    
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.active_alerts: List[Alert] = []
        
        # Alert thresholds
        self.alert_thresholds = {
            'response_time_ms': 5000,      # 5 second max response time
            'error_rate': 0.05,            # 5% max error rate  
            'cache_hit_rate_min': 0.7,     # 70% minimum cache hit rate
            'api_failure_rate': 0.1,       # 10% max API failure rate
            'queue_depth': 100,            # 100 max queue depth
            'memory_usage_mb': 1000,       # 1GB max memory usage
            'cpu_usage_percent': 80        # 80% max CPU usage
        }
        
        # Component availability tracking
        self.component_uptime = {
            'reference_service': {'start_time': datetime.utcnow(), 'downtime': 0},
            'cache_system': {'start_time': datetime.utcnow(), 'downtime': 0},
            'api_management': {'start_time': datetime.utcnow(), 'downtime': 0},
            'external_apis': {'start_time': datetime.utcnow(), 'downtime': 0}
        }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        
        health_checks = []
        start_time = time.time()
        
        # Check reference service
        ref_service_health = await self._check_reference_service()
        health_checks.append(ref_service_health)
        
        # Check cache system
        cache_health = await self._check_cache_system()
        health_checks.append(cache_health)
        
        # Check API management
        api_health = await self._check_api_management()
        health_checks.append(api_health)
        
        # Check external APIs
        external_api_health = await self._check_external_apis()
        health_checks.extend(external_api_health)
        
        # Check system resources
        resource_health = await self._check_system_resources()
        health_checks.append(resource_health)
        
        # Determine overall status
        overall_status = self._calculate_overall_status(health_checks)
        
        # Update uptime tracking
        self._update_uptime_tracking(health_checks)
        
        # Store health checks
        self.health_checks.extend(health_checks)
        
        # Keep only last 24 hours of health checks
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.health_checks = [hc for hc in self.health_checks if hc.timestamp > cutoff_time]
        
        health_check_time = (time.time() - start_time) * 1000
        
        return {
            'overall_status': overall_status,
            'health_check_time_ms': health_check_time,
            'timestamp': datetime.utcnow().isoformat(),
            'components': [
                {
                    'component': check.component,
                    'status': check.status,
                    'response_time_ms': check.response_time_ms,
                    'details': check.details
                }
                for check in health_checks
            ],
            'uptime_summary': self._get_uptime_summary(),
            'recent_alerts': [
                {
                    'alert_id': alert.alert_id,
                    'severity': alert.severity,
                    'component': alert.component,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in self.active_alerts[-10:]  # Last 10 alerts
            ]
        }
    
    async def _check_reference_service(self) -> HealthCheck:
        """Check reference management service health."""
        start_time = time.time()
        
        try:
            ref_service = await get_reference_service()
            stats = await ref_service.get_stats()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on stats and response time
            status = 'healthy'
            if response_time > self.alert_thresholds['response_time_ms']:
                status = 'degraded'
                await self._create_alert('warning', 'reference_service', 
                                       f'High response time: {response_time:.0f}ms', 
                                       response_time, self.alert_thresholds['response_time_ms'])
            
            if stats['processings_performed'] > 0:
                avg_processing_time = stats['average_processing_time_seconds'] * 1000
                if avg_processing_time > 10000:  # 10 second threshold
                    status = 'degraded'
            
            return HealthCheck(
                component='reference_service',
                status=status,
                response_time_ms=response_time,
                details={
                    **stats,
                    'service_ready': True,
                    'processing_avg_time_ms': stats.get('average_processing_time_seconds', 0) * 1000
                }
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await self._create_alert('critical', 'reference_service', 
                                   f'Service unavailable: {str(e)}', 
                                   0, 1)
            return HealthCheck(
                component='reference_service',
                status='unhealthy',
                response_time_ms=response_time,
                details={'error': str(e), 'service_ready': False}
            )
    
    async def _check_cache_system(self) -> HealthCheck:
        """Check Redis cache system health."""
        start_time = time.time()
        
        try:
            cache = await get_cache()
            
            # Test cache operation
            test_key = f"health_check_{int(time.time())}"
            await cache.set('api_responses', test_key, {'test': True}, ttl_override=10)
            test_result = await cache.get('api_responses', test_key)
            
            if test_result is None:
                raise Exception("Cache read/write test failed")
            
            stats = await cache.get_stats()
            response_time = (time.time() - start_time) * 1000
            
            # Check hit rate
            hit_rate = stats.get('hit_rate', 0)
            status = 'healthy'
            
            if hit_rate < self.alert_thresholds['cache_hit_rate_min']:
                status = 'degraded'
                await self._create_alert('warning', 'cache_system', 
                                       f'Low cache hit rate: {hit_rate:.2%}', 
                                       hit_rate, self.alert_thresholds['cache_hit_rate_min'])
            
            # Clean up test key
            await cache.delete('api_responses', test_key)
            
            return HealthCheck(
                component='cache_system',
                status=status,
                response_time_ms=response_time,
                details={
                    **stats,
                    'cache_ready': True,
                    'read_write_test': 'passed'
                }
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await self._create_alert('critical', 'cache_system', 
                                   f'Cache system unavailable: {str(e)}', 
                                   0, 1)
            return HealthCheck(
                component='cache_system',
                status='unhealthy',
                response_time_ms=response_time,
                details={'error': str(e), 'cache_ready': False}
            )
    
    async def _check_api_management(self) -> HealthCheck:
        """Check API management system health."""
        start_time = time.time()
        
        try:
            api_manager = await get_api_manager()
            stats = await api_manager.get_stats()
            
            response_time = (time.time() - start_time) * 1000
            
            # Calculate error rate
            total_requests = stats['requests_made'] + stats['requests_failed']
            error_rate = stats['requests_failed'] / total_requests if total_requests > 0 else 0
            
            status = 'healthy'
            if error_rate > self.alert_thresholds['error_rate']:
                status = 'degraded'
                await self._create_alert('warning', 'api_management', 
                                       f'High API error rate: {error_rate:.2%}', 
                                       error_rate, self.alert_thresholds['error_rate'])
            
            return HealthCheck(
                component='api_management',
                status=status,
                response_time_ms=response_time,
                details={
                    **stats,
                    'api_manager_ready': True,
                    'error_rate': error_rate,
                    'total_requests': total_requests
                }
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            await self._create_alert('critical', 'api_management', 
                                   f'API manager unavailable: {str(e)}', 
                                   0, 1)
            return HealthCheck(
                component='api_management',
                status='unhealthy',
                response_time_ms=response_time,
                details={'error': str(e), 'api_manager_ready': False}
            )
    
    async def _check_external_apis(self) -> List[HealthCheck]:
        """Check external API availability."""
        apis_to_check = [
            ('crossref', 'https://api.crossref.org/works?rows=1', 'GET'),
            ('pubmed', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi', 'GET'),
            ('semantic_scholar', 'https://api.semanticscholar.org/graph/v1/paper/batch', 'POST')
        ]
        
        health_checks = []
        
        for api_name, test_url, method in apis_to_check:
            start_time = time.time()
            
            try:
                timeout_config = httpx.Timeout(10.0)
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    if method == 'GET':
                        response = await client.get(test_url)
                    else:
                        response = await client.post(test_url, json={'ids': []})
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    if 200 <= response.status_code < 300:
                        status = 'healthy'
                    elif 400 <= response.status_code < 500:
                        status = 'degraded'  # Client error but API is responding
                    else:
                        status = 'unhealthy'
                        await self._create_alert('warning', f'external_api_{api_name}', 
                                               f'API returning {response.status_code}', 
                                               response.status_code, 200)
                    
                    health_checks.append(HealthCheck(
                        component=f'external_api_{api_name}',
                        status=status,
                        response_time_ms=response_time,
                        details={
                            'status_code': response.status_code,
                            'api_url': test_url,
                            'api_ready': status != 'unhealthy'
                        }
                    ))
            
            except asyncio.TimeoutError:
                response_time = (time.time() - start_time) * 1000
                await self._create_alert('warning', f'external_api_{api_name}', 
                                       f'API timeout after 10 seconds', 
                                       response_time, 10000)
                health_checks.append(HealthCheck(
                    component=f'external_api_{api_name}',
                    status='unhealthy',
                    response_time_ms=response_time,
                    details={'error': 'timeout', 'api_ready': False}
                ))
            
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                health_checks.append(HealthCheck(
                    component=f'external_api_{api_name}',
                    status='unhealthy',
                    response_time_ms=response_time,
                    details={'error': str(e), 'api_ready': False}
                ))
        
        return health_checks
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / 1024 / 1024
            memory_percent = memory.percent
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get disk usage for temp/cache
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            response_time = (time.time() - start_time) * 1000
            
            status = 'healthy'
            
            # Check thresholds
            if memory_usage_mb > self.alert_thresholds['memory_usage_mb']:
                status = 'degraded'
                await self._create_alert('warning', 'system_resources', 
                                       f'High memory usage: {memory_usage_mb:.0f}MB', 
                                       memory_usage_mb, self.alert_thresholds['memory_usage_mb'])
            
            if cpu_percent > self.alert_thresholds['cpu_usage_percent']:
                status = 'degraded'
                await self._create_alert('warning', 'system_resources', 
                                       f'High CPU usage: {cpu_percent:.1f}%', 
                                       cpu_percent, self.alert_thresholds['cpu_usage_percent'])
            
            return HealthCheck(
                component='system_resources',
                status=status,
                response_time_ms=response_time,
                details={
                    'memory_usage_mb': memory_usage_mb,
                    'memory_percent': memory_percent,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk_percent,
                    'system_ready': status != 'unhealthy'
                }
            )
        
        except ImportError:
            # psutil not available
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                component='system_resources',
                status='healthy',
                response_time_ms=response_time,
                details={
                    'monitoring': 'limited',
                    'note': 'psutil not available for detailed system monitoring',
                    'system_ready': True
                }
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                component='system_resources',
                status='degraded',
                response_time_ms=response_time,
                details={'error': str(e), 'system_ready': True}
            )
    
    def _calculate_overall_status(self, health_checks: List[HealthCheck]) -> str:
        """Calculate overall system status."""
        if any(check.status == 'unhealthy' for check in health_checks):
            return 'unhealthy'
        elif any(check.status == 'degraded' for check in health_checks):
            return 'degraded'
        else:
            return 'healthy'
    
    def _update_uptime_tracking(self, health_checks: List[HealthCheck]):
        """Update component uptime tracking."""
        now = datetime.utcnow()
        
        for check in health_checks:
            component_name = check.component
            if component_name in self.component_uptime:
                if check.status == 'unhealthy':
                    # Start tracking downtime
                    if 'last_downtime_start' not in self.component_uptime[component_name]:
                        self.component_uptime[component_name]['last_downtime_start'] = now
                else:
                    # Component is healthy, end downtime tracking if it was down
                    if 'last_downtime_start' in self.component_uptime[component_name]:
                        downtime_duration = now - self.component_uptime[component_name]['last_downtime_start']
                        self.component_uptime[component_name]['downtime'] += downtime_duration.total_seconds()
                        del self.component_uptime[component_name]['last_downtime_start']
    
    def _get_uptime_summary(self) -> Dict[str, Any]:
        """Get uptime summary for all components."""
        now = datetime.utcnow()
        summary = {}
        
        for component, data in self.component_uptime.items():
            total_time = (now - data['start_time']).total_seconds()
            current_downtime = data['downtime']
            
            # Add current downtime if component is down
            if 'last_downtime_start' in data:
                current_downtime += (now - data['last_downtime_start']).total_seconds()
            
            uptime_seconds = total_time - current_downtime
            uptime_percentage = (uptime_seconds / total_time * 100) if total_time > 0 else 100
            
            summary[component] = {
                'uptime_percentage': uptime_percentage,
                'total_downtime_seconds': current_downtime,
                'total_runtime_seconds': total_time,
                'is_currently_up': 'last_downtime_start' not in data
            }
        
        return summary
    
    async def collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        
        # Get stats from all components
        ref_service = await get_reference_service()
        cache = await get_cache()
        api_manager = await get_api_manager()
        
        ref_stats = await ref_service.get_stats()
        cache_stats = await cache.get_stats()
        api_stats = await api_manager.get_stats()
        
        # Calculate metrics
        cache_hit_rate = cache_stats.get('hit_rate', 0)
        
        total_requests = api_stats['requests_made'] + api_stats['requests_failed']
        error_rate = api_stats['requests_failed'] / total_requests if total_requests > 0 else 0
        
        avg_response_time = ref_stats.get('average_processing_time_seconds', 0) * 1000
        
        # Get system metrics if available
        memory_usage_mb = 0
        cpu_usage_percent = 0
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / 1024 / 1024
            cpu_usage_percent = psutil.cpu_percent()
        except ImportError:
            pass
        
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            requests_per_second=0,  # Would need time-window calculation
            average_response_time_ms=avg_response_time,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate,
            active_connections=0,  # Would get from connection pool
            queue_depth=0,  # Would get from queue monitoring
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent
        )
        
        # Store in history (keep last 24 hours)
        self.performance_history.append(metrics)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.performance_history = [m for m in self.performance_history if m.timestamp > cutoff_time]
        
        return metrics
    
    async def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        current_metrics = await self.collect_performance_metrics()
        
        # Filter metrics for specified time range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self.performance_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            recent_metrics = [current_metrics]
        
        # Calculate trends and averages
        avg_response_time = sum(m.average_response_time_ms for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        
        # Calculate trends
        if len(recent_metrics) > 1:
            recent_avg_response = sum(m.average_response_time_ms for m in recent_metrics[-5:]) / min(5, len(recent_metrics))
            historical_avg_response = sum(m.average_response_time_ms for m in recent_metrics) / len(recent_metrics)
            response_time_trend = 'improving' if recent_avg_response < historical_avg_response else 'degrading' if recent_avg_response > historical_avg_response else 'stable'
        else:
            response_time_trend = 'stable'
        
        return {
            'report_period_hours': hours,
            'generated_at': datetime.utcnow().isoformat(),
            'current_metrics': {
                'response_time_ms': current_metrics.average_response_time_ms,
                'cache_hit_rate': current_metrics.cache_hit_rate,
                'error_rate': current_metrics.error_rate,
                'memory_usage_mb': current_metrics.memory_usage_mb,
                'cpu_usage_percent': current_metrics.cpu_usage_percent
            },
            'period_averages': {
                'response_time_ms': avg_response_time,
                'cache_hit_rate': avg_cache_hit_rate,
                'error_rate': avg_error_rate
            },
            'trends': {
                'response_time_trend': response_time_trend,
                'total_data_points': len(recent_metrics)
            },
            'alerts': await self._get_recent_alerts(hours),
            'recommendations': await self._generate_recommendations(current_metrics, recent_metrics),
            'sla_compliance': self._calculate_sla_compliance(recent_metrics)
        }
    
    async def _create_alert(self, severity: str, component: str, message: str, metric_value: float, threshold: float):
        """Create a new alert."""
        import hashlib
        alert_id = hashlib.md5(f"{component}_{message}_{datetime.utcnow()}".encode()).hexdigest()[:16]
        
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            component=component,
            message=message,
            metric_value=metric_value,
            threshold=threshold,
            timestamp=datetime.utcnow()
        )
        
        self.active_alerts.append(alert)
        
        # Keep only recent alerts
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.active_alerts = [a for a in self.active_alerts if a.timestamp > cutoff_time]
        
        logger.warning(f"Alert created [{severity}] {component}: {message}")
    
    async def _get_recent_alerts(self, hours: int) -> List[Dict[str, Any]]:
        """Get alerts from specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_alerts = [a for a in self.active_alerts if a.timestamp > cutoff_time]
        
        return [
            {
                'alert_id': alert.alert_id,
                'severity': alert.severity,
                'component': alert.component,
                'message': alert.message,
                'metric_value': alert.metric_value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            for alert in recent_alerts
        ]
    
    async def _generate_recommendations(self, current: PerformanceMetrics, history: List[PerformanceMetrics]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Cache recommendations
        if current.cache_hit_rate < 0.7:
            recommendations.append("Cache hit rate is below optimal. Consider increasing cache TTL or warming strategy.")
        
        # Response time recommendations
        if current.average_response_time_ms > 3000:
            recommendations.append("Response times are high. Consider optimizing queries or increasing cache usage.")
        
        # Error rate recommendations
        if current.error_rate > 0.05:
            recommendations.append("Error rate is elevated. Review API call patterns and implement better retry logic.")
        
        # Memory recommendations
        if current.memory_usage_mb > 800:
            recommendations.append("Memory usage is high. Consider implementing memory cleanup or garbage collection.")
        
        # Historical trend recommendations
        if len(history) > 5:
            recent_errors = sum(m.error_rate for m in history[-5:]) / 5
            historical_errors = sum(m.error_rate for m in history) / len(history)
            
            if recent_errors > historical_errors * 1.5:
                recommendations.append("Error rate trend is increasing. Investigate recent changes or external API issues.")
        
        if not recommendations:
            recommendations.append("System performance is within normal parameters.")
        
        return recommendations
    
    def _calculate_sla_compliance(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Calculate SLA compliance metrics."""
        if not metrics:
            return {'availability': 1.0, 'response_time_sla': 1.0, 'error_rate_sla': 1.0}
        
        # Availability (based on whether system was responding)
        availability = 1.0  # Assume 100% availability if we have metrics
        
        # Response time SLA (95% under 5 seconds)
        response_times = [m.average_response_time_ms for m in metrics]
        under_5s_count = len([rt for rt in response_times if rt < 5000])
        response_time_sla = under_5s_count / len(response_times) if response_times else 1.0
        
        # Error rate SLA (99% success rate)
        error_rates = [m.error_rate for m in metrics]
        avg_error_rate = sum(error_rates) / len(error_rates)
        error_rate_sla = max(0, 1.0 - avg_error_rate)
        
        return {
            'availability': availability,
            'response_time_sla': response_time_sla,
            'error_rate_sla': error_rate_sla,
            'overall_sla': min(availability, response_time_sla, error_rate_sla)
        }
    
    async def get_system_status_summary(self) -> Dict[str, Any]:
        """Get high-level system status summary."""
        health_result = await self.comprehensive_health_check()
        perf_metrics = await self.collect_performance_metrics()
        
        return {
            'status': health_result['overall_status'],
            'timestamp': datetime.utcnow().isoformat(),
            'key_metrics': {
                'response_time_ms': perf_metrics.average_response_time_ms,
                'cache_hit_rate': perf_metrics.cache_hit_rate,
                'error_rate': perf_metrics.error_rate,
                'uptime_summary': self._get_uptime_summary()
            },
            'active_alerts_count': len([a for a in self.active_alerts if not a.resolved]),
            'components_healthy': len([c for c in health_result['components'] if c['status'] == 'healthy']),
            'total_components': len(health_result['components'])
        }


# Global monitor instance
_monitor_instance: Optional[ReferenceSystemMonitor] = None


async def get_system_monitor() -> ReferenceSystemMonitor:
    """Get global system monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ReferenceSystemMonitor()
    return _monitor_instance


async def close_system_monitor() -> None:
    """Close global system monitor instance."""
    global _monitor_instance
    _monitor_instance = None