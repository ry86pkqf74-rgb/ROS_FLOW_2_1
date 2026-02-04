"""
Reference Duplicate Detection and Merging

Identifies duplicate references using multiple matching strategies and provides
intelligent merging recommendations.

Linear Issues: ROS-XXX
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from difflib import SequenceMatcher
import hashlib

from .reference_types import Reference, DuplicateGroup
from .reference_cache import get_cache

logger = logging.getLogger(__name__)


class PaperDeduplicator:
    """Reference deduplication service with multiple matching strategies."""
    
    # Similarity thresholds for different matching strategies
    SIMILARITY_THRESHOLDS = {
        'exact_match': 1.0,
        'doi_match': 1.0,
        'pmid_match': 1.0,
        'title_high': 0.95,
        'title_medium': 0.85,
        'title_low': 0.70,
        'author_title': 0.80,
        'fuzzy_comprehensive': 0.75,
    }
    
    # Weights for different fields in fuzzy matching
    FIELD_WEIGHTS = {
        'title': 0.4,
        'authors': 0.3,
        'journal': 0.15,
        'year': 0.1,
        'doi': 0.05,
    }
    
    def __init__(self):
        """Initialize duplicate detector."""
        self.cache = None
        self.stats = {
            'comparisons_made': 0,
            'duplicates_found': 0,
            'exact_matches': 0,
            'doi_matches': 0,
            'pmid_matches': 0,
            'fuzzy_matches': 0,
        }
    
    async def initialize(self) -> None:
        """Initialize dependencies."""
        self.cache = await get_cache()
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove common punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common stop words that don't affect meaning
        stop_words = {'a', 'an', 'and', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        words = normalized.split()
        words = [w for w in words if w not in stop_words]
        
        return ' '.join(words).strip()
    
    def _normalize_author_list(self, authors: List[str]) -> List[str]:
        """
        Normalize author names for comparison.
        
        Args:
            authors: List of author names
            
        Returns:
            List of normalized author names
        """
        if not authors:
            return []
        
        normalized = []
        for author in authors:
            # Extract last name and first initial
            author = author.strip()
            if ',' in author:
                # Format: "Last, First Middle"
                parts = author.split(',', 1)
                last_name = parts[0].strip()
                first_part = parts[1].strip() if len(parts) > 1 else ""
                if first_part:
                    first_initial = first_part[0].upper()
                    normalized.append(f"{last_name.lower()}, {first_initial}")
                else:
                    normalized.append(last_name.lower())
            else:
                # Format: "First Middle Last"
                parts = author.split()
                if len(parts) >= 2:
                    first_initial = parts[0][0].upper()
                    last_name = parts[-1]
                    normalized.append(f"{last_name.lower()}, {first_initial}")
                else:
                    normalized.append(author.lower())
        
        return sorted(normalized)  # Sort for consistent comparison
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            Similarity score (0-1)
        """
        if not title1 or not title2:
            return 0.0
        
        norm_title1 = self._normalize_text(title1)
        norm_title2 = self._normalize_text(title2)
        
        if norm_title1 == norm_title2:
            return 1.0
        
        # Use sequence matcher for fuzzy comparison
        return SequenceMatcher(None, norm_title1, norm_title2).ratio()
    
    def _calculate_author_similarity(self, authors1: List[str], authors2: List[str]) -> float:
        """
        Calculate similarity between two author lists.
        
        Args:
            authors1: First author list
            authors2: Second author list
            
        Returns:
            Similarity score (0-1)
        """
        if not authors1 or not authors2:
            return 0.0
        
        norm_authors1 = set(self._normalize_author_list(authors1))
        norm_authors2 = set(self._normalize_author_list(authors2))
        
        if not norm_authors1 or not norm_authors2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(norm_authors1.intersection(norm_authors2))
        union = len(norm_authors1.union(norm_authors2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_journal_similarity(self, journal1: str, journal2: str) -> float:
        """
        Calculate similarity between two journal names.
        
        Args:
            journal1: First journal name
            journal2: Second journal name
            
        Returns:
            Similarity score (0-1)
        """
        if not journal1 or not journal2:
            return 0.0
        
        norm_journal1 = self._normalize_text(journal1)
        norm_journal2 = self._normalize_text(journal2)
        
        if norm_journal1 == norm_journal2:
            return 1.0
        
        # Handle common journal name variations
        journal_abbreviations = {
            'j': 'journal',
            'am j': 'american journal',
            'br j': 'british journal',
            'eur j': 'european journal',
            'int j': 'international journal',
            'n engl j med': 'new england journal of medicine',
            'jama': 'journal of the american medical association',
        }
        
        for abbrev, full in journal_abbreviations.items():
            if abbrev in norm_journal1 or abbrev in norm_journal2:
                norm_journal1 = norm_journal1.replace(abbrev, full)
                norm_journal2 = norm_journal2.replace(abbrev, full)
        
        return SequenceMatcher(None, norm_journal1, norm_journal2).ratio()
    
    def _calculate_year_similarity(self, year1: Optional[int], year2: Optional[int]) -> float:
        """
        Calculate similarity between two publication years.
        
        Args:
            year1: First publication year
            year2: Second publication year
            
        Returns:
            Similarity score (0-1)
        """
        if year1 is None or year2 is None:
            return 0.0
        
        if year1 == year2:
            return 1.0
        
        # Allow small differences (typos, early online publication)
        diff = abs(year1 - year2)
        if diff <= 1:
            return 0.9
        elif diff <= 2:
            return 0.5
        else:
            return 0.0
    
    def _calculate_comprehensive_similarity(self, ref1: Reference, ref2: Reference) -> Tuple[float, List[str]]:
        """
        Calculate comprehensive similarity score between two references.
        
        Args:
            ref1: First reference
            ref2: Second reference
            
        Returns:
            Tuple of (similarity score, list of matching criteria)
        """
        self.stats['comparisons_made'] += 1
        
        # Check for exact matches first
        if ref1.doi and ref2.doi:
            if self._normalize_text(ref1.doi) == self._normalize_text(ref2.doi):
                self.stats['doi_matches'] += 1
                return 1.0, ['doi_match']
        
        if ref1.pmid and ref2.pmid:
            if ref1.pmid == ref2.pmid:
                self.stats['pmid_matches'] += 1
                return 1.0, ['pmid_match']
        
        # Calculate individual field similarities
        title_sim = self._calculate_title_similarity(ref1.title, ref2.title)
        author_sim = self._calculate_author_similarity(ref1.authors, ref2.authors)
        journal_sim = self._calculate_journal_similarity(ref1.journal or "", ref2.journal or "")
        year_sim = self._calculate_year_similarity(ref1.year, ref2.year)
        
        # Weighted overall similarity
        overall_sim = (
            title_sim * self.FIELD_WEIGHTS['title'] +
            author_sim * self.FIELD_WEIGHTS['authors'] +
            journal_sim * self.FIELD_WEIGHTS['journal'] +
            year_sim * self.FIELD_WEIGHTS['year']
        )
        
        # Determine matching criteria
        criteria = []
        if title_sim >= self.SIMILARITY_THRESHOLDS['title_high']:
            criteria.append('title_high_similarity')
        elif title_sim >= self.SIMILARITY_THRESHOLDS['title_medium']:
            criteria.append('title_medium_similarity')
        elif title_sim >= self.SIMILARITY_THRESHOLDS['title_low']:
            criteria.append('title_low_similarity')
        
        if author_sim >= 0.8:
            criteria.append('author_similarity')
        
        if journal_sim >= 0.9:
            criteria.append('journal_similarity')
        
        if year_sim >= 0.9:
            criteria.append('year_match')
        
        if overall_sim >= self.SIMILARITY_THRESHOLDS['fuzzy_comprehensive']:
            criteria.append('comprehensive_similarity')
            self.stats['fuzzy_matches'] += 1
        
        return overall_sim, criteria
    
    async def find_duplicates(self, references: List[Reference]) -> List[DuplicateGroup]:
        """
        Find duplicate references in a list.
        
        Args:
            references: List of references to check for duplicates
            
        Returns:
            List of duplicate groups
        """
        if not self.cache:
            await self.initialize()
        
        if len(references) < 2:
            return []
        
        # Generate cache key for this set of references
        ref_ids = sorted([ref.id for ref in references])
        cache_key = hashlib.md5('|'.join(ref_ids).encode()).hexdigest()
        
        # Check cache
        if self.cache:
            cached_result = await self.cache.get('duplicate_detection', cache_key, 'dict')
            if cached_result:
                return [DuplicateGroup.model_validate(group) for group in cached_result]
        
        duplicate_groups = []
        processed_refs = set()
        
        for i, ref1 in enumerate(references):
            if ref1.id in processed_refs:
                continue
            
            duplicates = [ref1.id]
            
            for j, ref2 in enumerate(references[i+1:], i+1):
                if ref2.id in processed_refs:
                    continue
                
                similarity, criteria = self._calculate_comprehensive_similarity(ref1, ref2)
                
                if similarity >= self.SIMILARITY_THRESHOLDS['fuzzy_comprehensive']:
                    duplicates.append(ref2.id)
                    processed_refs.add(ref2.id)
            
            if len(duplicates) > 1:
                # Determine primary reference (prefer one with DOI, more complete metadata)
                primary_ref_id = self._select_primary_reference(
                    [ref for ref in references if ref.id in duplicates]
                )
                
                group = DuplicateGroup(
                    group_id=f"dup_{len(duplicate_groups)}_{int(datetime.utcnow().timestamp())}",
                    reference_ids=duplicates,
                    primary_reference_id=primary_ref_id,
                    similarity_score=similarity,
                    match_criteria=criteria,
                    auto_resolvable=self._can_auto_resolve(criteria, similarity),
                    resolution_strategy=self._get_resolution_strategy(criteria)
                )
                
                duplicate_groups.append(group)
                processed_refs.update(duplicates)
                self.stats['duplicates_found'] += len(duplicates) - 1
        
        # Cache result
        if self.cache and duplicate_groups:
            cache_data = [group.model_dump() for group in duplicate_groups]
            await self.cache.set('duplicate_detection', cache_key, cache_data)
        
        return duplicate_groups
    
    def _select_primary_reference(self, references: List[Reference]) -> str:
        """
        Select the primary reference from a duplicate group.
        
        Args:
            references: List of duplicate references
            
        Returns:
            ID of the primary reference
        """
        if not references:
            return ""
        
        if len(references) == 1:
            return references[0].id
        
        # Scoring criteria for primary reference selection
        scores = []
        for ref in references:
            score = 0
            
            # Prefer references with DOI
            if ref.doi:
                score += 10
            
            # Prefer references with PMID
            if ref.pmid:
                score += 8
            
            # Prefer more complete author lists
            if ref.authors:
                score += min(len(ref.authors), 5)
            
            # Prefer references with abstracts
            if ref.abstract:
                score += 5
            
            # Prefer references with complete metadata
            if ref.journal:
                score += 2
            if ref.year:
                score += 2
            if ref.volume:
                score += 1
            if ref.issue:
                score += 1
            if ref.pages:
                score += 1
            
            # Prefer more recent entries (better data quality)
            if ref.created_at:
                days_old = (datetime.utcnow() - ref.created_at).days
                score += max(0, 5 - days_old // 30)  # Bonus for recent entries
            
            scores.append((score, ref.id))
        
        # Return ID of reference with highest score
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1]
    
    def _can_auto_resolve(self, criteria: List[str], similarity: float) -> bool:
        """
        Determine if duplicate group can be automatically resolved.
        
        Args:
            criteria: List of matching criteria
            similarity: Overall similarity score
            
        Returns:
            True if can be auto-resolved
        """
        # Auto-resolve if we have strong evidence
        if 'doi_match' in criteria or 'pmid_match' in criteria:
            return True
        
        if 'title_high_similarity' in criteria and 'author_similarity' in criteria:
            return True
        
        if similarity >= 0.95:
            return True
        
        return False
    
    def _get_resolution_strategy(self, criteria: List[str]) -> str:
        """
        Get resolution strategy for duplicate group.
        
        Args:
            criteria: List of matching criteria
            
        Returns:
            Resolution strategy name
        """
        if 'doi_match' in criteria or 'pmid_match' in criteria:
            return 'merge_identical'
        
        if 'title_high_similarity' in criteria and 'author_similarity' in criteria:
            return 'merge_high_confidence'
        
        if 'comprehensive_similarity' in criteria:
            return 'merge_with_review'
        
        return 'manual_review'
    
    async def merge_duplicates(self, references: List[Reference], duplicate_groups: List[DuplicateGroup]) -> List[Reference]:
        """
        Merge duplicate references based on duplicate groups.
        
        Args:
            references: Original list of references
            duplicate_groups: List of duplicate groups
            
        Returns:
            List of merged references (duplicates removed)
        """
        # Create reference lookup
        ref_lookup = {ref.id: ref for ref in references}
        
        # Track which references to keep
        refs_to_keep = set(ref.id for ref in references)
        merged_refs = {}
        
        for group in duplicate_groups:
            if not group.auto_resolvable:
                continue  # Skip groups that need manual review
            
            # Get primary reference
            primary_ref = ref_lookup.get(group.primary_reference_id)
            if not primary_ref:
                continue
            
            # Merge metadata from all references in the group
            merged_ref = self._merge_reference_metadata(
                primary_ref,
                [ref_lookup[ref_id] for ref_id in group.reference_ids if ref_id in ref_lookup]
            )
            
            # Remove duplicates from keep set
            for ref_id in group.reference_ids:
                if ref_id != group.primary_reference_id:
                    refs_to_keep.discard(ref_id)
            
            merged_refs[group.primary_reference_id] = merged_ref
        
        # Build result list
        result = []
        for ref in references:
            if ref.id in refs_to_keep:
                if ref.id in merged_refs:
                    result.append(merged_refs[ref.id])
                else:
                    result.append(ref)
        
        return result
    
    def _merge_reference_metadata(self, primary: Reference, all_refs: List[Reference]) -> Reference:
        """
        Merge metadata from multiple references into the primary reference.
        
        Args:
            primary: Primary reference to merge into
            all_refs: All references in the duplicate group
            
        Returns:
            Merged reference
        """
        merged = primary.model_copy()
        
        # Merge data, preferring the most complete information
        for ref in all_refs:
            if ref.id == primary.id:
                continue
            
            # Title - prefer longer, more complete title
            if not merged.title or (ref.title and len(ref.title) > len(merged.title)):
                merged.title = ref.title
            
            # Authors - prefer longer author list
            if not merged.authors or (ref.authors and len(ref.authors) > len(merged.authors)):
                merged.authors = ref.authors
            
            # Journal - prefer non-empty
            if not merged.journal and ref.journal:
                merged.journal = ref.journal
            
            # Year - prefer non-empty
            if not merged.year and ref.year:
                merged.year = ref.year
            
            # DOI - prefer non-empty
            if not merged.doi and ref.doi:
                merged.doi = ref.doi
            
            # PMID - prefer non-empty
            if not merged.pmid and ref.pmid:
                merged.pmid = ref.pmid
            
            # Abstract - prefer longer abstract
            if not merged.abstract or (ref.abstract and len(ref.abstract) > len(merged.abstract or "")):
                merged.abstract = ref.abstract
            
            # Citation count - prefer higher count
            if ref.citation_count and (not merged.citation_count or ref.citation_count > merged.citation_count):
                merged.citation_count = ref.citation_count
            
            # Other metadata fields
            if not merged.volume and ref.volume:
                merged.volume = ref.volume
            
            if not merged.issue and ref.issue:
                merged.issue = ref.issue
            
            if not merged.pages and ref.pages:
                merged.pages = ref.pages
            
            if not merged.url and ref.url:
                merged.url = ref.url
        
        merged.updated_at = datetime.utcnow()
        return merged
    
    async def get_stats(self) -> Dict[str, any]:
        """Get deduplication statistics."""
        return {
            **self.stats,
            'thresholds': self.SIMILARITY_THRESHOLDS,
            'field_weights': self.FIELD_WEIGHTS,
        }


async def deduplicate_references(references: List[Reference]) -> Tuple[List[Reference], List[DuplicateGroup]]:
    """
    Convenience function to deduplicate a list of references.
    
    Args:
        references: List of references to deduplicate
        
    Returns:
        Tuple of (deduplicated references, duplicate groups found)
    """
    deduplicator = PaperDeduplicator()
    await deduplicator.initialize()
    
    # Find duplicates
    duplicate_groups = await deduplicator.find_duplicates(references)
    
    # Merge duplicates
    deduplicated_refs = await deduplicator.merge_duplicates(references, duplicate_groups)
    
    return deduplicated_refs, duplicate_groups