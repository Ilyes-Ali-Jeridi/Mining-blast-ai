"""
Optimization Engine Coordinator for Drill-and-Blast System.

This module implements the main OptimizationEngine class that coordinates
multiple optimization algorithms, manages solution comparison and ranking,
tracks optimization progress, and provides caching capabilities.

Key Features:
- Multi-algorithm coordination (CP-SAT, SciPy, Genetic Algorithm)
- Intelligent algorithm selection based on problem characteristics
- Solution comparison and ranking with multiple criteria
- Real-time progress tracking with WebSocket support
- Result caching and retrieval for performance
- Comprehensive logging and error handling

Usage:
    # Basic usage
    engine = OptimizationEngine()
    result = engine.optimize(problem)
    
    # With custom configuration and progress tracking
    config = OptimizationEngineConfig(enable_caching=True, max_algorithms=2)
    engine = OptimizationEngine(config=config, progress_callback=my_callback)
    result = engine.optimize(problem, track_progress=True)
"""

from typing import List, Dict, Tuple, Optional, Any, Callable, Union
import asyncio
import logging
import time
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from enum import Enum

from .data_structures import (
    OptimizationProblem, OptimizationResult, OptimizationStatus,
    BlastPlan, DrillHole
)
from .formulation import ObjectiveFunction, ConstraintManager
from .cp_sat_optimizer import CPSATOptimizer, CPSATConfig
from .scipy_optimizer import ScipyOptimizer, ScipyConfig
from .genetic_optimizer import GeneticOptimizer, GeneticConfig, PYGAD_AVAILABLE
from .complexity import estimate_problem_complexity


class AlgorithmType(Enum):
    """Available optimization algorithms"""
    CP_SAT = "cp_sat"
    SCIPY_DE = "scipy_differential_evolution"
    SCIPY_SLSQP = "scipy_slsqp"
    GENETIC = "genetic_algorithm"


@dataclass
class AlgorithmConfig:
    """Configuration for individual algorithms"""
    algorithm_type: AlgorithmType
    enabled: bool = True
    max_time_seconds: float = 300.0
    priority: int = 1  # Lower number = higher priority
    config: Any = None  # Algorithm-specific configuration


