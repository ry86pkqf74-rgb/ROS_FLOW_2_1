"""Writing agents for manuscript generation and results interpretation.

This module contains agents responsible for:
- Results interpretation and clinical significance assessment
- Manuscript writing and narrative synthesis
- Table and figure legend generation
- Citation generation and formatting
- Quality review and editorial assistance

Key Components:
- ResultsInterpretationAgent: Stage 9 clinical results interpretation
- TableFigureLegendAgent: Publication-ready legend generation
- Type definitions: Comprehensive data models and enums
- Utility functions: Clinical interpretation and analysis tools
- Testing suite: Comprehensive test coverage
"""

from .results_interpretation_agent import (
    ResultsInterpretationAgent, 
    create_results_interpretation_agent,
    process_interpretation_request
)
from .table_figure_legend_agent import (
    TableFigureLegendAgent,
    create_table_figure_legend_agent
)
from .legend_types import (
    TableFigureLegendState,
    TableLegend,
    FigureLegend,
    Table,
    Figure,
    JournalSpec,
    JournalStyleEnum,
    PanelLabelStyle,
    LegendGenerationRequest,
    LegendGenerationResponse
)
from .results_types import (
    ResultsInterpretationState,
    Finding,
    ClinicalSignificanceLevel,
    ConfidenceLevel,
    EffectMagnitude,
    LimitationType,
    Limitation,
    InterpretationRequest,
    InterpretationResponse
)
from .results_utils import (
    interpret_p_value,
    assess_clinical_magnitude,
    calculate_nnt,
    interpret_cohens_d,
    format_clinical_narrative,
    generate_apa_summary
)

__all__ = [
    # Main agents
    "ResultsInterpretationAgent", 
    "create_results_interpretation_agent",
    "process_interpretation_request",
    "TableFigureLegendAgent",
    "create_table_figure_legend_agent",
    
    # Core types
    "ResultsInterpretationState",
    "Finding",
    "ClinicalSignificanceLevel",
    "ConfidenceLevel", 
    "EffectMagnitude",
    "LimitationType",
    "Limitation",
    
    # Request/Response types
    "InterpretationRequest",
    "InterpretationResponse",
    "LegendGenerationRequest",
    "LegendGenerationResponse",
    
    # Legend types
    "TableFigureLegendState",
    "TableLegend",
    "FigureLegend",
    "Table",
    "Figure",
    "JournalSpec",
    "JournalStyleEnum",
    "PanelLabelStyle",
    
    # Utility functions
    "interpret_p_value",
    "assess_clinical_magnitude",
    "calculate_nnt",
    "interpret_cohens_d",
    "format_clinical_narrative",
    "generate_apa_summary"
]