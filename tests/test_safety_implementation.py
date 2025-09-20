"""
Minimal test for safety implementation without schema dependencies.
Tests the core safety reporting and audit trail functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
import tempfile
from pathlib import Path

# Import safety modules directly
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity
)
from src.drill_blast_system.safety.audit import SafetyAuditTrail, AuditEntry
from src.drill_blast_system.safety.reporting import SafetyReportGenerator
from src.drill_blast_system.safety.status_tracker import SafetyStatusTracker


class TestSafetyImplementation:
    """Test core safety implementation without schema dependencies."""
    
    def test_safety_validation_result_creation(self):
        """Test creating safety validation result."""
        safety_checks = [
            SafetyCheck(
                check_name="Test Check",
                check_type=SafetyCheckType.CHARGE_PER_HOLE,
                status=SafetyStatus.PASS,
                limit_value=50.0,
                actual_value=30.0,
                safety_margin=0.4,
                description="Test check passed",
                units="kg"
            )
        ]
        
        result = SafetyValidationResult(
            validation_timestamp=datetime.utcnow(),
            is_valid=True,
            safety_checks=safety_checks,
            violations=[],
            safety_config_snapshot={'max_charge_per_hole': 50.0}
        )
        
        assert result.is_valid
        assert len(result.safety_checks) == 1
        assert len(result.violations) == 0
        assert result.validation_id is not None
    
    def test_safety_violation_creation(self):
        """Test creating safety violations."""
        violation = SafetyViolation(
            violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
            severity=ViolationSeverity.CRITICAL,
            description="Charge exceeds limit",
            suggested_mitigation="Reduce charge"
        )
        
        assert violation.severity == ViolationSeverity.CRITICAL
        assert "charge" in violation.description.lower()
        
        # Test to_dict conversion
        violation_dict = violation.to_dict()
        assert 'violation_type' in violation_dict
        assert 'severity' in violation_dict
    
    def test_audit_entry_creation_and_integrity(self):
        """Test audit entry creation and integrity verification."""
        entry = AuditEntry(
            entry_id="test_001",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="test_user",
            blast_plan_id="test_plan",
            validation_result={'is_valid': True},
            configuration_snapshot={'version': '1.0.0'},
            metadata={'test': 'data'}
        )
        
        # Should have generated hash
        assert entry.hash_signature is not None
        assert len(entry.hash_signature) == 64  # SHA-256 hex
        
        # Should verify integrity
        assert entry.verify_integrity()
        
        # Tampering should break integrity
        entry.metadata['tampered'] = True
        assert not entry.verify_integrity()
    
    def test_audit_trail_basic_operations(self):
        """Test basic audit trail operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            # Create sample validation result
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={}
            )
            
            # Record validation
            entry_id = audit_trail.record_validation(
                validation_result, "test_plan", "test_user"
            )
            
            assert entry_id is not None
            
            # Retrieve entry
            entry = audit_trail.get_audit_entry(entry_id)
            assert entry is not None
            assert entry.blast_plan_id == "test_plan"
            assert entry.user_id == "test_user"
            
            # Get validation history
            history = audit_trail.get_validation_history("test_plan")
            assert len(history.validations) == 1
    
    def test_safety_report_generation(self):
        """Test safety report generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            report_generator = SafetyReportGenerator(audit_trail=audit_trail)
            
            # Create validation result with violations
            safety_checks = [
                SafetyCheck(
                    check_name="Charge Check",
                    check_type=SafetyCheckType.CHARGE_PER_HOLE,
                    status=SafetyStatus.FAIL,
                    limit_value=50.0,
                    actual_value=75.0,
                    safety_margin=-0.5,
                    description="Charge exceeds limit",
                    units="kg"
                )
            ]
            
            violations = [
                SafetyViolation(
                    violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                    severity=ViolationSeverity.CRITICAL,
                    description="Critical charge violation",
                    suggested_mitigation="Reduce charge immediately",
                    check_details=safety_checks[0]
                )
            ]
            
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=False,
                safety_checks=safety_checks,
                violations=violations,
                safety_config_snapshot={'max_charge_per_hole': 50.0}
            )
            
            # Generate report
            report = report_generator.generate_detailed_safety_report(
                validation_result, "test_plan", include_history=False
            )
            
            assert report is not None
            assert hasattr(report, 'detailed_analysis')
            
            # Check report components
            analysis = report.detailed_analysis
            assert 'status_summary' in analysis
            assert 'violation_reports' in analysis
            assert 'margin_analysis' in analysis
            
            # Status should be invalid
            status_summary = analysis['status_summary']
            assert status_summary.overall_status == "INVALID"
            assert status_summary.critical_violations == 1
    
    def test_status_tracker_basic_functionality(self):
        """Test status tracker basic functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            status_tracker = SafetyStatusTracker(audit_trail=audit_trail)
            
            # Create validation result
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={}
            )
            
            # Track validation
            status_summary = status_tracker.track_validation_status(
                validation_result, "test_plan", "test_user"
            )
            
            assert 'audit_entry_id' in status_summary
            assert status_summary['is_valid'] == True
            assert 'status_score' in status_summary
            assert status_summary['status_score'] > 0
    
    def test_critical_violation_alert_generation(self):
        """Test alert generation for critical violations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            status_tracker = SafetyStatusTracker(audit_trail=audit_trail)
            
            # Create critical violation
            violations = [
                SafetyViolation(
                    violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                    severity=ViolationSeverity.CRITICAL,
                    description="Critical violation",
                    suggested_mitigation="Immediate action required"
                )
            ]
            
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=False,
                safety_checks=[],
                violations=violations,
                safety_config_snapshot={}
            )
            
            # Track validation - should generate alerts
            status_summary = status_tracker.track_validation_status(
                validation_result, "test_plan", "test_user"
            )
            
            # Should have generated alerts
            alerts = status_summary['alerts']
            assert len(alerts) > 0
            
            # Should have critical violation alert
            critical_alerts = [a for a in alerts if a['alert_type'] == 'CRITICAL_VIOLATION']
            assert len(critical_alerts) > 0
            assert critical_alerts[0]['severity'] == 'CRITICAL'
    
    def test_compliance_report_generation(self):
        """Test compliance report generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            # Record validation and sign-off
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={}
            )
            
            validation_entry_id = audit_trail.record_validation(
                validation_result, "test_plan", "test_user"
            )
            
            signoff_entry_id = audit_trail.record_sign_off(
                "test_plan", "John Engineer", "ENG001", 
                validation_entry_id, "Plan certified safe"
            )
            
            # Generate compliance report
            report = audit_trail.generate_compliance_report("test_plan")
            
            assert report['blast_plan_id'] == "test_plan"
            assert report['compliance_status'] == 'COMPLIANT'
            assert report['sign_off_status'] == 'SIGNED'
            assert 'sign_off_details' in report
    
    def test_audit_integrity_verification(self):
        """Test audit trail integrity verification."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            # Record multiple validations
            for i in range(3):
                validation_result = SafetyValidationResult(
                    validation_timestamp=datetime.utcnow(),
                    is_valid=True,
                    safety_checks=[],
                    violations=[],
                    safety_config_snapshot={}
                )
                
                audit_trail.record_validation(
                    validation_result, f"test_plan_{i}", f"user_{i}"
                )
            
            # Verify integrity
            integrity_result = audit_trail.verify_audit_integrity()
            
            assert integrity_result['overall_status'] == 'VALID'
            assert integrity_result['total_entries'] == 3
            assert integrity_result['verified_entries'] == 3
            assert len(integrity_result['failed_entries']) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])