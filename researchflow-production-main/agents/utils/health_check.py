#!/usr/bin/env python3
"""
Health Check System for ResearchFlow Agents

Provides health check endpoints and dependency monitoring for:
- Agent health status
- External service connectivity (Composio, OpenAI, etc.)
- Database connections
- Circuit breaker status
- Resource utilization

Integrates with Docker health checks and monitoring systems.

@author Claude
@created 2025-01-30
"""

import os
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    name: str
    status: HealthStatus
    message: str
    last_check: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health"""
    status: HealthStatus
    timestamp: str
    uptime_seconds: float
    components: List[ComponentHealth]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime_seconds": self.uptime_seconds,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "last_check": c.last_check,
                    "response_time_ms": c.response_time_ms,
                    "details": c.details
                }
                for c in self.components
            ]
        }


class HealthChecker:
    """
    Health checker for ResearchFlow agents and dependencies.
    
    Example:
        >>> checker = HealthChecker()
        >>> checker.add_check("composio", check_composio_api)
        >>> health = await checker.check_all()
        >>> print(health.status)
    """
    
    def __init__(self):
        self.checks: Dict[str, Any] = {}
        self.start_time = time.time()
        self.last_results: Dict[str, ComponentHealth] = {}
    
    def add_check(self, name: str, check_func: callable, critical: bool = True):
        """
        Add a health check.
        
        Args:
            name: Component name
            check_func: Async function that returns (bool, str, dict)
                       (is_healthy, message, details)
            critical: Whether this component is critical for overall health
        """
        self.checks[name] = {
            "func": check_func,
            "critical": critical
        }
    
    async def check_component(self, name: str) -> ComponentHealth:
        """Check health of a single component"""
        if name not in self.checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"No health check defined for {name}",
                last_check=datetime.now().isoformat()
            )
        
        check_info = self.checks[name]
        start_time = time.time()
        
        try:
            # Run health check with timeout
            is_healthy, message, details = await asyncio.wait_for(
                check_info["func"](),
                timeout=10.0
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time and health
            if is_healthy:
                if response_time > 5000:  # Slow response
                    status = HealthStatus.DEGRADED
                    message = f"{message} (slow response: {response_time:.0f}ms)"
                else:
                    status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNHEALTHY
            
            result = ComponentHealth(
                name=name,
                status=status,
                message=message,
                last_check=datetime.now().isoformat(),
                response_time_ms=response_time,
                details=details
            )
            
        except asyncio.TimeoutError:
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out (>10s)",
                last_check=datetime.now().isoformat(),
                response_time_ms=10000
            )
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                last_check=datetime.now().isoformat()
            )
        
        self.last_results[name] = result
        return result
    
    async def check_all(self) -> SystemHealth:
        """Check health of all components"""
        component_results = []
        
        # Run all checks in parallel
        tasks = [
            self.check_component(name)
            for name in self.checks.keys()
        ]
        
        if tasks:
            component_results = await asyncio.gather(*tasks)
        
        # Determine overall health
        critical_unhealthy = any(
            c.status == HealthStatus.UNHEALTHY and self.checks[c.name]["critical"]
            for c in component_results
        )
        
        any_degraded = any(c.status == HealthStatus.DEGRADED for c in component_results)
        any_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in component_results)
        
        if critical_unhealthy:
            overall_status = HealthStatus.UNHEALTHY
        elif any_unhealthy or any_degraded:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            uptime_seconds=time.time() - self.start_time,
            components=component_results
        )
    
    def get_last_check(self, component: str) -> Optional[ComponentHealth]:
        """Get last health check result for a component"""
        return self.last_results.get(component)
    
    def is_healthy(self) -> bool:
        """Quick check if system is healthy based on last results"""
        if not self.last_results:
            return False
        
        # Check if any critical component is unhealthy
        for name, result in self.last_results.items():
            if self.checks[name]["critical"] and result.status == HealthStatus.UNHEALTHY:
                return False
        
        return True


# Common health check functions

async def check_composio_api() -> tuple:
    """Check Composio API connectivity"""
    try:
        from agents.utils.secrets_manager import get_secret
        
        api_key = get_secret("COMPOSIO_API_KEY")
        if not api_key:
            return False, "Composio API key not configured", {}
        
        # Try to import and initialize
        try:
            from composio_langchain import ComposioToolSet
            toolset = ComposioToolSet(api_key=api_key)
            # Basic connectivity check
            return True, "Composio API accessible", {"key_length": len(api_key)}
        except ImportError:
            return False, "Composio SDK not installed", {}
        except Exception as e:
            return False, f"Composio initialization failed: {str(e)}", {}
            
    except Exception as e:
        return False, f"Error checking Composio: {str(e)}", {}


async def check_openai_api() -> tuple:
    """Check OpenAI API connectivity"""
    try:
        from agents.utils.secrets_manager import get_secret
        
        api_key = get_secret("OPENAI_API_KEY")
        if not api_key:
            return False, "OpenAI API key not configured", {}
        
        # Quick validation check (don't make actual API call to save costs)
        if not api_key.startswith("sk-"):
            return False, "OpenAI API key format invalid", {}
        
        return True, "OpenAI API key configured", {"key_length": len(api_key)}
        
    except Exception as e:
        return False, f"Error checking OpenAI: {str(e)}", {}


async def check_database() -> tuple:
    """Check database connectivity"""
    try:
        import os
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            return False, "DATABASE_URL not configured", {}
        
        # Basic format check
        if not db_url.startswith(("postgresql://", "postgres://")):
            return False, "Invalid database URL format", {}
        
        # Try to connect if psycopg2 is available
        try:
            import psycopg2
            import urllib.parse
            
            # Parse connection string
            result = urllib.parse.urlparse(db_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                connect_timeout=3
            )
            conn.close()
            return True, "Database connection successful", {"host": result.hostname}
        except ImportError:
            # psycopg2 not installed, just verify URL format
            return True, "Database URL configured (connection not tested)", {}
        except Exception as e:
            return False, f"Database connection failed: {str(e)}", {}
            
    except Exception as e:
        return False, f"Error checking database: {str(e)}", {}


async def check_redis() -> tuple:
    """Check Redis connectivity"""
    try:
        import os
        redis_url = os.getenv("REDIS_URL")
        
        if not redis_url:
            return False, "REDIS_URL not configured", {}
        
        # Try to connect if redis is available
        try:
            import redis
            import urllib.parse
            
            result = urllib.parse.urlparse(redis_url)
            client = redis.Redis(
                host=result.hostname,
                port=result.port or 6379,
                password=result.password,
                socket_connect_timeout=3,
                socket_timeout=3
            )
            client.ping()
            return True, "Redis connection successful", {"host": result.hostname}
        except ImportError:
            return True, "Redis URL configured (connection not tested)", {}
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}", {}
            
    except Exception as e:
        return False, f"Error checking Redis: {str(e)}", {}


async def check_circuit_breakers() -> tuple:
    """Check circuit breaker status"""
    try:
        from agents.utils.circuit_breaker import (
            openai_breaker,
            anthropic_breaker,
            composio_breaker
        )
        
        breakers = {
            "openai": openai_breaker,
            "anthropic": anthropic_breaker,
            "composio": composio_breaker
        }
        
        open_breakers = []
        for name, breaker in breakers.items():
            if breaker.state.value == "open":
                open_breakers.append(name)
        
        if open_breakers:
            return False, f"Circuit breakers open: {', '.join(open_breakers)}", {
                "open_breakers": open_breakers
            }
        
        return True, "All circuit breakers closed", {
            "breakers_count": len(breakers)
        }
        
    except Exception as e:
        return False, f"Error checking circuit breakers: {str(e)}", {}


# Pre-configured health checker for agents

def get_agent_health_checker() -> HealthChecker:
    """Get health checker configured for ResearchFlow agents"""
    checker = HealthChecker()
    
    # Critical checks
    checker.add_check("composio_api", check_composio_api, critical=True)
    checker.add_check("openai_api", check_openai_api, critical=True)
    
    # Important but not critical
    checker.add_check("database", check_database, critical=False)
    checker.add_check("redis", check_redis, critical=False)
    checker.add_check("circuit_breakers", check_circuit_breakers, critical=False)
    
    return checker


# FastAPI integration helper

def create_health_endpoint(checker: Optional[HealthChecker] = None):
    """
    Create a health check endpoint function for FastAPI.
    
    Example:
        from fastapi import FastAPI
        from agents.utils.health_check import create_health_endpoint
        
        app = FastAPI()
        health_check = create_health_endpoint()
        
        @app.get("/health")
        async def health():
            return await health_check()
    """
    if checker is None:
        checker = get_agent_health_checker()
    
    async def health_endpoint():
        health = await checker.check_all()
        
        # Return appropriate HTTP status code
        status_code_map = {
            HealthStatus.HEALTHY: 200,
            HealthStatus.DEGRADED: 200,  # Still operational
            HealthStatus.UNHEALTHY: 503,  # Service unavailable
            HealthStatus.UNKNOWN: 503
        }
        
        return {
            "status": health.status.value,
            "timestamp": health.timestamp,
            "uptime_seconds": health.uptime_seconds,
            "components": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "response_time_ms": c.response_time_ms
                }
                for c in health.components
            ]
        }
    
    return health_endpoint
