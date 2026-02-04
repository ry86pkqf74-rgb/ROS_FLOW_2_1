from __future__ import annotations

import pytest

from src.phi.scanner.batch_scanner import HybridDetector


@pytest.mark.asyncio
async def test_detects_all_18_hipaa_identifiers(synthetic_phi_samples: dict):
    det = HybridDetector()

    # one text containing at least one instance of each identifier kind
    text = "\n".join(
        [
            synthetic_phi_samples["name"],
            synthetic_phi_samples["zip"],
            synthetic_phi_samples["date"],
            synthetic_phi_samples["phone"],
            synthetic_phi_samples["fax"],
            synthetic_phi_samples["email"],
            synthetic_phi_samples["ssn"],
            synthetic_phi_samples["mrn"],
            synthetic_phi_samples["health_plan"],
            synthetic_phi_samples["account"],
            synthetic_phi_samples["license"],
            synthetic_phi_samples["vehicle"],
            synthetic_phi_samples["device"],
            synthetic_phi_samples["url"],
            f"IP: {synthetic_phi_samples['ip4']} and {synthetic_phi_samples['ip6']}",
            synthetic_phi_samples["biometric"],
            synthetic_phi_samples["photo"],
            synthetic_phi_samples["other_unique"],
        ]
    )

    dets = await det.detect(text, sensitivity="low")
    kinds = {d.kind for d in dets}

    # All 18 keys defined in hipaa_identifiers.py
    expected = {
        "names",
        "geographic",
        "dates",
        "phone",
        "fax",
        "email",
        "ssn",
        "mrn",
        "health_plan",
        "account",
        "certificate_license",
        "vehicle",
        "device",
        "url",
        "ip",
        "biometric",
        "photo",
        "other_unique",
    }

    missing = expected - kinds
    assert not missing, f"Missing kinds: {missing} (got {kinds})"


@pytest.mark.asyncio
async def test_edge_cases_partial_matches_and_false_positives_are_minimized():
    det = HybridDetector()

    # partial SSN should not match
    text = "SSN 123-45-678 and not-an-email alice@ example.com"
    dets = await det.detect(text, sensitivity="low")
    kinds = {d.kind for d in dets}
    assert "ssn" not in kinds
    assert "email" not in kinds


@pytest.mark.asyncio
async def test_international_variations_are_detected():
    det = HybridDetector()

    # NHS number (3-3-4 digits, optional spaces)
    text = "NHS: 9434765919 and spaced 943 476 5919"
    dets = await det.detect(text, sensitivity="low")
    kinds = {d.kind for d in dets}
    assert "nhs_number" in kinds
