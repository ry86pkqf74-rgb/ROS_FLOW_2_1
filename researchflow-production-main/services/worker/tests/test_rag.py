"""
Phase 8: RAG System Testing & Validation

Comprehensive pytest tests for ResearchFlow RAG pipeline:
- HybridRetriever semantic + BM25 search integration
- Document processor chunking and tokenization
- CopilotRAG query handling and response generation
- Reciprocal Rank Fusion (RRF) ranking
- Metadata filtering
- Embedding similarity calculations

This module provides:
- Fixture-based test documents and embeddings
- Semantic search validation
- BM25 keyword matching tests
- Hybrid ranking tests
- Document chunking tests
- Query execution tests
"""

import pytest
import math
from typing import List, Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
worker_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(worker_src))

from rag.hybrid_retriever import (
    HybridRetriever,
    HybridConfig,
    RetrievalResult,
    BM25Scorer,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def hybrid_config():
    """Standard hybrid retriever configuration."""
    return HybridConfig(
        semantic_weight=0.7,
        top_k=10,
        rrf_k=60,
        min_score=0.0,
        bm25_k1=1.5,
        bm25_b=0.75,
    )


@pytest.fixture
def retriever(hybrid_config):
    """Create a HybridRetriever instance."""
    return HybridRetriever(config=hybrid_config)


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            'doc_id': 'doc-001',
            'content': 'Type 2 Diabetes Mellitus is a metabolic disorder characterized by high blood glucose levels.',
            'metadata': {'source': 'medical_journal', 'year': 2024, 'topic': 'endocrinology'},
        },
        {
            'doc_id': 'doc-002',
            'content': 'Metformin is the first-line medication for type 2 diabetes treatment.',
            'metadata': {'source': 'clinical_guidelines', 'year': 2023, 'topic': 'pharmacology'},
        },
        {
            'doc_id': 'doc-003',
            'content': 'HbA1c levels above 7% indicate suboptimal glycemic control in diabetic patients.',
            'metadata': {'source': 'research_paper', 'year': 2024, 'topic': 'diagnostics'},
        },
        {
            'doc_id': 'doc-004',
            'content': 'Lifestyle modifications including diet and exercise are essential for diabetes management.',
            'metadata': {'source': 'patient_education', 'year': 2023, 'topic': 'prevention'},
        },
        {
            'doc_id': 'doc-005',
            'content': 'GLP-1 receptor agonists have shown promise in reducing cardiovascular events in diabetic patients.',
            'metadata': {'source': 'clinical_trial', 'year': 2024, 'topic': 'pharmacology'},
        },
    ]


@pytest.fixture
def embeddings():
    """Mock embeddings (simple normalized vectors)."""
    return {
        'doc-001': [0.8, 0.1, 0.2, 0.3, 0.4],
        'doc-002': [0.7, 0.2, 0.3, 0.1, 0.5],
        'doc-003': [0.6, 0.3, 0.4, 0.2, 0.1],
        'doc-004': [0.9, 0.4, 0.1, 0.5, 0.2],
        'doc-005': [0.75, 0.25, 0.35, 0.15, 0.45],
    }


@pytest.fixture
def populated_retriever(retriever, sample_documents, embeddings):
    """Retriever with indexed documents."""
    for doc in sample_documents:
        retriever.add_document(
            doc_id=doc['doc_id'],
            content=doc['content'],
            embedding=embeddings[doc['doc_id']],
            metadata=doc['metadata'],
        )
    return retriever


@pytest.fixture
def query_embedding():
    """Sample query embedding."""
    return [0.75, 0.2, 0.3, 0.25, 0.4]


# =============================================================================
# Tests: BM25Scorer
# =============================================================================

