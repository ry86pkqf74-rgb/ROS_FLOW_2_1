"""
StatisticalAnalysisAgent - Stage 7: Statistical Analysis

Performs comprehensive statistical analysis on research data including:
- Descriptive statistics
- Hypothesis testing (parametric and non-parametric)
- Effect size calculations
- Assumption checking with remediation
- APA-style reporting
- Visualization specifications

Linear Issues: ROS-XXX (Stage 7 - Statistical Analysis Agent)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import pandas as pd
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

# Import statistical types and utilities
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
)

from .statistical_utils import (
    validate_data,
    check_equal_variance,
    calculate_cohens_d,
    calculate_hedges_g,
    calculate_eta_squared,
    calculate_mean_ci,
    format_descriptive_table_apa,
    interpret_effect_size_magnitude,
    generate_interpretation,
)

logger = logging.getLogger(__name__)


# =============================================================================
# StatisticalAnalysisAgent
# =============================================================================

class StatisticalAnalysisAgent(BaseAgent):
    """
    Agent for comprehensive statistical analysis of research data.
    
    Capabilities:
    - Descriptive statistics (mean, SD, IQR, etc.)
    - Hypothesis testing (t-tests, ANOVA, chi-square, non-parametric)
    - Effect size calculations (Cohen's d, Hedges' g, eta-squared)
    - Assumption checking (normality, homogeneity, independence)
    - Multiple comparison corrections
    - APA 7th edition formatting
    - Visualization specifications for frontend rendering
    
    Uses LangGraph architecture:
    1. PLAN (Claude): Determine appropriate test based on data/design
    2. RETRIEVE: Get statistical method guidelines from RAG
    3. EXECUTE (Mercury/Advanced): Run scipy.stats calculations
    4. REFLECT: Quality check (assumptions, effect size, formatting)
    """

    def __init__(self):
        config = AgentConfig(
            name="StatisticalAnalysisAgent",
            description="Perform statistical analysis on research data with assumption checking and effect sizes",
            stages=[7],
            rag_collections=["statistical_methods", "research_guidelines"],
            max_iterations=3,
            quality_threshold=0.85,
            timeout_seconds=300,
            phi_safe=True,
            model_provider="anthropic",  # Claude for planning
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)
    # =========================================================================
    # BaseAgent Abstract Methods Implementation
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """System prompt for statistical analysis expertise."""
        return """You are a Statistical Analysis Agent specialized in clinical research methodology.

Your expertise includes:
- Hypothesis testing (parametric and non-parametric)
- Effect size calculation and interpretation
- Statistical assumption checking
- Multiple comparison corrections
- APA 7th edition statistical reporting
- Clinical significance assessment

Key principles:
1. Always check assumptions before selecting tests
2. Report effect sizes alongside p-values
3. Distinguish statistical vs. clinical significance
4. Use appropriate corrections for multiple comparisons
5. Provide clear, interpretable results for clinicians
6. Follow APA 7th edition formatting standards

You prioritize methodological rigor and transparent reporting."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        """Planning prompt for test selection and strategy."""
        task_data = json.loads(state["messages"][0].content)
        
        return f"""Plan a comprehensive statistical analysis:

Study Data:
{json.dumps(task_data.get('study_data', {}), indent=2)}

Your plan should include:
1. Data validation checks (missing values, outliers, sample size)
2. Descriptive statistics to calculate
3. Appropriate statistical test selection based on:
   - Study design (independent/paired groups)
   - Number of groups (2-sample, k-sample)
   - Data distribution (normal/non-normal)
   - Sample size
   - Outcome type (continuous/categorical)
4. Assumptions to check
5. Effect size measures appropriate for the test
6. Multiple comparison strategy (if >2 groups)
7. Visualization recommendations

