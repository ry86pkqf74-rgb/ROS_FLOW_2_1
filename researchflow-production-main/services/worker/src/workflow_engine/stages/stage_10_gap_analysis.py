"""
Stage 10: Gap Analysis (Enhanced Mode)

Comprehensive gap analysis using AI agents:
- Literature comparison with semantic similarity
- Multi-dimensional gap identification (6 types)
- PICO framework generation
- Impact vs Feasibility prioritization matrix
- Manuscript-ready narrative generation

This is an enhanced alternative to stage_10_validation.py
Enable via config: stage_10_mode = "gap_analysis"
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add agents to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agents"))

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stages.stage_10_gap_analysis")

# Import gap analysis agent with graceful fallback
try:
    from agents.analysis import (
        GapAnalysisAgent,
        create_gap_analysis_agent,
        StudyContext,
        Paper,
        Finding,
        GapAnalysisResult,
    )
    GAP_ANALYSIS_AVAILABLE = True
except ImportError as e:
    GAP_ANALYSIS_AVAILABLE = False
    logger.warning(f"GapAnalysisAgent not available: {e}")
    GapAnalysisAgent = None
    create_gap_analysis_agent = None
    StudyContext = None
    Paper = None
    Finding = None
    GapAnalysisResult = None


@register_stage
class GapAnalysisStageAgent(BaseStageAgent):
    """
    Stage 10: Gap Analysis (Enhanced Mode)
    
    Integrates GapAnalysisAgent into the workflow engine for
    comprehensive gap analysis and future research directions.
    
    Features:
    - Multi-model AI integration (Claude, Grok, Mercury, OpenAI)
    - Semantic literature comparison
    - 6-dimensional gap identification
    - PICO framework generation
    - Prioritization matrix (Impact vs Feasibility)
    - Manuscript-ready narratives
    
    Input Requirements:
    - Stage 6 output: literature papers
    - Stage 7 output: statistical findings
    - Study metadata in config
    
    Output:
    - Comprehensive gap analysis report
    - Prioritized research suggestions
    - Future Directions section for manuscript
    """

    stage_id = 10
    stage_name = "Gap Analysis"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the GapAnalysisStageAgent.

        Args:
            config: Optional configuration dict. If None, uses defaults.
        """
        bridge_config = None
        if config and "bridge_url" in config:
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0),
            )
        super().__init__(bridge_config=bridge_config)
        
        # Initialize gap analysis agent if available
        self.gap_agent: Optional[GapAnalysisAgent] = None
        if GAP_ANALYSIS_AVAILABLE:
            try:
                self.gap_agent = create_gap_analysis_agent()
                logger.info("GapAnalysisAgent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GapAnalysisAgent: {e}")
                self.gap_agent = None

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        # Gap analysis uses its own agent workflow, no external tools needed
        return []

    def get_prompt_template(self):
        """Get prompt template for gap analysis."""
        # Gap analysis uses internal prompts via GapAnalysisAgent
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        
        return PromptTemplate.from_template(
            "Gap Analysis Stage - this is handled by GapAnalysisAgent internally"
        )

    async def execute(self, context: StageContext) -> StageResult:
        """
        Execute gap analysis stage.

        Args:
            context: StageContext with job configuration and prior results

        Returns:
            StageResult with gap analysis output
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        warnings: List[str] = []
        errors: List[str] = []
        artifacts: List[str] = []

        logger.info(f"Starting gap analysis stage for job {context.job_id}")

        # Check if gap analysis is available
        if not GAP_ANALYSIS_AVAILABLE or self.gap_agent is None:
            errors.append(
                "GapAnalysisAgent not available. Install with: "
                "pip install langchain langchain-anthropic langchain-openai"
            )
            return self.create_stage_result(
                context=context,
                status="failed",
                started_at=started_at,
                output={"error": "GapAnalysisAgent not available"},
                errors=errors,
                warnings=warnings,
            )

        # Get gap analysis configuration
        gap_config = context.config.get("gap_analysis", {})
        min_literature = gap_config.get("min_literature_count", 10)
        max_literature = gap_config.get("max_literature_papers", 50)
        enable_semantic = gap_config.get("enable_semantic_comparison", True)
        target_suggestions = gap_config.get("target_suggestions", 5)

        # Initialize output structure
        output: Dict[str, Any] = {
            "comparisons": {},
            "gaps": {},
            "prioritized_gaps": [],
            "prioritization_matrix": {},
            "research_suggestions": [],
            "narrative": "",
            "future_directions_section": "",
            "summary": {},
        }

        try:
            # Extract study context from config
            study_context = self._extract_study_context(context)
            if not study_context:
                errors.append("Study context not found in config. Provide study metadata.")
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at,
                    output=output,
                    errors=errors,
                    warnings=warnings,
                )

            # Extract literature from Stage 6 results
            literature = self._extract_literature(context)
            if len(literature) < min_literature:
                warnings.append(
                    f"Only {len(literature)} papers found. Gap analysis works best with "
                    f"{min_literature}+ papers."
                )
            
            if not literature:
                errors.append(
                    "No literature found. Gap analysis requires Stage 6 (literature search) results."
                )
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at,
                    output=output,
                    errors=errors,
                    warnings=warnings,
                )

            # Limit literature for performance
            if len(literature) > max_literature:
                warnings.append(
                    f"Limiting literature from {len(literature)} to {max_literature} papers"
                )
                literature = literature[:max_literature]

            # Extract findings from Stage 7 results
            findings = self._extract_findings(context)
            if not findings:
                warnings.append(
                    "No findings found from Stage 7. Gap analysis will focus on literature gaps only."
                )

            # Check API keys
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if not anthropic_key:
                errors.append(
                    "ANTHROPIC_API_KEY not set. Required for gap analysis planning."
                )
            
            if not openai_key and enable_semantic:
                warnings.append(
                    "OPENAI_API_KEY not set. Semantic comparison will use keyword fallback."
                )

            if errors:
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at,
                    output=output,
                    errors=errors,
                    warnings=warnings,
                )

            # Execute gap analysis
            logger.info(
                f"Executing gap analysis: {len(literature)} papers, "
                f"{len(findings)} findings"
            )
            
            result: GapAnalysisResult = await self.gap_agent.execute(
                study=study_context,
                literature=literature,
                findings=findings if findings else None
            )

            # Convert result to output format
            output = self._format_gap_analysis_result(result)

            # Generate artifacts
            artifact_path = await self._generate_artifacts(context, result)
            if artifact_path:
                artifacts.append(artifact_path)

            # Add metadata
            output["metadata"] = {
                "literature_count": len(literature),
                "findings_count": len(findings),
                "semantic_comparison_enabled": enable_semantic,
                "anthropic_key_present": bool(anthropic_key),
                "openai_key_present": bool(openai_key),
            }

            # Add demo mode indicator
            if context.governance_mode == "DEMO":
                output["demo_mode"] = True
                warnings.append(
                    "Running in DEMO mode - gap analysis uses real AI but may have limitations"
                )

            logger.info(
                f"Gap analysis complete: {output['summary'].get('total_gaps_identified', 0)} gaps, "
                f"{output['summary'].get('high_priority_count', 0)} high priority"
            )

        except Exception as e:
            logger.error(f"Error during gap analysis: {str(e)}", exc_info=True)
            errors.append(f"Gap analysis failed: {str(e)}")

        status = "failed" if errors else "completed"

        return self.create_stage_result(
            context=context,
            status=status,
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            warnings=warnings,
            errors=errors,
            metadata={
                "governance_mode": context.governance_mode,
                "literature_count": len(literature) if 'literature' in locals() else 0,
                "gap_analysis_agent_version": "1.0.0",
            },
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_study_context(self, context: StageContext) -> Optional[StudyContext]:
        """Extract study context from config."""
        try:
            study_data = context.config.get("study_context", {})
            
            # Also check top-level config keys
            if not study_data:
                study_data = {
                    "title": context.config.get("study_title", ""),
                    "research_question": context.config.get("research_question", ""),
                    "study_type": context.config.get("study_type", ""),
                    "population": context.config.get("population", ""),
                    "intervention": context.config.get("intervention", ""),
                    "outcome": context.config.get("outcome", ""),
                }
            
            # Validate required fields
            if not study_data.get("title") or not study_data.get("research_question"):
                logger.warning("Study context missing required fields")
                return None
            
            return StudyContext(**study_data)
        
        except Exception as e:
            logger.error(f"Failed to extract study context: {e}")
            return None

    def _extract_literature(self, context: StageContext) -> List[Paper]:
        """Extract literature papers from Stage 6 results."""
        literature = []
        
        try:
            # Check Stage 6 results
            if context.previous_results and 6 in context.previous_results:
                stage6_result = context.previous_results[6]
                papers_data = stage6_result.output.get("papers", [])
                
                for paper_data in papers_data:
                    try:
                        # Convert to Paper object
                        paper = Paper(
                            title=paper_data.get("title", ""),
                            authors=paper_data.get("authors", []),
                            year=paper_data.get("year"),
                            abstract=paper_data.get("abstract", ""),
                            doi=paper_data.get("doi"),
                            pmid=paper_data.get("pmid"),
                            url=paper_data.get("url"),
                            source=paper_data.get("source", "unknown"),
                            relevance_score=paper_data.get("relevance_score", 0.0),
                        )
                        literature.append(paper)
                    except Exception as e:
                        logger.warning(f"Failed to parse paper: {e}")
                        continue
            
            logger.info(f"Extracted {len(literature)} papers from Stage 6")
        
        except Exception as e:
            logger.error(f"Failed to extract literature: {e}")
        
        return literature

    def _extract_findings(self, context: StageContext) -> List[Finding]:
        """Extract findings from Stage 7 results."""
        findings = []
        
        try:
            # Check Stage 7 results
            if context.previous_results and 7 in context.previous_results:
                stage7_result = context.previous_results[7]
                findings_data = stage7_result.output.get("findings", [])
                
                for finding_data in findings_data:
                    try:
                        # Convert to Finding object
                        finding = Finding(
                            description=finding_data.get("description", ""),
                            effect_size=finding_data.get("effect_size"),
                            p_value=finding_data.get("p_value"),
                            confidence_interval=finding_data.get("confidence_interval"),
                            statistical_test=finding_data.get("statistical_test", ""),
                            significance=finding_data.get("significance", ""),
                            confidence=finding_data.get("confidence", "moderate"),
                        )
                        findings.append(finding)
                    except Exception as e:
                        logger.warning(f"Failed to parse finding: {e}")
                        continue
            
            logger.info(f"Extracted {len(findings)} findings from Stage 7")
        
        except Exception as e:
            logger.error(f"Failed to extract findings: {e}")
        
        return findings

    def _format_gap_analysis_result(self, result: GapAnalysisResult) -> Dict[str, Any]:
        """Format GapAnalysisResult for StageResult output."""
        try:
            # Convert Pydantic models to dict
            return {
                "comparisons": result.comparisons.model_dump() if result.comparisons else {},
                "gaps": {
                    "knowledge": [g.model_dump() for g in result.knowledge_gaps],
                    "methodological": [g.model_dump() for g in result.method_gaps],
                    "population": [g.model_dump() for g in result.population_gaps],
                    "temporal": [g.model_dump() for g in result.temporal_gaps],
                    "geographic": [g.model_dump() for g in result.geographic_gaps],
                },
                "prioritized_gaps": [
                    pg.model_dump() for pg in result.prioritized_gaps
                ],
                "prioritization_matrix": (
                    result.prioritization_matrix.model_dump()
                    if result.prioritization_matrix
                    else {}
                ),
                "research_suggestions": [
                    rs.model_dump() for rs in result.research_suggestions
                ],
                "narrative": result.narrative,
                "future_directions_section": result.future_directions_section,
                "summary": {
                    "total_gaps_identified": result.total_gaps_identified,
                    "high_priority_count": result.high_priority_count,
                    "gap_diversity_score": result.gap_diversity_score,
                    "literature_coverage": result.literature_coverage,
                },
            }
        except Exception as e:
            logger.error(f"Failed to format gap analysis result: {e}")
            return {}

    async def _generate_artifacts(
        self,
        context: StageContext,
        result: GapAnalysisResult
    ) -> Optional[str]:
        """Generate gap analysis artifact file."""
        try:
            os.makedirs(context.artifact_path, exist_ok=True)
            artifact_path = os.path.join(context.artifact_path, "gap_analysis_report.json")
            
            artifact_data = {
                "schema_version": "1.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "job_id": context.job_id,
                "gap_analysis": self._format_gap_analysis_result(result),
            }
            
            with open(artifact_path, "w") as f:
                json.dump(artifact_data, f, indent=2, default=str)
            
            logger.info(f"Gap analysis artifact written to {artifact_path}")
            return artifact_path
        
        except Exception as e:
            logger.warning(f"Could not write gap analysis artifact: {e}")
            return None
