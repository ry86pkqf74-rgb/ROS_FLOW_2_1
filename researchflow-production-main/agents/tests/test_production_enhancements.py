#!/usr/bin/env python3
"""
Unit Tests for Production Enhancements

Tests the new production features:
- Metrics collection
- Advanced health checks
- Configuration management
- Retry logic
- Timeout protection
- Performance testing
- Rate limiting
"""

import pytest
import asyncio
import time
import os
from unittest.mock import Mock, patch, AsyncMock
from agents.utils import (
    get_metrics_collector,
    get_advanced_health_checker,
    get_config_manager,
    get_retry_manager,
    get_timeout_manager,
    get_performance_tester,
    get_rate_limiter,
    RateLimitConfig,
    BackoffStrategy,
    TimeoutError,
    RateLimitExceeded
)


class TestMetricsCollection:
    """Test metrics collection functionality"""
    
    def test_metrics_collector_singleton(self):
        """Test metrics collector is singleton"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2
    
    def test_counter_increment(self):
        """Test counter metric increment"""
        collector = get_metrics_collector()
        
        # Should not raise exception
        collector.increment_counter("test_counter", {"label": "value"})
        collector.increment_counter("test_counter", {"label": "value"}, amount=5)
    
    def test_histogram_observation(self):
        """Test histogram metric observation"""
        collector = get_metrics_collector()
        
        # Should not raise exception
        collector.observe_histogram("test_histogram", 1.23, {"label": "value"})
    
    def test_gauge_setting(self):
        """Test gauge metric setting"""
        collector = get_metrics_collector()
        
        # Should not raise exception
        collector.set_gauge("test_gauge", 42.0, {"label": "value"})
    
    def test_track_agent_task_decorator(self):
        """Test track_agent_task decorator"""
        from agents.utils.metrics import track_agent_task
        
        call_count = 0
        
        @track_agent_task("TestAgent", "test_task")
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        assert result == "success"
        assert call_count == 1


class TestAdvancedHealthChecks:
    """Test advanced health check functionality"""
    
    @pytest.mark.asyncio
    async def test_system_resources_check(self):
        """Test system resources health check"""
        from agents.utils.advanced_health import AdvancedHealthChecker
        
        checker = AdvancedHealthChecker()
        is_healthy, message, details = await checker.check_system_resources()
        
        assert isinstance(is_healthy, bool)
        assert isinstance(message, str)
        assert isinstance(details, dict)
        assert "cpu_percent" in details
        assert "memory_percent" in details
    
    @pytest.mark.asyncio
    async def test_disk_space_check(self):
        """Test disk space health check"""
        from agents.utils.advanced_health import AdvancedHealthChecker
        
        checker = AdvancedHealthChecker()
        is_healthy, message, details = await checker.check_disk_space()
        
        assert isinstance(is_healthy, bool)
        assert isinstance(message, str)
        assert isinstance(details, dict)
    
    @pytest.mark.asyncio
    async def test_workflow_dependencies_check(self):
        """Test workflow dependencies health check"""
        from agents.utils.advanced_health import AdvancedHealthChecker
        
        checker = AdvancedHealthChecker()
        is_healthy, message, details = await checker.check_workflow_dependencies()
        
        assert isinstance(is_healthy, bool)
        assert isinstance(message, str)
        assert isinstance(details, dict)
        assert "successful_imports" in details


class TestConfigurationManagement:
    """Test configuration management"""
    
    def test_config_manager_singleton(self):
        """Test config manager is singleton"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        assert manager1 is manager2
    
    def test_load_default_config(self):
        """Test loading default configuration"""
        manager = get_config_manager()
        config = manager.load_config("development")
        
        assert config.environment.value == "development"
        assert config.debug is False  # Default for dataclass
        assert config.database is not None
        assert config.api is not None
    
    def test_environment_variable_override(self):
        """Test environment variable overrides"""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'METRICS_ENABLED': 'false'
        }):
            manager = get_config_manager()
            config = manager.load_config()
            
            assert config.logging.level == "DEBUG"
            assert config.metrics.enabled is False


