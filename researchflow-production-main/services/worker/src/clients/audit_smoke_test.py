"""
Dev-only CLI smoke test for audit event emission.

Posts a single sample audit event to the orchestrator internal audit endpoint.
Uses same env as production: ORCHESTRATOR_BASE_URL, INTERNAL_API_KEY.
No LangGraph or heavy dependencies; uses orchestrator_audit_client only.

Usage:
  ORCHESTRATOR_BASE_URL=http://... INTERNAL_API_KEY=... python -m clients.audit_smoke_test
  # or from services/worker: python -m src.clients.audit_smoke_test
"""

from __future__ import annotations

import json
import sys

# Same client used by worker at runtime; no extra deps
from .orchestrator_audit_client import emit_audit_event


def main() -> None:
    event = {
        "stream_type": "RUN",
        "stream_key": "smoke-test",
        "actor_type": "WORKER",
        "service": "worker",
        "action": "SMOKE_TEST",
        "resource_type": "SMOKE",
        "resource_id": "SMOKE",
    }
    try:
        result = emit_audit_event(event)
        out = result if result is not None else {"ok": True}
        print(json.dumps(out, indent=2))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
