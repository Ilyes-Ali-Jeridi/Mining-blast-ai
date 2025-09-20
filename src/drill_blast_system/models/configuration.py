"""
Configuration model for system settings and parameters.
Implements requirement 9.4, 9.5: Configuration management with versioning and validation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, JSON, Text, Boolean, DateTime, Enum as SQLEnum, Index
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.database import BaseModel


class ConfigurationType(str, Enum):
    """Configuration type enumeration."""
    PHYSICS = "physics"                    # Physics model parameters
    SAFETY = "safety"                     # Safety limits and constraints
    OPTIMIZATION = "optimization"          # Optimization algorithm settings
    EXPLOSIVES = "explosives"             # Explosives database
    EQUIPMENT = "equipment"               # Equipment specifications
    SYSTEM = "system"                     # System-wide settings
    USER = "user"                         # User preferences
    SITE_SPECIFIC = "site_specific"       # Site-specific overrides


class ConfigurationScope(str, Enum):
    """Configuration scope enumeration."""
    GLOBAL = "global"                     # System-wide default
    SITE = "site"                        # Site-specific override
    USER = "user"                        # User-specific setting
    SESSION = "session"                   # Session-specific temporary


class Configuration(BaseModel):
    """
    System configuration storage with versioning and validation.
    
    Stores all configurable parameters including:
    - Physics model constants and calibration parameters
    - Safety limits and regulatory constraints
    - Optimization algorithm settings and preferences
    - Explosives database and equipment specifications
    - User preferences and site-specific overrides
    """
    __tablename__ = "configurations"
    
    # Configuration identification
    config_key = Column(String(200), nullable=False, index=True)
    config_name = Column(String(200), nullable=False)
    config_description = Column(Text, nullable=True)
    
    # Configuration categorization
    config_type = Column(SQLEnum(ConfigurationType), nullable=False, index=True)
    config_scope = Column(SQLEnum(ConfigurationScope), default=ConfigurationScope.GLOBAL, nullable=False, index=True)
    
    # Scope-specific identifiers
    site_id = Column(Integer, nullable=True, index=True)  # For site-specific configs
    user_id = Column(String(100), nullable=True, index=True)  # For user-specific configs
    
    # Configuration data
    config_value = Column(JSON, nullable=False)
    """
    Configuration value structure (varies by config_type):
    
    For PHYSICS:
    {
        "kuz_ram": {
            "rock_factor_a": float,            # Default 7.0
            "uniformity_index": float,         # Default 1.25
            "calibration_data": [              # Optional calibration points
                {
                    "site_name": str,
                    "rock_type": str,
                    "calibrated_a": float,
                    "validation_r2": float
                }, ...
            ]
        },
        "ppv": {
            "k": float,                        # Default 1.4
            "a": float,                        # Default 0.333
            "b": float,                        # Default 1.6
            "site_specific_constants": {       # Site-specific overrides
                "site_id": {
                    "k": float, "a": float, "b": float
                }, ...
            }
        },
        "fragmentation_curves": {
            "default_distribution": str,       # rosin_rammler, swebrec
            "rosin_rammler": {
                "default_n": float             # Uniformity index
            },
            "swebrec": {
                "default_b": float,            # Swebrec b parameter
                "default_x0": float            # Swebrec x0 parameter
            }
        }
    }
    
    For SAFETY:
    {
        "charge_limits": {
            "max_charge_per_hole": float,      # kg
            "max_charge_per_delay": float,     # kg
            "safety_factor": float             # Additional margin (default 1.0)
        },
        "powder_factor_limits": {
            "min_powder_factor": float,        # kg/t
            "max_powder_factor": float,        # kg/t
            "recommended_range": [float, float] # [min, max] recommended
        },
        "ppv_limits": {
            "default_limit": float,            # mm/s
            "structure_limits": {              # Structure-specific limits
                "residential": float,          # mm/s
                "commercial": float,           # mm/s
                "industrial": float,           # mm/s
                "sensitive": float             # mm/s
            }
        },
        "distance_limits": {
            "min_distance_to_structures": float, # meters
            "min_distance_to_roads": float,      # meters
            "exclusion_zone_buffer": float       # meters
        },
        "regulatory_compliance": {
            "jurisdiction": str,               # Country/state/province
            "regulation_reference": str,       # Legal reference
            "last_updated": str,               # ISO date
            "compliance_notes": str
        }
    }
    
    For OPTIMIZATION:
    {
        "algorithms": {
            "default_algorithm": str,          # cp_sat, scipy, genetic
            "algorithm_preferences": {
                "cp_sat": {
                    "max_time_seconds": int,
                    "num_search_workers": int,
                    "log_search_progress": bool
                },
                "scipy": {
                    "method": str,             # differential_evolution, SLSQP
                    "max_iterations": int,
                    "tolerance": float,
                    "polish": bool
                },
                "genetic": {
                    "population_size": int,
                    "num_generations": int,
                    "mutation_rate": float,
                    "crossover_rate": float
                }
            }
        },
        "objectives": {
            "default_weights": {
                "fragmentation": float,        # Weight for P80 objective
                "cost": float,                 # Weight for cost minimization
                "ppv": float,                  # Weight for PPV minimization
                "uniformity": float            # Weight for pattern uniformity
            },
            "convergence_criteria": {
                "max_runtime_seconds": int,
                "objective_tolerance": float,
                "stagnation_generations": int
            }
        },
        "constraints": {
            "default_bounds": {
                "burden_range": [float, float],    # [min, max] meters
                "spacing_range": [float, float],   # [min, max] meters
                "charge_range": [float, float],    # [min, max] kg
                "delay_range": [int, int]          # [min, max] milliseconds
            }
        }
    }
    
    For EXPLOSIVES:
    {
        "catalog": [
            {
                "id": str,
                "name": str,
                "manufacturer": str,
                "type": str,                   # ANFO, Emulsion, etc.
                "density": float,              # kg/m³
                "rws": float,                  # Relative Weight Strength (%)
                "vod": float,                  # Velocity of Detonation (m/s)
                "energy": float,               # MJ/kg
                "cost_per_kg": float,          # $/kg
                "availability": {
                    "regions": [str],          # Available regions
                    "lead_time_days": int,
                    "minimum_order": float     # kg
                },
                "regulatory": {
                    "max_per_hole": float,     # kg
                    "max_per_delay": float,    # kg
                    "storage_class": str,
                    "transport_class": str
                },
                "performance": {
                    "temperature_range": [float, float], # °C
                    "water_resistance": str,   # excellent, good, fair, poor
                    "fume_class": int,         # 1-3
                    "sensitivity": str         # high, medium, low
                },
                "is_active": bool
            }, ...
        ],
        "default_selections": {
            "primary_explosive": str,          # Default explosive ID
            "secondary_explosive": str,        # Alternative explosive ID
            "stemming_material": str
        }
    }
    """
    
    # Version control
    version = Column(Integer, default=1, nullable=False)
    parent_config_id = Column(Integer, nullable=True)  # For configuration history
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Validation and approval
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_by = Column(String(100), nullable=True)
    validation_date = Column(DateTime, nullable=True)
    validation_notes = Column(Text, nullable=True)
    
    # Change tracking
    created_by = Column(String(100), nullable=True)
    modified_by = Column(String(100), nullable=True)
    change_reason = Column(Text, nullable=True)
    
    # Metadata
    tags = Column(JSON, nullable=True)  # List of tags for categorization
    dependencies = Column(JSON, nullable=True)  # List of dependent configuration keys
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_config_key_scope', 'config_key', 'config_scope'),
        Index('ix_config_type_active', 'config_type', 'is_active'),
        Index('ix_config_site_user', 'site_id', 'user_id'),
    )
    
    @hybrid_property
    def full_key(self) -> str:
        """Generate full configuration key including scope."""
        if self.config_scope == ConfigurationScope.SITE and self.site_id:
            return f"site_{self.site_id}.{self.config_key}"
        elif self.config_scope == ConfigurationScope.USER and self.user_id:
            return f"user_{self.user_id}.{self.config_key}"
        else:
            return self.config_key
    
    @hybrid_property
    def is_site_specific(self) -> bool:
        """Check if configuration is site-specific."""
        return self.config_scope == ConfigurationScope.SITE and self.site_id is not None
    
    @hybrid_property
    def is_user_specific(self) -> bool:
        """Check if configuration is user-specific."""
        return self.config_scope == ConfigurationScope.USER and self.user_id is not None
    
    def get_physics_parameter(self, parameter_path: str) -> Optional[Any]:
        """
        Get physics parameter by dot-notation path.
        
        Args:
            parameter_path: Dot-separated path like "kuz_ram.rock_factor_a"
            
        Returns:
            Parameter value or None if not found
        """
        if self.config_type != ConfigurationType.PHYSICS:
            return None
        
        value = self.config_value
        for key in parameter_path.split('.'):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def get_safety_limit(self, limit_name: str) -> Optional[float]:
        """
        Get safety limit value.
        
        Args:
            limit_name: Name of the safety limit
            
        Returns:
            Limit value or None if not found
        """
        if self.config_type != ConfigurationType.SAFETY:
            return None
        
        # Check various sections for the limit
        sections = ['charge_limits', 'powder_factor_limits', 'ppv_limits', 'distance_limits']
        for section in sections:
            if section in self.config_value and limit_name in self.config_value[section]:
                return self.config_value[section][limit_name]
        
        return None
    
    def get_explosive_by_name(self, explosive_name: str) -> Optional[Dict[str, Any]]:
        """
        Get explosive specification by name.
        
        Args:
            explosive_name: Name of the explosive
            
        Returns:
            Explosive specification dict or None if not found
        """
        if self.config_type != ConfigurationType.EXPLOSIVES:
            return None
        
        catalog = self.config_value.get('catalog', [])
        for explosive in catalog:
            if explosive.get('name') == explosive_name and explosive.get('is_active', True):
                return explosive
        
        return None
    
    def get_available_explosives(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available explosives, optionally filtered by region.
        
        Args:
            region: Optional region filter
            
        Returns:
            List of explosive specifications
        """
        if self.config_type != ConfigurationType.EXPLOSIVES:
            return []
        
        catalog = self.config_value.get('catalog', [])
        available = [exp for exp in catalog if exp.get('is_active', True)]
        
        if region:
            available = [
                exp for exp in available
                if region in exp.get('availability', {}).get('regions', [])
            ]
        
        return available
    
    def validate_configuration_data(self) -> List[str]:
        """
        Validate configuration data for completeness and consistency.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.config_value:
            errors.append("Configuration value is required")
            return errors
        
        # Type-specific validation
        if self.config_type == ConfigurationType.PHYSICS:
            errors.extend(self._validate_physics_config())
        elif self.config_type == ConfigurationType.SAFETY:
            errors.extend(self._validate_safety_config())
        elif self.config_type == ConfigurationType.EXPLOSIVES:
            errors.extend(self._validate_explosives_config())
        elif self.config_type == ConfigurationType.OPTIMIZATION:
            errors.extend(self._validate_optimization_config())
        
        return errors
    
    def _validate_physics_config(self) -> List[str]:
        """Validate physics configuration parameters."""
        errors = []
        
        # Validate Kuz-Ram parameters
        if 'kuz_ram' in self.config_value:
            kuz_ram = self.config_value['kuz_ram']
            if 'rock_factor_a' in kuz_ram:
                if not isinstance(kuz_ram['rock_factor_a'], (int, float)) or kuz_ram['rock_factor_a'] <= 0:
                    errors.append("Kuz-Ram rock_factor_a must be positive number")
        
        # Validate PPV parameters
        if 'ppv' in self.config_value:
            ppv = self.config_value['ppv']
            for param in ['k', 'a', 'b']:
                if param in ppv:
                    if not isinstance(ppv[param], (int, float)) or ppv[param] <= 0:
                        errors.append(f"PPV parameter {param} must be positive number")
        
        return errors
    
    def _validate_safety_config(self) -> List[str]:
        """Validate safety configuration parameters."""
        errors = []
        
        # Validate charge limits
        if 'charge_limits' in self.config_value:
            limits = self.config_value['charge_limits']
            for limit_name in ['max_charge_per_hole', 'max_charge_per_delay']:
                if limit_name in limits:
                    if not isinstance(limits[limit_name], (int, float)) or limits[limit_name] <= 0:
                        errors.append(f"{limit_name} must be positive number")
        
        # Validate PPV limits
        if 'ppv_limits' in self.config_value:
            ppv_limits = self.config_value['ppv_limits']
            if 'default_limit' in ppv_limits:
                if not isinstance(ppv_limits['default_limit'], (int, float)) or ppv_limits['default_limit'] <= 0:
                    errors.append("Default PPV limit must be positive number")
        
        return errors
    
    def _validate_explosives_config(self) -> List[str]:
        """Validate explosives configuration parameters."""
        errors = []
        
        if 'catalog' not in self.config_value:
            errors.append("Explosives catalog is required")
            return errors
        
        catalog = self.config_value['catalog']
        if not isinstance(catalog, list):
            errors.append("Explosives catalog must be a list")
            return errors
        
        for i, explosive in enumerate(catalog):
            required_fields = ['name', 'type', 'density', 'rws', 'vod']
            for field in required_fields:
                if field not in explosive:
                    errors.append(f"Explosive {i}: missing required field {field}")
            
            # Validate numeric fields
            numeric_fields = ['density', 'rws', 'vod', 'energy', 'cost_per_kg']
            for field in numeric_fields:
                if field in explosive:
                    if not isinstance(explosive[field], (int, float)) or explosive[field] < 0:
                        errors.append(f"Explosive {i}: {field} must be non-negative number")
        
        return errors
    
    def _validate_optimization_config(self) -> List[str]:
        """Validate optimization configuration parameters."""
        errors = []
        
        # Validate algorithm settings
        if 'algorithms' in self.config_value:
            algorithms = self.config_value['algorithms']
            if 'default_algorithm' in algorithms:
                valid_algorithms = ['cp_sat', 'scipy', 'genetic']
                if algorithms['default_algorithm'] not in valid_algorithms:
                    errors.append(f"Default algorithm must be one of: {valid_algorithms}")
        
        # Validate objective weights
        if 'objectives' in self.config_value and 'default_weights' in self.config_value['objectives']:
            weights = self.config_value['objectives']['default_weights']
            for weight_name, weight_value in weights.items():
                if not isinstance(weight_value, (int, float)) or weight_value < 0:
                    errors.append(f"Objective weight {weight_name} must be non-negative number")
        
        return errors
    
    def create_revision(self, new_config_value: Dict[str, Any], modified_by: str, change_reason: str = "") -> 'Configuration':
        """
        Create a new revision of this configuration.
        
        Args:
            new_config_value: Updated configuration value
            modified_by: User creating the revision
            change_reason: Reason for the change
            
        Returns:
            New Configuration instance (not yet saved to database)
        """
        revision = Configuration(
            config_key=self.config_key,
            config_name=self.config_name,
            config_description=self.config_description,
            config_type=self.config_type,
            config_scope=self.config_scope,
            site_id=self.site_id,
            user_id=self.user_id,
            config_value=new_config_value,
            version=self.version + 1,
            parent_config_id=self.id,
            is_active=True,
            is_default=self.is_default,
            is_validated=False,  # Requires new validation
            created_by=modified_by,
            modified_by=modified_by,
            change_reason=change_reason,
            tags=self.tags,
            dependencies=self.dependencies
        )
        
        return revision
    
    def __repr__(self) -> str:
        """String representation of the configuration."""
        return f"<Configuration(id={self.id}, key='{self.config_key}', type='{self.config_type}', scope='{self.config_scope}', v{self.version})>"