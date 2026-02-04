"""Common helper utilities for integration tests."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional


async def poll(
    fn: Callable[[], Awaitable[Any]],
    *,
    timeout_s: float = 30.0,
    interval_s: float = 0.5,
    predicate: Optional[Callable[[Any], bool]] = None,
) -> Any:
    deadline = asyncio.get_event_loop().time() + timeout_s
    last = None
    while asyncio.get_event_loop().time() < deadline:
        last = await fn()
        if predicate is None or predicate(last):
            return last
        await asyncio.sleep(interval_s)
    return last


async def gather_with_concurrency(n: int, coros: list[Awaitable[Any]]) -> list[Any]:
    sem = asyncio.Semaphore(n)

    async def _run(c):
        async with sem:
            return await c

    return await asyncio.gather(*[_run(c) for c in coros])
