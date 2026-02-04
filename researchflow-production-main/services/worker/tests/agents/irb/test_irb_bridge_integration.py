"""
IRB Agent + AI Router Bridge Integration Test

Tests the integration between the IRB agent and AI Router Bridge.
This test verifies that the LangGraph implementation works with the bridge
without needing a running orchestrator service.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from src.bridges.ai_router_bridge import (
        AIRouterBridge, ModelOptions, LLMResponse, 
        TokenUsage, CostBreakdown, ModelTier, GovernanceMode
    )
    from src.agents.irb.agent import IRBAgent
    from src.agents.base.state import create_initial_state
    from langgraph.checkpoint.memory import MemorySaver
    BRIDGE_AVAILABLE = True
except ImportError as e:
    print(f"Bridge/Agent not available: {e}")
    BRIDGE_AVAILABLE = False


class MockAIRouterBridge:
    """Mock AI Router Bridge for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.connected = False
        self.responses = {
            "risk_assessment": "Comprehensive risk assessment: Minimal risk study with appropriate safeguards.",
            "phi_detection": "PHI assessment: No PHI involved in this observational study.",
            "irb_protocol": "Complete IRB protocol with all required sections including objectives, procedures, and risk mitigation.",
            "consent_form": "Informed consent form with all required elements for voluntary participation.",
            "irb_compliance": "Regulatory compliance review complete: Ready for IRB submission."
        }
    
    async def connect(self):
        """Mock connect"""
        self.connected = True
    
    async def close(self):
        """Mock close"""
        self.connected = False
    
    async def invoke(self, prompt: str, options: ModelOptions) -> LLMResponse:
        """Mock LLM invocation"""
        self.call_count += 1
        
        # Get appropriate response based on task type
        content = self.responses.get(options.task_type, f"Mock response for {options.task_type}: {prompt[:50]}...")
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                total_tokens=150,
                prompt_tokens=100, 
                completion_tokens=50
            ),
            cost=CostBreakdown(
                total=0.01,
                input=0.005,
                output=0.005
            ),
            model="claude-3-5-sonnet-20241022",
            tier=options.model_tier.value if options.model_tier else "STANDARD",
            finish_reason="stop",
            metadata={"mock": True}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check"""
        return {
            "status": "healthy",
            "orchestrator_reachable": True,
            "ai_router_available": True,
            "latency_ms": 10
        }
    
    def get_cost_stats(self) -> Dict[str, float]:
        """Mock cost stats"""
        return {
            "total_cost": self.call_count * 0.01,
            "request_count": self.call_count,
            "average_cost_per_request": 0.01
        }


@pytest.mark.skipif(not BRIDGE_AVAILABLE, reason="Bridge/Agent not available")
class TestIRBAgentBridgeIntegration:
    """Test IRB Agent with AI Router Bridge"""

    @pytest.fixture
    def mock_bridge(self):
        """Create mock bridge"""
        return MockAIRouterBridge()

    @pytest.fixture
    async def irb_agent(self, mock_bridge):
        """Create IRB agent with mock bridge"""
        agent = IRBAgent(
            llm_bridge=mock_bridge,
            checkpointer=MemorySaver()
        )
        return agent

    @pytest.fixture
    def test_state(self):
        """Create test state"""
        return create_initial_state(
            agent_id='irb',
            project_id='test-project',
            run_id='test-run-123',
            thread_id='test-thread-456',
            stage_range=(13, 14),
            governance_mode='DEMO',
            input_artifact_ids=[],
            max_iterations=3,
        )

    def test_irb_agent_initialization_with_bridge(self, irb_agent, mock_bridge):
        """Test IRB agent initializes with bridge"""
        assert irb_agent.llm == mock_bridge
        assert irb_agent.agent_id == 'irb'
        assert irb_agent.stages == [13, 14]
    
    @pytest.mark.asyncio
    async def test_bridge_health_check(self, mock_bridge):
        """Test bridge health check"""
        health = await mock_bridge.health_check()
        assert health["status"] == "healthy"
        assert health["orchestrator_reachable"] is True
    
    @pytest.mark.asyncio
    async def test_bridge_llm_call(self, mock_bridge):
        """Test basic LLM call through bridge"""
        options = ModelOptions(
            task_type="risk_assessment",
            model_tier=ModelTier.STANDARD,
            governance_mode=GovernanceMode.DEMO
        )
        
        response = await mock_bridge.invoke("Test prompt", options)
        
        assert response.content.startswith("Comprehensive risk assessment")
        assert response.usage.total_tokens == 150
        assert response.cost.total == 0.01
        assert response.tier == "STANDARD"
        assert mock_bridge.call_count == 1
    
    @pytest.mark.asyncio
    async def test_irb_agent_call_llm_method(self, irb_agent, test_state):
        """Test IRB agent's call_llm method"""
        response_content = await irb_agent.call_llm(
            prompt="Assess risks for research study",
            task_type="risk_assessment",
            state=test_state,
            model_tier="STANDARD"
        )
        
        assert isinstance(response_content, str)
        assert len(response_content) > 0
        assert "risk assessment" in response_content.lower()
        
        # Check token count was updated in state
        assert test_state['token_count'] == 150
    
    @pytest.mark.asyncio
    async def test_irb_risk_assessment_node(self, irb_agent, test_state, mock_bridge):
        """Test risk assessment node execution"""
        test_state['messages'] = [{
            'role': 'user',
            'content': 'Please assess risks for a sleep study with college students.'
        }]
        
        result = await irb_agent.assess_risk_node(test_state)
        
        assert 'current_stage' in result
        assert result['current_stage'] == 13
        assert 'risk_result' in result
        assert 'current_output' in result
        assert len(result['risk_result']) > 0
        assert mock_bridge.call_count >= 1
    
    @pytest.mark.asyncio  
    async def test_irb_phi_detection_node(self, irb_agent, test_state, mock_bridge):
        """Test PHI detection node"""
        test_state['risk_result'] = "Low risk assessment completed"
        
        result = await irb_agent.check_phi_node(test_state)
        
        assert 'phi_result' in result
        assert 'current_output' in result
        assert len(result['phi_result']) > 0
        assert mock_bridge.call_count >= 1

    @pytest.mark.asyncio
    async def test_irb_protocol_generation_node(self, irb_agent, test_state, mock_bridge):
        """Test protocol generation"""
        test_state['risk_result'] = "Risk assessment complete"
        test_state['phi_result'] = "No PHI detected"
        test_state['messages'] = [{
            'role': 'user',
            'content': 'Generate IRB protocol for academic study'
        }]
        
        result = await irb_agent.generate_protocol_node(test_state)
        
        assert 'protocol_result' in result
        assert 'current_stage' in result
        assert result['current_stage'] == 13
        assert len(result['protocol_result']) > 0
        assert "protocol" in result['protocol_result'].lower()
        assert mock_bridge.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_irb_consent_creation_node(self, irb_agent, test_state, mock_bridge):
        """Test consent form creation"""
        test_state['protocol_result'] = "Complete protocol document"
        test_state['risk_result'] = "Minimal risk study"
        
        result = await irb_agent.create_consent_node(test_state)
        
        assert 'consent_result' in result
        assert 'current_stage' in result
        assert result['current_stage'] == 14
        assert len(result['consent_result']) > 0
        assert "consent" in result['consent_result'].lower()
        assert mock_bridge.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_irb_compliance_review_node(self, irb_agent, test_state, mock_bridge):
        """Test compliance review"""
        test_state['protocol_result'] = "Protocol complete"
        test_state['consent_result'] = "Consent form complete"
        test_state['phi_result'] = "No PHI issues"
        
        result = await irb_agent.review_compliance_node(test_state)
        
        assert 'compliance_result' in result
        assert 'current_output' in result
        assert len(result['compliance_result']) > 0
        assert "compliance" in result['compliance_result'].lower()
        assert mock_bridge.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_irb_human_review_node(self, irb_agent, test_state):
        """Test mandatory human review"""
        test_state.update({
            'protocol_result': 'Complete protocol',
            'consent_result': 'Complete consent form',
            'compliance_result': 'All requirements met',
            'risk_result': 'Low risk assessment'
        })
        
        result = await irb_agent.human_review_node(test_state)
        
        assert result['human_review_required'] is True
        assert result['gate_status'] == 'needs_human'
        assert 'review_summary' in result
        assert 'HUMAN APPROVAL MANDATORY' in result['review_summary']
    
    def test_irb_quality_gate_evaluation(self, irb_agent, test_state):
        """Test quality gate with IRB-specific criteria"""
        test_state['current_output'] = """
        Complete risk assessment with minimal risk determination.
        PHI protection measures documented and compliant.
        Informed consent includes voluntary participation, risks, benefits, 
        confidentiality protections, and withdrawal procedures.
        Full protocol with objectives, procedures, and safeguards.
        No vulnerable populations involved.
        """
        
        result = irb_agent.quality_gate_node(test_state)
        
        assert 'gate_status' in result
        assert 'gate_score' in result
        assert 'gate_result' in result
        
        gate_result = result['gate_result']
        
        # Should pass most criteria except human_reviewed
        expected_criteria = ['risk_assessed', 'phi_addressed', 'consent_complete', 'protocol_complete']
        for criterion in expected_criteria:
            assert criterion in gate_result['criteria_met']
        
        # Human review should be required
        assert 'human_reviewed' in gate_result['criteria_failed']
    
    def test_governance_mode_handling(self, irb_agent, test_state):
        """Test different governance modes"""
        # Test DEMO mode
        test_state['governance_mode'] = 'DEMO'
        result = irb_agent.should_require_human_review(test_state)
        assert result == 'human_review'  # IRB always requires human review
        
        # Test LIVE mode
        test_state['governance_mode'] = 'LIVE'  
        result = irb_agent.should_require_human_review(test_state)
        assert result == 'human_review'  # IRB always requires human review

    @pytest.mark.asyncio
    async def test_cost_tracking(self, mock_bridge):
        """Test cost tracking functionality"""
        initial_stats = mock_bridge.get_cost_stats()
        assert initial_stats['request_count'] == 0
        
        # Make some calls
        options = ModelOptions(task_type="general")
        await mock_bridge.invoke("Test 1", options)
        await mock_bridge.invoke("Test 2", options) 
        
        final_stats = mock_bridge.get_cost_stats()
        assert final_stats['request_count'] == 2
        assert final_stats['total_cost'] == 0.02
        assert final_stats['average_cost_per_request'] == 0.01


