"""
Safety configuration management system.
Implements requirements 4.8, 9.3, 9.4, 9.7 for safety parameter configuration.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import logging
from copy import deepcopy

from .models import SafetyConfigValidationError

logger = logging.getLogger(__name__)


@dataclass
class ReceptorConfig:
    """Configuration for a sensitive receptor."""
    name: str
    coordinates: Dict[str, float]  # x, y, z
    ppv_limit: float  # mm/s
    frequency_limit: Optional[float] = None  # Hz
    description: str = ""
    is_active: bool = True


@dataclass
class ExplosiveRegulatory:
    """Regulatory limits for explosive types."""
    explosive_type: str
    max_charge_per_hole: float  # kg
    max_charge_per_delay: float  # kg
    storage_limit: float  # kg
    transport_limit: float  # kg
    requires_permit: bool = True
    permit_conditions: List[str] = field(default_factory=list)


@dataclass
class SafetyConfig:
    """Complete safety configuration with all regulatory parameters."""
    
    # Charge limits
    max_charge_per_hole: float = 50.0  # kg
    max_charge_per_delay: float = 200.0  # kg
    max_total_explosive: float = 5000.0  # kg
    
    # Powder factor limits
    powder_factor_min: float = 0.05  # kg/t
    powder_factor_max: float = 1.5   # kg/t
    
    # PPV limits
    ppv_default_limit: float = 5.0  # mm/s
    ppv_structure_limit: float = 2.0  # mm/s for structures
    ppv_residential_limit: float = 1.0  # mm/s for residential
    
    # Geometric constraints
    min_burden: float = 2.0  # m
    max_burden: float = 8.0  # m
    min_spacing: float = 2.0  # m
    max_spacing: float = 10.0  # m
    min_stemming_ratio: float = 0.2  # stemming/depth ratio
    max_hole_depth: float = 30.0  # m
    
    # Safety distances
    min_distance_to_structures: float = 100.0  # m
    min_distance_to_roads: float = 50.0  # m
    exclusion_zone_radius: float = 300.0  # m
    
    # Timing constraints
    max_delay_time: float = 10000.0  # ms
    min_delay_interval: float = 8.0  # ms between delays
    
    # Environmental limits
    noise_limit_day: float = 115.0  # dB(A)
    noise_limit_night: float = 105.0  # dB(A)
    dust_limit: float = 50.0  # μg/m³
    
    # Receptors and regulatory
    sensitive_receptors: List[ReceptorConfig] = field(default_factory=list)
    explosive_regulations: List[ExplosiveRegulatory] = field(default_factory=list)
    
    # Configuration metadata
    config_name: str = "default"
    config_version: str = "1.0.0"
    site_id: Optional[int] = None
    jurisdiction: str = "generic"
    regulatory_authority: str = ""
    effective_date: datetime = field(default_factory=datetime.utcnow)
    expiry_date: Optional[datetime] = None
    created_by: str = "system"
    
    # Validation settings
    enforce_critical_only: bool = False  # If True, only enforce critical violations
    allow_engineering_override: bool = False  # Allow engineer override of warnings
    require_dual_signoff: bool = False  # Require two engineer signatures
    
    def validate(self) -> List[str]:
        """Validate configuration parameters and return any errors."""
        errors = []
        
        # Validate charge limits
        if self.max_charge_per_hole <= 0:
            errors.append("Maximum charge per hole must be positive")
        if self.max_charge_per_delay <= 0:
            errors.append("Maximum charge per delay must be positive")
        if self.max_charge_per_delay < self.max_charge_per_hole:
            errors.append("Maximum charge per delay must be >= maximum charge per hole")
        
        # Validate powder factor limits
        if self.powder_factor_min <= 0:
            errors.append("Minimum powder factor must be positive")
        if self.powder_factor_max <= self.powder_factor_min:
            errors.append("Maximum powder factor must be greater than minimum")
        
        # Validate PPV limits
        if self.ppv_default_limit <= 0:
            errors.append("Default PPV limit must be positive")
        
        # Validate geometric constraints
        if self.min_burden <= 0 or self.max_burden <= self.min_burden:
            errors.append("Invalid burden constraints")
        if self.min_spacing <= 0 or self.max_spacing <= self.min_spacing:
            errors.append("Invalid spacing constraints")
        if not (0 < self.min_stemming_ratio < 1):
            errors.append("Stemming ratio must be between 0 and 1")
        
        # Validate receptors
        for i, receptor in enumerate(self.sensitive_receptors):
            if receptor.ppv_limit <= 0:
                errors.append(f"Receptor {receptor.name} has invalid PPV limit")
            if not all(key in receptor.coordinates for key in ['x', 'y', 'z']):
                errors.append(f"Receptor {receptor.name} missing coordinates")
        
        # Validate explosive regulations
        for explosive in self.explosive_regulations:
            if explosive.max_charge_per_hole <= 0:
                errors.append(f"Explosive {explosive.explosive_type} has invalid per-hole limit")
            if explosive.max_charge_per_delay <= 0:
                errors.append(f"Explosive {explosive.explosive_type} has invalid per-delay limit")
        
        return errors
    
    def get_receptor_limit(self, receptor_name: str) -> float:
        """Get PPV limit for a specific receptor."""
        for receptor in self.sensitive_receptors:
            if receptor.name == receptor_name and receptor.is_active:
                return receptor.ppv_limit
        return self.ppv_default_limit
    
    def get_explosive_limits(self, explosive_type: str) -> Optional[ExplosiveRegulatory]:
        """Get regulatory limits for specific explosive type."""
        for explosive in self.explosive_regulations:
            if explosive.explosive_type == explosive_type:
                return explosive
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def validate_against_jurisdiction(self, jurisdiction_limits: Dict[str, Any]) -> List[str]:
        """Validate configuration against jurisdiction-specific limits."""
        errors = []
        
        # Check if current limits exceed jurisdiction maximums
        jurisdiction_checks = {
            'max_charge_per_hole': self.max_charge_per_hole,
            'max_charge_per_delay': self.max_charge_per_delay,
            'ppv_default_limit': self.ppv_default_limit,
            'powder_factor_max': self.powder_factor_max,
            'noise_limit_day': self.noise_limit_day,
            'noise_limit_night': self.noise_limit_night
        }
        
        for param, current_value in jurisdiction_checks.items():
            if param in jurisdiction_limits:
                max_allowed = jurisdiction_limits[param]
                if current_value > max_allowed:
                    errors.append(
                        f"{param} ({current_value}) exceeds jurisdiction limit ({max_allowed})"
                    )
        
        return errors
    
    def get_safety_margin_analysis(self) -> Dict[str, Dict[str, float]]:
        """Analyze safety margins for all critical parameters."""
        # Industry standard conservative limits for comparison
        conservative_limits = {
            'max_charge_per_hole': 25.0,  # kg
            'max_charge_per_delay': 100.0,  # kg
            'ppv_default_limit': 2.0,  # mm/s
            'powder_factor_max': 1.0,  # kg/t
            'min_burden': 3.0,  # m
            'min_spacing': 3.0,  # m
        }
        
        analysis = {}
        
        for param, conservative_value in conservative_limits.items():
            current_value = getattr(self, param)
            
            if param.startswith('min_'):
                # For minimum values, higher is more conservative
                margin = (current_value - conservative_value) / conservative_value
                risk_level = "LOW" if margin >= 0 else "HIGH" if margin < -0.2 else "MEDIUM"
            else:
                # For maximum values, lower is more conservative
                margin = (conservative_value - current_value) / conservative_value
                risk_level = "LOW" if margin >= 0 else "HIGH" if margin < -0.5 else "MEDIUM"
            
            analysis[param] = {
                'current_value': current_value,
                'conservative_reference': conservative_value,
                'safety_margin': margin,
                'risk_level': risk_level
            }
        
        return analysis
    
    def check_regulatory_compliance(self) -> Dict[str, Any]:
        """Check compliance with common regulatory frameworks."""
        compliance = {
            'overall_status': 'COMPLIANT',
            'framework_checks': {},
            'recommendations': []
        }
        
        # Generic mining safety framework checks
        frameworks = {
            'MSHA_US': {
                'max_charge_per_hole': 50.0,
                'ppv_structure_limit': 2.0,
                'noise_limit_day': 115.0
            },
            'DMIRS_AU': {
                'max_charge_per_hole': 45.0,
                'ppv_residential_limit': 1.0,
                'exclusion_zone_radius': 500.0
            },
            'HSE_UK': {
                'ppv_default_limit': 6.0,
                'noise_limit_day': 110.0,
                'min_distance_to_structures': 150.0
            }
        }
        
        for framework, limits in frameworks.items():
            framework_status = 'COMPLIANT'
            violations = []
            
            for param, limit in limits.items():
                if hasattr(self, param):
                    current_value = getattr(self, param)
                    
                    # Check if current value violates framework limit
                    if param.startswith('max_') or param.endswith('_limit'):
                        if current_value > limit:
                            violations.append(f"{param}: {current_value} > {limit}")
                            framework_status = 'NON_COMPLIANT'
                    elif param.startswith('min_'):
                        if current_value < limit:
                            violations.append(f"{param}: {current_value} < {limit}")
                            framework_status = 'NON_COMPLIANT'
            
            compliance['framework_checks'][framework] = {
                'status': framework_status,
                'violations': violations
            }
            
            if framework_status == 'NON_COMPLIANT':
                compliance['overall_status'] = 'NON_COMPLIANT'
        
        # Generate recommendations
        if compliance['overall_status'] == 'NON_COMPLIANT':
            compliance['recommendations'].append(
                "Review configuration against applicable regulatory frameworks"
            )
            compliance['recommendations'].append(
                "Consider using more conservative safety limits"
            )
            compliance['recommendations'].append(
                "Consult with local regulatory authority for specific requirements"
            )
        
        return compliance
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SafetyConfig':
        """Create SafetyConfig from dictionary."""
        # Handle datetime fields
        if 'effective_date' in data and isinstance(data['effective_date'], str):
            data['effective_date'] = datetime.fromisoformat(data['effective_date'])
        if 'expiry_date' in data and isinstance(data['expiry_date'], str):
            data['expiry_date'] = datetime.fromisoformat(data['expiry_date'])
        
        # Handle nested objects
        if 'sensitive_receptors' in data:
            data['sensitive_receptors'] = [
                ReceptorConfig(**receptor) if isinstance(receptor, dict) else receptor
                for receptor in data['sensitive_receptors']
            ]
        
        if 'explosive_regulations' in data:
            data['explosive_regulations'] = [
                ExplosiveRegulatory(**explosive) if isinstance(explosive, dict) else explosive
                for explosive in data['explosive_regulations']
            ]
        
        return cls(**data)


class SafetyConfigManager:
    """Manages safety configuration with versioning and audit trails."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager."""
        self.config_dir = config_dir or Path("configs/safety")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.config_dir / "sites").mkdir(exist_ok=True)
        (self.config_dir / "templates").mkdir(exist_ok=True)
        (self.config_dir / "backups").mkdir(exist_ok=True)
        (self.config_dir / "exports").mkdir(exist_ok=True)
        
        self._current_config: Optional[SafetyConfig] = None
        self._config_history: List[SafetyConfig] = []
        self._site_configs: Dict[int, SafetyConfig] = {}  # site_id -> config
        
    def load_config(self, config_name: str = "default") -> SafetyConfig:
        """Load safety configuration from file."""
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            logger.warning(f"Config file {config_file} not found, creating default")
            return self.create_default_config(config_name)
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            config = SafetyConfig.from_dict(data)
            
            # Validate configuration
            errors = config.validate()
            if errors:
                raise SafetyConfigValidationError(f"Invalid configuration: {'; '.join(errors)}")
            
            self._current_config = config
            logger.info(f"Loaded safety config: {config_name} v{config.config_version}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config {config_name}: {e}")
            raise SafetyConfigValidationError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: SafetyConfig, backup_current: bool = True) -> None:
        """Save safety configuration to file with versioning."""
        # Validate before saving
        errors = config.validate()
        if errors:
            raise SafetyConfigValidationError(f"Cannot save invalid configuration: {'; '.join(errors)}")
        
        # Backup current config if requested
        if backup_current and self._current_config:
            self._backup_config(self._current_config)
        
        # Save new config
        config_file = self.config_dir / f"{config.config_name}.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2, default=str)
            
            self._current_config = config
            logger.info(f"Saved safety config: {config.config_name} v{config.config_version}")
            
        except Exception as e:
            logger.error(f"Failed to save config {config.config_name}: {e}")
            raise SafetyConfigValidationError(f"Failed to save configuration: {e}")
    
    def create_default_config(self, config_name: str = "default") -> SafetyConfig:
        """Create and save default safety configuration."""
        config = SafetyConfig(
            config_name=config_name,
            config_version="1.0.0",
            jurisdiction="generic",
            regulatory_authority="Generic Mining Authority",
            created_by="system"
        )
        
        # Add default receptors
        config.sensitive_receptors = [
            ReceptorConfig(
                name="Default Structure",
                coordinates={"x": 0.0, "y": 0.0, "z": 0.0},
                ppv_limit=2.0,
                description="Default structure receptor"
            )
        ]
        
        # Add default explosive regulations
        config.explosive_regulations = [
            ExplosiveRegulatory(
                explosive_type="ANFO",
                max_charge_per_hole=50.0,
                max_charge_per_delay=200.0,
                storage_limit=1000.0,
                transport_limit=500.0,
                requires_permit=True,
                permit_conditions=["Licensed operator required", "Weather restrictions apply"]
            )
        ]
        
        self.save_config(config, backup_current=False)
        return config
    
    def get_current_config(self) -> SafetyConfig:
        """Get current safety configuration."""
        if self._current_config is None:
            return self.load_config()
        return self._current_config
    
    def update_config(self, updates: Dict[str, Any]) -> SafetyConfig:
        """Update current configuration with new values."""
        current = self.get_current_config()
        
        # Create new config with updates
        config_dict = current.to_dict()
        config_dict.update(updates)
        
        # Increment version
        version_parts = current.config_version.split('.')
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        config_dict['config_version'] = '.'.join(version_parts)
        config_dict['effective_date'] = datetime.utcnow()
        
        new_config = SafetyConfig.from_dict(config_dict)
        self.save_config(new_config)
        
        return new_config
    
    def add_receptor(self, receptor: ReceptorConfig) -> SafetyConfig:
        """Add new sensitive receptor to configuration."""
        current = self.get_current_config()
        
        # Check for duplicate names
        existing_names = [r.name for r in current.sensitive_receptors]
        if receptor.name in existing_names:
            raise SafetyConfigValidationError(f"Receptor {receptor.name} already exists")
        
        new_receptors = current.sensitive_receptors + [receptor]
        return self.update_config({'sensitive_receptors': [asdict(r) for r in new_receptors]})
    
    def remove_receptor(self, receptor_name: str) -> SafetyConfig:
        """Remove sensitive receptor from configuration."""
        current = self.get_current_config()
        
        new_receptors = [r for r in current.sensitive_receptors if r.name != receptor_name]
        if len(new_receptors) == len(current.sensitive_receptors):
            raise SafetyConfigValidationError(f"Receptor {receptor_name} not found")
        
        return self.update_config({'sensitive_receptors': [asdict(r) for r in new_receptors]})
    
    def export_config(self, config_name: str, export_path: Path) -> None:
        """Export configuration to external file."""
        config = self.load_config(config_name)
        
        with open(export_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2, default=str)
        
        logger.info(f"Exported config {config_name} to {export_path}")
    
    def import_config(self, import_path: Path, config_name: str) -> SafetyConfig:
        """Import configuration from external file."""
        with open(import_path, 'r') as f:
            data = json.load(f)
        
        # Override config name
        data['config_name'] = config_name
        data['config_version'] = "1.0.0"
        data['effective_date'] = datetime.utcnow()
        data['created_by'] = "imported"
        
        config = SafetyConfig.from_dict(data)
        self.save_config(config)
        
        logger.info(f"Imported config from {import_path} as {config_name}")
        return config
    
    def list_configs(self) -> List[str]:
        """List available configuration files."""
        config_files = list(self.config_dir.glob("*.json"))
        return [f.stem for f in config_files]
    
    def get_config_history(self, config_name: str) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        backup_dir = self.config_dir / "backups" / config_name
        if not backup_dir.exists():
            return []
        
        history = []
        for backup_file in sorted(backup_dir.glob("*.json")):
            try:
                with open(backup_file, 'r') as f:
                    data = json.load(f)
                history.append({
                    'version': data.get('config_version', 'unknown'),
                    'effective_date': data.get('effective_date', 'unknown'),
                    'created_by': data.get('created_by', 'unknown'),
                    'backup_file': str(backup_file)
                })
            except Exception as e:
                logger.warning(f"Failed to read backup {backup_file}: {e}")
        
        return history
    
    def load_site_config(self, site_id: int, base_config: str = "default") -> SafetyConfig:
        """Load site-specific safety configuration with base template."""
        site_config_file = self.config_dir / "sites" / f"site_{site_id}.json"
        
        # Load base configuration
        base = self.load_config(base_config)
        
        if not site_config_file.exists():
            logger.info(f"No site-specific config for site {site_id}, using base config")
            # Create site-specific config from base
            site_config = deepcopy(base)
            site_config.site_id = site_id
            site_config.config_name = f"site_{site_id}"
            site_config.config_version = "1.0.0"
            site_config.created_by = "auto_generated"
            
            self.save_site_config(site_config)
            return site_config
        
        try:
            with open(site_config_file, 'r') as f:
                site_data = json.load(f)
            
            # Merge site overrides with base config
            base_dict = base.to_dict()
            base_dict.update(site_data)
            base_dict['site_id'] = site_id
            
            site_config = SafetyConfig.from_dict(base_dict)
            
            # Validate merged configuration
            errors = site_config.validate()
            if errors:
                raise SafetyConfigValidationError(f"Invalid site config: {'; '.join(errors)}")
            
            self._site_configs[site_id] = site_config
            logger.info(f"Loaded site config for site {site_id} v{site_config.config_version}")
            return site_config
            
        except Exception as e:
            logger.error(f"Failed to load site config for site {site_id}: {e}")
            raise SafetyConfigValidationError(f"Failed to load site configuration: {e}")
    
    def save_site_config(self, config: SafetyConfig) -> None:
        """Save site-specific safety configuration."""
        if config.site_id is None:
            raise SafetyConfigValidationError("Site ID is required for site-specific configuration")
        
        # Validate before saving
        errors = config.validate()
        if errors:
            raise SafetyConfigValidationError(f"Cannot save invalid site configuration: {'; '.join(errors)}")
        
        # Backup existing site config if it exists
        site_config_file = self.config_dir / "sites" / f"site_{config.site_id}.json"
        if site_config_file.exists():
            self._backup_site_config(config.site_id)
        
        try:
            with open(site_config_file, 'w') as f:
                json.dump(config.to_dict(), f, indent=2, default=str)
            
            self._site_configs[config.site_id] = config
            logger.info(f"Saved site config for site {config.site_id} v{config.config_version}")
            
        except Exception as e:
            logger.error(f"Failed to save site config for site {config.site_id}: {e}")
            raise SafetyConfigValidationError(f"Failed to save site configuration: {e}")
    
    def create_site_override(self, site_id: int, overrides: Dict[str, Any], 
                           base_config: str = "default") -> SafetyConfig:
        """Create site-specific configuration with selective overrides."""
        base = self.load_config(base_config)
        
        # Create site config with overrides
        site_dict = base.to_dict()
        site_dict.update(overrides)
        site_dict['site_id'] = site_id
        site_dict['config_name'] = f"site_{site_id}"
        site_dict['config_version'] = "1.0.0"
        site_dict['effective_date'] = datetime.utcnow()
        site_dict['created_by'] = overrides.get('created_by', 'system')
        
        site_config = SafetyConfig.from_dict(site_dict)
        self.save_site_config(site_config)
        
        logger.info(f"Created site override config for site {site_id}")
        return site_config
    
    def get_site_overrides(self, site_id: int, base_config: str = "default") -> Dict[str, Any]:
        """Get only the overridden parameters for a site."""
        base = self.load_config(base_config)
        site = self.load_site_config(site_id, base_config)
        
        base_dict = base.to_dict()
        site_dict = site.to_dict()
        
        overrides = {}
        for key, site_value in site_dict.items():
            if key in ['site_id', 'config_name', 'config_version', 'effective_date', 'created_by']:
                continue  # Skip metadata fields
            
            base_value = base_dict.get(key)
            if base_value != site_value:
                overrides[key] = {
                    'base_value': base_value,
                    'site_value': site_value,
                    'override_type': type(site_value).__name__
                }
        
        return overrides
    
    def export_config_template(self, config_name: str, export_path: Path, 
                             include_metadata: bool = False) -> None:
        """Export configuration as template for reuse."""
        config = self.load_config(config_name)
        
        export_data = config.to_dict()
        
        if not include_metadata:
            # Remove instance-specific metadata for template use
            metadata_fields = ['site_id', 'effective_date', 'created_by', 'config_version']
            for field in metadata_fields:
                export_data.pop(field, None)
            
            # Add template metadata
            export_data['template_name'] = config_name
            export_data['template_version'] = "1.0.0"
            export_data['exported_at'] = datetime.utcnow().isoformat()
            export_data['description'] = f"Safety configuration template based on {config_name}"
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported config template {config_name} to {export_path}")
    
    def import_config_template(self, import_path: Path, config_name: str, 
                             site_id: Optional[int] = None) -> SafetyConfig:
        """Import configuration from template file."""
        with open(import_path, 'r') as f:
            template_data = json.load(f)
        
        # Clean up template metadata and set new config metadata
        template_data.pop('template_name', None)
        template_data.pop('template_version', None)
        template_data.pop('exported_at', None)
        
        template_data['config_name'] = config_name
        template_data['config_version'] = "1.0.0"
        template_data['effective_date'] = datetime.utcnow()
        template_data['created_by'] = "imported_template"
        template_data['site_id'] = site_id
        
        config = SafetyConfig.from_dict(template_data)
        
        if site_id is not None:
            self.save_site_config(config)
        else:
            self.save_config(config)
        
        logger.info(f"Imported config template from {import_path} as {config_name}")
        return config
    
    def validate_config_compatibility(self, config1_name: str, config2_name: str) -> Dict[str, Any]:
        """Validate compatibility between two configurations."""
        config1 = self.load_config(config1_name)
        config2 = self.load_config(config2_name)
        
        compatibility = {
            'compatible': True,
            'warnings': [],
            'conflicts': [],
            'differences': {}
        }
        
        # Check critical safety parameters
        critical_params = [
            'max_charge_per_hole', 'max_charge_per_delay', 'ppv_default_limit',
            'powder_factor_max', 'min_burden', 'max_burden'
        ]
        
        for param in critical_params:
            val1 = getattr(config1, param)
            val2 = getattr(config2, param)
            
            if val1 != val2:
                compatibility['differences'][param] = {'config1': val1, 'config2': val2}
                
                # Check for potential safety conflicts
                if param in ['max_charge_per_hole', 'max_charge_per_delay', 'ppv_default_limit']:
                    if abs(val1 - val2) / max(val1, val2) > 0.2:  # >20% difference
                        compatibility['conflicts'].append(
                            f"{param}: significant difference ({val1} vs {val2})"
                        )
                        compatibility['compatible'] = False
        
        # Check receptor compatibility
        receptors1 = {r.name: r.ppv_limit for r in config1.sensitive_receptors}
        receptors2 = {r.name: r.ppv_limit for r in config2.sensitive_receptors}
        
        for name, limit1 in receptors1.items():
            if name in receptors2:
                limit2 = receptors2[name]
                if limit1 != limit2:
                    compatibility['warnings'].append(
                        f"Receptor {name} has different PPV limits: {limit1} vs {limit2}"
                    )
        
        return compatibility
    
    def get_configuration_audit_log(self, config_name: str) -> List[Dict[str, Any]]:
        """Get audit log for configuration changes."""
        audit_log = []
        
        # Get backup history
        backup_dir = self.config_dir / "backups" / config_name
        if backup_dir.exists():
            for backup_file in sorted(backup_dir.glob("*.json")):
                try:
                    with open(backup_file, 'r') as f:
                        backup_data = json.load(f)
                    
                    audit_log.append({
                        'timestamp': backup_data.get('effective_date', 'unknown'),
                        'version': backup_data.get('config_version', 'unknown'),
                        'created_by': backup_data.get('created_by', 'unknown'),
                        'action': 'backup_created',
                        'backup_file': str(backup_file)
                    })
                except Exception as e:
                    logger.warning(f"Failed to read backup {backup_file}: {e}")
        
        # Add current config info
        try:
            current = self.load_config(config_name)
            audit_log.append({
                'timestamp': current.effective_date.isoformat(),
                'version': current.config_version,
                'created_by': current.created_by,
                'action': 'current_active',
                'backup_file': None
            })
        except Exception as e:
            logger.warning(f"Failed to load current config {config_name}: {e}")
        
        return sorted(audit_log, key=lambda x: x['timestamp'])
    
    def rollback_config(self, config_name: str, target_version: str) -> SafetyConfig:
        """Rollback configuration to a previous version."""
        backup_dir = self.config_dir / "backups" / config_name
        
        # Find backup with target version
        target_backup = None
        for backup_file in backup_dir.glob("*.json"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = json.load(f)
                
                if backup_data.get('config_version') == target_version:
                    target_backup = backup_file
                    break
            except Exception as e:
                logger.warning(f"Failed to read backup {backup_file}: {e}")
        
        if not target_backup:
            raise SafetyConfigValidationError(f"No backup found for version {target_version}")
        
        # Load and restore backup
        with open(target_backup, 'r') as f:
            backup_data = json.load(f)
        
        # Update metadata for rollback
        backup_data['config_version'] = f"{target_version}_rollback"
        backup_data['effective_date'] = datetime.utcnow()
        backup_data['created_by'] = f"rollback_from_{target_version}"
        
        restored_config = SafetyConfig.from_dict(backup_data)
        self.save_config(restored_config)
        
        logger.info(f"Rolled back config {config_name} to version {target_version}")
        return restored_config
    
    def _backup_config(self, config: SafetyConfig) -> None:
        """Create backup of configuration."""
        backup_dir = self.config_dir / "backups" / config.config_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{config.config_version}_{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2, default=str)
        
        logger.debug(f"Backed up config to {backup_file}")
    
    def _backup_site_config(self, site_id: int) -> None:
        """Create backup of site-specific configuration."""
        site_config_file = self.config_dir / "sites" / f"site_{site_id}.json"
        
        if not site_config_file.exists():
            return
        
        backup_dir = self.config_dir / "backups" / f"site_{site_id}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        with open(site_config_file, 'r') as f:
            site_data = json.load(f)
        
        version = site_data.get('config_version', 'unknown')
        backup_file = backup_dir / f"{version}_{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(site_data, f, indent=2, default=str)
        
        logger.debug(f"Backed up site config to {backup_file}")