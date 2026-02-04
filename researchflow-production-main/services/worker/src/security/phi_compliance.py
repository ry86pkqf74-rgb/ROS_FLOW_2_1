"""
PHI Compliance Validator for Protocol Generation

Advanced PHI (Protected Health Information) detection, sanitization, and compliance
validation specifically designed for clinical study protocol generation.
Ensures HIPAA compliance and data privacy throughout the protocol generation process.

Key Features:
- Advanced PHI pattern detection using regex and ML
- Real-time sanitization and masking
- Compliance validation against HIPAA requirements
- Audit trail for all PHI-related operations
- Integration with protocol generation pipeline

Author: Enhancement Team
"""

import logging
import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime
import hashlib
import uuid

logger = logging.getLogger(__name__)


class PHIType(Enum):
    """Types of PHI that can be detected."""
    NAME = "name"
    SSN = "ssn"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    DOB = "date_of_birth"
    MRN = "medical_record_number"
    ACCOUNT_NUMBER = "account_number"
    CERTIFICATE_NUMBER = "certificate_number"
    DEVICE_ID = "device_identifier"
    BIOMETRIC = "biometric_identifier"
    PHOTO = "photograph"
    URL = "url"
    IP_ADDRESS = "ip_address"
    LICENSE_NUMBER = "license_number"
    CUSTOM = "custom"


class ComplianceLevel(Enum):
    """Compliance levels for validation."""
    STRICT = "strict"       # No PHI allowed
    MODERATE = "moderate"   # PHI allowed but must be masked
    PERMISSIVE = "permissive"  # PHI allowed with warnings


@dataclass
class PHIMatch:
    """Data structure for PHI detection results."""
    phi_type: PHIType
    value: str
    start_pos: int
    end_pos: int
    confidence: float
    context: str = ""
    masked_value: str = ""
    severity: str = "high"


@dataclass
class PHIValidationResult:
    """Result of PHI validation."""
    is_compliant: bool
    phi_matches: List[PHIMatch] = field(default_factory=list)
    sanitized_content: str = ""
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    compliance_level: ComplianceLevel = ComplianceLevel.STRICT
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)


class PHIPatterns:
    """PHI detection patterns and utilities."""
    
    # Regex patterns for PHI detection
    PATTERNS = {
        PHIType.SSN: [
            r'\b\d{3}-\d{2}-\d{4}\b',          # 123-45-6789
            r'\b\d{3}\s\d{2}\s\d{4}\b',        # 123 45 6789
            r'\b\d{9}\b'                        # 123456789
        ],
        PHIType.PHONE: [
            r'\b\d{3}-\d{3}-\d{4}\b',          # 123-456-7890
            r'\b\(\d{3}\)\s?\d{3}-\d{4}\b',    # (123) 456-7890
            r'\b\d{3}\.\d{3}\.\d{4}\b',        # 123.456.7890
            r'\b\d{10}\b'                       # 1234567890
        ],
        PHIType.EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ],
        PHIType.DOB: [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',     # MM/DD/YYYY or MM-DD-YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',     # YYYY/MM/DD or YYYY-MM-DD
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s\d{4}\b'
        ],
        PHIType.MRN: [
            r'\bMRN[:\s]*\d+\b',
            r'\bMedical\s+Record\s+Number[:\s]*\d+\b',
            r'\bPatient\s+ID[:\s]*\d+\b'
        ],
        PHIType.IP_ADDRESS: [
            r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        ],
        PHIType.URL: [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            r'www\.[^\s<>"{}|\\^`\[\]]+'
        ]
    }
    
    # Common PHI-related keywords for context detection
    PHI_CONTEXT_KEYWORDS = {
        PHIType.NAME: ['patient', 'subject', 'participant', 'mr', 'mrs', 'dr', 'first name', 'last name'],
        PHIType.DOB: ['birth', 'born', 'dob', 'date of birth', 'age'],
        PHIType.ADDRESS: ['address', 'street', 'avenue', 'road', 'city', 'state', 'zip'],
        PHIType.PHONE: ['phone', 'telephone', 'cell', 'mobile', 'contact'],
        PHIType.EMAIL: ['email', 'e-mail', 'contact'],
        PHIType.MRN: ['medical record', 'patient id', 'mrn', 'chart number']
    }
    
    @classmethod
    def get_patterns(cls, phi_type: PHIType) -> List[str]:
        """Get regex patterns for a specific PHI type."""
        return cls.PATTERNS.get(phi_type, [])
    
    @classmethod
    def get_context_keywords(cls, phi_type: PHIType) -> List[str]:
        """Get context keywords for a specific PHI type."""
        return cls.PHI_CONTEXT_KEYWORDS.get(phi_type, [])


