#!/usr/bin/env python3
"""
Agent contract conformance check. For each target in AGENT_CONTRACT_TARGETS:
  - GET /health and GET /health/ready: validate JSON has required keys and types
  - POST /agents/run/sync (and /agents/run/stream): validate response JSON envelope and types

Usage:
   AGENT_CONTRACT_TARGETS=http://agent-lit-retrieval:8000=LIT_RETRIEVAL,http://agent-policy-review:8000=POLICY_REVIEW,http://agent-rag-ingest:8000=RAG_INGEST python3 scripts/check-agent-contract.py

Requires: AGENT_CONTRACT_TARGETS (comma-separated baseUrl=task_type). Exits 2 if unset.
Uses Python stdlib; optional: if jsonschema is installed, validates sync response against
docs/agent_response_schema.json (same schema used by the RAG retrieve agent). PHI-safe: never prints request/response bodies on success.
"""

from __future__ import annotations

import json
import os
import sys
import time
from http.client import HTTPConnection, HTTPException, HTTPResponse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# --- config ---
SYNC_TIMEOUT = 15
STREAM_OVERALL_TIMEOUT = 30
STREAM_IDLE_TIMEOUT = 10
STREAM_FIRST_EVENT_TIMEOUT = 10
HEADERS = {"Content-Type": "application/json"}


LIT_RETRIEVAL_QUERY_FALLBACK = "contract-check query"


def get_body_dict(n: int, task_type: str) -> dict:
    """Build request body dict. For LIT_RETRIEVAL/RAG_RETRIEVE sets inputs.query; for RAG_INGEST sets inputs for ingest."""
    inputs: dict = {}
    if task_type == "LIT_RETRIEVAL":
        research_question = (os.environ.get("RESEARCH_QUESTION") or "").strip()
        existing_query = ""  # contract script builds from scratch; no prior inputs
        query = research_question or existing_query or LIT_RETRIEVAL_QUERY_FALLBACK
        inputs["query"] = query.strip() or LIT_RETRIEVAL_QUERY_FALLBACK
    elif task_type == "RAG_RETRIEVE":
        inputs["query"] = (os.environ.get("RAG_RETRIEVE_QUERY") or "contract-check query").strip() or "contract-check query"
        inputs["knowledgeBase"] = os.environ.get("RAG_RETRIEVE_KB", "default")
        inputs["topK"] = 5
        inputs["domainId"] = os.environ.get("RAG_RETRIEVE_DOMAIN_ID", "default")
        inputs["projectId"] = os.environ.get("RAG_RETRIEVE_PROJECT_ID", "default")
    elif task_type == "RAG_INGEST":
        # Minimal payload: no documents so no embedding/Chroma write; agent returns 0 ingested
        inputs["documents"] = []
        inputs["knowledgeBase"] = "contract-check"
        inputs["domainId"] = "default"
        inputs["projectId"] = "default"
    elif task_type == "CLAIM_VERIFY":
        inputs["claims"] = ["Contract check claim."]
        inputs["groundingPack"] = {"sources": [{"id": "c1", "text": "Sample grounding text."}]}
        inputs["governanceMode"] = "DEMO"
        inputs["strictness"] = "normal"
    return {
        "request_id": f"contract-check-{n}",
        "task_type": task_type,
        "inputs": inputs,
    }


def ensure_lit_retrieval_has_query(body_dict: dict, task_type: str) -> None:
    """Exit with code 1 if LIT_RETRIEVAL payload is missing or empty inputs.query."""
    if task_type != "LIT_RETRIEVAL":
        return
    inputs = body_dict.get("inputs")
    query = inputs.get("query") if isinstance(inputs, dict) else None
    if not (isinstance(query, str) and query.strip()):
        print("Error: LIT_RETRIEVAL request must include non-empty inputs.query.", file=sys.stderr)
        sys.exit(1)


def ensure_rag_retrieve_has_query(body_dict: dict, task_type: str) -> None:
    """Exit with code 1 if RAG_RETRIEVE payload is missing or empty inputs.query."""
    if task_type != "RAG_RETRIEVE":
        return
    inputs = body_dict.get("inputs")
    query = inputs.get("query") if isinstance(inputs, dict) else None
    if not (isinstance(query, str) and query.strip()):
        print("Error: RAG_RETRIEVE request must include non-empty inputs.query.", file=sys.stderr)
        sys.exit(1)


def make_body(n: int, task_type: str) -> bytes:
    body = get_body_dict(n, task_type)
    return json.dumps(body).encode("utf-8")


def get_agent_targets() -> list[tuple[str, str]]:
    raw = os.environ.get("AGENT_CONTRACT_TARGETS", "").strip()
    if not raw:
        print("Error: AGENT_CONTRACT_TARGETS is not set.", file=sys.stderr)
        print("Example: AGENT_CONTRACT_TARGETS=http://agent-lit-retrieval:8000=LIT_RETRIEVAL,http://agent-rag-retrieve:8000=RAG_RETRIEVE,http://agent-policy-review:8000=POLICY_REVIEW python3 scripts/check-agent-contract.py", file=sys.stderr)
        sys.exit(2)
    out: list[tuple[str, str]] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            print("Error: AGENT_CONTRACT_TARGETS entries must be baseUrl=task_type.", file=sys.stderr)
            sys.exit(2)
        base, task_type = entry.split("=", 1)
        out.append((base.strip(), task_type.strip()))
    return out


