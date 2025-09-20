"""
Core safety system tests without schema dependencies.
Tests the safety reporting and audit trail functionality directly.
"""

import pytest
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import json

# Import only the core safety modules without validator
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity, SafetyReport
)
from src.drill_blast_system.safety.audit import SafetyAuditTrail, AuditEntry, ValidationHistory
from src.drill_blast_system.safety.reporting import SafetyReportGenerator, ReportFormat
from src.drill_blast_system.safety.status_tracker import SafetyStatusTracker


class TestSafetyCore:
    """Test core safety functionality without schema dependencies."""
    
    def test_safety_check_creation(self):
        """Test creating safety checks."""
        check = SafetyCheck(
            check_name="Test Charge Check",
            check_type=SafetyCheckType.CHARGE_PER_HOLE,
            status=SafetyStatus.PASS,
            limit_value=50.0,
            actual_value=30.0,
            safety_margin=0.4,
            description="Charge within limits",
            units="kg"
        )
        
        assert check.check_name == "Test Charge Check"
        assert check.check_type == SafetyCheckType.CHARGE_PER_HOLE
        assert check.status == SafetyStatus.PASS
        assert check.safety_margin == 0.4
    
    def test_safety_violation_creation(self):
        """Test creating safety violations."""
        violation = SafetyViolation(
            violation_type=SafetyCheckType.PPV_LIMIT.value,
            severity=ViolationSeverity.CRITICAL,
            description="PPV exceeds limit",
            suggested_mitigation="Reduce charges or increase distance"
        )
        
        assert violation.violation_type == SafetyCheckType.PPV_LIMIT.value
        assert violation.severity == ViolationSeverity.CRITICAL
        assert "PPV" in violation.description
        
        # Test serialization
        violation_dict = violation.to_dict()
        assert violation_dict['severity'] == 'CRITICAL'
        assert violation_dict['violation_type'] == SafetyCheckType.PPV_LIMIT.value
    
    def test_safety_validation_result(self):
        """Test safety validation result creation and properties."""
        # Create some checks
        checks = [
            SafetyCheck(
                check_name="Charge Check 1",
                check_type=SafetyCheckType.CHARGE_PER_HOLE,
                status=SafetyStatus.PASS,
                limit_value=50.0,
                actual_value=30.0,
                safety_margin=0.4,
                description="Pass",
                units="kg"
            ),
            SafetyCheck(
                check_name="PPV Check 1",
                check_type=SafetyCheckType.PPV_LIMIT,
                status=SafetyStatus.FAIL,
                limit_value=5.0,
                actual_value=7.0,
                safety_margin=-0.4,
                description="Fail",
                units="mm/s"
            ),
            SafetyCheck(
                check_name="Warning Check",
                check_type=SafetyCheckType.POWDER_FACTOR,
                status=SafetyStatus.WARNING,
                limit_value=1.0,
                actual_value=0.95,
                safety_margin=0.05,
                description="Warning",
                units="kg/t"
            )
        ]
        
        # Create violations
        violations = [
            SafetyViolation(
                violation_type=SafetyCheckType.PPV_LIMIT.value,
                severity=ViolationSeverity.CRITICAL,
                description="PPV violation",
                suggested_mitigation="Reduce charges",
                check_details=checks[1]
            )
        ]
        
        # Create validation result
        result = SafetyValidationResult(
            validation_timestamp=datetime.utcnow(),
            is_valid=False,
            safety_checks=checks,
            violations=violations,
            safety_config_snapshot={'test': 'config'}
        )
        
        # Test properties
        assert not result.is_valid
        assert len(result.safety_checks) == 3
        assert len(result.violations) == 1
        assert len(result.passed_checks) == 1
        assert len(result.failed_checks) == 1
        assert len(result.warning_checks) == 1
        assert len(result.critical_violations) == 1
        assert result.has_critical_violations
        
        # Test serialization
        result_dict = result.to_dict()
        assert 'validation_id' in result_dict
        assert 'is_valid' in result_dict
        assert 'summary' in result_dict
        assert result_dict['summary']['total_checks'] == 3
    
    def test_audit_entry_integrity(self):
        """Test audit entry creation and integrity verification."""
        entry = AuditEntry(
            entry_id="test_001",
            timestamp=datetime.utcnow(),
            operation_type="safety_validation",
            user_id="test_user",
            blast_plan_id="test_plan",
            validation_result={'is_valid': True, 'checks': []},
            configuration_snapshot={'version': '1.0.0'},
            metadata={'source': 'test'}
        )
        
        # Should have hash
        assert entry.hash_signature is not None
        assert len(entry.hash_signature) == 64  # SHA-256
        
        # Should verify integrity
        assert entry.verify_integrity()
        
        # Tampering should break integrity
        original_hash = entry.hash_signature
        entry.metadata['tampered'] = True
        assert not entry.verify_integrity()
        
        # Hash should be different after tampering
        new_hash = entry._generate_hash()
        assert new_hash != original_hash
    
    def test_validation_history(self):
        """Test validation history management."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # Initially empty
        assert len(history.validations) == 0
        assert history.get_latest_validation() is None
        
        # Add entries
        entries = []
        for i in range(3):
            entry = AuditEntry(
                entry_id=f"entry_{i}",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                operation_type="safety_validation",
                user_id=f"user_{i}",
                blast_plan_id="test_plan",
                validation_result={'is_valid': True},
                configuration_snapshot={},
                metadata={}
            )
            entries.append(entry)
            history.add_validation(entry)
        
        # Should be sorted by timestamp
        assert len(history.validations) == 3
        timestamps = [v.timestamp for v in history.validations]
        assert timestamps == sorted(timestamps)
        
        # Latest should be most recent
        latest = history.get_latest_validation()
        assert latest == entries[0]  # Most recent (0 hours ago)
        
        # Should find by ID
        found = history.get_validation_by_id("entry_1")
        assert found == entries[1]
        
        # Should verify chain integrity
        assert history.verify_chain_integrity()
        
        # Tampering should break chain integrity
        entries[0].metadata['tampered'] = True
        assert not history.verify_chain_integrity()
    
    def test_audit_trail_operations(self):
        """Test audit trail basic operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            # Create validation result
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={'version': '1.0.0'}
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
            assert entry.operation_type == "safety_validation"
            
            # Get history
            history = audit_trail.get_validation_history("test_plan")
            assert len(history.validations) == 1
            assert history.validations[0].entry_id == entry_id
    
    def test_audit_trail_configuration_changes(self):
        """Test recording configuration changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            old_config = {'max_charge': 50.0, 'version': '1.0.0'}
            new_config = {'max_charge': 45.0, 'version': '1.1.0'}
            
            entry_id = audit_trail.record_configuration_change(
                old_config, new_config, "admin_user", "Safety update"
            )
            
            entry = audit_trail.get_audit_entry(entry_id)
            assert entry.operation_type == "config_change"
            assert entry.user_id == "admin_user"
            assert entry.metadata['change_reason'] == "Safety update"
            assert 'config_diff' in entry.metadata
            
            # Check diff calculation
            diff = entry.metadata['config_diff']
            assert 'modified' in diff
            assert 'max_charge' in diff['modified']
    
    def test_audit_trail_sign_off(self):
        """Test engineer sign-off recording."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            entry_id = audit_trail.record_sign_off(
                "test_plan", "John Engineer", "ENG001", 
                "validation_123", "I certify this plan is safe"
            )
            
            entry = audit_trail.get_audit_entry(entry_id)
            assert entry.operation_type == "engineer_signoff"
            assert entry.blast_plan_id == "test_plan"
            assert entry.metadata['engineer_name'] == "John Engineer"
            assert entry.metadata['engineer_id'] == "ENG001"
            assert 'digital_signature' in entry.metadata
    
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
                    validation_result, f"plan_{i}", f"user_{i}"
                )
            
            # Verify integrity
            integrity_result = audit_trail.verify_audit_integrity()
            
            assert integrity_result['overall_status'] == 'VALID'
            assert integrity_result['total_entries'] == 3
            assert integrity_result['verified_entries'] == 3
            assert len(integrity_result['failed_entries']) == 0
    
    def test_compliance_report_generation(self):
        """Test compliance report generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            
            # Record validation
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
            
            # Record sign-off
            signoff_entry_id = audit_trail.record_sign_off(
                "test_plan", "Jane Engineer", "ENG002", 
                validation_entry_id, "Plan approved"
            )
            
            # Generate compliance report
            report = audit_trail.generate_compliance_report("test_plan")
            
            assert report['blast_plan_id'] == "test_plan"
            assert report['total_validations'] == 2  # validation + sign-off
            assert report['compliance_status'] == 'COMPLIANT'
            assert report['sign_off_status'] == 'SIGNED'
            assert report['audit_trail_integrity'] == 'VALID'
            
            # Check sign-off details
            assert 'sign_off_details' in report
            assert report['sign_off_details']['engineer_name'] == "Jane Engineer"
    
    def test_safety_report_generation(self):
        """Test safety report generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            report_generator = SafetyReportGenerator(audit_trail=audit_trail)
            
            # Create validation with violations
            checks = [
                SafetyCheck(
                    check_name="Critical Check",
                    check_type=SafetyCheckType.CHARGE_PER_HOLE,
                    status=SafetyStatus.FAIL,
                    limit_value=50.0,
                    actual_value=75.0,
                    safety_margin=-0.5,
                    description="Exceeds limit",
                    units="kg"
                )
            ]
            
            violations = [
                SafetyViolation(
                    violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                    severity=ViolationSeverity.CRITICAL,
                    description="Critical violation",
                    suggested_mitigation="Reduce charge immediately",
                    check_details=checks[0]
                )
            ]
            
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=False,
                safety_checks=checks,
                violations=violations,
                safety_config_snapshot={'max_charge_per_hole': 50.0}
            )
            
            # Generate report
            report = report_generator.generate_detailed_safety_report(
                validation_result, "test_plan", include_history=False
            )
            
            assert report is not None
            assert hasattr(report, 'detailed_analysis')
            
            analysis = report.detailed_analysis
            assert 'status_summary' in analysis
            assert 'violation_reports' in analysis
            assert 'margin_analysis' in analysis
            
            # Check status
            status = analysis['status_summary']
            assert status.overall_status == "INVALID"
            assert status.critical_violations == 1
            
            # Check violation reports
            violation_reports = analysis['violation_reports']
            assert len(violation_reports) == 1
            assert violation_reports[0].violation.severity == ViolationSeverity.CRITICAL
    
    def test_report_export_formats(self):
        """Test report export in different formats."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            report_generator = SafetyReportGenerator(audit_trail=audit_trail)
            
            # Simple validation result
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={}
            )
            
            report = report_generator.generate_detailed_safety_report(
                validation_result, "test_plan", include_history=False
            )
            
            # Test JSON export
            json_path = Path(tmp_dir) / "report.json"
            report_generator.export_report(report, ReportFormat.JSON, json_path)
            assert json_path.exists()
            
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            assert 'validation_result' in json_data
            
            # Test HTML export
            html_path = Path(tmp_dir) / "report.html"
            report_generator.export_report(report, ReportFormat.HTML, html_path)
            assert html_path.exists()
            
            with open(html_path, 'r') as f:
                html_content = f.read()
            assert "Safety Validation Report" in html_content
            
            # Test CSV export
            csv_path = Path(tmp_dir) / "report.csv"
            report_generator.export_report(report, ReportFormat.CSV, csv_path)
            assert csv_path.exists()
    
    def test_status_tracker_basic_functionality(self):
        """Test status tracker basic functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            status_tracker = SafetyStatusTracker(audit_trail=audit_trail)
            
            validation_result = SafetyValidationResult(
                validation_timestamp=datetime.utcnow(),
                is_valid=True,
                safety_checks=[],
                violations=[],
                safety_config_snapshot={}
            )
            
            status_summary = status_tracker.track_validation_status(
                validation_result, "test_plan", "test_user"
            )
            
            assert 'audit_entry_id' in status_summary
            assert status_summary['is_valid'] == True
            assert 'status_score' in status_summary
            assert status_summary['status_score'] > 0
            assert 'trends' in status_summary
            assert 'metrics' in status_summary
            assert 'alerts' in status_summary
    
    def test_status_tracker_alert_generation(self):
        """Test alert generation by status tracker."""
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
            
            status_summary = status_tracker.track_validation_status(
                validation_result, "test_plan", "test_user"
            )
            
            # Should generate alerts
            alerts = status_summary['alerts']
            assert len(alerts) > 0
            
            # Should have critical violation alert
            critical_alerts = [a for a in alerts if a['alert_type'] == 'CRITICAL_VIOLATION']
            assert len(critical_alerts) > 0
            assert critical_alerts[0]['severity'] == 'CRITICAL'
    
    def test_safety_dashboard(self):
        """Test safety dashboard generation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_trail = SafetyAuditTrail(audit_dir=Path(tmp_dir))
            status_tracker = SafetyStatusTracker(audit_trail=audit_trail)
            
            # Track multiple validations
            for i in range(3):
                validation_result = SafetyValidationResult(
                    validation_timestamp=datetime.utcnow(),
                    is_valid=i % 2 == 0,  # Alternate valid/invalid
                    safety_checks=[],
                    violations=[],
                    safety_config_snapshot={}
                )
                
                status_tracker.track_validation_status(
                    validation_result, "test_plan", f"user_{i}"
                )
            
            # Get dashboard
            dashboard = status_tracker.get_safety_dashboard(
                blast_plan_id="test_plan", time_window_days=30
            )
            
            assert dashboard['type'] == 'single_plan'
            assert dashboard['blast_plan_id'] == "test_plan"
            assert 'metrics' in dashboard
            assert 'recent_summary' in dashboard
            assert 'time_window' in dashboard
            
            # Check recent summary
            recent = dashboard['recent_summary']
            assert recent['total_recent'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])