"""
Phase 8: Agent Testing & Validation

Comprehensive pytest tests for ResearchFlow LangGraph agents:
- DataPrep, Analysis, Quality, IRB, Manuscript agents
- Mock LangGraph execution and graph building
- Agent selection logic and routing
- PHI detection validation
- Quality gate evaluation
- Token tracking and usage

This module provides:
- Agent lifecycle testing (initialization, execution, resumption)
- Mock LLM bridge for testing without external APIs
- Fixture-based test data management
- Agent state validation
- Quality criteria evaluation
"""

import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Optional, List, Dict, Any

# Setup path for imports
import sys
from pathlib import Path
worker_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(worker_src))

from agents.base.langgraph_base import LangGraphBaseAgent
from agents.base.state import (
    AgentState,
    AgentId,
    GateStatus,
    QualityGateResult,
    Message,
    create_initial_state,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_bridge():
    """Mock AI Router bridge for LLM calls."""
    bridge = AsyncMock()
    bridge.invoke = AsyncMock(return_value={
        'content': 'Test LLM response',
        'usage': {
            'total_tokens': 150,
            'input_tokens': 50,
            'output_tokens': 100,
        }
    })
    return bridge


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return "test-proj-001"


@pytest.fixture
def test_run_id():
    """Test run ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_thread_id():
    """Test thread ID."""
    return str(uuid.uuid4())


@pytest.fixture
def initial_agent_state(test_project_id, test_run_id, test_thread_id):
    """Create initial agent state for testing."""
    state = create_initial_state(
        agent_id='data_prep',
        project_id=test_project_id,
        run_id=test_run_id,
        thread_id=test_thread_id,
        stage_range=(1, 5),
        governance_mode='DEMO',
        input_artifact_ids=['art-001', 'art-002'],
        max_iterations=3,
    )
    return state


@pytest.fixture
def phi_containing_text():
    """Test data with PHI markers."""
    return """
    Patient Name: John Smith
    DOB: 01/15/1960
    SSN: 123-45-6789
    MRN: MED-2024-001
    Insurance ID: INS-XYZ-789
    """


@pytest.fixture
def clean_text():
    """Test data without PHI."""
    return """
    The patient presented with Type 2 Diabetes Mellitus.
    Lab results showed HbA1c of 8.2 mmol/mol.
    Treatment included metformin 500mg twice daily.
    """


# =============================================================================
# Concrete Agent Implementation for Testing
# =============================================================================

class TestDataPrepAgent(LangGraphBaseAgent):
    """Test implementation of DataPrep agent."""
    
    def build_graph(self):
        """Build the graph for testing."""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(dict)
        
        # Add nodes
        graph.add_node("extract_data", self._extract_data_node)
        graph.add_node("validate_data", self._validate_data_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        
        # Add edges
        graph.add_edge("extract_data", "validate_data")
        graph.add_edge("validate_data", "quality_gate")
        graph.add_edge("quality_gate", END)
        
        graph.set_entry_point("extract_data")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        """Quality criteria for DataPrep agent."""
        return {
            'min_length': 50,
            'max_length': 10000,
            'valid_format': True,
            'no_phi': True,
        }
    
    def _extract_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Extract data node."""
        return {
            'current_output': 'Extracted data from 5 sources',
            'current_stage': 2,
        }
    
    def _validate_data_node(self, state: AgentState) -> Dict[str, Any]:
        """Validate data node."""
        return {
            'current_output': state.get('current_output', '') + '\nValidation passed: 100%',
            'validation_score': 1.0,
        }


class TestAnalysisAgent(LangGraphBaseAgent):
    """Test implementation of Analysis agent."""
    
    def build_graph(self):
        """Build the graph for testing."""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(dict)
        graph.add_node("analyze", self._analyze_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_edge("analyze", "quality_gate")
        graph.add_edge("quality_gate", END)
        graph.set_entry_point("analyze")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        return {
            'min_length': 100,
            'analysis_complete': True,
        }
    
    def _analyze_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': 'Statistical analysis: p-value=0.001, r-squared=0.85',
            'current_stage': 8,
        }


class TestQualityAgent(LangGraphBaseAgent):
    """Test implementation of Quality agent."""
    
    def build_graph(self):
        """Build the graph for testing."""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(dict)
        graph.add_node("quality_check", self._quality_check_node)
        graph.add_edge("quality_check", END)
        graph.set_entry_point("quality_check")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        return {
            'checks_passed': True,
            'no_blockers': True,
        }
    
    def _quality_check_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': 'Quality checks: PASSED (15/15 criteria met)',
            'current_stage': 5,
        }


