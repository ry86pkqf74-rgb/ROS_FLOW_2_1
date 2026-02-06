from __future__ import annotations
import os
from typing import Any, Dict, Optional
import httpx


class LocalOnlyPolicyError(RuntimeError):
    pass


def _require_local_only() -> None:
    policy = (os.getenv("INFERENCE_POLICY") or "local_only").strip().lower()
    if policy not in ("local_only", "local-only"):
        # In this architecture, we default to local-only; do not silently call cloud models.
        raise LocalOnlyPolicyError(f"INFERENCE_POLICY must be local_only, got {policy!r}")


def _pick_base_url() -> str:
    # Align with repo conventions (docker-compose.yml)
    return (
        os.getenv("OLLAMA_URL")
        or os.getenv("OLLAMA_BASE_URL")
        or os.getenv("LOCAL_MODEL_ENDPOINT")
        or "http://ollama:11434"
    )


def _pick_model(model: Optional[str] = None) -> str:
    # Prefer LOCAL_MODEL_NAME (repo default: ai/qwen3-coder:latest), then fall back.
    return model or os.getenv("LOCAL_MODEL_NAME") or os.getenv("OLLAMA_MODEL") or "ai/qwen3-coder:latest"


async def ollama_chat(prompt: str, model: Optional[str] = None) -> str:
    _require_local_only()
    base_url = _pick_base_url()
    model_name = _pick_model(model)

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        r.raise_for_status()
        data: Dict[str, Any] = r.json()
        msg = (data.get("message") or {}).get("content")
        return msg or ""
