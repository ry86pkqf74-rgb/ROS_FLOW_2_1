"""
Unit Tests for DataVisualizationAgent

Tests for data visualization functionality including:
- Chart creation methods
- Journal style application
- Color palette selection
- Export formats
- Quality checks
- Data validation

Linear Issues: ROS-XXX (Stage 8 - Data Visualization Agent)
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.analysis.data_visualization_agent import (
    DataVisualizationAgent,
    create_data_visualization_agent,
)
from agents.analysis.visualization_types import (
    VizType,
    VizRequest,
    Figure,
    VizResult,
    BarChartConfig,
    LineChartConfig,
    ScatterConfig,
    BoxPlotConfig,
    KMConfig,
    ForestConfig,
    FlowStage,
    EffectSize,
    StudyContext,
    JournalStyle,
    ColorPalette,
    ExportFormat,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_bar_data():
    """Sample data for bar chart."""
    return pd.DataFrame({
        "group": ["Control", "Treatment A", "Treatment B"],
        "outcome": [5.2, 6.8, 7.3],
        "std": [1.1, 1.3, 1.0],
    })


@pytest.fixture
def sample_line_data():
    """Sample data for line chart."""
    return pd.DataFrame({
        "time": [0, 1, 2, 3, 4, 5],
        "value": [10, 12, 11, 14, 13, 15],
        "group": ["A"] * 3 + ["B"] * 3,
    })


@pytest.fixture
def sample_km_data():
    """Sample data for Kaplan-Meier curve."""
    np.random.seed(42)
    return pd.DataFrame({
        "time": np.random.exponential(10, 100),
        "event": np.random.binomial(1, 0.7, 100),
        "group": ["Treatment"] * 50 + ["Control"] * 50,
    })


@pytest.fixture
def sample_study_context():
    """Sample study context."""
    return StudyContext(
        study_title="Test Clinical Trial",
        research_question="Does treatment X improve outcomes?",
        outcome_variable="Pain Score (0-10)",
        sample_size=150,
        study_design="Randomized controlled trial",
    )


@pytest.fixture
def sample_effect_sizes():
    """Sample effect sizes for forest plot."""
    return [
        EffectSize(
            study_id="study1",
            study_label="Smith et al. 2020",
            effect_estimate=0.85,
            ci_lower=0.72,
            ci_upper=1.01,
            weight=0.25,
            n_treatment=150,
            n_control=145,
        ),
        EffectSize(
            study_id="study2",
            study_label="Jones et al. 2021",
            effect_estimate=0.92,
            ci_lower=0.80,
            ci_upper=1.06,
            weight=0.30,
        ),
    ]


# =============================================================================
# Type Definition Tests
# =============================================================================

class TestTypeDefinitions:
    """Tests for type definitions and data structures."""
    
    def test_viz_request_creation(self):
        """Test creating VizRequest."""
        request = VizRequest(
            viz_type=VizType.BAR_CHART,
            data_columns={"x": "group", "y": "outcome"},
            title="Test Chart",
        )
        
        assert request.viz_type == VizType.BAR_CHART
        assert "x" in request.data_columns
        assert request.title == "Test Chart"
    
    def test_viz_request_to_dict(self):
        """Test VizRequest serialization."""
        request = VizRequest(
            viz_type=VizType.LINE_CHART,
            data_columns={"x": "time", "y": "value"},
        )
        
        result = request.to_dict()
        assert result["viz_type"] == "line_chart"
        assert result["data_columns"]["x"] == "time"
    
    def test_figure_creation(self):
        """Test Figure object creation."""
        figure = Figure(
            figure_id="test_fig",
            viz_type=VizType.SCATTER_PLOT,
            width=800,
            height=600,
            dpi=300,
        )
        
        assert figure.figure_id == "test_fig"
        assert figure.viz_type == VizType.SCATTER_PLOT
        assert figure.dpi == 300
    
    def test_figure_to_dict(self):
        """Test Figure serialization."""
        figure = Figure(
            figure_id="fig1",
            viz_type=VizType.BOX_PLOT,
            caption="Test caption",
            alt_text="Box plot showing...",
        )
        
        result = figure.to_dict()
        assert result["figure_id"] == "fig1"
        assert result["caption"] == "Test caption"
        assert "created_at" in result
    
    def test_study_context_to_dict(self, sample_study_context):
        """Test StudyContext serialization."""
        result = sample_study_context.to_dict()
        
        assert result["study_title"] == "Test Clinical Trial"
        assert result["sample_size"] == 150


# =============================================================================
# Agent Initialization Tests
# =============================================================================

class TestAgentInitialization:
    """Tests for agent initialization and configuration."""
    
    def test_agent_creation(self):
        """Test agent initializes correctly."""
        agent = DataVisualizationAgent()
        
        assert agent.config.name == "DataVisualizationAgent"
        assert 8 in agent.config.stages
        assert agent.config.phi_safe is True
        assert agent.config.quality_threshold == 0.85
    
    def test_factory_function(self):
        """Test factory function creates agent."""
        agent = create_data_visualization_agent()
        
        assert isinstance(agent, DataVisualizationAgent)
        assert agent.config.name == "DataVisualizationAgent"
    
    def test_style_presets_initialized(self):
        """Test journal style presets are initialized."""
        agent = DataVisualizationAgent()
        
        assert hasattr(agent, 'style_presets')
        assert JournalStyle.NATURE in agent.style_presets
        assert JournalStyle.JAMA in agent.style_presets
    
    def test_color_palettes_initialized(self):
        """Test color palettes are initialized."""
        agent = DataVisualizationAgent()
        
        assert hasattr(agent, 'color_palettes')
        assert ColorPalette.COLORBLIND_SAFE in agent.color_palettes
        
        # Check colorblind palette has colors
        colors = agent.color_palettes[ColorPalette.COLORBLIND_SAFE]
        assert len(colors) > 0
        assert all(color.startswith("#") for color in colors)


# =============================================================================
# Chart Configuration Tests
# =============================================================================

class TestChartConfigurations:
    """Tests for chart configuration classes."""
    
    def test_bar_chart_config(self):
        """Test BarChartConfig creation."""
        config = BarChartConfig(
            title="Test Bar Chart",
            show_error_bars=True,
            error_bar_type="ci",
        )
        
        assert config.title == "Test Bar Chart"
        assert config.show_error_bars is True
        assert config.error_bar_type == "ci"
        assert config.dpi == 300  # Default value
    
    def test_line_chart_config(self):
        """Test LineChartConfig creation."""
        config = LineChartConfig(
            show_markers=True,
            show_confidence_bands=True,
            confidence_level=0.95,
        )
        
        assert config.show_markers is True
        assert config.show_confidence_bands is True
        assert config.confidence_level == 0.95
    
    def test_km_config(self):
        """Test KMConfig creation."""
        config = KMConfig(
            time_label="Time (months)",
            show_risk_table=True,
            show_confidence_intervals=True,
        )
        
        assert config.time_label == "Time (months)"
        assert config.show_risk_table is True


# =============================================================================
# Chart Creation Tests
# =============================================================================

class TestChartCreation:
    """Tests for chart creation methods."""
    
    def test_create_bar_chart(self, sample_bar_data):
        """Test bar chart creation."""
        agent = DataVisualizationAgent()
        config = BarChartConfig(title="Test Bar Chart")
        
        figure = agent.create_bar_chart(sample_bar_data, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.BAR_CHART
        assert figure.figure_id is not None
    
    def test_create_line_chart(self, sample_line_data):
        """Test line chart creation."""
        agent = DataVisualizationAgent()
        config = LineChartConfig(title="Test Line Chart")
        
        figure = agent.create_line_chart(sample_line_data, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.LINE_CHART
    
    def test_create_scatter_plot(self):
        """Test scatter plot creation."""
        agent = DataVisualizationAgent()
        data = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 5, 4, 6],
        })
        config = ScatterConfig(show_trendline=True)
        
        figure = agent.create_scatter_plot(data, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.SCATTER_PLOT
    
    def test_create_box_plot(self):
        """Test box plot creation."""
        agent = DataVisualizationAgent()
        data = pd.DataFrame({
            "group": ["A"] * 10 + ["B"] * 10,
            "value": list(range(10)) + list(range(5, 15)),
        })
        config = BoxPlotConfig(show_outliers=True)
        
        figure = agent.create_box_plot(data, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.BOX_PLOT
    
    def test_create_kaplan_meier(self, sample_km_data):
        """Test Kaplan-Meier curve creation."""
        agent = DataVisualizationAgent()
        config = KMConfig(show_risk_table=True)
        
        figure = agent.create_kaplan_meier(sample_km_data, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.KAPLAN_MEIER
    
    def test_create_forest_plot(self, sample_effect_sizes):
        """Test forest plot creation."""
        agent = DataVisualizationAgent()
        config = ForestConfig(effect_measure="OR")
        
        figure = agent.create_forest_plot(sample_effect_sizes, config)
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.FOREST_PLOT
    
    def test_create_consort_flowchart(self):
        """Test CONSORT flowchart creation."""
        agent = DataVisualizationAgent()
        stages = [
            FlowStage(name="Assessed for eligibility", n=500),
            FlowStage(name="Randomized", n=350),
        ]
        
        figure = agent.create_flowchart(stages, diagram_type="consort")
        
        assert isinstance(figure, Figure)
        assert figure.viz_type == VizType.CONSORT_DIAGRAM


# =============================================================================
# Quality Check Tests
# =============================================================================

@pytest.mark.asyncio
class TestQualityChecks:
    """Tests for quality checking functionality."""
    
    async def test_quality_check_with_figures(self):
        """Test quality check with complete result."""
        agent = DataVisualizationAgent()
        
        state = {
            "execution_result": {
                "figures": [
                    {
                        "figure_id": "fig1",
                        "viz_type": "bar_chart",
                        "caption": "Test caption",
                        "alt_text": "Alt text",
                        "dpi": 300,
                        "width": 800,
                        "height": 600,
                        "rendering_info": {"color_palette": "colorblind_safe"},
                        "data_summary": {"n_groups": 3},
                    }
                ]
            },
            "messages": [MagicMock(content='{"viz_requests": [{}]}')],
        }
        
        result = await agent._check_quality(state)
        
        assert result.score >= 0
        assert isinstance(result.passed, bool)
    
    async def test_quality_check_empty_result(self):
        """Test quality check with no figures."""
        agent = DataVisualizationAgent()
        
        state = {
            "execution_result": {"figures": []},
            "messages": [MagicMock(content='{"viz_requests": [{}]}')],
        }
        
        result = await agent._check_quality(state)
        
        assert result.score < 0.85  # Should fail threshold
        assert result.passed is False


# =============================================================================
# Prompting Tests
# =============================================================================

class TestPrompting:
    """Tests for prompt generation."""
    
    def test_system_prompt(self):
        """Test system prompt generation."""
        agent = DataVisualizationAgent()
        prompt = agent._get_system_prompt()
        
        assert len(prompt) > 0
        assert "visualization" in prompt.lower() or "figure" in prompt.lower()
    
    def test_planning_prompt(self):
        """Test planning prompt generation."""
        agent = DataVisualizationAgent()
        state = {
            "messages": [MagicMock(content='{"study_data": {}, "viz_requests": []}')],
        }
        
        prompt = agent._get_planning_prompt(state)
        
        assert len(prompt) > 0
    
    def test_execution_prompt(self):
        """Test execution prompt generation."""
        agent = DataVisualizationAgent()
        state = {
            "messages": [MagicMock(content='{"study_data": {}}')],
        }
        
        prompt = agent._get_execution_prompt(state, "test context")
        
        assert len(prompt) > 0
        assert "context" in prompt.lower()


# =============================================================================
# Response Parsing Tests
# =============================================================================

class TestResponseParsing:
    """Tests for LLM response parsing."""
    
    def test_parse_json_response(self):
        """Test parsing JSON from response."""
        agent = DataVisualizationAgent()
        response = '''Here's the result:
```json
{
    "figures": [{"figure_id": "fig1", "viz_type": "bar_chart"}],
    "warnings": []
}
```
'''
        
        result = agent._parse_execution_result(response)
        
        assert "figures" in result
        assert len(result["figures"]) == 1
    
    def test_parse_invalid_response(self):
        """Test parsing invalid response."""
        agent = DataVisualizationAgent()
        response = "This is not valid JSON"
        
        result = agent._parse_execution_result(response)
        
        assert "figures" in result
        assert "warnings" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
