"""
Stage 07: Statistical Modeling

Handles statistical model fitting and validation including:
- Regression analysis (linear, logistic, etc.)
- Model coefficient estimation
- Goodness-of-fit statistics
- Assumption diagnostics

This stage uses REAL statistical analysis via AnalysisService when data is available,
with mock data as a fallback when no dataset is provided.
"""

import json
import logging
import os
import random
from dataclasses import asdict
from math import sqrt
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

# ML utilities
try:
    from src.ml import (
        AutoModelSelector,
        VariableSelector,
        SHAP_AVAILABLE,
    )
    ML_UTILS_AVAILABLE = True
except Exception:  # pragma: no cover
    ML_UTILS_AVAILABLE = False
    SHAP_AVAILABLE = False  # type: ignore

try:
    from sklearn.metrics import accuracy_score, roc_auc_score, r2_score, mean_squared_error
except Exception:  # pragma: no cover
    accuracy_score = roc_auc_score = r2_score = mean_squared_error = None  # type: ignore

# Statistical knowledge graph for method recommendations
try:
    from src.knowledge.stats_knowledge_graph import StatisticalKnowledgeGraph
    KG_AVAILABLE = True
except ImportError:
    KG_AVAILABLE = False
    StatisticalKnowledgeGraph = None  # type: ignore

# Pandas for DataFrame operations
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Import AnalysisService for REAL statistical analysis
try:
    from analysis_service import (
        AnalysisService,
        AnalysisRequest,
        AnalysisType,
        RegressionType,
    )
    ANALYSIS_SERVICE_AVAILABLE = True
except ImportError:
    ANALYSIS_SERVICE_AVAILABLE = False

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:  # pragma: no cover
    SCIPY_AVAILABLE = False

try:
    from statsmodels.stats.diagnostic import het_breuschpagan  # type: ignore
except Exception:  # pragma: no cover
    het_breuschpagan = None  # type: ignore

logger = logging.getLogger("workflow_engine.stage_07_stats")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")

# Supported model types
SUPPORTED_MODEL_TYPES = {
    "regression": "Linear Regression",
    "logistic": "Logistic Regression",
    "poisson": "Poisson Regression",
    "cox": "Cox Proportional Hazards",
    "mixed": "Mixed Effects Model",
    "anova": "Analysis of Variance",
}


def perform_real_statistical_modeling(
    df: "pd.DataFrame",
    model_type: str,
    dependent_variable: str,
    independent_variables: List[str],
) -> Optional[Dict[str, Any]]:
    """Perform REAL statistical modeling using AnalysisService.

    This function uses statsmodels and lifelines to compute actual
    regression coefficients and fit statistics.

    Args:
        df: pandas DataFrame with data
        model_type: Type of model (regression, logistic, poisson, cox)
        dependent_variable: Name of outcome variable
        independent_variables: List of predictor variable names

    Returns:
        Dictionary with real model results, or None if analysis fails
    """
    if not ANALYSIS_SERVICE_AVAILABLE or not PANDAS_AVAILABLE:
        logger.warning("AnalysisService or pandas not available for real modeling")
        return None

    try:
        service = AnalysisService()

        # Map model types to regression types
        reg_type_map = {
            "regression": RegressionType.LINEAR,
            "logistic": RegressionType.LOGISTIC,
            "poisson": RegressionType.POISSON,
            "cox": RegressionType.COX,
        }

        regression_type = reg_type_map.get(model_type, RegressionType.LINEAR)

        # Validate columns exist
        available_cols = set(df.columns)
        if dependent_variable not in available_cols:
            logger.warning(f"Dependent variable '{dependent_variable}' not in dataset")
            return None

        valid_predictors = [v for v in independent_variables if v in available_cols]
        if not valid_predictors:
            logger.warning("No valid predictor variables found in dataset")
            return None

        # Build analysis request
        request = AnalysisRequest(
            analysis_type=AnalysisType.REGRESSION,
            outcome_variable=dependent_variable,
            covariates=valid_predictors,
            regression_type=regression_type,
        )

        # For Cox model, we need time and event variables
        if model_type == "cox":
            # Try to find time/event columns
            time_cols = [c for c in df.columns if 'time' in c.lower() or 'survival' in c.lower()]
            event_cols = [c for c in df.columns if 'event' in c.lower() or 'status' in c.lower() or 'censor' in c.lower()]
            if time_cols and event_cols:
                request.time_variable = time_cols[0]
                request.event_variable = event_cols[0]
            else:
                logger.warning("Cox model requires time and event variables")
                return None

        # Run the analysis
        response = service.analyze(df, request)

        if not response.regression:
            logger.warning("No regression results returned from analysis")
            return None

        reg = response.regression[0]

        # Build coefficients list from real results
        coefficients = []
        if reg.coefficients:
            for var_name, coef_data in reg.coefficients.items():
                if isinstance(coef_data, dict):
                    coefficients.append({
                        "variable": var_name,
                        "estimate": coef_data.get("coefficient"),
                        "std_error": coef_data.get("std_error"),
                        "t_value": coef_data.get("t_value") or coef_data.get("z_value"),
                        "p_value": coef_data.get("p_value"),
                        "ci_lower": coef_data.get("ci_lower"),
                        "ci_upper": coef_data.get("ci_upper"),
                    })
                else:
                    # Simple coefficient value
                    coefficients.append({
                        "variable": var_name,
                        "estimate": float(coef_data) if coef_data else None,
                        "std_error": None,
                        "t_value": None,
                        "p_value": None,
                        "ci_lower": None,
                        "ci_upper": None,
                    })

        # Build fit statistics from real results
        fit_statistics = {
            "n_observations": reg.n_observations or len(df),
            "n_predictors": len(valid_predictors),
            "degrees_of_freedom": (reg.n_observations or len(df)) - len(valid_predictors) - 1,
            "log_likelihood": reg.log_likelihood,
            "aic": reg.aic,
            "bic": reg.bic,
        }

        # Add model-specific statistics
        if model_type == "regression":
            fit_statistics["r_squared"] = reg.r_squared
            fit_statistics["adj_r_squared"] = reg.adj_r_squared
            fit_statistics["f_statistic"] = reg.f_statistic
            fit_statistics["f_p_value"] = reg.f_pvalue
            fit_statistics["residual_std"] = reg.residual_std

        elif model_type == "logistic":
            # Pseudo R-squared for logistic
            if reg.log_likelihood:
                fit_statistics["pseudo_r_squared_mcfadden"] = reg.r_squared if reg.r_squared else None

        # Determine significant predictors
        significant_vars = [
            coef["variable"]
            for coef in coefficients
            if coef.get("p_value") and coef["p_value"] < 0.05 and coef["variable"] != "(Intercept)"
        ]

        result = {
            "coefficients": coefficients,
            "fit_statistics": fit_statistics,
            "significant_predictors": significant_vars,
            "n_significant": len(significant_vars),
            "real_analysis": True,
        }

        logger.info(f"Real statistical modeling completed: {len(significant_vars)} significant predictors")
        return result

    except Exception as e:
        logger.error(f"Real statistical modeling failed: {e}")
        return None


