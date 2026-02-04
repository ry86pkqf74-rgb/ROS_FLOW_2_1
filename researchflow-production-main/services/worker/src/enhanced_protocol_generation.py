"""
Enhanced Protocol Generation Integration Layer

Integrates all enhancement components:
- PHI Compliance Validation
- Configuration Management
- API Layer
- Performance Monitoring
- Template Management

This module provides a unified interface for the enhanced protocol generation system
with full PHI compliance, user configuration support, and enterprise features.

Author: Enhancement Team
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

# Import core components
from workflow_engine.stages.study_analyzers.protocol_generator import (
    ProtocolGenerator,
    ProtocolFormat,
    TemplateType
)

# Import enhancements
from security.phi_compliance import (
    PHIComplianceValidator,
    ComplianceLevel,
    validate_protocol_phi_compliance,
    create_phi_compliant_template_variables
)
from config.protocol_config import (
    ProtocolConfig,
    ConfigManager,
    get_current_config,
    TemplateConfiguration
)

logger = logging.getLogger(__name__)


class EnhancedProtocolGenerator:
    """
    Enhanced Protocol Generator with PHI compliance, configuration management,
    and advanced features integrated.
    """
    
    def __init__(self, config_name: str = "default"):
        """
        Initialize enhanced protocol generator.
        
        Args:
            config_name: Name of configuration to use
        """
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config(config_name)
        
        # Initialize core generator with config
        self.protocol_generator = ProtocolGenerator(
            template_version=self.config.template_version,
            enable_phi_integration=self.config.phi_compliance.enabled,
            regulatory_templates=self.config.regulatory.compliance_checking
        )
        
        # Initialize PHI compliance validator
        compliance_level = ComplianceLevel(self.config.phi_compliance.compliance_level)
        self.phi_validator = PHIComplianceValidator(
            compliance_level=compliance_level,
            enable_audit=self.config.phi_compliance.audit_logging
        )
        
        # Performance and monitoring
        self.generation_metrics = []
        
        logger.info(f"Enhanced Protocol Generator initialized with config: {config_name}")
    
    async def generate_protocol_enhanced(self,
                                       template_id: str,
                                       study_data: Dict[str, Any],
                                       output_format: ProtocolFormat = ProtocolFormat.MARKDOWN,
                                       user_id: Optional[str] = None,
                                       phi_check: bool = True) -> Dict[str, Any]:
        """
        Generate protocol with full enhancement features.
        
        Args:
            template_id: Template to use
            study_data: Study parameters
            output_format: Desired output format
            user_id: User identifier for preferences
            phi_check: Perform PHI compliance checking
            
        Returns:
            Enhanced generation result with compliance info
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting enhanced protocol generation for template: {template_id}")
            
            # Apply user preferences if provided
            if user_id:
                study_data = await self._apply_user_preferences(study_data, user_id)
            
            # Apply template-specific configuration
            template_config = self.config_manager.get_template_configuration(template_id)
            if template_config:
                study_data = await self._apply_template_config(study_data, template_config)
            
            # PHI compliance preprocessing
            phi_compliant_data = study_data
            phi_validation_result = None
            
            if phi_check and self.config.phi_compliance.enabled:
                logger.info("Performing PHI compliance validation")
                
                # Create PHI-compliant variables
                if self.config.phi_compliance.auto_sanitize:
                    phi_compliant_data = create_phi_compliant_template_variables(study_data)
                
                # Validate compliance
                import json
                phi_validation_result = validate_protocol_phi_compliance(
                    json.dumps(study_data),
                    study_data,
                    ComplianceLevel(self.config.phi_compliance.compliance_level)
                )
                
                if not phi_validation_result.is_compliant:
                    logger.warning(f"PHI compliance issues detected: {len(phi_validation_result.phi_matches)} matches")
            
            # Generate protocol using core generator
            generation_result = await self.protocol_generator.generate_protocol(
                template_id=template_id,
                study_data=phi_compliant_data,
                output_format=output_format
            )
            
            # Enhance result with compliance and configuration info
            enhanced_result = {
                **generation_result,
                "enhanced_features": {
                    "phi_compliance": {
                        "enabled": self.config.phi_compliance.enabled,
                        "level": self.config.phi_compliance.compliance_level,
                        "validation_result": phi_validation_result.to_dict() if phi_validation_result else None
                    },
                    "configuration": {
                        "config_version": self.config.config_version,
                        "template_version": self.config.template_version,
                        "customization_level": self.config.customization_level.value
                    },
                    "performance": {
                        "generation_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                        "phi_validation_time_ms": 0  # Could track separately
                    },
                    "regulatory": {
                        "frameworks": self.config.regulatory.enabled_frameworks,
                        "compliance_checking": self.config.regulatory.compliance_checking
                    }
                }
            }
            
            # Record metrics
            self._record_generation_metrics(
                template_id, output_format, 
                datetime.now() - start_time, 
                enhanced_result["success"]
            )
            
            logger.info(f"Enhanced protocol generation completed successfully")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Enhanced protocol generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "template_id": template_id,
                "output_format": output_format.value,
                "enhanced_features": {
                    "error_context": "enhanced_generation_failure"
                }
            }
    
    async def _apply_user_preferences(self, 
                                    study_data: Dict[str, Any], 
                                    user_id: str) -> Dict[str, Any]:
        """Apply user-specific preferences and custom variables."""
        try:
            # Get user preferences from config
            user_prefs = self.config.user_preferences
            
            # Apply custom variables
            enhanced_data = study_data.copy()
            for key, value in user_prefs.custom_variables.items():
                if key not in enhanced_data:
                    enhanced_data[key] = value
            
            # Apply language preferences
            if user_prefs.language != "en":
                enhanced_data["language"] = user_prefs.language
            
            return enhanced_data
            
        except Exception as e:
            logger.warning(f"Failed to apply user preferences: {str(e)}")
            return study_data
    
    async def _apply_template_config(self, 
                                   study_data: Dict[str, Any], 
                                   template_config: TemplateConfiguration) -> Dict[str, Any]:
        """Apply template-specific configuration."""
        try:
            enhanced_data = study_data.copy()
            
            # Apply variable overrides
            for key, value in template_config.variable_overrides.items():
                enhanced_data[key] = value
            
            # Apply customizations
            for key, value in template_config.customizations.items():
                enhanced_data[key] = value
            
            return enhanced_data
            
        except Exception as e:
            logger.warning(f"Failed to apply template config: {str(e)}")
            return study_data
    
    def _record_generation_metrics(self, 
                                 template_id: str, 
                                 output_format: ProtocolFormat, 
                                 duration: datetime, 
                                 success: bool):
        """Record generation metrics for monitoring."""
        metric = {
            "timestamp": datetime.now(),
            "template_id": template_id,
            "output_format": output_format.value,
            "duration_ms": duration.total_seconds() * 1000,
            "success": success,
            "config_version": self.config.config_version
        }
        
        self.generation_metrics.append(metric)
        
        # Keep only recent metrics (last 1000)
        if len(self.generation_metrics) > 1000:
            self.generation_metrics = self.generation_metrics[-1000:]
    
    def get_available_templates_enhanced(self) -> Dict[str, Any]:
        """Get enhanced template information with configuration details."""
        base_templates = self.protocol_generator.get_available_templates()
        
        enhanced_templates = {}
        for template_id, template_info in base_templates.items():
            # Get template-specific configuration
            template_config = self.config_manager.get_template_configuration(template_id)
            
            enhanced_info = {
                **template_info,
                "enhanced_features": {
                    "phi_compliance": self.config.phi_compliance.enabled,
                    "regulatory_frameworks": self.config.regulatory.enabled_frameworks,
                    "customization_level": self.config.customization_level.value,
                    "custom_configuration": template_config is not None
                }
            }
            
            if template_config:
                enhanced_info["custom_config"] = {
                    "enabled": template_config.enabled,
                    "has_customizations": len(template_config.customizations) > 0,
                    "has_variable_overrides": len(template_config.variable_overrides) > 0,
                    "has_custom_sections": len(template_config.custom_sections) > 0
                }
            
            enhanced_templates[template_id] = enhanced_info
        
        return enhanced_templates
    
    def validate_template_variables_enhanced(self, 
                                           template_id: str, 
                                           variables: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced variable validation with PHI checking."""
        # Base validation
        base_result = self.protocol_generator.validate_template_variables(template_id, variables)
        
        # PHI validation if enabled
        phi_result = None
        if self.config.phi_compliance.enabled:
            import json
            variables_text = json.dumps(variables, indent=2)
            phi_result = self.phi_validator.validate_content(
                variables_text, 
                context="template_variables"
            )
        
        return {
            **base_result,
            "phi_compliance": {
                "enabled": self.config.phi_compliance.enabled,
                "validation_result": phi_result.to_dict() if phi_result else None
            }
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        templates = self.protocol_generator.get_available_templates()
        
        # Calculate metrics
        recent_metrics = [m for m in self.generation_metrics 
                         if (datetime.now() - m["timestamp"]).total_seconds() < 3600]
        
        success_rate = (
            sum(1 for m in recent_metrics if m["success"]) / len(recent_metrics)
            if recent_metrics else 1.0
        )
        
        avg_duration = (
            sum(m["duration_ms"] for m in recent_metrics) / len(recent_metrics)
            if recent_metrics else 0
        )
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "config_version": self.config.config_version,
                "environment": self.config.environment.value,
                "phi_compliance_enabled": self.config.phi_compliance.enabled,
                "regulatory_checking": self.config.regulatory.compliance_checking
            },
            "templates": {
                "total_available": len(templates),
                "template_ids": list(templates.keys())
            },
            "performance": {
                "recent_generations": len(recent_metrics),
                "success_rate": success_rate,
                "average_duration_ms": avg_duration
            },
            "phi_compliance": {
                "enabled": self.config.phi_compliance.enabled,
                "level": self.config.phi_compliance.compliance_level,
                "validation_history": len(self.phi_validator.validation_history)
            }
        }
    
    async def batch_generate_enhanced(self, 
                                    requests: List[Dict[str, Any]],
                                    parallel_processing: bool = True) -> Dict[str, Any]:
        """Enhanced batch processing with configuration and PHI compliance."""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting enhanced batch generation of {len(requests)} protocols")
            
            # Apply batch size limits from configuration
            if len(requests) > self.config.performance.batch_size_limit:
                logger.warning(f"Batch size {len(requests)} exceeds limit {self.config.performance.batch_size_limit}")
                requests = requests[:self.config.performance.batch_size_limit]
            
            results = []
            
            if parallel_processing and self.config.performance.async_processing:
                # Parallel processing with concurrency limits
                semaphore = asyncio.Semaphore(self.config.performance.max_concurrent_requests)
                
                async def process_request(request):
                    async with semaphore:
                        return await self.generate_protocol_enhanced(**request)
                
                tasks = [process_request(request) for request in requests]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle exceptions
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append({
                            "success": False,
                            "error": str(result),
                            "request_index": i
                        })
                    else:
                        processed_results.append(result)
                results = processed_results
                
            else:
                # Sequential processing
                for request in requests:
                    result = await self.generate_protocol_enhanced(**request)
                    results.append(result)
            
            # Calculate batch statistics
            successful_count = sum(1 for r in results if r.get("success", False))
            failed_count = len(results) - successful_count
            processing_time = (datetime.now() - start_time).total_seconds()
            
            batch_result = {
                "success": True,
                "results": results,
                "batch_statistics": {
                    "total_requests": len(requests),
                    "successful_requests": successful_count,
                    "failed_requests": failed_count,
                    "processing_time_seconds": processing_time,
                    "average_time_per_request": processing_time / len(requests) if requests else 0
                },
                "enhanced_features": {
                    "parallel_processing": parallel_processing and self.config.performance.async_processing,
                    "concurrency_limit": self.config.performance.max_concurrent_requests,
                    "batch_size_limit": self.config.performance.batch_size_limit,
                    "phi_compliance_enabled": self.config.phi_compliance.enabled
                }
            }
            
            logger.info(f"Enhanced batch generation completed: {successful_count}/{len(requests)} successful")
            return batch_result
            
        except Exception as e:
            logger.error(f"Enhanced batch generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "batch_statistics": {
                    "total_requests": len(requests),
                    "successful_requests": 0,
                    "failed_requests": len(requests)
                }
            }


# Convenience function for easy integration
def create_enhanced_generator(config_name: str = "default") -> EnhancedProtocolGenerator:
    """Create enhanced protocol generator with specified configuration."""
    return EnhancedProtocolGenerator(config_name)


# Global instance for simple usage
_global_enhanced_generator: Optional[EnhancedProtocolGenerator] = None


def get_enhanced_generator() -> EnhancedProtocolGenerator:
    """Get global enhanced protocol generator instance."""
    global _global_enhanced_generator
    if _global_enhanced_generator is None:
        _global_enhanced_generator = EnhancedProtocolGenerator()
    return _global_enhanced_generator