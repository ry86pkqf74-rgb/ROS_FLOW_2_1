"""
Test Suite for GapAnalysisAgent

Tests covering:
- Gap identification
- Literature comparison
- PICO generation
- Prioritization
- Quality checks
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from gap_analysis_agent import GapAnalysisAgent, create_gap_analysis_agent
from gap_analysis_types import *
from gap_analysis_utils import LiteratureComparator, PICOExtractor
from gap_prioritization import GapPrioritizer
from pico_generator import PICOGenerator
from lit_search_agent import StudyContext, Paper


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_study_context():
    """Sample study for testing."""
    return StudyContext(
        title="Impact of Mindfulness on Anxiety in College Students",
        keywords=["mindfulness", "anxiety", "college", "students"],
        research_question="Does MBSR reduce anxiety in college students?",
        study_type="Randomized Controlled Trial",
        population="College students aged 18-25",
        intervention="8-week MBSR program",
        outcome="GAD-7 anxiety score"
    )


@pytest.fixture
def sample_literature():
    """Sample literature papers."""
    return [
        Paper(
            title="Mindfulness for Anxiety: A Meta-Analysis",
            authors=["Smith J", "Doe A", "Jones B"],
            abstract="Meta-analysis of 25 RCTs showing moderate effect of mindfulness on anxiety.",
            doi="10.1234/meta2020",
            year=2020,
            source="pubmed",
            journal="Journal of Anxiety",
            citation_count=150
        ),
        Paper(
            title="MBSR in College Students: Pilot Study",
            authors=["Brown C", "Green D"],
            abstract="Pilot RCT with 30 students showing promising results.",
            doi="10.1234/pilot2019",
            year=2019,
            source="pubmed",
            journal="Student Health",
            citation_count=25
        ),
        Paper(
            title="Long-term Effects of Mindfulness Training",
            authors=["White E", "Black F"],
            abstract="Cohort study following students for 2 years post-intervention.",
            doi="10.1234/longterm2018",
            year=2018,
            source="pubmed",
            journal="Psychology",
            citation_count=40
        )
    ]


@pytest.fixture
def sample_findings():
    """Sample findings from statistical analysis."""
    return [
        Finding(
            description="MBSR reduced GAD-7 scores by 30% compared to control",
            effect_size=0.72,
            significance=0.001,
            confidence="high",
            statistical_test="Independent t-test"
        ),
        Finding(
            description="Benefits maintained at 3-month follow-up",
            effect_size=0.65,
            significance=0.005,
            confidence="high",
            statistical_test="Paired t-test"
        )
    ]


@pytest.fixture
def sample_gaps():
    """Sample research gaps."""
    return [
        Gap(
            gap_type=GapType.POPULATION,
            description="Limited research on non-traditional students (>25 years)",
            evidence_level=EvidenceLevel.STRONG,
            addressability=Addressability.FEASIBLE,
            impact_score=4.0,
            feasibility_score=4.5,
            related_papers=["10.1234/meta2020"]
        ),
        Gap(
            gap_type=GapType.TEMPORAL,
            description="Most studies conducted pre-2015, need updated evidence",
            evidence_level=EvidenceLevel.MODERATE,
            addressability=Addressability.FEASIBLE,
            impact_score=3.5,
            feasibility_score=4.0,
            related_papers=["10.1234/longterm2018"]
        ),
        Gap(
            gap_type=GapType.METHODOLOGICAL,
            description="Lack of active control groups in most trials",
            evidence_level=EvidenceLevel.STRONG,
            addressability=Addressability.CHALLENGING,
            impact_score=4.5,
            feasibility_score=2.5,
            related_papers=["10.1234/pilot2019"]
        )
    ]


# =============================================================================
# Agent Tests
# =============================================================================

@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent can be initialized with correct config."""
    agent = create_gap_analysis_agent()
    
    assert agent.config.name == "GapAnalysisAgent"
    assert 10 in agent.config.stages
    assert agent.config.quality_threshold == 0.80
    assert agent.comparator is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_gap_analysis(sample_study_context, sample_literature, sample_findings):
    """Integration test: complete gap analysis workflow."""
    agent = create_gap_analysis_agent()
    
    # Mock LLM responses to avoid actual API calls in tests
    with patch.object(agent, 'llm') as mock_llm:
        mock_llm.ainvoke = AsyncMock(return_value=Mock(
            content='{"steps": ["compare", "identify", "prioritize"]}'
        ))
        
        result = await agent.execute(
            study=sample_study_context,
            literature=sample_literature,
            findings=sample_findings
        )
        
        # Assertions
        assert isinstance(result, GapAnalysisResult)
        # Note: With mocked LLM, we mainly test the structure works


