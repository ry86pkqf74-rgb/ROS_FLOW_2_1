"""
ML-Enhanced PHI Detection

Uses pre-trained NER models to detect PHI that regex patterns might miss.
Provides contextual analysis and confidence scoring for better accuracy.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import numpy as np

# Optional ML dependencies with graceful fallback
try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

try:
    from transformers import (
        AutoTokenizer, 
        AutoModelForTokenClassification,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Medical context patterns that increase PHI likelihood
MEDICAL_CONTEXTS = [
    r"\b(?:patient|subject|case|individual|person)\b",
    r"\b(?:diagnosis|diagnosed|condition|disease|illness)\b", 
    r"\b(?:treatment|therapy|medication|prescription|drug)\b",
    r"\b(?:admission|discharge|visit|appointment|exam)\b",
    r"\b(?:doctor|physician|nurse|clinician|provider)\b",
    r"\b(?:hospital|clinic|medical|healthcare|health)\b",
    r"\b(?:record|chart|file|documentation|report)\b",
]

# High-confidence PHI entity types from NER models
PHI_ENTITY_TYPES = {
    "PERSON": "NAME",
    "ORG": "ORGANIZATION", 
    "GPE": "LOCATION",
    "DATE": "DATE",
    "TIME": "TIME",
    "MONEY": "FINANCIAL",
    "CARDINAL": "NUMBER",
    "ORDINAL": "NUMBER",
}

# Clinical NER entity mappings (for clinical models)
CLINICAL_ENTITY_TYPES = {
    "PATIENT": "NAME",
    "DOCTOR": "NAME", 
    "HOSPITAL": "ORGANIZATION",
    "MEDICATION": "MEDICAL_INFO",
    "CONDITION": "MEDICAL_INFO",
    "PROCEDURE": "MEDICAL_INFO",
    "TEST": "MEDICAL_INFO",
}


@dataclass
class MLPHIFinding:
    """ML-detected PHI finding with confidence scoring."""
    text: str
    start: int
    end: int
    entity_type: str
    phi_category: str
    confidence: float
    context_score: float  # How medical/PHI-relevant the context is
    model_source: str  # "spacy", "transformers", "clinical"
    surrounding_context: str = ""
    is_likely_phi: bool = False
    
    @property
    def combined_confidence(self) -> float:
        """Combined confidence score factoring in context."""
        return (self.confidence * 0.7) + (self.context_score * 0.3)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "entity_type": self.entity_type,
            "phi_category": self.phi_category,
            "confidence": self.confidence,
            "context_score": self.context_score,
            "combined_confidence": self.combined_confidence,
            "model_source": self.model_source,
            "is_likely_phi": self.is_likely_phi,
            "surrounding_context": self.surrounding_context[:100],  # Truncate for safety
        }


class MLPhiDetector:
    """
    ML-enhanced PHI detection using NER models.
    
    Combines multiple approaches:
    1. SpaCy general NER model  
    2. HuggingFace biomedical NER models
    3. Context analysis for medical relevance
    4. Confidence scoring and filtering
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.8,
                 context_threshold: float = 0.6,
                 enable_spacy: bool = True,
                 enable_transformers: bool = True,
                 clinical_model: Optional[str] = None):
        """
        Initialize the ML PHI detector.
        
        Args:
            confidence_threshold: Minimum confidence for PHI detection
            context_threshold: Minimum context score for PHI relevance
            enable_spacy: Whether to use SpaCy NER
            enable_transformers: Whether to use HuggingFace models
            clinical_model: Optional clinical NER model name
        """
        self.confidence_threshold = confidence_threshold
        self.context_threshold = context_threshold
        self.enable_spacy = enable_spacy and SPACY_AVAILABLE
        self.enable_transformers = enable_transformers and TRANSFORMERS_AVAILABLE
        self.clinical_model = clinical_model
        
        # Initialize models
        self.spacy_model = None
        self.transformer_pipeline = None
        self.clinical_pipeline = None
        
        # Compile medical context patterns
        self.medical_context_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in MEDICAL_CONTEXTS
        ]
        
        self._initialize_models()
        
        logger.info(
            f"MLPhiDetector initialized: spacy={self.spacy_model is not None}, "
            f"transformers={self.transformer_pipeline is not None}, "
            f"clinical={self.clinical_pipeline is not None}"
        )
    
    def _initialize_models(self):
        """Initialize ML models with graceful fallback."""
        # Initialize SpaCy model
        if self.enable_spacy:
            try:
                # Try to load English model
                self.spacy_model = spacy.load("en_core_web_sm")
                logger.info("SpaCy model loaded successfully")
            except OSError:
                try:
                    # Fall back to larger model if available
                    self.spacy_model = spacy.load("en_core_web_md")
                    logger.info("SpaCy medium model loaded successfully")
                except OSError:
                    logger.warning("SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
                    self.enable_spacy = False
        
        # Initialize Transformers pipeline
        if self.enable_transformers:
            try:
                # Use a biomedical NER model if available, fallback to general
                model_options = [
                    "d4data/biomedical-ner-all",  # Biomedical model
                    "dbmdz/bert-large-cased-finetuned-conll03-english",  # General NER
                    "dslim/bert-base-NER",  # Lightweight option
                ]
                
                for model_name in model_options:
                    try:
                        self.transformer_pipeline = pipeline(
                            "ner", 
                            model=model_name,
                            tokenizer=model_name,
                            aggregation_strategy="simple"
                        )
                        logger.info(f"Transformers model loaded: {model_name}")
                        break
                    except Exception as e:
                        logger.debug(f"Could not load {model_name}: {e}")
                        continue
                
                if not self.transformer_pipeline:
                    logger.warning("No Transformers NER model could be loaded")
                    self.enable_transformers = False
                    
            except Exception as e:
                logger.warning(f"Transformers initialization failed: {e}")
                self.enable_transformers = False
        
        # Initialize clinical model if specified
        if self.clinical_model and self.enable_transformers:
            try:
                self.clinical_pipeline = pipeline(
                    "ner",
                    model=self.clinical_model,
                    tokenizer=self.clinical_model,
                    aggregation_strategy="simple"
                )
                logger.info(f"Clinical model loaded: {self.clinical_model}")
            except Exception as e:
                logger.warning(f"Could not load clinical model {self.clinical_model}: {e}")
    
    def analyze_medical_context(self, text: str, entity_start: int, entity_end: int) -> float:
        """
        Analyze the medical context around an entity.
        
        Args:
            text: Full text
            entity_start: Start position of entity
            entity_end: End position of entity
            
        Returns:
            Context score (0.0-1.0) indicating medical/PHI relevance
        """
        # Extract context window around entity
        context_window = 100  # characters before/after
        start = max(0, entity_start - context_window)
        end = min(len(text), entity_end + context_window)
        context = text[start:end].lower()
        
        # Count medical context pattern matches
        medical_matches = 0
        total_patterns = len(self.medical_context_patterns)
        
        for pattern in self.medical_context_patterns:
            if pattern.search(context):
                medical_matches += 1
        
        # Base context score
        context_score = medical_matches / total_patterns if total_patterns > 0 else 0.0
        
        # Boost score for certain keywords close to entity
        entity_text = text[entity_start:entity_end].lower()
        close_context = text[max(0, entity_start-50):min(len(text), entity_end+50)].lower()
        
        # High-confidence medical indicators
        if any(indicator in close_context for indicator in [
            "patient", "subject", "mr.", "mrs.", "dr.", "admission", "discharge"
        ]):
            context_score = min(1.0, context_score + 0.3)
        
        # Medical record number patterns
        if any(indicator in close_context for indicator in [
            "mrn", "medical record", "patient id", "chart"
        ]):
            context_score = min(1.0, context_score + 0.4)
        
        # Date context in medical settings
        if "date" in entity_text and any(indicator in close_context for indicator in [
            "birth", "admission", "discharge", "visit", "procedure"
        ]):
            context_score = min(1.0, context_score + 0.3)
        
        return context_score
    
    def detect_with_spacy(self, text: str) -> List[MLPHIFinding]:
        """Detect PHI using SpaCy NER model."""
        if not self.spacy_model:
            return []
        
        findings = []
        
        try:
            doc = self.spacy_model(text)
            
            for ent in doc.ents:
                # Map SpaCy entity type to PHI category
                phi_category = PHI_ENTITY_TYPES.get(ent.label_, "OTHER")
                if phi_category == "OTHER":
                    continue  # Skip non-PHI entities
                
                # Analyze context
                context_score = self.analyze_medical_context(text, ent.start_char, ent.end_char)
                
                # Get surrounding context for analysis
                context_start = max(0, ent.start_char - 50)
                context_end = min(len(text), ent.end_char + 50)
                surrounding_context = text[context_start:context_end]
                
                finding = MLPHIFinding(
                    text=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    entity_type=ent.label_,
                    phi_category=phi_category,
                    confidence=ent._.get("confidence", 0.85),  # SpaCy doesn't provide confidence by default
                    context_score=context_score,
                    model_source="spacy",
                    surrounding_context=surrounding_context,
                    is_likely_phi=context_score >= self.context_threshold
                )
                
                findings.append(finding)
                
        except Exception as e:
            logger.warning(f"SpaCy NER failed: {e}")
        
        return findings
    
    def detect_with_transformers(self, text: str) -> List[MLPHIFinding]:
        """Detect PHI using HuggingFace Transformers NER model."""
        if not self.transformer_pipeline:
            return []
        
        findings = []
        
        try:
            # Run NER pipeline
            entities = self.transformer_pipeline(text)
            
            for entity in entities:
                # Map entity type to PHI category  
                entity_type = entity.get("entity_group", entity.get("label", ""))
                phi_category = PHI_ENTITY_TYPES.get(entity_type, "OTHER")
                if phi_category == "OTHER":
                    phi_category = CLINICAL_ENTITY_TYPES.get(entity_type, "OTHER")
                if phi_category == "OTHER":
                    continue  # Skip non-PHI entities
                
                # Extract position information
                start = entity["start"]
                end = entity["end"] 
                entity_text = text[start:end]
                
                # Analyze context
                context_score = self.analyze_medical_context(text, start, end)
                
                # Get surrounding context
                context_start = max(0, start - 50)
                context_end = min(len(text), end + 50)
                surrounding_context = text[context_start:context_end]
                
                finding = MLPHIFinding(
                    text=entity_text,
                    start=start,
                    end=end,
                    entity_type=entity_type,
                    phi_category=phi_category,
                    confidence=entity.get("score", 0.0),
                    context_score=context_score,
                    model_source="transformers",
                    surrounding_context=surrounding_context,
                    is_likely_phi=context_score >= self.context_threshold
                )
                
                findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Transformers NER failed: {e}")
        
        return findings
    
    def detect_with_clinical_model(self, text: str) -> List[MLPHIFinding]:
        """Detect PHI using specialized clinical NER model."""
        if not self.clinical_pipeline:
            return []
        
        findings = []
        
        try:
            entities = self.clinical_pipeline(text)
            
            for entity in entities:
                entity_type = entity.get("entity_group", entity.get("label", ""))
                phi_category = CLINICAL_ENTITY_TYPES.get(entity_type, "MEDICAL_INFO")
                
                start = entity["start"]
                end = entity["end"]
                entity_text = text[start:end]
                
                # Clinical models have high context by default
                context_score = min(1.0, 0.8 + self.analyze_medical_context(text, start, end) * 0.2)
                
                context_start = max(0, start - 50)
                context_end = min(len(text), end + 50)
                surrounding_context = text[context_start:context_end]
                
                finding = MLPHIFinding(
                    text=entity_text,
                    start=start,
                    end=end,
                    entity_type=entity_type,
                    phi_category=phi_category,
                    confidence=entity.get("score", 0.9),  # Clinical models typically high confidence
                    context_score=context_score,
                    model_source="clinical",
                    surrounding_context=surrounding_context,
                    is_likely_phi=True  # Clinical models are specialized for medical PHI
                )
                
                findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Clinical NER failed: {e}")
        
        return findings
    
    def detect_phi(self, text: str) -> List[MLPHIFinding]:
        """
        Perform comprehensive ML-based PHI detection.
        
        Args:
            text: Text to analyze for PHI
            
        Returns:
            List of ML-detected PHI findings
        """
        if not text or not text.strip():
            return []
        
        all_findings = []
        
        # Run all available models
        if self.enable_spacy:
            spacy_findings = self.detect_with_spacy(text)
            all_findings.extend(spacy_findings)
            logger.debug(f"SpaCy detected {len(spacy_findings)} potential PHI entities")
        
        if self.enable_transformers:
            transformer_findings = self.detect_with_transformers(text)
            all_findings.extend(transformer_findings)
            logger.debug(f"Transformers detected {len(transformer_findings)} potential PHI entities")
        
        if self.clinical_pipeline:
            clinical_findings = self.detect_with_clinical_model(text) 
            all_findings.extend(clinical_findings)
            logger.debug(f"Clinical model detected {len(clinical_findings)} potential PHI entities")
        
        # Deduplicate overlapping findings
        deduplicated_findings = self._deduplicate_findings(all_findings)
        
        # Filter by confidence thresholds
        high_confidence_findings = [
            finding for finding in deduplicated_findings
            if finding.confidence >= self.confidence_threshold or 
               finding.combined_confidence >= self.confidence_threshold
        ]
        
        logger.info(
            f"ML PHI Detection: {len(all_findings)} raw → "
            f"{len(deduplicated_findings)} deduplicated → "
            f"{len(high_confidence_findings)} high confidence"
        )
        
        return high_confidence_findings
    
    def _deduplicate_findings(self, findings: List[MLPHIFinding]) -> List[MLPHIFinding]:
        """Remove overlapping findings, keeping highest confidence."""
        if not findings:
            return []
        
        # Sort by confidence descending
        sorted_findings = sorted(findings, key=lambda f: f.combined_confidence, reverse=True)
        
        deduplicated = []
        used_spans = []
        
        for finding in sorted_findings:
            # Check for overlap with existing spans
            overlaps = False
            for used_start, used_end in used_spans:
                if (finding.start < used_end and finding.end > used_start):  # Overlap detected
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(finding)
                used_spans.append((finding.start, finding.end))
        
        return deduplicated
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "spacy_available": SPACY_AVAILABLE,
            "transformers_available": TRANSFORMERS_AVAILABLE,
            "spacy_enabled": self.enable_spacy,
            "transformers_enabled": self.enable_transformers,
            "spacy_model": str(self.spacy_model) if self.spacy_model else None,
            "transformer_model": "loaded" if self.transformer_pipeline else None,
            "clinical_model": self.clinical_model if self.clinical_pipeline else None,
            "confidence_threshold": self.confidence_threshold,
            "context_threshold": self.context_threshold,
        }


