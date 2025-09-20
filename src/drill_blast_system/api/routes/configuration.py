"""
Configuration management API endpoints.
Implements requirement 8.4: Configuration management endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db, SystemConfiguration
from ...core.logging import get_logger
from ...physics_models.config import PhysicsConfig
from ...safety.config import SafetyConfig

router = APIRouter()
logger = get_logger(__name__)


class ConfigurationCreateRequest(BaseModel):
    """Configuration creation request schema."""
    config_key: str
    config_value: Dict[str, Any]
    config_type: str
    description: Optional[str] = None


class ConfigurationUpdateRequest(BaseModel):
    """Configuration update request schema."""
    config_value: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ConfigurationResponse(BaseModel):
    """Configuration response schema."""
    id: int
    config_key: str
    config_value: Dict[str, Any]
    config_type: str
    description: Optional[str]
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class PhysicsConfigResponse(BaseModel):
    """Physics configuration response schema."""
    kuz_ram: Dict[str, Any]
    ppv: Dict[str, Any]
    fragmentation: Dict[str, Any]


class ExplosiveResponse(BaseModel):
    """Explosive configuration response schema."""
    name: str
    type: str
    density: float
    rws: float
    vod: float
    energy: float
    cost_per_kg: float
    regulatory_limit_per_hole: float
    regulatory_limit_per_delay: float
    is_available: bool


@router.get("/", response_model=List[ConfigurationResponse])
async def list_configurations(
    config_type: Optional[str] = Query(None, description="Filter by configuration type"),
    active_only: bool = Query(True, description="Return only active configurations"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
) -> List[ConfigurationResponse]:
    """
    List system configurations.
    
    Args:
        config_type: Optional filter by configuration type
        active_only: Return only active configurations
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of configurations
    """
    try:
        query = db.query(SystemConfiguration)
        
        if config_type:
            query = query.filter(SystemConfiguration.config_type == config_type)
        
        if active_only:
            query = query.filter(SystemConfiguration.is_active == True)
        
        configurations = query.offset(skip).limit(limit).all()
        
        logger.debug(
            "Configurations retrieved",
            count=len(configurations),
            config_type=config_type,
            active_only=active_only
        )
        
        return [
            ConfigurationResponse(
                id=config.id,
                config_key=config.config_key,
                config_value=config.config_value,
                config_type=config.config_type,
                description=config.description,
                version=config.version,
                is_active=config.is_active,
                created_at=config.created_at.isoformat(),
                updated_at=config.updated_at.isoformat()
            )
            for config in configurations
        ]
        
    except Exception as e:
        logger.error("Failed to list configurations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations"
        )


@router.get("/{config_key}", response_model=ConfigurationResponse)
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
        Configuration data
        
    Raises:
        HTTPException: If configuration not found
    """
    try:
        config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == config_key,
            SystemConfiguration.is_active == True
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_key}' not found"
            )
        
        logger.debug("Configuration retrieved", config_key=config_key)
        
        return ConfigurationResponse(
            id=config.id,
            config_key=config.config_key,
            config_value=config.config_value,
            config_type=config.config_type,
            description=config.description,
            version=config.version,
            is_active=config.is_active,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get configuration",
            config_key=config_key,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.post("/", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    config_data: ConfigurationCreateRequest,
    db: Session = Depends(get_db)
) -> ConfigurationResponse:
    """
    Create a new configuration.
    
    Args:
        config_data: Configuration creation data
        db: Database session
        
    Returns:
        Created configuration data
        
    Raises:
        HTTPException: If configuration creation fails
    """
    try:
        # Check if configuration key already exists
        existing_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == config_data.config_key,
            SystemConfiguration.is_active == True
        ).first()
        
        if existing_config:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Configuration '{config_data.config_key}' already exists"
            )
        
        # Create new configuration
        new_config = SystemConfiguration(
            config_key=config_data.config_key,
            config_value=config_data.config_value,
            config_type=config_data.config_type,
            description=config_data.description,
            version=1,
            is_active=True
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        logger.info(
            "Configuration created",
            config_key=config_data.config_key,
            config_type=config_data.config_type
        )
        
        return ConfigurationResponse(
            id=new_config.id,
            config_key=new_config.config_key,
            config_value=new_config.config_value,
            config_type=new_config.config_type,
            description=new_config.description,
            version=new_config.version,
            is_active=new_config.is_active,
            created_at=new_config.created_at.isoformat(),
            updated_at=new_config.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to create configuration",
            config_key=config_data.config_key,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )


@router.put("/{config_key}", response_model=ConfigurationResponse)
async def update_configuration(
    config_key: str,
    config_data: ConfigurationUpdateRequest,
    db: Session = Depends(get_db)
) -> ConfigurationResponse:
    """
    Update a configuration.
    
    Args:
        config_key: Configuration key
        config_data: Configuration update data
        db: Database session
        
    Returns:
        Updated configuration data
        
    Raises:
        HTTPException: If configuration not found or update fails
    """
    try:
        # Get existing configuration
        existing_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == config_key,
            SystemConfiguration.is_active == True
        ).first()
        
        if not existing_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_key}' not found"
            )
        
        # Update configuration
        if config_data.config_value is not None:
            existing_config.config_value = config_data.config_value
            existing_config.version += 1
        
        if config_data.description is not None:
            existing_config.description = config_data.description
        
        if config_data.is_active is not None:
            existing_config.is_active = config_data.is_active
        
        db.commit()
        db.refresh(existing_config)
        
        logger.info(
            "Configuration updated",
            config_key=config_key,
            version=existing_config.version
        )
        
        return ConfigurationResponse(
            id=existing_config.id,
            config_key=existing_config.config_key,
            config_value=existing_config.config_value,
            config_type=existing_config.config_type,
            description=existing_config.description,
            version=existing_config.version,
            is_active=existing_config.is_active,
            created_at=existing_config.created_at.isoformat(),
            updated_at=existing_config.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to update configuration",
            config_key=config_key,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.delete("/{config_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    config_key: str,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a configuration (soft delete by deactivating).
    
    Args:
        config_key: Configuration key
        db: Database session
        
    Raises:
        HTTPException: If configuration not found or deletion fails
    """
    try:
        # Get existing configuration
        existing_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == config_key,
            SystemConfiguration.is_active == True
        ).first()
        
        if not existing_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration '{config_key}' not found"
            )
        
        # Soft delete by deactivating
        existing_config.is_active = False
        db.commit()
        
        logger.info("Configuration deactivated", config_key=config_key)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Failed to delete configuration",
            config_key=config_key,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )


@router.get("/physics/defaults", response_model=PhysicsConfigResponse)
async def get_physics_defaults(
    db: Session = Depends(get_db)
) -> PhysicsConfigResponse:
    """
    Get default physics model parameters.
    
    Args:
        db: Database session
        
    Returns:
        Default physics parameters
    """
    try:
        # Get physics configuration from database
        physics_config_db = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "default_physics_parameters",
            SystemConfiguration.is_active == True
        ).first()
        
        if physics_config_db:
            physics_params = physics_config_db.config_value
        else:
            # Use default physics configuration
            physics_config = PhysicsConfig()
            physics_params = {
                "kuz_ram": {
                    "default_rock_factor_a": physics_config.default_rock_factor_a,
                    "default_uniformity_index": physics_config.default_uniformity_index
                },
                "ppv": {
                    "default_ppv_k": physics_config.default_ppv_k,
                    "default_ppv_a": physics_config.default_ppv_a,
                    "default_ppv_b": physics_config.default_ppv_b
                },
                "fragmentation": {
                    "distribution_type": "rosin_rammler",
                    "min_fragment_size": 1.0,
                    "max_fragment_size": 1000.0
                }
            }
        
        logger.debug("Physics defaults retrieved", params=physics_params)
        
        return PhysicsConfigResponse(
            kuz_ram=physics_params.get("kuz_ram", {}),
            ppv=physics_params.get("ppv", {}),
            fragmentation=physics_params.get("fragmentation", {})
        )
        
    except Exception as e:
        logger.error("Failed to get physics defaults", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve physics defaults"
        )


@router.put("/physics/defaults", response_model=PhysicsConfigResponse)
async def update_physics_defaults(
    physics_params: PhysicsConfigResponse,
    db: Session = Depends(get_db)
) -> PhysicsConfigResponse:
    """
    Update default physics model parameters.
    
    Args:
        physics_params: Updated physics parameters
        db: Database session
        
    Returns:
        Updated physics parameters
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Get existing physics configuration
        physics_config_db = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "default_physics_parameters",
            SystemConfiguration.is_active == True
        ).first()
        
        physics_dict = {
            "kuz_ram": physics_params.kuz_ram,
            "ppv": physics_params.ppv,
            "fragmentation": physics_params.fragmentation
        }
        
        if physics_config_db:
            # Update existing configuration
            physics_config_db.config_value = physics_dict
            physics_config_db.version += 1
        else:
            # Create new configuration
            physics_config_db = SystemConfiguration(
                config_key="default_physics_parameters",
                config_value=physics_dict,
                config_type="physics",
                description="Default physics model parameters",
                version=1,
                is_active=True
            )
            db.add(physics_config_db)
        
        db.commit()
        
        logger.info("Physics defaults updated", params=physics_dict)
        
        return physics_params
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to update physics defaults", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update physics defaults"
        )


