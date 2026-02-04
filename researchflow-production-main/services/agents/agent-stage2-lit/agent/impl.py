import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

# Use our pure Entrez client instead of worker agents
from agent.pubmed_client import PubMedClient


def _as_str_list(x: Any, max_items: int) -> List[str]:
    if not x:
        return []
    if isinstance(x, str):
        return [x.strip()][:max_items]
    if isinstance(x, list):
        out = []
        for item in x:
            if item is None:
                continue
            s = str(item).strip()
            if s:
                out.append(s)
            if len(out) >= max_items:
                break
        return out
    return [str(x).strip()][:max_items]


def _clamp_int(x: Any, default: int, lo: int, hi: int) -> int:
    try:
        v = int(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


def _normalize_year_range(obj: Any) -> Tuple[Optional[int], Optional[int]]:
    if not isinstance(obj, dict):
        return None, None
    y_from = obj.get("from")
    y_to = obj.get("to")
    try:
        y_from = int(y_from) if y_from is not None else None
    except Exception:
        y_from = None
    try:
        y_to = int(y_to) if y_to is not None else None
    except Exception:
        y_to = None
    if y_from is not None and (y_from < 1900 or y_from > 2100):
        y_from = None
    if y_to is not None and (y_to < 1900 or y_to > 2100):
        y_to = None
    if y_from is not None and y_to is not None and y_from > y_to:
        y_from, y_to = y_to, y_from
    return y_from, y_to


MAX_QUERY_CHARS = 900
MAX_MESH_TERMS = 12
MAX_INCLUDE_KW = 20
MAX_EXCLUDE_KW = 12
MAX_STUDY_TYPES = 8

PUBMED_STUDYTYPE_MAP = {
    "clinical_trial": '"clinical trial"[Publication Type]',
    "randomized_controlled_trial": '"randomized controlled trial"[Publication Type]',
    "cohort_study": '"cohort studies"[MeSH Terms]',
    "case_control_study": '"case-control studies"[MeSH Terms]',
    "cross_sectional_study": '"cross-sectional studies"[MeSH Terms]',
    "systematic_review": '"systematic review"[Publication Type]',
    "meta_analysis": '"meta-analysis"[Publication Type]',
    "case_report": '"case reports"[Publication Type]',
    "observational_study": '"observational study"[Publication Type]',
    "review": '"review"[Publication Type]',
}


def _quote_term(term: str) -> str:
    term = term.strip().replace('"', '\\"')
    return f'"{term}"'


def build_pubmed_query(
    research_question: str,
    query_override: Optional[str],
    mesh_terms: List[str],
    include_keywords: List[str],
    exclude_keywords: List[str],
    year_from: Optional[int],
    year_to: Optional[int],
    study_types: List[str],
) -> str:
    parts: List[str] = []

    base = (query_override or research_question or "").strip()
    if base:
        parts.append(base)

    mesh_terms = [m for m in mesh_terms if m][:MAX_MESH_TERMS]
    if mesh_terms:
        mesh_q = " OR ".join([f'{_quote_term(m)}[MeSH Terms]' for m in mesh_terms])
        parts.append(f"({mesh_q})")

    include_keywords = [k for k in include_keywords if k][:MAX_INCLUDE_KW]
    if include_keywords:
        kw_q = " OR ".join([f'{_quote_term(k)}[Title/Abstract]' for k in include_keywords])
        parts.append(f"({kw_q})")

    st_filters = []
    for st in study_types[:MAX_STUDY_TYPES]:
        mapped = PUBMED_STUDYTYPE_MAP.get(st)
        if mapped:
            st_filters.append(mapped)
    if st_filters:
        parts.append(f"({ ' OR '.join(st_filters) })")

    if year_from or year_to:
        y1 = year_from if year_from else 1900
        y2 = year_to if year_to else 2100
        parts.append(f'("{y1}"[dp] : "{y2}"[dp])')

    exclude_keywords = [k for k in exclude_keywords if k][:MAX_EXCLUDE_KW]
    if exclude_keywords:
        ex_q = " OR ".join([f'{_quote_term(k)}[Title/Abstract]' for k in exclude_keywords])
        parts.append(f"NOT ({ex_q})")

    q = " AND ".join([p for p in parts if p])
    if len(q) <= MAX_QUERY_CHARS:
        return q

    # Trim: keep base + mesh + year + small keyword set
    safe_parts = [base] if base else []
    if mesh_terms:
        mesh_q = " OR ".join([f'{_quote_term(m)}[MeSH Terms]' for m in mesh_terms[:8]])
        safe_parts.append(f"({mesh_q})")
    if year_from or year_to:
        y1 = year_from if year_from else 1900
        y2 = year_to if year_to else 2100
        safe_parts.append(f'("{y1}"[dp] : "{y2}"[dp])')
    if include_keywords:
        kw_q = " OR ".join([f'{_quote_term(k)}[Title/Abstract]' for k in include_keywords[:8]])
        safe_parts.append(f"({kw_q})")

    q2 = " AND ".join([p for p in safe_parts if p])
    return q2[:MAX_QUERY_CHARS]


def normalize_stage2_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    inputs = payload.get("inputs") or {}
    research_question = str(inputs.get("research_question") or payload.get("research_question") or "").strip()
    query_override = inputs.get("query")
    query_override = str(query_override).strip() if query_override else None

    databases = _as_str_list(inputs.get("databases"), max_items=4) or ["pubmed"]
    max_results = _clamp_int(inputs.get("max_results"), default=25, lo=1, hi=200)
    language = str(inputs.get("language") or "en").strip()[:10]
    require_abstract = bool(inputs.get("require_abstract", True))
    dedupe = bool(inputs.get("dedupe", True))

    mesh_terms = _as_str_list(inputs.get("mesh_terms"), max_items=MAX_MESH_TERMS)
    include_keywords = _as_str_list(inputs.get("include_keywords"), max_items=MAX_INCLUDE_KW)
    exclude_keywords = _as_str_list(inputs.get("exclude_keywords"), max_items=MAX_EXCLUDE_KW)
    year_from, year_to = _normalize_year_range(inputs.get("year_range"))
    study_types = _as_str_list(inputs.get("study_types"), max_items=MAX_STUDY_TYPES)

    pubmed_query = build_pubmed_query(
        research_question=research_question,
        query_override=query_override,
        mesh_terms=mesh_terms,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
        year_from=year_from,
        year_to=year_to,
        study_types=study_types,
    )

    return {
        "research_question": research_question,
        "query_override": query_override,
        "databases": databases,
        "max_results": max_results,
        "language": language,
        "mesh_terms": mesh_terms,
        "include_keywords": include_keywords,
        "exclude_keywords": exclude_keywords,
        "year_from": year_from,
        "year_to": year_to,
        "study_types": study_types,
        "require_abstract": require_abstract,
        "dedupe": dedupe,
        "pubmed_query": pubmed_query,
    }


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    started = time.time()
    request_id = payload.get("request_id", "unknown")

    norm = normalize_stage2_inputs(payload)

    if not norm["research_question"] and not norm["query_override"]:
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {"error": "Missing research_question (or inputs.query)."},
            "artifacts": [],
            "provenance": {},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
        }

    client = PubMedClient()
    papers = []
    try:
        papers = await client.search_pubmed(query=norm["pubmed_query"], max_results=norm["max_results"])
    except Exception as e:
        return {
            "status": "degraded",
            "request_id": request_id,
            "outputs": {
                "normalized_inputs": norm,
                "pubmed_query": norm["pubmed_query"],
                "papers": [],
                "warning": f"PubMed search failed: {e}",
            },
            "artifacts": [],
            "provenance": {"databases_used": ["pubmed"]},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
        }

    duration_ms = int((time.time() - started) * 1000)
    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": {
            "normalized_inputs": norm,
            "pubmed_query": norm["pubmed_query"],
            "papers": papers,
            "count": len(papers),
        },
        "artifacts": [],
        "provenance": {"databases_used": ["pubmed"]},
        "usage": {"duration_ms": duration_ms, "input_tokens": None, "output_tokens": None},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    request_id = payload.get("request_id", "unknown")

    yield {"type": "status", "request_id": request_id, "step": "normalize_inputs", "progress": 10}

    norm = normalize_stage2_inputs(payload)

    yield {"type": "status", "request_id": request_id, "step": "build_pubmed_query", "progress": 25, "pubmed_query": norm["pubmed_query"]}

    yield {"type": "status", "request_id": request_id, "step": "search_pubmed", "progress": 50, "max_results": norm["max_results"]}

    result = await run_sync(payload)

    yield {"type": "status", "request_id": request_id, "step": "finalize", "progress": 90}

    yield {"type": "final", **result}
