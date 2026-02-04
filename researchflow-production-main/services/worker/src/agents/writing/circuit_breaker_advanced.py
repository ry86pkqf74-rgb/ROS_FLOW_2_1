"""
Advanced Circuit Breaker Implementation for AI Bridge

Enterprise-grade circuit breaker with:
- Multiple failure detection strategies
- Adaptive thresholds
- Service health monitoring  
- Automatic recovery mechanisms
- Performance-based triggering

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import statistics
import json

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"    # Testing if service has recovered

class FailureType(Enum):
    """Types of failures that can trigger circuit breaker."""
    TIMEOUT = "timeout"
    ERROR_RESPONSE = "error_response"
    SLOW_RESPONSE = "slow_response"
    SERVICE_UNAVAILABLE = "service_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMIT = "rate_limit"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    # Basic thresholds
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout_seconds: int = 60  # Time before trying half-open
    success_threshold: int = 3          # Successes needed in half-open to close
    
    # Advanced thresholds
    slow_request_threshold_ms: int = 5000    # Requests slower than this count as failures
    error_rate_threshold: float = 0.5        # Error rate (0.0-1.0) that triggers opening
    min_requests_for_stats: int = 10         # Minimum requests before using error rate
    
    # Adaptive behavior
    adaptive_thresholds: bool = True         # Enable adaptive threshold adjustment
    max_failure_threshold: int = 20          # Maximum adaptive failure threshold
    min_failure_threshold: int = 3           # Minimum adaptive failure threshold
    
    # Performance monitoring
    performance_window_size: int = 100       # Number of recent requests to consider
    enable_performance_triggering: bool = True  # Trigger on performance degradation
    
    # Recovery behavior
    gradual_recovery: bool = True            # Gradually increase allowed traffic
    max_recovery_attempts: int = 5           # Maximum recovery attempts before extended timeout

@dataclass
class RequestResult:
    """Result of a request attempt."""
    timestamp: datetime
    success: bool
    duration_ms: float
    error_type: Optional[FailureType] = None
    error_message: Optional[str] = None
    response_size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type.value if self.error_type else None,
            "error_message": self.error_message,
            "response_size": self.response_size
        }

class AdvancedCircuitBreaker:
    """
    Advanced Circuit Breaker with multiple failure detection strategies.
    
    Features:
    - Multiple failure types detection
    - Adaptive threshold adjustment
    - Performance-based triggering
    - Gradual recovery
    - Health monitoring
    - Detailed metrics and reporting
    """
    
    def __init__(self, 
                 name: str,
                 config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # Circuit state
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.utcnow()
        
        # Failure tracking
        self.failure_count = 0
        self.success_count_in_half_open = 0
        self.consecutive_failures = 0
        
        # Request history
        self.request_history: deque = deque(maxlen=self.config.performance_window_size)
        
        # Adaptive thresholds
        self.current_failure_threshold = self.config.failure_threshold
        self.performance_baseline_ms: Optional[float] = None
        
        # Recovery tracking
        self.recovery_attempts = 0
        self.last_recovery_attempt = datetime.utcnow()
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_circuit_openings = 0
        
        logger.info(f"Advanced Circuit Breaker '{name}' initialized")
    
    async def call(self, 
                   func: Callable[..., Awaitable[Any]], 
                   *args,
                   timeout_seconds: float = 30.0,
                   **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Async function to call
            *args: Positional arguments for the function
            timeout_seconds: Request timeout
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result if successful
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Other exceptions from the underlying function
        """
        self.total_requests += 1
        
        # Check if circuit should be open
        if self.state == CircuitState.OPEN:
            if not self._should_attempt_reset():
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
            else:
                # Transition to half-open
                await self._transition_to_half_open()
        
        # Execute the request
        start_time = time.time()
        try:
            # Apply timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Record successful request
            await self._record_success(duration_ms, len(str(result)))
            
            return result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            await self._record_failure(duration_ms, FailureType.TIMEOUT, "Request timeout")
            raise
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            await self._record_failure(duration_ms, error_type, str(e))
            raise
    
    async def _record_success(self, duration_ms: float, response_size: int):
        """Record a successful request."""
        result = RequestResult(
            timestamp=datetime.utcnow(),
            success=True,
            duration_ms=duration_ms,
            response_size=response_size
        )
        self.request_history.append(result)
        
        # Handle success based on current state
        if self.state == CircuitState.HALF_OPEN:
            self.success_count_in_half_open += 1
            logger.debug(f"Circuit '{self.name}': Success in half-open ({self.success_count_in_half_open}/{self.config.success_threshold})")
            
            if self.success_count_in_half_open >= self.config.success_threshold:
                await self._transition_to_closed()
        
        # Reset consecutive failures on success
        self.consecutive_failures = 0
        
        # Update performance baseline
        await self._update_performance_baseline()
        
        # Adapt thresholds based on performance
        if self.config.adaptive_thresholds:
            await self._adapt_thresholds()
    
    async def _record_failure(self, duration_ms: float, error_type: FailureType, error_message: str):
        """Record a failed request."""
        self.total_failures += 1
        self.failure_count += 1
        self.consecutive_failures += 1
        
        result = RequestResult(
            timestamp=datetime.utcnow(),
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message
        )
        self.request_history.append(result)
        
        logger.warning(f"Circuit '{self.name}': Failure recorded - {error_type.value}: {error_message}")
        
        # Check if circuit should open
        if await self._should_open_circuit():
            await self._transition_to_open()
    
    def _classify_error(self, error: Exception) -> FailureType:
        """Classify the type of error."""
        error_msg = str(error).lower()
        
        if "timeout" in error_msg:
            return FailureType.TIMEOUT
        elif "quota" in error_msg or "limit" in error_msg:
            return FailureType.QUOTA_EXCEEDED
        elif "auth" in error_msg or "unauthorized" in error_msg:
            return FailureType.AUTHENTICATION_FAILED
        elif "rate" in error_msg and "limit" in error_msg:
            return FailureType.RATE_LIMIT
        elif "unavailable" in error_msg or "service" in error_msg:
            return FailureType.SERVICE_UNAVAILABLE
        else:
            return FailureType.ERROR_RESPONSE
    
    async def _should_open_circuit(self) -> bool:
        """Determine if the circuit should be opened."""
        # Check basic failure threshold
        if self.failure_count >= self.current_failure_threshold:
            logger.info(f"Circuit '{self.name}': Failure threshold reached ({self.failure_count}/{self.current_failure_threshold})")
            return True
        
        # Check error rate if we have enough requests
        if len(self.request_history) >= self.config.min_requests_for_stats:
            recent_requests = list(self.request_history)
            error_rate = sum(1 for r in recent_requests if not r.success) / len(recent_requests)
            
            if error_rate >= self.config.error_rate_threshold:
                logger.info(f"Circuit '{self.name}': Error rate threshold exceeded ({error_rate:.2f})")
                return True
        
        # Check performance degradation
        if self.config.enable_performance_triggering and self.performance_baseline_ms:
            recent_requests = [r for r in self.request_history if r.success]
            if recent_requests:
                avg_duration = statistics.mean([r.duration_ms for r in recent_requests[-10:]])
                if avg_duration > self.performance_baseline_ms * 3:  # 3x slower than baseline
                    logger.info(f"Circuit '{self.name}': Performance degradation detected ({avg_duration:.1f}ms vs {self.performance_baseline_ms:.1f}ms baseline)")
                    return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset (transition to half-open)."""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_open = datetime.utcnow() - self.last_state_change
        base_timeout = self.config.recovery_timeout_seconds
        
        # Exponential backoff for repeated failures
        timeout_multiplier = min(2 ** self.recovery_attempts, 16)  # Cap at 16x
        actual_timeout = base_timeout * timeout_multiplier
        
        return time_since_open.total_seconds() >= actual_timeout
    
    async def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.utcnow()
        self.total_circuit_openings += 1
        self.recovery_attempts += 1
        
        logger.warning(f"Circuit '{self.name}' OPENED after {self.failure_count} failures")
        
        # Reset failure count
        self.failure_count = 0
    
    async def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.utcnow()
        self.success_count_in_half_open = 0
        self.last_recovery_attempt = datetime.utcnow()
        
        logger.info(f"Circuit '{self.name}' transitioned to HALF_OPEN for recovery testing")
    
    async def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.utcnow()
        self.recovery_attempts = 0  # Reset recovery attempts on successful recovery
        
        logger.info(f"Circuit '{self.name}' CLOSED - service recovered")
    
    async def _update_performance_baseline(self):
        """Update performance baseline based on successful requests."""
        successful_requests = [r for r in self.request_history if r.success]
        
        if len(successful_requests) >= 20:  # Need enough data points
            recent_durations = [r.duration_ms for r in successful_requests[-20:]]
            new_baseline = statistics.median(recent_durations)
            
            if self.performance_baseline_ms is None:
                self.performance_baseline_ms = new_baseline
            else:
                # Gradually adjust baseline (moving average)
                self.performance_baseline_ms = (self.performance_baseline_ms * 0.8) + (new_baseline * 0.2)
    
    async def _adapt_thresholds(self):
        """Adapt failure thresholds based on recent performance."""
        if not self.config.adaptive_thresholds:
            return
        
        if len(self.request_history) < 50:  # Need sufficient history
            return
        
        recent_requests = list(self.request_history)[-50:]
        error_rate = sum(1 for r in recent_requests if not r.success) / len(recent_requests)
        
        # Adjust thresholds based on error patterns
        if error_rate < 0.1:  # Low error rate - can be more sensitive
            new_threshold = max(
                self.config.min_failure_threshold,
                self.current_failure_threshold - 1
            )
        elif error_rate > 0.3:  # High error rate - be more tolerant
            new_threshold = min(
                self.config.max_failure_threshold,
                self.current_failure_threshold + 2
            )
        else:
            return  # No adjustment needed
        
        if new_threshold != self.current_failure_threshold:
            logger.info(f"Circuit '{self.name}': Adapted failure threshold from {self.current_failure_threshold} to {new_threshold} (error rate: {error_rate:.2f})")
            self.current_failure_threshold = new_threshold
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state and statistics."""
        recent_requests = list(self.request_history)
        
        # Calculate statistics
        if recent_requests:
            successful_requests = [r for r in recent_requests if r.success]
            error_rate = (len(recent_requests) - len(successful_requests)) / len(recent_requests)
            
            if successful_requests:
                avg_duration = statistics.mean([r.duration_ms for r in successful_requests])
                p95_duration = statistics.quantiles([r.duration_ms for r in successful_requests], n=20)[18] if len(successful_requests) > 20 else avg_duration
            else:
                avg_duration = 0.0
                p95_duration = 0.0
        else:
            error_rate = 0.0
            avg_duration = 0.0
            p95_duration = 0.0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "last_state_change": self.last_state_change.isoformat(),
            "failure_count": self.failure_count,
            "current_failure_threshold": self.current_failure_threshold,
            "consecutive_failures": self.consecutive_failures,
            "recovery_attempts": self.recovery_attempts,
            "statistics": {
                "total_requests": self.total_requests,
                "total_failures": self.total_failures,
                "total_circuit_openings": self.total_circuit_openings,
                "recent_error_rate": error_rate,
                "recent_avg_duration_ms": avg_duration,
                "recent_p95_duration_ms": p95_duration,
                "request_history_size": len(recent_requests)
            },
            "performance": {
                "baseline_duration_ms": self.performance_baseline_ms,
                "adaptive_thresholds_enabled": self.config.adaptive_thresholds,
                "performance_triggering_enabled": self.config.enable_performance_triggering
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout_seconds": self.config.recovery_timeout_seconds,
                "success_threshold": self.config.success_threshold,
                "slow_request_threshold_ms": self.config.slow_request_threshold_ms,
                "error_rate_threshold": self.config.error_rate_threshold
            }
        }
    
    def get_health_score(self) -> float:
        """
        Calculate a health score (0.0 to 1.0) based on recent performance.
        
        Returns:
            float: Health score where 1.0 is perfect health, 0.0 is completely unhealthy
        """
        if not self.request_history:
            return 1.0  # No data means we assume healthy
        
        recent_requests = list(self.request_history)[-20:]  # Last 20 requests
        
        # Base score on success rate
        success_rate = sum(1 for r in recent_requests if r.success) / len(recent_requests)
        
        # Adjust for circuit state
        state_multiplier = {
            CircuitState.CLOSED: 1.0,
            CircuitState.HALF_OPEN: 0.5,
            CircuitState.OPEN: 0.0
        }
        
        # Adjust for performance
        performance_factor = 1.0
        if self.performance_baseline_ms:
            successful_requests = [r for r in recent_requests if r.success]
            if successful_requests:
                avg_duration = statistics.mean([r.duration_ms for r in successful_requests])
                if avg_duration > self.performance_baseline_ms * 2:  # 2x slower than baseline
                    performance_factor = 0.5
                elif avg_duration > self.performance_baseline_ms * 1.5:  # 1.5x slower
                    performance_factor = 0.7
        
        health_score = success_rate * state_multiplier[self.state] * performance_factor
        return max(0.0, min(1.0, health_score))

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass

class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, AdvancedCircuitBreaker] = {}
    
    def get_or_create_circuit_breaker(self, 
                                     name: str, 
                                     config: Optional[CircuitBreakerConfig] = None) -> AdvancedCircuitBreaker:
        """Get existing circuit breaker or create a new one."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = AdvancedCircuitBreaker(name, config)
        return self.circuit_breakers[name]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get states of all circuit breakers."""
        return {name: cb.get_state() for name, cb in self.circuit_breakers.items()}
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health summary of all circuit breakers."""
        if not self.circuit_breakers:
            return {"overall_health": 1.0, "status": "no_circuits"}
        
        health_scores = {name: cb.get_health_score() for name, cb in self.circuit_breakers.items()}
        overall_health = sum(health_scores.values()) / len(health_scores)
        
        return {
            "overall_health": overall_health,
            "individual_health": health_scores,
            "circuits_open": sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN),
            "circuits_half_open": sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.HALF_OPEN),
            "circuits_closed": sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.CLOSED),
            "status": "healthy" if overall_health > 0.8 else "degraded" if overall_health > 0.5 else "unhealthy"
        }

# Global circuit breaker manager
_circuit_manager: Optional[CircuitBreakerManager] = None

def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance."""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitBreakerManager()
    return _circuit_manager

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> AdvancedCircuitBreaker:
    """Get circuit breaker by name."""
    manager = get_circuit_breaker_manager()
    return manager.get_or_create_circuit_breaker(name, config)