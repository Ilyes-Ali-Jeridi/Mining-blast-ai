"""
Tests for enhanced residual learning pipeline.

Tests feature engineering, model training, physics integration, and performance monitoring.
"""

import pytest
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.drill_blast_system.ml_pipeline.residual_learner import (
    ResidualLearner, 
    FeatureEngineeringConfig,
    ModelPerformanceMetrics,
    RetrainingRecommendation
)
from src.drill_blast_system.ml_pipeline.data_structures import ModelMetrics
from src.drill_blast_system.physics_models import KuzRamModel, PPVModel, BlastParameters


class TestFeatureEngineering:
    """Test feature engineering capabilities"""
    
    @pytest.fixture
    def learner(self):
        """Create residual learner with feature engineering enabled"""
        config = FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=True,
            polynomial_degree=2,
            normalize_features=True
        )
        return ResidualLearner(feature_config=config)
    
    @pytest.fixture
    def sample_blast_data(self):
        """Sample blast data for testing"""
        return {
            "burden_m": 3.0,
            "spacing_m": 3.5,
            "bench_height_m": 12.0,
            "hole_diameter_mm": 165.0,
            "stemming_length_m": 3.0,
            "powder_factor_kg_m3": 0.3,
            "charge_per_hole_kg": 30.0,
            "explosive_density_kg_m3": 1200.0,
            "explosive_rws": 100.0,
            "explosive_vod_m_s": 5000.0,
            "rock_density_kg_m3": 2700.0,
            "ucs_mpa": 100.0,
            "rock_factor_a": 7.0
        }
    
    def test_basic_feature_extraction(self, learner, sample_blast_data):
        """Test basic feature extraction without engineering"""
        learner.feature_config.include_interaction_terms = False
        learner.feature_config.include_polynomial_features = False
        
        features = learner.extract_blast_features(sample_blast_data)
        
        assert features.shape[0] == 1  # Single sample
        assert features.shape[1] >= len(learner.feature_columns)  # At least base features
    
    def test_interaction_terms(self, learner, sample_blast_data):
        """Test interaction term generation"""
        learner.feature_config.include_polynomial_features = False
        
        features = learner.extract_blast_features(sample_blast_data)
        
        # Should have more features than base columns due to interactions
        assert features.shape[1] > len(learner.feature_columns)
    
    def test_polynomial_features(self, learner, sample_blast_data):
        """Test polynomial feature generation"""
        learner.feature_config.include_interaction_terms = False
        
        with patch('sklearn.preprocessing.PolynomialFeatures') as mock_poly:
            mock_poly_instance = Mock()
            mock_poly_instance.fit_transform.return_value = np.random.rand(1, 50)
            mock_poly.return_value = mock_poly_instance
            
            features = learner.extract_blast_features(sample_blast_data)
            
            mock_poly.assert_called_once()
            mock_poly_instance.fit_transform.assert_called_once()
    
    def test_domain_specific_features(self, learner, sample_blast_data):
        """Test domain-specific feature engineering"""
        features = learner.extract_blast_features(sample_blast_data)
        
        # Should include engineered features like burden-diameter ratio, stemming ratio, etc.
        assert features.shape[1] > len(learner.feature_columns)
    
    def test_missing_feature_handling(self, learner):
        """Test handling of missing features"""
        incomplete_data = {
            "burden_m": 3.0,
            "spacing_m": 3.5
            # Missing other required features
        }
        
        features = learner.extract_blast_features(incomplete_data)
        
        # Should still produce features using defaults
        assert features.shape[0] == 1
        assert not np.any(np.isnan(features))


