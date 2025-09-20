# Residual Learning Pipeline

## Overview

The residual learning pipeline implements XGBoost-based machine learning to improve physics model predictions using post-blast measurement data. This system learns corrections to physics-based predictions while keeping the physics models as the primary prediction source.

## Key Features

### 1. Feature Engineering
- **Interaction Terms**: Automatically generates meaningful interactions between blast parameters
- **Polynomial Features**: Creates polynomial combinations for non-linear relationships
- **Domain-Specific Features**: Engineering features specific to blast analysis (burden-diameter ratio, stemming ratio, etc.)
- **Configurable**: Feature engineering can be customized via `FeatureEngineeringConfig`

### 2. Physics Model Integration
- **Seamless Integration**: Works with existing Kuz-Ram and PPV physics models
- **Correction Layer**: ML model provides corrections to physics predictions rather than replacing them
- **Confidence Weighting**: Corrections are applied based on model confidence

### 3. Performance Monitoring
- **Drift Detection**: Monitors prediction performance to detect when retraining is needed
- **Performance History**: Tracks model performance over time
- **Retraining Recommendations**: Provides intelligent recommendations for when to retrain

### 4. Model Management
- **Versioning**: Tracks model versions and training history
- **Persistence**: Save and load trained models
- **Diagnostics**: Comprehensive model diagnostics and performance analysis

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Blast Data    │───▶│ Feature Engineer │───▶│  XGBoost Model  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│ Physics Models  │───▶│ Physics Predict  │◀────────────┘
└─────────────────┘    └──────────────────┘             │
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Final Prediction │◀───│  ML Correction  │
                       └──────────────────┘    └─────────────────┘
```

## Usage

### Basic Setup

```python
from drill_blast_system.ml_pipeline.residual_learner import (
    ResidualLearner, 
    FeatureEngineeringConfig
)
from drill_blast_system.physics_models import KuzRamModel, PPVModel

# Configure feature engineering
feature_config = FeatureEngineeringConfig(
    include_interaction_terms=True,
    include_polynomial_features=True,
    polynomial_degree=2,
    normalize_features=True
)

# Initialize residual learner
learner = ResidualLearner(
    model_save_path="models/residual_model.pkl",
    feature_config=feature_config
)

# Integrate physics models
kuz_ram_model = KuzRamModel(rock_factor_a=7.0)
ppv_model = PPVModel(k=1.4, a=1/3, b=1.6)
learner.integrate_physics_models(kuz_ram_model, ppv_model)
```

### Training the Model

```python
# Prepare training data
blast_features = extract_features_from_blast_records(blast_record_ids)
physics_predictions = compute_physics_predictions(blast_records)
measured_values = get_measurement_data(blast_records)

# Train residual model
metrics = learner.train_residual_model(
    blast_features=blast_features,
    physics_predictions=physics_predictions,
    measured_values=measured_values,
    validation_split=0.2,
    cross_validation_folds=5
)

print(f"Model R²: {metrics.val_r2:.3f}")
print(f"Model RMSE: {metrics.val_rmse:.2f}")
print(f"Is reliable: {metrics.is_reliable}")
```

### Making Predictions

```python
from drill_blast_system.physics_models import BlastParameters

# Define blast parameters
blast_params = BlastParameters(
    powder_factor_kg_per_t=0.5,
    powder_factor_kg_per_m3=1.35,
    burden=3.0,
    spacing=3.5,
    bench_height=12.0,
    hole_diameter=165.0,
    stemming_length=3.0,
    rock_density=2700.0,
    explosive_rws=100.0,
    explosive_density=1200.0
)

# Get prediction with ML correction
result = learner.predict_with_physics_correction(
    blast_params=blast_params,
    prediction_type="fragmentation"
)

print(f"Physics prediction: {result['physics_prediction']:.2f} mm")
print(f"ML correction: {result['ml_correction']:.2f} mm")
print(f"Final prediction: {result['corrected_prediction']:.2f} mm")
print(f"Confidence: {result['confidence']:.3f}")
```

### Performance Monitoring

```python
# Monitor prediction performance
learner.monitor_prediction_performance(
    predicted_value=predicted_p80,
    actual_value=measured_p80,
    prediction_timestamp=datetime.now()
)

# Get retraining recommendation
recommendation = learner.get_retraining_recommendation(new_data_count=50)

if recommendation.should_retrain:
    print(f"Retraining recommended: {recommendation.urgency}")
    print(f"Reasons: {', '.join(recommendation.reasons)}")
    print(f"Action: {recommendation.recommended_action}")
