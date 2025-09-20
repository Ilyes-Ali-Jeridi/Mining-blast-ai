"""
Measurement data Pydantic schemas for API validation.
Implements requirements 5.1, 5.2, 5.3 for measurement data validation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, validator

from .common import Coordinates, FileReference, NumericRange


class MeasurementTypeEnum(str, Enum):
    """Measurement type enumeration for validation."""
    FRAGMENTATION = "fragmentation"
    PPV = "ppv"
    VIBRATION = "vibration"
    AIRBLAST = "airblast"
    FLYROCK = "flyrock"
    DISPLACEMENT = "displacement"
    NOISE = "noise"


class MeasurementQualityEnum(str, Enum):
    """Measurement quality enumeration for validation."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


class MeasurementLocation(BaseModel):
    """Measurement location validation schema."""
    coordinates: Coordinates = Field(..., description="Measurement coordinates")
    description: Optional[str] = Field(None, description="Human-readable location description")
    reference_system: Optional[str] = Field(None, description="Coordinate system used")
    accuracy: Optional[float] = Field(None, gt=0, description="Location accuracy in meters")
    measurement_area: Optional[Dict[str, Any]] = Field(None, description="Area measurement details")
    
    class Config:
        schema_extra = {
            "example": {
                "coordinates": {"x": 1000.0, "y": 2000.0, "z": 200.0},
                "description": "Muckpile center, north face",
                "reference_system": "mine_grid",
                "accuracy": 0.5,
                "measurement_area": {
                    "polygon": [
                        {"x": 995.0, "y": 1995.0},
                        {"x": 1005.0, "y": 1995.0},
                        {"x": 1005.0, "y": 2005.0},
                        {"x": 995.0, "y": 2005.0}
                    ],
                    "area_m2": 100.0
                }
            }
        }


class SieveAnalysis(BaseModel):
    """Sieve analysis validation schema."""
    sieve_sizes_mm: List[float] = Field(..., min_items=2, description="Sieve sizes in mm")
    passing_percent: List[float] = Field(..., min_items=2, description="Percent passing each sieve")
    retained_percent: Optional[List[float]] = Field(None, description="Percent retained on each sieve")
    
    @validator('passing_percent')
    def validate_passing_percent(cls, v, values):
        if 'sieve_sizes_mm' in values and len(v) != len(values['sieve_sizes_mm']):
            raise ValueError('passing_percent must have same length as sieve_sizes_mm')
        
        for percent in v:
            if not 0 <= percent <= 100:
                raise ValueError('All passing percentages must be between 0 and 100')
        
        # Check that passing percentages are non-increasing (larger sieves have lower passing %)
        if not all(v[i] >= v[i+1] for i in range(len(v)-1)):
            raise ValueError('Passing percentages must be non-increasing with sieve size')
        
        return v
    
    @validator('sieve_sizes_mm')
    def validate_sieve_sizes(cls, v):
        if not all(size > 0 for size in v):
            raise ValueError('All sieve sizes must be positive')
        
        # Check that sieve sizes are in ascending order
        if not all(v[i] <= v[i+1] for i in range(len(v)-1)):
            raise ValueError('Sieve sizes must be in ascending order')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "sieve_sizes_mm": [25.0, 50.0, 100.0, 200.0, 400.0],
                "passing_percent": [15.2, 35.8, 65.4, 85.7, 95.3],
                "retained_percent": [15.2, 20.6, 29.6, 20.3, 9.6]
            }
        }


class FragmentationMeasurement(BaseModel):
    """Fragmentation measurement validation schema."""
    p10: float = Field(..., gt=0, description="P10 fragment size in mm")
    p50: float = Field(..., gt=0, description="P50 fragment size in mm")
    p80: float = Field(..., gt=0, description="P80 fragment size in mm")
    mean_size: Optional[float] = Field(None, gt=0, description="Mean fragment size in mm")
    max_size: Optional[float] = Field(None, gt=0, description="Maximum fragment size in mm")
    uniformity_index: Optional[float] = Field(None, gt=0, description="Distribution uniformity index")
    
    sieve_analysis: Optional[SieveAnalysis] = Field(None, description="Sieve analysis data")
    fragment_count: Optional[int] = Field(None, gt=0, description="Number of fragments analyzed")
    total_area_analyzed: Optional[float] = Field(None, gt=0, description="Total area analyzed in m²")
    scale_factor: Optional[float] = Field(None, gt=0, description="Pixels per mm conversion factor")
    
    distribution_fit: Optional[Dict[str, Any]] = Field(None, description="Distribution fitting results")
    
    @validator('p80')
    def validate_percentiles(cls, v, values):
        if 'p50' in values and v <= values['p50']:
            raise ValueError('P80 must be greater than P50')
        return v
    
    @validator('p50')
    def validate_p50(cls, v, values):
        if 'p10' in values and v <= values['p10']:
            raise ValueError('P50 must be greater than P10')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "p10": 45.2,
                "p50": 95.8,
                "p80": 185.3,
                "mean_size": 125.7,
                "max_size": 850.0,
                "uniformity_index": 1.28,
                "fragment_count": 1247,
                "total_area_analyzed": 25.5,
                "scale_factor": 2.35,
                "distribution_fit": {
                    "distribution_type": "rosin_rammler",
                    "parameters": {"n": 1.28, "xc": 110.5},
                    "r_squared": 0.95
                }
            }
        }


