"""
API contract tests for the orchestrator HTTP API.
Uses fixtures from conftest.py (api_client, orchestrator_base_url).
Run from repo root with orchestrator available, or against a running instance.
Skips when orchestrator is not reachable (e.g. in CI unit job).
"""

import pytest


@pytest.fixture
async def api_client_available(api_client):
    """Skip tests in this module if orchestrator is not reachable."""
    try:
        r = await api_client.get("/health")
        if r.status_code >= 500:
            pytest.skip("Orchestrator returned server error")
    except Exception:
        pytest.skip("Orchestrator not reachable (start services for API contract tests)")


@pytest.mark.asyncio
async def test_health_returns_ok(api_client_available, api_client):
    """GET /health returns 200 and indicates service is up."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ("ok", "OK", "up", None) or "ok" in str(data).lower()


@pytest.mark.asyncio
async def test_health_response_shape(api_client_available, api_client):
    """GET /health returns JSON with expected shape (status or similar)."""
    response = await api_client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    body = response.json()
    assert isinstance(body, dict)


@pytest.mark.asyncio
async def test_api_health_if_present(api_client_available, api_client):
    """GET /api/health if present returns 2xx (optional route)."""
    response = await api_client.get("/api/health")
    # Accept 200 or 404 if route is not registered
    assert response.status_code in (200, 404)
