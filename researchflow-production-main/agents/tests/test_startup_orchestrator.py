#!/usr/bin/env python3
"""
Tests for Startup Orchestration

Tests cover:
- Startup check registration and execution
- Dependency resolution
- Error handling and retry logic
- Kubernetes probe endpoints
- Graceful shutdown handling
- Health check integration
"""

import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from agents.utils.startup_orchestrator import (
    StartupOrchestrator,
    StartupCheck,
    CheckResult,
    StartupMetrics,
    StartupStatus,
    OrchestrationPhase,
    get_startup_orchestrator,
    register_startup_check,
    startup_agent_system,
    check_agent_readiness,
    check_agent_liveness,
    get_agent_startup_status,
    managed_agent_lifecycle,
    _orchestrator
)


class TestStartupOrchestrator:
    """Test StartupOrchestrator class"""
    
    def test_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = StartupOrchestrator(max_startup_time=120.0)
        
        assert orchestrator.max_startup_time == 120.0
        assert not orchestrator.is_ready
        assert not orchestrator.is_live
        assert orchestrator.startup_start_time is None
        
        # Should have default system checks registered
        assert len(orchestrator.checks) >= 4
        assert "environment_validation" in orchestrator.checks
        assert "configuration_load" in orchestrator.checks
        assert "secrets_access" in orchestrator.checks
        assert "health_subsystem" in orchestrator.checks
        
    def test_register_check_decorator(self):
        """Test check registration via decorator"""
        orchestrator = StartupOrchestrator()
        
        @orchestrator.register_check(
            name="test_check",
            priority=10,
            timeout=30.0,
            description="Test check"
        )
        async def test_check():
            return {"status": "ok"}
            
        assert "test_check" in orchestrator.checks
        check = orchestrator.checks["test_check"]
        
        assert check.name == "test_check"
        assert check.priority == 10
        assert check.timeout == 30.0
        assert check.description == "Test check"
        assert check.func is test_check
        

class TestDependencyResolution:
    """Test dependency resolution and execution order"""
    
    def test_simple_dependency_resolution(self):
        """Test resolving dependencies in correct order"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()  # Clear default checks
        
        # Register checks with dependencies
        @orchestrator.register_check("check_a", priority=3)
        async def check_a():
            return {"status": "ok"}
            
        @orchestrator.register_check("check_b", priority=1, depends_on=["check_a"])
        async def check_b():
            return {"status": "ok"}
            
        @orchestrator.register_check("check_c", priority=2, depends_on=["check_b"])
        async def check_c():
            return {"status": "ok"}
            
        execution_order = orchestrator._resolve_dependencies()
        
        # Should be ordered: check_a, check_b, check_c
        assert len(execution_order) == 3
        assert execution_order[0].name == "check_a"
        assert execution_order[1].name == "check_b"
        assert execution_order[2].name == "check_c"
        
    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        # Create circular dependency
        @orchestrator.register_check("check_a", priority=1, depends_on=["check_b"])
        async def check_a():
            return {"status": "ok"}
            
        @orchestrator.register_check("check_b", priority=2, depends_on=["check_a"])
        async def check_b():
            return {"status": "ok"}
            
        with pytest.raises(RuntimeError, match="Circular dependency"):
            orchestrator._resolve_dependencies()
            
    def test_missing_dependency(self):
        """Test handling missing dependencies"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        @orchestrator.register_check("check_a", priority=1, depends_on=["missing_check"])
        async def check_a():
            return {"status": "ok"}
            
        with pytest.raises(RuntimeError, match="Circular dependency"):
            orchestrator._resolve_dependencies()
            

