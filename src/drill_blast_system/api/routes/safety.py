"""
Safety validation API endpoints.
Implements requirement 8.4: Safety validation endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ...core.logging import get_logger
from ...repositories.blast_record import BlastRecordRepository
from ...repositories.site import SiteRepository
from ...safety.validator import SafetyValidator
from ...safety.config import SafetyConfig
from ...safety.models import SafetyStatus, SafetyViolation
from ...schemas.blast_record import SafetyValidation, SafetyCheck, BlastPlan

router = APIRouter()
logger = get_logger(__name__)


class SafetyValidationRequest(BaseModel):
    """Safety validation request schema."""
    blast_plan: BlastPlan
    site_id: int
    safety_config_override: Optional[Dict[str, Any]] = None


class SafetyValidationResponse(BaseModel):
    """Safety validation response schema."""
    is_valid: bool
    validation_timestamp: str
    safety_checks: List[Dict[str, Any]]
    violations: List[Dict[str, Any]]
    safety_config_used: Dict[str, Any]
    recommendations: List[str]


class SafetyConfigResponse(BaseModel):
    """Safety configuration response schema."""
    max_charge_per_hole: float
    max_charge_per_delay: float
    powder_factor_min: float
    powder_factor_max: float
    ppv_default_limit: float
    receptor_limits: Dict[str, float]
    regulatory_zone: Optional[str] = None


@router.post("/validate", response_model=SafetyValidationResponse)
async def validate_blast_plan(
    validation_request: SafetyValidationRequest,
    db: Session = Depends(get_db)
) -> SafetyValidationResponse:
    """
    Validate a blast plan against safety constraints.
    
    Args:
        validation_request: Safety validation request
        db: Database session
        
    Returns:
        Safety validation results
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        site_repo = SiteRepository(db)
        
        # Get site data
        site = site_repo.get_by_id(validation_request.site_id)
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {validation_request.site_id} not found"
            )
        
        # Initialize safety configuration
        safety_config = SafetyConfig()
        
        # Apply site-specific safety configuration if available
        if site.safety_config:
            safety_config.update_from_dict(site.safety_config)
        
        # Apply override configuration if provided
        if validation_request.safety_config_override:
            safety_config.update_from_dict(validation_request.safety_config_override)
        
        # Initialize safety validator
        safety_validator = SafetyValidator(safety_config)
        
        # Convert blast plan to internal format
        blast_plan_dict = validation_request.blast_plan.dict()
        
        # Perform safety validation
        safety_status = safety_validator.validate_blast_plan(blast_plan_dict)
        
        # Generate recommendations
        recommendations = []
        if not safety_status.is_valid:
            recommendations = safety_validator.generate_recommendations(safety_status.violations)
        
        logger.info(
            "Safety validation completed",
            site_id=validation_request.site_id,
            is_valid=safety_status.is_valid,
            violation_count=len(safety_status.violations)
        )
        
        return SafetyValidationResponse(
            is_valid=safety_status.is_valid,
            validation_timestamp=safety_status.validation_timestamp.isoformat(),
            safety_checks=safety_status.safety_checks,
            violations=[v.dict() for v in safety_status.violations],
            safety_config_used=safety_config.to_dict(),
            recommendations=recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to validate blast plan",
            site_id=validation_request.site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate blast plan"
        )