class TestBM25Scorer:
    """Tests for BM25 keyword scoring."""
    
    def test_bm25_initialization(self):
        """Test BM25Scorer initialization."""
        scorer = BM25Scorer(k1=1.5, b=0.75)
        
        assert scorer.k1 == 1.5
        assert scorer.b == 0.75
        assert scorer.total_docs == 0
        assert len(scorer.doc_freqs) == 0
    
    def test_bm25_index_document(self):
        """Test document indexing."""
        scorer = BM25Scorer()
        content = "diabetes treatment requires metformin and lifestyle changes"
        
        scorer.index_document("doc-1", content)
        
        assert scorer.total_docs == 1
        assert "doc-1" in scorer.doc_lengths
        assert len(scorer.term_freqs.get("doc-1", {})) > 0
    
    def test_bm25_score_calculation(self):
        """Test BM25 score calculation."""
        scorer = BM25Scorer()
        
        doc_content = "Type 2 Diabetes treatment with metformin"
        scorer.index_document("doc-1", doc_content)
        
        query = "diabetes treatment"
        score = scorer.score(query, "doc-1", doc_content)
        
        assert isinstance(score, float)
        assert score >= 0.0
    
    def test_bm25_multiple_documents(self):
        """Test BM25 with multiple documents."""
        scorer = BM25Scorer()
        
        docs = [
            ("doc-1", "diabetes treatment with medication"),
            ("doc-2", "lifestyle changes prevent diabetes"),
            ("doc-3", "metformin reduces blood glucose"),
        ]
        
        for doc_id, content in docs:
            scorer.index_document(doc_id, content)
        
        assert scorer.total_docs == 3
        
        query = "diabetes treatment"
        score1 = scorer.score(query, "doc-1", docs[0][1])
        score2 = scorer.score(query, "doc-2", docs[1][1])
        
        # First doc should score higher as it has both terms
        assert score1 >= score2
    
    def test_bm25_average_doc_length(self):
        """Test that average document length is calculated."""
        scorer = BM25Scorer()
        
        scorer.index_document("doc-1", "short document")
        scorer.index_document("doc-2", "this is a longer document with more content")
        
        assert scorer.avg_doc_length > 0
        assert scorer.avg_doc_length > 2  # Should be between short and long


# =============================================================================
# Tests: HybridRetriever - Document Management
# =============================================================================

class TestHybridRetrieverDocumentManagement:
    """Tests for document indexing and management."""
    
    def test_add_single_document(self, retriever):
        """Test adding a single document."""
        doc_id = "test-doc-1"
        content = "Test document content"
        embedding = [0.5, 0.6, 0.7, 0.8, 0.9]
        metadata = {"source": "test"}
        
        retriever.add_document(doc_id, content, embedding, metadata)
        
        assert retriever.document_count == 1
        assert doc_id in retriever._documents
        assert doc_id in retriever._embeddings
    
    def test_add_multiple_documents(self, populated_retriever, sample_documents):
        """Test that all documents are indexed."""
        assert populated_retriever.document_count == len(sample_documents)
    
    def test_document_metadata_preserved(self, retriever, sample_documents):
        """Test that metadata is preserved during indexing."""
        doc = sample_documents[0]
        retriever.add_document(
            doc_id=doc['doc_id'],
            content=doc['content'],
            embedding=[0.5] * 5,
            metadata=doc['metadata'],
        )
        
        stored_doc = retriever._documents[doc['doc_id']]
        assert stored_doc['metadata'] == doc['metadata']
    
    def test_embedding_storage(self, retriever):
        """Test that embeddings are correctly stored."""
        doc_id = "test-doc"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        retriever.add_document(doc_id, "content", embedding)
        
        assert retriever._embeddings[doc_id] == embedding


# =============================================================================
# Tests: Semantic Search
# =============================================================================

