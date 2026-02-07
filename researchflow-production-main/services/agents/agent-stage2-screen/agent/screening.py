"""
Core screening logic for Stage 2 literature screening.
Handles deduplication, criteria application, and study type classification.
"""
import structlog
from typing import List, Dict, Any, Set, Optional, Tuple
import re
from agent.schemas import (
    PaperScreeningResult,
    ScreeningCriteria,
    StudyType,
)

logger = structlog.get_logger()


class PaperDeduplicator:
    """Deduplicate papers based on DOI, title, and author similarity."""
    
    @staticmethod
    def get_paper_signature(paper: Dict[str, Any]) -> str:
        """Generate unique signature for a paper."""
        # Prefer DOI if available
        if paper.get("doi"):
            return f"doi:{paper['doi'].lower().strip()}"
        
        # Fallback to normalized title + first author + year
        title = PaperDeduplicator._normalize_title(paper.get("title", ""))
        authors = paper.get("authors", [])
        first_author = ""
        if authors:
            if isinstance(authors[0], dict):
                first_author = authors[0].get("name", "").lower().strip()
            else:
                first_author = str(authors[0]).lower().strip()
        
        year = paper.get("year", "") or paper.get("publication_year", "")
        
        return f"title:{title[:100]}|author:{first_author[:50]}|year:{year}"
    
    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""
        # Convert to lowercase, remove punctuation, collapse whitespace
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    @staticmethod
    def find_duplicates(
        papers: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, str]]:
        """
        Find and separate duplicate papers.
        
        Returns:
            Tuple of (unique_papers, duplicates, duplicate_map)
            duplicate_map: signature -> original_paper_id
        """
        seen_signatures: Dict[str, str] = {}  # signature -> paper_id
        unique_papers = []
        duplicates = []
        duplicate_map = {}
        
        for paper in papers:
            signature = PaperDeduplicator.get_paper_signature(paper)
            paper_id = paper.get("id") or paper.get("pmid") or paper.get("paper_id", "")
            
            if signature not in seen_signatures:
                seen_signatures[signature] = str(paper_id)
                unique_papers.append(paper)
            else:
                # Mark as duplicate
                original_id = seen_signatures[signature]
                duplicate_map[str(paper_id)] = original_id
                duplicates.append({
                    **paper,
                    "duplicate_of": original_id,
                    "duplicate_signature": signature,
                })
                logger.debug(
                    "duplicate_found",
                    title=paper.get("title", "")[:50],
                    duplicate_of=original_id,
                )
        
        return unique_papers, duplicates, duplicate_map


class StudyTypeClassifier:
    """Classify study types based on title, abstract, and metadata."""
    
    # Keyword patterns for study type detection
    PATTERNS = {
        StudyType.RANDOMIZED_CONTROLLED_TRIAL: [
            r'\brandomized controlled trial\b',
            r'\brct\b',
            r'\brandomised\b.*\btrial\b',
            r'\brandom allocation\b',
        ],
        StudyType.SYSTEMATIC_REVIEW: [
            r'\bsystematic review\b',
            r'\bsystematic literature review\b',
        ],
        StudyType.META_ANALYSIS: [
            r'\bmeta-analysis\b',
            r'\bmeta analysis\b',
            r'\bpooled analysis\b',
        ],
        StudyType.COHORT_STUDY: [
            r'\bcohort study\b',
            r'\bprospective cohort\b',
            r'\bretrospective cohort\b',
            r'\blongitudinal study\b',
        ],
        StudyType.CASE_CONTROL_STUDY: [
            r'\bcase-control\b',
            r'\bcase control\b',
        ],
        StudyType.CROSS_SECTIONAL_STUDY: [
            r'\bcross-sectional\b',
            r'\bcross sectional\b',
        ],
        StudyType.CASE_REPORT: [
            r'\bcase report\b',
            r'\bcase series\b',
        ],
        StudyType.REVIEW: [
            r'\breview\b',
            r'\bliterature review\b',
        ],
    }
    
    @staticmethod
    def classify(paper: Dict[str, Any]) -> StudyType:
        """Classify study type based on paper metadata."""
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        publication_types = paper.get("publication_types", [])
        
        text = f"{title} {abstract}"
        
        # Check publication type metadata first
        if publication_types:
            for pub_type in publication_types:
                pt_lower = str(pub_type).lower()
                if "randomized controlled trial" in pt_lower:
                    return StudyType.RANDOMIZED_CONTROLLED_TRIAL
                if "systematic review" in pt_lower:
                    return StudyType.SYSTEMATIC_REVIEW
                if "meta-analysis" in pt_lower:
                    return StudyType.META_ANALYSIS
        
        # Pattern matching on title/abstract
        for study_type, patterns in StudyTypeClassifier.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return study_type
        
        return StudyType.UNKNOWN


