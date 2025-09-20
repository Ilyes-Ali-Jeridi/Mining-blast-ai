"""
Example demonstrating WebSocket optimization progress functionality.
Shows how to use real-time optimization progress tracking with WebSocket updates.
"""

import asyncio
import json
import time
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.drill_blast_system.api.websocket import ConnectionManager, OptimizationProgressBroadcaster
from src.drill_blast_system.optimization.progress_tracker import (
    ProgressTracker, ProgressTrackerManager, ProgressEvent
)
from src.drill_blast_system.optimization.data_structures import OptimizationStatus


async def simulate_websocket_client(manager: ConnectionManager, optimization_id: str):
    """
    Simulate a WebSocket client receiving optimization progress updates.
    
    Args:
        manager: Connection manager instance
        optimization_id: Optimization session ID to monitor
    """
    print(f"🔌 WebSocket client connecting to optimization {optimization_id}")
    
    # Simulate WebSocket connection (in real implementation, this would be a WebSocket)
    class MockWebSocket:
        def __init__(self):
            self.messages = []
        
        async def accept(self):
            pass
        
        async def send_text(self, message: str):
            data = json.loads(message)
            print(f"📨 WebSocket received: {data['type']}")
            if data['type'] == 'optimization_progress':
                if 'event' in data:
                    print(f"   Event: {data['event']}")
                if 'algorithm' in data:
                    print(f"   Algorithm: {data['algorithm']}")
                if 'iterations' in data:
                    print(f"   Iterations: {data['iterations']}")
                if 'current_objective' in data:
                    print(f"   Objective: {data['current_objective']:.2f}")
            self.messages.append(data)
    
    mock_websocket = MockWebSocket()
    connection_id = await manager.connect(mock_websocket, optimization_id)
    
    # Keep connection alive for the duration of the example
    await asyncio.sleep(15)  # Wait for optimization to complete
    
    manager.disconnect(connection_id)
    print(f"🔌 WebSocket client disconnected from optimization {optimization_id}")
    
    return mock_websocket.messages


async def simulate_optimization_with_progress(optimization_id: str, tracker: ProgressTracker):
    """
    Simulate an optimization process with realistic progress updates.
    
    Args:
        optimization_id: Optimization session ID
        tracker: Progress tracker instance
    """
    print(f"🚀 Starting optimization simulation: {optimization_id}")
    
    # Define algorithms to run
    algorithms = ["cp_sat", "scipy_de", "genetic"]
    
    # Start optimization
    tracker.start_optimization(len(algorithms), algorithms)
    print(f"📊 Optimization started with {len(algorithms)} algorithms")
    
    # Simulate each algorithm
    for i, algorithm in enumerate(algorithms):
        print(f"\n🔧 Starting algorithm: {algorithm}")
        tracker.start_algorithm(algorithm)
        
        # Simulate algorithm iterations
        max_iterations = 50 + i * 25  # Different algorithms have different iteration counts
        best_objective = 1000.0
        
        for iteration in range(1, max_iterations + 1):
            # Simulate objective improvement
            improvement = (iteration / max_iterations) * 0.8 + 0.1  # 10-90% improvement
            current_objective = best_objective * (1.0 - improvement)
            
            if current_objective < best_objective:
                best_objective = current_objective
            
            # Update progress
            progress_percentage = (iteration / max_iterations) * 100
            tracker.update_algorithm_progress(
                algorithm_name=algorithm,
                iterations=iteration,
                function_evaluations=iteration * 2,
                current_objective=current_objective,
                progress_percentage=progress_percentage,
                message=f"Iteration {iteration}/{max_iterations}"
            )
            
            # Simulate computation time
            await asyncio.sleep(0.1)
            
            # Check for cancellation
            if tracker.is_cancelled():
                print(f"❌ Optimization cancelled during {algorithm}")
                return
        
        # Complete algorithm
        result = {
            "objective_value": best_objective,
            "iterations": max_iterations,
            "converged": True,
            "solve_time": max_iterations * 0.1
        }
        tracker.complete_algorithm(algorithm, result)
        print(f"✅ Algorithm {algorithm} completed with objective: {best_objective:.2f}")
    
    # Complete optimization
    final_result = {
        "best_objective": best_objective,
        "total_algorithms": len(algorithms),
        "total_time": sum(50 + i * 25 for i in range(len(algorithms))) * 0.1
    }
    tracker.complete_optimization(final_result)
    print(f"🎉 Optimization completed! Best objective: {best_objective:.2f}")


