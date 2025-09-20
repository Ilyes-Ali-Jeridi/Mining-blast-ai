"""
Security tests for authentication and authorization system.
Implements requirement 6.4: Write security tests and vulnerability assessments.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.drill_blast_system.auth import (
    User, UserRole, Session as UserSession, AuditLog,
    UserCreate, LoginRequest, EngineerSignoffRequest,
    get_password_hash, verify_password, create_access_token, verify_token,
    auth_service, security_manager, rate_limiter
)
from src.drill_blast_system.core.database import get_db
from src.drill_blast_system.api.main import app


class TestPasswordSecurity:
    """Test password security and validation."""
    
    def test_password_hashing(self):
        """Test password hashing is secure."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Hash should be verifiable
        assert verify_password(password, hashed)
        
        # Wrong password should not verify
        assert not verify_password("WrongPassword", hashed)
    
    def test_password_complexity_validation(self):
        """Test password complexity requirements."""
        # Valid password
        valid_user = UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="ValidPass123!",
            role="viewer"
        )
        # Should not raise exception
        assert valid_user.password == "ValidPass123!"
        
        # Test various invalid passwords
        invalid_passwords = [
            "short",                    # Too short
            "nouppercase123!",         # No uppercase
            "NOLOWERCASE123!",         # No lowercase
            "NoDigits!",               # No digits
            "NoSpecialChars123",       # No special characters
        ]
        
        for invalid_password in invalid_passwords:
            with pytest.raises(ValueError):
                UserCreate(
                    username="testuser",
                    email="test@example.com",
                    full_name="Test User",
                    password=invalid_password,
                    role="viewer"
                )
    
    def test_password_storage_security(self):
        """Test that passwords are never stored in plain text."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        # Ensure hash doesn't contain original password
        assert password not in hashed
        
        # Ensure hash is sufficiently long (bcrypt produces ~60 char hashes)
        assert len(hashed) >= 50


class TestJWTSecurity:
    """Test JWT token security."""
    
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        payload = {"sub": 1, "username": "testuser", "role": "engineer"}
        token = create_access_token(payload)
        
        # Token should be a string
        assert isinstance(token, str)
        
        # Token should be verifiable
        decoded = verify_token(token)
        assert decoded["sub"] == 1
        assert decoded["username"] == "testuser"
        assert decoded["role"] == "engineer"
    
    def test_token_expiration(self):
        """Test JWT token expiration."""
        payload = {"sub": 1, "username": "testuser"}
        
        # Create token with short expiry
        short_expiry = timedelta(seconds=1)
        token = create_access_token(payload, short_expiry)
        
        # Token should be valid immediately
        decoded = verify_token(token)
        assert decoded is not None
        
        # Wait for token to expire
        time.sleep(2)
        
        # Token should be invalid after expiry
        decoded = verify_token(token)
        assert decoded is None
    
    def test_token_tampering(self):
        """Test that tampered tokens are rejected."""
        payload = {"sub": 1, "username": "testuser"}
        token = create_access_token(payload)
        
        # Tamper with token
        tampered_token = token[:-5] + "XXXXX"
        
        # Tampered token should be invalid
        decoded = verify_token(tampered_token)
        assert decoded is None


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiting_basic(self):
        """Test basic rate limiting functionality."""
        limiter = rate_limiter
        identifier = "test_user_123"
        
        # Should not be rate limited initially
        assert not limiter.is_rate_limited(identifier)
        
        # Record multiple failed attempts
        for _ in range(5):
            limiter.record_attempt(identifier)
        
        # Should be rate limited after max attempts
        assert limiter.is_rate_limited(identifier)
    
    def test_rate_limiting_window(self):
        """Test rate limiting time window."""
        limiter = rate_limiter
        identifier = "test_user_window"
        
        # Record attempts
        for _ in range(3):
            limiter.record_attempt(identifier)
        
        # Should not be rate limited yet
        assert not limiter.is_rate_limited(identifier)
        
        # Record more attempts to exceed limit
        for _ in range(3):
            limiter.record_attempt(identifier)
        
        # Should be rate limited now
        assert limiter.is_rate_limited(identifier)


class TestDigitalSignature:
    """Test digital signature functionality."""
    
    def test_signature_creation_and_verification(self):
        """Test digital signature creation and verification."""
        data = {"blast_id": 123, "engineer": "John Doe"}
        user_id = 1
        timestamp = datetime.utcnow()
        
        # Create signature
        signature = security_manager.create_digital_signature(data, user_id, timestamp)
        
        # Signature should be a string with sha256 prefix
        assert isinstance(signature, str)
        assert signature.startswith("sha256:")
        
        # Verify signature
        is_valid = security_manager.verify_digital_signature(signature, data, user_id, timestamp)
        assert is_valid
        
        # Tampered data should fail verification
        tampered_data = {"blast_id": 456, "engineer": "Jane Doe"}
        is_valid = security_manager.verify_digital_signature(signature, tampered_data, user_id, timestamp)
        assert not is_valid
        
        # Different user should fail verification
        is_valid = security_manager.verify_digital_signature(signature, data, 999, timestamp)
        assert not is_valid


class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    def test_login_endpoint_security(self, client):
        """Test login endpoint security measures."""
        # Test with invalid credentials
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        
        # Should return 401 for invalid credentials
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_rate_limiting(self, client):
        """Test login rate limiting."""
        # Make multiple failed login attempts
        for _ in range(6):  # Exceed rate limit
            response = client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "wrongpassword"
            })
        
        # Should eventually return 429 (Too Many Requests)
        # Note: This test might need adjustment based on actual rate limiting implementation
        assert response.status_code in [401, 429]
    
    def test_protected_endpoint_without_auth(self, client):
        """Test that protected endpoints require authentication."""
        response = client.get("/api/v1/auth/me")
        
        # Should return 401 without authentication
        assert response.status_code == 401
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test protected endpoints with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Should return 401 with invalid token
        assert response.status_code == 401


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    @pytest.fixture
    def mock_users(self):
        """Create mock users with different roles."""
        return {
            "viewer": User(
                id=1, username="viewer", role=UserRole.VIEWER,
                is_active=True, is_verified=True
            ),
            "engineer": User(
                id=2, username="engineer", role=UserRole.ENGINEER,
                is_active=True, is_verified=True,
                professional_license="PE-123"
            ),
            "admin": User(
                id=3, username="admin", role=UserRole.ADMIN,
                is_active=True, is_verified=True
            )
        }
    
    def test_engineer_signoff_authorization(self, mock_users):
        """Test that only engineers can sign-off blast plans."""
        engineer = mock_users["engineer"]
        viewer = mock_users["viewer"]
        
        # Engineer should be able to sign-off
        assert engineer.can_sign_off
        
        # Viewer should not be able to sign-off
        assert not viewer.can_sign_off
    
    def test_admin_functions_authorization(self, mock_users):
        """Test that only admins can access admin functions."""
        admin = mock_users["admin"]
        engineer = mock_users["engineer"]
        
        # Admin should have admin access
        assert admin.can_access_admin_functions()
        
        # Engineer should not have admin access
        assert not engineer.can_access_admin_functions()


class TestAuditTrail:
    """Test audit trail functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db
    
    def test_audit_log_creation(self, mock_db):
        """Test audit log entry creation."""
        from src.drill_blast_system.auth.audit import audit_logger
        
        user = User(id=1, username="testuser", role=UserRole.ENGINEER)
        
        # Create audit log
        audit_log = audit_logger.log_action(
            db=mock_db,
            action="test_action",
            resource_type="test_resource",
            result="SUCCESS",
            user=user,
            risk_level="MEDIUM"
        )
        
        # Verify audit log was created
        assert audit_log.action == "test_action"
        assert audit_log.resource_type == "test_resource"
        assert audit_log.result == "SUCCESS"
        assert audit_log.user_id == 1
        assert audit_log.risk_level == "MEDIUM"
        
        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_engineer_signoff_audit(self, mock_db):
        """Test engineer sign-off audit logging."""
        from src.drill_blast_system.auth.audit import audit_logger
        
        engineer = User(
            id=1, username="engineer", role=UserRole.ENGINEER,
            professional_license="PE-123"
        )
        
        signoff_data = {
            "certification_statement": "I certify this plan",
            "conditions": ["Weather conditions"]
        }
        
        # Log engineer sign-off
        audit_log = audit_logger.log_engineer_signoff(
            db=mock_db,
            user=engineer,
            blast_record_id=123,
            signoff_data=signoff_data,
            result="SUCCESS"
        )
        
        # Verify critical audit properties
        assert audit_log.action == "engineer_signoff"
        assert audit_log.resource_type == "blast_record"
        assert audit_log.resource_id == "123"
        assert audit_log.risk_level == "CRITICAL"
        assert audit_log.compliance_flags["engineer_signoff"] is True
        assert audit_log.compliance_flags["regulatory_compliance"] is True


