"""
Integration tests for WebSocket optimization progress functionality.
Tests requirement 8.2: Real-time solver iterations and objective improvements.
"""

import asyncio
import json
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from src.drill_blast_system.api.main import app
from src.drill_blast_system.api.websocket import ConnectionManager, OptimizationProgressBroadcaster
from src.drill_blast_system.optimization.progress_tracker import (
    ProgressTracker, ProgressTrackerManager, ProgressEvent, ProgressEventType
)
from src.drill_blast_system.optimization.data_structures import OptimizationStatus


class TestConnectionManager:
    """Test WebSocket connection management"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        """Test basic connection and disconnection"""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        
        # Test connection
        connection_id = await self.manager.connect(mock_websocket, "test_opt_123")
        
        assert connection_id in self.manager.active_connections
        assert self.manager.get_connection_count() == 1
        assert self.manager.get_optimization_connections("test_opt_123") == 1
        mock_websocket.accept.assert_called_once()
        
        # Test disconnection
        self.manager.disconnect(connection_id)
        
        assert connection_id not in self.manager.active_connections
        assert self.manager.get_connection_count() == 0
        assert self.manager.get_optimization_connections("test_opt_123") == 0
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Test sending messages to specific connections"""
        mock_websocket = AsyncMock()
        connection_id = await self.manager.connect(mock_websocket)
        
        message = {"type": "test", "data": "hello"}
        await self.manager.send_personal_message(message, connection_id)
        
        mock_websocket.send_text.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_broadcast_to_optimization(self):
        """Test broadcasting to optimization session"""
        # Create multiple connections for same optimization
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        
        conn1 = await self.manager.connect(mock_ws1, "opt_123")
        conn2 = await self.manager.connect(mock_ws2, "opt_123")
        
        message = {"type": "progress", "data": "update"}
        await self.manager.broadcast_to_optimization(message, "opt_123")
        
        expected_json = json.dumps(message)
        mock_ws1.send_text.assert_called_once_with(expected_json)
        mock_ws2.send_text.assert_called_once_with(expected_json)
    
    @pytest.mark.asyncio
    async def test_handle_broken_connection(self):
        """Test handling of broken WebSocket connections"""
        mock_websocket = AsyncMock()
        mock_websocket.send_text.side_effect = Exception("Connection broken")
        
        connection_id = await self.manager.connect(mock_websocket)
        
        # This should remove the broken connection
        await self.manager.send_personal_message({"test": "message"}, connection_id)
        
        assert connection_id not in self.manager.active_connections
    
    def test_get_stats(self):
        """Test connection statistics"""
        stats = self.manager.get_stats()
        
        assert "total_connections" in stats
        assert "active_optimizations" in stats
        assert "optimization_sessions" in stats
        assert isinstance(stats["total_connections"], int)


