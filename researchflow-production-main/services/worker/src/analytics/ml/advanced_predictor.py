"""
Advanced Machine Learning Predictor
===================================

Enhanced ML features including:
- Model versioning and A/B testing
- Auto-retraining pipeline
- Anomaly detection
- Ensemble methods
- Feature importance analysis
"""

import numpy as np
import pandas as pd
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import hashlib
import asyncio
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class ModelVersion:
    """Model version metadata."""
    version: str
    created_at: datetime
    model_type: str
    performance_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    training_data_size: int
    validation_score: float
    is_active: bool = False


@dataclass
class PredictionResult:
    """Enhanced prediction result with uncertainty and explanation."""
    predicted_value: float
    confidence_score: float
    uncertainty_range: Tuple[float, float]
    feature_contributions: Dict[str, float]
    model_version: str
    anomaly_score: float
    is_anomaly: bool
    explanation: str


class AdvancedPredictor:
    """Advanced ML predictor with versioning and ensemble methods."""
    
    def __init__(self, model_dir: str = "models/advanced"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Model registry
        self.models: Dict[str, Any] = {}
        self.model_versions: List[ModelVersion] = []
        self.active_model_version: Optional[str] = None
        
        # Ensemble components
        self.ensemble_models = {}
        self.feature_scaler = StandardScaler()
        
        # A/B testing
        self.ab_test_config = {
            "enabled": False,
            "test_model_version": None,
            "control_model_version": None,
            "traffic_split": 0.1  # 10% to test model
        }
        
        # Anomaly detection
        self.anomaly_threshold = 2.0
        self.baseline_stats = {}
        
        self._load_models()
    
    def _load_models(self):
        """Load existing models and versions."""
        try:
            versions_file = self.model_dir / "versions.json"
            if versions_file.exists():
                with open(versions_file, 'r') as f:
                    versions_data = json.load(f)
                
                self.model_versions = [
                    ModelVersion(
                        version=v["version"],
                        created_at=datetime.fromisoformat(v["created_at"]),
                        model_type=v["model_type"],
                        performance_metrics=v["performance_metrics"],
                        feature_importance=v["feature_importance"],
                        training_data_size=v["training_data_size"],
                        validation_score=v["validation_score"],
                        is_active=v.get("is_active", False)
                    )
                    for v in versions_data
                ]
                
                # Load active model
                active_versions = [v for v in self.model_versions if v.is_active]
                if active_versions:
                    self.active_model_version = active_versions[0].version
                    self._load_model_by_version(self.active_model_version)
                    
        except Exception as e:
            logger.warning(f"Failed to load model versions: {e}")
    
    def _load_model_by_version(self, version: str):
        """Load specific model version."""
        try:
            model_file = self.model_dir / f"model_{version}.pkl"
            if model_file.exists():
                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.models[version] = model_data["model"]
                if "scaler" in model_data:
                    self.feature_scaler = model_data["scaler"]
                    
                logger.info(f"Loaded model version {version}")
            
        except Exception as e:
            logger.error(f"Failed to load model version {version}: {e}")
    
    def _save_model_version(self, version: str, model: Any, scaler: Any = None):
        """Save model version to disk."""
        try:
            model_file = self.model_dir / f"model_{version}.pkl"
            model_data = {"model": model}
            if scaler:
                model_data["scaler"] = scaler
            
            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            # Update versions file
            versions_file = self.model_dir / "versions.json"
            versions_data = [
                {
                    "version": v.version,
                    "created_at": v.created_at.isoformat(),
                    "model_type": v.model_type,
                    "performance_metrics": v.performance_metrics,
                    "feature_importance": v.feature_importance,
                    "training_data_size": v.training_data_size,
                    "validation_score": v.validation_score,
                    "is_active": v.is_active
                }
                for v in self.model_versions
            ]
            
            with open(versions_file, 'w') as f:
                json.dump(versions_data, f, indent=2)
                
            logger.info(f"Saved model version {version}")
            
        except Exception as e:
            logger.error(f"Failed to save model version {version}: {e}")
    
    def train_ensemble_model(self, 
                           training_data: List[Dict[str, Any]],
                           target_column: str = "actual_size",
                           test_size: float = 0.2) -> str:
        """Train ensemble model with multiple algorithms."""
        if len(training_data) < 10:
            raise ValueError("Insufficient training data (minimum 10 samples required)")
        
        # Prepare data
        df = pd.DataFrame(training_data)
        X, y = self._prepare_features(df, target_column)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Train ensemble models
        models = {
            "random_forest": RandomForestRegressor(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                n_jobs=-1
            ),
            "gradient_boosting": GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ),
            "linear_regression": LinearRegression()
        }
        
        trained_models = {}
        model_scores = {}
        feature_importance = {}
        
        for name, model in models.items():
            # Train model
            if name == "linear_regression":
                model.fit(X_train_scaled, y_train)
                y_pred = model.predict(X_test_scaled)
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            
            # Evaluate
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
            
            trained_models[name] = model
            model_scores[name] = {
                "mae": mae,
                "r2": r2,
                "cv_mean": cv_scores.mean(),
                "cv_std": cv_scores.std()
            }
            
            # Feature importance (if available)
            if hasattr(model, 'feature_importances_'):
                importance_dict = dict(zip(X.columns, model.feature_importances_))
                feature_importance[name] = importance_dict
        
        # Create ensemble (weighted average based on R²)
        weights = {name: max(0, scores["r2"]) for name, scores in model_scores.items()}
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {name: w/total_weight for name, w in weights.items()}
        else:
            weights = {name: 1/len(weights) for name in weights.keys()}
        
        # Create version
        version = self._generate_version_id(training_data)
        
        # Ensemble predictions for validation
        ensemble_pred = np.zeros(len(X_test))
        for name, weight in weights.items():
            model = trained_models[name]
            if name == "linear_regression":
                pred = model.predict(X_test_scaled)
            else:
                pred = model.predict(X_test)
            ensemble_pred += weight * pred
        
        # Calculate ensemble performance
        ensemble_mae = mean_absolute_error(y_test, ensemble_pred)
        ensemble_r2 = r2_score(y_test, ensemble_pred)
        
        # Combine feature importance
        combined_importance = {}
        for feature in X.columns:
            weighted_importance = 0
            for name, weight in weights.items():
                if name in feature_importance:
                    weighted_importance += weight * feature_importance[name].get(feature, 0)
            combined_importance[feature] = weighted_importance
        
        # Create model version
        model_version = ModelVersion(
            version=version,
            created_at=datetime.now(),
            model_type="ensemble",
            performance_metrics={
                "ensemble_mae": ensemble_mae,
                "ensemble_r2": ensemble_r2,
                "individual_scores": model_scores,
                "model_weights": weights
            },
            feature_importance=combined_importance,
            training_data_size=len(training_data),
            validation_score=ensemble_r2,
            is_active=False
        )
        
        # Store models
        ensemble_model = {
            "models": trained_models,
            "weights": weights,
            "scaler": self.feature_scaler,
            "feature_columns": list(X.columns)
        }
        
        self.models[version] = ensemble_model
        self.model_versions.append(model_version)
        self._save_model_version(version, ensemble_model, self.feature_scaler)
        
        logger.info(f"Trained ensemble model {version} with R² = {ensemble_r2:.4f}")
        return version
    
    def _prepare_features(self, df: pd.DataFrame, target_column: str) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features from dataframe."""
        # Extract features from manuscript data if needed
        feature_columns = []
        
        if 'manuscript' in df.columns:
            # Extract features from manuscript column
            manuscript_features = []
            for _, row in df.iterrows():
                manuscript = row['manuscript']
                features = self._extract_manuscript_features(manuscript)
                manuscript_features.append(features)
            
            feature_df = pd.DataFrame(manuscript_features)
            feature_columns.extend(feature_df.columns)
            df = pd.concat([df.reset_index(drop=True), feature_df.reset_index(drop=True)], axis=1)
        
        # Select feature columns (exclude target and metadata)
        exclude_columns = [target_column, 'manuscript', 'prediction_id', 'created_at']
        feature_columns = [col for col in df.columns if col not in exclude_columns and pd.api.types.is_numeric_dtype(df[col])]
        
        X = df[feature_columns].fillna(0)  # Handle missing values
        y = df[target_column]
        
        return X, y
    
    def _extract_manuscript_features(self, manuscript: Dict[str, Any]) -> Dict[str, float]:
        """Extract numerical features from manuscript data."""
        features = {}
        
        # Text-based features
        text_content = ""
        for key in ['title', 'abstract', 'introduction', 'methods', 'results', 'discussion']:
            if key in manuscript and manuscript[key]:
                text_content += str(manuscript[key]) + " "
        
        features['word_count'] = len(text_content.split())
        features['char_count'] = len(text_content)
        features['sentence_count'] = text_content.count('.') + text_content.count('!') + text_content.count('?')
        
        # Metadata features
        if 'metadata' in manuscript:
            metadata = manuscript['metadata']
            features['reference_count'] = metadata.get('reference_count', 0)
            features['figure_count'] = metadata.get('figure_count', 0)
            features['table_count'] = metadata.get('table_count', 0)
        
        # Calculate derived features
        features['references_per_1k_words'] = (features['reference_count'] / max(features['word_count'], 1)) * 1000
        features['figures_per_1k_words'] = (features['figure_count'] / max(features['word_count'], 1)) * 1000
        features['avg_sentence_length'] = features['word_count'] / max(features['sentence_count'], 1)
        
        # Content type encoding (if available)
        if 'content_type' in manuscript:
            content_type = manuscript['content_type']
            type_mapping = {
                'clinical_trial': 1.2,
                'systematic_review': 1.5,
                'observational': 1.0,
                'case_study': 0.8,
                'letter': 0.3,
                'editorial': 0.5
            }
            features['content_type_multiplier'] = type_mapping.get(content_type, 1.0)
        else:
            features['content_type_multiplier'] = 1.0
        
        return features
    
    def predict_with_uncertainty(self, 
                                input_data: Dict[str, Any],
                                model_version: Optional[str] = None) -> PredictionResult:
        """Make prediction with uncertainty estimation and explanation."""
        if model_version is None:
            model_version = self.active_model_version
        
        if model_version not in self.models:
            raise ValueError(f"Model version {model_version} not found")
        
        model = self.models[model_version]
        
        # Prepare features
        df = pd.DataFrame([input_data])
        features = self._extract_manuscript_features(input_data)
        feature_df = pd.DataFrame([features])
        
        X = feature_df[model["feature_columns"]]
        
        # Make predictions with ensemble
        predictions = []
        feature_contributions = {}
        
        for name, individual_model in model["models"].items():
            weight = model["weights"][name]
            
            if name == "linear_regression":
                X_scaled = model["scaler"].transform(X)
                pred = individual_model.predict(X_scaled)[0]
            else:
                pred = individual_model.predict(X)[0]
            
            predictions.append(pred * weight)
            
            # Feature contributions (for tree-based models)
            if hasattr(individual_model, 'feature_importances_'):
                importances = individual_model.feature_importances_
                for i, feature in enumerate(X.columns):
                    if feature not in feature_contributions:
                        feature_contributions[feature] = 0
                    feature_contributions[feature] += weight * importances[i] * X.iloc[0, i]
        
        # Ensemble prediction
        ensemble_pred = sum(predictions)
        
        # Uncertainty estimation (using prediction variance)
        individual_preds = []
        for name, individual_model in model["models"].items():
            if name == "linear_regression":
                X_scaled = model["scaler"].transform(X)
                pred = individual_model.predict(X_scaled)[0]
            else:
                pred = individual_model.predict(X)[0]
            individual_preds.append(pred)
        
        prediction_std = np.std(individual_preds)
        uncertainty_range = (
            ensemble_pred - 1.96 * prediction_std,
            ensemble_pred + 1.96 * prediction_std
        )
        
        # Confidence score based on model agreement
        confidence_score = 1.0 / (1.0 + prediction_std / abs(ensemble_pred))
        
        # Anomaly detection
        anomaly_score = self._calculate_anomaly_score(features)
        is_anomaly = anomaly_score > self.anomaly_threshold
        
        # Generate explanation
        explanation = self._generate_explanation(
            ensemble_pred, feature_contributions, is_anomaly, model_version
        )
        
        return PredictionResult(
            predicted_value=ensemble_pred,
            confidence_score=confidence_score,
            uncertainty_range=uncertainty_range,
            feature_contributions=feature_contributions,
            model_version=model_version,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            explanation=explanation
        )
    
    def _calculate_anomaly_score(self, features: Dict[str, float]) -> float:
        """Calculate anomaly score based on feature distributions."""
        if not self.baseline_stats:
            return 0.0  # No baseline available
        
        anomaly_score = 0.0
        feature_count = 0
        
        for feature, value in features.items():
            if feature in self.baseline_stats:
                baseline = self.baseline_stats[feature]
                mean = baseline.get("mean", value)
                std = baseline.get("std", 1.0)
                
                if std > 0:
                    z_score = abs(value - mean) / std
                    anomaly_score += z_score
                    feature_count += 1
        
        return anomaly_score / max(feature_count, 1)
    
    def _generate_explanation(self, 
                            prediction: float,
                            feature_contributions: Dict[str, float],
                            is_anomaly: bool,
                            model_version: str) -> str:
        """Generate human-readable explanation for prediction."""
        explanation_parts = []
        
        # Base prediction
        explanation_parts.append(f"Predicted size: {self._format_bytes(prediction)}")
        
        # Top contributing factors
        sorted_contributions = sorted(
            feature_contributions.items(), 
            key=lambda x: abs(x[1]), 
            reverse=True
        )[:3]
        
        if sorted_contributions:
            explanation_parts.append("Key factors:")
            for feature, contribution in sorted_contributions:
                impact = "increases" if contribution > 0 else "decreases"
                feature_name = feature.replace('_', ' ').title()
                explanation_parts.append(f"• {feature_name} {impact} size prediction")
        
        # Anomaly warning
        if is_anomaly:
            explanation_parts.append("⚠️ This input appears unusual compared to training data")
        
        # Model info
        model_info = next((v for v in self.model_versions if v.version == model_version), None)
        if model_info:
            explanation_parts.append(f"Using {model_info.model_type} model (v{model_version[:8]})")
        
        return " | ".join(explanation_parts)
    
    def _format_bytes(self, bytes_value: float) -> str:
        """Format bytes into human-readable format."""
        if bytes_value < 1024:
            return f"{bytes_value:.0f} B"
        elif bytes_value < 1024**2:
            return f"{bytes_value/1024:.1f} KB"
        elif bytes_value < 1024**3:
            return f"{bytes_value/(1024**2):.1f} MB"
        else:
            return f"{bytes_value/(1024**3):.1f} GB"
    
    def start_ab_test(self, test_model_version: str, traffic_split: float = 0.1):
        """Start A/B testing between current active model and test model."""
        if test_model_version not in self.models:
            raise ValueError(f"Test model version {test_model_version} not found")
        
        self.ab_test_config = {
            "enabled": True,
            "test_model_version": test_model_version,
            "control_model_version": self.active_model_version,
            "traffic_split": traffic_split
        }
        
        logger.info(f"Started A/B test: {traffic_split*100}% traffic to {test_model_version}")
    
    def stop_ab_test(self):
        """Stop current A/B test."""
        self.ab_test_config["enabled"] = False
        logger.info("Stopped A/B test")
    
    def get_ab_test_recommendation(self, min_samples: int = 100) -> Optional[str]:
        """Get recommendation for A/B test winner."""
        if not self.ab_test_config["enabled"]:
            return None
        
        # This would analyze actual performance metrics from database
        # For now, return placeholder logic
        return "insufficient_data"
    
    def activate_model_version(self, version: str):
        """Activate a specific model version."""
        if version not in self.models:
            raise ValueError(f"Model version {version} not found")
        
        # Deactivate current active model
        for v in self.model_versions:
            v.is_active = False
        
        # Activate new model
        version_obj = next((v for v in self.model_versions if v.version == version), None)
        if version_obj:
            version_obj.is_active = True
        
        self.active_model_version = version
        self._save_model_version(version, self.models[version])
        
        logger.info(f"Activated model version {version}")
    
    def _generate_version_id(self, training_data: List[Dict[str, Any]]) -> str:
        """Generate unique version ID based on training data."""
        data_hash = hashlib.md5(json.dumps(training_data, sort_keys=True).encode()).hexdigest()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"{timestamp}_{data_hash[:8]}"
    
    def update_baseline_stats(self, training_data: List[Dict[str, Any]]):
        """Update baseline statistics for anomaly detection."""
        df = pd.DataFrame(training_data)
        
        # Calculate baseline stats for manuscript features
        all_features = []
        for _, row in df.iterrows():
            if 'manuscript' in row:
                features = self._extract_manuscript_features(row['manuscript'])
                all_features.append(features)
        
        if all_features:
            features_df = pd.DataFrame(all_features)
            self.baseline_stats = {
                col: {
                    "mean": features_df[col].mean(),
                    "std": features_df[col].std(),
                    "min": features_df[col].min(),
                    "max": features_df[col].max()
                }
                for col in features_df.columns
            }
            
            logger.info(f"Updated baseline statistics for {len(self.baseline_stats)} features")
    
    def get_model_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive model performance report."""
        if not self.model_versions:
            return {"status": "no_models"}
        
        active_model = next((v for v in self.model_versions if v.is_active), None)
        
        report = {
            "total_models": len(self.model_versions),
            "active_model": {
                "version": active_model.version if active_model else None,
                "performance": active_model.performance_metrics if active_model else None,
                "created_at": active_model.created_at.isoformat() if active_model else None
            },
            "model_history": [
                {
                    "version": v.version,
                    "model_type": v.model_type,
                    "validation_score": v.validation_score,
                    "training_data_size": v.training_data_size,
                    "created_at": v.created_at.isoformat(),
                    "is_active": v.is_active
                }
                for v in sorted(self.model_versions, key=lambda x: x.created_at, reverse=True)
            ],
            "ab_test_status": self.ab_test_config,
            "baseline_stats_available": bool(self.baseline_stats)
        }
        
        return report


