"""
Example demonstrating the optimization engine coordinator.

This example shows how to use the OptimizationEngine to coordinate
multiple optimization algorithms for drill-and-blast optimization.
"""

import logging
from typing import Dict, Any

from src.drill_blast_system.optimization import (
    OptimizationEngine, OptimizationEngineConfig, create_optimization_engine,
    OptimizationProblem, BlastPlan, DrillHole, DecisionVariable
)
from src.drill_blast_system.optimization.formulation import (
    ProblemFormulator, OptimizationParameters, SiteGeometry
)
from src.drill_blast_system.optimization.engine import OptimizationProgress
from src.drill_blast_system.safety.config import SafetyConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_example_problem() -> OptimizationProblem:
    """Create an example optimization problem"""
    
    # Create drill holes
    holes = [
        DrillHole(
            hole_id="H001",
            coordinates=(0.0, 0.0, 100.0),
            depth=12.0,
            diameter=150.0,
            charge_kg=30.0,
            delay_ms=0
        ),
        DrillHole(
            hole_id="H002", 
            coordinates=(4.0, 0.0, 100.0),
            depth=12.0,
            diameter=150.0,
            charge_kg=30.0,
            delay_ms=25
        ),
        DrillHole(
            hole_id="H003",
            coordinates=(8.0, 0.0, 100.0),
            depth=12.0,
            diameter=150.0,
            charge_kg=30.0,
            delay_ms=50
        )
    ]
    
    # Create decision variables
    variables = []
    for hole in holes:
        # Charge variables
        variables.append(DecisionVariable(
            name=f"charge_{hole.hole_id}",
            var_type="continuous",
            lower_bound=10.0,
            upper_bound=50.0,
            initial_value=hole.charge_kg,
            description=f"Charge for hole {hole.hole_id}",
            units="kg"
        ))
        
        # Delay variables
        variables.append(DecisionVariable(
            name=f"delay_{hole.hole_id}",
            var_type="integer",
            lower_bound=0,
            upper_bound=500,
            initial_value=hole.delay_ms,
            description=f"Delay for hole {hole.hole_id}",
            units="ms"
        ))
    
    # Create problem
    problem = OptimizationProblem(
        problem_id="example_blast_optimization",
        site_data={
            "site_id": "example_site",
            "hole_pattern": holes,
            "total_rock_volume": 1000.0,  # m³
            "rock_density": 2.7  # t/m³
        },
        variables=variables,
        num_holes=len(holes)
    )
    
    problem.calculate_problem_size()
    return problem


def progress_callback(progress: OptimizationProgress):
    """Callback function to track optimization progress"""
    logger.info(f"Progress: {progress.overall_progress:.1%} - "
               f"Algorithm: {progress.current_algorithm} - "
               f"Message: {progress.current_message}")


def main():
    """Main example function"""
    logger.info("=== Optimization Engine Example ===")
    
    # Create example problem
    logger.info("Creating optimization problem...")
    problem = create_example_problem()
    logger.info(f"Problem created with {problem.num_variables} variables, "
               f"{problem.num_holes} holes")
    
    # Example 1: Basic optimization with default settings
    logger.info("\n--- Example 1: Basic Optimization ---")
    
    engine = create_optimization_engine(
        enable_caching=True,
        max_algorithms=2,
        parallel_execution=False,  # Sequential for clearer logging
        progress_callback=progress_callback
    )
    
    logger.info(f"Engine initialized with algorithms: {engine.get_available_algorithms()}")
    
    # Run optimization
    result = engine.optimize(problem, track_progress=True)
    
    logger.info(f"Optimization completed!")
    logger.info(f"Status: {result.status}")
    logger.info(f"Algorithm used: {result.algorithm_used}")
    logger.info(f"Objective value: {result.objective_value:.2f}")
    logger.info(f"Solve time: {result.solve_time_seconds:.2f} seconds")
    logger.info(f"Converged: {result.converged}")
    
    if result.best_plan:
        logger.info(f"Best plan has {len(result.best_plan.holes)} holes")
        logger.info(f"Total charge: {result.best_plan.total_charge_kg:.1f} kg")
    
    # Example 2: Custom configuration
    logger.info("\n--- Example 2: Custom Configuration ---")
    
    config = OptimizationEngineConfig(
        max_algorithms=1,  # Only run one algorithm
        parallel_execution=False,
        enable_caching=False,  # Disable caching
        algorithm_timeout=30.0  # Short timeout
    )
    
    custom_engine = OptimizationEngine(config=config)
    
    logger.info("Running optimization with custom configuration...")
    result2 = custom_engine.optimize(problem)
    
    logger.info(f"Custom optimization completed!")
    logger.info(f"Algorithm used: {result2.algorithm_used}")
    logger.info(f"Solve time: {result2.solve_time_seconds:.2f} seconds")
    
    # Example 3: Cache demonstration
    logger.info("\n--- Example 3: Cache Demonstration ---")
    
    # First run (should compute)
    cached_engine = create_optimization_engine(enable_caching=True)
    
    logger.info("First run (computing result)...")
    start_time = time.time()
    result3a = cached_engine.optimize(problem)
    first_time = time.time() - start_time
    
    # Second run (should use cache)
    logger.info("Second run (should use cache)...")
    start_time = time.time()
    result3b = cached_engine.optimize(problem)
    second_time = time.time() - start_time
    
    logger.info(f"First run time: {first_time:.2f}s")
    logger.info(f"Second run time: {second_time:.2f}s")
    logger.info(f"Cache stats: {cached_engine.get_cache_stats()}")
    
    # Example 4: Engine information
    logger.info("\n--- Example 4: Engine Information ---")
    
    engine_info = engine.get_engine_info()
    logger.info("Engine configuration:")
    for key, value in engine_info.items():
        logger.info(f"  {key}: {value}")
    
    logger.info("\n=== Example Complete ===")


if __name__ == "__main__":
    import time
    main()