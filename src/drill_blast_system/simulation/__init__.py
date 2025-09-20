"""
Advanced Simulation Integration Module

This module provides optional integration with high-fidelity simulation tools:
- blastFoam (OpenFOAM-based blast simulation)
- YADE (Discrete Element Method)

These integrations are optional and require separate installation of the simulation tools.
The system will gracefully degrade to physics-based models if simulation tools are not available.
"""

from .blastfoam_interface import BlastFoamInterface, BlastFoamConfig
from .yade_interface import YadeInterface, YadeConfig
from .simulation_manager import SimulationManager
from .data_structures import SimulationResult, SimulationConfig

__all__ = [
    'BlastFoamInterface',
    'BlastFoamConfig', 
    'YadeInterface',
    'YadeConfig',
    'SimulationManager',
    'SimulationResult',
    'SimulationConfig'
]