@pytest.mark.asyncio
async def test_quality_check_diversity(sample_gaps):
    """Test quality check assesses gap diversity."""
    agent = create_gap_analysis_agent()
    
    # Create mock state with gaps
    state = {
        "execution_result": {
            "prioritized_gaps": [
                {"gap": g.model_dump(), "priority_score": 7.0}
                for g in sample_gaps
            ],
            "research_suggestions": [
                {"research_question": "Q1", "pico_framework": {"population": "P"}}
            ],
            "narrative": " ".join(["word"] * 300)
        },
        "iteration": 1
    }
    
    quality_result = await agent._check_quality(state)
    
    assert quality_result.score > 0.0
    assert "diversity" in quality_result.criteria_scores
    # 3 gap types out of 6 = 0.5
    assert quality_result.criteria_scores["diversity"] == 0.5


# =============================================================================
# Literature Comparison Tests
# =============================================================================

@pytest.mark.asyncio
async def test_literature_comparator_semantic():
    """Test semantic literature comparison with embeddings."""
    comparator = LiteratureComparator()
    
    # Mock OpenAI client
    with patch.object(comparator, 'client') as mock_client:
        mock_embedding_response = Mock()
        mock_embedding_response.data = [
            Mock(embedding=[0.1] * 3072),
            Mock(embedding=[0.2] * 3072),
            Mock(embedding=[0.15] * 3072)
        ]
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)
        
        findings = ["Finding 1", "Finding 2"]
        literature = [
            {"paper_id": "p1", "title": "Paper 1", "abstract": "Abstract 1"}
        ]
        
        comparisons = await comparator.compare_findings_semantic(findings, literature)
        
        assert len(comparisons) == 2  # 2 findings x 1 paper
        assert all(len(c) == 4 for c in comparisons)  # (finding, id, title, score)


def test_literature_comparator_categorize_similarity():
    """Test similarity categorization thresholds."""
    comparator = LiteratureComparator()
    
    assert comparator.categorize_similarity(0.95) == "consistent_with"
    assert comparator.categorize_similarity(0.75) == "extends"
    assert comparator.categorize_similarity(0.50) == "novel_findings"
    assert comparator.categorize_similarity(0.25) == "contradicts"


# =============================================================================
# PICO Tests
# =============================================================================

def test_pico_extraction_from_text():
    """Test PICO component extraction from text."""
    text = "In adults with diabetes, does metformin compared to placebo reduce HbA1c?"
    
    pico_dict = PICOExtractor.extract_from_text(text)
    
    assert "diabetes" in pico_dict["population"].lower()
    assert "metformin" in pico_dict["intervention"].lower()
    assert "placebo" in pico_dict["comparison"].lower()


def test_pico_generator_from_gap(sample_gaps):
    """Test PICO generation from research gap."""
    generator = PICOGenerator()
    
    gap = sample_gaps[0]  # Population gap
    study_context = {
        "population": "college students",
        "intervention": "MBSR",
        "outcome": "anxiety"
    }
    
    pico = generator.generate_from_gap(gap, study_context)
    
    assert pico.population is not None
    assert pico.intervention is not None
    assert pico.outcome is not None
    assert len(pico.format_research_question()) > 20


def test_pico_pubmed_query_generation():
    """Test PubMed query generation from PICO."""
    pico = PICOFramework(
        population="college students",
        intervention="mindfulness",
        comparison="control",
        outcome="anxiety"
    )
    
    query = pico.generate_pubmed_query()
    
    assert "college students" in query
    assert "mindfulness" in query
    assert "anxiety" in query
    assert "AND" in query


