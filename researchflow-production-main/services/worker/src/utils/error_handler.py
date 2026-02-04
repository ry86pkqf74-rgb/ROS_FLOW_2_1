"""
Error handling and recovery for workflow execution.

Phase 3: App Integration & Monitoring.
- Custom exception classes per failure type
- Retry logic with exponential backoff (tenacity)
- Dead letter queue for failed stages (in-memory and optional Redis)
- Graceful degradation strategies
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

T = TypeVar("T")


# -----------------------------------------------------------------------------
# Custom exceptions
# -----------------------------------------------------------------------------


class WorkflowError(Exception):
    """Base exception for workflow failures."""

    def __init__(self, message: str, code: str = "WORKFLOW_ERROR") -> None:
        self.code = code
        super().__init__(message)


class StageExecutionError(WorkflowError):
    """A workflow stage failed during execution."""

    def __init__(
        self,
        message: str,
        stage_id: Optional[int] = None,
        stage_name: Optional[str] = None,
    ) -> None:
        super().__init__(message, code="STAGE_EXECUTION_ERROR")
        self.stage_id = stage_id
        self.stage_name = stage_name


class StageTimeoutError(WorkflowError):
    """A stage exceeded its timeout."""

    def __init__(
        self,
        message: str,
        stage_id: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(message, code="STAGE_TIMEOUT")
        self.stage_id = stage_id
        self.timeout_seconds = timeout_seconds


class BridgeUnavailableError(WorkflowError):
    """Orchestrator/bridge service unavailable."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="BRIDGE_UNAVAILABLE")


class RecoverableError(WorkflowError):
    """Transient error that may succeed on retry."""

    def __init__(self, message: str, code: str = "RECOVERABLE") -> None:
        super().__init__(message, code=code)


# -----------------------------------------------------------------------------
# Dead letter queue
# -----------------------------------------------------------------------------

DLQ_ENTRY = Dict[str, Any]  # job_id, stage_id, error, timestamp, etc.

_in_memory_dlq: List[DLQ_ENTRY] = []
_DLQ_MAX_SIZE = int(os.getenv("WORKFLOW_DLQ_MAX_SIZE", "1000"))


def push_to_dlq(
    job_id: str,
    stage_id: int,
    error: str,
    stage_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a failed stage to the in-memory dead letter queue."""
    entry: DLQ_ENTRY = {
        "job_id": job_id,
        "stage_id": stage_id,
        "error": error,
        "timestamp": time.time(),
    }
    if stage_name is not None:
        entry["stage_name"] = stage_name
    if extra:
        entry.update(extra)
    _in_memory_dlq.append(entry)
    while len(_in_memory_dlq) > _DLQ_MAX_SIZE:
        _in_memory_dlq.pop(0)


def get_dlq_snapshot() -> List[DLQ_ENTRY]:
    """Return a copy of the current DLQ (for admin endpoint or debugging)."""
    return list(_in_memory_dlq)


def clear_dlq() -> None:
    """Clear the in-memory DLQ (for tests)."""
    _in_memory_dlq.clear()


async def push_to_redis_dlq(
    redis_url: str,
    job_id: str,
    stage_id: int,
    error: str,
    stage_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Push a failed stage to Redis list researchflow:dlq:stages. Returns True if pushed."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)
        entry: DLQ_ENTRY = {
            "job_id": job_id,
            "stage_id": stage_id,
            "error": error,
            "timestamp": time.time(),
        }
        if stage_name is not None:
            entry["stage_name"] = stage_name
        if extra:
            entry.update(extra)
        import json
        await client.lpush("researchflow:dlq:stages", json.dumps(entry))
        await client.close()
        return True
    except Exception:
        return False


def push_dlq(
    job_id: str,
    stage_id: int,
    error: str,
    stage_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append to in-memory DLQ. For Redis, call push_to_redis_dlq from async code."""
    push_to_dlq(job_id, stage_id, error, stage_name=stage_name, extra=extra)


# -----------------------------------------------------------------------------
# Retry with exponential backoff
# -----------------------------------------------------------------------------

def retry_async(
    fn: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    retry_exceptions: tuple = (RecoverableError, BridgeUnavailableError),
    **kwargs: Any,
) -> T:
    """Sync wrapper: run fn with tenacity retry (exponential backoff)."""
    r = retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=0.5, min=1, max=30),
        retry=retry_if_exception_type(retry_exceptions),
        reraise=True,
    )
    return r(lambda: fn(*args, **kwargs))()


async def retry_async_await(
    fn: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    retry_exceptions: tuple = (RecoverableError, BridgeUnavailableError),
    **kwargs: Any,
) -> T:
    """Async: call fn (coroutine) with tenacity retry. Use for async functions."""
    from tenacity import AsyncRetrying
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=0.5, min=1, max=30),
        retry=retry_if_exception_type(retry_exceptions),
        reraise=True,
    ):
        with attempt:
            return await fn(*args, **kwargs)
