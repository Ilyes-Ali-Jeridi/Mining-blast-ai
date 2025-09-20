"""
Site management API endpoints.
Implements requirement 1.8: Site management endpoints (CRUD operations).
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.logging import get_logger
from ...repositories.site import SiteRepository
from ...schemas.site import (
    SiteCreate, SiteUpdate, SiteResponse,
    BenchGeometry, RockProperties, EquipmentSpecs, OperationalConstraints
)

router = APIRouter()
logger = get_logger(__name__)


def get_db_optional():
    """Get database session only if database is enabled."""
    if os.getenv('SKIP_DB_INIT'):
        return None
    return next(get_db())

@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_data: SiteCreate,
    db: Optional[Session] = Depends(get_db_optional)
) -> SiteResponse:
    """
    Create a new site.
    
    Args:
        site_data: Site creation data
        db: Database session (optional when SKIP_DB_INIT is set)
        
    Returns:
        Created site data
        
    Raises:
        HTTPException: If site creation fails
    """
    # Mock response when database is disabled
    if os.getenv('SKIP_DB_INIT'):
        logger.warning("Database disabled - returning mock site response")
        
        # Calculate derived properties
        bench_height = site_data.bench_geometry.bench_top_elevation - site_data.bench_geometry.bench_bottom_elevation
        bench_area = site_data.bench_geometry.bench_width * site_data.bench_geometry.bench_length
        bench_volume = bench_area * bench_height
        
        return SiteResponse(
            id=1,
            name=site_data.name,
            description=site_data.description,
            location=site_data.location,
            coordinates=site_data.coordinates,
            is_active=True,
            site_type=site_data.site_type,
            regulatory_zone=site_data.regulatory_zone,
            bench_geometry=site_data.bench_geometry,
            rock_properties=site_data.rock_properties,
            equipment_specs=site_data.equipment_specs,
            operational_constraints=site_data.operational_constraints,
            safety_config=site_data.safety_config,
            bench_height=bench_height,
            bench_area=bench_area,
            bench_volume=bench_volume,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    try:
        site_repo = SiteRepository(db)
        
        # Check if site name already exists
        existing_site = site_repo.get_by_name(site_data.name)
        if existing_site:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Site with name '{site_data.name}' already exists"
            )
        
        # Create site
        site = site_repo.create(site_data.dict())
        
        logger.info(
            "Site created successfully",
            site_id=site.id,
            site_name=site.name
        )
        
        return SiteResponse.from_orm(site)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create site",
            site_name=site_data.name,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create site"
        )


@router.get("/", response_model=List[SiteResponse])
async def list_sites(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    active_only: bool = Query(True, description="Return only active sites"),
    site_type: Optional[str] = Query(None, description="Filter by site type"),
    search: Optional[str] = Query(None, description="Search by name or location"),
    db: Session = Depends(get_db)
) -> List[SiteResponse]:
    """
    List sites with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Return only active sites
        site_type: Filter by site type
        search: Search by name or location
        db: Database session
        
    Returns:
        List of sites
    """
    try:
        site_repo = SiteRepository(db)
        
        if search:
            # Search by name or location pattern
            sites = site_repo.search_by_name(f"%{search}%")
            location_sites = site_repo.get_by_location(f"%{search}%")
            
            # Combine and deduplicate results
            site_ids = set()
            combined_sites = []
            for site in sites + location_sites:
                if site.id not in site_ids:
                    site_ids.add(site.id)
                    combined_sites.append(site)
            
            sites = combined_sites
        elif site_type:
            sites = site_repo.get_by_site_type(site_type)
        elif active_only:
            sites = site_repo.get_active_sites(skip=skip, limit=limit)
        else:
            sites = site_repo.get_all(skip=skip, limit=limit)
        
        # Apply pagination if not already applied
        if search or site_type:
            sites = sites[skip:skip + limit]
        
        logger.debug(
            "Sites retrieved",
            count=len(sites),
            skip=skip,
            limit=limit,
            active_only=active_only,
            site_type=site_type,
            search=search
        )
        
        return [SiteResponse.from_orm(site) for site in sites]
        
    except Exception as e:
        logger.error("Failed to list sites", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sites"
        )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    db: Session = Depends(get_db)
) -> SiteResponse:
    """
    Get a specific site by ID.
    
    Args:
        site_id: Site ID
        db: Database session
        
    Returns:
        Site data
        
    Raises:
        HTTPException: If site not found
    """
    try:
        site_repo = SiteRepository(db)
        site = site_repo.get_by_id(site_id)
        
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {site_id} not found"
            )
        
        logger.debug("Site retrieved", site_id=site_id, site_name=site.name)
        
        return SiteResponse.from_orm(site)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get site",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site"
        )


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    site_data: SiteUpdate,
    db: Session = Depends(get_db)
) -> SiteResponse:
    """
    Update a site.
    
    Args:
        site_id: Site ID
        site_data: Site update data
        db: Database session
        
    Returns:
        Updated site data
        
    Raises:
        HTTPException: If site not found or update fails
    """
    try:
        site_repo = SiteRepository(db)
        
        # Check if site exists
        existing_site = site_repo.get_by_id(site_id)
        if not existing_site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {site_id} not found"
            )
        
        # Check for name conflicts if name is being updated
        if site_data.name and site_data.name != existing_site.name:
            name_conflict = site_repo.get_by_name(site_data.name)
            if name_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Site with name '{site_data.name}' already exists"
                )
        
        # Update site
        update_dict = site_data.dict(exclude_unset=True)
        updated_site = site_repo.update(site_id, update_dict)
        
        if not updated_site:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update site"
            )
        
        logger.info(
            "Site updated successfully",
            site_id=site_id,
            site_name=updated_site.name
        )
        
        return SiteResponse.from_orm(updated_site)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update site",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update site"
        )


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    force: bool = Query(False, description="Force delete (hard delete)"),
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a site (soft delete by default).
    
    Args:
        site_id: Site ID
        force: Force delete (hard delete)
        db: Database session
        
    Raises:
        HTTPException: If site not found or deletion fails
    """
    try:
        site_repo = SiteRepository(db)
        
        # Check if site exists
        existing_site = site_repo.get_by_id(site_id)
        if not existing_site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {site_id} not found"
            )
        
        if force:
            # Hard delete
            deleted = site_repo.delete(site_id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete site"
                )
            logger.info("Site hard deleted", site_id=site_id)
        else:
            # Soft delete (deactivate)
            deactivated = site_repo.deactivate_site(site_id)
            if not deactivated:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to deactivate site"
                )
            logger.info("Site deactivated", site_id=site_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete site",
            site_id=site_id,
            force=force,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete site"
        )


