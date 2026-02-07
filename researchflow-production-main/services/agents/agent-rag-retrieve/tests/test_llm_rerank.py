"""Tests for LLM rerank functionality."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from agent.llm_rerank import (
    _build_rerank_prompt,
    _parse_ranked_ids,
    llm_rerank,
)


class TestParseRankedIds:
    """Unit tests for _parse_ranked_ids."""

    def test_parses_valid_json_array(self) -> None:
        content = '["chunk-1", "chunk-2", "chunk-3"]'
        result = _parse_ranked_ids(content)
        assert result == ["chunk-1", "chunk-2", "chunk-3"]

    def test_parses_json_with_whitespace(self) -> None:
        content = '  ["a", "b", "c"]  '
        result = _parse_ranked_ids(content)
        assert result == ["a", "b", "c"]

    def test_parses_json_in_markdown_fence(self) -> None:
        content = '```json\n["chunk-1", "chunk-2"]\n```'
        result = _parse_ranked_ids(content)
        assert result == ["chunk-1", "chunk-2"]

    def test_parses_json_in_plain_fence(self) -> None:
        content = '```\n["x", "y"]\n```'
        result = _parse_ranked_ids(content)
        assert result == ["x", "y"]

    def test_extracts_array_from_mixed_content(self) -> None:
        content = 'Here are the ranked IDs: ["id1", "id2", "id3"]'
        result = _parse_ranked_ids(content)
        assert result == ["id1", "id2", "id3"]

    def test_returns_empty_for_empty_string(self) -> None:
        assert _parse_ranked_ids("") == []

    def test_returns_empty_for_invalid_json(self) -> None:
        assert _parse_ranked_ids("not json at all") == []

    def test_filters_non_string_items(self) -> None:
        content = '["valid", 123, "also-valid", null]'
        result = _parse_ranked_ids(content)
        assert result == ["valid", "also-valid"]


class TestBuildRerankPrompt:
    """Unit tests for _build_rerank_prompt."""

    def test_includes_query_and_chunks(self) -> None:
        chunks = [
            {"id": "c1", "text": "First chunk content"},
            {"id": "c2", "text": "Second chunk content"},
        ]
        prompt = _build_rerank_prompt("test query", chunks, top_k=5)

        assert "test query" in prompt
        assert "[c1]" in prompt
        assert "First chunk content" in prompt
        assert "[c2]" in prompt
        assert "Second chunk content" in prompt
        assert "5" in prompt  # top_k in instructions

    def test_truncates_long_text(self) -> None:
        chunks = [{"id": "long", "text": "x" * 3000}]
        prompt = _build_rerank_prompt("q", chunks, top_k=10)

        # Text should be truncated to 1500 chars (plus ~500 chars template)
        # Verify truncation occurred: 3000 chars input -> 1500 chars in prompt
        assert "x" * 1500 in prompt
        assert "x" * 1501 not in prompt


class TestLlmRerank:
    """Integration-style tests for llm_rerank (with mocked AI Bridge)."""

    @pytest.mark.asyncio
    async def test_returns_chunks_as_is_when_empty(self) -> None:
        result = await llm_rerank("query", [], top_k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_reorders_chunks_based_on_llm_response(self) -> None:
        chunks = [
            {"id": "a", "text": "A text", "score": 0.9, "metadata": {}},
            {"id": "b", "text": "B text", "score": 0.8, "metadata": {}},
            {"id": "c", "text": "C text", "score": 0.7, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM says: c is most relevant, then a, then b
            mock_invoke.return_value = ["c", "a", "b"]

            result = await llm_rerank("query", chunks, top_k=3)

        assert len(result) == 3
        assert result[0]["id"] == "c"
        assert result[1]["id"] == "a"
        assert result[2]["id"] == "b"

        # Check llmRank is set
        assert result[0]["metadata"]["llmRank"] == 1
        assert result[1]["metadata"]["llmRank"] == 2
        assert result[2]["metadata"]["llmRank"] == 3

    @pytest.mark.asyncio
    async def test_ignores_hallucinated_ids(self) -> None:
        chunks = [
            {"id": "real-1", "text": "Real", "score": 0.9, "metadata": {}},
            {"id": "real-2", "text": "Also real", "score": 0.8, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM returns a hallucinated ID
            mock_invoke.return_value = ["fake-id", "real-2", "real-1"]

            result = await llm_rerank("query", chunks, top_k=5)

        # Only real IDs are included
        assert len(result) == 2
        assert result[0]["id"] == "real-2"
        assert result[1]["id"] == "real-1"

    @pytest.mark.asyncio
    async def test_respects_top_k_limit(self) -> None:
        chunks = [
            {"id": f"c{i}", "text": f"Chunk {i}", "score": 0.9 - i * 0.1, "metadata": {}}
            for i in range(10)
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            mock_invoke.return_value = [f"c{i}" for i in range(10)]

            result = await llm_rerank("query", chunks, top_k=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_falls_back_on_bridge_failure(self) -> None:
        chunks = [
            {"id": "a", "text": "A", "score": 0.9, "metadata": {}},
            {"id": "b", "text": "B", "score": 0.8, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            mock_invoke.side_effect = Exception("Bridge unavailable")

            result = await llm_rerank("query", chunks, top_k=5)

        # Falls back to original order
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"
        # llmRank should be None
        assert result[0]["metadata"]["llmRank"] is None

    @pytest.mark.asyncio
    async def test_handles_duplicate_ids_in_response(self) -> None:
        chunks = [
            {"id": "a", "text": "A", "score": 0.9, "metadata": {}},
            {"id": "b", "text": "B", "score": 0.8, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM returns duplicates
            mock_invoke.return_value = ["a", "a", "b", "b"]

            result = await llm_rerank("query", chunks, top_k=5)

        # Duplicates are deduplicated
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"

    @pytest.mark.asyncio
    async def test_appends_missing_chunks_when_llm_returns_partial(self) -> None:
        chunks = [
            {"id": "a", "text": "A", "score": 0.9, "metadata": {}},
            {"id": "b", "text": "B", "score": 0.8, "metadata": {}},
            {"id": "c", "text": "C", "score": 0.7, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM only returns one ID
            mock_invoke.return_value = ["b"]

            result = await llm_rerank("query", chunks, top_k=5)

        # b is first (from LLM), then a and c appended
        assert len(result) == 3
        assert result[0]["id"] == "b"
        assert result[0]["metadata"]["llmRank"] == 1
        # Remaining chunks have llmRank = None
        assert result[1]["metadata"]["llmRank"] is None
        assert result[2]["metadata"]["llmRank"] is None


class TestCandidateSetIntegrity:
    """Tests that prove output chunk IDs are always a subset of input chunk IDs."""

    @pytest.mark.asyncio
    async def test_output_ids_subset_of_input_ids_on_success(self) -> None:
        """Output chunk IDs must be a subset of input chunk IDs when LLM succeeds."""
        input_chunks = [
            {"id": "chunk-alpha", "text": "Alpha content", "score": 0.9, "metadata": {}},
            {"id": "chunk-beta", "text": "Beta content", "score": 0.8, "metadata": {}},
            {"id": "chunk-gamma", "text": "Gamma content", "score": 0.7, "metadata": {}},
        ]
        input_ids = {ch["id"] for ch in input_chunks}

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM returns valid reordering
            mock_invoke.return_value = ["chunk-gamma", "chunk-alpha", "chunk-beta"]

            result = await llm_rerank("test query", input_chunks, top_k=10)

        output_ids = {ch["id"] for ch in result}
        assert output_ids <= input_ids, f"Output IDs {output_ids} not subset of input IDs {input_ids}"

    @pytest.mark.asyncio
    async def test_output_ids_subset_of_input_ids_on_hallucination(self) -> None:
        """Even when LLM hallucinates IDs, output must only contain valid input IDs."""
        input_chunks = [
            {"id": "valid-1", "text": "Valid one", "score": 0.9, "metadata": {}},
            {"id": "valid-2", "text": "Valid two", "score": 0.8, "metadata": {}},
        ]
        input_ids = {ch["id"] for ch in input_chunks}

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM hallucinates IDs that don't exist
            mock_invoke.return_value = [
                "hallucinated-id-1",
                "valid-2",
                "hallucinated-id-2",
                "totally-fake",
                "valid-1",
            ]

            result = await llm_rerank("test query", input_chunks, top_k=10)

        output_ids = {ch["id"] for ch in result}
        assert output_ids <= input_ids, f"Hallucinated IDs leaked through: {output_ids - input_ids}"
        # Should still return both valid chunks
        assert "valid-1" in output_ids
        assert "valid-2" in output_ids

    @pytest.mark.asyncio
    async def test_output_ids_subset_of_input_ids_on_failure(self) -> None:
        """On LLM failure, output must still only contain valid input IDs."""
        input_chunks = [
            {"id": "fallback-a", "text": "A", "score": 0.9, "metadata": {}},
            {"id": "fallback-b", "text": "B", "score": 0.8, "metadata": {}},
        ]
        input_ids = {ch["id"] for ch in input_chunks}

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            mock_invoke.side_effect = ConnectionError("Network failure")

            result = await llm_rerank("test query", input_chunks, top_k=10)

        output_ids = {ch["id"] for ch in result}
        assert output_ids <= input_ids, f"Output IDs {output_ids} not subset of input IDs {input_ids}"


class TestStableOutputSchema:
    """Tests that prove output schema is stable regardless of rerank mode/outcome."""

    REQUIRED_CHUNK_KEYS = {"id", "text", "score", "metadata"}

    @pytest.mark.asyncio
    async def test_schema_stable_on_llm_success(self) -> None:
        """Chunk schema is stable when LLM rerank succeeds."""
        chunks = [
            {"id": "s1", "text": "Success chunk", "score": 0.9, "metadata": {"source": "test"}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            mock_invoke.return_value = ["s1"]

            result = await llm_rerank("query", chunks, top_k=5)

        assert len(result) == 1
        chunk = result[0]
        # Verify all required keys present
        assert self.REQUIRED_CHUNK_KEYS <= set(chunk.keys()), f"Missing keys: {self.REQUIRED_CHUNK_KEYS - set(chunk.keys())}"
        # Verify metadata has llmRank (integer when ranked)
        assert "llmRank" in chunk["metadata"]
        assert isinstance(chunk["metadata"]["llmRank"], int)

    @pytest.mark.asyncio
    async def test_schema_stable_on_llm_failure(self) -> None:
        """Chunk schema is stable when LLM rerank fails (fallback)."""
        chunks = [
            {"id": "f1", "text": "Fallback chunk", "score": 0.9, "metadata": {"source": "test"}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            mock_invoke.side_effect = TimeoutError("LLM timeout")

            result = await llm_rerank("query", chunks, top_k=5)

        assert len(result) == 1
        chunk = result[0]
        # Verify all required keys present
        assert self.REQUIRED_CHUNK_KEYS <= set(chunk.keys()), f"Missing keys: {self.REQUIRED_CHUNK_KEYS - set(chunk.keys())}"
        # Verify metadata has llmRank (None when fallback)
        assert "llmRank" in chunk["metadata"]
        assert chunk["metadata"]["llmRank"] is None

    @pytest.mark.asyncio
    async def test_schema_stable_on_partial_ranking(self) -> None:
        """Chunk schema is stable when LLM returns partial ranking."""
        chunks = [
            {"id": "p1", "text": "Partial 1", "score": 0.9, "metadata": {}},
            {"id": "p2", "text": "Partial 2", "score": 0.8, "metadata": {}},
            {"id": "p3", "text": "Partial 3", "score": 0.7, "metadata": {}},
        ]

        with patch("agent.llm_rerank._invoke_bridge_rerank") as mock_invoke:
            # LLM only ranks one chunk
            mock_invoke.return_value = ["p2"]

            result = await llm_rerank("query", chunks, top_k=5)

        assert len(result) == 3
        for chunk in result:
            # Verify all required keys present
            assert self.REQUIRED_CHUNK_KEYS <= set(chunk.keys())
            # Verify metadata has llmRank key
            assert "llmRank" in chunk["metadata"]
            # llmRank is either int (ranked) or None (unranked)
            rank = chunk["metadata"]["llmRank"]
            assert rank is None or isinstance(rank, int)

        # Ranked chunk has integer, others have None
        ranked_chunk = next(ch for ch in result if ch["id"] == "p2")
        unranked_chunks = [ch for ch in result if ch["id"] != "p2"]
        assert ranked_chunk["metadata"]["llmRank"] == 1
        for ch in unranked_chunks:
            assert ch["metadata"]["llmRank"] is None
