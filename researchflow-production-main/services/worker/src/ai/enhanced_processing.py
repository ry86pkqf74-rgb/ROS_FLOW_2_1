"""
Enhanced AI Processing Module
Provides comprehensive AI functionality including semantic search, text embeddings,
and enhanced literature matching using sentence-transformers and transformers.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

import numpy as np
import pandas as pd

# PHI scanning import
try:
    from validation.phi_detector import PHIDetector
    HAS_PHI_SCANNER = True
except ImportError:
    HAS_PHI_SCANNER = False
    logging.warning("PHI detector not available - PHI scanning disabled")

# Core AI imports with fallback handling
try:
    from sentence_transformers import SentenceTransformer
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    HAS_AI_PACKAGES = True
except ImportError as e:
    logging.warning(f"AI packages not available: {e}")
    HAS_AI_PACKAGES = False

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result from text embedding operation"""
    text: str
    embedding: np.ndarray
    model_name: str
    processing_time: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class SimilarityResult:
    """Result from similarity search operation"""
    query: str
    matches: List[Dict[str, Any]]
    scores: List[float]
    model_name: str
    processing_time: float

class EnhancedAIProcessor:
    """
    Enhanced AI processor combining sentence-transformers, transformers,
    and other AI models for comprehensive text processing.
    """
    
    def __init__(self, config: Optional[Dict] = None, enable_phi_scan: bool = True):
        """Initialize the AI processor with optional configuration
        
        Args:
            config: Optional configuration dictionary
            enable_phi_scan: Enable PHI scanning before processing (default: True)
        """
        self.config = config or self._get_default_config()
        self.models = {}
        self.embeddings_cache = {}
        self._initialized = False
        self.enable_phi_scan = enable_phi_scan and HAS_PHI_SCANNER
        self._phi_detector = PHIDetector() if self.enable_phi_scan else None
        self._audit_log_entries: List[Dict[str, Any]] = []
        
        # Check if AI packages are available
        if not HAS_AI_PACKAGES:
            logger.warning("AI packages not available. Enhanced processing disabled.")
            return
            
        # Models will be initialized on first use
        self._initialization_started = False
        self._audit_log("AI processor initialized", {"phi_scan_enabled": self.enable_phi_scan})
    
    def _get_default_config(self) -> Dict:
        """Get default configuration for AI processing"""
        return {
            "sentence_transformer_model": "all-MiniLM-L6-v2",
            "clinical_model": "emilyalsentzer/Bio_ClinicalBERT",
            "similarity_threshold": 0.7,
            "max_sequence_length": 512,
            "batch_size": 32,
            "use_gpu": torch.cuda.is_available() if HAS_AI_PACKAGES else False,
            "cache_embeddings": True,
            "models_to_load": ["sentence_transformer", "clinical_ner"]
        }
    
    async def _initialize_models(self):
        """Initialize AI models asynchronously"""
        if not HAS_AI_PACKAGES:
            return
            
        try:
            # Initialize sentence transformer
            if "sentence_transformer" in self.config["models_to_load"]:
                model_name = self.config["sentence_transformer_model"]
                logger.info(f"Loading sentence transformer: {model_name}")
                
                device = "cuda" if self.config["use_gpu"] else "cpu"
                self.models["sentence_transformer"] = SentenceTransformer(
                    model_name, device=device
                )
                logger.info(f"Sentence transformer loaded on {device}")
            
            # Initialize clinical NER pipeline
            if "clinical_ner" in self.config["models_to_load"]:
                try:
                    self.models["clinical_ner"] = pipeline(
                        "ner",
                        model=self.config["clinical_model"],
                        aggregation_strategy="simple",
                        device=0 if self.config["use_gpu"] else -1
                    )
                    logger.info("Clinical NER model loaded")
                except Exception as e:
                    logger.warning(f"Could not load clinical model: {e}")
                    # Fallback to general NER
                    self.models["clinical_ner"] = pipeline(
                        "ner",
                        model="dbmdz/bert-large-cased-finetuned-conll03-english",
                        aggregation_strategy="simple",
                        device=0 if self.config["use_gpu"] else -1
                    )
            
            self._initialized = True
            logger.info("Enhanced AI processor initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI models: {e}")
            self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure models are initialized before use"""
        if not self._initialization_started and HAS_AI_PACKAGES:
            self._initialization_started = True
            await self._initialize_models()
    
    def is_ready(self) -> bool:
        """Check if the processor is ready for use"""
        return HAS_AI_PACKAGES and self._initialized
    
    def _audit_log(self, action: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log audit trail entry for compliance
        
        Args:
            action: Description of the action
            metadata: Additional metadata for the audit entry
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "metadata": metadata or {}
        }
        self._audit_log_entries.append(entry)
        logger.info(f"AUDIT: {action}", extra=metadata or {})
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log entries
        
        Returns:
            List of audit log entries
        """
        return self._audit_log_entries.copy()
    
    def _scan_for_phi(self, texts: Union[str, List[str]]) -> Dict[str, Any]:
        """Scan text(s) for PHI before processing
        
        Args:
            texts: Single text or list of texts to scan
            
        Returns:
            Dictionary with scan results
        """
        if not self.enable_phi_scan or not self._phi_detector:
            return {"phi_detected": False, "scan_enabled": False}
        
        text_list = [texts] if isinstance(texts, str) else texts
        
        for text in text_list:
            detections = self._phi_detector.scan_value(str(text))
            if detections:
                phi_types = [str(phi_type.value) for phi_type, _ in detections]
                self._audit_log("PHI detected in input", {
                    "phi_types": phi_types,
                    "text_length": len(text)
                })
                return {
                    "phi_detected": True,
                    "phi_types": phi_types,
                    "scan_enabled": True
                }
        
        return {"phi_detected": False, "scan_enabled": True}
    
    async def get_embeddings(self, texts: Union[str, List[str]]) -> List[EmbeddingResult]:
        """
        Generate embeddings for text(s) using sentence-transformers
        
        Args:
            texts: Single text string or list of texts
            
        Returns:
            List of EmbeddingResult objects
        """
        await self._ensure_initialized()
        
        if not self.is_ready():
            return [EmbeddingResult(
                text=text if isinstance(texts, str) else texts[0],
                embedding=np.zeros(384),  # Default dimension
                model_name="fallback",
                processing_time=0.0,
                success=False,
                error_message="AI models not available"
            )]
        
        # PHI scan before processing
        phi_scan_result = self._scan_for_phi(texts)
        if phi_scan_result.get("phi_detected", False):
            self._audit_log("Embeddings blocked due to PHI", phi_scan_result)
            text_list = [texts] if isinstance(texts, str) else texts
            return [EmbeddingResult(
                text=text,
                embedding=np.zeros(384),
                model_name="blocked",
                processing_time=0.0,
                success=False,
                error_message=f"PHI detected: {', '.join(phi_scan_result.get('phi_types', []))}"
            ) for text in text_list]
        
        import time
        start_time = time.time()
        
        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]
        
        self._audit_log("Generating embeddings", {"count": len(texts)})
        
        results = []
        model = self.models.get("sentence_transformer")
        
        if not model:
            logger.error("Sentence transformer not loaded")
            return [EmbeddingResult(
                text=text,
                embedding=np.zeros(384),
                model_name="error",
                processing_time=0.0,
                success=False,
                error_message="Model not loaded"
            ) for text in texts]
        
        try:
            # Generate embeddings
            embeddings = model.encode(texts, convert_to_numpy=True)
            processing_time = time.time() - start_time
            
            # Create results
            for text, embedding in zip(texts, embeddings):
                results.append(EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model_name=self.config["sentence_transformer_model"],
                    processing_time=processing_time / len(texts),
                    success=True
                ))
            
            self._audit_log("Embeddings generated successfully", {
                "count": len(results),
                "processing_time": processing_time
            })
                
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            results = [EmbeddingResult(
                text=text,
                embedding=np.zeros(384),
                model_name="error",
                processing_time=0.0,
                success=False,
                error_message=str(e)
            ) for text in texts]
        
        return results
    
    async def semantic_search(self, query: str, documents: List[str], 
                            top_k: int = 5) -> SimilarityResult:
        """
        Perform semantic search using embeddings
        
        Args:
            query: Search query text
            documents: List of documents to search
            top_k: Number of top results to return
            
        Returns:
            SimilarityResult with matches and scores
        """
        import time
        start_time = time.time()
        
        await self._ensure_initialized()
        
        if not self.is_ready():
            return SimilarityResult(
                query=query,
                matches=[],
                scores=[],
                model_name="fallback",
                processing_time=0.0
            )
        
        # PHI scan for query
        phi_scan_result = self._scan_for_phi(query)
        if phi_scan_result.get("phi_detected", False):
            self._audit_log("Semantic search blocked due to PHI in query", phi_scan_result)
            return SimilarityResult(
                query=query,
                matches=[],
                scores=[],
                model_name="blocked",
                processing_time=0.0
            )
        
        self._audit_log("Starting semantic search", {"doc_count": len(documents), "top_k": top_k})
        
        try:
            # Get embeddings for query and documents
            query_embeddings = await self.get_embeddings(query)
            doc_embeddings = await self.get_embeddings(documents)
            
            if not query_embeddings[0].success:
                raise Exception("Failed to embed query")
            
            query_vec = query_embeddings[0].embedding
            doc_vecs = np.array([emb.embedding for emb in doc_embeddings if emb.success])
            
            if len(doc_vecs) == 0:
                raise Exception("No valid document embeddings")
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity([query_vec], doc_vecs)[0]
            
            # Get top-k results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            top_scores = similarities[top_indices]
            
            # Format results
            matches = []
            for idx, score in zip(top_indices, top_scores):
                if score >= self.config["similarity_threshold"]:
                    matches.append({
                        "document": documents[idx],
                        "score": float(score),
                        "index": int(idx)
                    })
            
            processing_time = time.time() - start_time
            
            self._audit_log("Semantic search completed", {
                "matches_found": len(matches),
                "processing_time": processing_time
            })
            
            return SimilarityResult(
                query=query,
                matches=matches,
                scores=top_scores.tolist(),
                model_name=self.config["sentence_transformer_model"],
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return SimilarityResult(
                query=query,
                matches=[],
                scores=[],
                model_name="error",
                processing_time=time.time() - start_time
            )
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from text using clinical NER
        
        Args:
            text: Input text for entity extraction
            
        Returns:
            Dictionary with extracted entities and metadata
        """
        await self._ensure_initialized()
        
        if not self.is_ready() or "clinical_ner" not in self.models:
            return {
                "entities": [],
                "success": False,
                "error": "NER model not available"
            }
        
        # PHI scan for input text
        phi_scan_result = self._scan_for_phi(text)
        if phi_scan_result.get("phi_detected", False):
            self._audit_log("Entity extraction blocked due to PHI", phi_scan_result)
            return {
                "entities": [],
                "success": False,
                "error": f"PHI detected: {', '.join(phi_scan_result.get('phi_types', []))}"
            }
        
        self._audit_log("Starting entity extraction", {"text_length": len(text)})
        
        try:
            ner_model = self.models["clinical_ner"]
            results = ner_model(text)
            
            # Format results
            entities = []
            for entity in results:
                entities.append({
                    "text": entity["word"],
                    "label": entity["entity_group"],
                    "confidence": entity["score"],
                    "start": entity.get("start", 0),
                    "end": entity.get("end", len(entity["word"]))
                })
            
            self._audit_log("Entity extraction completed", {"entity_count": len(entities)})
            
            return {
                "entities": entities,
                "text": text,
                "model": self.config["clinical_model"],
                "success": True,
                "count": len(entities)
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return {
                "entities": [],
                "success": False,
                "error": str(e)
            }
    
    async def enhanced_literature_matching(self, query: str, 
                                         literature_db: List[Dict]) -> Dict[str, Any]:
        """
        Enhanced literature matching using semantic similarity
        
        Args:
            query: Research query or abstract
            literature_db: List of literature documents with metadata
            
        Returns:
            Ranked matches with similarity scores and metadata
        """
        if not literature_db:
            return {"matches": [], "query": query, "total": 0}
        
        try:
            # Extract text fields from literature database
            documents = []
            metadata = []
            
            for item in literature_db:
                # Combine title and abstract for better matching
                text_parts = []
                if "title" in item:
                    text_parts.append(item["title"])
                if "abstract" in item:
                    text_parts.append(item["abstract"])
                
                combined_text = " ".join(text_parts)
                documents.append(combined_text)
                metadata.append(item)
            
            # Perform semantic search
            search_result = await self.semantic_search(query, documents, top_k=10)
            
            # Combine results with metadata
            enhanced_matches = []
            for match in search_result.matches:
                doc_metadata = metadata[match["index"]]
                enhanced_match = {
                    **doc_metadata,
                    "similarity_score": match["score"],
                    "matched_text": match["document"][:200] + "..." if len(match["document"]) > 200 else match["document"]
                }
                enhanced_matches.append(enhanced_match)
            
            return {
                "matches": enhanced_matches,
                "query": query,
                "total": len(enhanced_matches),
                "processing_time": search_result.processing_time,
                "model_used": search_result.model_name
            }
            
        except Exception as e:
            logger.error(f"Enhanced literature matching failed: {e}")
            return {
                "matches": [],
                "query": query,
                "total": 0,
                "error": str(e)
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models"""
        info = {
            "ai_packages_available": HAS_AI_PACKAGES,
            "initialized": self._initialized,
            "config": self.config,
            "loaded_models": list(self.models.keys()) if self._initialized else []
        }
        
        if HAS_AI_PACKAGES:
            info.update({
                "torch_version": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
            })
        
        return info

# Global instance for easy access
_ai_processor = None

def get_ai_processor(config: Optional[Dict] = None) -> EnhancedAIProcessor:
    """Get global AI processor instance"""
    global _ai_processor
    if _ai_processor is None:
        _ai_processor = EnhancedAIProcessor(config)
    return _ai_processor

# Convenience functions
async def get_text_embeddings(texts: Union[str, List[str]]) -> List[EmbeddingResult]:
    """Convenience function to get text embeddings"""
    processor = get_ai_processor()
    return await processor.get_embeddings(texts)

async def search_documents(query: str, documents: List[str], top_k: int = 5) -> SimilarityResult:
    """Convenience function for document search"""
    processor = get_ai_processor()
    return await processor.semantic_search(query, documents, top_k)

async def extract_named_entities(text: str) -> Dict[str, Any]:
    """Convenience function for entity extraction"""
    processor = get_ai_processor()
    return await processor.extract_entities(text)