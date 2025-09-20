# Advanced Simulation Integration

This module provides optional integration with high-fidelity simulation tools for enhanced blast analysis and fragmentation prediction. The system gracefully degrades to physics-based models when simulation tools are not available.

## Overview

The simulation integration supports three approaches:

1. **Physics-Only** (always available): Uses established physics models (Kuz-Ram, empirical PPV)
2. **blastFoam** (optional): OpenFOAM-based CFD simulation for blast wave propagation
3. **YADE** (optional): Discrete Element Method (DEM) for particle-based fragmentation modeling

## Architecture

```
SimulationManager
├── BlastFoamInterface (optional)
├── YadeInterface (optional)
└── Physics Models (always available)
    ├── Kuz-Ram fragmentation
    └── Empirical PPV
```

## Usage

### Basic Usage

```python
from drill_blast_system.simulation import SimulationManager, SimulationType
from drill_blast_system.simulation.data_structures import MeshGeometry

# Create simulation manager
manager = SimulationManager()

# Create blast geometry
geometry = MeshGeometry(
    bench_vertices=[(0,0,0), (50,0,0), (50,30,0), (0,30,0)],
    charge_positions=[(10,10,-8), (25,10,-8), (40,10,-8)],
    charge_masses=[30.0, 30.0, 30.0],
    charge_types=["ANFO", "ANFO", "ANFO"]
)

# Create and run simulation job
job_id = manager.create_simulation_job(SimulationType.PHYSICS_ONLY, geometry)
result = manager.run_simulation_sync(job_id)

print(f"P80 fragmentation: {result.fragment_size_distribution['P80']} mm")
```

### Advanced Usage with High-Fidelity Simulations

```python
import asyncio
from drill_blast_system.simulation import BlastFoamConfig, YadeConfig

# Configure high-fidelity simulations
blastfoam_config = BlastFoamConfig(
    mesh_resolution=0.5,
    simulation_time=0.1,
    parallel_processes=4
)

yade_config = YadeConfig(
    particle_radius_min=0.01,
    particle_radius_max=0.1,
    max_iterations=100000
)

manager.configure_blastfoam(blastfoam_config)
manager.configure_yade(yade_config)

# Run multiple simulations and compare
async def compare_simulations():
    jobs = []
    for sim_type in manager.get_available_simulations():
        job_id = manager.create_simulation_job(sim_type, geometry)
        jobs.append((sim_type, job_id))
    
    results = []
    for sim_type, job_id in jobs:
        result = await manager.run_simulation_async(job_id)
        results.append(result)
    
    comparison = manager.compare_simulation_results(results)
    return comparison

# Run comparison
comparison = asyncio.run(compare_simulations())
```

## Simulation Types

### Physics-Only Simulation

Always available, uses established engineering models:

- **Fragmentation**: Kuz-Ram model with Rosin-Rammler distribution
- **PPV**: Empirical scaled charge model (PPV = k * W^a / R^b)
- **Runtime**: < 1 second
- **Accuracy**: Good for preliminary design

### blastFoam Simulation

High-fidelity CFD simulation using OpenFOAM:

- **Fragmentation**: Damage field analysis
- **PPV**: Direct pressure wave simulation
- **Runtime**: Minutes to hours
- **Accuracy**: High for blast wave propagation

**Requirements**:
- OpenFOAM v2112+
- blastFoam extension
- Linux environment recommended

### YADE Simulation

Discrete Element Method for particle-based modeling:

- **Fragmentation**: Particle fracture mechanics
- **PPV**: Particle velocity analysis
- **Runtime**: Minutes to hours
- **Accuracy**: High for fragmentation analysis

**Requirements**:
- YADE 1.20.0+
- Python bindings
- Sufficient memory for particle simulation

## Configuration

### BlastFoam Configuration