@router.get("/explosives", response_model=List[ExplosiveResponse])
async def get_explosives_catalog(
    available_only: bool = Query(True, description="Return only available explosives"),
    db: Session = Depends(get_db)
) -> List[ExplosiveResponse]:
    """
    Get explosives catalog.
    
    Args:
        available_only: Return only available explosives
        db: Database session
        
    Returns:
        List of explosives
    """
    try:
        # Get explosives configuration from database
        explosives_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "explosives_catalog",
            SystemConfiguration.is_active == True
        ).first()
        
        if explosives_config and "explosives" in explosives_config.config_value:
            explosives_list = explosives_config.config_value["explosives"]
        else:
            # Default explosives catalog
            explosives_list = [
                {
                    "name": "Standard ANFO",
                    "type": "ANFO",
                    "density": 850.0,
                    "rws": 100.0,
                    "vod": 4500.0,
                    "energy": 3.7,
                    "cost_per_kg": 1.50,
                    "regulatory_limit_per_hole": 50.0,
                    "regulatory_limit_per_delay": 200.0,
                    "is_available": True
                },
                {
                    "name": "Heavy ANFO",
                    "type": "ANFO",
                    "density": 1200.0,
                    "rws": 110.0,
                    "vod": 5000.0,
                    "energy": 4.2,
                    "cost_per_kg": 2.00,
                    "regulatory_limit_per_hole": 45.0,
                    "regulatory_limit_per_delay": 180.0,
                    "is_available": True
                }
            ]
        
        # Filter by availability if requested
        if available_only:
            explosives_list = [e for e in explosives_list if e.get("is_available", True)]
        
        logger.debug(
            "Explosives catalog retrieved",
            count=len(explosives_list),
            available_only=available_only
        )
        
        return [ExplosiveResponse(**explosive) for explosive in explosives_list]
        
    except Exception as e:
        logger.error("Failed to get explosives catalog", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve explosives catalog"
        )


