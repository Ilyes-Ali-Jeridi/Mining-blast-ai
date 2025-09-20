# Synthetic Data Generator

The synthetic data generator creates realistic blast scenarios for testing, validation, and model training. It provides comprehensive tools for generating controlled datasets with known ground truth.

## Features

### 1. Scenario Generation
- **Realistic blast scenarios** with randomized but realistic parameters
- **Multiple rock types** (soft sedimentary, hard igneous, metamorphic, etc.)
- **Various explosive types** (ANFO, emulsion, slurry, bulk emulsion)
- **Configurable site geometry** and operational constraints
- **Physics-based predictions** using Kuz-Ram and PPV models

### 2. Measurement Noise Simulation
- **Controlled noise addition** to simulate real measurement uncertainty
- **Configurable noise levels** for fragmentation and PPV measurements
- **Outlier simulation** with adjustable probability
- **Missing data simulation** to reflect real-world conditions
- **Quality assessment** metrics for synthetic measurements

### 3. Parameter Space Exploration
- **Latin Hypercube Sampling** for efficient parameter space coverage
- **Customizable parameter ranges** for systematic exploration
- **Multi-dimensional parameter analysis**
- **Statistical coverage validation**

### 4. Benchmark Dataset Generation
- **Comprehensive datasets** with proper train/validation/test splits
- **Quality assessment** and validation reporting
- **Multiple export formats** (JSON, CSV, pickle)
- **Dataset statistics** and completeness metrics

### 5. Model Benchmarking
- **Physics model validation** against synthetic ground truth
- **Performance metrics** (MAE, RMSE, MAPE, R²)
- **Cross-rock-type evaluation**
- **Comparative analysis** between different models

## API Endpoints

### Core Generation
- `POST /api/v1/synthetic/scenarios/generate` - Generate single scenario
- `POST /api/v1/synthetic/parameter-exploration` - Parameter space exploration
- `POST /api/v1/synthetic/benchmark-dataset` - Generate benchmark dataset

### Analysis Tools
- `POST /api/v1/synthetic/benchmark-models` - Benchmark physics models
- `POST /api/v1/synthetic/noise-analysis` - Analyze noise effects

### Configuration
- `GET /api/v1/synthetic/rock-types` - Available rock types
- `GET /api/v1/synthetic/explosive-types` - Available explosive types

## Frontend Interface

The React-based frontend provides:

### 1. Scenario Generator Tab
- Interactive parameter configuration
- Real-time scenario generation
- Detailed results display with predictions vs measurements
- Rock type and noise level controls

### 2. Parameter Exploration Tab
- Custom parameter range definition
- Batch scenario generation
- Interactive scatter plots
- CSV export functionality

### 3. Benchmark Dataset Tab
- Dataset size and split configuration
- Quality assessment dashboard
- Export progress tracking
- Statistical summaries

### 4. Model Benchmarking Tab
- Model selection interface
- Performance comparison charts
- Detailed metrics tables
- Color-coded performance indicators

### 5. Noise Analysis Tab
- Noise level configuration
- Measurement precision analysis
- Bias detection and quantification
- Recommendations for quality control

## Usage Examples

### Python API
```python
from drill_blast_system.ml_pipeline.synthetic_generator import SyntheticDataGenerator

# Initialize generator
generator = SyntheticDataGenerator(random_seed=42)

# Generate single scenario
scenario = generator.generate_scenario()
print(f"P80: {scenario.true_fragmentation.p80:.1f} mm")

# Parameter exploration
scenarios = generator.generate_parameter_space_exploration(num_scenarios=100)

# Benchmark dataset
dataset = generator.generate_benchmark_dataset(num_scenarios=500)

# Model benchmarking
results = generator.benchmark_physics_models(scenarios)
```

### REST API
```bash
# Generate scenario
curl -X POST "http://localhost:8000/api/v1/synthetic/scenarios/generate?noise_level=0.15"

# Parameter exploration
curl -X POST "http://localhost:8000/api/v1/synthetic/parameter-exploration?num_scenarios=50"

# Get rock types
curl "http://localhost:8000/api/v1/synthetic/rock-types"
```

## Data Quality

### Validation Metrics
- **Completeness**: Fraction of valid measurements
- **Missing Rate**: Percentage of missing data
- **Quality Issues**: Count of low-quality measurements
- **Statistical Coverage**: Parameter space coverage assessment

### Noise Characteristics
- **Fragmentation Noise**: 5-50% standard deviation
- **PPV Noise**: 5-50% standard deviation
- **Outlier Rate**: 0-20% probability
- **Missing Data**: 0-10% probability

## Rock Type Database

| Rock Type | UCS (MPa) | Density (kg/m³) | Rock Factor A | Description |
|-----------|-----------|-----------------|---------------|-------------|
| Soft Sedimentary | 25 | 2200 | 12.0 | Soft sandstone, limestone |
| Hard Sedimentary | 80 | 2500 | 8.0 | Hard sandstone, quartzite |
| Soft Igneous | 60 | 2400 | 9.0 | Weathered granite, soft basalt |
| Hard Igneous | 150 | 2700 | 6.0 | Fresh granite, hard basalt |
| Metamorphic | 120 | 2650 | 7.0 | Gneiss, schist, slate |
| Weathered | 15 | 1900 | 15.0 | Highly weathered rock |

## Explosive Type Database

| Explosive | Density (kg/m³) | RWS (%) | VOD (m/s) | Cost ($/kg) |
|-----------|-----------------|---------|-----------|-------------|
| ANFO | 850 | 100 | 4500 | 1.20 |
| Emulsion | 1200 | 115 | 5500 | 2.50 |
| Slurry | 1300 | 110 | 5200 | 2.20 |
| Bulk Emulsion | 1150 | 120 | 5800 | 1.80 |

## Best Practices

### For Testing
- Use fixed random seeds for reproducible results
- Start with low noise levels (5-15%) for initial validation
- Generate diverse rock type coverage
- Validate against known physics relationships

### For Training
- Use large datasets (500+ scenarios) for robust training
- Include edge cases and challenging conditions
- Maintain proper train/validation/test splits
- Monitor data quality metrics

### For Benchmarking
- Test across multiple rock types and conditions
- Use consistent evaluation metrics
- Include confidence intervals
- Document model assumptions and limitations

## Integration

The synthetic data generator integrates with:
- **Physics Models**: Kuz-Ram fragmentation, PPV prediction
- **ML Pipeline**: Residual learning, quality assessment
- **Optimization**: Algorithm validation and testing
- **Reporting**: Export and visualization tools
- **Authentication**: Role-based access control

## Performance

- **Single Scenario**: ~100ms generation time
- **Parameter Exploration**: ~5-10 seconds for 100 scenarios
- **Benchmark Dataset**: ~30-60 seconds for 500 scenarios
- **Model Benchmarking**: ~10-30 seconds for 100 test scenarios

## Future Enhancements

- **Advanced Noise Models**: Correlated noise, systematic biases
- **Temporal Variations**: Time-dependent parameter changes
- **Spatial Correlations**: Spatially correlated rock properties
- **Multi-Bench Scenarios**: Complex mine geometries
- **Real Data Calibration**: Calibration against actual measurements