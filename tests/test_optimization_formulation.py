"""
Unit tests for optimization problem formulation.
"""

import pytest
import numpy as np
from datetime import datetime

from src.drill_blast_system.optimization.data_structures import (
    DrillHole, BlastPlan, DecisionVariable, OptimizationProblem,
    OptimizationConstraint, OptimizationObjective, OptimizationResult,
    OptimizationStatus
)
from src.drill_blast_system.optimization.formulation import (
    ProblemFormulator, ObjectiveFunction, ConstraintManager,
    SiteGeometry, OptimizationParameters
)
from src.drill_blast_system.optimization.complexity import ComplexityAnalyzer, analyze_problem_structure
from src.drill_blast_system.safety.config import SafetyConfig


class TestDrillHole:
    """Test DrillHole data structure"""
    
    def test_drill_hole_creation(self):
        """Test basic drill hole creation"""
        hole = DrillHole(
            hole_id="H001",
            coordinates=(100.0, 200.0, 50.0),
            depth=15.0,
            diameter=150.0,
            charge_kg=25.0,
            delay_ms=100
        )
        
        assert hole.hole_id == "H001"
        assert hole.coordinates == (100.0, 200.0, 50.0)
        assert hole.charge_kg == 25.0
        assert hole.delay_ms == 100
    
    def test_actual_coordinates_with_offset(self):
        """Test coordinate calculation with position offsets"""
        hole = DrillHole(
            hole_id="H001",
            coordinates=(100.0, 200.0, 50.0),
            depth=15.0,
            diameter=150.0,
            position_offset_x=1.5,
            position_offset_y=-0.5
        )
        
        actual_coords = hole.get_actual_coordinates()
        assert actual_coords == (101.5, 199.5, 50.0)
    
    def test_powder_factor_calculation(self):
        """Test powder factor calculation"""
        hole = DrillHole(
            hole_id="H001",
            coordinates=(100.0, 200.0, 50.0),
            depth=15.0,
            diameter=150.0,
            charge_kg=30.0
        )
        
        # Test with valid parameters
        rock_volume = 100.0  # m³
        rock_density = 2.7   # t/m³
        powder_factor = hole.get_powder_factor(rock_volume, rock_density)
        
        expected_pf = 30.0 / (100.0 * 2.7)  # kg/t
        assert abs(powder_factor - expected_pf) < 1e-6
        
        # Test with zero volume
        assert hole.get_powder_factor(0.0, rock_density) == 0.0


class TestBlastPlan:
    """Test BlastPlan data structure"""
    
    def test_blast_plan_creation(self):
        """Test basic blast plan creation"""
        plan = BlastPlan(
            plan_id="PLAN001",
            site_id="SITE001"
        )
        
        assert plan.plan_id == "PLAN001"
        assert plan.site_id == "SITE001"
        assert len(plan.holes) == 0
        assert plan.total_charge_kg == 0.0
    
    def test_calculate_totals(self):
        """Test total calculation from holes"""
        holes = [
            DrillHole("H001", (0, 0, 0), 15.0, 150.0, charge_kg=25.0),
            DrillHole("H002", (5, 0, 0), 15.0, 150.0, charge_kg=30.0),
            DrillHole("H003", (10, 0, 0), 15.0, 150.0, charge_kg=20.0)
        ]
        
        plan = BlastPlan(
            plan_id="PLAN001",
            site_id="SITE001",
            holes=holes
        )
        
        plan.calculate_totals()
        
        assert plan.total_holes == 3
        assert plan.total_charge_kg == 75.0
    
    def test_holes_by_delay(self):
        """Test grouping holes by delay"""
        holes = [
            DrillHole("H001", (0, 0, 0), 15.0, 150.0, delay_ms=0),
            DrillHole("H002", (5, 0, 0), 15.0, 150.0, delay_ms=100),
            DrillHole("H003", (10, 0, 0), 15.0, 150.0, delay_ms=0),
            DrillHole("H004", (15, 0, 0), 15.0, 150.0, delay_ms=200)
        ]
        
        plan = BlastPlan(
            plan_id="PLAN001",
            site_id="SITE001", 
            holes=holes
        )
        
        delay_groups = plan.get_holes_by_delay()
        
        assert len(delay_groups[0]) == 2  # H001, H003
        assert len(delay_groups[100]) == 1  # H002
        assert len(delay_groups[200]) == 1  # H004
    
    def test_charge_per_delay(self):
        """Test charge calculation per delay"""
        holes = [
            DrillHole("H001", (0, 0, 0), 15.0, 150.0, charge_kg=25.0, delay_ms=0),
            DrillHole("H002", (5, 0, 0), 15.0, 150.0, charge_kg=30.0, delay_ms=100),
            DrillHole("H003", (10, 0, 0), 15.0, 150.0, charge_kg=20.0, delay_ms=0)
        ]
        
        plan = BlastPlan(
            plan_id="PLAN001",
            site_id="SITE001",
            holes=holes
        )
        
        delay_charges = plan.get_charge_per_delay()
        
        assert delay_charges[0] == 45.0  # H001 + H003
        assert delay_charges[100] == 30.0  # H002


