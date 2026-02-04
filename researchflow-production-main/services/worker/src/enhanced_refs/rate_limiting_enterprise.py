"""
Enterprise Rate Limiting System for AI Bridge

Advanced rate limiting with:
- Multi-tier rate limiting (per second, minute, hour, day)
- Dynamic rate adjustment based on system load
- Cost-based rate limiting
- Organization-level quotas
- API endpoint-specific limits
- Burst handling and token bucket algorithm
- Redis-backed distributed rate limiting

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
from collections import defaultdict, deque
import math

logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Types of rate limits."""
    REQUEST_COUNT = "request_count"      # Number of requests
    TOKEN_COUNT = "token_count"         # Number of tokens consumed
    COST_BASED = "cost_based"           # USD cost consumed
    COMPUTE_TIME = "compute_time"       # Processing time consumed
    DATA_VOLUME = "data_volume"         # Data volume processed

class RateLimitScope(Enum):
    """Rate limit scopes."""
    USER = "user"                       # Per user
    ORGANIZATION = "organization"       # Per organization
    API_KEY = "api_key"                # Per API key
    ENDPOINT = "endpoint"              # Per API endpoint
    GLOBAL = "global"                  # System-wide

class RateLimitPeriod(Enum):
    """Rate limit time periods."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"

@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""
    name: str
    limit_type: RateLimitType
    scope: RateLimitScope
    period: RateLimitPeriod
    limit: int
    
    # Advanced configuration
    burst_limit: Optional[int] = None    # Allow bursts up to this limit
    refill_rate: Optional[int] = None    # Tokens refilled per second
    cost_multiplier: float = 1.0         # Cost calculation multiplier
    
    # Dynamic adjustment
    dynamic_adjustment: bool = False     # Enable dynamic limit adjustment
    min_limit: Optional[int] = None      # Minimum limit during adjustment
    max_limit: Optional[int] = None      # Maximum limit during adjustment
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)  # Additional conditions
    priority: int = 100                  # Priority for rule application (lower = higher priority)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "limit_type": self.limit_type.value,
            "scope": self.scope.value,
            "period": self.period.value,
            "limit": self.limit,
            "burst_limit": self.burst_limit,
            "refill_rate": self.refill_rate,
            "cost_multiplier": self.cost_multiplier,
            "dynamic_adjustment": self.dynamic_adjustment,
            "min_limit": self.min_limit,
            "max_limit": self.max_limit,
            "conditions": self.conditions,
            "priority": self.priority
        }

@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None
    
    # Additional information
    limit_type: RateLimitType = RateLimitType.REQUEST_COUNT
    scope: RateLimitScope = RateLimitScope.USER
    rule_name: str = "default"
    
    # Cost information
    cost_consumed: float = 0.0
    cost_remaining: float = 0.0
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        return {
            "X-RateLimit-Limit": str(self.remaining + (0 if self.allowed else 1)),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time.timestamp())),
            "X-RateLimit-Type": self.limit_type.value,
            "X-RateLimit-Scope": self.scope.value,
            "X-RateLimit-Rule": self.rule_name,
            **({"Retry-After": str(self.retry_after)} if self.retry_after else {})
        }

class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: int, initial_tokens: Optional[int] = None):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        if elapsed > 0:
            tokens_to_add = int(elapsed * self.refill_rate)
            if tokens_to_add > 0:
                self.tokens = min(self.capacity, self.tokens + tokens_to_add)
                self.last_refill = now
    
    def get_tokens(self) -> int:
        """Get current token count."""
        self._refill()
        return self.tokens
    
    def time_to_refill(self, needed_tokens: int) -> float:
        """Calculate time until enough tokens are available."""
        self._refill()
        
        if self.tokens >= needed_tokens:
            return 0.0
        
        tokens_needed = needed_tokens - self.tokens
        return tokens_needed / self.refill_rate

class EnterpriseRateLimiter:
    """
    Enterprise-grade rate limiting system with multiple strategies.
    
    Features:
    - Multiple rate limiting algorithms (token bucket, sliding window)
    - Multi-tier rate limits (per second, minute, hour, day)
    - Cost-based and usage-based limiting
    - Dynamic limit adjustment
    - Distributed rate limiting with Redis
    - Burst handling
    - Organization-level quotas
    """
    
    def __init__(self, 
                 redis_url: Optional[str] = None,
                 enable_distributed: bool = True):
        self.enable_distributed = enable_distributed
        
        # Redis connection for distributed rate limiting
        self.redis_client: Optional[redis.Redis] = None
        if redis_url and enable_distributed:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Redis connection established for distributed rate limiting")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.enable_distributed = False
        
        # Rate limit rules
        self.rules: List[RateLimitConfig] = []
        
        # In-memory rate limiting (fallback)
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.usage_counters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # System load tracking for dynamic adjustment
        self.system_load_history: deque = deque(maxlen=60)  # Last 60 data points
        self.current_system_load = 0.0
        
        # Initialize default rules
        self._setup_default_rules()
        
        logger.info("Enterprise Rate Limiter initialized")
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules."""
        default_rules = [
            # User-level request limits
            RateLimitConfig(
                name="user_requests_per_minute",
                limit_type=RateLimitType.REQUEST_COUNT,
                scope=RateLimitScope.USER,
                period=RateLimitPeriod.MINUTE,
                limit=60,
                burst_limit=100,
                refill_rate=1,
                dynamic_adjustment=True,
                min_limit=10,
                max_limit=200,
                priority=100
            ),
            RateLimitConfig(
                name="user_requests_per_hour",
                limit_type=RateLimitType.REQUEST_COUNT,
                scope=RateLimitScope.USER,
                period=RateLimitPeriod.HOUR,
                limit=1000,
                burst_limit=1500,
                dynamic_adjustment=True,
                min_limit=100,
                max_limit=5000,
                priority=90
            ),
            
            # Cost-based limits
            RateLimitConfig(
                name="user_daily_cost_limit",
                limit_type=RateLimitType.COST_BASED,
                scope=RateLimitScope.USER,
                period=RateLimitPeriod.DAY,
                limit=10,  # $10 USD per day
                priority=80
            ),
            
            # Organization limits
            RateLimitConfig(
                name="org_hourly_requests",
                limit_type=RateLimitType.REQUEST_COUNT,
                scope=RateLimitScope.ORGANIZATION,
                period=RateLimitPeriod.HOUR,
                limit=10000,
                dynamic_adjustment=True,
                min_limit=1000,
                max_limit=50000,
                priority=70
            ),
            
            # Global system limits
            RateLimitConfig(
                name="global_requests_per_second",
                limit_type=RateLimitType.REQUEST_COUNT,
                scope=RateLimitScope.GLOBAL,
                period=RateLimitPeriod.SECOND,
                limit=1000,
                burst_limit=2000,
                refill_rate=1000,
                dynamic_adjustment=True,
                min_limit=500,
                max_limit=5000,
                priority=60
            )
        ]
        
        self.rules.extend(default_rules)
    
    def add_rule(self, rule: RateLimitConfig):
        """Add a new rate limiting rule."""
        self.rules.append(rule)
        # Sort rules by priority (lower number = higher priority)
        self.rules.sort(key=lambda r: r.priority)
        logger.info(f"Rate limiting rule added: {rule.name}")
    
    async def check_rate_limit(self,
                              user_id: str,
                              organization_id: Optional[str] = None,
                              endpoint: Optional[str] = None,
                              api_key_id: Optional[str] = None,
                              request_cost: float = 0.0,
                              token_count: int = 0,
                              data_volume: int = 0) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Args:
            user_id: User identifier
            organization_id: Organization identifier  
            endpoint: API endpoint being called
            api_key_id: API key identifier
            request_cost: Estimated cost of request in USD
            token_count: Number of tokens to be consumed
            data_volume: Data volume to be processed
            
        Returns:
            RateLimitResult with decision and metadata
        """
        try:
            # Apply rules in priority order
            for rule in self.rules:
                result = await self._check_rule(
                    rule, user_id, organization_id, endpoint, api_key_id,
                    request_cost, token_count, data_volume
                )
                
                if not result.allowed:
                    logger.warning(f"Rate limit exceeded for rule '{rule.name}': {user_id}")
                    return result
            
            # All rules passed - consume resources
            await self._consume_resources(
                user_id, organization_id, endpoint, api_key_id,
                request_cost, token_count, data_volume
            )
            
            # Return success result
            return RateLimitResult(
                allowed=True,
                remaining=9999,  # TODO: Calculate actual remaining
                reset_time=datetime.utcnow() + timedelta(minutes=1)
            )
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open - allow request but log error
            return RateLimitResult(
                allowed=True,
                remaining=0,
                reset_time=datetime.utcnow() + timedelta(minutes=1),
                rule_name="error_fallback"
            )
    
    async def _check_rule(self,
                         rule: RateLimitConfig,
                         user_id: str,
                         organization_id: Optional[str],
                         endpoint: Optional[str],
                         api_key_id: Optional[str],
                         request_cost: float,
                         token_count: int,
                         data_volume: int) -> RateLimitResult:
        """Check a specific rate limiting rule."""
        
        # Determine the key for this rule
        key = self._get_rate_limit_key(rule, user_id, organization_id, endpoint, api_key_id)
        
        # Get current usage
        current_usage = await self._get_current_usage(rule, key)
        
        # Calculate effective limit (with dynamic adjustment)
        effective_limit = await self._calculate_effective_limit(rule)
        
        # Determine consumption amount
        consumption = self._calculate_consumption(rule, request_cost, token_count, data_volume)
        
        # Check if request would exceed limit
        if current_usage + consumption > effective_limit:
            # Check burst allowance
            if rule.burst_limit and current_usage + consumption <= rule.burst_limit:
                # Within burst limit - use token bucket if available
                if rule.refill_rate:
                    bucket = self._get_token_bucket(key, rule)
                    if bucket.consume(consumption):
                        return RateLimitResult(
                            allowed=True,
                            remaining=max(0, effective_limit - current_usage - consumption),
                            reset_time=self._calculate_reset_time(rule),
                            limit_type=rule.limit_type,
                            scope=rule.scope,
                            rule_name=rule.name
                        )
            
            # Exceeded limit
            retry_after = await self._calculate_retry_after(rule, key, consumption)
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=self._calculate_reset_time(rule),
                retry_after=retry_after,
                limit_type=rule.limit_type,
                scope=rule.scope,
                rule_name=rule.name
            )
        
        # Within limit
        return RateLimitResult(
            allowed=True,
            remaining=max(0, effective_limit - current_usage - consumption),
            reset_time=self._calculate_reset_time(rule),
            limit_type=rule.limit_type,
            scope=rule.scope,
            rule_name=rule.name
        )
    
    def _get_rate_limit_key(self,
                           rule: RateLimitConfig,
                           user_id: str,
                           organization_id: Optional[str],
                           endpoint: Optional[str],
                           api_key_id: Optional[str]) -> str:
        """Generate rate limit key for rule."""
        
        scope_parts = []
        
        if rule.scope == RateLimitScope.USER:
            scope_parts.append(f"user:{user_id}")
        elif rule.scope == RateLimitScope.ORGANIZATION and organization_id:
            scope_parts.append(f"org:{organization_id}")
        elif rule.scope == RateLimitScope.API_KEY and api_key_id:
            scope_parts.append(f"key:{api_key_id}")
        elif rule.scope == RateLimitScope.ENDPOINT and endpoint:
            scope_parts.append(f"endpoint:{endpoint}")
        elif rule.scope == RateLimitScope.GLOBAL:
            scope_parts.append("global")
        
        # Add time window
        now = datetime.utcnow()
        time_window = self._get_time_window(now, rule.period)
        
        key_parts = [
            "rate_limit",
            rule.name,
            ":".join(scope_parts),
            rule.limit_type.value,
            time_window
        ]
        
        return ":".join(key_parts)
    
    def _get_time_window(self, dt: datetime, period: RateLimitPeriod) -> str:
        """Get time window string for period."""
        if period == RateLimitPeriod.SECOND:
            return dt.strftime("%Y-%m-%d-%H-%M-%S")
        elif period == RateLimitPeriod.MINUTE:
            return dt.strftime("%Y-%m-%d-%H-%M")
        elif period == RateLimitPeriod.HOUR:
            return dt.strftime("%Y-%m-%d-%H")
        elif period == RateLimitPeriod.DAY:
            return dt.strftime("%Y-%m-%d")
        elif period == RateLimitPeriod.MONTH:
            return dt.strftime("%Y-%m")
        else:
            return dt.strftime("%Y-%m-%d-%H-%M")
    
    async def _get_current_usage(self, rule: RateLimitConfig, key: str) -> int:
        """Get current usage for rate limit key."""
        try:
            if self.enable_distributed and self.redis_client:
                # Use Redis for distributed rate limiting
                usage = await self.redis_client.get(key)
                return int(usage) if usage else 0
            else:
                # Use in-memory tracking
                return self.usage_counters.get(key, {}).get("usage", 0)
        except Exception as e:
            logger.error(f"Error getting current usage: {e}")
            return 0
    
    async def _calculate_effective_limit(self, rule: RateLimitConfig) -> int:
        """Calculate effective limit with dynamic adjustment."""
        base_limit = rule.limit
        
        if not rule.dynamic_adjustment:
            return base_limit
        
        # Dynamic adjustment based on system load
        load_factor = await self._get_system_load_factor()
        
        # Adjust limit based on load (higher load = lower limits)
        if load_factor > 0.8:  # High load
            adjustment_factor = 0.5
        elif load_factor > 0.6:  # Medium-high load
            adjustment_factor = 0.7
        elif load_factor < 0.3:  # Low load
            adjustment_factor = 1.3
        elif load_factor < 0.5:  # Medium-low load
            adjustment_factor = 1.1
        else:  # Normal load
            adjustment_factor = 1.0
        
        adjusted_limit = int(base_limit * adjustment_factor)
        
        # Apply min/max constraints
        if rule.min_limit:
            adjusted_limit = max(adjusted_limit, rule.min_limit)
        if rule.max_limit:
            adjusted_limit = min(adjusted_limit, rule.max_limit)
        
        return adjusted_limit
    
    async def _get_system_load_factor(self) -> float:
        """Get system load factor (0.0 to 1.0)."""
        try:
            import psutil
            
            # Calculate composite load factor
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
            memory_percent = psutil.virtual_memory().percent / 100.0
            
            # Weight CPU more heavily for API services
            load_factor = (cpu_percent * 0.7) + (memory_percent * 0.3)
            
            # Update history
            self.system_load_history.append(load_factor)
            
            # Return smoothed average of recent load
            if len(self.system_load_history) > 5:
                recent_loads = list(self.system_load_history)[-5:]
                return sum(recent_loads) / len(recent_loads)
            
            return load_factor
            
        except Exception as e:
            logger.error(f"Error calculating system load: {e}")
            return 0.5  # Default to medium load
    
    def _calculate_consumption(self,
                              rule: RateLimitConfig,
                              request_cost: float,
                              token_count: int,
                              data_volume: int) -> int:
        """Calculate consumption amount for rule type."""
        
        if rule.limit_type == RateLimitType.REQUEST_COUNT:
            return 1
        elif rule.limit_type == RateLimitType.TOKEN_COUNT:
            return token_count
        elif rule.limit_type == RateLimitType.COST_BASED:
            return int(request_cost * rule.cost_multiplier * 100)  # Convert to cents
        elif rule.limit_type == RateLimitType.DATA_VOLUME:
            return data_volume
        else:
            return 1
    
    def _get_token_bucket(self, key: str, rule: RateLimitConfig) -> TokenBucket:
        """Get or create token bucket for key."""
        if key not in self.token_buckets:
            capacity = rule.burst_limit or rule.limit
            refill_rate = rule.refill_rate or (rule.limit // 60)  # Default to limit per minute
            
            self.token_buckets[key] = TokenBucket(capacity, refill_rate)
        
        return self.token_buckets[key]
    
    def _calculate_reset_time(self, rule: RateLimitConfig) -> datetime:
        """Calculate when rate limit resets."""
        now = datetime.utcnow()
        
        if rule.period == RateLimitPeriod.SECOND:
            return now.replace(microsecond=0) + timedelta(seconds=1)
        elif rule.period == RateLimitPeriod.MINUTE:
            return now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        elif rule.period == RateLimitPeriod.HOUR:
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif rule.period == RateLimitPeriod.DAY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif rule.period == RateLimitPeriod.MONTH:
            # Next month's first day
            if now.month == 12:
                return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return now + timedelta(minutes=1)
    
    async def _calculate_retry_after(self, rule: RateLimitConfig, key: str, consumption: int) -> Optional[int]:
        """Calculate retry-after seconds."""
        if rule.refill_rate:
            bucket = self._get_token_bucket(key, rule)
            return int(math.ceil(bucket.time_to_refill(consumption)))
        
        # Default retry after based on period
        period_seconds = {
            RateLimitPeriod.SECOND: 1,
            RateLimitPeriod.MINUTE: 60,
            RateLimitPeriod.HOUR: 3600,
            RateLimitPeriod.DAY: 86400,
            RateLimitPeriod.MONTH: 86400 * 30
        }
        
        return period_seconds.get(rule.period, 60)
    
    async def _consume_resources(self,
                                user_id: str,
                                organization_id: Optional[str],
                                endpoint: Optional[str],
                                api_key_id: Optional[str],
                                request_cost: float,
                                token_count: int,
                                data_volume: int):
        """Consume resources for successful requests."""
        
        for rule in self.rules:
            key = self._get_rate_limit_key(rule, user_id, organization_id, endpoint, api_key_id)
            consumption = self._calculate_consumption(rule, request_cost, token_count, data_volume)
            
            try:
                if self.enable_distributed and self.redis_client:
                    # Atomic increment in Redis with expiration
                    ttl = self._get_period_seconds(rule.period)
                    await self.redis_client.incrby(key, consumption)
                    await self.redis_client.expire(key, ttl)
                else:
                    # In-memory tracking
                    if key not in self.usage_counters:
                        self.usage_counters[key] = {"usage": 0, "expires": self._calculate_reset_time(rule)}
                    
                    # Clean expired entries
                    if datetime.utcnow() > self.usage_counters[key]["expires"]:
                        self.usage_counters[key] = {"usage": 0, "expires": self._calculate_reset_time(rule)}
                    
                    self.usage_counters[key]["usage"] += consumption
                    
            except Exception as e:
                logger.error(f"Error consuming resources for rule {rule.name}: {e}")
    
    def _get_period_seconds(self, period: RateLimitPeriod) -> int:
        """Get period duration in seconds."""
        return {
            RateLimitPeriod.SECOND: 1,
            RateLimitPeriod.MINUTE: 60,
            RateLimitPeriod.HOUR: 3600,
            RateLimitPeriod.DAY: 86400,
            RateLimitPeriod.MONTH: 86400 * 30
        }.get(period, 60)
    
    async def get_rate_limit_status(self, user_id: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limit status for user/organization."""
        try:
            status = {
                "user_id": user_id,
                "organization_id": organization_id,
                "timestamp": datetime.utcnow().isoformat(),
                "rules": []
            }
            
            for rule in self.rules:
                key = self._get_rate_limit_key(rule, user_id, organization_id, None, None)
                current_usage = await self._get_current_usage(rule, key)
                effective_limit = await self._calculate_effective_limit(rule)
                
                rule_status = {
                    "name": rule.name,
                    "type": rule.limit_type.value,
                    "scope": rule.scope.value,
                    "period": rule.period.value,
                    "limit": effective_limit,
                    "used": current_usage,
                    "remaining": max(0, effective_limit - current_usage),
                    "percentage_used": (current_usage / effective_limit) * 100 if effective_limit > 0 else 0,
                    "reset_time": self._calculate_reset_time(rule).isoformat()
                }
                
                # Add burst info if applicable
                if rule.burst_limit:
                    rule_status["burst_limit"] = rule.burst_limit
                    if rule.refill_rate:
                        bucket = self._get_token_bucket(key, rule)
                        rule_status["burst_tokens"] = bucket.get_tokens()
                
                status["rules"].append(rule_status)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def reset_rate_limits(self, user_id: str, organization_id: Optional[str] = None) -> bool:
        """Reset rate limits for user/organization (admin function)."""
        try:
            reset_count = 0
            
            for rule in self.rules:
                key = self._get_rate_limit_key(rule, user_id, organization_id, None, None)
                
                if self.enable_distributed and self.redis_client:
                    await self.redis_client.delete(key)
                else:
                    if key in self.usage_counters:
                        del self.usage_counters[key]
                    if key in self.token_buckets:
                        del self.token_buckets[key]
                
                reset_count += 1
            
            logger.info(f"Reset {reset_count} rate limits for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limits: {e}")
            return False

# Global rate limiter instance
_rate_limiter: Optional[EnterpriseRateLimiter] = None

def get_rate_limiter() -> EnterpriseRateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = EnterpriseRateLimiter()
    return _rate_limiter