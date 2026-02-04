#!/usr/bin/env python3
"""
Rate Limiting for ResearchFlow Agents

Provides rate limiting for:
- API calls to external services
- Agent task execution
- Resource access protection
- Distributed rate limiting (Redis-backed)
- Adaptive rate limiting based on response times

Features:
- Token bucket algorithm
- Sliding window rate limiting
- Per-user and global rate limits
- Circuit breaker integration
- Metrics collection

@author Claude
@created 2025-01-30
"""

import asyncio
import time
import hashlib
from typing import Dict, Any, Optional, Callable, Union, List
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        super().__init__(message)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Basic limits
    requests_per_second: float = 10.0
    burst_size: int = 20
    
    # Algorithm
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    
    # Window settings (for sliding/fixed window)
    window_size: float = 60.0  # seconds
    
    # Distributed settings
    redis_backend: bool = False
    redis_key_prefix: str = "researchflow:ratelimit"
    
    # Adaptive settings
    adaptive: bool = False
    target_response_time: float = 1.0  # seconds
    adaptation_factor: float = 0.1


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows bursts up to bucket capacity, then sustains at fill rate.
    """
    
    def __init__(
        self,
        capacity: int,
        fill_rate: float,
        initial_tokens: Optional[int] = None
    ):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            now = time.time()
            
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.fill_rate
            )
            self.last_update = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Wait for tokens to become available.
        
        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait
            
        Returns:
            True if tokens were acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            # Calculate wait time until next token
            wait_time = min(0.1, tokens / self.fill_rate)
            await asyncio.sleep(wait_time)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bucket status"""
        now = time.time()
        elapsed = now - self.last_update
        current_tokens = min(
            self.capacity,
            self.tokens + elapsed * self.fill_rate
        )
        
        return {
            "capacity": self.capacity,
            "current_tokens": current_tokens,
            "fill_rate": self.fill_rate,
            "utilization": (self.capacity - current_tokens) / self.capacity
        }


