"""AI Bridge invocation for section writer. No provider SDKs."""
from __future__ import annotations

import os
from typing import Any, Dict

import httpx


def _ai_bridge_url() -> str:
    return (
        os.getenv("AI_BRIDGE_URL")
        or os.getenv("ORCHESTRATOR_INTERNAL_URL")
        or os.getenv("ORCHESTRATOR_URL")
        or "http://localhost:3001"
    ).rstrip("/")


def _auth_token() -> str:
    return os.getenv("AI_BRIDGE_TOKEN") or os.getenv("WORKER_SERVICE_TOKEN") or ""


async def invoke_ai_bridge(
    prompt: str,
    options: Dict[str, Any],
    metadata: Dict[str, Any],
    *,
    timeout: float = 120.0,
) -> str:
    """
    POST to orchestrator /api/ai-bridge/invoke. Returns LLM content string.

    Args:
        prompt: User/system prompt (caller may combine system + user).
        options: Bridge options (taskType, modelTier, governanceMode, maxTokens, etc.).
        metadata: Agent metadata (agentId, runId, projectId, etc.).
        timeout: Request timeout in seconds.

    Returns:
        content string from bridge response (content or text field).
    """
    base = _ai_bridge_url()
    token = _auth_token()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "prompt": prompt,
        "options": options,
        "metadata": metadata,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{base}/api/ai-bridge/invoke",
            json=payload,
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        content = (data.get("content") or data.get("text") or "").strip()
        return content or ""
