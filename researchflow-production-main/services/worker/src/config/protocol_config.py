"""
Protocol Configuration Management System

Centralized configuration management for protocol generation including:
- User preferences and default values
- Template customizations
- Regulatory compliance settings
- PHI compliance levels
- API configuration
- Performance tuning parameters

Key Features:
- Environment-based configuration
- User-specific preferences
- Template customization
- Validation and schema enforcement
- Configuration versioning
- Secure credential management

Author: Enhancement Team
"""

import os
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigEnvironment(Enum):
    """Configuration environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class TemplateCustomizationLevel(Enum):
    """Levels of template customization allowed."""
    NONE = "none"           # Use default templates only
    BASIC = "basic"         # Allow variable customization
    ADVANCED = "advanced"   # Allow section customization
    FULL = "full"           # Allow complete template editing


@dataclass
class PHIComplianceSettings:
    """PHI compliance configuration."""
    enabled: bool = True
    compliance_level: str = "strict"  # strict, moderate, permissive
    auto_sanitize: bool = True
    audit_logging: bool = True
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)
    allowed_phi_types: List[str] = field(default_factory=list)
    sanitization_method: str = "redact"  # redact, mask, encrypt, remove


@dataclass
class APIConfiguration:
    """API-specific configuration."""
    host: str = "0.0.0.0"
    port: int = 8002
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    gzip_enabled: bool = True
    request_timeout: int = 30
    max_content_length: int = 10 * 1024 * 1024  # 10MB


@dataclass
class PerformanceSettings:
    """Performance optimization settings."""
    max_concurrent_requests: int = 10
    template_caching: bool = True
    cache_ttl: int = 3600  # seconds
    async_processing: bool = True
    batch_size_limit: int = 50
    memory_limit_mb: int = 512
    cpu_optimization: bool = True


@dataclass
class RegulatorySettings:
    """Regulatory compliance configuration."""
    enabled_frameworks: List[str] = field(default_factory=lambda: ["hipaa", "ich_gcp"])
    default_framework: str = "hipaa"
    require_framework_selection: bool = True
    framework_validation: bool = True
    compliance_checking: bool = True
    audit_trail: bool = True


@dataclass
class UserPreferences:
    """User-specific preferences."""
    user_id: str = "default"
    default_template: str = "rct_basic_v1"
    preferred_output_format: str = "markdown"
    auto_save: bool = True
    language: str = "en"
    timezone: str = "UTC"
    notification_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "generation_complete": True,
        "validation_warnings": True,
        "phi_alerts": True
    })
    custom_variables: Dict[str, str] = field(default_factory=dict)


@dataclass
class TemplateConfiguration:
    """Template-specific configuration."""
    template_id: str
    customizations: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    version_lock: Optional[str] = None
    custom_sections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    variable_overrides: Dict[str, str] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class ProtocolConfig:
    """Main configuration class for protocol generation system."""
    
    # Environment settings
    environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT
    debug_mode: bool = False
    log_level: str = "INFO"
    
    # Core settings
    template_version: str = "v1.2"
    customization_level: TemplateCustomizationLevel = TemplateCustomizationLevel.BASIC
    
    # Component configurations
    phi_compliance: PHIComplianceSettings = field(default_factory=PHIComplianceSettings)
    api_config: APIConfiguration = field(default_factory=APIConfiguration)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    regulatory: RegulatorySettings = field(default_factory=RegulatorySettings)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Template configurations
    template_configs: Dict[str, TemplateConfiguration] = field(default_factory=dict)
    
    # Metadata
    config_version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    def save_to_file(self, file_path: Path, format_type: str = "json"):
        """Save configuration to file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == "json":
                with open(file_path, 'w') as f:
                    f.write(self.to_json())
            elif format_type.lower() == "yaml":
                with open(file_path, 'w') as f:
                    f.write(self.to_yaml())
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            raise
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration settings."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Validate API configuration
            if self.api_config.port < 1 or self.api_config.port > 65535:
                validation_result["errors"].append("API port must be between 1 and 65535")
                validation_result["valid"] = False
            
            # Validate PHI compliance settings
            valid_compliance_levels = ["strict", "moderate", "permissive"]
            if self.phi_compliance.compliance_level not in valid_compliance_levels:
                validation_result["errors"].append(
                    f"PHI compliance level must be one of: {valid_compliance_levels}"
                )
                validation_result["valid"] = False
            
            # Validate performance settings
            if self.performance.max_concurrent_requests < 1:
                validation_result["errors"].append("Max concurrent requests must be >= 1")
                validation_result["valid"] = False
            
            # Validate template configurations
            for template_id, template_config in self.template_configs.items():
                if not template_config.template_id:
                    validation_result["errors"].append(f"Template {template_id} missing template_id")
                    validation_result["valid"] = False
            
            # Warnings for development settings in production
            if self.environment == ConfigEnvironment.PRODUCTION:
                if self.debug_mode:
                    validation_result["warnings"].append("Debug mode enabled in production")
                
                if self.log_level == "DEBUG":
                    validation_result["warnings"].append("Debug logging enabled in production")
            
            return validation_result
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            return validation_result


