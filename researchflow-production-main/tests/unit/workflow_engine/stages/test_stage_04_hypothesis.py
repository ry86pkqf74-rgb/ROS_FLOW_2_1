"""
Unit tests for Stage 4: HypothesisRefinerAgent

Tests the HypothesisRefinerAgent implementation:
- Hypothesis extraction from config
- Literature findings integration from Stage 2
- Dataset columns validation
- Literature gap identification
- Hypothesis variant generation
- Variable extraction and categorization
- Testability validation
- DEMO mode handling
- Bridge integration with claude-writer
- Artifact generation
"""

import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_04_hypothesis import HypothesisRefinerAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create a HypothesisRefinerAgent instance."""
    return HypothesisRefinerAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext for testing."""
    return StageContext(
        job_id="test-job",
        config={
            "studyTitle": "Effects of Treatment on Patient Outcomes",
            "hypothesis": "We hypothesize that treatment A improves patient outcomes compared to treatment B",
            "columns": ["patient_id", "treatment", "outcome_score", "age", "gender"]
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
        previous_results={
            2: MagicMock(output={
                "ranked_papers": [
                    {
                        "title": "Treatment Efficacy Study",
                        "doi": "10.1234/test",
                        "citationCount": 50,
                        "year": 2023,
                        "abstract": "This study investigates treatment outcomes",
                        "publicationType": "Research Article",
                    }
                ],
                "key_papers": [],
                "literature_summary": {
                    "search_keywords": ["treatment", "outcomes"],
                    "total_papers": 1
                }
            }),
            4: MagicMock(output={
                "schema_metadata": {
                    "columns": ["patient_id", "treatment", "outcome_score", "age", "gender"],
                    "column_count": 5
                }
            })
        },
    )


@pytest.fixture
def mock_literature_findings():
    """Mock Stage 2 literature findings."""
    return {
        "ranked_papers": [
            {
                "title": "Treatment Efficacy in Clinical Trials",
                "doi": "10.1234/test1",
                "citationCount": 100,
                "year": 2024,
                "abstract": "This systematic review examines treatment efficacy",
                "publicationType": "Systematic Review",
            },
            {
                "title": "Patient Outcomes Research",
                "doi": "10.5678/test2",
                "citationCount": 50,
                "year": 2023,
                "abstract": "Study of patient outcomes",
                "publicationType": "Research Article",
            },
        ],
        "key_papers": [
            {
                "title": "Treatment Efficacy in Clinical Trials",
                "doi": "10.1234/test1",
                "citationCount": 100,
                "year": 2024,
                "publicationType": "Systematic Review",
            }
        ],
        "literature_summary": {
            "search_keywords": ["treatment", "outcomes", "efficacy"],
            "total_papers": 2,
            "year_distribution": {2023: 1, 2024: 1}
        }
    }


@pytest.fixture
def mock_claude_writer_response():
    """Mock claude-writer service response."""
    return {
        "paragraph": "The hypothesis was refined based on identified research gaps in treatment efficacy studies and the availability of outcome variables in the dataset.",
        "content": "The hypothesis was refined based on identified research gaps..."
    }


class TestHypothesisRefinerAgent:
    """Tests for HypothesisRefinerAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 4
        assert agent.stage_name == "Hypothesis Refinement"

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
    async def test_execute_success(self, agent, sample_context, mock_claude_writer_response):
        """Execute should succeed with complete context."""
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_claude_writer_response
            
            result = await agent.execute(sample_context)
            
            assert result.status == "completed"
            assert "original_hypothesis" in result.output
            assert "refined_hypothesis" in result.output
            assert "secondary_hypotheses" in result.output
            assert "literature_gaps" in result.output
            assert "key_variables" in result.output
            assert "testability_score" in result.output
            assert "refinement_rationale" in result.output
            assert len(result.artifacts) == 1  # refined_hypothesis.json

    @pytest.mark.asyncio
    async def test_execute_with_stage_2_output(self, agent, tmp_path, mock_literature_findings, mock_claude_writer_response):
        """Execute should use Stage 2 output for literature context."""
        context = StageContext(
            job_id="test-job",
            config={
                "hypothesis": "Treatment improves outcomes",
                "columns": ["treatment", "outcome"]
            },
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
            previous_results={
                2: MagicMock(output=mock_literature_findings)
            }
        )
        
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_claude_writer_response
            
            result = await agent.execute(context)
            
            assert result.status == "completed"
            assert result.output.get("literature_papers_reviewed") == 2
            assert len(result.output.get("literature_gaps", [])) > 0

    @pytest.mark.asyncio
    async def test_execute_without_stage_2_demo_mode(self, agent, tmp_path, mock_claude_writer_response):
        """DEMO mode should handle missing Stage 2 output gracefully."""
        context = StageContext(
            job_id="test-job",
            config={"hypothesis": "Test hypothesis"},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_claude_writer_response
            
            result = await agent.execute(context)
            
            # Should succeed with warnings in DEMO mode
            assert result.status == "completed"
            assert any("Stage 2 output not found" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_without_stage_2_live_mode(self, agent, tmp_path):
        """LIVE mode should fail if Stage 2 output missing."""
        context = StageContext(
            job_id="test-job",
            config={"hypothesis": "Test hypothesis"},
            artifact_path=str(tmp_path),
            governance_mode="LIVE",
        )
        
        result = await agent.execute(context)
        
        assert result.status == "failed"
        assert any("Stage 2" in err for err in result.errors)


class TestExtractInitialHypothesis:
    """Tests for _extract_initial_hypothesis method."""

    def test_extract_from_config(self, agent, tmp_path):
        """Should extract hypothesis from config."""
        context = StageContext(
            job_id="test",
            config={"hypothesis": "Test hypothesis"},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        hypothesis = agent._extract_initial_hypothesis(context)
        assert hypothesis == "Test hypothesis"

    def test_extract_from_research_question(self, agent, tmp_path):
        """Should extract from research_question field."""
        context = StageContext(
            job_id="test",
            config={"research_question": "What is the effect?"},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        hypothesis = agent._extract_initial_hypothesis(context)
        assert "effect" in hypothesis.lower()

    def test_demo_mode_default_generation(self, agent, tmp_path):
        """DEMO mode should generate default hypothesis if missing."""
        context = StageContext(
            job_id="test",
            config={
                "studyTitle": "Effects of Treatment",
                "columns": ["treatment", "outcome"]
            },
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
            previous_results={
                2: MagicMock(output={
                    "literature_summary": {"search_keywords": ["treatment"]}
                })
            }
        )
        
        hypothesis = agent._extract_initial_hypothesis(context)
        assert len(hypothesis) > 0
        assert "hypothesize" in hypothesis.lower() or "associated" in hypothesis.lower()


class TestGetLiteratureFindings:
    """Tests for _get_literature_findings method."""

    def test_get_from_stage_2(self, agent, tmp_path, mock_literature_findings):
        """Should retrieve literature findings from Stage 2."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
            previous_results={
                2: MagicMock(output=mock_literature_findings)
            }
        )
        
        findings = agent._get_literature_findings(context)
        assert findings["total_unique_papers"] == 2
        assert len(findings["ranked_papers"]) == 2
        assert len(findings["key_papers"]) == 1

    def test_get_empty_if_no_stage_2(self, agent, tmp_path):
        """Should return empty dict if Stage 2 output missing."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        findings = agent._get_literature_findings(context)
        assert findings == {}


class TestGetDatasetColumns:
    """Tests for _get_dataset_columns method."""

    def test_get_from_stage_4(self, agent, tmp_path):
        """Should get columns from Stage 4 schema metadata."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
            previous_results={
                4: MagicMock(output={
                    "schema_metadata": {
                        "columns": ["col1", "col2", "col3"]
                    }
                })
            }
        )
        
        columns = agent._get_dataset_columns(context)
        assert columns == ["col1", "col2", "col3"]

    def test_get_from_config(self, agent, tmp_path):
        """Should get columns from config if Stage 4 not available."""
        context = StageContext(
            job_id="test",
            config={"columns": ["col1", "col2"]},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        columns = agent._get_dataset_columns(context)
        assert "col1" in columns
        assert "col2" in columns

    def test_get_empty_if_none(self, agent, tmp_path):
        """Should return empty list if no columns found."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        columns = agent._get_dataset_columns(context)
        assert columns == []


class TestIdentifyGaps:
    """Tests for _identify_gaps method."""

    def test_identify_gaps_with_papers(self, agent, mock_literature_findings):
        """Should identify research gaps from papers."""
        gaps = agent._identify_gaps(
            mock_literature_findings["ranked_papers"],
            mock_literature_findings["key_papers"],
            mock_literature_findings["literature_summary"]["search_keywords"]
        )
        
        assert len(gaps) > 0
        assert isinstance(gaps, list)

    def test_identify_gaps_no_papers(self, agent):
        """Should return default gap if no papers."""
        gaps = agent._identify_gaps([], [], [])
        
        assert len(gaps) > 0
        assert "Insufficient literature" in gaps[0]

    def test_identify_gaps_checks_systematic_reviews(self, agent):
        """Should check for systematic reviews."""
        papers = [
            {
                "title": "Systematic Review",
                "publicationType": "Systematic Review",
                "year": 2024
            }
        ]
        
        gaps = agent._identify_gaps(papers, papers, ["treatment"])
        # Should not flag missing systematic review
        assert len(gaps) > 0


class TestGenerateHypothesisVariants:
    """Tests for _generate_hypothesis_variants method."""

    def test_generate_variants(self, agent):
        """Should generate refined hypothesis and secondary hypotheses."""
        original = "Treatment improves outcomes"
        gaps = ["Limited recent research"]
        findings = {}
        columns = ["treatment", "outcome", "age"]
        
        refined, secondary = agent._generate_hypothesis_variants(
            original, gaps, findings, columns
        )
        
        assert len(refined) > 0
        assert len(secondary) >= 2
        assert len(secondary) <= 3

    def test_generate_variants_with_columns(self, agent):
        """Should use columns to generate variants."""
        original = "Treatment improves outcomes"
        gaps = []
        findings = {}
        columns = ["treatment_type", "outcome_score", "patient_age"]
        
        refined, secondary = agent._generate_hypothesis_variants(
            original, gaps, findings, columns
        )
        
        # Should generate variants referencing columns
        assert len(secondary) >= 2


class TestExtractVariables:
    """Tests for _extract_variables method."""

    def test_extract_variables(self, agent):
        """Should extract and categorize variables."""
        hypothesis = "Treatment predicts outcome"
        columns = ["treatment", "outcome", "age", "gender"]
        
        variables = agent._extract_variables(hypothesis, columns)
        
        assert "independent" in variables
        assert "dependent" in variables
        assert "confounding" in variables
        assert isinstance(variables["independent"], list)
        assert isinstance(variables["dependent"], list)
        assert isinstance(variables["confounding"], list)

    def test_extract_variables_from_column_names(self, agent):
        """Should infer variable types from column names."""
        hypothesis = "Study of outcomes"
        columns = ["treatment_type", "outcome_score", "patient_age", "gender"]
        
        variables = agent._extract_variables(hypothesis, columns)
        
        # Should identify treatment as independent, outcome as dependent
        assert len(variables["independent"]) > 0 or len(variables["dependent"]) > 0


class TestValidateTestability:
    """Tests for _validate_testability method."""

    def test_validate_testability_high_score(self, agent):
        """Should return high score when variables match columns."""
        hypothesis = "Treatment predicts outcome"
        variables = {
            "independent": ["treatment"],
            "dependent": ["outcome"],
            "confounding": ["age"]
        }
        columns = ["treatment", "outcome", "age"]
        
        score = agent._validate_testability(hypothesis, variables, columns)
        
        assert score > 0.5
        assert score <= 1.0

    def test_validate_testability_low_score(self, agent):
        """Should return low score when no columns available."""
        hypothesis = "Treatment predicts outcome"
        variables = {
            "independent": ["treatment"],
            "dependent": ["outcome"],
            "confounding": []
        }
        columns = []
        
        score = agent._validate_testability(hypothesis, variables, columns)
        
        assert score < 0.5

    def test_validate_testability_partial_match(self, agent):
        """Should return medium score for partial variable match."""
        hypothesis = "Treatment predicts outcome"
        variables = {
            "independent": ["treatment"],
            "dependent": ["outcome"],
            "confounding": []
        }
        columns = ["treatment"]  # Missing outcome
        
        score = agent._validate_testability(hypothesis, variables, columns)
        
        assert 0.3 <= score <= 0.7


class TestGenerateRefinementRationale:
    """Tests for _generate_refinement_rationale method."""

    @pytest.mark.asyncio
    async def test_generate_rationale_via_bridge(self, agent, mock_claude_writer_response):
        """Should generate rationale using claude-writer service."""
        original = "Original hypothesis"
        refined = "Refined hypothesis"
        gaps = ["Gap 1", "Gap 2"]
        variables = {
            "independent": ["var1"],
            "dependent": ["var2"],
            "confounding": []
        }
        
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_claude_writer_response
            
            rationale = await agent._generate_refinement_rationale(
                original, refined, gaps, variables
            )
            
            assert len(rationale) > 0
            mock_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_rationale_fallback(self, agent):
        """Should fallback to local generation if bridge fails."""
        original = "Original hypothesis"
        refined = "Refined hypothesis"
        gaps = ["Gap 1"]
        variables = {
            "independent": ["var1"],
            "dependent": ["var2"],
            "confounding": []
        }
        
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.side_effect = Exception("Service unavailable")
            
            rationale = await agent._generate_refinement_rationale(
                original, refined, gaps, variables
            )
            
            assert len(rationale) > 0
            assert "original hypothesis" in rationale.lower() or "refined" in rationale.lower()


class TestGenerateDefaultHypothesis:
    """Tests for _generate_default_hypothesis method."""

    def test_generate_default_with_columns(self, agent):
        """Should generate default hypothesis using columns."""
        study_title = "Effects of Treatment"
        columns = ["treatment_type", "outcome_score", "age"]
        keywords = ["treatment"]
        
        hypothesis = agent._generate_default_hypothesis(study_title, columns, keywords)
        
        assert len(hypothesis) > 0
        assert "hypothesize" in hypothesis.lower() or "associated" in hypothesis.lower()

    def test_generate_default_without_columns(self, agent):
        """Should generate default hypothesis without columns."""
        study_title = "Research Study"
        columns = []
        keywords = ["research"]
        
        hypothesis = agent._generate_default_hypothesis(study_title, columns, keywords)
        
        assert len(hypothesis) > 0


class TestSaveRefinedHypothesis:
    """Tests for _save_refined_hypothesis method."""

    def test_save_artifact(self, agent, tmp_path):
        """Should save refined hypothesis to JSON file."""
        context = StageContext(
            job_id="test",
            config={},
            artifact_path=str(tmp_path),
            governance_mode="DEMO",
        )
        
        output = {
            "original_hypothesis": "Original",
            "refined_hypothesis": "Refined",
            "secondary_hypotheses": ["Secondary 1", "Secondary 2"],
            "literature_gaps": ["Gap 1"],
            "key_variables": {
                "independent": ["var1"],
                "dependent": ["var2"],
                "confounding": []
            },
            "testability_score": 0.8,
            "refinement_rationale": "Rationale",
            "dataset_columns_used": ["col1"],
            "literature_papers_reviewed": 5
        }
        
        artifact_path = agent._save_refined_hypothesis(context, output)
        
        assert os.path.exists(artifact_path)
        assert artifact_path.endswith("refined_hypothesis.json")
        
        with open(artifact_path) as f:
            loaded = json.load(f)
            assert loaded["original_hypothesis"] == "Original"
            assert loaded["refined_hypothesis"] == "Refined"
            assert len(loaded["secondary_hypotheses"]) == 2
            assert loaded["testability_score"] == 0.8


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_analyze_literature_gaps_tool(self, agent):
        """Tool should analyze gaps from papers JSON."""
        papers = [
            {"title": "Paper 1", "year": 2023},
            {"title": "Paper 2", "year": 2024}
        ]
        
        result = agent._analyze_literature_gaps_tool(json.dumps(papers))
        
        assert "gaps" in result.lower() or "gap" in result.lower()

    def test_generate_hypothesis_variants_tool(self, agent):
        """Tool should generate variants from hypothesis."""
        original = "Treatment improves outcomes"
        
        result = agent._generate_hypothesis_variants_tool(original)
        
        assert "refined" in result.lower() or "secondary" in result.lower()

    def test_validate_hypothesis_testability_tool(self, agent):
        """Tool should validate testability."""
        hypothesis = "Treatment predicts outcome"
        columns = ["treatment", "outcome"]
        
        result = agent._validate_hypothesis_testability_tool(
            hypothesis, json.dumps(columns)
        )
        
        assert "testability" in result.lower() or "score" in result.lower()

    def test_extract_key_variables_tool(self, agent):
        """Tool should extract variables."""
        hypothesis = "Treatment predicts outcome"
        columns = ["treatment", "outcome", "age"]
        
        result = agent._extract_key_variables_tool(
            hypothesis, json.dumps(columns)
        )
        
        assert "independent" in result.lower() or "dependent" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(self, agent, sample_context, mock_claude_writer_response):
        """Output should match required schema."""
        with patch.object(agent, 'call_manuscript_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_claude_writer_response
            
            result = await agent.execute(sample_context)
            
            output = result.output
            
            # Required fields
            assert "original_hypothesis" in output
            assert "refined_hypothesis" in output
            assert "secondary_hypotheses" in output
            assert isinstance(output["secondary_hypotheses"], list)
            assert len(output["secondary_hypotheses"]) >= 2
            assert len(output["secondary_hypotheses"]) <= 3
            
            assert "literature_gaps" in output
            assert isinstance(output["literature_gaps"], list)
            
            assert "key_variables" in output
            assert isinstance(output["key_variables"], dict)
            assert "independent" in output["key_variables"]
            assert "dependent" in output["key_variables"]
            assert "confounding" in output["key_variables"]
            
            assert "testability_score" in output
            assert isinstance(output["testability_score"], float)
            assert 0.0 <= output["testability_score"] <= 1.0
            
            assert "refinement_rationale" in output
            assert isinstance(output["refinement_rationale"], str)
            
            assert "dataset_columns_used" in output
            assert "literature_papers_reviewed" in output
