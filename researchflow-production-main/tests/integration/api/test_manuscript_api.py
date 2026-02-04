"""Integration tests for Worker manuscript APIs (FastAPI).

Targets (Worker):
- POST /api/manuscript/generate
- POST /api/manuscript/generate/section
- GET  /api/manuscript/{id}/status
- GET  /api/manuscript/{id}/download/{format}

These tests run against WORKER_URL (default http://localhost:8000).
"""

from __future__ import annotations

import uuid

import pytest

from tests.integration.utils.api_client import APIClient
from tests.integration.utils.assertions import assert_json, assert_perf, assert_status
from tests.integration.utils.helpers import poll


@pytest.mark.asyncio
async def test_generate_full_manuscript(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    manuscript_id = str(uuid.uuid4())

    tr = await api.post(
        "/api/manuscript/generate",
        json={
            "manuscript_id": manuscript_id,
            "title": "Integration Test Manuscript",
            "data": {"population": "synthetic", "notes": "integration"},
            "journal_style": "JAMA",
            "citation_style": "Vancouver",
        },
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/manuscript/generate")
    assert_status(tr.response, (200, 202))
    body = assert_json(tr.response)
    assert body.get("manuscript_id")

    mid = body["manuscript_id"]

    # Poll status until running|completed
    async def _get_status():
        return await api.get(f"/api/manuscript/{mid}/status")

    last = await poll(_get_status, timeout_s=30, interval_s=0.5)
    assert_status(last.response, 200)
    status = assert_json(last.response)
    assert status.get("manuscript_id") == mid


@pytest.mark.asyncio
async def test_generate_section(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)

    tr = await api.post(
        "/api/manuscript/generate/section",
        json={
            "section": "abstract",
            "title": "Section Test",
            "data": {"population": "synthetic"},
            "journal_style": "JAMA",
            "citation_style": "Vancouver",
        },
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/manuscript/generate/section")
    assert_status(tr.response, (200, 202))
    body = assert_json(tr.response)
    assert body.get("manuscript_id")


@pytest.mark.asyncio
@pytest.mark.parametrize("fmt,expected_ct", [("docx", "application/vnd.openxmlformats-officedocument"), ("pdf", "application/pdf"), ("latex", "application/x-latex"), ("markdown", "text/markdown")])
async def test_download_formats(require_worker, worker_client, perf_budget_seconds, fmt, expected_ct):
    api = APIClient(worker_client)

    # Create a manuscript first
    tr = await api.post(
        "/api/manuscript/generate",
        json={"title": "Download Test", "data": {"population": "synthetic"}},
    )
    assert_status(tr.response, (200, 202))
    mid = assert_json(tr.response)["manuscript_id"]

    # Wait until completed or at least generated artifacts
    async def _status():
        return await api.get(f"/api/manuscript/{mid}/status")

    await poll(_status, timeout_s=30, interval_s=0.5)

    tr_dl = await api.get(f"/api/manuscript/{mid}/download/{fmt}")
    assert_perf(tr_dl.elapsed_s, perf_budget_seconds, label=f"GET /api/manuscript/{{id}}/download/{fmt}")
    assert_status(tr_dl.response, (200, 404))
    if tr_dl.response.status_code == 200:
        ct = tr_dl.response.headers.get("content-type", "")
        assert expected_ct in ct
        assert len(tr_dl.response.content) > 0
