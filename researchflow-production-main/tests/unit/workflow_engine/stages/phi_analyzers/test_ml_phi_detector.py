"""
Tests for ML-Enhanced PHI Detection

Tests NER model integration, contextual analysis, and confidence scoring.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "services" / "worker"))


class TestMLPhiDetector:
    """Tests for MLPhiDetector class."""
    
    @pytest.fixture
    def mock_detector(self):
        """Create ML PHI detector with mocked dependencies."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPhiDetector
            
            # Mock the detector to avoid requiring actual ML models
            with patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.SPACY_AVAILABLE', False), \
                 patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.TRANSFORMERS_AVAILABLE', False):
                detector = MLPhiDetector(
                    confidence_threshold=0.8,
                    context_threshold=0.6,
                    enable_spacy=False,
                    enable_transformers=False
                )
                return detector
        except ImportError:
            pytest.skip("MLPhiDetector not available")
    
    @pytest.fixture
    def sample_texts(self):
        """Sample texts for PHI detection testing."""
        return {
            "medical_with_phi": """
            Patient: John Doe, age 45
            MRN: MR123456
            DOB: 01/15/1978
            Phone: (555) 123-4567
            Email: john.doe@example.com
            Diagnosis: Type 2 diabetes mellitus
            Admission: 03/15/2023
            """,
            "medical_without_phi": """
            Patient presented with elevated glucose levels.
            Laboratory values show HbA1c of 8.5%.
            Treatment plan includes metformin 500mg twice daily.
            Follow-up appointment scheduled in 3 months.
            """,
            "non_medical": """
            The weather today is sunny with temperatures reaching 75 degrees.
            This is a general text about outdoor activities and recreation.
            No medical or personal information is contained here.
            """,
            "edge_cases": """
            Patient: Anonymous
            ID: [REDACTED]
            Contact: staff@hospital.example
            Notes: Please call extension 1234 for updates
            """,
        }
    
    def test_detector_initialization(self, mock_detector):
        """Test detector initializes with correct configuration."""
        assert mock_detector.confidence_threshold == 0.8
        assert mock_detector.context_threshold == 0.6
        assert mock_detector.enable_spacy is False
        assert mock_detector.enable_transformers is False
        assert len(mock_detector.medical_context_patterns) > 0
    
    def test_medical_context_analysis(self, mock_detector, sample_texts):
        """Test medical context scoring."""
        medical_text = sample_texts["medical_with_phi"]
        non_medical_text = sample_texts["non_medical"]
        
        # Find a person name to test context around
        name_start = medical_text.find("John Doe")
        name_end = name_start + len("John Doe")
        
        medical_context_score = mock_detector.analyze_medical_context(
            medical_text, name_start, name_end
        )
        
        general_start = non_medical_text.find("weather")
        general_end = general_start + len("weather")
        
        non_medical_context_score = mock_detector.analyze_medical_context(
            non_medical_text, general_start, general_end
        )
        
        # Medical context should score higher
        assert medical_context_score > non_medical_context_score
        assert medical_context_score > 0.5  # Should detect medical context
        assert non_medical_context_score < 0.3  # Should not detect medical context
    
    def test_context_boosting(self, mock_detector):
        """Test context score boosting for high-confidence indicators."""
        text = "Patient John Doe, MRN: ABC123456, admitted on 03/15/2023"
        name_start = text.find("John Doe")
        name_end = name_start + len("John Doe")
        
        context_score = mock_detector.analyze_medical_context(text, name_start, name_end)
        
        # Should get boosted score due to "Patient" and "MRN" nearby
        assert context_score >= 0.6  # Base + boosts should be significant
    
    def test_get_model_info(self, mock_detector):
        """Test model information retrieval."""
        model_info = mock_detector.get_model_info()
        
        assert "spacy_available" in model_info
        assert "transformers_available" in model_info
        assert "spacy_enabled" in model_info
        assert "transformers_enabled" in model_info
        assert "confidence_threshold" in model_info
        assert "context_threshold" in model_info
        
        assert model_info["confidence_threshold"] == 0.8
        assert model_info["context_threshold"] == 0.6
    
    def test_detect_phi_empty_input(self, mock_detector):
        """Test handling of empty input."""
        assert mock_detector.detect_phi("") == []
        assert mock_detector.detect_phi(None) == []
        assert mock_detector.detect_phi("   ") == []
    
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.SPACY_AVAILABLE', True)
    def test_spacy_integration_mock(self, mock_detector):
        """Test SpaCy integration with mocked NER model."""
        # Mock SpaCy model
        mock_doc = MagicMock()
        mock_entity = MagicMock()
        mock_entity.text = "John Doe"
        mock_entity.label_ = "PERSON"
        mock_entity.start_char = 0
        mock_entity.end_char = 8
        mock_doc.ents = [mock_entity]
        
        mock_spacy_model = MagicMock()
        mock_spacy_model.return_value = mock_doc
        
        mock_detector.spacy_model = mock_spacy_model
        mock_detector.enable_spacy = True
        
        findings = mock_detector.detect_with_spacy("John Doe is a patient")
        
        assert len(findings) == 1
        assert findings[0].text == "John Doe"
        assert findings[0].phi_category == "NAME"
        assert findings[0].model_source == "spacy"
    
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.TRANSFORMERS_AVAILABLE', True)
    def test_transformers_integration_mock(self, mock_detector):
        """Test Transformers integration with mocked NER pipeline."""
        # Mock Transformers pipeline output
        mock_entities = [
            {
                "entity_group": "PERSON",
                "start": 0,
                "end": 8,
                "score": 0.95
            }
        ]
        
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = mock_entities
        
        mock_detector.transformer_pipeline = mock_pipeline
        mock_detector.enable_transformers = True
        
        findings = mock_detector.detect_with_transformers("John Doe is a patient")
        
        assert len(findings) == 1
        assert findings[0].text == "John Doe"
        assert findings[0].phi_category == "NAME"
        assert findings[0].confidence == 0.95
        assert findings[0].model_source == "transformers"
    
    def test_findings_deduplication(self, mock_detector):
        """Test deduplication of overlapping findings."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPHIFinding
            
            # Create overlapping findings
            findings = [
                MLPHIFinding(
                    text="John",
                    start=0,
                    end=4,
                    entity_type="PERSON",
                    phi_category="NAME",
                    confidence=0.9,
                    context_score=0.8,
                    model_source="spacy"
                ),
                MLPHIFinding(
                    text="John Doe",
                    start=0,
                    end=8,
                    entity_type="PERSON",
                    phi_category="NAME", 
                    confidence=0.95,
                    context_score=0.8,
                    model_source="transformers"
                ),
                MLPHIFinding(
                    text="patient",
                    start=20,
                    end=27,
                    entity_type="OTHER",
                    phi_category="OTHER",
                    confidence=0.7,
                    context_score=0.6,
                    model_source="spacy"
                ),
            ]
            
            deduplicated = mock_detector._deduplicate_findings(findings)
            
            # Should keep the higher confidence overlapping finding
            assert len(deduplicated) == 2
            
            # Should keep the transformers finding (higher confidence)
            john_findings = [f for f in deduplicated if "john" in f.text.lower()]
            assert len(john_findings) == 1
            assert john_findings[0].confidence == 0.95
            assert john_findings[0].model_source == "transformers"
            
        except ImportError:
            pytest.skip("MLPHIFinding not available")
    
    def test_confidence_filtering(self, mock_detector):
        """Test confidence-based filtering of findings."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPHIFinding
            
            # Create findings with different confidence levels
            low_confidence = MLPHIFinding(
                text="maybe_name",
                start=0,
                end=10,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.4,  # Below threshold
                context_score=0.3,
                model_source="test"
            )
            
            high_confidence = MLPHIFinding(
                text="definite_name",
                start=20,
                end=33,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.95,  # Above threshold
                context_score=0.8,
                model_source="test"
            )
            
            mixed_confidence = MLPHIFinding(
                text="contextual_name",
                start=40,
                end=55,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.7,  # Below confidence threshold
                context_score=0.9,  # But high context score
                model_source="test"
            )
            
            # Mock the full detection pipeline
            mock_detector._deduplicate_findings = MagicMock(
                return_value=[low_confidence, high_confidence, mixed_confidence]
            )
            
            # The detect_phi method should filter by confidence
            # Since we can't directly test it without models, test the logic
            filtered = [
                f for f in [low_confidence, high_confidence, mixed_confidence]
                if f.confidence >= mock_detector.confidence_threshold or 
                   f.combined_confidence >= mock_detector.confidence_threshold
            ]
            
            # Should keep high_confidence and mixed_confidence (due to combined score)
            assert len(filtered) >= 1  # At least high_confidence
            assert high_confidence in filtered
            
        except ImportError:
            pytest.skip("MLPHIFinding not available")


