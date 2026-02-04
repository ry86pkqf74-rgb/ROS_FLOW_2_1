"""
Stage 3: IRB Drafting Agent

Generates IRB protocol documents using the IRB Generator service.
This stage creates comprehensive IRB submission materials including:
- Protocol sections (background, objectives, study design, etc.)
- Consent form drafts
- Risk/benefit assessments
- Data management plans

See: Linear ROS-123
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import BaseTool
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = Any  # type: ignore
    PromptTemplate = Any  # type: ignore

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent
from .errors import (
    IRBValidationError,
    IRBServiceError,
    ProcessingError,
    ArtifactError,
    DependencyError
)

# Import Pydantic schemas with graceful fallback
try:
    from .schemas.irb_schemas import (
        validate_irb_config,
        IRBProtocolRequest,
        IRBValidationResult,
        StudyType
    )
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logger.warning("Pydantic schemas not available. Install with: pip install pydantic")

logger = logging.getLogger("workflow_engine.stages.stage_03_irb")


@register_stage
class IRBDraftingAgent(BaseStageAgent):
    """Stage 3: IRB Drafting Agent.

    Generates comprehensive IRB protocol documents (protocol, consent, risk/benefit,
    data management) using the TypeScript IRB Generator via ManuscriptClient.

    Inputs: StageContext (config with irb fields, previous_results).
    Outputs: StageResult with draft application, consent template, protocol summary.
    See also: StageContext, StageResult.
    """

    stage_id = 3
    stage_name = "IRB Drafting"

    def get_tools(self) -> List[BaseTool]:
        """Get LangChain tools for IRB drafting.

        Returns:
            List of LangChain tools (empty for now, can be extended)
        """
        if not LANGCHAIN_AVAILABLE:
            return []
        # Future: Could add tools for IRB database queries, compliance checking, etc.
        return []

    def get_prompt_template(self) -> PromptTemplate:
        """Get prompt template for IRB protocol generation.

        Returns:
            LangChain PromptTemplate for IRB protocol generation
        """
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        return PromptTemplate.from_template(
            "Generate IRB protocol for research study.\n\n"
            "Study Title: {study_title}\n"
            "Principal Investigator: {principal_investigator}\n"
            "Study Type: {study_type}\n"
            "Hypothesis: {hypothesis}\n"
            "Population: {population}\n"
            "Data Source: {data_source}\n"
            "Variables: {variables}\n"
            "Analysis Approach: {analysis_approach}\n"
            "{optional_fields}"
        )

    def _extract_irb_data(self, context: StageContext) -> Dict[str, Any]:
        """Extract IRB protocol data from context with fallbacks.

        Uses Pydantic validation schemas when available for robust data extraction
        and validation. Falls back to legacy extraction method if schemas unavailable.

        Args:
            context: Stage execution context

        Returns:
            Dictionary matching IrbProtocolRequest interface
        """
        # Use Pydantic validation if available
        if PYDANTIC_AVAILABLE:
            return self._extract_with_validation(context)
        
        # Fall back to legacy extraction
        return self._extract_legacy(context)
    
    def _extract_with_validation(self, context: StageContext) -> Dict[str, Any]:
        """Extract IRB data using Pydantic validation schemas.
        
        Args:
            context: Stage execution context
            
        Returns:
            Dictionary with validated IRB protocol data
            
        Raises:
            ValueError: If validation fails in strict modes
        """
        validation_result = validate_irb_config(
            config=context.config,
            previous_results=context.previous_results,
            governance_mode=context.governance_mode
        )
        
        if not validation_result.is_valid:
            if context.governance_mode == "DEMO":
                # In DEMO mode, log warnings but continue with defaults
                logger.warning(f"IRB validation warnings: {validation_result.warnings}")
                if validation_result.errors:
                    logger.warning(f"IRB validation errors (ignored in DEMO): {validation_result.errors}")
            else:
                # In LIVE/STAGING mode, raise validation errors
                raise IRBValidationError(
                    message=f"IRB validation failed: {'; '.join(validation_result.errors)}",
                    missing_fields=validation_result.missing_required_fields,
                    governance_mode=context.governance_mode,
                    irb_requirements={"errors": validation_result.errors, "warnings": validation_result.warnings}
                )
        
        # Convert Pydantic model to dict for compatibility
        if validation_result.protocol_request:
            protocol_data = validation_result.protocol_request.dict()
            # Convert back to camelCase for TypeScript service compatibility
            return {
                "studyTitle": protocol_data["study_title"],
                "principalInvestigator": protocol_data["principal_investigator"],
                "studyType": protocol_data["study_type"],
                "hypothesis": protocol_data["hypothesis"],
                "population": protocol_data["population"],
                "dataSource": protocol_data["data_source"],
                "variables": protocol_data["variables"],
                "analysisApproach": protocol_data["analysis_approach"],
                "institution": protocol_data.get("institution"),
                "expectedDuration": protocol_data.get("expected_duration"),
                "risks": protocol_data.get("risks"),
                "benefits": protocol_data.get("benefits"),
            }
        else:
            # Fallback to legacy extraction
            logger.warning("Pydantic validation failed, falling back to legacy extraction")
            return self._extract_legacy(context)
    
    def _extract_legacy(self, context: StageContext) -> Dict[str, Any]:
        """Legacy IRB data extraction method.
        
        Maintained for backward compatibility when Pydantic is not available.
        
        Args:
            context: Stage execution context
            
        Returns:
            Dictionary with IRB protocol data
        """
        irb_config = context.config.get("irb", {})
        config = context.config

        # Extract with fallbacks
        study_title = (
            irb_config.get("study_title") or
            irb_config.get("studyTitle") or
            config.get("study_title") or
            config.get("studyTitle") or
            config.get("title") or
            "Research Study"
        )

        principal_investigator = (
            irb_config.get("principal_investigator") or
            irb_config.get("principalInvestigator") or
            config.get("principal_investigator") or
            config.get("principalInvestigator") or
            config.get("pi") or
            config.get("principal_investigator_name") or
            "Principal Investigator"
        )

        # INTEGRATION: Use study type from Stage 1 ProtocolDesignAgent first
        stage1_study_type = stage1_output.get("study_type", "")
        
        study_type_raw = (
            stage1_study_type or  # Prioritize Stage 1 detection
            irb_config.get("study_type") or
            irb_config.get("studyType") or
            config.get("study_type") or
            config.get("studyType") or
            "retrospective"
        )
        
        # Enhanced study type mapping including Stage 1 types
        study_type_map = {
            "retrospective": "retrospective",
            "prospective": "prospective",
            "clinical_trial": "clinical_trial",
            "clinical trial": "clinical_trial",
            "trial": "clinical_trial",
            # Stage 1 ProtocolDesignAgent types
            "randomized_controlled_trial": "clinical_trial",
            "prospective_cohort": "prospective",
            "retrospective_cohort": "retrospective",
            "case_control": "retrospective",
            "cross_sectional": "retrospective",
            "observational": "retrospective",
        }
        study_type = study_type_map.get(study_type_raw.lower(), "retrospective")

        # INTEGRATION: Prioritize Stage 1 primary hypothesis
        stage1_hypothesis = stage1_output.get("primary_hypothesis", "")
        
        hypothesis = (
            stage1_hypothesis or  # Prioritize Stage 1 hypothesis
            irb_config.get("hypothesis") or
            config.get("hypothesis") or
            config.get("research_question") or
            config.get("researchQuestion") or
            self._extract_hypothesis_from_stages(context) or
            "To be determined"
        )

        # INTEGRATION: Prioritize Stage 1 PICO population
        stage1_population = pico_elements.get("population", "")
        
        population = (
            stage1_population or  # Prioritize Stage 1 PICO
            irb_config.get("population") or
            config.get("population") or
            config.get("study_population") or
            config.get("studyPopulation") or
            self._extract_population_from_stages(context) or
            "Study participants"
        )

        data_source = (
            irb_config.get("data_source") or
            irb_config.get("dataSource") or
            config.get("data_source") or
            config.get("dataSource") or
            self._extract_data_source_from_stages(context) or
            "Primary dataset"
        )

        # INTEGRATION: Enhanced PICO integration for Stage 1 ProtocolDesignAgent
        stage1_output = context.get_prior_stage_output(1) or {}
        pico_elements = stage1_output.get("pico_elements", {})
        stage1_complete = stage1_output.get("stage_1_complete", False)
        study_design_analysis = stage1_output.get("study_design_analysis", "")
        
        # Log PICO integration status for IRB
        if stage1_complete and pico_elements:
            logger.info(f"Using PICO data from Stage 1 for IRB protocol: {pico_elements.get('population', '')[:50]}...")
        
        variables_raw = (
            irb_config.get("variables") or
            config.get("variables") or
            config.get("study_variables") or
            config.get("studyVariables") or
            pico_elements.get("outcomes", []) or  # Use PICO outcomes as variables
            []
        )
        # Ensure variables is a list
        if isinstance(variables_raw, str):
            variables = [v.strip() for v in variables_raw.split(",")]
        elif isinstance(variables_raw, list):
            variables = variables_raw
        else:
            variables = []

        # INTEGRATION: Enhance analysis approach with Stage 1 study design context
        base_analysis = (
            irb_config.get("analysis_approach") or
            irb_config.get("analysisApproach") or
            config.get("analysis_approach") or
            config.get("analysisApproach") or
            config.get("statistical_analysis") or
            config.get("statisticalAnalysis") or
            "Statistical analysis"
        )
        
        # Enhance with Stage 1 study design insights
        if study_design_analysis and "Statistical analysis" == base_analysis:
            analysis_approach = f"Statistical analysis appropriate for {study_type_raw.replace('_', ' ')} design"
        else:
            analysis_approach = base_analysis

        # Optional fields
        institution = (
            irb_config.get("institution") or
            config.get("institution") or
            config.get("institution_name") or
            None
        )

        expected_duration = (
            irb_config.get("expected_duration") or
            irb_config.get("expectedDuration") or
            config.get("expected_duration") or
            config.get("expectedDuration") or
            config.get("study_duration") or
            None
        )

        risks_raw = (
            irb_config.get("risks") or
            config.get("risks") or
            []
        )
        if isinstance(risks_raw, str):
            risks = [r.strip() for r in risks_raw.split(",")]
        elif isinstance(risks_raw, list):
            risks = risks_raw
        else:
            risks = None

        benefits_raw = (
            irb_config.get("benefits") or
            config.get("benefits") or
            []
        )
        if isinstance(benefits_raw, str):
            benefits = [b.strip() for b in benefits_raw.split(",")]
        elif isinstance(benefits_raw, list):
            benefits = benefits_raw
        else:
            benefits = None

        return {
            "studyTitle": study_title,
            "principalInvestigator": principal_investigator,
            "studyType": study_type,
            "hypothesis": hypothesis,
            "population": population,
            "dataSource": data_source,
            "variables": variables,
            "analysisApproach": analysis_approach,
            "institution": institution,
            "expectedDuration": expected_duration,
            "risks": risks,
            "benefits": benefits,
            # PICO integration metadata
            "picoElements": pico_elements if pico_elements else None,
            "studyDesignAnalysis": study_design_analysis if study_design_analysis else None,
            "stage1Complete": stage1_complete,
        }

    def _extract_hypothesis_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract hypothesis from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Hypothesis string or None
        """
        # INTEGRATION: Check Stage 1 Protocol Design Agent output first
        stage1_output = context.get_prior_stage_output(1) or {}
        
        # Get primary hypothesis from Stage 1 Protocol Design Agent
        if stage1_output.get("primary_hypothesis"):
            return stage1_output["primary_hypothesis"]
        
        # Fallback to hypotheses dict
        stage1_hypotheses = stage1_output.get("hypotheses", {})
        if stage1_hypotheses.get("primary"):
            return stage1_hypotheses["primary"]
        
        # Check Stage 1 (Upload) for research question
        stage_1_result = context.previous_results.get(1)
        if stage_1_result and stage_1_result.output:
            output = stage_1_result.output
            if isinstance(output, dict):
                return output.get("research_question") or output.get("hypothesis")

        # Check Stage 2 (Literature) for research context
        stage_2_result = context.previous_results.get(2)
        if stage_2_result and stage_2_result.output:
            output = stage_2_result.output
            if isinstance(output, dict):
                return output.get("research_question") or output.get("hypothesis")

        return None

    def _extract_population_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract population from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Population string or None
        """
        # INTEGRATION: Check Stage 1 Protocol Design Agent PICO elements first
        stage1_output = context.get_prior_stage_output(1) or {}
        pico_elements = stage1_output.get("pico_elements", {})
        
        if pico_elements.get("population"):
            return pico_elements["population"]
        
        # Check Stage 1 (Upload) for dataset metadata
        stage_1_result = context.previous_results.get(1)
        if stage_1_result and stage_1_result.output:
            output = stage_1_result.output
            if isinstance(output, dict):
                return output.get("population") or output.get("study_population")

        return None

    def _extract_data_source_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract data source from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Data source string or None
        """
        # Check Stage 1 (Upload) for dataset info
        stage_1_result = context.previous_results.get(1)
        if stage_1_result and stage_1_result.output:
            output = stage_1_result.output
            if isinstance(output, dict):
                file_name = output.get("file_name", "")
                if file_name:
                    return f"Dataset: {file_name}"
                return output.get("data_source") or output.get("dataset_source")

        return None

    async def execute(self, context: StageContext) -> StageResult:
        """Execute IRB protocol generation.

        Args:
            context: Stage execution context

        Returns:
            StageResult with generated IRB protocol
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []
        output: Dict[str, Any] = {}

        logger.info(f"Starting IRB protocol generation for job {context.job_id}")

        try:
            # Extract IRB data from context with error handling
            try:
                irb_data = self._extract_irb_data(context)
            except Exception as e:
                raise ProcessingError(
                    message=f"Failed to extract IRB data from context: {str(e)}",
                    stage_id=3,
                    stage_name="IRB Drafting",
                    processing_step="data_extraction",
                    input_data_summary=f"Config keys: {list(context.config.keys())}"
                )

            # Validation is now handled in _extract_irb_data via Pydantic schemas
            # Legacy validation for backward compatibility
            if not PYDANTIC_AVAILABLE:
                required_fields = [
                    "studyTitle",
                    "principalInvestigator",
                    "hypothesis",
                    "population",
                    "dataSource",
                    "analysisApproach",
                ]
                missing_fields = [
                    field for field in required_fields
                    if not irb_data.get(field) or irb_data[field] == "To be determined"
                ]

                # In DEMO mode, allow missing fields with warnings
                if missing_fields and context.governance_mode == "DEMO":
                    warnings.append(
                        f"Missing required fields in DEMO mode: {', '.join(missing_fields)}. "
                        "Using default values."
                    )
                    # Fill in defaults
                    if "studyTitle" in missing_fields:
                        irb_data["studyTitle"] = "Research Study"
                    if "principalInvestigator" in missing_fields:
                        irb_data["principalInvestigator"] = "Principal Investigator"
                    if "hypothesis" in missing_fields:
                        irb_data["hypothesis"] = "To investigate the relationship between study variables and outcomes"
                    if "population" in missing_fields:
                        irb_data["population"] = "Study participants"
                    if "dataSource" in missing_fields:
                        irb_data["dataSource"] = "Primary dataset"
                    if "analysisApproach" in missing_fields:
                        irb_data["analysisApproach"] = "Statistical analysis"
                elif missing_fields:
                    errors.append(
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                    return self.create_stage_result(
                        context=context,
                        status="failed",
                        started_at=started_at,
                        errors=errors,
                        warnings=warnings,
                    )

            # Ensure variables is not empty
            if not irb_data.get("variables"):
                warnings.append("No variables specified, using default")
                irb_data["variables"] = ["Primary outcome", "Secondary outcomes"]

            logger.info(f"Generating IRB protocol for: {irb_data['studyTitle']}")

            # Generate IRB protocol using ManuscriptClient with error handling
            try:
                protocol = await self.generate_irb_protocol(
                    study_title=irb_data["studyTitle"],
                    principal_investigator=irb_data["principalInvestigator"],
                    study_type=irb_data["studyType"],
                    hypothesis=irb_data["hypothesis"],
                    population=irb_data["population"],
                    data_source=irb_data["dataSource"],
                    variables=irb_data["variables"],
                    analysis_approach=irb_data["analysisApproach"],
                    institution=irb_data.get("institution"),
                    expected_duration=irb_data.get("expectedDuration"),
                    risks=irb_data.get("risks"),
                    benefits=irb_data.get("benefits"),
                )
            except ConnectionError as e:
                # Network connectivity issues
                raise IRBServiceError(
                    message=f"IRB service connection failed: {str(e)}",
                    method_name="generate_irb_protocol",
                    is_retryable=True,
                    protocol_data_summary={
                        "study_title": irb_data["studyTitle"][:50] + "...",
                        "study_type": irb_data["studyType"],
                        "variable_count": len(irb_data.get("variables", []))
                    }
                )
            except TimeoutError as e:
                # Service timeout
                raise IRBServiceError(
                    message=f"IRB service timeout: {str(e)}",
                    method_name="generate_irb_protocol",
                    is_retryable=True
                )
            except KeyError as e:
                # Missing required service response fields
                raise ProcessingError(
                    message=f"IRB service returned incomplete response: missing {str(e)}",
                    stage_id=3,
                    stage_name="IRB Drafting",
                    processing_step="service_response_parsing"
                )

            # Store protocol in output
            output["protocol"] = protocol
            output["protocol_number"] = protocol.get("protocolNumber")
            output["generated_at"] = protocol.get("generatedAt")

            # Save protocol as JSON artifact with error handling
            try:
                os.makedirs(context.artifact_path, exist_ok=True)
                protocol_filename = f"irb_protocol_{context.job_id}.json"
                protocol_path = os.path.join(context.artifact_path, protocol_filename)

                with open(protocol_path, "w", encoding="utf-8") as f:
                    json.dump(protocol, f, indent=2, ensure_ascii=False)

                artifacts.append(protocol_path)
                output["protocol_file"] = protocol_filename
                
                logger.info(f"IRB protocol artifact saved: {protocol_filename}")
                
            except OSError as e:
                # File system errors
                raise ArtifactError(
                    message=f"Failed to save IRB protocol artifact: {str(e)}",
                    stage_id=3,
                    stage_name="IRB Drafting",
                    artifact_type="json",
                    artifact_path=protocol_path if 'protocol_path' in locals() else context.artifact_path,
                    operation="create"
                )
            except (TypeError, ValueError) as e:
                # JSON serialization errors
                raise ProcessingError(
                    message=f"Failed to serialize IRB protocol to JSON: {str(e)}",
                    stage_id=3,
                    stage_name="IRB Drafting",
                    processing_step="json_serialization"
                )

            logger.info(
                f"IRB protocol generated successfully: {protocol.get('protocolNumber')}"
            )

        except IRBValidationError as e:
            # IRB-specific validation errors
            error_msg = f"IRB data validation failed: {e.message}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            # Add validation details to metadata for debugging
            if "validation_details" not in output:
                output["validation_details"] = e.metadata
        
        except IRBServiceError as e:
            # IRB service-specific errors
            error_msg = f"IRB protocol generation service failed: {e.message}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            # Add retry information if applicable
            if e.is_retryable and e.retry_count < 3:
                warnings.append(f"IRB service error is retryable (attempt {e.retry_count + 1}/3)")
        
        except ProcessingError as e:
            # Data processing errors
            error_msg = f"IRB data processing failed: {e.message}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
        
        except ArtifactError as e:
            # Artifact creation errors
            error_msg = f"IRB artifact creation failed: {e.message}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            # Continue execution if only artifact creation failed
            warnings.append("IRB protocol generated successfully but artifact creation failed")
        
        except DependencyError as e:
            # Dependency-related errors
            error_msg = f"IRB dependency error: {e.message}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
            
            if e.install_hint:
                warnings.append(f"Resolution hint: {e.install_hint}")
        
        except ValueError as e:
            # Generic validation errors (fallback)
            error_msg = f"IRB data validation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
        
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error in IRB protocol generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

        # Create result
        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "protocol_generated": len(errors) == 0,
            },
        )
