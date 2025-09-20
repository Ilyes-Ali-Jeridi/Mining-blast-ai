"""
Tests for optimization engine coordinator.
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from src.drill_blast_system.optimization.engine import (
    OptimizationEngine, OptimizationEngineConfig, AlgorithmType,
    OptimizationProgress, SolutionRanker, OptimizationCache,
    create_optimization_engine
)
from src.drill_blast_system.optimization.data_structures import (
    OptimizationProblem, OptimizationResult, OptimizationStatus,
    BlastPlan, DrillHole, DecisionVariable
)
from src.drill_blast_system.optimization.formulation import ObjectiveFunction, ConstraintManager
from src.drill_blast_system.safety.config import SafetyConfig


class TestOptimizationEngineConfig:
    """Test optimization engine configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = OptimizationEngineConfig()
        
        assert config.max_algorithms == 3
        assert config.parallel_execution is True
        assert config.enable_caching is True
        assert config.enable_progress_tracking is True
        
        # Check default algorithm configs
        assert AlgorithmType.CP_SAT in config.algorithm_configs
        assert AlgorithmType.SCIPY_DE in config.algorithm_configs
        assert AlgorithmType.SCIPY_SLSQP in config.algorithm_configs
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = OptimizationEngineConfig(
            max_algorithms=2,
            parallel_execution=False,
            enable_caching=False
        )
        
        assert config.max_algorithms == 2
        assert config.parallel_execution is False
        assert config.enable_caching is False


class TestSolutionRanker:
    """Test solution ranking functionality"""
    
    def test_rank_empty_results(self):
        """Test ranking empty results list"""
        ranker = SolutionRanker(["objective_value"])
        results = ranker.rank_solutions([])
        assert results == []
    
    def test_rank_single_result(self):
        """Test ranking single result"""
        ranker = SolutionRanker(["objective_value"])
        
        result = OptimizationResult(
            objective_value=100.0,
            status=OptimizationStatus.COMPLETED,
            algorithm_used="test"
        )
        
        results = ranker.rank_solutions([result])
        assert len(results) == 1
        assert results[0] == result
    
    def test_rank_multiple_results(self):
        """Test ranking multiple results"""
        ranker = SolutionRanker(["objective_value", "constraint_satisfaction"])
        
        # Create results with different objective values
        result1 = OptimizationResult(
            objective_value=100.0,
            status=OptimizationStatus.COMPLETED,
            algorithm_used="algo1"
        )
        
        result2 = OptimizationResult(
            objective_value=50.0,  # Better objective
            status=OptimizationStatus.COMPLETED,
            algorithm_used="algo2"
        )
        
        result3 = OptimizationResult(
            objective_value=200.0,  # Worse objective
            status=OptimizationStatus.COMPLETED,
            algorithm_used="algo3"
        )
        
        results = ranker.rank_solutions([result1, result2, result3])
        
        # Should be ranked by objective value (lower is better)
        assert len(results) == 3
        assert results[0].algorithm_used == "algo2"  # Best objective
        assert results[1].algorithm_used == "algo1"  # Middle objective
        assert results[2].algorithm_used == "algo3"  # Worst objective
    
    def test_rank_with_failed_results(self):
        """Test ranking with failed results"""
        ranker = SolutionRanker(["objective_value"])
        
        good_result = OptimizationResult(
            objective_value=100.0,
            status=OptimizationStatus.COMPLETED,
            algorithm_used="good"
        )
        
        failed_result = OptimizationResult(
            status=OptimizationStatus.FAILED,
            algorithm_used="failed"
        )
        
        results = ranker.rank_solutions([failed_result, good_result])
        
        # Good result should come first, failed result last
        assert len(results) == 2
        assert results[0].algorithm_used == "good"
        assert results[1].algorithm_used == "failed"


