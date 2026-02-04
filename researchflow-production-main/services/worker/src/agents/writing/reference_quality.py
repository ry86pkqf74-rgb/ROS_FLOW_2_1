"""
Reference Quality Assessment and Analytics

AI-powered assessment of reference quality, relevance, and provides
analytics for reference strategy optimization.

Linear Issues: ROS-XXX
"""

import re
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import asyncio
from statistics import mean, median

from .reference_types import (
    Reference, QualityScore, QualityWarning, QualityLevel,
    CitationNeed, ReferenceAnalytics
)
from .reference_cache import get_cache

logger = logging.getLogger(__name__)


class ReferenceQualityAssessor:
    """AI-powered assessment of reference quality and relevance."""
    
    # Known predatory journals (would be updated from external sources)
    PREDATORY_JOURNALS = {
        'international journal of advanced research',
        'global journal of research',
        'american journal of modern science',
        # This would be a much larger list from external databases
    }
    
    # High-impact journals by field
    HIGH_IMPACT_JOURNALS = {
        'medical': {
            'new england journal of medicine', 'lancet', 'jama',
            'british medical journal', 'annals of internal medicine'
        },
        'general': {
            'nature', 'science', 'cell', 'proceedings of the national academy of sciences'
        }
    }
    
    # Citation count percentiles by field (rough estimates)
    CITATION_PERCENTILES = {
        'medical': {'50th': 10, '75th': 25, '90th': 50, '95th': 100},
        'biology': {'50th': 15, '75th': 35, '90th': 70, '95th': 150},
        'general': {'50th': 8, '75th': 20, '90th': 40, '95th': 80},
    }
    
    def __init__(self):
        """Initialize quality assessor."""
        self.cache = None
        self.stats = {
            'assessments_performed': 0,
            'excellent_quality': 0,
            'good_quality': 0,
            'acceptable_quality': 0,
            'poor_quality': 0,
            'problematic_quality': 0,
            'warnings_generated': 0,
        }
    
    async def initialize(self) -> None:
        """Initialize dependencies."""
        self.cache = await get_cache()
    
    async def assess_reference_quality(
        self, 
        reference: Reference, 
        manuscript_context: str = "",
        research_field: str = "general"
    ) -> QualityScore:
        """
        Score reference on multiple quality dimensions.
        
        Args:
            reference: Reference to assess
            manuscript_context: Manuscript context for relevance scoring
            research_field: Research field for field-specific assessment
            
        Returns:
            Quality score with detailed breakdown
        """
        if not self.cache:
            await self.initialize()
        
        self.stats['assessments_performed'] += 1
        
        # Check cache first
        cache_key = f"{reference.id}_{hash(manuscript_context)}"
        if self.cache:
            cached_score = await self.cache.get('quality_scores', cache_key, 'quality_score')
            if cached_score:
                return cached_score
        
        # Calculate individual dimension scores
        credibility_score = await self._assess_credibility(reference, research_field)
        recency_score = self._assess_recency(reference)
        relevance_score = await self._assess_relevance(reference, manuscript_context)
        impact_score = self._assess_impact(reference, research_field)
        methodology_score = await self._assess_methodology(reference)
        
        # Calculate overall score (weighted average)
        weights = {
            'credibility': 0.3,
            'recency': 0.2,
            'relevance': 0.25,
            'impact': 0.15,
            'methodology': 0.1
        }
        
        overall_score = (
            credibility_score * weights['credibility'] +
            recency_score * weights['recency'] +
            relevance_score * weights['relevance'] +
            impact_score * weights['impact'] +
            methodology_score * weights['methodology']
        )
        
        # Determine quality level
        quality_level = self._determine_quality_level(overall_score)
        
        # Generate strengths, weaknesses, and recommendations
        strengths, weaknesses, recommendations = self._generate_feedback(
            reference, credibility_score, recency_score, relevance_score, 
            impact_score, methodology_score, quality_level
        )
        
        # Create quality score
        quality_score = QualityScore(
            reference_id=reference.id,
            overall_score=overall_score,
            quality_level=quality_level,
            credibility_score=credibility_score,
            recency_score=recency_score,
            relevance_score=relevance_score,
            impact_score=impact_score,
            methodology_score=methodology_score,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
        
        # Cache result
        if self.cache:
            await self.cache.set('quality_scores', cache_key, quality_score)
        
        # Update stats
        self.stats[f"{quality_level.value}_quality"] += 1
        
        return quality_score
    
    async def _assess_credibility(self, reference: Reference, research_field: str) -> float:
        """Assess source credibility."""
        score = 0.5  # Base score
        
        # Check if journal is known predatory
        if reference.journal:
            journal_lower = reference.journal.lower()
            if any(pred in journal_lower for pred in self.PREDATORY_JOURNALS):
                score -= 0.4  # Significant penalty
            
            # Check if high-impact journal
            high_impact_journals = self.HIGH_IMPACT_JOURNALS.get(research_field, set()) | self.HIGH_IMPACT_JOURNALS.get('general', set())
            if any(journal in journal_lower for journal in high_impact_journals):
                score += 0.3
        
        # Check retraction status
        if reference.is_retracted:
            score = 0.0  # Retracted papers get zero credibility
        
        # Preprint handling
        if reference.is_preprint:
            score *= 0.8  # Moderate penalty for preprints
        
        # DOI presence indicates formal publication
        if reference.doi:
            score += 0.1
        
        # Complete metadata indicates reliable source
        metadata_completeness = self._calculate_metadata_completeness(reference)
        score += metadata_completeness * 0.2
        
        return min(1.0, max(0.0, score))
    
    def _assess_recency(self, reference: Reference) -> float:
        """Assess publication recency relevance."""
        if not reference.year:
            return 0.3  # Unknown year gets low score
        
        current_year = datetime.now().year
        age = current_year - reference.year
        
        # Recency scoring based on field norms
        if age <= 2:
            return 1.0  # Very recent
        elif age <= 5:
            return 0.8  # Recent
        elif age <= 10:
            return 0.6  # Moderately recent
        elif age <= 15:
            return 0.4  # Older but potentially valuable
        elif age <= 25:
            return 0.2  # Old but may be foundational
        else:
            return 0.1  # Very old
    
    async def _assess_relevance(self, reference: Reference, manuscript_context: str) -> float:
        """Assess topic relevance to manuscript."""
        if not manuscript_context:
            return 0.5  # No context to assess relevance
        
        # Extract key terms from manuscript context
        manuscript_terms = self._extract_key_terms(manuscript_context.lower())
        
        # Extract key terms from reference
        ref_text = f"{reference.title or ''} {reference.abstract or ''} {' '.join(reference.keywords)}".lower()
        ref_terms = self._extract_key_terms(ref_text)
        
        if not manuscript_terms or not ref_terms:
            return 0.5
        
        # Calculate term overlap
        common_terms = manuscript_terms.intersection(ref_terms)
        relevance = len(common_terms) / max(len(manuscript_terms), len(ref_terms))
        
        # Boost score if reference type matches typical citation patterns
        if reference.reference_type.value in ['journal_article', 'review']:
            relevance += 0.1
        
        return min(1.0, relevance)
    
    def _assess_impact(self, reference: Reference, research_field: str) -> float:
        """Assess citation impact and importance."""
        score = 0.5  # Base score
        
        # Citation count assessment
        if reference.citation_count is not None:
            percentiles = self.CITATION_PERCENTILES.get(research_field, self.CITATION_PERCENTILES['general'])
            
            if reference.citation_count >= percentiles['95th']:
                score = 1.0
            elif reference.citation_count >= percentiles['90th']:
                score = 0.9
            elif reference.citation_count >= percentiles['75th']:
                score = 0.8
            elif reference.citation_count >= percentiles['50th']:
                score = 0.7
            else:
                score = 0.6
        
        # Journal impact factor (if available)
        if reference.impact_factor:
            if reference.impact_factor >= 10:
                score += 0.2
            elif reference.impact_factor >= 5:
                score += 0.1
            elif reference.impact_factor >= 2:
                score += 0.05
        
        return min(1.0, score)
    
    async def _assess_methodology(self, reference: Reference) -> float:
        """Assess methodological rigor (simplified)."""
        score = 0.5  # Base score
        
        # Check title and abstract for methodology keywords
        text = f"{reference.title or ''} {reference.abstract or ''}".lower()
        
        # Positive methodology indicators
        positive_indicators = [
            'randomized', 'controlled', 'systematic review', 'meta-analysis',
            'double-blind', 'placebo', 'prospective', 'cohort', 'multicenter'
        ]
        
        # Negative methodology indicators
        negative_indicators = [
            'case report', 'editorial', 'opinion', 'commentary',
            'letter to editor', 'correspondence'
        ]
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in text)
        negative_count = sum(1 for indicator in negative_indicators if indicator in text)
        
        score += positive_count * 0.1
        score -= negative_count * 0.2
        
        # Reference type bonus
        if reference.reference_type.value in ['journal_article']:
            score += 0.1
        elif reference.reference_type.value in ['book', 'book_chapter']:
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """Determine quality level from overall score."""
        if overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif overall_score >= 0.75:
            return QualityLevel.GOOD
        elif overall_score >= 0.6:
            return QualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.PROBLEMATIC
    
    def _generate_feedback(
        self, 
        reference: Reference,
        credibility: float, 
        recency: float, 
        relevance: float,
        impact: float, 
        methodology: float,
        quality_level: QualityLevel
    ) -> tuple[List[str], List[str], List[str]]:
        """Generate strengths, weaknesses, and recommendations."""
        strengths = []
        weaknesses = []
        recommendations = []
        
        # Strengths
        if credibility >= 0.8:
            strengths.append("Published in reputable source")
        if recency >= 0.8:
            strengths.append("Recent publication")
        if relevance >= 0.8:
            strengths.append("Highly relevant to manuscript topic")
        if impact >= 0.8:
            strengths.append("High citation impact")
        if methodology >= 0.8:
            strengths.append("Strong methodological approach")
        if reference.doi:
            strengths.append("Formally published with DOI")
        
        # Weaknesses
        if credibility <= 0.4:
            weaknesses.append("Source credibility concerns")
        if recency <= 0.3:
            weaknesses.append("Outdated publication")
        if relevance <= 0.4:
            weaknesses.append("Limited relevance to topic")
        if impact <= 0.3:
            weaknesses.append("Low citation impact")
        if methodology <= 0.4:
            weaknesses.append("Methodological limitations")
        if reference.is_retracted:
            weaknesses.append("Retracted publication")
        
        # Recommendations
        if quality_level == QualityLevel.PROBLEMATIC:
            recommendations.append("Consider replacing with higher quality source")
        if recency <= 0.4 and not any("foundational" in s.lower() for s in strengths):
            recommendations.append("Consider more recent literature")
        if relevance <= 0.5:
            recommendations.append("Verify relevance to manuscript claims")
        if reference.is_preprint:
            recommendations.append("Check if peer-reviewed version available")
        if not reference.doi and not reference.pmid:
            recommendations.append("Verify citation details and formal publication")
        
        return strengths, weaknesses, recommendations
    
    def _calculate_metadata_completeness(self, reference: Reference) -> float:
        """Calculate metadata completeness score."""
        required_fields = ['title', 'authors', 'year']
        optional_fields = ['journal', 'volume', 'issue', 'pages', 'doi', 'abstract']
        
        required_present = sum(1 for field in required_fields if getattr(reference, field))
        optional_present = sum(1 for field in optional_fields if getattr(reference, field))
        
        required_score = required_present / len(required_fields)
        optional_score = optional_present / len(optional_fields)
        
        return 0.7 * required_score + 0.3 * optional_score
    
    def _extract_key_terms(self, text: str) -> Set[str]:
        """Extract key terms from text (simplified)."""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'were', 'will', 'with', 'the', 'this', 'these',
            'they', 'their', 'there', 'than', 'then', 'them', 'we', 'would'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        meaningful_terms = {word for word in words if word not in stop_words}
        
        return meaningful_terms
    
    async def flag_problematic_references(self, references: List[Reference]) -> List[QualityWarning]:
        """Identify potentially problematic references."""
        warnings = []
        
        for reference in references:
            ref_warnings = await self._check_reference_issues(reference)
            warnings.extend(ref_warnings)
        
        self.stats['warnings_generated'] += len(warnings)
        return warnings
    
    async def _check_reference_issues(self, reference: Reference) -> List[QualityWarning]:
        """Check for issues with a single reference."""
        warnings = []
        
        # Retracted paper
        if reference.is_retracted:
            warnings.append(QualityWarning(
                reference_id=reference.id,
                warning_type="retracted_paper",
                severity="critical",
                message="This paper has been retracted",
                recommendation="Remove or replace with alternative source",
                auto_fixable=False
            ))
        
        # Predatory journal
        if reference.journal:
            journal_lower = reference.journal.lower()
            if any(pred in journal_lower for pred in self.PREDATORY_JOURNALS):
                warnings.append(QualityWarning(
                    reference_id=reference.id,
                    warning_type="predatory_journal",
                    severity="high",
                    message="Journal may be predatory",
                    recommendation="Verify journal reputation and consider alternative sources",
                    auto_fixable=False
                ))
        
        # Very old reference
        if reference.year and datetime.now().year - reference.year > 25:
            warnings.append(QualityWarning(
                reference_id=reference.id,
                warning_type="very_old",
                severity="medium",
                message=f"Reference is {datetime.now().year - reference.year} years old",
                recommendation="Consider if more recent literature is available",
                auto_fixable=False
            ))
        
        # Preprint misuse (if preprint is very old)
        if reference.is_preprint and reference.year and datetime.now().year - reference.year > 2:
            warnings.append(QualityWarning(
                reference_id=reference.id,
                warning_type="preprint_misuse",
                severity="medium",
                message="Old preprint may have been published in peer-reviewed journal",
                recommendation="Check if peer-reviewed version is available",
                auto_fixable=False
            ))
        
        # Incomplete metadata
        completeness = self._calculate_metadata_completeness(reference)
        if completeness < 0.5:
            warnings.append(QualityWarning(
                reference_id=reference.id,
                warning_type="incomplete_metadata",
                severity="low",
                message="Reference has incomplete metadata",
                recommendation="Complete missing fields (authors, title, publication details)",
                auto_fixable=True
            ))
        
        # Broken URL
        if reference.url and not await self._check_url_validity(reference.url):
            warnings.append(QualityWarning(
                reference_id=reference.id,
                warning_type="broken_link",
                severity="low",
                message="URL appears to be broken",
                recommendation="Update or remove broken URL",
                auto_fixable=True
            ))
        
        return warnings
    
    async def _check_url_validity(self, url: str) -> bool:
        """Check if URL is valid (simplified check)."""
        # In production, this would make HTTP HEAD requests
        # For now, just basic format check
        return url.startswith(('http://', 'https://')) and '.' in url
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get quality assessment statistics."""
        total = self.stats['assessments_performed']
        return {
            **self.stats,
            'quality_distribution': {
                level: self.stats[f"{level}_quality"] / total if total > 0 else 0
                for level in ['excellent', 'good', 'acceptable', 'poor', 'problematic']
            }
        }


class ReferenceAnalytics:
    """Advanced analytics for reference strategy optimization."""
    
    def __init__(self):
        """Initialize analytics."""
        self.cache = None
    
    async def initialize(self) -> None:
        """Initialize dependencies."""
        self.cache = await get_cache()
    
    async def analyze_citation_patterns(self, references: List[Reference], manuscript_text: str = "") -> ReferenceAnalytics:
        """
        Analyze citation patterns for insights.
        
        Args:
            references: List of references to analyze
            manuscript_text: Manuscript text for section analysis
            
        Returns:
            Detailed analytics report
        """
        if not self.cache:
            await self.initialize()
        
        if not references:
            return ReferenceAnalytics(study_id="unknown")
        
        # Basic statistics
        total_refs = len(references)
        unique_journals = len(set(ref.journal for ref in references if ref.journal))
        
        # Year analysis
        years = [ref.year for ref in references if ref.year]
        year_range = (min(years), max(years)) if years else (0, 0)
        
        # Distribution analysis
        refs_by_year = self._count_by_field(references, 'year')
        refs_by_journal = self._count_by_field(references, 'journal', top_n=10)
        refs_by_type = self._count_by_field(references, 'reference_type')
        
        # Section analysis (if manuscript text provided)
        refs_by_section = {}
        if manuscript_text:
            refs_by_section = self._analyze_citations_by_section(manuscript_text)
        
        # Quality metrics
        impact_factors = [ref.impact_factor for ref in references if ref.impact_factor]
        avg_impact_factor = mean(impact_factors) if impact_factors else 0.0
        
        citation_counts = [ref.citation_count for ref in references if ref.citation_count]
        avg_citation_count = mean(citation_counts) if citation_counts else 0.0
        
        # Pattern analysis
        self_citation_rate = self._calculate_self_citation_rate(references)
        recent_refs_rate = self._calculate_recent_references_rate(references)
        preprint_rate = len([r for r in references if r.is_preprint]) / total_refs
        
        return ReferenceAnalytics(
            study_id=f"analysis_{int(datetime.utcnow().timestamp())}",
            total_references=total_refs,
            unique_journals=unique_journals,
            year_range=year_range,
            references_by_year=refs_by_year,
            references_by_journal=refs_by_journal,
            references_by_type=refs_by_type,
            references_by_section=refs_by_section,
            average_impact_factor=avg_impact_factor,
            average_citation_count=avg_citation_count,
            self_citation_rate=self_citation_rate,
            recent_references_rate=recent_refs_rate,
            preprint_rate=preprint_rate
        )
    
    def _count_by_field(self, references: List[Reference], field: str, top_n: Optional[int] = None) -> Dict[str, int]:
        """Count references by field value."""
        counts = {}
        for ref in references:
            value = getattr(ref, field)
            if value:
                key = str(value)
                counts[key] = counts.get(key, 0) + 1
        
        if top_n:
            # Return top N most common
            sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_items[:top_n])
        
        return counts
    
    def _analyze_citations_by_section(self, manuscript_text: str) -> Dict[str, int]:
        """Analyze citation distribution by manuscript section."""
        sections = {
            'introduction': 0,
            'methods': 0,
            'results': 0,
            'discussion': 0,
            'conclusion': 0
        }
        
        # This is simplified - would need more sophisticated section detection
        text_lower = manuscript_text.lower()
        
        # Count citation markers in each section (very simplified)
        for section in sections:
            if section in text_lower:
                # Count citations in section (looking for [1], [2], etc.)
                section_start = text_lower.find(section)
                if section_start != -1:
                    # Look ahead 2000 characters for citations
                    section_text = text_lower[section_start:section_start+2000]
                    citations = re.findall(r'\[\d+\]', section_text)
                    sections[section] = len(citations)
        
        return sections
    
    def _calculate_self_citation_rate(self, references: List[Reference]) -> float:
        """Calculate self-citation rate (simplified)."""
        # This would require author matching against manuscript authors
        # For now, return placeholder
        return 0.1  # 10% placeholder
    
    def _calculate_recent_references_rate(self, references: List[Reference]) -> float:
        """Calculate rate of recent references (last 5 years)."""
        current_year = datetime.now().year
        recent_refs = [r for r in references if r.year and current_year - r.year <= 5]
        return len(recent_refs) / len(references) if references else 0.0