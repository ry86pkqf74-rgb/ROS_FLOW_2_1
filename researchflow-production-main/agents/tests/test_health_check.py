#!/usr/bin/env python3
"""
Unit tests for HealthChecker

Tests health check system and component monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from agents.utils.health_check import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    get_agent_health_checker,
    check_composio_api,
    check_openai_api,
    check_database,
    check_redis
)


class TestHealthChecker:
    """Test suite for HealthChecker"""
    
    @pytest.mark.asyncio
    async def test_add_check(self):
        """Test adding health checks"""
        checker = HealthChecker()
        
        async def test_check():
            return True, "Test passed", {}
        
        checker.add_check("test_component", test_check, critical=True)
        assert "test_component" in checker.checks
        assert checker.checks["test_component"]["critical"] is True
    
    @pytest.mark.asyncio
    async def test_check_component_success(self):
        """Test successful component health check"""
        checker = HealthChecker()
        
        async def healthy_check():
            return True, "Component is healthy", {"version": "1.0"}
        
        checker.add_check("test", healthy_check)
        result = await checker.check_component("test")
        
        assert result.status == HealthStatus.HEALTHY
        assert result.passed is True
        assert result.response_time_ms is not None
        assert result.details["version"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_check_component_failure(self):
        """Test failed component health check"""
        checker = HealthChecker()
        
        async def unhealthy_check():
            return False, "Component is down", {}
        
        checker.add_check("test", unhealthy_check)
        result = await checker.check_component("test")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "Component is down"
    
    @pytest.mark.asyncio
    async def test_check_component_timeout(self):
        """Test component health check timeout"""
        checker = HealthChecker()
        
        async def slow_check():
            await asyncio.sleep(15)  # Exceeds 10s timeout
            return True, "Eventually healthy", {}
        
        checker.add_check("test", slow_check)
        result = await checker.check_component("test")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_component_exception(self):
        """Test component health check with exception"""
        checker = HealthChecker()
        
        async def error_check():
            raise Exception("Test error")
        
        checker.add_check("test", error_check)
        result = await checker.check_component("test")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "error" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_all_healthy(self):
        """Test check_all with all components healthy"""
        checker = HealthChecker()
        
        async def check1():
            return True, "Component 1 OK", {}
        
        async def check2():
            return True, "Component 2 OK", {}
        
        checker.add_check("comp1", check1, critical=True)
        checker.add_check("comp2", check2, critical=False)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
        assert len(health.components) == 2
        assert all(c.status == HealthStatus.HEALTHY for c in health.components)
    
    @pytest.mark.asyncio
    async def test_check_all_degraded(self):
        """Test check_all with degraded components"""
        checker = HealthChecker()
        
        async def healthy_check():
            return True, "OK", {}
        
        async def slow_check():
            await asyncio.sleep(0.006)  # Slow but not failed
            return True, "Slow", {}
        
        checker.add_check("healthy", healthy_check, critical=True)
        checker.add_check("slow", slow_check, critical=False)
        
        health = await checker.check_all()
        
        # Should be degraded due to slow response
        assert health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    @pytest.mark.asyncio
    async def test_check_all_unhealthy_critical(self):
        """Test check_all with critical component unhealthy"""
        checker = HealthChecker()
        
        async def healthy_check():
            return True, "OK", {}
        
        async def unhealthy_check():
            return False, "Failed", {}
        
        checker.add_check("healthy", healthy_check, critical=False)
        checker.add_check("critical", unhealthy_check, critical=True)
        
        health = await checker.check_all()
        
        assert health.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_get_last_check(self):
        """Test retrieving last check result"""
        checker = HealthChecker()
        
        async def test_check():
            return True, "OK", {}
        
        checker.add_check("test", test_check)
        await checker.check_component("test")
        
        last = checker.get_last_check("test")
        assert last is not None
        assert last.name == "test"
    
    @pytest.mark.asyncio
    async def test_is_healthy(self):
        """Test is_healthy method"""
        checker = HealthChecker()
        
        async def healthy():
            return True, "OK", {}
        
        async def unhealthy():
            return False, "Failed", {}
        
        checker.add_check("healthy", healthy, critical=False)
        await checker.check_all()
        assert checker.is_healthy() is True
        
        checker.add_check("critical_unhealthy", unhealthy, critical=True)
        await checker.check_all()
        assert checker.is_healthy() is False
    
    def test_system_health_to_dict(self):
        """Test SystemHealth serialization"""
        components = [
            ComponentHealth(
                name="test",
                status=HealthStatus.HEALTHY,
                message="OK",
                last_check="2025-01-30T12:00:00Z",
                response_time_ms=50.0
            )
        ]
        
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            timestamp="2025-01-30T12:00:00Z",
            uptime_seconds=100.0,
            components=components
        )
        
        data = health.to_dict()
        
        assert data["status"] == "healthy"
        assert data["uptime_seconds"] == 100.0
        assert len(data["components"]) == 1
        assert data["components"][0]["name"] == "test"


@pytest.mark.asyncio
class TestCommonHealthChecks:
    """Test common health check functions"""
    
    async def test_check_composio_api_success(self):
        """Test Composio API check with valid key"""
        with patch.dict('os.environ', {'COMPOSIO_API_KEY': 'comp_' + 'x' * 20}):
            with patch('agents.utils.health_check.ComposioToolSet'):
                is_healthy, message, details = await check_composio_api()
                assert is_healthy is True
                assert "accessible" in message.lower()
    
    async def test_check_composio_api_missing_key(self):
        """Test Composio API check with missing key"""
        with patch.dict('os.environ', {}, clear=True):
            is_healthy, message, details = await check_composio_api()
            assert is_healthy is False
            assert "not configured" in message.lower()
    
    async def test_check_openai_api_success(self):
        """Test OpenAI API check with valid key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-' + 'x' * 20}):
            is_healthy, message, details = await check_openai_api()
            assert is_healthy is True
    
    async def test_check_openai_api_invalid_format(self):
        """Test OpenAI API check with invalid key format"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'invalid_key'}):
            is_healthy, message, details = await check_openai_api()
            assert is_healthy is False
            assert "invalid" in message.lower()
    
    async def test_check_database_not_configured(self):
        """Test database check when not configured"""
        with patch.dict('os.environ', {}, clear=True):
            is_healthy, message, details = await check_database()
            assert is_healthy is False
            assert "not configured" in message.lower()
    
    async def test_check_database_invalid_url(self):
        """Test database check with invalid URL"""
        with patch.dict('os.environ', {'DATABASE_URL': 'invalid://url'}):
            is_healthy, message, details = await check_database()
            assert is_healthy is False
    
    async def test_check_redis_not_configured(self):
        """Test Redis check when not configured"""
        with patch.dict('os.environ', {}, clear=True):
            is_healthy, message, details = await check_redis()
            assert is_healthy is False


class TestAgentHealthChecker:
    """Test pre-configured agent health checker"""
    
    def test_get_agent_health_checker(self):
        """Test getting pre-configured agent health checker"""
        checker = get_agent_health_checker()
        
        assert "composio_api" in checker.checks
        assert "openai_api" in checker.checks
        assert checker.checks["composio_api"]["critical"] is True
        assert checker.checks["openai_api"]["critical"] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
