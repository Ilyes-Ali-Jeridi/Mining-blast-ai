"""
Blast record Pydantic schemas for API validation.
Implements requirements 1.4, 1.5, 1.6 for blast plan validation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator

from .common import Coordinates, NumericRange, FileReference, AuditInfo


class BlastStatusEnum(str, Enum):
    """Blast status enumeration for validation."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXECUTED = "executed"
    MEASURED = "measured"
    ARCHIVED = "archived"


class DrillHole(BaseModel):
    """Drill hole specification validation schema."""
    hole_id: str = Field(..., description="Unique hole identifier")
    coordinates: Coordinates = Field(..., description="Hole collar coordinates")
    depth: float = Field(..., gt=0, description="Hole depth in meters")
    diameter: float = Field(..., gt=0, description="Hole diameter in mm")
    charge_kg: float = Field(..., ge=0, description="Explosive charge in kg")
    stemming_m: float = Field(..., ge=0, description="Stemming length in meters")
    delay_ms: int = Field(..., ge=0, description="Delay time in milliseconds")
    explosive_type: str = Field(..., description="Explosive type name")
    drill_rig: str = Field(..., description="Drill rig used")
    
    # Additional hole parameters
    collar_elevation: float = Field(..., description="Collar elevation in meters above sea level")
    toe_elevation: float = Field(..., description="Toe elevation in meters above sea level")
    burden: float = Field(..., gt=0, description="Burden distance in meters")
    spacing: float = Field(..., gt=0, description="Spacing distance in meters")
    subdrill: float = Field(..., ge=0, description="Subdrill below bench floor in meters")
    hole_angle: float = Field(90.0, ge=0, le=180, description="Hole angle from vertical in degrees")
    hole_azimuth: float = Field(0.0, ge=0, lt=360, description="Hole azimuth from north in degrees")
    
    @validator('toe_elevation')
    def validate_toe_elevation(cls, v, values):
        if 'collar_elevation' in values and v > values['collar_elevation']:
            raise ValueError('Toe elevation must be less than or equal to collar elevation')
        return v
    
    @validator('stemming_m')
    def validate_stemming(cls, v, values):
        if 'depth' in values and v > values['depth']:
            raise ValueError('Stemming length cannot exceed hole depth')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "hole_id": "H001",
                "coordinates": {"x": 1000.0, "y": 2000.0, "z": 200.0},
                "depth": 16.5,
                "diameter": 165.0,
                "charge_kg": 35.2,
                "stemming_m": 4.0,
                "delay_ms": 0,
                "explosive_type": "Standard ANFO",
                "drill_rig": "Atlas Copco ROC D65",
                "collar_elevation": 200.0,
                "toe_elevation": 183.5,
                "burden": 4.5,
                "spacing": 5.0,
                "subdrill": 1.5,
                "hole_angle": 90.0,
                "hole_azimuth": 0.0
            }
        }


class BlastGeometry(BaseModel):
    """Blast geometry summary validation schema."""
    total_holes: int = Field(..., ge=1, description="Total number of holes")
    total_depth: float = Field(..., gt=0, description="Total drilling depth in meters")
    blast_area: float = Field(..., gt=0, description="Blast area in m²")
    blast_volume: float = Field(..., gt=0, description="Blast volume in m³")
    rock_tonnage: float = Field(..., gt=0, description="Rock tonnage")
    average_burden: float = Field(..., gt=0, description="Average burden in meters")
    average_spacing: float = Field(..., gt=0, description="Average spacing in meters")
    hole_pattern: str = Field(..., description="Hole pattern type (rectangular, triangular, etc.)")
    
    class Config:
        schema_extra = {
            "example": {
                "total_holes": 24,
                "total_depth": 396.0,
                "blast_area": 1200.0,
                "blast_volume": 18000.0,
                "rock_tonnage": 47700.0,
                "average_burden": 4.5,
                "average_spacing": 5.0,
                "hole_pattern": "rectangular"
            }
        }


class ExplosiveSummary(BaseModel):
    """Explosive summary validation schema."""
    total_explosive: float = Field(..., gt=0, description="Total explosive weight in kg")
    powder_factor_kg_t: float = Field(..., gt=0, description="Powder factor in kg/tonne")
    powder_factor_kg_m3: float = Field(..., gt=0, description="Powder factor in kg/m³")
    explosive_types_used: List[str] = Field(..., min_items=1, description="List of explosive types used")
    total_cost: Optional[float] = Field(None, ge=0, description="Total explosive cost in $")
    max_charge_per_hole: float = Field(..., gt=0, description="Maximum charge per hole in kg")
    max_charge_per_delay: float = Field(..., gt=0, description="Maximum charge per delay in kg")
    
    class Config:
        schema_extra = {
            "example": {
                "total_explosive": 845.0,
                "powder_factor_kg_t": 0.35,
                "powder_factor_kg_m3": 0.47,
                "explosive_types_used": ["Standard ANFO"],
                "total_cost": 1267.50,
                "max_charge_per_hole": 45.2,
                "max_charge_per_delay": 180.8
            }
        }