class TestProgressTracker:
    """Test optimization progress tracking"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = ProgressTracker("test_opt_123", update_interval=0.1)
        self.events_received = []
        
        def event_callback(event: ProgressEvent):
            self.events_received.append(event)
        
        self.tracker.add_event_callback(event_callback)
    
    def test_start_optimization(self):
        """Test optimization start tracking"""
        algorithm_names = ["cp_sat", "scipy_de"]
        self.tracker.start_optimization(2, algorithm_names)
        
        progress = self.tracker.get_progress()
        assert progress.status == OptimizationStatus.RUNNING
        assert progress.total_algorithms == 2
        assert len(progress.algorithms) == 2
        assert "cp_sat" in progress.algorithms
        assert "scipy_de" in progress.algorithms
        
        # Check event was emitted
        assert len(self.events_received) == 1
        assert self.events_received[0].event_type == ProgressEventType.OPTIMIZATION_STARTED
    
    def test_algorithm_progress_tracking(self):
        """Test algorithm-level progress tracking"""
        self.tracker.start_optimization(1, ["test_algo"])
        self.tracker.start_algorithm("test_algo")
        
        # Update progress
        self.tracker.update_algorithm_progress(
            algorithm_name="test_algo",
            iterations=50,
            current_objective=123.45,
            progress_percentage=75.0,
            message="Running iteration 50"
        )
        
        progress = self.tracker.get_progress()
        algo_progress = progress.algorithms["test_algo"]
        
        assert algo_progress.iterations == 50
        assert algo_progress.current_objective == 123.45
        assert algo_progress.best_objective == 123.45
        assert algo_progress.progress_percentage == 75.0
        assert algo_progress.current_message == "Running iteration 50"
        
        # Check events
        start_events = [e for e in self.events_received if e.event_type == ProgressEventType.ALGORITHM_STARTED]
        update_events = [e for e in self.events_received if e.event_type == ProgressEventType.ITERATION_UPDATE]
        
        assert len(start_events) == 1
        assert len(update_events) >= 1
    
    def test_optimization_completion(self):
        """Test optimization completion tracking"""
        self.tracker.start_optimization(1, ["test_algo"])
        
        result = {"objective_value": 100.0, "converged": True}
        self.tracker.complete_optimization(result)
        
        progress = self.tracker.get_progress()
        assert progress.status == OptimizationStatus.COMPLETED
        assert progress.overall_progress == 1.0
        
        # Check completion event
        completion_events = [e for e in self.events_received if e.event_type == ProgressEventType.OPTIMIZATION_COMPLETED]
        assert len(completion_events) == 1
        assert completion_events[0].data["result"] == result
    
    def test_optimization_cancellation(self):
        """Test optimization cancellation"""
        self.tracker.start_optimization(1, ["test_algo"])
        self.tracker.cancel_optimization()
        
        assert self.tracker.is_cancelled()
        
        progress = self.tracker.get_progress()
        assert progress.status == OptimizationStatus.CANCELLED
        
        # Check cancellation event
        cancel_events = [e for e in self.events_received if e.event_type == ProgressEventType.OPTIMIZATION_CANCELLED]
        assert len(cancel_events) == 1
    
    def test_progress_update_throttling(self):
        """Test that progress updates are throttled"""
        import time
        
        self.tracker.start_optimization(1, ["test_algo"])
        self.tracker.start_algorithm("test_algo")
        
        # Clear previous events
        self.events_received.clear()
        
        # Send multiple rapid updates
        for i in range(5):
            self.tracker.update_algorithm_progress(
                algorithm_name="test_algo",
                iterations=i,
                current_objective=100.0 - i
            )
        
        # Should be throttled due to update_interval
        update_events = [e for e in self.events_received if e.event_type == ProgressEventType.ITERATION_UPDATE]
        assert len(update_events) <= 2  # Should be throttled
        
        # Wait for throttle interval and try again
        time.sleep(0.2)
        self.tracker.update_algorithm_progress(
            algorithm_name="test_algo",
            iterations=10,
            current_objective=90.0
        )
        
        # Should have more events now
        update_events = [e for e in self.events_received if e.event_type == ProgressEventType.ITERATION_UPDATE]
        assert len(update_events) >= 1


class TestProgressTrackerManager:
    """Test progress tracker manager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ProgressTrackerManager()
    
    def test_create_and_get_tracker(self):
        """Test tracker creation and retrieval"""
        tracker = self.manager.create_tracker("opt_123")
        
        assert tracker is not None
        assert tracker.optimization_id == "opt_123"
        
        # Test retrieval
        retrieved = self.manager.get_tracker("opt_123")
        assert retrieved is tracker
        
        # Test non-existent tracker
        assert self.manager.get_tracker("nonexistent") is None
    
    def test_remove_tracker(self):
        """Test tracker removal"""
        self.manager.create_tracker("opt_123")
        assert self.manager.get_tracker("opt_123") is not None
        
        self.manager.remove_tracker("opt_123")
        assert self.manager.get_tracker("opt_123") is None
    
    def test_cancel_optimization(self):
        """Test optimization cancellation through manager"""
        tracker = self.manager.create_tracker("opt_123")
        
        # Cancel through manager
        result = self.manager.cancel_optimization("opt_123")
        assert result is True
        assert tracker.is_cancelled()
        
        # Try to cancel non-existent optimization
        result = self.manager.cancel_optimization("nonexistent")
        assert result is False
    
    def test_get_all_progress(self):
        """Test getting progress for all optimizations"""
        tracker1 = self.manager.create_tracker("opt_1")
        tracker2 = self.manager.create_tracker("opt_2")
        
        tracker1.start_optimization(1, ["algo1"])
        tracker2.start_optimization(2, ["algo2", "algo3"])
        
        all_progress = self.manager.get_all_progress()
        
        assert len(all_progress) == 2
        assert "opt_1" in all_progress
        assert "opt_2" in all_progress
        assert all_progress["opt_1"].total_algorithms == 1
        assert all_progress["opt_2"].total_algorithms == 2


