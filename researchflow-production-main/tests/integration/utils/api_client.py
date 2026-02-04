"""Typed-ish async API client wrappers for integration tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class TimedResponse:
    response: httpx.Response
    elapsed_s: float


class APIClient:
    def __init__(self, client: httpx.AsyncClient, default_headers: Optional[Dict[str, str]] = None):
        self._client = client
        self._default_headers = default_headers or {}

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Any = None,
        data: Any = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> TimedResponse:
        merged = {**self._default_headers, **(headers or {})}
        t0 = time.perf_counter()
        resp = await self._client.request(method, url, headers=merged, json=json, data=data, params=params)
        elapsed = time.perf_counter() - t0
        return TimedResponse(resp, elapsed)

    async def get(self, url: str, **kw: Any) -> TimedResponse:
        return await self.request("GET", url, **kw)

    async def post(self, url: str, **kw: Any) -> TimedResponse:
        return await self.request("POST", url, **kw)

    async def put(self, url: str, **kw: Any) -> TimedResponse:
        return await self.request("PUT", url, **kw)

    async def delete(self, url: str, **kw: Any) -> TimedResponse:
        return await self.request("DELETE", url, **kw)