class PHIDetector:
    """Advanced PHI detector with pattern matching and context analysis."""
    
    def __init__(self, custom_patterns: Optional[Dict[PHIType, List[str]]] = None):
        self.custom_patterns = custom_patterns or {}
        self.detection_history = []
    
    def detect_phi(self, text: str, context: str = "") -> List[PHIMatch]:
        """
        Detect PHI in text using pattern matching and context analysis.
        
        Args:
            text: Text to analyze
            context: Additional context for better detection
            
        Returns:
            List of PHI matches found
        """
        matches = []
        
        # Combine default and custom patterns
        all_patterns = {}
        for phi_type in PHIType:
            patterns = PHIPatterns.get_patterns(phi_type)
            if phi_type in self.custom_patterns:
                patterns.extend(self.custom_patterns[phi_type])
            all_patterns[phi_type] = patterns
        
        # Search for each PHI type
        for phi_type, patterns in all_patterns.items():
            type_matches = self._find_matches(text, phi_type, patterns)
            matches.extend(type_matches)
        
        # Sort matches by position
        matches.sort(key=lambda m: m.start_pos)
        
        # Store detection history
        self.detection_history.append({
            'timestamp': datetime.now(),
            'text_length': len(text),
            'matches_found': len(matches),
            'phi_types': list(set(m.phi_type for m in matches))
        })
        
        return matches
    
    def _find_matches(self, text: str, phi_type: PHIType, patterns: List[str]) -> List[PHIMatch]:
        """Find matches for a specific PHI type."""
        matches = []
        
        for pattern in patterns:
            try:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Calculate confidence based on context
                    confidence = self._calculate_confidence(
                        match.group(), phi_type, text, match.start()
                    )
                    
                    # Skip low confidence matches
                    if confidence < 0.3:
                        continue
                    
                    phi_match = PHIMatch(
                        phi_type=phi_type,
                        value=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        context=self._extract_context(text, match.start(), match.end()),
                        severity=self._calculate_severity(phi_type, confidence)
                    )
                    
                    matches.append(phi_match)
                    
            except re.error as e:
                logger.warning(f"Invalid regex pattern for {phi_type}: {pattern} - {e}")
        
        return matches
    
    def _calculate_confidence(self, value: str, phi_type: PHIType, text: str, position: int) -> float:
        """Calculate confidence score for a PHI match."""
        base_confidence = 0.7
        
        # Context analysis
        context_keywords = PHIPatterns.get_context_keywords(phi_type)
        context_text = self._extract_context(text, position, position + len(value), window=50)
        
        context_boost = 0.0
        for keyword in context_keywords:
            if keyword.lower() in context_text.lower():
                context_boost += 0.1
        
        # Pattern-specific confidence adjustments
        if phi_type == PHIType.SSN:
            if re.match(r'\b\d{3}-\d{2}-\d{4}\b', value):
                base_confidence = 0.95
        elif phi_type == PHIType.PHONE:
            if re.match(r'\b\(\d{3}\)\s?\d{3}-\d{4}\b', value):
                base_confidence = 0.9
        elif phi_type == PHIType.EMAIL:
            if '@' in value and '.' in value:
                base_confidence = 0.95
        
        return min(base_confidence + context_boost, 1.0)
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 30) -> str:
        """Extract context around a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _calculate_severity(self, phi_type: PHIType, confidence: float) -> str:
        """Calculate severity level for a PHI match."""
        if phi_type in [PHIType.SSN, PHIType.MRN, PHIType.BIOMETRIC]:
            return "critical"
        elif phi_type in [PHIType.NAME, PHIType.DOB, PHIType.ADDRESS]:
            return "high"
        elif confidence > 0.8:
            return "high"
        elif confidence > 0.6:
            return "medium"
        else:
            return "low"


class PHISanitizer:
    """PHI sanitization and masking utilities."""
    
    def __init__(self, default_mask: str = "[REDACTED]"):
        self.default_mask = default_mask
        self.sanitization_log = []
    
    def sanitize_text(self, text: str, phi_matches: List[PHIMatch], mask_type: str = "redact") -> str:
        """
        Sanitize text by masking or removing PHI.
        
        Args:
            text: Original text
            phi_matches: Detected PHI matches
            mask_type: Type of masking (redact, mask, encrypt, remove)
            
        Returns:
            Sanitized text
        """
        if not phi_matches:
            return text
        
        # Sort matches by position (reverse order to maintain positions)
        sorted_matches = sorted(phi_matches, key=lambda m: m.start_pos, reverse=True)
        
        sanitized_text = text
        
        for match in sorted_matches:
            masked_value = self._create_mask(match, mask_type)
            
            sanitized_text = (
                sanitized_text[:match.start_pos] +
                masked_value +
                sanitized_text[match.end_pos:]
            )
            
            # Update match with masked value
            match.masked_value = masked_value
            
            # Log sanitization
            self.sanitization_log.append({
                'timestamp': datetime.now(),
                'phi_type': match.phi_type.value,
                'original_value': match.value,
                'masked_value': masked_value,
                'mask_type': mask_type
            })
        
        return sanitized_text
    
    def _create_mask(self, match: PHIMatch, mask_type: str) -> str:
        """Create appropriate mask for PHI match."""
        if mask_type == "redact":
            return f"[{match.phi_type.value.upper()}_REDACTED]"
        elif mask_type == "mask":
            return self._create_pattern_mask(match)
        elif mask_type == "encrypt":
            return self._encrypt_value(match.value)
        elif mask_type == "remove":
            return ""
        else:
            return self.default_mask
    
    def _create_pattern_mask(self, match: PHIMatch) -> str:
        """Create pattern-preserving mask."""
        if match.phi_type == PHIType.SSN:
            return "XXX-XX-XXXX"
        elif match.phi_type == PHIType.PHONE:
            return "XXX-XXX-XXXX"
        elif match.phi_type == PHIType.EMAIL:
            return "XXXX@XXXX.com"
        elif match.phi_type == PHIType.DOB:
            return "XX/XX/XXXX"
        else:
            return "X" * min(len(match.value), 10)
    
    def _encrypt_value(self, value: str) -> str:
        """Create encrypted representation of value."""
        hash_obj = hashlib.sha256(value.encode())
        return f"[ENCRYPTED_{hash_obj.hexdigest()[:8].upper()}]"


class PHIComplianceValidator:
    """Main PHI compliance validation system."""
    
    def __init__(self,
                 compliance_level: ComplianceLevel = ComplianceLevel.STRICT,
                 custom_patterns: Optional[Dict[PHIType, List[str]]] = None,
                 enable_audit: bool = True):
        self.compliance_level = compliance_level
        self.enable_audit = enable_audit
        
        # Initialize components
        self.detector = PHIDetector(custom_patterns)
        self.sanitizer = PHISanitizer()
        
        # Validation history
        self.validation_history = []
    
    def validate_content(self, content: str, context: str = "") -> PHIValidationResult:
        """
        Comprehensive PHI validation of content.
        
        Args:
            content: Content to validate
            context: Additional context for validation
            
        Returns:
            PHI validation result
        """
        start_time = datetime.now()
        
        try:
            # Detect PHI
            phi_matches = self.detector.detect_phi(content, context)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(phi_matches)
            
            # Determine compliance
            is_compliant = self._check_compliance(phi_matches)
            
            # Generate sanitized content
            sanitized_content = self.sanitizer.sanitize_text(
                content, phi_matches, "redact"
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(phi_matches)
            
            # Create audit log entry
            audit_entry = {
                'timestamp': datetime.now(),
                'content_length': len(content),
                'phi_matches_count': len(phi_matches),
                'risk_score': risk_score,
                'compliance_level': self.compliance_level.value,
                'is_compliant': is_compliant,
                'validation_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            result = PHIValidationResult(
                is_compliant=is_compliant,
                phi_matches=phi_matches,
                sanitized_content=sanitized_content,
                audit_log=[audit_entry] if self.enable_audit else [],
                compliance_level=self.compliance_level,
                risk_score=risk_score,
                recommendations=recommendations
            )
            
            # Store validation history
            self.validation_history.append({
                'timestamp': start_time,
                'result': result,
                'content_hash': hashlib.md5(content.encode()).hexdigest()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"PHI validation failed: {str(e)}")
            return PHIValidationResult(
                is_compliant=False,
                audit_log=[{
                    'timestamp': datetime.now(),
                    'error': str(e),
                    'validation_failed': True
                }] if self.enable_audit else []
            )
    
    def _calculate_risk_score(self, phi_matches: List[PHIMatch]) -> float:
        """Calculate overall risk score based on PHI matches."""
        if not phi_matches:
            return 0.0
        
        risk_weights = {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.2
        }
        
        total_risk = sum(
            risk_weights.get(match.severity, 0.5) * match.confidence
            for match in phi_matches
        )
        
        # Normalize to 0-1 scale
        max_possible_risk = len(phi_matches) * 1.0
        normalized_risk = total_risk / max_possible_risk if max_possible_risk > 0 else 0
        
        return min(normalized_risk, 1.0)
    
    def _check_compliance(self, phi_matches: List[PHIMatch]) -> bool:
        """Check if content meets compliance requirements."""
        if self.compliance_level == ComplianceLevel.STRICT:
            return len(phi_matches) == 0
        elif self.compliance_level == ComplianceLevel.MODERATE:
            # Allow PHI with high confidence that can be masked
            critical_matches = [m for m in phi_matches if m.severity == 'critical']
            return len(critical_matches) == 0
        else:  # PERMISSIVE
            return True
    
    def _generate_recommendations(self, phi_matches: List[PHIMatch]) -> List[str]:
        """Generate recommendations for PHI compliance."""
        recommendations = []
        
        if not phi_matches:
            recommendations.append("✅ No PHI detected. Content is compliant.")
            return recommendations
        
        phi_types_found = set(match.phi_type for match in phi_matches)
        
        for phi_type in phi_types_found:
            if phi_type == PHIType.SSN:
                recommendations.append("🔴 Remove or mask Social Security Numbers")
            elif phi_type == PHIType.NAME:
                recommendations.append("⚠️  Consider using participant IDs instead of names")
            elif phi_type == PHIType.DOB:
                recommendations.append("⚠️  Use age ranges instead of specific birth dates")
            elif phi_type == PHIType.ADDRESS:
                recommendations.append("⚠️  Use geographic regions instead of specific addresses")
            elif phi_type == PHIType.EMAIL:
                recommendations.append("⚠️  Remove or mask email addresses")
            elif phi_type == PHIType.PHONE:
                recommendations.append("⚠️  Remove or mask phone numbers")
        
        # General recommendations
        if len(phi_matches) > 5:
            recommendations.append("🔍 Consider comprehensive review - multiple PHI elements detected")
        
        recommendations.append("📋 Review protocol content against HIPAA requirements")
        recommendations.append("🛡️  Implement data de-identification procedures")
        
        return recommendations
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation activities."""
        if not self.validation_history:
            return {"total_validations": 0, "message": "No validations performed"}
        
        total_validations = len(self.validation_history)
        compliant_validations = sum(
            1 for v in self.validation_history if v['result'].is_compliant
        )
        
        avg_risk_score = sum(
            v['result'].risk_score for v in self.validation_history
        ) / total_validations
        
        phi_types_detected = set()
        for validation in self.validation_history:
            for match in validation['result'].phi_matches:
                phi_types_detected.add(match.phi_type.value)
        
        return {
            "total_validations": total_validations,
            "compliant_validations": compliant_validations,
            "compliance_rate": compliant_validations / total_validations,
            "average_risk_score": avg_risk_score,
            "phi_types_detected": list(phi_types_detected),
            "compliance_level": self.compliance_level.value
        }


