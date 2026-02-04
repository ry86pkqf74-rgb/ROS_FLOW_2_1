"""
Statistical Methods Knowledge Graph.

Maps study types and outcome types to recommended statistical methods with
rationale, assumptions, alternatives, reporting guidelines, and sample-size validation.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class StudyType(str, Enum):
    RCT = "RCT"
    COHORT = "COHORT"
    CASE_CONTROL = "CASE_CONTROL"
    CROSS_SECTIONAL = "CROSS_SECTIONAL"
    META_ANALYSIS = "META_ANALYSIS"
    OBSERVATIONAL = "OBSERVATIONAL"


class OutcomeType(str, Enum):
    BINARY = "BINARY"
    CONTINUOUS = "CONTINUOUS"
    TIME_TO_EVENT = "TIME_TO_EVENT"
    COUNT = "COUNT"
    ORDINAL = "ORDINAL"


@dataclass
class MethodRecommendation:
    """A single statistical method recommendation with rationale and metadata."""

    method: str
    rationale: str
    assumptions: List[str]
    alternatives: List[str]
    guidelines: List[str]  # CONSORT, STROBE, PRISMA
    confidence: float


# ---------------------------------------------------------------------------
# String normalization for API and stage (config / prior stage output)
# ---------------------------------------------------------------------------

_STUDY_TYPE_ALIASES = {
    "rct": StudyType.RCT,
    "randomized_controlled_trial": StudyType.RCT,
    "randomised_controlled_trial": StudyType.RCT,
    "cohort": StudyType.COHORT,
    "case_control": StudyType.CASE_CONTROL,
    "case-control": StudyType.CASE_CONTROL,
    "cross_sectional": StudyType.CROSS_SECTIONAL,
    "cross-sectional": StudyType.CROSS_SECTIONAL,
    "meta_analysis": StudyType.META_ANALYSIS,
    "meta-analysis": StudyType.META_ANALYSIS,
    "systematic_review": StudyType.META_ANALYSIS,
    "observational": StudyType.OBSERVATIONAL,
}

_OUTCOME_TYPE_ALIASES = {
    "binary": OutcomeType.BINARY,
    "continuous": OutcomeType.CONTINUOUS,
    "time_to_event": OutcomeType.TIME_TO_EVENT,
    "time-to-event": OutcomeType.TIME_TO_EVENT,
    "survival": OutcomeType.TIME_TO_EVENT,
    "count": OutcomeType.COUNT,
    "ordinal": OutcomeType.ORDINAL,
}


def _normalize_study_type(value: Union[str, StudyType]) -> StudyType:
    if isinstance(value, StudyType):
        return value
    key = (value or "").strip().lower().replace(" ", "_")
    return _STUDY_TYPE_ALIASES.get(key, StudyType.OBSERVATIONAL)


def _normalize_outcome_type(value: Union[str, OutcomeType]) -> OutcomeType:
    if isinstance(value, OutcomeType):
        return value
    key = (value or "").strip().lower().replace(" ", "_")
    return _OUTCOME_TYPE_ALIASES.get(key, OutcomeType.CONTINUOUS)


# ---------------------------------------------------------------------------
# Shared recommendation building blocks
# ---------------------------------------------------------------------------

def _logistic_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Logistic regression",
        rationale="Appropriate for binary outcomes; estimates odds ratios and allows adjustment for confounders.",
        assumptions=["Binary outcome", "Independence of observations", "No perfect multicollinearity", "Linearity of logit"],
        alternatives=["Chi-square test", "Fisher exact test", "Generalized linear mixed model"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.92,
    )


def _chi_square_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Chi-square test",
        rationale="Compares proportions in two or more groups; use when cell counts are sufficient (expected ≥5).",
        assumptions=["Categorical variables", "Independence", "Expected cell count ≥5"],
        alternatives=["Fisher exact test", "Logistic regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.85,
    )


def _fisher_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Fisher exact test",
        rationale="Exact test for 2×2 tables when expected counts are small.",
        assumptions=["2×2 contingency table", "Fixed marginal totals"],
        alternatives=["Chi-square test", "Logistic regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.88,
    )


def _ttest_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Independent-samples t-test",
        rationale="Compares means between two groups; assumes normality and equal variances.",
        assumptions=["Continuous outcome", "Normality (or large n)", "Homoscedasticity", "Independence"],
        alternatives=["Mann-Whitney U", "Welch t-test", "ANOVA"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.88,
    )


def _anova_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="One-way ANOVA",
        rationale="Compares means across three or more groups; extends t-test.",
        assumptions=["Continuous outcome", "Normality", "Homoscedasticity", "Independence"],
        alternatives=["Kruskal-Wallis", "Mixed-effects model", "Linear regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.87,
    )


def _linear_reg_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Linear regression",
        rationale="Models continuous outcome as a function of predictors; allows adjustment for confounders.",
        assumptions=["Continuous outcome", "Linearity", "Homoscedasticity", "Normality of residuals", "Independence"],
        alternatives=["Generalized linear model", "Mixed-effects model"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.90,
    )


def _cox_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Cox proportional hazards regression",
        rationale="Standard for time-to-event (survival) data; handles censoring.",
        assumptions=["Proportional hazards", "Independence of censoring", "No informative censoring"],
        alternatives=["Kaplan-Meier + log-rank", "Parametric survival (Weibull)", "Accelerated failure time"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.93,
    )


def _km_logrank_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Kaplan-Meier estimator and log-rank test",
        rationale="Nonparametric survival curves and comparison of survival between groups.",
        assumptions=["Independence of censoring", "Non-informative censoring"],
        alternatives=["Cox regression", "Stratified log-rank"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.88,
    )


def _poisson_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Poisson regression",
        rationale="For count outcomes; models rate or count as function of predictors.",
        assumptions=["Count outcome", "Mean = variance (or use negative binomial if overdispersion)"],
        alternatives=["Negative binomial regression", "Zero-inflated models"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.88,
    )


def _ordinal_logistic_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Ordinal logistic regression (proportional odds)",
        rationale="For ordered categorical outcomes; assumes proportional odds across categories.",
        assumptions=["Ordinal outcome", "Proportional odds", "No multicollinearity"],
        alternatives=["Mann-Whitney / Kruskal-Wallis", "Multinomial logistic regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.85,
    )


def _mann_whitney_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Mann-Whitney U test",
        rationale="Nonparametric comparison of two independent groups; does not assume normality.",
        assumptions=["Ordinal or continuous outcome", "Independence", "Same shape (for location interpretation)"],
        alternatives=["t-test", "Wilcoxon rank-sum"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.82,
    )


def _kruskal_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Kruskal-Wallis test",
        rationale="Nonparametric comparison of three or more groups.",
        assumptions=["Ordinal or continuous", "Independence", "Same shape across groups"],
        alternatives=["ANOVA", "Ordinal regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.82,
    )


def _mixed_effects_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Mixed-effects (multilevel) model",
        rationale="For clustered or repeated measures; random effects for clusters/patients.",
        assumptions=["Hierarchical structure", "Appropriate random effects specification", "Normality of random effects"],
        alternatives=["GEE", "Fixed-effects regression"],
        guidelines=["CONSORT", "STROBE"],
        confidence=0.88,
    )


def _meta_fixed_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Fixed-effects meta-analysis",
        rationale="Pool effect sizes assuming a single true effect; inverse-variance weighting.",
        assumptions=["Homogeneity of effects", "No substantial between-study heterogeneity"],
        alternatives=["Random-effects meta-analysis", "Meta-regression"],
        guidelines=["PRISMA"],
        confidence=0.90,
    )


def _meta_random_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Random-effects meta-analysis",
        rationale="Pool effect sizes allowing between-study heterogeneity; DerSimonian-Laird or REML.",
        assumptions=["Studies are exchangeable", "Heterogeneity is estimable"],
        alternatives=["Fixed-effects meta-analysis", "Meta-regression", "Subgroup analysis"],
        guidelines=["PRISMA"],
        confidence=0.91,
    )


def _forest_plot_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Forest plot and pooled estimate",
        rationale="Visual and numeric summary of study-level effects and overall estimate.",
        assumptions=["Same effect measure across studies", "Appropriate choice of model (fixed vs random)"],
        alternatives=["Funnel plot (bias)", "Meta-regression"],
        guidelines=["PRISMA"],
        confidence=0.89,
    )


def _gee_rec() -> MethodRecommendation:
    return MethodRecommendation(
        method="Generalized estimating equations (GEE)",
        rationale="Population-averaged effects for clustered/longitudinal data; robust to correlation structure.",
        assumptions=["Correct specification of working correlation", "Large number of clusters"],
        alternatives=["Mixed-effects model", "Fixed effects"],
        guidelines=["STROBE"],
        confidence=0.85,
    )


# ---------------------------------------------------------------------------
# STUDY_METHOD_MAP: (StudyType, OutcomeType) -> List[MethodRecommendation]
# ---------------------------------------------------------------------------

def _negative_binomial_placeholder() -> MethodRecommendation:
    return MethodRecommendation(
        method="Negative binomial regression",
        rationale="For overdispersed count outcomes when Poisson assumption (mean=variance) is violated.",
        assumptions=["Count outcome", "Overdispersion allowed"],
        alternatives=["Poisson regression", "Zero-inflated models"],
        guidelines=["STROBE"],
        confidence=0.85,
    )


def _build_study_method_map() -> Dict[Tuple[StudyType, OutcomeType], List[MethodRecommendation]]:
    m: Dict[Tuple[StudyType, OutcomeType], List[MethodRecommendation]] = {}

    # RCT + BINARY
    m[(StudyType.RCT, OutcomeType.BINARY)] = [
        _logistic_rec(),
        _chi_square_rec(),
        _fisher_rec(),
    ]

    # RCT + CONTINUOUS
    m[(StudyType.RCT, OutcomeType.CONTINUOUS)] = [
        _ttest_rec(),
        _anova_rec(),
        _linear_reg_rec(),
    ]

    # RCT + TIME_TO_EVENT
    m[(StudyType.RCT, OutcomeType.TIME_TO_EVENT)] = [
        _cox_rec(),
        _km_logrank_rec(),
    ]

    # RCT + COUNT
    m[(StudyType.RCT, OutcomeType.COUNT)] = [
        _poisson_rec(),
        _linear_reg_rec(),
    ]

    # RCT + ORDINAL
    m[(StudyType.RCT, OutcomeType.ORDINAL)] = [
        _ordinal_logistic_rec(),
        _mann_whitney_rec(),
        _kruskal_rec(),
    ]

    # COHORT + BINARY
    m[(StudyType.COHORT, OutcomeType.BINARY)] = [
        _logistic_rec(),
        _chi_square_rec(),
        _gee_rec(),
    ]

    # COHORT + CONTINUOUS
    m[(StudyType.COHORT, OutcomeType.CONTINUOUS)] = [
        _linear_reg_rec(),
        _ttest_rec(),
        _mixed_effects_rec(),
    ]

    # COHORT + TIME_TO_EVENT
    m[(StudyType.COHORT, OutcomeType.TIME_TO_EVENT)] = [
        _cox_rec(),
        _km_logrank_rec(),
    ]

    # COHORT + COUNT
    m[(StudyType.COHORT, OutcomeType.COUNT)] = [
        _poisson_rec(),
        _negative_binomial_placeholder(),
    ]

    # COHORT + ORDINAL
    m[(StudyType.COHORT, OutcomeType.ORDINAL)] = [
        _ordinal_logistic_rec(),
        _kruskal_rec(),
    ]

    # CASE_CONTROL + BINARY
    m[(StudyType.CASE_CONTROL, OutcomeType.BINARY)] = [
        _logistic_rec(),
        _chi_square_rec(),
        _fisher_rec(),
    ]

    # CASE_CONTROL + CONTINUOUS (e.g. continuous exposure)
    m[(StudyType.CASE_CONTROL, OutcomeType.CONTINUOUS)] = [
        _linear_reg_rec(),
        _ttest_rec(),
    ]

    # CASE_CONTROL + TIME_TO_EVENT (rare)
    m[(StudyType.CASE_CONTROL, OutcomeType.TIME_TO_EVENT)] = [
        _cox_rec(),
        _km_logrank_rec(),
    ]

    # CASE_CONTROL + COUNT
    m[(StudyType.CASE_CONTROL, OutcomeType.COUNT)] = [
        _poisson_rec(),
    ]

    # CASE_CONTROL + ORDINAL
    m[(StudyType.CASE_CONTROL, OutcomeType.ORDINAL)] = [
        _ordinal_logistic_rec(),
        _mann_whitney_rec(),
    ]

    # CROSS_SECTIONAL + BINARY
    m[(StudyType.CROSS_SECTIONAL, OutcomeType.BINARY)] = [
        _logistic_rec(),
        _chi_square_rec(),
    ]

    # CROSS_SECTIONAL + CONTINUOUS
    m[(StudyType.CROSS_SECTIONAL, OutcomeType.CONTINUOUS)] = [
        _linear_reg_rec(),
        _ttest_rec(),
        _anova_rec(),
    ]

    # CROSS_SECTIONAL + TIME_TO_EVENT (rare in cross-sectional)
    m[(StudyType.CROSS_SECTIONAL, OutcomeType.TIME_TO_EVENT)] = [
        _cox_rec(),
        _km_logrank_rec(),
    ]

    # CROSS_SECTIONAL + COUNT
    m[(StudyType.CROSS_SECTIONAL, OutcomeType.COUNT)] = [
        _poisson_rec(),
    ]

    # CROSS_SECTIONAL + ORDINAL
    m[(StudyType.CROSS_SECTIONAL, OutcomeType.ORDINAL)] = [
        _ordinal_logistic_rec(),
        _kruskal_rec(),
    ]

    # META_ANALYSIS: outcome type often reflects the pooled effect (e.g. binary = OR, continuous = MD)
    m[(StudyType.META_ANALYSIS, OutcomeType.BINARY)] = [
        _meta_random_rec(),
        _meta_fixed_rec(),
        _forest_plot_rec(),
    ]
    m[(StudyType.META_ANALYSIS, OutcomeType.CONTINUOUS)] = [
        _meta_random_rec(),
        _meta_fixed_rec(),
        _forest_plot_rec(),
    ]
    m[(StudyType.META_ANALYSIS, OutcomeType.TIME_TO_EVENT)] = [
        _meta_random_rec(),
        _meta_fixed_rec(),
        _forest_plot_rec(),
    ]
    m[(StudyType.META_ANALYSIS, OutcomeType.COUNT)] = [
        _meta_random_rec(),
        _meta_fixed_rec(),
        _forest_plot_rec(),
    ]
    m[(StudyType.META_ANALYSIS, OutcomeType.ORDINAL)] = [
        _meta_random_rec(),
        _meta_fixed_rec(),
        _forest_plot_rec(),
    ]

    # OBSERVATIONAL + all outcome types
    m[(StudyType.OBSERVATIONAL, OutcomeType.BINARY)] = [
        _logistic_rec(),
        _chi_square_rec(),
        _gee_rec(),
    ]
    m[(StudyType.OBSERVATIONAL, OutcomeType.CONTINUOUS)] = [
        _linear_reg_rec(),
        _ttest_rec(),
        _anova_rec(),
        _mixed_effects_rec(),
    ]
    m[(StudyType.OBSERVATIONAL, OutcomeType.TIME_TO_EVENT)] = [
        _cox_rec(),
        _km_logrank_rec(),
    ]
    m[(StudyType.OBSERVATIONAL, OutcomeType.COUNT)] = [
        _poisson_rec(),
    ]
    m[(StudyType.OBSERVATIONAL, OutcomeType.ORDINAL)] = [
        _ordinal_logistic_rec(),
        _kruskal_rec(),
    ]

    return m


# ---------------------------------------------------------------------------
# Assumption tests by method (canonical method names, lowercase)
# ---------------------------------------------------------------------------

_ASSUMPTION_TESTS: Dict[str, List[Dict[str, Any]]] = {
    "logistic regression": [
        {"test": "Hosmer-Lemeshow", "purpose": "Goodness of fit", "threshold": "p > 0.05", "interpretation": "Good fit"},
        {"test": "VIF", "purpose": "Multicollinearity", "threshold": "VIF < 5", "interpretation": "No concerning multicollinearity"},
        {"test": "Deviance residuals", "purpose": "Outliers", "threshold": "|residual| < 3", "interpretation": "No influential outliers"},
    ],
    "chi-square test": [
        {"test": "Expected cell count", "purpose": "Validity", "threshold": "All expected ≥ 5", "interpretation": "Use Fisher if not met"},
    ],
    "fisher exact test": [
        {"test": "Table margins", "purpose": "Fixed margins", "threshold": "N/A", "interpretation": "Exact conditional test"},
    ],
    "independent-samples t-test": [
        {"test": "Shapiro-Wilk", "purpose": "Normality", "threshold": "p > 0.05", "interpretation": "Normality plausible"},
        {"test": "Levene", "purpose": "Homoscedasticity", "threshold": "p > 0.05", "interpretation": "Equal variances"},
    ],
    "one-way anova": [
        {"test": "Shapiro-Wilk (residuals)", "purpose": "Normality", "threshold": "p > 0.05", "interpretation": "Normality plausible"},
        {"test": "Levene", "purpose": "Homoscedasticity", "threshold": "p > 0.05", "interpretation": "Equal variances"},
        {"test": "Brown-Forsythe", "purpose": "Homoscedasticity (robust)", "threshold": "p > 0.05", "interpretation": "Equal variances"},
    ],
    "linear regression": [
        {"test": "Shapiro-Wilk (residuals)", "purpose": "Normality", "threshold": "p > 0.05", "interpretation": "Normality of residuals"},
        {"test": "Breusch-Pagan", "purpose": "Homoscedasticity", "threshold": "p > 0.05", "interpretation": "Constant variance"},
        {"test": "VIF", "purpose": "Multicollinearity", "threshold": "VIF < 5", "interpretation": "No multicollinearity"},
        {"test": "Durbin-Watson", "purpose": "Autocorrelation", "threshold": "1.5 < DW < 2.5", "interpretation": "No autocorrelation"},
    ],
    "cox proportional hazards regression": [
        {"test": "Schoenfeld residuals", "purpose": "Proportional hazards", "threshold": "p > 0.05 (global)", "interpretation": "PH assumption holds"},
        {"test": "Log-log survival plot", "purpose": "Proportional hazards (visual)", "threshold": "Parallel lines", "interpretation": "PH plausible"},
    ],
    "kaplan-meier estimator and log-rank test": [
        {"test": "Censoring independence", "purpose": "Non-informative censoring", "threshold": "N/A", "interpretation": "Assess clinically"},
    ],
    "poisson regression": [
        {"test": "Dispersion", "purpose": "Overdispersion", "threshold": "Dispersion ≈ 1", "interpretation": "Use negative binomial if > 1"},
    ],
    "ordinal logistic regression (proportional odds)": [
        {"test": "Brant test", "purpose": "Proportional odds", "threshold": "p > 0.05", "interpretation": "Proportional odds holds"},
    ],
    "mann-whitney u test": [
        {"test": "Distribution shape", "purpose": "Interpretation (location)", "threshold": "Similar shape", "interpretation": "Otherwise interpret as dominance"},
    ],
    "kruskal-wallis test": [
        {"test": "Distribution shape", "purpose": "Interpretation", "threshold": "Similar shape", "interpretation": "Post-hoc pairwise if significant"},
    ],
    "mixed-effects (multilevel) model": [
        {"test": "Normality of random effects", "purpose": "Random effects", "threshold": "QQ plot", "interpretation": "Approximate normality"},
        {"test": "ICC", "purpose": "Clustering", "threshold": "Report ICC", "interpretation": "Substantial clustering"},
    ],
    "fixed-effects meta-analysis": [
        {"test": "Cochran Q", "purpose": "Heterogeneity", "threshold": "p > 0.10", "interpretation": "Homogeneity plausible"},
        {"test": "I²", "purpose": "Heterogeneity", "threshold": "I² < 25%", "interpretation": "Low heterogeneity"},
    ],
    "random-effects meta-analysis": [
        {"test": "Cochran Q", "purpose": "Heterogeneity", "threshold": "Report Q, p", "interpretation": "Between-study variance"},
        {"test": "I²", "purpose": "Heterogeneity", "threshold": "Report I²", "interpretation": "Proportion of variance"},
    ],
    "forest plot and pooled estimate": [
        {"test": "Funnel plot", "purpose": "Publication bias", "threshold": "Visual symmetry", "interpretation": "Egger test if needed"},
    ],
    "generalized estimating equations (gee)": [
        {"test": "Working correlation", "purpose": "Specification", "threshold": "QIC comparison", "interpretation": "Choose structure"},
    ],
    "negative binomial regression": [
        {"test": "Dispersion", "purpose": "Overdispersion", "threshold": "α > 0", "interpretation": "Overdispersion present"},
    ],
}


# ---------------------------------------------------------------------------
# Sample size rules (min n or warnings)
# ---------------------------------------------------------------------------

_SAMPLE_SIZE_RULES: Dict[str, Dict[str, Any]] = {
    "logistic regression": {"min_n": 50, "events_per_var": 10, "message": "At least 10 events per predictor; min n ≈ 50"},
    "chi-square test": {"min_cell": 5, "message": "Expected count in each cell ≥ 5; otherwise use Fisher exact"},
    "fisher exact test": {"message": "No minimum n; use when expected counts are small"},
    "independent-samples t-test": {"min_n_per_group": 30, "message": "n ≥ 30 per group for robustness to non-normality"},
    "one-way anova": {"min_n_per_group": 20, "message": "At least 20 per group for robustness"},
    "linear regression": {"min_n": 50, "observations_per_var": 10, "message": "At least 10 observations per predictor"},
    "cox proportional hazards regression": {"events_per_var": 10, "message": "At least 10 events per predictor"},
    "kaplan-meier estimator and log-rank test": {"min_events": 5, "message": "Reasonable number of events per group"},
    "poisson regression": {"min_n": 30, "message": "Larger n preferred for stability"},
    "ordinal logistic regression (proportional odds)": {"min_n": 100, "message": "Larger samples for stable estimates"},
    "mann-whitney u test": {"min_n_per_group": 5, "message": "Exact p available for small n"},
    "kruskal-wallis test": {"min_n_per_group": 5, "message": "Exact p available for small n"},
    "mixed-effects (multilevel) model": {"min_clusters": 5, "message": "At least 5 clusters for random effects"},
    "fixed-effects meta-analysis": {"min_studies": 2, "message": "At least 2 studies"},
    "random-effects meta-analysis": {"min_studies": 2, "message": "At least 2 studies"},
    "generalized estimating equations (gee)": {"min_clusters": 10, "message": "At least 10 clusters for robust SE"},
    "negative binomial regression": {"min_n": 30, "message": "Larger n for dispersion estimation"},
}


class StatisticalKnowledgeGraph:
    """Knowledge graph mapping study type and outcome type to statistical method recommendations."""

    STUDY_METHOD_MAP: Dict[Tuple[StudyType, OutcomeType], List[MethodRecommendation]] = _build_study_method_map()

    def recommend_methods(
        self,
        study_type: Union[str, StudyType],
        outcome_type: Union[str, OutcomeType],
        sample_size: Optional[int] = None,
        has_confounders: bool = False,
        is_clustered: bool = False,
    ) -> List[MethodRecommendation]:
        """
        Return method recommendations for the given study/outcome type, optionally
        filtered or ranked by sample size, confounders, and clustering.
        """
        st = _normalize_study_type(study_type)
        ot = _normalize_outcome_type(outcome_type)
        key = (st, ot)
        recs = list(self.STUDY_METHOD_MAP.get(key, []))

        # If confounders: prefer regression/adjustment methods
        if has_confounders and recs:
            adjustment_preferred = {"logistic regression", "linear regression", "cox proportional hazards regression", "ordinal logistic regression (proportional odds)", "poisson regression", "negative binomial regression", "generalized estimating equations (gee)", "mixed-effects (multilevel) model"}
            recs = sorted(recs, key=lambda r: (r.method.lower() not in adjustment_preferred, -r.confidence))

        # If clustered: prefer mixed effects or GEE
        if is_clustered and recs:
            cluster_preferred = {"mixed-effects (multilevel) model", "generalized estimating equations (gee)"}
            recs = sorted(recs, key=lambda r: (r.method.lower() not in cluster_preferred, -r.confidence))

        return recs

    def explain_recommendation(self, method: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Return a natural-language explanation for why and how to use the given method.
        """
        context = context or {}
        study = context.get("study_type", "the study")
        outcome = context.get("outcome_type", "the outcome")
        method_lower = (method or "").strip().lower()

        # Find a matching recommendation to get rationale
        for key, recs in self.STUDY_METHOD_MAP.items():
            for r in recs:
                if r.method.lower() == method_lower:
                    parts = [
                        f"{r.method} is recommended because {r.rationale}",
                        f"Key assumptions: {', '.join(r.assumptions)}.",
                    ]
                    if r.alternatives:
                        parts.append(f"Alternatives include: {', '.join(r.alternatives)}.")
                    if r.guidelines:
                        parts.append(f"Reporting guidelines: {', '.join(r.guidelines)}.")
                    return " ".join(parts)

        return f"{method} is a statistical method. Check the knowledge graph for study-type and outcome-type specific rationale and assumptions."

    def get_assumption_tests(self, method: str) -> List[Dict[str, Any]]:
        """Return list of assumption tests (name, purpose, threshold, interpretation) for the method."""
        method_lower = (method or "").strip().lower()
        for canonical, tests in _ASSUMPTION_TESTS.items():
            if canonical in method_lower or method_lower in canonical:
                return list(tests)
        # Try exact match
        return _ASSUMPTION_TESTS.get(method_lower, [])

    def validate_sample_size(self, method: str, n: Optional[int]) -> Tuple[bool, List[str]]:
        """
        Return (valid, list of warning messages). If n is None, return (True, []).
        """
        if n is None:
            return True, []
        warnings: List[str] = []
        method_lower = (method or "").strip().lower()
        rules = None
        for canonical, r in _SAMPLE_SIZE_RULES.items():
            if canonical in method_lower or method_lower in canonical:
                rules = r
                break
        if not rules:
            return True, []
        msg = rules.get("message", "")
        if "min_n" in rules and n < rules["min_n"]:
            warnings.append(f"Sample size n={n} is below suggested minimum {rules['min_n']} for {method}. {msg}")
        if "min_n_per_group" in rules:
            # Assume two groups for simplicity
            per_group = n // 2
            if per_group < rules["min_n_per_group"]:
                warnings.append(f"Per-group n may be below {rules['min_n_per_group']} for {method}. {msg}")
        if "min_clusters" in rules and "min_clusters" in rules:
            # We don't have cluster count here; mention in message
            warnings.append(f"For {method}, ensure at least {rules.get('min_clusters')} clusters. {msg}")
        valid = len(warnings) == 0
        return valid, warnings
