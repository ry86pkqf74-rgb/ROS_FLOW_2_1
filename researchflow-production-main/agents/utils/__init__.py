#!/usr/bin/env python3
"""
ResearchFlow Agent Utilities

Common utilities for agent operations including:
- Circuit breakers for external API resilience
- FAISS vector database client
- Model timeout configuration
- Secrets management (Vault, AWS, Azure)
- AI helper for external AI service integration
- Environment validation
- Health checks
- Structured logging
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    circuit_breaker,
    # Pre-configured breakers
    openai_breaker,
    anthropic_breaker,
    composio_breaker,
    faiss_breaker,
    github_breaker,
    notion_breaker,
)

from .faiss_client import (
    FAISSClient,
    FAISSConfig,
    VectorSearchResult,
    get_faiss_client,
)

from .model_config import (
    ModelTimeoutConfig,
    get_model_timeout,
    DEFAULT_TIMEOUTS,
)

from .secrets_manager import (
    SecretsManager,
    SecretBackend,
    SecretConfig,
    get_secrets_manager,
    get_secret,
    get_required_secret,
    validate_required_secrets,
)

from .ai_helper import (
    AIHelper,
    AIProvider,
    AIResponse,
    get_ai_helper,
)

from .env_validator import (
    EnvValidator,
    ValidationRule,
    ValidationSeverity,
    ValidationResult,
    get_agent_validator,
    get_service_validator,
    validate_startup_environment,
    # Common validators
    is_url,
    is_postgres_url,
    is_redis_url,
    is_positive_int,
    is_boolean,
    is_api_key,
)

from .health_check import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    get_agent_health_checker,
    create_health_endpoint,
    # Common checks
    check_composio_api,
    check_openai_api,
    check_database,
    check_redis,
    check_circuit_breakers,
)

from .structured_logging import (
    StructuredFormatter,
    setup_structured_logging,
    get_logger,
    get_agent_logger,
    LogContext,
    log_execution_time,
    log_async_execution_time,
    MetricsLogger,
)

from .metrics import (
    MetricsCollector,
    MetricType,
    MetricConfig,
    get_metrics_collector,
    track_agent_task,
    track_api_call,
    create_metrics_endpoint,
)

from .advanced_health import (
    AdvancedHealthChecker,
    ResourceUsage,
    get_advanced_health_checker,
)

from .config_manager import (
    ConfigManager,
    ResearchFlowConfig,
    Environment,
    get_config_manager,
    load_config,
    get_config,
)

from .retry import (
    RetryManager,
    RetryPolicy,
    RetryResult,
    BackoffStrategy,
    RetryableError,
    get_retry_manager,
    retry_api_call,
    retry_database_operation,
    retry_file_operation,
)

from .timeout import (
    TimeoutManager,
    TimeoutConfig,
    TimeoutError,
    get_timeout_manager,
    timeout_api_call,
    timeout_database_operation,
    timeout_file_operation,
    timeout_workflow_step,
    timeout_long_operation,
    timeout_after,
    timeout_after_sync,
)

from .performance import (
    PerformanceTester,
    BenchmarkResult,
    LoadTestConfig,
    ResourceSnapshot,
    get_performance_tester,
    benchmark,
    load_test,
)

from .rate_limiting import (
    RateLimiter,
    RateLimitConfig,
    RateLimitAlgorithm,
    RateLimitExceeded,
    TokenBucket,
    SlidingWindowRateLimit,
    get_rate_limiter,
    rate_limit_api_calls,
    rate_limit_per_user,
    adaptive_rate_limit,
)

from .error_tracking import (
    ErrorTracker,
    ErrorStats,
    SpanContext,
    TraceContext,
    initialize_error_tracking,
    track_error,
    create_span,
    get_error_stats,
    manual_track_error,
    get_active_traces,
    clear_old_errors,
    get_error_tracker,
    check_error_health,
)

from .startup_orchestrator import (
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
    add_k8s_probes,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "circuit_breaker",
    "openai_breaker",
    "anthropic_breaker",
    "composio_breaker",
    "faiss_breaker",
    "github_breaker",
    "notion_breaker",
    # FAISS Client
    "FAISSClient",
    "FAISSConfig",
    "VectorSearchResult",
    "get_faiss_client",
    # Model Config
    "ModelTimeoutConfig",
    "get_model_timeout",
    "DEFAULT_TIMEOUTS",
    # Secrets Management
    "SecretsManager",
    "SecretBackend",
    "SecretConfig",
    "get_secrets_manager",
    "get_secret",
    "get_required_secret",
    "validate_required_secrets",
    # AI Helper
    "AIHelper",
    "AIProvider",
    "AIResponse",
    "get_ai_helper",
    # Environment Validation
    "EnvValidator",
    "ValidationRule",
    "ValidationSeverity",
    "ValidationResult",
    "get_agent_validator",
    "get_service_validator",
    "validate_startup_environment",
    "is_url",
    "is_postgres_url",
    "is_redis_url",
    "is_positive_int",
    "is_boolean",
    "is_api_key",
    # Health Checks
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "get_agent_health_checker",
    "create_health_endpoint",
    "check_composio_api",
    "check_openai_api",
    "check_database",
    "check_redis",
    "check_circuit_breakers",
    # Structured Logging
    "StructuredFormatter",
    "setup_structured_logging",
    "get_logger",
    "get_agent_logger",
    "LogContext",
    "log_execution_time",
    "log_async_execution_time",
    "MetricsLogger",
    # Metrics Collection
    "MetricsCollector",
    "MetricType",
    "MetricConfig",
    "get_metrics_collector",
    "track_agent_task",
    "track_api_call",
    "create_metrics_endpoint",
    # Advanced Health Checks
    "AdvancedHealthChecker",
    "ResourceUsage",
    "get_advanced_health_checker",
    # Configuration Management
    "ConfigManager",
    "ResearchFlowConfig",
    "Environment",
    "get_config_manager",
    "load_config",
    "get_config",
    # Retry Logic
    "RetryManager",
    "RetryPolicy",
    "RetryResult",
    "BackoffStrategy",
    "RetryableError",
    "get_retry_manager",
    "retry_api_call",
    "retry_database_operation",
    "retry_file_operation",
    # Timeout Protection
    "TimeoutManager",
    "TimeoutConfig",
    "TimeoutError",
    "get_timeout_manager",
    "timeout_api_call",
    "timeout_database_operation",
    "timeout_file_operation",
    "timeout_workflow_step",
    "timeout_long_operation",
    "timeout_after",
    "timeout_after_sync",
    # Performance Testing
    "PerformanceTester",
    "BenchmarkResult",
    "LoadTestConfig",
    "ResourceSnapshot",
    "get_performance_tester",
    "benchmark",
    "load_test",
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitAlgorithm",
    "RateLimitExceeded",
    "TokenBucket",
    "SlidingWindowRateLimit",
    "get_rate_limiter",
    "rate_limit_api_calls",
    "rate_limit_per_user",
    "adaptive_rate_limit",
    # Error Tracking & APM
    "ErrorTracker",
    "ErrorStats",
    "SpanContext",
    "TraceContext",
    "initialize_error_tracking",
    "track_error",
    "create_span",
    "get_error_stats",
    "manual_track_error",
    "get_active_traces",
    "clear_old_errors",
    "get_error_tracker",
    "check_error_health",
    # Startup Orchestration
    "StartupOrchestrator",
    "StartupCheck",
    "CheckResult",
    "StartupMetrics",
    "StartupStatus",
    "OrchestrationPhase",
    "get_startup_orchestrator",
    "register_startup_check",
    "startup_agent_system",
    "check_agent_readiness",
    "check_agent_liveness",
    "get_agent_startup_status",
    "managed_agent_lifecycle",
    "add_k8s_probes",
]
