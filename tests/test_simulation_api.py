"""
Tests for simulation API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.drill_blast_system.api.main import create_app
from src.drill_blast_system.simulation.data_structures import SimulationType, SimulationResult


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock authentication"""
    with patch('src.drill_blast_system.api.routes.simulations.get_current_user') as mock:
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock.return_value = mock_user
        yield mock


@pytest.fixture
def mock_simulation_manager():
    """Mock simulation manager"""
    with patch('src.drill_blast_system.api.routes.simulations.simulation_manager') as mock:
        yield mock


class TestSimulationAPI:
    
    def test_get_capabilities(self, client, mock_auth, mock_simulation_manager):
        """Test getting simulation capabilities"""
        # Mock simulation manager methods
        mock_simulation_manager.get_available_simulations.return_value = [SimulationType.PHYSICS_ONLY]
        mock_simulation_manager.get_installation_guides.return_value = {"blastfoam": "guide content"}
        
        response = client.get("/api/v1/simulations/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert "available_types" in data
        assert "blastfoam_available" in data
        assert "yade_available" in data
        assert "installation_guides" in data
    
    def test_create_simulation_job(self, client, mock_auth, mock_simulation_manager):
        """Test creating a simulation job"""
        # Mock simulation manager methods
        mock_simulation_manager.create_simulation_job.return_value = "test-job-id"
        mock_simulation_manager.active_jobs = {
            "test-job-id": Mock(
                job_id="test-job-id",
                blast_plan_id=None,
                priority=5
            )
        }
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "pending",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "has_result": False
        }
        
        job_request = {
            "simulation_type": "physics_only",
            "geometry": {
                "bench_vertices": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
                "bench_faces": [[0, 1, 2, 3]],
                "hole_positions": [[5, 5, 0]],
                "hole_depths": [10.0],
                "hole_diameters": [0.15],
                "charge_positions": [[5, 5, -8]],
                "charge_masses": [25.0],
                "charge_types": ["ANFO"]
            },
            "priority": 5
        }
        
        response = client.post("/api/v1/simulations/jobs", json=job_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["simulation_type"] == "physics_only"
        assert data["status"] == "pending"
    
    def test_list_simulation_jobs(self, client, mock_auth, mock_simulation_manager):
        """Test listing simulation jobs"""
        # Mock active jobs
        mock_job = Mock()
        mock_job.job_id = "test-job-id"
        mock_job.blast_plan_id = None
        mock_job.priority = 5
        mock_job.result = None
        
        mock_simulation_manager.active_jobs = {"test-job-id": mock_job}
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "completed",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "started_at": "2023-01-01T00:01:00",
            "completed_at": "2023-01-01T00:02:00",
            "has_result": False
        }
        
        response = client.get("/api/v1/simulations/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_id"] == "test-job-id"
    
    def test_get_simulation_job(self, client, mock_auth, mock_simulation_manager):
        """Test getting a specific simulation job"""
        mock_job = Mock()
        mock_job.job_id = "test-job-id"
        mock_job.blast_plan_id = None
        mock_job.priority = 5
        mock_job.result = None
        
        mock_simulation_manager.active_jobs = {"test-job-id": mock_job}
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "completed",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "started_at": "2023-01-01T00:01:00",
            "completed_at": "2023-01-01T00:02:00",
            "has_result": False
        }
        
        response = client.get("/api/v1/simulations/jobs/test-job-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "completed"
    
    def test_get_nonexistent_job(self, client, mock_auth, mock_simulation_manager):
        """Test getting a non-existent simulation job"""
        mock_simulation_manager.get_job_status.return_value = None
        
        response = client.get("/api/v1/simulations/jobs/nonexistent-job")
        
        assert response.status_code == 404
    
    def test_update_simulation_job(self, client, mock_auth, mock_simulation_manager):
        """Test updating a simulation job"""
        mock_job = Mock()
        mock_job.job_id = "test-job-id"
        mock_job.blast_plan_id = None
        mock_job.priority = 5
        mock_job.result = None
        
        mock_simulation_manager.active_jobs = {"test-job-id": mock_job}
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "pending",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "has_result": False
        }
        
        update_data = {"priority": 8}
        
        response = client.patch("/api/v1/simulations/jobs/test-job-id", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        # Check that priority was updated
        assert mock_job.priority == 8
    
    def test_cancel_simulation_job(self, client, mock_auth, mock_simulation_manager):
        """Test cancelling a simulation job"""
        mock_job = Mock()
        mock_job.job_id = "test-job-id"
        mock_job.blast_plan_id = None
        mock_job.priority = 5
        mock_job.result = None
        
        mock_simulation_manager.active_jobs = {"test-job-id": mock_job}
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "running",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "started_at": "2023-01-01T00:01:00",
            "completed_at": None,
            "has_result": False
        }
        mock_simulation_manager.cancel_job.return_value = True
        
        update_data = {"status": "cancelled"}
        
        response = client.patch("/api/v1/simulations/jobs/test-job-id", json=update_data)
        
        assert response.status_code == 200
        mock_simulation_manager.cancel_job.assert_called_once_with("test-job-id")
    
    def test_delete_simulation_job(self, client, mock_auth, mock_simulation_manager):
        """Test deleting a simulation job"""
        mock_job = Mock()
        mock_job.job_id = "test-job-id"
        
        mock_simulation_manager.active_jobs = {"test-job-id": mock_job}
        mock_simulation_manager.get_job_status.return_value = {
            "job_id": "test-job-id",
            "status": "completed",
            "simulation_type": "physics_only",
            "created_at": "2023-01-01T00:00:00",
            "has_result": False
        }
        
        response = client.delete("/api/v1/simulations/jobs/test-job-id")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
    
    def test_compare_simulation_results(self, client, mock_auth, mock_simulation_manager):
        """Test comparing simulation results"""
        # Mock jobs with results
        mock_result1 = SimulationResult(
            simulation_type=SimulationType.PHYSICS_ONLY,
            success=True,
            runtime_seconds=1.0,
            ppv_predictions={"receptor_0": 3.0},
            ppv_time_series={},
            fragment_size_distribution={"P80": 100.0},
            mesh_quality_metrics={},
            convergence_metrics={},
            warnings=[],
            errors=[]
        )
        
        mock_result2 = SimulationResult(
            simulation_type=SimulationType.PHYSICS_ONLY,
            success=True,
            runtime_seconds=2.0,
            ppv_predictions={"receptor_0": 3.5},
            ppv_time_series={},
            fragment_size_distribution={"P80": 110.0},
            mesh_quality_metrics={},
            convergence_metrics={},
            warnings=[],
            errors=[]
        )
        
        mock_job1 = Mock()
        mock_job1.result = mock_result1
        mock_job2 = Mock()
        mock_job2.result = mock_result2
        
        mock_simulation_manager.active_jobs = {
            "job1": mock_job1,
            "job2": mock_job2
        }
        mock_simulation_manager.get_job_status.side_effect = lambda job_id: {
            "job_id": job_id,
            "status": "completed",
            "has_result": True
        }
        mock_simulation_manager.compare_simulation_results.return_value = {
            "simulation_types": ["physics_only", "physics_only"],
            "success_rates": [True, True],
            "runtimes": [1.0, 2.0],
            "fragmentation_comparison": {
                "physics_only": {"P80": 105.0}
            },
            "ppv_comparison": {
                "physics_only": {"receptor_0": 3.25}
            },
            "performance_metrics": {
                "fastest_runtime": 1.0,
                "slowest_runtime": 2.0,
                "average_runtime": 1.5,
                "success_rate": 1.0
            }
        }
        
        response = client.post("/api/v1/simulations/compare", json=["job1", "job2"])
        
        assert response.status_code == 200
        data = response.json()
        assert "simulation_types" in data
        assert "performance_metrics" in data
        assert len(data["simulation_types"]) == 2
    
    def test_cleanup_jobs(self, client, mock_auth, mock_simulation_manager):
        """Test cleaning up old simulation jobs"""
        mock_simulation_manager.cleanup_completed_jobs.return_value = 3
        
        response = client.post("/api/v1/simulations/cleanup?max_age_hours=24")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cleaned_jobs"] == 3
        mock_simulation_manager.cleanup_completed_jobs.assert_called_once_with(24)
    
    def test_get_installation_guides(self, client, mock_auth, mock_simulation_manager):
        """Test getting installation guides"""
        mock_guides = {
            "blastfoam": "blastFoam installation guide content",
            "yade": "YADE installation guide content"
        }
        mock_simulation_manager.get_installation_guides.return_value = mock_guides
        
        response = client.get("/api/v1/simulations/installation-guides")
        
        assert response.status_code == 200
        data = response.json()
        assert data == mock_guides
    
    def test_test_config_blastfoam(self, client, mock_auth):
        """Test testing blastFoam configuration"""
        config_test = {
            "simulation_type": "blastfoam",
            "blastfoam_config": {
                "enabled": True,
                "mesh_resolution": 1.0,
                "simulation_time": 0.05,
                "time_step": 1e-6,
                "parallel_processes": 4,
                "explosive_density": 1200.0,
                "detonation_velocity": 6000.0,
                "chapman_jouguet_pressure": 21e9,
                "timeout_seconds": 3600
            }
        }
        
        with patch('src.drill_blast_system.api.routes.simulations.simulation_manager') as mock_manager:
            mock_manager.blastfoam_interface = Mock()
            mock_manager.blastfoam_interface.is_available = False
            
            response = client.post("/api/v1/simulations/test-config", json=config_test)
            
            assert response.status_code == 200
            data = response.json()
            assert data["simulation_type"] == "blastfoam"
            assert data["available"] == False
            assert data["test_passed"] == False
    
    def test_invalid_simulation_type(self, client, mock_auth):
        """Test creating job with invalid simulation type"""
        job_request = {
            "simulation_type": "invalid_type",
            "geometry": {
                "bench_vertices": [[0, 0, 0]],
                "bench_faces": [],
                "hole_positions": [],
                "hole_depths": [],
                "hole_diameters": [],
                "charge_positions": [],
                "charge_masses": [],
                "charge_types": []
            }
        }
        
        response = client.post("/api/v1/simulations/jobs", json=job_request)
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])