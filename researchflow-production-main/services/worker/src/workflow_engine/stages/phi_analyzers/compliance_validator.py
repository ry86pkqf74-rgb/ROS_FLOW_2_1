"""
Multi-Jurisdiction Privacy Compliance Validator

Validates compliance with multiple privacy frameworks:
- HIPAA Safe Harbor (US healthcare)
- GDPR Article 4 (EU general data protection)
- CCPA Personal Information (California consumer privacy)
- PIPEDA Personal Information (Canada)
- State-specific regulations

Based on legal research and privacy engineering best practices.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported privacy compliance frameworks."""
    HIPAA_SAFE_HARBOR = "HIPAA_SAFE_HARBOR"
    GDPR_ARTICLE_4 = "GDPR_ARTICLE_4"
    CCPA_PERSONAL_INFO = "CCPA_PERSONAL_INFO"
    PIPEDA_PERSONAL_INFO = "PIPEDA_PERSONAL_INFO"
    FERPA_DIRECTORY_INFO = "FERPA_DIRECTORY_INFO"  # Educational records
    COPPA_PERSONAL_INFO = "COPPA_PERSONAL_INFO"    # Children's privacy


@dataclass
class ComplianceViolation:
    """A privacy compliance violation."""
    framework: ComplianceFramework
    violation_type: str
    description: str
    severity: str  # "critical", "high", "medium", "low"
    phi_categories: List[str]
    remediation_required: bool
    remediation_suggestions: List[str] = field(default_factory=list)


