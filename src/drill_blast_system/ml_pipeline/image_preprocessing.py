"""
Image preprocessing utilities for fragmentation analysis.

This module provides image preprocessing and scale detection capabilities
for preparing muckpile images for SAM-based fragmentation analysis.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional
import logging
from dataclasses import dataclass

from .data_structures import ImagePreprocessingResult, ScaleMarker

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses muckpile images for fragmentation analysis"""
    
    def __init__(self, 
                 target_size: Optional[Tuple[int, int]] = None,
                 enhance_contrast: bool = True,
                 reduce_noise: bool = True):
        """
        Initialize image preprocessor.
        
        Args:
            target_size: Target image size (width, height). If None, keeps original size
            enhance_contrast: Whether to apply contrast enhancement
            reduce_noise: Whether to apply noise reduction
        """
        self.target_size = target_size
        self.enhance_contrast = enhance_contrast
        self.reduce_noise = reduce_noise
    
    def preprocess_image(self, image_path: str) -> ImagePreprocessingResult:
        """
        Preprocess muckpile image for analysis.
        
        Args:
            image_path: Path to input image
            
        Returns:
            ImagePreprocessingResult with processed image and metadata
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            original_shape = image.shape[:2]
            processed_image = image.copy()
            
            # Track preprocessing parameters
            brightness_adj = 0.0
            contrast_adj = 1.0
            noise_reduction_applied = False
            flags = []
            
            # Convert to RGB for processing
            processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            
            # Assess initial image quality
            initial_quality = self._assess_image_quality(processed_image)
            
            # Apply brightness/contrast adjustment if needed
            if initial_quality['brightness_score'] < 0.6:
                brightness_adj, contrast_adj = self._auto_adjust_brightness_contrast(processed_image)
                processed_image = self._apply_brightness_contrast(processed_image, brightness_adj, contrast_adj)
                flags.append("brightness_contrast_adjusted")
            
            # Apply noise reduction if enabled and needed
            if self.reduce_noise and initial_quality['noise_level'] > 0.3:
                processed_image = self._reduce_noise(processed_image)
                noise_reduction_applied = True
                flags.append("noise_reduction_applied")
            
            # Enhance contrast if enabled
            if self.enhance_contrast:
                processed_image = self._enhance_contrast(processed_image)
                flags.append("contrast_enhanced")
            
            # Resize if target size specified
            if self.target_size:
                processed_image = cv2.resize(processed_image, self.target_size)
                flags.append("resized")
            
            # Final quality assessment
            final_quality = self._assess_image_quality(processed_image)
            
            return ImagePreprocessingResult(
                processed_image=processed_image,
                original_shape=original_shape,
                processed_shape=processed_image.shape[:2],
                brightness_adjustment=brightness_adj,
                contrast_adjustment=contrast_adj,
                noise_reduction_applied=noise_reduction_applied,
                image_quality_score=final_quality['overall_score'],
                sharpness_score=final_quality['sharpness_score'],
                lighting_uniformity=final_quality['lighting_uniformity'],
                preprocessing_flags=flags
            )
            
        except Exception as e:
            logger.error(f"Error preprocessing image {image_path}: {str(e)}")
            raise
    
    def _assess_image_quality(self, image: np.ndarray) -> dict:
        """Assess various quality metrics of the image"""
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Sharpness (Laplacian variance)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(sharpness / 1000.0, 1.0)  # Normalize
        
        # Brightness assessment
        mean_brightness = np.mean(gray)
        brightness_score = 1.0 - abs(mean_brightness - 127.5) / 127.5
        
        # Lighting uniformity (standard deviation of brightness)
        brightness_std = np.std(gray)
        lighting_uniformity = max(0.0, 1.0 - brightness_std / 64.0)
        
        # Noise level estimation (high frequency content)
        noise_level = np.std(cv2.Laplacian(gray, cv2.CV_64F)) / 255.0
        
        # Overall score
        overall_score = (sharpness_score * 0.4 + 
                        brightness_score * 0.3 + 
                        lighting_uniformity * 0.3)
        
        return {
            'sharpness_score': sharpness_score,
            'brightness_score': brightness_score,
            'lighting_uniformity': lighting_uniformity,
            'noise_level': noise_level,
            'overall_score': overall_score
        }
    
    def _auto_adjust_brightness_contrast(self, image: np.ndarray) -> Tuple[float, float]:
        """Automatically determine optimal brightness and contrast adjustments"""
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Calculate histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        # Find percentiles for contrast stretching
        cumsum = np.cumsum(hist)
        total_pixels = cumsum[-1]
        
        # Find 2nd and 98th percentiles
        p2 = np.where(cumsum >= total_pixels * 0.02)[0][0]
        p98 = np.where(cumsum >= total_pixels * 0.98)[0][0]
        
        # Calculate contrast adjustment
        if p98 > p2:
            contrast = 255.0 / (p98 - p2)
            brightness = -p2 * contrast
        else:
            contrast = 1.0
            brightness = 0.0
        
        # Limit adjustments to reasonable ranges
        contrast = np.clip(contrast, 0.5, 3.0)
        brightness = np.clip(brightness, -50, 50)
        
        return brightness, contrast
    
    def _apply_brightness_contrast(self, image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
        """Apply brightness and contrast adjustments"""
        
        adjusted = image.astype(np.float32)
        adjusted = adjusted * contrast + brightness
        adjusted = np.clip(adjusted, 0, 255)
        
        return adjusted.astype(np.uint8)
    
    def _reduce_noise(self, image: np.ndarray) -> np.ndarray:
        """Apply noise reduction using bilateral filter"""
        
        # Use bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(image, 9, 75, 75)
        
        return denoised
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
        
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        
        # Convert back to RGB
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        
        return enhanced


class ScaleDetector:
    """Detects scale markers in muckpile images for size calibration"""
    
    def __init__(self, 
                 known_marker_sizes: List[float] = None,
                 detection_method: str = "template_matching"):
        """
        Initialize scale detector.
        
        Args:
            known_marker_sizes: List of known marker sizes in mm
            detection_method: Method for detection ("template_matching", "contour_analysis")
        """
        self.known_marker_sizes = known_marker_sizes or [100.0, 200.0, 300.0]  # Common sizes in mm
        self.detection_method = detection_method
    
    def detect_scale_marker(self, 
                          image: np.ndarray,
                          marker_coords: Optional[Tuple[float, float, float, float]] = None) -> Optional[ScaleMarker]:
        """
        Detect scale marker in image.
        
        Args:
            image: Input image (RGB)
            marker_coords: Optional bounding box (x1, y1, x2, y2) if marker location is known
            
        Returns:
            ScaleMarker object if detected, None otherwise
        """
        try:
            if marker_coords:
                return self._detect_marker_in_region(image, marker_coords)
            else:
                return self._detect_marker_full_image(image)
                
        except Exception as e:
            logger.error(f"Error detecting scale marker: {str(e)}")
            return None
    
    def _detect_marker_in_region(self, 
                                image: np.ndarray, 
                                coords: Tuple[float, float, float, float]) -> Optional[ScaleMarker]:
        """Detect marker in specified region"""
        
        x1, y1, x2, y2 = coords
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        # Extract region of interest
        roi = image[y1:y2, x1:x2]
        
        if roi.size == 0:
            return None
        
        # Analyze the ROI for scale marker
        marker_info = self._analyze_marker_region(roi)
        
        if marker_info:
            # Adjust coordinates to full image
            marker_info['center_x'] += x1
            marker_info['center_y'] += y1
            
            return ScaleMarker(
                center_x=marker_info['center_x'],
                center_y=marker_info['center_y'],
                width=marker_info['width'],
                height=marker_info['height'],
                rotation=marker_info['rotation'],
                detection_confidence=marker_info['confidence'],
                physical_size_mm=marker_info['estimated_size_mm'],
                pixels_per_mm=marker_info['pixels_per_mm']
            )
        
        return None
    
    def _detect_marker_full_image(self, image: np.ndarray) -> Optional[ScaleMarker]:
        """Detect marker in full image using various methods"""
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Try different detection approaches
        candidates = []
        
        # Method 1: Look for rectangular objects (rulers, coins, etc.)
        rectangular_candidates = self._find_rectangular_markers(gray)
        candidates.extend(rectangular_candidates)
        
        # Method 2: Look for circular objects (coins, tokens)
        circular_candidates = self._find_circular_markers(gray)
        candidates.extend(circular_candidates)
        
        # Select best candidate
        if candidates:
            best_candidate = max(candidates, key=lambda x: x['confidence'])
            
            return ScaleMarker(
                center_x=best_candidate['center_x'],
                center_y=best_candidate['center_y'],
                width=best_candidate['width'],
                height=best_candidate['height'],
                rotation=best_candidate['rotation'],
                detection_confidence=best_candidate['confidence'],
                physical_size_mm=best_candidate['estimated_size_mm'],
                pixels_per_mm=best_candidate['pixels_per_mm']
            )
        
        return None
    
    def _analyze_marker_region(self, roi: np.ndarray) -> Optional[dict]:
        """Analyze a region of interest for scale marker properties"""
        
        gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Find largest contour (likely the marker)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle
        rect = cv2.minAreaRect(largest_contour)
        center, (width, height), rotation = rect
        
        # Calculate confidence based on contour properties
        area = cv2.contourArea(largest_contour)
        perimeter = cv2.arcLength(largest_contour, True)
        
        if perimeter == 0:
            return None
        
        # Circularity measure
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        
        # Aspect ratio
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 0
        
        # Estimate confidence based on shape regularity
        confidence = 0.5
        if 0.7 < circularity < 1.3:  # Roughly circular
            confidence += 0.3
        if 1.0 < aspect_ratio < 2.0:  # Reasonable aspect ratio
            confidence += 0.2
        
        # Estimate physical size (assume most common marker size)
        estimated_size_mm = self.known_marker_sizes[0]  # Default to first known size
        pixels_per_mm = max(width, height) / estimated_size_mm
        
        return {
            'center_x': center[0],
            'center_y': center[1],
            'width': width,
            'height': height,
            'rotation': rotation,
            'confidence': confidence,
            'estimated_size_mm': estimated_size_mm,
            'pixels_per_mm': pixels_per_mm
        }
    
    def _find_rectangular_markers(self, gray: np.ndarray) -> List[dict]:
        """Find rectangular scale markers (rulers, cards, etc.)"""
        
        candidates = []
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Look for rectangular shapes (4 corners)
            if len(approx) == 4:
                rect = cv2.minAreaRect(contour)
                center, (width, height), rotation = rect
                
                area = cv2.contourArea(contour)
                
                # Filter by size (reasonable marker size)
                if 1000 < area < 50000:  # Adjust based on expected marker sizes
                    aspect_ratio = max(width, height) / min(width, height)
                    
                    # Prefer rectangular markers (rulers, cards)
                    if 2.0 < aspect_ratio < 10.0:
                        confidence = 0.7 + min(0.3, area / 50000)
                        
                        # Estimate size based on aspect ratio
                        if aspect_ratio > 5:  # Likely a ruler
                            estimated_size_mm = 300.0  # Standard ruler
                        else:  # Likely a card or token
                            estimated_size_mm = 100.0
                        
                        pixels_per_mm = max(width, height) / estimated_size_mm
                        
                        candidates.append({
                            'center_x': center[0],
                            'center_y': center[1],
                            'width': width,
                            'height': height,
                            'rotation': rotation,
                            'confidence': confidence,
                            'estimated_size_mm': estimated_size_mm,
                            'pixels_per_mm': pixels_per_mm
                        })
        
        return candidates
    
    def _find_circular_markers(self, gray: np.ndarray) -> List[dict]:
        """Find circular scale markers (coins, tokens, etc.)"""
        
        candidates = []
        
        # Use HoughCircles to detect circular objects
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=20,
            maxRadius=200
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            
            for (x, y, r) in circles:
                # Estimate confidence based on circle properties
                confidence = 0.6
                
                # Estimate physical size (assume coin or token)
                estimated_size_mm = 25.0  # Typical coin diameter
                pixels_per_mm = (2 * r) / estimated_size_mm
                
                candidates.append({
                    'center_x': float(x),
                    'center_y': float(y),
                    'width': float(2 * r),
                    'height': float(2 * r),
                    'rotation': 0.0,
                    'confidence': confidence,
                    'estimated_size_mm': estimated_size_mm,
                    'pixels_per_mm': pixels_per_mm
                })
        
        return candidates