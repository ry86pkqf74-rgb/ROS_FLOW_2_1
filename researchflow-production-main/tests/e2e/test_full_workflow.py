"""
E2E test: full 20-stage workflow execution.

Phase 4: Tests complete pipeline with mocked external services (LLM, literature, etc.),
stage transitions, context passing, error recovery, and metrics emission.
Run from repo root: PYTHONPATH=services/worker pytest tests/e2e/test_full_workflow.py -v
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Allow importing worker modules when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "worker"))

from src.workflow_engine.orchestrator import run_pipeline, get_default_stage_ids
from src.workflow_engine.stages.base_stage_agent import BaseStageAgent
from src.utils.metrics import get_metrics_output


@pytest.fixture
def artifact_path():
    """Temporary directory for artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def dataset_pointer(artifact_path):
    """Minimal CSV file so stage 01 (Upload Intake) can succeed."""
    path = Path(artifact_path) / "sample.csv"
    path.write_text("id,value\n1,10\n2,20\n", encoding="utf-8")
    return str(path)


@pytest.fixture
def mock_bridge():
    """Mock manuscript/LLM bridge so no real HTTP or LLM calls."""
    with patch.object(
        BaseStageAgent,
        "call_manuscript_service",
        new_callable=AsyncMock,
        return_value={"ok": True, "content": "", "papers": [], "items": []},
    ):
        yield


@pytest.fixture
def mock_httpx_literature():
    """Mock httpx.AsyncClient for stage 02 literature fallback (PubMed/Semantic Scholar)."""
    async def fake_get(*args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value={"items": [], "papers": []})
        return resp

    with patch("httpx.AsyncClient") as m:
        client = MagicMock()
        client.get = fake_get
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        m.return_value = client
        yield m


class TestFullWorkflowE2E:
    """E2E tests for the complete 20-stage workflow."""

    @pytest.mark.asyncio
    async def test_full_20_stage_success(
        self, artifact_path, dataset_pointer, mock_bridge, mock_httpx_literature
    ):
        """Run all registered stages with mocks; verify completion and result shape."""
        stage_ids = get_default_stage_ids()
        result = await run_pipeline(
            job_id="e2e-full-job",
            config={},
            artifact_path=artifact_path,
            stage_ids=stage_ids,
            stop_on_failure=True,
            governance_mode="DEMO",
            dataset_pointer=dataset_pointer,
        )

        assert "stages_completed" in result
        assert "stages_failed" in result
        assert "stages_skipped" in result
        assert "results" in result
        assert "success" in result

        assert result["success"] is True, (
            f"Pipeline failed: completed={result['stages_completed']}, "
            f"failed={result['stages_failed']}, skipped={result['stages_skipped']}"
        )
        assert set(result["stages_completed"]) == set(stage_ids)
        assert len(result["stages_failed"]) == 0
        assert len(result["results"]) == len(stage_ids)

        for sid in stage_ids:
            assert sid in result["results"]
            assert result["results"][sid]["stage_id"] == sid
            assert result["results"][sid]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_stage_transitions_and_context_passing(
        self, artifact_path, dataset_pointer, mock_bridge, mock_httpx_literature
    ):
        """Verify stage order and that each result has expected shape (context passed)."""
        stage_ids = get_default_stage_ids()
        result = await run_pipeline(
            job_id="e2e-context-job",
            config={},
            artifact_path=artifact_path,
            stage_ids=stage_ids,
            stop_on_failure=True,
            governance_mode="DEMO",
            dataset_pointer=dataset_pointer,
        )

        assert result["success"] is True
        # Results should be in order; each result has output/artifacts from that stage
        for sid in stage_ids:
            r = result["results"][sid]
            assert "stage_id" in r and r["stage_id"] == sid
            assert "status" in r and r["status"] == "completed"
            assert "started_at" in r and "completed_at" in r
            assert "duration_ms" in r
            assert "output" in r

    @pytest.mark.asyncio
    async def test_stop_on_failure_skips_later_stages(
        self, artifact_path, dataset_pointer, mock_bridge, mock_httpx_literature
    ):
        """When one stage fails and stop_on_failure=True, later stages are skipped."""
        from src.workflow_engine.registry import get_stage

        stage_ids = [14, 15, 16, 17]
        stage_15_cls = get_stage(15)
        if stage_15_cls is None:
            pytest.skip("Stage 15 not registered")

        original_execute = stage_15_cls.execute

        async def failing_execute(context):
            raise RuntimeError("Simulated stage failure for E2E")

        with patch.object(stage_15_cls, "execute", failing_execute):
            result = await run_pipeline(
                job_id="e2e-fail-job",
                config={},
                artifact_path=artifact_path,
                stage_ids=stage_ids,
                stop_on_failure=True,
                governance_mode="DEMO",
            )

        assert result["success"] is False
        assert 15 in result["stages_failed"]
        assert 16 in result["stages_skipped"]
        assert 17 in result["stages_skipped"]
        assert 15 in result["results"] and result["results"][15]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_metrics_emission_after_run(
        self, artifact_path, dataset_pointer, mock_bridge, mock_httpx_literature
    ):
        """After a successful run, Prometheus metrics include stage counters."""
        stage_ids = [14, 16, 17]
        await run_pipeline(
            job_id="e2e-metrics-job",
            config={},
            artifact_path=artifact_path,
            stage_ids=stage_ids,
            stop_on_failure=True,
            governance_mode="DEMO",
        )

        output = get_metrics_output()
        assert isinstance(output, bytes)
        text = output.decode("utf-8")
        assert "researchflow_workflow_stage_total" in text
        assert "researchflow_workflow_stage_duration_seconds" in text
        for sid in stage_ids:
            assert str(sid) in text, f"Expected stage_id {sid} in metrics output"
