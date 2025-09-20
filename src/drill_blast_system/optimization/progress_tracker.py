"""
Optimization progress tracking system.
Implements requirement 8.2: Real-time solver iterations and objective improvements.
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .data_structures import OptimizationStatus


class ProgressEventType(Enum):
    """Types of progress events"""
    OPTIMIZATION_STARTED = "optimization_started"
    ALGORITHM_STARTED = "algorithm_started"
    ITERATION_UPDATE = "iteration_update"
    ALGORITHM_COMPLETED = "algorithm_completed"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    OPTIMIZATION_FAILED = "optimization_failed"
    OPTIMIZATION_CANCELLED = "optimization_cancelled"


@dataclass
class ProgressEvent:
    """Progress event data structure"""
    event_type: ProgressEventType
    optimization_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_type": self.event_type.value,
            "optimization_id": self.optimization_id,
            "timestamp": self.timestamp.isoformat(),
            **self.data
        }


@dataclass
class AlgorithmProgress:
    """Progress information for a single algorithm"""
    algorithm_name: str
    status: OptimizationStatus = OptimizationStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    iterations: int = 0
    function_evaluations: int = 0
    current_objective: float = float('inf')
    best_objective: float = float('inf')
    progress_percentage: float = 0.0
    current_message: str = ""
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "algorithm_name": self.algorithm_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_time": self.get_elapsed_time(),
            "iterations": self.iterations,
            "function_evaluations": self.function_evaluations,
            "current_objective": self.current_objective,
            "best_objective": self.best_objective,
            "progress_percentage": self.progress_percentage,
            "current_message": self.current_message
        }


@dataclass
class OptimizationProgress:
    """Overall optimization progress information"""
    optimization_id: str
    status: OptimizationStatus = OptimizationStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_algorithms: int = 0
    completed_algorithms: int = 0
    current_algorithm: Optional[str] = None
    algorithms: Dict[str, AlgorithmProgress] = field(default_factory=dict)
    overall_progress: float = 0.0
    best_objective_overall: float = float('inf')
    current_message: str = ""
    
    def get_elapsed_time(self) -> float:
        """Get total elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds()
    
    def get_estimated_remaining_time(self) -> float:
        """Estimate remaining time based on current progress"""
        if self.overall_progress <= 0.0:
            return 0.0
        
        elapsed = self.get_elapsed_time()
        if elapsed <= 0.0:
            return 0.0
        
        total_estimated = elapsed / self.overall_progress
        return max(0.0, total_estimated - elapsed)
    
    def update_overall_progress(self):
        """Update overall progress based on algorithm progress"""
        if self.total_algorithms == 0:
            self.overall_progress = 0.0
            return
        
        # Calculate progress based on completed algorithms and current algorithm progress
        completed_weight = self.completed_algorithms / self.total_algorithms
        
        current_weight = 0.0
        if self.current_algorithm and self.current_algorithm in self.algorithms:
            current_algo_progress = self.algorithms[self.current_algorithm].progress_percentage
            current_weight = (current_algo_progress / 100.0) / self.total_algorithms
        
        self.overall_progress = min(1.0, completed_weight + current_weight)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "optimization_id": self.optimization_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_time": self.get_elapsed_time(),
            "estimated_remaining_time": self.get_estimated_remaining_time(),
            "total_algorithms": self.total_algorithms,
            "completed_algorithms": self.completed_algorithms,
            "current_algorithm": self.current_algorithm,
            "overall_progress": self.overall_progress,
            "best_objective_overall": self.best_objective_overall,
            "current_message": self.current_message,
            "algorithms": {name: algo.to_dict() for name, algo in self.algorithms.items()}
        }


