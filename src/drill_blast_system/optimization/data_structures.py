"""
Core data structures for optimization problems and solutions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import numpy as np
from datetime import datetime


class OptimizationStatus(Enum):
    """Status of optimization process"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class DrillHole:
    """Individual drill hole specification with optimization variables"""
    
    # Fixed parameters (from site geometry)
    hole_id: str
    coordinates: Tuple[float, float, float]  # x, y, z in meters
    depth: float  # meters
    diameter: float  # mm
    
    # Optimization variables
    charge_kg: float = 0.0  # kg of explosive
    stemming_m: float = 0.0  # meters of stemming
    delay_ms: int = 0  # delay time in milliseconds
    explosive_type: str = "ANFO"  # type of explosive
    
    # Optional position adjustments (for continuous optimization)
    position_offset_x: float = 0.0  # meters
    position_offset_y: float = 0.0  # meters
    
    # Derived properties
    burden: Optional[float] = None  # meters to free face
    spacing: Optional[float] = None  # meters to adjacent holes
    
    def get_actual_coordinates(self) -> Tuple[float, float, float]:
        """Get coordinates including position offsets"""
        x, y, z = self.coordinates
        return (x + self.position_offset_x, y + self.position_offset_y, z)
    
    def get_powder_factor(self, rock_volume: float, rock_density: float) -> float:
        """Calculate powder factor in kg/t"""
        if rock_volume <= 0 or rock_density <= 0:
            return 0.0
        rock_mass_tonnes = rock_volume * rock_density  # rock_density is already in t/m³
        return self.charge_kg / rock_mass_tonnes if rock_mass_tonnes > 0 else 0.0


@dataclass
class BlastPlan:
    """Complete drill-and-blast plan with holes and predictions"""
    
    # Plan identification
    plan_id: str
    site_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Drill holes
    holes: List[DrillHole] = field(default_factory=list)
    
    # Predicted results (populated by physics models)
    predicted_fragmentation: Optional[Dict[str, float]] = None  # P50, P80, etc.
    predicted_ppv: Dict[str, float] = field(default_factory=dict)  # receptor_id -> ppv_value
    
    # Safety and validation
    safety_status: Optional[Dict[str, Any]] = None
    is_safety_validated: bool = False
    
    # Economic metrics
    total_charge_kg: float = 0.0
    total_holes: int = 0
    estimated_cost: float = 0.0
    
    # Optimization metadata
    optimization_algorithm: Optional[str] = None
    optimization_time_seconds: float = 0.0
    objective_value: float = float('inf')
    
    def calculate_totals(self) -> None:
        """Calculate total metrics from holes"""
        self.total_holes = len(self.holes)
        self.total_charge_kg = sum(hole.charge_kg for hole in self.holes)
    
    def get_holes_by_delay(self) -> Dict[int, List[DrillHole]]:
        """Group holes by delay timing"""
        delay_groups = {}
        for hole in self.holes:
            if hole.delay_ms not in delay_groups:
                delay_groups[hole.delay_ms] = []
            delay_groups[hole.delay_ms].append(hole)
        return delay_groups
    
    def get_charge_per_delay(self) -> Dict[int, float]:
        """Calculate total charge per delay"""
        delay_charges = {}
        for hole in self.holes:
            if hole.delay_ms not in delay_charges:
                delay_charges[hole.delay_ms] = 0.0
            delay_charges[hole.delay_ms] += hole.charge_kg
        return delay_charges


@dataclass
class DecisionVariable:
    """Definition of an optimization decision variable"""
    
    name: str
    var_type: str  # 'continuous', 'integer', 'binary'
    lower_bound: float
    upper_bound: float
    initial_value: Optional[float] = None
    
    # For discrete variables
    discrete_values: Optional[List[float]] = None
    
    # Variable metadata
    description: str = ""
    units: str = ""


