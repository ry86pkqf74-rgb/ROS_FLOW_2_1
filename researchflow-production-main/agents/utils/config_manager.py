#!/usr/bin/env python3
"""
Production Configuration Manager for ResearchFlow Agents

Provides centralized configuration management with:
- Environment-specific configurations (dev, staging, prod)
- Configuration validation and type checking
- Hot reloading of configuration
- Configuration templating
- Secret interpolation

@author Claude
@created 2025-01-30
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Type, Union, List
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
import logging

from .secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str
    pool_size: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str
    max_connections: int = 10
    socket_timeout: int = 30
    socket_connect_timeout: int = 30


@dataclass
class APIConfig:
    """API service configuration"""
    openai_api_key: str
    anthropic_api_key: Optional[str] = None
    composio_api_key: str = ""
    xai_api_key: Optional[str] = None
    mercury_api_key: Optional[str] = None
    github_token: Optional[str] = None
    notion_api_key: Optional[str] = None
    figma_api_key: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "text"  # text or json
    structured: bool = True
    file_path: Optional[str] = None
    max_file_size: int = 100  # MB
    backup_count: int = 5


@dataclass
class MetricsConfig:
    """Metrics configuration"""
    enabled: bool = True
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    log_metrics: bool = True
    push_gateway_url: Optional[str] = None


@dataclass
class HealthConfig:
    """Health check configuration"""
    enabled: bool = True
    check_interval: int = 30
    timeout: int = 10
    critical_threshold: float = 0.8  # 80% failure rate
    warning_threshold: float = 0.5   # 50% failure rate


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_backend: str = "env"
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    jwt_secret: str = "change-me-in-production"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 100


@dataclass
class AgentConfig:
    """Individual agent configuration"""
    enabled: bool = True
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 120
    max_retries: int = 3


@dataclass
class ResearchFlowConfig:
    """Complete ResearchFlow configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Service configurations
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(url=""))
    redis: RedisConfig = field(default_factory=lambda: RedisConfig(url=""))
    api: APIConfig = field(default_factory=lambda: APIConfig(openai_api_key="", composio_api_key=""))
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Agent configurations
    design_ops: AgentConfig = field(default_factory=AgentConfig)
    spec_ops: AgentConfig = field(default_factory=AgentConfig)
    compliance: AgentConfig = field(default_factory=AgentConfig)
    release_guardian: AgentConfig = field(default_factory=AgentConfig)
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT


class ConfigManager:
    """
    Configuration manager with environment-specific loading.
    
    Loads configuration from multiple sources in order of precedence:
    1. Environment variables
    2. Configuration files (config.{env}.yaml)
    3. Default values
    
    Example:
        >>> config_manager = ConfigManager()
        >>> config = config_manager.load_config()
        >>> print(config.database.url)
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.secrets_manager = get_secrets_manager()
        self._config: Optional[ResearchFlowConfig] = None
    
    def load_config(self, environment: Optional[str] = None) -> ResearchFlowConfig:
        """
        Load configuration for the specified environment.
        
        Args:
            environment: Environment name (development, staging, production)
                        If None, uses ENV environment variable
        """
        env_name = environment or os.getenv("ENV", "development")
        
        try:
            env = Environment(env_name.lower())
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            env = Environment.DEVELOPMENT
        
        logger.info(f"Loading configuration for environment: {env.value}")
        
        # Start with default configuration
        config = ResearchFlowConfig(environment=env)
        
        # Load from configuration file if it exists
        config_file = self.config_dir / f"config.{env.value}.yaml"
        if config_file.exists():
            file_config = self._load_config_file(config_file)
            config = self._merge_config(config, file_config)
        else:
            logger.info(f"No config file found at {config_file}, using defaults + environment")
        
        # Override with environment variables
        config = self._apply_environment_variables(config)
        
        # Interpolate secrets
        config = self._interpolate_secrets(config)
        
        # Validate configuration
        self._validate_config(config)
        
        self._config = config
        return config
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")
            return {}
    
    def _merge_config(self, base_config: ResearchFlowConfig, file_config: Dict[str, Any]) -> ResearchFlowConfig:
        """Merge file configuration with base configuration"""
        try:
            # Convert nested dictionaries to dataclass instances
            for field_name, field_type in [
                ("database", DatabaseConfig),
                ("redis", RedisConfig),
                ("api", APIConfig),
                ("logging", LoggingConfig),
                ("metrics", MetricsConfig),
                ("health", HealthConfig),
                ("security", SecurityConfig),
                ("design_ops", AgentConfig),
                ("spec_ops", AgentConfig),
                ("compliance", AgentConfig),
                ("release_guardian", AgentConfig),
            ]:
                if field_name in file_config:
                    field_data = file_config[field_name]
                    if isinstance(field_data, dict):
                        # Create new instance with merged data
                        current_instance = getattr(base_config, field_name)
                        current_dict = current_instance.__dict__.copy()
                        current_dict.update(field_data)
                        setattr(base_config, field_name, field_type(**current_dict))
            
            # Handle top-level fields
            if "environment" in file_config:
                base_config.environment = Environment(file_config["environment"])
            if "debug" in file_config:
                base_config.debug = file_config["debug"]
                
        except Exception as e:
            logger.error(f"Error merging configuration: {e}")
        
        return base_config
    
    def _apply_environment_variables(self, config: ResearchFlowConfig) -> ResearchFlowConfig:
        """Apply environment variable overrides"""
        
        # Environment mapping
        env_mapping = {
            # Database
            "DATABASE_URL": ("database", "url"),
            "DATABASE_POOL_SIZE": ("database", "pool_size", int),
            
            # Redis
            "REDIS_URL": ("redis", "url"),
            "REDIS_MAX_CONNECTIONS": ("redis", "max_connections", int),
            
            # API Keys
            "OPENAI_API_KEY": ("api", "openai_api_key"),
            "ANTHROPIC_API_KEY": ("api", "anthropic_api_key"),
            "COMPOSIO_API_KEY": ("api", "composio_api_key"),
            "XAI_API_KEY": ("api", "xai_api_key"),
            "MERCURY_API_KEY": ("api", "mercury_api_key"),
            "GITHUB_TOKEN": ("api", "github_token"),
            "NOTION_API_KEY": ("api", "notion_api_key"),
            "FIGMA_API_KEY": ("api", "figma_api_key"),
            
            # Logging
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FORMAT": ("logging", "format"),
            "LOG_FILE": ("logging", "file_path"),
            
            # Metrics
            "METRICS_ENABLED": ("metrics", "enabled", bool),
            "PROMETHEUS_ENABLED": ("metrics", "prometheus_enabled", bool),
            "PROMETHEUS_PORT": ("metrics", "prometheus_port", int),
            
            # Health
            "HEALTH_ENABLED": ("health", "enabled", bool),
            "HEALTH_INTERVAL": ("health", "check_interval", int),
            
            # Security
            "SECRET_BACKEND": ("security", "secret_backend"),
            "VAULT_URL": ("security", "vault_url"),
            "VAULT_TOKEN": ("security", "vault_token"),
            "JWT_SECRET": ("security", "jwt_secret"),
            
            # Top-level
            "ENV": ("environment", None, Environment),
            "DEBUG": ("debug", None, bool),
        }
        
        for env_var, (section, field, *converter) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Apply type conversion
                if converter:
                    converter_func = converter[0]
                    if converter_func == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    elif converter_func == int:
                        try:
                            value = int(value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {env_var}: {value}")
                            continue
                    elif converter_func == Environment:
                        try:
                            value = Environment(value.lower())
                        except ValueError:
                            logger.warning(f"Invalid environment value: {value}")
                            continue
                
                # Set the value
                if field is None:
                    # Top-level field
                    setattr(config, section, value)
                else:
                    # Nested field
                    section_obj = getattr(config, section)
                    setattr(section_obj, field, value)
        
        return config
    
    def _interpolate_secrets(self, config: ResearchFlowConfig) -> ResearchFlowConfig:
        """Interpolate secrets from secret management backend"""
        
        # Secret fields that should be retrieved securely
        secret_fields = [
            ("api", "openai_api_key"),
            ("api", "anthropic_api_key"),
            ("api", "composio_api_key"),
            ("api", "xai_api_key"),
            ("api", "mercury_api_key"),
            ("api", "github_token"),
            ("api", "notion_api_key"),
            ("api", "figma_api_key"),
            ("database", "url"),
            ("redis", "url"),
            ("security", "vault_token"),
            ("security", "jwt_secret"),
        ]
        
        for section_name, field_name in secret_fields:
            section = getattr(config, section_name)
            current_value = getattr(section, field_name)
            
            # If value is not set or is placeholder, try to get from secrets
            if not current_value or current_value in ["", "change-me-in-production"]:
                # Convert field name to environment variable format
                env_var = f"{field_name.upper()}"
                if section_name != "api":
                    env_var = f"{section_name.upper()}_{env_var}"
                
                secret_value = self.secrets_manager.get_secret(env_var)
                if secret_value:
                    setattr(section, field_name, secret_value)
        
        return config
    
    def _validate_config(self, config: ResearchFlowConfig):
        """Validate configuration for production readiness"""
        errors = []
        warnings = []
        
        # Required fields for production
        if config.is_production():
            if not config.api.openai_api_key:
                errors.append("OpenAI API key is required for production")
            
            if not config.api.composio_api_key:
                errors.append("Composio API key is required for production")
            
            if not config.database.url or "change-me" in config.database.url:
                errors.append("Valid database URL is required for production")
            
            if not config.redis.url or "change-me" in config.redis.url:
                errors.append("Valid Redis URL is required for production")
            
            if config.security.jwt_secret == "change-me-in-production":
                errors.append("JWT secret must be changed for production")
            
            if config.debug:
                warnings.append("Debug mode should be disabled in production")
        
        # Validation warnings
        if config.api.max_retries > 10:
            warnings.append(f"High retry count ({config.api.max_retries}) may cause delays")
        
        if config.metrics.prometheus_port < 1024:
            warnings.append("Prometheus port below 1024 requires root privileges")
        
        # Log results
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        logger.info("✅ Configuration validation passed")
    
    def get_config(self) -> Optional[ResearchFlowConfig]:
        """Get current loaded configuration"""
        return self._config
    
    def save_config_template(self, output_file: str = "config.template.yaml"):
        """Save configuration template with all options"""
        template = {
            "environment": "development",
            "debug": True,
            "database": {
                "url": "postgresql://user:password@localhost:5432/researchflow",
                "pool_size": 10,
                "pool_timeout": 30,
                "echo": False
            },
            "redis": {
                "url": "redis://:password@localhost:6379",
                "max_connections": 10
            },
            "api": {
                "openai_api_key": "${OPENAI_API_KEY}",
                "anthropic_api_key": "${ANTHROPIC_API_KEY}",
                "composio_api_key": "${COMPOSIO_API_KEY}",
                "max_retries": 3,
                "timeout_seconds": 30
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "structured": True
            },
            "metrics": {
                "enabled": True,
                "prometheus_enabled": True,
                "prometheus_port": 9090
            },
            "health": {
                "enabled": True,
                "check_interval": 30,
                "timeout": 10
            },
            "security": {
                "secret_backend": "vault",
                "vault_url": "${VAULT_URL}",
                "cors_origins": ["http://localhost:3000"]
            },
            "design_ops": {
                "enabled": True,
                "model": "gpt-4o",
                "temperature": 0.7
            },
            "spec_ops": {
                "enabled": True,
                "model": "gpt-4o"
            },
            "compliance": {
                "enabled": True,
                "model": "claude-3-5-sonnet-20241022"
            },
            "release_guardian": {
                "enabled": True,
                "model": "gpt-4o"
            }
        }
        
        with open(output_file, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration template saved to {output_file}")


# Singleton config manager
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config(environment: Optional[str] = None) -> ResearchFlowConfig:
    """Load configuration for the specified environment"""
    return get_config_manager().load_config(environment)


def get_config() -> Optional[ResearchFlowConfig]:
    """Get the current loaded configuration"""
    return get_config_manager().get_config()