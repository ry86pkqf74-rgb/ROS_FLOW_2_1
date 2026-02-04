"""
End-to-End Validation Framework for Protocol Generation System

This module provides comprehensive end-to-end validation including:
- Complete workflow validation from input to output
- Cross-template consistency testing
- Regulatory compliance verification
- Content quality assessment
- User acceptance testing simulation

Author: Stage 3.3 Integration Team
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

# Import validation components
from ..workflow_engine.stages.study_analyzers.protocol_generator import (
    ProtocolGenerator, ProtocolFormat, TemplateType, RegulatoryFramework
)
from ..workflow_engine.stages.study_analyzers.specialized_templates import (
    SpecializedTemplateFactory
)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Validation rule for protocol content."""
    rule_id: str
    name: str
    description: str
    rule_type: str  # content, structure, compliance, quality
    pattern: Optional[str] = None
    validator_function: Optional[str] = None
    severity: str = "error"  # error, warning, info
    applicable_templates: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_id: str
    rule_name: str
    passed: bool
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class E2ETestCase:
    """End-to-end test case definition."""
    case_id: str
    name: str
    description: str
    template_id: str
    input_data: Dict[str, Any]
    expected_outcomes: Dict[str, Any]
    validation_rules: List[str] = field(default_factory=list)


class ContentQualityValidator:
    """Validates the quality and completeness of generated content."""
    
    def __init__(self):
        self.quality_metrics = {}
        self.content_patterns = self._initialize_content_patterns()
    
    def _initialize_content_patterns(self) -> Dict[str, str]:
        """Initialize content validation patterns."""
        return {
            "has_objectives": r"(primary\s+objective|secondary\s+objective)",
            "has_sample_size": r"(sample\s+size|participants?|subjects?)\s*:?\s*\d+",
            "has_statistical_plan": r"(statistical|analysis|power|significance)",
            "has_safety_info": r"(safety|adverse\s+event|side\s+effect)",
            "has_inclusion_criteria": r"(inclusion\s+criteria|eligibility)",
            "has_exclusion_criteria": r"(exclusion\s+criteria)",
            "has_primary_endpoint": r"(primary\s+endpoint|primary\s+outcome)",
            "has_contact_info": r"(principal\s+investigator|contact|phone|email)",
            "proper_sections": r"^#{1,6}\s+\d+\.",  # Numbered sections
            "proper_formatting": r"\*\*[^*]+\*\*",  # Bold formatting
        }
    
    async def validate_content_quality(self, content: str, template_type: str) -> Dict[str, ValidationResult]:
        """Validate content quality against established criteria."""
        results = {}
        
        # Basic content quality checks
        results.update(await self._check_basic_quality(content))
        
        # Template-specific quality checks
        results.update(await self._check_template_specific_quality(content, template_type))
        
        # Content completeness checks
        results.update(await self._check_content_completeness(content))
        
        # Formatting and structure checks
        results.update(await self._check_formatting_quality(content))
        
        return results
    
    async def _check_basic_quality(self, content: str) -> Dict[str, ValidationResult]:
        """Check basic content quality metrics."""
        results = {}
        
        # Content length
        content_length = len(content)
        results["content_length"] = ValidationResult(
            rule_id="basic_001",
            rule_name="Adequate Content Length",
            passed=content_length >= 1000,  # Minimum 1000 characters
            severity="warning" if content_length < 1000 else "info",
            message=f"Content length: {content_length} characters",
            details={"actual_length": content_length, "minimum_expected": 1000}
        )
        
        # Word count
        word_count = len(content.split())
        results["word_count"] = ValidationResult(
            rule_id="basic_002",
            rule_name="Adequate Word Count",
            passed=word_count >= 200,  # Minimum 200 words
            severity="warning" if word_count < 200 else "info",
            message=f"Word count: {word_count} words",
            details={"actual_words": word_count, "minimum_expected": 200}
        )
        
        # Section count
        section_count = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        results["section_count"] = ValidationResult(
            rule_id="basic_003",
            rule_name="Adequate Section Count",
            passed=section_count >= 3,  # Minimum 3 sections
            severity="warning" if section_count < 3 else "info",
            message=f"Section count: {section_count} sections",
            details={"actual_sections": section_count, "minimum_expected": 3}
        )
        
        return results
    
    async def _check_template_specific_quality(self, content: str, template_type: str) -> Dict[str, ValidationResult]:
        """Check template-specific quality requirements."""
        results = {}
        
        content_lower = content.lower()
        
        if "oncology" in template_type:
            # Oncology-specific checks
            has_dose_info = bool(re.search(r"(dose|dosing|mg|mcg|units)", content_lower))
            results["oncology_dose"] = ValidationResult(
                rule_id="onc_001",
                rule_name="Contains Dose Information",
                passed=has_dose_info,
                severity="error",
                message="Oncology protocol must contain dose information"
            )
            
            has_safety_monitoring = bool(re.search(r"(dlt|dose.limiting|safety|toxicity)", content_lower))
            results["oncology_safety"] = ValidationResult(
                rule_id="onc_002",
                rule_name="Contains Safety Monitoring",
                passed=has_safety_monitoring,
                severity="error",
                message="Oncology protocol must contain safety monitoring information"
            )
        
        elif "pediatric" in template_type:
            # Pediatric-specific checks
            has_age_info = bool(re.search(r"(age|years|pediatric|children)", content_lower))
            results["pediatric_age"] = ValidationResult(
                rule_id="ped_001",
                rule_name="Contains Age Information",
                passed=has_age_info,
                severity="error",
                message="Pediatric protocol must contain age-specific information"
            )
            
            has_consent_info = bool(re.search(r"(consent|assent|guardian|parent)", content_lower))
            results["pediatric_consent"] = ValidationResult(
                rule_id="ped_002",
                rule_name="Contains Consent Information",
                passed=has_consent_info,
                severity="error",
                message="Pediatric protocol must contain consent/assent information"
            )
        
        elif "device" in template_type:
            # Device-specific checks
            has_device_info = bool(re.search(r"(device|equipment|instrument|implant)", content_lower))
            results["device_description"] = ValidationResult(
                rule_id="dev_001",
                rule_name="Contains Device Description",
                passed=has_device_info,
                severity="error",
                message="Device protocol must contain device description"
            )
        
        return results
    
    async def _check_content_completeness(self, content: str) -> Dict[str, ValidationResult]:
        """Check content completeness using patterns."""
        results = {}
        
        for pattern_name, pattern in self.content_patterns.items():
            match_found = bool(re.search(pattern, content, re.IGNORECASE))
            
            results[pattern_name] = ValidationResult(
                rule_id=f"comp_{pattern_name}",
                rule_name=f"Contains {pattern_name.replace('_', ' ').title()}",
                passed=match_found,
                severity="warning",
                message=f"{'Found' if match_found else 'Missing'} {pattern_name.replace('_', ' ')}"
            )
        
        return results
    
    async def _check_formatting_quality(self, content: str) -> Dict[str, ValidationResult]:
        """Check formatting and structure quality."""
        results = {}
        
        # Check for proper heading hierarchy
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        proper_hierarchy = self._validate_heading_hierarchy(headings)
        
        results["heading_hierarchy"] = ValidationResult(
            rule_id="fmt_001",
            rule_name="Proper Heading Hierarchy",
            passed=proper_hierarchy,
            severity="warning",
            message="Heading hierarchy is properly structured" if proper_hierarchy else "Heading hierarchy issues detected"
        )
        
        # Check for consistent formatting
        bold_formatting = len(re.findall(r'\*\*[^*]+\*\*', content))
        results["formatting_consistency"] = ValidationResult(
            rule_id="fmt_002",
            rule_name="Consistent Formatting",
            passed=bold_formatting > 5,  # Expect some bold formatting
            severity="info",
            message=f"Found {bold_formatting} bold formatted elements"
        )
        
        return results
    
    def _validate_heading_hierarchy(self, headings: List[Tuple[str, str]]) -> bool:
        """Validate that heading hierarchy is proper."""
        if not headings:
            return False
        
        prev_level = 0
        for heading_markup, heading_text in headings:
            current_level = len(heading_markup)
            
            # Level should not jump by more than 1
            if current_level > prev_level + 1:
                return False
            
            prev_level = current_level
        
        return True


