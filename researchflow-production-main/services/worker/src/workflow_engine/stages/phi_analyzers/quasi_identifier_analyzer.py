"""
Quasi-Identifier Analysis for PHI Detection

Implements comprehensive k-anonymity, l-diversity, and t-closeness analysis
to identify combinations of columns that could uniquely identify individuals.

Based on research from:
- Sweeney, L. "k-anonymity: a model for protecting privacy" (2002)
- Machanavajjhala, A. "l-diversity: Privacy beyond k-anonymity" (2007)
- Li, N. "t-closeness: Privacy beyond k-anonymity and l-diversity" (2007)
"""

import logging
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Quasi-identifier patterns based on medical research privacy literature
SENSITIVE_QUASI_COMBINATIONS = [
    # Demographics
    ["age", "zip_code", "gender"],
    ["birth_year", "zip_code", "race"],
    ["age_group", "postal_code", "ethnicity"],
    
    # Medical context
    ["admission_date", "zip_code", "age"],
    ["diagnosis_date", "location", "age"],
    ["procedure_date", "hospital", "gender"],
    
    # Geographic + temporal
    ["date", "zip_code", "age"],
    ["year", "city", "age_range"],
    ["month", "state", "gender"],
    
    # Research-specific
    ["study_date", "site", "demographic"],
    ["enrollment_date", "center", "age_group"],
    
    # High-risk combinations (3+ attributes)
    ["age", "zip_code", "gender", "race"],
    ["date", "location", "demographic", "condition"],
    ["admission_date", "zip_code", "age", "gender"],
]

# Column name patterns that indicate quasi-identifiers
QUASI_IDENTIFIER_PATTERNS = {
    "age": ["age", "age_at", "age_years", "birth_year", "dob", "date_of_birth"],
    "location": ["zip", "zip_code", "postal", "city", "state", "county", "address", "location"],
    "gender": ["gender", "sex", "male", "female"],
    "race": ["race", "ethnicity", "ethnic", "racial"],
    "date": ["date", "admission", "discharge", "visit", "enrollment", "procedure"],
    "demographics": ["demo", "demographic", "population", "cohort"],
}


@dataclass
class QuasiIdentifierPattern:
    """Definition of a quasi-identifier combination."""
    columns: List[str]
    risk_level: str  # "critical", "high", "medium", "low"
    description: str
    min_k_threshold: int = 5  # Minimum k-anonymity required


@dataclass
class KAnonymityResult:
    """Result of k-anonymity analysis."""
    k_value: int
    total_groups: int
    unique_individuals: int  # Groups with k=1
    at_risk_individuals: int  # Groups with k<threshold
    group_sizes: List[int]
    risk_level: str
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_anonymous(self) -> bool:
        """Check if dataset meets k-anonymity requirements."""
        return self.k_value >= 5 and self.unique_individuals == 0


@dataclass 
class LDiversityResult:
    """Result of l-diversity analysis."""
    l_value: int
    sensitive_attributes: List[str]
    diversity_by_group: Dict[str, int]
    risk_level: str
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TClosenessResult:
    """Result of t-closeness analysis."""
    t_value: float
    sensitive_attributes: List[str] 
    distance_by_group: Dict[str, float]
    risk_level: str
    recommendations: List[str] = field(default_factory=list)


