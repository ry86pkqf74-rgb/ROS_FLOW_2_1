# AI Bridge Integration Guide

## Quick Start

### 1. Python Client Setup

```python
import httpx
import asyncio
import json
import time
from typing import Optional, Dict, Any, List

class AIBridgeClient:
    """Python client for ResearchFlow AI Bridge"""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check bridge health status"""
        response = await self.client.get(
            f"{self.base_url}/api/ai-bridge/health",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get bridge capabilities and supported features"""
        response = await self.client.get(
            f"{self.base_url}/api/ai-bridge/capabilities",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def invoke(
        self,
        prompt: str,
        task_type: str,
        agent_id: str,
        project_id: str,
        run_id: Optional[str] = None,
        model_tier: str = "STANDARD",
        governance_mode: str = "DEMO",
        require_phi_compliance: bool = False,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stage_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make a single LLM invocation"""
        
        payload = {
            "prompt": prompt,
            "options": {
                "taskType": task_type,
                "modelTier": model_tier,
                "governanceMode": governance_mode,
                "requirePhiCompliance": require_phi_compliance
            },
            "metadata": {
                "agentId": agent_id,
                "projectId": project_id,
                "runId": run_id or f"run-{int(time.time())}",
                "threadId": f"thread-{agent_id}",
                "stageRange": [1, 20],
                "currentStage": stage_id or 1
            }
        }
        
        # Add optional parameters
        if max_tokens:
            payload["options"]["maxTokens"] = max_tokens
        if temperature is not None:
            payload["options"]["temperature"] = temperature
        if stage_id:
            payload["options"]["stageId"] = stage_id
        
        # Add any additional options
        payload["options"].update(kwargs)
        
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/invoke",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def batch(
        self,
        prompts: List[str],
        task_type: str,
        agent_id: str,
        project_id: str,
        run_id: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """Process multiple prompts in batch"""
        
        payload = {
            "prompts": prompts,
            "options": {
                "taskType": task_type,
                **options
            },
            "metadata": {
                "agentId": agent_id,
                "projectId": project_id,
                "runId": run_id or f"batch-{int(time.time())}",
                "threadId": f"thread-{agent_id}",
                "stageRange": [1, 20],
                "currentStage": 1
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/batch",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    async def stream(
        self,
        prompt: str,
        task_type: str,
        agent_id: str,
        project_id: str,
        run_id: Optional[str] = None,
        **options
    ):
        """Stream LLM responses"""
        
        payload = {
            "prompt": prompt,
            "options": {
                "taskType": task_type,
                **options
            },
            "metadata": {
                "agentId": agent_id,
                "projectId": project_id,
                "runId": run_id or f"stream-{int(time.time())}",
                "threadId": f"thread-{agent_id}",
                "stageRange": [1, 20],
                "currentStage": 1
            }
        }
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/ai-bridge/stream",
            json=payload,
            headers=self.headers
        ) as response:
            response.raise_for_status()
            
            content = ""
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                    
                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break
                
                try:
                    data = json.loads(data_str)
                    if data["type"] == "status":
                        yield {"type": "status", "data": data}
                    elif data["type"] == "content":
                        content += data["content"]
                        yield {"type": "content", "data": data}
                    elif data["type"] == "complete":
                        yield {"type": "complete", "data": data}
                        break
                except json.JSONDecodeError:
                    continue
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
```

### 2. Basic Usage Examples

```python
# Initialize client
bridge = AIBridgeClient(
    base_url="http://localhost:3001",
    auth_token="your-jwt-token"
)

# Check health
health = await bridge.health_check()
print(f"Bridge status: {health['status']}")

# Single invocation
result = await bridge.invoke(
    prompt="Generate a research hypothesis for this dataset",
    task_type="hypothesis_generation",
    agent_id="research-agent",
    project_id="proj-123",
    model_tier="STANDARD"
)

print(f"Response: {result['content']}")
print(f"Cost: ${result['cost']['total']:.4f}")

# Batch processing
responses = await bridge.batch(
    prompts=[
        "Summarize the methodology section",
        "Extract key findings",
        "Identify limitations"
    ],
    task_type="summarization",
    agent_id="manuscript-agent",
    project_id="proj-123",
    model_tier="ECONOMY"
)

for i, response in enumerate(responses["responses"]):
    print(f"Response {i}: {response['content'][:100]}...")

# Streaming
async for chunk in bridge.stream(
    prompt="Provide a detailed analysis of the research data",
    task_type="data_analysis",
    agent_id="analysis-agent",
    project_id="proj-123",
    model_tier="PREMIUM"
):
    if chunk["type"] == "content":
        print(chunk["data"]["content"], end="", flush=True)
    elif chunk["type"] == "complete":
        print(f"\nTotal cost: ${chunk['data']['cost']['total']:.4f}")

await bridge.close()
```

## Agent Integration Patterns

