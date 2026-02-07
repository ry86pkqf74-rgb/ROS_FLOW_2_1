"""
Unit tests for agent-rag-retrieve impl (run_sync / run_stream).

Run: python -m pytest tests/test_impl.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from agent.chroma_client import ChromaHit


@pytest.fixture
def _mock_chroma():
    """Patch chroma_query to return predictable hits."""
    hits = [
        ChromaHit(
            id=f"hit-{i}",
            document=f"document text about clinical trials number {i}",
            score=round(1.0 - i * 0.05, 4),
            distance=round(i * 0.05, 4),
            metadata={"doc_id": f"doc-{i}", "source": "test"},
        )
        for i in range(10)
    ]
    with patch("agent.impl.chroma_query", new_callable=AsyncMock, return_value=hits):
        yield hits


@pytest.mark.asyncio
async def test_run_sync_basic(_mock_chroma):
    from agent.impl import run_sync

    result = await run_sync({
        "request_id": "test-001",
        "task_type": "RAG_RETRIEVE",
        "inputs": {"query_text": "clinical trials"},
    })

    assert result["status"] == "ok"
    assert result["request_id"] == "test-001"
    assert result["outputs"]["count"] > 0

    chunks = result["outputs"]["chunks"]
    assert len(chunks) > 0

    # Check BM25 scores are present
    for ch in chunks:
        assert "semanticScore" in ch["metadata"]
        assert "bm25Score" in ch["metadata"]

    # Check retrieval trace
    trace = result["outputs"]["retrieval_trace"]
    assert "semantic" in trace["stages"]
    assert "bm25" in trace["stages"]


@pytest.mark.asyncio
async def test_run_sync_missing_query():
    from agent.impl import run_sync

    result = await run_sync({
        "request_id": "test-002",
        "task_type": "RAG_RETRIEVE",
        "inputs": {},
    })

    assert result["status"] == "error"
    assert "query_text" in result["outputs"]["error"]


@pytest.mark.asyncio
async def test_run_sync_chroma_failure():
    from agent.impl import run_sync

    with patch(
        "agent.impl.chroma_query",
        new_callable=AsyncMock,
        side_effect=ConnectionError("ChromaDB unreachable"),
    ):
        result = await run_sync({
            "request_id": "test-003",
            "task_type": "RAG_RETRIEVE",
            "inputs": {"query_text": "test query"},
        })

    assert result["status"] == "degraded"
    assert result["outputs"]["count"] == 0


@pytest.mark.asyncio
async def test_run_stream_yields_events(_mock_chroma):
    from agent.impl import run_stream

    events = []
    async for evt in run_stream({
        "request_id": "test-004",
        "task_type": "RAG_RETRIEVE",
        "inputs": {"query_text": "clinical trials"},
    }):
        events.append(evt)

    types = [e["type"] for e in events]
    assert "status" in types
    assert "final" in types

    final = [e for e in events if e["type"] == "final"][0]
    assert final["status"] == "ok"
    assert final["outputs"]["count"] > 0


@pytest.mark.asyncio
async def test_semantic_weight_parameter(_mock_chroma):
    from agent.impl import run_sync

    result = await run_sync({
        "request_id": "test-005",
        "task_type": "RAG_RETRIEVE",
        "inputs": {
            "query_text": "clinical trials",
            "semantic_weight": 0.8,
        },
    })

    assert result["status"] == "ok"
    assert result["provenance"]["semantic_weight"] == 0.8
