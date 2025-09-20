"""
FastAPI application with basic routing and middleware.
Implements requirement 10.1: FastAPI application with basic routing and middleware.
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ..core.config import get_settings
from ..core.logging import setup_logging, get_logger, ErrorHandler
from ..core.database import init_database, db_manager
from .routes import health, system, sites, blast_plans, safety, configuration, optimization, exports, auth, ml_pipeline, simulations, admin, synthetic, measurement_data
from .middleware import LoggingMiddleware, SecurityMiddleware, ErrorHandlingMiddleware
from .websocket import websocket_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)
error_handler = ErrorHandler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Automated Drill-and-Blast System...")
    
    try:
        # Initialize database (skip if SKIP_DB_INIT is set)
        if not os.getenv('SKIP_DB_INIT'):
            init_database()
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization skipped (SKIP_DB_INIT=true)")
        
        # Log startup completion
        logger.info(
            "Application startup completed",
            app_name=app.title,
            version=app.version
        )
        
        yield
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        # Close database connections
        db_manager.close()
        
        logger.info("Application shutdown completed")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A comprehensive, production-grade solution for generating complete, safety-validated drill-and-blast plans for mining operations.",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    setup_middleware(app, settings)
    
    # Add routes
    setup_routes(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    return app


def setup_middleware(app: FastAPI, settings) -> None:
    """
    Configure application middleware.
    
    Args:
        app: FastAPI application instance
        settings: Application settings
    """
    # Security middleware (must be first)
    app.add_middleware(SecurityMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=settings.api.cors_credentials,
        allow_methods=settings.api.cors_methods,
        allow_headers=settings.api.cors_headers,
    )
    
    # Trusted host middleware
    if settings.is_production():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.mining.com"]
        )
    
    # Custom middleware
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)


def setup_routes(app: FastAPI) -> None:
    """
    Configure application routes.
    
    Args:
        app: FastAPI application instance
    """
    # Include route modules
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
    app.include_router(sites.router, prefix="/api/v1/sites", tags=["sites"])
    app.include_router(blast_plans.router, prefix="/api/v1/blast-plans", tags=["blast-plans"])
    app.include_router(optimization.router, prefix="/api/v1/optimization", tags=["optimization"])
    app.include_router(safety.router, prefix="/api/v1/safety", tags=["safety"])
    app.include_router(configuration.router, prefix="/api/v1/config", tags=["configuration"])
    app.include_router(exports.router, prefix="/api/v1/exports", tags=["exports"])
    app.include_router(ml_pipeline.router, prefix="/api/v1/ml", tags=["ml-pipeline"])
    app.include_router(measurement_data.router, prefix="/api/v1", tags=["measurement-data"])
    app.include_router(simulations.router, prefix="/api/v1", tags=["simulations"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(synthetic.router, prefix="/api/v1/synthetic", tags=["synthetic"])
    
    # Include WebSocket routes
    app.include_router(websocket_router, prefix="/api/v1", tags=["websockets"])
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> Dict[str, str]:
        """Root endpoint with basic application information."""
        settings = get_settings()
        return {
            "message": "Automated Drill-and-Blast System API",
            "version": settings.app_version,
            "status": "operational",
            "docs_url": "/docs" if settings.debug else "disabled"
        }


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            "HTTP exception occurred",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Exception",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors."""
        error_response = error_handler.handle_physics_model_error(
            model_name="validation",
            parameters={"request_path": request.url.path},
            error=exc
        )
        
        return JSONResponse(
            status_code=400,
            content=error_response
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(
            "Unhandled exception occurred",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "path": request.url.path,
                "error_id": f"{type(exc).__name__}_{hash(str(exc))}"
            }
        )


# Create application instance
app = create_app()


def run_server() -> None:
    """
    Run the FastAPI server.
    """
    settings = get_settings()
    
    uvicorn.run(
        "drill_blast_system.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload and settings.is_development(),
        workers=settings.api.workers if settings.is_production() else 1,
        log_level=settings.api.log_level,
        access_log=True
    )


if __name__ == "__main__":
    run_server()