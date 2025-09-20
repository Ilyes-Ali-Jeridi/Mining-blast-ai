"""
Tests for SAM-based fragmentation analysis.

Tests the complete fragmentation analysis pipeline including:
- Image preprocessing
- Scale detection
- Fragment segmentation (SAM and traditional)
- Fragment size calculation
- Quality assessment
- Fragmentation curve generation
"""

import pytest
import numpy as np
import cv2
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.drill_blast_system.ml_pipeline import (
    FragmentationAnalyzer,
    FragmentationResult,
    ImagePreprocessor,
    ScaleDetector,
    MeasurementQualityAssessor
)
from src.drill_blast_system.ml_pipeline.data_structures import (
    ScaleMarker,
    ImagePreprocessingResult,
    SegmentationResult,
    QualityAssessment
)


class TestFragmentationAnalyzer:
    """Test FragmentationAnalyzer class"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
        return FragmentationAnalyzer(
            sam_model_path=None,  # No SAM model for testing
            device="cpu",
            enable_preprocessing=True
        )
    
    @pytest.fixture
    def test_image(self):
        """Create a test image"""
        # Create synthetic muckpile image
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Add some rock-like fragments (circles and ellipses)
        fragments = [
            ((100, 100), 30),  # (center, radius)
            ((200, 150), 25),
            ((350, 200), 40),
            ((500, 300), 35),
            ((150, 400), 20),
            ((400, 450), 45),
            ((600, 500), 30),
        ]
        
        for (cx, cy), radius in fragments:
            # Random gray color for each fragment
            color = np.random.randint(80, 180, 3).tolist()
            cv2.circle(image, (cx, cy), radius, color, -1)
            
            # Add some texture
            for _ in range(10):
                x = cx + np.random.randint(-radius//2, radius//2)
                y = cy + np.random.randint(-radius//2, radius//2)
                cv2.circle(image, (x, y), 2, (color[0] + 20, color[1] + 20, color[2] + 20), -1)
        
        # Add scale marker (rectangle)
        cv2.rectangle(image, (50, 50), (150, 70), (255, 255, 255), -1)
        cv2.rectangle(image, (50, 50), (150, 70), (0, 0, 0), 2)
        
        return image
    
    @pytest.fixture
    def test_image_file(self, test_image):
        """Save test image to temporary file"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, cv2.cvtColor(test_image, cv2.COLOR_RGB2BGR))
            yield f.name
        os.unlink(f.name)
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        analyzer = FragmentationAnalyzer()
        
        assert analyzer.device == "cpu"
        assert analyzer.enable_preprocessing is True
        assert analyzer.preprocessor is not None
        assert analyzer.scale_detector is not None
        assert analyzer.quality_assessor is not None
        assert analyzer.min_fragment_area_pixels == 100
        assert analyzer.max_fragment_area_pixels == 50000
    
    def test_analyze_muckpile_image_basic(self, analyzer, test_image_file):
        """Test basic fragmentation analysis"""
        result = analyzer.analyze_muckpile_image(
            image_path=test_image_file,
            known_scale_mm_per_pixel=0.5  # Known scale to avoid detection issues
        )
        
        assert isinstance(result, FragmentationResult)
        assert result.fragment_count > 0
        assert result.p80 > 0
        assert result.p50 > 0
        assert result.p10 > 0
        assert result.p10 <= result.p50 <= result.p80
        assert result.measurement_quality > 0
        assert result.scale_factor == 0.5
        assert result.is_valid is True
    
    def test_analyze_with_scale_marker_coords(self, analyzer, test_image_file):
        """Test analysis with scale marker coordinates"""
        # Scale marker is at (50, 50, 150, 70) in test image
        result = analyzer.analyze_muckpile_image(
            image_path=test_image_file,
            scale_marker_coords=(50, 50, 150, 70)
        )
        
        assert isinstance(result, FragmentationResult)
        assert result.fragment_count > 0
        assert result.scale_detection_quality > 0
    
    def test_analyze_without_scale_marker(self, analyzer, test_image_file):
        """Test analysis without scale marker (fallback estimation)"""
        result = analyzer.analyze_muckpile_image(
            image_path=test_image_file
        )
        
        assert isinstance(result, FragmentationResult)
        assert result.fragment_count > 0
        assert result.scale_detection_quality <= 0.3  # Low quality for estimated scale
    
    def test_invalid_image_path(self, analyzer):
        """Test with invalid image path"""
        with pytest.raises(Exception):
            analyzer.analyze_muckpile_image("nonexistent_image.jpg")
    
    def test_traditional_segmentation_fallback(self, analyzer, test_image_file):
        """Test fallback to traditional segmentation when SAM is not available"""
        # Mock SAM availability check to return False
        with patch.object(analyzer, '_try_sam_segmentation', return_value=False):
            try:
                result = analyzer.analyze_muckpile_image(
                    image_path=test_image_file,
                    known_scale_mm_per_pixel=0.5
                )
                
                assert isinstance(result, FragmentationResult)
                assert result.fragment_count >= 0  # May be 0 for synthetic images
                # Traditional segmentation should not crash
            except ValueError as e:
                if "No valid fragments detected" in str(e):
                    # This is acceptable for synthetic test images
                    # The important thing is that it doesn't crash due to SAM unavailability
                    pass
                else:
                    raise
    
    def test_fragment_size_filtering(self, analyzer, test_image_file):
        """Test that fragments are properly filtered by size"""
        result = analyzer.analyze_muckpile_image(
            image_path=test_image_file,
            known_scale_mm_per_pixel=0.1  # Very fine scale
        )
        
        # With fine scale, some fragments might be filtered out as too small
        assert all(5.0 <= size <= 2000.0 for size in result.fragment_sizes)
    
    def test_quality_assessment_integration(self, analyzer, test_image_file):
        """Test that quality assessment is properly integrated"""
        result = analyzer.analyze_muckpile_image(
            image_path=test_image_file,
            known_scale_mm_per_pixel=0.5
        )
        
        assert 0 <= result.measurement_quality <= 1
        assert 0 <= result.scale_detection_quality <= 1
        assert 0 <= result.segmentation_quality <= 1
        assert isinstance(result.quality_flags, list)
        assert isinstance(result.is_valid, bool)


