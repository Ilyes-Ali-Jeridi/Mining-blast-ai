"""
Basic test to verify authentication system implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_auth_imports():
    """Test that all authentication modules can be imported."""
    try:
        from drill_blast_system.auth import (
            User, UserRole, Session, AuditLog,
            UserCreate, UserUpdate, UserResponse,
            LoginRequest, LoginResponse, TokenResponse,
            EngineerSignoffRequest, EngineerSignoffResponse,
            get_password_hash, verify_password,
            create_access_token, verify_token,
            auth_service, audit_logger
        )
        print("✓ All authentication modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_password_hashing():
    """Test password hashing functionality."""
    try:
        from drill_blast_system.auth.security import get_password_hash, verify_password
        
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Verify password works
        assert verify_password(password, hashed), "Password verification failed"
        
        # Wrong password should fail
        assert not verify_password("WrongPassword", hashed), "Wrong password should not verify"
        
        print("✓ Password hashing works correctly")
        return True
    except Exception as e:
        print(f"✗ Password hashing error: {e}")
        return False

def test_jwt_tokens():
    """Test JWT token creation and verification."""
    try:
        from drill_blast_system.auth.security import create_access_token, verify_token
        
        payload = {"sub": "1", "username": "testuser", "role": "engineer"}
        token = create_access_token(payload)
        
        # Verify token
        decoded = verify_token(token)
        assert decoded is not None, "Token verification failed"
        assert decoded["sub"] == "1", "Token payload incorrect"
        assert decoded["username"] == "testuser", "Token username incorrect"
        
        print("✓ JWT tokens work correctly")
        return True
    except Exception as e:
        print(f"✗ JWT token error: {e}")
        return False

def test_user_model():
    """Test User model functionality."""
    try:
        from drill_blast_system.auth.models import User, UserRole
        from datetime import datetime, timedelta
        
        # Create engineer user
        engineer = User(
            id=1,
            username="engineer_test",
            email="engineer@test.com",
            full_name="Dr. Test Engineer, P.Eng",
            hashed_password="dummy_hash",
            role=UserRole.ENGINEER,
            is_active=True,
            is_verified=True,
            professional_license="PE-123",
            license_expiry=datetime.utcnow() + timedelta(days=365)
        )
        
        # Test properties
        assert engineer.is_engineer, "Engineer role check failed"
        assert engineer.can_sign_off, "Engineer sign-off check failed"
        assert not engineer.is_locked, "Engineer lock check failed"
        
        # Test credentials
        credentials = engineer.get_signoff_credentials()
        assert credentials["engineer_name"] == "Dr. Test Engineer, P.Eng"
        assert credentials["engineer_id"] == "PE-123"
        
        print("✓ User model works correctly")
        return True
    except Exception as e:
        print(f"✗ User model error: {e}")
        return False

def test_digital_signature():
    """Test digital signature functionality."""
    try:
        from drill_blast_system.auth.security import security_manager
        from datetime import datetime
        
        data = {"blast_id": 123, "engineer": "John Doe"}
        user_id = 1
        timestamp = datetime.utcnow()
        
        # Create signature
        signature = security_manager.create_digital_signature(data, user_id, timestamp)
        assert signature.startswith("sha256:"), "Signature format incorrect"
        
        # Verify signature
        is_valid = security_manager.verify_digital_signature(signature, data, user_id, timestamp)
        assert is_valid, "Signature verification failed"
        
        # Tampered data should fail
        tampered_data = {"blast_id": 456, "engineer": "Jane Doe"}
        is_valid = security_manager.verify_digital_signature(signature, tampered_data, user_id, timestamp)
        assert not is_valid, "Tampered signature should fail"
        
        print("✓ Digital signatures work correctly")
        return True
    except Exception as e:
        print(f"✗ Digital signature error: {e}")
        return False

def main():
    """Run all basic tests."""
    print("Testing Authentication System Implementation...")
    print("=" * 50)
    
    tests = [
        test_auth_imports,
        test_password_hashing,
        test_jwt_tokens,
        test_user_model,
        test_digital_signature
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All authentication tests passed!")
        return True
    else:
        print("❌ Some authentication tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)