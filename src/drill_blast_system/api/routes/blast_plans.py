"""
Blast plan management API endpoints.
Implements requirement 8.1: Blast plan creation and optimization endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.logging import get_logger
from ...repositories.blast_record import BlastRecordRepository
from ...repositories.site import SiteRepository
from ...schemas.blast_record import (
    BlastRecordCreate, BlastRecordUpdate, BlastRecordResponse,
    BlastStatusEnum, BlastPlan, PredictedResults, SafetyValidation
)
from ...optimization.engine import OptimizationEngine
from ...safety.validator import SafetyValidator
from ...safety.config import SafetyConfig
from ...physics_models.kuz_ram import KuzRamModel
from ...physics_models.ppv import PPVModel

router = APIRouter()
logger = get_logger(__name__)


@router.post("/", response_model=BlastRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_blast_plan(
    blast_data: BlastRecordCreate,
    db: Session = Depends(get_db)
) -> BlastRecordResponse:
    """
    Create a new blast plan.
    
    Args:
        blast_data: Blast plan creation data
        db: Database session
        
    Returns:
        Created blast plan data
        
    Raises:
        HTTPException: If blast plan creation fails
    """
    try:
        blast_repo = BlastRecordRepository(db)
        site_repo = SiteRepository(db)
        
        # Verify site exists
        site = site_repo.get_by_id(blast_data.site_id)
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {blast_data.site_id} not found"
            )
        
        # Check if blast name already exists for this site
        existing_blast = blast_repo.get_latest_version(blast_data.blast_name, blast_data.site_id)
        if existing_blast and not blast_data.is_template:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Blast plan with name '{blast_data.blast_name}' already exists for this site"
            )
        
        # Create blast record
        blast_dict = blast_data.dict()
        blast_dict["blast_status"] = BlastStatusEnum.DRAFT
        blast_dict["plan_version"] = 1
        
        blast = blast_repo.create(blast_dict)
        
        logger.info(
            "Blast plan created successfully",
            blast_id=blast.id,
            blast_name=blast.blast_name,
            site_id=blast.site_id
        )
        
        return BlastRecordResponse.from_orm(blast)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create blast plan",
            blast_name=blast_data.blast_name,
            site_id=blast_data.site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create blast plan"
        )


@router.get("/", response_model=List[BlastRecordResponse])
async def list_blast_plans(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    status: Optional[BlastStatusEnum] = Query(None, description="Filter by blast status"),
    search: Optional[str] = Query(None, description="Search by blast name"),
    templates_only: bool = Query(False, description="Return only templates"),
    db: Session = Depends(get_db)
) -> List[BlastRecordResponse]:
    """
    List blast plans with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        site_id: Filter by site ID
        status: Filter by blast status
        search: Search by blast name
        templates_only: Return only templates
        db: Database session
        
    Returns:
        List of blast plans
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        if templates_only:
            blasts = blast_repo.get_templates(site_id=site_id)
        elif search:
            blasts = blast_repo.get_by_name_pattern(f"%{search}%")
            if site_id:
                blasts = [b for b in blasts if b.site_id == site_id]
        elif status:
            blasts = blast_repo.get_by_status(status, skip=skip, limit=limit)
            if site_id:
                blasts = [b for b in blasts if b.site_id == site_id]
        elif site_id:
            blasts = blast_repo.get_by_site_id(site_id, skip=skip, limit=limit)
        else:
            blasts = blast_repo.get_all(skip=skip, limit=limit)
        
        # Apply pagination if not already applied
        if search or templates_only:
            blasts = blasts[skip:skip + limit]
        
        logger.debug(
            "Blast plans retrieved",
            count=len(blasts),
            skip=skip,
            limit=limit,
            site_id=site_id,
            status=status,
            search=search,
            templates_only=templates_only
        )
        
        return [BlastRecordResponse.from_orm(blast) for blast in blasts]
        
    except Exception as e:
        logger.error("Failed to list blast plans", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blast plans"
        )


