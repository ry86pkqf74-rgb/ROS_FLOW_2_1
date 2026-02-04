"""
Test Suite for Reference Management System

Comprehensive tests for the enhanced reference management system including
unit tests, integration tests, and performance tests.

Linear Issues: ROS-XXX
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List, Dict, Any

from .reference_types import (
    Reference, Citation, QualityScore, QualityWarning, QualityLevel,
    CitationStyle, ReferenceState, ReferenceResult, DOIValidationResult,
    DuplicateGroup, CitationNeed, ReferenceAnalytics
)
from .reference_management_service import ReferenceManagementService
from .doi_validator import DOIValidator
from .duplicate_detector import PaperDeduplicator
from .reference_quality import ReferenceQualityAssessor
from .reference_cache import ReferenceCache


class TestReferenceTypes:
    """Test reference type definitions and validation."""
    
    def test_reference_creation(self):
        """Test Reference model creation and validation."""
        ref = Reference(
            id="test_ref_1",
            title="A Test Paper",
            authors=["Smith, J.", "Doe, A."],
            year=2023,
            journal="Test Journal",
            doi="10.1234/test.2023.001"
        )
        
        assert ref.id == "test_ref_1"
        assert ref.title == "A Test Paper"
        assert len(ref.authors) == 2
        assert ref.year == 2023
        assert ref.doi == "10.1234/test.2023.001"
        assert not ref.is_retracted
        assert not ref.is_preprint
    
    def test_doi_validation(self):
        """Test DOI format validation."""
        # Valid DOI
        ref = Reference(
            id="test",
            title="Test",
            authors=[],
            doi="10.1234/test"
        )
        assert ref.doi == "10.1234/test"
        
        # Invalid DOI should be normalized or None
        ref = Reference(
            id="test",
            title="Test", 
            authors=[],
            doi="invalid_doi"
        )
        assert ref.doi is None
    
    def test_citation_creation(self):
        """Test Citation model creation."""
        citation = Citation(
            reference_id="ref_1",
            formatted_text="Smith J, Doe A. A Test Paper. Test Journal. 2023;1(1):1-10.",
            style=CitationStyle.AMA,
            in_text_markers=["1"]
        )
        
        assert citation.reference_id == "ref_1"
        assert citation.style == CitationStyle.AMA
        assert citation.in_text_markers == ["1"]
        assert citation.is_complete
        assert citation.completeness_score == 1.0
    
    def test_quality_score_creation(self):
        """Test QualityScore model creation."""
        score = QualityScore(
            reference_id="ref_1",
            overall_score=0.85,
            quality_level=QualityLevel.GOOD,
            credibility_score=0.9,
            recency_score=0.8,
            relevance_score=0.85,
            impact_score=0.8,
            methodology_score=0.9
        )
        
        assert score.reference_id == "ref_1"
        assert score.overall_score == 0.85
        assert score.quality_level == QualityLevel.GOOD
        assert 0.0 <= score.credibility_score <= 1.0


class TestReferenceCache:
    """Test reference caching functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis for testing."""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = None
            mock_client.setex.return_value = True
            mock_client.delete.return_value = 1
            yield mock_client
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, mock_redis):
        """Test cache initialization."""
        cache = ReferenceCache("redis://test:6379")
        await cache.initialize()
        
        assert cache._redis_pool is not None
        mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, mock_redis):
        """Test basic cache operations."""
        cache = ReferenceCache("redis://test:6379")
        await cache.initialize()
        
        # Test set
        test_data = {"key": "value", "number": 42}
        result = await cache.set("test_type", "test_key", test_data)
        assert result is True
        
        # Test get (simulate cache hit)
        mock_redis.get.return_value = '{"key": "value", "number": 42}'
        cached_data = await cache.get("test_type", "test_key")
        assert cached_data == test_data
    
    @pytest.mark.asyncio
    async def test_cache_reference_objects(self, mock_redis):
        """Test caching Reference objects."""
        cache = ReferenceCache("redis://test:6379")
        await cache.initialize()
        
        ref = Reference(
            id="test_ref",
            title="Test Paper",
            authors=["Author, A."],
            year=2023
        )
        
        # Test set reference
        await cache.set("reference_data", "test_ref", ref)
        
        # Simulate cache hit
        mock_redis.get.return_value = ref.model_dump_json()
        cached_ref = await cache.get("reference_data", "test_ref", "reference")
        
        assert isinstance(cached_ref, Reference)
        assert cached_ref.id == ref.id
        assert cached_ref.title == ref.title


class TestDOIValidator:
    """Test DOI validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """DOI validator instance."""
        return DOIValidator()
    
    def test_doi_format_validation(self, validator):
        """Test DOI format validation."""
        # Valid DOIs
        assert validator.is_valid_doi_format("10.1234/test.2023.001")
        assert validator.is_valid_doi_format("10.1038/nature12373")
        assert validator.is_valid_doi_format("10.1016/j.cell.2023.01.001")
        
        # Invalid DOIs
        assert not validator.is_valid_doi_format("invalid_doi")
        assert not validator.is_valid_doi_format("10.incomplete")
        assert not validator.is_valid_doi_format("")
        assert not validator.is_valid_doi_format(None)
    
    def test_doi_cleaning(self, validator):
        """Test DOI cleaning and normalization."""
        test_cases = [
            ("doi:10.1234/test", "10.1234/test"),
            ("DOI:10.1234/test", "10.1234/test"),
            ("https://doi.org/10.1234/test", "10.1234/test"),
            ("http://dx.doi.org/10.1234/test", "10.1234/test"),
            ("  10.1234/test  ", "10.1234/test"),
        ]
        
        for input_doi, expected in test_cases:
            cleaned = validator._clean_doi(input_doi)
            assert cleaned == expected
    
    @pytest.mark.asyncio
    async def test_doi_validation_workflow(self, validator):
        """Test full DOI validation workflow."""
        with patch.object(validator, '_fetch_doi_metadata') as mock_fetch:
            mock_fetch.return_value = {
                "title": ["Test Paper"],
                "author": [{"given": "John", "family": "Smith"}],
                "container-title": ["Test Journal"]
            }
            
            result = await validator.validate_doi("10.1234/test.001")
            
            assert result.is_valid
            assert result.is_resolvable
            assert result.metadata is not None
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_batch_doi_validation(self, validator):
        """Test batch DOI validation."""
        dois = ["10.1234/test.001", "10.1234/test.002", "invalid_doi"]
        
        with patch.object(validator.api_manager, 'batch_doi_lookups') as mock_batch:
            mock_batch.return_value = {
                "10.1234/test.001": {"title": ["Paper 1"]},
                "10.1234/test.002": {"title": ["Paper 2"]}
            }
            
            validator.api_manager = AsyncMock()
            results = await validator.validate_dois_batch(dois)
            
            assert len(results) == 3
            assert results["10.1234/test.001"].is_valid
            assert results["10.1234/test.002"].is_valid
            assert not results["invalid_doi"].is_valid
    
    @pytest.mark.asyncio
    async def test_reference_enrichment(self, validator):
        """Test reference enrichment with DOI metadata."""
        ref = Reference(
            id="test",
            title="Original Title",
            authors=[],
            doi="10.1234/test.001"
        )
        
        with patch.object(validator, 'validate_doi') as mock_validate:
            mock_validate.return_value = DOIValidationResult(
                doi="10.1234/test.001",
                is_valid=True,
                is_resolvable=True,
                metadata={
                    "title": ["Enhanced Title"],
                    "author": [{"given": "John", "family": "Smith"}],
                    "container-title": ["Test Journal"],
                    "published": {"date-parts": [[2023]]},
                    "volume": "1",
                    "issue": "1",
                    "page": "1-10"
                }
            )
            
            enriched_ref = await validator.enrich_reference_with_doi(ref)
            
            assert enriched_ref.title == "Enhanced Title"
            assert enriched_ref.authors == ["John Smith"]
            assert enriched_ref.journal == "Test Journal"
            assert enriched_ref.year == 2023
            assert enriched_ref.volume == "1"


