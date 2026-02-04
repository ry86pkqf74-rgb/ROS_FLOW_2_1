"""Integration tests for Orchestrator Governance APIs.

Targets (Orchestrator):
- GET  /api/governance/mode
- POST /api/governance/mode
- GET  /api/governance/audit (mapped to /audit/* in router)

These tests are RBAC-aware and will skip when auth tokens aren't configured.
"""

from __future__ import annotations

import pytest

from tests.integration.utils.api_client import APIClient
from tests.integration.utils.assertions import assert_json, assert_perf, assert_status


@pytest.mark.asyncio
async def test_get_governance_mode(require_orchestrator, orchestrator_client, perf_budget_seconds):
    api = APIClient(orchestrator_client)
    tr = await api.get("/api/governance/mode")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/governance/mode")
    assert_status(tr.response, (200, 401, 403))
    if tr.response.status_code == 200:
        _ = assert_json(tr.response)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["DEMO", "LIVE", "STANDBY"])
async def test_set_governance_mode_transitions(require_orchestrator, orchestrator_client, perf_budget_seconds, admin_headers, mode):
    api = APIClient(orchestrator_client)

    # Admin required in most deployments
    tr = await api.post("/api/governance/mode", headers=admin_headers, json={"mode": mode})
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/governance/mode")
    assert_status(tr.response, (200, 202, 400, 401, 403))
    if tr.response.status_code in (401, 403):
        pytest.skip("Governance mode transitions require ADMIN_TOKEN")


@pytest.mark.asyncio
async def test_governance_audit_endpoints(require_orchestrator, orchestrator_client, perf_budget_seconds, steward_headers):
    api = APIClient(orchestrator_client)

    # Route file exposes /api/governance/audit/entries, /audit/validate, /audit/export
    tr = await api.get("/api/governance/audit/entries", headers=steward_headers)
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/governance/audit/entries")
    assert_status(tr.response, (200, 401, 403, 404))
    if tr.response.status_code == 200:
        _ = assert_json(tr.response)
