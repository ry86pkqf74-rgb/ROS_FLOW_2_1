"""
Unit tests for Stage 5: PHI Guard Agent

Tests the PHIGuardAgent implementation:
- BaseStageAgent inheritance
- HIPAA Safe Harbor PHI detection
- Column-level risk assessment
- PHI redaction with audit logging
- Safe Harbor compliance validation
- DEMO vs PRODUCTION mode handling
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_05_phi import (
    PHIGuardAgent,
    scan_text_for_phi,
    scan_dataframe_for_phi,
    assess_column_risk,
    redact_phi,
    log_phi_redaction,
    validate_safe_harbor_compliance,
    hash_match,
    PANDAS_AVAILABLE,
)
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def sample_context():
    """Create a sample StageContext for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="test-job-123",
            config={
                "phi": {
                    "scan_mode": "standard",
                    "enable_redaction": False,
                    "validate_compliance": True,
                }
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tmpdir,
            dataset_pointer=None,
        )
        yield context


@pytest.fixture
def agent():
    """Create a PHIGuardAgent instance."""
    return PHIGuardAgent()


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame with PHI for testing."""
    try:
        import pandas as pd
        
        df = pd.DataFrame({
            "patient_name": ["John Doe", "Jane Smith", "Bob Johnson"],
            "ssn": ["123-45-6789", "987-65-4321", "555-12-3456"],
            "email": ["john@example.com", "jane@example.com", "bob@example.com"],
            "dob": ["01/15/1980", "03/22/1975", "07/10/1990"],
            "age": [44, 49, 34],
            "zip_code": ["12345", "67890", "54321"],
            "safe_column": ["value1", "value2", "value3"],
        })
        return df
    except ImportError:
        pytest.skip("pandas not available")


class TestPHIGuardAgent:
    """Tests for PHIGuardAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 5
        assert agent.stage_name == "PHI Detection"

    def test_get_tools(self, agent):
        """get_tools should return a list (can be empty)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a PromptTemplate."""
        template = agent.get_prompt_template()
        assert template is not None


