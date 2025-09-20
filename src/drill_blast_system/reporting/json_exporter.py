"""
JSON export functionality for blast plan data.
Implements requirement 7.2: JSON export with full plan structure.
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class JSONExporter:
    """Exports blast plan data to JSON format."""
    
    def __init__(self):
        """Initialize JSON exporter."""
        pass
    
    def export_complete_blast_plan(
        self,
        blast_record: BlastRecord,
        include_safety_report: bool = True,
        include_hole_details: bool = True,
        include_predictions: bool = True,
        include_measurements: bool = False,
        include_metadata: bool = True
    ) -> bytes:
        """
        Export complete blast plan to JSON format.
        
        Args:
            blast_record: Blast record to export
            include_safety_report: Include safety validation report
            include_hole_details: Include detailed hole information
            include_predictions: Include prediction results
            include_measurements: Include measurement data if available
            include_metadata: Include metadata and audit information
            
        Returns:
            JSON content as bytes
        """
        try:
            export_data = {
                "export_metadata": {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "export_version": "1.0",
                    "exporter": "drill_blast_system",
                    "format": "json"
                },
                "blast_record": self._build_blast_record_data(
                    blast_record, include_safety_report, include_hole_details,
                    include_predictions, include_measurements, include_metadata
                )
            }
            
            content = json.dumps(export_data, indent=2, default=self._json_serializer).encode('utf-8')
            
            logger.info(
                "Complete blast plan exported to JSON",
                blast_id=blast_record.id,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export blast plan to JSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_hole_data_only(
        self,
        blast_record: BlastRecord,
        include_predictions: bool = True
    ) -> bytes:
        """
        Export only hole data to JSON format.
        
        Args:
            blast_record: Blast record to export
            include_predictions: Include prediction results
            
        Returns:
            JSON content as bytes
        """
        try:
            export_data = {
                "export_metadata": {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "export_type": "hole_data_only",
                    "blast_id": blast_record.id,
                    "blast_name": blast_record.blast_name
                },
                "holes": []
            }
            
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                for hole in blast_record.plan_data['holes']:
                    hole_data = self._build_hole_data(hole, blast_record, include_predictions)
                    export_data["holes"].append(hole_data)
            
            content = json.dumps(export_data, indent=2, default=self._json_serializer).encode('utf-8')
            
            logger.info(
                "Hole data exported to JSON",
                blast_id=blast_record.id,
                hole_count=len(export_data["holes"]),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export hole data to JSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_safety_validation_only(
        self,
        blast_record: BlastRecord
    ) -> bytes:
        """
        Export only safety validation data to JSON format.
        
        Args:
            blast_record: Blast record to export
            
        Returns:
            JSON content as bytes
        """
        try:
            export_data = {
                "export_metadata": {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "export_type": "safety_validation_only",
                    "blast_id": blast_record.id,
                    "blast_name": blast_record.blast_name
                },
                "safety_validation": blast_record.safety_validation or {},
                "safety_summary": {
                    "overall_status": blast_record.safety_status,
                    "is_signed_off": blast_record.is_signed_off,
                    "can_be_exported": blast_record.can_be_exported()[0],
                    "blocking_reasons": blast_record.can_be_exported()[1]
                }
            }
            
            content = json.dumps(export_data, indent=2, default=self._json_serializer).encode('utf-8')
            
            logger.info(
                "Safety validation exported to JSON",
                blast_id=blast_record.id,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export safety validation to JSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_multiple_blast_plans(
        self,
        blast_records: List[BlastRecord],
        include_full_details: bool = False
    ) -> bytes:
        """
        Export multiple blast plans to JSON format.
        
        Args:
            blast_records: List of blast records to export
            include_full_details: Include full details or summary only
            
        Returns:
            JSON content as bytes
        """
        try:
            export_data = {
                "export_metadata": {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "export_type": "multiple_blast_plans",
                    "blast_count": len(blast_records),
                    "include_full_details": include_full_details
                },
                "blast_plans": []
            }
            
            for blast_record in blast_records:
                if include_full_details:
                    blast_data = self._build_blast_record_data(
                        blast_record, True, True, True, False, True
                    )
                else:
                    blast_data = self._build_blast_summary_data(blast_record)
                
                export_data["blast_plans"].append(blast_data)
            
            content = json.dumps(export_data, indent=2, default=self._json_serializer).encode('utf-8')
            
            logger.info(
                "Multiple blast plans exported to JSON",
                blast_count=len(blast_records),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export multiple blast plans to JSON",
                blast_count=len(blast_records),
                error=str(e)
            )
            raise
    
    def _build_blast_record_data(
        self,
        blast_record: BlastRecord,
        include_safety_report: bool,
        include_hole_details: bool,
        include_predictions: bool,
        include_measurements: bool,
        include_metadata: bool
    ) -> Dict[str, Any]:
        """Build complete blast record data structure."""
        data = {
            "basic_info": {
                "id": blast_record.id,
                "blast_name": blast_record.blast_name,
                "blast_description": blast_record.blast_description,
                "site_id": blast_record.site_id,
                "blast_status": blast_record.blast_status.value,
                "blast_operator": blast_record.blast_operator,
                "planned_execution_date": blast_record.planned_execution_date.isoformat() if blast_record.planned_execution_date else None,
                "actual_execution_date": blast_record.actual_execution_date.isoformat() if blast_record.actual_execution_date else None,
                "is_template": blast_record.is_template,
                "plan_version": blast_record.plan_version,
                "parent_blast_id": blast_record.parent_blast_id
            },
            "computed_properties": {
                "total_holes": blast_record.total_holes,
                "total_explosive": blast_record.total_explosive,
                "powder_factor": blast_record.powder_factor,
                "predicted_p80": blast_record.predicted_p80,
                "measured_p80": blast_record.measured_p80,
                "is_signed_off": blast_record.is_signed_off,
                "safety_status": blast_record.safety_status
            }
        }
        
        # Plan data
        if include_hole_details and blast_record.plan_data:
            data["plan_data"] = blast_record.plan_data
        elif blast_record.plan_data:
            # Include summary without hole details
            plan_summary = {}
            if 'blast_geometry' in blast_record.plan_data:
                plan_summary['blast_geometry'] = blast_record.plan_data['blast_geometry']
            if 'explosive_summary' in blast_record.plan_data:
                plan_summary['explosive_summary'] = blast_record.plan_data['explosive_summary']
            data["plan_summary"] = plan_summary
        
        # Predictions
        if include_predictions and blast_record.predicted_results:
            data["predicted_results"] = blast_record.predicted_results
        
        # Measurements
        if include_measurements and blast_record.measured_results:
            data["measured_results"] = blast_record.measured_results
        
        # Safety validation
        if include_safety_report and blast_record.safety_validation:
            data["safety_validation"] = blast_record.safety_validation
        
        # Engineer sign-off
        if blast_record.engineer_signoff:
            data["engineer_signoff"] = blast_record.engineer_signoff
        
        # Metadata
        if include_metadata:
            data["metadata"] = {
                "created_at": blast_record.created_at.isoformat() if blast_record.created_at else None,
                "updated_at": blast_record.updated_at.isoformat() if blast_record.updated_at else None,
                "optimization_metadata": blast_record.optimization_metadata
            }
            
            # Performance metrics
            if blast_record.predicted_p80 and blast_record.measured_p80:
                accuracy = blast_record.calculate_fragmentation_accuracy()
                if accuracy is not None:
                    data["metadata"]["fragmentation_accuracy_percent"] = accuracy
            
            # Export capability
            can_export, blocking_reasons = blast_record.can_be_exported()
            data["metadata"]["export_capability"] = {
                "can_be_exported": can_export,
                "blocking_reasons": blocking_reasons
            }
        
        return data
    
    def _build_blast_summary_data(self, blast_record: BlastRecord) -> Dict[str, Any]:
        """Build summary data for blast record."""
        return {
            "id": blast_record.id,
            "blast_name": blast_record.blast_name,
            "site_id": blast_record.site_id,
            "blast_status": blast_record.blast_status.value,
            "created_at": blast_record.created_at.isoformat() if blast_record.created_at else None,
            "total_holes": blast_record.total_holes,
            "total_explosive": blast_record.total_explosive,
            "powder_factor": blast_record.powder_factor,
            "predicted_p80": blast_record.predicted_p80,
            "measured_p80": blast_record.measured_p80,
            "safety_status": blast_record.safety_status,
            "is_signed_off": blast_record.is_signed_off,
            "can_be_exported": blast_record.can_be_exported()[0]
        }
    
    def _build_hole_data(
        self,
        hole: Dict[str, Any],
        blast_record: BlastRecord,
        include_predictions: bool
    ) -> Dict[str, Any]:
        """Build hole data structure."""
        hole_data = {
            "hole_id": hole.get('hole_id', ''),
            "coordinates": hole.get('coordinates', {}),
            "geometry": {
                "collar_elevation": hole.get('collar_elevation', 0),
                "toe_elevation": hole.get('toe_elevation', 0),
                "depth": hole.get('depth', 0),
                "diameter": hole.get('diameter', 0),
                "burden": hole.get('burden', 0),
                "spacing": hole.get('spacing', 0),
                "subdrill": hole.get('subdrill', 0),
                "hole_angle": hole.get('hole_angle', 90),
                "hole_azimuth": hole.get('hole_azimuth', 0)
            },
            "explosive_loading": {
                "charge_kg": hole.get('charge_kg', 0),
                "stemming_m": hole.get('stemming_m', 0),
                "explosive_type": hole.get('explosive_type', ''),
                "delay_ms": hole.get('delay_ms', 0)
            },
            "equipment": {
                "drill_rig": hole.get('drill_rig', '')
            }
        }
        
        if include_predictions:
            # TODO: Add hole-specific predictions when available
            hole_data["predictions"] = {
                "fragment_size_contribution": blast_record.predicted_p80 or 0,
                "ppv_contribution": 0  # Would need hole-specific calculation
            }
        
        return hole_data
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'value'):  # For Enum objects
            return obj.value
        elif hasattr(obj, '__dict__'):  # For custom objects
            return obj.__dict__
        else:
            return str(obj)