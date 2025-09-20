# ML Pipeline - SAM-based Fragmentation Analysis

This module implements SAM (Segment Anything Model) based fragmentation analysis for post-blast measurement and learning, fulfilling requirements 5.1 and 5.7 of the automated drill-and-blast system.

## Overview

The ML pipeline provides comprehensive fragmentation analysis capabilities:

- **SAM-based Segmentation**: Uses Meta's Segment Anything Model for accurate rock fragment segmentation
- **Traditional CV Fallback**: Provides robust fallback using traditional computer vision when SAM is unavailable
- **Scale Detection**: Automatic detection and calibration using scale markers in images
- **Quality Assessment**: Comprehensive quality metrics and validation for measurement reliability
- **Fragmentation Curves**: Generation of size distribution curves compatible with physics models
- **Residual Learning**: XGBoost-based learning for improving physics model predictions

## Key Components

### FragmentationAnalyzer
Main class that orchestrates the complete analysis pipeline:

```python
from drill_blast_system.ml_pipeline import FragmentationAnalyzer

analyzer = FragmentationAnalyzer(
    sam_model_path="path/to/sam_model.pth",  # Optional
    device="cpu",  # or "cuda"
    enable_preprocessing=True
)

result = analyzer.analyze_muckpile_image(
    image_path="muckpile.jpg",
    scale_marker_coords=(x1, y1, x2, y2),  # Optional
    known_scale_mm_per_pixel=0.5  # Optional
)
```

### ImagePreprocessor
Handles image preprocessing and quality enhancement:

```python
from drill_blast_system.ml_pipeline import ImagePreprocessor

preprocessor = ImagePreprocessor(
    target_size=(1024, 768),  # Optional resizing
    enhance_contrast=True,
    reduce_noise=True
)

result = preprocessor.preprocess_image("image.jpg")
```

### ScaleDetector
Detects scale markers for size calibration:

```python
from drill_blast_system.ml_pipeline import ScaleDetector

detector = ScaleDetector(
    known_marker_sizes=[100.0, 200.0, 300.0],  # mm
    detection_method="template_matching"
)

marker = detector.detect_scale_marker(image, marker_coords)
```

### MeasurementQualityAssessor
Assesses measurement quality and reliability:

```python
from drill_blast_system.ml_pipeline import MeasurementQualityAssessor

assessor = MeasurementQualityAssessor(
    min_acceptable_quality=0.6,
    min_reliable_quality=0.8,
    min_fragments_for_training=50
)

assessment = assessor.assess_measurement_quality(...)
```

## Installation and Setup

### Basic Installation
The ML pipeline works out-of-the-box with traditional computer vision methods:

```bash
pip install opencv-python scikit-learn xgboost
```

### SAM Installation (Optional but Recommended)
For best segmentation results, install SAM:

```bash
# Install segment-anything
pip install git+https://github.com/facebookresearch/segment-anything.git

# Install PyTorch (if not already installed)
pip install torch torchvision

# Download SAM model checkpoint
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
```