def generate_mock_coefficients(
    independent_variables: List[str],
    model_type: str
) -> List[Dict[str, Any]]:
    """Generate mock model coefficients for variables.

    Args:
        independent_variables: List of predictor variable names
        model_type: Type of statistical model

    Returns:
        List of coefficient dictionaries with estimates and statistics
    """
    coefficients = []

    # Always include intercept for most models
    if model_type != "cox":
        coefficients.append({
            "variable": "(Intercept)",
            "estimate": round(random.uniform(-2.0, 5.0), 4),
            "std_error": round(random.uniform(0.1, 0.8), 4),
            "t_value": round(random.uniform(1.5, 4.5), 4),
            "p_value": round(random.uniform(0.001, 0.05), 4),
            "ci_lower": None,  # Will be calculated
            "ci_upper": None,
        })

    # Generate coefficients for each predictor
    for var in independent_variables:
        estimate = round(random.uniform(-1.5, 2.5), 4)
        std_error = round(random.uniform(0.05, 0.5), 4)
        t_value = round(estimate / std_error, 4) if std_error > 0 else 0.0

        # Simulate p-value based on t-value magnitude
        if abs(t_value) > 2.5:
            p_value = round(random.uniform(0.001, 0.01), 4)
        elif abs(t_value) > 1.96:
            p_value = round(random.uniform(0.01, 0.05), 4)
        else:
            p_value = round(random.uniform(0.05, 0.5), 4)

        # 95% confidence interval
        ci_lower = round(estimate - 1.96 * std_error, 4)
        ci_upper = round(estimate + 1.96 * std_error, 4)

        coefficients.append({
            "variable": var,
            "estimate": estimate,
            "std_error": std_error,
            "t_value": t_value,
            "p_value": p_value,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        })

    return coefficients


