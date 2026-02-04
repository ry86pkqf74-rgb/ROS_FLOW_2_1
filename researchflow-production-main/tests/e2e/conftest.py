"""
Pytest fixtures for E2E tests: API client, base URL, optional test database config.
Used by tests/e2e/test_api_endpoints.py and other Python E2E tests.
"""

import os
from typing import AsyncGenerator

import pytest
import httpx


def _orchestrator_base_url() -> str:
    """Base URL for orchestrator API (env ORCHESTRATOR_URL or default)."""
    return os.environ.get("ORCHESTRATOR_URL", "http://localhost:3001").rstrip("/")


@pytest.fixture
def orchestrator_base_url() -> str:
    """Base URL for the orchestrator API."""
    return _orchestrator_base_url()


@pytest.fixture
def database_url() -> str:
    """Postgres connection URL for tests (same as CI services)."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://ros:ros@localhost:5432/ros",
    )


@pytest.fixture
async def api_client(orchestrator_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for orchestrator API. Use for API contract tests."""
    async with httpx.AsyncClient(
        base_url=orchestrator_base_url,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client