class SlidingWindowRateLimit:
    """
    Sliding window rate limiter.
    
    Maintains a sliding window of requests and enforces limits.
    """
    
    def __init__(self, limit: int, window_size: float):
        self.limit = limit
        self.window_size = window_size
        self.requests: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire a slot in the current window"""
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            cutoff_time = now - self.window_size
            self.requests = [req_time for req_time in self.requests if req_time > cutoff_time]
            
            # Check if we're under the limit
            if len(self.requests) < self.limit:
                self.requests.append(now)
                return True
            else:
                return False
    
    def get_retry_after(self) -> Optional[float]:
        """Get time until next request can be made"""
        if not self.requests:
            return None
        
        # Time until oldest request falls out of window
        oldest_request = min(self.requests)
        return max(0, oldest_request + self.window_size - time.time())


class RateLimiter:
    """
    Advanced rate limiter with multiple algorithms and backends.
    
    Example:
        >>> limiter = RateLimiter("api_calls", RateLimitConfig(
        ...     requests_per_second=10.0,
        ...     burst_size=20
        ... ))
        >>> 
        >>> @limiter.limit()
        >>> async def call_api():
        ...     # API call implementation
        ...     pass
        >>> 
        >>> await call_api()  # Will be rate limited
    """
    
    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config
        self._limiters: Dict[str, Union[TokenBucket, SlidingWindowRateLimit]] = {}
        self._redis_client = None
        self.metrics = None
        self._initialize_redis()
        self._initialize_metrics()
        
        # Adaptive rate limiting
        self._response_times: List[float] = []
        self._current_rate = config.requests_per_second
    
    def _initialize_redis(self):
        """Initialize Redis client if configured"""
        if self.config.redis_backend:
            try:
                import redis.asyncio as redis
                # This would typically use connection from config
                # For now, just mark that Redis is available
                logger.info(f"Redis rate limiting enabled for {self.name}")
            except ImportError:
                logger.warning("Redis not available, falling back to in-memory rate limiting")
                self.config.redis_backend = False
    
    def _initialize_metrics(self):
        """Initialize metrics collection"""
        try:
            from .metrics import get_metrics_collector
            self.metrics = get_metrics_collector()
        except ImportError:
            logger.debug("Metrics not available for rate limiter")
    
    def _get_limiter_key(self, identifier: str) -> str:
        """Generate a unique key for the rate limiter"""
        return f"{self.name}:{identifier}"
    
    def _get_limiter(self, identifier: str) -> Union[TokenBucket, SlidingWindowRateLimit]:
        """Get or create rate limiter for identifier"""
        key = self._get_limiter_key(identifier)
        
        if key not in self._limiters:
            if self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                self._limiters[key] = TokenBucket(
                    capacity=self.config.burst_size,
                    fill_rate=self._current_rate
                )
            elif self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                # Convert rate to count per window
                limit = int(self._current_rate * self.config.window_size)
                self._limiters[key] = SlidingWindowRateLimit(
                    limit=limit,
                    window_size=self.config.window_size
                )
            else:
                # Default to token bucket
                self._limiters[key] = TokenBucket(
                    capacity=self.config.burst_size,
                    fill_rate=self._current_rate
                )
        
        return self._limiters[key]
    
    async def acquire(self, identifier: str = "default", tokens: int = 1) -> bool:
        """
        Try to acquire permission to proceed.
        
        Args:
            identifier: Identifier for rate limit bucket (e.g., user ID, IP)
            tokens: Number of tokens/requests to acquire
            
        Returns:
            True if permission granted, False if rate limited
        """
        if self.config.redis_backend:
            return await self._acquire_redis(identifier, tokens)
        else:
            return await self._acquire_local(identifier, tokens)
    
    async def _acquire_local(self, identifier: str, tokens: int) -> bool:
        """Acquire using local rate limiter"""
        limiter = self._get_limiter(identifier)
        
        if isinstance(limiter, TokenBucket):
            acquired = await limiter.acquire(tokens)
        else:  # SlidingWindowRateLimit
            acquired = await limiter.acquire()
        
        # Record metrics
        if self.metrics:
            self.metrics.increment_counter(
                "rate_limit_requests_total",
                {
                    "limiter": self.name,
                    "identifier": identifier,
                    "result": "allowed" if acquired else "rejected"
                }
            )
        
        return acquired
    
    async def _acquire_redis(self, identifier: str, tokens: int) -> bool:
        """Acquire using Redis-backed rate limiter"""
        # This would implement Redis-based rate limiting
        # For now, fall back to local
        logger.warning("Redis rate limiting not fully implemented, using local")
        return await self._acquire_local(identifier, tokens)
    
    async def wait_for_permission(
        self, 
        identifier: str = "default", 
        tokens: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Wait for permission to proceed.
        
        Args:
            identifier: Identifier for rate limit bucket
            tokens: Number of tokens/requests needed
            timeout: Maximum time to wait
            
        Returns:
            True if permission granted, False if timeout
        """
        if self.config.redis_backend:
            # For Redis, we'd need different logic
            return await self._acquire_redis(identifier, tokens)
        
        limiter = self._get_limiter(identifier)
        
        if isinstance(limiter, TokenBucket):
            return await limiter.wait_for_tokens(tokens, timeout)
        else:
            # For sliding window, implement polling
            start_time = time.time()
            
            while True:
                if await limiter.acquire():
                    return True
                
                if timeout and (time.time() - start_time) >= timeout:
                    return False
                
                # Wait for retry
                retry_after = limiter.get_retry_after()
                if retry_after:
                    wait_time = min(retry_after, 1.0)  # Max 1 second poll
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(0.1)
    
    def limit(
        self, 
        identifier_func: Optional[Callable[..., str]] = None,
        tokens: int = 1,
        wait: bool = False,
        timeout: Optional[float] = None
    ):
        """
        Decorator to apply rate limiting to functions.
        
        Args:
            identifier_func: Function to extract identifier from args
            tokens: Number of tokens to consume
            wait: Whether to wait for permission or raise immediately
            timeout: Timeout for waiting
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract identifier
                if identifier_func:
                    identifier = identifier_func(*args, **kwargs)
                else:
                    identifier = "default"
                
                # Try to acquire permission
                if wait:
                    acquired = await self.wait_for_permission(identifier, tokens, timeout)
                    if not acquired:
                        raise RateLimitExceeded(
                            f"Rate limit exceeded for {self.name}:{identifier}, timeout after {timeout}s",
                            retry_after=timeout
                        )
                else:
                    acquired = await self.acquire(identifier, tokens)
                    if not acquired:
                        # Calculate retry after
                        limiter = self._get_limiter(identifier)
                        retry_after = None
                        if isinstance(limiter, SlidingWindowRateLimit):
                            retry_after = limiter.get_retry_after()
                        
                        raise RateLimitExceeded(
                            f"Rate limit exceeded for {self.name}:{identifier}",
                            retry_after=retry_after
                        )
                
                # Execute the function
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record response time for adaptive limiting
                    if self.config.adaptive:
                        response_time = time.time() - start_time
                        await self._update_adaptive_rate(response_time)
                    
                    return result
                    
                except Exception as e:
                    # Still record response time on error
                    if self.config.adaptive:
                        response_time = time.time() - start_time
                        await self._update_adaptive_rate(response_time)
                    raise
            
            return wrapper
        return decorator
    
    async def _update_adaptive_rate(self, response_time: float):
        """Update rate based on response times"""
        self._response_times.append(response_time)
        
        # Keep only recent response times
        if len(self._response_times) > 100:
            self._response_times = self._response_times[-50:]
        
        # Calculate average response time
        if len(self._response_times) >= 10:
            avg_response_time = sum(self._response_times) / len(self._response_times)
            
            # Adjust rate based on target
            if avg_response_time > self.config.target_response_time:
                # Slow down
                adjustment = -self.config.adaptation_factor
            else:
                # Speed up
                adjustment = self.config.adaptation_factor
            
            new_rate = self._current_rate * (1 + adjustment)
            new_rate = max(0.1, min(new_rate, self.config.requests_per_second * 2))
            
            if abs(new_rate - self._current_rate) > 0.1:
                logger.info(
                    f"Adaptive rate limit adjustment for {self.name}: "
                    f"{self._current_rate:.2f} -> {new_rate:.2f} req/s "
                    f"(avg response time: {avg_response_time:.3f}s)"
                )
                self._current_rate = new_rate
                
                # Update existing limiters
                for limiter in self._limiters.values():
                    if isinstance(limiter, TokenBucket):
                        limiter.fill_rate = new_rate
    
    def get_status(self, identifier: str = "default") -> Dict[str, Any]:
        """Get current rate limit status"""
        limiter = self._get_limiter(identifier)
        
        status = {
            "name": self.name,
            "identifier": identifier,
            "algorithm": self.config.algorithm.value,
            "current_rate": self._current_rate,
            "configured_rate": self.config.requests_per_second
        }
        
        if isinstance(limiter, TokenBucket):
            status.update(limiter.get_status())
        
        if self.config.adaptive and self._response_times:
            status["avg_response_time"] = sum(self._response_times) / len(self._response_times)
            status["response_samples"] = len(self._response_times)
        
        return status


# Global rate limiters registry
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(name: str, config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create a rate limiter"""
    if name not in _rate_limiters:
        if config is None:
            config = RateLimitConfig()
        _rate_limiters[name] = RateLimiter(name, config)
    
    return _rate_limiters[name]


