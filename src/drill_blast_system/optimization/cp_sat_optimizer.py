"""
OR-Tools CP-SAT optimizer for discrete drill-and-blast optimization.

This module implements constraint programming optimization using Google OR-Tools
CP-SAT solver for discrete variables like charges and delays.
"""

from typing import List, Dict, Tuple, Optional, Any, Callable
import numpy as np
from ortools.sat.python import cp_model
import logging
from dataclasses import dataclass
import time

from .data_structures import (
    OptimizationProblem, OptimizationResult, OptimizationStatus,
    BlastPlan, DrillHole, DecisionVariable
)
from .formulation import ObjectiveFunction, ConstraintManager


@dataclass
class CPSATConfig:
    """Configuration for CP-SAT solver"""
    
    # Solver parameters
    max_time_seconds: float = 300.0  # 5 minutes default
    num_search_workers: int = 4
    log_search_progress: bool = True
    
    # Solution parameters
    enumerate_all_solutions: bool = False
    max_solutions: int = 10
    
    # Discretization parameters
    charge_discretization: float = 1.0  # kg
    delay_discretization: int = 25  # ms
    
    # Objective scaling (to avoid floating point in CP-SAT)
    objective_scale_factor: int = 1000


class CPSATSolutionCallback(cp_model.CpSolverSolutionCallback):
    """Callback to collect multiple solutions from CP-SAT"""
    
    def __init__(self, variables: Dict[str, cp_model.IntVar], max_solutions: int = 10):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.variables = variables
        self.max_solutions = max_solutions
        self.solutions = []
        self.objective_values = []
        
    def on_solution_callback(self):
        """Called when a new solution is found"""
        if len(self.solutions) >= self.max_solutions:
            return
            
        # Extract variable values
        solution = {}
        for name, var in self.variables.items():
            solution[name] = self.Value(var)
        
        self.solutions.append(solution)
        self.objective_values.append(self.ObjectiveValue())
        
        # Stop if we have enough solutions
        if len(self.solutions) >= self.max_solutions:
            self.StopSearch()


