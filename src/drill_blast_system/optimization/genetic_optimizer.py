"""
Genetic Algorithm optimizer for drill-and-blast optimization.

This module implements a genetic algorithm optimizer using PyGAD for global
optimization of drill-and-blast patterns. It includes custom crossover and
mutation operators designed for blast pattern optimization, population diversity
management, and multi-objective optimization capabilities.

Key Features:
- Custom genetic operators for blast pattern variables (charges, delays, positions)
- Multi-objective optimization with Pareto front management
- Population diversity tracking and convergence detection
- Integration with physics models and safety constraints
- Performance benchmarking and algorithm comparison capabilities

Usage:
    # Basic usage
    config = GeneticConfig(population_size=50, num_generations=100)
    optimizer = GeneticOptimizer(config=config)
    result = optimizer.optimize(problem)
    
    # With custom operators and multi-objective optimization
    config = GeneticConfig(
        use_pareto_ranking=True,
        crossover_type="blast_custom",
        mutation_type="blast_custom"
    )
    optimizer = create_genetic_optimizer(use_pareto=True, population_size=100)
    result = optimizer.optimize(problem)

Requirements:
- PyGAD library for genetic algorithm implementation
- NumPy for numerical operations
- Optional: ObjectiveFunction and ConstraintManager for full functionality
"""

from typing import List, Dict, Tuple, Optional, Any, Union
import numpy as np
import logging
from dataclasses import dataclass
import time

try:
    import pygad
    PYGAD_AVAILABLE = True
except ImportError:
    PYGAD_AVAILABLE = False
    pygad = None

from .data_structures import (
    OptimizationProblem, OptimizationResult, OptimizationStatus,
    BlastPlan, DrillHole
)
from .formulation import ObjectiveFunction, ConstraintManager


@dataclass
class GeneticConfig:
    """Configuration for genetic algorithm optimizer"""
    population_size: int = 50
    num_generations: int = 100
    num_parents_mating: int = 20
    parent_selection_type: str = "tournament"
    tournament_size: int = 3
    crossover_type: str = "uniform"
    mutation_type: str = "adaptive"
    mutation_probability: float = 0.1
    keep_elitism: int = 5
    max_stagnation_generations: int = 20
    convergence_threshold: float = 1e-6
    constraint_penalty_factor: float = 1000.0
    use_pareto_ranking: bool = False
    random_seed: Optional[int] = None
    max_time_seconds: float = 300.0


class BlastGeneticOperators:
    """Custom genetic operators for blast pattern optimization"""
    
    @staticmethod
    def blast_crossover(parents: np.ndarray, offspring_size: Tuple[int, int], ga_instance) -> np.ndarray:
        """
        Custom crossover operator for blast patterns.
        Preserves hole groupings and maintains feasible charge/delay combinations.
        """
        offspring = np.zeros(offspring_size)
        
        for k in range(offspring_size[0]):
            # Select two parents
            parent1_idx = k % parents.shape[0]
            parent2_idx = (k + 1) % parents.shape[0]
            parent1 = parents[parent1_idx]
            parent2 = parents[parent2_idx]
            
            # Determine variables per hole (charge, delay, offset_x, offset_y)
            vars_per_hole = 4
            num_holes = len(parent1) // vars_per_hole
            
            # Hole-wise crossover: randomly select holes from each parent
            for hole_idx in range(num_holes):
                start_idx = hole_idx * vars_per_hole
                end_idx = start_idx + vars_per_hole
                
                if np.random.random() < 0.5:
                    offspring[k, start_idx:end_idx] = parent1[start_idx:end_idx]
                else:
                    offspring[k, start_idx:end_idx] = parent2[start_idx:end_idx]
        
        return offspring
    
    @staticmethod
    def blast_mutation(offspring: np.ndarray, ga_instance) -> np.ndarray:
        """
        Custom mutation operator for blast patterns.
        Applies different mutation strategies for different variable types.
        """
        mutation_probability = ga_instance.mutation_probability
        
        for solution_idx in range(offspring.shape[0]):
            vars_per_hole = 4
            num_holes = offspring.shape[1] // vars_per_hole
            
            for hole_idx in range(num_holes):
                start_idx = hole_idx * vars_per_hole
                
                # Mutate charge (continuous)
                if np.random.random() < mutation_probability:
                    charge_idx = start_idx
                    current_charge = offspring[solution_idx, charge_idx]
                    # Add Gaussian noise (±10% of current value)
                    noise = np.random.normal(0, 0.1 * current_charge)
                    offspring[solution_idx, charge_idx] = max(0, current_charge + noise)
                
                # Mutate delay (discrete)
                if np.random.random() < mutation_probability:
                    delay_idx = start_idx + 1
                    # Random delay increment/decrement
                    delay_change = np.random.choice([-25, 0, 25])
                    offspring[solution_idx, delay_idx] = max(0, 
                        offspring[solution_idx, delay_idx] + delay_change)
                
                # Mutate position offsets (continuous)
                for offset_idx in [start_idx + 2, start_idx + 3]:
                    if np.random.random() < mutation_probability:
                        # Small position adjustment
                        noise = np.random.normal(0, 0.1)  # ±0.1m standard deviation
                        offspring[solution_idx, offset_idx] += noise
        
        return offspring


