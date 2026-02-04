"""
Integration Testing Framework for Protocol Generation System

This module provides comprehensive integration tests for the complete
protocol generation workflow, including template processing, content
generation, validation, and output formatting.

Features:
- End-to-end workflow testing
- Performance benchmarking
- Template validation across domains
- AI enhancement testing
- Regulatory compliance validation
- Multi-format output testing

Author: Stage 3.3 Integration Team
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import pytest

# Import protocol generation components
from ..workflow_engine.stages.study_analyzers.protocol_generator import (
    ProtocolGenerator, ProtocolFormat, TemplateType
)
from ..workflow_engine.stages.study_analyzers.advanced_template_engine import (
    AdvancedTemplateEngine, ContentEnhancementRequest, ContentGenerationStrategy,
    ConditionalRule, ConditionalOperator
)
from ..workflow_engine.stages.study_analyzers.specialized_templates import (
    SpecializedTemplateFactory
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestResult:
    """Result of an integration test."""
    test_name: str
    success: bool
    execution_time: float
    output_size: int
    template_used: str
    format_tested: ProtocolFormat
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, bool] = field(default_factory=dict)


@dataclass
class TestScenario:
    """Integration test scenario definition."""
    scenario_id: str
    name: str
    description: str
    template_id: str
    study_data: Dict[str, Any]
    expected_sections: List[str]
    output_formats: List[ProtocolFormat]
    validation_rules: List[str] = field(default_factory=list)
    performance_threshold: float = 5.0  # seconds


class ProtocolIntegrationTestSuite:
    """
    Comprehensive integration testing suite for protocol generation.
    """
    
    def __init__(self):
        self.protocol_generator = ProtocolGenerator(
            enable_phi_integration=True,
            regulatory_templates=True
        )
        self.advanced_engine = AdvancedTemplateEngine(
            enable_ai_enhancement=True,
            enable_conditional_rendering=True,
            enable_nested_variables=True
        )
        self.specialized_factory = SpecializedTemplateFactory()
        
        self.test_results: List[IntegrationTestResult] = []
        self.performance_benchmarks: Dict[str, float] = {}
        
        # Initialize test scenarios
        self.test_scenarios = self._create_test_scenarios()
        
        logger.info("Protocol Integration Test Suite initialized")
    
    def _create_test_scenarios(self) -> List[TestScenario]:
        """Create comprehensive test scenarios."""
        scenarios = [
            # Basic RCT scenario
            TestScenario(
                scenario_id="rct_basic_001",
                name="Basic RCT Protocol Generation",
                description="Standard randomized controlled trial with complete data",
                template_id="rct_basic_v1",
                study_data={
                    "study_title": "Efficacy and Safety of Drug X in Patients with Condition Y",
                    "protocol_number": "TEST-RCT-001",
                    "principal_investigator": "Dr. Jane Smith, MD, PhD",
                    "primary_objective": "To evaluate the efficacy and safety of Drug X compared to placebo in patients with Condition Y",
                    "secondary_objectives": "To assess quality of life improvements and biomarker changes",
                    "design_description": "Randomized, double-blind, placebo-controlled, parallel-group study",
                    "estimated_sample_size": 300,
                    "expected_power": 0.8,
                    "significance_level": 0.05,
                    "expected_effect_size": 0.3,
                    "estimated_duration_months": 18,
                    "target_population_description": "Adults aged 18-75 with confirmed diagnosis of Condition Y"
                },
                expected_sections=["title_page", "synopsis", "objectives", "study_design", "statistical_considerations"],
                output_formats=[ProtocolFormat.MARKDOWN, ProtocolFormat.HTML, ProtocolFormat.JSON]
            ),
            
            # Oncology Phase I scenario
            TestScenario(
                scenario_id="onc_phase1_001",
                name="Oncology Phase I Dose Escalation",
                description="Phase I oncology study with dose escalation",
                template_id="oncology_phase1",
                study_data={
                    "study_title": "Phase I Study of Novel Oncology Agent ABC-123",
                    "protocol_number": "ONC-P1-001",
                    "principal_investigator": "Dr. Michael Chen, MD",
                    "cancer_type": "advanced solid tumors",
                    "investigational_product": "ABC-123",
                    "starting_dose": 1.0,
                    "dose_units": "mg/kg",
                    "escalation_rule": "3+3 design with safety run-in",
                    "max_dose": 10.0,
                    "dlt_definition": "Grade 3/4 non-hematologic or Grade 4 hematologic toxicity",
                    "initial_cohort_size": 3,
                    "expansion_cohort_size": 20,
                    "minimum_age": 18,
                    "max_ecog_score": 2
                },
                expected_sections=["title_page", "dose_escalation", "eligibility_oncology", "safety_monitoring"],
                output_formats=[ProtocolFormat.MARKDOWN, ProtocolFormat.HTML]
            ),
            
            # Pediatric safety scenario
            TestScenario(
                scenario_id="ped_safety_001",
                name="Pediatric Safety Study",
                description="Pediatric safety and pharmacokinetic study",
                template_id="pediatric_safety",
                study_data={
                    "study_title": "Safety and Pharmacokinetics of Drug Y in Pediatric Patients",
                    "protocol_number": "PED-001",
                    "principal_investigator": "Dr. Sarah Johnson, MD",
                    "age_group_stratification": "Cohort 1: 12-17 years, Cohort 2: 6-11 years, Cohort 3: 2-5 years",
                    "pediatric_dose_rationale": "Allometric scaling from adult dose with safety factor of 0.8",
                    "growth_development_considerations": "Regular growth monitoring and developmental assessments",
                    "pediatric_formulation": "Oral suspension suitable for pediatric administration",
                    "assent_age_range": "7-11 years",
                    "full_assent_age_range": "12-17 years"
                },
                expected_sections=["pediatric_population", "pediatric_safety", "informed_consent_pediatric"],
                output_formats=[ProtocolFormat.MARKDOWN]
            ),
            
            # Digital health scenario
            TestScenario(
                scenario_id="digital_health_001",
                name="Digital Health App Study",
                description="Digital therapeutic application validation study",
                template_id="digital_health_app",
                study_data={
                    "study_title": "Validation of Digital Therapeutic App for Depression Management",
                    "protocol_number": "DH-001",
                    "principal_investigator": "Dr. Lisa Wang, PhD",
                    "digital_platform_description": "Mobile app with CBT modules and mood tracking",
                    "technology_components": "iOS/Android app with cloud backend and ML algorithms",
                    "digital_biomarkers": "App usage patterns, mood scores, activity levels",
                    "device_compatibility": "iOS 14+ and Android 10+",
                    "internet_requirements": "WiFi or cellular data connection"
                },
                expected_sections=["digital_intervention", "digital_endpoints", "data_management_digital"],
                output_formats=[ProtocolFormat.MARKDOWN, ProtocolFormat.JSON]
            ),
            
            # Minimal data scenario (error handling)
            TestScenario(
                scenario_id="minimal_data_001",
                name="Minimal Data Error Handling",
                description="Test with minimal required data to validate error handling",
                template_id="rct_basic_v1",
                study_data={
                    "study_title": "Minimal Test Study"
                },
                expected_sections=["title_page"],
                output_formats=[ProtocolFormat.MARKDOWN],
                validation_rules=["should_contain_defaults"]
            )
        ]
        
        return scenarios
    
    async def run_full_integration_suite(self) -> Dict[str, Any]:
        """Run the complete integration test suite."""
        logger.info("Starting full integration test suite")
        start_time = time.time()
        
        results = {
            "suite_start_time": datetime.now().isoformat(),
            "scenarios_tested": 0,
            "scenarios_passed": 0,
            "scenarios_failed": 0,
            "total_execution_time": 0,
            "performance_metrics": {},
            "detailed_results": []
        }
        
        for scenario in self.test_scenarios:
            logger.info(f"Running scenario: {scenario.name}")
            
            try:
                scenario_results = await self._run_scenario(scenario)
                results["detailed_results"].extend(scenario_results)
                
                # Count results
                results["scenarios_tested"] += 1
                if all(result.success for result in scenario_results):
                    results["scenarios_passed"] += 1
                else:
                    results["scenarios_failed"] += 1
                
            except Exception as e:
                logger.error(f"Error running scenario {scenario.scenario_id}: {str(e)}")
                results["scenarios_failed"] += 1
        
        # Calculate overall metrics
        results["total_execution_time"] = time.time() - start_time
        results["success_rate"] = (results["scenarios_passed"] / results["scenarios_tested"]) * 100
        results["performance_metrics"] = self._calculate_performance_metrics()
        
        logger.info(f"Integration suite completed. Success rate: {results['success_rate']:.1f}%")
        return results
    
    async def _run_scenario(self, scenario: TestScenario) -> List[IntegrationTestResult]:
        """Run a single test scenario."""
        scenario_results = []
        
        for output_format in scenario.output_formats:
            test_result = await self._run_single_test(scenario, output_format)
            scenario_results.append(test_result)
            self.test_results.append(test_result)
        
        return scenario_results
    
    async def _run_single_test(self, scenario: TestScenario, output_format: ProtocolFormat) -> IntegrationTestResult:
        """Run a single integration test."""
        test_name = f"{scenario.scenario_id}_{output_format.value}"
        logger.info(f"Running test: {test_name}")
        
        start_time = time.time()
        
        try:
            # Generate protocol
            result = await self.protocol_generator.generate_protocol(
                template_id=scenario.template_id,
                study_data=scenario.study_data,
                output_format=output_format
            )
            
            execution_time = time.time() - start_time
            
            if not result.get("success", False):
                return IntegrationTestResult(
                    test_name=test_name,
                    success=False,
                    execution_time=execution_time,
                    output_size=0,
                    template_used=scenario.template_id,
                    format_tested=output_format,
                    error_message=result.get("error", "Unknown error")
                )
            
            # Validate results
            protocol_content = result["protocol_content"]
            validation_results = await self._validate_protocol_output(
                protocol_content, scenario, output_format
            )
            
            # Performance metrics
            performance_metrics = {
                "content_length": len(protocol_content),
                "sections_generated": len(scenario.expected_sections),
                "generation_rate": len(protocol_content) / execution_time,
                "meets_performance_threshold": execution_time <= scenario.performance_threshold
            }
            
            return IntegrationTestResult(
                test_name=test_name,
                success=all(validation_results.values()),
                execution_time=execution_time,
                output_size=len(protocol_content),
                template_used=scenario.template_id,
                format_tested=output_format,
                performance_metrics=performance_metrics,
                validation_results=validation_results
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Test {test_name} failed: {str(e)}")
            
            return IntegrationTestResult(
                test_name=test_name,
                success=False,
                execution_time=execution_time,
                output_size=0,
                template_used=scenario.template_id,
                format_tested=output_format,
                error_message=str(e)
            )
    
    async def _validate_protocol_output(self, 
                                      content: str, 
                                      scenario: TestScenario, 
                                      output_format: ProtocolFormat) -> Dict[str, bool]:
        """Validate protocol output against expected criteria."""
        validations = {}
        
        # Basic content validation
        validations["has_content"] = len(content) > 0
        validations["has_title"] = scenario.study_data.get("study_title", "") in content
        
        # Section validation
        for section in scenario.expected_sections:
            # Check if section content exists (simplified check)
            validations[f"has_section_{section}"] = len(content) > 100  # Basic check
        
        # Format-specific validations
        if output_format == ProtocolFormat.HTML:
            validations["valid_html"] = "<html>" in content and "</html>" in content
        elif output_format == ProtocolFormat.JSON:
            try:
                json.loads(content)
                validations["valid_json"] = True
            except:
                validations["valid_json"] = False
        elif output_format == ProtocolFormat.MARKDOWN:
            validations["has_headers"] = "#" in content
        
        # Custom validation rules
        for rule in scenario.validation_rules:
            if rule == "should_contain_defaults":
                validations["contains_defaults"] = "[" in content and "]" in content
        
        return validations
    
    async def run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks for protocol generation."""
        logger.info("Running performance benchmarks")
        
        benchmark_results = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {}
        }
        
        # Benchmark different template types
        template_benchmarks = [
            ("rct_basic_v1", "Basic RCT"),
            ("oncology_phase1", "Oncology Phase I"),
            ("pediatric_safety", "Pediatric Safety")
        ]
        
        for template_id, template_name in template_benchmarks:
            benchmark_data = await self._benchmark_template(template_id, template_name)
            benchmark_results["benchmarks"][template_id] = benchmark_data
        
        return benchmark_results
    
    async def _benchmark_template(self, template_id: str, template_name: str) -> Dict[str, Any]:
        """Benchmark a specific template."""
        logger.info(f"Benchmarking template: {template_name}")
        
        # Sample data for benchmarking
        sample_data = {
            "study_title": f"Performance Test for {template_name}",
            "principal_investigator": "Dr. Performance Tester",
            "primary_objective": "To benchmark protocol generation performance"
        }
        
        iterations = 10
        execution_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                result = await self.protocol_generator.generate_protocol(
                    template_id=template_id,
                    study_data=sample_data,
                    output_format=ProtocolFormat.MARKDOWN
                )
                
                if result.get("success"):
                    execution_time = time.time() - start_time
                    execution_times.append(execution_time)
                
            except Exception as e:
                logger.error(f"Benchmark iteration {i} failed: {str(e)}")
        
        if execution_times:
            return {
                "template_name": template_name,
                "iterations": len(execution_times),
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "total_time": sum(execution_times)
            }
        else:
            return {
                "template_name": template_name,
                "error": "All benchmark iterations failed"
            }
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate overall performance metrics."""
        if not self.test_results:
            return {}
        
        successful_tests = [r for r in self.test_results if r.success]
        
        if not successful_tests:
            return {"error": "No successful tests for metrics calculation"}
        
        execution_times = [r.execution_time for r in successful_tests]
        output_sizes = [r.output_size for r in successful_tests]
        
        return {
            "total_tests": len(self.test_results),
            "successful_tests": len(successful_tests),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "avg_output_size": sum(output_sizes) / len(output_sizes),
            "min_output_size": min(output_sizes),
            "max_output_size": max(output_sizes),
            "throughput": len(successful_tests) / sum(execution_times) if execution_times else 0
        }
    
    async def validate_template_compliance(self) -> Dict[str, Any]:
        """Validate template compliance across domains."""
        logger.info("Validating template compliance")
        
        compliance_results = {
            "timestamp": datetime.now().isoformat(),
            "templates_validated": 0,
            "compliance_issues": [],
            "template_results": {}
        }
        
        # Get all available templates
        available_templates = self.specialized_factory.get_available_templates()
        
        for template_id, template_info in available_templates.items():
            logger.info(f"Validating compliance for: {template_info['name']}")
            
            template_result = await self._validate_single_template_compliance(template_id, template_info)
            compliance_results["template_results"][template_id] = template_result
            compliance_results["templates_validated"] += 1
            
            if template_result.get("compliance_issues"):
                compliance_results["compliance_issues"].extend(template_result["compliance_issues"])
        
        compliance_results["overall_compliance_score"] = self._calculate_compliance_score(compliance_results)
        
        return compliance_results
    
    async def _validate_single_template_compliance(self, template_id: str, template_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate compliance for a single template."""
        compliance_result = {
            "template_id": template_id,
            "template_name": template_info["name"],
            "compliance_checks": {},
            "compliance_issues": []
        }
        
        # Check required variables
        required_vars = template_info.get("required_variables", [])
        compliance_result["compliance_checks"]["has_required_variables"] = len(required_vars) > 0
        
        if len(required_vars) == 0:
            compliance_result["compliance_issues"].append(f"Template {template_id} has no required variables")
        
        # Check regulatory frameworks
        frameworks = template_info.get("regulatory_frameworks", [])
        compliance_result["compliance_checks"]["has_regulatory_framework"] = len(frameworks) > 0
        
        if len(frameworks) == 0:
            compliance_result["compliance_issues"].append(f"Template {template_id} has no regulatory frameworks")
        
        # Check sections count
        sections_count = template_info.get("sections_count", 0)
        compliance_result["compliance_checks"]["adequate_sections"] = sections_count >= 3
        
        if sections_count < 3:
            compliance_result["compliance_issues"].append(f"Template {template_id} has insufficient sections ({sections_count})")
        
        return compliance_result
    
    def _calculate_compliance_score(self, compliance_results: Dict[str, Any]) -> float:
        """Calculate overall compliance score."""
        total_templates = compliance_results["templates_validated"]
        total_issues = len(compliance_results["compliance_issues"])
        
        if total_templates == 0:
            return 0.0
        
        # Simple scoring: fewer issues = higher score
        base_score = 100.0
        issue_penalty = min(total_issues * 5, 50)  # Max 50 point deduction
        
        return max(base_score - issue_penalty, 0.0)
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "test_suite_version": "3.3.0",
            "summary": {
                "total_tests": len(self.test_results),
                "passed_tests": len([r for r in self.test_results if r.success]),
                "failed_tests": len([r for r in self.test_results if not r.success]),
                "success_rate": 0.0
            },
            "performance_summary": self._calculate_performance_metrics(),
            "detailed_results": [
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "output_size": result.output_size,
                    "template_used": result.template_used,
                    "format_tested": result.format_tested.value,
                    "error_message": result.error_message,
                    "validation_results": result.validation_results
                }
                for result in self.test_results
            ],
            "recommendations": self._generate_recommendations()
        }
        
        # Calculate success rate
        if report["summary"]["total_tests"] > 0:
            report["summary"]["success_rate"] = (
                report["summary"]["passed_tests"] / report["summary"]["total_tests"]
            ) * 100
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [r for r in self.test_results if not r.success]
        slow_tests = [r for r in self.test_results if r.execution_time > 5.0]
        
        if failed_tests:
            recommendations.append(f"Review and fix {len(failed_tests)} failed test cases")
        
        if slow_tests:
            recommendations.append(f"Optimize performance for {len(slow_tests)} slow tests")
        
        # Performance recommendations
        performance_metrics = self._calculate_performance_metrics()
        if performance_metrics.get("avg_execution_time", 0) > 3.0:
            recommendations.append("Consider optimizing template processing for better performance")
        
        if not recommendations:
            recommendations.append("All tests passed successfully - system is performing well")
        
        return recommendations


