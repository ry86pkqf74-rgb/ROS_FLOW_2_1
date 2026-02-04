"""
MetaAnalysisAgent - Stage 10-11: Meta-Analysis & Synthesis

Performs comprehensive meta-analysis including:
- Effect size pooling (fixed & random effects)
- Heterogeneity assessment (I², τ², Q-test)
- Publication bias detection (Egger, trim-and-fill)
- Subgroup & sensitivity analyses
- Forest plot & funnel plot generation

Linear Issues: ROS-XXX (Stage 10-11 - Meta-Analysis Agent)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import numpy as np
from scipy import stats

# Import base agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

# Import meta-analysis types
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

logger = logging.getLogger(__name__)


# =============================================================================
# MetaAnalysisAgent
# =============================================================================

class MetaAnalysisAgent(BaseAgent):
    """
    Agent for comprehensive meta-analysis of study effects.
    
    Capabilities:
    - Effect size pooling using fixed-effect and random-effects models
    - Heterogeneity assessment (I², τ², Cochran's Q)
    - Publication bias detection (Egger's test, funnel plots, trim-and-fill)
    - Subgroup analysis by moderator variables
    - Leave-one-out sensitivity analysis
    - Forest plot and funnel plot specifications
    - GRADE quality of evidence assessment
    
    Uses LangGraph architecture:
    1. PLAN: Determine appropriate model and analyses based on data
    2. RETRIEVE: Get meta-analysis guidelines from RAG
    3. EXECUTE: Run statistical calculations
    4. REFLECT: Quality check for heterogeneity, publication bias, robustness
    """

    def __init__(self):
        config = AgentConfig(
            name="MetaAnalysisAgent",
            description="Perform meta-analysis with heterogeneity and bias assessment",
            stages=[10, 11],
            rag_collections=["cochrane_handbook", "meta_analysis_methods"],
            max_iterations=3,
            quality_threshold=0.80,
            timeout_seconds=300,
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)


    # =========================================================================
    # BaseAgent Abstract Methods Implementation
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """System prompt for meta-analysis expertise."""
        return """You are a Meta-Analysis Agent specialized in evidence synthesis for medical research.

Your expertise includes:
- Fixed-effect and random-effects meta-analysis models
- Heterogeneity assessment (I², τ², Q-test)
- Publication bias detection and correction
- Subgroup and sensitivity analyses
- GRADE quality of evidence framework
- Cochrane systematic review standards

Key principles:
1. Always assess heterogeneity before interpreting pooled effects
2. Consider publication bias in every meta-analysis
3. Use random-effects model when I² > 25%
4. Report prediction intervals for random-effects models
5. Conduct sensitivity analyses to test robustness
6. Follow Cochrane Handbook recommendations
7. Distinguish between statistical significance and clinical importance

You prioritize transparency and methodological rigor in evidence synthesis."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        """Planning prompt for meta-analysis strategy."""
        task_data = json.loads(state["messages"][0].content)
        
        return f"""Plan a comprehensive meta-analysis:

Study Effects Data:
{json.dumps(task_data.get('studies', [])[:3], indent=2)}
... ({len(task_data.get('studies', []))} studies total)

Configuration:
{json.dumps(task_data.get('config', {}), indent=2)}

Your plan should include:
1. Data validation (sample sizes, effect estimates, standard errors)
2. Choice of effect measure (OR, RR, MD, SMD)
3. Statistical model selection (fixed vs. random effects)
   - Consider heterogeneity expectations
   - Justification for model choice
4. Heterogeneity assessment strategy
5. Publication bias tests to perform
6. Subgroup analyses (if applicable)
7. Sensitivity analyses to conduct
8. Visualization specifications (forest plot, funnel plot)

Output as JSON:
{{
    "steps": ["validate_data", "calculate_weights", "pool_effects", "assess_heterogeneity", "test_bias"],
    "recommended_model": "random_effects",
    "heterogeneity_tests": ["cochran_q", "i_squared", "tau_squared"],
    "bias_tests": ["egger", "trim_and_fill"],
    "subgroup_variable": "study_quality",
    "visualizations": ["forest_plot", "funnel_plot"],
    "initial_query": "random-effects meta-analysis heterogeneity interpretation",
    "primary_collection": "cochrane_handbook"
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        """Execution prompt with RAG context."""
        task_data = json.loads(state["messages"][0].content)
        plan = state.get("plan", {})
        
        return f"""Execute meta-analysis:

Plan: {json.dumps(plan, indent=2)}
Studies: {len(task_data.get('studies', []))} included

Meta-Analysis Guidelines Context:
{context}

Tasks:
1. Calculate study weights (inverse variance weighting)
2. Pool effect sizes using {plan.get('recommended_model', 'random_effects')} model
3. Calculate 95% confidence intervals
4. Assess heterogeneity:
   - Cochran's Q test
   - I² statistic with 95% CI
   - τ² (between-study variance)
5. Test for publication bias:
   - Egger's regression test
   - Trim-and-fill method
6. Conduct subgroup analysis (if applicable)
7. Leave-one-out sensitivity analysis
8. Generate forest plot and funnel plot specifications

Return JSON:
{{
    "pooled_effect": 1.45,
    "ci_lower": 1.12,
    "ci_upper": 1.89,
    "p_value": 0.003,
    "model_used": "random_effects",
    "heterogeneity": {{
        "i_squared": 68.5,
        "tau_squared": 0.15,
        "cochran_q": 25.3,
        "cochran_q_p": 0.001
    }},
    "publication_bias": {{
        "egger_p": 0.23,
        "trim_and_fill_k0": 2,
        "adjusted_effect": 1.38
    }},
    "forest_plot_data": {{...}},
    "funnel_plot_data": {{...}},
    "interpretation": "Random-effects meta-analysis shows..."
}}"""


    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured result."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
            else:
                raise ValueError("No JSON in response")
        except Exception as e:
            logger.error(f"Failed to parse execution result: {e}")
            return {
                "pooled_effect": 0.0,
                "model_used": "random_effects",
            }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Quality check for meta-analysis results."""
        result = state.get("execution_result", {})
        criteria_scores = {}
        feedback_parts = []
        
        # 1. Heterogeneity assessment (30% weight)
        heterogeneity = result.get("heterogeneity", {})
        if heterogeneity:
            has_i_squared = "i_squared" in heterogeneity
            has_tau = "tau_squared" in heterogeneity
            has_q_test = "cochran_q" in heterogeneity
            
            if has_i_squared and has_tau and has_q_test:
                criteria_scores["heterogeneity"] = 1.0
            elif has_i_squared:
                criteria_scores["heterogeneity"] = 0.6
                feedback_parts.append("Include τ² and Cochran's Q for complete heterogeneity assessment")
            else:
                criteria_scores["heterogeneity"] = 0.3
                feedback_parts.append("Heterogeneity not assessed")
        else:
            criteria_scores["heterogeneity"] = 0.0
            feedback_parts.append("Heterogeneity assessment missing")
        
        # 2. Publication bias assessment (25% weight)
        pub_bias = result.get("publication_bias", {})
        if pub_bias and ("egger_p" in pub_bias or "trim_and_fill_k0" in pub_bias):
            criteria_scores["publication_bias"] = 1.0
        else:
            criteria_scores["publication_bias"] = 0.0
            feedback_parts.append("Publication bias not assessed")
        
        # 3. Model appropriateness (20% weight)
        model_used = result.get("model_used", "")
        i_squared = heterogeneity.get("i_squared", 0)
        
        if i_squared > 50 and "random" in model_used:
            criteria_scores["model_choice"] = 1.0
        elif i_squared <= 50 and "fixed" in model_used:
            criteria_scores["model_choice"] = 1.0
        elif i_squared > 25 and "random" in model_used:
            criteria_scores["model_choice"] = 0.8
        else:
            criteria_scores["model_choice"] = 0.5
            feedback_parts.append(f"Consider model appropriateness (I²={i_squared:.1f}%)")
        
        # 4. Sensitivity analysis (15% weight)
        sensitivity = result.get("sensitivity", [])
        if sensitivity and len(sensitivity) > 0:
            criteria_scores["sensitivity"] = 1.0
        else:
            criteria_scores["sensitivity"] = 0.5
            feedback_parts.append("Add leave-one-out sensitivity analysis")
        
        # 5. Interpretation quality (10% weight)
        interpretation = result.get("interpretation", "")
        if interpretation and len(interpretation) > 50:
            criteria_scores["interpretation"] = 1.0
        else:
            criteria_scores["interpretation"] = 0.3
            feedback_parts.append("Provide clinical interpretation of findings")
        
        # Calculate overall score
        weights = {
            "heterogeneity": 0.30,
            "publication_bias": 0.25,
            "model_choice": 0.20,
            "sensitivity": 0.15,
            "interpretation": 0.10,
        }
        
        overall = sum(criteria_scores.get(k, 0) * weights[k] for k in weights)
        feedback = "; ".join(feedback_parts) if feedback_parts else "Meta-analysis meets quality standards"
        
        return QualityCheckResult(
            passed=overall >= self.config.quality_threshold,
            score=overall,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


    # =========================================================================
    # Core Meta-Analysis Methods
    # =========================================================================

    async def execute(
        self,
        studies: List[StudyEffect],
        config: MetaAnalysisConfig
    ) -> MetaAnalysisResult:
        """
        Execute complete meta-analysis workflow.
        
        Args:
            studies: List of study effect sizes
            config: Meta-analysis configuration
        
        Returns:
            MetaAnalysisResult with pooled effect, heterogeneity, bias assessment
        """
        logger.info(f"[MetaAnalysisAgent] Starting meta-analysis of {len(studies)} studies")
        
        input_data = {
            "studies": [s.model_dump() for s in studies],
            "config": config.model_dump(),
        }
        
        agent_result = await self.run(
            task_id=f"meta_analysis_{datetime.utcnow().timestamp()}",
            stage_id=10,
            research_id=config.effect_measure.value,
            input_data=input_data,
        )
        
        if not agent_result.success:
            logger.error(f"Meta-analysis failed: {agent_result.error}")
            return self._create_empty_result()
        
        # Build result from execution
        exec_result = agent_result.result or {}
        
        # Calculate actual statistics
        pooled_result = self.pool_effects(studies, config.model_type)
        heterogeneity = self.assess_heterogeneity(studies, pooled_result)
        pub_bias = await self.test_publication_bias(studies, config) if config.test_publication_bias else None
        sensitivity = self.sensitivity_analysis(studies, config.model_type)
        
        # Generate visualizations
        forest_data = self.generate_forest_plot_data(studies, pooled_result, heterogeneity)
        funnel_data = self.generate_funnel_plot_data(studies, pooled_result)
        
        return MetaAnalysisResult(
            effect_measure=config.effect_measure,
            model_type=config.model_type,
            n_studies=len(studies),
            total_n=sum(s.sample_size or 0 for s in studies),
            pooled_effect=pooled_result["pooled_effect"],
            ci_lower=pooled_result["ci_lower"],
            ci_upper=pooled_result["ci_upper"],
            p_value=pooled_result["p_value"],
            z_score=pooled_result["z_score"],
            study_weights=pooled_result["weights"],
            heterogeneity=heterogeneity,
            publication_bias=pub_bias,
            sensitivity=sensitivity,
            forest_plot_data=forest_data,
            funnel_plot_data=funnel_data,
            summary=exec_result.get("interpretation", ""),
        )

    def pool_effects(
        self,
        studies: List[StudyEffect],
        model_type: ModelType
    ) -> Dict[str, Any]:
        """
        Pool effect sizes using inverse variance weighting.
        
        Args:
            studies: List of study effects
            model_type: Fixed or random effects model
        
        Returns:
            Dictionary with pooled estimate, CI, weights
        """
        effects = np.array([s.effect_estimate for s in studies])
        variances = np.array([s.se**2 if s.se else 0.01 for s in studies])
        
        if model_type in [ModelType.RANDOM_EFFECTS, ModelType.RANDOM_EFFECTS_REML]:
            # DerSimonian-Laird random-effects
            tau_squared = self._estimate_tau_squared(effects, variances)
            variances = variances + tau_squared
        
        # Inverse variance weights
        weights = 1 / variances
        weights_normalized = weights / np.sum(weights)
        
        # Pooled effect
        pooled_effect = np.sum(effects * weights_normalized)
        
        # Standard error and CI
        pooled_se = np.sqrt(1 / np.sum(weights))
        z_score = pooled_effect / pooled_se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        ci_lower = pooled_effect - 1.96 * pooled_se
        ci_upper = pooled_effect + 1.96 * pooled_se
        
        # Study weights dictionary
        study_weights = {
            s.study_id: float(w) for s, w in zip(studies, weights_normalized)
        }
        
        return {
            "pooled_effect": float(pooled_effect),
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "p_value": float(p_value),
            "z_score": float(z_score),
            "weights": study_weights,
        }

    def _estimate_tau_squared(
        self,
        effects: np.ndarray,
        variances: np.ndarray
    ) -> float:
        """
        Estimate between-study variance (τ²) using DerSimonian-Laird method.
        
        Args:
            effects: Array of effect estimates
            variances: Array of within-study variances
        
        Returns:
            Estimated τ²
        """
        k = len(effects)
        weights = 1 / variances
        
        # Weighted mean
        pooled = np.sum(effects * weights) / np.sum(weights)
        
        # Q statistic
        Q = np.sum(weights * (effects - pooled)**2)
        
        # Expected value of Q under null
        c = np.sum(weights) - (np.sum(weights**2) / np.sum(weights))
        
        # Tau-squared
        tau_squared = max(0, (Q - (k - 1)) / c)
        
        return float(tau_squared)


    def assess_heterogeneity(
        self,
        studies: List[StudyEffect],
        pooled_result: Dict[str, Any]
    ) -> HeterogeneityResult:
        """
        Assess heterogeneity using Cochran's Q, I², τ².
        
        Args:
            studies: List of study effects
            pooled_result: Result from pool_effects()
        
        Returns:
            HeterogeneityResult object
        """
        effects = np.array([s.effect_estimate for s in studies])
        variances = np.array([s.se**2 if s.se else 0.01 for s in studies])
        weights = 1 / variances
        
        pooled_effect = pooled_result["pooled_effect"]
        k = len(studies)
        
        # Cochran's Q
        Q = np.sum(weights * (effects - pooled_effect)**2)
        df = k - 1
        Q_p = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
        
        # I² statistic
        I_squared = max(0, ((Q - df) / Q) * 100) if Q > 0 else 0
        
        # I² confidence interval (Higgins & Thompson 2002)
        I_squared_ci_lower = max(0, (1 - np.sqrt(1 / Q)) * 100) if Q > 1 else 0
        I_squared_ci_upper = min(100, (1 - stats.chi2.ppf(0.025, df) / Q) * 100) if Q > 0 and df > 0 else 100
        
        # Tau-squared
        tau_squared = self._estimate_tau_squared(effects, variances)
        tau = np.sqrt(tau_squared)
        
        # H statistic
        H = np.sqrt(Q / df) if df > 0 else 1.0
        
        # Interpretation
        if I_squared < 25:
            interpretation = "Low heterogeneity"
        elif I_squared < 50:
            interpretation = "Moderate heterogeneity"
        elif I_squared < 75:
            interpretation = "Substantial heterogeneity"
        else:
            interpretation = "Considerable heterogeneity"
        
        return HeterogeneityResult(
            cochran_q=float(Q),
            cochran_q_p=float(Q_p),
            df=int(df),
            i_squared=float(I_squared),
            i_squared_ci_lower=float(I_squared_ci_lower),
            i_squared_ci_upper=float(I_squared_ci_upper),
            tau_squared=float(tau_squared),
            tau=float(tau),
            h_statistic=float(H),
            interpretation=interpretation,
        )

    async def test_publication_bias(
        self,
        studies: List[StudyEffect],
        config: MetaAnalysisConfig
    ) -> PublicationBiasResult:
        """
        Test for publication bias using Egger's test and trim-and-fill.
        
        Args:
            studies: List of study effects
            config: Meta-analysis configuration
        
        Returns:
            PublicationBiasResult object
        """
        if len(studies) < 3:
            return PublicationBiasResult(
                test_name="Egger's test",
                statistic=0.0,
                p_value=1.0,
                interpretation="Insufficient studies for publication bias assessment"
            )
        
        effects = np.array([s.effect_estimate for s in studies])
        se = np.array([s.se if s.se else 0.1 for s in studies])
        
        # Egger's regression test
        precision = 1 / se
        
        # Linear regression: effect/se = b0 + b1 * (1/se)
        standardized_effect = effects / se
        X = np.column_stack([np.ones(len(studies)), precision])
        
        try:
            from scipy.linalg import lstsq
            beta, _, _, _ = lstsq(X, standardized_effect)
            
            # Test intercept
            residuals = standardized_effect - (beta[0] + beta[1] * precision)
            mse = np.sum(residuals**2) / (len(studies) - 2)
            se_intercept = np.sqrt(mse * np.linalg.inv(X.T @ X)[0, 0])
            t_stat = beta[0] / se_intercept
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), len(studies) - 2))
        except Exception as e:
            logger.warning(f"Egger's test failed: {e}")
            t_stat = 0.0
            p_value = 1.0
        
        # Trim-and-fill (simplified)
        k0 = 0
        trim_fill_effect = None
        if config.trim_and_fill:
            # Count asymmetric studies (basic implementation)
            median_effect = np.median(effects)
            asymmetry = np.sum(effects < median_effect) - np.sum(effects > median_effect)
            k0 = abs(asymmetry) // 2
            
            if k0 > 0:
                # Impute missing studies
                imputed_effects = np.concatenate([effects, np.full(k0, median_effect)])
                imputed_se = np.concatenate([se, np.full(k0, np.median(se))])
                
                # Re-calculate pooled effect
                weights = 1 / imputed_se**2
                trim_fill_effect = np.sum(imputed_effects * weights) / np.sum(weights)
        
        # Interpretation
        if p_value < 0.05:
            interpretation = f"Significant publication bias detected (p = {p_value:.3f})"
        else:
            interpretation = f"No significant publication bias detected (p = {p_value:.3f})"
        
        return PublicationBiasResult(
            test_name="Egger's test",
            statistic=float(t_stat),
            p_value=float(p_value),
            trim_and_fill_k0=int(k0) if k0 > 0 else None,
            trim_and_fill_estimate=float(trim_fill_effect) if trim_fill_effect else None,
            interpretation=interpretation,
        )

    def sensitivity_analysis(
        self,
        studies: List[StudyEffect],
        model_type: ModelType
    ) -> List[SensitivityAnalysisResult]:
        """
        Leave-one-out sensitivity analysis.
        
        Args:
            studies: List of study effects
            model_type: Model type to use
        
        Returns:
            List of SensitivityAnalysisResult objects
        """
        results = []
        
        for i, excluded_study in enumerate(studies):
            # Create subset excluding current study
            subset = studies[:i] + studies[i+1:]
            
            if len(subset) < 2:
                continue
            
            # Re-run meta-analysis
            pooled = self.pool_effects(subset, model_type)
            heterogeneity = self.assess_heterogeneity(subset, pooled)
            
            results.append(SensitivityAnalysisResult(
                excluded_study_id=excluded_study.study_id,
                pooled_effect=pooled["pooled_effect"],
                ci_lower=pooled["ci_lower"],
                ci_upper=pooled["ci_upper"],
                i_squared=heterogeneity.i_squared,
            ))
        
        return results

    def generate_forest_plot_data(
        self,
        studies: List[StudyEffect],
        pooled_result: Dict[str, Any],
        heterogeneity: HeterogeneityResult
    ) -> Dict[str, Any]:
        """
        Generate data specification for forest plot visualization.
        
        Returns JSON structure for frontend rendering (not actual image).
        """
        study_data = []
        for study in studies:
            study_data.append({
                "label": study.study_label,
                "effect": study.effect_estimate,
                "ci_lower": study.ci_lower or (study.effect_estimate - 1.96 * (study.se or 0.1)),
                "ci_upper": study.ci_upper or (study.effect_estimate + 1.96 * (study.se or 0.1)),
                "weight": pooled_result["weights"].get(study.study_id, 0) * 100,
            })
        
        return {
            "type": "forest_plot",
            "studies": study_data,
            "pooled": {
                "effect": pooled_result["pooled_effect"],
                "ci_lower": pooled_result["ci_lower"],
                "ci_upper": pooled_result["ci_upper"],
            },
            "heterogeneity": {
                "i_squared": heterogeneity.i_squared,
                "tau_squared": heterogeneity.tau_squared,
                "p_value": heterogeneity.cochran_q_p,
            },
            "x_axis_label": "Effect Size",
            "title": "Forest Plot",
        }

    def generate_funnel_plot_data(
        self,
        studies: List[StudyEffect],
        pooled_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate data specification for funnel plot visualization.
        """
        plot_data = []
        for study in studies:
            plot_data.append({
                "effect": study.effect_estimate,
                "se": study.se or 0.1,
                "label": study.study_label,
            })
        
        return {
            "type": "funnel_plot",
            "studies": plot_data,
            "pooled_effect": pooled_result["pooled_effect"],
            "x_axis_label": "Effect Size",
            "y_axis_label": "Standard Error",
            "title": "Funnel Plot (Publication Bias Assessment)",
        }

    def _create_empty_result(self) -> MetaAnalysisResult:
        """Create empty result for error cases."""
        return MetaAnalysisResult(
            effect_measure=EffectMeasure.ODDS_RATIO,
            model_type=ModelType.RANDOM_EFFECTS,
            n_studies=0,
            total_n=0,
            pooled_effect=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            p_value=1.0,
            z_score=0.0,
            warnings=["Meta-analysis execution failed"],
        )


# =============================================================================
# Factory Function
# =============================================================================

def create_meta_analysis_agent() -> MetaAnalysisAgent:
    """Factory function for creating MetaAnalysisAgent."""
    return MetaAnalysisAgent()

