"""HIPAA Safe Harbor identifiers (18) pattern library.

These patterns are intended for hybrid detection: regex + optional spaCy NER.
They are conservative and should be used with context-aware heuristics.

NOTE: Regex alone cannot perfectly disambiguate all cases (e.g., names).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PatternDef:
    key: str
    description: str
    regexes: List[str]
    # Optional allowlist hints for suppression
    allowlist: Optional[List[str]] = None


# 18 identifiers per HIPAA Safe Harbor
HIPAA_IDENTIFIER_PATTERNS: Dict[str, PatternDef] = {
    # 1. Names
    "names": PatternDef(
        key="names",
        description="Names (person names) - regex is heuristic; prefer spaCy PERSON NER.",
        regexes=[
            # Heuristic title + last name
            r"\b(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?|Patient|Pt\.?|MD|DO)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b",
        ],
    ),

    # 2. Geographic data (smaller than state)
    "geographic": PatternDef(
        key="geographic",
        description="Geographic subdivisions smaller than a state (street address, city, ZIP).",
        regexes=[
            # US ZIP / ZIP+4
            r"\b\d{5}(?:-\d{4})?\b",
            # Common street address pattern (very heuristic)
            r"\b\d{1,6}\s+(?:[A-Za-z0-9.]+\s){0,5}(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Way|Pkwy|Parkway)\b\.?,?\s*(?:[A-Za-z.]+\s*){0,4}(?:,\s*[A-Z]{2})?\s*\d{5}(?:-\d{4})?\b",
        ],
    ),

    # 3. Dates (except year) related to individual
    "dates": PatternDef(
        key="dates",
        description="All elements of dates (except year) directly related to an individual.",
        regexes=[
            # MM/DD/YYYY or MM-DD-YYYY
            r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](\d{2}|\d{4})\b",
            # YYYY-MM-DD
            r"\b\d{4}-\d{2}-\d{2}\b",
            # Month name + day (+ optional year)
            r"\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)\s+(?:0?[1-9]|[12]\d|3[01])(?:,\s*\d{4})?\b",
        ],
    ),

    # 4. Telephone numbers
    "phone": PatternDef(
        key="phone",
        description="Telephone numbers.",
        regexes=[
            r"\b(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
        ],
    ),

    # 5. Fax numbers
    "fax": PatternDef(
        key="fax",
        description="Fax numbers.",
        regexes=[
            r"\b(?:fax\s*[:#]?\s*)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
        ],
    ),

    # 6. Email addresses
    "email": PatternDef(
        key="email",
        description="Email addresses.",
        regexes=[
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        ],
    ),

    # 7. Social Security numbers
    "ssn": PatternDef(
        key="ssn",
        description="Social Security Numbers.",
        regexes=[
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{9}\b",
        ],
        allowlist=[
            # suppress common dataset sizes like 1234567890 etc (placeholder example)
            r"\b000-00-0000\b",
        ],
    ),

    # 8. Medical record numbers
    "mrn": PatternDef(
        key="mrn",
        description="Medical record numbers (MRN).",
        regexes=[
            r"\b(?:MRN|Medical\s*Record\s*Number)\s*[:#]?\s*[A-Z0-9]{6,12}\b",
        ],
    ),

    # 9. Health plan beneficiary numbers
    "health_plan": PatternDef(
        key="health_plan",
        description="Health plan beneficiary numbers.",
        regexes=[
            r"\b(?:HICN|Health\s*Plan|Member\s*ID|Policy\s*Number)\s*[:#]?\s*[A-Z0-9-]{6,20}\b",
        ],
    ),

    # 10. Account numbers
    "account": PatternDef(
        key="account",
        description="Account numbers.",
        regexes=[
            r"\b(?:Account|Acct)\s*[:#]?\s*\d{6,18}\b",
        ],
    ),

    # 11. Certificate/license numbers
    "certificate_license": PatternDef(
        key="certificate_license",
        description="Certificate/license numbers.",
        regexes=[
            r"\b(?:License|Lic)\s*[:#]?\s*[A-Z0-9-]{5,20}\b",
        ],
    ),

    # 12. Vehicle identifiers and serial numbers, including license plates
    "vehicle": PatternDef(
        key="vehicle",
        description="Vehicle identifiers, VINs, license plates.",
        regexes=[
            # VIN
            r"\b[A-HJ-NPR-Z0-9]{17}\b",
            # Plate heuristic
            r"\b(?:Plate|License\s*Plate)\s*[:#]?\s*[A-Z0-9-]{5,10}\b",
        ],
    ),

    # 13. Device identifiers and serial numbers
    "device": PatternDef(
        key="device",
        description="Device identifiers and serial numbers.",
        regexes=[
            r"\b(?:Device\s*ID|Device|Serial\s*(?:No\.?|Number))\s*[:#]?\s*[A-Z0-9-]{6,30}\b",
        ],
    ),

    # 14. Web URLs
    "url": PatternDef(
        key="url",
        description="Web URLs.",
        regexes=[
            r"\bhttps?://[^\s)\]}>'\"]+\b",
            r"\bwww\.[^\s)\]}>'\"]+\b",
        ],
    ),

    # 15. IP addresses
    "ip": PatternDef(
        key="ip",
        description="IP addresses (IPv4/IPv6).",
        regexes=[
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b",
            r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b",
        ],
    ),

    # 16. Biometric identifiers
    "biometric": PatternDef(
        key="biometric",
        description="Biometric identifiers (finger/voice).",
        regexes=[
            r"\b(?:fingerprint|retina|iris\s*scan|voiceprint|biometric)\b",
        ],
    ),

    # 17. Full-face photos and comparable images
    "photo": PatternDef(
        key="photo",
        description="Full-face photos and comparable images (heuristic, metadata-driven).",
        regexes=[
            r"\b(?:full[- ]?face|face\s*photo|portrait)\b",
        ],
    ),

    # 18. Any other unique identifying number, characteristic, or code
    "other_unique": PatternDef(
        key="other_unique",
        description="Other unique identifying number/characteristic/code.",
        regexes=[
            r"\b(?:Patient\s*ID|Subject\s*ID|Study\s*ID)\s*[:#]?\s*[A-Z0-9-]{4,20}\b",
        ],
    ),
}
