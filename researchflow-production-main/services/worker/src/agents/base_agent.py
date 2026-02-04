"""
BaseAgent - LangGraph Foundation for ResearchFlow Agents

This module provides the base class for all research workflow agents.
Implements the Planner → Retriever → Executor → Reflector architecture
with Redis checkpointing and quality gates.

Linear Issues: ROS-67, ROS-68
"""

import os
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Literal
from dataclasses import dataclass, field, asdict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

import httpx
import redis.asyncio as redis

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class AgentState(TypedDict):
    """State passed through the agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    task_id: str
    stage_id: int
    research_id: str
    
    # Planning
    plan: Optional[Dict[str, Any]]
    current_step: int
    total_steps: int
    
    # RAG Context
    retrieved_docs: List[Dict[str, Any]]
    rag_query: Optional[str]
    rag_collection: Optional[str]
    
    # Execution
    execution_result: Optional[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    
    # Reflection
    quality_score: float
    quality_feedback: Optional[str]
    iteration: int
    max_iterations: int
    
    # Metadata
    started_at: str
    phi_safe: bool
    error: Optional[str]


@dataclass
class AgentConfig:
    """Configuration for research agents."""
    name: str
    description: str
    stages: List[int]  # Which workflow stages this agent handles
    rag_collections: List[str]  # Collections to query for RAG
    max_iterations: int = 3
    quality_threshold: float = 0.8
    timeout_seconds: int = 120
    phi_safe: bool = True
    model_provider: str = "anthropic"  # anthropic, openai, local
    model_name: Optional[str] = None


@dataclass
class QualityCheckResult:
    """Result of quality gate evaluation."""
    passed: bool
    score: float
    feedback: str
    criteria_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Final result from agent execution."""
    task_id: str
    agent_name: str
    success: bool
    result: Optional[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    quality_score: float
    iterations: int
    duration_ms: int
    rag_sources: List[str]
    error: Optional[str] = None


# =============================================================================
# Base Agent Class
# =============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for LangGraph-powered research agents.
    
    Implements the core flow:
    1. PLAN - Decompose task into steps
    2. RETRIEVE - Fetch relevant context from vector store
    3. EXECUTE - Perform the actual work
    4. REFLECT - Quality check and iterate if needed
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = self._create_llm()
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    def _create_llm(self):
        """Create the appropriate LLM based on config."""
        if self.config.model_provider == "anthropic":
            return ChatAnthropic(
                model=self.config.model_name or "claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.3,
            )
        elif self.config.model_provider == "openai":
            return ChatOpenAI(
                model=self.config.model_name or "gpt-4o",
                max_tokens=4096,
                temperature=0.3,
            )
        elif self.config.model_provider == "local":
            # Use local Ollama via OpenAI-compatible API
            return ChatOpenAI(
                model=self.config.model_name or "qwen2.5-coder:7b",
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1",
                api_key="ollama",  # Ollama doesn't need a real key
                max_tokens=4096,
                temperature=0.3,
            )
        else:
            raise ValueError(f"Unknown model provider: {self.config.model_provider}")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("reflect", self._reflect_node)

        # Define edges
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "retrieve")
        workflow.add_edge("retrieve", "execute")
        workflow.add_edge("execute", "reflect")
        
        # Conditional edge from reflect - iterate or finish
        workflow.add_conditional_edges(
            "reflect",
            self._should_continue,
            {
                "continue": "retrieve",  # Try again with refined approach
                "end": END,
            }
        )

        return workflow.compile(checkpointer=self.checkpointer)

    # =========================================================================
    # Graph Nodes
    # =========================================================================

    async def _plan_node(self, state: AgentState) -> AgentState:
        """Plan the execution steps for the task."""
        logger.info(f"[{self.config.name}] Planning task {state['task_id']}")
        
        planning_prompt = self._get_planning_prompt(state)
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=planning_prompt),
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Parse the plan from the response
            plan = self._parse_plan(response.content)
            return {
                **state,
                "plan": plan,
                "total_steps": len(plan.get("steps", [])),
                "current_step": 0,
                "rag_query": plan.get("initial_query"),
                "rag_collection": plan.get("primary_collection", self.config.rag_collections[0]),
            }
        except Exception as e:
            logger.error(f"[{self.config.name}] Planning failed: {e}")
            return {**state, "error": f"Planning failed: {str(e)}"}

    async def _retrieve_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents from vector store."""
        if not state.get("rag_query"):
            return state
            
        logger.info(f"[{self.config.name}] Retrieving context for: {state['rag_query'][:50]}...")
        
        try:
            docs = await self._retrieve_documents(
                query=state["rag_query"],
                collection=state.get("rag_collection", self.config.rag_collections[0]),
                top_k=5,
            )
            
            return {
                **state,
                "retrieved_docs": docs,
            }
        except Exception as e:
            logger.warning(f"[{self.config.name}] RAG retrieval failed: {e}")
            return {**state, "retrieved_docs": []}

    async def _execute_node(self, state: AgentState) -> AgentState:
        """Execute the main agent task."""
        logger.info(f"[{self.config.name}] Executing task (iteration {state['iteration']})")
        
        try:
            # Build context from retrieved docs
            context = self._format_retrieved_context(state.get("retrieved_docs", []))
            
            # Get task-specific execution prompt
            execution_prompt = self._get_execution_prompt(state, context)
            
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                *state.get("messages", []),
                HumanMessage(content=execution_prompt),
            ]
            
            # PHI check before execution
            if not self.config.phi_safe:
                messages = await self._scan_phi(messages)
            
            response = await self.llm.ainvoke(messages)
            
            # Parse execution result
            result = self._parse_execution_result(response.content)
            artifacts = self._extract_artifacts(result)
            
            return {
                **state,
                "execution_result": result,
                "artifacts": [*state.get("artifacts", []), *artifacts],
                "messages": [*state.get("messages", []), AIMessage(content=response.content)],
            }
        except Exception as e:
            logger.error(f"[{self.config.name}] Execution failed: {e}")
            return {**state, "error": f"Execution failed: {str(e)}"}

    async def _reflect_node(self, state: AgentState) -> AgentState:
        """Reflect on the result and check quality."""
        logger.info(f"[{self.config.name}] Reflecting on result")
        
        if state.get("error"):
            return {
                **state,
                "quality_score": 0.0,
                "quality_feedback": f"Error occurred: {state['error']}",
            }
        
        try:
            quality_result = await self._check_quality(state)
            
            # Prepare for potential next iteration
            refined_query = None
            if not quality_result.passed and state["iteration"] < state["max_iterations"]:
                refined_query = await self._refine_query(state, quality_result.feedback)
            
            return {
                **state,
                "quality_score": quality_result.score,
                "quality_feedback": quality_result.feedback,
                "iteration": state["iteration"] + 1,
                "rag_query": refined_query or state.get("rag_query"),
            }
        except Exception as e:
            logger.error(f"[{self.config.name}] Reflection failed: {e}")
            return {
                **state,
                "quality_score": 0.5,  # Assume partial success
                "quality_feedback": f"Reflection error: {str(e)}",
                "iteration": state["iteration"] + 1,
            }

    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Decide whether to iterate or finish."""
        # End if error
        if state.get("error"):
            return "end"
        
        # End if quality threshold met
        if state["quality_score"] >= self.config.quality_threshold:
            logger.info(f"[{self.config.name}] Quality threshold met: {state['quality_score']:.2f}")
            return "end"
        
        # End if max iterations reached
        if state["iteration"] >= state["max_iterations"]:
            logger.info(f"[{self.config.name}] Max iterations reached")
            return "end"
        
        # Continue iterating
        logger.info(f"[{self.config.name}] Continuing iteration {state['iteration']}")
        return "continue"

    # =========================================================================
    # Abstract Methods - Implement in Subclasses
    # =========================================================================

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def _get_planning_prompt(self, state: AgentState) -> str:
        """Return the planning prompt for decomposing the task."""
        pass

    @abstractmethod
    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        """Return the execution prompt with RAG context."""
        pass

    @abstractmethod
    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured result."""
        pass

    @abstractmethod
    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Evaluate the quality of the execution result."""
        pass

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """Parse planning response into structured plan."""
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                # Try to find JSON object
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: create simple plan
        return {
            "steps": ["Execute main task"],
            "initial_query": None,
            "primary_collection": self.config.rag_collections[0] if self.config.rag_collections else None,
        }

    def _format_retrieved_context(self, docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context string."""
        if not docs:
            return "No relevant context found."
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("metadata", {}).get("source", "Unknown")
            content = doc.get("content", "")[:1000]  # Truncate long docs
            context_parts.append(f"[Source {i}: {source}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)

    def _extract_artifacts(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract artifacts from execution result."""
        artifacts = []
        
        # Check for common artifact patterns
        if "output" in result:
            artifacts.append({
                "type": "output",
                "content": result["output"],
                "created_at": datetime.utcnow().isoformat(),
            })
        
        if "tables" in result:
            for table in result["tables"]:
                artifacts.append({
                    "type": "table",
                    "content": table,
                    "created_at": datetime.utcnow().isoformat(),
                })
        
        if "figures" in result:
            for figure in result["figures"]:
                artifacts.append({
                    "type": "figure",
                    "content": figure,
                    "created_at": datetime.utcnow().isoformat(),
                })
        
        return artifacts

    async def _refine_query(self, state: AgentState, feedback: str) -> str:
        """Refine the RAG query based on quality feedback."""
        refine_prompt = f"""Based on this feedback, suggest a better search query:

Feedback: {feedback}
Original query: {state.get('rag_query', 'None')}
Task context: {state.get('plan', {}).get('steps', ['Unknown'])[0]}

Return only the refined query, no explanation."""

        response = await self.llm.ainvoke([HumanMessage(content=refine_prompt)])
        return response.content.strip()

    async def _retrieve_documents(
        self,
        query: str,
        collection: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve documents from ChromaDB via orchestrator API."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        
        orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001")
        
        try:
            response = await self.http_client.post(
                f"{orchestrator_url}/api/rag/search",
                json={
                    "query": query,
                    "collection": collection,
                    "top_k": top_k,
                }
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return []

    async def _scan_phi(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Scan messages for PHI and redact if necessary."""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        
        orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:3001")
        
        try:
            # Extract text content
            text = "\n".join(m.content for m in messages if hasattr(m, "content"))
            
            response = await self.http_client.post(
                f"{orchestrator_url}/api/phi/scan",
                json={"text": text}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("has_phi"):
                logger.warning(f"PHI detected and redacted: {result.get('entities', [])}")
                # Replace with redacted version
                redacted = result.get("redacted_text", text)
                return [HumanMessage(content=redacted)]
            
            return messages
        except Exception as e:
            logger.error(f"PHI scan failed: {e}")
            # Fail closed - don't send if we can't verify
            raise RuntimeError(f"PHI scan required but failed: {e}")

    # =========================================================================
    # Public API
    # =========================================================================

    async def run(
        self,
        task_id: str,
        stage_id: int,
        research_id: str,
        input_data: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> AgentResult:
        """
        Run the agent on a task.
        
        Args:
            task_id: Unique identifier for this task
            stage_id: Workflow stage number
            research_id: Parent research project ID
            input_data: Task-specific input data
            thread_id: Optional thread ID for checkpointing
        
        Returns:
            AgentResult with success status, outputs, and metrics
        """
        start_time = datetime.utcnow()
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=json.dumps(input_data))],
            "task_id": task_id,
            "stage_id": stage_id,
            "research_id": research_id,
            "plan": None,
            "current_step": 0,
            "total_steps": 0,
            "retrieved_docs": [],
            "rag_query": None,
            "rag_collection": None,
            "execution_result": None,
            "artifacts": [],
            "quality_score": 0.0,
            "quality_feedback": None,
            "iteration": 0,
            "max_iterations": self.config.max_iterations,
            "started_at": start_time.isoformat(),
            "phi_safe": self.config.phi_safe,
            "error": None,
        }

        # Run the graph
        config = {"configurable": {"thread_id": thread_id or task_id}}
        
        try:
            final_state = await self.graph.ainvoke(initial_state, config)
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return AgentResult(
                task_id=task_id,
                agent_name=self.config.name,
                success=final_state.get("error") is None and final_state["quality_score"] >= self.config.quality_threshold,
                result=final_state.get("execution_result"),
                artifacts=final_state.get("artifacts", []),
                quality_score=final_state["quality_score"],
                iterations=final_state["iteration"],
                duration_ms=duration_ms,
                rag_sources=[d.get("id", "") for d in final_state.get("retrieved_docs", [])],
                error=final_state.get("error"),
            )
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"[{self.config.name}] Agent execution failed: {e}")
            
            return AgentResult(
                task_id=task_id,
                agent_name=self.config.name,
                success=False,
                result=None,
                artifacts=[],
                quality_score=0.0,
                iterations=0,
                duration_ms=duration_ms,
                rag_sources=[],
                error=str(e),
            )

    async def close(self):
        """Clean up resources."""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            await self.redis_client.close()
