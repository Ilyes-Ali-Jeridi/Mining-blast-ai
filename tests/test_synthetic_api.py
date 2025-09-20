"""
Tests for synthetic data API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.drill_blast_system.api.main import app

client = TestClient(app)


class TestSyntheticAPI:
    """Test synthetic data API endpoints"""
    
    def test_get_rock_types(self):
        """Test getting available rock types"""
        response = client.get("/api/v1/synthetic/rock-types")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "rock_types" in data["data"]
        assert len(data["data"]["rock_types"]) > 0
        
        # Check rock type structure
        rock_type = data["data"]["rock_types"][0]
        assert "value" in rock_type
        assert "name" in rock_type
        assert "ucs" in rock_type
        assert "density" in rock_type
        assert "rock_factor_a" in rock_type
        assert "description" in rock_type
    
    def test_get_explosive_types(self):
        """Test getting available explosive types"""
        response = client.get("/api/v1/synthetic/explosive-types")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "explosive_types" in data["data"]
        assert len(data["data"]["explosive_types"]) > 0
        
        # Check explosive type structure
        explosive_type = data["data"]["explosive_types"][0]
        assert "value" in explosive_type
        assert "name" in explosive_type
        assert "density" in explosive_type
        assert "rws" in explosive_type
        assert "vod" in explosive_type
        assert "cost_per_kg" in explosive_type
        assert "description" in explosive_type
    
    @pytest.mark.skip(reason="Requires authentication - implement when auth is ready")
    def test_generate_scenario(self):
        """Test generating a single synthetic scenario"""
        response = client.post(
            "/api/v1/synthetic/scenarios/generate",
            params={"noise_level": 0.15}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "scenario_id" in data["data"]
        assert "site" in data["data"]
        assert "blast_plan" in data["data"]
        assert "predictions" in data["data"]
        assert "measurements" in data["data"]
    
    @pytest.mark.skip(reason="Requires authentication - implement when auth is ready")
    def test_parameter_exploration(self):
        """Test parameter space exploration"""
        response = client.post(
            "/api/v1/synthetic/parameter-exploration",
            params={"num_scenarios": 10}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "scenarios" in data["data"]
        assert "statistics" in data["data"]
        assert len(data["data"]["scenarios"]) == 10
    
    @pytest.mark.skip(reason="Requires authentication - implement when auth is ready")
    def test_benchmark_models(self):
        """Test model benchmarking"""
        response = client.post(
            "/api/v1/synthetic/benchmark-models",
            params={
                "num_test_scenarios": 20,
                "models_to_test": ["kuz_ram_default"]
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "benchmark_results" in data["data"]
        assert "kuz_ram_default" in data["data"]["benchmark_results"]
        
        # Check benchmark metrics
        metrics = data["data"]["benchmark_results"]["kuz_ram_default"]
        assert "mae_mm" in metrics
        assert "rmse_mm" in metrics
        assert "mape_percent" in metrics
        assert "r2_score" in metrics
        assert "num_predictions" in metrics
    
    @pytest.mark.skip(reason="Requires authentication - implement when auth is ready")
    def test_noise_analysis(self):
        """Test noise analysis"""
        response = client.post(
            "/api/v1/synthetic/noise-analysis",
            params={
                "noise_levels": [0.1, 0.2],
                "num_samples": 10
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "base_scenario" in data["data"]
        assert "noise_analysis" in data["data"]
        assert len(data["data"]["noise_analysis"]) == 2


if __name__ == '__main__':
    pytest.main([__file__])