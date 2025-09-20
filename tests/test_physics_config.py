"""
Unit tests for physics model configuration system.

Tests parameter validation, default configurations, calibration utilities,
and configuration management functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.drill_blast_system.physics_models.config import (
    PhysicsConfig,
    PhysicsConfigManager,
    KuzRamParameters,
    PPVParameters,
    FragmentationParameters,
    SafetyParameters,
    RockType
)


class TestKuzRamParameters:
    """Test KuzRamParameters validation"""
    
    def test_valid_parameters(self):
        """Test valid parameter creation"""
        params = KuzRamParameters(rock_factor_a=7.0, scaling_factor=0.005)
        errors = params.validate()
        assert len(errors) == 0
    
    def test_invalid_rock_factor(self):
        """Test invalid rock factor validation"""
        params = KuzRamParameters(rock_factor_a=25.0)  # Too high
        errors = params.validate()
        assert len(errors) > 0
        assert "Rock factor A" in errors[0]
        
        params = KuzRamParameters(rock_factor_a=0.5)  # Too low
        errors = params.validate()
        assert len(errors) > 0
        assert "Rock factor A" in errors[0]
    
    def test_invalid_scaling_factor(self):
        """Test invalid scaling factor validation"""
        params = KuzRamParameters(scaling_factor=0.2)  # Too high
        errors = params.validate()
        assert len(errors) > 0
        assert "Scaling factor" in errors[0]
    
    def test_invalid_min_fragment_size(self):
        """Test invalid minimum fragment size"""
        params = KuzRamParameters(min_fragment_size_mm=-1.0)
        errors = params.validate()
        assert len(errors) > 0
        assert "Minimum fragment size" in errors[0]


class TestPPVParameters:
    """Test PPVParameters validation"""
    
    def test_valid_parameters(self):
        """Test valid parameter creation"""
        params = PPVParameters(k=1.4, a=0.33, b=1.6)
        errors = params.validate()
        assert len(errors) == 0
    
    def test_invalid_k_value(self):
        """Test invalid k value validation"""
        params = PPVParameters(k=6000.0)  # Too high
        errors = params.validate()
        assert len(errors) > 0
        assert "Site constant k" in errors[0]
    
    def test_invalid_exponents(self):
        """Test invalid exponent validation"""
        params = PPVParameters(a=1.5)  # Too high
        errors = params.validate()
        assert len(errors) > 0
        assert "Charge exponent a" in errors[0]
        
        params = PPVParameters(b=0.3)  # Too low
        errors = params.validate()
        assert len(errors) > 0
        assert "Distance exponent b" in errors[0]


class TestFragmentationParameters:
    """Test FragmentationParameters validation"""
    
    def test_valid_parameters(self):
        """Test valid parameter creation"""
        params = FragmentationParameters(default_uniformity_index=1.5)
        errors = params.validate()
        assert len(errors) == 0
    
    def test_invalid_uniformity_index_range(self):
        """Test invalid uniformity index range"""
        params = FragmentationParameters(
            default_uniformity_index=4.0,  # Outside range
            min_uniformity_index=0.5,
            max_uniformity_index=3.0
        )
        errors = params.validate()
        assert len(errors) > 0
        assert "uniformity index" in errors[0]
    
    def test_invalid_distribution_type(self):
        """Test invalid distribution type"""
        params = FragmentationParameters(default_distribution_type="invalid")
        errors = params.validate()
        assert len(errors) > 0
        assert "Invalid distribution type" in errors[0]


class TestSafetyParameters:
    """Test SafetyParameters validation"""
    
    def test_valid_parameters(self):
        """Test valid parameter creation"""
        params = SafetyParameters()
        errors = params.validate()
        assert len(errors) == 0
    
    def test_invalid_charge_limits(self):
        """Test invalid charge limit validation"""
        params = SafetyParameters(max_charge_per_hole_kg=-10.0)
        errors = params.validate()
        assert len(errors) > 0
        assert "Max charge per hole" in errors[0]
    
    def test_invalid_powder_factor_range(self):
        """Test invalid powder factor range"""
        params = SafetyParameters(
            powder_factor_min_kg_per_t=1.0,
            powder_factor_max_kg_per_t=0.5  # Min > Max
        )
        errors = params.validate()
        assert len(errors) > 0
        assert "powder factor range" in errors[0]


class TestPhysicsConfig:
    """Test PhysicsConfig class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.valid_config = PhysicsConfig(
            site_name="Test Site",
            description="Test configuration"
        )
    
    def test_valid_config_creation(self):
        """Test valid configuration creation"""
        assert self.valid_config.is_valid()
        validation = self.valid_config.get_validation_summary()
        assert validation["is_valid"]
        assert validation["total_errors"] == 0
    
    def test_invalid_config_validation(self):
        """Test invalid configuration validation"""
        invalid_config = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=25.0),  # Invalid
            ppv=PPVParameters(k=6000.0)  # Invalid
        )
        
        assert not invalid_config.is_valid()
        validation = invalid_config.get_validation_summary()
        assert not validation["is_valid"]
        assert validation["total_errors"] > 0
        assert "kuz_ram" in validation["errors_by_category"]
        assert "ppv" in validation["errors_by_category"]
    
    def test_rock_type_assignment(self):
        """Test rock type assignment"""
        config = PhysicsConfig(rock_type=RockType.HARD)
        assert config.rock_type == RockType.HARD


