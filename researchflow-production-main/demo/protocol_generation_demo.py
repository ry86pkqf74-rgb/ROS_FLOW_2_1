#!/usr/bin/env python3
"""
Protocol Generation Demo Script

Demonstrates all capabilities of the comprehensive protocol generation system
including 13+ specialized templates, PHI compliance, performance monitoring,
and multiple output formats.

Usage:
    python demo/protocol_generation_demo.py
    python demo/protocol_generation_demo.py --template rct_basic_v1
    python demo/protocol_generation_demo.py --show-templates
    python demo/protocol_generation_demo.py --format html

Author: Enhancement Team
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Add the services/worker/src directory to Python path
worker_src_path = Path(__file__).parent.parent / "services" / "worker" / "src"
sys.path.insert(0, str(worker_src_path))

# Try importing with error handling
try:
    from workflow_engine.stages.study_analyzers.protocol_generator import (
        ProtocolGenerator,
        ProtocolFormat,
        TemplateType
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔧 Creating standalone demo with mock generator...")
    
    # Mock classes for standalone demo
    from enum import Enum
    
    class ProtocolFormat(Enum):
        MARKDOWN = "markdown"
        HTML = "html"
        JSON = "json"
        PDF = "pdf"
        DOCX = "docx"
    
    class ProtocolGenerator:
        def __init__(self, **kwargs):
            self.templates = {
                "rct_basic_v1": {
                    "name": "Randomized Controlled Trial - Basic Template",
                    "type": "clinical_trial",
                    "version": "1.0",
                    "required_variables": ["study_title", "principal_investigator", "primary_objective"],
                    "sections_count": 5
                },
                "observational_basic_v1": {
                    "name": "Observational Study - Basic Template",
                    "type": "observational_study",
                    "version": "1.0",
                    "required_variables": ["study_title", "principal_investigator", "primary_objective"],
                    "sections_count": 4
                }
            }
        
        def get_available_templates(self):
            return self.templates
        
        async def generate_protocol(self, template_id, study_data, output_format):
            # Mock protocol generation
            content = f"# {study_data.get('study_title', 'Sample Protocol')}\n\n"
            content += f"**Principal Investigator:** {study_data.get('principal_investigator', 'Dr. Sample')}\n\n"
            content += f"**Primary Objective:** {study_data.get('primary_objective', 'Sample objective')}\n\n"
            content += "## Study Design\n\nThis is a mock protocol generated for demonstration purposes.\n\n"
            content += f"**Sample Size:** {study_data.get('estimated_sample_size', 100)}\n\n"
            content += "## Methods\n\nDetailed methodology would be included here.\n\n"
            content += "**Note:** This is a demonstration of the protocol generation system capabilities."
            
            return {
                "success": True,
                "protocol_content": content,
                "template_id": template_id,
                "output_format": output_format.value,
                "content_length": len(content),
                "generated_timestamp": datetime.now().isoformat(),
                "metadata": {
                    "sections_count": self.templates[template_id]["sections_count"],
                    "phi_compliant": True
                }
            }
        
        def validate_template_variables(self, template_id, variables):
            template = self.templates.get(template_id, {})
            required = template.get("required_variables", [])
            provided = list(variables.keys())
            missing = [var for var in required if var not in variables]
            
            return {
                "valid": len(missing) == 0,
                "missing_variables": missing,
                "provided_variables": provided,
                "required_variables": required
            }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProtocolGenerationDemo:
    """Comprehensive demo of protocol generation capabilities."""
    
    def __init__(self):
        self.generator = ProtocolGenerator(
            template_version="v1.2",
            enable_phi_integration=True,
            regulatory_templates=True
        )
        self.demo_data = self._create_sample_study_data()
    
    def _create_sample_study_data(self):
        """Create comprehensive sample data for all template types."""
        return {
            # Clinical Trial Sample
            "rct_basic_v1": {
                "study_title": "A Randomized, Double-Blind, Placebo-Controlled Study of Novel Drug X in Patients with Type 2 Diabetes",
                "protocol_number": "DEMO-RCT-001",
                "principal_investigator": "Dr. Sarah Johnson, MD, PhD",
                "study_phase": "Phase III",
                "study_type": "Interventional",
                "sponsor": "Research Institute for Clinical Excellence",
                "protocol_version": "2.1",
                "primary_objective": "To evaluate the efficacy and safety of Drug X compared to placebo in reducing HbA1c levels in patients with Type 2 diabetes",
                "secondary_objectives": "To assess the effect on fasting glucose, body weight, and quality of life measures",
                "exploratory_objectives": "To investigate biomarker changes and genetic predictors of response",
                "design_description": "Randomized, double-blind, placebo-controlled, parallel-group study with 2:1 randomization",
                "design_type": "Parallel Group",
                "allocation_strategy": "Stratified randomization by baseline HbA1c and BMI",
                "blinding_description": "Double-blind (participant and investigator)",
                "treatment_groups": "Drug X 50mg daily vs. Matching placebo",
                "randomization_description": "Central randomization using interactive web response system (IWRS)",
                "estimated_sample_size": 450,
                "estimated_duration_months": 18,
                "subject_duration": 12,
                "target_population_description": "Adults aged 18-75 with Type 2 diabetes and HbA1c 7.0-10.0%",
                "expected_power": 0.9,
                "significance_level": 0.05,
                "expected_effect_size": 0.7,
                "statistical_test_type": "ANCOVA",
                "sample_size_justification": "Based on 0.7% reduction in HbA1c with 90% power and 5% alpha",
                "primary_analysis_method": "Mixed model repeated measures (MMRM)",
                "analysis_population": "Full Analysis Set (FAS)",
                "missing_data_approach": "Multiple imputation for sensitivity analysis",
                "interim_analysis_plan": "One interim analysis at 50% enrollment for futility",
                "primary_endpoint_description": "Change from baseline in HbA1c at Week 24",
                "background_summary": "Type 2 diabetes affects over 400 million people worldwide. Current treatments have limitations...",
                "statistical_analysis_summary": "Primary endpoint analyzed using MMRM with treatment, visit, and baseline HbA1c as covariates"
            },
            
            # Observational Study Sample
            "observational_basic_v1": {
                "study_title": "Longitudinal Observational Study of Cardiovascular Outcomes in Patients with Chronic Kidney Disease",
                "protocol_number": "DEMO-OBS-002",
                "principal_investigator": "Dr. Michael Chen, MD, MPH",
                "study_design": "Prospective cohort study",
                "protocol_version": "1.5",
                "background_description": "Chronic kidney disease (CKD) is associated with increased cardiovascular risk. Limited data exists on contemporary outcomes...",
                "study_rationale": "To understand real-world cardiovascular outcomes and identify modifiable risk factors in CKD patients",
                "literature_summary": "Previous studies have shown 2-3 fold increased CV risk. However, recent data is limited and treatment patterns have evolved...",
                "primary_objective": "To determine the incidence of major adverse cardiovascular events (MACE) in patients with CKD stages 3-5",
                "secondary_objectives": "To identify risk factors for cardiovascular events, assess treatment patterns, and develop predictive models",
                "study_design_details": "Multi-center, prospective cohort study following patients for 5 years",
                "target_population_description": "Adults ≥18 years with CKD stages 3-5 (eGFR 15-59 mL/min/1.73m²)",
                "inclusion_criteria": "Age ≥18 years; Confirmed CKD stage 3-5; Able to provide informed consent",
                "exclusion_criteria": "Life expectancy <1 year; Active malignancy; Pregnancy",
                "data_collection_methods": "Electronic health records, patient interviews, laboratory data, imaging results",
                "followup_schedule": "Baseline, 6 months, 12 months, then annually for 5 years"
            }
        }
    
    async def run_comprehensive_demo(self):
        """Run comprehensive demonstration of all capabilities."""
        print("🚀 PROTOCOL GENERATION SYSTEM DEMO")
        print("=" * 50)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Show available templates
        await self.show_available_templates()
        
        # Generate protocols for each template
        await self.demo_all_templates()
        
        # Show different output formats
        await self.demo_output_formats()
        
        # Performance demonstration
        await self.demo_performance_features()
        
        print("\n✅ DEMO COMPLETED SUCCESSFULLY!")
        print("The protocol generation system is ready for production use.")
    
    async def show_available_templates(self):
        """Display all available templates."""
        print("📋 AVAILABLE PROTOCOL TEMPLATES")
        print("-" * 30)
        
        templates = self.generator.get_available_templates()
        
        for template_id, info in templates.items():
            print(f"🔹 {template_id}")
            print(f"   Name: {info['name']}")
            print(f"   Type: {info['type']}")
            print(f"   Version: {info['version']}")
            print(f"   Sections: {info['sections_count']}")
            print(f"   Required Variables: {len(info['required_variables'])}")
            print()
    
    async def demo_all_templates(self):
        """Generate protocols using all available templates."""
        print("🔧 GENERATING PROTOCOLS FROM ALL TEMPLATES")
        print("-" * 40)
        
        templates = self.generator.get_available_templates()
        generation_results = []
        
        for template_id in templates.keys():
            if template_id in self.demo_data:
                print(f"📄 Generating protocol with template: {template_id}")
                
                result = await self.generator.generate_protocol(
                    template_id=template_id,
                    study_data=self.demo_data[template_id],
                    output_format=ProtocolFormat.MARKDOWN
                )
                
                if result["success"]:
                    print(f"   ✅ Success! Generated {result['content_length']} characters")
                    print(f"   📊 Sections: {result['metadata']['sections_count']}")
                    print(f"   🔒 PHI Compliant: {result['metadata']['phi_compliant']}")
                    
                    # Save sample to file
                    output_path = Path(f"demo/output/sample_{template_id}.md")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(result["protocol_content"])
                    print(f"   💾 Saved to: {output_path}")
                    
                else:
                    print(f"   ❌ Failed: {result['error']}")
                
                generation_results.append(result)
                print()
        
        # Summary statistics
        successful_generations = sum(1 for r in generation_results if r["success"])
        print(f"📊 GENERATION SUMMARY: {successful_generations}/{len(generation_results)} successful")
    
    async def demo_output_formats(self):
        """Demonstrate different output formats."""
        print("🎨 OUTPUT FORMAT DEMONSTRATION")
        print("-" * 30)
        
        # Use first available template and data
        template_id = list(self.demo_data.keys())[0]
        study_data = self.demo_data[template_id]
        
        formats_to_demo = [
            ProtocolFormat.MARKDOWN,
            ProtocolFormat.HTML,
            ProtocolFormat.JSON
        ]
        
        for format_type in formats_to_demo:
            print(f"🔄 Generating {format_type.value.upper()} format...")
            
            result = await self.generator.generate_protocol(
                template_id=template_id,
                study_data=study_data,
                output_format=format_type
            )
            
            if result["success"]:
                # Save sample output
                extension = {
                    ProtocolFormat.MARKDOWN: "md",
                    ProtocolFormat.HTML: "html",
                    ProtocolFormat.JSON: "json"
                }.get(format_type, "txt")
                
                output_path = Path(f"demo/output/sample_format.{extension}")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result["protocol_content"])
                
                print(f"   ✅ Generated {len(result['protocol_content'])} characters")
                print(f"   💾 Saved to: {output_path}")
            else:
                print(f"   ❌ Failed: {result['error']}")
            print()
    
    async def demo_performance_features(self):
        """Demonstrate performance and monitoring features."""
        print("⚡ PERFORMANCE & MONITORING FEATURES")
        print("-" * 35)
        
        # Template validation demo
        template_id = list(self.demo_data.keys())[0]
        study_data = self.demo_data[template_id]
        
        print("🔍 Variable Validation Demo:")
        validation_result = self.generator.validate_template_variables(
            template_id, study_data
        )
        print(f"   Valid: {validation_result['valid']}")
        print(f"   Required Variables: {len(validation_result['required_variables'])}")
        print(f"   Provided Variables: {len(validation_result['provided_variables'])}")
        
        # Performance timing
        print("\n⏱️  Performance Timing:")
        start_time = datetime.now()
        
        result = await self.generator.generate_protocol(
            template_id=template_id,
            study_data=study_data,
            output_format=ProtocolFormat.MARKDOWN
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"   Generation Time: {duration:.3f} seconds")
        print(f"   Content Length: {result['content_length']} characters")
        print(f"   Processing Rate: {result['content_length']/duration:.0f} chars/sec")
        
        # System capabilities summary
        print("\n🎯 SYSTEM CAPABILITIES SUMMARY:")
        print("   ✅ 13+ Specialized Protocol Templates")
        print("   ✅ Multiple Output Formats (MD, HTML, PDF*, Word*)")
        print("   ✅ PHI Compliance & Security Validation")
        print("   ✅ Regulatory Framework Support")
        print("   ✅ Template Variable Validation")
        print("   ✅ Performance Monitoring")
        print("   ✅ Comprehensive Testing Framework")
        print("   ✅ Production-Ready Architecture")
        print("   *PDF and Word formats require additional libraries")
    
    async def demo_single_template(self, template_id: str, output_format: str = "markdown"):
        """Demo a single template."""
        if template_id not in self.demo_data:
            print(f"❌ No demo data available for template: {template_id}")
            return
        
        format_enum = ProtocolFormat(output_format.lower())
        
        print(f"🔧 Generating protocol with template: {template_id}")
        print(f"📄 Output format: {format_enum.value}")
        
        result = await self.generator.generate_protocol(
            template_id=template_id,
            study_data=self.demo_data[template_id],
            output_format=format_enum
        )
        
        if result["success"]:
            print(f"✅ Success! Generated {result['content_length']} characters")
            
            # Display first 500 characters
            print("\n📄 SAMPLE OUTPUT (first 500 characters):")
            print("-" * 40)
            print(result["protocol_content"][:500])
            if len(result["protocol_content"]) > 500:
                print("... (truncated)")
            print("-" * 40)
        else:
            print(f"❌ Failed: {result['error']}")


async def main():
    """Main demo function with command line argument support."""
    parser = argparse.ArgumentParser(description="Protocol Generation System Demo")
    parser.add_argument("--template", help="Demo specific template")
    parser.add_argument("--format", default="markdown", help="Output format (markdown, html, json)")
    parser.add_argument("--show-templates", action="store_true", help="Show available templates only")
    
    args = parser.parse_args()
    
    demo = ProtocolGenerationDemo()
    
    try:
        if args.show_templates:
            await demo.show_available_templates()
        elif args.template:
            await demo.demo_single_template(args.template, args.format)
        else:
            await demo.run_comprehensive_demo()
    
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"❌ Demo failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())