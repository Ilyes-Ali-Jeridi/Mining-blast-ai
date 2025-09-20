"""
WebSocket endpoints for real-time optimization progress updates.
Implements requirement 8.2: Real-time solver iterations and objective improvements.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.routing import APIRouter

from ..core.logging import get_logger
from ..optimization.data_structures import OptimizationStatus

logger = get_logger(__name__)

# WebSocket router
websocket_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for optimization progress updates."""
    
    def __init__(self):
        # Active connections: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Optimization sessions: {optimization_id: set of connection_ids}
        self.optimization_sessions: Dict[str, Set[str]] = {}
        # Simulation sessions: {simulation_job_id: set of connection_ids}
        self.simulation_sessions: Dict[str, Set[str]] = {}
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__ + ".ConnectionManager")
    
    async def connect(self, websocket: WebSocket, optimization_id: Optional[str] = None) -> str:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            optimization_id: Optional optimization session ID to join
            
        Returns:
            Connection ID
        """
        await websocket.accept()
        
        # Generate unique connection ID
        connection_id = str(uuid4())
        
        # Store connection
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "optimization_id": optimization_id,
            "last_ping": datetime.utcnow().isoformat()
        }
        
        # Join optimization session if specified
        if optimization_id:
            if optimization_id not in self.optimization_sessions:
                self.optimization_sessions[optimization_id] = set()
            self.optimization_sessions[optimization_id].add(connection_id)
        
        self.logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            optimization_id=optimization_id,
            total_connections=len(self.active_connections)
        )
        
        return connection_id
    
    def disconnect(self, connection_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            connection_id: Connection ID to remove
        """
        if connection_id in self.active_connections:
            # Remove from optimization sessions
            optimization_id = self.connection_metadata.get(connection_id, {}).get("optimization_id")
            if optimization_id and optimization_id in self.optimization_sessions:
                self.optimization_sessions[optimization_id].discard(connection_id)
                # Clean up empty sessions
                if not self.optimization_sessions[optimization_id]:
                    del self.optimization_sessions[optimization_id]
            
            # Remove connection
            del self.active_connections[connection_id]
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            self.logger.info(
                "WebSocket connection closed",
                connection_id=connection_id,
                optimization_id=optimization_id,
                total_connections=len(self.active_connections)
            )
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """
        Send a message to a specific connection.
        
        Args:
            message: Message to send
            connection_id: Target connection ID
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(
                    "Failed to send message to connection",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Remove broken connection
                self.disconnect(connection_id)
    
    async def broadcast_to_optimization(self, message: Dict[str, Any], optimization_id: str):
        """
        Broadcast a message to all connections in an optimization session.
        
        Args:
            message: Message to broadcast
            optimization_id: Optimization session ID
        """
        if optimization_id not in self.optimization_sessions:
            return
        
        # Get all connections for this optimization
        connection_ids = list(self.optimization_sessions[optimization_id])
        
        # Send to all connections
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """
        Broadcast a message to all active connections.
        
        Args:
            message: Message to broadcast
        """
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_optimization_connections(self, optimization_id: str) -> int:
        """Get number of connections for a specific optimization."""
        return len(self.optimization_sessions.get(optimization_id, set()))
    
    async def join_simulation_session(self, connection_id: str, simulation_job_id: str):
        """Add connection to a simulation session."""
        if simulation_job_id not in self.simulation_sessions:
            self.simulation_sessions[simulation_job_id] = set()
        
        self.simulation_sessions[simulation_job_id].add(connection_id)
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["simulation_job_id"] = simulation_job_id
        
        self.logger.info(
            f"Connection {connection_id} joined simulation session {simulation_job_id}"
        )
    
    async def leave_simulation_session(self, connection_id: str, simulation_job_id: str):
        """Remove connection from a simulation session."""
        if simulation_job_id in self.simulation_sessions:
            self.simulation_sessions[simulation_job_id].discard(connection_id)
            
            # Clean up empty sessions
            if not self.simulation_sessions[simulation_job_id]:
                del self.simulation_sessions[simulation_job_id]
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id].pop("simulation_job_id", None)
        
        self.logger.info(
            f"Connection {connection_id} left simulation session {simulation_job_id}"
        )
    
    async def broadcast_to_simulation(self, message: Dict[str, Any], simulation_job_id: str):
        """Broadcast a message to all connections in a simulation session."""
        if simulation_job_id not in self.simulation_sessions:
            return
        
        connection_ids = self.simulation_sessions[simulation_job_id].copy()
        
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    def get_simulation_connections(self, simulation_job_id: str) -> int:
        """Get number of connections for a specific simulation."""
        return len(self.simulation_sessions.get(simulation_job_id, set()))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics."""
        return {
            "total_connections": len(self.active_connections),
            "active_optimizations": len(self.optimization_sessions),
            "active_simulations": len(self.simulation_sessions),
            "optimization_sessions": {
                opt_id: len(connections) 
                for opt_id, connections in self.optimization_sessions.items()
            },
            "simulation_sessions": {
                sim_id: len(connections)
                for sim_id, connections in self.simulation_sessions.items()
            }
        }


