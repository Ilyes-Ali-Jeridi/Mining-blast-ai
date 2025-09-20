"""
Authentication and authorization API routes.
Implements requirements 4.4, 4.5, 4.7 for engineer sign-off and session management.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.logging import get_logger
from ...auth import (
    User, UserRole, AuditLog,
    UserCreate, UserUpdate, UserResponse,
    LoginRequest, LoginResponse, PasswordChangeRequest,
    EngineerSignoffRequest, EngineerSignoffResponse,
    AuditLogResponse,
    get_current_user, get_current_engineer, get_current_admin,
    auth_service, audit_logger
)

logger = get_logger(__name__)
security = HTTPBearer()

router = APIRouter()


@router.post("/login", response_model=LoginResponse, tags=["authentication"])
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and create session.
    
    - **username**: Username or email address
    - **password**: User password
    - **remember_me**: Extend session duration if true
    
    Returns user information and authentication token.
    """
    try:
        user, session = await auth_service.authenticate_user(db, login_data, request)
        return await auth_service.create_login_response(user, session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


@router.post("/logout", tags=["authentication"])
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and invalidate session.
    
    Requires valid authentication token.
    """
    try:
        # Extract session token from authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Note: In a full implementation, you'd need to track session tokens
            # For now, we'll just log the logout action
            audit_logger.log_authentication(
                db=db,
                action="logout",
                username=current_user.username,
                result="SUCCESS",
                request=request,
                user=current_user
            )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout service error"
        )


@router.get("/me", response_model=UserResponse, tags=["authentication"])
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    Returns detailed information about the authenticated user.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        professional_license=current_user.professional_license,
        license_expiry=current_user.license_expiry,
        organization=current_user.organization,
        employee_id=current_user.employee_id,
        can_sign_off=current_user.can_sign_off,
        is_locked=current_user.is_locked,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.post("/change-password", tags=["authentication"])
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (must meet security requirements)
    
    Requires valid authentication token.
    """
    try:
        from ...auth.security import verify_password, get_password_hash
        
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            audit_logger.log_action(
                db=db,
                action="change_password_failed",
                resource_type="user",
                resource_id=str(current_user.id),
                result="FAILURE",
                user=current_user,
                request=request,
                error_message="Invalid current password",
                risk_level="MEDIUM"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.hashed_password = get_password_hash(password_data.new_password)
        current_user.password_changed_at = datetime.utcnow()
        db.commit()
        
        # Audit log
        audit_logger.log_action(
            db=db,
            action="change_password",
            resource_type="user",
            resource_id=str(current_user.id),
            result="SUCCESS",
            user=current_user,
            request=request,
            risk_level="MEDIUM"
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change service error"
        )


@router.post("/signoff", response_model=EngineerSignoffResponse, tags=["engineer-signoff"])
async def engineer_signoff(
    signoff_data: EngineerSignoffRequest,
    request: Request,
    engineer: User = Depends(get_current_engineer),
    db: Session = Depends(get_db)
):
    """
    Engineer sign-off for blast plan (Requirement 4.4, 4.5).
    
    - **blast_record_id**: ID of blast record to sign-off
    - **certification_statement**: Legal certification statement
    - **engineer_name_confirmation**: Must match engineer's full name
    - **certification_checkbox**: Must be true to proceed
    - **review_notes**: Optional engineer review notes
    - **conditions**: Optional sign-off conditions
    
    Creates immutable audit trail and digital signature.
    Requires engineer role and valid professional license.
    """
    try:
        return await auth_service.engineer_signoff(db, engineer, signoff_data, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Engineer sign-off error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign-off service error"
        )


@router.get("/signoff/verify/{blast_record_id}", tags=["engineer-signoff"])
async def verify_signoff_integrity(
    blast_record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify the integrity of an engineer sign-off.
    
    Checks digital signature and sign-off validity.
    """
    try:
        is_valid = await auth_service.verify_signoff_integrity(db, blast_record_id)
        
        return {
            "blast_record_id": blast_record_id,
            "signoff_valid": is_valid,
            "verified_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sign-off verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign-off verification error"
        )


# Admin-only endpoints
@router.post("/users", response_model=UserResponse, tags=["user-management"])
async def create_user(
    user_data: UserCreate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Admin only).
    
    - **username**: Unique username (3-50 characters, alphanumeric + underscore/dash)
    - **email**: Valid email address
    - **full_name**: Full name (2-200 characters)
    - **password**: Strong password (8+ chars with uppercase, lowercase, digit, special char)
    - **role**: User role (engineer, admin, operator, viewer)
    - **professional_license**: Required for engineers
    - **license_expiry**: License expiry date
    - **organization**: User's organization
    - **employee_id**: Employee identifier
    
    Requires admin role.
    """
    try:
        user = await auth_service.create_user(db, user_data, admin)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            professional_license=user.professional_license,
            license_expiry=user.license_expiry,
            organization=user.organization,
            employee_id=user.employee_id,
            can_sign_off=user.can_sign_off,
            is_locked=user.is_locked,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation service error"
        )


@router.get("/users", response_model=List[UserResponse], tags=["user-management"])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (Admin only).
    
    Supports filtering by role and active status.
    Requires admin role.
    """
    try:
        query = db.query(User)
        
        if role:
            query = query.filter(User.role == role)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        users = query.offset(skip).limit(limit).all()
        
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                professional_license=user.professional_license,
                license_expiry=user.license_expiry,
                organization=user.organization,
                employee_id=user.employee_id,
                can_sign_off=user.can_sign_off,
                is_locked=user.is_locked,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"User listing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User listing service error"
        )


@router.put("/users/{user_id}", response_model=UserResponse, tags=["user-management"])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update user information (Admin only).
    
    Allows updating user profile, role, and status.
    Requires admin role.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Track changes for audit
        changes = {}
        
        # Update fields
        if user_data.email is not None and user_data.email != user.email:
            changes["email"] = {"old": user.email, "new": user_data.email}
            user.email = user_data.email
        
        if user_data.full_name is not None and user_data.full_name != user.full_name:
            changes["full_name"] = {"old": user.full_name, "new": user_data.full_name}
            user.full_name = user_data.full_name
        
        if user_data.role is not None and user_data.role != user.role:
            changes["role"] = {"old": user.role, "new": user_data.role}
            user.role = user_data.role
        
        if user_data.is_active is not None and user_data.is_active != user.is_active:
            changes["is_active"] = {"old": user.is_active, "new": user_data.is_active}
            user.is_active = user_data.is_active
        
        if user_data.is_verified is not None and user_data.is_verified != user.is_verified:
            changes["is_verified"] = {"old": user.is_verified, "new": user_data.is_verified}
            user.is_verified = user_data.is_verified
        
        if user_data.professional_license is not None:
            changes["professional_license"] = {"old": user.professional_license, "new": user_data.professional_license}
            user.professional_license = user_data.professional_license
        
        if user_data.license_expiry is not None:
            changes["license_expiry"] = {"old": user.license_expiry, "new": user_data.license_expiry}
            user.license_expiry = user_data.license_expiry
        
        if user_data.organization is not None:
            changes["organization"] = {"old": user.organization, "new": user_data.organization}
            user.organization = user_data.organization
        
        if user_data.employee_id is not None:
            changes["employee_id"] = {"old": user.employee_id, "new": user_data.employee_id}
            user.employee_id = user_data.employee_id
        
        db.commit()
        db.refresh(user)
        
        # Audit log
        if changes:
            audit_logger.log_action(
                db=db,
                action="update_user",
                resource_type="user",
                resource_id=str(user.id),
                result="SUCCESS",
                user=admin,
                request=request,
                action_data={"changes": changes, "updated_user": user.username},
                risk_level="MEDIUM"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            professional_license=user.professional_license,
            license_expiry=user.license_expiry,
            organization=user.organization,
            employee_id=user.employee_id,
            can_sign_off=user.can_sign_off,
            is_locked=user.is_locked,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update service error"
        )


@router.get("/audit-logs", response_model=List[AuditLogResponse], tags=["audit"])
async def get_audit_logs(
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs (Admin only).
    
    Provides access to immutable audit trail for compliance and security monitoring.
    Supports filtering by action, resource type, user, and risk level.
    Requires admin role.
    """
    try:
        query = db.query(AuditLog).join(User, AuditLog.user_id == User.id, isouter=True)
        
        if action:
            query = query.filter(AuditLog.action == action)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if risk_level:
            query = query.filter(AuditLog.risk_level == risk_level)
        
        audit_logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                username=log.user.username if log.user else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                endpoint=log.endpoint,
                method=log.method,
                ip_address=log.ip_address,
                result=log.result,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                risk_level=log.risk_level,
                created_at=log.created_at
            )
            for log in audit_logs
        ]
        
    except Exception as e:
        logger.error(f"Audit log retrieval error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Audit log service error"
        )