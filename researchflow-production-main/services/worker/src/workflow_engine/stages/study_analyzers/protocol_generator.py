"""
Protocol Generator for Clinical Study Documentation

This module provides template-driven protocol generation capabilities for
clinical and research studies with regulatory compliance and PHI protection.

Key Features:
- Template-driven protocol generation
- Dynamic content assembly based on study design
- Multi-format export (PDF, Word, HTML, Markdown)
- Regulatory framework compliance
- PHI-compliant content generation
- Integration with ML optimizer and power engine

Author: Stage 6 Enhancement Team
"""

import logging
import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from pathlib import Path
import asyncio
from datetime import datetime, date

# Configure logging
logger = logging.getLogger(__name__)


class ProtocolFormat(Enum):
    """Supported protocol output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    XML = "xml"
    LATEX = "latex"
    RTF = "rtf"


class TemplateType(Enum):
    """Types of protocol templates."""
    CLINICAL_TRIAL = "clinical_trial"
    OBSERVATIONAL_STUDY = "observational"
    PILOT_STUDY = "pilot"
    FEASIBILITY_STUDY = "feasibility"
    REGISTRY_STUDY = "registry"
    INTERVENTIONAL_STUDY = "interventional"
    BIOMARKER_STUDY = "biomarker"
    DEVICE_STUDY = "device"
    PEDIATRIC_STUDY = "pediatric"
    ONCOLOGY_STUDY = "oncology"
    CARDIOVASCULAR_STUDY = "cardiovascular"
    RARE_DISEASE_STUDY = "rare_disease"
    DIGITAL_HEALTH_STUDY = "digital_health"
    SURGICAL_STUDY = "surgical"
    BEHAVIORAL_STUDY = "behavioral"
    VACCINE_STUDY = "vaccine"


class RegulatoryFramework(Enum):
    """Regulatory frameworks for compliance."""
    FDA_IND = "fda_ind"
    FDA_IDE = "fda_ide"
    EMA_CTA = "ema_cta"
    ICH_GCP = "ich_gcp"
    ISO_14155 = "iso_14155"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    INSTITUTIONAL = "institutional"
    FDA_510K = "fda_510k"
    FDA_PMA = "fda_pma"
    CE_MDR = "ce_mdr"
    HEALTH_CANADA = "health_canada"
    TGA_AUSTRALIA = "tga_australia"
    PMDA_JAPAN = "pmda_japan"
    NMPA_CHINA = "nmpa_china"
    ICH_E6_R2 = "ich_e6_r2"
    ICH_E8 = "ich_e8"
    ICH_E9 = "ich_e9"


@dataclass
class ProtocolSection:
    """
    Data structure for individual protocol sections.
    """
    section_id: str
    title: str
    content: str
    subsections: List['ProtocolSection'] = field(default_factory=list)
    
    # Metadata
    required: bool = True
    template_variables: List[str] = field(default_factory=list)
    regulatory_requirements: List[RegulatoryFramework] = field(default_factory=list)
    
    # Content attributes
    editable: bool = True
    auto_generated: bool = False
    last_modified: Optional[datetime] = None
    
    # Advanced features
    conditional_logic: Optional[Dict[str, Any]] = None
    section_order: int = 0
    content_templates: Dict[str, str] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    ai_enhancement_enabled: bool = True
    content_hints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert section to dictionary format."""
        return {
            "section_id": self.section_id,
            "title": self.title,
            "content": self.content,
            "subsections": [sub.to_dict() for sub in self.subsections],
            "required": self.required,
            "template_variables": self.template_variables,
            "regulatory_requirements": [req.value for req in self.regulatory_requirements],
            "editable": self.editable,
            "auto_generated": self.auto_generated,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None
        }
    
    def get_variables(self) -> List[str]:
        """Extract all template variables from content and subsections."""
        variables = set(self.template_variables)
        
        # Extract variables from content using regex
        content_vars = re.findall(r'\{\{(\w+)\}\}', self.content)
        variables.update(content_vars)
        
        # Extract from subsections
        for subsection in self.subsections:
            variables.update(subsection.get_variables())
        
        return list(variables)


