"""
Performance Validation for Results Interpretation Agent

This script validates the performance, quality, and robustness of the
ResultsInterpretationAgent against various test scenarios and edge cases.
"""

import asyncio
import time
import statistics
import json
from typing import List, Dict, Any, Tuple
from pathlib import Path

from .results_interpretation_agent import (
    ResultsInterpretationAgent,
    process_interpretation_request
)
from .results_types import (
    ResultsInterpretationState,
    InterpretationRequest,
    ClinicalSignificanceLevel,
    ConfidenceLevel
)


# =============================================================================
# Performance Test Data
# =============================================================================

def get_performance_test_datasets() -> List[Dict[str, Any]]:
    """
    Generate diverse test datasets for performance validation.
    """
    datasets = []
    
    # Dataset 1: Standard RCT with clear effects
    datasets.append({
        "name": "standard_rct_clear_effects",
        "description": "Standard RCT with clear treatment effects",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "Treatment reduces symptoms",
                    "p_value": 0.003,
                    "effect_size": 0.75,
                    "confidence_interval": {"lower": 0.4, "upper": 1.1}
                }
            ],
            "sample_info": {"total_n": 200, "missing_data_rate": 0.02}
        },
        "study_context": {
            "protocol": {"study_design": "randomized controlled trial", "randomized": True},
            "sample_size": 200
        }
    })
    
    # Dataset 2: Observational study with confounders
    datasets.append({
        "name": "observational_confounders",
        "description": "Observational study with potential confounders",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "Exposure associated with outcome",
                    "p_value": 0.045,
                    "effect_size": 0.35,
                    "confidence_interval": {"lower": 0.02, "upper": 0.68}
                }
            ],
            "sample_info": {"total_n": 500, "missing_data_rate": 0.12}
        },
        "study_context": {
            "protocol": {"study_design": "cohort study", "randomized": False},
            "sample_size": 500
        }
    })
    
    # Dataset 3: Small sample size study
    datasets.append({
        "name": "small_sample_underpowered",
        "description": "Small sample size study with power issues",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "Pilot treatment effect",
                    "p_value": 0.12,
                    "effect_size": 0.45,
                    "confidence_interval": {"lower": -0.15, "upper": 1.05}
                }
            ],
            "sample_info": {"total_n": 30, "missing_data_rate": 0.05}
        },
        "study_context": {
            "protocol": {"study_design": "pilot randomized trial", "randomized": True},
            "sample_size": 30
        }
    })
    
    # Dataset 4: Multiple primary endpoints
    datasets.append({
        "name": "multiple_primary_endpoints",
        "description": "Study with multiple primary endpoints",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "Primary endpoint 1",
                    "p_value": 0.025,
                    "effect_size": 0.55,
                    "confidence_interval": {"lower": 0.2, "upper": 0.9}
                },
                {
                    "hypothesis": "Primary endpoint 2", 
                    "p_value": 0.087,
                    "effect_size": 0.32,
                    "confidence_interval": {"lower": -0.05, "upper": 0.69}
                },
                {
                    "hypothesis": "Primary endpoint 3",
                    "p_value": 0.001,
                    "effect_size": 0.85,
                    "confidence_interval": {"lower": 0.48, "upper": 1.22}
                }
            ],
            "sample_info": {"total_n": 180, "missing_data_rate": 0.06}
        },
        "study_context": {
            "protocol": {"study_design": "randomized controlled trial", "randomized": True},
            "sample_size": 180
        }
    })
    
    # Dataset 5: Non-significant results
    datasets.append({
        "name": "non_significant_results",
        "description": "Study with non-significant results",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "No significant treatment effect",
                    "p_value": 0.34,
                    "effect_size": 0.15,
                    "confidence_interval": {"lower": -0.25, "upper": 0.55}
                }
            ],
            "sample_info": {"total_n": 150, "missing_data_rate": 0.03}
        },
        "study_context": {
            "protocol": {"study_design": "randomized controlled trial", "randomized": True},
            "sample_size": 150
        }
    })
    
    # Dataset 6: Large effect with wide confidence intervals
    datasets.append({
        "name": "large_effect_wide_ci",
        "description": "Large effect with wide confidence intervals",
        "statistical_results": {
            "primary_outcomes": [
                {
                    "hypothesis": "Large but uncertain effect",
                    "p_value": 0.048,
                    "effect_size": 1.2,
                    "confidence_interval": {"lower": 0.05, "upper": 2.35}
                }
            ],
            "sample_info": {"total_n": 45, "missing_data_rate": 0.08}
        },
        "study_context": {
            "protocol": {"study_design": "randomized controlled trial", "randomized": True},
            "sample_size": 45
        }
    })
    
    return datasets


