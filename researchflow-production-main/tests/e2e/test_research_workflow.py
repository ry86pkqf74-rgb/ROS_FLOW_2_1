"""
E2E test: full 20-stage research workflow (re-exports test_full_workflow).
Run from repo root: PYTHONPATH=services/worker pytest tests/e2e/test_research_workflow.py -v
"""

import sys
from pathlib import Path

import pytest

# Ensure worker src is on path when run from repo root
_repo_root = Path(__file__).resolve().parents[2]
_worker_src = _repo_root / "services" / "worker"
if str(_worker_src) not in sys.path:
    sys.path.insert(0, str(_worker_src))

# Re-export the full 20-stage workflow test class so both filenames are supported
pytest.importorskip("src.workflow_engine.orchestrator", reason="worker src not on path")

from test_full_workflow import TestFullWorkflowE2E  # noqa: E402

__all__ = ["TestFullWorkflowE2E"]
