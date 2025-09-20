"""
Tests for safety configuration management system.
Validates requirements 4.8, 9.3, 9.4, 9.7 for safety configuration management.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.drill_blast_system.safety.config import (
    SafetyConfig, SafetyConfigManager, ReceptorConfig, ExplosiveRegulatory
)
from src.drill_blast_system.safety.models import SafetyConfigValidationError


class TestSafetyConfig:
    """Test SafetyConfig class functionality."""
    
    def test_default_config_creation(self):
        """Test creating default safety configuration."""
        config = SafetyConfig()
        
        assert config.max_charge_per_hole == 50.0
        assert config.max_charge_per_delay == 200.0
        assert config.ppv_default_limit == 5.0
        assert config.config_name == "default"
        assert config.config_version == "1.0.0"
        assert config.jurisdiction == "generic"
    
    def test_config_validation_success(self):
        """Test successful configuration validation."""
        config = SafetyConfig(
            max_charge_per_hole=30.0,
            max_charge_per_delay=150.0,
            powder_factor_min=0.1,
            powder_factor_max=1.2,
            ppv_default_limit=4.0
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_failures(self):
        """Test configuration validation with invalid parameters."""
        config = SafetyConfig(
            max_charge_per_hole=-10.0,  # Invalid: negative
            max_charge_per_delay=50.0,  # Invalid: less than per-hole
            powder_factor_min=0.0,      # Invalid: zero
            powder_factor_max=0.05,     # Invalid: less than min
            ppv_default_limit=-1.0      # Invalid: negative
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("positive" in error.lower() for error in errors)
        assert any("greater than minimum" in error for error in errors)
    
    def test_receptor_management(self):
        """Test receptor configuration management."""
        config = SafetyConfig()
        
        # Test getting default limit
        assert config.get_receptor_limit("nonexistent") == config.ppv_default_limit
        
        # Add receptor
        receptor = ReceptorConfig(
            name="test_structure",
            coordinates={"x": 100.0, "y": 200.0, "z": 10.0},
            ppv_limit=2.0,
            description="Test structure"
        )
        config.sensitive_receptors.append(receptor)
        
        # Test getting specific receptor limit
        assert config.get_receptor_limit("test_structure") == 2.0
        
        # Test inactive receptor
        receptor.is_active = False
        assert config.get_receptor_limit("test_structure") == config.ppv_default_limit
    
    def test_explosive_regulations(self):
        """Test explosive regulatory limits."""
        config = SafetyConfig()
        
        explosive = ExplosiveRegulatory(
            explosive_type="ANFO",
            max_charge_per_hole=40.0,
            max_charge_per_delay=180.0,
            storage_limit=1000.0,
            transport_limit=500.0
        )
        config.explosive_regulations.append(explosive)
        
        # Test getting explosive limits
        limits = config.get_explosive_limits("ANFO")
        assert limits is not None
        assert limits.max_charge_per_hole == 40.0
        
        # Test non-existent explosive
        assert config.get_explosive_limits("NonExistent") is None
    
    def test_safety_margin_analysis(self):
        """Test safety margin analysis functionality."""
        config = SafetyConfig(
            max_charge_per_hole=20.0,  # More conservative than reference (25.0)
            max_charge_per_delay=80.0,  # More conservative than reference (100.0)
            ppv_default_limit=1.5,     # More conservative than reference (2.0)
            min_burden=3.5             # More conservative than reference (3.0)
        )
        
        analysis = config.get_safety_margin_analysis()
        
        # Check that more conservative values show positive margins
        assert analysis['max_charge_per_hole']['safety_margin'] > 0
        assert analysis['max_charge_per_delay']['safety_margin'] > 0
        assert analysis['ppv_default_limit']['safety_margin'] > 0
        assert analysis['min_burden']['safety_margin'] > 0
        
        # Check risk levels
        assert analysis['max_charge_per_hole']['risk_level'] == "LOW"
    
    def test_regulatory_compliance_check(self):
        """Test regulatory compliance checking."""
        # Create compliant configuration
        config = SafetyConfig(
            max_charge_per_hole=30.0,
            ppv_structure_limit=1.5,
            noise_limit_day=110.0
        )
        
        compliance = config.check_regulatory_compliance()
        
        assert 'overall_status' in compliance
        assert 'framework_checks' in compliance
        assert 'recommendations' in compliance
        
        # Should have checks for multiple frameworks
        assert len(compliance['framework_checks']) > 0
    
    def test_jurisdiction_validation(self):
        """Test validation against jurisdiction limits."""
        config = SafetyConfig(
            max_charge_per_hole=60.0,  # Exceeds some jurisdiction limits
            ppv_default_limit=8.0      # Exceeds some jurisdiction limits
        )
        
        jurisdiction_limits = {
            'max_charge_per_hole': 50.0,
            'ppv_default_limit': 6.0
        }
        
        errors = config.validate_against_jurisdiction(jurisdiction_limits)
        
        assert len(errors) == 2
        assert any("max_charge_per_hole" in error for error in errors)
        assert any("ppv_default_limit" in error for error in errors)
    
    def test_config_serialization(self):
        """Test configuration serialization and deserialization."""
        original_config = SafetyConfig(
            config_name="test_config",
            max_charge_per_hole=35.0,
            jurisdiction="test_jurisdiction"
        )
        
        # Add receptor
        receptor = ReceptorConfig(
            name="test_receptor",
            coordinates={"x": 0.0, "y": 0.0, "z": 0.0},
            ppv_limit=3.0
        )
        original_config.sensitive_receptors.append(receptor)
        
        # Serialize to dict
        config_dict = original_config.to_dict()
        
        # Deserialize from dict
        restored_config = SafetyConfig.from_dict(config_dict)
        
        assert restored_config.config_name == original_config.config_name
        assert restored_config.max_charge_per_hole == original_config.max_charge_per_hole
        assert restored_config.jurisdiction == original_config.jurisdiction
        assert len(restored_config.sensitive_receptors) == 1
        assert restored_config.sensitive_receptors[0].name == "test_receptor"


class TestSafetyConfigManager:
    """Test SafetyConfigManager functionality."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for configuration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create SafetyConfigManager with temporary directory."""
        return SafetyConfigManager(temp_config_dir)
    
    def test_manager_initialization(self, config_manager, temp_config_dir):
        """Test configuration manager initialization."""
        assert config_manager.config_dir == temp_config_dir
        
        # Check that subdirectories are created
        assert (temp_config_dir / "sites").exists()
        assert (temp_config_dir / "templates").exists()
        assert (temp_config_dir / "backups").exists()
        assert (temp_config_dir / "exports").exists()
    
    def test_create_and_load_default_config(self, config_manager):
        """Test creating and loading default configuration."""
        config = config_manager.create_default_config("test_default")
        
        assert config.config_name == "test_default"
        assert config.config_version == "1.0.0"
        assert len(config.sensitive_receptors) > 0
        assert len(config.explosive_regulations) > 0
        
        # Test loading the created config
        loaded_config = config_manager.load_config("test_default")
        assert loaded_config.config_name == config.config_name
        assert loaded_config.max_charge_per_hole == config.max_charge_per_hole
    
    def test_config_update_and_versioning(self, config_manager):
        """Test configuration updates and version management."""
        # Create initial config
        config_manager.create_default_config("version_test")
        
        # Update configuration
        updates = {
            'max_charge_per_hole': 35.0,
            'ppv_default_limit': 4.0
        }
        updated_config = config_manager.update_config(updates)
        
        assert updated_config.max_charge_per_hole == 35.0
        assert updated_config.ppv_default_limit == 4.0
        assert updated_config.config_version != "1.0.0"  # Version should be incremented
    
    def test_site_specific_configuration(self, config_manager):
        """Test site-specific configuration management."""
        site_id = 123
        
        # Create base config
        config_manager.create_default_config("base_config")
        
        # Create site-specific overrides
        overrides = {
            'max_charge_per_hole': 40.0,
            'ppv_default_limit': 3.0,
            'jurisdiction': 'site_specific'
        }
        
        site_config = config_manager.create_site_override(site_id, overrides, "base_config")
        
        assert site_config.site_id == site_id
        assert site_config.max_charge_per_hole == 40.0
        assert site_config.ppv_default_limit == 3.0
        assert site_config.jurisdiction == 'site_specific'
        
        # Test loading site config
        loaded_site_config = config_manager.load_site_config(site_id, "base_config")
        assert loaded_site_config.site_id == site_id
        assert loaded_site_config.max_charge_per_hole == 40.0
    
    def test_site_overrides_analysis(self, config_manager):
        """Test analysis of site-specific overrides."""
        site_id = 456
        
        # Create base and site configs
        config_manager.create_default_config("base_analysis")
        overrides = {
            'max_charge_per_hole': 45.0,
            'min_burden': 2.5
        }
        config_manager.create_site_override(site_id, overrides, "base_analysis")
        
        # Get override analysis
        override_analysis = config_manager.get_site_overrides(site_id, "base_analysis")
        
        assert 'max_charge_per_hole' in override_analysis
        assert 'min_burden' in override_analysis
        assert override_analysis['max_charge_per_hole']['site_value'] == 45.0
        assert override_analysis['min_burden']['site_value'] == 2.5
    
    def test_receptor_management(self, config_manager):
        """Test receptor addition and removal."""
        config_manager.create_default_config("receptor_test")
        
        # Add receptor
        receptor = ReceptorConfig(
            name="new_receptor",
            coordinates={"x": 150.0, "y": 250.0, "z": 15.0},
            ppv_limit=1.5,
            description="New test receptor"
        )
        
        updated_config = config_manager.add_receptor(receptor)
        
        # Check receptor was added
        receptor_names = [r.name for r in updated_config.sensitive_receptors]
        assert "new_receptor" in receptor_names
        
        # Test duplicate receptor rejection
        with pytest.raises(SafetyConfigValidationError):
            config_manager.add_receptor(receptor)
        
        # Remove receptor
        final_config = config_manager.remove_receptor("new_receptor")
        final_receptor_names = [r.name for r in final_config.sensitive_receptors]
        assert "new_receptor" not in final_receptor_names
    
    def test_config_export_import(self, config_manager, temp_config_dir):
        """Test configuration export and import functionality."""
        # Create and customize config
        config = config_manager.create_default_config("export_test")
        config_manager.update_config({'max_charge_per_hole': 42.0})
        
        # Export config
        export_path = temp_config_dir / "exported_config.json"
        config_manager.export_config("export_test", export_path)
        
        assert export_path.exists()
        
        # Import config with new name
        imported_config = config_manager.import_config(export_path, "imported_test")
        
        assert imported_config.config_name == "imported_test"
        assert imported_config.max_charge_per_hole == 42.0
    
    def test_template_export_import(self, config_manager, temp_config_dir):
        """Test configuration template export and import."""
        # Create config
        config_manager.create_default_config("template_source")
        config_manager.update_config({'max_charge_per_hole': 38.0})
        
        # Export as template
        template_path = temp_config_dir / "config_template.json"
        config_manager.export_config_template("template_source", template_path)
        
        assert template_path.exists()
        
        # Import template
        imported_config = config_manager.import_config_template(
            template_path, "from_template", site_id=789
        )
        
        assert imported_config.config_name == "from_template"
        assert imported_config.site_id == 789
        assert imported_config.max_charge_per_hole == 38.0
    
    def test_config_compatibility_validation(self, config_manager):
        """Test configuration compatibility validation."""
        # Create two configs with different parameters
        config_manager.create_default_config("config_a")
        config_manager.create_default_config("config_b")
        
        # Modify one config to create differences
        config_manager._current_config = None  # Reset current config
        config_manager.load_config("config_b")
        config_manager.update_config({'max_charge_per_hole': 60.0})  # Significant difference
        
        # Check compatibility
        compatibility = config_manager.validate_config_compatibility("config_a", "config_b")
        
        assert 'compatible' in compatibility
        assert 'differences' in compatibility
        assert 'conflicts' in compatibility
        assert 'warnings' in compatibility
        
        # Should detect the significant difference in max_charge_per_hole
        assert 'max_charge_per_hole' in compatibility['differences']
    
    def test_audit_log_functionality(self, config_manager):
        """Test configuration audit logging."""
        config_name = "audit_test"
        
        # Create and modify config multiple times
        config_manager.create_default_config(config_name)
        config_manager.update_config({'max_charge_per_hole': 35.0})
        config_manager.update_config({'ppv_default_limit': 4.0})
        
        # Get audit log
        audit_log = config_manager.get_configuration_audit_log(config_name)
        
        assert len(audit_log) > 0
        
        # Check audit log structure
        for entry in audit_log:
            assert 'timestamp' in entry
            assert 'version' in entry
            assert 'created_by' in entry
            assert 'action' in entry
    
    def test_config_rollback(self, config_manager):
        """Test configuration rollback functionality."""
        config_name = "rollback_test"
        
        # Create initial config
        initial_config = config_manager.create_default_config(config_name)
        initial_version = initial_config.config_version
        
        # Make changes
        config_manager.update_config({'max_charge_per_hole': 35.0})
        config_manager.update_config({'max_charge_per_hole': 40.0})
        
        # Rollback to initial version
        rolled_back_config = config_manager.rollback_config(config_name, initial_version)
        
        assert rolled_back_config.max_charge_per_hole == initial_config.max_charge_per_hole
        assert "rollback" in rolled_back_config.config_version
    
    def test_invalid_config_handling(self, config_manager):
        """Test handling of invalid configurations."""
        # Try to save invalid config
        invalid_config = SafetyConfig(
            config_name="invalid_test",
            max_charge_per_hole=-10.0  # Invalid value
        )
        
        with pytest.raises(SafetyConfigValidationError):
            config_manager.save_config(invalid_config)
    
    def test_list_configs(self, config_manager):
        """Test listing available configurations."""
        # Create multiple configs
        config_manager.create_default_config("config_1")
        config_manager.create_default_config("config_2")
        config_manager.create_default_config("config_3")
        
        # List configs
        config_list = config_manager.list_configs()
        
        assert "config_1" in config_list
        assert "config_2" in config_list
        assert "config_3" in config_list
        assert len(config_list) >= 3


