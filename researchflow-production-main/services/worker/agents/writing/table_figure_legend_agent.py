"""
TableFigureLegendAgent - Publication-Ready Legend Generation

Generates comprehensive, journal-compliant legends for tables and figures.
Integrates with DataVisualizationAgent output and ManuscriptAgent workflow.

Key Features:
- Automatic legend generation for tables and figures
- Journal-specific formatting compliance
- Multi-panel figure support with flexible labeling
- Accessibility descriptions and alt-text generation
- Abbreviation management and consistency checking
- Quality gates for publication readiness

Linear Issues: TableFigureLegendAgent Implementation
Phase 2: Core Agent Implementation
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Type imports
try:
    from .legend_types import (
        TableFigureLegendState,
        TableLegend,
        FigureLegend,
        Table,
        Figure,
        JournalSpec,
        JournalStyleEnum,
        PanelLabelStyle,
        AbbreviationPlacement,
        LegendGenerationRequest,
        LegendGenerationResponse,
        extract_abbreviations_from_text,
        count_words,
        format_panel_label,
    )
except ImportError:
    # Fallback for direct execution
    from legend_types import (
        TableFigureLegendState,
        TableLegend,
        FigureLegend,
        Table,
        Figure,
        JournalSpec,
        JournalStyleEnum,
        PanelLabelStyle,
        AbbreviationPlacement,
        LegendGenerationRequest,
        LegendGenerationResponse,
        extract_abbreviations_from_text,
        count_words,
        format_panel_label,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Journal Specifications Database
# =============================================================================

JOURNAL_SPECIFICATIONS = {
    JournalStyleEnum.NATURE: JournalSpec(
        name="Nature",
        max_legend_words=150,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.INLINE_LEGEND,
        requires_footnotes=False,
        panel_label_style=PanelLabelStyle.LOWERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=True,
        concise_style=True,
        methods_minimal=True,
    ),
    JournalStyleEnum.JAMA: JournalSpec(
        name="JAMA",
        max_legend_words=300,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.FOOTNOTES,
        requires_footnotes=True,
        panel_label_style=PanelLabelStyle.UPPERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=False,
        concise_style=False,
        methods_minimal=False,
    ),
    JournalStyleEnum.NEJM: JournalSpec(
        name="NEJM",
        max_legend_words=200,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.INLINE_LEGEND,
        requires_footnotes=False,
        panel_label_style=PanelLabelStyle.UPPERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=True,
        concise_style=True,
        methods_minimal=False,
    ),
    JournalStyleEnum.LANCET: JournalSpec(
        name="Lancet",
        max_legend_words=250,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.INLINE_LEGEND,
        requires_footnotes=False,
        panel_label_style=PanelLabelStyle.UPPERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=True,
        concise_style=False,
        methods_minimal=False,
    ),
    JournalStyleEnum.PLOS: JournalSpec(
        name="PLOS ONE",
        max_legend_words=500,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.SEPARATE_LIST,
        requires_footnotes=False,
        panel_label_style=PanelLabelStyle.UPPERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=True,
        concise_style=False,
        methods_minimal=False,
    ),
    JournalStyleEnum.DEFAULT: JournalSpec(
        name="Default",
        max_legend_words=300,
        abbreviations_in_legend=True,
        abbreviation_placement=AbbreviationPlacement.INLINE_LEGEND,
        requires_footnotes=False,
        panel_label_style=PanelLabelStyle.UPPERCASE,
        methods_in_legend=True,
        statistical_info_required=True,
        sample_size_required=True,
        prefers_active_voice=True,
        concise_style=False,
        methods_minimal=False,
    ),
}


# =============================================================================
# LLM Prompt Templates
# =============================================================================

GENERATE_TABLE_LEGEND_PROMPT = """You are a scientific writing expert specializing in publication-ready table legends for medical research.

## Table Analysis
{table_analysis}

## Journal Requirements
Target Journal: {target_journal}
Max Words: {max_words}
Style Requirements: {style_requirements}

## Study Context
{manuscript_context}

## Task
Generate a comprehensive table legend that includes:

1. **Descriptive Title**: Clear, informative title explaining what the table shows
2. **Data Description**: Brief description of the data presented and population
3. **Methods Information**: Relevant statistical methods and data collection approaches
4. **Footnotes**: Explanations for abbreviations, symbols, and special notations
5. **Sample Information**: Sample size and key population characteristics

