"""Schema-validity metric — validates agent responses against JSON Schema.

P0 metric: no LLM calls required, pure structural validation.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Optional

import jsonschema
import jsonschema.validators

# ── Schema directory (tests/eval/datasets/schemas/) ──────────────────────────
SCHEMAS_DIR = pathlib.Path(__file__).resolve().parent.parent / "datasets" / "schemas"

# Cache loaded schemas so we don't re-read per call
_schema_cache: Dict[str, dict] = {}


def _load_schema(agent_name: str) -> dict:
    """Load and cache a JSON Schema for a given agent name."""
    if agent_name in _schema_cache:
        return _schema_cache[agent_name]

    schema_path = SCHEMAS_DIR / f"{agent_name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"No schema for agent '{agent_name}' at {schema_path}")

    schema = json.loads(schema_path.read_text())

    # Resolve local $ref (allOf → _base_envelope.json / _alt_envelope.json)
    schema = _resolve_local_refs(schema)

    _schema_cache[agent_name] = schema
    return schema


def _resolve_local_refs(schema: dict) -> dict:
    """Inline-resolve allOf $ref entries pointing at local _*.json files."""
    if "allOf" not in schema:
        return schema

    merged: dict = {}
    for entry in schema.get("allOf", []):
        ref = entry.get("$ref")
        if ref and ref.endswith(".json"):
            ref_path = SCHEMAS_DIR / ref
            if ref_path.exists():
                base = json.loads(ref_path.read_text())
                merged = _deep_merge(merged, base)
        else:
            merged = _deep_merge(merged, entry)

    # Overlay the agent-specific properties on top
    rest = {k: v for k, v in schema.items() if k not in ("allOf", "$schema", "$id")}
    merged = _deep_merge(merged, rest)

    # Preserve meta
    if "$schema" in schema:
        merged["$schema"] = schema["$schema"]
    if "$id" in schema:
        merged["$id"] = schema["$id"]

    return merged


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base (overlay wins on conflict)."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def validate_schema(
    response: Dict[str, Any],
    agent_name: str,
    schema: Optional[dict] = None,
) -> List[str]:
    """Validate *response* against the agent's JSON Schema.

    Returns a list of error strings (empty list == pass).
    """
    if schema is None:
        schema = _load_schema(agent_name)

    # Merge definitions from base into the resolved schema if present
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)

    errors: List[str] = []
    for err in sorted(validator.iter_errors(response), key=lambda e: list(e.absolute_path)):
        path = ".".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"[{path}] {err.message}")
    return errors


def list_available_schemas() -> List[str]:
    """Return agent names for which a schema file exists."""
    return sorted(
        p.stem
        for p in SCHEMAS_DIR.glob("*.json")
        if not p.stem.startswith("_")
    )
