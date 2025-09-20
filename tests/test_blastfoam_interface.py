"""
Tests for blastFoam integration interface
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.drill_blast_system.simulation.blastfoam_interface import BlastFoamInterface
from src.drill_blast_system.simulation.data_structures import (
    BlastFoamConfig, SimulationJob, MeshGeometry, SimulationType
)


class TestBlastFoamInterface:
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration"""
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        assert interface.config == config
        assert interface.config.simulation_type == SimulationType.BLASTFOAM
        assert interface.config.mesh_resolution == 0.5
        assert interface.config.simulation_time == 0.1
    
    @patch('subprocess.run')
    def test_check_availability_success(self, mock_run):
        """Test successful availability check"""
        # Mock successful which commands
        mock_run.side_effect = [
            Mock(returncode=0),  # blockMesh found
            Mock(returncode=0)   # rhoCentralFoam found
        ]
        
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        assert interface.is_available == True
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_check_availability_failure(self, mock_run):
        """Test availability check when tools not found"""
        # Mock failed which commands
        mock_run.side_effect = [
            Mock(returncode=1),  # blockMesh not found
        ]
        
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        assert interface.is_available == False
    
    @patch('subprocess.run')
    def test_check_availability_with_custom_path(self, mock_run):
        """Test availability check with custom blastFoam path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock solver executable
            solver_path = Path(temp_dir) / "rhoCentralFoam"
            solver_path.touch()
            solver_path.chmod(0o755)
            
            mock_run.return_value = Mock(returncode=0)  # blockMesh found
            
            config = BlastFoamConfig(blastfoam_path=temp_dir)
            interface = BlastFoamInterface(config)
            
            assert interface.is_available == True
    
    def test_generate_case_files(self):
        """Test OpenFOAM case file generation"""
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
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
            case_dir = Path(temp_dir) / "test_case"
            case_dir.mkdir()
            
            interface._generate_case_files(case_dir, geometry, config)
            
            # Check that required directories were created
            assert (case_dir / "0").exists()
            assert (case_dir / "constant").exists()
            assert (case_dir / "system").exists()
            
            # Check that key files were created
            assert (case_dir / "system" / "controlDict").exists()
            assert (case_dir / "system" / "blockMeshDict").exists()
            assert (case_dir / "0" / "p").exists()
            assert (case_dir / "0" / "U").exists()
            assert (case_dir / "constant" / "thermophysicalProperties").exists()
    
    def test_write_control_dict(self):
        """Test controlDict file generation"""
        config = BlastFoamConfig(
            simulation_time=0.05,
            time_step=5e-7,
            pressure_solver="rhoCentralFoam"
        )
        interface = BlastFoamInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            control_dict_path = Path(temp_dir) / "controlDict"
            interface._write_control_dict(control_dict_path, config)
            
            content = control_dict_path.read_text()
            
            assert "application     rhoCentralFoam" in content
            assert "endTime         0.05" in content
            assert "deltaT          5e-07" in content
            assert "maxCo           0.5" in content
    
    def test_write_block_mesh_dict(self):
        """Test blockMeshDict file generation"""
        config = BlastFoamConfig(mesh_resolution=1.0)
        interface = BlastFoamInterface(config)
        
        geometry = MeshGeometry(
            bench_vertices=[(0, 0, 0), (20, 20, 10)],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[],
            charge_masses=[],
            charge_types=[]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mesh_dict_path = Path(temp_dir) / "blockMeshDict"
            interface._write_block_mesh_dict(mesh_dict_path, geometry, config)
            
            content = mesh_dict_path.read_text()
            
            assert "vertices" in content
            assert "blocks" in content
            assert "boundary" in content
            assert "ground" in content
            assert "atmosphere" in content
    
    def test_write_explosive_sources(self):
        """Test explosive source term generation"""
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        geometry = MeshGeometry(
            bench_vertices=[],
            bench_faces=[],
            hole_positions=[],
            hole_depths=[],
            hole_diameters=[],
            charge_positions=[(5, 5, -8), (15, 5, -8)],
            charge_masses=[25.0, 30.0],
            charge_types=["ANFO", "Emulsion"]
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            constant_dir = Path(temp_dir)
            interface._write_explosive_sources(constant_dir, geometry, config)
            
            fv_options_path = constant_dir / "fvOptions"
            assert fv_options_path.exists()
            
            content = fv_options_path.read_text()
            
            assert "explosive0" in content
            assert "explosive1" in content
            assert "explosiveMass   25.0" in content
            assert "explosiveMass   30.0" in content
            assert f"detonationVelocity {config.detonation_velocity}" in content
    
    @patch('subprocess.run')
    def test_generate_mesh_success(self, mock_run):
        """Test successful mesh generation"""
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir)
            result = interface._generate_mesh(case_dir)
            
            assert result == True
            # Check that blockMesh was called (last call should be the mesh generation)
            assert mock_run.call_args[0][0] == ["blockMesh", "-case", str(case_dir)]
            assert mock_run.call_args[1]["capture_output"] == True
            assert mock_run.call_args[1]["text"] == True
            assert mock_run.call_args[1]["timeout"] == 300
    
    @patch('subprocess.run')
    def test_generate_mesh_failure(self, mock_run):
        """Test mesh generation failure"""
        mock_run.return_value = Mock(returncode=1, stderr="Mesh generation failed")
        
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir)
            result = interface._generate_mesh(case_dir)
            
            assert result == False
    
    @patch('subprocess.run')
    def test_run_solver_success(self, mock_run):
        """Test successful solver execution"""
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        config = BlastFoamConfig(pressure_solver="rhoCentralFoam")
        interface = BlastFoamInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir)
            result = interface._run_solver(case_dir)
            
            assert result == True
            # Check that solver was called (last call should be the solver execution)
            assert mock_run.call_args[0][0] == ["rhoCentralFoam", "-case", str(case_dir)]
            assert mock_run.call_args[1]["capture_output"] == True
            assert mock_run.call_args[1]["text"] == True
            assert mock_run.call_args[1]["timeout"] == config.timeout_seconds
    
    @patch('subprocess.run')
    def test_run_solver_parallel(self, mock_run):
        """Test parallel solver execution"""
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        config = BlastFoamConfig(
            pressure_solver="rhoCentralFoam",
            parallel_processes=4
        )
        interface = BlastFoamInterface(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir)
            result = interface._run_solver(case_dir)
            
            assert result == True
            expected_cmd = [
                "mpirun", "-np", "4",
                "rhoCentralFoam", "-case", str(case_dir), "-parallel"
            ]
            # Check that parallel solver was called (last call should be the solver execution)
            assert mock_run.call_args[0][0] == expected_cmd
            assert mock_run.call_args[1]["capture_output"] == True
            assert mock_run.call_args[1]["text"] == True
            assert mock_run.call_args[1]["timeout"] == config.timeout_seconds
    
    def test_parse_results(self):
        """Test result parsing"""
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
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
            case_dir = Path(temp_dir)
            result = interface._parse_results(case_dir, geometry)
            
            assert result.simulation_type == SimulationType.BLASTFOAM
            assert result.success == True
            assert "receptor_0" in result.ppv_predictions
            assert result.fragment_size_distribution is not None
            assert "P80" in result.fragment_size_distribution
    
    @patch.object(BlastFoamInterface, '_check_availability')
    def test_run_simulation_not_available(self, mock_check):
        """Test simulation when blastFoam not available"""
        mock_check.return_value = False
        
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
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
        assert "blastFoam not available" in result.errors[0]
    
    def test_generate_installation_guide(self):
        """Test installation guide generation"""
        config = BlastFoamConfig()
        interface = BlastFoamInterface(config)
        
        guide = interface.generate_installation_guide()
        
        assert "blastFoam Installation Guide" in guide
        assert "OpenFOAM Installation" in guide
        assert "Prerequisites" in guide
        assert "Configuration" in guide
        assert "Troubleshooting" in guide
        assert "github.com/synthetik-technologies/blastfoam" in guide


if __name__ == "__main__":
    pytest.main([__file__])