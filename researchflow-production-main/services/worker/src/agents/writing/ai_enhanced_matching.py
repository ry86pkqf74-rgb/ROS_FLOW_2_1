"""
AI-Enhanced Citation Matching with Semantic Similarity

Leverages embeddings and LLMs for superior citation-to-context matching.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime
import hashlib

from .reference_types import Reference, CitationNeed
from .reference_cache import get_cache

logger = logging.getLogger(__name__)

class AIEnhancedMatcher:
    """AI-powered semantic citation matching."""
    
    def __init__(self):
        self.encoder = None  # Lazy load
        self.cache = None
        self.fallback_matcher = BasicTextMatcher()
        
    async def initialize(self):
        """Initialize semantic encoder and cache."""
        self.cache = await get_cache()
        
        try:
            # Try to import and initialize sentence transformers
            from sentence_transformers import SentenceTransformer
            # Use lightweight model for production
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("AI-Enhanced matcher initialized with SentenceTransformer")
        except ImportError:
            logger.warning("SentenceTransformers not available, using fallback text matching")
            self.encoder = None
        except Exception as e:
            logger.warning(f"Failed to initialize SentenceTransformer: {e}, using fallback")
            self.encoder = None
    
    async def find_best_matches(
        self, 
        citation_need: CitationNeed, 
        candidate_refs: List[Reference],
        top_k: int = 5
    ) -> List[Tuple[Reference, float]]:
        """Find best semantic matches for citation need."""
        
        if not self.cache:
            await self.initialize()
        
        # Use AI matching if available, otherwise fallback
        if self.encoder is not None:
            return await self._semantic_matching(citation_need, candidate_refs, top_k)
        else:
            return await self._fallback_matching(citation_need, candidate_refs, top_k)
    
    async def _semantic_matching(
        self, 
        citation_need: CitationNeed, 
        candidate_refs: List[Reference],
        top_k: int
    ) -> List[Tuple[Reference, float]]:
        """Perform semantic similarity matching using embeddings."""
        
        # Cache key for citation need embedding
        need_text = f"{citation_need.text_snippet} {citation_need.context}"
        cache_key = f"embedding_{hashlib.md5(need_text.encode()).hexdigest()[:16]}"
        
        # Get or compute citation need embedding
        need_embedding = await self.cache.get('api_responses', cache_key)
        if need_embedding is None:
            need_embedding = self.encoder.encode([need_text])[0]
            await self.cache.set('api_responses', cache_key, need_embedding.tolist(), ttl_override=24*3600)
        
        # Compute reference embeddings
        ref_embeddings = []
        for ref in candidate_refs:
            ref_cache_key = f"ref_embedding_{ref.id}"
            ref_embedding = await self.cache.get('api_responses', ref_cache_key)
            
            if ref_embedding is None:
                ref_text = f"{ref.title} {ref.abstract or ''} {' '.join(ref.keywords)}"
                ref_embedding = self.encoder.encode([ref_text])[0]
                await self.cache.set('api_responses', ref_cache_key, ref_embedding.tolist(), ttl_override=7*24*3600)
            
            ref_embeddings.append(np.array(ref_embedding))
        
        # Calculate semantic similarities
        if ref_embeddings:
            need_emb_array = np.array(need_embedding)
            similarities = [
                np.dot(need_emb_array, ref_emb) / (np.linalg.norm(need_emb_array) * np.linalg.norm(ref_emb))
                for ref_emb in ref_embeddings
            ]
            
            # Combine with existing scoring factors
            scored_refs = []
            for ref, sim_score in zip(candidate_refs, similarities):
                # Boost score based on citation type matching
                type_boost = await self._calculate_type_compatibility(citation_need, ref)
                recency_boost = self._calculate_recency_boost(ref)
                final_score = sim_score * 0.6 + type_boost * 0.3 + recency_boost * 0.1
                scored_refs.append((ref, final_score))
            
            # Sort and return top matches
            scored_refs.sort(key=lambda x: x[1], reverse=True)
            return scored_refs[:top_k]
        
        return []
    
    async def _fallback_matching(
        self, 
        citation_need: CitationNeed, 
        candidate_refs: List[Reference],
        top_k: int
    ) -> List[Tuple[Reference, float]]:
        """Fallback text-based matching when AI models aren't available."""
        return await self.fallback_matcher.find_matches(citation_need, candidate_refs, top_k)
    
    async def _calculate_type_compatibility(self, need: CitationNeed, ref: Reference) -> float:
        """Calculate compatibility between citation need type and reference."""
        compatibility_matrix = {
            'statistical_fact': {
                'journal_article': 1.0,
                'report': 0.8,
                'book': 0.3,
                'conference_paper': 0.7,
                'thesis': 0.6
            },
            'methodology': {
                'journal_article': 1.0,
                'book': 0.8,
                'book_chapter': 0.7,
                'conference_paper': 0.6,
                'thesis': 0.5
            },
            'clinical_guideline': {
                'report': 1.0,
                'journal_article': 0.9,
                'book': 0.6,
                'website': 0.4
            },
            'prior_research': {
                'journal_article': 1.0,
                'conference_paper': 0.8,
                'thesis': 0.6,
                'preprint': 0.7
            },
            'definition': {
                'book': 1.0,
                'journal_article': 0.8,
                'book_chapter': 0.9,
                'website': 0.3
            },
            'background_info': {
                'journal_article': 0.8,
                'book': 0.9,
                'report': 0.7,
                'website': 0.4
            }
        }
        
        type_scores = compatibility_matrix.get(need.claim_type, {})
        return type_scores.get(ref.reference_type.value, 0.5)
    
    def _calculate_recency_boost(self, ref: Reference) -> float:
        """Calculate boost based on publication recency."""
        if not ref.year:
            return 0.3
        
        current_year = datetime.now().year
        age = current_year - ref.year
        
        if age <= 2:
            return 1.0
        elif age <= 5:
            return 0.8
        elif age <= 10:
            return 0.5
        else:
            return 0.2


