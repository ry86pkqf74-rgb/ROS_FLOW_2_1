"""
RAG (Retrieval-Augmented Generation) Pipeline for ResearchFlow
Phase 4: Hybrid Retrieval Implementation

Combines semantic search with BM25 keyword matching for improved retrieval.
"""

from .hybrid_retriever import HybridRetriever, RetrievalResult
from .document_processor import DocumentProcessor
from .copilot_rag import CopilotRAG

__all__ = [
    'HybridRetriever',
    'RetrievalResult', 
    'DocumentProcessor',
    'CopilotRAG',
]
