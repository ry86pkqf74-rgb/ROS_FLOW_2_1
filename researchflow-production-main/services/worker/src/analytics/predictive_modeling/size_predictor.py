"""
Predictive Size Modeling System
==============================

Machine learning-based system for predicting manuscript and package sizes,
compression ratios, and optimization potential before processing.

Features:
- Historical data analysis
- Feature extraction from manuscript content
- Size prediction algorithms
- Compression ratio estimation
- Processing time prediction
- Resource requirement forecasting
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ManuscriptFeatures:
    """Feature representation of a manuscript for prediction."""
    word_count: int
    section_count: int
    reference_count: int
    figure_count: int
    table_count: int
    equation_count: int
    citation_density: float
    complexity_score: float
    formatting_richness: float
    content_type: str  # 'clinical_trial', 'observational', 'review', etc.


@dataclass
class SizePrediction:
    """Size prediction result."""
    predicted_size_bytes: int
    confidence_score: float
    predicted_compression_ratio: float
    estimated_processing_time: float
    recommended_compression_level: str
    size_breakdown: Dict[str, int]
    prediction_factors: Dict[str, float]


class PredictiveSizeModeler:
    """Machine learning-based size prediction system."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/size_predictor.pkl"
        self.feature_weights = self._initialize_feature_weights()
        self.historical_data = []
        self.model_trained = False
        
    def _initialize_feature_weights(self) -> Dict[str, float]:
        """Initialize feature weights for size prediction."""
        return {
            "word_count": 0.4,           # Primary factor
            "reference_count": 0.15,     # References add size
            "figure_count": 0.2,         # Images/figures significant
            "table_count": 0.1,          # Tables moderate impact
            "complexity_score": 0.1,     # Complex formatting adds size
            "citation_density": 0.05     # Dense citations add metadata
        }
    
    def extract_features(self, manuscript_data: Dict[str, Any]) -> ManuscriptFeatures:
        """Extract predictive features from manuscript data."""
        # Basic counts
        word_count = self._count_words(manuscript_data)
        section_count = self._count_sections(manuscript_data)
        reference_count = self._count_references(manuscript_data)
        figure_count = self._count_figures(manuscript_data)
        table_count = self._count_tables(manuscript_data)
        equation_count = self._count_equations(manuscript_data)
        
        # Derived metrics
        citation_density = reference_count / word_count if word_count > 0 else 0
        complexity_score = self._calculate_complexity_score(manuscript_data)
        formatting_richness = self._calculate_formatting_richness(manuscript_data)
        content_type = self._determine_content_type(manuscript_data)
        
        return ManuscriptFeatures(
            word_count=word_count,
            section_count=section_count,
            reference_count=reference_count,
            figure_count=figure_count,
            table_count=table_count,
            equation_count=equation_count,
            citation_density=citation_density,
            complexity_score=complexity_score,
            formatting_richness=formatting_richness,
            content_type=content_type
        )
    
    def predict_size(self, manuscript_data: Dict[str, Any]) -> SizePrediction:
        """Predict manuscript package size and compression characteristics."""
        features = self.extract_features(manuscript_data)
        
        # Base size calculation using feature weights
        base_size = (
            features.word_count * self.feature_weights["word_count"] * 5 +  # ~5 bytes per word
            features.reference_count * self.feature_weights["reference_count"] * 150 +  # ~150 bytes per reference
            features.figure_count * self.feature_weights["figure_count"] * 50000 +  # ~50KB per figure
            features.table_count * self.feature_weights["table_count"] * 5000 +  # ~5KB per table
            features.complexity_score * self.feature_weights["complexity_score"] * 10000 +  # Complexity overhead
            features.citation_density * self.feature_weights["citation_density"] * 20000  # Citation metadata
        )
        
        # Content type multipliers
        content_type_multipliers = {
            "clinical_trial": 1.2,      # More structured, regulatory content
            "observational": 1.0,       # Standard size
            "systematic_review": 1.5,   # Large reference lists
            "case_study": 0.8,          # Typically shorter
            "letter": 0.3,              # Very short
            "editorial": 0.5            # Short opinion pieces
        }
        
        multiplier = content_type_multipliers.get(features.content_type, 1.0)
        predicted_size = int(base_size * multiplier)
        
        # Predict compression ratio based on content characteristics
        compression_ratio = self._predict_compression_ratio(features)
        
        # Estimate processing time based on size and complexity
        processing_time = self._estimate_processing_time(predicted_size, features.complexity_score)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(features)
        
        # Determine recommended compression level
        compression_level = self._recommend_compression_level(predicted_size, features)
        
        # Size breakdown
        size_breakdown = {
            "text_content": int(features.word_count * 5),
            "references": int(features.reference_count * 150),
            "figures": int(features.figure_count * 50000),
            "tables": int(features.table_count * 5000),
            "metadata": int(predicted_size * 0.1),
            "formatting": int(predicted_size * 0.05)
        }
        
        # Prediction factors (what drives the size)
        prediction_factors = {
            "word_count_impact": features.word_count / 10000,  # Normalized
            "media_content_impact": (features.figure_count + features.table_count) / 10,
            "complexity_impact": features.complexity_score,
            "citation_impact": features.citation_density * 100
        }
        
        return SizePrediction(
            predicted_size_bytes=predicted_size,
            confidence_score=confidence,
            predicted_compression_ratio=compression_ratio,
            estimated_processing_time=processing_time,
            recommended_compression_level=compression_level,
            size_breakdown=size_breakdown,
            prediction_factors=prediction_factors
        )
    
    def train_model(self, historical_data: List[Dict[str, Any]]):
        """Train the prediction model using historical data."""
        if not historical_data:
            logger.warning("No historical data provided for training")
            return
        
        self.historical_data = historical_data
        
        # Extract features and labels from historical data
        feature_matrix = []
        size_labels = []
        compression_labels = []
        
        for record in historical_data:
            manuscript_data = record.get("manuscript", {})
            actual_size = record.get("actual_size", 0)
            actual_compression_ratio = record.get("actual_compression_ratio", 1.0)
            
            features = self.extract_features(manuscript_data)
            
            feature_vector = [
                features.word_count,
                features.section_count,
                features.reference_count,
                features.figure_count,
                features.table_count,
                features.complexity_score,
                features.citation_density,
                features.formatting_richness
            ]
            
            feature_matrix.append(feature_vector)
            size_labels.append(actual_size)
            compression_labels.append(actual_compression_ratio)
        
        # Update feature weights using simple linear regression approach
        self._update_feature_weights(feature_matrix, size_labels)
        
        self.model_trained = True
        logger.info(f"Model trained on {len(historical_data)} historical records")
    
    def _update_feature_weights(self, features: List[List[float]], labels: List[float]):
        """Update feature weights based on historical performance."""
        if not features or not labels:
            return
        
        # Convert to numpy arrays for calculation
        X = np.array(features)
        y = np.array(labels)
        
        # Simple correlation-based weight adjustment
        feature_names = ["word_count", "section_count", "reference_count", 
                        "figure_count", "table_count", "complexity_score",
                        "citation_density", "formatting_richness"]
        
        for i, feature_name in enumerate(feature_names):
            if feature_name in self.feature_weights and X.shape[0] > 1:
                # Calculate correlation between feature and size
                if np.std(X[:, i]) > 0:  # Avoid division by zero
                    correlation = np.corrcoef(X[:, i], y)[0, 1]
                    if not np.isnan(correlation):
                        # Adjust weight based on correlation strength
                        self.feature_weights[feature_name] *= (1 + correlation * 0.1)
    
    def _count_words(self, manuscript_data: Dict[str, Any]) -> int:
        """Count words in manuscript content."""
        word_count = 0
        
        # Check metadata first
        if "metadata" in manuscript_data and "word_count" in manuscript_data["metadata"]:
            return manuscript_data["metadata"]["word_count"]
        
        # Count from content
        for section_name, content in manuscript_data.items():
            if isinstance(content, str):
                word_count += len(content.split())
            elif isinstance(content, dict):
                word_count += self._count_words(content)
        
        return word_count
    
    def _count_sections(self, manuscript_data: Dict[str, Any]) -> int:
        """Count manuscript sections."""
        # Common manuscript sections
        section_keys = ["abstract", "introduction", "methods", "results", 
                       "discussion", "conclusion", "references"]
        
        count = 0
        for key in section_keys:
            if key in manuscript_data:
                count += 1
        
        return count
    
    def _count_references(self, manuscript_data: Dict[str, Any]) -> int:
        """Count references in manuscript."""
        # Check metadata first
        if "metadata" in manuscript_data:
            if "reference_count" in manuscript_data["metadata"]:
                return manuscript_data["metadata"]["reference_count"]
            if "citation_count" in manuscript_data["metadata"]:
                return manuscript_data["metadata"]["citation_count"]
        
        # Count from references section
        references = manuscript_data.get("references", [])
        if isinstance(references, list):
            return len(references)
        elif isinstance(references, str):
            # Count numbered references [1], [2], etc.
            import re
            ref_pattern = r'\[\d+\]'
            matches = re.findall(ref_pattern, references)
            return len(set(matches))  # Unique references
        
        return 0
    
    def _count_figures(self, manuscript_data: Dict[str, Any]) -> int:
        """Count figures in manuscript."""
        if "metadata" in manuscript_data and "figure_count" in manuscript_data["metadata"]:
            return manuscript_data["metadata"]["figure_count"]
        
        # Look for figure references
        content = str(manuscript_data)
        import re
        figure_pattern = r'[Ff]igure\s+\d+'
        matches = re.findall(figure_pattern, content)
        return len(set(matches))
    
    def _count_tables(self, manuscript_data: Dict[str, Any]) -> int:
        """Count tables in manuscript."""
        if "metadata" in manuscript_data and "table_count" in manuscript_data["metadata"]:
            return manuscript_data["metadata"]["table_count"]
        
        # Look for table references
        content = str(manuscript_data)
        import re
        table_pattern = r'[Tt]able\s+\d+'
        matches = re.findall(table_pattern, content)
        return len(set(matches))
    
    def _count_equations(self, manuscript_data: Dict[str, Any]) -> int:
        """Count equations in manuscript."""
        content = str(manuscript_data)
        # Look for equation indicators
        equation_indicators = ["$", "\\begin{equation}", "\\(", "\\["]
        equation_count = sum(content.count(indicator) for indicator in equation_indicators)
        return equation_count // 2  # Assume paired delimiters
    
    def _calculate_complexity_score(self, manuscript_data: Dict[str, Any]) -> float:
        """Calculate manuscript complexity score (0-1)."""
        complexity_factors = {
            "technical_terms": self._count_technical_terms(manuscript_data),
            "statistical_content": self._count_statistical_content(manuscript_data),
            "formatting_elements": self._count_formatting_elements(manuscript_data),
            "cross_references": self._count_cross_references(manuscript_data)
        }
        
        # Normalize and weight factors
        normalized_complexity = min(1.0, sum(
            factor_value / 100 for factor_value in complexity_factors.values()
        ) / len(complexity_factors))
        
        return normalized_complexity
    
    def _calculate_formatting_richness(self, manuscript_data: Dict[str, Any]) -> float:
        """Calculate formatting richness score (0-1)."""
        content = str(manuscript_data)
        
        # Look for formatting indicators
        formatting_indicators = {
            "bold": content.count("**") + content.count("<b>") + content.count("\\textbf"),
            "italic": content.count("*") + content.count("<i>") + content.count("\\textit"),
            "headers": content.count("#") + content.count("<h"),
            "lists": content.count("- ") + content.count("1. ") + content.count("\\item"),
            "links": content.count("http") + content.count("\\href")
        }
        
        total_indicators = sum(formatting_indicators.values())
        word_count = self._count_words(manuscript_data)
        
        # Normalize by word count
        richness_score = min(1.0, total_indicators / max(word_count / 100, 1))
        return richness_score
    
    def _determine_content_type(self, manuscript_data: Dict[str, Any]) -> str:
        """Determine manuscript content type."""
        content = str(manuscript_data).lower()
        
        # Check for content type indicators
        type_indicators = {
            "clinical_trial": ["randomized", "controlled trial", "rct", "intervention"],
            "systematic_review": ["systematic review", "meta-analysis", "prisma"],
            "observational": ["cohort", "case-control", "cross-sectional", "observational"],
            "case_study": ["case study", "case report", "case series"],
            "letter": ["letter to editor", "correspondence", "comment"],
            "editorial": ["editorial", "opinion", "perspective"]
        }
        
        for content_type, keywords in type_indicators.items():
            if any(keyword in content for keyword in keywords):
                return content_type
        
        return "research_article"  # Default
    
    def _predict_compression_ratio(self, features: ManuscriptFeatures) -> float:
        """Predict compression ratio based on content characteristics."""
        # Base compression ratio
        base_ratio = 0.8
        
        # Adjust based on content characteristics
        adjustments = {
            "text_heavy": -0.1 if features.word_count > 5000 else 0,  # Text compresses well
            "media_heavy": 0.15 if (features.figure_count + features.table_count) > 5 else 0,  # Media less compressible
            "complex_formatting": features.formatting_richness * 0.1,  # Rich formatting reduces compression
            "repetitive_content": -0.05 if features.citation_density > 0.1 else 0  # Citations are repetitive
        }
        
        adjusted_ratio = base_ratio + sum(adjustments.values())
        return max(0.3, min(1.0, adjusted_ratio))  # Clamp between 30% and 100%
    
    def _estimate_processing_time(self, predicted_size: int, complexity_score: float) -> float:
        """Estimate processing time in seconds."""
        # Base processing time (size-dependent)
        base_time = predicted_size / 100000  # 100KB per second base rate
        
        # Complexity multiplier
        complexity_multiplier = 1 + complexity_score
        
        # Content type multipliers
        type_multipliers = {
            "systematic_review": 2.0,    # Complex citation processing
            "clinical_trial": 1.5,       # Statistical processing
            "observational": 1.2,        # Data analysis
            "case_study": 0.8,           # Simpler processing
            "letter": 0.5               # Minimal processing
        }
        
        estimated_time = base_time * complexity_multiplier
        return max(0.1, estimated_time)  # Minimum 0.1 seconds
    
    def _calculate_confidence(self, features: ManuscriptFeatures) -> float:
        """Calculate prediction confidence score."""
        # Confidence factors
        confidence_factors = {
            "sufficient_content": min(1.0, features.word_count / 1000),  # More content = higher confidence
            "standard_structure": 1.0 if features.section_count >= 4 else 0.7,  # Standard sections
            "reasonable_references": min(1.0, features.reference_count / 20),  # Adequate references
            "content_type_known": 1.0 if features.content_type != "research_article" else 0.8
        }
        
        # Weighted average
        weights = [0.3, 0.3, 0.2, 0.2]
        weighted_confidence = sum(
            factor * weight for factor, weight in zip(confidence_factors.values(), weights)
        )
        
        return min(1.0, weighted_confidence)
    
    def _recommend_compression_level(self, predicted_size: int, features: ManuscriptFeatures) -> str:
        """Recommend appropriate compression level."""
        if predicted_size > 1000000:  # > 1MB
            return "high"
        elif predicted_size > 100000:  # > 100KB
            if features.figure_count > 3:
                return "high"  # Many figures benefit from high compression
            else:
                return "medium"
        else:
            return "low"  # Small files don't need aggressive compression
    
    def _count_technical_terms(self, manuscript_data: Dict[str, Any]) -> int:
        """Count technical terms in manuscript."""
        content = str(manuscript_data).lower()
        
        # Common technical/medical terms
        technical_terms = [
            "analysis", "methodology", "significant", "correlation", "regression",
            "hypothesis", "variable", "statistical", "confidence", "interval",
            "patient", "clinical", "treatment", "outcome", "biomarker",
            "prevalence", "incidence", "odds ratio", "hazard ratio"
        ]
        
        return sum(content.count(term) for term in technical_terms)
    
    def _count_statistical_content(self, manuscript_data: Dict[str, Any]) -> int:
        """Count statistical content indicators."""
        content = str(manuscript_data)
        
        statistical_patterns = [
            r'p\s*[<>=]\s*0\.\d+',      # p-values
            r'95%\s*CI',                # Confidence intervals
            r'[Mm]ean\s*±\s*\d+',      # Mean ± SD
            r'OR\s*=\s*\d+\.\d+',      # Odds ratios
            r'HR\s*=\s*\d+\.\d+',      # Hazard ratios
            r'r\s*=\s*0\.\d+',         # Correlation coefficients
            r'F\(\d+,\s*\d+\)',        # F-statistics
            r't\(\d+\)',               # t-statistics
        ]
        
        import re
        count = 0
        for pattern in statistical_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            count += len(matches)
        
        return count
    
    def _count_formatting_elements(self, manuscript_data: Dict[str, Any]) -> int:
        """Count formatting elements in manuscript."""
        content = str(manuscript_data)
        
        # Look for various formatting elements
        formatting_elements = [
            "**", "*", "#", "-", "1.", "2.", "3.",  # Markdown
            "<b>", "<i>", "<u>", "<em>", "<strong>",  # HTML
            "\\textbf", "\\textit", "\\section", "\\subsection"  # LaTeX
        ]
        
        return sum(content.count(element) for element in formatting_elements)
    
    def _count_cross_references(self, manuscript_data: Dict[str, Any]) -> int:
        """Count cross-references within manuscript."""
        content = str(manuscript_data)
        
        import re
        # Look for cross-reference patterns
        cross_ref_patterns = [
            r'Figure\s+\d+',
            r'Table\s+\d+', 
            r'Section\s+\d+',
            r'Equation\s+\d+',
            r'see\s+above',
            r'as\s+shown\s+in',
            r'as\s+described\s+in'
        ]
        
        count = 0
        for pattern in cross_ref_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            count += len(matches)
        
        return count
    
    def get_size_prediction_analytics(self) -> Dict[str, Any]:
        """Get analytics on size prediction performance."""
        if not self.historical_data:
            return {"status": "no_historical_data"}
        
        predictions = []
        actual_sizes = []
        
        for record in self.historical_data:
            manuscript_data = record.get("manuscript", {})
            actual_size = record.get("actual_size", 0)
            
            prediction = self.predict_size(manuscript_data)
            predictions.append(prediction.predicted_size_bytes)
            actual_sizes.append(actual_size)
        
        if not predictions:
            return {"status": "no_predictions"}
        
        # Calculate accuracy metrics
        errors = [abs(pred - actual) for pred, actual in zip(predictions, actual_sizes)]
        relative_errors = [error / actual if actual > 0 else 0 for error, actual in zip(errors, actual_sizes)]
        
        return {
            "prediction_count": len(predictions),
            "mean_absolute_error": np.mean(errors),
            "mean_relative_error": np.mean(relative_errors),
            "accuracy_within_10_percent": sum(1 for error in relative_errors if error < 0.1) / len(relative_errors),
            "accuracy_within_20_percent": sum(1 for error in relative_errors if error < 0.2) / len(relative_errors),
            "max_error": max(errors),
            "min_error": min(errors),
            "prediction_trend": "improving" if len(relative_errors) > 5 and relative_errors[-5:] < relative_errors[:5] else "stable"
        }
    
    def save_model(self, path: Optional[str] = None):
        """Save trained model to disk."""
        save_path = path or self.model_path
        
        model_data = {
            "feature_weights": self.feature_weights,
            "model_trained": self.model_trained,
            "training_date": datetime.now().isoformat(),
            "historical_data_count": len(self.historical_data)
        }
        
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, path: Optional[str] = None):
        """Load trained model from disk."""
        load_path = path or self.model_path
        
        if not Path(load_path).exists():
            logger.warning(f"Model file not found: {load_path}")
            return
        
        try:
            with open(load_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.feature_weights = model_data["feature_weights"]
            self.model_trained = model_data["model_trained"]
            
            logger.info(f"Model loaded from {load_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")


# Global predictor instance
_global_predictor: Optional[PredictiveSizeModeler] = None


def get_size_predictor() -> PredictiveSizeModeler:
    """Get global size predictor instance."""
    global _global_predictor
    if _global_predictor is None:
        _global_predictor = PredictiveSizeModeler()
    return _global_predictor


if __name__ == "__main__":
    # Example usage
    predictor = PredictiveSizeModeler()
    
    # Sample manuscript data
    sample_manuscript = {
        "title": "Machine Learning in Clinical Research",
        "abstract": "This study explores machine learning applications...",
        "introduction": "Machine learning has revolutionized healthcare...",
        "methods": "We used advanced algorithms to analyze...",
        "results": "Our analysis revealed significant patterns...",
        "discussion": "The findings have important implications...",
        "references": ["Reference 1", "Reference 2", "Reference 3"],
        "metadata": {
            "word_count": 4500,
            "reference_count": 35,
            "figure_count": 6,
            "table_count": 3
        }
    }
    
    # Get prediction
    prediction = predictor.predict_size(sample_manuscript)
    
    print("Size Prediction Results:")
    print(f"Predicted size: {prediction.predicted_size_bytes:,} bytes")
    print(f"Confidence: {prediction.confidence_score:.2%}")
    print(f"Compression ratio: {prediction.predicted_compression_ratio:.2f}")
    print(f"Processing time: {prediction.estimated_processing_time:.1f}s")
    print(f"Recommended compression: {prediction.recommended_compression_level}")
    
    print("\nSize breakdown:")
    for component, size in prediction.size_breakdown.items():
        print(f"  {component}: {size:,} bytes")