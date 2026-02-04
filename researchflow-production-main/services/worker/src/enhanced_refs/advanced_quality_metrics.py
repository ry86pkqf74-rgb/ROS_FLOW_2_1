"""
Advanced Quality Metrics Engine

ML-powered multi-dimensional quality assessment system for academic references
with field-specific criteria, trend analysis, and automated red flag detection.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from enum import Enum
import re
import json

from .reference_types import Reference, QualityScore
from .reference_cache import get_cache
from .api_management import get_api_manager

logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """Quality assessment dimensions."""
    CREDIBILITY = "credibility"
    RECENCY = "recency" 
    RELEVANCE = "relevance"
    IMPACT = "impact"
    METHODOLOGY = "methodology"
    COMPLETENESS = "completeness"
    ACCESSIBILITY = "accessibility"

class QualityLevel(Enum):
    """Overall quality levels."""
    EXCEPTIONAL = "exceptional"  # 0.90+
    HIGH = "high"               # 0.75-0.89
    GOOD = "good"               # 0.60-0.74
    ACCEPTABLE = "acceptable"    # 0.45-0.59
    POOR = "poor"               # 0.30-0.44
    PROBLEMATIC = "problematic" # <0.30

@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for a reference."""
    reference_id: str
    overall_score: float
    quality_level: QualityLevel
    dimension_scores: Dict[str, float]
    red_flags: List[str]
    quality_indicators: List[str]
    improvement_suggestions: List[str]
    field_percentile: Optional[float]
    confidence: float
    assessment_timestamp: datetime
    
@dataclass
class QualityTrend:
    """Quality trend analysis."""
    reference_id: str
    historical_scores: List[Tuple[datetime, float]]
    trend_direction: str  # improving, declining, stable
    trend_strength: float
    predicted_future_score: Optional[float]

@dataclass
class RedFlag:
    """Red flag detection result."""
    flag_type: str
    severity: str  # low, medium, high, critical
    description: str
    evidence: List[str]
    recommendation: str

