"""
Document Processor for RAG Pipeline
Handles chunking, embedding, and indexing of documents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Generator

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for document chunking."""
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


class DocumentProcessor:
    """
    Process documents for RAG indexing.
    
    Handles:
    - Text chunking with overlap
    - Metadata extraction
    - Batch processing
    """
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()
        logger.info(f"DocumentProcessor initialized with chunk_size={self.config.chunk_size}")
    
    def chunk_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Split document into overlapping chunks.
        
        Args:
            doc_id: Document identifier
            content: Full document text
            metadata: Additional metadata to attach to chunks
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        metadata = metadata or {}
        
        # Split into sentences first for better boundaries
        sentences = self._split_sentences(content)
        
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        char_pos = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # Check if adding this sentence exceeds chunk size
            if len(current_chunk) + sentence_len > self.config.chunk_size and current_chunk:
                # Save current chunk
                if len(current_chunk.strip()) >= self.config.min_chunk_size:
                    chunks.append(DocumentChunk(
                        chunk_id=f"{doc_id}_chunk_{chunk_index}",
                        doc_id=doc_id,
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=char_pos,
                        metadata={**metadata, 'chunk_index': chunk_index},
                    ))
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + sentence
                current_start = char_pos - len(overlap_text)
            else:
                current_chunk += sentence
            
            char_pos += sentence_len
        
        # Don't forget the last chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= self.config.min_chunk_size:
            chunks.append(DocumentChunk(
                chunk_id=f"{doc_id}_chunk_{chunk_index}",
                doc_id=doc_id,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=char_pos,
                metadata={**metadata, 'chunk_index': chunk_index},
            ))
        
        logger.debug(f"Document {doc_id} split into {len(chunks)} chunks")
        return chunks
    
    def process_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> Generator[DocumentChunk, None, None]:
        """
        Process multiple documents and yield chunks.
        
        Args:
            documents: List of dicts with 'id', 'content', and optional 'metadata'
            
        Yields:
            DocumentChunk objects
        """
        for doc in documents:
            doc_id = doc.get('id', '')
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                continue
            
            chunks = self.chunk_document(doc_id, content, metadata)
            yield from chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s + ' ' for s in sentences if s.strip()]
    
    def _get_overlap(self, text: str) -> str:
        """Get overlap text from the end of a chunk."""
        words = text.split()
        overlap_words = self.config.chunk_overlap // 5  # Approximate words
        
        if len(words) <= overlap_words:
            return text
        
        return ' '.join(words[-overlap_words:]) + ' '