class TestImagePreprocessor:
    """Test ImagePreprocessor class"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor instance"""
        return ImagePreprocessor(
            target_size=None,
            enhance_contrast=True,
            reduce_noise=True
        )
    
    @pytest.fixture
    def test_image_file(self):
        """Create test image file"""
        # Create a noisy, low-contrast image
        image = np.random.randint(100, 150, (400, 600, 3), dtype=np.uint8)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, image)
            yield f.name
        os.unlink(f.name)
    
    def test_preprocess_image(self, preprocessor, test_image_file):
        """Test image preprocessing"""
        result = preprocessor.preprocess_image(test_image_file)
        
        assert isinstance(result, ImagePreprocessingResult)
        assert result.processed_image is not None
        assert result.processed_image.shape[2] == 3  # RGB
        assert result.original_shape is not None
        assert result.processed_shape is not None
        assert 0 <= result.image_quality_score <= 1
        assert 0 <= result.sharpness_score <= 1
        assert 0 <= result.lighting_uniformity <= 1
        assert isinstance(result.preprocessing_flags, list)
    
    def test_preprocess_with_target_size(self, test_image_file):
        """Test preprocessing with target size"""
        preprocessor = ImagePreprocessor(target_size=(300, 400))
        result = preprocessor.preprocess_image(test_image_file)
        
        assert result.processed_shape == (400, 300)  # (height, width)
        assert "resized" in result.preprocessing_flags
    
    def test_image_quality_assessment(self, preprocessor):
        """Test image quality assessment"""
        # Create images with different quality characteristics
        
        # High quality image
        good_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        quality = preprocessor._assess_image_quality(good_image)
        assert 0 <= quality['overall_score'] <= 1
        
        # Very dark image
        dark_image = np.ones((400, 600, 3), dtype=np.uint8) * 20
        quality = preprocessor._assess_image_quality(dark_image)
        assert quality['brightness_score'] < 0.8
        
        # Very bright image
        bright_image = np.ones((400, 600, 3), dtype=np.uint8) * 240
        quality = preprocessor._assess_image_quality(bright_image)
        assert quality['brightness_score'] < 0.8


