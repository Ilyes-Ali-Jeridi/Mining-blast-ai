"""
Safety validation data models and enums.
Implements requirements 4.1, 4.2, 4.6 for safety constraint definitions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class SafetyCheckType(str, Enum):
    """Types of safety checks performed."""
    CHARGE_PER_HOLE = "charge_per_hole"
    CHARGE_PER_DELAY = "charge_per_delay"
    PPV_LIMIT = "ppv_limit"
    POWDER_FACTOR = "powder_factor"
    BURDEN_SPACING = "burden_spacing"
    HOLE_DEPTH = "hole_depth"
    STEMMING_LENGTH = "stemming_length"
    REGULATORY_COMPLIANCE = "regulatory_compliance"


class SafetyStatus(str, Enum):
    """Safety validation status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class ViolationSeverity(str, Enum):
    """Safety violation severity levels."""
    CRITICAL = "CRITICAL"  # Plan cannot be executed
    HIGH = "HIGH"         # Requires immediate attention
    MEDIUM = "MEDIUM"     # Should be addressed
    LOW = "LOW"          # Advisory only


@dataclass
class SafetyCheck:
    """Individual safety check result."""
    check_name: str
    check_type: SafetyCheckType
    status: SafetyStatus
    limit_value: float
    actual_value: float
    safety_margin: float
    description: str
    units: str = ""
    tolerance: float = 0.0
    
    def __post_init__(self):
        """Calculate safety margin after initialization."""
        if self.limit_value > 0:
            self.safety_margin = (self.limit_value - self.actual_value) / self.limit_value
        else:
            self.safety_margin = 0.0


@dataclass
class SafetyViolation:
    """Safety constraint violation."""
    violation_type: str
    severity: ViolationSeverity
    description: str
    suggested_mitigation: str
    affected_holes: Optional[List[str]] = None
    affected_delays: Optional[List[int]] = None
    check_details: Optional[SafetyCheck] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'violation_type': self.violation_type,
            'severity': self.severity.value,
            'description': self.description,
            'suggested_mitigation': self.suggested_mitigation,
            'affected_holes': self.affected_holes,
            'affected_delays': self.affected_delays,
            'check_details': self.check_details.__dict__ if self.check_details else None
        }


@dataclass
class SafetyValidationResult:
    """Complete safety validation result."""
    validation_timestamp: datetime
    is_valid: bool
    safety_checks: List[SafetyCheck]
    violations: List[SafetyViolation]
    safety_config_snapshot: Dict[str, Any]
    validation_id: str = ""
    
    def __post_init__(self):
        """Generate validation ID if not provided."""
        if not self.validation_id:
            self.validation_id = f"safety_{self.validation_timestamp.strftime('%Y%m%d_%H%M%S')}"
    
    @property
    def critical_violations(self) -> List[SafetyViolation]:
        """Get critical violations that prevent plan execution."""
        return [v for v in self.violations if v.severity == ViolationSeverity.CRITICAL]
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations."""
        return len(self.critical_violations) > 0
    
    @property
    def passed_checks(self) -> List[SafetyCheck]:
        """Get all passed safety checks."""
        return [c for c in self.safety_checks if c.status == SafetyStatus.PASS]
    
    @property
    def failed_checks(self) -> List[SafetyCheck]:
        """Get all failed safety checks."""
        return [c for c in self.safety_checks if c.status == SafetyStatus.FAIL]
    
    @property
    def warning_checks(self) -> List[SafetyCheck]:
        """Get all warning safety checks."""
        return [c for c in self.safety_checks if c.status == SafetyStatus.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'validation_id': self.validation_id,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'is_valid': self.is_valid,
            'safety_checks': [check.__dict__ for check in self.safety_checks],
            'violations': [violation.to_dict() for violation in self.violations],
            'safety_config_snapshot': self.safety_config_snapshot,
            'summary': {
                'total_checks': len(self.safety_checks),
                'passed_checks': len(self.passed_checks),
                'failed_checks': len(self.failed_checks),
                'warning_checks': len(self.warning_checks),
                'total_violations': len(self.violations),
                'critical_violations': len(self.critical_violations)
            }
        }


@dataclass
class SafetyReport:
    """Comprehensive safety report for documentation."""
    validation_result: SafetyValidationResult
    blast_plan_summary: Dict[str, Any]
    regulatory_compliance: Dict[str, Any]
    mitigation_recommendations: List[str]
    sign_off_required: bool = True
    report_generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary of safety status."""
        result = self.validation_result
        
        if result.is_valid:
            summary = f"SAFETY VALIDATION: PASSED\n"
            summary += f"All {len(result.safety_checks)} safety checks completed successfully.\n"
        else:
            summary = f"SAFETY VALIDATION: FAILED\n"
            summary += f"{len(result.failed_checks)} of {len(result.safety_checks)} checks failed.\n"
            summary += f"{len(result.critical_violations)} critical violations require immediate attention.\n"
        
        summary += f"\nValidation performed: {result.validation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        summary += f"Validation ID: {result.validation_id}\n"
        
        return summary
    
    def generate_mitigation_plan(self) -> List[str]:
        """Generate specific mitigation actions for violations."""
        mitigations = []
        
        for violation in self.validation_result.violations:
            if violation.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]:
                mitigations.append(f"[{violation.severity.value}] {violation.suggested_mitigation}")
        
        return mitigations


class SafetyConfigValidationError(Exception):
    """Exception raised when safety configuration is invalid."""
    pass


class SafetyValidationError(Exception):
    """Exception raised during safety validation process."""
    pass