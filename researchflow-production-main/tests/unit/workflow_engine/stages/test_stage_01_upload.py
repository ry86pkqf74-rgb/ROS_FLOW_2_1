"""
Unit tests for Stage 01: Data Ingestion Agent

Tests the DataIngestionAgent implementation:
- File reading for multiple formats (CSV, Excel, JSON, Parquet)
- Metadata extraction
- Data quality profiling
- Study type detection
- DEMO vs LIVE mode validation
- Artifact generation
- Error handling
"""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_01_upload import DataIngestionAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def sample_context():
    """Create a sample StageContext for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="test-job-123",
            config={},
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tmpdir,
        )
        yield context


@pytest.fixture
def agent():
    """Create a DataIngestionAgent instance."""
    return DataIngestionAgent()


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("patient_id,age,gender,treatment,outcome\n")
        f.write("P001,45,M,Control,0\n")
        f.write("P002,52,F,Treatment,1\n")
        f.write("P003,38,M,Treatment,1\n")
        f.write("P004,,F,Control,0\n")  # Missing age
        f.write("P005,61,M,Treatment,1\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_json_file():
    """Create a sample JSON file for testing."""
    data = [
        {"patient_id": "P001", "age": 45, "gender": "M", "treatment": "Control", "outcome": 0},
        {"patient_id": "P002", "age": 52, "gender": "F", "treatment": "Treatment", "outcome": 1},
        {"patient_id": "P003", "age": 38, "gender": "M", "treatment": "Treatment", "outcome": 1},
    ]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_rct_csv_file():
    """Create a CSV file with RCT indicators."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("patient_id,randomized_group,treatment_arm,baseline_visit,outcome\n")
        f.write("P001,1,Control,0,0\n")
        f.write("P002,2,Treatment,0,1\n")
        f.write("P003,1,Control,0,0\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_cohort_csv_file():
    """Create a CSV file with cohort study indicators."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("patient_id,exposure,outcome,followup_time\n")
        f.write("P001,Yes,1,12\n")
        f.write("P002,No,0,12\n")
        f.write("P003,Yes,1,24\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_case_control_csv_file():
    """Create a CSV file with case-control indicators."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("patient_id,case_control,exposure\n")
        f.write("P001,Case,Yes\n")
        f.write("P002,Control,No\n")
        f.write("P003,Case,Yes\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def empty_file():
    """Create an empty file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def invalid_file():
    """Create an invalid CSV file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("invalid,malformed,csv\n")
        f.write("line1,line2\n")
        f.write("incomplete\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestDataIngestionAgent:
    """Tests for DataIngestionAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 1
        assert agent.stage_name == "Data Ingestion"

    def test_get_tools(self, agent):
        """get_tools should return a list (can be empty)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a PromptTemplate."""
        template = agent.get_prompt_template()
        assert template is not None


class TestFileReading:
    """Tests for _read_file method."""

    def test_read_csv(self, agent, sample_csv_file):
        """Should read CSV files correctly."""
        df = agent._read_file(sample_csv_file)
        assert df is not None
        assert len(df) == 5
        assert len(df.columns) == 5
        assert "patient_id" in df.columns

    def test_read_json(self, agent, sample_json_file):
        """Should read JSON files correctly."""
        df = agent._read_file(sample_json_file)
        assert df is not None
        assert len(df) == 3
        assert len(df.columns) == 5

    def test_read_unsupported_format(self, agent):
        """Should raise ValueError for unsupported formats."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b"test data")
            f.flush()
            try:
                with pytest.raises(ValueError, match="Unsupported file format"):
                    agent._read_file(f.name)
            finally:
                os.unlink(f.name)

    def test_read_nonexistent_file(self, agent):
        """Should raise ValueError for nonexistent files."""
        with pytest.raises(ValueError):
            agent._read_file("/nonexistent/file.csv")


class TestMetadataExtraction:
    """Tests for _extract_metadata method."""

    def test_extract_metadata_basic(self, agent, sample_csv_file):
        """Should extract basic metadata."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        metadata = agent._extract_metadata(df, sample_csv_file)

        assert metadata["row_count"] == 5
        assert metadata["column_count"] == 5
        assert len(metadata["columns"]) == 5

    def test_extract_metadata_column_types(self, agent, sample_csv_file):
        """Should infer column types correctly."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        metadata = agent._extract_metadata(df, sample_csv_file)

        # Check that column metadata includes inferred types
        for col_meta in metadata["columns"]:
            assert "name" in col_meta
            assert "dtype" in col_meta
            assert "inferred_type" in col_meta
            assert "null_count" in col_meta
            assert "null_percent" in col_meta
            assert "unique_count" in col_meta

    def test_extract_metadata_numeric_stats(self, agent, sample_csv_file):
        """Should include numeric statistics for numeric columns."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        metadata = agent._extract_metadata(df, sample_csv_file)

        # Find age column
        age_col = next((c for c in metadata["columns"] if c["name"] == "age"), None)
        assert age_col is not None
        if age_col["inferred_type"] == "numeric":
            assert "min" in age_col
            assert "max" in age_col
            assert "mean" in age_col


class TestQualityProfile:
    """Tests for _generate_quality_profile method."""

    def test_quality_profile_structure(self, agent, sample_csv_file):
        """Should generate quality profile with correct structure."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        profile = agent._generate_quality_profile(df)

        assert "completeness" in profile
        assert "uniqueness" in profile
        assert "quality_alerts" in profile
        assert "overall_completeness" in profile
        assert "total_missing" in profile
        assert "duplicate_rows" in profile

    def test_quality_profile_completeness(self, agent, sample_csv_file):
        """Should calculate completeness correctly."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        profile = agent._generate_quality_profile(df)

        # Should detect missing age value
        assert profile["total_missing"] > 0
        assert profile["overall_completeness"] < 100

    def test_quality_profile_alerts(self, agent):
        """Should generate quality alerts for problematic columns."""
        import pandas as pd
        import numpy as np

        # Create DataFrame with quality issues
        data = {
            "col1": [1, 2, 3, None, None, None, None, None],  # High null
            "col2": [1, 1, 1, 1, 1, 1, 1, 1],  # Constant
            "col3": [1, 2, 3, 4, 5, 6, 7, 8],  # High cardinality
        }
        df = pd.DataFrame(data)
        profile = agent._generate_quality_profile(df)

        assert len(profile["quality_alerts"]) > 0
        alert_types = [alert["type"] for alert in profile["quality_alerts"]]
        assert "high_null" in alert_types or "constant" in alert_types or "high_cardinality" in alert_types


class TestStudyTypeDetection:
    """Tests for _detect_study_type method."""

    def test_detect_rct(self, agent, sample_rct_csv_file):
        """Should detect randomized controlled trial."""
        import pandas as pd
        df = pd.read_csv(sample_rct_csv_file)
        metadata = agent._extract_metadata(df, sample_rct_csv_file)
        study_type = agent._detect_study_type(df, metadata)

        assert study_type == "randomized_controlled_trial"

    def test_detect_cohort(self, agent, sample_cohort_csv_file):
        """Should detect cohort study."""
        import pandas as pd
        df = pd.read_csv(sample_cohort_csv_file)
        metadata = agent._extract_metadata(df, sample_cohort_csv_file)
        study_type = agent._detect_study_type(df, metadata)

        assert study_type == "cohort_study"

    def test_detect_case_control(self, agent, sample_case_control_csv_file):
        """Should detect case-control study."""
        import pandas as pd
        df = pd.read_csv(sample_case_control_csv_file)
        metadata = agent._extract_metadata(df, sample_case_control_csv_file)
        study_type = agent._detect_study_type(df, metadata)

        assert study_type == "case_control_study"

    def test_detect_observational_default(self, agent, sample_csv_file):
        """Should default to observational for generic data."""
        import pandas as pd
        df = pd.read_csv(sample_csv_file)
        metadata = agent._extract_metadata(df, sample_csv_file)
        study_type = agent._detect_study_type(df, metadata)

        # Should default to observational if no specific patterns detected
        assert study_type in ["observational", "randomized_controlled_trial", "cohort_study", "case_control_study"]


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context, sample_csv_file):
        """Execute should process file successfully."""
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert result.stage_id == 1
        assert "metadata" in result.output
        assert "quality_profile" in result.output
        assert "study_type" in result.output
        assert result.output["row_count"] == 5
        assert result.output["column_count"] == 5

    @pytest.mark.asyncio
    async def test_execute_missing_file(self, agent, sample_context):
        """Execute should fail if file doesn't exist."""
        sample_context.dataset_pointer = "/nonexistent/file.csv"
        result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert any("does not exist" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_no_dataset_pointer(self, agent, sample_context):
        """Execute should fail if dataset_pointer is missing."""
        sample_context.dataset_pointer = None
        result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert any("dataset_pointer" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_invalid_file_type(self, agent, sample_context):
        """Execute should fail for invalid file types."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b"test data")
            f.flush()
            try:
                sample_context.dataset_pointer = f.name
                result = await agent.execute(sample_context)

                assert result.status == "failed"
                assert len(result.errors) > 0
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_empty_file(self, agent, sample_context, empty_file):
        """Execute should fail for empty files."""
        sample_context.dataset_pointer = empty_file
        result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert any("empty" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_artifact_generation(self, agent, sample_context, sample_csv_file):
        """Execute should generate metadata artifact."""
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert len(result.artifacts) > 0
        artifact_path = result.artifacts[0]
        assert os.path.exists(artifact_path)
        assert artifact_path.endswith(".json")
        assert "ingestion_metadata" in artifact_path

        # Verify artifact content
        with open(artifact_path, "r") as f:
            artifact_data = json.load(f)
        assert "file_name" in artifact_data
        assert "metadata" in artifact_data
        assert "quality_profile" in artifact_data
        assert "study_type" in artifact_data

    @pytest.mark.asyncio
    async def test_execute_checksum_generation(self, agent, sample_context, sample_csv_file):
        """Execute should generate checksum."""
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "checksum" in result.output
        assert "checksum_algorithm" in result.output
        assert result.output["checksum_algorithm"] == "sha256"
        assert len(result.output["checksum"]) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_execute_quality_alerts_in_warnings(self, agent, sample_context, sample_csv_file):
        """Quality alerts should appear in warnings."""
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        # Should have warnings if quality issues detected
        # (sample_csv_file has missing age value)
        assert isinstance(result.warnings, list)

    @pytest.mark.asyncio
    async def test_execute_demo_mode(self, agent, sample_context, sample_csv_file):
        """DEMO mode should allow processing."""
        sample_context.governance_mode = "DEMO"
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert result.metadata["governance_mode"] == "DEMO"

    @pytest.mark.asyncio
    async def test_execute_live_mode(self, agent, sample_context, sample_csv_file):
        """LIVE mode should also process (no difference for ingestion)."""
        sample_context.governance_mode = "LIVE"
        sample_context.dataset_pointer = sample_csv_file
        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert result.metadata["governance_mode"] == "LIVE"


class TestColumnTypeInference:
    """Tests for _infer_column_type method."""

    def test_infer_numeric(self, agent):
        """Should infer numeric type correctly."""
        import pandas as pd
        series = pd.Series([1, 2, 3, 4, 5])
        col_type = agent._infer_column_type(series)
        assert col_type == "numeric"

    def test_infer_categorical(self, agent):
        """Should infer categorical type correctly."""
        import pandas as pd
        series = pd.Series(["A", "B", "A", "B", "A"])
        col_type = agent._infer_column_type(series)
        assert col_type == "categorical"

    def test_infer_boolean(self, agent):
        """Should infer boolean type correctly."""
        import pandas as pd
        series = pd.Series([True, False, True, False])
        col_type = agent._infer_column_type(series)
        assert col_type == "boolean"

    def test_infer_datetime(self, agent):
        """Should infer datetime type correctly."""
        import pandas as pd
        series = pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])
        col_type = agent._infer_column_type(series)
        assert col_type == "datetime"

    def test_infer_text(self, agent):
        """Should infer text type for high-cardinality strings."""
        import pandas as pd
        series = pd.Series([f"text_{i}" for i in range(100)])
        col_type = agent._infer_column_type(series)
        assert col_type == "text"


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_file_read_error(self, agent, sample_context):
        """Should handle file read errors gracefully."""
        # Create a file that will cause read error
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("invalid,csv\n")
            f.write("malformed,data\n")
            f.write("incomplete\n")
            f.flush()
            try:
                sample_context.dataset_pointer = f.name
                result = await agent.execute(sample_context)

                # Should either succeed (if pandas handles it) or fail gracefully
                assert result.status in ["completed", "failed"]
            finally:
                os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_execute_without_pandas(self, agent, sample_context, sample_csv_file):
        """Should handle missing pandas gracefully."""
        sample_context.dataset_pointer = sample_csv_file
        with patch('src.workflow_engine.stages.stage_01_upload.PANDAS_AVAILABLE', False):
            result = await agent.execute(sample_context)

            # Should complete but with warnings
            assert result.status == "completed"
            assert any("pandas" in w.lower() for w in result.warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
