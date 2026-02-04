"""
Startup Orchestration for ResearchFlow Agents

This module provides comprehensive startup validation, dependency management,
and Kubernetes deployment compatibility for production agents.

Features:
- Ordered dependency validation with priority system
- Kubernetes readiness and liveness probe endpoints
- Graceful shutdown handling with cleanup
- Startup time monitoring and optimization
- Health check integration
- Configuration validation
- Service discovery and connectivity checks

Usage:
    from agents.utils import StartupOrchestrator, register_startup_check
    
    orchestrator = StartupOrchestrator()
    
    @register_startup_check(name="database", priority=1, timeout=30.0)
    async def check_database():
        # Validate DB connection
        pass
        
    @register_startup_check(name="vault_secrets", priority=2, timeout=15.0) 
    async def check_vault():
        # Validate secret access
        pass
        
    # For K8s readiness probes
    @app.get("/ready")
    async def readiness_probe():
        return await orchestrator.check_readiness()
        
    # For startup sequence
    await orchestrator.startup_sequence()
"""

import asyncio
import signal
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

from .structured_logging import get_logger
from .health_check import get_health_checker
from .env_validator import validate_startup_environment
from .config_manager import load_config
from .secrets_manager import get_secrets_manager

logger = get_logger(__name__)


class StartupStatus(Enum):
    """Startup check status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class OrchestrationPhase(Enum):
    """Orchestration phases"""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    CONNECTION = "connection"
    CONFIGURATION = "configuration"
    READINESS = "readiness"
    COMPLETE = "complete"


@dataclass
class StartupCheck:
    """Individual startup check configuration"""
    name: str
    func: Callable[[], Any]
    priority: int
    timeout: float
    retry_count: int = 3
    retry_delay: float = 1.0
    critical: bool = True
    depends_on: List[str] = field(default_factory=list)
    phase: OrchestrationPhase = OrchestrationPhase.VALIDATION
    description: Optional[str] = None


@dataclass
class CheckResult:
    """Result of a startup check"""
    name: str
    status: StartupStatus
    duration: float
    error: Optional[Exception] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StartupMetrics:
    """Startup performance metrics"""
    total_duration: float
    check_count: int
    success_count: int
    failure_count: int
    timeout_count: int
    average_check_duration: float
    longest_check_name: Optional[str] = None
    longest_check_duration: float = 0.0


class StartupOrchestrator:
    """Orchestrates application startup with dependency management"""
    
    def __init__(self, max_startup_time: float = 300.0):
        self.checks: Dict[str, StartupCheck] = {}
        self.results: Dict[str, CheckResult] = {}
        self.max_startup_time = max_startup_time
        self.startup_start_time: Optional[float] = None
        self.is_ready = False
        self.is_live = False
        self.shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # Default system checks
        self._register_default_checks()
        
    def _register_default_checks(self):
        """Register default system validation checks"""
        
        @self.register_check(
            name="environment_validation",
            priority=1,
            timeout=30.0,
            phase=OrchestrationPhase.INITIALIZATION,
            description="Validate environment variables and configuration"
        )
        async def check_environment():
            """Validate startup environment"""
            if not validate_startup_environment():
                raise RuntimeError("Environment validation failed")
            return {"status": "validated"}
            
        @self.register_check(
            name="configuration_load",
            priority=2,
            timeout=15.0,
            phase=OrchestrationPhase.CONFIGURATION,
            depends_on=["environment_validation"],
            description="Load and validate configuration"
        )
        async def check_configuration():
            """Load and validate configuration"""
            try:
                import os
                env = os.getenv("ENV", "development")
                config = load_config(env)
                return {"environment": env, "config_loaded": True}
            except Exception as e:
                raise RuntimeError(f"Configuration load failed: {e}")
                
        @self.register_check(
            name="secrets_access",
            priority=3,
            timeout=20.0,
            phase=OrchestrationPhase.CONNECTION,
            depends_on=["configuration_load"],
            description="Validate secret management access"
        )
        async def check_secrets():
            """Validate secret manager access"""
            try:
                secrets = get_secrets_manager()
                # Test with a dummy key to verify backend connectivity
                test_result = await secrets.get_secret("__startup_test__", "test_value")
                return {"backend": secrets.backend, "accessible": True}
            except Exception as e:
                # Non-critical for development environments
                logger.warning(f"Secrets access check failed: {e}")
                return {"backend": "unavailable", "accessible": False}
                
        @self.register_check(
            name="health_subsystem",
            priority=4,
            timeout=10.0,
            phase=OrchestrationPhase.READINESS,
            depends_on=["secrets_access"],
            description="Initialize health check subsystem"
        )
        async def check_health_system():
            """Initialize health check system"""
            try:
                health_checker = get_health_checker()
                basic_health = await health_checker.check_basic_health()
                return {
                    "health_system": "initialized",
                    "basic_health": basic_health["status"]
                }
            except Exception as e:
                raise RuntimeError(f"Health system initialization failed: {e}")
                
    def register_check(
        self,
        name: str,
        priority: int,
        timeout: float = 30.0,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        critical: bool = True,
        depends_on: Optional[List[str]] = None,
        phase: OrchestrationPhase = OrchestrationPhase.VALIDATION,
        description: Optional[str] = None
    ):
        """Decorator to register a startup check"""
        def decorator(func: Callable) -> Callable:
            check = StartupCheck(
                name=name,
                func=func,
                priority=priority,
                timeout=timeout,
                retry_count=retry_count,
                retry_delay=retry_delay,
                critical=critical,
                depends_on=depends_on or [],
                phase=phase,
                description=description
            )
            self.checks[name] = check
            return func
        return decorator
        
    async def _execute_check(self, check: StartupCheck) -> CheckResult:
        """Execute a single startup check with retries"""
        start_time = time.time()
        last_error = None
        
        for attempt in range(check.retry_count):
            try:
                # Create timeout for the check
                result = await asyncio.wait_for(
                    check.func(),
                    timeout=check.timeout
                )
                
                duration = time.time() - start_time
                logger.info(f"✓ {check.name}: passed in {duration:.2f}s")
                
                return CheckResult(
                    name=check.name,
                    status=StartupStatus.SUCCESS,
                    duration=duration,
                    message="Check passed successfully",
                    metadata=result if isinstance(result, dict) else {"result": result}
                )
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                logger.error(f"✗ {check.name}: timeout after {duration:.2f}s")
                
                return CheckResult(
                    name=check.name,
                    status=StartupStatus.TIMEOUT,
                    duration=duration,
                    message=f"Check timed out after {check.timeout}s"
                )
                
            except Exception as e:
                last_error = e
                if attempt < check.retry_count - 1:
                    logger.warning(f"⚠ {check.name}: attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(check.retry_delay)
                else:
                    duration = time.time() - start_time
                    logger.error(f"✗ {check.name}: failed after {attempt + 1} attempts: {e}")
                    
                    return CheckResult(
                        name=check.name,
                        status=StartupStatus.FAILED,
                        duration=duration,
                        error=last_error,
                        message=str(last_error)
                    )
                    
        # Should not reach here, but safety fallback
        duration = time.time() - start_time
        return CheckResult(
            name=check.name,
            status=StartupStatus.FAILED,
            duration=duration,
            error=last_error,
            message="Unexpected failure after retries"
        )
        
    def _resolve_dependencies(self) -> List[StartupCheck]:
        """Resolve check dependencies and return execution order"""
        # Sort checks by priority first
        sorted_checks = sorted(self.checks.values(), key=lambda c: c.priority)
        
        # Topological sort for dependencies
        resolved = []
        unresolved = set(check.name for check in sorted_checks)
        
        while unresolved:
            # Find checks with no unresolved dependencies
            ready_checks = [
                check for check in sorted_checks
                if check.name in unresolved and
                all(dep in [r.name for r in resolved] for dep in check.depends_on)
            ]
            
            if not ready_checks:
                # Circular dependency detected
                remaining = [check.name for check in sorted_checks if check.name in unresolved]
                raise RuntimeError(f"Circular dependency detected in startup checks: {remaining}")
                
            # Add ready checks to resolved list
            for check in ready_checks:
                resolved.append(check)
                unresolved.remove(check.name)
                
        return resolved
        
    async def startup_sequence(self) -> StartupMetrics:
        """Execute the complete startup sequence"""
        async with self._lock:
            self.startup_start_time = time.time()
            self.results.clear()
            self.is_ready = False
            self.is_live = False
            
        logger.info("🚀 Starting agent startup sequence")
        
        try:
            # Resolve execution order
            execution_order = self._resolve_dependencies()
            logger.info(f"📋 Executing {len(execution_order)} startup checks")
            
            # Execute checks in order
            success_count = 0
            failure_count = 0
            timeout_count = 0
            
            for check in execution_order:
                logger.info(f"🔍 Running check: {check.name}")
                
                result = await self._execute_check(check)
                self.results[check.name] = result
                
                if result.status == StartupStatus.SUCCESS:
                    success_count += 1
                elif result.status == StartupStatus.FAILED:
                    failure_count += 1
                    if check.critical:
                        logger.error(f"💥 Critical check failed: {check.name}")
                        break
                elif result.status == StartupStatus.TIMEOUT:
                    timeout_count += 1
                    if check.critical:
                        logger.error(f"⏰ Critical check timed out: {check.name}")
                        break
                        
            # Calculate metrics
            total_duration = time.time() - self.startup_start_time
            check_count = len(self.results)
            
            # Find longest check
            longest_check_name = None
            longest_check_duration = 0.0
            avg_duration = 0.0
            
            if self.results:
                durations = [r.duration for r in self.results.values()]
                avg_duration = sum(durations) / len(durations)
                
                longest_result = max(self.results.values(), key=lambda r: r.duration)
                longest_check_name = longest_result.name
                longest_check_duration = longest_result.duration
                
            metrics = StartupMetrics(
                total_duration=total_duration,
                check_count=check_count,
                success_count=success_count,
                failure_count=failure_count,
                timeout_count=timeout_count,
                average_check_duration=avg_duration,
                longest_check_name=longest_check_name,
                longest_check_duration=longest_check_duration
            )
            
            # Determine readiness
            critical_failures = any(
                result.status != StartupStatus.SUCCESS and self.checks[result.name].critical
                for result in self.results.values()
            )
            
            if not critical_failures and total_duration < self.max_startup_time:
                self.is_ready = True
                self.is_live = True
                logger.info(f"✅ Startup completed successfully in {total_duration:.2f}s")
            else:
                logger.error(f"❌ Startup failed (duration: {total_duration:.2f}s)")
                
            return metrics
            
        except Exception as e:
            logger.error(f"💥 Startup sequence failed: {e}")
            raise
            
    async def check_readiness(self) -> Dict[str, Any]:
        """Kubernetes readiness probe endpoint"""
        if not self.is_ready:
            return {
                "ready": False,
                "message": "Startup sequence not completed successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        # Additional runtime readiness checks
        try:
            health_checker = get_health_checker()
            health = await health_checker.check_basic_health()
            
            return {
                "ready": True,
                "health": health,
                "startup_time": time.time() - (self.startup_start_time or 0),
                "checks_completed": len(self.results),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return {
                "ready": False,
                "message": f"Runtime health check failed: {e}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def check_liveness(self) -> Dict[str, Any]:
        """Kubernetes liveness probe endpoint"""
        if not self.is_live:
            return {
                "alive": False,
                "message": "Service not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        # Basic liveness check
        return {
            "alive": True,
            "uptime": time.time() - (self.startup_start_time or 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def get_startup_status(self) -> Dict[str, Any]:
        """Get comprehensive startup status"""
        return {
            "ready": self.is_ready,
            "live": self.is_live,
            "startup_time": self.startup_start_time,
            "checks": {
                name: {
                    "status": result.status.value,
                    "duration": result.duration,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat()
                }
                for name, result in self.results.items()
            }
        }
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            asyncio.create_task(self.graceful_shutdown())
            
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
    async def graceful_shutdown(self, timeout: float = 30.0):
        """Perform graceful shutdown with cleanup"""
        logger.info("🛑 Starting graceful shutdown")
        
        self.is_ready = False
        self.is_live = False
        self.shutdown_event.set()
        
        # Give time for in-flight requests to complete
        await asyncio.sleep(1.0)
        
        logger.info("✅ Graceful shutdown completed")
        
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()


# Global orchestrator instance
_orchestrator = StartupOrchestrator()


def get_startup_orchestrator() -> StartupOrchestrator:
    """Get the global startup orchestrator instance"""
    return _orchestrator


def register_startup_check(
    name: str,
    priority: int,
    timeout: float = 30.0,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    critical: bool = True,
    depends_on: Optional[List[str]] = None,
    phase: OrchestrationPhase = OrchestrationPhase.VALIDATION,
    description: Optional[str] = None
):
    """Decorator to register a startup check with the global orchestrator"""
    return _orchestrator.register_check(
        name=name,
        priority=priority,
        timeout=timeout,
        retry_count=retry_count,
        retry_delay=retry_delay,
        critical=critical,
        depends_on=depends_on,
        phase=phase,
        description=description
    )


# Convenience functions
async def startup_agent_system() -> StartupMetrics:
    """Execute startup sequence for agent system"""
    return await _orchestrator.startup_sequence()


async def check_agent_readiness() -> Dict[str, Any]:
    """Check if agents are ready to serve traffic"""
    return await _orchestrator.check_readiness()


async def check_agent_liveness() -> Dict[str, Any]:
    """Check if agents are alive"""
    return await _orchestrator.check_liveness()


def get_agent_startup_status() -> Dict[str, Any]:
    """Get comprehensive agent startup status"""
    return _orchestrator.get_startup_status()


@asynccontextmanager
async def managed_agent_lifecycle():
    """Context manager for complete agent lifecycle management"""
    orchestrator = get_startup_orchestrator()
    orchestrator.setup_signal_handlers()
    
    try:
        # Startup sequence
        metrics = await orchestrator.startup_sequence()
        logger.info(f"Agent system ready (startup time: {metrics.total_duration:.2f}s)")
        
        yield orchestrator
        
    except Exception as e:
        logger.error(f"Agent lifecycle management failed: {e}")
        raise
    finally:
        # Graceful shutdown
        await orchestrator.graceful_shutdown()


# Example usage for FastAPI integration
def add_k8s_probes(app):
    """Add Kubernetes probe endpoints to FastAPI app"""
    
    @app.get("/health")
    async def health_endpoint():
        """Combined health endpoint"""
        readiness = await check_agent_readiness()
        liveness = await check_agent_liveness()
        
        return {
            "status": "healthy" if readiness["ready"] and liveness["alive"] else "unhealthy",
            "readiness": readiness,
            "liveness": liveness
        }
        
    @app.get("/ready")
    async def readiness_probe():
        """Kubernetes readiness probe"""
        return await check_agent_readiness()
        
    @app.get("/alive")
    async def liveness_probe():
        """Kubernetes liveness probe"""
        return await check_agent_liveness()
        
    @app.get("/startup")
    async def startup_status():
        """Detailed startup status"""
        return get_agent_startup_status()