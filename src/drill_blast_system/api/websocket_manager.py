"""
WebSocket connection management with timeout and cancellation handling.
Implements requirement 8.2: Real-time optimization progress with cancellation support.
"""

import asyncio
import time
from typing import Dict, Set, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from ..core.logging import get_logger


class ConnectionState(Enum):
    """WebSocket connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection"""
    connection_id: str
    websocket: Any  # WebSocket instance
    optimization_id: Optional[str]
    simulation_job_id: Optional[str] = None
    state: ConnectionState
    connected_at: datetime
    last_ping: datetime
    last_pong: datetime
    ping_count: int = 0
    pong_count: int = 0
    message_count: int = 0
    
    def is_alive(self, timeout_seconds: float = 60.0) -> bool:
        """Check if connection is considered alive based on ping/pong"""
        if self.state != ConnectionState.CONNECTED:
            return False
        
        # Check if we've received a pong recently
        time_since_pong = (datetime.utcnow() - self.last_pong).total_seconds()
        return time_since_pong < timeout_seconds
    
    def get_connection_age(self) -> float:
        """Get connection age in seconds"""
        return (datetime.utcnow() - self.connected_at).total_seconds()


class WebSocketConnectionManager:
    """
    Advanced WebSocket connection manager with timeout handling and health monitoring.
    """
    
    def __init__(self, 
                 ping_interval: float = 30.0,
                 pong_timeout: float = 60.0,
                 max_connections_per_optimization: int = 10,
                 cleanup_interval: float = 300.0):
        """
        Initialize connection manager.
        
        Args:
            ping_interval: Interval between ping messages (seconds)
            pong_timeout: Timeout for pong responses (seconds)
            max_connections_per_optimization: Maximum connections per optimization
            cleanup_interval: Interval for connection cleanup (seconds)
        """
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.max_connections_per_optimization = max_connections_per_optimization
        self.cleanup_interval = cleanup_interval
        
        # Connection storage
        self.connections: Dict[str, ConnectionInfo] = {}
        self.optimization_connections: Dict[str, Set[str]] = {}
        self.simulation_connections: Dict[str, Set[str]] = {}  # simulation_job_id -> connection_ids
        
        # Health monitoring
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Event callbacks
        self.connection_callbacks: Dict[str, Callable] = {}
        self.disconnection_callbacks: Dict[str, Callable] = {}
        
        self.logger = get_logger(__name__ + ".WebSocketConnectionManager")
    
    async def start(self):
        """Start the connection manager and background tasks"""
        if self.running:
            return
        
        self.running = True
        
        # Start background tasks
        self.health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("WebSocket connection manager started")
    
    async def stop(self):
        """Stop the connection manager and cleanup"""
        self.running = False
        
        # Cancel background tasks
        if self.health_monitor_task:
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id, reason="Manager shutdown")
        
        self.logger.info("WebSocket connection manager stopped")
    
    async def connect(self, 
                     websocket: Any, 
                     connection_id: str,
                     optimization_id: Optional[str] = None) -> bool:
        """
        Register a new WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            connection_id: Unique connection identifier
            optimization_id: Optional optimization session ID
            
        Returns:
            True if connection was accepted, False otherwise
        """
        try:
            # Check connection limits
            if optimization_id:
                current_connections = len(self.optimization_connections.get(optimization_id, set()))
                if current_connections >= self.max_connections_per_optimization:
                    self.logger.warning(
                        "Connection limit exceeded for optimization",
                        optimization_id=optimization_id,
                        current_connections=current_connections,
                        limit=self.max_connections_per_optimization
                    )
                    return False
            
            # Accept WebSocket connection
            await websocket.accept()
            
            # Create connection info
            now = datetime.utcnow()
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                websocket=websocket,
                optimization_id=optimization_id,
                state=ConnectionState.CONNECTED,
                connected_at=now,
                last_ping=now,
                last_pong=now
            )
            
            # Store connection
            self.connections[connection_id] = connection_info
            
            # Add to optimization session
            if optimization_id:
                if optimization_id not in self.optimization_connections:
                    self.optimization_connections[optimization_id] = set()
                self.optimization_connections[optimization_id].add(connection_id)
            
            # Trigger connection callback
            if "connect" in self.connection_callbacks:
                try:
                    await self.connection_callbacks["connect"](connection_id, optimization_id)
                except Exception as e:
                    self.logger.error(f"Connection callback error: {e}")
            
            self.logger.info(
                "WebSocket connection established",
                connection_id=connection_id,
                optimization_id=optimization_id,
                total_connections=len(self.connections)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to establish WebSocket connection",
                connection_id=connection_id,
                error=str(e)
            )
            return False
    
    async def disconnect(self, connection_id: str, reason: str = "Normal closure"):
        """
        Disconnect a WebSocket connection.
        
        Args:
            connection_id: Connection identifier
            reason: Reason for disconnection
        """
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        
        try:
            # Update connection state
            connection_info.state = ConnectionState.DISCONNECTING
            
            # Close WebSocket if still open
            try:
                await connection_info.websocket.close()
            except Exception as e:
                self.logger.debug(f"Error closing WebSocket: {e}")
            
            # Remove from optimization session
            if connection_info.optimization_id:
                opt_id = connection_info.optimization_id
                if opt_id in self.optimization_connections:
                    self.optimization_connections[opt_id].discard(connection_id)
                    # Clean up empty sessions
                    if not self.optimization_connections[opt_id]:
                        del self.optimization_connections[opt_id]
            
            # Remove from simulation session
            if connection_info.simulation_job_id:
                sim_id = connection_info.simulation_job_id
                if sim_id in self.simulation_connections:
                    self.simulation_connections[sim_id].discard(connection_id)
                    # Clean up empty sessions
                    if not self.simulation_connections[sim_id]:
                        del self.simulation_connections[sim_id]
            
            # Trigger disconnection callback
            if "disconnect" in self.disconnection_callbacks:
                try:
                    await self.disconnection_callbacks["disconnect"](
                        connection_id, 
                        connection_info.optimization_id,
                        reason
                    )
                except Exception as e:
                    self.logger.error(f"Disconnection callback error: {e}")
            
            # Remove connection
            del self.connections[connection_id]
            
            self.logger.info(
                "WebSocket connection closed",
                connection_id=connection_id,
                optimization_id=connection_info.optimization_id,
                reason=reason,
                connection_age=connection_info.get_connection_age(),
                total_connections=len(self.connections)
            )
            
        except Exception as e:
            self.logger.error(
                "Error during WebSocket disconnection",
                connection_id=connection_id,
                error=str(e)
            )
        finally:
            # Ensure connection is removed even if there was an error
            if connection_id in self.connections:
                del self.connections[connection_id]
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection ID
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        if connection_info.state != ConnectionState.CONNECTED:
            return False
        
        try:
            import json
            await connection_info.websocket.send_text(json.dumps(message))
            connection_info.message_count += 1
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to send WebSocket message",
                connection_id=connection_id,
                error=str(e)
            )
            
            # Mark connection as error and schedule for cleanup
            connection_info.state = ConnectionState.ERROR
            asyncio.create_task(self.disconnect(connection_id, f"Send error: {e}"))
            return False
    
    async def broadcast_to_optimization(self, optimization_id: str, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connections in an optimization session.
        
        Args:
            optimization_id: Optimization session ID
            message: Message to broadcast
            
        Returns:
            Number of connections that received the message
        """
        if optimization_id not in self.optimization_connections:
            return 0
        
        connection_ids = list(self.optimization_connections[optimization_id])
        successful_sends = 0
        
        for connection_id in connection_ids:
            if await self.send_message(connection_id, message):
                successful_sends += 1
        
        return successful_sends
    
    async def ping_connection(self, connection_id: str) -> bool:
        """
        Send a ping to a specific connection.
        
        Args:
            connection_id: Connection to ping
            
        Returns:
            True if ping was sent successfully
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat(),
            "ping_id": connection_info.ping_count
        }
        
        success = await self.send_message(connection_id, ping_message)
        if success:
            connection_info.ping_count += 1
            connection_info.last_ping = datetime.utcnow()
        
        return success
    
    async def handle_pong(self, connection_id: str, pong_data: Dict[str, Any]):
        """
        Handle a pong response from a connection.
        
        Args:
            connection_id: Connection that sent the pong
            pong_data: Pong message data
        """
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        connection_info.last_pong = datetime.utcnow()
        connection_info.pong_count += 1
        
        self.logger.debug(
            "Received pong from connection",
            connection_id=connection_id,
            ping_count=connection_info.ping_count,
            pong_count=connection_info.pong_count
        )
    
    async def _health_monitor_loop(self):
        """Background task to monitor connection health"""
        while self.running:
            try:
                await asyncio.sleep(self.ping_interval)
                
                if not self.running:
                    break
                
                # Send pings to all connections
                for connection_id in list(self.connections.keys()):
                    await self.ping_connection(connection_id)
                
                # Check for timed out connections
                timed_out_connections = []
                for connection_id, connection_info in self.connections.items():
                    if not connection_info.is_alive(self.pong_timeout):
                        timed_out_connections.append(connection_id)
                
                # Disconnect timed out connections
                for connection_id in timed_out_connections:
                    await self.disconnect(connection_id, "Ping timeout")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup"""
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.running:
                    break
                
                # Clean up error state connections
                error_connections = [
                    conn_id for conn_id, conn_info in self.connections.items()
                    if conn_info.state == ConnectionState.ERROR
                ]
                
                for connection_id in error_connections:
                    await self.disconnect(connection_id, "Cleanup - error state")
                
                # Log statistics
                self.logger.debug(
                    "Connection cleanup completed",
                    total_connections=len(self.connections),
                    active_optimizations=len(self.optimization_connections),
                    cleaned_up=len(error_connections)
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
    
    def add_connection_callback(self, event: str, callback: Callable):
        """Add a callback for connection events"""
        if event in ["connect"]:
            self.connection_callbacks[event] = callback
    
    def add_disconnection_callback(self, event: str, callback: Callable):
        """Add a callback for disconnection events"""
        if event in ["disconnect"]:
            self.disconnection_callbacks[event] = callback
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get information about a specific connection"""
        return self.connections.get(connection_id)
    
    def get_optimization_connections(self, optimization_id: str) -> Set[str]:
        """Get all connection IDs for an optimization session"""
        return self.optimization_connections.get(optimization_id, set()).copy()
    
    async def subscribe_to_simulation(self, connection_id: str, simulation_job_id: str) -> bool:
        """
        Subscribe a connection to simulation updates.
        
        Args:
            connection_id: Connection identifier
            simulation_job_id: Simulation job identifier
            
        Returns:
            bool: True if subscription successful
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        connection_info.simulation_job_id = simulation_job_id
        
        # Add to simulation connections
        if simulation_job_id not in self.simulation_connections:
            self.simulation_connections[simulation_job_id] = set()
        
        self.simulation_connections[simulation_job_id].add(connection_id)
        
        self.logger.info(
            "Connection subscribed to simulation",
            connection_id=connection_id,
            simulation_job_id=simulation_job_id
        )
        
        return True
    
    async def unsubscribe_from_simulation(self, connection_id: str) -> bool:
        """
        Unsubscribe a connection from simulation updates.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            bool: True if unsubscription successful
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        simulation_job_id = connection_info.simulation_job_id
        
        if simulation_job_id:
            # Remove from simulation connections
            if simulation_job_id in self.simulation_connections:
                self.simulation_connections[simulation_job_id].discard(connection_id)
                # Clean up empty sessions
                if not self.simulation_connections[simulation_job_id]:
                    del self.simulation_connections[simulation_job_id]
            
            connection_info.simulation_job_id = None
            
            self.logger.info(
                "Connection unsubscribed from simulation",
                connection_id=connection_id,
                simulation_job_id=simulation_job_id
            )
        
        return True
    
    async def broadcast_simulation_update(self, simulation_job_id: str, message: Dict[str, Any]):
        """
        Broadcast simulation update to all subscribed connections.
        
        Args:
            simulation_job_id: Simulation job identifier
            message: Message to broadcast
        """
        if simulation_job_id not in self.simulation_connections:
            return
        
        connection_ids = self.simulation_connections[simulation_job_id].copy()
        
        for connection_id in connection_ids:
            try:
                await self.send_message(connection_id, message)
            except Exception as e:
                self.logger.error(
                    "Failed to send simulation update",
                    connection_id=connection_id,
                    simulation_job_id=simulation_job_id,
                    error=str(e)
                )
                # Remove failed connection
                await self.disconnect(connection_id, "Send error")
    
    def get_simulation_connections(self, simulation_job_id: str) -> Set[str]:
        """Get all connection IDs for a simulation session"""
        return self.simulation_connections.get(simulation_job_id, set()).copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics"""
        total_connections = len(self.connections)
        active_optimizations = len(self.optimization_connections)
        
        # Calculate connection states
        state_counts = {}
        for connection_info in self.connections.values():
            state = connection_info.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Calculate average connection age
        if self.connections:
            avg_age = sum(
                conn.get_connection_age() 
                for conn in self.connections.values()
            ) / len(self.connections)
        else:
            avg_age = 0.0
        
        return {
            "total_connections": total_connections,
            "active_optimizations": active_optimizations,
            "active_simulations": len(self.simulation_connections),
            "connection_states": state_counts,
            "average_connection_age": avg_age,
            "optimization_sessions": {
                opt_id: len(connections)
                for opt_id, connections in self.optimization_connections.items()
            },
            "simulation_sessions": {
                sim_id: len(connections)
                for sim_id, connections in self.simulation_connections.items()
            }
        }


# Global connection manager instance
websocket_manager = WebSocketConnectionManager()


async def get_websocket_manager() -> WebSocketConnectionManager:
    """Get the global WebSocket connection manager"""
    if not websocket_manager.running:
        await websocket_manager.start()
    return websocket_manager