def has_success_indicator(obj: dict) -> bool:
    if obj.get("ok") is True:
        return True
    if obj.get("status") in ("ok", "success"):
        return True
    if obj.get("success") is True:
        return True
    return False


def has_outputs_or_data(obj: dict) -> bool:
    out = obj.get("outputs")
    if out is not None and isinstance(out, dict):
        return True
    data = obj.get("data")
    if data is not None and isinstance(data, dict):
        return True
    return False


def _validate_against_canonical_schema(data: dict) -> tuple[bool, str]:
    """Optional: validate sync response against docs/agent_response_schema.json (requires jsonschema)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(script_dir, "..", "docs", "agent_response_schema.json")
    if not os.path.isfile(schema_path):
        return True, ""
    try:
        import jsonschema
    except ImportError:
        return True, ""
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    try:
        jsonschema.validate(data, schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"canonical schema validation failed: {getattr(e, 'message', str(e))}"


def validate_sync_response(data: dict, status_code: int) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "response is not a JSON object"
    rid = data.get("request_id")
    if not (isinstance(rid, str) and rid):
        return False, "missing or invalid request_id (must be non-empty string)"
    if not has_outputs_or_data(data):
        return False, "missing outputs or data object"
    out = data.get("outputs") if data.get("outputs") is not None else data.get("data")
    if out is not None and not isinstance(out, dict):
        return False, "outputs/data must be a JSON object"
    st = data.get("status")
    if st is not None and not isinstance(st, str):
        return False, "status must be a string"
    if not has_success_indicator(data):
        return False, "missing success indicator (ok=true or status in ['ok','success'])"
    ok, msg = _validate_against_canonical_schema(data)
    if not ok:
        return False, msg
    return True, ""


def validate_health_like(data: dict, endpoint: str) -> tuple[bool, str]:
    """Validate JSON from /health or /health/ready: required key 'status' (string)."""
    if not isinstance(data, dict):
        return False, f"{endpoint}: response is not a JSON object"
    status = data.get("status")
    if status is None:
        return False, f"{endpoint}: missing key 'status'"
    if not isinstance(status, str):
        return False, f"{endpoint}: 'status' must be a string, got {type(status).__name__}"
    return True, ""


def health_check(base: str) -> tuple[bool, str]:
    url = base.rstrip("/") + "/health"
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, f"/health status {e.code}. {raw[:200]!r}"
    except URLError as e:
        return False, f"request failed: {e.reason}"
    except Exception as e:
        return False, str(e)
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return False, "/health: invalid JSON"
    ok, msg = validate_health_like(data, "/health")
    return ok, msg


def ready_check(base: str) -> tuple[bool, str]:
    url = base.rstrip("/") + "/health/ready"
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, f"/health/ready status {e.code}. {raw[:200]!r}"
    except URLError as e:
        return False, f"request failed: {e.reason}"
    except Exception as e:
        return False, str(e)
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return False, "/health/ready: invalid JSON"
    ok, msg = validate_health_like(data, "/health/ready")
    return ok, msg


def sync_check(base: str, task_type: str, n: int = 1) -> tuple[bool, str]:
    url = base.rstrip("/") + "/agents/run/sync"
    req = Request(url, data=make_body(n, task_type), headers=HEADERS, method="POST")
    try:
        with urlopen(req, timeout=SYNC_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.getcode()
    except HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8") if e.fp else ""
    except URLError as e:
        return False, f"request failed: {e.reason}"
    except Exception as e:
        return False, str(e)
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        snippet = (raw[:500] + "..." if len(raw) > 500 else raw) if raw else "(empty)"
        return False, f"invalid JSON (status {code}). snippet: {snippet!r}"
    ok, msg = validate_sync_response(data, code)
    if ok:
        return True, ""
    snippet = json.dumps(data)[:500] + ("..." if len(json.dumps(data)) > 500 else "")
    return False, f"status {code}; {msg}. snippet: {snippet!r}"


def parse_sse_line(line: str) -> tuple[str | None, str | None]:
    line = line.rstrip("\r\n")
    if line.startswith("event:"):
        return line[6:].strip(), None
    if line.startswith("data:"):
        return None, line[5:] if len(line) == 5 else line[5:].lstrip(" ")
    return None, None


def stream_check(base: str, task_type: str, n: int = 1) -> tuple[bool, str]:
    from urllib.parse import urlparse
    parsed = urlparse(base.rstrip("/"))
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = (parsed.path or "/").rstrip("/") + "/agents/run/stream"
    if parsed.scheme == "https":
        from http.client import HTTPSConnection
        conn = HTTPSConnection(host, port, timeout=STREAM_OVERALL_TIMEOUT)
    else:
        conn = HTTPConnection(host, port, timeout=STREAM_OVERALL_TIMEOUT)
    try:
        conn.request("POST", path or "/agents/run/stream", make_body(n, task_type), HEADERS)
        resp: HTTPResponse = conn.getresponse()
        if resp.status != 200:
            raw = resp.read().decode("utf-8", errors="replace")
            snippet = (raw[:500] + "..." if len(raw) > 500 else raw) if raw else "(empty)"
            return False, f"status {resp.status}. snippet: {snippet!r}"
        # Set idle timeout on underlying socket when available
        if hasattr(resp, "fp") and resp.fp is not None and hasattr(resp.fp, "settimeout"):
            resp.fp.settimeout(STREAM_IDLE_TIMEOUT)
        events: list[dict] = []
        current_event: str | None = None
        current_data: list[str] = []
        start = time.monotonic()
        first_event_at: float | None = None
        while True:
            elapsed = time.monotonic() - start
            if elapsed > STREAM_OVERALL_TIMEOUT:
                break
            line = resp.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            ev, data_part = parse_sse_line(line_str)
            if ev is not None:
                current_event = ev
            if data_part is not None:
                current_data.append(data_part)
            if line_str.strip() == "" and (current_event is not None or current_data):
                # End of event
                data_joined = "\n".join(current_data) if current_data else "{}"
                current_data = []
                try:
                    data_obj = json.loads(data_joined) if data_joined.strip() else {}
                except json.JSONDecodeError:
                    data_obj = {}
                events.append({"event": current_event or "message", "data": data_obj})
                if first_event_at is None:
                    first_event_at = time.monotonic()
                current_event = None
        if first_event_at is not None and first_event_at - start > STREAM_FIRST_EVENT_TIMEOUT:
            return False, "first event received after 10s"
        if not events:
            return False, "no events received within timeout"
        has_rid = any(
            isinstance(e.get("data"), dict) and isinstance(e["data"].get("request_id"), str) and e["data"].get("request_id")
            for e in events
        )
        if not has_rid:
            return False, "no event contained request_id"
        # Invariant: exactly one terminal event = the last event. It MUST include request_id, task_type, status.
        terminal = events[-1].get("data") if events else None
        if not isinstance(terminal, dict):
            return False, "no terminal event with parsed JSON"
        if not (isinstance(terminal.get("request_id"), str) and terminal.get("request_id")):
            return False, "terminal event missing request_id"
        if not (isinstance(terminal.get("task_type"), str) and terminal.get("task_type")):
            return False, "terminal event missing task_type"
        if not (isinstance(terminal.get("status"), str) and terminal.get("status")):
            return False, "terminal event missing status"
        if not has_success_indicator(terminal):
            return False, "terminal event missing success indicator"
        if not has_outputs_or_data(terminal):
            return False, "terminal event missing outputs or data"
        # Optional: last event should be a named terminal type to avoid ending on progress/started
        terminal_names = ("complete", "done", "final")
        if events and events[-1].get("event") not in terminal_names:
            return False, "stream must end with a terminal event type (complete, done, or final)"
        return True, ""
    except HTTPException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def main() -> int:
    targets = get_agent_targets()
    results: list[tuple[str, bool, str, bool, str, bool, str, bool, str]] = []
    for i, (base, task_type) in enumerate(targets, start=1):
        body_dict = get_body_dict(i, task_type)
        ensure_lit_retrieval_has_query(body_dict, task_type)
        ensure_rag_retrieve_has_query(body_dict, task_type)
        health_ok, health_msg = health_check(base)
        ready_ok, ready_msg = ready_check(base)
        sync_ok, sync_msg = sync_check(base, task_type, n=i)
        stream_ok, stream_msg = stream_check(base, task_type, n=i)
        results.append((base, health_ok, health_msg, ready_ok, ready_msg, sync_ok, sync_msg, stream_ok, stream_msg))
    # Table
    print("Agent contract check summary")
    print("-" * 72)
    for base, health_ok, health_msg, ready_ok, ready_msg, sync_ok, sync_msg, stream_ok, stream_msg in results:
        def _s(ok: bool) -> str:
            return "PASS" if ok else "FAIL"
        print(f"  {base}")
        print(f"    /health:       {_s(health_ok)}")
        if not health_ok and health_msg:
            print(f"                  {health_msg[:200]}")
        print(f"    /health/ready: {_s(ready_ok)}")
        if not ready_ok and ready_msg:
            print(f"                  {ready_msg[:200]}")
        print(f"    /run (sync):   {_s(sync_ok)}")
        if not sync_ok and sync_msg:
            print(f"                  {sync_msg[:200]}")
        print(f"    /run (stream): {_s(stream_ok)}")
        if not stream_ok and stream_msg:
            print(f"                  {stream_msg[:200]}")
        print()
    failed = any(
        not health_ok or not ready_ok or not sync_ok or not stream_ok
        for _, health_ok, _, ready_ok, _, sync_ok, _, stream_ok, _ in results
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
