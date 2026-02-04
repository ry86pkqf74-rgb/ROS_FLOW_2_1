from __future__ import annotations

import pytest

from src.phi.redaction.redactor import RedactionConfig, Redactor


@pytest.mark.asyncio
async def test_consistent_tokenization_for_repeated_kinds():
    redactor = Redactor()
    cfg = RedactionConfig(sensitivity="low", token_prefix="PHI")

    text = "Call 555-123-4567. Call 555-123-4567 again. Email a@b.com."
    out = await redactor.redact(text, cfg)

    # phone appears twice -> should produce two tokens of same kind with ordinals 1 and 2
    phone_tokens = [s.token for s in out.spans if s.kind == "phone"]
    assert phone_tokens == ["[PHI:PHONE:1]", "[PHI:PHONE:2]"]


@pytest.mark.asyncio
async def test_reversible_vs_irreversible_redaction_behavior():
    redactor = Redactor()
    cfg = RedactionConfig(sensitivity="low", token_prefix="PHI")

    text = "Email alice@example.com"
    out = await redactor.redact(text, cfg)

    # mapping should contain hashed originals enabling limited reversibility by secure lookup
    assert out.mapping
    assert "[PHI:EMAIL:1]" in out.mapping
    assert len(out.mapping["[PHI:EMAIL:1]"][0]) == 12


@pytest.mark.asyncio
async def test_format_preservation_document_structure(text_with_multiple_phi: str):
    redactor = Redactor()
    cfg = RedactionConfig(sensitivity="low", token_prefix="PHI")

    out = await redactor.redact(text_with_multiple_phi, cfg)

    # should preserve line breaks count
    assert out.redacted_text.count("\n") == text_with_multiple_phi.count("\n")
