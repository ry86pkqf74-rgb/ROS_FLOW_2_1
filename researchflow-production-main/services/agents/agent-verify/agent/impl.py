"""
Claim verification agent: verify claims against a GroundingPack using AI Bridge.
Fail-closed in LIVE: if no evidence quote for a claim, verdict must be fail or unclear (not pass).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from agent.schemas import ClaimVerdict, EvidenceQuote

logger = structlog.get_logger()

# Task type for orchestrator and contract
TASK_TYPE = "CLAIM_VERIFY"

# Default task type for AI Bridge
AI_BRIDGE_TASK_TYPE = "CLAIM_VERIFY"


def _ai_bridge_url() -> str:
    return (
        os.getenv("AI_BRIDGE_URL")
        or os.getenv("ORCHESTRATOR_INTERNAL_URL")
        or os.getenv("ORCHESTRATOR_URL")
        or "http://localhost:3001"
    ).rstrip("/")


def _auth_token() -> str:
    return os.getenv("AI_BRIDGE_TOKEN") or os.getenv("WORKER_SERVICE_TOKEN") or ""


async def _invoke_bridge(
    prompt: str,
    governance_mode: str = "DEMO",
    request_id: str = "verify",
    max_tokens: int = 2000,
) -> str:
    """Call AI Bridge /api/ai-bridge/invoke; returns content string. No provider SDKs."""
    base = _ai_bridge_url()
    token = _auth_token()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "prompt": prompt,
        "options": {
            "taskType": AI_BRIDGE_TASK_TYPE,
            "modelTier": "STANDARD",
            "governanceMode": governance_mode,
            "requirePhiCompliance": False,
            "maxTokens": max_tokens,
        },
        "metadata": {
            "agentId": "agent-verify",
            "projectId": "researchflow",
            "runId": request_id,
            "threadId": "thread-verify",
            "stageRange": [1, 20],
            "currentStage": 1,
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{base}/api/ai-bridge/invoke",
            json=payload,
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        content = (data.get("content") or data.get("text") or "").strip()
        return content or ""


def _chunks_from_grounding(grounding: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract list of chunks (id + text) from GroundingPack. Prefer sources[].id or chunkId."""
    if not grounding:
        return []
    sources = grounding.get("sources") or []
    out: List[Dict[str, Any]] = []
    for s in sources:
        if not isinstance(s, dict):
            continue
        chunk_id = s.get("id") or s.get("chunkId") or s.get("chunk_id")
        text = s.get("text") or s.get("content") or ""
        if chunk_id and isinstance(chunk_id, str):
            out.append({"id": chunk_id, "text": str(text)[:8000]})
        elif text:
            out.append({"id": f"chunk_{len(out)}", "text": str(text)[:8000]})
    return out


def _apply_fail_closed_live(
    verdicts: List[ClaimVerdict],
    governance_mode: str,
) -> List[ClaimVerdict]:
    """In LIVE mode: any claim with no evidence quote must be fail or unclear (not pass)."""
    if governance_mode.upper() != "LIVE":
        return verdicts
    result: List[ClaimVerdict] = []
    for v in verdicts:
        has_evidence = any(
            (e.quote and e.quote.strip()) for e in (v.evidence or [])
        )
        if v.verdict == "pass" and not has_evidence:
            result.append(
                ClaimVerdict(
                    claim=v.claim,
                    verdict="unclear",
                    evidence=v.evidence or [],
                )
            )
        else:
            result.append(v)
    return result


def _parse_llm_verdicts(raw: str, claims: List[str]) -> List[ClaimVerdict]:
    """Parse LLM response into ClaimVerdict list. Tolerates JSON block or line-based format."""
    verdicts: List[ClaimVerdict] = []
    raw = (raw or "").strip()
    # Try JSON array
    if raw.startswith("["):
        try:
            arr = json.loads(raw)
            for i, item in enumerate(arr):
                if not isinstance(item, dict):
                    continue
                claim = item.get("claim") or (claims[i] if i < len(claims) else "")
                v = (item.get("verdict") or "unclear").lower()
                if v not in ("pass", "fail", "unclear"):
                    v = "unclear"
                ev = item.get("evidence") or []
                evidence = [
                    EvidenceQuote(
                        chunk_id=str(e.get("chunk_id") or e.get("chunkId") or ""),
                        quote=str(e.get("quote") or ""),
                    )
                    for e in ev
                    if isinstance(e, dict)
                ]
                verdicts.append(ClaimVerdict(claim=claim, verdict=v, evidence=evidence))
            return verdicts
        except json.JSONDecodeError:
            pass
    # Fallback: one verdict per claim as unclear
    for c in claims:
        verdicts.append(
            ClaimVerdict(claim=c, verdict="unclear", evidence=[])
        )
    return verdicts