# Global advanced predictor instance
_advanced_predictor: Optional[AdvancedPredictor] = None


def get_advanced_predictor() -> AdvancedPredictor:
    """Get global advanced predictor instance."""
    global _advanced_predictor
    if _advanced_predictor is None:
        _advanced_predictor = AdvancedPredictor()
    return _advanced_predictor


if __name__ == "__main__":
    # Example usage
    predictor = AdvancedPredictor()
    
    # Sample training data
    training_data = [
        {
            "manuscript": {
                "title": "Clinical Trial Analysis",
                "abstract": "This study analyzes...",
                "metadata": {"word_count": 4500, "reference_count": 25, "figure_count": 5}
            },
            "actual_size": 2400000  # 2.4 MB
        },
        {
            "manuscript": {
                "title": "Systematic Review",
                "abstract": "Comprehensive review...",
                "metadata": {"word_count": 8000, "reference_count": 150, "figure_count": 12}
            },
            "actual_size": 8100000  # 8.1 MB
        }
    ]
    
    # Train ensemble model
    version = predictor.train_ensemble_model(training_data)
    predictor.activate_model_version(version)
    
    # Make prediction with uncertainty
    test_input = {
        "title": "New Research Study",
        "abstract": "Innovative study on...",
        "metadata": {"word_count": 6000, "reference_count": 40, "figure_count": 8}
    }
    
    result = predictor.predict_with_uncertainty(test_input)
    print(f"Prediction: {result.predicted_value:,.0f} bytes")
    print(f"Confidence: {result.confidence_score:.2%}")
    print(f"Uncertainty range: {result.uncertainty_range[0]:,.0f} - {result.uncertainty_range[1]:,.0f}")
    print(f"Explanation: {result.explanation}")
    print(f"Is anomaly: {result.is_anomaly}")