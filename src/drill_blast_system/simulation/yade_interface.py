"""
YADE DEM Integration Interface

This module provides integration with YADE (Yet Another Dynamic Engine),
a discrete element method (DEM) simulation platform for particle-based modeling.

YADE can simulate rock fragmentation through particle interactions and fracture mechanics,
providing detailed fragmentation analysis and particle size distributions.

Installation Requirements:
- YADE (1.20.0 or later)
- Python bindings for YADE
- NumPy, SciPy for data processing

Documentation: https://yade-dem.org/
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import logging
from datetime import datetime
import json

from .data_structures import (
    YadeConfig, SimulationResult, MeshGeometry, 
    SimulationType, SimulationJob
)

logger = logging.getLogger(__name__)


class YadeInterface:
    """Interface for YADE DEM simulation integration"""
    
    def __init__(self, config: YadeConfig):
        self.config = config
        self.is_available = self._check_availability()
        
    def _check_availability(self) -> bool:
        """Check if YADE is available on the system"""
        try:
            # Check for YADE executable
            if self.config.yade_executable:
                yade_path = Path(self.config.yade_executable)
                if not yade_path.exists():
                    logger.warning(f"YADE executable not found at {yade_path}")
                    return False
            else:
                # Try to find YADE in standard locations
                result = subprocess.run(
                    ["which", "yade"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning("YADE not found in PATH")
                    return False
            
            # Test YADE Python import
            test_script = """
import sys
try:
    import yade
    print("YADE_AVAILABLE")
    sys.exit(0)
except ImportError as e:
    print(f"YADE_IMPORT_ERROR: {e}")
    sys.exit(1)
