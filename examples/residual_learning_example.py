"""
Example demonstrating the residual learning pipeline for physics model corrections.

This example shows how to:
1. Set up the residual learning system
2. Generate synthetic training data
3. Train the residual model
4. Make predictions with physics corrections
5. Monitor model performance
"""

import numpy as np
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drill_blast_system.ml_pipeline.residual_learner import (
    ResidualLearner, 
    FeatureEngineeringConfig,
    ModelPerformanceMetrics
)
from drill_blast_system.physics_models import KuzRamModel, PPVModel, BlastParameters


def generate_synthetic_blast_data(n_samples: int = 100):
    """Generate synthetic blast data for training"""
    
    np.random.seed(42)
    
    blast_data = []
    physics_predictions = []
    measured_values = []
    
    # Initialize physics model
    kuz_ram = KuzRamModel(rock_factor_a=7.0)
    
    for i in range(n_samples):
        # Generate realistic blast parameters with some variation
        burden = np.random.uniform(2.5, 4.0)
        spacing = np.random.uniform(3.0, 4.5)
        bench_height = np.random.uniform(10.0, 15.0)
        hole_diameter = np.random.uniform(150.0, 200.0)
        stemming_length = np.random.uniform(2.0, 4.0)
        powder_factor_kg_per_t = np.random.uniform(0.3, 0.8)
        rock_density = np.random.uniform(2500.0, 2900.0)
        explosive_rws = np.random.uniform(90.0, 110.0)
        explosive_density = np.random.uniform(1100.0, 1300.0)
        
        # Calculate powder factor in kg/m³
        powder_factor_kg_per_m3 = powder_factor_kg_per_t * rock_density / 1000.0
        
        # Create blast parameters
        blast_params = BlastParameters(
            powder_factor_kg_per_t=powder_factor_kg_per_t,
            powder_factor_kg_per_m3=powder_factor_kg_per_m3,
            burden=burden,
            spacing=spacing,
            bench_height=bench_height,
            hole_diameter=hole_diameter,
            stemming_length=stemming_length,
            rock_density=rock_density,
            explosive_rws=explosive_rws,
            explosive_density=explosive_density
        )
        
        # Get physics prediction
        physics_pred = kuz_ram.predict_mean_fragment_size(blast_params)
        
        # Generate "measured" value with some systematic bias and noise
        # Simulate that physics model tends to underpredict for high powder factors
        bias_factor = 1.0 + 0.2 * (powder_factor_kg_per_t - 0.5)  # Systematic bias
        noise = np.random.normal(0, physics_pred * 0.15)  # 15% noise
        measured = physics_pred * bias_factor + noise
        
        # Store data
        blast_data.append({
            "burden_m": burden,
            "spacing_m": spacing,
            "bench_height_m": bench_height,
            "hole_diameter_mm": hole_diameter,
            "stemming_length_m": stemming_length,
            "powder_factor_kg_per_t": powder_factor_kg_per_t,
            "powder_factor_kg_m3": powder_factor_kg_per_m3,
            "rock_density_kg_m3": rock_density,
            "explosive_rws": explosive_rws,
            "explosive_density_kg_m3": explosive_density,
            "charge_per_hole_kg": burden * spacing * bench_height * rock_density * powder_factor_kg_per_m3 / 1000.0,
            "hole_depth_m": bench_height + stemming_length,
            "ucs_mpa": np.random.uniform(80.0, 120.0),
            "rock_factor_a": 7.0,
            "explosive_vod_m_s": 5000.0,
            "number_of_holes": 1.0,
            "delay_timing_ms": 25.0,
            "bench_face_angle_deg": 70.0,
            "free_face_distance_m": burden
        })
        
        physics_predictions.append(physics_pred)
        measured_values.append(measured)
    
    return blast_data, np.array(physics_predictions), np.array(measured_values)


