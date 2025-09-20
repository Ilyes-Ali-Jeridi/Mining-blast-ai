"""
Tests for safety validation system.
Validates requirements 4.1, 4.2, 4.6 for safety constraint validation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import json
from pathlib import Path

from src.drill_blast_system.safety.validator import SafetyValidator
from src.drill_blast_system.safety.config import SafetyConfig, SafetyConfigManager, ReceptorConfig
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity
)
from src.drill_blast_system.schemas.blast_record import (
    BlastPlan, DrillHole, Coordinates, BlastGeometry, ExplosiveSummary
)


@pytest.fixture
def safety_config():
    """Create test safety configuration."""
    config = SafetyConfig(
        max_charge_per_hole=50.0,
        max_charge_per_delay=200.0,
        powder_factor_min=0.1,
        powder_factor_max=1.0,
        ppv_default_limit=5.0,
        min_burden=2.0,
        max_burden=6.0,
        min_spacing=2.0,
        max_spacing=8.0,
        min_stemming_ratio=0.2,
        max_hole_depth=25.0,
        min_delay_interval=8.0
    )
    
    # Add test receptor
    config.sensitive_receptors = [
        ReceptorConfig(
            name="Test Structure",
            coordinates={"x": 100.0, "y": 100.0, "z": 0.0},
            ppv_limit=2.0,
            description="Test structure for validation"
        )
    ]
    
    return config


@pytest.fixture
def config_manager(tmp_path, safety_config):
    """Create test configuration manager."""
    manager = SafetyConfigManager(config_dir=tmp_path / "safety_configs")
    manager._current_config = safety_config
    return manager


@pytest.fixture
def safety_validator(config_manager):
    """Create safety validator with test configuration."""
    return SafetyValidator(config_manager)


@pytest.fixture
def valid_blast_plan():
    """Create valid blast plan for testing."""
    holes = [
        DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=15.0,
            diameter=0.15,
            charge_kg=30.0,
            stemming_m=3.0,
            delay_ms=0,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        ),
        DrillHole(
            hole_id="H002",
            coordinates=Coordinates(x=14.0, y=10.0, z=0.0),
            depth=15.0,
            diameter=0.15,
            charge_kg=25.0,
            stemming_m=3.0,
            delay_ms=25,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        )
    ]
    
    return BlastPlan(
        holes=holes,
        blast_geometry=BlastGeometry(
            bench_height=15.0,
            bench_width=50.0,
            bench_length=100.0,
            rock_tonnage=1000.0,
            free_face_angle=90.0
        ),
        explosive_summary=ExplosiveSummary(
            total_explosive=55.0,
            explosive_types={"ANFO": 55.0},
            total_holes=2,
            average_charge_per_hole=27.5
        )
    )


@pytest.fixture
def invalid_blast_plan():
    """Create invalid blast plan for testing violations."""
    holes = [
        DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=30.0,  # Exceeds max depth
            diameter=0.15,
            charge_kg=60.0,  # Exceeds max charge per hole
            stemming_m=2.0,  # Insufficient stemming
            delay_ms=0,
            explosive_type="ANFO",
            burden=1.5,  # Below minimum burden
            spacing=1.5   # Below minimum spacing
        ),
        DrillHole(
            hole_id="H002",
            coordinates=Coordinates(x=12.0, y=10.0, z=0.0),
            depth=25.0,
            diameter=0.15,
            charge_kg=180.0,  # Large charge
            stemming_m=3.0,
            delay_ms=0,  # Same delay - will exceed per-delay limit
            explosive_type="ANFO",
            burden=2.0,
            spacing=2.0
        )
    ]
    
    return BlastPlan(
        holes=holes,
        blast_geometry=BlastGeometry(
            bench_height=25.0,
            bench_width=50.0,
            bench_length=100.0,
            rock_tonnage=800.0,  # Low tonnage for high explosive = high powder factor
            free_face_angle=90.0
        ),
        explosive_summary=ExplosiveSummary(
            total_explosive=240.0,
            explosive_types={"ANFO": 240.0},
            total_holes=2,
            average_charge_per_hole=120.0
        )
    )


class TestSafetyValidator:
    """Test safety validator functionality."""
    
    def test_valid_blast_plan_validation(self, safety_validator, valid_blast_plan):
        """Test validation of a valid blast plan."""
        result = safety_validator.validate_plan(valid_blast_plan)
        
        assert isinstance(result, SafetyValidationResult)
        assert result.is_valid
        assert len(result.violations) == 0
        assert len(result.safety_checks) > 0
        assert all(check.status in [SafetyStatus.PASS, SafetyStatus.WARNING] 
                  for check in result.safety_checks)
    
    def test_invalid_blast_plan_validation(self, safety_validator, invalid_blast_plan):
        """Test validation of an invalid blast plan."""
        result = safety_validator.validate_plan(invalid_blast_plan)
        
        assert isinstance(result, SafetyValidationResult)
        assert not result.is_valid
        assert len(result.violations) > 0
        assert len(result.failed_checks) > 0
        
        # Check for expected violation types
        violation_types = [v.violation_type for v in result.violations]
        assert SafetyCheckType.CHARGE_PER_HOLE.value in violation_types
        assert SafetyCheckType.CHARGE_PER_DELAY.value in violation_types
    
    def test_charge_per_hole_validation(self, safety_validator, safety_config):
        """Test per-hole charge limit validation."""
        # Create plan with excessive charge
        hole = DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=15.0,
            diameter=0.15,
            charge_kg=safety_config.max_charge_per_hole + 10.0,  # Exceed limit
            stemming_m=3.0,
            delay_ms=0,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        )
        
        blast_plan = BlastPlan(
            holes=[hole],
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=1000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=hole.charge_kg,
                explosive_types={"ANFO": hole.charge_kg},
                total_holes=1,
                average_charge_per_hole=hole.charge_kg
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        assert not result.is_valid
        charge_violations = [v for v in result.violations 
                           if v.violation_type == SafetyCheckType.CHARGE_PER_HOLE.value]
        assert len(charge_violations) > 0
        assert charge_violations[0].severity == ViolationSeverity.CRITICAL
    
    def test_charge_per_delay_validation(self, safety_validator, safety_config):
        """Test per-delay charge limit validation."""
        # Create multiple holes with same delay exceeding limit
        total_charge = safety_config.max_charge_per_delay + 50.0
        charge_per_hole = total_charge / 3
        
        holes = []
        for i in range(3):
            hole = DrillHole(
                hole_id=f"H{i+1:03d}",
                coordinates=Coordinates(x=10.0 + i*4, y=10.0, z=0.0),
                depth=15.0,
                diameter=0.15,
                charge_kg=charge_per_hole,
                stemming_m=3.0,
                delay_ms=0,  # Same delay for all holes
                explosive_type="ANFO",
                burden=4.0,
                spacing=4.0
            )
            holes.append(hole)
        
        blast_plan = BlastPlan(
            holes=holes,
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=2000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=total_charge,
                explosive_types={"ANFO": total_charge},
                total_holes=3,
                average_charge_per_hole=charge_per_hole
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        assert not result.is_valid
        delay_violations = [v for v in result.violations 
                          if v.violation_type == SafetyCheckType.CHARGE_PER_DELAY.value]
        assert len(delay_violations) > 0
    
    def test_ppv_limit_validation(self, safety_validator, safety_config):
        """Test PPV limit validation at receptors."""
        # Create hole close to receptor with high charge
        hole = DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=95.0, y=95.0, z=0.0),  # Close to receptor at (100,100,0)
            depth=15.0,
            diameter=0.15,
            charge_kg=45.0,  # High charge close to receptor
            stemming_m=3.0,
            delay_ms=0,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        )
        
        blast_plan = BlastPlan(
            holes=[hole],
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=1000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=hole.charge_kg,
                explosive_types={"ANFO": hole.charge_kg},
                total_holes=1,
                average_charge_per_hole=hole.charge_kg
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        # Should have PPV violation
        ppv_violations = [v for v in result.violations 
                         if v.violation_type == SafetyCheckType.PPV_LIMIT.value]
        assert len(ppv_violations) > 0
    
    def test_powder_factor_validation(self, safety_validator, safety_config):
        """Test powder factor range validation."""
        # Test high powder factor
        hole = DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=15.0,
            diameter=0.15,
            charge_kg=40.0,
            stemming_m=3.0,
            delay_ms=0,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        )
        
        blast_plan = BlastPlan(
            holes=[hole],
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=30.0,  # Very low tonnage = high powder factor
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=hole.charge_kg,
                explosive_types={"ANFO": hole.charge_kg},
                total_holes=1,
                average_charge_per_hole=hole.charge_kg
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        powder_factor_violations = [v for v in result.violations 
                                  if v.violation_type == SafetyCheckType.POWDER_FACTOR.value]
        assert len(powder_factor_violations) > 0
    
    def test_geometric_constraints_validation(self, safety_validator, safety_config):
        """Test burden and spacing constraint validation."""
        hole = DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=15.0,
            diameter=0.15,
            charge_kg=30.0,
            stemming_m=3.0,
            delay_ms=0,
            explosive_type="ANFO",
            burden=1.0,  # Below minimum burden
            spacing=1.0   # Below minimum spacing
        )
        
        blast_plan = BlastPlan(
            holes=[hole],
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=1000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=hole.charge_kg,
                explosive_types={"ANFO": hole.charge_kg},
                total_holes=1,
                average_charge_per_hole=hole.charge_kg
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        geometric_violations = [v for v in result.violations 
                              if v.violation_type == SafetyCheckType.BURDEN_SPACING.value]
        assert len(geometric_violations) > 0
    
    def test_hole_specifications_validation(self, safety_validator, safety_config):
        """Test hole depth and stemming validation."""
        hole = DrillHole(
            hole_id="H001",
            coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
            depth=safety_config.max_hole_depth + 5.0,  # Exceed max depth
            diameter=0.15,
            charge_kg=30.0,
            stemming_m=1.0,  # Insufficient stemming ratio
            delay_ms=0,
            explosive_type="ANFO",
            burden=4.0,
            spacing=4.0
        )
        
        blast_plan = BlastPlan(
            holes=[hole],
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=1000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=hole.charge_kg,
                explosive_types={"ANFO": hole.charge_kg},
                total_holes=1,
                average_charge_per_hole=hole.charge_kg
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        depth_violations = [v for v in result.violations 
                          if v.violation_type == SafetyCheckType.HOLE_DEPTH.value]
        stemming_violations = [v for v in result.violations 
                             if v.violation_type == SafetyCheckType.STEMMING_LENGTH.value]
        
        assert len(depth_violations) > 0
        assert len(stemming_violations) > 0
    
    def test_delay_interval_validation(self, safety_validator, safety_config):
        """Test minimum delay interval validation."""
        holes = [
            DrillHole(
                hole_id="H001",
                coordinates=Coordinates(x=10.0, y=10.0, z=0.0),
                depth=15.0,
                diameter=0.15,
                charge_kg=30.0,
                stemming_m=3.0,
                delay_ms=0,
                explosive_type="ANFO",
                burden=4.0,
                spacing=4.0
            ),
            DrillHole(
                hole_id="H002",
                coordinates=Coordinates(x=14.0, y=10.0, z=0.0),
                depth=15.0,
                diameter=0.15,
                charge_kg=30.0,
                stemming_m=3.0,
                delay_ms=5,  # Too short interval (< min_delay_interval)
                explosive_type="ANFO",
                burden=4.0,
                spacing=4.0
            )
        ]
        
        blast_plan = BlastPlan(
            holes=holes,
            blast_geometry=BlastGeometry(
                bench_height=15.0,
                bench_width=50.0,
                bench_length=100.0,
                rock_tonnage=1000.0,
                free_face_angle=90.0
            ),
            explosive_summary=ExplosiveSummary(
                total_explosive=60.0,
                explosive_types={"ANFO": 60.0},
                total_holes=2,
                average_charge_per_hole=30.0
            )
        )
        
        result = safety_validator.validate_plan(blast_plan)
        
        regulatory_violations = [v for v in result.violations 
                               if v.violation_type == SafetyCheckType.REGULATORY_COMPLIANCE.value]
        assert len(regulatory_violations) > 0
    
    def test_validation_result_properties(self, safety_validator, invalid_blast_plan):
        """Test validation result properties and methods."""
        result = safety_validator.validate_plan(invalid_blast_plan)
        
        # Test properties
        assert len(result.critical_violations) >= 0
        assert len(result.passed_checks) >= 0
        assert len(result.failed_checks) > 0
        assert len(result.warning_checks) >= 0
        
        # Test has_critical_violations
        critical_count = len(result.critical_violations)
        assert result.has_critical_violations == (critical_count > 0)
        
        # Test to_dict method
        result_dict = result.to_dict()
        assert 'validation_id' in result_dict
        assert 'is_valid' in result_dict
        assert 'safety_checks' in result_dict
        assert 'violations' in result_dict
        assert 'summary' in result_dict
    
    def test_mitigation_suggestions(self, safety_validator, invalid_blast_plan):
        """Test that violations include appropriate mitigation suggestions."""
        result = safety_validator.validate_plan(invalid_blast_plan)
        
        for violation in result.violations:
            assert violation.suggested_mitigation is not None
            assert len(violation.suggested_mitigation) > 0
            
            # Check that mitigation is relevant to violation type
            if violation.violation_type == SafetyCheckType.CHARGE_PER_HOLE.value:
                assert any(keyword in violation.suggested_mitigation.lower() 
                          for keyword in ['reduce', 'charge', 'hole'])
            elif violation.violation_type == SafetyCheckType.PPV_LIMIT.value:
                assert any(keyword in violation.suggested_mitigation.lower() 
                          for keyword in ['reduce', 'distance', 'delay'])
    
    def test_safety_margin_calculations(self, safety_validator, valid_blast_plan):
        """Test safety margin calculations."""
        result = safety_validator.validate_plan(valid_blast_plan)
        
        for check in result.safety_checks:
            # Safety margin should be calculated
            assert hasattr(check, 'safety_margin')
            
            # For passed checks, margin should generally be positive
            if check.status == SafetyStatus.PASS and check.limit_value > 0:
                # Allow some tolerance for rounding
                assert check.safety_margin >= -0.1
    
    def test_configuration_snapshot(self, safety_validator, valid_blast_plan):
        """Test that validation result includes configuration snapshot."""
        result = safety_validator.validate_plan(valid_blast_plan)
        
        assert result.safety_config_snapshot is not None
        assert isinstance(result.safety_config_snapshot, dict)
        
        # Should contain key safety parameters
        expected_keys = [
            'max_charge_per_hole', 'max_charge_per_delay', 
            'ppv_default_limit', 'powder_factor_min', 'powder_factor_max'
        ]
        
        for key in expected_keys:
            assert key in result.safety_config_snapshot
    
    def test_site_specific_configuration(self, safety_validator, valid_blast_plan):
        """Test validation with site-specific configuration."""
        site_id = 123
        
        # This should use site-specific config if available, otherwise default
        result = safety_validator.validate_plan(valid_blast_plan, site_id=site_id)
        
        assert isinstance(result, SafetyValidationResult)
        # Should still validate successfully with default config
        assert result.is_valid
    
    def test_validation_error_handling(self, safety_validator):
        """Test error handling in validation process."""
        # Test with None blast plan
        with pytest.raises(Exception):
            safety_validator.validate_plan(None)
        
        # Test with invalid blast plan structure
        invalid_plan = Mock()
        invalid_plan.holes = None
        
        with pytest.raises(Exception):
            safety_validator.validate_plan(invalid_plan)