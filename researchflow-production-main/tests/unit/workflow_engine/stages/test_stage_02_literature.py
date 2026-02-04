"""
Unit tests for Stage 2: LiteratureScoutAgent

Tests the LiteratureScoutAgent implementation:
- Search configuration extraction
- PubMed and Semantic Scholar search (bridge and fallback)
- Merge and deduplication
- Relevance ranking
- Key paper identification
- DEMO mode handling
- Artifact generation
"""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create a LiteratureScoutAgent instance."""
    return LiteratureScoutAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext for testing."""
    return StageContext(
        job_id="test-job",
        config={
            "studyTitle": "Effects of AI on Healthcare",
            "literature": {
                "keywords": ["artificial intelligence", "healthcare", "clinical decision"],
                "max_results": 25,
            }
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
        previous_results={
            1: MagicMock(output={"detected_study_type": "observational"})
        },
    )


@pytest.fixture
def mock_pubmed_response():
    """Mock PubMed API response."""
    return {
        "papers": [
            {
                "title": "AI in Healthcare",
                "doi": "10.1234/test",
                "citationCount": 50,
                "year": 2023,
                "abstract": "This study investigates AI applications in healthcare",
                "authors": [{"name": "Smith, J."}],
                "publicationType": "Research Article",
            },
            {
                "title": "Clinical ML",
                "doi": "10.5678/test2",
                "citationCount": 100,
                "year": 2024,
                "abstract": "Machine learning for clinical decision support",
                "authors": [{"name": "Jones, A."}],
                "publicationType": "Systematic Review",
            },
        ]
    }


@pytest.fixture
def mock_semantic_scholar_response():
    """Mock Semantic Scholar API response."""
    return {
        "papers": [
            {
                "title": "AI in Healthcare",
                "doi": "10.1234/test",  # Duplicate with PubMed
                "citationCount": 50,
                "year": 2023,
                "abstract": "This study investigates AI applications in healthcare",
            },
            {
                "title": "Deep Learning Medicine",
                "doi": "10.9999/test3",
                "citationCount": 200,
                "year": 2024,
                "abstract": "Deep learning applications in medicine",
            },
        ]
    }


class TestLiteratureScoutAgent:
    """Tests for LiteratureScoutAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 2
        assert agent.stage_name == "Literature Discovery"
        assert agent.max_results_per_source == 50

    def test_get_tools(self, agent):
        """get_tools should return a list of tools."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        # Tools may be empty if LangChain not available, that's OK

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context, mock_pubmed_response, mock_semantic_scholar_response):
        """Execute should succeed with mock service responses."""
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            # Mock service calls
            async def mock_call(service_name, method_name, params):
                if service_name == "pubmed":
                    return mock_pubmed_response
                elif service_name == "semantic-scholar":
                    return mock_semantic_scholar_response
                return {}
            
            mock_service.side_effect = mock_call
            
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert result.output.get("total_unique_papers") > 0
            assert "ranked_papers" in result.output
            assert "key_papers" in result.output
            assert "literature_summary" in result.output
            assert len(result.artifacts) == 2  # papers.json and summary.json

    @pytest.mark.asyncio
    async def test_demo_mode_no_keywords(self, agent, tmp_path):
        """DEMO mode should handle missing keywords gracefully."""
        context = StageContext(
            job_id="test-job",
            config={},  # No config
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = {"papers": []}
            
            result = await agent.execute(context)
            
            # Should succeed with defaults in DEMO mode
            assert result.status == "completed"
            assert len(result.warnings) > 0  # Should warn about using defaults

    @pytest.mark.asyncio
    async def test_live_mode_no_keywords_fails(self, agent, tmp_path):
        """LIVE mode should fail if no keywords provided."""
        context = StageContext(
            job_id="test-job",
            config={},  # No config
            artifact_path=str(tmp_path),
            governance_mode="LIVE",
        )
        
        result = await agent.execute(context)
        
        assert result.status == "failed"
        assert any("No search keywords" in err for err in result.errors)


class TestMergeAndDeduplicate:
    """Tests for _merge_and_deduplicate method."""

    def test_merge_and_deduplicate(self, agent):
        """Should merge results and remove duplicates."""
        pubmed = {
            "papers": [
                {"title": "Paper A", "doi": "10.1/a"},
                {"title": "Paper B", "doi": "10.1/b"},
            ]
        }
        semantic = {
            "papers": [
                {"title": "Paper A", "doi": "10.1/a"},  # Duplicate
                {"title": "Paper C", "doi": "10.1/c"},
            ]
        }
        
        merged = agent._merge_and_deduplicate(pubmed, semantic)
        
        assert len(merged) == 3  # A, B, C (no duplicates)
        assert all(p.get("source") in ["pubmed", "semantic_scholar"] for p in merged)

    def test_deduplicate_by_title(self, agent):
        """Should deduplicate by title if DOI missing."""
        pubmed = {
            "papers": [
                {"title": "Same Title Paper", "doi": None},
            ]
        }
        semantic = {
            "papers": [
                {"title": "Same Title Paper", "doi": None},  # Should be deduplicated
            ]
        }
        
        merged = agent._merge_and_deduplicate(pubmed, semantic)
        assert len(merged) == 1


class TestRankByRelevance:
    """Tests for _rank_by_relevance method."""

    def test_rank_by_relevance(self, agent):
        """Should rank papers by relevance score."""
        papers = [
            {"title": "Low relevance", "citationCount": 5, "year": 2020},
            {"title": "AI healthcare study", "citationCount": 200, "year": 2024},
        ]
        search_config = {"keywords": ["AI", "healthcare"]}
        
        ranked = agent._rank_by_relevance(papers, search_config)
        
        assert ranked[0]["title"] == "AI healthcare study"  # Should be first
        assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]

    def test_keyword_matching_boost(self, agent):
        """Keywords in title should boost score more than in abstract."""
        papers = [
            {"title": "AI healthcare", "abstract": "other text", "citationCount": 10},
            {"title": "other title", "abstract": "AI healthcare", "citationCount": 10},
        ]
        search_config = {"keywords": ["AI", "healthcare"]}
        
        ranked = agent._rank_by_relevance(papers, search_config)
        
        assert ranked[0]["title"] == "AI healthcare"  # Title match should rank higher

    def test_citation_boost(self, agent):
        """Higher citations should boost score."""
        papers = [
            {"title": "Paper A", "citationCount": 10},
            {"title": "Paper B", "citationCount": 150},
        ]
        search_config = {"keywords": []}
        
        ranked = agent._rank_by_relevance(papers, search_config)
        
        assert ranked[0]["citationCount"] == 150

    def test_recency_boost(self, agent):
        """Recent papers should get recency boost."""
        current_year = datetime.now().year
        papers = [
            {"title": "Old paper", "year": current_year - 10, "citationCount": 50},
            {"title": "Recent paper", "year": current_year - 1, "citationCount": 50},
        ]
        search_config = {"keywords": []}
        
        ranked = agent._rank_by_relevance(papers, search_config)
        
        assert ranked[0]["year"] == current_year - 1