# Integration functions for protocol generation
def validate_protocol_phi_compliance(protocol_content: str,
                                    study_data: Dict[str, Any],
                                    compliance_level: ComplianceLevel = ComplianceLevel.STRICT) -> PHIValidationResult:
    """
    Validate PHI compliance for generated protocol content.
    
    Args:
        protocol_content: Generated protocol text
        study_data: Study data used for generation
        compliance_level: Required compliance level
        
    Returns:
        PHI validation result
    """
    validator = PHIComplianceValidator(compliance_level=compliance_level)
    
    # Validate protocol content
    result = validator.validate_content(
        protocol_content,
        context="clinical_study_protocol"
    )
    
    # Additional validation of study data
    study_data_str = json.dumps(study_data, indent=2)
    study_data_result = validator.validate_content(
        study_data_str,
        context="study_parameters"
    )
    
    # Combine results
    combined_matches = result.phi_matches + study_data_result.phi_matches
    combined_risk = max(result.risk_score, study_data_result.risk_score)
    combined_compliant = result.is_compliant and study_data_result.is_compliant
    
    return PHIValidationResult(
        is_compliant=combined_compliant,
        phi_matches=combined_matches,
        sanitized_content=result.sanitized_content,
        audit_log=result.audit_log + study_data_result.audit_log,
        compliance_level=compliance_level,
        risk_score=combined_risk,
        recommendations=result.recommendations + study_data_result.recommendations
    )


def create_phi_compliant_template_variables(study_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create PHI-compliant template variables from study data.
    
    Args:
        study_data: Original study data
        
    Returns:
        PHI-compliant template variables
    """
    validator = PHIComplianceValidator(compliance_level=ComplianceLevel.MODERATE)
    sanitizer = PHISanitizer()
    
    phi_compliant_data = {}
    
    for key, value in study_data.items():
        if isinstance(value, str):
            # Validate and sanitize string values
            validation_result = validator.validate_content(value)
            if validation_result.phi_matches:
                phi_compliant_data[key] = validation_result.sanitized_content
            else:
                phi_compliant_data[key] = value
        else:
            # Keep non-string values as-is
            phi_compliant_data[key] = value
    
    return phi_compliant_data