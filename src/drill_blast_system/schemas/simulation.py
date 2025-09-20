"""
Pydantic schemas for simulation API endpoints
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class SimulationType(str, Enum):
    """Available simulation types"""
    PHYSICS_ONLY = "physics_only"
    BLASTFOAM = "blastfoam"
    YADE = "yade"


class SimulationStatus(str, Enum):
    """Simulation job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BlastFoamConfigSchema(BaseModel):
    """Configuration for blastFoam simulation"""
    enabled: bool = True
    mesh_resolution: float = Field(default=1.0, ge=0.1, le=10.0, description="Mesh resolution in meters")
    simulation_time: float = Field(default=0.05, ge=0.001, le=1.0, description="Simulation time in seconds")
    time_step: float = Field(default=1e-6, ge=1e-8, le=1e-3, description="Time step in seconds")
    parallel_processes: int = Field(default=1, ge=1, le=16, description="Number of parallel processes")
    explosive_density: float = Field(default=1200.0, ge=800.0, le=2000.0, description="Explosive density in kg/m³")
    detonation_velocity: float = Field(default=6000.0, ge=3000.0, le=9000.0, description="Detonation velocity in m/s")
    chapman_jouguet_pressure: float = Field(default=21e9, ge=1e9, le=50e9, description="Chapman-Jouguet pressure in Pa")
    timeout_seconds: int = Field(default=3600, ge=60, le=86400, description="Simulation timeout in seconds")


class YadeConfigSchema(BaseModel):
    """Configuration for YADE DEM simulation"""
    enabled: bool = True
    particle_radius_min: float = Field(default=0.01, ge=0.001, le=0.1, description="Minimum particle radius in meters")
    particle_radius_max: float = Field(default=0.1, ge=0.01, le=1.0, description="Maximum particle radius in meters")
    particle_density: float = Field(default=2700.0, ge=1000.0, le=5000.0, description="Particle density in kg/m³")
    young_modulus: float = Field(default=70e9, ge=1e9, le=200e9, description="Young's modulus in Pa")
    poisson_ratio: float = Field(default=0.25, ge=0.1, le=0.49, description="Poisson's ratio")
    friction_angle: float = Field(default=30.0, ge=0.0, le=90.0, description="Friction angle in degrees")
    cohesion: float = Field(default=1e6, ge=0.0, le=50e6, description="Cohesion in Pa")
    tensile_strength: float = Field(default=5e6, ge=0.0, le=50e6, description="Tensile strength in Pa")
    max_iterations: int = Field(default=100000, ge=1000, le=1000000, description="Maximum iterations")
    convergence_tolerance: float = Field(default=1e-6, ge=1e-10, le=1e-3, description="Convergence tolerance")
    timeout_seconds: int = Field(default=3600, ge=60, le=86400, description="Simulation timeout in seconds")

    @validator('particle_radius_max')
    def validate_radius_range(cls, v, values):
        if 'particle_radius_min' in values and v <= values['particle_radius_min']:
            raise ValueError('particle_radius_max must be greater than particle_radius_min')
        return v


class MeshGeometrySchema(BaseModel):
    """Geometry definition for simulation mesh"""
    bench_vertices: List[List[float]] = Field(description="3D vertices defining bench geometry")
    bench_faces: List[List[int]] = Field(description="Face connectivity for bench")
    hole_positions: List[List[float]] = Field(description="Drill hole collar positions [x, y, z]")
    hole_depths: List[float] = Field(description="Drill hole depths in meters")
    hole_diameters: List[float] = Field(description="Drill hole diameters in meters")
    charge_positions: List[List[float]] = Field(description="Explosive charge positions [x, y, z]")
    charge_masses: List[float] = Field(description="Explosive charge masses in kg")
    charge_types: List[str] = Field(description="Explosive charge types")

    @validator('bench_vertices')
    def validate_bench_vertices(cls, v):
        for vertex in v:
            if len(vertex) != 3:
                raise ValueError('Each bench vertex must have exactly 3 coordinates [x, y, z]')
        return v

    @validator('hole_positions', 'charge_positions')
    def validate_positions(cls, v):
        for pos in v:
            if len(pos) != 3:
                raise ValueError('Each position must have exactly 3 coordinates [x, y, z]')
        return v


class SimulationJobCreateSchema(BaseModel):
    """Schema for creating a new simulation job"""
    simulation_type: SimulationType
    geometry: MeshGeometrySchema
    blast_plan_id: Optional[str] = None
    blastfoam_config: Optional[BlastFoamConfigSchema] = None
    yade_config: Optional[YadeConfigSchema] = None
    priority: int = Field(default=0, ge=0, le=10, description="Job priority (0=lowest, 10=highest)")


class SimulationResultSchema(BaseModel):
    """Schema for simulation results"""
    simulation_type: SimulationType
    success: bool
    runtime_seconds: float
    ppv_predictions: Dict[str, float] = Field(default_factory=dict, description="PPV predictions by receptor ID")
    ppv_time_series: Dict[str, List[List[float]]] = Field(default_factory=dict, description="PPV time series data")
    fragment_sizes: Optional[List[float]] = Field(None, description="Fragment sizes array")
    fragment_size_distribution: Optional[Dict[str, float]] = Field(None, description="Fragment size statistics")
    mesh_quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Mesh quality metrics")
    convergence_metrics: Dict[str, float] = Field(default_factory=dict, description="Convergence metrics")
    warnings: List[str] = Field(default_factory=list, description="Simulation warnings")
    errors: List[str] = Field(default_factory=list, description="Simulation errors")


class SimulationJobSchema(BaseModel):
    """Schema for simulation job information"""
    job_id: str
    simulation_type: SimulationType
    status: SimulationStatus
    blast_plan_id: Optional[str] = None
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    runtime_seconds: Optional[float] = None
    result: Optional[SimulationResultSchema] = None


class SimulationJobListSchema(BaseModel):
    """Schema for listing simulation jobs"""
    jobs: List[SimulationJobSchema]
    total_count: int
    page: int
    page_size: int


class SimulationComparisonSchema(BaseModel):
    """Schema for simulation result comparison"""
    simulation_types: List[str]
    success_rates: List[bool]
    runtimes: List[float]
    fragmentation_comparison: Dict[str, Any] = Field(default_factory=dict)
    ppv_comparison: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)


class SimulationCapabilitiesSchema(BaseModel):
    """Schema for available simulation capabilities"""
    available_types: List[SimulationType]
    blastfoam_available: bool
    yade_available: bool
    installation_guides: Dict[str, str] = Field(default_factory=dict)


class SimulationJobUpdateSchema(BaseModel):
    """Schema for updating simulation job"""
    priority: Optional[int] = Field(None, ge=0, le=10)
    status: Optional[SimulationStatus] = None


class SimulationConfigTestSchema(BaseModel):
    """Schema for testing simulation configuration"""
    simulation_type: SimulationType
    blastfoam_config: Optional[BlastFoamConfigSchema] = None
    yade_config: Optional[YadeConfigSchema] = None


class SimulationConfigTestResultSchema(BaseModel):
    """Schema for simulation configuration test results"""
    simulation_type: SimulationType
    available: bool
    version_info: Optional[str] = None
    test_passed: bool
    test_duration_seconds: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)