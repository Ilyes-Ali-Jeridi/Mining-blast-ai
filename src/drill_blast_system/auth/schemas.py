"""
Authentication and authorization Pydantic schemas.
Implements requirements 4.4, 4.5, 4.7 for sign-off validation and audit trails.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator

from .models import UserRole


class UserRoleEnum(str, Enum):
    """User role enumeration for validation."""
    ENGINEER = "engineer"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserCreate(BaseModel):
    """User creation validation schema."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$', description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., min_length=2, max_length=200, description="Full name")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    role: UserRoleEnum = Field(UserRoleEnum.VIEWER, description="User role")
    
    # Professional credentials
    professional_license: Optional[str] = Field(None, max_length=100, description="Professional license number")
    license_expiry: Optional[datetime] = Field(None, description="License expiry date")
    organization: Optional[str] = Field(None, max_length=200, description="Organization")
    employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v)
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError('Password must contain at least one uppercase letter, lowercase letter, digit, and special character')
        
        return v
    
    @validator('professional_license')
    def validate_license_for_engineer(cls, v, values):
        """Validate that engineers have professional license."""
        if values.get('role') == UserRoleEnum.ENGINEER and not v:
            raise ValueError('Engineers must have a professional license number')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "username": "jsmith_eng",
                "email": "jane.smith@mining.com",
                "full_name": "Dr. Jane Smith, P.Eng",
                "password": "SecurePass123!",
                "role": "engineer",
                "professional_license": "PE-12345",
                "license_expiry": "2025-12-31T23:59:59Z",
                "organization": "Mining Corp Ltd",
                "employee_id": "EMP-001"
            }
        }


class UserUpdate(BaseModel):
    """User update validation schema."""
    email: Optional[EmailStr] = Field(None, description="Email address")
    full_name: Optional[str] = Field(None, min_length=2, max_length=200, description="Full name")
    role: Optional[UserRoleEnum] = Field(None, description="User role")
    is_active: Optional[bool] = Field(None, description="Active status")
    is_verified: Optional[bool] = Field(None, description="Verified status")
    
    # Professional credentials
    professional_license: Optional[str] = Field(None, max_length=100, description="Professional license number")
    license_expiry: Optional[datetime] = Field(None, description="License expiry date")
    organization: Optional[str] = Field(None, max_length=200, description="Organization")
    employee_id: Optional[str] = Field(None, max_length=50, description="Employee ID")


class UserResponse(BaseModel):
    """User response validation schema."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    role: UserRoleEnum = Field(..., description="User role")
    is_active: bool = Field(..., description="Active status")
    is_verified: bool = Field(..., description="Verified status")
    
    # Professional credentials
    professional_license: Optional[str] = Field(None, description="Professional license number")
    license_expiry: Optional[datetime] = Field(None, description="License expiry date")
    organization: Optional[str] = Field(None, description="Organization")
    employee_id: Optional[str] = Field(None, description="Employee ID")
    
    # Computed properties
    can_sign_off: bool = Field(..., description="Can sign-off blast plans")
    is_locked: bool = Field(..., description="Account locked status")
    
    # Audit information
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "username": "jsmith_eng",
                "email": "jane.smith@mining.com",
                "full_name": "Dr. Jane Smith, P.Eng",
                "role": "engineer",
                "is_active": True,
                "is_verified": True,
                "professional_license": "PE-12345",
                "license_expiry": "2025-12-31T23:59:59Z",
                "organization": "Mining Corp Ltd",
                "employee_id": "EMP-001",
                "can_sign_off": True,
                "is_locked": False,
                "last_login_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class LoginRequest(BaseModel):
    """Login request validation schema."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember login for extended session")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "jsmith_eng",
                "password": "SecurePass123!",
                "remember_me": False
            }
        }