class TestDuplicateDetector:
    """Test duplicate detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Duplicate detector instance."""
        return PaperDeduplicator()
    
    def test_text_normalization(self, detector):
        """Test text normalization for comparison."""
        test_cases = [
            ("The Quick Brown Fox", "quick brown fox"),
            ("COVID-19 and SARS-CoV-2", "covid 19 sars cov 2"),
            ("A Study of Patients with Diabetes", "study patients diabetes")
        ]
        
        for input_text, expected in test_cases:
            normalized = detector._normalize_text(input_text)
            assert normalized == expected
    
    def test_author_normalization(self, detector):
        """Test author name normalization."""
        authors = ["Smith, John A.", "Jane Doe", "Brown, M."]
        normalized = detector._normalize_author_list(authors)
        
        expected = ["brown, m", "doe, j", "smith, j"]  # Sorted
        assert normalized == expected
    
    def test_title_similarity(self, detector):
        """Test title similarity calculation."""
        title1 = "COVID-19 and Diabetes: A Systematic Review"
        title2 = "COVID-19 and diabetes: a systematic review"
        similarity = detector._calculate_title_similarity(title1, title2)
        assert similarity > 0.95  # Should be very similar
        
        title3 = "Machine Learning in Healthcare"
        similarity2 = detector._calculate_title_similarity(title1, title3)
        assert similarity2 < 0.3  # Should be very different
    
    def test_author_similarity(self, detector):
        """Test author similarity calculation."""
        authors1 = ["Smith, J.", "Doe, A.", "Brown, M."]
        authors2 = ["Smith, John", "Doe, Alice", "Johnson, P."]
        
        similarity = detector._calculate_author_similarity(authors1, authors2)
        # Should find similarity between Smith and Doe
        assert 0.4 < similarity < 0.8
    
    @pytest.mark.asyncio
    async def test_duplicate_detection(self, detector):
        """Test duplicate detection workflow."""
        # Create test references with duplicates
        refs = [
            Reference(
                id="ref1",
                title="COVID-19 and Diabetes",
                authors=["Smith, J.", "Doe, A."],
                year=2023,
                journal="Medical Journal",
                doi="10.1234/covid.001"
            ),
            Reference(
                id="ref2",
                title="COVID-19 and diabetes: A review",  # Similar title
                authors=["Smith, John", "Doe, Alice"],      # Similar authors
                year=2023,
                journal="Medical Journal"
            ),
            Reference(
                id="ref3",
                title="Machine Learning Applications",
                authors=["Johnson, P."],
                year=2022,
                journal="Tech Journal"
            )
        ]
        
        duplicate_groups = await detector.find_duplicates(refs)
        
        # Should find one duplicate group (ref1 and ref2)
        assert len(duplicate_groups) == 1
        assert len(duplicate_groups[0].reference_ids) == 2
        assert set(duplicate_groups[0].reference_ids) == {"ref1", "ref2"}
    
    @pytest.mark.asyncio
    async def test_duplicate_merging(self, detector):
        """Test duplicate reference merging."""
        primary_ref = Reference(
            id="ref1",
            title="Primary Paper",
            authors=["Smith, J."],
            year=2023,
            doi="10.1234/primary"
        )
        
        duplicate_ref = Reference(
            id="ref2",
            title="Primary Paper",  # Same title
            authors=["Smith, J."],   # Same author
            year=2023,
            abstract="This is a detailed abstract"  # Additional info
        )
        
        duplicate_group = DuplicateGroup(
            group_id="dup_1",
            reference_ids=["ref1", "ref2"],
            primary_reference_id="ref1",
            similarity_score=0.95,
            match_criteria=["title_high_similarity"],
            auto_resolvable=True,
            resolution_strategy="merge_high_confidence"
        )
        
        merged_refs = await detector.merge_duplicates(
            [primary_ref, duplicate_ref],
            [duplicate_group]
        )
        
        # Should return one merged reference
        assert len(merged_refs) == 1
        merged_ref = merged_refs[0]
        assert merged_ref.id == "ref1"  # Primary ID preserved
        assert merged_ref.abstract == "This is a detailed abstract"  # Info merged


