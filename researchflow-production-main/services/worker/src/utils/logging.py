"""
Structured JSON logging with structlog.

Phase 3: App Integration & Monitoring.
- Timestamps, log levels (DEBUG, INFO, WARNING, ERROR)
- Stage execution logs with timing metrics
- Context propagation (project_id, stage_id, execution_id, job_id)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor

# Default to console format if structlog not configured yet
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = (os.getenv("LOG_FORMAT") or "console").strip().lower()


def _add_timestamp(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    import time
    event_dict["timestamp"] = time.time()
    return event_dict


def _configure_structlog() -> None:
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_timestamp,
    ]
    if LOG_FORMAT == "json":
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, LOG_LEVEL, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structlog logger bound to the given name."""
    configure_logging()
    return structlog.get_logger(name)


def bind_context(
    project_id: Optional[str] = None,
    stage_id: Optional[int] = None,
    execution_id: Optional[str] = None,
    job_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Bind context vars for propagation to all subsequent log lines."""
    ctx: Dict[str, Any] = {}
    if project_id is not None:
        ctx["project_id"] = project_id
    if stage_id is not None:
        ctx["stage_id"] = stage_id
    if execution_id is not None:
        ctx["execution_id"] = execution_id
    if job_id is not None:
        ctx["job_id"] = job_id
    ctx.update(kwargs)
    structlog.contextvars.bind_contextvars(**ctx)


def unbind_context(*keys: str) -> None:
    """Unbind context vars."""
    structlog.contextvars.unbind_contextvars(*keys)


def log_stage_start(
    logger: structlog.BoundLogger,
    stage_id: int,
    stage_name: str,
    job_id: str,
    execution_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> None:
    """Log the start of a stage execution with context."""
    logger.info(
        "stage_start",
        stage_id=stage_id,
        stage_name=stage_name,
        job_id=job_id,
        execution_id=execution_id or job_id,
        project_id=project_id,
    )


def log_stage_end(
    logger: structlog.BoundLogger,
    stage_id: int,
    stage_name: str,
    job_id: str,
    duration_ms: int,
    status: str,
    execution_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> None:
    """Log the end of a stage execution with timing and status."""
    logger.info(
        "stage_end",
        stage_id=stage_id,
        stage_name=stage_name,
        job_id=job_id,
        duration_ms=duration_ms,
        status=status,
        execution_id=execution_id or job_id,
        project_id=project_id,
    )


# One-time configure on module load
_configured = False


def configure_logging() -> None:
    """Ensure structlog is configured (idempotent)."""
    global _configured
    if not _configured:
        _configure_structlog()
        _configured = True