class PPVComponents(BaseModel):
    """PPV components validation schema."""
    vertical: float = Field(..., ge=0, description="Vertical component in mm/s")
    longitudinal: float = Field(..., ge=0, description="Longitudinal component in mm/s")
    transverse: float = Field(..., ge=0, description="Transverse component in mm/s")
    
    class Config:
        schema_extra = {
            "example": {
                "vertical": 1.8,
                "longitudinal": 1.2,
                "transverse": 0.9
            }
        }


class FrequencySpectrum(BaseModel):
    """Frequency spectrum validation schema."""
    frequencies: List[float] = Field(..., min_items=2, description="Frequency values in Hz")
    amplitudes: List[float] = Field(..., min_items=2, description="Amplitude values")
    
    @validator('amplitudes')
    def validate_amplitudes_length(cls, v, values):
        if 'frequencies' in values and len(v) != len(values['frequencies']):
            raise ValueError('amplitudes must have same length as frequencies')
        return v
    
    @validator('frequencies')
    def validate_frequencies(cls, v):
        if not all(freq >= 0 for freq in v):
            raise ValueError('All frequencies must be non-negative')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "frequencies": [5.0, 10.0, 15.0, 20.0, 25.0],
                "amplitudes": [0.5, 1.8, 1.2, 0.8, 0.3]
            }
        }


class PPVMeasurement(BaseModel):
    """PPV measurement validation schema."""
    peak_ppv: float = Field(..., ge=0, description="Peak particle velocity in mm/s")
    dominant_frequency: Optional[float] = Field(None, gt=0, description="Dominant frequency in Hz")
    duration: Optional[float] = Field(None, gt=0, description="Signal duration in seconds")
    vector_sum: Optional[float] = Field(None, ge=0, description="Vector sum PPV in mm/s")
    
    components: Optional[PPVComponents] = Field(None, description="Individual PPV components")
    frequency_spectrum: Optional[FrequencySpectrum] = Field(None, description="Frequency spectrum")
    
    distance_to_blast: Optional[float] = Field(None, gt=0, description="Distance to blast in meters")
    charge_weight: Optional[float] = Field(None, gt=0, description="Relevant charge weight in kg")
    
    class Config:
        schema_extra = {
            "example": {
                "peak_ppv": 1.8,
                "dominant_frequency": 12.5,
                "duration": 2.3,
                "vector_sum": 2.1,
                "components": {
                    "vertical": 1.8,
                    "longitudinal": 1.2,
                    "transverse": 0.9
                },
                "distance_to_blast": 250.0,
                "charge_weight": 845.0
            }
        }


class VibrationMeasurement(BaseModel):
    """General vibration measurement validation schema."""
    peak_acceleration: Optional[float] = Field(None, ge=0, description="Peak acceleration in m/s²")
    peak_velocity: Optional[float] = Field(None, ge=0, description="Peak velocity in mm/s")
    peak_displacement: Optional[float] = Field(None, ge=0, description="Peak displacement in mm")
    dominant_frequency: Optional[float] = Field(None, gt=0, description="Dominant frequency in Hz")
    duration: Optional[float] = Field(None, gt=0, description="Signal duration in seconds")
    
    rms_values: Optional[Dict[str, float]] = Field(None, description="RMS values for different parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "peak_acceleration": 0.15,
                "peak_velocity": 1.8,
                "peak_displacement": 0.05,
                "dominant_frequency": 12.5,
                "duration": 2.3,
                "rms_values": {
                    "acceleration": 0.08,
                    "velocity": 0.9,
                    "displacement": 0.02
                }
            }
        }


