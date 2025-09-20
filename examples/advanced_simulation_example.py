#!/usr/bin/env python3
"""
Advanced Simulation Integration Example

This example demonstrates how to use the high-fidelity simulation integration
with blastFoam and YADE for detailed blast analysis and fragmentation prediction.

The example shows:
1. Setting up simulation configurations
2. Creating blast geometry
3. Running different simulation types
4. Comparing results between physics models and high-fidelity simulations
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drill_blast_system.simulation.simulation_manager import SimulationManager
from drill_blast_system.simulation.data_structures import (
    SimulationType, BlastFoamConfig, YadeConfig, MeshGeometry
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_example_geometry():
    """Create example blast geometry for simulation"""
    
    # Define bench geometry (simplified rectangular bench)
    bench_vertices = [
        (0, 0, 0),      # Bottom corners
        (50, 0, 0),
        (50, 30, 0),
        (0, 30, 0),
        (0, 0, 15),     # Top corners
        (50, 0, 15),
        (50, 30, 15),
        (0, 30, 15)
    ]
    
    # Define bench faces (simplified)
    bench_faces = [
        [0, 1, 2, 3],   # Bottom face
        [4, 5, 6, 7],   # Top face
        [0, 1, 5, 4],   # Front face
        [2, 3, 7, 6],   # Back face
        [0, 3, 7, 4],   # Left face
        [1, 2, 6, 5]    # Right face
    ]
    
    # Define drill hole pattern (3x3 grid)
    hole_positions = []
    hole_depths = []
    hole_diameters = []
    charge_positions = []
    charge_masses = []
    charge_types = []
    
    # Create 3x3 hole pattern
    for i in range(3):
        for j in range(3):
            x = 10 + i * 15  # 15m spacing
            y = 10 + j * 10  # 10m spacing
            z = 0            # Collar at bench top
            
            # Hole parameters
            hole_positions.append((x, y, z))
            hole_depths.append(18.0)  # 3m subdrill
            hole_diameters.append(0.15)  # 150mm diameter
            
            # Charge parameters (charge at bottom of hole)
            charge_positions.append((x, y, z - 15))  # 15m down from collar
            charge_masses.append(30.0)  # 30kg charge
            charge_types.append("ANFO")
    
    return MeshGeometry(
        bench_vertices=bench_vertices,
        bench_faces=bench_faces,
        hole_positions=hole_positions,
        hole_depths=hole_depths,
        hole_diameters=hole_diameters,
        charge_positions=charge_positions,
        charge_masses=charge_masses,
        charge_types=charge_types
    )


def setup_simulation_configs():
    """Setup configurations for different simulation types"""
    
    # blastFoam configuration
    blastfoam_config = BlastFoamConfig(
        enabled=True,
        mesh_resolution=1.0,  # 1m mesh resolution
        simulation_time=0.05,  # 50ms simulation
        time_step=1e-6,       # 1 microsecond time step
        parallel_processes=4,  # Use 4 CPU cores
        explosive_density=1200.0,  # kg/m³
        detonation_velocity=6000.0,  # m/s
        chapman_jouguet_pressure=21e9  # Pa
    )
    
    # YADE configuration
    yade_config = YadeConfig(
        enabled=True,
        particle_radius_min=0.02,  # 2cm minimum particle
        particle_radius_max=0.1,   # 10cm maximum particle
        particle_density=2700.0,   # kg/m³ (granite)
        young_modulus=70e9,        # Pa
        poisson_ratio=0.25,
        friction_angle=35.0,       # degrees
        cohesion=5e6,              # Pa
        tensile_strength=10e6,     # Pa
        max_iterations=100000,
        convergence_tolerance=1e-6
    )
    
    return blastfoam_config, yade_config


async def run_simulation_comparison():
    """Run and compare different simulation approaches"""
    
    logger.info("Starting advanced simulation comparison example")
    
    # Create simulation manager
    manager = SimulationManager()
    
    # Setup configurations
    blastfoam_config, yade_config = setup_simulation_configs()
    
    # Configure simulation interfaces
    manager.configure_blastfoam(blastfoam_config)
    manager.configure_yade(yade_config)
    
    # Check what simulations are available
    available_sims = manager.get_available_simulations()
    logger.info(f"Available simulation types: {[sim.value for sim in available_sims]}")
    
    # Create example geometry
    geometry = create_example_geometry()
    logger.info(f"Created blast geometry with {len(geometry.hole_positions)} holes")
    
    # Create simulation jobs for each available type
    job_ids = []
    for sim_type in available_sims:
        if sim_type == SimulationType.BLASTFOAM:
            job_id = manager.create_simulation_job(sim_type, geometry, blastfoam_config)
        elif sim_type == SimulationType.YADE:
            job_id = manager.create_simulation_job(sim_type, geometry, yade_config)
        else:
            job_id = manager.create_simulation_job(sim_type, geometry)
        
        job_ids.append((sim_type, job_id))
        logger.info(f"Created {sim_type.value} simulation job: {job_id}")
    
    # Run simulations
    results = []
    for sim_type, job_id in job_ids:
        logger.info(f"Running {sim_type.value} simulation...")
        
        try:
            result = await manager.run_simulation_async(job_id)
            results.append(result)
            
            if result.success:
                logger.info(f"{sim_type.value} simulation completed successfully")
                logger.info(f"  Runtime: {result.runtime_seconds:.2f} seconds")
                
                if result.fragment_size_distribution:
                    p80 = result.fragment_size_distribution.get("P80", "N/A")
                    logger.info(f"  P80 fragmentation: {p80}")
                
                if result.ppv_predictions:
                    max_ppv = max(result.ppv_predictions.values())
                    logger.info(f"  Maximum PPV: {max_ppv:.2f} mm/s")
            else:
                logger.warning(f"{sim_type.value} simulation failed: {result.errors}")
                
        except Exception as e:
            logger.error(f"Error running {sim_type.value} simulation: {e}")
    
    # Compare results
    if len(results) > 1:
        logger.info("\nComparing simulation results...")
        comparison = manager.compare_simulation_results(results)
        
        print("\n" + "="*60)
        print("SIMULATION COMPARISON RESULTS")
        print("="*60)
        
        print(f"Simulation types: {comparison['simulation_types']}")
        print(f"Success rates: {comparison['success_rates']}")
        print(f"Runtimes (s): {[f'{t:.2f}' for t in comparison['runtimes']]}")
        
        if comparison.get('fragmentation_comparison'):
            print("\nFragmentation Results:")
            for sim_type, frag_data in comparison['fragmentation_comparison'].items():
                if isinstance(frag_data, dict) and 'P80' in frag_data:
                    print(f"  {sim_type}: P80 = {frag_data['P80']:.1f} mm")
        
        if comparison.get('ppv_comparison'):
            print("\nPPV Results:")
            for sim_type, ppv_data in comparison['ppv_comparison'].items():
                if isinstance(ppv_data, dict):
                    max_ppv = max(ppv_data.values()) if ppv_data else 0
                    print(f"  {sim_type}: Max PPV = {max_ppv:.2f} mm/s")
        
        if comparison.get('performance_metrics'):
            metrics = comparison['performance_metrics']
            print(f"\nPerformance Metrics:")
            print(f"  Fastest runtime: {metrics['fastest_runtime']:.2f} s")
            print(f"  Slowest runtime: {metrics['slowest_runtime']:.2f} s")
            print(f"  Average runtime: {metrics['average_runtime']:.2f} s")
            print(f"  Success rate: {metrics['success_rate']:.1%}")
    
    # Show job statuses
    print("\n" + "="*60)
    print("JOB STATUS SUMMARY")
    print("="*60)
    
    for sim_type, job_id in job_ids:
        status = manager.get_job_status(job_id)
        if status:
            print(f"{sim_type.value}:")
            print(f"  Job ID: {status['job_id']}")
            print(f"  Status: {status['status']}")
            print(f"  Created: {status['created_at']}")
            print(f"  Has result: {status['has_result']}")
    
    # Clean up old jobs
    cleaned = manager.cleanup_completed_jobs(max_age_hours=0)  # Clean all completed jobs
    logger.info(f"Cleaned up {cleaned} completed jobs")


def show_installation_guides():
    """Show installation guides for simulation tools"""
    
    manager = SimulationManager()
    
    # Configure interfaces to get installation guides
    manager.configure_blastfoam(BlastFoamConfig())
    manager.configure_yade(YadeConfig())
    
    guides = manager.get_installation_guides()
    
    print("\n" + "="*80)
    print("INSTALLATION GUIDES")
    print("="*80)
    
    for tool_name, guide in guides.items():
        print(f"\n{tool_name.upper()} INSTALLATION GUIDE:")
        print("-" * 40)
        print(guide)


def main():
    """Main example function"""
    
    print("Advanced Simulation Integration Example")
    print("="*50)
    
    # Show available simulation types
    manager = SimulationManager()
    available = manager.get_available_simulations()
    
    print(f"Available simulation types: {[sim.value for sim in available]}")
    
    if len(available) == 1 and available[0] == SimulationType.PHYSICS_ONLY:
        print("\nNote: Only physics-based simulation is available.")
        print("To enable high-fidelity simulations, install blastFoam and/or YADE.")
        print("Use --guides option to see installation instructions.")
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--guides":
        show_installation_guides()
        return
    
    # Run simulation comparison
    try:
        asyncio.run(run_simulation_comparison())
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    main()