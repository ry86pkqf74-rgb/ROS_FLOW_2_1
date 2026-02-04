import math

import pytest
from sklearn.datasets import make_classification, make_regression
from sklearn.ensemble import RandomForestClassifier

from src.ml import AutoModelSelector, SHAP_AVAILABLE


def _df_from_np(X, y, target_name):
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return X, y
    cols = [f"f{i}" for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=cols)
    df[target_name] = y
    return df[cols], df[target_name]


def test_model_selector_regression_basic():
    X, y = make_regression(
        n_samples=80, n_features=6, n_informative=3, random_state=0, noise=0.1
    )
    X_df, y_series = _df_from_np(X, y, "target")
    selector = AutoModelSelector(random_state=0)
    summary = selector.analyze_data_characteristics(
        y_series.to_frame().join(X_df), "target"
    )
    assert summary["problem_type"] == "regression"

    best = selector.evaluate_model_families(X_df, y_series, "regression")
    assert best is not None
    assert selector.candidates, "No candidates evaluated"
    assert math.isfinite(best.aic)
    assert math.isfinite(best.bic)

    best.estimator.fit(X_df, y_series)
    shap_expl = selector.get_shap_explanations(best.estimator, X_df)
    assert "available" in shap_expl


def test_model_selector_classification_basic():
    X, y = make_classification(
        n_samples=90,
        n_features=8,
        n_informative=4,
        n_classes=2,
        random_state=1,
    )
    X_df, y_series = _df_from_np(X, y, "label")
    selector = AutoModelSelector(random_state=1)
    summary = selector.analyze_data_characteristics(
        y_series.to_frame().join(X_df), "label"
    )
    assert summary["problem_type"] == "classification"
    best = selector.evaluate_model_families(X_df, y_series, "classification")
    assert best.family is not None
    assert selector.selection_rationale

    # sanity check SHAP path does not raise even if unavailable
    rf = RandomForestClassifier(random_state=1).fit(X_df, y_series)
    shap_expl = selector.get_shap_explanations(rf, X_df)
    assert "available" in shap_expl

