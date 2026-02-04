"""
Unit tests for Protocol Generator

Tests the template-driven protocol generation functionality including
template processing, variable substitution, and multi-format output.

Author: Stage 6 Enhancement Team
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
from services.worker.src.workflow_engine.stages.study_analyzers.protocol_generator import (
    ProtocolGenerator,
    ProtocolTemplate,
    ProtocolSection,
    TemplateEngine,
    ProtocolFormat,
    TemplateType,
    RegulatoryFramework
)


@pytest.fixture
def sample_study_data():
    """Sample study data for testing."""
    return {
        "study_title": "Test Clinical Trial",
        "protocol_number": "TEST-001",
        "principal_investigator": "Dr. Test Investigator",
        "primary_objective": "To evaluate the safety and efficacy of test intervention",
        "secondary_objectives": "To assess secondary endpoints",
        "design_description": "Randomized, double-blind, placebo-controlled trial",
        "estimated_sample_size": 200,
        "expected_power": 0.8,
        "significance_level": 0.05,
        "expected_effect_size": 0.3,
        "estimated_duration_months": 18,
        "target_population_description": "Adult patients with test condition"
    }


@pytest.fixture
def protocol_generator():
    """Create ProtocolGenerator instance."""
    return ProtocolGenerator(
        template_version="v1.0",
        enable_phi_integration=True,
        regulatory_templates=True
    )


@pytest.fixture
def template_engine():
    """Create TemplateEngine instance."""
    return TemplateEngine()


@pytest.fixture
def sample_protocol_section():
    """Create sample protocol section."""
    return ProtocolSection(
        section_id="test_section",
        title="Test Section",
        content="This is a test section with {{variable_name}} placeholder.",
        required=True,
        template_variables=["variable_name"]
    )


@pytest.fixture
def sample_protocol_template():
    """Create sample protocol template."""
    sections = [
        ProtocolSection(
            section_id="title",
            title="Study Title",
            content="**Title:** {{study_title}}\n**PI:** {{principal_investigator}}",
            required=True,
            template_variables=["study_title", "principal_investigator"]
        ),
        ProtocolSection(
            section_id="objectives",
            title="Objectives",
            content="Primary: {{primary_objective}}\nSecondary: {{secondary_objectives}}",
            required=True,
            template_variables=["primary_objective", "secondary_objectives"]
        )
    ]
    
    return ProtocolTemplate(
        template_id="test_template",
        name="Test Protocol Template",
        description="Template for testing",
        template_type=TemplateType.CLINICAL_TRIAL,
        version="1.0",
        sections=sections,
        required_variables=["study_title", "principal_investigator", "primary_objective"],
        created_date=datetime.now()
    )


class TestProtocolSection:
    """Test cases for ProtocolSection class."""
    
    def test_protocol_section_creation(self, sample_protocol_section):
        """Test ProtocolSection creation."""
        assert sample_protocol_section.section_id == "test_section"
        assert sample_protocol_section.title == "Test Section"
        assert "{{variable_name}}" in sample_protocol_section.content
        assert sample_protocol_section.required is True
    
    def test_protocol_section_to_dict(self, sample_protocol_section):
        """Test ProtocolSection dictionary conversion."""
        section_dict = sample_protocol_section.to_dict()
        
        assert section_dict["section_id"] == "test_section"
        assert section_dict["title"] == "Test Section"
        assert section_dict["required"] is True
        assert "template_variables" in section_dict
        assert isinstance(section_dict["subsections"], list)
    
    def test_get_variables_from_content(self, sample_protocol_section):
        """Test variable extraction from section content."""
        variables = sample_protocol_section.get_variables()
        
        assert "variable_name" in variables
        assert len(variables) >= 1
    
    def test_nested_sections_variables(self):
        """Test variable extraction from nested sections."""
        subsection = ProtocolSection(
            section_id="sub",
            title="Subsection with {{sub_var}}",
            content="Content with {{another_var}}",
            template_variables=["explicit_var"]
        )
        
        main_section = ProtocolSection(
            section_id="main",
            title="Main Section",
            content="Main content with {{main_var}}",
            subsections=[subsection]
        )
        
        variables = main_section.get_variables()
        
        assert "main_var" in variables
        assert "sub_var" in variables
        assert "another_var" in variables
        assert "explicit_var" in variables


class TestProtocolTemplate:
    """Test cases for ProtocolTemplate class."""
    
    def test_protocol_template_creation(self, sample_protocol_template):
        """Test ProtocolTemplate creation."""
        assert sample_protocol_template.template_id == "test_template"
        assert sample_protocol_template.name == "Test Protocol Template"
        assert sample_protocol_template.template_type == TemplateType.CLINICAL_TRIAL
        assert len(sample_protocol_template.sections) == 2
    
    def test_template_to_dict(self, sample_protocol_template):
        """Test ProtocolTemplate dictionary conversion."""
        template_dict = sample_protocol_template.to_dict()
        
        assert template_dict["template_id"] == "test_template"
        assert template_dict["template_type"] == "clinical_trial"
        assert len(template_dict["sections"]) == 2
        assert "required_variables" in template_dict
    
    def test_get_all_variables(self, sample_protocol_template):
        """Test getting all variables from template."""
        required_vars, optional_vars = sample_protocol_template.get_all_variables()
        
        assert "study_title" in required_vars
        assert "principal_investigator" in required_vars
        assert "primary_objective" in required_vars
        assert "secondary_objectives" in optional_vars  # From section content
    
    def test_validate_variables_success(self, sample_protocol_template):
        """Test successful variable validation."""
        variables = {
            "study_title": "Test Study",
            "principal_investigator": "Dr. Test",
            "primary_objective": "Test objective"
        }
        
        valid, missing = sample_protocol_template.validate_variables(variables)
        
        assert valid is True
        assert len(missing) == 0
    
    def test_validate_variables_missing(self, sample_protocol_template):
        """Test variable validation with missing variables."""
        variables = {
            "study_title": "Test Study"
            # Missing principal_investigator and primary_objective
        }
        
        valid, missing = sample_protocol_template.validate_variables(variables)
        
        assert valid is False
        assert "principal_investigator" in missing
        assert "primary_objective" in missing


class TestTemplateEngine:
    """Test cases for TemplateEngine class."""
    
    def test_template_engine_creation(self, template_engine):
        """Test TemplateEngine initialization."""
        assert template_engine.template_cache == {}
        assert template_engine.processing_history == []
    
    def test_simple_variable_substitution(self, template_engine):
        """Test simple variable substitution."""
        content = "Hello {{name}}, welcome to {{place}}!"
        variables = {"name": "John", "place": "the study"}
        
        result = template_engine._substitute_variables(content, variables)
        
        assert result == "Hello John, welcome to the study!"
    
    def test_missing_variable_handling(self, template_engine):
        """Test handling of missing variables."""
        content = "Hello {{name}}, welcome to {{missing_var}}!"
        variables = {"name": "John"}
        
        result = template_engine._substitute_variables(content, variables)
        
        # Missing variable should remain as placeholder
        assert "{{missing_var}}" in result
        assert "Hello John" in result
    
    def test_complex_value_formatting(self, template_engine):
        """Test formatting of complex values."""
        # Test list formatting
        list_result = template_engine._format_complex_value(["item1", "item2", "item3"])
        assert list_result == "item1, item2, item3"
        
        # Test dict formatting
        dict_result = template_engine._format_complex_value({"key1": "value1", "key2": "value2"})
        assert "key1: value1" in dict_result
        assert "key2: value2" in dict_result
    
    def test_render_section_basic(self, template_engine, sample_protocol_section):
        """Test basic section rendering."""
        variables = {"variable_name": "test_value"}
        
        rendered_section = template_engine._render_section(sample_protocol_section, variables)
        
        assert rendered_section.title == "Test Section"
        assert "test_value" in rendered_section.content
        assert "{{variable_name}}" not in rendered_section.content
        assert rendered_section.last_modified is not None
    
    def test_render_template_complete(self, template_engine, sample_protocol_template):
        """Test complete template rendering."""
        variables = {
            "study_title": "Test Study Title",
            "principal_investigator": "Dr. Jane Smith",
            "primary_objective": "Primary test objective",
            "secondary_objectives": "Secondary test objectives"
        }
        
        result = template_engine.render_template(sample_protocol_template, variables)
        
        assert "Test Study Title" in result
        assert "Dr. Jane Smith" in result
        assert "Primary test objective" in result
        assert "# Test Protocol Template" in result
        assert len(template_engine.processing_history) == 1
    
    def test_render_template_missing_variables(self, template_engine, sample_protocol_template):
        """Test template rendering with missing required variables."""
        variables = {
            "study_title": "Test Study Title"
            # Missing principal_investigator and primary_objective
        }
        
        result = template_engine.render_template(sample_protocol_template, variables)
        
        assert "Test Study Title" in result
        assert "[PRINCIPAL_INVESTIGATOR_REQUIRED]" in result
        assert "[PRIMARY_OBJECTIVE_REQUIRED]" in result
    
    def test_section_content_formatting(self, template_engine):
        """Test section content formatting."""
        section = ProtocolSection(
            section_id="test",
            title="Test Section",
            content="Main content",
            subsections=[
                ProtocolSection(
                    section_id="sub1",
                    title="Subsection 1",
                    content="Sub content 1"
                ),
                ProtocolSection(
                    section_id="sub2", 
                    title="Subsection 2",
                    content="Sub content 2"
                )
            ]
        )
        
        formatted_content = template_engine._format_section_content(section, level=1, number=1)
        
        assert "## 1. Test Section" in formatted_content
        assert "Main content" in formatted_content
        assert "### 1.1" in formatted_content
        assert "### 1.2" in formatted_content


class TestProtocolGenerator:
    """Test cases for ProtocolGenerator class."""
    
    def test_protocol_generator_initialization(self, protocol_generator):
        """Test ProtocolGenerator initialization."""
        assert protocol_generator.template_version == "v1.0"
        assert protocol_generator.enable_phi_integration is True
        assert protocol_generator.regulatory_templates is True
        assert len(protocol_generator.available_templates) >= 2  # RCT and observational
    
    def test_get_available_templates(self, protocol_generator):
        """Test getting available templates."""
        templates = protocol_generator.get_available_templates()
        
        assert isinstance(templates, dict)
        assert len(templates) >= 2
        
        # Check that template info contains expected fields
        for template_id, template_info in templates.items():
            assert "name" in template_info
            assert "description" in template_info
            assert "type" in template_info
            assert "required_variables" in template_info
    
    @pytest.mark.asyncio
    async def test_generate_protocol_basic(self, protocol_generator, sample_study_data):
        """Test basic protocol generation."""
        result = await protocol_generator.generate_protocol(
            template_id="rct_basic_v1",
            study_data=sample_study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert result["success"] is True
        assert "protocol_content" in result
        assert result["template_id"] == "rct_basic_v1"
        assert result["output_format"] == "markdown"
        assert "metadata" in result
        
        # Check content contains study data
        content = result["protocol_content"]
        assert sample_study_data["study_title"] in content
        assert sample_study_data["principal_investigator"] in content
        assert str(sample_study_data["estimated_sample_size"]) in content
    
    @pytest.mark.asyncio
    async def test_generate_protocol_html_format(self, protocol_generator, sample_study_data):
        """Test protocol generation with HTML format."""
        result = await protocol_generator.generate_protocol(
            template_id="rct_basic_v1",
            study_data=sample_study_data,
            output_format=ProtocolFormat.HTML
        )
        
        assert result["success"] is True
        assert result["output_format"] == "html"
        
        content = result["protocol_content"]
        assert "<!DOCTYPE html>" in content
        assert "<html>" in content
        assert "<h1>" in content or "<h2>" in content
    
    @pytest.mark.asyncio
    async def test_generate_protocol_json_format(self, protocol_generator, sample_study_data):
        """Test protocol generation with JSON format."""
        result = await protocol_generator.generate_protocol(
            template_id="rct_basic_v1",
            study_data=sample_study_data,
            output_format=ProtocolFormat.JSON
        )
        
        assert result["success"] is True
        assert result["output_format"] == "json"
        
        content = result["protocol_content"]
        assert content.startswith("{")  # Valid JSON
        assert "protocol_content" in content
    
    @pytest.mark.asyncio
    async def test_generate_protocol_observational(self, protocol_generator):
        """Test observational study protocol generation."""
        study_data = {
            "study_title": "Observational Study Test",
            "principal_investigator": "Dr. Observer",
            "primary_objective": "To observe test outcomes",
            "study_design_details": "Prospective cohort study",
            "target_population_description": "Adult population"
        }
        
        result = await protocol_generator.generate_protocol(
            template_id="observational_basic_v1",
            study_data=study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert result["success"] is True
        content = result["protocol_content"]
        assert "Observational Study Test" in content
        assert "Dr. Observer" in content
        assert "Prospective cohort study" in content
    
    @pytest.mark.asyncio
    async def test_generate_protocol_invalid_template(self, protocol_generator, sample_study_data):
        """Test protocol generation with invalid template."""
        result = await protocol_generator.generate_protocol(
            template_id="nonexistent_template",
            study_data=sample_study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_prepare_template_variables(self, protocol_generator, sample_study_data):
        """Test template variable preparation."""
        variables = await protocol_generator._prepare_template_variables(sample_study_data)
        
        # Check that all sample_study_data fields are included
        for key, value in sample_study_data.items():
            assert key in variables
            assert variables[key] == value
        
        # Check that additional default variables are added
        assert "protocol_date" in variables
        assert "protocol_version" in variables
    
    @pytest.mark.asyncio
    async def test_prepare_template_variables_minimal(self, protocol_generator):
        """Test template variable preparation with minimal data."""
        minimal_data = {"study_title": "Minimal Study"}
        
        variables = await protocol_generator._prepare_template_variables(minimal_data)
        
        assert variables["study_title"] == "Minimal Study"
        assert variables["principal_investigator"] == "[PI NAME]"  # Default value
        assert variables["estimated_sample_size"] == 100  # Default value
    
    def test_validate_template_variables_valid(self, protocol_generator):
        """Test template variable validation with valid variables."""
        variables = {
            "study_title": "Test Study",
            "principal_investigator": "Dr. Test",
            "primary_objective": "Test objective",
            "estimated_sample_size": 100,
            "design_description": "Test design"
        }
        
        result = protocol_generator.validate_template_variables("rct_basic_v1", variables)
        
        assert result["valid"] is True
        assert len(result["missing_variables"]) == 0
    
    def test_validate_template_variables_missing(self, protocol_generator):
        """Test template variable validation with missing variables."""
        variables = {
            "study_title": "Test Study"
            # Missing other required variables
        }
        
        result = protocol_generator.validate_template_variables("rct_basic_v1", variables)
        
        assert result["valid"] is False
        assert len(result["missing_variables"]) > 0
        assert "principal_investigator" in result["missing_variables"]
    
    def test_validate_template_variables_invalid_template(self, protocol_generator):
        """Test template variable validation with invalid template."""
        result = protocol_generator.validate_template_variables("invalid_template", {})
        
        assert result["valid"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_convert_to_html_basic(self, protocol_generator):
        """Test basic markdown to HTML conversion."""
        markdown_content = """# Main Title
