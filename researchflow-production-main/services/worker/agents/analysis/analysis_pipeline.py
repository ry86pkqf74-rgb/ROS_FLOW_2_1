"""
Analysis Pipeline - Orchestrate Multi-Stage Analysis Workflow

Coordinates execution of multiple analysis agents in sequence:
1. Literature Search → 2. Statistical Analysis → 3. Meta-Analysis → 4. PRISMA Reporting

Provides:
- Sequential agent execution with dependency management
- State passing between stages
- Error handling and recovery
- Progress tracking
- Artifact aggregation

Linear Issues: ROS-XXX (Analysis Pipeline Orchestration)
"""

import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Configuration
# =============================================================================

class AnalysisStage(str, Enum):
    """Analysis pipeline stages."""
    LIT_SEARCH = "literature_search"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    META_ANALYSIS = "meta_analysis"
    PRISMA_REPORTING = "prisma_reporting"


@dataclass
class StageResult:
    """Result from a single pipeline stage."""
    stage: AnalysisStage
    success: bool
    output: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Complete pipeline execution result."""
    pipeline_id: str
    stages_completed: List[AnalysisStage] = field(default_factory=list)
    stage_results: Dict[AnalysisStage, StageResult] = field(default_factory=dict)
    final_artifacts: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: int = 0
    success: bool = False
    error: Optional[str] = None


# =============================================================================
# Analysis Pipeline
# =============================================================================

class AnalysisPipeline:
    """
    Orchestrates multi-stage analysis workflows.
    
    Example usage:
        pipeline = AnalysisPipeline()
        result = await pipeline.execute_full_workflow(
            study_context=study_context,
            data=research_data,
            config=pipeline_config
        )
    """

    def __init__(self):
        self.lit_search_agent = None
        self.statistical_agent = None
        self.meta_analysis_agent = None
        self.prisma_agent = None
        
        self._initialize_agents()

    def _initialize_agents(self):
        """Lazy initialize agents."""
        try:
            from .lit_search_agent import create_lit_search_agent
            from .statistical_analysis_agent import create_statistical_analysis_agent
            from .meta_analysis_agent import create_meta_analysis_agent
            from .prisma_agent import create_prisma_agent
            
            self.lit_search_agent = create_lit_search_agent()
            self.statistical_agent = create_statistical_analysis_agent()
            self.meta_analysis_agent = create_meta_analysis_agent()
            self.prisma_agent = create_prisma_agent()
            
            logger.info("[AnalysisPipeline] All agents initialized")
        except Exception as e:
            logger.error(f"[AnalysisPipeline] Agent initialization failed: {e}")
            raise

    async def execute_full_workflow(
        self,
        research_id: str,
        study_context: Dict[str, Any],
        statistical_data: Optional[Dict[str, Any]] = None,
        meta_analysis_studies: Optional[List[Dict[str, Any]]] = None,
        pipeline_config: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        Execute complete analysis workflow: LitSearch → Stats → Meta → PRISMA.
        
        Args:
            research_id: Unique research project ID
            study_context: Study context for literature search
            statistical_data: Optional data for statistical analysis
            meta_analysis_studies: Optional studies for meta-analysis
            pipeline_config: Optional configuration overrides
        
        Returns:
            PipelineResult with all stage outputs and artifacts
        """
        start_time = datetime.utcnow()
        pipeline_id = f"pipeline_{research_id}_{int(start_time.timestamp())}"
        
        logger.info(f"[AnalysisPipeline] Starting full workflow: {pipeline_id}")
        
        result = PipelineResult(pipeline_id=pipeline_id)
        config = pipeline_config or {}
        
        # Stage 1: Literature Search
        if config.get("run_lit_search", True):
            lit_result = await self._run_stage(
                AnalysisStage.LIT_SEARCH,
                self._execute_literature_search,
                study_context=study_context,
            )
            result.stage_results[AnalysisStage.LIT_SEARCH] = lit_result
            
            if lit_result.success:
                result.stages_completed.append(AnalysisStage.LIT_SEARCH)
                result.final_artifacts.extend(lit_result.artifacts)
            else:
                result.error = f"Literature search failed: {lit_result.error}"
                return self._finalize_result(result, start_time)
        
        # Stage 2: Statistical Analysis
        if config.get("run_statistical_analysis", True) and statistical_data:
            stats_result = await self._run_stage(
                AnalysisStage.STATISTICAL_ANALYSIS,
                self._execute_statistical_analysis,
                data=statistical_data,
            )
            result.stage_results[AnalysisStage.STATISTICAL_ANALYSIS] = stats_result
            
            if stats_result.success:
                result.stages_completed.append(AnalysisStage.STATISTICAL_ANALYSIS)
                result.final_artifacts.extend(stats_result.artifacts)
            elif config.get("strict_mode", False):
                result.error = f"Statistical analysis failed: {stats_result.error}"
                return self._finalize_result(result, start_time)
        
        # Stage 3: Meta-Analysis
        if config.get("run_meta_analysis", True) and meta_analysis_studies:
            meta_result = await self._run_stage(
                AnalysisStage.META_ANALYSIS,
                self._execute_meta_analysis,
                studies=meta_analysis_studies,
                config=config.get("meta_config", {}),
            )
            result.stage_results[AnalysisStage.META_ANALYSIS] = meta_result
            
            if meta_result.success:
                result.stages_completed.append(AnalysisStage.META_ANALYSIS)
                result.final_artifacts.extend(meta_result.artifacts)
            elif config.get("strict_mode", False):
                result.error = f"Meta-analysis failed: {meta_result.error}"
                return self._finalize_result(result, start_time)
        
        # Stage 4: PRISMA Reporting
        if config.get("run_prisma_report", True):
            prisma_result = await self._run_stage(
                AnalysisStage.PRISMA_REPORTING,
                self._execute_prisma_reporting,
                previous_results=result.stage_results,
                study_context=study_context,
            )
            result.stage_results[AnalysisStage.PRISMA_REPORTING] = prisma_result
            
            if prisma_result.success:
                result.stages_completed.append(AnalysisStage.PRISMA_REPORTING)
                result.final_artifacts.extend(prisma_result.artifacts)
        
        return self._finalize_result(result, start_time)

    async def _run_stage(
        self,
        stage: AnalysisStage,
        executor_func,
        **kwargs
    ) -> StageResult:
        """
        Execute a single pipeline stage with error handling.
        
        Args:
            stage: Stage identifier
            executor_func: Async function to execute
            **kwargs: Arguments for executor function
        
        Returns:
            StageResult with outputs or error
        """
        logger.info(f"[AnalysisPipeline] Running stage: {stage.value}")
        start_time = datetime.utcnow()
        
        try:
            output, artifacts = await executor_func(**kwargs)
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return StageResult(
                stage=stage,
                success=True,
                output=output,
                artifacts=artifacts,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"[AnalysisPipeline] Stage {stage.value} failed: {e}")
            
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=duration_ms,
                error=str(e),
            )

    # =========================================================================
    # Stage Executors
    # =========================================================================

    async def _execute_literature_search(
        self,
        study_context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Execute literature search stage."""
        from .lit_search_agent import StudyContext
        
        context = StudyContext(**study_context)
        result = await self.lit_search_agent.execute(context, max_results=50)
        
        output = {
            "total_papers": len(result.papers),
            "databases_searched": result.databases_searched,
            "search_queries": result.search_queries_used,
        }
        
        artifacts = [
            {
                "type": "literature_search_results",
                "content": result.model_dump(),
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "type": "citations",
                "content": [c.model_dump() for c in result.citations],
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        
        return output, artifacts

    async def _execute_statistical_analysis(
        self,
        data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Execute statistical analysis stage."""
        from .statistical_types import StudyData
        
        study_data = StudyData(**data)
        result = await self.statistical_agent.execute(study_data)
        
        output = {
            "test_performed": result.inferential.test_name if result.inferential else "None",
            "p_value": result.inferential.p_value if result.inferential else None,
            "effect_size": result.effect_sizes.cohens_d if result.effect_sizes else None,
        }
        
        artifacts = [
            {
                "type": "statistical_results",
                "content": result.to_dict() if hasattr(result, 'to_dict') else {},
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        
        if result.tables:
            artifacts.append({
                "type": "statistical_tables",
                "content": result.tables,
                "created_at": datetime.utcnow().isoformat(),
            })
        
        return output, artifacts

    async def _execute_meta_analysis(
        self,
        studies: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Execute meta-analysis stage."""
        from .meta_analysis_types import StudyEffect, MetaAnalysisConfig
        
        study_effects = [StudyEffect(**s) for s in studies]
        ma_config = MetaAnalysisConfig(**config) if config else MetaAnalysisConfig(
            effect_measure="OR",
        )
        
        result = await self.meta_analysis_agent.execute(study_effects, ma_config)
        
        output = {
            "pooled_effect": result.pooled_effect,
            "ci_95": [result.ci_lower, result.ci_upper],
            "p_value": result.p_value,
            "i_squared": result.heterogeneity.i_squared if result.heterogeneity else None,
        }
        
        artifacts = [
            {
                "type": "meta_analysis_results",
                "content": result.to_dict(),
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        
        if result.forest_plot_data:
            artifacts.append({
                "type": "forest_plot",
                "content": result.forest_plot_data,
                "created_at": datetime.utcnow().isoformat(),
            })
        
        if result.funnel_plot_data:
            artifacts.append({
                "type": "funnel_plot",
                "content": result.funnel_plot_data,
                "created_at": datetime.utcnow().isoformat(),
            })
        
        return output, artifacts

    async def _execute_prisma_reporting(
        self,
        previous_results: Dict[AnalysisStage, StageResult],
        study_context: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Execute PRISMA reporting stage."""
        from .prisma_types import PRISMAFlowchartData, SearchStrategy
        
        # Extract data from previous stages
        lit_result = previous_results.get(AnalysisStage.LIT_SEARCH)
        meta_result = previous_results.get(AnalysisStage.META_ANALYSIS)
        
        # Build flowchart data
        if lit_result and lit_result.output:
            total_found = lit_result.output.get("total_papers", 0)
            flowchart = PRISMAFlowchartData(
                records_identified_databases=total_found,
                records_screened=int(total_found * 0.7),  # Placeholder
                reports_sought_retrieval=int(total_found * 0.3),
                reports_assessed_eligibility=int(total_found * 0.2),
                new_studies_included=int(total_found * 0.1),
                total_studies_included=int(total_found * 0.1),
                records_excluded=int(total_found * 0.5),
                reports_excluded=int(total_found * 0.1),
            )
        else:
            flowchart = PRISMAFlowchartData(
                records_identified_databases=0,
                records_screened=0,
                reports_sought_retrieval=0,
                reports_assessed_eligibility=0,
                new_studies_included=0,
                total_studies_included=0,
                reports_excluded=0,
            )
        
        # Build search strategies
        search_strategies = []
        if lit_result and lit_result.output:
            for db in lit_result.output.get("databases_searched", []):
                search_strategies.append(SearchStrategy(
                    database=db,
                    search_date=datetime.utcnow().strftime("%Y-%m-%d"),
                    search_string="Placeholder search string",
                    results_count=100,
                ))
        
        # Generate PRISMA report
        report = await self.prisma_agent.execute(
            flowchart_data=flowchart,
            search_strategies=search_strategies,
            review_title=study_context.get("title", "Systematic Review"),
            authors=study_context.get("authors", ["Author 1"]),
        )
        
        output = {
            "checklist_completion": len([c for c in report.checklist if c.reported]) / len(report.checklist) * 100 if report.checklist else 0,
            "total_studies_included": flowchart.total_studies_included,
        }
        
        # Generate report formats
        markdown_report = self.prisma_agent.generate_report_markdown(report)
        html_report = self.prisma_agent.export_to_html(report)
        
        artifacts = [
            {
                "type": "prisma_report_data",
                "content": report.to_dict(),
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "type": "prisma_report_markdown",
                "content": markdown_report,
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "type": "prisma_report_html",
                "content": html_report,
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        
        return output, artifacts

    def _finalize_result(
        self,
        result: PipelineResult,
        start_time: datetime
    ) -> PipelineResult:
        """Finalize pipeline result with success status and duration."""
        result.total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        result.success = len(result.stages_completed) > 0 and not result.error
        
        logger.info(
            f"[AnalysisPipeline] Pipeline {result.pipeline_id} completed: "
            f"{len(result.stages_completed)} stages, {result.total_duration_ms}ms"
        )
        
        return result

    async def close(self):
        """Clean up resources."""
        agents = [
            self.lit_search_agent,
            self.statistical_agent,
            self.meta_analysis_agent,
            self.prisma_agent,
        ]
        
        for agent in agents:
            if agent and hasattr(agent, 'close'):
                try:
                    await agent.close()
                except Exception as e:
                    logger.warning(f"Agent cleanup failed: {e}")


# =============================================================================
# Factory Function
# =============================================================================

def create_analysis_pipeline() -> AnalysisPipeline:
    """Factory function for creating AnalysisPipeline."""
    return AnalysisPipeline()

