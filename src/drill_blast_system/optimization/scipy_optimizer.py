"""
SciPy-based continuous optimizer for drill-and-blast optimization.

This module implements continuous optimization using SciPy algorithms
including differential evolution and SLSQP for gradient-based polishing.
"""

from typing import List, Dict, Tuple, Optional, Any, Callable, Union
import numpy as np
from scipy import optimize
from scipy.optimize import OptimizeResult
import logging
from dataclasses import dataclass
import time
import warnings

from .data_structures import (
    OptimizationProblem, OptimizationResult, OptimizationStatus,
    BlastPlan, DrillHole, DecisionVariable
)
from .formulation import ObjectiveFunction, ConstraintManager


@dataclass
class ScipyConfig:
    """Configuration for SciPy optimizers"""
    
    # Algorithm selection
    primary_algorithm: str = "differential_evolution"  # or "slsqp", "dual_annealing"
    use_polishing: bool = True  # Use SLSQP for polishing DE results
    
    # Differential Evolution parameters
    de_maxiter: int = 1000
    de_popsize: int = 15
    de_mutation: Tuple[float, float] = (0.5, 1.0)
    de_recombination: float = 0.7
    de_seed: Optional[int] = None
    de_atol: float = 1e-6
    de_tol: float = 1e-6
    
    # SLSQP parameters
    slsqp_maxiter: int = 100
    slsqp_ftol: float = 1e-9
    slsqp_eps: float = 1.4901161193847656e-08
    
    # Dual Annealing parameters
    da_maxiter: int = 1000
    da_initial_temp: float = 5230.0
    da_restart_temp_ratio: float = 2e-05
    da_visit: float = 2.62
    da_accept: float = -5.0
    
    # General parameters
    max_time_seconds: float = 300.0
    max_function_evaluations: int = 10000
    constraint_penalty_factor: float = 1000.0
    
    # Convergence monitoring
    convergence_window: int = 50  # Number of iterations to check for convergence
    convergence_threshold: float = 1e-6
    
    # Bounds handling
    enforce_bounds: bool = True
    bounds_penalty_factor: float = 1e6


class ConvergenceMonitor:
    """Monitor convergence during optimization"""
    
    def __init__(self, window_size: int = 50, threshold: float = 1e-6):
        self.window_size = window_size
        self.threshold = threshold
        self.objective_history = []
        self.iteration_count = 0
        
    def update(self, objective_value: float) -> bool:
        """
        Update with new objective value and check convergence.
        
        Args:
            objective_value: Current objective function value
            
        Returns:
            True if converged, False otherwise
        """
        self.objective_history.append(objective_value)
        self.iteration_count += 1
        
        # Keep only recent history
        if len(self.objective_history) > self.window_size:
            self.objective_history.pop(0)
        
        # Check convergence if we have enough history
        if len(self.objective_history) >= self.window_size:
            recent_values = np.array(self.objective_history[-self.window_size:])
            
            # Check if improvement is below threshold
            if len(recent_values) > 1:
                improvement = np.abs(recent_values[-1] - recent_values[0])
                relative_improvement = improvement / (np.abs(recent_values[0]) + 1e-12)
                
                return relative_improvement < self.threshold
        
        return False
    
    def reset(self):
        """Reset convergence monitoring"""
        self.objective_history = []
        self.iteration_count = 0


