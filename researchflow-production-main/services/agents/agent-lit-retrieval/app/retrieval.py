from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from app.schemas import LitRetrievalInputs

logger = logging.getLogger(__name__)

# Fixture papers for DEMO mode (PHI-safe, no user input)
DEMO_PAPERS: List[Dict[str, Any]] = [
    {
        "title": "Example systematic review of interventions (DEMO)",
        "abstract": "This is a placeholder abstract for DEMO mode.",
        "authors": ["Demo Author"],
        "year": 2024,
        "journal": "Demo Journal",
        "doi": None,
        "pmid": "00000001",
        "source": "pubmed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/00000001/",
    },
    {
        "title": "Second example paper for DEMO mode",
        "abstract": "Another fixture for offline testing.",
        "authors": ["Another Author"],
        "year": 2023,
        "journal": "Example Journal",
        "doi": None,
        "pmid": "00000002",
        "source": "pubmed",
        "url": "https://pubmed.ncbi.nlm.nih.gov/00000002/",
    },
]


def _normalize_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure paper dict has standard keys for contract."""
    out: Dict[str, Any] = {}
    for k in ["title", "abstract", "authors", "year", "journal", "doi", "pmid", "source", "url"]:
        out[k] = paper.get(k)
    return out


async def _run_pubmed(query: str, max_results: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    from app.pubmed_client import PubMedClient

    client = PubMedClient()
    try:
        papers = await client.search_pubmed(query=query, max_results=max_results)
        return [_normalize_paper(p) for p in papers], []
    except Exception as e:
        logger.exception("PubMed search failed")
        return [], [f"PubMed search failed: {e}"]


def run_lit_retrieval(
    inputs_raw: Dict[str, Any],
    mode: str | None = None,
    demo_override: bool = False,
    timeout_seconds: int = 60,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Run deterministic literature retrieval. DEMO mode or LIT_RETRIEVAL_DEMO=true
    returns fixture papers without calling NCBI. timeout_seconds caps the PubMed call.
    """
    inputs = LitRetrievalInputs.model_validate(inputs_raw)
    warnings: List[str] = []

    if mode == "DEMO" or demo_override:
        n = min(inputs.max_results, len(DEMO_PAPERS))
        return [DEMO_PAPERS[i].copy() for i in range(n)], warnings

    # Run async PubMed client with timeout to avoid hung requests
    try:
        papers, pubmed_warnings = asyncio.run(
            asyncio.wait_for(
                _run_pubmed(query=inputs.query, max_results=inputs.max_results),
                timeout=float(timeout_seconds),
            )
        )
        warnings.extend(pubmed_warnings)
    except asyncio.TimeoutError:
        logger.warning("PubMed retrieval timed out after %s seconds", timeout_seconds)
        papers = []
        warnings.append(f"Retrieval timed out after {timeout_seconds}s")

    # Optional: Semantic Scholar stub when in databases (future)
    if "semantic_scholar" in (inputs.databases or []):
        # Stub: no-op for now, could merge real results later
        pass

    return papers, warnings
