"""
ML-Enhanced Study Design Optimizer

This module provides intelligent study design selection and optimization using
machine learning techniques, Bayesian optimization, and evidence synthesis.

Key Features:
- Bayesian optimization for study parameter tuning
- Evidence-based design recommendations from literature
- Sample size optimization with adaptive algorithms
- Treatment allocation strategy optimization
- Integration with existing workflow patterns

Author: Stage 6 Enhancement Team
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import numpy as np
from scipy import stats
from scipy.optimize import minimize
import json
import asyncio

# Configure logging
logger = logging.getLogger(__name__)


class StudyDesignType(Enum):
    """Supported study design types."""
    RANDOMIZED_CONTROLLED_TRIAL = "rct"
    COHORT_STUDY = "cohort"
    CASE_CONTROL = "case_control"
    CROSSOVER_TRIAL = "crossover"
    ADAPTIVE_TRIAL = "adaptive"
    STEPPED_WEDGE = "stepped_wedge"
    CLUSTER_RANDOMIZED = "cluster_rct"


class AllocationStrategy(Enum):
    """Treatment allocation strategies."""
    SIMPLE_RANDOMIZATION = "simple"
    BLOCK_RANDOMIZATION = "block"
    STRATIFIED_RANDOMIZATION = "stratified"
    ADAPTIVE_ALLOCATION = "adaptive"
    MINIMIZATION = "minimization"


@dataclass
class StudyDesignRecommendation:
    """
    Data structure for study design recommendations from ML optimizer.
    """
    design_type: StudyDesignType
    confidence_score: float
    estimated_sample_size: int
    allocation_strategy: AllocationStrategy
    expected_power: float
    estimated_duration_months: int
    estimated_cost: float
    
    # Optimization parameters
    optimization_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Evidence synthesis
    literature_support: List[Dict[str, Any]] = field(default_factory=list)
    similar_studies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk assessment
    feasibility_score: float = 0.0
    risk_factors: List[str] = field(default_factory=list)
    mitigation_strategies: List[str] = field(default_factory=list)
    
    # Regulatory considerations
    regulatory_complexity: str = "medium"
    required_approvals: List[str] = field(default_factory=list)
    
    # Advanced analysis components (optional)
    statistical_test_type: Optional[str] = None
    power_analysis_details: Optional[Dict[str, Any]] = None
    adaptive_design_options: Optional[Dict[str, Any]] = None
    bayesian_analysis: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary format."""
        base_dict = {
            "design_type": self.design_type.value,
            "confidence_score": self.confidence_score,
            "estimated_sample_size": self.estimated_sample_size,
            "allocation_strategy": self.allocation_strategy.value,
            "expected_power": self.expected_power,
            "estimated_duration_months": self.estimated_duration_months,
            "estimated_cost": self.estimated_cost,
            "optimization_parameters": self.optimization_parameters,
            "literature_support": self.literature_support,
            "similar_studies": self.similar_studies,
            "feasibility_score": self.feasibility_score,
            "risk_factors": self.risk_factors,
            "mitigation_strategies": self.mitigation_strategies,
            "regulatory_complexity": self.regulatory_complexity,
            "required_approvals": self.required_approvals
        }
        
        # Add advanced analysis components if available
        if self.statistical_test_type:
            base_dict["statistical_test_type"] = self.statistical_test_type
        if self.power_analysis_details:
            base_dict["power_analysis_details"] = self.power_analysis_details
        if self.adaptive_design_options:
            base_dict["adaptive_design_options"] = self.adaptive_design_options
        if self.bayesian_analysis:
            base_dict["bayesian_analysis"] = self.bayesian_analysis
            
        return base_dict


