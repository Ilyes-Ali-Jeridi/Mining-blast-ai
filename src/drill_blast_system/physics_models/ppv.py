"""
PPV (Peak Particle Velocity) Prediction Model Implementation

Implements empirical PPV prediction using scaled charge approach and distance calculations.
Supports multiple charges, delays, and site-specific parameter overrides.
"""

import math
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
from dataclasses import dataclass
from enum import Enum


@dataclass
class Coordinates3D:
    """3D coordinates in meters"""
    x: float
    y: float
    z: float


@dataclass
class Charge:
    """Individual explosive charge"""
    charge_id: str
    coordinates: Coordinates3D
    weight_kg: float
    delay_ms: int
    explosive_type: str = "ANFO"


@dataclass
class Receptor:
    """Sensitive receptor location"""
    receptor_id: str
    coordinates: Coordinates3D
    name: str
    ppv_limit_mm_per_s: float
    description: Optional[str] = None


class PPVModel:
    """
    Empirical PPV prediction using scaled charge approach.
    
    Uses the standard form: PPV = k * (W^a / R^b)
    Where:
    - PPV = Peak Particle Velocity (mm/s)
    - k = Site constant (default 1.4)
    - W = Charge weight (kg)
    - R = Distance (m)
    - a = Charge exponent (default 1/3)
    - b = Distance exponent (default 1.6)
    """
    
    def __init__(self, 
                 k: float = 1.4, 
                 a: float = 1/3, 
                 b: float = 1.6):
        """
        Initialize PPV model with empirical constants.
        
        Args:
            k: Site constant (typical range 0.5-5.0)
            a: Charge weight exponent (typical range 0.2-0.5)
            b: Distance exponent (typical range 1.0-2.0)
        """
        self.k = k
        self.a = a
        self.b = b
        self._validate_constants()
    
    def _validate_constants(self) -> None:
        """Validate PPV model constants are within reasonable ranges"""
        if not 0.1 <= self.k <= 5000.0:  # Expanded range for different unit systems
            raise ValueError(f"Site constant k must be between 0.1 and 5000.0, got {self.k}")
        if not 0.1 <= self.a <= 1.0:
            raise ValueError(f"Charge exponent a must be between 0.1 and 1.0, got {self.a}")
        if not 0.5 <= self.b <= 3.0:
            raise ValueError(f"Distance exponent b must be between 0.5 and 3.0, got {self.b}")
    
    def calculate_distance_3d(self, 
                            point1: Coordinates3D, 
                            point2: Coordinates3D) -> float:
        """
        Calculate 3D Euclidean distance between two points.
        
        Args:
            point1: First coordinate point
            point2: Second coordinate point
            
        Returns:
            Distance in meters
        """
        dx = point2.x - point1.x
        dy = point2.y - point1.y
        dz = point2.z - point1.z
        
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        return max(distance, 1.0)  # Minimum 1m distance to avoid division issues
    
    def predict_ppv_single_charge(self, 
                                charge_weight_kg: float, 
                                distance_m: float) -> float:
        """
        Predict PPV for a single charge using scaled charge approach.
        
        Args:
            charge_weight_kg: Explosive charge weight in kg
            distance_m: Distance from charge to receptor in meters
            
        Returns:
            Predicted PPV in mm/s
        """
        if charge_weight_kg <= 0:
            return 0.0
        if distance_m <= 0:
            raise ValueError("Distance must be positive")
        
        # PPV = k * W^a / R^b
        ppv = self.k * (charge_weight_kg ** self.a) / (distance_m ** self.b)
        
        return max(ppv, 0.0)
    
    def predict_ppv_charge_to_receptor(self, 
                                     charge: Charge, 
                                     receptor: Receptor) -> float:
        """
        Predict PPV from a single charge to a receptor.
        
        Args:
            charge: Charge object with location and weight
            receptor: Receptor object with location
            
        Returns:
            Predicted PPV in mm/s
        """
        distance = self.calculate_distance_3d(charge.coordinates, receptor.coordinates)
        return self.predict_ppv_single_charge(charge.weight_kg, distance)
    
    def predict_ppv_multiple_charges(self, 
                                   charges: List[Charge], 
                                   receptor: Receptor,
                                   aggregation_method: str = "rms") -> Dict[str, float]:
        """
        Predict PPV from multiple charges to a receptor.
        
        Args:
            charges: List of charges
            receptor: Target receptor
            aggregation_method: Method to combine PPV from multiple charges
                              ("rms", "algebraic", "maximum")
            
        Returns:
            Dictionary with PPV predictions and component analysis
        """
        if not charges:
            return {"total_ppv": 0.0, "individual_ppvs": {}, "method": aggregation_method}
        
        # Calculate PPV from each charge
        individual_ppvs = {}
        ppv_values = []
        
        for charge in charges:
            ppv = self.predict_ppv_charge_to_receptor(charge, receptor)
            individual_ppvs[charge.charge_id] = ppv
            ppv_values.append(ppv)
        
        # Aggregate PPV values
        if aggregation_method == "rms":
            # Root Mean Square - most conservative for simultaneous firing
            total_ppv = math.sqrt(sum(ppv**2 for ppv in ppv_values))
        elif aggregation_method == "algebraic":
            # Simple algebraic sum - assumes perfect constructive interference
            total_ppv = sum(ppv_values)
        elif aggregation_method == "maximum":
            # Maximum individual PPV - assumes no interference
            total_ppv = max(ppv_values) if ppv_values else 0.0
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation_method}")
        
        return {
            "total_ppv": total_ppv,
            "individual_ppvs": individual_ppvs,
            "method": aggregation_method,
            "max_individual": max(ppv_values) if ppv_values else 0.0,
            "num_charges": len(charges)
        }
    
    def predict_ppv_with_delays(self, 
                              charges: List[Charge], 
                              receptor: Receptor,
                              delay_interference_factor: float = 0.7) -> Dict[str, float]:
        """
        Predict PPV considering delay timing between charges.
        
        Args:
            charges: List of charges with delay timing
            receptor: Target receptor
            delay_interference_factor: Factor to reduce interference for delayed charges (0-1)
            
        Returns:
            Dictionary with PPV predictions considering delays
        """
        if not charges:
            return {"total_ppv": 0.0, "delay_groups": {}}
        
        # Group charges by delay
        delay_groups = {}
        for charge in charges:
            delay = charge.delay_ms
            if delay not in delay_groups:
                delay_groups[delay] = []
            delay_groups[delay].append(charge)
        
        # Calculate PPV for each delay group
        delay_ppvs = {}
        for delay, delay_charges in delay_groups.items():
            group_result = self.predict_ppv_multiple_charges(
                delay_charges, receptor, "rms"
            )
            delay_ppvs[delay] = group_result["total_ppv"]
        
        # Combine delay groups with interference factor
        if len(delay_groups) == 1:
            # Single delay - no interference reduction
            total_ppv = list(delay_ppvs.values())[0]
        else:
            # Multiple delays - apply interference factor
            sorted_delays = sorted(delay_ppvs.keys())
            total_ppv = delay_ppvs[sorted_delays[0]]  # First delay at full strength
            
            for delay in sorted_delays[1:]:
                # Subsequent delays reduced by interference factor
                total_ppv += delay_ppvs[delay] * delay_interference_factor
        
        return {
            "total_ppv": total_ppv,
            "delay_groups": delay_ppvs,
            "interference_factor": delay_interference_factor,
            "num_delay_groups": len(delay_groups)
        }
    
    def validate_against_limits(self, 
                              charges: List[Charge], 
                              receptors: List[Receptor]) -> Dict[str, Dict]:
        """
        Validate predicted PPV against receptor limits.
        
        Args:
            charges: List of charges
            receptors: List of receptors with PPV limits
            
        Returns:
            Dictionary with validation results for each receptor
        """
        results = {}
        
        for receptor in receptors:
            # Predict PPV with delays
            ppv_result = self.predict_ppv_with_delays(charges, receptor)
            predicted_ppv = ppv_result["total_ppv"]
            
            # Check against limit
            is_compliant = predicted_ppv <= receptor.ppv_limit_mm_per_s
            safety_margin = receptor.ppv_limit_mm_per_s - predicted_ppv
            safety_factor = receptor.ppv_limit_mm_per_s / predicted_ppv if predicted_ppv > 0 else float('inf')
            
            results[receptor.receptor_id] = {
                "predicted_ppv": predicted_ppv,
                "limit": receptor.ppv_limit_mm_per_s,
                "is_compliant": is_compliant,
                "safety_margin": safety_margin,
                "safety_factor": safety_factor,
                "exceedance": max(0, predicted_ppv - receptor.ppv_limit_mm_per_s),
                "ppv_details": ppv_result
            }
        
        return results
    
    def calculate_safe_charge_weight(self, 
                                   distance_m: float, 
                                   target_ppv_mm_per_s: float) -> float:
        """
        Calculate maximum safe charge weight for given distance and PPV limit.
        
        Args:
            distance_m: Distance to receptor in meters
            target_ppv_mm_per_s: Target PPV limit in mm/s
            
        Returns:
            Maximum safe charge weight in kg
        """
        if distance_m <= 0 or target_ppv_mm_per_s <= 0:
            return 0.0
        
        # Rearrange PPV = k * W^a / R^b to solve for W
        # W = (PPV * R^b / k)^(1/a)
        safe_weight = ((target_ppv_mm_per_s * (distance_m ** self.b)) / self.k) ** (1/self.a)
        
        return max(safe_weight, 0.0)
    
    def calculate_safe_distance(self, 
                              charge_weight_kg: float, 
                              target_ppv_mm_per_s: float) -> float:
        """
        Calculate minimum safe distance for given charge weight and PPV limit.
        
        Args:
            charge_weight_kg: Charge weight in kg
            target_ppv_mm_per_s: Target PPV limit in mm/s
            
        Returns:
            Minimum safe distance in meters
        """
        if charge_weight_kg <= 0 or target_ppv_mm_per_s <= 0:
            return float('inf')
        
        # Rearrange PPV = k * W^a / R^b to solve for R
        # R = (k * W^a / PPV)^(1/b)
        safe_distance = ((self.k * (charge_weight_kg ** self.a)) / target_ppv_mm_per_s) ** (1/self.b)
        
        return safe_distance
    
    def calibrate_constants(self, 
                          measured_data: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Calibrate PPV constants from measured blast data.
        
        Args:
            measured_data: List of dictionaries with keys:
                          'charge_weight_kg', 'distance_m', 'measured_ppv'
            
        Returns:
            Dictionary with calibrated constants and fit statistics
        """
        if len(measured_data) < 3:
            raise ValueError("Need at least 3 data points for calibration")
        
        # Extract data for regression
        charges = np.array([d['charge_weight_kg'] for d in measured_data])
        distances = np.array([d['distance_m'] for d in measured_data])
        ppvs = np.array([d['measured_ppv'] for d in measured_data])
        
        # Log-transform for linear regression
        # log(PPV) = log(k) + a*log(W) - b*log(R)
        log_ppv = np.log(ppvs)
        log_charge = np.log(charges)
        log_distance = np.log(distances)
        
        # Set up design matrix
        X = np.column_stack([np.ones(len(measured_data)), log_charge, log_distance])
        
        # Solve using least squares
        coeffs, residuals, rank, s = np.linalg.lstsq(X, log_ppv, rcond=None)
        
        # Extract calibrated constants
        k_calibrated = math.exp(coeffs[0])
        a_calibrated = coeffs[1]
        b_calibrated = -coeffs[2]  # Negative because distance is in denominator
        
        # Calculate fit statistics
        predicted_log_ppv = X @ coeffs
        predicted_ppv = np.exp(predicted_log_ppv)
        
        # R-squared
        ss_res = np.sum((log_ppv - predicted_log_ppv) ** 2)
        ss_tot = np.sum((log_ppv - np.mean(log_ppv)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Mean absolute percentage error
        mape = np.mean(np.abs((ppvs - predicted_ppv) / ppvs)) * 100
        
        return {
            "k": k_calibrated,
            "a": a_calibrated,
            "b": b_calibrated,
            "r_squared": r_squared,
            "mape": mape,
            "num_points": len(measured_data),
            "residual_std": math.sqrt(ss_res / (len(measured_data) - 3)) if len(measured_data) > 3 else 0
        }
    
    def get_model_info(self) -> Dict[str, Union[float, str]]:
        """
        Get current model parameters and information.
        
        Returns:
            Dictionary with model information
        """
        return {
            "k": self.k,
            "a": self.a,
            "b": self.b,
            "equation": f"PPV = {self.k:.3f} * (W^{self.a:.3f} / R^{self.b:.3f})",
            "units": "PPV in mm/s, W in kg, R in m"
        }