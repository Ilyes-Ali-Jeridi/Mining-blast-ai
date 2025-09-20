"""
System configuration and administration endpoints.
"""

from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db, SystemConfiguration
from ...core.config import get_settings
from ...core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class ConfigurationResponse(BaseModel):
    """Response model for configuration data."""
    config_key: str
    config_value: Dict[str, Any]
    config_type: str
    description: str
    version: int
    is_active: str
    created_at: datetime
    updated_at: datetime


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    app_name: str
    app_version: str
    environment: str
    debug: bool
    database_type: str
    features_enabled: Dict[str, bool]


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info() -> SystemInfoResponse:
    """
    Get system information and configuration.
    
    Returns:
        SystemInfoResponse: System information
    """
    settings = get_settings()
    
    return SystemInfoResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
        database_type="PostgreSQL (Supabase)",
        features_enabled={
            "engineer_signoff": settings.security.require_engineer_signoff,
            "audit_trail": settings.security.audit_trail_enabled,
            "optimization_enabled": True,
            "safety_validation": True,
            "report_generation": True
        }
    )


@router.get("/config", response_model=List[ConfigurationResponse])
async def get_configurations(
    config_type: str = Query(None, description="Filter by configuration type"),
    active_only: bool = Query(True, description="Return only active configurations"),
    db: Session = Depends(get_db)
) -> List[ConfigurationResponse]:
    """
    Get system configurations.
    
    Args:
        config_type: Optional filter by configuration type
        active_only: Return only active configurations
        db: Database session
        
    Returns:
        List[ConfigurationResponse]: List of configurations
    """
    query = db.query(SystemConfiguration)
    
    if config_type:
        query = query.filter(SystemConfiguration.config_type == config_type)
    
    if active_only:
        query = query.filter(SystemConfiguration.is_active == True)
    
    configurations = query.all()
    
    return [
        ConfigurationResponse(
            config_key=config.config_key,
            config_value=config.config_value,
            config_type=config.config_type,
            description=config.description or "",
            version=config.version,
            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        for config in configurations
    ]


@router.get("/config/{config_key}", response_model=ConfigurationResponse)
async def get_configuration(
    config_key: str,
    db: Session = Depends(get_db)
) -> ConfigurationResponse:
    """
    Get a specific configuration by key.
    
    Args:
        config_key: Configuration key
        db: Database session
        
    Returns:
        ConfigurationResponse: Configuration data
        
    Raises:
        HTTPException: If configuration not found
    """
    config = db.query(SystemConfiguration).filter(
        SystemConfiguration.config_key == config_key,
        SystemConfiguration.is_active == True
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Configuration '{config_key}' not found"
        )
    
    return ConfigurationResponse(
        config_key=config.config_key,
        config_value=config.config_value,
        config_type=config.config_type,
        description=config.description or "",
        version=config.version,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/defaults", response_model=Dict[str, Any])
async def get_default_parameters(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get default physics and safety parameters.
    
    Args:
        db: Database session
        
    Returns:
        dict: Default parameters
    """
    settings = get_settings()
    
    # Get physics defaults from database
    physics_config = db.query(SystemConfiguration).filter(
        SystemConfiguration.config_key == "default_physics_parameters",
        SystemConfiguration.is_active == True
    ).first()
    
    # Get safety defaults from database
    safety_config = db.query(SystemConfiguration).filter(
        SystemConfiguration.config_key == "default_safety_limits",
        SystemConfiguration.is_active == True
    ).first()
    
    defaults = {
        "physics": physics_config.config_value if physics_config else {
            "kuz_ram": {
                "rock_factor_a": settings.physics.default_rock_factor_a,
                "uniformity_index": 1.25
            },
            "ppv": {
                "k": settings.physics.default_ppv_k,
                "a": settings.physics.default_ppv_a,
                "b": settings.physics.default_ppv_b
            }
        },
        "safety": safety_config.config_value if safety_config else {
            "max_charge_per_hole": settings.physics.default_max_charge_per_hole,
            "max_charge_per_delay": settings.physics.default_max_charge_per_delay,
            "ppv_default_limit": settings.physics.default_ppv_limit
        },
        "optimization": {
            "cp_sat_timeout": settings.optimization.cp_sat_timeout_seconds,
            "scipy_timeout": settings.optimization.scipy_timeout_seconds,
            "default_algorithms": settings.optimization.default_algorithms
        }
    }
    
    return defaults


@router.get("/status", response_model=Dict[str, Any])
async def get_system_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current system status and metrics.
    
    Args:
        db: Database session
        
    Returns:
        dict: System status information
    """
    try:
        # Get database statistics
        audit_count = db.execute("SELECT COUNT(*) FROM audit_log").scalar()
        config_count = db.execute("SELECT COUNT(*) FROM system_configuration").scalar()
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": True,
                "audit_entries": audit_count,
                "configurations": config_count
            },
            "services": {
                "api": "running",
                "optimization": "available",
                "safety_validation": "available",
                "report_generation": "available"
            },
            "uptime_seconds": 0  # Would be calculated from startup time
        }
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve system status"
        )