def create_ml_phi_detector(
    confidence_threshold: float = 0.8,
    enable_clinical: bool = True,
    clinical_model: Optional[str] = None
) -> Optional[MLPhiDetector]:
    """
    Factory function to create ML PHI detector with optimal configuration.
    
    Args:
        confidence_threshold: Minimum confidence for PHI detection
        enable_clinical: Whether to try loading clinical models
        clinical_model: Specific clinical model to use
        
    Returns:
        MLPhiDetector instance or None if no models available
    """
    if not SPACY_AVAILABLE and not TRANSFORMERS_AVAILABLE:
        logger.warning("No ML libraries available for PHI detection")
        return None
    
    # Try clinical models if requested
    if enable_clinical and not clinical_model:
        clinical_options = [
            "emilyalsentzer/Bio_ClinicalBERT",
            "d4data/biomedical-ner-all", 
            "allenai/scibert_scivocab_uncased"
        ]
        
        for option in clinical_options:
            try:
                # Test if model is available
                detector = MLPhiDetector(
                    confidence_threshold=confidence_threshold,
                    clinical_model=option
                )
                if detector.clinical_pipeline:
                    logger.info(f"Using clinical model: {option}")
                    return detector
            except Exception as e:
                logger.debug(f"Clinical model {option} not available: {e}")
                continue
    
    # Fall back to general models
    return MLPhiDetector(
        confidence_threshold=confidence_threshold,
        clinical_model=clinical_model
    )