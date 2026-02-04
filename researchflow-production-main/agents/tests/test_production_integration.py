#!/usr/bin/env python3
"""
Production Integration Tests

Tests the integration between error tracking, startup orchestration,
and existing production infrastructure.

These tests verify:
- Complete production workflow
- Error tracking during startup
- Metrics collection during operations
- Health monitoring integration
- Graceful failure handling
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from agents.utils import (
    # Error tracking
    initialize_error_tracking,
    track_error,
    create_span,
    get_error_stats,
    clear_old_errors,
    get_error_tracker,
    
    # Startup orchestration
    StartupOrchestrator,
    register_startup_check,
    startup_agent_system,
    check_agent_readiness,
    check_agent_liveness,
    managed_agent_lifecycle,
    
    # Existing infrastructure
    get_metrics_collector,
    setup_structured_logging,
    track_agent_task,
    retry_api_call,
    timeout_api_call,
)


class TestProductionIntegration:
    """Test integration of all production components"""
    
    @pytest.fixture(autouse=True)
    def setup_clean_state(self):
        """Setup clean state for each test"""
        # Clear error tracking state
        get_error_tracker().error_history.clear()
        get_error_tracker().active_spans.clear()
        get_error_tracker().enabled = True
        
        # Initialize error tracking for tests
        initialize_error_tracking(environment="test", sample_rate=1.0)
        
        yield
        
        # Cleanup
        get_error_tracker().error_history.clear()
        get_error_tracker().active_spans.clear()
        
    @pytest.mark.asyncio
    async def test_complete_production_workflow(self):
        """Test complete production workflow with all components"""
        
        # Setup structured logging (silent for test)
        setup_structured_logging(level="ERROR")  # Quiet for tests
        
        # Create custom orchestrator for test isolation
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()  # Clear default checks for isolation
        
        # Register test startup checks
        @orchestrator.register_check("test_metrics", priority=1, timeout=5.0)
        async def check_metrics():
            """Test metrics system startup"""
            metrics = get_metrics_collector()
            return {"metrics_available": metrics is not None}
            
        @orchestrator.register_check(
            "test_error_tracking", 
            priority=2, 
            timeout=5.0,
            depends_on=["test_metrics"]
        )
        async def check_error_tracking():
            """Test error tracking system"""
            tracker = get_error_tracker()
            return {
                "error_tracking_enabled": tracker.enabled,
                "error_history_empty": len(tracker.error_history) == 0
            }
            
        @orchestrator.register_check(
            "test_integration",
            priority=3,
            timeout=5.0,
            depends_on=["test_error_tracking"]
        )
        async def check_integration():
            """Test integration components"""
            await asyncio.sleep(0.01)  # Simulate work
            return {"integration_ready": True}
            
        # Execute startup sequence
        metrics = await orchestrator.startup_sequence()
        
        # Verify successful startup
        assert orchestrator.is_ready
        assert orchestrator.is_live
        assert metrics.success_count == 3
        assert metrics.failure_count == 0
        
        # Test production task execution with all features
        @track_error(component="IntegrationTest", operation="test_task")
        @create_span("integration_test_task")
        @track_agent_task("IntegrationTest", "production_workflow")
        @retry_api_call(max_attempts=2, base_delay=0.1)
        @timeout_api_call(10.0)
        async def production_task():
            """Simulate production task with all infrastructure"""
            await asyncio.sleep(0.05)  # Simulate work
            return {"status": "success", "processed": True}
            
        # Execute task
        result = await production_task()
        assert result["status"] == "success"
        
        # Verify no errors were tracked for successful execution
        error_stats = await get_error_stats()
        assert error_stats.total_errors == 0
        
        # Test health probes
        readiness = await orchestrator.check_readiness()
        assert readiness["ready"]
        
        liveness = await orchestrator.check_liveness()
        assert liveness["alive"]
        
        # Test graceful shutdown
        await orchestrator.graceful_shutdown()
        assert not orchestrator.is_ready
        assert not orchestrator.is_live
        
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling across all components"""
        
        # Create orchestrator for test
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        # Register a check that will fail
        @orchestrator.register_check("failing_check", priority=1, timeout=5.0)
        async def failing_check():
            """Check that fails to test error handling"""
            raise RuntimeError("Test startup failure")
            
        # Execute startup (should fail)
        metrics = await orchestrator.startup_sequence()
        
        assert not orchestrator.is_ready
        assert metrics.failure_count == 1
        
        # Clear error history
        await clear_old_errors(hours=0)
        
        # Test error tracking in tasks
        @track_error(component="ErrorTest", operation="failing_task")
        @create_span("error_test_task")
        async def failing_task():
            """Task that fails to test error tracking"""
            raise ValueError("Intentional test error")
            
        # Execute failing task
        with pytest.raises(ValueError):
            await failing_task()
            
        # Verify error was tracked
        error_stats = await get_error_stats()
        assert error_stats.total_errors == 1
        assert "ValueError" in error_stats.error_types
        
    @pytest.mark.asyncio
    async def test_managed_lifecycle_integration(self):
        """Test managed agent lifecycle with full integration"""
        
        # Clear checks and setup test checks
        from agents.utils.startup_orchestrator import _orchestrator
        original_checks = _orchestrator.checks.copy()
        _orchestrator.checks.clear()
        _orchestrator.results.clear()
        
        # Register test checks
        @register_startup_check("lifecycle_test", priority=1, timeout=5.0)
        async def lifecycle_test():
            """Test check for lifecycle management"""
            return {"lifecycle": "ready"}
            
        try:
            # Use managed lifecycle
            async with managed_agent_lifecycle() as orchestrator:
                assert orchestrator.is_ready
                assert orchestrator.is_live
                
                # Execute production operations
                @track_error(component="LifecycleTest")
                @create_span("lifecycle_operation")
                async def lifecycle_operation():
                    await asyncio.sleep(0.01)
                    return "lifecycle_success"
                    
                result = await lifecycle_operation()
                assert result == "lifecycle_success"
                
            # After context exit, should be shut down
            assert not orchestrator.is_ready
            assert not orchestrator.is_live
            
        finally:
            # Restore original state
            _orchestrator.checks = original_checks
            
    @pytest.mark.asyncio
    async def test_performance_under_load_with_error_tracking(self):
        """Test system performance under load with error tracking"""
        
        # Setup
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        orchestrator.is_live = True
        
        # Clear error history
        await clear_old_errors(hours=0)
        
        # Create task that occasionally fails
        import random
        
        @track_error(component="LoadTest")
        @create_span("load_test_task")
        async def load_test_task(task_id: int):
            """Task for load testing"""
            await asyncio.sleep(0.001)  # Minimal work
            
            # 10% failure rate
            if random.random() < 0.1:
                raise RuntimeError(f"Load test error {task_id}")
                
            return {"task_id": task_id, "status": "success"}
            
        # Execute many tasks concurrently
        tasks = [load_test_task(i) for i in range(50)]
        
        # Measure performance
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Verify performance
        assert duration < 5.0  # Should complete quickly
        
        # Count successes and failures
        successes = sum(1 for r in results if isinstance(r, dict))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        assert successes + failures == 50
        assert successes > 40  # Most should succeed
        
        # Verify error tracking captured failures
        error_stats = await get_error_stats()
        assert error_stats.total_errors == failures
        
        if failures > 0:
            assert "RuntimeError" in error_stats.error_types
            
    @pytest.mark.asyncio
    async def test_health_monitoring_with_errors(self):
        """Test health monitoring integration with error conditions"""
        
        # Setup orchestrator
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        orchestrator.is_live = True
        orchestrator.startup_start_time = time.time()
        
        # Clear error history
        await clear_old_errors(hours=0)
        
        # Initial health should be good
        readiness = await orchestrator.check_readiness()
        assert readiness["ready"]
        
        # Simulate errors
        for i in range(10):
            try:
                raise RuntimeError(f"Health test error {i}")
            except Exception as e:
                await get_error_tracker().track_error(
                    error=e,
                    component="HealthTest",
                    operation="error_simulation"
                )
                
        # Check error health
        from agents.utils.error_tracking import check_error_health
        error_health = await check_error_health(error_rate_threshold=0.1)
        
        # Should detect high error rate
        assert not error_health["healthy"]
        assert error_health["error_rate"] > 0.1
        
        # Basic readiness should still work (depends on health check implementation)
        readiness = await orchestrator.check_readiness()
        # Note: Basic readiness might still pass even with errors
        # depending on health check configuration
        
    @pytest.mark.asyncio
    async def test_concurrent_operations_with_tracing(self):
        """Test concurrent operations with distributed tracing"""
        
        from agents.utils.error_tracking import TraceContext
        
        # Clear spans
        get_error_tracker().active_spans.clear()
        
        async def traced_operation(operation_id: int):
            """Operation with tracing"""
            async with TraceContext(f"operation_{operation_id}", "ConcurrentTest"):
                await asyncio.sleep(0.01)
                
                # Nested span
                async with TraceContext(f"nested_{operation_id}", "ConcurrentTest"):
                    await asyncio.sleep(0.005)
                    
                return operation_id
                
        # Execute concurrent operations
        operations = [traced_operation(i) for i in range(10)]
        results = await asyncio.gather(*operations)
        
        # Verify all completed
        assert len(results) == 10
        assert sorted(results) == list(range(10))
        
        # All spans should be cleaned up
        assert len(get_error_tracker().active_spans) == 0
        
    @pytest.mark.asyncio
    async def test_startup_failure_recovery(self):
        """Test system behavior during startup failures"""
        
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        attempt_count = 0
        
        @orchestrator.register_check(
            "flaky_startup",
            priority=1,
            timeout=5.0,
            retry_count=3,
            retry_delay=0.01
        )
        async def flaky_startup():
            """Check that fails first few times"""
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise RuntimeError(f"Startup attempt {attempt_count} failed")
                
            return {"attempts": attempt_count, "status": "success"}
            
        # Execute startup
        metrics = await orchestrator.startup_sequence()
        
        # Should eventually succeed
        assert orchestrator.is_ready
        assert metrics.success_count == 1
        assert attempt_count == 3  # Should have retried
        
    @pytest.mark.asyncio 
    async def test_timeout_integration(self):
        """Test timeout handling with error tracking"""
        
        @track_error(component="TimeoutTest")
        @timeout_api_call(0.1)  # Very short timeout
        async def slow_operation():
            """Operation that will timeout"""
            await asyncio.sleep(1.0)  # Will timeout
            return "should_not_reach"
            
        # Should timeout and track error
        from agents.utils.timeout import TimeoutError
        with pytest.raises(TimeoutError):
            await slow_operation()
            
        # Should have tracked the timeout as an error
        error_stats = await get_error_stats()
        assert error_stats.total_errors == 1
        assert "TimeoutError" in error_stats.error_types
        
    @pytest.mark.asyncio
    async def test_retry_integration_with_tracing(self):
        """Test retry logic with distributed tracing"""
        
        attempt_count = 0
        
        @track_error(component="RetryTest")
        @create_span("retry_operation")
        @retry_api_call(max_attempts=3, base_delay=0.01)
        async def retryable_operation():
            """Operation that succeeds on third attempt"""
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise RuntimeError(f"Attempt {attempt_count} failed")
                
            return {"attempts": attempt_count, "success": True}
            
        # Execute with retries
        result = await retryable_operation()
        
        # Should succeed after retries
        assert result["success"]
        assert result["attempts"] == 3
        
        # Should track errors for failed attempts but not final success
        error_stats = await get_error_stats()
        # Note: The retry decorator tracks intermediate failures
        assert error_stats.total_errors >= 2  # At least 2 failed attempts