# =============================================================================
# Performance Metrics
# =============================================================================

class PerformanceMetrics:
    """Track performance metrics for validation."""
    
    def __init__(self):
        self.processing_times: List[float] = []
        self.quality_scores: List[float] = []
        self.error_rates: List[float] = []
        self.completeness_scores: List[float] = []
        self.interpretation_counts: Dict[str, int] = {}
    
    def add_result(
        self,
        processing_time: float,
        quality_score: float,
        error_count: int,
        completeness_score: float,
        interpretation_data: Dict[str, Any]
    ):
        """Add a performance measurement."""
        self.processing_times.append(processing_time)
        self.quality_scores.append(quality_score)
        self.error_rates.append(error_count)
        self.completeness_scores.append(completeness_score)
        
        # Track interpretation characteristics
        for key, value in interpretation_data.items():
            if key not in self.interpretation_counts:
                self.interpretation_counts[key] = 0
            self.interpretation_counts[key] += value
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        return {
            "processing_time": {
                "mean": statistics.mean(self.processing_times) if self.processing_times else 0,
                "median": statistics.median(self.processing_times) if self.processing_times else 0,
                "std": statistics.stdev(self.processing_times) if len(self.processing_times) > 1 else 0,
                "min": min(self.processing_times) if self.processing_times else 0,
                "max": max(self.processing_times) if self.processing_times else 0
            },
            "quality_score": {
                "mean": statistics.mean(self.quality_scores) if self.quality_scores else 0,
                "median": statistics.median(self.quality_scores) if self.quality_scores else 0,
                "std": statistics.stdev(self.quality_scores) if len(self.quality_scores) > 1 else 0,
                "min": min(self.quality_scores) if self.quality_scores else 0,
                "max": max(self.quality_scores) if self.quality_scores else 0
            },
            "error_rate": {
                "mean": statistics.mean(self.error_rates) if self.error_rates else 0,
                "total_tests": len(self.error_rates),
                "error_free_tests": sum(1 for rate in self.error_rates if rate == 0),
                "success_rate": sum(1 for rate in self.error_rates if rate == 0) / len(self.error_rates) if self.error_rates else 0
            },
            "completeness": {
                "mean": statistics.mean(self.completeness_scores) if self.completeness_scores else 0,
                "median": statistics.median(self.completeness_scores) if self.completeness_scores else 0
            },
            "interpretation_totals": self.interpretation_counts
        }


# =============================================================================
# Validation Functions
# =============================================================================