def demonstrate_residual_learning():
    """Demonstrate the complete residual learning pipeline"""
    
    print("=== Residual Learning Pipeline Demonstration ===\n")
    
    # 1. Set up residual learner with feature engineering
    print("1. Setting up residual learner...")
    
    feature_config = FeatureEngineeringConfig(
        include_interaction_terms=True,
        include_polynomial_features=False,  # Disable to avoid sklearn dependency
        normalize_features=True,
        feature_selection_threshold=0.01
    )
    
    learner = ResidualLearner(
        model_save_path="models/demo_residual_model.pkl",
        feature_config=feature_config
    )
    
    # Integrate physics models
    kuz_ram_model = KuzRamModel(rock_factor_a=7.0)
    ppv_model = PPVModel(k=1.4, a=1/3, b=1.6)
    learner.integrate_physics_models(kuz_ram_model, ppv_model)
    
    print(f"✓ Residual learner initialized")
    print(f"✓ Feature engineering: interactions={feature_config.include_interaction_terms}")
    print(f"✓ Physics models integrated")
    
    # 2. Generate synthetic training data
    print("\n2. Generating synthetic training data...")
    
    blast_data, physics_predictions, measured_values = generate_synthetic_blast_data(n_samples=75)
    
    print(f"✓ Generated {len(blast_data)} synthetic blast scenarios")
    print(f"✓ Physics predictions range: {physics_predictions.min():.1f} - {physics_predictions.max():.1f} mm")
    print(f"✓ Measured values range: {measured_values.min():.1f} - {measured_values.max():.1f} mm")
    
    # Extract features for training
    print("\n3. Feature engineering...")
    
    feature_matrix = []
    for data in blast_data:
        features = learner.extract_blast_features(data)
        feature_matrix.append(features[0])  # Extract single row
    
    feature_matrix = np.array(feature_matrix)
    
    print(f"✓ Extracted {feature_matrix.shape[1]} engineered features per sample")
    print(f"✓ Feature matrix shape: {feature_matrix.shape}")
    
    # 4. Train residual model (mock training since XGBoost might not be available)
    print("\n4. Training residual model...")
    
    try:
        # Try actual training if XGBoost is available
        metrics = learner.train_residual_model(
            blast_features=feature_matrix,
            physics_predictions=physics_predictions,
            measured_values=measured_values,
            validation_split=0.2,
            cross_validation_folds=3
        )
        
        print(f"✓ Model training completed successfully")
        print(f"✓ Validation R²: {metrics.val_r2:.3f}")
        print(f"✓ Validation RMSE: {metrics.val_rmse:.2f} mm")
        print(f"✓ Model is reliable: {metrics.is_reliable}")
        
        # Show feature importance
        print(f"\n   Top 5 most important features:")
        sorted_features = sorted(metrics.feature_importance.items(), 
                               key=lambda x: x[1], reverse=True)
        for feature, importance in sorted_features[:5]:
            print(f"   - {feature}: {importance:.3f}")
        
    except ImportError:
        print("⚠ XGBoost not available - simulating training results")
        
        # Create mock metrics
        from drill_blast_system.ml_pipeline.data_structures import ModelMetrics
        
        metrics = ModelMetrics(
            train_r2=0.85, train_rmse=8.5, train_mae=6.2,
            val_r2=0.78, val_rmse=10.2, val_mae=7.8,
            cv_r2_mean=0.76, cv_r2_std=0.04,
            cv_rmse_mean=10.8, cv_rmse_std=1.2,
            feature_importance={
                "powder_factor_kg_m3": 0.25,
                "burden_m": 0.20,
                "spacing_m": 0.18,
                "rock_density_kg_m3": 0.15,
                "explosive_rws": 0.12
            },
            model_version="1.0",
            training_samples=len(blast_data),
            training_timestamp=datetime.now(),
            is_reliable=True,
            reliability_flags=[]
        )
        
        learner.is_trained = True
        learner.training_history.append(metrics)
        learner.update_performance_metrics(metrics)
        
        print(f"✓ Mock training completed")
        print(f"✓ Simulated Validation R²: {metrics.val_r2:.3f}")
        print(f"✓ Simulated Validation RMSE: {metrics.val_rmse:.2f} mm")
    
    # 5. Make predictions with physics corrections
    print("\n5. Making predictions with physics corrections...")
    
    # Test with a new blast scenario
    test_blast_params = BlastParameters(
        powder_factor_kg_per_t=0.6,
        powder_factor_kg_per_m3=0.6 * 2700 / 1000,
        burden=3.2,
        spacing=3.8,
        bench_height=12.5,
        hole_diameter=165.0,
        stemming_length=3.2,
        rock_density=2700.0,
        explosive_rws=105.0,
        explosive_density=1200.0
    )
    
    # Get prediction with correction
    result = learner.predict_with_physics_correction(
        blast_params=test_blast_params,
        prediction_type="fragmentation"
    )
    
    print(f"✓ Physics prediction: {result['physics_prediction']:.2f} mm")
    print(f"✓ ML correction: {result['ml_correction']:.2f} mm")
    print(f"✓ Corrected prediction: {result['corrected_prediction']:.2f} mm")
    print(f"✓ Confidence: {result['confidence']:.3f}")
    
    # 6. Demonstrate performance monitoring
    print("\n6. Performance monitoring...")
    
    # Simulate some predictions and actual measurements
    for i in range(10):
        # Generate test prediction
        test_params = BlastParameters(
            powder_factor_kg_per_t=np.random.uniform(0.4, 0.7),
            powder_factor_kg_per_m3=np.random.uniform(0.4, 0.7) * 2700 / 1000,
            burden=np.random.uniform(2.8, 3.5),
            spacing=np.random.uniform(3.2, 4.0),
            bench_height=12.0,
            hole_diameter=165.0,
            stemming_length=3.0,
            rock_density=2700.0,
            explosive_rws=100.0,
            explosive_density=1200.0
        )
        
        pred_result = learner.predict_with_physics_correction(test_params, "fragmentation")
        predicted = pred_result['corrected_prediction']
        
        # Simulate actual measurement (with some error)
        actual = predicted + np.random.normal(0, 5)
        
        # Monitor performance
        learner.monitor_prediction_performance(predicted, actual)
    
    print(f"✓ Monitored {len(learner.recent_predictions)} recent predictions")
    
    # 7. Get retraining recommendation
    print("\n7. Retraining recommendation...")
    
    recommendation = learner.get_retraining_recommendation(new_data_count=25)
    
    print(f"✓ Should retrain: {recommendation.should_retrain}")
    print(f"✓ Urgency: {recommendation.urgency}")
    print(f"✓ Reasons: {', '.join(recommendation.reasons)}")
    print(f"✓ Recommended action: {recommendation.recommended_action}")
    
    # 8. Export diagnostics
    print("\n8. Model diagnostics...")
    
    try:
        diagnostics = learner.export_model_diagnostics()
        
        print(f"✓ Model info exported")
        print(f"✓ Performance history: {len(diagnostics['performance_history'])} entries")
        print(f"✓ Training history: {len(diagnostics['training_history'])} entries")
        
        if 'recent_performance' in diagnostics and 'r2_score' in diagnostics['recent_performance']:
            recent_r2 = diagnostics['recent_performance']['r2_score']
            print(f"✓ Recent performance R²: {recent_r2:.3f}")
        
    except Exception as e:
        print(f"⚠ Diagnostics export failed (expected without sklearn): {e}")
    
    print("\n=== Residual Learning Pipeline Demo Complete ===")
    
    return learner