```

## Feature Engineering

### Base Features
The system extracts 18 base features from blast data:

**Blast Geometry:**
- `burden_m`: Burden distance
- `spacing_m`: Hole spacing
- `bench_height_m`: Bench height
- `hole_diameter_mm`: Hole diameter
- `hole_depth_m`: Total hole depth
- `stemming_length_m`: Stemming length

**Explosives:**
- `powder_factor_kg_m3`: Powder factor (kg/m³)
- `charge_per_hole_kg`: Charge per hole
- `explosive_density_kg_m3`: Explosive density
- `explosive_rws`: Relative Weight Strength
- `explosive_vod_m_s`: Velocity of Detonation

**Rock Properties:**
- `rock_density_kg_m3`: Rock density
- `ucs_mpa`: Unconfined Compressive Strength
- `rock_factor_a`: Kuz-Ram rock factor

**Operational:**
- `delay_timing_ms`: Delay timing
- `number_of_holes`: Number of holes
- `bench_face_angle_deg`: Bench face angle
- `free_face_distance_m`: Free face distance

### Engineered Features

**Interaction Terms:**
- `burden_m × spacing_m`: Blast pattern area
- `powder_factor_kg_m3 × rock_density_kg_m3`: Energy per unit rock mass
- `explosive_rws × explosive_vod_m_s`: Explosive energy characteristics
- `hole_diameter_mm × bench_height_m`: Hole volume factor

**Domain-Specific Features:**
- `burden_diameter_ratio`: Burden to hole diameter ratio
- `stemming_ratio`: Stemming length to bench height ratio
- `specific_charge`: Charge per unit rock volume
- `strength_energy_ratio`: Rock strength to explosive energy ratio

**Polynomial Features:**
- Quadratic terms for key variables
- Configurable polynomial degree

## Performance Monitoring

### Drift Detection
The system monitors prediction performance to detect when model retraining is needed:

- **Performance Window**: Tracks recent predictions (default: 100 predictions)
- **Degradation Threshold**: Triggers retraining when performance drops by >10%
- **Statistical Tests**: Uses R² and RMSE to assess performance changes

### Retraining Recommendations
Automatic recommendations based on:

- **Data Availability**: Sufficient new training data (≥50 samples)
- **Performance Drift**: Detected degradation in prediction accuracy
- **Model Age**: Time since last training (>90 days triggers recommendation)
- **Reliability**: Model reliability scores and confidence intervals

### Performance Metrics
Comprehensive tracking includes:

- **Training Metrics**: R², RMSE, MAE on training data
- **Validation Metrics**: Cross-validation performance
- **Feature Importance**: XGBoost feature importance scores
- **Reliability Flags**: Issues affecting model reliability
- **Confidence Intervals**: Prediction uncertainty quantification

## API Endpoints

### Training
- `POST /api/v1/ml/residual-learning/train`: Train residual model
- `GET /api/v1/ml/residual-learning/status`: Get model status and metrics

### Prediction
- `POST /api/v1/ml/residual-learning/predict`: Make corrected predictions
- `POST /api/v1/ml/residual-learning/monitor-prediction`: Monitor performance

### Diagnostics
- `GET /api/v1/ml/residual-learning/diagnostics`: Export model diagnostics

## Requirements Implementation

This implementation satisfies the following requirements:

### Requirement 5.4: XGBoost Residual Model Training
✅ **Implemented**: XGBoost-based residual model with comprehensive training pipeline
- Automatic training when sufficient data exists (N ≥ 50)
- Cross-validation and performance metrics
- Feature importance analysis

### Requirement 5.5: Physics Model Integration
✅ **Implemented**: Residual model as correction layer
- Physics models remain primary prediction source
- ML corrections applied with confidence weighting
- Seamless integration with existing Kuz-Ram and PPV models

### Requirement 5.6: Performance Monitoring and Retraining
✅ **Implemented**: Comprehensive monitoring system
- Real-time performance tracking
- Drift detection algorithms
- Intelligent retraining recommendations
- Performance history and diagnostics

## Dependencies

**Required:**
- `numpy`: Numerical computations
- `pandas`: Data manipulation
- `pickle`: Model serialization

**Optional (for full functionality):**
- `xgboost`: XGBoost machine learning model
- `scikit-learn`: Feature engineering and metrics
- `fastapi`: API endpoints

## Testing

Comprehensive test suite covers:
- Feature engineering functionality
- Physics model integration
- Performance monitoring
- Model diagnostics
- API endpoints

Run tests with:
```bash
python -m pytest tests/test_residual_learning_pipeline.py -v
```

## Example

See `examples/residual_learning_example.py` for a complete demonstration of the residual learning pipeline including:
- Synthetic data generation
- Feature engineering
- Model training (with fallback for missing dependencies)
- Prediction with corrections
- Performance monitoring
- Retraining recommendations

## Future Enhancements

1. **Online Learning**: Implement incremental learning for real-time model updates
2. **Multi-Target Models**: Support for multiple prediction targets (P50, P80, PPV)
3. **Ensemble Methods**: Combine multiple ML models for improved accuracy
4. **Uncertainty Quantification**: Advanced confidence interval estimation
5. **Automated Hyperparameter Tuning**: Optimize XGBoost parameters automatically