"""
Problem complexity analysis and algorithm selection utilities.
"""

from typing import Dict, List, Tuple, Any
import numpy as np
from dataclasses import dataclass
import logging

from .data_structures import OptimizationProblem, DecisionVariable


@dataclass
class ComplexityMetrics:
    """Metrics for assessing optimization problem complexity"""
    
    # Problem size
    num_variables: int
    num_constraints: int
    num_holes: int
    
    # Variable type distribution
    num_continuous: int
    num_integer: int
    num_binary: int
    
    # Constraint characteristics
    num_linear_constraints: int
    num_nonlinear_constraints: int
    
    # Problem structure
    sparsity_ratio: float  # Fraction of zero entries in constraint matrix
    condition_number: float  # Numerical conditioning
    
    # Complexity assessment
    complexity_score: float
    complexity_class: str  # 'simple', 'moderate', 'complex', 'very_complex'
    
    # Time estimates (seconds)
    estimated_cp_sat_time: float
    estimated_scipy_time: float
    estimated_genetic_time: float


class ComplexityAnalyzer:
    """Analyzes optimization problem complexity and suggests algorithms"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".ComplexityAnalyzer")
    
    def analyze_problem(self, problem: OptimizationProblem) -> ComplexityMetrics:
        """
        Analyze problem complexity and provide metrics.
        
        Args:
            problem: Optimization problem to analyze
            
        Returns:
            Complexity metrics and recommendations
        """
        self.logger.info(f"Analyzing complexity for problem {problem.problem_id}")
        
        # Count variable types
        var_counts = self._count_variable_types(problem.variables)
        
        # Estimate constraint characteristics
        constraint_counts = self._analyze_constraints(problem.constraints)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(
            problem.num_variables, 
            problem.num_constraints,
            var_counts,
            constraint_counts
        )
        
        # Classify complexity
        complexity_class = self._classify_complexity(complexity_score)
        
        # Estimate solve times
        time_estimates = self._estimate_solve_times(
            problem.num_variables,
            problem.num_constraints, 
            complexity_class
        )
        
        metrics = ComplexityMetrics(
            num_variables=problem.num_variables,
            num_constraints=problem.num_constraints,
            num_holes=problem.num_holes,
            num_continuous=var_counts['continuous'],
            num_integer=var_counts['integer'],
            num_binary=var_counts['binary'],
            num_linear_constraints=constraint_counts['linear'],
            num_nonlinear_constraints=constraint_counts['nonlinear'],
            sparsity_ratio=0.8,  # Typical for blast problems
            condition_number=1.0,  # Placeholder
            complexity_score=complexity_score,
            complexity_class=complexity_class,
            estimated_cp_sat_time=time_estimates['cp_sat'],
            estimated_scipy_time=time_estimates['scipy'],
            estimated_genetic_time=time_estimates['genetic']
        )
        
        self.logger.info(f"Problem complexity: {complexity_class} (score: {complexity_score:.2f})")
        
        return metrics
    
    def _count_variable_types(self, variables: List[DecisionVariable]) -> Dict[str, int]:
        """Count variables by type"""
        counts = {'continuous': 0, 'integer': 0, 'binary': 0}
        
        for var in variables:
            if var.var_type == 'continuous':
                counts['continuous'] += 1
            elif var.var_type == 'integer':
                counts['integer'] += 1
            elif var.var_type == 'binary':
                counts['binary'] += 1
        
        return counts
    
    def _analyze_constraints(self, constraints: List) -> Dict[str, int]:
        """Analyze constraint characteristics"""
        # For now, assume most constraints are linear
        # In a full implementation, this would analyze constraint functions
        return {
            'linear': len(constraints),
            'nonlinear': 0
        }
    
    def _calculate_complexity_score(self, 
                                  num_vars: int,
                                  num_constraints: int,
                                  var_counts: Dict[str, int],
                                  constraint_counts: Dict[str, int]) -> float:
        """Calculate overall complexity score"""
        
        # Base complexity from problem size
        size_complexity = np.log10(max(1, num_vars * num_constraints))
        
        # Variable type complexity (integer/binary variables are harder)
        var_complexity = (
            var_counts['continuous'] * 1.0 +
            var_counts['integer'] * 2.0 +
            var_counts['binary'] * 1.5
        ) / max(1, num_vars)
        
        # Constraint complexity (nonlinear constraints are harder)
        constraint_complexity = (
            constraint_counts['linear'] * 1.0 +
            constraint_counts['nonlinear'] * 3.0
        ) / max(1, num_constraints)
        
        # Combined score
        total_score = size_complexity + var_complexity + constraint_complexity
        
        return total_score
    
    def _classify_complexity(self, score: float) -> str:
        """Classify complexity based on score"""
        if score < 3.0:
            return "simple"
        elif score < 5.0:
            return "moderate"
        elif score < 7.0:
            return "complex"
        else:
            return "very_complex"
    
    def _estimate_solve_times(self, 
                            num_vars: int,
                            num_constraints: int,
                            complexity_class: str) -> Dict[str, float]:
        """Estimate solve times for different algorithms"""
        
        # Base time estimates (seconds)
        base_times = {
            "simple": {"cp_sat": 0.1, "scipy": 0.5, "genetic": 2.0},
            "moderate": {"cp_sat": 1.0, "scipy": 5.0, "genetic": 10.0},
            "complex": {"cp_sat": 10.0, "scipy": 30.0, "genetic": 60.0},
            "very_complex": {"cp_sat": 60.0, "scipy": 300.0, "genetic": 600.0}
        }
        
        base = base_times.get(complexity_class, base_times["moderate"])
        
        # Scale by problem size
        size_factor = np.sqrt(num_vars * num_constraints / 100.0)
        
        return {
            "cp_sat": base["cp_sat"] * size_factor,
            "scipy": base["scipy"] * size_factor,
            "genetic": base["genetic"] * size_factor
        }
    
    def suggest_algorithms(self, metrics: ComplexityMetrics) -> List[Tuple[str, float]]:
        """
        Suggest algorithms with priority scores.
        
        Args:
            metrics: Problem complexity metrics
            
        Returns:
            List of (algorithm_name, priority_score) tuples, sorted by priority
        """
        suggestions = []
        
        # CP-SAT is good for discrete variables and moderate complexity
        if metrics.num_integer > 0 or metrics.num_binary > 0:
            cp_sat_score = 0.9 if metrics.complexity_class in ["simple", "moderate"] else 0.6
            suggestions.append(("cp_sat", cp_sat_score))
        
        # SciPy methods are good for continuous problems
        if metrics.num_continuous > 0:
            scipy_score = 0.8 if metrics.complexity_class in ["simple", "moderate"] else 0.5
            suggestions.append(("scipy_differential_evolution", scipy_score))
            
            # SLSQP is good for polishing but needs good starting point
            suggestions.append(("scipy_slsqp", scipy_score * 0.7))
        
        # Genetic algorithms are good for complex, multi-objective problems
        genetic_score = {
            "simple": 0.3,
            "moderate": 0.6,
            "complex": 0.8,
            "very_complex": 0.9
        }.get(metrics.complexity_class, 0.5)
        suggestions.append(("genetic_algorithm", genetic_score))
        
        # Sort by priority score (descending)
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        return suggestions
    
    def estimate_memory_usage(self, metrics: ComplexityMetrics) -> Dict[str, float]:
        """Estimate memory usage for different algorithms (MB)"""
        
        # Rough estimates based on problem size
        base_memory = metrics.num_variables * metrics.num_constraints * 8 / (1024 * 1024)  # MB
        
        return {
            "cp_sat": base_memory * 2.0,  # CP-SAT uses more memory for search tree
            "scipy": base_memory * 1.0,   # SciPy is memory efficient
            "genetic": base_memory * 5.0  # Genetic algorithms store populations
        }
    
    def check_resource_limits(self, 
                            metrics: ComplexityMetrics,
                            max_time_seconds: float = 300.0,
                            max_memory_mb: float = 1000.0) -> Dict[str, bool]:
        """Check if algorithms are feasible within resource limits"""
        
        memory_usage = self.estimate_memory_usage(metrics)
        
        feasible = {}
        
        # Check time limits
        feasible["cp_sat"] = (
            metrics.estimated_cp_sat_time <= max_time_seconds and
            memory_usage["cp_sat"] <= max_memory_mb
        )
        
        feasible["scipy"] = (
            metrics.estimated_scipy_time <= max_time_seconds and
            memory_usage["scipy"] <= max_memory_mb
        )
        
        feasible["genetic"] = (
            metrics.estimated_genetic_time <= max_time_seconds and
            memory_usage["genetic"] <= max_memory_mb
        )
        
        return feasible


def estimate_problem_complexity(problem: OptimizationProblem) -> str:
    """
    Estimate problem complexity class for algorithm selection.
    
    Args:
        problem: Optimization problem to analyze
        
    Returns:
        Complexity class: 'low', 'medium', or 'high'
    """
    analyzer = ComplexityAnalyzer()
    metrics = analyzer.analyze_problem(problem)
    
    # Map complexity classes to simplified categories
    complexity_mapping = {
        "simple": "low",
        "moderate": "medium", 
        "complex": "high",
        "very_complex": "high"
    }
    
    return complexity_mapping.get(metrics.complexity_class, "medium")


def analyze_problem_structure(problem: OptimizationProblem) -> Dict[str, Any]:
    """
    Analyze the structure of an optimization problem for algorithm selection.
    
    Args:
        problem: Optimization problem to analyze
        
    Returns:
        Dictionary with structural analysis results
    """
    analyzer = ComplexityAnalyzer()
    metrics = analyzer.analyze_problem(problem)
    
    # Get algorithm suggestions
    algorithm_suggestions = analyzer.suggest_algorithms(metrics)
    
    # Check resource feasibility
    resource_feasibility = analyzer.check_resource_limits(metrics)
    
    return {
        "metrics": metrics,
        "suggested_algorithms": algorithm_suggestions,
        "resource_feasibility": resource_feasibility,
        "recommended_algorithm": algorithm_suggestions[0][0] if algorithm_suggestions else "scipy_differential_evolution"
    }