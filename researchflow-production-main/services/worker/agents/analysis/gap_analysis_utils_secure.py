"""
Gap Analysis Utilities (Security-Compliant Version)

Helper functions for gap analysis including:
- Semantic literature comparison using AI Router (SECURITY COMPLIANT)
- Text similarity calculations
- Gap categorization heuristics
- PICO extraction from text
- Citation processing

SECURITY: All AI calls must go through packages/ai-router/ - no direct OpenAI/Anthropic imports
Linear Issues: ROS-XXX (Stage 10 - Gap Analysis Agent)
"""

import os
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

# SECURITY: Use AI Router instead of direct AI provider imports
# from openai import AsyncOpenAI  # REMOVED - Violates ResearchFlow AI Router pattern

logger = logging.getLogger(__name__)


# =============================================================================
# Literature Comparison Engine (AI Router Compliant)
# =============================================================================

class LiteratureComparator:
    """
    Semantic comparison of study findings against literature using embeddings.
    
    SECURITY: Uses AI Router service for embeddings (HIPAA compliant)
    """
    
    def __init__(self, model: str = "text-embedding-3-large"):
        """
        Initialize comparator with AI Router client.
        
        Args:
            model: Embedding model to use (default: text-embedding-3-large)
        """
        # SECURITY FIX: Must use AI Router instead of direct AI providers
        logger.warning(
            "LiteratureComparator requires AI Router integration. "
            "Direct AI provider access violates ResearchFlow security policy. "
            "Using fallback keyword comparison until migration complete."
        )
        self.ai_router_client = None  # TODO: Integrate with packages/ai-router/
        
        self.model = model
        self.dimension = 3072 if "large" in model else 1536
        self.cache = {}  # Cache embeddings
    
    async def compare_findings_semantic(
        self,
        current_findings: List[str],
        literature_abstracts: List[Dict[str, str]]
    ) -> List[Tuple[str, str, str, float]]:
        """
        Compare findings to literature using semantic embeddings.
        
        Args:
            current_findings: List of finding descriptions
            literature_abstracts: List of dicts with 'paper_id', 'title', 'abstract'
        
        Returns:
            List of tuples: (finding, paper_id, paper_title, similarity_score)
            Sorted by similarity (highest first)
        """
        # SECURITY: AI Router integration pending
        if not self.ai_router_client:
            logger.info("Using fallback keyword comparison (AI Router integration pending)")
            return self._fallback_comparison(current_findings, literature_abstracts)
        
        try:
            # TODO: Replace with AI Router embedding calls
            # finding_embeddings = await self._get_embeddings_via_router(current_findings)
            # lit_texts = [f"{lit['title']} {lit.get('abstract', '')}" for lit in literature_abstracts]
            # lit_embeddings = await self._get_embeddings_via_router(lit_texts)
            
            # For now, use fallback
            return self._fallback_comparison(current_findings, literature_abstracts)
            
        except Exception as e:
            logger.error(f"Semantic comparison failed: {e}")
            return self._fallback_comparison(current_findings, literature_abstracts)
    
    async def _get_embeddings_via_router(self, texts: List[str]) -> List[np.ndarray]:
        """
        Get embeddings via AI Router (SECURITY COMPLIANT).
        
        TODO: Implement AI Router integration
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors as numpy arrays
        """
        # SECURITY TODO: Replace with AI Router calls
        # Example implementation:
        # 
        # from packages.ai_router import AIRouterClient
        # 
        # async with AIRouterClient() as router:
        #     response = await router.get_embeddings(
        #         texts=texts,
        #         model=self.model,
        #         phi_scan=True  # Enable PHI detection
        #     )
        #     return [np.array(emb) for emb in response.embeddings]
        
        raise NotImplementedError("AI Router integration pending")
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            a, b: Embedding vectors
        
        Returns:
            Similarity score (0-1)
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def categorize_similarity(self, score: float) -> str:
        """
        Categorize similarity score into alignment types.
        
        Args:
            score: Similarity score (0-1)
        
        Returns:
            Category: consistent_with, extends, contradicts, novel_findings
        """
        if score >= 0.85:
            return "consistent_with"
        elif score >= 0.65:
            return "extends"
        elif score <= 0.35:
            return "contradicts"
        else:
            return "novel_findings"
    
    def _fallback_comparison(
        self,
        findings: List[str],
        literature: List[Dict[str, str]]
    ) -> List[Tuple[str, str, str, float]]:
        """
        Fallback keyword-based comparison when embeddings unavailable.
        
        SECURITY: PHI-safe keyword comparison (no AI calls)
        
        Args:
            findings: List of finding descriptions
            literature: List of literature dicts
        
        Returns:
            List of comparison tuples with keyword-based scores
        """
        comparisons = []
        
        for finding in findings:
            finding_words = set(re.findall(r'\w+', finding.lower()))
            
            for lit in literature:
                lit_text = f"{lit.get('title', '')} {lit.get('abstract', '')}".lower()
                lit_words = set(re.findall(r'\w+', lit_text))
                
                # Jaccard similarity
                if len(finding_words) > 0 and len(lit_words) > 0:
                    intersection = finding_words & lit_words
                    union = finding_words | lit_words
                    score = len(intersection) / len(union)
                else:
                    score = 0.0
                
                comparisons.append((
                    finding,
                    lit.get('paper_id', 'unknown'),
                    lit.get('title', 'Unknown'),
                    score
                ))
        
        return sorted(comparisons, key=lambda x: x[3], reverse=True)