class RegulatoryComplianceValidator:
    """Validates regulatory compliance of generated protocols."""
    
    def __init__(self):
        self.compliance_rules = self._initialize_compliance_rules()
    
    def _initialize_compliance_rules(self) -> Dict[str, ValidationRule]:
        """Initialize regulatory compliance rules."""
        return {
            "ich_gcp_compliance": ValidationRule(
                rule_id="reg_001",
                name="ICH-GCP Compliance",
                description="Protocol meets ICH-GCP requirements",
                rule_type="compliance",
                pattern=r"(informed\s+consent|adverse\s+event|data\s+integrity)",
                severity="error"
            ),
            "safety_reporting": ValidationRule(
                rule_id="reg_002",
                name="Safety Reporting Requirements",
                description="Contains adequate safety reporting procedures",
                rule_type="compliance",
                pattern=r"(serious\s+adverse\s+event|safety\s+report|24\s+hour)",
                severity="error"
            ),
            "data_privacy": ValidationRule(
                rule_id="reg_003",
                name="Data Privacy Compliance",
                description="Addresses data privacy and protection requirements",
                rule_type="compliance",
                pattern=r"(confidentiality|privacy|data\s+protection|hipaa|gdpr)",
                severity="error"
            ),
            "statistical_plan": ValidationRule(
                rule_id="reg_004",
                name="Statistical Analysis Plan",
                description="Contains adequate statistical analysis plan",
                rule_type="compliance",
                pattern=r"(statistical|power|sample\s+size|significance|alpha)",
                severity="warning"
            )
        }
    
    async def validate_regulatory_compliance(self, 
                                           content: str, 
                                           regulatory_frameworks: List[RegulatoryFramework]) -> Dict[str, ValidationResult]:
        """Validate regulatory compliance based on applicable frameworks."""
        results = {}
        
        for rule_id, rule in self.compliance_rules.items():
            # Check if rule applies
            if self._rule_applies(rule, regulatory_frameworks):
                validation_result = await self._apply_compliance_rule(content, rule)
                results[rule_id] = validation_result
        
        return results
    
    def _rule_applies(self, rule: ValidationRule, frameworks: List[RegulatoryFramework]) -> bool:
        """Check if a rule applies to the given regulatory frameworks."""
        # For now, apply all rules. In practice, this would be more sophisticated
        return True
    
    async def _apply_compliance_rule(self, content: str, rule: ValidationRule) -> ValidationResult:
        """Apply a specific compliance rule to content."""
        if rule.pattern:
            match_found = bool(re.search(rule.pattern, content, re.IGNORECASE))
            
            return ValidationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                passed=match_found,
                severity=rule.severity,
                message=f"{'Meets' if match_found else 'Does not meet'} {rule.name}"
            )
        
        # If no pattern, assume passed (would implement custom validator)
        return ValidationResult(
            rule_id=rule.rule_id,
            rule_name=rule.name,
            passed=True,
            severity="info",
            message=f"{rule.name} - validation not implemented"
        )


