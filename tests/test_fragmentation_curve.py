"""
Unit tests for FragmentationCurve class.

Tests distribution calculations, characteristic sizes, and curve fitting functionality.
"""

import pytest
import math
import numpy as np
from src.drill_blast_system.physics_models.fragmentation_curve import (
    FragmentationCurve, 
    DistributionType, 
    SieveAnalysis
)


class TestFragmentationCurve:
    """Test cases for FragmentationCurve class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.curve = FragmentationCurve(
            mean_size_mm=50.0,
            uniformity_index=1.25,
            distribution_type="rosin_rammler"
        )
    
    def test_initialization(self):
        """Test curve initialization"""
        assert self.curve.mean_size_mm == 50.0
        assert self.curve.uniformity_index == 1.25
        assert self.curve.distribution_type == DistributionType.ROSIN_RAMMLER
        assert self.curve.characteristic_size_mm > 0
    
    def test_initialization_validation(self):
        """Test initialization parameter validation"""
        # Invalid mean size
        with pytest.raises(ValueError):
            FragmentationCurve(mean_size_mm=-10.0, uniformity_index=1.0)
        
        # Invalid uniformity index
        with pytest.raises(ValueError):
            FragmentationCurve(mean_size_mm=50.0, uniformity_index=0.0)
        
        with pytest.raises(ValueError):
            FragmentationCurve(mean_size_mm=50.0, uniformity_index=15.0)
    
    def test_rosin_rammler_distribution(self):
        """Test Rosin-Rammler distribution calculations"""
        # Test known points
        passing_0 = self.curve.get_passing_percentage(0.0)
        assert passing_0 == 0.0
        
        # At characteristic size, should be around 63.2% for Rosin-Rammler
        xc = self.curve.characteristic_size_mm
        passing_xc = self.curve.get_passing_percentage(xc)
        expected_passing = (1 - math.exp(-1)) * 100  # ~63.2%
        assert abs(passing_xc - expected_passing) < 1.0
        
        # Very large size should approach 100%
        passing_large = self.curve.get_passing_percentage(1000.0)
        assert passing_large > 99.0
    
    def test_swebrec_distribution(self):
        """Test Swebrec distribution calculations"""
        swebrec_curve = FragmentationCurve(
            mean_size_mm=50.0,
            uniformity_index=1.5,
            distribution_type="swebrec"
        )
        
        # Test boundary conditions
        assert swebrec_curve.get_passing_percentage(0.0) == 0.0
        
        # Test monotonic increase
        sizes = [1, 10, 50, 100, 200]
        passing_values = [swebrec_curve.get_passing_percentage(s) for s in sizes]
        
        for i in range(1, len(passing_values)):
            assert passing_values[i] >= passing_values[i-1]
    
    def test_kco_distribution(self):
        """Test KCO distribution calculations"""
        kco_curve = FragmentationCurve(
            mean_size_mm=50.0,
            uniformity_index=2.0,
            distribution_type="kco"
        )
        
        # Test boundary conditions
        assert kco_curve.get_passing_percentage(0.0) == 0.0
        
        # Test that it produces reasonable values
        p50_approx = kco_curve.get_passing_percentage(50.0)
        assert 30.0 <= p50_approx <= 70.0
    
    def test_characteristic_sizes(self):
        """Test characteristic size calculations"""
        char_sizes = self.curve.get_characteristic_sizes()
        
        # Check that all expected percentiles are present
        expected_keys = ["P10", "P20", "P30", "P40", "P50", "P60", "P70", "P80", "P90", "P95", "mean"]
        for key in expected_keys:
            assert key in char_sizes
            assert char_sizes[key] > 0
        
        # Check monotonic increase
        percentiles = ["P10", "P20", "P30", "P40", "P50", "P60", "P70", "P80", "P90", "P95"]
        for i in range(1, len(percentiles)):
            assert char_sizes[percentiles[i]] >= char_sizes[percentiles[i-1]]
        
        # P50 should be close to mean for well-behaved distributions
        p50 = char_sizes["P50"]
        mean = char_sizes["mean"]
        assert abs(p50 - mean) / mean < 0.5  # Within 50%
    
    def test_sieve_analysis_standard(self):
        """Test sieve analysis with standard sieve sizes"""
        sieve_analysis = self.curve.get_sieve_analysis()
        
        assert isinstance(sieve_analysis, SieveAnalysis)
        assert len(sieve_analysis.sieve_sizes_mm) > 0
        assert len(sieve_analysis.mass_fractions) == len(sieve_analysis.sieve_sizes_mm)
        assert len(sieve_analysis.cumulative_passing) == len(sieve_analysis.sieve_sizes_mm)
        
        # Mass fractions should sum to approximately 1.0
        total_mass = sum(sieve_analysis.mass_fractions)
        assert abs(total_mass - 1.0) < 0.1
        
        # Cumulative passing should be monotonic
        for i in range(1, len(sieve_analysis.cumulative_passing)):
            assert sieve_analysis.cumulative_passing[i] >= sieve_analysis.cumulative_passing[i-1]
    
    def test_sieve_analysis_custom(self):
        """Test sieve analysis with custom sieve sizes"""
        custom_sizes = [1.0, 5.0, 10.0, 25.0, 50.0, 100.0]
        sieve_analysis = self.curve.get_sieve_analysis(custom_sizes)
        
        assert sieve_analysis.sieve_sizes_mm == custom_sizes
        assert len(sieve_analysis.mass_fractions) == len(custom_sizes)
    
    def test_visualization_data(self):
        """Test visualization data generation"""
        viz_data = self.curve.get_visualization_data(num_points=50)
        
        assert "sizes_mm" in viz_data
        assert "passing_percentage" in viz_data
        assert len(viz_data["sizes_mm"]) == 50
        assert len(viz_data["passing_percentage"]) == 50
        
        # Check monotonic increase
        for i in range(1, len(viz_data["passing_percentage"])):
            assert viz_data["passing_percentage"][i] >= viz_data["passing_percentage"][i-1]
        
        # Check reasonable ranges
        assert all(0 <= p <= 100 for p in viz_data["passing_percentage"])
        assert all(s > 0 for s in viz_data["sizes_mm"])
    
    def test_curve_comparison(self):
        """Test curve comparison functionality"""
        # Create a similar curve for comparison
        similar_curve = FragmentationCurve(
            mean_size_mm=55.0,  # Slightly different
            uniformity_index=1.3,
            distribution_type="rosin_rammler"
        )
        
        comparison = self.curve.compare_with_measured(similar_curve)
        
        assert "P50_relative_error" in comparison
        assert "P80_relative_error" in comparison
        assert "r_squared" in comparison
        assert "mean_absolute_error" in comparison
        
        # Should have reasonable R-squared for similar curves
        assert comparison["r_squared"] > 0.8
        
        # Relative errors should be small for similar curves
        assert comparison["P50_relative_error"] < 0.2
        assert comparison["P80_relative_error"] < 0.2
    
    def test_analytical_solutions(self):
        """Test analytical solutions for size calculations"""
        # Test P50 calculation for Rosin-Rammler
        p50 = self.curve._find_size_for_passing(50.0)
        
        # Verify by calculating passing percentage at P50
        passing_at_p50 = self.curve.get_passing_percentage(p50)
        assert abs(passing_at_p50 - 50.0) < 0.1
        
        # Test P80
        p80 = self.curve._find_size_for_passing(80.0)
        passing_at_p80 = self.curve.get_passing_percentage(p80)
        assert abs(passing_at_p80 - 80.0) < 0.1
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Very small uniformity index
        fine_curve = FragmentationCurve(
            mean_size_mm=50.0,
            uniformity_index=0.5,
            distribution_type="rosin_rammler"
        )
        
        char_sizes = fine_curve.get_characteristic_sizes()
        assert char_sizes["P80"] > char_sizes["P50"] > char_sizes["P20"]
        
        # Very large uniformity index
        coarse_curve = FragmentationCurve(
            mean_size_mm=50.0,
            uniformity_index=3.0,
            distribution_type="rosin_rammler"
        )
        
        char_sizes = coarse_curve.get_characteristic_sizes()
        assert char_sizes["P80"] > char_sizes["P50"] > char_sizes["P20"]
    
    def test_distribution_type_differences(self):
        """Test that different distribution types produce different results"""
        rosin_rammler = FragmentationCurve(50.0, 1.5, "rosin_rammler")
        swebrec = FragmentationCurve(50.0, 1.5, "swebrec")
        kco = FragmentationCurve(50.0, 1.5, "kco")
        
        test_size = 50.0
        rr_passing = rosin_rammler.get_passing_percentage(test_size)
        sw_passing = swebrec.get_passing_percentage(test_size)
        kco_passing = kco.get_passing_percentage(test_size)
        
        # Should produce different results
        assert rr_passing != sw_passing
        assert sw_passing != kco_passing
        assert rr_passing != kco_passing
    
    def test_numerical_stability(self):
        """Test numerical stability with extreme parameters"""
        # Very fine material
        fine_curve = FragmentationCurve(
            mean_size_mm=0.1,
            uniformity_index=0.8,
            distribution_type="rosin_rammler"
        )
        
        # Should handle without numerical issues
        p80 = fine_curve.get_characteristic_sizes()["P80"]
        assert p80 > 0 and not math.isinf(p80)
        
        # Very coarse material
        coarse_curve = FragmentationCurve(
            mean_size_mm=1000.0,
            uniformity_index=2.5,
            distribution_type="rosin_rammler"
        )
        
        p50 = coarse_curve.get_characteristic_sizes()["P50"]
        assert p50 > 0 and not math.isinf(p50)


class TestSieveAnalysis:
    """Test SieveAnalysis dataclass"""
    
    def test_sieve_analysis_creation(self):
        """Test SieveAnalysis creation"""
        sieve_sizes = [1.0, 5.0, 10.0, 25.0]
        mass_fractions = [0.1, 0.3, 0.4, 0.2]
        cumulative_passing = [0.1, 0.4, 0.8, 1.0]
        
        analysis = SieveAnalysis(
            sieve_sizes_mm=sieve_sizes,
            mass_fractions=mass_fractions,
            cumulative_passing=cumulative_passing
        )
        
        assert analysis.sieve_sizes_mm == sieve_sizes
        assert analysis.mass_fractions == mass_fractions
        assert analysis.cumulative_passing == cumulative_passing


if __name__ == "__main__":
    pytest.main([__file__])