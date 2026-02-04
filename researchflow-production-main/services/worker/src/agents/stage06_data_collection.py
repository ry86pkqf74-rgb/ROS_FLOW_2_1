"""
Stage 06 — Data Collection

Gather relevant sources (URLs, papers, docs) and extract key claims.
Spec: docs/stages/STAGE_WORKER_SPECS.md (ANALYSIS Phase).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .stage_base import (
    call_llm_async,
    make_error,
    make_result,
    parse_json_from_llm,
    VALIDATION_ERROR,
    LOW_COVERAGE,
)

logger = logging.getLogger(__name__)

STAGE = 6
MIN_SOURCES = 5


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    if not inputs.get("topic"):
        errors.append("topic is required")
    max_sources = inputs.get("maxSources") or inputs.get("max_sources", 20)
    if not isinstance(max_sources, (int, float)) or max_sources < 1:
        errors.append("maxSources must be a positive number")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 06: Data Collection.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with workflowId, stage, runId, inputs, etc.

    Returns:
        Canonical result envelope: ok, workflowId, stage, runId, outputs, next_stage, warnings?, errors?
    """
    run_id = stage_data.get("runId", "")
    inputs = stage_data.get("inputs") or stage_data
    validation_errors = _validate_inputs(inputs)
    if validation_errors:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(VALIDATION_ERROR, "; ".join(validation_errors))],
        )

    topic = inputs.get("topic", "")
    research_question = inputs.get("researchQuestion") or inputs.get("research_question", "")
    keywords = inputs.get("keywords") or []
    max_sources = int(inputs.get("maxSources") or inputs.get("max_sources", 20))
    constraints = inputs.get("constraints") or {}

    system_prompt = """You are a research assistant. Output valid JSON only (no markdown).
For each source provide: id, title, url, publisher (optional), publishedAt (optional), summary, keyClaims (array of strings).
Also provide queryLog: array of { query, resultsCount }."""

    prompt = f"""Topic: {topic}
Research question: {research_question or "Not specified"}
Keywords: {keywords}
Max sources to return: {max_sources}
Constraints: {constraints}

Generate a list of relevant research sources (papers, articles, docs) and for each:
1. id (short unique id, e.g. s1, s2)
2. title
3. url
4. publisher (optional)
5. publishedAt (optional, ISO date or year)
6. summary (2-3 sentences)
7. keyClaims (array of bullet strings)

Also provide queryLog: array of search queries you would use and their approximate resultsCount.

Return JSON in this exact shape:
{{ "sources": [ {{ "id", "title", "url", "publisher?", "publishedAt?", "summary", "keyClaims" }} ], "queryLog": [ {{ "query", "resultsCount" }} ] }}"""

    warnings: List[Dict[str, Any]] = []
    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage06_data_collection",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage06_data_collection")
    except Exception as e:
        logger.exception("Stage 06 LLM failed: %s", e)
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("UPSTREAM_5XX", str(e), retryable=True)],
        )

    if not parsed or "sources" not in parsed:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("INCONSISTENT_OUTPUT", "LLM did not return valid sources JSON", retryable=True)],
        )

    sources = parsed.get("sources") or []
    query_log = parsed.get("queryLog") or parsed.get("query_log") or []
    min_expected = min(MIN_SOURCES, max_sources)
    if len(sources) < min_expected:
        warnings.append({"code": LOW_COVERAGE, "message": f"Fewer than {min_expected} sources found ({len(sources)})"})

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"sources": sources, "queryLog": query_log},
        warnings=warnings if warnings else None,
    )