@dataclass
class OptimizationConstraint:
    """Definition of an optimization constraint"""
    
    name: str
    constraint_type: str  # 'equality', 'inequality', 'bound'
    description: str = ""
    
    # Constraint parameters
    is_hard: bool = True  # Hard constraints must be satisfied
    penalty_weight: float = 1000.0  # For soft constraints
    
    # Tolerance for constraint satisfaction
    tolerance: float = 1e-6


@dataclass
class OptimizationObjective:
    """Definition of optimization objective component"""
    
    name: str
    objective_type: str  # 'minimize', 'maximize'
    weight: float = 1.0
    description: str = ""
    
    # Target value (for tracking objectives)
    target_value: Optional[float] = None
    
    # Normalization parameters
    scale_factor: float = 1.0
    offset: float = 0.0


@dataclass
class OptimizationProblem:
    """Complete optimization problem formulation"""
    
    # Problem identification
    problem_id: str
    site_data: Dict[str, Any]
    
    # Decision variables
    variables: List[DecisionVariable] = field(default_factory=list)
    
    # Constraints
    constraints: List[OptimizationConstraint] = field(default_factory=list)
    
    # Objectives
    objectives: List[OptimizationObjective] = field(default_factory=list)
    
    # Problem size metrics
    num_holes: int = 0
    num_variables: int = 0
    num_constraints: int = 0
    
    # Complexity estimation
    estimated_complexity: str = "unknown"  # 'low', 'medium', 'high'
    estimated_solve_time: float = 0.0  # seconds
    
    # Algorithm preferences
    preferred_algorithms: List[str] = field(default_factory=list)
    
    def calculate_problem_size(self) -> None:
        """Calculate problem size metrics"""
        self.num_variables = len(self.variables)
        self.num_constraints = len(self.constraints)
        
        # Estimate complexity based on problem size
        total_size = self.num_variables * self.num_constraints
        if total_size < 1000:
            self.estimated_complexity = "low"
            self.estimated_solve_time = 1.0
        elif total_size < 10000:
            self.estimated_complexity = "medium" 
            self.estimated_solve_time = 10.0
        else:
            self.estimated_complexity = "high"
            self.estimated_solve_time = 60.0
    
    def get_variable_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get variable bounds as numpy arrays"""
        lower_bounds = np.array([var.lower_bound for var in self.variables])
        upper_bounds = np.array([var.upper_bound for var in self.variables])
        return lower_bounds, upper_bounds
    
    def get_initial_solution(self) -> np.ndarray:
        """Get initial solution vector"""
        initial = []
        for var in self.variables:
            if var.initial_value is not None:
                initial.append(var.initial_value)
            else:
                # Use midpoint of bounds as default
                initial.append((var.lower_bound + var.upper_bound) / 2.0)
        return np.array(initial)


@dataclass
class OptimizationResult:
    """Result of optimization process"""
    
    # Solution
    best_plan: Optional[BlastPlan] = None
    objective_value: float = float('inf')
    
    # Algorithm information
    algorithm_used: str = ""
    status: OptimizationStatus = OptimizationStatus.NOT_STARTED
    
    # Performance metrics
    solve_time_seconds: float = 0.0
    iterations: int = 0
    function_evaluations: int = 0
    
    # Convergence information
    converged: bool = False
    convergence_tolerance: float = 1e-6
    
    # Multiple solutions (for multi-objective)
    alternative_plans: List[BlastPlan] = field(default_factory=list)
    
    # Constraint satisfaction
    constraint_violations: List[str] = field(default_factory=list)
    max_constraint_violation: float = 0.0
    
    # Progress tracking
    objective_history: List[float] = field(default_factory=list)
    
    def is_feasible(self) -> bool:
        """Check if solution satisfies all constraints"""
        return len(self.constraint_violations) == 0
    
    def get_solution_quality(self) -> str:
        """Assess solution quality"""
        if not self.is_feasible():
            return "infeasible"
        elif not self.converged:
            return "suboptimal"
        elif self.objective_value == float('inf'):
            return "no_solution"
        else:
            return "optimal"