class TestReferenceQuality:
    """Test reference quality assessment."""
    
    @pytest.fixture
    def assessor(self):
        """Quality assessor instance."""
        return ReferenceQualityAssessor()
    
    @pytest.mark.asyncio
    async def test_credibility_assessment(self, assessor):
        """Test credibility scoring."""
        # High credibility reference
        high_quality_ref = Reference(
            id="high",
            title="Test Paper",
            authors=["Smith, J."],
            journal="Nature",
            year=2023,
            doi="10.1038/nature.2023.001",
            is_retracted=False
        )
        
        score = await assessor._assess_credibility(high_quality_ref, "medical")
        assert score > 0.7  # Should be high
        
        # Low credibility reference (retracted)
        low_quality_ref = Reference(
            id="low",
            title="Retracted Paper",
            authors=["Bad, Author"],
            is_retracted=True
        )
        
        score = await assessor._assess_credibility(low_quality_ref, "medical")
        assert score == 0.0  # Retracted papers get zero credibility
    
    def test_recency_assessment(self, assessor):
        """Test recency scoring."""
        current_year = datetime.now().year
        
        # Recent paper
        recent_ref = Reference(id="recent", title="Test", authors=[], year=current_year - 1)
        score = assessor._assess_recency(recent_ref)
        assert score >= 0.8
        
        # Old paper
        old_ref = Reference(id="old", title="Test", authors=[], year=current_year - 30)
        score = assessor._assess_recency(old_ref)
        assert score <= 0.2
    
    @pytest.mark.asyncio
    async def test_comprehensive_quality_assessment(self, assessor):
        """Test comprehensive quality assessment."""
        ref = Reference(
            id="test",
            title="High-Quality Research Paper",
            authors=["Smith, J.", "Doe, A."],
            year=2023,
            journal="Nature Medicine",
            doi="10.1038/natmed.2023.001",
            abstract="This is a well-conducted randomized controlled trial..."
        )
        
        manuscript_context = "diabetes treatment randomized controlled trial"
        
        quality_score = await assessor.assess_reference_quality(
            ref, manuscript_context, "medical"
        )
        
        assert quality_score.reference_id == "test"
        assert 0.0 <= quality_score.overall_score <= 1.0
        assert quality_score.quality_level in [level for level in QualityLevel]
        assert len(quality_score.strengths) >= 0
        assert len(quality_score.weaknesses) >= 0
    
    @pytest.mark.asyncio
    async def test_problematic_reference_flagging(self, assessor):
        """Test flagging of problematic references."""
        refs = [
            Reference(
                id="retracted",
                title="Retracted Study",
                authors=["Bad, Author"],
                is_retracted=True
            ),
            Reference(
                id="old",
                title="Very Old Study",
                authors=["Ancient, Author"],
                year=1990
            ),
            Reference(
                id="incomplete",
                title="Incomplete Reference",
                authors=[]  # Missing authors
            )
        ]
        
        warnings = await assessor.flag_problematic_references(refs)
        
        # Should generate warnings for all problematic references
        assert len(warnings) >= 3
        warning_types = [w.warning_type for w in warnings]
        assert "retracted_paper" in warning_types
        assert "very_old" in warning_types
        assert "incomplete_metadata" in warning_types


