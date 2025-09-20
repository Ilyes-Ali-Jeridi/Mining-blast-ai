"""
Unit tests for SciPy optimizer.
"""

import pytest
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock

from src.drill_blast_system.optimization.scipy_optimizer import (
    ScipyOptimizer, ScipyConfig, ConvergenceMonitor, create_scipy_optimizer
)
from src.drill_blast_system.optimization.data_structures import (
    OptimizationProblem, DecisionVariable, OptimizationConstraint,
    OptimizationObjective, BlastPlan, DrillHole, OptimizationStatus
)
from src.drill_blast_system.safety.config import SafetyConfig


class TestScipyConfig:
    """Test SciPy configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ScipyConfig()
        
        assert config.primary_algorithm == "differential_evolution"
        assert config.use_polishing is True
        assert config.de_maxiter == 1000
        assert config.de_popsize == 15
        assert config.max_time_seconds == 300.0
        assert config.constraint_penalty_factor == 1000.0


class TestConvergenceMonitor:
    """Test convergence monitoring"""
    
    def test_convergence_monitor_creation(self):
        """Test convergence monitor creation"""
        monitor = ConvergenceMonitor(window_size=10, threshold=1e-3)
        
        assert monitor.window_size == 10
        assert monitor.threshold == 1e-3
        assert len(monitor.objective_history) == 0
        assert monitor.iteration_count == 0
    
    def test_convergence_detection(self):
        """Test convergence detection"""
        monitor = ConvergenceMonitor(window_size=5, threshold=1e-3)
        
        # Add values that don't converge
        for i in range(10):
            converged = monitor.update(10.0 - i)  # Decreasing values
            if i < 4:
                assert not converged  # Not enough history
            # Later values should not converge due to large changes
        
        # Add values that converge
        for i in range(10):
            converged = monitor.update(1.0 + 1e-6 * i)  # Small changes
            if i >= 4:  # After window is full
                assert converged  # Should detect convergence
                break
    
    def test_reset(self):
        """Test monitor reset"""
        monitor = ConvergenceMonitor()
        
        # Add some history
        monitor.update(1.0)
        monitor.update(2.0)
        
        assert len(monitor.objective_history) == 2
        assert monitor.iteration_count == 2
        
        # Reset
        monitor.reset()
        
        assert len(monitor.objective_history) == 0
        assert monitor.iteration_count == 0


class TestScipyOptimizer:
    """Test SciPy optimizer"""
    
    @pytest.fixture
    def sample_problem(self):
        """Create a sample optimization problem"""
        problem = OptimizationProblem(
            problem_id="test_problem",
            site_data={
                'site_id': 'TEST_SITE',
                'hole_pattern': [
                    DrillHole("H001", (0, 0, 0), 15.0, 150.0),
                    DrillHole("H002", (5, 0, 0), 15.0, 150.0)
                ]
            },
            num_holes=2
        )
        
        # Add decision variables
        problem.variables = [
            DecisionVariable("charge_H001", "continuous", 10, 50),
            DecisionVariable("charge_H002", "continuous", 10, 50),
            DecisionVariable("delay_H001", "continuous", 0, 1000),
            DecisionVariable("delay_H002", "continuous", 0, 1000)
        ]
        
        # Add constraints
        problem.constraints = [
            OptimizationConstraint("charge_limit", "inequality")
        ]
        
        # Add objectives
        problem.objectives = [
            OptimizationObjective("minimize_cost", "minimize", weight=1.0)
        ]
        
        problem.calculate_problem_size()
        
        return problem
    
    @pytest.fixture
    def optimizer(self):
        """Create SciPy optimizer"""
        config = ScipyConfig(
            primary_algorithm="differential_evolution",
            de_maxiter=10,  # Small for tests
            max_time_seconds=5.0
        )
        return ScipyOptimizer(config=config)
    
    def test_optimizer_creation(self, optimizer):
        """Test optimizer creation"""
        assert optimizer.config.primary_algorithm == "differential_evolution"
        assert optimizer.config.de_maxiter == 10
        assert optimizer.problem is None
        assert optimizer.bounds is None
    
    def test_prepare_problem(self, optimizer, sample_problem):
        """Test problem preparation"""
        optimizer._prepare_problem(sample_problem)
        
        assert optimizer.bounds is not None
        assert optimizer.bounds.shape == (4, 2)  # 4 variables, 2 bounds each
        assert optimizer.function_evaluations == 0
    
    def test_get_initial_solution(self, optimizer, sample_problem):
        """Test initial solution generation"""
        optimizer._prepare_problem(sample_problem)
        
        # Without initial plan
        x0 = optimizer._get_initial_solution(sample_problem, None)
        assert len(x0) == 4
        assert np.all(x0 >= optimizer.bounds[:, 0])
        assert np.all(x0 <= optimizer.bounds[:, 1])
        
        # With initial plan
        initial_plan = BlastPlan(
            plan_id="initial",
            site_id="test",
            holes=[
                DrillHole("H001", (0, 0, 0), 15.0, 150.0, charge_kg=25.0, delay_ms=100),
                DrillHole("H002", (5, 0, 0), 15.0, 150.0, charge_kg=30.0, delay_ms=200)
            ]
        )
        
        x0_with_plan = optimizer._get_initial_solution(sample_problem, initial_plan)
        assert len(x0_with_plan) == 4
        assert x0_with_plan[0] == 25.0  # charge_H001
        assert x0_with_plan[2] == 100.0  # delay_H001
    
    def test_solution_to_blast_plan(self, optimizer, sample_problem):
        """Test solution vector to blast plan conversion"""
        optimizer.problem = sample_problem
        
        # Test solution vector
        x = np.array([25.0, 30.0, 100.0, 200.0])
        
        blast_plan = optimizer._solution_to_blast_plan(x)
        
        assert isinstance(blast_plan, BlastPlan)
        assert len(blast_plan.holes) == 2
        assert blast_plan.holes[0].charge_kg == 25.0
        assert blast_plan.holes[1].charge_kg == 30.0
        assert blast_plan.holes[0].delay_ms == 100
        assert blast_plan.holes[1].delay_ms == 200
    
    def test_objective_function_wrapper(self, optimizer, sample_problem):
        """Test objective function wrapper"""
        optimizer.problem = sample_problem
        optimizer._prepare_problem(sample_problem)
        
        # Test with valid solution
        x = np.array([25.0, 30.0, 100.0, 200.0])
        
        objective_value = optimizer._objective_function_wrapper(x)
        
        assert isinstance(objective_value, float)
        assert objective_value >= 0
        assert optimizer.function_evaluations == 1
    
    def test_objective_function_bounds_penalty(self, optimizer, sample_problem):
        """Test bounds penalty in objective function"""
        optimizer.problem = sample_problem
        optimizer._prepare_problem(sample_problem)
        optimizer.config.enforce_bounds = True
        
        # Test with out-of-bounds solution
        x = np.array([5.0, 30.0, 100.0, 200.0])  # charge_H001 below lower bound (10)
        
        objective_value = optimizer._objective_function_wrapper(x)
        
        # Should have large penalty
        assert objective_value > 1000
    
    def test_optimization_callback(self, optimizer):
        """Test optimization callback"""
        optimizer.start_time = time.time()
        optimizer.config.max_time_seconds = 1.0
        
        # Test normal callback
        x = np.array([25.0, 30.0, 100.0, 200.0])
        
        # Mock the objective function wrapper
        optimizer._objective_function_wrapper = Mock(return_value=100.0)
        
        should_stop = optimizer._optimization_callback(x)
        
        # Should not stop immediately
        assert isinstance(should_stop, bool)
    
    @patch('src.drill_blast_system.optimization.scipy_optimizer.optimize.differential_evolution')
    def test_run_differential_evolution(self, mock_de, optimizer, sample_problem):
        """Test differential evolution execution"""
        optimizer._prepare_problem(sample_problem)
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.fun = 100.0
        mock_result.x = np.array([25.0, 30.0, 100.0, 200.0])
        mock_de.return_value = mock_result
        
        x0 = optimizer._get_initial_solution(sample_problem, None)
        result = optimizer._run_differential_evolution(x0)
        
        assert result.success is True
        assert result.fun == 100.0
        mock_de.assert_called_once()
    
    @patch('src.drill_blast_system.optimization.scipy_optimizer.optimize.minimize')
    def test_run_slsqp(self, mock_minimize, optimizer, sample_problem):
        """Test SLSQP execution"""
        optimizer._prepare_problem(sample_problem)
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.fun = 100.0
        mock_result.x = np.array([25.0, 30.0, 100.0, 200.0])
        mock_minimize.return_value = mock_result
        
        x0 = optimizer._get_initial_solution(sample_problem, None)
        result = optimizer._run_slsqp(x0)
        
        assert result.success is True
        assert result.fun == 100.0
        mock_minimize.assert_called_once()
    
    @patch('src.drill_blast_system.optimization.scipy_optimizer.optimize.dual_annealing')
    def test_run_dual_annealing(self, mock_da, optimizer, sample_problem):
        """Test dual annealing execution"""
        optimizer._prepare_problem(sample_problem)
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.fun = 100.0
        mock_result.x = np.array([25.0, 30.0, 100.0, 200.0])
        mock_da.return_value = mock_result
        
        x0 = optimizer._get_initial_solution(sample_problem, None)
        result = optimizer._run_dual_annealing(x0)
        
        assert result.success is True
        assert result.fun == 100.0
        mock_da.assert_called_once()
    
    def test_polish_solution(self, optimizer, sample_problem):
        """Test solution polishing"""
        optimizer._prepare_problem(sample_problem)
        
        # Mock primary result
        primary_result = Mock()
        primary_result.fun = 100.0
        primary_result.success = True
        
        x = np.array([25.0, 30.0, 100.0, 200.0])
        
        with patch('src.drill_blast_system.optimization.scipy_optimizer.optimize.minimize') as mock_minimize:
            # Mock better polished result
            mock_polish_result = Mock()
            mock_polish_result.success = True
            mock_polish_result.fun = 90.0  # Better than primary
            mock_polish_result.x = x
            mock_minimize.return_value = mock_polish_result
            
            result = optimizer._polish_solution(x, primary_result)
            
            assert result.fun == 90.0  # Should use polished result
    
    def test_create_optimization_result(self, optimizer, sample_problem):
        """Test optimization result creation"""
        # Mock SciPy result
        scipy_result = Mock()
        scipy_result.success = True
        scipy_result.fun = 100.0
        scipy_result.x = np.array([25.0, 30.0, 100.0, 200.0])
        scipy_result.nit = 50
        
        optimizer.problem = sample_problem
        optimizer.function_evaluations = 200
        optimizer.start_time = time.time() - 10.0  # 10 seconds ago
        
        result = optimizer._create_optimization_result(scipy_result, sample_problem)
        
        assert result.status == OptimizationStatus.COMPLETED
        assert result.objective_value == 100.0
        assert result.iterations == 50
        assert result.function_evaluations == 200
        assert result.solve_time_seconds >= 10.0
        assert result.converged is True
    
    def test_get_algorithm_info(self, optimizer):
        """Test algorithm information retrieval"""
        optimizer.function_evaluations = 100
        optimizer.constraint_evaluations = 50
        
        info = optimizer.get_algorithm_info()
        
        assert info["primary_algorithm"] == "differential_evolution"
        assert info["use_polishing"] is True
        assert info["function_evaluations"] == 100
        assert info["constraint_evaluations"] == 50


class TestScipyFactory:
    """Test SciPy factory function"""
    
    def test_create_optimizer_differential_evolution(self):
        """Test creating DE optimizer"""
        optimizer = create_scipy_optimizer("differential_evolution")
        
        assert isinstance(optimizer, ScipyOptimizer)
        assert optimizer.config.primary_algorithm == "differential_evolution"
        assert optimizer.constraint_manager is None
    
    def test_create_optimizer_slsqp(self):
        """Test creating SLSQP optimizer"""
        optimizer = create_scipy_optimizer("slsqp")
        
        assert isinstance(optimizer, ScipyOptimizer)
        assert optimizer.config.primary_algorithm == "slsqp"
    
    def test_create_optimizer_with_safety_config(self):
        """Test creating optimizer with safety config"""
        safety_config = SafetyConfig(
            max_charge_per_hole=50.0,
            max_charge_per_delay=200.0
        )
        
        optimizer = create_scipy_optimizer("differential_evolution", safety_config)
        
        assert isinstance(optimizer, ScipyOptimizer)
        assert optimizer.constraint_manager is not None


class TestScipyIntegration:
    """Integration tests for SciPy optimizer"""
    
    @pytest.fixture
    def small_problem(self):
        """Create a small problem for integration testing"""
        problem = OptimizationProblem(
            problem_id="small_test",
            site_data={
                'site_id': 'TEST',
                'hole_pattern': [
                    DrillHole("H001", (0, 0, 0), 15.0, 150.0),
                    DrillHole("H002", (5, 0, 0), 15.0, 150.0)
                ]
            },
            num_holes=2
        )
        
        # Simple variables
        problem.variables = [
            DecisionVariable("charge_H001", "continuous", 10, 30),
            DecisionVariable("charge_H002", "continuous", 10, 30)
        ]
        
        problem.constraints = [
            OptimizationConstraint("simple_constraint", "inequality")
        ]
        
        problem.objectives = [
            OptimizationObjective("minimize_charge", "minimize")
        ]
        
        return problem
    
    def test_full_optimization_workflow_de(self, small_problem):
        """Test complete optimization workflow with DE"""
        config = ScipyConfig(
            primary_algorithm="differential_evolution",
            de_maxiter=5,  # Very small for test
            max_time_seconds=2.0,
            use_polishing=False
        )
        optimizer = ScipyOptimizer(config=config)
        
        result = optimizer.optimize(small_problem)
        
        # Should complete without error
        assert result.algorithm_used == "scipy_differential_evolution"
        assert result.solve_time_seconds >= 0
        
        # Result status should be valid
        assert result.status in [
            OptimizationStatus.COMPLETED,
            OptimizationStatus.FAILED,
            OptimizationStatus.TIMEOUT
        ]
    
    def test_full_optimization_workflow_slsqp(self, small_problem):
        """Test complete optimization workflow with SLSQP"""
        config = ScipyConfig(
            primary_algorithm="slsqp",
            slsqp_maxiter=5,  # Very small for test
            max_time_seconds=2.0,
            use_polishing=False
        )
        optimizer = ScipyOptimizer(config=config)
        
        result = optimizer.optimize(small_problem)
        
        # Should complete without error
        assert result.algorithm_used == "scipy_slsqp"
        assert result.solve_time_seconds >= 0
        
        # Result status should be valid
        assert result.status in [
            OptimizationStatus.COMPLETED,
            OptimizationStatus.FAILED,
            OptimizationStatus.TIMEOUT
        ]


if __name__ == "__main__":
    pytest.main([__file__])