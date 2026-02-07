"""
Unit tests for BM25-lite reranking module.

Run: python -m pytest tests/test_bm25_lite.py -v
"""
from __future__ import annotations

import pytest
from agent.bm25_lite import bm25_rerank, _tokenize


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_empty(self):
        assert _tokenize("") == []

    def test_mixed_case(self):
        assert _tokenize("BM25 Scoring") == ["bm25", "scoring"]


class TestBm25Rerank:
    def _make_chunks(self, texts, scores=None):
        """Helper to build chunk dicts."""
        chunks = []
        for i, text in enumerate(texts):
            chunks.append({
                "id": f"chunk-{i}",
                "text": text,
                "score": scores[i] if scores else 1.0 - i * 0.1,
                "metadata": {"source": "test"},
            })
        return chunks

    def test_empty_chunks(self):
        result = bm25_rerank("query", [])
        assert result == []

    def test_empty_query(self):
        chunks = self._make_chunks(["hello world"])
        result = bm25_rerank("", chunks)
        assert len(result) == 1
        assert result[0]["metadata"]["bm25Score"] == 0.0

    def test_bm25_scores_injected(self):
        chunks = self._make_chunks(
            ["clinical trial drug efficacy", "unrelated text about weather"],
            scores=[0.9, 0.8],
        )
        result = bm25_rerank("clinical trial efficacy", chunks)

        for ch in result:
            assert "semanticScore" in ch["metadata"]
            assert "bm25Score" in ch["metadata"]

    def test_relevant_chunk_promoted(self):
        """A chunk with lower semantic score but high keyword match should be boosted."""
        chunks = self._make_chunks(
            [
                "general medical information overview",         # high semantic, low keyword
                "clinical trial drug efficacy randomized study", # lower semantic, high keyword
            ],
            scores=[0.95, 0.6],
        )
        result = bm25_rerank("clinical trial efficacy", chunks, semantic_weight=0.3)

        # The keyword-rich chunk should rank first with low semantic_weight
        assert result[0]["id"] == "chunk-1"

    def test_backward_compatible_score_field(self):
        chunks = self._make_chunks(["test document"], scores=[0.85])
        result = bm25_rerank("test", chunks)
        # score field still exists and is a float
        assert isinstance(result[0]["score"], float)

    def test_semantic_weight_one_preserves_order(self):
        """With semantic_weight=1.0, BM25 has no effect → order preserved."""
        chunks = self._make_chunks(
            ["alpha beta gamma", "delta epsilon zeta"],
            scores=[0.9, 0.5],
        )
        result = bm25_rerank("delta epsilon", chunks, semantic_weight=1.0)
        # Original order preserved (0.9 > 0.5)
        assert result[0]["id"] == "chunk-0"

    def test_semantic_weight_zero_pure_bm25(self):
        """With semantic_weight=0.0, only BM25 matters."""
        chunks = self._make_chunks(
            ["unrelated text", "exact query match exact query match"],
            scores=[0.99, 0.01],
        )
        result = bm25_rerank("exact query match", chunks, semantic_weight=0.0)
        assert result[0]["id"] == "chunk-1"

    def test_metadata_preserved(self):
        chunks = [
            {
                "id": "c1",
                "text": "some text",
                "score": 0.8,
                "metadata": {"source": "pubmed", "year": 2024},
            }
        ]
        result = bm25_rerank("text", chunks)
        assert result[0]["metadata"]["source"] == "pubmed"
        assert result[0]["metadata"]["year"] == 2024

    def test_sorted_descending(self):
        chunks = self._make_chunks(
            ["a b c d", "e f g h", "a b e f"],
            scores=[0.5, 0.5, 0.5],
        )
        result = bm25_rerank("a b", chunks)
        scores = [ch["score"] for ch in result]
        assert scores == sorted(scores, reverse=True)
