"""
Configuration settings for Results Interpretation Agent

This module provides configuration management for the ResultsInterpretationAgent,
including model settings, quality thresholds, and clinical interpretation parameters.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import os


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class ClinicalDomain(str, Enum):
    """Clinical domains for specialized interpretation."""
    GENERAL = "general"
    CARDIOLOGY = "cardiology"
    ONCOLOGY = "oncology"
    NEUROLOGY = "neurology"
    PSYCHIATRY = "psychiatry"
    PAIN_MANAGEMENT = "pain_management"
    INFECTIOUS_DISEASE = "infectious_disease"


@dataclass
class ModelConfig:
    """Configuration for language models."""
    provider: ModelProvider
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 300
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    def __post_init__(self):
        """Set API key from environment if not provided."""
        if self.api_key is None:
            if self.provider == ModelProvider.ANTHROPIC:
                self.api_key = os.getenv("ANTHROPIC_API_KEY")
            elif self.provider == ModelProvider.OPENAI:
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == ModelProvider.AZURE_OPENAI:
                self.api_key = os.getenv("AZURE_OPENAI_API_KEY")


@dataclass
class QualityThresholds:
    """Quality thresholds for interpretation validation."""
    overall_quality: float = 0.85
    completeness: float = 0.80
    clinical_assessment: float = 0.85
    effect_interpretation: float = 0.80
    limitation_identification: float = 0.75
    confidence_assessment: float = 0.80
    phi_detection_sensitivity: float = 0.95


@dataclass
class ClinicalBenchmarks:
    """Clinical benchmarks for significance assessment."""
    small_effect_threshold: float = 0.2
    medium_effect_threshold: float = 0.5
    large_effect_threshold: float = 0.8
    very_large_effect_threshold: float = 1.2
    
    # Clinical significance thresholds
    minimal_clinically_important_difference: float = 0.2
    substantial_clinical_benefit: float = 0.5
    
    # Statistical power thresholds
    adequate_power: float = 0.80
    marginal_power: float = 0.70
    
    # Sample size considerations
    minimum_sample_size: int = 30
    adequate_sample_size: int = 100
    large_sample_size: int = 500


@dataclass
class InterpretationSettings:
    """Settings for clinical interpretation behavior."""
    include_effect_size_interpretation: bool = True
    calculate_nnt_when_possible: bool = True
    perform_literature_comparison: bool = False  # Requires RAG integration
    include_confidence_intervals: bool = True
    assess_clinical_magnitude: bool = True
    identify_statistical_limitations: bool = True
    identify_design_limitations: bool = True
    generate_confidence_statements: bool = True
    synthesize_clinical_narrative: bool = True
    
    # Clinical domain specialization
    clinical_domain: ClinicalDomain = ClinicalDomain.GENERAL
    use_domain_specific_mcid: bool = False
    
    # Output formatting
    generate_apa_summary: bool = True
    include_structured_findings: bool = True
    format_for_manuscript: bool = True
    
    # Safety and compliance
    phi_protection_enabled: bool = True
    redact_phi_automatically: bool = False
    validate_clinical_accuracy: bool = True


@dataclass
class PerformanceSettings:
    """Performance and reliability settings."""
    max_timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 5
    enable_caching: bool = False
    cache_ttl_seconds: int = 3600
    
    # Concurrency settings
    max_concurrent_interpretations: int = 5
    rate_limit_requests_per_minute: int = 60
    
    # Memory management
    max_memory_usage_mb: int = 2048
    clear_cache_on_memory_limit: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None
    log_to_console: bool = True
    
    # Audit logging
    audit_enabled: bool = True
    audit_file: str = "interpretation_audit.log"
    
    # Performance logging
    performance_logging: bool = True
    log_processing_times: bool = True
    log_quality_scores: bool = True


@dataclass
class AgentConfig:
    """Complete configuration for Results Interpretation Agent."""
    
    # Model configurations
    primary_model: ModelConfig = field(default_factory=lambda: ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-5-sonnet-20241022"
    ))
    
    fallback_model: ModelConfig = field(default_factory=lambda: ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o"
    ))
    
    # Quality and performance
    quality_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    clinical_benchmarks: ClinicalBenchmarks = field(default_factory=ClinicalBenchmarks)
    interpretation_settings: InterpretationSettings = field(default_factory=InterpretationSettings)
    performance_settings: PerformanceSettings = field(default_factory=PerformanceSettings)
    
    # Logging and monitoring
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Environment-specific settings
    environment: str = "development"  # development, staging, production
    debug_mode: bool = False
    
    def __post_init__(self):
        """Post-initialization validation and environment-specific adjustments."""
        self._validate_config()
        self._apply_environment_settings()
    
    def _validate_config(self):
        """Validate configuration settings."""
        # Validate quality thresholds
        for threshold_name, threshold_value in self.quality_thresholds.__dict__.items():
            if not 0.0 <= threshold_value <= 1.0:
                raise ValueError(f"Quality threshold {threshold_name} must be between 0.0 and 1.0")
        
        # Validate clinical benchmarks
        benchmarks = self.clinical_benchmarks
        if not (benchmarks.small_effect_threshold < benchmarks.medium_effect_threshold < 
                benchmarks.large_effect_threshold < benchmarks.very_large_effect_threshold):
            raise ValueError("Effect size thresholds must be in ascending order")
        
        # Validate performance settings
        if self.performance_settings.max_timeout_seconds <= 0:
            raise ValueError("Max timeout must be positive")
        
        if self.performance_settings.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
    
    def _apply_environment_settings(self):
        """Apply environment-specific configuration adjustments."""
        if self.environment == "production":
            # Production optimizations
            self.logging.log_level = "WARNING"
            self.debug_mode = False
            self.interpretation_settings.phi_protection_enabled = True
            self.quality_thresholds.overall_quality = 0.90  # Higher quality in production
            
        elif self.environment == "staging":
            # Staging settings
            self.logging.log_level = "INFO"
            self.debug_mode = False
            self.quality_thresholds.overall_quality = 0.85
            
        elif self.environment == "development":
            # Development settings
            self.logging.log_level = "DEBUG"
            self.debug_mode = True
            self.quality_thresholds.overall_quality = 0.75  # More lenient for testing
            
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
    
    def get_model_kwargs(self, model_config: ModelConfig) -> Dict[str, Any]:
        """Get keyword arguments for model initialization."""
        kwargs = {
            "model": model_config.model_name,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens,
            "timeout": model_config.timeout
        }
        
        if model_config.api_key:
            kwargs["api_key"] = model_config.api_key
        
        if model_config.base_url:
            kwargs["base_url"] = model_config.base_url
        
        return kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def _convert_dataclass(obj):
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if hasattr(value, '__dict__'):
                        result[key] = _convert_dataclass(value)
                    elif isinstance(value, Enum):
                        result[key] = value.value
                    else:
                        result[key] = value
                return result
            return obj
        
        return _convert_dataclass(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AgentConfig':
        """Create configuration from dictionary."""
        # This is a simplified implementation
        # In production, you'd want more robust deserialization
        config = cls()
        
        # Update with provided values
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'AgentConfig':
        """Load configuration from JSON file."""
        import json
        from pathlib import Path
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        
        return cls.from_dict(config_dict)
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to JSON file."""
        import json
        from pathlib import Path
        
        config_dict = self.to_dict()
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)


