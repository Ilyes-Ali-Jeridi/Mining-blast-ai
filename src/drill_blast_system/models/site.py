"""
Site model for storing site configuration and geometry data.
Implements requirement 1.7: Site data management with geometry and rock properties.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, JSON, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.database import BaseModel


class Site(BaseModel):
    """
    Site configuration and geometry storage.
    
    Stores comprehensive site data including:
    - Bench geometry (elevations, orientations, dimensions)
    - Rock properties (UCS, density, rock types)
    - Equipment specifications (drill rigs, explosives)
    - Operational constraints and safety parameters
    """
    __tablename__ = "sites"
    
    # Basic site information
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)  # Human-readable location
    coordinates = Column(JSON, nullable=True)  # {"latitude": float, "longitude": float}
    
    # Site status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    site_type = Column(String(50), nullable=False, default="open_pit")  # open_pit, underground, quarry
    regulatory_zone = Column(String(100), nullable=True)  # For region-specific safety limits
    
    # Bench geometry data - stored as JSON for flexibility
    bench_geometry = Column(JSON, nullable=False)
    """
    Bench geometry structure:
    {
        "bench_top_elevation": float,      # meters above sea level
        "bench_bottom_elevation": float,   # meters above sea level  
        "bench_height": float,             # calculated or specified
        "bench_width": float,              # meters
        "bench_length": float,             # meters
        "free_face_orientation": float,    # degrees from north
        "bench_angle": float,              # degrees from horizontal
        "topography_mesh": [               # Optional 3D mesh points
            {"x": float, "y": float, "z": float}, ...
        ],
        "exclusion_zones": [               # Areas where drilling is prohibited
            {
                "name": str,
                "polygon": [{"x": float, "y": float}, ...],
                "reason": str
            }, ...
        ]
    }
    """
    
    # Rock properties - can be uniform or block model
    rock_properties = Column(JSON, nullable=False)
    """
    Rock properties structure:
    {
        "is_uniform": bool,                # True for uniform properties, False for block model
        "uniform_properties": {            # Used when is_uniform=True
            "rock_type": str,
            "ucs": float,                  # MPa - Unconfined Compressive Strength
            "density": float,              # kg/m³
            "rock_factor_a": float,        # Kuz-Ram rock factor (default 7.0)
            "grade": float                 # Optional ore grade
        },
        "block_model": [                   # Used when is_uniform=False
            {
                "x": float, "y": float, "z": float,  # Cell center coordinates
                "rock_type": str,
                "ucs": float,
                "density": float, 
                "rock_factor_a": float,
                "grade": float
            }, ...
        ],
        "rock_type_definitions": {         # Definitions for rock type codes
            "rock_type_code": {
                "name": str,
                "description": str,
                "default_ucs": float,
                "default_density": float,
                "default_rock_factor_a": float
            }, ...
        }
    }
    """
    
    # Equipment specifications
    equipment_specs = Column(JSON, nullable=False)
    """
    Equipment specifications structure:
    {
        "drill_rigs": [
            {
                "name": str,
                "max_hole_diameter": float,    # mm
                "max_depth": float,            # meters
                "collar_accuracy": float,      # meters
                "drilling_rate": float,        # m/hr
                "setup_time": float,           # minutes
                "operating_cost": float        # $/hour
            }, ...
        ],
        "explosives_catalog": [
            {
                "name": str,
                "type": str,                   # ANFO, Emulsion, Slurry, etc.
                "density": float,              # kg/m³
                "rws": float,                  # Relative Weight Strength (%)
                "vod": float,                  # Velocity of Detonation (m/s)
                "energy": float,               # MJ/kg
                "cost_per_kg": float,          # $/kg
                "regulatory_limit_per_hole": float,    # kg
                "regulatory_limit_per_delay": float,   # kg
                "is_available": bool
            }, ...
        ]
    }
    """
    
    # Operational constraints
    operational_constraints = Column(JSON, nullable=False)
    """
    Operational constraints structure:
    {
        "drilling_constraints": {
            "min_burden": float,           # meters
            "max_burden": float,           # meters  
            "min_spacing": float,          # meters
            "max_spacing": float,          # meters
            "min_hole_diameter": float,    # mm
            "max_hole_diameter": float,    # mm
            "min_stemming": float,         # meters
            "max_stemming": float          # meters
        },
        "powder_factor_limits": {
            "min_powder_factor": float,    # kg/t
            "max_powder_factor": float,    # kg/t
            "target_powder_factor": float  # kg/t (optional)
        },
        "sensitive_receptors": [
            {
                "name": str,
                "coordinates": {"x": float, "y": float, "z": float},
                "ppv_limit": float,        # mm/s
                "frequency_limit": float,  # Hz (optional)
                "receptor_type": str       # building, equipment, etc.
            }, ...
        ],
        "time_constraints": {
            "blast_windows": [             # Allowed blasting times
                {
                    "day_of_week": str,    # monday, tuesday, etc.
                    "start_time": str,     # HH:MM format
                    "end_time": str        # HH:MM format
                }, ...
            ],
            "weather_constraints": {
                "max_wind_speed": float,   # m/s
                "min_visibility": float,   # meters
                "no_blast_conditions": [str]  # rain, fog, etc.
            }
        }
    }
    """
    
    # Safety configuration specific to this site
    safety_config = Column(JSON, nullable=True)
    """
    Site-specific safety overrides:
    {
        "max_charge_per_hole": float,      # kg (overrides global default)
        "max_charge_per_delay": float,     # kg (overrides global default)
        "ppv_default_limit": float,        # mm/s (overrides global default)
        "safety_factor": float,            # Additional safety margin (default 1.0)
        "requires_engineer_signoff": bool, # Force engineer signoff (default True)
        "custom_safety_rules": [           # Site-specific safety rules
            {
                "rule_name": str,
                "description": str,
                "constraint_type": str,    # charge, ppv, distance, etc.
                "limit_value": float,
                "is_active": bool
            }, ...
        ]
    }
    """
    
    # Relationships
    blast_records = relationship("BlastRecord", back_populates="site", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_sites_name_active', 'name', 'is_active'),
        Index('ix_sites_location', 'location'),
        Index('ix_sites_type_active', 'site_type', 'is_active'),
    )
    
    @hybrid_property
    def bench_height(self) -> Optional[float]:
        """Calculate bench height from geometry data."""
        if self.bench_geometry and 'bench_top_elevation' in self.bench_geometry and 'bench_bottom_elevation' in self.bench_geometry:
            return self.bench_geometry['bench_top_elevation'] - self.bench_geometry['bench_bottom_elevation']
        return None
    
    @hybrid_property
    def bench_area(self) -> Optional[float]:
        """Calculate bench area from geometry data."""
        if self.bench_geometry and 'bench_width' in self.bench_geometry and 'bench_length' in self.bench_geometry:
            return self.bench_geometry['bench_width'] * self.bench_geometry['bench_length']
        return None
    
    @hybrid_property
    def bench_volume(self) -> Optional[float]:
        """Calculate bench volume from geometry data."""
        area = self.bench_area
        height = self.bench_height
        if area and height:
            return area * height
        return None
    
    def get_rock_properties_at_location(self, x: float, y: float, z: float) -> Optional[Dict[str, Any]]:
        """
        Get rock properties at specific coordinates.
        
        Args:
            x, y, z: Coordinates in site coordinate system
            
        Returns:
            Dict with rock properties or None if not found
        """
        if not self.rock_properties:
            return None
            
        # If uniform properties, return them directly
        if self.rock_properties.get('is_uniform', True):
            return self.rock_properties.get('uniform_properties')
        
        # For block model, find nearest cell
        block_model = self.rock_properties.get('block_model', [])
        if not block_model:
            return None
        
        # Simple nearest neighbor search (could be optimized with spatial indexing)
        min_distance = float('inf')
        nearest_cell = None
        
        for cell in block_model:
            distance = ((cell['x'] - x) ** 2 + (cell['y'] - y) ** 2 + (cell['z'] - z) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_cell = cell
        
        return nearest_cell
    
    def get_available_explosives(self) -> List[Dict[str, Any]]:
        """Get list of available explosives for this site."""
        if not self.equipment_specs or 'explosives_catalog' not in self.equipment_specs:
            return []
        
        return [
            explosive for explosive in self.equipment_specs['explosives_catalog']
            if explosive.get('is_available', True)
        ]
    
    def get_sensitive_receptors_within_distance(self, x: float, y: float, max_distance: float) -> List[Dict[str, Any]]:
        """
        Get sensitive receptors within specified distance from coordinates.
        
        Args:
            x, y: Coordinates to search from
            max_distance: Maximum distance in meters
            
        Returns:
            List of receptors within distance
        """
        if not self.operational_constraints or 'sensitive_receptors' not in self.operational_constraints:
            return []
        
        nearby_receptors = []
        for receptor in self.operational_constraints['sensitive_receptors']:
            receptor_coords = receptor.get('coordinates', {})
            if 'x' in receptor_coords and 'y' in receptor_coords:
                distance = ((receptor_coords['x'] - x) ** 2 + (receptor_coords['y'] - y) ** 2) ** 0.5
                if distance <= max_distance:
                    receptor_with_distance = receptor.copy()
                    receptor_with_distance['distance'] = distance
                    nearby_receptors.append(receptor_with_distance)
        
        # Sort by distance
        nearby_receptors.sort(key=lambda r: r['distance'])
        return nearby_receptors
    
    def validate_geometry_data(self) -> List[str]:
        """
        Validate bench geometry data for completeness and consistency.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.bench_geometry:
            errors.append("Bench geometry data is required")
            return errors
        
        required_fields = ['bench_top_elevation', 'bench_bottom_elevation', 'bench_width', 'bench_length']
        for field in required_fields:
            if field not in self.bench_geometry:
                errors.append(f"Missing required geometry field: {field}")
        
        # Validate elevation consistency
        if 'bench_top_elevation' in self.bench_geometry and 'bench_bottom_elevation' in self.bench_geometry:
            if self.bench_geometry['bench_top_elevation'] <= self.bench_geometry['bench_bottom_elevation']:
                errors.append("Bench top elevation must be greater than bottom elevation")
        
        # Validate positive dimensions
        for field in ['bench_width', 'bench_length']:
            if field in self.bench_geometry and self.bench_geometry[field] <= 0:
                errors.append(f"{field} must be positive")
        
        return errors
    
    def validate_rock_properties(self) -> List[str]:
        """
        Validate rock properties data for completeness and consistency.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not self.rock_properties:
            errors.append("Rock properties data is required")
            return errors
        
        is_uniform = self.rock_properties.get('is_uniform', True)
        
        if is_uniform:
            uniform_props = self.rock_properties.get('uniform_properties', {})
            required_fields = ['rock_type', 'ucs', 'density']
            for field in required_fields:
                if field not in uniform_props:
                    errors.append(f"Missing required rock property: {field}")
            
            # Validate ranges
            if 'ucs' in uniform_props and uniform_props['ucs'] <= 0:
                errors.append("UCS must be positive")
            if 'density' in uniform_props and uniform_props['density'] <= 0:
                errors.append("Density must be positive")
        else:
            block_model = self.rock_properties.get('block_model', [])
            if not block_model:
                errors.append("Block model data is required when is_uniform=False")
            else:
                for i, cell in enumerate(block_model):
                    required_fields = ['x', 'y', 'z', 'rock_type', 'ucs', 'density']
                    for field in required_fields:
                        if field not in cell:
                            errors.append(f"Block model cell {i}: missing field {field}")
        
        return errors
    
    def __repr__(self) -> str:
        """String representation of the site."""
        return f"<Site(id={self.id}, name='{self.name}', type='{self.site_type}', active={self.is_active})>"