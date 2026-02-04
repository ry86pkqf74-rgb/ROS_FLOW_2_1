"""International PHI/PII identifier patterns.

Includes examples for:
- UK NHS numbers
- EU identifiers (generic placeholders)
- Canadian Health Insurance Numbers (HIN)

These are jurisdiction-specific; validate against your compliance program.
"""

from __future__ import annotations

from typing import Dict

from .hipaa_identifiers import PatternDef


INTERNATIONAL_PATTERNS: Dict[str, PatternDef] = {
    "nhs_number": PatternDef(
        key="nhs_number",
        description="UK NHS Number (10 digits, commonly spaced as 3-3-4).",
        regexes=[
            r"\b\d{3}\s?\d{3}\s?\d{4}\b",
        ],
    ),
    "eu_passport_like": PatternDef(
        key="eu_passport_like",
        description="EU passport-like identifier (generic alphanumeric).",
        regexes=[
            r"\b[A-Z]{2}\d{6,9}\b",
        ],
    ),
    "canadian_hin": PatternDef(
        key="canadian_hin",
        description="Canadian Health Insurance Number (varies by province; generic pattern).",
        regexes=[
            r"\b[A-Z]{0,2}\d{8,12}\b",
        ],
    ),
}