class TestPhysicsIntegration:
    """Test integration with physics models"""
    
    @pytest.fixture
    def learner_with_physics(self):
        """Create learner with integrated physics models"""
        learner = ResidualLearner()
        kuz_ram = KuzRamModel(rock_factor_a=7.0)
        ppv_model = PPVModel(k=1.4, a=1/3, b=1.6)
        
        learner.integrate_physics_models(kuz_ram, ppv_model)
        return learner
    
    @pytest.fixture
    def sample_blast_params(self):
        """Sample blast parameters"""
        return BlastParameters(
            powder_factor_kg_per_t=0.5,
            powder_factor_kg_per_m3=0.3,
            burden=3.0,
            spacing=3.5,
            bench_height=12.0,
            hole_diameter=165.0,
            stemming_length=3.0,
            rock_density=2700.0,
            explosive_rws=100.0,
            explosive_density=1200.0
        )
    
    def test_physics_model_integration(self, learner_with_physics):
        """Test physics model integration"""
        assert learner_with_physics.kuz_ram_model is not None
        assert learner_with_physics.ppv_model is not None
    
    def test_prediction_with_physics_correction(self, learner_with_physics, sample_blast_params):
        """Test prediction with physics model correction"""
        # Mock trained model
        learner_with_physics.is_trained = True
        learner_with_physics.model = Mock()
        learner_with_physics.model.predict.return_value = np.array([5.0])  # ML correction
        learner_with_physics.feature_scaler = Mock()
        learner_with_physics.feature_scaler.transform.return_value = np.random.rand(1, 10)
        
        result = learner_with_physics.predict_with_physics_correction(
            sample_blast_params, 
            prediction_type="fragmentation"
        )
        
        assert "physics_prediction" in result
        assert "ml_correction" in result
        assert "corrected_prediction" in result
        assert "confidence" in result
        assert result["prediction_type"] == "fragmentation"
    
    def test_prediction_without_trained_model(self, learner_with_physics, sample_blast_params):
        """Test prediction when ML model is not trained"""
        result = learner_with_physics.predict_with_physics_correction(
            sample_blast_params,
            prediction_type="fragmentation"
        )
        
        # Should still work with physics model only
        assert result["ml_correction"] == 0.0
        assert result["corrected_prediction"] == result["physics_prediction"]
    
    def test_blast_params_conversion(self, learner_with_physics, sample_blast_params):
        """Test conversion of BlastParameters to dictionary"""
        blast_dict = learner_with_physics._blast_params_to_dict(sample_blast_params)
        
        assert "burden_m" in blast_dict
        assert "spacing_m" in blast_dict
        assert "powder_factor_kg_m3" in blast_dict
        assert blast_dict["burden_m"] == sample_blast_params.burden