"""
            
            result = subprocess.run(
                ["python3", "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if "YADE_AVAILABLE" not in result.stdout:
                logger.warning("YADE Python bindings not available")
                return False
                
            logger.info("YADE integration available")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking YADE availability: {e}")
            return False
    
    def run_simulation(self, job: SimulationJob) -> SimulationResult:
        """Run YADE DEM simulation for given job"""
        if not self.is_available:
            return SimulationResult(
                simulation_type=SimulationType.YADE,
                success=False,
                runtime_seconds=0.0,
                errors=["YADE not available on system"]
            )
        
        start_time = datetime.now()
        
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory(prefix="yade_") as temp_dir:
                work_dir = Path(temp_dir)
                
                # Generate YADE simulation script
                script_path = self._generate_simulation_script(work_dir, job.geometry, job.config)
                
                # Run YADE simulation
                sim_success, output_files = self._run_yade_simulation(script_path, work_dir)
                if not sim_success:
                    return SimulationResult(
                        simulation_type=SimulationType.YADE,
                        success=False,
                        runtime_seconds=(datetime.now() - start_time).total_seconds(),
                        errors=["YADE simulation failed"]
                    )
                
                # Parse results
                result = self._parse_yade_results(output_files, job.geometry)
                result.runtime_seconds = (datetime.now() - start_time).total_seconds()
                
                return result
                
        except Exception as e:
            logger.error(f"YADE simulation failed: {e}")
            return SimulationResult(
                simulation_type=SimulationType.YADE,
                success=False,
                runtime_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[f"Simulation failed: {str(e)}"]
            )
    
    def _generate_simulation_script(self, work_dir: Path, geometry: MeshGeometry, config: YadeConfig) -> Path:
        """Generate YADE Python simulation script"""
        
        script_content = f'''#!/usr/bin/env python3
"""
YADE DEM Simulation Script for Blast Fragmentation Analysis
Generated automatically by Drill-Blast System
"""

import yade
from yade import pack, plot, export, timing
import numpy as np
import json
from pathlib import Path

# Simulation parameters
WORK_DIR = Path("{work_dir}")
OUTPUT_DIR = WORK_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Material properties
PARTICLE_DENSITY = {config.particle_density}
YOUNG_MODULUS = {config.young_modulus}
POISSON_RATIO = {config.poisson_ratio}
FRICTION_ANGLE = {config.friction_angle}
COHESION = {config.cohesion}
TENSILE_STRENGTH = {config.tensile_strength}

# Simulation parameters
GRAVITY = {list(config.gravity)}
DAMPING = {config.damping}
MAX_ITERATIONS = {config.max_iterations}
CONVERGENCE_TOL = {config.convergence_tolerance}

# Particle size distribution
RADIUS_MIN = {config.particle_radius_min}
RADIUS_MAX = {config.particle_radius_max}

def create_rock_mass():
    """Create rock mass using particle packing"""
    
    # Define rock mass geometry from blast plan
    # This is a simplified box for demonstration
    # In practice, this would use the actual bench geometry
    
    rock_bounds = ({geometry.bench_vertices[0] if geometry.bench_vertices else (-25, -25, -25, 25, 25, 25)})
    
    # Create particle packing
    sp = pack.SpherePack()
    
    # Generate random particle sizes following specified distribution
    num_particles = 10000  # Adjust based on desired resolution
    radii = np.random.uniform(RADIUS_MIN, RADIUS_MAX, num_particles)
    
    # Create spherical particles in the rock mass
    pred = pack.inGtsSurface(
        pack.gtsSurface2Facets(pack.gtsBox(rock_bounds)),
        nSurfNodes=1000
    )
    
    sp.makeCloud(
        minCorner=rock_bounds[:3],
        maxCorner=rock_bounds[3:],
        rMean=(RADIUS_MIN + RADIUS_MAX) / 2,
        rRelFuzz=0.3,
        num=num_particles,
        predicate=pred
    )
    
    return sp.toSimulation()

def setup_materials():
    """Setup material properties for DEM simulation"""
    
    # Rock material
    rock_mat = yade.FrictMat(
        young=YOUNG_MODULUS,
        poisson=POISSON_RATIO,
        frictionAngle=np.radians(FRICTION_ANGLE),
        density=PARTICLE_DENSITY,
        label='rock'
    )
    
    # Cohesive contact model for rock bonding
    cohesive_mat = yade.CohFrictMat(
        young=YOUNG_MODULUS,
        poisson=POISSON_RATIO,
        frictionAngle=np.radians(FRICTION_ANGLE),
        density=PARTICLE_DENSITY,
        normalCohesion=COHESION,
        shearCohesion=COHESION,
        momentRotationLaw=True,
        label='cohesive_rock'
    )
    
    yade.O.materials.append([rock_mat, cohesive_mat])

def setup_engines():
    """Setup simulation engines"""
    
    engines = [
        yade.ForceResetter(),
        yade.InsertionSortCollider([yade.Bo1_Sphere_Aabb()]),
        yade.InteractionLoop(
            [yade.Ig2_Sphere_Sphere_ScGeom()],
            [yade.Ip2_CohFrictMat_CohFrictMat_CohFrictPhys()],
            [yade.Law2_ScGeom_CohFrictPhys_CohesionMoment()]
        ),
        yade.NewtonIntegrator(gravity=GRAVITY, damping=DAMPING),
        yade.PyRunner(command='check_convergence()', iterPeriod=1000),
        yade.PyRunner(command='save_data()', iterPeriod=5000)
    ]
    
    yade.O.engines = engines

def apply_blast_loading():
    """Apply blast loading to simulate explosive effects"""
    
    # Blast hole positions and charges
    blast_positions = {[list(pos) for pos in geometry.charge_positions] if geometry.charge_positions else []}
    blast_masses = {geometry.charge_masses if geometry.charge_masses else []}
    
    for pos, mass in zip(blast_positions, blast_masses):
        # Calculate blast radius and pressure
        blast_radius = (mass / 1000) ** (1/3) * 10  # Empirical scaling
        blast_pressure = mass * 1e6  # Simplified pressure calculation
        
        # Apply radial forces to particles within blast radius
        for body in yade.O.bodies:
            if isinstance(body.shape, yade.Sphere):
                particle_pos = body.state.pos
                distance = np.linalg.norm(np.array(particle_pos) - np.array(pos))
                
                if distance < blast_radius:
                    # Calculate radial force
                    direction = (np.array(particle_pos) - np.array(pos)) / distance
                    force_magnitude = blast_pressure * np.exp(-distance / blast_radius)
                    force = direction * force_magnitude
                    
                    # Apply force to particle
                    body.state.vel += yade.Vector3(force[0], force[1], force[2]) / body.material.density

def check_convergence():
    """Check simulation convergence"""
    global convergence_achieved
    
    if yade.O.iter > MAX_ITERATIONS:
        print(f"Maximum iterations reached: {{yade.O.iter}}")
        yade.O.pause()
        return
    
    # Check kinetic energy convergence
    kinetic_energy = yade.kineticEnergy()
    if kinetic_energy < CONVERGENCE_TOL:
        print(f"Convergence achieved at iteration {{yade.O.iter}}")
        convergence_achieved = True
        yade.O.pause()

def save_data():
    """Save simulation data periodically"""
    
    # Save particle positions and properties
    particle_data = []
    for body in yade.O.bodies:
        if isinstance(body.shape, yade.Sphere):
            particle_data.append({{
                'id': body.id,
                'position': list(body.state.pos),
                'radius': body.shape.radius,
                'velocity': list(body.state.vel),
                'force': list(body.state.force) if hasattr(body.state, 'force') else [0, 0, 0]
            }})
    
    # Save to JSON file
    output_file = OUTPUT_DIR / f"particles_{{yade.O.iter:06d}}.json"
    with open(output_file, 'w') as f:
        json.dump(particle_data, f, indent=2)

def analyze_fragmentation():
    """Analyze final fragmentation state"""
    
    # Collect fragment sizes
    fragment_sizes = []
    for body in yade.O.bodies:
        if isinstance(body.shape, yade.Sphere):
            fragment_sizes.append(body.shape.radius * 2)  # Diameter
    
    fragment_sizes = np.array(fragment_sizes)
    
    # Calculate size distribution statistics
    p10 = np.percentile(fragment_sizes, 10)
    p50 = np.percentile(fragment_sizes, 50)
    p80 = np.percentile(fragment_sizes, 80)
    mean_size = np.mean(fragment_sizes)
    
    # Save fragmentation results
    fragmentation_results = {{
        'fragment_sizes': fragment_sizes.tolist(),
        'statistics': {{
            'P10': float(p10),
            'P50': float(p50),
            'P80': float(p80),
            'mean': float(mean_size),
            'count': len(fragment_sizes)
        }}
    }}
    
    with open(OUTPUT_DIR / "fragmentation_results.json", 'w') as f:
        json.dump(fragmentation_results, f, indent=2)
    
    return fragmentation_results

def main():
    """Main simulation function"""
    
    print("Starting YADE DEM simulation...")
    
    # Initialize simulation
    yade.O.reset()
    
    # Setup materials and engines
    setup_materials()
    setup_engines()
    
    # Create rock mass
    print("Creating rock mass...")
    create_rock_mass()
    
    # Apply blast loading
    print("Applying blast loading...")
    apply_blast_loading()
    
    # Run simulation
    print("Running simulation...")
    global convergence_achieved
    convergence_achieved = False
    
    yade.O.run()
    yade.O.wait()
    
    # Analyze results
    print("Analyzing fragmentation...")
    results = analyze_fragmentation()
    
    print(f"Simulation completed. P80 = {{results['statistics']['P80']:.2f}} m")
    
    # Save final state
    yade.export.text(OUTPUT_DIR / "final_state.txt")
    
    return results

if __name__ == "__main__":
    results = main()
'''
        
        script_path = work_dir / "yade_simulation.py"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        return script_path
    
    def _run_yade_simulation(self, script_path: Path, work_dir: Path) -> Tuple[bool, Dict[str, Path]]:
        """Run YADE simulation script"""
        try:
            # Determine YADE executable
            yade_cmd = self.config.yade_executable or "yade"
            
            # Run simulation
            result = subprocess.run(
                [yade_cmd, str(script_path)],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )
            
            if result.returncode != 0:
                logger.error(f"YADE simulation failed: {result.stderr}")
                return False, {}
            
            # Collect output files
            results_dir = work_dir / "results"
            output_files = {}
            
            if results_dir.exists():
                for file_path in results_dir.iterdir():
                    if file_path.is_file():
                        output_files[file_path.stem] = file_path
            
            logger.info("YADE simulation completed successfully")
            return True, output_files
            
        except subprocess.TimeoutExpired:
            logger.error("YADE simulation timed out")
            return False, {}
        except Exception as e:
            logger.error(f"YADE simulation failed: {e}")
            return False, {}
    
    def _parse_yade_results(self, output_files: Dict[str, Path], geometry: MeshGeometry) -> SimulationResult:
        """Parse YADE simulation results"""
        
        result = SimulationResult(
            simulation_type=SimulationType.YADE,
            success=True,
            runtime_seconds=0.0  # Will be set by caller
        )
        
        try:
            # Parse fragmentation results
            if "fragmentation_results" in output_files:
                with open(output_files["fragmentation_results"], 'r') as f:
                    frag_data = json.load(f)
                
                result.fragment_sizes = np.array(frag_data["fragment_sizes"])
                result.fragment_size_distribution = frag_data["statistics"]
            
            # Parse particle data for PPV estimation
            # This is a simplified approach - in practice, you would need
            # to track particle velocities at receptor locations
            particle_files = [f for f in output_files.keys() if f.startswith("particles_")]
            
            if particle_files:
                # Use the final particle state
                final_file = max(particle_files, key=lambda x: int(x.split('_')[1]))
                
                with open(output_files[final_file], 'r') as f:
                    particle_data = json.load(f)
                
                # Estimate PPV from particle velocities
                # This is a simplified calculation
                max_velocities = []
                for particle in particle_data:
                    velocity = np.array(particle["velocity"])
                    max_velocities.append(np.linalg.norm(velocity))
                
                if max_velocities:
                    estimated_ppv = max(max_velocities) * 1000  # Convert to mm/s
                    
                    # Assign to all receptors (simplified)
                    result.ppv_predictions = {
                        f"receptor_{i}": estimated_ppv 
                        for i in range(len(geometry.charge_positions) or 1)
                    }
            
            # Add simulation metrics
            result.convergence_metrics = {
                "particles_simulated": len(particle_data) if 'particle_data' in locals() else 0,
                "final_iteration": 0  # Would be extracted from simulation log
            }
            
        except Exception as e:
            logger.error(f"Failed to parse YADE results: {e}")
            result.success = False
            result.errors.append(f"Result parsing failed: {str(e)}")
        
        return result
    
    def generate_installation_guide(self) -> str:
        """Generate installation guide for YADE"""
        
        guide = """
