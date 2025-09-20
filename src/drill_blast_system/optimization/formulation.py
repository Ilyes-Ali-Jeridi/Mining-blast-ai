"""
Optimization problem formulation utilities.

This module provides tools for formulating drill-and-blast optimization problems,
including decision variables, constraints, and objective functions.
"""

from typing import List, Dict, Tuple, Any, Optional, Callable
import numpy as np
from dataclasses import dataclass
import logging

from .data_structures import (
    OptimizationProblem, DecisionVariable, OptimizationConstraint,
    OptimizationObjective, BlastPlan, DrillHole
)
# from ..physics_models.fragmentation_curve import FragmentationCurve
from ..safety.config import SafetyConfig

logger = logging.getLogger(__name__)


@dataclass
class SiteGeometry:
    """Site geometry parameters for optimization"""
    bench_width: float
    bench_length: float
    bench_height: float
    free_face_coordinates: List[Tuple[float, float]]
    excluded_zones: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.excluded_zones is None:
            self.excluded_zones = []


@dataclass
class OptimizationParameters:
    """Parameters controlling optimization behavior"""
    
    # Hole pattern parameters
    min_burden: float = 2.0  # meters
    max_burden: float = 8.0  # meters
    min_spacing: float = 2.0  # meters
    max_spacing: float = 8.0  # meters
    
    # Charge parameters
    min_charge_per_hole: float = 0.0  # kg
    max_charge_per_hole: float = 50.0  # kg
    charge_discretization: float = 1.0  # kg steps
    
    # Delay parameters
    min_delay: int = 0  # ms
    max_delay: int = 1000  # ms
    delay_increment: int = 25  # ms
    
    # Position adjustment limits (for continuous optimization)
    max_position_offset: float = 1.0  # meters
    
    # Objective weights
    fragmentation_weight: float = 1.0
    cost_weight: float = 0.5
    ppv_weight: float = 2.0
    
    # Target values
    target_p80: float = 200.0  # mm
    max_acceptable_ppv: float = 5.0  # mm/s