async def _execute_verify(inputs: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """
    Verify claims against grounding pack. Uses AI Bridge for LLM when available.
    LIVE: fail-closed — no evidence quote for a claim -> verdict fail/unclear (not pass).
    """
    claims = inputs.get("claims") or []
    grounding_pack = inputs.get("groundingPack") or inputs.get("grounding_pack")
    governance_mode = (inputs.get("governanceMode") or inputs.get("governance_mode") or mode or "DEMO").strip()
    strictness = (inputs.get("strictness") or "normal").strip().lower()

    if not claims:
        return {
            "claim_verdicts": [],
            "overallPass": True,
        }

    chunks = _chunks_from_grounding(grounding_pack)
    context = "\n\n".join(
        f"[{c['id']}]\n{c['text']}" for c in chunks
    ) if chunks else "(no grounding chunks provided)"

    # LIVE with no grounding: fail-closed, no LLM call
    if governance_mode.upper() == "LIVE" and not chunks:
        claim_verdicts = [
            ClaimVerdict(claim=c, verdict="unclear", evidence=[])
            for c in claims
        ]
        return {
            "claim_verdicts": [v.model_dump(by_alias=True) for v in claim_verdicts],
            "overallPass": False,
        }

    # DEMO with no bridge or no chunks: stub verdicts (first claim pass with first chunk if any, else unclear)
    use_bridge = bool(_ai_bridge_url() and chunks)
    if governance_mode.upper() == "DEMO" and not use_bridge:
        claim_verdicts: List[ClaimVerdict] = []
        for i, claim in enumerate(claims):
            if chunks and i == 0 and strictness != "strict":
                ev = [EvidenceQuote(chunk_id=chunks[0]["id"], quote=(chunks[0].get("text") or "")[:200])]
                claim_verdicts.append(ClaimVerdict(claim=claim, verdict="pass", evidence=ev))
            else:
                claim_verdicts.append(ClaimVerdict(claim=claim, verdict="unclear", evidence=[]))
        applied = _apply_fail_closed_live(claim_verdicts, governance_mode)
        return {
            "claim_verdicts": [v.model_dump(by_alias=True) for v in applied],
            "overallPass": all(v.verdict == "pass" for v in applied),
        }

    # Build prompt for AI Bridge
    prompt = f"""You are a fact-checker. Given the following GROUNDING CONTEXT (chunks with ids) and a list of CLAIMS, for each claim output:
1) verdict: one of pass, fail, unclear (pass = supported by evidence, fail = contradicted or unsupported, unclear = cannot determine)
2) evidence: list of {{ "chunk_id": "<id>", "quote": "<exact or near-exact quote from that chunk>" }}. Only include quotes that actually support or contradict the claim.

GROUNDING CONTEXT:
{context}

CLAIMS TO VERIFY:
"""
    for i, c in enumerate(claims, 1):
        prompt += f"{i}. {c}\n"

    prompt += """
Respond with a JSON array only, one object per claim, each with keys: "claim", "verdict" (pass|fail|unclear), "evidence" (array of { "chunk_id": "...", "quote": "..." }). No other text.
"""

    try:
        raw = await _invoke_bridge(prompt, governance_mode=governance_mode, max_tokens=2500)
    except Exception as e:
        logger.warning("verify_bridge_invoke_failed", error=str(type(e).__name__))
        # On bridge failure: all unclear (fail-closed)
        claim_verdicts = [
            ClaimVerdict(claim=c, verdict="unclear", evidence=[])
            for c in claims
        ]
        applied = _apply_fail_closed_live(claim_verdicts, governance_mode)
        return {
            "claim_verdicts": [v.model_dump(by_alias=True) for v in applied],
            "overallPass": False,
        }

    claim_verdicts = _parse_llm_verdicts(raw, claims)
    if len(claim_verdicts) != len(claims):
        # Pad or trim to match claims
        out: List[ClaimVerdict] = []
        for i, c in enumerate(claims):
            if i < len(claim_verdicts):
                out.append(claim_verdicts[i])
            else:
                out.append(ClaimVerdict(claim=c, verdict="unclear", evidence=[]))
        claim_verdicts = out

    applied = _apply_fail_closed_live(claim_verdicts, governance_mode)
    return {
        "claim_verdicts": [v.model_dump(by_alias=True) for v in applied],
        "overallPass": all(v.verdict == "pass" for v in applied),
    }


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous agent execution for claim verification."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    logger.info(
        "agent_sync_start",
        request_id=request_id,
        task_type=task_type,
    )

    outputs = await _execute_verify(inputs, mode)

    logger.info(
        "agent_sync_complete",
        request_id=request_id,
        task_type=task_type,
    )

    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
        "artifacts": [],
        "provenance": {"governance_mode": mode},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming agent execution with SSE events."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    logger.info(
        "agent_stream_start",
        request_id=request_id,
        task_type=task_type,
    )

    yield {
        "type": "started",
        "request_id": request_id,
        "task_type": task_type,
    }

    yield {
        "type": "progress",
        "request_id": request_id,
        "progress": 50,
        "step": "verifying_claims",
    }

    outputs = await _execute_verify(inputs, mode)

    yield {
        "type": "final",
        "request_id": request_id,
        "task_type": task_type,
        "status": "ok",
        "success": True,
        "outputs": outputs,
        "duration_ms": 0,
    }

    logger.info(
        "agent_stream_complete",
        request_id=request_id,
        task_type=task_type,
    )