# YADE Installation Guide

YADE (Yet Another Dynamic Engine) is a discrete element method (DEM) platform.
Follow these steps to install YADE for blast fragmentation simulation:

## Prerequisites

1. **System Requirements**
   - Linux (Ubuntu 20.04+ recommended)
   - Python 3.8+
   - GCC 9+ or Clang 10+
   - CMake 3.12+
   - Qt5 development libraries
   - Boost libraries (1.71+)
   - Eigen3
   - VTK (optional, for visualization)

2. **Install Dependencies (Ubuntu/Debian)**
   ```bash
   sudo apt update
   sudo apt install cmake git build-essential
   sudo apt install libboost-all-dev libeigen3-dev
   sudo apt install qtbase5-dev qttools5-dev-tools
   sudo apt install python3-dev python3-pip python3-numpy
   sudo apt install libvtk9-dev python3-vtk9  # Optional
   ```

## YADE Installation

### Option 1: Package Installation (Recommended)

1. **Ubuntu/Debian**
   ```bash
   sudo apt install yade
   ```

2. **Verify Installation**
   ```bash
   yade --version
   python3 -c "import yade; print('YADE available')"
   ```

### Option 2: Source Installation

1. **Download Source Code**
   ```bash
   git clone https://github.com/yade/trunk.git yade
   cd yade
   ```

