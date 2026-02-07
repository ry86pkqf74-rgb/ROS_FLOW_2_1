"""Unit tests for BM25-lite tokenize and score_candidates."""
from __future__ import annotations

import pytest

from agent.bm25_lite import score_candidates, tokenize


def test_tokenize_basic() -> None:
    tokens = tokenize("Hello World  foo")
    assert tokens == ["hello", "world", "foo"]


def test_tokenize_empty() -> None:
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_tokenize_lowercase() -> None:
    assert tokenize("Query Terms") == ["query", "terms"]


def test_score_candidates_empty() -> None:
    assert score_candidates("query", []) == {}


def test_score_candidates_matching_doc_scores_higher() -> None:
    """Doc containing query terms should get higher BM25 than one that does not."""
    candidates = [
        ("id1", "stroke prevention anticoagulants atrial fibrillation"),
        ("id2", "unrelated content about weather"),
    ]
    query = "stroke prevention anticoagulants"
    scores = score_candidates(query, candidates)
    assert scores["id1"] > scores["id2"]
    assert scores["id2"] == 0.0


def test_score_candidates_multiple_docs() -> None:
    """Multiple docs with varying term overlap; ordering by score is sensible."""
    candidates = [
        ("a", "apixaban reduces stroke risk in atrial fibrillation"),
        ("b", "apixaban stroke risk"),
        ("c", "random other text"),
    ]
    query = "apixaban stroke"
    scores = score_candidates(query, candidates)
    assert scores["a"] > 0
    assert scores["b"] > 0
    assert scores["c"] == 0.0
    assert scores["a"] >= scores["b"]


def test_score_candidates_single_doc() -> None:
    candidates = [("only", "the quick brown fox")]
    scores = score_candidates("quick fox", candidates)
    assert "only" in scores
    assert scores["only"] > 0
