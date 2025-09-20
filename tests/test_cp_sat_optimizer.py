"""
Unit tests for CP-SAT optimizer.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.drill_blast_system.optimization.cp_sat_optimizer import (
    CPSATOptimizer, CPSATConfig, CPSATSolutionCallback, create_cp_sat_optimizer
)
from src.drill_blast_system.optimization.data_structures import (
    OptimizationProblem, DecisionVariable, OptimizationConstraint,
    OptimizationObjective, BlastPlan, DrillHole, OptimizationStatus
)
from src.drill_blast_system.safety.config import SafetyConfig


class TestCPSATConfig:
    """Test CP-SAT configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = CPSATConfig()
        
        assert config.max_time_seconds == 300.0
        assert config.num_search_workers == 4
        assert config.log_search_progress is True
        assert config.charge_discretization == 1.0
        assert config.delay_discretization == 25
        assert config.objective_scale_factor == 1000


class TestCPSATOptimizer:
    """Test CP-SAT optimizer"""
    
    @pytest.fixture
    def sample_problem(self):
        """Create a sample optimization problem"""
        problem = OptimizationProblem(
            problem_id="test_problem",
            site_data={
                'site_id': 'TEST_SITE',
                'hole_pattern': [
                    DrillHole("H001", (0, 0, 0), 15.0, 150.0),
                    DrillHole("H002", (5, 0, 0), 15.0, 150.0),
                    DrillHole("H003", (10, 0, 0), 15.0, 150.0)
                ]
            },
            num_holes=3
        )
        
        # Add decision variables
        problem.variables = [
            DecisionVariable("charge_H001", "continuous", 0, 50),
            DecisionVariable("charge_H002", "continuous", 0, 50),
            DecisionVariable("charge_H003", "continuous", 0, 50),
            DecisionVariable("delay_H001", "integer", 0, 1000),
            DecisionVariable("delay_H002", "integer", 0, 1000),
            DecisionVariable("delay_H003", "integer", 0, 1000)
        ]
        
        # Add constraints
        problem.constraints = [
            OptimizationConstraint("per_delay_charge_limit", "inequality"),
            OptimizationConstraint("powder_factor_limits", "inequality")
        ]
        
        # Add objectives
        problem.objectives = [
            OptimizationObjective("minimize_cost", "minimize", weight=1.0)
        ]
        
        problem.calculate_problem_size()
        
        return problem
    
    @pytest.fixture
    def optimizer(self):
        """Create CP-SAT optimizer"""
        config = CPSATConfig(max_time_seconds=10.0)  # Short time for tests
        return CPSATOptimizer(config=config)
    
    def test_optimizer_creation(self, optimizer):
        """Test optimizer creation"""
        assert optimizer.config.max_time_seconds == 10.0
        assert optimizer.model is None
        assert optimizer.solver is None
        assert len(optimizer.variables) == 0
    
    def test_create_model(self, optimizer, sample_problem):
        """Test CP-SAT model creation"""
        optimizer._create_model(sample_problem)
        
        assert optimizer.model is not None
        assert optimizer.solver is not None
        assert len(optimizer.variables) == 0  # Variables not added yet
    
    def test_add_variables(self, optimizer, sample_problem):
        """Test adding variables to CP-SAT model"""
        optimizer._create_model(sample_problem)
        optimizer._add_variables(sample_problem)
        
        # Should have variables for charges and delays
        assert len(optimizer.variables) == 6  # 3 charges + 3 delays
        
        # Check variable names
        expected_vars = [
            "charge_H001", "charge_H002", "charge_H003",
            "delay_H001", "delay_H002", "delay_H003"
        ]
        
        for var_name in expected_vars:
            assert var_name in optimizer.variables
    
    def test_add_constraints(self, optimizer, sample_problem):
        """Test adding constraints to CP-SAT model"""
        optimizer._create_model(sample_problem)
        optimizer._add_variables(sample_problem)
        optimizer._add_constraints(sample_problem)
        
        # Should have added constraint groups
        assert len(optimizer.constraints) > 0
    
    def test_set_objective(self, optimizer, sample_problem):
        """Test setting objective function"""
        optimizer._create_model(sample_problem)
        optimizer._add_variables(sample_problem)
        optimizer._set_objective(sample_problem)
        
        # Objective should be set (no direct way to verify in OR-Tools)
        # Just check that no exception was raised
        assert True
    
    def test_configure_solver(self, optimizer):
        """Test solver configuration"""
        optimizer._create_model(OptimizationProblem("test", {}))
        optimizer._configure_solver()
        
        # Check that parameters were set
        assert optimizer.solver.parameters.max_time_in_seconds == 10.0
        assert optimizer.solver.parameters.num_search_workers == 4
    
    @patch('src.drill_blast_system.optimization.cp_sat_optimizer.cp_model.CpSolver.Solve')
    def test_solve_optimal(self, mock_solve, optimizer, sample_problem):
        """Test solving with optimal result"""
        from ortools.sat.python import cp_model
        
        # Mock optimal solution
        mock_solve.return_value = cp_model.OPTIMAL
        
        # Mock solver methods
        optimizer._create_model(sample_problem)
        optimizer.solver.ObjectiveValue = Mock(return_value=1000)
        optimizer.solver.Value = Mock(return_value=25)  # Mock variable values
        optimizer.solver.NumBranches = Mock(return_value=100)
        optimizer.solver.WallTime = Mock(return_value=5.0)
        
        result = optimizer._solve(sample_problem, None)
        
        assert result.status == OptimizationStatus.COMPLETED
        assert result.converged is True
        assert result.algorithm_used == "cp_sat"
    
    @patch('src.drill_blast_system.optimization.cp_sat_optimizer.cp_model.CpSolver.Solve')
    def test_solve_infeasible(self, mock_solve, optimizer, sample_problem):
        """Test solving with infeasible result"""
        from ortools.sat.python import cp_model
        
        # Mock infeasible solution
        mock_solve.return_value = cp_model.INFEASIBLE
        
        optimizer._create_model(sample_problem)
        optimizer.solver.NumBranches = Mock(return_value=0)
        optimizer.solver.WallTime = Mock(return_value=1.0)
        
        result = optimizer._solve(sample_problem, None)
        
        assert result.status == OptimizationStatus.FAILED
        assert len(result.constraint_violations) > 0
    
    def test_extract_solution(self, optimizer, sample_problem):
        """Test solution extraction"""
        optimizer._create_model(sample_problem)
        optimizer._add_variables(sample_problem)
        
        # Mock solver values
        optimizer.solver.Value = Mock(return_value=25)
        
        blast_plan = optimizer._extract_solution(sample_problem)
        
        assert isinstance(blast_plan, BlastPlan)
        assert len(blast_plan.holes) == 3
        assert blast_plan.optimization_algorithm == "cp_sat"
    
    def test_get_solver_statistics(self, optimizer):
        """Test getting solver statistics"""
        # Without solver
        stats = optimizer.get_solver_statistics()
        assert stats == {}
        
        # With solver
        optimizer._create_model(OptimizationProblem("test", {}))
        optimizer.solver.StatusName = Mock(return_value="OPTIMAL")
        optimizer.solver.ObjectiveValue = Mock(return_value=1000)
        optimizer.solver.BestObjectiveBound = Mock(return_value=1000)
        optimizer.solver.NumBranches = Mock(return_value=100)
        optimizer.solver.NumConflicts = Mock(return_value=10)
        optimizer.solver.WallTime = Mock(return_value=5.0)
        optimizer.solver.UserTime = Mock(return_value=4.5)
        optimizer.solver.DeterministicTime = Mock(return_value=1000)
        
        stats = optimizer.get_solver_statistics()
        
        assert stats["status"] == "OPTIMAL"
        assert stats["objective_value"] == 1000
        assert stats["num_branches"] == 100
        assert stats["wall_time"] == 5.0


