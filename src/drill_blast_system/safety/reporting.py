"""
Safety reporting system with detailed violation reporting and mitigation suggestions.
Implements requirements 4.3, 4.5, 4.6 for safety reporting and audit trails.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from enum import Enum

from .models import (
    SafetyValidationResult, SafetyViolation, SafetyCheck, SafetyStatus,
    ViolationSeverity, SafetyCheckType, SafetyReport
)
from .audit import SafetyAuditTrail, ValidationHistory

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Available report formats."""
    PDF = "pdf"
    JSON = "json"
    HTML = "html"
    CSV = "csv"


@dataclass
class SafetyMarginAnalysis:
    """Detailed safety margin analysis for a parameter."""
    parameter_name: str
    current_value: float
    limit_value: float
    safety_margin: float
    margin_percentage: float
    risk_level: str
    units: str
    recommendation: str


@dataclass
class ViolationReport:
    """Detailed violation report with specific margins and mitigation."""
    violation: SafetyViolation
    safety_margin: float
    margin_percentage: float
    risk_assessment: str
    detailed_mitigation: List[str]
    regulatory_reference: Optional[str] = None
    cost_impact: Optional[str] = None
    time_impact: Optional[str] = None


@dataclass
class SafetyStatusSummary:
    """Summary of overall safety status."""
    overall_status: str  # VALID, INVALID, WARNING
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    worst_safety_margin: float
    best_safety_margin: float
    compliance_score: float  # 0-100


