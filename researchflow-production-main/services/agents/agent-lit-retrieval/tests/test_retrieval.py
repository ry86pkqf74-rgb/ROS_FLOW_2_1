"""Unit tests for run_lit_retrieval."""
from __future__ import annotations

import pytest

from app.retrieval import DEMO_PAPERS, run_lit_retrieval


def test_demo_mode_returns_fixture_papers() -> None:
    papers, warnings = run_lit_retrieval(
        {"query": "anything", "max_results": 5},
        mode="DEMO",
    )
    assert len(papers) <= 5
    assert len(papers) <= len(DEMO_PAPERS)
    assert len(warnings) == 0
    for p in papers:
        assert "title" in p
        assert "source" in p
        assert p["source"] == "pubmed"


def test_demo_override_returns_fixtures() -> None:
    papers, warnings = run_lit_retrieval(
        {"query": "test", "max_results": 1},
        demo_override=True,
    )
    assert len(papers) == 1
    assert papers[0]["title"]
    assert len(warnings) == 0


def test_invalid_inputs_raises() -> None:
    with pytest.raises(Exception):  # pydantic ValidationError
        run_lit_retrieval({"query": ""})
    with pytest.raises(Exception):
        run_lit_retrieval({"query": "x", "max_results": 300})


def test_normalize_paper_keys() -> None:
    papers, _ = run_lit_retrieval({"query": "x", "max_results": 2}, demo_override=True)
    for p in papers:
        for k in ["title", "abstract", "authors", "year", "journal", "doi", "pmid", "source", "url"]:
            assert k in p
