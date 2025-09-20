"""
Test script for ML Pipeline API endpoints.
"""

import requests
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

BASE_URL = "http://localhost:8000/api/v1"

def test_ml_pipeline_endpoints():
    """Test ML pipeline API endpoints"""
    
    print("Testing ML Pipeline API Endpoints...")
    
    # Test analyzer status
    print("\n1. Testing analyzer status...")
    try:
        response = requests.get(f"{BASE_URL}/ml/analyzer-status")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test residual learning status
    print("\n2. Testing residual learning status...")
    try:
        response = requests.get(f"{BASE_URL}/ml/residual-learning/status")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test residual learning prediction
    print("\n3. Testing residual learning prediction...")
    try:
        params = {
            "burden_m": 3.0,
            "spacing_m": 3.5,
            "bench_height_m": 12.0,
            "hole_diameter_mm": 165.0,
            "stemming_length_m": 3.0,
            "powder_factor_kg_per_t": 0.5,
            "powder_factor_kg_per_m3": 1.35,
            "rock_density_kg_m3": 2700.0,
            "explosive_rws": 100.0,
            "explosive_density_kg_m3": 1200.0,
            "prediction_type": "fragmentation"
        }
        
        response = requests.post(f"{BASE_URL}/ml/residual-learning/predict", params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test model diagnostics
    print("\n4. Testing model diagnostics...")
    try:
        response = requests.get(f"{BASE_URL}/ml/residual-learning/diagnostics")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.get('data', {}).keys())}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nML Pipeline API test completed!")

if __name__ == "__main__":
    test_ml_pipeline_endpoints()