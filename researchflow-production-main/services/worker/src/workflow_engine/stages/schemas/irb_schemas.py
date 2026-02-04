"""
Pydantic schemas for IRB Stage data validation.

This module provides data validation schemas for Stage 3 IRB Drafting Agent,
ensuring proper type checking and validation of IRB protocol request data.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class StudyType(str, Enum):
    """Allowed study types for IRB protocols."""
    RETROSPECTIVE = "retrospective"
    PROSPECTIVE = "prospective"
    CLINICAL_TRIAL = "clinical_trial"


class VulnerablePopulation(str, Enum):
    """Vulnerable populations requiring additional protections."""
    CHILDREN = "children"
    PRISONERS = "prisoners"
    PREGNANT_WOMEN = "pregnant_women"
    COGNITIVE_IMPAIRMENT = "cognitive_impairment"
    ECONOMICALLY_DISADVANTAGED = "economically_disadvantaged"


class IRBRiskLevel(str, Enum):
    """IRB risk level classifications."""
    MINIMAL = "minimal"
    GREATER_THAN_MINIMAL = "greater_than_minimal"


class IRBReviewType(str, Enum):
    """IRB review type categories."""
    EXEMPT = "exempt"
    EXPEDITED = "expedited"
    FULL_BOARD = "full_board"


class IRBProtocolRequest(BaseModel):
    """
    Pydantic model for IRB protocol generation requests.
    
    Validates all required and optional fields for IRB protocol creation,
    matching the TypeScript IrbProtocolRequest interface.
    """
    
    # Required fields
    study_title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Title of the research study"
    )
    
    principal_investigator: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the principal investigator"
    )
    
    study_type: StudyType = Field(
        ...,
        description="Type of study design"
    )
    
    hypothesis: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Research hypothesis or research question"
    )
    
    population: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Description of study population"
    )
    
    data_source: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Description of data source"
    )
    
    variables: List[str] = Field(
        ...,
        min_items=1,
        description="List of variables to be collected or analyzed"
    )
    
    analysis_approach: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Statistical analysis approach"
    )
    
    # Optional fields
    institution: Optional[str] = Field(
        None,
        max_length=100,
        description="Institution name"
    )
    
    expected_duration: Optional[str] = Field(
        None,
        max_length=50,
        description="Expected duration of the study"
    )
    
    risks: Optional[List[str]] = Field(
        None,
        description="List of potential risks"
    )
    
    benefits: Optional[List[str]] = Field(
        None,
        description="List of potential benefits"
    )
    
    vulnerable_populations: Optional[List[VulnerablePopulation]] = Field(
        None,
        description="Vulnerable populations involved in the study"
    )
    
    expected_risk_level: Optional[IRBRiskLevel] = Field(
        None,
        description="Expected IRB risk level classification"
    )
    
    expected_review_type: Optional[IRBReviewType] = Field(
        None,
        description="Expected IRB review type"
    )
    
    @validator('variables', each_item=True)
    def validate_variable_names(cls, v):
        """Validate individual variable names."""
        if not v.strip():
            raise ValueError("Variable names cannot be empty")
        if len(v.strip()) > 100:
            raise ValueError("Variable names must be less than 100 characters")
        return v.strip()
    
    @validator('risks', each_item=True, pre=True, always=True)
    def validate_risks(cls, v):
        """Validate risk descriptions."""
        if v and len(v.strip()) > 200:
            raise ValueError("Risk descriptions must be less than 200 characters")
        return v.strip() if v else None
    
    @validator('benefits', each_item=True, pre=True, always=True)
    def validate_benefits(cls, v):
        """Validate benefit descriptions."""
        if v and len(v.strip()) > 200:
            raise ValueError("Benefit descriptions must be less than 200 characters")
        return v.strip() if v else None
    
    @validator('principal_investigator')
    def validate_pi_name(cls, v):
        """Validate principal investigator name format."""
        if not any(char.isalpha() for char in v):
            raise ValueError("Principal investigator name must contain letters")
        return v.strip()
    
    @validator('study_title')
    def validate_study_title(cls, v):
        """Validate study title format."""
        if v.lower().strip() in ['test', 'study', 'research']:
            raise ValueError("Study title must be more descriptive than generic terms")
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        validate_assignment = True


class IRBConfigExtraction(BaseModel):
    """
    Model for extracting IRB configuration from various sources.
    
    Handles data extraction from context.config with fallbacks to
    different naming conventions and prior stage outputs.
    """
    
    # Direct IRB config
    irb_config: Optional[dict] = Field(None, description="Direct IRB configuration")
    
    # Root-level config fallbacks
    study_title: Optional[str] = None
    title: Optional[str] = None
    principal_investigator: Optional[str] = None
    pi: Optional[str] = None
    principal_investigator_name: Optional[str] = None
    study_type: Optional[str] = None
    hypothesis: Optional[str] = None
    research_question: Optional[str] = None
    population: Optional[str] = None
    study_population: Optional[str] = None
    data_source: Optional[str] = None
    dataset_source: Optional[str] = None
    variables: Optional[List[str]] = None
    study_variables: Optional[List[str]] = None
    analysis_approach: Optional[str] = None
    statistical_analysis: Optional[str] = None
    institution: Optional[str] = None
    institution_name: Optional[str] = None
    expected_duration: Optional[str] = None
    study_duration: Optional[str] = None
    risks: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    
    # Stage 1 PICO integration
    stage1_output: Optional[dict] = None
    
    def extract_to_protocol_request(self) -> IRBProtocolRequest:
        """
        Extract and normalize data to IRBProtocolRequest.
        
        Returns:
            IRBProtocolRequest with normalized and validated data
            
        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Get IRB-specific config or fall back to root level
        irb_data = self.irb_config or {}
        
        # Extract study title with fallbacks
        study_title = (
            irb_data.get("study_title") or
            irb_data.get("studyTitle") or
            self.study_title or
            self.title or
            "Research Study"
        )
        
        # Extract principal investigator with fallbacks
        principal_investigator = (
            irb_data.get("principal_investigator") or
            irb_data.get("principalInvestigator") or
            self.principal_investigator or
            self.pi or
            self.principal_investigator_name or
            "Principal Investigator"
        )
        
        # Extract and normalize study type
        study_type_raw = (
            irb_data.get("study_type") or
            irb_data.get("studyType") or
            self.study_type or
            "retrospective"
        )
        
        # Normalize study type
        study_type_map = {
            "retrospective": StudyType.RETROSPECTIVE,
            "prospective": StudyType.PROSPECTIVE,
            "clinical_trial": StudyType.CLINICAL_TRIAL,
            "clinical trial": StudyType.CLINICAL_TRIAL,
            "trial": StudyType.CLINICAL_TRIAL,
        }
        study_type = study_type_map.get(study_type_raw.lower(), StudyType.RETROSPECTIVE)
        
        # Extract hypothesis with Stage 1 integration
        hypothesis = (
            irb_data.get("hypothesis") or
            self.hypothesis or
            self.research_question or
            self._extract_hypothesis_from_stage1() or
            "To be determined"
        )
        
        # Extract population with Stage 1 PICO integration
        population = (
            irb_data.get("population") or
            self.population or
            self.study_population or
            self._extract_population_from_stage1() or
            "Study participants"
        )
        
        # Extract data source
        data_source = (
            irb_data.get("data_source") or
            irb_data.get("dataSource") or
            self.data_source or
            self.dataset_source or
            "Primary dataset"
        )
        
        # Extract variables with Stage 1 PICO integration
        variables_raw = (
            irb_data.get("variables") or
            self.variables or
            self.study_variables or
            self._extract_variables_from_stage1() or
            ["Primary outcome", "Secondary outcomes"]
        )
        
        # Ensure variables is a list
        if isinstance(variables_raw, str):
            variables = [v.strip() for v in variables_raw.split(",")]
        else:
            variables = list(variables_raw)
        
        # Extract analysis approach
        analysis_approach = (
            irb_data.get("analysis_approach") or
            irb_data.get("analysisApproach") or
            self.analysis_approach or
            self.statistical_analysis or
            "Statistical analysis"
        )
        
        # Extract optional fields
        institution = (
            irb_data.get("institution") or
            self.institution or
            self.institution_name
        )
        
        expected_duration = (
            irb_data.get("expected_duration") or
            irb_data.get("expectedDuration") or
            self.expected_duration or
            self.study_duration
        )
        
        # Process risks and benefits
        risks = self._process_list_field(irb_data.get("risks") or self.risks)
        benefits = self._process_list_field(irb_data.get("benefits") or self.benefits)
        
        return IRBProtocolRequest(
            study_title=study_title,
            principal_investigator=principal_investigator,
            study_type=study_type,
            hypothesis=hypothesis,
            population=population,
            data_source=data_source,
            variables=variables,
            analysis_approach=analysis_approach,
            institution=institution,
            expected_duration=expected_duration,
            risks=risks,
            benefits=benefits
        )
    
    def _extract_hypothesis_from_stage1(self) -> Optional[str]:
        """Extract hypothesis from Stage 1 PICO output."""
        if not self.stage1_output:
            return None
            
        # Try primary_hypothesis first
        if self.stage1_output.get("primary_hypothesis"):
            return self.stage1_output["primary_hypothesis"]
        
        # Try hypotheses dict
        hypotheses = self.stage1_output.get("hypotheses", {})
        if hypotheses.get("primary"):
            return hypotheses["primary"]
            
        return None
    
    def _extract_population_from_stage1(self) -> Optional[str]:
        """Extract population from Stage 1 PICO elements."""
        if not self.stage1_output:
            return None
            
        pico_elements = self.stage1_output.get("pico_elements", {})
        return pico_elements.get("population")
    
    def _extract_variables_from_stage1(self) -> Optional[List[str]]:
        """Extract variables from Stage 1 PICO outcomes."""
        if not self.stage1_output:
            return None
            
        pico_elements = self.stage1_output.get("pico_elements", {})
        outcomes = pico_elements.get("outcomes", [])
        
        if isinstance(outcomes, list) and len(outcomes) > 0:
            return outcomes
            
        return None
    
    def _process_list_field(self, field_value) -> Optional[List[str]]:
        """Process a field that can be string or list into a list."""
        if not field_value:
            return None
            
        if isinstance(field_value, str):
            return [item.strip() for item in field_value.split(",") if item.strip()]
        elif isinstance(field_value, list):
            return [str(item).strip() for item in field_value if str(item).strip()]
        else:
            return None


