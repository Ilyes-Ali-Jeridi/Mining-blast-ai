"""
API routes for synthetic data generation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
import tempfile
import os
from pathlib import Path

from ...auth.security import get_current_user
from ...ml_pipeline.synthetic_generator import (
    SyntheticDataGenerator,
    RockType,
    ExplosiveType,
    NoiseParameters,
    SyntheticBlastScenario
)
from ...schemas.common import ResponseModel
from ...auth.models import User

router = APIRouter(prefix="/synthetic", tags=["synthetic"])

# Global generator instance
_generator = None

def get_generator() -> SyntheticDataGenerator:
    """Get or create synthetic data generator instance"""
    global _generator
    if _generator is None:
        _generator = SyntheticDataGenerator()
    return _generator


@router.post("/scenarios/generate", response_model=ResponseModel)
async def generate_scenario(
    rock_type: Optional[str] = None,
    noise_level: float = 0.15,
    current_user: User = Depends(get_current_user)
):
    """Generate a single synthetic blast scenario"""
    try:
        generator = get_generator()
        
        # Parse rock type if provided
        rock_type_enum = None
        if rock_type:
            try:
                rock_type_enum = RockType(rock_type.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid rock type: {rock_type}")
        
        # Create noise parameters
        noise_params = NoiseParameters(
            fragmentation_noise=noise_level,
            ppv_noise=noise_level,
            outlier_probability=0.05,
            missing_data_probability=0.02
        )
        
        # Generate site and scenario
        site = generator.generate_random_site(rock_type=rock_type_enum)
        scenario = generator.generate_scenario(site=site, noise_params=noise_params)
        
        # Convert to response format
        scenario_data = {
            "scenario_id": scenario.scenario_id,
            "site": {
                "site_id": scenario.site.site_id,
                "name": scenario.site.name,
                "rock_type": scenario.site.rock_properties.rock_type.value,
                "bench_height": scenario.site.bench_height,
                "bench_width": scenario.site.bench_width,
                "bench_length": scenario.site.bench_length,
                "ucs": scenario.site.rock_properties.ucs,
                "density": scenario.site.rock_properties.density,
                "rock_factor_a": scenario.site.rock_properties.rock_factor_a
            },
            "blast_plan": {
                "plan_id": scenario.blast_plan.plan_id,
                "num_holes": len(scenario.blast_plan.holes),
                "total_charge": scenario.blast_plan.total_charge_kg,
                "powder_factor": scenario.blast_plan.powder_factor_kg_per_t,
                "holes": [
                    {
                        "hole_id": hole.hole_id,
                        "x": hole.coordinates[0],
                        "y": hole.coordinates[1],
                        "z": hole.coordinates[2],
                        "depth": hole.depth,
                        "diameter": hole.diameter,
                        "charge_kg": hole.charge_kg,
                        "delay_ms": hole.delay_ms,
                        "explosive_type": hole.explosive_type,
                        "burden": hole.burden,
                        "spacing": hole.spacing
                    }
                    for hole in scenario.blast_plan.holes[:20]  # Limit for response size
                ]
            },
            "predictions": {
                "fragmentation": {
                    "p10": scenario.true_fragmentation.p10,
                    "p50": scenario.true_fragmentation.p50,
                    "p80": scenario.true_fragmentation.p80,
                    "mean_size": scenario.true_fragmentation.mean_size,
                    "uniformity_index": scenario.true_fragmentation.uniformity_index
                },
                "ppv": scenario.true_ppv
            },
            "measurements": {
                "fragmentation": {
                    "p10": scenario.measured_fragmentation.p10 if scenario.measured_fragmentation else None,
                    "p50": scenario.measured_fragmentation.p50 if scenario.measured_fragmentation else None,
                    "p80": scenario.measured_fragmentation.p80 if scenario.measured_fragmentation else None,
                    "quality": scenario.measured_fragmentation.measurement_quality if scenario.measured_fragmentation else None,
                    "is_valid": scenario.measured_fragmentation.is_valid if scenario.measured_fragmentation else False
                },
                "ppv": scenario.measured_ppv
            },
            "created_at": scenario.created_at.isoformat()
        }
        
        return ResponseModel(
            success=True,
            message="Synthetic scenario generated successfully",
            data=scenario_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate scenario: {str(e)}")


@router.post("/parameter-exploration", response_model=ResponseModel)
async def generate_parameter_exploration(
    num_scenarios: int = Query(50, ge=10, le=200),
    parameter_ranges: Optional[Dict[str, List[float]]] = None,
    current_user: User = Depends(get_current_user)
):
    """Generate scenarios for parameter space exploration"""
    try:
        generator = get_generator()
        
        # Convert parameter ranges format
        ranges = None
        if parameter_ranges:
            ranges = {k: tuple(v) for k, v in parameter_ranges.items()}
        
        scenarios = generator.generate_parameter_space_exploration(
            num_scenarios=num_scenarios,
            parameter_ranges=ranges
        )
        
        # Convert to summary format
        summary_data = []
        for scenario in scenarios:
            summary_data.append({
                "scenario_id": scenario.scenario_id,
                "rock_type": scenario.site.rock_properties.rock_type.value,
                "powder_factor": scenario.blast_plan.powder_factor_kg_per_t,
                "bench_height": scenario.site.bench_height,
                "rock_factor_a": scenario.site.rock_properties.rock_factor_a,
                "true_p80": scenario.true_fragmentation.p80,
                "measured_p80": scenario.measured_fragmentation.p80 if scenario.measured_fragmentation else None,
                "max_ppv": max(scenario.true_ppv.values()) if scenario.true_ppv else 0
            })
        
        return ResponseModel(
            success=True,
            message=f"Generated {len(scenarios)} scenarios for parameter exploration",
            data={
                "scenarios": summary_data,
                "statistics": {
                    "total_scenarios": len(scenarios),
                    "parameter_ranges": ranges or "default"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate parameter exploration: {str(e)}")


@router.post("/benchmark-dataset", response_model=ResponseModel)
async def generate_benchmark_dataset(
    background_tasks: BackgroundTasks,
    num_scenarios: int = Query(100, ge=50, le=1000),
    test_split: float = Query(0.2, ge=0.1, le=0.3),
    validation_split: float = Query(0.1, ge=0.05, le=0.2),
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive benchmark dataset"""
    try:
        generator = get_generator()
        
        # Generate dataset
        dataset = generator.generate_benchmark_dataset(
            num_scenarios=num_scenarios,
            test_split=test_split,
            validation_split=validation_split
        )
        
        # Validate dataset
        all_scenarios = dataset['train'] + dataset['validation'] + dataset['test']
        validation_report = generator.validate_dataset(all_scenarios)
        
        # Create temporary export files
        temp_dir = Path(tempfile.mkdtemp())
        
        # Export datasets in background
        def export_datasets():
            try:
                generator.export_dataset(
                    dataset['train'], 
                    str(temp_dir / "training_dataset.json"), 
                    format='json'
                )
                generator.export_dataset(
                    all_scenarios, 
                    str(temp_dir / "full_dataset.csv"), 
                    format='csv'
                )
            except Exception as e:
                print(f"Export error: {e}")
        
        background_tasks.add_task(export_datasets)
        
        return ResponseModel(
            success=True,
            message=f"Generated benchmark dataset with {len(all_scenarios)} scenarios",
            data={
                "dataset_splits": {
                    "train": len(dataset['train']),
                    "validation": len(dataset['validation']),
                    "test": len(dataset['test'])
                },
                "validation_report": validation_report,
                "export_path": str(temp_dir)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate benchmark dataset: {str(e)}")


@router.post("/benchmark-models", response_model=ResponseModel)
async def benchmark_physics_models(
    num_test_scenarios: int = Query(100, ge=20, le=500),
    models_to_test: List[str] = Query(["kuz_ram_default", "kuz_ram_calibrated"]),
    current_user: User = Depends(get_current_user)
):
    """Benchmark physics models against synthetic data"""
    try:
        generator = get_generator()
        
        # Generate test scenarios with different rock types
        test_scenarios = []
        scenarios_per_rock = num_test_scenarios // len(RockType)
        
        for rock_type in RockType:
            for _ in range(scenarios_per_rock):
                site = generator.generate_random_site(rock_type=rock_type)
                scenario = generator.generate_scenario(site=site)
                test_scenarios.append(scenario)
        
        # Benchmark models
        benchmark_results = generator.benchmark_physics_models(
            test_scenarios,
            models_to_test=models_to_test
        )
        
        return ResponseModel(
            success=True,
            message=f"Benchmarked {len(models_to_test)} models on {len(test_scenarios)} scenarios",
            data={
                "benchmark_results": benchmark_results,
                "test_scenarios": len(test_scenarios),
                "models_tested": models_to_test
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to benchmark models: {str(e)}")


@router.get("/rock-types", response_model=ResponseModel)
async def get_rock_types():
    """Get available rock types"""
    try:
        generator = get_generator()
        
        rock_types = []
        for rock_type in RockType:
            props = generator.rock_database[rock_type]
            rock_types.append({
                "value": rock_type.value,
                "name": rock_type.value.replace('_', ' ').title(),
                "ucs": props.ucs,
                "density": props.density,
                "rock_factor_a": props.rock_factor_a,
                "description": props.description
            })
        
        return ResponseModel(
            success=True,
            message="Rock types retrieved successfully",
            data={"rock_types": rock_types}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rock types: {str(e)}")


@router.get("/explosive-types", response_model=ResponseModel)
async def get_explosive_types():
    """Get available explosive types"""
    try:
        generator = get_generator()
        
        explosive_types = []
        for explosive_type in ExplosiveType:
            props = generator.explosive_database[explosive_type]
            explosive_types.append({
                "value": explosive_type.value,
                "name": explosive_type.value.upper(),
                "density": props.density,
                "rws": props.rws,
                "vod": props.vod,
                "cost_per_kg": props.cost_per_kg,
                "description": props.description
            })
        
        return ResponseModel(
            success=True,
            message="Explosive types retrieved successfully",
            data={"explosive_types": explosive_types}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get explosive types: {str(e)}")


@router.post("/noise-analysis", response_model=ResponseModel)
async def analyze_measurement_noise(
    base_scenario_id: Optional[str] = None,
    noise_levels: List[float] = Query([0.05, 0.10, 0.20, 0.30]),
    num_samples: int = Query(50, ge=10, le=200),
    current_user: User = Depends(get_current_user)
):
    """Analyze the effect of measurement noise on synthetic data"""
    try:
        generator = get_generator()
        
        # Generate or use base scenario
        if base_scenario_id:
            # In a real implementation, you'd retrieve the scenario from storage
            base_scenario = generator.generate_scenario()
        else:
            base_scenario = generator.generate_scenario()
        
        true_frag = base_scenario.true_fragmentation
        true_ppv = base_scenario.true_ppv
        
        noise_analysis = []
        
        for noise_level in noise_levels:
            noise_params = NoiseParameters(
                fragmentation_noise=noise_level,
                ppv_noise=noise_level,
                outlier_probability=0.05
            )
            
            # Generate multiple noisy measurements
            p80_measurements = []
            ppv_measurements = []
            
            for _ in range(num_samples):
                noisy_frag, noisy_ppv = generator.add_measurement_noise(
                    true_frag, true_ppv, noise_params
                )
                
                if noisy_frag is not None:
                    p80_measurements.append(noisy_frag.p80)
                
                if noisy_ppv:
                    ppv_measurements.extend(noisy_ppv.values())
            
            # Calculate statistics
            if p80_measurements:
                import numpy as np
                mean_p80 = np.mean(p80_measurements)
                std_p80 = np.std(p80_measurements)
                bias_p80 = mean_p80 - true_frag.p80
                
                noise_analysis.append({
                    "noise_level": noise_level,
                    "fragmentation": {
                        "true_p80": true_frag.p80,
                        "mean_p80": mean_p80,
                        "std_p80": std_p80,
                        "bias": bias_p80,
                        "measurements": len(p80_measurements)
                    },
                    "ppv": {
                        "measurements": len(ppv_measurements),
                        "mean_ppv": np.mean(ppv_measurements) if ppv_measurements else 0,
                        "std_ppv": np.std(ppv_measurements) if ppv_measurements else 0
                    }
                })
        
        return ResponseModel(
            success=True,
            message="Noise analysis completed successfully",
            data={
                "base_scenario": {
                    "scenario_id": base_scenario.scenario_id,
                    "true_p80": true_frag.p80,
                    "rock_type": base_scenario.site.rock_properties.rock_type.value
                },
                "noise_analysis": noise_analysis
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze noise: {str(e)}")