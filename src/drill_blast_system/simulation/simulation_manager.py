"""
Simulation Manager

Coordinates high-fidelity simulation tools (blastFoam, YADE) with the physics-based models.
Provides a unified interface for running simulations and comparing results.
"""

import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid

from .data_structures import (
    SimulationType, SimulationConfig, SimulationResult, 
    SimulationJob, MeshGeometry, BlastFoamConfig, YadeConfig
)
from .blastfoam_interface import BlastFoamInterface
from .yade_interface import YadeInterface
from ..physics_models.kuz_ram import KuzRamModel
from ..physics_models.ppv import PPVModel
from ..physics_models.fragmentation_curve import FragmentationCurve

logger = logging.getLogger(__name__)


class SimulationManager:
    """Manages and coordinates different simulation approaches"""
    
    def __init__(self):
        self.blastfoam_interface: Optional[BlastFoamInterface] = None
        self.yade_interface: Optional[YadeInterface] = None
        self.physics_models = {
            'kuz_ram': KuzRamModel(),
            'ppv': PPVModel()
        }
        self.active_jobs: Dict[str, SimulationJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def configure_blastfoam(self, config: BlastFoamConfig):
        """Configure blastFoam interface"""
        self.blastfoam_interface = BlastFoamInterface(config)
        logger.info(f"blastFoam configured, available: {self.blastfoam_interface.is_available}")
    
    def configure_yade(self, config: YadeConfig):
        """Configure YADE interface"""
        self.yade_interface = YadeInterface(config)
        logger.info(f"YADE configured, available: {self.yade_interface.is_available}")
    
    def get_available_simulations(self) -> List[SimulationType]:
        """Get list of available simulation types"""
        available = [SimulationType.PHYSICS_ONLY]  # Always available
        
        if self.blastfoam_interface and self.blastfoam_interface.is_available:
            available.append(SimulationType.BLASTFOAM)
            
        if self.yade_interface and self.yade_interface.is_available:
            available.append(SimulationType.YADE)
            
        return available
    
    def create_simulation_job(self, 
                            simulation_type: SimulationType,
                            geometry: MeshGeometry,
                            config: Optional[SimulationConfig] = None) -> str:
        """Create a new simulation job"""
        
        job_id = str(uuid.uuid4())
        
        # Use appropriate config based on simulation type
        if config is None:
            if simulation_type == SimulationType.BLASTFOAM:
                config = BlastFoamConfig()
            elif simulation_type == SimulationType.YADE:
                config = YadeConfig()
            else:
                config = SimulationConfig(simulation_type=simulation_type)
        
        job = SimulationJob(
            job_id=job_id,
            config=config,
            geometry=geometry,
            created_at=datetime.now().isoformat(),
            status="pending"
        )
        
        self.active_jobs[job_id] = job
        logger.info(f"Created simulation job {job_id} for {simulation_type.value}")
        
        return job_id
    
    async def run_simulation_async(self, job_id: str) -> SimulationResult:
        """Run simulation asynchronously"""
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        job.status = "running"
        job.started_at = datetime.now().isoformat()
        
        try:
            # Run simulation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._run_simulation_sync, 
                job
            )
            
            job.result = result
            job.status = "completed" if result.success else "failed"
            job.completed_at = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Simulation job {job_id} failed: {e}")
            job.status = "failed"
            job.completed_at = datetime.now().isoformat()
            
            error_result = SimulationResult(
                simulation_type=job.config.simulation_type,
                success=False,
                runtime_seconds=0.0,
                errors=[f"Job execution failed: {str(e)}"]
            )
            job.result = error_result
            return error_result
    
    def run_simulation_sync(self, job_id: str) -> SimulationResult:
        """Run simulation synchronously"""
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        return self._run_simulation_sync(job)
    
    def _run_simulation_sync(self, job: SimulationJob) -> SimulationResult:
        """Internal synchronous simulation runner"""
        
        simulation_type = job.config.simulation_type
        
        if simulation_type == SimulationType.BLASTFOAM:
            if not self.blastfoam_interface or not self.blastfoam_interface.is_available:
                return SimulationResult(
                    simulation_type=simulation_type,
                    success=False,
                    runtime_seconds=0.0,
                    errors=["blastFoam not available"]
                )
            return self.blastfoam_interface.run_simulation(job)
            
        elif simulation_type == SimulationType.YADE:
            if not self.yade_interface or not self.yade_interface.is_available:
                return SimulationResult(
                    simulation_type=simulation_type,
                    success=False,
                    runtime_seconds=0.0,
                    errors=["YADE not available"]
                )
            return self.yade_interface.run_simulation(job)
            
        elif simulation_type == SimulationType.PHYSICS_ONLY:
            return self._run_physics_simulation(job)
            
        else:
            return SimulationResult(
                simulation_type=simulation_type,
                success=False,
                runtime_seconds=0.0,
                errors=[f"Unknown simulation type: {simulation_type}"]
            )
    
    def _run_physics_simulation(self, job: SimulationJob) -> SimulationResult:
        """Run physics-based simulation using built-in models"""
        
        start_time = datetime.now()
        
        try:
            geometry = job.geometry
            
            # Calculate fragmentation using Kuz-Ram
            fragmentation_results = {}
            if geometry.charge_masses and geometry.hole_positions:
                
                # Simplified calculation for demonstration
                # In practice, this would use the full blast plan data
                total_charge = sum(geometry.charge_masses)
                rock_volume = 1000.0  # m³ - would be calculated from geometry
                powder_factor = total_charge / rock_volume
                
                # Use Kuz-Ram model
                from ..physics_models.kuz_ram import BlastParameters
                kuz_ram = self.physics_models['kuz_ram']
                
                # Create blast parameters
                blast_params = BlastParameters(
                    powder_factor_kg_per_t=powder_factor,
                    powder_factor_kg_per_m3=powder_factor * 2.7,  # Assuming 2.7 t/m³ density
                    burden=5.0,
                    spacing=5.0,
                    bench_height=10.0,
                    hole_diameter=150.0,  # mm
                    stemming_length=3.0,
                    rock_density=2700.0,
                    explosive_rws=100.0,
                    explosive_density=1200.0
                )
                
                mean_fragment_size = kuz_ram.predict_mean_fragment_size(blast_params)
                
                # Generate fragmentation curve
                frag_curve = FragmentationCurve(
                    mean_size_mm=mean_fragment_size,
                    uniformity_index=1.25,
                    distribution_type="rosin_rammler"
                )
                
                # Get characteristic sizes
                char_sizes = frag_curve.get_characteristic_sizes()
                fragmentation_results = {
                    "P10": char_sizes.get("P10", 0.0),
                    "P50": char_sizes.get("P50", 0.0),
                    "P80": char_sizes.get("P80", 0.0),
                    "mean": mean_fragment_size
                }
            
            # Calculate PPV using empirical model
            ppv_results = {}
            if geometry.charge_positions and geometry.charge_masses:
                ppv_model = self.physics_models['ppv']
                
                # Calculate PPV at each charge location (simplified)
                for i, (pos, mass) in enumerate(zip(geometry.charge_positions, geometry.charge_masses)):
                    # Assume receptor at 100m distance for demonstration
                    distance = 100.0
                    ppv = ppv_model.predict_ppv_single_charge(mass, distance)
                    ppv_results[f"receptor_{i}"] = ppv
            
            result = SimulationResult(
                simulation_type=SimulationType.PHYSICS_ONLY,
                success=True,
                runtime_seconds=(datetime.now() - start_time).total_seconds(),
                ppv_predictions=ppv_results,
                fragment_size_distribution=fragmentation_results
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Physics simulation failed: {e}")
            return SimulationResult(
                simulation_type=SimulationType.PHYSICS_ONLY,
                success=False,
                runtime_seconds=(datetime.now() - start_time).total_seconds(),
                errors=[f"Physics simulation failed: {str(e)}"]
            )
    
    def compare_simulation_results(self, results: List[SimulationResult]) -> Dict[str, any]:
        """Compare results from different simulation approaches"""
        
        if not results:
            return {"error": "No results to compare"}
        
        comparison = {
            "simulation_types": [r.simulation_type.value for r in results],
            "success_rates": [r.success for r in results],
            "runtimes": [r.runtime_seconds for r in results],
            "fragmentation_comparison": {},
            "ppv_comparison": {},
            "performance_metrics": {}
        }
        
        # Compare fragmentation results
        frag_data = {}
        for result in results:
            if result.fragment_size_distribution:
                frag_data[result.simulation_type.value] = result.fragment_size_distribution
        
        if frag_data:
            comparison["fragmentation_comparison"] = frag_data
            
            # Calculate relative differences
            if len(frag_data) > 1:
                physics_result = frag_data.get("physics_only")
                if physics_result:
                    # Create a copy to avoid modifying dict during iteration
                    frag_data_copy = dict(frag_data)
                    for sim_type, data in frag_data_copy.items():
                        if sim_type != "physics_only" and "P80" in data and "P80" in physics_result:
                            relative_diff = (data["P80"] - physics_result["P80"]) / physics_result["P80"] * 100
                            comparison["fragmentation_comparison"][f"{sim_type}_vs_physics_p80_diff_%"] = relative_diff
        
        # Compare PPV results
        ppv_data = {}
        for result in results:
            if result.ppv_predictions:
                ppv_data[result.simulation_type.value] = result.ppv_predictions
        
        if ppv_data:
            comparison["ppv_comparison"] = ppv_data
        
        # Performance metrics
        successful_results = [r for r in results if r.success]
        if successful_results:
            comparison["performance_metrics"] = {
                "fastest_runtime": min(r.runtime_seconds for r in successful_results),
                "slowest_runtime": max(r.runtime_seconds for r in successful_results),
                "average_runtime": sum(r.runtime_seconds for r in successful_results) / len(successful_results),
                "success_rate": len(successful_results) / len(results)
            }
        
        return comparison
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, any]]:
        """Get status of simulation job"""
        if job_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[job_id]
        return {
            "job_id": job.job_id,
            "status": job.status,
            "simulation_type": job.config.simulation_type.value,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "has_result": job.result is not None
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running simulation job"""
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        if job.status == "running":
            # Note: Actual cancellation would require more sophisticated
            # process management for external simulation tools
            job.status = "cancelled"
            logger.info(f"Cancelled simulation job {job_id}")
            return True
        
        return False
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        current_time = datetime.now()
        jobs_to_remove = []
        
        for job_id, job in self.active_jobs.items():
            if job.status in ["completed", "failed", "cancelled"] and job.completed_at:
                completed_time = datetime.fromisoformat(job.completed_at)
                age_hours = (current_time - completed_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up old job {job_id}")
        
        return len(jobs_to_remove)
    
    def get_installation_guides(self) -> Dict[str, str]:
        """Get installation guides for all simulation tools"""
        guides = {}
        
        if self.blastfoam_interface:
            guides["blastfoam"] = self.blastfoam_interface.generate_installation_guide()
        
        if self.yade_interface:
            guides["yade"] = self.yade_interface.generate_installation_guide()
        
        return guides