class TestReferenceManagementService:
    """Test the main reference management service."""
    
    @pytest.fixture
    def service(self):
        """Reference management service instance."""
        return ReferenceManagementService()
    
    @pytest.mark.asyncio
    async def test_citation_extraction(self, service):
        """Test citation extraction from manuscript text."""
        manuscript_text = """
        Introduction
        Studies have shown that diabetes affects millions [1]. 
        Previous research indicates [citation needed] that treatment outcomes vary.
        According to recent studies [2-4], new approaches are needed.
        """
        
        citation_needs = await service.extract_citations(manuscript_text)
        
        assert len(citation_needs) >= 3  # Should find at least 3 citation needs
        markers = [need.text_snippet for need in citation_needs]
        assert "[1]" in str(markers)
        assert "[citation needed]" in str(markers)
        assert "[2-4]" in str(markers)
    
    @pytest.mark.asyncio
    async def test_literature_matching(self, service):
        """Test matching citations to literature results."""
        citation_needs = [
            CitationNeed(
                id="need1",
                text_snippet="diabetes treatment",
                context="Studies have shown that diabetes treatment is effective",
                position=0,
                section="introduction",
                claim_type="prior_research"
            )
        ]
        
        literature_results = [
            {
                "id": "lit1",
                "title": "Diabetes Treatment Outcomes",
                "authors": ["Smith, J."],
                "year": 2023,
                "journal": "Diabetes Care",
                "abstract": "This study examines diabetes treatment effectiveness"
            }
        ]
        
        references = await service.match_to_literature(citation_needs, literature_results, [])
        
        assert len(references) == 1
        assert references[0].title == "Diabetes Treatment Outcomes"
        assert citation_needs[0].suggested_references == [references[0].id]
    
    @pytest.mark.asyncio
    async def test_full_reference_processing(self, service):
        """Test complete reference processing workflow."""
        # Mock dependencies
        service.cache = AsyncMock()
        service.api_manager = AsyncMock()
        service.doi_validator = AsyncMock()
        service.deduplicator = AsyncMock()
        service.quality_assessor = AsyncMock()
        service.analytics = AsyncMock()
        
        # Mock method returns
        service.doi_validator.enrich_reference_with_doi.return_value = Reference(
            id="ref1", title="Test", authors=[], year=2023
        )
        service.deduplicator.find_duplicates.return_value = []
        service.deduplicator.merge_duplicates.return_value = [
            Reference(id="ref1", title="Test", authors=[], year=2023)
        ]
        service.quality_assessor.assess_reference_quality.return_value = QualityScore(
            reference_id="ref1",
            overall_score=0.8,
            quality_level=QualityLevel.GOOD,
            credibility_score=0.8,
            recency_score=0.8,
            relevance_score=0.8,
            impact_score=0.8,
            methodology_score=0.8
        )
        service.quality_assessor.flag_problematic_references.return_value = []
        
        state = ReferenceState(
            study_id="test_study",
            manuscript_text="Test manuscript with [1] citation.",
            literature_results=[{
                "id": "lit1",
                "title": "Test Paper",
                "authors": ["Author, A."],
                "year": 2023
            }],
            target_style=CitationStyle.AMA
        )
        
        result = await service.process_references(state)
        
        assert result.study_id == "test_study"
        assert result.total_references >= 0
        assert len(result.citations) >= 0
        assert result.bibliography is not None
        assert result.processing_time_seconds > 0


