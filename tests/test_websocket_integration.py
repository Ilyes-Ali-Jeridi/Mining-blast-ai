"""
Simple integration test for WebSocket optimization progress functionality.
Tests requirement 8.2: Real-time solver iterations and objective improvements.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock

from src.drill_blast_system.api.websocket import ConnectionManager, OptimizationProgressBroadcaster
from src.drill_blast_system.optimization.progress_tracker import ProgressTracker, ProgressEventType
from src.drill_blast_system.optimization.data_structures import OptimizationStatus


class TestWebSocketIntegration:
    """Test WebSocket integration functionality"""
    
    def test_connection_manager_basic(self):
        """Test basic connection manager functionality"""
        manager = ConnectionManager()
        
        # Test initial state
        assert manager.get_connection_count() == 0
        assert len(manager.get_stats()["optimization_sessions"]) == 0
        
        # Test stats
        stats = manager.get_stats()
        assert "total_connections" in stats
        assert "active_optimizations" in stats
        assert "optimization_sessions" in stats
    
    def test_progress_tracker_basic(self):
        """Test basic progress tracker functionality"""
        tracker = ProgressTracker("test_opt_123")
        
        # Test initial state
        progress = tracker.get_progress()
        assert progress.optimization_id == "test_opt_123"
        assert progress.status == OptimizationStatus.NOT_STARTED
        assert progress.total_algorithms == 0
        
        # Test starting optimization
        tracker.start_optimization(2, ["cp_sat", "scipy_de"])
        progress = tracker.get_progress()
        assert progress.status == OptimizationStatus.RUNNING
        assert progress.total_algorithms == 2
        assert len(progress.algorithms) == 2
        
        # Test algorithm progress
        tracker.start_algorithm("cp_sat")
        tracker.update_algorithm_progress(
            "cp_sat",
            iterations=10,
            current_objective=100.0,
            progress_percentage=50.0
        )
        
        progress = tracker.get_progress()
        algo_progress = progress.algorithms["cp_sat"]
        assert algo_progress.iterations == 10
        assert algo_progress.current_objective == 100.0
        assert algo_progress.progress_percentage == 50.0
        
        # Test completion
        tracker.complete_optimization({"objective": 90.0})
        progress = tracker.get_progress()
        assert progress.status == OptimizationStatus.COMPLETED
        assert progress.overall_progress == 1.0
    
    def test_progress_broadcaster_basic(self):
        """Test basic progress broadcaster functionality"""
        mock_manager = AsyncMock()
        broadcaster = OptimizationProgressBroadcaster(mock_manager)
        
        # Test that broadcaster can be created
        assert broadcaster is not None
        assert broadcaster.manager is mock_manager
    
    def test_event_callback_system(self):
        """Test progress tracker event callback system"""
        tracker = ProgressTracker("test_opt_123")
        events_received = []
        
        def event_callback(event):
            events_received.append(event)
        
        tracker.add_event_callback(event_callback)
        
        # Start optimization and check events
        tracker.start_optimization(1, ["test_algo"])
        assert len(events_received) == 1
        assert events_received[0].event_type == ProgressEventType.OPTIMIZATION_STARTED
        
        # Start algorithm and check events
        tracker.start_algorithm("test_algo")
        assert len(events_received) == 2
        assert events_received[1].event_type == ProgressEventType.ALGORITHM_STARTED
        
        # Complete optimization and check events
        tracker.complete_optimization({"result": "success"})
        completion_events = [e for e in events_received if e.event_type == ProgressEventType.OPTIMIZATION_COMPLETED]
        assert len(completion_events) == 1
    
    def test_cancellation_functionality(self):
        """Test optimization cancellation"""
        tracker = ProgressTracker("test_opt_123")
        
        # Start optimization
        tracker.start_optimization(1, ["test_algo"])
        assert not tracker.is_cancelled()
        
        # Cancel optimization
        tracker.cancel_optimization()
        assert tracker.is_cancelled()
        
        progress = tracker.get_progress()
        assert progress.status == OptimizationStatus.CANCELLED
    
    def test_progress_serialization(self):
        """Test that progress data can be serialized to JSON"""
        tracker = ProgressTracker("test_opt_123")
        tracker.start_optimization(2, ["cp_sat", "scipy_de"])
        tracker.start_algorithm("cp_sat")
        tracker.update_algorithm_progress(
            "cp_sat",
            iterations=50,
            current_objective=123.45,
            progress_percentage=75.0
        )
        
        progress = tracker.get_progress()
        progress_dict = progress.to_dict()
        
        # Test that it can be serialized to JSON
        json_str = json.dumps(progress_dict)
        assert json_str is not None
        
        # Test that it can be deserialized
        deserialized = json.loads(json_str)
        assert deserialized["optimization_id"] == "test_opt_123"
        assert deserialized["total_algorithms"] == 2
        assert "cp_sat" in deserialized["algorithms"]
    
    def test_multiple_algorithm_progress(self):
        """Test tracking progress for multiple algorithms"""
        tracker = ProgressTracker("test_opt_123")
        tracker.start_optimization(3, ["cp_sat", "scipy_de", "genetic"])
        
        # Start and progress first algorithm
        tracker.start_algorithm("cp_sat")
        tracker.update_algorithm_progress("cp_sat", iterations=100, progress_percentage=100.0)
        tracker.complete_algorithm("cp_sat", {"objective": 100.0})
        
        # Start and progress second algorithm
        tracker.start_algorithm("scipy_de")
        tracker.update_algorithm_progress("scipy_de", iterations=50, progress_percentage=50.0)
        
        progress = tracker.get_progress()
        
        # Check overall progress
        assert progress.completed_algorithms == 1
        assert progress.current_algorithm == "scipy_de"
        assert progress.overall_progress > 0.0 and progress.overall_progress < 1.0
        
        # Check individual algorithm progress
        assert progress.algorithms["cp_sat"].status == OptimizationStatus.COMPLETED
        assert progress.algorithms["scipy_de"].status == OptimizationStatus.RUNNING
        assert progress.algorithms["genetic"].status == OptimizationStatus.NOT_STARTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])