# =============================================================================
# PICO Extraction (No AI Required)
# =============================================================================

class PICOExtractor:
    """
    Extract PICO components from text using pattern matching.
    
    SECURITY: Pure regex-based, no AI calls required
    """
    
    # Common patterns
    POPULATION_PATTERNS = [
        r'(?:in|among|participants)\s+([^,\.]+(?:patients|adults|children|individuals))',
        r'(\d+\s+(?:patients|participants|subjects))',
    ]
    
    INTERVENTION_PATTERNS = [
        r'(?:treatment|intervention|therapy)\s+(?:with|using|involving)\s+([^,\.]+)',
        r'(?:received|administered|given)\s+([^,\.]+)',
    ]
    
    OUTCOME_PATTERNS = [
        r'(?:outcome|endpoint|measure)\s+(?:was|were)\s+([^,\.]+)',
        r'(?:measured|assessed|evaluated)\s+([^,\.]+)',
    ]
    
    @classmethod
    def extract_from_text(cls, text: str) -> Dict[str, Optional[str]]:
        """
        Extract PICO components from text using regex patterns.
        
        Args:
            text: Research question or study description
        
        Returns:
            Dict with P, I, C, O components (values may be None)
        """
        text_lower = text.lower()
        
        pico = {
            "population": None,
            "intervention": None,
            "comparison": None,
            "outcome": None
        }
        
        # Extract population
        for pattern in cls.POPULATION_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                pico["population"] = match.group(1).strip()
                break
        
        # Extract intervention
        for pattern in cls.INTERVENTION_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                pico["intervention"] = match.group(1).strip()
                break
        
        # Extract outcome
        for pattern in cls.OUTCOME_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                pico["outcome"] = match.group(1).strip()
                break
        
        # Comparison is harder to extract automatically
        if "compared to" in text_lower or "versus" in text_lower:
            # Try to extract comparison
            comp_match = re.search(r'(?:compared to|versus|vs\.?)\s+([^,\.]+)', text_lower)
            if comp_match:
                pico["comparison"] = comp_match.group(1).strip()
        
        return pico


# =============================================================================
# Gap Categorization Heuristics (No AI Required)
# =============================================================================