class SafetyReportGenerator:
    """Generates comprehensive safety reports with detailed analysis."""
    
    def __init__(self, audit_trail: Optional[SafetyAuditTrail] = None):
        """Initialize report generator."""
        self.audit_trail = audit_trail or SafetyAuditTrail()
        
    def generate_detailed_safety_report(self, 
                                      validation_result: SafetyValidationResult,
                                      blast_plan_id: str,
                                      include_history: bool = True) -> SafetyReport:
        """
        Generate comprehensive safety report with detailed analysis.
        
        Args:
            validation_result: Safety validation result
            blast_plan_id: Blast plan identifier
            include_history: Include validation history
            
        Returns:
            Complete safety report
        """
        # Generate safety status summary
        status_summary = self._generate_status_summary(validation_result)
        
        # Generate detailed violation reports
        violation_reports = self._generate_violation_reports(validation_result)
        
        # Generate safety margin analysis
        margin_analysis = self._generate_margin_analysis(validation_result)
        
        # Generate mitigation recommendations
        mitigation_recommendations = self._generate_mitigation_recommendations(
            validation_result, violation_reports
        )
        
        # Generate regulatory compliance analysis
        regulatory_compliance = self._generate_regulatory_compliance(validation_result)
        
        # Get validation history if requested
        validation_history = None
        if include_history:
            history = self.audit_trail.get_validation_history(blast_plan_id)
            validation_history = self._format_validation_history(history)
        
        # Create blast plan summary
        blast_plan_summary = self._create_blast_plan_summary(validation_result)
        
        # Create comprehensive report
        report = SafetyReport(
            validation_result=validation_result,
            blast_plan_summary=blast_plan_summary,
            regulatory_compliance=regulatory_compliance,
            mitigation_recommendations=mitigation_recommendations
        )
        
        # Add extended report data
        report_data = {
            'status_summary': status_summary,
            'violation_reports': violation_reports,
            'margin_analysis': margin_analysis,
            'validation_history': validation_history,
            'compliance_analysis': regulatory_compliance,
            'executive_summary': report.generate_executive_summary(),
            'mitigation_plan': report.generate_mitigation_plan()
        }
        
        # Store detailed report data
        setattr(report, 'detailed_analysis', report_data)
        
        logger.info(f"Generated detailed safety report for blast plan {blast_plan_id}")
        return report
    
    def _generate_status_summary(self, validation_result: SafetyValidationResult) -> SafetyStatusSummary:
        """Generate overall safety status summary."""
        total_checks = len(validation_result.safety_checks)
        passed_checks = len(validation_result.passed_checks)
        failed_checks = len(validation_result.failed_checks)
        warning_checks = len(validation_result.warning_checks)
        
        # Count violations by severity
        violation_counts = {
            ViolationSeverity.CRITICAL: 0,
            ViolationSeverity.HIGH: 0,
            ViolationSeverity.MEDIUM: 0,
            ViolationSeverity.LOW: 0
        }
        
        for violation in validation_result.violations:
            violation_counts[violation.severity] += 1
        
        # Calculate safety margins
        margins = [check.safety_margin for check in validation_result.safety_checks 
                  if hasattr(check, 'safety_margin')]
        worst_margin = min(margins) if margins else 0.0
        best_margin = max(margins) if margins else 0.0
        
        # Calculate compliance score (0-100)
        if total_checks > 0:
            base_score = (passed_checks / total_checks) * 100
            # Penalize for violations
            penalty = (violation_counts[ViolationSeverity.CRITICAL] * 25 +
                      violation_counts[ViolationSeverity.HIGH] * 15 +
                      violation_counts[ViolationSeverity.MEDIUM] * 10 +
                      violation_counts[ViolationSeverity.LOW] * 5)
            compliance_score = max(0, base_score - penalty)
        else:
            compliance_score = 0.0
        
        # Determine overall status
        if failed_checks == 0:
            overall_status = "WARNING" if warning_checks > 0 else "VALID"
        else:
            overall_status = "INVALID"
        
        return SafetyStatusSummary(
            overall_status=overall_status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            critical_violations=violation_counts[ViolationSeverity.CRITICAL],
            high_violations=violation_counts[ViolationSeverity.HIGH],
            medium_violations=violation_counts[ViolationSeverity.MEDIUM],
            low_violations=violation_counts[ViolationSeverity.LOW],
            worst_safety_margin=worst_margin,
            best_safety_margin=best_margin,
            compliance_score=compliance_score
        )
    
    def _generate_violation_reports(self, 
                                  validation_result: SafetyValidationResult) -> List[ViolationReport]:
        """Generate detailed reports for each violation."""
        violation_reports = []
        
        for violation in validation_result.violations:
            # Calculate detailed safety margin
            safety_margin = 0.0
            margin_percentage = 0.0
            
            if violation.check_details:
                check = violation.check_details
                if check.limit_value > 0:
                    safety_margin = check.limit_value - check.actual_value
                    margin_percentage = (safety_margin / check.limit_value) * 100
            
            # Assess risk level
            risk_assessment = self._assess_violation_risk(violation, margin_percentage)
            
            # Generate detailed mitigation steps
            detailed_mitigation = self._generate_detailed_mitigation(violation)
            
            # Get regulatory reference
            regulatory_reference = self._get_regulatory_reference(violation)
            
            # Estimate impact
            cost_impact, time_impact = self._estimate_violation_impact(violation)
            
            violation_report = ViolationReport(
                violation=violation,
                safety_margin=safety_margin,
                margin_percentage=margin_percentage,
                risk_assessment=risk_assessment,
                detailed_mitigation=detailed_mitigation,
                regulatory_reference=regulatory_reference,
                cost_impact=cost_impact,
                time_impact=time_impact
            )
            
            violation_reports.append(violation_report)
        
        # Sort by severity and margin
        violation_reports.sort(key=lambda x: (
            x.violation.severity.value,
            x.margin_percentage
        ))
        
        return violation_reports
    
    def _generate_margin_analysis(self, 
                                validation_result: SafetyValidationResult) -> List[SafetyMarginAnalysis]:
        """Generate detailed safety margin analysis for all parameters."""
        margin_analyses = []
        
        for check in validation_result.safety_checks:
            if not hasattr(check, 'safety_margin'):
                continue
                
            # Calculate margin percentage
            margin_percentage = 0.0
            if check.limit_value > 0:
                margin_percentage = (check.safety_margin * 100)
            
            # Determine risk level
            if margin_percentage < -50:
                risk_level = "CRITICAL"
            elif margin_percentage < -20:
                risk_level = "HIGH"
            elif margin_percentage < 0:
                risk_level = "MEDIUM"
            elif margin_percentage < 20:
                risk_level = "LOW"
            else:
                risk_level = "SAFE"
            
            # Generate recommendation
            recommendation = self._generate_margin_recommendation(check, margin_percentage)
            
            analysis = SafetyMarginAnalysis(
                parameter_name=check.check_name,
                current_value=check.actual_value,
                limit_value=check.limit_value,
                safety_margin=check.safety_margin,
                margin_percentage=margin_percentage,
                risk_level=risk_level,
                units=check.units,
                recommendation=recommendation
            )
            
            margin_analyses.append(analysis)
        
        # Sort by risk level and margin
        risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "SAFE": 4}
        margin_analyses.sort(key=lambda x: (risk_order.get(x.risk_level, 5), x.margin_percentage))
        
        return margin_analyses
    
    def _generate_mitigation_recommendations(self, 
                                          validation_result: SafetyValidationResult,
                                          violation_reports: List[ViolationReport]) -> List[str]:
        """Generate prioritized mitigation recommendations."""
        recommendations = []
        
        # Critical violations first
        critical_violations = [vr for vr in violation_reports 
                             if vr.violation.severity == ViolationSeverity.CRITICAL]
        
        if critical_violations:
            recommendations.append("IMMEDIATE ACTION REQUIRED - Critical safety violations detected:")
            for vr in critical_violations:
                recommendations.extend([f"  • {step}" for step in vr.detailed_mitigation])
        
        # High priority violations
        high_violations = [vr for vr in violation_reports 
                          if vr.violation.severity == ViolationSeverity.HIGH]
        
        if high_violations:
            recommendations.append("HIGH PRIORITY - Address before plan execution:")
            for vr in high_violations:
                recommendations.extend([f"  • {step}" for step in vr.detailed_mitigation])
        
        # General recommendations
        if validation_result.warning_checks:
            recommendations.append("ADVISORY - Consider the following improvements:")
            for check in validation_result.warning_checks:
                if check.check_type == SafetyCheckType.PPV_LIMIT:
                    recommendations.append("  • Monitor PPV levels closely during execution")
                elif check.check_type == SafetyCheckType.POWDER_FACTOR:
                    recommendations.append("  • Review powder factor for optimal fragmentation")
                elif check.check_type == SafetyCheckType.CHARGE_PER_HOLE:
                    recommendations.append("  • Consider charge distribution optimization")
        
        # Add regulatory compliance recommendations
        if not validation_result.is_valid:
            recommendations.extend([
                "REGULATORY COMPLIANCE:",
                "  • Obtain engineering review before proceeding",
                "  • Document all safety considerations",
                "  • Ensure all permits and approvals are current"
            ])
        
        return recommendations
    
    def _generate_regulatory_compliance(self, 
                                     validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Generate regulatory compliance analysis."""
        compliance = {
            'overall_status': 'COMPLIANT' if validation_result.is_valid else 'NON_COMPLIANT',
            'framework_compliance': {},
            'permit_requirements': [],
            'documentation_requirements': [],
            'sign_off_requirements': []
        }
        
        # Check against common regulatory frameworks
        config = validation_result.safety_config_snapshot
        
        # Generic mining safety compliance
        framework_checks = {
            'charge_limits': self._check_charge_compliance(validation_result),
            'ppv_limits': self._check_ppv_compliance(validation_result),
            'geometric_constraints': self._check_geometric_compliance(validation_result),
            'environmental_limits': self._check_environmental_compliance(validation_result)
        }
        
        compliance['framework_compliance'] = framework_checks
        
        # Determine permit requirements
        if any(check.status == SafetyStatus.FAIL for check in validation_result.safety_checks):
            compliance['permit_requirements'].extend([
                "Engineering variance permit may be required",
                "Environmental impact assessment",
                "Regulatory authority notification"
            ])
        
        # Documentation requirements
        compliance['documentation_requirements'] = [
            "Safety validation report",
            "Engineer sign-off certification",
            "Blast plan technical drawings",
            "Risk assessment documentation"
        ]
        
        # Sign-off requirements
        if validation_result.has_critical_violations:
            compliance['sign_off_requirements'] = [
                "Senior engineer approval required",
                "Safety manager review",
                "Regulatory authority notification"
            ]
        else:
            compliance['sign_off_requirements'] = [
                "Qualified engineer certification"
            ]
        
        return compliance
    
    def _format_validation_history(self, history: ValidationHistory) -> Dict[str, Any]:
        """Format validation history for reporting."""
        if not history.validations:
            return {'total_validations': 0, 'history': []}
        
        formatted_history = []
        
        for entry in history.validations:
            formatted_entry = {
                'validation_id': entry.entry_id,
                'timestamp': entry.timestamp.isoformat(),
                'operation_type': entry.operation_type,
                'user_id': entry.user_id,
                'integrity_verified': entry.verify_integrity()
            }
            
            if entry.validation_result:
                result = entry.validation_result
                formatted_entry['validation_summary'] = {
                    'is_valid': result.get('is_valid', False),
                    'total_checks': len(result.get('safety_checks', [])),
                    'violations': len(result.get('violations', []))
                }
            
            formatted_history.append(formatted_entry)
        
        return {
            'total_validations': len(history.validations),
            'first_validation': history.validations[0].timestamp.isoformat(),
            'latest_validation': history.validations[-1].timestamp.isoformat(),
            'history': formatted_history
        }
    
    def _create_blast_plan_summary(self, validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Create blast plan summary from validation result."""
        config = validation_result.safety_config_snapshot
        
        return {
            'validation_id': validation_result.validation_id,
            'validation_timestamp': validation_result.validation_timestamp.isoformat(),
            'configuration_version': config.get('config_version', 'unknown'),
            'jurisdiction': config.get('jurisdiction', 'generic'),
            'regulatory_authority': config.get('regulatory_authority', 'unknown')
        }
    
    def _assess_violation_risk(self, violation: SafetyViolation, margin_percentage: float) -> str:
        """Assess risk level for violation."""
        if violation.severity == ViolationSeverity.CRITICAL:
            return "EXTREME - Immediate safety risk"
        elif violation.severity == ViolationSeverity.HIGH:
            if margin_percentage < -50:
                return "SEVERE - Significant safety concern"
            else:
                return "HIGH - Safety limits exceeded"
        elif violation.severity == ViolationSeverity.MEDIUM:
            return "MODERATE - Review recommended"
        else:
            return "LOW - Advisory only"
    
    def _generate_detailed_mitigation(self, violation: SafetyViolation) -> List[str]:
        """Generate detailed mitigation steps for violation."""
        base_mitigation = violation.suggested_mitigation
        detailed_steps = [base_mitigation]
        
        # Add specific steps based on violation type
        if violation.violation_type == SafetyCheckType.CHARGE_PER_HOLE.value:
            detailed_steps.extend([
                "Review hole diameter and depth specifications",
                "Consider using lower density explosives",
                "Split large holes into multiple smaller holes",
                "Verify explosive loading calculations"
            ])
        elif violation.violation_type == SafetyCheckType.PPV_LIMIT.value:
            detailed_steps.extend([
                "Increase distance between charges and receptors",
                "Implement additional delay timing",
                "Reduce charge weights in critical areas",
                "Install vibration monitoring equipment"
            ])
        elif violation.violation_type == SafetyCheckType.POWDER_FACTOR.value:
            detailed_steps.extend([
                "Recalculate rock tonnage and explosive requirements",
                "Review rock properties and fragmentation targets",
                "Adjust hole pattern geometry",
                "Consider alternative explosive types"
            ])
        
        # Add regulatory compliance steps
        detailed_steps.extend([
            "Document all changes and justifications",
            "Obtain required approvals before implementation",
            "Update safety documentation"
        ])
        
        return detailed_steps
    
    def _get_regulatory_reference(self, violation: SafetyViolation) -> Optional[str]:
        """Get regulatory reference for violation type."""
        references = {
            SafetyCheckType.CHARGE_PER_HOLE.value: "Mining Safety Regulation 4.2.1 - Maximum Explosive Charges",
            SafetyCheckType.PPV_LIMIT.value: "Environmental Protection Act Section 12 - Vibration Limits",
            SafetyCheckType.POWDER_FACTOR.value: "Mining Operations Standard 3.1 - Explosive Usage",
            SafetyCheckType.BURDEN_SPACING.value: "Technical Standard TS-001 - Blast Pattern Design"
        }
        
        return references.get(violation.violation_type)
    
    def _estimate_violation_impact(self, violation: SafetyViolation) -> Tuple[Optional[str], Optional[str]]:
        """Estimate cost and time impact of violation mitigation."""
        if violation.severity == ViolationSeverity.CRITICAL:
            cost_impact = "HIGH - Significant redesign required"
            time_impact = "2-5 days for plan revision"
        elif violation.severity == ViolationSeverity.HIGH:
            cost_impact = "MEDIUM - Pattern adjustments needed"
            time_impact = "1-2 days for modifications"
        elif violation.severity == ViolationSeverity.MEDIUM:
            cost_impact = "LOW - Minor adjustments"
            time_impact = "4-8 hours for review"
        else:
            cost_impact = "MINIMAL - Documentation only"
            time_impact = "1-2 hours for updates"
        
        return cost_impact, time_impact
    
    def _generate_margin_recommendation(self, check: SafetyCheck, margin_percentage: float) -> str:
        """Generate recommendation based on safety margin."""
        if margin_percentage < -50:
            return "CRITICAL: Immediate revision required - safety limit severely exceeded"
        elif margin_percentage < -20:
            return "HIGH: Significant adjustment needed - approaching dangerous levels"
        elif margin_percentage < 0:
            return "MEDIUM: Parameter exceeds limit - review and adjust"
        elif margin_percentage < 20:
            return "LOW: Close to limit - monitor during execution"
        else:
            return "SAFE: Parameter well within acceptable range"
    
    def _check_charge_compliance(self, validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Check compliance with charge limit regulations."""
        charge_checks = [c for c in validation_result.safety_checks 
                        if c.check_type in [SafetyCheckType.CHARGE_PER_HOLE, SafetyCheckType.CHARGE_PER_DELAY]]
        
        failed_charge_checks = [c for c in charge_checks if c.status == SafetyStatus.FAIL]
        
        return {
            'status': 'COMPLIANT' if not failed_charge_checks else 'NON_COMPLIANT',
            'total_checks': len(charge_checks),
            'failed_checks': len(failed_charge_checks),
            'details': [c.description for c in failed_charge_checks]
        }
    
    def _check_ppv_compliance(self, validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Check compliance with PPV regulations."""
        ppv_checks = [c for c in validation_result.safety_checks 
                     if c.check_type == SafetyCheckType.PPV_LIMIT]
        
        failed_ppv_checks = [c for c in ppv_checks if c.status == SafetyStatus.FAIL]
        
        return {
            'status': 'COMPLIANT' if not failed_ppv_checks else 'NON_COMPLIANT',
            'total_checks': len(ppv_checks),
            'failed_checks': len(failed_ppv_checks),
            'details': [c.description for c in failed_ppv_checks]
        }
    
    def _check_geometric_compliance(self, validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Check compliance with geometric constraints."""
        geometric_checks = [c for c in validation_result.safety_checks 
                           if c.check_type == SafetyCheckType.BURDEN_SPACING]
        
        failed_geometric_checks = [c for c in geometric_checks if c.status == SafetyStatus.FAIL]
        
        return {
            'status': 'COMPLIANT' if not failed_geometric_checks else 'NON_COMPLIANT',
            'total_checks': len(geometric_checks),
            'failed_checks': len(failed_geometric_checks),
            'details': [c.description for c in failed_geometric_checks]
        }
    
    def _check_environmental_compliance(self, validation_result: SafetyValidationResult) -> Dict[str, Any]:
        """Check compliance with environmental regulations."""
        # For now, assume environmental compliance based on PPV and other limits
        environmental_violations = [v for v in validation_result.violations 
                                  if v.violation_type in [SafetyCheckType.PPV_LIMIT.value]]
        
        return {
            'status': 'COMPLIANT' if not environmental_violations else 'NON_COMPLIANT',
            'violations': len(environmental_violations),
            'details': [v.description for v in environmental_violations]
        }
    
    def export_report(self, report: SafetyReport, format: ReportFormat, 
                     output_path: Path) -> None:
        """Export safety report in specified format."""
        if format == ReportFormat.JSON:
            self._export_json_report(report, output_path)
        elif format == ReportFormat.HTML:
            self._export_html_report(report, output_path)
        elif format == ReportFormat.CSV:
            self._export_csv_report(report, output_path)
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def _export_json_report(self, report: SafetyReport, output_path: Path) -> None:
        """Export report as JSON."""
        report_data = {
            'validation_result': report.validation_result.to_dict(),
            'blast_plan_summary': report.blast_plan_summary,
            'regulatory_compliance': report.regulatory_compliance,
            'mitigation_recommendations': report.mitigation_recommendations,
            'executive_summary': report.generate_executive_summary(),
            'report_generated_at': report.report_generated_at.isoformat()
        }
        
        if hasattr(report, 'detailed_analysis'):
            report_data['detailed_analysis'] = report.detailed_analysis
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"Exported JSON safety report to {output_path}")
    
    def _export_html_report(self, report: SafetyReport, output_path: Path) -> None:
        """Export report as HTML."""
        # Basic HTML template - in production, use proper templating
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Safety Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 10px; }}
                .violation {{ background-color: #ffe6e6; padding: 10px; margin: 5px 0; }}
                .pass {{ background-color: #e6ffe6; padding: 10px; margin: 5px 0; }}
                .warning {{ background-color: #fff3cd; padding: 10px; margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Safety Validation Report</h1>
                <p>Generated: {report.report_generated_at}</p>
            </div>
            
            <h2>Executive Summary</h2>
            <pre>{report.generate_executive_summary()}</pre>
            
            <h2>Validation Results</h2>
            <p>Valid: {report.validation_result.is_valid}</p>
            <p>Total Checks: {len(report.validation_result.safety_checks)}</p>
            <p>Violations: {len(report.validation_result.violations)}</p>
            
            <h2>Mitigation Recommendations</h2>
            <ul>
        """
        
        for recommendation in report.mitigation_recommendations:
            html_content += f"<li>{recommendation}</li>"
        
        html_content += """
            </ul>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Exported HTML safety report to {output_path}")
    
    def _export_csv_report(self, report: SafetyReport, output_path: Path) -> None:
        """Export report as CSV."""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['Check Name', 'Type', 'Status', 'Limit', 'Actual', 'Margin', 'Units', 'Description'])
            
            # Safety checks
            for check in report.validation_result.safety_checks:
                writer.writerow([
                    check.check_name,
                    check.check_type.value,
                    check.status.value,
                    check.limit_value,
                    check.actual_value,
                    getattr(check, 'safety_margin', 0.0),
                    check.units,
                    check.description
                ])
        
        logger.info(f"Exported CSV safety report to {output_path}")