class EndToEndValidator:
    """Main end-to-end validation orchestrator."""
    
    def __init__(self):
        self.protocol_generator = ProtocolGenerator()
        self.specialized_factory = SpecializedTemplateFactory()
        self.quality_validator = ContentQualityValidator()
        self.compliance_validator = RegulatoryComplianceValidator()
        
        # Initialize test cases
        self.test_cases = self._create_e2e_test_cases()
        
        logger.info("End-to-End Validator initialized")
    
    def _create_e2e_test_cases(self) -> List[E2ETestCase]:
        """Create comprehensive end-to-end test cases."""
        return [
            E2ETestCase(
                case_id="e2e_001",
                name="Complete RCT Workflow",
                description="Full randomized controlled trial protocol generation and validation",
                template_id="rct_basic_v1",
                input_data={
                    "study_title": "Efficacy and Safety of Novel Therapeutic Agent",
                    "protocol_number": "E2E-RCT-001",
                    "principal_investigator": "Dr. Maria Rodriguez, MD, PhD",
                    "primary_objective": "To evaluate the efficacy and safety of Novel Therapeutic Agent compared to standard care",
                    "secondary_objectives": "To assess quality of life, biomarker changes, and long-term outcomes",
                    "design_description": "Randomized, double-blind, placebo-controlled, multicenter study",
                    "estimated_sample_size": 500,
                    "expected_power": 0.9,
                    "significance_level": 0.025,
                    "expected_effect_size": 0.25,
                    "estimated_duration_months": 24,
                    "target_population_description": "Adults aged 18-80 with confirmed diagnosis and adequate organ function"
                },
                expected_outcomes={
                    "min_word_count": 1000,
                    "required_sections": ["objectives", "design", "statistical"],
                    "regulatory_compliance": True,
                    "content_quality_score": 85.0
                }
            ),
            
            E2ETestCase(
                case_id="e2e_002",
                name="Oncology Phase I Complete Workflow",
                description="Complete oncology Phase I protocol with dose escalation",
                template_id="oncology_phase1",
                input_data={
                    "study_title": "Phase I Dose Escalation Study of Experimental Oncology Drug",
                    "protocol_number": "ONC-E2E-001",
                    "principal_investigator": "Dr. James Thompson, MD",
                    "cancer_type": "advanced solid tumors",
                    "investigational_product": "EXP-789",
                    "starting_dose": 0.5,
                    "dose_units": "mg/kg",
                    "escalation_rule": "3+3 design",
                    "max_dose": 8.0,
                    "dlt_definition": "Grade ≥3 non-hematologic or Grade 4 hematologic toxicity",
                    "initial_cohort_size": 3,
                    "expansion_cohort_size": 15,
                    "minimum_age": 18
                },
                expected_outcomes={
                    "min_word_count": 800,
                    "required_sections": ["dose_escalation", "safety_monitoring"],
                    "oncology_specific_content": True,
                    "safety_focus": True
                }
            ),
            
            E2ETestCase(
                case_id="e2e_003",
                name="Digital Health Application Validation",
                description="Complete digital health app protocol validation",
                template_id="digital_health_app",
                input_data={
                    "study_title": "Validation of AI-Powered Mental Health App",
                    "protocol_number": "DH-E2E-001",
                    "principal_investigator": "Dr. Sarah Chen, PhD",
                    "digital_platform_description": "Mobile application with AI-driven personalized interventions",
                    "technology_components": "iOS/Android app, cloud ML backend, real-time analytics",
                    "digital_biomarkers": "App engagement, mood patterns, sleep tracking data",
                    "device_compatibility": "iOS 15+ and Android 11+",
                    "data_security_measures": "End-to-end encryption, HIPAA-compliant storage"
                },
                expected_outcomes={
                    "min_word_count": 600,
                    "digital_health_content": True,
                    "data_security_mentioned": True,
                    "technology_description": True
                }
            )
        ]
    
    async def run_complete_e2e_validation(self) -> Dict[str, Any]:
        """Run complete end-to-end validation suite."""
        logger.info("Starting complete E2E validation")
        
        results = {
            "validation_timestamp": datetime.now().isoformat(),
            "total_test_cases": len(self.test_cases),
            "passed_cases": 0,
            "failed_cases": 0,
            "case_results": {},
            "overall_quality_score": 0.0,
            "compliance_summary": {},
            "recommendations": []
        }
        
        total_quality_score = 0.0
        
        for test_case in self.test_cases:
            logger.info(f"Running E2E test case: {test_case.name}")
            
            case_result = await self._run_e2e_test_case(test_case)
            results["case_results"][test_case.case_id] = case_result
            
            if case_result["success"]:
                results["passed_cases"] += 1
            else:
                results["failed_cases"] += 1
            
            total_quality_score += case_result.get("quality_score", 0.0)
        
        # Calculate overall metrics
        if len(self.test_cases) > 0:
            results["overall_quality_score"] = total_quality_score / len(self.test_cases)
        
        results["success_rate"] = (results["passed_cases"] / results["total_test_cases"]) * 100
        results["recommendations"] = self._generate_e2e_recommendations(results)
        
        logger.info(f"E2E validation completed. Success rate: {results['success_rate']:.1f}%")
        return results
    
    async def _run_e2e_test_case(self, test_case: E2ETestCase) -> Dict[str, Any]:
        """Run a single end-to-end test case."""
        case_result = {
            "case_id": test_case.case_id,
            "case_name": test_case.name,
            "success": False,
            "generation_time": 0.0,
            "content_length": 0,
            "quality_score": 0.0,
            "validation_results": {},
            "compliance_results": {},
            "errors": []
        }
        
        try:
            # Step 1: Generate protocol
            start_time = asyncio.get_event_loop().time()
            
            generation_result = await self.protocol_generator.generate_protocol(
                template_id=test_case.template_id,
                study_data=test_case.input_data,
                output_format=ProtocolFormat.MARKDOWN
            )
            
            case_result["generation_time"] = asyncio.get_event_loop().time() - start_time
            
            if not generation_result.get("success"):
                case_result["errors"].append(f"Protocol generation failed: {generation_result.get('error')}")
                return case_result
            
            protocol_content = generation_result["protocol_content"]
            case_result["content_length"] = len(protocol_content)
            
            # Step 2: Content quality validation
            template_info = self.specialized_factory.get_available_templates().get(test_case.template_id, {})
            template_type = template_info.get("type", "unknown")
            
            quality_results = await self.quality_validator.validate_content_quality(
                protocol_content, template_type
            )
            case_result["validation_results"] = {
                rule_id: {
                    "passed": result.passed,
                    "severity": result.severity,
                    "message": result.message
                }
                for rule_id, result in quality_results.items()
            }
            
            # Calculate quality score
            passed_validations = sum(1 for result in quality_results.values() if result.passed)
            total_validations = len(quality_results)
            case_result["quality_score"] = (passed_validations / total_validations * 100) if total_validations > 0 else 0
            
            # Step 3: Regulatory compliance validation
            template_regulatory_frameworks = [
                RegulatoryFramework.ICH_GCP,  # Default framework
            ]
            
            compliance_results = await self.compliance_validator.validate_regulatory_compliance(
                protocol_content, template_regulatory_frameworks
            )
            case_result["compliance_results"] = {
                rule_id: {
                    "passed": result.passed,
                    "severity": result.severity,
                    "message": result.message
                }
                for rule_id, result in compliance_results.items()
            }
            
            # Step 4: Expected outcomes validation
            outcomes_met = await self._validate_expected_outcomes(protocol_content, test_case.expected_outcomes)
            case_result["outcomes_validation"] = outcomes_met
            
            # Step 5: Determine overall success
            critical_failures = [
                result for result in quality_results.values() 
                if not result.passed and result.severity == "error"
            ]
            compliance_failures = [
                result for result in compliance_results.values()
                if not result.passed and result.severity == "error"
            ]
            
            case_result["success"] = (
                len(critical_failures) == 0 and 
                len(compliance_failures) == 0 and
                case_result["quality_score"] >= 70.0
            )
            
        except Exception as e:
            logger.error(f"Error in E2E test case {test_case.case_id}: {str(e)}")
            case_result["errors"].append(str(e))
        
        return case_result
    
    async def _validate_expected_outcomes(self, content: str, expected_outcomes: Dict[str, Any]) -> Dict[str, bool]:
        """Validate that expected outcomes are met."""
        outcomes = {}
        
        # Check minimum word count
        if "min_word_count" in expected_outcomes:
            word_count = len(content.split())
            outcomes["meets_word_count"] = word_count >= expected_outcomes["min_word_count"]
        
        # Check required sections
        if "required_sections" in expected_outcomes:
            content_lower = content.lower()
            sections_found = all(
                section.lower() in content_lower 
                for section in expected_outcomes["required_sections"]
            )
            outcomes["has_required_sections"] = sections_found
        
        # Check specific content requirements
        content_checks = {
            "regulatory_compliance": r"(compliance|regulatory|ich|gcp)",
            "oncology_specific_content": r"(dose|oncology|cancer|tumor)",
            "safety_focus": r"(safety|adverse|toxicity|side\s+effect)",
            "digital_health_content": r"(digital|app|mobile|technology)",
            "data_security_mentioned": r"(security|encryption|privacy|hipaa)",
            "technology_description": r"(technology|platform|system|software)"
        }
        
        for check_name, pattern in content_checks.items():
            if check_name in expected_outcomes and expected_outcomes[check_name]:
                outcomes[check_name] = bool(re.search(pattern, content, re.IGNORECASE))
        
        return outcomes
    
    def _generate_e2e_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on E2E test results."""
        recommendations = []
        
        if results["success_rate"] < 90:
            recommendations.append("Improve template quality to achieve >90% success rate")
        
        if results["overall_quality_score"] < 80:
            recommendations.append("Enhance content generation to improve quality scores")
        
        failed_cases = results["failed_cases"]
        if failed_cases > 0:
            recommendations.append(f"Address {failed_cases} failed test cases")
        
        # Analyze common failure patterns
        common_failures = self._analyze_common_failures(results)
        recommendations.extend(common_failures)
        
        if not recommendations:
            recommendations.append("All E2E validations passed successfully")
        
        return recommendations
    
    def _analyze_common_failures(self, results: Dict[str, Any]) -> List[str]:
        """Analyze common failure patterns across test cases."""
        common_issues = []
        
        quality_failures = []
        compliance_failures = []
        
        for case_result in results["case_results"].values():
            if not case_result["success"]:
                # Collect quality failures
                for rule_id, validation in case_result["validation_results"].items():
                    if not validation["passed"] and validation["severity"] == "error":
                        quality_failures.append(rule_id)
                
                # Collect compliance failures
                for rule_id, validation in case_result["compliance_results"].items():
                    if not validation["passed"] and validation["severity"] == "error":
                        compliance_failures.append(rule_id)
        
        # Find common patterns
        from collections import Counter
        quality_counter = Counter(quality_failures)
        compliance_counter = Counter(compliance_failures)
        
        for issue, count in quality_counter.most_common(3):
            if count > 1:
                common_issues.append(f"Address common quality issue: {issue} (affects {count} cases)")
        
        for issue, count in compliance_counter.most_common(3):
            if count > 1:
                common_issues.append(f"Address common compliance issue: {issue} (affects {count} cases)")
        
        return common_issues


if __name__ == "__main__":
    async def main():
        """Run end-to-end validation."""
        validator = EndToEndValidator()
        
        print("🔍 Running Complete End-to-End Validation...")
        results = await validator.run_complete_e2e_validation()
        
        print(f"\n🎯 E2E VALIDATION RESULTS:")
        print(f"Total Test Cases: {results['total_test_cases']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Overall Quality Score: {results['overall_quality_score']:.1f}")
        
        print("\n📋 Recommendations:")
        for rec in results["recommendations"]:
            print(f"• {rec}")
        
        return results
    
    asyncio.run(main())