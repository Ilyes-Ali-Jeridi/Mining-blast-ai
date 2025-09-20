"""
Integration tests for authentication and authorization system.
Tests the complete authentication flow and API integration.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.drill_blast_system.core.database import Base, get_db
from src.drill_blast_system.api.main import app
from src.drill_blast_system.auth import User, UserRole, auth_service
from src.drill_blast_system.auth.security import get_password_hash


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create database session for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_users(db_session):
    """Create test users."""
    users = {}
    
    # Create admin user
    admin = User(
        username="admin_test",
        email="admin@test.com",
        full_name="Test Administrator",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True
    )
    db_session.add(admin)
    
    # Create engineer user
    engineer = User(
        username="engineer_test",
        email="engineer@test.com",
        full_name="Dr. Test Engineer, P.Eng",
        hashed_password=get_password_hash("EngineerPass123!"),
        role=UserRole.ENGINEER,
        is_active=True,
        is_verified=True,
        professional_license="PE-TEST-123",
        license_expiry=datetime.utcnow() + timedelta(days=365),
        organization="Test Mining Corp"
    )
    db_session.add(engineer)
    
    # Create viewer user
    viewer = User(
        username="viewer_test",
        email="viewer@test.com",
        full_name="Test Viewer",
        hashed_password=get_password_hash("ViewerPass123!"),
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True
    )
    db_session.add(viewer)
    
    db_session.commit()
    
    users["admin"] = admin
    users["engineer"] = engineer
    users["viewer"] = viewer
    
    return users


class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    def test_successful_login(self, client, test_users, setup_database):
        """Test successful user login."""
        response = client.post("/api/v1/auth/login", json={
            "username": "engineer_test",
            "password": "EngineerPass123!",
            "remember_me": False
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "user" in data
        assert "token" in data
        assert "session_id" in data
        
        # Check user data
        user_data = data["user"]
        assert user_data["username"] == "engineer_test"
        assert user_data["role"] == "engineer"
        assert user_data["can_sign_off"] is True
        
        # Check token data
        token_data = data["token"]
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert "expires_in" in token_data
    
    def test_failed_login_invalid_credentials(self, client, test_users, setup_database):
        """Test login with invalid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "username": "engineer_test",
            "password": "WrongPassword",
            "remember_me": False
        })
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_get_current_user_info(self, client, test_users, setup_database):
        """Test getting current user information."""
        # First login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "engineer_test",
            "password": "EngineerPass123!"
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["token"]["access_token"]
        
        # Get user info with token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        user_data = response.json()
        
        assert user_data["username"] == "engineer_test"
        assert user_data["role"] == "engineer"
        assert user_data["can_sign_off"] is True


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def get_auth_headers(self, client, username, password):
        """Helper to get authentication headers."""
        login_response = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["token"]["access_token"]
            return {"Authorization": f"Bearer {token}"}
        return None
    
    def test_admin_can_create_users(self, client, test_users, setup_database):
        """Test that admin can create users."""
        headers = self.get_auth_headers(client, "admin_test", "AdminPass123!")
        
        response = client.post(
            "/api/v1/auth/users",
            headers=headers,
            json={
                "username": "new_user",
                "email": "newuser@test.com",
                "full_name": "New User",
                "password": "NewUserPass123!",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "new_user"
        assert user_data["role"] == "viewer"
    
    def test_non_admin_cannot_create_users(self, client, test_users, setup_database):
        """Test that non-admin cannot create users."""
        headers = self.get_auth_headers(client, "engineer_test", "EngineerPass123!")
        
        response = client.post(
            "/api/v1/auth/users",
            headers=headers,
            json={
                "username": "new_user",
                "email": "newuser@test.com",
                "full_name": "New User",
                "password": "NewUserPass123!",
                "role": "viewer"
            }
        )
        
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])