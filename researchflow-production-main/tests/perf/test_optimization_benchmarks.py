"""
Performance Benchmarking Tests for ResearchFlow Optimization
===========================================================

Comprehensive performance benchmarks for:
- Citation analysis performance
- Manuscript generation speed
- Package compression efficiency  
- AI endpoint response times
- Memory usage optimization
"""

import pytest
import time
import psutil
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import json
import numpy as np

# Performance monitoring utilities
from tests.integration.utils.api_client import ResearchFlowTestClient
from tests.integration.utils.helpers import generate_test_data, create_performance_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float
    error_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation_name,
            "execution_time": self.execution_time,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "throughput": self.throughput_ops_per_sec,
            "error_rate": self.error_rate
        }


class PerformanceBenchmarkSuite:
    """Main performance benchmarking test suite."""
    
    def __init__(self):
        self.test_client = ResearchFlowTestClient(base_url="http://localhost:8000")
        self.performance_logger = create_performance_logger()
        self.benchmark_results = []
    
    def measure_performance(self, operation_name: str, operation_func, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance metrics for a given operation."""
        # Get initial system metrics
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = psutil.cpu_percent(interval=None)
        
        start_time = time.time()
        
        try:
            # Execute operation
            result = operation_func(*args, **kwargs)
            error_occurred = False
        except Exception as e:
            self.performance_logger.error(f"Performance test error in {operation_name}: {e}")
            result = None
            error_occurred = True
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Get final system metrics
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_cpu = psutil.cpu_percent(interval=None)
        
        memory_delta = final_memory - initial_memory
        cpu_usage = (initial_cpu + final_cpu) / 2  # Average during operation
        
        # Calculate throughput (operations per second)
        throughput = 1.0 / execution_time if execution_time > 0 else 0
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            execution_time=execution_time,
            memory_usage_mb=memory_delta,
            cpu_usage_percent=cpu_usage,
            throughput_ops_per_sec=throughput,
            error_rate=1.0 if error_occurred else 0.0
        )
        
        self.benchmark_results.append(metrics)
        return metrics
    
    @pytest.mark.performance
    def test_citation_analysis_performance(self):
        """Benchmark citation analysis operations."""
        test_cases = [
            ("small_network", 10),    # 10 papers
            ("medium_network", 100),  # 100 papers  
            ("large_network", 1000),  # 1000 papers
        ]
        
        for case_name, paper_count in test_cases:
            # Generate test citation network
            citation_network = generate_test_data("citation_network", size=paper_count)
            
            def run_citation_analysis():
                # Mock citation analysis operation
                return self.test_client.post("/api/citations/analyze", 
                                           json={"network": citation_network})
            
            metrics = self.measure_performance(
                f"citation_analysis_{case_name}",
                run_citation_analysis
            )
            
            # Performance assertions
            if paper_count <= 10:
                assert metrics.execution_time < 1.0, f"Small network should analyze in <1s, took {metrics.execution_time}s"
            elif paper_count <= 100:
                assert metrics.execution_time < 5.0, f"Medium network should analyze in <5s, took {metrics.execution_time}s"
            else:
                assert metrics.execution_time < 30.0, f"Large network should analyze in <30s, took {metrics.execution_time}s"
            
            # Memory usage should scale reasonably
            expected_memory_mb = paper_count * 0.1  # ~0.1MB per paper
            assert metrics.memory_usage_mb < expected_memory_mb * 2, "Memory usage too high"
    
    @pytest.mark.performance
    def test_manuscript_generation_performance(self):
        """Benchmark manuscript generation speed."""
        manuscript_configs = [
            ("short_manuscript", {"word_count": 1000, "sections": 4}),
            ("medium_manuscript", {"word_count": 5000, "sections": 6}),
            ("long_manuscript", {"word_count": 10000, "sections": 8}),
        ]
        
        for config_name, config in manuscript_configs:
            def run_manuscript_generation():
                return self.test_client.post("/api/manuscript/generate",
                                           json=config)
            
            metrics = self.measure_performance(
                f"manuscript_generation_{config_name}",
                run_manuscript_generation
            )
            
            # Performance assertions based on word count
            words_per_second = config["word_count"] / metrics.execution_time if metrics.execution_time > 0 else 0
            
            # Should generate at least 100 words per second
            assert words_per_second > 100, f"Generation too slow: {words_per_second} words/sec"
            
            # Memory usage should be reasonable
            assert metrics.memory_usage_mb < 100, f"Memory usage too high: {metrics.memory_usage_mb}MB"
    
    @pytest.mark.performance  
    def test_package_compression_performance(self):
        """Benchmark package compression efficiency."""
        compression_test_cases = [
            ("text_heavy", generate_test_data("text_document", size=50000)),
            ("image_heavy", generate_test_data("image_document", size=500000)),
            ("mixed_content", generate_test_data("mixed_document", size=200000)),
        ]
        
        for case_name, test_data in compression_test_cases:
            def run_compression():
                return self.test_client.post("/api/optimization/compress",
                                           json={"data": test_data, "target_ratio": 0.8})
            
            metrics = self.measure_performance(
                f"package_compression_{case_name}",
                run_compression
            )
            
            # Compression should be reasonably fast
            data_size_mb = len(str(test_data)) / 1024 / 1024
            compression_speed_mbps = data_size_mb / metrics.execution_time if metrics.execution_time > 0 else 0
            
            # Should compress at least 1 MB/second
            assert compression_speed_mbps > 1.0, f"Compression too slow: {compression_speed_mbps} MB/s"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_operation_performance(self):
        """Test performance under concurrent operations."""
        concurrent_operations = [
            ("citation_analysis", "/api/citations/analyze"),
            ("manuscript_generation", "/api/manuscript/generate"),
            ("package_compression", "/api/optimization/compress"),
        ]
        
        async def run_concurrent_operation(operation_name: str, endpoint: str):
            """Run a single operation concurrently."""
            start_time = time.time()
            
            try:
                response = await self.test_client.post_async(endpoint, json={"test": "data"})
                success = response.status_code == 200
            except Exception:
                success = False
            
            end_time = time.time()
            return {
                "operation": operation_name,
                "duration": end_time - start_time,
                "success": success
            }
        
        # Run 10 concurrent operations of each type
        tasks = []
        for operation_name, endpoint in concurrent_operations:
            for i in range(10):
                task = run_concurrent_operation(f"{operation_name}_{i}", endpoint)
                tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze concurrent performance
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        success_rate = len(successful_operations) / len(tasks)
        
        # Performance assertions
        assert success_rate > 0.8, f"Success rate too low under concurrency: {success_rate}"
        assert total_time < 60, f"Concurrent operations took too long: {total_time}s"
        
        # Average response time should be reasonable
        avg_response_time = statistics.mean([r["duration"] for r in successful_operations])
        assert avg_response_time < 10, f"Average response time too high: {avg_response_time}s"
    
    @pytest.mark.performance
    def test_memory_usage_optimization(self):
        """Test memory usage patterns and optimization."""
        initial_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
        
        # Simulate memory-intensive operations
        memory_intensive_operations = [
            ("large_dataset_processing", lambda: self.process_large_dataset()),
            ("batch_compression", lambda: self.run_batch_compression()),
            ("concurrent_analysis", lambda: self.run_concurrent_analysis()),
        ]
        
        memory_metrics = []
        
        for operation_name, operation_func in memory_intensive_operations:
            before_memory = psutil.virtual_memory().used / 1024 / 1024
            
            # Run operation
            try:
                operation_func()
            except Exception as e:
                self.performance_logger.warning(f"Memory test operation failed: {e}")
            
            after_memory = psutil.virtual_memory().used / 1024 / 1024
            memory_delta = after_memory - before_memory
            
            memory_metrics.append({
                "operation": operation_name,
                "memory_delta_mb": memory_delta,
                "peak_memory_mb": after_memory
            })
            
            # Memory should be released after operation
            time.sleep(1)  # Allow for cleanup
            final_memory = psutil.virtual_memory().used / 1024 / 1024
            memory_released = after_memory - final_memory
            
            # Should release at least 80% of used memory
            if memory_delta > 10:  # Only check if significant memory was used
                assert memory_released > memory_delta * 0.8, f"Memory not released properly for {operation_name}"
        
        # Overall memory usage should not grow excessively
        final_memory = psutil.virtual_memory().used / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        assert total_memory_growth < 500, f"Excessive memory growth: {total_memory_growth}MB"
    
    def process_large_dataset(self):
        """Simulate processing a large dataset."""
        large_data = generate_test_data("large_dataset", size=1000000)
        # Mock processing
        return len(str(large_data))
    
    def run_batch_compression(self):
        """Simulate batch compression operations."""
        for i in range(10):
            test_data = generate_test_data("document", size=50000)
            # Mock compression
            compressed = str(test_data)[:int(len(str(test_data)) * 0.8)]
        return True
    
    def run_concurrent_analysis(self):
        """Simulate concurrent analysis operations."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(20):
                future = executor.submit(self.analyze_sample_data, i)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    self.performance_logger.warning(f"Concurrent analysis task failed: {e}")
        return True
    
    def analyze_sample_data(self, sample_id: int):
        """Analyze a sample data set."""
        sample_data = generate_test_data("analysis_sample", size=1000)
        # Mock analysis
        return {"sample_id": sample_id, "result": "analyzed"}
    
    @pytest.mark.performance
    def test_scalability_benchmarks(self):
        """Test system scalability with increasing loads."""
        load_levels = [1, 5, 10, 25, 50]  # Number of concurrent operations
        
        scalability_results = []
        
        for load_level in load_levels:
            start_time = time.time()
            
            # Run multiple concurrent operations
            with ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = []
                for i in range(load_level):
                    future = executor.submit(self.run_scalability_operation, i)
                    futures.append(future)
                
                successful_operations = 0
                total_operations = 0
                
                for future in as_completed(futures):
                    total_operations += 1
                    try:
                        result = future.result()
                        if result:
                            successful_operations += 1
                    except Exception:
                        pass
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            success_rate = successful_operations / total_operations if total_operations > 0 else 0
            operations_per_second = total_operations / total_duration if total_duration > 0 else 0
            
            scalability_results.append({
                "load_level": load_level,
                "success_rate": success_rate,
                "ops_per_second": operations_per_second,
                "total_duration": total_duration
            })
        
        # Analyze scalability
        for i, result in enumerate(scalability_results):
            # Success rate should remain high even under load
            assert result["success_rate"] > 0.7, f"Success rate too low at load {result['load_level']}: {result['success_rate']}"
            
            # Performance degradation should be graceful
            if i > 0:
                prev_ops_per_sec = scalability_results[i-1]["ops_per_second"]
                current_ops_per_sec = result["ops_per_second"]
                
                # Performance shouldn't degrade by more than 50% per load level increase
                if prev_ops_per_sec > 0:
                    performance_ratio = current_ops_per_sec / prev_ops_per_sec
                    assert performance_ratio > 0.5, f"Performance degraded too much at load {result['load_level']}"
    
    def run_scalability_operation(self, operation_id: int) -> bool:
        """Run a single operation for scalability testing."""
        try:
            # Mock operation
            test_data = generate_test_data("scalability_test", size=1000)
            time.sleep(0.1)  # Simulate processing time
            return True
        except Exception:
            return False
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        if not self.benchmark_results:
            return {"error": "No benchmark results available"}
        
        # Calculate aggregate statistics
        execution_times = [m.execution_time for m in self.benchmark_results]
        memory_usage = [m.memory_usage_mb for m in self.benchmark_results]
        cpu_usage = [m.cpu_usage_percent for m in self.benchmark_results]
        throughput = [m.throughput_ops_per_sec for m in self.benchmark_results]
        
        report = {
            "summary": {
                "total_tests": len(self.benchmark_results),
                "avg_execution_time": statistics.mean(execution_times),
                "avg_memory_usage_mb": statistics.mean(memory_usage),
                "avg_cpu_usage_percent": statistics.mean(cpu_usage),
                "avg_throughput": statistics.mean(throughput),
            },
            "performance_breakdown": [m.to_dict() for m in self.benchmark_results],
            "recommendations": self.generate_performance_recommendations()
        }
        
        return report
    
    def generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not self.benchmark_results:
            return recommendations
        
        # Analyze patterns and generate recommendations
        slow_operations = [m for m in self.benchmark_results if m.execution_time > 5.0]
        if slow_operations:
            recommendations.append("Consider optimizing slow operations: " + 
                                 ", ".join([m.operation_name for m in slow_operations]))
        
        memory_heavy_operations = [m for m in self.benchmark_results if m.memory_usage_mb > 100]
        if memory_heavy_operations:
            recommendations.append("Consider memory optimization for: " + 
                                 ", ".join([m.operation_name for m in memory_heavy_operations]))
        
        low_throughput_operations = [m for m in self.benchmark_results if m.throughput_ops_per_sec < 1.0]
        if low_throughput_operations:
            recommendations.append("Consider throughput improvements for: " + 
                                 ", ".join([m.operation_name for m in low_throughput_operations]))
        
        return recommendations


@pytest.fixture(scope="session")
def performance_suite():
    """Create performance benchmark suite for session."""
    return PerformanceBenchmarkSuite()


@pytest.mark.performance
def test_generate_performance_report(performance_suite):
    """Generate final performance report."""
    report = performance_suite.generate_performance_report()
    
    # Save report to file
    report_path = "tests/perf/reports/benchmark_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nPerformance report saved to: {report_path}")
    print(f"Total tests run: {report['summary']['total_tests']}")
    print(f"Average execution time: {report['summary']['avg_execution_time']:.2f}s")
    print(f"Average memory usage: {report['summary']['avg_memory_usage_mb']:.2f}MB")


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([__file__, "-v", "-m", "performance"])