def demonstrate_feature_engineering():
    """Demonstrate feature engineering capabilities"""
    
    print("\n=== Feature Engineering Demonstration ===\n")
    
    # Create learner with different feature engineering settings
    configs = [
        ("Basic features only", FeatureEngineeringConfig(
            include_interaction_terms=False,
            include_polynomial_features=False
        )),
        ("With interaction terms", FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=False
        )),
        ("With polynomial features", FeatureEngineeringConfig(
            include_interaction_terms=False,
            include_polynomial_features=True,
            polynomial_degree=2
        )),
        ("Full feature engineering", FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=True,
            polynomial_degree=2
        ))
    ]
    
    # Sample blast data
    sample_data = {
        "burden_m": 3.0,
        "spacing_m": 3.5,
        "bench_height_m": 12.0,
        "hole_diameter_mm": 165.0,
        "stemming_length_m": 3.0,
        "powder_factor_kg_per_t": 0.5,
        "powder_factor_kg_m3": 1.35,
        "rock_density_kg_m3": 2700.0,
        "explosive_rws": 100.0,
        "explosive_density_kg_m3": 1200.0,
        "ucs_mpa": 100.0
    }
    
    for config_name, config in configs:
        learner = ResidualLearner(feature_config=config)
        
        try:
            features = learner.extract_blast_features(sample_data)
            print(f"{config_name:25}: {features.shape[1]:3d} features")
        except Exception as e:
            print(f"{config_name:25}: Error - {e}")
    
    print("\n✓ Feature engineering comparison complete")


if __name__ == "__main__":
    print("Starting Residual Learning Pipeline Example...\n")
    
    # Demonstrate feature engineering
    demonstrate_feature_engineering()
    
    # Demonstrate full pipeline
    learner = demonstrate_residual_learning()
    
    print(f"\nExample completed successfully!")
    print(f"Model trained: {learner.is_trained}")
    print(f"Feature count: {len(learner.feature_columns)}")
    print(f"Performance history: {len(learner.performance_history)} entries")