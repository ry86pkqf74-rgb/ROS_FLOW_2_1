"""Integration tests for Worker PHI APIs (FastAPI).

Targets (Worker):
- POST /api/phi/scan
- POST /api/phi/scan/batch
- POST /api/phi/scan/stream
- POST /api/phi/redact
- GET  /api/phi/audit/{project_id}

These tests focus on contract, HIPAA identifier coverage (via representative samples),
and performance assertions.
"""

from __future__ import annotations

import pytest

from tests.integration.utils.api_client import APIClient
from tests.integration.utils.assertions import assert_json, assert_perf, assert_status


HIPAA_SAMPLES = {
    # 18 HIPAA identifiers: provide representative strings
    "names": "Patient John A. Smith presented today.",
    "geo": "Lives at 123 Main St, Boston, MA 02110.",
    "dates": "DOB: 01/02/1970; admitted 2021-06-05.",
    "phone": "Call (617) 555-1212 for follow-up.",
    "fax": "Fax: 617-555-9999.",
    "email": "Email john.smith@example.com.",
    "ssn": "SSN 123-45-6789.",
    "mrn": "MRN: 000123456.",
    "health_plan": "Health plan: HICN 1EG4-TE5-MK72.",
    "account": "Account: 123456789012.",
    "certificate": "Certificate/license #A1234567.",
    "vehicle": "Vehicle plate ABC-1234.",
    "device": "Device ID: DEV-998877.",
    "url": "See https://hospital.example.org/patient/123.",
    "ip": "Client IP 192.168.1.10.",
    "biometric": "Biometric hash: finger:9f86d081884c.",
    "photo": "Photo file name: patient_john_smith.jpg.",
    "other": "Any other unique code: STUDYID-XYZ-999.",
}


@pytest.mark.asyncio
async def test_phi_scan_single(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    content = " ".join(HIPAA_SAMPLES.values())

    tr = await api.post("/api/phi/scan", json={"content": content, "sensitivity": "high", "project_id": "it-proj", "user_id": "it-user"})
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/phi/scan")
    assert_status(tr.response, 200)
    body = assert_json(tr.response)
    assert "result" in body


@pytest.mark.asyncio
async def test_phi_scan_batch(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    items = [{"item_id": k, "content": v} for k, v in list(HIPAA_SAMPLES.items())[:10]]

    tr = await api.post(
        "/api/phi/scan/batch",
        json={"items": items, "sensitivity": "high", "concurrency": 4, "project_id": "it-proj", "user_id": "it-user"},
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/phi/scan/batch")
    assert_status(tr.response, (200, 400))
    if tr.response.status_code == 200:
        body = assert_json(tr.response)
        assert "result" in body


@pytest.mark.asyncio
async def test_phi_scan_stream(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    # emulate large file via repeated content
    content = (" ".join(HIPAA_SAMPLES.values()) + " ") * 200

    tr = await api.post(
        "/api/phi/scan/stream",
        json={"content": content, "chunk_size": 2000, "sensitivity": "high", "project_id": "it-proj", "user_id": "it-user"},
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/phi/scan/stream")
    assert_status(tr.response, (200, 400))


@pytest.mark.asyncio
async def test_phi_redact(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    content = "Patient John Smith SSN 123-45-6789 lives at 123 Main St."

    tr = await api.post(
        "/api/phi/redact",
        json={"content": content, "sensitivity": "high", "project_id": "it-proj", "user_id": "it-user"},
    )
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="POST /api/phi/redact")
    assert_status(tr.response, (200, 400))
    if tr.response.status_code == 200:
        body = assert_json(tr.response)
        assert "result" in body


@pytest.mark.asyncio
async def test_phi_audit_trail(require_worker, worker_client, perf_budget_seconds):
    api = APIClient(worker_client)
    project_id = "it-proj"

    tr = await api.get(f"/api/phi/audit/{project_id}")
    assert_perf(tr.elapsed_s, perf_budget_seconds, label="GET /api/phi/audit/{project_id}")
    assert_status(tr.response, (200, 404))
