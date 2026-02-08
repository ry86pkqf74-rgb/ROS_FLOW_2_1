from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Tuple
from app.schemas import LitTriageInputs
from agent import LiteratureTriageAgent, TriageRequest


async def run_lit_triage_ai(inputs_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run AI-powered literature triage using the LangSmith agent
    
    This replaces the rule-based filtering with intelligent search and ranking
    """
    warnings: List[str] = []
    
    # Extract query from inputs
    query = inputs_raw.get("query", "")
    date_range_days = inputs_raw.get("date_range_days", 730)
    min_results = inputs_raw.get("min_results", 15)
    
    if not query:
        warnings.append("No query provided, returning empty results")
        return {"papers": [], "stats": {"found": 0, "ranked": 0}}, warnings
    
    # Create agent and execute triage
    agent = LiteratureTriageAgent()
    request = TriageRequest(
        query=query,
        date_range_days=date_range_days,
        min_results=min_results
    )
    
    try:
        report = await agent.execute_triage(request)
        
        # Convert report to API response format
        all_papers = report.tier1_papers + report.tier2_papers + report.tier3_papers
        
        outputs = {
            "query": report.query,
            "executive_summary": report.executive_summary,
            "papers": [p.model_dump() for p in all_papers],
            "tier1_count": len(report.tier1_papers),
            "tier2_count": len(report.tier2_papers),
            "tier3_count": len(report.tier3_papers),
            "stats": {
                "found": report.papers_found,
                "ranked": report.papers_ranked
            },
            "markdown_report": agent.format_report_markdown(report)
        }
        
        return outputs, warnings
        
    except Exception as e:
        warnings.append(f"Error during triage: {str(e)}")
        return {"papers": [], "stats": {"found": 0, "ranked": 0}, "error": str(e)}, warnings


def run_lit_triage(inputs_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Synchronous wrapper for async AI triage
    
    Falls back to legacy rule-based triage if AI mode is not requested
    """
    # Check if AI mode is requested
    use_ai = inputs_raw.get("use_ai", True)
    
    if use_ai:
        # Run AI-powered triage
        return asyncio.run(run_lit_triage_ai(inputs_raw))
    else:
        # Legacy rule-based triage (kept for compatibility)
        return run_lit_triage_legacy(inputs_raw)


def run_lit_triage_legacy(inputs_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Legacy rule-based triage (original implementation)
    
    Kept for backward compatibility and testing
    """
    import hashlib
    from app.schemas import Paper
    
    def _norm(s: str) -> str:
        return " ".join((s or "").strip().lower().split())

    def _paper_key(p: Paper) -> str:
        if p.doi:
            return f"doi:{_norm(p.doi)}"
        if p.pmid:
            return f"pmid:{_norm(p.pmid)}"
        title = _norm(p.title or "")
        return "title:" + hashlib.sha256(title.encode("utf-8")).hexdigest()

    def _contains_any(text: str, keywords: List[str]) -> bool:
        t = _norm(text)
        for kw in keywords:
            if _norm(kw) and _norm(kw) in t:
                return True
        return False

    inputs = LitTriageInputs.model_validate(inputs_raw)
    warnings: List[str] = []

    kept: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    seen = set()

    for p in inputs.papers:
        reason: List[str] = []

        if inputs.require_abstract and not (p.abstract and p.abstract.strip()):
            reason.append("missing_abstract")

        if inputs.exclude_keywords and _contains_any(
            (p.title or "") + " " + (p.abstract or ""), inputs.exclude_keywords
        ):
            reason.append("excluded_keyword_match")

        if inputs.include_keywords and _contains_any(
            (p.title or "") + " " + (p.abstract or ""), inputs.include_keywords
        ):
            reason.append("missing_include_keyword_match")

        if inputs.dedupe:
            k = _paper_key(p)
            if k in seen:
                reason.append("duplicate")
            else:
                seen.add(k)

        if reason:
            excluded.append({"paper": p.model_dump(), "reasons": reason})
        else:
            kept.append(p.model_dump())

    outputs = {
        "kept_papers": kept,
        "excluded_papers": excluded,
        "stats": {"kept": len(kept), "excluded": len(excluded), "input": len(inputs.papers)},
    }
    return outputs, warnings