### 1. LangGraph Agent Integration

```python
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langgraph import StateGraph, Node
from typing import TypedDict, List

class AgentState(TypedDict):
    messages: List[BaseMessage]
    project_id: str
    stage_id: int
    context: Dict[str, Any]

class AIBridgeAgent:
    def __init__(self, bridge: AIBridgeClient, agent_id: str):
        self.bridge = bridge
        self.agent_id = agent_id
    
    async def hypothesis_generation_node(self, state: AgentState) -> AgentState:
        """Generate research hypotheses"""
        last_message = state["messages"][-1]
        
        response = await self.bridge.invoke(
            prompt=last_message.content,
            task_type="hypothesis_generation",
            agent_id=self.agent_id,
            project_id=state["project_id"],
            stage_id=state["stage_id"],
            model_tier="STANDARD"
        )
        
        state["messages"].append(AIMessage(content=response["content"]))
        state["context"]["last_cost"] = response["cost"]["total"]
        state["context"]["last_tokens"] = response["usage"]["totalTokens"]
        
        return state
    
    async def literature_analysis_node(self, state: AgentState) -> AgentState:
        """Analyze literature"""
        last_message = state["messages"][-1]
        
        response = await self.bridge.invoke(
            prompt=last_message.content,
            task_type="literature_search",
            agent_id=self.agent_id,
            project_id=state["project_id"],
            stage_id=state["stage_id"],
            model_tier="ECONOMY",
            require_phi_compliance=False
        )
        
        state["messages"].append(AIMessage(content=response["content"]))
        return state

# Build the graph
def create_research_graph(bridge: AIBridgeClient) -> StateGraph:
    agent = AIBridgeAgent(bridge, "research-agent")
    
    graph = StateGraph(AgentState)
    graph.add_node("hypothesis", agent.hypothesis_generation_node)
    graph.add_node("literature", agent.literature_analysis_node)
    
    graph.add_edge("hypothesis", "literature")
    graph.set_entry_point("hypothesis")
    graph.set_finish_point("literature")
    
    return graph
```

### 2. Error Handling and Retry Logic

```python
import asyncio
import logging
from typing import Callable, TypeVar, Any

T = TypeVar('T')

class BridgeError(Exception):
    def __init__(self, message: str, error_code: str = None, retry_after: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after

async def with_retry(
    func: Callable[..., T], 
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> T:
    """Execute function with exponential backoff retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            if attempt == max_retries:
                raise BridgeError(
                    f"Max retries ({max_retries}) exceeded",
                    error_code="MAX_RETRIES_EXCEEDED"
                )
            
            if e.response.status_code == 429:  # Rate limited
                retry_after = int(e.response.headers.get('retry-after', base_delay))
                logging.warning(f"Rate limited, retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
            elif e.response.status_code == 503:  # Service unavailable
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                logging.warning(f"Service unavailable, retrying after {delay}s")
                await asyncio.sleep(delay)
            elif e.response.status_code in [500, 502, 504]:  # Server errors
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                logging.warning(f"Server error, retrying after {delay}s")
                await asyncio.sleep(delay)
            else:
                # Don't retry client errors (4xx except 429)
                raise BridgeError(
                    f"Request failed: {e.response.status_code}",
                    error_code=str(e.response.status_code)
                )
        except httpx.RequestError as e:
            if attempt == max_retries:
                raise BridgeError(
                    f"Connection error after {max_retries} retries: {str(e)}",
                    error_code="CONNECTION_ERROR"
                )
            
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            logging.warning(f"Connection error, retrying after {delay}s: {str(e)}")
            await asyncio.sleep(delay)

# Usage
async def safe_invoke(bridge: AIBridgeClient, **kwargs):
    return await with_retry(
        lambda: bridge.invoke(**kwargs),
        max_retries=3
    )
```

### 3. Cost and Usage Tracking