class TestProblemFormulator:
    """Test optimization problem formulation"""
    
    @pytest.fixture
    def safety_config(self):
        """Create test safety configuration"""
        return SafetyConfig(
            max_charge_per_hole=50.0,
            max_charge_per_delay=200.0,
            powder_factor_min=0.1,
            powder_factor_max=1.5,
            ppv_default_limit=5.0
        )
    
    @pytest.fixture
    def site_geometry(self):
        """Create test site geometry"""
        return SiteGeometry(
            bench_width=50.0,
            bench_length=100.0,
            bench_height=15.0,
            free_face_coordinates=[(0, 0), (100, 0), (100, 50), (0, 50)]
        )
    
    @pytest.fixture
    def hole_pattern(self):
        """Create test hole pattern"""
        return [
            DrillHole("H001", (10, 10, 0), 15.0, 150.0),
            DrillHole("H002", (20, 10, 0), 15.0, 150.0),
            DrillHole("H003", (30, 10, 0), 15.0, 150.0)
        ]
    
    @pytest.fixture
    def optimization_params(self):
        """Create test optimization parameters"""
        return OptimizationParameters(
            min_burden=3.0,
            max_burden=6.0,
            min_spacing=3.0,
            max_spacing=6.0,
            max_charge_per_hole=40.0,
            target_p80=200.0
        )
    
    def test_problem_formulation(self, safety_config, site_geometry, hole_pattern, optimization_params):
        """Test complete problem formulation"""
        formulator = ProblemFormulator(safety_config)
        
        problem = formulator.formulate_problem(
            site_geometry, hole_pattern, optimization_params
        )
        
        assert problem.num_holes == 3
        assert problem.num_variables > 0
        assert problem.num_constraints > 0
        assert len(problem.objectives) > 0
        assert problem.estimated_complexity in ["low", "medium", "high"]
    
    def test_decision_variables_creation(self, safety_config, site_geometry, hole_pattern, optimization_params):
        """Test decision variable creation"""
        formulator = ProblemFormulator(safety_config)
        variables = formulator._create_decision_variables(hole_pattern, optimization_params)
        
        # Should have 4 variables per hole: charge, delay, offset_x, offset_y
        expected_vars = len(hole_pattern) * 4
        assert len(variables) == expected_vars
        
        # Check variable types and bounds
        charge_vars = [v for v in variables if v.name.startswith("charge_")]
        assert len(charge_vars) == len(hole_pattern)
        
        for var in charge_vars:
            assert var.var_type == "continuous"
            assert var.lower_bound >= 0
            assert var.upper_bound <= safety_config.max_charge_per_hole
    
    def test_constraints_creation(self, safety_config, site_geometry, hole_pattern, optimization_params):
        """Test constraint creation"""
        formulator = ProblemFormulator(safety_config)
        constraints = formulator._create_constraints(hole_pattern, site_geometry, optimization_params)
        
        assert len(constraints) > 0
        
        # Check for required constraint types
        constraint_names = [c.name for c in constraints]
        assert "per_delay_charge_limit" in constraint_names
        assert "minimum_burden" in constraint_names
        assert "minimum_spacing" in constraint_names
    
    def test_objectives_creation(self, safety_config, optimization_params):
        """Test objective creation"""
        formulator = ProblemFormulator(safety_config)
        objectives = formulator._create_objectives(optimization_params)
        
        assert len(objectives) >= 3  # fragmentation, cost, ppv
        
        objective_names = [obj.name for obj in objectives]
        assert "fragmentation_quality" in objective_names
        assert "total_cost" in objective_names
        assert "ppv_penalty" in objective_names


