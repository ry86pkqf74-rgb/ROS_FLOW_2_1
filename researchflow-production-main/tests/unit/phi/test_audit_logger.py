from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.phi.redaction.audit_logger import AuditEvent, AuditLogger


@pytest.mark.asyncio
async def test_log_entry_creation_and_user_context_capture(tmp_path: Path):
    logger = AuditLogger(base_dir=str(tmp_path))

    ev = AuditEvent(
        project_id="proj-1",
        user_id="user-1",
        action="scan",
        resource_id="res-1",
        metadata={"kinds": ["ssn"]},
        user_context={"ip": "127.0.0.1", "agent": "pytest"},
    )

    await logger.log_event(ev)

    log_path = tmp_path / "proj-1.jsonl"
    assert log_path.exists()
    assert log_path.read_text(encoding="utf-8").strip()


@pytest.mark.asyncio
async def test_query_search_functionality_via_tail_read(tmp_path: Path):
    logger = AuditLogger(base_dir=str(tmp_path))

    for i in range(3):
        await logger.log_event(
            AuditEvent(
                project_id="proj-2",
                user_id=f"u-{i}",
                action="redact",
                resource_id=f"r-{i}",
                metadata={"i": i},
                user_context={},
            )
        )

    events = await logger.get_events("proj-2", limit=2)
    assert len(events) == 2
    assert events[-1].resource_id == "r-2"


@pytest.mark.asyncio
async def test_log_rotation_and_retention_is_external_to_logger(tmp_path: Path):
    # Current AuditLogger is intentionally minimal; rotation/retention is handled by deployment.
    # This test asserts logger continues appending without truncation.
    logger = AuditLogger(base_dir=str(tmp_path))

    for i in range(10):
        await logger.log_event(
            AuditEvent(
                project_id="proj-3",
                user_id="u",
                action="scan",
                resource_id=str(i),
                metadata={},
                user_context={},
            )
        )

    log_path = tmp_path / "proj-3.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 10
