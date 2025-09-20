"""
Physics Model Configuration System

Provides configurable parameter management for all physics constants,
parameter validation, default parameter sets, and calibration utilities.
"""

import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from pathlib import Path


class RockType(Enum):
    """Standard rock type classifications"""
    VERY_SOFT = "very_soft"
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"


@dataclass
class KuzRamParameters:
    """Kuz-Ram model parameters"""
    rock_factor_a: float = 7.0
    scaling_factor: float = 0.005
    min_fragment_size_mm: float = 1.0
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        if not 1.0 <= self.rock_factor_a <= 20.0:
            errors.append(f"Rock factor A must be between 1.0 and 20.0, got {self.rock_factor_a}")
        if not 0.001 <= self.scaling_factor <= 0.1:
            errors.append(f"Scaling factor must be between 0.001 and 0.1, got {self.scaling_factor}")
        if self.min_fragment_size_mm <= 0:
            errors.append("Minimum fragment size must be positive")
        return errors


@dataclass
class PPVParameters:
    """PPV model parameters"""
    k: float = 1.4
    a: float = 1/3
    b: float = 1.6
    max_k: float = 5000.0
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        if not 0.1 <= self.k <= self.max_k:
            errors.append(f"Site constant k must be between 0.1 and {self.max_k}, got {self.k}")
        if not 0.1 <= self.a <= 1.0:
            errors.append(f"Charge exponent a must be between 0.1 and 1.0, got {self.a}")
        if not 0.5 <= self.b <= 3.0:
            errors.append(f"Distance exponent b must be between 0.5 and 3.0, got {self.b}")
        return errors


@dataclass
class FragmentationParameters:
    """Fragmentation curve parameters"""
    default_uniformity_index: float = 1.25
    min_uniformity_index: float = 0.5
    max_uniformity_index: float = 3.0
    default_distribution_type: str = "rosin_rammler"
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        if not self.min_uniformity_index <= self.default_uniformity_index <= self.max_uniformity_index:
            errors.append("Default uniformity index must be within min/max range")
        if self.default_distribution_type not in ["rosin_rammler", "swebrec", "kco"]:
            errors.append(f"Invalid distribution type: {self.default_distribution_type}")
        return errors


@dataclass
class SafetyParameters:
    """Safety constraint parameters"""
    max_charge_per_hole_kg: float = 50.0
    max_charge_per_delay_kg: float = 200.0
    powder_factor_min_kg_per_t: float = 0.05
    powder_factor_max_kg_per_t: float = 1.5
    ppv_default_limit_mm_per_s: float = 5.0
    
    def validate(self) -> List[str]:
        """Validate parameters and return list of errors"""
        errors = []
        if self.max_charge_per_hole_kg <= 0:
            errors.append("Max charge per hole must be positive")
        if self.max_charge_per_delay_kg <= 0:
            errors.append("Max charge per delay must be positive")
        if not 0.01 <= self.powder_factor_min_kg_per_t <= self.powder_factor_max_kg_per_t:
            errors.append("Invalid powder factor range")
        if self.ppv_default_limit_mm_per_s <= 0:
            errors.append("PPV limit must be positive")
        return errors


