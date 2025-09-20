"""
Health check endpoints for monitoring and diagnostics.
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.database import get_db, db_manager
from ...core.config import get_settings
from ...core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Automated Drill-and-Blast System"
    }


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with database connectivity.
    
    Args:
        db: Database session
        
    Returns:
        dict: Detailed health status information
        
    Raises:
        HTTPException: If health check fails
    """
    settings = get_settings()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Automated Drill-and-Blast System",
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {}
    }
    
    # Check database connectivity
    try:
        # Simple query to test database connection
        db.execute("SELECT 1")
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "SQLite" if "sqlite" in settings.database.url else "PostgreSQL"
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check configuration
    try:
        # Validate critical configuration
        if settings.physics.default_rock_factor_a > 0:
            health_status["components"]["configuration"] = {
                "status": "healthy",
                "physics_defaults": "loaded"
            }
        else:
            raise ValueError("Invalid physics configuration")
    except Exception as e:
        logger.error("Configuration health check failed", error=str(e))
        health_status["status"] = "unhealthy"
        health_status["components"]["configuration"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness check for deployment orchestration.
    
    Args:
        db: Database session
        
    Returns:
        dict: Readiness status information
        
    Raises:
        HTTPException: If system is not ready
    """
    try:
        # Check if database tables exist
        from ...core.database import Base
        
        # Try to query a core table
        db.execute("SELECT COUNT(*) FROM system_configuration")
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "System is ready to accept requests"
        }
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "message": "System is not ready to accept requests"
            }
        )


@router.get("/live", response_model=Dict[str, Any])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for deployment orchestration.
    
    Returns:
        dict: Liveness status information
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "System is alive and responding"
    }