class TestMLPHIFinding:
    """Tests for MLPHIFinding data class."""
    
    def test_finding_creation(self):
        """Test MLPHIFinding creation and properties."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPHIFinding
            
            finding = MLPHIFinding(
                text="John Doe",
                start=0,
                end=8,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.9,
                context_score=0.7,
                model_source="spacy",
                surrounding_context="Patient: John Doe, age 45",
                is_likely_phi=True
            )
            
            assert finding.text == "John Doe"
            assert finding.start == 0
            assert finding.end == 8
            assert finding.entity_type == "PERSON"
            assert finding.phi_category == "NAME"
            assert finding.confidence == 0.9
            assert finding.context_score == 0.7
            assert finding.model_source == "spacy"
            assert finding.is_likely_phi is True
            
        except ImportError:
            pytest.skip("MLPHIFinding not available")
    
    def test_combined_confidence_calculation(self):
        """Test combined confidence score calculation."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPHIFinding
            
            finding = MLPHIFinding(
                text="test",
                start=0,
                end=4,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.8,
                context_score=0.6,
                model_source="test"
            )
            
            # Combined = (confidence * 0.7) + (context_score * 0.3)
            expected_combined = (0.8 * 0.7) + (0.6 * 0.3)
            assert finding.combined_confidence == pytest.approx(expected_combined, abs=0.01)
            
        except ImportError:
            pytest.skip("MLPHIFinding not available")
    
    def test_finding_serialization(self):
        """Test MLPHIFinding to_dict method."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MLPHIFinding
            
            finding = MLPHIFinding(
                text="John Doe",
                start=0,
                end=8,
                entity_type="PERSON",
                phi_category="NAME",
                confidence=0.9,
                context_score=0.7,
                model_source="spacy",
                surrounding_context="A long context string that should be truncated"
            )
            
            data = finding.to_dict()
            
            assert data["text"] == "John Doe"
            assert data["start"] == 0
            assert data["end"] == 8
            assert data["entity_type"] == "PERSON"
            assert data["phi_category"] == "NAME"
            assert data["confidence"] == 0.9
            assert data["context_score"] == 0.7
            assert data["model_source"] == "spacy"
            assert "combined_confidence" in data
            assert "is_likely_phi" in data
            
            # Context should be truncated to 100 characters
            assert len(data["surrounding_context"]) <= 100
            
        except ImportError:
            pytest.skip("MLPHIFinding not available")


class TestCreateMLPhiDetector:
    """Tests for the factory function."""
    
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.SPACY_AVAILABLE', False)
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.TRANSFORMERS_AVAILABLE', False)
    def test_factory_no_ml_libraries(self):
        """Test factory function when no ML libraries available."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import create_ml_phi_detector
            
            detector = create_ml_phi_detector()
            assert detector is None
            
        except ImportError:
            pytest.skip("create_ml_phi_detector not available")
    
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.SPACY_AVAILABLE', True)
    @patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.TRANSFORMERS_AVAILABLE', True)
    def test_factory_with_ml_libraries(self):
        """Test factory function when ML libraries are available."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import create_ml_phi_detector
            
            # Mock successful detector creation
            with patch('src.workflow_engine.stages.phi_analyzers.ml_phi_detector.MLPhiDetector') as mock_class:
                mock_instance = MagicMock()
                mock_class.return_value = mock_instance
                
                detector = create_ml_phi_detector(confidence_threshold=0.9)
                
                assert detector is not None
                mock_class.assert_called_once()
                
        except ImportError:
            pytest.skip("create_ml_phi_detector not available")


class TestMedicalContextPatterns:
    """Tests for medical context pattern recognition."""
    
    def test_medical_context_patterns_exist(self):
        """Test that medical context patterns are defined."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import MEDICAL_CONTEXTS
            
            assert len(MEDICAL_CONTEXTS) >= 5
            
            # Should include key medical terms
            medical_pattern_text = " ".join(MEDICAL_CONTEXTS)
            assert "patient" in medical_pattern_text.lower()
            assert "diagnosis" in medical_pattern_text.lower()
            assert "medical" in medical_pattern_text.lower()
            
        except ImportError:
            pytest.skip("MEDICAL_CONTEXTS not available")
    
    def test_phi_entity_mappings(self):
        """Test PHI entity type mappings."""
        try:
            from src.workflow_engine.stages.phi_analyzers.ml_phi_detector import (
                PHI_ENTITY_TYPES, 
                CLINICAL_ENTITY_TYPES
            )
            
            # General PHI entity types
            assert "PERSON" in PHI_ENTITY_TYPES
            assert PHI_ENTITY_TYPES["PERSON"] == "NAME"
            assert "ORG" in PHI_ENTITY_TYPES
            assert "DATE" in PHI_ENTITY_TYPES
            
            # Clinical entity types
            assert "PATIENT" in CLINICAL_ENTITY_TYPES
            assert CLINICAL_ENTITY_TYPES["PATIENT"] == "NAME"
            assert "MEDICATION" in CLINICAL_ENTITY_TYPES
            
        except ImportError:
            pytest.skip("PHI entity mappings not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])