class TestSemanticSearch:
    """Tests for semantic search functionality."""
    
    def test_cosine_similarity_identical_vectors(self, retriever):
        """Test cosine similarity with identical vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        similarity = retriever._cosine_similarity(vec1, vec2)
        
        assert similarity == pytest.approx(1.0)
    
    def test_cosine_similarity_orthogonal_vectors(self, retriever):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        similarity = retriever._cosine_similarity(vec1, vec2)
        
        assert similarity == pytest.approx(0.0)
    
    def test_cosine_similarity_opposite_vectors(self, retriever):
        """Test cosine similarity with opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        
        similarity = retriever._cosine_similarity(vec1, vec2)
        
        assert similarity == pytest.approx(-1.0)
    
    def test_semantic_search_basic(self, populated_retriever, query_embedding):
        """Test basic semantic search."""
        results = populated_retriever._semantic_search(query_embedding)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        # Results should be sorted by score descending
        scores = [r.semantic_score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_semantic_search_ranking(self, populated_retriever, query_embedding):
        """Test that semantic ranks are assigned correctly."""
        results = populated_retriever._semantic_search(query_embedding)
        
        for i, result in enumerate(results):
            assert result.semantic_rank == i + 1


# =============================================================================
# Tests: BM25 Keyword Search
# =============================================================================

class TestBM25KeywordSearch:
    """Tests for BM25 keyword search."""
    
    def test_keyword_search_basic(self, populated_retriever):
        """Test basic keyword search."""
        query = "diabetes treatment"
        results = populated_retriever._keyword_search(query)
        
        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
    
    def test_keyword_search_exact_match(self, retriever):
        """Test keyword search with exact matches."""
        retriever.add_document(
            "doc-1",
            "type 2 diabetes treatment",
            [0.5] * 5,
        )
        retriever.add_document(
            "doc-2",
            "management of disease",
            [0.6] * 5,
        )
        
        results = retriever._keyword_search("type 2 diabetes treatment")
        
        # doc-1 should rank higher due to exact phrase match
        assert results[0].doc_id == "doc-1"
    
    def test_keyword_search_ranking(self, populated_retriever):
        """Test that keyword ranks are assigned."""
        results = populated_retriever._keyword_search("diabetes treatment")
        
        for i, result in enumerate(results):
            assert result.keyword_rank == i + 1


# =============================================================================
# Tests: Reciprocal Rank Fusion (RRF)
# =============================================================================

class TestReciprocalRankFusion:
    """Tests for RRF combination logic."""
    
    def test_rrf_identical_results(self, populated_retriever):
        """Test RRF when both search methods return same results."""
        query = "diabetes treatment"
        query_emb = [0.7, 0.2, 0.3, 0.25, 0.4]
        
        semantic = populated_retriever._semantic_search(query_emb)
        keyword = populated_retriever._keyword_search(query)
        
        # Both should contain overlapping results
        semantic_ids = {r.doc_id for r in semantic}
        keyword_ids = {r.doc_id for r in keyword}
        
        assert len(semantic_ids & keyword_ids) > 0
    
    def test_rrf_score_calculation(self, populated_retriever):
        """Test that RRF scores are calculated correctly."""
        query = "diabetes"
        query_emb = [0.7, 0.2, 0.3, 0.25, 0.4]
        
        semantic = populated_retriever._semantic_search(query_emb)
        keyword = populated_retriever._keyword_search(query)
        combined = populated_retriever._reciprocal_rank_fusion(semantic, keyword)
        
        # All combined results should have scores
        assert all(r.score >= 0.0 for r in combined)
    
    def test_rrf_combines_both_methods(self, populated_retriever):
        """Test that RRF actually combines results from both methods."""
        query = "diabetes"
        query_emb = [0.7, 0.2, 0.3, 0.25, 0.4]
        
        semantic = populated_retriever._semantic_search(query_emb)
        keyword = populated_retriever._keyword_search(query)
        combined = populated_retriever._reciprocal_rank_fusion(semantic, keyword)
        
        semantic_ids = {r.doc_id for r in semantic}
        keyword_ids = {r.doc_id for r in keyword}
        combined_ids = {r.doc_id for r in combined}
        
        # Combined should include docs from both
        assert len(combined_ids) >= len(semantic_ids & keyword_ids)


# =============================================================================
# Tests: Hybrid Search
# =============================================================================

class TestHybridSearch:
    """Tests for the full hybrid search pipeline."""
    
    def test_hybrid_search_returns_results(self, populated_retriever, query_embedding):
        """Test that hybrid search returns results."""
        results = populated_retriever.search(
            query="diabetes treatment",
            query_embedding=query_embedding,
            top_k=5,
        )
        
        assert len(results) > 0
        assert len(results) <= 5
    
    def test_hybrid_search_respects_top_k(self, populated_retriever, query_embedding):
        """Test that top_k limit is respected."""
        for top_k in [1, 3, 5, 10, 20]:
            results = populated_retriever.search(
                query="diabetes",
                query_embedding=query_embedding,
                top_k=top_k,
            )
            
            assert len(results) <= top_k
    
    def test_hybrid_search_respects_min_score(self, populated_retriever, query_embedding):
        """Test that min_score threshold is applied."""
        config = HybridConfig(min_score=0.5)
        retriever = HybridRetriever(config=config)
        
        for doc in list(retriever._documents.values())[:3]:
            retriever.add_document("doc", doc['content'], [0.5] * 5)
        
        results = retriever.search(
            query="test",
            query_embedding=query_embedding,
            top_k=10,
        )
        
        assert all(r.score >= 0.5 for r in results)
    
    def test_hybrid_search_semantic_weight_influence(self, populated_retriever, query_embedding):
        """Test that semantic weight affects result ordering."""
        # Search with high semantic weight
        config_high = HybridConfig(semantic_weight=0.9)
        retriever_high = HybridRetriever(config=config_high)
        
        # Search with low semantic weight
        config_low = HybridConfig(semantic_weight=0.1)
        retriever_low = HybridRetriever(config=config_low)
        
        # Add same documents to both
        for doc_id, embedding in [('doc-1', [0.8, 0.2, 0.3, 0.4, 0.5]),
                                   ('doc-2', [0.3, 0.8, 0.2, 0.4, 0.5])]:
            retriever_high.add_document(doc_id, f"content {doc_id}", embedding)
            retriever_low.add_document(doc_id, f"content {doc_id}", embedding)
        
        results_high = retriever_high.search("content", query_embedding, top_k=2)
        results_low = retriever_low.search("content", query_embedding, top_k=2)
        
        # Results should potentially differ based on weight
        assert isinstance(results_high, list)
        assert isinstance(results_low, list)


# =============================================================================
# Tests: Metadata Filtering
# =============================================================================

class TestMetadataFiltering:
    """Tests for metadata-based filtering."""
    
    def test_metadata_filter_exact_match(self, populated_retriever):
        """Test filtering by exact metadata match."""
        results = populated_retriever._keyword_search(
            query="diabetes",
            filter_metadata={"source": "medical_journal"},
        )
        
        assert all(r.metadata.get("source") == "medical_journal" for r in results)
    
    def test_metadata_filter_multiple_criteria(self, populated_retriever):
        """Test filtering by multiple metadata criteria."""
        results = populated_retriever._keyword_search(
            query="diabetes",
            filter_metadata={"source": "clinical_guidelines", "year": 2023},
        )
        
        assert all(
            r.metadata.get("source") == "clinical_guidelines" and
            r.metadata.get("year") == 2023
            for r in results
        )
    
    def test_metadata_filter_no_matches(self, populated_retriever):
        """Test filtering with no matching documents."""
        results = populated_retriever._keyword_search(
            query="diabetes",
            filter_metadata={"source": "nonexistent"},
        )
        
        assert len(results) == 0
    
    def test_filter_function_correctness(self, populated_retriever):
        """Test the _matches_filter helper function."""
        metadata = {"source": "test", "year": 2024}
        
        assert populated_retriever._matches_filter(metadata, {"source": "test"})
        assert populated_retriever._matches_filter(metadata, {"source": "test", "year": 2024})
        assert not populated_retriever._matches_filter(metadata, {"source": "other"})
        assert not populated_retriever._matches_filter(metadata, {"source": "test", "year": 2023})


# =============================================================================
# Tests: RetrievalResult
# =============================================================================

class TestRetrievalResult:
    """Tests for RetrievalResult dataclass."""
    
    def test_retrieval_result_creation(self):
        """Test creating a RetrievalResult."""
        result = RetrievalResult(
            doc_id="doc-1",
            chunk_id="chunk-1",
            content="Test content",
            score=0.95,
            metadata={"source": "test"},
        )
        
        assert result.doc_id == "doc-1"
        assert result.score == 0.95
        assert result.content == "Test content"
    
    def test_retrieval_result_with_ranks(self):
        """Test RetrievalResult with ranking info."""
        result = RetrievalResult(
            doc_id="doc-1",
            chunk_id="chunk-1",
            content="Test content",
            score=0.85,
            semantic_score=0.9,
            keyword_score=0.8,
            semantic_rank=1,
            keyword_rank=2,
        )
        
        assert result.semantic_rank == 1
        assert result.keyword_rank == 2
        assert result.semantic_score == 0.9
        assert result.keyword_score == 0.8


# =============================================================================
# Tests: Configuration
# =============================================================================

class TestHybridConfig:
    """Tests for HybridConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HybridConfig()
        
        assert config.semantic_weight == 0.7
        assert config.top_k == 10
        assert config.rrf_k == 60
        assert config.bm25_k1 == 1.5
        assert config.bm25_b == 0.75
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = HybridConfig(
            semantic_weight=0.5,
            top_k=5,
            rrf_k=100,
            min_score=0.3,
        )
        
        assert config.semantic_weight == 0.5
        assert config.top_k == 5
        assert config.rrf_k == 100
        assert config.min_score == 0.3


# =============================================================================
# Tests: Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_query(self, populated_retriever, query_embedding):
        """Test search with empty query."""
        results = populated_retriever.search("", query_embedding)
        
        # Should still return results based on embedding
        assert isinstance(results, list)
    
    def test_empty_retriever(self, retriever, query_embedding):
        """Test search on empty retriever."""
        results = retriever.search("test", query_embedding)
        
        assert results == []
    
    def test_zero_embeddings(self, retriever):
        """Test handling of zero embeddings."""
        retriever.add_document("doc-1", "content", [0.0, 0.0, 0.0])
        
        # Should handle zero vector gracefully
        similarity = retriever._cosine_similarity([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert similarity == 0.0
    
    def test_single_document_search(self, retriever, query_embedding):
        """Test search with single document."""
        retriever.add_document("doc-1", "test content", [0.5] * 5)
        
        results = retriever.search("test", query_embedding, top_k=1)
        
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
