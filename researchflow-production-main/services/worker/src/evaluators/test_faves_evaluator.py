"""
Tests for FAVES Compliance Evaluator

Phase 10: Transparency & Compliance
"""

import os
import tempfile
import json
from datetime import datetime
from pathlib import Path

# Mock pytest if not available
try:
    import pytest
except ImportError:
    class MockPytest:
        @staticmethod
        def fixture(func):
            return func
    pytest = MockPytest()

from evaluators.faves_evaluator import (
    FAVESEvaluator,
    FAVESGate,
    FAVESRequirements,
    FAVESDimension,
    FAVESStatus,
    create_faves_evaluator,
)


class TestFAVESDimension:
    """Test FAVESDimension enum."""
    
    def test_dimension_values(self):
        """Test all dimension values are defined."""
        assert FAVESDimension.FAIR == "FAIR"
        assert FAVESDimension.APPROPRIATE == "APPROPRIATE"
        assert FAVESDimension.VALID == "VALID"
        assert FAVESDimension.EFFECTIVE == "EFFECTIVE"
        assert FAVESDimension.SAFE == "SAFE"


class TestFAVESStatus:
    """Test FAVESStatus enum."""
    
    def test_status_values(self):
        """Test all status values are defined."""
        assert FAVESStatus.PASS == "PASS"
        assert FAVESStatus.FAIL == "FAIL"
        assert FAVESStatus.PARTIAL == "PARTIAL"
        assert FAVESStatus.NOT_EVALUATED == "NOT_EVALUATED"


class TestFAVESRequirements:
    """Test FAVES requirements matrix."""
    
    def test_thresholds_exist(self):
        """Test thresholds defined for all dimensions."""
        requirements = FAVESRequirements()
        
        for dimension in FAVESDimension:
            assert dimension in requirements.THRESHOLDS
            assert isinstance(requirements.THRESHOLDS[dimension], dict)
    
    def test_artifacts_exist(self):
        """Test artifacts defined for all dimensions."""
        requirements = FAVESRequirements()
        
        for dimension in FAVESDimension:
            assert dimension in requirements.ARTIFACTS
            assert isinstance(requirements.ARTIFACTS[dimension], list)
            assert len(requirements.ARTIFACTS[dimension]) > 0
    
    def test_metrics_exist(self):
        """Test metrics defined for all dimensions."""
        requirements = FAVESRequirements()
        
        for dimension in FAVESDimension:
            assert dimension in requirements.METRICS
            assert isinstance(requirements.METRICS[dimension], list)
            assert len(requirements.METRICS[dimension]) > 0


