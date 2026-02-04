"""
Hybrid Retriever for ResearchFlow RAG Pipeline
Combines semantic vector search with BM25 keyword matching.

Architecture:
    Query -> [Semantic Search] + [BM25 Keyword] -> Reciprocal Rank Fusion -> Results
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Single retrieval result with metadata."""
    doc_id: str
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Source tracking for hybrid retrieval
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    semantic_rank: Optional[int] = None
    keyword_rank: Optional[int] = None


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval."""
    semantic_weight: float = 0.7  # Weight for semantic vs keyword (0-1)
    top_k: int = 10  # Number of results to return
    rrf_k: int = 60  # Reciprocal Rank Fusion constant
    min_score: float = 0.0  # Minimum score threshold
    
    # BM25 parameters
    bm25_k1: float = 1.5
    bm25_b: float = 0.75


class BM25Scorer:
    """BM25 keyword scoring implementation."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.term_freqs: Dict[str, Dict[str, int]] = {}
        self.total_docs: int = 0
        
    def index_document(self, doc_id: str, content: str) -> None:
        """Index a document for BM25 scoring."""
        terms = self._tokenize(content)
        self.doc_lengths[doc_id] = len(terms)
        self.total_docs += 1
        
        # Update average document length
        total_length = sum(self.doc_lengths.values())
        self.avg_doc_length = total_length / self.total_docs
        
        # Track term frequencies
        term_counts: Dict[str, int] = defaultdict(int)
        seen_terms = set()
        
        for term in terms:
            term_counts[term] += 1
            if term not in seen_terms:
                self.doc_freqs[term] += 1
                seen_terms.add(term)
        
        self.term_freqs[doc_id] = dict(term_counts)
    
    def score(self, query: str, doc_id: str, content: str) -> float:
        """Calculate BM25 score for a document."""
        if doc_id not in self.term_freqs:
            self.index_document(doc_id, content)
        
        query_terms = self._tokenize(query)
        doc_length = self.doc_lengths.get(doc_id, len(content.split()))
        term_freqs = self.term_freqs.get(doc_id, {})
        
        score = 0.0
        for term in query_terms:
            if term not in term_freqs:
                continue
                
            tf = term_freqs[term]
            df = self.doc_freqs.get(term, 1)
            
            # IDF calculation
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)
            
            # TF normalization
            tf_norm = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * (doc_length / max(self.avg_doc_length, 1)))
            )
            
            score += idf * tf_norm
        
        return score
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - lowercase and split."""
        return text.lower().split()


class HybridRetriever:
    """
    Hybrid retrieval combining semantic and keyword search.
    
    Uses Reciprocal Rank Fusion (RRF) to combine rankings from
    both retrieval methods.
    """
    
    def __init__(self, config: Optional[HybridConfig] = None):
        self.config = config or HybridConfig()
        self.bm25 = BM25Scorer(k1=self.config.bm25_k1, b=self.config.bm25_b)
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Dict[str, List[float]] = {}
        
        logger.info(f"HybridRetriever initialized with config: {self.config}")
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a document to the retriever index."""
        self._documents[doc_id] = {
            'content': content,
            'metadata': metadata or {},
        }
        self._embeddings[doc_id] = embedding
        self.bm25.index_document(doc_id, content)
        
        logger.debug(f"Added document {doc_id} to index")
    
    def search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Perform hybrid search combining semantic and keyword retrieval.
        
        Args:
            query: Search query text
            query_embedding: Pre-computed query embedding
            top_k: Number of results (defaults to config.top_k)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of RetrievalResult ordered by combined score
        """
        top_k = top_k or self.config.top_k
        
        # Get semantic search results
        semantic_results = self._semantic_search(query_embedding, filter_metadata)
        
        # Get BM25 keyword results  
        keyword_results = self._keyword_search(query, filter_metadata)
        
        # Combine using Reciprocal Rank Fusion
        combined = self._reciprocal_rank_fusion(semantic_results, keyword_results)
        
        # Filter and return top_k
        results = [r for r in combined if r.score >= self.config.min_score]
        return results[:top_k]
    
    def _semantic_search(
        self,
        query_embedding: List[float],
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Perform semantic search using cosine similarity."""
        results = []
        
        for doc_id, embedding in self._embeddings.items():
            doc_data = self._documents.get(doc_id, {})
            
            # Apply metadata filter
            if filter_metadata and not self._matches_filter(doc_data.get('metadata', {}), filter_metadata):
                continue
            
            score = self._cosine_similarity(query_embedding, embedding)
            
            results.append(RetrievalResult(
                doc_id=doc_id,
                chunk_id=doc_id,
                content=doc_data.get('content', ''),
                score=score,
                metadata=doc_data.get('metadata', {}),
                semantic_score=score,
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, result in enumerate(results):
            result.semantic_rank = i + 1
        
        return results
    
    def _keyword_search(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Perform BM25 keyword search."""
        results = []
        
        for doc_id, doc_data in self._documents.items():
            # Apply metadata filter
            if filter_metadata and not self._matches_filter(doc_data.get('metadata', {}), filter_metadata):
                continue
            
            content = doc_data.get('content', '')
            score = self.bm25.score(query, doc_id, content)
            
            results.append(RetrievalResult(
                doc_id=doc_id,
                chunk_id=doc_id,
                content=content,
                score=score,
                metadata=doc_data.get('metadata', {}),
                keyword_score=score,
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks
        for i, result in enumerate(results):
            result.keyword_rank = i + 1
        
        return results
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Combine results using Reciprocal Rank Fusion.
        
        RRF score = sum(1 / (k + rank)) for each ranking
        """
        k = self.config.rrf_k
        semantic_weight = self.config.semantic_weight
        keyword_weight = 1.0 - semantic_weight
        
        # Build lookup maps
        semantic_map = {r.doc_id: r for r in semantic_results}
        keyword_map = {r.doc_id: r for r in keyword_results}
        
        # Get all unique doc_ids
        all_doc_ids = set(semantic_map.keys()) | set(keyword_map.keys())
        
        # Calculate RRF scores
        combined_results = []
        
        for doc_id in all_doc_ids:
            semantic_result = semantic_map.get(doc_id)
            keyword_result = keyword_map.get(doc_id)
            
            rrf_score = 0.0
            
            if semantic_result and semantic_result.semantic_rank:
                rrf_score += semantic_weight * (1.0 / (k + semantic_result.semantic_rank))
            
            if keyword_result and keyword_result.keyword_rank:
                rrf_score += keyword_weight * (1.0 / (k + keyword_result.keyword_rank))
            
            # Use semantic result as base if available, else keyword
            base_result = semantic_result or keyword_result
            
            combined_results.append(RetrievalResult(
                doc_id=doc_id,
                chunk_id=base_result.chunk_id,
                content=base_result.content,
                score=rrf_score,
                metadata=base_result.metadata,
                semantic_score=semantic_result.semantic_score if semantic_result else None,
                keyword_score=keyword_result.keyword_score if keyword_result else None,
                semantic_rank=semantic_result.semantic_rank if semantic_result else None,
                keyword_rank=keyword_result.keyword_rank if keyword_result else None,
            ))
        
        # Sort by combined RRF score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        return combined_results
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filter_metadata: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_metadata.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    @property
    def document_count(self) -> int:
        """Number of indexed documents."""
        return len(self._documents)