# Global connection manager instance
connection_manager = ConnectionManager()


@websocket_router.websocket("/ws/optimization/{optimization_id}")
async def websocket_optimization_progress(websocket: WebSocket, optimization_id: str):
    """
    WebSocket endpoint for optimization progress updates.
    
    Args:
        websocket: WebSocket connection
        optimization_id: Optimization session ID
    """
    connection_id = await connection_manager.connect(websocket, optimization_id)
    
    try:
        # Send initial connection confirmation
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "optimization_id": optimization_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages with timeout for ping/pong
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                    
                    # Update last ping time
                    if connection_id in connection_manager.connection_metadata:
                        connection_manager.connection_metadata[connection_id]["last_ping"] = datetime.utcnow().isoformat()
                
                elif message.get("type") == "cancel_optimization":
                    # Handle optimization cancellation request
                    await handle_optimization_cancellation(optimization_id, connection_id)
                
                elif message.get("type") == "get_status":
                    # Send current optimization status
                    await send_optimization_status(optimization_id, connection_id)
                
            except asyncio.TimeoutError:
                # Send ping to check if connection is still alive
                await connection_manager.send_personal_message({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON message format",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for optimization {optimization_id}")
    except Exception as e:
        logger.error(
            "WebSocket error",
            optimization_id=optimization_id,
            connection_id=connection_id,
            error=str(e)
        )
    finally:
        connection_manager.disconnect(connection_id)


@websocket_router.websocket("/ws/simulation/{simulation_job_id}")
async def websocket_simulation_progress(websocket: WebSocket, simulation_job_id: str):
    """
    WebSocket endpoint for simulation progress updates.
    
    Args:
        websocket: WebSocket connection
        simulation_job_id: Simulation job identifier
    """
    connection_id = await connection_manager.connect(websocket)
    
    try:
        # Join simulation session
        await connection_manager.join_simulation_session(connection_id, simulation_job_id)
        
        logger.info(f"Simulation WebSocket connected: {connection_id} for job {simulation_job_id}")
        
        # Send welcome message
        await connection_manager.send_personal_message({
            "type": "simulation_connected",
            "connection_id": connection_id,
            "simulation_job_id": simulation_job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to simulation {simulation_job_id}"
        }, connection_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages with timeout for ping/pong
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                    
                elif message.get("type") == "cancel_simulation":
                    # Handle simulation cancellation request
                    await handle_simulation_cancellation(simulation_job_id, connection_id)
                
                elif message.get("type") == "get_status":
                    # Send current simulation status
                    await send_simulation_status(simulation_job_id, connection_id)
                
            except asyncio.TimeoutError:
                # Send ping to check if connection is still alive
                await connection_manager.send_personal_message({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON message format",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
    except WebSocketDisconnect:
        logger.info(f"Simulation WebSocket disconnected for job {simulation_job_id}")
    except Exception as e:
        logger.error(
            "Simulation WebSocket error",
            simulation_job_id=simulation_job_id,
            connection_id=connection_id,
            error=str(e)
        )
    finally:
        await connection_manager.leave_simulation_session(connection_id, simulation_job_id)
        connection_manager.disconnect(connection_id)


@websocket_router.websocket("/ws/general")
async def websocket_general(websocket: WebSocket):
    """
    General WebSocket endpoint for system-wide updates.
    
    Args:
        websocket: WebSocket connection
    """
    connection_id = await connection_manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await connection_manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await connection_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
                
            except asyncio.TimeoutError:
                await connection_manager.send_personal_message({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
            
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON message format",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info("General WebSocket disconnected")
    except Exception as e:
        logger.error(
            "General WebSocket error",
            connection_id=connection_id,
            error=str(e)
        )
    finally:
        connection_manager.disconnect(connection_id)


async def handle_optimization_cancellation(optimization_id: str, connection_id: str):
    """
    Handle optimization cancellation request.
    
    Args:
        optimization_id: Optimization session ID
        connection_id: Connection ID that requested cancellation
    """
    # TODO: Implement actual optimization cancellation logic
    # This would integrate with the optimization engine to cancel running optimizations
    
    logger.info(
        "Optimization cancellation requested",
        optimization_id=optimization_id,
        connection_id=connection_id
    )
    
    # Broadcast cancellation to all connections in the optimization session
    await connection_manager.broadcast_to_optimization({
        "type": "optimization_cancelled",
        "optimization_id": optimization_id,
        "cancelled_by": connection_id,
        "timestamp": datetime.utcnow().isoformat()
    }, optimization_id)


async def send_optimization_status(optimization_id: str, connection_id: str):
    """
    Send current optimization status to a connection.
    
    Args:
        optimization_id: Optimization session ID
        connection_id: Connection ID to send status to
    """
    # TODO: Implement actual status retrieval from optimization engine
    # For now, send a placeholder status
    
    status = {
        "type": "optimization_status",
        "optimization_id": optimization_id,
        "status": "running",  # This would come from actual optimization engine
        "progress": 0.5,
        "current_algorithm": "cp_sat",
        "iterations": 100,
        "best_objective": 1234.56,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await connection_manager.send_personal_message(status, connection_id)


class OptimizationProgressBroadcaster:
    """
    Utility class for broadcasting optimization progress updates.
    This class is used by the optimization engine to send real-time updates.
    """
    
    def __init__(self, manager: ConnectionManager = None):
        self.manager = manager or connection_manager
        self.logger = logging.getLogger(__name__ + ".OptimizationProgressBroadcaster")
    
    async def send_progress_update(self, optimization_id: str, progress_data: Dict[str, Any]):
        """
        Send optimization progress update to all connected clients.
        
        Args:
            optimization_id: Optimization session ID
            progress_data: Progress information to broadcast
        """
        message = {
            "type": "optimization_progress",
            "optimization_id": optimization_id,
            "timestamp": datetime.utcnow().isoformat(),
            **progress_data
        }
        
        await self.manager.broadcast_to_optimization(message, optimization_id)
        
        self.logger.debug(
            "Progress update sent",
            optimization_id=optimization_id,
            connections=self.manager.get_optimization_connections(optimization_id)
        )
    
    async def send_algorithm_started(self, optimization_id: str, algorithm_name: str):
        """
        Notify that a new algorithm has started.
        
        Args:
            optimization_id: Optimization session ID
            algorithm_name: Name of the algorithm that started
        """
        await self.send_progress_update(optimization_id, {
            "event": "algorithm_started",
            "algorithm": algorithm_name,
            "message": f"Started {algorithm_name} optimization"
        })
    
    async def send_algorithm_completed(self, optimization_id: str, algorithm_name: str, result: Dict[str, Any]):
        """
        Notify that an algorithm has completed.
        
        Args:
            optimization_id: Optimization session ID
            algorithm_name: Name of the completed algorithm
            result: Algorithm result summary
        """
        await self.send_progress_update(optimization_id, {
            "event": "algorithm_completed",
            "algorithm": algorithm_name,
            "result": result,
            "message": f"Completed {algorithm_name} optimization"
        })
    
    async def send_iteration_update(self, optimization_id: str, iteration_data: Dict[str, Any]):
        """
        Send iteration-level progress update.
        
        Args:
            optimization_id: Optimization session ID
            iteration_data: Iteration progress data
        """
        await self.send_progress_update(optimization_id, {
            "event": "iteration_update",
            **iteration_data
        })
    
    async def send_optimization_completed(self, optimization_id: str, final_result: Dict[str, Any]):
        """
        Notify that optimization has completed.
        
        Args:
            optimization_id: Optimization session ID
            final_result: Final optimization result
        """
        await self.send_progress_update(optimization_id, {
            "event": "optimization_completed",
            "result": final_result,
            "message": "Optimization completed successfully"
        })
    
    async def send_optimization_failed(self, optimization_id: str, error_message: str):
        """
        Notify that optimization has failed.
        
        Args:
            optimization_id: Optimization session ID
            error_message: Error description
        """
        await self.send_progress_update(optimization_id, {
            "event": "optimization_failed",
            "error": error_message,
            "message": f"Optimization failed: {error_message}"
        })
    
    async def send_optimization_cancelled(self, optimization_id: str):
        """
        Notify that optimization was cancelled.
        
        Args:
            optimization_id: Optimization session ID
        """
        await self.send_progress_update(optimization_id, {
            "event": "optimization_cancelled",
            "message": "Optimization was cancelled by user"
        })


# Global broadcaster instance
progress_broadcaster = OptimizationProgressBroadcaster()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager


def get_progress_broadcaster() -> OptimizationProgressBroadcaster:
    """Get the global progress broadcaster instance."""
    return progress_broadcaster

async def handle_simulation_cancellation(simulation_job_id: str, connection_id: str):
    """
    Handle simulation cancellation request.
    
    Args:
        simulation_job_id: Simulation job identifier
        connection_id: Connection identifier
    """
    try:
        # Import here to avoid circular imports
        from .routes.simulations import simulation_manager
        
        # Cancel the simulation
        success = simulation_manager.cancel_job(simulation_job_id)
        
        if success:
            # Broadcast cancellation to all connected clients
            await connection_manager.broadcast_to_simulation({
                "type": "simulation_cancelled",
                "simulation_job_id": simulation_job_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Simulation cancelled by user request"
            }, simulation_job_id)
        else:
            await connection_manager.send_personal_message({
                "type": "error",
                "message": "Failed to cancel simulation",
                "timestamp": datetime.utcnow().isoformat()
            }, connection_id)
        
    except Exception as e:
        logger.error(f"Failed to cancel simulation {simulation_job_id}: {e}")
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Failed to cancel simulation",
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)


async def send_simulation_status(simulation_job_id: str, connection_id: str):
    """
    Send current simulation status to a connection.
    
    Args:
        simulation_job_id: Simulation job identifier
        connection_id: Connection identifier
    """
    try:
        # Import here to avoid circular imports
        from .routes.simulations import simulation_manager
        
        # Get simulation status
        job_status = simulation_manager.get_job_status(simulation_job_id)
        
        if job_status:
            status_message = {
                "type": "simulation_status",
                "simulation_job_id": simulation_job_id,
                "status": job_status["status"],
                "simulation_type": job_status["simulation_type"],
                "created_at": job_status["created_at"],
                "started_at": job_status.get("started_at"),
                "completed_at": job_status.get("completed_at"),
                "has_result": job_status["has_result"],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            status_message = {
                "type": "simulation_status",
                "simulation_job_id": simulation_job_id,
                "status": "not_found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        await connection_manager.send_personal_message(status_message, connection_id)
        
    except Exception as e:
        logger.error(f"Failed to send simulation status: {e}")
        await connection_manager.send_personal_message({
            "type": "error",
            "message": "Failed to get simulation status",
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)


class SimulationProgressBroadcaster:
    """
    Utility class for broadcasting simulation progress updates.
    """
    
    def __init__(self, manager: ConnectionManager = None):
        self.manager = manager or connection_manager
        self.logger = logging.getLogger(__name__ + ".SimulationProgressBroadcaster")
    
    async def send_simulation_started(self, simulation_job_id: str, simulation_type: str):
        """
        Notify that a simulation has started.
        
        Args:
            simulation_job_id: Simulation job identifier
            simulation_type: Type of simulation (blastfoam, yade, physics_only)
        """
        await self.manager.broadcast_to_simulation({
            "type": "simulation_started",
            "simulation_job_id": simulation_job_id,
            "simulation_type": simulation_type,
            "timestamp": datetime.utcnow().isoformat()
        }, simulation_job_id)
    
    async def send_simulation_progress(self, simulation_job_id: str, progress_data: Dict[str, Any]):
        """
        Send simulation progress update to all connected clients.
        
        Args:
            simulation_job_id: Simulation job identifier
            progress_data: Progress information
        """
        message = {
            "type": "simulation_progress",
            "simulation_job_id": simulation_job_id,
            "timestamp": datetime.utcnow().isoformat(),
            **progress_data
        }
        
        await self.manager.broadcast_to_simulation(message, simulation_job_id)
        
        self.logger.debug(
            "Simulation progress update sent",
            simulation_job_id=simulation_job_id,
            progress=progress_data.get("progress", "unknown")
        )
    
    async def send_simulation_completed(self, simulation_job_id: str, result: Dict[str, Any]):
        """
        Notify that simulation has completed.
        
        Args:
            simulation_job_id: Simulation job identifier
            result: Simulation results
        """
        await self.manager.broadcast_to_simulation({
            "type": "simulation_completed",
            "simulation_job_id": simulation_job_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }, simulation_job_id)
    
    async def send_simulation_failed(self, simulation_job_id: str, error_message: str):
        """
        Notify that simulation has failed.
        
        Args:
            simulation_job_id: Simulation job identifier
            error_message: Error description
        """
        await self.manager.broadcast_to_simulation({
            "type": "simulation_failed",
            "simulation_job_id": simulation_job_id,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }, simulation_job_id)
    
    async def send_simulation_cancelled(self, simulation_job_id: str):
        """
        Notify that simulation was cancelled.
        
        Args:
            simulation_job_id: Simulation job identifier
        """
        await self.manager.broadcast_to_simulation({
            "type": "simulation_cancelled",
            "simulation_job_id": simulation_job_id,
            "timestamp": datetime.utcnow().isoformat()
        }, simulation_job_id)


# Global simulation broadcaster instance
simulation_broadcaster = SimulationProgressBroadcaster()


def get_simulation_broadcaster() -> SimulationProgressBroadcaster:
    """Get the global simulation progress broadcaster instance."""
    return simulation_broadcaster