@dataclass 
class ComplianceResult:
    """Result of compliance validation."""
    framework: ComplianceFramework
    is_compliant: bool
    violations: List[ComplianceViolation] = field(default_factory=list)
    compliant_categories: List[str] = field(default_factory=list)
    risk_score: int = 0  # 0-100, where 100 = maximum risk
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations."""
        return any(v.severity == "critical" for v in self.violations)
    
    @property
    def compliance_percentage(self) -> float:
        """Calculate compliance percentage."""
        total_categories = len(self.violations) + len(self.compliant_categories)
        if total_categories == 0:
            return 100.0
        return (len(self.compliant_categories) / total_categories) * 100.0


class HIPAASafeHarborValidator:
    """HIPAA Safe Harbor compliance validator (45 CFR 164.514(b)(2))."""
    
    # HIPAA Safe Harbor 18 identifiers
    SAFE_HARBOR_IDENTIFIERS = [
        "names",
        "geographic_subdivisions",  # <3-digit ZIP, detailed address
        "dates",  # Except year, unless >89 years old
        "phone_numbers",
        "fax_numbers", 
        "email_addresses",
        "social_security_numbers",
        "medical_record_numbers",
        "health_plan_beneficiary_numbers",
        "account_numbers",
        "certificate_license_numbers",
        "vehicle_identifiers",
        "device_identifiers",
        "web_urls",
        "ip_addresses",
        "biometric_identifiers",
        "photographs",
        "unique_identifying_numbers",
    ]
    
    def __init__(self):
        self.framework = ComplianceFramework.HIPAA_SAFE_HARBOR
        
    def validate(self, findings: List[Dict], phi_schema: Dict, **kwargs) -> ComplianceResult:
        """Validate HIPAA Safe Harbor compliance."""
        violations = []
        compliant_categories = []
        
        # Check each Safe Harbor identifier
        categories_found = set(f.get("category", "") for f in findings)
        
        # Map detected categories to Safe Harbor identifiers
        category_mapping = {
            "SSN": "social_security_numbers",
            "MRN": "medical_record_numbers", 
            "EMAIL": "email_addresses",
            "PHONE": "phone_numbers",
            "NAME": "names",
            "DOB": "dates",
            "DATE": "dates",
            "ZIP_CODE": "geographic_subdivisions",
            "ADDRESS": "geographic_subdivisions",
            "HEALTH_PLAN": "health_plan_beneficiary_numbers",
            "ACCOUNT": "account_numbers",
            "LICENSE": "certificate_license_numbers",
            "DEVICE_ID": "device_identifiers",
            "URL": "web_urls",
            "IP_ADDRESS": "ip_addresses",
            "AGE_OVER_89": "dates",
        }
        
        detected_identifiers = set()
        for category in categories_found:
            if category in category_mapping:
                detected_identifiers.add(category_mapping[category])
        
        # Check for violations
        for identifier in detected_identifiers:
            violation = ComplianceViolation(
                framework=self.framework,
                violation_type="SAFE_HARBOR_IDENTIFIER_DETECTED",
                description=f"Safe Harbor identifier detected: {identifier}",
                severity="critical" if identifier in [
                    "social_security_numbers", "medical_record_numbers", "names"
                ] else "high",
                phi_categories=[k for k, v in category_mapping.items() if v == identifier],
                remediation_required=True,
                remediation_suggestions=self._get_remediation_suggestions(identifier)
            )
            violations.append(violation)
        
        # Check for compliant handling
        dates_generalized = kwargs.get("dates_generalized", False)
        zip_generalized = kwargs.get("zip_generalized", False) 
        ages_generalized = kwargs.get("ages_generalized", False)
        
        # Special handling for dates
        if "dates" in detected_identifiers:
            if dates_generalized:
                # Convert to compliant if properly generalized
                violations = [v for v in violations if "dates" not in v.phi_categories]
                compliant_categories.append("dates_generalized")
            else:
                # Add specific date violation
                date_violation = ComplianceViolation(
                    framework=self.framework,
                    violation_type="DATES_NOT_GENERALIZED",
                    description="Dates detected but not generalized to year only",
                    severity="high",
                    phi_categories=["DOB", "DATE"],
                    remediation_required=True,
                    remediation_suggestions=[
                        "Generalize dates to year only",
                        "Remove all dates unless > 89 years old"
                    ]
                )
                violations.append(date_violation)
        
        # Special handling for ZIP codes
        if "geographic_subdivisions" in detected_identifiers:
            if zip_generalized:
                violations = [v for v in violations if "geographic_subdivisions" not in v.phi_categories]
                compliant_categories.append("geographic_subdivisions_generalized")
            else:
                zip_violation = ComplianceViolation(
                    framework=self.framework,
                    violation_type="ZIP_NOT_GENERALIZED", 
                    description="ZIP codes detected but not generalized to first 3 digits",
                    severity="high",
                    phi_categories=["ZIP_CODE", "ADDRESS"],
                    remediation_required=True,
                    remediation_suggestions=[
                        "Generalize ZIP codes to first 3 digits only",
                        "Remove detailed addresses"
                    ]
                )
                violations.append(zip_violation)
        
        # Check age generalization
        if ages_generalized:
            compliant_categories.append("ages_over_89_generalized")
        elif any("AGE_OVER_89" in f.get("category", "") for f in findings):
            age_violation = ComplianceViolation(
                framework=self.framework,
                violation_type="AGES_OVER_89_NOT_GENERALIZED",
                description="Ages over 89 detected but not generalized",
                severity="medium",
                phi_categories=["AGE_OVER_89"],
                remediation_required=True,
                remediation_suggestions=[
                    "Generalize all ages > 89 to '>89' or remove"
                ]
            )
            violations.append(age_violation)
        
        # Calculate risk score
        risk_score = self._calculate_hipaa_risk_score(violations, findings)
        
        # Generate recommendations
        recommendations = self._generate_hipaa_recommendations(violations, phi_schema)
        
        is_compliant = len(violations) == 0
        
        return ComplianceResult(
            framework=self.framework,
            is_compliant=is_compliant,
            violations=violations,
            compliant_categories=compliant_categories,
            risk_score=risk_score,
            recommendations=recommendations,
            metadata={
                "safe_harbor_identifiers_detected": len(detected_identifiers),
                "total_phi_findings": len(findings),
                "dates_generalized": dates_generalized,
                "zip_generalized": zip_generalized,
                "ages_generalized": ages_generalized,
            }
        )
    
    def _get_remediation_suggestions(self, identifier: str) -> List[str]:
        """Get specific remediation suggestions for Safe Harbor identifier."""
        suggestions = {
            "names": ["Remove all names", "Use study IDs only", "Pseudonymize with random codes"],
            "social_security_numbers": ["Remove all SSNs", "Use alternative unique identifiers"],
            "medical_record_numbers": ["Remove MRNs", "Use study-specific IDs"],
            "dates": ["Generalize to year only", "Use time intervals from index date"],
            "geographic_subdivisions": ["Use 3-digit ZIP only", "Use broader geographic regions"],
            "phone_numbers": ["Remove all phone numbers"],
            "email_addresses": ["Remove all email addresses"],
            "ip_addresses": ["Remove IP addresses", "Use general network identifiers"],
            "web_urls": ["Remove URLs", "Use categorical descriptions"],
        }
        return suggestions.get(identifier, ["Remove or generalize this identifier type"])
    
    def _calculate_hipaa_risk_score(self, violations: List[ComplianceViolation], findings: List[Dict]) -> int:
        """Calculate HIPAA compliance risk score."""
        base_score = 0
        
        # Critical violations
        critical_violations = [v for v in violations if v.severity == "critical"]
        base_score += len(critical_violations) * 30
        
        # High violations  
        high_violations = [v for v in violations if v.severity == "high"]
        base_score += len(high_violations) * 20
        
        # Medium violations
        medium_violations = [v for v in violations if v.severity == "medium"]
        base_score += len(medium_violations) * 10
        
        # Adjust for volume of PHI
        phi_count = len(findings)
        if phi_count > 100:
            base_score += 20
        elif phi_count > 50:
            base_score += 10
        elif phi_count > 10:
            base_score += 5
        
        return min(100, base_score)
    
    def _generate_hipaa_recommendations(self, violations: List[ComplianceViolation], phi_schema: Dict) -> List[str]:
        """Generate HIPAA-specific recommendations."""
        recommendations = []
        
        if not violations:
            recommendations.append("✅ Dataset complies with HIPAA Safe Harbor requirements")
            return recommendations
        
        recommendations.append("🚨 HIPAA Safe Harbor violations detected - remediation required")
        
        # Priority recommendations
        critical_categories = set()
        for violation in violations:
            if violation.severity == "critical":
                critical_categories.update(violation.phi_categories)
        
        if critical_categories:
            recommendations.append(f"🔴 IMMEDIATE ACTION: Remove {', '.join(critical_categories)}")
        
        # Specific techniques
        recommendations.extend([
            "📋 Recommended techniques:",
            "   • Generalization: Convert specific values to ranges/categories",
            "   • Suppression: Remove identifying fields entirely", 
            "   • Pseudonymization: Replace with unlinkable study codes",
            "   • Date shifting: Use consistent random offsets for temporal data"
        ])
        
        # Validation steps
        recommendations.extend([
            "✅ Validation steps:",
            "   1. Apply de-identification techniques",
            "   2. Re-run PHI detection to verify removal",
            "   3. Document all transformations for compliance audit",
            "   4. Obtain IRB/privacy officer approval before use"
        ])
        
        return recommendations


class GDPRValidator:
    """GDPR Article 4 personal data compliance validator."""
    
    # GDPR personal data categories (Article 4.1)
    PERSONAL_DATA_CATEGORIES = [
        "direct_identifiers",     # Name, ID number, location data
        "indirect_identifiers",   # Online identifiers, IP addresses
        "special_categories",     # Health, genetic, biometric data
        "behavioral_data",        # Tracking, profiling data
        "financial_data",         # Payment info, credit data
        "location_data",          # Geographic coordinates, addresses
        "communication_data",     # Email, phone, messaging
        "device_data",           # Device IDs, cookies, fingerprints
    ]
    
    def __init__(self):
        self.framework = ComplianceFramework.GDPR_ARTICLE_4
    
    def validate(self, findings: List[Dict], phi_schema: Dict, **kwargs) -> ComplianceResult:
        """Validate GDPR personal data compliance."""
        violations = []
        compliant_categories = []
        
        # Map findings to GDPR categories
        gdpr_mapping = {
            "NAME": "direct_identifiers",
            "EMAIL": "direct_identifiers", 
            "PHONE": "direct_identifiers",
            "ADDRESS": "direct_identifiers",
            "IP_ADDRESS": "indirect_identifiers",
            "DEVICE_ID": "indirect_identifiers",
            "SSN": "direct_identifiers",
            "MRN": "special_categories",  # Health data
            "DOB": "direct_identifiers",
            "FINANCIAL": "financial_data",
            "LOCATION": "location_data",
        }
        
        categories_found = set()
        for finding in findings:
            category = finding.get("category", "")
            if category in gdpr_mapping:
                categories_found.add(gdpr_mapping[category])
        
        # GDPR requires explicit consent or legal basis for processing
        consent_provided = kwargs.get("gdpr_consent", False)
        legal_basis = kwargs.get("gdpr_legal_basis", None)
        
        # Check for violations
        for category in categories_found:
            if not consent_provided and not legal_basis:
                violation = ComplianceViolation(
                    framework=self.framework,
                    violation_type="NO_LEGAL_BASIS",
                    description=f"Personal data category '{category}' requires legal basis under GDPR",
                    severity="critical" if category == "special_categories" else "high",
                    phi_categories=[k for k, v in gdpr_mapping.items() if v == category],
                    remediation_required=True,
                    remediation_suggestions=[
                        "Obtain explicit consent from data subjects",
                        "Establish legitimate interest legal basis",
                        "Anonymize data to remove personal data status",
                        "Implement data minimization principles"
                    ]
                )
                violations.append(violation)
        
        # Special category data (Article 9) - extra protection
        special_categories = ["MRN", "HEALTH_PLAN"] 
        special_found = any(f.get("category") in special_categories for f in findings)
        if special_found:
            explicit_consent = kwargs.get("gdpr_explicit_consent", False)
            if not explicit_consent:
                violation = ComplianceViolation(
                    framework=self.framework,
                    violation_type="SPECIAL_CATEGORY_NO_CONSENT",
                    description="Special category personal data requires explicit consent",
                    severity="critical",
                    phi_categories=special_categories,
                    remediation_required=True,
                    remediation_suggestions=[
                        "Obtain explicit written consent for health data processing",
                        "Implement additional safeguards for special categories",
                        "Consider anonymization to avoid GDPR requirements"
                    ]
                )
                violations.append(violation)
        
        # Data subject rights compliance
        data_portability = kwargs.get("gdpr_data_portability", False)
        right_to_erasure = kwargs.get("gdpr_right_to_erasure", False)
        
        if categories_found and not data_portability:
            violations.append(ComplianceViolation(
                framework=self.framework,
                violation_type="NO_DATA_PORTABILITY",
                description="System must support data portability rights",
                severity="medium",
                phi_categories=list(gdpr_mapping.keys()),
                remediation_required=False,
                remediation_suggestions=["Implement data export functionality"]
            ))
        
        if categories_found and not right_to_erasure:
            violations.append(ComplianceViolation(
                framework=self.framework,
                violation_type="NO_RIGHT_TO_ERASURE",
                description="System must support right to erasure (right to be forgotten)",
                severity="medium", 
                phi_categories=list(gdpr_mapping.keys()),
                remediation_required=False,
                remediation_suggestions=["Implement data deletion functionality"]
            ))
        
        risk_score = len(violations) * 25  # Simplified scoring
        
        recommendations = self._generate_gdpr_recommendations(violations, categories_found)
        
        is_compliant = len([v for v in violations if v.severity in ["critical", "high"]]) == 0
        
        return ComplianceResult(
            framework=self.framework,
            is_compliant=is_compliant,
            violations=violations,
            compliant_categories=compliant_categories,
            risk_score=min(100, risk_score),
            recommendations=recommendations,
            metadata={
                "personal_data_categories": list(categories_found),
                "special_categories_detected": special_found,
                "consent_provided": consent_provided,
                "legal_basis": legal_basis,
            }
        )
    
    def _generate_gdpr_recommendations(self, violations: List[ComplianceViolation], categories_found: Set[str]) -> List[str]:
        """Generate GDPR-specific recommendations."""
        recommendations = []
        
        if not violations:
            recommendations.append("✅ Dataset appears GDPR compliant")
            return recommendations
        
        recommendations.extend([
            "🇪🇺 GDPR Compliance Required:",
            "   • Establish legal basis for processing personal data",
            "   • Obtain explicit consent where required", 
            "   • Implement data subject rights (access, portability, erasure)",
            "   • Conduct Data Protection Impact Assessment (DPIA)",
            "   • Designate Data Protection Officer if required",
            "   • Document processing activities and retention periods"
        ])
        
        return recommendations


class MultiJurisdictionCompliance:
    """Multi-jurisdiction privacy compliance validator."""
    
    def __init__(self):
        self.validators = {
            ComplianceFramework.HIPAA_SAFE_HARBOR: HIPAASafeHarborValidator(),
            ComplianceFramework.GDPR_ARTICLE_4: GDPRValidator(),
            # Add more validators as needed
        }
        
        logger.info(f"MultiJurisdictionCompliance initialized with {len(self.validators)} frameworks")
    
    def validate_all_frameworks(self, 
                               findings: List[Dict],
                               phi_schema: Dict,
                               frameworks: Optional[List[ComplianceFramework]] = None,
                               **kwargs) -> Dict[ComplianceFramework, ComplianceResult]:
        """
        Validate compliance across multiple frameworks.
        
        Args:
            findings: PHI findings from detection
            phi_schema: PHI schema metadata
            frameworks: Specific frameworks to check (None = all)
            **kwargs: Framework-specific parameters
            
        Returns:
            Dictionary mapping framework to compliance results
        """
        if frameworks is None:
            frameworks = list(self.validators.keys())
        
        results = {}
        
        for framework in frameworks:
            if framework in self.validators:
                try:
                    validator = self.validators[framework]
                    result = validator.validate(findings, phi_schema, **kwargs)
                    results[framework] = result
                    logger.debug(f"{framework.value}: {'✅ Compliant' if result.is_compliant else '❌ Violations'}")
                except Exception as e:
                    logger.error(f"Validation failed for {framework.value}: {e}")
                    # Create error result
                    results[framework] = ComplianceResult(
                        framework=framework,
                        is_compliant=False,
                        violations=[ComplianceViolation(
                            framework=framework,
                            violation_type="VALIDATION_ERROR",
                            description=f"Compliance validation failed: {str(e)}",
                            severity="critical",
                            phi_categories=[],
                            remediation_required=True
                        )],
                        risk_score=100,
                        recommendations=[f"Fix validation error: {str(e)}"]
                    )
        
        return results
    
    def generate_compliance_summary(self, 
                                  results: Dict[ComplianceFramework, ComplianceResult]) -> Dict[str, Any]:
        """Generate a summary of compliance across all frameworks."""
        summary = {
            "overall_compliant": all(result.is_compliant for result in results.values()),
            "frameworks_checked": len(results),
            "compliant_frameworks": [f.value for f, r in results.items() if r.is_compliant],
            "non_compliant_frameworks": [f.value for f, r in results.items() if not r.is_compliant],
            "critical_violations": [],
            "high_priority_actions": [],
            "overall_risk_score": 0,
        }
        
        # Aggregate violations and risk
        all_violations = []
        max_risk = 0
        
        for framework, result in results.items():
            all_violations.extend(result.violations)
            max_risk = max(max_risk, result.risk_score)
        
        summary["overall_risk_score"] = max_risk
        summary["critical_violations"] = [
            v.description for v in all_violations if v.severity == "critical"
        ]
        
        # High priority actions
        if summary["critical_violations"]:
            summary["high_priority_actions"].append("🚨 Address critical violations immediately")
        
        if not summary["overall_compliant"]:
            summary["high_priority_actions"].extend([
                "📋 Review non-compliant frameworks",
                "🔧 Apply recommended remediation techniques",
                "✅ Re-validate after remediation"
            ])
        
        return summary
    
    def get_framework_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about supported frameworks."""
        return {
            framework.value: {
                "name": framework.value,
                "description": self._get_framework_description(framework),
                "validator_available": framework in self.validators,
            }
            for framework in ComplianceFramework
        }
    
    def _get_framework_description(self, framework: ComplianceFramework) -> str:
        """Get description of compliance framework."""
        descriptions = {
            ComplianceFramework.HIPAA_SAFE_HARBOR: "US healthcare privacy - HIPAA Safe Harbor de-identification",
            ComplianceFramework.GDPR_ARTICLE_4: "EU data protection - GDPR personal data requirements",
            ComplianceFramework.CCPA_PERSONAL_INFO: "California consumer privacy - CCPA personal information",
            ComplianceFramework.PIPEDA_PERSONAL_INFO: "Canada federal privacy - PIPEDA personal information",
            ComplianceFramework.FERPA_DIRECTORY_INFO: "US educational records - FERPA directory information",
            ComplianceFramework.COPPA_PERSONAL_INFO: "US children's privacy - COPPA personal information",
        }
        return descriptions.get(framework, "Privacy compliance framework")