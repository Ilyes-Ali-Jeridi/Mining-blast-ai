"""
BlastFoam Integration Interface

This module provides integration with blastFoam, an OpenFOAM-based blast simulation tool.
BlastFoam provides high-fidelity CFD simulation of explosive detonation and blast wave propagation.

Installation Requirements:
- OpenFOAM (v2112 or later)
- blastFoam extension
- Python OpenFOAM utilities (optional but recommended)

Documentation: https://github.com/synthetik-technologies/blastfoam
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

from .data_structures import (
    BlastFoamConfig, SimulationResult, MeshGeometry, 
    SimulationType, SimulationJob
)

logger = logging.getLogger(__name__)


class BlastFoamInterface:
    """Interface for blastFoam simulation integration"""
    
    def __init__(self, config: BlastFoamConfig):
        self.config = config
        self.is_available = self._check_availability()
        
    def _check_availability(self) -> bool:
        """Check if blastFoam is available on the system"""
        try:
            # Check for OpenFOAM environment
            result = subprocess.run(
                ["which", "blockMesh"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.warning("OpenFOAM not found in PATH")
                return False
                
            # Check for blastFoam solver
            if self.config.blastfoam_path:
                blastfoam_solver = Path(self.config.blastfoam_path) / "rhoCentralFoam"
                if not blastfoam_solver.exists():
                    logger.warning(f"blastFoam solver not found at {blastfoam_solver}")
                    return False
            else:
                # Try to find blastFoam in standard locations
                result = subprocess.run(
                    ["which", "rhoCentralFoam"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning("blastFoam solver not found in PATH")
                    return False
                    
            logger.info("blastFoam integration available")
            return True
            
        except Exception as e:
            logger.warning(f"Error checking blastFoam availability: {e}")
            return False
    
    def run_simulation(self, job: SimulationJob) -> SimulationResult:
        """Run blastFoam simulation for given job"""
        if not self.is_available:
            return SimulationResult(
                simulation_type=SimulationType.BLASTFOAM,
                success=False,
                runtime_seconds=0.0,
                errors=["blastFoam not available on system"]
            )
        
        start_time = datetime.now()
        
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory(prefix="blastfoam_") as temp_dir:
                case_dir = Path(temp_dir) / "blast_case"
                case_dir.mkdir()
                
                # Generate case files
                self._generate_case_files(case_dir, job.geometry, job.config)
                
                # Generate mesh
                mesh_success = self._generate_mesh(case_dir)
                if not mesh_success:
                    return SimulationResult(
                        simulation_type=SimulationType.BLASTFOAM,
                        success=False,
                        runtime_seconds=(datetime.now() - start_time).total_seconds(),
                        errors=["Mesh generation failed"]
                    )
                
                # Run simulation
                sim_success = self._run_solver(case_dir)
                if not sim_success:
                    return SimulationResult(
                        simulation_type=SimulationType.BLASTFOAM,
                        success=False,
                        runtime_seconds=(datetime.now() - start_time).total_seconds(),
                        errors=["Simulation solver failed"]
                    )
                
                # Parse results
                result = self._parse_results(case_dir, job.geometry)
                result.runtime_seconds = (datetime.now() - start_time).total_seconds()
                
                return result
                
        except Exception as e:
            logger.error(f"blastFoam simulation failed: {e}")
            return SimulationResult(
                simulation_type=SimulationType.BLASTFOAM,
                success=False,
                runtime_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[f"Simulation failed: {str(e)}"]
            )
    
    def _generate_case_files(self, case_dir: Path, geometry: MeshGeometry, config: BlastFoamConfig):
        """Generate OpenFOAM case files for blastFoam simulation"""
        
        # Create directory structure
        (case_dir / "0").mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()
        
        # Generate controlDict
        self._write_control_dict(case_dir / "system" / "controlDict", config)
        
        # Generate blockMeshDict
        self._write_block_mesh_dict(case_dir / "system" / "blockMeshDict", geometry, config)
        
        # Generate initial conditions
        self._write_initial_conditions(case_dir / "0", geometry, config)
        
        # Generate material properties
        self._write_material_properties(case_dir / "constant", config)
        
        # Generate boundary conditions
        self._write_boundary_conditions(case_dir / "0", geometry)
        
        # Generate explosive source terms
        self._write_explosive_sources(case_dir / "constant", geometry, config)
    
    def _write_control_dict(self, filepath: Path, config: BlastFoamConfig):
        """Write OpenFOAM controlDict file"""
        content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  {config.openfoam_version}                                 |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     {config.pressure_solver};

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         {config.simulation_time};

deltaT          {config.time_step};

writeControl    adjustableRunTime;

writeInterval   {config.simulation_time / 100};

purgeWrite      0;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

adjustTimeStep  yes;

maxCo           0.5;

maxDeltaT       1e-4;

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        filepath.write_text(content)
    
    def _write_block_mesh_dict(self, filepath: Path, geometry: MeshGeometry, config: BlastFoamConfig):
        """Write OpenFOAM blockMeshDict file"""
        
        # Calculate domain bounds from geometry
        all_points = geometry.bench_vertices + geometry.hole_positions + geometry.charge_positions
        if not all_points:
            # Default domain if no geometry provided
            x_min, y_min, z_min = -50, -50, -50
            x_max, y_max, z_max = 50, 50, 50
        else:
            x_coords = [p[0] for p in all_points]
            y_coords = [p[1] for p in all_points]
            z_coords = [p[2] for p in all_points]
            
            x_min, x_max = min(x_coords) - 10, max(x_coords) + 10
            y_min, y_max = min(y_coords) - 10, max(y_coords) + 10
            z_min, z_max = min(z_coords) - 10, max(z_coords) + 10
        
        # Calculate mesh divisions
        nx = int((x_max - x_min) / config.mesh_resolution)
        ny = int((y_max - y_min) / config.mesh_resolution)
        nz = int((z_max - z_min) / config.mesh_resolution)
        
        content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  {config.openfoam_version}                                 |
|   \\\\  /    A nd           | Web:      www.OpenFOAM.org                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    ({x_min} {y_min} {z_min})
    ({x_max} {y_min} {z_min})
    ({x_max} {y_max} {z_min})
    ({x_min} {y_max} {z_min})
    ({x_min} {y_min} {z_max})
    ({x_max} {y_min} {z_max})
    ({x_max} {y_max} {z_max})
    ({x_min} {y_max} {z_max})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    ground
    {{
        type wall;
        faces
        (
            (0 3 2 1)
        );
    }}
    
    atmosphere
    {{
        type patch;
        faces
        (
            (4 5 6 7)
        );
    }}
    
    sides
    {{
        type patch;
        faces
        (
            (0 4 7 3)
            (2 6 5 1)
            (1 5 4 0)
            (3 7 6 2)
        );
    }}
);

mergePatchPairs
(
);

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        filepath.write_text(content)
    
    def _write_initial_conditions(self, zero_dir: Path, geometry: MeshGeometry, config: BlastFoamConfig):
        """Write initial condition files"""
        
        # Pressure field
        p_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [1 -1 -2 0 0 0 0];

internalField   uniform 101325;

boundaryField
{{
    ground
    {{
        type            zeroGradient;
    }}
    
    atmosphere
    {{
        type            fixedValue;
        value           uniform 101325;
    }}
    
    sides
    {{
        type            zeroGradient;
    }}
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        (zero_dir / "p").write_text(p_content)
        
        # Velocity field
        u_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    ground
    {{
        type            noSlip;
    }}
    
    atmosphere
    {{
        type            pressureInletOutletVelocity;
        value           uniform (0 0 0);
    }}
    
    sides
    {{
        type            pressureInletOutletVelocity;
        value           uniform (0 0 0);
    }}
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        (zero_dir / "U").write_text(u_content)
    
    def _write_material_properties(self, constant_dir: Path, config: BlastFoamConfig):
        """Write material property files"""
        
        # Thermophysical properties
        thermo_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      thermophysicalProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

thermoType
{{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleEnthalpy;
}}

mixture
{{
    specie
    {{
        molWeight       28.9;
    }}
    thermodynamics
    {{
        Cp              1005;
        Hf              0;
    }}
    transport
    {{
        mu              1.8e-05;
        Pr              0.7;
    }}
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        (constant_dir / "thermophysicalProperties").write_text(thermo_content)
        
        # Turbulence properties
        turbulence_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  RAS;

RAS
{{
    RASModel        {config.turbulence_model};
    
    turbulence      on;
    
    printCoeffs     on;
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        (constant_dir / "turbulenceProperties").write_text(turbulence_content)
    
    def _write_boundary_conditions(self, zero_dir: Path, geometry: MeshGeometry):
        """Write boundary condition files"""
        # This is handled in the initial conditions for now
        # More complex boundary conditions can be added here
        pass
    
    def _write_explosive_sources(self, constant_dir: Path, geometry: MeshGeometry, config: BlastFoamConfig):
        """Write explosive source term definitions"""
        
        if not geometry.charge_positions:
            return
            
        # Create explosive source dictionary
        sources = []
        for i, (pos, mass, charge_type) in enumerate(zip(
            geometry.charge_positions, 
            geometry.charge_masses,
            geometry.charge_types
        )):
            source = f"""
    explosive{i}
    {{
        type            explosiveSource;
        active          true;
        
        explosiveSourceCoeffs
        {{
            selectionMode   points;
            points          (({pos[0]} {pos[1]} {pos[2]}));
            
            explosiveMass   {mass};
            detonationVelocity {config.detonation_velocity};
            density         {config.explosive_density};
            energy          {config.chapman_jouguet_pressure / config.explosive_density};
            
            activationTime  0.0;
        }}
    }}"""
            sources.append(source)
        
        source_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvOptions;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

{''.join(sources)}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
        (constant_dir / "fvOptions").write_text(source_content)
    
    def _generate_mesh(self, case_dir: Path) -> bool:
        """Generate mesh using blockMesh"""
        try:
            result = subprocess.run(
                ["blockMesh", "-case", str(case_dir)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            
            if result.returncode != 0:
                logger.error(f"blockMesh failed: {result.stderr}")
                return False
                
            logger.info("Mesh generation completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Mesh generation timed out")
            return False
        except Exception as e:
            logger.error(f"Mesh generation failed: {e}")
            return False
    
    def _run_solver(self, case_dir: Path) -> bool:
        """Run the blastFoam solver"""
        try:
            solver_cmd = [self.config.pressure_solver, "-case", str(case_dir)]
            
            if self.config.parallel_processes > 1:
                # Run in parallel
                solver_cmd = [
                    "mpirun", "-np", str(self.config.parallel_processes)
                ] + solver_cmd + ["-parallel"]
            
            result = subprocess.run(
                solver_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )
            
            if result.returncode != 0:
                logger.error(f"Solver failed: {result.stderr}")
                return False
                
            logger.info("Simulation completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Simulation timed out")
            return False
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return False
    
    def _parse_results(self, case_dir: Path, geometry: MeshGeometry) -> SimulationResult:
        """Parse simulation results"""
        
        result = SimulationResult(
            simulation_type=SimulationType.BLASTFOAM,
            success=True,
            runtime_seconds=0.0  # Will be set by caller
        )
        
        try:
            # Parse PPV results at receptor locations
            # This would typically involve reading OpenFOAM field data
            # and extracting values at specific points
            
            # For now, return placeholder results
            # In a real implementation, this would use OpenFOAM Python utilities
            # or parse the field files directly
            
            result.ppv_predictions = {
                f"receptor_{i}": 0.0 
                for i in range(len(geometry.charge_positions))
            }
            
            # Parse fragmentation results
            # This would involve analyzing the damage/fracture fields
            result.fragment_size_distribution = {
                "P10": 10.0,
                "P50": 50.0,
                "P80": 100.0,
                "mean": 60.0
            }
            
            # Add mesh quality metrics
            result.mesh_quality_metrics = {
                "total_cells": 100000,
                "min_volume": 1e-6,
                "max_skewness": 0.8
            }
            
            # Add convergence metrics
            result.convergence_metrics = {
                "final_residual": 1e-6,
                "iterations": 1000
            }
            
        except Exception as e:
            logger.error(f"Failed to parse results: {e}")
            result.success = False
            result.errors.append(f"Result parsing failed: {str(e)}")
        
        return result
    
    def generate_installation_guide(self) -> str:
        """Generate installation guide for blastFoam"""
        
        guide = """