@router.put("/explosives", response_model=List[ExplosiveResponse])
async def update_explosives_catalog(
    explosives: List[ExplosiveResponse],
    db: Session = Depends(get_db)
) -> List[ExplosiveResponse]:
    """
    Update explosives catalog.
    
    Args:
        explosives: Updated explosives list
        db: Database session
        
    Returns:
        Updated explosives catalog
        
    Raises:
        HTTPException: If update fails
    """
    try:
        # Get existing explosives configuration
        explosives_config = db.query(SystemConfiguration).filter(
            SystemConfiguration.config_key == "explosives_catalog",
            SystemConfiguration.is_active == True
        ).first()
        
        explosives_dict = {
            "explosives": [explosive.dict() for explosive in explosives]
        }
        
        if explosives_config:
            # Update existing configuration
            explosives_config.config_value = explosives_dict
            explosives_config.version += 1
        else:
            # Create new configuration
            explosives_config = SystemConfiguration(
                config_key="explosives_catalog",
                config_value=explosives_dict,
                config_type="explosives",
                description="System explosives catalog",
                version=1,
                is_active=True
            )
            db.add(explosives_config)
        
        db.commit()
        
        logger.info(
            "Explosives catalog updated",
            explosive_count=len(explosives)
        )
        
        return explosives
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to update explosives catalog", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update explosives catalog"
        )