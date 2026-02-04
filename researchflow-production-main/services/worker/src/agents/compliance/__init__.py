"""
Compliance Agent Module

Provides compliance validation and governance automation for AI/ML research.

Includes:
- ComplianceAgent: Main orchestrator for compliance validation
- FAVES gate validator
- TRIPOD+AI checklist validator
- CONSORT-AI checklist validator
"""

from .agent import ComplianceAgent

__all__ = ["ComplianceAgent"]
