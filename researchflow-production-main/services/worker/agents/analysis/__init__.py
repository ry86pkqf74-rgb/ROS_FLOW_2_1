"""Analysis Phase Agents

Agents for the analysis phase of the research workflow.
"""

from .lit_search_agent import (
    LitSearchAgent,
    create_lit_search_agent,
    StudyContext,
    Paper,
    RankedPaper,
    Citation,
    LitSearchResult,
)

from .statistical_analysis_agent import (
    StatisticalAnalysisAgent,
    create_statistical_analysis_agent,
)

from .statistical_types import (
    StudyData,
    TestType,
    DescriptiveStats,
    HypothesisTestResult,
    EffectSize,
    ConfidenceInterval,
    AssumptionCheckResult,
    StatisticalResult,
    FigureSpec,
    PowerAnalysisResult,
)

from .data_visualization_agent import (
    DataVisualizationAgent,
    create_data_visualization_agent,
)

from .visualization_types import (
    VizType,
    VizRequest,
    VizResult,
    Figure,
    BarChartConfig,
    LineChartConfig,
    ScatterConfig,
    BoxPlotConfig,
    KMConfig,
    ForestConfig,
    FlowStage,
    EffectSize as VizEffectSize,
    StudyContext as VizStudyContext,
    JournalStyle,
    ColorPalette,
    ExportFormat,
    Orientation,
)

from .meta_analysis_agent import (
    MetaAnalysisAgent,
    create_meta_analysis_agent,
)

from .meta_analysis_types import (
    StudyEffect,
    MetaAnalysisConfig,
    EffectMeasure,
    ModelType,
    HeterogeneityResult,
    PublicationBiasResult,
    SubgroupResult,
    SensitivityAnalysisResult,
    MetaAnalysisResult,
)

from .prisma_agent import (
    PRISMAAgent,
    create_prisma_agent,
)

from .prisma_types import (
    PRISMAFlowchartData,
    SearchStrategy,
    PRISMAChecklistItem,
    RiskOfBiasSummary,
    PRISMAReport,
    PRISMAStage,
    SearchDatabase,
)

from .analysis_pipeline import (
    AnalysisPipeline,
    create_analysis_pipeline,
    AnalysisStage,
    StageResult,
    PipelineResult,
)

from .gap_analysis_agent import (
    GapAnalysisAgent,
    create_gap_analysis_agent,
)

from .gap_analysis_types import (
    GapType,
    EvidenceLevel,
    Addressability,
    GapPriority,
    Finding,
    LiteratureAlignment,
    ComparisonResult,
    KnowledgeGap,
    MethodGap,
    PopulationGap,
    TemporalGap,
    GeographicGap,
    Gap,
    PrioritizedGap,
    PrioritizationMatrix,
    PICOFramework,
    ResearchSuggestion,
    GapAnalysisResult,
    StudyMetadata,
)

__all__ = [
    # Literature search
    "LitSearchAgent",
    "create_lit_search_agent",
    "StudyContext",
    "Paper",
    "RankedPaper",
    "Citation",
    "LitSearchResult",
    # Statistical analysis
    "StatisticalAnalysisAgent",
    "create_statistical_analysis_agent",
    "StudyData",
    "TestType",
    "DescriptiveStats",
    "HypothesisTestResult",
    "EffectSize",
    "ConfidenceInterval",
    "AssumptionCheckResult",
    "StatisticalResult",
    "FigureSpec",
    "PowerAnalysisResult",
    # Data visualization
    "DataVisualizationAgent",
    "create_data_visualization_agent",
    "VizType",
    "VizRequest",
    "VizResult",
    "Figure",
    "BarChartConfig",
    "LineChartConfig",
    "ScatterConfig",
    "BoxPlotConfig",
    "KMConfig",
    "ForestConfig",
    "FlowStage",
    "VizEffectSize",
    "VizStudyContext",
    "JournalStyle",
    "ColorPalette",
    "ExportFormat",
    "Orientation",
    # Meta-analysis
    "MetaAnalysisAgent",
    "create_meta_analysis_agent",
    "StudyEffect",
    "MetaAnalysisConfig",
    "EffectMeasure",
    "ModelType",
    "HeterogeneityResult",
    "PublicationBiasResult",
    "SubgroupResult",
    "SensitivityAnalysisResult",
    "MetaAnalysisResult",
    # PRISMA reporting
    "PRISMAAgent",
    "create_prisma_agent",
    "PRISMAFlowchartData",
    "SearchStrategy",
    "PRISMAChecklistItem",
    "RiskOfBiasSummary",
    "PRISMAReport",
    "PRISMAStage",
    "SearchDatabase",
    # Analysis pipeline
    "AnalysisPipeline",
    "create_analysis_pipeline",
    "AnalysisStage",
    "StageResult",
    "PipelineResult",
    # Gap analysis
    "GapAnalysisAgent",
    "create_gap_analysis_agent",
    "GapType",
    "EvidenceLevel",
    "Addressability",
    "GapPriority",
    "Finding",
    "LiteratureAlignment",
    "ComparisonResult",
    "KnowledgeGap",
    "MethodGap",
    "PopulationGap",
    "TemporalGap",
    "GeographicGap",
    "Gap",
    "PrioritizedGap",
    "PrioritizationMatrix",
    "PICOFramework",
    "ResearchSuggestion",
    "GapAnalysisResult",
    "StudyMetadata",
]