class TestOptimizationCache:
    """Test optimization result caching"""
    
    def test_cache_miss(self):
        """Test cache miss"""
        cache = OptimizationCache(max_size=10, ttl_hours=1)
        
        problem = OptimizationProblem(
            problem_id="test",
            site_data={"site_id": "test_site"}
        )
        
        result = cache.get(problem)
        assert result is None
    
    def test_cache_hit(self):
        """Test cache hit"""
        cache = OptimizationCache(max_size=10, ttl_hours=1)
        
        problem = OptimizationProblem(
            problem_id="test",
            site_data={"site_id": "test_site"}
        )
        
        original_result = OptimizationResult(
            objective_value=100.0,
            algorithm_used="test"
        )
        
        # Store result
        cache.put(problem, original_result)
        
        # Retrieve result
        cached_result = cache.get(problem)
        assert cached_result is not None
        assert cached_result.objective_value == 100.0
        assert cached_result.algorithm_used == "test"
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        cache = OptimizationCache(max_size=10, ttl_hours=1)
        
        problem = OptimizationProblem(
            problem_id="test",
            site_data={"site_id": "test_site"}
        )
        
        result = OptimizationResult(objective_value=100.0)
        cache.put(problem, result)
        
        # Manually expire the entry by modifying timestamp
        problem_hash = cache.get_problem_hash(problem)
        if problem_hash in cache.cache:
            # Set timestamp to 2 hours ago to force expiry
            from datetime import datetime, timedelta
            cache.cache[problem_hash].timestamp = datetime.utcnow() - timedelta(hours=2)
        
        # Should be expired now
        cached_result = cache.get(problem)
        assert cached_result is None
    
    def test_cache_eviction(self):
        """Test cache eviction when at capacity"""
        cache = OptimizationCache(max_size=2, ttl_hours=1)
        
        # Add first result
        problem1 = OptimizationProblem(
            problem_id="test1",
            site_data={"site_id": "site1"}
        )
        result1 = OptimizationResult(objective_value=100.0)
        cache.put(problem1, result1)
        
        # Add second result
        problem2 = OptimizationProblem(
            problem_id="test2", 
            site_data={"site_id": "site2"}
        )
        result2 = OptimizationResult(objective_value=200.0)
        cache.put(problem2, result2)
        
        # Add third result (should evict oldest)
        problem3 = OptimizationProblem(
            problem_id="test3",
            site_data={"site_id": "site3"}
        )
        result3 = OptimizationResult(objective_value=300.0)
        cache.put(problem3, result3)
        
        # First result should be evicted
        assert cache.get(problem1) is None
        assert cache.get(problem2) is not None
        assert cache.get(problem3) is not None


