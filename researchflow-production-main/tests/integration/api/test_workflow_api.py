"""Integration tests for Orchestrator workflow APIs.

Targets (Orchestrator, Node/Express):
- /api/workflow/* (stage navigation + lifecycle)
- /api/workflows/* (workflow CRUD + versions)

These tests assume a running orchestrator at ORCHESTRATOR_URL (default http://localhost:3001).
"""

from __future__ import annotations

import asyncio

import pytest

from tests.integration.utils.api_client import APIClient
from tests.integration.utils.assertions import assert_json, assert_perf, assert_status
from tests.integration.utils.factories import stage_inputs_payload, workflow_create_payload, workflow_update_payload
from tests.integration.utils.helpers import gather_with_concurrency


@pytest.mark.asyncio
async def test_workflow_stages_list(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/workflow/stages")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/workflow/stages")
    assert_status(tr.response, 200)
    body = assert_json(tr.response)
    # tolerant shape: list or object with groups
    assert body is not None


@pytest.mark.asyncio
async def test_workflow_stage_group_get(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    # Discover a stage/group id from /api/workflow/stages
    tr = await api.get("/api/workflow/stages")
    assert_status(tr.response, 200)
    body = assert_json(tr.response)

    # best-effort: locate an id-like field
    group_id = None
    if isinstance(body, list) and body:
        group_id = body[0].get("id") or body[0].get("key")
    elif isinstance(body, dict):
        groups = body.get("groups") or body.get("stageGroups") or body.get("data")
        if isinstance(groups, list) and groups:
            group_id = groups[0].get("id") or groups[0].get("key")

    if not group_id:
        pytest.skip("No group id found in /api/workflow/stages response")

    tr2 = await api.get(f"/api/workflow/groups/{group_id}")
    assert_perf(tr2.elapsed_s, perf_budget_seconds, label="GET /api/workflow/groups/:id")
    assert_status(tr2.response, (200, 404))


@pytest.mark.asyncio
async def test_workflow_resume(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/workflow/resume")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/workflow/resume")
    assert_status(tr.response, (200, 204, 404))


@pytest.mark.asyncio
async def test_workflow_crud_happy_path(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)

    # Create
    tr_create = await api.post("/api/workflows", json=workflow_create_payload())
    assert_perf(tr_create.elapsed_s, perf_budget_seconds, label="POST /api/workflows")
    assert_status(tr_create.response, (200, 201, 400, 401, 403))

    if tr_create.response.status_code in (401, 403):
        pytest.skip("Workflow CRUD requires auth token in this environment")

    if tr_create.response.status_code == 400:
        pytest.skip("Workflow create rejected payload; adjust factories to match deployment schema")

    created = assert_json(tr_create.response)
    wf_id = created.get("id") or created.get("workflowId")
    if not wf_id:
        pytest.skip("Workflow create response did not include an id")

    # Read
    tr_get = await api.get(f"/api/workflows/{wf_id}")
    assert_perf(tr_get.elapsed_s, perf_budget_seconds, label="GET /api/workflows/:id")
    assert_status(tr_get.response, 200)

    # Update
    tr_put = await api.put(f"/api/workflows/{wf_id}", json=workflow_update_payload())
    assert_perf(tr_put.elapsed_s, perf_budget_seconds, label="PUT /api/workflows/:id")
    assert_status(tr_put.response, (200, 204))

    # Delete
    tr_del = await api.delete(f"/api/workflows/{wf_id}")
    assert_perf(tr_del.elapsed_s, perf_budget_seconds, label="DELETE /api/workflows/:id")
    assert_status(tr_del.response, (200, 204))


@pytest.mark.asyncio
async def test_workflow_templates(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/workflows/templates")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/workflows/templates")
    assert_status(tr.response, (200, 404))


@pytest.mark.asyncio
async def test_workflow_stage_inputs_and_execute_best_effort(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)

    # Best-effort discovery of a stageId
    tr = await api.get("/api/workflow/stages")
    assert_status(tr.response, 200)
    body = assert_json(tr.response)

    stage_id = None
    # Accept various shapes
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("stageId", "id") and isinstance(v, (str, int)):
                    yield str(v)
                yield from _walk(v)
        elif isinstance(obj, list):
            for it in obj:
                yield from _walk(it)

    for sid in _walk(body):
        stage_id = sid
        break

    if not stage_id:
        pytest.skip("No stageId discovered from /api/workflow/stages")

    tr_inputs = await api.post(f"/api/workflow/stages/{stage_id}/inputs", json=stage_inputs_payload())
    assert_perf(tr_inputs.elapsed_s, perf_budget_seconds, label="POST /api/workflow/stages/:stageId/inputs")
    assert_status(tr_inputs.response, (200, 201, 204, 400, 401, 403, 404))

    tr_exec = await api.post(f"/api/workflow/execute/{stage_id}", json={})
    assert_perf(tr_exec.elapsed_s, perf_budget_seconds, label="POST /api/workflow/execute/:stageId")
    assert_status(tr_exec.response, (200, 202, 400, 401, 403, 404, 409))


@pytest.mark.asyncio
async def test_concurrent_stage_inputs(require_orchestrator, orchestrator_client):
    api = APIClient(orchestrator_client)

    tr = await api.get("/api/workflow/stages")
    assert_status(tr.response, 200)
    body = assert_json(tr.response)

    stage_ids = []

    def _collect(obj):
        if isinstance(obj, dict):
            if isinstance(obj.get("stageId"), (str, int)):
                stage_ids.append(str(obj["stageId"]))
            if isinstance(obj.get("id"), (str, int)) and obj.get("type") in ("stage", "workflow-stage"):
                stage_ids.append(str(obj["id"]))
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for it in obj:
                _collect(it)

    _collect(body)
    stage_ids = list(dict.fromkeys(stage_ids))[:5]

    if not stage_ids:
        pytest.skip("No stage ids discovered for concurrency test")

    coros = [api.post(f"/api/workflow/stages/{sid}/inputs", json=stage_inputs_payload(inputs={"n": i})) for i, sid in enumerate(stage_ids)]
    results = await gather_with_concurrency(5, coros)

    # Ensure at least one succeeded or was auth-rejected (not 5xx)
    for trr in results:
        assert trr.response.status_code < 500
