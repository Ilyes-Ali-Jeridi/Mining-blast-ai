"""
Kuz-Ram Fragmentation Model Implementation

Implements the Kuznetsov form of the Kuz-Ram fragmentation model for predicting
mean fragment size and size distribution from blast parameters.
"""

import math
from typing import Optional, Dict, Any
import numpy as np
from dataclasses import dataclass

from .fragmentation_curve import FragmentationCurve


@dataclass
class BlastParameters:
    """Parameters required for Kuz-Ram calculations"""
    powder_factor_kg_per_t: float  # kg/t
    powder_factor_kg_per_m3: float  # kg/m³
    burden: float  # m
    spacing: float  # m
    bench_height: float  # m
    hole_diameter: float  # mm
    stemming_length: float  # m
    rock_density: float  # kg/m³
    explosive_rws: float  # Relative Weight Strength (%)
    explosive_density: float  # kg/m³


class KuzRamModel:
    """
    Implements the Kuznetsov form of Kuz-Ram fragmentation model.
    
    The model predicts mean fragment size using:
    X50 = A * (V/Q)^0.8 * Q^0.167 * (115/RWS)^0.633
    
    Where:
    - A = Rock Factor (site-specific constant)
    - V = Rock volume per hole (m³)
    - Q = Explosive charge per hole (kg)
    - RWS = Relative Weight Strength of explosive (%)
    """
    
    def __init__(self, rock_factor_a: float = 7.0):
        """
        Initialize Kuz-Ram model with rock factor.
        
        Args:
            rock_factor_a: Rock factor A (default 7.0 for medium rock)
        """
        self.rock_factor_a = rock_factor_a
        self._validate_rock_factor()
    
    def _validate_rock_factor(self) -> None:
        """Validate rock factor is within reasonable range"""
        if not 1.0 <= self.rock_factor_a <= 20.0:
            raise ValueError(f"Rock factor A must be between 1.0 and 20.0, got {self.rock_factor_a}")
    
    def calculate_powder_factors(self, 
                               charge_kg: float,
                               rock_volume_m3: float,
                               rock_density_kg_per_m3: float) -> Dict[str, float]:
        """
        Calculate powder factors in different units.
        
        Args:
            charge_kg: Explosive charge weight (kg)
            rock_volume_m3: Rock volume (m³)
            rock_density_kg_per_m3: Rock density (kg/m³)
            
        Returns:
            Dictionary with powder factors in kg/t and kg/m³
        """
        if charge_kg <= 0 or rock_volume_m3 <= 0 or rock_density_kg_per_m3 <= 0:
            raise ValueError("All parameters must be positive")
        
        rock_mass_tonnes = rock_volume_m3 * rock_density_kg_per_m3 / 1000.0
        
        return {
            "kg_per_tonne": charge_kg / rock_mass_tonnes,
            "kg_per_m3": charge_kg / rock_volume_m3
        }
    
    def predict_mean_fragment_size(self, params: BlastParameters) -> float:
        """
        Calculate mean fragment size using Kuznetsov form of Kuz-Ram.
        
        The Kuznetsov equation is: X50 = A * (V/Q)^0.8 * Q^0.167 * (115/RWS)^0.633
        Where:
        - A = Rock factor (site-specific constant)
        - V = Rock volume per hole (m³)
        - Q = Explosive charge per hole (kg)
        - RWS = Relative Weight Strength of explosive (%)
        
        Args:
            params: Blast parameters for calculation
            
        Returns:
            Mean fragment size X50 in mm
        """
        # Calculate rock volume per hole
        rock_volume = params.burden * params.spacing * params.bench_height
        
        # Calculate charge per hole from powder factor
        rock_mass_tonnes = rock_volume * params.rock_density / 1000.0
        charge_kg = params.powder_factor_kg_per_t * rock_mass_tonnes
        
        if charge_kg <= 0 or rock_volume <= 0:
            raise ValueError("Invalid blast parameters: charge or volume is zero or negative")
        
        # Kuznetsov form: X50 = A * (V/Q)^0.8 * Q^0.167 * (115/RWS)^0.633
        # Note: The original Kuz-Ram gives results in meters, but we need reasonable fragment sizes
        volume_charge_ratio = rock_volume / charge_kg
        charge_factor = charge_kg ** 0.167
        rws_factor = (115.0 / params.explosive_rws) ** 0.633
        
        # Apply the formula - result is in meters in the original formulation
        x50_m = self.rock_factor_a * (volume_charge_ratio ** 0.8) * charge_factor * rws_factor
        
        # The original Kuz-Ram formula often needs scaling for practical results
        # Apply a scaling factor to get realistic fragment sizes (typically 0.001-0.01)
        scaling_factor = 0.005  # Empirical scaling to get reasonable mm values
        x50_mm = x50_m * scaling_factor * 1000.0
        
        return max(x50_mm, 1.0)  # Minimum 1mm fragment size
    
    def calculate_uniformity_index(self, params: BlastParameters) -> float:
        """
        Calculate uniformity index for fragmentation distribution.
        
        Empirical relationship based on blast geometry and explosive properties.
        
        Args:
            params: Blast parameters
            
        Returns:
            Uniformity index n (typically 0.5 to 2.5)
        """
        # Empirical relationship for uniformity index
        # Based on burden/spacing ratio and stemming effectiveness
        burden_spacing_ratio = params.burden / params.spacing
        stemming_ratio = params.stemming_length / params.bench_height
        
        # Base uniformity index
        n_base = 1.25
        
        # Adjustments based on geometry
        if burden_spacing_ratio > 1.2:
            n_base *= 0.9  # More uniform with higher burden/spacing
        elif burden_spacing_ratio < 0.8:
            n_base *= 1.1  # Less uniform with lower burden/spacing
        
        # Stemming effect
        if stemming_ratio < 0.2:
            n_base *= 1.15  # Poor stemming increases variability
        elif stemming_ratio > 0.4:
            n_base *= 0.95  # Good stemming improves uniformity
        
        return max(0.5, min(2.5, n_base))
    
    def get_fragmentation_curve(self, 
                              params: BlastParameters,
                              distribution_type: str = "rosin_rammler") -> FragmentationCurve:
        """
        Generate complete fragmentation curve from blast parameters.
        
        Args:
            params: Blast parameters
            distribution_type: Type of distribution ("rosin_rammler" or "swebrec")
            
        Returns:
            FragmentationCurve object with complete size distribution
        """
        mean_size = self.predict_mean_fragment_size(params)
        uniformity_index = self.calculate_uniformity_index(params)
        
        return FragmentationCurve(
            mean_size_mm=mean_size,
            uniformity_index=uniformity_index,
            distribution_type=distribution_type
        )
    
    def validate_parameters(self, params: BlastParameters) -> Dict[str, Any]:
        """
        Validate blast parameters and return validation results.
        
        Args:
            params: Blast parameters to validate
            
        Returns:
            Dictionary with validation results and warnings
        """
        warnings = []
        errors = []
        
        # Check powder factor ranges
        if params.powder_factor_kg_per_t < 0.05:
            warnings.append("Very low powder factor may result in poor fragmentation")
        elif params.powder_factor_kg_per_t > 1.5:
            warnings.append("High powder factor may be uneconomical")
        
        # Check burden/spacing ratio
        burden_spacing_ratio = params.burden / params.spacing
        if burden_spacing_ratio < 0.5 or burden_spacing_ratio > 2.0:
            warnings.append(f"Unusual burden/spacing ratio: {burden_spacing_ratio:.2f}")
        
        # Check hole diameter vs burden
        if params.hole_diameter > params.burden * 100:  # Convert burden to mm
            warnings.append("Hole diameter is large relative to burden")
        
        # Check stemming
        stemming_ratio = params.stemming_length / params.bench_height
        if stemming_ratio < 0.15:
            warnings.append("Low stemming may cause poor energy utilization")
        elif stemming_ratio > 0.5:
            warnings.append("Excessive stemming may reduce fragmentation")
        
        # Check for errors
        if params.powder_factor_kg_per_t <= 0:
            errors.append("Powder factor must be positive")
        if params.burden <= 0 or params.spacing <= 0:
            errors.append("Burden and spacing must be positive")
        if params.bench_height <= 0:
            errors.append("Bench height must be positive")
        if params.explosive_rws <= 0 or params.explosive_rws > 200:
            errors.append("Explosive RWS must be between 0 and 200%")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "burden_spacing_ratio": burden_spacing_ratio,
            "stemming_ratio": stemming_ratio
        }