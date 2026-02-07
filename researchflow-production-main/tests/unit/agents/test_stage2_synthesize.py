"""
Unit tests for agent-stage2-synthesize: normalize_synthesize_inputs and run_sync output shape.
Run from repo root with PYTHONPATH including the agent:
  PYTHONPATH=services/agents/agent-stage2-synthesize pytest tests/unit/agents/test_stage2_synthesize.py -v
"""
import pytest

# Ensure agent package is importable when run with PYTHONPATH=services/agents/agent-stage2-synthesize
try:
    from agent.impl import normalize_synthesize_inputs, run_sync
except ImportError:
    pytest.skip("Run with PYTHONPATH=services/agents/agent-stage2-synthesize", allow_module_level=True)


def test_normalize_synthesize_inputs_required_papers():
    """inputs.papers is required."""
    with pytest.raises(ValueError, match="inputs.papers is required"):
        normalize_synthesize_inputs({"request_id": "r1", "inputs": {}})


def test_normalize_synthesize_inputs_papers_must_be_list():
    """inputs.papers must be a list."""
    with pytest.raises(ValueError, match="inputs.papers must be a list"):
        normalize_synthesize_inputs({"request_id": "r1", "inputs": {"papers": "not-a-list"}})


def test_normalize_synthesize_inputs_valid_minimal():
    """Valid minimal payload: papers array (can be empty)."""
    out = normalize_synthesize_inputs({
        "request_id": "r1",
        "inputs": {"papers": []},
    })
    assert out["papers"] == []
    assert out["research_question"] == "Synthesize the provided evidence."
    assert out["synthesis_type"] == "narrative"
    assert out["citations"] == []


def test_normalize_synthesize_inputs_with_papers_and_question():
    """Normalizes papers and research_question."""
    out = normalize_synthesize_inputs({
        "request_id": "r1",
        "inputs": {
            "papers": [
                {"id": "pmid-1", "extracted_data": {"methods": "RCT"}},
            ],
            "research_question": "Does X improve Y?",
            "synthesisType": "narrative",
        },
    })
    assert len(out["papers"]) == 1
    assert out["papers"][0]["id"] == "pmid-1"
    assert out["papers"][0]["extracted_data"] == {"methods": "RCT"}
    assert out["research_question"] == "Does X improve Y?"
    assert out["synthesis_type"] == "narrative"


@pytest.mark.asyncio
async def test_run_sync_returns_section_markdown_and_citations():
    """run_sync returns outputs.section_markdown and outputs.citations (demo when no INFERENCE_URL)."""
    payload = {
        "request_id": "req-synth-001",
        "task_type": "STAGE2_SYNTHESIZE",
        "inputs": {
            "papers": [
                {"id": "1", "extracted_data": {"methods": "RCT", "outcomes": "HbA1c"}},
            ],
            "research_question": "Does telemedicine improve glycemic control?",
        },
    }
    result = await run_sync(payload)
    assert result["status"] == "ok"
    assert "outputs" in result
    assert "section_markdown" in result["outputs"]
    assert "citations" in result["outputs"]
    assert isinstance(result["outputs"]["section_markdown"], str)
    assert isinstance(result["outputs"]["citations"], list)


@pytest.mark.asyncio
async def test_run_sync_validation_error_on_missing_papers():
    """run_sync returns error status when inputs.papers is missing."""
    payload = {
        "request_id": "req-synth-002",
        "task_type": "STAGE2_SYNTHESIZE",
        "inputs": {},
    }
    result = await run_sync(payload)
    assert result["status"] == "error"
    assert result.get("error", {}).get("code") == "VALIDATION_ERROR"
