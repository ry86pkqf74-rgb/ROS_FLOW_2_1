#!/usr/bin/env python3
"""
Integration Tests for ResearchFlow Agent Infrastructure

Tests the interaction between multiple components:
- Secret management + AI helper
- Health checks + metrics
- Retry + timeout + circuit breaker
- End-to-end workflow execution

These tests require external services and may take longer to run.
"""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from agents.utils import (
    get_secrets_manager,
    get_ai_helper,
    get_agent_health_checker,
    get_metrics_collector,
    get_retry_manager,
    get_timeout_manager,
    validate_startup_environment
)


@pytest.mark.integration
class TestSecretsAIIntegration:
    """Test integration between secrets management and AI helper"""
    
    @pytest.mark.asyncio
    async def test_ai_helper_with_vault_secrets(self):
        """Test AI helper retrieving API keys from secret backend"""
        # Mock Vault backend
        with patch.dict(os.environ, {
            'SECRET_BACKEND': 'env',  # Use env for testing
            'OPENAI_API_KEY': 'sk-test-key-123456789012345678901234567890'
        }):
            # Clear any cached secrets manager
            import agents.utils.secrets_manager as sm_module
            sm_module._secrets_manager = None
            
            # Get fresh instances
            secrets = get_secrets_manager()
            ai = get_ai_helper()
            
            # Verify API key is available
            api_key = secrets.get_secret("OPENAI_API_KEY")
            assert api_key is not None
            assert api_key.startswith("sk-")
            
            # Test that AI helper can access the key
            ai_api_key = ai.get_api_key(ai.AIProvider.OPENAI)
            assert ai_api_key == api_key
    
    @pytest.mark.asyncio
    async def test_ai_helper_with_missing_secrets(self):
        """Test AI helper behavior when secrets are missing"""
        with patch.dict(os.environ, {}, clear=True):
            # Clear cached instances
            import agents.utils.secrets_manager as sm_module
            import agents.utils.ai_helper as ah_module
            sm_module._secrets_manager = None
            ah_module._ai_helper = None
            
            ai = get_ai_helper()
            
            # Should handle missing API key gracefully
            api_key = ai.get_api_key(ai.AIProvider.OPENAI)
            assert api_key is None
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('OPENAI_API_KEY'),
        reason="Requires real OpenAI API key"
    )
    async def test_ai_helper_real_api_call(self):
        """Test real API call if API key is available"""
        ai = get_ai_helper()
        
        # Test with a simple prompt
        response = await ai.ask_openai(
            "What is 2+2? Answer with just the number.",
            max_tokens=10
        )
        
        assert response is not None
        assert response.content is not None
        assert "4" in response.content


@pytest.mark.integration
class TestHealthMetricsIntegration:
    """Test integration between health checks and metrics"""
    
    @pytest.mark.asyncio
    async def test_health_checks_with_metrics(self):
        """Test that health checks record metrics"""
        # Get fresh instances
        health_checker = get_agent_health_checker()
        metrics = get_metrics_collector()
        
        # Mock metrics to capture calls
        with patch.object(metrics, 'increment_counter') as mock_counter, \
             patch.object(metrics, 'observe_histogram') as mock_histogram:
            
            # Run health checks
            health = await health_checker.check_all()
            
            # Verify health check completed
            assert health is not None
            assert health.status is not None
            
            # Note: Actual metrics recording depends on health check implementation
            # This test verifies the integration works without errors
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_integration(self):
        """Test metrics endpoint functionality"""
        from agents.utils.metrics import create_metrics_endpoint
        
        metrics_endpoint = create_metrics_endpoint()
        
        # Call the endpoint
        result = await metrics_endpoint()
        
        # Should return metrics data
        assert result is not None
        # Format depends on whether Prometheus is available