class TestRetryLogic:
    """Test retry logic functionality"""
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test retry succeeds after initial failures"""
        retry_manager = get_retry_manager()
        
        call_count = 0
        
        @retry_manager.retry(max_attempts=3, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry gives up after max attempts"""
        retry_manager = get_retry_manager()
        
        @retry_manager.retry(max_attempts=2, base_delay=0.01)
        async def always_fails():
            raise ConnectionError("Always fails")
        
        with pytest.raises(Exception):  # RetryableError
            await always_fails()
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff timing"""
        retry_manager = get_retry_manager()
        
        attempt_times = []
        
        @retry_manager.retry(
            max_attempts=3,
            base_delay=0.1,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False  # Disable jitter for predictable timing
        )
        async def timing_test():
            attempt_times.append(time.time())
            raise ConnectionError("Fail")
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            await timing_test()
        
        # Should have 3 attempts
        assert len(attempt_times) == 3
        
        # Check approximate timing (allowing for some variance)
        total_time = time.time() - start_time
        # Expected: 0 + 0.1 + 0.2 = 0.3 seconds minimum
        assert total_time >= 0.25  # Allow some variance


class TestTimeoutProtection:
    """Test timeout protection"""
    
    @pytest.mark.asyncio
    async def test_timeout_success(self):
        """Test function completes within timeout"""
        timeout_manager = get_timeout_manager()
        
        @timeout_manager.timeout(1.0)
        async def fast_function():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await fast_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test function times out"""
        timeout_manager = get_timeout_manager()
        
        @timeout_manager.timeout(0.1)
        async def slow_function():
            await asyncio.sleep(1.0)
            return "should not reach here"
        
        with pytest.raises(TimeoutError) as exc_info:
            await slow_function()
        
        assert exc_info.value.timeout_seconds == 0.1
    
    @pytest.mark.asyncio
    async def test_timeout_context_manager(self):
        """Test timeout context manager"""
        timeout_manager = get_timeout_manager()
        
        async with timeout_manager.timeout_context(1.0, "test_operation"):
            await asyncio.sleep(0.1)  # Should succeed
        
        with pytest.raises(TimeoutError):
            async with timeout_manager.timeout_context(0.1, "test_operation"):
                await asyncio.sleep(1.0)  # Should timeout


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_token_bucket_acquire(self):
        """Test token bucket acquisition"""
        from agents.utils.rate_limiting import TokenBucket
        
        bucket = TokenBucket(capacity=5, fill_rate=1.0)
        
        # Should be able to acquire initial tokens
        for _ in range(5):
            acquired = await bucket.acquire()
            assert acquired is True
        
        # Should fail to acquire more
        acquired = await bucket.acquire()
        assert acquired is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_decorator(self):
        """Test rate limiter decorator"""
        config = RateLimitConfig(
            requests_per_second=10.0,
            burst_size=5
        )
        limiter = get_rate_limiter("test", config)
        
        call_count = 0
        
        @limiter.limit()
        async def limited_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        # Should succeed within burst
        for _ in range(5):
            result = await limited_function()
            assert result == "success"
        
        assert call_count == 5
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit exceeded exception"""
        config = RateLimitConfig(
            requests_per_second=1.0,
            burst_size=1
        )
        limiter = get_rate_limiter("test_exceed", config)
        
        @limiter.limit()
        async def limited_function():
            return "success"
        
        # First call should succeed
        result = await limited_function()
        assert result == "success"
        
        # Second call should fail
        with pytest.raises(RateLimitExceeded):
            await limited_function()


@pytest.mark.slow
class TestPerformanceTesting:
    """Test performance testing utilities"""
    
    @pytest.mark.asyncio
    async def test_benchmark_function(self):
        """Test function benchmarking"""
        tester = get_performance_tester()
        
        async def test_function():
            await asyncio.sleep(0.001)  # 1ms
            return "result"
        
        result = await tester.benchmark_function(
            test_function,
            iterations=10,
            warmup_iterations=2
        )
        
        assert result.operation == "test_function"
        assert result.total_operations == 10
        assert result.operations_per_second > 0
        assert result.mean_latency > 0
        assert result.error_rate == 0
    
    @pytest.mark.asyncio
    async def test_load_test(self):
        """Test load testing"""
        from agents.utils.performance import LoadTestConfig
        
        tester = get_performance_tester()
        
        async def test_operation():
            await asyncio.sleep(0.01)  # 10ms
            return "result"
        
        config = LoadTestConfig(
            concurrent_users=5,
            total_requests=25,
            ramp_up_duration=0.1,
            monitor_resources=False  # Disable for test speed
        )
        
        results = await tester.load_test(test_operation, config)
        
        assert results["successful_requests"] == 25
        assert results["failed_requests"] == 0
        assert results["throughput_rps"] > 0
        assert results["error_rate"] == 0


class TestIntegratedFeatures:
    """Test integration between new features"""
    
    @pytest.mark.asyncio
    async def test_retry_with_timeout_and_rate_limiting(self):
        """Test retry, timeout, and rate limiting working together"""
        # Create components
        retry_manager = get_retry_manager()
        timeout_manager = get_timeout_manager()
        rate_limiter = get_rate_limiter("integrated_test", RateLimitConfig(
            requests_per_second=10.0,
            burst_size=5
        ))
        
        call_count = 0
        
        @rate_limiter.limit()
        @retry_manager.retry(max_attempts=3, base_delay=0.01)
        @timeout_manager.timeout(1.0)
        async def integrated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            await asyncio.sleep(0.01)
            return "success"
        
        result = await integrated_function()
        assert result == "success"
        assert call_count == 2
    
    def test_all_managers_are_singletons(self):
        """Test all managers maintain singleton pattern"""
        # Get instances twice
        metrics1 = get_metrics_collector()
        metrics2 = get_metrics_collector()
        
        config1 = get_config_manager()
        config2 = get_config_manager()
        
        retry1 = get_retry_manager()
        retry2 = get_retry_manager()
        
        timeout1 = get_timeout_manager()
        timeout2 = get_timeout_manager()
        
        perf1 = get_performance_tester()
        perf2 = get_performance_tester()
        
        # Verify singletons
        assert metrics1 is metrics2
        assert config1 is config2
        assert retry1 is retry2
        assert timeout1 is timeout2
        assert perf1 is perf2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])