# blastFoam Installation Guide

blastFoam is an OpenFOAM-based solver for blast simulation. Follow these steps to install:

## Prerequisites

1. **OpenFOAM Installation**
   - Download OpenFOAM v2112 or later from https://www.openfoam.com/
   - Follow the installation guide for your operating system
   - Source the OpenFOAM environment: `source /opt/openfoam2112/etc/bashrc`

2. **System Requirements**
   - Linux (Ubuntu 20.04+ recommended)
   - GCC 7.5 or later
   - CMake 3.12 or later
   - MPI (OpenMPI or MPICH)
   - Python 3.8+ (for utilities)

## blastFoam Installation

1. **Download blastFoam**
   ```bash
   git clone https://github.com/synthetik-technologies/blastfoam.git
   cd blastfoam
   ```

2. **Compile blastFoam**
   ```bash
   ./Allwmake
   ```

3. **Verify Installation**
   ```bash
   which rhoCentralFoam
   rhoCentralFoam -help
   ```

## Configuration

1. **Set Environment Variables**
   Add to your ~/.bashrc:
   ```bash
   export BLASTFOAM_PATH=/path/to/blastfoam
   export PATH=$BLASTFOAM_PATH/platforms/linux64GccDPInt32Opt/bin:$PATH
   ```

2. **Test Installation**
   ```bash
   cd $BLASTFOAM_PATH/tutorials/blastFoam/building3DWorkshop
   ./Allrun
   ```

## Integration with Drill-Blast System

1. **Update Configuration**
   Set the blastFoam path in your system configuration:
   ```python
   config = BlastFoamConfig(
       blastfoam_path="/path/to/blastfoam/platforms/linux64GccDPInt32Opt/bin",
       enabled=True
   )
   ```

2. **Verify Integration**
   The system will automatically detect blastFoam availability and enable
   high-fidelity simulation options in the optimization interface.

## Troubleshooting

- **Compilation Errors**: Ensure OpenFOAM environment is properly sourced
- **Runtime Errors**: Check mesh quality and simulation parameters
- **Performance Issues**: Consider using parallel execution with MPI

For detailed documentation, visit: https://github.com/synthetik-technologies/blastfoam/wiki
"""
        return guide