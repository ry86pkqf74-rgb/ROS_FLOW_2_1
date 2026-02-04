"""
Statistical method recommendations API.

FastAPI router for the statistical knowledge graph:
- GET /api/analysis/recommendations - Recommend methods by study type and outcome type
- POST /api/analysis/explain-method - Natural-language explanation for a method
- GET /api/analysis/assumption-tests/{method} - Assumption tests for a method
"""

from dataclasses import asdict
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

try:
    from src.knowledge.stats_knowledge_graph import StatisticalKnowledgeGraph, MethodRecommendation
    KG_AVAILABLE = True
except ImportError:
    KG_AVAILABLE = False

router = APIRouter(prefix="/analysis", tags=["stats-recommendations"])


def _get_kg() -> StatisticalKnowledgeGraph:
    if not KG_AVAILABLE:
        raise HTTPException(status_code=503, detail="Statistical knowledge graph not available")
    return StatisticalKnowledgeGraph()


@router.get("/recommendations")
async def get_recommendations(
    studyType: str = Query(..., description="Study type (e.g. RCT, COHORT, CASE_CONTROL)"),
    outcomeType: str = Query(..., description="Outcome type (e.g. BINARY, CONTINUOUS, TIME_TO_EVENT)"),
    sampleSize: Optional[int] = Query(None, description="Sample size for filtering"),
    hasConfounders: bool = Query(False, description="Whether to adjust for confounders"),
    isClustered: bool = Query(False, description="Whether data are clustered"),
) -> List[dict]:
    """
    Return statistical method recommendations for the given study type and outcome type.
    """
    kg = _get_kg()
    recs = kg.recommend_methods(
        study_type=studyType,
        outcome_type=outcomeType,
        sample_size=sampleSize,
        has_confounders=hasConfounders,
        is_clustered=isClustered,
    )
    return [asdict(r) for r in recs]


@router.post("/explain-method")
async def explain_method(body: dict) -> dict:
    """
    Return a natural-language explanation for the given method and optional context.
    Body: { "method": str, "context"?: { "study_type", "outcome_type", ... } }
    """
    method = body.get("method")
    if not method:
        raise HTTPException(status_code=400, detail="Missing 'method' in body")
    context = body.get("context") or {}
    kg = _get_kg()
    explanation = kg.explain_recommendation(method, context)
    return {"explanation": explanation}


@router.get("/assumption-tests/{method}")
async def get_assumption_tests(method: str) -> List[dict]:
    """
    Return assumption tests (name, purpose, threshold, interpretation) for the given method.
    """
    if not method or not method.strip():
        raise HTTPException(status_code=400, detail="Method path is required")
    kg = _get_kg()
    tests = kg.get_assumption_tests(method)
    return tests
