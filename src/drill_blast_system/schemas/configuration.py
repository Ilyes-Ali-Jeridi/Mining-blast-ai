"""
Configuration Pydantic schemas for API validation.
Implements requirements 9.4, 9.5 for configuration management validation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, validator

from .common import NumericRange


class ConfigurationTypeEnum(str, Enum):
    """Configuration type enumeration for validation."""
    PHYSICS = "physics"
    SAFETY = "safety"
    OPTIMIZATION = "optimization"
    EXPLOSIVES = "explosives"
    EQUIPMENT = "equipment"
    SYSTEM = "system"
    USER = "user"
    SITE_SPECIFIC = "site_specific"


class ConfigurationScopeEnum(str, Enum):
    """Configuration scope enumeration for validation."""
    GLOBAL = "global"
    SITE = "site"
    USER = "user"
    SESSION = "session"


class KuzRamParameters(BaseModel):
    """Kuz-Ram model parameters validation schema."""
    rock_factor_a: float = Field(7.0, gt=0, description="Rock factor A parameter")
    uniformity_index: float = Field(1.25, gt=0, description="Uniformity index parameter")
    calibration_data: Optional[List[Dict[str, Any]]] = Field(None, description="Calibration data points")
    
    class Config:
        schema_extra = {
            "example": {
                "rock_factor_a": 7.0,
                "uniformity_index": 1.25,
                "calibration_data": [
                    {
                        "site_name": "North Pit",
                        "rock_type": "granite",
                        "calibrated_a": 6.8,
                        "validation_r2": 0.92
                    }
                ]
            }
        }


class PPVParameters(BaseModel):
    """PPV model parameters validation schema."""
    k: float = Field(1.4, gt=0, description="PPV constant K")
    a: float = Field(0.333, gt=0, description="PPV exponent A")
    b: float = Field(1.6, gt=0, description="PPV exponent B")
    site_specific_constants: Optional[Dict[str, Dict[str, float]]] = Field(None, description="Site-specific overrides")
    
    class Config:
        schema_extra = {
            "example": {
                "k": 1.4,
                "a": 0.333,
                "b": 1.6,
                "site_specific_constants": {
                    "site_1": {"k": 1.2, "a": 0.35, "b": 1.55}
                }
            }
        }


class FragmentationCurves(BaseModel):
    """Fragmentation curve parameters validation schema."""
    default_distribution: str = Field("rosin_rammler", description="Default distribution type")
    rosin_rammler: Optional[Dict[str, float]] = Field(None, description="Rosin-Rammler parameters")
    swebrec: Optional[Dict[str, float]] = Field(None, description="Swebrec parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "default_distribution": "rosin_rammler",
                "rosin_rammler": {
                    "default_n": 1.25
                },
                "swebrec": {
                    "default_b": 1.5,
                    "default_x0": 50.0
                }
            }
        }


class PhysicsConfig(BaseModel):
    """Physics configuration validation schema."""
    kuz_ram: KuzRamParameters = Field(..., description="Kuz-Ram model parameters")
    ppv: PPVParameters = Field(..., description="PPV model parameters")
    fragmentation_curves: Optional[FragmentationCurves] = Field(None, description="Fragmentation curve parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "kuz_ram": {
                    "rock_factor_a": 7.0,
                    "uniformity_index": 1.25
                },
                "ppv": {
                    "k": 1.4,
                    "a": 0.333,
                    "b": 1.6
                },
                "fragmentation_curves": {
                    "default_distribution": "rosin_rammler",
                    "rosin_rammler": {"default_n": 1.25}
                }
            }
        }


class ChargeLimits(BaseModel):
    """Charge limits validation schema."""
    max_charge_per_hole: float = Field(..., gt=0, description="Maximum charge per hole in kg")
    max_charge_per_delay: float = Field(..., gt=0, description="Maximum charge per delay in kg")
    safety_factor: float = Field(1.0, gt=0, description="Additional safety factor")
    
    @validator('max_charge_per_delay')
    def validate_delay_limit(cls, v, values):
        if 'max_charge_per_hole' in values and v < values['max_charge_per_hole']:
            raise ValueError('max_charge_per_delay must be >= max_charge_per_hole')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "max_charge_per_hole": 50.0,
                "max_charge_per_delay": 200.0,
                "safety_factor": 1.0
            }
        }


class PowderFactorLimits(BaseModel):
    """Powder factor limits validation schema."""
    min_powder_factor: float = Field(..., gt=0, description="Minimum powder factor in kg/t")
    max_powder_factor: float = Field(..., gt=0, description="Maximum powder factor in kg/t")
    recommended_range: Optional[List[float]] = Field(None, description="Recommended range [min, max]")
    
    @validator('max_powder_factor')
    def validate_powder_factor_range(cls, v, values):
        if 'min_powder_factor' in values and v <= values['min_powder_factor']:
            raise ValueError('max_powder_factor must be greater than min_powder_factor')
        return v
    
    @validator('recommended_range')
    def validate_recommended_range(cls, v, values):
        if v and len(v) != 2:
            raise ValueError('recommended_range must have exactly 2 values [min, max]')
        if v and v[0] >= v[1]:
            raise ValueError('recommended_range min must be less than max')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "min_powder_factor": 0.05,
                "max_powder_factor": 1.5,
                "recommended_range": [0.2, 0.8]
            }
        }


class PPVLimits(BaseModel):
    """PPV limits validation schema."""
    default_limit: float = Field(..., gt=0, description="Default PPV limit in mm/s")
    structure_limits: Optional[Dict[str, float]] = Field(None, description="Structure-specific limits")
    
    @validator('structure_limits')
    def validate_structure_limits(cls, v):
        if v:
            for limit_value in v.values():
                if limit_value <= 0:
                    raise ValueError('All structure limits must be positive')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "default_limit": 5.0,
                "structure_limits": {
                    "residential": 2.0,
                    "commercial": 5.0,
                    "industrial": 10.0,
                    "sensitive": 1.0
                }
            }
        }


class DistanceLimits(BaseModel):
    """Distance limits validation schema."""
    min_distance_to_structures: float = Field(..., gt=0, description="Minimum distance to structures in meters")
    min_distance_to_roads: float = Field(..., gt=0, description="Minimum distance to roads in meters")
    exclusion_zone_buffer: float = Field(..., gt=0, description="Exclusion zone buffer in meters")
    
    class Config:
        schema_extra = {
            "example": {
                "min_distance_to_structures": 100.0,
                "min_distance_to_roads": 50.0,
                "exclusion_zone_buffer": 25.0
            }
        }


class RegulatoryCompliance(BaseModel):
    """Regulatory compliance validation schema."""
    jurisdiction: str = Field(..., description="Regulatory jurisdiction")
    regulation_reference: str = Field(..., description="Legal regulation reference")
    last_updated: str = Field(..., description="Last update date (ISO format)")
    compliance_notes: Optional[str] = Field(None, description="Compliance notes")
    
    class Config:
        schema_extra = {
            "example": {
                "jurisdiction": "Australia - NSW",
                "regulation_reference": "Work Health and Safety Regulation 2017",
                "last_updated": "2024-01-01",
                "compliance_notes": "Updated for latest safety standards"
            }
        }


class SafetyConfig(BaseModel):
    """Safety configuration validation schema."""
    charge_limits: ChargeLimits = Field(..., description="Charge limits")
    powder_factor_limits: PowderFactorLimits = Field(..., description="Powder factor limits")
    ppv_limits: PPVLimits = Field(..., description="PPV limits")
    distance_limits: DistanceLimits = Field(..., description="Distance limits")
    regulatory_compliance: Optional[RegulatoryCompliance] = Field(None, description="Regulatory compliance info")
    
    class Config:
        schema_extra = {
            "example": {
                "charge_limits": {
                    "max_charge_per_hole": 50.0,
                    "max_charge_per_delay": 200.0,
                    "safety_factor": 1.0
                },
                "powder_factor_limits": {
                    "min_powder_factor": 0.05,
                    "max_powder_factor": 1.5
                },
                "ppv_limits": {
                    "default_limit": 5.0
                },
                "distance_limits": {
                    "min_distance_to_structures": 100.0,
                    "min_distance_to_roads": 50.0,
                    "exclusion_zone_buffer": 25.0
                }
            }
        }


class AlgorithmPreferences(BaseModel):
    """Algorithm preferences validation schema."""
    cp_sat: Optional[Dict[str, Any]] = Field(None, description="CP-SAT solver preferences")
    scipy: Optional[Dict[str, Any]] = Field(None, description="SciPy optimizer preferences")
    genetic: Optional[Dict[str, Any]] = Field(None, description="Genetic algorithm preferences")
    
    class Config:
        schema_extra = {
            "example": {
                "cp_sat": {
                    "max_time_seconds": 300,
                    "num_search_workers": 4,
                    "log_search_progress": False
                },
                "scipy": {
                    "method": "differential_evolution",
                    "max_iterations": 1000,
                    "tolerance": 1e-6,
                    "polish": True
                },
                "genetic": {
                    "population_size": 50,
                    "num_generations": 100,
                    "mutation_rate": 0.1,
                    "crossover_rate": 0.8
                }
            }
        }


class ObjectiveWeights(BaseModel):
    """Objective weights validation schema."""
    fragmentation: float = Field(..., ge=0, description="Fragmentation objective weight")
    cost: float = Field(..., ge=0, description="Cost objective weight")
    ppv: float = Field(..., ge=0, description="PPV objective weight")
    uniformity: float = Field(..., ge=0, description="Pattern uniformity weight")
    
    class Config:
        schema_extra = {
            "example": {
                "fragmentation": 1.0,
                "cost": 0.5,
                "ppv": 2.0,
                "uniformity": 0.3
            }
        }


class ConvergenceCriteria(BaseModel):
    """Convergence criteria validation schema."""
    max_runtime_seconds: int = Field(..., gt=0, description="Maximum runtime in seconds")
    objective_tolerance: float = Field(..., gt=0, description="Objective tolerance")
    stagnation_generations: int = Field(..., gt=0, description="Stagnation generations limit")
    
    class Config:
        schema_extra = {
            "example": {
                "max_runtime_seconds": 600,
                "objective_tolerance": 0.001,
                "stagnation_generations": 20
            }
        }


class DefaultBounds(BaseModel):
    """Default parameter bounds validation schema."""
    burden_range: List[float] = Field(..., description="Burden range [min, max] in meters")
    spacing_range: List[float] = Field(..., description="Spacing range [min, max] in meters")
    charge_range: List[float] = Field(..., description="Charge range [min, max] in kg")
    delay_range: List[int] = Field(..., description="Delay range [min, max] in milliseconds")
    
    @validator('burden_range', 'spacing_range', 'charge_range')
    def validate_float_ranges(cls, v):
        if len(v) != 2:
            raise ValueError('Range must have exactly 2 values [min, max]')
        if v[0] >= v[1]:
            raise ValueError('Range minimum must be less than maximum')
        if v[0] <= 0:
            raise ValueError('Range values must be positive')
        return v
    
    @validator('delay_range')
    def validate_delay_range(cls, v):
        if len(v) != 2:
            raise ValueError('Delay range must have exactly 2 values [min, max]')
        if v[0] >= v[1]:
            raise ValueError('Delay range minimum must be less than maximum')
        if v[0] < 0:
            raise ValueError('Delay range values must be non-negative')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "burden_range": [2.0, 8.0],
                "spacing_range": [2.0, 8.0],
                "charge_range": [5.0, 50.0],
                "delay_range": [0, 1000]
            }
        }


class OptimizationConfig(BaseModel):
    """Optimization configuration validation schema."""
    algorithms: Dict[str, Any] = Field(..., description="Algorithm settings")
    objectives: Dict[str, Any] = Field(..., description="Objective settings")
    constraints: Dict[str, Any] = Field(..., description="Constraint settings")
    
    class Config:
        schema_extra = {
            "example": {
                "algorithms": {
                    "default_algorithm": "cp_sat",
                    "algorithm_preferences": {
                        "cp_sat": {
                            "max_time_seconds": 300,
                            "num_search_workers": 4
                        }
                    }
                },
                "objectives": {
                    "default_weights": {
                        "fragmentation": 1.0,
                        "cost": 0.5,
                        "ppv": 2.0,
                        "uniformity": 0.3
                    }
                },
                "constraints": {
                    "default_bounds": {
                        "burden_range": [2.0, 8.0],
                        "spacing_range": [2.0, 8.0],
                        "charge_range": [5.0, 50.0],
                        "delay_range": [0, 1000]
                    }
                }
            }
        }


class ExplosiveSpec(BaseModel):
    """Explosive specification validation schema."""
    id: str = Field(..., description="Explosive identifier")
    name: str = Field(..., description="Explosive name")
    manufacturer: str = Field(..., description="Manufacturer name")
    type: str = Field(..., description="Explosive type")
    density: float = Field(..., gt=0, description="Density in kg/m³")
    rws: float = Field(..., gt=0, description="Relative Weight Strength (%)")
    vod: float = Field(..., gt=0, description="Velocity of Detonation in m/s")
    energy: float = Field(..., gt=0, description="Energy content in MJ/kg")
    cost_per_kg: float = Field(..., ge=0, description="Cost per kg in $")
    
    availability: Optional[Dict[str, Any]] = Field(None, description="Availability information")
    regulatory: Optional[Dict[str, Any]] = Field(None, description="Regulatory information")
    performance: Optional[Dict[str, Any]] = Field(None, description="Performance characteristics")
    is_active: bool = Field(True, description="Active status")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "anfo_standard",
                "name": "Standard ANFO",
                "manufacturer": "Generic",
                "type": "ANFO",
                "density": 850.0,
                "rws": 100.0,
                "vod": 4500.0,
                "energy": 3.7,
                "cost_per_kg": 1.50,
                "availability": {
                    "regions": ["global"],
                    "lead_time_days": 7,
                    "minimum_order": 1000.0
                },
                "regulatory": {
                    "max_per_hole": 50.0,
                    "max_per_delay": 200.0,
                    "storage_class": "1.1D"
                },
                "is_active": True
            }
        }


class ExplosivesConfig(BaseModel):
    """Explosives configuration validation schema."""
    catalog: List[ExplosiveSpec] = Field(..., min_items=1, description="Explosives catalog")
    default_selections: Optional[Dict[str, str]] = Field(None, description="Default explosive selections")
    
    @validator('catalog')
    def validate_unique_explosive_ids(cls, v):
        explosive_ids = [exp.id for exp in v]
        if len(explosive_ids) != len(set(explosive_ids)):
            raise ValueError('All explosive IDs must be unique')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "catalog": [
                    {
                        "id": "anfo_standard",
                        "name": "Standard ANFO",
                        "manufacturer": "Generic",
                        "type": "ANFO",
                        "density": 850.0,
                        "rws": 100.0,
                        "vod": 4500.0,
                        "energy": 3.7,
                        "cost_per_kg": 1.50,
                        "is_active": True
                    }
                ],
                "default_selections": {
                    "primary_explosive": "anfo_standard",
                    "stemming_material": "drill_cuttings"
                }
            }
        }


class ConfigurationCreate(BaseModel):
    """Configuration creation validation schema."""
    config_key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    config_name: str = Field(..., min_length=1, max_length=200, description="Configuration name")
    config_description: Optional[str] = Field(None, description="Configuration description")
    config_type: ConfigurationTypeEnum = Field(..., description="Configuration type")
    config_scope: ConfigurationScopeEnum = Field(ConfigurationScopeEnum.GLOBAL, description="Configuration scope")
    
    site_id: Optional[int] = Field(None, description="Site ID for site-specific configs")
    user_id: Optional[str] = Field(None, max_length=100, description="User ID for user-specific configs")
    
    config_value: Dict[str, Any] = Field(..., description="Configuration value")
    
    is_default: bool = Field(False, description="Default configuration flag")
    created_by: Optional[str] = Field(None, max_length=100, description="Creator user ID")
    change_reason: Optional[str] = Field(None, description="Reason for creating this configuration")
    
    tags: Optional[List[str]] = Field(None, description="Configuration tags")
    dependencies: Optional[List[str]] = Field(None, description="Dependent configuration keys")
    
    @model_validator(mode='after')
    def validate_scope_requirements(self):
        config_scope = self.config_scope
        site_id = values.get('site_id')
        user_id = values.get('user_id')
        
        if config_scope == ConfigurationScopeEnum.SITE and not site_id:
            raise ValueError('site_id required for site-scoped configurations')
        if config_scope == ConfigurationScopeEnum.USER and not user_id:
            raise ValueError('user_id required for user-scoped configurations')
        if config_scope == ConfigurationScopeEnum.GLOBAL and (site_id or user_id):
            raise ValueError('site_id and user_id must be null for global configurations')
            
        return self
    
    class Config:
        schema_extra = {
            "example": {
                "config_key": "custom_physics_parameters",
                "config_name": "Custom Physics Parameters",
                "config_description": "Site-specific physics model parameters",
                "config_type": "physics",
                "config_scope": "site",
                "site_id": 1,
                "config_value": {
                    "kuz_ram": {
                        "rock_factor_a": 6.8,
                        "uniformity_index": 1.3
                    }
                },
                "created_by": "engineer@company.com",
                "change_reason": "Calibrated for local rock conditions"
            }
        }


class ConfigurationUpdate(BaseModel):
    """Configuration update validation schema."""
    config_name: Optional[str] = Field(None, min_length=1, max_length=200, description="Configuration name")
    config_description: Optional[str] = Field(None, description="Configuration description")
    config_value: Optional[Dict[str, Any]] = Field(None, description="Configuration value")
    
    is_active: Optional[bool] = Field(None, description="Active status")
    is_default: Optional[bool] = Field(None, description="Default configuration flag")
    
    modified_by: Optional[str] = Field(None, max_length=100, description="Modifier user ID")
    change_reason: Optional[str] = Field(None, description="Reason for this change")
    
    tags: Optional[List[str]] = Field(None, description="Configuration tags")
    dependencies: Optional[List[str]] = Field(None, description="Dependent configuration keys")


class ConfigurationResponse(BaseModel):
    """Configuration response validation schema."""
    id: int = Field(..., description="Configuration ID")
    config_key: str = Field(..., description="Configuration key")
    config_name: str = Field(..., description="Configuration name")
    config_description: Optional[str] = Field(None, description="Configuration description")
    config_type: ConfigurationTypeEnum = Field(..., description="Configuration type")
    config_scope: ConfigurationScopeEnum = Field(..., description="Configuration scope")
    
    site_id: Optional[int] = Field(None, description="Site ID for site-specific configs")
    user_id: Optional[str] = Field(None, description="User ID for user-specific configs")
    
    config_value: Dict[str, Any] = Field(..., description="Configuration value")
    
    version: int = Field(..., description="Configuration version")
    parent_config_id: Optional[int] = Field(None, description="Parent configuration ID")
    is_active: bool = Field(..., description="Active status")
    is_default: bool = Field(..., description="Default configuration flag")
    
    is_validated: bool = Field(..., description="Validation status")
    validated_by: Optional[str] = Field(None, description="Validator user ID")
    validation_date: Optional[datetime] = Field(None, description="Validation date")
    validation_notes: Optional[str] = Field(None, description="Validation notes")
    
    created_by: Optional[str] = Field(None, description="Creator user ID")
    modified_by: Optional[str] = Field(None, description="Last modifier user ID")
    change_reason: Optional[str] = Field(None, description="Reason for last change")
    
    tags: Optional[List[str]] = Field(None, description="Configuration tags")
    dependencies: Optional[List[str]] = Field(None, description="Dependent configuration keys")
    
    # Computed properties
    full_key: str = Field(..., description="Full configuration key including scope")
    is_site_specific: bool = Field(..., description="Site-specific flag")
    is_user_specific: bool = Field(..., description="User-specific flag")
    
    # Audit information
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "config_key": "default_physics_parameters",
                "config_name": "Default Physics Parameters",
                "config_type": "physics",
                "config_scope": "global",
                "version": 1,
                "is_active": True,
                "is_default": True,
                "is_validated": True,
                "full_key": "default_physics_parameters",
                "is_site_specific": False,
                "is_user_specific": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-16T14:45:00Z"
            }
        }