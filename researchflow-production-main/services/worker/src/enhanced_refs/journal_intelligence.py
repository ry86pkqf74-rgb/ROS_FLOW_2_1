"""
Journal Intelligence System

Provides journal recommendations, impact analysis, and submission guidance
based on reference patterns and manuscript content.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from statistics import mean, median
from collections import Counter
import httpx

from .reference_types import Reference, QualityScore
from .api_management import get_api_manager, APIRequest, APIProvider
from .reference_cache import get_cache

logger = logging.getLogger(__name__)

class JournalIntelligence:
    """Advanced journal intelligence and recommendations."""
    
    # Journal impact factors and categories (would be loaded from external database)
    JOURNAL_DATABASE = {
        'nature': {
            'impact_factor': 49.962,
            'category': 'multidisciplinary',
            'acceptance_rate': 0.08,
            'review_time_weeks': 12,
            'open_access': False,
            'issn': '0028-0836'
        },
        'science': {
            'impact_factor': 47.728,
            'category': 'multidisciplinary', 
            'acceptance_rate': 0.07,
            'review_time_weeks': 10,
            'open_access': False,
            'issn': '0036-8075'
        },
        'new england journal of medicine': {
            'impact_factor': 91.245,
            'category': 'medicine',
            'acceptance_rate': 0.05,
            'review_time_weeks': 8,
            'open_access': False,
            'issn': '0028-4793'
        },
        'lancet': {
            'impact_factor': 79.321,
            'category': 'medicine',
            'acceptance_rate': 0.09,
            'review_time_weeks': 10,
            'open_access': False,
            'issn': '0140-6736'
        },
        'jama': {
            'impact_factor': 51.273,
            'category': 'medicine',
            'acceptance_rate': 0.08,
            'review_time_weeks': 12,
            'open_access': False,
            'issn': '0098-7484'
        },
        'plos one': {
            'impact_factor': 3.240,
            'category': 'multidisciplinary',
            'acceptance_rate': 0.69,
            'review_time_weeks': 4,
            'open_access': True,
            'issn': '1932-6203'
        }
    }
    
    def __init__(self):
        self.cache = None
        self.api_manager = None
        self.stats = {
            'recommendations_generated': 0,
            'impact_analyses_performed': 0,
            'journal_lookups': 0,
            'cache_hits': 0
        }
    
    async def initialize(self):
        """Initialize journal intelligence system."""
        self.cache = await get_cache()
        self.api_manager = await get_api_manager()
        logger.info("Journal intelligence system initialized")
    
    async def recommend_target_journals(
        self, 
        references: List[Reference], 
        manuscript_abstract: str = "",
        research_field: str = "general",
        target_impact_range: Tuple[float, float] = (1.0, 100.0),
        open_access_preference: bool = False
    ) -> List[Dict[str, any]]:
        """
        Recommend target journals based on reference patterns and manuscript content.
        
        Args:
            references: List of references in manuscript
            manuscript_abstract: Abstract text for topic analysis
            research_field: Primary research field
            target_impact_range: Desired impact factor range (min, max)
            open_access_preference: Prefer open access journals
            
        Returns:
            List of journal recommendations with scores
        """
        self.stats['recommendations_generated'] += 1
        
        # Cache key for recommendation
        cache_key = f"journal_rec_{hashlib.md5((str(len(references)) + manuscript_abstract[:100] + research_field).encode()).hexdigest()[:16]}"
        
        if self.cache:
            cached_result = await self.cache.get('api_responses', cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # Analyze reference patterns
        journal_analysis = await self._analyze_reference_journals(references)
        
        # Extract topics from abstract and references
        topics = await self._extract_topics(manuscript_abstract, references)
        
        # Find similar journals
        candidate_journals = await self._find_candidate_journals(
            journal_analysis, topics, research_field
        )
        
        # Score and rank journals
        recommendations = []
        for journal_name, journal_info in candidate_journals.items():
            score = await self._calculate_journal_score(
                journal_info,
                journal_analysis,
                target_impact_range,
                open_access_preference,
                topics
            )
            
            if score > 0.3:  # Minimum score threshold
                recommendations.append({
                    'journal_name': journal_name,
                    'impact_factor': journal_info.get('impact_factor'),
                    'compatibility_score': score,
                    'citation_frequency': journal_analysis['journal_counts'].get(journal_name.lower(), 0),
                    'acceptance_rate': journal_info.get('acceptance_rate'),
                    'review_time_weeks': journal_info.get('review_time_weeks'),
                    'open_access': journal_info.get('open_access', False),
                    'issn': journal_info.get('issn'),
                    'submission_guidelines': await self._get_submission_guidelines(journal_name),
                    'recent_similar_papers': await self._find_similar_papers(journal_name, topics),
                    'recommendation_reasons': await self._generate_recommendation_reasons(
                        journal_info, journal_analysis, score
                    )
                })
        
        # Sort by compatibility score
        recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
        recommendations = recommendations[:15]  # Top 15 recommendations
        
        # Cache results
        if self.cache:
            await self.cache.set('api_responses', cache_key, recommendations, ttl_override=6*3600)
        
        return recommendations
    
    async def analyze_citation_impact(self, references: List[Reference]) -> Dict[str, any]:
        """
        Analyze potential citation impact and research positioning.
        
        Args:
            references: List of references to analyze
            
        Returns:
            Comprehensive impact analysis
        """
        self.stats['impact_analyses_performed'] += 1
        
        if not references:
            return self._empty_impact_analysis()
        
        # Basic metrics
        total_citations = sum(ref.citation_count or 0 for ref in references)
        avg_citations = total_citations / len(references)
        median_citations = median([ref.citation_count or 0 for ref in references])
        
        # Impact distribution
        citation_counts = [ref.citation_count or 0 for ref in references]
        high_impact = [r for r in references if (r.citation_count or 0) >= 100]
        medium_impact = [r for r in references if 20 <= (r.citation_count or 0) < 100]
        low_impact = [r for r in references if (r.citation_count or 0) < 20]
        
        # Temporal analysis
        current_year = datetime.now().year
        recent_refs = [r for r in references if r.year and current_year - r.year <= 5]
        very_recent_refs = [r for r in references if r.year and current_year - r.year <= 2]
        
        # Journal diversity
        journals = [r.journal.lower() for r in references if r.journal]
        unique_journals = len(set(journals))
        journal_diversity = unique_journals / len(references) if references else 0
        
        # Field analysis
        field_analysis = await self._analyze_field_positioning(references)
        
        # H-index estimation
        h_index = await self._estimate_h_index_boost(references)
        
        # Research network analysis
        network_analysis = await self._analyze_research_network(references)
        
        # Impact prediction
        impact_prediction = await self._predict_citation_impact(references)
        
        return {
            'summary_metrics': {
                'total_references': len(references),
                'total_citations': total_citations,
                'average_citations': avg_citations,
                'median_citations': median_citations,
                'citation_range': {
                    'min': min(citation_counts) if citation_counts else 0,
                    'max': max(citation_counts) if citation_counts else 0
                }
            },
            'impact_distribution': {
                'high_impact_count': len(high_impact),
                'medium_impact_count': len(medium_impact),
                'low_impact_count': len(low_impact),
                'high_impact_percentage': len(high_impact) / len(references) * 100,
                'top_cited_references': [
                    {
                        'title': ref.title,
                        'citations': ref.citation_count,
                        'year': ref.year,
                        'journal': ref.journal
                    }
                    for ref in sorted(references, key=lambda x: x.citation_count or 0, reverse=True)[:5]
                ]
            },
            'temporal_analysis': {
                'recent_references': len(recent_refs),
                'very_recent_references': len(very_recent_refs),
                'recency_rate': len(recent_refs) / len(references) * 100,
                'average_age': mean([current_year - r.year for r in references if r.year]),
                'year_distribution': dict(Counter([r.year for r in references if r.year]))
            },
            'diversity_metrics': {
                'unique_journals': unique_journals,
                'journal_diversity_score': journal_diversity,
                'most_cited_journals': dict(Counter(journals).most_common(10)),
                'interdisciplinary_score': await self._calculate_interdisciplinary_score(references)
            },
            'field_positioning': field_analysis,
            'research_network': network_analysis,
            'predicted_impact': impact_prediction,
            'h_index_contribution': h_index,
            'recommendations': await self._generate_impact_recommendations(references, field_analysis)
        }
    
    async def analyze_journal_fit(
        self, 
        journal_name: str,
        references: List[Reference],
        manuscript_abstract: str = ""
    ) -> Dict[str, any]:
        """
        Analyze how well a manuscript fits a specific journal.
        
        Args:
            journal_name: Target journal name
            references: Manuscript references
            manuscript_abstract: Abstract text
            
        Returns:
            Journal fit analysis
        """
        journal_info = await self._get_journal_details(journal_name)
        
        # Reference alignment
        ref_alignment = await self._calculate_reference_alignment(journal_name, references)
        
        # Topic alignment
        journal_topics = await self._get_journal_topics(journal_name)
        manuscript_topics = await self._extract_topics(manuscript_abstract, references)
        topic_alignment = await self._calculate_topic_alignment(journal_topics, manuscript_topics)
        
        # Citation pattern analysis
        citation_analysis = await self._analyze_journal_citation_patterns(journal_name, references)
        
        # Overall fit score
        fit_score = (ref_alignment * 0.4 + topic_alignment * 0.4 + citation_analysis * 0.2)
        
        return {
            'journal_name': journal_name,
            'overall_fit_score': fit_score,
            'fit_level': self._categorize_fit_score(fit_score),
            'journal_info': journal_info,
            'reference_alignment': {
                'score': ref_alignment,
                'common_journals': await self._find_common_reference_journals(journal_name, references),
                'reference_overlap_rate': await self._calculate_reference_overlap(journal_name, references)
            },
            'topic_alignment': {
                'score': topic_alignment,
                'matching_topics': set(journal_topics).intersection(set(manuscript_topics)),
                'topic_coverage': len(set(journal_topics).intersection(set(manuscript_topics))) / len(manuscript_topics) if manuscript_topics else 0
            },
            'citation_patterns': citation_analysis,
            'submission_recommendation': await self._generate_submission_recommendation(fit_score, journal_info),
            'improvement_suggestions': await self._suggest_manuscript_improvements(journal_name, references, manuscript_abstract)
        }
    
    async def _analyze_reference_journals(self, references: List[Reference]) -> Dict[str, any]:
        """Analyze journal patterns in references."""
        journals = [ref.journal.lower() for ref in references if ref.journal]
        journal_counts = Counter(journals)
        
        # Get impact factors for cited journals
        journal_impacts = {}
        for journal in set(journals):
            impact = await self._get_journal_impact_factor(journal)
            if impact:
                journal_impacts[journal] = impact
        
        return {
            'journal_counts': dict(journal_counts),
            'most_common_journals': journal_counts.most_common(10),
            'unique_journals': len(set(journals)),
            'journal_impacts': journal_impacts,
            'avg_impact_factor': mean(journal_impacts.values()) if journal_impacts else 0,
            'total_references': len(references)
        }
    
    async def _extract_topics(self, abstract: str, references: List[Reference]) -> List[str]:
        """Extract research topics from abstract and references."""
        topics = set()
        
        # Extract from abstract
        if abstract:
            abstract_topics = await self._extract_topics_from_text(abstract)
            topics.update(abstract_topics)
        
        # Extract from reference titles and keywords
        for ref in references:
            if ref.title:
                title_topics = await self._extract_topics_from_text(ref.title)
                topics.update(title_topics)
            
            if ref.keywords:
                topics.update([k.lower().strip() for k in ref.keywords])
        
        return list(topics)[:20]  # Top 20 topics
    
    async def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract topics from text using keyword extraction."""
        # Simple keyword extraction (in production, would use NLP libraries)
        
        # Common research terms
        medical_terms = [
            'treatment', 'therapy', 'diagnosis', 'patient', 'clinical', 'trial', 
            'outcome', 'efficacy', 'safety', 'intervention', 'randomized', 'study',
            'analysis', 'association', 'risk', 'prevalence', 'incidence', 'mortality',
            'morbidity', 'disease', 'syndrome', 'disorder', 'condition'
        ]
        
        research_methods = [
            'meta-analysis', 'systematic review', 'cohort', 'case-control', 'cross-sectional',
            'longitudinal', 'retrospective', 'prospective', 'observational', 'experimental',
            'survey', 'interview', 'questionnaire', 'statistical', 'regression', 'correlation'
        ]
        
        text_lower = text.lower()
        found_topics = []
        
        # Find medical terms
        for term in medical_terms:
            if term in text_lower:
                found_topics.append(term)
        
        # Find research methods
        for method in research_methods:
            if method in text_lower:
                found_topics.append(method)
        
        # Extract noun phrases (simplified)
        import re
        phrases = re.findall(r'\b[a-z]{3,}\s+[a-z]{3,}\b', text_lower)
        found_topics.extend(phrases[:5])  # Top 5 phrases
        
        return list(set(found_topics))[:10]  # Top 10 unique topics
    
    async def _find_candidate_journals(
        self, 
        journal_analysis: Dict[str, any], 
        topics: List[str], 
        research_field: str
    ) -> Dict[str, Dict[str, any]]:
        """Find candidate journals based on analysis."""
        candidates = {}
        
        # Add journals from our database that match field/topics
        for journal_name, journal_info in self.JOURNAL_DATABASE.items():
            # Check field match
            if research_field.lower() in ['medicine', 'medical', 'clinical'] and journal_info['category'] == 'medicine':
                candidates[journal_name] = journal_info
            elif journal_info['category'] == 'multidisciplinary':
                candidates[journal_name] = journal_info
        
        # Add highly cited journals from references
        for journal, count in journal_analysis['most_common_journals'][:5]:
            if journal not in candidates:
                journal_details = await self._get_journal_details(journal)
                if journal_details:
                    candidates[journal] = journal_details
        
        return candidates
    
    async def _calculate_journal_score(
        self,
        journal_info: Dict[str, any],
        journal_analysis: Dict[str, any], 
        target_impact_range: Tuple[float, float],
        open_access_preference: bool,
        topics: List[str]
    ) -> float:
        """Calculate compatibility score for a journal."""
        score = 0.0
        
        # Citation frequency in references
        journal_name = journal_info.get('journal_name', '').lower()
        citation_freq = journal_analysis['journal_counts'].get(journal_name, 0)
        total_refs = journal_analysis['total_references']
        citation_score = min(citation_freq / total_refs * 5, 1.0) if total_refs > 0 else 0
        score += citation_score * 0.3
        
        # Impact factor alignment
        impact_factor = journal_info.get('impact_factor', 0)
        min_impact, max_impact = target_impact_range
        if min_impact <= impact_factor <= max_impact:
            impact_score = 1.0
        elif impact_factor > max_impact:
            impact_score = 0.8  # High impact is good but may be too competitive
        else:
            impact_score = 0.4  # Below range
        score += impact_score * 0.25
        
        # Open access preference
        if open_access_preference and journal_info.get('open_access', False):
            score += 0.15
        elif not open_access_preference and not journal_info.get('open_access', False):
            score += 0.05
        
        # Acceptance rate (higher is better for submission success)
        acceptance_rate = journal_info.get('acceptance_rate', 0.5)
        acceptance_score = min(acceptance_rate * 2, 1.0)
        score += acceptance_score * 0.2
        
        # Review time (shorter is better)
        review_weeks = journal_info.get('review_time_weeks', 12)
        review_score = max(1.0 - (review_weeks - 4) / 20, 0.2)  # 4-week baseline
        score += review_score * 0.1
        
        return min(score, 1.0)
    
    async def _get_journal_details(self, journal_name: str) -> Optional[Dict[str, any]]:
        """Retrieve detailed journal information."""
        journal_lower = journal_name.lower().strip()
        
        # Check our database first
        if journal_lower in self.JOURNAL_DATABASE:
            return {**self.JOURNAL_DATABASE[journal_lower], 'journal_name': journal_name}
        
        # Check cache
        cache_key = f"journal_details_{journal_lower.replace(' ', '_')}"
        if self.cache:
            cached = await self.cache.get('api_responses', cache_key)
            if cached:
                self.stats['cache_hits'] += 1
                return cached
        
        self.stats['journal_lookups'] += 1
        
        # Default journal info with reasonable estimates
        journal_details = {
            'journal_name': journal_name,
            'impact_factor': 3.0,  # Average impact factor
            'category': 'unknown',
            'acceptance_rate': 0.3,  # Average acceptance rate
            'review_time_weeks': 10,  # Average review time
            'open_access': False,
            'issn': None,
            'publisher': 'Unknown'
        }
        
        # Cache for 7 days
        if self.cache:
            await self.cache.set('api_responses', cache_key, journal_details, ttl_override=7*24*3600)
        
        return journal_details
    
    async def _get_journal_impact_factor(self, journal_name: str) -> Optional[float]:
        """Get impact factor for a journal."""
        journal_details = await self._get_journal_details(journal_name)
        return journal_details.get('impact_factor') if journal_details else None
    
    async def _estimate_h_index_boost(self, references: List[Reference]) -> Dict[str, any]:
        """Estimate potential h-index contribution from references."""
        citation_counts = sorted([r.citation_count or 0 for r in references], reverse=True)
        
        # Calculate current h-index of reference set
        h_index = 0
        for i, citations in enumerate(citation_counts):
            if citations >= (i + 1):
                h_index = i + 1
            else:
                break
        
        # Estimate future impact based on reference quality
        high_quality_refs = len([r for r in references if (r.citation_count or 0) >= 50])
        recent_refs = len([r for r in references if r.year and datetime.now().year - r.year <= 3])
        
        estimated_boost = high_quality_refs * 0.1 + recent_refs * 0.05
        predicted_h_index = h_index + estimated_boost
        
        return {
            'current_h_index': h_index,
            'predicted_h_index': predicted_h_index,
            'estimated_boost': estimated_boost,
            'high_quality_references': high_quality_refs,
            'recent_references': recent_refs
        }
    
    async def _analyze_field_positioning(self, references: List[Reference]) -> Dict[str, any]:
        """Analyze how references position the work within the field."""
        
        # Analyze reference types
        type_counts = Counter([ref.reference_type.value for ref in references])
        
        # Analyze publication venues
        journal_counts = Counter([ref.journal.lower() for ref in references if ref.journal])
        
        # Analyze temporal distribution
        year_counts = Counter([ref.year for ref in references if ref.year])
        current_year = datetime.now().year
        recent_rate = len([r for r in references if r.year and current_year - r.year <= 5]) / len(references)
        
        # Classify theoretical vs empirical
        theoretical_empirical = await self._classify_theoretical_empirical(references)
        
        return {
            'reference_type_distribution': dict(type_counts),
            'top_venues': dict(journal_counts.most_common(10)),
            'temporal_distribution': dict(year_counts),
            'interdisciplinary_score': len(set(r.journal for r in references if r.journal)) / len(references),
            'recent_literature_rate': recent_rate,
            'theoretical_vs_empirical': theoretical_empirical,
            'field_breadth_score': await self._calculate_field_breadth(references)
        }
    
    async def _classify_theoretical_empirical(self, references: List[Reference]) -> Dict[str, float]:
        """Classify references as theoretical vs empirical."""
        theoretical_keywords = ['theory', 'model', 'framework', 'concept', 'review', 'paradigm']
        empirical_keywords = ['study', 'trial', 'experiment', 'data', 'analysis', 'results', 'findings']
        
        theoretical_count = 0
        empirical_count = 0
        mixed_count = 0
        
        for ref in references:
            title_abstract = f"{ref.title or ''} {ref.abstract or ''}".lower()
            
            has_theoretical = any(keyword in title_abstract for keyword in theoretical_keywords)
            has_empirical = any(keyword in title_abstract for keyword in empirical_keywords)
            
            if has_theoretical and has_empirical:
                mixed_count += 1
            elif has_theoretical:
                theoretical_count += 1
            elif has_empirical:
                empirical_count += 1
        
        total = len(references)
        return {
            'theoretical_ratio': theoretical_count / total if total > 0 else 0,
            'empirical_ratio': empirical_count / total if total > 0 else 0,
            'mixed_ratio': mixed_count / total if total > 0 else 0,
            'unclassified_ratio': (total - theoretical_count - empirical_count - mixed_count) / total if total > 0 else 0
        }
    
    async def _calculate_field_breadth(self, references: List[Reference]) -> float:
        """Calculate how broad the field coverage is."""
        # Simple breadth calculation based on journal diversity
        journals = set(r.journal.lower() for r in references if r.journal)
        # Normalize by log to avoid over-penalizing focused studies
        import math
        breadth_score = min(math.log(len(journals) + 1) / 3, 1.0)
        return breadth_score
    
    async def _analyze_research_network(self, references: List[Reference]) -> Dict[str, any]:
        """Analyze research network characteristics."""
        # Author collaboration analysis
        all_authors = []
        for ref in references:
            if ref.authors:
                all_authors.extend([author.lower().strip() for author in ref.authors])
        
        author_counts = Counter(all_authors)
        frequent_authors = [author for author, count in author_counts.items() if count > 1]
        
        # Journal network
        journals = [ref.journal.lower() for ref in references if ref.journal]
        journal_network = Counter(journals)
        
        return {
            'total_unique_authors': len(set(all_authors)),
            'frequently_cited_authors': dict(author_counts.most_common(10)),
            'author_collaboration_rate': len(frequent_authors) / len(set(all_authors)) if all_authors else 0,
            'journal_network_density': len(set(journals)) / len(journals) if journals else 0,
            'core_journals': dict(journal_network.most_common(5))
        }
    
    async def _predict_citation_impact(self, references: List[Reference]) -> Dict[str, any]:
        """Predict potential citation impact."""
        if not references:
            return {'predicted_citations': 0, 'confidence': 0}
        
        # Simple prediction based on reference quality
        high_impact_refs = len([r for r in references if (r.citation_count or 0) >= 100])
        medium_impact_refs = len([r for r in references if 20 <= (r.citation_count or 0) < 100])
        recent_refs = len([r for r in references if r.year and datetime.now().year - r.year <= 3])
        
        # Basic prediction model
        predicted_base = len(references) * 2  # Base 2 citations per reference
        quality_boost = high_impact_refs * 5 + medium_impact_refs * 2
        recency_boost = recent_refs * 1.5
        
        predicted_citations = predicted_base + quality_boost + recency_boost
        
        # Confidence based on reference quality
        total_citations = sum(r.citation_count or 0 for r in references)
        confidence = min(total_citations / (len(references) * 50), 1.0)  # Normalize by avg 50 cites
        
        return {
            'predicted_citations': int(predicted_citations),
            'confidence_score': confidence,
            'factors': {
                'base_prediction': predicted_base,
                'quality_boost': quality_boost,
                'recency_boost': recency_boost
            },
            'prediction_range': {
                'low': int(predicted_citations * 0.7),
                'high': int(predicted_citations * 1.5)
            }
        }
    
    async def _generate_impact_recommendations(self, references: List[Reference], field_analysis: Dict[str, any]) -> List[str]:
        """Generate recommendations for improving citation impact."""
        recommendations = []
        
        # Check recency
        recent_rate = field_analysis.get('recent_literature_rate', 0)
        if recent_rate < 0.4:
            recommendations.append("Include more recent literature (last 5 years) to increase relevance")
        
        # Check diversity
        interdisciplinary_score = field_analysis.get('interdisciplinary_score', 0)
        if interdisciplinary_score < 0.3:
            recommendations.append("Consider citing papers from related disciplines to broaden impact")
        
        # Check high-impact sources
        high_impact_count = len([r for r in references if (r.citation_count or 0) >= 100])
        if high_impact_count < len(references) * 0.2:
            recommendations.append("Include more high-impact references to strengthen credibility")
        
        # Check theoretical balance
        theoretical_ratio = field_analysis.get('theoretical_vs_empirical', {}).get('theoretical_ratio', 0)
        empirical_ratio = field_analysis.get('theoretical_vs_empirical', {}).get('empirical_ratio', 0)
        
        if theoretical_ratio > 0.7:
            recommendations.append("Consider adding empirical studies to balance theoretical foundation")
        elif empirical_ratio > 0.8:
            recommendations.append("Consider adding theoretical papers to strengthen conceptual framework")
        
        return recommendations
    
    def _empty_impact_analysis(self) -> Dict[str, any]:
        """Return empty impact analysis structure."""
        return {
            'summary_metrics': {
                'total_references': 0,
                'total_citations': 0,
                'average_citations': 0,
                'median_citations': 0
            },
            'impact_distribution': {},
            'temporal_analysis': {},
            'diversity_metrics': {},
            'field_positioning': {},
            'research_network': {},
            'predicted_impact': {'predicted_citations': 0, 'confidence': 0},
            'h_index_contribution': {'current_h_index': 0, 'predicted_h_index': 0},
            'recommendations': ["No references available for analysis"]
        }
    
    async def get_stats(self) -> Dict[str, any]:
        """Get journal intelligence statistics."""
        return self.stats


# Global journal intelligence instance
_journal_intelligence_instance: Optional[JournalIntelligence] = None


async def get_journal_intelligence() -> JournalIntelligence:
    """Get global journal intelligence instance."""
    global _journal_intelligence_instance
    if _journal_intelligence_instance is None:
        _journal_intelligence_instance = JournalIntelligence()
        await _journal_intelligence_instance.initialize()
    return _journal_intelligence_instance


async def close_journal_intelligence() -> None:
    """Close global journal intelligence instance."""
    global _journal_intelligence_instance
    if _journal_intelligence_instance:
        _journal_intelligence_instance = None