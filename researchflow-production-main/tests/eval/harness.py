"""Core evaluation harness — run agent → collect metrics → write results.

Supports two modes:
  - Live: calls a running agent via HTTP
  - Dry-run (P0): validates pre-recorded or synthetic responses against schemas only
"""
from __future__ import annotations

import json
import os
import pathlib
import time
from typing import Any, Callable, Dict, List, Optional

import httpx

from tests.eval.metrics.schema_validity import validate_schema, list_available_schemas
from tests.eval.metrics.latency import timed_call, check_latency
from tests.eval.metrics.groundedness import rouge_l_f1, flatten_outputs
from tests.eval.metrics.cost import estimate_cost


# ── Agent invocation ─────────────────────────────────────────────────────────

DEFAULT_BASE_URL = os.environ.get("EVAL_AGENT_BASE_URL", "http://localhost")

# Port map — matches docker-compose port mappings (internal 8000)
AGENT_PORTS: Dict[str, int] = {
    "agent-stage2-lit":        8010,
    "agent-stage2-screen":     8011,
    "agent-stage2-extract":    8012,
    "agent-stage2-synthesize": 8013,
    "agent-lit-retrieval":     8020,
    "agent-policy-review":     8021,
    "agent-rag-ingest":        8030,
    "agent-rag-retrieve":      8031,
    "agent-verify":            8040,
    "agent-intro-writer":      8050,
    "agent-methods-writer":    8051,
    "agent-evidence-synth":    8060,
    "agent-lit-triage":        8061,
}


def invoke_agent(
    agent_name: str,
    payload: Dict[str, Any],
    base_url: Optional[str] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """POST to the agent's /agents/run/sync endpoint and return the JSON response."""
    base = base_url or DEFAULT_BASE_URL
    port = AGENT_PORTS.get(agent_name, 8000)
    url = f"{base}:{port}/agents/run/sync"

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


# ── Synthetic response builder (for dry-run / P0) ───────────────────────────

def build_synthetic_response(agent_name: str) -> Dict[str, Any]:
    """Build a minimal valid response for schema-only (dry-run) validation.

    This lets P0 schema validation run without any live agents.
    """
    # Determine envelope type
    alt_agents = {"agent-evidence-synth", "agent-lit-triage"}

    if agent_name in alt_agents:
        return {
            "ok": True,
            "request_id": f"eval-dry-{agent_name}",
            "task_type": "eval_dry_run",
            "outputs": {},
            "warnings": [],
        }

    return {
        "status": "ok",
        "request_id": f"eval-dry-{agent_name}",
        "outputs": {},
        "artifacts": [],
        "provenance": {},
        "usage": {},
        "grounding": None,
        "error": None,
    }


# ── Evaluation loop ─────────────────────────────────────────────────────────

def evaluate_schema_only(agents: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """P0 evaluation: validate synthetic responses against schemas.

    No LLM calls, no running agents required.
    """
    if agents is None:
        agents = list_available_schemas()

    results: List[Dict[str, Any]] = []
    for agent_name in agents:
        response = build_synthetic_response(agent_name)
        errors = validate_schema(response, agent_name)
        results.append({
            "id": f"schema-{agent_name}",
            "agent": agent_name,
            "metric": "schema_validity",
            "schema_errors": errors,
            "error_count": len(errors),
            "passed": len(errors) == 0,
        })
    return results


def evaluate_dataset(
    agent_name: str,
    dataset_path: pathlib.Path,
    dry_run: bool = False,
    base_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Full evaluation: invoke agent on each dataset record, collect all metrics.

    In dry-run mode, uses cached responses from datasets/cached_responses/ if available.
    """
    from tests.eval.conftest import load_jsonl

    records = load_jsonl(dataset_path)
    results: List[Dict[str, Any]] = []

    ci_mode = os.environ.get("EVAL_MODE") == "ci"
    if ci_mode and len(records) > 5:
        records = records[:5]  # CI: sample 5 records max

    for case in records:
        case_id = case.get("id", "unknown")

        if dry_run:
            actual = build_synthetic_response(agent_name)
            latency_s = 0.0
        else:
            actual, latency_s = timed_call(
                invoke_agent, agent_name, case.get("input", {}), base_url
            )

        schema_errors = validate_schema(actual, agent_name)

        # Groundedness (only if expected_output provided)
        groundedness_f1 = 0.0
        expected = case.get("expected_output")
        if expected:
            actual_text = flatten_outputs(actual.get("outputs", {}))
            expected_text = flatten_outputs(expected) if isinstance(expected, dict) else str(expected)
            groundedness_f1 = rouge_l_f1(actual_text, expected_text)

        # Cost
        usage = actual.get("usage", {})
        cost_usd = estimate_cost(usage, agent_name) if usage else 0.0

        passed = len(schema_errors) == 0
        results.append({
            "id": case_id,
            "agent": agent_name,
            "groundedness_f1": groundedness_f1,
            "schema_errors": schema_errors,
            "schema_error_count": len(schema_errors),
            "latency_s": round(latency_s, 4),
            "cost_usd": cost_usd,
            "passed": passed,
        })

    return results


def write_results(results: List[Dict[str, Any]], output_dir: pathlib.Path) -> pathlib.Path:
    """Write evaluation results to a timestamped JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"eval_{ts}.json"
    out_path.write_text(json.dumps(results, indent=2, default=str))
    return out_path
