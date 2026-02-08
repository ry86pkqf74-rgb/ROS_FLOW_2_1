"""Stage 4b: Dataset Validation using Pandera
Validates datasets using Pandera DataFrameSchema, catches SchemaErrors, generates validation reports."""

import json
import logging
import os
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


@register_stage
class DatasetValidationAgent(BaseStageAgent):
    """Stage 4b: Dataset Validation using Pandera."""
    
    stage_id = "4b"
    stage_name = "Dataset Validation"
    
    async def execute(self, context: StageContext) -> StageResult:
        """Execute dataset validation using Pandera."""
        started_at = datetime.utcnow().isoformat() + "Z"
        
        try:
            dataset_path = self._get_dataset_path(context)
            if not dataset_path:
                return self.create_stage_result(context=context, status="failed",
                    errors=["Dataset path not found"], started_at=started_at)
            
            schema = self._define_schema(dataset_path)
            validation_result = self._validate_dataset(dataset_path, schema)
            
            output = {"validation_result": validation_result.__dict__}
            
            # Feature-flagged: Optional bias detection during dataset validation
            if os.getenv("ENABLE_BIAS_DETECTION_STAGE4B", "false").lower() == "true":
                try:
                    bias_result = await self._run_bias_detection(context, dataset_path, validation_result)
                    if bias_result:
                        output["bias_detection"] = bias_result
                        logger.info(f"Bias detection completed for stage 4b: {bias_result.get('bias_verdict', 'N/A')}")
                except Exception as e:
                    logger.warning(f"Bias detection failed (non-blocking): {str(e)}")
            
            status = "completed" if validation_result.valid_rows > 0 else "failed"
            return self.create_stage_result(context=context, status=status, output=output,
                errors=validation_result.schema_errors, warnings=validation_result.warnings,
                started_at=started_at, artifacts=[str(dataset_path)])
                
        except Exception as e:
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
            warnings = [f"Potential PHI columns: {phi_columns}"] if phi_columns else []
            
            try:
                validated_df = schema.validate(df)
                return ValidationResult(valid_rows=len(validated_df), invalid_rows=0, 
                    total_rows=total_rows, column_issues={}, schema_errors=[], warnings=warnings,
                    validation_summary=f"All {total_rows} rows passed validation", file_format=file_format)
            except pa.errors.SchemaErrors as e:
                valid_rows = max(0, total_rows - len(e.failure_cases))
                invalid_rows = len(e.failure_cases)
                column_issues = self._extract_column_issues(e)
                schema_errors = [str(error)[:200] for error in e.schema_errors[:5]]
                return ValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows, 
                    total_rows=total_rows, column_issues=column_issues, schema_errors=schema_errors,
                    warnings=warnings, validation_summary=f"{valid_rows}/{total_rows} rows valid", file_format=file_format)
            except pa.errors.SchemaError as e:
                return ValidationResult(valid_rows=0, invalid_rows=total_rows, total_rows=total_rows,
                    column_issues={"schema": [str(e)[:200]]}, schema_errors=[str(e)[:200]],
                    warnings=warnings, validation_summary=f"Schema validation failed", file_format=file_format)
        except Exception as e:
            return ValidationResult(valid_rows=0, invalid_rows=0, total_rows=0,
                column_issues={"loading": [f"Failed to load: {str(e)[:200]}"]},
                schema_errors=[f"Loading failed: {str(e)[:200]}"], warnings=[],
                validation_summary=f"Validation failed: {str(e)[:100]}", file_format="unknown")
    
    def _extract_column_issues(self, schema_errors: pa.errors.SchemaErrors) -> Dict[str, List[str]]:
        """Extract column-specific issues from SchemaErrors."""
        column_issues = {}
        for error in schema_errors.schema_errors[:10]:
            col = str(error.column) if hasattr(error, 'column') and error.column else "general"
            column_issues.setdefault(col, []).append(str(error)[:200])
        return column_issues
    
    async def _run_bias_detection(self, context: StageContext, dataset_path: str, validation_result: ValidationResult) -> Optional[Dict[str, Any]]:
        """Run bias detection agent (feature-flagged, non-blocking).
        
        Args:
            context: Stage context
            dataset_path: Path to validated dataset
            validation_result: Pandera validation result
            
        Returns:
            Bias detection results or None if disabled/failed
        """
        try:
            import httpx
            
            # Build dataset summary for bias detection
            dataset_summary = f"Clinical dataset with {validation_result.total_rows} rows, {len(validation_result.column_issues)} columns"
            
            # Call orchestrator AI router for bias detection
            orchestrator_url = os.getenv("ORCHESTRATOR_INTERNAL_URL", "http://orchestrator:3001")
            service_token = os.getenv("WORKER_SERVICE_TOKEN", "")
            
            payload = {
                "task_type": "CLINICAL_BIAS_DETECTION",
                "request_id": f"{context.run_id}-stage4b-bias",
                "workflow_id": context.run_id,
                "mode": context.config.get("mode", "DEMO"),
                "inputs": {
                    "dataset_summary": dataset_summary,
                    "sample_size": validation_result.total_rows,
                    "generate_report": True
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{orchestrator_url}/api/ai/router/dispatch",
                    json=payload,
                    headers={"Authorization": f"Bearer {service_token}"}
                )
                
                if response.status_code == 200:
                    dispatch_result = response.json()
                    
                    # Write artifact
                    artifact_dir = Path(f"/data/artifacts/{context.run_id}/bias_detection/stage_4b")
                    artifact_dir.mkdir(parents=True, exist_ok=True)
                    
                    report_path = artifact_dir / "report.json"
                    with open(report_path, "w") as f:
                        json.dump(dispatch_result, f, indent=2)
                    
                    logger.info(f"Bias detection artifact written to {report_path}")
                    return dispatch_result
                else:
                    logger.warning(f"Bias detection dispatch failed: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Bias detection error (non-blocking): {str(e)}")
            return None
    
    def get_tools(self) -> List[Any]:
        return []  # No external tools needed for pure data validation
    
    def get_prompt_template(self) -> Any:
        try:
            from langchain_core.prompts import PromptTemplate
            return PromptTemplate.from_template("Dataset validation - no AI required")
        except ImportError:
            return None