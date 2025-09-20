"""
CSV export functionality for blast plan data.
Implements requirement 7.2: CSV export with complete hole data.
"""

from typing import List, Dict, Any, Optional
import csv
import io
from datetime import datetime

from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class CSVExporter:
    """Exports blast plan data to CSV format."""
    
    def __init__(self):
        """Initialize CSV exporter."""
        pass
    
    def export_hole_data(
        self,
        blast_record: BlastRecord,
        include_predictions: bool = True,
        include_measurements: bool = False,
        include_geometry: bool = True
    ) -> bytes:
        """
        Export drill hole data to CSV format.
        
        Args:
            blast_record: Blast record to export
            include_predictions: Include prediction results
            include_measurements: Include measurement data if available
            include_geometry: Include geometric parameters
            
        Returns:
            CSV content as bytes
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Build header row
            headers = self._build_hole_headers(
                include_predictions, include_measurements, include_geometry
            )
            writer.writerow(headers)
            
            # Export hole data
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                holes = blast_record.plan_data['holes']
                
                for hole in holes:
                    row = self._build_hole_row(
                        hole, blast_record, include_predictions, 
                        include_measurements, include_geometry
                    )
                    writer.writerow(row)
            
            content = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(
                "Hole data exported to CSV",
                blast_id=blast_record.id,
                hole_count=blast_record.total_holes,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export hole data to CSV",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_blast_summary(
        self,
        blast_records: List[BlastRecord],
        include_performance: bool = True
    ) -> bytes:
        """
        Export blast plan summary data to CSV format.
        
        Args:
            blast_records: List of blast records to export
            include_performance: Include performance metrics
            
        Returns:
            CSV content as bytes
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Build header row
            headers = self._build_summary_headers(include_performance)
            writer.writerow(headers)
            
            # Export blast summary data
            for blast_record in blast_records:
                row = self._build_summary_row(blast_record, include_performance)
                writer.writerow(row)
            
            content = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(
                "Blast summary exported to CSV",
                blast_count=len(blast_records),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export blast summary to CSV",
                blast_count=len(blast_records),
                error=str(e)
            )
            raise
    
    def export_safety_validation(
        self,
        blast_record: BlastRecord
    ) -> bytes:
        """
        Export safety validation results to CSV format.
        
        Args:
            blast_record: Blast record to export
            
        Returns:
            CSV content as bytes
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header row
            headers = [
                'blast_id', 'blast_name', 'validation_timestamp', 'overall_status',
                'check_name', 'check_type', 'status', 'limit_value', 'actual_value',
                'safety_margin', 'units', 'description'
            ]
            writer.writerow(headers)
            
            # Export safety check data
            if blast_record.safety_validation:
                safety_data = blast_record.safety_validation
                validation_timestamp = safety_data.get('validation_timestamp', '')
                overall_status = 'VALID' if safety_data.get('is_valid', False) else 'INVALID'
                
                safety_checks = safety_data.get('safety_checks', [])
                
                for check in safety_checks:
                    row = [
                        blast_record.id,
                        blast_record.blast_name,
                        validation_timestamp,
                        overall_status,
                        check.get('check_name', ''),
                        check.get('check_type', ''),
                        check.get('status', ''),
                        check.get('limit_value', 0),
                        check.get('actual_value', 0),
                        check.get('safety_margin', 0),
                        check.get('units', ''),
                        check.get('description', '')
                    ]
                    writer.writerow(row)
            
            content = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(
                "Safety validation exported to CSV",
                blast_id=blast_record.id,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export safety validation to CSV",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_fragmentation_curve(
        self,
        blast_record: BlastRecord,
        sieve_sizes: Optional[List[float]] = None
    ) -> bytes:
        """
        Export fragmentation curve data to CSV format.
        
        Args:
            blast_record: Blast record to export
            sieve_sizes: Optional list of sieve sizes (mm)
            
        Returns:
            CSV content as bytes
        """
        try:
            if sieve_sizes is None:
                # Standard sieve sizes in mm
                sieve_sizes = [
                    6.3, 8, 10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100,
                    125, 160, 200, 250, 315, 400, 500, 630, 800, 1000
                ]
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header row
            headers = ['blast_id', 'blast_name', 'sieve_size_mm', 'percent_passing']
            if blast_record.predicted_results and 'fragmentation' in blast_record.predicted_results:
                headers.append('predicted_percent_passing')
            if blast_record.measured_results and 'fragmentation_measurements' in blast_record.measured_results:
                headers.append('measured_percent_passing')
            
            writer.writerow(headers)
            
            # Export fragmentation curve data
            for size in sieve_sizes:
                row = [blast_record.id, blast_record.blast_name, size]
                
                # Calculate percent passing for this size
                # This is a simplified calculation - in practice, you'd use the actual
                # fragmentation curve calculation from the physics models
                
                # Predicted data
                if blast_record.predicted_results and 'fragmentation' in blast_record.predicted_results:
                    frag = blast_record.predicted_results['fragmentation']
                    p80 = frag.get('p80', 100)
                    
                    # Simple Rosin-Rammler approximation
                    if size <= p80:
                        percent_passing = 80 * (size / p80) ** 0.8
                    else:
                        percent_passing = 80 + 20 * (1 - ((size - p80) / (2 * p80)) ** 0.5)
                        percent_passing = min(100, max(80, percent_passing))
                    
                    row.append(round(percent_passing, 2))
                
                # Measured data (if available)
                if blast_record.measured_results and 'fragmentation_measurements' in blast_record.measured_results:
                    # TODO: Implement actual measured curve calculation
                    row.append(0)  # Placeholder
                
                writer.writerow(row)
            
            content = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(
                "Fragmentation curve exported to CSV",
                blast_id=blast_record.id,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export fragmentation curve to CSV",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def _build_hole_headers(
        self,
        include_predictions: bool,
        include_measurements: bool,
        include_geometry: bool
    ) -> List[str]:
        """Build header row for hole data export."""
        headers = [
            'blast_id', 'blast_name', 'hole_id', 'x_coordinate', 'y_coordinate', 'z_coordinate',
            'collar_elevation', 'toe_elevation', 'depth', 'diameter', 'charge_kg',
            'stemming_m', 'delay_ms', 'explosive_type', 'drill_rig'
        ]
        
        if include_geometry:
            headers.extend([
                'burden', 'spacing', 'subdrill', 'hole_angle', 'hole_azimuth'
            ])
        
        if include_predictions:
            headers.extend([
                'predicted_fragment_size', 'predicted_ppv'
            ])
        
        if include_measurements:
            headers.extend([
                'measured_fragment_size', 'measured_ppv', 'measurement_quality'
            ])
        
        return headers
    
    def _build_hole_row(
        self,
        hole: Dict[str, Any],
        blast_record: BlastRecord,
        include_predictions: bool,
        include_measurements: bool,
        include_geometry: bool
    ) -> List[Any]:
        """Build data row for a single hole."""
        coords = hole.get('coordinates', {})
        
        row = [
            blast_record.id,
            blast_record.blast_name,
            hole.get('hole_id', ''),
            coords.get('x', 0),
            coords.get('y', 0),
            coords.get('z', 0),
            hole.get('collar_elevation', 0),
            hole.get('toe_elevation', 0),
            hole.get('depth', 0),
            hole.get('diameter', 0),
            hole.get('charge_kg', 0),
            hole.get('stemming_m', 0),
            hole.get('delay_ms', 0),
            hole.get('explosive_type', ''),
            hole.get('drill_rig', '')
        ]
        
        if include_geometry:
            row.extend([
                hole.get('burden', 0),
                hole.get('spacing', 0),
                hole.get('subdrill', 0),
                hole.get('hole_angle', 90),
                hole.get('hole_azimuth', 0)
            ])
        
        if include_predictions:
            # TODO: Get hole-specific predictions
            row.extend([
                blast_record.predicted_p80 or 0,  # Simplified - use blast average
                0  # PPV would need hole-specific calculation
            ])
        
        if include_measurements:
            # TODO: Get hole-specific measurements
            row.extend([
                blast_record.measured_p80 or 0,  # Simplified - use blast average
                0,  # PPV measurement
                0   # Quality score
            ])
        
        return row
    
    def _build_summary_headers(self, include_performance: bool) -> List[str]:
        """Build header row for blast summary export."""
        headers = [
            'blast_id', 'blast_name', 'site_id', 'blast_status', 'created_at',
            'planned_execution_date', 'actual_execution_date', 'blast_operator',
            'total_holes', 'total_explosive_kg', 'powder_factor_kg_t',
            'blast_area_m2', 'rock_tonnage', 'safety_status', 'is_signed_off'
        ]
        
        if include_performance:
            headers.extend([
                'predicted_p80', 'measured_p80', 'fragmentation_accuracy_percent',
                'max_predicted_ppv', 'optimization_runtime_seconds'
            ])
        
        return headers
    
    def _build_summary_row(
        self,
        blast_record: BlastRecord,
        include_performance: bool
    ) -> List[Any]:
        """Build data row for blast summary."""
        geometry = blast_record.plan_data.get('blast_geometry', {}) if blast_record.plan_data else {}
        explosives = blast_record.plan_data.get('explosive_summary', {}) if blast_record.plan_data else {}
        
        row = [
            blast_record.id,
            blast_record.blast_name,
            blast_record.site_id,
            blast_record.blast_status.value,
            blast_record.created_at.isoformat() if blast_record.created_at else '',
            blast_record.planned_execution_date.isoformat() if blast_record.planned_execution_date else '',
            blast_record.actual_execution_date.isoformat() if blast_record.actual_execution_date else '',
            blast_record.blast_operator or '',
            blast_record.total_holes,
            blast_record.total_explosive,
            explosives.get('powder_factor_kg_t', 0),
            geometry.get('blast_area', 0),
            geometry.get('rock_tonnage', 0),
            blast_record.safety_status,
            blast_record.is_signed_off
        ]
        
        if include_performance:
            # Calculate fragmentation accuracy
            accuracy = blast_record.calculate_fragmentation_accuracy()
            
            # Get max PPV
            max_ppv = 0
            if blast_record.predicted_results and 'ppv_predictions' in blast_record.predicted_results:
                max_ppv = blast_record.predicted_results['ppv_predictions'].get('max_predicted_ppv', 0)
            
            # Get optimization runtime
            runtime = 0
            if blast_record.optimization_metadata and 'solver_results' in blast_record.optimization_metadata:
                solver_results = blast_record.optimization_metadata['solver_results']
                if solver_results:
                    runtime = sum(result.get('runtime_seconds', 0) for result in solver_results)
            
            row.extend([
                blast_record.predicted_p80 or 0,
                blast_record.measured_p80 or 0,
                accuracy or 0,
                max_ppv,
                runtime
            ])
        
        return row