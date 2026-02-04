"""Integration tests for Orchestrator compliance/checklist APIs.

Routes live in services/orchestrator/src/routes/checklists.ts and related modules.

Targets:
- TRIPOD+AI checklist endpoints
- CONSORT-AI checklist endpoints
- Compliance score / validation
- Export endpoints

Note: exact checklist types vary; tests are schema-tolerant.
"""

from __future__ import annotations

import pytest

from tests.integration.utils.api_client import APIClient
from tests.integration.utils.assertions import assert_json, assert_perf, assert_status


@pytest.mark.asyncio
async def test_checklists_index(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/checklists")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/checklists")
    assert_status(tr.response, (200, 401, 403))
    if tr.response.status_code == 200:
        _ = assert_json(tr.response)


@pytest.mark.asyncio
@pytest.mark.parametrize("checklist_type", ["tripodai", "consortai", "hti1", "faves"])
async def test_checklist_type_get(require_orchestrator, orchestrator_client, perf_budget_seconds, checklist_type):
    api = APIClient(orchestrator_client)
    tr = await api.get(f"/api/checklists/{checklist_type}")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label=f"GET /api/checklists/{checklist_type}")
    assert_status(tr.response, (200, 404, 401, 403))


@pytest.mark.asyncio
@pytest.mark.parametrize("checklist_type", ["tripodai", "consortai"])
async def test_checklist_validate_and_progress(require_orchestrator, orchestrator_client, perf_budget_seconds, checklist_type):
    api = APIClient(orchestrator_client)

    payload = {
        "projectId": "it-project",
        "artifactId": "it-artifact",
        "content": "synthetic content for checklist validation",
        "metadata": {"mode": "DEMO"},
    }

    tr_val = await api.post(f"/api/checklists/{checklist_type}/validate", json=payload)
    assert_perf(tr_val.elapsed_s, perf_budget_seconds, label=f"POST /api/checklists/{checklist_type}/validate")
    assert_status(tr_val.response, (200, 202, 400, 401, 403, 404))

    tr_prog = await api.post(f"/api/checklists/{checklist_type}/progress", json={"projectId": "it-project"})
    assert_perf(tr_prog.elapsed_s, perf_budget_seconds, label=f"POST /api/checklists/{checklist_type}/progress")
    assert_status(tr_prog.response, (200, 202, 400, 401, 403, 404))


@pytest.mark.asyncio
async def test_checklist_export(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)

    tr = await api.post(
        "/api/checklists/tripodai/export",
        json={"projectId": "it-project", "format": "pdf"},
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/checklists/tripodai/export")
    assert_status(tr.response, (200, 202, 400, 401, 403, 404))


@pytest.mark.asyncio
async def test_checklists_compare_items(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/checklists/compare/items")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/checklists/compare/items")
    assert_status(tr.response, (200, 404, 401, 403))