# =============================================================================
# Predefined Configurations
# =============================================================================

def get_development_config() -> AgentConfig:
    """Get configuration optimized for development."""
    config = AgentConfig()
    config.environment = "development"
    config.debug_mode = True
    config.logging.log_level = "DEBUG"
    config.quality_thresholds.overall_quality = 0.75
    config.performance_settings.max_timeout_seconds = 120
    return config


def get_staging_config() -> AgentConfig:
    """Get configuration optimized for staging."""
    config = AgentConfig()
    config.environment = "staging"
    config.debug_mode = False
    config.logging.log_level = "INFO"
    config.quality_thresholds.overall_quality = 0.85
    config.interpretation_settings.phi_protection_enabled = True
    return config


def get_production_config() -> AgentConfig:
    """Get configuration optimized for production."""
    config = AgentConfig()
    config.environment = "production"
    config.debug_mode = False
    config.logging.log_level = "WARNING"
    config.quality_thresholds.overall_quality = 0.90
    config.interpretation_settings.phi_protection_enabled = True
    config.interpretation_settings.redact_phi_automatically = True
    config.performance_settings.enable_caching = True
    return config


def get_high_accuracy_config() -> AgentConfig:
    """Get configuration optimized for maximum accuracy."""
    config = get_production_config()
    config.quality_thresholds.overall_quality = 0.95
    config.quality_thresholds.completeness = 0.90
    config.quality_thresholds.clinical_assessment = 0.95
    config.quality_thresholds.effect_interpretation = 0.90
    config.performance_settings.max_timeout_seconds = 600
    config.performance_settings.max_retries = 5
    return config