class TestSystemBoundaries:
    """Test system behavior at boundaries and edge cases"""
    
    @pytest.mark.asyncio
    async def test_startup_timeout_handling(self):
        """Test startup check timeout handling"""
        
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        @orchestrator.register_check("timeout_check", priority=1, timeout=0.1)
        async def timeout_check():
            """Check that times out"""
            await asyncio.sleep(1.0)  # Will timeout
            return {"should": "not_reach"}
            
        # Execute startup
        metrics = await orchestrator.startup_sequence()
        
        # Should handle timeout gracefully
        assert not orchestrator.is_ready
        assert metrics.timeout_count == 1
        assert metrics.failure_count == 0  # Timeouts are separate from failures
        
    @pytest.mark.asyncio
    async def test_error_tracking_without_sentry(self):
        """Test error tracking works without Sentry backend"""
        
        # Reinitialize without Sentry DSN
        initialize_error_tracking(dsn=None, environment="test")
        
        # Clear error history
        await clear_old_errors(hours=0)
        
        @track_error(component="NoSentryTest")
        async def test_operation():
            """Operation that fails"""
            raise ValueError("Test error without Sentry")
            
        # Should still track error locally
        with pytest.raises(ValueError):
            await test_operation()
            
        # Verify local tracking works
        error_stats = await get_error_stats()
        assert error_stats.total_errors == 1
        assert "ValueError" in error_stats.error_types
        
    @pytest.mark.asyncio
    async def test_large_error_history_cleanup(self):
        """Test error history size management"""
        
        # Clear and simulate large error history
        tracker = get_error_tracker()
        await clear_old_errors(hours=0)
        
        # Add many errors
        for i in range(1200):  # More than limit
            await tracker.track_error(
                error=RuntimeError(f"Error {i}"),
                component="CleanupTest",
                operation="bulk_error_test"
            )
            
        # Should limit to 1000
        assert len(tracker.error_history) == 1000
        
        # Should keep most recent errors
        last_error = tracker.error_history[-1]
        assert "Error 1199" in last_error["error_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])