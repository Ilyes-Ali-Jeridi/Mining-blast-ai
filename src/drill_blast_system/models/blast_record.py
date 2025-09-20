"""
BlastRecord model for storing blast plans and results.
Implements requirement 1.8: Historical blast plans and results storage with audit trails.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, JSON, Text, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from ..core.database import BaseModel


class BlastStatus(str, Enum):
    """Blast record status enumeration."""
    DRAFT = "draft"                    # Plan created but not finalized
    PENDING_REVIEW = "pending_review"  # Awaiting engineer review
    APPROVED = "approved"              # Engineer approved, ready for execution
    EXECUTED = "executed"              # Blast has been executed
    MEASURED = "measured"              # Post-blast measurements completed
    ARCHIVED = "archived"              # Archived for historical reference


class BlastRecord(BaseModel):
    """
    Historical blast plans and results storage.
    
    Stores complete blast plans with:
    - Drill hole specifications and patterns
    - Predicted fragmentation and PPV results
    - Safety validation results and engineer sign-off
    - Post-blast measurements and actual results
    - Optimization parameters and solver results
    """
    __tablename__ = "blast_records"
    
    # Foreign key to site
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Basic blast information
    blast_name = Column(String(200), nullable=False, index=True)
    blast_description = Column(Text, nullable=True)
    blast_status = Column(SQLEnum(BlastStatus), default=BlastStatus.DRAFT, nullable=False, index=True)
    
    # Blast execution information
    planned_execution_date = Column(DateTime, nullable=True)
    actual_execution_date = Column(DateTime, nullable=True)
    blast_operator = Column(String(100), nullable=True)
    
    # Complete blast plan data
    plan_data = Column(JSON, nullable=False)
    """
    Blast plan structure:
    {
        "holes": [
            {
                "hole_id": str,
                "coordinates": {"x": float, "y": float, "z": float},
                "depth": float,                    # meters
                "diameter": float,                 # mm
                "charge_kg": float,                # kg of explosive
                "stemming_m": float,               # meters of stemming
                "delay_ms": int,                   # delay time in milliseconds
                "explosive_type": str,             # explosive name from catalog
                "drill_rig": str,                  # drill rig used
                "collar_elevation": float,         # meters above sea level
                "toe_elevation": float,            # meters above sea level
                "burden": float,                   # meters to free face
                "spacing": float,                  # meters to adjacent holes
                "subdrill": float,                 # meters below bench floor
                "hole_angle": float,               # degrees from vertical
                "hole_azimuth": float              # degrees from north
            }, ...
        ],
        "blast_geometry": {
            "total_holes": int,
            "total_depth": float,              # meters
            "blast_area": float,               # m²
            "blast_volume": float,             # m³
            "rock_tonnage": float,             # tonnes
            "average_burden": float,           # meters
            "average_spacing": float,          # meters
            "hole_pattern": str                # rectangular, triangular, etc.
        },
        "explosive_summary": {
            "total_explosive": float,          # kg
            "powder_factor_kg_t": float,       # kg/tonne
            "powder_factor_kg_m3": float,      # kg/m³
            "explosive_types_used": [str],
            "total_cost": float,               # $ (if cost data available)
            "max_charge_per_hole": float,      # kg
            "max_charge_per_delay": float      # kg
        }
    }
    """
    
    # Predicted results from physics models
    predicted_results = Column(JSON, nullable=False)
    """
    Predicted results structure:
    {
        "fragmentation": {
            "mean_fragment_size": float,       # mm
            "p10": float,                      # mm (10% passing)
            "p50": float,                      # mm (50% passing)
            "p80": float,                      # mm (80% passing)
            "uniformity_index": float,         # Rosin-Rammler n parameter
            "characteristic_size": float,      # mm (Rosin-Rammler Xc)
            "distribution_type": str,          # rosin_rammler, swebrec, etc.
            "sieve_analysis": {                # Mass fractions for standard sieves
                "size_mm": [float],            # Sieve sizes
                "passing_percent": [float]     # Percent passing each sieve
            }
        },
        "ppv_predictions": {
            "receptor_predictions": [
                {
                    "receptor_name": str,
                    "coordinates": {"x": float, "y": float, "z": float},
                    "predicted_ppv": float,    # mm/s
                    "distance_to_blast": float, # meters
                    "dominant_frequency": float, # Hz (if predicted)
                    "safety_margin": float     # ratio to limit
                }, ...
            ],
            "max_predicted_ppv": float,        # mm/s
            "ppv_model_parameters": {
                "k": float,
                "a": float, 
                "b": float
            }
        },
        "model_metadata": {
            "physics_model_version": str,
            "kuz_ram_parameters": {
                "rock_factor_a": float,
                "uniformity_index": float
            },
            "prediction_timestamp": str,       # ISO format
            "model_confidence": float          # 0-1 if available
        }
    }
    """
    
    # Measured results (populated after blast execution)
    measured_results = Column(JSON, nullable=True)
    """
    Measured results structure:
    {
        "fragmentation_measurements": [
            {
                "measurement_id": str,
                "measurement_method": str,     # image_analysis, sieving, etc.
                "measurement_date": str,       # ISO format
                "measured_p10": float,         # mm
                "measured_p50": float,         # mm  
                "measured_p80": float,         # mm
                "measurement_quality": float,  # 0-1 confidence score
                "image_paths": [str],          # Paths to analysis images
                "notes": str
            }, ...
        ],
        "ppv_measurements": [
            {
                "sensor_id": str,
                "sensor_location": {"x": float, "y": float, "z": float},
                "measured_ppv": float,         # mm/s
                "dominant_frequency": float,   # Hz
                "measurement_timestamp": str,  # ISO format
                "sensor_type": str,            # geophone, accelerometer, etc.
                "data_quality": float          # 0-1 confidence score
            }, ...
        ],
        "blast_performance": {
            "fragmentation_accuracy": float,   # Predicted vs measured P80 error
            "ppv_accuracy": float,             # Predicted vs measured PPV error
            "overall_success_rating": float,   # 0-1 subjective rating
            "lessons_learned": str,
            "recommendations": str
        }
    }
    """
    
    # Safety validation results
    safety_validation = Column(JSON, nullable=False)
    """
    Safety validation structure:
    {
        "validation_timestamp": str,           # ISO format
        "is_valid": bool,                      # Overall safety status
        "safety_checks": [
            {
                "check_name": str,
                "check_type": str,             # charge_limit, ppv_limit, etc.
                "status": str,                 # PASS, FAIL, WARNING
                "limit_value": float,
                "actual_value": float,
                "safety_margin": float,        # (limit - actual) / limit
                "description": str
            }, ...
        ],
        "violations": [                        # Only populated if is_valid=False
            {
                "violation_type": str,
                "severity": str,               # CRITICAL, HIGH, MEDIUM, LOW
                "description": str,
                "suggested_mitigation": str,
                "affected_holes": [str]        # hole_ids if applicable
            }, ...
        ],
        "safety_config_used": {                # Snapshot of safety config at validation
            "max_charge_per_hole": float,
            "max_charge_per_delay": float,
            "ppv_limits": dict,
            "config_version": str
        }
    }
    """
    
    # Engineer sign-off information
    engineer_signoff = Column(JSON, nullable=True)
    """
    Engineer sign-off structure:
    {
        "engineer_name": str,
        "engineer_id": str,                    # Employee ID or license number
        "signoff_timestamp": str,              # ISO format
        "certification_statement": str,        # Legal certification text
        "digital_signature": str,              # Hash or digital signature
        "review_notes": str,                   # Engineer's review comments
        "conditions": [str],                   # Any conditions or requirements
        "is_valid": bool,                      # Sign-off validity
        "expiry_date": str                     # ISO format (if applicable)
    }
    """
    
    # Optimization metadata
    optimization_metadata = Column(JSON, nullable=True)
    """
    Optimization metadata structure:
    {
        "optimization_timestamp": str,         # ISO format
        "algorithms_used": [str],              # cp_sat, scipy, genetic, etc.
        "optimization_objectives": {
            "target_p80": float,
            "weight_fragmentation": float,
            "weight_cost": float,
            "weight_ppv": float
        },
        "solver_results": [
            {
                "algorithm": str,
                "runtime_seconds": float,
                "iterations": int,
                "final_objective": float,
                "convergence_status": str,     # converged, timeout, failed
                "solution_rank": int           # 1 = best solution
            }, ...
        ],
        "optimization_seed": int,              # For reproducibility
        "parameter_bounds": dict,              # Constraint ranges used
        "solution_quality_metrics": {
            "objective_improvement": float,    # vs initial guess
            "constraint_satisfaction": float,  # 0-1 score
            "solution_diversity": float        # If multiple solutions
        }
    }
    """
    
    # Version control and audit
    plan_version = Column(Integer, default=1, nullable=False)
    parent_blast_id = Column(Integer, ForeignKey("blast_records.id"), nullable=True)  # For plan revisions
    is_template = Column(Boolean, default=False, nullable=False)  # Can be used as template
    
    # Relationships
    site = relationship("Site", back_populates="blast_records")
    measurement_data = relationship("MeasurementData", back_populates="blast_record", cascade="all, delete-orphan")
    child_blasts = relationship("BlastRecord", backref="parent_blast", remote_side="BlastRecord.id")
    
    @hybrid_property
    def total_holes(self) -> int:
        """Get total number of holes in the blast."""
        if self.plan_data and 'holes' in self.plan_data:
            return len(self.plan_data['holes'])
        return 0
    
    @hybrid_property
    def total_explosive(self) -> float:
        """Get total explosive weight in kg."""
        if self.plan_data and 'explosive_summary' in self.plan_data:
            return self.plan_data['explosive_summary'].get('total_explosive', 0.0)
        return 0.0
    
    @hybrid_property
    def powder_factor(self) -> Optional[float]:
        """Get powder factor in kg/t."""
        if self.plan_data and 'explosive_summary' in self.plan_data:
            return self.plan_data['explosive_summary'].get('powder_factor_kg_t')
        return None
    
    @hybrid_property
    def predicted_p80(self) -> Optional[float]:
        """Get predicted P80 fragment size in mm."""
        if self.predicted_results and 'fragmentation' in self.predicted_results:
            return self.predicted_results['fragmentation'].get('p80')
        return None
    
    @hybrid_property
    def measured_p80(self) -> Optional[float]:
        """Get measured P80 fragment size in mm (if available)."""
        if not self.measured_results or 'fragmentation_measurements' not in self.measured_results:
            return None
        
        measurements = self.measured_results['fragmentation_measurements']
        if measurements:
            # Return the most recent or highest quality measurement
            best_measurement = max(measurements, key=lambda m: m.get('measurement_quality', 0))
            return best_measurement.get('measured_p80')
        return None
    
    @hybrid_property
    def is_signed_off(self) -> bool:
        """Check if blast has valid engineer sign-off."""
        return (self.engineer_signoff is not None and 
                self.engineer_signoff.get('is_valid', False))
    
    @hybrid_property
    def safety_status(self) -> str:
        """Get current safety validation status."""
        if not self.safety_validation:
            return "NOT_VALIDATED"
        return "VALID" if self.safety_validation.get('is_valid', False) else "INVALID"
    
    def get_holes_by_delay(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Group holes by delay timing.
        
        Returns:
            Dict mapping delay_ms to list of holes
        """
        if not self.plan_data or 'holes' not in self.plan_data:
            return {}
        
        holes_by_delay = {}
        for hole in self.plan_data['holes']:
            delay = hole.get('delay_ms', 0)
            if delay not in holes_by_delay:
                holes_by_delay[delay] = []
            holes_by_delay[delay].append(hole)
        
        return holes_by_delay
    
    def get_charge_by_delay(self) -> Dict[int, float]:
        """
        Calculate total charge per delay.
        
        Returns:
            Dict mapping delay_ms to total charge in kg
        """
        holes_by_delay = self.get_holes_by_delay()
        charge_by_delay = {}
        
        for delay, holes in holes_by_delay.items():
            total_charge = sum(hole.get('charge_kg', 0) for hole in holes)
            charge_by_delay[delay] = total_charge
        
        return charge_by_delay
    
    def get_safety_violations(self) -> List[Dict[str, Any]]:
        """
        Get list of safety violations.
        
        Returns:
            List of violation dictionaries
        """
        if not self.safety_validation:
            return []
        return self.safety_validation.get('violations', [])
    
    def calculate_fragmentation_accuracy(self) -> Optional[float]:
        """
        Calculate fragmentation prediction accuracy if measured data available.
        
        Returns:
            Accuracy as percentage error (None if no measured data)
        """
        predicted = self.predicted_p80
        measured = self.measured_p80
        
        if predicted is None or measured is None:
            return None
        
        # Calculate percentage error
        error = abs(predicted - measured) / measured * 100
        return error
    
    def can_be_exported(self) -> tuple[bool, List[str]]:
        """
        Check if blast plan can be exported.
        
        Returns:
            Tuple of (can_export, list_of_blocking_reasons)
        """
        blocking_reasons = []
        
        # Check safety validation
        if self.safety_status != "VALID":
            blocking_reasons.append("Safety validation failed or not completed")
        
        # Check engineer sign-off
        if not self.is_signed_off:
            blocking_reasons.append("Engineer sign-off required")
        
        # Check blast status
        if self.blast_status == BlastStatus.DRAFT:
            blocking_reasons.append("Blast is still in draft status")
        
        # Check plan completeness
        if not self.plan_data or 'holes' not in self.plan_data or not self.plan_data['holes']:
            blocking_reasons.append("No drill holes defined in plan")
        
        return len(blocking_reasons) == 0, blocking_reasons
    
    def create_revision(self, new_plan_data: Dict[str, Any], revised_by: str) -> 'BlastRecord':
        """
        Create a new revision of this blast record.
        
        Args:
            new_plan_data: Updated plan data
            revised_by: User creating the revision
            
        Returns:
            New BlastRecord instance (not yet saved to database)
        """
        # Create new blast record as revision
        revision = BlastRecord(
            site_id=self.site_id,
            blast_name=f"{self.blast_name} (Rev {self.plan_version + 1})",
            blast_description=f"Revision of {self.blast_name}. {self.blast_description or ''}",
            blast_status=BlastStatus.DRAFT,
            plan_data=new_plan_data,
            predicted_results={},  # Will be recalculated
            safety_validation={},  # Will be revalidated
            engineer_signoff=None,  # Requires new sign-off
            optimization_metadata=None,  # Will be regenerated
            plan_version=self.plan_version + 1,
            parent_blast_id=self.id,
            is_template=False
        )
        
        return revision
    
    def __repr__(self) -> str:
        """String representation of the blast record."""
        return f"<BlastRecord(id={self.id}, name='{self.blast_name}', status='{self.blast_status}', holes={self.total_holes})>"