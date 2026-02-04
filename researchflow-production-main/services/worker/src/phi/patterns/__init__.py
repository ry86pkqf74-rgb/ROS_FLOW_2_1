"""Pattern sets for PHI detection."""

from .hipaa_identifiers import HIPAA_IDENTIFIER_PATTERNS
from .custom_patterns import CUSTOM_PATTERNS
from .international_patterns import INTERNATIONAL_PATTERNS

__all__ = [
    "HIPAA_IDENTIFIER_PATTERNS",
    "CUSTOM_PATTERNS",
    "INTERNATIONAL_PATTERNS",
]