class BlastPlan(BaseModel):
    """Complete blast plan validation schema."""
    holes: List[DrillHole] = Field(..., min_items=1, description="List of drill holes")
    blast_geometry: BlastGeometry = Field(..., description="Blast geometry summary")
    explosive_summary: ExplosiveSummary = Field(..., description="Explosive usage summary")
    
    @validator('holes')
    def validate_unique_hole_ids(cls, v):
        hole_ids = [hole.hole_id for hole in v]
        if len(hole_ids) != len(set(hole_ids)):
            raise ValueError('All hole IDs must be unique')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "holes": [
                    {
                        "hole_id": "H001",
                        "coordinates": {"x": 1000.0, "y": 2000.0, "z": 200.0},
                        "depth": 16.5,
                        "diameter": 165.0,
                        "charge_kg": 35.2,
                        "stemming_m": 4.0,
                        "delay_ms": 0,
                        "explosive_type": "Standard ANFO",
                        "drill_rig": "Atlas Copco ROC D65",
                        "collar_elevation": 200.0,
                        "toe_elevation": 183.5,
                        "burden": 4.5,
                        "spacing": 5.0,
                        "subdrill": 1.5,
                        "hole_angle": 90.0,
                        "hole_azimuth": 0.0
                    }
                ],
                "blast_geometry": {
                    "total_holes": 24,
                    "total_depth": 396.0,
                    "blast_area": 1200.0,
                    "blast_volume": 18000.0,
                    "rock_tonnage": 47700.0,
                    "average_burden": 4.5,
                    "average_spacing": 5.0,
                    "hole_pattern": "rectangular"
                },
                "explosive_summary": {
                    "total_explosive": 845.0,
                    "powder_factor_kg_t": 0.35,
                    "powder_factor_kg_m3": 0.47,
                    "explosive_types_used": ["Standard ANFO"],
                    "max_charge_per_hole": 45.2,
                    "max_charge_per_delay": 180.8
                }
            }
        }


class FragmentationPrediction(BaseModel):
    """Fragmentation prediction validation schema."""
    mean_fragment_size: float = Field(..., gt=0, description="Mean fragment size in mm")
    p10: float = Field(..., gt=0, description="P10 fragment size in mm")
    p50: float = Field(..., gt=0, description="P50 fragment size in mm")
    p80: float = Field(..., gt=0, description="P80 fragment size in mm")
    uniformity_index: float = Field(..., gt=0, description="Rosin-Rammler uniformity index")
    characteristic_size: float = Field(..., gt=0, description="Rosin-Rammler characteristic size in mm")
    distribution_type: str = Field("rosin_rammler", description="Distribution type")
    
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
                "mean_fragment_size": 125.0,
                "p10": 45.0,
                "p50": 95.0,
                "p80": 180.0,
                "uniformity_index": 1.25,
                "characteristic_size": 110.0,
                "distribution_type": "rosin_rammler"
            }
        }


class PPVPrediction(BaseModel):
    """PPV prediction for a receptor validation schema."""
    receptor_name: str = Field(..., description="Receptor name")
    coordinates: Coordinates = Field(..., description="Receptor coordinates")
    predicted_ppv: float = Field(..., ge=0, description="Predicted PPV in mm/s")
    distance_to_blast: float = Field(..., gt=0, description="Distance to blast in meters")
    dominant_frequency: Optional[float] = Field(None, gt=0, description="Dominant frequency in Hz")
    safety_margin: float = Field(..., description="Safety margin ratio to limit")
    
    class Config:
        schema_extra = {
            "example": {
                "receptor_name": "Office Building A",
                "coordinates": {"x": 1500.0, "y": 2500.0, "z": 200.0},
                "predicted_ppv": 1.8,
                "distance_to_blast": 250.0,
                "dominant_frequency": 12.5,
                "safety_margin": 0.9
            }
        }


