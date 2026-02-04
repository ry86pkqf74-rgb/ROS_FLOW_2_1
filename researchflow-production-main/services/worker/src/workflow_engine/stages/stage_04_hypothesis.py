"""
Stage 04: Hypothesis Refinement

HypothesisRefinerAgent refines research questions and hypotheses based on:
- Literature findings from Stage 2 (LiteratureScoutAgent)
- Dataset columns from Stage 1/4 (Schema Validation)
- Initial hypothesis from config

Implements ROS-146: HypothesisRefinerAgent - Stage 4 Implementation

NOTE: Stage 4 is currently registered as SchemaValidationStage. This implementation
assumes Hypothesis Refinement will replace Schema Validation at Stage 4, or Schema
Validation will be moved to a different stage number. The conflict must be resolved
before both stages can be registered simultaneously.
"""

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stage_04_hypothesis")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")


@register_stage
class HypothesisRefinerAgent(BaseStageAgent):
    """Stage 4: Hypothesis Refiner.

    Refines research questions based on literature gaps, dataset columns,
    and testability. Uses LangChain tools for gap analysis and variable extraction.

    Inputs: StageContext (config, previous_results from Stage 01/02).
    Outputs: StageResult with refined hypothesis, key variables, alternatives.
    See also: StageContext, StageResult.
    """

    stage_id = 4
    stage_name = "Hypothesis Refinement"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the HypothesisRefinerAgent.
        
        Args:
            config: Optional configuration dict. If None, uses defaults.
        """
        # Extract bridge config if provided
        bridge_config = None
        if config and "bridge_url" in config:
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0)
            )
        
        super().__init__(bridge_config=bridge_config)

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        if not LANGCHAIN_AVAILABLE:
            return []
        
        return [
            Tool(
                name="analyze_literature_gaps",
                description="Analyze literature papers to identify research gaps and what's missing in existing research",
                func=self._analyze_literature_gaps_tool
            ),
            Tool(
                name="generate_hypothesis_variants",
                description="Generate alternative hypothesis phrasings and variants based on literature gaps",
                func=self._generate_hypothesis_variants_tool
            ),
            Tool(
                name="validate_hypothesis_testability",
                description="Validate if a hypothesis is testable with available dataset columns",
                func=self._validate_hypothesis_testability_tool
            ),
            Tool(
                name="extract_key_variables",
                description="Extract and categorize key variables (independent, dependent, confounding) from hypothesis",
                func=self._extract_key_variables_tool
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for hypothesis refinement."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        from langchain_core.prompts import PromptTemplate
        
        return PromptTemplate.from_template("""You are a Hypothesis Refinement Specialist for clinical research.

Your task is to refine research hypotheses based on:
1. Literature findings from Stage 2 (existing research, gaps, key papers)
2. Dataset columns available from Stage 1/4 (what variables are available)
3. Initial hypothesis from the research configuration

Literature Context:
- Key Papers: {key_papers}
- Literature Summary: {literature_summary}
- Research Gaps: {literature_gaps}

Dataset Context:
- Available Columns: {dataset_columns}
- Column Count: {column_count}

Initial Hypothesis: {original_hypothesis}