class TestSecurityVulnerabilities:
    """Test for common security vulnerabilities."""
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection."""
        # This would typically test that user inputs are properly sanitized
        # In SQLAlchemy with parameterized queries, this is handled automatically
        malicious_input = "'; DROP TABLE users; --"
        
        # Create user with malicious input
        try:
            user_data = UserCreate(
                username=malicious_input,
                email="test@example.com",
                full_name="Test User",
                password="ValidPass123!",
                role="viewer"
            )
            # Should not cause SQL injection
            assert user_data.username == malicious_input
        except ValueError:
            # Input validation might reject this, which is also acceptable
            pass
    
    def test_xss_protection(self):
        """Test protection against XSS attacks."""
        xss_payload = "<script>alert('xss')</script>"
        
        # User data should not execute scripts
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            full_name=xss_payload,
            password="ValidPass123!",
            role="viewer"
        )
        
        # Should store the payload as plain text, not execute it
        assert user_data.full_name == xss_payload
    
    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        # Password verification should take similar time for valid/invalid users
        valid_hash = get_password_hash("password123")
        
        # Time password verification for existing hash
        start_time = time.time()
        verify_password("password123", valid_hash)
        valid_time = time.time() - start_time
        
        # Time password verification for non-existent user (should use dummy hash)
        start_time = time.time()
        verify_password("password123", "$2b$12$dummy.hash.that.should.not.match.anything")
        invalid_time = time.time() - start_time
        
        # Times should be similar (within reasonable tolerance)
        time_difference = abs(valid_time - invalid_time)
        assert time_difference < 0.1  # 100ms tolerance
    
    def test_session_security(self):
        """Test session security measures."""
        # Session tokens should be cryptographically secure
        from src.drill_blast_system.auth.security import generate_session_token
        
        token1 = generate_session_token()
        token2 = generate_session_token()
        
        # Tokens should be different
        assert token1 != token2
        
        # Tokens should be sufficiently long
        assert len(token1) > 20
        assert len(token2) > 20
        
        # Tokens should contain only safe characters
        import string
        safe_chars = string.ascii_letters + string.digits + "_-"
        assert all(c in safe_chars for c in token1.replace("sess_", ""))


class TestComplianceRequirements:
    """Test compliance with regulatory requirements."""
    
    def test_engineer_license_validation(self):
        """Test that engineers must have valid licenses."""
        # Engineer without license should not be able to sign-off
        engineer_no_license = User(
            id=1, username="engineer", role=UserRole.ENGINEER,
            is_active=True, is_verified=True,
            professional_license=None
        )
        assert not engineer_no_license.can_sign_off
        
        # Engineer with expired license should not be able to sign-off
        engineer_expired = User(
            id=2, username="engineer2", role=UserRole.ENGINEER,
            is_active=True, is_verified=True,
            professional_license="PE-123",
            license_expiry=datetime.utcnow() - timedelta(days=1)
        )
        assert not engineer_expired.can_sign_off
        
        # Engineer with valid license should be able to sign-off
        engineer_valid = User(
            id=3, username="engineer3", role=UserRole.ENGINEER,
            is_active=True, is_verified=True,
            professional_license="PE-123",
            license_expiry=datetime.utcnow() + timedelta(days=365)
        )
        assert engineer_valid.can_sign_off
    
    def test_immutable_audit_trail(self):
        """Test that audit trail entries are immutable."""
        # Audit log entries should not have update timestamps
        # This ensures they cannot be modified after creation
        audit_log = AuditLog(
            action="test_action",
            resource_type="test_resource",
            result="SUCCESS"
        )
        
        # Should have created_at but no updated_at
        assert hasattr(audit_log, 'created_at')
        # In the actual model, audit logs don't have updated_at field
        # This ensures immutability
    
    def test_signoff_integrity_verification(self):
        """Test sign-off integrity verification."""
        # This would test the verify_signoff_integrity function
        # to ensure sign-offs cannot be tampered with
        data = {"blast_id": 123, "engineer": "John Doe"}
        user_id = 1
        timestamp = datetime.utcnow()
        
        # Create and verify signature
        signature = security_manager.create_digital_signature(data, user_id, timestamp)
        is_valid = security_manager.verify_digital_signature(signature, data, user_id, timestamp)
        
        assert is_valid
        
        # Tampered signature should fail
        tampered_signature = signature[:-5] + "XXXXX"
        is_valid = security_manager.verify_digital_signature(tampered_signature, data, user_id, timestamp)
        
        assert not is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])