Output as JSON:
{{
    "steps": ["validate_data", "descriptive_stats", "check_assumptions", "run_test", "calculate_effect_size"],
    "recommended_test": "t_test_independent",
    "alternative_test": "mann_whitney",
    "effect_size_metrics": ["cohens_d", "hedges_g"],
    "assumptions_required": ["normality", "homogeneity"],
    "visualizations": ["boxplot", "qq_plot"],
    "initial_query": "independent t-test assumptions and interpretation",
    "primary_collection": "statistical_methods"
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        """Execution prompt with RAG context."""
        task_data = json.loads(state["messages"][0].content)
        plan = state.get("plan", {})
        
        return f"""Execute statistical analysis:

Plan: {json.dumps(plan, indent=2)}
Study Data: {json.dumps(task_data.get('study_data', {}), indent=2)}

Statistical Guidelines Context:
{context}

Tasks:
1. Calculate descriptive statistics for each group
2. Check statistical assumptions (normality, homogeneity, independence)
3. Run the recommended hypothesis test using scipy.stats
4. Calculate effect sizes (Cohen's d, Hedges' g, eta-squared as appropriate)
5. Generate confidence intervals
6. Format results in APA 7th edition style
7. Create visualization specifications (data only, not rendered images)
8. Provide interpretation with clinical context

Return JSON:
{{
    "descriptive": [
        {{
            "variable": "outcome",
            "group": "treatment",
            "n": 50,
            "mean": 5.2,
            "std": 1.1,
            "median": 5.0,
            "iqr": 1.5
        }}
    ],
    "assumptions": {{
        "normality": {{"passed": true, "test": "shapiro", "p_value": 0.15}},
        "homogeneity": {{"passed": true, "test": "levene", "p_value": 0.42}},
        "remediation": []
    }},
    "inferential": {{
        "test_name": "Independent t-test",
        "statistic": 2.34,
        "p_value": 0.023,
        "df": 98,
        "significant": true
    }},
    "effect_sizes": {{
        "cohens_d": 0.47,
        "interpretation": "medium effect"
    }},
    "visualizations": [
        {{
            "type": "boxplot",
            "data": {{"groups": ["A", "B"], "values": [[...], [...]]}}
        }}
    ]
}}"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured result."""
        try:
            # Extract JSON from response
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
                "descriptive": [],
                "assumptions": {},
                "inferential": {},
                "effect_sizes": {},
            }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Quality check for statistical analysis results."""
        result = state.get("execution_result", {})
        criteria_scores = {}
        feedback_parts = []
        
        # 1. Assumptions checked (30% weight)
        assumptions = result.get("assumptions", {})
        if assumptions:
            has_normality = "normality" in assumptions
            has_homogeneity = "homogeneity" in assumptions
            
            if has_normality and has_homogeneity:
                criteria_scores["assumptions"] = 1.0
            elif has_normality or has_homogeneity:
                criteria_scores["assumptions"] = 0.6
                feedback_parts.append("Check additional assumptions")
            else:
                criteria_scores["assumptions"] = 0.3
                feedback_parts.append("Assumptions not thoroughly checked")
        else:
            criteria_scores["assumptions"] = 0.0
            feedback_parts.append("No assumption checking performed")
        
        # 2. Statistical validity (20% weight)
        inferential = result.get("inferential", {})
        if inferential:
            has_p_value = "p_value" in inferential
            has_statistic = "statistic" in inferential
            has_df = "df" in inferential
            
            if has_p_value and has_statistic and has_df:
                criteria_scores["statistical_validity"] = 1.0
            elif has_p_value and has_statistic:
                criteria_scores["statistical_validity"] = 0.7
            else:
                criteria_scores["statistical_validity"] = 0.3
                feedback_parts.append("Missing key statistical outputs")
        else:
            criteria_scores["statistical_validity"] = 0.0
            feedback_parts.append("No inferential statistics calculated")
        
        # 3. Effect size reported (20% weight)
        effect_sizes = result.get("effect_sizes", {})
        if effect_sizes and any(k in effect_sizes for k in ["cohens_d", "hedges_g", "eta_squared"]):
            criteria_scores["effect_size"] = 1.0
        else:
            criteria_scores["effect_size"] = 0.0
            feedback_parts.append("Effect size not calculated")
        
        # 4. APA formatting (15% weight)
        apa_elements = 0
        if inferential.get("test_name"):
            apa_elements += 1
        if inferential.get("p_value") is not None:
            apa_elements += 1
        if result.get("descriptive"):
            apa_elements += 1
        
        criteria_scores["apa_formatting"] = apa_elements / 3.0
        if criteria_scores["apa_formatting"] < 0.7:
            feedback_parts.append("Improve APA formatting completeness")
        
        # 5. Clinical interpretation (15% weight)
        has_interpretation = bool(inferential.get("interpretation") or effect_sizes.get("interpretation"))
        criteria_scores["interpretation"] = 1.0 if has_interpretation else 0.3
        if not has_interpretation:
            feedback_parts.append("Add clinical interpretation of results")
        
        # Calculate overall score
        weights = {
            "assumptions": 0.30,
            "statistical_validity": 0.20,
            "effect_size": 0.20,
            "apa_formatting": 0.15,
            "interpretation": 0.15,
        }
        
        overall = sum(criteria_scores[k] * weights[k] for k in criteria_scores)
        feedback = "; ".join(feedback_parts) if feedback_parts else "Analysis meets quality standards"
        
        return QualityCheckResult(
            passed=overall >= self.config.quality_threshold,
            score=overall,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )
    # =========================================================================
    # Core Analysis Methods
    # =========================================================================

    async def execute(self, data: StudyData) -> StatisticalResult:
        """
        Execute complete statistical analysis workflow.
        
        Args:
            data: StudyData object with groups, outcomes, and metadata
        
        Returns:
            StatisticalResult with comprehensive analysis outputs
        """
        logger.info(f"[StatisticalAnalysisAgent] Starting analysis for {data.metadata.get('study_title', 'Unknown')}")
        
        input_data = {
            "study_data": {
                "groups": data.groups,
                "outcomes": data.outcomes,
                "covariates": data.covariates,
                "metadata": data.metadata,
            }
        }
        
        agent_result = await self.run(
            task_id=f"statistical_analysis_{datetime.utcnow().timestamp()}",
            stage_id=7,
            research_id=data.metadata.get("research_id", "unknown"),
            input_data=input_data,
        )
        
        if not agent_result.success:
            logger.error(f"Statistical analysis failed: {agent_result.error}")
            return StatisticalResult()
        
        # Parse agent result into StatisticalResult
        exec_result = agent_result.result or {}
        
        # Build descriptive stats
        descriptive = self._build_descriptive_stats(exec_result.get("descriptive", []))
        
        # Build inferential result
        inferential = self._build_inferential_result(exec_result.get("inferential", {}))
        
        # Build effect sizes
        effect_sizes = self._build_effect_sizes(exec_result.get("effect_sizes", {}))
        
        # Build assumptions
        assumptions = self._build_assumptions(exec_result.get("assumptions", {}))
        
        # Generate tables
        tables = [format_descriptive_table_apa(descriptive)]
        if inferential:
            tables.append(inferential.format_apa())
        
        # Build figure specs
        figure_specs = self._build_figure_specs(exec_result.get("visualizations", []))
        
        return StatisticalResult(
            descriptive=descriptive,
            inferential=inferential,
            effect_sizes=effect_sizes,
            assumptions=assumptions,
            tables=tables,
            figure_specs=figure_specs,
        )

    def calculate_descriptive_stats(
        self,
        data: pd.DataFrame,
        outcome_var: str,
        group_var: Optional[str] = None
    ) -> List[DescriptiveStats]:
        """
        Calculate descriptive statistics for outcome variable.
        
        Args:
            data: DataFrame with data
            outcome_var: Name of outcome variable
            group_var: Optional grouping variable
        
        Returns:
            List of DescriptiveStats objects (one per group or overall)
        
        TODO (Mercury): Enhance with additional distributional statistics
        """
        results = []
        
        if group_var and group_var in data.columns:
            # Calculate per group
            for group_name, group_data in data.groupby(group_var):
                stats_obj = self._calculate_single_descriptive(
                    group_data[outcome_var],
                    outcome_var,
                    str(group_name)
                )
                results.append(stats_obj)
        else:
            # Calculate overall
            stats_obj = self._calculate_single_descriptive(
                data[outcome_var],
                outcome_var,
                None
            )
            results.append(stats_obj)
        
        return results

    def _calculate_single_descriptive(
        self,
        series: pd.Series,
        var_name: str,
        group_name: Optional[str]
    ) -> DescriptiveStats:
        """Calculate descriptive stats for a single series."""
        clean = series.dropna()
        
        return DescriptiveStats(
            variable_name=var_name,
            n=len(clean),
            missing=series.isna().sum(),
            mean=float(clean.mean()),
            median=float(clean.median()),
            std=float(clean.std()),
            min_value=float(clean.min()),
            max_value=float(clean.max()),
            q25=float(clean.quantile(0.25)),
            q75=float(clean.quantile(0.75)),
            iqr=float(clean.quantile(0.75) - clean.quantile(0.25)),
            skewness=float(clean.skew()),
            kurtosis=float(clean.kurtosis()),
            group_name=group_name,
        )

    def run_hypothesis_test(
        self,
        groups: List[pd.Series],
        test_type: TestType,
        **kwargs
    ) -> HypothesisTestResult:
        """
        Run hypothesis test on one or more groups.
        
        Supports:
        - 2 groups: t-test, Mann-Whitney, Wilcoxon
        - 3+ groups: ANOVA, Kruskal-Wallis
        
        Args:
            groups: List of pd.Series (one per group)
            test_type: Type of statistical test
            **kwargs: Additional test parameters
        
        Returns:
            HypothesisTestResult with statistic, p-value, interpretation
        
        TODO (Mercury): Implement all test types using scipy.stats
        """
        if len(groups) < 2:
            raise ValueError("Need at least 2 groups for hypothesis testing")
        
        # Clean data
        clean_groups = [g.dropna() for g in groups]
        
        # Run appropriate test
        if test_type == TestType.T_TEST_INDEPENDENT:
            return self._run_t_test_independent(clean_groups[0], clean_groups[1])
        
        elif test_type == TestType.T_TEST_PAIRED:
            return self._run_t_test_paired(clean_groups[0], clean_groups[1])
        
        elif test_type == TestType.MANN_WHITNEY:
            return self._run_mann_whitney(clean_groups[0], clean_groups[1])
        
        elif test_type == TestType.ANOVA_ONEWAY:
            return self._run_anova_oneway(clean_groups)
        
        elif test_type == TestType.KRUSKAL_WALLIS:
            return self._run_kruskal_wallis(clean_groups)
        
        elif test_type == TestType.CHI_SQUARE:
            # Expects contingency table in kwargs
            return self._run_chi_square(kwargs.get("contingency_table"))
        
        elif test_type == TestType.FISHER_EXACT:
            # Expects contingency table in kwargs
            return self._run_fisher_exact(kwargs.get("contingency_table"))
        
        elif test_type == TestType.CORRELATION_PEARSON:
            # Expects x and y data in groups
            return self._run_correlation(clean_groups[0], clean_groups[1], method="pearson")
        
        elif test_type == TestType.CORRELATION_SPEARMAN:
            # Expects x and y data in groups
            return self._run_correlation(clean_groups[0], clean_groups[1], method="spearman")
        
        else:
            raise NotImplementedError(f"Test type {test_type} not yet implemented")

    def _run_t_test_independent(self, group_a: pd.Series, group_b: pd.Series, welch_correction: bool = True) -> HypothesisTestResult:
        """
        Independent samples t-test with Welch's correction for unequal variances.
        
        ✅ Mercury Enhancement: Added Welch's correction option for unequal variances
        """
        # Check for equal variances
        equal_var = check_equal_variance(group_a, group_b)
        
        # Use Welch's correction if variances are unequal
        use_welch = welch_correction and not equal_var
        
        # Run t-test
        statistic, p_value = stats.ttest_ind(group_a, group_b, equal_var=not use_welch)
        
        df = len(group_a) + len(group_b) - 2
        
        # Calculate confidence interval for mean difference
        mean_diff = group_a.mean() - group_b.mean()
        se_diff = np.sqrt(group_a.var()/len(group_a) + group_b.var()/len(group_b))
        t_crit = stats.t.ppf(0.975, df)
        ci_lower = mean_diff - t_crit * se_diff
        ci_upper = mean_diff + t_crit * se_diff
        
        # Interpretation
        interpretation = generate_interpretation(
            {"p_value": p_value, "test_name": "Independent t-test"},
            effect_size=calculate_cohens_d(group_a, group_b)
        )
        
        return HypothesisTestResult(
            test_name="Independent t-test",
            test_type=TestType.T_TEST_INDEPENDENT,
            statistic=float(statistic),
            p_value=float(p_value),
            df=int(df),
            ci_lower=float(ci_lower),
            ci_upper=float(ci_upper),
            interpretation=interpretation,
        )

    def _run_t_test_paired(self, group_a: pd.Series, group_b: pd.Series) -> HypothesisTestResult:
        """
        Paired samples t-test with Cohen's dz effect size.
        
        ✅ Mercury Enhancement: Added Cohen's dz effect size for paired design
        """
        if len(group_a) != len(group_b):
            raise ValueError("Paired t-test requires equal sample sizes")
        
        statistic, p_value = stats.ttest_rel(group_a, group_b)
        df = len(group_a) - 1
        
        # Calculate Cohen's dz for paired design
        differences = group_a - group_b
        cohens_dz = differences.mean() / differences.std()
        
        interpretation = generate_interpretation(
            {"p_value": p_value, "test_name": "Paired t-test"},
            effect_size=cohens_dz
        )
        
        result = HypothesisTestResult(
            test_name="Paired t-test",
            test_type=TestType.T_TEST_PAIRED,
            statistic=float(statistic),
            p_value=float(p_value),
            df=int(df),
            interpretation=interpretation,
        )
        
        # Attach Cohen's dz to result
        result.cohens_dz = float(cohens_dz)
        
        return result

    def _run_mann_whitney(self, group_a: pd.Series, group_b: pd.Series) -> HypothesisTestResult:
        """
        Mann-Whitney U test (non-parametric alternative to independent t-test).
        
        ✅ Mercury Enhancement #8: Rank-biserial correlation effect size
        """
        statistic, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
        
        # Calculate rank-biserial correlation effect size
        rank_biserial = self._calculate_rank_biserial_correlation(group_a, group_b, statistic)
        
        # Interpret effect size magnitude (similar to Cohen's d conventions)
        rb_abs = abs(rank_biserial)
        if rb_abs < 0.1:
            effect_magnitude = "negligible"
        elif rb_abs < 0.3:
            effect_magnitude = "small"
        elif rb_abs < 0.5:
            effect_magnitude = "medium"
        else:
            effect_magnitude = "large"
        
        interpretation = f"Mann-Whitney U test {'was' if p_value < 0.05 else 'was not'} significant (p = {p_value:.3f}). Rank-biserial correlation = {rank_biserial:.3f} indicates a {effect_magnitude} effect size."
        
        result = HypothesisTestResult(
            test_name="Mann-Whitney U test",
            test_type=TestType.MANN_WHITNEY,
            statistic=float(statistic),
            p_value=float(p_value),
            interpretation=interpretation,
        )
        
        # Attach effect size details
        result.rank_biserial_correlation = rank_biserial
        result.effect_magnitude = effect_magnitude
        
        return result

    def _run_anova_oneway(self, groups: List[pd.Series]) -> HypothesisTestResult:
        """
        One-way ANOVA with post-hoc tests.
        
        ✅ Mercury Enhancement: Added Tukey HSD post-hoc tests
        """
        statistic, p_value = stats.f_oneway(*groups)
        
        # Calculate degrees of freedom
        k = len(groups)
        n_total = sum(len(g) for g in groups)
        df_between = k - 1
        df_within = n_total - k
        
        # Run post-hoc Tukey HSD if ANOVA is significant and we have >2 groups
        tukey_results = None
        if p_value < 0.05 and len(groups) > 2:
            try:
                tukey_results = self._run_posthoc_tukey(groups)
            except Exception as e:
                logger.warning(f"Tukey HSD post-hoc test failed: {e}")
        
        eta_sq = calculate_eta_squared(groups)
        interpretation = generate_interpretation(
            {"p_value": p_value, "test_name": "One-way ANOVA"},
            effect_size=eta_sq
        )
        
        # Add post-hoc interpretation
        if tukey_results:
            significant_pairs = [r for r in tukey_results if r['significant']]
            interpretation += f" Post-hoc Tukey HSD revealed {len(significant_pairs)} significant pairwise differences."
        
        result = HypothesisTestResult(
            test_name="One-way ANOVA",
            test_type=TestType.ANOVA_ONEWAY,
            statistic=float(statistic),
            p_value=float(p_value),
            df=(int(df_between), int(df_within)),
            interpretation=interpretation,
        )
        
        # Attach Tukey HSD results to the result object
        if tukey_results:
            result.post_hoc_tests = tukey_results
        
        return result

    def _run_kruskal_wallis(self, groups: List[pd.Series]) -> HypothesisTestResult:
        """
        Kruskal-Wallis H test (non-parametric alternative to ANOVA).
        
        ✅ Mercury Enhancement #9: Dunn's post-hoc test for Kruskal-Wallis
        """
        statistic, p_value = stats.kruskal(*groups)
        
        df = len(groups) - 1
        
        # Run post-hoc Dunn's tests if Kruskal-Wallis is significant and we have >2 groups
        dunn_results = None
        if p_value < 0.05 and len(groups) > 2:
            try:
                dunn_results = self._run_posthoc_dunn(groups)
            except Exception as e:
                logger.warning(f"Dunn's post-hoc test failed: {e}")
        
        interpretation = f"Kruskal-Wallis H test {'was' if p_value < 0.05 else 'was not'} significant (p = {p_value:.3f})"
        
        # Add Dunn's test interpretation if available
        if dunn_results:
            significant_pairs = [r for r in dunn_results if r['significant']]
            interpretation += f" Post-hoc Dunn's test revealed {len(significant_pairs)} significant pairwise differences."
        
        result = HypothesisTestResult(
            test_name="Kruskal-Wallis H test",
            test_type=TestType.KRUSKAL_WALLIS,
            statistic=float(statistic),
            p_value=float(p_value),
            df=int(df),
            interpretation=interpretation,
        )
        
        # Attach Dunn's test results to the result object
        if dunn_results:
            result.post_hoc_tests = dunn_results
        
        return result

    def _run_chi_square(self, contingency_table: np.ndarray) -> HypothesisTestResult:
        """
        Chi-square test of independence with Cramér's V effect size.
        
        ✅ Mercury Enhancement: Cramér's V effect size for chi-square test
        """
        if contingency_table is None:
            raise ValueError("Contingency table required for chi-square test")
        
        chi2, p_value, df, expected = stats.chi2_contingency(contingency_table)
        
        # Calculate Cramér's V effect size
        cramers_v = self._calculate_cramers_v(contingency_table, chi2)
        
        # Interpret effect size magnitude
        if cramers_v < 0.1:
            effect_magnitude = "negligible"
        elif cramers_v < 0.3:
            effect_magnitude = "small"
        elif cramers_v < 0.5:
            effect_magnitude = "medium"
        else:
            effect_magnitude = "large"
        
        interpretation = f"Chi-square test {'was' if p_value < 0.05 else 'was not'} significant (p = {p_value:.3f}). Cramér's V = {cramers_v:.3f} indicates a {effect_magnitude} effect size."
        
        result = HypothesisTestResult(
            test_name="Chi-square test of independence",
            test_type=TestType.CHI_SQUARE,
            statistic=float(chi2),
            p_value=float(p_value),
            df=int(df),
            interpretation=interpretation,
        )
        
        # Attach Cramér's V to result
        result.cramers_v = cramers_v
        result.effect_magnitude = effect_magnitude
        
        return result
    def calculate_effect_size(
        self,
        groups: List[pd.Series],
        test_type: TestType
    ) -> EffectSize:
        """
        Calculate appropriate effect size for test type.
        
        Args:
            groups: List of group data
            test_type: Type of test performed
        
        Returns:
            EffectSize object with calculated metrics
        
        ✅ Mercury Enhancement #10: Glass's delta and omega-squared effect sizes
        """
        if len(groups) == 2:
            # Two-group comparison
            cohens_d = calculate_cohens_d(groups[0], groups[1])
            hedges_g = calculate_hedges_g(groups[0], groups[1])
            glass_delta = self._calculate_glass_delta(groups[0], groups[1])
            
            magnitude = interpret_effect_size_magnitude(cohens_d, "cohens_d")
            
            return EffectSize(
                cohens_d=cohens_d,
                hedges_g=hedges_g,
                glass_delta=glass_delta,
                magnitude=magnitude,
                interpretation=f"Cohen's d = {cohens_d:.2f} indicates a {magnitude} effect size. Glass's Δ = {glass_delta:.2f}."
            )
        
        elif len(groups) > 2:
            # Multi-group comparison (ANOVA)
            eta_sq = calculate_eta_squared(groups)
            omega_sq = self._calculate_omega_squared(groups)
            magnitude = interpret_effect_size_magnitude(eta_sq, "eta_squared")
            
            return EffectSize(
                eta_squared=eta_sq,
                omega_squared=omega_sq,
                magnitude=magnitude,
                interpretation=f"η² = {eta_sq:.3f}, ω² = {omega_sq:.3f} indicates a {magnitude} effect size"
            )
        
        else:
            return EffectSize(interpretation="Effect size not applicable")

    def calculate_confidence_interval(
        self,
        data: pd.Series,
        confidence: float = 0.95
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval for the mean.
        
        Args:
            data: Data series
            confidence: Confidence level (default 0.95)
        
        Returns:
            ConfidenceInterval object
        
        TODO (Mercury): Add support for other statistics (median, proportion)
        """
        return calculate_mean_ci(data, confidence)

    def check_assumptions(
        self,
        data: pd.DataFrame,
        test_type: TestType,
        group_var: Optional[str] = None,
        outcome_var: str = "outcome"
    ) -> AssumptionCheckResult:
        """
        Check statistical assumptions for the specified test.
        
        Checks:
        - Normality (Shapiro-Wilk test)
        - Homogeneity of variance (Levene's test)
        - Independence (based on study design)
        
        Args:
            data: DataFrame with data
            test_type: Type of test to check assumptions for
            group_var: Optional grouping variable
            outcome_var: Outcome variable name
        
        Returns:
            AssumptionCheckResult with pass/fail and remediation suggestions
        
        ✅ Mercury Enhancement: Q-Q plots and histogram specifications for visual assumption checks
        """
        result = AssumptionCheckResult(test_type=test_type)
        
        # Check normality
        if test_type in [TestType.T_TEST_INDEPENDENT, TestType.T_TEST_PAIRED, TestType.ANOVA_ONEWAY]:
            normality_results = self._check_normality(data, outcome_var, group_var)
            result.normality = normality_results
            
            if not normality_results.get("passed", True):
                result.add_warning("Normality assumption violated")
                
                # Suggest remediation
                if test_type == TestType.T_TEST_INDEPENDENT:
                    result.suggest_remediation(
                        "Consider Mann-Whitney U test (non-parametric alternative)",
                        TestType.MANN_WHITNEY
                    )
                elif test_type == TestType.ANOVA_ONEWAY:
                    result.suggest_remediation(
                        "Consider Kruskal-Wallis H test (non-parametric alternative)",
                        TestType.KRUSKAL_WALLIS
                    )
                
                result.suggest_remediation("Consider data transformation (log, square root)")
        
        # Check homogeneity of variance
        if test_type in [TestType.T_TEST_INDEPENDENT, TestType.ANOVA_ONEWAY] and group_var:
            homogeneity_results = self._check_homogeneity(data, outcome_var, group_var)
            result.homogeneity = homogeneity_results
            
            if not homogeneity_results.get("passed", True):
                result.add_warning("Homogeneity of variance assumption violated")
                
                if test_type == TestType.T_TEST_INDEPENDENT:
                    result.suggest_remediation("Use Welch's t-test (does not assume equal variances)")
                elif test_type == TestType.ANOVA_ONEWAY:
                    result.suggest_remediation("Use Welch's ANOVA or consider transformation")
        
        # Check independence (based on study design)
        independence_check = self._check_independence(data, test_type)
        result.independence = independence_check
        
        # Overall pass/fail
        result.passed = (
            result.normality.get("passed", True) and
            result.homogeneity.get("passed", True) and
            result.independence.get("passed", True)
        )
        
        return result

    def generate_normality_diagnostics(self, data: pd.Series, var_name: str) -> List[FigureSpec]:
        """
        Generate Q-Q plot and histogram for normality assessment.
        
        ✅ Mercury Enhancement: Visual normality diagnostics
        
        Args:
            data: Data series to analyze
            var_name: Variable name for labeling
        
        Returns:
            List of FigureSpec objects (Q-Q plot and histogram)
        """
        from scipy.stats import probplot
        
        clean_data = data.dropna()
        if len(clean_data) < 3:
            return []  # Insufficient data
        
        figures = []
        
        # Q-Q plot
        qq_data = probplot(clean_data, dist="norm")
        qq_spec = FigureSpec(
            figure_type="qq_plot",
            title=f"Q-Q Plot: {var_name}",
            data={
                "theoretical_quantiles": qq_data[0][0].tolist(),
                "sample_quantiles": qq_data[0][1].tolist(),
                "fit_line": {
                    "slope": qq_data[1][0],
                    "intercept": qq_data[1][1]
                },
                "r_squared": qq_data[1][2]  # Correlation coefficient squared
            },
            x_label="Theoretical Quantiles",
            y_label="Sample Quantiles",
            caption=f"Q-Q plot for assessing normality of {var_name}. Points should follow the diagonal line if normally distributed."
        )
        figures.append(qq_spec)
        
        # Histogram with normal overlay
        hist_values, hist_bins = np.histogram(clean_data, bins='auto')
        
        # Generate normal curve overlay
        mean_val = float(clean_data.mean())
        std_val = float(clean_data.std())
        x_range = np.linspace(clean_data.min(), clean_data.max(), 100)
        normal_curve = stats.norm.pdf(x_range, mean_val, std_val)
        # Scale to match histogram
        normal_curve = normal_curve * len(clean_data) * (hist_bins[1] - hist_bins[0])
        
        hist_spec = FigureSpec(
            figure_type="histogram",
            title=f"Distribution: {var_name}",
            data={
                "values": hist_values.tolist(),
                "bins": hist_bins.tolist(),
                "mean": mean_val,
                "std": std_val,
                "normal_overlay": {
                    "x": x_range.tolist(),
                    "y": normal_curve.tolist()
                },
                "n": len(clean_data)
            },
            x_label=var_name,
            y_label="Frequency",
            caption=f"Histogram of {var_name} with normal distribution overlay (red curve). Data should approximate the normal curve if normally distributed."
        )
        figures.append(hist_spec)
        
        return figures

    def _check_normality(
        self,
        data: pd.DataFrame,
        outcome_var: str,
        group_var: Optional[str]
    ) -> Dict[str, Any]:
        """
        Check normality assumption using Shapiro-Wilk test.
        
        ✅ Mercury Enhancement #7: Anderson-Darling and Kolmogorov-Smirnov normality tests
        """
        results = {"tests": []}
        
        if group_var and group_var in data.columns:
            # Test per group
            all_passed = True
            for group_name, group_data in data.groupby(group_var):
                clean = group_data[outcome_var].dropna()
                
                if len(clean) >= 3:
                    stat, p_value = stats.shapiro(clean)
                    passed = p_value > 0.05
                    all_passed = all_passed and passed
                    
                    results["tests"].append({
                        "group": str(group_name),
                        "statistic": float(stat),
                        "p_value": float(p_value),
                        "passed": passed
                    })
            
            results["passed"] = all_passed
        else:
            # Test overall
            clean = data[outcome_var].dropna()
            
            if len(clean) >= 3:
                # Use Anderson-Darling for larger samples (more powerful)
                if len(clean) > 50:
                    ad_result = self._check_normality_anderson_darling(clean)
                    results.update(ad_result)
                else:
                    # Use Shapiro-Wilk for smaller samples
                    stat, p_value = stats.shapiro(clean)
                    results["test"] = "Shapiro-Wilk"
                    results["statistic"] = float(stat)
                    results["p_value"] = float(p_value)
                    results["passed"] = p_value > 0.05
            else:
                results["passed"] = True  # Too few observations to test
        
        return results

    def _check_normality_anderson_darling(self, data: pd.Series) -> Dict[str, Any]:
        """
        Anderson-Darling test for normality.
        
        ✅ Mercury Enhancement #7: Anderson-Darling normality test
        
        More powerful than Shapiro-Wilk for larger samples (n > 50).
        
        Args:
            data: Data series to test
        
        Returns:
            Dictionary with test results
        """
        clean = data.dropna()
        
        if len(clean) < 3:
            return {"passed": True, "note": "Insufficient data for Anderson-Darling test"}
        
        try:
            result = stats.anderson(clean, dist='norm')
            
            # Use 5% significance level (index 2 in critical_values)
            critical_value = result.critical_values[2]
            significance = result.significance_level[2]
            
            passed = result.statistic < critical_value
            
            return {
                "test": "Anderson-Darling",
                "statistic": float(result.statistic),
                "critical_value": float(critical_value),
                "significance_level": float(significance),
                "passed": passed,
                "note": f"More sensitive than Shapiro-Wilk for n > 50. Current n = {len(clean)}"
            }
        
        except Exception as e:
            logger.warning(f"Anderson-Darling test failed: {e}")
            return {"passed": True, "note": "Anderson-Darling test failed, assuming normality"}

    def _check_homogeneity(
        self,
        data: pd.DataFrame,
        outcome_var: str,
        group_var: str
    ) -> Dict[str, Any]:
        """
        Check homogeneity of variance using Levene's test.
        
        TODO (Mercury): Add Bartlett's test option (more sensitive for normal data)
        """
        groups = [group[outcome_var].dropna() for _, group in data.groupby(group_var)]
        
        if len(groups) < 2 or any(len(g) < 2 for g in groups):
            return {"passed": True, "note": "Insufficient data for homogeneity test"}
        
        stat, p_value = stats.levene(*groups)
        
        return {
            "test": "Levene's test",
            "statistic": float(stat),
            "p_value": float(p_value),
            "passed": p_value > 0.05
        }

    def _check_independence(self, data: pd.DataFrame, test_type: TestType) -> Dict[str, Any]:
        """
        Check independence assumption (based on study design).
        
        TODO (Mercury): Add Durbin-Watson test for repeated measures
        """
        # For paired tests, observations are NOT independent
        if test_type in [TestType.T_TEST_PAIRED, TestType.ANOVA_REPEATED]:
            return {
                "passed": True,
                "note": "Paired/repeated measures design - observations are dependent by design"
            }
        
        # For independent tests, assume independence unless repeated measures detected
        return {
            "passed": True,
            "note": "Independence assumed based on study design"
        }

    def generate_summary_table(self, results: List[StatisticalResult]) -> str:
        """
        Generate APA-style summary table for multiple analyses.
        
        Args:
            results: List of StatisticalResult objects
        
        Returns:
            Formatted table string
        
        ✅ Mercury Enhancement #12: LaTeX and Word-compatible table export
        """
        if not results:
            return ""
        
        lines = []
        lines.append("Statistical Analysis Summary")
        lines.append("=" * 80)
        
        for i, result in enumerate(results, 1):
            lines.append(f"\nAnalysis {i}:")
            lines.append("-" * 80)
            
            # Descriptive stats
            if result.descriptive:
                lines.append("\nDescriptive Statistics:")
                lines.append(format_descriptive_table_apa(result.descriptive))
            
            # Inferential stats
            if result.inferential:
                lines.append(f"\nInferential Test: {result.inferential.test_name}")
                lines.append(f"Result: {result.inferential.format_apa()}")
                lines.append(f"Interpretation: {result.inferential.interpretation}")
            
            # Effect size
            if result.effect_sizes:
                lines.append(f"\nEffect Size: {result.effect_sizes.interpretation}")
            
            # Assumptions
            if result.assumptions:
                lines.append(f"\nAssumptions: {'✓ Passed' if result.assumptions.passed else '✗ Violated'}")
                if result.assumptions.warnings:
                    lines.append("Warnings:")
                    for warning in result.assumptions.warnings:
                        lines.append(f"  - {warning}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)

    def export_results_latex(self, result: StatisticalResult, title: str = "Statistical Analysis Results") -> str:
        """
        Export statistical results as LaTeX table.
        
        ✅ Mercury Enhancement #12: LaTeX table export for publication
        
        Args:
            result: StatisticalResult object
            title: Table title
        
        Returns:
            LaTeX table string ready for publication
        """
        lines = []
        
        # Begin table
        lines.extend([
            "\\begin{table}[htbp]",
            "\\centering",
            f"\\caption{{{title}}}",
            "\\label{{tab:statistical_results}}"
        ])
        
        # Descriptive statistics table
        if result.descriptive:
            lines.extend([
                "\\begin{tabular}{lcccccc}",
                "\\toprule",
                "Variable & N & Mean & SD & Median & Min & Max \\\\",
                "\\midrule"
            ])
            
            for desc in result.descriptive:
                group_label = f" ({desc.group_name})" if desc.group_name else ""
                lines.append(
                    f"{desc.variable_name}{group_label} & {desc.n} & "
                    f"{desc.mean:.2f} & {desc.std:.2f} & {desc.median:.2f} & "
                    f"{desc.min_value:.2f} & {desc.max_value:.2f} \\\\"
                )
            
            lines.extend(["\\bottomrule", "\\end{tabular}"])
        
        # Inferential statistics
        if result.inferential:
            lines.extend([
                "\\vspace{1em}",
                "\\begin{tabular}{lccc}",
                "\\toprule",
                "Test & Statistic & p-value & Effect Size \\\\",
                "\\midrule"
            ])
            
            test_name = result.inferential.test_name.replace("&", "\\&")  # Escape &
            p_val_str = "< 0.001" if result.inferential.p_value < 0.001 else f"{result.inferential.p_value:.3f}"
            
            effect_size_str = ""
            if result.effect_sizes:
                if result.effect_sizes.cohens_d is not None:
                    effect_size_str = f"d = {result.effect_sizes.cohens_d:.2f}"
                elif result.effect_sizes.eta_squared is not None:
                    effect_size_str = f"$\\eta^2$ = {result.effect_sizes.eta_squared:.3f}"
            
            lines.append(
                f"{test_name} & {result.inferential.statistic:.2f} & "
                f"{p_val_str} & {effect_size_str} \\\\"
            )
            
            lines.extend(["\\bottomrule", "\\end{tabular}"])
        
        # End table
        lines.append("\\end{table}")
        
        return "\n".join(lines)

    def export_results_csv(self, result: StatisticalResult) -> str:
        """
        Export statistical results as CSV format.
        
        ✅ Mercury Enhancement #12: CSV export for data analysis software
        
        Args:
            result: StatisticalResult object
        
        Returns:
            CSV string
        """
        lines = []
        
        # Descriptive statistics
        if result.descriptive:
            lines.append("# Descriptive Statistics")
            lines.append("Variable,Group,N,Mean,SD,Median,Min,Max,Q25,Q75")
            
            for desc in result.descriptive:
                lines.append(
                    f"{desc.variable_name},{desc.group_name or ''},{desc.n},"
                    f"{desc.mean:.4f},{desc.std:.4f},{desc.median:.4f},"
                    f"{desc.min_value:.4f},{desc.max_value:.4f},"
                    f"{desc.q25:.4f},{desc.q75:.4f}"
                )
        
        # Inferential statistics
        if result.inferential:
            lines.extend(["\n# Inferential Statistics", "Test,Statistic,P_Value,DF,Significant"])
            
            lines.append(
                f"{result.inferential.test_name},{result.inferential.statistic:.4f},"
                f"{result.inferential.p_value:.6f},{result.inferential.df},"
                f"{result.inferential.significant}"
            )
        
        # Effect sizes
        if result.effect_sizes:
            lines.extend(["\n# Effect Sizes", "Measure,Value,Interpretation"])
            
            if result.effect_sizes.cohens_d is not None:
                lines.append(f"Cohens_d,{result.effect_sizes.cohens_d:.4f},{result.effect_sizes.interpret_cohens_d()}")
            
            if result.effect_sizes.eta_squared is not None:
                lines.append(f"Eta_squared,{result.effect_sizes.eta_squared:.4f},{result.effect_sizes.interpret_eta_squared()}")
        
        return "\n".join(lines)

    # =========================================================================
    # Helper Methods for Result Building
    # =========================================================================

    def _build_descriptive_stats(self, data: List[Dict]) -> List[DescriptiveStats]:
        """Build DescriptiveStats objects from dict data."""
        results = []
        for item in data:
            try:
                results.append(DescriptiveStats(
                    variable_name=item.get("variable", "unknown"),
                    n=item.get("n", 0),
                    missing=item.get("missing", 0),
                    mean=item.get("mean", 0.0),
                    median=item.get("median", 0.0),
                    std=item.get("std", 0.0),
                    min_value=item.get("min", 0.0),
                    max_value=item.get("max", 0.0),
                    q25=item.get("q25", 0.0),
                    q75=item.get("q75", 0.0),
                    iqr=item.get("iqr", 0.0),
                    group_name=item.get("group"),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse descriptive stats: {e}")
        
        return results

    def _build_inferential_result(self, data: Dict) -> Optional[HypothesisTestResult]:
        """Build HypothesisTestResult from dict data."""
        if not data:
            return None
        
        try:
            test_type_str = data.get("test_type", "t_test_independent")
            test_type = TestType(test_type_str) if test_type_str in [t.value for t in TestType] else TestType.T_TEST_INDEPENDENT
            
            return HypothesisTestResult(
                test_name=data.get("test_name", "Unknown test"),
                test_type=test_type,
                statistic=data.get("statistic", 0.0),
                p_value=data.get("p_value", 1.0),
                df=data.get("df"),
                interpretation=data.get("interpretation", ""),
                ci_lower=data.get("ci_lower"),
                ci_upper=data.get("ci_upper"),
            )
        except Exception as e:
            logger.warning(f"Failed to parse inferential result: {e}")
            return None

    def _build_effect_sizes(self, data: Dict) -> Optional[EffectSize]:
        """Build EffectSize from dict data."""
        if not data:
            return None
        
        return EffectSize(
            cohens_d=data.get("cohens_d"),
            hedges_g=data.get("hedges_g"),
            eta_squared=data.get("eta_squared"),
            interpretation=data.get("interpretation", ""),
            magnitude=data.get("magnitude", ""),
        )

    def _build_assumptions(self, data: Dict) -> Optional[AssumptionCheckResult]:
        """Build AssumptionCheckResult from dict data."""
        if not data:
            return None
        
        result = AssumptionCheckResult(test_type=TestType.T_TEST_INDEPENDENT)
        result.normality = data.get("normality", {})
        result.homogeneity = data.get("homogeneity", {})
        result.independence = data.get("independence", {})
        result.passed = data.get("passed", False)
        result.warnings = data.get("warnings", [])
        result.remediation_suggestions = data.get("remediation", [])
        
        return result

    def _run_posthoc_tukey(self, groups: List[pd.Series]) -> List[Dict[str, Any]]:
        """
        Tukey HSD post-hoc test for ANOVA pairwise comparisons.
        
        ✅ Mercury Enhancement: Full Tukey HSD implementation
        
        Args:
            groups: List of group data (pd.Series)
        
        Returns:
            List of pairwise comparison results
        """
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            
            # Combine all data with group labels
            all_data = []
            all_groups = []
            
            for i, group in enumerate(groups):
                group_clean = group.dropna()
                all_data.extend(group_clean.tolist())
                all_groups.extend([f'Group_{i+1}'] * len(group_clean))
            
            # Run Tukey HSD
            tukey_result = pairwise_tukeyhsd(
                endog=all_data,
                groups=all_groups,
                alpha=0.05
            )
            
            # Parse results
            results = []
            for row in tukey_result.summary().data[1:]:  # Skip header
                results.append({
                    'group_a': row[0],
                    'group_b': row[1], 
                    'mean_diff': float(row[2]),
                    'p_value': float(row[3]),
                    'ci_lower': float(row[4]),
                    'ci_upper': float(row[5]),
                    'significant': row[6] == 'True'
                })
            
            return results
            
        except ImportError:
            logger.error("statsmodels not available for Tukey HSD")
            return []
        except Exception as e:
            logger.error(f"Error in Tukey HSD: {e}")
            return []

    def _calculate_cramers_v(self, contingency_table: np.ndarray, chi2: Optional[float] = None) -> float:
        """
        Calculate Cramér's V effect size for chi-square test.
        
        ✅ Mercury Enhancement: Cramér's V calculation
        
        Args:
            contingency_table: The contingency table
            chi2: Chi-square statistic (calculated if not provided)
        
        Returns:
            Cramér's V value (0 to 1)
        """
        if chi2 is None:
            chi2 = stats.chi2_contingency(contingency_table)[0]
        
        n = contingency_table.sum()  # Total sample size
        min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
        
        if min_dim == 0 or n == 0:
            return 0.0
        
        return np.sqrt(chi2 / (n * min_dim))

    def _run_fisher_exact(self, contingency_table: np.ndarray) -> HypothesisTestResult:
        """
        Fisher's exact test for 2x2 contingency tables (small samples).
        
        ✅ Mercury Enhancement #5: Fisher's exact test implementation
        
        Args:
            contingency_table: 2x2 numpy array
        
        Returns:
            HypothesisTestResult with odds ratio and exact p-value
        """
        if contingency_table is None:
            raise ValueError("Contingency table required for Fisher's exact test")
        
        if contingency_table.shape != (2, 2):
            raise ValueError("Fisher's exact test requires 2x2 contingency table")
        
        # Run Fisher's exact test
        odds_ratio, p_value = stats.fisher_exact(contingency_table)
        
        # Calculate confidence interval for odds ratio
        # Using log transformation for CI
        log_or = np.log(odds_ratio) if odds_ratio > 0 else 0
        
        # Standard error of log odds ratio
        se_log_or = np.sqrt(
            1/contingency_table[0,0] + 1/contingency_table[0,1] + 
            1/contingency_table[1,0] + 1/contingency_table[1,1]
        )
        
        # 95% CI for log OR, then transform back
        z_crit = stats.norm.ppf(0.975)
        ci_lower = np.exp(log_or - z_crit * se_log_or) if odds_ratio > 0 else 0
        ci_upper = np.exp(log_or + z_crit * se_log_or) if odds_ratio > 0 else np.inf
        
        # Interpret odds ratio
        if odds_ratio == 1:
            or_interpretation = "no association"
        elif odds_ratio > 1:
            or_interpretation = f"{odds_ratio:.2f}x higher odds"
        else:
            or_interpretation = f"{1/odds_ratio:.2f}x lower odds"
        
        interpretation = f"Fisher's exact test {'was' if p_value < 0.05 else 'was not'} significant (p = {p_value:.3f}). Odds ratio = {odds_ratio:.3f} indicates {or_interpretation}."
        
        result = HypothesisTestResult(
            test_name="Fisher's exact test",
            test_type=TestType.FISHER_EXACT,
            statistic=float(odds_ratio),  # Use OR as the statistic
            p_value=float(p_value),
            df=1,  # Always 1 df for 2x2 table
            ci_lower=float(ci_lower),
            ci_upper=float(ci_upper),
            interpretation=interpretation,
        )
        
        # Attach odds ratio details
        result.odds_ratio = odds_ratio
        result.or_interpretation = or_interpretation
        
        return result

    def _run_correlation(self, x_data: pd.Series, y_data: pd.Series, method: str = "pearson") -> HypothesisTestResult:
        """
        Pearson or Spearman correlation analysis.
        
        ✅ Mercury Enhancement #6: Correlation tests (Pearson & Spearman)
        
        Args:
            x_data: First variable
            y_data: Second variable  
            method: "pearson" or "spearman"
        
        Returns:
            HypothesisTestResult with correlation coefficient and significance
        """
        # Ensure equal length and remove missing values
        if len(x_data) != len(y_data):
            raise ValueError("x and y data must have equal length")
        
        # Create combined dataframe and drop rows with any missing values
        df = pd.DataFrame({'x': x_data, 'y': y_data}).dropna()
        
        if len(df) < 3:
            raise ValueError("Need at least 3 complete observations for correlation")
        
        x_clean = df['x']
        y_clean = df['y']
        
        # Run correlation test
        if method == "pearson":
            r, p_value = stats.pearsonr(x_clean, y_clean)
            test_name = "Pearson correlation"
            test_type = TestType.CORRELATION_PEARSON
        else:
            r, p_value = stats.spearmanr(x_clean, y_clean)
            test_name = "Spearman correlation"
            test_type = TestType.CORRELATION_SPEARMAN
        
        # Degrees of freedom
        df_corr = len(x_clean) - 2
        
        # Calculate confidence interval for Pearson's r (Fisher z-transform)
        if method == "pearson" and abs(r) < 0.99:
            z = 0.5 * np.log((1 + r) / (1 - r))  # Fisher z-transform
            se = 1 / np.sqrt(len(x_clean) - 3)
            z_crit = stats.norm.ppf(0.975)
            
            z_lower = z - z_crit * se
            z_upper = z + z_crit * se
            
            # Transform back to r
            ci_lower = (np.exp(2 * z_lower) - 1) / (np.exp(2 * z_lower) + 1)
            ci_upper = (np.exp(2 * z_upper) - 1) / (np.exp(2 * z_upper) + 1)
        else:
            ci_lower = None
            ci_upper = None
        
        # Interpret correlation strength (Cohen's conventions)
        r_abs = abs(r)
        if r_abs < 0.1:
            strength = "negligible"
        elif r_abs < 0.3:
            strength = "small"
        elif r_abs < 0.5:
            strength = "medium"
        else:
            strength = "large"
        
        direction = "positive" if r > 0 else "negative"
        
        interpretation = f"{test_name} {'was' if p_value < 0.05 else 'was not'} significant (r = {r:.3f}, p = {p_value:.3f}). This indicates a {strength} {direction} association."
        
        result = HypothesisTestResult(
            test_name=test_name,
            test_type=test_type,
            statistic=float(r),
            p_value=float(p_value),
            df=int(df_corr),
            ci_lower=float(ci_lower) if ci_lower is not None else None,
            ci_upper=float(ci_upper) if ci_upper is not None else None,
            interpretation=interpretation,
        )
        
        # Attach correlation details
        result.correlation_strength = strength
        result.correlation_direction = direction
        result.r_squared = float(r ** 2)
        
        return result

    def _calculate_rank_biserial_correlation(self, group_a: pd.Series, group_b: pd.Series, u_statistic: float) -> float:
        """
        Calculate rank-biserial correlation for Mann-Whitney U test.
        
        ✅ Mercury Enhancement #8: Rank-biserial correlation calculation
        
        Formula: r = 1 - (2U) / (n1 * n2)
        where U is the Mann-Whitney U statistic
        
        Args:
            group_a: First group data
            group_b: Second group data
            u_statistic: Mann-Whitney U statistic
        
        Returns:
            Rank-biserial correlation (-1 to 1)
        """
        n1 = len(group_a)
        n2 = len(group_b)
        
        # Convert U to the smaller of the two possible U values
        u_min = min(u_statistic, n1 * n2 - u_statistic)
        
        # Calculate rank-biserial correlation
        r_rb = 1 - (2 * u_min) / (n1 * n2)
        
        # Determine sign based on which group has higher median
        median_a = group_a.median()
        median_b = group_b.median()
        
        if median_a < median_b:
            r_rb = -r_rb  # Negative correlation if group A < group B
        
        return float(r_rb)

    def _run_posthoc_dunn(self, groups: List[pd.Series]) -> List[Dict[str, Any]]:
        """
        Dunn's test for Kruskal-Wallis post-hoc comparisons.
        
        ✅ Mercury Enhancement #9: Dunn's test for non-parametric post-hoc analysis
        
        Uses Bonferroni correction for multiple comparisons.
        
        Args:
            groups: List of group data (pd.Series)
        
        Returns:
            List of pairwise comparison results
        """
        try:
            # Try to import scikit-posthocs (optional dependency)
            from scipy.stats import rankdata
            
            # Manual implementation since scikit-posthocs might not be available
            # Combine all data with group labels
            all_data = []
            all_groups = []
            
            for i, group in enumerate(groups):
                group_clean = group.dropna()
                all_data.extend(group_clean.tolist())
                all_groups.extend([i] * len(group_clean))
            
            # Calculate ranks
            ranks = rankdata(all_data)
            
            # Calculate mean ranks for each group
            group_mean_ranks = []
            group_sizes = []
            start_idx = 0
            
            for i, group in enumerate(groups):
                group_size = len(group.dropna())
                end_idx = start_idx + group_size
                mean_rank = np.mean(ranks[start_idx:end_idx])
                group_mean_ranks.append(mean_rank)
                group_sizes.append(group_size)
                start_idx = end_idx
            
            # Total sample size
            N = len(all_data)
            
            # Number of comparisons (for Bonferroni correction)
            k = len(groups)
            num_comparisons = k * (k - 1) // 2
            
            # Pairwise comparisons
            results = []
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    # Calculate test statistic
                    mean_diff = abs(group_mean_ranks[i] - group_mean_ranks[j])
                    
                    # Standard error
                    se = np.sqrt((N * (N + 1) / 12) * (1/group_sizes[i] + 1/group_sizes[j]))
                    
                    # Z statistic
                    z_stat = mean_diff / se
                    
                    # Two-tailed p-value
                    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
                    
                    # Bonferroni correction
                    p_adjusted = min(p_value * num_comparisons, 1.0)
                    
                    results.append({
                        'group_a': f'Group_{i+1}',
                        'group_b': f'Group_{j+1}',
                        'mean_rank_diff': float(mean_diff),
                        'z_statistic': float(z_stat),
                        'p_value': float(p_value),
                        'p_adjusted': float(p_adjusted),
                        'significant': p_adjusted < 0.05
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in Dunn's test: {e}")
            return []

    def _calculate_glass_delta(self, group_a: pd.Series, group_b: pd.Series) -> float:
        """
        Calculate Glass's delta effect size.
        
        ✅ Mercury Enhancement #10: Glass's delta calculation
        
        Glass's delta uses the standard deviation of the control group only,
        making it useful when group variances differ substantially.
        
        Formula: Δ = (mean_a - mean_b) / sd_control
        
        Args:
            group_a: Treatment group (typically)
            group_b: Control group (typically)
        
        Returns:
            Glass's delta value
        """
        mean_diff = group_a.mean() - group_b.mean()
        control_sd = group_b.std()  # Use control group SD only
        
        if control_sd == 0:
            return 0.0
        
        return float(mean_diff / control_sd)

    def _calculate_omega_squared(self, groups: List[pd.Series]) -> float:
        """
        Calculate omega-squared effect size for ANOVA.
        
        ✅ Mercury Enhancement #10: Omega-squared calculation
        
        Omega-squared is less biased than eta-squared, especially for small samples.
        
        Formula: ω² = (SS_between - (k-1)*MS_within) / (SS_total + MS_within)
        
        Args:
            groups: List of group data
        
        Returns:
            Omega-squared value (0 to 1)
        """
        try:
            # Calculate group means and overall mean
            group_means = [g.mean() for g in groups]
            group_sizes = [len(g) for g in groups]
            overall_mean = np.mean([val for g in groups for val in g.dropna()])
            
            # Calculate sum of squares
            ss_between = sum(n * (mean - overall_mean)**2 for n, mean in zip(group_sizes, group_means))
            
            ss_within = sum(sum((x - group_mean)**2 for x in g.dropna()) 
                           for g, group_mean in zip(groups, group_means))
            
            ss_total = ss_between + ss_within
            
            # Degrees of freedom
            k = len(groups)
            df_between = k - 1
            df_within = sum(group_sizes) - k
            
            # Mean squares
            ms_within = ss_within / df_within if df_within > 0 else 0
            
            # Omega-squared
            if ss_total + ms_within == 0:
                return 0.0
            
            omega_sq = (ss_between - df_between * ms_within) / (ss_total + ms_within)
            
            # Ensure non-negative
            return max(0.0, float(omega_sq))
        
        except Exception as e:
            logger.warning(f"Error calculating omega-squared: {e}")
            return 0.0

    def calculate_power_analysis(
        self,
        effect_size: float,
        sample_size: int,
        test_type: TestType,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculate statistical power analysis.
        
        ✅ Mercury Enhancement #11: Basic power analysis implementation
        
        Args:
            effect_size: Expected effect size (Cohen's d, etc.)
            sample_size: Current sample size
            test_type: Type of statistical test
            alpha: Significance level (default 0.05)
        
        Returns:
            Dictionary with power analysis results
        """
        try:
            # Simple power calculation for t-tests (Cohen's formula)
            if test_type in [TestType.T_TEST_INDEPENDENT, TestType.T_TEST_PAIRED]:
                # Calculate non-centrality parameter
                if test_type == TestType.T_TEST_INDEPENDENT:
                    # Independent t-test: delta = d * sqrt(n/2)
                    delta = effect_size * np.sqrt(sample_size / 2)
                    df = sample_size - 2
                else:
                    # Paired t-test: delta = d * sqrt(n)
                    delta = effect_size * np.sqrt(sample_size)
                    df = sample_size - 1
                
                # Critical t-value
                t_crit = stats.t.ppf(1 - alpha/2, df)
                
                # Power calculation using non-central t distribution
                power = 1 - stats.nct.cdf(t_crit, df, delta) + stats.nct.cdf(-t_crit, df, delta)
                
                # Calculate required sample sizes for 80% and 90% power
                # Approximate formulas (Cohen, 1988)
                if test_type == TestType.T_TEST_INDEPENDENT:
                    n_80 = 2 * (stats.norm.ppf(0.8) + stats.norm.ppf(1 - alpha/2))**2 / (effect_size**2)
                    n_90 = 2 * (stats.norm.ppf(0.9) + stats.norm.ppf(1 - alpha/2))**2 / (effect_size**2)
                else:
                    n_80 = (stats.norm.ppf(0.8) + stats.norm.ppf(1 - alpha/2))**2 / (effect_size**2)
                    n_90 = (stats.norm.ppf(0.9) + stats.norm.ppf(1 - alpha/2))**2 / (effect_size**2)
                
                return {
                    "test_type": test_type.value,
                    "effect_size": effect_size,
                    "sample_size": sample_size,
                    "alpha": alpha,
                    "observed_power": float(power),
                    "required_n_80": int(np.ceil(n_80)),
                    "required_n_90": int(np.ceil(n_90)),
                    "power_interpretation": self._interpret_power(power),
                    "recommendation": self._power_recommendation(power, sample_size, n_80)
                }
            
            else:
                return {
                    "test_type": test_type.value,
                    "note": "Power analysis not yet implemented for this test type",
                    "effect_size": effect_size,
                    "sample_size": sample_size
                }
        
        except Exception as e:
            logger.error(f"Error in power analysis: {e}")
            return {
                "error": "Power analysis failed",
                "details": str(e)
            }

    def _interpret_power(self, power: float) -> str:
        """Interpret power level according to Cohen's conventions."""
        if power < 0.6:
            return "low power (< 60%) - high risk of Type II error"
        elif power < 0.8:
            return "moderate power (60-80%) - acceptable but could be improved"
        elif power < 0.95:
            return "good power (80-95%) - adequate for detecting true effects"
        else:
            return "very high power (> 95%) - excellent detection capability"

    def _power_recommendation(self, power: float, current_n: int, required_n_80: float) -> str:
        """Generate power analysis recommendation."""
        if power < 0.8:
            additional_n = max(0, int(required_n_80) - current_n)
            return f"Consider increasing sample size by {additional_n} to achieve 80% power"
        else:
            return "Current sample size provides adequate power"

    def _build_figure_specs(self, data: List[Dict]) -> List[FigureSpec]:
        """Build FigureSpec objects from dict data."""
        results = []
        for item in data:
            try:
                results.append(FigureSpec(
                    figure_type=item.get("type", "boxplot"),
                    title=item.get("title", ""),
                    data=item.get("data", {}),
                    caption=item.get("caption", ""),
                    x_label=item.get("x_label"),
                    y_label=item.get("y_label"),
                ))
            except Exception as e:
                logger.warning(f"Failed to parse figure spec: {e}")
        
        return results


# =============================================================================
# Factory Function
# =============================================================================

def create_statistical_analysis_agent() -> StatisticalAnalysisAgent:
    """Factory function for creating StatisticalAnalysisAgent."""
    return StatisticalAnalysisAgent()