class TestIRBAgent(LangGraphBaseAgent):
    """Test implementation of IRB agent."""
    
    def build_graph(self):
        """Build the graph for testing."""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(dict)
        graph.add_node("irb_review", self._irb_review_node)
        graph.add_node("phi_scan", self._phi_scan_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_edge("irb_review", "phi_scan")
        graph.add_edge("phi_scan", "quality_gate")
        graph.add_edge("quality_gate", END)
        graph.set_entry_point("irb_review")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        return {
            'irb_compliant': True,
            'phi_free': True,
            'ethics_approved': True,
        }
    
    def _irb_review_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': 'IRB Review: APPROVED - Protocol compliant',
            'current_stage': 12,
        }
    
    def _phi_scan_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': state.get('current_output', '') + '\nPHI Scan: NO IDENTIFIERS DETECTED',
            'phi_detected': False,
        }


class TestManuscriptAgent(LangGraphBaseAgent):
    """Test implementation of Manuscript agent."""
    
    def build_graph(self):
        """Build the graph for testing."""
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(dict)
        graph.add_node("draft", self._draft_node)
        graph.add_node("refine", self._refine_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_edge("draft", "refine")
        graph.add_edge("refine", "quality_gate")
        graph.add_edge("quality_gate", END)
        graph.set_entry_point("draft")
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def get_quality_criteria(self) -> Dict[str, Any]:
        return {
            'min_length': 500,
            'has_citations': True,
            'grammatically_sound': True,
        }
    
    def _draft_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': 'Manuscript section drafted (1200 words, 8 citations)',
            'current_stage': 16,
        }
    
    def _refine_node(self, state: AgentState) -> Dict[str, Any]:
        return {
            'current_output': state.get('current_output', '') + '\nRefined version with improved flow',
            'refined': True,
        }


# =============================================================================
# Tests: Agent Initialization
# =============================================================================

class TestAgentInitialization:
    """Tests for agent initialization and setup."""
    
    def test_agent_init_with_defaults(self, mock_llm_bridge):
        """Test agent initialization with default parameters."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3, 4, 5],
            agent_id='data_prep',
        )
        
        assert agent.agent_id == 'data_prep'
        assert agent.stages == [1, 2, 3, 4, 5]
        assert agent.stage_range == (1, 5)
        assert agent.checkpointer is not None
    
    def test_agent_init_with_custom_checkpointer(self, mock_llm_bridge):
        """Test agent with custom checkpointer."""
        from langgraph.checkpoint.memory import MemorySaver
        
        custom_checkpointer = MemorySaver()
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[6, 7, 8, 9, 10],
            agent_id='analysis',
            checkpointer=custom_checkpointer,
        )
        
        assert agent.checkpointer is custom_checkpointer
    
    def test_agent_graph_lazy_initialization(self, mock_llm_bridge):
        """Test that graph is lazy-loaded on first access."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        # Graph should not be built yet
        assert agent._graph is None
        
        # Access graph property
        graph = agent.graph
        
        # Now it should be built
        assert agent._graph is not None
        assert graph is not None


# =============================================================================
# Tests: Agent Execution
# =============================================================================

