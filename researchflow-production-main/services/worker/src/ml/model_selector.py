"""
AutoML-style model family selection with SHAP explainability.

This module is intentionally self-contained and defensive:
- All heavy optional dependencies (shap, tpot, auto-sklearn) are guarded.
- Falls back gracefully when a dependency is missing or a fit fails.
- Keeps runtimes short for worker jobs by capping CV folds/sample sizes.
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

try:  # pandas is expected in the worker, but guard anyway
    import pandas as pd
except ImportError:  # pragma: no cover - handled gracefully
    pd = None  # type: ignore

# Optional heavy libs
try:
    import shap  # type: ignore

    SHAP_AVAILABLE = True
except Exception:  # pragma: no cover - shap not installed
    shap = None  # type: ignore
    SHAP_AVAILABLE = False

try:
    from tpot import TPOTClassifier, TPOTRegressor  # type: ignore

    TPOT_AVAILABLE = True
except Exception:  # pragma: no cover - tpot not installed
    TPOT_AVAILABLE = False
    TPOTClassifier = TPOTRegressor = None  # type: ignore

try:
    import autosklearn  # type: ignore
    import autosklearn.classification  # type: ignore
    import autosklearn.regression  # type: ignore

    AUTOSKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover - auto-sklearn not installed
    AUTOSKLEARN_AVAILABLE = False

# Statsmodels only for better metrics when available
try:
    import statsmodels.api as sm  # type: ignore
except Exception:  # pragma: no cover
    sm = None  # type: ignore

from sklearn.base import BaseEstimator, clone
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import (
    BayesianRidge,
    ElasticNet,
    LinearRegression,
    LogisticRegression,
)
from sklearn.metrics import (
    accuracy_score,
    log_loss,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.svm import SVC, SVR

logger = logging.getLogger(__name__)

CV_FOLDS_DEFAULT = 3
MAX_SHAP_SAMPLE = 200  # keep SHAP fast


class ModelFamily(str, Enum):
    LINEAR = "LINEAR"
    LOGISTIC = "LOGISTIC"
    TREE_BASED = "TREE_BASED"
    ENSEMBLE = "ENSEMBLE"
    NONPARAMETRIC = "NONPARAMETRIC"
    BAYESIAN = "BAYESIAN"
    TPOT = "TPOT"
    AUTOSKLEARN = "AUTOSKLEARN"


@dataclass
class ModelCandidate:
    family: ModelFamily
    model_name: str
    estimator: BaseEstimator
    aic: float
    bic: float
    cv_score: float
    assumptions_met: bool
    rationale: str = ""
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def _is_classification(y: np.ndarray) -> bool:
    if y.dtype.kind in {"b", "O", "U", "S"}:
        return True
    unique = np.unique(y)
    return len(unique) <= 15 and np.all(np.mod(unique, 1) == 0)


def _train_test_split_indices(n: int, frac: float = 0.8) -> Tuple[np.ndarray, np.ndarray]:
    idx = np.arange(n)
    np.random.shuffle(idx)
    cut = int(n * frac)
    return idx[:cut], idx[cut:]


def _compute_rss(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    residuals = y_true - y_pred
    return float(np.sum(residuals**2))


def _safe_log_loss(y_true: np.ndarray, proba: np.ndarray) -> float:
    try:
        return float(log_loss(y_true, proba, labels=np.unique(y_true)))
    except Exception:
        # fall back to small epsilon smoothing
        eps = 1e-9
        proba = np.clip(proba, eps, 1 - eps)
        return float(log_loss(y_true, proba, labels=np.unique(y_true)))


def _aic_bic_from_regression(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> Tuple[float, float]:
    n = len(y_true)
    rss = _compute_rss(y_true, y_pred)
    sigma2 = rss / n if n else 0.0
    if sigma2 <= 0:
        sigma2 = 1e-9
    loglik = -0.5 * n * (math.log(2 * math.pi) + math.log(sigma2) + 1)
    aic = -2 * loglik + 2 * k
    bic = -2 * loglik + k * math.log(max(n, 1))
    return float(aic), float(bic)


def _aic_bic_from_classification(y_true: np.ndarray, proba: np.ndarray, k: int) -> Tuple[float, float]:
    n = len(y_true)
    nll = _safe_log_loss(y_true, proba) * n
    aic = 2 * k + 2 * nll
    bic = math.log(max(n, 1)) * k + 2 * nll
    return float(aic), float(bic)


def _normalize_feature_importance(raw: Dict[str, float]) -> Dict[str, float]:
    total = sum(abs(v) for v in raw.values()) or 1.0
    return {k: abs(v) / total for k, v in raw.items()}


class AutoModelSelector:
    """
    Light-weight AutoML helper that compares a curated set of model families.

    It computes cross-validation scores plus approximate AIC/BIC to penalize
    complexity. SHAP explanations are provided for the best model when shap is
    available. All operations are defensive and capped for runtime safety.
    """

    def __init__(self, cv_folds: int = CV_FOLDS_DEFAULT, random_state: int = 42):
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.problem_type: Optional[str] = None  # "classification" or "regression"
        self.data_summary: Dict[str, Any] = {}
        self.candidates: List[ModelCandidate] = []
        self.best_candidate: Optional[ModelCandidate] = None
        self.selection_rationale: str = ""

    # ------------------------------------------------------------------ #
    # Data analysis
    # ------------------------------------------------------------------ #
    def analyze_data_characteristics(self, df: "pd.DataFrame", target: str) -> Dict[str, Any]:
        if df is None or target not in df:
            raise ValueError("Target column missing for data analysis")
        y = df[target]
        problem_type = "classification" if _is_classification(y.to_numpy()) else "regression"
        feature_types = {
            "numeric": [c for c in df.columns if c != target and pd.api.types.is_numeric_dtype(df[c])],
            "categorical": [c for c in df.columns if c != target and not pd.api.types.is_numeric_dtype(df[c])],
        }
        class_balance = None
        if problem_type == "classification":
            counts = y.value_counts(normalize=True).to_dict()
            class_balance = counts
        missingness = df.isna().mean().to_dict()
        self.problem_type = problem_type
        self.data_summary = {
            "problem_type": problem_type,
            "class_balance": class_balance,
            "missingness": missingness,
            "feature_types": feature_types,
            "n_rows": len(df),
            "n_features": df.shape[1] - 1,
        }
        return self.data_summary

    # ------------------------------------------------------------------ #
    # Model family evaluation
    # ------------------------------------------------------------------ #
    def _build_preprocessor(self, feature_types: Dict[str, List[str]]) -> ColumnTransformer:
        transformers = []
        numeric_cols = feature_types.get("numeric", [])
        categorical_cols = feature_types.get("categorical", [])
        if numeric_cols:
            transformers.append(("num", StandardScaler(), numeric_cols))
        if categorical_cols:
            transformers.append(("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols))
        return ColumnTransformer(transformers=transformers, remainder="drop")

    def _cross_val_safe(self, estimator: BaseEstimator, X, y, scoring: str) -> float:
        try:
            scores = cross_val_score(estimator, X, y, cv=self.cv_folds, scoring=scoring, error_score=np.nan)
            finite_scores = scores[np.isfinite(scores)]
            if len(finite_scores) == 0:
                return float("nan")
            return float(np.nanmean(finite_scores))
        except Exception as exc:  # pragma: no cover - robustness
            logger.debug("Cross-val failed for %s: %s", estimator, exc)
            return float("nan")

    def _fit_and_score_regression(self, estimator: BaseEstimator, X, y) -> Tuple[float, float, float]:
        estimator = clone(estimator)
        estimator.fit(X, y)
        y_pred = estimator.predict(X)
        k = getattr(estimator, "n_features_in_", X.shape[1])
        aic, bic = _aic_bic_from_regression(y, y_pred, k)
        cv_score = self._cross_val_safe(estimator, X, y, scoring="r2")
        return aic, bic, cv_score

    def _fit_and_score_classification(self, estimator: BaseEstimator, X, y) -> Tuple[float, float, float]:
        estimator = clone(estimator)
        estimator.fit(X, y)
        if hasattr(estimator, "predict_proba"):
            proba = estimator.predict_proba(X)
        elif hasattr(estimator, "decision_function"):
            df_scores = estimator.decision_function(X)
            proba = self._sigmoid_scores(df_scores)
        else:
            proba = np.stack([1 - estimator.predict(X), estimator.predict(X)], axis=1)

        k = getattr(estimator, "n_features_in_", X.shape[1])
        aic, bic = _aic_bic_from_classification(y, proba, k)
        scoring = "roc_auc" if len(np.unique(y)) == 2 else "accuracy"
        cv_score = self._cross_val_safe(estimator, X, y, scoring=scoring)
        return aic, bic, cv_score

    def _sigmoid_scores(self, scores: np.ndarray) -> np.ndarray:
        if scores.ndim == 1:
            scores = scores.reshape(-1, 1)
        probs = 1 / (1 + np.exp(-scores))
        if probs.shape[1] == 1:
            probs = np.hstack([1 - probs, probs])
        return probs

    def evaluate_model_families(self, X, y, problem_type: Optional[str] = None) -> ModelCandidate:
        if problem_type is None:
            problem_type = "classification" if _is_classification(np.asarray(y)) else "regression"
        self.problem_type = problem_type

        feature_types = {"numeric": list(range(X.shape[1])), "categorical": []} if not pd else None
        preprocessor = None
        if pd and isinstance(X, pd.DataFrame):
            feature_types = {
                "numeric": [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])],
                "categorical": [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])],
            }
            preprocessor = self._build_preprocessor(feature_types)

        candidates: List[Tuple[ModelFamily, str, BaseEstimator]] = []
        if problem_type == "regression":
            candidates.extend(
                [
                    (ModelFamily.LINEAR, "LinearRegression", LinearRegression()),
                    (ModelFamily.LINEAR, "ElasticNet", ElasticNet(random_state=self.random_state)),
                    (ModelFamily.TREE_BASED, "RandomForestRegressor", RandomForestRegressor(random_state=self.random_state, n_estimators=150)),
                    (ModelFamily.ENSEMBLE, "GradientBoostingRegressor", GradientBoostingRegressor(random_state=self.random_state)),
                    (ModelFamily.NONPARAMETRIC, "KNeighborsRegressor", KNeighborsRegressor()),
                    (ModelFamily.NONPARAMETRIC, "SVR", SVR()),
                    (ModelFamily.BAYESIAN, "BayesianRidge", BayesianRidge()),
                ]
            )
        else:
            candidates.extend(
                [
                    (ModelFamily.LOGISTIC, "LogisticRegression", LogisticRegression(max_iter=1000, penalty="l2", solver="lbfgs")),
                    (ModelFamily.TREE_BASED, "RandomForestClassifier", RandomForestClassifier(random_state=self.random_state, n_estimators=200)),
                    (ModelFamily.ENSEMBLE, "GradientBoostingClassifier", GradientBoostingClassifier(random_state=self.random_state)),
                    (ModelFamily.NONPARAMETRIC, "KNeighborsClassifier", KNeighborsClassifier()),
                    (ModelFamily.NONPARAMETRIC, "SVC", SVC(probability=True)),
                    (ModelFamily.BAYESIAN, "GaussianNB", __import__("sklearn.naive_bayes").naive_bayes.GaussianNB()),
                ]
            )

        # Optional TPOT candidate
        if TPOT_AVAILABLE:
            if problem_type == "regression":
                candidates.append(
                    (
                        ModelFamily.TPOT,
                        "TPOTRegressor",
                        TPOTRegressor(
                            generations=3,
                            population_size=20,
                            verbosity=0,
                            max_time_mins=1,
                            random_state=self.random_state,
                        ),
                    )
                )
            else:
                candidates.append(
                    (
                        ModelFamily.TPOT,
                        "TPOTClassifier",
                        TPOTClassifier(
                            generations=3,
                            population_size=20,
                            verbosity=0,
                            max_time_mins=1,
                            random_state=self.random_state,
                        ),
                    )
                )

        # Optional auto-sklearn stub
        if AUTOSKLEARN_AVAILABLE:
            if problem_type == "regression":
                model = autosklearn.regression.AutoSklearnRegressor(  # type: ignore
                    time_left_for_this_task=60, per_run_time_limit=30, seed=self.random_state
                )
                candidates.append((ModelFamily.AUTOSKLEARN, "AutoSklearnRegressor", model))
            else:
                model = autosklearn.classification.AutoSklearnClassifier(  # type: ignore
                    time_left_for_this_task=60, per_run_time_limit=30, seed=self.random_state
                )
                candidates.append((ModelFamily.AUTOSKLEARN, "AutoSklearnClassifier", model))

        self.candidates = []
        for family, name, est in candidates:
            estimator = est
            if preprocessor is not None and not isinstance(estimator, Pipeline):
                estimator = Pipeline([("prep", preprocessor), ("model", estimator)])
            try:
                if problem_type == "regression":
                    aic, bic, cv_score = self._fit_and_score_regression(estimator, X, y)
                else:
                    aic, bic, cv_score = self._fit_and_score_classification(estimator, X, y)
                assumptions_met = self._assumptions_ok(family, X, y)
                rationale = f"{name} evaluated with CV={cv_score:.3f}, AIC={aic:.2f}, BIC={bic:.2f}"
                candidate = ModelCandidate(
                    family=family,
                    model_name=name,
                    estimator=estimator,
                    aic=aic,
                    bic=bic,
                    cv_score=cv_score,
                    assumptions_met=assumptions_met,
                    rationale=rationale,
                )
                self.candidates.append(candidate)
            except Exception as exc:  # pragma: no cover - robustness
                logger.warning("Skipping %s due to failure: %s", name, exc)

        if not self.candidates:
            raise RuntimeError("No model candidates succeeded during evaluation")

        self.best_candidate = self._rank_candidates()
        self.selection_rationale = self.generate_selection_rationale()
        return self.best_candidate

    def _assumptions_ok(self, family: ModelFamily, X, y) -> bool:
        if family in (ModelFamily.LINEAR, ModelFamily.LOGISTIC):
            # Simple heuristic: require at least 10 samples per feature
            n, p = X.shape if hasattr(X, "shape") else (len(y), 1)
            return n >= 10 * max(p, 1)
        return True

    def _rank_candidates(self) -> ModelCandidate:
        # Primary: lowest BIC; tie-breaker AIC; then highest CV score
        ranked = sorted(
            self.candidates,
            key=lambda c: (math.inf if math.isnan(c.bic) else c.bic, math.inf if math.isnan(c.aic) else c.aic, -c.cv_score),
        )
        return ranked[0]

    # ------------------------------------------------------------------ #
    # SHAP explanations
    # ------------------------------------------------------------------ #
    def get_shap_explanations(self, model: BaseEstimator, X) -> Dict[str, Any]:
        if not SHAP_AVAILABLE:
            return {"available": False, "reason": "shap not installed"}
        try:
            sample_X = X
            if hasattr(X, "sample"):
                sample_X = X.sample(min(len(X), MAX_SHAP_SAMPLE), random_state=self.random_state)
            elif hasattr(X, "__len__") and len(X) > MAX_SHAP_SAMPLE:
                idx = np.random.default_rng(self.random_state).choice(len(X), size=MAX_SHAP_SAMPLE, replace=False)
                sample_X = X[idx]

            explainer = None
            inner_model = model
            if isinstance(model, Pipeline):
                inner_model = model[-1]

            if hasattr(inner_model, "estimators_") or "Forest" in inner_model.__class__.__name__:
                explainer = shap.TreeExplainer(model)
            elif isinstance(inner_model, (LinearRegression, ElasticNet, LogisticRegression, BayesianRidge)):
                explainer = shap.LinearExplainer(model, sample_X)
            else:
                explainer = shap.KernelExplainer(model.predict_proba if self.problem_type == "classification" else model.predict, sample_X)

            shap_values = explainer(sample_X)
            if isinstance(shap_values, list):
                sv = shap_values[0]
            else:
                sv = shap_values
            base = getattr(sv, "base_values", None)
            values = getattr(sv, "values", None)

            # Feature importance: mean absolute SHAP per feature
            if hasattr(sv, "values"):
                if isinstance(values, list):  # multi-class; take mean over classes
                    arr = np.mean(np.abs(np.stack(values)), axis=0)
                else:
                    arr = np.mean(np.abs(values), axis=0) if values.ndim > 1 else np.abs(values)
                if hasattr(sample_X, "columns"):
                    names = list(sample_X.columns)
                else:
                    names = [f"feature_{i}" for i in range(arr.shape[-1])]
                importance = {name: float(val) for name, val in zip(names, np.ravel(arr))}
            else:
                importance = {}

            return {
                "available": True,
                "values": np.array(values).tolist() if values is not None else None,
                "base_values": base.tolist() if base is not None else None,
                "feature_importance": _normalize_feature_importance(importance),
            }
        except Exception as exc:  # pragma: no cover - robustness
            logger.warning("SHAP explanation failed: %s", exc)
            return {"available": False, "reason": str(exc)}

    # ------------------------------------------------------------------ #
    # Rationale
    # ------------------------------------------------------------------ #
    def generate_selection_rationale(self) -> str:
        if not self.best_candidate:
            return "No best candidate selected."
        lines = [
            f"Problem type: {self.problem_type}",
            f"Best model: {self.best_candidate.model_name} ({self.best_candidate.family})",
            f"BIC={self.best_candidate.bic:.2f}, AIC={self.best_candidate.aic:.2f}, CV={self.best_candidate.cv_score:.3f}",
        ]
        # Compare against runner-up
        if len(self.candidates) > 1:
            runner_up = sorted(self.candidates, key=lambda c: c.bic)[1]
            delta_bic = runner_up.bic - self.best_candidate.bic
            delta_cv = self.best_candidate.cv_score - runner_up.cv_score
            lines.append(f"Runner-up: {runner_up.model_name} (ΔBIC={delta_bic:.2f}, ΔCV={delta_cv:.3f})")
        if self.data_summary:
            lines.append(f"Data summary: {json.dumps(self.data_summary, default=str)}")
        return "\n".join(lines)


# Convenience flag exports for consistency with __init__.py
__all__ = [
    "AutoModelSelector",
    "ModelFamily",
    "ModelCandidate",
    "SHAP_AVAILABLE",
    "TPOT_AVAILABLE",
    "AUTOSKLEARN_AVAILABLE",
]