class TestIdentifyKeyPapers:
    """Tests for _identify_key_papers method."""

    def test_identify_key_papers(self, agent):
        """Should identify key papers correctly."""
        papers = [
            {"title": "Regular paper", "citationCount": 10, "relevance_score": 2.0},
            {"title": "Highly cited", "citationCount": 150, "relevance_score": 3.0},
            {
                "title": "Systematic Review",
                "publicationType": "Systematic Review",
                "citationCount": 50,
                "relevance_score": 4.0
            },
        ]
        
        key_papers = agent._identify_key_papers(papers)
        
        assert len(key_papers) == 2  # Highly cited + Systematic Review
        assert any("Highly cited" in p["title"] for p in key_papers)
        assert any("Systematic Review" in p["title"] for p in key_papers)

    def test_key_papers_limit(self, agent):
        """Should limit to top 10 key papers."""
        papers = [
            {"title": f"Paper {i}", "citationCount": 150 + i, "relevance_score": 5.0}
            for i in range(15)
        ]
        
        key_papers = agent._identify_key_papers(papers)
        
        assert len(key_papers) <= 10


class TestExtractKeywords:
    """Tests for _extract_keywords method."""

    def test_extract_keywords_from_title(self, agent):
        """Should extract keywords from study title."""
        config = {"studyTitle": "The Effects of Machine Learning on Clinical Diagnosis"}
        keywords = agent._extract_keywords(config)
        
        assert len(keywords) > 0
        # Should contain meaningful words (not stop words)
        assert any("machine" in kw.lower() or "learning" in kw.lower() or "clinical" in kw.lower() for kw in keywords)

    def test_extract_from_explicit_keywords(self, agent):
        """Should use explicit keywords if provided."""
        config = {"keywords": ["diabetes", "treatment", "outcomes"]}
        keywords = agent._extract_keywords(config)
        
        assert "diabetes" in keywords
        assert "treatment" in keywords

    def test_extract_from_hypothesis(self, agent):
        """Should extract from hypothesis if available."""
        config = {
            "hypothesis": "We hypothesize that AI improves patient outcomes"
        }
        keywords = agent._extract_keywords(config)
        
        assert len(keywords) > 0