class ProblemFormulator:
    """Formulates optimization problems from site data and parameters"""
    
    def __init__(self, safety_config: SafetyConfig):
        self.safety_config = safety_config
        self.logger = logging.getLogger(__name__ + ".ProblemFormulator")
    
    def formulate_problem(self, 
                         site_geometry: SiteGeometry,
                         hole_pattern: List[DrillHole],
                         optimization_params: OptimizationParameters) -> OptimizationProblem:
        """
        Formulate complete optimization problem from site data.
        
        Args:
            site_geometry: Site geometry and constraints
            hole_pattern: Initial hole pattern (positions and basic specs)
            optimization_params: Optimization parameters and limits
            
        Returns:
            Complete optimization problem formulation
        """
        self.logger.info(f"Formulating optimization problem with {len(hole_pattern)} holes")
        
        problem = OptimizationProblem(
            problem_id=f"blast_opt_{len(hole_pattern)}holes",
            site_data={
                "geometry": site_geometry,
                "parameters": optimization_params
            },
            num_holes=len(hole_pattern)
        )
        
        # Create decision variables
        problem.variables = self._create_decision_variables(hole_pattern, optimization_params)
        
        # Create constraints
        problem.constraints = self._create_constraints(
            hole_pattern, site_geometry, optimization_params
        )
        
        # Create objectives
        problem.objectives = self._create_objectives(optimization_params)
        
        # Calculate problem size and complexity
        problem.calculate_problem_size()
        
        # Suggest preferred algorithms based on problem characteristics
        problem.preferred_algorithms = self._suggest_algorithms(problem)
        
        self.logger.info(f"Problem formulated: {problem.num_variables} variables, "
                        f"{problem.num_constraints} constraints, complexity: {problem.estimated_complexity}")
        
        return problem
    
    def _create_decision_variables(self, 
                                 hole_pattern: List[DrillHole],
                                 params: OptimizationParameters) -> List[DecisionVariable]:
        """Create decision variables for each hole"""
        variables = []
        
        for i, hole in enumerate(hole_pattern):
            # Charge per hole (continuous or discrete)
            variables.append(DecisionVariable(
                name=f"charge_{hole.hole_id}",
                var_type="continuous",
                lower_bound=params.min_charge_per_hole,
                upper_bound=min(params.max_charge_per_hole, self.safety_config.max_charge_per_hole),
                initial_value=hole.charge_kg if hole.charge_kg > 0 else params.max_charge_per_hole / 2,
                description=f"Charge for hole {hole.hole_id}",
                units="kg"
            ))
            
            # Delay timing (discrete)
            delay_values = list(range(params.min_delay, params.max_delay + 1, params.delay_increment))
            variables.append(DecisionVariable(
                name=f"delay_{hole.hole_id}",
                var_type="integer",
                lower_bound=params.min_delay,
                upper_bound=params.max_delay,
                discrete_values=delay_values,
                initial_value=hole.delay_ms if hole.delay_ms > 0 else params.min_delay,
                description=f"Delay timing for hole {hole.hole_id}",
                units="ms"
            ))
            
            # Position offsets (for continuous optimization)
            variables.append(DecisionVariable(
                name=f"offset_x_{hole.hole_id}",
                var_type="continuous",
                lower_bound=-params.max_position_offset,
                upper_bound=params.max_position_offset,
                initial_value=hole.position_offset_x,
                description=f"X position offset for hole {hole.hole_id}",
                units="m"
            ))
            
            variables.append(DecisionVariable(
                name=f"offset_y_{hole.hole_id}",
                var_type="continuous", 
                lower_bound=-params.max_position_offset,
                upper_bound=params.max_position_offset,
                initial_value=hole.position_offset_y,
                description=f"Y position offset for hole {hole.hole_id}",
                units="m"
            ))
        
        return variables
    
    def _create_constraints(self,
                          hole_pattern: List[DrillHole],
                          site_geometry: SiteGeometry,
                          params: OptimizationParameters) -> List[OptimizationConstraint]:
        """Create optimization constraints"""
        constraints = []
        
        # Per-delay charge limits (regulatory constraint)
        constraints.append(OptimizationConstraint(
            name="per_delay_charge_limit",
            constraint_type="inequality",
            description=f"Total charge per delay ≤ {self.safety_config.max_charge_per_delay} kg",
            is_hard=True
        ))
        
        # PPV limits at sensitive receptors
        if hasattr(self.safety_config, 'receptor_limits'):
            for receptor_id, ppv_limit in self.safety_config.receptor_limits.items():
                constraints.append(OptimizationConstraint(
                    name=f"ppv_limit_{receptor_id}",
                    constraint_type="inequality",
                    description=f"PPV at {receptor_id} ≤ {ppv_limit} mm/s",
                    is_hard=True
                ))
        
        # Minimum burden/spacing constraints
        constraints.append(OptimizationConstraint(
            name="minimum_burden",
            constraint_type="inequality",
            description=f"Burden ≥ {params.min_burden} m",
            is_hard=True
        ))
        
        constraints.append(OptimizationConstraint(
            name="minimum_spacing",
            constraint_type="inequality", 
            description=f"Spacing ≥ {params.min_spacing} m",
            is_hard=True
        ))
        
        # Powder factor limits
        constraints.append(OptimizationConstraint(
            name="powder_factor_min",
            constraint_type="inequality",
            description=f"Powder factor ≥ {self.safety_config.powder_factor_min} kg/t",
            is_hard=True
        ))
        
        constraints.append(OptimizationConstraint(
            name="powder_factor_max",
            constraint_type="inequality",
            description=f"Powder factor ≤ {self.safety_config.powder_factor_max} kg/t",
            is_hard=True
        ))
        
        # Excluded zones constraints
        for i, zone in enumerate(site_geometry.excluded_zones):
            constraints.append(OptimizationConstraint(
                name=f"excluded_zone_{i}",
                constraint_type="inequality",
                description=f"Holes must avoid excluded zone {i}",
                is_hard=True
            ))
        
        return constraints
    
    def _create_objectives(self, params: OptimizationParameters) -> List[OptimizationObjective]:
        """Create optimization objectives"""
        objectives = []
        
        # Fragmentation objective (minimize deviation from target P80)
        objectives.append(OptimizationObjective(
            name="fragmentation_quality",
            objective_type="minimize",
            weight=params.fragmentation_weight,
            target_value=params.target_p80,
            description=f"Minimize |P80 - {params.target_p80}| mm"
        ))
        
        # Cost objective (minimize total charge and drilling)
        objectives.append(OptimizationObjective(
            name="total_cost",
            objective_type="minimize",
            weight=params.cost_weight,
            description="Minimize total explosive and drilling cost"
        ))
        
        # PPV penalty (minimize maximum PPV)
        objectives.append(OptimizationObjective(
            name="ppv_penalty",
            objective_type="minimize",
            weight=params.ppv_weight,
            target_value=params.max_acceptable_ppv,
            description=f"Minimize PPV penalty above {params.max_acceptable_ppv} mm/s"
        ))
        
        return objectives
    
    def _suggest_algorithms(self, problem: OptimizationProblem) -> List[str]:
        """Suggest appropriate algorithms based on problem characteristics"""
        algorithms = []
        
        # Always include CP-SAT for discrete variables
        algorithms.append("cp_sat")
        
        # Add continuous algorithms based on problem size
        if problem.estimated_complexity in ["low", "medium"]:
            algorithms.extend(["scipy_differential_evolution", "scipy_slsqp"])
        
        # Add genetic algorithm for complex problems
        if problem.estimated_complexity == "high":
            algorithms.append("genetic_algorithm")
        
        return algorithms