def get_fast_processing_config() -> AgentConfig:
    """Get configuration optimized for speed."""
    config = AgentConfig()
    config.performance_settings.max_timeout_seconds = 60
    config.performance_settings.max_retries = 1
    config.quality_thresholds.overall_quality = 0.75
    config.interpretation_settings.include_effect_size_interpretation = True
    config.interpretation_settings.synthesize_clinical_narrative = False  # Skip for speed
    config.primary_model.model_name = "claude-3-haiku-20240307"  # Faster model
    return config


# =============================================================================
# Domain-Specific Configurations
# =============================================================================

def get_oncology_config() -> AgentConfig:
    """Get configuration specialized for oncology studies."""
    config = get_production_config()
    config.interpretation_settings.clinical_domain = ClinicalDomain.ONCOLOGY
    config.interpretation_settings.use_domain_specific_mcid = True
    
    # Oncology-specific clinical benchmarks
    config.clinical_benchmarks.minimal_clinically_important_difference = 0.3
    config.clinical_benchmarks.substantial_clinical_benefit = 0.6
    
    return config


def get_cardiology_config() -> AgentConfig:
    """Get configuration specialized for cardiology studies."""
    config = get_production_config()
    config.interpretation_settings.clinical_domain = ClinicalDomain.CARDIOLOGY
    config.interpretation_settings.use_domain_specific_mcid = True
    config.interpretation_settings.calculate_nnt_when_possible = True
    
    return config


def get_pain_management_config() -> AgentConfig:
    """Get configuration specialized for pain management studies."""
    config = get_production_config()
    config.interpretation_settings.clinical_domain = ClinicalDomain.PAIN_MANAGEMENT
    config.interpretation_settings.use_domain_specific_mcid = True
    
    # Pain-specific benchmarks
    config.clinical_benchmarks.minimal_clinically_important_difference = 1.5  # For VAS pain scale
    config.clinical_benchmarks.substantial_clinical_benefit = 3.0
    
    return config


# =============================================================================
# Configuration Factory
# =============================================================================

