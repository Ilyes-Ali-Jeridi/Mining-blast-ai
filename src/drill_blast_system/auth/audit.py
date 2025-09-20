"""
Audit logging utilities for tracking authenticated actions.
Implements requirements 4.5, 4.7 for immutable audit trails.
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.logging import get_logger
from .models import User, AuditLog, Session

logger = get_logger(__name__)


class AuditLogger:
    """
    Audit logger for tracking all authenticated actions.
    
    Provides immutable audit trail for regulatory compliance
    and security monitoring.
    """
    
    def __init__(self):
        self.logger = logger
    
    def log_action(
        self,
        db: Session,
        action: str,
        resource_type: str,
        result: str = "SUCCESS",
        user: Optional[User] = None,
        session_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
        action_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        risk_level: str = "LOW",
        compliance_flags: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log an authenticated action.
        
        Args:
            db: Database session
            action: Action performed
            resource_type: Type of resource affected
            result: Action result (SUCCESS, FAILURE, ERROR)
            user: User performing action
            session_id: Session ID
            resource_id: ID of affected resource
            request: FastAPI request object
            action_data: Additional action data
            error_message: Error message if failed
            duration_ms: Action duration
            risk_level: Security risk level
            compliance_flags: Compliance markers
            
        Returns:
            Created audit log entry
        """
        # Extract request information
        endpoint = None
        method = None
        ip_address = None
        user_agent = None
        
        if request:
            endpoint = str(request.url.path)
            method = request.method
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")
        
        # Create audit log entry
        audit_log = AuditLog.create_log(
            action=action,
            resource_type=resource_type,
            result=result,
            user_id=user.id if user else None,
            session_id=session_id,
            resource_id=resource_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            action_data=action_data,
            error_message=error_message,
            duration_ms=duration_ms,
            risk_level=risk_level,
            compliance_flags=compliance_flags
        )
        
        # Save to database
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        # Log to application logger
        self.logger.info(
            f"Audit: {action}",
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            risk_level=risk_level,
            duration_ms=duration_ms
        )
        
        return audit_log
    
    def log_authentication(
        self,
        db: Session,
        action: str,
        username: str,
        result: str,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        user: Optional[User] = None
    ) -> AuditLog:
        """
        Log authentication-related actions.
        
        Args:
            db: Database session
            action: Authentication action (login, logout, failed_login, etc.)
            username: Username attempted
            result: Action result
            request: FastAPI request object
            error_message: Error message if failed
            user: User object if successful
            
        Returns:
            Created audit log entry
        """
        risk_level = "MEDIUM" if result == "SUCCESS" else "HIGH"
        
        action_data = {
            "username": username,
            "authentication_method": "password"
        }
        
        return self.log_action(
            db=db,
            action=action,
            resource_type="authentication",
            result=result,
            user=user,
            request=request,
            action_data=action_data,
            error_message=error_message,
            risk_level=risk_level,
            compliance_flags={"authentication": True}
        )
    
    def log_engineer_signoff(
        self,
        db: Session,
        user: User,
        blast_record_id: int,
        signoff_data: Dict[str, Any],
        result: str = "SUCCESS",
        request: Optional[Request] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log engineer sign-off actions (high-risk compliance action).
        
        Args:
            db: Database session
            user: Engineer performing sign-off
            blast_record_id: Blast record ID
            signoff_data: Sign-off data
            result: Action result
            request: FastAPI request object
            error_message: Error message if failed
            
        Returns:
            Created audit log entry
        """
        action_data = {
            "blast_record_id": blast_record_id,
            "engineer_license": user.professional_license,
            "signoff_timestamp": datetime.utcnow().isoformat(),
            "certification_statement": signoff_data.get("certification_statement"),
            "conditions": signoff_data.get("conditions", [])
        }
        
        compliance_flags = {
            "engineer_signoff": True,
            "regulatory_compliance": True,
            "safety_critical": True,
            "immutable_record": True
        }
        
        return self.log_action(
            db=db,
            action="engineer_signoff",
            resource_type="blast_record",
            resource_id=str(blast_record_id),
            result=result,
            user=user,
            request=request,
            action_data=action_data,
            error_message=error_message,
            risk_level="CRITICAL",
            compliance_flags=compliance_flags
        )
    
    def log_export_action(
        self,
        db: Session,
        user: User,
        blast_record_id: int,
        export_format: str,
        result: str = "SUCCESS",
        request: Optional[Request] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log blast plan export actions.
        
        Args:
            db: Database session
            user: User performing export
            blast_record_id: Blast record ID
            export_format: Export format (PDF, CSV, etc.)
            result: Action result
            request: FastAPI request object
            error_message: Error message if failed
            
        Returns:
            Created audit log entry
        """
        action_data = {
            "blast_record_id": blast_record_id,
            "export_format": export_format,
            "export_timestamp": datetime.utcnow().isoformat()
        }
        
        compliance_flags = {
            "data_export": True,
            "blast_plan_distribution": True
        }
        
        return self.log_action(
            db=db,
            action="export_blast_plan",
            resource_type="blast_record",
            resource_id=str(blast_record_id),
            result=result,
            user=user,
            request=request,
            action_data=action_data,
            error_message=error_message,
            risk_level="HIGH",
            compliance_flags=compliance_flags
        )
    
    def log_configuration_change(
        self,
        db: Session,
        user: User,
        config_type: str,
        config_id: str,
        changes: Dict[str, Any],
        result: str = "SUCCESS",
        request: Optional[Request] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log configuration changes (admin actions).
        
        Args:
            db: Database session
            user: Admin user making changes
            config_type: Type of configuration
            config_id: Configuration ID
            changes: Configuration changes made
            result: Action result
            request: FastAPI request object
            error_message: Error message if failed
            
        Returns:
            Created audit log entry
        """
        action_data = {
            "config_type": config_type,
            "config_id": config_id,
            "changes": changes,
            "change_timestamp": datetime.utcnow().isoformat()
        }
        
        compliance_flags = {
            "configuration_change": True,
            "admin_action": True,
            "system_modification": True
        }
        
        return self.log_action(
            db=db,
            action="modify_configuration",
            resource_type="configuration",
            resource_id=config_id,
            result=result,
            user=user,
            request=request,
            action_data=action_data,
            error_message=error_message,
            risk_level="HIGH",
            compliance_flags=compliance_flags
        )
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    @asynccontextmanager
    async def audit_context(
        self,
        db: Session,
        action: str,
        resource_type: str,
        user: Optional[User] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
        risk_level: str = "LOW"
    ):
        """
        Context manager for auditing actions with timing.
        
        Args:
            db: Database session
            action: Action being performed
            resource_type: Type of resource
            user: User performing action
            resource_id: Resource ID
            request: FastAPI request object
            risk_level: Security risk level
            
        Yields:
            Dictionary to store action data
        """
        start_time = time.time()
        action_data = {}
        result = "SUCCESS"
        error_message = None
        
        try:
            yield action_data
            
        except Exception as e:
            result = "ERROR"
            error_message = str(e)
            raise
            
        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log the action
            self.log_action(
                db=db,
                action=action,
                resource_type=resource_type,
                result=result,
                user=user,
                resource_id=resource_id,
                request=request,
                action_data=action_data,
                error_message=error_message,
                duration_ms=duration_ms,
                risk_level=risk_level
            )


# Global audit logger instance
audit_logger = AuditLogger()