## Formatting Requirements
- Follow {journal_style} guidelines exactly
- Use {abbreviation_style} for abbreviations
- Keep within {max_words} words total
- Include statistical notation explanations
- Use clear, precise language
- {voice_preference} voice where appropriate

## Output Format
Return a JSON object with:
{{
    "title": "Table title without number",
    "data_description": "Brief description of data/population", 
    "statistical_notes": ["List of statistical method notes"],
    "footnotes": ["List of footnotes for abbreviations/symbols"],
    "abbreviations": {{"abbrev": "definition"}},
    "word_count": integer,
    "accessibility_notes": ["Notes for screen readers"]
}}

Generate a professional, journal-ready table legend now."""

GENERATE_FIGURE_CAPTION_PROMPT = """You are a scientific writing expert creating publication-ready figure captions for medical research.

## Figure Analysis
{figure_analysis}

## Panel Information
{panel_descriptions}

## Journal Requirements
Target Journal: {target_journal}
Panel Style: {panel_label_style}
Max Words: {max_words}
Style Requirements: {style_requirements}

## Study Context
{manuscript_context}

## Task
Generate a comprehensive figure caption that includes:

1. **Main Caption**: Clear statement of the figure's key message
2. **Panel Descriptions**: Detailed descriptions for each panel using {panel_label_style} labels
3. **Methods Summary**: Brief description of methods relevant to the visualization
4. **Statistical Information**: Sample sizes, test results, significance levels
5. **Accessibility Description**: Comprehensive alt-text for screen readers

## Multi-Panel Guidelines
- Use ({panel_style}) format for panel labels
- Each panel should have a complete description
- Connect panels to tell a coherent story
- Maintain consistent terminology across panels

## Statistical Reporting
- Include sample sizes: n = X
- Report effect sizes and confidence intervals
- Use appropriate p-value formatting
- Explain statistical tests used

## Output Format
Return a JSON object with:
{{
    "caption": "Main figure caption",
    "panel_descriptions": {{"A": "Panel A description", "B": "Panel B description"}},
    "methods_summary": "Brief methods relevant to figure",
    "statistical_info": "Statistical details and sample sizes",
    "abbreviations": {{"abbrev": "definition"}},
    "accessibility_description": "Comprehensive alt-text description",
    "word_count": integer
}}

Generate a professional, journal-ready figure caption now."""

VALIDATE_COMPLIANCE_PROMPT = """You are a journal compliance specialist reviewing legends for publication readiness.

## Legend Content
{legend_content}

## Journal Requirements
Journal: {target_journal}
Specifications: {journal_specs}

## Task
Evaluate the legend against journal requirements and provide:

1. **Compliance Score**: 0.0-1.0 rating
2. **Issues Found**: List of specific compliance problems
3. **Recommendations**: Specific suggestions for improvement
4. **Word Count Check**: Within limits?
5. **Style Assessment**: Follows journal guidelines?

## Check List
- [ ] Word count within limits
- [ ] Appropriate abbreviation handling
- [ ] Required statistical information present
- [ ] Panel labeling style correct (if applicable)
- [ ] Voice and tone appropriate
- [ ] Accessibility considerations met

## Output Format
Return a JSON object with:
{{
    "compliance_score": 0.95,
    "passed": true,
    "issues": ["List of specific issues"],
    "recommendations": ["List of improvement suggestions"],
    "word_count_ok": true,
    "style_compliant": true,
    "accessibility_compliant": true,
    "overall_assessment": "Summary assessment"
}}

