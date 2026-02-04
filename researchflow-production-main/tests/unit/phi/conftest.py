from __future__ import annotations

import pytest


@pytest.fixture()
def synthetic_phi_samples() -> dict:
    """Synthetic samples for PHI tests (non-real data)."""

    return {
        "name": "Patient: Dr. Alice Smith",
        "zip": "Address: 123 Main St, New York, NY 10001",
        "date": "DOB: 01/02/1980",
        "phone": "Call 555-123-4567 today",
        "fax": "Fax: 555-000-1212",
        "email": "Email alice.smith+test@example.com",
        "ssn": "SSN 123-45-6789",
        "mrn": "MRN: A1B2C3D4",
        "health_plan": "Member ID: ABCD-123456",
        "account": "Acct: 123456789",
        "license": "Lic: MD-123456",
        "vehicle": "VIN 1HGCM82633A004352",
        "device": "Device ID: SN-ABC123456",
        "url": "https://example.com/patient/123",
        "ip4": "192.168.1.25",
        "ip6": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "biometric": "fingerprint scan",
        "photo": "full-face photo",
        "other_unique": "Patient ID: X-12345",
        # international
        "nhs": "NHS 943 476 5919",
    }


@pytest.fixture()
def text_with_multiple_phi(synthetic_phi_samples: dict) -> str:
    return (
        f"{synthetic_phi_samples['name']}\n"
        f"{synthetic_phi_samples['zip']}\n"
        f"{synthetic_phi_samples['date']}\n"
        f"{synthetic_phi_samples['phone']}\n"
        f"{synthetic_phi_samples['email']}\n"
        f"{synthetic_phi_samples['ssn']}\n"
        f"{synthetic_phi_samples['mrn']}\n"
        f"{synthetic_phi_samples['nhs']}\n"
    )