2. **Configure Build**
   ```bash
   mkdir build
   cd build
   cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
   ```

3. **Compile and Install**
   ```bash
   make -j$(nproc)
   sudo make install
   ```

4. **Setup Environment**
   Add to ~/.bashrc:
   ```bash
   export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH
   export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
   ```

## Python Dependencies

Install additional Python packages:
```bash
pip3 install numpy scipy matplotlib
pip3 install vtk  # Optional, for advanced visualization
```

## Configuration

1. **Test YADE Installation**
   ```bash
   yade --test
   ```

2. **Run Example Simulation**
   ```bash
   yade -x
   # In YADE console:
   from yade import pack
   O.bodies.append(pack.regularHexa(pack.inSphere((0,0,0),1),radius=.1,gap=0))
   O.engines=[ForceResetter(),InsertionSortCollider([Bo1_Sphere_Aabb()]),InteractionLoop([Ig2_Sphere_Sphere_ScGeom()],[Ip2_FrictMat_FrictMat_FrictPhys()],[Law2_ScGeom_FrictPhys_CundallStrack()]),NewtonIntegrator(gravity=(0,0,-9.81),damping=0.4)]
   O.run(1000,True)
   ```

## Integration with Drill-Blast System

1. **Update Configuration**
   Set the YADE path in your system configuration:
   ```python
   config = YadeConfig(
       yade_executable="/usr/bin/yade",  # or custom path
       enabled=True
   )
   ```

2. **Verify Integration**
   The system will automatically detect YADE availability and enable
   DEM-based fragmentation analysis in the simulation options.

## Performance Optimization

1. **Parallel Execution**
   YADE supports OpenMP parallelization:
   ```bash
   export OMP_NUM_THREADS=4
   yade simulation_script.py
   ```

2. **Memory Management**
   For large simulations, monitor memory usage:
   ```bash
   yade --debug simulation_script.py
   ```

## Troubleshooting

- **Import Errors**: Ensure PYTHONPATH includes YADE installation directory
- **Compilation Issues**: Check all dependencies are installed
- **Runtime Errors**: Verify particle parameters are physically reasonable
- **Performance Issues**: Reduce particle count or increase time step

## Advanced Features

1. **Custom Contact Laws**
   Implement specialized fracture mechanics models

2. **Visualization**
   Use built-in Qt interface or export to ParaView

3. **Scripting**
   Create custom Python scripts for specific blast scenarios

For detailed documentation, visit: https://yade-dem.org/doc/
"""
        return guide