@router.get("/{blast_id}", response_model=BlastRecordResponse)
async def get_blast_plan(
    blast_id: int,
    db: Session = Depends(get_db)
) -> BlastRecordResponse:
    """
    Get a specific blast plan by ID.
    
    Args:
        blast_id: Blast plan ID
        db: Database session
        
    Returns:
        Blast plan data
        
    Raises:
        HTTPException: If blast plan not found
    """
    try:
        blast_repo = BlastRecordRepository(db)
        blast = blast_repo.get_by_id(blast_id)
        
        if not blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        logger.debug("Blast plan retrieved", blast_id=blast_id, blast_name=blast.blast_name)
        
        return BlastRecordResponse.from_orm(blast)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get blast plan",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blast plan"
        )


@router.put("/{blast_id}", response_model=BlastRecordResponse)
async def update_blast_plan(
    blast_id: int,
    blast_data: BlastRecordUpdate,
    db: Session = Depends(get_db)
) -> BlastRecordResponse:
    """
    Update a blast plan.
    
    Args:
        blast_id: Blast plan ID
        blast_data: Blast plan update data
        db: Database session
        
    Returns:
        Updated blast plan data
        
    Raises:
        HTTPException: If blast plan not found or update fails
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Check if blast exists
        existing_blast = blast_repo.get_by_id(blast_id)
        if not existing_blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Check if blast can be modified
        if existing_blast.blast_status in [BlastStatusEnum.EXECUTED, BlastStatusEnum.ARCHIVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify executed or archived blast plans"
            )
        
        # Update blast
        update_dict = blast_data.dict(exclude_unset=True)
        
        # If plan data is updated, invalidate sign-off and reset status
        if "plan_data" in update_dict:
            update_dict["engineer_signoff"] = None
            update_dict["blast_status"] = BlastStatusEnum.DRAFT
        
        updated_blast = blast_repo.update(blast_id, update_dict)
        
        if not updated_blast:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update blast plan"
            )
        
        logger.info(
            "Blast plan updated successfully",
            blast_id=blast_id,
            blast_name=updated_blast.blast_name
        )
        
        return BlastRecordResponse.from_orm(updated_blast)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update blast plan",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update blast plan"
        )


@router.delete("/{blast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blast_plan(
    blast_id: int,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a blast plan.
    
    Args:
        blast_id: Blast plan ID
        db: Database session
        
    Raises:
        HTTPException: If blast plan not found or deletion fails
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Check if blast exists
        existing_blast = blast_repo.get_by_id(blast_id)
        if not existing_blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Check if blast can be deleted
        if existing_blast.blast_status in [BlastStatusEnum.EXECUTED, BlastStatusEnum.MEASURED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete executed blast plans with measurements"
            )
        
        # Delete blast
        deleted = blast_repo.delete(blast_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete blast plan"
            )
        
        logger.info("Blast plan deleted", blast_id=blast_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete blast plan",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete blast plan"
        )


@router.post("/{blast_id}/optimize", response_model=BlastRecordResponse)
async def optimize_blast_plan(
    blast_id: int,
    background_tasks: BackgroundTasks,
    optimization_params: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
) -> BlastRecordResponse:
    """
    Optimize a blast plan using the optimization engine.
    
    Args:
        blast_id: Blast plan ID
        background_tasks: Background task manager
        optimization_params: Optional optimization parameters
        db: Database session
        
    Returns:
        Optimized blast plan data
        
    Raises:
        HTTPException: If blast plan not found or optimization fails
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
        if blast.blast_status in [BlastStatusEnum.EXECUTED, BlastStatusEnum.ARCHIVED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot optimize executed or archived blast plans"
            )
        
        # Initialize optimization engine
        kuz_ram = KuzRamModel()
        ppv_model = PPVModel()
        safety_config = SafetyConfig()
        safety_validator = SafetyValidator(safety_config)
        
        optimization_engine = OptimizationEngine(
            physics_models={
                "kuz_ram": kuz_ram,
                "ppv": ppv_model
            },
            safety_validator=safety_validator
        )
        
        # TODO: Implement actual optimization logic
        # For now, return the blast plan as-is with a note that optimization is pending
        
        # Update blast status to indicate optimization is in progress
        updated_blast = blast_repo.update(blast_id, {
            "blast_status": BlastStatusEnum.PENDING_REVIEW,
            "optimization_metadata": {
                "optimization_requested": True,
                "optimization_params": optimization_params or {},
                "optimization_status": "pending"
            }
        })
        
        logger.info(
            "Blast plan optimization requested",
            blast_id=blast_id,
            blast_name=blast.blast_name
        )
        
        return BlastRecordResponse.from_orm(updated_blast)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to optimize blast plan",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize blast plan"
        )