class AirblastMeasurement(BaseModel):
    """Airblast measurement validation schema."""
    peak_overpressure: float = Field(..., ge=0, description="Peak overpressure in Pa or dB")
    duration: Optional[float] = Field(None, gt=0, description="Signal duration in seconds")
    impulse: Optional[float] = Field(None, ge=0, description="Impulse in Pa·s")
    frequency_content: Optional[FrequencySpectrum] = Field(None, description="Frequency content")
    
    class Config:
        schema_extra = {
            "example": {
                "peak_overpressure": 120.5,
                "duration": 0.8,
                "impulse": 15.2,
                "frequency_content": {
                    "frequencies": [10.0, 20.0, 30.0, 40.0],
                    "amplitudes": [110.0, 120.5, 115.0, 105.0]
                }
            }
        }


class EnvironmentalConditions(BaseModel):
    """Environmental conditions validation schema."""
    weather: Optional[str] = Field(None, description="Weather conditions")
    lighting: Optional[str] = Field(None, description="Lighting conditions")
    visibility: Optional[float] = Field(None, gt=0, description="Visibility in meters")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in m/s")
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity in %")
    
    class Config:
        schema_extra = {
            "example": {
                "weather": "clear",
                "lighting": "good",
                "visibility": 1000.0,
                "wind_speed": 5.2,
                "temperature": 22.5,
                "humidity": 65.0
            }
        }


class EquipmentStatus(BaseModel):
    """Equipment status validation schema."""
    calibration_date: Optional[datetime] = Field(None, description="Last calibration date")
    battery_level: Optional[float] = Field(None, ge=0, le=100, description="Battery level in %")
    signal_quality: Optional[str] = Field(None, description="Signal quality assessment")
    interference_detected: Optional[bool] = Field(None, description="Interference detection flag")
    
    class Config:
        schema_extra = {
            "example": {
                "calibration_date": "2024-01-10T08:00:00Z",
                "battery_level": 85.0,
                "signal_quality": "excellent",
                "interference_detected": False
            }
        }


class OperatorAssessment(BaseModel):
    """Operator assessment validation schema."""
    difficulty_rating: int = Field(..., ge=1, le=5, description="Difficulty rating (1-5 scale)")
    notes: Optional[str] = Field(None, description="Operator notes")
    recommended_for_training: bool = Field(True, description="Recommendation for training use")
    
    class Config:
        schema_extra = {
            "example": {
                "difficulty_rating": 2,
                "notes": "Good lighting conditions, clear muckpile boundaries",
                "recommended_for_training": True
            }
        }


class QualityMetrics(BaseModel):
    """Quality metrics validation schema."""
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence score (0-1)")
    data_completeness: Optional[float] = Field(None, ge=0, le=1, description="Data completeness score (0-1)")
    measurement_accuracy: Optional[float] = Field(None, gt=0, description="Estimated accuracy in %")
    
    environmental_conditions: Optional[EnvironmentalConditions] = Field(None, description="Environmental conditions")
    equipment_status: Optional[EquipmentStatus] = Field(None, description="Equipment status")
    operator_assessment: Optional[OperatorAssessment] = Field(None, description="Operator assessment")
    
    class Config:
        schema_extra = {
            "example": {
                "confidence_score": 0.92,
                "data_completeness": 0.98,
                "measurement_accuracy": 5.2,
                "environmental_conditions": {
                    "weather": "clear",
                    "lighting": "good",
                    "visibility": 1000.0
                },
                "operator_assessment": {
                    "difficulty_rating": 2,
                    "recommended_for_training": True
                }
            }
        }


class ProcessingStep(BaseModel):
    """Processing step validation schema."""
    step_name: str = Field(..., description="Processing step name")
    parameters: Dict[str, Any] = Field(..., description="Step parameters")
    timestamp: datetime = Field(..., description="Step execution timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "step_name": "image_segmentation",
                "parameters": {
                    "algorithm": "watershed",
                    "threshold": 0.5,
                    "min_fragment_size": 10
                },
                "timestamp": "2024-01-15T10:35:00Z"
            }
        }


