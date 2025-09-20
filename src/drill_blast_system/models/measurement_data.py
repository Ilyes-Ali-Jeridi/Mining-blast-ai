"""
MeasurementData model for storing post-blast measurements.
Implements requirement 5.1, 5.2, 5.3: Post-blast measurement storage and learning pipeline.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, JSON, Text, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.database import BaseModel


class MeasurementType(str, Enum):
    """Measurement data type enumeration."""
    FRAGMENTATION = "fragmentation"        # Muckpile fragmentation analysis
    PPV = "ppv"                           # Peak Particle Velocity
    VIBRATION = "vibration"               # General vibration monitoring
    AIRBLAST = "airblast"                 # Air overpressure
    FLYROCK = "flyrock"                   # Flyrock distance/trajectory
    DISPLACEMENT = "displacement"          # Ground displacement
    NOISE = "noise"                       # Noise level measurements


class MeasurementQuality(str, Enum):
    """Measurement quality assessment."""
    EXCELLENT = "excellent"    # High confidence, suitable for model training
    GOOD = "good"             # Good quality, usable for training
    FAIR = "fair"             # Acceptable quality, use with caution
    POOR = "poor"             # Low quality, exclude from training
    INVALID = "invalid"       # Invalid data, do not use


class MeasurementData(BaseModel):
    """
    Post-blast measurements for learning and validation.
    
    Stores various types of post-blast measurements including:
    - Fragmentation analysis from muckpile images
    - PPV sensor readings and vibration data
    - Air overpressure and noise measurements
    - Quality assessments and confidence scores
    """
    __tablename__ = "measurement_data"
    
    # Foreign key to blast record
    blast_record_id = Column(Integer, ForeignKey("blast_records.id"), nullable=False, index=True)
    
    # Measurement identification
    measurement_name = Column(String(200), nullable=False)
    measurement_type = Column(SQLEnum(MeasurementType), nullable=False, index=True)
    measurement_quality = Column(SQLEnum(MeasurementQuality), nullable=False, index=True)
    
    # Measurement metadata
    measurement_date = Column(DateTime, nullable=False, index=True)
    measurement_method = Column(String(100), nullable=False)  # image_analysis, sieving, sensor, etc.
    operator_name = Column(String(100), nullable=True)
    equipment_used = Column(String(200), nullable=True)
    
    # Location information
    measurement_location = Column(JSON, nullable=True)
    """
    Measurement location structure:
    {
        "coordinates": {"x": float, "y": float, "z": float},
        "description": str,                    # Human-readable location
        "reference_system": str,               # coordinate system used
        "accuracy": float,                     # location accuracy in meters
        "measurement_area": {                  # For area measurements like fragmentation
            "polygon": [{"x": float, "y": float}, ...],
            "area_m2": float
        }
    }
    """
    
    # Core measurement values
    measured_values = Column(JSON, nullable=False)
    """
    Measured values structure (varies by measurement_type):
    
    For FRAGMENTATION:
    {
        "p10": float,                          # mm (10% passing)
        "p50": float,                          # mm (50% passing)
        "p80": float,                          # mm (80% passing)
        "mean_size": float,                    # mm
        "max_size": float,                     # mm
        "uniformity_index": float,             # Distribution parameter
        "sieve_analysis": {
            "sieve_sizes_mm": [float],         # Sieve sizes
            "passing_percent": [float],        # Percent passing each sieve
            "retained_percent": [float]        # Percent retained on each sieve
        },
        "fragment_count": int,                 # Number of fragments analyzed
        "total_area_analyzed": float,          # m² of muckpile analyzed
        "scale_factor": float,                 # pixels/mm conversion
        "distribution_fit": {
            "distribution_type": str,          # rosin_rammler, swebrec, etc.
            "parameters": dict,                # Distribution parameters
            "r_squared": float                 # Goodness of fit
        }
    }
    
    For PPV:
    {
        "peak_ppv": float,                     # mm/s
        "dominant_frequency": float,           # Hz
        "duration": float,                     # seconds
        "vector_sum": float,                   # mm/s (if 3-component)
        "components": {                        # Individual components
            "vertical": float,                 # mm/s
            "longitudinal": float,             # mm/s
            "transverse": float                # mm/s
        },
        "frequency_spectrum": {
            "frequencies": [float],            # Hz
            "amplitudes": [float]              # mm/s
        },
        "distance_to_blast": float,            # meters
        "charge_weight": float                 # kg (nearest charge or total)
    }
    
    For VIBRATION:
    {
        "peak_acceleration": float,            # m/s²
        "peak_velocity": float,                # mm/s
        "peak_displacement": float,            # mm
        "dominant_frequency": float,           # Hz
        "duration": float,                     # seconds
        "rms_values": {
            "acceleration": float,             # m/s²
            "velocity": float,                 # mm/s
            "displacement": float              # mm
        }
    }
    
    For AIRBLAST:
    {
        "peak_overpressure": float,            # Pa or dB
        "duration": float,                     # seconds
        "impulse": float,                      # Pa·s
        "frequency_content": {
            "frequencies": [float],            # Hz
            "amplitudes": [float]              # Pa or dB
        }
    }
    """
    
    # Quality assessment and confidence
    quality_metrics = Column(JSON, nullable=True)
    """
    Quality metrics structure:
    {
        "confidence_score": float,             # 0-1 overall confidence
        "data_completeness": float,            # 0-1 completeness score
        "measurement_accuracy": float,         # Estimated accuracy (%)
        "environmental_conditions": {
            "weather": str,                    # clear, rain, fog, etc.
            "lighting": str,                   # good, poor, artificial
            "visibility": float,               # meters
            "wind_speed": float                # m/s
        },
        "equipment_status": {
            "calibration_date": str,           # ISO format
            "battery_level": float,            # % (for sensors)
            "signal_quality": str,             # excellent, good, fair, poor
            "interference_detected": bool
        },
        "operator_assessment": {
            "difficulty_rating": int,          # 1-5 scale
            "notes": str,
            "recommended_for_training": bool
        }
    }
    """
    
    # File references (images, sensor data files, etc.)
    file_references = Column(JSON, nullable=True)
    """
    File references structure:
    {
        "images": [
            {
                "file_path": str,              # Path in storage system
                "file_type": str,              # jpg, png, tiff, etc.
                "description": str,            # Image description
                "capture_timestamp": str,      # ISO format
                "camera_settings": {
                    "resolution": str,         # e.g., "1920x1080"
                    "focal_length": float,     # mm
                    "aperture": str,           # e.g., "f/8"
                    "iso": int
                },
                "scale_reference": {           # For fragmentation images
                    "reference_object": str,   # coin, ruler, etc.
                    "known_size_mm": float,
                    "pixel_coordinates": [int] # [x1, y1, x2, y2]
                }
            }, ...
        ],
        "sensor_data_files": [
            {
                "file_path": str,
                "file_format": str,            # csv, binary, etc.
                "sampling_rate": float,        # Hz
                "duration": float,             # seconds
                "channels": [str],             # channel names
                "preprocessing_applied": [str] # filters, corrections, etc.
            }, ...
        ],
        "analysis_outputs": [
            {
                "file_path": str,
                "analysis_type": str,          # segmentation, fft, etc.
                "software_used": str,
                "version": str,
                "parameters": dict
            }, ...
        ]
    }
    """
    
    # Processing metadata
    processing_metadata = Column(JSON, nullable=True)
    """
    Processing metadata structure:
    {
        "processing_timestamp": str,           # ISO format
        "processing_method": str,              # manual, automated, hybrid
        "software_used": {
            "name": str,                       # SAM, ImageJ, custom, etc.
            "version": str,
            "parameters": dict
        },
        "preprocessing_steps": [
            {
                "step_name": str,
                "parameters": dict,
                "timestamp": str
            }, ...
        ],
        "validation_checks": [
            {
                "check_name": str,
                "status": str,                 # PASS, FAIL, WARNING
                "details": str
            }, ...
        ],
        "processing_time": float,              # seconds
        "manual_review_required": bool,
        "reviewer_notes": str
    }
    """
    
    # Comparison with predictions
    prediction_comparison = Column(JSON, nullable=True)
    """
    Prediction comparison structure:
    {
        "predicted_values": dict,              # Copy of relevant predicted values
        "comparison_metrics": {
            "absolute_error": float,
            "relative_error_percent": float,
            "bias": float,                     # predicted - measured
            "within_tolerance": bool
        },
        "model_performance": {
            "model_version": str,
            "prediction_confidence": float,    # 0-1 if available
            "feature_importance": dict         # If ML model used
        }
    }
    """
    
    # Notes and comments
    notes = Column(Text, nullable=True)
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_by = Column(String(100), nullable=True)
    validation_date = Column(DateTime, nullable=True)
    
    # Flags for data usage
    use_for_training = Column(Boolean, default=True, nullable=False)
    use_for_validation = Column(Boolean, default=True, nullable=False)
    is_outlier = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    blast_record = relationship("BlastRecord", back_populates="measurement_data")
    
    @hybrid_property
    def measurement_age_days(self) -> float:
        """Calculate age of measurement in days."""
        return (datetime.utcnow() - self.measurement_date).total_seconds() / 86400
    
    @hybrid_property
    def confidence_score(self) -> Optional[float]:
        """Get overall confidence score."""
        if self.quality_metrics:
            return self.quality_metrics.get('confidence_score')
        return None
    
    @hybrid_property
    def is_high_quality(self) -> bool:
        """Check if measurement is high quality for training."""
        return (self.measurement_quality in [MeasurementQuality.EXCELLENT, MeasurementQuality.GOOD] and
                self.use_for_training and
                not self.is_outlier)
    
    def get_fragmentation_p80(self) -> Optional[float]:
        """Get P80 value for fragmentation measurements."""
        if self.measurement_type != MeasurementType.FRAGMENTATION:
            return None
        return self.measured_values.get('p80')
    
    def get_ppv_value(self) -> Optional[float]:
        """Get peak PPV value for vibration measurements."""
        if self.measurement_type not in [MeasurementType.PPV, MeasurementType.VIBRATION]:
            return None
        return self.measured_values.get('peak_ppv')
    
    def calculate_prediction_error(self) -> Optional[float]:
        """
        Calculate prediction error if comparison data available.
        
        Returns:
            Relative error as percentage (None if no comparison data)
        """
        if not self.prediction_comparison:
            return None
        
        comparison = self.prediction_comparison.get('comparison_metrics', {})
        return comparison.get('relative_error_percent')
    
    def get_sieve_analysis(self) -> Optional[Dict[str, List[float]]]:
        """
        Get sieve analysis data for fragmentation measurements.
        
        Returns:
            Dict with sieve_sizes_mm and passing_percent lists
        """
        if self.measurement_type != MeasurementType.FRAGMENTATION:
            return None
        
        sieve_data = self.measured_values.get('sieve_analysis', {})
        if 'sieve_sizes_mm' in sieve_data and 'passing_percent' in sieve_data:
            return {
                'sieve_sizes_mm': sieve_data['sieve_sizes_mm'],
                'passing_percent': sieve_data['passing_percent']
            }
        return None
    
    def get_image_paths(self) -> List[str]:
        """Get list of image file paths associated with this measurement."""
        if not self.file_references or 'images' not in self.file_references:
            return []
        
        return [img['file_path'] for img in self.file_references['images']]
    
    def add_validation_check(self, check_name: str, status: str, details: str = "") -> None:
        """
        Add a validation check to processing metadata.
        
        Args:
            check_name: Name of the validation check
            status: PASS, FAIL, or WARNING
            details: Additional details about the check
        """
        if not self.processing_metadata:
            self.processing_metadata = {}
        
        if 'validation_checks' not in self.processing_metadata:
            self.processing_metadata['validation_checks'] = []
        
        validation_check = {
            'check_name': check_name,
            'status': status,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.processing_metadata['validation_checks'].append(validation_check)
    
    def mark_as_outlier(self, reason: str) -> None:
        """
        Mark measurement as outlier and exclude from training.
        
        Args:
            reason: Reason for marking as outlier
        """
        self.is_outlier = True
        self.use_for_training = False
        
        if not self.notes:
            self.notes = f"Marked as outlier: {reason}"
        else:
            self.notes += f"\nMarked as outlier: {reason}"
    
    def validate_measurement_data(self) -> List[str]:
        """
        Validate measurement data for completeness and consistency.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.measured_values:
            errors.append("Measured values are required")
            return errors
        
        # Type-specific validation
        if self.measurement_type == MeasurementType.FRAGMENTATION:
            required_fields = ['p50', 'p80']
            for field in required_fields:
                if field not in self.measured_values:
                    errors.append(f"Missing required fragmentation field: {field}")
                elif self.measured_values[field] <= 0:
                    errors.append(f"Fragmentation {field} must be positive")
        
        elif self.measurement_type == MeasurementType.PPV:
            if 'peak_ppv' not in self.measured_values:
                errors.append("Missing required PPV field: peak_ppv")
            elif self.measured_values['peak_ppv'] < 0:
                errors.append("Peak PPV cannot be negative")
        
        # Check measurement date
        if self.measurement_date > datetime.utcnow():
            errors.append("Measurement date cannot be in the future")
        
        # Check quality assessment
        if self.measurement_quality == MeasurementQuality.INVALID and self.use_for_training:
            errors.append("Invalid measurements cannot be used for training")
        
        return errors
    
    def __repr__(self) -> str:
        """String representation of the measurement data."""
        return f"<MeasurementData(id={self.id}, type='{self.measurement_type}', quality='{self.measurement_quality}', blast_id={self.blast_record_id})>"