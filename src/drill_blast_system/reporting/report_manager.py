"""
Report manager that coordinates all export functionality.
Implements requirements 7.1, 7.2, 7.7 for comprehensive reporting and export management.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path
import tempfile
import zipfile
import io
from enum import Enum

from .pdf_generator import PDFReportGenerator
from .csv_exporter import CSVExporter
from .json_exporter import JSONExporter
from .geojson_exporter import GeoJSONExporter
from .export_validator import ExportValidator
from .visualization import BlastVisualization
from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    GEOJSON = "geojson"


class ExportType(str, Enum):
    """Types of exports available."""
    COMPLETE_REPORT = "complete_report"
    HOLE_DATA = "hole_data"
    SAFETY_VALIDATION = "safety_validation"
    FRAGMENTATION_CURVE = "fragmentation_curve"
    BLAST_SUMMARY = "blast_summary"
    DELAY_SEQUENCE = "delay_sequence"
    PPV_CONTOURS = "ppv_contours"
    BLAST_BOUNDARY = "blast_boundary"


class ReportManager:
    """Manages all export and reporting functionality."""
    
    def __init__(self):
        """Initialize report manager with all exporters."""
        self.pdf_generator = PDFReportGenerator()
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
        self.geojson_exporter = GeoJSONExporter()
        self.export_validator = ExportValidator()
        self.visualization = BlastVisualization()
        
        # Track export statistics
        self.export_stats = {
            "total_exports": 0,
            "exports_by_format": {},
            "exports_by_type": {},
            "total_bytes_exported": 0,
            "validation_failures": 0
        }
    
    def export_blast_plan(
        self,
        blast_record: BlastRecord,
        format: ExportFormat,
        export_type: ExportType = ExportType.COMPLETE_REPORT,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str, str]:
        """
        Export blast plan in specified format and type.
        
        Args:
            blast_record: Blast record to export
            format: Export format (PDF, CSV, JSON, GeoJSON)
            export_type: Type of export (complete_report, hole_data, etc.)
            options: Export options and parameters
            
        Returns:
            Tuple of (content_bytes, filename, media_type)
            
        Raises:
            ValueError: If format/type combination not supported
            Exception: If export fails
        """
        try:
            if options is None:
                options = {}
            
            # Validate format/type combination
            self._validate_export_combination(format, export_type)
            
            # Generate export based on format and type
            if format == ExportFormat.PDF:
                content, filename, media_type = self._export_pdf(
                    blast_record, export_type, options
                )
            elif format == ExportFormat.CSV:
                content, filename, media_type = self._export_csv(
                    blast_record, export_type, options
                )
            elif format == ExportFormat.JSON:
                content, filename, media_type = self._export_json(
                    blast_record, export_type, options
                )
            elif format == ExportFormat.GEOJSON:
                content, filename, media_type = self._export_geojson(
                    blast_record, export_type, options
                )
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Validate export if requested
            if options.get('validate_export', True):
                is_valid, validation_errors = self.validate_export(
                    content, format, export_type, blast_record
                )
                
                if not is_valid:
                    self.export_stats["validation_failures"] += 1
                    logger.warning(
                        "Export validation failed",
                        blast_id=blast_record.id,
                        format=format.value,
                        validation_errors=validation_errors
                    )
                    
                    if options.get('strict_validation', False):
                        raise ValueError(f"Export validation failed: {validation_errors}")
            
            # Update statistics
            self._update_export_stats(format, export_type, len(content))
            
            logger.info(
                "Blast plan exported successfully",
                blast_id=blast_record.id,
                format=format.value,
                export_type=export_type.value,
                size_bytes=len(content)
            )
            
            return content, filename, media_type
            
        except Exception as e:
            logger.error(
                "Failed to export blast plan",
                blast_id=blast_record.id,
                format=format.value,
                export_type=export_type.value,
                error=str(e)
            )
            raise
    
    def export_multiple_blast_plans(
        self,
        blast_records: List[BlastRecord],
        format: ExportFormat,
        export_type: ExportType = ExportType.BLAST_SUMMARY,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str, str]:
        """
        Export multiple blast plans in specified format.
        
        Args:
            blast_records: List of blast records to export
            format: Export format
            export_type: Type of export
            options: Export options
            
        Returns:
            Tuple of (content_bytes, filename, media_type)
        """
        try:
            if options is None:
                options = {}
            
            if len(blast_records) == 1:
                # Single blast plan
                return self.export_blast_plan(blast_records[0], format, export_type, options)
            
            # Multiple blast plans
            if format == ExportFormat.CSV and export_type == ExportType.BLAST_SUMMARY:
                content = self.csv_exporter.export_blast_summary(
                    blast_records, 
                    include_performance=options.get('include_performance', True)
                )
                filename = f"blast_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
                media_type = "text/csv"
                
            elif format == ExportFormat.JSON:
                content = self.json_exporter.export_multiple_blast_plans(
                    blast_records,
                    include_full_details=options.get('include_full_details', False)
                )
                filename = f"blast_plans_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                media_type = "application/json"
                
            else:
                # Create ZIP archive with individual files
                content, filename, media_type = self._create_multi_blast_archive(
                    blast_records, format, export_type, options
                )
            
            # Update statistics
            self._update_export_stats(format, export_type, len(content))
            
            logger.info(
                "Multiple blast plans exported successfully",
                blast_count=len(blast_records),
                format=format.value,
                export_type=export_type.value,
                size_bytes=len(content)
            )
            
            return content, filename, media_type
            
        except Exception as e:
            logger.error(
                "Failed to export multiple blast plans",
                blast_count=len(blast_records),
                format=format.value,
                export_type=export_type.value,
                error=str(e)
            )
            raise
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics."""
        return {
            **self.export_stats,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_supported_formats(self, export_type: ExportType) -> List[ExportFormat]:
        """Get supported formats for an export type."""
        format_support = {
            ExportType.COMPLETE_REPORT: [ExportFormat.PDF, ExportFormat.JSON],
            ExportType.HOLE_DATA: [ExportFormat.CSV, ExportFormat.JSON, ExportFormat.GEOJSON],
            ExportType.SAFETY_VALIDATION: [ExportFormat.CSV, ExportFormat.JSON],
            ExportType.FRAGMENTATION_CURVE: [ExportFormat.CSV, ExportFormat.JSON],
            ExportType.BLAST_SUMMARY: [ExportFormat.CSV, ExportFormat.JSON],
            ExportType.DELAY_SEQUENCE: [ExportFormat.GEOJSON, ExportFormat.JSON],
            ExportType.PPV_CONTOURS: [ExportFormat.GEOJSON, ExportFormat.JSON],
            ExportType.BLAST_BOUNDARY: [ExportFormat.GEOJSON, ExportFormat.JSON]
        }
        
        return format_support.get(export_type, [])
    
    def validate_export(
        self,
        export_content: bytes,
        format: ExportFormat,
        export_type: ExportType,
        blast_record: Optional[BlastRecord] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate exported content.
        
        Args:
            export_content: Exported content as bytes
            format: Export format
            export_type: Export type
            blast_record: Original blast record for completeness validation
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        try:
            if format == ExportFormat.CSV:
                return self.export_validator.validate_csv_export(
                    export_content,
                    expected_columns=self._get_expected_csv_columns(export_type),
                    min_rows=1 if blast_record and blast_record.total_holes > 0 else 0
                )
            
            elif format == ExportFormat.JSON:
                required_fields = ['export_metadata']
                if export_type == ExportType.COMPLETE_REPORT:
                    required_fields.append('blast_record')
                elif export_type == ExportType.HOLE_DATA:
                    required_fields.append('holes')
                
                return self.export_validator.validate_json_export(
                    export_content,
                    required_fields=required_fields
                )
            
            elif format == ExportFormat.GEOJSON:
                expected_features = None
                if export_type == ExportType.HOLE_DATA and blast_record:
                    expected_features = blast_record.total_holes
                
                return self.export_validator.validate_geojson_export(
                    export_content,
                    expected_feature_count=expected_features
                )
            
            elif format == ExportFormat.PDF:
                return self.export_validator.validate_pdf_export(export_content)
            
            else:
                return False, [f"Validation not implemented for format: {format.value}"]
                
        except Exception as e:
            logger.error(
                "Export validation failed with exception",
                format=format.value,
                export_type=export_type.value,
                error=str(e)
            )
            return False, [f"Validation error: {e}"]
    
    def _get_expected_csv_columns(self, export_type: ExportType) -> List[str]:
        """Get expected CSV columns for export type."""
        if export_type == ExportType.HOLE_DATA:
            return [
                'blast_id', 'blast_name', 'hole_id', 'x_coordinate', 'y_coordinate',
                'depth', 'diameter', 'charge_kg', 'delay_ms', 'explosive_type'
            ]
        elif export_type == ExportType.SAFETY_VALIDATION:
            return [
                'blast_id', 'blast_name', 'check_name', 'status', 'limit_value',
                'actual_value', 'safety_margin'
            ]
        elif export_type == ExportType.BLAST_SUMMARY:
            return [
                'blast_id', 'blast_name', 'site_id', 'total_holes', 'total_explosive_kg',
                'powder_factor_kg_t', 'safety_status'
            ]
        else:
            return []
    
    def create_visualization(
        self,
        blast_record: BlastRecord,
        visualization_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[bytes, str, Dict[str, Any]]:
        """
        Create visualization for blast record.
        
        Args:
            blast_record: Blast record to visualize
            visualization_type: Type of visualization ('map', 'fragmentation', 'delay', 'ppv', 'interactive')
            options: Visualization options
            
        Returns:
            Visualization content (bytes, string, or data dict)
        """
        try:
            if options is None:
                options = {}
            
            if visualization_type == 'map':
                return self.visualization.create_blast_plan_map(
                    blast_record,
                    color_by=options.get('color_by', 'charge'),
                    include_labels=options.get('include_labels', True),
                    include_legend=options.get('include_legend', True),
                    include_scale=options.get('include_scale', True),
                    include_north_arrow=options.get('include_north_arrow', True),
                    output_format=options.get('output_format', 'png')
                )
            
            elif visualization_type == 'fragmentation':
                return self.visualization.create_fragmentation_curve(
                    blast_record,
                    include_measured=options.get('include_measured', True),
                    include_targets=options.get('include_targets', True),
                    sieve_sizes=options.get('sieve_sizes'),
                    output_format=options.get('output_format', 'png')
                )
            
            elif visualization_type == 'delay':
                return self.visualization.create_delay_sequence_visualization(
                    blast_record,
                    show_timing=options.get('show_timing', True),
                    show_charge_flow=options.get('show_charge_flow', True),
                    output_format=options.get('output_format', 'png')
                )
            
            elif visualization_type == 'ppv':
                return self.visualization.create_ppv_contour_map(
                    blast_record,
                    contour_levels=options.get('contour_levels'),
                    include_receptors=options.get('include_receptors', True),
                    output_format=options.get('output_format', 'png')
                )
            
            elif visualization_type == 'interactive':
                return self.visualization.create_interactive_visualization_data(blast_record)
            
            else:
                raise ValueError(f"Unsupported visualization type: {visualization_type}")
            
        except Exception as e:
            logger.error(
                "Failed to create visualization",
                blast_id=blast_record.id,
                visualization_type=visualization_type,
                error=str(e)
            )
            raise
    
    def _validate_export_combination(self, format: ExportFormat, export_type: ExportType):
        """Validate that format and export type combination is supported."""
        supported_formats = self.get_supported_formats(export_type)
        
        if format not in supported_formats:
            raise ValueError(
                f"Export type '{export_type.value}' does not support format '{format.value}'. "
                f"Supported formats: {[f.value for f in supported_formats]}"
            )
    
    def _export_pdf(
        self,
        blast_record: BlastRecord,
        export_type: ExportType,
        options: Dict[str, Any]
    ) -> Tuple[bytes, str, str]:
        """Export to PDF format."""
        if export_type != ExportType.COMPLETE_REPORT:
            raise ValueError("PDF format only supports complete_report export type")
        
        content = self.pdf_generator.generate_blast_plan_report(
            blast_record,
            include_safety_report=options.get('include_safety_report', True),
            include_hole_details=options.get('include_hole_details', True),
            include_predictions=options.get('include_predictions', True),
            include_measurements=options.get('include_measurements', False)
        )
        
        filename = f"{blast_record.blast_name.replace(' ', '_')}_report.pdf"
        return content, filename, "application/pdf"
    
    def _export_csv(
        self,
        blast_record: BlastRecord,
        export_type: ExportType,
        options: Dict[str, Any]
    ) -> Tuple[bytes, str, str]:
        """Export to CSV format."""
        if export_type == ExportType.HOLE_DATA:
            content = self.csv_exporter.export_hole_data(
                blast_record,
                include_predictions=options.get('include_predictions', True),
                include_measurements=options.get('include_measurements', False),
                include_geometry=options.get('include_geometry', True)
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_holes.csv"
            
        elif export_type == ExportType.SAFETY_VALIDATION:
            content = self.csv_exporter.export_safety_validation(blast_record)
            filename = f"{blast_record.blast_name.replace(' ', '_')}_safety.csv"
            
        elif export_type == ExportType.FRAGMENTATION_CURVE:
            content = self.csv_exporter.export_fragmentation_curve(
                blast_record,
                sieve_sizes=options.get('sieve_sizes')
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_fragmentation.csv"
            
        elif export_type == ExportType.BLAST_SUMMARY:
            content = self.csv_exporter.export_blast_summary(
                [blast_record],
                include_performance=options.get('include_performance', True)
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_summary.csv"
            
        else:
            raise ValueError(f"CSV format does not support export type: {export_type.value}")
        
        return content, filename, "text/csv"
    
    def _export_json(
        self,
        blast_record: BlastRecord,
        export_type: ExportType,
        options: Dict[str, Any]
    ) -> Tuple[bytes, str, str]:
        """Export to JSON format."""
        if export_type == ExportType.COMPLETE_REPORT:
            content = self.json_exporter.export_complete_blast_plan(
                blast_record,
                include_safety_report=options.get('include_safety_report', True),
                include_hole_details=options.get('include_hole_details', True),
                include_predictions=options.get('include_predictions', True),
                include_measurements=options.get('include_measurements', False),
                include_metadata=options.get('include_metadata', True)
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_complete.json"
            
        elif export_type == ExportType.HOLE_DATA:
            content = self.json_exporter.export_hole_data_only(
                blast_record,
                include_predictions=options.get('include_predictions', True)
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_holes.json"
            
        elif export_type == ExportType.SAFETY_VALIDATION:
            content = self.json_exporter.export_safety_validation_only(blast_record)
            filename = f"{blast_record.blast_name.replace(' ', '_')}_safety.json"
            
        else:
            # For other types, use complete export with filtered data
            content = self.json_exporter.export_complete_blast_plan(
                blast_record,
                include_safety_report=export_type == ExportType.SAFETY_VALIDATION,
                include_hole_details=export_type in [ExportType.HOLE_DATA, ExportType.DELAY_SEQUENCE],
                include_predictions=True,
                include_measurements=False,
                include_metadata=True
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_{export_type.value}.json"
        
        return content, filename, "application/json"
    
    def _export_geojson(
        self,
        blast_record: BlastRecord,
        export_type: ExportType,
        options: Dict[str, Any]
    ) -> Tuple[bytes, str, str]:
        """Export to GeoJSON format."""
        coordinate_system = options.get('coordinate_system', 'local')
        
        if export_type == ExportType.HOLE_DATA:
            content = self.geojson_exporter.export_drill_holes(
                blast_record,
                include_predictions=options.get('include_predictions', True),
                include_measurements=options.get('include_measurements', False),
                coordinate_system=coordinate_system
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_holes.geojson"
            
        elif export_type == ExportType.DELAY_SEQUENCE:
            content = self.geojson_exporter.export_delay_sequence(
                blast_record,
                coordinate_system=coordinate_system
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_delays.geojson"
            
        elif export_type == ExportType.PPV_CONTOURS:
            content = self.geojson_exporter.export_ppv_contours(
                blast_record,
                contour_levels=options.get('contour_levels'),
                coordinate_system=coordinate_system
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_ppv_contours.geojson"
            
        elif export_type == ExportType.BLAST_BOUNDARY:
            content = self.geojson_exporter.export_blast_boundary(
                blast_record,
                coordinate_system=coordinate_system
            )
            filename = f"{blast_record.blast_name.replace(' ', '_')}_boundary.geojson"
            
        else:
            raise ValueError(f"GeoJSON format does not support export type: {export_type.value}")
        
        return content, filename, "application/geo+json"
    
    def _create_multi_blast_archive(
        self,
        blast_records: List[BlastRecord],
        format: ExportFormat,
        export_type: ExportType,
        options: Dict[str, Any]
    ) -> Tuple[bytes, str, str]:
        """Create ZIP archive containing multiple blast plan exports."""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for blast_record in blast_records:
                try:
                    # Export individual blast plan
                    content, filename, _ = self.export_blast_plan(
                        blast_record, format, export_type, options
                    )
                    
                    # Add to ZIP with blast name prefix
                    blast_folder = blast_record.blast_name.replace(' ', '_')
                    zip_path = f"{blast_folder}/{filename}"
                    zip_file.writestr(zip_path, content)
                    
                except Exception as e:
                    logger.warning(
                        "Failed to export blast plan for archive",
                        blast_id=blast_record.id,
                        error=str(e)
                    )
                    # Continue with other blast plans
        
        zip_content = zip_buffer.getvalue()
        zip_filename = f"blast_plans_{format.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return zip_content, zip_filename, "application/zip"
    
    def _update_export_stats(self, format: ExportFormat, export_type: ExportType, size_bytes: int):
        """Update export statistics."""
        self.export_stats["total_exports"] += 1
        self.export_stats["total_bytes_exported"] += size_bytes
        
        # Update format statistics
        format_key = format.value
        if format_key not in self.export_stats["exports_by_format"]:
            self.export_stats["exports_by_format"][format_key] = 0
        self.export_stats["exports_by_format"][format_key] += 1
        
        # Update type statistics
        type_key = export_type.value
        if type_key not in self.export_stats["exports_by_type"]:
            self.export_stats["exports_by_type"][type_key] = 0
        self.export_stats["exports_by_type"][type_key] += 1