class TokenResponse(BaseModel):
    """Token response validation schema."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 28800
            }
        }


class LoginResponse(BaseModel):
    """Login response validation schema."""
    user: UserResponse = Field(..., description="User information")
    token: TokenResponse = Field(..., description="Authentication token")
    session_id: str = Field(..., description="Session identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "username": "jsmith_eng",
                    "email": "jane.smith@mining.com",
                    "full_name": "Dr. Jane Smith, P.Eng",
                    "role": "engineer",
                    "can_sign_off": True
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 28800
                },
                "session_id": "sess_abc123def456"
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request validation schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase, lowercase, digit, and special character
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v)
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError('Password must contain at least one uppercase letter, lowercase letter, digit, and special character')
        
        return v


class EngineerSignoffRequest(BaseModel):
    """Engineer sign-off request validation schema."""
    blast_record_id: int = Field(..., gt=0, description="Blast record ID to sign-off")
    certification_statement: str = Field(..., min_length=10, description="Legal certification statement")
    review_notes: Optional[str] = Field(None, description="Engineer review notes")
    conditions: Optional[List[str]] = Field(None, description="Sign-off conditions")
    
    # Confirmation fields (requirement 4.4)
    engineer_name_confirmation: str = Field(..., description="Engineer name confirmation (must match user)")
    certification_checkbox: bool = Field(..., description="Certification checkbox confirmation")
    
    @validator('certification_checkbox')
    def validate_certification(cls, v):
        """Validate certification checkbox is checked."""
        if not v:
            raise ValueError('Certification checkbox must be checked to proceed with sign-off')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "blast_record_id": 123,
                "certification_statement": "I certify that this blast plan complies with all applicable safety regulations and professional standards.",
                "review_notes": "Plan reviewed and approved with standard safety margins. All calculations verified.",
                "conditions": ["Execute only in dry weather conditions", "Notify all personnel 30 minutes before blast"],
                "engineer_name_confirmation": "Dr. Jane Smith, P.Eng",
                "certification_checkbox": True
            }
        }


class EngineerSignoffResponse(BaseModel):
    """Engineer sign-off response validation schema."""
    signoff_id: str = Field(..., description="Sign-off identifier")
    blast_record_id: int = Field(..., description="Blast record ID")
    engineer_name: str = Field(..., description="Engineer name")
    engineer_id: str = Field(..., description="Engineer ID or license number")
    signoff_timestamp: datetime = Field(..., description="Sign-off timestamp")
    certification_statement: str = Field(..., description="Legal certification statement")
    digital_signature: str = Field(..., description="Digital signature hash")
    is_valid: bool = Field(..., description="Sign-off validity")
    audit_trail_id: int = Field(..., description="Audit trail entry ID")
    
    class Config:
        schema_extra = {
            "example": {
                "signoff_id": "signoff_abc123def456",
                "blast_record_id": 123,
                "engineer_name": "Dr. Jane Smith, P.Eng",
                "engineer_id": "PE-12345",
                "signoff_timestamp": "2024-01-15T15:30:00Z",
                "certification_statement": "I certify that this blast plan complies with all applicable safety regulations and professional standards.",
                "digital_signature": "sha256:abc123def456...",
                "is_valid": True,
                "audit_trail_id": 789
            }
        }


class AuditLogResponse(BaseModel):
    """Audit log response validation schema."""
    id: int = Field(..., description="Audit log ID")
    user_id: Optional[int] = Field(None, description="User ID")
    username: Optional[str] = Field(None, description="Username")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: Optional[str] = Field(None, description="HTTP method")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    result: str = Field(..., description="Action result")
    error_message: Optional[str] = Field(None, description="Error message")
    duration_ms: Optional[int] = Field(None, description="Action duration in milliseconds")
    risk_level: str = Field(..., description="Security risk level")
    created_at: datetime = Field(..., description="Log timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "username": "jsmith_eng",
                "action": "sign_off_blast",
                "resource_type": "blast_record",
                "resource_id": "123",
                "endpoint": "/api/v1/auth/signoff",
                "method": "POST",
                "ip_address": "192.168.1.100",
                "result": "SUCCESS",
                "duration_ms": 250,
                "risk_level": "HIGH",
                "created_at": "2024-01-15T15:30:00Z"
            }
        }


class SessionResponse(BaseModel):
    """Session response validation schema."""
    id: int = Field(..., description="Session ID")
    session_token: str = Field(..., description="Session token")
    user_id: int = Field(..., description="User ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    expires_at: datetime = Field(..., description="Session expiry")
    last_activity_at: datetime = Field(..., description="Last activity")
    is_active: bool = Field(..., description="Session active status")
    is_admin_session: bool = Field(..., description="Admin session flag")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "session_token": "sess_abc123def456",
                "user_id": 1,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "expires_at": "2024-01-16T15:30:00Z",
                "last_activity_at": "2024-01-15T15:30:00Z",
                "is_active": True,
                "is_admin_session": False
            }
        }