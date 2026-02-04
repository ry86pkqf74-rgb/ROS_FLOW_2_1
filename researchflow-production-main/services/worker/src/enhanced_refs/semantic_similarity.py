"""
Semantic Similarity Engine for Reference Management

Advanced AI-powered reference matching using semantic embeddings,
contextual understanding, and intelligent relevance scoring.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

from .reference_types import Reference, CitationNeed
from .reference_cache import get_cache
from .api_management import get_api_manager

logger = logging.getLogger(__name__)

@dataclass
class SemanticMatch:
    """Represents a semantic match between citation need and reference."""
    reference: Reference
    similarity_score: float
    context_relevance: float
    semantic_distance: float
    matching_concepts: List[str]
    confidence: float
    explanation: str

class SemanticSimilarityEngine:
    """
    Advanced semantic similarity engine for intelligent reference matching.
    
    Uses contextual embeddings, concept extraction, and multi-dimensional
    similarity scoring to find the most relevant references for citations.
    """
    
    def __init__(self):
        self.cache = None
        self.api_manager = None
        self.embedding_cache = {}
        self.concept_cache = {}
        self.stats = {
            'similarity_computations': 0,
            'embedding_generations': 0,
            'cache_hits': 0,
            'successful_matches': 0
        }
    
    async def initialize(self):
        """Initialize the semantic similarity engine."""
        self.cache = await get_cache()
        self.api_manager = await get_api_manager()
        logger.info("Semantic similarity engine initialized")
    
    async def find_semantic_matches(
        self, 
        citation_need: CitationNeed, 
        references: List[Reference],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[SemanticMatch]:
        """
        Find semantically similar references for a citation need.
        
        Args:
            citation_need: The citation need to match
            references: Pool of references to search
            top_k: Maximum number of matches to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of semantic matches ordered by relevance
        """
        self.stats['similarity_computations'] += 1
        
        if not references:
            return []
        
        # Get semantic embedding for citation need
        need_embedding = await self._get_citation_embedding(citation_need)
        need_concepts = await self._extract_concepts(citation_need.context)
        
        matches = []
        
        for reference in references:
            try:
                # Compute semantic similarity
                ref_embedding = await self._get_reference_embedding(reference)
                semantic_score = await self._compute_semantic_similarity(need_embedding, ref_embedding)
                
                # Compute contextual relevance
                ref_concepts = await self._extract_concepts(f"{reference.title} {reference.abstract or ''}")
                context_score = await self._compute_context_relevance(citation_need, reference, need_concepts, ref_concepts)
                
                # Compute overall similarity
                overall_score = self._combine_similarity_scores(semantic_score, context_score, citation_need, reference)
                
                if overall_score >= min_similarity:
                    matching_concepts = list(set(need_concepts).intersection(set(ref_concepts)))
                    
                    match = SemanticMatch(
                        reference=reference,
                        similarity_score=overall_score,
                        context_relevance=context_score,
                        semantic_distance=1.0 - semantic_score,
                        matching_concepts=matching_concepts,
                        confidence=self._calculate_match_confidence(semantic_score, context_score, matching_concepts),
                        explanation=self._generate_match_explanation(citation_need, reference, semantic_score, context_score, matching_concepts)
                    )
                    
                    matches.append(match)
                    
            except Exception as e:
                logger.warning(f"Failed to compute similarity for reference {reference.id}: {e}")
        
        # Sort by similarity score and return top matches
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        result = matches[:top_k]
        
        if result:
            self.stats['successful_matches'] += 1
        
        return result
    
    async def _get_citation_embedding(self, citation_need: CitationNeed) -> np.ndarray:
        """Get semantic embedding for citation need."""
        text = f"{citation_need.text_snippet} {citation_need.context}"
        return await self._get_text_embedding(text, f"citation_{citation_need.id}")
    
    async def _get_reference_embedding(self, reference: Reference) -> np.ndarray:
        """Get semantic embedding for reference."""
        text = f"{reference.title} {reference.abstract or ''}"
        return await self._get_text_embedding(text, f"reference_{reference.id}")
    
    async def _get_text_embedding(self, text: str, cache_key: str) -> np.ndarray:
        """
        Get semantic embedding for text using caching.
        
        In production, this would use models like:
        - OpenAI text-embedding-ada-002
        - sentence-transformers/all-MiniLM-L6-v2
        - PubMedBERT for medical texts
        """
        
        # Check cache first
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        # Check persistent cache
        if self.cache:
            cached_embedding = await self.cache.get('embeddings', cache_key)
            if cached_embedding:
                self.stats['cache_hits'] += 1
                embedding = np.array(cached_embedding)
                self.embedding_cache[cache_key] = embedding
                return embedding
        
        # Generate embedding (mock implementation)
        embedding = await self._generate_mock_embedding(text)
        
        # Cache the embedding
        self.embedding_cache[cache_key] = embedding
        if self.cache:
            await self.cache.set('embeddings', cache_key, embedding.tolist(), ttl_override=7*24*3600)
        
        self.stats['embedding_generations'] += 1
        return embedding
    
    async def _generate_mock_embedding(self, text: str) -> np.ndarray:
        """
        Generate mock embedding based on text characteristics.
        In production, replace with actual embedding model.
        """
        # Simple hash-based embedding for demonstration
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hex to numbers and normalize
        embedding = np.array([int(text_hash[i:i+2], 16) for i in range(0, min(64, len(text_hash)), 2)])
        
        # Normalize to unit vector
        embedding = embedding / np.linalg.norm(embedding) if np.linalg.norm(embedding) > 0 else embedding
        
        # Add some text-based features
        text_lower = text.lower()
        features = np.array([
            len(text) / 1000,  # Length feature
            text_lower.count('study') / 100,  # Study mentions
            text_lower.count('result') / 100,  # Result mentions  
            text_lower.count('method') / 100,  # Method mentions
            text_lower.count('patient') / 100,  # Patient mentions
            text_lower.count('treatment') / 100,  # Treatment mentions
            text_lower.count('analysis') / 100,  # Analysis mentions
            text_lower.count('significant') / 100,  # Significance mentions
        ])
        
        # Combine hash embedding with features
        combined = np.concatenate([embedding[:24], features])
        return combined / np.linalg.norm(combined) if np.linalg.norm(combined) > 0 else combined
    
    async def _compute_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings."""
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0
            
        # Ensure same dimensions
        min_dim = min(len(embedding1), len(embedding2))
        emb1 = embedding1[:min_dim]
        emb2 = embedding2[:min_dim]
        
        # Compute cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, similarity)  # Ensure non-negative
    
    async def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text."""
        if not text:
            return []
        
        text_lower = text.lower()
        
        # Medical and research concepts
        medical_concepts = [
            'diagnosis', 'treatment', 'therapy', 'patient', 'clinical', 'trial',
            'outcome', 'efficacy', 'safety', 'intervention', 'randomized',
            'placebo', 'control', 'cohort', 'mortality', 'morbidity',
            'prevalence', 'incidence', 'risk', 'factor', 'association'
        ]
        
        research_concepts = [
            'hypothesis', 'methodology', 'analysis', 'statistical', 'significant',
            'correlation', 'regression', 'meta-analysis', 'systematic review',
            'observational', 'experimental', 'longitudinal', 'cross-sectional'
        ]
        
        domain_concepts = [
            'cardiovascular', 'oncology', 'neurology', 'psychiatry', 'surgery',
            'pediatric', 'geriatric', 'infectious', 'chronic', 'acute',
            'inflammation', 'immune', 'genetic', 'molecular', 'biomarker'
        ]
        
        all_concepts = medical_concepts + research_concepts + domain_concepts
        
        found_concepts = []
        for concept in all_concepts:
            if concept in text_lower:
                found_concepts.append(concept)
        
        # Extract numerical concepts
        import re
        numbers = re.findall(r'\d+%|\d+\.\d+', text)
        if numbers:
            found_concepts.extend(['quantitative_data', 'statistical_result'])
        
        return list(set(found_concepts))
    
    async def _compute_context_relevance(
        self, 
        citation_need: CitationNeed, 
        reference: Reference,
        need_concepts: List[str],
        ref_concepts: List[str]
    ) -> float:
        """Compute contextual relevance between citation need and reference."""
        
        relevance_score = 0.0
        
        # Concept overlap
        if need_concepts and ref_concepts:
            common_concepts = set(need_concepts).intersection(set(ref_concepts))
            concept_overlap = len(common_concepts) / len(set(need_concepts + ref_concepts))
            relevance_score += concept_overlap * 0.4
        
        # Claim type matching
        claim_relevance = await self._assess_claim_type_relevance(citation_need.claim_type, reference)
        relevance_score += claim_relevance * 0.3
        
        # Section relevance
        section_relevance = await self._assess_section_relevance(citation_need.section, reference)
        relevance_score += section_relevance * 0.2
        
        # Temporal relevance (more recent = more relevant, generally)
        if reference.year:
            current_year = datetime.now().year
            years_old = current_year - reference.year
            temporal_score = max(0, 1.0 - years_old / 20)  # Decay over 20 years
            relevance_score += temporal_score * 0.1
        
        return min(relevance_score, 1.0)
    
    async def _assess_claim_type_relevance(self, claim_type: str, reference: Reference) -> float:
        """Assess how well reference supports the claim type."""
        
        ref_text = f"{reference.title} {reference.abstract or ''}".lower()
        
        claim_indicators = {
            'statistical_fact': ['significant', 'p <', 'p=', '%', 'odds ratio', 'confidence interval', 'statistic'],
            'prior_research': ['study', 'research', 'found', 'showed', 'demonstrated', 'reported'],
            'methodology': ['method', 'procedure', 'technique', 'approach', 'protocol', 'analysis'],
            'clinical_guideline': ['guideline', 'recommendation', 'standard', 'protocol', 'consensus'],
            'definition': ['defined', 'definition', 'characterized', 'described as'],
            'background_info': ['background', 'context', 'overview', 'review']
        }
        
        indicators = claim_indicators.get(claim_type, [])
        matches = sum(1 for indicator in indicators if indicator in ref_text)
        
        return min(matches / len(indicators), 1.0) if indicators else 0.5
    
    async def _assess_section_relevance(self, section: str, reference: Reference) -> float:
        """Assess relevance based on manuscript section."""
        
        ref_text = f"{reference.title} {reference.abstract or ''}".lower()
        
        section_preferences = {
            'introduction': ['background', 'review', 'overview', 'context'],
            'methods': ['method', 'procedure', 'technique', 'protocol', 'analysis'],
            'results': ['result', 'finding', 'outcome', 'data', 'significant'],
            'discussion': ['discussion', 'implication', 'interpretation', 'limitation'],
            'conclusion': ['conclusion', 'summary', 'future', 'recommendation']
        }
        
        preferences = section_preferences.get(section, [])
        matches = sum(1 for pref in preferences if pref in ref_text)
        
        return min(matches / len(preferences), 1.0) if preferences else 0.5
    
    def _combine_similarity_scores(
        self, 
        semantic_score: float, 
        context_score: float,
        citation_need: CitationNeed,
        reference: Reference
    ) -> float:
        """Combine different similarity scores into overall score."""
        
        # Base combination
        base_score = 0.6 * semantic_score + 0.4 * context_score
        
        # Boost for high-quality references
        quality_boost = 0.0
        if reference.citation_count and reference.citation_count > 50:
            quality_boost += 0.1
        if reference.doi:
            quality_boost += 0.05
        if reference.journal and 'nature' in reference.journal.lower():
            quality_boost += 0.1
        
        # Boost for urgency
        urgency_boost = 0.05 if citation_need.urgency == 'high' else 0.0
        
        # Penalize very old references for certain claim types
        age_penalty = 0.0
        if reference.year and citation_need.claim_type in ['statistical_fact', 'clinical_guideline']:
            years_old = datetime.now().year - reference.year
            if years_old > 10:
                age_penalty = 0.1
        
        final_score = base_score + quality_boost + urgency_boost - age_penalty
        return max(0.0, min(1.0, final_score))
    
    def _calculate_match_confidence(
        self, 
        semantic_score: float, 
        context_score: float, 
        matching_concepts: List[str]
    ) -> float:
        """Calculate confidence in the match."""
        
        # High confidence if both scores are high
        score_confidence = min(semantic_score, context_score)
        
        # Boost confidence with concept matches
        concept_confidence = min(len(matching_concepts) / 5, 1.0)
        
        # Combined confidence
        return 0.7 * score_confidence + 0.3 * concept_confidence
    
    def _generate_match_explanation(
        self,
        citation_need: CitationNeed,
        reference: Reference,
        semantic_score: float,
        context_score: float,
        matching_concepts: List[str]
    ) -> str:
        """Generate human-readable explanation for the match."""
        
        explanations = []
        
        # Semantic similarity
        if semantic_score > 0.8:
            explanations.append("Very high semantic similarity to citation context")
        elif semantic_score > 0.6:
            explanations.append("Good semantic similarity to citation context")
        
        # Context relevance
        if context_score > 0.7:
            explanations.append(f"Highly relevant for {citation_need.claim_type} claims")
        
        # Concept matches
        if matching_concepts:
            explanations.append(f"Shares key concepts: {', '.join(matching_concepts[:3])}")
        
        # Reference quality
        if reference.citation_count and reference.citation_count > 100:
            explanations.append("High-impact reference (>100 citations)")
        
        # Journal prestige
        if reference.journal and any(journal in reference.journal.lower() 
                                   for journal in ['nature', 'science', 'cell', 'lancet', 'nejm']):
            explanations.append("Published in prestigious journal")
        
        if not explanations:
            explanations.append("Moderate relevance based on content analysis")
        
        return ". ".join(explanations)
    
    async def batch_find_matches(
        self, 
        citation_needs: List[CitationNeed], 
        references: List[Reference],
        top_k: int = 3
    ) -> Dict[str, List[SemanticMatch]]:
        """Efficiently find matches for multiple citation needs."""
        
        results = {}
        
        # Pre-compute all reference embeddings
        ref_embeddings = {}
        for ref in references:
            ref_embeddings[ref.id] = await self._get_reference_embedding(ref)
        
        # Find matches for each citation need
        for need in citation_needs:
            matches = await self.find_semantic_matches(need, references, top_k)
            results[need.id] = matches
        
        return results
    
    async def get_stats(self) -> Dict[str, any]:
        """Get semantic similarity engine statistics."""
        cache_size = len(self.embedding_cache)
        hit_rate = (self.stats['cache_hits'] / max(self.stats['embedding_generations'], 1)) * 100
        
        return {
            **self.stats,
            'embedding_cache_size': cache_size,
            'cache_hit_rate_percent': hit_rate,
            'average_matches_per_need': self.stats['successful_matches'] / max(self.stats['similarity_computations'], 1)
        }

# Global semantic similarity engine instance
_semantic_engine_instance: Optional[SemanticSimilarityEngine] = None

async def get_semantic_similarity_engine() -> SemanticSimilarityEngine:
    """Get global semantic similarity engine instance."""
    global _semantic_engine_instance
    if _semantic_engine_instance is None:
        _semantic_engine_instance = SemanticSimilarityEngine()
        await _semantic_engine_instance.initialize()
    return _semantic_engine_instance

async def close_semantic_similarity_engine() -> None:
    """Close global semantic similarity engine instance."""
    global _semantic_engine_instance
    if _semantic_engine_instance:
        _semantic_engine_instance = None