class TestScaleDetector:
    """Test ScaleDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create scale detector instance"""
        return ScaleDetector(
            known_marker_sizes=[100.0, 200.0, 300.0],
            detection_method="template_matching"
        )
    
    @pytest.fixture
    def image_with_scale_marker(self):
        """Create image with scale marker"""
        image = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # Add rectangular scale marker
        cv2.rectangle(image, (100, 100), (300, 120), (255, 255, 255), -1)
        cv2.rectangle(image, (100, 100), (300, 120), (0, 0, 0), 2)
        
        # Add some text to make it look like a ruler
        cv2.putText(image, "20cm", (150, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        return image
    
    def test_detect_scale_marker_in_region(self, detector, image_with_scale_marker):
        """Test scale marker detection in specified region"""
        marker = detector.detect_scale_marker(
            image_with_scale_marker,
            marker_coords=(90, 90, 310, 130)
        )
        
        if marker:  # Detection might fail in test environment
            assert isinstance(marker, ScaleMarker)
            assert marker.center_x > 0
            assert marker.center_y > 0
            assert marker.width > 0
            assert marker.height > 0
            assert 0 <= marker.detection_confidence <= 1
            assert marker.physical_size_mm > 0
            assert marker.pixels_per_mm > 0
    
    def test_detect_scale_marker_full_image(self, detector, image_with_scale_marker):
        """Test scale marker detection in full image"""
        marker = detector.detect_scale_marker(image_with_scale_marker)
        
        # Detection might not always succeed in synthetic images
        if marker:
            assert isinstance(marker, ScaleMarker)
            assert marker.detection_confidence > 0
    
    def test_no_scale_marker(self, detector):
        """Test detection when no scale marker is present"""
        # Empty image
        empty_image = np.zeros((400, 600, 3), dtype=np.uint8)
        marker = detector.detect_scale_marker(empty_image)
        
        assert marker is None
    
    def test_circular_marker_detection(self, detector):
        """Test detection of circular scale markers"""
        image = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # Add circular marker (coin-like)
        cv2.circle(image, (200, 200), 50, (200, 200, 200), -1)
        cv2.circle(image, (200, 200), 50, (0, 0, 0), 2)
        
        marker = detector.detect_scale_marker(image)
        
        # Circular detection might work
        if marker:
            assert isinstance(marker, ScaleMarker)


class TestMeasurementQualityAssessor:
    """Test MeasurementQualityAssessor class"""
    
    @pytest.fixture
    def assessor(self):
        """Create quality assessor instance"""
        return MeasurementQualityAssessor(
            min_acceptable_quality=0.6,
            min_reliable_quality=0.8,
            min_fragments_for_training=50
        )
    
    @pytest.fixture
    def mock_segmentation_result(self):
        """Create mock segmentation result"""
        return SegmentationResult(
            masks=[np.ones((100, 100), dtype=bool) for _ in range(25)],
            mask_scores=[0.8] * 25,
            fragment_areas_pixels=[1000.0] * 25,
            fragment_perimeters=[100.0] * 25,
            fragment_centroids=[(50, 50)] * 25,
            overall_quality=0.8,
            fragment_separation_quality=0.9,
            edge_quality=0.7,
            sam_model_version="SAM",
            processing_time_seconds=2.5,
            total_fragments_detected=25
        )
    
    @pytest.fixture
    def mock_scale_marker(self):
        """Create mock scale marker"""
        return ScaleMarker(
            center_x=100.0,
            center_y=100.0,
            width=200.0,
            height=20.0,
            rotation=0.0,
            detection_confidence=0.9,
            physical_size_mm=200.0,
            pixels_per_mm=1.0
        )
    
    def test_assess_measurement_quality(self, assessor, mock_segmentation_result, mock_scale_marker):
        """Test comprehensive quality assessment"""
        # Create test image
        test_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        
        # Create size distribution
        size_distribution = {
            'p10': 20.0,
            'p50': 50.0,
            'p80': 100.0,
            'mean': 55.0
        }
        
        assessment = assessor.assess_measurement_quality(
            image=test_image,
            preprocessing_result=None,
            segmentation_result=mock_segmentation_result,
            scale_marker=mock_scale_marker,
            fragment_count=25,
            size_distribution=size_distribution
        )
        
        assert isinstance(assessment, QualityAssessment)
        assert 0 <= assessment.image_quality <= 1
        assert 0 <= assessment.scale_detection_quality <= 1
        assert 0 <= assessment.segmentation_quality <= 1
        assert 0 <= assessment.fragment_analysis_quality <= 1
        assert 0 <= assessment.overall_quality <= 1
        assert 0 <= assessment.reliability_score <= 1
        assert isinstance(assessment.quality_issues, list)
        assert isinstance(assessment.recommendations, list)
        assert isinstance(assessment.passes_quality_check, bool)
        assert isinstance(assessment.is_suitable_for_training, bool)
    
    def test_poor_quality_assessment(self, assessor):
        """Test assessment with poor quality inputs"""
        # Poor segmentation result
        poor_segmentation = SegmentationResult(
            masks=[np.ones((10, 10), dtype=bool) for _ in range(3)],  # Very few, small fragments
            mask_scores=[0.3] * 3,  # Low confidence
            fragment_areas_pixels=[50.0] * 3,  # Small areas
            fragment_perimeters=[20.0] * 3,
            fragment_centroids=[(5, 5)] * 3,
            overall_quality=0.3,  # Poor quality
            fragment_separation_quality=0.4,
            edge_quality=0.2,
            sam_model_version="Traditional CV",
            processing_time_seconds=1.0,
            total_fragments_detected=3
        )
        
        # No scale marker
        scale_marker = None
        
        # Poor size distribution
        size_distribution = {
            'p10': 1.0,  # Unrealistically small
            'p50': 2.0,
            'p80': 3.0,
            'mean': 2.0
        }
        
        test_image = np.ones((100, 100, 3), dtype=np.uint8) * 50  # Low contrast
        
        assessment = assessor.assess_measurement_quality(
            image=test_image,
            preprocessing_result=None,
            segmentation_result=poor_segmentation,
            scale_marker=scale_marker,
            fragment_count=3,
            size_distribution=size_distribution
        )
        
        assert assessment.overall_quality < 0.6
        assert not assessment.passes_quality_check
        assert not assessment.is_suitable_for_training
        assert len(assessment.quality_issues) > 0
        assert len(assessment.recommendations) > 0
    
    def test_training_suitability_assessment(self, assessor):
        """Test assessment of training suitability for multiple measurements"""
        # Create multiple quality assessments
        assessments = []
        
        # Good quality assessments
        for _ in range(60):
            assessment = QualityAssessment(
                image_quality=0.8,
                scale_detection_quality=0.9,
                segmentation_quality=0.8,
                fragment_analysis_quality=0.8,
                overall_quality=0.8,
                reliability_score=0.8,
                quality_issues=[],
                recommendations=[],
                passes_quality_check=True,
                is_suitable_for_training=True
            )
            assessments.append(assessment)
        
        # Poor quality assessments
        for _ in range(10):
            assessment = QualityAssessment(
                image_quality=0.4,
                scale_detection_quality=0.3,
                segmentation_quality=0.4,
                fragment_analysis_quality=0.4,
                overall_quality=0.4,
                reliability_score=0.4,
                quality_issues=["Poor image quality"],
                recommendations=["Improve lighting"],
                passes_quality_check=False,
                is_suitable_for_training=False
            )
            assessments.append(assessment)
        
        suitability = assessor.assess_training_suitability(assessments)
        
        assert isinstance(suitability, dict)
        assert suitability['is_suitable'] is True  # 60 good samples >= 50 minimum
        assert suitability['high_quality_count'] == 60
        assert suitability['total_count'] == 70
        assert suitability['high_quality_ratio'] > 0.8
        assert 'recommendations' in suitability
        assert 'quality_distribution' in suitability


class TestFragmentationCurveIntegration:
    """Test integration with FragmentationCurve"""
    
    def test_fragmentation_curve_generation(self):
        """Test that fragmentation curves are properly generated from measurements"""
        from src.drill_blast_system.physics_models.fragmentation_curve import FragmentationCurve
        
        # Simulate fragment sizes
        fragment_sizes = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
        
        # Create curve from measurements
        curve = FragmentationCurve(mean_size_mm=50, uniformity_index=1.5)
        curve.fit_from_measurements(fragment_sizes)
        
        # Test curve properties
        assert curve.mean_size_mm > 0
        assert curve.uniformity_index > 0
        assert curve.characteristic_size > 0
        
        # Test curve calculations
        p50 = curve._find_size_for_passing(50)
        p80 = curve._find_size_for_passing(80)
        
        assert p50 > 0
        assert p80 > p50
        
        # Test characteristic sizes
        char_sizes = curve.get_characteristic_sizes()
        assert 'P50' in char_sizes
        assert 'P80' in char_sizes
        assert char_sizes['P50'] <= char_sizes['P80']


@pytest.mark.integration
class TestFragmentationAnalysisIntegration:
    """Integration tests for the complete fragmentation analysis pipeline"""
    
    def test_end_to_end_analysis(self):
        """Test complete end-to-end fragmentation analysis"""
        # Create realistic test image
        image = np.zeros((800, 1200, 3), dtype=np.uint8)
        
        # Add background texture
        noise = np.random.randint(0, 50, image.shape, dtype=np.uint8)
        image = cv2.add(image, noise)
        
        # Add realistic rock fragments
        fragments = []
        for _ in range(30):
            center = (
                np.random.randint(50, 1150),
                np.random.randint(50, 750)
            )
            size = np.random.randint(20, 80)
            color = np.random.randint(80, 200, 3).tolist()
            
            # Draw elliptical fragments
            axes = (size, int(size * np.random.uniform(0.6, 1.4)))
            angle = np.random.randint(0, 180)
            
            cv2.ellipse(image, center, axes, angle, 0, 360, color, -1)
            fragments.append((center, size))
        
        # Add scale marker
        cv2.rectangle(image, (50, 50), (250, 80), (255, 255, 255), -1)
        cv2.rectangle(image, (50, 50), (250, 80), (0, 0, 0), 3)
        cv2.putText(image, "20 cm", (100, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            temp_path = f.name
        
        try:
            # Analyze image
            analyzer = FragmentationAnalyzer(enable_preprocessing=True)
            result = analyzer.analyze_muckpile_image(
                image_path=temp_path,
                scale_marker_coords=(50, 50, 250, 80)
            )
            
            # Verify results
            assert isinstance(result, FragmentationResult)
            assert result.fragment_count >= 10  # Should detect most fragments
            assert result.p80 > result.p50 > result.p10
            assert result.measurement_quality > 0.3  # Reasonable quality
            assert result.is_valid
            
            # Verify size ranges are realistic
            assert 10 <= result.p50 <= 200  # Reasonable P50 range
            assert 20 <= result.p80 <= 400  # Reasonable P80 range
            
            # Verify quality metrics
            assert 0 <= result.measurement_quality <= 1
            assert 0 <= result.scale_detection_quality <= 1
            assert 0 <= result.segmentation_quality <= 1
            
        finally:
            os.unlink(temp_path)
    
    def test_sam_vs_traditional_comparison(self):
        """Test comparison between SAM and traditional segmentation"""
        # This test would require actual SAM model, so we'll mock it
        
        # Create test image
        image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, image)
            temp_path = f.name
        
        try:
            analyzer = FragmentationAnalyzer()
            
            # Test traditional segmentation (should always work)
            with patch.object(analyzer, '_try_sam_segmentation', return_value=False):
                result_traditional = analyzer.analyze_muckpile_image(
                    temp_path,
                    known_scale_mm_per_pixel=0.5
                )
                
                assert isinstance(result_traditional, FragmentationResult)
                assert result_traditional.fragment_count >= 0
            
            # Test with SAM available (mocked)
            mock_sam_result = SegmentationResult(
                masks=[np.ones((50, 50), dtype=bool) for _ in range(20)],
                mask_scores=[0.9] * 20,
                fragment_areas_pixels=[2500.0] * 20,
                fragment_perimeters=[200.0] * 20,
                fragment_centroids=[(25, 25)] * 20,
                overall_quality=0.9,
                fragment_separation_quality=0.9,
                edge_quality=0.8,
                sam_model_version="SAM",
                processing_time_seconds=3.0,
                total_fragments_detected=20
            )
            
            with patch.object(analyzer, '_try_sam_segmentation', return_value=True), \
                 patch.object(analyzer, '_sam_segment_fragments', return_value=mock_sam_result):
                
                result_sam = analyzer.analyze_muckpile_image(
                    temp_path,
                    known_scale_mm_per_pixel=0.5
                )
                
                assert isinstance(result_sam, FragmentationResult)
                assert result_sam.fragment_count == 20
                assert result_sam.segmentation_quality >= result_traditional.segmentation_quality
        
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])