"""
Tests for Stage 2 IRB Submission Agent

Comprehensive test suite covering all models, helper functions, and agent functionality
for the IRB submission preparation workflow.
"""

import pytest
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

from .irb_submission_agent import (
    IRBSubmissionAgent,
    IRBSubmissionState,
    Investigator,
    TrainingCertification,
    COIDisclosure,
    PopulationDescription,
    Risk,
    RiskAssessment,
    ConsentForm,
    IRBApplication,
    determine_review_type,
    assess_flesch_kincaid,
    check_hipaa_requirements,
    generate_risk_mitigation,
    validate_citi_training,
    _requires_full_board,
    _qualifies_for_exemption,
    _qualifies_for_expedited,
    _count_syllables
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_training():
    """Sample training certification."""
    return TrainingCertification(
        type="CITI",
        completion_date=date.today() - timedelta(days=30),
        expiration_date=date.today() + timedelta(days=335),  # 3 years from completion
        modules_completed=[
            "Basic Human Subjects Research",
            "Informed Consent",
            "Responsibilities of Principal Investigators",
            "Research with Vulnerable Populations"
        ],
        certificate_number="CITI12345"
    )


@pytest.fixture  
def sample_coi():
    """Sample COI disclosure."""
    return COIDisclosure(
        has_conflicts=False,
        conflicts_description=None,
        financial_interests=[],
        management_plan=None,
        last_updated=date.today() - timedelta(days=10)
    )


@pytest.fixture
def sample_investigator(sample_training, sample_coi):
    """Sample principal investigator."""
    return Investigator(
        name="Dr. Jane Smith",
        credentials=["MD", "PhD"],
        institution="University Medical Center",
        department="Internal Medicine",
        email="jane.smith@umc.edu",
        role="PI",
        human_subjects_training=sample_training,
        coi_disclosure=sample_coi
    )


@pytest.fixture
def sample_population():
    """Sample population description."""
    return PopulationDescription(
        target_population="Adults with Type 2 diabetes",
        inclusion_criteria=[
            "Age 18-75 years",
            "Diagnosed Type 2 diabetes",
            "HbA1c 7-10%"
        ],
        exclusion_criteria=[
            "Type 1 diabetes",
            "Pregnancy",
            "Severe kidney disease"
        ],
        sample_size=100,
        vulnerable_populations=[],
        recruitment_sites=["University Medical Center", "Community Health Clinic"],
        age_range="18-75",
        sex_distribution="50% male, 50% female"
    )


@pytest.fixture
def sample_risk():
    """Sample risk assessment item."""
    return Risk(
        category="Physical",
        description="Risk of hypoglycemia from blood draws",
        likelihood="Unlikely",
        severity="Minimal",
        mitigation="Monitor blood glucose levels, provide snacks"
    )


@pytest.fixture
def sample_protocol():
    """Sample protocol data."""
    return {
        "study_type": "observational survey",
        "risk_level": "minimal risk",
        "data_sensitivity": "non-sensitive",
        "data_type": "identifiable survey responses",
        "title": "Diabetes Self-Management Survey Study",
        "objectives": ["Assess self-management behaviors", "Identify barriers to care"]
    }


@pytest.fixture
def irb_agent():
    """IRB Submission Agent instance."""
    return IRBSubmissionAgent()


# =============================================================================
# Model Validation Tests
# =============================================================================

class TestTrainingCertification:
    """Test TrainingCertification model validation."""
    
    def test_valid_training(self, sample_training):
        """Test valid training certification."""
        assert sample_training.type == "CITI"
        assert sample_training.expiration_date > sample_training.completion_date
        
    def test_invalid_expiration_date(self):
        """Test invalid expiration date validation."""
        with pytest.raises(ValueError, match="Expiration date must be after completion date"):
            TrainingCertification(
                type="CITI",
                completion_date=date.today(),
                expiration_date=date.today() - timedelta(days=1),
                modules_completed=["Basic Human Subjects Research"]
            )


class TestInvestigator:
    """Test Investigator model validation."""
    
    def test_valid_investigator(self, sample_investigator):
        """Test valid investigator creation."""
        assert sample_investigator.name == "Dr. Jane Smith"
        assert sample_investigator.role == "PI"
        assert "@" in sample_investigator.email
        
    def test_invalid_email(self, sample_training, sample_coi):
        """Test invalid email validation."""
        with pytest.raises(ValueError, match="Invalid email address"):
            Investigator(
                name="Dr. Test",
                credentials=["MD"],
                institution="Test Hospital",
                department="Medicine",
                email="invalid-email",
                role="PI",
                human_subjects_training=sample_training,
                coi_disclosure=sample_coi
            )
            
    def test_invalid_role(self, sample_training, sample_coi):
        """Test invalid role validation."""
        with pytest.raises(ValueError, match="Role must be one of"):
            Investigator(
                name="Dr. Test",
                credentials=["MD"],
                institution="Test Hospital", 
                department="Medicine",
                email="test@example.com",
                role="Invalid Role",
                human_subjects_training=sample_training,
                coi_disclosure=sample_coi
            )


class TestRisk:
    """Test Risk model validation."""
    
    def test_valid_risk(self, sample_risk):
        """Test valid risk creation."""
        assert sample_risk.category == "Physical"
        assert sample_risk.likelihood == "Unlikely"
        assert sample_risk.severity == "Minimal"
        
    def test_invalid_category(self):
        """Test invalid risk category."""
        with pytest.raises(ValueError, match="Category must be one of"):
            Risk(
                category="InvalidCategory",
                description="Test risk",
                likelihood="Unlikely", 
                severity="Minimal",
                mitigation="Test mitigation"
            )
            
    def test_invalid_likelihood(self):
        """Test invalid likelihood value."""
        with pytest.raises(ValueError, match="Likelihood must be one of"):
            Risk(
                category="Physical",
                description="Test risk",
                likelihood="InvalidLikelihood",
                severity="Minimal", 
                mitigation="Test mitigation"
            )


class TestIRBSubmissionState:
    """Test IRBSubmissionState model validation."""
    
    def test_valid_state(self, sample_investigator):
        """Test valid state creation."""
        state = IRBSubmissionState(
            study_id="STUDY001",
            protocol={"title": "Test Study"},
            principal_investigator=sample_investigator,
            institution="University Medical Center",
            irb_type="Local",
            review_type="Expedited"
        )
        assert state.study_id == "STUDY001"
        assert state.approval_status == "Draft"
        assert state.current_stage == 2
        
    def test_invalid_approval_status(self, sample_investigator):
        """Test invalid approval status."""
        with pytest.raises(ValueError, match="Approval status must be one of"):
            IRBSubmissionState(
                study_id="STUDY001",
                protocol={"title": "Test Study"},
                principal_investigator=sample_investigator,
                institution="University Medical Center",
                irb_type="Local",
                review_type="Expedited",
                approval_status="Invalid Status"
            )


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestReviewTypeDetermination:
    """Test review type determination logic."""
    
    def test_full_board_vulnerable_populations(self, sample_protocol):
        """Test full board required for vulnerable populations."""
        population = PopulationDescription(
            target_population="Children with asthma",
            inclusion_criteria=["Age 6-17 years"],
            exclusion_criteria=[],
            sample_size=50,
            vulnerable_populations=["children"],
            recruitment_sites=["Children's Hospital"]
        )
        
        result = determine_review_type(sample_protocol, population)
        assert result == "Full Board"
        
    def test_full_board_high_risk(self, sample_population):
        """Test full board required for high risk studies."""
        protocol = {
            "study_type": "drug intervention trial",
            "risk_level": "greater than minimal risk"
        }
        
        result = determine_review_type(protocol, sample_population)
        assert result == "Full Board"
        
    def test_exempt_survey_study(self, sample_population):
        """Test exempt classification for appropriate survey."""
        protocol = {
            "study_type": "survey questionnaire",
            "risk_level": "minimal risk",
            "data_sensitivity": "non-sensitive",
            "data_type": "non-identifiable survey responses"
        }
        
        result = determine_review_type(protocol, sample_population)
        assert result == "Exempt"
        
    def test_expedited_observational(self, sample_population):
        """Test expedited classification for observational study."""
        protocol = {
            "study_type": "observational non-invasive",
            "risk_level": "minimal risk"
        }
        
        result = determine_review_type(protocol, sample_population)
        assert result == "Expedited"


class TestFleschKincaidAssessment:
    """Test reading level assessment."""
    
    def test_simple_text_grade_level(self):
        """Test grade level calculation for simple text."""
        text = "This is a simple test. It has short sentences. The words are easy."
        grade_level = assess_flesch_kincaid(text)
        assert isinstance(grade_level, float)
        assert 0 <= grade_level <= 20
        
    def test_complex_text_grade_level(self):
        """Test grade level calculation for complex text."""
        text = """The pharmacokinetic characteristics of the investigational 
                  compound demonstrate significant bioavailability parameters 
                  that necessitate comprehensive evaluation of therapeutic efficacy."""
        grade_level = assess_flesch_kincaid(text)
        assert grade_level > 10  # Should be high school+ level
        
    def test_empty_text(self):
        """Test grade level for empty text."""
        grade_level = assess_flesch_kincaid("")
        assert grade_level == 0.0
        
    def test_syllable_counting(self):
        """Test syllable counting helper function."""
        # Simple test cases
        assert _count_syllables("cat") == 1
        assert _count_syllables("table") == 2  
        assert _count_syllables("computer") >= 3
        assert _count_syllables("hello world") >= 3


class TestHIPAARequirements:
    """Test HIPAA requirements determination."""
    
    def test_requires_hipaa_with_identifiers(self):
        """Test HIPAA required when identifiers present."""
        data_elements = [
            "participant_name",
            "date_of_birth", 
            "survey_responses",
            "contact_phone"
        ]
        assert check_hipaa_requirements(data_elements) is True
        
    def test_no_hipaa_without_identifiers(self):
        """Test HIPAA not required without identifiers."""
        data_elements = [
            "age_group",
            "survey_responses",
            "study_condition",
            "anonymous_id"
        ]
        assert check_hipaa_requirements(data_elements) is False
        
    def test_hipaa_with_medical_record_numbers(self):
        """Test HIPAA required with medical record numbers."""
        data_elements = [
            "medical_record_number",
            "diagnosis_codes"
        ]
        assert check_hipaa_requirements(data_elements) is True


class TestRiskMitigation:
    """Test risk mitigation strategy generation."""
    
    def test_physical_risk_mitigation(self):
        """Test mitigation for physical risks."""
        risks = [
            Risk(
                category="Physical",
                description="Blood draw discomfort",
                likelihood="Possible",
                severity="Minimal",
                mitigation="Use trained phlebotomist"
            )
        ]
        
        mitigation_map = generate_risk_mitigation(risks)
        assert "Physical" in mitigation_map
        assert "safety protocols" in mitigation_map["Physical"].lower()
        
    def test_psychological_risk_mitigation(self):
        """Test mitigation for psychological risks."""
        risks = [
            Risk(
                category="Psychological",
                description="Anxiety from questionnaire topics",
                likelihood="Possible",
                severity="Minimal",
                mitigation="Provide counseling resources"
            )
        ]
        
        mitigation_map = generate_risk_mitigation(risks)
        assert "Psychological" in mitigation_map
        assert "counseling" in mitigation_map["Psychological"].lower()


class TestTrainingValidation:
    """Test investigator training validation."""
    
    def test_valid_pi_training(self, sample_investigator):
        """Test validation for properly trained PI."""
        errors = validate_citi_training(sample_investigator)
        assert len(errors) == 0
        
    def test_expired_training(self, sample_coi):
        """Test validation with expired training."""
        expired_training = TrainingCertification(
            type="CITI",
            completion_date=date.today() - timedelta(days=1100),
            expiration_date=date.today() - timedelta(days=100), 
            modules_completed=["Basic Human Subjects Research"]
        )
        
        investigator = Investigator(
            name="Dr. Test",
            credentials=["MD"],
            institution="Test Hospital",
            department="Medicine",
            email="test@example.com", 
            role="PI",
            human_subjects_training=expired_training,
            coi_disclosure=sample_coi
        )
        
        errors = validate_citi_training(investigator)
        assert len(errors) > 0
        assert "expired" in errors[0].lower()
        
    def test_missing_pi_modules(self, sample_coi):
        """Test validation with missing required modules."""
        incomplete_training = TrainingCertification(
            type="CITI",
            completion_date=date.today() - timedelta(days=30),
            expiration_date=date.today() + timedelta(days=335),
            modules_completed=["Basic Human Subjects Research"]  # Missing PI modules
        )
        
        investigator = Investigator(
            name="Dr. Test",
            credentials=["MD"],
            institution="Test Hospital",
            department="Medicine", 
            email="test@example.com",
            role="PI",
            human_subjects_training=incomplete_training,
            coi_disclosure=sample_coi
        )
        
        errors = validate_citi_training(investigator)
        assert len(errors) > 0
        assert "missing required modules" in errors[0].lower()


# =============================================================================
# Agent Integration Tests
# =============================================================================

class TestIRBSubmissionAgent:
    """Test IRBSubmissionAgent integration."""
    
    def test_agent_initialization(self, irb_agent):
        """Test agent initialization."""
        assert irb_agent.agent_id == 'irb_submission'
        assert irb_agent.stage == 2
        assert "IRB submission" in irb_agent.description
        
    def test_determine_review_type_integration(self, irb_agent, sample_protocol, sample_population):
        """Test review type determination through agent."""
        review_type = irb_agent.determine_review_type(sample_protocol, sample_population)
        assert review_type in ["Full Board", "Expedited", "Exempt"]
        
    def test_assess_reading_level_integration(self, irb_agent):
        """Test reading level assessment through agent."""
        text = "This consent form explains the research study."
        grade_level = irb_agent.assess_reading_level(text)
        assert isinstance(grade_level, float)
        assert grade_level >= 0
        
    def test_hipaa_requirements_integration(self, irb_agent):
        """Test HIPAA requirements check through agent."""
        data_elements = ["name", "medical_record_number"]
        requires_hipaa = irb_agent.check_hipaa_requirements(data_elements)
        assert requires_hipaa is True
        
    def test_training_validation_integration(self, irb_agent, sample_investigator):
        """Test training validation through agent."""
        errors = irb_agent.validate_investigator_training(sample_investigator)
        assert isinstance(errors, list)


# =============================================================================
# Edge Case and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_protocol_data(self, sample_population):
        """Test handling of empty protocol data."""
        empty_protocol = {}
        result = determine_review_type(empty_protocol, sample_population)
        assert result == "Full Board"  # Should default to most restrictive
        
    def test_unknown_study_type(self, sample_population):
        """Test handling of unknown study type."""
        protocol = {
            "study_type": "completely unknown type",
            "risk_level": "unknown risk"
        }
        result = determine_review_type(protocol, sample_population)
        assert result == "Full Board"  # Should default to most restrictive
        
    def test_mixed_risk_signals(self, sample_population):
        """Test handling of conflicting risk signals."""
        protocol = {
            "study_type": "survey",  # Suggests exempt
            "risk_level": "greater than minimal risk"  # Suggests full board
        }
        result = determine_review_type(protocol, sample_population)
        assert result == "Full Board"  # Should prioritize safety
        
    def test_reading_level_extreme_cases(self):
        """Test reading level calculation for extreme cases."""
        # Single word
        assert assess_flesch_kincaid("Hello.") >= 0
        
        # Very long sentence
        long_text = "This is a very long sentence " * 20 + "."
        grade_level = assess_flesch_kincaid(long_text)
        assert grade_level > 15  # Should be high complexity
        
    def test_hipaa_case_insensitive(self):
        """Test HIPAA detection is case insensitive."""
        data_elements = ["PARTICIPANT_NAME", "Date_Of_Birth", "PHONE_NUMBER"]
        assert check_hipaa_requirements(data_elements) is True


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test performance of key functions."""
    
    def test_reading_level_performance(self):
        """Test reading level calculation performance."""
        # Large text should still process reasonably quickly
        large_text = "This is a test sentence. " * 1000
        
        import time
        start_time = time.time()
        grade_level = assess_flesch_kincaid(large_text)
        end_time = time.time()
        
        assert end_time - start_time < 1.0  # Should complete within 1 second
        assert isinstance(grade_level, float)
        
    def test_hipaa_detection_performance(self):
        """Test HIPAA detection performance with many data elements."""
        # Large list of data elements
        data_elements = [f"data_element_{i}" for i in range(1000)]
        data_elements.extend(["name", "phone"])  # Add identifiers
        
        import time
        start_time = time.time()
        result = check_hipaa_requirements(data_elements)
        end_time = time.time()
        
        assert end_time - start_time < 1.0  # Should complete within 1 second
        assert result is True


if __name__ == "__main__":
    # Run tests if script executed directly
    pytest.main([__file__, "-v"])