def create_config(
    environment: str = "development",
    clinical_domain: Optional[str] = None,
    optimization: Optional[str] = None
) -> AgentConfig:
    """
    Factory function to create appropriate configuration.
    
    Args:
        environment: Target environment (development, staging, production)
        clinical_domain: Clinical specialization (oncology, cardiology, etc.)
        optimization: Optimization target (accuracy, speed)
    
    Returns:
        Configured AgentConfig instance
    """
    # Base configuration by environment
    if environment == "development":
        config = get_development_config()
    elif environment == "staging":
        config = get_staging_config()
    elif environment == "production":
        config = get_production_config()
    else:
        raise ValueError(f"Unknown environment: {environment}")
    
    # Apply optimization
    if optimization == "accuracy":
        accuracy_config = get_high_accuracy_config()
        config.quality_thresholds = accuracy_config.quality_thresholds
        config.performance_settings.max_timeout_seconds = accuracy_config.performance_settings.max_timeout_seconds
        config.performance_settings.max_retries = accuracy_config.performance_settings.max_retries
        
    elif optimization == "speed":
        speed_config = get_fast_processing_config()
        config.performance_settings = speed_config.performance_settings
        config.primary_model.model_name = speed_config.primary_model.model_name
        config.interpretation_settings.synthesize_clinical_narrative = False
    
    # Apply domain specialization
    if clinical_domain:
        try:
            domain_enum = ClinicalDomain(clinical_domain.lower())
            config.interpretation_settings.clinical_domain = domain_enum
            
            if domain_enum == ClinicalDomain.ONCOLOGY:
                oncology_config = get_oncology_config()
                config.clinical_benchmarks = oncology_config.clinical_benchmarks
                
            elif domain_enum == ClinicalDomain.CARDIOLOGY:
                cardiology_config = get_cardiology_config()
                config.interpretation_settings.calculate_nnt_when_possible = True
                
            elif domain_enum == ClinicalDomain.PAIN_MANAGEMENT:
                pain_config = get_pain_management_config()
                config.clinical_benchmarks = pain_config.clinical_benchmarks
                
        except ValueError:
            raise ValueError(f"Unknown clinical domain: {clinical_domain}")
    
    return config


# =============================================================================
# Environment Variables
# =============================================================================

def load_config_from_env() -> AgentConfig:
    """Load configuration from environment variables."""
    config = AgentConfig()
    
    # Environment
    config.environment = os.getenv("RESEARCHFLOW_ENVIRONMENT", "development")
    
    # Model settings
    if os.getenv("ANTHROPIC_MODEL"):
        config.primary_model.model_name = os.getenv("ANTHROPIC_MODEL")
    
    if os.getenv("OPENAI_MODEL"):
        config.fallback_model.model_name = os.getenv("OPENAI_MODEL")
    
    # Quality thresholds
    if os.getenv("QUALITY_THRESHOLD"):
        config.quality_thresholds.overall_quality = float(os.getenv("QUALITY_THRESHOLD"))
    
    # Performance settings
    if os.getenv("MAX_TIMEOUT"):
        config.performance_settings.max_timeout_seconds = int(os.getenv("MAX_TIMEOUT"))
    
    # PHI protection
    if os.getenv("PHI_PROTECTION"):
        config.interpretation_settings.phi_protection_enabled = os.getenv("PHI_PROTECTION").lower() == "true"
    
    # Debug mode
    if os.getenv("DEBUG_MODE"):
        config.debug_mode = os.getenv("DEBUG_MODE").lower() == "true"
    
    return config


if __name__ == "__main__":
    # Example usage
    print("🔧 Results Interpretation Agent Configuration")
    print("=" * 50)
    
    # Test different configurations
    configs = {
        "Development": get_development_config(),
        "Production": get_production_config(), 
        "High Accuracy": get_high_accuracy_config(),
        "Fast Processing": get_fast_processing_config(),
        "Oncology Specialized": get_oncology_config()
    }
    
    for name, config in configs.items():
        print(f"\n{name} Configuration:")
        print(f"  Environment: {config.environment}")
        print(f"  Quality threshold: {config.quality_thresholds.overall_quality}")
        print(f"  Timeout: {config.performance_settings.max_timeout_seconds}s")
        print(f"  PHI protection: {config.interpretation_settings.phi_protection_enabled}")
        print(f"  Clinical domain: {config.interpretation_settings.clinical_domain.value}")
    
    print("\n✅ Configuration system initialized successfully!")