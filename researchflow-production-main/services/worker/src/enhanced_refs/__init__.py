"""
Writing Agents Package

This package contains specialized agents for manuscript writing, citation management,
and reference handling.

Linear Issues: ROS-XXX
"""

from .reference_management_service import (
    ReferenceManagementService,
    ReferenceState,
    ReferenceResult,
    Citation,
    Reference,
    QualityScore,
    QualityWarning,
)

from .doi_validator import DOIValidator, DOIValidationResult
from .duplicate_detector import PaperDeduplicator, DuplicateGroup
from .reference_cache import ReferenceCache
from .api_management import ExternalAPIManager, AsyncRateLimiter
from .reference_quality import ReferenceQualityAssessor, ReferenceAnalytics

__all__ = [
    "ReferenceManagementService",
    "ReferenceState",
    "ReferenceResult",
    "Citation",
    "Reference", 
    "QualityScore",
    "QualityWarning",
    "DOIValidator",
    "DOIValidationResult",
    "PaperDeduplicator",
    "DuplicateGroup",
    "ReferenceCache",
    "ExternalAPIManager",
    "AsyncRateLimiter",
    "ReferenceQualityAssessor",
    "ReferenceAnalytics",
]