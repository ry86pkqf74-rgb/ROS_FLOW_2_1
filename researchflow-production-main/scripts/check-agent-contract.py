#!/usr/bin/env python3
"""
Agent contract conformance check. Hits /agents/run/sync and /agents/run/stream
for each base URL in AGENT_CONTRACT_URLS and validates response/event shape.

Usage:
  AGENT_CONTRACT_URLS=http://localhost:8000,http://localhost:8001 python3 scripts/check-agent-contract.py

Requires: AGENT_CONTRACT_URLS (comma-separated agent base URLs). Exits 2 if unset.
Uses Python stdlib only (no extra dependencies). PHI-safe: never prints request/response bodies on success.
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


def make_body(n: int = 1) -> bytes:
    return json.dumps({
        "request_id": f"contract-check-{n}",
        "task_type": "CONTRACT_CHECK",
        "inputs": {},
    }).encode("utf-8")


def get_agent_urls() -> list[str]:
    raw = os.environ.get("AGENT_CONTRACT_URLS", "").strip()
    if not raw:
        print("Error: AGENT_CONTRACT_URLS is not set.", file=sys.stderr)
        print("Example: AGENT_CONTRACT_URLS=http://localhost:8000,http://localhost:8001 python3 scripts/check-agent-contract.py", file=sys.stderr)
        sys.exit(2)
    return [u.strip() for u in raw.split(",") if u.strip()]


def has_success_indicator(obj: dict) -> bool:
    if obj.get("ok") is True:
        return True
    if obj.get("status") in ("ok", "success"):
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


def validate_sync_response(data: dict, status_code: int) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "response is not a JSON object"
    rid = data.get("request_id")
    if not (isinstance(rid, str) and rid):
        return False, "missing or invalid request_id"
    if not has_outputs_or_data(data):
        return False, "missing outputs or data object"
    if not has_success_indicator(data):
        return False, "missing success indicator (ok=true or status in ['ok','success'])"
    return True, ""


def sync_check(base: str, n: int = 1) -> tuple[bool, str]:
    url = base.rstrip("/") + "/agents/run/sync"
    req = Request(url, data=make_body(n), headers=HEADERS, method="POST")
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


def stream_check(base: str, n: int = 1) -> tuple[bool, str]:
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
        conn.request("POST", path or "/agents/run/stream", make_body(n), HEADERS)
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
        terminal_names = ("complete", "done", "final")
        terminal = None
        for e in events:
            if e.get("event") in terminal_names:
                terminal = e.get("data")
        if not terminal and events:
            terminal = events[-1].get("data")
        if not isinstance(terminal, dict):
            return False, "no terminal event with parsed JSON"
        if not (isinstance(terminal.get("request_id"), str) and terminal.get("request_id")):
            return False, "terminal event missing request_id"
        if not has_success_indicator(terminal):
            return False, "terminal event missing success indicator"
        if not has_outputs_or_data(terminal):
            return False, "terminal event missing outputs or data"
        return True, ""
    except HTTPException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def main() -> int:
    urls = get_agent_urls()
    results: list[tuple[str, bool, str, bool, str]] = []
    for i, base in enumerate(urls, start=1):
        sync_ok, sync_msg = sync_check(base, n=i)
        stream_ok, stream_msg = stream_check(base, n=i)
        results.append((base, sync_ok, sync_msg, stream_ok, stream_msg))
    # Table
    print("Agent contract check summary")
    print("-" * 72)
    for base, sync_ok, sync_msg, stream_ok, stream_msg in results:
        sync_s = "PASS" if sync_ok else "FAIL"
        stream_s = "PASS" if stream_ok else "FAIL"
        print(f"  {base}")
        print(f"    SYNC:   {sync_s}")
        if not sync_ok and sync_msg:
            print(f"           {sync_msg[:200]}")
        print(f"    STREAM: {stream_s}")
        if not stream_ok and stream_msg:
            print(f"           {stream_msg[:200]}")
        print()
    failed = any(not sync_ok or not stream_ok for _, sync_ok, _, stream_ok, _ in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
