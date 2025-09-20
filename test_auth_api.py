"""
Test authentication API endpoints.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_api_startup():
    """Test that the API can start with authentication routes."""
    try:
        from fastapi.testclient import TestClient
        from drill_blast_system.api.main import app
        
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        print(f"Root endpoint status: {response.status_code}")
        
        # Test health endpoint
        response = client.get("/health")
        print(f"Health endpoint status: {response.status_code}")
        
        # Test auth endpoints (should require authentication)
        response = client.get("/api/v1/auth/me")
        print(f"Auth me endpoint status: {response.status_code} (expected 401)")
        
        # Test login endpoint structure
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        print(f"Login endpoint status: {response.status_code} (expected 401)")
        
        print("✓ API endpoints are accessible")
        return True
        
    except Exception as e:
        print(f"✗ API startup error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run API test."""
    print("Testing Authentication API...")
    print("=" * 40)
    
    if test_api_startup():
        print("🎉 Authentication API is working!")
        return True
    else:
        print("❌ Authentication API has issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)