class ProgressTracker:
    """
    Tracks optimization progress and manages event broadcasting.
    Thread-safe implementation for use with concurrent optimization algorithms.
    """
    
    def __init__(self, optimization_id: str, update_interval: float = 1.0):
        """
        Initialize progress tracker.
        
        Args:
            optimization_id: Unique optimization session ID
            update_interval: Minimum interval between progress updates (seconds)
        """
        self.optimization_id = optimization_id
        self.update_interval = update_interval
        
        # Progress state
        self.progress = OptimizationProgress(optimization_id=optimization_id)
        self.progress_lock = threading.RLock()
        
        # Event handling
        self.event_callbacks: List[Callable[[ProgressEvent], None]] = []
        self.async_event_callbacks: List[Callable[[ProgressEvent], None]] = []
        
        # Update throttling
        self.last_update_time = 0.0
        
        # Cancellation support
        self.cancellation_requested = threading.Event()
        
        self.logger = logging.getLogger(__name__ + ".ProgressTracker")
    
    def add_event_callback(self, callback: Callable[[ProgressEvent], None], is_async: bool = False):
        """
        Add a callback for progress events.
        
        Args:
            callback: Callback function to receive progress events
            is_async: Whether the callback is async (coroutine)
        """
        if is_async:
            self.async_event_callbacks.append(callback)
        else:
            self.event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable[[ProgressEvent], None]):
        """Remove a progress event callback."""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
        if callback in self.async_event_callbacks:
            self.async_event_callbacks.remove(callback)
    
    def _emit_event(self, event: ProgressEvent):
        """Emit a progress event to all callbacks."""
        # Synchronous callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
        
        # Asynchronous callbacks (run in event loop if available)
        if self.async_event_callbacks:
            try:
                loop = asyncio.get_event_loop()
                for callback in self.async_event_callbacks:
                    asyncio.create_task(callback(event))
            except RuntimeError:
                # No event loop running, skip async callbacks
                pass
    
    def start_optimization(self, total_algorithms: int, algorithm_names: List[str]):
        """
        Start optimization tracking.
        
        Args:
            total_algorithms: Total number of algorithms to run
            algorithm_names: List of algorithm names
        """
        with self.progress_lock:
            self.progress.status = OptimizationStatus.RUNNING
            self.progress.start_time = datetime.utcnow()
            self.progress.total_algorithms = total_algorithms
            self.progress.current_message = "Starting optimization..."
            
            # Initialize algorithm progress
            for algo_name in algorithm_names:
                self.progress.algorithms[algo_name] = AlgorithmProgress(algorithm_name=algo_name)
        
        event = ProgressEvent(
            event_type=ProgressEventType.OPTIMIZATION_STARTED,
            optimization_id=self.optimization_id,
            data={
                "total_algorithms": total_algorithms,
                "algorithm_names": algorithm_names
            }
        )
        self._emit_event(event)
        
        self.logger.info(
            "Optimization tracking started",
            optimization_id=self.optimization_id,
            total_algorithms=total_algorithms
        )
    
    def start_algorithm(self, algorithm_name: str):
        """
        Start tracking a specific algorithm.
        
        Args:
            algorithm_name: Name of the algorithm starting
        """
        with self.progress_lock:
            self.progress.current_algorithm = algorithm_name
            self.progress.current_message = f"Running {algorithm_name}..."
            
            if algorithm_name in self.progress.algorithms:
                algo_progress = self.progress.algorithms[algorithm_name]
                algo_progress.status = OptimizationStatus.RUNNING
                algo_progress.start_time = datetime.utcnow()
                algo_progress.current_message = "Starting..."
        
        event = ProgressEvent(
            event_type=ProgressEventType.ALGORITHM_STARTED,
            optimization_id=self.optimization_id,
            data={"algorithm_name": algorithm_name}
        )
        self._emit_event(event)
        
        self.logger.debug(f"Algorithm {algorithm_name} started")
    
    def update_algorithm_progress(self, 
                                algorithm_name: str,
                                iterations: Optional[int] = None,
                                function_evaluations: Optional[int] = None,
                                current_objective: Optional[float] = None,
                                progress_percentage: Optional[float] = None,
                                message: Optional[str] = None):
        """
        Update progress for a specific algorithm.
        
        Args:
            algorithm_name: Name of the algorithm
            iterations: Current iteration count
            function_evaluations: Current function evaluation count
            current_objective: Current objective value
            progress_percentage: Progress percentage (0-100)
            message: Status message
        """
        current_time = time.time()
        
        # Throttle updates to avoid overwhelming WebSocket clients
        if current_time - self.last_update_time < self.update_interval:
            return
        
        with self.progress_lock:
            if algorithm_name not in self.progress.algorithms:
                return
            
            algo_progress = self.progress.algorithms[algorithm_name]
            
            # Update algorithm progress
            if iterations is not None:
                algo_progress.iterations = iterations
            if function_evaluations is not None:
                algo_progress.function_evaluations = function_evaluations
            if current_objective is not None:
                algo_progress.current_objective = current_objective
                # Update best objective if improved
                if current_objective < algo_progress.best_objective:
                    algo_progress.best_objective = current_objective
                    # Update overall best
                    if current_objective < self.progress.best_objective_overall:
                        self.progress.best_objective_overall = current_objective
            if progress_percentage is not None:
                algo_progress.progress_percentage = progress_percentage
            if message is not None:
                algo_progress.current_message = message
            
            # Update overall progress
            self.progress.update_overall_progress()
        
        self.last_update_time = current_time
        
        # Emit iteration update event
        event_data = {
            "algorithm_name": algorithm_name,
            "iterations": iterations,
            "function_evaluations": function_evaluations,
            "current_objective": current_objective,
            "progress_percentage": progress_percentage,
            "message": message
        }
        # Remove None values
        event_data = {k: v for k, v in event_data.items() if v is not None}
        
        event = ProgressEvent(
            event_type=ProgressEventType.ITERATION_UPDATE,
            optimization_id=self.optimization_id,
            data=event_data
        )
        self._emit_event(event)
    
    def complete_algorithm(self, algorithm_name: str, result: Dict[str, Any]):
        """
        Mark an algorithm as completed.
        
        Args:
            algorithm_name: Name of the completed algorithm
            result: Algorithm result summary
        """
        with self.progress_lock:
            if algorithm_name in self.progress.algorithms:
                algo_progress = self.progress.algorithms[algorithm_name]
                algo_progress.status = OptimizationStatus.COMPLETED
                algo_progress.end_time = datetime.utcnow()
                algo_progress.progress_percentage = 100.0
                algo_progress.current_message = "Completed"
            
            self.progress.completed_algorithms += 1
            self.progress.update_overall_progress()
            
            # Update current algorithm if this was the current one
            if self.progress.current_algorithm == algorithm_name:
                self.progress.current_algorithm = None
        
        event = ProgressEvent(
            event_type=ProgressEventType.ALGORITHM_COMPLETED,
            optimization_id=self.optimization_id,
            data={
                "algorithm_name": algorithm_name,
                "result": result
            }
        )
        self._emit_event(event)
        
        self.logger.debug(f"Algorithm {algorithm_name} completed")
    
    def complete_optimization(self, final_result: Dict[str, Any]):
        """
        Mark optimization as completed.
        
        Args:
            final_result: Final optimization result
        """
        with self.progress_lock:
            self.progress.status = OptimizationStatus.COMPLETED
            self.progress.end_time = datetime.utcnow()
            self.progress.overall_progress = 1.0
            self.progress.current_message = "Optimization completed"
            self.progress.current_algorithm = None
        
        event = ProgressEvent(
            event_type=ProgressEventType.OPTIMIZATION_COMPLETED,
            optimization_id=self.optimization_id,
            data={"result": final_result}
        )
        self._emit_event(event)
        
        self.logger.info(
            "Optimization completed",
            optimization_id=self.optimization_id,
            elapsed_time=self.progress.get_elapsed_time()
        )
    
    def fail_optimization(self, error_message: str):
        """
        Mark optimization as failed.
        
        Args:
            error_message: Error description
        """
        with self.progress_lock:
            self.progress.status = OptimizationStatus.FAILED
            self.progress.end_time = datetime.utcnow()
            self.progress.current_message = f"Failed: {error_message}"
            self.progress.current_algorithm = None
        
        event = ProgressEvent(
            event_type=ProgressEventType.OPTIMIZATION_FAILED,
            optimization_id=self.optimization_id,
            data={"error": error_message}
        )
        self._emit_event(event)
        
        self.logger.error(
            "Optimization failed",
            optimization_id=self.optimization_id,
            error=error_message
        )
    
    def cancel_optimization(self):
        """Cancel the optimization."""
        self.cancellation_requested.set()
        
        with self.progress_lock:
            self.progress.status = OptimizationStatus.CANCELLED
            self.progress.end_time = datetime.utcnow()
            self.progress.current_message = "Cancelled by user"
            self.progress.current_algorithm = None
        
        event = ProgressEvent(
            event_type=ProgressEventType.OPTIMIZATION_CANCELLED,
            optimization_id=self.optimization_id,
            data={}
        )
        self._emit_event(event)
        
        self.logger.info(
            "Optimization cancelled",
            optimization_id=self.optimization_id
        )
    
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self.cancellation_requested.is_set()
    
    def get_progress(self) -> OptimizationProgress:
        """Get current progress state (thread-safe copy)."""
        with self.progress_lock:
            # Create a deep copy of the progress state
            progress_copy = OptimizationProgress(
                optimization_id=self.progress.optimization_id,
                status=self.progress.status,
                start_time=self.progress.start_time,
                end_time=self.progress.end_time,
                total_algorithms=self.progress.total_algorithms,
                completed_algorithms=self.progress.completed_algorithms,
                current_algorithm=self.progress.current_algorithm,
                overall_progress=self.progress.overall_progress,
                best_objective_overall=self.progress.best_objective_overall,
                current_message=self.progress.current_message
            )
            
            # Copy algorithm progress
            for name, algo_progress in self.progress.algorithms.items():
                progress_copy.algorithms[name] = AlgorithmProgress(
                    algorithm_name=algo_progress.algorithm_name,
                    status=algo_progress.status,
                    start_time=algo_progress.start_time,
                    end_time=algo_progress.end_time,
                    iterations=algo_progress.iterations,
                    function_evaluations=algo_progress.function_evaluations,
                    current_objective=algo_progress.current_objective,
                    best_objective=algo_progress.best_objective,
                    progress_percentage=algo_progress.progress_percentage,
                    current_message=algo_progress.current_message
                )
            
            return progress_copy