# =============================================================================
# Prioritization Tests
# =============================================================================

def test_gap_prioritizer_prioritize(sample_gaps):
    """Test gap prioritization algorithm."""
    prioritizer = GapPrioritizer()
    
    prioritized = prioritizer.prioritize_gaps(sample_gaps)
    
    assert len(prioritized) == len(sample_gaps)
    assert all(isinstance(g, PrioritizedGap) for g in prioritized)
    # Should be sorted by priority score
    assert prioritized[0].priority_score >= prioritized[-1].priority_score


def test_gap_prioritizer_matrix(sample_gaps):
    """Test prioritization matrix generation."""
    prioritizer = GapPrioritizer()
    
    matrix = prioritizer.create_prioritization_matrix(sample_gaps)
    
    assert isinstance(matrix, PrioritizationMatrix)
    assert len(matrix.high_priority) > 0 or len(matrix.strategic) > 0
    assert matrix.visualization_config is not None
    assert matrix.visualization_config["type"] == "scatter"


def test_priority_level_determination():
    """Test priority level classification."""
    prioritizer = GapPrioritizer()
    
    # High priority: high impact + high feasibility
    assert prioritizer._determine_priority_level(4.5, 4.5) == GapPriority.HIGH
    
    # Strategic: high impact + low feasibility
    assert prioritizer._determine_priority_level(4.5, 2.0) == GapPriority.STRATEGIC
    
    # Low priority: low impact + low feasibility
    assert prioritizer._determine_priority_level(2.0, 2.0) == GapPriority.LOW


# =============================================================================
# Type Validation Tests
# =============================================================================

def test_gap_analysis_result_validation():
    """Test GapAnalysisResult type validation."""
    result = GapAnalysisResult(
        comparisons=ComparisonResult(overall_similarity_score=0.75),
        knowledge_gaps=[],
        research_suggestions=[]
    )
    
    assert result.total_gaps_identified == 0
    result.calculate_summary_stats()
    assert result.gap_diversity_score == 0.0


def test_pico_framework_validation():
    """Test PICO framework validation."""
    pico = PICOFramework(
        population="adults",
        intervention="drug A",
        comparison="placebo",
        outcome="symptom reduction"
    )
    
    assert pico.format_research_question().endswith("?")
    assert "adults" in pico.format_research_question()


def test_prioritized_gap_validation():
    """Test PrioritizedGap validation."""
    gap = Gap(
        gap_type=GapType.EMPIRICAL,
        description="Missing data on X",
        evidence_level=EvidenceLevel.MODERATE,
        addressability=Addressability.FEASIBLE,
        impact_score=3.5,
        feasibility_score=4.0
    )
    
    prioritized = PrioritizedGap(
        gap=gap,
        priority_score=7.5,
        priority_level=GapPriority.MEDIUM,
        rationale="Test",
        feasibility="Feasible",
        expected_impact="Moderate"
    )
    
    assert prioritized.priority_score == 7.5
    assert prioritized.gap.gap_type == GapType.EMPIRICAL


# =============================================================================
# Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_empty_literature_handling():
    """Test handling of empty literature list."""
    agent = create_gap_analysis_agent()
    
    study = StudyContext(
        title="Test",
        research_question="Q?",
        study_type="RCT"
    )
    
    result = await agent.execute(study, [], [])
    
    # Should return valid result even with empty literature
    assert isinstance(result, GapAnalysisResult)


def test_pico_extraction_with_minimal_text():
    """Test PICO extraction with minimal/ambiguous text."""
    text = "Does X affect Y?"
    
    pico_dict = PICOExtractor.extract_from_text(text)
    
    # Should not crash, may have None values
    assert "population" in pico_dict
    assert "intervention" in pico_dict


def test_gap_categorizer_with_ambiguous_description():
    """Test gap categorization with ambiguous description."""
    from gap_analysis_utils import GapCategorizer
    
    ambiguous = "There is a lack of understanding"
    
    gap_type = GapCategorizer.suggest_gap_type(ambiguous)
    
    # Should return a valid type (defaults to empirical)
    assert gap_type in ["empirical", "theoretical", "methodological"]


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