class ObjectiveFunction:
    """Calculates objective function values for blast plans"""
    
    def __init__(self, physics_models: Any, optimization_params: OptimizationParameters):
        self.physics_models = physics_models
        self.params = optimization_params
        self.logger = logging.getLogger(__name__ + ".ObjectiveFunction")
    
    def evaluate(self, blast_plan: BlastPlan, site_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate all objective components for a blast plan.
        
        Args:
            blast_plan: Complete blast plan to evaluate
            site_data: Site geometry and rock properties
            
        Returns:
            Dictionary of objective component values
        """
        objectives = {}
        
        try:
            # Calculate fragmentation quality
            objectives["fragmentation_quality"] = self._calculate_fragmentation_objective(
                blast_plan, site_data
            )
            
            # Calculate cost objective
            objectives["total_cost"] = self._calculate_cost_objective(blast_plan)
            
            # Calculate PPV penalty
            objectives["ppv_penalty"] = self._calculate_ppv_penalty(blast_plan, site_data)
            
            # Calculate weighted total
            total_objective = (
                objectives["fragmentation_quality"] * self.params.fragmentation_weight +
                objectives["total_cost"] * self.params.cost_weight +
                objectives["ppv_penalty"] * self.params.ppv_weight
            )
            objectives["total"] = total_objective
            
        except Exception as e:
            self.logger.error(f"Error evaluating objectives: {e}")
            # Return penalty values for invalid solutions
            objectives = {
                "fragmentation_quality": 1e6,
                "total_cost": 1e6,
                "ppv_penalty": 1e6,
                "total": 3e6
            }
        
        return objectives
    
    def _calculate_fragmentation_objective(self, blast_plan: BlastPlan, site_data: Dict[str, Any]) -> float:
        """Calculate fragmentation quality objective"""
        if not blast_plan.predicted_fragmentation:
            return 1e6  # Large penalty for missing predictions
        
        predicted_p80 = blast_plan.predicted_fragmentation.get("P80", 0)
        target_p80 = self.params.target_p80
        
        # Minimize absolute deviation from target
        deviation = abs(predicted_p80 - target_p80)
        
        # Normalize by target value
        normalized_deviation = deviation / target_p80 if target_p80 > 0 else deviation
        
        return normalized_deviation
    
    def _calculate_cost_objective(self, blast_plan: BlastPlan) -> float:
        """Calculate total cost objective"""
        # Simple cost model: charge cost + drilling cost
        explosive_cost_per_kg = 2.0  # $/kg (configurable)
        drilling_cost_per_meter = 5.0  # $/m (configurable)
        
        total_explosive_cost = blast_plan.total_charge_kg * explosive_cost_per_kg
        total_drilling_cost = sum(hole.depth for hole in blast_plan.holes) * drilling_cost_per_meter
        
        total_cost = total_explosive_cost + total_drilling_cost
        
        # Normalize by typical cost range
        normalized_cost = total_cost / 10000.0  # Assuming $10k typical range
        
        return normalized_cost
    
    def _calculate_ppv_penalty(self, blast_plan: BlastPlan, site_data: Dict[str, Any]) -> float:
        """Calculate PPV penalty objective"""
        if not blast_plan.predicted_ppv:
            return 0.0  # No penalty if no receptors
        
        max_acceptable_ppv = self.params.max_acceptable_ppv
        penalty = 0.0
        
        for receptor_id, predicted_ppv in blast_plan.predicted_ppv.items():
            if predicted_ppv > max_acceptable_ppv:
                # Quadratic penalty for PPV violations
                excess = predicted_ppv - max_acceptable_ppv
                penalty += (excess / max_acceptable_ppv) ** 2
        
        return penalty


class ConstraintManager:
    """Manages constraint evaluation and violation checking"""
    
    def __init__(self, safety_config: SafetyConfig):
        self.safety_config = safety_config
        self.logger = logging.getLogger(__name__ + ".ConstraintManager")
    
    def evaluate_constraints(self, 
                           blast_plan: BlastPlan,
                           site_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate all constraints for a blast plan.
        
        Args:
            blast_plan: Blast plan to evaluate
            site_data: Site geometry and parameters
            
        Returns:
            Dictionary of constraint violations (0 = satisfied, >0 = violation)
        """
        violations = {}
        
        try:
            # Per-delay charge limits
            violations.update(self._check_delay_charge_limits(blast_plan))
            
            # PPV limits
            violations.update(self._check_ppv_limits(blast_plan))
            
            # Powder factor limits
            violations.update(self._check_powder_factor_limits(blast_plan, site_data))
            
            # Geometric constraints
            violations.update(self._check_geometric_constraints(blast_plan, site_data))
            
        except Exception as e:
            self.logger.error(f"Error evaluating constraints: {e}")
            violations["evaluation_error"] = 1.0
        
        return violations
    
    def _check_delay_charge_limits(self, blast_plan: BlastPlan) -> Dict[str, float]:
        """Check per-delay charge limits"""
        violations = {}
        delay_charges = blast_plan.get_charge_per_delay()
        
        for delay, total_charge in delay_charges.items():
            if total_charge > self.safety_config.max_charge_per_delay:
                excess = total_charge - self.safety_config.max_charge_per_delay
                violations[f"delay_{delay}_charge_limit"] = excess
        
        return violations
    
    def _check_ppv_limits(self, blast_plan: BlastPlan) -> Dict[str, float]:
        """Check PPV limits at receptors"""
        violations = {}
        
        if hasattr(self.safety_config, 'receptor_limits'):
            for receptor_id, ppv_limit in self.safety_config.receptor_limits.items():
                predicted_ppv = blast_plan.predicted_ppv.get(receptor_id, 0)
                if predicted_ppv > ppv_limit:
                    excess = predicted_ppv - ppv_limit
                    violations[f"ppv_{receptor_id}"] = excess
        
        return violations
    
    def _check_powder_factor_limits(self, blast_plan: BlastPlan, site_data: Dict[str, Any]) -> Dict[str, float]:
        """Check powder factor limits"""
        violations = {}
        
        # Calculate overall powder factor (simplified)
        total_rock_volume = site_data.get("total_rock_volume", 1000.0)  # m³
        rock_density = site_data.get("rock_density", 2.7)  # t/m³
        total_rock_mass = total_rock_volume * rock_density
        
        if total_rock_mass > 0:
            powder_factor = blast_plan.total_charge_kg / total_rock_mass
            
            if powder_factor < self.safety_config.powder_factor_min:
                violations["powder_factor_min"] = self.safety_config.powder_factor_min - powder_factor
            
            if powder_factor > self.safety_config.powder_factor_max:
                violations["powder_factor_max"] = powder_factor - self.safety_config.powder_factor_max
        
        return violations
    
    def _check_geometric_constraints(self, blast_plan: BlastPlan, site_data: Dict[str, Any]) -> Dict[str, float]:
        """Check geometric constraints (burden, spacing, excluded zones)"""
        violations = {}
        
        # This would implement detailed geometric constraint checking
        # For now, return empty (constraints satisfied)
        
        return violations
    
    def is_feasible(self, constraint_violations: Dict[str, float], tolerance: float = 1e-6) -> bool:
        """Check if solution is feasible within tolerance"""
        return all(violation <= tolerance for violation in constraint_violations.values())