class GapCategorizer:
    """
    Heuristic rules for categorizing research gaps.
    
    SECURITY: Pure keyword-based, no AI calls required
    """
    
    # Keywords for gap types
    TEMPORAL_KEYWORDS = ['outdated', 'old', 'years ago', 'recent', 'update', 'current']
    POPULATION_KEYWORDS = ['diverse', 'demographic', 'underrepresented', 'minority', 'age', 'gender']
    METHOD_KEYWORDS = ['design', 'methodology', 'measurement', 'bias', 'limitation', 'validity']
    GEOGRAPHIC_KEYWORDS = ['region', 'country', 'culture', 'geographic', 'international', 'global']
    EMPIRICAL_KEYWORDS = ['data', 'evidence', 'study', 'research', 'findings', 'lacking']
    THEORETICAL_KEYWORDS = ['theory', 'framework', 'model', 'mechanism', 'explanation', 'understanding']
    
    @classmethod
    def suggest_gap_type(cls, gap_description: str) -> str:
        """
        Suggest gap type based on keywords in description.
        
        Args:
            gap_description: Text description of the gap
        
        Returns:
            Suggested gap type: temporal/population/methodological/geographic/empirical/theoretical
        """
        desc_lower = gap_description.lower()
        
        # Count keyword matches
        scores = {
            'temporal': sum(1 for kw in cls.TEMPORAL_KEYWORDS if kw in desc_lower),
            'population': sum(1 for kw in cls.POPULATION_KEYWORDS if kw in desc_lower),
            'methodological': sum(1 for kw in cls.METHOD_KEYWORDS if kw in desc_lower),
            'geographic': sum(1 for kw in cls.GEOGRAPHIC_KEYWORDS if kw in desc_lower),
            'empirical': sum(1 for kw in cls.EMPIRICAL_KEYWORDS if kw in desc_lower),
            'theoretical': sum(1 for kw in cls.THEORETICAL_KEYWORDS if kw in desc_lower),
        }
        
        # Return type with highest score
        max_type = max(scores, key=scores.get)
        
        # If all scores are 0, default to empirical
        if scores[max_type] == 0:
            return 'empirical'
        
        return max_type


# =============================================================================
# Citation Processing (No AI Required)
# =============================================================================

class CitationProcessor:
    """
    Process and format citations for gap analysis.
    
    SECURITY: Pure text processing, no AI calls required
    """
    
    @staticmethod
    def extract_citation_info(paper: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract key citation info from paper dict.
        
        Args:
            paper: Dict with paper metadata
        
        Returns:
            Dict with formatted citation components
        """
        authors = paper.get('authors', [])
        if isinstance(authors, list) and authors:
            if len(authors) > 3:
                author_str = f"{authors[0]} et al."
            else:
                author_str = ", ".join(authors)
        else:
            author_str = "Unknown"
        
        year = paper.get('year', 'n.d.')
        title = paper.get('title', 'Unknown title')
        
        # Short citation
        short = f"{author_str} ({year})"
        
        # Full citation (AMA style)
        journal = paper.get('journal', '')
        if journal:
            full = f"{author_str}. {title}. {journal}. {year}."
        else:
            full = f"{author_str}. {title}. {year}."
        
        return {
            'short': short,
            'full': full,
            'paper_id': paper.get('doi') or paper.get('pmid') or paper.get('paper_id', 'unknown')
        }
    
    @staticmethod
    def format_citation_list(citations: List[Dict[str, str]]) -> str:
        """
        Format list of citations for narrative.
        
        Args:
            citations: List of citation dicts
        
        Returns:
            Formatted citation string
        """
        if not citations:
            return ""
        
        short_cites = [c.get('short', 'Unknown') for c in citations]
        
        if len(short_cites) == 1:
            return short_cites[0]
        elif len(short_cites) == 2:
            return f"{short_cites[0]} and {short_cites[1]}"
        else:
            return ", ".join(short_cites[:-1]) + f", and {short_cites[-1]}"


# =============================================================================
# Text Utilities (PHI-Safe)
# =============================================================================

def clean_text(text: str) -> str:
    """
    Clean text for analysis.
    
    SECURITY: PHI-safe text cleaning
    
    Args:
        text: Raw text
    
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters
    text = re.sub(r'[^\w\s\.,;:!?-]', '', text)
    return text.strip()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to max length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def extract_sentences(text: str, max_sentences: int = 5) -> List[str]:
    """
    Extract first N sentences from text.
    
    Args:
        text: Input text
        max_sentences: Maximum number of sentences
    
    Returns:
        List of sentences
    """
    # Simple sentence splitting
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences[:max_sentences]