async def validate_single_dataset(
    dataset: Dict[str, Any],
    agent: ResultsInterpretationAgent
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate agent performance on a single dataset.
    
    Args:
        dataset: Test dataset
        agent: Agent instance to test
        
    Returns:
        Tuple of (success, metrics)
    """
    start_time = time.time()
    
    try:
        # Create request
        request = InterpretationRequest(
            study_id=f"PERF_TEST_{dataset['name']}",
            statistical_results=dataset["statistical_results"],
            study_context=dataset["study_context"]
        )
        
        # Process interpretation
        response = await process_interpretation_request(request)
        
        processing_time = time.time() - start_time
        
        if response.success:
            state = response.interpretation_state
            
            # Calculate metrics
            quality_score = calculate_quality_score(state)
            completeness_issues = state.validate_completeness()
            completeness_score = 1.0 - (len(completeness_issues) / 10.0)  # Normalize to 0-1
            
            interpretation_data = {
                "primary_findings": len(state.primary_findings),
                "secondary_findings": len(state.secondary_findings), 
                "effect_interpretations": len(state.effect_interpretations),
                "limitations": len(state.limitations_identified),
                "confidence_statements": len(state.confidence_statements)
            }
            
            metrics = {
                "success": True,
                "processing_time": processing_time,
                "quality_score": quality_score,
                "error_count": len(state.errors),
                "warning_count": len(state.warnings),
                "completeness_score": max(0.0, completeness_score),
                "interpretation_data": interpretation_data,
                "completeness_issues": completeness_issues
            }
            
            return True, metrics
            
        else:
            metrics = {
                "success": False,
                "processing_time": processing_time,
                "error_message": response.error_message,
                "quality_score": 0.0,
                "error_count": 1,
                "completeness_score": 0.0
            }
            
            return False, metrics
            
    except Exception as e:
        processing_time = time.time() - start_time
        
        metrics = {
            "success": False,
            "processing_time": processing_time,
            "error_message": str(e),
            "quality_score": 0.0,
            "error_count": 1,
            "completeness_score": 0.0
        }
        
        return False, metrics


def calculate_quality_score(state: ResultsInterpretationState) -> float:
    """Calculate quality score for performance validation."""
    score = 0.0
    
    # Completeness (40%)
    if state.primary_findings:
        score += 0.2
    if state.clinical_significance:
        score += 0.1
    if state.limitations_identified:
        score += 0.1
    
    # Content quality (40%)
    if state.confidence_statements:
        score += 0.1
    if state.effect_interpretations:
        score += 0.1
    
    # Statistical interpretation quality (20%)
    significant_findings = [
        f for f in state.primary_findings 
        if f.clinical_significance != ClinicalSignificanceLevel.NOT_SIGNIFICANT
    ]
    if significant_findings:
        score += 0.1
    
    high_confidence_findings = [
        f for f in state.primary_findings
        if f.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]
    ]
    if high_confidence_findings:
        score += 0.1
    
    return min(score, 1.0)


async def run_performance_validation(
    quality_threshold: float = 0.85,
    num_iterations: int = 3
) -> Dict[str, Any]:
    """
    Run comprehensive performance validation.
    
    Args:
        quality_threshold: Minimum acceptable quality score
        num_iterations: Number of iterations per dataset
        
    Returns:
        Validation results summary
    """
    print("🔬 Starting Performance Validation")
    print("=" * 50)
    
    # Initialize agent and metrics
    agent = ResultsInterpretationAgent(quality_threshold=quality_threshold)
    metrics = PerformanceMetrics()
    
    # Get test datasets
    datasets = get_performance_test_datasets()
    
    validation_results = {
        "config": {
            "quality_threshold": quality_threshold,
            "num_iterations": num_iterations,
            "num_datasets": len(datasets)
        },
        "results": [],
        "failures": []
    }
    
    total_tests = len(datasets) * num_iterations
    completed_tests = 0
    
    print(f"📊 Running {total_tests} validation tests...")
    
    for dataset in datasets:
        print(f"\n📋 Testing dataset: {dataset['name']}")
        print(f"   Description: {dataset['description']}")
        
        dataset_results = {
            "dataset_name": dataset["name"],
            "description": dataset["description"],
            "iterations": [],
            "summary": {}
        }
        
        iteration_times = []
        iteration_qualities = []
        iteration_successes = []
        
        for iteration in range(num_iterations):
            print(f"   Iteration {iteration + 1}/{num_iterations}...", end=" ")
            
            success, result_metrics = await validate_single_dataset(dataset, agent)
            
            if success:
                print("✅")
                
                # Add to overall metrics
                metrics.add_result(
                    processing_time=result_metrics["processing_time"],
                    quality_score=result_metrics["quality_score"],
                    error_count=result_metrics["error_count"],
                    completeness_score=result_metrics["completeness_score"],
                    interpretation_data=result_metrics["interpretation_data"]
                )
                
                # Track iteration metrics
                iteration_times.append(result_metrics["processing_time"])
                iteration_qualities.append(result_metrics["quality_score"])
                iteration_successes.append(True)
                
            else:
                print("❌")
                
                # Record failure
                failure_record = {
                    "dataset": dataset["name"],
                    "iteration": iteration + 1,
                    "error": result_metrics.get("error_message", "Unknown error")
                }
                validation_results["failures"].append(failure_record)
                
                iteration_successes.append(False)
            
            dataset_results["iterations"].append(result_metrics)
            completed_tests += 1
        
        # Calculate dataset summary
        if iteration_times:
            dataset_results["summary"] = {
                "success_rate": sum(iteration_successes) / len(iteration_successes),
                "avg_processing_time": statistics.mean(iteration_times),
                "avg_quality_score": statistics.mean(iteration_qualities),
                "quality_threshold_met": all(q >= quality_threshold for q in iteration_qualities)
            }
        else:
            dataset_results["summary"] = {
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "avg_quality_score": 0.0,
                "quality_threshold_met": False
            }
        
        validation_results["results"].append(dataset_results)
        
        print(f"   📈 Success rate: {dataset_results['summary']['success_rate']*100:.1f}%")
        print(f"   ⏱️  Avg time: {dataset_results['summary']['avg_processing_time']:.2f}s")
        print(f"   🎯 Avg quality: {dataset_results['summary']['avg_quality_score']:.2f}")
    
    # Generate overall summary
    overall_metrics = metrics.get_summary()
    
    validation_results["overall_summary"] = {
        "total_tests": total_tests,
        "completed_tests": completed_tests,
        "overall_success_rate": overall_metrics["error_rate"]["success_rate"],
        "performance_metrics": overall_metrics,
        "quality_threshold_compliance": overall_metrics["quality_score"]["mean"] >= quality_threshold,
        "performance_benchmarks": {
            "avg_processing_time_acceptable": overall_metrics["processing_time"]["mean"] < 30.0,  # 30 seconds
            "quality_consistency": overall_metrics["quality_score"]["std"] < 0.2,  # Low variance
            "error_rate_acceptable": overall_metrics["error_rate"]["success_rate"] >= 0.95  # 95% success
        }
    }
    
    return validation_results


def print_validation_summary(results: Dict[str, Any]) -> None:
    """Print formatted validation summary."""
    print("\n" + "=" * 60)
    print("🎯 PERFORMANCE VALIDATION SUMMARY")
    print("=" * 60)
    
    config = results["config"]
    summary = results["overall_summary"]
    
    print(f"\n📋 Configuration:")
    print(f"   Quality threshold: {config['quality_threshold']}")
    print(f"   Iterations per dataset: {config['num_iterations']}")
    print(f"   Total datasets: {config['num_datasets']}")
    print(f"   Total tests: {summary['total_tests']}")
    
    print(f"\n📊 Overall Results:")
    print(f"   Success rate: {summary['overall_success_rate']*100:.1f}%")
    print(f"   Quality threshold compliance: {'✅' if summary['quality_threshold_compliance'] else '❌'}")
    
    perf_metrics = summary["performance_metrics"]
    print(f"\n⏱️  Performance Metrics:")
    print(f"   Avg processing time: {perf_metrics['processing_time']['mean']:.2f}s")
    print(f"   Processing time range: {perf_metrics['processing_time']['min']:.2f}s - {perf_metrics['processing_time']['max']:.2f}s")
    
    print(f"\n🎯 Quality Metrics:")
    print(f"   Avg quality score: {perf_metrics['quality_score']['mean']:.3f}")
    print(f"   Quality score range: {perf_metrics['quality_score']['min']:.3f} - {perf_metrics['quality_score']['max']:.3f}")
    print(f"   Quality consistency (std): {perf_metrics['quality_score']['std']:.3f}")
    
    benchmarks = summary["performance_benchmarks"]
    print(f"\n✅ Benchmark Compliance:")
    print(f"   Processing time acceptable (<30s): {'✅' if benchmarks['avg_processing_time_acceptable'] else '❌'}")
    print(f"   Quality consistency (<0.2 std): {'✅' if benchmarks['quality_consistency'] else '❌'}")
    print(f"   Error rate acceptable (>95%): {'✅' if benchmarks['error_rate_acceptable'] else '❌'}")
    
    print(f"\n📈 Interpretation Totals:")
    totals = perf_metrics["interpretation_totals"]
    for key, value in totals.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    if results["failures"]:
        print(f"\n❌ Failures ({len(results['failures'])}):")
        for failure in results["failures"]:
            print(f"   {failure['dataset']} (iter {failure['iteration']}): {failure['error']}")
    
    # Dataset-specific results
    print(f"\n📋 Dataset Results:")
    for result in results["results"]:
        name = result["dataset_name"]
        summary = result["summary"]
        print(f"   {name}:")
        print(f"     Success: {summary['success_rate']*100:.1f}%")
        print(f"     Quality: {summary['avg_quality_score']:.3f}")
        print(f"     Time: {summary['avg_processing_time']:.2f}s")
    
    # Overall assessment
    all_benchmarks_met = all(benchmarks.values())
    print(f"\n🏆 Overall Assessment: {'PASS' if all_benchmarks_met else 'NEEDS ATTENTION'}")
    
    if all_benchmarks_met:
        print("✅ All performance benchmarks met - Ready for production!")
    else:
        print("⚠️  Some benchmarks not met - Review performance issues before deployment")


async def save_validation_results(results: Dict[str, Any], filename: str = None) -> str:
    """Save validation results to file."""
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"performance_validation_{timestamp}.json"
    
    filepath = Path(filename)
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Validation results saved to: {filepath}")
    return str(filepath)


# =============================================================================
# Main Execution
# =============================================================================

async def main():
    """Main execution function for performance validation."""
    
    print("🔬 ResearchFlow Stage 9 Performance Validation")
    print("📊 Comprehensive Quality and Performance Testing")
    print("=" * 60)
    
    try:
        # Run validation
        results = await run_performance_validation(
            quality_threshold=0.85,
            num_iterations=2  # Reduced for demo - increase for full validation
        )
        
        # Print summary
        print_validation_summary(results)
        
        # Save results
        output_file = await save_validation_results(results)
        
        print(f"\n🎉 Performance validation completed!")
        print(f"📄 Detailed results available in: {output_file}")
        
        return results
        
    except Exception as e:
        print(f"\n💥 Performance validation failed: {str(e)}")
        return None


if __name__ == "__main__":
    asyncio.run(main())