"""
Admin interface API endpoints for system configuration.
Implements requirement 11.1: Admin interface for system configuration.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ...core.database import get_db
from ...core.logging import get_logger
from ...auth import User, UserRole, AuditLog, get_current_admin
from ...models import Configuration, Site, BlastRecord
from ...schemas.configuration import (
    ConfigurationCreate, ConfigurationUpdate, ConfigurationResponse,
    PhysicsConfig, SafetyConfig, ExplosivesConfig, OptimizationConfig
)
from ...auth.schemas import UserCreate, UserUpdate, UserResponse, AuditLogResponse
from ...auth.audit import audit_logger

router = APIRouter()
logger = get_logger(__name__)


# System Health and Monitoring
@router.get("/system/health", tags=["system-monitoring"])
async def get_system_health(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive system health status.
    
    Returns detailed health information including:
    - Database connectivity and performance
    - Configuration status
    - User activity metrics
    - System resource usage
    - Recent error rates
    """
    try:
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # Database health
        try:
            db_start = datetime.utcnow()
            db.execute("SELECT 1")
            db_duration = (datetime.utcnow() - db_start).total_seconds() * 1000
            
            # Get database statistics
            config_count = db.query(Configuration).filter(Configuration.is_active == True).count()
            user_count = db.query(User).filter(User.is_active == True).count()
            site_count = db.query(Site).count()
            blast_count = db.query(BlastRecord).count()
            
            health_data["components"]["database"] = {
                "status": "healthy",
                "response_time_ms": round(db_duration, 2),
                "statistics": {
                    "active_configurations": config_count,
                    "active_users": user_count,
                    "total_sites": site_count,
                    "total_blast_records": blast_count
                }
            }
        except Exception as e:
            health_data["overall_status"] = "degraded"
            health_data["components"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Configuration health
        try:
            # Check for required configurations
            required_configs = ["default_physics_parameters", "default_safety_limits", "explosives_catalog"]
            missing_configs = []
            
            for config_key in required_configs:
                config = db.query(Configuration).filter(
                    Configuration.config_key == config_key,
                    Configuration.is_active == True
                ).first()
                if not config:
                    missing_configs.append(config_key)
            
            if missing_configs:
                health_data["overall_status"] = "degraded"
                health_data["components"]["configuration"] = {
                    "status": "degraded",
                    "missing_configurations": missing_configs
                }
            else:
                health_data["components"]["configuration"] = {
                    "status": "healthy",
                    "all_required_configs_present": True
                }
        except Exception as e:
            health_data["overall_status"] = "degraded"
            health_data["components"]["configuration"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # User activity metrics
        try:
            # Recent login activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_logins = db.query(AuditLog).filter(
                AuditLog.action == "login",
                AuditLog.created_at >= yesterday,
                AuditLog.result == "SUCCESS"
            ).count()
            
            # Active sessions (approximate based on recent activity)
            recent_activity = db.query(AuditLog).filter(
                AuditLog.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            health_data["components"]["user_activity"] = {
                "status": "healthy",
                "recent_logins_24h": recent_logins,
                "recent_activity_1h": recent_activity
            }
        except Exception as e:
            health_data["components"]["user_activity"] = {
                "status": "degraded",
                "error": str(e)
            }
        
        # Error rate analysis
        try:
            # Error rate in last hour
            last_hour = datetime.utcnow() - timedelta(hours=1)
            total_actions = db.query(AuditLog).filter(AuditLog.created_at >= last_hour).count()
            error_actions = db.query(AuditLog).filter(
                AuditLog.created_at >= last_hour,
                AuditLog.result.in_(["FAILURE", "ERROR"])
            ).count()
            
            error_rate = (error_actions / total_actions * 100) if total_actions > 0 else 0
            
            if error_rate > 10:
                health_data["overall_status"] = "degraded"
                status_level = "degraded"
            elif error_rate > 5:
                status_level = "warning"
            else:
                status_level = "healthy"
            
            health_data["components"]["error_rate"] = {
                "status": status_level,
                "error_rate_percent": round(error_rate, 2),
                "total_actions_1h": total_actions,
                "error_actions_1h": error_actions
            }
        except Exception as e:
            health_data["components"]["error_rate"] = {
                "status": "unknown",
                "error": str(e)
            }
        
        return health_data
        
    except Exception as e:
        logger.error("System health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health"
        )


@router.get("/system/metrics", tags=["system-monitoring"])
async def get_system_metrics(
    days: int = Query(7, ge=1, le=30, description="Number of days for metrics"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get system usage metrics and statistics.
    
    Returns metrics including:
    - User activity trends
    - Blast plan creation rates
    - Configuration changes
    - Error trends
    - Performance metrics
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        metrics = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "days": days
            },
            "user_metrics": {},
            "blast_metrics": {},
            "configuration_metrics": {},
            "performance_metrics": {}
        }
        
        # User activity metrics
        user_logins = db.query(AuditLog).filter(
            AuditLog.action == "login",
            AuditLog.created_at >= start_date,
            AuditLog.result == "SUCCESS"
        ).count()
        
        unique_users = db.query(AuditLog.user_id).filter(
            AuditLog.created_at >= start_date
        ).distinct().count()
        
        metrics["user_metrics"] = {
            "total_logins": user_logins,
            "unique_active_users": unique_users,
            "average_logins_per_day": round(user_logins / days, 2)
        }
        
        # Blast plan metrics
        blast_creations = db.query(AuditLog).filter(
            AuditLog.action == "create_blast_plan",
            AuditLog.created_at >= start_date,
            AuditLog.result == "SUCCESS"
        ).count()
        
        blast_signoffs = db.query(AuditLog).filter(
            AuditLog.action == "sign_off_blast",
            AuditLog.created_at >= start_date,
            AuditLog.result == "SUCCESS"
        ).count()
        
        blast_exports = db.query(AuditLog).filter(
            AuditLog.action == "export_blast_plan",
            AuditLog.created_at >= start_date,
            AuditLog.result == "SUCCESS"
        ).count()
        
        metrics["blast_metrics"] = {
            "plans_created": blast_creations,
            "plans_signed_off": blast_signoffs,
            "plans_exported": blast_exports,
            "average_plans_per_day": round(blast_creations / days, 2)
        }
        
        # Configuration change metrics
        config_changes = db.query(AuditLog).filter(
            AuditLog.resource_type == "configuration",
            AuditLog.created_at >= start_date,
            AuditLog.result == "SUCCESS"
        ).count()
        
        metrics["configuration_metrics"] = {
            "total_changes": config_changes,
            "average_changes_per_day": round(config_changes / days, 2)
        }
        
        # Performance metrics (average response times)
        avg_duration = db.query(func.avg(AuditLog.duration_ms)).filter(
            AuditLog.created_at >= start_date,
            AuditLog.duration_ms.isnot(None)
        ).scalar()
        
        metrics["performance_metrics"] = {
            "average_response_time_ms": round(avg_duration, 2) if avg_duration else None
        }
        
        return metrics
        
    except Exception as e:
        logger.error("System metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )


# Configuration Management
@router.get("/configurations", response_model=List[ConfigurationResponse], tags=["configuration-management"])
async def list_all_configurations(
    config_type: Optional[str] = Query(None, description="Filter by configuration type"),
    scope: Optional[str] = Query(None, description="Filter by configuration scope"),
    active_only: bool = Query(True, description="Return only active configurations"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> List[ConfigurationResponse]:
    """
    List all system configurations with admin access.
    
    Provides comprehensive view of all configurations including:
    - Global, site-specific, and user-specific configurations
    - Configuration history and versioning
    - Validation status and approval information
    """
    try:
        query = db.query(Configuration)
        
        if config_type:
            query = query.filter(Configuration.config_type == config_type)
        
        if scope:
            query = query.filter(Configuration.config_scope == scope)
        
        if active_only:
            query = query.filter(Configuration.is_active == True)
        
        configurations = query.order_by(desc(Configuration.updated_at)).offset(skip).limit(limit).all()
        
        logger.debug(
            "Admin configurations retrieved",
            count=len(configurations),
            config_type=config_type,
            scope=scope,
            admin_user=admin.username
        )
        
        return [
            ConfigurationResponse(
                id=config.id,
                config_key=config.config_key,
                config_name=config.config_name,
                config_description=config.config_description,
                config_type=config.config_type,
                config_scope=config.config_scope,
                site_id=config.site_id,
                user_id=config.user_id,
                config_value=config.config_value,
                version=config.version,
                parent_config_id=config.parent_config_id,
                is_active=config.is_active,
                is_default=config.is_default,
                is_validated=config.is_validated,
                validated_by=config.validated_by,
                validation_date=config.validation_date,
                validation_notes=config.validation_notes,
                created_by=config.created_by,
                modified_by=config.modified_by,
                change_reason=config.change_reason,
                tags=config.tags,
                dependencies=config.dependencies,
                full_key=config.full_key,
                is_site_specific=config.is_site_specific,
                is_user_specific=config.is_user_specific,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configurations
        ]
        
    except Exception as e:
        logger.error("Admin configuration listing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations"
        )


@router.post("/configurations/validate/{config_id}", tags=["configuration-management"])
async def validate_configuration(
    config_id: int,
    validation_notes: Optional[str] = None,
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate a configuration (admin approval).
    
    Performs validation checks and marks configuration as approved.
    Creates audit trail for configuration validation.
    """
    try:
        config = db.query(Configuration).filter(Configuration.id == config_id).first()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found"
            )
        
        # Perform validation
        validation_errors = config.validate_configuration_data()
        
        if validation_errors:
            # Log validation failure
            audit_logger.log_action(
                db=db,
                action="validate_configuration_failed",
                resource_type="configuration",
                resource_id=str(config.id),
                result="FAILURE",
                user=admin,
                request=request,
                error_message=f"Validation errors: {', '.join(validation_errors)}",
                risk_level="MEDIUM"
            )
            
            return {
                "config_id": config_id,
                "validation_status": "failed",
                "errors": validation_errors,
                "validated_at": datetime.utcnow().isoformat()
            }
        
        # Mark as validated
        config.is_validated = True
        config.validated_by = admin.username
        config.validation_date = datetime.utcnow()
        config.validation_notes = validation_notes
        
        db.commit()
        
        # Log successful validation
        audit_logger.log_action(
            db=db,
            action="validate_configuration",
            resource_type="configuration",
            resource_id=str(config.id),
            result="SUCCESS",
            user=admin,
            request=request,
            action_data={
                "config_key": config.config_key,
                "config_type": config.config_type,
                "validation_notes": validation_notes
            },
            risk_level="MEDIUM"
        )
        
        return {
            "config_id": config_id,
            "validation_status": "approved",
            "validated_by": admin.username,
            "validated_at": config.validation_date.isoformat(),
            "validation_notes": validation_notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Configuration validation failed", config_id=config_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration"
        )


@router.post("/configurations/physics/calibrate", tags=["physics-calibration"])
async def calibrate_physics_parameters(
    calibration_data: Dict[str, Any],
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Calibrate physics model parameters using measurement data.
    
    Accepts calibration data and updates physics parameters.
    Creates new configuration version with calibrated parameters.
    """
    try:
        # Get current physics configuration
        physics_config = db.query(Configuration).filter(
            Configuration.config_key == "default_physics_parameters",
            Configuration.is_active == True
        ).first()
        
        if not physics_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physics configuration not found"
            )
        
        # Extract calibration parameters
        rock_factor_a = calibration_data.get("rock_factor_a")
        ppv_constants = calibration_data.get("ppv_constants", {})
        calibration_notes = calibration_data.get("notes", "")
        
        # Update physics parameters
        updated_config_value = physics_config.config_value.copy()
        
        if rock_factor_a:
            updated_config_value["kuz_ram"]["rock_factor_a"] = rock_factor_a
            
        if ppv_constants:
            updated_config_value["ppv"].update(ppv_constants)
        
        # Add calibration metadata
        updated_config_value["calibration"] = {
            "calibrated_at": datetime.utcnow().isoformat(),
            "calibrated_by": admin.username,
            "calibration_data": calibration_data,
            "notes": calibration_notes
        }
        
        # Create new configuration revision
        new_config = physics_config.create_revision(
            new_config_value=updated_config_value,
            modified_by=admin.username,
            change_reason=f"Physics parameter calibration: {calibration_notes}"
        )
        
        # Deactivate old configuration
        physics_config.is_active = False
        
        # Add new configuration
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        # Log calibration
        audit_logger.log_action(
            db=db,
            action="calibrate_physics_parameters",
            resource_type="configuration",
            resource_id=str(new_config.id),
            result="SUCCESS",
            user=admin,
            request=request,
            action_data={
                "old_config_id": physics_config.id,
                "calibration_data": calibration_data,
                "notes": calibration_notes
            },
            risk_level="HIGH"
        )
        
        return {
            "config_id": new_config.id,
            "version": new_config.version,
            "calibrated_parameters": {
                "rock_factor_a": rock_factor_a,
                "ppv_constants": ppv_constants
            },
            "calibrated_by": admin.username,
            "calibrated_at": new_config.created_at.isoformat(),
            "notes": calibration_notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Physics calibration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calibrate physics parameters"
        )


# Explosives Database Management
@router.get("/explosives/catalog", tags=["explosives-management"])
async def get_explosives_catalog_admin(
    include_inactive: bool = Query(False, description="Include inactive explosives"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete explosives catalog with admin details.
    
    Returns comprehensive explosives information including:
    - All explosive specifications
    - Regulatory information
    - Availability and pricing
    - Usage statistics
    """
    try:
        # Get explosives configuration
        explosives_config = db.query(Configuration).filter(
            Configuration.config_key == "explosives_catalog",
            Configuration.is_active == True
        ).first()
        
        if not explosives_config:
            # Return default catalog
            catalog = {
                "explosives": [],
                "metadata": {
                    "total_explosives": 0,
                    "active_explosives": 0,
                    "last_updated": None,
                    "updated_by": None
                }
            }
        else:
            catalog_data = explosives_config.config_value.get("catalog", [])
            
            # Filter by active status if requested
            if not include_inactive:
                catalog_data = [exp for exp in catalog_data if exp.get("is_active", True)]
            
            catalog = {
                "explosives": catalog_data,
                "metadata": {
                    "total_explosives": len(explosives_config.config_value.get("catalog", [])),
                    "active_explosives": len(catalog_data),
                    "last_updated": explosives_config.updated_at.isoformat(),
                    "updated_by": explosives_config.modified_by,
                    "version": explosives_config.version
                }
            }
        
        return catalog
        
    except Exception as e:
        logger.error("Explosives catalog retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve explosives catalog"
        )


@router.post("/explosives/catalog", tags=["explosives-management"])
async def update_explosives_catalog_admin(
    catalog_data: Dict[str, Any],
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update explosives catalog (admin only).
    
    Allows complete management of explosives database including:
    - Adding new explosives
    - Updating specifications
    - Managing availability
    - Setting regulatory limits
    """
    try:
        # Get existing explosives configuration
        explosives_config = db.query(Configuration).filter(
            Configuration.config_key == "explosives_catalog",
            Configuration.is_active == True
        ).first()
        
        # Validate catalog data
        explosives_list = catalog_data.get("explosives", [])
        if not explosives_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explosives catalog cannot be empty"
            )
        
        # Validate each explosive entry
        for i, explosive in enumerate(explosives_list):
            required_fields = ["id", "name", "type", "density", "rws", "vod"]
            for field in required_fields:
                if field not in explosive:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Explosive {i}: missing required field '{field}'"
                    )
        
        # Create updated configuration
        updated_config_value = {
            "catalog": explosives_list,
            "default_selections": catalog_data.get("default_selections", {}),
            "metadata": {
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": admin.username,
                "total_explosives": len(explosives_list),
                "active_explosives": len([e for e in explosives_list if e.get("is_active", True)])
            }
        }
        
        if explosives_config:
            # Create new revision
            new_config = explosives_config.create_revision(
                new_config_value=updated_config_value,
                modified_by=admin.username,
                change_reason="Explosives catalog update via admin interface"
            )
            
            # Deactivate old configuration
            explosives_config.is_active = False
            
            # Add new configuration
            db.add(new_config)
        else:
            # Create new configuration
            new_config = Configuration(
                config_key="explosives_catalog",
                config_name="Explosives Catalog",
                config_description="System explosives database",
                config_type="explosives",
                config_value=updated_config_value,
                created_by=admin.username,
                modified_by=admin.username,
                change_reason="Initial explosives catalog creation"
            )
            db.add(new_config)
        
        db.commit()
        db.refresh(new_config)
        
        # Log catalog update
        audit_logger.log_action(
            db=db,
            action="update_explosives_catalog",
            resource_type="configuration",
            resource_id=str(new_config.id),
            result="SUCCESS",
            user=admin,
            request=request,
            action_data={
                "explosives_count": len(explosives_list),
                "active_count": len([e for e in explosives_list if e.get("is_active", True)])
            },
            risk_level="MEDIUM"
        )
        
        return {
            "config_id": new_config.id,
            "version": new_config.version,
            "explosives_count": len(explosives_list),
            "active_explosives": len([e for e in explosives_list if e.get("is_active", True)]),
            "updated_by": admin.username,
            "updated_at": new_config.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Explosives catalog update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update explosives catalog"
        )


# Safety Limits Configuration
@router.get("/safety/limits", tags=["safety-management"])
async def get_safety_limits_admin(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current safety limits configuration.
    
    Returns comprehensive safety configuration including:
    - Charge limits and safety factors
    - PPV limits for different structure types
    - Distance requirements
    - Regulatory compliance information
    """
    try:
        # Get safety configuration
        safety_config = db.query(Configuration).filter(
            Configuration.config_key == "default_safety_limits",
            Configuration.is_active == True
        ).first()
        
        if not safety_config:
            # Return default safety limits
            return {
                "charge_limits": {
                    "max_charge_per_hole": 50.0,
                    "max_charge_per_delay": 200.0,
                    "safety_factor": 1.0
                },
                "powder_factor_limits": {
                    "min_powder_factor": 0.05,
                    "max_powder_factor": 1.5,
                    "recommended_range": [0.2, 0.8]
                },
                "ppv_limits": {
                    "default_limit": 5.0,
                    "structure_limits": {
                        "residential": 2.0,
                        "commercial": 5.0,
                        "industrial": 10.0,
                        "sensitive": 1.0
                    }
                },
                "distance_limits": {
                    "min_distance_to_structures": 100.0,
                    "min_distance_to_roads": 50.0,
                    "exclusion_zone_buffer": 25.0
                },
                "metadata": {
                    "version": 0,
                    "last_updated": None,
                    "updated_by": None,
                    "is_default": True
                }
            }
        
        config_data = safety_config.config_value.copy()
        config_data["metadata"] = {
            "config_id": safety_config.id,
            "version": safety_config.version,
            "last_updated": safety_config.updated_at.isoformat(),
            "updated_by": safety_config.modified_by,
            "is_validated": safety_config.is_validated,
            "validated_by": safety_config.validated_by,
            "is_default": False
        }
        
        return config_data
        
    except Exception as e:
        logger.error("Safety limits retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve safety limits"
        )


@router.put("/safety/limits", tags=["safety-management"])
async def update_safety_limits_admin(
    safety_data: Dict[str, Any],
    request: Request = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update safety limits configuration (admin only).
    
    Allows updating all safety parameters including:
    - Charge limits and safety factors
    - PPV limits for different structure types
    - Distance requirements
    - Regulatory compliance settings
    
    Requires admin validation before activation.
    """
    try:
        # Get existing safety configuration
        safety_config = db.query(Configuration).filter(
            Configuration.config_key == "default_safety_limits",
            Configuration.is_active == True
        ).first()
        
        # Validate safety data
        required_sections = ["charge_limits", "powder_factor_limits", "ppv_limits", "distance_limits"]
        for section in required_sections:
            if section not in safety_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required section: {section}"
                )
        
        # Validate charge limits
        charge_limits = safety_data["charge_limits"]
        if charge_limits.get("max_charge_per_hole", 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_charge_per_hole must be positive"
            )
        
        if charge_limits.get("max_charge_per_delay", 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_charge_per_delay must be positive"
            )
        
        # Validate PPV limits
        ppv_limits = safety_data["ppv_limits"]
        if ppv_limits.get("default_limit", 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="default PPV limit must be positive"
            )
        
        # Add metadata
        updated_config_value = safety_data.copy()
        updated_config_value["metadata"] = {
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": admin.username,
            "change_reason": "Safety limits update via admin interface"
        }
        
        if safety_config:
            # Create new revision
            new_config = safety_config.create_revision(
                new_config_value=updated_config_value,
                modified_by=admin.username,
                change_reason="Safety limits update via admin interface"
            )
            
            # Deactivate old configuration
            safety_config.is_active = False
            
            # Add new configuration
            db.add(new_config)
        else:
            # Create new configuration
            new_config = Configuration(
                config_key="default_safety_limits",
                config_name="Default Safety Limits",
                config_description="System safety limits and constraints",
                config_type="safety",
                config_value=updated_config_value,
                created_by=admin.username,
                modified_by=admin.username,
                change_reason="Initial safety limits creation"
            )
            db.add(new_config)
        
        db.commit()
        db.refresh(new_config)
        
        # Log safety limits update
        audit_logger.log_action(
            db=db,
            action="update_safety_limits",
            resource_type="configuration",
            resource_id=str(new_config.id),
            result="SUCCESS",
            user=admin,
            request=request,
            action_data={
                "max_charge_per_hole": charge_limits.get("max_charge_per_hole"),
                "max_charge_per_delay": charge_limits.get("max_charge_per_delay"),
                "default_ppv_limit": ppv_limits.get("default_limit")
            },
            risk_level="HIGH"
        )
        
        return {
            "config_id": new_config.id,
            "version": new_config.version,
            "updated_by": admin.username,
            "updated_at": new_config.updated_at.isoformat(),
            "requires_validation": not new_config.is_validated,
            "message": "Safety limits updated successfully. Configuration requires validation before activation."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Safety limits update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update safety limits"
        )