async def websocket_progress_callback(event: ProgressEvent, broadcaster: OptimizationProgressBroadcaster):
    """
    Callback to broadcast progress events via WebSocket.
    
    Args:
        event: Progress event to broadcast
        broadcaster: WebSocket broadcaster instance
    """
    await broadcaster.send_progress_update(
        event.optimization_id,
        event.to_dict()
    )


async def main():
    """Main example function demonstrating WebSocket optimization progress."""
    
    print("🌟 WebSocket Optimization Progress Example")
    print("=" * 50)
    
    # Create components
    connection_manager = ConnectionManager()
    progress_broadcaster = OptimizationProgressBroadcaster(connection_manager)
    tracker_manager = ProgressTrackerManager()
    
    # Create optimization session
    optimization_id = "example_opt_123"
    tracker = tracker_manager.create_tracker(optimization_id, update_interval=0.05)
    
    # Set up WebSocket progress broadcasting
    async def websocket_callback(event):
        await websocket_progress_callback(event, progress_broadcaster)
    
    tracker.add_event_callback(websocket_callback, is_async=True)
    
    # Start WebSocket client simulation
    client_task = asyncio.create_task(
        simulate_websocket_client(connection_manager, optimization_id)
    )
    
    # Start optimization simulation
    optimization_task = asyncio.create_task(
        simulate_optimization_with_progress(optimization_id, tracker)
    )
    
    # Wait for both to complete
    messages, _ = await asyncio.gather(client_task, optimization_task)
    
    # Display results
    print("\n📈 WebSocket Messages Summary:")
    print("-" * 30)
    
    message_types = {}
    for message in messages:
        msg_type = message.get('type', 'unknown')
        message_types[msg_type] = message_types.get(msg_type, 0) + 1
    
    for msg_type, count in message_types.items():
        print(f"  {msg_type}: {count} messages")
    
    # Display final progress
    final_progress = tracker.get_progress()
    print(f"\n📊 Final Progress Summary:")
    print(f"  Status: {final_progress.status.value}")
    print(f"  Overall Progress: {final_progress.overall_progress * 100:.1f}%")
    print(f"  Completed Algorithms: {final_progress.completed_algorithms}/{final_progress.total_algorithms}")
    print(f"  Best Objective: {final_progress.best_objective_overall:.2f}")
    print(f"  Total Time: {final_progress.get_elapsed_time():.1f} seconds")
    
    # Clean up
    tracker_manager.remove_tracker(optimization_id)
    
    print("\n✨ Example completed successfully!")


async def cancellation_example():
    """Example demonstrating optimization cancellation via WebSocket."""
    
    print("\n🛑 Cancellation Example")
    print("=" * 30)
    
    # Create components
    connection_manager = ConnectionManager()
    progress_broadcaster = OptimizationProgressBroadcaster(connection_manager)
    tracker_manager = ProgressTrackerManager()
    
    # Create optimization session
    optimization_id = "cancellation_example"
    tracker = tracker_manager.create_tracker(optimization_id)
    
    # Set up WebSocket progress broadcasting
    async def websocket_callback(event):
        await progress_broadcaster.send_progress_update(
            event.optimization_id,
            event.to_dict()
        )
    
    tracker.add_event_callback(websocket_callback, is_async=True)
    
    # Start optimization
    tracker.start_optimization(2, ["cp_sat", "scipy_de"])
    tracker.start_algorithm("cp_sat")
    
    # Simulate some progress
    for i in range(10):
        tracker.update_algorithm_progress(
            "cp_sat",
            iterations=i * 10,
            current_objective=1000.0 - i * 50,
            progress_percentage=i * 10
        )
        await asyncio.sleep(0.1)
    
    # Cancel optimization
    print("❌ Cancelling optimization...")
    tracker.cancel_optimization()
    
    # Check final state
    final_progress = tracker.get_progress()
    print(f"Final status: {final_progress.status.value}")
    print(f"Is cancelled: {tracker.is_cancelled()}")
    
    # Clean up
    tracker_manager.remove_tracker(optimization_id)


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Run cancellation example
    asyncio.run(cancellation_example())