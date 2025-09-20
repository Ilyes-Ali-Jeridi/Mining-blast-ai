"""
Tests for YADE DEM integration interface
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import numpy as np

from src.drill_blast_system.simulation.yade_interface import YadeInterface
from src.drill_blast_system.simulation.data_structures import (
    YadeConfig, SimulationJob, MeshGeometry, SimulationType, SimulationResult
)


class TestYadeInterface:
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration"""
        config = YadeConfig()
        interface = YadeInterface(config)
        
        assert interface.config == config
        assert interface.config.simulation_type == SimulationType.YADE
        assert interface.config.particle_radius_min == 0.01
        assert interface.config.particle_radius_max == 0.1
        assert interface.config.particle_density == 2700.0
    
    @patch('subprocess.run')
    def test_check_availability_success(self, mock_run):
        """Test successful availability check"""
        # Mock successful which command and Python import test
        mock_run.side_effect = [
            Mock(returncode=0),  # yade found
            Mock(returncode=0, stdout="YADE_AVAILABLE")  # Python import successful
        ]
        
        config = YadeConfig()
        interface = YadeInterface(config)
        
        assert interface.is_available == True
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_check_availability_failure_not_found(self, mock_run):
        """Test availability check when YADE not found"""
        mock_run.return_value = Mock(returncode=1)  # yade not found
        
        config = YadeConfig()
        interface = YadeInterface(config)
        
        assert interface.is_available == False
    
    @patch('subprocess.run')
    def test_check_availability_failure_import_error(self, mock_run):
        """Test availability check when Python import fails"""
        mock_run.side_effect = [
            Mock(returncode=0),  # yade found
            Mock(returncode=1, stdout="YADE_IMPORT_ERROR: No module named 'yade'")  # Import failed
        ]
        
        config = YadeConfig()
        interface = YadeInterface(config)
        
        assert interface.is_available == False
    
    @patch('subprocess.run')
    def test_check_availability_with_custom_executable(self, mock_run):
        """Test availability check with custom YADE executable"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock YADE executable
            yade_path = Path(temp_dir) / "yade"
            yade_path.touch()
            yade_path.chmod(0o755)
            
            mock_run.return_value = Mock(returncode=0, stdout="YADE_AVAILABLE")
            
            config = YadeConfig(yade_executable=str(yade_path))
            interface = YadeInterface(config)
            
            assert interface.is_available == True
    
    def test_generate_simulation_script(self):
        """Test YADE simulation script generation"""
        config = YadeConfig(
            particle_radius_min=0.02,
            particle_radius_max=0.08,
            young_modulus=50e9,
            max_iterations=50000
        )
        interface = YadeInterface(config)
        
        geometry = MeshGeometry(
            bench_vertices=[(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)],
            bench_faces=[[0, 1, 2, 3]],
            hole_positions=[(5, 5, -5)],
            hole_depths=[10.0],
            hole_diameters=[0.15],
            charge_positions=[(5, 5, -8)],
            charge_masses=[25.0],
            charge_types=["ANFO"]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            script_path = interface._generate_simulation_script(work_dir, geometry, config)
            
            assert script_path.exists()
            assert script_path.is_file()
            assert script_path.suffix == ".py"
            
            content = script_path.read_text()
            
            # Check that key parameters are included
            assert f"PARTICLE_DENSITY = {config.particle_density}" in content
            assert f"YOUNG_MODULUS = {config.young_modulus}" in content
            assert f"MAX_ITERATIONS = {config.max_iterations}" in content
            assert f"RADIUS_MIN = {config.particle_radius_min}" in content
            assert f"RADIUS_MAX = {config.particle_radius_max}" in content
            
            # Check that key functions are defined
            assert "def create_rock_mass():" in content
            assert "def setup_materials():" in content
            assert "def setup_engines():" in content
            assert "def apply_blast_loading():" in content
            assert "def analyze_fragmentation():" in content
            
            # Check that blast parameters are included
            assert "blast_positions" in content
            assert "blast_masses" in content
    
    @patch('subprocess.run')
    def test_run_yade_simulation_success(self, mock_run):
        """Test successful YADE simulation execution"""
        mock_run.return_value = Mock(returncode=0, stdout="Simulation completed")
        
        config = YadeConfig()
        interface = YadeInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            script_path = work_dir / "test_script.py"
            script_path.write_text("# Test script")
            
            # Create mock results directory and files
            results_dir = work_dir / "results"
            results_dir.mkdir()
            
            # Create mock fragmentation results
            frag_results = {
                "fragment_sizes": [0.1, 0.2, 0.3, 0.4, 0.5],
                "statistics": {
                    "P10": 0.15,
                    "P50": 0.3,
                    "P80": 0.45,
                    "mean": 0.3,
                    "count": 5
                }
            }
            (results_dir / "fragmentation_results.json").write_text(json.dumps(frag_results))
            
            # Create mock particle data
            particle_data = [
                {
                    "id": 0,
                    "position": [1.0, 2.0, 3.0],
                    "radius": 0.05,
                    "velocity": [0.1, 0.2, 0.3],
                    "force": [10.0, 20.0, 30.0]
                }
            ]
            (results_dir / "particles_001000.json").write_text(json.dumps(particle_data))
            
            success, output_files = interface._run_yade_simulation(script_path, work_dir)
            
            assert success == True
            assert "fragmentation_results" in output_files
            assert "particles_001000" in output_files
    
    @patch('subprocess.run')
    def test_run_yade_simulation_failure(self, mock_run):
        """Test YADE simulation execution failure"""
        mock_run.return_value = Mock(returncode=1, stderr="Simulation failed")
        
        config = YadeConfig()
        interface = YadeInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            script_path = work_dir / "test_script.py"
            script_path.write_text("# Test script")
            
            success, output_files = interface._run_yade_simulation(script_path, work_dir)
            
            assert success == False
            assert output_files == {}
    
    def test_parse_yade_results(self):
        """Test YADE result parsing"""
        config = YadeConfig()
        interface = YadeInterface(config)
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[(5, 5, -8)],
            charge_masses=[25.0],
            charge_types=["ANFO"]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock result files
            frag_results = {
                "fragment_sizes": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
                "statistics": {
                    "P10": 0.08,
                    "P50": 0.175,
                    "P80": 0.26,
                    "mean": 0.175,
                    "count": 6
                }
            }
            frag_file = Path(temp_dir) / "fragmentation_results.json"
            frag_file.write_text(json.dumps(frag_results))
            
            particle_data = [
                {
                    "id": i,
                    "position": [i, i, i],
                    "radius": 0.05,
                    "velocity": [0.1 * i, 0.2 * i, 0.3 * i],
                    "force": [10.0 * i, 20.0 * i, 30.0 * i]
                }
                for i in range(5)
            ]
            particle_file = Path(temp_dir) / "particles_010000.json"
            particle_file.write_text(json.dumps(particle_data))
            
            output_files = {
                "fragmentation_results": frag_file,
                "particles_010000": particle_file
            }
            
            result = interface._parse_yade_results(output_files, geometry)
            
            assert result.simulation_type == SimulationType.YADE
            assert result.success == True
            
            # Check fragmentation results
            assert result.fragment_sizes is not None
            assert len(result.fragment_sizes) == 6
            assert result.fragment_size_distribution is not None
            assert result.fragment_size_distribution["P80"] == 0.26
            
            # Check PPV results
            assert result.ppv_predictions is not None
            assert "receptor_0" in result.ppv_predictions
            assert result.ppv_predictions["receptor_0"] > 0
            
            # Check convergence metrics
            assert result.convergence_metrics is not None
            assert "particles_simulated" in result.convergence_metrics
    
    def test_parse_yade_results_missing_files(self):
        """Test result parsing with missing files"""
        config = YadeConfig()
        interface = YadeInterface(config)
        
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
        
        # Empty output files
        output_files = {}
        
        result = interface._parse_yade_results(output_files, geometry)
        
        assert result.simulation_type == SimulationType.YADE
        assert result.success == True  # Should still succeed with empty results
        assert result.fragment_sizes is None
        assert result.fragment_size_distribution is None
    
    @patch.object(YadeInterface, '_check_availability')
    def test_run_simulation_not_available(self, mock_check):
        """Test simulation when YADE not available"""
        mock_check.return_value = False
        
        config = YadeConfig()
        interface = YadeInterface(config)
        interface.is_available = False
        
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
        
        job = SimulationJob(
            job_id="test_job",
            config=config,
            geometry=geometry
        )
        
        result = interface.run_simulation(job)
        
        assert result.success == False
        assert "YADE not available" in result.errors[0]
    
    @patch.object(YadeInterface, '_check_availability')
    @patch.object(YadeInterface, '_run_yade_simulation')
    @patch.object(YadeInterface, '_generate_simulation_script')
    @patch.object(YadeInterface, '_parse_yade_results')
    def test_run_simulation_success(self, mock_parse, mock_script, mock_run, mock_check):
        """Test successful simulation run"""
        mock_check.return_value = True
        mock_script.return_value = Path("/tmp/script.py")
        
        # Mock successful simulation with results
        mock_run.return_value = (True, {"fragmentation_results": Path("/tmp/frag.json")})
        
        # Mock successful result parsing
        mock_result = SimulationResult(
            simulation_type=SimulationType.YADE,
            success=True,
            runtime_seconds=0.0,
            fragment_size_distribution={"P80": 0.25}
        )
        mock_parse.return_value = mock_result
        
        config = YadeConfig()
        interface = YadeInterface(config)
        interface.is_available = True
        
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
        
        job = SimulationJob(
            job_id="test_job",
            config=config,
            geometry=geometry
        )
        
        result = interface.run_simulation(job)
        
        assert result.success == True
        assert result.simulation_type == SimulationType.YADE
        assert result.runtime_seconds >= 0
    
    def test_generate_installation_guide(self):
        """Test installation guide generation"""
        config = YadeConfig()
        interface = YadeInterface(config)
        
        guide = interface.generate_installation_guide()
        
        assert "YADE Installation Guide" in guide
        assert "Prerequisites" in guide
        assert "System Requirements" in guide
        assert "Package Installation" in guide
        assert "Source Installation" in guide
        assert "Configuration" in guide
        assert "Troubleshooting" in guide
        assert "yade-dem.org" in guide
        assert "sudo apt install yade" in guide
    
    def test_config_validation(self):
        """Test configuration parameter validation"""
        # Test valid configuration
        config = YadeConfig(
            particle_radius_min=0.01,
            particle_radius_max=0.1,
            young_modulus=70e9,
            poisson_ratio=0.25,
            friction_angle=30.0
        )
        
        assert config.particle_radius_min < config.particle_radius_max
        assert 0 < config.poisson_ratio < 0.5
        assert config.young_modulus > 0
        assert 0 <= config.friction_angle <= 90
    
    def test_geometry_handling(self):
        """Test handling of different geometry configurations"""
        config = YadeConfig()
        interface = YadeInterface(config)
        
        # Test with minimal geometry
        minimal_geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            script_path = interface._generate_simulation_script(work_dir, minimal_geometry, config)
            
            content = script_path.read_text()
            assert "blast_positions = []" in content
            assert "blast_masses = []" in content
        
        # Test with complex geometry
        complex_geometry = MeshGeometry(
            bench_vertices=[(0, 0, 0), (50, 0, 0), (50, 50, 0), (0, 50, 0)],
            bench_faces=[[0, 1, 2, 3]],
            hole_positions=[(10, 10, -5), (20, 20, -5), (30, 30, -5)],
            hole_depths=[15.0, 15.0, 15.0],
            hole_diameters=[0.15, 0.15, 0.15],
            charge_positions=[(10, 10, -12), (20, 20, -12), (30, 30, -12)],
            charge_masses=[30.0, 35.0, 40.0],
            charge_types=["ANFO", "Emulsion", "ANFO"]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            script_path = interface._generate_simulation_script(work_dir, complex_geometry, config)
            
            content = script_path.read_text()
            assert "[10, 10, -12]" in content
            assert "[20, 20, -12]" in content
            assert "[30, 30, -12]" in content
            assert "30.0" in content
            assert "35.0" in content
            assert "40.0" in content


if __name__ == "__main__":
    pytest.main([__file__])