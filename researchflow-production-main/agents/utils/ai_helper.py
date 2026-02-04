#!/usr/bin/env python3
"""
AI Helper - External AI Service Integration for ResearchFlow Agents

Allows agents to delegate tasks to specialized AI services:
- Code generation (OpenAI, Claude, XAI)
- Document analysis (Claude, GPT-4)
- Data extraction (OpenAI, Anthropic)
- Error analysis and debugging
- Code review assistance

All API keys are managed securely via SecretsManager.

@author Claude
@created 2025-01-30
"""

import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
import json
import re
from dataclasses import dataclass

# Lazy import httpx to avoid dependency issues
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import warnings
    warnings.warn("httpx not available - AI helper will have limited functionality")

from agents.utils.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    MERCURY = "mercury"
    SOURCEGRAPH = "sourcegraph"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    provider: AIProvider
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None


class AIHelper:
    """
    Helper to delegate tasks to external AI services.
    
    Manages API keys securely and provides unified interface across providers.
    Implements automatic fallback if primary provider fails.
    
    Example:
        >>> from agents.utils.ai_helper import get_ai_helper
        >>> ai = get_ai_helper()
        >>> response = await ai.ask_openai("Explain circuit breakers")
        >>> print(response.content)
    """
    
    def __init__(self):
        self.secrets = get_secrets_manager()
        
        if HTTPX_AVAILABLE:
            self.timeout = httpx.Timeout(60.0, connect=10.0)
        else:
            self.timeout = None
            logger.warning("⚠️  httpx not available - AI helper disabled")
    
    def get_api_key(self, provider: AIProvider) -> Optional[str]:
        """
        Get API key for provider from secure storage.
        
        Args:
            provider: AI provider enum
            
        Returns:
            API key or None if not found
        """
        key_mapping = {
            AIProvider.OPENAI: "OPENAI_API_KEY",
            AIProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            AIProvider.XAI: "XAI_API_KEY",
            AIProvider.MERCURY: "MERCURY_API_KEY",
            AIProvider.SOURCEGRAPH: "SOURCEGRAPH_API_KEY",
        }
        
        env_key = key_mapping.get(provider)
        if not env_key:
            return None
        
        return self.secrets.get_secret(env_key)
    
    async def ask_openai(
        self, 
        prompt: str,
        model: str = "gpt-4o",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        """
        Ask OpenAI for help with a task.
        
        Use cases:
        - Code generation
        - Documentation writing
        - API response analysis
        - General reasoning
        
        Args:
            prompt: User prompt
            model: Model to use (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
            system_prompt: Optional system prompt
            temperature: Creativity level (0.0 - 2.0)
            max_tokens: Maximum response length
            
        Returns:
            AIResponse or None if failed
        """
        if not HTTPX_AVAILABLE:
            logger.error("❌ httpx not available")
            return None
        
        api_key = self.get_api_key(AIProvider.OPENAI)
        if not api_key:
            logger.warning("⚠️  OpenAI API key not available")
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                
                return AIResponse(
                    content=content,
                    provider=AIProvider.OPENAI,
                    model=model,
                    tokens_used=usage.get("total_tokens"),
                    cost_estimate=self._estimate_openai_cost(model, usage)
                )
                
        except Exception as e:
            logger.error(f"❌ OpenAI request failed: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.OPENAI,
                model=model,
                error=str(e)
            )
    
    async def ask_claude(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        """
        Ask Claude (Anthropic) for help.
        
        Best for:
        - Long document analysis (200K context)
        - Complex reasoning
        - Code review and generation
        - Detailed explanations
        
        Args:
            prompt: User prompt
            model: Model to use
            system_prompt: Optional system prompt
            max_tokens: Maximum response length
            
        Returns:
            AIResponse or None if failed
        """
        if not HTTPX_AVAILABLE:
            logger.error("❌ httpx not available")
            return None
        
        api_key = self.get_api_key(AIProvider.ANTHROPIC)
        if not api_key:
            logger.warning("⚠️  Anthropic API key not available")
            return None
        
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=request_body
                )
                response.raise_for_status()
                data = response.json()
                
                content = data["content"][0]["text"]
                usage = data.get("usage", {})
                
                return AIResponse(
                    content=content,
                    provider=AIProvider.ANTHROPIC,
                    model=model,
                    tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    cost_estimate=self._estimate_anthropic_cost(model, usage)
                )
                
        except Exception as e:
            logger.error(f"❌ Claude request failed: {e}")
            return AIResponse(
                content="",
                provider=AIProvider.ANTHROPIC,
                model=model,
                error=str(e)
            )
    
    def _estimate_openai_cost(self, model: str, usage: Dict) -> float:
        """Estimate OpenAI API cost"""
        # Approximate pricing (as of Jan 2025)
        pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},  # per 1K tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }
        
        model_pricing = pricing.get(model, pricing["gpt-4o"])
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        cost = (input_tokens / 1000 * model_pricing["input"]) + \
               (output_tokens / 1000 * model_pricing["output"])
        
        return round(cost, 6)
    
    def _estimate_anthropic_cost(self, model: str, usage: Dict) -> float:
        """Estimate Anthropic API cost"""
        # Approximate pricing (as of Jan 2025)
        pricing = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
        }
        
        model_pricing = pricing.get(model, pricing["claude-3-5-sonnet-20241022"])
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        cost = (input_tokens / 1000 * model_pricing["input"]) + \
               (output_tokens / 1000 * model_pricing["output"])
        
        return round(cost, 6)


    async def get_code_suggestions(
        self,
        code_context: str,
        task: str,
        language: str = "python",
        provider_preference: List[AIProvider] = None
    ) -> Optional[AIResponse]:
        """
        Get code suggestions using available AI services.
        Tries multiple providers in priority order.
        
        Args:
            code_context: Existing code context
            task: What to implement
            language: Programming language
            provider_preference: Ordered list of providers to try
            
        Returns:
            AIResponse with code suggestions
            
        Example:
            >>> ai = get_ai_helper()
            >>> response = await ai.get_code_suggestions(
            ...     code_context="class MyClass:\n    pass",
            ...     task="Add a method to validate email",
            ...     language="python"
            ... )
        """
        prompt = f"""Given this code context:

```{language}
{code_context}
```

Task: {task}

Please provide the implementation. Include comments and follow best practices for {language}."""

        # Default preference: Claude (better for code) -> OpenAI
        providers = provider_preference or [AIProvider.ANTHROPIC, AIProvider.OPENAI]
        
        for provider in providers:
            try:
                if provider == AIProvider.ANTHROPIC:
                    response = await self.ask_claude(
                        prompt,
                        system_prompt=f"You are an expert {language} developer. Provide clean, well-documented code."
                    )
                elif provider == AIProvider.OPENAI:
                    response = await self.ask_openai(
                        prompt,
                        system_prompt=f"You are an expert {language} developer. Provide clean, well-documented code."
                    )
                else:
                    continue
                
                if response and response.content and not response.error:
                    return response
                    
            except Exception as e:
                logger.warning(f"⚠️  {provider.value} failed: {e}")
                continue
        
        return None
    
    async def review_code(
        self,
        code: str,
        language: str = "python",
        focus_areas: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI code review.
        
        Args:
            code: Code to review
            language: Programming language
            focus_areas: Specific areas to focus on (e.g., ["security", "performance"])
            
        Returns:
            {
                "issues": [...],
                "suggestions": [...],
                "security_concerns": [...],
                "performance_tips": [...]
            }
        """
        focus = focus_areas or ["bugs", "security", "performance", "best_practices"]
        focus_str = ", ".join(focus)
        
        prompt = f"""Review this {language} code for: {focus_str}

```{language}
{code}
```

Provide structured feedback in JSON format with keys:
- issues: List of problems found
- suggestions: List of improvements
- security_concerns: List of security issues
- performance_tips: List of performance improvements

Each item should have: severity (low/medium/high), description, line_number (if applicable)"""

        # Use Claude for code review (better at analysis)
        response = await self.ask_claude(prompt, max_tokens=8192)
        
        if not response or response.error:
            return None
        
        try:
            # Try to parse JSON response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse review response: {e}")
        
        return {"raw_response": response.content}
    
    async def analyze_error(
        self,
        error_message: str,
        stack_trace: Optional[str] = None,
        code_context: Optional[str] = None,
        language: str = "python"
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze error and suggest fixes using AI.
        
        Args:
            error_message: Error message
            stack_trace: Stack trace (optional)
            code_context: Relevant code (optional)
            language: Programming language
            
        Returns:
            {
                "root_cause": "...",
                "suggested_fixes": [...],
                "related_issues": [...],
                "prevention_tips": [...]
            }
        """
        context_parts = [f"Error: {error_message}"]
        
        if stack_trace:
            context_parts.append(f"\nStack trace:\n{stack_trace[:2000]}")
        
        if code_context:
            context_parts.append(f"\nCode context:\n```{language}\n{code_context[:1000]}\n```")
        
        prompt = "\n".join(context_parts) + """

Please analyze this error and provide:
1. Root cause explanation
2. Suggested fixes (step by step)
3. Related issues to check
4. Prevention tips for the future

Format as JSON with keys: root_cause, suggested_fixes (array), related_issues (array), prevention_tips (array)"""

        response = await self.ask_openai(prompt, model="gpt-4o", max_tokens=2048)
        
        if not response or response.error:
            return None
        
        try:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse error analysis: {e}")
        
        return {"raw_response": response.content}
    
    async def generate_documentation(
        self,
        code: str,
        doc_type: str = "docstring",
        language: str = "python"
    ) -> Optional[str]:
        """
        Generate documentation for code.
        
        Args:
            code: Code to document
            doc_type: Type of documentation (docstring, readme, api_doc)
            language: Programming language
            
        Returns:
            Generated documentation
        """
        prompt = f"""Generate {doc_type} documentation for this {language} code:

```{language}
{code}
```

Provide clear, comprehensive documentation following {language} conventions."""

        response = await self.ask_openai(prompt, model="gpt-4o")
        return response.content if response and not response.error else None
    
    async def explain_concept(
        self,
        concept: str,
        context: Optional[str] = None,
        audience_level: str = "intermediate"
    ) -> Optional[str]:
        """
        Get explanation of a technical concept.
        
        Args:
            concept: Concept to explain
            context: Additional context (optional)
            audience_level: beginner, intermediate, or advanced
            
        Returns:
            Explanation text
        """
        context_str = f"\n\nContext: {context}" if context else ""
        
        prompt = f"""Explain the concept of '{concept}' for a {audience_level} developer.{context_str}

Provide:
1. Clear definition
2. Why it's important
3. How it works
4. Common use cases
5. Best practices

Use examples where helpful."""

        response = await self.ask_openai(prompt, model="gpt-4o")
        return response.content if response and not response.error else None


# Singleton instance
_ai_helper: Optional[AIHelper] = None


def get_ai_helper() -> AIHelper:
    """Get or create the global AI helper"""
    global _ai_helper
    if _ai_helper is None:
        _ai_helper = AIHelper()
    return _ai_helper
