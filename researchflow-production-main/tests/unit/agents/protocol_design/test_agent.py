"""
Unit tests for Protocol Design Agent

Tests the Stage 1 ProtocolDesignAgent functionality including:
- Entry mode detection (Quick Entry, PICO Direct, Hypothesis)
- PICO extraction and validation
- Hypothesis generation
- Study type detection
- Protocol outline generation
- Quality gates and improvement loops
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

# Import the agent and dependencies
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.agents.protocol_design.agent import ProtocolDesignAgent
from src.agents.common.pico import PICOElements
from src.agents.base.state import AgentState, create_initial_state


class TestProtocolDesignAgent:
    """Tests for ProtocolDesignAgent core functionality"""
    
    @pytest.fixture
    def mock_llm_bridge(self):
        """Mock LLM bridge for testing"""
        bridge = AsyncMock()
        bridge.invoke = AsyncMock()
        return bridge
    
    @pytest.fixture
    def agent(self, mock_llm_bridge):
        """Create ProtocolDesignAgent instance for testing"""
        return ProtocolDesignAgent(llm_bridge=mock_llm_bridge)
    
    @pytest.fixture
    def sample_state(self) -> AgentState:
        """Create sample agent state for testing"""
        return create_initial_state(
            agent_id='protocol_design',
            project_id='test-project',
            run_id='test-run',
            thread_id='test-thread',
            stage_range=(1, 1),
            governance_mode='DEMO',
        )
    
    @pytest.fixture
    def sample_pico_data(self) -> Dict[str, Any]:
        """Sample PICO elements for testing"""
        return {
            'population': 'Adults aged 40-65 with Type 2 diabetes',
            'intervention': 'Structured exercise program (150 min/week)',
            'comparator': 'Standard diabetes care without exercise',
            'outcomes': ['HbA1c reduction', 'Weight loss', 'Cardiovascular events'],
            'timeframe': '12 months follow-up'
        }

    def test_agent_initialization(self, mock_llm_bridge):
        """Should initialize agent with correct properties"""
        agent = ProtocolDesignAgent(llm_bridge=mock_llm_bridge)
        
        assert agent.agent_id == 'protocol_design'
        assert agent.stages == [1]
        assert agent.stage_range == (1, 1)
        assert agent.llm is mock_llm_bridge

    def test_quality_criteria(self, agent):
        """Should define appropriate quality criteria"""
        criteria = agent.get_quality_criteria()
        
        expected_criteria = [
            'pico_complete', 'pico_quality_score', 'hypothesis_generated',
            'study_type_identified', 'protocol_sections', 'min_protocol_length',
            'phi_compliant'
        ]
        
        for criterion in expected_criteria:
            assert criterion in criteria

        # Check specific thresholds
        assert criteria['pico_quality_score'] == 70.0
        assert criteria['protocol_sections'] == 7
        assert criteria['min_protocol_length'] == 500

    def test_graph_construction(self, agent):
        """Should build graph with correct nodes and edges"""
        graph = agent.build_graph()
        
        # Verify graph is compiled and callable
        assert graph is not None
        assert callable(graph.ainvoke)

    # =========================================================================
    # Entry Mode Detection Tests
    # =========================================================================

    def test_detect_entry_mode_quick_entry(self, agent, sample_state):
        """Should detect quick entry mode for natural language"""
        state = sample_state.copy()
        state['messages'] = [{
            'role': 'user',
            'content': 'I want to study the effects of exercise on diabetes in adults'
        }]
        
        result = agent.detect_entry_mode_node(state)
        
        assert result['entry_mode'] == 'quick_entry'
        assert result['current_stage'] == 1
        assert result['input_text'] == 'I want to study the effects of exercise on diabetes in adults'

    def test_detect_entry_mode_pico_direct(self, agent, sample_state):
        """Should detect PICO direct mode when structured elements provided"""
        state = sample_state.copy()
        state['messages'] = [{
            'role': 'user',
            'content': 'Population: diabetic adults, Intervention: exercise, Comparator: standard care, Outcomes: HbA1c, Timeframe: 6 months'
        }]
        
        result = agent.detect_entry_mode_node(state)
        
        assert result['entry_mode'] == 'pico_direct'

    def test_detect_entry_mode_hypothesis(self, agent, sample_state):
        """Should detect hypothesis mode when hypothesis keywords present"""
        state = sample_state.copy()
        state['messages'] = [{
            'role': 'user',
            'content': 'We hypothesize that exercise compared to standard care will show significant improvement in glucose control'
        }]
        
        result = agent.detect_entry_mode_node(state)
        
        assert result['entry_mode'] == 'hypothesis_mode'

    def test_detect_entry_mode_no_messages(self, agent, sample_state):
        """Should default to quick entry when no messages"""
        state = sample_state.copy()
        state['messages'] = []
        
        result = agent.detect_entry_mode_node(state)
        
        assert result['entry_mode'] == 'quick_entry'

    # =========================================================================
    # PICO Conversion Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_convert_quick_to_pico_success(self, agent, sample_state, sample_pico_data):
        """Should successfully convert quick entry to PICO"""
        state = sample_state.copy()
        state['input_text'] = 'Study of exercise effects on diabetes in adults over 12 months'
        
        # Mock LLM response
        agent.llm.invoke = AsyncMock(return_value={
            'content': json.dumps(sample_pico_data)
        })
        
        result = await agent.convert_quick_to_pico_node(state)
        
        assert 'pico_elements' in result
        assert result['pico_elements']['population'] == sample_pico_data['population']
        assert 'messages' in result
        assert 'PICO Extraction Complete' in result['current_output']

    @pytest.mark.asyncio
    async def test_convert_quick_to_pico_no_input(self, agent, sample_state):
        """Should handle missing input text"""
        state = sample_state.copy()
        # No input_text set
        
        result = await agent.convert_quick_to_pico_node(state)
        
        assert 'error' in result
        assert 'Missing input' in result['current_output']

    @pytest.mark.asyncio
    async def test_convert_quick_to_pico_extraction_failed(self, agent, sample_state):
        """Should handle LLM extraction failure"""
        state = sample_state.copy()
        state['input_text'] = 'Test research topic'
        
        # Mock LLM returning invalid JSON
        agent.llm.invoke = AsyncMock(return_value={
            'content': 'This is not valid JSON'
        })
        
        result = await agent.convert_quick_to_pico_node(state)
        
        assert 'error' in result
        assert 'Could not extract PICO' in result['current_output']

    # =========================================================================
    # PICO Validation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_validate_pico_success(self, agent, sample_state, sample_pico_data):
        """Should successfully validate complete PICO"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        
        result = await agent.validate_pico_node(state)
        
        assert result['pico_valid'] is True
        assert 'pico_quality' in result
        assert 'Quality Score' in result['current_output']
        assert 'PICO Elements:' in result['current_output']

    @pytest.mark.asyncio
    async def test_validate_pico_incomplete(self, agent, sample_state):
        """Should identify validation errors for incomplete PICO"""
        state = sample_state.copy()
        state['pico_elements'] = {
            'population': 'Adults',
            'intervention': 'X',  # Too short
            'comparator': '',     # Empty
            'outcomes': [],       # Empty list
            'timeframe': 'Soon'   # Vague
        }
        
        result = await agent.validate_pico_node(state)
        
        assert result['pico_valid'] is False
        assert 'pico_errors' in result
        assert len(result['pico_errors']) > 0

    @pytest.mark.asyncio
    async def test_validate_pico_missing(self, agent, sample_state):
        """Should handle missing PICO elements"""
        state = sample_state.copy()
        # No pico_elements set
        
        result = await agent.validate_pico_node(state)
        
        assert 'error' in result
        assert 'Missing PICO elements' in result['current_output']

    # =========================================================================
    # Hypothesis Generation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_hypothesis_success(self, agent, sample_state, sample_pico_data):
        """Should generate all hypothesis types"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        
        result = await agent.generate_hypothesis_node(state)
        
        assert 'hypotheses' in result
        assert 'null' in result['hypotheses']
        assert 'alternative' in result['hypotheses']
        assert 'comparative' in result['hypotheses']
        assert 'primary' in result['hypotheses']
        
        assert result['primary_hypothesis'] == result['hypotheses']['alternative']
        assert 'Primary Hypothesis' in result['current_output']

    @pytest.mark.asyncio
    async def test_generate_hypothesis_missing_pico(self, agent, sample_state):
        """Should handle missing PICO for hypothesis generation"""
        state = sample_state.copy()
        # No pico_elements set
        
        result = await agent.generate_hypothesis_node(state)
        
        assert 'error' in result
        assert 'Missing PICO elements' in result['current_output']

    # =========================================================================
    # Study Type Detection Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_detect_study_type_rct(self, agent, sample_state, sample_pico_data):
        """Should detect RCT when intervention is randomizable"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        state['hypotheses'] = {'primary': 'Test hypothesis'}
        state['input_text'] = 'Randomized trial of exercise intervention'
        
        # Mock LLM response recommending RCT
        agent.llm.invoke = AsyncMock(return_value={
            'content': 'Recommended: Randomized Controlled Trial (RCT) because the intervention can be randomly assigned and controlled.'
        })
        
        result = await agent.detect_study_type_node(state)
        
        assert result['study_type'] == 'randomized_controlled_trial'
        assert 'study_design_analysis' in result
        assert 'Recommended Design' in result['current_output']

    @pytest.mark.asyncio
    async def test_detect_study_type_cohort(self, agent, sample_state, sample_pico_data):
        """Should detect cohort study for observational research"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        state['hypotheses'] = {'primary': 'Test hypothesis'}
        state['input_text'] = 'Prospective cohort study following patients over time'
        
        # Mock LLM response recommending cohort
        agent.llm.invoke = AsyncMock(return_value={
            'content': 'Recommended: Prospective Cohort study to follow participants longitudinally and observe outcomes.'
        })
        
        result = await agent.detect_study_type_node(state)
        
        assert result['study_type'] == 'prospective_cohort'

    @pytest.mark.asyncio
    async def test_detect_study_type_missing_pico(self, agent, sample_state):
        """Should handle missing PICO for study type detection"""
        state = sample_state.copy()
        # No pico_elements set
        
        result = await agent.detect_study_type_node(state)
        
        assert 'error' in result
        assert 'Missing PICO elements' in result['current_output']

    # =========================================================================
    # Protocol Generation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_protocol_comprehensive(self, agent, sample_state, sample_pico_data):
        """Should generate comprehensive protocol outline"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        state['hypotheses'] = {'primary': 'Exercise will reduce HbA1c compared to standard care'}
        state['study_type'] = 'randomized_controlled_trial'
        state['study_design_analysis'] = 'RCT is appropriate for testing intervention'
        
        # Mock LLM response with protocol sections
        protocol_content = """
        ## 1. Study Summary
        Title: Exercise intervention in diabetes
        
        ## 2. Background and Rationale
        Current evidence supports...
        
        ## 3. Study Objectives and Hypotheses
        Primary objective: Test exercise effects
        
        ## 4. Study Design and Methods
        Randomized controlled trial design
        
        ## 5. Participant Selection
        Inclusion: Adults with diabetes
        
        ## 6. Interventions/Exposures
        Exercise program details
        
        ## 7. Outcome Measures
        Primary: HbA1c reduction
        
        ## 8. Statistical Analysis Plan
        Sample size and analysis methods
        
        ## 9. Data Management
        Data collection procedures
        
        ## 10. Ethical Considerations
        IRB and consent requirements
        """
        
        agent.llm.invoke = AsyncMock(return_value={
            'content': protocol_content
        })
        
        result = await agent.generate_protocol_outline_node(state)
        
        assert 'protocol_outline' in result
        assert 'final_output' in result
        assert 'messages' in result
        assert '## 1. Study Summary' in result['final_output']
        assert 'PICO Framework Summary' in result['final_output']
        assert 'Next Steps' in result['final_output']

    @pytest.mark.asyncio
    async def test_generate_protocol_missing_pico(self, agent, sample_state):
        """Should handle missing PICO for protocol generation"""
        state = sample_state.copy()
        # No pico_elements set
        
        result = await agent.generate_protocol_outline_node(state)
        
        assert 'error' in result
        assert 'Missing PICO elements' in result['current_output']

    # =========================================================================
    # Improvement Node Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_improve_node_with_feedback(self, agent, sample_state):
        """Should improve protocol based on feedback"""
        state = sample_state.copy()
        state['feedback'] = 'Protocol needs more statistical detail'
        state['current_output'] = 'Basic protocol outline'
        state['gate_result'] = {
            'score': 0.6,
            'criteria_failed': ['protocol_sections', 'min_protocol_length'],
            'reason': 'Insufficient detail'
        }
        state['pico_elements'] = {'population': 'Adults', 'intervention': 'Exercise', 'comparator': 'Control', 'outcomes': ['HbA1c'], 'timeframe': '6 months'}
        
        # Mock LLM improvement response
        agent.llm.invoke = AsyncMock(return_value={
            'content': 'Improved protocol with enhanced statistical methods section and detailed methodology...'
        })
        
        result = await agent.improve_node(state)
        
        assert 'current_output' in result
        assert result['feedback'] is None  # Should clear feedback
        assert result['iteration_improved'] is True
        assert 'Improved protocol' in result['current_output']

    # =========================================================================
    # Quality Criteria Evaluation Tests
    # =========================================================================

    def test_evaluate_criterion_pico_complete_valid(self, agent, sample_state, sample_pico_data):
        """Should pass PICO completeness check for valid PICO"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        
        passed, score = agent._evaluate_criterion('pico_complete', True, '', state)
        
        assert passed is True
        assert score == 1.0

    def test_evaluate_criterion_pico_complete_invalid(self, agent, sample_state):
        """Should fail PICO completeness check for missing PICO"""
        state = sample_state.copy()
        state['pico_elements'] = {
            'population': 'Adults',
            'intervention': '',  # Empty
            'comparator': '',    # Empty
            'outcomes': [],      # Empty
            'timeframe': ''      # Empty
        }
        
        passed, score = agent._evaluate_criterion('pico_complete', True, '', state)
        
        assert passed is False
        assert score == 0.3  # Partial score for invalid PICO

    def test_evaluate_criterion_pico_quality_score(self, agent, sample_state):
        """Should evaluate PICO quality score correctly"""
        state = sample_state.copy()
        state['pico_quality'] = {'score': 85.0}  # Above threshold
        
        passed, score = agent._evaluate_criterion('pico_quality_score', 70.0, '', state)
        
        assert passed is True
        assert score == 0.85  # Normalized score

    def test_evaluate_criterion_hypothesis_generated(self, agent, sample_state):
        """Should check if hypothesis was generated"""
        state = sample_state.copy()
        state['hypotheses'] = {'primary': 'Test hypothesis'}
        
        passed, score = agent._evaluate_criterion('hypothesis_generated', True, '', state)
        
        assert passed is True
        assert score == 1.0

    def test_evaluate_criterion_protocol_sections(self, agent, sample_state):
        """Should count protocol sections correctly"""
        output_with_sections = """
        ## 1. Summary
        Content here
        ## 2. Background  
        Content here
        ## 3. Methods
        Content here
        ## 4. Analysis
        Content here
        ## 5. Ethics
        Content here
        ## 6. Timeline
        Content here
        ## 7. Budget
        Content here
        ## 8. Additional
        Content here
        """
        
        passed, score = agent._evaluate_criterion('protocol_sections', 7, output_with_sections, sample_state)
        
        assert passed is True
        assert score >= 1.0  # Should have enough sections

    def test_evaluate_criterion_phi_compliant(self, agent, sample_state):
        """Should detect PHI violations"""
        output_with_phi = "Patient's SSN is 123-45-6789 and date of birth is 01/01/1990"
        
        passed, score = agent._evaluate_criterion('phi_compliant', True, output_with_phi, sample_state)
        
        assert passed is False
        assert score == 0.0

    # =========================================================================
    # Integration and End-to-End Tests
    # =========================================================================

    def test_get_stage_output_for_next_stages(self, agent, sample_state, sample_pico_data):
        """Should prepare output for subsequent stages"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        state['hypotheses'] = {'primary': 'Test hypothesis'}
        state['study_type'] = 'randomized_controlled_trial'
        state['protocol_outline'] = 'Detailed protocol...'
        
        output = agent.get_stage_output_for_next_stages(state)
        
        # Check required fields for Stage 2 & 3
        assert 'pico_elements' in output
        assert 'hypotheses' in output
        assert 'study_type' in output
        assert 'protocol_outline' in output
        assert 'search_query' in output
        assert 'stage_1_complete' in output
        assert output['stage_1_complete'] is True
        assert output['agent_id'] == 'protocol_design'

    def test_generate_search_query(self, agent, sample_state, sample_pico_data):
        """Should generate search query from PICO for Stage 2"""
        state = sample_state.copy()
        state['pico_elements'] = sample_pico_data
        
        search_query = agent._generate_search_query(state)
        
        assert search_query != ""
        assert "Adults aged 40-65 with Type 2 diabetes" in search_query
        assert "AND" in search_query  # Boolean format
        assert "OR" in search_query   # For multiple outcomes

    @pytest.mark.asyncio
    async def test_full_agent_invoke_demo_mode(self, agent, mock_llm_bridge):
        """Integration test: full agent execution in DEMO mode"""
        # Mock all LLM calls for a complete flow
        mock_responses = [
            # PICO extraction response
            json.dumps({
                'population': 'Adults with Type 2 diabetes',
                'intervention': 'Exercise program',
                'comparator': 'Standard care',
                'outcomes': ['HbA1c reduction'],
                'timeframe': '6 months'
            }),
            # Study type detection response
            'Recommended: Randomized Controlled Trial (RCT) for testing exercise intervention.',
            # Protocol generation response
            '''## 1. Study Summary
            Exercise RCT in diabetes
            ## 2. Background
            Literature supports exercise
            ## 3. Methods
            RCT design with 6-month follow-up
            ## 4. Analysis
            Statistical analysis plan
            ## 5. Ethics
            IRB approval required
            ## 6. Timeline
            12-month study timeline
            ## 7. Budget
            Resource requirements'''
        ]
        
        mock_llm_bridge.invoke.side_effect = [
            {'content': response} for response in mock_responses
        ]
        
        # Execute agent
        result = await agent.invoke(
            project_id='test-project',
            initial_message='I want to study exercise effects on diabetes in adults',
            governance_mode='DEMO',
        )
        
        # Verify completion
        assert result['current_stage'] == 1
        assert 'pico_elements' in result
        assert 'protocol_outline' in result
        assert result.get('gate_status') in ['passed', 'needs_human', 'failed']  # Should complete quality gate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])