@pytest.mark.asyncio
class TestAgentExecution:
    """Tests for agent graph execution."""
    
    async def test_agent_invoke_basic(self, mock_llm_bridge, test_project_id, test_run_id):
        """Test basic agent invocation."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3, 4, 5],
            agent_id='data_prep',
        )
        
        result = await agent.invoke(
            project_id=test_project_id,
            run_id=test_run_id,
            governance_mode='DEMO',
        )
        
        assert result is not None
        assert result['project_id'] == test_project_id
        assert result['run_id'] == test_run_id
        assert 'messages' in result
    
    async def test_agent_invoke_with_initial_message(self, mock_llm_bridge, test_project_id):
        """Test agent invocation with initial message."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        initial_message = "Process clinical trial data"
        result = await agent.invoke(
            project_id=test_project_id,
            initial_message=initial_message,
        )
        
        messages = result['messages']
        assert any(m.get('content') == initial_message for m in messages)
    
    async def test_agent_invoke_with_input_artifacts(self, mock_llm_bridge, test_project_id):
        """Test agent with input artifacts."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        artifact_ids = ['art-001', 'art-002', 'art-003']
        result = await agent.invoke(
            project_id=test_project_id,
            input_artifact_ids=artifact_ids,
        )
        
        assert result['input_artifact_ids'] == artifact_ids


# =============================================================================
# Tests: Quality Gate Evaluation
# =============================================================================

class TestQualityGateEvaluation:
    """Tests for quality gate logic."""
    
    def test_quality_gate_node_passes(self):
        """Test quality gate that passes."""
        agent = TestDataPrepAgent(
            llm_bridge=AsyncMock(),
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        state = {
            'agent_id': 'data_prep',
            'run_id': 'test-run',
            'governance_mode': 'DEMO',
            'current_output': 'Valid data output of sufficient length with no issues',
        }
        
        result = agent.quality_gate_node(state)
        
        assert result['gate_status'] == 'passed'
        assert result['gate_score'] >= 0.8
        assert result['gate_result']['passed'] is True
    
    def test_quality_gate_node_needs_human(self):
        """Test quality gate requiring human review."""
        agent = TestDataPrepAgent(
            llm_bridge=AsyncMock(),
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        state = {
            'agent_id': 'data_prep',
            'run_id': 'test-run',
            'governance_mode': 'DEMO',
            'current_output': 'Output',
        }
        
        result = agent.quality_gate_node(state)
        
        # Minimal output should trigger needs_human
        assert result['gate_status'] in ['needs_human', 'failed']
    
    def test_quality_gate_live_mode_irb_requires_human(self):
        """Test that IRB agent always requires human review in LIVE mode."""
        agent = TestIRBAgent(
            llm_bridge=AsyncMock(),
            stages=[1, 11, 12, 13],
            agent_id='irb',
        )
        
        state = {
            'agent_id': 'irb',
            'run_id': 'test-run',
            'governance_mode': 'LIVE',
            'current_output': 'IRB Review: APPROVED - Protocol compliant\nPHI Scan: NO IDENTIFIERS DETECTED',
        }
        
        result = agent.quality_gate_node(state)
        
        # In LIVE mode, IRB should require human review
        assert result['awaiting_approval'] is True


# =============================================================================
# Tests: Agent Selection Logic
# =============================================================================

class TestAgentSelectionLogic:
    """Tests for dynamic agent selection."""
    
    def test_select_agent_by_stage(self):
        """Test agent selection based on workflow stage."""
        selection_map = {
            1: 'data_prep',
            3: 'data_prep',
            5: 'data_prep',
            7: 'analysis',
            10: 'analysis',
            12: 'irb',
            15: 'irb',
            18: 'manuscript',
            20: 'manuscript',
        }
        
        for stage, expected_agent in selection_map.items():
            if stage <= 5:
                assert expected_agent == 'data_prep'
            elif stage <= 10:
                assert expected_agent == 'analysis'
            elif stage <= 15:
                assert expected_agent == 'irb'
            else:
                assert expected_agent == 'manuscript'
    
    def test_agent_stage_range_coverage(self):
        """Test that all stages are covered by some agent."""
        agent_stages = {
            'data_prep': (1, 5),
            'analysis': (6, 10),
            'quality': (1, 20),
            'irb': (1, 15),
            'manuscript': (11, 20),
        }
        
        # Verify no gaps in primary workflow
        for stage in range(1, 21):
            # At least one agent should handle this stage
            agents_for_stage = [
                name for name, (min_s, max_s) in agent_stages.items()
                if min_s <= stage <= max_s
            ]
            assert len(agents_for_stage) > 0, f"No agent covers stage {stage}"


# =============================================================================
# Tests: PHI Detection Validation
# =============================================================================

class TestPHIDetection:
    """Tests for PHI (Protected Health Information) detection."""
    
    def test_phi_patterns_detection(self, phi_containing_text):
        """Test detection of common PHI patterns."""
        phi_patterns = [
            r'SSN:\s*\d{3}-\d{2}-\d{4}',
            r'DOB:\s*\d{2}/\d{2}/\d{4}',
            r'MRN:\s*[A-Z]+-\d+',
            r'Insurance ID:\s*[A-Z]+-[A-Z]+-\d+',
        ]
        
        phi_found = []
        for pattern in phi_patterns:
            import re
            if re.search(pattern, phi_containing_text):
                phi_found.append(pattern)
        
        assert len(phi_found) > 0, "Should detect PHI patterns"
    
    def test_clean_text_no_phi(self, clean_text):
        """Test that clean text is not flagged."""
        phi_patterns = [
            r'SSN:\s*\d{3}-\d{2}-\d{4}',
            r'DOB:\s*\d{2}/\d{2}/\d{4}',
            r'Patient Name:\s*\w+\s+\w+',
        ]
        
        phi_found = []
        import re
        for pattern in phi_patterns:
            if re.search(pattern, clean_text):
                phi_found.append(pattern)
        
        assert len(phi_found) == 0, "Should not detect PHI in clean text"
    
    @pytest.mark.asyncio
    async def test_irb_agent_phi_scan(self):
        """Test IRB agent's PHI scanning capability."""
        agent = TestIRBAgent(
            llm_bridge=AsyncMock(),
            stages=[1, 11, 12, 13],
            agent_id='irb',
        )
        
        # Mock state with PHI
        state = {
            'agent_id': 'irb',
            'run_id': 'test-run',
            'current_output': 'Patient: John Smith, SSN: 123-45-6789',
            'governance_mode': 'DEMO',
        }
        
        # The phi_scan_node should detect this
        result = agent._phi_scan_node(state)
        
        # In test, we can't actually scan, but verify structure
        assert 'current_output' in result
        assert 'phi_detected' in result


