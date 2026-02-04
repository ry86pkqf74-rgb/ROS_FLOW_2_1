"""PHI access audit logging.

This module provides an offline-safe audit logger for PHI scan/redaction events.
It is intentionally minimal and stores JSONL locally under a configurable path.

In production, this can be swapped to a durable sink (DB/S3/SIEM).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    project_id: str
    user_id: str
    action: str
    resource_id: str
    timestamp_utc: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_context: Dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """JSONL file-backed audit logger with per-project files."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(
            base_dir
            or os.getenv("PHI_AUDIT_LOG_DIR", "/tmp/researchflow_phi_audit")
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path_for_project(self, project_id: str) -> Path:
        safe = "".join(ch for ch in project_id if ch.isalnum() or ch in ("-", "_")) or "unknown"
        return self.base_dir / f"{safe}.jsonl"

    async def log_event(self, event: AuditEvent) -> None:
        path = self._path_for_project(event.project_id)
        line = json.dumps(event.model_dump(), ensure_ascii=False)
        async with self._lock:
            await asyncio.to_thread(self._append_line, path, line)

    def _append_line(self, path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    async def get_events(self, project_id: str, limit: int = 200) -> List[AuditEvent]:
        path = self._path_for_project(project_id)
        if not path.exists():
            return []

        def read_tail() -> List[AuditEvent]:
            # naive tail: read whole file (acceptable for unit tests / small logs)
            lines = path.read_text(encoding="utf-8").splitlines()
            out: List[AuditEvent] = []
            for raw in lines[-limit:]:
                try:
                    out.append(AuditEvent(**json.loads(raw)))
                except Exception:
                    continue
            return out

        return await asyncio.to_thread(read_tail)
