"""Custom assertions for API responses."""

from __future__ import annotations

from typing import Any, Iterable, Optional

import httpx


def assert_status(resp: httpx.Response, expected: Iterable[int] | int, *, body_hint: bool = True) -> None:
    if isinstance(expected, int):
        expected_set = {expected}
    else:
        expected_set = set(expected)

    if resp.status_code not in expected_set:
        hint = ""
        if body_hint:
            try:
                hint = f"\nBody: {resp.text[:2000]}"
            except Exception:
                hint = ""
        raise AssertionError(f"Expected status {sorted(expected_set)}, got {resp.status_code}{hint}")


def assert_json(resp: httpx.Response) -> Any:
    ct = resp.headers.get("content-type", "")
    if "application/json" not in ct:
        raise AssertionError(f"Expected JSON response; got content-type={ct!r} body={resp.text[:500]!r}")
    return resp.json()


def assert_perf(elapsed_s: float, budget_s: float, *, label: str = "request") -> None:
    if elapsed_s > budget_s:
        raise AssertionError(f"{label} exceeded perf budget: {elapsed_s:.2f}s > {budget_s:.2f}s")


def assert_has_keys(obj: Any, keys: Iterable[str]) -> None:
    if not isinstance(obj, dict):
        raise AssertionError(f"Expected dict, got {type(obj)}")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise AssertionError(f"Missing keys: {missing}; got keys={list(obj.keys())}")


def maybe_skip_auth(resp: httpx.Response) -> None:
    # Many orchestrator endpoints are RBAC-protected; allow tests to skip when tokens are absent.
    if resp.status_code in (401, 403):
        raise httpx.HTTPStatusError("Auth required for endpoint", request=resp.request, response=resp)
