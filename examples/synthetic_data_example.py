#!/usr/bin/env python3
"""
Synthetic Data Generator Example

Demonstrates how to use the synthetic data generator for:
1. Creating individual blast scenarios
2. Parameter space exploration
3. Benchmark dataset generation
4. Model validation and benchmarking
"""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drill_blast_system.ml_pipeline.synthetic_generator import (
    SyntheticDataGenerator,
    RockType,
    ExplosiveType,
    NoiseParameters
)


def example_basic_scenario_generation():
    """Example 1: Generate basic synthetic scenarios"""
    print("=== Example 1: Basic Scenario Generation ===")
    
    # Initialize generator with fixed seed for reproducibility
    generator = SyntheticDataGenerator(random_seed=42)
    
    # Generate a single random scenario
    scenario = generator.generate_scenario()
    
    print(f"Generated scenario: {scenario.scenario_id}")
    print(f"Site: {scenario.site.name}")
    print(f"Rock type: {scenario.site.rock_properties.rock_type.value}")
    print(f"Bench dimensions: {scenario.site.bench_width:.1f}m x {scenario.site.bench_length:.1f}m x {scenario.site.bench_height:.1f}m")
    print(f"Number of holes: {len(scenario.blast_plan.holes)}")
    print(f"Total charge: {scenario.blast_plan.total_charge_kg:.1f} kg")
    print(f"Powder factor: {scenario.blast_plan.powder_factor_kg_per_t:.3f} kg/t")
    print(f"True P80: {scenario.true_fragmentation.p80:.1f} mm")
    
    if scenario.measured_fragmentation:
        print(f"Measured P80: {scenario.measured_fragmentation.p80:.1f} mm")
        print(f"Measurement quality: {scenario.measured_fragmentation.measurement_quality:.2f}")
    
    print(f"PPV predictions: {len(scenario.true_ppv)} receptors")
    for receptor_id, ppv in scenario.true_ppv.items():
        print(f"  {receptor_id}: {ppv:.2f} mm/s")
    
    print()