### Model Checkpoints
Available SAM models (download from [SAM repository](https://github.com/facebookresearch/segment-anything#model-checkpoints)):

- **ViT-B**: `sam_vit_b_01ec64.pth` (358MB) - Recommended for most use cases
- **ViT-L**: `sam_vit_l_0b3195.pth` (1.2GB) - Better accuracy, slower
- **ViT-H**: `sam_vit_h_4b8939.pth` (2.4GB) - Best accuracy, slowest

## Configuration

Configure the ML pipeline through environment variables or settings:

```python
# Environment variables
ML_SAM_MODEL_PATH=/path/to/sam_vit_b_01ec64.pth
ML_SAM_DEVICE=cpu  # or cuda
ML_ENABLE_PREPROCESSING=true
ML_MIN_FRAGMENT_AREA_PIXELS=100
ML_MAX_FRAGMENT_AREA_PIXELS=50000
ML_MIN_ACCEPTABLE_QUALITY=0.6
ML_MIN_RELIABLE_QUALITY=0.8
ML_MIN_FRAGMENTS_FOR_TRAINING=50
```

Or through the settings object:

```python
from drill_blast_system.core.config import get_settings

settings = get_settings()
ml_settings = settings.ml_pipeline

# Configure SAM
ml_settings.sam_model_path = "/path/to/model.pth"
ml_settings.sam_device = "cuda"
ml_settings.enable_preprocessing = True
```

## API Usage

### REST API Endpoints

#### Analyze Fragmentation
```http
POST /api/v1/ml/analyze-fragmentation
Content-Type: multipart/form-data

image: [image file]
scale_x1: 50 (optional)
scale_y1: 50 (optional)
scale_x2: 250 (optional)
scale_y2: 80 (optional)
known_scale_mm_per_pixel: 0.5 (optional)
```

#### Get Analyzer Status
```http
GET /api/v1/ml/analyzer-status
```

#### Test Segmentation Methods
```http
POST /api/v1/ml/test-segmentation
Content-Type: multipart/form-data

image: [image file]
```

### Example Response
```json
{
  "success": true,
  "message": "Fragmentation analysis completed successfully",
  "data": {
    "fragmentation_analysis": {
      "p10_mm": 25.0,
      "p50_mm": 50.0,
      "p80_mm": 100.0,
      "mean_size_mm": 55.0,
      "characteristic_size_mm": 60.0,
      "uniformity_index": 1.5,
      "fragment_count": 25,
      "total_analyzed_area_mm2": 50000.0,
      "measurement_quality": 0.8,
      "scale_detection_quality": 0.9,
      "segmentation_quality": 0.8,
      "is_valid": true,
      "scale_factor_mm_per_pixel": 0.5,
      "processing_timestamp": "2024-01-15T10:30:00",
      "quality_flags": []
    },
    "recommendations": [
      "Analysis quality is good - results are reliable for use"
    ]
  }
}
```

## Quality Assessment

The system provides comprehensive quality assessment with multiple metrics:

### Quality Metrics
- **Image Quality**: Sharpness, brightness, contrast assessment
- **Scale Detection Quality**: Confidence in scale marker detection
- **Segmentation Quality**: Fragment separation and edge quality
- **Fragment Analysis Quality**: Size distribution reasonableness

### Quality Grades
- **A (0.9-1.0)**: Excellent quality, suitable for all uses
- **B (0.8-0.9)**: Good quality, suitable for most uses
- **C (0.7-0.8)**: Acceptable quality with minor issues
- **D (0.6-0.7)**: Poor quality, use with caution
- **F (0.0-0.6)**: Unacceptable quality, do not use

### Quality Flags
The system automatically identifies common issues:
- Poor image quality
- Scale detection issues
- Insufficient fragments
- Unrealistic size distributions
- Segmentation problems

## Fragmentation Curve Integration

Results are automatically converted to FragmentationCurve objects compatible with the physics models:

```python
# Analysis result includes fragmentation curve
result = analyzer.analyze_muckpile_image("image.jpg")

# Access curve parameters
p80 = result.p80
characteristic_size = result.characteristic_size
uniformity_index = result.uniformity_index

# Generate full curve for visualization
from drill_blast_system.physics_models.fragmentation_curve import FragmentationCurve

curve = FragmentationCurve(
    mean_size_mm=result.mean_size,
    uniformity_index=result.uniformity_index
)
curve.fit_from_measurements(result.fragment_sizes)

# Get sieve analysis
sieve_analysis = curve.get_sieve_analysis()
```

## Performance Considerations

### Processing Time
- **Traditional CV**: 1-5 seconds for typical images
- **SAM (CPU)**: 10-30 seconds for typical images
- **SAM (GPU)**: 3-10 seconds for typical images

### Memory Usage
- **Traditional CV**: ~100MB
- **SAM**: 1-4GB depending on model size

### Optimization Tips
1. Use ViT-B model for best speed/accuracy balance
2. Enable GPU acceleration when available
3. Resize large images to max 2048px
4. Use preprocessing to improve segmentation quality
5. Cache analyzer instance to avoid model reloading

## Error Handling

The system provides robust error handling with graceful degradation:

### SAM Unavailable
- Automatically falls back to traditional computer vision
- Logs warning but continues processing
- Quality scores adjusted accordingly

### Scale Detection Failure
- Falls back to estimated scale based on image size
- Reduces scale detection quality score
- Provides recommendations for better scale markers

### Processing Errors
- Detailed error messages with suggestions
- Temporary file cleanup
- Proper HTTP status codes in API responses

## Testing

Run the comprehensive test suite:

```bash
# Run all ML pipeline tests
pytest tests/test_fragmentation_analysis.py -v

# Run API tests
pytest tests/test_ml_pipeline_api.py -v

# Run with coverage
pytest tests/test_fragmentation_analysis.py --cov=src/drill_blast_system/ml_pipeline
```

## Examples

### Basic Usage
```python
from drill_blast_system.ml_pipeline import FragmentationAnalyzer

# Initialize analyzer
analyzer = FragmentationAnalyzer()

# Analyze image
result = analyzer.analyze_muckpile_image(
    "muckpile.jpg",
    known_scale_mm_per_pixel=0.5
)

print(f"P80: {result.p80:.1f} mm")
print(f"Fragment count: {result.fragment_count}")
print(f"Quality: {result.measurement_quality:.2f}")
```

### With Scale Marker Detection
```python
# Analyze with scale marker coordinates
result = analyzer.analyze_muckpile_image(
    "muckpile.jpg",
    scale_marker_coords=(50, 50, 250, 80)
)

print(f"Scale detection quality: {result.scale_detection_quality:.2f}")
```

### Quality Assessment
```python
if result.is_valid and result.measurement_quality > 0.8:
    print("High quality measurement - suitable for training")
    # Use for model training or calibration
else:
    print("Quality issues detected:")
    for flag in result.quality_flags:
        print(f"  - {flag}")
```

### Batch Processing
```python
import os
from pathlib import Path

analyzer = FragmentationAnalyzer()
results = []

for image_file in Path("images").glob("*.jpg"):
    try:
        result = analyzer.analyze_muckpile_image(str(image_file))
        if result.is_valid:
            results.append(result)
            print(f"{image_file.name}: P80={result.p80:.1f}mm")
    except Exception as e:
        print(f"Error processing {image_file.name}: {e}")

print(f"Successfully processed {len(results)} images")
```

## Integration with Physics Models

The fragmentation analysis integrates seamlessly with the physics models:

```python
# Get fragmentation result
result = analyzer.analyze_muckpile_image("image.jpg")

# Use in Kuz-Ram model validation
from drill_blast_system.physics_models.kuz_ram import KuzRamModel

kuz_ram = KuzRamModel()
predicted_p80 = kuz_ram.predict_p80(
    powder_factor=0.8,
    burden=3.0,
    spacing=3.5,
    # ... other parameters
)

# Compare with measured
error = abs(predicted_p80 - result.p80) / result.p80
print(f"Prediction error: {error*100:.1f}%")

# Use for model calibration if sufficient quality
if result.measurement_quality > 0.8:
    # Add to training dataset for residual learning
    pass
```

## Troubleshooting

### Common Issues

#### SAM Model Not Loading
```
Error: SAM model not found at path/to/model.pth
```
**Solution**: Download the SAM model checkpoint and update the path in configuration.

#### CUDA Out of Memory
```
RuntimeError: CUDA out of memory
```
**Solution**: Use CPU device or smaller model (ViT-B instead of ViT-H).

#### Poor Segmentation Quality
```
Warning: Segmentation quality below threshold
```
**Solutions**:
- Improve image lighting and focus
- Use higher resolution images
- Ensure scale marker is clearly visible
- Try different preprocessing settings

#### Scale Detection Failed
```
Warning: Scale marker not detected, using estimated scale
```
**Solutions**:
- Use standardized scale markers (rulers, coins)
- Ensure marker is unobstructed and well-lit
- Provide marker coordinates manually
- Use known scale factor if available

### Performance Issues

#### Slow Processing
- Use GPU acceleration if available
- Reduce image size for faster processing
- Use ViT-B model instead of larger variants
- Enable preprocessing to improve segmentation efficiency

#### High Memory Usage
- Process images sequentially instead of in parallel
- Use smaller SAM model variants
- Reduce image resolution
- Clear analyzer cache periodically

## Contributing

When contributing to the ML pipeline:

1. **Add Tests**: All new functionality must include comprehensive tests
2. **Quality Metrics**: Ensure quality assessment covers new features
3. **Error Handling**: Implement graceful degradation for failures
4. **Documentation**: Update this README and add docstrings
5. **Performance**: Consider memory and processing time impacts

## References

- [Segment Anything Model (SAM)](https://github.com/facebookresearch/segment-anything)
- [Kuz-Ram Fragmentation Model](https://en.wikipedia.org/wiki/Kuz%E2%80%93Ram_model)
- [Rosin-Rammler Distribution](https://en.wikipedia.org/wiki/Rosin%E2%80%93Rammler_distribution)
- [OpenCV Documentation](https://docs.opencv.org/)
- [scikit-learn Documentation](https://scikit-learn.org/)