class TestPerformanceMonitoring:
    """Test performance monitoring and drift detection"""
    
    @pytest.fixture
    def learner_with_history(self):
        """Create learner with performance history"""
        learner = ResidualLearner()
        
        # Add some performance history
        for i in range(5):
            metrics = ModelPerformanceMetrics(
                timestamp=datetime.now() - timedelta(days=i*30),
                model_version=f"1.{i}",
                training_samples=100 + i*20,
                validation_r2=0.8 - i*0.05,  # Gradually decreasing performance
                validation_rmse=10.0 + i*2,
                validation_mae=8.0 + i*1.5,
                feature_importance={"feature_1": 0.3, "feature_2": 0.2},
                prediction_bias=0.1,
                prediction_variance=100.0,
                confidence_interval_coverage=0.95,
                is_reliable=True,
                reliability_score=0.8 - i*0.05
            )
            learner.performance_history.append(metrics)
        
        learner.is_trained = True
        return learner
    
    def test_performance_monitoring(self, learner_with_history):
        """Test prediction performance monitoring"""
        # Add some predictions
        for i in range(25):
            predicted = 50.0 + np.random.normal(0, 5)
            actual = 50.0 + np.random.normal(0, 3)  # Better than predictions
            learner_with_history.monitor_prediction_performance(predicted, actual)
        
        assert len(learner_with_history.recent_predictions) == 25
        assert len(learner_with_history.recent_actuals) == 25
        assert len(learner_with_history.prediction_timestamps) == 25
    
    def test_drift_detection(self, learner_with_history):
        """Test performance drift detection"""
        # Add predictions that show clear drift (predictions getting worse)
        for i in range(30):
            predicted = 50.0 + i * 2  # Predictions getting more biased
            actual = 50.0 + np.random.normal(0, 2)
            learner_with_history.monitor_prediction_performance(predicted, actual)
        
        # Should detect drift
        with patch('sklearn.metrics.r2_score', return_value=0.3):  # Poor recent performance
            with patch('sklearn.metrics.mean_squared_error', return_value=400):  # High error
                drift_detected = learner_with_history._check_performance_drift()
                assert drift_detected
    
    def test_retraining_recommendation_no_model(self):
        """Test retraining recommendation when no model exists"""
        learner = ResidualLearner()
        
        recommendation = learner.get_retraining_recommendation(new_data_count=100)
        
        assert recommendation.should_retrain is True
        assert recommendation.urgency == "high"
        assert "No trained model exists" in recommendation.reasons
    
    def test_retraining_recommendation_sufficient_data(self, learner_with_history):
        """Test retraining recommendation with sufficient new data"""
        recommendation = learner_with_history.get_retraining_recommendation(new_data_count=75)
        
        assert recommendation.should_retrain is True
        assert recommendation.new_data_count == 75
        assert any("new data available" in reason for reason in recommendation.reasons)
    
    def test_retraining_recommendation_old_model(self, learner_with_history):
        """Test retraining recommendation for old model"""
        # Set last training date to 6 months ago
        learner_with_history.last_training_date = datetime.now() - timedelta(days=180)
        
        recommendation = learner_with_history.get_retraining_recommendation()
        
        assert recommendation.should_retrain is True
        assert any("days old" in reason for reason in recommendation.reasons)
    
    def test_performance_metrics_update(self, learner_with_history):
        """Test updating performance metrics"""
        initial_count = len(learner_with_history.performance_history)
        
        new_metrics = ModelMetrics(
            train_r2=0.85,
            train_rmse=8.0,
            train_mae=6.0,
            val_r2=0.82,
            val_rmse=9.0,
            val_mae=7.0,
            cv_r2_mean=0.80,
            cv_r2_std=0.05,
            cv_rmse_mean=9.5,
            cv_rmse_std=1.0,
            feature_importance={"feature_1": 0.4, "feature_2": 0.3},
            model_version="2.0",
            training_samples=150,
            training_timestamp=datetime.now(),
            is_reliable=True,
            reliability_flags=[]
        )
        
        learner_with_history.update_performance_metrics(new_metrics)
        
        assert len(learner_with_history.performance_history) == initial_count + 1
        latest_metrics = learner_with_history.performance_history[-1]
        assert latest_metrics.validation_r2 == 0.82
        assert latest_metrics.model_version == "2.0"


class TestModelDiagnostics:
    """Test model diagnostics and export functionality"""
    
    @pytest.fixture
    def comprehensive_learner(self):
        """Create learner with comprehensive data for diagnostics"""
        learner = ResidualLearner()
        learner.is_trained = True
        learner.last_training_date = datetime.now() - timedelta(days=30)
        
        # Add training history
        metrics = ModelMetrics(
            train_r2=0.85, train_rmse=8.0, train_mae=6.0,
            val_r2=0.82, val_rmse=9.0, val_mae=7.0,
            cv_r2_mean=0.80, cv_r2_std=0.05,
            cv_rmse_mean=9.5, cv_rmse_std=1.0,
            feature_importance={"burden_m": 0.3, "spacing_m": 0.2},
            model_version="1.0", training_samples=100,
            training_timestamp=datetime.now() - timedelta(days=30),
            is_reliable=True, reliability_flags=[]
        )
        learner.training_history.append(metrics)
        learner.update_performance_metrics(metrics)
        
        # Add recent predictions
        for i in range(20):
            learner.recent_predictions.append(50.0 + np.random.normal(0, 5))
            learner.recent_actuals.append(50.0 + np.random.normal(0, 3))
            learner.prediction_timestamps.append(datetime.now() - timedelta(hours=i))
        
        return learner
    
    def test_model_diagnostics_export(self, comprehensive_learner):
        """Test comprehensive model diagnostics export"""
        with patch('sklearn.metrics.r2_score', return_value=0.78):
            with patch('sklearn.metrics.mean_squared_error', return_value=64):
                with patch('sklearn.metrics.mean_absolute_error', return_value=6.5):
                    diagnostics = comprehensive_learner.export_model_diagnostics()
        
        assert "model_info" in diagnostics
        assert "feature_config" in diagnostics
        assert "performance_history" in diagnostics
        assert "training_history" in diagnostics
        assert "retraining_recommendation" in diagnostics
        assert "recent_performance" in diagnostics
        
        # Check recent performance
        recent_perf = diagnostics["recent_performance"]
        assert "sample_count" in recent_perf
        assert "r2_score" in recent_perf
        assert "rmse" in recent_perf
        assert "prediction_bias" in recent_perf
    
    def test_model_info_retrieval(self, comprehensive_learner):
        """Test model information retrieval"""
        info = comprehensive_learner.get_model_info()
        
        assert info["is_trained"] is True
        assert "last_training_date" in info
        assert "training_samples" in info
        assert "validation_r2" in info
        assert "is_reliable" in info


