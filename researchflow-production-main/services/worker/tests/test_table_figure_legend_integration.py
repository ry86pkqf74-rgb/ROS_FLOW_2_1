"""
Integration Tests for TableFigureLegendAgent

Tests the complete integration from API endpoints through to legend generation.

Phase 2: Stage 1b - API Integration Testing
"""

import pytest
import asyncio
from typing import Dict, Any, List
import sys
from pathlib import Path

# Add agents directory to path for imports
agents_dir = Path(__file__).parent.parent / "agents" / "writing"
sys.path.insert(0, str(agents_dir))

# Test imports
try:
    # Try absolute imports first
    import legend_types
    import table_figure_legend_agent
    
    Table = legend_types.Table
    Figure = legend_types.Figure
    TableFigureLegendState = legend_types.TableFigureLegendState
    JournalStyleEnum = legend_types.JournalStyleEnum
    PanelLabelStyle = legend_types.PanelLabelStyle
    
    create_table_figure_legend_agent = table_figure_legend_agent.create_table_figure_legend_agent
    TableFigureLegendAgent = table_figure_legend_agent.TableFigureLegendAgent
    JOURNAL_SPECIFICATIONS = table_figure_legend_agent.JOURNAL_SPECIFICATIONS
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    # Fallback for missing imports
    IMPORTS_AVAILABLE = False
    print(f"Warning: Could not import legend modules: {e}")
    
    # Create dummy classes for testing structure
    class Table:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class Figure:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class TableFigureLegendState:
        pass
    
    class JournalStyleEnum:
        DEFAULT = "default"
        NATURE = "nature"
        JAMA = "jama"
        NEJM = "nejm"
        PLOS = "plos"
        LANCET = "lancet"
    
    class PanelLabelStyle:
        UPPERCASE = "A, B, C"
        LOWERCASE = "a, b, c"
        NUMERIC = "1, 2, 3"
    
    def create_table_figure_legend_agent(**kwargs):
        return None
    
    TableFigureLegendAgent = None
    JOURNAL_SPECIFICATIONS = {}


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Legend modules not available")
class TestTableFigureLegendAgent:
    """Test suite for TableFigureLegendAgent functionality."""

    @pytest.fixture
    def sample_table(self) -> Table:
        """Create a sample table for testing."""
        return Table(
            id="test_table_1",
            title="Patient Demographics",
            headers=["Characteristic", "Treatment (n=50)", "Control (n=50)", "P-value"],
            rows=[
                ["Age, mean ± SD", "65.2 ± 12.4", "63.8 ± 11.9", "0.45"],
                ["Male sex, n (%)", "28 (56%)", "31 (62%)", "0.54"],
                ["BMI, kg/m²", "27.3 ± 4.2", "26.8 ± 3.9", "0.52"],
                ["Diabetes, n (%)", "15 (30%)", "18 (36%)", "0.52"],
                ["Hypertension, n (%)", "35 (70%)", "33 (66%)", "0.67"],
            ],
            contains_statistics=True,
            statistical_methods=["t-test", "chi-square test"],
            sample_size=100,
        )

    @pytest.fixture
    def sample_figure(self) -> Figure:
        """Create a sample figure for testing."""
        return Figure(
            id="test_figure_1",
            title="Treatment Efficacy Results",
            figure_type="bar_chart",
            has_panels=True,
            panel_info={
                "A": {"description": "Primary outcome by treatment group"},
                "B": {"description": "Secondary outcomes comparison"},
                "C": {"description": "Subgroup analysis results"},
            },
            data_summary={
                "primary_outcome": "HbA1c reduction",
                "sample_size": 100,
                "follow_up": "12 weeks",
            },
            analysis_methods=["ANOVA", "post-hoc testing"],
            statistical_tests=["Tukey HSD", "Bonferroni correction"],
            shows_significance=True,
            includes_error_bars=True,
        )

    @pytest.fixture
    def agent(self) -> TableFigureLegendAgent:
        """Create agent instance for testing."""
        return create_table_figure_legend_agent(
            default_journal=JournalStyleEnum.DEFAULT
        )

    async def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert agent is not None
        assert agent.default_journal == JournalStyleEnum.DEFAULT
        assert agent.quality_threshold == 0.85
        assert agent.max_iterations == 3

    async def test_table_analysis(self, agent, sample_table):
        """Test table analysis functionality."""
        analysis = agent._analyze_table(sample_table)
        
        # Check analysis structure
        assert "table_id" in analysis
        assert "headers" in analysis
        assert "row_count" in analysis
        assert "column_count" in analysis
        assert "contains_statistics" in analysis
        assert "potential_abbreviations" in analysis
        
        # Check values
        assert analysis["table_id"] == "test_table_1"
        assert analysis["row_count"] == 5
        assert analysis["column_count"] == 4
        assert analysis["contains_statistics"] is True

    async def test_figure_analysis(self, agent, sample_figure):
        """Test figure analysis functionality."""
        analysis = agent._analyze_figure(sample_figure)
        
        # Check analysis structure
        assert "figure_id" in analysis
        assert "figure_type" in analysis
        assert "has_panels" in analysis
        assert "panel_count" in analysis
        assert "analysis_methods" in analysis
        
        # Check values
        assert analysis["figure_id"] == "test_figure_1"
        assert analysis["figure_type"] == "bar_chart"
        assert analysis["has_panels"] is True
        assert analysis["panel_count"] == 3

    async def test_table_legend_generation(self, agent, sample_table):
        """Test table legend generation."""
        legend = await agent.generate_table_legend(
            table=sample_table,
            manuscript_context="Randomized trial of diabetes treatment",
            target_journal=JournalStyleEnum.JAMA,
        )
        
        # Check legend structure
        assert legend.table_id == "test_table_1"
        assert legend.title is not None
        assert len(legend.title) > 0
        assert legend.word_count > 0
        assert isinstance(legend.journal_compliant, bool)
        assert isinstance(legend.abbreviations, dict)
        
        # Check complete legend
        complete_legend = legend.get_complete_legend()
        assert len(complete_legend) > 0
        assert "Table" in complete_legend

    async def test_figure_legend_generation(self, agent, sample_figure):
        """Test figure legend generation."""
        legend = await agent.generate_figure_legend(
            figure=sample_figure,
            manuscript_context="Clinical trial results",
            target_journal=JournalStyleEnum.NATURE,
        )
        
        # Check legend structure
        assert legend.figure_id == "test_figure_1"
        assert legend.caption is not None
        assert len(legend.caption) > 0
        assert legend.word_count > 0
        assert isinstance(legend.journal_compliant, bool)
        
        # Check panel descriptions for multi-panel figure
        assert len(legend.panel_descriptions) > 0
        
        # Check complete legend
        complete_legend = legend.get_complete_legend()
        assert len(complete_legend) > 0
        assert "Figure" in complete_legend

    async def test_journal_compliance_validation(self, agent, sample_table):
        """Test journal compliance validation."""
        # Test with strict journal (Nature - 150 words max)
        legend_nature = await agent.generate_table_legend(
            table=sample_table,
            manuscript_context="Brief study context",
            target_journal=JournalStyleEnum.NATURE,
        )
        
        # Test with permissive journal (PLOS - 500 words max)
        legend_plos = await agent.generate_table_legend(
            table=sample_table,
            manuscript_context="Detailed study context with extensive background information",
            target_journal=JournalStyleEnum.PLOS,
        )
        
        # Both should be valid but may have different compliance
        assert isinstance(legend_nature.journal_compliant, bool)
        assert isinstance(legend_plos.journal_compliant, bool)
        
        # Nature should be more restrictive on word count
        nature_spec = JOURNAL_SPECIFICATIONS[JournalStyleEnum.NATURE]
        plos_spec = JOURNAL_SPECIFICATIONS[JournalStyleEnum.PLOS]
        assert nature_spec.max_legend_words < plos_spec.max_legend_words

    async def test_batch_legend_generation(self, agent, sample_table, sample_figure):
        """Test generating legends for multiple visuals."""
        # Create state with multiple tables and figures
        state = TableFigureLegendState(
            study_id="test_study",
            tables=[sample_table],
            figures=[sample_figure],
            manuscript_context="Comprehensive clinical trial analysis",
            target_journal="jama",
        )
        
        # Generate all legends
        updated_state = await agent.generate_all_legends(
            state=state,
            target_journal=JournalStyleEnum.JAMA,
        )
        
        # Check results
        assert len(updated_state.table_legends) == 1
        assert len(updated_state.figure_legends) == 1
        assert sample_table.id in updated_state.table_legends
        assert sample_figure.id in updated_state.figure_legends
        
        # Check master abbreviation list
        assert isinstance(updated_state.abbreviation_list, list)
        
        # Check total word count
        total_words = updated_state.get_total_word_count()
        assert total_words > 0

    def test_journal_specifications(self):
        """Test journal specifications database."""
        # Check all major journals are present
        assert JournalStyleEnum.NATURE in JOURNAL_SPECIFICATIONS
        assert JournalStyleEnum.JAMA in JOURNAL_SPECIFICATIONS
        assert JournalStyleEnum.NEJM in JOURNAL_SPECIFICATIONS
        assert JournalStyleEnum.LANCET in JOURNAL_SPECIFICATIONS
        assert JournalStyleEnum.PLOS in JOURNAL_SPECIFICATIONS
        
        # Check specification structure
        nature_spec = JOURNAL_SPECIFICATIONS[JournalStyleEnum.NATURE]
        assert hasattr(nature_spec, "max_legend_words")
        assert hasattr(nature_spec, "panel_label_style")
        assert hasattr(nature_spec, "abbreviation_placement")
        assert hasattr(nature_spec, "requires_footnotes")
        
        # Check Nature-specific requirements
        assert nature_spec.max_legend_words == 150  # Concise
        assert nature_spec.panel_label_style == PanelLabelStyle.LOWERCASE  # a, b, c
        assert nature_spec.concise_style is True

    def test_panel_label_styles(self, agent):
        """Test panel labeling functionality."""
        from legend_types import format_panel_label
        
        # Test different label styles
        assert format_panel_label("1", PanelLabelStyle.UPPERCASE) == "A"
        assert format_panel_label("2", PanelLabelStyle.UPPERCASE) == "B"
        assert format_panel_label("1", PanelLabelStyle.LOWERCASE) == "a"
        assert format_panel_label("1", PanelLabelStyle.NUMERIC) == "1"
        
        # Test panel description generation
        panel_info = {
            "1": {"description": "Primary analysis"},
            "2": {"description": "Secondary analysis"},
        }
        
        descriptions = agent._generate_panel_descriptions(
            panel_info, PanelLabelStyle.UPPERCASE
        )
        
        assert "A" in descriptions
        assert "B" in descriptions
        assert descriptions["A"] == "Primary analysis"

    def test_abbreviation_extraction(self):
        """Test abbreviation extraction utility."""
        from legend_types import extract_abbreviations_from_text
        
        text = "The BMI, HDL, and LDL levels were measured using standard protocols"
        abbreviations = extract_abbreviations_from_text(text)
        
        assert "BMI" in abbreviations
        assert "HDL" in abbreviations
        assert "LDL" in abbreviations

    async def test_error_handling(self, agent):
        """Test error handling in legend generation."""
        # Test with minimal/invalid table
        minimal_table = Table(
            id="minimal_table",
            headers=[],
            rows=[],
        )
        
        try:
            legend = await agent.generate_table_legend(
                table=minimal_table,
                manuscript_context="",
                target_journal=JournalStyleEnum.DEFAULT,
            )
            # Should still generate something, even if minimal
            assert legend is not None
        except Exception as e:
            # Should handle gracefully
            assert "failed" in str(e).lower() or "error" in str(e).lower()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Legend modules not available")