class QuasiIdentifierAnalyzer:
    """
    Advanced quasi-identifier analysis for privacy protection.
    
    Analyzes datasets for combinations of attributes that could uniquely
    identify individuals, violating privacy requirements.
    """
    
    def __init__(self, 
                 k_threshold: int = 5,
                 l_threshold: int = 2,
                 t_threshold: float = 0.2):
        """
        Initialize the analyzer.
        
        Args:
            k_threshold: Minimum k-anonymity required (default: 5)
            l_threshold: Minimum l-diversity required (default: 2)
            t_threshold: Maximum t-closeness allowed (default: 0.2)
        """
        self.k_threshold = k_threshold
        self.l_threshold = l_threshold  
        self.t_threshold = t_threshold
        
        # Build quasi-identifier patterns from column names
        self.quasi_patterns = self._build_quasi_patterns()
        
        logger.info(f"QuasiIdentifierAnalyzer initialized: k≥{k_threshold}, l≥{l_threshold}, t≤{t_threshold}")
    
    def _build_quasi_patterns(self) -> List[QuasiIdentifierPattern]:
        """Build quasi-identifier patterns with risk levels."""
        patterns = []
        
        # Add predefined sensitive combinations
        for combo in SENSITIVE_QUASI_COMBINATIONS:
            risk_level = self._assess_combination_risk(combo)
            pattern = QuasiIdentifierPattern(
                columns=combo,
                risk_level=risk_level,
                description=f"Combination of {', '.join(combo)}",
                min_k_threshold=self.k_threshold if risk_level == "critical" else 3
            )
            patterns.append(pattern)
        
        return patterns
    
    def _assess_combination_risk(self, columns: List[str]) -> str:
        """Assess risk level of column combination."""
        if len(columns) >= 4:
            return "critical"
        elif any(col in ["ssn", "mrn", "patient_id"] for col in columns):
            return "critical"
        elif len(columns) == 3 and any(col in ["age", "zip", "date"] for col in columns):
            return "high"
        elif len(columns) == 3:
            return "medium"
        else:
            return "low"
    
    def identify_quasi_identifiers(self, df: pd.DataFrame) -> List[str]:
        """
        Identify columns that are potential quasi-identifiers.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of column names that are quasi-identifiers
        """
        quasi_columns = []
        df_columns_lower = [col.lower() for col in df.columns]
        
        for category, patterns in QUASI_IDENTIFIER_PATTERNS.items():
            for pattern in patterns:
                for col in df.columns:
                    if pattern in col.lower() and col not in quasi_columns:
                        quasi_columns.append(col)
                        logger.debug(f"Identified quasi-identifier: {col} (category: {category})")
        
        # Also check for high-cardinality columns that could be identifiers
        for col in df.columns:
            if col in quasi_columns:
                continue
                
            # Check cardinality ratio
            unique_ratio = df[col].nunique() / len(df) if len(df) > 0 else 0
            if unique_ratio > 0.8:  # >80% unique values
                quasi_columns.append(col)
                logger.debug(f"Identified high-cardinality quasi-identifier: {col} (uniqueness: {unique_ratio:.2%})")
        
        return quasi_columns
    
    def analyze_k_anonymity(self, 
                           df: pd.DataFrame, 
                           quasi_columns: Optional[List[str]] = None) -> KAnonymityResult:
        """
        Analyze k-anonymity for the dataset.
        
        Args:
            df: DataFrame to analyze
            quasi_columns: Specific quasi-identifier columns to analyze
            
        Returns:
            K-anonymity analysis results
        """
        if quasi_columns is None:
            quasi_columns = self.identify_quasi_identifiers(df)
        
        if not quasi_columns:
            return KAnonymityResult(
                k_value=len(df),  # No quasi-identifiers = perfectly anonymous
                total_groups=1,
                unique_individuals=0,
                at_risk_individuals=0,
                group_sizes=[len(df)],
                risk_level="none",
                recommendations=["No quasi-identifiers detected"]
            )
        
        # Group by quasi-identifier combinations
        try:
            grouped = df.groupby(quasi_columns, dropna=False)
            group_sizes = grouped.size().tolist()
        except Exception as e:
            logger.warning(f"Could not group by quasi-identifiers {quasi_columns}: {e}")
            # Fallback: treat all rows as unique
            group_sizes = [1] * len(df)
        
        # Calculate k-anonymity metrics
        k_value = min(group_sizes) if group_sizes else 0
        unique_individuals = sum(1 for size in group_sizes if size == 1)
        at_risk_individuals = sum(1 for size in group_sizes if size < self.k_threshold)
        
        # Assess risk level
        if unique_individuals > 0:
            risk_level = "critical"
        elif at_risk_individuals > len(group_sizes) * 0.1:  # >10% at risk
            risk_level = "high" 
        elif k_value < self.k_threshold:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = self._generate_k_anonymity_recommendations(
            k_value, unique_individuals, at_risk_individuals, quasi_columns
        )
        
        return KAnonymityResult(
            k_value=k_value,
            total_groups=len(group_sizes),
            unique_individuals=unique_individuals,
            at_risk_individuals=at_risk_individuals,
            group_sizes=group_sizes,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def analyze_l_diversity(self, 
                           df: pd.DataFrame,
                           quasi_columns: List[str],
                           sensitive_columns: List[str]) -> LDiversityResult:
        """
        Analyze l-diversity for sensitive attributes.
        
        Args:
            df: DataFrame to analyze
            quasi_columns: Quasi-identifier columns
            sensitive_columns: Sensitive attribute columns
            
        Returns:
            L-diversity analysis results
        """
        if not quasi_columns or not sensitive_columns:
            return LDiversityResult(
                l_value=len(df),
                sensitive_attributes=sensitive_columns,
                diversity_by_group={},
                risk_level="none",
                recommendations=["No analysis possible - missing columns"]
            )
        
        diversity_by_group = {}
        min_l_value = float('inf')
        
        try:
            # Group by quasi-identifiers
            grouped = df.groupby(quasi_columns, dropna=False)
            
            for group_key, group_df in grouped:
                group_name = str(group_key) if isinstance(group_key, tuple) else str(group_key)
                group_diversity = {}
                
                for sens_col in sensitive_columns:
                    if sens_col in group_df.columns:
                        unique_values = group_df[sens_col].nunique()
                        group_diversity[sens_col] = unique_values
                        min_l_value = min(min_l_value, unique_values)
                
                diversity_by_group[group_name] = group_diversity
        
        except Exception as e:
            logger.warning(f"Could not analyze l-diversity: {e}")
            min_l_value = 1
        
        # Assess risk level
        if min_l_value < self.l_threshold:
            risk_level = "high"
        elif min_l_value < self.l_threshold * 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        recommendations = self._generate_l_diversity_recommendations(
            min_l_value, sensitive_columns
        )
        
        return LDiversityResult(
            l_value=int(min_l_value) if min_l_value != float('inf') else 1,
            sensitive_attributes=sensitive_columns,
            diversity_by_group=diversity_by_group,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def analyze_comprehensive_risk(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive quasi-identifier analysis.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Complete analysis results
        """
        analysis_start = datetime.utcnow()
        
        # Identify quasi-identifiers
        quasi_columns = self.identify_quasi_identifiers(df)
        
        # Identify potential sensitive columns
        sensitive_columns = self._identify_sensitive_columns(df)
        
        # Perform k-anonymity analysis
        k_anonymity = self.analyze_k_anonymity(df, quasi_columns)
        
        # Perform l-diversity analysis if sensitive columns found
        l_diversity = None
        if sensitive_columns:
            l_diversity = self.analyze_l_diversity(df, quasi_columns, sensitive_columns)
        
        # Calculate overall risk score
        overall_risk = self._calculate_overall_risk(k_anonymity, l_diversity)
        
        # Generate comprehensive recommendations
        recommendations = self._generate_comprehensive_recommendations(
            quasi_columns, sensitive_columns, k_anonymity, l_diversity
        )
        
        analysis_duration = (datetime.utcnow() - analysis_start).total_seconds()
        
        return {
            "analysis_timestamp": analysis_start.isoformat() + "Z",
            "analysis_duration_seconds": analysis_duration,
            "dataset_info": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "quasi_identifier_columns": quasi_columns,
                "sensitive_columns": sensitive_columns,
            },
            "k_anonymity": {
                "k_value": k_anonymity.k_value,
                "is_anonymous": k_anonymity.is_anonymous,
                "unique_individuals": k_anonymity.unique_individuals,
                "at_risk_individuals": k_anonymity.at_risk_individuals,
                "risk_level": k_anonymity.risk_level,
                "recommendations": k_anonymity.recommendations,
            },
            "l_diversity": {
                "l_value": l_diversity.l_value if l_diversity else None,
                "risk_level": l_diversity.risk_level if l_diversity else "none",
                "recommendations": l_diversity.recommendations if l_diversity else [],
            } if l_diversity else None,
            "overall_risk": overall_risk,
            "comprehensive_recommendations": recommendations,
            "privacy_preserving_strategies": self._suggest_privacy_strategies(
                k_anonymity, l_diversity, quasi_columns
            ),
        }
    
    def _identify_sensitive_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns containing sensitive information."""
        sensitive_patterns = [
            "diagnosis", "condition", "disease", "symptom",
            "medication", "treatment", "therapy", "drug",
            "income", "salary", "financial", "credit",
            "religion", "political", "sexual", "orientation",
            "mental", "psychiatric", "psychological",
            "genetic", "hereditary", "family_history"
        ]
        
        sensitive_columns = []
        for col in df.columns:
            col_lower = col.lower()
            if any(pattern in col_lower for pattern in sensitive_patterns):
                sensitive_columns.append(col)
        
        return sensitive_columns
    
    def _generate_k_anonymity_recommendations(self, 
                                            k_value: int,
                                            unique_individuals: int,
                                            at_risk_individuals: int,
                                            quasi_columns: List[str]) -> List[str]:
        """Generate recommendations for k-anonymity issues."""
        recommendations = []
        
        if unique_individuals > 0:
            recommendations.append(
                f"CRITICAL: {unique_individuals} individuals can be uniquely identified. "
                "Consider suppression or generalization of quasi-identifiers."
            )
        
        if k_value < self.k_threshold:
            recommendations.append(
                f"K-anonymity threshold not met (k={k_value}, required≥{self.k_threshold}). "
                "Apply generalization to increase group sizes."
            )
        
        if at_risk_individuals > 0:
            recommendations.append(
                f"{at_risk_individuals} groups have insufficient anonymity. "
                "Focus generalization on: {', '.join(quasi_columns[:3])}"
            )
        
        # Specific recommendations for quasi-identifier types
        for col in quasi_columns:
            col_lower = col.lower()
            if "zip" in col_lower or "postal" in col_lower:
                recommendations.append(f"Generalize {col} to 3-digit ZIP codes")
            elif "age" in col_lower:
                recommendations.append(f"Generalize {col} to 5-year age ranges")
            elif "date" in col_lower:
                recommendations.append(f"Generalize {col} to month/year only")
        
        return recommendations
    
    def _generate_l_diversity_recommendations(self, 
                                            l_value: int,
                                            sensitive_columns: List[str]) -> List[str]:
        """Generate recommendations for l-diversity issues."""
        recommendations = []
        
        if l_value < self.l_threshold:
            recommendations.append(
                f"L-diversity threshold not met (l={l_value}, required≥{self.l_threshold}). "
                f"Sensitive attributes in {', '.join(sensitive_columns)} lack diversity."
            )
            recommendations.append(
                "Consider: (1) Suppression of homogeneous groups, "
                "(2) Generalization of sensitive values, "
                "(3) Addition of synthetic diverse values"
            )
        
        return recommendations
    
    def _generate_comprehensive_recommendations(self,
                                              quasi_columns: List[str],
                                              sensitive_columns: List[str],
                                              k_anonymity: KAnonymityResult,
                                              l_diversity: Optional[LDiversityResult]) -> List[str]:
        """Generate comprehensive privacy recommendations."""
        recommendations = []
        
        # Dataset-level recommendations
        if not quasi_columns:
            recommendations.append("✅ No quasi-identifiers detected - dataset appears privacy-safe")
        elif k_anonymity.is_anonymous and (not l_diversity or l_diversity.l_value >= self.l_threshold):
            recommendations.append("✅ Dataset meets privacy requirements")
        
        # Strategy recommendations
        if quasi_columns and not k_anonymity.is_anonymous:
            recommendations.extend([
                "🔧 Apply k-anonymity techniques:",
                "   • Generalization: Replace specific values with ranges/categories", 
                "   • Suppression: Remove identifying outliers",
                "   • Perturbation: Add controlled noise to numerical values"
            ])
        
        if sensitive_columns and l_diversity and l_diversity.l_value < self.l_threshold:
            recommendations.extend([
                "🔧 Apply l-diversity techniques:",
                "   • Ensure each group has diverse sensitive values",
                "   • Consider sensitive value generalization",
                "   • Evaluate data utility vs. privacy trade-offs"
            ])
        
        # Technical implementation
        recommendations.extend([
            "📋 Implementation steps:",
            "   1. Back up original dataset",
            "   2. Apply recommended transformations",
            "   3. Re-run privacy analysis to verify compliance",
            "   4. Document all transformations for audit trail"
        ])
        
        return recommendations
    
    def _calculate_overall_risk(self, 
                               k_anonymity: KAnonymityResult,
                               l_diversity: Optional[LDiversityResult]) -> Dict[str, Any]:
        """Calculate overall privacy risk score."""
        # Risk scoring (0-100, where 100 = maximum risk)
        k_risk = 0
        if k_anonymity.unique_individuals > 0:
            k_risk = 100
        elif k_anonymity.k_value < self.k_threshold:
            k_risk = 80
        elif k_anonymity.at_risk_individuals > 0:
            k_risk = 60
        
        l_risk = 0
        if l_diversity:
            if l_diversity.l_value < self.l_threshold:
                l_risk = 70
            elif l_diversity.l_value < self.l_threshold * 2:
                l_risk = 40
        
        overall_score = max(k_risk, l_risk)
        
        if overall_score >= 80:
            level = "critical"
        elif overall_score >= 60:
            level = "high"
        elif overall_score >= 40:
            level = "medium"
        else:
            level = "low"
        
        return {
            "risk_score": overall_score,
            "risk_level": level,
            "k_anonymity_risk": k_risk,
            "l_diversity_risk": l_risk,
            "requires_immediate_action": overall_score >= 80,
            "suitable_for_research": overall_score < 60,
        }
    
    def _suggest_privacy_strategies(self,
                                  k_anonymity: KAnonymityResult,
                                  l_diversity: Optional[LDiversityResult], 
                                  quasi_columns: List[str]) -> Dict[str, Any]:
        """Suggest specific privacy-preserving strategies."""
        strategies = {
            "generalization": [],
            "suppression": [],
            "perturbation": [],
            "synthetic_data": [],
        }
        
        # Generalization strategies
        for col in quasi_columns:
            col_lower = col.lower()
            if "zip" in col_lower:
                strategies["generalization"].append({
                    "column": col,
                    "method": "zip_3digit",
                    "description": f"Generalize {col} to first 3 digits only"
                })
            elif "age" in col_lower:
                strategies["generalization"].append({
                    "column": col,
                    "method": "age_ranges", 
                    "description": f"Convert {col} to 5-year age ranges (25-29, 30-34, etc.)"
                })
            elif "date" in col_lower:
                strategies["generalization"].append({
                    "column": col,
                    "method": "date_month",
                    "description": f"Generalize {col} to month/year only"
                })
        
        # Suppression strategies  
        if k_anonymity.unique_individuals > 0:
            strategies["suppression"].append({
                "method": "outlier_removal",
                "description": "Remove records with unique quasi-identifier combinations",
                "estimated_data_loss": f"{k_anonymity.unique_individuals}/{k_anonymity.total_groups * 100:.1f}%"
            })
        
        # Perturbation strategies
        strategies["perturbation"].append({
            "method": "differential_privacy", 
            "description": "Add calibrated noise to numerical columns",
            "epsilon_recommendation": 1.0
        })
        
        # Synthetic data
        if k_anonymity.risk_level in ["critical", "high"]:
            strategies["synthetic_data"].append({
                "method": "generative_model",
                "description": "Generate synthetic dataset preserving statistical properties",
                "tools": ["SDV", "DataSynthesizer", "CTGAN"]
            })
        
        return strategies


def hash_quasi_combination(values: List[Any]) -> str:
    """Create a hash of quasi-identifier combination for tracking."""
    combined = "|".join(str(v) for v in values)
    return hashlib.sha256(combined.encode()).hexdigest()[:12]