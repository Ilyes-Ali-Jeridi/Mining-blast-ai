"""
Optimization API endpoints with WebSocket progress tracking.
Implements requirement 8.2: Real-time solver iterations and objective improvements.
"""

import asyncio
from typing import Dict, Any, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.logging import get_logger
from ...optimization.progress_tracker import get_progress_tracker_manager, ProgressTracker
from ...optimization.engine import OptimizationEngine, OptimizationEngineConfig
from ...optimization.data_structures import OptimizationProblem, OptimizationResult
from ...repositories.blast_record import BlastRecordRepository
from ...repositories.site import SiteRepository
from ...schemas.blast_record import BlastRecordResponse
from ..websocket import get_progress_broadcaster

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{blast_id}/optimize-async")
async def start_optimization_async(
    blast_id: int,
    background_tasks: BackgroundTasks,
    optimization_params: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Start asynchronous optimization with WebSocket progress tracking.
    
    Args:
        blast_id: Blast plan ID
        background_tasks: Background task manager
        optimization_params: Optional optimization parameters
        db: Database session
        
    Returns:
        Optimization session information
        
    Raises:
        HTTPException: If blast plan not found or optimization cannot start
    """
    try:
        blast_repo = BlastRecordRepository(db)
        site_repo = SiteRepository(db)
        
        # Get blast plan
        blast = blast_repo.get_by_id(blast_id)
        if not blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Get site data
        site = site_repo.get_by_id(blast.site_id)
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {blast.site_id} not found"
            )
        
        # Check if blast can be optimized
        if blast.blast_status.value in ["executed", "archived"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot optimize executed or archived blast plans"
            )
        
        # Generate unique optimization session ID
        optimization_id = f"opt_{blast_id}_{uuid4().hex[:8]}"
        
        # Create progress tracker
        tracker_manager = get_progress_tracker_manager()
        progress_tracker = tracker_manager.create_tracker(optimization_id)
        
        # Set up WebSocket progress broadcasting
        progress_broadcaster = get_progress_broadcaster()
        
        async def websocket_callback(event):
            """Callback to broadcast progress events via WebSocket"""
            await progress_broadcaster.send_progress_update(
                optimization_id, 
                event.to_dict()
            )
        
        progress_tracker.add_event_callback(websocket_callback, is_async=True)
        
        # Start optimization in background
        background_tasks.add_task(
            run_optimization_background,
            optimization_id,
            blast_id,
            blast,
            site,
            optimization_params or {},
            progress_tracker
        )
        
        # Update blast status
        blast_repo.update(blast_id, {
            "optimization_metadata": {
                "optimization_id": optimization_id,
                "optimization_status": "running",
                "optimization_params": optimization_params or {}
            }
        })
        
        logger.info(
            "Async optimization started",
            blast_id=blast_id,
            optimization_id=optimization_id
        )
        
        return {
            "optimization_id": optimization_id,
            "blast_id": blast_id,
            "status": "started",
            "websocket_url": f"/api/v1/ws/optimization/{optimization_id}",
            "message": "Optimization started. Connect to WebSocket for real-time progress."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to start async optimization",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start optimization"
        )


@router.get("/status/{optimization_id}")
async def get_optimization_status(optimization_id: str) -> Dict[str, Any]:
    """
    Get current optimization status.
    
    Args:
        optimization_id: Optimization session ID
        
    Returns:
        Current optimization status and progress
        
    Raises:
        HTTPException: If optimization session not found
    """
    try:
        tracker_manager = get_progress_tracker_manager()
        tracker = tracker_manager.get_tracker(optimization_id)
        
        if not tracker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization session {optimization_id} not found"
            )
        
        progress = tracker.get_progress()
        
        return {
            "optimization_id": optimization_id,
            "status": progress.status.value,
            "progress": progress.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get optimization status",
            optimization_id=optimization_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve optimization status"
        )


@router.post("/cancel/{optimization_id}")
async def cancel_optimization(optimization_id: str) -> Dict[str, Any]:
    """
    Cancel a running optimization.
    
    Args:
        optimization_id: Optimization session ID
        
    Returns:
        Cancellation confirmation
        
    Raises:
        HTTPException: If optimization session not found
    """
    try:
        tracker_manager = get_progress_tracker_manager()
        cancelled = tracker_manager.cancel_optimization(optimization_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization session {optimization_id} not found"
            )
        
        # Broadcast cancellation via WebSocket
        progress_broadcaster = get_progress_broadcaster()
        await progress_broadcaster.send_optimization_cancelled(optimization_id)
        
        logger.info(f"Optimization {optimization_id} cancelled")
        
        return {
            "optimization_id": optimization_id,
            "status": "cancelled",
            "message": "Optimization cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cancel optimization",
            optimization_id=optimization_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel optimization"
        )


@router.get("/active")
async def list_active_optimizations() -> Dict[str, Any]:
    """
    List all active optimization sessions.
    
    Returns:
        List of active optimization sessions with their status
    """
    try:
        tracker_manager = get_progress_tracker_manager()
        all_progress = tracker_manager.get_all_progress()
        
        active_optimizations = []
        for opt_id, progress in all_progress.items():
            active_optimizations.append({
                "optimization_id": opt_id,
                "status": progress.status.value,
                "elapsed_time": progress.get_elapsed_time(),
                "overall_progress": progress.overall_progress,
                "current_algorithm": progress.current_algorithm,
                "message": progress.current_message
            })
        
        return {
            "active_optimizations": active_optimizations,
            "total_count": len(active_optimizations)
        }
        
    except Exception as e:
        logger.error("Failed to list active optimizations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active optimizations"
        )


async def run_optimization_background(
    optimization_id: str,
    blast_id: int,
    blast_record: Any,
    site_record: Any,
    optimization_params: Dict[str, Any],
    progress_tracker: ProgressTracker
):
    """
    Run optimization in background with progress tracking.
    
    Args:
        optimization_id: Optimization session ID
        blast_id: Blast plan ID
        blast_record: Blast record from database
        site_record: Site record from database
        optimization_params: Optimization parameters
        progress_tracker: Progress tracker instance
    """
    try:
        logger.info(f"Starting background optimization {optimization_id}")
        
        # Create optimization engine configuration
        config = OptimizationEngineConfig(
            enable_progress_tracking=True,
            progress_update_interval=1.0,
            **optimization_params
        )
        
        # Create optimization engine with progress callback
        def progress_callback(progress_data):
            """Callback for optimization engine progress updates"""
            if hasattr(progress_data, 'current_algorithm') and progress_data.current_algorithm:
                progress_tracker.update_algorithm_progress(
                    algorithm_name=progress_data.current_algorithm,
                    iterations=getattr(progress_data, 'iterations', None),
                    function_evaluations=getattr(progress_data, 'function_evaluations', None),
                    current_objective=getattr(progress_data, 'current_best_objective', None),
                    progress_percentage=getattr(progress_data, 'algorithm_progress', 0) * 100,
                    message=getattr(progress_data, 'current_message', '')
                )
        
        optimization_engine = OptimizationEngine(
            config=config,
            progress_callback=progress_callback
        )
        
        # TODO: Create actual optimization problem from blast and site data
        # For now, create a mock problem
        problem = create_optimization_problem_from_blast(blast_record, site_record)
        
        # Start progress tracking
        algorithm_names = ["cp_sat", "scipy_de", "scipy_slsqp"]
        progress_tracker.start_optimization(len(algorithm_names), algorithm_names)
        
        # Run optimization
        result = optimization_engine.optimize(
            problem=problem,
            track_progress=True
        )
        
        # Handle result
        if result.status.value == "completed":
            # Update blast record with optimization result
            await update_blast_with_result(blast_id, optimization_id, result)
            
            # Complete progress tracking
            progress_tracker.complete_optimization({
                "objective_value": result.objective_value,
                "algorithm_used": result.algorithm_used,
                "solve_time": result.solve_time_seconds,
                "converged": result.converged
            })
            
            logger.info(f"Optimization {optimization_id} completed successfully")
            
        else:
            # Handle failed optimization
            error_msg = f"Optimization failed with status: {result.status.value}"
            progress_tracker.fail_optimization(error_msg)
            
            logger.error(f"Optimization {optimization_id} failed: {error_msg}")
    
    except Exception as e:
        error_msg = f"Optimization error: {str(e)}"
        progress_tracker.fail_optimization(error_msg)
        
        logger.error(
            "Background optimization failed",
            optimization_id=optimization_id,
            error=str(e)
        )
    
    finally:
        # Clean up progress tracker after some delay
        await asyncio.sleep(300)  # Keep for 5 minutes after completion
        tracker_manager = get_progress_tracker_manager()
        tracker_manager.remove_tracker(optimization_id)


def create_optimization_problem_from_blast(blast_record: Any, site_record: Any) -> OptimizationProblem:
    """
    Create optimization problem from blast and site data.
    
    Args:
        blast_record: Blast record from database
        site_record: Site record from database
        
    Returns:
        Optimization problem instance
    """
    # TODO: Implement actual problem creation from blast and site data
    # For now, return a mock problem
    
    from ...optimization.data_structures import OptimizationProblem, Variable
    
    # Create mock variables (in real implementation, these would come from blast geometry)
    variables = [
        Variable(name=f"charge_{i}", lower_bound=0.0, upper_bound=100.0, variable_type="continuous")
        for i in range(10)  # Mock 10 holes
    ]
    
    problem = OptimizationProblem(
        problem_id=f"blast_{blast_record.id}",
        variables=variables,
        site_data={
            "site_id": site_record.id,
            "site_name": site_record.site_name,
            "bench_geometry": site_record.bench_geometry
        },
        blast_data={
            "blast_id": blast_record.id,
            "blast_name": blast_record.blast_name,
            "plan_data": blast_record.plan_data
        }
    )
    
    return problem


async def update_blast_with_result(blast_id: int, optimization_id: str, result: OptimizationResult):
    """
    Update blast record with optimization result.
    
    Args:
        blast_id: Blast plan ID
        optimization_id: Optimization session ID
        result: Optimization result
    """
    try:
        # TODO: Implement actual blast record update with optimization result
        # This would update the blast plan with optimized hole charges, delays, etc.
        
        logger.info(
            "Blast record updated with optimization result",
            blast_id=blast_id,
            optimization_id=optimization_id,
            objective_value=result.objective_value
        )
        
    except Exception as e:
        logger.error(
            "Failed to update blast record with optimization result",
            blast_id=blast_id,
            optimization_id=optimization_id,
            error=str(e)
        )