"""Pytest fixtures for the eval harness."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List

import pytest

EVAL_DIR = pathlib.Path(__file__).resolve().parent
DATASETS_DIR = EVAL_DIR / "datasets"
SCHEMAS_DIR = DATASETS_DIR / "schemas"
RESULTS_DIR = EVAL_DIR / "results"


@pytest.fixture
def eval_dir() -> pathlib.Path:
    return EVAL_DIR


@pytest.fixture
def schemas_dir() -> pathlib.Path:
    return SCHEMAS_DIR


@pytest.fixture
def datasets_dir() -> pathlib.Path:
    return DATASETS_DIR


def load_jsonl(path: pathlib.Path) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of dicts."""
    records: List[Dict[str, Any]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_schema(agent_name: str) -> dict:
    """Load the JSON Schema for a given agent name."""
    path = SCHEMAS_DIR / f"{agent_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text())
