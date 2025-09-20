"""
Tests for simulation manager
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.drill_blast_system.simulation.simulation_manager import SimulationManager
from src.drill_blast_system.simulation.data_structures import (
    SimulationType, BlastFoamConfig, YadeConfig, MeshGeometry, SimulationResult
)


class TestSimulationManager:
    
    def test_init(self):
        """Test simulation manager initialization"""
        manager = SimulationManager()
        
        assert manager.blastfoam_interface is None
        assert manager.yade_interface is None
        assert 'kuz_ram' in manager.physics_models
        assert 'ppv' in manager.physics_models
        assert manager.active_jobs == {}
    
    def test_configure_blastfoam(self):
        """Test blastFoam configuration"""
        manager = SimulationManager()
        config = BlastFoamConfig(enabled=True)
        
        with patch('src.drill_blast_system.simulation.simulation_manager.BlastFoamInterface') as mock_interface:
            mock_instance = Mock()
            mock_instance.is_available = True
            mock_interface.return_value = mock_instance
            
            manager.configure_blastfoam(config)
            
            assert manager.blastfoam_interface is not None
            mock_interface.assert_called_once_with(config)
    
    def test_configure_yade(self):
        """Test YADE configuration"""
        manager = SimulationManager()
        config = YadeConfig(enabled=True)
        
        with patch('src.drill_blast_system.simulation.simulation_manager.YadeInterface') as mock_interface:
            mock_instance = Mock()
            mock_instance.is_available = True
            mock_interface.return_value = mock_instance
            
            manager.configure_yade(config)
            
            assert manager.yade_interface is not None
            mock_interface.assert_called_once_with(config)
    
    def test_get_available_simulations_physics_only(self):
        """Test getting available simulations with physics only"""
        manager = SimulationManager()
        
        available = manager.get_available_simulations()
        
        assert available == [SimulationType.PHYSICS_ONLY]
    
    def test_get_available_simulations_all_available(self):
        """Test getting available simulations with all tools available"""
        manager = SimulationManager()
        
        # Mock available interfaces
        mock_blastfoam = Mock()
        mock_blastfoam.is_available = True
        manager.blastfoam_interface = mock_blastfoam
        
        mock_yade = Mock()
        mock_yade.is_available = True
        manager.yade_interface = mock_yade
        
        available = manager.get_available_simulations()
        
        assert SimulationType.PHYSICS_ONLY in available
        assert SimulationType.BLASTFOAM in available
        assert SimulationType.YADE in available
        assert len(available) == 3
    
    def test_get_available_simulations_partial_available(self):
        """Test getting available simulations with some tools unavailable"""
        manager = SimulationManager()
        
        # Mock partially available interfaces
        mock_blastfoam = Mock()
        mock_blastfoam.is_available = False
        manager.blastfoam_interface = mock_blastfoam
        
        mock_yade = Mock()
        mock_yade.is_available = True
        manager.yade_interface = mock_yade
        
        available = manager.get_available_simulations()
        
        assert SimulationType.PHYSICS_ONLY in available
        assert SimulationType.BLASTFOAM not in available
        assert SimulationType.YADE in available
        assert len(available) == 2
    
    def test_create_simulation_job(self):
        """Test creating simulation job"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[(0, 0, -5)],
            charge_masses=[25.0],
            charge_types=["ANFO"]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        
        assert job_id in manager.active_jobs
        job = manager.active_jobs[job_id]
        assert job.config.simulation_type == SimulationType.PHYSICS_ONLY
        assert job.geometry == geometry
        assert job.status == "pending"
        assert job.created_at is not None
    
    def test_create_simulation_job_with_config(self):
        """Test creating simulation job with custom config"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        config = BlastFoamConfig(mesh_resolution=0.25)
        job_id = manager.create_simulation_job(SimulationType.BLASTFOAM, geometry, config)
        
        job = manager.active_jobs[job_id]
        assert job.config == config
        assert job.config.mesh_resolution == 0.25
    
    def test_run_physics_simulation(self):
        """Test running physics-based simulation"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[(0, 0, -5)],
            hole_depths=[10.0],
            hole_diameters=[0.15],
            charge_positions=[(0, 0, -8)],
            charge_masses=[25.0],
            charge_types=["ANFO"]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        job = manager.active_jobs[job_id]
        
        result = manager._run_physics_simulation(job)
        
        assert result.simulation_type == SimulationType.PHYSICS_ONLY
        assert result.success == True
        assert result.runtime_seconds >= 0
        assert result.ppv_predictions is not None
        assert result.fragment_size_distribution is not None
        assert "P80" in result.fragment_size_distribution
    
    def test_run_simulation_sync_physics(self):
        """Test synchronous simulation run with physics"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[(0, 0, -5)],
            charge_masses=[20.0],
            charge_types=["ANFO"]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        result = manager.run_simulation_sync(job_id)
        
        assert result.success == True
        assert result.simulation_type == SimulationType.PHYSICS_ONLY
    
    def test_run_simulation_sync_blastfoam_not_available(self):
        """Test synchronous simulation run with blastFoam not available"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        job_id = manager.create_simulation_job(SimulationType.BLASTFOAM, geometry)
        result = manager.run_simulation_sync(job_id)
        
        assert result.success == False
        assert "blastFoam not available" in result.errors
    
    def test_run_simulation_sync_yade_not_available(self):
        """Test synchronous simulation run with YADE not available"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        job_id = manager.create_simulation_job(SimulationType.YADE, geometry)
        result = manager.run_simulation_sync(job_id)
        
        assert result.success == False
        assert "YADE not available" in result.errors
    
    def test_run_simulation_sync_unknown_type(self):
        """Test synchronous simulation run with unknown simulation type"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        # Create job with invalid simulation type (hack for testing)
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        job = manager.active_jobs[job_id]
        job.config.simulation_type = "invalid_type"  # This would normally not be possible
        
        # Mock the enum comparison to fail
        with patch.object(job.config, 'simulation_type', "invalid_type"):
            result = manager._run_simulation_sync(job)
        
            assert result.success == False
            assert "Unknown simulation type" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_run_simulation_async(self):
        """Test asynchronous simulation run"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[(0, 0, -5)],
            charge_masses=[15.0],
            charge_types=["ANFO"]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        result = await manager.run_simulation_async(job_id)
        
        assert result.success == True
        assert result.simulation_type == SimulationType.PHYSICS_ONLY
        
        # Check job status was updated
        job = manager.active_jobs[job_id]
        assert job.status == "completed"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.result == result
    
    @pytest.mark.asyncio
    async def test_run_simulation_async_job_not_found(self):
        """Test asynchronous simulation run with non-existent job"""
        manager = SimulationManager()
        
        with pytest.raises(ValueError, match="Job .* not found"):
            await manager.run_simulation_async("non_existent_job")
    
    def test_compare_simulation_results_empty(self):
        """Test comparing empty results list"""
        manager = SimulationManager()
        
        comparison = manager.compare_simulation_results([])
        
        assert "error" in comparison
        assert comparison["error"] == "No results to compare"
    
    def test_compare_simulation_results_single(self):
        """Test comparing single result"""
        manager = SimulationManager()
        
        result = SimulationResult(
            simulation_type=SimulationType.PHYSICS_ONLY,
            success=True,
            runtime_seconds=1.5,
            fragment_size_distribution={"P80": 150.0, "P50": 100.0},
            ppv_predictions={"receptor_0": 3.2}
        )
        
        comparison = manager.compare_simulation_results([result])
        
        assert comparison["simulation_types"] == ["physics_only"]
        assert comparison["success_rates"] == [True]
        assert comparison["runtimes"] == [1.5]
        assert "physics_only" in comparison["fragmentation_comparison"]
        assert "physics_only" in comparison["ppv_comparison"]
    
    def test_compare_simulation_results_multiple(self):
        """Test comparing multiple results"""
        manager = SimulationManager()
        
        physics_result = SimulationResult(
            simulation_type=SimulationType.PHYSICS_ONLY,
            success=True,
            runtime_seconds=1.0,
            fragment_size_distribution={"P80": 100.0, "P50": 70.0},
            ppv_predictions={"receptor_0": 3.0}
        )
        
        blastfoam_result = SimulationResult(
            simulation_type=SimulationType.BLASTFOAM,
            success=True,
            runtime_seconds=120.0,
            fragment_size_distribution={"P80": 110.0, "P50": 75.0},
            ppv_predictions={"receptor_0": 3.5}
        )
        
        comparison = manager.compare_simulation_results([physics_result, blastfoam_result])
        
        assert len(comparison["simulation_types"]) == 2
        assert "physics_only" in comparison["simulation_types"]
        assert "blastfoam" in comparison["simulation_types"]
        
        # Check relative difference calculation
        assert "blastfoam_vs_physics_p80_diff_%" in comparison["fragmentation_comparison"]
        expected_diff = (110.0 - 100.0) / 100.0 * 100  # 10%
        assert comparison["fragmentation_comparison"]["blastfoam_vs_physics_p80_diff_%"] == expected_diff
        
        # Check performance metrics
        assert comparison["performance_metrics"]["fastest_runtime"] == 1.0
        assert comparison["performance_metrics"]["slowest_runtime"] == 120.0
        assert comparison["performance_metrics"]["success_rate"] == 1.0
    
    def test_get_job_status(self):
        """Test getting job status"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        status = manager.get_job_status(job_id)
        
        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == "pending"
        assert status["simulation_type"] == "physics_only"
        assert status["created_at"] is not None
        assert status["has_result"] == False
    
    def test_get_job_status_not_found(self):
        """Test getting status of non-existent job"""
        manager = SimulationManager()
        
        status = manager.get_job_status("non_existent_job")
        
        assert status is None
    
    def test_cancel_job(self):
        """Test cancelling job"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        
        # Set job to running status
        job = manager.active_jobs[job_id]
        job.status = "running"
        
        success = manager.cancel_job(job_id)
        
        assert success == True
        assert job.status == "cancelled"
    
    def test_cancel_job_not_running(self):
        """Test cancelling job that's not running"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        
        # Job is in pending status
        success = manager.cancel_job(job_id)
        
        assert success == False
    
    def test_cancel_job_not_found(self):
        """Test cancelling non-existent job"""
        manager = SimulationManager()
        
        success = manager.cancel_job("non_existent_job")
        
        assert success == False
    
    def test_cleanup_completed_jobs(self):
        """Test cleaning up old completed jobs"""
        manager = SimulationManager()
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        # Create some jobs
        job_id1 = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        job_id2 = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
        
        # Set jobs to completed with old timestamps
        old_time = datetime.now().replace(year=2020).isoformat()
        
        job1 = manager.active_jobs[job_id1]
        job1.status = "completed"
        job1.completed_at = old_time
        
        job2 = manager.active_jobs[job_id2]
        job2.status = "failed"
        job2.completed_at = old_time
        
        # Clean up jobs older than 1 hour
        cleaned_count = manager.cleanup_completed_jobs(max_age_hours=1)
        
        assert cleaned_count == 2
        assert job_id1 not in manager.active_jobs
        assert job_id2 not in manager.active_jobs
    
    def test_get_installation_guides(self):
        """Test getting installation guides"""
        manager = SimulationManager()
        
        # Configure interfaces
        mock_blastfoam = Mock()
        mock_blastfoam.generate_installation_guide.return_value = "blastFoam guide"
        manager.blastfoam_interface = mock_blastfoam
        
        mock_yade = Mock()
        mock_yade.generate_installation_guide.return_value = "YADE guide"
        manager.yade_interface = mock_yade
        
        guides = manager.get_installation_guides()
        
        assert "blastfoam" in guides
        assert "yade" in guides
        assert guides["blastfoam"] == "blastFoam guide"
        assert guides["yade"] == "YADE guide"
    
    def test_get_installation_guides_no_interfaces(self):
        """Test getting installation guides with no interfaces configured"""
        manager = SimulationManager()
        
        guides = manager.get_installation_guides()
        
        assert guides == {}


if __name__ == "__main__":
    pytest.main([__file__])