class TestBuildPubMedQuery:
    """Tests for _build_pubmed_query method."""

    def test_build_pubmed_query(self, agent):
        """Should build PubMed query correctly."""
        search_config = {
            "keywords": ["diabetes", "treatment"],
            "study_types": ["rct", "systematic_review"]
        }
        
        query = agent._build_pubmed_query(search_config)
        
        assert '"diabetes"' in query
        assert '"treatment"' in query
        assert "Randomized Controlled Trial[pt]" in query
        assert "Systematic Review[pt]" in query

    def test_build_query_no_keywords(self, agent):
        """Should return default query if no keywords."""
        search_config = {"keywords": []}
        
        query = agent._build_pubmed_query(search_config)
        
        assert query == "clinical trial"


class TestGenerateSummary:
    """Tests for _generate_summary method."""

    def test_generate_summary(self, agent):
        """Should generate summary with statistics."""
        papers = [
            {"year": 2023, "publicationType": "Research Article", "source": "pubmed", "citationCount": 10},
            {"year": 2024, "publicationType": "Review", "source": "semantic_scholar", "citationCount": 20},
        ]
        search_config = {"keywords": ["AI", "healthcare"]}
        
        summary = agent._generate_summary(papers, search_config)
        
        assert summary["total_papers"] == 2
        assert summary["search_keywords"] == ["AI", "healthcare"]
        assert 2023 in summary["year_distribution"]
        assert 2024 in summary["year_distribution"]
        assert summary["sources"]["pubmed"] == 1
        assert summary["sources"]["semantic_scholar"] == 1
        assert summary["avg_citations"] == 15.0


class TestArtifactSaving:
    """Tests for artifact saving methods."""

    def test_save_papers_json(self, agent, tmp_path):
        """Should save papers to JSON file."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        papers = [
            {"title": "Paper 1", "doi": "10.1/1"},
            {"title": "Paper 2", "doi": "10.1/2"},
        ]
        
        artifact_path = agent._save_papers_json(context, papers)
        
        assert os.path.exists(artifact_path)
        assert artifact_path.endswith("literature_papers.json")
        
        with open(artifact_path) as f:
            loaded = json.load(f)
            assert len(loaded) == 2

    def test_save_summary(self, agent, tmp_path):
        """Should save summary to JSON file."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        summary = {
            "total_papers": 10,
            "search_keywords": ["test"],
        }
        
        artifact_path = agent._save_summary(context, summary)
        
        assert os.path.exists(artifact_path)
        assert artifact_path.endswith("literature_summary.json")
        
        with open(artifact_path) as f:
            loaded = json.load(f)
            assert loaded["total_papers"] == 10


class TestExtractSearchConfig:
    """Tests for _extract_search_config method."""

    def test_extract_from_literature_config(self, agent):
        """Should extract from literature config section."""
        context = StageContext(
            job_id="test",
            config={
                "literature": {
                    "keywords": ["test", "keywords"],
                    "max_results": 30,
                    "date_range": {"start": "2020-01-01"},
                }
            },
            artifact_path="/tmp",
            governance_mode="DEMO",
        )
        
        config = agent._extract_search_config(context)
        
        assert config["keywords"] == ["test", "keywords"]
        assert config["max_results"] == 30

    def test_extract_from_stage_1_output(self, agent):
        """Should extract detected study type from Stage 1."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path="/tmp",
            governance_mode="DEMO",
            previous_results={
                1: MagicMock(output={"detected_study_type": "clinical_trial"})
            },
        )
        
        config = agent._extract_search_config(context)
        
        assert config["detected_study_type"] == "clinical_trial"
