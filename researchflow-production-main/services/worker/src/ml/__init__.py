"""
Machine learning utilities for the worker service.

Exports:
    - AutoModelSelector: automated model family evaluation with SHAP explainability
    - VariableSelector: feature selection helpers (SHAP, Lasso/Logistic L1, RFE, VIF)
    - ModelFamily, ModelCandidate: metadata containers
    - SHAP_AVAILABLE, TPOT_AVAILABLE, AUTOSKLEARN_AVAILABLE: capability flags
"""

from .model_selector import (
    AutoModelSelector,
    ModelCandidate,
    ModelFamily,
    SHAP_AVAILABLE,
    TPOT_AVAILABLE,
    AUTOSKLEARN_AVAILABLE,
)
from .variable_selector import VariableSelector

__all__ = [
    "AutoModelSelector",
    "VariableSelector",
    "ModelFamily",
    "ModelCandidate",
    "SHAP_AVAILABLE",
    "TPOT_AVAILABLE",
    "AUTOSKLEARN_AVAILABLE",
]