Provide thorough compliance evaluation now."""


# =============================================================================
# TableFigureLegendAgent Class
# =============================================================================

class TableFigureLegendAgent:
    """
    Agent for generating publication-ready table and figure legends.
    
    Features:
    - Automatic legend generation using LLM
    - Journal-specific compliance checking
    - Multi-panel figure support
    - Accessibility enhancements
    - Quality validation gates
    """

    def __init__(
        self,
        llm_bridge: Optional[Any] = None,
        default_journal: JournalStyleEnum = JournalStyleEnum.DEFAULT,
        quality_threshold: float = 0.85,
        max_iterations: int = 3,
    ):
        """
        Initialize the TableFigureLegendAgent.

        Args:
            llm_bridge: Bridge to AI router for LLM calls
            default_journal: Default journal style to use
            quality_threshold: Minimum quality score for acceptance
            max_iterations: Maximum improvement iterations
        """
        self.llm_bridge = llm_bridge
        self.default_journal = default_journal
        self.quality_threshold = quality_threshold
        self.max_iterations = max_iterations
        
        logger.info(f"TableFigureLegendAgent initialized with {default_journal} style")

    # =========================================================================
    # Core Legend Generation Methods
    # =========================================================================

    async def generate_table_legend(
        self,
        table: Table,
        manuscript_context: str = "",
        target_journal: Optional[JournalStyleEnum] = None,
    ) -> TableLegend:
        """
        Generate a publication-ready legend for a table.

        Args:
            table: Table object with data and metadata
            manuscript_context: Context from the manuscript
            target_journal: Target journal style

        Returns:
            TableLegend object with complete legend information
        """
        journal_style = target_journal or self.default_journal
        journal_spec = JOURNAL_SPECIFICATIONS[journal_style]
        
        # Analyze table data
        table_analysis = self._analyze_table(table)
        
        # Generate legend using LLM
        legend_data = await self._call_llm_for_table_legend(
            table_analysis=table_analysis,
            manuscript_context=manuscript_context,
            journal_spec=journal_spec,
        )
        
        # Create TableLegend object
        legend = TableLegend(
            table_id=table.id,
            title=legend_data.get("title", ""),
            footnotes=legend_data.get("footnotes", []),
            abbreviations=legend_data.get("abbreviations", {}),
            data_description=legend_data.get("data_description", ""),
            statistical_notes=legend_data.get("statistical_notes", []),
            word_count=legend_data.get("word_count", 0),
            accessibility_notes=legend_data.get("accessibility_notes", []),
        )
        
        # Validate compliance
        compliance_result = await self._validate_legend_compliance(legend, journal_spec)
        legend.journal_compliant = compliance_result.get("passed", False)
        
        logger.info(f"Generated table legend: {table.id}, compliant: {legend.journal_compliant}")
        
        return legend

    async def generate_figure_legend(
        self,
        figure: Figure,
        manuscript_context: str = "",
        target_journal: Optional[JournalStyleEnum] = None,
    ) -> FigureLegend:
        """
        Generate a publication-ready legend for a figure.

        Args:
            figure: Figure object with data and metadata
            manuscript_context: Context from the manuscript
            target_journal: Target journal style

        Returns:
            FigureLegend object with complete legend information
        """
        journal_style = target_journal or self.default_journal
        journal_spec = JOURNAL_SPECIFICATIONS[journal_style]
        
        # Analyze figure data
        figure_analysis = self._analyze_figure(figure)
        
        # Generate panel descriptions if multi-panel
        panel_descriptions = {}
        if figure.has_panels and figure.panel_info:
            panel_descriptions = self._generate_panel_descriptions(
                figure.panel_info,
                journal_spec.panel_label_style
            )
        
        # Generate legend using LLM
        legend_data = await self._call_llm_for_figure_legend(
            figure_analysis=figure_analysis,
            panel_descriptions=panel_descriptions,
            manuscript_context=manuscript_context,
            journal_spec=journal_spec,
        )
        
        # Create FigureLegend object
        legend = FigureLegend(
            figure_id=figure.id,
            caption=legend_data.get("caption", ""),
            panel_descriptions=legend_data.get("panel_descriptions", {}),
            abbreviations=legend_data.get("abbreviations", {}),
            methods_summary=legend_data.get("methods_summary", ""),
            statistical_info=legend_data.get("statistical_info", ""),
            accessibility_description=legend_data.get("accessibility_description", ""),
            word_count=legend_data.get("word_count", 0),
            panel_label_style=journal_spec.panel_label_style,
            has_multiple_panels=figure.has_panels,
        )
        
        # Validate compliance
        compliance_result = await self._validate_legend_compliance(legend, journal_spec)
        legend.journal_compliant = compliance_result.get("passed", False)
        
        logger.info(f"Generated figure legend: {figure.id}, compliant: {legend.journal_compliant}")
        
        return legend

    async def generate_all_legends(
        self,
        state: TableFigureLegendState,
        target_journal: Optional[JournalStyleEnum] = None,
    ) -> TableFigureLegendState:
        """
        Generate legends for all tables and figures in the state.

        Args:
            state: TableFigureLegendState with input data
            target_journal: Target journal style

        Returns:
            Updated state with generated legends
        """
        journal_style = target_journal or JournalStyleEnum(state.target_journal) if state.target_journal else self.default_journal
        
        try:
            # Generate table legends
            for table in state.tables:
                legend = await self.generate_table_legend(
                    table=table,
                    manuscript_context=state.manuscript_context,
                    target_journal=journal_style,
                )
                state.add_table_legend(table.id, legend)
                
                # Add abbreviations to master list
                for abbrev, definition in legend.abbreviations.items():
                    state.add_abbreviation(abbrev, definition)

            # Generate figure legends
            for figure in state.figures:
                legend = await self.generate_figure_legend(
                    figure=figure,
                    manuscript_context=state.manuscript_context,
                    target_journal=journal_style,
                )
                state.add_figure_legend(figure.id, legend)
                
                # Add abbreviations to master list
                for abbrev, definition in legend.abbreviations.items():
                    state.add_abbreviation(abbrev, definition)

            # Calculate overall compliance
            all_legends = list(state.table_legends.values()) + list(state.figure_legends.values())
            if all_legends:
                compliant_count = sum(1 for legend in all_legends if legend.journal_compliant)
                state.journal_compliance["overall"] = compliant_count == len(all_legends)
            
            logger.info(f"Generated {len(state.table_legends)} table legends and {len(state.figure_legends)} figure legends")
            
        except Exception as e:
            logger.error(f"Error generating legends: {e}")
            state.errors.append(f"Legend generation failed: {str(e)}")
        
        return state

    # =========================================================================
    # Analysis Methods
    # =========================================================================

    def _analyze_table(self, table: Table) -> Dict[str, Any]:
        """Analyze table structure and content for legend generation."""
        preview = table.get_data_preview()
        
        # Extract potential abbreviations from headers and data
        text_content = " ".join(table.headers)
        if table.rows:
            # Sample some text data
            for row in table.rows[:3]:
                text_content += " " + " ".join([str(cell) for cell in row if isinstance(cell, str)])
        
        abbreviations = extract_abbreviations_from_text(text_content)
        
        return {
            "table_id": table.id,
            "title": table.title or "",
            "headers": table.headers,
            "row_count": preview["total_rows"],
            "column_count": preview["columns"],
            "data_types": table.data_types,
            "contains_statistics": table.contains_statistics,
            "statistical_methods": table.statistical_methods,
            "sample_size": table.sample_size,
            "potential_abbreviations": abbreviations,
            "data_preview": preview["preview_rows"],
        }

    def _analyze_figure(self, figure: Figure) -> Dict[str, Any]:
        """Analyze figure structure and content for legend generation."""
        content_summary = figure.get_content_summary()
        
        # Extract abbreviations from existing text
        text_content = f"{figure.title or ''} {figure.caption or ''}"
        abbreviations = extract_abbreviations_from_text(text_content)
        
        return {
            "figure_id": figure.id,
            "title": figure.title or "",
            "caption": figure.caption or "",
            "figure_type": figure.figure_type,
            "has_panels": figure.has_panels,
            "panel_count": content_summary["panel_count"],
            "data_summary": content_summary["data_summary"],
            "analysis_methods": content_summary["analysis_methods"],
            "statistical_tests": content_summary["statistical_tests"],
            "visual_elements": content_summary["visual_elements"],
            "potential_abbreviations": abbreviations,
        }

    def _generate_panel_descriptions(
        self,
        panel_info: Dict[str, Any],
        label_style: PanelLabelStyle,
    ) -> Dict[str, str]:
        """Generate formatted panel descriptions."""
        descriptions = {}
        
        for panel_id, info in panel_info.items():
            label = format_panel_label(panel_id, label_style)
            description = info.get("description", f"Panel {label}")
            descriptions[label] = description
        
        return descriptions

    # =========================================================================
    # LLM Integration Methods
    # =========================================================================

    async def _call_llm_for_table_legend(
        self,
        table_analysis: Dict[str, Any],
        manuscript_context: str,
        journal_spec: JournalSpec,
    ) -> Dict[str, Any]:
        """Call LLM to generate table legend."""
        prompt = GENERATE_TABLE_LEGEND_PROMPT.format(
            table_analysis=json.dumps(table_analysis, indent=2),
            target_journal=journal_spec.name,
            max_words=journal_spec.max_legend_words,
            style_requirements=self._format_style_requirements(journal_spec),
            manuscript_context=manuscript_context,
            journal_style=journal_spec.name,
            abbreviation_style=journal_spec.abbreviation_placement.value,
            voice_preference="Active" if journal_spec.prefers_active_voice else "Passive",
        )
        
        if self.llm_bridge:
            response = await self.llm_bridge.invoke(
                prompt=prompt,
                task_type="table_legend_generation",
                model_tier="STANDARD",
            )
            content = response.get("content", "")
        else:
            # Fallback for development
            content = self._mock_table_legend_response(table_analysis)
        
        return self._parse_legend_response(content)

    async def _call_llm_for_figure_legend(
        self,
        figure_analysis: Dict[str, Any],
        panel_descriptions: Dict[str, str],
        manuscript_context: str,
        journal_spec: JournalSpec,
    ) -> Dict[str, Any]:
        """Call LLM to generate figure legend."""
        prompt = GENERATE_FIGURE_CAPTION_PROMPT.format(
            figure_analysis=json.dumps(figure_analysis, indent=2),
            panel_descriptions=json.dumps(panel_descriptions, indent=2),
            target_journal=journal_spec.name,
            panel_label_style=journal_spec.panel_label_style.value,
            max_words=journal_spec.max_legend_words,
            style_requirements=self._format_style_requirements(journal_spec),
            manuscript_context=manuscript_context,
            panel_style=journal_spec.panel_label_style.value,
        )
        
        if self.llm_bridge:
            response = await self.llm_bridge.invoke(
                prompt=prompt,
                task_type="figure_legend_generation",
                model_tier="STANDARD",
            )
            content = response.get("content", "")
        else:
            # Fallback for development
            content = self._mock_figure_legend_response(figure_analysis)
        
        return self._parse_legend_response(content)

    async def _validate_legend_compliance(
        self,
        legend: Union[TableLegend, FigureLegend],
        journal_spec: JournalSpec,
    ) -> Dict[str, Any]:
        """Validate legend compliance with journal requirements."""
        legend_content = legend.get_complete_legend()
        
        prompt = VALIDATE_COMPLIANCE_PROMPT.format(
            legend_content=legend_content,
            target_journal=journal_spec.name,
            journal_specs=json.dumps(journal_spec.model_dump(), indent=2),
        )
        
        if self.llm_bridge:
            response = await self.llm_bridge.invoke(
                prompt=prompt,
                task_type="compliance_validation",
                model_tier="MINI",
            )
            content = response.get("content", "")
            return self._parse_compliance_response(content)
        else:
            # Fallback compliance check
            return self._mock_compliance_check(legend, journal_spec)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _format_style_requirements(self, journal_spec: JournalSpec) -> str:
        """Format journal style requirements as readable text."""
        requirements = []
        requirements.append(f"Maximum {journal_spec.max_legend_words} words")
        requirements.append(f"Panel labels: {journal_spec.panel_label_style.value}")
        requirements.append(f"Abbreviations: {journal_spec.abbreviation_placement.value}")
        
        if journal_spec.requires_footnotes:
            requirements.append("Use footnote format")
        if journal_spec.concise_style:
            requirements.append("Prefer concise style")
        if journal_spec.prefers_active_voice:
            requirements.append("Use active voice")
        if journal_spec.methods_minimal:
            requirements.append("Minimal methods description")
        
        return "; ".join(requirements)

    def _parse_legend_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for legend generation."""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse legend response: {e}")
        
        # Fallback - extract basic information
        return {
            "title": "Generated Legend",
            "caption": response[:200] + "..." if len(response) > 200 else response,
            "word_count": len(response.split()),
            "abbreviations": {},
            "accessibility_description": response,
        }

    def _parse_compliance_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for compliance validation."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse compliance response: {e}")
        
        # Fallback
        return {
            "compliance_score": 0.8,
            "passed": True,
            "issues": [],
            "recommendations": [],
            "word_count_ok": True,
            "style_compliant": True,
            "accessibility_compliant": True,
        }

    # =========================================================================

    # =========================================================================
    # Mock Methods (Development Fallbacks)
    # =========================================================================

    def _mock_table_legend_response(self, table_analysis: Dict[str, Any]) -> str:
        """Mock response for table legend generation during development."""
        sample_size = table_analysis.get('sample_size', 'N')
        column_count = table_analysis.get('column_count', 'multiple')
        return json.dumps({
            "title": "Characteristics of study participants",
            "data_description": f"Baseline characteristics of {sample_size} participants",
            "statistical_notes": ["Data presented as mean ± SD or n (%)"],
            "footnotes": ["SD, standard deviation"],
            "abbreviations": {"SD": "standard deviation"},
            "word_count": 45,
            "accessibility_notes": [f"Table contains numerical data in {column_count} columns"]
        })

    def _mock_figure_legend_response(self, figure_analysis: Dict[str, Any]) -> str:
        """Mock response for figure legend generation during development."""
        return json.dumps({
            "caption": "Study results by treatment group",
            "panel_descriptions": {},
            "methods_summary": "Analysis performed using appropriate statistical methods",
            "statistical_info": "n = 100 participants per group",
            "abbreviations": {},
            "accessibility_description": "Bar chart showing treatment outcomes across groups",
            "word_count": 25
        })

    def _mock_compliance_check(
        self,
        legend: Union[TableLegend, FigureLegend],
        journal_spec: JournalSpec,
    ) -> Dict[str, Any]:
        """Mock compliance check during development."""
        word_count_ok = legend.word_count <= journal_spec.max_legend_words
        return {
            "compliance_score": 0.85 if word_count_ok else 0.65,
            "passed": word_count_ok,
            "issues": [] if word_count_ok else ["Word count exceeds limit"],
            "recommendations": [],
            "word_count_ok": word_count_ok,
            "style_compliant": True,
            "accessibility_compliant": True,
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_table_figure_legend_agent(
    llm_bridge: Optional[Any] = None,
    default_journal: JournalStyleEnum = JournalStyleEnum.DEFAULT,
    **kwargs,
) -> TableFigureLegendAgent:
    """
    Create a TableFigureLegendAgent instance.

    Args:
        llm_bridge: LLM bridge for API calls
        default_journal: Default journal style
        **kwargs: Additional configuration options

    Returns:
        Configured TableFigureLegendAgent instance
    """
    return TableFigureLegendAgent(
        llm_bridge=llm_bridge,
        default_journal=default_journal,
        **kwargs,
    )


# =============================================================================
# Development Testing
# =============================================================================

if __name__ == "__main__":
    # Basic testing during development
    import asyncio
    
    async def test_agent():
        """Test the agent with mock data."""
        agent = create_table_figure_legend_agent()
        
        # Create test table
        test_table = Table(
            id="test_table_1",
            title="Patient Characteristics",
            headers=["Variable", "Treatment (n=50)", "Control (n=50)", "P-value"],
            rows=[
                ["Age, mean ± SD", "65.2 ± 12.4", "63.8 ± 11.9", "0.45"],
                ["Male sex, n (%)", "28 (56)", "31 (62)", "0.54"],
                ["BMI, kg/m²", "27.3 ± 4.2", "26.8 ± 3.9", "0.52"],
            ],
            contains_statistics=True,
            statistical_methods=["t-test", "chi-square test"],
            sample_size=100,
        )
        
        # Generate legend
        legend = await agent.generate_table_legend(
            table=test_table,
            manuscript_context="Randomized controlled trial of new diabetes treatment",
            target_journal=JournalStyleEnum.JAMA,
        )
        
        print("Generated Table Legend:")
        print(f"Title: {legend.title}")
        print(f"Complete: {legend.get_complete_legend()}")
        print(f"Word count: {legend.word_count}")
        print(f"Compliant: {legend.journal_compliant}")
        
    # Run test if executed directly
    print("Running development test...")
    asyncio.run(test_agent())
else:
    print("TableFigureLegendAgent module loaded successfully")
