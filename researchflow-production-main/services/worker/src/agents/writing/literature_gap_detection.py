"""
Literature Gap Detection Engine

AI-powered system to identify missing key references in manuscripts
by analyzing citation patterns, research domains, and knowledge gaps.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import re

from .reference_types import Reference, CitationNeed
from .semantic_similarity import get_semantic_similarity_engine, SemanticMatch
from .reference_cache import get_cache
from .api_management import get_api_manager

logger = logging.getLogger(__name__)

@dataclass
class LiteratureGap:
    """Represents an identified literature gap."""
    gap_id: str
    gap_type: str  # missing_foundational, missing_recent, missing_methodology, missing_domain
    description: str
    importance_score: float
    context: str
    section_suggestion: str
    suggested_search_terms: List[str]
    existing_references_related: List[str]
    confidence: float
    evidence: List[str]
    urgency: str  # low, medium, high, critical

@dataclass
class CitationAnalysis:
    """Analysis of citation patterns and coverage."""
    total_references: int
    temporal_distribution: Dict[int, int]
    domain_coverage: Dict[str, int]
    methodology_coverage: Dict[str, int]
    citation_density: float
    foundational_works_ratio: float
    recent_works_ratio: float
    diversity_score: float
    completeness_score: float

class LiteratureGapDetectionEngine:
    """
    Advanced literature gap detection system.
    
    Analyzes manuscripts to identify:
    - Missing foundational references in the field
    - Lack of recent literature (recency gaps)
    - Missing methodological references
    - Domain-specific knowledge gaps
    - Insufficient citation density for claims
    - Missing comparative studies
    """
    
    # Knowledge base of important works by domain (would be loaded from database)
    FOUNDATIONAL_WORKS = {
        'machine_learning': [
            {'title': 'Deep Learning', 'authors': ['Goodfellow', 'Bengio', 'Courville'], 'year': 2016},
            {'title': 'Pattern Recognition and Machine Learning', 'authors': ['Bishop'], 'year': 2006},
            {'title': 'The Elements of Statistical Learning', 'authors': ['Hastie', 'Tibshirani', 'Friedman'], 'year': 2009}
        ],
        'medical_research': [
            {'title': 'Principles and Practice of Clinical Research', 'authors': ['Gallin', 'Ognibene'], 'year': 2018},
            {'title': 'Clinical Epidemiology: The Essentials', 'authors': ['Fletcher', 'Fletcher'], 'year': 2019},
            {'title': 'Randomised Controlled Trials', 'authors': ['Pocock'], 'year': 2013}
        ],
        'statistics': [
            {'title': 'Statistical Inference', 'authors': ['Casella', 'Berger'], 'year': 2002},
            {'title': 'An Introduction to Statistical Learning', 'authors': ['James', 'Witten', 'Hastie', 'Tibshirani'], 'year': 2021},
            {'title': 'Bayesian Data Analysis', 'authors': ['Gelman', 'Carlin', 'Stern', 'Rubin'], 'year': 2013}
        ]
    }
    
    METHODOLOGY_INDICATORS = {
        'randomized_controlled_trial': ['randomized', 'controlled trial', 'rct', 'placebo', 'blind'],
        'meta_analysis': ['meta-analysis', 'systematic review', 'pooled analysis', 'forest plot'],
        'cohort_study': ['cohort', 'longitudinal', 'prospective', 'follow-up'],
        'case_control': ['case-control', 'retrospective', 'odds ratio'],
        'cross_sectional': ['cross-sectional', 'survey', 'prevalence'],
        'machine_learning': ['machine learning', 'deep learning', 'neural network', 'algorithm', 'model'],
        'statistical_analysis': ['regression', 'anova', 'statistical', 't-test', 'chi-square', 'correlation']
    }
    
    def __init__(self):
        self.cache = None
        self.api_manager = None
        self.semantic_engine = None
        self.stats = {
            'gaps_detected': 0,
            'manuscripts_analyzed': 0,
            'gap_types_found': defaultdict(int),
            'avg_gaps_per_manuscript': 0.0
        }
    
    async def initialize(self):
        """Initialize the literature gap detection engine."""
        self.cache = await get_cache()
        self.api_manager = await get_api_manager()
        self.semantic_engine = await get_semantic_similarity_engine()
        logger.info("Literature gap detection engine initialized")
    
    async def detect_literature_gaps(
        self,
        manuscript_text: str,
        references: List[Reference],
        research_field: str = "general",
        manuscript_type: str = "research_article"
    ) -> List[LiteratureGap]:
        """
        Detect literature gaps in a manuscript.
        
        Args:
            manuscript_text: Full manuscript text
            references: Current references
            research_field: Primary research field
            manuscript_type: Type of manuscript (research_article, review, etc.)
            
        Returns:
            List of identified literature gaps
        """
        self.stats['manuscripts_analyzed'] += 1
        
        # Analyze current citation landscape
        citation_analysis = await self._analyze_citation_patterns(manuscript_text, references)
        
        # Detect different types of gaps
        gaps = []
        
        # 1. Missing foundational works
        foundational_gaps = await self._detect_foundational_gaps(references, research_field)
        gaps.extend(foundational_gaps)
        
        # 2. Missing recent literature
        recency_gaps = await self._detect_recency_gaps(manuscript_text, references, research_field)
        gaps.extend(recency_gaps)
        
        # 3. Missing methodological references
        methodology_gaps = await self._detect_methodology_gaps(manuscript_text, references)
        gaps.extend(methodology_gaps)
        
        # 4. Domain-specific gaps
        domain_gaps = await self._detect_domain_gaps(manuscript_text, references, research_field)
        gaps.extend(domain_gaps)
        
        # 5. Citation density gaps
        density_gaps = await self._detect_citation_density_gaps(manuscript_text, references)
        gaps.extend(density_gaps)
        
        # 6. Comparative study gaps
        comparative_gaps = await self._detect_comparative_gaps(manuscript_text, references)
        gaps.extend(comparative_gaps)
        
        # Score and prioritize gaps
        prioritized_gaps = await self._prioritize_gaps(gaps, citation_analysis, manuscript_type)
        
        self.stats['gaps_detected'] += len(prioritized_gaps)
        self.stats['avg_gaps_per_manuscript'] = self.stats['gaps_detected'] / self.stats['manuscripts_analyzed']
        
        for gap in prioritized_gaps:
            self.stats['gap_types_found'][gap.gap_type] += 1
        
        return prioritized_gaps
    
    async def _analyze_citation_patterns(self, manuscript_text: str, references: List[Reference]) -> CitationAnalysis:
        """Analyze citation patterns and coverage."""
        
        # Temporal distribution
        years = [ref.year for ref in references if ref.year]
        temporal_dist = Counter(years)
        
        # Domain coverage (simplified)
        domains = []
        for ref in references:
            if ref.journal:
                domain = await self._classify_journal_domain(ref.journal)
                domains.append(domain)
        domain_coverage = Counter(domains)
        
        # Methodology coverage
        methodologies = []
        for ref in references:
            ref_text = f"{ref.title} {ref.abstract or ''}".lower()
            for method, indicators in self.METHODOLOGY_INDICATORS.items():
                if any(indicator in ref_text for indicator in indicators):
                    methodologies.append(method)
        methodology_coverage = Counter(methodologies)
        
        # Citation density (citations per 1000 words)
        word_count = len(manuscript_text.split())
        citation_density = (len(references) / word_count) * 1000 if word_count > 0 else 0
        
        # Recent works ratio (last 5 years)
        current_year = datetime.now().year
        recent_refs = [ref for ref in references if ref.year and current_year - ref.year <= 5]
        recent_ratio = len(recent_refs) / len(references) if references else 0
        
        # Foundational works ratio (older than 10 years but highly cited)
        foundational_refs = [
            ref for ref in references 
            if ref.year and current_year - ref.year > 10 and (ref.citation_count or 0) > 100
        ]
        foundational_ratio = len(foundational_refs) / len(references) if references else 0
        
        # Diversity score (unique journals / total references)
        unique_journals = len(set(ref.journal for ref in references if ref.journal))
        diversity_score = unique_journals / len(references) if references else 0
        
        # Completeness score (based on metadata completeness)
        complete_refs = [
            ref for ref in references 
            if all([ref.title, ref.authors, ref.year, ref.journal])
        ]
        completeness_score = len(complete_refs) / len(references) if references else 0
        
        return CitationAnalysis(
            total_references=len(references),
            temporal_distribution=dict(temporal_dist),
            domain_coverage=dict(domain_coverage),
            methodology_coverage=dict(methodology_coverage),
            citation_density=citation_density,
            foundational_works_ratio=foundational_ratio,
            recent_works_ratio=recent_ratio,
            diversity_score=diversity_score,
            completeness_score=completeness_score
        )
    
    async def _detect_foundational_gaps(self, references: List[Reference], research_field: str) -> List[LiteratureGap]:
        """Detect missing foundational works in the field."""
        gaps = []
        
        # Get foundational works for the field
        foundational_works = self.FOUNDATIONAL_WORKS.get(research_field, [])
        
        # Check which foundational works are missing
        ref_titles_lower = [ref.title.lower() for ref in references if ref.title]
        ref_authors_lower = [
            author.lower() for ref in references if ref.authors 
            for author in ref.authors
        ]
        
        for work in foundational_works:
            work_title = work['title'].lower()
            work_authors = [author.lower() for author in work['authors']]
            
            # Check if work is already cited (fuzzy matching)
            is_cited = False
            
            # Title similarity check
            for ref_title in ref_titles_lower:
                if self._calculate_title_similarity(work_title, ref_title) > 0.8:
                    is_cited = True
                    break
            
            # Author check
            if not is_cited:
                for work_author in work_authors:
                    if any(work_author in ref_author for ref_author in ref_authors_lower):
                        # Found author, check if from similar time period
                        matching_refs = [
                            ref for ref in references 
                            if ref.authors and any(work_author in author.lower() for author in ref.authors)
                            and ref.year and abs(ref.year - work['year']) <= 3
                        ]
                        if matching_refs:
                            is_cited = True
                            break
            
            if not is_cited:
                gap = LiteratureGap(
                    gap_id=f"foundational_{hashlib.md5(work_title.encode()).hexdigest()[:8]}",
                    gap_type="missing_foundational",
                    description=f"Missing foundational work: '{work['title']}' by {', '.join(work['authors'])} ({work['year']})",
                    importance_score=0.9,  # High importance for foundational works
                    context=f"This is a seminal work in {research_field} that provides theoretical foundation",
                    section_suggestion="Introduction or Literature Review",
                    suggested_search_terms=[work['title']] + work['authors'],
                    existing_references_related=[],
                    confidence=0.85,
                    evidence=[f"Foundational work in {research_field}", f"Published in {work['year']}"],
                    urgency="high"
                )
                gaps.append(gap)
        
        return gaps
    
    async def _detect_recency_gaps(self, manuscript_text: str, references: List[Reference], research_field: str) -> List[LiteratureGap]:
        """Detect lack of recent literature."""
        gaps = []
        
        current_year = datetime.now().year
        recent_refs = [ref for ref in references if ref.year and current_year - ref.year <= 3]
        very_recent_refs = [ref for ref in references if ref.year and current_year - ref.year <= 1]
        
        total_refs = len(references)
        recent_ratio = len(recent_refs) / total_refs if total_refs > 0 else 0
        very_recent_ratio = len(very_recent_refs) / total_refs if total_refs > 0 else 0
        
        # Detect recency gaps
        if recent_ratio < 0.2:  # Less than 20% recent literature
            gap = LiteratureGap(
                gap_id=f"recency_general_{current_year}",
                gap_type="missing_recent",
                description="Insufficient recent literature (last 3 years)",
                importance_score=0.7,
                context="Recent developments and findings may not be adequately covered",
                section_suggestion="Introduction, Results, or Discussion",
                suggested_search_terms=[research_field, "recent", str(current_year-1), str(current_year)],
                existing_references_related=[ref.id for ref in recent_refs],
                confidence=0.8,
                evidence=[
                    f"Only {recent_ratio:.1%} of references are from last 3 years",
                    f"Field likely has recent developments not covered"
                ],
                urgency="medium" if recent_ratio > 0.1 else "high"
            )
            gaps.append(gap)
        
        if very_recent_ratio < 0.05 and total_refs > 20:  # Less than 5% very recent
            gap = LiteratureGap(
                gap_id=f"recency_current_{current_year}",
                gap_type="missing_recent",
                description="Missing very recent literature (last year)",
                importance_score=0.6,
                context="Latest findings and developments may be missing",
                section_suggestion="Introduction or Discussion",
                suggested_search_terms=[research_field, str(current_year), "latest", "recent"],
                existing_references_related=[ref.id for ref in very_recent_refs],
                confidence=0.7,
                evidence=[
                    f"Only {very_recent_ratio:.1%} of references are from last year",
                    "May miss cutting-edge developments"
                ],
                urgency="low"
            )
            gaps.append(gap)
        
        return gaps
    
    async def _detect_methodology_gaps(self, manuscript_text: str, references: List[Reference]) -> List[LiteratureGap]:
        """Detect missing methodological references."""
        gaps = []
        
        manuscript_lower = manuscript_text.lower()
        
        # Find methodologies mentioned in manuscript
        mentioned_methods = []
        for method, indicators in self.METHODOLOGY_INDICATORS.items():
            if any(indicator in manuscript_lower for indicator in indicators):
                mentioned_methods.append(method)
        
        # Check if methods are supported by appropriate references
        for method in mentioned_methods:
            method_refs = []
            for ref in references:
                ref_text = f"{ref.title} {ref.abstract or ''}".lower()
                indicators = self.METHODOLOGY_INDICATORS[method]
                if any(indicator in ref_text for indicator in indicators):
                    method_refs.append(ref)
            
            # Determine if methodology is under-referenced
            method_mentions = sum(
                manuscript_lower.count(indicator) 
                for indicator in self.METHODOLOGY_INDICATORS[method]
            )
            
            if method_mentions > 2 and len(method_refs) == 0:
                # Method mentioned but no supporting references
                gap = LiteratureGap(
                    gap_id=f"methodology_{method}",
                    gap_type="missing_methodology",
                    description=f"Missing methodological references for {method.replace('_', ' ')}",
                    importance_score=0.8,
                    context=f"Manuscript mentions {method.replace('_', ' ')} but lacks supporting methodological references",
                    section_suggestion="Methods or Introduction",
                    suggested_search_terms=[method.replace('_', ' ')] + self.METHODOLOGY_INDICATORS[method][:3],
                    existing_references_related=[],
                    confidence=0.85,
                    evidence=[
                        f"Method mentioned {method_mentions} times in manuscript",
                        "No supporting methodological references found"
                    ],
                    urgency="high"
                )
                gaps.append(gap)
            
            elif method_mentions > 5 and len(method_refs) < 2:
                # Method heavily used but under-referenced
                gap = LiteratureGap(
                    gap_id=f"methodology_under_{method}",
                    gap_type="missing_methodology", 
                    description=f"Insufficient methodological references for {method.replace('_', ' ')}",
                    importance_score=0.6,
                    context=f"Method is central to work but may need more supporting references",
                    section_suggestion="Methods",
                    suggested_search_terms=[method.replace('_', ' ')] + self.METHODOLOGY_INDICATORS[method][:2],
                    existing_references_related=[ref.id for ref in method_refs],
                    confidence=0.7,
                    evidence=[
                        f"Method mentioned {method_mentions} times",
                        f"Only {len(method_refs)} supporting references found"
                    ],
                    urgency="medium"
                )
                gaps.append(gap)
        
        return gaps
    
    async def _detect_domain_gaps(self, manuscript_text: str, references: List[Reference], research_field: str) -> List[LiteratureGap]:
        """Detect domain-specific knowledge gaps."""
        gaps = []
        
        # Extract domain-specific terms from manuscript
        domain_terms = await self._extract_domain_terms(manuscript_text, research_field)
        
        # Check coverage of each domain term
        for term in domain_terms:
            supporting_refs = []
            for ref in references:
                ref_text = f"{ref.title} {ref.abstract or ''}".lower()
                if term.lower() in ref_text:
                    supporting_refs.append(ref)
            
            # Count mentions in manuscript
            term_mentions = manuscript_text.lower().count(term.lower())
            
            if term_mentions > 3 and len(supporting_refs) == 0:
                gap = LiteratureGap(
                    gap_id=f"domain_{hashlib.md5(term.encode()).hexdigest()[:8]}",
                    gap_type="missing_domain",
                    description=f"Missing references for domain concept: {term}",
                    importance_score=0.6,
                    context=f"Concept '{term}' is discussed but lacks supporting literature",
                    section_suggestion="Introduction or Literature Review",
                    suggested_search_terms=[term, research_field],
                    existing_references_related=[],
                    confidence=0.7,
                    evidence=[
                        f"Term '{term}' mentioned {term_mentions} times",
                        "No supporting references found for this concept"
                    ],
                    urgency="medium"
                )
                gaps.append(gap)
        
        return gaps
    
    async def _detect_citation_density_gaps(self, manuscript_text: str, references: List[Reference]) -> List[LiteratureGap]:
        """Detect sections with insufficient citation density."""
        gaps = []
        
        # Split manuscript into sections
        sections = self._split_into_sections(manuscript_text)
        
        for section_name, section_text in sections.items():
            if len(section_text.split()) < 200:  # Skip short sections
                continue
            
            # Count citations in section
            citation_count = len(re.findall(r'\[\d+\]|\(\d+\)', section_text))
            word_count = len(section_text.split())
            density = (citation_count / word_count) * 1000  # citations per 1000 words
            
            # Section-specific density thresholds
            thresholds = {
                'introduction': 15,
                'literature_review': 25,
                'methods': 8,
                'results': 5,
                'discussion': 12,
                'conclusion': 3
            }
            
            threshold = thresholds.get(section_name.lower(), 10)
            
            if density < threshold:
                gap = LiteratureGap(
                    gap_id=f"density_{section_name}",
                    gap_type="missing_citation_density",
                    description=f"Low citation density in {section_name} section",
                    importance_score=0.5,
                    context=f"Section may need more supporting references (current: {density:.1f}/1000 words)",
                    section_suggestion=section_name,
                    suggested_search_terms=[],
                    existing_references_related=[],
                    confidence=0.6,
                    evidence=[
                        f"Citation density: {density:.1f}/1000 words (threshold: {threshold})",
                        f"Section length: {word_count} words"
                    ],
                    urgency="low"
                )
                gaps.append(gap)
        
        return gaps
    
    async def _detect_comparative_gaps(self, manuscript_text: str, references: List[Reference]) -> List[LiteratureGap]:
        """Detect missing comparative studies or alternative approaches."""
        gaps = []
        
        manuscript_lower = manuscript_text.lower()
        
        # Look for claims that need comparative support
        comparative_indicators = [
            'better than', 'superior to', 'outperforms', 'compared to',
            'versus', 'alternative to', 'state-of-the-art', 'best'
        ]
        
        comparative_claims = []
        for indicator in comparative_indicators:
            if indicator in manuscript_lower:
                comparative_claims.append(indicator)
        
        if comparative_claims:
            # Check if there are sufficient comparative references
            comparative_refs = []
            for ref in references:
                ref_text = f"{ref.title} {ref.abstract or ''}".lower()
                if any(indicator in ref_text for indicator in ['comparison', 'comparative', 'versus', 'vs']):
                    comparative_refs.append(ref)
            
            claims_count = len(comparative_claims)
            refs_count = len(comparative_refs)
            
            if claims_count > 2 and refs_count < 2:
                gap = LiteratureGap(
                    gap_id="comparative_studies",
                    gap_type="missing_comparative",
                    description="Missing comparative studies to support comparative claims",
                    importance_score=0.7,
                    context="Manuscript makes comparative claims but lacks sufficient comparative literature",
                    section_suggestion="Literature Review or Results",
                    suggested_search_terms=["comparative study", "comparison", "versus"],
                    existing_references_related=[ref.id for ref in comparative_refs],
                    confidence=0.75,
                    evidence=[
                        f"Found {claims_count} comparative claims",
                        f"Only {refs_count} comparative references"
                    ],
                    urgency="medium"
                )
                gaps.append(gap)
        
        return gaps
    
    async def _prioritize_gaps(self, gaps: List[LiteratureGap], analysis: CitationAnalysis, manuscript_type: str) -> List[LiteratureGap]:
        """Prioritize identified gaps based on importance and context."""
        
        # Adjust importance scores based on manuscript type
        type_multipliers = {
            'research_article': {'missing_foundational': 1.0, 'missing_methodology': 1.2, 'missing_recent': 1.1},
            'review_article': {'missing_foundational': 1.3, 'missing_recent': 1.3, 'missing_comparative': 1.2},
            'case_study': {'missing_methodology': 0.8, 'missing_comparative': 1.1}
        }
        
        multipliers = type_multipliers.get(manuscript_type, {})
        
        for gap in gaps:
            # Apply type-specific multiplier
            multiplier = multipliers.get(gap.gap_type, 1.0)
            gap.importance_score *= multiplier
            
            # Adjust based on overall citation analysis
            if analysis.completeness_score < 0.5:
                gap.importance_score *= 1.1  # Boost if overall quality is low
            
            if analysis.diversity_score < 0.3:
                if gap.gap_type == 'missing_domain':
                    gap.importance_score *= 1.2  # Boost domain gaps if diversity is low
        
        # Sort by importance score and return top gaps
        gaps.sort(key=lambda x: x.importance_score, reverse=True)
        return gaps[:15]  # Return top 15 gaps
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def _classify_journal_domain(self, journal_name: str) -> str:
        """Classify journal domain (simplified)."""
        journal_lower = journal_name.lower()
        
        domains = {
            'medical': ['medicine', 'medical', 'clinical', 'health', 'bmj', 'lancet', 'nejm'],
            'engineering': ['engineering', 'ieee', 'acm'],
            'biology': ['biology', 'nature', 'science', 'cell', 'molecular'],
            'computer_science': ['computer', 'artificial', 'machine learning', 'ieee'],
            'psychology': ['psychology', 'behavioral', 'cognitive'],
            'physics': ['physics', 'physical', 'quantum']
        }
        
        for domain, keywords in domains.items():
            if any(keyword in journal_lower for keyword in keywords):
                return domain
        
        return 'general'
    
    async def _extract_domain_terms(self, text: str, research_field: str) -> List[str]:
        """Extract domain-specific terms from text."""
        
        # Domain-specific term dictionaries (simplified)
        domain_terms = {
            'medical_research': [
                'intervention', 'treatment', 'therapy', 'diagnosis', 'prognosis',
                'biomarker', 'clinical trial', 'patient outcome', 'adverse event',
                'efficacy', 'safety', 'protocol', 'randomization'
            ],
            'machine_learning': [
                'algorithm', 'neural network', 'deep learning', 'supervised learning',
                'unsupervised learning', 'feature extraction', 'model training',
                'cross-validation', 'overfitting', 'hyperparameter'
            ],
            'statistics': [
                'hypothesis testing', 'p-value', 'confidence interval', 'regression',
                'correlation', 'variance', 'standard deviation', 'statistical significance'
            ]
        }
        
        field_terms = domain_terms.get(research_field, [])
        text_lower = text.lower()
        
        found_terms = []
        for term in field_terms:
            if term in text_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Split manuscript into sections."""
        
        # Common section headers
        section_patterns = {
            'abstract': r'\babstract\b',
            'introduction': r'\bintroduction\b',
            'literature_review': r'\bliterature review\b|\brelated work\b',
            'methods': r'\bmethods?\b|\bmethodology\b',
            'results': r'\bresults?\b|\bfindings?\b',
            'discussion': r'\bdiscussion\b',
            'conclusion': r'\bconclusion\b|\bconcluding remarks\b'
        }
        
        sections = {}
        text_lower = text.lower()
        
        # Find section boundaries
        section_starts = {}
        for section_name, pattern in section_patterns.items():
            matches = list(re.finditer(pattern, text_lower))
            if matches:
                section_starts[section_name] = matches[0].start()
        
        # Sort sections by position
        sorted_sections = sorted(section_starts.items(), key=lambda x: x[1])
        
        # Extract section content
        for i, (section_name, start_pos) in enumerate(sorted_sections):
            if i + 1 < len(sorted_sections):
                end_pos = sorted_sections[i + 1][1]
            else:
                end_pos = len(text)
            
            section_content = text[start_pos:end_pos]
            sections[section_name] = section_content
        
        return sections
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get literature gap detection statistics."""
        return {
            **self.stats,
            'gap_type_distribution': dict(self.stats['gap_types_found'])
        }

# Global literature gap detection engine instance
_gap_detection_instance: Optional[LiteratureGapDetectionEngine] = None

async def get_literature_gap_engine() -> LiteratureGapDetectionEngine:
    """Get global literature gap detection engine instance."""
    global _gap_detection_instance
    if _gap_detection_instance is None:
        _gap_detection_instance = LiteratureGapDetectionEngine()
        await _gap_detection_instance.initialize()
    return _gap_detection_instance

async def close_literature_gap_engine() -> None:
    """Close global literature gap detection engine instance."""
    global _gap_detection_instance
    if _gap_detection_instance:
        _gap_detection_instance = None