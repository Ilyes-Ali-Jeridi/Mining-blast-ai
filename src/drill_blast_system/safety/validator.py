"""
Core safety validator for drill-and-blast plans.
Implements requirements 4.1, 4.2, 4.6 for safety constraint validation.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
import math
from collections import defaultdict

from ..schemas.blast_record import BlastPlan, DrillHole
from ..physics_models.ppv import PPVModel
from .config import SafetyConfig, SafetyConfigManager
from .models import (
    SafetyCheck, SafetyViolation, SafetyValidationResult, SafetyStatus,
    SafetyCheckType, ViolationSeverity, SafetyValidationError
)

logger = logging.getLogger(__name__)


class SafetyValidator:
    """Core safety validator with configurable constraints."""
    
    def __init__(self, config_manager: Optional[SafetyConfigManager] = None):
        """Initialize safety validator with configuration manager."""
        self.config_manager = config_manager or SafetyConfigManager()
        self.ppv_model = PPVModel()
        
    def validate_plan(self, blast_plan: BlastPlan, site_id: Optional[int] = None) -> SafetyValidationResult:
        """
        Comprehensive safety validation of blast plan.
        
        Args:
            blast_plan: Complete blast plan to validate
            site_id: Optional site ID for site-specific configuration
            
        Returns:
            SafetyValidationResult with all checks and violations
        """
        try:
            # Load appropriate safety configuration
            config = self._get_safety_config(site_id)
            
            # Initialize validation result
            validation_timestamp = datetime.utcnow()
            safety_checks = []
            violations = []
            
            # Perform all safety checks
            safety_checks.extend(self._validate_charge_limits(blast_plan, config))
            safety_checks.extend(self._validate_delay_limits(blast_plan, config))
            safety_checks.extend(self._validate_ppv_limits(blast_plan, config))
            safety_checks.extend(self._validate_powder_factor(blast_plan, config))
            safety_checks.extend(self._validate_geometric_constraints(blast_plan, config))
            safety_checks.extend(self._validate_hole_specifications(blast_plan, config))
            
            # Collect violations from failed checks
            for check in safety_checks:
                if check.status == SafetyStatus.FAIL:
                    violation = self._create_violation_from_check(check, blast_plan)
                    violations.append(violation)
            
            # Determine overall validity
            is_valid = len([c for c in safety_checks if c.status == SafetyStatus.FAIL]) == 0
            
            # Create validation result
            result = SafetyValidationResult(
                validation_timestamp=validation_timestamp,
                is_valid=is_valid,
                safety_checks=safety_checks,
                violations=violations,
                safety_config_snapshot=config.to_dict()
            )
            
            logger.info(f"Safety validation completed: {len(safety_checks)} checks, "
                       f"{len(violations)} violations, valid={is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            raise SafetyValidationError(f"Validation process failed: {e}")
    
    def _get_safety_config(self, site_id: Optional[int]) -> SafetyConfig:
        """Get appropriate safety configuration for site."""
        if site_id:
            try:
                return self.config_manager.load_config(f"site_{site_id}")
            except Exception:
                logger.warning(f"Site-specific config for site {site_id} not found, using default")
        
        return self.config_manager.get_current_config()
    
    def _validate_charge_limits(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate per-hole charge limits."""
        checks = []
        
        for hole in blast_plan.holes:
            # Check per-hole charge limit
            check = SafetyCheck(
                check_name=f"Charge limit - Hole {hole.hole_id}",
                check_type=SafetyCheckType.CHARGE_PER_HOLE,
                status=SafetyStatus.PASS,
                limit_value=config.max_charge_per_hole,
                actual_value=hole.charge_kg,
                safety_margin=0.0,
                description=f"Charge in hole {hole.hole_id} within regulatory limits",
                units="kg"
            )
            
            if hole.charge_kg > config.max_charge_per_hole:
                check.status = SafetyStatus.FAIL
                check.description = f"Hole {hole.hole_id} exceeds maximum charge per hole limit"
            elif hole.charge_kg > config.max_charge_per_hole * 0.9:
                check.status = SafetyStatus.WARNING
                check.description = f"Hole {hole.hole_id} approaching maximum charge limit"
            
            checks.append(check)
            
            # Check explosive-specific limits
            explosive_limits = config.get_explosive_limits(hole.explosive_type)
            if explosive_limits:
                explosive_check = SafetyCheck(
                    check_name=f"Explosive limit - Hole {hole.hole_id}",
                    check_type=SafetyCheckType.REGULATORY_COMPLIANCE,
                    status=SafetyStatus.PASS,
                    limit_value=explosive_limits.max_charge_per_hole,
                    actual_value=hole.charge_kg,
                    safety_margin=0.0,
                    description=f"Explosive {hole.explosive_type} charge within limits",
                    units="kg"
                )
                
                if hole.charge_kg > explosive_limits.max_charge_per_hole:
                    explosive_check.status = SafetyStatus.FAIL
                    explosive_check.description = f"Hole {hole.hole_id} exceeds {hole.explosive_type} charge limit"
                
                checks.append(explosive_check)
        
        return checks
    
    def _validate_delay_limits(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate per-delay charge aggregation and limits."""
        checks = []
        
        # Group charges by delay
        delay_charges = defaultdict(float)
        delay_holes = defaultdict(list)
        
        for hole in blast_plan.holes:
            delay_charges[hole.delay_ms] += hole.charge_kg
            delay_holes[hole.delay_ms].append(hole.hole_id)
        
        # Check each delay
        for delay_ms, total_charge in delay_charges.items():
            check = SafetyCheck(
                check_name=f"Delay charge limit - Delay {delay_ms}ms",
                check_type=SafetyCheckType.CHARGE_PER_DELAY,
                status=SafetyStatus.PASS,
                limit_value=config.max_charge_per_delay,
                actual_value=total_charge,
                safety_margin=0.0,
                description=f"Total charge for delay {delay_ms}ms within limits",
                units="kg"
            )
            
            if total_charge > config.max_charge_per_delay:
                check.status = SafetyStatus.FAIL
                check.description = f"Delay {delay_ms}ms exceeds maximum charge per delay limit"
            elif total_charge > config.max_charge_per_delay * 0.9:
                check.status = SafetyStatus.WARNING
                check.description = f"Delay {delay_ms}ms approaching maximum charge limit"
            
            checks.append(check)
        
        # Check delay timing constraints
        if len(delay_charges) > 1:
            delays = sorted(delay_charges.keys())
            for i in range(1, len(delays)):
                interval = delays[i] - delays[i-1]
                
                check = SafetyCheck(
                    check_name=f"Delay interval - {delays[i-1]}ms to {delays[i]}ms",
                    check_type=SafetyCheckType.REGULATORY_COMPLIANCE,
                    status=SafetyStatus.PASS,
                    limit_value=config.min_delay_interval,
                    actual_value=interval,
                    safety_margin=0.0,
                    description=f"Delay interval within minimum requirements",
                    units="ms"
                )
                
                if interval < config.min_delay_interval:
                    check.status = SafetyStatus.FAIL
                    check.description = f"Delay interval {interval}ms below minimum {config.min_delay_interval}ms"
                
                checks.append(check)
        
        return checks
    
    def _validate_ppv_limits(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate PPV limits at sensitive receptors."""
        checks = []
        
        if not config.sensitive_receptors:
            logger.warning("No sensitive receptors configured for PPV validation")
            return checks
        
        # Group charges by delay for PPV calculation
        delay_charges = defaultdict(list)
        for hole in blast_plan.holes:
            delay_charges[hole.delay_ms].append({
                'charge': hole.charge_kg,
                'coordinates': (hole.coordinates.x, hole.coordinates.y, hole.coordinates.z)
            })
        
        # Check PPV at each receptor
        for receptor in config.sensitive_receptors:
            if not receptor.is_active:
                continue
                
            receptor_coords = (receptor.coordinates['x'], receptor.coordinates['y'], receptor.coordinates['z'])
            max_ppv = 0.0
            
            # Calculate PPV from each delay
            for delay_ms, charges in delay_charges.items():
                delay_ppv = 0.0
                
                for charge_info in charges:
                    distance = self._calculate_distance(charge_info['coordinates'], receptor_coords)
                    if distance > 0:
                        ppv = self.ppv_model.predict_ppv(charge_info['charge'], distance)
                        delay_ppv += ppv  # Simple superposition
                
                max_ppv = max(max_ppv, delay_ppv)
            
            # Create PPV check
            check = SafetyCheck(
                check_name=f"PPV limit - {receptor.name}",
                check_type=SafetyCheckType.PPV_LIMIT,
                status=SafetyStatus.PASS,
                limit_value=receptor.ppv_limit,
                actual_value=max_ppv,
                safety_margin=0.0,
                description=f"PPV at {receptor.name} within limits",
                units="mm/s"
            )
            
            if max_ppv > receptor.ppv_limit:
                check.status = SafetyStatus.FAIL
                check.description = f"PPV at {receptor.name} exceeds limit"
            elif max_ppv > receptor.ppv_limit * 0.9:
                check.status = SafetyStatus.WARNING
                check.description = f"PPV at {receptor.name} approaching limit"
            
            checks.append(check)
        
        return checks
    
    def _validate_powder_factor(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate powder factor range."""
        checks = []
        
        # Calculate powder factor from blast geometry
        total_explosive = blast_plan.explosive_summary.total_explosive
        rock_tonnage = blast_plan.blast_geometry.rock_tonnage
        
        if rock_tonnage > 0:
            powder_factor = total_explosive / rock_tonnage
            
            # Check minimum powder factor
            min_check = SafetyCheck(
                check_name="Minimum powder factor",
                check_type=SafetyCheckType.POWDER_FACTOR,
                status=SafetyStatus.PASS,
                limit_value=config.powder_factor_min,
                actual_value=powder_factor,
                safety_margin=0.0,
                description="Powder factor above minimum threshold",
                units="kg/t"
            )
            
            if powder_factor < config.powder_factor_min:
                min_check.status = SafetyStatus.FAIL
                min_check.description = "Powder factor below minimum - insufficient fragmentation expected"
            
            checks.append(min_check)
            
            # Check maximum powder factor
            max_check = SafetyCheck(
                check_name="Maximum powder factor",
                check_type=SafetyCheckType.POWDER_FACTOR,
                status=SafetyStatus.PASS,
                limit_value=config.powder_factor_max,
                actual_value=powder_factor,
                safety_margin=0.0,
                description="Powder factor below maximum threshold",
                units="kg/t"
            )
            
            if powder_factor > config.powder_factor_max:
                max_check.status = SafetyStatus.FAIL
                max_check.description = "Powder factor exceeds maximum - over-blasting risk"
            elif powder_factor > config.powder_factor_max * 0.9:
                max_check.status = SafetyStatus.WARNING
                max_check.description = "Powder factor approaching maximum"
            
            checks.append(max_check)
        
        return checks
    
    def _validate_geometric_constraints(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate burden, spacing, and geometric constraints."""
        checks = []
        
        for hole in blast_plan.holes:
            # Validate burden
            burden_check = SafetyCheck(
                check_name=f"Burden - Hole {hole.hole_id}",
                check_type=SafetyCheckType.BURDEN_SPACING,
                status=SafetyStatus.PASS,
                limit_value=config.min_burden,
                actual_value=hole.burden,
                safety_margin=0.0,
                description=f"Burden for hole {hole.hole_id} within limits",
                units="m"
            )
            
            if hole.burden < config.min_burden:
                burden_check.status = SafetyStatus.FAIL
                burden_check.description = f"Hole {hole.hole_id} burden below minimum"
            elif hole.burden > config.max_burden:
                burden_check.status = SafetyStatus.FAIL
                burden_check.description = f"Hole {hole.hole_id} burden exceeds maximum"
                burden_check.limit_value = config.max_burden
            
            checks.append(burden_check)
            
            # Validate spacing
            spacing_check = SafetyCheck(
                check_name=f"Spacing - Hole {hole.hole_id}",
                check_type=SafetyCheckType.BURDEN_SPACING,
                status=SafetyStatus.PASS,
                limit_value=config.min_spacing,
                actual_value=hole.spacing,
                safety_margin=0.0,
                description=f"Spacing for hole {hole.hole_id} within limits",
                units="m"
            )
            
            if hole.spacing < config.min_spacing:
                spacing_check.status = SafetyStatus.FAIL
                spacing_check.description = f"Hole {hole.hole_id} spacing below minimum"
            elif hole.spacing > config.max_spacing:
                spacing_check.status = SafetyStatus.FAIL
                spacing_check.description = f"Hole {hole.hole_id} spacing exceeds maximum"
                spacing_check.limit_value = config.max_spacing
            
            checks.append(spacing_check)
        
        return checks
    
    def _validate_hole_specifications(self, blast_plan: BlastPlan, config: SafetyConfig) -> List[SafetyCheck]:
        """Validate hole depth, stemming, and other specifications."""
        checks = []
        
        for hole in blast_plan.holes:
            # Validate hole depth
            depth_check = SafetyCheck(
                check_name=f"Hole depth - Hole {hole.hole_id}",
                check_type=SafetyCheckType.HOLE_DEPTH,
                status=SafetyStatus.PASS,
                limit_value=config.max_hole_depth,
                actual_value=hole.depth,
                safety_margin=0.0,
                description=f"Hole {hole.hole_id} depth within limits",
                units="m"
            )
            
            if hole.depth > config.max_hole_depth:
                depth_check.status = SafetyStatus.FAIL
                depth_check.description = f"Hole {hole.hole_id} exceeds maximum depth"
            
            checks.append(depth_check)
            
            # Validate stemming ratio
            stemming_ratio = hole.stemming_m / hole.depth if hole.depth > 0 else 0
            
            stemming_check = SafetyCheck(
                check_name=f"Stemming ratio - Hole {hole.hole_id}",
                check_type=SafetyCheckType.STEMMING_LENGTH,
                status=SafetyStatus.PASS,
                limit_value=config.min_stemming_ratio,
                actual_value=stemming_ratio,
                safety_margin=0.0,
                description=f"Stemming ratio for hole {hole.hole_id} adequate",
                units="ratio"
            )
            
            if stemming_ratio < config.min_stemming_ratio:
                stemming_check.status = SafetyStatus.FAIL
                stemming_check.description = f"Hole {hole.hole_id} insufficient stemming"
            
            checks.append(stemming_check)
        
        return checks
    
    def _calculate_distance(self, coord1: Tuple[float, float, float], 
                          coord2: Tuple[float, float, float]) -> float:
        """Calculate 3D Euclidean distance between coordinates."""
        dx = coord1[0] - coord2[0]
        dy = coord1[1] - coord2[1]
        dz = coord1[2] - coord2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _create_violation_from_check(self, check: SafetyCheck, blast_plan: BlastPlan) -> SafetyViolation:
        """Create safety violation from failed check."""
        # Determine severity based on check type and margin
        severity = ViolationSeverity.MEDIUM
        
        if check.check_type in [SafetyCheckType.CHARGE_PER_HOLE, SafetyCheckType.CHARGE_PER_DELAY, 
                               SafetyCheckType.PPV_LIMIT]:
            severity = ViolationSeverity.CRITICAL
        elif check.check_type == SafetyCheckType.POWDER_FACTOR:
            severity = ViolationSeverity.HIGH
        elif check.safety_margin < -0.5:  # Significantly over limit
            severity = ViolationSeverity.HIGH
        
        # Generate mitigation suggestion
        mitigation = self._generate_mitigation_suggestion(check, blast_plan)
        
        # Extract affected holes
        affected_holes = self._extract_affected_holes(check, blast_plan)
        
        return SafetyViolation(
            violation_type=check.check_type.value,
            severity=severity,
            description=check.description,
            suggested_mitigation=mitigation,
            affected_holes=affected_holes,
            check_details=check
        )
    
    def _generate_mitigation_suggestion(self, check: SafetyCheck, blast_plan: BlastPlan) -> str:
        """Generate specific mitigation suggestion for failed check."""
        if check.check_type == SafetyCheckType.CHARGE_PER_HOLE:
            return "Reduce charge in affected holes or split into multiple smaller holes"
        elif check.check_type == SafetyCheckType.CHARGE_PER_DELAY:
            return "Redistribute charges across additional delays or reduce individual hole charges"
        elif check.check_type == SafetyCheckType.PPV_LIMIT:
            return "Reduce charges, increase distance to receptors, or use additional delays"
        elif check.check_type == SafetyCheckType.POWDER_FACTOR:
            if check.actual_value < check.limit_value:
                return "Increase explosive charge or reduce rock tonnage"
            else:
                return "Reduce explosive charge or increase rock tonnage"
        elif check.check_type == SafetyCheckType.BURDEN_SPACING:
            return "Adjust hole pattern geometry to meet burden/spacing requirements"
        elif check.check_type == SafetyCheckType.STEMMING_LENGTH:
            return "Increase stemming length or reduce hole depth"
        else:
            return "Review and adjust blast parameters to meet safety requirements"
    
    def _extract_affected_holes(self, check: SafetyCheck, blast_plan: BlastPlan) -> Optional[List[str]]:
        """Extract hole IDs affected by the failed check."""
        # Extract hole ID from check name if present
        if "Hole " in check.check_name:
            hole_id = check.check_name.split("Hole ")[1].split(" ")[0].split("-")[0]
            return [hole_id]
        
        # For delay-based checks, find all holes in that delay
        if "Delay " in check.check_name and "ms" in check.check_name:
            try:
                delay_str = check.check_name.split("Delay ")[1].split("ms")[0]
                delay_ms = int(delay_str)
                affected_holes = [hole.hole_id for hole in blast_plan.holes if hole.delay_ms == delay_ms]
                return affected_holes if affected_holes else None
            except (ValueError, IndexError):
                pass
        
        return None