class TestOptimizationProgressBroadcaster:
    """Test WebSocket progress broadcasting"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_manager = Mock()
        self.broadcaster = OptimizationProgressBroadcaster(self.mock_manager)
    
    @pytest.mark.asyncio
    async def test_send_progress_update(self):
        """Test sending progress updates"""
        self.mock_manager.broadcast_to_optimization = AsyncMock()
        
        progress_data = {
            "algorithm": "cp_sat",
            "iterations": 100,
            "objective": 123.45
        }
        
        await self.broadcaster.send_progress_update("opt_123", progress_data)
        
        self.mock_manager.broadcast_to_optimization.assert_called_once()
        call_args = self.mock_manager.broadcast_to_optimization.call_args
        
        assert call_args[0][1] == "opt_123"  # optimization_id
        message = call_args[0][0]  # message
        assert message["type"] == "optimization_progress"
        assert message["optimization_id"] == "opt_123"
        assert message["algorithm"] == "cp_sat"
        assert message["iterations"] == 100
        assert message["objective"] == 123.45
    
    @pytest.mark.asyncio
    async def test_send_algorithm_events(self):
        """Test algorithm start/completion events"""
        self.mock_manager.broadcast_to_optimization = AsyncMock()
        
        # Test algorithm started
        await self.broadcaster.send_algorithm_started("opt_123", "cp_sat")
        
        call_args = self.mock_manager.broadcast_to_optimization.call_args
        message = call_args[0][0]
        assert message["event"] == "algorithm_started"
        assert message["algorithm"] == "cp_sat"
        
        # Test algorithm completed
        result = {"objective": 100.0, "time": 30.5}
        await self.broadcaster.send_algorithm_completed("opt_123", "cp_sat", result)
        
        call_args = self.mock_manager.broadcast_to_optimization.call_args
        message = call_args[0][0]
        assert message["event"] == "algorithm_completed"
        assert message["algorithm"] == "cp_sat"
        assert message["result"] == result


@pytest.mark.asyncio
class TestWebSocketEndpoints:
    """Test WebSocket endpoint functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment"""
        with self.client.websocket_connect("/api/v1/ws/optimization/test_opt_123") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["optimization_id"] == "test_opt_123"
            assert "connection_id" in data
            assert "timestamp" in data
    
    def test_websocket_ping_pong(self):
        """Test WebSocket ping/pong functionality"""
        with self.client.websocket_connect("/api/v1/ws/optimization/test_opt_123") as websocket:
            # Skip connection confirmation
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response
    
    def test_websocket_invalid_json(self):
        """Test WebSocket handling of invalid JSON"""
        with self.client.websocket_connect("/api/v1/ws/optimization/test_opt_123") as websocket:
            # Skip connection confirmation
            websocket.receive_json()
            
            # Send invalid JSON
            websocket.send_text("invalid json")
            
            # Should receive error message
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid JSON" in response["message"]
    
    def test_general_websocket_connection(self):
        """Test general WebSocket endpoint"""
        with self.client.websocket_connect("/api/v1/ws/general") as websocket:
            # Should receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert "connection_id" in data
            assert "timestamp" in data


@pytest.mark.asyncio
class TestOptimizationAPIEndpoints:
    """Test optimization API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
    
    @patch('src.drill_blast_system.api.routes.optimization.BlastRecordRepository')
    @patch('src.drill_blast_system.api.routes.optimization.SiteRepository')
    def test_start_optimization_async(self, mock_site_repo, mock_blast_repo):
        """Test starting async optimization"""
        # Mock database responses
        mock_blast = Mock()
        mock_blast.id = 1
        mock_blast.blast_status.value = "draft"
        mock_blast_repo.return_value.get_by_id.return_value = mock_blast
        mock_blast_repo.return_value.update.return_value = mock_blast
        
        mock_site = Mock()
        mock_site.id = 1
        mock_site_repo.return_value.get_by_id.return_value = mock_site
        
        # Start optimization
        response = self.client.post(
            "/api/v1/optimization/1/optimize-async",
            json={"max_algorithms": 2, "algorithm_timeout": 60.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "optimization_id" in data
        assert data["blast_id"] == 1
        assert data["status"] == "started"
        assert "websocket_url" in data
        assert "/ws/optimization/" in data["websocket_url"]
    
    def test_get_optimization_status_not_found(self):
        """Test getting status for non-existent optimization"""
        response = self.client.get("/api/v1/optimization/status/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_cancel_optimization_not_found(self):
        """Test cancelling non-existent optimization"""
        response = self.client.post("/api/v1/optimization/cancel/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_list_active_optimizations(self):
        """Test listing active optimizations"""
        response = self.client.get("/api/v1/optimization/active")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "active_optimizations" in data
        assert "total_count" in data
        assert isinstance(data["active_optimizations"], list)
        assert isinstance(data["total_count"], int)


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_optimization_flow(self):
        """Test complete optimization flow with WebSocket updates"""
        # This would be a more complex integration test
        # that simulates a real optimization with WebSocket updates
        
        manager = ConnectionManager()
        tracker_manager = ProgressTrackerManager()
        broadcaster = OptimizationProgressBroadcaster(manager)
        
        # Create optimization tracker
        tracker = tracker_manager.create_tracker("integration_test")
        
        # Set up WebSocket callback
        messages_received = []
        
        async def websocket_callback(event):
            messages_received.append(event.to_dict())
        
        tracker.add_event_callback(websocket_callback, is_async=True)
        
        # Simulate optimization flow
        tracker.start_optimization(2, ["cp_sat", "scipy_de"])
        
        # Simulate first algorithm
        tracker.start_algorithm("cp_sat")
        for i in range(5):
            tracker.update_algorithm_progress(
                "cp_sat",
                iterations=i * 10,
                current_objective=1000.0 - i * 50,
                progress_percentage=i * 20
            )
            await asyncio.sleep(0.01)  # Small delay to allow async processing
        
        tracker.complete_algorithm("cp_sat", {"objective": 750.0, "time": 30.0})
        
        # Simulate second algorithm
        tracker.start_algorithm("scipy_de")
        tracker.update_algorithm_progress(
            "scipy_de",
            iterations=100,
            current_objective=700.0,
            progress_percentage=100.0
        )
        tracker.complete_algorithm("scipy_de", {"objective": 700.0, "time": 45.0})
        
        # Complete optimization
        tracker.complete_optimization({"best_objective": 700.0, "total_time": 75.0})
        
        # Verify events were generated
        assert len(messages_received) > 0
        
        # Check for key events
        event_types = [msg["event_type"] for msg in messages_received]
        assert "optimization_started" in event_types
        assert "algorithm_started" in event_types
        assert "algorithm_completed" in event_types
        assert "optimization_completed" in event_types
        
        # Verify final state
        final_progress = tracker.get_progress()
        assert final_progress.status == OptimizationStatus.COMPLETED
        assert final_progress.overall_progress == 1.0
        assert final_progress.completed_algorithms == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])