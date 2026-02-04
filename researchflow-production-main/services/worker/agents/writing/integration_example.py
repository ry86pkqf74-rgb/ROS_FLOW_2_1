"""
Integration Example for Results Interpretation Agent

This file demonstrates how to integrate and use the ResultsInterpretationAgent
in the ResearchFlow pipeline. It shows real-world usage patterns and integration
with Stage 7 (Statistical Analysis) and Stage 10+ (Manuscript Writing).
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from . import (
    ResultsInterpretationAgent,
    ResultsInterpretationState,
    InterpretationRequest,
    process_interpretation_request
)


# =============================================================================
# Example Data (Stage 7 Statistical Analysis Output)
# =============================================================================

def get_example_statistical_results() -> Dict[str, Any]:
    """
    Example statistical results from Stage 7 (Statistical Analysis).
    This represents the typical output that would be passed to Stage 9.
    """
    return {
        "study_metadata": {
            "study_id": "RCT_PAIN_2024_001",
            "analysis_date": "2024-01-30T10:30:00Z",
            "analysis_version": "2.1",
            "analyst": "StatisticalAnalysisAgent"
        },
        "primary_outcomes": [
            {
                "outcome_id": "primary_1",
                "hypothesis": "Treatment reduces pain intensity compared to placebo",
                "measure": "Visual Analog Scale (VAS) pain score",
                "comparison": "Treatment vs Placebo",
                "test_type": "t-test",
                "test_statistic": "t = 3.45",
                "degrees_freedom": 148,
                "p_value": 0.0007,
                "effect_size": 0.72,
                "effect_size_type": "Cohen's d",
                "confidence_interval": {
                    "lower": 0.38,
                    "upper": 1.06,
                    "level": 0.95
                },
                "descriptive_statistics": {
                    "treatment_mean": 3.2,
                    "treatment_sd": 1.8,
                    "treatment_n": 75,
                    "control_mean": 5.4,
                    "control_sd": 2.1,
                    "control_n": 75
                },
                "clinical_benchmark": {
                    "mcid": 1.5,  # Minimal clinically important difference
                    "large_effect": 2.0
                }
            },
            {
                "outcome_id": "primary_2", 
                "hypothesis": "Treatment improves functional status compared to placebo",
                "measure": "Oswestry Disability Index (ODI)",
                "comparison": "Treatment vs Placebo",
                "test_type": "Mann-Whitney U",
                "test_statistic": "U = 2156",
                "p_value": 0.032,
                "effect_size": 0.48,
                "effect_size_type": "Cohen's d",
                "confidence_interval": {
                    "lower": 0.12,
                    "upper": 0.84,
                    "level": 0.95
                },
                "descriptive_statistics": {
                    "treatment_median": 24.0,
                    "treatment_iqr": [18.0, 32.0],
                    "treatment_n": 75,
                    "control_median": 31.0,
                    "control_iqr": [26.0, 38.0],
                    "control_n": 75
                }
            }
        ],
        "secondary_outcomes": [
            {
                "outcome_id": "secondary_1",
                "hypothesis": "Treatment reduces medication usage",
                "measure": "Daily morphine equivalent dose (mg)",
                "test_type": "t-test",
                "p_value": 0.089,
                "effect_size": 0.34,
                "confidence_interval": {
                    "lower": -0.05,
                    "upper": 0.73
                }
            },
            {
                "outcome_id": "secondary_2",
                "hypothesis": "Treatment improves sleep quality",
                "measure": "Pittsburgh Sleep Quality Index",
                "test_type": "t-test", 
                "p_value": 0.156,
                "effect_size": 0.22,
                "confidence_interval": {
                    "lower": -0.10,
                    "upper": 0.54
                }
            }
        ],
        "sample_info": {
            "total_n": 150,
            "randomized_n": 160,
            "treatment_n": 75,
            "control_n": 75,
            "attrition_rate": 0.0625,  # 6.25%
            "missing_data_rate": 0.033,  # 3.3%
            "per_protocol_n": 140,
            "intention_to_treat_n": 150
        },
        "statistical_assumptions": {
            "normality": {
                "vas_pain": {"shapiro_wilk_p": 0.087, "passed": True},
                "odi": {"shapiro_wilk_p": 0.023, "passed": False}
            },
            "homoscedasticity": {
                "vas_pain": {"levene_p": 0.234, "passed": True},
                "odi": {"levene_p": 0.445, "passed": True}
            },
            "independence": {"passed": True, "notes": "Randomized design ensures independence"}
        },
        "sensitivity_analyses": [
            {
                "analysis_type": "per_protocol",
                "primary_outcome_1_p": 0.0003,
                "primary_outcome_1_effect": 0.81
            },
            {
                "analysis_type": "complete_case",
                "primary_outcome_1_p": 0.0005,
                "primary_outcome_1_effect": 0.76
            }
        ],
        "multiple_comparisons": {
            "method": "Bonferroni",
            "adjusted_alpha": 0.025,
            "primary_outcomes_significant": 2
        }
    }


def get_example_study_context() -> Dict[str, Any]:
    """
    Example study context from protocol and design information.
    This provides the clinical and methodological context needed for interpretation.
    """
    return {
        "protocol": {
            "study_design": "randomized controlled trial",
            "study_phase": "Phase III",
            "randomization": True,
            "randomization_method": "permuted block",
            "allocation_concealment": "central randomization",
            "blinding": "double-blind",
            "blinding_details": "participants, investigators, and outcomes assessors",
            "follow_up_duration": "12 weeks",
            "primary_endpoint_timing": "12 weeks",
            "secondary_endpoint_timing": "4, 8, 12 weeks"
        },
        "population": {
            "target_population": "adults with chronic lower back pain",
            "age_range": "18-65 years",
            "condition_duration": "≥6 months",
            "baseline_pain_threshold": "VAS ≥4/10"
        },
        "intervention": {
            "treatment_name": "Novel analgesic compound XR-450",
            "treatment_dose": "150mg twice daily",
            "control_name": "Placebo",
            "control_description": "matching placebo capsules",
            "duration": "12 weeks"
        },
        "outcomes": {
            "primary_outcome": "change in pain intensity on VAS scale",
            "primary_endpoint": "12-week change from baseline",
            "key_secondary_outcomes": [
                "functional status (ODI)",
                "medication usage",
                "sleep quality"
            ]
        },
        "statistical_plan": {
            "sample_size": 150,
            "power": 0.80,
            "alpha": 0.05,
            "expected_effect_size": 0.5,
            "primary_analysis": "intention_to_treat",
            "missing_data_method": "multiple_imputation"
        },
        "clinical_context": {
            "therapeutic_area": "pain management",
            "unmet_medical_need": "effective non-opioid pain relief",
            "current_standard_of_care": "NSAIDs, physical therapy",
            "baseline_risk": 0.25,  # Estimated baseline event rate
            "target_improvement": "30% pain reduction"
        },
        "regulatory": {
            "fda_guidance_followed": True,
            "ich_gcp_compliant": True,
            "primary_endpoint_validated": True
        }
    }


# =============================================================================
# Integration Examples
# =============================================================================

async def basic_interpretation_example():
    """
    Basic example of using the ResultsInterpretationAgent.
    This shows the simplest integration pattern.
    """
    print("🔬 Basic Results Interpretation Example")
    print("=" * 50)
    
    # Create interpretation request
    request = InterpretationRequest(
        study_id="RCT_PAIN_2024_001",
        statistical_results=get_example_statistical_results(),
        study_context=get_example_study_context(),
        visualizations=["pain_reduction_chart.png", "functional_improvement_chart.png"]
    )
    
    try:
        # Process interpretation
        response = await process_interpretation_request(request)
        
        if response.success:
            state = response.interpretation_state
            
            print(f"✅ Interpretation completed successfully in {response.processing_time_ms}ms")
            print(f"📊 Primary findings: {len(state.primary_findings)}")
            print(f"🔍 Clinical significance: {len(state.clinical_significance)}")
            print(f"⚠️  Limitations identified: {len(state.limitations_identified)}")
            print(f"🎯 Confidence statements: {len(state.confidence_statements)}")
            
            # Display key findings
            print("\n📋 Key Findings:")
            for i, finding in enumerate(state.primary_findings, 1):
                print(f"\n{i}. {finding.hypothesis}")
                print(f"   Statistical: {finding.statistical_result}")
                print(f"   Clinical: {finding.clinical_interpretation}")
                print(f"   Confidence: {finding.confidence_level.value}")
                print(f"   Significance: {finding.clinical_significance.value}")
            
            return state
            
        else:
            print(f"❌ Interpretation failed: {response.error_message}")
            return None
            
    except Exception as e:
        print(f"💥 Error during interpretation: {str(e)}")
        return None


async def advanced_interpretation_example():
    """
    Advanced example showing custom agent configuration and quality validation.
    This demonstrates more sophisticated integration patterns.
    """
    print("\n🎯 Advanced Results Interpretation Example")
    print("=" * 50)
    
    # Create agent with custom configuration
    agent = ResultsInterpretationAgent(
        primary_model="claude-3-5-sonnet-20241022",
        fallback_model="gpt-4o",
        quality_threshold=0.90,  # Higher quality threshold
        max_timeout_seconds=600,  # Longer timeout for complex cases
        phi_protection=True
    )
    
    # Create interpretation state directly
    state = ResultsInterpretationState(
        study_id="RCT_PAIN_2024_001",
        statistical_results=get_example_statistical_results(),
        study_context=get_example_study_context(),
        visualizations=[
            "primary_outcome_forest_plot.png",
            "effect_size_comparison.png",
            "subgroup_analysis.png"
        ]
    )
    
    try:
        print("🚀 Starting advanced interpretation workflow...")
        
        # Execute interpretation with detailed monitoring
        result_state = await agent.execute_interpretation(state)
        
        # Quality assessment
        completeness_issues = result_state.validate_completeness()
        quality_score = calculate_quality_score(result_state)
        
        print(f"\n📊 Interpretation Results:")
        print(f"   Study ID: {result_state.study_id}")
        print(f"   Primary findings: {len(result_state.primary_findings)}")
        print(f"   Secondary findings: {len(result_state.secondary_findings)}")
        print(f"   Effect interpretations: {len(result_state.effect_interpretations)}")
        print(f"   Limitations: {len(result_state.limitations_identified)}")
        print(f"   Errors: {len(result_state.errors)}")
        print(f"   Warnings: {len(result_state.warnings)}")
        
        print(f"\n🎯 Quality Assessment:")
        print(f"   Quality score: {quality_score:.2f}")
        print(f"   Completeness issues: {len(completeness_issues)}")
        print(f"   Meets threshold: {'✅' if quality_score >= agent.quality_threshold else '❌'}")
        
        # Display clinical significance assessment
        if result_state.clinical_significance:
            print(f"\n🏥 Clinical Significance Assessment:")
            print(f"   {result_state.clinical_significance}")
        
        # Display key limitations
        if result_state.limitations_identified:
            print(f"\n⚠️  Key Limitations:")
            for limitation in result_state.limitations_identified[:3]:
                print(f"   • {limitation}")
        
        return result_state
        
    except Exception as e:
        print(f"💥 Error during advanced interpretation: {str(e)}")
        return None


def calculate_quality_score(state: ResultsInterpretationState) -> float:
    """Calculate a quality score for the interpretation results."""
    score = 0.0
    
    # Completeness scoring
    if state.primary_findings:
        score += 0.3
    if state.clinical_significance:
        score += 0.2
    if state.limitations_identified:
        score += 0.2
    if state.confidence_statements:
        score += 0.15
    if state.effect_interpretations:
        score += 0.15
    
    return score


async def pipeline_integration_example():
    """
    Example showing integration with the complete ResearchFlow pipeline.
    This demonstrates how Stage 9 fits into the broader workflow.
    """
    print("\n🔄 Pipeline Integration Example")
    print("=" * 50)
    
    # Simulate pipeline context
    pipeline_context = {
        "project_id": "PROJ_2024_001",
        "workflow_stage": 9,
        "previous_stages": {
            "stage_1": {"status": "completed", "output": "protocol_analysis_complete"},
            "stage_7": {"status": "completed", "output": "statistical_analysis_complete"},
            "stage_8": {"status": "completed", "output": "data_visualization_complete"}
        },
        "next_stages": {
            "stage_10": {"type": "manuscript_writing", "input_required": "clinical_interpretation"}
        }
    }
    
    print(f"🏗️  Pipeline Context:")
    print(f"   Project: {pipeline_context['project_id']}")
    print(f"   Current stage: {pipeline_context['workflow_stage']}")
    print(f"   Previous stages completed: {len(pipeline_context['previous_stages'])}")
    
    # Execute interpretation as part of pipeline
    try:
        # Create request with pipeline context
        request = InterpretationRequest(
            study_id="RCT_PAIN_2024_001", 
            statistical_results=get_example_statistical_results(),
            study_context=get_example_study_context()
        )
        
        response = await process_interpretation_request(request)
        
        if response.success:
            # Prepare outputs for next pipeline stage
            pipeline_outputs = prepare_pipeline_outputs(response.interpretation_state)
            
            print(f"✅ Stage 9 completed successfully")
            print(f"📤 Outputs prepared for Stage 10:")
            print(f"   Clinical narrative: {len(pipeline_outputs['clinical_narrative'])} chars")
            print(f"   Key findings: {len(pipeline_outputs['key_findings'])} items")
            print(f"   Effect summaries: {len(pipeline_outputs['effect_summaries'])} items")
            print(f"   Limitation summary: {len(pipeline_outputs['limitation_summary'])} chars")
            
            # Save outputs for next stage
            output_file = Path(f"stage_9_outputs_{request.study_id}.json")
            with open(output_file, 'w') as f:
                json.dump(pipeline_outputs, f, indent=2, default=str)
            
            print(f"💾 Outputs saved to: {output_file}")
            
            return pipeline_outputs
            
        else:
            print(f"❌ Stage 9 failed: {response.error_message}")
            return None
            
    except Exception as e:
        print(f"💥 Pipeline integration error: {str(e)}")
        return None


def prepare_pipeline_outputs(state: ResultsInterpretationState) -> Dict[str, Any]:
    """
    Prepare interpretation outputs for consumption by downstream pipeline stages.
    This creates a standardized interface between stages.
    """
    from .results_utils import format_clinical_narrative, generate_apa_summary
    
    # Generate clinical narrative
    clinical_narrative = format_clinical_narrative(
        primary_findings=state.primary_findings,
        secondary_findings=state.secondary_findings,
        clinical_significance=state.clinical_significance,
        effect_interpretations=state.effect_interpretations,
        limitations=state.limitations_identified,
        confidence_statements=state.confidence_statements
    )
    
    # Generate APA summary
    apa_summary = generate_apa_summary(
        primary_findings=state.primary_findings,
        study_context=state.study_context
    )
    
    # Extract key findings for manuscript writing
    key_findings = []
    for finding in state.primary_findings:
        key_findings.append({
            "hypothesis": finding.hypothesis,
            "result": finding.statistical_result,
            "interpretation": finding.clinical_interpretation,
            "confidence": finding.confidence_level.value,
            "significance": finding.clinical_significance.value,
            "effect_size": finding.effect_size
        })
    
    # Create effect size summaries
    effect_summaries = []
    for hypothesis, interpretation in state.effect_interpretations.items():
        if hypothesis != "clinical_narrative":  # Exclude the narrative
            effect_summaries.append({
                "outcome": hypothesis,
                "interpretation": interpretation
            })
    
    # Prepare limitation summary
    limitation_summary = "; ".join(state.limitations_identified) if state.limitations_identified else ""
    
    return {
        "stage_info": {
            "stage_number": 9,
            "stage_name": "Results Interpretation",
            "study_id": state.study_id,
            "timestamp": state.created_at.isoformat(),
            "version": state.interpretation_version
        },
        "clinical_narrative": clinical_narrative,
        "apa_summary": apa_summary,
        "key_findings": key_findings,
        "effect_summaries": effect_summaries,
        "clinical_significance": state.clinical_significance,
        "limitation_summary": limitation_summary,
        "confidence_statements": state.confidence_statements,
        "quality_metrics": {
            "num_primary_findings": len(state.primary_findings),
            "num_secondary_findings": len(state.secondary_findings),
            "num_limitations": len(state.limitations_identified),
            "num_errors": len(state.errors),
            "num_warnings": len(state.warnings)
        },
        "outputs_for_stage_10": {
            "clinical_interpretation_section": clinical_narrative,
            "results_summary": apa_summary,
            "key_findings_list": key_findings,
            "study_limitations": limitation_summary,
            "clinical_relevance": state.clinical_significance
        }
    }


# =============================================================================
# Main Execution
# =============================================================================

async def main():
    """
    Main execution function demonstrating all integration patterns.
    """
    print("🔬 ResearchFlow Stage 9: Results Interpretation Agent")
    print("📋 Integration Examples and Usage Patterns")
    print("=" * 60)
    
    # Run examples in sequence
    basic_result = await basic_interpretation_example()
    
    if basic_result:
        advanced_result = await advanced_interpretation_example()
        
        if advanced_result:
            pipeline_result = await pipeline_integration_example()
            
            if pipeline_result:
                print("\n🎉 All integration examples completed successfully!")
                print("\n📈 Summary:")
                print(f"   ✅ Basic interpretation: Complete")
                print(f"   ✅ Advanced interpretation: Complete") 
                print(f"   ✅ Pipeline integration: Complete")
                print(f"\n🚀 Ready for production deployment!")
            else:
                print("\n❌ Pipeline integration example failed")
        else:
            print("\n❌ Advanced interpretation example failed")
    else:
        print("\n❌ Basic interpretation example failed")


if __name__ == "__main__":
    # Run the integration examples
    asyncio.run(main())