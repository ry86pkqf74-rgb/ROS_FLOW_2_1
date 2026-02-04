"""
Gap Prioritization Logic

Implements prioritization algorithms for research gaps including:
- Impact vs Feasibility matrix (2x2)
- Multi-criteria scoring
- Visualization data generation
- Priority ranking algorithms

Linear Issues: ROS-XXX (Stage 10 - Gap Analysis Agent)
"""

import logging
from typing import List, Dict, Any, Tuple
from .gap_analysis_types import Gap, PrioritizedGap, GapPriority, PrioritizationMatrix

logger = logging.getLogger(__name__)


# =============================================================================
# Prioritization Matrix Generator
# =============================================================================

class GapPrioritizer:
    """
    Prioritize research gaps using multiple criteria.
    
    Main algorithm: Impact vs Feasibility matrix
    Additional factors: Urgency, resource requirements, alignment with goals
    """
    
    # Threshold for high/low classification
    IMPACT_THRESHOLD = 3.5
    FEASIBILITY_THRESHOLD = 3.5
    
    def __init__(self):
        """Initialize prioritizer with default weights."""
        self.weights = {
            "impact": 0.50,
            "feasibility": 0.30,
            "urgency": 0.20
        }
    
    def prioritize_gaps(
        self,
        gaps: List[Gap],
        custom_weights: Dict[str, float] = None
    ) -> List[PrioritizedGap]:
        """
        Prioritize list of gaps using multi-criteria scoring.
        
        Args:
            gaps: List of Gap objects
            custom_weights: Optional custom weights for criteria
        
        Returns:
            List of PrioritizedGap objects sorted by priority
        """
        if custom_weights:
            self.weights.update(custom_weights)
        
        prioritized = []
        
        for gap in gaps:
            # Calculate priority score
            impact = gap.impact_score or 3.0
            feasibility = gap.feasibility_score or 3.0
            urgency = self._calculate_urgency_score(gap)
            
            priority_score = (
                self.weights["impact"] * impact +
                self.weights["feasibility"] * feasibility +
                self.weights["urgency"] * urgency
            )
            
            # Determine priority level
            priority_level = self._determine_priority_level(impact, feasibility)
            
            # Generate rationale
            rationale = self._generate_rationale(gap, impact, feasibility, urgency)
            
            prioritized.append(PrioritizedGap(
                gap=gap,
                priority_score=priority_score,
                priority_level=priority_level,
                rationale=rationale,
                feasibility=self._interpret_feasibility(feasibility),
                expected_impact=self._interpret_impact(impact)
            ))
        
        # Sort by priority score (descending)
        return sorted(prioritized, key=lambda x: x.priority_score, reverse=True)
    
    def create_prioritization_matrix(
        self,
        gaps: List[Gap]
    ) -> PrioritizationMatrix:
        """
        Create 2x2 prioritization matrix (Impact vs Feasibility).
        
        Quadrants:
        - High Priority: High impact + High feasibility
        - Strategic: High impact + Low feasibility
        - Quick Wins: Low impact + High feasibility
        - Low Priority: Low impact + Low feasibility
        
        Args:
            gaps: List of Gap objects
        
        Returns:
            PrioritizationMatrix with gaps categorized
        """
        matrix = PrioritizationMatrix()
        
        for gap in gaps:
            impact = gap.impact_score or 3.0
            feasibility = gap.feasibility_score or 3.0
            
            # Create gap data dict
            gap_data = {
                "gap_id": gap.description[:50],
                "gap_type": gap.gap_type.value,
                "description": gap.description,
                "impact": impact,
                "feasibility": feasibility,
                "evidence_level": gap.evidence_level.value
            }
            
            # Assign to quadrant
            if impact >= self.IMPACT_THRESHOLD and feasibility >= self.FEASIBILITY_THRESHOLD:
                matrix.high_priority.append(gap_data)
            elif impact >= self.IMPACT_THRESHOLD and feasibility < self.FEASIBILITY_THRESHOLD:
                matrix.strategic.append(gap_data)
            elif impact < self.IMPACT_THRESHOLD and feasibility >= self.FEASIBILITY_THRESHOLD:
                matrix.quick_wins.append(gap_data)
            else:
                matrix.low_priority.append(gap_data)
        
        # Add visualization config
        matrix.visualization_config = self._generate_viz_config(matrix)
        
        return matrix
    
    def _determine_priority_level(self, impact: float, feasibility: float) -> GapPriority:
        """Determine priority level from impact and feasibility scores."""
        if impact >= self.IMPACT_THRESHOLD and feasibility >= self.FEASIBILITY_THRESHOLD:
            return GapPriority.HIGH
        elif impact >= self.IMPACT_THRESHOLD and feasibility < self.FEASIBILITY_THRESHOLD:
            return GapPriority.STRATEGIC
        elif impact >= self.IMPACT_THRESHOLD or feasibility >= self.FEASIBILITY_THRESHOLD:
            return GapPriority.MEDIUM
        else:
            return GapPriority.LOW
    
    def _calculate_urgency_score(self, gap: Gap) -> float:
        """
        Calculate urgency score based on gap characteristics.
        
        Args:
            gap: Gap object
        
        Returns:
            Urgency score (1-5)
        """
        # Higher urgency for:
        # - Strong evidence
        # - Temporal gaps (outdated evidence)
        # - Population gaps (equity issues)
        
        urgency = 3.0  # Default
        
        if gap.evidence_level.value == "strong":
            urgency += 0.5
        
        if gap.gap_type.value == "temporal":
            urgency += 1.0
        elif gap.gap_type.value == "population":
            urgency += 0.7
        elif gap.gap_type.value == "methodological":
            urgency += 0.3
        
        return min(5.0, urgency)
    
    def _generate_rationale(
        self,
        gap: Gap,
        impact: float,
        feasibility: float,
        urgency: float
    ) -> str:
        """Generate rationale for priority assignment."""
        parts = []
        
        # Impact reasoning
        if impact >= 4.5:
            parts.append("High potential impact on the field")
        elif impact >= 3.5:
            parts.append("Moderate potential impact")
        else:
            parts.append("Limited immediate impact")
        
        # Feasibility reasoning
        if feasibility >= 4.0:
            parts.append("highly feasible with current resources")
        elif feasibility >= 3.0:
            parts.append("feasible with additional resources")
        else:
            parts.append("requires significant resources")
        
        # Urgency reasoning
        if urgency >= 4.0:
            parts.append("Urgent need for addressing")
        
        # Evidence level
        parts.append(f"supported by {gap.evidence_level.value} evidence")
        
        return "; ".join(parts) + "."
    
    def _interpret_feasibility(self, score: float) -> str:
        """Convert feasibility score to text interpretation."""
        if score >= 4.0:
            return "Highly feasible with current resources and methodology"
        elif score >= 3.0:
            return "Feasible but requires additional resources or methodological development"
        elif score >= 2.0:
            return "Challenging; requires significant methodological innovation"
        else:
            return "Currently not feasible; requires major breakthroughs"
    
    def _interpret_impact(self, score: float) -> str:
        """Convert impact score to text interpretation."""
        if score >= 4.5:
            return "Transformative impact on theory and practice"
        elif score >= 3.5:
            return "Significant contribution to knowledge and clinical practice"
        elif score >= 2.5:
            return "Moderate contribution to specific research area"
        else:
            return "Incremental contribution to literature"
    
    def _generate_viz_config(self, matrix: PrioritizationMatrix) -> Dict[str, Any]:
        """Generate visualization configuration for frontend rendering."""
        return {
            "type": "scatter",
            "title": "Gap Prioritization Matrix: Impact vs Feasibility",
            "x_axis": {
                "label": "Feasibility (1-5)",
                "min": 1,
                "max": 5,
                "threshold": self.FEASIBILITY_THRESHOLD
            },
            "y_axis": {
                "label": "Impact (1-5)",
                "min": 1,
                "max": 5,
                "threshold": self.IMPACT_THRESHOLD
            },
            "quadrants": [
                {
                    "name": "Low Priority",
                    "position": "bottom-left",
                    "color": "#cccccc",
                    "count": len(matrix.low_priority)
                },
                {
                    "name": "Quick Wins",
                    "position": "bottom-right",
                    "color": "#90EE90",
                    "count": len(matrix.quick_wins)
                },
                {
                    "name": "Strategic",
                    "position": "top-left",
                    "color": "#FFD700",
                    "count": len(matrix.strategic)
                },
                {
                    "name": "High Priority",
                    "position": "top-right",
                    "color": "#FF6347",
                    "count": len(matrix.high_priority)
                }
            ],
            "data_points": self._prepare_scatter_data(matrix)
        }
    
    def _prepare_scatter_data(self, matrix: PrioritizationMatrix) -> List[Dict[str, Any]]:
        """Prepare scatter plot data points."""
        points = []
        
        for quadrant_name, gaps in [
            ("high_priority", matrix.high_priority),
            ("strategic", matrix.strategic),
            ("quick_wins", matrix.quick_wins),
            ("low_priority", matrix.low_priority)
        ]:
            for gap in gaps:
                points.append({
                    "x": gap["feasibility"],
                    "y": gap["impact"],
                    "label": gap["gap_id"],
                    "quadrant": quadrant_name,
                    "gap_type": gap["gap_type"],
                    "tooltip": gap["description"]
                })
        
        return points


