"""
Reference Management Service

Centralized service for comprehensive reference management including
citation extraction, DOI validation, duplicate detection, quality assessment,
and bibliography generation.

Linear Issues: ROS-XXX
"""

import re
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import asyncio
import time

from .reference_types import (
    ReferenceState, ReferenceResult, Reference, Citation, CitationStyle,
    QualityScore, QualityWarning, CitationNeed, DuplicateGroup,
    ReferenceAnalytics
)
from .reference_cache import get_cache
from .api_management import get_api_manager
from .doi_validator import DOIValidator
from .duplicate_detector import PaperDeduplicator
from .reference_quality import ReferenceQualityAssessor, ReferenceAnalytics as Analytics
from ..analysis.citation_formatters import CitationFormatterFactory
from .ai_enhanced_matching import get_ai_matcher

logger = logging.getLogger(__name__)


class ReferenceManagementService:
    """
    Centralized reference management service for comprehensive citation handling.
    
    This service orchestrates all reference management functionality including:
    - Citation extraction from manuscript text
    - Reference matching with literature search results
    - DOI validation and metadata enrichment
    - Duplicate detection and merging
    - Quality assessment and warnings
    - Citation formatting in multiple styles
    - Bibliography generation
    """
    
    # Citation patterns for extraction
    CITATION_PATTERNS = [
        r'\[(\d+(?:[-,]\d+)*)\]',  # [1], [1-3], [1,2,3]
        r'\((\d+(?:[-,]\d+)*)\)',  # (1), (1-3), (1,2,3)
        r'\[\s*citation\s+needed\s*\]',  # [citation needed]
        r'\[\s*CITATION\s+NEEDED\s*\]',  # [CITATION NEEDED]
    ]
    
    def __init__(self):
        """Initialize reference management service."""
        self.cache = None
        self.api_manager = None
        self.doi_validator = DOIValidator()
        self.deduplicator = PaperDeduplicator()
        self.quality_assessor = ReferenceQualityAssessor()
        self.analytics = Analytics()
        self.formatter_factory = CitationFormatterFactory()
        self.ai_matcher = None
        
        self.stats = {
            'processings_performed': 0,
            'citations_extracted': 0,
            'references_matched': 0,
            'dois_validated': 0,
            'duplicates_found': 0,
            'quality_assessments': 0,
            'bibliographies_generated': 0,
            'processing_time_total': 0.0,
        }
    
    async def initialize(self) -> None:
        """Initialize all service dependencies."""
        self.cache = await get_cache()
        self.api_manager = await get_api_manager()
        await self.doi_validator.initialize()
        await self.deduplicator.initialize()
        await self.quality_assessor.initialize()
        await self.analytics.initialize()
        self.ai_matcher = await get_ai_matcher()
        
        logger.info("Reference management service initialized")
    
    async def process_references(self, state: ReferenceState) -> ReferenceResult:
        """
        Main reference processing workflow.
        
        Args:
            state: Reference processing state
            
        Returns:
            Comprehensive reference processing result
        """
        start_time = time.time()
        
        if not self.cache:
            await self.initialize()
        
        self.stats['processings_performed'] += 1
        
        logger.info(f"Processing references for study: {state.study_id}")
        
        try:
            # 1. Extract citations from manuscript text
            citation_needs = await self.extract_citations(state.manuscript_text)
            logger.info(f"Extracted {len(citation_needs)} citation needs")
            
            # 2. Match citations to literature results and existing references
            references = await self.match_to_literature(
                citation_needs, state.literature_results, state.existing_references
            )
            logger.info(f"Matched to {len(references)} references")
            
            # 3. Fetch missing metadata via DOI validation
            if state.enable_doi_validation:
                references = await self.fetch_missing_metadata(references)
                logger.info("Completed DOI validation and metadata enrichment")
            
            # 4. Check for duplicates
            duplicate_groups = []
            if state.enable_duplicate_detection:
                references, duplicate_groups = await self.check_duplicates(references)
                logger.info(f"Found {len(duplicate_groups)} duplicate groups")
            
            # 5. Apply reference limit if specified
            if state.max_references and len(references) > state.max_references:
                references = await self.prioritize_references(references, state.max_references)
                logger.info(f"Limited to {len(references)} references")
            
            # 6. Format citations
            citations = await self.format_references(references, state.target_style)
            logger.info(f"Formatted {len(citations)} citations")
            
            # 7. Quality assessment
            quality_scores = []
            warnings = []
            if state.enable_quality_assessment:
                quality_scores = await self.assess_quality(references, state.manuscript_text, state.research_field or "general")
                warnings = await self.quality_assessor.flag_problematic_references(references)
                logger.info(f"Generated {len(quality_scores)} quality scores and {len(warnings)} warnings")
            
            # 8. Generate bibliography
            bibliography = await self.generate_bibliography(citations, state.target_style)
            logger.info("Generated bibliography")
            
            # 9. Create citation map
            citation_map = self.create_citation_map(citation_needs, citations)
            
            # 10. Calculate processing metrics
            processing_time = time.time() - start_time
            self.stats['processing_time_total'] += processing_time
            
            # 11. Calculate style compliance score
            style_compliance_score = await self.calculate_style_compliance(citations, state.target_style)
            
            # 12. Create result
            result = ReferenceResult(
                study_id=state.study_id,
                references=references,
                citations=citations,
                bibliography=bibliography,
                citation_map=citation_map,
                quality_scores=quality_scores,
                warnings=warnings,
                total_references=len(references),
                style_compliance_score=style_compliance_score,
                missing_citations=[need.text_snippet for need in citation_needs if not need.suggested_references],
                duplicate_references=[group.group_id for group in duplicate_groups],
                doi_verified={ref.id: bool(ref.doi) for ref in references},
                processing_time_seconds=processing_time,
                api_calls_made=self.api_manager.stats.get('requests_made', 0) if self.api_manager else 0,
                cache_hits=self.cache.stats.get('hits', 0) if self.cache else 0,
                cache_misses=self.cache.stats.get('misses', 0) if self.cache else 0,
            )
            
            logger.info(f"Reference processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Reference processing failed: {e}", exc_info=True)
            # Return partial result on error
            return ReferenceResult(
                study_id=state.study_id,
                processing_time_seconds=time.time() - start_time,
            )
    
    async def extract_citations(self, manuscript_text: str) -> List[CitationNeed]:
        """
        Extract citation needs from manuscript text.
        
        Args:
            manuscript_text: Full manuscript text
            
        Returns:
            List of identified citation needs
        """
        citation_needs = []
        
        # Find explicit citation markers
        for pattern in self.CITATION_PATTERNS:
            for match in re.finditer(pattern, manuscript_text, re.IGNORECASE):
                citation_need = CitationNeed(
                    id=f"citation_{len(citation_needs)}_{match.start()}",
                    text_snippet=match.group(),
                    context=self._extract_context(manuscript_text, match.start(), match.end()),
                    position=match.start(),
                    section=self._identify_section(manuscript_text, match.start()),
                    claim_type=self._classify_claim_type(
                        self._extract_context(manuscript_text, match.start(), match.end())
                    )
                )
                citation_needs.append(citation_need)
        
        # Find implicit citation needs (claims without citations)
        implicit_needs = await self._find_implicit_citation_needs(manuscript_text)
        citation_needs.extend(implicit_needs)
        
        self.stats['citations_extracted'] += len(citation_needs)
        return citation_needs
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 200) -> str:
        """Extract context around citation."""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        return text[context_start:context_end]
    
    def _identify_section(self, text: str, position: int) -> str:
        """Identify which section of manuscript contains the citation."""
        text_before = text[:position].lower()
        
        # Look for section headers
        section_markers = {
            'introduction': ['introduction', 'background'],
            'methods': ['methods', 'methodology', 'materials and methods'],
            'results': ['results', 'findings'],
            'discussion': ['discussion', 'interpretation'],
            'conclusion': ['conclusion', 'conclusions'],
        }
        
        current_section = 'unknown'
        last_section_pos = -1
        
        for section, markers in section_markers.items():
            for marker in markers:
                marker_pos = text_before.rfind(marker)
                if marker_pos > last_section_pos:
                    current_section = section
                    last_section_pos = marker_pos
        
        return current_section
    
    def _classify_claim_type(self, context: str) -> str:
        """Classify the type of claim needing citation."""
        context_lower = context.lower()
        
        # Statistical indicators
        if any(indicator in context_lower for indicator in ['%', 'percent', 'odds ratio', 'p =', 'p<', 'p>']):
            return 'statistical_fact'
        
        # Prior research indicators
        if any(indicator in context_lower for indicator in ['study', 'research', 'found', 'showed', 'demonstrated']):
            return 'prior_research'
        
        # Methodology indicators
        if any(indicator in context_lower for indicator in ['method', 'procedure', 'technique', 'approach']):
            return 'methodology'
        
        # Clinical guideline indicators
        if any(indicator in context_lower for indicator in ['guideline', 'recommendation', 'standard', 'protocol']):
            return 'clinical_guideline'
        
        # Definition indicators
        if any(indicator in context_lower for indicator in ['defined as', 'is defined', 'definition']):
            return 'definition'
        
        return 'background_info'
    
    async def _find_implicit_citation_needs(self, text: str) -> List[CitationNeed]:
        """Find claims that need citations but don't have them."""
        needs = []
        
        # Patterns that typically need citations
        citation_needed_patterns = [
            r'studies have shown',
            r'research indicates',
            r'evidence suggests',
            r'it has been demonstrated',
            r'previous work has established',
            r'\d+% of (?:patients|subjects|participants)',
            r'according to (?:recent )?(?:studies|research)',
        ]
        
        for pattern in citation_needed_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Check if there's already a citation nearby
                context_window = 100
                context_start = max(0, match.start() - context_window)
                context_end = min(len(text), match.end() + context_window)
                context = text[context_start:context_end]
                
                # Skip if citation already present
                if any(re.search(p, context) for p in self.CITATION_PATTERNS):
                    continue
                
                need = CitationNeed(
                    id=f"implicit_{len(needs)}_{match.start()}",
                    text_snippet=match.group(),
                    context=self._extract_context(text, match.start(), match.end()),
                    position=match.start(),
                    section=self._identify_section(text, match.start()),
                    claim_type=self._classify_claim_type(context),
                    urgency='high'  # Implicit needs are high priority
                )
                needs.append(need)
        
        return needs
    
    async def match_to_literature(
        self, 
        citation_needs: List[CitationNeed],
        literature_results: List[Dict[str, Any]],
        existing_references: List[Reference]
    ) -> List[Reference]:
        """
        Match citations to literature search results and existing references.
        
        Args:
            citation_needs: Identified citation needs
            literature_results: Results from literature search
            existing_references: Pre-existing references
            
        Returns:
            List of matched references
        """
        references = existing_references.copy()
        
        # Convert literature results to Reference objects
        for lit_result in literature_results:
            try:
                reference = self._convert_literature_result_to_reference(lit_result)
                references.append(reference)
            except Exception as e:
                logger.warning(f"Failed to convert literature result: {e}")
        
        # Match citation needs to references using relevance scoring
        for need in citation_needs:
            matching_refs = await self._find_matching_references(need, references)
            need.suggested_references = [ref.id for ref in matching_refs[:3]]  # Top 3 matches
        
        self.stats['references_matched'] += len(references)
        return references
    
    def _convert_literature_result_to_reference(self, lit_result: Dict[str, Any]) -> Reference:
        """Convert literature search result to Reference object."""
        return Reference(
            id=lit_result.get('id', f"lit_{hash(str(lit_result))}"),
            title=lit_result.get('title', ''),
            authors=lit_result.get('authors', []),
            year=lit_result.get('year'),
            journal=lit_result.get('journal'),
            doi=lit_result.get('doi'),
            pmid=lit_result.get('pmid'),
            url=lit_result.get('url'),
            abstract=lit_result.get('abstract'),
            source_database=lit_result.get('source', 'literature_search')
        )
    
    async def _find_matching_references(self, need: CitationNeed, references: List[Reference]) -> List[Reference]:
        """Find references that match a citation need using AI-enhanced matching."""
        if self.ai_matcher:
            # Use AI-enhanced matching for better results
            try:
                scored_matches = await self.ai_matcher.find_best_matches(need, references, top_k=10)
                return [ref for ref, score in scored_matches if score > 0.3]
            except Exception as e:
                logger.warning(f"AI matching failed, falling back to basic matching: {e}")
        
        # Fallback to basic matching
        matches = []
        
        for reference in references:
            relevance_score = await self._calculate_relevance_score(need, reference)
            if relevance_score > 0.3:  # Minimum relevance threshold
                matches.append((reference, relevance_score))
        
        # Sort by relevance score
        matches.sort(key=lambda x: x[1], reverse=True)
        return [ref for ref, _ in matches]
    
    async def _calculate_relevance_score(self, need: CitationNeed, reference: Reference) -> float:
        """Calculate relevance score between citation need and reference."""
        score = 0.0
        
        # Text similarity
        need_text = f"{need.text_snippet} {need.context}".lower()
        ref_text = f"{reference.title} {reference.abstract or ''}".lower()
        
        # Simple keyword overlap (in production, would use embeddings)
        need_words = set(need_text.split())
        ref_words = set(ref_text.split())
        
        if need_words and ref_words:
            overlap = len(need_words.intersection(ref_words))
            score += overlap / max(len(need_words), len(ref_words))
        
        # Claim type matching
        if need.claim_type == 'statistical_fact' and 'study' in ref_text:
            score += 0.2
        elif need.claim_type == 'methodology' and reference.reference_type.value == 'journal_article':
            score += 0.1
        
        return min(1.0, score)
    
    async def fetch_missing_metadata(self, references: List[Reference]) -> List[Reference]:
        """
        Fetch missing metadata using DOI validation.
        
        Args:
            references: List of references
            
        Returns:
            List of references with enriched metadata
        """
        enriched_refs = []
        
        for reference in references:
            try:
                enriched_ref = await self.doi_validator.enrich_reference_with_doi(reference)
                enriched_refs.append(enriched_ref)
            except Exception as e:
                logger.warning(f"Failed to enrich reference {reference.id}: {e}")
                enriched_refs.append(reference)
        
        self.stats['dois_validated'] += len([r for r in references if r.doi])
        return enriched_refs
    
    async def check_duplicates(self, references: List[Reference]) -> Tuple[List[Reference], List[DuplicateGroup]]:
        """
        Check for and resolve duplicate references.
        
        Args:
            references: List of references to check
            
        Returns:
            Tuple of (deduplicated references, duplicate groups found)
        """
        duplicate_groups = await self.deduplicator.find_duplicates(references)
        deduplicated_refs = await self.deduplicator.merge_duplicates(references, duplicate_groups)
        
        self.stats['duplicates_found'] += len(duplicate_groups)
        return deduplicated_refs, duplicate_groups
    
    async def prioritize_references(self, references: List[Reference], max_count: int) -> List[Reference]:
        """
        Prioritize references when count exceeds limit.
        
        Args:
            references: List of references
            max_count: Maximum number to keep
            
        Returns:
            Prioritized list of references
        """
        if len(references) <= max_count:
            return references
        
        # Score references for prioritization
        scored_refs = []
        
        for reference in references:
            score = 0.0
            
            # Prefer references with DOI
            if reference.doi:
                score += 2.0
            
            # Prefer higher citation count
            if reference.citation_count:
                score += min(reference.citation_count / 100, 2.0)
            
            # Prefer more recent
            if reference.year:
                years_old = datetime.now().year - reference.year
                score += max(0, 2.0 - years_old / 10)
            
            # Prefer complete metadata
            if reference.abstract:
                score += 1.0
            if reference.authors:
                score += 0.5
            if reference.journal:
                score += 0.5
            
            scored_refs.append((reference, score))
        
        # Sort by score and return top references
        scored_refs.sort(key=lambda x: x[1], reverse=True)
        return [ref for ref, _ in scored_refs[:max_count]]
    
    async def format_references(self, references: List[Reference], style: CitationStyle) -> List[Citation]:
        """
        Format references as citations in specified style.
        
        Args:
            references: List of references to format
            style: Citation style to use
            
        Returns:
            List of formatted citations
        """
        citations = []
        formatter = self.formatter_factory.get_formatter(style.value.upper())
        
        for i, reference in enumerate(references):
            try:
                formatted_text = formatter.format_journal_article(
                    authors=reference.authors,
                    title=reference.title,
                    journal=reference.journal or "",
                    year=reference.year,
                    volume=reference.volume,
                    issue=reference.issue,
                    pages=reference.pages,
                    doi=reference.doi
                )
                
                # Generate BibTeX
                bibtex = self._generate_bibtex(reference)
                
                citation = Citation(
                    reference_id=reference.id,
                    formatted_text=formatted_text,
                    style=style,
                    in_text_markers=[str(i + 1)],  # Sequential numbering
                    bibtex=bibtex,
                    is_complete=self._is_citation_complete(reference),
                    completeness_score=self._calculate_citation_completeness(reference)
                )
                
                citations.append(citation)
                
            except Exception as e:
                logger.warning(f"Failed to format reference {reference.id}: {e}")
                # Create fallback citation
                fallback_citation = Citation(
                    reference_id=reference.id,
                    formatted_text=f"{reference.title or 'Unknown title'} ({reference.year or 'Unknown year'})",
                    style=style,
                    in_text_markers=[str(i + 1)],
                    is_complete=False,
                    completeness_score=0.5
                )
                citations.append(fallback_citation)
        
        return citations
    
    def _generate_bibtex(self, reference: Reference) -> str:
        """Generate BibTeX entry for reference."""
        entry_id = reference.doi or reference.pmid or reference.id
        entry_type = 'article' if reference.reference_type.value == 'journal_article' else 'misc'
        
        lines = [f'@{entry_type}{{{entry_id},']
        
        if reference.title:
            lines.append(f'  title = {{{reference.title}}},')
        
        if reference.authors:
            authors_str = ' and '.join(reference.authors)
            lines.append(f'  author = {{{authors_str}}},')
        
        if reference.journal:
            lines.append(f'  journal = {{{reference.journal}}},')
        
        if reference.year:
            lines.append(f'  year = {{{reference.year}}},')
        
        if reference.volume:
            lines.append(f'  volume = {{{reference.volume}}},')
        
        if reference.issue:
            lines.append(f'  number = {{{reference.issue}}},')
        
        if reference.pages:
            lines.append(f'  pages = {{{reference.pages}}},')
        
        if reference.doi:
            lines.append(f'  doi = {{{reference.doi}}},')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def _is_citation_complete(self, reference: Reference) -> bool:
        """Check if citation has all required fields."""
        required_fields = ['title', 'authors', 'year']
        return all(getattr(reference, field) for field in required_fields)
    
    def _calculate_citation_completeness(self, reference: Reference) -> float:
        """Calculate completeness score for citation."""
        required_fields = ['title', 'authors', 'year']
        optional_fields = ['journal', 'volume', 'issue', 'pages', 'doi']
        
        required_present = sum(1 for field in required_fields if getattr(reference, field))
        optional_present = sum(1 for field in optional_fields if getattr(reference, field))
        
        required_score = required_present / len(required_fields)
        optional_score = optional_present / len(optional_fields)
        
        return 0.7 * required_score + 0.3 * optional_score
    
    async def assess_quality(
        self, 
        references: List[Reference], 
        manuscript_text: str,
        research_field: str
    ) -> List[QualityScore]:
        """
        Assess quality of references.
        
        Args:
            references: List of references to assess
            manuscript_text: Manuscript text for relevance assessment
            research_field: Research field for field-specific assessment
            
        Returns:
            List of quality scores
        """
        quality_scores = []
        
        for reference in references:
            try:
                score = await self.quality_assessor.assess_reference_quality(
                    reference, manuscript_text, research_field
                )
                quality_scores.append(score)
            except Exception as e:
                logger.warning(f"Failed to assess quality for reference {reference.id}: {e}")
        
        self.stats['quality_assessments'] += len(quality_scores)
        return quality_scores
    
    async def generate_bibliography(self, citations: List[Citation], style: CitationStyle) -> str:
        """
        Generate formatted bibliography.
        
        Args:
            citations: List of formatted citations
            style: Citation style
            
        Returns:
            Formatted bibliography string
        """
        if not citations:
            return ""
        
        # Sort citations by in-text marker (numerical order)
        try:
            sorted_citations = sorted(citations, key=lambda c: int(c.in_text_markers[0]) if c.in_text_markers else 999)
        except (ValueError, IndexError):
            sorted_citations = citations
        
        bibliography_lines = []
        
        for citation in sorted_citations:
            # Add numbering for numbered styles
            if style in [CitationStyle.VANCOUVER, CitationStyle.AMA]:
                number = citation.in_text_markers[0] if citation.in_text_markers else "?"
                bibliography_lines.append(f"{number}. {citation.formatted_text}")
            else:
                bibliography_lines.append(citation.formatted_text)
        
        bibliography = '\n\n'.join(bibliography_lines)
        self.stats['bibliographies_generated'] += 1
        
        return bibliography
    
    def create_citation_map(self, citation_needs: List[CitationNeed], citations: List[Citation]) -> Dict[str, str]:
        """
        Create mapping from citation markers to reference IDs.
        
        Args:
            citation_needs: Original citation needs
            citations: Formatted citations
            
        Returns:
            Dictionary mapping markers to reference IDs
        """
        citation_map = {}
        
        # Create lookup from reference ID to citation
        ref_to_citation = {citation.reference_id: citation for citation in citations}
        
        for need in citation_needs:
            if need.suggested_references:
                # Map citation need to first suggested reference
                primary_ref_id = need.suggested_references[0]
                if primary_ref_id in ref_to_citation:
                    citation = ref_to_citation[primary_ref_id]
                    if citation.in_text_markers:
                        citation_map[need.text_snippet] = citation.in_text_markers[0]
        
        return citation_map
    
    async def calculate_style_compliance(self, citations: List[Citation], style: CitationStyle) -> float:
        """Calculate overall style compliance score."""
        if not citations:
            return 1.0
        
        compliant_citations = sum(1 for citation in citations if citation.format_compliance)
        return compliant_citations / len(citations)
    
    async def get_analytics(self, references: List[Reference], manuscript_text: str = "") -> ReferenceAnalytics:
        """
        Get analytics for reference strategy.
        
        Args:
            references: List of references
            manuscript_text: Manuscript text for analysis
            
        Returns:
            Reference analytics report
        """
        return await self.analytics.analyze_citation_patterns(references, manuscript_text)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        avg_processing_time = (
            self.stats['processing_time_total'] / self.stats['processings_performed']
            if self.stats['processings_performed'] > 0 else 0
        )
        
        service_stats = {
            **self.stats,
            'average_processing_time_seconds': avg_processing_time,
        }
        
        # Add component stats
        if self.cache:
            service_stats['cache'] = await self.cache.get_stats()
        
        if self.api_manager:
            service_stats['api_manager'] = await self.api_manager.get_stats()
        
        if self.doi_validator:
            service_stats['doi_validator'] = await self.doi_validator.get_stats()
        
        if self.quality_assessor:
            service_stats['quality_assessor'] = await self.quality_assessor.get_stats()
        
        return service_stats


# Global service instance
_service_instance: Optional[ReferenceManagementService] = None


async def get_reference_service() -> ReferenceManagementService:
    """Get global reference management service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReferenceManagementService()
        await _service_instance.initialize()
    return _service_instance


async def close_reference_service() -> None:
    """Close global reference management service."""
    global _service_instance
    if _service_instance:
        _service_instance = None