def example_parameter_space_exploration():
    """Example 2: Parameter space exploration"""
    print("=== Example 2: Parameter Space Exploration ===")
    
    generator = SyntheticDataGenerator(random_seed=123)
    
    # Define parameter ranges for exploration
    parameter_ranges = {
        'powder_factor': (0.2, 0.6),  # kg/t
        'burden': (3.0, 6.0),  # m
        'bench_height': (10.0, 18.0),  # m
        'rock_factor_a': (6.0, 12.0),  # Kuz-Ram parameter
    }
    
    # Generate scenarios exploring parameter space
    scenarios = generator.generate_parameter_space_exploration(
        num_scenarios=50,
        parameter_ranges=parameter_ranges
    )
    
    print(f"Generated {len(scenarios)} scenarios for parameter exploration")
    
    # Analyze parameter coverage
    powder_factors = [s.blast_plan.powder_factor_kg_per_t for s in scenarios]
    p80_values = [s.true_fragmentation.p80 for s in scenarios]
    
    print(f"Powder factor range: {min(powder_factors):.3f} - {max(powder_factors):.3f} kg/t")
    print(f"P80 range: {min(p80_values):.1f} - {max(p80_values):.1f} mm")
    
    # Create scatter plot
    plt.figure(figsize=(10, 6))
    plt.scatter(powder_factors, p80_values, alpha=0.6)
    plt.xlabel('Powder Factor (kg/t)')
    plt.ylabel('P80 Fragmentation (mm)')
    plt.title('Parameter Space Exploration: Powder Factor vs P80')
    plt.grid(True, alpha=0.3)
    
    # Save plot
    output_dir = Path("output/synthetic_examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / "parameter_exploration.png", dpi=300, bbox_inches='tight')
    print(f"Saved plot to {output_dir / 'parameter_exploration.png'}")
    plt.close()
    
    print()


def example_benchmark_dataset():
    """Example 3: Generate benchmark dataset"""
    print("=== Example 3: Benchmark Dataset Generation ===")
    
    generator = SyntheticDataGenerator(random_seed=456)
    
    # Generate comprehensive benchmark dataset
    dataset = generator.generate_benchmark_dataset(
        num_scenarios=200,
        test_split=0.2,
        validation_split=0.1
    )
    
    print(f"Generated benchmark dataset:")
    print(f"  Training: {len(dataset['train'])} scenarios")
    print(f"  Validation: {len(dataset['validation'])} scenarios")
    print(f"  Test: {len(dataset['test'])} scenarios")
    
    # Validate dataset quality
    all_scenarios = dataset['train'] + dataset['validation'] + dataset['test']
    validation_report = generator.validate_dataset(all_scenarios)
    
    print(f"\nDataset Quality Report:")
    print(f"  Total scenarios: {validation_report['total_scenarios']}")
    print(f"  Valid scenarios: {validation_report['valid_scenarios']}")
    print(f"  Completeness: {validation_report['data_quality']['completeness']:.2%}")
    print(f"  Missing data rate: {validation_report['data_quality']['missing_rate']:.2%}")
    
    if 'p80_mm' in validation_report['statistics']:
        p80_stats = validation_report['statistics']['p80_mm']
        print(f"  P80 statistics: {p80_stats['mean']:.1f} ± {p80_stats['std']:.1f} mm")
    
    # Export dataset
    output_dir = Path("output/synthetic_examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export training set as JSON
    generator.export_dataset(
        dataset['train'], 
        str(output_dir / "training_dataset.json"), 
        format='json'
    )
    
    # Export full dataset as CSV for analysis
    generator.export_dataset(
        all_scenarios, 
        str(output_dir / "full_dataset.csv"), 
        format='csv'
    )
    
    print(f"Exported datasets to {output_dir}")
    print()


def example_noise_analysis():
    """Example 4: Analyze effect of measurement noise"""
    print("=== Example 4: Measurement Noise Analysis ===")
    
    generator = SyntheticDataGenerator(random_seed=789)
    
    # Generate base scenario
    base_site = generator.generate_random_site()
    blast_plan = generator.generate_blast_pattern(base_site)
    true_frag, true_ppv = generator.calculate_true_predictions(base_site, blast_plan)
    
    print(f"Base scenario - True P80: {true_frag.p80:.1f} mm")
    
    # Test different noise levels
    noise_levels = [0.05, 0.10, 0.20, 0.30]  # 5%, 10%, 20%, 30%
    
    results = []
    
    for noise_level in noise_levels:
        noise_params = NoiseParameters(
            fragmentation_noise=noise_level,
            ppv_noise=noise_level,
            outlier_probability=0.05
        )
        
        # Generate multiple noisy measurements
        p80_measurements = []
        for _ in range(100):  # 100 repeated measurements
            noisy_frag, _ = generator.add_measurement_noise(
                true_frag, true_ppv, noise_params
            )
            if noisy_frag is not None:
                p80_measurements.append(noisy_frag.p80)
        
        if p80_measurements:
            mean_p80 = np.mean(p80_measurements)
            std_p80 = np.std(p80_measurements)
            bias = mean_p80 - true_frag.p80
            
            results.append({
                'noise_level': noise_level,
                'mean_p80': mean_p80,
                'std_p80': std_p80,
                'bias': bias,
                'measurements': len(p80_measurements)
            })
            
            print(f"Noise {noise_level:.0%}: Mean P80 = {mean_p80:.1f} ± {std_p80:.1f} mm, "
                  f"Bias = {bias:.1f} mm ({len(p80_measurements)} measurements)")
    
    # Plot noise analysis
    if results:
        noise_levels_plot = [r['noise_level'] * 100 for r in results]
        std_values = [r['std_p80'] for r in results]
        bias_values = [abs(r['bias']) for r in results]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Standard deviation vs noise level
        ax1.plot(noise_levels_plot, std_values, 'bo-')
        ax1.set_xlabel('Noise Level (%)')
        ax1.set_ylabel('P80 Standard Deviation (mm)')
        ax1.set_title('Measurement Precision vs Noise Level')
        ax1.grid(True, alpha=0.3)
        
        # Bias vs noise level
        ax2.plot(noise_levels_plot, bias_values, 'ro-')
        ax2.set_xlabel('Noise Level (%)')
        ax2.set_ylabel('Absolute Bias (mm)')
        ax2.set_title('Measurement Bias vs Noise Level')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_dir = Path("output/synthetic_examples")
        output_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_dir / "noise_analysis.png", dpi=300, bbox_inches='tight')
        print(f"Saved noise analysis plot to {output_dir / 'noise_analysis.png'}")
        plt.close()
    
    print()


def example_model_benchmarking():
    """Example 5: Benchmark physics models"""
    print("=== Example 5: Physics Model Benchmarking ===")
    
    generator = SyntheticDataGenerator(random_seed=999)
    
    # Generate test scenarios with different rock types
    test_scenarios = []
    
    for rock_type in [RockType.SOFT_SEDIMENTARY, RockType.HARD_IGNEOUS, RockType.METAMORPHIC]:
        for _ in range(20):  # 20 scenarios per rock type
            site = generator.generate_random_site(rock_type=rock_type)
            scenario = generator.generate_scenario(site=site)
            test_scenarios.append(scenario)
    
    print(f"Generated {len(test_scenarios)} test scenarios")
    
    # Benchmark models
    benchmark_results = generator.benchmark_physics_models(
        test_scenarios,
        models_to_test=['kuz_ram_default', 'kuz_ram_calibrated']
    )
    
    print("\nBenchmark Results:")
    for model_name, metrics in benchmark_results.items():
        print(f"\n{model_name}:")
        print(f"  MAE: {metrics['mae_mm']:.2f} mm")
        print(f"  RMSE: {metrics['rmse_mm']:.2f} mm")
        print(f"  MAPE: {metrics['mape_percent']:.1f}%")
        print(f"  R²: {metrics['r2_score']:.3f}")
        print(f"  Predictions: {metrics['num_predictions']}")
    
    # Create comparison plot
    if len(benchmark_results) >= 2:
        models = list(benchmark_results.keys())
        mae_values = [benchmark_results[model]['mae_mm'] for model in models]
        rmse_values = [benchmark_results[model]['rmse_mm'] for model in models]
        
        x = np.arange(len(models))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x - width/2, mae_values, width, label='MAE', alpha=0.8)
        ax.bar(x + width/2, rmse_values, width, label='RMSE', alpha=0.8)
        
        ax.set_xlabel('Model')
        ax.set_ylabel('Error (mm)')
        ax.set_title('Model Performance Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(models)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        output_dir = Path("output/synthetic_examples")
        output_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_dir / "model_benchmark.png", dpi=300, bbox_inches='tight')
        print(f"Saved benchmark plot to {output_dir / 'model_benchmark.png'}")
        plt.close()
    
    print()


def main():
    """Run all examples"""
    print("Synthetic Data Generator Examples")
    print("=" * 50)
    
    try:
        example_basic_scenario_generation()
        example_parameter_space_exploration()
        example_benchmark_dataset()
        example_noise_analysis()
        example_model_benchmarking()
        
        print("All examples completed successfully!")
        print("Check the 'output/synthetic_examples' directory for generated files and plots.")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()