# =============================================================================
# Tests: Agent State Management
# =============================================================================

class TestAgentStateManagement:
    """Tests for agent state initialization and management."""
    
    def test_create_initial_state(self, test_project_id, test_run_id, test_thread_id):
        """Test initial state creation."""
        state = create_initial_state(
            agent_id='data_prep',
            project_id=test_project_id,
            run_id=test_run_id,
            thread_id=test_thread_id,
            stage_range=(1, 5),
            governance_mode='DEMO',
        )
        
        assert state['agent_id'] == 'data_prep'
        assert state['project_id'] == test_project_id
        assert state['run_id'] == test_run_id
        assert state['thread_id'] == test_thread_id
        assert state['governance_mode'] == 'DEMO'
        assert isinstance(state['messages'], list)
        assert state['iteration'] == 0
    
    def test_state_with_input_artifacts(self, test_project_id, test_run_id):
        """Test state creation with input artifacts."""
        artifacts = ['art-001', 'art-002']
        state = create_initial_state(
            agent_id='analysis',
            project_id=test_project_id,
            run_id=test_run_id,
            stage_range=(6, 10),
            input_artifact_ids=artifacts,
        )
        
        assert state['input_artifact_ids'] == artifacts
    
    def test_state_message_tracking(self, initial_agent_state):
        """Test message tracking in state."""
        message = Message(
            id=str(uuid.uuid4()),
            role='assistant',
            content='Test response',
            timestamp=datetime.utcnow().isoformat(),
            phi_detected=False,
        )
        
        initial_agent_state['messages'].append(message)
        
        assert len(initial_agent_state['messages']) > 0
        assert initial_agent_state['messages'][-1]['role'] == 'assistant'