class TestComplexityAnalyzer:
    """Test complexity analysis"""
    
    def test_complexity_analysis(self):
        """Test basic complexity analysis"""
        # Create a simple problem
        problem = OptimizationProblem(
            problem_id="test_problem",
            site_data={},
            num_holes=5
        )
        
        # Add some variables
        problem.variables = [
            DecisionVariable("var1", "continuous", 0, 100),
            DecisionVariable("var2", "integer", 0, 10),
            DecisionVariable("var3", "continuous", 0, 50)
        ]
        
        # Add some constraints
        problem.constraints = [
            OptimizationConstraint("c1", "inequality"),
            OptimizationConstraint("c2", "equality")
        ]
        
        problem.calculate_problem_size()
        
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.analyze_problem(problem)
        
        assert metrics.num_variables == 3
        assert metrics.num_constraints == 2
        assert metrics.complexity_class in ["simple", "moderate", "complex", "very_complex"]
        assert metrics.complexity_score > 0
    
    def test_algorithm_suggestions(self):
        """Test algorithm suggestion logic"""
        analyzer = ComplexityAnalyzer()
        
        # Create metrics for different complexity levels
        simple_metrics = ComplexityAnalyzer().analyze_problem(OptimizationProblem(
            problem_id="simple",
            site_data={},
            variables=[DecisionVariable("v1", "continuous", 0, 1)],
            constraints=[OptimizationConstraint("c1", "inequality")]
        ))
        
        suggestions = analyzer.suggest_algorithms(simple_metrics)
        
        assert len(suggestions) > 0
        assert all(isinstance(alg, str) and isinstance(score, float) for alg, score in suggestions)
        assert all(0 <= score <= 1 for _, score in suggestions)


class TestOptimizationResult:
    """Test optimization result data structure"""
    
    def test_result_creation(self):
        """Test optimization result creation"""
        result = OptimizationResult(
            algorithm_used="cp_sat",
            status=OptimizationStatus.COMPLETED,
            objective_value=123.45,
            solve_time_seconds=5.2
        )
        
        assert result.algorithm_used == "cp_sat"
        assert result.status == OptimizationStatus.COMPLETED
        assert result.objective_value == 123.45
        assert result.solve_time_seconds == 5.2
    
    def test_feasibility_check(self):
        """Test feasibility checking"""
        # Feasible result
        feasible_result = OptimizationResult(constraint_violations=[])
        assert feasible_result.is_feasible()
        
        # Infeasible result
        infeasible_result = OptimizationResult(constraint_violations=["violation1"])
        assert not infeasible_result.is_feasible()
    
    def test_solution_quality_assessment(self):
        """Test solution quality assessment"""
        # Optimal solution
        optimal = OptimizationResult(
            constraint_violations=[],
            converged=True,
            objective_value=100.0
        )
        assert optimal.get_solution_quality() == "optimal"
        
        # Infeasible solution
        infeasible = OptimizationResult(constraint_violations=["violation"])
        assert infeasible.get_solution_quality() == "infeasible"
        
        # Suboptimal solution
        suboptimal = OptimizationResult(
            constraint_violations=[],
            converged=False,
            objective_value=100.0
        )
        assert suboptimal.get_solution_quality() == "suboptimal"


if __name__ == "__main__":
    pytest.main([__file__])