class ProgressTrackerManager:
    """
    Manages multiple progress trackers for concurrent optimizations.
    """
    
    def __init__(self):
        self.trackers: Dict[str, ProgressTracker] = {}
        self.trackers_lock = threading.RLock()
        self.logger = logging.getLogger(__name__ + ".ProgressTrackerManager")
    
    def create_tracker(self, optimization_id: str, update_interval: float = 1.0) -> ProgressTracker:
        """
        Create a new progress tracker.
        
        Args:
            optimization_id: Unique optimization session ID
            update_interval: Minimum interval between progress updates
            
        Returns:
            Progress tracker instance
        """
        with self.trackers_lock:
            if optimization_id in self.trackers:
                self.logger.warning(f"Progress tracker already exists for {optimization_id}")
                return self.trackers[optimization_id]
            
            tracker = ProgressTracker(optimization_id, update_interval)
            self.trackers[optimization_id] = tracker
            
            self.logger.info(f"Created progress tracker for {optimization_id}")
            return tracker
    
    def get_tracker(self, optimization_id: str) -> Optional[ProgressTracker]:
        """Get an existing progress tracker."""
        with self.trackers_lock:
            return self.trackers.get(optimization_id)
    
    def remove_tracker(self, optimization_id: str):
        """Remove a progress tracker."""
        with self.trackers_lock:
            if optimization_id in self.trackers:
                del self.trackers[optimization_id]
                self.logger.info(f"Removed progress tracker for {optimization_id}")
    
    def get_all_progress(self) -> Dict[str, OptimizationProgress]:
        """Get progress for all active optimizations."""
        with self.trackers_lock:
            return {
                opt_id: tracker.get_progress()
                for opt_id, tracker in self.trackers.items()
            }
    
    def cancel_optimization(self, optimization_id: str) -> bool:
        """
        Cancel an optimization.
        
        Args:
            optimization_id: Optimization session ID
            
        Returns:
            True if optimization was found and cancelled
        """
        with self.trackers_lock:
            if optimization_id in self.trackers:
                self.trackers[optimization_id].cancel_optimization()
                return True
            return False


# Global progress tracker manager
progress_tracker_manager = ProgressTrackerManager()


def get_progress_tracker_manager() -> ProgressTrackerManager:
    """Get the global progress tracker manager."""
    return progress_tracker_manager