class ScipyOptimizer:
    """SciPy-based continuous optimizer for blast optimization"""
    
    def __init__(self, 
                 config: ScipyConfig = None,
                 objective_function: ObjectiveFunction = None,
                 constraint_manager: ConstraintManager = None):
        self.config = config or ScipyConfig()
        self.objective_function = objective_function
        self.constraint_manager = constraint_manager
        self.logger = logging.getLogger(__name__ + ".ScipyOptimizer")
        
        # Optimization state
        self.problem = None
        self.bounds = None
        self.convergence_monitor = ConvergenceMonitor(
            self.config.convergence_window,
            self.config.convergence_threshold
        )
        
        # Statistics
        self.function_evaluations = 0
        self.constraint_evaluations = 0
        self.start_time = 0.0
        
    def optimize(self, 
                problem: OptimizationProblem,
                initial_plan: Optional[BlastPlan] = None) -> OptimizationResult:
        """
        Optimize blast plan using SciPy algorithms.
        
        Args:
            problem: Optimization problem formulation
            initial_plan: Optional initial blast plan for warm start
            
        Returns:
            Optimization result with best solution found
        """
        self.logger.info(f"Starting SciPy optimization for problem {problem.problem_id}")
        self.start_time = time.time()
        self.problem = problem
        
        try:
            # Prepare optimization problem
            self._prepare_problem(problem)
            
            # Get initial solution
            x0 = self._get_initial_solution(problem, initial_plan)
            
            # Run primary optimization algorithm
            result = self._run_primary_optimization(x0)
            
            # Polish with SLSQP if requested and feasible
            if self.config.use_polishing and result.success:
                result = self._polish_solution(result.x, result)
            
            # Convert to optimization result
            opt_result = self._create_optimization_result(result, problem)
            
            self.logger.info(f"SciPy optimization completed in {opt_result.solve_time_seconds:.2f}s, "
                           f"status: {opt_result.status}")
            
            return opt_result
            
        except Exception as e:
            self.logger.error(f"SciPy optimization failed: {e}")
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                algorithm_used=f"scipy_{self.config.primary_algorithm}",
                solve_time_seconds=time.time() - self.start_time
            )
    
    def _prepare_problem(self, problem: OptimizationProblem):
        """Prepare optimization problem for SciPy"""
        # Extract bounds from decision variables
        self.bounds = []
        for var in problem.variables:
            self.bounds.append((var.lower_bound, var.upper_bound))
        
        self.bounds = np.array(self.bounds)
        
        # Reset statistics
        self.function_evaluations = 0
        self.constraint_evaluations = 0
        self.convergence_monitor.reset()
        
        self.logger.debug(f"Prepared problem with {len(problem.variables)} variables")
    
    def _get_initial_solution(self, 
                            problem: OptimizationProblem,
                            initial_plan: Optional[BlastPlan] = None) -> np.ndarray:
        """Get initial solution vector"""
        
        if initial_plan and len(initial_plan.holes) > 0:
            # Extract from initial plan
            x0 = []
            hole_dict = {hole.hole_id: hole for hole in initial_plan.holes}
            
            for var in problem.variables:
                if var.name.startswith('charge_'):
                    hole_id = var.name.replace('charge_', '')
                    hole = hole_dict.get(hole_id)
                    x0.append(hole.charge_kg if hole else var.initial_value or 25.0)
                    
                elif var.name.startswith('delay_'):
                    hole_id = var.name.replace('delay_', '')
                    hole = hole_dict.get(hole_id)
                    x0.append(hole.delay_ms if hole else var.initial_value or 0.0)
                    
                elif var.name.startswith('offset_x_'):
                    hole_id = var.name.replace('offset_x_', '')
                    hole = hole_dict.get(hole_id)
                    x0.append(hole.position_offset_x if hole else var.initial_value or 0.0)
                    
                elif var.name.startswith('offset_y_'):
                    hole_id = var.name.replace('offset_y_', '')
                    hole = hole_dict.get(hole_id)
                    x0.append(hole.position_offset_y if hole else var.initial_value or 0.0)
                    
                else:
                    x0.append(var.initial_value or (var.lower_bound + var.upper_bound) / 2.0)
            
            x0 = np.array(x0)
        else:
            # Use problem's initial solution
            x0 = problem.get_initial_solution()
        
        # Ensure bounds are satisfied
        x0 = np.clip(x0, self.bounds[:, 0], self.bounds[:, 1])
        
        return x0
    
    def _run_primary_optimization(self, x0: np.ndarray) -> OptimizeResult:
        """Run primary optimization algorithm"""
        
        if self.config.primary_algorithm == "differential_evolution":
            return self._run_differential_evolution(x0)
        elif self.config.primary_algorithm == "slsqp":
            return self._run_slsqp(x0)
        elif self.config.primary_algorithm == "dual_annealing":
            return self._run_dual_annealing(x0)
        else:
            raise ValueError(f"Unknown algorithm: {self.config.primary_algorithm}")
    
    def _run_differential_evolution(self, x0: np.ndarray) -> OptimizeResult:
        """Run differential evolution optimization"""
        
        self.logger.debug("Running differential evolution")
        
        # Suppress warnings for cleaner output
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            result = optimize.differential_evolution(
                func=self._objective_function_wrapper,
                bounds=self.bounds,
                maxiter=self.config.de_maxiter,
                popsize=self.config.de_popsize,
                mutation=self.config.de_mutation,
                recombination=self.config.de_recombination,
                seed=self.config.de_seed,
                atol=self.config.de_atol,
                tol=self.config.de_tol,
                callback=self._optimization_callback,
                x0=x0 if len(x0) == len(self.bounds) else None,
                workers=1  # Single threaded for now
            )
        
        return result
    
    def _run_slsqp(self, x0: np.ndarray) -> OptimizeResult:
        """Run SLSQP optimization"""
        
        self.logger.debug("Running SLSQP")
        
        # Create constraints for SLSQP
        constraints = self._create_slsqp_constraints()
        
        result = optimize.minimize(
            fun=self._objective_function_wrapper,
            x0=x0,
            method='SLSQP',
            bounds=self.bounds,
            constraints=constraints,
            options={
                'maxiter': self.config.slsqp_maxiter,
                'ftol': self.config.slsqp_ftol,
                'eps': self.config.slsqp_eps,
                'disp': False
            },
            callback=self._optimization_callback
        )
        
        return result
    
    def _run_dual_annealing(self, x0: np.ndarray) -> OptimizeResult:
        """Run dual annealing optimization"""
        
        self.logger.debug("Running dual annealing")
        
        result = optimize.dual_annealing(
            func=self._objective_function_wrapper,
            bounds=self.bounds,
            maxiter=self.config.da_maxiter,
            initial_temp=self.config.da_initial_temp,
            restart_temp_ratio=self.config.da_restart_temp_ratio,
            visit=self.config.da_visit,
            accept=self.config.da_accept,
            callback=self._optimization_callback,
            x0=x0,
            seed=self.config.de_seed
        )
        
        return result
    
    def _polish_solution(self, 
                        x: np.ndarray,
                        primary_result: OptimizeResult) -> OptimizeResult:
        """Polish solution using SLSQP"""
        
        self.logger.debug("Polishing solution with SLSQP")
        
        try:
            constraints = self._create_slsqp_constraints()
            
            polish_result = optimize.minimize(
                fun=self._objective_function_wrapper,
                x0=x,
                method='SLSQP',
                bounds=self.bounds,
                constraints=constraints,
                options={
                    'maxiter': min(self.config.slsqp_maxiter, 50),  # Fewer iterations for polishing
                    'ftol': self.config.slsqp_ftol,
                    'eps': self.config.slsqp_eps,
                    'disp': False
                }
            )
            
            # Use polished result if it's better
            if polish_result.success and polish_result.fun < primary_result.fun:
                self.logger.debug(f"Polishing improved objective from {primary_result.fun:.6f} to {polish_result.fun:.6f}")
                return polish_result
            else:
                self.logger.debug("Polishing did not improve solution")
                return primary_result
                
        except Exception as e:
            self.logger.warning(f"Polishing failed: {e}")
            return primary_result
    
    def _objective_function_wrapper(self, x: np.ndarray) -> float:
        """Wrapper for objective function evaluation"""
        
        self.function_evaluations += 1
        
        try:
            # Check time limit
            if time.time() - self.start_time > self.config.max_time_seconds:
                return 1e12  # Large penalty for timeout
            
            # Check function evaluation limit
            if self.function_evaluations > self.config.max_function_evaluations:
                return 1e12
            
            # Enforce bounds with penalty
            if self.config.enforce_bounds:
                penalty = 0.0
                for i, (lower, upper) in enumerate(self.bounds):
                    if x[i] < lower:
                        penalty += self.config.bounds_penalty_factor * (lower - x[i]) ** 2
                    elif x[i] > upper:
                        penalty += self.config.bounds_penalty_factor * (x[i] - upper) ** 2
                
                if penalty > 0:
                    return penalty
            
            # Convert solution vector to blast plan
            blast_plan = self._solution_to_blast_plan(x)
            
            # Evaluate objective function
            if self.objective_function:
                objectives = self.objective_function.evaluate(blast_plan, self.problem.site_data)
                objective_value = objectives.get("total", sum(objectives.values()))
            else:
                # Simple default objective: minimize total charge
                objective_value = blast_plan.total_charge_kg
            
            # Add constraint penalties
            if self.constraint_manager:
                constraint_violations = self.constraint_manager.evaluate_constraints(
                    blast_plan, self.problem.site_data
                )
                
                constraint_penalty = 0.0
                for violation_name, violation_value in constraint_violations.items():
                    if violation_value > 0:
                        constraint_penalty += self.config.constraint_penalty_factor * violation_value ** 2
                
                objective_value += constraint_penalty
            
            return objective_value
            
        except Exception as e:
            self.logger.warning(f"Objective function evaluation failed: {e}")
            return 1e12  # Large penalty for evaluation errors
    
    def _create_slsqp_constraints(self) -> List[Dict[str, Any]]:
        """Create constraint definitions for SLSQP"""
        constraints = []
        
        # This would create constraint functions for SLSQP
        # For now, we rely on penalty methods in the objective function
        
        return constraints
    
    def _optimization_callback(self, x: np.ndarray, convergence: float = None) -> bool:
        """Callback function called during optimization"""
        
        try:
            # Evaluate current objective
            current_objective = self._objective_function_wrapper(x)
            
            # Update convergence monitor
            converged = self.convergence_monitor.update(current_objective)
            
            # Check time limit
            elapsed_time = time.time() - self.start_time
            if elapsed_time > self.config.max_time_seconds:
                self.logger.debug(f"Time limit reached: {elapsed_time:.2f}s")
                return True  # Stop optimization
            
            # Check convergence
            if converged:
                self.logger.debug(f"Convergence detected at iteration {self.convergence_monitor.iteration_count}")
                return True  # Stop optimization
            
            # Log progress periodically
            if self.convergence_monitor.iteration_count % 100 == 0:
                self.logger.debug(f"Iteration {self.convergence_monitor.iteration_count}, "
                                f"objective: {current_objective:.6f}, "
                                f"evaluations: {self.function_evaluations}")
            
            return False  # Continue optimization
            
        except Exception as e:
            self.logger.warning(f"Callback error: {e}")
            return False
    
    def _solution_to_blast_plan(self, x: np.ndarray) -> BlastPlan:
        """Convert solution vector to blast plan"""
        
        # Get hole pattern from problem
        site_data = self.problem.site_data
        hole_pattern = site_data.get('hole_pattern', [])
        
        # Create holes with optimized parameters
        optimized_holes = []
        
        # Create mapping from variable names to values
        var_values = {}
        for i, var in enumerate(self.problem.variables):
            var_values[var.name] = x[i]
        
        for hole in hole_pattern:
            # Extract values for this hole
            hole_values = {}
            
            # Create optimized hole
            optimized_hole = DrillHole(
                hole_id=hole.hole_id,
                coordinates=hole.coordinates,
                depth=hole.depth,
                diameter=hole.diameter,
                charge_kg=var_values.get(f'charge_{hole.hole_id}', hole.charge_kg),
                delay_ms=int(var_values.get(f'delay_{hole.hole_id}', hole.delay_ms)),
                position_offset_x=var_values.get(f'offset_x_{hole.hole_id}', hole.position_offset_x),
                position_offset_y=var_values.get(f'offset_y_{hole.hole_id}', hole.position_offset_y),
                explosive_type=hole.explosive_type
            )
            
            optimized_holes.append(optimized_hole)
        
        # Create blast plan
        blast_plan = BlastPlan(
            plan_id=f"{self.problem.problem_id}_scipy_solution",
            site_id=self.problem.site_data.get('site_id', 'unknown'),
            holes=optimized_holes,
            optimization_algorithm=f"scipy_{self.config.primary_algorithm}"
        )
        
        # Calculate totals
        blast_plan.calculate_totals()
        
        return blast_plan
    
    def _create_optimization_result(self, 
                                  scipy_result: OptimizeResult,
                                  problem: OptimizationProblem) -> OptimizationResult:
        """Convert SciPy result to optimization result"""
        
        # Determine status
        if scipy_result.success:
            status = OptimizationStatus.COMPLETED
        elif hasattr(scipy_result, 'message') and 'time' in scipy_result.message.lower():
            status = OptimizationStatus.TIMEOUT
        else:
            status = OptimizationStatus.FAILED
        
        # Extract best solution
        best_plan = None
        if hasattr(scipy_result, 'x') and scipy_result.x is not None:
            best_plan = self._solution_to_blast_plan(scipy_result.x)
        
        # Create result
        result = OptimizationResult(
            best_plan=best_plan,
            objective_value=scipy_result.fun if hasattr(scipy_result, 'fun') else float('inf'),
            algorithm_used=f"scipy_{self.config.primary_algorithm}",
            status=status,
            solve_time_seconds=time.time() - self.start_time,
            iterations=getattr(scipy_result, 'nit', self.convergence_monitor.iteration_count),
            function_evaluations=self.function_evaluations,
            converged=scipy_result.success,
            objective_history=self.convergence_monitor.objective_history.copy()
        )
        
        return result
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the optimization algorithm"""
        return {
            "primary_algorithm": self.config.primary_algorithm,
            "use_polishing": self.config.use_polishing,
            "max_iterations": getattr(self.config, f"{self.config.primary_algorithm.split('_')[0]}_maxiter", 1000),
            "convergence_threshold": self.config.convergence_threshold,
            "function_evaluations": self.function_evaluations,
            "constraint_evaluations": self.constraint_evaluations
        }


def create_scipy_optimizer(algorithm: str = "differential_evolution",
                          safety_config: Any = None) -> ScipyOptimizer:
    """
    Factory function to create SciPy optimizer with specified algorithm.
    
    Args:
        algorithm: Algorithm to use ('differential_evolution', 'slsqp', 'dual_annealing')
        safety_config: Safety configuration for constraints
        
    Returns:
        Configured SciPy optimizer
    """
    config = ScipyConfig(primary_algorithm=algorithm)
    
    # Create constraint manager if safety config provided
    constraint_manager = None
    if safety_config:
        constraint_manager = ConstraintManager(safety_config)
    
    return ScipyOptimizer(
        config=config,
        constraint_manager=constraint_manager
    )