class TestOptimizationEngine:
    """Test optimization engine coordinator"""
    
    def create_test_problem(self) -> OptimizationProblem:
        """Create a test optimization problem"""
        variables = [
            DecisionVariable(
                name="charge_1",
                var_type="continuous",
                lower_bound=0.0,
                upper_bound=50.0,
                initial_value=25.0
            ),
            DecisionVariable(
                name="delay_1",
                var_type="integer",
                lower_bound=0,
                upper_bound=1000,
                initial_value=0
            )
        ]
        
        problem = OptimizationProblem(
            problem_id="test_problem",
            site_data={
                "site_id": "test_site",
                "hole_pattern": [
                    DrillHole(
                        hole_id="1",
                        coordinates=(0, 0, 0),
                        depth=10.0,
                        diameter=150.0,
                        charge_kg=25.0
                    )
                ]
            },
            variables=variables
        )
        
        problem.calculate_problem_size()
        return problem
    
    def test_engine_initialization(self):
        """Test engine initialization"""
        config = OptimizationEngineConfig(enable_caching=False)
        engine = OptimizationEngine(config=config)
        
        assert engine.config == config
        assert engine.cache is None  # Caching disabled
        assert len(engine.optimizers) >= 1  # At least one optimizer available
    
    def test_algorithm_selection(self):
        """Test algorithm selection based on problem characteristics"""
        engine = OptimizationEngine()
        problem = self.create_test_problem()
        
        selected = engine._select_algorithms(problem)
        
        assert len(selected) > 0
        assert len(selected) <= engine.config.max_algorithms
        
        # Should include CP-SAT for discrete variables
        assert AlgorithmType.CP_SAT in selected
    
    @patch('src.drill_blast_system.optimization.engine.CPSATOptimizer')
    def test_single_algorithm_execution(self, mock_cp_sat):
        """Test running a single algorithm"""
        # Mock the optimizer
        mock_optimizer = Mock()
        mock_result = OptimizationResult(
            objective_value=100.0,
            status=OptimizationStatus.COMPLETED,
            algorithm_used="cp_sat"
        )
        mock_optimizer.optimize.return_value = mock_result
        mock_cp_sat.return_value = mock_optimizer
        
        # Create engine with only CP-SAT
        config = OptimizationEngineConfig(max_algorithms=1, parallel_execution=False)
        engine = OptimizationEngine(config=config)
        
        problem = self.create_test_problem()
        result = engine._run_single_algorithm(
            AlgorithmType.CP_SAT, mock_optimizer, problem, None
        )
        
        assert result.objective_value == 100.0
        assert result.algorithm_used == "cp_sat"
        mock_optimizer.optimize.assert_called_once()
    
    def test_progress_tracking(self):
        """Test progress tracking functionality"""
        progress_updates = []
        
        def progress_callback(progress: OptimizationProgress):
            progress_updates.append(progress.to_dict())
        
        config = OptimizationEngineConfig(enable_progress_tracking=True)
        engine = OptimizationEngine(config=config, progress_callback=progress_callback)
        
        problem = self.create_test_problem()
        engine._initialize_progress_tracking(problem)
        
        # Check initial progress
        assert len(progress_updates) > 0
        initial_progress = progress_updates[0]
        assert initial_progress["status"] == OptimizationStatus.RUNNING.value
        assert initial_progress["overall_progress"] == 0.0
    
    def test_caching_integration(self):
        """Test caching integration"""
        config = OptimizationEngineConfig(enable_caching=True)
        engine = OptimizationEngine(config=config)
        
        problem = self.create_test_problem()
        
        # First call should miss cache
        cached_result = engine.cache.get(problem)
        assert cached_result is None
        
        # Store a result
        result = OptimizationResult(objective_value=100.0)
        engine.cache.put(problem, result)
        
        # Second call should hit cache
        cached_result = engine.cache.get(problem)
        assert cached_result is not None
        assert cached_result.objective_value == 100.0
    
    def test_get_engine_info(self):
        """Test engine information retrieval"""
        engine = OptimizationEngine()
        info = engine.get_engine_info()
        
        assert "available_algorithms" in info
        assert "max_algorithms" in info
        assert "parallel_execution" in info
        assert "caching_enabled" in info
        assert isinstance(info["available_algorithms"], list)
    
    def test_factory_function(self):
        """Test factory function"""
        engine = create_optimization_engine(
            enable_caching=False,
            max_algorithms=2,
            parallel_execution=False
        )
        
        assert engine.config.enable_caching is False
        assert engine.config.max_algorithms == 2
        assert engine.config.parallel_execution is False


class TestOptimizationProgress:
    """Test optimization progress tracking"""
    
    def test_progress_initialization(self):
        """Test progress initialization"""
        progress = OptimizationProgress()
        
        assert progress.total_algorithms == 0
        assert progress.completed_algorithms == 0
        assert progress.overall_progress == 0.0
        assert progress.status == OptimizationStatus.NOT_STARTED
    
    def test_progress_to_dict(self):
        """Test progress serialization"""
        progress = OptimizationProgress(
            total_algorithms=3,
            completed_algorithms=1,
            current_algorithm="cp_sat",
            overall_progress=0.33
        )
        
        progress_dict = progress.to_dict()
        
        assert progress_dict["total_algorithms"] == 3
        assert progress_dict["completed_algorithms"] == 1
        assert progress_dict["current_algorithm"] == "cp_sat"
        assert progress_dict["overall_progress"] == 0.33


if __name__ == "__main__":
    pytest.main([__file__])