```python
class CostTracker:
    def __init__(self):
        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_count = 0
        self.cost_by_task_type = {}
        
    def track_response(self, response: Dict[str, Any], task_type: str):
        """Track cost and usage from bridge response"""
        cost = response["cost"]["total"]
        tokens = response["usage"]["totalTokens"]
        
        self.total_cost += cost
        self.total_tokens += tokens
        self.request_count += 1
        
        if task_type not in self.cost_by_task_type:
            self.cost_by_task_type[task_type] = {"cost": 0.0, "tokens": 0, "count": 0}
        
        self.cost_by_task_type[task_type]["cost"] += cost
        self.cost_by_task_type[task_type]["tokens"] += tokens
        self.cost_by_task_type[task_type]["count"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary"""
        return {
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "average_cost_per_request": self.total_cost / max(self.request_count, 1),
            "cost_by_task_type": self.cost_by_task_type
        }
    
    def check_budget(self, daily_limit: float = 50.0) -> Dict[str, Any]:
        """Check if approaching budget limits"""
        usage_percent = (self.total_cost / daily_limit) * 100
        
        return {
            "current_cost": self.total_cost,
            "daily_limit": daily_limit,
            "usage_percent": usage_percent,
            "remaining_budget": daily_limit - self.total_cost,
            "warning": usage_percent > 80,
            "critical": usage_percent > 95
        }

# Usage in agent
class CostAwareAgent:
    def __init__(self, bridge: AIBridgeClient, daily_budget: float = 50.0):
        self.bridge = bridge
        self.cost_tracker = CostTracker()
        self.daily_budget = daily_budget
    
    async def invoke_with_tracking(self, task_type: str, **kwargs):
        # Check budget before making request
        budget_status = self.cost_tracker.check_budget(self.daily_budget)
        if budget_status["critical"]:
            raise BridgeError(
                f"Daily budget nearly exceeded: ${budget_status['current_cost']:.2f}",
                error_code="BUDGET_WARNING"
            )
        
        response = await self.bridge.invoke(task_type=task_type, **kwargs)
        self.cost_tracker.track_response(response, task_type)
        
        logging.info(
            f"Request completed - Cost: ${response['cost']['total']:.4f}, "
            f"Tokens: {response['usage']['totalTokens']}, "
            f"Total spent: ${self.cost_tracker.total_cost:.2f}"
        )
        
        return response
```

### 4. Configuration Management

```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class BridgeConfig:
    base_url: str
    auth_token: str
    default_model_tier: str = "STANDARD"
    default_governance_mode: str = "DEMO"
    daily_budget_limit: float = 50.0
    max_retries: int = 3
    timeout_seconds: float = 60.0
    phi_compliance_enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'BridgeConfig':
        """Load configuration from environment variables"""
        return cls(
            base_url=os.getenv('AI_BRIDGE_URL', 'http://localhost:3001'),
            auth_token=os.getenv('AI_BRIDGE_TOKEN', ''),
            default_model_tier=os.getenv('AI_BRIDGE_DEFAULT_TIER', 'STANDARD'),
            default_governance_mode=os.getenv('AI_BRIDGE_GOVERNANCE_MODE', 'DEMO'),
            daily_budget_limit=float(os.getenv('AI_BRIDGE_DAILY_BUDGET', '50.0')),
            max_retries=int(os.getenv('AI_BRIDGE_MAX_RETRIES', '3')),
            timeout_seconds=float(os.getenv('AI_BRIDGE_TIMEOUT', '60.0')),
            phi_compliance_enabled=os.getenv('AI_BRIDGE_PHI_COMPLIANCE', 'false').lower() == 'true'
        )

# Environment file (.env)
"""
AI_BRIDGE_URL=http://localhost:3001
AI_BRIDGE_TOKEN=your-jwt-token-here
AI_BRIDGE_DEFAULT_TIER=STANDARD
AI_BRIDGE_GOVERNANCE_MODE=DEMO
AI_BRIDGE_DAILY_BUDGET=50.0
AI_BRIDGE_MAX_RETRIES=3
AI_BRIDGE_TIMEOUT=60.0
AI_BRIDGE_PHI_COMPLIANCE=false
"""
```

## Task Type Selection Guide

| Task Type | Recommended Tier | PHI Compliance | Use Case |
|-----------|------------------|----------------|----------|
| `hypothesis_generation` | STANDARD | No | Generate research hypotheses |
| `literature_search` | ECONOMY | No | Search and analyze papers |
| `data_analysis` | STANDARD | Varies | Analyze datasets and results |
| `statistical_analysis` | PREMIUM | No | Complex statistical tests |
| `manuscript_drafting` | STANDARD | No | Draft paper sections |
| `manuscript_revision` | ECONOMY | No | Edit and improve content |
| `citation_formatting` | ECONOMY | No | Format references |
| `phi_redaction` | PREMIUM | Yes | Remove PHI from text |
| `ethical_review` | PREMIUM | Yes | Review for ethics compliance |
| `claim_verification` | STANDARD | No | Verify research claims |
| `summarization` | ECONOMY | No | Summarize documents |
| `code_generation` | STANDARD | No | Generate analysis code |
| `figure_generation` | STANDARD | No | Create visualizations |

## Production Checklist

- [ ] **Authentication**: Valid JWT token configured
- [ ] **Error Handling**: Implement retry logic with exponential backoff
- [ ] **Cost Tracking**: Monitor usage and set budget alerts
- [ ] **Logging**: Log all bridge interactions for debugging
- [ ] **Health Checks**: Monitor bridge health in your application
- [ ] **Rate Limiting**: Respect rate limits and implement queuing
- [ ] **Security**: Use PHI compliance mode for sensitive data
- [ ] **Monitoring**: Set up alerts for errors and cost overruns
- [ ] **Graceful Degradation**: Handle bridge outages gracefully
- [ ] **Configuration**: Use environment variables for all settings