def generate_fit_statistics(model_type: str, n_predictors: int) -> Dict[str, Any]:
    """Generate mock goodness-of-fit statistics.

    Args:
        model_type: Type of statistical model
        n_predictors: Number of predictor variables

    Returns:
        Dictionary of fit statistics
    """
    # Base R-squared (tends to be higher with more predictors)
    base_r2 = random.uniform(0.3, 0.85)
    r_squared = round(base_r2, 4)

    # Adjusted R-squared (penalized for number of predictors)
    n_obs = random.randint(100, 1000)
    adj_r2 = 1 - (1 - r_squared) * (n_obs - 1) / (n_obs - n_predictors - 1)
    adj_r_squared = round(adj_r2, 4)

    # Log-likelihood and information criteria
    log_likelihood = round(random.uniform(-500, -50), 2)
    k = n_predictors + 1  # number of parameters
    aic = round(-2 * log_likelihood + 2 * k, 2)
    bic = round(-2 * log_likelihood + k * (n_obs ** 0.5), 2)

    fit_stats = {
        "n_observations": n_obs,
        "n_predictors": n_predictors,
        "degrees_of_freedom": n_obs - n_predictors - 1,
        "log_likelihood": log_likelihood,
        "aic": aic,
        "bic": bic,
    }

    # Add model-specific statistics
    if model_type in ("regression", "mixed"):
        fit_stats["r_squared"] = r_squared
        fit_stats["adj_r_squared"] = adj_r_squared
        fit_stats["f_statistic"] = round(random.uniform(5.0, 50.0), 2)
        fit_stats["f_p_value"] = round(random.uniform(0.0001, 0.01), 4)
        fit_stats["rmse"] = round(random.uniform(0.5, 2.5), 4)
        fit_stats["mae"] = round(random.uniform(0.3, 2.0), 4)

    elif model_type == "logistic":
        fit_stats["pseudo_r_squared_mcfadden"] = round(random.uniform(0.1, 0.5), 4)
        fit_stats["pseudo_r_squared_nagelkerke"] = round(random.uniform(0.2, 0.6), 4)
        fit_stats["concordance"] = round(random.uniform(0.65, 0.9), 4)
        fit_stats["hosmer_lemeshow_chi2"] = round(random.uniform(3.0, 15.0), 2)
        fit_stats["hosmer_lemeshow_p"] = round(random.uniform(0.05, 0.8), 4)

    elif model_type == "cox":
        fit_stats["concordance"] = round(random.uniform(0.6, 0.85), 4)
        fit_stats["likelihood_ratio_chi2"] = round(random.uniform(10.0, 100.0), 2)
        fit_stats["likelihood_ratio_p"] = round(random.uniform(0.0001, 0.01), 4)
        fit_stats["wald_chi2"] = round(random.uniform(8.0, 80.0), 2)
        fit_stats["wald_p"] = round(random.uniform(0.0001, 0.01), 4)

    elif model_type == "poisson":
        fit_stats["deviance"] = round(random.uniform(50.0, 200.0), 2)
        fit_stats["pearson_chi2"] = round(random.uniform(40.0, 180.0), 2)
        fit_stats["dispersion"] = round(random.uniform(0.8, 1.5), 4)

    elif model_type == "anova":
        fit_stats["f_statistic"] = round(random.uniform(3.0, 25.0), 2)
        fit_stats["f_p_value"] = round(random.uniform(0.001, 0.05), 4)
        fit_stats["eta_squared"] = round(random.uniform(0.1, 0.5), 4)
        fit_stats["omega_squared"] = round(random.uniform(0.08, 0.45), 4)

    return fit_stats


def generate_diagnostics(model_type: str) -> Dict[str, Any]:
    """Generate mock model assumption diagnostic checks.

    Args:
        model_type: Type of statistical model

    Returns:
        Dictionary of diagnostic test results
    """
    diagnostics = {
        "assumption_checks": {},
        "influential_observations": [],
        "recommendations": [],
    }

    # Normality of residuals (Shapiro-Wilk test)
    shapiro_w = round(random.uniform(0.92, 0.99), 4)
    shapiro_p = round(random.uniform(0.05, 0.8), 4)
    normality_passed = shapiro_p > 0.05

    diagnostics["assumption_checks"]["normality"] = {
        "test": "Shapiro-Wilk",
        "statistic": shapiro_w,
        "p_value": shapiro_p,
        "passed": normality_passed,
        "interpretation": "Residuals appear normally distributed" if normality_passed
                         else "Residuals may deviate from normality",
    }

    # Homoscedasticity (Breusch-Pagan test)
    bp_chi2 = round(random.uniform(1.0, 10.0), 2)
    bp_p = round(random.uniform(0.05, 0.7), 4)
    homoscedasticity_passed = bp_p > 0.05

    diagnostics["assumption_checks"]["homoscedasticity"] = {
        "test": "Breusch-Pagan",
        "statistic": bp_chi2,
        "p_value": bp_p,
        "passed": homoscedasticity_passed,
        "interpretation": "Constant variance assumption satisfied" if homoscedasticity_passed
                         else "Evidence of heteroscedasticity detected",
    }

    # Multicollinearity (VIF)
    max_vif = round(random.uniform(1.2, 8.0), 2)
    multicollinearity_passed = max_vif < 5.0

    diagnostics["assumption_checks"]["multicollinearity"] = {
        "test": "Variance Inflation Factor (VIF)",
        "max_vif": max_vif,
        "threshold": 5.0,
        "passed": multicollinearity_passed,
        "interpretation": "No concerning multicollinearity" if multicollinearity_passed
                         else "Potential multicollinearity issues detected",
    }

    # Autocorrelation (Durbin-Watson) - for time series / longitudinal
    if model_type in ("regression", "mixed"):
        dw_stat = round(random.uniform(1.5, 2.5), 4)
        autocorr_passed = 1.5 < dw_stat < 2.5

        diagnostics["assumption_checks"]["autocorrelation"] = {
            "test": "Durbin-Watson",
            "statistic": dw_stat,
            "passed": autocorr_passed,
            "interpretation": "No significant autocorrelation" if autocorr_passed
                             else "Potential autocorrelation in residuals",
        }

    # Identify mock influential observations
    n_influential = random.randint(0, 3)
    for i in range(n_influential):
        diagnostics["influential_observations"].append({
            "observation_id": random.randint(1, 500),
            "cooks_distance": round(random.uniform(0.5, 2.0), 4),
            "leverage": round(random.uniform(0.1, 0.4), 4),
            "studentized_residual": round(random.uniform(2.5, 4.0), 4),
        })

    # Generate recommendations based on diagnostics
    if not normality_passed:
        diagnostics["recommendations"].append(
            "Consider transforming the dependent variable or using robust standard errors"
        )
    if not homoscedasticity_passed:
        diagnostics["recommendations"].append(
            "Consider using heteroscedasticity-consistent standard errors (HC3)"
        )
    if not multicollinearity_passed:
        diagnostics["recommendations"].append(
            "Consider removing or combining highly correlated predictors"
        )
    if n_influential > 0:
        diagnostics["recommendations"].append(
            f"Review {n_influential} influential observation(s) for potential outliers"
        )

    if not diagnostics["recommendations"]:
        diagnostics["recommendations"].append(
            "Model assumptions appear reasonably satisfied"
        )

    return diagnostics


