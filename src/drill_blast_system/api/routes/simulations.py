"""
API routes for advanced simulation management
"""

import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.security import HTTPBearer
import logging

from ...auth.security import get_current_user
from ...auth.models import User
from ...simulation.simulation_manager import SimulationManager
from ...simulation.data_structures import (
    SimulationType, BlastFoamConfig, YadeConfig, MeshGeometry,
    SimulationJob, SimulationResult
)
from ...schemas.simulation import (
    SimulationJobCreateSchema, SimulationJobSchema, SimulationJobListSchema,
    SimulationResultSchema, SimulationComparisonSchema, SimulationCapabilitiesSchema,
    SimulationJobUpdateSchema, SimulationConfigTestSchema, SimulationConfigTestResultSchema,
    BlastFoamConfigSchema, YadeConfigSchema, MeshGeometrySchema
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Global simulation manager instance
simulation_manager = SimulationManager()

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


def convert_geometry_schema_to_dataclass(geometry_schema: MeshGeometrySchema) -> MeshGeometry:
    """Convert Pydantic schema to dataclass"""
    return MeshGeometry(
        bench_vertices=[tuple(v) for v in geometry_schema.bench_vertices],
        bench_faces=geometry_schema.bench_faces,
        hole_positions=[tuple(p) for p in geometry_schema.hole_positions],
        hole_depths=geometry_schema.hole_depths,
        hole_diameters=geometry_schema.hole_diameters,
        charge_positions=[tuple(p) for p in geometry_schema.charge_positions],
        charge_masses=geometry_schema.charge_masses,
        charge_types=geometry_schema.charge_types
    )


def convert_blastfoam_config_schema_to_dataclass(config_schema: BlastFoamConfigSchema) -> BlastFoamConfig:
    """Convert Pydantic schema to dataclass"""
    return BlastFoamConfig(
        enabled=config_schema.enabled,
        mesh_resolution=config_schema.mesh_resolution,
        simulation_time=config_schema.simulation_time,
        time_step=config_schema.time_step,
        parallel_processes=config_schema.parallel_processes,
        explosive_density=config_schema.explosive_density,
        detonation_velocity=config_schema.detonation_velocity,
        chapman_jouguet_pressure=config_schema.chapman_jouguet_pressure,
        timeout_seconds=config_schema.timeout_seconds
    )


def convert_yade_config_schema_to_dataclass(config_schema: YadeConfigSchema) -> YadeConfig:
    """Convert Pydantic schema to dataclass"""
    return YadeConfig(
        enabled=config_schema.enabled,
        particle_radius_min=config_schema.particle_radius_min,
        particle_radius_max=config_schema.particle_radius_max,
        particle_density=config_schema.particle_density,
        young_modulus=config_schema.young_modulus,
        poisson_ratio=config_schema.poisson_ratio,
        friction_angle=config_schema.friction_angle,
        cohesion=config_schema.cohesion,
        tensile_strength=config_schema.tensile_strength,
        max_iterations=config_schema.max_iterations,
        convergence_tolerance=config_schema.convergence_tolerance,
        timeout_seconds=config_schema.timeout_seconds
    )


def convert_simulation_result_to_schema(result: SimulationResult) -> SimulationResultSchema:
    """Convert simulation result dataclass to Pydantic schema"""
    return SimulationResultSchema(
        simulation_type=result.simulation_type,
        success=result.success,
        runtime_seconds=result.runtime_seconds,
        ppv_predictions=result.ppv_predictions,
        ppv_time_series=result.ppv_time_series,
        fragment_sizes=result.fragment_sizes.tolist() if result.fragment_sizes is not None else None,
        fragment_size_distribution=result.fragment_size_distribution,
        mesh_quality_metrics=result.mesh_quality_metrics,
        convergence_metrics=result.convergence_metrics,
        warnings=result.warnings,
        errors=result.errors
    )


@router.get("/capabilities", response_model=SimulationCapabilitiesSchema)
async def get_simulation_capabilities(
    current_user: User = Depends(get_current_user)
) -> SimulationCapabilitiesSchema:
    """Get available simulation capabilities and installation status"""
    try:
        # Configure simulation interfaces to check availability
        simulation_manager.configure_blastfoam(BlastFoamConfig())
        simulation_manager.configure_yade(YadeConfig())
        
        available_types = simulation_manager.get_available_simulations()
        installation_guides = simulation_manager.get_installation_guides()
        
        return SimulationCapabilitiesSchema(
            available_types=available_types,
            blastfoam_available=SimulationType.BLASTFOAM in available_types,
            yade_available=SimulationType.YADE in available_types,
            installation_guides=installation_guides
        )
    except Exception as e:
        logger.error(f"Error getting simulation capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get simulation capabilities: {str(e)}")


@router.post("/test-config", response_model=SimulationConfigTestResultSchema)
async def test_simulation_config(
    config: SimulationConfigTestSchema,
    current_user: User = Depends(get_current_user)
) -> SimulationConfigTestResultSchema:
    """Test simulation configuration and tool availability"""
    try:
        import time
        start_time = time.time()
        
        if config.simulation_type == SimulationType.BLASTFOAM:
            if config.blastfoam_config:
                blastfoam_config = convert_blastfoam_config_schema_to_dataclass(config.blastfoam_config)
                simulation_manager.configure_blastfoam(blastfoam_config)
            else:
                simulation_manager.configure_blastfoam(BlastFoamConfig())
            
            available = simulation_manager.blastfoam_interface and simulation_manager.blastfoam_interface.is_available
            
        elif config.simulation_type == SimulationType.YADE:
            if config.yade_config:
                yade_config = convert_yade_config_schema_to_dataclass(config.yade_config)
                simulation_manager.configure_yade(yade_config)
            else:
                simulation_manager.configure_yade(YadeConfig())
            
            available = simulation_manager.yade_interface and simulation_manager.yade_interface.is_available
            
        else:  # PHYSICS_ONLY
            available = True
        
        test_duration = time.time() - start_time
        
        return SimulationConfigTestResultSchema(
            simulation_type=config.simulation_type,
            available=available,
            test_passed=available,
            test_duration_seconds=test_duration,
            errors=[] if available else [f"{config.simulation_type.value} not available on system"],
            warnings=[] if available else [f"Install {config.simulation_type.value} to enable high-fidelity simulation"]
        )
        
    except Exception as e:
        logger.error(f"Error testing simulation config: {e}")
        return SimulationConfigTestResultSchema(
            simulation_type=config.simulation_type,
            available=False,
            test_passed=False,
            test_duration_seconds=0.0,
            errors=[f"Configuration test failed: {str(e)}"]
        )


@router.post("/jobs", response_model=SimulationJobSchema)
async def create_simulation_job(
    job_request: SimulationJobCreateSchema,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> SimulationJobSchema:
    """Create a new simulation job"""
    try:
        # Convert schemas to dataclasses
        geometry = convert_geometry_schema_to_dataclass(job_request.geometry)
        
        # Configure simulation manager based on job type
        config = None
        if job_request.simulation_type == SimulationType.BLASTFOAM and job_request.blastfoam_config:
            config = convert_blastfoam_config_schema_to_dataclass(job_request.blastfoam_config)
            simulation_manager.configure_blastfoam(config)
        elif job_request.simulation_type == SimulationType.YADE and job_request.yade_config:
            config = convert_yade_config_schema_to_dataclass(job_request.yade_config)
            simulation_manager.configure_yade(config)
        
        # Create simulation job
        job_id = simulation_manager.create_simulation_job(
            simulation_type=job_request.simulation_type,
            geometry=geometry,
            config=config
        )
        
        # Update job metadata
        job = simulation_manager.active_jobs[job_id]
        job.blast_plan_id = job_request.blast_plan_id
        job.priority = job_request.priority
        
        # Start simulation in background
        background_tasks.add_task(run_simulation_background, job_id)
        
        # Return job information
        job_status = simulation_manager.get_job_status(job_id)
        return SimulationJobSchema(
            job_id=job_id,
            simulation_type=job_request.simulation_type,
            status=job_status["status"],
            blast_plan_id=job_request.blast_plan_id,
            priority=job_request.priority,
            created_at=job_status["created_at"],
            started_at=job_status.get("started_at"),
            completed_at=job_status.get("completed_at")
        )
        
    except Exception as e:
        logger.error(f"Error creating simulation job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create simulation job: {str(e)}")


async def run_simulation_background(job_id: str):
    """Run simulation in background task"""
    try:
        await simulation_manager.run_simulation_async(job_id)
        logger.info(f"Simulation job {job_id} completed")
    except Exception as e:
        logger.error(f"Background simulation job {job_id} failed: {e}")


@router.get("/jobs", response_model=SimulationJobListSchema)
async def list_simulation_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    simulation_type: Optional[SimulationType] = Query(None, description="Filter by simulation type"),
    current_user: User = Depends(get_current_user)
) -> SimulationJobListSchema:
    """List simulation jobs with pagination and filtering"""
    try:
        all_jobs = []
        
        for job_id, job in simulation_manager.active_jobs.items():
            job_status = simulation_manager.get_job_status(job_id)
            
            # Apply filters
            if status and job_status["status"] != status:
                continue
            if simulation_type and job_status["simulation_type"] != simulation_type.value:
                continue
            
            job_schema = SimulationJobSchema(
                job_id=job_id,
                simulation_type=job_status["simulation_type"],
                status=job_status["status"],
                blast_plan_id=job.blast_plan_id,
                priority=job.priority,
                created_at=job_status["created_at"],
                started_at=job_status.get("started_at"),
                completed_at=job_status.get("completed_at"),
                runtime_seconds=job.result.runtime_seconds if job.result else None,
                result=convert_simulation_result_to_schema(job.result) if job.result else None
            )
            all_jobs.append(job_schema)
        
        # Sort by created_at descending
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        total_count = len(all_jobs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = all_jobs[start_idx:end_idx]
        
        return SimulationJobListSchema(
            jobs=paginated_jobs,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing simulation jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list simulation jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=SimulationJobSchema)
async def get_simulation_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> SimulationJobSchema:
    """Get simulation job details"""
    try:
        job_status = simulation_manager.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Simulation job not found")
        
        job = simulation_manager.active_jobs[job_id]
        
        return SimulationJobSchema(
            job_id=job_id,
            simulation_type=job_status["simulation_type"],
            status=job_status["status"],
            blast_plan_id=job.blast_plan_id,
            priority=job.priority,
            created_at=job_status["created_at"],
            started_at=job_status.get("started_at"),
            completed_at=job_status.get("completed_at"),
            runtime_seconds=job.result.runtime_seconds if job.result else None,
            result=convert_simulation_result_to_schema(job.result) if job.result else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting simulation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get simulation job: {str(e)}")


@router.patch("/jobs/{job_id}", response_model=SimulationJobSchema)
async def update_simulation_job(
    job_id: str,
    job_update: SimulationJobUpdateSchema,
    current_user: User = Depends(get_current_user)
) -> SimulationJobSchema:
    """Update simulation job (priority, cancel, etc.)"""
    try:
        job_status = simulation_manager.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Simulation job not found")
        
        job = simulation_manager.active_jobs[job_id]
        
        # Update priority
        if job_update.priority is not None:
            job.priority = job_update.priority
        
        # Handle status changes
        if job_update.status:
            if job_update.status == "cancelled":
                success = simulation_manager.cancel_job(job_id)
                if not success:
                    raise HTTPException(status_code=400, detail="Cannot cancel job in current state")
        
        # Return updated job
        return await get_simulation_job(job_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating simulation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update simulation job: {str(e)}")


@router.delete("/jobs/{job_id}")
async def delete_simulation_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete simulation job"""
    try:
        job_status = simulation_manager.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Simulation job not found")
        
        # Cancel if running
        if job_status["status"] == "running":
            simulation_manager.cancel_job(job_id)
        
        # Remove from active jobs
        if job_id in simulation_manager.active_jobs:
            del simulation_manager.active_jobs[job_id]
        
        return {"message": f"Simulation job {job_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting simulation job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete simulation job: {str(e)}")


@router.post("/compare", response_model=SimulationComparisonSchema)
async def compare_simulation_results(
    job_ids: List[str],
    current_user: User = Depends(get_current_user)
) -> SimulationComparisonSchema:
    """Compare results from multiple simulation jobs"""
    try:
        if len(job_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 jobs required for comparison")
        
        results = []
        for job_id in job_ids:
            job_status = simulation_manager.get_job_status(job_id)
            if not job_status:
                raise HTTPException(status_code=404, detail=f"Simulation job {job_id} not found")
            
            job = simulation_manager.active_jobs[job_id]
            if not job.result:
                raise HTTPException(status_code=400, detail=f"Job {job_id} has no results yet")
            
            results.append(job.result)
        
        # Compare results
        comparison = simulation_manager.compare_simulation_results(results)
        
        return SimulationComparisonSchema(**comparison)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing simulation results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare simulation results: {str(e)}")


@router.post("/cleanup")
async def cleanup_completed_jobs(
    max_age_hours: int = Query(24, ge=1, le=168, description="Maximum age in hours"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, int]:
    """Clean up old completed simulation jobs"""
    try:
        cleaned_count = simulation_manager.cleanup_completed_jobs(max_age_hours)
        return {"cleaned_jobs": cleaned_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up simulation jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup simulation jobs: {str(e)}")


@router.get("/installation-guides")
async def get_installation_guides(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Get installation guides for simulation tools"""
    try:
        # Configure interfaces to get guides
        simulation_manager.configure_blastfoam(BlastFoamConfig())
        simulation_manager.configure_yade(YadeConfig())
        
        guides = simulation_manager.get_installation_guides()
        return guides
        
    except Exception as e:
        logger.error(f"Error getting installation guides: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get installation guides: {str(e)}")