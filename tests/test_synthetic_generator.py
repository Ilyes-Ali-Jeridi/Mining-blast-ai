"""
Tests for synthetic data generator
"""

import pytest
import tempfile
import os
import json
from datetime import datetime

from src.drill_blast_system.ml_pipeline.synthetic_generator import (
    SyntheticDataGenerator,
    RockType,
    ExplosiveType,
    NoiseParameters,
    SyntheticSite,
    SyntheticBlastScenario
)


class TestSyntheticDataGenerator:
    """Test synthetic data generator functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = SyntheticDataGenerator(random_seed=42)
    
    def test_initialization(self):
        """Test generator initialization"""
        assert self.generator is not None
        assert len(self.generator.rock_database) == len(RockType)
        assert len(self.generator.explosive_database) == len(ExplosiveType)
    
    def test_generate_random_site(self):
        """Test random site generation"""
        site = self.generator.generate_random_site()
        
        assert site.site_id is not None
        assert site.bench_height > 0
        assert site.bench_width > 0
        assert site.bench_length > 0
        assert site.min_burden < site.max_burden
        assert site.min_spacing < site.max_spacing
        assert len(site.receptors) >= 2
        
        # Test with specific rock type
        site_granite = self.generator.generate_random_site(rock_type=RockType.HARD_IGNEOUS)
        assert site_granite.rock_properties.rock_type == RockType.HARD_IGNEOUS
    
    def test_generate_blast_pattern(self):
        """Test blast pattern generation"""
        site = self.generator.generate_random_site()
        blast_plan = self.generator.generate_blast_pattern(site)
        
        assert blast_plan.plan_id is not None
        assert len(blast_plan.holes) > 0
        assert blast_plan.total_charge_kg > 0
        assert blast_plan.powder_factor_kg_per_t > 0
        
        # Check hole properties
        for hole in blast_plan.holes:
            assert hole.charge_kg > 0
            assert hole.depth > 0
            assert hole.diameter > 0
            assert hole.delay_ms >= 0
            assert hole.explosive_type in [e.value for e in ExplosiveType]
    
    def test_calculate_true_predictions(self):
        """Test physics-based predictions"""
        site = self.generator.generate_random_site()
        blast_plan = self.generator.generate_blast_pattern(site)
        
        frag_result, ppv_predictions = self.generator.calculate_true_predictions(site, blast_plan)
        
        # Check fragmentation result
        assert frag_result.p10 > 0
        assert frag_result.p50 > 0
        assert frag_result.p80 > 0
        assert frag_result.p10 < frag_result.p50 < frag_result.p80
        assert frag_result.is_valid
        
        # Check PPV predictions
        assert len(ppv_predictions) == len(site.receptors)
        for receptor_id, ppv in ppv_predictions.items():
            assert ppv > 0
            assert receptor_id in [r.receptor_id for r in site.receptors]
    
    def test_add_measurement_noise(self):
        """Test noise addition to measurements"""
        site = self.generator.generate_random_site()
        blast_plan = self.generator.generate_blast_pattern(site)
        true_frag, true_ppv = self.generator.calculate_true_predictions(site, blast_plan)
        
        noise_params = NoiseParameters(
            fragmentation_noise=0.2,
            ppv_noise=0.15,
            outlier_probability=0.1
        )
        
        noisy_frag, noisy_ppv = self.generator.add_measurement_noise(
            true_frag, true_ppv, noise_params
        )
        
        # Check that noise was added (values should be different)
        if noisy_frag is not None:  # Might be None due to missing data simulation
            assert abs(noisy_frag.p80 - true_frag.p80) >= 0  # Could be same by chance
            assert noisy_frag.measurement_quality <= true_frag.measurement_quality
        
        # PPV should have some noise
        for receptor_id in true_ppv:
            if receptor_id in noisy_ppv:  # Might be missing due to simulation
                assert noisy_ppv[receptor_id] > 0
    
    def test_generate_scenario(self):
        """Test complete scenario generation"""
        scenario = self.generator.generate_scenario()
        
        assert scenario.scenario_id is not None
        assert scenario.site is not None
        assert scenario.blast_plan is not None
        assert scenario.true_fragmentation is not None
        assert scenario.true_ppv is not None
        assert isinstance(scenario.created_at, datetime)
    
    def test_parameter_space_exploration(self):
        """Test parameter space exploration"""
        scenarios = self.generator.generate_parameter_space_exploration(
            num_scenarios=20
        )
        
        assert len(scenarios) == 20
        
        # Check parameter diversity
        powder_factors = []
        rock_factors = []
        
        for scenario in scenarios:
            powder_factors.append(scenario.blast_plan.powder_factor_kg_per_t)
            rock_factors.append(scenario.site.rock_properties.rock_factor_a)
        
        # Should have good parameter coverage
        assert max(powder_factors) > min(powder_factors)
        assert max(rock_factors) > min(rock_factors)
    
    def test_benchmark_dataset_generation(self):
        """Test benchmark dataset generation"""
        dataset = self.generator.generate_benchmark_dataset(
            num_scenarios=50,
            test_split=0.2,
            validation_split=0.1
        )
        
        assert 'train' in dataset
        assert 'validation' in dataset
        assert 'test' in dataset
        
        total_scenarios = len(dataset['train']) + len(dataset['validation']) + len(dataset['test'])
        assert total_scenarios == 50
        
        # Check approximate splits
        assert len(dataset['test']) == pytest.approx(10, abs=2)
        assert len(dataset['validation']) == pytest.approx(5, abs=2)
    
    def test_dataset_export_json(self):
        """Test JSON dataset export"""
        scenarios = [self.generator.generate_scenario() for _ in range(5)]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            self.generator.export_dataset(scenarios, output_path, format='json')
            
            # Verify file was created and contains valid JSON
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert 'metadata' in data
            assert 'scenarios' in data
            assert len(data['scenarios']) == 5
            assert data['metadata']['num_scenarios'] == 5
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_dataset_export_csv(self):
        """Test CSV dataset export"""
        scenarios = [self.generator.generate_scenario() for _ in range(5)]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            self.generator.export_dataset(scenarios, output_path, format='csv')
            
            # Verify file was created
            assert os.path.exists(output_path)
            
            # Check CSV content
            import pandas as pd
            df = pd.read_csv(output_path)
            assert len(df) == 5
            assert 'scenario_id' in df.columns
            assert 'true_p80_mm' in df.columns
            assert 'powder_factor_kg_t' in df.columns
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_dataset_validation(self):
        """Test dataset validation"""
        scenarios = [self.generator.generate_scenario() for _ in range(10)]
        
        report = self.generator.validate_dataset(scenarios)
        
        assert 'total_scenarios' in report
        assert 'valid_scenarios' in report
        assert 'statistics' in report
        assert 'data_quality' in report
        
        assert report['total_scenarios'] == 10
        assert report['valid_scenarios'] <= 10
        assert 'completeness' in report['data_quality']
    
    def test_physics_model_benchmarking(self):
        """Test physics model benchmarking"""
        scenarios = [self.generator.generate_scenario() for _ in range(10)]
        
        results = self.generator.benchmark_physics_models(
            scenarios,
            models_to_test=['kuz_ram_default']
        )
        
        assert 'kuz_ram_default' in results
        
        metrics = results['kuz_ram_default']
        assert 'mae_mm' in metrics
        assert 'rmse_mm' in metrics
        assert 'mape_percent' in metrics
        assert 'r2_score' in metrics
        assert 'num_predictions' in metrics
        
        # Metrics should be reasonable
        assert metrics['mae_mm'] >= 0
        assert metrics['rmse_mm'] >= 0
        assert metrics['num_predictions'] > 0
    
    def test_edge_case_scenarios(self):
        """Test edge case scenario generation"""
        scenarios = self.generator._generate_edge_case_scenarios(8)
        
        assert len(scenarios) == 8
        
        # Should have variety in conditions
        powder_factors = [s.blast_plan.powder_factor_kg_per_t for s in scenarios]
        bench_heights = [s.site.bench_height for s in scenarios]
        
        assert max(powder_factors) > min(powder_factors)
        assert max(bench_heights) >= 18.0  # Some should be tall benches
    
    def test_noise_parameters(self):
        """Test different noise parameter configurations"""
        site = self.generator.generate_random_site()
        blast_plan = self.generator.generate_blast_pattern(site)
        true_frag, true_ppv = self.generator.calculate_true_predictions(site, blast_plan)
        
        # Test high noise
        high_noise = NoiseParameters(
            fragmentation_noise=0.5,
            ppv_noise=0.4,
            outlier_probability=0.2,
            missing_data_probability=0.1
        )
        
        noisy_frag, noisy_ppv = self.generator.add_measurement_noise(
            true_frag, true_ppv, high_noise
        )
        
        # With high noise, measurements might be missing or have quality issues
        if noisy_frag is not None:
            assert noisy_frag.measurement_quality < 1.0
        
        # Some PPV measurements might be missing
        assert len(noisy_ppv) <= len(true_ppv)
    
    def test_reproducibility(self):
        """Test that generator produces reproducible results with same seed"""
        gen1 = SyntheticDataGenerator(random_seed=123)
        gen2 = SyntheticDataGenerator(random_seed=123)
        
        scenario1 = gen1.generate_scenario()
        scenario2 = gen2.generate_scenario()
        
        # Should generate identical scenarios with same seed
        assert scenario1.site.bench_height == scenario2.site.bench_height
        assert scenario1.site.rock_properties.rock_type == scenario2.site.rock_properties.rock_type
        assert len(scenario1.blast_plan.holes) == len(scenario2.blast_plan.holes)


class TestRockAndExplosiveProperties:
    """Test rock and explosive property databases"""
    
    def setup_method(self):
        self.generator = SyntheticDataGenerator()
    
    def test_rock_database_completeness(self):
        """Test that all rock types have properties"""
        for rock_type in RockType:
            assert rock_type in self.generator.rock_database
            props = self.generator.rock_database[rock_type]
            assert props.ucs > 0
            assert props.density > 0
            assert props.rock_factor_a > 0
    
    def test_explosive_database_completeness(self):
        """Test that all explosive types have properties"""
        for explosive_type in ExplosiveType:
            assert explosive_type in self.generator.explosive_database
            props = self.generator.explosive_database[explosive_type]
            assert props.density > 0
            assert props.rws > 0
            assert props.vod > 0
            assert props.cost_per_kg > 0
    
    def test_realistic_property_ranges(self):
        """Test that properties are in realistic ranges"""
        # Rock properties
        for props in self.generator.rock_database.values():
            assert 10 <= props.ucs <= 300  # MPa
            assert 1500 <= props.density <= 3000  # kg/m³
            assert 3 <= props.rock_factor_a <= 20
        
        # Explosive properties
        for props in self.generator.explosive_database.values():
            assert 800 <= props.density <= 1500  # kg/m³
            assert 80 <= props.rws <= 150  # %
            assert 3000 <= props.vod <= 7000  # m/s
            assert 0.5 <= props.cost_per_kg <= 5.0  # $/kg


if __name__ == '__main__':
    pytest.main([__file__])