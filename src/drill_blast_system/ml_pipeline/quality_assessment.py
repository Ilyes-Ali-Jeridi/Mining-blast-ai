"""
Quality assessment for fragmentation measurements.

This module provides comprehensive quality assessment for fragmentation analysis
results to ensure measurement reliability and suitability for training.
"""

import numpy as np
from typing import List, Dict, Optional
import logging

from .data_structures import (
    QualityAssessment,
    ImagePreprocessingResult,
    SegmentationResult,
    ScaleMarker
)

logger = logging.getLogger(__name__)


class MeasurementQualityAssessor:
    """Assesses quality of fragmentation measurements"""
    
    def __init__(self,
                 min_acceptable_quality: float = 0.6,
                 min_reliable_quality: float = 0.8,
                 min_fragments_for_training: int = 50):
        """
        Initialize quality assessor.
        
        Args:
            min_acceptable_quality: Minimum quality threshold for acceptance
            min_reliable_quality: Minimum quality threshold for reliability
            min_fragments_for_training: Minimum fragments needed for ML training
        """
        self.min_acceptable_quality = min_acceptable_quality
        self.min_reliable_quality = min_reliable_quality
        self.min_fragments_for_training = min_fragments_for_training
        
        # Quality weights for overall score calculation
        self.quality_weights = {
            'image_quality': 0.25,
            'scale_detection': 0.25,
            'segmentation': 0.30,
            'fragment_analysis': 0.20
        }
    
    def assess_measurement_quality(self,
                                 image: np.ndarray,
                                 preprocessing_result: Optional[ImagePreprocessingResult],
                                 segmentation_result: SegmentationResult,
                                 scale_marker: Optional[ScaleMarker],
                                 fragment_count: int,
                                 size_distribution: Dict[str, float]) -> QualityAssessment:
        """
        Comprehensive quality assessment of fragmentation measurement.
        
        Args:
            image: Original or preprocessed image
            preprocessing_result: Image preprocessing results
            segmentation_result: Fragment segmentation results
            scale_marker: Scale marker detection results
            fragment_count: Number of detected fragments
            size_distribution: Fragment size statistics
            
        Returns:
            QualityAssessment with detailed quality metrics
        """
        
        # Assess individual components
        image_quality = self._assess_image_quality(image, preprocessing_result)
        scale_quality = self._assess_scale_detection_quality(scale_marker)
        segmentation_quality = self._assess_segmentation_quality(segmentation_result, fragment_count)
        fragment_quality = self._assess_fragment_analysis_quality(size_distribution, fragment_count)
        
        # Calculate overall quality
        overall_quality = (
            image_quality * self.quality_weights['image_quality'] +
            scale_quality * self.quality_weights['scale_detection'] +
            segmentation_quality * self.quality_weights['segmentation'] +
            fragment_quality * self.quality_weights['fragment_analysis']
        )
        
        # Calculate reliability score (stricter than overall quality)
        reliability_score = min(image_quality, scale_quality, segmentation_quality, fragment_quality)
        
        # Identify quality issues and recommendations
        quality_issues = []
        recommendations = []
        
        if image_quality < 0.7:
            quality_issues.append("Poor image quality")
            recommendations.append("Improve lighting and image sharpness")
        
        if scale_quality < 0.7:
            quality_issues.append("Scale detection issues")
            recommendations.append("Ensure scale marker is clearly visible and unobstructed")
        
        if segmentation_quality < 0.7:
            quality_issues.append("Poor fragment segmentation")
            recommendations.append("Improve image contrast or use manual segmentation correction")
        
        if fragment_quality < 0.7:
            quality_issues.append("Insufficient or unrealistic fragment analysis")
            recommendations.append("Verify fragment detection parameters and size ranges")
        
        if fragment_count < 20:
            quality_issues.append("Too few fragments detected")
            recommendations.append("Capture image with more visible fragments or adjust detection sensitivity")
        
        # Determine pass/fail status
        passes_quality_check = overall_quality >= self.min_acceptable_quality
        is_suitable_for_training = (
            overall_quality >= self.min_reliable_quality and
            fragment_count >= self.min_fragments_for_training and
            reliability_score >= 0.7
        )
        
        return QualityAssessment(
            image_quality=image_quality,
            scale_detection_quality=scale_quality,
            segmentation_quality=segmentation_quality,
            fragment_analysis_quality=fragment_quality,
            overall_quality=overall_quality,
            reliability_score=reliability_score,
            min_acceptable_quality=self.min_acceptable_quality,
            min_reliable_quality=self.min_reliable_quality,
            quality_issues=quality_issues,
            recommendations=recommendations,
            passes_quality_check=passes_quality_check,
            is_suitable_for_training=is_suitable_for_training
        )
    
    def _assess_image_quality(self, 
                            image: np.ndarray, 
                            preprocessing_result: Optional[ImagePreprocessingResult]) -> float:
        """Assess overall image quality"""
        
        if preprocessing_result:
            # Use preprocessing quality metrics if available
            base_quality = preprocessing_result.image_quality_score
            sharpness_bonus = min(0.2, preprocessing_result.sharpness_score * 0.2)
            lighting_bonus = min(0.1, preprocessing_result.lighting_uniformity * 0.1)
            
            quality = base_quality + sharpness_bonus + lighting_bonus
        else:
            # Calculate basic quality metrics
            quality = self._calculate_basic_image_quality(image)
        
        return min(1.0, quality)
    
    def _calculate_basic_image_quality(self, image: np.ndarray) -> float:
        """Calculate basic image quality metrics"""
        
        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = np.mean(image, axis=2)
        else:
            gray = image
        
        # Sharpness (Laplacian variance)
        laplacian_var = np.var(np.gradient(gray))
        sharpness_score = min(1.0, laplacian_var / 1000.0)
        
        # Brightness distribution
        mean_brightness = np.mean(gray)
        brightness_score = 1.0 - abs(mean_brightness - 127.5) / 127.5
        
        # Contrast (standard deviation)
        contrast_score = min(1.0, np.std(gray) / 64.0)
        
        # Overall quality
        quality = (sharpness_score * 0.4 + brightness_score * 0.3 + contrast_score * 0.3)
        
        return quality
    
    def _assess_scale_detection_quality(self, scale_marker: Optional[ScaleMarker]) -> float:
        """Assess scale detection quality"""
        
        if scale_marker is None:
            return 0.3  # Low quality for estimated scale
        
        base_quality = scale_marker.detection_confidence
        
        # Bonus for reasonable scale factors
        if 0.1 <= scale_marker.pixels_per_mm <= 10.0:
            scale_reasonableness = 1.0
        else:
            scale_reasonableness = 0.5
        
        # Penalty for very small or very large markers
        marker_size_pixels = max(scale_marker.width, scale_marker.height)
        if 50 <= marker_size_pixels <= 500:
            size_quality = 1.0
        else:
            size_quality = 0.7
        
        quality = base_quality * scale_reasonableness * size_quality
        
        return min(1.0, quality)
    
    def _assess_segmentation_quality(self, 
                                   segmentation_result: SegmentationResult,
                                   fragment_count: int) -> float:
        """Assess segmentation quality"""
        
        base_quality = segmentation_result.overall_quality
        
        # Fragment count quality
        if 20 <= fragment_count <= 500:
            count_quality = 1.0
        elif fragment_count < 20:
            count_quality = fragment_count / 20.0
        else:
            count_quality = max(0.5, 500.0 / fragment_count)
        
        # Fragment separation quality
        separation_quality = segmentation_result.fragment_separation_quality
        
        # Edge quality
        edge_quality = segmentation_result.edge_quality
        
        # Processing method quality (SAM is better than traditional)
        if "SAM" in segmentation_result.sam_model_version:
            method_quality = 1.0
        else:
            method_quality = 0.8
        
        # Combine metrics
        quality = (
            base_quality * 0.4 +
            count_quality * 0.2 +
            separation_quality * 0.2 +
            edge_quality * 0.1 +
            method_quality * 0.1
        )
        
        return min(1.0, quality)
    
    def _assess_fragment_analysis_quality(self, 
                                        size_distribution: Dict[str, float],
                                        fragment_count: int) -> float:
        """Assess fragment analysis quality"""
        
        # Check for reasonable size distribution
        p10 = size_distribution.get('p10', 0)
        p50 = size_distribution.get('p50', 0)
        p80 = size_distribution.get('p80', 0)
        mean_size = size_distribution.get('mean', 0)
        
        # Size distribution should be reasonable
        size_quality = 1.0
        
        # P80 should be larger than P50, which should be larger than P10
        if not (p10 <= p50 <= p80):
            size_quality *= 0.5
        
        # Sizes should be in reasonable range for rock fragments (5mm to 2000mm)
        if not (5 <= p10 <= 2000 and 5 <= p50 <= 2000 and 5 <= p80 <= 2000):
            size_quality *= 0.7
        
        # P80/P10 ratio should be reasonable (not too uniform, not too spread)
        if p10 > 0:
            size_ratio = p80 / p10
            if 2 <= size_ratio <= 50:
                ratio_quality = 1.0
            else:
                ratio_quality = 0.6
        else:
            ratio_quality = 0.5
        
        # Fragment count quality
        if fragment_count >= 50:
            count_quality = 1.0
        elif fragment_count >= 20:
            count_quality = 0.8
        elif fragment_count >= 10:
            count_quality = 0.6
        else:
            count_quality = 0.3
        
        # Statistical validity (coefficient of variation)
        if mean_size > 0 and fragment_count > 1:
            # Estimate CV from percentiles (rough approximation)
            estimated_std = (p80 - p10) / 2.56  # Approximate std from percentile range
            cv = estimated_std / mean_size
            
            # Reasonable CV for rock fragmentation is 0.3 to 1.5
            if 0.3 <= cv <= 1.5:
                cv_quality = 1.0
            else:
                cv_quality = 0.7
        else:
            cv_quality = 0.5
        
        # Combine metrics
        quality = (
            size_quality * 0.3 +
            ratio_quality * 0.2 +
            count_quality * 0.3 +
            cv_quality * 0.2
        )
        
        return min(1.0, quality)
    
    def assess_training_suitability(self, 
                                  quality_assessments: List[QualityAssessment]) -> Dict[str, any]:
        """
        Assess suitability of a collection of measurements for ML training.
        
        Args:
            quality_assessments: List of quality assessments for multiple measurements
            
        Returns:
            Dictionary with training suitability metrics
        """
        
        if not quality_assessments:
            return {
                'is_suitable': False,
                'reason': 'No measurements provided',
                'recommendations': ['Collect fragmentation measurements']
            }
        
        # Count high-quality measurements
        high_quality_count = sum(1 for qa in quality_assessments if qa.is_suitable_for_training)
        total_count = len(quality_assessments)
        
        # Calculate average quality
        avg_quality = np.mean([qa.overall_quality for qa in quality_assessments])
        avg_reliability = np.mean([qa.reliability_score for qa in quality_assessments])
        
        # Check minimum requirements
        min_samples_met = high_quality_count >= self.min_fragments_for_training
        quality_threshold_met = avg_quality >= self.min_reliable_quality
        reliability_threshold_met = avg_reliability >= 0.7
        
        is_suitable = min_samples_met and quality_threshold_met and reliability_threshold_met
        
        # Generate recommendations
        recommendations = []
        if not min_samples_met:
            recommendations.append(f"Collect at least {self.min_fragments_for_training} high-quality measurements")
        
        if not quality_threshold_met:
            recommendations.append("Improve overall measurement quality")
        
        if not reliability_threshold_met:
            recommendations.append("Improve measurement reliability and consistency")
        
        # Identify common quality issues
        common_issues = {}
        for qa in quality_assessments:
            for issue in qa.quality_issues:
                common_issues[issue] = common_issues.get(issue, 0) + 1
        
        # Add recommendations for common issues
        for issue, count in common_issues.items():
            if count > total_count * 0.3:  # If issue affects >30% of measurements
                if issue == "Poor image quality":
                    recommendations.append("Improve camera settings and lighting conditions")
                elif issue == "Scale detection issues":
                    recommendations.append("Use more visible and standardized scale markers")
                elif issue == "Poor fragment segmentation":
                    recommendations.append("Consider manual segmentation correction or better image preprocessing")
        
        return {
            'is_suitable': is_suitable,
            'high_quality_count': high_quality_count,
            'total_count': total_count,
            'high_quality_ratio': high_quality_count / total_count if total_count > 0 else 0,
            'average_quality': avg_quality,
            'average_reliability': avg_reliability,
            'common_issues': common_issues,
            'recommendations': recommendations,
            'quality_distribution': {
                'A_grade': sum(1 for qa in quality_assessments if qa.quality_grade == 'A'),
                'B_grade': sum(1 for qa in quality_assessments if qa.quality_grade == 'B'),
                'C_grade': sum(1 for qa in quality_assessments if qa.quality_grade == 'C'),
                'D_grade': sum(1 for qa in quality_assessments if qa.quality_grade == 'D'),
                'F_grade': sum(1 for qa in quality_assessments if qa.quality_grade == 'F')
            }
        }