class TestEnhancedTraining:
    """Test enhanced training with feature engineering"""
    
    @pytest.fixture
    def training_data(self):
        """Generate synthetic training data"""
        np.random.seed(42)
        n_samples = 100
        
        # Generate blast features
        features = np.random.rand(n_samples, 18)  # 18 base features
        
        # Generate physics predictions (simplified)
        physics_pred = 50 + features[:, 0] * 20 + features[:, 1] * 15
        
        # Generate measured values with some noise and bias
        measured = physics_pred + np.random.normal(0, 5, n_samples) + features[:, 2] * 10
        
        return features, physics_pred, measured
    
    def test_enhanced_training_with_feature_engineering(self, training_data):
        """Test training with feature engineering enabled"""
        features, physics_pred, measured = training_data
        
        config = FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=False,  # Disable to avoid sklearn dependency in test
            normalize_features=True
        )
        
        learner = ResidualLearner(feature_config=config)
        
        with patch('xgboost.XGBRegressor') as mock_xgb:
            with patch('sklearn.model_selection.train_test_split') as mock_split:
                with patch('sklearn.preprocessing.StandardScaler') as mock_scaler:
                    with patch('sklearn.model_selection.cross_val_score', return_value=np.array([0.8, 0.75, 0.82, 0.78, 0.80])):
                        with patch('sklearn.metrics.r2_score', return_value=0.80):
                            with patch('sklearn.metrics.mean_squared_error', return_value=25):
                                with patch('sklearn.metrics.mean_absolute_error', return_value=4.0):
                                    
                                    # Setup mocks
                                    mock_split.return_value = (features[:80], features[80:], 
                                                             measured[:80] - physics_pred[:80], 
                                                             measured[80:] - physics_pred[80:])
                                    
                                    mock_scaler_instance = Mock()
                                    mock_scaler_instance.fit_transform.return_value = features[:80]
                                    mock_scaler_instance.transform.return_value = features[80:]
                                    mock_scaler.return_value = mock_scaler_instance
                                    
                                    mock_model = Mock()
                                    mock_model.predict.return_value = np.zeros(20)
                                    mock_model.feature_importances_ = np.random.rand(features.shape[1])
                                    mock_xgb.return_value = mock_model
                                    
                                    # Train model
                                    metrics = learner.train_residual_model(features, physics_pred, measured)
                                    
                                    assert learner.is_trained
                                    assert metrics.val_r2 == 0.80
                                    assert metrics.is_reliable
    
    def test_model_save_and_load_with_enhancements(self):
        """Test saving and loading enhanced model"""
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, "enhanced_model.pkl")
            
            # Create and configure learner
            config = FeatureEngineeringConfig(include_interaction_terms=True)
            learner1 = ResidualLearner(model_save_path=model_path, feature_config=config)
            
            # Mock training
            learner1.is_trained = True
            learner1.model = Mock()
            learner1.feature_scaler = Mock()
            learner1.model_version = "2.0"
            
            # Save model
            learner1.save_model()
            
            # Load in new learner
            learner2 = ResidualLearner(model_save_path=model_path)
            success = learner2.load_model()
            
            assert success
            assert learner2.is_trained
            assert learner2.model_version == "2.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])