@pytest.mark.skipif(not BRIDGE_AVAILABLE, reason="Bridge/Agent not available")
class TestBridgeErrorHandling:
    """Test error handling in bridge integration"""

    @pytest.fixture
    def failing_bridge(self):
        """Create bridge that simulates failures"""
        bridge = Mock()
        bridge.invoke = AsyncMock(side_effect=Exception("Connection failed"))
        bridge.connect = AsyncMock()
        bridge.close = AsyncMock()
        return bridge

    @pytest.fixture 
    async def irb_agent_with_failing_bridge(self, failing_bridge):
        """IRB agent with failing bridge"""
        return IRBAgent(
            llm_bridge=failing_bridge,
            checkpointer=MemorySaver()
        )

    @pytest.mark.asyncio
    async def test_bridge_failure_handling(self, irb_agent_with_failing_bridge, failing_bridge):
        """Test handling of bridge failures"""
        test_state = create_initial_state(
            agent_id='irb',
            project_id='test',
            run_id='test',
            thread_id='test',
            stage_range=(13, 14),
        )
        
        # This should raise an exception when trying to call LLM
        with pytest.raises(Exception):
            await irb_agent_with_failing_bridge.call_llm(
                prompt="test",
                task_type="general",
                state=test_state
            )


def test_bridge_imports():
    """Test that bridge imports work correctly"""
    try:
        from src.bridges.ai_router_bridge import AIRouterBridge, ModelOptions
        print("✅ Bridge imports successful")
    except ImportError as e:
        pytest.fail(f"Bridge import failed: {e}")


if __name__ == "__main__":
    # Basic verification
    print("🧪 IRB Agent + Bridge Integration Test")
    print("=" * 50)
    
    if not BRIDGE_AVAILABLE:
        print("❌ Bridge/Agent not available")
        exit(1)
    
    # Test imports
    test_bridge_imports()
    
    # Test basic functionality
    async def basic_test():
        mock_bridge = MockAIRouterBridge()
        
        # Test bridge functionality
        health = await mock_bridge.health_check()
        assert health["status"] == "healthy"
        
        # Test agent creation
        agent = IRBAgent(llm_bridge=mock_bridge, checkpointer=MemorySaver())
        assert agent.agent_id == 'irb'
        
        print("✅ Basic IRB Agent + Bridge integration working")
    
    try:
        asyncio.run(basic_test())
        print("\n🎯 Integration test ready! Run with pytest:")
        print("pytest services/worker/tests/agents/irb/test_irb_bridge_integration.py -v")
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        exit(1)