class PredictedResults(BaseModel):
    """Predicted results validation schema."""
    fragmentation: FragmentationPrediction = Field(..., description="Fragmentation predictions")
    ppv_predictions: Dict[str, Any] = Field(..., description="PPV predictions for all receptors")
    model_metadata: Dict[str, Any] = Field(..., description="Model metadata and parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "fragmentation": {
                    "mean_fragment_size": 125.0,
                    "p10": 45.0,
                    "p50": 95.0,
                    "p80": 180.0,
                    "uniformity_index": 1.25,
                    "characteristic_size": 110.0,
                    "distribution_type": "rosin_rammler"
                },
                "ppv_predictions": {
                    "receptor_predictions": [],
                    "max_predicted_ppv": 2.1,
                    "ppv_model_parameters": {
                        "k": 1.4,
                        "a": 0.333,
                        "b": 1.6
                    }
                },
                "model_metadata": {
                    "physics_model_version": "1.0.0",
                    "prediction_timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }


class SafetyCheck(BaseModel):
    """Individual safety check validation schema."""
    check_name: str = Field(..., description="Name of the safety check")
    check_type: str = Field(..., description="Type of check (charge_limit, ppv_limit, etc.)")
    status: str = Field(..., pattern=r'^(PASS|FAIL|WARNING)$', description="Check status")
    limit_value: float = Field(..., description="Safety limit value")
    actual_value: float = Field(..., description="Actual measured/calculated value")
    safety_margin: float = Field(..., description="Safety margin (limit - actual) / limit")
    description: str = Field(..., description="Check description")
    
    class Config:
        schema_extra = {
            "example": {
                "check_name": "Maximum charge per hole",
                "check_type": "charge_limit",
                "status": "PASS",
                "limit_value": 50.0,
                "actual_value": 45.2,
                "safety_margin": 0.096,
                "description": "Charge per hole within regulatory limits"
            }
        }


class SafetyViolation(BaseModel):
    """Safety violation validation schema."""
    violation_type: str = Field(..., description="Type of violation")
    severity: str = Field(..., pattern=r'^(CRITICAL|HIGH|MEDIUM|LOW)$', description="Violation severity")
    description: str = Field(..., description="Violation description")
    suggested_mitigation: str = Field(..., description="Suggested mitigation action")
    affected_holes: Optional[List[str]] = Field(None, description="Affected hole IDs")
    
    class Config:
        schema_extra = {
            "example": {
                "violation_type": "charge_limit_exceeded",
                "severity": "HIGH",
                "description": "Hole H015 exceeds maximum charge per hole limit",
                "suggested_mitigation": "Reduce charge in hole H015 or split into multiple holes",
                "affected_holes": ["H015"]
            }
        }


class SafetyValidation(BaseModel):
    """Safety validation results validation schema."""
    validation_timestamp: datetime = Field(..., description="Validation timestamp")
    is_valid: bool = Field(..., description="Overall safety validation status")
    safety_checks: List[SafetyCheck] = Field(..., description="Individual safety checks")
    violations: Optional[List[SafetyViolation]] = Field(None, description="Safety violations if any")
    safety_config_used: Dict[str, Any] = Field(..., description="Safety configuration snapshot")
    
    class Config:
        schema_extra = {
            "example": {
                "validation_timestamp": "2024-01-15T10:30:00Z",
                "is_valid": True,
                "safety_checks": [
                    {
                        "check_name": "Maximum charge per hole",
                        "check_type": "charge_limit",
                        "status": "PASS",
                        "limit_value": 50.0,
                        "actual_value": 45.2,
                        "safety_margin": 0.096,
                        "description": "Charge per hole within regulatory limits"
                    }
                ],
                "violations": [],
                "safety_config_used": {
                    "max_charge_per_hole": 50.0,
                    "max_charge_per_delay": 200.0,
                    "ppv_default_limit": 5.0
                }
            }
        }


class EngineerSignoff(BaseModel):
    """Engineer sign-off validation schema."""
    engineer_name: str = Field(..., description="Engineer name")
    engineer_id: str = Field(..., description="Engineer ID or license number")
    signoff_timestamp: datetime = Field(..., description="Sign-off timestamp")
    certification_statement: str = Field(..., description="Legal certification statement")
    digital_signature: Optional[str] = Field(None, description="Digital signature hash")
    review_notes: Optional[str] = Field(None, description="Engineer review notes")
    conditions: Optional[List[str]] = Field(None, description="Sign-off conditions")
    is_valid: bool = Field(True, description="Sign-off validity")
    expiry_date: Optional[datetime] = Field(None, description="Sign-off expiry date")
    
    class Config:
        schema_extra = {
            "example": {
                "engineer_name": "Dr. Jane Smith, P.Eng",
                "engineer_id": "PE-12345",
                "signoff_timestamp": "2024-01-15T15:30:00Z",
                "certification_statement": "I certify that this blast plan complies with all applicable safety regulations",
                "review_notes": "Plan reviewed and approved with standard safety margins",
                "is_valid": True
            }
        }


class BlastRecordCreate(BaseModel):
    """Blast record creation validation schema."""
    site_id: int = Field(..., gt=0, description="Site ID")
    blast_name: str = Field(..., min_length=1, max_length=200, description="Blast name")
    blast_description: Optional[str] = Field(None, description="Blast description")
    planned_execution_date: Optional[datetime] = Field(None, description="Planned execution date")
    blast_operator: Optional[str] = Field(None, max_length=100, description="Blast operator")
    
    plan_data: BlastPlan = Field(..., description="Complete blast plan")
    predicted_results: PredictedResults = Field(..., description="Predicted results")
    safety_validation: SafetyValidation = Field(..., description="Safety validation results")
    engineer_signoff: Optional[EngineerSignoff] = Field(None, description="Engineer sign-off")
    
    is_template: bool = Field(False, description="Template flag")
    
    class Config:
        schema_extra = {
            "example": {
                "site_id": 1,
                "blast_name": "North Pit Blast 001",
                "blast_description": "First blast in north pit phase 2",
                "planned_execution_date": "2024-01-20T10:00:00Z",
                "blast_operator": "John Doe",
                "plan_data": {},
                "predicted_results": {},
                "safety_validation": {},
                "is_template": False
            }
        }


class BlastRecordUpdate(BaseModel):
    """Blast record update validation schema."""
    blast_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Blast name")
    blast_description: Optional[str] = Field(None, description="Blast description")
    blast_status: Optional[BlastStatusEnum] = Field(None, description="Blast status")
    planned_execution_date: Optional[datetime] = Field(None, description="Planned execution date")
    actual_execution_date: Optional[datetime] = Field(None, description="Actual execution date")
    blast_operator: Optional[str] = Field(None, max_length=100, description="Blast operator")
    
    plan_data: Optional[BlastPlan] = Field(None, description="Complete blast plan")
    predicted_results: Optional[PredictedResults] = Field(None, description="Predicted results")
    measured_results: Optional[Dict[str, Any]] = Field(None, description="Measured results")
    safety_validation: Optional[SafetyValidation] = Field(None, description="Safety validation results")
    engineer_signoff: Optional[EngineerSignoff] = Field(None, description="Engineer sign-off")
    optimization_metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")


class BlastRecordResponse(BaseModel):
    """Blast record response validation schema."""
    id: int = Field(..., description="Blast record ID")
    site_id: int = Field(..., description="Site ID")
    blast_name: str = Field(..., description="Blast name")
    blast_description: Optional[str] = Field(None, description="Blast description")
    blast_status: BlastStatusEnum = Field(..., description="Blast status")
    
    planned_execution_date: Optional[datetime] = Field(None, description="Planned execution date")
    actual_execution_date: Optional[datetime] = Field(None, description="Actual execution date")
    blast_operator: Optional[str] = Field(None, description="Blast operator")
    
    plan_data: BlastPlan = Field(..., description="Complete blast plan")
    predicted_results: PredictedResults = Field(..., description="Predicted results")
    measured_results: Optional[Dict[str, Any]] = Field(None, description="Measured results")
    safety_validation: SafetyValidation = Field(..., description="Safety validation results")
    engineer_signoff: Optional[EngineerSignoff] = Field(None, description="Engineer sign-off")
    optimization_metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")
    
    # Version control
    plan_version: int = Field(..., description="Plan version number")
    parent_blast_id: Optional[int] = Field(None, description="Parent blast ID for revisions")
    is_template: bool = Field(..., description="Template flag")
    
    # Computed properties
    total_holes: int = Field(..., description="Total number of holes")
    total_explosive: float = Field(..., description="Total explosive weight")
    powder_factor: Optional[float] = Field(None, description="Powder factor")
    predicted_p80: Optional[float] = Field(None, description="Predicted P80")
    measured_p80: Optional[float] = Field(None, description="Measured P80")
    is_signed_off: bool = Field(..., description="Engineer sign-off status")
    safety_status: str = Field(..., description="Safety validation status")
    
    # Audit information
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "site_id": 1,
                "blast_name": "North Pit Blast 001",
                "blast_status": "approved",
                "total_holes": 24,
                "total_explosive": 845.0,
                "powder_factor": 0.35,
                "predicted_p80": 180.0,
                "is_signed_off": True,
                "safety_status": "VALID",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-16T14:45:00Z"
            }
        }