"""
Tests for Multi-Jurisdiction Compliance Validator

Tests HIPAA, GDPR, and other privacy framework compliance validation.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "services" / "worker"))


class TestHIPAASafeHarborValidator:
    """Tests for HIPAA Safe Harbor compliance validation."""
    
    @pytest.fixture
    def validator(self):
        """Create HIPAA Safe Harbor validator."""
        try:
            from src.workflow_engine.stages.phi_analyzers.compliance_validator import HIPAASafeHarborValidator
            return HIPAASafeHarborValidator()
        except ImportError:
            pytest.skip("HIPAASafeHarborValidator not available")
    
    @pytest.fixture
    def sample_findings(self):
        """Sample PHI findings for testing."""
        return [
            {"category": "SSN"},
            {"category": "MRN"},
            {"category": "EMAIL"},
            {"category": "PHONE"},
            {"category": "NAME"},
            {"category": "DOB"},
            {"category": "ZIP_CODE"},
        ]
    
    @pytest.fixture
    def sample_phi_schema(self):
        """Sample PHI schema for testing."""
        return {
            "columns_requiring_deidentification": ["patient_ssn", "patient_email"],
            "column_phi_map": {
                "patient_ssn": ["SSN"],
                "patient_email": ["EMAIL"],
            }
        }
    
    def test_validator_initialization(self, validator):
        """Test validator initializes correctly."""
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        assert validator.framework == ComplianceFramework.HIPAA_SAFE_HARBOR
        assert len(validator.SAFE_HARBOR_IDENTIFIERS) == 18
        
        # Check that all 18 identifiers are present
        expected_identifiers = [
            "names", "geographic_subdivisions", "dates", "phone_numbers",
            "fax_numbers", "email_addresses", "social_security_numbers",
            "medical_record_numbers", "health_plan_beneficiary_numbers",
            "account_numbers", "certificate_license_numbers",
            "vehicle_identifiers", "device_identifiers", "web_urls",
            "ip_addresses", "biometric_identifiers", "photographs",
            "unique_identifying_numbers"
        ]
        
        for identifier in expected_identifiers:
            assert identifier in validator.SAFE_HARBOR_IDENTIFIERS
    
    def test_validation_with_violations(self, validator, sample_findings, sample_phi_schema):
        """Test validation when PHI violations exist."""
        result = validator.validate(sample_findings, sample_phi_schema)
        
        assert result.is_compliant is False
        assert len(result.violations) > 0
        assert result.risk_score > 0
        
        # Check that critical identifiers are detected
        violation_descriptions = [v.description for v in result.violations]
        assert any("social_security_numbers" in desc for desc in violation_descriptions)
        assert any("medical_record_numbers" in desc for desc in violation_descriptions)
    
    def test_validation_no_violations(self, validator):
        """Test validation when no PHI violations exist."""
        empty_findings = []
        empty_schema = {"columns_requiring_deidentification": []}
        
        result = validator.validate(empty_findings, empty_schema)
        
        assert result.is_compliant is True
        assert len(result.violations) == 0
        assert result.risk_score == 0
        assert len(result.compliant_categories) >= 0
    
    def test_date_generalization_handling(self, validator):
        """Test handling of date generalization requirements."""
        dob_findings = [{"category": "DOB"}]
        schema = {}
        
        # Test without date generalization
        result = validator.validate(dob_findings, schema, dates_generalized=False)
        assert not result.is_compliant
        assert any("date" in v.description.lower() for v in result.violations)
        
        # Test with date generalization
        result = validator.validate(dob_findings, schema, dates_generalized=True)
        # Should have fewer violations (date-specific violation removed)
        assert "dates_generalized" in result.metadata
        assert result.metadata["dates_generalized"] is True
    
    def test_zip_generalization_handling(self, validator):
        """Test handling of ZIP code generalization requirements."""
        zip_findings = [{"category": "ZIP_CODE"}]
        schema = {}
        
        # Test without ZIP generalization
        result = validator.validate(zip_findings, schema, zip_generalized=False)
        assert not result.is_compliant
        assert any("zip" in v.description.lower() for v in result.violations)
        
        # Test with ZIP generalization
        result = validator.validate(zip_findings, schema, zip_generalized=True)
        assert "zip_generalized" in result.metadata
        assert result.metadata["zip_generalized"] is True
    
    def test_age_generalization_handling(self, validator):
        """Test handling of age generalization requirements."""
        age_findings = [{"category": "AGE_OVER_89"}]
        schema = {}
        
        # Test without age generalization
        result = validator.validate(age_findings, schema, ages_generalized=False)
        assert not result.is_compliant
        assert any("age" in v.description.lower() for v in result.violations)
        
        # Test with age generalization
        result = validator.validate(age_findings, schema, ages_generalized=True)
        assert "ages_generalized" in result.metadata
        assert result.metadata["ages_generalized"] is True
    
    def test_risk_score_calculation(self, validator):
        """Test risk score calculation logic."""
        # Critical violations
        critical_findings = [{"category": "SSN"}, {"category": "MRN"}]
        result = validator.validate(critical_findings, {})
        critical_score = result.risk_score
        
        # Medium violations
        medium_findings = [{"category": "URL"}]
        result = validator.validate(medium_findings, {})
        medium_score = result.risk_score
        
        # Critical should have higher score than medium
        assert critical_score > medium_score
        
        # No violations should have zero score
        result = validator.validate([], {})
        assert result.risk_score == 0
    
    def test_remediation_suggestions(self, validator):
        """Test that appropriate remediation suggestions are provided."""
        findings = [{"category": "SSN"}, {"category": "NAME"}]
        schema = {}
        
        result = validator.validate(findings, schema)
        
        # Should have remediation suggestions
        assert len(result.recommendations) > 0
        
        # Should include specific recommendations
        recommendations_text = " ".join(result.recommendations)
        assert "remove" in recommendations_text.lower() or "redact" in recommendations_text.lower()
        assert "compliance" in recommendations_text.lower() or "hipaa" in recommendations_text.lower()


class TestGDPRValidator:
    """Tests for GDPR compliance validation."""
    
    @pytest.fixture
    def validator(self):
        """Create GDPR validator."""
        try:
            from src.workflow_engine.stages.phi_analyzers.compliance_validator import GDPRValidator
            return GDPRValidator()
        except ImportError:
            pytest.skip("GDPRValidator not available")
    
    def test_validator_initialization(self, validator):
        """Test GDPR validator initializes correctly."""
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        assert validator.framework == ComplianceFramework.GDPR_ARTICLE_4
        assert len(validator.PERSONAL_DATA_CATEGORIES) >= 8
        
        # Check key personal data categories
        expected_categories = [
            "direct_identifiers", "indirect_identifiers", "special_categories",
            "behavioral_data", "financial_data", "location_data"
        ]
        
        for category in expected_categories:
            assert category in validator.PERSONAL_DATA_CATEGORIES
    
    def test_gdpr_validation_with_consent(self, validator):
        """Test GDPR validation when consent is provided."""
        findings = [{"category": "NAME"}, {"category": "EMAIL"}]
        schema = {}
        
        result = validator.validate(
            findings, schema,
            gdpr_consent=True,
            gdpr_data_portability=True,
            gdpr_right_to_erasure=True
        )
        
        # Should be compliant with proper consent and rights implementation
        assert result.is_compliant is True
        assert result.metadata["consent_provided"] is True
    
    def test_gdpr_validation_without_consent(self, validator):
        """Test GDPR validation when no consent provided."""
        findings = [{"category": "NAME"}, {"category": "EMAIL"}]
        schema = {}
        
        result = validator.validate(findings, schema, gdpr_consent=False)
        
        assert result.is_compliant is False
        assert len(result.violations) > 0
        
        # Should have violations for lack of legal basis
        violation_types = [v.violation_type for v in result.violations]
        assert "NO_LEGAL_BASIS" in violation_types
    
    def test_special_category_data(self, validator):
        """Test handling of special category personal data."""
        special_findings = [{"category": "MRN"}, {"category": "HEALTH_PLAN"}]
        schema = {}
        
        result = validator.validate(
            special_findings, schema,
            gdpr_consent=True,
            gdpr_explicit_consent=False  # No explicit consent for special categories
        )
        
        assert result.is_compliant is False
        
        # Should have specific violation for special categories
        violation_types = [v.violation_type for v in result.violations]
        assert "SPECIAL_CATEGORY_NO_CONSENT" in violation_types
    
    def test_data_subject_rights(self, validator):
        """Test data subject rights compliance."""
        findings = [{"category": "NAME"}]
        schema = {}
        
        result = validator.validate(
            findings, schema,
            gdpr_consent=True,
            gdpr_data_portability=False,
            gdpr_right_to_erasure=False
        )
        
        # Should have violations for missing data subject rights
        violation_types = [v.violation_type for v in result.violations]
        assert "NO_DATA_PORTABILITY" in violation_types or "NO_RIGHT_TO_ERASURE" in violation_types
    
    def test_gdpr_recommendations(self, validator):
        """Test GDPR-specific recommendations."""
        findings = [{"category": "EMAIL"}]
        schema = {}
        
        result = validator.validate(findings, schema)
        
        recommendations_text = " ".join(result.recommendations)
        assert "gdpr" in recommendations_text.lower() or "consent" in recommendations_text.lower()
        assert "legal basis" in recommendations_text.lower()


class TestMultiJurisdictionCompliance:
    """Tests for multi-jurisdiction compliance validation."""
    
    @pytest.fixture
    def validator(self):
        """Create multi-jurisdiction validator."""
        try:
            from src.workflow_engine.stages.phi_analyzers.compliance_validator import MultiJurisdictionCompliance
            return MultiJurisdictionCompliance()
        except ImportError:
            pytest.skip("MultiJurisdictionCompliance not available")
    
    def test_validator_initialization(self, validator):
        """Test multi-jurisdiction validator initializes correctly."""
        assert len(validator.validators) >= 2  # At least HIPAA and GDPR
        
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        # Should have HIPAA and GDPR validators
        assert ComplianceFramework.HIPAA_SAFE_HARBOR in validator.validators
        assert ComplianceFramework.GDPR_ARTICLE_4 in validator.validators
    
    def test_validate_all_frameworks(self, validator):
        """Test validation across all frameworks."""
        findings = [{"category": "EMAIL"}, {"category": "NAME"}]
        schema = {}
        
        results = validator.validate_all_frameworks(findings, schema)
        
        assert len(results) >= 2
        
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        # Should have results for each framework
        assert ComplianceFramework.HIPAA_SAFE_HARBOR in results
        assert ComplianceFramework.GDPR_ARTICLE_4 in results
        
        # Each result should be a ComplianceResult
        for framework, result in results.items():
            assert hasattr(result, 'is_compliant')
            assert hasattr(result, 'violations')
            assert hasattr(result, 'risk_score')
    
    def test_validate_specific_frameworks(self, validator):
        """Test validation of specific frameworks only."""
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        findings = [{"category": "EMAIL"}]
        schema = {}
        
        results = validator.validate_all_frameworks(
            findings, schema,
            frameworks=[ComplianceFramework.HIPAA_SAFE_HARBOR]
        )
        
        # Should only have HIPAA results
        assert len(results) == 1
        assert ComplianceFramework.HIPAA_SAFE_HARBOR in results
        assert ComplianceFramework.GDPR_ARTICLE_4 not in results
    
    def test_compliance_summary_generation(self, validator):
        """Test compliance summary generation."""
        findings = [{"category": "EMAIL"}]
        schema = {}
        
        results = validator.validate_all_frameworks(findings, schema)
        summary = validator.generate_compliance_summary(results)
        
        assert "overall_compliant" in summary
        assert "frameworks_checked" in summary
        assert "compliant_frameworks" in summary
        assert "non_compliant_frameworks" in summary
        assert "critical_violations" in summary
        assert "high_priority_actions" in summary
        assert "overall_risk_score" in summary
        
        # Should have checked multiple frameworks
        assert summary["frameworks_checked"] >= 2
    
    def test_framework_info(self, validator):
        """Test framework information retrieval."""
        framework_info = validator.get_framework_info()
        
        from src.workflow_engine.stages.phi_analyzers.compliance_validator import ComplianceFramework
        
        # Should have info for all frameworks
        for framework in ComplianceFramework:
            assert framework.value in framework_info
            
            info = framework_info[framework.value]
            assert "name" in info
            assert "description" in info
            assert "validator_available" in info
    
    def test_error_handling(self, validator):
        """Test error handling in validation."""
        # Test with None findings to trigger an error
        results = validator.validate_all_frameworks(None, {})
        
        # Should still return results (with error states)
        assert len(results) >= 1
        
        # Error results should have violations
        for framework, result in results.items():
            if not result.is_compliant:
                assert len(result.violations) > 0


class TestComplianceDataClasses:
    """Tests for compliance data classes."""
    
    def test_compliance_violation_creation(self):
        """Test ComplianceViolation creation."""
        try:
            from src.workflow_engine.stages.phi_analyzers.compliance_validator import (
                ComplianceViolation, ComplianceFramework
            )
            
            violation = ComplianceViolation(
                framework=ComplianceFramework.HIPAA_SAFE_HARBOR,
                violation_type="SAFE_HARBOR_IDENTIFIER_DETECTED",
                description="SSN detected in data",
                severity="critical",
                phi_categories=["SSN"],
                remediation_required=True,
                remediation_suggestions=["Remove SSN", "Use study IDs"]
            )
            
            assert violation.framework == ComplianceFramework.HIPAA_SAFE_HARBOR
            assert violation.violation_type == "SAFE_HARBOR_IDENTIFIER_DETECTED"
            assert violation.severity == "critical"
            assert violation.remediation_required is True
            assert len(violation.remediation_suggestions) == 2
            
        except ImportError:
            pytest.skip("ComplianceViolation not available")
    
    def test_compliance_result_properties(self):
        """Test ComplianceResult properties."""
        try:
            from src.workflow_engine.stages.phi_analyzers.compliance_validator import (
                ComplianceResult, ComplianceViolation, ComplianceFramework
            )
            
            critical_violation = ComplianceViolation(
                framework=ComplianceFramework.HIPAA_SAFE_HARBOR,
                violation_type="TEST",
                description="Test",
                severity="critical",
                phi_categories=[],
                remediation_required=True
            )
            
            result = ComplianceResult(
                framework=ComplianceFramework.HIPAA_SAFE_HARBOR,
                is_compliant=False,
                violations=[critical_violation],
                compliant_categories=["category1", "category2"],
                risk_score=85
            )
            
            # Test properties
            assert result.has_critical_violations is True
            assert result.compliance_percentage == 66.67  # 2 compliant out of 3 total (2 + 1)
            
        except ImportError:
            pytest.skip("ComplianceResult not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])