class TestCheckExecution:
    """Test individual check execution"""
    
    @pytest.mark.asyncio
    async def test_successful_check_execution(self):
        """Test successful check execution"""
        orchestrator = StartupOrchestrator()
        
        async def test_check():
            return {"result": "success", "value": 42}
            
        check = StartupCheck(
            name="test_check",
            func=test_check,
            priority=1,
            timeout=10.0
        )
        
        result = await orchestrator._execute_check(check)
        
        assert result.name == "test_check"
        assert result.status == StartupStatus.SUCCESS
        assert result.message == "Check passed successfully"
        assert result.metadata == {"result": "success", "value": 42}
        assert result.duration > 0
        
    @pytest.mark.asyncio
    async def test_failing_check_execution(self):
        """Test failing check execution"""
        orchestrator = StartupOrchestrator()
        
        async def failing_check():
            raise ValueError("Check failed")
            
        check = StartupCheck(
            name="failing_check",
            func=failing_check,
            priority=1,
            timeout=10.0,
            retry_count=1  # Single attempt
        )
        
        result = await orchestrator._execute_check(check)
        
        assert result.name == "failing_check"
        assert result.status == StartupStatus.FAILED
        assert "Check failed" in result.message
        assert isinstance(result.error, ValueError)
        
    @pytest.mark.asyncio
    async def test_timeout_check_execution(self):
        """Test check timeout"""
        orchestrator = StartupOrchestrator()
        
        async def slow_check():
            await asyncio.sleep(1.0)  # Will timeout
            return {"status": "ok"}
            
        check = StartupCheck(
            name="slow_check",
            func=slow_check,
            priority=1,
            timeout=0.1,  # Very short timeout
            retry_count=1
        )
        
        result = await orchestrator._execute_check(check)
        
        assert result.name == "slow_check"
        assert result.status == StartupStatus.TIMEOUT
        assert "timed out" in result.message
        
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test check retry logic"""
        orchestrator = StartupOrchestrator()
        attempt_count = 0
        
        async def flaky_check():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise RuntimeError(f"Attempt {attempt_count} failed")
            return {"status": "ok", "attempts": attempt_count}
            
        check = StartupCheck(
            name="flaky_check",
            func=flaky_check,
            priority=1,
            timeout=10.0,
            retry_count=3,
            retry_delay=0.01  # Fast retry for test
        )
        
        result = await orchestrator._execute_check(check)
        
        assert result.name == "flaky_check"
        assert result.status == StartupStatus.SUCCESS
        assert result.metadata["attempts"] == 3
        assert attempt_count == 3
        

class TestStartupSequence:
    """Test complete startup sequence"""
    
    @pytest.mark.asyncio
    async def test_successful_startup_sequence(self):
        """Test successful startup sequence"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()  # Clear default checks for simpler test
        
        # Add test checks
        @orchestrator.register_check("check_1", priority=1, timeout=1.0)
        async def check_1():
            await asyncio.sleep(0.01)
            return {"status": "ok"}
            
        @orchestrator.register_check("check_2", priority=2, timeout=1.0, depends_on=["check_1"])
        async def check_2():
            await asyncio.sleep(0.01)
            return {"status": "ok"}
            
        metrics = await orchestrator.startup_sequence()
        
        assert orchestrator.is_ready
        assert orchestrator.is_live
        assert metrics.check_count == 2
        assert metrics.success_count == 2
        assert metrics.failure_count == 0
        assert metrics.total_duration > 0
        
    @pytest.mark.asyncio
    async def test_failed_startup_sequence(self):
        """Test startup sequence with critical failure"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        @orchestrator.register_check("success_check", priority=1, timeout=1.0)
        async def success_check():
            return {"status": "ok"}
            
        @orchestrator.register_check("critical_fail", priority=2, timeout=1.0, critical=True)
        async def critical_fail():
            raise RuntimeError("Critical failure")
            
        @orchestrator.register_check("skipped_check", priority=3, timeout=1.0)
        async def skipped_check():
            return {"status": "ok"}  # Should not execute after critical failure
            
        metrics = await orchestrator.startup_sequence()
        
        assert not orchestrator.is_ready
        assert not orchestrator.is_live
        assert metrics.success_count == 1
        assert metrics.failure_count == 1
        # Third check should not execute due to critical failure
        assert metrics.check_count == 2
        
    @pytest.mark.asyncio
    async def test_non_critical_failure(self):
        """Test startup with non-critical failure"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        @orchestrator.register_check("success_check", priority=1, timeout=1.0)
        async def success_check():
            return {"status": "ok"}
            
        @orchestrator.register_check("non_critical_fail", priority=2, timeout=1.0, critical=False)
        async def non_critical_fail():
            raise RuntimeError("Non-critical failure")
            
        @orchestrator.register_check("final_check", priority=3, timeout=1.0)
        async def final_check():
            return {"status": "ok"}
            
        metrics = await orchestrator.startup_sequence()
        
        assert orchestrator.is_ready  # Should still be ready
        assert orchestrator.is_live
        assert metrics.success_count == 2
        assert metrics.failure_count == 1
        assert metrics.check_count == 3
        

