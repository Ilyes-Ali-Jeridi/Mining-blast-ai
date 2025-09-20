"""
Residual learning pipeline for physics model corrections.

This module implements XGBoost-based residual learning to improve physics model
predictions using post-blast measurement data. It provides feature engineering,
model training, validation, and integration with physics models.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Union, Any
import logging
from datetime import datetime, timedelta
import pickle
import json
from pathlib import Path
from dataclasses import dataclass, asdict

from .data_structures import ModelMetrics, FragmentationResult
from ..physics_models import KuzRamModel, PPVModel, BlastParameters

logger = logging.getLogger(__name__)


@dataclass
class FeatureEngineeringConfig:
    """Configuration for feature engineering"""
    include_interaction_terms: bool = True
    include_polynomial_features: bool = True
    polynomial_degree: int = 2
    normalize_features: bool = True
    feature_selection_threshold: float = 0.01  # Minimum feature importance
    

@dataclass
class ModelPerformanceMetrics:
    """Extended performance metrics for monitoring"""
    timestamp: datetime
    model_version: str
    training_samples: int
    validation_r2: float
    validation_rmse: float
    validation_mae: float
    feature_importance: Dict[str, float]
    prediction_bias: float  # Mean residual
    prediction_variance: float  # Variance of residuals
    confidence_interval_coverage: float  # % of predictions within CI
    is_reliable: bool
    reliability_score: float  # 0-1 overall reliability
    drift_detected: bool = False
    performance_degradation: float = 0.0  # Compared to previous model


@dataclass
class RetrainingRecommendation:
    """Recommendation for model retraining"""
    should_retrain: bool
    urgency: str  # "low", "medium", "high", "critical"
    reasons: List[str]
    new_data_count: int
    performance_change: float
    estimated_improvement: float
    recommended_action: str


class ResidualLearner:
    """XGBoost model for learning physics model corrections"""
    
    def __init__(self, 
                 model_save_path: Optional[str] = None,
                 feature_columns: Optional[List[str]] = None,
                 feature_config: Optional[FeatureEngineeringConfig] = None):
        """
        Initialize residual learner.
        
        Args:
            model_save_path: Path to save/load trained models
            feature_columns: List of feature column names for training
            feature_config: Configuration for feature engineering
        """
        self.model_save_path = model_save_path or "models/residual_model.pkl"
        self.feature_columns = feature_columns or self._get_default_feature_columns()
        self.feature_config = feature_config or FeatureEngineeringConfig()
        
        # Model components
        self.model = None
        self.is_trained = False
        self.feature_scaler = None
        self.target_scaler = None
        self.feature_selector = None
        
        # Training metadata
        self.training_history = []
        self.performance_history: List[ModelPerformanceMetrics] = []
        self.model_version = "1.0"
        self.last_training_date = None
        
        # Performance thresholds
        self.min_r2_threshold = 0.3  # Minimum R² for reliable model
        self.min_samples_threshold = 50  # Minimum samples for training
        self.performance_degradation_threshold = 0.1  # 10% degradation triggers retraining
        self.drift_detection_window = 100  # Number of recent predictions to monitor
        
        # Physics model integration
        self.kuz_ram_model = None
        self.ppv_model = None
        
        # Data storage for monitoring
        self.recent_predictions = []
        self.recent_actuals = []
        self.prediction_timestamps = []
        
    def train_residual_model(self, 
                           blast_features: np.ndarray,
                           physics_predictions: np.ndarray,
                           measured_values: np.ndarray,
                           validation_split: float = 0.2,
                           cross_validation_folds: int = 5) -> ModelMetrics:
        """
        Train model to predict (measured - physics_predicted).
        
        Args:
            blast_features: Feature matrix (n_samples, n_features)
            physics_predictions: Physics model predictions
            measured_values: Actual measured values
            validation_split: Fraction of data for validation
            cross_validation_folds: Number of CV folds
            
        Returns:
            ModelMetrics with training performance
        """
        try:
            # Import XGBoost
            try:
                import xgboost as xgb
                from sklearn.model_selection import train_test_split, cross_val_score
                from sklearn.preprocessing import StandardScaler
                from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
            except ImportError:
                raise ImportError(
                    "Required packages not installed. Please install with: "
                    "pip install xgboost scikit-learn"
                )
            
            logger.info("Starting residual model training")
            
            # Validate inputs
            if len(blast_features) < self.min_samples_threshold:
                raise ValueError(f"Insufficient training samples: {len(blast_features)} < {self.min_samples_threshold}")
            
            # Calculate residuals (target variable)
            residuals = measured_values - physics_predictions
            
            # Prepare features
            if blast_features.shape[1] != len(self.feature_columns):
                logger.warning(f"Feature dimension mismatch: {blast_features.shape[1]} vs {len(self.feature_columns)}")
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                blast_features, residuals, test_size=validation_split, random_state=42
            )
            
            # Scale features
            self.feature_scaler = StandardScaler()
            X_train_scaled = self.feature_scaler.fit_transform(X_train)
            X_val_scaled = self.feature_scaler.transform(X_val)
            
            # Train XGBoost model
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            
            # Fit model
            self.model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                early_stopping_rounds=10,
                verbose=False
            )
            
            # Make predictions
            train_pred = self.model.predict(X_train_scaled)
            val_pred = self.model.predict(X_val_scaled)
            
            # Calculate metrics
            train_r2 = r2_score(y_train, train_pred)
            train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
            train_mae = mean_absolute_error(y_train, train_pred)
            
            val_r2 = r2_score(y_val, val_pred)
            val_rmse = np.sqrt(mean_squared_error(y_val, val_pred))
            val_mae = mean_absolute_error(y_val, val_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(
                self.model, X_train_scaled, y_train, 
                cv=cross_validation_folds, scoring='r2'
            )
            
            cv_rmse_scores = -cross_val_score(
                self.model, X_train_scaled, y_train,
                cv=cross_validation_folds, scoring='neg_root_mean_squared_error'
            )
            
            # Feature importance
            feature_importance = {}
            if hasattr(self.model, 'feature_importances_'):
                for i, importance in enumerate(self.model.feature_importances_):
                    feature_name = self.feature_columns[i] if i < len(self.feature_columns) else f"feature_{i}"
                    feature_importance[feature_name] = float(importance)
            
            # Assess reliability
            is_reliable = (
                val_r2 >= self.min_r2_threshold and
                len(blast_features) >= self.min_samples_threshold and
                abs(train_r2 - val_r2) < 0.2  # Not overfitting
            )
            
            reliability_flags = []
            if val_r2 < self.min_r2_threshold:
                reliability_flags.append(f"Low validation R²: {val_r2:.3f}")
            if abs(train_r2 - val_r2) >= 0.2:
                reliability_flags.append("Potential overfitting detected")
            if len(blast_features) < 100:
                reliability_flags.append("Limited training data")
            
            # Create metrics object
            metrics = ModelMetrics(
                train_r2=train_r2,
                train_rmse=train_rmse,
                train_mae=train_mae,
                val_r2=val_r2,
                val_rmse=val_rmse,
                val_mae=val_mae,
                cv_r2_mean=np.mean(cv_scores),
                cv_r2_std=np.std(cv_scores),
                cv_rmse_mean=np.mean(cv_rmse_scores),
                cv_rmse_std=np.std(cv_rmse_scores),
                feature_importance=feature_importance,
                model_version=self.model_version,
                training_samples=len(blast_features),
                training_timestamp=datetime.now(),
                is_reliable=is_reliable,
                reliability_flags=reliability_flags
            )
            
            # Update training state
            self.is_trained = True
            self.last_training_date = datetime.now()
            self.training_history.append(metrics)
            
            # Save model if path provided
            if self.model_save_path:
                self.save_model()
            
            logger.info(f"Model training completed. Validation R²: {val_r2:.3f}, "
                       f"Reliable: {is_reliable}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training residual model: {str(e)}")
            raise
    
    def predict_correction(self, blast_features: np.ndarray) -> np.ndarray:
        """
        Predict correction to add to physics model.
        
        Args:
            blast_features: Feature matrix for prediction
            
        Returns:
            Predicted corrections
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained, returning zero corrections")
            return np.zeros(len(blast_features))
        
        try:
            # Scale features
            if self.feature_scaler is not None:
                features_scaled = self.feature_scaler.transform(blast_features)
            else:
                features_scaled = blast_features
            
            # Predict corrections
            corrections = self.model.predict(features_scaled)
            
            return corrections
            
        except Exception as e:
            logger.error(f"Error predicting corrections: {str(e)}")
            return np.zeros(len(blast_features))
    
    def update_model(self, 
                    new_blast_features: np.ndarray,
                    new_physics_predictions: np.ndarray,
                    new_measured_values: np.ndarray) -> ModelMetrics:
        """
        Update model with new data (incremental learning).
        
        Args:
            new_blast_features: New feature data
            new_physics_predictions: New physics predictions
            new_measured_values: New measured values
            
        Returns:
            Updated model metrics
        """
        if not self.is_trained:
            # If no existing model, train from scratch
            return self.train_residual_model(
                new_blast_features, new_physics_predictions, new_measured_values
            )
        
        # For XGBoost, we need to retrain with combined data
        # In a production system, you might implement true incremental learning
        logger.info("Retraining model with new data (full retrain)")
        
        # This is a simplified approach - in practice, you'd want to store
        # previous training data and combine it with new data
        return self.train_residual_model(
            new_blast_features, new_physics_predictions, new_measured_values
        )
    
    def save_model(self, path: Optional[str] = None) -> None:
        """Save trained model to disk"""
        
        if not self.is_trained:
            raise ValueError("No trained model to save")
        
        save_path = path or self.model_save_path
        save_dir = Path(save_path).parent
        save_dir.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_scaler': self.feature_scaler,
            'target_scaler': self.target_scaler,
            'feature_columns': self.feature_columns,
            'model_version': self.model_version,
            'training_history': self.training_history,
            'last_training_date': self.last_training_date,
            'is_trained': self.is_trained
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, path: Optional[str] = None) -> bool:
        """
        Load trained model from disk.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        load_path = path or self.model_save_path
        
        if not Path(load_path).exists():
            logger.warning(f"Model file not found: {load_path}")
            return False
        
        try:
            with open(load_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.feature_scaler = model_data.get('feature_scaler')
            self.target_scaler = model_data.get('target_scaler')
            self.feature_columns = model_data.get('feature_columns', self.feature_columns)
            self.model_version = model_data.get('model_version', '1.0')
            self.training_history = model_data.get('training_history', [])
            self.last_training_date = model_data.get('last_training_date')
            self.is_trained = model_data.get('is_trained', False)
            
            logger.info(f"Model loaded from {load_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, any]:
        """Get information about the current model"""
        
        if not self.is_trained:
            return {
                'is_trained': False,
                'message': 'No model trained'
            }
        
        latest_metrics = self.training_history[-1] if self.training_history else None
        
        return {
            'is_trained': self.is_trained,
            'model_version': self.model_version,
            'last_training_date': self.last_training_date,
            'training_samples': latest_metrics.training_samples if latest_metrics else 0,
            'validation_r2': latest_metrics.val_r2 if latest_metrics else 0,
            'is_reliable': latest_metrics.is_reliable if latest_metrics else False,
            'feature_count': len(self.feature_columns),
            'training_history_count': len(self.training_history)
        }
    
    def extract_blast_features(self, blast_data: Dict) -> np.ndarray:
        """
        Extract and engineer features from blast data for model input.
        
        Args:
            blast_data: Dictionary containing blast parameters
            
        Returns:
            Engineered feature array for model input
        """
        # Extract base features
        base_features = []
        feature_names = []
        
        for feature_name in self.feature_columns:
            if feature_name in blast_data:
                base_features.append(blast_data[feature_name])
                feature_names.append(feature_name)
            else:
                # Handle missing features with defaults
                default_value = self._get_default_feature_value(feature_name)
                base_features.append(default_value)
                feature_names.append(feature_name)
                logger.warning(f"Missing feature {feature_name}, using default: {default_value}")
        
        base_array = np.array(base_features).reshape(1, -1)
        
        # Apply feature engineering
        engineered_features = self._engineer_features(base_array, feature_names)
        
        return engineered_features
    
    def _engineer_features(self, base_features: np.ndarray, feature_names: List[str]) -> np.ndarray:
        """
        Apply feature engineering transformations.
        
        Args:
            base_features: Base feature matrix
            feature_names: Names of base features
            
        Returns:
            Engineered feature matrix
        """
        features = base_features.copy()
        
        if self.feature_config.include_interaction_terms:
            features = self._add_interaction_terms(features, feature_names)
        
        if self.feature_config.include_polynomial_features:
            features = self._add_polynomial_features(features)
        
        # Add domain-specific engineered features
        features = self._add_domain_features(features, feature_names)
        
        return features
    
    def _add_interaction_terms(self, features: np.ndarray, feature_names: List[str]) -> np.ndarray:
        """Add interaction terms between key features"""
        
        # Key interactions for blast analysis
        interactions = []
        
        # Find indices of key features
        feature_indices = {name: i for i, name in enumerate(feature_names)}
        
        # Burden × Spacing (blast pattern area)
        if 'burden_m' in feature_indices and 'spacing_m' in feature_indices:
            burden_idx = feature_indices['burden_m']
            spacing_idx = feature_indices['spacing_m']
            interactions.append(features[:, burden_idx] * features[:, spacing_idx])
        
        # Powder Factor × Rock Density (energy per unit rock mass)
        if 'powder_factor_kg_m3' in feature_indices and 'rock_density_kg_m3' in feature_indices:
            pf_idx = feature_indices['powder_factor_kg_m3']
            density_idx = feature_indices['rock_density_kg_m3']
            interactions.append(features[:, pf_idx] * features[:, density_idx])
        
        # Explosive RWS × VOD (explosive energy characteristics)
        if 'explosive_rws' in feature_indices and 'explosive_vod_m_s' in feature_indices:
            rws_idx = feature_indices['explosive_rws']
            vod_idx = feature_indices['explosive_vod_m_s']
            interactions.append(features[:, rws_idx] * features[:, vod_idx])
        
        # Hole Diameter × Bench Height (hole volume factor)
        if 'hole_diameter_mm' in feature_indices and 'bench_height_m' in feature_indices:
            diameter_idx = feature_indices['hole_diameter_mm']
            height_idx = feature_indices['bench_height_m']
            interactions.append(features[:, diameter_idx] * features[:, height_idx])
        
        if interactions:
            interaction_matrix = np.column_stack(interactions)
            features = np.column_stack([features, interaction_matrix])
        
        return features
    
    def _add_polynomial_features(self, features: np.ndarray) -> np.ndarray:
        """Add polynomial features for key variables"""
        
        try:
            from sklearn.preprocessing import PolynomialFeatures
        except ImportError:
            logger.warning("scikit-learn not available, skipping polynomial features")
            return features
        
        # Only apply to first few most important features to avoid explosion
        max_features_for_poly = min(8, features.shape[1])
        
        poly = PolynomialFeatures(
            degree=self.feature_config.polynomial_degree,
            interaction_only=False,
            include_bias=False
        )
        
        poly_features = poly.fit_transform(features[:, :max_features_for_poly])
        
        # Combine with remaining original features
        if features.shape[1] > max_features_for_poly:
            remaining_features = features[:, max_features_for_poly:]
            features = np.column_stack([poly_features, remaining_features])
        else:
            features = poly_features
        
        return features
    
    def _add_domain_features(self, features: np.ndarray, feature_names: List[str]) -> np.ndarray:
        """Add domain-specific engineered features"""
        
        domain_features = []
        feature_indices = {name: i for i, name in enumerate(feature_names)}
        
        # Burden-to-diameter ratio (critical for fragmentation)
        if 'burden_m' in feature_indices and 'hole_diameter_mm' in feature_indices:
            burden_idx = feature_indices['burden_m']
            diameter_idx = feature_indices['hole_diameter_mm']
            # Convert diameter to meters for ratio
            burden_diameter_ratio = features[:, burden_idx] / (features[:, diameter_idx] / 1000.0)
            domain_features.append(burden_diameter_ratio)
        
        # Stemming ratio (stemming length / bench height)
        if 'stemming_length_m' in feature_indices and 'bench_height_m' in feature_indices:
            stemming_idx = feature_indices['stemming_length_m']
            height_idx = feature_indices['bench_height_m']
            stemming_ratio = features[:, stemming_idx] / features[:, height_idx]
            domain_features.append(stemming_ratio)
        
        # Specific charge (kg/m³ of rock)
        if 'charge_per_hole_kg' in feature_indices and 'burden_m' in feature_indices and 'spacing_m' in feature_indices and 'bench_height_m' in feature_indices:
            charge_idx = feature_indices['charge_per_hole_kg']
            burden_idx = feature_indices['burden_m']
            spacing_idx = feature_indices['spacing_m']
            height_idx = feature_indices['bench_height_m']
            
            rock_volume = features[:, burden_idx] * features[:, spacing_idx] * features[:, height_idx]
            specific_charge = features[:, charge_idx] / rock_volume
            domain_features.append(specific_charge)
        
        # Rock strength to explosive energy ratio
        if 'ucs_mpa' in feature_indices and 'explosive_rws' in feature_indices:
            ucs_idx = feature_indices['ucs_mpa']
            rws_idx = feature_indices['explosive_rws']
            strength_energy_ratio = features[:, ucs_idx] / features[:, rws_idx]
            domain_features.append(strength_energy_ratio)
        
        if domain_features:
            domain_matrix = np.column_stack(domain_features)
            features = np.column_stack([features, domain_matrix])
        
        return features
    
    def _get_default_feature_columns(self) -> List[str]:
        """Get default feature columns for blast analysis"""
        
        return [
            # Blast geometry
            'burden_m',
            'spacing_m', 
            'bench_height_m',
            'hole_diameter_mm',
            'hole_depth_m',
            
            # Explosives
            'powder_factor_kg_m3',
            'charge_per_hole_kg',
            'explosive_density_kg_m3',
            'explosive_rws',
            'explosive_vod_m_s',
            
            # Rock properties
            'rock_density_kg_m3',
            'ucs_mpa',
            'rock_factor_a',
            
            # Operational
            'stemming_length_m',
            'delay_timing_ms',
            'number_of_holes',
            
            # Environmental
            'bench_face_angle_deg',
            'free_face_distance_m'
        ]
    
    def _get_default_feature_value(self, feature_name: str) -> float:
        """Get default value for missing features"""
        
        defaults = {
            'burden_m': 3.0,
            'spacing_m': 3.5,
            'bench_height_m': 12.0,
            'hole_diameter_mm': 165.0,
            'hole_depth_m': 13.0,
            'powder_factor_kg_m3': 0.3,
            'charge_per_hole_kg': 30.0,
            'explosive_density_kg_m3': 1200.0,
            'explosive_rws': 100.0,
            'explosive_vod_m_s': 5000.0,
            'rock_density_kg_m3': 2700.0,
            'ucs_mpa': 100.0,
            'rock_factor_a': 7.0,
            'stemming_length_m': 3.0,
            'delay_timing_ms': 25.0,
            'number_of_holes': 50.0,
            'bench_face_angle_deg': 70.0,
            'free_face_distance_m': 15.0
        }
        
        return defaults.get(feature_name, 0.0)
    
    def calculate_prediction_confidence(self, blast_features: np.ndarray) -> np.ndarray:
        """
        Calculate confidence intervals for predictions.
        
        Args:
            blast_features: Feature matrix
            
        Returns:
            Confidence scores (0-1)
        """
        if not self.is_trained or not self.training_history:
            return np.full(len(blast_features), 0.5)
        
        # Use latest model performance as baseline confidence
        latest_metrics = self.training_history[-1]
        base_confidence = latest_metrics.val_r2 if latest_metrics.val_r2 > 0 else 0.3
        
        # Adjust confidence based on feature similarity to training data
        # This is a simplified approach - in practice, you might use more sophisticated methods
        confidence_scores = np.full(len(blast_features), base_confidence)
        
        return np.clip(confidence_scores, 0.0, 1.0)
    
    def integrate_physics_models(self, kuz_ram_model: KuzRamModel, ppv_model: PPVModel) -> None:
        """
        Integrate physics models for correction predictions.
        
        Args:
            kuz_ram_model: Kuz-Ram fragmentation model
            ppv_model: PPV prediction model
        """
        self.kuz_ram_model = kuz_ram_model
        self.ppv_model = ppv_model
        logger.info("Physics models integrated for residual learning")
    
    def predict_with_physics_correction(self, 
                                      blast_params: BlastParameters,
                                      prediction_type: str = "fragmentation") -> Dict[str, Any]:
        """
        Make predictions using physics model with ML corrections.
        
        Args:
            blast_params: Blast parameters for prediction
            prediction_type: Type of prediction ("fragmentation" or "ppv")
            
        Returns:
            Dictionary with physics prediction, ML correction, and final prediction
        """
        if prediction_type == "fragmentation" and self.kuz_ram_model is None:
            raise ValueError("Kuz-Ram model not integrated")
        if prediction_type == "ppv" and self.ppv_model is None:
            raise ValueError("PPV model not integrated")
        
        # Get physics prediction
        if prediction_type == "fragmentation":
            physics_prediction = self.kuz_ram_model.predict_mean_fragment_size(blast_params)
            target_name = "mean_fragment_size_mm"
        else:
            # For PPV, we need charge weight and distance - simplified for now
            physics_prediction = 0.0  # Would need proper PPV calculation
            target_name = "ppv_mm_per_s"
        
        # Extract features for ML model
        blast_data = self._blast_params_to_dict(blast_params)
        features = self.extract_blast_features(blast_data)
        
        # Get ML correction
        ml_correction = self.predict_correction(features)[0] if self.is_trained else 0.0
        
        # Calculate confidence
        confidence = self.calculate_prediction_confidence(features)[0]
        
        # Apply correction with confidence weighting
        corrected_prediction = physics_prediction + (ml_correction * confidence)
        
        return {
            "physics_prediction": physics_prediction,
            "ml_correction": ml_correction,
            "corrected_prediction": corrected_prediction,
            "confidence": confidence,
            "prediction_type": prediction_type,
            "target": target_name
        }
    
    def _blast_params_to_dict(self, blast_params: BlastParameters) -> Dict[str, float]:
        """Convert BlastParameters to dictionary for feature extraction"""
        
        return {
            "burden_m": blast_params.burden,
            "spacing_m": blast_params.spacing,
            "bench_height_m": blast_params.bench_height,
            "hole_diameter_mm": blast_params.hole_diameter,
            "stemming_length_m": blast_params.stemming_length,
            "powder_factor_kg_m3": blast_params.powder_factor_kg_per_m3,
            "powder_factor_kg_per_t": blast_params.powder_factor_kg_per_t,
            "rock_density_kg_m3": blast_params.rock_density,
            "explosive_rws": blast_params.explosive_rws,
            "explosive_density_kg_m3": blast_params.explosive_density,
            # Derived features
            "charge_per_hole_kg": (blast_params.burden * blast_params.spacing * 
                                 blast_params.bench_height * blast_params.rock_density * 
                                 blast_params.powder_factor_kg_per_m3 / 1000.0),
            "hole_depth_m": blast_params.bench_height + blast_params.stemming_length,
            "number_of_holes": 1.0,  # Single hole analysis
            "delay_timing_ms": 25.0,  # Default delay
            "bench_face_angle_deg": 70.0,  # Default angle
            "free_face_distance_m": blast_params.burden,  # Approximate
            "ucs_mpa": 100.0,  # Default UCS - should be provided in blast_params
            "rock_factor_a": 7.0,  # Default rock factor
            "explosive_vod_m_s": 5000.0  # Default VOD - should be provided
        }
    
    def monitor_prediction_performance(self, 
                                     predicted_value: float,
                                     actual_value: float,
                                     prediction_timestamp: Optional[datetime] = None) -> None:
        """
        Monitor prediction performance for drift detection.
        
        Args:
            predicted_value: Model prediction
            actual_value: Actual measured value
            prediction_timestamp: When prediction was made
        """
        timestamp = prediction_timestamp or datetime.now()
        
        # Store recent predictions for monitoring
        self.recent_predictions.append(predicted_value)
        self.recent_actuals.append(actual_value)
        self.prediction_timestamps.append(timestamp)
        
        # Keep only recent data within window
        if len(self.recent_predictions) > self.drift_detection_window:
            self.recent_predictions.pop(0)
            self.recent_actuals.pop(0)
            self.prediction_timestamps.pop(0)
        
        # Check for performance degradation
        if len(self.recent_predictions) >= 20:  # Minimum for meaningful analysis
            self._check_performance_drift()
    
    def _check_performance_drift(self) -> bool:
        """
        Check for performance drift in recent predictions.
        
        Returns:
            True if drift detected
        """
        if len(self.recent_predictions) < 20:
            return False
        
        try:
            from sklearn.metrics import r2_score, mean_squared_error
            
            # Calculate recent performance
            recent_r2 = r2_score(self.recent_actuals, self.recent_predictions)
            recent_rmse = np.sqrt(mean_squared_error(self.recent_actuals, self.recent_predictions))
            
            # Compare with historical performance
            if self.performance_history:
                baseline_r2 = self.performance_history[-1].validation_r2
                baseline_rmse = self.performance_history[-1].validation_rmse
                
                r2_degradation = baseline_r2 - recent_r2
                rmse_increase = (recent_rmse - baseline_rmse) / baseline_rmse
                
                drift_detected = (r2_degradation > self.performance_degradation_threshold or
                                rmse_increase > self.performance_degradation_threshold)
                
                if drift_detected:
                    logger.warning(f"Performance drift detected: R² degradation: {r2_degradation:.3f}, "
                                 f"RMSE increase: {rmse_increase:.3f}")
                
                return drift_detected
        
        except Exception as e:
            logger.error(f"Error checking performance drift: {str(e)}")
        
        return False
    
    def get_retraining_recommendation(self, 
                                    new_data_count: int = 0) -> RetrainingRecommendation:
        """
        Generate recommendation for model retraining.
        
        Args:
            new_data_count: Number of new training samples available
            
        Returns:
            RetrainingRecommendation with detailed analysis
        """
        reasons = []
        urgency = "low"
        should_retrain = False
        performance_change = 0.0
        estimated_improvement = 0.0
        
        # Check if model exists
        if not self.is_trained:
            return RetrainingRecommendation(
                should_retrain=True,
                urgency="high",
                reasons=["No trained model exists"],
                new_data_count=new_data_count,
                performance_change=0.0,
                estimated_improvement=0.5,
                recommended_action="Train initial model with available data"
            )
        
        # Check data availability
        if new_data_count >= self.min_samples_threshold:
            reasons.append(f"Sufficient new data available ({new_data_count} samples)")
            should_retrain = True
            urgency = "medium"
            estimated_improvement = min(0.2, new_data_count / 200.0)  # Estimate based on data volume
        
        # Check performance drift
        drift_detected = self._check_performance_drift()
        if drift_detected:
            reasons.append("Performance drift detected in recent predictions")
            should_retrain = True
            urgency = "high"
            estimated_improvement += 0.15
        
        # Check model age
        if self.last_training_date:
            days_since_training = (datetime.now() - self.last_training_date).days
            if days_since_training > 90:  # 3 months
                reasons.append(f"Model is {days_since_training} days old")
                should_retrain = True
                if days_since_training > 180:  # 6 months
                    urgency = "medium"
        
        # Check performance history
        if len(self.performance_history) >= 2:
            recent_performance = self.performance_history[-1].validation_r2
            previous_performance = self.performance_history[-2].validation_r2
            performance_change = recent_performance - previous_performance
            
            if performance_change < -self.performance_degradation_threshold:
                reasons.append(f"Performance degraded by {abs(performance_change):.3f}")
                should_retrain = True
                urgency = "high"
        
        # Determine recommended action
        if urgency == "high":
            recommended_action = "Retrain immediately with all available data"
        elif urgency == "medium":
            recommended_action = "Schedule retraining within 1-2 weeks"
        elif should_retrain:
            recommended_action = "Consider retraining when convenient"
        else:
            recommended_action = "Continue monitoring, no retraining needed"
        
        return RetrainingRecommendation(
            should_retrain=should_retrain,
            urgency=urgency,
            reasons=reasons,
            new_data_count=new_data_count,
            performance_change=performance_change,
            estimated_improvement=estimated_improvement,
            recommended_action=recommended_action
        )
    
    def update_performance_metrics(self, metrics: ModelMetrics) -> None:
        """
        Update performance history with new metrics.
        
        Args:
            metrics: New model performance metrics
        """
        # Convert to extended metrics
        extended_metrics = ModelPerformanceMetrics(
            timestamp=datetime.now(),
            model_version=metrics.model_version,
            training_samples=metrics.training_samples,
            validation_r2=metrics.val_r2,
            validation_rmse=metrics.val_rmse,
            validation_mae=metrics.val_mae,
            feature_importance=metrics.feature_importance,
            prediction_bias=0.0,  # Would calculate from residuals
            prediction_variance=metrics.val_rmse ** 2,
            confidence_interval_coverage=0.95,  # Default assumption
            is_reliable=metrics.is_reliable,
            reliability_score=metrics.val_r2 if metrics.is_reliable else 0.0,
            drift_detected=self._check_performance_drift(),
            performance_degradation=0.0  # Calculate if previous metrics exist
        )
        
        # Calculate performance degradation if we have history
        if self.performance_history:
            previous_r2 = self.performance_history[-1].validation_r2
            extended_metrics.performance_degradation = previous_r2 - metrics.val_r2
        
        self.performance_history.append(extended_metrics)
        
        # Keep only recent history (last 10 models)
        if len(self.performance_history) > 10:
            self.performance_history.pop(0)
        
        logger.info(f"Performance metrics updated: R²={metrics.val_r2:.3f}, "
                   f"Reliable={metrics.is_reliable}")
    
    def export_model_diagnostics(self) -> Dict[str, Any]:
        """
        Export comprehensive model diagnostics for analysis.
        
        Returns:
            Dictionary with detailed model diagnostics
        """
        diagnostics = {
            "model_info": self.get_model_info(),
            "feature_config": asdict(self.feature_config),
            "performance_history": [asdict(m) for m in self.performance_history],
            "training_history": [asdict(m) for m in self.training_history],
            "retraining_recommendation": asdict(self.get_retraining_recommendation()),
            "recent_performance": {}
        }
        
        # Add recent performance if available
        if self.recent_predictions and self.recent_actuals:
            try:
                from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
                
                diagnostics["recent_performance"] = {
                    "sample_count": len(self.recent_predictions),
                    "r2_score": r2_score(self.recent_actuals, self.recent_predictions),
                    "rmse": np.sqrt(mean_squared_error(self.recent_actuals, self.recent_predictions)),
                    "mae": mean_absolute_error(self.recent_actuals, self.recent_predictions),
                    "prediction_bias": np.mean(np.array(self.recent_predictions) - np.array(self.recent_actuals)),
                    "time_range": {
                        "start": min(self.prediction_timestamps).isoformat(),
                        "end": max(self.prediction_timestamps).isoformat()
                    }
                }
            except Exception as e:
                diagnostics["recent_performance"]["error"] = str(e)
        
        return diagnostics