class TestLegendTypes:
    """Test legend type definitions and utilities."""

    def test_table_legend_creation(self):
        """Test TableLegend object creation."""
        from legend_types import TableLegend
        
        legend = TableLegend(
            table_id="test_table",
            title="Test Table Title",
            footnotes=["Test footnote"],
            abbreviations={"SD": "standard deviation"},
            word_count=25,
        )
        
        assert legend.table_id == "test_table"
        assert legend.title == "Test Table Title"
        assert len(legend.footnotes) == 1
        assert "SD" in legend.abbreviations
        
        # Test formatted title
        legend.table_number = 1
        formatted = legend.get_formatted_title()
        assert "Table 1" in formatted

    def test_figure_legend_creation(self):
        """Test FigureLegend object creation."""
        from legend_types import FigureLegend
        
        legend = FigureLegend(
            figure_id="test_figure",
            caption="Test Figure Caption",
            panel_descriptions={"A": "Panel A description"},
            word_count=30,
            has_multiple_panels=True,
        )
        
        assert legend.figure_id == "test_figure"
        assert legend.caption == "Test Figure Caption"
        assert "A" in legend.panel_descriptions
        assert legend.has_multiple_panels is True

    def test_state_validation(self):
        """Test TableFigureLegendState validation."""
        state = TableFigureLegendState(
            study_id="test_study",
            tables=[],
            figures=[],
        )
        
        # Test validation of completeness
        issues = state.validate_completeness()
        assert isinstance(issues, list)
        
        # Test summary generation
        summary = state.get_summary()
        assert "study_id" in summary
        assert "tables_processed" in summary
        assert "figures_processed" in summary


if __name__ == "__main__":
    # Run a simple test if called directly
    if IMPORTS_AVAILABLE:
        async def simple_test():
            agent = create_table_figure_legend_agent()
            
            test_table = Table(
                id="simple_test",
                title="Test Table",
                headers=["A", "B", "C"],
                rows=[["1", "2", "3"]],
                sample_size=10,
            )
            
            legend = await agent.generate_table_legend(
                table=test_table,
                manuscript_context="Simple test",
                target_journal=JournalStyleEnum.DEFAULT,
            )
            
            print(f"Generated legend: {legend.title}")
            print(f"Complete: {legend.get_complete_legend()}")
            print("✅ Basic functionality test passed!")
        
        asyncio.run(simple_test())
    else:
        print("❌ Cannot run tests - legend modules not available")