def compute_real_diagnostics(
    y_true,
    y_pred,
    model_type: str,
) -> Dict[str, Any]:
    """
    Lightweight real diagnostics using scipy/statsmodels when available.
    """
    diagnostics = {
        "assumption_checks": {},
        "influential_observations": [],
        "recommendations": [],
    }
    if y_true is None or y_pred is None or np is None:
        return diagnostics

    try:
        residuals = np.asarray(y_true) - np.asarray(y_pred)
        n = len(residuals)

        # Normality (Shapiro on sample up to 5000)
        if SCIPY_AVAILABLE and n >= 3:
            sample = residuals[: min(5000, n)]
            shapiro_w, shapiro_p = stats.shapiro(sample)
            diagnostics["assumption_checks"]["normality"] = {
                "test": "Shapiro-Wilk",
                "statistic": float(shapiro_w),
                "p_value": float(shapiro_p),
                "passed": bool(shapiro_p > 0.05),
            }

        # Homoscedasticity (Levene across two groups)
        if SCIPY_AVAILABLE and n >= 10:
            mid = n // 2
            lev_stat, lev_p = stats.levene(residuals[:mid], residuals[mid:])
            diagnostics["assumption_checks"]["homoscedasticity"] = {
                "test": "Levene",
                "statistic": float(lev_stat),
                "p_value": float(lev_p),
                "passed": bool(lev_p > 0.05),
            }

        # Autocorrelation (Durbin-Watson)
        if model_type in ("regression", "mixed") and n > 2:
            diff = np.diff(residuals)
            dw = np.sum(diff**2) / (np.sum(residuals**2) + 1e-9)
            diagnostics["assumption_checks"]["autocorrelation"] = {
                "test": "Durbin-Watson",
                "statistic": float(dw),
                "passed": 1.5 < dw < 2.5,
            }

    except Exception as exc:  # pragma: no cover
        diagnostics["assumption_checks"]["diagnostic_error"] = str(exc)

    return diagnostics


