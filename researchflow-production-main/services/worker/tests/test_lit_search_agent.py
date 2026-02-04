"""
Unit Tests for LitSearchAgent

Comprehensive tests for literature search functionality including:
- PICO framework extraction
- Query building
- Citation formatting
- Paper ranking
- API integration

Linear Issues: ROS-XXX
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.analysis.search_strategies import (
    PICOFramework,
    SearchQueryBuilder,
    MeSHTermExpander,
    DatabaseType,
    PaperDeduplicator,
)
from agents.analysis.citation_formatters import (
    AuthorNameParser,
    CitationFormatterFactory,
    AMAFormatter,
)
from agents.analysis.lit_search_agent import (
    LitSearchAgent,
    StudyContext,
    Paper,
    RankedPaper,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_study_context():
    """Sample study context for testing."""
    return StudyContext(
        title="Effect of Metformin on HbA1c in Type 2 Diabetes",
        keywords=["metformin", "type 2 diabetes", "HbA1c", "glycemic control"],
        research_question="Does metformin reduce HbA1c levels in adults with Type 2 diabetes?",
        study_type="RCT",
        population="adults with Type 2 diabetes",
        intervention="metformin",
        outcome="HbA1c reduction",
    )


@pytest.fixture
def sample_papers():
    """Sample papers for testing."""
    return [
        Paper(
            title="Metformin in Type 2 Diabetes",
            authors=["Smith J", "Jones A"],
            abstract="Study of metformin effects...",
            doi="10.1234/example1",
            year=2023,
            source="pubmed",
            journal="Diabetes Care",
        ),
        Paper(
            title="Glycemic Control with Metformin",
            authors=["Johnson B", "Williams C", "Brown D"],
            abstract="Analysis of HbA1c outcomes...",
            doi="10.1234/example2",
            year=2022,
            source="semantic_scholar",
            journal="JAMA",
        ),
    ]


# =============================================================================
# PICO Framework Tests
# =============================================================================

class TestPICOFramework:
    """Tests for PICO framework functionality."""
    
    def test_pico_creation(self):
        """Test creating a PICO framework."""
        pico = PICOFramework(
            population=["adults", "type 2 diabetes"],
            intervention=["metformin"],
            outcome=["HbA1c reduction"],
        )
        
        assert len(pico.population) == 2
        assert "metformin" in pico.intervention
        assert len(pico.outcome) == 1
    
    def test_pico_to_boolean_query(self):
        """Test converting PICO to boolean query."""
        pico = PICOFramework(
            population=["adults", "diabetes"],
            intervention=["metformin"],
        )
        
        query = pico.to_boolean_query()
        
        assert "adults" in query
        assert "diabetes" in query
        assert "metformin" in query
        assert " OR " in query
        assert " AND " in query
    
    def test_pico_from_research_question(self):
        """Test extracting PICO from research question."""
        question = "Does metformin reduce HbA1c in adults with Type 2 diabetes?"
        pico = PICOFramework.from_research_question(question)
        
        # Should extract some components (heuristic-based)
        assert isinstance(pico, PICOFramework)
        assert isinstance(pico.population, list)
        assert isinstance(pico.intervention, list)


# =============================================================================
# Query Builder Tests
# =============================================================================

class TestSearchQueryBuilder:
    """Tests for search query builder."""
    
    def test_basic_query_building(self):
        """Test building a basic query."""
        builder = SearchQueryBuilder(database=DatabaseType.PUBMED)
        builder.add_term("diabetes").add_term("metformin")
        
        query = builder.build()
        
        assert "diabetes" in query.query_string
        assert "metformin" in query.query_string
        assert query.database == DatabaseType.PUBMED
    
    def test_query_with_terms_group(self):
        """Test adding multiple terms with OR."""
        builder = SearchQueryBuilder()
        builder.add_terms(["diabetes", "hyperglycemia"], operator="OR")
        
        query = builder.build()
        
        assert "diabetes" in query.query_string
        assert "hyperglycemia" in query.query_string
    
    def test_query_with_date_filter(self):
        """Test adding date range filter."""
        builder = SearchQueryBuilder()
        builder.add_term("diabetes")
        builder.add_date_filter(year_from=2020, year_to=2024)
        
        query = builder.build()
        
        assert query.filters["year_from"] == 2020
        assert query.filters["year_to"] == 2024
    
    def test_query_from_pico(self):
        """Test building query from PICO framework."""
        pico = PICOFramework(
            population=["adults"],
            intervention=["metformin"],
        )
        
        builder = SearchQueryBuilder.from_pico(pico)
        query = builder.build()
        
        assert len(query.query_string) > 0


# =============================================================================
# MeSH Term Expansion Tests
# =============================================================================

class TestMeSHTermExpander:
    """Tests for MeSH term expansion."""
    
    def test_expand_single_term(self):
        """Test expanding a single term."""
        expander = MeSHTermExpander()
        expanded = expander.expand_term("diabetes")
        
        assert "diabetes" in [t.lower() for t in expanded]
        assert len(expanded) > 1  # Should include MeSH terms
    
    def test_expand_unknown_term(self):
        """Test expanding a term not in mappings."""
        expander = MeSHTermExpander()
        expanded = expander.expand_term("unknownterm")
        
        # Should return original term
        assert len(expanded) == 1
        assert expanded[0] == "unknownterm"
    
    def test_caching(self):
        """Test that expansion results are cached."""
        expander = MeSHTermExpander()
        
        result1 = expander.expand_term("diabetes")
        result2 = expander.expand_term("diabetes")
        
        # Should be the same object (cached)
        assert result1 is result2


# =============================================================================
# Citation Formatter Tests
# =============================================================================

class TestAuthorNameParser:
    """Tests for author name parsing."""
    
    def test_parse_first_last(self):
        """Test parsing 'First Last' format."""
        parsed = AuthorNameParser.parse_full_name("John Smith")
        
        assert parsed["first"] == "John"
        assert parsed["last"] == "Smith"
        assert parsed["middle"] == ""
    
    def test_parse_first_middle_last(self):
        """Test parsing 'First Middle Last' format."""
        parsed = AuthorNameParser.parse_full_name("John William Smith")
        
        assert parsed["first"] == "John"
        assert parsed["middle"] == "William"
        assert parsed["last"] == "Smith"
    
    def test_parse_last_first(self):
        """Test parsing 'Last, First' format."""
        parsed = AuthorNameParser.parse_full_name("Smith, John")
        
        assert parsed["first"] == "John"
        assert parsed["last"] == "Smith"
    
    def test_format_ama(self):
        """Test formatting for AMA style."""
        formatted = AuthorNameParser.format_ama("John William Smith")
        
        assert "Smith" in formatted
        assert "J" in formatted
        assert "W" in formatted


class TestAMAFormatter:
    """Tests for AMA citation formatter."""
    
    def test_format_journal_article(self):
        """Test formatting a journal article."""
        formatter = AMAFormatter()
        
        citation = formatter.format_journal_article(
            authors=["Smith J", "Jones A"],
            title="Test Article",
            journal="Test Journal",
            year=2023,
            volume="10",
            issue="2",
            pages="123-456",
            doi="10.1234/test",
        )
        
        assert "Smith" in citation
        assert "Test Article" in citation
        assert "Test Journal" in citation
        assert "2023" in citation
        assert "10(2)" in citation
        assert "doi:10.1234/test" in citation
    
    def test_format_with_et_al(self):
        """Test formatting with et al for many authors."""
        formatter = AMAFormatter()
        
        authors = [f"Author{i}" for i in range(10)]
        citation = formatter.format_journal_article(
            authors=authors,
            title="Many Authors",
            journal="Journal",
            year=2023,
        )
        
        assert "et al" in citation


class TestCitationFormatterFactory:
    """Tests for citation formatter factory."""
    
    def test_get_ama_formatter(self):
        """Test getting AMA formatter."""
        formatter = CitationFormatterFactory.get_formatter("AMA")
        
        assert isinstance(formatter, AMAFormatter)
        assert formatter.style_name == "AMA"
    
    def test_unsupported_style(self):
        """Test error for unsupported style."""
        with pytest.raises(ValueError):
            CitationFormatterFactory.get_formatter("UNSUPPORTED")
    
    def test_list_supported_styles(self):
        """Test listing supported styles."""
        styles = CitationFormatterFactory.list_supported_styles()
        
        assert "AMA" in styles
        assert len(styles) >= 1


# =============================================================================
# Paper Deduplication Tests
# =============================================================================

class TestPaperDeduplicator:
    """Tests for paper deduplication."""
    
    def test_deduplicate_by_doi(self):
        """Test deduplication using DOI."""
        papers = [
            {"title": "Paper 1", "doi": "10.1234/test", "authors": ["Smith"]},
            {"title": "Paper 1 Duplicate", "doi": "10.1234/test", "authors": ["Smith"]},
            {"title": "Paper 2", "doi": "10.5678/other", "authors": ["Jones"]},
        ]
        
        unique = PaperDeduplicator.deduplicate(papers)
        
        assert len(unique) == 2
        assert any(p["doi"] == "10.1234/test" for p in unique)
        assert any(p["doi"] == "10.5678/other" for p in unique)
    
    def test_deduplicate_by_title(self):
        """Test deduplication using title when no DOI."""
        papers = [
            {"title": "Test Paper", "authors": ["Smith"], "year": 2023},
            {"title": "Test Paper", "authors": ["Smith"], "year": 2023},
        ]
        
        unique = PaperDeduplicator.deduplicate(papers)
        
        assert len(unique) == 1


# =============================================================================
# LitSearchAgent Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestLitSearchAgent:
    """Tests for LitSearchAgent."""
    
    async def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = LitSearchAgent()
        
        assert agent.config.name == "LitSearchAgent"
        assert 6 in agent.config.stages
        assert agent.config.phi_safe is True
    
    @patch('agents.analysis.lit_search_agent.BaseAgent.run')
    async def test_execute_search(self, mock_run, sample_study_context):
        """Test executing a search."""
        # Mock agent run result
        mock_run.return_value = MagicMock(
            success=True,
            result={
                "ranked_papers": [],
                "total_found": 0,
                "queries_executed": ["test query"],
                "databases_used": ["pubmed"],
            },
        )
        
        agent = LitSearchAgent()
        result = await agent.execute(
            study_context=sample_study_context,
            max_results=10,
        )
        
        assert isinstance(result, LitSearchResult)
        assert result.total_found >= 0
        assert len(result.search_queries_used) > 0
    
    async def test_rank_relevance(self, sample_study_context, sample_papers):
        """Test ranking papers by relevance."""
        agent = LitSearchAgent()
        
        # Mock LLM response
        with patch.object(agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MagicMock(
                content='[{"index": 0, "score": 0.95, "reason": "Highly relevant"}]'
            )
            
            ranked = await agent.rank_relevance(
                papers=sample_papers,
                study_context=sample_study_context,
            )
            
            assert len(ranked) > 0
            assert all(isinstance(p, RankedPaper) for p in ranked)
    
    async def test_extract_citations(self, sample_papers):
        """Test citation extraction."""
        agent = LitSearchAgent()
        citations = await agent.extract_citations(papers=sample_papers)
        
        assert len(citations) == len(sample_papers)
        assert all(c.style == "AMA" for c in citations)
        assert all(len(c.formatted_citation) > 0 for c in citations)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
