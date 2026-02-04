"""
Audit Module for Workflow Engine

Provides cryptographically secure audit logging for PHI handling and compliance events.
Includes tamper-proof audit chains, integrity validation, and compliance reporting.
"""

from .phi_audit_chain import (
    PHIAuditChain,
    PHIAuditEvent,
    AuditEventType,
    StorageBackend,
)
from .chain_validator import (
    ChainIntegrityValidator,
    IntegrityValidationResult,
    AuditChainError,
)

__all__ = [
    "PHIAuditChain",
    "PHIAuditEvent", 
    "AuditEventType",
    "StorageBackend",
    "ChainIntegrityValidator",
    "IntegrityValidationResult",
    "AuditChainError",
]