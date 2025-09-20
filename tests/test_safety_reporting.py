"""
Tests for safety reporting system.
Validates requirements 4.3, 4.5, 4.6 for safety reporting and audit trails.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path
import tempfile

from src.drill_blast_system.safety.reporting import (
    SafetyReportGenerator, SafetyMarginAnalysis, ViolationReport,
    SafetyStatusSummary, ReportFormat
)
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity, SafetyReport
)
from src.drill_blast_system.safety.audit import SafetyAuditTrail, ValidationHistory, AuditEntry


@pytest.fixture
def sample_validation_result():
    """Create sample validation result for testing."""
    safety_checks = [
        SafetyCheck(
            check_name="Charge limit - Hole H001",
            check_type=SafetyCheckType.CHARGE_PER_HOLE,
            status=SafetyStatus.PASS,
            limit_value=50.0,
            actual_value=30.0,
            safety_margin=0.4,
            description="Charge within limits",
            units="kg"
        ),
        SafetyCheck(
            check_name="PPV limit - Test Structure",
            check_type=SafetyCheckType.PPV_LIMIT,
            status=SafetyStatus.FAIL,
            limit_value=2.0,
            actual_value=3.5,
            safety_margin=-0.75,
            description="PPV exceeds limit",
            units="mm/s"
        ),
        SafetyCheck(
            check_name="Powder factor",
            check_type=SafetyCheckType.POWDER_FACTOR,
            status=SafetyStatus.WARNING,
            limit_value=1.0,
            actual_value=0.95,
            safety_margin=0.05,
            description="Approaching maximum powder factor",
            units="kg/t"
        )
    ]
    
    violations = [
        SafetyViolation(
            violation_type=SafetyCheckType.PPV_LIMIT.value,
            severity=ViolationSeverity.CRITICAL,
            description="PPV exceeds limit at Test Structure",
            suggested_mitigation="Reduce charges or increase distance",
            affected_holes=["H001"],
            check_details=safety_checks[1]
        )
    ]
    
    return SafetyValidationResult(
        validation_timestamp=datetime.utcnow(),
        is_valid=False,
        safety_checks=safety_checks,
        violations=violations,
        safety_config_snapshot={
            'max_charge_per_hole': 50.0,
            'ppv_default_limit': 5.0,
            'config_version': '1.0.0'
        }
    )


@pytest.fixture
def mock_audit_trail(tmp_path):
    """Create mock audit trail for testing."""
    return SafetyAuditTrail(audit_dir=tmp_path / "audit")


@pytest.fixture
def report_generator(mock_audit_trail):
    """Create report generator with mock audit trail."""
    return SafetyReportGenerator(audit_trail=mock_audit_trail)


class TestSafetyReportGenerator:
    """Test safety report generation functionality."""
    
    def test_generate_detailed_safety_report(self, report_generator, sample_validation_result):
        """Test generation of detailed safety report."""
        blast_plan_id = "test_plan_001"
        
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, blast_plan_id, include_history=False
        )
        
        assert isinstance(report, SafetyReport)
        assert report.validation_result == sample_validation_result
        assert hasattr(report, 'detailed_analysis')
        
        # Check detailed analysis components
        analysis = report.detailed_analysis
        assert 'status_summary' in analysis
        assert 'violation_reports' in analysis
        assert 'margin_analysis' in analysis
        assert 'executive_summary' in analysis
        assert 'mitigation_plan' in analysis
    
    def test_status_summary_generation(self, report_generator, sample_validation_result):
        """Test safety status summary generation."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        status_summary = report.detailed_analysis['status_summary']
        
        assert isinstance(status_summary, SafetyStatusSummary)
        assert status_summary.overall_status == "INVALID"
        assert status_summary.total_checks == 3
        assert status_summary.passed_checks == 1
        assert status_summary.failed_checks == 1
        assert status_summary.warning_checks == 1
        assert status_summary.critical_violations == 1
        assert status_summary.compliance_score < 100.0
    
    def test_violation_reports_generation(self, report_generator, sample_validation_result):
        """Test detailed violation reports generation."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        violation_reports = report.detailed_analysis['violation_reports']
        
        assert len(violation_reports) == 1
        assert isinstance(violation_reports[0], ViolationReport)
        
        vr = violation_reports[0]
        assert vr.violation.severity == ViolationSeverity.CRITICAL
        assert vr.safety_margin < 0  # Negative margin for violation
        assert len(vr.detailed_mitigation) > 1  # Should have multiple steps
        assert vr.risk_assessment is not None
    
    def test_margin_analysis_generation(self, report_generator, sample_validation_result):
        """Test safety margin analysis generation."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        margin_analysis = report.detailed_analysis['margin_analysis']
        
        assert len(margin_analysis) == 3  # One for each check
        assert all(isinstance(ma, SafetyMarginAnalysis) for ma in margin_analysis)
        
        # Check that critical violation is first (sorted by risk)
        assert margin_analysis[0].risk_level == "CRITICAL"
        assert margin_analysis[0].margin_percentage < 0
    
    def test_mitigation_recommendations(self, report_generator, sample_validation_result):
        """Test mitigation recommendations generation."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        recommendations = report.detailed_analysis['mitigation_plan']
        
        assert len(recommendations) > 0
        assert any("IMMEDIATE ACTION REQUIRED" in rec for rec in recommendations)
        assert any("REGULATORY COMPLIANCE" in rec for rec in recommendations)
    
    def test_regulatory_compliance_analysis(self, report_generator, sample_validation_result):
        """Test regulatory compliance analysis."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        compliance = report.detailed_analysis['compliance_analysis']
        
        assert compliance['overall_status'] == 'NON_COMPLIANT'
        assert 'framework_compliance' in compliance
        assert 'permit_requirements' in compliance
        assert 'documentation_requirements' in compliance
        assert 'sign_off_requirements' in compliance
        
        # Should require senior approval for critical violations
        assert any("Senior engineer" in req for req in compliance['sign_off_requirements'])
    
    def test_executive_summary_generation(self, report_generator, sample_validation_result):
        """Test executive summary generation."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        summary = report.generate_executive_summary()
        
        assert "SAFETY VALIDATION: FAILED" in summary
        assert "1 of 3 checks failed" in summary
        assert "1 critical violations" in summary
        assert sample_validation_result.validation_id in summary
    
    def test_report_export_json(self, report_generator, sample_validation_result, tmp_path):
        """Test JSON report export."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        output_path = tmp_path / "safety_report.json"
        report_generator.export_report(report, ReportFormat.JSON, output_path)
        
        assert output_path.exists()
        
        # Verify JSON content
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert 'validation_result' in data
        assert 'executive_summary' in data
        assert 'detailed_analysis' in data
    
    def test_report_export_html(self, report_generator, sample_validation_result, tmp_path):
        """Test HTML report export."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        output_path = tmp_path / "safety_report.html"
        report_generator.export_report(report, ReportFormat.HTML, output_path)
        
        assert output_path.exists()
        
        # Verify HTML content
        with open(output_path, 'r') as f:
            content = f.read()
        
        assert "<!DOCTYPE html>" in content
        assert "Safety Validation Report" in content
        assert "Executive Summary" in content
    
    def test_report_export_csv(self, report_generator, sample_validation_result, tmp_path):
        """Test CSV report export."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        output_path = tmp_path / "safety_report.csv"
        report_generator.export_report(report, ReportFormat.CSV, output_path)
        
        assert output_path.exists()
        
        # Verify CSV content
        with open(output_path, 'r') as f:
            content = f.read()
        
        assert "Check Name,Type,Status,Limit,Actual,Margin,Units,Description" in content
        assert "Charge limit - Hole H001" in content
    
    def test_validation_history_formatting(self, report_generator, mock_audit_trail):
        """Test validation history formatting."""
        # Create mock validation history
        blast_plan_id = "test_plan"
        
        # Create mock audit entries
        entries = []
        for i in range(3):
            entry = AuditEntry(
                entry_id=f"entry_{i}",
                timestamp=datetime.utcnow() - timedelta(days=i),
                operation_type="safety_validation",
                user_id=f"user_{i}",
                blast_plan_id=blast_plan_id,
                validation_result={
                    'is_valid': i % 2 == 0,
                    'safety_checks': [{'status': 'PASS'}] * (i + 1),
                    'violations': [] if i % 2 == 0 else [{'type': 'test'}]
                },
                configuration_snapshot={'version': '1.0.0'},
                metadata={}
            )
            entries.append(entry)
        
        history = ValidationHistory(blast_plan_id=blast_plan_id, validations=entries)
        
        formatted = report_generator._format_validation_history(history)
        
        assert formatted['total_validations'] == 3
        assert 'first_validation' in formatted
        assert 'latest_validation' in formatted
        assert len(formatted['history']) == 3
        
        # Check individual entries
        for entry_data in formatted['history']:
            assert 'validation_id' in entry_data
            assert 'timestamp' in entry_data
            assert 'integrity_verified' in entry_data
    
    def test_compliance_framework_checks(self, report_generator, sample_validation_result):
        """Test compliance framework checking."""
        # Test individual compliance check methods
        charge_compliance = report_generator._check_charge_compliance(sample_validation_result)
        ppv_compliance = report_generator._check_ppv_compliance(sample_validation_result)
        
        assert charge_compliance['status'] == 'COMPLIANT'  # No charge violations in sample
        assert ppv_compliance['status'] == 'NON_COMPLIANT'  # Has PPV violation
        assert ppv_compliance['failed_checks'] == 1
    
    def test_risk_assessment_levels(self, report_generator):
        """Test violation risk assessment levels."""
        # Test different violation scenarios
        critical_violation = SafetyViolation(
            violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
            severity=ViolationSeverity.CRITICAL,
            description="Critical test violation",
            suggested_mitigation="Test mitigation"
        )
        
        risk = report_generator._assess_violation_risk(critical_violation, -75.0)
        assert "EXTREME" in risk
        
        high_violation = SafetyViolation(
            violation_type=SafetyCheckType.PPV_LIMIT.value,
            severity=ViolationSeverity.HIGH,
            description="High test violation",
            suggested_mitigation="Test mitigation"
        )
        
        risk = report_generator._assess_violation_risk(high_violation, -25.0)
        assert "HIGH" in risk
    
    def test_detailed_mitigation_generation(self, report_generator):
        """Test detailed mitigation step generation."""
        violation = SafetyViolation(
            violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
            severity=ViolationSeverity.CRITICAL,
            description="Charge exceeds limit",
            suggested_mitigation="Reduce charge"
        )
        
        detailed_steps = report_generator._generate_detailed_mitigation(violation)
        
        assert len(detailed_steps) > 1
        assert "Reduce charge" in detailed_steps[0]  # Base mitigation
        assert any("hole diameter" in step.lower() for step in detailed_steps)
        assert any("documentation" in step.lower() for step in detailed_steps)
    
    def test_margin_recommendation_generation(self, report_generator):
        """Test safety margin recommendation generation."""
        check = SafetyCheck(
            check_name="Test Check",
            check_type=SafetyCheckType.CHARGE_PER_HOLE,
            status=SafetyStatus.FAIL,
            limit_value=50.0,
            actual_value=75.0,
            safety_margin=-0.5,
            description="Test check",
            units="kg"
        )
        
        # Test critical margin
        recommendation = report_generator._generate_margin_recommendation(check, -60.0)
        assert "CRITICAL" in recommendation
        
        # Test safe margin
        recommendation = report_generator._generate_margin_recommendation(check, 30.0)
        assert "SAFE" in recommendation
    
    def test_impact_estimation(self, report_generator):
        """Test violation impact estimation."""
        critical_violation = SafetyViolation(
            violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
            severity=ViolationSeverity.CRITICAL,
            description="Critical violation",
            suggested_mitigation="Fix immediately"
        )
        
        cost_impact, time_impact = report_generator._estimate_violation_impact(critical_violation)
        
        assert "HIGH" in cost_impact
        assert "days" in time_impact
        
        low_violation = SafetyViolation(
            violation_type=SafetyCheckType.BURDEN_SPACING.value,
            severity=ViolationSeverity.LOW,
            description="Low violation",
            suggested_mitigation="Minor adjustment"
        )
        
        cost_impact, time_impact = report_generator._estimate_violation_impact(low_violation)
        
        assert "MINIMAL" in cost_impact
        assert "hours" in time_impact
    
    def test_regulatory_references(self, report_generator):
        """Test regulatory reference lookup."""
        charge_ref = report_generator._get_regulatory_reference(
            SafetyViolation(
                violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                severity=ViolationSeverity.HIGH,
                description="Test",
                suggested_mitigation="Test"
            )
        )
        
        assert charge_ref is not None
        assert "Mining Safety Regulation" in charge_ref
        
        ppv_ref = report_generator._get_regulatory_reference(
            SafetyViolation(
                violation_type=SafetyCheckType.PPV_LIMIT.value,
                severity=ViolationSeverity.HIGH,
                description="Test",
                suggested_mitigation="Test"
            )
        )
        
        assert ppv_ref is not None
        assert "Environmental Protection Act" in ppv_ref
    
    def test_unsupported_export_format(self, report_generator, sample_validation_result):
        """Test error handling for unsupported export formats."""
        report = report_generator.generate_detailed_safety_report(
            sample_validation_result, "test_plan", include_history=False
        )
        
        with pytest.raises(ValueError, match="Unsupported report format"):
            report_generator.export_report(report, "INVALID_FORMAT", Path("test.txt"))
    
    def test_report_with_validation_history(self, report_generator, sample_validation_result, mock_audit_trail):
        """Test report generation with validation history included."""
        blast_plan_id = "test_plan_with_history"
        
        # Mock the audit trail to return some history
        mock_history = ValidationHistory(blast_plan_id=blast_plan_id)
        mock_entry = AuditEntry(
            entry_id="test_entry",
            timestamp=datetime.utcnow() - timedelta(days=1),
            operation_type="safety_validation",
            user_id="test_user",
            blast_plan_id=blast_plan_id,
            validation_result={'is_valid': True, 'safety_checks': [], 'violations': []},
            configuration_snapshot={'version': '1.0.0'},
            metadata={}
        )
        mock_history.add_validation(mock_entry)
        
        with patch.object(mock_audit_trail, 'get_validation_history', return_value=mock_history):
            report = report_generator.generate_detailed_safety_report(
                sample_validation_result, blast_plan_id, include_history=True
            )
        
        assert 'validation_history' in report.detailed_analysis
        assert report.detailed_analysis['validation_history'] is not None
        assert report.detailed_analysis['validation_history']['total_validations'] == 1