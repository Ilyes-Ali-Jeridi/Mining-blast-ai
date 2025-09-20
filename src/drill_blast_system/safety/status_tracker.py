"""
Safety status tracking system for monitoring validation history and trends.
Implements requirements 4.3, 4.5, 4.6 for safety status tracking.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

from .models import SafetyValidationResult, SafetyStatus, ViolationSeverity
from .audit import SafetyAuditTrail, ValidationHistory, AuditEntry

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """Safety trend direction."""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class SafetyTrend:
    """Safety trend analysis."""
    parameter_name: str
    trend_direction: TrendDirection
    trend_strength: float  # -1.0 to 1.0
    recent_values: List[float]
    timestamps: List[datetime]
    statistical_significance: float  # 0.0 to 1.0
    recommendation: str


@dataclass
class SafetyMetrics:
    """Safety performance metrics."""
    total_validations: int
    successful_validations: int
    failed_validations: int
    success_rate: float
    average_violations_per_validation: float
    most_common_violation_type: Optional[str]
    worst_safety_margin: float
    best_safety_margin: float
    trend_analysis: List[SafetyTrend]


@dataclass
class SafetyAlert:
    """Safety alert for concerning trends or violations."""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    blast_plan_id: Optional[str]
    triggered_at: datetime
    parameters_affected: List[str]
    recommended_actions: List[str]
    auto_generated: bool = True


class SafetyStatusTracker:
    """Tracks safety validation status and trends over time."""
    
    def __init__(self, audit_trail: Optional[SafetyAuditTrail] = None):
        """Initialize status tracker."""
        self.audit_trail = audit_trail or SafetyAuditTrail()
        self._active_alerts: List[SafetyAlert] = []
        
    def track_validation_status(self, 
                              validation_result: SafetyValidationResult,
                              blast_plan_id: str,
                              user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Track validation status and update trends.
        
        Args:
            validation_result: Safety validation result
            blast_plan_id: Blast plan identifier
            user_id: User performing validation
            
        Returns:
            Status tracking summary
        """
        # Record validation in audit trail
        audit_entry_id = self.audit_trail.record_validation(
            validation_result, blast_plan_id, user_id
        )
        
        # Get validation history for trend analysis
        history = self.audit_trail.get_validation_history(blast_plan_id)
        
        # Analyze trends
        trends = self._analyze_safety_trends(history)
        
        # Generate alerts if needed
        alerts = self._check_for_alerts(validation_result, trends, blast_plan_id)
        self._active_alerts.extend(alerts)
        
        # Calculate metrics
        metrics = self._calculate_safety_metrics(history)
        
        # Create status summary
        status_summary = {
            'audit_entry_id': audit_entry_id,
            'validation_timestamp': validation_result.validation_timestamp.isoformat(),
            'is_valid': validation_result.is_valid,
            'total_checks': len(validation_result.safety_checks),
            'failed_checks': len(validation_result.failed_checks),
            'violations': len(validation_result.violations),
            'critical_violations': len(validation_result.critical_violations),
            'trends': [self._trend_to_dict(trend) for trend in trends],
            'metrics': self._metrics_to_dict(metrics),
            'alerts': [self._alert_to_dict(alert) for alert in alerts],
            'status_score': self._calculate_status_score(validation_result, trends)
        }
        
        logger.info(f"Tracked validation status for blast plan {blast_plan_id}: "
                   f"valid={validation_result.is_valid}, alerts={len(alerts)}")
        
        return status_summary
    
    def get_safety_dashboard(self, 
                           blast_plan_id: Optional[str] = None,
                           time_window_days: int = 30) -> Dict[str, Any]:
        """
        Get safety dashboard with current status and trends.
        
        Args:
            blast_plan_id: Specific blast plan or None for all
            time_window_days: Time window for analysis
            
        Returns:
            Safety dashboard data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        
        if blast_plan_id:
            # Single blast plan dashboard
            history = self.audit_trail.get_validation_history(blast_plan_id)
            recent_validations = [v for v in history.validations 
                                if v.timestamp >= cutoff_date]
            
            dashboard = self._create_single_plan_dashboard(history, recent_validations)
            dashboard['blast_plan_id'] = blast_plan_id
        else:
            # System-wide dashboard
            dashboard = self._create_system_dashboard(cutoff_date)
        
        # Add active alerts
        dashboard['active_alerts'] = [self._alert_to_dict(alert) for alert in self._active_alerts]
        dashboard['alert_summary'] = self._summarize_alerts()
        
        # Add time window info
        dashboard['time_window'] = {
            'days': time_window_days,
            'start_date': cutoff_date.isoformat(),
            'end_date': datetime.utcnow().isoformat()
        }
        
        return dashboard
    
    def _analyze_safety_trends(self, history: ValidationHistory) -> List[SafetyTrend]:
        """Analyze safety trends from validation history."""
        if len(history.validations) < 3:
            return []  # Need at least 3 points for trend analysis
        
        trends = []
        
        # Group validation results by parameter
        parameter_data = defaultdict(list)
        
        for entry in history.validations:
            if entry.validation_result and entry.operation_type == "safety_validation":
                result_data = entry.validation_result
                
                for check in result_data.get('safety_checks', []):
                    param_name = check.get('check_name', '')
                    actual_value = check.get('actual_value', 0.0)
                    timestamp = entry.timestamp
                    
                    parameter_data[param_name].append((timestamp, actual_value))
        
        # Analyze trends for each parameter
        for param_name, data_points in parameter_data.items():
            if len(data_points) < 3:
                continue
                
            # Sort by timestamp
            data_points.sort(key=lambda x: x[0])
            
            timestamps = [dp[0] for dp in data_points]
            values = [dp[1] for dp in data_points]
            
            # Calculate trend
            trend = self._calculate_trend(values, timestamps)
            trends.append(trend)
        
        return trends
    
    def _calculate_trend(self, values: List[float], timestamps: List[datetime]) -> SafetyTrend:
        """Calculate trend for a parameter."""
        if len(values) < 3:
            return SafetyTrend(
                parameter_name="unknown",
                trend_direction=TrendDirection.UNKNOWN,
                trend_strength=0.0,
                recent_values=values,
                timestamps=timestamps,
                statistical_significance=0.0,
                recommendation="Insufficient data for trend analysis"
            )
        
        # Simple linear regression for trend
        n = len(values)
        x_values = list(range(n))  # Use indices as x values
        
        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator
        
        # Determine trend direction and strength
        if abs(slope) < 0.01:  # Threshold for "stable"
            direction = TrendDirection.STABLE
            strength = 0.0
        elif slope > 0:
            direction = TrendDirection.IMPROVING
            strength = min(1.0, abs(slope) / max(values) if max(values) > 0 else 0.0)
        else:
            direction = TrendDirection.DEGRADING
            strength = min(1.0, abs(slope) / max(values) if max(values) > 0 else 0.0)
        
        # Calculate statistical significance (simplified)
        variance = sum((values[i] - y_mean) ** 2 for i in range(n)) / n
        significance = min(1.0, strength * n / 10)  # Simplified significance measure
        
        # Generate recommendation
        recommendation = self._generate_trend_recommendation(direction, strength, significance)
        
        return SafetyTrend(
            parameter_name=f"Parameter_{len(values)}_points",
            trend_direction=direction,
            trend_strength=strength,
            recent_values=values[-5:],  # Last 5 values
            timestamps=timestamps[-5:],
            statistical_significance=significance,
            recommendation=recommendation
        )
    
    def _check_for_alerts(self, 
                         validation_result: SafetyValidationResult,
                         trends: List[SafetyTrend],
                         blast_plan_id: str) -> List[SafetyAlert]:
        """Check for safety alerts based on validation and trends."""
        alerts = []
        
        # Critical violation alerts
        if validation_result.has_critical_violations:
            alert = SafetyAlert(
                alert_id=f"critical_{blast_plan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                alert_type="CRITICAL_VIOLATION",
                severity="CRITICAL",
                message=f"Critical safety violations detected in blast plan {blast_plan_id}",
                blast_plan_id=blast_plan_id,
                triggered_at=datetime.utcnow(),
                parameters_affected=[v.violation_type for v in validation_result.critical_violations],
                recommended_actions=[
                    "Stop all work on this blast plan",
                    "Review and address all critical violations",
                    "Obtain senior engineer approval before proceeding"
                ]
            )
            alerts.append(alert)
        
        # Degrading trend alerts
        degrading_trends = [t for t in trends 
                           if t.trend_direction == TrendDirection.DEGRADING 
                           and t.trend_strength > 0.5]
        
        if degrading_trends:
            alert = SafetyAlert(
                alert_id=f"trend_{blast_plan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                alert_type="DEGRADING_TREND",
                severity="HIGH",
                message=f"Degrading safety trends detected in blast plan {blast_plan_id}",
                blast_plan_id=blast_plan_id,
                triggered_at=datetime.utcnow(),
                parameters_affected=[t.parameter_name for t in degrading_trends],
                recommended_actions=[
                    "Review recent changes to blast parameters",
                    "Investigate causes of degrading trends",
                    "Consider reverting to previous safe configurations"
                ]
            )
            alerts.append(alert)
        
        # Multiple validation failures
        if len(validation_result.failed_checks) > 5:
            alert = SafetyAlert(
                alert_id=f"multiple_{blast_plan_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                alert_type="MULTIPLE_FAILURES",
                severity="HIGH",
                message=f"Multiple safety check failures in blast plan {blast_plan_id}",
                blast_plan_id=blast_plan_id,
                triggered_at=datetime.utcnow(),
                parameters_affected=[c.check_name for c in validation_result.failed_checks],
                recommended_actions=[
                    "Comprehensive review of blast plan parameters",
                    "Check for systematic issues in design",
                    "Consider using more conservative safety factors"
                ]
            )
            alerts.append(alert)
        
        return alerts
    
    def _calculate_safety_metrics(self, history: ValidationHistory) -> SafetyMetrics:
        """Calculate safety performance metrics."""
        if not history.validations:
            return SafetyMetrics(
                total_validations=0,
                successful_validations=0,
                failed_validations=0,
                success_rate=0.0,
                average_violations_per_validation=0.0,
                most_common_violation_type=None,
                worst_safety_margin=0.0,
                best_safety_margin=0.0,
                trend_analysis=[]
            )
        
        validation_entries = [v for v in history.validations 
                            if v.operation_type == "safety_validation" and v.validation_result]
        
        total_validations = len(validation_entries)
        successful_validations = sum(1 for v in validation_entries 
                                   if v.validation_result.get('is_valid', False))
        failed_validations = total_validations - successful_validations
        
        success_rate = successful_validations / total_validations if total_validations > 0 else 0.0
        
        # Calculate violation statistics
        all_violations = []
        violation_types = defaultdict(int)
        safety_margins = []
        
        for entry in validation_entries:
            result = entry.validation_result
            violations = result.get('violations', [])
            all_violations.extend(violations)
            
            for violation in violations:
                violation_types[violation.get('violation_type', 'unknown')] += 1
            
            # Collect safety margins
            for check in result.get('safety_checks', []):
                if 'safety_margin' in check:
                    safety_margins.append(check['safety_margin'])
        
        average_violations = len(all_violations) / total_validations if total_validations > 0 else 0.0
        most_common_violation = max(violation_types.items(), key=lambda x: x[1])[0] if violation_types else None
        
        worst_margin = min(safety_margins) if safety_margins else 0.0
        best_margin = max(safety_margins) if safety_margins else 0.0
        
        # Get trend analysis
        trends = self._analyze_safety_trends(history)
        
        return SafetyMetrics(
            total_validations=total_validations,
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            success_rate=success_rate,
            average_violations_per_validation=average_violations,
            most_common_violation_type=most_common_violation,
            worst_safety_margin=worst_margin,
            best_safety_margin=best_margin,
            trend_analysis=trends
        )
    
    def _calculate_status_score(self, 
                              validation_result: SafetyValidationResult,
                              trends: List[SafetyTrend]) -> float:
        """Calculate overall safety status score (0-100)."""
        base_score = 100.0
        
        # Deduct for violations
        for violation in validation_result.violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                base_score -= 25.0
            elif violation.severity == ViolationSeverity.HIGH:
                base_score -= 15.0
            elif violation.severity == ViolationSeverity.MEDIUM:
                base_score -= 10.0
            else:
                base_score -= 5.0
        
        # Deduct for failed checks
        base_score -= len(validation_result.failed_checks) * 5.0
        
        # Adjust for trends
        degrading_trends = [t for t in trends if t.trend_direction == TrendDirection.DEGRADING]
        improving_trends = [t for t in trends if t.trend_direction == TrendDirection.IMPROVING]
        
        base_score -= len(degrading_trends) * 5.0
        base_score += len(improving_trends) * 2.0
        
        return max(0.0, min(100.0, base_score))
    
    def _create_single_plan_dashboard(self, 
                                    history: ValidationHistory,
                                    recent_validations: List[AuditEntry]) -> Dict[str, Any]:
        """Create dashboard for single blast plan."""
        metrics = self._calculate_safety_metrics(history)
        trends = self._analyze_safety_trends(history)
        
        # Recent validation summary
        recent_summary = {
            'total_recent': len(recent_validations),
            'successful_recent': sum(1 for v in recent_validations 
                                   if v.validation_result and v.validation_result.get('is_valid', False)),
            'recent_success_rate': 0.0
        }
        
        if recent_summary['total_recent'] > 0:
            recent_summary['recent_success_rate'] = (
                recent_summary['successful_recent'] / recent_summary['total_recent']
            )
        
        return {
            'type': 'single_plan',
            'metrics': self._metrics_to_dict(metrics),
            'trends': [self._trend_to_dict(trend) for trend in trends],
            'recent_summary': recent_summary,
            'latest_validation': history.get_latest_validation().timestamp.isoformat() if history.validations else None
        }
    
    def _create_system_dashboard(self, cutoff_date: datetime) -> Dict[str, Any]:
        """Create system-wide dashboard."""
        # This would require access to all blast plans - simplified for now
        return {
            'type': 'system_wide',
            'message': 'System-wide dashboard requires additional implementation',
            'cutoff_date': cutoff_date.isoformat()
        }
    
    def _summarize_alerts(self) -> Dict[str, Any]:
        """Summarize active alerts."""
        alert_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for alert in self._active_alerts:
            alert_counts[alert.alert_type] += 1
            severity_counts[alert.severity] += 1
        
        return {
            'total_alerts': len(self._active_alerts),
            'by_type': dict(alert_counts),
            'by_severity': dict(severity_counts),
            'most_recent': self._active_alerts[-1].triggered_at.isoformat() if self._active_alerts else None
        }
    
    def _generate_trend_recommendation(self, 
                                     direction: TrendDirection,
                                     strength: float,
                                     significance: float) -> str:
        """Generate recommendation based on trend analysis."""
        if direction == TrendDirection.DEGRADING and strength > 0.7:
            return "URGENT: Investigate and address degrading safety performance"
        elif direction == TrendDirection.DEGRADING and strength > 0.3:
            return "CAUTION: Monitor safety parameters closely"
        elif direction == TrendDirection.IMPROVING:
            return "POSITIVE: Continue current safety practices"
        elif direction == TrendDirection.STABLE:
            return "STABLE: Maintain current safety standards"
        else:
            return "MONITOR: Collect more data for trend analysis"
    
    def _trend_to_dict(self, trend: SafetyTrend) -> Dict[str, Any]:
        """Convert trend to dictionary."""
        return {
            'parameter_name': trend.parameter_name,
            'trend_direction': trend.trend_direction.value,
            'trend_strength': trend.trend_strength,
            'recent_values': trend.recent_values,
            'timestamps': [ts.isoformat() for ts in trend.timestamps],
            'statistical_significance': trend.statistical_significance,
            'recommendation': trend.recommendation
        }
    
    def _metrics_to_dict(self, metrics: SafetyMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_validations': metrics.total_validations,
            'successful_validations': metrics.successful_validations,
            'failed_validations': metrics.failed_validations,
            'success_rate': metrics.success_rate,
            'average_violations_per_validation': metrics.average_violations_per_validation,
            'most_common_violation_type': metrics.most_common_violation_type,
            'worst_safety_margin': metrics.worst_safety_margin,
            'best_safety_margin': metrics.best_safety_margin,
            'trend_count': len(metrics.trend_analysis)
        }
    
    def _alert_to_dict(self, alert: SafetyAlert) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': alert.alert_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'blast_plan_id': alert.blast_plan_id,
            'triggered_at': alert.triggered_at.isoformat(),
            'parameters_affected': alert.parameters_affected,
            'recommended_actions': alert.recommended_actions,
            'auto_generated': alert.auto_generated
        }
    
    def clear_alerts(self, blast_plan_id: Optional[str] = None) -> int:
        """Clear alerts for specific blast plan or all alerts."""
        if blast_plan_id:
            initial_count = len(self._active_alerts)
            self._active_alerts = [a for a in self._active_alerts if a.blast_plan_id != blast_plan_id]
            cleared_count = initial_count - len(self._active_alerts)
        else:
            cleared_count = len(self._active_alerts)
            self._active_alerts.clear()
        
        logger.info(f"Cleared {cleared_count} safety alerts")
        return cleared_count
    
    def get_alert_by_id(self, alert_id: str) -> Optional[SafetyAlert]:
        """Get specific alert by ID."""
        for alert in self._active_alerts:
            if alert.alert_id == alert_id:
                return alert
        return None