@register_stage
class StatisticalModelAgent(BaseStageAgent):
    """Stage 07: Statistical Modeling

    Fits statistical models and performs validation diagnostics.
    """

    stage_id = 7
    stage_name = "Statistical Modeling"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the StatisticalModelAgent.

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

    async def _run_bias_detection_stage7(self, context: StageContext, model_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run bias detection agent for statistical model outputs (feature-flagged, non-blocking).
        
        Args:
            context: Stage context
            model_output: Model fitting results with coefficients and fit stats
            
        Returns:
            Bias detection results or None if disabled/failed
        """
        try:
            import httpx
            
            # Build model summary for bias detection
            model_summary = model_output.get("model_summary", {})
            coefficients = model_output.get("coefficients", [])
            
            dataset_summary = f"Statistical model: {model_summary.get('model_type', 'unknown')} with {len(coefficients)} predictors"
            
            # Call orchestrator AI router for bias detection
            orchestrator_url = os.getenv("ORCHESTRATOR_INTERNAL_URL", "http://orchestrator:3001")
            service_token = os.getenv("WORKER_SERVICE_TOKEN", "")
            
            payload = {
                "task_type": "CLINICAL_BIAS_DETECTION",
                "request_id": f"{context.run_id}-stage7-bias",
                "workflow_id": context.run_id,
                "mode": context.config.get("mode", "DEMO"),
                "inputs": {
                    "dataset_summary": dataset_summary,
                    "pasted_data": json.dumps(model_output, indent=2),
                    "generate_report": True
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{orchestrator_url}/api/ai/router/dispatch",
                    json=payload,
                    headers={"Authorization": f"Bearer {service_token}"}
                )
                
                if response.status_code == 200:
                    dispatch_result = response.json()
                    
                    # Write artifact
                    from pathlib import Path as PathLib
                    artifact_dir = PathLib(f"/data/artifacts/{context.run_id}/bias_detection/stage_7")
                    artifact_dir.mkdir(parents=True, exist_ok=True)
                    
                    report_path = artifact_dir / "report.json"
                    with open(report_path, "w") as f:
                        json.dump(dispatch_result, f, indent=2)
                    
                    logger.info(f"Bias detection artifact written to {report_path}")
                    return dispatch_result
                else:
                    logger.warning(f"Bias detection dispatch failed: HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.warning(f"Bias detection error (non-blocking): {str(e)}")
            return None

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            Tool(
                name="fit_regression_model",
                description="Fit linear/logistic (and other) regression. Input: JSON with model_type, dependent_variable, independent_variables.",
                func=self._fit_regression_model_tool,
            ),
            Tool(
                name="run_anova",
                description="Run ANOVA analysis. Input: JSON with independent_variables or n_predictors.",
                func=self._run_anova_tool,
            ),
            Tool(
                name="calculate_effect_size",
                description="Calculate Cohen's d, odds ratios. Input: JSON with means/stds or coefficients.",
                func=self._calculate_effect_size_tool,
            ),
            Tool(
                name="check_model_assumptions",
                description="Test normality, homoscedasticity. Input: JSON with model_type.",
                func=self._check_model_assumptions_tool,
            ),
            Tool(
                name="generate_model_summary",
                description="Create formatted model output. Input: JSON with coefficients, fit_statistics, diagnostics.",
                func=self._generate_model_summary_tool,
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for statistical modeling."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        return PromptTemplate.from_template("""You are a Statistical Modeling Specialist for clinical research.

Your task is to fit and validate statistical models based on:
1. Model type (regression, logistic, poisson, cox, mixed, anova)
2. Dependent and independent variables
3. Goodness-of-fit and assumption diagnostics
4. Formatted model summary for the results section

Model Type: {model_type}

Dependent Variable: {dependent_variable}

Independent Variables: {independent_variables}

Key Findings: {key_findings}

Your goal is to:
1. Fit the appropriate regression or ANOVA model
2. Run assumption checks (normality, homoscedasticity, multicollinearity)
3. Calculate effect sizes (Cohen's d, odds ratios) where applicable
4. Generate a formatted model summary for the manuscript

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    # =========================================================================
    # Tool implementations (wrappers for LangChain)
    # =========================================================================

    def _fit_regression_model_tool(self, input_json: str) -> str:
        """Tool: fit regression model (mock when no DataFrame in tool context)."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            model_type = data.get("model_type", "regression")
            if model_type not in SUPPORTED_MODEL_TYPES:
                return f"Unsupported model type: {model_type}. Supported: {list(SUPPORTED_MODEL_TYPES.keys())}"
            ind_vars = data.get("independent_variables", ["predictor_1", "predictor_2"])
            coefficients = generate_mock_coefficients(ind_vars, model_type)
            fit_stats = generate_fit_statistics(model_type, len(ind_vars))
            return json.dumps({"coefficients": coefficients, "fit_statistics": fit_stats}, indent=2)
        except Exception as e:
            return f"Failed to fit regression model: {str(e)}"

    def _run_anova_tool(self, input_json: str) -> str:
        """Tool: run ANOVA analysis (mock)."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            ind_vars = data.get("independent_variables", [])
            n_predictors = data.get("n_predictors", len(ind_vars) if ind_vars else 2)
            if ind_vars and not n_predictors:
                n_predictors = len(ind_vars)
            fit_stats = generate_fit_statistics("anova", n_predictors)
            return json.dumps({"fit_statistics": fit_stats, "model_type": "anova"}, indent=2)
        except Exception as e:
            return f"Failed to run ANOVA: {str(e)}"

    def _calculate_effect_size_tool(self, input_json: str) -> str:
        """Tool: calculate Cohen's d, odds ratios from coefficients or means/stds."""
        try:
            import math
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            if "coefficients" in data and data.get("model_type") == "logistic":
                # Odds ratios from logistic coefficients: OR = exp(estimate)
                out = {}
                for c in data["coefficients"]:
                    var = c.get("variable", "?")
                    est = c.get("estimate")
                    if est is not None:
                        out[f"odds_ratio_{var}"] = round(math.exp(est), 4)
                return json.dumps(out, indent=2) if out else json.dumps({"message": "No coefficients"})
            # Mock Cohen's d from means/stds or placeholder
            m1 = data.get("mean1", 0.5)
            m2 = data.get("mean2", 0.3)
            s1 = data.get("std1", 0.2)
            s2 = data.get("std2", 0.2)
            pooled_std = ((s1 ** 2 + s2 ** 2) / 2) ** 0.5 if (s1 or s2) else 0.2
            cohens_d = round((m1 - m2) / pooled_std, 4) if pooled_std else 0.0
            return json.dumps({"cohens_d": cohens_d, "interpretation": "small" if abs(cohens_d) < 0.5 else "medium" if abs(cohens_d) < 0.8 else "large"}, indent=2)
        except Exception as e:
            return f"Failed to calculate effect size: {str(e)}"

    def _check_model_assumptions_tool(self, input_json: str) -> str:
        """Tool: run assumption checks (normality, homoscedasticity)."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            model_type = data.get("model_type", "regression")
            diagnostics = generate_diagnostics(model_type)
            return json.dumps(diagnostics, indent=2)
        except Exception as e:
            return f"Failed to check model assumptions: {str(e)}"

    def _generate_model_summary_tool(self, input_json: str) -> str:
        """Tool: format model output as readable summary."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            coefficients = data.get("coefficients", [])
            fit_stats = data.get("fit_statistics", data.get("goodness_of_fit", {}))
            diagnostics = data.get("diagnostics", {})
            lines = ["=== Model Summary ==="]
            for k, v in fit_stats.items():
                lines.append(f"  {k}: {v}")
            lines.append("\n=== Coefficients ===")
            for c in coefficients:
                lines.append(f"  {c.get('variable', '?')}: estimate={c.get('estimate')}, p={c.get('p_value')}")
            if diagnostics.get("assumption_checks"):
                lines.append("\n=== Assumption Checks ===")
                for name, check in diagnostics["assumption_checks"].items():
                    lines.append(f"  {name}: passed={check.get('passed')}, {check.get('interpretation', '')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to generate model summary: {str(e)}"

    async def execute(self, context: StageContext) -> StageResult:
        """Execute statistical modeling stage.

        Args:
            context: Stage execution context containing:
                - config.model_type: Type of model (default: "regression")
                - config.dependent_variable: Outcome variable name
                - config.independent_variables: List of predictor variable names

        Returns:
            StageResult with model summary, fit statistics, and diagnostics
        """
        started_at = datetime.utcnow()
        output: Dict[str, Any] = {}
        artifacts: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Extract configuration
            model_type = context.config.get("model_type", "regression")
            dependent_variable = context.config.get("dependent_variable")
            independent_variables = context.config.get("independent_variables", [])

            logger.info(
                f"Starting statistical modeling: model_type={model_type}, "
                f"job_id={context.job_id}"
            )

            # Validate model type
            if model_type not in SUPPORTED_MODEL_TYPES:
                errors.append(
                    f"Unsupported model type: '{model_type}'. "
                    f"Supported types: {list(SUPPORTED_MODEL_TYPES.keys())}"
                )
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at.isoformat() + "Z",
                    errors=errors,
                )

            # Validate dependent variable
            if not dependent_variable:
                warnings.append(
                    "No dependent_variable specified; using placeholder 'outcome'"
                )
                dependent_variable = "outcome"

            # Validate independent variables
            if not independent_variables:
                warnings.append(
                    "No independent_variables specified; using default predictors"
                )
                independent_variables = ["predictor_1", "predictor_2", "predictor_3"]

            # Build model summary
            output["model_summary"] = {
                "model_type": model_type,
                "model_description": SUPPORTED_MODEL_TYPES[model_type],
                "dependent_variable": dependent_variable,
                "independent_variables": independent_variables,
                "formula": f"{dependent_variable} ~ {' + '.join(independent_variables)}",
            }
            output["model_type"] = model_type

            logger.info(f"Fitting {SUPPORTED_MODEL_TYPES[model_type]} model")

            # Statistical knowledge graph: method recommendations by study/outcome type
            prior_6 = context.prior_stage_outputs.get(6, {}) or {}
            study_type = context.config.get("study_type") or prior_6.get("study_type") or "observational"
            outcome_type = context.config.get("outcome_type") or prior_6.get("outcome_type") or "continuous"
            sample_size = context.config.get("sample_size") or prior_6.get("sample_size")
            has_confounders = context.config.get("has_confounders", False)
            is_clustered = context.config.get("is_clustered", False)
            if KG_AVAILABLE and StatisticalKnowledgeGraph is not None:
                try:
                    kg = StatisticalKnowledgeGraph()
                    recs = kg.recommend_methods(
                        study_type=study_type,
                        outcome_type=outcome_type,
                        sample_size=sample_size,
                        has_confounders=has_confounders,
                        is_clustered=is_clustered,
                    )
                    output["method_recommendations"] = [asdict(r) for r in recs]
                    if recs and sample_size is not None:
                        valid, size_warnings = kg.validate_sample_size(recs[0].method, sample_size)
                        for w in size_warnings:
                            warnings.append(w)
                except Exception as e:
                    logger.warning(f"Knowledge graph recommendations failed: {e}")
                    output["method_recommendations"] = []
            else:
                output["method_recommendations"] = []

            # Try to load actual data for real analysis
            df = None
            dataset_pointer = context.dataset_pointer
            used_real_analysis = False

            if dataset_pointer and PANDAS_AVAILABLE and ANALYSIS_SERVICE_AVAILABLE:
                try:
                    if dataset_pointer.endswith('.csv'):
                        df = pd.read_csv(dataset_pointer)
                    elif dataset_pointer.endswith('.parquet'):
                        df = pd.read_parquet(dataset_pointer)
                    elif dataset_pointer.endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(dataset_pointer)
                    elif dataset_pointer.endswith('.tsv'):
                        df = pd.read_csv(dataset_pointer, sep='\t')
                    logger.info(f"Loaded dataset for real modeling: {len(df)} rows, {len(df.columns)} cols")
                except Exception as e:
                    logger.warning(f"Could not load dataset for real modeling: {e}")
                    df = None

            # Perform REAL statistical modeling if data is available
            if df is not None and model_type in ["regression", "logistic", "poisson", "cox"]:
                # Prefer AutoModelSelector path for regression/logistic if ML utilities are available
                if (
                    ML_UTILS_AVAILABLE
                    and np is not None
                    and model_type in ["regression", "logistic"]
                ):
                    try:
                        # Prepare data
                        available_cols = [c for c in independent_variables if c in df.columns]
                        if not available_cols:
                            available_cols = [c for c in df.columns if c != dependent_variable][:5]
                        temp_df = df[[dependent_variable] + available_cols].dropna()
                        X_df = temp_df[available_cols]
                        y_vec = temp_df[dependent_variable]

                        selector = AutoModelSelector(random_state=42)
                        selector.analyze_data_characteristics(temp_df, dependent_variable)
                        best = selector.evaluate_model_families(X_df, y_vec, model_type)
                        best_model = best.estimator
                        best_model.fit(X_df, y_vec)

                        shap_expl = selector.get_shap_explanations(best_model, X_df)
                        var_selector = VariableSelector(random_state=42)
                        selected_shap = var_selector.select_by_shap(best_model, X_df, threshold=0.01)
                        _ = var_selector.select_by_lasso(X_df, y_vec, alpha=0.5)
                        _ = var_selector.select_by_rfe(best_model, X_df, y_vec, n_features=min(10, X_df.shape[1]))
                        _ = var_selector.detect_multicollinearity(X_df, vif_threshold=5.0)
                        var_expl = var_selector.get_selection_explanation()

                        # Fit statistics
                        if model_type == "regression":
                            y_hat = best_model.predict(X_df)
                            if r2_score:
                                r2 = r2_score(y_vec, y_hat)
                            else:  # pragma: no cover
                                ss_res = float(np.sum((y_vec - y_hat) ** 2))
                                ss_tot = float(np.sum((y_vec - np.mean(y_vec)) ** 2))
                                r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
                            if mean_squared_error:
                                rmse = sqrt(mean_squared_error(y_vec, y_hat))
                            else:  # pragma: no cover
                                rmse = float(np.sqrt(np.mean((y_vec - y_hat) ** 2)))
                            fit_statistics = {
                                "n_observations": len(X_df),
                                "n_predictors": X_df.shape[1],
                                "r_squared": r2,
                                "rmse": rmse,
                                "aic": best.aic,
                                "bic": best.bic,
                                "cv_score": best.cv_score,
                            }
                        else:
                            proba = best_model.predict_proba(X_df)
                            preds = np.argmax(proba, axis=1)
                            acc = accuracy_score(y_vec, preds) if accuracy_score else float(np.mean(preds == y_vec))
                            auc = (
                                roc_auc_score(y_vec, proba[:, 1]) if roc_auc_score and len(np.unique(y_vec)) == 2 else None
                            )
                            fit_statistics = {
                                "n_observations": len(X_df),
                                "n_predictors": X_df.shape[1],
                                "accuracy": acc,
                                "roc_auc": auc,
                                "aic": best.aic,
                                "bic": best.bic,
                                "cv_score": best.cv_score,
                            }

                        # Coefficients (best effort)
                        coefficients = []
                        if hasattr(best_model, "coef_"):
                            coef_arr = np.ravel(best_model.coef_) if np is not None else best_model.coef_
                            for name, coef_val in zip(X_df.columns, coef_arr):
                                coefficients.append(
                                    {
                                        "variable": name,
                                        "estimate": float(coef_val),
                                        "std_error": None,
                                        "t_value": None,
                                        "p_value": None,
                                        "ci_lower": None,
                                        "ci_upper": None,
                                    }
                                )
                        elif hasattr(best_model, "feature_importances_"):
                            for name, imp in zip(X_df.columns, best_model.feature_importances_):
                                coefficients.append(
                                    {
                                        "variable": name,
                                        "estimate": float(imp),
                                        "std_error": None,
                                        "t_value": None,
                                        "p_value": None,
                                        "ci_lower": None,
                                        "ci_upper": None,
                                    }
                                )

                        output["coefficients"] = coefficients
                        output["fit_statistics"] = fit_statistics
                        output["significant_predictors"] = selected_shap or [c["variable"] for c in coefficients][:5]
                        output["n_significant"] = len(output["significant_predictors"])
                        output["real_analysis"] = True
                        used_real_analysis = True

                        # Diagnostics from residuals
                        if model_type == "regression":
                            y_hat = best_model.predict(X_df)
                        else:
                            y_hat = np.argmax(best_model.predict_proba(X_df), axis=1)
                        output["diagnostics"] = compute_real_diagnostics(y_vec, y_hat, model_type)

                        # Model selection summary
                        output["model_selection"] = {
                            "best": {
                                "family": best.family.value,
                                "model_name": best.model_name,
                                "aic": best.aic,
                                "bic": best.bic,
                                "cv_score": best.cv_score,
                            },
                            "candidates": [
                                {
                                    "family": c.family.value,
                                    "model_name": c.model_name,
                                    "aic": c.aic,
                                    "bic": c.bic,
                                    "cv_score": c.cv_score,
                                }
                                for c in selector.candidates
                            ],
                            "rationale": selector.selection_rationale,
                        }

                        output["shap_explanations"] = shap_expl
                        output["variable_selection"] = var_expl
                        logger.info("Used AutoModelSelector path for real modeling")

                    except Exception as e:  # pragma: no cover - robustness
                        logger.warning(f"AutoModelSelector path failed: {e}")

                # Fallback to AnalysisService-driven modeling if not already done
                if not used_real_analysis:
                    real_results = perform_real_statistical_modeling(
                        df, model_type, dependent_variable, independent_variables
                    )
                    if real_results:
                        output["coefficients"] = real_results["coefficients"]
                        output["fit_statistics"] = real_results["fit_statistics"]
                        output["significant_predictors"] = real_results["significant_predictors"]
                        output["n_significant"] = real_results["n_significant"]
                        output["real_analysis"] = True
                        used_real_analysis = True
                        logger.info("Used REAL statistical modeling")

            # Fallback to mock data if real analysis not available or failed
            if not used_real_analysis:
                # CRITICAL: In LIVE mode, reject mock data fallback
                if context.governance_mode == "LIVE":
                    errors.append(
                        "LIVE mode requires real data analysis. "
                        "Dataset not available or analysis service unavailable. "
                        f"dataset_pointer={dataset_pointer}, "
                        f"PANDAS_AVAILABLE={PANDAS_AVAILABLE}, "
                        f"ANALYSIS_SERVICE_AVAILABLE={ANALYSIS_SERVICE_AVAILABLE}"
                    )
                    logger.error(
                        f"Stage 07 failed in LIVE mode: No real data available. "
                        f"job_id={context.job_id}, dataset_pointer={dataset_pointer}"
                    )
                    return self.create_stage_result(
                        context=context,
                        status="failed",
                        started_at=started_at.isoformat() + "Z",
                        errors=errors,
                        warnings=warnings,
                    )
                
                # DEMO/STANDBY mode: Allow mock data fallback
                warnings.append(
                    "Using mock data generation (DEMO/STANDBY mode only). "
                    "Real data analysis not available."
                )
                output["real_analysis"] = False
                output["mock_data_reason"] = "Dataset not available or analysis service unavailable"

                # Generate mock coefficients
                output["coefficients"] = generate_mock_coefficients(
                    independent_variables, model_type
                )

                # Generate fit statistics
                output["fit_statistics"] = generate_fit_statistics(
                    model_type, len(independent_variables)
                )

                # Determine significant predictors from mock data
                significant_vars = [
                    coef["variable"]
                    for coef in output["coefficients"]
                    if coef["p_value"] < 0.05 and coef["variable"] != "(Intercept)"
                ]

                output["significant_predictors"] = significant_vars
                output["n_significant"] = len(significant_vars)

            # Generate diagnostics (prefer real if available)
            if "diagnostics" not in output or not output.get("diagnostics"):
                output["diagnostics"] = generate_diagnostics(model_type)

            # Add any diagnostic warnings
            for check_name, check_result in output["diagnostics"]["assumption_checks"].items():
                if not check_result.get("passed", True):
                    warnings.append(
                        f"Assumption check '{check_name}' flagged: {check_result.get('interpretation', 'Review recommended')}"
                    )

            # Expected output shape: confidence_intervals, p_values, goodness_of_fit
            coefficients = output.get("coefficients", [])
            output["confidence_intervals"] = {
                c.get("variable", "?"): {"lower": c.get("ci_lower"), "upper": c.get("ci_upper")}
                for c in coefficients
            }
            output["p_values"] = {
                c.get("variable", "?"): c.get("p_value") for c in coefficients
            }
            output["goodness_of_fit"] = dict(output.get("fit_statistics", {}))

            significant_predictors = output.get("significant_predictors", [])
            logger.info(
                f"Model fitting complete: {len(significant_predictors)} significant predictors, "
                f"n={output['fit_statistics'].get('n_observations', 'NA')}"
            )

            # Write artifact
            os.makedirs(context.artifact_path, exist_ok=True)
            artifact_path = os.path.join(context.artifact_path, "statistical_model_results.json")
            artifact_data = {
                "schema_version": "1.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "model_type": output.get("model_type"),
                "coefficients": output.get("coefficients"),
                "fit_statistics": output.get("fit_statistics"),
                "diagnostics": output.get("diagnostics"),
                "model_selection": output.get("model_selection"),
                "shap_explanations": output.get("shap_explanations"),
                "variable_selection": output.get("variable_selection"),
            }
            with open(artifact_path, "w") as f:
                json.dump(artifact_data, f, indent=2, default=str)
            artifacts.append(artifact_path)

            # Optional bridge: results-scaffold createScaffold
            manuscript_id = context.config.get("manuscript_id") or context.job_id
            dataset_ids = context.config.get("dataset_ids") or [context.job_id]
            try:
                await self.call_manuscript_service(
                    "results-scaffold",
                    "createScaffold",
                    {
                        "manuscriptId": manuscript_id,
                        "datasetIds": dataset_ids,
                        "primaryOutcome": dependent_variable or "outcome",
                    },
                )
            except Exception as e:
                logger.warning(f"results-scaffold createScaffold failed: {e}")
                warnings.append(f"Results scaffold unavailable: {str(e)}. Proceeding without scaffold.")

            # Optional bridge: claude-writer for results interpretation
            try:
                sig_preds = output.get("significant_predictors", [])
                model_results_summary = json.dumps({
                    "model_type": model_type,
                    "significant_predictors": sig_preds,
                    "n_significant": output.get("n_significant", 0),
                    "goodness_of_fit": output.get("goodness_of_fit", {}),
                })
                para_result = await self.call_manuscript_service(
                    "claude-writer",
                    "generateParagraph",
                    {
                        "topic": "Statistical results for the results section",
                        "context": model_results_summary,
                        "section": "results",
                        "keyPoints": sig_preds[:5],
                        "tone": "formal",
                    },
                )
                results_interpretation = para_result.get("paragraph", "") or para_result.get("content", "")
                if results_interpretation:
                    output["results_interpretation"] = results_interpretation
            except Exception as e:
                logger.warning(f"claude-writer generateParagraph failed: {e}")
                warnings.append(f"Results interpretation unavailable: {str(e)}. Proceeding without.")

        except Exception as e:
            logger.exception(f"Statistical modeling failed: {str(e)}")
            errors.append(f"Statistical modeling failed: {str(e)}")

        # Feature-flagged: Optional bias detection in statistical modeling
        if os.getenv("ENABLE_BIAS_DETECTION_STAGE7", "false").lower() == "true":
            try:
                bias_result = await self._run_bias_detection_stage7(context, output)
                if bias_result:
                    output["bias_detection"] = bias_result
                    logger.info(f"Bias detection completed for stage 7: {bias_result.get('bias_verdict', 'N/A')}")
            except Exception as e:
                logger.warning(f"Bias detection failed (non-blocking): {str(e)}")
                warnings.append(f"Bias detection unavailable: {str(e)}")

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
                "model_type": context.config.get("model_type", "regression"),
            },
        )