```python
config = BlastFoamConfig(
    enabled=True,
    mesh_resolution=1.0,        # meters
    simulation_time=0.05,       # seconds
    time_step=1e-6,            # seconds
    parallel_processes=4,       # CPU cores
    explosive_density=1200.0,   # kg/m³
    detonation_velocity=6000.0, # m/s
    timeout_seconds=3600        # 1 hour
)
```

### YADE Configuration

```python
config = YadeConfig(
    enabled=True,
    particle_radius_min=0.01,   # meters
    particle_radius_max=0.1,    # meters
    particle_density=2700.0,    # kg/m³
    young_modulus=70e9,         # Pa
    poisson_ratio=0.25,
    friction_angle=30.0,        # degrees
    cohesion=1e6,              # Pa
    max_iterations=100000
)
```

## Result Comparison

The system provides detailed comparison between simulation approaches:

```python
comparison = manager.compare_simulation_results(results)

# Access comparison data
print(f"Simulation types: {comparison['simulation_types']}")
print(f"Runtimes: {comparison['runtimes']}")
print(f"Fragmentation results: {comparison['fragmentation_comparison']}")
print(f"PPV results: {comparison['ppv_comparison']}")
print(f"Performance metrics: {comparison['performance_metrics']}")
```

## Installation Guides

The system provides detailed installation guides for simulation tools:

```python
guides = manager.get_installation_guides()
print(guides['blastfoam'])  # blastFoam installation guide
print(guides['yade'])       # YADE installation guide
```

## Error Handling

The system gracefully handles simulation failures:

```python
result = manager.run_simulation_sync(job_id)

if not result.success:
    print(f"Simulation failed: {result.errors}")
    # System automatically falls back to physics models
```

## Performance Considerations

### Memory Usage

- **Physics-Only**: Minimal memory usage
- **blastFoam**: Memory scales with mesh size (O(N) where N = cells)
- **YADE**: Memory scales with particle count (O(N) where N = particles)

### Runtime Scaling

- **Physics-Only**: O(1) - constant time
- **blastFoam**: O(N * T) where N = mesh cells, T = time steps
- **YADE**: O(N² * I) where N = particles, I = iterations

### Parallelization

- **blastFoam**: Supports MPI parallelization
- **YADE**: Supports OpenMP parallelization
- **Physics-Only**: Single-threaded (fast enough)

## Validation and Testing

The simulation interfaces include comprehensive testing:

- Unit tests for all interfaces
- Integration tests with mock simulations
- Validation against known analytical solutions
- Performance benchmarking

Run tests:
```bash
pytest tests/test_blastfoam_interface.py
pytest tests/test_yade_interface.py
pytest tests/test_simulation_manager.py
```

## Troubleshooting

### Common Issues

1. **Simulation tools not found**
   - Check PATH environment variable
   - Verify installation with `which blastfoam` or `which yade`
   - Use absolute paths in configuration

2. **Simulation timeouts**
   - Increase `timeout_seconds` in configuration
   - Reduce mesh resolution or particle count
   - Use parallel processing

3. **Memory issues**
   - Reduce simulation domain size
   - Decrease mesh resolution (blastFoam)
   - Reduce particle count (YADE)

4. **Convergence problems**
   - Check mesh quality (blastFoam)
   - Adjust time step size
   - Verify material properties

### Debug Mode

Enable debug logging for detailed simulation information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run simulation with debug output
result = manager.run_simulation_sync(job_id)
```

## Future Enhancements

Planned improvements:

1. **Additional Simulation Tools**
   - LS-DYNA integration
   - ANSYS Autodyn support
   - Custom solver interfaces

2. **Advanced Features**
   - Adaptive mesh refinement
   - Multi-physics coupling
   - Uncertainty quantification

3. **Performance Optimization**
   - GPU acceleration support
   - Distributed computing
   - Result caching

## References

- [blastFoam Documentation](https://github.com/synthetik-technologies/blastfoam)
- [YADE Documentation](https://yade-dem.org/doc/)
- [OpenFOAM User Guide](https://www.openfoam.com/documentation/user-guide)
- Kuz-Ram fragmentation model references
- Empirical PPV model references