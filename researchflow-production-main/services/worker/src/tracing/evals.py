"""
LangSmith evaluation functions for ResearchFlow.

Evaluations:
  1. audit_completeness — Every node in a trace emitted both NODE_START and NODE_FINISH.
  2. phi_leak_check     — Trace payloads contain no PHI patterns.

Run via pytest:
    python -m pytest services/worker/src/tracing/evals.py -v

These can also be used as LangSmith custom evaluators when running
`client.run_on_dataset()` or programmatic evaluation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

import pytest

# ---------------------------------------------------------------------------
# PHI detection patterns (same as langsmith_config.py for consistency)
# ---------------------------------------------------------------------------

_PHI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
    re.compile(r"\b(?:MRN|MR#?)\s*:?\s*\d{4,}\b", re.IGNORECASE),  # MRN
    re.compile(
        r"\b(?:DOB|Date\s*of\s*Birth)\s*:?\s*\d{1,4}[/\-]\d{1,2}[/\-]\d{1,4}\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone
]


# ============================================================================
# Eval 1: audit_completeness
# ============================================================================


def eval_audit_completeness(
    trace_events: Sequence[Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Evaluate whether every node that emitted NODE_STARTED also emitted
    NODE_FINISHED (or NODE_FAILED). Reports any orphaned starts.

    Args:
        trace_events: List of audit event dicts, each containing at least
                      'node_id' and 'action' keys.

    Returns:
        (passed, reason) tuple.
    """
    started_nodes: dict[str, int] = {}
    ended_nodes: dict[str, int] = {}

    for event in trace_events:
        node_id = event.get("node_id", "")
        action = event.get("action", "")
        if action in ("NODE_STARTED", "RUN_STARTED", "RESUME_STARTED"):
            started_nodes[node_id] = started_nodes.get(node_id, 0) + 1
        elif action in (
            "NODE_FINISHED", "NODE_FAILED",
            "RUN_FINISHED", "RUN_FAILED",
            "RESUME_FINISHED", "RESUME_FAILED",
        ):
            ended_nodes[node_id] = ended_nodes.get(node_id, 0) + 1

    orphaned = []
    for node_id, count in started_nodes.items():
        ended = ended_nodes.get(node_id, 0)
        if ended < count:
            orphaned.append(f"{node_id} (started={count}, ended={ended})")

    if not orphaned:
        return True, f"All {len(started_nodes)} nodes have matching start/finish events"
    return False, f"Orphaned starts (no matching finish): {', '.join(orphaned)}"


# ============================================================================
# Eval 2: phi_leak_check
# ============================================================================


def eval_phi_leak_check(
    trace_payloads: Sequence[str | Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Scan trace payloads for PHI patterns (SSN, MRN, DOB, email, phone).

    Args:
        trace_payloads: List of payload strings or dicts to scan.

    Returns:
        (passed, reason) tuple.
    """

    def _flatten(obj: Any) -> List[str]:
        """Flatten nested dicts/lists into a list of strings for scanning."""
        if isinstance(obj, str):
            return [obj]
        if isinstance(obj, dict):
            parts = []
            for v in obj.values():
                parts.extend(_flatten(v))
            return parts
        if isinstance(obj, (list, tuple)):
            parts = []
            for item in obj:
                parts.extend(_flatten(item))
            return parts
        return [str(obj)] if obj is not None else []

    violations: list[str] = []
    for idx, payload in enumerate(trace_payloads):
        texts = _flatten(payload)
        for text in texts:
            for pattern in _PHI_PATTERNS:
                match = pattern.search(text)
                if match:
                    # Report location but NOT the matched text (it's PHI)
                    violations.append(
                        f"payload[{idx}]: PHI pattern detected at offset {match.start()}"
                    )
                    break  # One violation per payload is enough

    if not violations:
        return True, f"No PHI detected in {len(trace_payloads)} payloads"
    return False, f"PHI detected: {'; '.join(violations[:10])}"


# ============================================================================
# Pytest tests (runnable via: python -m pytest evals.py -v)
# ============================================================================


class TestAuditCompleteness:
    def test_all_matched(self):
        events = [
            {"node_id": "n1", "action": "NODE_STARTED"},
            {"node_id": "n1", "action": "NODE_FINISHED"},
            {"node_id": "n2", "action": "NODE_STARTED"},
            {"node_id": "n2", "action": "NODE_FAILED"},
        ]
        passed, reason = eval_audit_completeness(events)
        assert passed is True

    def test_orphaned_start(self):
        events = [
            {"node_id": "n1", "action": "NODE_STARTED"},
            {"node_id": "n2", "action": "NODE_STARTED"},
            {"node_id": "n2", "action": "NODE_FINISHED"},
        ]
        passed, reason = eval_audit_completeness(events)
        assert passed is False
        assert "n1" in reason

    def test_empty_trace(self):
        passed, reason = eval_audit_completeness([])
        assert passed is True

    def test_run_level_events(self):
        events = [
            {"node_id": "__invoke__", "action": "RUN_STARTED"},
            {"node_id": "n1", "action": "NODE_STARTED"},
            {"node_id": "n1", "action": "NODE_FINISHED"},
            {"node_id": "__invoke__", "action": "RUN_FINISHED"},
        ]
        passed, reason = eval_audit_completeness(events)
        assert passed is True

    def test_multiple_attempts(self):
        events = [
            {"node_id": "n1", "action": "NODE_STARTED"},
            {"node_id": "n1", "action": "NODE_FAILED"},
            {"node_id": "n1", "action": "NODE_STARTED"},
            {"node_id": "n1", "action": "NODE_FINISHED"},
        ]
        passed, reason = eval_audit_completeness(events)
        assert passed is True


class TestPhiLeakCheck:
    def test_clean_payloads(self):
        payloads = [
            {"node_id": "n1", "status": "ok", "score": 0.95},
            "This is a clean text with no PHI.",
        ]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is True

    def test_ssn_detected(self):
        payloads = ["Patient SSN: 123-45-6789"]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False
        assert "PHI pattern detected" in reason

    def test_mrn_detected(self):
        payloads = [{"patient_info": "MRN: 12345678"}]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False

    def test_email_detected(self):
        payloads = ["Contact: patient@hospital.org"]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False

    def test_dob_detected(self):
        payloads = ["DOB: 01/15/1985"]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False

    def test_phone_detected(self):
        payloads = ["Phone: (555) 123-4567"]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False

    def test_nested_dict_phi(self):
        payloads = [
            {
                "metadata": {
                    "patient": {"ssn": "111-22-3333", "name": "John Doe"}
                }
            }
        ]
        passed, reason = eval_phi_leak_check(payloads)
        assert passed is False

    def test_empty_payloads(self):
        passed, reason = eval_phi_leak_check([])
        assert passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
