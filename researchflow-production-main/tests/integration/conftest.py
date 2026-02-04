"""Integration test fixtures.

These tests target TWO services:
- Orchestrator (Node/Express): default http://localhost:3001
- Worker (Python/FastAPI):     default http://localhost:8000

Tests are written to be runnable locally (docker-compose.test.yml) and to
skip gracefully when services are not reachable.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Dict, Optional

import httpx
import pytest


ORCHESTRATOR_BASE_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:3001").rstrip("/")
WORKER_BASE_URL = os.getenv("WORKER_URL", "http://localhost:8000").rstrip("/")

# Optional tokens (tests will skip auth-enforced endpoints if not provided)
RESEARCHER_TOKEN = os.getenv("RESEARCHER_TOKEN")
STEWARD_TOKEN = os.getenv("STEWARD_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def _headers_for(token: Optional[str]) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


async def _is_reachable(client: httpx.AsyncClient, path: str = "/health") -> bool:
    try:
        r = await client.get(path)
        return r.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def orchestrator_base_url() -> str:
    return ORCHESTRATOR_BASE_URL


@pytest.fixture(scope="session")
def worker_base_url() -> str:
    return WORKER_BASE_URL


@pytest.fixture(scope="session")
def event_loop():
    # pytest-asyncio legacy compatibility
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def orchestrator_client(orchestrator_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        base_url=orchestrator_base_url,
        timeout=30.0,
        follow_redirects=True,
        headers={"Accept": "application/json"},
    ) as client:
        yield client


@pytest.fixture
async def worker_client(worker_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(
        base_url=worker_base_url,
        timeout=60.0,
        follow_redirects=True,
        headers={"Accept": "application/json"},
    ) as client:
        yield client


@pytest.fixture
async def require_orchestrator(orchestrator_client: httpx.AsyncClient):
    if not await _is_reachable(orchestrator_client, "/health"):
        pytest.skip("Orchestrator not reachable (set ORCHESTRATOR_URL or start docker-compose.test.yml)")


@pytest.fixture
async def require_worker(worker_client: httpx.AsyncClient):
    if not await _is_reachable(worker_client, "/health"):
        pytest.skip("Worker not reachable (set WORKER_URL or start docker-compose.test.yml)")


@dataclass
class AuthTokens:
    researcher: Optional[str] = RESEARCHER_TOKEN
    steward: Optional[str] = STEWARD_TOKEN
    admin: Optional[str] = ADMIN_TOKEN


@pytest.fixture(scope="session")
def auth_tokens() -> AuthTokens:
    return AuthTokens()


@pytest.fixture
def researcher_headers(auth_tokens: AuthTokens) -> Dict[str, str]:
    return _headers_for(auth_tokens.researcher)


@pytest.fixture
def steward_headers(auth_tokens: AuthTokens) -> Dict[str, str]:
    return _headers_for(auth_tokens.steward)


@pytest.fixture
def admin_headers(auth_tokens: AuthTokens) -> Dict[str, str]:
    return _headers_for(auth_tokens.admin)


@pytest.fixture
def perf_budget_seconds() -> float:
    # required by prompt
    return float(os.getenv("API_PERF_BUDGET_SECONDS", "5"))


@pytest.fixture
def request_timeout_seconds() -> float:
    return float(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "30"))


@pytest.fixture
def now_ms() -> int:
    return int(time.time() * 1000)