class ValidationCheck(BaseModel):
    """Validation check validation schema."""
    check_name: str = Field(..., description="Validation check name")
    status: str = Field(..., pattern=r'^(PASS|FAIL|WARNING)$', description="Check status")
    details: Optional[str] = Field(None, description="Check details")
    timestamp: Optional[datetime] = Field(None, description="Check timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "check_name": "fragment_count_sufficient",
                "status": "PASS",
                "details": "1247 fragments detected, exceeds minimum of 500",
                "timestamp": "2024-01-15T10:40:00Z"
            }
        }


class ProcessingMetadata(BaseModel):
    """Processing metadata validation schema."""
    processing_timestamp: datetime = Field(..., description="Processing timestamp")
    processing_method: str = Field(..., description="Processing method (manual, automated, hybrid)")
    software_used: Optional[Dict[str, Any]] = Field(None, description="Software information")
    preprocessing_steps: Optional[List[ProcessingStep]] = Field(None, description="Preprocessing steps")
    validation_checks: Optional[List[ValidationCheck]] = Field(None, description="Validation checks")
    processing_time: Optional[float] = Field(None, gt=0, description="Processing time in seconds")
    manual_review_required: bool = Field(False, description="Manual review requirement flag")
    reviewer_notes: Optional[str] = Field(None, description="Reviewer notes")
    
    class Config:
        schema_extra = {
            "example": {
                "processing_timestamp": "2024-01-15T10:30:00Z",
                "processing_method": "automated",
                "software_used": {
                    "name": "FragmentAnalyzer",
                    "version": "2.1.0",
                    "parameters": {"detection_threshold": 0.5}
                },
                "processing_time": 45.2,
                "manual_review_required": False
            }
        }


class PredictionComparison(BaseModel):
    """Prediction comparison validation schema."""
    predicted_values: Dict[str, Any] = Field(..., description="Predicted values for comparison")
    comparison_metrics: Dict[str, float] = Field(..., description="Comparison metrics")
    model_performance: Optional[Dict[str, Any]] = Field(None, description="Model performance metrics")
    
    class Config:
        schema_extra = {
            "example": {
                "predicted_values": {
                    "p80": 180.0,
                    "p50": 95.0
                },
                "comparison_metrics": {
                    "absolute_error": 5.3,
                    "relative_error_percent": 2.9,
                    "bias": -5.3,
                    "within_tolerance": True
                },
                "model_performance": {
                    "model_version": "1.0.0",
                    "prediction_confidence": 0.85
                }
            }
        }


class MeasurementDataCreate(BaseModel):
    """Measurement data creation validation schema."""
    blast_record_id: int = Field(..., gt=0, description="Blast record ID")
    measurement_name: str = Field(..., min_length=1, max_length=200, description="Measurement name")
    measurement_type: MeasurementTypeEnum = Field(..., description="Type of measurement")
    measurement_quality: MeasurementQualityEnum = Field(..., description="Quality assessment")
    
    measurement_date: datetime = Field(..., description="Measurement date and time")
    measurement_method: str = Field(..., max_length=100, description="Measurement method")
    operator_name: Optional[str] = Field(None, max_length=100, description="Operator name")
    equipment_used: Optional[str] = Field(None, max_length=200, description="Equipment used")
    
    measurement_location: Optional[MeasurementLocation] = Field(None, description="Measurement location")
    measured_values: Dict[str, Any] = Field(..., description="Core measurement values")
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Quality metrics")
    file_references: Optional[Dict[str, Any]] = Field(None, description="File references")
    processing_metadata: Optional[ProcessingMetadata] = Field(None, description="Processing metadata")
    prediction_comparison: Optional[PredictionComparison] = Field(None, description="Prediction comparison")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    use_for_training: bool = Field(True, description="Use for training flag")
    use_for_validation: bool = Field(True, description="Use for validation flag")
    
    @field_validator('measurement_date')
    @classmethod
    def validate_measurement_date(cls, v):
        if v > datetime.utcnow():
            raise ValueError('Measurement date cannot be in the future')
        return v
    
    @model_validator(mode='after')
    def validate_measurement_values(self):
        measurement_type = self.measurement_type
        measured_values = self.measured_values or {}
        
        if measurement_type == MeasurementTypeEnum.FRAGMENTATION:
            required_fields = ['p50', 'p80']
            for field in required_fields:
                if field not in measured_values:
                    raise ValueError(f'Fragmentation measurements require {field}')
        
        elif measurement_type == MeasurementTypeEnum.PPV:
            if 'peak_ppv' not in measured_values:
                raise ValueError('PPV measurements require peak_ppv')
        
        return self
    
    class Config:
        schema_extra = {
            "example": {
                "blast_record_id": 1,
                "measurement_name": "Muckpile Fragmentation Analysis 001",
                "measurement_type": "fragmentation",
                "measurement_quality": "good",
                "measurement_date": "2024-01-16T14:30:00Z",
                "measurement_method": "image_analysis",
                "operator_name": "Alice Johnson",
                "equipment_used": "Digital camera + FragmentAnalyzer",
                "measured_values": {
                    "p10": 45.2,
                    "p50": 95.8,
                    "p80": 185.3,
                    "fragment_count": 1247
                },
                "use_for_training": True,
                "use_for_validation": True
            }
        }


