"""
Automated variable selection with explainability.

The class collects multiple selectors (SHAP, L1 regularization, RFE, VIF) and
stores rationale that can be surfaced by workflow stages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

from sklearn.base import BaseEstimator, clone
from sklearn.feature_selection import RFE
from sklearn.linear_model import Lasso, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import log_loss, r2_score
try:
    from sklearn.inspection import permutation_importance
    PERM_AVAILABLE = True
except Exception:  # pragma: no cover
    permutation_importance = None  # type: ignore
    PERM_AVAILABLE = False

from .model_selector import SHAP_AVAILABLE

if SHAP_AVAILABLE:
    import shap  # type: ignore
else:  # pragma: no cover
    shap = None  # type: ignore

try:
    from statsmodels.stats.outliers_influence import variance_inflation_factor  # type: ignore

    SM_VIF_AVAILABLE = True
except Exception:  # pragma: no cover
    SM_VIF_AVAILABLE = False

logger = logging.getLogger(__name__)


def _as_dataframe(X):
    if pd and isinstance(X, pd.DataFrame):
        return X
    return pd.DataFrame(X, columns=[f"feature_{i}" for i in range(np.asarray(X).shape[1])]) if pd else X


def _safe_normalize_importance(imp: Dict[str, float]) -> Dict[str, float]:
    total = sum(abs(v) for v in imp.values()) or 1.0
    return {k: abs(v) / total for k, v in imp.items()}


@dataclass
class SelectionResult:
    method: str
    selected: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


class VariableSelector:
    """
    Combines multiple feature selection strategies and keeps human-readable
    explanations for downstream reporting.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.results: List[SelectionResult] = []
        self.last_importance: Dict[str, float] = {}
        self.multicollinearity_flags: Dict[str, float] = {}
        self._combined: Dict[str, Any] = {}

    # --------------------------------------------------------------- #
    # Internal helper
    # --------------------------------------------------------------- #
    def _store_result(self, method: str, selected: List[str], details: Dict[str, Any]):
        self.results.append(SelectionResult(method=method, selected=selected, details=details))
        for feat in selected:
            self._combined.setdefault(feat, 0)
            self._combined[feat] += 1
        self._combined: Dict[str, Any] = {}

    # --------------------------------------------------------------- #
    # SHAP-based selection
    # --------------------------------------------------------------- #
    def select_by_shap(self, model: BaseEstimator, X, threshold: float = 0.01) -> List[str]:
        if not SHAP_AVAILABLE:
            logger.info("SHAP not available; skipping SHAP selection")
            return []
        try:
            df = _as_dataframe(X)
            sample = df.sample(min(len(df), 150), random_state=self.random_state) if hasattr(df, "sample") else df
            explainer = shap.Explainer(model.predict, sample) if not hasattr(model, "predict_proba") else shap.Explainer(model.predict_proba, sample)
            values = explainer(sample)
            # values can be list for multiclass; take mean absolute
            val = values.values
            if isinstance(val, list):
                val_arr = np.mean(np.abs(np.stack(val)), axis=0)
            else:
                val_arr = np.mean(np.abs(val), axis=0) if val.ndim > 1 else np.abs(val)
            names = list(df.columns) if hasattr(df, "columns") else [f"feature_{i}" for i in range(val_arr.shape[-1])]
            importance = {n: float(v) for n, v in zip(names, np.ravel(val_arr))}
            importance = _safe_normalize_importance(importance)
            self.last_importance = importance
            selected = [k for k, v in importance.items() if v >= threshold]
            self._store_result(
                "shap",
                selected,
                {"threshold": threshold, "feature_importance": importance},
            )
            return selected
        except Exception as exc:  # pragma: no cover - robustness
            logger.warning("SHAP selection failed: %s", exc)
            return []

    # --------------------------------------------------------------- #
    # Lasso / Logistic L1 selection
    # --------------------------------------------------------------- #
    def select_by_lasso(self, X, y, alpha: float = 1.0) -> List[str]:
        df = _as_dataframe(X)
        X_arr = df.values if hasattr(df, "values") else np.asarray(X)
        is_classification = len(np.unique(y)) <= 15 and np.all(np.mod(np.unique(y), 1) == 0)

        if is_classification:
            model = LogisticRegression(
                penalty="l1", solver="saga", max_iter=2000, C=1.0 / max(alpha, 1e-3), random_state=self.random_state
            )
        else:
            model = Lasso(alpha=alpha, random_state=self.random_state, max_iter=5000)

        pipe = Pipeline([("scaler", StandardScaler(with_mean=not is_classification)), ("model", model)])
        try:
            pipe.fit(X_arr, y)
            coefs = pipe.named_steps["model"].coef_
            if coefs.ndim > 1:
                coefs = np.mean(coefs, axis=0)
            names = list(df.columns) if hasattr(df, "columns") else [f"feature_{i}" for i in range(coefs.shape[-1])]
            selected = [n for n, c in zip(names, coefs) if abs(c) > 1e-6]
            details = {"alpha": alpha, "nonzero": {n: float(c) for n, c in zip(names, coefs)}}
            self._store_result("lasso" if not is_classification else "logistic_l1", selected, details)
            return selected
        except Exception as exc:  # pragma: no cover
            logger.warning("L1 selection failed: %s", exc)
            return []

    # --------------------------------------------------------------- #
    # Recursive Feature Elimination
    # --------------------------------------------------------------- #
    def select_by_rfe(self, estimator: BaseEstimator, X, y, n_features: int = 10) -> List[str]:
        df = _as_dataframe(X)
        X_arr = df.values if hasattr(df, "values") else np.asarray(X)
        try:
            est = clone(estimator)
            selector = RFE(est, n_features_to_select=min(n_features, X_arr.shape[1]))
            selector.fit(X_arr, y)
            names = list(df.columns) if hasattr(df, "columns") else [f"feature_{i}" for i in range(X_arr.shape[1])]
            selected = [n for n, keep in zip(names, selector.support_) if keep]
            self._store_result("rfe", selected, {"ranking": dict(zip(names, selector.ranking_.tolist()))})
            return selected
        except Exception as exc:  # pragma: no cover
            logger.warning("RFE selection failed: %s", exc)
            return []

    # --------------------------------------------------------------- #
    # Multicollinearity detection (VIF)
    # --------------------------------------------------------------- #
    def detect_multicollinearity(self, X, vif_threshold: float = 5.0) -> Dict[str, float]:
        df = _as_dataframe(X)
        if not SM_VIF_AVAILABLE or df is None:
            logger.info("statsmodels not available; skipping VIF detection")
            return {}
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])] if pd else df.columns
        if len(numeric_cols) < 2:
            return {}
        vif_df = df[numeric_cols].fillna(0.0)
        vifs: Dict[str, float] = {}
        for i, col in enumerate(vif_df.columns):
            try:
                vifs[col] = float(variance_inflation_factor(vif_df.values, i))
            except Exception as exc:  # pragma: no cover
                logger.debug("VIF failed for %s: %s", col, exc)
        flagged = {k: v for k, v in vifs.items() if v >= vif_threshold}
        self.multicollinearity_flags = flagged
        self._store_result(
            "vif",
            [k for k, v in flagged.items() if v >= vif_threshold],
            {"vif": vifs, "threshold": vif_threshold},
        )
        return flagged

    # --------------------------------------------------------------- #
    # Importance-based quick selectors
    # --------------------------------------------------------------- #
    def select_top_k_importance(self, model: BaseEstimator, X, k: int = 10) -> List[str]:
        """
        Select top-k features using model-provided importance or coefficients.
        """
        df = _as_dataframe(X)
        names = list(df.columns) if hasattr(df, "columns") else [f"feature_{i}" for i in range(np.asarray(X).shape[1])]
        importance = None
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
        elif hasattr(model, "coef_"):
            coef = model.coef_
            if isinstance(coef, np.ndarray) and coef.ndim > 1:
                coef = np.mean(coef, axis=0)
            importance = np.abs(coef)
        if importance is None:
            return []
        pairs = sorted(zip(names, importance), key=lambda kv: kv[1], reverse=True)
        selected = [n for n, _ in pairs[:k]]
        self._store_result("top_k_importance", selected, {"k": k, "importance": dict(zip(names, map(float, importance)))})
        return selected

    def permutation_importance_select(self, model: BaseEstimator, X, y, n_repeats: int = 5, top_k: int = 10) -> List[str]:
        """
        Use permutation importance (if available) to select top-k features.
        """
        if not PERM_AVAILABLE:
            logger.info("Permutation importance not available in this environment")
            return []
        df = _as_dataframe(X)
        try:
            result = permutation_importance(model, df, y, n_repeats=n_repeats, random_state=self.random_state)
            names = list(df.columns) if hasattr(df, "columns") else [f"feature_{i}" for i in range(df.shape[1])]
            importances = dict(zip(names, result.importances_mean.tolist()))
            ordered = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)
            selected = [n for n, _ in ordered[:top_k]]
            self._store_result(
                "permutation_importance",
                selected,
                {"top_k": top_k, "n_repeats": n_repeats, "importance": importances},
            )
            return selected
        except Exception as exc:  # pragma: no cover
            logger.warning("Permutation importance selection failed: %s", exc)
            return []

    # --------------------------------------------------------------- #
    # Aggregation utilities
    # --------------------------------------------------------------- #
    def aggregate_selected(self, strategy: str = "union") -> List[str]:
        """
        Combine selections from multiple methods.

        Args:
            strategy: 'union', 'intersection', or 'vote>=2'
        """
        if not self.results:
            return []
        if strategy == "union":
            return list({feat for r in self.results for feat in r.selected})
        if strategy == "intersection":
            common = set(self.results[0].selected)
            for r in self.results[1:]:
                common &= set(r.selected)
            return list(common)
        if strategy.startswith("vote"):
            threshold = 2
            if ">=" in strategy:
                try:
                    threshold = int(strategy.split(">=")[-1])
                except ValueError:
                    threshold = 2
            return [feat for feat, count in self._combined.items() if count >= threshold]
        return list({feat for r in self.results for feat in r.selected})

    def get_feature_votes(self) -> Dict[str, int]:
        """Return vote counts for each feature across selection methods."""
        return dict(self._combined)

    def reset(self):
        """Clear stored results to reuse the selector on a new dataset."""
        self.results.clear()
        self.last_importance = {}
        self.multicollinearity_flags = {}
        self._combined = {}

    def manual_select(self, features: List[str], reason: str = "expert_override"):
        """
        Allow manual/override selection to be recorded alongside automated methods.
        """
        self._store_result(reason, features, {"reason": reason})

    def summarize(self) -> str:
        """
        Produce a human-readable multi-line summary of selection outcomes.
        """
        lines = []
        for res in self.results:
            lines.append(f"[{res.method}] selected {len(res.selected)} feature(s): {', '.join(res.selected) if res.selected else 'none'}")
        if self.multicollinearity_flags:
            flagged = ", ".join(f"{k}(VIF={v:.2f})" for k, v in self.multicollinearity_flags.items())
            lines.append(f"Multicollinearity flagged: {flagged}")
        combined_union = self.aggregate_selected("union")
        if combined_union:
            lines.append(f"Union of selections: {', '.join(combined_union)}")
        votes = self.get_feature_votes()
        if votes:
            vote_str = ", ".join(f"{k}:{v}" for k, v in sorted(votes.items(), key=lambda kv: kv[1], reverse=True))
            lines.append(f"Votes per feature: {vote_str}")
        return "\n".join(lines)

    def selection_matrix(self) -> List[Dict[str, Any]]:
        """
        Return a matrix-like structure describing feature participation across methods.
        Each row: {feature, methods: [...], vote_count}
        """
        feature_methods: Dict[str, List[str]] = {}
        for res in self.results:
            for feat in res.selected:
                feature_methods.setdefault(feat, []).append(res.method)
        matrix = []
        for feat, methods in feature_methods.items():
            matrix.append({"feature": feat, "methods": methods, "vote_count": len(methods)})
        return sorted(matrix, key=lambda row: row["vote_count"], reverse=True)

    # --------------------------------------------------------------- #
    # Explanation aggregation
    # --------------------------------------------------------------- #
    def get_selection_explanation(self) -> Dict[str, Any]:
        return {
            "results": [
                {
                    "method": r.method,
                    "selected": r.selected,
                    "details": r.details,
                }
                for r in self.results
            ],
            "feature_importance": self.last_importance,
            "multicollinearity": self.multicollinearity_flags,
            "combined": {
                "union": self.aggregate_selected("union"),
                "intersection": self.aggregate_selected("intersection"),
                "vote>=2": self.aggregate_selected("vote>=2"),
            },
        }


__all__ = ["VariableSelector"]
