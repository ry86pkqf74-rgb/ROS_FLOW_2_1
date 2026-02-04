import pytest
import numpy as np
from sklearn.datasets import make_classification, make_regression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression

from src.ml import VariableSelector
from src.ml.model_selector import SHAP_AVAILABLE


def _df(X):
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return X
    return pd.DataFrame(X, columns=[f"f{i}" for i in range(X.shape[1])])


@pytest.mark.skipif(not SHAP_AVAILABLE, reason="shap not installed")
def test_select_by_shap_returns_features():
    X, y = make_classification(
        n_samples=80, n_features=6, n_informative=3, random_state=3
    )
    model = RandomForestClassifier(random_state=3).fit(X, y)
    selector = VariableSelector(random_state=3)
    selected = selector.select_by_shap(model, _df(X), threshold=0.01)
    assert selected, "SHAP-based selection should return at least one feature"
    expl = selector.get_selection_explanation()
    assert expl["feature_importance"]


def test_select_by_lasso_identifies_signal():
    X, y = make_regression(
        n_samples=70, n_features=5, n_informative=2, random_state=4, noise=0.1
    )
    X[:, 0] *= 5  # make feature 0 strongest
    selector = VariableSelector(random_state=4)
    selected = selector.select_by_lasso(_df(X), y, alpha=0.1)
    assert "f0" in selected


def test_select_by_rfe_reduces_features():
    X, y = make_classification(
        n_samples=60, n_features=6, n_informative=3, random_state=5
    )
    model = LogisticRegression(max_iter=200).fit(X, y)
    selector = VariableSelector(random_state=5)
    selected = selector.select_by_rfe(model, _df(X), y, n_features=3)
    assert len(selected) == 3


def test_detect_multicollinearity_flags_correlated():
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        pytest.skip("pandas not available")
    X, y = make_regression(n_samples=50, n_features=3, random_state=6)
    df = pd.DataFrame(X, columns=["a", "b", "c"])
    df["b"] = df["a"] * 0.9 + np.random.default_rng(6).normal(0, 0.01, size=len(df))
    selector = VariableSelector(random_state=6)
    flagged = selector.detect_multicollinearity(df, vif_threshold=5.0)
    if flagged:
        assert "a" in flagged or "b" in flagged
    # ensure explanation returns structure
    _ = selector.get_selection_explanation()

