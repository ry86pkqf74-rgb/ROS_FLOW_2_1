"""
Minimal IRB Agent + Bridge Integration Test

This test focuses specifically on the LangGraph + AI Router Bridge integration
without importing the complex agent hierarchy.
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

try:
    # Test LangGraph availability
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"LangGraph not available: {e}")
    LANGGRAPH_AVAILABLE = False

try:
    # Test bridge availability (standalone)
    from src.bridges.ai_router_bridge import (
        AIRouterBridge, ModelOptions, LLMResponse,
        TokenUsage, CostBreakdown, ModelTier, GovernanceMode
    )
    BRIDGE_AVAILABLE = True
except ImportError as e:
    print(f"AI Router Bridge not available: {e}")
    BRIDGE_AVAILABLE = False


# Define minimal state for testing
from typing import TypedDict, List, Annotated
import operator

class IRBState(TypedDict):
    """Minimal IRB agent state for testing"""
    agent_id: str
    messages: Annotated[List[str], operator.add]
    current_stage: int
    current_output: str
    risk_result: str
    phi_result: str
    protocol_result: str
    consent_result: str
    compliance_result: str
    token_count: int
    governance_mode: str


class MockAIRouterBridge:
    """Mock bridge for testing without orchestrator"""
    
    def __init__(self):
        self.call_count = 0
        self.connected = False
        
    async def connect(self):
        self.connected = True
        
    async def close(self):
        self.connected = False
        
    async def invoke(self, prompt: str, options: ModelOptions) -> LLMResponse:
        """Mock LLM call"""
        self.call_count += 1
        
        # Generate response based on task type
        responses = {
            "risk_assessment": f"Risk Assessment: Minimal risk study. {prompt[:30]}...",
            "phi_detection": f"PHI Assessment: No PHI detected. {prompt[:30]}...",  
            "irb_protocol": f"IRB Protocol: Complete protocol document. {prompt[:30]}...",
            "consent_form": f"Consent Form: All elements included. {prompt[:30]}...",
            "irb_compliance": f"Compliance Review: All requirements met. {prompt[:30]}..."
        }
        
        content = responses.get(options.task_type, f"Mock response: {prompt[:50]}")
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(total_tokens=100, prompt_tokens=60, completion_tokens=40),
            cost=CostBreakdown(total=0.005, input=0.003, output=0.002),
            model="claude-3-5-sonnet-20241022",
            tier=options.model_tier.value if options.model_tier else "STANDARD",
            finish_reason="stop",
            metadata={"mock": True}
        )


class SimpleIRBAgent:
    """Simplified IRB agent for testing"""
    
    def __init__(self, bridge: AIRouterBridge):
        self.bridge = bridge
        
    async def call_llm(self, prompt: str, task_type: str, state: IRBState) -> str:
        """Call LLM through bridge"""
        options = ModelOptions(
            task_type=task_type,
            model_tier=ModelTier.STANDARD,
            governance_mode=GovernanceMode.DEMO
        )
        
        response = await self.bridge.invoke(prompt, options)
        
        # Update token count
        state['token_count'] += response.usage.total_tokens
        
        return response.content
    
    async def assess_risk_node(self, state: IRBState) -> Dict[str, Any]:
        """Risk assessment node"""
        prompt = f"Assess research risks for: {state.get('messages', [''])[-1]}"
        result = await self.call_llm(prompt, "risk_assessment", state)
        
        return {
            'current_stage': 13,
            'risk_result': result,
            'current_output': result
        }
    
    async def check_phi_node(self, state: IRBState) -> Dict[str, Any]:
        """PHI detection node"""  
        prompt = f"Check PHI compliance for: {state.get('risk_result', '')}"
        result = await self.call_llm(prompt, "phi_detection", state)
        
        return {
            'phi_result': result,
            'current_output': result
        }
    
    def create_graph(self):
        """Create simple LangGraph"""
        graph = StateGraph(IRBState)
        
        graph.add_node("assess_risk", self.assess_risk_node)
        graph.add_node("check_phi", self.check_phi_node)
        
        graph.set_entry_point("assess_risk")
        graph.add_edge("assess_risk", "check_phi")
        graph.add_edge("check_phi", END)
        
        return graph.compile(checkpointer=MemorySaver())


@pytest.mark.skipif(not (LANGGRAPH_AVAILABLE and BRIDGE_AVAILABLE), 
                   reason="LangGraph or Bridge not available")
class TestMinimalBridgeIntegration:
    """Test minimal bridge + LangGraph integration"""

    @pytest.fixture
    def mock_bridge(self):
        """Mock bridge"""
        return MockAIRouterBridge()
    
    @pytest.fixture
    async def simple_agent(self, mock_bridge):
        """Simple agent with mock bridge"""
        return SimpleIRBAgent(mock_bridge)
    
    @pytest.fixture
    def test_state(self):
        """Test state"""
        return IRBState(
            agent_id='irb',
            messages=["Generate IRB for sleep study"],
            current_stage=13,
            current_output="",
            risk_result="",
            phi_result="",
            protocol_result="",
            consent_result="",
            compliance_result="",
            token_count=0,
            governance_mode='DEMO'
        )

    @pytest.mark.asyncio
    async def test_bridge_basic_functionality(self, mock_bridge):
        """Test basic bridge functionality"""
        await mock_bridge.connect()
        assert mock_bridge.connected
        
        options = ModelOptions(
            task_type="risk_assessment",
            model_tier=ModelTier.STANDARD,
            governance_mode=GovernanceMode.DEMO
        )
        
        response = await mock_bridge.invoke("Test prompt", options)
        
        assert response.content.startswith("Risk Assessment")
        assert response.usage.total_tokens == 100
        assert response.cost.total == 0.005
        assert mock_bridge.call_count == 1
        
        await mock_bridge.close()
    
    @pytest.mark.asyncio
    async def test_agent_llm_calls(self, simple_agent, test_state, mock_bridge):
        """Test agent LLM calls through bridge"""
        await mock_bridge.connect()
        
        result = await simple_agent.call_llm(
            "Assess research risks", 
            "risk_assessment", 
            test_state
        )
        
        assert isinstance(result, str)
        assert "Risk Assessment" in result
        assert test_state['token_count'] == 100
        assert mock_bridge.call_count == 1
        
        await mock_bridge.close()
    
    @pytest.mark.asyncio
    async def test_individual_nodes(self, simple_agent, test_state, mock_bridge):
        """Test individual agent nodes"""
        await mock_bridge.connect()
        
        # Test risk assessment node
        risk_result = await simple_agent.assess_risk_node(test_state)
        
        assert 'current_stage' in risk_result
        assert risk_result['current_stage'] == 13
        assert 'risk_result' in risk_result
        assert 'Risk Assessment' in risk_result['risk_result']
        
        # Update state and test PHI node
        test_state['risk_result'] = risk_result['risk_result']
        phi_result = await simple_agent.check_phi_node(test_state)
        
        assert 'phi_result' in phi_result
        assert 'PHI Assessment' in phi_result['phi_result']
        assert mock_bridge.call_count == 2
        
        await mock_bridge.close()
    
    def test_langgraph_compilation(self, simple_agent):
        """Test LangGraph compilation"""
        graph = simple_agent.create_graph()
        assert graph is not None
        print("✅ LangGraph compilation successful")
    
    @pytest.mark.asyncio
    async def test_full_graph_execution(self, simple_agent, test_state, mock_bridge):
        """Test full graph execution"""
        await mock_bridge.connect()
        
        graph = simple_agent.create_graph()
        result = await graph.ainvoke(test_state)
        
        assert result is not None
        assert 'phi_result' in result
        assert 'risk_result' in result
        assert result['token_count'] > 0
        assert mock_bridge.call_count == 2
        
        print("✅ Full graph execution successful")
        await mock_bridge.close()


@pytest.mark.skipif(not BRIDGE_AVAILABLE, reason="Bridge not available")
class TestBridgeComponents:
    """Test bridge components independently"""
    
    def test_model_options_creation(self):
        """Test ModelOptions creation"""
        options = ModelOptions(
            task_type="risk_assessment",
            model_tier=ModelTier.STANDARD,
            governance_mode=GovernanceMode.DEMO,
            max_tokens=4096
        )
        
        assert options.task_type == "risk_assessment"
        assert options.model_tier == ModelTier.STANDARD
        assert options.governance_mode == GovernanceMode.DEMO
        assert options.max_tokens == 4096
    
    def test_response_creation(self):
        """Test LLMResponse creation"""
        response = LLMResponse(
            content="Test response",
            usage=TokenUsage(100, 60, 40),
            cost=CostBreakdown(0.01, 0.006, 0.004),
            model="test-model",
            tier="STANDARD",
            finish_reason="stop"
        )
        
        assert response.content == "Test response"
        assert response.usage.total_tokens == 100
        assert response.cost.total == 0.01
        assert response.tier == "STANDARD"
    
    def test_enums(self):
        """Test enum values"""
        assert ModelTier.ECONOMY.value == "ECONOMY"
        assert ModelTier.STANDARD.value == "STANDARD" 
        assert ModelTier.PREMIUM.value == "PREMIUM"
        
        assert GovernanceMode.DEMO.value == "DEMO"
        assert GovernanceMode.LIVE.value == "LIVE"


def test_imports():
    """Test critical imports"""
    if not LANGGRAPH_AVAILABLE:
        pytest.skip("LangGraph not available")
    if not BRIDGE_AVAILABLE:
        pytest.skip("Bridge not available")
    
    print("✅ All imports successful")


if __name__ == "__main__":
    print("🧪 Minimal IRB Agent + Bridge Test")
    print("=" * 40)
    
    if not LANGGRAPH_AVAILABLE:
        print("❌ LangGraph not available")
        exit(1)
    
    if not BRIDGE_AVAILABLE:  
        print("❌ AI Router Bridge not available")
        exit(1)
    
    print("✅ LangGraph available")
    print("✅ AI Router Bridge available")
    
    # Basic functionality test
    async def basic_test():
        mock_bridge = MockAIRouterBridge()
        await mock_bridge.connect()
        
        # Test bridge call
        options = ModelOptions(task_type="test", model_tier=ModelTier.STANDARD)
        response = await mock_bridge.invoke("test prompt", options)
        assert "Mock response" in response.content
        
        # Test simple agent
        agent = SimpleIRBAgent(mock_bridge)
        state = IRBState(
            agent_id='irb', messages=["test"], current_stage=13,
            current_output="", risk_result="", phi_result="",
            protocol_result="", consent_result="", compliance_result="",
            token_count=0, governance_mode='DEMO'
        )
        
        result = await agent.call_llm("test", "risk_assessment", state)
        assert len(result) > 0
        
        # Test graph compilation
        graph = agent.create_graph()
        assert graph is not None
        
        await mock_bridge.close()
        print("✅ All basic tests passed!")
    
    try:
        asyncio.run(basic_test())
        print("\n🎯 Ready for full integration! Run with pytest:")
        print("pytest services/worker/tests/agents/irb/test_minimal_bridge.py -v")
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        exit(1)