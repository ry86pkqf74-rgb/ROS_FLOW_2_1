"""
Integration tests for PICO pipeline flow between stages.

Tests the flow of PICO elements from Stage 1 Protocol Design Agent 
to Stage 2 Literature and Stage 3 IRB, ensuring proper integration.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

# Import test utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "worker"))

from src.agents.protocol_design.agent import ProtocolDesignAgent
from src.agents.common.pico import PICOElements
from src.agents.base.state import AgentState, create_initial_state


class TestPICOPipelineIntegration:
    """Integration tests for PICO pipeline across stages"""
    
    @pytest.fixture
    def mock_llm_bridge(self):
        """Mock LLM bridge for testing"""
        bridge = AsyncMock()
        bridge.invoke = AsyncMock()
        return bridge
    
    @pytest.fixture
    def protocol_agent(self, mock_llm_bridge):
        """Create ProtocolDesignAgent instance"""
        return ProtocolDesignAgent(llm_bridge=mock_llm_bridge)
    
    @pytest.fixture
    def sample_pico_data(self) -> Dict[str, Any]:
        """Sample PICO elements for testing"""
        return {
            'population': 'Adults aged 40-65 with Type 2 diabetes and HbA1c > 7.5%',
            'intervention': 'Structured exercise program (150 minutes/week, moderate intensity)',
            'comparator': 'Standard diabetes care without structured exercise',
            'outcomes': ['HbA1c reduction', 'Weight loss', 'Cardiovascular events'],
            'timeframe': '12 months follow-up'
        }
    
    @pytest.fixture
    def mock_stage_context(self):
        """Mock stage context with PICO output from Stage 1"""
        context = MagicMock()
        context.config = {}
        context.governance_mode = 'DEMO'
        context.job_id = 'test-job-123'
        context.artifact_path = '/tmp/test-artifacts'
        return context

    # =========================================================================
    # Protocol Design Agent Output Tests
    # =========================================================================

    def test_protocol_agent_stage_output_format(self, protocol_agent, sample_pico_data):
        """Should generate properly formatted output for subsequent stages"""
        # Create mock state with completed protocol design
        state = {
            'pico_elements': sample_pico_data,
            'hypotheses': {
                'primary': 'Exercise will significantly reduce HbA1c compared to standard care',
                'null': 'Exercise will show no difference from standard care',
                'alternative': 'Exercise will significantly improve glycemic control'
            },
            'study_type': 'randomized_controlled_trial',
            'protocol_outline': 'Comprehensive protocol with 10 sections...',
        }
        
        output = protocol_agent.get_stage_output_for_next_stages(state)
        
        # Verify all required fields for Stage 2 & 3
        required_fields = [
            'pico_elements', 'hypotheses', 'primary_hypothesis', 
            'study_type', 'protocol_outline', 'search_query', 
            'stage_1_complete', 'agent_id'
        ]
        
        for field in required_fields:
            assert field in output, f"Missing required field: {field}"
        
        # Verify specific values
        assert output['stage_1_complete'] is True
        assert output['agent_id'] == 'protocol_design'
        assert output['pico_elements'] == sample_pico_data
        assert 'search_query' in output and output['search_query'] != ""

    def test_search_query_generation_from_pico(self, protocol_agent, sample_pico_data):
        """Should generate valid search query from PICO elements"""
        state = {'pico_elements': sample_pico_data}
        
        search_query = protocol_agent._generate_search_query(state)
        
        # Verify Boolean query format
        assert search_query != ""
        assert "AND" in search_query  # Boolean operators
        assert "Adults aged 40-65 with Type 2 diabetes" in search_query
        assert "Structured exercise program" in search_query
        assert "Standard diabetes care" in search_query
        
        # Verify multiple outcomes handled with OR
        assert "OR" in search_query or len(sample_pico_data['outcomes']) == 1

    # =========================================================================
    # Stage 2 Literature Integration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_stage2_enhanced_pico_integration(self, mock_stage_context, sample_pico_data):
        """Stage 2 should use enhanced PICO integration from new Stage 1 agent"""
        # Import Stage 2 agent
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        # Mock enhanced Stage 1 output with complete PICO data
        stage1_output = {
            'pico_elements': sample_pico_data,
            'search_query': '(Adults aged 40-65 with Type 2 diabetes) AND (Structured exercise program) AND (Standard diabetes care) AND ((HbA1c reduction) OR (Weight loss))',
            'study_type': 'randomized_controlled_trial',
            'primary_hypothesis': 'Exercise will significantly reduce HbA1c compared to standard care',
            'stage_1_complete': True,
            'agent_id': 'protocol_design',
            'quality_score': 85.0
        }
        
        # Mock context to return Stage 1 output
        mock_stage_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        
        # Create Stage 2 agent
        agent = LiteratureScoutAgent()
        
        # Extract search config
        search_config = agent._extract_search_config(mock_stage_context)
        
        # Verify enhanced PICO integration
        assert 'pico_elements' in search_config
        assert 'pico_search_query' in search_config
        assert search_config['pico_search_query'] == stage1_output['search_query']
        assert search_config['detected_study_type'] == 'randomized_controlled_trial'
        assert search_config['primary_hypothesis'] == stage1_output['primary_hypothesis']
        assert search_config['stage1_complete'] is True
        assert search_config['pico_driven_search'] is True
        
        # Verify PICO-derived keywords include all components
        expected_keywords = [
            'Adults aged 40-65 with Type 2 diabetes and HbA1c > 7.5%',
            'Structured exercise program (150 minutes/week, moderate intensity)',
            'Standard diabetes care without structured exercise',
            '12 months follow-up',
            'HbA1c reduction',
            'Weight loss', 
            'Cardiovascular events'
        ]
        
        # All PICO components should be in keywords
        for keyword in expected_keywords:
            assert keyword in search_config['keywords']
        
        # Test enhanced PubMed query with study type filters
        pubmed_query = agent._build_pubmed_query(search_config)
        assert 'Randomized Controlled Trial[pt]' in pubmed_query
        assert search_config['pico_search_query'] in pubmed_query

    def test_stage2_build_pubmed_query_with_pico(self, mock_stage_context):
        """Stage 2 should use PICO search query for PubMed"""
        # Import Stage 2 agent
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        agent = LiteratureScoutAgent()
        
        # Search config with PICO query
        search_config = {
            'pico_search_query': '(diabetes patients) AND (exercise intervention) AND (standard care) AND ((HbA1c) OR (glucose))',
            'keywords': ['diabetes', 'exercise'],  # Fallback
            'study_types': ['rct']
        }
        
        query = agent._build_pubmed_query(search_config)
        
        # Should use enhanced PICO query with study type filters
        assert search_config['pico_search_query'] in query
        # Should include study type filter for RCT
        assert 'Randomized Controlled Trial[pt]' in query
    
    def test_stage2_fallback_without_pico(self, mock_stage_context):
        """Stage 2 should fallback to keyword search without PICO"""
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        agent = LiteratureScoutAgent()
        
        # Search config without PICO
        search_config = {
            'keywords': ['diabetes', 'exercise'],
            'study_types': ['rct']
        }
        
        query = agent._build_pubmed_query(search_config)
        
        # Should use keyword-based query
        assert '"diabetes"' in query
        assert '"exercise"' in query
        assert 'AND' in query

    # =========================================================================
    # Stage 3 IRB Integration Tests  
    # =========================================================================

    def test_stage3_enhanced_pico_integration(self, mock_stage_context, sample_pico_data):
        """Stage 3 should use enhanced PICO integration from new Stage 1 agent"""
        # Import Stage 3 agent
        from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
        
        # Mock comprehensive Stage 1 output with PICO and protocol data
        stage1_output = {
            'pico_elements': sample_pico_data,
            'primary_hypothesis': 'In adults aged 40-65 with Type 2 diabetes, structured exercise program compared to standard care will significantly reduce HbA1c over 12 months',
            'hypotheses': {
                'primary': 'Exercise will reduce HbA1c significantly',
                'null': 'Exercise will show no difference',
                'alternative': 'Exercise will improve glycemic control'
            },
            'study_type': 'randomized_controlled_trial',
            'study_design_analysis': 'RCT is appropriate for testing intervention effects with randomized assignment',
            'stage_1_complete': True,
            'agent_id': 'protocol_design'
        }
        
        # Mock context
        mock_stage_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        mock_stage_context.config = {}  # Empty config to force PICO usage
        
        # Create Stage 3 agent
        agent = IRBDraftingAgent()
        
        # Test comprehensive IRB data extraction
        irb_data = agent._extract_irb_data(mock_stage_context)
        
        # Verify enhanced PICO integration
        assert irb_data['hypothesis'] == stage1_output['primary_hypothesis']
        assert irb_data['population'] == sample_pico_data['population']
        assert irb_data['variables'] == sample_pico_data['outcomes']
        assert irb_data['studyType'] == 'clinical_trial'  # Mapped from RCT
        
        # Verify PICO metadata inclusion
        assert irb_data['picoElements'] == sample_pico_data
        assert irb_data['studyDesignAnalysis'] == stage1_output['study_design_analysis']
        assert irb_data['stage1Complete'] is True
        
        # Verify enhanced analysis approach
        assert 'randomized controlled trial' in irb_data['analysisApproach'].lower() or 'clinical trial' in irb_data['analysisApproach'].lower()

    def test_stage3_uses_pico_population(self, mock_stage_context, sample_pico_data):
        """Stage 3 should use PICO population for IRB protocol"""
        from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
        
        # Mock Stage 1 output with PICO
        stage1_output = {'pico_elements': sample_pico_data}
        mock_stage_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        
        agent = IRBDraftingAgent()
        population = agent._extract_population_from_stages(mock_stage_context)
        
        assert population == sample_pico_data['population']

    def test_stage3_irb_data_extraction_with_pico(self, mock_stage_context, sample_pico_data):
        """Stage 3 should extract complete IRB data using PICO elements"""
        from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
        
        # Mock complete Stage 1 output
        stage1_output = {
            'pico_elements': sample_pico_data,
            'primary_hypothesis': 'Exercise intervention will significantly reduce HbA1c in diabetic adults',
            'study_type': 'randomized_controlled_trial'
        }
        
        mock_stage_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        mock_stage_context.config = {}  # Empty config to force PICO usage
        
        agent = IRBDraftingAgent()
        irb_data = agent._extract_irb_data(mock_stage_context)
        
        # Verify PICO elements were used
        assert irb_data['hypothesis'] == stage1_output['primary_hypothesis']
        assert irb_data['population'] == sample_pico_data['population']
        assert irb_data['variables'] == sample_pico_data['outcomes']
        assert irb_data['studyType'] == 'clinical_trial'  # Mapped from RCT

    # =========================================================================
    # End-to-End Pipeline Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_full_pico_pipeline_stage1_to_stage2(self, protocol_agent, mock_llm_bridge, sample_pico_data):
        """Test complete PICO flow from Stage 1 to Stage 2"""
        
        # Mock Stage 1 execution with PICO extraction
        mock_llm_bridge.invoke.side_effect = [
            # PICO extraction response
            {'content': json.dumps(sample_pico_data)},
            # Study type detection
            {'content': 'Recommended: Randomized Controlled Trial (RCT)'},
            # Protocol generation  
            {'content': '## 1. Study Summary\nComprehensive RCT protocol\n## 2. Background\nLiterature review\n## 3. Methods\nRandomization protocol\n## 4. Analysis\nStatistical methods\n## 5. Ethics\nIRB requirements\n## 6. Timeline\nStudy schedule\n## 7. Budget\nResource planning'}
        ]
        
        # Execute Stage 1
        stage1_result = await protocol_agent.invoke(
            project_id='test-project',
            initial_message='Study exercise effects on diabetes in adults',
            governance_mode='DEMO'
        )
        
        # Get output for Stage 2
        stage1_output = protocol_agent.get_stage_output_for_next_stages(stage1_result)
        
        # Enhanced Stage 1 output verification
        assert stage1_output['stage_1_complete'] is True
        assert 'pico_elements' in stage1_output
        assert 'search_query' in stage1_output
        assert stage1_output['search_query'] != ""
        assert 'study_type' in stage1_output
        assert 'primary_hypothesis' in stage1_output
        assert stage1_output['agent_id'] == 'protocol_design'
        
        # Verify PICO completeness
        pico_elements = stage1_output['pico_elements']
        required_pico_fields = ['population', 'intervention', 'comparator', 'outcomes', 'timeframe']
        for field in required_pico_fields:
            assert field in pico_elements, f"Missing PICO field: {field}"
            assert pico_elements[field], f"Empty PICO field: {field}"
        
        # Mock Stage 2 context using Stage 1 output
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        # Create mock context that returns Stage 1 output
        stage2_context = MagicMock()
        stage2_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        stage2_context.config = {}
        
        stage2_agent = LiteratureScoutAgent()
        search_config = stage2_agent._extract_search_config(stage2_context)
        
        # Enhanced Stage 2 integration verification
        assert 'pico_elements' in search_config
        assert search_config['pico_elements'] == sample_pico_data
        assert 'pico_search_query' in search_config
        assert search_config['pico_search_query'] != ""
        assert search_config['stage1_complete'] is True
        assert search_config['pico_driven_search'] is True
        assert search_config['detected_study_type'] == stage1_output['study_type']
        assert search_config['primary_hypothesis'] == stage1_output['primary_hypothesis']
        
        # Test PubMed query generation with PICO
        pubmed_query = stage2_agent._build_pubmed_query(search_config)
        
        # Should use PICO query, not fallback
        assert 'clinical trial' != pubmed_query  # Should not be fallback
        assert len(pubmed_query) > 20  # Should be substantial PICO-based query

    def test_pico_data_consistency_across_stages(self, sample_pico_data):
        """Verify PICO data remains consistent across stage transformations"""
        
        # Test PICO -> Search Query -> Keywords transformation
        from src.agents.common.pico import PICOElements, PICOValidator
        
        pico = PICOElements(**sample_pico_data)
        
        # Generate search query
        search_query = PICOValidator.to_search_query(pico, use_boolean=True)
        
        # Verify all PICO components appear in search query
        assert sample_pico_data['population'] in search_query
        assert sample_pico_data['intervention'] in search_query
        assert sample_pico_data['comparator'] in search_query
        
        # Verify outcomes are joined with OR
        for outcome in sample_pico_data['outcomes']:
            assert outcome in search_query
        
        # Test hypothesis generation
        hypothesis = PICOValidator.to_hypothesis(pico, style="alternative")
        
        # Verify hypothesis contains key PICO elements
        assert any(word in hypothesis.lower() for word in ['adults', 'diabetes', 'diabetic'])
        assert any(word in hypothesis.lower() for word in ['exercise', 'program'])
        assert any(word in hypothesis.lower() for word in ['standard', 'care'])
        assert 'months' in hypothesis.lower()

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    def test_stage2_graceful_degradation_without_pico(self, mock_stage_context):
        """Stage 2 should gracefully handle missing PICO data"""
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        # Mock empty Stage 1 output
        mock_stage_context.get_prior_stage_output = MagicMock(return_value={})
        mock_stage_context.config = {
            'studyTitle': 'Test Study',
            'keywords': ['test', 'study']
        }
        
        agent = LiteratureScoutAgent()
        search_config = agent._extract_search_config(mock_stage_context)
        
        # Should fallback to config values
        assert search_config['research_topic'] == 'Test Study'
        assert search_config['keywords'] == ['test', 'study']
        assert search_config.get('pico_search_query', '') == ''

    def test_stage3_graceful_degradation_without_pico(self, mock_stage_context):
        """Stage 3 should gracefully handle missing PICO data"""
        from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
        
        # Mock empty Stage 1 output
        mock_stage_context.get_prior_stage_output = MagicMock(return_value={})
        mock_stage_context.config = {
            'irb': {
                'studyTitle': 'Test Study',
                'principalInvestigator': 'Dr. Test',
                'hypothesis': 'Test hypothesis'
            }
        }
        
        agent = IRBDraftingAgent()
        irb_data = agent._extract_irb_data(mock_stage_context)
        
        # Should use config values when PICO unavailable
        assert irb_data['studyTitle'] == 'Test Study'
        assert irb_data['principalInvestigator'] == 'Dr. Test'
        assert irb_data['hypothesis'] == 'Test hypothesis'

    def test_invalid_pico_elements_handling(self, mock_stage_context):
        """Stages should handle invalid/incomplete PICO elements gracefully"""
        from src.workflow_engine.stages.stage_02_literature import LiteratureScoutAgent
        
        # Mock Stage 1 output with invalid PICO
        stage1_output = {
            'pico_elements': {
                'population': '',  # Empty
                'intervention': 'Test',
                # Missing other required fields
            }
        }
        
        mock_stage_context.get_prior_stage_output = MagicMock(return_value=stage1_output)
        mock_stage_context.config = {}
        
        agent = LiteratureScoutAgent()
        
        # Should not crash, should fallback gracefully
        try:
            search_config = agent._extract_search_config(mock_stage_context)
            # Should have empty/fallback values
            assert isinstance(search_config, dict)
        except Exception as e:
            pytest.fail(f"Stage 2 should handle invalid PICO gracefully, but failed with: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])