@router.post("/{blast_id}/copy", response_model=BlastRecordResponse)
async def copy_blast_plan(
    blast_id: int,
    new_name: str = Query(..., description="Name for the copied blast plan"),
    as_template: bool = Query(False, description="Create as template"),
    db: Session = Depends(get_db)
) -> BlastRecordResponse:
    """
    Copy a blast plan.
    
    Args:
        blast_id: Source blast plan ID
        new_name: Name for the copied blast plan
        as_template: Create as template
        db: Database session
        
    Returns:
        Copied blast plan data
        
    Raises:
        HTTPException: If blast plan not found or copy fails
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Get source blast plan
        source_blast = blast_repo.get_by_id(blast_id)
        if not source_blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Check if new name already exists
        existing_blast = blast_repo.get_latest_version(new_name, source_blast.site_id)
        if existing_blast:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Blast plan with name '{new_name}' already exists for this site"
            )
        
        # Create copy
        copy_data = {
            "site_id": source_blast.site_id,
            "blast_name": new_name,
            "blast_description": f"Copy of {source_blast.blast_name}",
            "blast_status": BlastStatusEnum.DRAFT,
            "plan_data": source_blast.plan_data,
            "predicted_results": source_blast.predicted_results,
            "safety_validation": source_blast.safety_validation,
            "is_template": as_template,
            "parent_blast_id": blast_id,
            "plan_version": 1
        }
        
        copied_blast = blast_repo.create(copy_data)
        
        logger.info(
            "Blast plan copied successfully",
            source_blast_id=blast_id,
            copied_blast_id=copied_blast.id,
            new_name=new_name,
            as_template=as_template
        )
        
        return BlastRecordResponse.from_orm(copied_blast)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to copy blast plan",
            blast_id=blast_id,
            new_name=new_name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy blast plan"
        )


@router.get("/{blast_id}/revisions", response_model=List[BlastRecordResponse])
async def get_blast_plan_revisions(
    blast_id: int,
    db: Session = Depends(get_db)
) -> List[BlastRecordResponse]:
    """
    Get all revisions of a blast plan.
    
    Args:
        blast_id: Blast plan ID
        db: Database session
        
    Returns:
        List of blast plan revisions
        
    Raises:
        HTTPException: If blast plan not found
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Check if blast exists
        blast = blast_repo.get_by_id(blast_id)
        if not blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Get revisions
        revisions = blast_repo.get_blast_revisions(blast_id)
        
        logger.debug(
            "Blast plan revisions retrieved",
            blast_id=blast_id,
            revision_count=len(revisions)
        )
        
        return [BlastRecordResponse.from_orm(revision) for revision in revisions]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get blast plan revisions",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blast plan revisions"
        )


@router.get("/statistics/summary", response_model=Dict[str, Any])
async def get_blast_plan_statistics(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get blast plan statistics summary.
    
    Args:
        site_id: Optional site ID filter
        db: Database session
        
    Returns:
        Blast plan statistics
    """
    try:
        blast_repo = BlastRecordRepository(db)
        statistics = blast_repo.get_blast_performance_summary(site_id=site_id)
        
        logger.debug("Blast plan statistics retrieved", statistics=statistics)
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get blast plan statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve blast plan statistics"
        )