class TestPhysicsConfigManager:
    """Test PhysicsConfigManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Use temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PhysicsConfigManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_configs_creation(self):
        """Test default configuration creation"""
        for rock_type in RockType:
            config = self.manager.get_default_config(rock_type)
            assert config.rock_type == rock_type
            assert config.is_valid()
    
    def test_default_config_differences(self):
        """Test that different rock types have different parameters"""
        soft_config = self.manager.get_default_config(RockType.SOFT)
        hard_config = self.manager.get_default_config(RockType.HARD)
        
        # Hard rock should have higher rock factor A
        assert hard_config.kuz_ram.rock_factor_a > soft_config.kuz_ram.rock_factor_a
        
        # Hard rock should have higher PPV k value
        assert hard_config.ppv.k > soft_config.ppv.k
    
    def test_save_and_load_config(self):
        """Test configuration save and load"""
        original_config = self.manager.get_default_config(RockType.MEDIUM)
        original_config.site_name = "Test Save Site"
        
        # Save configuration
        saved_path = self.manager.save_config(original_config, "test_config")
        assert saved_path.exists()
        
        # Load configuration
        loaded_config = self.manager.load_config("test_config")
        
        # Compare configurations
        assert loaded_config.site_name == original_config.site_name
        assert loaded_config.rock_type == original_config.rock_type
        assert loaded_config.kuz_ram.rock_factor_a == original_config.kuz_ram.rock_factor_a
        assert loaded_config.ppv.k == original_config.ppv.k
    
    def test_save_invalid_config(self):
        """Test saving invalid configuration raises error"""
        invalid_config = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=25.0)  # Invalid
        )
        
        with pytest.raises(ValueError):
            self.manager.save_config(invalid_config, "invalid_config")
    
    def test_load_nonexistent_config(self):
        """Test loading non-existent configuration raises error"""
        with pytest.raises(FileNotFoundError):
            self.manager.load_config("nonexistent_config")
    
    def test_list_configs(self):
        """Test listing configurations"""
        # Initially empty
        configs = self.manager.list_configs()
        assert len(configs) == 0
        
        # Save a config
        test_config = self.manager.get_default_config(RockType.MEDIUM)
        self.manager.save_config(test_config, "test_list")
        
        # Should now appear in list
        configs = self.manager.list_configs()
        assert "test_list" in configs
    
    def test_delete_config(self):
        """Test configuration deletion"""
        # Save a config
        test_config = self.manager.get_default_config(RockType.MEDIUM)
        self.manager.save_config(test_config, "test_delete")
        
        # Verify it exists
        assert "test_delete" in self.manager.list_configs()
        
        # Delete it
        deleted = self.manager.delete_config("test_delete")
        assert deleted
        
        # Verify it's gone
        assert "test_delete" not in self.manager.list_configs()
        
        # Try to delete again
        deleted_again = self.manager.delete_config("test_delete")
        assert not deleted_again
    
    def test_kuz_ram_calibration(self):
        """Test Kuz-Ram parameter calibration"""
        # Create synthetic measured data
        measured_data = [
            {"predicted_p80": 50.0, "measured_p80": 60.0},
            {"predicted_p80": 75.0, "measured_p80": 90.0},
            {"predicted_p80": 100.0, "measured_p80": 120.0}
        ]
        
        base_config = self.manager.get_default_config(RockType.MEDIUM)
        original_rock_factor = base_config.kuz_ram.rock_factor_a
        
        calibrated_config = self.manager.calibrate_kuz_ram(measured_data, base_config)
        
        # Rock factor should be adjusted (measured > predicted, so factor should increase)
        assert calibrated_config.kuz_ram.rock_factor_a > original_rock_factor
        assert calibrated_config.is_valid()
        assert "Calibrated" in calibrated_config.site_name
    
    def test_kuz_ram_calibration_insufficient_data(self):
        """Test Kuz-Ram calibration with insufficient data"""
        measured_data = [
            {"predicted_p80": 50.0, "measured_p80": 60.0}  # Only 1 point
        ]
        
        with pytest.raises(ValueError):
            self.manager.calibrate_kuz_ram(measured_data)
    
    def test_ppv_calibration(self):
        """Test PPV parameter calibration"""
        # Create synthetic measured data that follows PPV relationship
        # Using base model to generate realistic data with some noise
        from src.drill_blast_system.physics_models.ppv import PPVModel
        base_model = PPVModel(k=1300, a=0.33, b=1.6)
        
        measured_data = []
        test_cases = [
            (50, 100), (75, 150), (100, 200), (25, 75), (60, 120)
        ]
        
        for charge, distance in test_cases:
            true_ppv = base_model.predict_ppv_single_charge(charge, distance)
            # Add some realistic noise (±20%)
            noise_factor = 1.0 + 0.2 * (0.5 - 0.3)  # Small consistent bias
            measured_ppv = true_ppv * noise_factor
            measured_data.append({
                "charge_weight_kg": charge,
                "distance_m": distance,
                "measured_ppv": measured_ppv
            })
        
        base_config = self.manager.get_default_config(RockType.MEDIUM)
        calibrated_config = self.manager.calibrate_ppv(measured_data, base_config)
        
        # Should have different PPV parameters
        assert calibrated_config.ppv.k != base_config.ppv.k
        assert calibrated_config.is_valid()
        assert "PPV Calibrated" in calibrated_config.site_name
    
    def test_config_comparison(self):
        """Test configuration comparison"""
        config1 = self.manager.get_default_config(RockType.SOFT)
        config2 = self.manager.get_default_config(RockType.HARD)
        
        comparison = self.manager.compare_configs(config1, config2)
        
        assert comparison["has_differences"]
        assert "kuz_ram" in comparison["differences"]
        assert "ppv" in comparison["differences"]
        assert "rock_type" in comparison["differences"]
    
    def test_config_export_summary(self):
        """Test configuration export summary"""
        config = self.manager.get_default_config(RockType.MEDIUM)
        summary = self.manager.export_config_summary(config)
        
        assert "site_name" in summary
        assert "parameters" in summary
        assert "validation" in summary
        assert "kuz_ram" in summary["parameters"]
        assert "ppv" in summary["parameters"]
        assert "safety" in summary["parameters"]
        assert "equation" in summary["parameters"]["ppv"]
    
    def test_edge_cases_and_robustness(self):
        """Test edge cases and robustness"""
        # Test with extreme calibration data
        extreme_data = [
            {"predicted_p80": 50.0, "measured_p80": 500.0},  # 10x difference
            {"predicted_p80": 75.0, "measured_p80": 750.0},
            {"predicted_p80": 100.0, "measured_p80": 1000.0}
        ]
        
        calibrated_config = self.manager.calibrate_kuz_ram(extreme_data)
        
        # Should still be valid (clamped to valid range)
        assert calibrated_config.is_valid()
        assert 1.0 <= calibrated_config.kuz_ram.rock_factor_a <= 20.0


class TestRockType:
    """Test RockType enum"""
    
    def test_rock_type_values(self):
        """Test rock type enum values"""
        assert RockType.VERY_SOFT.value == "very_soft"
        assert RockType.SOFT.value == "soft"
        assert RockType.MEDIUM.value == "medium"
        assert RockType.HARD.value == "hard"
        assert RockType.VERY_HARD.value == "very_hard"
    
    def test_rock_type_iteration(self):
        """Test iterating over rock types"""
        rock_types = list(RockType)
        assert len(rock_types) == 5
        assert RockType.MEDIUM in rock_types


class TestConfigurationIntegration:
    """Integration tests for configuration system"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PhysicsConfigManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete configuration workflow"""
        # 1. Get default config
        base_config = self.manager.get_default_config(RockType.MEDIUM)
        assert base_config.is_valid()
        
        # 2. Modify and save
        base_config.site_name = "My Mine Site"
        base_config.description = "Custom configuration for my site"
        saved_path = self.manager.save_config(base_config, "my_site")
        
        # 3. Load and verify
        loaded_config = self.manager.load_config("my_site")
        assert loaded_config.site_name == "My Mine Site"
        
        # 4. Calibrate with data - use realistic PPV data
        from src.drill_blast_system.physics_models.ppv import PPVModel
        base_model = PPVModel(k=1300, a=0.33, b=1.6)
        
        ppv_data = []
        for charge, distance in [(50, 100), (75, 150), (100, 200)]:
            true_ppv = base_model.predict_ppv_single_charge(charge, distance)
            measured_ppv = true_ppv * 1.1  # 10% higher than predicted
            ppv_data.append({
                "charge_weight_kg": charge,
                "distance_m": distance,
                "measured_ppv": measured_ppv
            })
        
        calibrated_config = self.manager.calibrate_ppv(ppv_data, loaded_config)
        
        # 5. Save calibrated version
        self.manager.save_config(calibrated_config, "my_site_calibrated")
        
        # 6. Compare configurations
        comparison = self.manager.compare_configs(loaded_config, calibrated_config)
        assert comparison["has_differences"]
        
        # 7. Export summary
        summary = self.manager.export_config_summary(calibrated_config)
        assert summary["validation"]["is_valid"]
        
        # 8. List all configs
        configs = self.manager.list_configs()
        assert "my_site" in configs
        assert "my_site_calibrated" in configs


if __name__ == "__main__":
    pytest.main([__file__])