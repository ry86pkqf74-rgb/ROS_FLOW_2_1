from __future__ import annotations

import logging
import os

from src.llm.providers.anthropic_provider import AnthropicProvider
from src.llm.providers.base import LLMResult
from src.llm.providers.mercury_provider import MercuryProvider
from src.llm.providers.mock import MockProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.providers.xai_provider import XAIProvider
from src.runtime_config import RuntimeConfig

logger = logging.getLogger("llm.router")


def _select_provider(name: str):
    n = name.strip().lower()
    if n == "openai":
        return OpenAIProvider()
    if n == "anthropic":
        return AnthropicProvider()
    if n == "xai":
        return XAIProvider()
    if n == "mercury":
        return MercuryProvider()
    return MockProvider()


def _get_bridge_provider_mode() -> str:
    """Return the AI Bridge provider mode: mock | shadow | real."""
    return os.getenv("AI_BRIDGE_PROVIDER_MODE", "mock").strip().lower()


def generate_text(
    *,
    task_name: str,
    prompt: str,
    system_prompt: str | None,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> LLMResult:
    """
    One entry point for draft-generation or summarization calls.

    Provider selection respects AI_BRIDGE_PROVIDER_MODE:
      mock   -> always MockProvider (default, zero cost)
      shadow -> MockProvider result returned, real provider called
                in background and logged for comparison
      real   -> real provider selected via LLM_PROVIDER env

    Within 'real' mode the provider is selected via:
      1) RuntimeConfig.llm_provider (env LLM_PROVIDER)
      2) fallback to env LLM_PROVIDER
      3) fallback to mock
    """
    bridge_mode = _get_bridge_provider_mode()
    logger.info("generate_text mode=%s task=%s model=%s", bridge_mode, task_name, model)

    if bridge_mode == "mock":
        return MockProvider().generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    cfg = RuntimeConfig.from_env_and_optional_yaml(None)
    provider_name = cfg.llm_provider or os.getenv("LLM_PROVIDER") or "mock"
    real_provider = _select_provider(provider_name)

    if bridge_mode == "shadow":
        # Return mock, but also fire real call for comparison logging
        mock_result = MockProvider().generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            real_result = real_provider.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(
                "shadow-mode real response provider=%s tokens_in=%d tokens_out=%d",
                real_result.provider,
                real_result.usage.input_tokens,
                real_result.usage.output_tokens,
            )
        except Exception:
            logger.warning("shadow-mode real call failed", exc_info=True)
        return mock_result

    # mode == 'real'
    return real_provider.generate_text(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
