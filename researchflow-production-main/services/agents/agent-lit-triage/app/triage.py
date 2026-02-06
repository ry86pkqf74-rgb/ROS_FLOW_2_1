from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Tuple
from app.schemas import LitTriageInputs, Paper


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


def run_lit_triage(inputs_raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
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

        if inputs.include_keywords and not _contains_any(
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
