"""
Stage 10 Dual-Mode Example

This example demonstrates how to use both validation mode and gap analysis mode
in realistic research workflows.

Usage:
    python stage10_dual_mode_example.py --mode validation
    python stage10_dual_mode_example.py --mode gap_analysis
    python stage10_dual_mode_example.py --mode both
"""

import asyncio
import json
import os
from typing import Dict, Any, Literal
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "worker" / "src"))

from workflow_engine.orchestrator import execute_workflow


# =============================================================================
# Example Data
# =============================================================================

SAMPLE_STUDY_CONTEXT = {
    "title": "Impact of Mindfulness-Based Stress Reduction on Anxiety in College Students",
    "research_question": (
        "Does an 8-week Mindfulness-Based Stress Reduction (MBSR) program "
        "reduce anxiety symptoms in college students with moderate anxiety?"
    ),
    "study_type": "Randomized Controlled Trial",
    "population": "College students aged 18-25 with moderate anxiety (GAD-7 > 10)",
    "intervention": "8-week MBSR program, 2 hours per week, with daily home practice",
    "comparison": "Wait-list control group receiving usual care",
    "outcome": "Change in GAD-7 anxiety score from baseline to 8 weeks",
    "setting": "Large public university in northeastern United States",
    "timeframe": "September 2023 - May 2024"
}

VALIDATION_CRITERIA = [
    {
        "id": "data_completeness",
        "name": "Data Completeness",
        "description": "Verify all required data fields are present and complete",
        "category": "data_quality",
        "severity": "high"
    },
    {
        "id": "statistical_validity",
        "name": "Statistical Validity",
        "description": "Verify statistical methods are appropriate for research question",
        "category": "methodology",
        "severity": "high"
    },
    {
        "id": "sample_size_adequacy",
        "name": "Sample Size Adequacy",
        "description": "Verify sample size meets minimum requirements for power",
        "category": "methodology",
        "severity": "medium"
    },
    {
        "id": "consort_compliance",
        "name": "CONSORT Compliance",
        "description": "Verify study design follows CONSORT guidelines",
        "category": "reporting",
        "severity": "high"
    },
    {
        "id": "reproducibility",
        "name": "Reproducibility Check",
        "description": "Verify results can be reproduced with provided methodology",
        "category": "reproducibility",
        "severity": "high"
    }
]


# =============================================================================
# Example 1: Validation Mode Only
# =============================================================================