class TestConfigurationIntegration:
    """Integration tests for safety configuration system."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_end_to_end_config_workflow(self, temp_config_dir):
        """Test complete configuration management workflow."""
        manager = SafetyConfigManager(temp_config_dir)
        
        # 1. Create base configuration
        base_config = manager.create_default_config("mining_base")
        assert base_config.config_name == "mining_base"
        
        # 2. Create site-specific configuration
        site_id = 100
        site_overrides = {
            'max_charge_per_hole': 45.0,
            'ppv_default_limit': 3.5,
            'jurisdiction': 'local_authority'
        }
        site_config = manager.create_site_override(site_id, site_overrides, "mining_base")
        
        # 3. Add site-specific receptor
        receptor = ReceptorConfig(
            name="site_office",
            coordinates={"x": 200.0, "y": 300.0, "z": 5.0},
            ppv_limit=1.0,
            description="Site office building"
        )
        manager._current_config = site_config
        updated_site_config = manager.add_receptor(receptor)
        manager.save_site_config(updated_site_config)
        
        # 4. Export configuration as template
        template_path = temp_config_dir / "site_template.json"
        manager.export_config_template(f"site_{site_id}", template_path, include_metadata=False)
        
        # 5. Import template for new site
        new_site_id = 200
        new_site_config = manager.import_config_template(
            template_path, f"site_{new_site_id}", site_id=new_site_id
        )
        
        # 6. Validate configurations
        assert new_site_config.site_id == new_site_id
        assert new_site_config.max_charge_per_hole == 45.0
        assert len(new_site_config.sensitive_receptors) > 1  # Default + added receptor
        
        # 7. Check compatibility between sites
        compatibility = manager.validate_config_compatibility(
            f"site_{site_id}", f"site_{new_site_id}"
        )
        assert compatibility['compatible'] is True
        
        # 8. Verify audit trails exist
        audit_log = manager.get_configuration_audit_log(f"site_{site_id}")
        assert len(audit_log) > 0
    
    def test_regulatory_compliance_workflow(self, temp_config_dir):
        """Test regulatory compliance checking workflow."""
        manager = SafetyConfigManager(temp_config_dir)
        
        # Create configuration with potential compliance issues
        config = manager.create_default_config("compliance_test")
        
        # Update with values that might violate some frameworks
        updates = {
            'max_charge_per_hole': 55.0,  # Might exceed some limits
            'ppv_default_limit': 7.0,     # Might exceed some limits
            'noise_limit_day': 120.0      # Might exceed some limits
        }
        updated_config = manager.update_config(updates)
        
        # Check regulatory compliance
        compliance = updated_config.check_regulatory_compliance()
        
        # Verify compliance structure
        assert 'overall_status' in compliance
        assert 'framework_checks' in compliance
        assert len(compliance['framework_checks']) > 0
        
        # Check safety margin analysis
        margin_analysis = updated_config.get_safety_margin_analysis()
        assert len(margin_analysis) > 0
        
        # Verify each parameter has proper analysis
        for param, analysis in margin_analysis.items():
            assert 'current_value' in analysis
            assert 'conservative_reference' in analysis
            assert 'safety_margin' in analysis
            assert 'risk_level' in analysis
            assert analysis['risk_level'] in ['LOW', 'MEDIUM', 'HIGH']


if __name__ == "__main__":
    pytest.main([__file__])