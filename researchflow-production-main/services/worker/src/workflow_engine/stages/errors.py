"""
Custom exceptions for workflow engine stages.

This module defines specific exception types for better error categorization
and handling across different stages of the workflow.
"""

from typing import List, Optional, Dict, Any


class StageError(Exception):
    """Base exception for all stage-related errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize stage error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            error_code: Optional error code for categorization
            metadata: Optional additional error metadata
        """
        super().__init__(message)
        self.message = message
        self.stage_id = stage_id
        self.stage_name = stage_name
        self.error_code = error_code or "STAGE_ERROR"
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "message": self.message,
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "error_code": self.error_code,
            "metadata": self.metadata,
        }


class ValidationError(StageError):
    """Exception for data validation errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        missing_fields: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None,
        validation_details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            missing_fields: List of missing required fields
            invalid_fields: List of fields with invalid values
            validation_details: Additional validation details
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="VALIDATION_ERROR"
        )
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []
        self.validation_details = validation_details or {}
        
        # Add validation info to metadata
        self.metadata.update({
            "missing_fields": self.missing_fields,
            "invalid_fields": self.invalid_fields,
            "validation_details": self.validation_details,
        })


class ServiceError(StageError):
    """Exception for external service call errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        service_name: str,
        method_name: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_count: int = 0,
        is_retryable: bool = False
    ):
        """
        Initialize service error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            service_name: Name of the external service
            method_name: Method that failed (if applicable)
            status_code: HTTP status code (if applicable)
            retry_count: Number of retries attempted
            is_retryable: Whether error is retryable
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="SERVICE_ERROR"
        )
        self.service_name = service_name
        self.method_name = method_name
        self.status_code = status_code
        self.retry_count = retry_count
        self.is_retryable = is_retryable
        
        # Add service info to metadata
        self.metadata.update({
            "service_name": self.service_name,
            "method_name": self.method_name,
            "status_code": self.status_code,
            "retry_count": self.retry_count,
            "is_retryable": self.is_retryable,
        })


class ProcessingError(StageError):
    """Exception for data processing errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        processing_step: Optional[str] = None,
        input_data_summary: Optional[str] = None
    ):
        """
        Initialize processing error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            processing_step: Step where processing failed
            input_data_summary: Summary of input data (PHI-safe)
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="PROCESSING_ERROR"
        )
        self.processing_step = processing_step
        self.input_data_summary = input_data_summary
        
        # Add processing info to metadata
        self.metadata.update({
            "processing_step": self.processing_step,
            "input_data_summary": self.input_data_summary,
        })


class ConfigurationError(StageError):
    """Exception for configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[str] = None
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            config_key: Configuration key that caused the error
            expected_type: Expected configuration type
            actual_value: Actual configuration value (sanitized)
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="CONFIGURATION_ERROR"
        )
        self.config_key = config_key
        self.expected_type = expected_type
        self.actual_value = actual_value
        
        # Add config info to metadata
        self.metadata.update({
            "config_key": self.config_key,
            "expected_type": self.expected_type,
            "actual_value": self.actual_value,
        })


class ArtifactError(StageError):
    """Exception for artifact creation or handling errors."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        artifact_type: Optional[str] = None,
        artifact_path: Optional[str] = None,
        operation: Optional[str] = None
    ):
        """
        Initialize artifact error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            artifact_type: Type of artifact (e.g., 'json', 'csv', 'pdf')
            artifact_path: Path where artifact should be created
            operation: Operation that failed (e.g., 'create', 'write', 'read')
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="ARTIFACT_ERROR"
        )
        self.artifact_type = artifact_type
        self.artifact_path = artifact_path
        self.operation = operation
        
        # Add artifact info to metadata
        self.metadata.update({
            "artifact_type": self.artifact_type,
            "artifact_path": self.artifact_path,
            "operation": self.operation,
        })


class DependencyError(StageError):
    """Exception for missing dependencies or integration issues."""
    
    def __init__(
        self,
        message: str,
        stage_id: int,
        stage_name: str,
        dependency_name: str,
        dependency_type: Optional[str] = None,
        install_hint: Optional[str] = None
    ):
        """
        Initialize dependency error.
        
        Args:
            message: Error description
            stage_id: Stage identifier
            stage_name: Stage name
            dependency_name: Name of missing dependency
            dependency_type: Type of dependency (e.g., 'package', 'service', 'file')
            install_hint: Hint for installing/resolving dependency
        """
        super().__init__(
            message=message,
            stage_id=stage_id,
            stage_name=stage_name,
            error_code="DEPENDENCY_ERROR"
        )
        self.dependency_name = dependency_name
        self.dependency_type = dependency_type
        self.install_hint = install_hint
        
        # Add dependency info to metadata
        self.metadata.update({
            "dependency_name": self.dependency_name,
            "dependency_type": self.dependency_type,
            "install_hint": self.install_hint,
        })


# IRB-specific errors
class IRBValidationError(ValidationError):
    """Specific validation error for IRB protocol data."""
    
    def __init__(
        self,
        message: str,
        missing_fields: Optional[List[str]] = None,
        invalid_fields: Optional[List[str]] = None,
        governance_mode: str = "DEMO",
        irb_requirements: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize IRB validation error.
        
        Args:
            message: Error description
            missing_fields: List of missing IRB fields
            invalid_fields: List of invalid IRB fields
            governance_mode: Current governance mode
            irb_requirements: IRB-specific requirements that failed
        """
        super().__init__(
            message=message,
            stage_id=3,
            stage_name="IRB Drafting",
            missing_fields=missing_fields,
            invalid_fields=invalid_fields
        )
        
        self.governance_mode = governance_mode
        self.irb_requirements = irb_requirements or {}
        
        # Add IRB-specific metadata
        self.metadata.update({
            "governance_mode": self.governance_mode,
            "irb_requirements": self.irb_requirements,
        })


class IRBServiceError(ServiceError):
    """Specific service error for IRB protocol generation."""
    
    def __init__(
        self,
        message: str,
        method_name: Optional[str] = None,
        protocol_data_summary: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize IRB service error.
        
        Args:
            message: Error description
            method_name: IRB service method that failed
            protocol_data_summary: Summary of protocol data (PHI-safe)
            **kwargs: Additional service error parameters
        """
        super().__init__(
            message=message,
            stage_id=3,
            stage_name="IRB Drafting",
            service_name="IRB Generator",
            method_name=method_name,
            **kwargs
        )
        
        self.protocol_data_summary = protocol_data_summary or {}
        
        # Add IRB-specific metadata
        self.metadata.update({
            "protocol_data_summary": self.protocol_data_summary,
        })


def create_error_summary(errors: List[StageError]) -> Dict[str, Any]:
    """
    Create a summary of multiple stage errors.
    
    Args:
        errors: List of StageError instances
        
    Returns:
        Dictionary with error summary statistics and categorization
    """
    if not errors:
        return {"total_errors": 0, "categories": {}}
    
    categories = {}
    by_stage = {}
    
    for error in errors:
        # Categorize by error code
        if error.error_code not in categories:
            categories[error.error_code] = []
        categories[error.error_code].append(error.to_dict())
        
        # Group by stage
        stage_key = f"stage_{error.stage_id}"
        if stage_key not in by_stage:
            by_stage[stage_key] = []
        by_stage[stage_key].append(error.to_dict())
    
    return {
        "total_errors": len(errors),
        "categories": categories,
        "by_stage": by_stage,
        "most_common_error": max(categories.keys(), key=lambda k: len(categories[k])) if categories else None,
    }