class ParetoFrontManager:
    """Manages Pareto front for multi-objective optimization"""
    
    def __init__(self):
        self.pareto_solutions = []
        self.pareto_objectives = []
    
    def update_pareto_front(self, solutions: np.ndarray, objectives: np.ndarray):
        """Update Pareto front with new solutions"""
        for i, (solution, obj) in enumerate(zip(solutions, objectives)):
            if self._is_pareto_optimal(obj, self.pareto_objectives):
                # Remove dominated solutions
                self._remove_dominated_solutions(obj)
                # Add new solution
                self.pareto_solutions.append(solution.copy())
                self.pareto_objectives.append(obj.copy())
    
    def _is_pareto_optimal(self, objective: np.ndarray, pareto_objectives: List[np.ndarray]) -> bool:
        """Check if solution is Pareto optimal"""
        if not pareto_objectives:
            return True
        
        for pareto_obj in pareto_objectives:
            # Check if current solution dominates any Pareto solution
            if np.all(objective <= pareto_obj) and np.any(objective < pareto_obj):
                return True
            # Check if any Pareto solution dominates current solution
            if np.all(pareto_obj <= objective) and np.any(pareto_obj < objective):
                return False
        
        return True
    
    def _remove_dominated_solutions(self, new_objective: np.ndarray):
        """Remove solutions dominated by new objective"""
        non_dominated = []
        non_dominated_obj = []
        
        for sol, obj in zip(self.pareto_solutions, self.pareto_objectives):
            # Keep solution if not dominated by new objective
            if not (np.all(new_objective <= obj) and np.any(new_objective < obj)):
                non_dominated.append(sol)
                non_dominated_obj.append(obj)
        
        self.pareto_solutions = non_dominated
        self.pareto_objectives = non_dominated_obj
    
    def get_best_solutions(self, max_solutions: int = 5) -> List[np.ndarray]:
        """Get best solutions from Pareto front"""
        if len(self.pareto_solutions) <= max_solutions:
            return self.pareto_solutions.copy()
        
        # Select diverse solutions from Pareto front
        indices = np.linspace(0, len(self.pareto_solutions) - 1, max_solutions, dtype=int)
        return [self.pareto_solutions[i] for i in indices]