class TestFAVESEvaluator:
    """Test FAVESEvaluator class."""
    
    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create temporary artifacts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def evaluator(self, temp_artifacts_dir):
        """Create evaluator instance."""
        return FAVESEvaluator(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            model_version="1.0.0",
            artifacts_dir=temp_artifacts_dir
        )
    
    @pytest.fixture
    def mock_metrics_provider(self):
        """Create mock metrics provider."""
        metrics = {
            "demographic_parity_gap": 0.08,
            "min_subgroup_auc": 0.75,
            "intended_use_coverage_score": 0.95,
            "workflow_fit_score": 0.85,
            "calibration_error": 0.09,
            "brier_score": 0.20,
            "external_validation_auc": 0.78,
            "net_benefit_at_threshold": 0.15,
            "overall_error_rate": 0.04,
            "failure_mode_coverage": 0.92,
        }
        
        def provider(metric_name: str):
            return metrics.get(metric_name)
        
        return provider
    
    def test_evaluator_initialization(self, evaluator):
        """Test evaluator initializes correctly."""
        assert evaluator.model_id == "550e8400-e29b-41d4-a716-446655440000"
        assert evaluator.model_version == "1.0.0"
        assert evaluator.requirements is not None
    
    def test_artifact_check_missing(self, evaluator):
        """Test artifact check for missing file."""
        artifact = evaluator._check_artifact("missing.md", required=True)
        
        assert artifact.name == "missing.md"
        assert artifact.required is True
        assert artifact.exists is False
        assert artifact.last_modified is None
    
    def test_artifact_check_exists(self, evaluator, temp_artifacts_dir):
        """Test artifact check for existing file."""
        # Create artifact file
        artifact_path = Path(temp_artifacts_dir) / "test.md"
        artifact_path.write_text("# Test Artifact")
        
        artifact = evaluator._check_artifact("test.md", required=True)
        
        assert artifact.name == "test.md"
        assert artifact.required is True
        assert artifact.exists is True
        assert artifact.last_modified is not None
    
    def test_evaluate_metric_passing(self, evaluator, mock_metrics_provider):
        """Test metric evaluation when passing threshold."""
        evaluator.metrics_provider = mock_metrics_provider
        
        result = evaluator._evaluate_metric(
            "min_subgroup_auc",
            "min_subgroup_auc",
            {"min_subgroup_auc": 0.7},
            higher_is_better=True
        )
        
        assert result is not None
        assert result.metric_name == "min_subgroup_auc"
        assert result.value == 0.75
        assert result.threshold == 0.7
        assert result.passed is True
    
    def test_evaluate_metric_failing(self, evaluator, mock_metrics_provider):
        """Test metric evaluation when failing threshold."""
        evaluator.metrics_provider = mock_metrics_provider
        
        # Override to fail
        evaluator.metrics_provider = lambda name: 0.15 if name == "demographic_parity_gap" else None
        
        result = evaluator._evaluate_metric(
            "demographic_parity_gap",
            "demographic_parity_gap",
            {"demographic_parity_gap": 0.1},
            higher_is_better=False
        )
        
        assert result is not None
        assert result.value == 0.15
        assert result.threshold == 0.1
        assert result.passed is False
    
    def test_evaluate_fairness_no_artifacts(self, evaluator, mock_metrics_provider):
        """Test fairness evaluation without artifacts."""
        evaluator.metrics_provider = mock_metrics_provider
        
        result = evaluator.evaluate_fairness()
        
        assert result.dimension == FAVESDimension.FAIR
        assert result.score >= 0
        assert result.score <= 100
        assert len(result.metrics) > 0
        assert len(result.required_artifacts) > 0
        # Should fail due to missing artifacts
        assert result.passed is False
    
    def test_evaluate_fairness_with_artifacts(self, evaluator, temp_artifacts_dir, mock_metrics_provider):
        """Test fairness evaluation with all artifacts."""
        evaluator.metrics_provider = mock_metrics_provider
        
        # Create required artifacts
        for artifact_name, _ in evaluator.requirements.ARTIFACTS[FAVESDimension.FAIR]:
            artifact_path = Path(temp_artifacts_dir) / artifact_name
            artifact_path.write_text(f"# {artifact_name}")
        
        result = evaluator.evaluate_fairness()
        
        assert result.dimension == FAVESDimension.FAIR
        assert result.passed is True
        assert result.score > 0
    
    def test_evaluate_appropriateness(self, evaluator, temp_artifacts_dir):
        """Test appropriateness evaluation."""
        # Create required artifacts
        for artifact_name, required in evaluator.requirements.ARTIFACTS[FAVESDimension.APPROPRIATE]:
            if required:
                artifact_path = Path(temp_artifacts_dir) / artifact_name
                artifact_path.write_text(f"# {artifact_name}\n\nContent here.")
        
        result = evaluator.evaluate_appropriateness()
        
        assert result.dimension == FAVESDimension.APPROPRIATE
        assert result.score >= 0
        assert len(result.required_artifacts) > 0
    
    def test_evaluate_validity(self, evaluator, mock_metrics_provider):
        """Test validity evaluation."""
        evaluator.metrics_provider = mock_metrics_provider
        
        result = evaluator.evaluate_validity()
        
        assert result.dimension == FAVESDimension.VALID
        assert result.score >= 0
        assert len(result.metrics) > 0
    
    def test_evaluate_effectiveness(self, evaluator, temp_artifacts_dir):
        """Test effectiveness evaluation."""
        # Create required artifacts
        for artifact_name, required in evaluator.requirements.ARTIFACTS[FAVESDimension.EFFECTIVE]:
            if required:
                artifact_path = Path(temp_artifacts_dir) / artifact_name
                artifact_path.write_text(f"# {artifact_name}")
        
        result = evaluator.evaluate_effectiveness()
        
        assert result.dimension == FAVESDimension.EFFECTIVE
        assert result.score >= 0
    
    def test_evaluate_safety(self, evaluator, temp_artifacts_dir):
        """Test safety evaluation."""
        # Create required artifacts
        for artifact_name, required in evaluator.requirements.ARTIFACTS[FAVESDimension.SAFE]:
            if required:
                artifact_path = Path(temp_artifacts_dir) / artifact_name
                artifact_path.write_text(f"# {artifact_name}")
        
        result = evaluator.evaluate_safety()
        
        assert result.dimension == FAVESDimension.SAFE
        assert result.score >= 0
        assert len(result.required_artifacts) > 0
    
    def test_full_evaluation(self, evaluator, temp_artifacts_dir, mock_metrics_provider):
        """Test full FAVES evaluation."""
        evaluator.metrics_provider = mock_metrics_provider
        
        # Create all required artifacts
        for dimension in FAVESDimension:
            for artifact_name, required in evaluator.requirements.ARTIFACTS[dimension]:
                if required:
                    artifact_path = Path(temp_artifacts_dir) / artifact_name
                    artifact_path.write_text(f"# {artifact_name}\n\nContent here.")
        
        result = evaluator.evaluate()
        
        # Verify result structure
        assert result.evaluation_id is not None
        assert result.model_id == evaluator.model_id
        assert result.model_version == evaluator.model_version
        assert result.overall_status in [FAVESStatus.PASS, FAVESStatus.FAIL, FAVESStatus.PARTIAL]
        assert 0 <= result.overall_score <= 100
        assert result.deployment_allowed in [True, False]
        
        # Verify all dimensions evaluated
        assert "fair" in result.dimensions
        assert "appropriate" in result.dimensions
        assert "valid" in result.dimensions
        assert "effective" in result.dimensions
        assert "safe" in result.dimensions
        
        # Verify metrics
        assert result.total_metrics_passed >= 0
        assert result.total_metrics_failed >= 0
        
        # Verify artifacts
        assert result.total_artifacts_present >= 0
        assert result.total_artifacts_missing >= 0
    
    def test_evaluation_all_pass(self, evaluator, temp_artifacts_dir, mock_metrics_provider):
        """Test evaluation when all dimensions pass."""
        evaluator.metrics_provider = mock_metrics_provider
        
        # Create all required artifacts
        for dimension in FAVESDimension:
            for artifact_name, required in evaluator.requirements.ARTIFACTS[dimension]:
                if required:
                    artifact_path = Path(temp_artifacts_dir) / artifact_name
                    artifact_path.write_text(f"# {artifact_name}\n\nSufficient content.")
        
        result = evaluator.evaluate()
        
        assert result.overall_status == FAVESStatus.PASS
        assert result.deployment_allowed is True
        assert len(result.blocking_issues) == 0
    
    def test_evaluation_blocking_issues(self, evaluator):
        """Test evaluation identifies blocking issues."""
        result = evaluator.evaluate()
        
        # Without artifacts and metrics, should fail
        assert result.overall_status in [FAVESStatus.FAIL, FAVESStatus.PARTIAL]
        assert result.deployment_allowed is False
        assert len(result.blocking_issues) > 0
    
    def test_to_json(self, evaluator):
        """Test JSON serialization."""
        result = evaluator.evaluate()
        json_str = evaluator.to_json(result)
        
        # Verify valid JSON
        parsed = json.loads(json_str)
        
        assert parsed["model_id"] == evaluator.model_id
        assert parsed["model_version"] == evaluator.model_version
        assert "overall_status" in parsed
        assert "dimensions" in parsed


