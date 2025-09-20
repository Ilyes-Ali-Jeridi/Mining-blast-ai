"""
Site-related Pydantic schemas for API validation.
Implements requirements 1.1, 1.2, 1.3 for site data validation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from .common import Coordinates, Coordinates2D, GeographicCoordinates, NumericRange, AuditInfo


class BenchGeometry(BaseModel):
    """Bench geometry validation schema."""
    bench_top_elevation: float = Field(..., description="Bench top elevation in meters above sea level")
    bench_bottom_elevation: float = Field(..., description="Bench bottom elevation in meters above sea level")
    bench_width: float = Field(..., gt=0, description="Bench width in meters")
    bench_length: float = Field(..., gt=0, description="Bench length in meters")
    free_face_orientation: float = Field(..., ge=0, lt=360, description="Free face orientation in degrees from north")
    bench_angle: Optional[float] = Field(None, ge=0, le=90, description="Bench angle in degrees from horizontal")
    
    # Optional 3D mesh points for complex topography
    topography_mesh: Optional[List[Coordinates]] = Field(None, description="3D mesh points for topography")
    
    # Exclusion zones where drilling is prohibited
    exclusion_zones: Optional[List[Dict[str, Any]]] = Field(None, description="Areas where drilling is prohibited")
    
    @field_validator('bench_bottom_elevation')
    @classmethod
    def validate_elevations(cls, v, info):
        if info.data and 'bench_top_elevation' in info.data and v >= info.data['bench_top_elevation']:
            raise ValueError('Bench bottom elevation must be less than top elevation')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "bench_top_elevation": 200.0,
                "bench_bottom_elevation": 185.0,
                "bench_width": 50.0,
                "bench_length": 100.0,
                "free_face_orientation": 45.0,
                "bench_angle": 70.0,
                "exclusion_zones": [
                    {
                        "name": "Power line corridor",
                        "polygon": [
                            {"x": 1000, "y": 2000},
                            {"x": 1100, "y": 2000},
                            {"x": 1100, "y": 2100},
                            {"x": 1000, "y": 2100}
                        ],
                        "reason": "High voltage power lines overhead"
                    }
                ]
            }
        }


class UniformRockProperties(BaseModel):
    """Uniform rock properties validation schema."""
    rock_type: str = Field(..., description="Rock type identifier")
    ucs: float = Field(..., gt=0, description="Unconfined Compressive Strength in MPa")
    density: float = Field(..., gt=0, description="Rock density in kg/m³")
    rock_factor_a: float = Field(7.0, gt=0, description="Kuz-Ram rock factor A parameter")
    grade: Optional[float] = Field(None, ge=0, description="Ore grade (optional)")
    
    class Config:
        schema_extra = {
            "example": {
                "rock_type": "granite",
                "ucs": 150.0,
                "density": 2650.0,
                "rock_factor_a": 7.0,
                "grade": 2.5
            }
        }


class BlockModelCell(BaseModel):
    """Block model cell validation schema."""
    x: float = Field(..., description="Cell center X coordinate")
    y: float = Field(..., description="Cell center Y coordinate")
    z: float = Field(..., description="Cell center Z coordinate")
    rock_type: str = Field(..., description="Rock type identifier")
    ucs: float = Field(..., gt=0, description="Unconfined Compressive Strength in MPa")
    density: float = Field(..., gt=0, description="Rock density in kg/m³")
    rock_factor_a: float = Field(7.0, gt=0, description="Kuz-Ram rock factor A parameter")
    grade: Optional[float] = Field(None, ge=0, description="Ore grade (optional)")


class RockProperties(BaseModel):
    """Rock properties validation schema."""
    is_uniform: bool = Field(..., description="True for uniform properties, False for block model")
    uniform_properties: Optional[UniformRockProperties] = Field(None, description="Uniform rock properties")
    block_model: Optional[List[BlockModelCell]] = Field(None, description="Block model cells")
    rock_type_definitions: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Rock type definitions")
    
    @model_validator(mode='after')
    def validate_rock_data(self):
        is_uniform = self.is_uniform
        uniform_props = self.uniform_properties
        block_model = self.block_model
        
        if is_uniform and not uniform_props:
            raise ValueError('uniform_properties required when is_uniform=True')
        if not is_uniform and not block_model:
            raise ValueError('block_model required when is_uniform=False')
        if is_uniform and block_model:
            raise ValueError('Cannot specify both uniform_properties and block_model')
            
        return self
    
    class Config:
        schema_extra = {
            "example": {
                "is_uniform": True,
                "uniform_properties": {
                    "rock_type": "granite",
                    "ucs": 150.0,
                    "density": 2650.0,
                    "rock_factor_a": 7.0
                }
            }
        }


class DrillRig(BaseModel):
    """Drill rig specification validation schema."""
    name: str = Field(..., description="Drill rig name/identifier")
    max_hole_diameter: float = Field(..., gt=0, description="Maximum hole diameter in mm")
    max_depth: float = Field(..., gt=0, description="Maximum drilling depth in meters")
    collar_accuracy: float = Field(..., gt=0, description="Collar positioning accuracy in meters")
    drilling_rate: float = Field(..., gt=0, description="Drilling rate in m/hr")
    setup_time: float = Field(..., ge=0, description="Setup time in minutes")
    operating_cost: float = Field(..., ge=0, description="Operating cost in $/hour")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Atlas Copco ROC D65",
                "max_hole_diameter": 165.0,
                "max_depth": 20.0,
                "collar_accuracy": 0.1,
                "drilling_rate": 25.0,
                "setup_time": 15.0,
                "operating_cost": 150.0
            }
        }


class Explosive(BaseModel):
    """Explosive specification validation schema."""
    name: str = Field(..., description="Explosive name")
    type: str = Field(..., description="Explosive type (ANFO, Emulsion, etc.)")
    density: float = Field(..., gt=0, description="Density in kg/m³")
    rws: float = Field(..., gt=0, description="Relative Weight Strength (%)")
    vod: float = Field(..., gt=0, description="Velocity of Detonation in m/s")
    energy: float = Field(..., gt=0, description="Energy content in MJ/kg")
    cost_per_kg: float = Field(..., ge=0, description="Cost per kg in $")
    regulatory_limit_per_hole: float = Field(..., gt=0, description="Regulatory limit per hole in kg")
    regulatory_limit_per_delay: float = Field(..., gt=0, description="Regulatory limit per delay in kg")
    is_available: bool = Field(True, description="Availability status")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Standard ANFO",
                "type": "ANFO",
                "density": 850.0,
                "rws": 100.0,
                "vod": 4500.0,
                "energy": 3.7,
                "cost_per_kg": 1.50,
                "regulatory_limit_per_hole": 50.0,
                "regulatory_limit_per_delay": 200.0,
                "is_available": True
            }
        }


class EquipmentSpecs(BaseModel):
    """Equipment specifications validation schema."""
    drill_rigs: List[DrillRig] = Field(..., min_items=1, description="Available drill rigs")
    explosives_catalog: List[Explosive] = Field(..., min_items=1, description="Available explosives")
    
    class Config:
        schema_extra = {
            "example": {
                "drill_rigs": [
                    {
                        "name": "Atlas Copco ROC D65",
                        "max_hole_diameter": 165.0,
                        "max_depth": 20.0,
                        "collar_accuracy": 0.1,
                        "drilling_rate": 25.0,
                        "setup_time": 15.0,
                        "operating_cost": 150.0
                    }
                ],
                "explosives_catalog": [
                    {
                        "name": "Standard ANFO",
                        "type": "ANFO",
                        "density": 850.0,
                        "rws": 100.0,
                        "vod": 4500.0,
                        "energy": 3.7,
                        "cost_per_kg": 1.50,
                        "regulatory_limit_per_hole": 50.0,
                        "regulatory_limit_per_delay": 200.0,
                        "is_available": True
                    }
                ]
            }
        }


class SensitiveReceptor(BaseModel):
    """Sensitive receptor validation schema."""
    name: str = Field(..., description="Receptor name/identifier")
    coordinates: Coordinates = Field(..., description="Receptor coordinates")
    ppv_limit: float = Field(..., gt=0, description="PPV limit in mm/s")
    frequency_limit: Optional[float] = Field(None, gt=0, description="Frequency limit in Hz")
    receptor_type: str = Field(..., description="Type of receptor (building, equipment, etc.)")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Office Building A",
                "coordinates": {"x": 1500.0, "y": 2500.0, "z": 200.0},
                "ppv_limit": 2.0,
                "frequency_limit": 10.0,
                "receptor_type": "building"
            }
        }


class BlastWindow(BaseModel):
    """Blast time window validation schema."""
    day_of_week: str = Field(..., description="Day of week (monday, tuesday, etc.)")
    start_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="Start time in HH:MM format")
    end_time: str = Field(..., pattern=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', description="End time in HH:MM format")
    
    class Config:
        schema_extra = {
            "example": {
                "day_of_week": "monday",
                "start_time": "10:00",
                "end_time": "15:00"
            }
        }


class OperationalConstraints(BaseModel):
    """Operational constraints validation schema."""
    drilling_constraints: Dict[str, float] = Field(..., description="Drilling parameter constraints")
    powder_factor_limits: Dict[str, float] = Field(..., description="Powder factor limits")
    sensitive_receptors: Optional[List[SensitiveReceptor]] = Field(None, description="Sensitive receptors")
    time_constraints: Optional[Dict[str, Any]] = Field(None, description="Time and weather constraints")
    
    @field_validator('drilling_constraints')
    @classmethod
    def validate_drilling_constraints(cls, v):
        required_keys = ['min_burden', 'max_burden', 'min_spacing', 'max_spacing']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Missing required drilling constraint: {key}')
            if v[key] <= 0:
                raise ValueError(f'Drilling constraint {key} must be positive')
        
        # Validate min < max relationships
        if v['min_burden'] >= v['max_burden']:
            raise ValueError('min_burden must be less than max_burden')
        if v['min_spacing'] >= v['max_spacing']:
            raise ValueError('min_spacing must be less than max_spacing')
            
        return v
    
    @field_validator('powder_factor_limits')
    @classmethod
    def validate_powder_factor_limits(cls, v):
        required_keys = ['min_powder_factor', 'max_powder_factor']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'Missing required powder factor limit: {key}')
            if v[key] <= 0:
                raise ValueError(f'Powder factor limit {key} must be positive')
        
        if v['min_powder_factor'] >= v['max_powder_factor']:
            raise ValueError('min_powder_factor must be less than max_powder_factor')
            
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "drilling_constraints": {
                    "min_burden": 2.0,
                    "max_burden": 8.0,
                    "min_spacing": 2.0,
                    "max_spacing": 8.0,
                    "min_hole_diameter": 100.0,
                    "max_hole_diameter": 200.0
                },
                "powder_factor_limits": {
                    "min_powder_factor": 0.1,
                    "max_powder_factor": 1.0,
                    "target_powder_factor": 0.4
                },
                "sensitive_receptors": [
                    {
                        "name": "Office Building A",
                        "coordinates": {"x": 1500.0, "y": 2500.0, "z": 200.0},
                        "ppv_limit": 2.0,
                        "receptor_type": "building"
                    }
                ]
            }
        }


class SiteCreate(BaseModel):
    """Site creation validation schema."""
    name: str = Field(..., min_length=1, max_length=200, description="Site name")
    description: Optional[str] = Field(None, description="Site description")
    location: Optional[str] = Field(None, max_length=500, description="Human-readable location")
    coordinates: Optional[GeographicCoordinates] = Field(None, description="Geographic coordinates")
    site_type: str = Field("open_pit", description="Site type (open_pit, underground, quarry)")
    regulatory_zone: Optional[str] = Field(None, max_length=100, description="Regulatory zone")
    
    bench_geometry: BenchGeometry = Field(..., description="Bench geometry data")
    rock_properties: RockProperties = Field(..., description="Rock properties data")
    equipment_specs: EquipmentSpecs = Field(..., description="Equipment specifications")
    operational_constraints: OperationalConstraints = Field(..., description="Operational constraints")
    safety_config: Optional[Dict[str, Any]] = Field(None, description="Site-specific safety configuration")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "North Pit Phase 2",
                "description": "Second phase of north pit development",
                "location": "Mine Site A, Sector 7",
                "coordinates": {
                    "latitude": -33.8688,
                    "longitude": 151.2093
                },
                "site_type": "open_pit",
                "bench_geometry": {
                    "bench_top_elevation": 200.0,
                    "bench_bottom_elevation": 185.0,
                    "bench_width": 50.0,
                    "bench_length": 100.0,
                    "free_face_orientation": 45.0
                },
                "rock_properties": {
                    "is_uniform": True,
                    "uniform_properties": {
                        "rock_type": "granite",
                        "ucs": 150.0,
                        "density": 2650.0,
                        "rock_factor_a": 7.0
                    }
                },
                "equipment_specs": {
                    "drill_rigs": [],
                    "explosives_catalog": []
                },
                "operational_constraints": {
                    "drilling_constraints": {
                        "min_burden": 2.0,
                        "max_burden": 8.0,
                        "min_spacing": 2.0,
                        "max_spacing": 8.0
                    },
                    "powder_factor_limits": {
                        "min_powder_factor": 0.1,
                        "max_powder_factor": 1.0
                    }
                }
            }
        }


class SiteUpdate(BaseModel):
    """Site update validation schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Site name")
    description: Optional[str] = Field(None, description="Site description")
    location: Optional[str] = Field(None, max_length=500, description="Human-readable location")
    coordinates: Optional[GeographicCoordinates] = Field(None, description="Geographic coordinates")
    is_active: Optional[bool] = Field(None, description="Site active status")
    regulatory_zone: Optional[str] = Field(None, max_length=100, description="Regulatory zone")
    
    bench_geometry: Optional[BenchGeometry] = Field(None, description="Bench geometry data")
    rock_properties: Optional[RockProperties] = Field(None, description="Rock properties data")
    equipment_specs: Optional[EquipmentSpecs] = Field(None, description="Equipment specifications")
    operational_constraints: Optional[OperationalConstraints] = Field(None, description="Operational constraints")
    safety_config: Optional[Dict[str, Any]] = Field(None, description="Site-specific safety configuration")


