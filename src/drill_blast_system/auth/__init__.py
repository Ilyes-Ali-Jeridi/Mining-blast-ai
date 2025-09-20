"""
Authentication and authorization module for the drill-and-blast system.
Implements requirements 4.4, 4.5, 4.7 for engineer sign-off and audit trails.
"""

from .models import User, UserRole, Session, AuditLog
from .schemas import (
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, LoginResponse, TokenResponse,
    PasswordChangeRequest,
    EngineerSignoffRequest, EngineerSignoffResponse,
    AuditLogResponse
)
from .security import (
    SecurityManager, 
    get_password_hash, 
    verify_password,
    create_access_token,
    verify_token,
    get_current_user,
    get_current_engineer,
    get_current_admin,
    require_role
)
from .service import AuthService, auth_service
from .audit import AuditLogger, audit_logger

__all__ = [
    # Models
    "User",
    "UserRole", 
    "Session",
    "AuditLog",
    
    # Schemas
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "PasswordChangeRequest",
    "EngineerSignoffRequest",
    "EngineerSignoffResponse",
    "AuditLogResponse",
    
    # Security
    "SecurityManager",
    "get_password_hash",
    "verify_password", 
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_engineer",
    "get_current_admin",
    "require_role",
    
    # Services
    "AuthService",
    "auth_service",
    "AuditLogger",
    "audit_logger"
]