class BasicTextMatcher:
    """Basic text-based matching as fallback."""
    
    async def find_matches(
        self, 
        citation_need: CitationNeed, 
        candidate_refs: List[Reference],
        top_k: int = 5
    ) -> List[Tuple[Reference, float]]:
        """Find matches using simple text similarity."""
        
        need_words = set(self._extract_keywords(citation_need.context.lower()))
        
        scored_refs = []
        for ref in candidate_refs:
            ref_text = f"{ref.title} {ref.abstract or ''} {' '.join(ref.keywords)}".lower()
            ref_words = set(self._extract_keywords(ref_text))
            
            # Calculate Jaccard similarity
            if need_words and ref_words:
                intersection = len(need_words.intersection(ref_words))
                union = len(need_words.union(ref_words))
                jaccard_score = intersection / union if union > 0 else 0
            else:
                jaccard_score = 0
            
            # Add title boost if keywords match title
            title_words = set(self._extract_keywords(ref.title.lower())) if ref.title else set()
            title_boost = 0.2 if need_words.intersection(title_words) else 0
            
            final_score = jaccard_score + title_boost
            scored_refs.append((ref, final_score))
        
        # Sort and return top matches
        scored_refs.sort(key=lambda x: x[1], reverse=True)
        return scored_refs[:top_k]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'were', 'will', 'with', 'this', 'these',
            'they', 'their', 'there', 'than', 'then', 'them', 'we', 'would',
            'could', 'should', 'have', 'had', 'may', 'might', 'can', 'did'
        }
        
        # Extract words (3+ characters)
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [word for word in words if word not in stop_words]


# Global matcher instance
_matcher_instance: Optional[AIEnhancedMatcher] = None


async def get_ai_matcher() -> AIEnhancedMatcher:
    """Get global AI matcher instance."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = AIEnhancedMatcher()
        await _matcher_instance.initialize()
    return _matcher_instance


async def close_ai_matcher() -> None:
    """Close global AI matcher instance."""
    global _matcher_instance
    if _matcher_instance:
        _matcher_instance = None