class MeasurementDataUpdate(BaseModel):
    """Measurement data update validation schema."""
    measurement_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Measurement name")
    measurement_quality: Optional[MeasurementQualityEnum] = Field(None, description="Quality assessment")
    operator_name: Optional[str] = Field(None, max_length=100, description="Operator name")
    equipment_used: Optional[str] = Field(None, max_length=200, description="Equipment used")
    
    measurement_location: Optional[MeasurementLocation] = Field(None, description="Measurement location")
    measured_values: Optional[Dict[str, Any]] = Field(None, description="Core measurement values")
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Quality metrics")
    file_references: Optional[Dict[str, Any]] = Field(None, description="File references")
    processing_metadata: Optional[ProcessingMetadata] = Field(None, description="Processing metadata")
    prediction_comparison: Optional[PredictionComparison] = Field(None, description="Prediction comparison")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    is_validated: Optional[bool] = Field(None, description="Validation status")
    validated_by: Optional[str] = Field(None, max_length=100, description="Validator name")
    validation_date: Optional[datetime] = Field(None, description="Validation date")
    
    use_for_training: Optional[bool] = Field(None, description="Use for training flag")
    use_for_validation: Optional[bool] = Field(None, description="Use for validation flag")
    is_outlier: Optional[bool] = Field(None, description="Outlier flag")


class MeasurementDataResponse(BaseModel):
    """Measurement data response validation schema."""
    id: int = Field(..., description="Measurement data ID")
    blast_record_id: int = Field(..., description="Blast record ID")
    measurement_name: str = Field(..., description="Measurement name")
    measurement_type: MeasurementTypeEnum = Field(..., description="Type of measurement")
    measurement_quality: MeasurementQualityEnum = Field(..., description="Quality assessment")
    
    measurement_date: datetime = Field(..., description="Measurement date and time")
    measurement_method: str = Field(..., description="Measurement method")
    operator_name: Optional[str] = Field(None, description="Operator name")
    equipment_used: Optional[str] = Field(None, description="Equipment used")
    
    measurement_location: Optional[MeasurementLocation] = Field(None, description="Measurement location")
    measured_values: Dict[str, Any] = Field(..., description="Core measurement values")
    quality_metrics: Optional[QualityMetrics] = Field(None, description="Quality metrics")
    file_references: Optional[Dict[str, Any]] = Field(None, description="File references")
    processing_metadata: Optional[ProcessingMetadata] = Field(None, description="Processing metadata")
    prediction_comparison: Optional[PredictionComparison] = Field(None, description="Prediction comparison")
    
    notes: Optional[str] = Field(None, description="Additional notes")
    is_validated: bool = Field(..., description="Validation status")
    validated_by: Optional[str] = Field(None, description="Validator name")
    validation_date: Optional[datetime] = Field(None, description="Validation date")
    
    use_for_training: bool = Field(..., description="Use for training flag")
    use_for_validation: bool = Field(..., description="Use for validation flag")
    is_outlier: bool = Field(..., description="Outlier flag")
    
    # Computed properties
    measurement_age_days: float = Field(..., description="Age of measurement in days")
    confidence_score: Optional[float] = Field(None, description="Overall confidence score")
    is_high_quality: bool = Field(..., description="High quality flag for training")
    
    # Audit information
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "blast_record_id": 1,
                "measurement_name": "Muckpile Fragmentation Analysis 001",
                "measurement_type": "fragmentation",
                "measurement_quality": "good",
                "measurement_date": "2024-01-16T14:30:00Z",
                "measurement_method": "image_analysis",
                "is_validated": True,
                "use_for_training": True,
                "is_high_quality": True,
                "measurement_age_days": 5.2,
                "confidence_score": 0.92,
                "created_at": "2024-01-16T15:00:00Z",
                "updated_at": "2024-01-17T09:15:00Z"
            }
        }