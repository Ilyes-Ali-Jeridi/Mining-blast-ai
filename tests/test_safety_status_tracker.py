"""
Tests for safety status tracking system.
Validates requirements 4.3, 4.5, 4.6 for safety status tracking and trends.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from collections import defaultdict

from src.drill_blast_system.safety.status_tracker import (
    SafetyStatusTracker, SafetyTrend, SafetyMetrics, SafetyAlert,
    TrendDirection
)
from src.drill_blast_system.safety.models import (
    SafetyValidationResult, SafetyCheck, SafetyViolation, SafetyStatus,
    SafetyCheckType, ViolationSeverity
)
from src.drill_blast_system.safety.audit import SafetyAuditTrail, ValidationHistory, AuditEntry


@pytest.fixture
def mock_audit_trail(tmp_path):
    """Create mock audit trail for testing."""
    return SafetyAuditTrail(audit_dir=tmp_path / "audit")


@pytest.fixture
def status_tracker(mock_audit_trail):
    """Create status tracker with mock audit trail."""
    return SafetyStatusTracker(audit_trail=mock_audit_trail)


@pytest.fixture
def sample_validation_result():
    """Create sample validation result."""
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
            check_name="PPV limit - Structure A",
            check_type=SafetyCheckType.PPV_LIMIT,
            status=SafetyStatus.WARNING,
            limit_value=5.0,
            actual_value=4.5,
            safety_margin=0.1,
            description="PPV approaching limit",
            units="mm/s"
        )
    ]
    
    return SafetyValidationResult(
        validation_timestamp=datetime.utcnow(),
        is_valid=True,
        safety_checks=safety_checks,
        violations=[],
        safety_config_snapshot={'max_charge_per_hole': 50.0}
    )


@pytest.fixture
def critical_validation_result():
    """Create validation result with critical violations."""
    safety_checks = [
        SafetyCheck(
            check_name="Charge limit - Hole H001",
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
            description="Charge exceeds maximum limit",
            suggested_mitigation="Reduce charge or split hole",
            affected_holes=["H001"]
        )
    ]
    
    return SafetyValidationResult(
        validation_timestamp=datetime.utcnow(),
        is_valid=False,
        safety_checks=safety_checks,
        violations=violations,
        safety_config_snapshot={'max_charge_per_hole': 50.0}
    )


class TestSafetyStatusTracker:
    """Test safety status tracking functionality."""
    
    def test_track_validation_status(self, status_tracker, sample_validation_result):
        """Test tracking validation status."""
        blast_plan_id = "test_plan_001"
        user_id = "test_user"
        
        status_summary = status_tracker.track_validation_status(
            sample_validation_result, blast_plan_id, user_id
        )
        
        assert isinstance(status_summary, dict)
        assert 'audit_entry_id' in status_summary
        assert 'validation_timestamp' in status_summary
        assert status_summary['is_valid'] == True
        assert status_summary['total_checks'] == 2
        assert status_summary['failed_checks'] == 0
        assert status_summary['violations'] == 0
        assert 'trends' in status_summary
        assert 'metrics' in status_summary
        assert 'alerts' in status_summary
        assert 'status_score' in status_summary
    
    def test_critical_violation_alert_generation(self, status_tracker, critical_validation_result):
        """Test alert generation for critical violations."""
        blast_plan_id = "test_plan_critical"
        
        status_summary = status_tracker.track_validation_status(
            critical_validation_result, blast_plan_id
        )
        
        alerts = status_summary['alerts']
        assert len(alerts) > 0
        
        # Should have critical violation alert
        critical_alerts = [a for a in alerts if a['alert_type'] == 'CRITICAL_VIOLATION']
        assert len(critical_alerts) > 0
        
        alert = critical_alerts[0]
        assert alert['severity'] == 'CRITICAL'
        assert blast_plan_id in alert['message']
        assert 'Stop all work' in alert['recommended_actions'][0]
    
    def test_multiple_failure_alert_generation(self, status_tracker):
        """Test alert generation for multiple failures."""
        # Create validation with many failures
        safety_checks = []
        violations = []
        
        for i in range(6):  # More than 5 failures
            check = SafetyCheck(
                check_name=f"Check {i}",
                check_type=SafetyCheckType.CHARGE_PER_HOLE,
                status=SafetyStatus.FAIL,
                limit_value=50.0,
                actual_value=60.0,
                safety_margin=-0.2,
                description=f"Check {i} failed",
                units="kg"
            )
            safety_checks.append(check)
            
            violation = SafetyViolation(
                violation_type=SafetyCheckType.CHARGE_PER_HOLE.value,
                severity=ViolationSeverity.HIGH,
                description=f"Violation {i}",
                suggested_mitigation="Fix it"
            )
            violations.append(violation)
        
        validation_result = SafetyValidationResult(
            validation_timestamp=datetime.utcnow(),
            is_valid=False,
            safety_checks=safety_checks,
            violations=violations,
            safety_config_snapshot={}
        )
        
        status_summary = status_tracker.track_validation_status(
            validation_result, "test_plan_multiple"
        )
        
        alerts = status_summary['alerts']
        multiple_alerts = [a for a in alerts if a['alert_type'] == 'MULTIPLE_FAILURES']
        assert len(multiple_alerts) > 0
    
    def test_status_score_calculation(self, status_tracker, sample_validation_result, critical_validation_result):
        """Test status score calculation."""
        # Valid result should have high score
        valid_summary = status_tracker.track_validation_status(
            sample_validation_result, "test_plan_valid"
        )
        valid_score = valid_summary['status_score']
        assert valid_score > 80.0
        
        # Critical violation should have low score
        critical_summary = status_tracker.track_validation_status(
            critical_validation_result, "test_plan_critical"
        )
        critical_score = critical_summary['status_score']
        assert critical_score < 80.0
        assert critical_score < valid_score
    
    def test_get_safety_dashboard_single_plan(self, status_tracker, sample_validation_result):
        """Test safety dashboard for single blast plan."""
        blast_plan_id = "test_plan_dashboard"
        
        # Track some validations
        for i in range(3):
            status_tracker.track_validation_status(
                sample_validation_result, blast_plan_id, f"user_{i}"
            )
        
        dashboard = status_tracker.get_safety_dashboard(
            blast_plan_id=blast_plan_id, time_window_days=30
        )
        
        assert dashboard['type'] == 'single_plan'
        assert dashboard['blast_plan_id'] == blast_plan_id
        assert 'metrics' in dashboard
        assert 'trends' in dashboard
        assert 'recent_summary' in dashboard
        assert 'active_alerts' in dashboard
        assert 'time_window' in dashboard
        
        # Check recent summary
        recent = dashboard['recent_summary']
        assert recent['total_recent'] == 3
        assert recent['successful_recent'] == 3
        assert recent['recent_success_rate'] == 1.0
    
    def test_get_safety_dashboard_system_wide(self, status_tracker):
        """Test system-wide safety dashboard."""
        dashboard = status_tracker.get_safety_dashboard(
            blast_plan_id=None, time_window_days=30
        )
        
        assert dashboard['type'] == 'system_wide'
        assert 'active_alerts' in dashboard
        assert 'time_window' in dashboard
    
    def test_trend_analysis_with_insufficient_data(self, status_tracker):
        """Test trend analysis with insufficient data points."""
        # Create validation history with only 2 entries (need 3+ for trends)
        history = ValidationHistory(blast_plan_id="test_plan")
        
        for i in range(2):
            entry = AuditEntry(
                entry_id=f"entry_{i}",
                timestamp=datetime.utcnow() - timedelta(days=i),
                operation_type="safety_validation",
                user_id="test_user",
                blast_plan_id="test_plan",
                validation_result={
                    'safety_checks': [
                        {'check_name': 'Test Check', 'actual_value': 30.0 + i}
                    ]
                },
                configuration_snapshot={},
                metadata={}
            )
            history.add_validation(entry)
        
        trends = status_tracker._analyze_safety_trends(history)
        assert len(trends) == 0  # Should return empty list
    
    def test_trend_analysis_with_sufficient_data(self, status_tracker):
        """Test trend analysis with sufficient data points."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # Create trend data - increasing values (degrading safety)
        for i in range(5):
            entry = AuditEntry(
                entry_id=f"entry_{i}",
                timestamp=datetime.utcnow() - timedelta(days=4-i),  # Chronological order
                operation_type="safety_validation",
                user_id="test_user",
                blast_plan_id="test_plan",
                validation_result={
                    'safety_checks': [
                        {
                            'check_name': 'Charge Check',
                            'actual_value': 30.0 + (i * 5.0)  # Increasing trend
                        }
                    ]
                },
                configuration_snapshot={},
                metadata={}
            )
            history.add_validation(entry)
        
        trends = status_tracker._analyze_safety_trends(history)
        assert len(trends) > 0
        
        # Should detect degrading trend (increasing values)
        trend = trends[0]
        assert isinstance(trend, SafetyTrend)
        assert trend.trend_direction in [TrendDirection.DEGRADING, TrendDirection.IMPROVING]
    
    def test_calculate_trend_stable(self, status_tracker):
        """Test trend calculation for stable values."""
        values = [30.0, 30.1, 29.9, 30.0, 30.1]  # Stable around 30
        timestamps = [datetime.utcnow() - timedelta(days=i) for i in range(5)]
        
        trend = status_tracker._calculate_trend(values, timestamps)
        
        assert trend.trend_direction == TrendDirection.STABLE
        assert abs(trend.trend_strength) < 0.1
    
    def test_calculate_trend_improving(self, status_tracker):
        """Test trend calculation for improving values."""
        values = [50.0, 45.0, 40.0, 35.0, 30.0]  # Decreasing (improving for safety)
        timestamps = [datetime.utcnow() - timedelta(days=i) for i in range(5)]
        
        trend = status_tracker._calculate_trend(values, timestamps)
        
        assert trend.trend_direction == TrendDirection.DEGRADING  # Negative slope
        assert trend.trend_strength > 0
    
    def test_calculate_trend_degrading(self, status_tracker):
        """Test trend calculation for degrading values."""
        values = [30.0, 35.0, 40.0, 45.0, 50.0]  # Increasing (degrading for safety)
        timestamps = [datetime.utcnow() - timedelta(days=i) for i in range(5)]
        
        trend = status_tracker._calculate_trend(values, timestamps)
        
        assert trend.trend_direction == TrendDirection.IMPROVING  # Positive slope
        assert trend.trend_strength > 0
    
    def test_degrading_trend_alert_generation(self, status_tracker, sample_validation_result):
        """Test alert generation for degrading trends."""
        blast_plan_id = "test_plan_trend"
        
        # Mock trend analysis to return degrading trend
        degrading_trend = SafetyTrend(
            parameter_name="Test Parameter",
            trend_direction=TrendDirection.DEGRADING,
            trend_strength=0.8,  # Strong degrading trend
            recent_values=[30.0, 35.0, 40.0, 45.0, 50.0],
            timestamps=[datetime.utcnow() - timedelta(days=i) for i in range(5)],
            statistical_significance=0.9,
            recommendation="Investigate degrading trend"
        )
        
        with patch.object(status_tracker, '_analyze_safety_trends', return_value=[degrading_trend]):
            status_summary = status_tracker.track_validation_status(
                sample_validation_result, blast_plan_id
            )
        
        alerts = status_summary['alerts']
        trend_alerts = [a for a in alerts if a['alert_type'] == 'DEGRADING_TREND']
        assert len(trend_alerts) > 0
        
        alert = trend_alerts[0]
        assert alert['severity'] == 'HIGH'
        assert 'degrading' in alert['message'].lower()
    
    def test_safety_metrics_calculation(self, status_tracker):
        """Test safety metrics calculation."""
        history = ValidationHistory(blast_plan_id="test_plan")
        
        # Add mix of successful and failed validations
        validation_data = [
            {'is_valid': True, 'violations': [], 'safety_checks': [{'safety_margin': 0.2}]},
            {'is_valid': False, 'violations': [{'violation_type': 'charge_per_hole'}], 'safety_checks': [{'safety_margin': -0.1}]},
            {'is_valid': True, 'violations': [], 'safety_checks': [{'safety_margin': 0.3}]},
        ]
        
        for i, val_data in enumerate(validation_data):
            entry = AuditEntry(
                entry_id=f"entry_{i}",
                timestamp=datetime.utcnow() - timedelta(days=i),
                operation_type="safety_validation",
                user_id="test_user",
                blast_plan_id="test_plan",
                validation_result=val_data,
                configuration_snapshot={},
                metadata={}
            )
            history.add_validation(entry)
        
        metrics = status_tracker._calculate_safety_metrics(history)
        
        assert isinstance(metrics, SafetyMetrics)
        assert metrics.total_validations == 3
        assert metrics.successful_validations == 2
        assert metrics.failed_validations == 1
        assert metrics.success_rate == 2/3
        assert metrics.average_violations_per_validation == 1/3
        assert metrics.most_common_violation_type == 'charge_per_hole'
        assert metrics.worst_safety_margin == -0.1
        assert metrics.best_safety_margin == 0.3
    
    def test_alert_management(self, status_tracker, critical_validation_result):
        """Test alert management functionality."""
        blast_plan_id = "test_plan_alerts"
        
        # Generate alerts
        status_tracker.track_validation_status(critical_validation_result, blast_plan_id)
        
        # Check active alerts
        assert len(status_tracker._active_alerts) > 0
        
        # Get alert by ID
        alert_id = status_tracker._active_alerts[0].alert_id
        alert = status_tracker.get_alert_by_id(alert_id)
        assert alert is not None
        assert alert.alert_id == alert_id
        
        # Clear alerts for specific plan
        cleared_count = status_tracker.clear_alerts(blast_plan_id)
        assert cleared_count > 0
        assert len(status_tracker._active_alerts) == 0
    
    def test_alert_summary(self, status_tracker, critical_validation_result):
        """Test alert summary generation."""
        # Generate multiple alerts
        for i in range(3):
            status_tracker.track_validation_status(
                critical_validation_result, f"test_plan_{i}"
            )
        
        dashboard = status_tracker.get_safety_dashboard()
        alert_summary = dashboard['alert_summary']
        
        assert alert_summary['total_alerts'] >= 3
        assert 'by_type' in alert_summary
        assert 'by_severity' in alert_summary
        assert 'most_recent' in alert_summary
        
        # Should have critical violation alerts
        assert 'CRITICAL_VIOLATION' in alert_summary['by_type']
        assert 'CRITICAL' in alert_summary['by_severity']
    
    def test_trend_recommendation_generation(self, status_tracker):
        """Test trend recommendation generation."""
        # Test different trend scenarios
        urgent_rec = status_tracker._generate_trend_recommendation(
            TrendDirection.DEGRADING, 0.8, 0.9
        )
        assert "URGENT" in urgent_rec
        
        caution_rec = status_tracker._generate_trend_recommendation(
            TrendDirection.DEGRADING, 0.4, 0.7
        )
        assert "CAUTION" in caution_rec
        
        positive_rec = status_tracker._generate_trend_recommendation(
            TrendDirection.IMPROVING, 0.6, 0.8
        )
        assert "POSITIVE" in positive_rec
        
        stable_rec = status_tracker._generate_trend_recommendation(
            TrendDirection.STABLE, 0.1, 0.5
        )
        assert "STABLE" in stable_rec
    
    def test_data_conversion_methods(self, status_tracker):
        """Test data conversion methods."""
        # Test trend to dict
        trend = SafetyTrend(
            parameter_name="Test Parameter",
            trend_direction=TrendDirection.IMPROVING,
            trend_strength=0.5,
            recent_values=[1.0, 2.0, 3.0],
            timestamps=[datetime.utcnow() - timedelta(days=i) for i in range(3)],
            statistical_significance=0.7,
            recommendation="Keep it up"
        )
        
        trend_dict = status_tracker._trend_to_dict(trend)
        assert trend_dict['parameter_name'] == "Test Parameter"
        assert trend_dict['trend_direction'] == "improving"
        assert trend_dict['trend_strength'] == 0.5
        assert len(trend_dict['timestamps']) == 3
        
        # Test metrics to dict
        metrics = SafetyMetrics(
            total_validations=10,
            successful_validations=8,
            failed_validations=2,
            success_rate=0.8,
            average_violations_per_validation=0.2,
            most_common_violation_type="charge_per_hole",
            worst_safety_margin=-0.1,
            best_safety_margin=0.5,
            trend_analysis=[]
        )
        
        metrics_dict = status_tracker._metrics_to_dict(metrics)
        assert metrics_dict['total_validations'] == 10
        assert metrics_dict['success_rate'] == 0.8
        assert metrics_dict['most_common_violation_type'] == "charge_per_hole"
        
        # Test alert to dict
        alert = SafetyAlert(
            alert_id="test_alert",
            alert_type="TEST_ALERT",
            severity="HIGH",
            message="Test alert message",
            blast_plan_id="test_plan",
            triggered_at=datetime.utcnow(),
            parameters_affected=["param1", "param2"],
            recommended_actions=["action1", "action2"]
        )
        
        alert_dict = status_tracker._alert_to_dict(alert)
        assert alert_dict['alert_id'] == "test_alert"
        assert alert_dict['alert_type'] == "TEST_ALERT"
        assert alert_dict['severity'] == "HIGH"
        assert len(alert_dict['parameters_affected']) == 2