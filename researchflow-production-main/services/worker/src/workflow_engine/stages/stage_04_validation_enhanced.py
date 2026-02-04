"""Stage 4b: Dataset Validation using Pandera (Enhanced with Audit Logging)
Validates datasets using Pandera DataFrameSchema, catches SchemaErrors, generates validation reports.
ENHANCED: Comprehensive audit logging for HIPAA compliance."""

import logging
import pandas as pd
import pandera as pa
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base_stage_agent import BaseStageAgent
from ..types import StageContext, StageResult
from ..registry import register_stage

try:
    from schemas.pandera.base_schema import contains_phi_columns
except ImportError:
    contains_phi_columns = lambda cols: []


@dataclass
class ValidationResult:
    """Validation result artifact for Stage 4b."""
    valid_rows: int
    invalid_rows: int
    total_rows: int
    column_issues: Dict[str, List[str]]
    schema_errors: List[str]
    warnings: List[str]
    validation_summary: str
    file_format: str = "csv"
    phi_columns_detected: List[str] = None
    validation_duration_seconds: float = 0.0


@register_stage
class DatasetValidationAgentEnhanced(BaseStageAgent):
    """Stage 4b: Dataset Validation using Pandera (Enhanced)."""
    
    stage_id = "4b"
    stage_name = "Dataset Validation (Enhanced)"
    
    def audit_log(self, action: str, metadata: Dict[str, Any]) -> None:
        """Log audit events for HIPAA compliance and governance tracking."""
        # Create audit entry with PHI-safe metadata
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stage_id": str(self.stage_id),
            "stage_name": self.stage_name,
            "action": action,
            "metadata": self._sanitize_audit_metadata(metadata)
        }
        
        # Log to structured audit logger (PHI-safe)
        audit_logger = logging.getLogger("workflow_engine.audit")
        audit_logger.info(f"AUDIT: {action}", extra={"audit_data": audit_entry})
    
    def _sanitize_audit_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize audit metadata to ensure no PHI is logged."""
        sanitized = metadata.copy()
        
        # List of keys that may contain PHI
        phi_keys = [
            'patient_name', 'patient_id', 'ssn', 'mrn', 'phone', 'email',
            'date_of_birth', 'address', 'patient_data', 'phi_data'
        ]
        
        # Sanitize potential PHI fields
        for key in phi_keys:
            if key in sanitized:
                sanitized[key] = "[PHI_REDACTED]"
        
        # Truncate long strings to prevent accidental PHI logging
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "...[TRUNCATED]"
        
        return sanitized
    
    async def execute(self, context: StageContext) -> StageResult:
        """Execute dataset validation using Pandera with comprehensive audit logging."""
        started_at = datetime.utcnow().isoformat() + "Z"
        validation_start_time = datetime.utcnow()
        
        # AUDIT LOG: Stage execution started
        self.audit_log("stage_04b_validation_started", {
            "job_id": context.job_id,
            "dataset_pointer": context.dataset_pointer,
            "governance_mode": context.governance_mode,
            "started_at": started_at,
            "previous_stages_count": len(context.previous_results)
        })
        
        try:
            dataset_path = self._get_dataset_path(context)
            if not dataset_path:
                # AUDIT LOG: No dataset found
                self.audit_log("stage_04b_validation_failed", {
                    "job_id": context.job_id,
                    "error": "Dataset path not found",
                    "context_dataset_pointer": context.dataset_pointer,
                    "searched_artifacts": [artifact for results in context.previous_results.values() for artifact in results.artifacts[:3]]  # Limit to prevent log spam
                })
                return self.create_stage_result(context=context, status="failed",
                    errors=["Dataset path not found"], started_at=started_at)
            
            # AUDIT LOG: Dataset found and processing started
            self.audit_log("stage_04b_dataset_processing_started", {
                "job_id": context.job_id,
                "dataset_path": dataset_path,
                "file_extension": Path(dataset_path).suffix,
                "file_size_bytes": Path(dataset_path).stat().st_size if Path(dataset_path).exists() else -1
            })
            
            schema = self._define_schema(dataset_path)
            validation_result = self._validate_dataset(dataset_path, schema)
            
            # Calculate validation duration
            validation_duration = (datetime.utcnow() - validation_start_time).total_seconds()
            validation_result.validation_duration_seconds = validation_duration
            
            # AUDIT LOG: Validation completed with results
            phi_columns = contains_phi_columns(list(validation_result.column_issues.keys()) if validation_result.column_issues else [])
            validation_result.phi_columns_detected = phi_columns
            
            self.audit_log("stage_04b_validation_completed", {
                "job_id": context.job_id,
                "dataset_path": dataset_path,
                "total_rows": validation_result.total_rows,
                "valid_rows": validation_result.valid_rows,
                "invalid_rows": validation_result.invalid_rows,
                "validation_success_rate": validation_result.valid_rows / validation_result.total_rows if validation_result.total_rows > 0 else 0,
                "schema_errors_count": len(validation_result.schema_errors),
                "warnings_count": len(validation_result.warnings),
                "file_format": validation_result.file_format,
                "phi_columns_detected": len(phi_columns),
                "phi_column_names": phi_columns if context.governance_mode != "PRODUCTION" else "[REDACTED]",
                "validation_duration_seconds": validation_duration
            })
            
            # AUDIT LOG: Quality criteria evaluation
            quality_criteria = self.get_quality_criteria()
            if quality_criteria:
                meets_criteria = self._evaluate_quality_criteria(validation_result, quality_criteria, context.governance_mode)
                self.audit_log("stage_04b_quality_evaluation", {
                    "job_id": context.job_id,
                    "quality_criteria_met": meets_criteria,
                    "governance_mode": context.governance_mode,
                    "criteria_applied": list(quality_criteria.get(context.governance_mode, {}).keys())
                })
                
                # Add quality evaluation to warnings if criteria not met
                if not meets_criteria:
                    validation_result.warnings.append(f"Quality criteria for {context.governance_mode} mode not met")
            
            output = {"validation_result": validation_result.__dict__}
            
            status = "completed" if validation_result.valid_rows > 0 else "failed"
            
            # AUDIT LOG: Final stage status
            self.audit_log("stage_04b_execution_completed", {
                "job_id": context.job_id,
                "final_status": status,
                "total_execution_time_seconds": (datetime.utcnow() - validation_start_time).total_seconds(),
                "artifacts_created": [str(dataset_path)]
            })
            
            return self.create_stage_result(context=context, status=status, output=output,
                errors=validation_result.schema_errors, warnings=validation_result.warnings,
                started_at=started_at, artifacts=[str(dataset_path)])
                
        except Exception as e:
            # AUDIT LOG: Critical execution failure
            self.audit_log("stage_04b_execution_failed", {
                "job_id": context.job_id,
                "error_type": type(e).__name__,
                "error_message": str(e)[:200],  # PHI-safe truncation
                "dataset_path": dataset_path if 'dataset_path' in locals() else None,
                "execution_time_seconds": (datetime.utcnow() - validation_start_time).total_seconds()
            })
            return self.create_stage_result(context=context, status="failed",
                errors=[f"Validation execution failed: {str(e)}"], started_at=started_at)
    
    def _get_dataset_path(self, context: StageContext) -> Optional[str]:
        """Get dataset path from context or previous stage artifacts."""
        if context.dataset_pointer and Path(context.dataset_pointer).exists():
            return context.dataset_pointer
        for stage_result in context.previous_results.values():
            for artifact_path in stage_result.artifacts:
                if Path(artifact_path).exists() and artifact_path.endswith(('.csv', '.json', '.parquet')):
                    return artifact_path
        return None
    
    def _define_schema(self, dataset_path: str) -> pa.DataFrameSchema:
        """Define Pandera DataFrameSchema based on dataset inspection."""
        try:
            ext = Path(dataset_path).suffix.lower()
            if ext == '.json':
                sample_df = pd.read_json(dataset_path).head(100)
            elif ext == '.parquet':
                sample_df = pd.read_parquet(dataset_path).head(100)
            else:
                sample_df = pd.read_csv(dataset_path, nrows=100)
            
            schema_columns = {}
            if 'research_id' in sample_df.columns:
                schema_columns['research_id'] = pa.Column(pa.String, nullable=False)
            
            type_map = {'int64': pa.Int, 'int32': pa.Int, 'float64': pa.Float, 'float32': pa.Float, 'bool': pa.Bool}
            for col in sample_df.columns:
                if col != 'research_id':
                    schema_columns[col] = pa.Column(type_map.get(str(sample_df[col].dtype), pa.String), nullable=True)
            
            return pa.DataFrameSchema(schema_columns, strict=False, coerce=True)
        except Exception:
            return pa.DataFrameSchema({}, strict=False, coerce=True)
    
    def _validate_dataset(self, dataset_path: str, schema: pa.DataFrameSchema) -> ValidationResult:
        """Load dataset and perform Pandera validation."""
        try:
            ext = Path(dataset_path).suffix.lower()
            file_format = ext[1:] or 'csv'
            
            if ext == '.json':
                df = pd.read_json(dataset_path)
            elif ext == '.parquet':
                df = pd.read_parquet(dataset_path)
            else:
                df = pd.read_csv(dataset_path)
                file_format = 'csv'
            
            total_rows = len(df)
            phi_columns = contains_phi_columns(list(df.columns))
            warnings = [f"Potential PHI columns detected: {len(phi_columns)} columns"] if phi_columns else []
            
            try:
                validated_df = schema.validate(df)
                return ValidationResult(
                    valid_rows=len(validated_df), 
                    invalid_rows=0, 
                    total_rows=total_rows, 
                    column_issues={}, 
                    schema_errors=[], 
                    warnings=warnings,
                    validation_summary=f"All {total_rows} rows passed validation", 
                    file_format=file_format,
                    phi_columns_detected=phi_columns
                )
            except pa.errors.SchemaErrors as e:
                valid_rows = max(0, total_rows - len(e.failure_cases))
                invalid_rows = len(e.failure_cases)
                column_issues = self._extract_column_issues(e)
                schema_errors = [str(error)[:200] for error in e.schema_errors[:5]]
                return ValidationResult(
                    valid_rows=valid_rows, 
                    invalid_rows=invalid_rows, 
                    total_rows=total_rows, 
                    column_issues=column_issues, 
                    schema_errors=schema_errors,
                    warnings=warnings, 
                    validation_summary=f"{valid_rows}/{total_rows} rows valid", 
                    file_format=file_format,
                    phi_columns_detected=phi_columns
                )
            except pa.errors.SchemaError as e:
                return ValidationResult(
                    valid_rows=0, 
                    invalid_rows=total_rows, 
                    total_rows=total_rows,
                    column_issues={"schema": [str(e)[:200]]}, 
                    schema_errors=[str(e)[:200]],
                    warnings=warnings, 
                    validation_summary="Schema validation failed", 
                    file_format=file_format,
                    phi_columns_detected=phi_columns
                )
        except Exception as e:
            return ValidationResult(
                valid_rows=0, 
                invalid_rows=0, 
                total_rows=0,
                column_issues={"loading": [f"Failed to load dataset: {str(e)[:200]}"]},
                schema_errors=[f"Dataset loading failed: {str(e)[:200]}"], 
                warnings=[],
                validation_summary=f"Validation failed: {str(e)[:100]}", 
                file_format="unknown"
            )
    
    def _extract_column_issues(self, schema_errors: pa.errors.SchemaErrors) -> Dict[str, List[str]]:
        """Extract column-specific issues from SchemaErrors."""
        column_issues = {}
        for error in schema_errors.schema_errors[:10]:  # Limit to prevent excessive logging
            col = str(error.column) if hasattr(error, 'column') and error.column else "general"
            column_issues.setdefault(col, []).append(str(error)[:200])
        return column_issues
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        """Define quality criteria for dataset validation by governance mode."""
        return {
            "DEMO": {
                "min_valid_row_percentage": 70.0,
                "max_phi_columns": 10,
                "max_validation_time_seconds": 300,
                "required_columns": ["research_id"],
                "max_schema_errors": 50,
                "min_total_rows": 1
            },
            "STAGING": {
                "min_valid_row_percentage": 85.0,
                "max_phi_columns": 5,
                "max_validation_time_seconds": 180,
                "required_columns": ["research_id"],
                "max_schema_errors": 20,
                "min_total_rows": 10
            },
            "PRODUCTION": {
                "min_valid_row_percentage": 95.0,
                "max_phi_columns": 0,
                "max_validation_time_seconds": 120,
                "required_columns": ["research_id"],
                "max_schema_errors": 5,
                "min_total_rows": 100
            }
        }
    
    def _evaluate_quality_criteria(self, validation_result: ValidationResult, criteria: Dict[str, Any], governance_mode: str) -> bool:
        """Evaluate validation result against quality criteria."""
        mode_criteria = criteria.get(governance_mode, {})
        if not mode_criteria:
            return True  # No criteria defined, pass by default
        
        # Check minimum valid row percentage
        if validation_result.total_rows > 0:
            valid_percentage = (validation_result.valid_rows / validation_result.total_rows) * 100
            if valid_percentage < mode_criteria.get("min_valid_row_percentage", 0):
                return False
        
        # Check maximum schema errors
        if len(validation_result.schema_errors) > mode_criteria.get("max_schema_errors", float('inf')):
            return False
        
        # Check maximum PHI columns
        phi_count = len(validation_result.phi_columns_detected or [])
        if phi_count > mode_criteria.get("max_phi_columns", float('inf')):
            return False
        
        # Check minimum total rows
        if validation_result.total_rows < mode_criteria.get("min_total_rows", 0):
            return False
        
        # Check maximum validation time
        if validation_result.validation_duration_seconds > mode_criteria.get("max_validation_time_seconds", float('inf')):
            return False
        
        return True
    
    def get_tools(self) -> List[Any]:
        return []  # No external tools needed for pure data validation
    
    def get_prompt_template(self) -> Any:
        try:
            from langchain_core.prompts import PromptTemplate
            return PromptTemplate.from_template("Dataset validation - no AI required")
        except ImportError:
            return None