class SiteResponse(BaseModel):
    """Site response validation schema."""
    id: int = Field(..., description="Site ID")
    name: str = Field(..., description="Site name")
    description: Optional[str] = Field(None, description="Site description")
    location: Optional[str] = Field(None, description="Human-readable location")
    coordinates: Optional[GeographicCoordinates] = Field(None, description="Geographic coordinates")
    
    is_active: bool = Field(..., description="Site active status")
    site_type: str = Field(..., description="Site type")
    regulatory_zone: Optional[str] = Field(None, description="Regulatory zone")
    
    bench_geometry: BenchGeometry = Field(..., description="Bench geometry data")
    rock_properties: RockProperties = Field(..., description="Rock properties data")
    equipment_specs: EquipmentSpecs = Field(..., description="Equipment specifications")
    operational_constraints: OperationalConstraints = Field(..., description="Operational constraints")
    safety_config: Optional[Dict[str, Any]] = Field(None, description="Site-specific safety configuration")
    
    # Computed properties
    bench_height: Optional[float] = Field(None, description="Calculated bench height")
    bench_area: Optional[float] = Field(None, description="Calculated bench area")
    bench_volume: Optional[float] = Field(None, description="Calculated bench volume")
    
    # Audit information
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "North Pit Phase 2",
                "description": "Second phase of north pit development",
                "location": "Mine Site A, Sector 7",
                "is_active": True,
                "site_type": "open_pit",
                "bench_height": 15.0,
                "bench_area": 5000.0,
                "bench_volume": 75000.0,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-16T14:45:00Z"
            }
        }