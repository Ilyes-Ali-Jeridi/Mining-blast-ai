"""
Pydantic schemas for API validation and serialization.
Implements requirements 1.1-1.6 for input/output validation.
"""

from .site import (
    SiteCreate,
    SiteUpdate, 
    SiteResponse,
    BenchGeometry,
    RockProperties,
    EquipmentSpecs,
    OperationalConstraints
)

from .blast_record import (
    BlastRecordCreate,
    BlastRecordUpdate,
    BlastRecordResponse,
    BlastPlan,
    DrillHole,
    PredictedResults,
    SafetyValidation,
    EngineerSignoff
)

from .measurement_data import (
    MeasurementDataCreate,
    MeasurementDataUpdate,
    MeasurementDataResponse,
    FragmentationMeasurement,
    PPVMeasurement,
    QualityMetrics
)

from .configuration import (
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationResponse,
    PhysicsConfig,
    SafetyConfig,
    OptimizationConfig,
    ExplosivesConfig
)

from .common import (
    Coordinates,
    ValidationError,
    PaginatedResponse
)

__all__ = [
    # Site schemas
    "SiteCreate",
    "SiteUpdate", 
    "SiteResponse",
    "BenchGeometry",
    "RockProperties",
    "EquipmentSpecs",
    "OperationalConstraints",
    
    # Blast record schemas
    "BlastRecordCreate",
    "BlastRecordUpdate",
    "BlastRecordResponse",
    "BlastPlan",
    "DrillHole",
    "PredictedResults",
    "SafetyValidation",
    "EngineerSignoff",
    
    # Measurement data schemas
    "MeasurementDataCreate",
    "MeasurementDataUpdate",
    "MeasurementDataResponse",
    "FragmentationMeasurement",
    "PPVMeasurement",
    "QualityMetrics",
    
    # Configuration schemas
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationResponse",
    "PhysicsConfig",
    "SafetyConfig",
    "OptimizationConfig",
    "ExplosivesConfig",
    
    # Common schemas
    "Coordinates",
    "ValidationError",
    "PaginatedResponse"
]