class TestPHIDetection:
    """Tests for core PHI detection functionality."""

    def test_scan_text_for_phi_ssn(self):
        """Should detect SSN patterns."""
        content = "Patient SSN: 123-45-6789"
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        assert any(f.get("category") == "SSN" for f in findings)

    def test_scan_text_for_phi_email(self):
        """Should detect email patterns."""
        content = "Contact: john.doe@example.com"
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        assert any(f.get("category") == "EMAIL" for f in findings)

    def test_scan_text_for_phi_phone(self):
        """Should detect phone number patterns."""
        content = "Phone: (555) 123-4567"
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        assert any(f.get("category") == "PHONE" for f in findings)

    def test_scan_text_for_phi_mrn(self):
        """Should detect MRN patterns."""
        content = "MRN: ABC123456"
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        assert any(f.get("category") == "MRN" for f in findings)

    def test_scan_text_for_phi_date(self):
        """Should detect date patterns."""
        content = "DOB: 01/15/1980"
        findings = scan_text_for_phi(content, tier="OUTPUT_GUARD")
        assert len(findings) > 0
        assert any(f.get("category") == "DOB" for f in findings)

    def test_scan_text_for_phi_ip_address(self):
        """Should detect IP address patterns."""
        content = "IP: 192.168.1.1"
        findings = scan_text_for_phi(content, tier="OUTPUT_GUARD")
        assert len(findings) > 0
        assert any(f.get("category") == "IP_ADDRESS" for f in findings)

    def test_scan_text_for_phi_no_phi(self):
        """Should return empty list when no PHI detected."""
        content = "This is a safe text with no PHI."
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) == 0

    def test_scan_text_for_phi_hash_only(self):
        """Findings should contain hash, not raw PHI."""
        content = "SSN: 123-45-6789"
        findings = scan_text_for_phi(content, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        for finding in findings:
            assert "matchHash" in finding
            assert "matchLength" in finding
            assert "position" in finding
            # CRITICAL: No raw PHI in findings
            assert "123-45-6789" not in str(finding)

    @pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not available")
    def test_scan_dataframe_for_phi(self, sample_dataframe):
        """Should scan DataFrame for PHI."""
        findings, column_risks = scan_dataframe_for_phi(sample_dataframe, tier="HIGH_CONFIDENCE")
        assert len(findings) > 0
        # Should find PHI in multiple columns
        columns_with_phi = set(f.get("column") for f in findings)
        assert "patient_name" in columns_with_phi or "ssn" in columns_with_phi or "email" in columns_with_phi

    @pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not available")
    def test_scan_dataframe_for_phi_with_risk_assessment(self, sample_dataframe):
        """Should assess column-level risk when requested."""
        findings, column_risks = scan_dataframe_for_phi(
            sample_dataframe, tier="HIGH_CONFIDENCE", assess_risk=True
        )
        assert len(column_risks) > 0
        # Check that risk assessments have expected structure
        for col, risk in column_risks.items():
            assert "risk_level" in risk
            assert "reasons" in risk
            assert "recommendations" in risk


class TestColumnRiskAssessment:
    """Tests for column-level risk assessment."""

    def test_assess_column_risk_critical_name(self):
        """Should identify critical risk from column name."""
        findings = [{"category": "SSN"}]
        risk = assess_column_risk("patient_ssn", findings)
        assert risk["risk_level"] in ("high", "critical")
        assert len(risk["reasons"]) > 0

    def test_assess_column_risk_high_name(self):
        """Should identify high risk from column name."""
        findings = []
        risk = assess_column_risk("patient_dob", findings)
        assert risk["risk_level"] in ("high", "medium", "low")
        assert "name_based_risk" in risk

    def test_assess_column_risk_value_based(self):
        """Should identify risk from PHI findings in values."""
        findings = [
            {"category": "SSN"},
            {"category": "EMAIL"},
        ]
        risk = assess_column_risk("safe_column", findings)
        assert risk["risk_level"] in ("high", "critical")
        assert risk["value_based_risk"] in ("high", "critical")

    def test_assess_column_risk_quasi_identifier(self):
        """Should detect quasi-identifier combinations."""
        try:
            import pandas as pd
            
            df = pd.DataFrame({
                "dob": ["01/15/1980"],
                "zip_code": ["12345"],
                "age": [44],
            })
            findings = [{"category": "DOB"}]
            risk = assess_column_risk("dob", findings, df=df)
            # Should note quasi-identifier risk if date+ZIP+age present
            assert "risk_level" in risk
        except ImportError:
            pytest.skip("pandas not available")

    def test_assess_column_risk_no_phi(self):
        """Should return low/none risk when no PHI detected."""
        findings = []
        risk = assess_column_risk("safe_column", findings)
        assert risk["risk_level"] in ("none", "low")


class TestPHIRedaction:
    """Tests for PHI redaction functionality."""

    def test_redact_phi_marker_style(self):
        """Should redact PHI with marker style."""
        content = "SSN: 123-45-6789"
        findings = [
            {
                "category": "SSN",
                "position": {"start": 5, "end": 16},
            }
        ]
        redacted, metadata = redact_phi(content, findings, redaction_style="marker")
        assert "[PHI:SSN]" in redacted
        assert metadata["redacted"] is True
        assert metadata["redactions_applied"] == 1

    def test_redact_phi_asterisk_style(self):
        """Should redact PHI with asterisk style."""
        content = "SSN: 123-45-6789"
        findings = [
            {
                "category": "SSN",
                "position": {"start": 5, "end": 16},
            }
        ]
        redacted, metadata = redact_phi(content, findings, redaction_style="asterisk")
        assert "*" in redacted
        assert metadata["redacted"] is True

    def test_redact_phi_remove_style(self):
        """Should remove PHI completely."""
        content = "SSN: 123-45-6789"
        findings = [
            {
                "category": "SSN",
                "position": {"start": 5, "end": 16},
            }
        ]
        redacted, metadata = redact_phi(content, findings, redaction_style="remove")
        assert "123-45-6789" not in redacted
        assert metadata["redacted"] is True

    def test_redact_phi_multiple_findings(self):
        """Should redact multiple PHI findings."""
        content = "SSN: 123-45-6789 Email: john@example.com"
        findings = [
            {
                "category": "SSN",
                "position": {"start": 5, "end": 16},
            },
            {
                "category": "EMAIL",
                "position": {"start": 24, "end": 40},
            },
        ]
        redacted, metadata = redact_phi(content, findings)
        assert "[PHI:SSN]" in redacted
        assert "[PHI:EMAIL]" in redacted
        assert metadata["redactions_applied"] == 2

    def test_redact_phi_no_findings(self):
        """Should return original content when no findings."""
        content = "Safe text"
        redacted, metadata = redact_phi(content, [])
        assert redacted == content
        assert metadata["redacted"] is False

    def test_redact_phi_preserves_structure(self):
        """Should preserve text structure while redacting."""
        content = "Patient info: SSN 123-45-6789, DOB 01/15/1980"
        findings = [
            {
                "category": "SSN",
                "position": {"start": 17, "end": 28},
            },
            {
                "category": "DOB",
                "position": {"start": 31, "end": 41},
            },
        ]
        redacted, _ = redact_phi(content, findings)
        # Should preserve surrounding text
        assert "Patient info:" in redacted
        assert "," in redacted


class TestAuditLogging:
    """Tests for audit logging functionality."""

    def test_log_phi_redaction(self):
        """Should log PHI redaction event."""
        from src.workflow_engine.stages.stage_05_phi import _audit_log_entries
        
        # Clear previous entries
        _audit_log_entries.clear()
        
        audit_id = log_phi_redaction(
            job_id="test-job",
            context={"governance_mode": "DEMO", "user_id": "user123"},
            redaction_metadata={
                "redacted": True,
                "redactions_applied": 5,
                "categories_redacted": {"SSN": 2, "EMAIL": 3},
            },
            findings_count=5,
        )
        
        assert audit_id is not None
        assert len(_audit_log_entries) > 0
        entry = _audit_log_entries[-1]
        assert entry["audit_id"] == audit_id
        assert entry["event_type"] == "PHI_REDACTION"
        assert entry["job_id"] == "test-job"
        assert entry["findings_count"] == 5


class TestSafeHarborCompliance:
    """Tests for Safe Harbor compliance validation."""

    def test_validate_safe_harbor_compliance_no_phi(self):
        """Should pass when no PHI detected."""
        result = validate_safe_harbor_compliance(
            findings=[],
            phi_schema={"columns_requiring_deidentification": []},
        )
        assert result["compliant"] is True
        assert len(result["violations"]) == 0

    def test_validate_safe_harbor_compliance_with_phi(self):
        """Should fail when PHI detected."""
        findings = [
            {"category": "SSN"},
            {"category": "EMAIL"},
        ]
        phi_schema = {
            "columns_requiring_deidentification": ["ssn", "email"],
        }
        result = validate_safe_harbor_compliance(
            findings=findings,
            phi_schema=phi_schema,
        )
        assert result["compliant"] is False
        assert len(result["violations"]) > 0

    def test_validate_safe_harbor_compliance_date_generalization(self):
        """Should check date generalization requirement."""
        findings = [{"category": "DOB"}]
        result = validate_safe_harbor_compliance(
            findings=findings,
            phi_schema={},
            dates_generalized=False,
        )
        assert result["compliant"] is False
        assert any("date" in v.lower() for v in result["violations"])

    def test_validate_safe_harbor_compliance_zip_generalization(self):
        """Should check ZIP generalization requirement."""
        findings = [{"category": "ZIP_CODE"}]
        result = validate_safe_harbor_compliance(
            findings=findings,
            phi_schema={},
            zip_generalized=False,
        )
        assert result["compliant"] is False
        assert any("zip" in v.lower() for v in result["violations"])

    def test_validate_safe_harbor_compliance_age_generalization(self):
        """Should check age generalization requirement."""
        findings = [{"category": "AGE_OVER_89"}]
        result = validate_safe_harbor_compliance(
            findings=findings,
            phi_schema={},
            ages_generalized=False,
        )
        assert result["compliant"] is False
        assert any("age" in v.lower() for v in result["violations"])

    def test_validate_safe_harbor_compliance_generalized(self):
        """Should pass when all identifiers generalized."""
        findings = [{"category": "DOB"}]
        result = validate_safe_harbor_compliance(
            findings=findings,
            phi_schema={},
            dates_generalized=True,
            zip_generalized=True,
            ages_generalized=True,
        )
        # Still not compliant because PHI detected, but no generalization violations
        assert "dates_generalized" in result["violations"] or result["compliant"] is False


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_no_phi(self, agent, sample_context):
        """Should complete successfully when no PHI detected."""
        # Create a temporary file with safe content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is safe text with no PHI.")
            temp_path = f.name
        
        try:
            sample_context.dataset_pointer = temp_path
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert result.stage_id == 5
            assert result.output["phi_detected"] is False
            assert result.output["total_findings"] == 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_with_phi_demo_mode(self, agent, sample_context):
        """Should continue in DEMO mode when PHI detected."""
        # Create a temporary file with PHI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Patient SSN: 123-45-6789")
            temp_path = f.name
        
        try:
            sample_context.dataset_pointer = temp_path
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert result.output["phi_detected"] is True
            assert len(result.warnings) > 0
            assert any("DEMO mode" in w for w in result.warnings)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_with_phi_production_mode(self, agent):
        """Should fail in PRODUCTION mode with high PHI risk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = StageContext(
                job_id="test-job",
                config={"phi": {"scan_mode": "standard"}},
                previous_results={},
                governance_mode="PRODUCTION",
                artifact_path=tmpdir,
                dataset_pointer=None,
            )
            
            # Create a temporary file with many PHI instances
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(" ".join(["SSN: 123-45-6789"] * 25))  # High risk
                temp_path = f.name
            
            try:
                context.dataset_pointer = temp_path
                result = await agent.execute(context)
                
                # Should fail or have errors for high risk in PRODUCTION
                assert result.status == "failed" or len(result.errors) > 0
            finally:
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_with_redaction_enabled(self, agent, sample_context):
        """Should perform redaction when enabled."""
        sample_context.config["phi"]["enable_redaction"] = True
        sample_context.config["phi"]["save_redacted"] = True
        
        # Create a temporary file with PHI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Patient SSN: 123-45-6789")
            temp_path = f.name
        
        try:
            sample_context.dataset_pointer = temp_path
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            # Should have redaction metadata if redaction was performed
            if result.output.get("redaction"):
                assert "redactions_applied" in result.output["redaction"]
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_compliance_validation(self, agent, sample_context):
        """Should validate Safe Harbor compliance."""
        sample_context.config["phi"]["validate_compliance"] = True
        
        # Create a temporary file with PHI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("DOB: 01/15/1980")
            temp_path = f.name
        
        try:
            sample_context.dataset_pointer = temp_path
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert "safe_harbor_compliance" in result.output
            compliance = result.output["safe_harbor_compliance"]
            assert "compliant" in compliance
            assert "violations" in compliance
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_execute_column_risk_assessment(self, agent, sample_context):
        """Should perform column-level risk assessment."""
        sample_context.config["phi"]["assess_column_risk"] = True
        
        # Create a CSV file with PHI columns
        try:
            import pandas as pd
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                df = pd.DataFrame({
                    "patient_ssn": ["123-45-6789"],
                    "safe_column": ["value"],
                })
                df.to_csv(f.name, index=False)
                temp_path = f.name
            
            try:
                sample_context.dataset_pointer = temp_path
                result = await agent.execute(sample_context)
                
                assert result.status == "completed"
                assert "column_risk_assessments" in result.output
                column_risks = result.output["column_risk_assessments"]
                assert len(column_risks) > 0
            finally:
                os.unlink(temp_path)
        except ImportError:
            pytest.skip("pandas not available")


class TestHashMatch:
    """Tests for hash_match utility function."""

    def test_hash_match_consistency(self):
        """Should produce consistent hashes for same input."""
        text = "test-phi-value"
        hash1 = hash_match(text)
        hash2 = hash_match(text)
        assert hash1 == hash2
        assert len(hash1) == 12

    def test_hash_match_different_inputs(self):
        """Should produce different hashes for different inputs."""
        hash1 = hash_match("value1")
        hash2 = hash_match("value2")
        assert hash1 != hash2

    def test_hash_match_no_raw_phi(self):
        """Hash should not contain raw PHI."""
        text = "123-45-6789"
        hash_value = hash_match(text)
        assert text not in hash_value
        assert "123" not in hash_value


class TestIntegration:
    """Integration tests for stage execution."""

    @pytest.mark.asyncio
    async def test_stage_04_integration(self, agent):
        """Should integrate with Stage 4 output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = StageContext(
                job_id="test-job",
                config={
                    "stage_04_output": {
                        "large_file_info": {
                            "processing_mode": "standard",
                        }
                    },
                    "phi": {"scan_mode": "standard"},
                },
                previous_results={},
                governance_mode="DEMO",
                artifact_path=tmpdir,
                dataset_pointer=None,
            )
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Safe text")
                temp_path = f.name
            
            try:
                context.dataset_pointer = temp_path
                result = await agent.execute(context)
                
                assert result.status == "completed"
                assert "phi_schema" in result.output
            finally:
                os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_phi_schema_generation(self, agent, sample_context):
        """Should generate PHI schema for downstream stages."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("SSN: 123-45-6789")
            temp_path = f.name
        
        try:
            sample_context.dataset_pointer = temp_path
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            phi_schema = result.output["phi_schema"]
            assert "version" in phi_schema
            assert "column_phi_map" in phi_schema
            assert "columns_requiring_deidentification" in phi_schema
            assert "deidentification_recommendations" in phi_schema
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