class TestHealthProbes:
    """Test Kubernetes health probe endpoints"""
    
    @pytest.mark.asyncio
    async def test_readiness_probe_not_ready(self):
        """Test readiness probe when not ready"""
        orchestrator = StartupOrchestrator()
        
        readiness = await orchestrator.check_readiness()
        
        assert not readiness["ready"]
        assert "not completed" in readiness["message"]
        assert "timestamp" in readiness
        
    @pytest.mark.asyncio
    async def test_readiness_probe_ready(self):
        """Test readiness probe when ready"""
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        orchestrator.startup_start_time = time.time() - 10.0  # Started 10 seconds ago
        
        with patch('agents.utils.startup_orchestrator.get_health_checker') as mock_health:
            mock_checker = AsyncMock()
            mock_checker.check_basic_health.return_value = {"status": "healthy"}
            mock_health.return_value = mock_checker
            
            readiness = await orchestrator.check_readiness()
            
            assert readiness["ready"]
            assert "health" in readiness
            assert readiness["startup_time"] > 9.0
            assert readiness["checks_completed"] == 0
            
    @pytest.mark.asyncio
    async def test_readiness_probe_health_failure(self):
        """Test readiness probe with health check failure"""
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        
        with patch('agents.utils.startup_orchestrator.get_health_checker') as mock_health:
            mock_checker = AsyncMock()
            mock_checker.check_basic_health.side_effect = Exception("Health check failed")
            mock_health.return_value = mock_checker
            
            readiness = await orchestrator.check_readiness()
            
            assert not readiness["ready"]
            assert "health check failed" in readiness["message"]
            
    @pytest.mark.asyncio
    async def test_liveness_probe_not_live(self):
        """Test liveness probe when not live"""
        orchestrator = StartupOrchestrator()
        
        liveness = await orchestrator.check_liveness()
        
        assert not liveness["alive"]
        assert "not initialized" in liveness["message"]
        
    @pytest.mark.asyncio
    async def test_liveness_probe_alive(self):
        """Test liveness probe when alive"""
        orchestrator = StartupOrchestrator()
        orchestrator.is_live = True
        orchestrator.startup_start_time = time.time() - 30.0
        
        liveness = await orchestrator.check_liveness()
        
        assert liveness["alive"]
        assert liveness["uptime"] > 29.0
        assert "timestamp" in liveness
        

class TestStartupStatus:
    """Test startup status reporting"""
    
    def test_get_startup_status(self):
        """Test getting comprehensive startup status"""
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        orchestrator.is_live = True
        orchestrator.startup_start_time = time.time()
        
        # Add some results
        orchestrator.results["test_check"] = CheckResult(
            name="test_check",
            status=StartupStatus.SUCCESS,
            duration=1.5,
            message="Test passed"
        )
        
        status = orchestrator.get_startup_status()
        
        assert status["ready"]
        assert status["live"]
        assert "checks" in status
        assert "test_check" in status["checks"]
        
        check_status = status["checks"]["test_check"]
        assert check_status["status"] == "success"
        assert check_status["duration"] == 1.5
        assert check_status["message"] == "Test passed"
        assert "timestamp" in check_status
        