@router.get("/validate/{blast_id}", response_model=SafetyValidationResponse)
async def validate_existing_blast_plan(
    blast_id: int,
    revalidate: bool = Query(False, description="Force revalidation"),
    db: Session = Depends(get_db)
) -> SafetyValidationResponse:
    """
    Validate an existing blast plan.
    
    Args:
        blast_id: Blast plan ID
        revalidate: Force revalidation
        db: Database session
        
    Returns:
        Safety validation results
        
    Raises:
        HTTPException: If blast plan not found or validation fails
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
        
        # Return existing validation if available and not forcing revalidation
        if not revalidate and blast.safety_validation:
            return SafetyValidationResponse(
                is_valid=blast.safety_validation.get("is_valid", False),
                validation_timestamp=blast.safety_validation.get("validation_timestamp", ""),
                safety_checks=blast.safety_validation.get("safety_checks", []),
                violations=blast.safety_validation.get("violations", []),
                safety_config_used=blast.safety_validation.get("safety_config_used", {}),
                recommendations=blast.safety_validation.get("recommendations", [])
            )
        
        # Get site data
        site = site_repo.get_by_id(blast.site_id)
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with ID {blast.site_id} not found"
            )
        
        # Perform validation
        validation_request = SafetyValidationRequest(
            blast_plan=BlastPlan(**blast.plan_data),
            site_id=blast.site_id
        )
        
        validation_result = await validate_blast_plan(validation_request, db)
        
        # Update blast record with new validation results
        blast_repo.update(blast_id, {
            "safety_validation": validation_result.dict()
        })
        
        logger.info(
            "Existing blast plan validated",
            blast_id=blast_id,
            is_valid=validation_result.is_valid
        )
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to validate existing blast plan",
            blast_id=blast_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate existing blast plan"
        )


@router.get("/config", response_model=SafetyConfigResponse)
async def get_safety_config(
    site_id: Optional[int] = Query(None, description="Site ID for site-specific config"),
    db: Session = Depends(get_db)
) -> SafetyConfigResponse:
    """
    Get safety configuration parameters.
    
    Args:
        site_id: Optional site ID for site-specific configuration
        db: Database session
        
    Returns:
        Safety configuration parameters
    """
    try:
        # Initialize default safety configuration
        safety_config = SafetyConfig()
        
        # Apply site-specific configuration if requested
        if site_id:
            site_repo = SiteRepository(db)
            site = site_repo.get_by_id(site_id)
            if not site:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Site with ID {site_id} not found"
                )
            
            if site.safety_config:
                safety_config.update_from_dict(site.safety_config)
        
        logger.debug(
            "Safety configuration retrieved",
            site_id=site_id,
            config=safety_config.to_dict()
        )
        
        return SafetyConfigResponse(
            max_charge_per_hole=safety_config.max_charge_per_hole,
            max_charge_per_delay=safety_config.max_charge_per_delay,
            powder_factor_min=safety_config.powder_factor_min,
            powder_factor_max=safety_config.powder_factor_max,
            ppv_default_limit=safety_config.ppv_default_limit,
            receptor_limits=safety_config.receptor_limits,
            regulatory_zone=getattr(safety_config, 'regulatory_zone', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get safety configuration",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve safety configuration"
        )


@router.put("/config", response_model=SafetyConfigResponse)
async def update_safety_config(
    config_update: Dict[str, Any],
    site_id: Optional[int] = Query(None, description="Site ID for site-specific config"),
    db: Session = Depends(get_db)
) -> SafetyConfigResponse:
    """
    Update safety configuration parameters.
    
    Args:
        config_update: Configuration updates
        site_id: Optional site ID for site-specific configuration
        db: Database session
        
    Returns:
        Updated safety configuration parameters
        
    Raises:
        HTTPException: If update fails or site not found
    """
    try:
        if site_id:
            # Update site-specific configuration
            site_repo = SiteRepository(db)
            site = site_repo.get_by_id(site_id)
            if not site:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Site with ID {site_id} not found"
                )
            
            # Merge with existing site safety config
            current_config = site.safety_config or {}
            updated_config = {**current_config, **config_update}
            
            # Update site
            site_repo.update(site_id, {"safety_config": updated_config})
            
            # Return updated configuration
            safety_config = SafetyConfig()
            safety_config.update_from_dict(updated_config)
            
            logger.info(
                "Site-specific safety configuration updated",
                site_id=site_id,
                updated_fields=list(config_update.keys())
            )
        else:
            # Update global configuration (would require admin privileges in real implementation)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Global safety configuration updates require admin privileges"
            )
        
        return SafetyConfigResponse(
            max_charge_per_hole=safety_config.max_charge_per_hole,
            max_charge_per_delay=safety_config.max_charge_per_delay,
            powder_factor_min=safety_config.powder_factor_min,
            powder_factor_max=safety_config.powder_factor_max,
            ppv_default_limit=safety_config.ppv_default_limit,
            receptor_limits=safety_config.receptor_limits,
            regulatory_zone=getattr(safety_config, 'regulatory_zone', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update safety configuration",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update safety configuration"
        )


@router.get("/violations", response_model=List[Dict[str, Any]])
async def get_safety_violations(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    severity: Optional[str] = Query(None, description="Filter by violation severity"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get blast plans with safety violations.
    
    Args:
        site_id: Optional site ID filter
        severity: Optional violation severity filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of blast plans with safety violations
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Get blasts with safety violations
        blasts_with_violations = blast_repo.get_blasts_with_safety_violations(site_id=site_id)
        
        # Filter by severity if specified
        if severity:
            filtered_blasts = []
            for blast in blasts_with_violations:
                if blast.safety_validation and "violations" in blast.safety_validation:
                    violations = blast.safety_validation["violations"]
                    if any(v.get("severity") == severity for v in violations):
                        filtered_blasts.append(blast)
            blasts_with_violations = filtered_blasts
        
        # Apply pagination
        paginated_blasts = blasts_with_violations[skip:skip + limit]
        
        # Format response
        violations_data = []
        for blast in paginated_blasts:
            if blast.safety_validation and "violations" in blast.safety_validation:
                for violation in blast.safety_validation["violations"]:
                    violations_data.append({
                        "blast_id": blast.id,
                        "blast_name": blast.blast_name,
                        "site_id": blast.site_id,
                        "violation": violation,
                        "validation_timestamp": blast.safety_validation.get("validation_timestamp")
                    })
        
        logger.debug(
            "Safety violations retrieved",
            site_id=site_id,
            severity=severity,
            count=len(violations_data)
        )
        
        return violations_data
        
    except Exception as e:
        logger.error(
            "Failed to get safety violations",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve safety violations"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_safety_statistics(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get safety validation statistics.
    
    Args:
        site_id: Optional site ID filter
        db: Database session
        
    Returns:
        Safety validation statistics
    """
    try:
        blast_repo = BlastRecordRepository(db)
        
        # Get all blasts for the site
        if site_id:
            all_blasts = blast_repo.get_by_site_id(site_id, skip=0, limit=10000)
        else:
            all_blasts = blast_repo.get_all(skip=0, limit=10000)
        
        # Calculate statistics
        total_blasts = len(all_blasts)
        validated_blasts = len([b for b in all_blasts if b.safety_validation])
        valid_blasts = len([
            b for b in all_blasts 
            if b.safety_validation and b.safety_validation.get("is_valid", False)
        ])
        invalid_blasts = len([
            b for b in all_blasts 
            if b.safety_validation and not b.safety_validation.get("is_valid", True)
        ])
        
        # Count violations by type
        violation_types = {}
        for blast in all_blasts:
            if blast.safety_validation and "violations" in blast.safety_validation:
                for violation in blast.safety_validation["violations"]:
                    violation_type = violation.get("violation_type", "unknown")
                    violation_types[violation_type] = violation_types.get(violation_type, 0) + 1
        
        statistics = {
            "total_blasts": total_blasts,
            "validated_blasts": validated_blasts,
            "valid_blasts": valid_blasts,
            "invalid_blasts": invalid_blasts,
            "validation_rate": validated_blasts / total_blasts if total_blasts > 0 else 0,
            "pass_rate": valid_blasts / validated_blasts if validated_blasts > 0 else 0,
            "violation_types": violation_types
        }
        
        logger.debug(
            "Safety statistics retrieved",
            site_id=site_id,
            statistics=statistics
        )
        
        return statistics
        
    except Exception as e:
        logger.error(
            "Failed to get safety statistics",
            site_id=site_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve safety statistics"
        )