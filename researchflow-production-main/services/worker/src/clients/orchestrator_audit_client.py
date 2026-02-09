"""
Worker-side client to send audit events to the orchestrator internal audit ingest endpoint.

Expected orchestrator contract:
- POST to {ORCHESTRATOR_BASE_URL}/api/internal/audit/ingest (or equivalent internal route)
- Header: x-internal-api-key: {INTERNAL_API_KEY}
- Body: JSON object with audit event fields. If present, 'dedupe_key' is sent unchanged
  for idempotency (orchestrator may use it to deduplicate).
- Responses: 2xx success; 5xx or network errors are retried with exponential backoff.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

if not _HAS_REQUESTS:
    import urllib.error
    import urllib.request


# Keys we keep in minimize_payload (IDs, hashes, small identifiers)
_MINIMIZE_KEEP_KEYS = frozenset({
    "id", "ids", "job_id", "run_id", "trace_id", "span_id", "hash", "hashes",
    "dedupe_key", "event_type", "action", "stage", "status", "code", "error_code",
})
# Approximate max character length for a string value before we drop it in minimize_payload
_MINIMIZE_MAX_STR_LEN = 256


def _get_config() -> tuple[str, str, float]:
    base = os.environ.get("ORCHESTRATOR_BASE_URL", "").rstrip("/")
    key = os.environ.get("INTERNAL_API_KEY", "")
    if not base or not key:
        raise ValueError(
            "ORCHESTRATOR_BASE_URL and INTERNAL_API_KEY must be set to emit audit events"
        )
    timeout = float(os.environ.get("ORCHESTRATOR_AUDIT_TIMEOUT_SECS", "5"))
    return base, key, timeout


def _make_payload_json_serializable(obj: Any) -> Any:
    """Convert non-JSON-serializable values to strings so payload_json is safe."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {k: _make_payload_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_payload_json_serializable(x) for x in obj]
    return str(obj)


def minimize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    PHI-safe default: drop large text fields, keep IDs/hashes and small identifiers.
    Does not perform complex redaction; that is left to later layers.
    """
    out: dict[str, Any] = {}
    for k, v in payload.items():
        key_lower = k.lower()
        if key_lower in _MINIMIZE_KEEP_KEYS:
            out[k] = v
            continue
        if isinstance(v, str) and len(v) <= _MINIMIZE_MAX_STR_LEN:
            out[k] = v
        elif isinstance(v, (int, float, bool, type(None))):
            out[k] = v
        elif isinstance(v, dict):
            out[k] = minimize_payload(v)
        elif isinstance(v, (list, tuple)) and len(v) <= 32:
            out[k] = [
                minimize_payload(x) if isinstance(x, dict) else x
                for x in v[:32]
            ]
        # else: drop long strings, large lists, etc.
    return out


def _ingest_url(base: str) -> str:
    return f"{base}/api/internal/audit/ingest"


def emit_audit_event(event: dict[str, Any]) -> dict[str, Any] | None:
    """
    Send an audit event to the orchestrator internal ingest endpoint.

    - Reads ORCHESTRATOR_BASE_URL, INTERNAL_API_KEY; optional ORCHESTRATOR_AUDIT_TIMEOUT_SECS (default 5).
    - Uses retries with exponential backoff (3 attempts) for 5xx and network errors.
    - If event contains 'dedupe_key', it is sent through unchanged for idempotency.
    - Payload is made JSON-serializable (non-serializable values converted to strings).

    Returns:
        Response data as dict (e.g. {"ok": True}) on success, or None if caller only needs fire-and-forget.
    """
    base, key, timeout = _get_config()
    url = _ingest_url(base)
    payload = dict(event)
    payload = _make_payload_json_serializable(payload)
    headers = {
        "Content-Type": "application/json",
        "x-internal-api-key": key,
    }
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            if _HAS_REQUESTS:
                resp = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                if resp.status_code >= 500 or resp.status_code == 408:
                    raise _Retryable(resp.status_code, resp.text)
                resp.raise_for_status()
                return resp.json() if resp.content else None
            else:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    code = resp.status
                    body = resp.read().decode("utf-8")
                if code >= 500 or code == 408:
                    raise _Retryable(code, body)
                if code >= 400:
                    raise RuntimeError(f"audit ingest returned {code}: {body}")
                return json.loads(body) if body.strip() else None
        except _Retryable as e:
            last_exc = e
        except (OSError, ConnectionError, TimeoutError) as e:
            last_exc = e
        except Exception as e:
            if _is_retryable(e):
                last_exc = e
            else:
                raise
        if attempt < 2:
            time.sleep(2**attempt)
    raise RuntimeError(f"audit emit failed after 3 attempts: {last_exc}") from last_exc


class _Retryable(Exception):
    def __init__(self, status_code: int, body: str = ""):
        self.status_code = status_code
        self.body = body
        super().__init__(f"status {status_code}: {body[:200]}")


def _is_retryable(e: Exception) -> bool:
    if _HAS_REQUESTS and hasattr(requests.exceptions, "RequestException"):
        return isinstance(e, requests.exceptions.RequestException)
    return isinstance(e, (urllib.error.URLError, urllib.error.HTTPError)) if not _HAS_REQUESTS else False
