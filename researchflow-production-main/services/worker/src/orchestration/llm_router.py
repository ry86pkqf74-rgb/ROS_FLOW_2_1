"""
Multi-LLM Router for ResearchFlow
Routes tasks to appropriate LLM based on task type, complexity, and PHI detection.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# LangChain imports with graceful fallback
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ChatAnthropic = None
    ANTHROPIC_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    ChatOpenAI = None
    OPENAI_AVAILABLE = False

try:
    from langchain_community.llms import Ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    Ollama = None
    OLLAMA_AVAILABLE = False


class TaskType(Enum):
    REASONING = "reasoning"
    GENERATION = "generation"
    CODING = "coding"
    INSIGHTS = "insights"
    REVIEW = "review"
    LOCAL = "local"


@dataclass
class RoutingDecision:
    provider: str
    model: str
    reason: str
    phi_detected: bool = False
    confidence: float = 1.0


class PHIDetector:
    """Detects Protected Health Information in text."""
    
    PHI_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card
        r'\b[A-Z]{2}\d{6,8}\b',  # Medical record numbers
        r'\bDOB[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DOB
    ]
    
    PHI_KEYWORDS = [
        'patient', 'diagnosis', 'treatment', 'medication', 
        'prescription', 'medical record', 'health insurance',
        'hipaa', 'phi', 'protected health'
    ]
    
    @classmethod
    def detect(cls, text: str) -> bool:
        text_lower = text.lower()
        
        # Check patterns
        for pattern in cls.PHI_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check keywords
        for keyword in cls.PHI_KEYWORDS:
            if keyword in text_lower:
                return True
        
        return False


class LLMRouter:
    """
    Routes tasks to appropriate LLM based on task characteristics.
    
    Routing Strategy:
    - Claude: Reasoning, code review, manuscript refinement
    - GPT-4: Generation, creative content
    - Grok: Real-time insights, analysis
    - Qwen/Ollama: Local tasks, PHI-sensitive, cost optimization
    """
    
    def __init__(self):
        self._claude = None
        self._gpt = None
        self._ollama = None
        self._routing_history: List[RoutingDecision] = []
    
    @property
    def claude(self):
        if self._claude is None and ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self._claude = ChatAnthropic(
                    model="claude-sonnet-4-20250514",
                    api_key=api_key
                )
        return self._claude
    
    @property
    def gpt(self):
        if self._gpt is None and OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._gpt = ChatOpenAI(
                    model="gpt-4o",
                    api_key=api_key
                )
        return self._gpt
    
    @property
    def ollama(self):
        if self._ollama is None and OLLAMA_AVAILABLE:
            self._ollama = Ollama(
                model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        return self._ollama
    
    def route(
        self, 
        task: str,
        task_type: Optional[str] = None,
        complexity: str = "medium",
        force_local: bool = False
    ) -> RoutingDecision:
        """
        Route a task to the appropriate LLM.
        
        Args:
            task: The task description
            task_type: Optional explicit task type
            complexity: low/medium/high
            force_local: Force local model for privacy
        
        Returns:
            RoutingDecision with provider, model, and reasoning
        """
        # Check for PHI
        phi_detected = PHIDetector.detect(task)
        
        # Force local if PHI detected or requested
        if phi_detected or force_local:
            decision = RoutingDecision(
                provider="ollama",
                model="qwen2.5-coder:7b",
                reason="PHI detected - routing to local model" if phi_detected else "Forced local",
                phi_detected=phi_detected
            )
            self._routing_history.append(decision)
            return decision
        
        # Infer task type if not provided
        if task_type is None:
            task_type = self._infer_task_type(task)
        
        # Route based on task type
        if task_type in ["reasoning", "review", "analysis"]:
            decision = RoutingDecision(
                provider="claude",
                model="claude-sonnet-4-20250514",
                reason=f"Task type '{task_type}' routes to Claude for reasoning"
            )
        elif task_type in ["generation", "creative", "writing"]:
            decision = RoutingDecision(
                provider="gpt",
                model="gpt-4o",
                reason=f"Task type '{task_type}' routes to GPT-4 for generation"
            )
        elif task_type in ["coding", "local"] or complexity == "low":
            decision = RoutingDecision(
                provider="ollama",
                model="qwen2.5-coder:7b",
                reason=f"Task type '{task_type}' or low complexity routes to local Qwen"
            )
        else:
            # Default to Claude
            decision = RoutingDecision(
                provider="claude",
                model="claude-sonnet-4-20250514",
                reason="Default routing to Claude"
            )
        
        self._routing_history.append(decision)
        logger.info(f"Routed task to {decision.provider}: {decision.reason}")
        return decision
    
    def _infer_task_type(self, task: str) -> str:
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["review", "analyze", "reason", "evaluate", "critique"]):
            return "reasoning"
        elif any(kw in task_lower for kw in ["generate", "create", "write", "draft", "compose"]):
            return "generation"
        elif any(kw in task_lower for kw in ["code", "implement", "fix", "debug", "refactor"]):
            return "coding"
        elif any(kw in task_lower for kw in ["insight", "trend", "predict", "forecast"]):
            return "insights"
        
        return "general"
    
    def get_llm(self, decision: RoutingDecision):
        """Get the LLM instance for a routing decision."""
        if decision.provider == "claude":
            return self.claude
        elif decision.provider == "gpt":
            return self.gpt
        elif decision.provider == "ollama":
            return self.ollama
        else:
            return self.claude  # fallback
    
    def invoke(self, task: str, **kwargs) -> str:
        """Route and invoke the appropriate LLM."""
        decision = self.route(task, **kwargs)
        llm = self.get_llm(decision)
        
        if llm is None:
            raise RuntimeError(f"LLM provider '{decision.provider}' not available")
        
        response = llm.invoke(task)
        return response.content if hasattr(response, 'content') else str(response)


# Singleton router instance
_router: Optional[LLMRouter] = None

def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# Convenience function
def route_and_invoke(task: str, **kwargs) -> str:
    return get_router().invoke(task, **kwargs)
