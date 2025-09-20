"""
Data structures for simulation integration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np


class SimulationType(Enum):
    """Types of simulation available"""
    BLASTFOAM = "blastfoam"
    YADE = "yade"
    PHYSICS_ONLY = "physics_only"


@dataclass
class SimulationConfig:
    """Base configuration for simulations"""
    simulation_type: SimulationType
    enabled: bool = False
    timeout_seconds: int = 3600  # 1 hour default
    working_directory: str = "./simulation_temp"
    cleanup_after_run: bool = True
    parallel_processes: int = 1


@dataclass
class BlastFoamConfig(SimulationConfig):
    """Configuration for blastFoam simulation"""
    simulation_type: SimulationType = SimulationType.BLASTFOAM
    openfoam_version: str = "v2112"
    blastfoam_path: Optional[str] = None
    mesh_resolution: float = 0.5  # meters
    simulation_time: float = 0.1  # seconds
    time_step: float = 1e-6  # seconds
    pressure_solver: str = "rhoCentralFoam"
    turbulence_model: str = "kEpsilon"
    
    # Explosive properties for simulation
    explosive_density: float = 1200.0  # kg/m³
    detonation_velocity: float = 6000.0  # m/s
    chapman_jouguet_pressure: float = 21e9  # Pa
    
    # Mesh parameters
    background_mesh_size: float = 1.0  # meters
    explosive_mesh_refinement: int = 3
    rock_mesh_refinement: int = 2


@dataclass
class YadeConfig(SimulationConfig):
    """Configuration for YADE DEM simulation"""
    simulation_type: SimulationType = SimulationType.YADE
    yade_executable: Optional[str] = None
    particle_radius_min: float = 0.01  # meters
    particle_radius_max: float = 0.1   # meters
    particle_density: float = 2700.0   # kg/m³
    young_modulus: float = 70e9        # Pa
    poisson_ratio: float = 0.25
    friction_angle: float = 30.0       # degrees
    cohesion: float = 1e6              # Pa
    tensile_strength: float = 5e6      # Pa
    
    # Simulation parameters
    gravity: Tuple[float, float, float] = (0.0, 0.0, -9.81)
    damping: float = 0.2
    max_iterations: int = 100000
    convergence_tolerance: float = 1e-6


@dataclass
class SimulationResult:
    """Results from high-fidelity simulation"""
    simulation_type: SimulationType
    success: bool
    runtime_seconds: float
    
    # PPV results
    ppv_predictions: Dict[str, float] = field(default_factory=dict)  # receptor_id -> ppv
    ppv_time_series: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # receptor_id -> [(time, ppv)]
    
    # Fragmentation results
    fragment_sizes: Optional[np.ndarray] = None
    fragment_size_distribution: Optional[Dict[str, float]] = None  # P10, P50, P80, etc.
    
    # Additional simulation data
    pressure_field: Optional[np.ndarray] = None
    velocity_field: Optional[np.ndarray] = None
    damage_field: Optional[np.ndarray] = None
    
    # Metadata
    mesh_quality_metrics: Dict[str, float] = field(default_factory=dict)
    convergence_metrics: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class MeshGeometry:
    """Geometry definition for simulation mesh"""
    # Bench geometry
    bench_vertices: List[Tuple[float, float, float]]  # 3D vertices defining bench
    bench_faces: List[List[int]]  # Face connectivity
    
    # Drill holes
    hole_positions: List[Tuple[float, float, float]]  # Hole collar positions
    hole_depths: List[float]
    hole_diameters: List[float]
    
    # Explosive charges
    charge_positions: List[Tuple[float, float, float]]
    charge_masses: List[float]
    charge_types: List[str]
    
    # Boundary conditions
    fixed_boundaries: List[str] = field(default_factory=list)
    pressure_boundaries: List[str] = field(default_factory=list)
    
    # Material zones
    rock_zones: List[Dict[str, Any]] = field(default_factory=list)
    explosive_zones: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SimulationJob:
    """Represents a simulation job to be executed"""
    job_id: str
    config: SimulationConfig
    geometry: MeshGeometry
    blast_plan_id: Optional[str] = None
    priority: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[SimulationResult] = None