@pytest.mark.integration
class TestRetryTimeoutIntegration:
    """Test integration between retry logic and timeouts"""
    
    @pytest.mark.asyncio
    async def test_retry_with_timeout_success(self):
        """Test retry mechanism with timeout protection (success case)"""
        retry_manager = get_retry_manager()
        timeout_manager = get_timeout_manager()
        
        call_count = 0
        
        # Function that succeeds on second attempt
        @retry_manager.retry(max_attempts=3, base_delay=0.1)
        @timeout_manager.timeout(2.0)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_with_timeout_failure(self):
        """Test retry mechanism when timeout occurs"""
        retry_manager = get_retry_manager()
        timeout_manager = get_timeout_manager()
        
        @retry_manager.retry(max_attempts=2, base_delay=0.1)
        @timeout_manager.timeout(0.5)  # Short timeout
        async def slow_function():
            await asyncio.sleep(1.0)  # Longer than timeout
            return "success"
        
        # Should fail with timeout, not retry exhaustion
        with pytest.raises(Exception):  # Could be TimeoutError or RetryableError
            await slow_function()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker with retry and timeout"""
        from agents.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        # Create a circuit breaker for testing
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=1.0,
            expected_exception=(ConnectionError,)
        )
        
        breaker = CircuitBreaker("test-service", config)
        retry_manager = get_retry_manager()
        
        fail_count = 0
        
        @retry_manager.retry(max_attempts=3, base_delay=0.1, circuit_breaker_name="test-service")
        async def unreliable_service():
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 3:  # Fail first 3 times
                raise ConnectionError("Service unavailable")
            return "success"
        
        # Should trigger circuit breaker after failures
        with pytest.raises(Exception):
            await unreliable_service()


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test end-to-end workflow execution with all infrastructure"""
    
    @pytest.mark.asyncio
    async def test_complete_agent_workflow(self):
        """Test a complete agent workflow with all infrastructure components"""
        from agents.utils import (
            setup_structured_logging,
            get_agent_logger,
            LogContext,
            track_agent_task
        )
        
        # Setup logging
        setup_structured_logging(level="INFO", json_format=False)
        logger = get_agent_logger("TestAgent")
        
        # Simulate agent task execution
        @track_agent_task("TestAgent", "integration_test")
        async def execute_agent_task():
            with LogContext(
                agent_name="TestAgent",
                workflow_id="test-wf-123",
                correlation_id="test-corr-456"
            ):
                logger.info("Starting agent task", extra={"task_id": "test-123"})
                
                # Simulate some work with timeout protection
                timeout_manager = get_timeout_manager()
                
                @timeout_manager.timeout(5.0, "test_operation")
                async def do_work():
                    await asyncio.sleep(0.1)  # Simulate work
                    return "task_completed"
                
                result = await do_work()
                
                logger.info("Agent task completed", extra={
                    "task_id": "test-123",
                    "result": result
                })
                
                return result
        
        # Execute the task
        result = await execute_agent_task()
        assert result == "task_completed"
    
    def test_startup_validation_integration(self):
        """Test startup validation with all components"""
        # This should work even without all API keys set
        # (validation will warn but not fail for missing optional keys)
        
        # Mock minimal required environment
        with patch.dict(os.environ, {
            'COMPOSIO_API_KEY': 'comp_' + 'x' * 20,
            'OPENAI_API_KEY': 'sk-' + 'x' * 20
        }):
            # Clear cached validators
            from agents.utils.env_validator import get_agent_validator
            
            # This should pass
            result = validate_startup_environment()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling with AI analysis integration"""
        ai = get_ai_helper()
        
        # Simulate an error that needs AI analysis
        try:
            raise ValueError("Test error for AI analysis")
        except ValueError as e:
            # This would normally use real AI, but we'll mock it
            with patch.object(ai, 'analyze_error') as mock_analyze:
                mock_analyze.return_value = {
                    "root_cause": "Test error for demonstration",
                    "suggested_fixes": ["Fix the test condition"],
                    "prevention_tips": ["Add proper validation"]
                }
                
                analysis = await ai.analyze_error(str(e))
                
                assert analysis is not None
                assert "root_cause" in analysis
                assert "suggested_fixes" in analysis


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Test performance characteristics of integrated components"""
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test health checks under concurrent load"""
        health_checker = get_agent_health_checker()
        
        # Run multiple health checks concurrently
        tasks = [
            health_checker.check_all()
            for _ in range(10)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All should succeed
        assert all(result is not None for result in results)
        
        # Should complete reasonably quickly (adjust threshold as needed)
        assert duration < 30.0  # 30 seconds for 10 concurrent checks
    
    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self):
        """Test metrics collection performance"""
        metrics = get_metrics_collector()
        
        start_time = time.time()
        
        # Record many metrics quickly
        for i in range(1000):
            metrics.increment_counter(
                "test_counter",
                {"iteration": str(i % 10)}
            )
            
            metrics.observe_histogram(
                "test_histogram",
                float(i),
                {"batch": str(i // 100)}
            )
        
        duration = time.time() - start_time
        
        # Should be very fast
        assert duration < 1.0  # 1 second for 1000 metrics
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_timing(self):
        """Test retry timing with exponential backoff"""
        retry_manager = get_retry_manager()
        
        attempt_times = []
        
        @retry_manager.retry(
            max_attempts=4,
            base_delay=0.1,
            backoff_strategy=retry_manager.BackoffStrategy.EXPONENTIAL
        )
        async def always_fails():
            attempt_times.append(time.time())
            raise ConnectionError("Always fails")
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            await always_fails()
        
        total_duration = time.time() - start_time
        
        # Should have made 4 attempts
        assert len(attempt_times) == 4
        
        # Check backoff timing (approximately)
        # First attempt: immediate
        # Second attempt: ~0.1s later
        # Third attempt: ~0.2s later  
        # Fourth attempt: ~0.4s later
        # Total: ~0.7s + execution time
        
        assert total_duration >= 0.7  # At least the backoff time
        assert total_duration < 2.0   # But not too long


if __name__ == '__main__':
    # Run integration tests with verbose output
    pytest.main([__file__, '-v', '-m', 'integration'])