@dataclass
class OptimizationEngineConfig:
    """Configuration for optimization engine"""
    
    # Algorithm selection
    max_algorithms: int = 3  # Maximum number of algorithms to run
    parallel_execution: bool = True  # Run algorithms in parallel
    algorithm_timeout: float = 300.0  # Default timeout per algorithm
    
    # Solution ranking
    ranking_criteria: List[str] = field(default_factory=lambda: [
        "objective_value", "constraint_satisfaction", "solve_time"
    ])
    
    # Progress tracking
    enable_progress_tracking: bool = True
    progress_update_interval: float = 1.0  # seconds
    
    # Caching
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    max_cache_size: int = 100
    
    # Performance
    max_workers: int = 4  # For parallel execution
    
    # Algorithm configurations
    algorithm_configs: Dict[AlgorithmType, AlgorithmConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default algorithm configurations"""
        if not self.algorithm_configs:
            self.algorithm_configs = {
                AlgorithmType.CP_SAT: AlgorithmConfig(
                    algorithm_type=AlgorithmType.CP_SAT,
                    priority=1,
                    config=CPSATConfig(max_time_seconds=self.algorithm_timeout)
                ),
                AlgorithmType.SCIPY_DE: AlgorithmConfig(
                    algorithm_type=AlgorithmType.SCIPY_DE,
                    priority=2,
                    config=ScipyConfig(
                        primary_algorithm="differential_evolution",
                        max_time_seconds=self.algorithm_timeout
                    )
                ),
                AlgorithmType.SCIPY_SLSQP: AlgorithmConfig(
                    algorithm_type=AlgorithmType.SCIPY_SLSQP,
                    priority=3,
                    config=ScipyConfig(
                        primary_algorithm="slsqp",
                        max_time_seconds=self.algorithm_timeout
                    )
                )
            }
            
            # Add genetic algorithm if available
            if PYGAD_AVAILABLE:
                self.algorithm_configs[AlgorithmType.GENETIC] = AlgorithmConfig(
                    algorithm_type=AlgorithmType.GENETIC,
                    priority=4,
                    config=GeneticConfig(
                        num_generations=100,
                        population_size=50,
                        max_time_seconds=self.algorithm_timeout
                    )
                )


@dataclass
class OptimizationProgress:
    """Progress information for optimization"""
    
    # Overall progress
    total_algorithms: int = 0
    completed_algorithms: int = 0
    current_algorithm: Optional[str] = None
    overall_progress: float = 0.0  # 0.0 to 1.0
    
    # Current algorithm progress
    algorithm_progress: float = 0.0  # 0.0 to 1.0
    iterations: int = 0
    function_evaluations: int = 0
    current_best_objective: float = float('inf')
    
    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    elapsed_time: float = 0.0
    estimated_remaining_time: float = 0.0
    
    # Status
    status: OptimizationStatus = OptimizationStatus.NOT_STARTED
    current_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "total_algorithms": self.total_algorithms,
            "completed_algorithms": self.completed_algorithms,
            "current_algorithm": self.current_algorithm,
            "overall_progress": self.overall_progress,
            "algorithm_progress": self.algorithm_progress,
            "iterations": self.iterations,
            "function_evaluations": self.function_evaluations,
            "current_best_objective": self.current_best_objective,
            "elapsed_time": self.elapsed_time,
            "estimated_remaining_time": self.estimated_remaining_time,
            "status": self.status.value,
            "current_message": self.current_message
        }


@dataclass
class CachedResult:
    """Cached optimization result"""
    result: OptimizationResult
    timestamp: datetime
    problem_hash: str
    
    def is_expired(self, ttl_hours: int) -> bool:
        """Check if cached result is expired"""
        expiry_time = self.timestamp + timedelta(hours=ttl_hours)
        return datetime.utcnow() > expiry_time


class SolutionRanker:
    """Ranks and compares optimization solutions"""
    
    def __init__(self, ranking_criteria: List[str]):
        self.criteria = ranking_criteria
        self.logger = logging.getLogger(__name__ + ".SolutionRanker")
    
    def rank_solutions(self, results: List[OptimizationResult]) -> List[OptimizationResult]:
        """
        Rank solutions based on multiple criteria.
        
        Args:
            results: List of optimization results to rank
            
        Returns:
            Sorted list of results (best first)
        """
        if not results:
            return []
        
        # Filter out failed results
        valid_results = [r for r in results if r.status != OptimizationStatus.FAILED]
        
        if not valid_results:
            return results  # Return original list if all failed
        
        # Calculate composite scores
        scored_results = []
        for result in valid_results:
            score = self._calculate_composite_score(result, valid_results)
            scored_results.append((score, result))
        
        # Sort by score (lower is better)
        scored_results.sort(key=lambda x: x[0])
        
        # Return sorted results
        ranked_results = [result for _, result in scored_results]
        
        # Add failed results at the end
        failed_results = [r for r in results if r.status == OptimizationStatus.FAILED]
        ranked_results.extend(failed_results)
        
        self.logger.debug(f"Ranked {len(results)} solutions, {len(valid_results)} valid")
        
        return ranked_results
    
    def _calculate_composite_score(self, 
                                 result: OptimizationResult,
                                 all_results: List[OptimizationResult]) -> float:
        """Calculate composite score for ranking"""
        score = 0.0
        
        # Normalize each criterion and add to score
        for criterion in self.criteria:
            if criterion == "objective_value":
                score += self._normalize_objective_value(result, all_results) * 0.5
            elif criterion == "constraint_satisfaction":
                score += self._normalize_constraint_satisfaction(result) * 0.3
            elif criterion == "solve_time":
                score += self._normalize_solve_time(result, all_results) * 0.1
            elif criterion == "convergence":
                score += self._normalize_convergence(result) * 0.1
        
        return score
    
    def _normalize_objective_value(self, 
                                 result: OptimizationResult,
                                 all_results: List[OptimizationResult]) -> float:
        """Normalize objective value (0 = best, 1 = worst)"""
        objective_values = [r.objective_value for r in all_results if r.objective_value != float('inf')]
        
        if not objective_values or len(objective_values) == 1:
            return 0.0
        
        min_obj = min(objective_values)
        max_obj = max(objective_values)
        
        if max_obj == min_obj:
            return 0.0
        
        if result.objective_value == float('inf'):
            return 1.0
        
        return (result.objective_value - min_obj) / (max_obj - min_obj)
    
    def _normalize_constraint_satisfaction(self, result: OptimizationResult) -> float:
        """Normalize constraint satisfaction (0 = all satisfied, 1 = many violations)"""
        if not result.constraint_violations:
            return 0.0
        
        # Penalty based on number and severity of violations
        violation_penalty = len(result.constraint_violations) * 0.1
        severity_penalty = result.max_constraint_violation * 0.5
        
        return min(1.0, violation_penalty + severity_penalty)
    
    def _normalize_solve_time(self, 
                            result: OptimizationResult,
                            all_results: List[OptimizationResult]) -> float:
        """Normalize solve time (0 = fastest, 1 = slowest)"""
        solve_times = [r.solve_time_seconds for r in all_results]
        
        if not solve_times or len(solve_times) == 1:
            return 0.0
        
        min_time = min(solve_times)
        max_time = max(solve_times)
        
        if max_time == min_time:
            return 0.0
        
        return (result.solve_time_seconds - min_time) / (max_time - min_time)
    
    def _normalize_convergence(self, result: OptimizationResult) -> float:
        """Normalize convergence quality (0 = converged, 1 = not converged)"""
        return 0.0 if result.converged else 0.5


class OptimizationCache:
    """Caches optimization results for performance"""
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        self.max_size = max_size
        self.ttl_hours = ttl_hours
        self.cache: Dict[str, CachedResult] = {}
        self.access_times: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__ + ".OptimizationCache")
    
    def get_problem_hash(self, problem: OptimizationProblem) -> str:
        """Generate hash for optimization problem"""
        # Create a deterministic hash based on problem characteristics
        problem_data = {
            "num_variables": problem.num_variables,
            "num_constraints": problem.num_constraints,
            "variable_bounds": [(v.lower_bound, v.upper_bound) for v in problem.variables],
            "site_id": problem.site_data.get("site_id", "unknown")
        }
        
        problem_str = json.dumps(problem_data, sort_keys=True)
        return hashlib.md5(problem_str.encode()).hexdigest()
    
    def get(self, problem: OptimizationProblem) -> Optional[OptimizationResult]:
        """Get cached result for problem"""
        problem_hash = self.get_problem_hash(problem)
        
        if problem_hash in self.cache:
            cached = self.cache[problem_hash]
            
            # Check if expired
            if cached.is_expired(self.ttl_hours):
                self.logger.debug(f"Cache entry expired for problem {problem_hash}")
                del self.cache[problem_hash]
                if problem_hash in self.access_times:
                    del self.access_times[problem_hash]
                return None
            
            # Update access time
            self.access_times[problem_hash] = datetime.utcnow()
            self.logger.debug(f"Cache hit for problem {problem_hash}")
            return cached.result
        
        return None
    
    def put(self, problem: OptimizationProblem, result: OptimizationResult):
        """Cache optimization result"""
        problem_hash = self.get_problem_hash(problem)
        
        # Clean cache if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        # Store result
        cached_result = CachedResult(
            result=result,
            timestamp=datetime.utcnow(),
            problem_hash=problem_hash
        )
        
        self.cache[problem_hash] = cached_result
        self.access_times[problem_hash] = datetime.utcnow()
        
        self.logger.debug(f"Cached result for problem {problem_hash}")
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        if not self.access_times:
            return
        
        oldest_hash = min(self.access_times.keys(), 
                         key=lambda k: self.access_times[k])
        
        if oldest_hash in self.cache:
            del self.cache[oldest_hash]
        del self.access_times[oldest_hash]
        
        self.logger.debug(f"Evicted cache entry {oldest_hash}")
    
    def clear(self):
        """Clear all cached results"""
        self.cache.clear()
        self.access_times.clear()
        self.logger.debug("Cleared optimization cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_hours": self.ttl_hours,
            "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1)
        }


class OptimizationEngine:
    """
    Main optimization engine that coordinates multiple algorithms.
    
    This class manages the execution of multiple optimization algorithms,
    tracks progress, ranks solutions, and provides caching capabilities.
    """
    
    def __init__(self, 
                 config: OptimizationEngineConfig = None,
                 objective_function: ObjectiveFunction = None,
                 constraint_manager: ConstraintManager = None,
                 progress_callback: Optional[Callable[[OptimizationProgress], None]] = None):
        
        self.config = config or OptimizationEngineConfig()
        self.objective_function = objective_function
        self.constraint_manager = constraint_manager
        self.progress_callback = progress_callback
        
        self.logger = logging.getLogger(__name__ + ".OptimizationEngine")
        
        # Initialize components
        self.solution_ranker = SolutionRanker(self.config.ranking_criteria)
        self.cache = OptimizationCache(
            max_size=self.config.max_cache_size,
            ttl_hours=self.config.cache_ttl_hours
        ) if self.config.enable_caching else None
        
        # Progress tracking
        self.current_progress = OptimizationProgress()
        self.progress_lock = threading.Lock()
        
        # Algorithm instances
        self.optimizers: Dict[AlgorithmType, Any] = {}
        self._initialize_optimizers()
    
    def _initialize_optimizers(self):
        """Initialize optimizer instances"""
        for algo_type, algo_config in self.config.algorithm_configs.items():
            if not algo_config.enabled:
                continue
                
            try:
                if algo_type == AlgorithmType.CP_SAT:
                    self.optimizers[algo_type] = CPSATOptimizer(
                        config=algo_config.config,
                        objective_function=self.objective_function,
                        constraint_manager=self.constraint_manager
                    )
                elif algo_type == AlgorithmType.SCIPY_DE:
                    self.optimizers[algo_type] = ScipyOptimizer(
                        config=algo_config.config,
                        objective_function=self.objective_function,
                        constraint_manager=self.constraint_manager
                    )
                elif algo_type == AlgorithmType.SCIPY_SLSQP:
                    self.optimizers[algo_type] = ScipyOptimizer(
                        config=algo_config.config,
                        objective_function=self.objective_function,
                        constraint_manager=self.constraint_manager
                    )
                elif algo_type == AlgorithmType.GENETIC and PYGAD_AVAILABLE:
                    self.optimizers[algo_type] = GeneticOptimizer(
                        config=algo_config.config,
                        objective_function=self.objective_function,
                        constraint_manager=self.constraint_manager
                    )
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize {algo_type.value} optimizer: {e}")
        
        self.logger.info(f"Initialized {len(self.optimizers)} optimizers")
    
    def optimize(self, 
                problem: OptimizationProblem,
                initial_plan: Optional[BlastPlan] = None,
                track_progress: bool = True) -> OptimizationResult:
        """
        Optimize blast plan using multiple algorithms.
        
        Args:
            problem: Optimization problem to solve
            initial_plan: Optional initial solution
            track_progress: Whether to track and report progress
            
        Returns:
            Best optimization result found
        """
        self.logger.info(f"Starting optimization for problem {problem.problem_id}")
        start_time = time.time()
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(problem)
            if cached_result:
                self.logger.info("Returning cached optimization result")
                return cached_result
        
        # Initialize progress tracking
        if track_progress:
            self._initialize_progress_tracking(problem)
        
        try:
            # Select algorithms for this problem
            selected_algorithms = self._select_algorithms(problem)
            
            if not selected_algorithms:
                self.logger.error("No suitable algorithms available for problem")
                return OptimizationResult(
                    status=OptimizationStatus.FAILED,
                    algorithm_used="none",
                    solve_time_seconds=time.time() - start_time
                )
            
            # Run optimization algorithms
            if self.config.parallel_execution and len(selected_algorithms) > 1:
                results = self._run_algorithms_parallel(
                    selected_algorithms, problem, initial_plan, track_progress
                )
            else:
                results = self._run_algorithms_sequential(
                    selected_algorithms, problem, initial_plan, track_progress
                )
            
            # Rank and select best result
            if results:
                ranked_results = self.solution_ranker.rank_solutions(results)
                best_result = ranked_results[0]
                
                # Add alternative solutions
                if len(ranked_results) > 1:
                    best_result.alternative_plans = [
                        r.best_plan for r in ranked_results[1:] 
                        if r.best_plan is not None
                    ]
                
                # Cache result
                if self.cache and best_result.status == OptimizationStatus.COMPLETED:
                    self.cache.put(problem, best_result)
                
                self.logger.info(f"Optimization completed in {time.time() - start_time:.2f}s, "
                               f"best algorithm: {best_result.algorithm_used}")
                
                return best_result
            else:
                self.logger.error("All optimization algorithms failed")
                return OptimizationResult(
                    status=OptimizationStatus.FAILED,
                    algorithm_used="all_failed",
                    solve_time_seconds=time.time() - start_time
                )
                
        except Exception as e:
            self.logger.error(f"Optimization engine failed: {e}")
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                algorithm_used="engine_error",
                solve_time_seconds=time.time() - start_time
            )
        finally:
            # Finalize progress tracking
            if track_progress:
                self._finalize_progress_tracking()
    
    def _select_algorithms(self, problem: OptimizationProblem) -> List[AlgorithmType]:
        """Select appropriate algorithms based on problem characteristics"""
        
        # Get problem complexity
        complexity = estimate_problem_complexity(problem)
        
        # Start with all enabled algorithms
        candidates = []
        for algo_type, algo_config in self.config.algorithm_configs.items():
            if algo_config.enabled and algo_type in self.optimizers:
                candidates.append((algo_type, algo_config.priority))
        
        # Sort by priority
        candidates.sort(key=lambda x: x[1])
        
        # Apply selection logic based on problem characteristics
        selected = []
        
        # Always include CP-SAT for discrete problems
        if AlgorithmType.CP_SAT in [c[0] for c in candidates]:
            selected.append(AlgorithmType.CP_SAT)
        
        # Add continuous algorithms based on complexity
        if complexity in ["low", "medium"]:
            # Prefer differential evolution for global search
            if AlgorithmType.SCIPY_DE in [c[0] for c in candidates]:
                selected.append(AlgorithmType.SCIPY_DE)
            
            # Add SLSQP for local refinement
            if AlgorithmType.SCIPY_SLSQP in [c[0] for c in candidates] and len(selected) < self.config.max_algorithms:
                selected.append(AlgorithmType.SCIPY_SLSQP)
        
        # Add genetic algorithm for complex problems
        if complexity == "high" and AlgorithmType.GENETIC in [c[0] for c in candidates]:
            if len(selected) < self.config.max_algorithms:
                selected.append(AlgorithmType.GENETIC)
        
        # Ensure we don't exceed max algorithms
        selected = selected[:self.config.max_algorithms]
        
        self.logger.info(f"Selected algorithms for {complexity} complexity problem: "
                        f"{[algo.value for algo in selected]}")
        
        return selected
    
    def _run_algorithms_parallel(self, 
                               algorithms: List[AlgorithmType],
                               problem: OptimizationProblem,
                               initial_plan: Optional[BlastPlan],
                               track_progress: bool) -> List[OptimizationResult]:
        """Run algorithms in parallel"""
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all algorithms
            future_to_algo = {}
            for algo_type in algorithms:
                optimizer = self.optimizers[algo_type]
                future = executor.submit(self._run_single_algorithm, 
                                       algo_type, optimizer, problem, initial_plan)
                future_to_algo[future] = algo_type
            
            # Collect results as they complete
            for future in as_completed(future_to_algo):
                algo_type = future_to_algo[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if track_progress:
                        self._update_algorithm_completed(algo_type, result)
                        
                except Exception as e:
                    self.logger.error(f"Algorithm {algo_type.value} failed: {e}")
                    # Create failed result
                    failed_result = OptimizationResult(
                        status=OptimizationStatus.FAILED,
                        algorithm_used=algo_type.value
                    )
                    results.append(failed_result)
        
        return results
    
    def _run_algorithms_sequential(self, 
                                 algorithms: List[AlgorithmType],
                                 problem: OptimizationProblem,
                                 initial_plan: Optional[BlastPlan],
                                 track_progress: bool) -> List[OptimizationResult]:
        """Run algorithms sequentially"""
        
        results = []
        
        for algo_type in algorithms:
            if track_progress:
                self._update_current_algorithm(algo_type)
            
            try:
                optimizer = self.optimizers[algo_type]
                result = self._run_single_algorithm(algo_type, optimizer, problem, initial_plan)
                results.append(result)
                
                if track_progress:
                    self._update_algorithm_completed(algo_type, result)
                    
            except Exception as e:
                self.logger.error(f"Algorithm {algo_type.value} failed: {e}")
                failed_result = OptimizationResult(
                    status=OptimizationStatus.FAILED,
                    algorithm_used=algo_type.value
                )
                results.append(failed_result)
        
        return results
    
    def _run_single_algorithm(self, 
                            algo_type: AlgorithmType,
                            optimizer: Any,
                            problem: OptimizationProblem,
                            initial_plan: Optional[BlastPlan]) -> OptimizationResult:
        """Run a single optimization algorithm"""
        
        self.logger.debug(f"Running {algo_type.value} optimizer")
        
        try:
            result = optimizer.optimize(problem, initial_plan)
            result.algorithm_used = algo_type.value
            return result
            
        except Exception as e:
            self.logger.error(f"Error in {algo_type.value} optimizer: {e}")
            return OptimizationResult(
                status=OptimizationStatus.FAILED,
                algorithm_used=algo_type.value
            )
    
    def _initialize_progress_tracking(self, problem: OptimizationProblem):
        """Initialize progress tracking"""
        with self.progress_lock:
            self.current_progress = OptimizationProgress(
                total_algorithms=len(self._select_algorithms(problem)),
                status=OptimizationStatus.RUNNING,
                current_message="Initializing optimization..."
            )
        
        if self.progress_callback:
            self.progress_callback(self.current_progress)
    
    def _update_current_algorithm(self, algo_type: AlgorithmType):
        """Update current algorithm in progress"""
        with self.progress_lock:
            self.current_progress.current_algorithm = algo_type.value
            self.current_progress.algorithm_progress = 0.0
            self.current_progress.current_message = f"Running {algo_type.value}..."
            self.current_progress.elapsed_time = (
                datetime.utcnow() - self.current_progress.start_time
            ).total_seconds()
        
        if self.progress_callback:
            self.progress_callback(self.current_progress)
    
    def _update_algorithm_completed(self, algo_type: AlgorithmType, result: OptimizationResult):
        """Update progress when algorithm completes"""
        with self.progress_lock:
            self.current_progress.completed_algorithms += 1
            self.current_progress.overall_progress = (
                self.current_progress.completed_algorithms / 
                max(self.current_progress.total_algorithms, 1)
            )
            
            if result.objective_value < self.current_progress.current_best_objective:
                self.current_progress.current_best_objective = result.objective_value
            
            self.current_progress.current_message = (
                f"Completed {algo_type.value} "
                f"({self.current_progress.completed_algorithms}/"
                f"{self.current_progress.total_algorithms})"
            )
            
            self.current_progress.elapsed_time = (
                datetime.utcnow() - self.current_progress.start_time
            ).total_seconds()
        
        if self.progress_callback:
            self.progress_callback(self.current_progress)
    
    def _finalize_progress_tracking(self):
        """Finalize progress tracking"""
        with self.progress_lock:
            self.current_progress.status = OptimizationStatus.COMPLETED
            self.current_progress.overall_progress = 1.0
            self.current_progress.current_message = "Optimization completed"
            self.current_progress.elapsed_time = (
                datetime.utcnow() - self.current_progress.start_time
            ).total_seconds()
        
        if self.progress_callback:
            self.progress_callback(self.current_progress)
    
    def get_progress(self) -> OptimizationProgress:
        """Get current optimization progress"""
        with self.progress_lock:
            return self.current_progress
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"caching_disabled": True}
    
    def clear_cache(self):
        """Clear optimization cache"""
        if self.cache:
            self.cache.clear()
            self.logger.info("Cleared optimization cache")
    
    def get_available_algorithms(self) -> List[str]:
        """Get list of available algorithms"""
        return [algo_type.value for algo_type in self.optimizers.keys()]
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine configuration and status information"""
        return {
            "available_algorithms": self.get_available_algorithms(),
            "max_algorithms": self.config.max_algorithms,
            "parallel_execution": self.config.parallel_execution,
            "caching_enabled": self.config.enable_caching,
            "cache_stats": self.get_cache_stats(),
            "progress_tracking": self.config.enable_progress_tracking
        }


def create_optimization_engine(
    enable_caching: bool = True,
    max_algorithms: int = 3,
    parallel_execution: bool = True,
    progress_callback: Optional[Callable[[OptimizationProgress], None]] = None
) -> OptimizationEngine:
    """
    Factory function to create optimization engine with common configurations.
    
    Args:
        enable_caching: Whether to enable result caching
        max_algorithms: Maximum number of algorithms to run
        parallel_execution: Whether to run algorithms in parallel
        progress_callback: Optional callback for progress updates
        
    Returns:
        Configured optimization engine
    """
    config = OptimizationEngineConfig(
        enable_caching=enable_caching,
        max_algorithms=max_algorithms,
        parallel_execution=parallel_execution
    )
    
    return OptimizationEngine(
        config=config,
        progress_callback=progress_callback
    )