"""
Integration test: full workflow pipeline

Runs a slice of the 20-stage pipeline (stages 14, 16, 17) with mocked
bridge/manuscript services. Uses the workflow orchestrator.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "worker"))

from src.workflow_engine.stages.base_stage_agent import BaseStageAgent
from src.workflow_engine.orchestrator import run_pipeline


@pytest.fixture
def artifact_path():
    """Temporary directory for artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_bridge():
    """Mock call_manuscript_service on BaseStageAgent so no real HTTP calls."""
    with patch.object(
        BaseStageAgent,
        "call_manuscript_service",
        new_callable=AsyncMock,
        return_value={"ok": True},
    ):
        yield


class TestFullWorkflowPipeline:
    """Integration tests for the full workflow pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_slice_14_16_17_success(self, artifact_path, mock_bridge):
        """Run stages 14, 16, 17 with mocked bridge; all should complete."""
        result = await run_pipeline(
            job_id="integration-job",
            config={},
            artifact_path=artifact_path,
            stage_ids=[14, 16, 17],
            stop_on_failure=True,
            governance_mode="DEMO",
        )

        assert "stages_completed" in result
        assert "stages_failed" in result
        assert "stages_skipped" in result
        assert "results" in result
        assert "success" in result

        assert result["success"] is True
        assert set(result["stages_completed"]) == {14, 16, 17}
        assert len(result["stages_failed"]) == 0
        assert len(result["results"]) == 3

        for stage_id in [14, 16, 17]:
            assert stage_id in result["results"]
            assert result["results"][stage_id]["stage_id"] == stage_id
            assert result["results"][stage_id]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_returns_expected_shape(self, artifact_path, mock_bridge):
        """Pipeline result has expected keys and result entries match stage_ids."""
        stage_ids = [14, 18, 19]
        result = await run_pipeline(
            job_id="shape-job",
            config={},
            artifact_path=artifact_path,
            stage_ids=stage_ids,
            stop_on_failure=True,
            governance_mode="DEMO",
        )

        assert result["success"] is True
        for sid in stage_ids:
            assert sid in result["results"]
            assert result["results"][sid]["status"] in ("completed", "skipped")
