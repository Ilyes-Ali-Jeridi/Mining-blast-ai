"""
Security utilities for authentication and authorization.
Implements requirements 4.4, 4.5, 4.7 for secure sign-off and session management.
"""

import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.database import get_db
from .models import User, UserRole, Session as UserSession, AuditLog


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

# Settings
settings = get_settings()


class SecurityManager:
    """
    Central security manager for authentication and authorization.
    """
    
    def __init__(self):
        self.pwd_context = pwd_context
        self.secret_key = settings.security.secret_key
        self.algorithm = settings.security.algorithm
        self.access_token_expire_hours = settings.security.access_token_expire_hours
    
    def get_password_hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiry time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.access_token_expire_hours)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def create_digital_signature(
        self, 
        data: Dict[str, Any], 
        user_id: int,
        timestamp: datetime
    ) -> str:
        """
        Create a digital signature for engineer sign-off.
        
        Args:
            data: Data to sign
            user_id: User ID
            timestamp: Signature timestamp
            
        Returns:
            Digital signature hash
        """
        # Create signature data (without including secret key directly)
        signature_data = {
            "data": data,
            "user_id": user_id,
            "timestamp": timestamp.isoformat(),
        }
        
        # Create hash using HMAC for better security
        import hmac
        signature_string = str(signature_data)
        signature_hash = hmac.new(
            self.secret_key.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"hmac-sha256:{signature_hash}"
    
    def verify_digital_signature(
        self,
        signature: str,
        data: Dict[str, Any],
        user_id: int,
        timestamp: datetime
    ) -> bool:
        """
        Verify a digital signature.
        
        Args:
            signature: Digital signature to verify
            data: Original data
            user_id: User ID
            timestamp: Original timestamp
            
        Returns:
            True if signature is valid
        """
        expected_signature = self.create_digital_signature(data, user_id, timestamp)
        return signature == expected_signature


# Global security manager instance
security_manager = SecurityManager()


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return security_manager.get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password."""
    return security_manager.verify_password(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create an access token."""
    return security_manager.create_access_token(data, expires_delta)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a token."""
    return security_manager.verify_token(token)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        # Get user ID from token
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Check if user is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is locked"
            )
        
        # Update last activity (optional - could be done in middleware)
        # This would require session management
        
        return user
        
    except JWTError:
        raise credentials_exception


def require_role(required_role: UserRole):
    """
    Decorator to require a specific user role.
    
    Args:
        required_role: Required user role
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (should be injected by dependency)
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            if "current_user" in kwargs:
                current_user = kwargs["current_user"]
            
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check role
            if current_user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role}' required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_engineer():
    """Decorator to require engineer role."""
    return require_role(UserRole.ENGINEER)


def require_admin():
    """Decorator to require admin role."""
    return require_role(UserRole.ADMIN)


async def get_current_engineer(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify engineer role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user (verified as engineer)
        
    Raises:
        HTTPException: If user is not an engineer
    """
    if current_user.role != UserRole.ENGINEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineer role required"
        )
    
    if not current_user.can_sign_off:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineer is not authorized to sign-off blast plans. Check license status."
        )
    
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user (verified as admin)
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    return current_user


def generate_session_token() -> str:
    """
    Generate a secure session token.
    
    Returns:
        Session token string
    """
    return f"sess_{secrets.token_urlsafe(32)}"


def generate_signoff_id() -> str:
    """
    Generate a unique sign-off identifier.
    
    Returns:
        Sign-off ID string
    """
    return f"signoff_{secrets.token_urlsafe(16)}"


class RateLimiter:
    """
    Simple rate limiter for authentication endpoints.
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        self.attempts = {}  # In production, use Redis or database
    
    def is_rate_limited(self, identifier: str) -> bool:
        """
        Check if identifier is rate limited.
        
        Args:
            identifier: IP address or username
            
        Returns:
            True if rate limited
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                attempt for attempt in self.attempts[identifier]
                if attempt > window_start
            ]
        
        # Check current attempts
        current_attempts = len(self.attempts.get(identifier, []))
        return current_attempts >= self.max_attempts
    
    def record_attempt(self, identifier: str) -> None:
        """
        Record a failed attempt.
        
        Args:
            identifier: IP address or username
        """
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        self.attempts[identifier].append(now)


# Global rate limiter instance
rate_limiter = RateLimiter()