## Subtitle
**Bold text** and regular text.

Another paragraph."""
        
        html_result = await protocol_generator._convert_to_html(markdown_content)
        
        assert "<!DOCTYPE html>" in html_result
        assert "<h1>Main Title</h1>" in html_result
        assert "<h2>Subtitle</h2>" in html_result
        assert "<strong>Bold text</strong>" in html_result
    
    def test_generate_protocol_metadata(self, protocol_generator, sample_protocol_template):
        """Test protocol metadata generation."""
        variables = {"test_var": "test_value", "another_var": "another_value"}
        
        metadata = protocol_generator._generate_protocol_metadata(sample_protocol_template, variables)
        
        assert metadata["template_name"] == "Test Protocol Template"
        assert metadata["template_version"] == "1.0"
        assert metadata["template_type"] == "clinical_trial"
        assert metadata["sections_count"] == 2
        assert metadata["variables_provided"] == 2
        assert metadata["phi_compliant"] is True


class TestIntegration:
    """Integration tests for the complete protocol generation workflow."""
    
    @pytest.mark.asyncio
    async def test_full_protocol_generation_workflow(self, sample_study_data):
        """Test complete protocol generation workflow."""
        generator = ProtocolGenerator()
        
        # Test with RCT template
        rct_result = await generator.generate_protocol(
            template_id="rct_basic_v1",
            study_data=sample_study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert rct_result["success"] is True
        
        # Test with observational template
        obs_data = sample_study_data.copy()
        obs_data.update({
            "study_design_details": "Observational cohort study",
            "target_population_description": "Adult patients"
        })
        
        obs_result = await generator.generate_protocol(
            template_id="observational_basic_v1",
            study_data=obs_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert obs_result["success"] is True
        
        # Both should contain study title
        assert sample_study_data["study_title"] in rct_result["protocol_content"]
        assert sample_study_data["study_title"] in obs_result["protocol_content"]
    
    @pytest.mark.asyncio
    async def test_multiple_output_formats(self, protocol_generator, sample_study_data):
        """Test protocol generation in multiple formats."""
        formats_to_test = [
            ProtocolFormat.MARKDOWN,
            ProtocolFormat.HTML,
            ProtocolFormat.JSON
        ]
        
        for output_format in formats_to_test:
            result = await protocol_generator.generate_protocol(
                template_id="rct_basic_v1",
                study_data=sample_study_data,
                output_format=output_format
            )
            
            assert result["success"] is True
            assert result["output_format"] == output_format.value
            assert len(result["protocol_content"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, protocol_generator):
        """Test error recovery in protocol generation."""
        # Test with empty study data
        empty_result = await protocol_generator.generate_protocol(
            template_id="rct_basic_v1",
            study_data={},
            output_format=ProtocolFormat.MARKDOWN
        )
        
        # Should still succeed with default values
        assert empty_result["success"] is True
        assert "[PI NAME]" in empty_result["protocol_content"]  # Default value
        
        # Test with invalid template
        invalid_result = await protocol_generator.generate_protocol(
            template_id="invalid_template",
            study_data=sample_study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        assert invalid_result["success"] is False
        assert "error" in invalid_result


if __name__ == "__main__":
    pytest.main([__file__])