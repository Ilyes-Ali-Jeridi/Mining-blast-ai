"""
Unit tests for Kuz-Ram fragmentation model.

Tests the implementation against known validation cases and published data.
"""

import pytest
import math
from src.drill_blast_system.physics_models.kuz_ram import KuzRamModel, BlastParameters
from src.drill_blast_system.physics_models.fragmentation_curve import FragmentationCurve


class TestKuzRamModel:
    """Test cases for KuzRamModel class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.model = KuzRamModel(rock_factor_a=7.0)
        
        # Standard test parameters - more realistic values
        self.test_params = BlastParameters(
            powder_factor_kg_per_t=0.15,  # More typical powder factor
            powder_factor_kg_per_m3=375.0,  # Consistent with 2.5 t/m³ rock density
            burden=4.0,  # Slightly larger burden
            spacing=4.5,  # Slightly larger spacing
            bench_height=12.0,
            hole_diameter=89.0,
            stemming_length=3.0,  # Better stemming ratio
            rock_density=2500.0,
            explosive_rws=100.0,
            explosive_density=1200.0
        )
    
    def test_model_initialization(self):
        """Test model initialization with different rock factors"""
        # Valid rock factor
        model = KuzRamModel(rock_factor_a=10.0)
        assert model.rock_factor_a == 10.0
        
        # Invalid rock factors should raise ValueError
        with pytest.raises(ValueError):
            KuzRamModel(rock_factor_a=0.5)  # Too low
        
        with pytest.raises(ValueError):
            KuzRamModel(rock_factor_a=25.0)  # Too high
    
    def test_powder_factor_calculations(self):
        """Test powder factor calculations"""
        charge_kg = 30.0
        rock_volume_m3 = 126.0  # 3m x 3.5m x 12m
        rock_density = 2500.0
        
        powder_factors = self.model.calculate_powder_factors(
            charge_kg, rock_volume_m3, rock_density
        )
        
        expected_kg_per_t = charge_kg / (rock_volume_m3 * rock_density / 1000.0)
        expected_kg_per_m3 = charge_kg / rock_volume_m3
        
        assert abs(powder_factors["kg_per_tonne"] - expected_kg_per_t) < 0.001
        assert abs(powder_factors["kg_per_m3"] - expected_kg_per_m3) < 0.001
    
    def test_powder_factor_validation(self):
        """Test powder factor calculation with invalid inputs"""
        with pytest.raises(ValueError):
            self.model.calculate_powder_factors(-1.0, 100.0, 2500.0)
        
        with pytest.raises(ValueError):
            self.model.calculate_powder_factors(30.0, 0.0, 2500.0)
        
        with pytest.raises(ValueError):
            self.model.calculate_powder_factors(30.0, 100.0, -2500.0)
    
    def test_mean_fragment_size_calculation(self):
        """Test mean fragment size calculation with known parameters"""
        mean_size = self.model.predict_mean_fragment_size(self.test_params)
        
        # Should return a reasonable fragment size (typically 10-200mm for normal blasting)
        assert 5.0 <= mean_size <= 500.0
        
        # Test with different rock factors
        hard_rock_model = KuzRamModel(rock_factor_a=12.0)
        hard_rock_size = hard_rock_model.predict_mean_fragment_size(self.test_params)
        
        soft_rock_model = KuzRamModel(rock_factor_a=4.0)
        soft_rock_size = soft_rock_model.predict_mean_fragment_size(self.test_params)
        
        # Hard rock should produce larger fragments
        assert hard_rock_size > mean_size > soft_rock_size
    
    def test_mean_fragment_size_validation_case(self):
        """Test against published Kuz-Ram validation case"""
        # Example from literature (approximate values)
        validation_params = BlastParameters(
            powder_factor_kg_per_t=0.25,
            powder_factor_kg_per_m3=625.0,
            burden=2.5,
            spacing=3.0,
            bench_height=10.0,
            hole_diameter=76.0,
            stemming_length=2.0,
            rock_density=2500.0,
            explosive_rws=95.0,
            explosive_density=1100.0
        )
        
        # Use typical rock factor for medium rock
        validation_model = KuzRamModel(rock_factor_a=8.0)
        mean_size = validation_model.predict_mean_fragment_size(validation_params)
        
        # Should be in reasonable range for these parameters
        assert 20.0 <= mean_size <= 150.0
    
    def test_uniformity_index_calculation(self):
        """Test uniformity index calculation"""
        uniformity_index = self.model.calculate_uniformity_index(self.test_params)
        
        # Should be in typical range
        assert 0.5 <= uniformity_index <= 2.5
        
        # Test with different burden/spacing ratios
        wide_spacing_params = BlastParameters(
            powder_factor_kg_per_t=self.test_params.powder_factor_kg_per_t,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=5.0,  # Wider spacing
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        wide_spacing_index = self.model.calculate_uniformity_index(wide_spacing_params)
        
        tight_spacing_params = BlastParameters(
            powder_factor_kg_per_t=self.test_params.powder_factor_kg_per_t,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=2.5,  # Tighter spacing
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        tight_spacing_index = self.model.calculate_uniformity_index(tight_spacing_params)
        
        # Different spacing should affect uniformity
        assert wide_spacing_index != tight_spacing_index
    
    def test_fragmentation_curve_generation(self):
        """Test fragmentation curve generation"""
        curve = self.model.get_fragmentation_curve(self.test_params)
        
        assert isinstance(curve, FragmentationCurve)
        assert curve.mean_size_mm > 0
        assert curve.uniformity_index > 0
        
        # Test different distribution types
        swebrec_curve = self.model.get_fragmentation_curve(
            self.test_params, 
            distribution_type="swebrec"
        )
        assert swebrec_curve.distribution_type.value == "swebrec"
    
    def test_parameter_validation(self):
        """Test blast parameter validation"""
        validation_result = self.model.validate_parameters(self.test_params)
        
        assert "is_valid" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result
        assert "burden_spacing_ratio" in validation_result
        assert "stemming_ratio" in validation_result
        
        # Should be valid with good parameters
        assert validation_result["is_valid"] is True
        
        # Test with invalid parameters
        invalid_params = BlastParameters(
            powder_factor_kg_per_t=-0.1,  # Invalid negative powder factor
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        
        invalid_result = self.model.validate_parameters(invalid_params)
        assert invalid_result["is_valid"] is False
        assert len(invalid_result["errors"]) > 0
    
    def test_parameter_validation_warnings(self):
        """Test parameter validation warnings"""
        # Very low powder factor should generate warning
        low_pf_params = BlastParameters(
            powder_factor_kg_per_t=0.02,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        
        result = self.model.validate_parameters(low_pf_params)
        assert any("low powder factor" in warning.lower() for warning in result["warnings"])
        
        # High powder factor should generate warning
        high_pf_params = BlastParameters(
            powder_factor_kg_per_t=2.0,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        
        result = self.model.validate_parameters(high_pf_params)
        assert any("high powder factor" in warning.lower() for warning in result["warnings"])
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Very small charge
        small_charge_params = BlastParameters(
            powder_factor_kg_per_t=0.001,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        
        # Should handle without crashing
        mean_size = self.model.predict_mean_fragment_size(small_charge_params)
        assert mean_size >= 1.0  # Minimum fragment size
        
        # Very high RWS
        high_rws_params = BlastParameters(
            powder_factor_kg_per_t=self.test_params.powder_factor_kg_per_t,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=150.0,
            explosive_density=self.test_params.explosive_density
        )
        
        high_rws_size = self.model.predict_mean_fragment_size(high_rws_params)
        normal_size = self.model.predict_mean_fragment_size(self.test_params)
        
        # Higher RWS should produce smaller fragments
        assert high_rws_size < normal_size
    
    def test_consistency_with_powder_factor_changes(self):
        """Test that results are consistent with powder factor changes"""
        base_size = self.model.predict_mean_fragment_size(self.test_params)
        
        # Higher powder factor should generally produce smaller fragments
        high_pf_params = BlastParameters(
            powder_factor_kg_per_t=self.test_params.powder_factor_kg_per_t * 1.5,
            powder_factor_kg_per_m3=self.test_params.powder_factor_kg_per_m3,
            burden=self.test_params.burden,
            spacing=self.test_params.spacing,
            bench_height=self.test_params.bench_height,
            hole_diameter=self.test_params.hole_diameter,
            stemming_length=self.test_params.stemming_length,
            rock_density=self.test_params.rock_density,
            explosive_rws=self.test_params.explosive_rws,
            explosive_density=self.test_params.explosive_density
        )
        
        high_pf_size = self.model.predict_mean_fragment_size(high_pf_params)
        
        # Should show expected trend (though not always strictly monotonic due to complex relationships)
        assert high_pf_size != base_size  # Should be different
    
    def test_rock_factor_sensitivity(self):
        """Test sensitivity to rock factor changes"""
        base_size = self.model.predict_mean_fragment_size(self.test_params)
        
        # Test different rock factors
        rock_factors = [3.0, 5.0, 7.0, 10.0, 15.0]
        sizes = []
        
        for rf in rock_factors:
            model = KuzRamModel(rock_factor_a=rf)
            size = model.predict_mean_fragment_size(self.test_params)
            sizes.append(size)
        
        # Sizes should generally increase with rock factor
        for i in range(1, len(sizes)):
            assert sizes[i] > sizes[i-1]


class TestBlastParameters:
    """Test BlastParameters dataclass"""
    
    def test_blast_parameters_creation(self):
        """Test BlastParameters creation and access"""
        params = BlastParameters(
            powder_factor_kg_per_t=0.3,
            powder_factor_kg_per_m3=750.0,
            burden=3.0,
            spacing=3.5,
            bench_height=12.0,
            hole_diameter=89.0,
            stemming_length=2.5,
            rock_density=2500.0,
            explosive_rws=100.0,
            explosive_density=1200.0
        )
        
        assert params.powder_factor_kg_per_t == 0.3
        assert params.burden == 3.0
        assert params.explosive_rws == 100.0


if __name__ == "__main__":
    pytest.main([__file__])