class CriteriaScreener:
    """Apply inclusion/exclusion criteria to papers."""
    
    def __init__(self, criteria: ScreeningCriteria):
        self.criteria = criteria
    
    def screen_paper(self, paper: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """
        Screen a single paper against criteria.
        
        Returns:
            Tuple of (is_included, reason, matched_criteria)
        """
        matched_criteria = []
        
        # Check year range
        year = paper.get("year") or paper.get("publication_year")
        if year:
            try:
                year_int = int(year)
                if self.criteria.year_min and year_int < self.criteria.year_min:
                    return False, f"Publication year {year_int} before minimum {self.criteria.year_min}", []
                if self.criteria.year_max and year_int > self.criteria.year_max:
                    return False, f"Publication year {year_int} after maximum {self.criteria.year_max}", []
            except (ValueError, TypeError):
                pass
        
        # Check abstract requirement
        if self.criteria.require_abstract:
            abstract = paper.get("abstract", "").strip()
            if not abstract:
                return False, "No abstract available (required by criteria)", []
        
        # Get text for keyword matching
        title = paper.get("title", "").lower()
        abstract = paper.get("abstract", "").lower()
        text = f"{title} {abstract}"
        
        # Check excluded keywords (fail fast)
        for keyword in self.criteria.excluded_keywords:
            if keyword.lower() in text:
                return False, f"Contains excluded keyword: {keyword}", []
        
        # Check exclusion criteria strings
        for excl in self.criteria.exclusion:
            excl_lower = excl.lower()
            if excl_lower in text:
                return False, f"Matches exclusion criterion: {excl}", []
        
        # Check study type exclusions
        study_type = StudyTypeClassifier.classify(paper)
        if study_type in self.criteria.study_types_excluded:
            return False, f"Study type {study_type.value} is excluded", []
        
        # Check study type requirements
        if self.criteria.study_types_required:
            if study_type not in self.criteria.study_types_required:
                return False, f"Study type {study_type.value} not in required types", []
            matched_criteria.append(f"Study type: {study_type.value}")
        
        # Check required keywords
        for keyword in self.criteria.required_keywords:
            if keyword.lower() in text:
                matched_criteria.append(f"Keyword: {keyword}")
            else:
                return False, f"Missing required keyword: {keyword}", matched_criteria
        
        # Check inclusion criteria strings
        for incl in self.criteria.inclusion:
            incl_lower = incl.lower()
            if incl_lower in text:
                matched_criteria.append(f"Inclusion: {incl}")
        
        # If we have inclusion criteria, at least one must match
        if self.criteria.inclusion and not any(
            incl.lower() in text for incl in self.criteria.inclusion
        ):
            return False, "Does not match any inclusion criteria", matched_criteria
        
        # Passed all checks
        if matched_criteria:
            reason = f"Meets criteria: {'; '.join(matched_criteria[:3])}"
        else:
            reason = "Meets all criteria (no specific matches required)"
        
        return True, reason, matched_criteria
