"""
Example script demonstrating SAM-based fragmentation analysis.

This script shows how to use the fragmentation analysis pipeline to:
1. Analyze muckpile images for fragment size distribution
2. Assess measurement quality
3. Generate fragmentation curves
4. Compare different segmentation methods

Usage:
    python examples/fragmentation_analysis_example.py [image_path]
"""

import sys
import os
import numpy as np
import cv2
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drill_blast_system.ml_pipeline import (
    FragmentationAnalyzer,
    ImagePreprocessor,
    ScaleDetector,
    MeasurementQualityAssessor
)
from drill_blast_system.ml_pipeline.data_structures import ScaleMarker


def create_synthetic_muckpile_image(width: int = 1200, height: int = 800) -> np.ndarray:
    """
    Create a synthetic muckpile image for demonstration.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Synthetic muckpile image as numpy array
    """
    print("Creating synthetic muckpile image...")
    
    # Create base image with rock-like background
    image = np.random.randint(60, 120, (height, width, 3), dtype=np.uint8)
    
    # Add texture noise
    noise = np.random.randint(-20, 20, (height, width, 3), dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Generate realistic rock fragments
    fragment_count = np.random.randint(30, 80)
    fragments_info = []
    
    for i in range(fragment_count):
        # Random position (avoid edges)
        center_x = np.random.randint(50, width - 50)
        center_y = np.random.randint(50, height - 50)
        
        # Random size (log-normal distribution for realistic sizes)
        base_size = np.random.lognormal(mean=3.0, sigma=0.5)  # Log-normal for realistic distribution
        size = int(np.clip(base_size, 15, 100))
        
        # Random color (rock-like)
        base_color = np.random.randint(80, 180)
        color = [
            base_color + np.random.randint(-20, 20),
            base_color + np.random.randint(-20, 20),
            base_color + np.random.randint(-20, 20)
        ]
        color = [max(0, min(255, c)) for c in color]
        
        # Random shape (ellipse with random orientation)
        axes_ratio = np.random.uniform(0.6, 1.4)
        axes = (size, int(size * axes_ratio))
        angle = np.random.randint(0, 180)
        
        # Draw fragment
        cv2.ellipse(image, (center_x, center_y), axes, angle, 0, 360, color, -1)
        
        # Add some internal texture
        for _ in range(5):
            texture_x = center_x + np.random.randint(-size//2, size//2)
            texture_y = center_y + np.random.randint(-size//2, size//2)
            texture_size = np.random.randint(2, 8)
            texture_color = [c + np.random.randint(-30, 30) for c in color]
            texture_color = [max(0, min(255, c)) for c in texture_color]
            cv2.circle(image, (texture_x, texture_y), texture_size, texture_color, -1)
        
        fragments_info.append({
            'center': (center_x, center_y),
            'size': size,
            'axes': axes,
            'angle': angle
        })
    
    # Add scale marker (ruler-like)
    marker_x1, marker_y1 = 50, 50
    marker_x2, marker_y2 = 250, 80
    
    # White background for marker
    cv2.rectangle(image, (marker_x1, marker_y1), (marker_x2, marker_y2), (255, 255, 255), -1)
    
    # Black border
    cv2.rectangle(image, (marker_x1, marker_y1), (marker_x2, marker_y2), (0, 0, 0), 3)
    
    # Add ruler markings
    for i in range(5):
        x = marker_x1 + 20 + i * 40
        cv2.line(image, (x, marker_y1 + 5), (x, marker_y2 - 5), (0, 0, 0), 2)
    
    # Add text
    cv2.putText(image, "20 cm", (marker_x1 + 60, marker_y1 + 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    print(f"Created synthetic image with {fragment_count} fragments")
    return image, fragments_info


def demonstrate_image_preprocessing(image: np.ndarray) -> None:
    """Demonstrate image preprocessing capabilities."""
    print("\n=== Image Preprocessing Demo ===")
    
    preprocessor = ImagePreprocessor(
        target_size=None,  # Keep original size
        enhance_contrast=True,
        reduce_noise=True
    )
    
    # Save original image temporarily
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        cv2.imwrite(f.name, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        temp_path = f.name
    
    try:
        # Preprocess image
        result = preprocessor.preprocess_image(temp_path)
        
        print(f"Original shape: {result.original_shape}")
        print(f"Processed shape: {result.processed_shape}")
        print(f"Image quality score: {result.image_quality_score:.3f}")
        print(f"Sharpness score: {result.sharpness_score:.3f}")
        print(f"Lighting uniformity: {result.lighting_uniformity:.3f}")
        print(f"Preprocessing flags: {result.preprocessing_flags}")
        
    finally:
        os.unlink(temp_path)


def demonstrate_scale_detection(image: np.ndarray) -> ScaleMarker:
    """Demonstrate scale marker detection."""
    print("\n=== Scale Detection Demo ===")
    
    detector = ScaleDetector(
        known_marker_sizes=[200.0],  # 20cm = 200mm
        detection_method="template_matching"
    )
    
    # Try to detect scale marker in known region
    marker_coords = (50, 50, 250, 80)  # Known marker location
    marker = detector.detect_scale_marker(image, marker_coords)
    
    if marker:
        print(f"Scale marker detected!")
        print(f"  Center: ({marker.center_x:.1f}, {marker.center_y:.1f})")
        print(f"  Size: {marker.width:.1f} x {marker.height:.1f} pixels")
        print(f"  Physical size: {marker.physical_size_mm:.1f} mm")
        print(f"  Scale factor: {marker.pixels_per_mm:.3f} pixels/mm")
        print(f"  Detection confidence: {marker.detection_confidence:.3f}")
    else:
        print("Scale marker not detected, will use estimated scale")
        # Create fallback marker
        marker = ScaleMarker(
            center_x=150.0,
            center_y=65.0,
            width=200.0,
            height=30.0,
            rotation=0.0,
            detection_confidence=0.3,
            physical_size_mm=200.0,
            pixels_per_mm=1.0
        )
    
    return marker


def demonstrate_fragmentation_analysis(image: np.ndarray, 
                                     fragments_info: list,
                                     scale_marker: ScaleMarker) -> None:
    """Demonstrate complete fragmentation analysis."""
    print("\n=== Fragmentation Analysis Demo ===")
    
    # Initialize analyzer
    analyzer = FragmentationAnalyzer(
        sam_model_path=None,  # Will use traditional segmentation
        device="cpu",
        enable_preprocessing=True
    )
    
    # Save image temporarily
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        cv2.imwrite(f.name, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        temp_path = f.name
    
    try:
        # Analyze fragmentation
        print("Running fragmentation analysis...")
        result = analyzer.analyze_muckpile_image(
            image_path=temp_path,
            scale_marker_coords=(50, 50, 250, 80),
            known_scale_mm_per_pixel=None  # Let it detect scale
        )
        
        print(f"\n--- Analysis Results ---")
        print(f"Fragment count: {result.fragment_count}")
        print(f"P10: {result.p10:.1f} mm")
        print(f"P50: {result.p50:.1f} mm") 
        print(f"P80: {result.p80:.1f} mm")
        print(f"Mean size: {result.mean_size:.1f} mm")
        print(f"Characteristic size: {result.characteristic_size:.1f} mm")
        print(f"Uniformity index: {result.uniformity_index:.2f}")
        
        print(f"\n--- Quality Metrics ---")
        print(f"Overall quality: {result.measurement_quality:.3f}")
        print(f"Scale detection quality: {result.scale_detection_quality:.3f}")
        print(f"Segmentation quality: {result.segmentation_quality:.3f}")
        print(f"Is valid: {result.is_valid}")
        
        if result.quality_flags:
            print(f"Quality flags: {result.quality_flags}")
        
        print(f"\n--- Processing Info ---")
        print(f"Scale factor: {result.scale_factor:.3f} mm/pixel")
        print(f"Total analyzed area: {result.total_analyzed_area:.0f} mm²")
        print(f"Processing time: {result.processing_timestamp}")
        
        # Compare with ground truth (synthetic data)
        print(f"\n--- Ground Truth Comparison ---")
        actual_count = len(fragments_info)
        detected_count = result.fragment_count
        print(f"Actual fragments: {actual_count}")
        print(f"Detected fragments: {detected_count}")
        print(f"Detection rate: {detected_count/actual_count*100:.1f}%")
        
        # Estimate actual P80 from synthetic data
        actual_sizes = [info['size'] * result.scale_factor for info in fragments_info]
        actual_p80 = np.percentile(actual_sizes, 80)
        print(f"Actual P80 (estimated): {actual_p80:.1f} mm")
        print(f"Detected P80: {result.p80:.1f} mm")
        print(f"P80 error: {abs(result.p80 - actual_p80)/actual_p80*100:.1f}%")
        
    finally:
        os.unlink(temp_path)


def demonstrate_quality_assessment(image: np.ndarray) -> None:
    """Demonstrate measurement quality assessment."""
    print("\n=== Quality Assessment Demo ===")
    
    assessor = MeasurementQualityAssessor(
        min_acceptable_quality=0.6,
        min_reliable_quality=0.8,
        min_fragments_for_training=50
    )
    
    # Create mock data for demonstration
    from drill_blast_system.ml_pipeline.data_structures import (
        SegmentationResult, ScaleMarker, QualityAssessment
    )
    
    # Mock segmentation result
    mock_segmentation = SegmentationResult(
        masks=[np.ones((50, 50), dtype=bool) for _ in range(25)],
        mask_scores=[0.8] * 25,
        fragment_areas_pixels=[2500.0] * 25,
        fragment_perimeters=[200.0] * 25,
        fragment_centroids=[(25, 25)] * 25,
        overall_quality=0.8,
        fragment_separation_quality=0.9,
        edge_quality=0.7,
        sam_model_version="Traditional CV",
        processing_time_seconds=2.0,
        total_fragments_detected=25
    )
    
    # Mock scale marker
    mock_scale = ScaleMarker(
        center_x=150.0, center_y=65.0, width=200.0, height=30.0,
        rotation=0.0, detection_confidence=0.9, physical_size_mm=200.0,
        pixels_per_mm=1.0
    )
    
    # Mock size distribution
    size_distribution = {
        'p10': 25.0, 'p50': 50.0, 'p80': 100.0, 'mean': 55.0
    }
    
    # Assess quality
    assessment = assessor.assess_measurement_quality(
        image=image,
        preprocessing_result=None,
        segmentation_result=mock_segmentation,
        scale_marker=mock_scale,
        fragment_count=25,
        size_distribution=size_distribution
    )
    
    print(f"Image quality: {assessment.image_quality:.3f}")
    print(f"Scale detection quality: {assessment.scale_detection_quality:.3f}")
    print(f"Segmentation quality: {assessment.segmentation_quality:.3f}")
    print(f"Fragment analysis quality: {assessment.fragment_analysis_quality:.3f}")
    print(f"Overall quality: {assessment.overall_quality:.3f}")
    print(f"Reliability score: {assessment.reliability_score:.3f}")
    print(f"Quality grade: {assessment.quality_grade}")
    print(f"Passes quality check: {assessment.passes_quality_check}")
    print(f"Suitable for training: {assessment.is_suitable_for_training}")
    
    if assessment.quality_issues:
        print(f"Quality issues: {assessment.quality_issues}")
    
    if assessment.recommendations:
        print(f"Recommendations: {assessment.recommendations}")


def demonstrate_fragmentation_curve_generation() -> None:
    """Demonstrate fragmentation curve generation and analysis."""
    print("\n=== Fragmentation Curve Demo ===")
    
    from drill_blast_system.physics_models.fragmentation_curve import FragmentationCurve
    
    # Create fragmentation curve from synthetic measurements
    fragment_sizes = [
        10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
        85, 90, 95, 100, 110, 120, 130, 140, 150, 160, 180, 200
    ]
    
    # Create curve
    curve = FragmentationCurve(mean_size_mm=75, uniformity_index=1.5)
    curve.fit_from_measurements(fragment_sizes)
    
    print(f"Fitted curve parameters:")
    print(f"  Mean size: {curve.mean_size_mm:.1f} mm")
    print(f"  Characteristic size: {curve.characteristic_size:.1f} mm")
    print(f"  Uniformity index: {curve.uniformity_index:.2f}")
    print(f"  Distribution type: {curve.distribution_type.value}")
    
    # Get characteristic sizes
    char_sizes = curve.get_characteristic_sizes()
    print(f"\nCharacteristic sizes:")
    for size_name, size_value in char_sizes.items():
        if size_name in ['P10', 'P50', 'P80', 'mean']:
            print(f"  {size_name}: {size_value:.1f} mm")
    
    # Generate sieve analysis
    sieve_analysis = curve.get_sieve_analysis()
    print(f"\nSieve analysis (selected sizes):")
    for i, (size, passing) in enumerate(zip(sieve_analysis.sieve_sizes_mm, 
                                          sieve_analysis.cumulative_passing)):
        if size in [25, 50, 100, 150]:
            print(f"  {size:3.0f} mm: {passing*100:5.1f}% passing")
    
    # Generate visualization data
    viz_data = curve.get_visualization_data(num_points=20)
    print(f"\nVisualization data (sample points):")
    for i in range(0, len(viz_data['sizes_mm']), 4):
        size = viz_data['sizes_mm'][i]
        passing = viz_data['passing_percentage'][i]
        print(f"  {size:6.1f} mm: {passing:5.1f}% passing")


def main():
    """Main demonstration function."""
    print("=== SAM-based Fragmentation Analysis Demo ===")
    print("This demo shows the complete fragmentation analysis pipeline.")
    
    # Check if image path provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print(f"Error: Image file '{image_path}' not found.")
            return
        
        print(f"Loading image: {image_path}")
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        fragments_info = []  # No ground truth for real images
    else:
        print("No image provided, creating synthetic muckpile image...")
        image, fragments_info = create_synthetic_muckpile_image()
    
    print(f"Image shape: {image.shape}")
    
    # Run demonstrations
    try:
        # 1. Image preprocessing
        demonstrate_image_preprocessing(image)
        
        # 2. Scale detection
        scale_marker = demonstrate_scale_detection(image)
        
        # 3. Fragmentation analysis
        demonstrate_fragmentation_analysis(image, fragments_info, scale_marker)
        
        # 4. Quality assessment
        demonstrate_quality_assessment(image)
        
        # 5. Fragmentation curve generation
        demonstrate_fragmentation_curve_generation()
        
        print("\n=== Demo Complete ===")
        print("The fragmentation analysis pipeline successfully demonstrated:")
        print("✓ Image preprocessing and quality assessment")
        print("✓ Scale marker detection and calibration")
        print("✓ Fragment segmentation (traditional CV fallback)")
        print("✓ Fragment size calculation and statistics")
        print("✓ Quality assessment and validation")
        print("✓ Fragmentation curve generation and analysis")
        
        print("\nNote: This demo uses traditional computer vision segmentation.")
        print("For SAM-based segmentation, install segment-anything:")
        print("pip install git+https://github.com/facebookresearch/segment-anything.git")
        print("And download a SAM model checkpoint from:")
        print("https://github.com/facebookresearch/segment-anything#model-checkpoints")
        
    except Exception as e:
        print(f"\nError during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()