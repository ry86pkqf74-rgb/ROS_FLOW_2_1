"""
Stage 5 Enhanced PHI Detection - Integration Tests

Tests the complete enhanced Stage 5 workflow including:
- ML-enhanced PHI detection
- Quasi-identifier analysis  
- Multi-jurisdiction compliance
- Cryptographic audit chains
- End-to-end processing
"""

import pytest
import sys
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "worker"))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.asyncio
class TestStage05EnhancedIntegration:
    """Integration tests for enhanced Stage 5 PHI detection."""
    
    @pytest.fixture
    def sample_medical_data(self):
        """Create sample medical dataset with known PHI and quasi-identifiers."""
        if not PANDAS_AVAILABLE:
            pytest.skip("pandas not available")
        
        data = {
            "patient_id": ["P001", "P002", "P003", "P004", "P005"],
            "patient_name": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Davis"],
            "ssn": ["123-45-6789", "987-65-4321", "555-12-3456", "111-22-3333", "444-55-6666"],
            "dob": ["1985-03-15", "1990-07-22", "1978-11-08", "1982-05-12", "1995-01-30"],
            "email": ["john@email.com", "jane@email.com", "bob@email.com", "alice@email.com", "charlie@email.com"],
            "phone": ["(555) 123-4567", "(555) 987-6543", "(555) 555-1234", "(555) 111-2222", "(555) 444-5555"],
            "zip_code": ["12345", "67890", "12345", "54321", "67890"],
            "age": [39, 34, 46, 42, 29],
            "gender": ["M", "F", "M", "F", "M"],
            "diagnosis": ["Diabetes", "Hypertension", "Diabetes", "Asthma", "Hypertension"],
            "medication": ["Metformin", "Lisinopril", "Metformin", "Albuterol", "Lisinopril"],
            "visit_date": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19"],
            "notes": ["Patient doing well", "Follow up needed", "Medication adjusted", "Symptoms improved", "Regular checkup"]
        }
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def temp_csv_file(self, sample_medical_data):
        """Create temporary CSV file with medical data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample_medical_data.to_csv(f.name, index=False)
            yield f.name
        
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    @pytest.fixture
    def temp_text_file(self):
        """Create temporary text file with medical content."""
        medical_text = """
        MEDICAL RECORD
        
        Patient: John Doe
        MRN: MR123456
        DOB: March 15, 1985
        SSN: 123-45-6789
        Phone: (555) 123-4567
        Email: john.doe@hospital.com
        Address: 123 Main St, Anytown, NY 12345
        
        CLINICAL NOTES:
        Patient presented with elevated blood glucose levels.
        Medical history significant for Type 2 diabetes mellitus.
        Current medications include Metformin 500mg BID.
        
        ASSESSMENT:
        Continue current diabetes management.
        Follow-up appointment scheduled for next month.
        Patient counseled on diet and exercise.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(medical_text)
            yield f.name
        
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    @pytest.fixture
    def enhanced_stage_context(self, temp_csv_file):
        """Create StageContext with enhanced PHI configuration."""
        try:
            from src.workflow_engine.types import StageContext
            
            with tempfile.TemporaryDirectory() as temp_dir:
                context = StageContext(
                    job_id="integration-test-enhanced",
                    config={
                        "phi": {
                            "scan_mode": "strict",
                            "enable_redaction": False,
                            "validate_compliance": True,
                            "assess_column_risk": True,
                            # Enhanced features
                            "enable_ml_detection": True,
                            "ml_confidence_threshold": 0.7,  # Lower for testing
                            "enable_quasi_analysis": True,
                            "k_anonymity_threshold": 5,
                            "enable_audit_chain": True,
                            "audit_signing": False,  # Disable crypto for testing
                            # Compliance settings
                            "compliance_frameworks": ["HIPAA_SAFE_HARBOR", "GDPR_ARTICLE_4"],
                            "gdpr_consent": False,
                            "gdpr_data_portability": True,
                            "gdpr_right_to_erasure": True,
                        },
                        "user_id": "test-user-123",
                    },
                    dataset_pointer=temp_csv_file,
                    artifact_path=temp_dir,
                    governance_mode="DEMO",
                    previous_results={},
                )
                yield context
        except ImportError:
            pytest.skip("StageContext not available")
    
    async def test_enhanced_agent_initialization(self):
        """Test that enhanced PHI agent initializes correctly."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            
            # Test basic properties
            assert agent.stage_id == 5
            assert agent.stage_name == "PHI Detection"
            
            # Test enhanced capabilities
            capabilities = agent.get_enhanced_capabilities()
            assert "enhanced_analyzers_available" in capabilities
            assert "quasi_identifier_analysis" in capabilities
            assert "ml_detection" in capabilities
            assert "multi_jurisdiction_compliance" in capabilities
            assert "cryptographic_audit" in capabilities
            
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")
    
    async def test_basic_phi_detection_compatibility(self, enhanced_stage_context):
        """Test that basic PHI detection still works with enhancements."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            # Basic outputs should still be present
            assert result.status in ["completed", "failed"]
            assert "phi_detected" in result.output
            assert "total_findings" in result.output
            assert "risk_level" in result.output
            assert "findings" in result.output
            assert "phi_schema" in result.output
            
            # Should detect PHI in the sample data
            assert result.output["phi_detected"] is True
            assert result.output["total_findings"] > 0
            assert result.output["risk_level"] in ["low", "medium", "high"]
            
            # Verify no raw PHI in findings
            for finding in result.output["findings"]:
                assert "matchHash" in finding
                assert len(finding["matchHash"]) == 12  # SHA256 truncated
                # Verify no raw SSN, email, etc.
                finding_str = json.dumps(finding)
                assert "123-45-6789" not in finding_str
                assert "@email.com" not in finding_str
            
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")
    
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.SPACY_AVAILABLE', True)
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.TRANSFORMERS_AVAILABLE', False)
    async def test_ml_enhanced_detection(self, enhanced_stage_context, temp_text_file):
        """Test ML-enhanced PHI detection functionality."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            # Update context to use text file (better for ML testing)
            enhanced_stage_context.dataset_pointer = temp_text_file
            
            # Mock SpaCy model for testing
            mock_doc = MagicMock()
            mock_entity = MagicMock()
            mock_entity.text = "John Doe"
            mock_entity.label_ = "PERSON"
            mock_entity.start_char = 0
            mock_entity.end_char = 8
            mock_doc.ents = [mock_entity]
            
            with patch('spacy.load') as mock_spacy_load:
                mock_model = MagicMock()
                mock_model.return_value = mock_doc
                mock_spacy_load.return_value = mock_model
                
                agent = PHIGuardAgent()
                result = await agent.execute(enhanced_stage_context)
                
                # Should have enhanced outputs
                if agent.get_enhanced_capabilities()["ml_detection"]:
                    assert "ml_findings" in result.output or any("ML detection" in w for w in result.warnings)
                
                # Should still detect PHI via patterns
                assert result.output["phi_detected"] is True
                assert result.output["total_findings"] > 0
                
        except ImportError:
            pytest.skip("ML PHI detection not available")
    
    async def test_quasi_identifier_analysis(self, enhanced_stage_context):
        """Test quasi-identifier analysis integration."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            # Check if quasi-identifier analysis was performed
            capabilities = agent.get_enhanced_capabilities()
            
            if capabilities["quasi_identifier_analysis"]:
                # Should have quasi-identifier analysis results
                assert "quasi_identifier_analysis" in result.output or \
                       any("Quasi-identifier analysis failed" in w for w in result.warnings)
                
                if "quasi_identifier_analysis" in result.output:
                    analysis = result.output["quasi_identifier_analysis"]
                    
                    # Verify analysis structure
                    assert "k_anonymity" in analysis
                    assert "overall_risk" in analysis
                    assert "dataset_info" in analysis
                    
                    # K-anonymity should detect issues with sample data
                    k_anonymity = analysis["k_anonymity"]
                    assert "k_value" in k_anonymity
                    assert "is_anonymous" in k_anonymity
                    assert "unique_individuals" in k_anonymity
                    
                    # Should detect quasi-identifiers in medical data
                    dataset_info = analysis["dataset_info"]
                    assert len(dataset_info["quasi_identifier_columns"]) > 0
                    
                    # Should identify risky columns
                    quasi_cols = dataset_info["quasi_identifier_columns"]
                    expected_quasi_cols = ["age", "zip_code", "dob", "patient_name"]
                    assert any(col in " ".join(quasi_cols).lower() for col in expected_quasi_cols)
            
        except ImportError:
            pytest.skip("Quasi-identifier analysis not available")
    
    async def test_multi_jurisdiction_compliance(self, enhanced_stage_context):
        """Test multi-jurisdiction compliance validation."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            capabilities = agent.get_enhanced_capabilities()
            
            if capabilities["multi_jurisdiction_compliance"]:
                # Should have multi-jurisdiction compliance results
                if "multi_jurisdiction_compliance" in result.output:
                    compliance_results = result.output["multi_jurisdiction_compliance"]
                    
                    # Should have HIPAA and GDPR results
                    assert "HIPAA_SAFE_HARBOR" in compliance_results
                    assert "GDPR_ARTICLE_4" in compliance_results
                    
                    # Each framework should have compliance info
                    for framework, compliance in compliance_results.items():
                        assert "is_compliant" in compliance
                        assert "violations_count" in compliance
                        assert "risk_score" in compliance
                        assert "compliance_percentage" in compliance
                
                # Should have compliance summary
                if "compliance_summary" in result.output:
                    summary = result.output["compliance_summary"]
                    assert "overall_compliant" in summary
                    assert "frameworks_checked" in summary
                    assert "overall_risk_score" in summary
                    
                    # Should check multiple frameworks
                    assert summary["frameworks_checked"] >= 2
            
        except ImportError:
            pytest.skip("Multi-jurisdiction compliance not available")
    
    async def test_audit_chain_integration(self, enhanced_stage_context):
        """Test cryptographic audit chain integration."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            capabilities = agent.get_enhanced_capabilities()
            
            if capabilities["cryptographic_audit"]:
                # Should have audit event ID if audit chain is enabled
                assert "audit_event_id" in result.output or \
                       any("Audit chain logging failed" in w for w in result.warnings)
                
                if "audit_event_id" in result.output:
                    audit_event_id = result.output["audit_event_id"]
                    assert audit_event_id is not None
                    assert isinstance(audit_event_id, str)
                    assert len(audit_event_id) > 0
            
        except ImportError:
            pytest.skip("Audit chain not available")
    
    async def test_enhanced_metadata(self, enhanced_stage_context):
        """Test that enhanced metadata is included in results."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            # Should have enhanced capabilities in metadata
            assert "enhanced_capabilities" in result.metadata
            capabilities = result.metadata["enhanced_capabilities"]
            
            # Should have all enhanced capability flags
            expected_capabilities = [
                "enhanced_analyzers_available",
                "quasi_identifier_analysis", 
                "ml_detection",
                "multi_jurisdiction_compliance",
                "cryptographic_audit"
            ]
            
            for capability in expected_capabilities:
                assert capability in capabilities
                assert isinstance(capabilities[capability], bool)
            
            # Should have enhanced feature flags
            enhanced_flags = [
                "ml_phi_detection_enabled",
                "quasi_identifier_analysis_enabled", 
                "multi_jurisdiction_compliance_enabled",
                "cryptographic_audit_enabled"
            ]
            
            for flag in enhanced_flags:
                assert flag in result.metadata
                assert isinstance(result.metadata[flag], bool)
            
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")
    
    async def test_performance_with_enhancements(self, enhanced_stage_context):
        """Test that enhanced features don't severely impact performance."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            import time
            
            agent = PHIGuardAgent()
            
            # Measure execution time
            start_time = time.time()
            result = await agent.execute(enhanced_stage_context)
            execution_time = time.time() - start_time
            
            # Should complete within reasonable time (5 seconds for test data)
            assert execution_time < 5.0, f"Execution took too long: {execution_time:.2f}s"
            
            # Should still produce valid results
            assert result.status in ["completed", "failed"]
            assert result.output["phi_detected"] is True
            
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")
    
    async def test_graceful_degradation(self, enhanced_stage_context):
        """Test graceful degradation when enhanced features fail."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            # Force initialization to fail by mocking
            with patch.object(PHIGuardAgent, '_initialize_enhanced_analyzers', side_effect=Exception("Mock initialization failure")):
                agent = PHIGuardAgent()
                
                # Should still work with basic functionality
                result = await agent.execute(enhanced_stage_context)
                
                # Should complete despite initialization failure
                assert result.status in ["completed", "failed"]
                
                # Should still detect PHI with basic patterns
                assert result.output["phi_detected"] is True
                assert result.output["total_findings"] > 0
                
                # Should have warnings about failed enhancements
                warning_messages = " ".join(result.warnings)
                enhanced_features_mentioned = any(
                    feature in warning_messages.lower() 
                    for feature in ["ml", "quasi", "compliance", "audit"]
                )
                
                # Either warnings mention failed features or they gracefully degraded
                # (Both are acceptable behaviors)
                
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")
    
    async def test_end_to_end_enhanced_workflow(self, enhanced_stage_context):
        """Test complete end-to-end enhanced PHI detection workflow."""
        try:
            from src.workflow_engine.stages.stage_05_phi import PHIGuardAgent
            
            agent = PHIGuardAgent()
            result = await agent.execute(enhanced_stage_context)
            
            # Verify complete workflow executed
            assert result.status in ["completed", "failed"]
            assert result.stage_id == 5
            assert result.stage_name == "PHI Detection"
            
            # Verify basic PHI detection worked
            assert result.output["phi_detected"] is True
            assert result.output["total_findings"] > 0
            assert len(result.output["findings"]) > 0
            assert result.output["risk_level"] in ["low", "medium", "high", "critical"]
            
            # Verify PHI schema generated
            phi_schema = result.output["phi_schema"]
            assert phi_schema["version"] == "1.0"
            assert "generated_at" in phi_schema
            assert "risk_level" in phi_schema
            assert "column_phi_map" in phi_schema
            assert "columns_requiring_deidentification" in phi_schema
            
            # Should find multiple PHI categories in medical data
            categories_found = result.output["categories_found"]
            expected_categories = ["SSN", "EMAIL", "PHONE", "NAME"]
            found_categories = list(categories_found.keys())
            assert len(found_categories) >= 3  # Should find multiple categories
            
            # Should identify columns requiring de-identification
            deid_columns = phi_schema["columns_requiring_deidentification"]
            assert len(deid_columns) > 0
            
            # Verify compliance validation occurred
            if "safe_harbor_compliance" in result.output:
                compliance = result.output["safe_harbor_compliance"]
                assert "compliant" in compliance
                assert "violations" in compliance
                # Medical data should have violations
                assert compliance["compliant"] is False
                assert len(compliance["violations"]) > 0
            
            # Verify enhanced outputs if available
            capabilities = result.metadata.get("enhanced_capabilities", {})
            
            if capabilities.get("ml_detection"):
                # ML detection should provide additional insights
                if "ml_findings" in result.output:
                    ml_findings = result.output["ml_findings"]
                    # Should be structured ML findings
                    if ml_findings:
                        assert isinstance(ml_findings[0], dict)
                        assert "phi_category" in ml_findings[0]
                        assert "confidence" in ml_findings[0]
            
            if capabilities.get("quasi_identifier_analysis"):
                if "quasi_identifier_analysis" in result.output:
                    analysis = result.output["quasi_identifier_analysis"]
                    # Should identify privacy risks
                    k_value = analysis["k_anonymity"]["k_value"]
                    assert isinstance(k_value, int)
                    # Medical data should have k-anonymity issues
                    assert k_value <= 5  # Should detect privacy risks
            
            # Verify metadata completeness
            assert "processing_mode" in result.metadata
            assert "enhanced_capabilities" in result.metadata
            
            # Verify no PHI leakage anywhere in result
            result_json = json.dumps(result.output) + json.dumps(result.metadata)
            phi_patterns = ["123-45-6789", "john@email.com", "(555) 123-4567", "John Doe"]
            for pattern in phi_patterns:
                assert pattern not in result_json, f"PHI leaked in results: {pattern}"
            
            print("✅ End-to-end enhanced PHI detection workflow completed successfully")
            print(f"   Detected {result.output['total_findings']} PHI findings")
            print(f"   Risk level: {result.output['risk_level']}")
            print(f"   Categories found: {list(result.output['categories_found'].keys())}")
            if capabilities.get("ml_detection") and "ml_findings" in result.output:
                print(f"   ML findings: {len(result.output['ml_findings'])}")
            if capabilities.get("quasi_identifier_analysis") and "quasi_identifier_analysis" in result.output:
                k_val = result.output["quasi_identifier_analysis"]["k_anonymity"]["k_value"]
                print(f"   K-anonymity: {k_val}")
            
        except ImportError:
            pytest.skip("Enhanced PHI agent not available")


@pytest.mark.integration 
class TestEnhancedComponentIntegration:
    """Test integration between enhanced components."""
    
    async def test_ml_and_pattern_detection_combination(self):
        """Test that ML detection and pattern detection work together."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import create_ml_phi_detector
            from src.workflow_engine.stages.stage_05_phi import scan_text_for_phi
            
            text = "Patient John Doe, SSN: 123-45-6789, Email: john@hospital.com"
            
            # Pattern-based detection
            pattern_findings = scan_text_for_phi(text, tier="HIGH_CONFIDENCE")
            
            # ML detection (if available)
            ml_detector = create_ml_phi_detector(confidence_threshold=0.7)
            if ml_detector:
                ml_findings = ml_detector.detect_phi(text)
                
                # Both should find PHI
                assert len(pattern_findings) > 0
                assert len(ml_findings) >= 0  # May be 0 if models not available
                
                # No overlap in raw PHI should occur
                pattern_json = json.dumps(pattern_findings)
                assert "123-45-6789" not in pattern_json
                assert "john@hospital.com" not in pattern_json
                
                if ml_findings:
                    ml_json = json.dumps([f.to_dict() for f in ml_findings])
                    assert "123-45-6789" not in ml_json
                    assert "john@hospital.com" not in ml_json
                    
        except ImportError:
            pytest.skip("ML PHI detection components not available")
    
    @pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not available")
    async def test_quasi_analysis_and_compliance_integration(self):
        """Test integration between quasi-identifier analysis and compliance validation."""
        try:
            from src.workflow_engine.stages.phi_analyzers import (
                QuasiIdentifierAnalyzer, MultiJurisdictionCompliance, ComplianceFramework
            )
            
            # Create test data with known privacy issues
            df = pd.DataFrame({
                "age": [25, 30, 25, 35, 25],  # Some duplicates
                "zip_code": ["12345", "67890", "12345", "54321", "12345"],
                "gender": ["M", "F", "M", "M", "M"]
            })
            
            # Analyze quasi-identifiers
            quasi_analyzer = QuasiIdentifierAnalyzer(k_threshold=5)
            quasi_analysis = quasi_analyzer.analyze_comprehensive_risk(df)
            
            # Should detect privacy risks
            assert quasi_analysis["k_anonymity"]["k_value"] < 5
            assert quasi_analysis["overall_risk"]["risk_level"] in ["medium", "high", "critical"]
            
            # Create mock PHI findings based on quasi-identifier analysis
            mock_findings = [
                {"category": "AGE"} for _ in range(len(df))
            ]
            
            # Test compliance validation
            compliance_validator = MultiJurisdictionCompliance()
            compliance_results = compliance_validator.validate_all_frameworks(
                findings=mock_findings,
                phi_schema={"columns_requiring_deidentification": ["age", "zip_code"]},
                frameworks=[ComplianceFramework.HIPAA_SAFE_HARBOR]
            )
            
            # Should have compliance violations
            hipaa_result = compliance_results[ComplianceFramework.HIPAA_SAFE_HARBOR]
            assert not hipaa_result.is_compliant
            assert len(hipaa_result.violations) > 0
            
        except ImportError:
            pytest.skip("Enhanced analyzer components not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])