class CPSATOptimizer:
    """CP-SAT optimizer for discrete blast optimization problems"""
    
    def __init__(self, 
                 config: CPSATConfig = None,
                 objective_function: ObjectiveFunction = None,
                 constraint_manager: ConstraintManager = None):
        self.config = config or CPSATConfig()
        self.objective_function = objective_function
        self.constraint_manager = constraint_manager
        self.logger = logging.getLogger(__name__ + ".CPSATOptimizer")
        
        # CP-SAT model components
        self.model = None
        self.solver = None
        self.variables = {}
        self.constraints = {}
        
    def optimize(self, 
                problem: OptimizationProblem,
                initial_plan: Optional[BlastPlan] = None) -> OptimizationResult:
        """
        Optimize blast plan using CP-SAT solver.
        
        Args:
            problem: Optimization problem formulation
            initial_plan: Optional initial blast plan for warm start
            
        Returns:
            Optimization result with best solution found
        """
        self.logger.info(f"Starting CP-SAT optimization for problem {problem.problem_id}")
        start_time = time.time()
        
        try:
            # Create CP-SAT model
            self._create_model(problem)
            
            # Add decision variables
            self._add_variables(problem)
            
            # Add constraints
            self._add_constraints(problem)
            
            # Set objective
            self._set_objective(problem)
            
            # Configure solver
            self._configure_solver()
            
            # Solve the problem
            result = self._solve(problem, initial_plan)
            
            # Update timing
            result.solve_time_seconds = time.time() - start_time
            
            self.logger.info(f"CP-SAT optimization completed in {result.solve_time_seconds:.2f}s, "
                           f"status: {result.status}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"CP-SAT optimization failed: {e}")
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                algorithm_used="cp_sat",
                solve_time_seconds=time.time() - start_time
            )
    
    def _create_model(self, problem: OptimizationProblem):
        """Create CP-SAT model"""
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.variables = {}
        self.constraints = {}
        
        self.logger.debug("Created CP-SAT model")
    
    def _add_variables(self, problem: OptimizationProblem):
        """Add decision variables to CP-SAT model"""
        for var in problem.variables:
            if var.var_type in ['integer', 'binary']:
                # Direct integer variables
                cp_var = self.model.NewIntVar(
                    int(var.lower_bound),
                    int(var.upper_bound),
                    var.name
                )
                self.variables[var.name] = cp_var
                
            elif var.var_type == 'continuous':
                # Discretize continuous variables for CP-SAT
                if 'charge' in var.name:
                    # Discretize charges
                    step = self.config.charge_discretization
                    min_val = int(var.lower_bound / step)
                    max_val = int(var.upper_bound / step)
                    
                    cp_var = self.model.NewIntVar(min_val, max_val, f"{var.name}_discrete")
                    self.variables[var.name] = cp_var
                    
                elif 'offset' in var.name:
                    # Discretize position offsets (0.1m precision)
                    step = 0.1
                    min_val = int(var.lower_bound / step)
                    max_val = int(var.upper_bound / step)
                    
                    cp_var = self.model.NewIntVar(min_val, max_val, f"{var.name}_discrete")
                    self.variables[var.name] = cp_var
                    
                else:
                    # Default discretization
                    min_val = int(var.lower_bound * 10)  # 0.1 precision
                    max_val = int(var.upper_bound * 10)
                    
                    cp_var = self.model.NewIntVar(min_val, max_val, f"{var.name}_discrete")
                    self.variables[var.name] = cp_var
        
        self.logger.debug(f"Added {len(self.variables)} variables to CP-SAT model")
    
    def _add_constraints(self, problem: OptimizationProblem):
        """Add constraints to CP-SAT model"""
        
        # Per-delay charge limits
        self._add_delay_charge_constraints(problem)
        
        # PPV constraints (simplified for CP-SAT)
        self._add_ppv_constraints(problem)
        
        # Powder factor constraints
        self._add_powder_factor_constraints(problem)
        
        # Geometric constraints
        self._add_geometric_constraints(problem)
        
        self.logger.debug(f"Added {len(self.constraints)} constraint groups to CP-SAT model")
    
    def _add_delay_charge_constraints(self, problem: OptimizationProblem):
        """Add per-delay charge limit constraints"""
        # Group charge variables by delay
        charge_vars = {name: var for name, var in self.variables.items() if 'charge_' in name}
        delay_vars = {name: var for name, var in self.variables.items() if 'delay_' in name}
        
        # Get hole IDs
        hole_ids = set()
        for name in charge_vars.keys():
            hole_id = name.replace('charge_', '')
            hole_ids.add(hole_id)
        
        # For each possible delay value, limit total charge
        delay_values = list(range(0, 1001, self.config.delay_discretization))
        max_charge_per_delay = 200  # kg (from safety config)
        
        for delay_val in delay_values:
            # Create boolean variables for holes assigned to this delay
            delay_indicators = []
            charge_contributions = []
            
            for hole_id in hole_ids:
                delay_var = delay_vars.get(f'delay_{hole_id}')
                charge_var = charge_vars.get(f'charge_{hole_id}')
                
                if delay_var is not None and charge_var is not None:
                    # Boolean indicator: is this hole assigned to this delay?
                    indicator = self.model.NewBoolVar(f'delay_{delay_val}_hole_{hole_id}')
                    
                    # indicator == 1 iff delay_var == delay_val
                    self.model.Add(delay_var == delay_val).OnlyEnforceIf(indicator)
                    self.model.Add(delay_var != delay_val).OnlyEnforceIf(indicator.Not())
                    
                    delay_indicators.append(indicator)
                    
                    # Charge contribution if assigned to this delay
                    charge_contrib = self.model.NewIntVar(0, int(max_charge_per_delay), 
                                                        f'charge_contrib_{delay_val}_{hole_id}')
                    
                    # charge_contrib = charge_var * indicator
                    self.model.Add(charge_contrib == charge_var).OnlyEnforceIf(indicator)
                    self.model.Add(charge_contrib == 0).OnlyEnforceIf(indicator.Not())
                    
                    charge_contributions.append(charge_contrib)
            
            # Total charge for this delay must not exceed limit
            if charge_contributions:
                total_charge = sum(charge_contributions)
                self.model.Add(total_charge <= int(max_charge_per_delay * self.config.charge_discretization))
                
                constraint_name = f'delay_{delay_val}_charge_limit'
                self.constraints[constraint_name] = total_charge
    
    def _add_ppv_constraints(self, problem: OptimizationProblem):
        """Add simplified PPV constraints for CP-SAT"""
        # For CP-SAT, we use simplified linear PPV approximations
        # This is a placeholder - full PPV calculation would be done in post-processing
        
        charge_vars = {name: var for name, var in self.variables.items() if 'charge_' in name}
        
        # Simple constraint: limit maximum single charge to control PPV
        max_single_charge = 50  # kg
        
        for name, charge_var in charge_vars.items():
            self.model.Add(charge_var <= int(max_single_charge * self.config.charge_discretization))
            
        self.constraints['max_single_charge'] = max_single_charge
    
    def _add_powder_factor_constraints(self, problem: OptimizationProblem):
        """Add powder factor constraints"""
        charge_vars = {name: var for name, var in self.variables.items() if 'charge_' in name}
        
        # Simple total charge limits based on powder factor
        total_charge = sum(charge_vars.values())
        
        # Assuming typical rock volume and density
        typical_rock_volume = 1000.0  # m³
        typical_rock_density = 2.7    # t/m³
        total_rock_mass = typical_rock_volume * typical_rock_density
        
        min_powder_factor = 0.1  # kg/t
        max_powder_factor = 1.5  # kg/t
        
        min_total_charge = int(min_powder_factor * total_rock_mass * self.config.charge_discretization)
        max_total_charge = int(max_powder_factor * total_rock_mass * self.config.charge_discretization)
        
        self.model.Add(total_charge >= min_total_charge)
        self.model.Add(total_charge <= max_total_charge)
        
        self.constraints['powder_factor_limits'] = (min_total_charge, max_total_charge)
    
    def _add_geometric_constraints(self, problem: OptimizationProblem):
        """Add geometric constraints (simplified for CP-SAT)"""
        # Position offset constraints are handled by variable bounds
        # More complex geometric constraints would require custom propagators
        pass
    
    def _set_objective(self, problem: OptimizationProblem):
        """Set objective function for CP-SAT"""
        # For CP-SAT, we need to linearize the objective
        # This is a simplified version - full objective evaluation happens in post-processing
        
        charge_vars = {name: var for name, var in self.variables.items() if 'charge_' in name}
        
        # Simple objective: minimize total charge (cost proxy)
        total_charge = sum(charge_vars.values())
        
        # Scale objective to integer
        scaled_objective = total_charge * self.config.objective_scale_factor
        
        self.model.Minimize(scaled_objective)
        
        self.logger.debug("Set linearized objective for CP-SAT")
    
    def _configure_solver(self):
        """Configure CP-SAT solver parameters"""
        self.solver.parameters.max_time_in_seconds = self.config.max_time_seconds
        self.solver.parameters.num_search_workers = self.config.num_search_workers
        self.solver.parameters.log_search_progress = self.config.log_search_progress
        
        # Enable solution enumeration if requested
        if self.config.enumerate_all_solutions:
            self.solver.parameters.enumerate_all_solutions = True
        
        self.logger.debug("Configured CP-SAT solver parameters")
    
    def _solve(self, 
              problem: OptimizationProblem,
              initial_plan: Optional[BlastPlan] = None) -> OptimizationResult:
        """Solve the CP-SAT model"""
        
        # Set up solution callback if enumerating solutions
        callback = None
        if self.config.enumerate_all_solutions:
            callback = CPSATSolutionCallback(self.variables, self.config.max_solutions)
        
        # Solve
        if callback:
            status = self.solver.SearchForAllSolutions(self.model, callback)
        else:
            status = self.solver.Solve(self.model)
        
        # Process results
        result = OptimizationResult(algorithm_used="cp_sat")
        
        if status == cp_model.OPTIMAL:
            result.status = OptimizationStatus.COMPLETED
            result.converged = True
            result.best_plan = self._extract_solution(problem)
            result.objective_value = self.solver.ObjectiveValue() / self.config.objective_scale_factor
            
        elif status == cp_model.FEASIBLE:
            result.status = OptimizationStatus.COMPLETED
            result.converged = False
            result.best_plan = self._extract_solution(problem)
            result.objective_value = self.solver.ObjectiveValue() / self.config.objective_scale_factor
            
        elif status == cp_model.INFEASIBLE:
            result.status = OptimizationStatus.FAILED
            result.constraint_violations = ["Problem is infeasible"]
            
        elif status == cp_model.MODEL_INVALID:
            result.status = OptimizationStatus.FAILED
            result.constraint_violations = ["Model is invalid"]
            
        else:
            result.status = OptimizationStatus.TIMEOUT
        
        # Add solver statistics
        result.iterations = self.solver.NumBranches()
        result.solve_time_seconds = self.solver.WallTime()
        
        # Extract alternative solutions if available
        if callback and callback.solutions:
            result.alternative_plans = self._extract_alternative_solutions(problem, callback)
        
        return result
    
    def _extract_solution(self, problem: OptimizationProblem) -> BlastPlan:
        """Extract blast plan from CP-SAT solution"""
        
        # Get hole pattern from problem
        site_data = problem.site_data
        hole_pattern = site_data.get('hole_pattern', [])
        
        # Create holes with optimized parameters
        optimized_holes = []
        
        for hole in hole_pattern:
            # Extract optimized values
            charge_var = self.variables.get(f'charge_{hole.hole_id}')
            delay_var = self.variables.get(f'delay_{hole.hole_id}')
            offset_x_var = self.variables.get(f'offset_x_{hole.hole_id}')
            offset_y_var = self.variables.get(f'offset_y_{hole.hole_id}')
            
            # Convert discrete values back to continuous
            charge_kg = (self.solver.Value(charge_var) * self.config.charge_discretization 
                        if charge_var is not None else hole.charge_kg)
            delay_ms = self.solver.Value(delay_var) if delay_var is not None else hole.delay_ms
            offset_x = (self.solver.Value(offset_x_var) * 0.1 
                       if offset_x_var is not None else hole.position_offset_x)
            offset_y = (self.solver.Value(offset_y_var) * 0.1 
                       if offset_y_var is not None else hole.position_offset_y)
            
            # Create optimized hole
            optimized_hole = DrillHole(
                hole_id=hole.hole_id,
                coordinates=hole.coordinates,
                depth=hole.depth,
                diameter=hole.diameter,
                charge_kg=charge_kg,
                delay_ms=delay_ms,
                position_offset_x=offset_x,
                position_offset_y=offset_y,
                explosive_type=hole.explosive_type
            )
            
            optimized_holes.append(optimized_hole)
        
        # Create blast plan
        blast_plan = BlastPlan(
            plan_id=f"{problem.problem_id}_cpsat_solution",
            site_id=problem.site_data.get('site_id', 'unknown'),
            holes=optimized_holes,
            optimization_algorithm="cp_sat"
        )
        
        # Calculate totals
        blast_plan.calculate_totals()
        
        return blast_plan
    
    def _extract_alternative_solutions(self, 
                                     problem: OptimizationProblem,
                                     callback: CPSATSolutionCallback) -> List[BlastPlan]:
        """Extract alternative solutions from callback"""
        alternative_plans = []
        
        for i, solution in enumerate(callback.solutions[1:], 1):  # Skip first (best) solution
            # This would extract each alternative solution
            # For now, return empty list
            pass
        
        return alternative_plans
    
    def get_solver_statistics(self) -> Dict[str, Any]:
        """Get detailed solver statistics"""
        if not self.solver:
            return {}
        
        return {
            "status": self.solver.StatusName(),
            "objective_value": self.solver.ObjectiveValue(),
            "best_objective_bound": self.solver.BestObjectiveBound(),
            "num_branches": self.solver.NumBranches(),
            "num_conflicts": self.solver.NumConflicts(),
            "wall_time": self.solver.WallTime(),
            "user_time": self.solver.UserTime(),
            "deterministic_time": self.solver.DeterministicTime()
        }


def create_cp_sat_optimizer(safety_config: Any = None) -> CPSATOptimizer:
    """
    Factory function to create CP-SAT optimizer with default configuration.
    
    Args:
        safety_config: Safety configuration for constraints
        
    Returns:
        Configured CP-SAT optimizer
    """
    config = CPSATConfig()
    
    # Create constraint manager if safety config provided
    constraint_manager = None
    if safety_config:
        constraint_manager = ConstraintManager(safety_config)
    
    return CPSATOptimizer(
        config=config,
        constraint_manager=constraint_manager
    )