"""
Fragmentation Curve Implementation

Provides FragmentationCurve class for representing and manipulating fragment size distributions
using Rosin-Rammler and Swebrec/KCO distributions.
"""

import math
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
from dataclasses import dataclass
from enum import Enum


class DistributionType(Enum):
    """Supported fragmentation distribution types"""
    ROSIN_RAMMLER = "rosin_rammler"
    SWEBREC = "swebrec"
    KCO = "kco"


@dataclass
class SieveAnalysis:
    """Results of sieve analysis"""
    sieve_sizes_mm: List[float]
    mass_fractions: List[float]  # Fraction passing each sieve
    cumulative_passing: List[float]


class FragmentationCurve:
    """
    Represents fragment size distribution with various distribution models.
    
    Supports:
    - Rosin-Rammler distribution: P(x) = 1 - exp(-(x/xc)^n)
    - Swebrec distribution: P(x) = (x/(x+xc))^n  
    - KCO distribution: Modified Swebrec with additional parameters
    """
    
    def __init__(self, 
                 mean_size_mm: float,
                 uniformity_index: float,
                 distribution_type: str = "rosin_rammler"):
        """
        Initialize fragmentation curve.
        
        Args:
            mean_size_mm: Mean fragment size in mm
            uniformity_index: Uniformity index (n parameter)
            distribution_type: Type of distribution to use
        """
        self.mean_size_mm = mean_size_mm
        self.uniformity_index = uniformity_index
        self.distribution_type = DistributionType(distribution_type)
        
        # Validate parameters first
        self._validate_parameters()
        
        # Calculate characteristic size based on distribution type
        self.characteristic_size_mm = self._calculate_characteristic_size()
    
    def _validate_parameters(self) -> None:
        """Validate curve parameters"""
        if self.mean_size_mm <= 0:
            raise ValueError("Mean size must be positive")
        if self.uniformity_index <= 0:
            raise ValueError("Uniformity index must be positive")
        if self.uniformity_index > 10:
            raise ValueError("Uniformity index too large (>10)")
    
    def _calculate_characteristic_size(self) -> float:
        """Calculate characteristic size from mean size and distribution type"""
        if self.distribution_type == DistributionType.ROSIN_RAMMLER:
            # For Rosin-Rammler: xc = mean_size / gamma(1 + 1/n)
            gamma_factor = math.gamma(1 + 1/self.uniformity_index)
            return self.mean_size_mm / gamma_factor
        elif self.distribution_type in [DistributionType.SWEBREC, DistributionType.KCO]:
            # For Swebrec: approximate relationship
            return self.mean_size_mm * 0.693  # ln(2) approximation
        else:
            return self.mean_size_mm
    
    def get_passing_percentage(self, size_mm: float) -> float:
        """
        Calculate percentage passing for given size.
        
        Args:
            size_mm: Fragment size in mm
            
        Returns:
            Percentage passing (0-100)
        """
        if size_mm <= 0:
            return 0.0
        
        x = size_mm
        xc = self.characteristic_size_mm
        n = self.uniformity_index
        
        if self.distribution_type == DistributionType.ROSIN_RAMMLER:
            # P(x) = 1 - exp(-(x/xc)^n)
            passing_fraction = 1.0 - math.exp(-((x / xc) ** n))
        elif self.distribution_type == DistributionType.SWEBREC:
            # P(x) = (x/(x+xc))^n
            passing_fraction = (x / (x + xc)) ** n
        elif self.distribution_type == DistributionType.KCO:
            # Modified Swebrec with additional shape parameter
            # P(x) = (x^n) / (x^n + xc^n)
            passing_fraction = (x ** n) / (x ** n + xc ** n)
        else:
            raise ValueError(f"Unsupported distribution type: {self.distribution_type}")
        
        return min(100.0, max(0.0, passing_fraction * 100.0))
    
    def get_characteristic_sizes(self) -> Dict[str, float]:
        """
        Calculate characteristic sizes (P10, P50, P80, etc.).
        
        Returns:
            Dictionary with characteristic sizes in mm
        """
        percentiles = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
        sizes = {}
        
        for p in percentiles:
            size = self._find_size_for_passing(p)
            sizes[f"P{p}"] = size
        
        # Add mean size
        sizes["mean"] = self.mean_size_mm
        
        return sizes
    
    def _find_size_for_passing(self, target_passing: float) -> float:
        """
        Find fragment size for target passing percentage using numerical methods.
        
        Args:
            target_passing: Target passing percentage (0-100)
            
        Returns:
            Fragment size in mm
        """
        if target_passing <= 0:
            return 0.0
        if target_passing >= 100:
            return float('inf')
        
        # Use analytical solutions where possible
        target_fraction = target_passing / 100.0
        xc = self.characteristic_size_mm
        n = self.uniformity_index
        
        if self.distribution_type == DistributionType.ROSIN_RAMMLER:
            # Analytical solution: x = xc * (-ln(1-P))^(1/n)
            if target_fraction >= 0.999:
                target_fraction = 0.999  # Avoid numerical issues
            return xc * ((-math.log(1 - target_fraction)) ** (1/n))
        
        elif self.distribution_type == DistributionType.SWEBREC:
            # Analytical solution: x = xc * P^(1/n) / (1 - P^(1/n))
            p_power = target_fraction ** (1/n)
            if p_power >= 0.999:
                p_power = 0.999
            return xc * p_power / (1 - p_power)
        
        elif self.distribution_type == DistributionType.KCO:
            # Analytical solution: x = xc * (P/(1-P))^(1/n)
            if target_fraction >= 0.999:
                target_fraction = 0.999
            return xc * ((target_fraction / (1 - target_fraction)) ** (1/n))
        
        else:
            # Fallback to numerical solution
            return self._numerical_size_search(target_passing)
    
    def _numerical_size_search(self, target_passing: float) -> float:
        """Numerical search for size at target passing percentage"""
        # Binary search
        low, high = 0.1, self.mean_size_mm * 10
        tolerance = 0.01  # 0.01mm tolerance
        
        for _ in range(100):  # Max iterations
            mid = (low + high) / 2
            passing = self.get_passing_percentage(mid)
            
            if abs(passing - target_passing) < 0.1:  # 0.1% tolerance
                return mid
            
            if passing < target_passing:
                low = mid
            else:
                high = mid
            
            if high - low < tolerance:
                break
        
        return (low + high) / 2
    
    def get_sieve_analysis(self, sieve_sizes_mm: Optional[List[float]] = None) -> SieveAnalysis:
        """
        Generate sieve analysis for standard or custom sieve sizes.
        
        Args:
            sieve_sizes_mm: Custom sieve sizes, or None for standard sizes
            
        Returns:
            SieveAnalysis object with results
        """
        if sieve_sizes_mm is None:
            # Standard sieve sizes in mm
            sieve_sizes_mm = [
                0.075, 0.15, 0.3, 0.6, 1.18, 2.36, 4.75, 9.5, 
                12.5, 19, 25, 37.5, 50, 75, 100, 150, 200, 300
            ]
        
        # Sort sizes
        sieve_sizes_mm = sorted(sieve_sizes_mm)
        
        # Calculate passing percentages
        cumulative_passing = [self.get_passing_percentage(size) for size in sieve_sizes_mm]
        
        # Calculate mass fractions (retained on each sieve)
        mass_fractions = []
        prev_passing = 0.0
        
        for passing in cumulative_passing:
            fraction_retained = (passing - prev_passing) / 100.0
            mass_fractions.append(fraction_retained)
            prev_passing = passing
        
        return SieveAnalysis(
            sieve_sizes_mm=sieve_sizes_mm,
            mass_fractions=mass_fractions,
            cumulative_passing=[p/100.0 for p in cumulative_passing]
        )
    
    def get_visualization_data(self, num_points: int = 100) -> Dict[str, List[float]]:
        """
        Generate data points for curve visualization.
        
        Args:
            num_points: Number of points to generate
            
        Returns:
            Dictionary with size and passing data for plotting
        """
        # Generate logarithmically spaced sizes
        min_size = 0.1
        max_size = max(1000.0, self.mean_size_mm * 5)
        
        sizes = np.logspace(math.log10(min_size), math.log10(max_size), num_points)
        passing_percentages = [self.get_passing_percentage(size) for size in sizes]
        
        return {
            "sizes_mm": sizes.tolist(),
            "passing_percentage": passing_percentages
        }
    
    def compare_with_measured(self, measured_curve: 'FragmentationCurve') -> Dict[str, float]:
        """
        Compare this curve with measured fragmentation data.
        
        Args:
            measured_curve: Measured fragmentation curve
            
        Returns:
            Dictionary with comparison metrics
        """
        # Compare characteristic sizes
        predicted_sizes = self.get_characteristic_sizes()
        measured_sizes = measured_curve.get_characteristic_sizes()
        
        # Calculate relative errors
        errors = {}
        for key in ["P50", "P80"]:
            if key in predicted_sizes and key in measured_sizes:
                predicted = predicted_sizes[key]
                measured = measured_sizes[key]
                if measured > 0:
                    relative_error = abs(predicted - measured) / measured
                    errors[f"{key}_relative_error"] = relative_error
        
        # Calculate R-squared for curve fit
        test_sizes = [1, 5, 10, 25, 50, 100, 200]
        predicted_passing = [self.get_passing_percentage(s) for s in test_sizes]
        measured_passing = [measured_curve.get_passing_percentage(s) for s in test_sizes]
        
        # Calculate R-squared
        mean_measured = np.mean(measured_passing)
        ss_tot = sum((m - mean_measured)**2 for m in measured_passing)
        ss_res = sum((p - m)**2 for p, m in zip(predicted_passing, measured_passing))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            **errors,
            "r_squared": r_squared,
            "mean_absolute_error": np.mean([abs(p - m) for p, m in zip(predicted_passing, measured_passing)])
        }
    
    def fit_to_data(self, sizes_mm: List[float], passing_percentages: List[float]) -> 'FragmentationCurve':
        """
        Fit curve parameters to measured data points.
        
        Args:
            sizes_mm: Fragment sizes in mm
            passing_percentages: Corresponding passing percentages
            
        Returns:
            New FragmentationCurve fitted to the data
        """
        from scipy.optimize import minimize_scalar
        
        def objective(uniformity_index):
            """Objective function for parameter fitting"""
            test_curve = FragmentationCurve(
                mean_size_mm=self.mean_size_mm,
                uniformity_index=uniformity_index,
                distribution_type=self.distribution_type.value
            )
            
            # Calculate sum of squared errors
            error = 0
            for size, target_passing in zip(sizes_mm, passing_percentages):
                predicted_passing = test_curve.get_passing_percentage(size)
                error += (predicted_passing - target_passing) ** 2
            
            return error
        
        # Optimize uniformity index
        result = minimize_scalar(objective, bounds=(0.1, 5.0), method='bounded')
        optimal_n = result.x
        
        # Estimate mean size from P50
        if len(sizes_mm) >= 3:
            # Find P50 from data
            p50_size = np.interp(50.0, passing_percentages, sizes_mm)
            
            return FragmentationCurve(
                mean_size_mm=p50_size,
                uniformity_index=optimal_n,
                distribution_type=self.distribution_type.value
            )
        
        return FragmentationCurve(
            mean_size_mm=self.mean_size_mm,
            uniformity_index=optimal_n,
            distribution_type=self.distribution_type.value
        )
    
    def fit_from_measurements(self, fragment_sizes: List[float]) -> None:
        """
        Fit curve parameters from measured fragment sizes.
        
        Args:
            fragment_sizes: List of individual fragment sizes in mm
        """
        if not fragment_sizes:
            raise ValueError("No fragment sizes provided")
        
        # Calculate statistics from measurements
        sizes_array = np.array(fragment_sizes)
        
        # Calculate mean size
        self.mean_size_mm = float(np.mean(sizes_array))
        
        # Estimate uniformity index from size distribution
        # Use coefficient of variation to estimate uniformity
        cv = np.std(sizes_array) / np.mean(sizes_array)
        
        # Empirical relationship between CV and uniformity index for Rosin-Rammler
        if self.distribution_type == DistributionType.ROSIN_RAMMLER:
            # For Rosin-Rammler, lower n means higher variability
            self.uniformity_index = max(0.5, min(5.0, 1.0 / (cv + 0.1)))
        else:
            # For other distributions, use similar relationship
            self.uniformity_index = max(0.5, min(5.0, 1.0 / cv))
        
        # Recalculate characteristic size with new parameters
        self.characteristic_size_mm = self._calculate_characteristic_size()
    
    @property
    def characteristic_size(self) -> float:
        """Get characteristic size (for compatibility with ML pipeline)"""
        return self.characteristic_size_mm
    
    @property
    def uniformity_index_n(self) -> float:
        """Get uniformity index (for compatibility with ML pipeline)"""
        return self.uniformity_index