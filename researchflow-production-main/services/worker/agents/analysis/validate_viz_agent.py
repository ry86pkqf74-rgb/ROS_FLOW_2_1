#!/usr/bin/env python3
"""
Validation script for DataVisualizationAgent

Checks:
1. Type definitions import correctly
2. Enumerations have expected values
3. Data structures can be created
4. Serialization works

Run: python3 services/worker/agents/analysis/validate_viz_agent.py
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pandas as pd
import numpy as np

from visualization_types import (
    VizType, ExportFormat, JournalStyle, ColorPalette,
    VizRequest, Figure, VizResult, StudyContext,
    BarChartConfig, LineChartConfig, KMConfig,
    FlowStage, EffectSize,
)

def validate_enumerations():
    """Validate all enumerations."""
    print("🔍 Validating enumerations...")
    
    # VizType
    assert len(VizType.__members__) == 13, "VizType should have 13 members"
    assert VizType.BAR_CHART.value == "bar_chart"
    assert VizType.KAPLAN_MEIER.value == "kaplan_meier"
    print("  ✅ VizType (13 members)")
    
    # ExportFormat
    assert len(ExportFormat.__members__) == 5, "ExportFormat should have 5 members"
    assert ExportFormat.PNG.value == "png"
    assert ExportFormat.SVG.value == "svg"
    print("  ✅ ExportFormat (5 members)")
    
    # JournalStyle
    assert len(JournalStyle.__members__) == 10, "JournalStyle should have 10 members"
    assert JournalStyle.NATURE.value == "nature"
    assert JournalStyle.JAMA.value == "jama"
    print("  ✅ JournalStyle (10 members)")
    
    # ColorPalette
    assert len(ColorPalette.__members__) == 8, "ColorPalette should have 8 members"
    assert ColorPalette.COLORBLIND_SAFE.value == "colorblind_safe"
    print("  ✅ ColorPalette (8 members)")


def validate_configurations():
    """Validate configuration classes."""
    print("\n🔍 Validating configurations...")
    
    # BarChartConfig
    config = BarChartConfig(
        title="Test Chart",
        show_error_bars=True,
        dpi=300,
    )
    assert config.title == "Test Chart"
    assert config.dpi == 300
    print("  ✅ BarChartConfig")
    
    # LineChartConfig
    config = LineChartConfig(show_markers=True, line_width=2.0)
    assert config.show_markers is True
    assert config.line_width == 2.0
    print("  ✅ LineChartConfig")
    
    # KMConfig
    config = KMConfig(time_label="Time (months)", show_risk_table=True)
    assert config.time_label == "Time (months)"
    assert config.show_risk_table is True
    print("  ✅ KMConfig")


def validate_data_structures():
    """Validate data structure classes."""
    print("\n🔍 Validating data structures...")
    
    # VizRequest
    request = VizRequest(
        viz_type=VizType.BAR_CHART,
        data_columns={"x": "group", "y": "outcome"},
        title="Test",
    )
    assert request.viz_type == VizType.BAR_CHART
    assert "x" in request.data_columns
    print("  ✅ VizRequest")
    
    # Figure
    figure = Figure(
        figure_id="fig1",
        viz_type=VizType.LINE_CHART,
        width=800,
        height=600,
        dpi=300,
        caption="Test caption",
    )
    assert figure.figure_id == "fig1"
    assert figure.dpi == 300
    print("  ✅ Figure")
    
    # StudyContext
    context = StudyContext(
        study_title="Test Study",
        sample_size=100,
    )
    assert context.study_title == "Test Study"
    assert context.sample_size == 100
    print("  ✅ StudyContext")
    
    # FlowStage
    stage = FlowStage(
        name="Enrollment",
        n=500,
        reasons_excluded={"Not eligible": 50}
    )
    assert stage.name == "Enrollment"
    assert stage.n == 500
    print("  ✅ FlowStage")
    
    # EffectSize
    effect = EffectSize(
        study_id="study1",
        study_label="Smith 2020",
        effect_estimate=0.85,
        ci_lower=0.72,
        ci_upper=1.01,
        weight=0.25,
    )
    assert effect.study_id == "study1"
    assert effect.weight == 0.25
    print("  ✅ EffectSize")


def validate_serialization():
    """Validate to_dict() methods."""
    print("\n🔍 Validating serialization...")
    
    # VizRequest
    request = VizRequest(
        viz_type=VizType.SCATTER_PLOT,
        data_columns={"x": "age", "y": "outcome"},
    )
    result = request.to_dict()
    assert result["viz_type"] == "scatter_plot"
    assert "data_columns" in result
    print("  ✅ VizRequest.to_dict()")
    
    # Figure
    figure = Figure(figure_id="test", viz_type=VizType.BOX_PLOT)
    result = figure.to_dict()
    assert result["figure_id"] == "test"
    assert result["viz_type"] == "box_plot"
    assert "created_at" in result
    print("  ✅ Figure.to_dict()")
    
    # StudyContext
    context = StudyContext(study_title="Test", sample_size=50)
    result = context.to_dict()
    assert result["study_title"] == "Test"
    assert result["sample_size"] == 50
    print("  ✅ StudyContext.to_dict()")
    
    # VizResult
    viz_result = VizResult(
        figures=[figure],
        captions=["Caption 1"],
        total_figures=1,
    )
    result = viz_result.to_dict()
    assert len(result["figures"]) == 1
    assert "generated_at" in result
    print("  ✅ VizResult.to_dict()")


def validate_agent_stub():
    """Validate agent can be imported (stub only)."""
    print("\n🔍 Validating agent stub...")
    
    try:
        from data_visualization_agent import (
            DataVisualizationAgent,
            create_data_visualization_agent,
        )
        
        # Create agent
        agent = create_data_visualization_agent()
        assert agent is not None
        assert hasattr(agent, 'config')
        assert agent.config.name == "DataVisualizationAgent"
        assert 8 in agent.config.stages
        
        print("  ✅ Agent import and creation")
        print(f"     Name: {agent.config.name}")
        print(f"     Stages: {agent.config.stages}")
        print(f"     Quality threshold: {agent.config.quality_threshold}")
        
        # Check presets initialized
        assert hasattr(agent, 'style_presets')
        assert hasattr(agent, 'color_palettes')
        print("  ✅ Style presets initialized")
        
        # Check methods exist
        assert hasattr(agent, 'create_bar_chart')
        assert hasattr(agent, 'create_line_chart')
        assert hasattr(agent, 'create_kaplan_meier')
        assert hasattr(agent, 'create_forest_plot')
        print("  ✅ Chart creation methods present")
        
        return True
        
    except ImportError as e:
        print(f"  ⚠️  Agent import skipped (BaseAgent not available): {e}")
        return False


def main():
    """Run all validations."""
    print("=" * 60)
    print("DataVisualizationAgent Validation")
    print("=" * 60)
    
    try:
        validate_enumerations()
        validate_configurations()
        validate_data_structures()
        validate_serialization()
        agent_ok = validate_agent_stub()
        
        print("\n" + "=" * 60)
        print("✅ All validations passed!")
        print("=" * 60)
        
        print("\n📊 Summary:")
        print(f"  ✅ Type definitions: Complete")
        print(f"  ✅ Configurations: Complete")
        print(f"  ✅ Data structures: Complete")
        print(f"  ✅ Serialization: Complete")
        print(f"  {'✅' if agent_ok else '⚠️ '} Agent scaffold: {'Complete' if agent_ok else 'Partial (BaseAgent dependency)'}")
        
        print("\n🚀 Next steps:")
        print("  1. Install dependencies: pip install matplotlib seaborn lifelines pillow")
        print("  2. Run tests: pytest tests/test_data_visualization_agent.py -v")
        print("  3. Implement rendering: Fill TODO (Mercury) markers")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Validation failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