# =============================================================================
# Multi-Criteria Decision Analysis (MCDA)
# =============================================================================

class MCDAScorer:
    """
    Multi-Criteria Decision Analysis for complex prioritization.
    
    Uses weighted criteria to score gaps:
    - Scientific impact
    - Feasibility
    - Urgency
    - Resource requirements
    - Ethical considerations
    - Alignment with research priorities
    """
    
    def __init__(self):
        """Initialize with default criteria weights."""
        self.criteria = {
            "scientific_impact": 0.25,
            "feasibility": 0.20,
            "urgency": 0.15,
            "resource_efficiency": 0.15,
            "ethical_importance": 0.15,
            "strategic_alignment": 0.10
        }
    
    def score_gap(
        self,
        gap: Gap,
        context: Dict[str, Any] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Score a gap using MCDA.
        
        Args:
            gap: Gap object to score
            context: Optional context (research priorities, resources, etc.)
        
        Returns:
            Tuple of (overall_score, criterion_scores)
        """
        context = context or {}
        
        # Score each criterion (1-5 scale)
        scores = {
            "scientific_impact": gap.impact_score or 3.0,
            "feasibility": gap.feasibility_score or 3.0,
            "urgency": self._score_urgency(gap),
            "resource_efficiency": self._score_resource_efficiency(gap),
            "ethical_importance": self._score_ethical_importance(gap),
            "strategic_alignment": self._score_strategic_alignment(gap, context)
        }
        
        # Calculate weighted overall score
        overall = sum(scores[k] * self.criteria[k] for k in self.criteria)
        
        return overall, scores
    
    def _score_urgency(self, gap: Gap) -> float:
        """Score urgency (1-5)."""
        # Similar to GapPrioritizer but more granular
        base_score = 3.0
        
        if gap.gap_type.value == "temporal":
            base_score = 4.5
        elif gap.gap_type.value == "population":
            base_score = 4.0
        elif gap.gap_type.value == "methodological":
            base_score = 3.5
        
        if gap.evidence_level.value == "strong":
            base_score += 0.5
        
        return min(5.0, base_score)
    
    def _score_resource_efficiency(self, gap: Gap) -> float:
        """Score how efficiently resources would be used (1-5)."""
        # Inverse of resource requirements
        if gap.addressability.value == "feasible":
            return 4.5
        elif gap.addressability.value == "challenging":
            return 3.0
        else:
            return 1.5
    
    def _score_ethical_importance(self, gap: Gap) -> float:
        """Score ethical importance (1-5)."""
        # Population and geographic gaps have higher ethical importance
        if gap.gap_type.value == "population":
            return 4.5
        elif gap.gap_type.value == "geographic":
            return 4.0
        else:
            return 3.0
    
    def _score_strategic_alignment(self, gap: Gap, context: Dict[str, Any]) -> float:
        """Score alignment with strategic priorities (1-5)."""
        # Would need context about organization/funder priorities
        # For now, return moderate score
        priorities = context.get("research_priorities", [])
        
        if not priorities:
            return 3.0
        
        # Check if gap type aligns with priorities
        if gap.gap_type.value in priorities:
            return 4.5
        
        return 2.5
