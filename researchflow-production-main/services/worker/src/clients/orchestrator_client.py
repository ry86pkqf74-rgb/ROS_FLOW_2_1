"""
Orchestrator client for worker-side HITL edit session operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import os


class OrchestratorClient:
    """Minimal client wrapper used by worker HITL nodes."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("ORCHESTRATOR_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("ORCHESTRATOR_API_KEY", "")
        self.session = session

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def create_edit_session(
        self,
        *,
        run_id: str,
        trace_id: str,
        node_id: str,
        attempt: int,
        dedupe_key: str,
    ) -> Dict[str, Any]:
        if not self.base_url:
            raise ValueError("ORCHESTRATOR_URL not configured")
        import requests

        payload = {
            "run_id": run_id,
            "trace_id": trace_id,
            "node_id": node_id,
            "attempt": attempt,
            "dedupe_key": dedupe_key,
        }
        response = requests.post(
            f"{self.base_url}/api/worker/edit-sessions",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_edit_session(self, edit_session_id: str) -> Dict[str, Any]:
        if not self.base_url:
            raise ValueError("ORCHESTRATOR_URL not configured")
        import requests

        response = requests.get(
            f"{self.base_url}/api/worker/edit-sessions/{edit_session_id}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


def get_orchestrator_client() -> Optional[OrchestratorClient]:
    """Return a client only when configured; otherwise None."""
    base_url = os.environ.get("ORCHESTRATOR_URL", "").strip()
    if not base_url:
        return None
    return OrchestratorClient(base_url=base_url)
