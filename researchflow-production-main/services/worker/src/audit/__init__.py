"""
Audit Module

Immutable audit logging with cryptographic hash chain for tamper detection
and compliance with data governance requirements.

Key Components:
- hash_chain: Hash chain audit logging with database persistence
- SQLAlchemy ORM models for audit entries
- Chain integrity verification
- Rollback support for audit entries

Phase 14 Implementation - ROS-114
Track E - Monitoring & Audit
"""

from .hash_chain import (
    HashChainAuditLogger,
    AuditEntry,
    get_audit_logger,
)

__all__ = [
    "HashChainAuditLogger",
    "AuditEntry",
    "get_audit_logger",
]
