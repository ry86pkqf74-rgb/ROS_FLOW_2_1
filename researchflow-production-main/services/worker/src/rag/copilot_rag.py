"""
Copilot RAG Integration for ResearchFlow
Enhances PDF Copilot with hybrid retrieval.
"""

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .hybrid_retriever import HybridRetriever, HybridConfig, RetrievalResult
from .document_processor import DocumentProcessor, ChunkConfig

logger = logging.getLogger(__name__)


@dataclass
class CopilotResponse:
    """Response from the Copilot RAG system."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_results: List[RetrievalResult]


class CopilotRAG:
    """
    RAG-enhanced Copilot for research paper Q&A.
    
    Integrates:
    - Document chunking and embedding
    - Hybrid retrieval (semantic + keyword)
    - Context augmentation for LLM
    """
    
    def __init__(
        self,
        embedding_provider: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
        hybrid_config: Optional[HybridConfig] = None,
        chunk_config: Optional[ChunkConfig] = None,
    ):
        self.retriever = HybridRetriever(hybrid_config)
        self.processor = DocumentProcessor(chunk_config)
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        
        self._indexed_papers: Dict[str, bool] = {}
        
        logger.info("CopilotRAG initialized")
    
    async def index_paper(
        self,
        paper_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Index a research paper for retrieval.
        
        Args:
            paper_id: Unique paper identifier
            content: Full paper text
            metadata: Additional metadata (title, authors, etc.)
            
        Returns:
            Number of chunks indexed
        """
        if paper_id in self._indexed_papers:
            logger.info(f"Paper {paper_id} already indexed, skipping")
            return 0
        
        metadata = metadata or {}
        metadata['paper_id'] = paper_id
        
        # Chunk the document
        chunks = self.processor.chunk_document(paper_id, content, metadata)
        
        # Generate embeddings
        if self.embedding_provider:
            chunk_texts = [c.content for c in chunks]
            embeddings = await self._generate_embeddings(chunk_texts)
        else:
            # Fallback: use dummy embeddings for testing
            embeddings = [[0.0] * 1536 for _ in chunks]
        
        # Index chunks
        for chunk, embedding in zip(chunks, embeddings):
            self.retriever.add_document(
                doc_id=chunk.chunk_id,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
            )
        
        self._indexed_papers[paper_id] = True
        logger.info(f"Indexed paper {paper_id} with {len(chunks)} chunks")
        
        return len(chunks)
    
    async def query(
        self,
        paper_id: str,
        question: str,
        top_k: int = 5,
    ) -> CopilotResponse:
        """
        Answer a question about a paper using RAG.
        
        Args:
            paper_id: Paper to query
            question: User's question
            top_k: Number of chunks to retrieve
            
        Returns:
            CopilotResponse with answer and sources
        """
        # Generate query embedding
        if self.embedding_provider:
            query_embedding = (await self._generate_embeddings([question]))[0]
        else:
            query_embedding = [0.0] * 1536
        
        # Retrieve relevant chunks
        results = self.retriever.search(
            query=question,
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata={'paper_id': paper_id},
        )
        
        if not results:
            return CopilotResponse(
                answer="I couldn't find relevant information in this paper to answer your question.",
                sources=[],
                confidence=0.0,
                retrieval_results=[],
            )
        
        # Build context from retrieved chunks
        context = self._build_context(results)
        
        # Generate answer using LLM
        if self.llm_provider:
            answer = await self._generate_answer(question, context)
        else:
            answer = f"Based on the retrieved context, here is what I found:\n\n{context[:500]}..."
        
        # Calculate confidence based on retrieval scores
        avg_score = sum(r.score for r in results) / len(results)
        confidence = min(avg_score * 10, 1.0)  # Normalize to 0-1
        
        # Format sources
        sources = [
            {
                'chunk_id': r.chunk_id,
                'content': r.content[:200] + '...' if len(r.content) > 200 else r.content,
                'score': r.score,
                'metadata': r.metadata,
            }
            for r in results
        ]
        
        return CopilotResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            retrieval_results=results,
        )
    
    def _build_context(self, results: List[RetrievalResult]) -> str:
        """Build context string from retrieval results."""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            context_parts.append(f"[Source {i}]\n{result.content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the configured provider."""
        if hasattr(self.embedding_provider, 'embed'):
            result = self.embedding_provider.embed(texts)
            return result.embeddings
        elif hasattr(self.embedding_provider, 'embed_documents'):
            return self.embedding_provider.embed_documents(texts)
        else:
            raise ValueError("Embedding provider must have 'embed' or 'embed_documents' method")
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using the configured LLM."""
        prompt = f"""Based on the following context from a research paper, answer the question.
        
Context:
{context}

Question: {question}

Answer:"""
        
        if hasattr(self.llm_provider, 'generate'):
            return await self.llm_provider.generate(prompt)
        elif hasattr(self.llm_provider, 'complete'):
            return await self.llm_provider.complete(prompt)
        else:
            return f"LLM provider not properly configured. Context retrieved: {len(context)} chars"
    
    @property
    def indexed_paper_count(self) -> int:
        """Number of indexed papers."""
        return len(self._indexed_papers)
    
    @property
    def total_chunks(self) -> int:
        """Total number of indexed chunks."""
        return self.retriever.document_count