class IRBStageConfig(BaseModel):
    """
    Configuration schema for Stage 3 IRB Drafting Agent.
    
    Defines the expected structure for IRB-related configuration
    within the StageContext.config dictionary.
    """
    
    # Basic study information
    study_title: Optional[str] = Field(None, description="Title of the research study")
    principal_investigator: Optional[str] = Field(None, description="Name of the PI")
    study_type: Optional[str] = Field(None, description="Type of study design")
    
    # Research components
    hypothesis: Optional[str] = Field(None, description="Research hypothesis")
    population: Optional[str] = Field(None, description="Study population description")
    data_source: Optional[str] = Field(None, description="Data source description")
    variables: Optional[List[str]] = Field(None, description="Study variables")
    analysis_approach: Optional[str] = Field(None, description="Analysis methodology")
    
    # Optional details
    institution: Optional[str] = Field(None, description="Institution name")
    expected_duration: Optional[str] = Field(None, description="Study duration")
    risks: Optional[List[str]] = Field(None, description="Potential risks")
    benefits: Optional[List[str]] = Field(None, description="Potential benefits")
    
    # IRB-specific fields
    irb_number: Optional[str] = Field(None, description="Existing IRB number if any")
    review_type: Optional[IRBReviewType] = Field(None, description="Expected review type")
    vulnerable_populations: Optional[List[VulnerablePopulation]] = Field(
        None, description="Vulnerable populations involved"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "allow"  # Allow additional fields for flexibility


class IRBValidationResult(BaseModel):
    """
    Result of IRB data validation.
    
    Contains validation status, errors, and the validated protocol request.
    """
    
    is_valid: bool = Field(..., description="Whether validation passed")
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )
    
    protocol_request: Optional[IRBProtocolRequest] = Field(
        None,
        description="Validated protocol request if validation passed"
    )
    
    missing_required_fields: List[str] = Field(
        default_factory=list,
        description="List of missing required fields"
    )
    
    applied_defaults: List[str] = Field(
        default_factory=list,
        description="List of fields where defaults were applied"
    )


