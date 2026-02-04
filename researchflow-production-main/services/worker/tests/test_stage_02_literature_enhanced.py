"""
Enhanced Unit Tests for Stage 02 Literature Discovery

Tests for the enhanced LiteratureScoutAgent with improved XML parsing,
Pydantic schemas, and PICO integration.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
import xml.etree.ElementTree as ET

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
from src.workflow_engine.stages.schemas.literature_schemas import (
    LiteratureCitation, LiteratureReview, LiteratureSearchQuery, 
    validate_literature_review, LiteratureSource
)
from src.workflow_engine.types import StageContext, StageResult


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_context():
    """Sample stage context for testing."""
    return StageContext(
        job_id="test-lit-001",
        config={
            "literature": {
                "keywords": ["diabetes", "metformin", "HbA1c"],
                "topic": "Metformin effectiveness in Type 2 diabetes",
                "max_results": 20,
                "study_types": ["rct", "systematic_review"]
            }
        },
        governance_mode="DEMO",
        metadata={"phi_scanned": True},
        artifact_path="/tmp/test_artifacts",
        log_path="/tmp/test_logs"
    )

@pytest.fixture
def sample_context_with_pico():
    """Sample context with Stage 1 PICO output."""
    return StageContext(
        job_id="test-lit-pico-001",
        config={
            "studyTitle": "PICO-based diabetes study"
        },
        governance_mode="DEMO",
        metadata={"phi_scanned": True},
        artifact_path="/tmp/test_artifacts",
        log_path="/tmp/test_logs",
        prior_stage_outputs={
            1: {
                "output_data": {
                    "pico_elements": {
                        "population": "adults with type 2 diabetes",
                        "intervention": "metformin therapy",
                        "comparator": "placebo or usual care",
                        "outcomes": ["HbA1c reduction", "glycemic control"]
                    },
                    "search_query": "type 2 diabetes AND metformin AND HbA1c",
                    "stage_1_complete": True,
                    "study_type": "randomized controlled trial"
                }
            }
        }
    )

@pytest.fixture
def sample_pubmed_xml():
    """Sample PubMed XML response."""
    return """<?xml version="1.0"?>
    <PubmedArticleSet>
        <PubmedArticle>
            <MedlineCitation>
                <PMID>12345678</PMID>
                <Article>
                    <Journal>
                        <Title>Diabetes Care</Title>
                    </Journal>
                    <ArticleTitle>Metformin Effects on Glycemic Control</ArticleTitle>
                    <Abstract>
                        <AbstractText>This study examines metformin's effects on HbA1c levels...</AbstractText>
                    </Abstract>
                    <AuthorList>
                        <Author>
                            <LastName>Smith</LastName>
                            <ForeName>John</ForeName>
                            <Initials>J</Initials>
                        </Author>
                        <Author>
                            <LastName>Johnson</LastName>
                            <ForeName>Mary</ForeName>
                            <Initials>M</Initials>
                        </Author>
                    </AuthorList>
                </Article>
                <PubDate>
                    <Year>2023</Year>
                </PubDate>
            </MedlineCitation>
            <PubmedData>
                <ArticleIdList>
                    <ArticleId IdType="doi">10.1234/diabetes.2023.001</ArticleId>
                </ArticleIdList>
            </PubmedData>
        </PubmedArticle>
    </PubmedArticleSet>"""

@pytest.fixture
def sample_papers_data():
    """Sample papers data for testing."""
    return [
        {
            "pmid": "12345678",
            "title": "Metformin Effects on Glycemic Control",
            "abstract": "This study examines metformin's effects on HbA1c levels in patients with type 2 diabetes...",
            "authors": ["Smith, John", "Johnson, Mary"],
            "journal": "Diabetes Care",
            "year": "2023",
            "doi": "10.1234/diabetes.2023.001",
            "source": "pubmed"
        },
        {
            "pmid": "87654321",
            "title": "Long-term Outcomes of Metformin Therapy",
            "abstract": "A comprehensive analysis of long-term metformin use...",
            "authors": ["Brown, Alice", "Davis, Robert"],
            "journal": "New England Journal of Medicine",
            "year": "2022",
            "doi": "10.5678/nejm.2022.diabetes",
            "source": "pubmed"
        }
    ]


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestLiteratureSchemas:
    """Tests for literature Pydantic schemas."""
    
    def test_literature_citation_validation(self):
        """Test literature citation schema validation."""
        citation_data = {
            "pmid": "12345678",
            "title": "Test Article",
            "authors": ["Smith, J", "Johnson, M"],
            "journal": "Test Journal",
            "year": "2023",
            "doi": "10.1234/test",
            "source": "pubmed"
        }
        
        citation = LiteratureCitation(**citation_data)
        
        assert citation.pmid == "12345678"
        assert citation.title == "Test Article"
        assert len(citation.authors) == 2
        assert citation.source == LiteratureSource.PUBMED
    
    def test_literature_review_validation(self):
        """Test literature review schema validation."""
        review_data = {
            "papers_found": 2,
            "key_themes": ["Treatment efficacy", "Safety profile"],
            "research_gaps": ["Long-term outcomes", "Pediatric populations"],
            "citations": [
                {
                    "pmid": "12345",
                    "title": "Test Paper 1",
                    "source": "pubmed"
                },
                {
                    "pmid": "67890",
                    "title": "Test Paper 2", 
                    "source": "pubmed"
                }
            ]
        }
        
        review = LiteratureReview(**review_data)
        
        assert review.papers_found == 2
        assert len(review.key_themes) == 2
        assert len(review.citations) == 2
    
    def test_validation_with_quality_metrics(self):
        """Test literature review validation with quality metrics."""
        review_data = {
            "papers_found": 15,
            "key_themes": ["Efficacy", "Safety", "Cost-effectiveness"],
            "research_gaps": ["Long-term studies needed"],
            "citations": [{"pmid": "123", "title": "Test", "source": "pubmed"}] * 15,
            "quality_metrics": {
                "total_papers_included": 15,
                "avg_citation_count": 45.2,
                "systematic_reviews_count": 3,
                "high_impact_papers": 8
            }
        }
        
        validation_result = validate_literature_review(review_data, "STAGING")
        
        assert validation_result.is_valid
        assert validation_result.quality_score > 5.0
        assert len(validation_result.recommendations) >= 0


# =============================================================================
# XML Parsing Tests
# =============================================================================

class TestXMLParsing:
    """Tests for enhanced XML parsing functionality."""
    
    def test_structured_xml_parsing(self, sample_pubmed_xml):
        """Test ElementTree XML parsing."""
        agent = LiteratureScoutAgent()
        papers = agent._parse_pubmed_xml_structured(sample_pubmed_xml)
        
        assert len(papers) == 1
        paper = papers[0]
        assert paper["pmid"] == "12345678"
        assert paper["title"] == "Metformin Effects on Glycemic Control"
        assert paper["journal"] == "Diabetes Care"
        assert paper["year"] == "2023"
        assert paper["doi"] == "10.1234/diabetes.2023.001"
        assert len(paper["authors"]) == 2
        assert "Smith, John" in paper["authors"]
    
    def test_xml_parsing_with_malformed_content(self):
        """Test XML parsing with malformed content."""
        agent = LiteratureScoutAgent()
        malformed_xml = "<incomplete><xml>content"
        
        # Should fallback to regex parsing without crashing
        papers = agent._parse_pubmed_xml_enhanced(malformed_xml, ["123"])
        
        assert isinstance(papers, list)
    
    def test_author_extraction(self):
        """Test author name extraction from XML."""
        agent = LiteratureScoutAgent()
        
        author_xml = ET.fromstring("""
            <Author>
                <LastName>Smith</LastName>
                <ForeName>John William</ForeName>
                <Initials>JW</Initials>
            </Author>
        """)
        
        author = agent._extract_author(author_xml)
        
        assert author == "Smith, John William"
    
    def test_clean_xml_text(self):
        """Test XML text cleaning."""
        agent = LiteratureScoutAgent()
        
        xml_element = ET.fromstring("""
            <AbstractText>
                This is <i>italic</i> and <b>bold</b> text.
                <br/>With line breaks.
            </AbstractText>
        """)
        
        cleaned = agent._clean_xml_text(xml_element)
        
        assert "italic" in cleaned
        assert "bold" in cleaned
        assert "<i>" not in cleaned
        assert "<b>" not in cleaned


# =============================================================================
# PICO Integration Tests
# =============================================================================

class TestPICOIntegration:
    """Tests for PICO framework integration."""
    
    def test_extract_search_config_with_pico(self, sample_context_with_pico):
        """Test search config extraction with PICO elements."""
        agent = LiteratureScoutAgent()
        search_config = agent._extract_search_config(sample_context_with_pico)
        
        assert search_config["stage1_complete"] is True
        assert search_config["pico_driven_search"] is True
        assert "type 2 diabetes AND metformin AND HbA1c" in search_config["pico_search_query"]
        assert search_config["research_topic"] is not None
    
    def test_build_pico_query(self, sample_context_with_pico):
        """Test building PubMed query from PICO elements."""
        agent = LiteratureScoutAgent()
        search_config = agent._extract_search_config(sample_context_with_pico)
        query = agent._build_pubmed_query(search_config)
        
        assert "type 2 diabetes" in query.lower()
        assert "metformin" in query.lower()
        assert "randomized controlled trial" in query.lower()
    
    def test_fallback_without_pico(self, sample_context):
        """Test fallback behavior when no PICO data available."""
        agent = LiteratureScoutAgent()
        search_config = agent._extract_search_config(sample_context)
        
        assert search_config["pico_driven_search"] is False
        assert search_config["stage1_complete"] is False
        assert len(search_config["keywords"]) > 0


# =============================================================================
# API Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestAPIIntegration:
    """Tests for external API integration."""
    
    async def test_pubmed_search_with_retry(self, sample_context):
        """Test PubMed search with retry logic."""
        agent = LiteratureScoutAgent()
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate timeout then success
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "esearchresult": {"idlist": ["123", "456"]}
            }
            mock_response.text = "<PubmedArticleSet></PubmedArticleSet>"
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            search_config = agent._extract_search_config(sample_context)
            papers = await agent._search_pubmed_direct(search_config)
            
            assert isinstance(papers, list)
    
    async def test_ai_router_integration(self, sample_context, sample_papers_data):
        """Test AI Router integration for structured summary."""
        agent = LiteratureScoutAgent()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "response": json.dumps({
                    "key_themes": ["Treatment efficacy", "Safety"],
                    "research_gaps": ["Long-term outcomes", "Pediatric use"],
                    "summary": "Metformin shows consistent efficacy"
                })
            }
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            search_config = agent._extract_search_config(sample_context)
            summary = await agent._generate_structured_summary(
                sample_papers_data, search_config, sample_context
            )
            
            assert summary["papers_found"] == len(sample_papers_data)
            assert len(summary["key_themes"]) > 0
            assert len(summary["research_gaps"]) > 0
            assert len(summary["citations"]) == len(sample_papers_data)
    
    async def test_ai_router_fallback(self, sample_context, sample_papers_data):
        """Test AI Router fallback behavior."""
        agent = LiteratureScoutAgent()
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate API failure
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
            
            search_config = agent._extract_search_config(sample_context)
            summary = await agent._generate_structured_summary(
                sample_papers_data, search_config, sample_context
            )
            
            # Should use fallback summary
            assert summary["papers_found"] == len(sample_papers_data)
            assert "Treatment efficacy" in summary["key_themes"]
            assert len(summary["citations"]) == len(sample_papers_data)


# =============================================================================
# Stage Execution Tests
# =============================================================================

@pytest.mark.asyncio
class TestStageExecution:
    """Tests for complete stage execution."""
    
    async def test_full_execution_demo_mode(self, sample_context):
        """Test full stage execution in DEMO mode."""
        agent = LiteratureScoutAgent()
        
        with patch.object(agent, '_search_pubmed_direct') as mock_search, \
             patch.object(agent, '_generate_structured_summary') as mock_summary, \
             patch.object(agent, '_save_literature_review_artifact') as mock_save, \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()):
            
            # Mock successful search
            mock_search.return_value = [
                {"pmid": "123", "title": "Test Paper", "source": "pubmed"}
            ]
            
            # Mock AI summary
            mock_summary.return_value = {
                "papers_found": 1,
                "key_themes": ["Efficacy"],
                "research_gaps": ["Safety"],
                "citations": [{"pmid": "123", "title": "Test Paper"}]
            }
            
            # Mock artifact saving
            mock_save.return_value = "/tmp/literature_review.json"
            
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert result.output["papers_found"] == 1
            assert len(result.artifacts) > 0
            assert len(result.errors) == 0
    
    async def test_execution_with_phi_scan_failure(self, sample_context):
        """Test execution failure due to PHI scan."""
        # Modify context for STAGING mode without PHI scan
        sample_context.governance_mode = "STAGING"
        sample_context.metadata = {"phi_scanned": False}
        
        agent = LiteratureScoutAgent()
        result = await agent.execute(sample_context)
        
        assert result.status == "failed"
        assert "PHI scan required" in " ".join(result.errors)
    
    async def test_execution_with_no_papers_found(self, sample_context):
        """Test execution when no papers are found."""
        agent = LiteratureScoutAgent()
        
        with patch.object(agent, '_search_pubmed_direct') as mock_search, \
             patch.object(agent, '_generate_structured_summary') as mock_summary, \
             patch.object(agent, '_save_literature_review_artifact') as mock_save:
            
            # Mock empty search results
            mock_search.return_value = []
            
            # Mock empty summary
            mock_summary.return_value = {
                "papers_found": 0,
                "key_themes": [],
                "research_gaps": [],
                "citations": []
            }
            
            mock_save.return_value = "/tmp/literature_review.json"
            
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"  # Should complete even with no results
            assert result.output["papers_found"] == 0
            assert len(result.warnings) > 0  # Should have warnings about low paper count


# =============================================================================
# Performance and Error Handling Tests
# =============================================================================

class TestPerformanceAndErrorHandling:
    """Tests for performance optimization and error handling."""
    
    def test_rate_limiting(self):
        """Test rate limiting implementation."""
        agent = LiteratureScoutAgent()
        
        # Reset class variable
        agent._last_api_call = None
        
        import asyncio
        async def test_delays():
            start_time = asyncio.get_event_loop().time()
            await agent._rate_limit_delay()
            first_call = asyncio.get_event_loop().time()
            
            await agent._rate_limit_delay()
            second_call = asyncio.get_event_loop().time()
            
            # Second call should be delayed
            delay = second_call - first_call
            assert delay >= 0.3  # Minimum delay for rate limiting
        
        asyncio.run(test_delays())
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test with invalid max_results
        invalid_config = {"max_results": -5}
        agent = LiteratureScoutAgent(invalid_config)
        
        # Should default to 50
        assert agent.max_results_per_source == 50
        
        # Test with invalid min_relevance
        invalid_config2 = {"min_relevance": 5.0}  # > 1.0
        agent2 = LiteratureScoutAgent(invalid_config2)
        
        # Should default to 0.5
        assert agent2.min_relevance_score == 0.5
    
    def test_audit_logging(self, sample_context):
        """Test audit logging functionality."""
        agent = LiteratureScoutAgent()
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.makedirs') as mock_makedirs:
            
            agent.audit_log(
                action="test_action",
                details={"test": "data"},
                context=sample_context
            )
            
            # Should create log directory
            mock_makedirs.assert_called_once()
            
            # Should write to audit file
            mock_file.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])