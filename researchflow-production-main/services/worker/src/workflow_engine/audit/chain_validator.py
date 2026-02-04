"""
Audit Chain Integrity Validator

Provides cryptographic validation of audit chain integrity with detailed reporting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from .phi_audit_chain import PHIAuditEvent, PHIAuditChain

logger = logging.getLogger(__name__)


class AuditChainError(Exception):
    """Exception raised for audit chain integrity violations."""
    pass


@dataclass
class IntegrityValidationResult:
    """Result of audit chain integrity validation."""
    is_valid: bool
    total_events_checked: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    validation_timestamp: str = ""
    chain_start_hash: Optional[str] = None
    chain_end_hash: Optional[str] = None
    
    def __post_init__(self):
        if not self.validation_timestamp:
            self.validation_timestamp = datetime.utcnow().isoformat() + "Z"
    
    @property
    def violation_count(self) -> int:
        return len(self.violations)
    
    @property
    def has_critical_violations(self) -> bool:
        return any(v.get("severity") == "critical" for v in self.violations)


class ChainIntegrityValidator:
    """Validates the integrity of PHI audit chains."""
    
    def __init__(self):
        self.validation_rules = [
            self._validate_chain_continuity,
            self._validate_content_hashes,
            self._validate_signatures,
            self._validate_timestamps,
            self._validate_required_fields,
        ]
    
    def validate_full_chain(self, audit_chain: PHIAuditChain) -> IntegrityValidationResult:
        """
        Perform comprehensive validation of entire audit chain.
        
        Args:
            audit_chain: PHI audit chain to validate
            
        Returns:
            Detailed validation result
        """
        events = audit_chain.get_audit_trail(limit=100000)  # Get all events
        
        if not events:
            return IntegrityValidationResult(
                is_valid=True,
                total_events_checked=0,
                violations=[],
                chain_start_hash=None,
                chain_end_hash=None
            )
        
        violations = []
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                rule_violations = rule(events, audit_chain)
                violations.extend(rule_violations)
            except Exception as e:
                logger.error(f"Validation rule failed: {e}")
                violations.append({
                    "type": "VALIDATION_ERROR",
                    "severity": "critical",
                    "description": f"Validation rule failed: {str(e)}",
                    "event_id": None,
                    "details": {"error": str(e)}
                })
        
        return IntegrityValidationResult(
            is_valid=len(violations) == 0,
            total_events_checked=len(events),
            violations=violations,
            chain_start_hash=events[0].content_hash if events else None,
            chain_end_hash=events[-1].content_hash if events else None
        )
    
    def _validate_chain_continuity(self, 
                                  events: List[PHIAuditEvent], 
                                  audit_chain: PHIAuditChain) -> List[Dict[str, Any]]:
        """Validate that the chain is continuous (each event links to the previous)."""
        violations = []
        
        if not events:
            return violations
        
        # First event should have no previous hash
        first_event = events[0]
        if first_event.previous_hash is not None:
            violations.append({
                "type": "INVALID_CHAIN_START",
                "severity": "high", 
                "description": "First event should not have a previous hash",
                "event_id": first_event.event_id,
                "details": {
                    "expected_previous_hash": None,
                    "actual_previous_hash": first_event.previous_hash
                }
            })
        
        # Validate chain continuity for subsequent events
        for i in range(1, len(events)):
            current_event = events[i]
            previous_event = events[i-1]
            
            expected_previous_hash = previous_event.content_hash
            actual_previous_hash = current_event.previous_hash
            
            if actual_previous_hash != expected_previous_hash:
                violations.append({
                    "type": "BROKEN_CHAIN_LINK",
                    "severity": "critical",
                    "description": f"Chain link broken between events {previous_event.event_id} and {current_event.event_id}",
                    "event_id": current_event.event_id,
                    "details": {
                        "previous_event_id": previous_event.event_id,
                        "expected_previous_hash": expected_previous_hash,
                        "actual_previous_hash": actual_previous_hash
                    }
                })
        
        return violations
    
    def _validate_content_hashes(self,
                                events: List[PHIAuditEvent],
                                audit_chain: PHIAuditChain) -> List[Dict[str, Any]]:
        """Validate that each event's content hash matches its calculated hash."""
        violations = []
        
        for event in events:
            calculated_hash = event.calculate_content_hash()
            stored_hash = event.content_hash
            
            if calculated_hash != stored_hash:
                violations.append({
                    "type": "CONTENT_HASH_MISMATCH",
                    "severity": "critical",
                    "description": f"Event content has been tampered with",
                    "event_id": event.event_id,
                    "details": {
                        "calculated_hash": calculated_hash,
                        "stored_hash": stored_hash,
                        "event_timestamp": event.timestamp
                    }
                })
        
        return violations
    
    def _validate_signatures(self,
                            events: List[PHIAuditEvent], 
                            audit_chain: PHIAuditChain) -> List[Dict[str, Any]]:
        """Validate cryptographic signatures if present."""
        violations = []
        
        # Skip if signing is not enabled
        if not audit_chain.enable_signing or not audit_chain._public_key:
            return violations
        
        for event in events:
            if event.signature:
                # Use audit chain's signature verification
                is_valid = audit_chain._verify_signature(event)
                
                if not is_valid:
                    violations.append({
                        "type": "INVALID_SIGNATURE",
                        "severity": "high",
                        "description": f"Cryptographic signature verification failed",
                        "event_id": event.event_id,
                        "details": {
                            "signature_present": True,
                            "verification_result": False,
                            "event_timestamp": event.timestamp
                        }
                    })
            elif audit_chain.enable_signing:
                # If signing is enabled, all events should have signatures
                violations.append({
                    "type": "MISSING_SIGNATURE",
                    "severity": "medium",
                    "description": f"Event missing cryptographic signature",
                    "event_id": event.event_id,
                    "details": {
                        "signing_enabled": True,
                        "signature_present": False
                    }
                })
        
        return violations
    
    def _validate_timestamps(self,
                            events: List[PHIAuditEvent],
                            audit_chain: PHIAuditChain) -> List[Dict[str, Any]]:
        """Validate timestamp ordering and format."""
        violations = []
        
        previous_timestamp = None
        
        for event in events:
            # Validate timestamp format
            try:
                event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
            except ValueError:
                violations.append({
                    "type": "INVALID_TIMESTAMP_FORMAT",
                    "severity": "medium",
                    "description": f"Invalid timestamp format",
                    "event_id": event.event_id,
                    "details": {
                        "timestamp": event.timestamp,
                        "expected_format": "ISO 8601 with Z suffix"
                    }
                })
                continue
            
            # Validate timestamp ordering (events should be chronological)
            if previous_timestamp and event_time < previous_timestamp:
                violations.append({
                    "type": "TIMESTAMP_OUT_OF_ORDER",
                    "severity": "medium",
                    "description": f"Event timestamp is earlier than previous event",
                    "event_id": event.event_id,
                    "details": {
                        "event_timestamp": event.timestamp,
                        "previous_timestamp": previous_timestamp.isoformat()
                    }
                })
            
            # Check for future timestamps (beyond reasonable clock skew)
            now = datetime.utcnow()
            if event_time > now.replace(microsecond=0) + timedelta(minutes=5):  # 5 min clock skew allowance
                violations.append({
                    "type": "FUTURE_TIMESTAMP",
                    "severity": "medium",
                    "description": f"Event timestamp is in the future",
                    "event_id": event.event_id,
                    "details": {
                        "event_timestamp": event.timestamp,
                        "current_time": now.isoformat(),
                        "skew_minutes": (event_time - now).total_seconds() / 60
                    }
                })
            
            previous_timestamp = event_time
        
        return violations
    
    def _validate_required_fields(self,
                                 events: List[PHIAuditEvent],
                                 audit_chain: PHIAuditChain) -> List[Dict[str, Any]]:
        """Validate that all required fields are present and valid."""
        violations = []
        
        required_fields = [
            "event_id", "timestamp", "event_type", "job_id", 
            "governance_mode", "content_hash"
        ]
        
        for event in events:
            # Check required fields
            for field in required_fields:
                value = getattr(event, field, None)
                if value is None or (isinstance(value, str) and not value.strip()):
                    violations.append({
                        "type": "MISSING_REQUIRED_FIELD",
                        "severity": "high",
                        "description": f"Required field '{field}' is missing or empty",
                        "event_id": event.event_id,
                        "details": {
                            "missing_field": field,
                            "current_value": value
                        }
                    })
            
            # Validate event_id format (should be UUID)
            try:
                import uuid
                uuid.UUID(event.event_id)
            except ValueError:
                violations.append({
                    "type": "INVALID_EVENT_ID_FORMAT",
                    "severity": "medium",
                    "description": f"Event ID is not a valid UUID",
                    "event_id": event.event_id,
                    "details": {
                        "event_id": event.event_id,
                        "expected_format": "UUID v4"
                    }
                })
            
            # Validate governance mode
            valid_governance_modes = ["DEMO", "STAGING", "PRODUCTION", "UNKNOWN"]
            if event.governance_mode not in valid_governance_modes:
                violations.append({
                    "type": "INVALID_GOVERNANCE_MODE",
                    "severity": "medium",
                    "description": f"Invalid governance mode",
                    "event_id": event.event_id,
                    "details": {
                        "governance_mode": event.governance_mode,
                        "valid_modes": valid_governance_modes
                    }
                })
        
        return violations
    
    def validate_event_sequence(self,
                               events: List[PHIAuditEvent],
                               expected_sequence: List[str]) -> List[Dict[str, Any]]:
        """
        Validate that events follow an expected sequence pattern.
        
        Args:
            events: List of events to validate
            expected_sequence: List of expected event types in order
            
        Returns:
            List of violations if sequence is incorrect
        """
        violations = []
        
        if len(events) < len(expected_sequence):
            violations.append({
                "type": "INCOMPLETE_SEQUENCE",
                "severity": "medium",
                "description": f"Event sequence is incomplete",
                "event_id": None,
                "details": {
                    "expected_events": len(expected_sequence),
                    "actual_events": len(events),
                    "expected_sequence": expected_sequence
                }
            })
            return violations
        
        for i, expected_type in enumerate(expected_sequence):
            if i < len(events):
                actual_type = events[i].event_type.value
                if actual_type != expected_type:
                    violations.append({
                        "type": "SEQUENCE_VIOLATION",
                        "severity": "medium", 
                        "description": f"Event sequence violation at position {i}",
                        "event_id": events[i].event_id,
                        "details": {
                            "position": i,
                            "expected_type": expected_type,
                            "actual_type": actual_type,
                            "expected_sequence": expected_sequence
                        }
                    })
        
        return violations
    
    def generate_integrity_report(self, 
                                 result: IntegrityValidationResult,
                                 include_recommendations: bool = True) -> Dict[str, Any]:
        """
        Generate a detailed integrity validation report.
        
        Args:
            result: Validation result to report on
            include_recommendations: Whether to include remediation recommendations
            
        Returns:
            Comprehensive integrity report
        """
        # Categorize violations by type and severity
        violation_summary = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        violation_types = {}
        
        for violation in result.violations:
            severity = violation.get("severity", "unknown")
            violation_type = violation.get("type", "UNKNOWN")
            
            if severity in violation_summary:
                violation_summary[severity].append(violation)
            
            violation_types[violation_type] = violation_types.get(violation_type, 0) + 1
        
        # Generate overall assessment
        if result.is_valid:
            overall_status = "VALID"
            risk_level = "LOW"
        elif result.has_critical_violations:
            overall_status = "CRITICAL_VIOLATIONS"
            risk_level = "CRITICAL"
        elif violation_summary["high"]:
            overall_status = "HIGH_RISK_VIOLATIONS"
            risk_level = "HIGH"
        elif violation_summary["medium"]:
            overall_status = "MEDIUM_RISK_VIOLATIONS"
            risk_level = "MEDIUM"
        else:
            overall_status = "LOW_RISK_VIOLATIONS"
            risk_level = "LOW"
        
        report = {
            "report_timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_status": overall_status,
            "risk_level": risk_level,
            "is_valid": result.is_valid,
            "summary": {
                "total_events_checked": result.total_events_checked,
                "total_violations": result.violation_count,
                "violation_breakdown": {
                    "critical": len(violation_summary["critical"]),
                    "high": len(violation_summary["high"]), 
                    "medium": len(violation_summary["medium"]),
                    "low": len(violation_summary["low"])
                },
                "violation_types": violation_types
            },
            "chain_metadata": {
                "start_hash": result.chain_start_hash,
                "end_hash": result.chain_end_hash,
                "validation_timestamp": result.validation_timestamp
            },
            "violations": result.violations
        }
        
        # Add recommendations if requested
        if include_recommendations:
            report["recommendations"] = self._generate_recommendations(result)
        
        return report
    
    def _generate_recommendations(self, result: IntegrityValidationResult) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if result.is_valid:
            recommendations.append("✅ Audit chain integrity verified - no action required")
            return recommendations
        
        # Critical violations
        critical_violations = [v for v in result.violations if v.get("severity") == "critical"]
        if critical_violations:
            recommendations.extend([
                "🚨 IMMEDIATE ACTION REQUIRED:",
                "   • Audit chain has critical integrity violations",
                "   • Investigate potential tampering or data corruption",
                "   • Restore from backup if available",
                "   • Review system security and access controls"
            ])
        
        # Specific violation type recommendations
        violation_types = set(v.get("type") for v in result.violations)
        
        if "BROKEN_CHAIN_LINK" in violation_types:
            recommendations.append("🔗 Chain continuity broken - verify event storage integrity")
        
        if "CONTENT_HASH_MISMATCH" in violation_types:
            recommendations.append("🔒 Content tampering detected - investigate unauthorized modifications")
        
        if "INVALID_SIGNATURE" in violation_types:
            recommendations.append("🔐 Signature verification failed - check cryptographic keys")
        
        if "TIMESTAMP_OUT_OF_ORDER" in violation_types:
            recommendations.append("⏰ Timestamp ordering issues - verify system clock synchronization")
        
        # General recommendations
        recommendations.extend([
            "📋 Recommended actions:",
            "   1. Document all violations for compliance review",
            "   2. Implement additional monitoring and alerting", 
            "   3. Review audit chain storage and backup procedures",
            "   4. Consider re-generating chain from authoritative source"
        ])
        
        return recommendations


# Need to import timedelta
from datetime import timedelta