def validate_irb_config(
    config: dict,
    previous_results: dict,
    governance_mode: str = "DEMO"
) -> IRBValidationResult:
    """
    Validate IRB configuration data with fallbacks and mode-specific behavior.
    
    Args:
        config: Configuration dictionary from StageContext
        previous_results: Previous stage results for integration
        governance_mode: Current governance mode (DEMO, LIVE, etc.)
        
    Returns:
        IRBValidationResult with validation status and details
    """
    errors = []
    warnings = []
    applied_defaults = []
    
    try:
        # Get Stage 1 output for integration
        stage1_output = None
        if 1 in previous_results:
            stage1_output = previous_results[1].output
        
        # Create extraction model
        extractor = IRBConfigExtraction(
            irb_config=config.get("irb"),
            study_title=config.get("study_title"),
            title=config.get("title"),
            principal_investigator=config.get("principal_investigator"),
            pi=config.get("pi"),
            principal_investigator_name=config.get("principal_investigator_name"),
            study_type=config.get("study_type"),
            hypothesis=config.get("hypothesis"),
            research_question=config.get("research_question"),
            population=config.get("population"),
            study_population=config.get("study_population"),
            data_source=config.get("data_source"),
            dataset_source=config.get("dataset_source"),
            variables=config.get("variables"),
            study_variables=config.get("study_variables"),
            analysis_approach=config.get("analysis_approach"),
            statistical_analysis=config.get("statistical_analysis"),
            institution=config.get("institution"),
            institution_name=config.get("institution_name"),
            expected_duration=config.get("expected_duration"),
            study_duration=config.get("study_duration"),
            risks=config.get("risks"),
            benefits=config.get("benefits"),
            stage1_output=stage1_output
        )
        
        # Extract to protocol request
        protocol_request = extractor.extract_to_protocol_request()
        
        # Check for defaults applied
        if protocol_request.study_title == "Research Study":
            applied_defaults.append("study_title")
        if protocol_request.principal_investigator == "Principal Investigator":
            applied_defaults.append("principal_investigator")
        if protocol_request.hypothesis == "To be determined":
            applied_defaults.append("hypothesis")
        if protocol_request.population == "Study participants":
            applied_defaults.append("population")
        if protocol_request.data_source == "Primary dataset":
            applied_defaults.append("data_source")
        if protocol_request.analysis_approach == "Statistical analysis":
            applied_defaults.append("analysis_approach")
        
        # Mode-specific validation
        missing_required_fields = []
        if applied_defaults:
            if governance_mode == "DEMO":
                warnings.append(
                    f"Applied defaults for missing fields in DEMO mode: {', '.join(applied_defaults)}"
                )
            else:
                missing_required_fields = applied_defaults
                errors.append(
                    f"Missing required fields in {governance_mode} mode: {', '.join(applied_defaults)}"
                )
        
        # Additional warnings
        if len(protocol_request.variables) < 2:
            warnings.append("Consider specifying more variables for comprehensive analysis")
        
        if not protocol_request.risks:
            warnings.append("No risks specified - consider adding risk assessment")
        
        if not protocol_request.benefits:
            warnings.append("No benefits specified - consider adding benefit assessment")
        
        is_valid = len(errors) == 0
        
        return IRBValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            protocol_request=protocol_request if is_valid else None,
            missing_required_fields=missing_required_fields,
            applied_defaults=applied_defaults
        )
        
    except Exception as e:
        return IRBValidationResult(
            is_valid=False,
            errors=[f"Validation failed: {str(e)}"],
            warnings=warnings,
            protocol_request=None,
            missing_required_fields=[],
            applied_defaults=applied_defaults
        )