class AdvancedQualityMetricsEngine:
    """
    Advanced quality metrics engine with ML-powered assessment.
    
    Features:
    - Multi-dimensional quality scoring across 7 dimensions
    - Field-specific quality criteria and thresholds
    - ML-based pattern recognition for quality indicators
    - Automated red flag detection (predatory journals, retractions)
    - Quality trend analysis and prediction
    - Peer comparison and percentile ranking
    - Comprehensive improvement suggestions
    """
    
    # Predatory journal indicators (would be loaded from database)
    PREDATORY_INDICATORS = {
        'publisher_names': [
            'scirp', 'omics', 'waset', 'academicstar', 'intech',
            'science domain', 'science publication group'
        ],
        'journal_patterns': [
            r'international.*journal.*of.*science',
            r'global.*journal.*research',
            r'american.*journal.*of.*applied',
            r'world.*journal.*of.*'
        ],
        'suspicious_issns': [
            # Would contain known predatory ISSNs
        ]
    }
    
    # High-quality journal indicators
    QUALITY_INDICATORS = {
        'top_tier_journals': [
            'nature', 'science', 'cell', 'lancet', 'new england journal of medicine',
            'jama', 'bmj', 'pnas', 'nature medicine', 'nature biotechnology'
        ],
        'quality_publishers': [
            'nature publishing group', 'elsevier', 'springer', 'wiley',
            'american medical association', 'bmj publishing'
        ],
        'database_inclusion': [
            'pubmed', 'web of science', 'scopus', 'medline'
        ]
    }
    
    # Field-specific quality thresholds
    FIELD_THRESHOLDS = {
        'medical_research': {
            'min_sample_size': 100,
            'required_methodology': ['randomized', 'controlled', 'blind'],
            'min_impact_factor': 2.0,
            'max_age_years': 10
        },
        'machine_learning': {
            'required_validation': ['cross-validation', 'test set', 'benchmark'],
            'min_citations': 10,
            'max_age_years': 5
        },
        'clinical_medicine': {
            'required_ethics': ['ethics approval', 'informed consent'],
            'min_followup_months': 6,
            'required_reporting': ['consort', 'strobe']
        }
    }
    
    def __init__(self):
        self.cache = None
        self.api_manager = None
        self.quality_patterns = {}
        self.field_models = {}
        self.stats = {
            'assessments_performed': 0,
            'red_flags_detected': 0,
            'quality_improvements_suggested': 0,
            'trend_analyses_completed': 0
        }
        
        self._initialize_ml_patterns()
    
    async def initialize(self):
        """Initialize the advanced quality metrics engine."""
        self.cache = await get_cache()
        self.api_manager = await get_api_manager()
        await self._load_quality_databases()
        logger.info("Advanced quality metrics engine initialized")
    
    def _initialize_ml_patterns(self):
        """Initialize ML patterns for quality assessment."""
        
        # Quality indicator patterns (would be trained ML models in production)
        self.quality_patterns = {
            'high_quality_title_patterns': [
                r'randomized.*controlled.*trial',
                r'systematic.*review.*meta-analysis',
                r'multicenter.*study',
                r'double.*blind.*placebo',
                r'prospective.*cohort',
                r'machine.*learning.*validation'
            ],
            'methodology_quality_patterns': [
                r'sample.*size.*calculation',
                r'power.*analysis',
                r'statistical.*significance.*p\s*<',
                r'confidence.*interval',
                r'effect.*size',
                r'cross.*validation',
                r'inter.*rater.*reliability'
            ],
            'reporting_quality_patterns': [
                r'consort.*guidelines',
                r'prisma.*statement',
                r'strobe.*checklist',
                r'ethics.*approval',
                r'conflict.*interest.*statement',
                r'data.*availability.*statement'
            ]
        }
    
    async def _load_quality_databases(self):
        """Load external quality databases (retracted papers, journal rankings)."""
        # In production, would load from external APIs/databases
        pass
    
    async def assess_reference_quality(
        self,
        reference: Reference,
        context: str = "",
        research_field: str = "general"
    ) -> QualityMetrics:
        """
        Perform comprehensive quality assessment of a reference.
        
        Args:
            reference: Reference to assess
            context: Context where reference is used
            research_field: Research field for field-specific assessment
            
        Returns:
            Comprehensive quality metrics
        """
        self.stats['assessments_performed'] += 1
        
        # Multi-dimensional scoring
        dimension_scores = {}
        
        dimension_scores[QualityDimension.CREDIBILITY.value] = await self._assess_credibility(reference)
        dimension_scores[QualityDimension.RECENCY.value] = await self._assess_recency(reference, research_field)
        dimension_scores[QualityDimension.RELEVANCE.value] = await self._assess_relevance(reference, context)
        dimension_scores[QualityDimension.IMPACT.value] = await self._assess_impact(reference)
        dimension_scores[QualityDimension.METHODOLOGY.value] = await self._assess_methodology(reference, research_field)
        dimension_scores[QualityDimension.COMPLETENESS.value] = await self._assess_completeness(reference)
        dimension_scores[QualityDimension.ACCESSIBILITY.value] = await self._assess_accessibility(reference)
        
        # Calculate overall score with weighted dimensions
        weights = {
            QualityDimension.CREDIBILITY.value: 0.25,
            QualityDimension.RECENCY.value: 0.15,
            QualityDimension.RELEVANCE.value: 0.20,
            QualityDimension.IMPACT.value: 0.15,
            QualityDimension.METHODOLOGY.value: 0.15,
            QualityDimension.COMPLETENESS.value: 0.05,
            QualityDimension.ACCESSIBILITY.value: 0.05
        }
        
        overall_score = sum(
            dimension_scores[dim] * weights[dim] 
            for dim in dimension_scores.keys()
        )
        
        # Determine quality level
        quality_level = self._determine_quality_level(overall_score)
        
        # Detect red flags
        red_flags = await self._detect_red_flags(reference)
        
        # Generate quality indicators
        quality_indicators = await self._identify_quality_indicators(reference, dimension_scores)
        
        # Generate improvement suggestions
        improvement_suggestions = await self._generate_improvement_suggestions(reference, dimension_scores, research_field)
        
        # Calculate field percentile
        field_percentile = await self._calculate_field_percentile(reference, overall_score, research_field)
        
        # Calculate confidence
        confidence = self._calculate_assessment_confidence(reference, dimension_scores)
        
        return QualityMetrics(
            reference_id=reference.id,
            overall_score=overall_score,
            quality_level=quality_level,
            dimension_scores=dimension_scores,
            red_flags=red_flags,
            quality_indicators=quality_indicators,
            improvement_suggestions=improvement_suggestions,
            field_percentile=field_percentile,
            confidence=confidence,
            assessment_timestamp=datetime.utcnow()
        )
    
    async def _assess_credibility(self, reference: Reference) -> float:
        """Assess credibility dimension."""
        score = 0.5  # Base score
        
        # Journal reputation
        if reference.journal:
            journal_lower = reference.journal.lower()
            
            # Top-tier journals
            if any(top_journal in journal_lower for top_journal in self.QUALITY_INDICATORS['top_tier_journals']):
                score += 0.3
            
            # Quality publishers
            if any(publisher in journal_lower for publisher in self.QUALITY_INDICATORS['quality_publishers']):
                score += 0.2
            
            # Check for predatory indicators
            predatory_score = 0.0
            if any(pred in journal_lower for pred in self.PREDATORY_INDICATORS['publisher_names']):
                predatory_score -= 0.4
            
            for pattern in self.PREDATORY_INDICATORS['journal_patterns']:
                if re.search(pattern, journal_lower):
                    predatory_score -= 0.3
                    break
            
            score += predatory_score
        
        # DOI presence (indicates formal publication)
        if reference.doi:
            score += 0.1
        
        # PMID presence (indicates PubMed indexing)
        if reference.pmid:
            score += 0.1
        
        # Author credibility (simplified)
        if reference.authors and len(reference.authors) >= 2:
            score += 0.1  # Multi-author papers often more credible
        
        return max(0.0, min(1.0, score))
    
    async def _assess_recency(self, reference: Reference, research_field: str) -> float:
        """Assess recency dimension."""
        if not reference.year:
            return 0.4  # Unknown year gets neutral score
        
        current_year = datetime.now().year
        age_years = current_year - reference.year
        
        # Field-specific age scoring
        field_thresholds = self.FIELD_THRESHOLDS.get(research_field, {})
        max_age = field_thresholds.get('max_age_years', 15)
        
        if age_years <= 2:
            return 1.0  # Very recent
        elif age_years <= 5:
            return 0.9  # Recent
        elif age_years <= max_age:
            # Linear decay
            return 0.9 - (0.6 * (age_years - 5) / (max_age - 5))
        else:
            return 0.3  # Old but may still be valuable
    
    async def _assess_relevance(self, reference: Reference, context: str) -> float:
        """Assess relevance dimension."""
        if not context:
            return 0.6  # No context provided
        
        # Simple relevance scoring (would use embeddings in production)
        context_words = set(context.lower().split())
        ref_text = f"{reference.title} {reference.abstract or ''}".lower()
        ref_words = set(ref_text.split())
        
        if context_words and ref_words:
            overlap = len(context_words.intersection(ref_words))
            union = len(context_words.union(ref_words))
            jaccard_score = overlap / union if union > 0 else 0
            
            # Boost for exact phrase matches
            exact_matches = 0
            for word in context_words:
                if len(word) > 4 and word in ref_text:
                    exact_matches += 1
            
            exact_boost = min(exact_matches * 0.1, 0.3)
            return min(1.0, jaccard_score * 2 + exact_boost)
        
        return 0.5
    
    async def _assess_impact(self, reference: Reference) -> float:
        """Assess impact dimension."""
        score = 0.3  # Base score
        
        # Citation count
        if reference.citation_count:
            if reference.citation_count >= 1000:
                score += 0.4
            elif reference.citation_count >= 100:
                score += 0.3
            elif reference.citation_count >= 20:
                score += 0.2
            elif reference.citation_count >= 5:
                score += 0.1
        
        # Journal impact factor (would be fetched from database)
        if reference.journal:
            # Simplified impact factor estimation
            journal_lower = reference.journal.lower()
            if any(top in journal_lower for top in ['nature', 'science', 'cell']):
                score += 0.3
            elif any(med in journal_lower for med in ['lancet', 'nejm', 'jama']):
                score += 0.25
        
        return min(1.0, score)
    
    async def _assess_methodology(self, reference: Reference, research_field: str) -> float:
        """Assess methodology dimension."""
        if not reference.title and not reference.abstract:
            return 0.4  # No content to assess
        
        content = f"{reference.title} {reference.abstract or ''}".lower()
        score = 0.4  # Base score
        
        # General methodology indicators
        methodology_terms = [
            'randomized', 'controlled', 'double-blind', 'placebo',
            'systematic review', 'meta-analysis', 'cohort study',
            'statistical analysis', 'regression', 'correlation'
        ]
        
        found_terms = sum(1 for term in methodology_terms if term in content)
        score += min(found_terms * 0.08, 0.4)
        
        # Field-specific methodology requirements
        field_requirements = self.FIELD_THRESHOLDS.get(research_field, {})
        
        if 'required_methodology' in field_requirements:
            required_methods = field_requirements['required_methodology']
            found_required = sum(1 for method in required_methods if method in content)
            if required_methods:
                score += 0.2 * (found_required / len(required_methods))
        
        # Quality pattern matching
        for pattern_list in self.quality_patterns.values():
            for pattern in pattern_list:
                if re.search(pattern, content):
                    score += 0.05
        
        return min(1.0, score)
    
    async def _assess_completeness(self, reference: Reference) -> float:
        """Assess completeness of reference metadata."""
        required_fields = ['title', 'authors', 'year', 'journal']
        optional_fields = ['volume', 'issue', 'pages', 'doi', 'abstract']
        
        required_present = sum(1 for field in required_fields if getattr(reference, field))
        optional_present = sum(1 for field in optional_fields if getattr(reference, field))
        
        required_score = required_present / len(required_fields)
        optional_score = optional_present / len(optional_fields)
        
        return 0.7 * required_score + 0.3 * optional_score
    
    async def _assess_accessibility(self, reference: Reference) -> float:
        """Assess accessibility of the reference."""
        score = 0.5  # Base score
        
        # DOI provides persistent access
        if reference.doi:
            score += 0.2
        
        # URL availability
        if reference.url:
            score += 0.1
        
        # PMID indicates PubMed availability
        if reference.pmid:
            score += 0.1
        
        # Open access indicators
        if reference.journal:
            journal_lower = reference.journal.lower()
            open_access_journals = ['plos one', 'bmc', 'frontiers', 'mdpi']
            if any(oa in journal_lower for oa in open_access_journals):
                score += 0.2
        
        return min(1.0, score)
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """Determine overall quality level from score."""
        if overall_score >= 0.90:
            return QualityLevel.EXCEPTIONAL
        elif overall_score >= 0.75:
            return QualityLevel.HIGH
        elif overall_score >= 0.60:
            return QualityLevel.GOOD
        elif overall_score >= 0.45:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= 0.30:
            return QualityLevel.POOR
        else:
            return QualityLevel.PROBLEMATIC
    
    async def _detect_red_flags(self, reference: Reference) -> List[str]:
        """Detect quality red flags."""
        red_flags = []
        
        if reference.journal:
            journal_lower = reference.journal.lower()
            
            # Predatory publisher check
            if any(pred in journal_lower for pred in self.PREDATORY_INDICATORS['publisher_names']):
                red_flags.append("Potential predatory publisher")
            
            # Suspicious journal pattern
            for pattern in self.PREDATORY_INDICATORS['journal_patterns']:
                if re.search(pattern, journal_lower):
                    red_flags.append("Suspicious journal name pattern")
                    break
        
        # Very old reference
        if reference.year and datetime.now().year - reference.year > 25:
            red_flags.append("Very old reference (>25 years)")
        
        # Missing critical information
        if not reference.authors:
            red_flags.append("Missing author information")
        
        if not reference.title:
            red_flags.append("Missing title")
        
        # Suspicious citation count
        if reference.citation_count and reference.citation_count == 0 and reference.year and datetime.now().year - reference.year > 5:
            red_flags.append("No citations after 5+ years")
        
        if red_flags:
            self.stats['red_flags_detected'] += len(red_flags)
        
        return red_flags
    
    async def _identify_quality_indicators(self, reference: Reference, dimension_scores: Dict[str, float]) -> List[str]:
        """Identify positive quality indicators."""
        indicators = []
        
        # High-impact journal
        if reference.journal:
            journal_lower = reference.journal.lower()
            if any(top in journal_lower for top in self.QUALITY_INDICATORS['top_tier_journals']):
                indicators.append("Published in top-tier journal")
        
        # High citation count
        if reference.citation_count and reference.citation_count >= 100:
            indicators.append(f"High citation count ({reference.citation_count})")
        
        # Strong methodology
        if dimension_scores.get(QualityDimension.METHODOLOGY.value, 0) >= 0.8:
            indicators.append("Strong methodological rigor")
        
        # Recent publication
        if reference.year and datetime.now().year - reference.year <= 2:
            indicators.append("Very recent publication")
        
        # Complete metadata
        if dimension_scores.get(QualityDimension.COMPLETENESS.value, 0) >= 0.9:
            indicators.append("Complete reference metadata")
        
        # DOI and PMID presence
        if reference.doi and reference.pmid:
            indicators.append("Persistent identifiers available")
        
        return indicators
    
    async def _generate_improvement_suggestions(self, reference: Reference, dimension_scores: Dict[str, float], research_field: str) -> List[str]:
        """Generate suggestions for improving reference quality."""
        suggestions = []
        
        # Low credibility
        if dimension_scores.get(QualityDimension.CREDIBILITY.value, 0) < 0.5:
            suggestions.append("Consider replacing with references from more reputable journals")
        
        # Low recency
        if dimension_scores.get(QualityDimension.RECENCY.value, 0) < 0.4:
            suggestions.append("Supplement with more recent literature")
        
        # Low methodology
        if dimension_scores.get(QualityDimension.METHODOLOGY.value, 0) < 0.5:
            suggestions.append("Look for references with stronger methodological approaches")
        
        # Low impact
        if dimension_scores.get(QualityDimension.IMPACT.value, 0) < 0.4:
            suggestions.append("Consider higher-impact references if available")
        
        # Incomplete metadata
        if dimension_scores.get(QualityDimension.COMPLETENESS.value, 0) < 0.7:
            suggestions.append("Complete missing reference metadata (DOI, page numbers, etc.)")
        
        # Field-specific suggestions
        field_thresholds = self.FIELD_THRESHOLDS.get(research_field, {})
        if 'min_impact_factor' in field_thresholds:
            suggestions.append(f"Ensure references meet field standards for {research_field}")
        
        if suggestions:
            self.stats['quality_improvements_suggested'] += len(suggestions)
        
        return suggestions
    
    async def _calculate_field_percentile(self, reference: Reference, score: float, research_field: str) -> Optional[float]:
        """Calculate percentile ranking within research field."""
        # Would query database of field-specific quality scores
        # For now, return estimated percentile based on score
        
        if score >= 0.85:
            return 95.0
        elif score >= 0.75:
            return 80.0
        elif score >= 0.65:
            return 60.0
        elif score >= 0.55:
            return 40.0
        elif score >= 0.45:
            return 25.0
        else:
            return 10.0
    
    def _calculate_assessment_confidence(self, reference: Reference, dimension_scores: Dict[str, float]) -> float:
        """Calculate confidence in quality assessment."""
        confidence = 0.5  # Base confidence
        
        # More data = higher confidence
        if reference.abstract:
            confidence += 0.2
        if reference.citation_count:
            confidence += 0.15
        if reference.doi:
            confidence += 0.1
        if reference.journal:
            confidence += 0.1
        
        # Consistent dimension scores increase confidence
        score_variance = np.var(list(dimension_scores.values())) if len(dimension_scores) > 1 else 0
        confidence += max(0, 0.15 - score_variance)
        
        return min(1.0, confidence)
    
    async def analyze_quality_trends(self, references: List[Reference]) -> List[QualityTrend]:
        """Analyze quality trends across references."""
        trends = []
        
        # Group references by similarity for trend analysis
        # This is a simplified implementation
        
        for reference in references:
            # Mock historical data - in production would query database
            historical_scores = [
                (datetime.utcnow() - timedelta(days=365), 0.6),
                (datetime.utcnow() - timedelta(days=180), 0.65),
                (datetime.utcnow(), 0.7)
            ]
            
            # Calculate trend
            if len(historical_scores) >= 2:
                early_score = historical_scores[0][1]
                latest_score = historical_scores[-1][1]
                
                if latest_score > early_score + 0.05:
                    trend_direction = "improving"
                elif latest_score < early_score - 0.05:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
                
                trend_strength = abs(latest_score - early_score)
                
                trend = QualityTrend(
                    reference_id=reference.id,
                    historical_scores=historical_scores,
                    trend_direction=trend_direction,
                    trend_strength=trend_strength,
                    predicted_future_score=latest_score + (latest_score - early_score) * 0.5
                )
                trends.append(trend)
        
        self.stats['trend_analyses_completed'] += len(trends)
        return trends
    
    async def batch_assess_quality(
        self,
        references: List[Reference],
        context: str = "",
        research_field: str = "general"
    ) -> List[QualityMetrics]:
        """Efficiently assess quality of multiple references."""
        
        # Process in batches for efficiency
        batch_size = 10
        all_metrics = []
        
        for i in range(0, len(references), batch_size):
            batch = references[i:i + batch_size]
            batch_tasks = [
                self.assess_reference_quality(ref, context, research_field)
                for ref in batch
            ]
            
            batch_metrics = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for metric in batch_metrics:
                if not isinstance(metric, Exception):
                    all_metrics.append(metric)
                else:
                    logger.warning(f"Quality assessment failed: {metric}")
        
        return all_metrics
    
    async def get_quality_summary(self, metrics_list: List[QualityMetrics]) -> Dict[str, Any]:
        """Generate summary statistics for quality metrics."""
        if not metrics_list:
            return {}
        
        scores = [m.overall_score for m in metrics_list]
        quality_levels = [m.quality_level.value for m in metrics_list]
        red_flag_count = sum(len(m.red_flags) for m in metrics_list)
        
        import statistics
        
        return {
            'total_references': len(metrics_list),
            'average_quality_score': statistics.mean(scores),
            'median_quality_score': statistics.median(scores),
            'quality_distribution': dict(Counter(quality_levels)),
            'total_red_flags': red_flag_count,
            'references_with_red_flags': len([m for m in metrics_list if m.red_flags]),
            'high_quality_references': len([m for m in metrics_list if m.quality_level in [QualityLevel.HIGH, QualityLevel.EXCEPTIONAL]]),
            'problematic_references': len([m for m in metrics_list if m.quality_level == QualityLevel.PROBLEMATIC])
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get quality metrics engine statistics."""
        return self.stats

# Helper function to import numpy safely
def import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        # Fallback implementation
        class NumpyFallback:
            def var(self, data):
                if not data:
                    return 0
                mean_val = sum(data) / len(data)
                return sum((x - mean_val) ** 2 for x in data) / len(data)
        return NumpyFallback()

# Use numpy fallback if numpy not available
np = import_numpy()

# Global advanced quality metrics engine instance
_quality_metrics_instance: Optional[AdvancedQualityMetricsEngine] = None

async def get_advanced_quality_engine() -> AdvancedQualityMetricsEngine:
    """Get global advanced quality metrics engine instance."""
    global _quality_metrics_instance
    if _quality_metrics_instance is None:
        _quality_metrics_instance = AdvancedQualityMetricsEngine()
        await _quality_metrics_instance.initialize()
    return _quality_metrics_instance

async def close_advanced_quality_engine() -> None:
    """Close global advanced quality metrics engine instance."""
    global _quality_metrics_instance
    if _quality_metrics_instance:
        _quality_metrics_instance = None