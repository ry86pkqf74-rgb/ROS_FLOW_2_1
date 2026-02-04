"""
Analytics Configuration Management
=================================

Configuration management for analytics system including:
- Environment variables
- Default settings
- Feature flags
- Performance tuning
- Security settings
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    max_connections: int = 20
    min_connections: int = 5
    command_timeout: int = 30
    retention_days: int = 90
    batch_size: int = 1000
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            url=os.getenv("ANALYTICS_DATABASE_URL", "postgresql://localhost/researchflow_analytics"),
            max_connections=int(os.getenv("ANALYTICS_DB_MAX_CONNECTIONS", "20")),
            min_connections=int(os.getenv("ANALYTICS_DB_MIN_CONNECTIONS", "5")),
            command_timeout=int(os.getenv("ANALYTICS_DB_TIMEOUT", "30")),
            retention_days=int(os.getenv("ANALYTICS_RETENTION_DAYS", "90")),
            batch_size=int(os.getenv("ANALYTICS_DB_BATCH_SIZE", "1000"))
        )


@dataclass
class MonitoringConfig:
    """Monitoring system configuration."""
    enabled: bool = True
    metrics_interval: float = 5.0
    max_history_points: int = 1000
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> 'MonitoringConfig':
        # Default alert thresholds
        default_thresholds = {
            "cpu_usage_high": 80.0,
            "memory_usage_high": 85.0,
            "disk_usage_high": 90.0,
            "error_rate_high": 5.0,
            "response_time_high": 10.0,
            "queue_length_high": 100
        }
        
        # Override with environment variables
        alert_thresholds = default_thresholds.copy()
        for key in default_thresholds:
            env_key = f"ANALYTICS_THRESHOLD_{key.upper()}"
            if os.getenv(env_key):
                try:
                    alert_thresholds[key] = float(os.getenv(env_key))
                except ValueError:
                    logger.warning(f"Invalid threshold value for {env_key}")
        
        return cls(
            enabled=os.getenv("ANALYTICS_MONITORING_ENABLED", "true").lower() == "true",
            metrics_interval=float(os.getenv("ANALYTICS_METRICS_INTERVAL", "5.0")),
            max_history_points=int(os.getenv("ANALYTICS_MAX_HISTORY_POINTS", "1000")),
            alert_thresholds=alert_thresholds
        )


@dataclass
class PredictorConfig:
    """Size predictor configuration."""
    model_path: str
    auto_retrain: bool = True
    retrain_threshold: int = 100
    confidence_threshold: float = 0.7
    ensemble_enabled: bool = True
    ab_testing_enabled: bool = False
    anomaly_detection_enabled: bool = True
    feature_selection: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> 'PredictorConfig':
        default_features = [
            "word_count", "reference_count", "figure_count", "table_count",
            "complexity_score", "citation_density", "content_type_multiplier"
        ]
        
        feature_list = os.getenv("ANALYTICS_PREDICTOR_FEATURES")
        if feature_list:
            features = [f.strip() for f in feature_list.split(",")]
        else:
            features = default_features
        
        return cls(
            model_path=os.getenv("ANALYTICS_MODEL_PATH", "/app/models/analytics"),
            auto_retrain=os.getenv("ANALYTICS_AUTO_RETRAIN", "true").lower() == "true",
            retrain_threshold=int(os.getenv("ANALYTICS_RETRAIN_THRESHOLD", "100")),
            confidence_threshold=float(os.getenv("ANALYTICS_CONFIDENCE_THRESHOLD", "0.7")),
            ensemble_enabled=os.getenv("ANALYTICS_ENSEMBLE_ENABLED", "true").lower() == "true",
            ab_testing_enabled=os.getenv("ANALYTICS_AB_TESTING_ENABLED", "false").lower() == "true",
            anomaly_detection_enabled=os.getenv("ANALYTICS_ANOMALY_DETECTION_ENABLED", "true").lower() == "true",
            feature_selection=features
        )


@dataclass
class WebSocketConfig:
    """WebSocket service configuration."""
    enabled: bool = True
    max_connections: int = 1000
    rate_limit_messages: int = 100
    rate_limit_window: int = 60
    ping_interval: int = 30
    broadcast_interval: float = 5.0
    cleanup_interval: int = 60
    message_queue_size: int = 1000
    
    @classmethod
    def from_env(cls) -> 'WebSocketConfig':
        return cls(
            enabled=os.getenv("ANALYTICS_WEBSOCKET_ENABLED", "true").lower() == "true",
            max_connections=int(os.getenv("ANALYTICS_WEBSOCKET_MAX_CONNECTIONS", "1000")),
            rate_limit_messages=int(os.getenv("ANALYTICS_WEBSOCKET_RATE_LIMIT_MESSAGES", "100")),
            rate_limit_window=int(os.getenv("ANALYTICS_WEBSOCKET_RATE_LIMIT_WINDOW", "60")),
            ping_interval=int(os.getenv("ANALYTICS_WEBSOCKET_PING_INTERVAL", "30")),
            broadcast_interval=float(os.getenv("ANALYTICS_WEBSOCKET_BROADCAST_INTERVAL", "5.0")),
            cleanup_interval=int(os.getenv("ANALYTICS_WEBSOCKET_CLEANUP_INTERVAL", "60")),
            message_queue_size=int(os.getenv("ANALYTICS_WEBSOCKET_QUEUE_SIZE", "1000"))
        )


@dataclass
class SecurityConfig:
    """Security configuration."""
    authentication_enabled: bool = False
    jwt_secret: Optional[str] = None
    allowed_origins: List[str] = field(default_factory=list)
    rate_limiting_enabled: bool = True
    encryption_enabled: bool = False
    audit_logging: bool = True
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        origins = os.getenv("ANALYTICS_ALLOWED_ORIGINS", "*")
        if origins == "*":
            allowed_origins = ["*"]
        else:
            allowed_origins = [origin.strip() for origin in origins.split(",")]
        
        return cls(
            authentication_enabled=os.getenv("ANALYTICS_AUTH_ENABLED", "false").lower() == "true",
            jwt_secret=os.getenv("ANALYTICS_JWT_SECRET"),
            allowed_origins=allowed_origins,
            rate_limiting_enabled=os.getenv("ANALYTICS_RATE_LIMITING", "true").lower() == "true",
            encryption_enabled=os.getenv("ANALYTICS_ENCRYPTION_ENABLED", "false").lower() == "true",
            audit_logging=os.getenv("ANALYTICS_AUDIT_LOGGING", "true").lower() == "true"
        )


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""
    cache_enabled: bool = True
    cache_ttl: int = 300
    compression_enabled: bool = True
    batch_processing: bool = True
    async_processing: bool = True
    connection_pooling: bool = True
    query_optimization: bool = True
    
    @classmethod
    def from_env(cls) -> 'PerformanceConfig':
        return cls(
            cache_enabled=os.getenv("ANALYTICS_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=int(os.getenv("ANALYTICS_CACHE_TTL", "300")),
            compression_enabled=os.getenv("ANALYTICS_COMPRESSION_ENABLED", "true").lower() == "true",
            batch_processing=os.getenv("ANALYTICS_BATCH_PROCESSING", "true").lower() == "true",
            async_processing=os.getenv("ANALYTICS_ASYNC_PROCESSING", "true").lower() == "true",
            connection_pooling=os.getenv("ANALYTICS_CONNECTION_POOLING", "true").lower() == "true",
            query_optimization=os.getenv("ANALYTICS_QUERY_OPTIMIZATION", "true").lower() == "true"
        )


@dataclass
class FeatureFlags:
    """Feature flags for analytics system."""
    advanced_predictor: bool = True
    real_time_websocket: bool = True
    database_persistence: bool = True
    anomaly_detection: bool = True
    ab_testing: bool = False
    auto_scaling: bool = False
    ml_monitoring: bool = True
    export_functionality: bool = True
    
    @classmethod
    def from_env(cls) -> 'FeatureFlags':
        return cls(
            advanced_predictor=os.getenv("ANALYTICS_FEATURE_ADVANCED_PREDICTOR", "true").lower() == "true",
            real_time_websocket=os.getenv("ANALYTICS_FEATURE_REAL_TIME_WEBSOCKET", "true").lower() == "true",
            database_persistence=os.getenv("ANALYTICS_FEATURE_DATABASE_PERSISTENCE", "true").lower() == "true",
            anomaly_detection=os.getenv("ANALYTICS_FEATURE_ANOMALY_DETECTION", "true").lower() == "true",
            ab_testing=os.getenv("ANALYTICS_FEATURE_AB_TESTING", "false").lower() == "true",
            auto_scaling=os.getenv("ANALYTICS_FEATURE_AUTO_SCALING", "false").lower() == "true",
            ml_monitoring=os.getenv("ANALYTICS_FEATURE_ML_MONITORING", "true").lower() == "true",
            export_functionality=os.getenv("ANALYTICS_FEATURE_EXPORT", "true").lower() == "true"
        )


@dataclass
class AnalyticsConfig:
    """Main analytics configuration."""
    database: DatabaseConfig
    monitoring: MonitoringConfig
    predictor: PredictorConfig
    websocket: WebSocketConfig
    security: SecurityConfig
    performance: PerformanceConfig
    features: FeatureFlags
    
    debug: bool = False
    log_level: str = "INFO"
    environment: str = "development"
    
    @classmethod
    def from_env(cls) -> 'AnalyticsConfig':
        return cls(
            database=DatabaseConfig.from_env(),
            monitoring=MonitoringConfig.from_env(),
            predictor=PredictorConfig.from_env(),
            websocket=WebSocketConfig.from_env(),
            security=SecurityConfig.from_env(),
            performance=PerformanceConfig.from_env(),
            features=FeatureFlags.from_env(),
            debug=os.getenv("ANALYTICS_DEBUG", "false").lower() == "true",
            log_level=os.getenv("ANALYTICS_LOG_LEVEL", "INFO").upper(),
            environment=os.getenv("ANALYTICS_ENVIRONMENT", "development")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "database": {
                "url": "***hidden***",  # Don't expose DB URL
                "max_connections": self.database.max_connections,
                "min_connections": self.database.min_connections,
                "command_timeout": self.database.command_timeout,
                "retention_days": self.database.retention_days,
                "batch_size": self.database.batch_size
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "metrics_interval": self.monitoring.metrics_interval,
                "max_history_points": self.monitoring.max_history_points,
                "alert_thresholds": self.monitoring.alert_thresholds
            },
            "predictor": {
                "model_path": self.predictor.model_path,
                "auto_retrain": self.predictor.auto_retrain,
                "retrain_threshold": self.predictor.retrain_threshold,
                "confidence_threshold": self.predictor.confidence_threshold,
                "ensemble_enabled": self.predictor.ensemble_enabled,
                "ab_testing_enabled": self.predictor.ab_testing_enabled,
                "anomaly_detection_enabled": self.predictor.anomaly_detection_enabled,
                "feature_selection": self.predictor.feature_selection
            },
            "websocket": {
                "enabled": self.websocket.enabled,
                "max_connections": self.websocket.max_connections,
                "rate_limit_messages": self.websocket.rate_limit_messages,
                "rate_limit_window": self.websocket.rate_limit_window,
                "broadcast_interval": self.websocket.broadcast_interval
            },
            "security": {
                "authentication_enabled": self.security.authentication_enabled,
                "jwt_secret": "***hidden***" if self.security.jwt_secret else None,
                "allowed_origins": self.security.allowed_origins,
                "rate_limiting_enabled": self.security.rate_limiting_enabled,
                "encryption_enabled": self.security.encryption_enabled,
                "audit_logging": self.security.audit_logging
            },
            "performance": {
                "cache_enabled": self.performance.cache_enabled,
                "cache_ttl": self.performance.cache_ttl,
                "compression_enabled": self.performance.compression_enabled,
                "batch_processing": self.performance.batch_processing,
                "async_processing": self.performance.async_processing
            },
            "features": {
                "advanced_predictor": self.features.advanced_predictor,
                "real_time_websocket": self.features.real_time_websocket,
                "database_persistence": self.features.database_persistence,
                "anomaly_detection": self.features.anomaly_detection,
                "ab_testing": self.features.ab_testing,
                "auto_scaling": self.features.auto_scaling,
                "ml_monitoring": self.features.ml_monitoring,
                "export_functionality": self.features.export_functionality
            },
            "system": {
                "debug": self.debug,
                "log_level": self.log_level,
                "environment": self.environment
            }
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Database validation
        if not self.database.url:
            issues.append("Database URL is required")
        
        if self.database.max_connections < self.database.min_connections:
            issues.append("Max connections must be >= min connections")
        
        # Monitoring validation
        if self.monitoring.metrics_interval <= 0:
            issues.append("Metrics interval must be positive")
        
        if self.monitoring.max_history_points <= 0:
            issues.append("Max history points must be positive")
        
        # Predictor validation
        if not Path(self.predictor.model_path).parent.exists():
            issues.append(f"Model path directory does not exist: {self.predictor.model_path}")
        
        if not 0 <= self.predictor.confidence_threshold <= 1:
            issues.append("Confidence threshold must be between 0 and 1")
        
        # WebSocket validation
        if self.websocket.max_connections <= 0:
            issues.append("WebSocket max connections must be positive")
        
        if self.websocket.rate_limit_messages <= 0:
            issues.append("Rate limit messages must be positive")
        
        # Security validation
        if self.security.authentication_enabled and not self.security.jwt_secret:
            issues.append("JWT secret is required when authentication is enabled")
        
        # Performance validation
        if self.performance.cache_ttl <= 0:
            issues.append("Cache TTL must be positive")
        
        return issues
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        if self.debug:
            logging.basicConfig(level=logging.DEBUG, format=log_format)
        else:
            level = getattr(logging, self.log_level, logging.INFO)
            logging.basicConfig(level=level, format=log_format)
        
        # Set analytics logger levels
        analytics_loggers = [
            "analytics",
            "analytics.predictor",
            "analytics.monitoring", 
            "analytics.websocket",
            "analytics.database"
        ]
        
        for logger_name in analytics_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, self.log_level, logging.INFO))


class ConfigManager:
    """Configuration manager with environment variable support."""
    
    def __init__(self):
        self._config: Optional[AnalyticsConfig] = None
        self._config_file_path: Optional[str] = None
    
    def load_config(self, config_file: Optional[str] = None) -> AnalyticsConfig:
        """Load configuration from environment and optional config file."""
        if config_file and Path(config_file).exists():
            self._config_file_path = config_file
            return self._load_from_file(config_file)
        else:
            return self._load_from_env()
    
    def _load_from_env(self) -> AnalyticsConfig:
        """Load configuration from environment variables."""
        config = AnalyticsConfig.from_env()
        
        # Validate configuration
        issues = config.validate()
        if issues:
            logger.warning(f"Configuration validation issues: {issues}")
        
        # Setup logging
        config.setup_logging()
        
        self._config = config
        return config
    
    def _load_from_file(self, config_file: str) -> AnalyticsConfig:
        """Load configuration from JSON file, with environment overrides."""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            
            # Start with file config, then apply environment overrides
            # This would require more complex merging logic
            # For now, just use environment-based config
            return self._load_from_env()
            
        except Exception as e:
            logger.error(f"Failed to load config from file {config_file}: {e}")
            logger.info("Falling back to environment-based configuration")
            return self._load_from_env()
    
    def get_config(self) -> AnalyticsConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self):
        """Reload configuration from source."""
        self._config = None
        return self.get_config()
    
    def save_config(self, file_path: str):
        """Save current configuration to file."""
        if self._config is None:
            raise ValueError("No configuration loaded")
        
        config_dict = self._config.to_dict()
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to {file_path}")


# Global configuration manager
_config_manager: Optional[ConfigManager] = None


def get_analytics_config() -> AnalyticsConfig:
    """Get global analytics configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.get_config()


def reload_analytics_config() -> AnalyticsConfig:
    """Reload global analytics configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.reload_config()


if __name__ == "__main__":
    # Example usage and configuration validation
    config = get_analytics_config()
    
    print("Analytics Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    
    # Validate configuration
    issues = config.validate()
    if issues:
        print(f"\nConfiguration Issues: {issues}")
    else:
        print("\nConfiguration is valid!")
    
    # Display feature flags
    print(f"\nFeature Flags:")
    for flag, enabled in config.features.__dict__.items():
        status = "✓" if enabled else "✗"
        print(f"  {status} {flag}: {enabled}")