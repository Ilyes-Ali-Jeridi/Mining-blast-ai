"""
Data structures for ML pipeline and fragmentation analysis.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime


@dataclass
class FragmentationResult:
    """Results from SAM-based fragmentation analysis"""
    
    # Fragment size statistics
    p10: float  # 10th percentile size (mm)
    p50: float  # 50th percentile size (mm) 
    p80: float  # 80th percentile size (mm)
    mean_size: float  # Mean fragment size (mm)
    
    # Distribution parameters
    characteristic_size: float  # Xc parameter (mm)
    uniformity_index: float  # n parameter
    
    # Fragment data
    fragment_count: int
    fragment_sizes: List[float]  # Individual fragment sizes (mm)
    fragment_areas: List[float]  # Fragment areas (mm²)
    
    # Quality metrics
    measurement_quality: float  # 0-1 confidence score
    scale_detection_quality: float  # 0-1 scale marker detection quality
    segmentation_quality: float  # 0-1 segmentation quality
    
    # Processing metadata
    image_path: str
    processing_timestamp: datetime
    scale_factor: float  # pixels per mm
    total_analyzed_area: float  # mm²
    
    # Quality flags
    quality_flags: List[str]  # List of quality issues detected
    is_valid: bool  # Overall validity flag


@dataclass
class ScaleMarker:
    """Scale marker detection result"""
    
    # Marker geometry
    center_x: float  # Pixel coordinates
    center_y: float
    width: float  # Marker width in pixels
    height: float  # Marker height in pixels
    rotation: float  # Rotation angle in degrees
    
    # Detection confidence
    detection_confidence: float  # 0-1 confidence score
    
    # Known physical size
    physical_size_mm: float  # Known size in mm
    
    # Calculated scale
    pixels_per_mm: float  # Calculated scale factor


@dataclass
class ImagePreprocessingResult:
    """Result from image preprocessing"""
    
    # Processed image data
    processed_image: np.ndarray
    original_shape: Tuple[int, int]
    processed_shape: Tuple[int, int]
    
    # Preprocessing parameters
    brightness_adjustment: float
    contrast_adjustment: float
    noise_reduction_applied: bool
    
    # Quality metrics
    image_quality_score: float  # 0-1 overall quality
    sharpness_score: float  # Image sharpness metric
    lighting_uniformity: float  # Lighting quality metric
    
    # Processing flags
    preprocessing_flags: List[str]


@dataclass
class SegmentationResult:
    """Result from SAM segmentation"""
    
    # Segmentation masks
    masks: List[np.ndarray]  # Individual fragment masks
    mask_scores: List[float]  # Confidence scores for each mask
    
    # Fragment properties
    fragment_areas_pixels: List[float]  # Areas in pixels
    fragment_perimeters: List[float]  # Perimeters in pixels
    fragment_centroids: List[Tuple[float, float]]  # Centroid coordinates
    
    # Segmentation quality
    overall_quality: float  # 0-1 segmentation quality
    fragment_separation_quality: float  # How well fragments are separated
    edge_quality: float  # Quality of fragment edges
    
    # Processing metadata
    sam_model_version: str
    processing_time_seconds: float
    total_fragments_detected: int


@dataclass
class ModelMetrics:
    """Metrics for residual learning model performance"""
    
    # Training metrics
    train_r2: float
    train_rmse: float
    train_mae: float
    
    # Validation metrics  
    val_r2: float
    val_rmse: float
    val_mae: float
    
    # Cross-validation metrics
    cv_r2_mean: float
    cv_r2_std: float
    cv_rmse_mean: float
    cv_rmse_std: float
    
    # Feature importance
    feature_importance: Dict[str, float]
    
    # Model metadata
    model_version: str
    training_samples: int
    training_timestamp: datetime
    
    # Performance flags
    is_reliable: bool  # Whether model meets reliability thresholds
    reliability_flags: List[str]  # Issues affecting reliability


@dataclass
class QualityAssessment:
    """Overall quality assessment for fragmentation measurement"""
    
    # Individual component scores (0-1)
    image_quality: float
    scale_detection_quality: float
    segmentation_quality: float
    fragment_analysis_quality: float
    
    # Overall scores
    overall_quality: float  # Weighted combination
    reliability_score: float  # Confidence in results
    
    # Quality flags and recommendations
    quality_issues: List[str]
    recommendations: List[str]
    
    # Pass/fail status
    passes_quality_check: bool
    is_suitable_for_training: bool  # Whether suitable for ML training
    
    # Quality thresholds
    min_acceptable_quality: float = 0.6
    min_reliable_quality: float = 0.8
    
    @property
    def quality_grade(self) -> str:
        """Return quality grade A-F"""
        if self.overall_quality >= 0.9:
            return "A"
        elif self.overall_quality >= 0.8:
            return "B" 
        elif self.overall_quality >= 0.7:
            return "C"
        elif self.overall_quality >= 0.6:
            return "D"
        else:
            return "F"