Your goal is to:
1. Identify what's missing in existing research (gaps)
2. Strengthen the hypothesis based on evidence
3. Ensure the hypothesis is testable with available data
4. Generate alternative hypothesis phrasings
5. Extract key variables (independent, dependent, confounding)

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    async def execute(self, context: StageContext) -> StageResult:
        """Execute hypothesis refinement workflow.

        Args:
            context: Stage execution context (config, previous_results).

        Returns:
            StageResult with refined hypothesis, key variables, and alternatives.
        """
        started_at = datetime.utcnow()
        output: Dict[str, Any] = {}
        artifacts: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # 1. Extract initial hypothesis from config
            original_hypothesis = self._extract_initial_hypothesis(context)
            output["original_hypothesis"] = original_hypothesis

            # 2. Get literature findings from Stage 2
            literature_findings = self._get_literature_findings(context)
            if not literature_findings and context.governance_mode != "DEMO":
                errors.append("Stage 2 (Literature Discovery) output not found. Hypothesis refinement requires literature context.")
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at.isoformat() + "Z",
                    errors=errors,
                )
            elif not literature_findings:
                warnings.append("Stage 2 output not found. Proceeding with limited literature context.")

            # 3. Get dataset columns from Stage 1/4
            dataset_columns = self._get_dataset_columns(context)
            if not dataset_columns:
                warnings.append("No dataset columns found. Hypothesis refinement will proceed without data validation.")

            # 4. Identify literature gaps
            literature_gaps = self._identify_gaps(
                literature_findings.get("ranked_papers", []),
                literature_findings.get("key_papers", []),
                literature_findings.get("literature_summary", {}).get("search_keywords", [])
            )
            output["literature_gaps"] = literature_gaps

            # 5. Generate refined hypotheses
            refined_hypothesis, secondary_hypotheses = self._generate_hypothesis_variants(
                original_hypothesis,
                literature_gaps,
                literature_findings,
                dataset_columns
            )
            output["refined_hypothesis"] = refined_hypothesis
            output["secondary_hypotheses"] = secondary_hypotheses

            # 6. Extract key variables
            key_variables = self._extract_variables(refined_hypothesis, dataset_columns)
            output["key_variables"] = key_variables

            # 7. Validate testability
            testability_score = self._validate_testability(
                refined_hypothesis,
                key_variables,
                dataset_columns
            )
            output["testability_score"] = testability_score

            # 8. Generate refinement rationale using claude-writer service
            refinement_rationale = await self._generate_refinement_rationale(
                original_hypothesis,
                refined_hypothesis,
                literature_gaps,
                key_variables
            )
            output["refinement_rationale"] = refinement_rationale

            # 9. Additional metadata
            output["dataset_columns_used"] = dataset_columns[:20] if dataset_columns else []
            output["literature_papers_reviewed"] = len(literature_findings.get("ranked_papers", []))

            # 10. Save artifacts
            artifact_path = self._save_refined_hypothesis(context, output)
            artifacts.append(artifact_path)

            # Add warnings for low testability
            if testability_score < 0.5:
                warnings.append(f"Low testability score ({testability_score:.2f}). Hypothesis may not be fully testable with available data.")
            if len(literature_gaps) == 0 and literature_findings:
                warnings.append("No clear research gaps identified. Consider broadening literature search.")

        except Exception as e:
            logger.error(f"Hypothesis refinement failed: {e}", exc_info=True)
            errors.append(f"Hypothesis refinement failed: {str(e)}")

        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at.isoformat() + "Z",
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "testability_score": output.get("testability_score", 0.0),
                "literature_gaps_count": len(output.get("literature_gaps", [])),
                "secondary_hypotheses_count": len(output.get("secondary_hypotheses", [])),
            },
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_initial_hypothesis(self, context: StageContext) -> str:
        """Extract initial hypothesis from config with fallbacks."""
        config = context.config or {}
        
        # Try multiple config paths
        hypothesis = (
            config.get("hypothesis") or
            config.get("research_question") or
            config.get("researchQuestion") or
            config.get("initial_hypothesis") or
            config.get("initialHypothesis") or
            None
        )

        # DEMO mode: generate default if missing
        if not hypothesis and context.governance_mode == "DEMO":
            study_title = config.get("studyTitle") or config.get("study_title") or "Research Study"
            dataset_columns = self._get_dataset_columns(context)
            literature_findings = self._get_literature_findings(context)
            keywords = []
            if literature_findings:
                keywords = literature_findings.get("literature_summary", {}).get("search_keywords", [])
            
            hypothesis = self._generate_default_hypothesis(study_title, dataset_columns, keywords)
            logger.info(f"Generated default hypothesis in DEMO mode: {hypothesis[:100]}...")

        return hypothesis or "To investigate the relationship between study variables and outcomes"

    def _get_literature_findings(self, context: StageContext) -> Dict[str, Any]:
        """Get literature findings from Stage 2 output."""
        stage2_output = context.get_prior_stage_output(2)
        if not stage2_output:
            return {}
        
        return {
            "ranked_papers": stage2_output.get("ranked_papers", []),
            "key_papers": stage2_output.get("key_papers", []),
            "literature_summary": stage2_output.get("literature_summary", {}),
            "total_unique_papers": stage2_output.get("total_unique_papers", 0),
        }

    def _get_dataset_columns(self, context: StageContext) -> List[str]:
        """Get dataset columns from Stage 1/4 or config."""
        columns = []
        
        # Try Stage 4 (Schema Validation) first
        stage4_output = context.get_prior_stage_output(4)
        if stage4_output:
            schema_metadata = stage4_output.get("schema_metadata", {})
            columns = schema_metadata.get("columns", [])
            if columns:
                logger.info(f"Found {len(columns)} columns from Stage 4")
                return columns[:50]  # Limit to prevent bloat
        
        # Try Stage 1 (Upload) output
        stage1_output = context.get_prior_stage_output(1)
        if stage1_output and not columns:
            # Stage 1 doesn't typically have columns, but check anyway
            pass
        
        # Try config directly
        config = context.config or {}
        if not columns:
            columns = config.get("columns", [])
            if isinstance(columns, str):
                columns = [c.strip() for c in columns.split(",")]
        
        # Try from dataset metadata in config
        if not columns:
            dataset_metadata = config.get("dataset_metadata", {})
            columns = dataset_metadata.get("columns", [])
        
        return columns[:50] if columns else []

    def _identify_gaps(
        self,
        papers: List[Dict[str, Any]],
        key_papers: List[Dict[str, Any]],
        keywords: List[str]
    ) -> List[str]:
        """Identify research gaps from literature."""
        gaps = []
        
        if not papers and not key_papers:
            return ["Insufficient literature to identify gaps"]
        
        # Analyze key papers for common themes
        themes = set()
        for paper in key_papers[:10]:  # Top 10 key papers
            title = (paper.get("title") or "").lower()
            abstract = (paper.get("abstract") or "").lower()
            # Extract common terms
            for keyword in keywords[:5]:
                if keyword.lower() in title or keyword.lower() in abstract:
                    themes.add(keyword)
        
        # Identify gaps based on missing combinations
        if len(papers) < 10:
            gaps.append("Limited number of relevant papers found. Broader search may reveal additional research.")
        
        # Check for systematic reviews
        has_systematic_review = any(
            "systematic review" in (p.get("publicationType") or "").lower() or
            "meta-analysis" in (p.get("publicationType") or "").lower()
            for p in key_papers
        )
        if not has_systematic_review:
            gaps.append("No systematic reviews or meta-analyses found. Current evidence may lack comprehensive synthesis.")
        
        # Check for recent papers
        current_year = datetime.now().year
        recent_papers = [p for p in papers if p.get("year") and int(p.get("year", 0)) >= current_year - 2]
        if len(recent_papers) < 3:
            gaps.append("Limited recent research (last 2 years). Field may be evolving or understudied.")
        
        # Check for diverse study types
        study_types = set()
        for paper in papers[:20]:
            pub_type = paper.get("publicationType", "")
            if pub_type:
                study_types.add(pub_type.lower())
        if len(study_types) < 2:
            gaps.append("Limited diversity in study types. Consider different research designs.")
        
        if not gaps:
            gaps.append("Literature appears comprehensive. Focus on specific population or outcome variations.")
        
        return gaps[:5]  # Limit to top 5 gaps

    def _generate_hypothesis_variants(
        self,
        original: str,
        gaps: List[str],
        literature_findings: Dict[str, Any],
        columns: List[str]
    ) -> tuple[str, List[str]]:
        """Generate refined hypothesis and secondary hypotheses."""
        # Use gaps to refine
        refined = original
        
        # If gaps suggest specific directions, incorporate them
        if gaps:
            # Simple refinement: add gap context
            gap_context = gaps[0] if gaps else ""
            if "limited" in gap_context.lower() or "missing" in gap_context.lower():
                refined = f"{original} This study addresses the gap in {gap_context.lower()}."
        
        # Generate secondary hypotheses (2-3 alternatives)
        secondary = []
        
        # Variant 1: More specific population
        if columns:
            # Try to infer population from columns
            population_indicators = [c for c in columns if any(term in c.lower() for term in ["age", "gender", "sex", "race", "ethnicity"])]
            if population_indicators:
                secondary.append(f"{original} Specifically focusing on {population_indicators[0]} as a key factor.")
        
        # Variant 2: Different outcome focus
        outcome_indicators = [c for c in columns if any(term in c.lower() for term in ["outcome", "result", "event", "score", "measure"])]
        if outcome_indicators and len(outcome_indicators) > 0:
            secondary.append(f"{original} With emphasis on {outcome_indicators[0]} as primary outcome.")
        
        # Variant 3: Temporal or longitudinal aspect
        time_indicators = [c for c in columns if any(term in c.lower() for term in ["time", "date", "follow", "baseline", "visit"])]
        if time_indicators:
            secondary.append(f"{original} Examining changes over time using {time_indicators[0]}.")
        
        # Ensure we have at least 2 secondary hypotheses
        if len(secondary) < 2:
            secondary.append(f"{original} Exploring alternative mechanisms and pathways.")
            if len(secondary) < 2:
                secondary.append(f"{original} With focus on clinical significance and practical implications.")
        
        return refined, secondary[:3]  # Limit to 3 secondary hypotheses

    def _extract_variables(
        self,
        hypothesis: str,
        columns: List[str]
    ) -> Dict[str, List[str]]:
        """Extract and categorize key variables from hypothesis."""
        variables = {
            "independent": [],
            "dependent": [],
            "confounding": []
        }
        
        hypothesis_lower = hypothesis.lower()
        
        # Common patterns for independent variables
        ind_patterns = ["associated with", "predicts", "influences", "affects", "leads to", "causes"]
        # Common patterns for dependent variables
        dep_patterns = ["outcome", "result", "effect", "impact", "change in"]
        
        # Try to match columns to hypothesis
        for col in columns[:30]:  # Check first 30 columns
            col_lower = col.lower()
            
            # Check if column appears in hypothesis
            if col_lower in hypothesis_lower:
                # Try to infer type from context
                if any(pattern in hypothesis_lower for pattern in ind_patterns):
                    # Check if column appears before "associated with" etc.
                    for pattern in ind_patterns:
                        if pattern in hypothesis_lower:
                            idx = hypothesis_lower.find(pattern)
                            if col_lower in hypothesis_lower[:idx]:
                                variables["independent"].append(col)
                                break
                
                if any(pattern in hypothesis_lower for pattern in dep_patterns):
                    variables["dependent"].append(col)
            
            # Infer from column name patterns
            if any(term in col_lower for term in ["treatment", "intervention", "exposure", "predictor", "risk_factor"]):
                if col not in variables["independent"]:
                    variables["independent"].append(col)
            
            if any(term in col_lower for term in ["outcome", "result", "event", "response", "endpoint"]):
                if col not in variables["dependent"]:
                    variables["dependent"].append(col)
            
            if any(term in col_lower for term in ["age", "gender", "sex", "race", "ethnicity", "bmi", "comorbidity"]):
                if col not in variables["confounding"]:
                    variables["confounding"].append(col)
        
        # Limit to prevent bloat
        variables["independent"] = variables["independent"][:10]
        variables["dependent"] = variables["dependent"][:10]
        variables["confounding"] = variables["confounding"][:10]
        
        return variables

    def _validate_testability(
        self,
        hypothesis: str,
        variables: Dict[str, List[str]],
        columns: List[str]
    ) -> float:
        """Validate if hypothesis is testable with available data. Returns score 0-1."""
        if not columns:
            return 0.3  # Low score if no columns available
        
        score = 0.0
        
        # Check if we have independent variables
        if variables["independent"]:
            score += 0.3
            # Check if they exist in columns
            ind_in_columns = sum(1 for v in variables["independent"] if v in columns)
            if ind_in_columns > 0:
                score += 0.2
        
        # Check if we have dependent variables
        if variables["dependent"]:
            score += 0.3
            # Check if they exist in columns
            dep_in_columns = sum(1 for v in variables["dependent"] if v in columns)
            if dep_in_columns > 0:
                score += 0.2
        
        # Bonus for having confounding variables (suggests sophisticated analysis)
        if variables["confounding"]:
            score += 0.1
        
        # Check if hypothesis mentions specific columns
        hypothesis_lower = hypothesis.lower()
        mentioned_columns = sum(1 for col in columns[:20] if col.lower() in hypothesis_lower)
        if mentioned_columns > 0:
            score += min(0.1 * mentioned_columns, 0.2)
        
        return min(score, 1.0)  # Cap at 1.0

    async def _generate_refinement_rationale(
        self,
        original: str,
        refined: str,
        gaps: List[str],
        variables: Dict[str, List[str]]
    ) -> str:
        """Generate refinement rationale using claude-writer service."""
        try:
            context = f"""
Original Hypothesis: {original}

Refined Hypothesis: {refined}

Research Gaps Identified: {', '.join(gaps[:3])}

Key Variables:
- Independent: {', '.join(variables.get('independent', [])[:5])}
- Dependent: {', '.join(variables.get('dependent', [])[:5])}
- Confounding: {', '.join(variables.get('confounding', [])[:5])}
"""
            
            result = await self.call_manuscript_service(
                "claude-writer",
                "generateParagraph",
                {
                    "prompt": "Explain why the hypothesis was refined based on literature gaps and data availability.",
                    "context": context,
                    "section": "hypothesis",
                    "keyPoints": gaps[:3],
                    "tone": "formal"
                }
            )
            
            rationale = result.get("paragraph", "") or result.get("content", "")
            if rationale:
                return rationale
            
        except Exception as e:
            logger.warning(f"Failed to generate rationale via claude-writer: {e}")
        
        # Fallback to local generation
        rationale_parts = [
            f"The original hypothesis '{original[:100]}...' was refined based on:",
            f"- {len(gaps)} research gaps identified in the literature",
            f"- Availability of {len(variables.get('independent', []))} independent variables",
            f"- Availability of {len(variables.get('dependent', []))} dependent variables",
        ]
        if gaps:
            rationale_parts.append(f"- Primary gap: {gaps[0]}")
        
        return " ".join(rationale_parts)

    def _generate_default_hypothesis(
        self,
        study_title: str,
        columns: List[str],
        keywords: List[str]
    ) -> str:
        """Generate default hypothesis in DEMO mode."""
        # Extract key terms from title
        title_words = [w.lower() for w in study_title.split() if len(w) > 3]
        
        # Try to infer variables from columns
        ind_var = None
        dep_var = None
        
        for col in columns[:20]:
            col_lower = col.lower()
            if not ind_var and any(term in col_lower for term in ["treatment", "intervention", "exposure", "predictor"]):
                ind_var = col
            if not dep_var and any(term in col_lower for term in ["outcome", "result", "event", "response"]):
                dep_var = col
        
        # Use keywords if no columns
        if not ind_var and keywords:
            ind_var = keywords[0] if keywords else "study variable"
        if not dep_var:
            dep_var = "outcome" if not columns else (columns[0] if columns else "outcome")
        
        # Construct hypothesis
        hypothesis = f"We hypothesize that {ind_var} is associated with {dep_var}"
        if keywords:
            hypothesis += f" in the context of {keywords[0]}"
        
        return hypothesis

    def _save_refined_hypothesis(self, context: StageContext, output: Dict[str, Any]) -> str:
        """Save refined hypothesis to JSON artifact."""
        artifact_path = os.path.join(context.artifact_path, "refined_hypothesis.json")
        os.makedirs(context.artifact_path, exist_ok=True)

        artifact_data = {
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "original_hypothesis": output.get("original_hypothesis"),
            "refined_hypothesis": output.get("refined_hypothesis"),
            "secondary_hypotheses": output.get("secondary_hypotheses", []),
            "literature_gaps": output.get("literature_gaps", []),
            "key_variables": output.get("key_variables", {}),
            "testability_score": output.get("testability_score", 0.0),
            "refinement_rationale": output.get("refinement_rationale", ""),
            "metadata": {
                "dataset_columns_used": output.get("dataset_columns_used", []),
                "literature_papers_reviewed": output.get("literature_papers_reviewed", 0),
            }
        }

        with open(artifact_path, "w") as f:
            json.dump(artifact_data, f, indent=2, default=str)

        return artifact_path

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    def _analyze_literature_gaps_tool(self, papers_json: str) -> str:
        """Tool wrapper for analyzing literature gaps."""
        try:
            papers = json.loads(papers_json) if isinstance(papers_json, str) else papers_json
            gaps = self._identify_gaps(papers, [], [])
            return json.dumps({"gaps": gaps}, indent=2)
        except Exception as e:
            return f"Failed to analyze gaps: {str(e)}"

    def _generate_hypothesis_variants_tool(self, original: str) -> str:
        """Tool wrapper for generating hypothesis variants."""
        try:
            refined, secondary = self._generate_hypothesis_variants(original, [], {}, [])
            return json.dumps({
                "refined": refined,
                "secondary": secondary
            }, indent=2)
        except Exception as e:
            return f"Failed to generate variants: {str(e)}"

    def _validate_hypothesis_testability_tool(self, hypothesis: str, columns_json: str) -> str:
        """Tool wrapper for validating testability."""
        try:
            columns = json.loads(columns_json) if isinstance(columns_json, str) else columns_json
            variables = self._extract_variables(hypothesis, columns)
            score = self._validate_testability(hypothesis, variables, columns)
            return json.dumps({
                "testability_score": score,
                "variables": variables
            }, indent=2)
        except Exception as e:
            return f"Failed to validate testability: {str(e)}"

    def _extract_key_variables_tool(self, hypothesis: str, columns_json: str) -> str:
        """Tool wrapper for extracting key variables."""
        try:
            columns = json.loads(columns_json) if isinstance(columns_json, str) else columns_json
            variables = self._extract_variables(hypothesis, columns)
            return json.dumps(variables, indent=2)
        except Exception as e:
            return f"Failed to extract variables: {str(e)}"