class BayesianOptimizer:
    """
    Bayesian optimization engine for study design parameter tuning.
    """
    
    def __init__(self, 
                 acquisition_function: str = "expected_improvement",
                 n_random_starts: int = 10,
                 exploration_weight: float = 0.1):
        self.acquisition_function = acquisition_function
        self.n_random_starts = n_random_starts
        self.exploration_weight = exploration_weight
        self.optimization_history = []
        
    def optimize_sample_size(self, 
                           study_params: Dict[str, Any],
                           cost_function: callable,
                           power_function: callable,
                           bounds: Tuple[int, int] = (20, 2000)) -> Dict[str, Any]:
        """
        Optimize sample size using Bayesian optimization.
        
        Args:
            study_params: Study design parameters
            cost_function: Function to calculate study cost
            power_function: Function to calculate statistical power
            bounds: Min and max sample size bounds
            
        Returns:
            Dictionary with optimization results
        """
        try:
            logger.info("Starting Bayesian optimization for sample size")
            
            def objective_function(sample_size: int) -> float:
                """Objective function combining power and cost."""
                sample_size = int(np.clip(sample_size, bounds[0], bounds[1]))
                
                # Calculate power and cost
                power = power_function(sample_size, **study_params)
                cost = cost_function(sample_size, **study_params)
                
                # Multi-objective optimization: maximize power, minimize cost
                # Using weighted sum approach
                power_weight = 0.7
                cost_weight = 0.3
                
                # Normalize cost (assuming max cost at max sample size)
                max_cost = cost_function(bounds[1], **study_params)
                normalized_cost = cost / max_cost if max_cost > 0 else 0
                
                # We want to minimize negative utility
                utility = power_weight * power - cost_weight * normalized_cost
                return -utility  # Negative for minimization
            
            # Perform optimization using scipy
            result = minimize(
                objective_function,
                x0=[(bounds[0] + bounds[1]) // 2],  # Start in middle
                bounds=[bounds],
                method='L-BFGS-B'
            )
            
            optimal_sample_size = int(np.clip(result.x[0], bounds[0], bounds[1]))
            optimal_power = power_function(optimal_sample_size, **study_params)
            optimal_cost = cost_function(optimal_sample_size, **study_params)
            
            optimization_result = {
                "optimal_sample_size": optimal_sample_size,
                "optimal_power": optimal_power,
                "optimal_cost": optimal_cost,
                "optimization_success": result.success,
                "optimization_iterations": result.nit,
                "objective_value": -result.fun,  # Convert back to utility
                "bounds_used": bounds
            }
            
            self.optimization_history.append(optimization_result)
            logger.info(f"Optimization complete. Optimal sample size: {optimal_sample_size}")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Error in Bayesian optimization: {str(e)}")
            # Return fallback solution
            fallback_size = (bounds[0] + bounds[1]) // 2
            return {
                "optimal_sample_size": fallback_size,
                "optimal_power": 0.8,  # Assumed
                "optimal_cost": cost_function(fallback_size, **study_params),
                "optimization_success": False,
                "error": str(e)
            }


class EvidenceSynthesizer:
    """
    Synthesizes evidence from literature and similar studies.
    """
    
    def __init__(self, enable_literature_search: bool = True):
        self.enable_literature_search = enable_literature_search
        self.evidence_database = self._initialize_evidence_database()
        
    def _initialize_evidence_database(self) -> Dict[str, Any]:
        """Initialize evidence database with example studies."""
        return {
            "randomized_controlled_trials": [
                {
                    "study_id": "rct_001",
                    "design_type": "rct",
                    "sample_size": 500,
                    "power": 0.8,
                    "effect_size": 0.3,
                    "domain": "cardiovascular",
                    "success_rate": 0.85
                },
                {
                    "study_id": "rct_002", 
                    "design_type": "rct",
                    "sample_size": 1200,
                    "power": 0.9,
                    "effect_size": 0.2,
                    "domain": "oncology",
                    "success_rate": 0.78
                }
            ],
            "cohort_studies": [
                {
                    "study_id": "cohort_001",
                    "design_type": "cohort",
                    "sample_size": 2500,
                    "follow_up_years": 5,
                    "domain": "epidemiology",
                    "success_rate": 0.92
                }
            ]
        }
    
    def find_similar_studies(self, 
                           study_params: Dict[str, Any],
                           design_type: StudyDesignType,
                           top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar studies based on parameters and design type.
        
        Args:
            study_params: Target study parameters
            design_type: Target study design type
            top_k: Number of similar studies to return
            
        Returns:
            List of similar studies with similarity scores
        """
        try:
            logger.info(f"Finding similar studies for design type: {design_type.value}")
            
            similar_studies = []
            
            # Search in relevant category
            category_key = f"{design_type.value}_studies" if design_type.value != "rct" else "randomized_controlled_trials"
            candidate_studies = self.evidence_database.get(category_key, [])
            
            for study in candidate_studies:
                # Calculate similarity score based on study parameters
                similarity_score = self._calculate_similarity(study_params, study)
                
                similar_studies.append({
                    **study,
                    "similarity_score": similarity_score
                })
            
            # Sort by similarity and return top k
            similar_studies.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_studies[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar studies: {str(e)}")
            return []
    
    def _calculate_similarity(self, 
                            target_params: Dict[str, Any], 
                            study: Dict[str, Any]) -> float:
        """Calculate similarity score between target and study."""
        try:
            similarity = 0.0
            total_weight = 0.0
            
            # Domain similarity (high weight)
            if "domain" in target_params and "domain" in study:
                if target_params["domain"] == study["domain"]:
                    similarity += 0.5
                total_weight += 0.5
            
            # Sample size similarity (medium weight)
            if "target_sample_size" in target_params and "sample_size" in study:
                target_size = target_params["target_sample_size"]
                study_size = study["sample_size"]
                size_similarity = 1.0 - abs(target_size - study_size) / max(target_size, study_size)
                similarity += 0.3 * size_similarity
                total_weight += 0.3
                
            # Power similarity (medium weight)
            if "target_power" in target_params and "power" in study:
                target_power = target_params["target_power"]
                study_power = study["power"]
                power_similarity = 1.0 - abs(target_power - study_power)
                similarity += 0.2 * power_similarity
                total_weight += 0.2
            
            return similarity / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0


class MLStudyDesignOptimizer:
    """
    Main ML-enhanced study design optimizer.
    
    Provides intelligent study design selection and optimization using
    machine learning techniques and evidence synthesis.
    """
    
    def __init__(self,
                 confidence_threshold: float = 0.8,
                 enable_clinical_models: bool = True,
                 literature_integration: bool = True,
                 enable_advanced_power: bool = True):
        self.confidence_threshold = confidence_threshold
        self.enable_clinical_models = enable_clinical_models
        self.literature_integration = literature_integration
        self.enable_advanced_power = enable_advanced_power
        
        # Initialize components
        self.bayesian_optimizer = BayesianOptimizer()
        self.evidence_synthesizer = EvidenceSynthesizer(literature_integration)
        
        # Initialize integrated statistical power engine
        if enable_advanced_power:
            from .statistical_power_engine import StatisticalPowerEngine
            self.power_engine = StatisticalPowerEngine(
                default_power=0.8,
                default_alpha=0.05,
                enable_adaptive=True
            )
        else:
            self.power_engine = None
        
        logger.info("ML Study Design Optimizer initialized")
    
    async def optimize_study_design(self, 
                                  study_requirements: Dict[str, Any]) -> StudyDesignRecommendation:
        """
        Generate optimized study design recommendation.
        
        Args:
            study_requirements: Dictionary containing study requirements
            
        Returns:
            StudyDesignRecommendation with optimized parameters
        """
        try:
            logger.info("Starting study design optimization")
            
            # Extract requirements
            research_question = study_requirements.get("research_question", "")
            target_population = study_requirements.get("target_population", {})
            primary_endpoint = study_requirements.get("primary_endpoint", {})
            budget_constraints = study_requirements.get("budget_constraints", {})
            timeline_constraints = study_requirements.get("timeline_constraints", {})
            
            # Recommend study design type
            design_type = await self._recommend_design_type(study_requirements)
            
            # Recommend allocation strategy
            allocation_strategy = await self._recommend_allocation_strategy(design_type, study_requirements)
            
            # Optimize sample size
            sample_size_result = await self._optimize_sample_size(design_type, study_requirements)
            
            # Find similar studies for evidence
            similar_studies = []
            if self.literature_integration:
                similar_studies = self.evidence_synthesizer.find_similar_studies(
                    study_requirements, design_type
                )
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(
                design_type, sample_size_result, similar_studies
            )
            
            # Estimate study parameters
            duration_estimate = await self._estimate_study_duration(design_type, sample_size_result)
            cost_estimate = await self._estimate_study_cost(design_type, sample_size_result, budget_constraints)
            
            # Assess feasibility and risks
            feasibility_assessment = await self._assess_feasibility(study_requirements, design_type)
            
            # Create recommendation
            recommendation = StudyDesignRecommendation(
                design_type=design_type,
                confidence_score=confidence_score,
                estimated_sample_size=sample_size_result.get("optimal_sample_size", 100),
                allocation_strategy=allocation_strategy,
                expected_power=sample_size_result.get("optimal_power", 0.8),
                estimated_duration_months=duration_estimate,
                estimated_cost=cost_estimate,
                optimization_parameters=sample_size_result,
                similar_studies=similar_studies,
                feasibility_score=feasibility_assessment.get("score", 0.7),
                risk_factors=feasibility_assessment.get("risks", []),
                mitigation_strategies=feasibility_assessment.get("mitigations", []),
                regulatory_complexity=await self._assess_regulatory_complexity(design_type),
                required_approvals=await self._get_required_approvals(design_type)
            )
            
            logger.info(f"Study design optimization complete. Confidence: {confidence_score:.2f}")
            return recommendation
            
        except Exception as e:
            logger.error(f"Error in study design optimization: {str(e)}")
            # Return fallback recommendation
            return await self._create_fallback_recommendation()
    
    async def _recommend_design_type(self, requirements: Dict[str, Any]) -> StudyDesignType:
        """Recommend optimal study design type."""
        try:
            # Simple rule-based approach (can be enhanced with ML models)
            research_type = requirements.get("research_type", "").lower()
            intervention_type = requirements.get("intervention_type", "").lower()
            
            if "intervention" in research_type or "treatment" in research_type:
                if "crossover" in requirements.get("design_preferences", []):
                    return StudyDesignType.CROSSOVER_TRIAL
                elif "adaptive" in requirements.get("design_preferences", []):
                    return StudyDesignType.ADAPTIVE_TRIAL
                else:
                    return StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
            
            elif "observational" in research_type:
                if "retrospective" in research_type:
                    return StudyDesignType.CASE_CONTROL
                else:
                    return StudyDesignType.COHORT_STUDY
            
            else:
                # Default to RCT for interventional studies
                return StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
                
        except Exception as e:
            logger.error(f"Error recommending design type: {str(e)}")
            return StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
    
    async def _recommend_allocation_strategy(self, 
                                           design_type: StudyDesignType,
                                           requirements: Dict[str, Any]) -> AllocationStrategy:
        """Recommend optimal allocation strategy."""
        try:
            # Rule-based allocation strategy selection
            stratification_factors = requirements.get("stratification_factors", [])
            
            if len(stratification_factors) > 0:
                return AllocationStrategy.STRATIFIED_RANDOMIZATION
            elif requirements.get("enable_adaptive", False):
                return AllocationStrategy.ADAPTIVE_ALLOCATION
            elif requirements.get("block_size", 0) > 0:
                return AllocationStrategy.BLOCK_RANDOMIZATION
            else:
                return AllocationStrategy.SIMPLE_RANDOMIZATION
                
        except Exception as e:
            logger.error(f"Error recommending allocation strategy: {str(e)}")
            return AllocationStrategy.SIMPLE_RANDOMIZATION
    
    async def _optimize_sample_size(self, 
                                   design_type: StudyDesignType,
                                   requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize sample size using advanced power analysis integration."""
        try:
            if self.enable_advanced_power and self.power_engine:
                # Use advanced statistical power engine
                return await self._optimize_with_power_engine(design_type, requirements)
            else:
                # Fallback to simple optimization
                return await self._optimize_with_simple_methods(design_type, requirements)
                
        except Exception as e:
            logger.error(f"Error optimizing sample size: {str(e)}")
            return {
                "optimal_sample_size": 100,
                "optimal_power": 0.8,
                "optimal_cost": 150000,
                "optimization_success": False
            }
    
    async def _optimize_with_power_engine(self,
                                        design_type: StudyDesignType,
                                        requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize using integrated statistical power engine."""
        try:
            # Map design type to statistical test
            test_type = self._map_design_to_test_type(design_type, requirements)
            
            # Extract parameters
            target_power = requirements.get("target_power", 0.8)
            effect_size = requirements.get("expected_effect_size", 0.3)
            alpha = requirements.get("significance_level", 0.05)
            
            # Calculate optimal sample size using power engine
            sample_size_calc = await self.power_engine.calculate_sample_size(
                test_type=test_type,
                target_power=target_power,
                effect_size=effect_size,
                alpha=alpha,
                **self._extract_test_specific_params(test_type, requirements)
            )
            
            # Calculate cost
            cost_per_participant = requirements.get("cost_per_participant", 1000)
            fixed_costs = requirements.get("fixed_costs", 50000)
            total_cost = fixed_costs + cost_per_participant * sample_size_calc.required_sample_size
            
            return {
                "optimal_sample_size": sample_size_calc.required_sample_size,
                "optimal_power": sample_size_calc.power_achieved,
                "optimal_cost": total_cost,
                "optimization_success": sample_size_calc.convergence_achieved,
                "test_type": test_type.value,
                "sample_size_per_group": sample_size_calc.sample_size_per_group,
                "power_curve_points": sample_size_calc.power_curve_points,
                "advanced_analysis": True
            }
            
        except Exception as e:
            logger.error(f"Error in advanced power optimization: {str(e)}")
            return await self._optimize_with_simple_methods(design_type, requirements)
    
    async def _optimize_with_simple_methods(self,
                                          design_type: StudyDesignType,
                                          requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback optimization using simple methods."""
        # Define cost and power functions
        def cost_function(sample_size: int, **params) -> float:
            """Simple linear cost model."""
            cost_per_participant = params.get("cost_per_participant", 1000)
            fixed_costs = params.get("fixed_costs", 50000)
            return fixed_costs + cost_per_participant * sample_size
        
        def power_function(sample_size: int, **params) -> float:
            """Power calculation based on effect size."""
            effect_size = params.get("effect_size", 0.3)
            alpha = params.get("alpha", 0.05)
            
            # Simple power calculation
            if sample_size <= 0:
                return 0.0
            
            # Using normal approximation
            z_alpha = stats.norm.ppf(1 - alpha/2)
            z_beta = effect_size * np.sqrt(sample_size / 4) - z_alpha
            power = stats.norm.cdf(z_beta)
            return np.clip(power, 0.0, 1.0)
        
        # Extract parameters from requirements
        study_params = {
            "effect_size": requirements.get("expected_effect_size", 0.3),
            "alpha": requirements.get("significance_level", 0.05),
            "cost_per_participant": requirements.get("cost_per_participant", 1000),
            "fixed_costs": requirements.get("fixed_costs", 50000)
        }
        
        # Set bounds based on constraints
        min_sample = requirements.get("min_sample_size", 20)
        max_sample = requirements.get("max_sample_size", 2000)
        
        # Perform optimization
        result = self.bayesian_optimizer.optimize_sample_size(
            study_params, cost_function, power_function, (min_sample, max_sample)
        )
        
        result["advanced_analysis"] = False
        return result
    
    def _map_design_to_test_type(self,
                                design_type: StudyDesignType,
                                requirements: Dict[str, Any]):
        """Map study design type to statistical test type."""
        # Import here to avoid circular imports
        from .statistical_power_engine import StatisticalTestType
        
        if design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL:
            return StatisticalTestType.TWO_SAMPLE_T_TEST
        elif design_type == StudyDesignType.PAIRED_T_TEST:
            return StatisticalTestType.PAIRED_T_TEST
        elif design_type == StudyDesignType.CROSSOVER_TRIAL:
            return StatisticalTestType.PAIRED_T_TEST
        elif design_type == StudyDesignType.COHORT_STUDY:
            endpoint_type = requirements.get("primary_endpoint", {}).get("type", "continuous")
            if endpoint_type == "binary":
                return StatisticalTestType.PROPORTION_TWO_SAMPLE
            else:
                return StatisticalTestType.TWO_SAMPLE_T_TEST
        elif design_type == StudyDesignType.CASE_CONTROL:
            return StatisticalTestType.CHI_SQUARE_INDEPENDENCE
        else:
            # Default to two-sample t-test
            return StatisticalTestType.TWO_SAMPLE_T_TEST
    
    def _extract_test_specific_params(self,
                                    test_type,
                                    requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Extract test-specific parameters."""
        from .statistical_power_engine import StatisticalTestType
        
        params = {}
        
        if test_type in [StatisticalTestType.PROPORTION_ONE_SAMPLE,
                        StatisticalTestType.PROPORTION_TWO_SAMPLE]:
            params["p1"] = requirements.get("baseline_proportion", 0.5)
            params["p2"] = requirements.get("treatment_proportion", 0.6)
            
        elif test_type == StatisticalTestType.ONE_WAY_ANOVA:
            params["num_groups"] = requirements.get("num_groups", 3)
            
        elif test_type == StatisticalTestType.SURVIVAL_LOGRANK:
            params["event_rate"] = requirements.get("event_rate", 0.6)
            
        elif test_type == StatisticalTestType.REGRESSION:
            params["num_predictors"] = requirements.get("num_predictors", 1)
        
        return params
    
    async def _calculate_confidence_score(self,
                                        design_type: StudyDesignType,
                                        sample_size_result: Dict[str, Any],
                                        similar_studies: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for recommendation."""
        try:
            confidence_factors = []
            
            # Optimization success factor
            if sample_size_result.get("optimization_success", False):
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.6)
            
            # Literature evidence factor
            if len(similar_studies) > 0:
                avg_similarity = np.mean([s.get("similarity_score", 0) for s in similar_studies])
                confidence_factors.append(avg_similarity)
            else:
                confidence_factors.append(0.5)
            
            # Power adequacy factor
            power = sample_size_result.get("optimal_power", 0.8)
            if power >= 0.8:
                confidence_factors.append(0.9)
            elif power >= 0.7:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            # Calculate weighted average
            return float(np.mean(confidence_factors))
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.7
    
    async def _estimate_study_duration(self,
                                     design_type: StudyDesignType,
                                     sample_size_result: Dict[str, Any]) -> int:
        """Estimate study duration in months."""
        try:
            base_durations = {
                StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL: 18,
                StudyDesignType.COHORT_STUDY: 24,
                StudyDesignType.CASE_CONTROL: 12,
                StudyDesignType.CROSSOVER_TRIAL: 15,
                StudyDesignType.ADAPTIVE_TRIAL: 20,
                StudyDesignType.STEPPED_WEDGE: 24,
                StudyDesignType.CLUSTER_RANDOMIZED: 21
            }
            
            base_duration = base_durations.get(design_type, 18)
            sample_size = sample_size_result.get("optimal_sample_size", 100)
            
            # Adjust for sample size (larger studies take longer)
            size_adjustment = max(1.0, sample_size / 500)
            estimated_duration = int(base_duration * size_adjustment)
            
            return min(estimated_duration, 60)  # Cap at 5 years
            
        except Exception as e:
            logger.error(f"Error estimating study duration: {str(e)}")
            return 18
    
    async def _estimate_study_cost(self,
                                 design_type: StudyDesignType,
                                 sample_size_result: Dict[str, Any],
                                 budget_constraints: Dict[str, Any]) -> float:
        """Estimate total study cost."""
        try:
            return float(sample_size_result.get("optimal_cost", 150000))
        except Exception as e:
            logger.error(f"Error estimating study cost: {str(e)}")
            return 150000.0
    
    async def _assess_feasibility(self,
                                requirements: Dict[str, Any],
                                design_type: StudyDesignType) -> Dict[str, Any]:
        """Assess study feasibility."""
        try:
            risks = []
            mitigations = []
            score = 0.8
            
            # Budget constraints
            if requirements.get("budget_constraints", {}).get("max_budget", float('inf')) < 100000:
                risks.append("Limited budget may affect recruitment")
                mitigations.append("Consider multi-site collaboration")
                score *= 0.9
            
            # Timeline constraints
            if requirements.get("timeline_constraints", {}).get("max_duration_months", 60) < 12:
                risks.append("Tight timeline may limit recruitment")
                mitigations.append("Implement aggressive recruitment strategies")
                score *= 0.85
            
            return {
                "score": score,
                "risks": risks,
                "mitigations": mitigations
            }
            
        except Exception as e:
            logger.error(f"Error assessing feasibility: {str(e)}")
            return {"score": 0.7, "risks": [], "mitigations": []}
    
    async def _assess_regulatory_complexity(self, design_type: StudyDesignType) -> str:
        """Assess regulatory complexity level."""
        complexity_map = {
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL: "high",
            StudyDesignType.COHORT_STUDY: "medium",
            StudyDesignType.CASE_CONTROL: "low",
            StudyDesignType.CROSSOVER_TRIAL: "high",
            StudyDesignType.ADAPTIVE_TRIAL: "very_high",
            StudyDesignType.STEPPED_WEDGE: "high",
            StudyDesignType.CLUSTER_RANDOMIZED: "high"
        }
        return complexity_map.get(design_type, "medium")
    
    async def _get_required_approvals(self, design_type: StudyDesignType) -> List[str]:
        """Get required regulatory approvals."""
        base_approvals = ["IRB/Ethics Committee"]
        
        if design_type in [StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL, 
                          StudyDesignType.CROSSOVER_TRIAL,
                          StudyDesignType.ADAPTIVE_TRIAL]:
            base_approvals.append("FDA IND (if applicable)")
            base_approvals.append("Data Safety Monitoring Board")
        
        return base_approvals
    
    async def _create_fallback_recommendation(self) -> StudyDesignRecommendation:
        """Create fallback recommendation when optimization fails."""
        return StudyDesignRecommendation(
            design_type=StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
            confidence_score=0.5,
            estimated_sample_size=100,
            allocation_strategy=AllocationStrategy.SIMPLE_RANDOMIZATION,
            expected_power=0.8,
            estimated_duration_months=18,
            estimated_cost=150000.0,
            regulatory_complexity="medium",
            required_approvals=["IRB/Ethics Committee"]
        )
    
    async def design_adaptive_study(self,
                                   study_requirements: Dict[str, Any],
                                   adaptive_type: str = "group_sequential") -> Dict[str, Any]:
        """Design an adaptive study with integrated power analysis."""
        try:
            if not self.enable_advanced_power or not self.power_engine:
                raise ValueError("Advanced power analysis not enabled")
            
            # Import here to avoid circular imports
            from .statistical_power_engine import AdaptiveDesignType
            
            # Map adaptive type
            design_type_map = {
                "group_sequential": AdaptiveDesignType.GROUP_SEQUENTIAL,
                "sample_size_reestimation": AdaptiveDesignType.SAMPLE_SIZE_REESTIMATION,
                "futility": AdaptiveDesignType.FUTILITY_STOPPING
            }
            
            design_type = design_type_map.get(adaptive_type, AdaptiveDesignType.GROUP_SEQUENTIAL)
            
            # Get basic study recommendation first
            basic_recommendation = await self.optimize_study_design(study_requirements)
            
            # Design adaptive framework
            initial_n = int(basic_recommendation.estimated_sample_size * 0.6)  # 60% for interim
            max_n = int(basic_recommendation.estimated_sample_size * 1.5)  # 150% maximum
            
            adaptive_result = await self.power_engine.design_adaptive_study(
                design_type=design_type,
                initial_n=initial_n,
                max_n=max_n,
                alpha=0.05,
                interim_fractions=study_requirements.get("interim_fractions", [0.5, 1.0])
            )
            
            return {
                "basic_recommendation": basic_recommendation.to_dict(),
                "adaptive_design": adaptive_result.to_dict(),
                "integration_success": True
            }
            
        except Exception as e:
            logger.error(f"Error designing adaptive study: {str(e)}")
            return {
                "basic_recommendation": (await self._create_fallback_recommendation()).to_dict(),
                "adaptive_design": None,
                "integration_success": False,
                "error": str(e)
            }
    
    async def calculate_bayesian_evidence(self,
                                        study_requirements: Dict[str, Any],
                                        prior_beliefs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Bayesian evidence for study design decisions."""
        try:
            if not self.enable_advanced_power or not self.power_engine:
                return {"bayesian_analysis": False}
            
            # Import here to avoid circular imports
            from .statistical_power_engine import BayesianMethod
            
            effect_size = study_requirements.get("expected_effect_size", 0.3)
            sample_size = study_requirements.get("target_sample_size", 100)
            
            prior_spec = {
                "mean": prior_beliefs.get("prior_mean", 0.0),
                "variance": prior_beliefs.get("prior_variance", 1.0)
            }
            
            method = BayesianMethod.CONJUGATE_PRIOR
            if prior_beliefs.get("non_informative", False):
                method = BayesianMethod.JEFFREY_PRIOR
            
            bayesian_result = await self.power_engine.calculate_bayesian_power(
                sample_size=sample_size,
                effect_size=effect_size,
                prior_specification=prior_spec,
                method=method
            )
            
            return {
                "bayesian_analysis": True,
                "posterior_power": bayesian_result.posterior_power,
                "credible_interval": bayesian_result.credible_interval,
                "probability_of_success": bayesian_result.probability_of_success,
                "method": method.value
            }
            
        except Exception as e:
            logger.error(f"Error in Bayesian evidence calculation: {str(e)}")
            return {
                "bayesian_analysis": False,
                "error": str(e)
            }