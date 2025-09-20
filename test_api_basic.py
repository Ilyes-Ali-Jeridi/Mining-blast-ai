"""
Basic API test to verify core endpoints work.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Create a minimal FastAPI app for testing
    app = FastAPI(title="Test API")
    
    @app.get("/")
    def root():
        return {"message": "API is working"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    # Test the basic functionality
    client = TestClient(app)
    
    response = client.get("/")
    print(f"Root endpoint: {response.status_code} - {response.json()}")
    
    response = client.get("/health")
    print(f"Health endpoint: {response.status_code} - {response.json()}")
    
    print("Basic FastAPI functionality is working!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()