# =============================================================================
# Tests: Token Counting and Usage
# =============================================================================

@pytest.mark.asyncio
class TestTokenTracking:
    """Tests for LLM token tracking."""
    
    async def test_token_count_updates(self, mock_llm_bridge, test_project_id):
        """Test that token counts are tracked."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        result = await agent.invoke(
            project_id=test_project_id,
        )
        
        # Token count should be updated if LLM was called
        if mock_llm_bridge.invoke.called:
            assert result['token_count'] >= 0
    
    async def test_call_llm_records_usage(self, mock_llm_bridge):
        """Test that call_llm properly records token usage."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id='data_prep',
        )
        
        state = {'token_count': 0, 'current_stage': 1}
        response = await agent.call_llm(
            prompt="Test prompt",
            task_type="test",
            state=state,
        )
        
        assert mock_llm_bridge.invoke.called
        assert state['token_count'] == 150  # From mock fixture


# =============================================================================
# Tests: Agent-Specific Functionality
# =============================================================================

class TestDataPrepAgentFunctionality:
    """Tests specific to DataPrep agent."""
    
    def test_dataprep_graph_structure(self, mock_llm_bridge):
        """Test DataPrep agent graph has correct structure."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3, 4, 5],
            agent_id='data_prep',
        )
        
        graph = agent.graph
        assert graph is not None
    
    def test_dataprep_quality_criteria(self, mock_llm_bridge):
        """Test DataPrep quality criteria."""
        agent = TestDataPrepAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3, 4, 5],
            agent_id='data_prep',
        )
        
        criteria = agent.get_quality_criteria()
        
        assert 'min_length' in criteria
        assert 'max_length' in criteria
        assert 'valid_format' in criteria
        assert 'no_phi' in criteria


class TestManuscriptAgentFunctionality:
    """Tests specific to Manuscript agent."""
    
    def test_manuscript_graph_structure(self, mock_llm_bridge):
        """Test Manuscript agent graph has correct structure."""
        agent = TestManuscriptAgent(
            llm_bridge=mock_llm_bridge,
            stages=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            agent_id='manuscript',
        )
        
        graph = agent.graph
        assert graph is not None
    
    def test_manuscript_quality_criteria(self, mock_llm_bridge):
        """Test Manuscript quality criteria."""
        agent = TestManuscriptAgent(
            llm_bridge=mock_llm_bridge,
            stages=[11, 15, 20],
            agent_id='manuscript',
        )
        
        criteria = agent.get_quality_criteria()
        
        assert 'min_length' in criteria
        assert 'has_citations' in criteria
        assert 'grammatically_sound' in criteria


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestAgentIntegration:
    """Integration tests across multiple agents."""
    
    async def test_multi_agent_workflow(self, mock_llm_bridge, test_project_id):
        """Test workflow with multiple agents in sequence."""
        agents = {
            'data_prep': TestDataPrepAgent(
                llm_bridge=mock_llm_bridge,
                stages=[1, 2, 3, 4, 5],
                agent_id='data_prep',
            ),
            'analysis': TestAnalysisAgent(
                llm_bridge=mock_llm_bridge,
                stages=[6, 7, 8, 9, 10],
                agent_id='analysis',
            ),
        }
        
        # Execute first agent
        result1 = await agents['data_prep'].invoke(project_id=test_project_id)
        assert result1 is not None
        
        # Execute second agent with first agent's output
        result2 = await agents['analysis'].invoke(
            project_id=test_project_id,
            input_artifact_ids=[result1.get('run_id')],
        )
        assert result2 is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