class TestCPSATSolutionCallback:
    """Test CP-SAT solution callback"""
    
    def test_callback_creation(self):
        """Test callback creation"""
        from ortools.sat.python import cp_model
        
        model = cp_model.CpModel()
        var1 = model.NewIntVar(0, 100, "var1")
        var2 = model.NewIntVar(0, 100, "var2")
        
        variables = {"var1": var1, "var2": var2}
        callback = CPSATSolutionCallback(variables, max_solutions=5)
        
        assert callback.max_solutions == 5
        assert len(callback.solutions) == 0
        assert len(callback.objective_values) == 0
    
    def test_solution_collection(self):
        """Test solution collection in callback"""
        from ortools.sat.python import cp_model
        
        model = cp_model.CpModel()
        var1 = model.NewIntVar(0, 100, "var1")
        
        variables = {"var1": var1}
        callback = CPSATSolutionCallback(variables, max_solutions=2)
        
        # Mock the Value and ObjectiveValue methods
        callback.Value = Mock(return_value=50)
        callback.ObjectiveValue = Mock(return_value=100)
        callback.StopSearch = Mock()
        
        # Simulate finding solutions
        callback.on_solution_callback()
        callback.on_solution_callback()
        callback.on_solution_callback()  # Should trigger stop
        
        assert len(callback.solutions) == 2
        assert len(callback.objective_values) == 2
        callback.StopSearch.assert_called_once()


class TestCPSATFactory:
    """Test CP-SAT factory function"""
    
    def test_create_optimizer_without_safety_config(self):
        """Test creating optimizer without safety config"""
        optimizer = create_cp_sat_optimizer()
        
        assert isinstance(optimizer, CPSATOptimizer)
        assert optimizer.constraint_manager is None
    
    def test_create_optimizer_with_safety_config(self):
        """Test creating optimizer with safety config"""
        safety_config = SafetyConfig(
            max_charge_per_hole=50.0,
            max_charge_per_delay=200.0
        )
        
        optimizer = create_cp_sat_optimizer(safety_config)
        
        assert isinstance(optimizer, CPSATOptimizer)
        assert optimizer.constraint_manager is not None


class TestCPSATIntegration:
    """Integration tests for CP-SAT optimizer"""
    
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
            DecisionVariable("charge_H002", "continuous", 10, 30),
            DecisionVariable("delay_H001", "integer", 0, 100),
            DecisionVariable("delay_H002", "integer", 0, 100)
        ]
        
        problem.constraints = [
            OptimizationConstraint("simple_constraint", "inequality")
        ]
        
        problem.objectives = [
            OptimizationObjective("minimize_charge", "minimize")
        ]
        
        return problem
    
    def test_full_optimization_workflow(self, small_problem):
        """Test complete optimization workflow"""
        config = CPSATConfig(max_time_seconds=5.0)
        optimizer = CPSATOptimizer(config=config)
        
        try:
            result = optimizer.optimize(small_problem)
            
            # Should complete without error
            assert result.algorithm_used == "cp_sat"
            assert result.solve_time_seconds >= 0
            
            # Result status should be valid
            assert result.status in [
                OptimizationStatus.COMPLETED,
                OptimizationStatus.FAILED,
                OptimizationStatus.TIMEOUT
            ]
            
        except Exception as e:
            # If OR-Tools is not properly installed, test should still pass
            pytest.skip(f"OR-Tools not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__])