class ConfigManager:
    """Configuration manager for loading and managing protocol configurations."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent / "configs"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._current_config: Optional[ProtocolConfig] = None
        self._config_cache: Dict[str, ProtocolConfig] = {}
    
    def load_config(self,
                   config_name: str = "default",
                   environment: Optional[ConfigEnvironment] = None) -> ProtocolConfig:
        """
        Load configuration from file or create default.
        
        Args:
            config_name: Name of the configuration
            environment: Override environment
            
        Returns:
            Loaded configuration
        """
        try:
            # Try to load from cache first
            cache_key = f"{config_name}_{environment or 'auto'}"
            if cache_key in self._config_cache:
                return self._config_cache[cache_key]
            
            # Determine config file path
            config_file = self.config_dir / f"{config_name}.json"
            
            if config_file.exists():
                config = self._load_from_file(config_file)
            else:
                logger.info(f"Config file {config_file} not found, creating default")
                config = self._create_default_config()
                self.save_config(config, config_name)
            
            # Override environment if specified
            if environment:
                config.environment = environment
            
            # Validate configuration
            validation_result = config.validate_configuration()
            if not validation_result["valid"]:
                logger.error(f"Configuration validation failed: {validation_result['errors']}")
                raise ValueError(f"Invalid configuration: {validation_result['errors']}")
            
            if validation_result["warnings"]:
                for warning in validation_result["warnings"]:
                    logger.warning(f"Configuration warning: {warning}")
            
            # Cache and return
            self._config_cache[cache_key] = config
            self._current_config = config
            
            logger.info(f"Configuration '{config_name}' loaded successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            # Return default config as fallback
            return self._create_default_config()
    
    def _load_from_file(self, config_file: Path) -> ProtocolConfig:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            return self._dict_to_config(config_data)
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {str(e)}")
            raise
    
    def _dict_to_config(self, config_data: Dict[str, Any]) -> ProtocolConfig:
        """Convert dictionary to ProtocolConfig object."""
        try:
            # Handle nested dataclass objects
            if 'phi_compliance' in config_data:
                config_data['phi_compliance'] = PHIComplianceSettings(**config_data['phi_compliance'])
            
            if 'api_config' in config_data:
                config_data['api_config'] = APIConfiguration(**config_data['api_config'])
            
            if 'performance' in config_data:
                config_data['performance'] = PerformanceSettings(**config_data['performance'])
            
            if 'regulatory' in config_data:
                config_data['regulatory'] = RegulatorySettings(**config_data['regulatory'])
            
            if 'user_preferences' in config_data:
                config_data['user_preferences'] = UserPreferences(**config_data['user_preferences'])
            
            # Handle template configurations
            if 'template_configs' in config_data:
                template_configs = {}
                for template_id, template_data in config_data['template_configs'].items():
                    template_configs[template_id] = TemplateConfiguration(**template_data)
                config_data['template_configs'] = template_configs
            
            # Handle enums
            if 'environment' in config_data:
                config_data['environment'] = ConfigEnvironment(config_data['environment'])
            
            if 'customization_level' in config_data:
                config_data['customization_level'] = TemplateCustomizationLevel(
                    config_data['customization_level']
                )
            
            return ProtocolConfig(**config_data)
            
        except Exception as e:
            logger.error(f"Failed to convert dict to config: {str(e)}")
            raise
    
    def save_config(self, config: ProtocolConfig, config_name: str = "default"):
        """Save configuration to file."""
        try:
            config.last_modified = datetime.now().isoformat()
            config_file = self.config_dir / f"{config_name}.json"
            config.save_to_file(config_file, "json")
            
            # Update cache
            cache_key = f"{config_name}_{config.environment.value}"
            self._config_cache[cache_key] = config
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            raise
    
    def _create_default_config(self) -> ProtocolConfig:
        """Create default configuration."""
        # Environment-based defaults
        env = os.getenv("PROTOCOL_ENV", "development").lower()
        
        if env == "production":
            environment = ConfigEnvironment.PRODUCTION
            debug_mode = False
            log_level = "INFO"
        elif env == "staging":
            environment = ConfigEnvironment.STAGING
            debug_mode = False
            log_level = "INFO"
        else:
            environment = ConfigEnvironment.DEVELOPMENT
            debug_mode = True
            log_level = "DEBUG"
        
        return ProtocolConfig(
            environment=environment,
            debug_mode=debug_mode,
            log_level=log_level,
            template_version="v1.2",
            customization_level=TemplateCustomizationLevel.BASIC
        )
    
    def get_current_config(self) -> ProtocolConfig:
        """Get currently loaded configuration."""
        if self._current_config is None:
            self._current_config = self.load_config()
        return self._current_config
    
    def update_user_preferences(self,
                              user_id: str,
                              preferences: Dict[str, Any],
                              config_name: str = "default"):
        """Update user preferences in configuration."""
        try:
            config = self.load_config(config_name)
            
            # Update user preferences
            for key, value in preferences.items():
                if hasattr(config.user_preferences, key):
                    setattr(config.user_preferences, key, value)
            
            config.user_preferences.user_id = user_id
            config.last_modified = datetime.now().isoformat()
            
            # Save updated configuration
            self.save_config(config, config_name)
            
            logger.info(f"Updated user preferences for {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {str(e)}")
            raise
    
    def add_template_configuration(self,
                                 template_config: TemplateConfiguration,
                                 config_name: str = "default"):
        """Add or update template configuration."""
        try:
            config = self.load_config(config_name)
            config.template_configs[template_config.template_id] = template_config
            config.last_modified = datetime.now().isoformat()
            
            self.save_config(config, config_name)
            
            logger.info(f"Added template configuration: {template_config.template_id}")
            
        except Exception as e:
            logger.error(f"Failed to add template configuration: {str(e)}")
            raise
    
    def get_template_configuration(self,
                                 template_id: str,
                                 config_name: str = "default") -> Optional[TemplateConfiguration]:
        """Get template-specific configuration."""
        try:
            config = self.load_config(config_name)
            return config.template_configs.get(template_id)
            
        except Exception as e:
            logger.error(f"Failed to get template configuration: {str(e)}")
            return None
    
    def create_environment_config(self, environment: ConfigEnvironment, config_name: str):
        """Create environment-specific configuration."""
        try:
            base_config = self._create_default_config()
            base_config.environment = environment
            
            # Environment-specific adjustments
            if environment == ConfigEnvironment.PRODUCTION:
                base_config.debug_mode = False
                base_config.log_level = "WARNING"
                base_config.phi_compliance.compliance_level = "strict"
                base_config.api_config.cors_origins = []  # Restrict CORS in production
                base_config.performance.max_concurrent_requests = 20
                
            elif environment == ConfigEnvironment.STAGING:
                base_config.debug_mode = False
                base_config.log_level = "INFO"
                base_config.phi_compliance.compliance_level = "moderate"
                
            else:  # DEVELOPMENT, TESTING
                base_config.debug_mode = True
                base_config.log_level = "DEBUG"
                base_config.phi_compliance.compliance_level = "permissive"
            
            self.save_config(base_config, config_name)
            logger.info(f"Created {environment.value} configuration: {config_name}")
            
        except Exception as e:
            logger.error(f"Failed to create environment config: {str(e)}")
            raise


# Global configuration manager instance
config_manager = ConfigManager()


# Convenience functions
def get_config(config_name: str = "default") -> ProtocolConfig:
    """Get configuration by name."""
    return config_manager.load_config(config_name)


def get_current_config() -> ProtocolConfig:
    """Get currently active configuration."""
    return config_manager.get_current_config()


def update_user_preferences(user_id: str, preferences: Dict[str, Any]):
    """Update user preferences."""
    config_manager.update_user_preferences(user_id, preferences)


def create_template_config(template_id: str, **kwargs) -> TemplateConfiguration:
    """Create template configuration."""
    return TemplateConfiguration(template_id=template_id, **kwargs)