class GeneticOptimizer:
    """Genetic algorithm optimizer for blast optimization"""
    
    def __init__(self, 
                 config: GeneticConfig = None,
                 objective_function: Optional[ObjectiveFunction] = None,
                 constraint_manager: Optional[ConstraintManager] = None):
        if not PYGAD_AVAILABLE:
            raise ImportError("PyGAD is required for genetic algorithm optimization. "
                            "Install with: pip install pygad")
        
        self.config = config or GeneticConfig()
        self.objective_function = objective_function
        self.constraint_manager = constraint_manager
        self.logger = logging.getLogger(__name__ + ".GeneticOptimizer")
        
        # Optimization state
        self.problem = None
        self.ga_instance = None
        
        # Statistics for performance benchmarking
        self.generation_count = 0
        self.best_fitness_history = []
        self.diversity_history = []
        self.start_time = 0.0
        
        # Multi-objective optimization
        self.pareto_manager = ParetoFrontManager() if self.config.use_pareto_ranking else None
        
        # Convergence tracking
        self.stagnation_count = 0
        self.last_best_fitness = float('-inf')
        
    def optimize(self, 
                problem: OptimizationProblem,
                initial_plan: Optional[BlastPlan] = None) -> OptimizationResult:
        """Optimize blast plan using genetic algorithm"""
        self.logger.info(f"Starting genetic algorithm optimization for problem {problem.problem_id}")
        self.start_time = time.time()
        self.problem = problem
        
        try:
            # Create initial population
            initial_population = self._create_initial_population(problem, initial_plan)
            
            # Configure PyGAD instance
            self._configure_pygad(problem, initial_population)
            
            # Run optimization
            self.ga_instance.run()
            
            # Extract results
            result = self._extract_results(problem)
            
            self.logger.info(f"Genetic algorithm completed in {result.solve_time_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Genetic algorithm optimization failed: {e}")
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                algorithm_used="genetic_algorithm",
                solve_time_seconds=time.time() - self.start_time
            )
    
    def _create_initial_population(self, 
                                 problem: OptimizationProblem,
                                 initial_plan: Optional[BlastPlan] = None) -> np.ndarray:
        """Create initial population for genetic algorithm"""
        
        bounds = np.array([(var.lower_bound, var.upper_bound) for var in problem.variables])
        population = np.zeros((self.config.population_size, len(problem.variables)))
        
        # Include initial plan if provided
        if initial_plan is not None:
            population[0] = self._blast_plan_to_solution_vector(initial_plan, problem)
            start_idx = 1
        else:
            start_idx = 0
        
        # Generate random solutions for remaining population
        for i in range(start_idx, self.config.population_size):
            for j, var in enumerate(problem.variables):
                if var.var_type == "integer" and var.discrete_values:
                    # Sample from discrete values
                    population[i, j] = np.random.choice(var.discrete_values)
                else:
                    # Continuous or integer with bounds
                    population[i, j] = np.random.uniform(var.lower_bound, var.upper_bound)
        
        self.logger.debug(f"Created initial population of {self.config.population_size} solutions")
        return population
    
    def _blast_plan_to_solution_vector(self, blast_plan: BlastPlan, problem: OptimizationProblem) -> np.ndarray:
        """Convert blast plan to solution vector"""
        solution = np.zeros(len(problem.variables))
        
        # Map hole parameters to decision variables
        vars_per_hole = 4  # charge, delay, offset_x, offset_y
        for i, hole in enumerate(blast_plan.holes):
            base_idx = i * vars_per_hole
            if base_idx + 3 < len(solution):
                solution[base_idx] = hole.charge_kg
                solution[base_idx + 1] = hole.delay_ms
                solution[base_idx + 2] = hole.position_offset_x
                solution[base_idx + 3] = hole.position_offset_y
        
        return solution
    
    def _solution_vector_to_blast_plan(self, solution: np.ndarray, problem: OptimizationProblem) -> BlastPlan:
        """Convert solution vector to blast plan"""
        site_data = problem.site_data
        hole_pattern = site_data.get('hole_pattern', [])
        
        # Create new holes with optimized parameters
        optimized_holes = []
        vars_per_hole = 4
        
        for i, base_hole in enumerate(hole_pattern):
            base_idx = i * vars_per_hole
            if base_idx + 3 < len(solution):
                optimized_hole = DrillHole(
                    hole_id=base_hole.hole_id,
                    coordinates=base_hole.coordinates,
                    depth=base_hole.depth,
                    diameter=base_hole.diameter,
                    charge_kg=max(0, solution[base_idx]),
                    delay_ms=int(max(0, solution[base_idx + 1])),
                    position_offset_x=solution[base_idx + 2],
                    position_offset_y=solution[base_idx + 3],
                    explosive_type=base_hole.explosive_type
                )
                optimized_holes.append(optimized_hole)
        
        # Create blast plan
        blast_plan = BlastPlan(
            plan_id=f"genetic_opt_{int(time.time())}",
            site_id=site_data.get('site_id', 'unknown'),
            holes=optimized_holes
        )
        blast_plan.calculate_totals()
        
        return blast_plan
    
    def _configure_pygad(self, problem: OptimizationProblem, initial_population: np.ndarray):
        """Configure PyGAD genetic algorithm instance"""
        
        if self.config.random_seed is not None:
            np.random.seed(self.config.random_seed)
        
        # Ensure num_parents_mating is not greater than population size
        num_parents_mating = min(self.config.num_parents_mating, self.config.population_size)
        
        ga_params = {
            'num_generations': self.config.num_generations,
            'num_parents_mating': num_parents_mating,
            'fitness_func': self._fitness_function,
            'initial_population': initial_population,
            'parent_selection_type': self.config.parent_selection_type,
            'keep_elitism': min(self.config.keep_elitism, self.config.population_size // 2),
            'mutation_probability': self.config.mutation_probability,
            'on_generation': self._on_generation_callback,
            'suppress_warnings': True
        }
        
        # Add custom genetic operators for blast optimization
        if self.config.crossover_type == "blast_custom":
            ga_params['crossover_type'] = BlastGeneticOperators.blast_crossover
        else:
            ga_params['crossover_type'] = self.config.crossover_type
        
        if self.config.mutation_type == "blast_custom":
            ga_params['mutation_type'] = BlastGeneticOperators.blast_mutation
        elif self.config.mutation_type == "adaptive":
            ga_params['mutation_type'] = "adaptive"
            # For adaptive mutation, PyGAD expects exactly 2 elements [low, high]
            ga_params['mutation_probability'] = [self.config.mutation_probability * 0.5, self.config.mutation_probability * 1.5]
        else:
            ga_params['mutation_type'] = self.config.mutation_type
        
        if self.config.parent_selection_type == "tournament":
            ga_params['K_tournament'] = self.config.tournament_size
        
        self.ga_instance = pygad.GA(**ga_params)
        
        self.logger.debug("Configured PyGAD genetic algorithm instance")
    
    def _fitness_function(self, ga_instance, solution: np.ndarray, solution_idx: int) -> float:
        """Fitness function for genetic algorithm"""
        
        try:
            # Convert solution vector to blast plan
            blast_plan = self._solution_vector_to_blast_plan(solution, self.problem)
            
            # Evaluate objectives if objective function is available
            if self.objective_function:
                objectives = self.objective_function.evaluate(blast_plan, self.problem.site_data)
                objective_value = objectives.get('total', np.sum(solution))
            else:
                # Fallback: minimize sum of variables (for testing)
                objective_value = np.sum(solution)
            
            # Evaluate constraints if constraint manager is available
            constraint_penalty = 0.0
            if self.constraint_manager:
                violations = self.constraint_manager.evaluate_constraints(blast_plan, self.problem.site_data)
                constraint_penalty = sum(violations.values()) * self.config.constraint_penalty_factor
            
            # Total penalty (minimize)
            total_penalty = objective_value + constraint_penalty
            
            # Convert to fitness (higher is better)
            fitness = 1.0 / (1.0 + total_penalty)
            
            return fitness
            
        except Exception as e:
            self.logger.warning(f"Fitness evaluation failed: {e}")
            return 0.0
    
    def _on_generation_callback(self, ga_instance):
        """Callback called after each generation"""
        
        self.generation_count += 1
        
        # Get current best fitness
        best_fitness = ga_instance.best_solution()[1]
        self.best_fitness_history.append(best_fitness)
        
        # Calculate population diversity
        diversity = self._calculate_diversity(ga_instance.population)
        self.diversity_history.append(diversity)
        
        # Check for convergence
        if self._check_convergence():
            self.logger.info(f"Convergence detected at generation {self.generation_count}")
            # Note: PyGAD doesn't support early stopping, so we continue
        
        # Update Pareto front for multi-objective optimization
        if self.config.use_pareto_ranking and self.pareto_manager:
            # Evaluate all solutions in current population
            objectives = []
            for solution in ga_instance.population:
                blast_plan = self._solution_vector_to_blast_plan(solution, self.problem)
                if self.objective_function:
                    obj = self.objective_function.evaluate(blast_plan, self.problem.site_data)
                    # Use individual objective components for Pareto ranking
                    objectives.append([
                        obj.get('fragmentation_quality', 0),
                        obj.get('total_cost', 0),
                        obj.get('ppv_penalty', 0)
                    ])
                else:
                    objectives.append([np.sum(solution)])
            
            self.pareto_manager.update_pareto_front(ga_instance.population, np.array(objectives))
        
        # Check timeout
        if time.time() - self.start_time > self.config.max_time_seconds:
            self.logger.warning(f"Optimization timeout reached at generation {self.generation_count}")
        
        # Log progress
        if self.generation_count % 10 == 0:
            self.logger.debug(f"Generation {self.generation_count}, "
                            f"best fitness: {best_fitness:.6f}, "
                            f"diversity: {diversity:.4f}")
    
    def _check_convergence(self) -> bool:
        """Check if algorithm has converged"""
        if len(self.best_fitness_history) < self.config.max_stagnation_generations:
            return False
        
        # Check for stagnation
        recent_fitness = self.best_fitness_history[-self.config.max_stagnation_generations:]
        fitness_range = max(recent_fitness) - min(recent_fitness)
        
        # Check if fitness has stagnated
        is_stagnant = fitness_range < self.config.convergence_threshold
        
        if is_stagnant:
            self.stagnation_count += 1
        else:
            self.stagnation_count = 0
        
        return is_stagnant
    
    def _calculate_diversity(self, population: np.ndarray) -> float:
        """Calculate population diversity"""
        if len(population) < 2:
            return 0.0
        
        distances = []
        for i in range(len(population)):
            for j in range(i + 1, len(population)):
                distance = np.linalg.norm(population[i] - population[j])
                distances.append(distance)
        
        return np.mean(distances) if distances else 0.0
    
    def _extract_results(self, problem: OptimizationProblem) -> OptimizationResult:
        """Extract optimization results from genetic algorithm"""
        
        best_solution, best_fitness, _ = self.ga_instance.best_solution()
        
        # Convert fitness back to objective value
        objective_value = (1.0 / best_fitness) - 1.0 if best_fitness > 0 else float('inf')
        
        # Convert best solution to blast plan
        best_blast_plan = self._solution_vector_to_blast_plan(best_solution, problem)
        
        # Determine status
        elapsed_time = time.time() - self.start_time
        if elapsed_time > self.config.max_time_seconds:
            status = OptimizationStatus.TIMEOUT
        elif self._check_convergence():
            status = OptimizationStatus.COMPLETED
        else:
            status = OptimizationStatus.COMPLETED
        
        # Get alternative solutions from Pareto front if available
        alternative_plans = []
        if self.config.use_pareto_ranking and self.pareto_manager:
            pareto_solutions = self.pareto_manager.get_best_solutions(max_solutions=5)
            for solution in pareto_solutions:
                if not np.array_equal(solution, best_solution):
                    alt_plan = self._solution_vector_to_blast_plan(solution, problem)
                    alternative_plans.append(alt_plan)
        
        result = OptimizationResult(
            best_plan=best_blast_plan,
            objective_value=objective_value,
            algorithm_used="genetic_algorithm",
            status=status,
            solve_time_seconds=elapsed_time,
            iterations=self.generation_count,
            function_evaluations=self.generation_count * self.config.population_size,
            converged=self._check_convergence(),
            alternative_plans=alternative_plans,
            objective_history=[1.0/f - 1.0 if f > 0 else float('inf') for f in self.best_fitness_history]
        )
        
        return result
    
    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the genetic algorithm for performance benchmarking"""
        return {
            "algorithm": "genetic_algorithm",
            "population_size": self.config.population_size,
            "num_generations": self.config.num_generations,
            "crossover_type": self.config.crossover_type,
            "mutation_type": self.config.mutation_type,
            "selection_type": self.config.parent_selection_type,
            "use_pareto_ranking": self.config.use_pareto_ranking,
            "generation_count": self.generation_count,
            "best_fitness_history": self.best_fitness_history,
            "diversity_history": self.diversity_history
        }


def create_genetic_optimizer(use_pareto: bool = False,
                           population_size: int = 50,
                           safety_config: Any = None) -> GeneticOptimizer:
    """Factory function to create genetic algorithm optimizer"""
    config = GeneticConfig(
        use_pareto_ranking=use_pareto,
        population_size=population_size,
        crossover_type="blast_custom" if use_pareto else "uniform",
        mutation_type="blast_custom" if use_pareto else "adaptive"
    )
    
    # Create constraint manager if safety config is provided
    constraint_manager = None
    if safety_config is not None:
        try:
            constraint_manager = ConstraintManager(safety_config)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not create constraint manager: {e}")
    
    return GeneticOptimizer(
        config=config,
        constraint_manager=constraint_manager
    )