@router.post("/{site_id}/reactivate", response_model=SiteResponse)
async def reactivate_site(
    site_id: int,
    db: Session = Depends(get_db)
) -> SiteResponse:
    """
    Reactivate a deactivated site.
    
    Args:
        site_id: Site ID
        db: Database session
        
    Returns:
        Reactivated site data
        
    Raises:
        HTTPException: If site not found or reactivation fails
    """
    try:
        site_repo = SiteRepository(db)
        
        # Check if site exists
        existing_site = site_repo.get_by_id(site_id)
        if not existing_site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {site_id} not found"
            )
        
        # Reactivate site
        reactivated = site_repo.reactivate_site(site_id)
        if not reactivated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reactivate site"
            )
        
        # Get updated site
        updated_site = site_repo.get_by_id(site_id)
        
        logger.info("Site reactivated", site_id=site_id)
        
        return SiteResponse.from_orm(updated_site)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to reactivate site",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate site"
        )


@router.get("/{site_id}/validate", response_model=Dict[str, Any])
async def validate_site(
    site_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate site data for completeness and consistency.
    
    Args:
        site_id: Site ID
        db: Database session
        
    Returns:
        Validation results
        
    Raises:
        HTTPException: If site not found or validation fails
    """
    try:
        site_repo = SiteRepository(db)
        
        # Check if site exists
        existing_site = site_repo.get_by_id(site_id)
        if not existing_site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {site_id} not found"
            )
        
        # Validate site data
        validation_results = site_repo.validate_site_data(site_id)
        
        logger.debug(
            "Site validation completed",
            site_id=site_id,
            errors=len(validation_results.get("errors", [])),
            warnings=len(validation_results.get("warnings", []))
        )
        
        return validation_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to validate site",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate site"
        )


@router.get("/statistics/summary", response_model=Dict[str, Any])
async def get_site_statistics(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get site statistics summary.
    
    Args:
        db: Database session
        
    Returns:
        Site statistics
    """
    try:
        site_repo = SiteRepository(db)
        statistics = site_repo.get_site_statistics()
        
        logger.debug("Site statistics retrieved", statistics=statistics)
        
        return statistics
        
    except Exception as e:
        logger.error("Failed to get site statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site statistics"
        )