"""
Custom middleware for the FastAPI application.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..core.logging import get_logger
from ..core.database import get_db, create_audit_log_entry

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2)
            )
            
            # Re-raise exception to be handled by error handlers
            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for security headers and basic security measures.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers and perform basic security checks.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response with security headers
        """
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        
        # Add cache control for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling and audit logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle errors and create audit logs for critical operations.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response or error response
        """
        try:
            response = await call_next(request)
            
            # Log critical operations for audit trail
            if self._is_critical_operation(request):
                await self._log_critical_operation(request, response)
            
            return response
            
        except Exception as e:
            # Log error for audit trail
            await self._log_error_operation(request, e)
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "path": request.url.path
                }
            )
    
    def _is_critical_operation(self, request: Request) -> bool:
        """
        Determine if the request is a critical operation requiring audit logging.
        
        Args:
            request: HTTP request
            
        Returns:
            bool: True if critical operation
        """
        critical_paths = [
            "/api/v1/blast-plans",
            "/api/v1/safety/validate",
            "/api/v1/export",
            "/api/v1/signoff"
        ]
        
        return any(request.url.path.startswith(path) for path in critical_paths)
    
    async def _log_critical_operation(self, request: Request, response: Response) -> None:
        """
        Log critical operations for audit trail.
        
        Args:
            request: HTTP request
            response: HTTP response
        """
        try:
            # This would normally use dependency injection, but for middleware
            # we'll create a temporary session
            from ..core.database import db_manager
            
            db = db_manager.get_session()
            try:
                create_audit_log_entry(
                    db=db,
                    event_type="critical_operation",
                    event_data={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "request_id": getattr(request.state, "request_id", "unknown")
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Failed to create audit log entry", error=str(e))
    
    async def _log_error_operation(self, request: Request, error: Exception) -> None:
        """
        Log error operations for audit trail.
        
        Args:
            request: HTTP request
            error: Exception that occurred
        """
        try:
            from ..core.database import db_manager
            
            db = db_manager.get_session()
            try:
                create_audit_log_entry(
                    db=db,
                    event_type="error_operation",
                    event_data={
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(error),
                        "error_type": type(error).__name__,
                        "request_id": getattr(request.state, "request_id", "unknown")
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Failed to create error audit log entry", error=str(e))