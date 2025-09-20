"""
Authentication service for user management and sign-off operations.
Implements requirements 4.4, 4.5, 4.7 for engineer sign-off and session management.
"""

import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.logging import get_logger
from ..repositories.blast_record import BlastRecordRepository
from .models import User, UserRole, Session, AuditLog
from .schemas import (
    UserCreate, UserUpdate, LoginRequest, EngineerSignoffRequest,
    EngineerSignoffResponse, TokenResponse, LoginResponse
)
from .security import (
    security_manager, get_password_hash, verify_password, 
    create_access_token, generate_session_token, generate_signoff_id,
    rate_limiter
)
from .audit import audit_logger

logger = get_logger(__name__)


class AuthService:
    """
    Authentication service for user management and operations.
    """
    
    def __init__(self):
        self.logger = logger
        self.audit_logger = audit_logger
    
    async def create_user(
        self,
        db: Session,
        user_data: UserCreate,
        created_by: Optional[User] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            user_data: User creation data
            created_by: User creating this user (for audit)
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If user creation fails
        """
        # Check if username or email already exists
        existing_user = db.query(User).filter(
            or_(User.username == user_data.username, User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            role=user_data.role,
            professional_license=user_data.professional_license,
            license_expiry=user_data.license_expiry,
            organization=user_data.organization,
            employee_id=user_data.employee_id,
            is_active=True,
            is_verified=False  # Requires admin verification
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Audit log
        self.audit_logger.log_action(
            db=db,
            action="create_user",
            resource_type="user",
            resource_id=str(user.id),
            result="SUCCESS",
            user=created_by,
            action_data={
                "created_user_id": user.id,
                "created_username": user.username,
                "created_role": user.role
            },
            risk_level="MEDIUM"
        )
        
        self.logger.info(
            "User created successfully",
            user_id=user.id,
            username=user.username,
            role=user.role,
            created_by=created_by.username if created_by else "system"
        )
        
        return user
    
    async def authenticate_user(
        self,
        db: Session,
        login_data: LoginRequest,
        request: Optional[Request] = None
    ) -> Tuple[User, Session]:
        """
        Authenticate user and create session.
        
        Args:
            db: Database session
            login_data: Login credentials
            request: FastAPI request object
            
        Returns:
            Tuple of (user, session)
            
        Raises:
            HTTPException: If authentication fails
        """
        # Rate limiting check
        client_ip = self._get_client_ip(request) if request else "unknown"
        if rate_limiter.is_rate_limited(login_data.username) or rate_limiter.is_rate_limited(client_ip):
            self.audit_logger.log_authentication(
                db=db,
                action="login_rate_limited",
                username=login_data.username,
                result="FAILURE",
                request=request,
                error_message="Rate limit exceeded"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later."
            )
        
        # Find user by username or email
        user = db.query(User).filter(
            or_(User.username == login_data.username, User.email == login_data.username)
        ).first()
        
        # Verify password
        if not user or not verify_password(login_data.password, user.hashed_password):
            # Record failed attempt
            rate_limiter.record_attempt(login_data.username)
            rate_limiter.record_attempt(client_ip)
            
            # Update failed login attempts
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                db.commit()
            
            self.audit_logger.log_authentication(
                db=db,
                action="login_failed",
                username=login_data.username,
                result="FAILURE",
                request=request,
                error_message="Invalid credentials",
                user=user
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Check if user is active
        if not user.is_active:
            self.audit_logger.log_authentication(
                db=db,
                action="login_inactive_user",
                username=login_data.username,
                result="FAILURE",
                request=request,
                error_message="User account is inactive",
                user=user
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Check if user is locked
        if user.is_locked:
            self.audit_logger.log_authentication(
                db=db,
                action="login_locked_user",
                username=login_data.username,
                result="FAILURE",
                request=request,
                error_message="User account is locked",
                user=user
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is locked. Please contact administrator."
            )
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        
        # Create session
        session_token = generate_session_token()
        session_expiry = datetime.utcnow() + timedelta(
            hours=24 if login_data.remember_me else 8
        )
        
        session = Session(
            session_token=session_token,
            user_id=user.id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent") if request else None,
            expires_at=session_expiry,
            is_admin_session=user.role == UserRole.ADMIN
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Audit log
        self.audit_logger.log_authentication(
            db=db,
            action="login_success",
            username=user.username,
            result="SUCCESS",
            request=request,
            user=user
        )
        
        self.logger.info(
            "User authenticated successfully",
            user_id=user.id,
            username=user.username,
            session_id=session.id
        )
        
        return user, session
    
    async def create_login_response(
        self,
        user: User,
        session: Session
    ) -> LoginResponse:
        """
        Create login response with token.
        
        Args:
            user: Authenticated user
            session: User session
            
        Returns:
            Login response
        """
        # Create access token
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "session_id": session.id
        }
        
        expires_delta = timedelta(hours=8)
        access_token = create_access_token(token_data, expires_delta)
        
        # Create response
        from .schemas import UserResponse, TokenResponse
        
        user_response = UserResponse(
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
        
        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds())
        )
        
        return LoginResponse(
            user=user_response,
            token=token_response,
            session_id=session.session_token
        )
    
    async def engineer_signoff(
        self,
        db: Session,
        engineer: User,
        signoff_data: EngineerSignoffRequest,
        request: Optional[Request] = None
    ) -> EngineerSignoffResponse:
        """
        Perform engineer sign-off on blast plan.
        
        Args:
            db: Database session
            engineer: Engineer performing sign-off
            signoff_data: Sign-off request data
            request: FastAPI request object
            
        Returns:
            Sign-off response
            
        Raises:
            HTTPException: If sign-off fails
        """
        # Verify engineer can sign-off
        if not engineer.can_sign_off:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Engineer is not authorized to sign-off blast plans"
            )
        
        # Verify engineer name confirmation (requirement 4.4)
        if signoff_data.engineer_name_confirmation.strip() != engineer.full_name.strip():
            self.audit_logger.log_engineer_signoff(
                db=db,
                user=engineer,
                blast_record_id=signoff_data.blast_record_id,
                signoff_data=signoff_data.dict(),
                result="FAILURE",
                request=request,
                error_message="Engineer name confirmation mismatch"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Engineer name confirmation does not match your profile"
            )
        
        # Get blast record
        blast_record_repo = BlastRecordRepository(db)
        blast_record = blast_record_repo.get_by_id(signoff_data.blast_record_id)
        if not blast_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blast record not found"
            )
        
        # Check if blast plan is valid for sign-off
        can_export, blocking_reasons = blast_record.can_be_exported()
        if not can_export and "Engineer sign-off required" not in blocking_reasons:
            # If there are other blocking reasons besides missing sign-off
            other_reasons = [r for r in blocking_reasons if r != "Engineer sign-off required"]
            if other_reasons:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Blast plan cannot be signed-off: {'; '.join(other_reasons)}"
                )
        
        # Create sign-off data
        signoff_timestamp = datetime.utcnow()
        signoff_id = generate_signoff_id()
        
        engineer_credentials = engineer.get_signoff_credentials()
        
        # Create digital signature
        signature_data = {
            "blast_record_id": signoff_data.blast_record_id,
            "engineer_id": engineer_credentials["engineer_id"],
            "certification_statement": signoff_data.certification_statement,
            "timestamp": signoff_timestamp.isoformat()
        }
        
        digital_signature = security_manager.create_digital_signature(
            signature_data, engineer.id, signoff_timestamp
        )
        
        # Update blast record with sign-off
        engineer_signoff_data = {
            "engineer_name": engineer.full_name,
            "engineer_id": engineer_credentials["engineer_id"],
            "signoff_timestamp": signoff_timestamp.isoformat(),
            "certification_statement": signoff_data.certification_statement,
            "digital_signature": digital_signature,
            "review_notes": signoff_data.review_notes,
            "conditions": signoff_data.conditions or [],
            "is_valid": True,
            "signoff_id": signoff_id
        }
        
        blast_record.engineer_signoff = engineer_signoff_data
        db.commit()
        
        # Create audit log
        audit_log = self.audit_logger.log_engineer_signoff(
            db=db,
            user=engineer,
            blast_record_id=signoff_data.blast_record_id,
            signoff_data=signoff_data.dict(),
            result="SUCCESS",
            request=request
        )
        
        self.logger.info(
            "Engineer sign-off completed",
            engineer_id=engineer.id,
            engineer_name=engineer.full_name,
            blast_record_id=signoff_data.blast_record_id,
            signoff_id=signoff_id
        )
        
        return EngineerSignoffResponse(
            signoff_id=signoff_id,
            blast_record_id=signoff_data.blast_record_id,
            engineer_name=engineer.full_name,
            engineer_id=engineer_credentials["engineer_id"],
            signoff_timestamp=signoff_timestamp,
            certification_statement=signoff_data.certification_statement,
            digital_signature=digital_signature,
            is_valid=True,
            audit_trail_id=audit_log.id
        )
    
    async def invalidate_session(
        self,
        db: Session,
        session_token: str,
        user: Optional[User] = None,
        request: Optional[Request] = None
    ) -> bool:
        """
        Invalidate a user session (logout).
        
        Args:
            db: Database session
            session_token: Session token to invalidate
            user: User logging out
            request: FastAPI request object
            
        Returns:
            True if session was invalidated
        """
        session = db.query(Session).filter(
            Session.session_token == session_token
        ).first()
        
        if session:
            session.invalidate()
            db.commit()
            
            # Audit log
            self.audit_logger.log_authentication(
                db=db,
                action="logout",
                username=user.username if user else "unknown",
                result="SUCCESS",
                request=request,
                user=user
            )
            
            return True
        
        return False
    
    async def verify_signoff_integrity(
        self,
        db: Session,
        blast_record_id: int
    ) -> bool:
        """
        Verify the integrity of an engineer sign-off.
        
        Args:
            db: Database session
            blast_record_id: Blast record ID
            
        Returns:
            True if sign-off is valid and intact
        """
        blast_record_repo = BlastRecordRepository(db)
        blast_record = blast_record_repo.get_by_id(blast_record_id)
        if not blast_record or not blast_record.engineer_signoff:
            return False
        
        signoff_data = blast_record.engineer_signoff
        
        # Find the engineer who signed off
        engineer_id = signoff_data.get("engineer_id")
        engineer = db.query(User).filter(
            or_(
                User.professional_license == engineer_id,
                User.employee_id == engineer_id,
                User.username == engineer_id
            )
        ).first()
        
        if not engineer:
            return False
        
        # Verify digital signature
        signature_timestamp = datetime.fromisoformat(
            signoff_data["signoff_timestamp"].replace("Z", "+00:00")
        )
        
        signature_data = {
            "blast_record_id": blast_record_id,
            "engineer_id": engineer_id,
            "certification_statement": signoff_data["certification_statement"],
            "timestamp": signature_timestamp.isoformat()
        }
        
        return security_manager.verify_digital_signature(
            signoff_data["digital_signature"],
            signature_data,
            engineer.id,
            signature_timestamp
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        if hasattr(request, "client") and request.client:
            return request.client.host
        return "unknown"


# Global auth service instance
auth_service = AuthService()