class TestFAVESGate:
    """Test FAVESGate CI/CD enforcement."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evaluator = FAVESEvaluator(
                model_id="550e8400-e29b-41d4-a716-446655440000",
                model_version="1.0.0",
                artifacts_dir=tmpdir
            )
            yield evaluator
    
    def test_gate_initialization(self, evaluator):
        """Test gate initializes correctly."""
        gate = FAVESGate(evaluator)
        assert gate.evaluator is evaluator
    
    def test_gate_check_failing(self, evaluator):
        """Test gate check when evaluation fails."""
        gate = FAVESGate(evaluator)
        passed, result = gate.check()
        
        assert passed is False
        assert result.deployment_allowed is False
    
    def test_gate_check_passing(self, evaluator):
        """Test gate check when evaluation passes."""
        # Mock passing metrics
        def mock_provider(name):
            return 0.85  # All metrics pass
        
        evaluator.metrics_provider = mock_provider
        
        # Create all artifacts
        for dimension in FAVESDimension:
            for artifact_name, required in evaluator.requirements.ARTIFACTS[dimension]:
                if required:
                    artifact_path = Path(evaluator.artifacts_dir) / artifact_name
                    artifact_path.write_text("# Content")
        
        gate = FAVESGate(evaluator)
        passed, result = gate.check()
        
        # Should pass with all artifacts and passing metrics
        assert passed is True
        assert result.deployment_allowed is True


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_faves_evaluator(self):
        """Test factory function creates evaluator."""
        evaluator = create_faves_evaluator(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            model_version="2.0.0",
            artifacts_dir="docs/faves"
        )
        
        assert isinstance(evaluator, FAVESEvaluator)
        assert evaluator.model_id == "550e8400-e29b-41d4-a716-446655440000"
        assert evaluator.model_version == "2.0.0"
        assert evaluator.artifacts_dir == "docs/faves"


# Run tests if executed directly
if __name__ == "__main__":
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running basic tests...")
        
        # Run basic tests without pytest
        test_dim = TestFAVESDimension()
        test_dim.test_dimension_values()
        print("✓ TestFAVESDimension.test_dimension_values")
        
        test_status = TestFAVESStatus()
        test_status.test_status_values()
        print("✓ TestFAVESStatus.test_status_values")
        
        test_req = TestFAVESRequirements()
        test_req.test_thresholds_exist()
        test_req.test_artifacts_exist()
        test_req.test_metrics_exist()
        print("✓ TestFAVESRequirements (all tests)")
        
        print("\n✅ Basic tests passed. Install pytest for full test suite.")