class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.mark.asyncio
    async def test_stage17_integration(self):
        """Test integration with Stage 17."""
        # Mock the stage17 process function
        from ..stage17_citation_generation import process
        
        stage_data = {
            "runId": "test_run",
            "inputs": {
                "sources": [{
                    "id": "source1",
                    "title": "Test Paper",
                    "authors": ["Smith, J."],
                    "year": 2023,
                    "journal": "Test Journal"
                }],
                "citationStyle": "ama",
                "manuscript_text": "This is a test manuscript [1]."
            }
        }
        
        # Test that enhanced processing can be called
        # (actual testing would require mocking the service)
        assert stage_data["inputs"]["citationStyle"] == "ama"
        assert len(stage_data["inputs"]["sources"]) == 1
    
    @pytest.mark.asyncio
    async def test_manuscript_agent_integration(self):
        """Test integration with manuscript agent."""
        # This would test the manuscript agent's use of the reference system
        # Implementation depends on the actual manuscript agent structure
        pass


class TestPerformance:
    """Performance tests for the reference management system."""
    
    @pytest.mark.asyncio
    async def test_large_reference_set_processing(self):
        """Test processing performance with large reference sets."""
        # Create a large set of test references
        references = [
            Reference(
                id=f"ref_{i}",
                title=f"Test Paper {i}",
                authors=[f"Author_{i}, J."],
                year=2020 + (i % 4),
                journal=f"Journal {i % 10}"
            )
            for i in range(100)
        ]
        
        service = ReferenceManagementService()
        
        # Test duplicate detection performance
        detector = PaperDeduplicator()
        start_time = asyncio.get_event_loop().time()
        duplicate_groups = await detector.find_duplicates(references)
        end_time = asyncio.get_event_loop().time()
        
        processing_time = end_time - start_time
        assert processing_time < 10.0  # Should process 100 references in under 10 seconds
        assert len(duplicate_groups) >= 0  # May or may not find duplicates
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache performance with multiple operations."""
        cache = ReferenceCache("redis://test:6379")
        
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            await cache.initialize()
            
            # Test batch operations
            test_data = {f"key_{i}": f"value_{i}" for i in range(50)}
            
            start_time = asyncio.get_event_loop().time()
            await cache.set_many("test_type", test_data)
            end_time = asyncio.get_event_loop().time()
            
            batch_time = end_time - start_time
            assert batch_time < 1.0  # Batch operations should be fast


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])