class TestGracefulShutdown:
    """Test graceful shutdown handling"""
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown"""
        orchestrator = StartupOrchestrator()
        orchestrator.is_ready = True
        orchestrator.is_live = True
        
        await orchestrator.graceful_shutdown(timeout=0.1)
        
        assert not orchestrator.is_ready
        assert not orchestrator.is_live
        assert orchestrator.shutdown_event.is_set()
        
    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self):
        """Test waiting for shutdown signal"""
        orchestrator = StartupOrchestrator()
        
        # Start waiting for shutdown in background
        wait_task = asyncio.create_task(orchestrator.wait_for_shutdown())
        
        # Give it a moment to start waiting
        await asyncio.sleep(0.01)
        
        # Signal shutdown
        orchestrator.shutdown_event.set()
        
        # Should complete quickly
        await asyncio.wait_for(wait_task, timeout=1.0)
        

class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_startup_orchestrator(self):
        """Test getting global orchestrator instance"""
        orchestrator = get_startup_orchestrator()
        
        assert isinstance(orchestrator, StartupOrchestrator)
        assert orchestrator is _orchestrator
        
    def test_register_startup_check_global(self):
        """Test registering check with global orchestrator"""
        initial_count = len(_orchestrator.checks)
        
        @register_startup_check(
            name="global_test_check",
            priority=100,
            timeout=5.0
        )
        async def global_test_check():
            return {"status": "ok"}
            
        assert len(_orchestrator.checks) == initial_count + 1
        assert "global_test_check" in _orchestrator.checks
        
    @pytest.mark.asyncio
    async def test_startup_agent_system(self):
        """Test startup_agent_system convenience function"""
        # Clear existing checks for predictable test
        original_checks = _orchestrator.checks.copy()
        _orchestrator.checks.clear()
        
        @register_startup_check("simple_check", priority=1, timeout=1.0)
        async def simple_check():
            return {"status": "ok"}
            
        try:
            metrics = await startup_agent_system()
            assert isinstance(metrics, StartupMetrics)
        finally:
            # Restore original checks
            _orchestrator.checks = original_checks
            
    @pytest.mark.asyncio
    async def test_check_functions(self):
        """Test check convenience functions"""
        readiness = await check_agent_readiness()
        assert isinstance(readiness, dict)
        assert "ready" in readiness
        
        liveness = await check_agent_liveness()
        assert isinstance(liveness, dict)
        assert "alive" in liveness
        
    def test_get_agent_startup_status(self):
        """Test get_agent_startup_status convenience function"""
        status = get_agent_startup_status()
        assert isinstance(status, dict)
        assert "ready" in status
        assert "live" in status
        

class TestManagedLifecycle:
    """Test managed agent lifecycle"""
    
    @pytest.mark.asyncio
    async def test_managed_agent_lifecycle_success(self):
        """Test successful managed agent lifecycle"""
        # Clear checks for simpler test
        original_checks = _orchestrator.checks.copy()
        _orchestrator.checks.clear()
        _orchestrator.results.clear()
        
        @register_startup_check("lifecycle_check", priority=1, timeout=1.0)
        async def lifecycle_check():
            return {"status": "ok"}
            
        try:
            async with managed_agent_lifecycle() as orchestrator:
                assert orchestrator.is_ready
                assert orchestrator.is_live
                
            # Should perform graceful shutdown
            assert not orchestrator.is_ready
            assert not orchestrator.is_live
        finally:
            # Restore original state
            _orchestrator.checks = original_checks
            
    @pytest.mark.asyncio
    async def test_managed_agent_lifecycle_failure(self):
        """Test managed agent lifecycle with startup failure"""
        original_checks = _orchestrator.checks.copy()
        _orchestrator.checks.clear()
        _orchestrator.results.clear()
        
        @register_startup_check("failing_check", priority=1, timeout=1.0)
        async def failing_check():
            raise RuntimeError("Startup failed")
            
        try:
            with pytest.raises(RuntimeError):
                async with managed_agent_lifecycle():
                    pass  # Should not reach here
        finally:
            _orchestrator.checks = original_checks
            

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_startup_workflow(self):
        """Test complete startup workflow"""
        orchestrator = StartupOrchestrator()
        orchestrator.checks.clear()
        
        # Create realistic startup checks
        database_ready = False
        
        @orchestrator.register_check(
            "database_connection",
            priority=1,
            timeout=5.0,
            phase=OrchestrationPhase.CONNECTION
        )
        async def check_database():
            nonlocal database_ready
            await asyncio.sleep(0.1)  # Simulate connection time
            database_ready = True
            return {"connection": "established", "host": "localhost"}
            
        @orchestrator.register_check(
            "data_migration",
            priority=2,
            timeout=10.0,
            depends_on=["database_connection"],
            phase=OrchestrationPhase.CONFIGURATION
        )
        async def check_migrations():
            if not database_ready:
                raise RuntimeError("Database not ready")
            await asyncio.sleep(0.05)
            return {"migrations": "up_to_date"}
            
        @orchestrator.register_check(
            "service_readiness",
            priority=3,
            timeout=5.0,
            depends_on=["data_migration"],
            phase=OrchestrationPhase.READINESS
        )
        async def check_service():
            await asyncio.sleep(0.02)
            return {"services": ["api", "worker"], "status": "ready"}
            
        # Execute startup
        metrics = await orchestrator.startup_sequence()
        
        # Verify results
        assert orchestrator.is_ready
        assert orchestrator.is_live
        assert metrics.success_count == 3
        assert metrics.failure_count == 0
        
        # Verify execution order was correct
        results = list(orchestrator.results.values())
        assert len(results) == 3
        
        # Database should be checked first
        db_result = orchestrator.results["database_connection"]
        assert db_result.status == StartupStatus.SUCCESS
        assert database_ready
        
        # Check health probes
        readiness = await orchestrator.check_readiness()
        assert readiness["ready"]
        
        liveness = await orchestrator.check_liveness()
        assert liveness["alive"]
        
        # Test graceful shutdown
        await orchestrator.graceful_shutdown()
        assert not orchestrator.is_ready
        assert not orchestrator.is_live
        

if __name__ == "__main__":
    pytest.main([__file__, "-v"])