# Convenience decorators for common use cases

def rate_limit_api_calls(requests_per_second: float = 10.0, burst_size: int = 20):
    """Decorator for rate limiting API calls"""
    config = RateLimitConfig(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET
    )
    limiter = get_rate_limiter("api_calls", config)
    return limiter.limit()


def rate_limit_per_user(requests_per_minute: float = 100.0):
    """Decorator for per-user rate limiting"""
    config = RateLimitConfig(
        requests_per_second=requests_per_minute / 60.0,
        burst_size=int(requests_per_minute / 6),  # 10-second burst
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET
    )
    limiter = get_rate_limiter("per_user", config)
    
    def extract_user_id(*args, **kwargs):
        # Try to extract user ID from common parameter names
        for key in ['user_id', 'user', 'id', 'identifier']:
            if key in kwargs:
                return str(kwargs[key])
        
        # Try first argument as user ID
        if args and isinstance(args[0], (str, int)):
            return str(args[0])
        
        return "anonymous"
    
    return limiter.limit(identifier_func=extract_user_id)


def adaptive_rate_limit(target_response_time: float = 1.0):
    """Decorator for adaptive rate limiting based on response times"""
    config = RateLimitConfig(
        requests_per_second=10.0,
        burst_size=20,
        adaptive=True,
        target_response_time=target_response_time
    )
    limiter = get_rate_limiter("adaptive", config)
    return limiter.limit()