@dataclass
class PhysicsConfig:
    """Complete physics model configuration"""
    kuz_ram: KuzRamParameters = field(default_factory=KuzRamParameters)
    ppv: PPVParameters = field(default_factory=PPVParameters)
    fragmentation: FragmentationParameters = field(default_factory=FragmentationParameters)
    safety: SafetyParameters = field(default_factory=SafetyParameters)
    rock_type: RockType = RockType.MEDIUM
    site_name: str = "Default Site"
    description: str = "Default physics configuration"
    version: str = "1.0"
    
    def validate(self) -> Dict[str, List[str]]:
        """Validate all parameters and return categorized errors"""
        validation_results = {
            "kuz_ram": self.kuz_ram.validate(),
            "ppv": self.ppv.validate(),
            "fragmentation": self.fragmentation.validate(),
            "safety": self.safety.validate()
        }
        return validation_results
    
    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        validation_results = self.validate()
        return all(len(errors) == 0 for errors in validation_results.values())
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary with error counts"""
        validation_results = self.validate()
        total_errors = sum(len(errors) for errors in validation_results.values())
        
        return {
            "is_valid": total_errors == 0,
            "total_errors": total_errors,
            "errors_by_category": validation_results,
            "error_count_by_category": {
                category: len(errors) for category, errors in validation_results.items()
            }
        }


class PhysicsConfigManager:
    """Manager for physics model configurations"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configuration files
        """
        self.config_dir = config_dir or Path("configs/physics")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load default configurations
        self._default_configs = self._create_default_configs()
    
    def _create_default_configs(self) -> Dict[RockType, PhysicsConfig]:
        """Create default configurations for different rock types"""
        configs = {}
        
        # Very Soft Rock (e.g., clay, soft shale)
        configs[RockType.VERY_SOFT] = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=3.0, scaling_factor=0.008),
            ppv=PPVParameters(k=800, a=0.35, b=1.4),
            rock_type=RockType.VERY_SOFT,
            site_name="Very Soft Rock Default",
            description="Configuration for very soft rocks like clay and soft shale"
        )
        
        # Soft Rock (e.g., sandstone, limestone)
        configs[RockType.SOFT] = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=5.0, scaling_factor=0.006),
            ppv=PPVParameters(k=1000, a=0.33, b=1.5),
            rock_type=RockType.SOFT,
            site_name="Soft Rock Default",
            description="Configuration for soft rocks like sandstone and limestone"
        )
        
        # Medium Rock (e.g., granite, basalt)
        configs[RockType.MEDIUM] = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=7.0, scaling_factor=0.005),
            ppv=PPVParameters(k=1300, a=0.33, b=1.6),
            rock_type=RockType.MEDIUM,
            site_name="Medium Rock Default",
            description="Configuration for medium rocks like granite and basalt"
        )
        
        # Hard Rock (e.g., quartzite, hard granite)
        configs[RockType.HARD] = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=10.0, scaling_factor=0.004),
            ppv=PPVParameters(k=1600, a=0.30, b=1.7),
            rock_type=RockType.HARD,
            site_name="Hard Rock Default",
            description="Configuration for hard rocks like quartzite and hard granite"
        )
        
        # Very Hard Rock (e.g., taconite, very hard quartzite)
        configs[RockType.VERY_HARD] = PhysicsConfig(
            kuz_ram=KuzRamParameters(rock_factor_a=15.0, scaling_factor=0.003),
            ppv=PPVParameters(k=2000, a=0.28, b=1.8),
            rock_type=RockType.VERY_HARD,
            site_name="Very Hard Rock Default",
            description="Configuration for very hard rocks like taconite"
        )
        
        return configs
    
    def get_default_config(self, rock_type: RockType) -> PhysicsConfig:
        """Get default configuration for rock type"""
        return self._default_configs[rock_type]
    
    def save_config(self, config: PhysicsConfig, filename: str) -> Path:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            filename: Name of file (without extension)
            
        Returns:
            Path to saved file
        """
        if not config.is_valid():
            raise ValueError("Cannot save invalid configuration")
        
        filepath = self.config_dir / f"{filename}.json"
        
        # Convert to dictionary and save
        config_dict = asdict(config)
        # Convert enum to string
        config_dict["rock_type"] = config.rock_type.value
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return filepath
    
    def load_config(self, filename: str) -> PhysicsConfig:
        """
        Load configuration from file.
        
        Args:
            filename: Name of file (with or without extension)
            
        Returns:
            Loaded configuration
        """
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        # Convert rock_type string back to enum
        if "rock_type" in config_dict:
            config_dict["rock_type"] = RockType(config_dict["rock_type"])
        
        # Reconstruct nested dataclasses
        if "kuz_ram" in config_dict:
            config_dict["kuz_ram"] = KuzRamParameters(**config_dict["kuz_ram"])
        if "ppv" in config_dict:
            config_dict["ppv"] = PPVParameters(**config_dict["ppv"])
        if "fragmentation" in config_dict:
            config_dict["fragmentation"] = FragmentationParameters(**config_dict["fragmentation"])
        if "safety" in config_dict:
            config_dict["safety"] = SafetyParameters(**config_dict["safety"])
        
        return PhysicsConfig(**config_dict)
    
    def list_configs(self) -> List[str]:
        """List available configuration files"""
        return [f.stem for f in self.config_dir.glob("*.json")]
    
    def delete_config(self, filename: str) -> bool:
        """
        Delete configuration file.
        
        Args:
            filename: Name of file to delete
            
        Returns:
            True if deleted, False if not found
        """
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.config_dir / filename
        
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    
    def calibrate_kuz_ram(self, 
                         measured_data: List[Dict[str, float]], 
                         base_config: Optional[PhysicsConfig] = None) -> PhysicsConfig:
        """
        Calibrate Kuz-Ram parameters from measured fragmentation data.
        
        Args:
            measured_data: List of dicts with 'predicted_p80', 'measured_p80', 'blast_params'
            base_config: Base configuration to modify (uses medium rock default if None)
            
        Returns:
            Calibrated configuration
        """
        if len(measured_data) < 3:
            raise ValueError("Need at least 3 data points for calibration")
        
        if base_config is None:
            base_config = self.get_default_config(RockType.MEDIUM)
        
        # Extract data for calibration
        predicted_p80 = np.array([d['predicted_p80'] for d in measured_data])
        measured_p80 = np.array([d['measured_p80'] for d in measured_data])
        
        # Calculate correction factor
        correction_factors = measured_p80 / predicted_p80
        mean_correction = np.mean(correction_factors)
        
        # Adjust rock factor A based on correction
        new_rock_factor = base_config.kuz_ram.rock_factor_a * mean_correction
        
        # Clamp to valid range
        new_rock_factor = max(1.0, min(20.0, new_rock_factor))
        
        # Create calibrated configuration
        calibrated_config = PhysicsConfig(
            kuz_ram=KuzRamParameters(
                rock_factor_a=new_rock_factor,
                scaling_factor=base_config.kuz_ram.scaling_factor,
                min_fragment_size_mm=base_config.kuz_ram.min_fragment_size_mm
            ),
            ppv=base_config.ppv,
            fragmentation=base_config.fragmentation,
            safety=base_config.safety,
            rock_type=base_config.rock_type,
            site_name=f"{base_config.site_name} (Calibrated)",
            description=f"Calibrated from {len(measured_data)} measurements",
            version=f"{base_config.version}-cal"
        )
        
        return calibrated_config
    
    def calibrate_ppv(self, 
                     measured_data: List[Dict[str, float]], 
                     base_config: Optional[PhysicsConfig] = None) -> PhysicsConfig:
        """
        Calibrate PPV parameters from measured blast data.
        
        Args:
            measured_data: List of dicts with 'charge_weight_kg', 'distance_m', 'measured_ppv'
            base_config: Base configuration to modify
            
        Returns:
            Calibrated configuration
        """
        if len(measured_data) < 3:
            raise ValueError("Need at least 3 data points for calibration")
        
        if base_config is None:
            base_config = self.get_default_config(RockType.MEDIUM)
        
        # Use the PPV model's calibration method
        from .ppv import PPVModel
        
        temp_model = PPVModel(
            k=base_config.ppv.k,
            a=base_config.ppv.a,
            b=base_config.ppv.b
        )
        
        calibration_result = temp_model.calibrate_constants(measured_data)
        
        # Validate calibrated parameters and clamp to safe ranges if needed
        k_cal = max(0.1, min(base_config.ppv.max_k, calibration_result["k"]))
        a_cal = max(0.1, min(1.0, calibration_result["a"]))
        b_cal = max(0.5, min(3.0, calibration_result["b"]))
        
        # Create calibrated configuration
        calibrated_config = PhysicsConfig(
            kuz_ram=base_config.kuz_ram,
            ppv=PPVParameters(
                k=k_cal,
                a=a_cal,
                b=b_cal,
                max_k=base_config.ppv.max_k
            ),
            fragmentation=base_config.fragmentation,
            safety=base_config.safety,
            rock_type=base_config.rock_type,
            site_name=f"{base_config.site_name} (PPV Calibrated)",
            description=f"PPV calibrated from {len(measured_data)} measurements (R²={calibration_result['r_squared']:.3f})",
            version=f"{base_config.version}-ppv-cal"
        )
        
        return calibrated_config
    
    def compare_configs(self, config1: PhysicsConfig, config2: PhysicsConfig) -> Dict[str, Any]:
        """
        Compare two configurations and highlight differences.
        
        Args:
            config1: First configuration
            config2: Second configuration
            
        Returns:
            Dictionary with comparison results
        """
        differences = {}
        
        # Compare Kuz-Ram parameters
        kuz_ram_diff = {}
        if config1.kuz_ram.rock_factor_a != config2.kuz_ram.rock_factor_a:
            kuz_ram_diff["rock_factor_a"] = {
                "config1": config1.kuz_ram.rock_factor_a,
                "config2": config2.kuz_ram.rock_factor_a,
                "difference": config2.kuz_ram.rock_factor_a - config1.kuz_ram.rock_factor_a
            }
        
        if kuz_ram_diff:
            differences["kuz_ram"] = kuz_ram_diff
        
        # Compare PPV parameters
        ppv_diff = {}
        for param in ["k", "a", "b"]:
            val1 = getattr(config1.ppv, param)
            val2 = getattr(config2.ppv, param)
            if val1 != val2:
                ppv_diff[param] = {
                    "config1": val1,
                    "config2": val2,
                    "difference": val2 - val1,
                    "percent_change": ((val2 - val1) / val1) * 100 if val1 != 0 else float('inf')
                }
        
        if ppv_diff:
            differences["ppv"] = ppv_diff
        
        # Compare other parameters
        if config1.rock_type != config2.rock_type:
            differences["rock_type"] = {
                "config1": config1.rock_type.value,
                "config2": config2.rock_type.value
            }
        
        return {
            "has_differences": len(differences) > 0,
            "differences": differences,
            "config1_name": config1.site_name,
            "config2_name": config2.site_name
        }
    
    def export_config_summary(self, config: PhysicsConfig) -> Dict[str, Any]:
        """
        Export configuration summary for reporting.
        
        Args:
            config: Configuration to summarize
            
        Returns:
            Dictionary with configuration summary
        """
        validation = config.get_validation_summary()
        
        return {
            "site_name": config.site_name,
            "description": config.description,
            "rock_type": config.rock_type.value,
            "version": config.version,
            "validation": validation,
            "parameters": {
                "kuz_ram": {
                    "rock_factor_a": config.kuz_ram.rock_factor_a,
                    "scaling_factor": config.kuz_ram.scaling_factor
                },
                "ppv": {
                    "k": config.ppv.k,
                    "a": config.ppv.a,
                    "b": config.ppv.b,
                    "equation": f"PPV = {config.ppv.k:.1f} * (W^{config.ppv.a:.3f} / R^{config.ppv.b:.3f})"
                },
                "safety": {
                    "max_charge_per_hole_kg": config.safety.max_charge_per_hole_kg,
                    "max_charge_per_delay_kg": config.safety.max_charge_per_delay_kg,
                    "powder_factor_range": f"{config.safety.powder_factor_min_kg_per_t}-{config.safety.powder_factor_max_kg_per_t} kg/t",
                    "ppv_default_limit": f"{config.safety.ppv_default_limit_mm_per_s} mm/s"
                }
            }
        }