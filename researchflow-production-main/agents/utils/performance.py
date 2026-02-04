#!/usr/bin/env python3
"""
Performance Testing Utilities for ResearchFlow Agents

Provides tools for:
- Load testing agent endpoints
- Benchmarking agent operations
- Resource utilization monitoring
- Performance regression detection
- Stress testing workflows

@author Claude
@created 2025-01-30
"""

import asyncio
import time
import psutil
import statistics
from typing import Dict, Any, List, Optional, Callable, NamedTuple, Awaitable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class BenchmarkResult(NamedTuple):
    """Result of a benchmark run"""
    operation: str
    total_operations: int
    total_duration: float
    operations_per_second: float
    mean_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float
    error_rate: float
    errors: List[str]


@dataclass
class ResourceSnapshot:
    """Snapshot of system resource usage"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int


@dataclass
class LoadTestConfig:
    """Configuration for load testing"""
    concurrent_users: int = 10
    total_requests: int = 100
    ramp_up_duration: float = 5.0  # seconds to reach full load
    test_duration: Optional[float] = None  # run for specific duration
    think_time: float = 0.0  # delay between requests per user
    timeout: float = 30.0
    
    # Resource monitoring
    monitor_resources: bool = True
    resource_sample_interval: float = 1.0  # seconds


class PerformanceTester:
    """
    Comprehensive performance testing for agent operations.
    
    Example:
        >>> tester = PerformanceTester()
        >>> 
        >>> # Benchmark a function
        >>> result = await tester.benchmark_function(my_function, iterations=1000)
        >>> print(f"Operations per second: {result.operations_per_second}")
        >>> 
        >>> # Load test an API endpoint
        >>> async def api_call():
        ...     async with httpx.AsyncClient() as client:
        ...         response = await client.get("http://localhost:3001/health")
        ...         return response.status_code
        >>> 
        >>> load_result = await tester.load_test(api_call, config=LoadTestConfig(
        ...     concurrent_users=50,
        ...     total_requests=1000
        ... ))
    """
    
    def __init__(self):
        self.metrics = None
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize metrics collection"""
        try:
            from .metrics import get_metrics_collector
            self.metrics = get_metrics_collector()
        except ImportError:
            logger.debug("Metrics not available for performance tester")
    
    async def benchmark_function(
        self,
        func: Callable,
        iterations: int = 1000,
        warmup_iterations: int = 100,
        *args,
        **kwargs
    ) -> BenchmarkResult:
        """
        Benchmark a function's performance.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            BenchmarkResult with performance metrics
        """
        logger.info(f"Benchmarking {func.__name__} with {iterations} iterations")
        
        latencies = []
        errors = []
        
        # Warmup
        if warmup_iterations > 0:
            logger.info(f"Running {warmup_iterations} warmup iterations...")
            for _ in range(warmup_iterations):
                try:
                    start_time = time.perf_counter()
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        func(*args, **kwargs)
                    end_time = time.perf_counter()
                except Exception:
                    pass  # Ignore warmup errors
        
        # Actual benchmark
        logger.info(f"Running {iterations} benchmark iterations...")
        total_start_time = time.perf_counter()
        
        for i in range(iterations):
            try:
                start_time = time.perf_counter()
                
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                
                end_time = time.perf_counter()
                latency = end_time - start_time
                latencies.append(latency)
                
            except Exception as e:
                end_time = time.perf_counter()
                latency = end_time - start_time
                latencies.append(latency)
                errors.append(str(e))
        
        total_duration = time.perf_counter() - total_start_time
        
        # Calculate statistics
        if latencies:
            mean_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = self._percentile(latencies, 95)
            p99_latency = self._percentile(latencies, 99)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            mean_latency = median_latency = p95_latency = p99_latency = 0
            min_latency = max_latency = 0
        
        operations_per_second = iterations / total_duration if total_duration > 0 else 0
        error_rate = len(errors) / iterations if iterations > 0 else 0
        
        result = BenchmarkResult(
            operation=func.__name__,
            total_operations=iterations,
            total_duration=total_duration,
            operations_per_second=operations_per_second,
            mean_latency=mean_latency,
            median_latency=median_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            min_latency=min_latency,
            max_latency=max_latency,
            error_rate=error_rate,
            errors=errors[:10]  # Keep first 10 errors for analysis
        )
        
        # Record metrics
        if self.metrics:
            self._record_benchmark_metrics(result)
        
        return result
    
    async def load_test(
        self,
        operation: Callable[[], Awaitable[Any]],
        config: LoadTestConfig
    ) -> Dict[str, Any]:
        """
        Perform load testing on an operation.
        
        Args:
            operation: Async function to test
            config: Load test configuration
            
        Returns:
            Detailed load test results
        """
        logger.info(f"Starting load test: {config.concurrent_users} users, {config.total_requests} requests")
        
        # Start resource monitoring
        resource_monitor = None
        if config.monitor_resources:
            resource_monitor = asyncio.create_task(
                self._monitor_resources(config.resource_sample_interval)
            )
        
        # Calculate requests per user
        requests_per_user = config.total_requests // config.concurrent_users
        remaining_requests = config.total_requests % config.concurrent_users
        
        # Create user tasks
        user_tasks = []
        for user_id in range(config.concurrent_users):
            user_requests = requests_per_user
            if user_id < remaining_requests:
                user_requests += 1
            
            # Calculate ramp-up delay
            ramp_up_delay = (config.ramp_up_duration / config.concurrent_users) * user_id
            
            user_task = asyncio.create_task(
                self._simulate_user(
                    user_id,
                    operation,
                    user_requests,
                    ramp_up_delay,
                    config.think_time,
                    config.timeout
                )
            )
            user_tasks.append(user_task)
        
        # Wait for all users to complete
        start_time = time.time()
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Stop resource monitoring
        if resource_monitor:
            resource_monitor.cancel()
            try:
                await resource_monitor
            except asyncio.CancelledError:
                pass
        
        # Aggregate results
        all_latencies = []
        all_errors = []
        successful_requests = 0
        
        for result in user_results:
            if isinstance(result, Exception):
                all_errors.append(str(result))
                continue
                
            user_latencies, user_errors = result
            all_latencies.extend(user_latencies)
            all_errors.extend(user_errors)
            successful_requests += len(user_latencies) - len(user_errors)
        
        # Calculate aggregate statistics
        if all_latencies:
            mean_latency = statistics.mean(all_latencies)
            median_latency = statistics.median(all_latencies)
            p95_latency = self._percentile(all_latencies, 95)
            p99_latency = self._percentile(all_latencies, 99)
        else:
            mean_latency = median_latency = p95_latency = p99_latency = 0
        
        throughput = successful_requests / total_duration if total_duration > 0 else 0
        error_rate = len(all_errors) / config.total_requests if config.total_requests > 0 else 0
        
        results = {
            "config": config,
            "total_duration": total_duration,
            "successful_requests": successful_requests,
            "failed_requests": len(all_errors),
            "throughput_rps": throughput,
            "error_rate": error_rate,
            "latency_stats": {
                "mean": mean_latency,
                "median": median_latency,
                "p95": p95_latency,
                "p99": p99_latency,
                "min": min(all_latencies) if all_latencies else 0,
                "max": max(all_latencies) if all_latencies else 0
            },
            "errors": all_errors[:20],  # Keep first 20 errors
            "resource_usage": getattr(self, '_resource_snapshots', [])
        }
        
        # Record load test metrics
        if self.metrics:
            self._record_load_test_metrics(results)
        
        return results
    
    async def _simulate_user(
        self,
        user_id: int,
        operation: Callable[[], Awaitable[Any]],
        num_requests: int,
        ramp_up_delay: float,
        think_time: float,
        timeout: float
    ) -> tuple:
        """Simulate a single user's load"""
        # Wait for ramp-up
        if ramp_up_delay > 0:
            await asyncio.sleep(ramp_up_delay)
        
        latencies = []
        errors = []
        
        for request_id in range(num_requests):
            try:
                start_time = time.perf_counter()
                
                # Execute operation with timeout
                await asyncio.wait_for(operation(), timeout=timeout)
                
                end_time = time.perf_counter()
                latency = end_time - start_time
                latencies.append(latency)
                
            except Exception as e:
                end_time = time.perf_counter()
                latency = end_time - start_time
                latencies.append(latency)
                errors.append(f"User {user_id}, Request {request_id}: {str(e)}")
            
            # Think time between requests
            if think_time > 0 and request_id < num_requests - 1:
                await asyncio.sleep(think_time)
        
        return latencies, errors
    
    async def _monitor_resources(self, interval: float):
        """Monitor system resources during load test"""
        self._resource_snapshots = []
        
        process = psutil.Process()
        
        # Get initial network/disk stats
        initial_net = psutil.net_io_counters()
        initial_disk = psutil.disk_io_counters()
        
        try:
            while True:
                # Get current stats
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                
                # System-wide network/disk (approximate)
                net_stats = psutil.net_io_counters()
                disk_stats = psutil.disk_io_counters()
                
                snapshot = ResourceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_info.rss / (1024 * 1024),
                    memory_percent=memory_percent,
                    disk_io_read=disk_stats.read_bytes - initial_disk.read_bytes if disk_stats and initial_disk else 0,
                    disk_io_write=disk_stats.write_bytes - initial_disk.write_bytes if disk_stats and initial_disk else 0,
                    network_bytes_sent=net_stats.bytes_sent - initial_net.bytes_sent if net_stats and initial_net else 0,
                    network_bytes_recv=net_stats.bytes_recv - initial_net.bytes_recv if net_stats and initial_net else 0
                )
                
                self._resource_snapshots.append(snapshot)
                
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            pass
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile from list of values"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _record_benchmark_metrics(self, result: BenchmarkResult):
        """Record benchmark metrics"""
        labels = {"operation": result.operation}
        
        self.metrics.observe_histogram(
            "benchmark_operations_per_second",
            result.operations_per_second,
            labels
        )
        
        self.metrics.observe_histogram(
            "benchmark_latency_seconds",
            result.mean_latency,
            {**labels, "percentile": "mean"}
        )
        
        self.metrics.observe_histogram(
            "benchmark_latency_seconds",
            result.p95_latency,
            {**labels, "percentile": "p95"}
        )
        
        self.metrics.set_gauge(
            "benchmark_error_rate",
            result.error_rate,
            labels
        )
    
    def _record_load_test_metrics(self, results: Dict[str, Any]):
        """Record load test metrics"""
        config = results["config"]
        labels = {
            "concurrent_users": str(config.concurrent_users),
            "total_requests": str(config.total_requests)
        }
        
        self.metrics.observe_histogram(
            "load_test_throughput_rps",
            results["throughput_rps"],
            labels
        )
        
        self.metrics.set_gauge(
            "load_test_error_rate",
            results["error_rate"],
            labels
        )
        
        for percentile, value in results["latency_stats"].items():
            self.metrics.observe_histogram(
                "load_test_latency_seconds",
                value,
                {**labels, "percentile": percentile}
            )
    
    def print_benchmark_report(self, result: BenchmarkResult):
        """Print formatted benchmark report"""
        print(f"\n📊 Benchmark Report: {result.operation}")
        print("=" * 60)
        print(f"Total Operations:     {result.total_operations:,}")
        print(f"Total Duration:       {result.total_duration:.2f}s")
        print(f"Operations/Second:    {result.operations_per_second:.2f}")
        print(f"Error Rate:           {result.error_rate:.2%}")
        print()
        print("Latency Statistics:")
        print(f"  Mean:               {result.mean_latency*1000:.2f}ms")
        print(f"  Median:             {result.median_latency*1000:.2f}ms")
        print(f"  95th Percentile:    {result.p95_latency*1000:.2f}ms")
        print(f"  99th Percentile:    {result.p99_latency*1000:.2f}ms")
        print(f"  Min:                {result.min_latency*1000:.2f}ms")
        print(f"  Max:                {result.max_latency*1000:.2f}ms")
        
        if result.errors:
            print(f"\nFirst {len(result.errors)} Errors:")
            for i, error in enumerate(result.errors[:5]):
                print(f"  {i+1}. {error}")
    
    def print_load_test_report(self, results: Dict[str, Any]):
        """Print formatted load test report"""
        config = results["config"]
        
        print(f"\n🚀 Load Test Report")
        print("=" * 60)
        print(f"Configuration:")
        print(f"  Concurrent Users:     {config.concurrent_users}")
        print(f"  Total Requests:       {config.total_requests}")
        print(f"  Ramp-up Duration:     {config.ramp_up_duration}s")
        print(f"  Think Time:           {config.think_time}s")
        print()
        print(f"Results:")
        print(f"  Total Duration:       {results['total_duration']:.2f}s")
        print(f"  Successful Requests:  {results['successful_requests']:,}")
        print(f"  Failed Requests:      {results['failed_requests']:,}")
        print(f"  Throughput:           {results['throughput_rps']:.2f} req/s")
        print(f"  Error Rate:           {results['error_rate']:.2%}")
        print()
        print("Response Time Statistics:")
        stats = results["latency_stats"]
        print(f"  Mean:                 {stats['mean']*1000:.2f}ms")
        print(f"  Median:               {stats['median']*1000:.2f}ms")
        print(f"  95th Percentile:      {stats['p95']*1000:.2f}ms")
        print(f"  99th Percentile:      {stats['p99']*1000:.2f}ms")
        print(f"  Min:                  {stats['min']*1000:.2f}ms")
        print(f"  Max:                  {stats['max']*1000:.2f}ms")


# Global performance tester instance
_performance_tester: Optional[PerformanceTester] = None


def get_performance_tester() -> PerformanceTester:
    """Get or create the global performance tester"""
    global _performance_tester
    if _performance_tester is None:
        _performance_tester = PerformanceTester()
    return _performance_tester


# Convenience functions

async def benchmark(func: Callable, iterations: int = 1000, **kwargs) -> BenchmarkResult:
    """Convenience function to benchmark a function"""
    tester = get_performance_tester()
    return await tester.benchmark_function(func, iterations, **kwargs)


async def load_test(operation: Callable, **config_kwargs) -> Dict[str, Any]:
    """Convenience function to load test an operation"""
    tester = get_performance_tester()
    config = LoadTestConfig(**config_kwargs)
    return await tester.load_test(operation, config)