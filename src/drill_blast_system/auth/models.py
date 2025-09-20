"""
Authentication and authorization models.
Implements requirements 4.4, 4.5, 4.7 for user management and audit trails.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.database import BaseModel


class UserRole(str, Enum):
    """User role enumeration."""
    ENGINEER = "engineer"           # Mining engineer - can create and sign-off blast plans
    ADMIN = "admin"                # System administrator - can manage configurations
    OPERATOR = "operator"          # Blast operator - can view and execute approved plans
    VIEWER = "viewer"              # Read-only access to plans and reports


class User(BaseModel):
    """
    User model for authentication and authorization.
    
    Stores user credentials, roles, and professional information
    required for engineer sign-off validation.
    """
    __tablename__ = "users"
    
    # Basic user information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False, index=True)
    
    # Professional credentials (required for engineer sign-off)
    professional_license = Column(String(100), nullable=True)  # P.Eng, PE, etc.
    license_expiry = Column(DateTime, nullable=True)
    organization = Column(String(200), nullable=True)
    employee_id = Column(String(50), nullable=True)
    
    # Security settings
    password_changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    # Two-factor authentication (future enhancement)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    @hybrid_property
    def is_engineer(self) -> bool:
        """Check if user has engineer role."""
        return self.role == UserRole.ENGINEER
    
    @hybrid_property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    @hybrid_property
    def can_sign_off(self) -> bool:
        """Check if user can sign-off blast plans."""
        return (
            self.is_active and 
            self.is_verified and
            self.role == UserRole.ENGINEER and
            self.professional_license is not None and
            (self.license_expiry is None or self.license_expiry > datetime.utcnow())
        )
    
    @hybrid_property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        return (
            self.locked_until is not None and 
            self.locked_until > datetime.utcnow()
        )
    
    def can_access_admin_functions(self) -> bool:
        """Check if user can access admin functions."""
        return self.is_active and self.is_verified and self.role == UserRole.ADMIN
    
    def get_signoff_credentials(self) -> Dict[str, Any]:
        """
        Get credentials for engineer sign-off.
        
        Returns:
            Dict containing sign-off credentials
        """
        return {
            "engineer_name": self.full_name,
            "engineer_id": self.professional_license or self.employee_id or self.username,
            "license_number": self.professional_license,
            "organization": self.organization,
            "license_expiry": self.license_expiry.isoformat() if self.license_expiry else None
        }
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Session(BaseModel):
    """
    User session model for session management.
    
    Tracks active user sessions for security and audit purposes.
    """
    __tablename__ = "sessions"
    
    # Session identification
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)
    
    # Session lifecycle
    expires_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Security flags
    is_admin_session = Column(Boolean, default=False, nullable=False)
    requires_2fa = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired
    
    def extend_session(self, hours: int = 8) -> None:
        """
        Extend session expiry time.
        
        Args:
            hours: Number of hours to extend
        """
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity_at = datetime.utcnow()
    
    def invalidate(self) -> None:
        """Invalidate the session."""
        self.is_active = False
    
    def __repr__(self) -> str:
        """String representation of the session."""
        return f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class AuditLog(BaseModel):
    """
    Audit log model for tracking all authenticated actions.
    
    Provides immutable audit trail for regulatory compliance
    and security monitoring.
    """
    __tablename__ = "audit_logs"
    
    # User and session information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Nullable for system actions
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True, index=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # create_blast, sign_off, export, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # blast_plan, configuration, etc.
    resource_id = Column(String(100), nullable=True, index=True)  # ID of affected resource
    
    # Request details
    endpoint = Column(String(200), nullable=True)
    method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Action metadata
    action_data = Column(JSON, nullable=True)  # Additional action-specific data
    result = Column(String(20), nullable=False, index=True)  # SUCCESS, FAILURE, ERROR
    error_message = Column(Text, nullable=True)
    
    # Timing
    duration_ms = Column(Integer, nullable=True)  # Action duration in milliseconds
    
    # Security and compliance
    risk_level = Column(String(20), default="LOW", nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    compliance_flags = Column(JSON, nullable=True)  # Regulatory compliance markers
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    @classmethod
    def create_log(
        cls,
        action: str,
        resource_type: str,
        result: str = "SUCCESS",
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        risk_level: str = "LOW",
        compliance_flags: Optional[Dict[str, Any]] = None
    ) -> 'AuditLog':
        """
        Create a new audit log entry.
        
        Args:
            action: Action performed
            resource_type: Type of resource affected
            result: Action result (SUCCESS, FAILURE, ERROR)
            user_id: User ID (optional for system actions)
            session_id: Session ID
            resource_id: ID of affected resource
            endpoint: API endpoint
            method: HTTP method
            ip_address: Client IP address
            user_agent: Client user agent
            action_data: Additional action data
            error_message: Error message if failed
            duration_ms: Action duration
            risk_level: Security risk level
            compliance_flags: Compliance markers
            
        Returns:
            New AuditLog instance
        """
        return cls(
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            action_data=action_data,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            risk_level=risk_level,
            compliance_flags=compliance_flags
        )
    
    def __repr__(self) -> str:
        """String representation of the audit log."""
        return f"<AuditLog(id={self.id}, action='{self.action}', result='{self.result}')>"