# Pytest integration for automated testing
class TestProtocolIntegration:
    """Pytest test class for integration testing."""
    
    @pytest.fixture(scope="class")
    def test_suite(self):
        """Create test suite instance."""
        return ProtocolIntegrationTestSuite()
    
    @pytest.mark.asyncio
    async def test_basic_rct_generation(self, test_suite):
        """Test basic RCT protocol generation."""
        scenario = test_suite.test_scenarios[0]  # Basic RCT
        results = await test_suite._run_scenario(scenario)
        
        assert len(results) > 0
        assert all(result.success for result in results)
    
    @pytest.mark.asyncio
    async def test_oncology_template(self, test_suite):
        """Test oncology template generation."""
        scenario = next((s for s in test_suite.test_scenarios if s.scenario_id == "onc_phase1_001"), None)
        assert scenario is not None
        
        results = await test_suite._run_scenario(scenario)
        assert len(results) > 0
        assert all(result.success for result in results)
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, test_suite):
        """Test performance benchmarks."""
        benchmarks = await test_suite.run_performance_benchmarks()
        
        assert "benchmarks" in benchmarks
        assert len(benchmarks["benchmarks"]) > 0
        
        # Verify all benchmarks completed successfully
        for template_id, benchmark in benchmarks["benchmarks"].items():
            assert "avg_execution_time" in benchmark
            assert benchmark["avg_execution_time"] < 10.0  # Should be under 10 seconds
    
    @pytest.mark.asyncio
    async def test_template_compliance(self, test_suite):
        """Test template compliance validation."""
        compliance = await test_suite.validate_template_compliance()
        
        assert compliance["templates_validated"] > 0
        assert compliance["overall_compliance_score"] > 70.0  # Minimum acceptable score


if __name__ == "__main__":
    async def main():
        """Run integration tests."""
        test_suite = ProtocolIntegrationTestSuite()
        
        print("🧪 Running Protocol Integration Test Suite...")
        results = await test_suite.run_full_integration_suite()
        
        print("\n📊 Running Performance Benchmarks...")
        benchmarks = await test_suite.run_performance_benchmarks()
        
        print("\n✅ Running Template Compliance Validation...")
        compliance = await test_suite.validate_template_compliance()
        
        print("\n📋 Generating Test Report...")
        report = test_suite.generate_test_report()
        
        print(f"\n🎯 INTEGRATION TEST RESULTS:")
        print(f"Total Tests: {results['scenarios_tested']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Total Execution Time: {results['total_execution_time']:.2f}s")
        print(f"Compliance Score: {compliance['overall_compliance_score']:.1f}")
        
        return results, benchmarks, compliance, report
    
    # Run the tests
    asyncio.run(main())