async def example_validation_mode():
    """
    Example: Use validation mode for CONSORT compliance checking.
    
    Use Case:
    - Quick validation before data analysis
    - CONSORT/STROBE compliance checking
    - Quality gate before proceeding to next stage
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Validation Mode Only")
    print("="*80 + "\n")
    
    config = {
        "stage_10_mode": "validation",
        "validation": {
            "criteria": VALIDATION_CRITERIA,
            "strict_mode": True,  # Fail on high severity issues
            "fail_on_warning": False,
            "checklist_type": "CONSORT"
        }
    }
    
    print("Configuration:")
    print(json.dumps(config, indent=2))
    print("\nExecuting Stage 10 in validation mode...")
    
    result = await execute_workflow(
        job_id="validation-example-001",
        config=config,
        artifact_path="/tmp/stage10_validation",
        stage_ids=[10],
        governance_mode="DEMO"
    )
    
    # Process results
    stage_10_result = result["results"][10]
    
    print(f"\nStatus: {stage_10_result['status']}")
    print(f"Duration: {stage_10_result['duration_ms']}ms")
    
    if stage_10_result["status"] == "completed":
        output = stage_10_result["output"]
        summary = output["summary"]
        
        print(f"\n✅ Validation Complete!")
        print(f"   - Total Criteria: {summary['total_criteria']}")
        print(f"   - Passed: {summary['passed']}")
        print(f"   - Failed: {summary['failed']}")
        print(f"   - Warnings: {summary['warnings']}")
        print(f"   - Pass Rate: {output['checklist_status']['pass_rate']}%")
        
        # Show checklist status
        print("\n📋 Checklist Status:")
        for item in output["checklist_status"]["items"]:
            status_icon = "✅" if item["passed"] else "❌" if item["checked"] else "⏳"
            print(f"   {status_icon} {item['name']}: {item['status']}")
        
        # Show issues if any
        issues = output["issues_found"]
        if issues["critical"] or issues["high"]:
            print("\n⚠️  Issues Found:")
            for issue in issues["critical"]:
                print(f"   🔴 CRITICAL: {issue['criterion_name']}")
            for issue in issues["high"]:
                print(f"   🟠 HIGH: {issue['criterion_name']}")
    
    else:
        print(f"\n❌ Validation Failed!")
        for error in stage_10_result["errors"]:
            print(f"   - {error}")
    
    return result


# =============================================================================
# Example 2: Gap Analysis Mode
# =============================================================================

async def example_gap_analysis_mode():
    """
    Example: Use gap analysis mode for comprehensive literature review.
    
    Use Case:
    - Manuscript Discussion section
    - Future Directions section
    - Grant proposal preparation
    - Research planning
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Gap Analysis Mode")
    print("="*80 + "\n")
    
    # Check API keys
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Gap analysis will fail.")
        print("   Set it with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return None
    
    config = {
        "stage_10_mode": "gap_analysis",
        "study_context": SAMPLE_STUDY_CONTEXT,
        "gap_analysis": {
            "enable_semantic_comparison": True,
            "gap_types": ["empirical", "methodological", "population", "temporal", "geographic"],
            "min_literature_count": 10,
            "max_literature_papers": 40,
            "prioritization_method": "impact_feasibility_matrix",
            "generate_pico": True,
            "target_suggestions": 5,
            "quality_threshold": 0.80,
            "cache_embeddings": True,
            "max_iterations": 3,
            "timeout_seconds": 300
        },
        
        # Literature search config (Stage 6)
        "literature": {
            "query": "mindfulness based stress reduction anxiety college students",
            "databases": ["pubmed", "semantic_scholar"],
            "max_results": 40,
            "years": [2018, 2024]
        },
        
        # Statistical analysis config (Stage 7) - optional
        "statistical_analysis": {
            "outcome_variable": "gad7_change",
            "treatment_variable": "mbsr_group",
            "covariates": ["baseline_gad7", "age", "gender", "prior_meditation"]
        }
    }
    
    print("Configuration:")
    print(json.dumps({
        "mode": config["stage_10_mode"],
        "study": config["study_context"]["title"],
        "gap_analysis": config["gap_analysis"]
    }, indent=2))
    
    print("\nExecuting full pipeline (Stages 6, 7, 10)...")
    print("This may take 30-120 seconds...\n")
    
    result = await execute_workflow(
        job_id="gap-analysis-example-001",
        config=config,
        artifact_path="/tmp/stage10_gap_analysis",
        stage_ids=[6, 7, 10],  # Literature, Stats, Gap Analysis
        stop_on_failure=True,
        governance_mode="DEMO"
    )
    
    # Process results
    if 10 not in result["results"]:
        print("❌ Stage 10 did not execute")
        return result
    
    stage_10_result = result["results"][10]
    
    print(f"\nStatus: {stage_10_result['status']}")
    print(f"Duration: {stage_10_result['duration_ms']}ms")
    
    if stage_10_result["status"] == "completed":
        output = stage_10_result["output"]
        summary = output["summary"]
        
        print(f"\n✅ Gap Analysis Complete!")
        print(f"   - Total Gaps: {summary['total_gaps_identified']}")
        print(f"   - High Priority: {summary['high_priority_count']}")
        print(f"   - Gap Diversity: {summary['gap_diversity_score']:.2f}")
        print(f"   - Literature Coverage: {summary['literature_coverage']:.2f}")
        
        # Show prioritization matrix
        matrix = output["prioritization_matrix"]
        print(f"\n📊 Prioritization Matrix:")
        print(f"   - High Priority (High Impact + High Feasibility): {len(matrix.get('high_priority', []))}")
        print(f"   - Strategic (High Impact + Low Feasibility): {len(matrix.get('strategic', []))}")
        print(f"   - Quick Wins (Low Impact + High Feasibility): {len(matrix.get('quick_wins', []))}")
        print(f"   - Low Priority: {len(matrix.get('low_priority', []))}")
        
        # Show top research suggestions
        suggestions = output["research_suggestions"]
        if suggestions:
            print(f"\n🔬 Top Research Suggestions:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"\n   {i}. {suggestion['research_question']}")
                print(f"      Study Design: {suggestion['study_design']}")
                print(f"      Priority Score: {suggestion.get('impact_score', 0):.1f}/5")
                if suggestion.get('pico_framework'):
                    pico = suggestion['pico_framework']
                    print(f"      PICO: {pico.get('population', 'N/A')[:50]}...")
        
        # Show narrative excerpt
        narrative = output.get("narrative", "")
        if narrative:
            print(f"\n📝 Narrative Excerpt (first 200 chars):")
            print(f"   {narrative[:200]}...")
        
        # Show high priority gaps
        prioritized = output.get("prioritized_gaps", [])
        high_priority = [g for g in prioritized if g.get("priority_level") == "high"]
        if high_priority:
            print(f"\n⚠️  High Priority Gaps:")
            for gap in high_priority[:3]:
                gap_data = gap.get("gap", {})
                print(f"   • {gap_data.get('description', 'N/A')[:80]}...")
                print(f"     Impact: {gap_data.get('impact_score', 0):.1f}/5, "
                      f"Feasibility: {gap_data.get('feasibility_score', 0):.1f}/5")
    
    else:
        print(f"\n❌ Gap Analysis Failed!")
        for error in stage_10_result["errors"]:
            print(f"   - {error}")
        for warning in stage_10_result.get("warnings", []):
            print(f"   ⚠️  {warning}")
    
    return result


# =============================================================================
# Example 3: Both Modes (Validation → Gap Analysis)
# =============================================================================

async def example_both_modes():
    """
    Example: Run validation first, then gap analysis if validation passes.
    
    Use Case:
    - Quality gate before expensive gap analysis
    - Comprehensive research workflow
    - Manuscript generation pipeline
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Both Modes (Validation → Gap Analysis)")
    print("="*80 + "\n")
    
    # Step 1: Validation
    print("STEP 1: Running Validation...")
    print("-" * 80)
    
    validation_result = await example_validation_mode()
    
    if validation_result["results"][10]["status"] != "completed":
        print("\n❌ Validation failed. Skipping gap analysis.")
        return validation_result
    
    validation_summary = validation_result["results"][10]["output"]["summary"]
    if not validation_summary["validation_passed"]:
        print("\n⚠️  Validation did not pass quality gates. Skipping gap analysis.")
        return validation_result
    
    # Step 2: Gap Analysis
    print("\n" + "="*80)
    print("STEP 2: Running Gap Analysis...")
    print("-" * 80)
    
    gap_result = await example_gap_analysis_mode()
    
    # Combine results
    return {
        "validation": validation_result,
        "gap_analysis": gap_result
    }


# =============================================================================
# Example 4: Full Manuscript Pipeline
# =============================================================================

async def example_full_pipeline():
    """
    Example: Complete pipeline from data to manuscript with gap analysis.
    
    Use Case:
    - Complete research workflow
    - Automated manuscript generation
    - Publication-ready output
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Full Manuscript Pipeline")
    print("="*80 + "\n")
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Pipeline will fail.")
        return None
    
    config = {
        # Stage 6: Literature
        "literature": {
            "query": "mindfulness anxiety college",
            "databases": ["pubmed"],
            "max_results": 30
        },
        
        # Stage 7: Statistical Analysis
        "statistical_analysis": {
            "outcome_variable": "anxiety_score",
            "treatment_variable": "mbsr_group"
        },
        
        # Stage 10: Gap Analysis
        "stage_10_mode": "gap_analysis",
        "study_context": SAMPLE_STUDY_CONTEXT,
        "gap_analysis": {
            "enable_semantic_comparison": True,
            "target_suggestions": 5
        },
        
        # Stage 12: Manuscript
        "manuscript": {
            "style": "apa7",
            "include_future_directions": True,  # Use gap analysis output
            "journal_template": "general"
        }
    }
    
    print("Executing full pipeline (Stages 1, 2, 6, 7, 10, 12)...")
    print("This may take several minutes...\n")
    
    result = await execute_workflow(
        job_id="full-pipeline-001",
        config=config,
        artifact_path="/tmp/stage10_full_pipeline",
        stage_ids=[1, 2, 6, 7, 10, 12],
        stop_on_failure=True,
        governance_mode="DEMO"
    )
    
    # Show results
    print("\n" + "="*80)
    print("Pipeline Results")
    print("="*80 + "\n")
    
    for stage_id in [6, 7, 10, 12]:
        if stage_id in result["results"]:
            stage_result = result["results"][stage_id]
            print(f"Stage {stage_id}: {stage_result['stage_name']} - {stage_result['status']}")
    
    # Show manuscript with gap analysis
    if 12 in result["results"] and result["results"][12]["status"] == "completed":
        manuscript = result["results"][12]["output"]
        print("\n📄 Manuscript Generated!")
        
        if "future_directions" in manuscript:
            print("\n🔮 Future Directions Section:")
            print(manuscript["future_directions"][:300] + "...")
    
    return result


# =============================================================================
# Main
# =============================================================================

async def main():
    """Run examples based on command line argument."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stage 10 Dual-Mode Examples")
    parser.add_argument(
        "--mode",
        choices=["validation", "gap_analysis", "both", "full_pipeline"],
        default="validation",
        help="Which example to run"
    )
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("Stage 10 Dual-Mode Examples")
    print("="*80)
    
    if args.mode == "validation":
        result = await example_validation_mode()
    elif args.mode == "gap_analysis":
        result = await example_gap_analysis_mode()
    elif args.mode == "both":
        result = await example_both_modes()
    elif args.mode == "full_pipeline":
        result = await example_full_pipeline()
    
    print("\n" + "="*80)
    print("Example Complete")
    print("="*80 + "\n")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