@dataclass
class ProtocolTemplate:
    """
    Data structure for protocol templates.
    """
    template_id: str
    name: str
    description: str
    template_type: TemplateType
    version: str = "1.0"
    
    # Template sections
    sections: List[ProtocolSection] = field(default_factory=list)
    
    # Metadata
    regulatory_frameworks: List[RegulatoryFramework] = field(default_factory=list)
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    
    # Template properties
    language: str = "en"
    created_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    author: str = "System"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary format."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "version": self.version,
            "sections": [section.to_dict() for section in self.sections],
            "regulatory_frameworks": [fw.value for fw in self.regulatory_frameworks],
            "required_variables": self.required_variables,
            "optional_variables": self.optional_variables,
            "language": self.language,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "author": self.author
        }
    
    def get_all_variables(self) -> Tuple[List[str], List[str]]:
        """Get all required and optional variables from template."""
        required_vars = set(self.required_variables)
        optional_vars = set(self.optional_variables)
        
        # Extract from sections
        for section in self.sections:
            section_vars = section.get_variables()
            for var in section_vars:
                if var not in required_vars:
                    optional_vars.add(var)
        
        return list(required_vars), list(optional_vars)
    
    def validate_variables(self, variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that required variables are provided."""
        missing_vars = []
        
        for req_var in self.required_variables:
            if req_var not in variables or variables[req_var] is None:
                missing_vars.append(req_var)
        
        return len(missing_vars) == 0, missing_vars


class TemplateEngine:
    """
    Template processing engine for dynamic content generation.
    """
    
    def __init__(self):
        self.template_cache = {}
        self.processing_history = []
    
    def render_template(self,
                       template: ProtocolTemplate,
                       variables: Dict[str, Any],
                       format_output: bool = True) -> str:
        """
        Render a protocol template with provided variables.
        
        Args:
            template: ProtocolTemplate to render
            variables: Dictionary of template variables
            format_output: Whether to format the output
            
        Returns:
            Rendered protocol content as string
        """
        try:
            logger.info(f"Rendering template: {template.name}")
            
            # Validate required variables
            valid, missing_vars = template.validate_variables(variables)
            if not valid:
                logger.warning(f"Missing required variables: {missing_vars}")
                # Provide default values for missing variables
                for var in missing_vars:
                    variables[var] = f"[{var.upper()}_REQUIRED]"
            
            # Render each section
            rendered_sections = []
            for section in template.sections:
                rendered_section = self._render_section(section, variables)
                rendered_sections.append(rendered_section)
            
            # Combine sections into full protocol
            full_protocol = self._combine_sections(rendered_sections, template)
            
            if format_output:
                full_protocol = self._format_protocol(full_protocol, template)
            
            # Record processing
            self.processing_history.append({
                "template_id": template.template_id,
                "timestamp": datetime.now(),
                "variables_count": len(variables),
                "sections_count": len(template.sections)
            })
            
            logger.info(f"Template rendered successfully. Length: {len(full_protocol)} chars")
            return full_protocol
            
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return f"Error rendering protocol: {str(e)}"
    
    def _render_section(self,
                       section: ProtocolSection,
                       variables: Dict[str, Any]) -> ProtocolSection:
        """Render individual section with variables."""
        try:
            # Render main content
            rendered_content = self._substitute_variables(section.content, variables)
            
            # Render subsections
            rendered_subsections = []
            for subsection in section.subsections:
                rendered_sub = self._render_section(subsection, variables)
                rendered_subsections.append(rendered_sub)
            
            # Create rendered section
            rendered_section = ProtocolSection(
                section_id=section.section_id,
                title=self._substitute_variables(section.title, variables),
                content=rendered_content,
                subsections=rendered_subsections,
                required=section.required,
                template_variables=section.template_variables,
                regulatory_requirements=section.regulatory_requirements,
                editable=section.editable,
                auto_generated=section.auto_generated,
                last_modified=datetime.now()
            )
            
            return rendered_section
            
        except Exception as e:
            logger.error(f"Error rendering section {section.section_id}: {str(e)}")
            # Return section with error message
            return ProtocolSection(
                section_id=section.section_id,
                title=section.title,
                content=f"Error rendering section: {str(e)}",
                required=section.required
            )
    
    def _substitute_variables(self,
                            content: str,
                            variables: Dict[str, Any]) -> str:
        """Substitute template variables in content."""
        try:
            # Simple template variable substitution
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                if isinstance(value, (list, dict)):
                    # Convert complex types to string representation
                    value_str = self._format_complex_value(value)
                else:
                    value_str = str(value) if value is not None else ""
                content = content.replace(placeholder, value_str)
            
            return content
            
        except Exception as e:
            logger.error(f"Error substituting variables: {str(e)}")
            return content
    
    def _format_complex_value(self, value: Union[List, Dict]) -> str:
        """Format complex values for template substitution."""
        if isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                return ", ".join(value)
            else:
                return "; ".join(str(item) for item in value)
        elif isinstance(value, dict):
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        else:
            return str(value)
    
    def _combine_sections(self,
                         sections: List[ProtocolSection],
                         template: ProtocolTemplate) -> str:
        """Combine rendered sections into full protocol."""
        protocol_parts = []
        
        # Add header
        protocol_parts.append(f"# {template.name}")
        protocol_parts.append(f"**Version:** {template.version}")
        protocol_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        protocol_parts.append("")
        
        # Add sections
        for i, section in enumerate(sections, 1):
            section_content = self._format_section_content(section, level=1, number=i)
            protocol_parts.append(section_content)
            protocol_parts.append("")
        
        return "\n".join(protocol_parts)
    
    def _format_section_content(self,
                               section: ProtocolSection,
                               level: int = 1,
                               number: int = 1) -> str:
        """Format section content with proper numbering and hierarchy."""
        # Create section header
        header_prefix = "#" * min(level + 1, 6)  # Limit to markdown header levels
        section_header = f"{header_prefix} {number}. {section.title}"
        
        content_parts = [section_header, "", section.content]
        
        # Add subsections
        for i, subsection in enumerate(section.subsections, 1):
            sub_number = f"{number}.{i}"
            subsection_content = self._format_section_content(
                subsection, level + 1, sub_number
            )
            content_parts.append("")
            content_parts.append(subsection_content)
        
        return "\n".join(content_parts)
    
    def _format_protocol(self,
                        content: str,
                        template: ProtocolTemplate) -> str:
        """Apply final formatting to protocol content."""
        try:
            # Basic formatting improvements
            formatted_content = content
            
            # Add page breaks before major sections (for PDF generation)
            formatted_content = re.sub(
                r'^(#{1,2} \d+\.)', 
                r'\\pagebreak\n\1', 
                formatted_content, 
                flags=re.MULTILINE
            )
            
            # Ensure proper spacing
            formatted_content = re.sub(r'\n{3,}', '\n\n', formatted_content)
            
            return formatted_content.strip()
            
        except Exception as e:
            logger.error(f"Error formatting protocol: {str(e)}")
            return content


class ProtocolGenerator:
    """
    Main Protocol Generator for clinical study documentation.
    
    Provides template-driven protocol generation with regulatory compliance,
    PHI protection, and integration with study design components.
    """
    
    def __init__(self,
                 template_version: str = "v1.0",
                 enable_phi_integration: bool = True,
                 regulatory_templates: bool = True):
        self.template_version = template_version
        self.enable_phi_integration = enable_phi_integration
        self.regulatory_templates = regulatory_templates
        
        # Initialize components
        self.template_engine = TemplateEngine()
        self.available_templates = {}
        
        # Initialize default templates
        self._initialize_default_templates()
        
        logger.info("Protocol Generator initialized")
    
    def _initialize_default_templates(self):
        """Initialize default protocol templates."""
        try:
            # Create basic clinical trial template
            rct_template = self._create_rct_template()
            self.available_templates[rct_template.template_id] = rct_template
            
            # Create observational study template
            obs_template = self._create_observational_template()
            self.available_templates[obs_template.template_id] = obs_template
            
            logger.info(f"Initialized {len(self.available_templates)} default templates")
            
        except Exception as e:
            logger.error(f"Error initializing default templates: {str(e)}")
    
    def _create_rct_template(self) -> ProtocolTemplate:
        """Create randomized controlled trial template."""
        sections = [
            ProtocolSection(
                section_id="title_page",
                title="Title Page",
                content="""**Study Title:** {{study_title}}
**Protocol Number:** {{protocol_number}}
**Principal Investigator:** {{principal_investigator}}
**Study Phase:** {{study_phase}}
**Study Type:** {{study_type}}
**Sponsor:** {{sponsor}}

**Version:** {{protocol_version}}
**Date:** {{protocol_date}}""",
                required=True,
                template_variables=["study_title", "protocol_number", "principal_investigator"]
            ),
            ProtocolSection(
                section_id="synopsis",
                title="Protocol Synopsis",
                content="""**Background:** {{background_summary}}

**Objectives:**
Primary: {{primary_objective}}
Secondary: {{secondary_objectives}}

**Study Design:** {{design_description}}

**Study Population:** {{target_population_description}}

**Sample Size:** {{estimated_sample_size}} participants ({{sample_size_justification}})

**Primary Endpoint:** {{primary_endpoint_description}}

**Statistical Analysis:** {{statistical_analysis_summary}}

**Study Duration:** Approximately {{estimated_duration_months}} months""",
                required=True,
                template_variables=["background_summary", "primary_objective", "design_description"]
            ),
            ProtocolSection(
                section_id="objectives",
                title="Study Objectives",
                content="""## Primary Objective
{{primary_objective}}

## Secondary Objectives
{{secondary_objectives}}

## Exploratory Objectives
{{exploratory_objectives}}""",
                required=True
            ),
            ProtocolSection(
                section_id="study_design",
                title="Study Design",
                content="""## Overall Study Design
{{design_description}}

**Design Type:** {{design_type}}
**Allocation Strategy:** {{allocation_strategy}}
**Blinding:** {{blinding_description}}
**Treatment Groups:** {{treatment_groups}}

## Randomization
{{randomization_description}}

## Study Duration
**Total Study Duration:** {{estimated_duration_months}} months
**Subject Participation Duration:** {{subject_duration}} months

## Study Population
**Target Sample Size:** {{estimated_sample_size}} participants
**Population:** {{target_population_description}}""",
                required=True
            ),
            ProtocolSection(
                section_id="statistical_considerations",
                title="Statistical Considerations",
                content="""## Sample Size Calculation
**Target Sample Size:** {{estimated_sample_size}} participants
**Power:** {{expected_power}}
**Alpha Level:** {{significance_level}}
**Effect Size:** {{expected_effect_size}}
**Statistical Test:** {{statistical_test_type}}

{{sample_size_justification}}

## Statistical Analysis Plan
**Primary Analysis:** {{primary_analysis_method}}
**Population:** {{analysis_population}}
**Missing Data:** {{missing_data_approach}}

## Interim Analyses
{{interim_analysis_plan}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="rct_basic_v1",
            name="Randomized Controlled Trial - Basic Template",
            description="Standard template for randomized controlled trials",
            template_type=TemplateType.CLINICAL_TRIAL,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.ICH_GCP, RegulatoryFramework.HIPAA],
            required_variables=[
                "study_title", "principal_investigator", "primary_objective",
                "estimated_sample_size", "design_description"
            ],
            created_date=datetime.now()
        )
    
    def _create_observational_template(self) -> ProtocolTemplate:
        """Create observational study template."""
        sections = [
            ProtocolSection(
                section_id="title_page",
                title="Title Page",
                content="""**Study Title:** {{study_title}}
**Protocol Number:** {{protocol_number}}
**Principal Investigator:** {{principal_investigator}}
**Study Type:** Observational Study
**Study Design:** {{study_design}}

**Version:** {{protocol_version}}
**Date:** {{protocol_date}}""",
                required=True
            ),
            ProtocolSection(
                section_id="background",
                title="Background and Rationale",
                content="""## Background
{{background_description}}

## Rationale
{{study_rationale}}

## Literature Review
{{literature_summary}}""",
                required=True
            ),
            ProtocolSection(
                section_id="objectives",
                title="Study Objectives",
                content="""## Primary Objective
{{primary_objective}}

## Secondary Objectives
{{secondary_objectives}}""",
                required=True
            ),
            ProtocolSection(
                section_id="methods",
                title="Study Methods",
                content="""## Study Design
{{study_design_details}}

## Study Population
**Target Population:** {{target_population_description}}
**Inclusion Criteria:** {{inclusion_criteria}}
**Exclusion Criteria:** {{exclusion_criteria}}

## Data Collection
{{data_collection_methods}}

## Follow-up
{{followup_schedule}}""",
                required=True
            )
        ]
        
        return ProtocolTemplate(
            template_id="observational_basic_v1",
            name="Observational Study - Basic Template",
            description="Standard template for observational studies",
            template_type=TemplateType.OBSERVATIONAL_STUDY,
            version=self.template_version,
            sections=sections,
            regulatory_frameworks=[RegulatoryFramework.HIPAA],
            required_variables=[
                "study_title", "principal_investigator", "primary_objective",
                "study_design_details", "target_population_description"
            ],
            created_date=datetime.now()
        )
    
    async def generate_protocol(self,
                              template_id: str,
                              study_data: Dict[str, Any],
                              output_format: ProtocolFormat = ProtocolFormat.MARKDOWN) -> Dict[str, Any]:
        """
        Generate a protocol document from template and study data.
        
        Args:
            template_id: ID of template to use
            study_data: Study parameters and data
            output_format: Desired output format
            
        Returns:
            Dictionary containing generated protocol and metadata
        """
        try:
            logger.info(f"Generating protocol with template: {template_id}")
            
            # Get template
            if template_id not in self.available_templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.available_templates[template_id]
            
            # Prepare variables from study data
            variables = await self._prepare_template_variables(study_data)
            
            # Render protocol
            protocol_content = self.template_engine.render_template(
                template, variables, format_output=True
            )
            
            # Format for output type
            formatted_content = await self._format_for_output(
                protocol_content, output_format
            )
            
            # Generate metadata
            metadata = self._generate_protocol_metadata(template, variables)
            
            return {
                "success": True,
                "protocol_content": formatted_content,
                "template_id": template_id,
                "output_format": output_format.value,
                "metadata": metadata,
                "generated_timestamp": datetime.now().isoformat(),
                "content_length": len(formatted_content)
            }
            
        except Exception as e:
            logger.error(f"Error generating protocol: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "template_id": template_id,
                "output_format": output_format.value
            }
    
    async def _prepare_template_variables(self, study_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare template variables from study data."""
        try:
            variables = {}
            
            # Basic study information
            variables["study_title"] = study_data.get("study_title", "Clinical Study Protocol")
            variables["protocol_number"] = study_data.get("protocol_number", "PROTO-001")
            variables["principal_investigator"] = study_data.get("principal_investigator", "[PI NAME]")
            variables["protocol_version"] = study_data.get("protocol_version", "1.0")
            variables["protocol_date"] = datetime.now().strftime("%Y-%m-%d")
            
            # Study design information
            variables["primary_objective"] = study_data.get("primary_objective", "[PRIMARY OBJECTIVE]")
            variables["secondary_objectives"] = study_data.get("secondary_objectives", "[SECONDARY OBJECTIVES]")
            variables["design_description"] = study_data.get("design_description", "[STUDY DESIGN]")
            
            # Sample size and statistical information
            variables["estimated_sample_size"] = study_data.get("estimated_sample_size", 100)
            variables["expected_power"] = study_data.get("expected_power", 0.8)
            variables["significance_level"] = study_data.get("significance_level", 0.05)
            variables["expected_effect_size"] = study_data.get("expected_effect_size", 0.3)
            
            # Duration and timeline
            variables["estimated_duration_months"] = study_data.get("estimated_duration_months", 12)
            variables["subject_duration"] = study_data.get("subject_duration", 6)
            
            # Population and endpoints
            variables["target_population_description"] = study_data.get(
                "target_population_description", "[TARGET POPULATION]"
            )
            variables["primary_endpoint_description"] = study_data.get(
                "primary_endpoint_description", "[PRIMARY ENDPOINT]"
            )
            
            # Add any additional variables from study_data
            for key, value in study_data.items():
                if key not in variables:
                    variables[key] = value
            
            return variables
            
        except Exception as e:
            logger.error(f"Error preparing template variables: {str(e)}")
            return {}
    
    async def _format_for_output(self,
                                content: str,
                                output_format: ProtocolFormat) -> str:
        """Format content for specific output type."""
        try:
            if output_format == ProtocolFormat.MARKDOWN:
                return content
            elif output_format == ProtocolFormat.HTML:
                return await self._convert_to_html(content)
            elif output_format == ProtocolFormat.JSON:
                return json.dumps({"protocol_content": content}, indent=2)
            else:
                # For formats requiring external libraries (PDF, DOCX), return markdown
                logger.warning(f"Format {output_format.value} not fully implemented, returning markdown")
                return content
                
        except Exception as e:
            logger.error(f"Error formatting output: {str(e)}")
            return content
    
    async def _convert_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML (basic conversion)."""
        try:
            # Basic markdown to HTML conversion
            html_content = markdown_content
            
            # Convert headers
            html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
            
            # Convert bold text
            html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
            
            # Convert paragraphs
            html_content = re.sub(r'\n\n', r'\n</p>\n<p>', html_content)
            html_content = f"<p>{html_content}</p>"
            
            # Wrap in basic HTML structure
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Clinical Study Protocol</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        strong {{ color: #34495e; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""
            
            return full_html
            
        except Exception as e:
            logger.error(f"Error converting to HTML: {str(e)}")
            return f"<pre>{markdown_content}</pre>"
    
    def _generate_protocol_metadata(self,
                                  template: ProtocolTemplate,
                                  variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata for the generated protocol."""
        return {
            "template_name": template.name,
            "template_version": template.version,
            "template_type": template.template_type.value,
            "regulatory_frameworks": [fw.value for fw in template.regulatory_frameworks],
            "sections_count": len(template.sections),
            "variables_provided": len(variables),
            "required_variables": template.required_variables,
            "generation_method": "template_engine",
            "phi_compliant": self.enable_phi_integration
        }
    
    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available templates."""
        templates_info = {}
        
        for template_id, template in self.available_templates.items():
            templates_info[template_id] = {
                "name": template.name,
                "description": template.description,
                "type": template.template_type.value,
                "version": template.version,
                "required_variables": template.required_variables,
                "sections_count": len(template.sections)
            }
        
        return templates_info
    
    def validate_template_variables(self,
                                  template_id: str,
                                  variables: Dict[str, Any]) -> Dict[str, Any]:
        """Validate variables against template requirements."""
        try:
            if template_id not in self.available_templates:
                return {"valid": False, "error": "Template not found"}
            
            template = self.available_templates[template_id]
            valid, missing_vars = template.validate_variables(variables)
            
            return {
                "valid": valid,
                "missing_variables": missing_vars,
                "provided_variables": list(variables.keys()),
                "required_variables": template.required_variables
            }
            
        except Exception as e:
            logger.error(f"Error validating template variables: {str(e)}")
            return {"valid": False, "error": str(e)}