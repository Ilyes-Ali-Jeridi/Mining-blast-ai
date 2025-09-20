"""
Tests for export and reporting functionality.
Tests requirements 7.1, 7.2, 7.7: PDF reports, machine-readable exports, and audit logging.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import json
import csv
import io

from src.drill_blast_system.reporting.report_manager import ReportManager, ExportFormat, ExportType
from src.drill_blast_system.reporting.csv_exporter import CSVExporter
from src.drill_blast_system.reporting.json_exporter import JSONExporter
from src.drill_blast_system.reporting.geojson_exporter import GeoJSONExporter
from src.drill_blast_system.models.blast_record import BlastRecord, BlastStatus


@pytest.fixture
def sample_blast_record():
    """Create a sample blast record for testing."""
    blast_record = Mock()
    blast_record.id = 1
    blast_record.blast_name = "Test Blast 001"
    blast_record.site_id = 1
    blast_record.blast_status = BlastStatus.APPROVED
    blast_record.total_holes = 24
    blast_record.total_explosive = 845.0
    blast_record.powder_factor = 0.35
    blast_record.predicted_p80 = 180.0
    blast_record.measured_p80 = None
    blast_record.safety_status = "VALID"
    blast_record.is_signed_off = True
    blast_record.created_at = datetime.utcnow()
    blast_record.updated_at = datetime.utcnow()
    blast_record.blast_description = "Test blast for unit testing"
    blast_record.blast_operator = "Test Operator"
    blast_record.planned_execution_date = None
    blast_record.actual_execution_date = None
    blast_record.is_template = False
    blast_record.plan_version = 1
    blast_record.parent_blast_id = None
    blast_record.engineer_signoff = None
    blast_record.optimization_metadata = None
    
    # Mock plan data
    blast_record.plan_data = {
        "holes": [
            {
                "hole_id": "H001",
                "coordinates": {"x": 1000.0, "y": 2000.0, "z": 200.0},
                "depth": 16.5,
                "diameter": 165.0,
                "charge_kg": 35.2,
                "stemming_m": 4.0,
                "delay_ms": 0,
                "explosive_type": "Standard ANFO",
                "drill_rig": "Atlas Copco ROC D65",
                "collar_elevation": 200.0,
                "toe_elevation": 183.5,
                "burden": 4.5,
                "spacing": 5.0,
                "subdrill": 1.5,
                "hole_angle": 90.0,
                "hole_azimuth": 0.0
            },
            {
                "hole_id": "H002",
                "coordinates": {"x": 1005.0, "y": 2000.0, "z": 200.0},
                "depth": 16.0,
                "diameter": 165.0,
                "charge_kg": 34.8,
                "stemming_m": 4.0,
                "delay_ms": 25,
                "explosive_type": "Standard ANFO",
                "drill_rig": "Atlas Copco ROC D65",
                "collar_elevation": 200.0,
                "toe_elevation": 184.0,
                "burden": 4.5,
                "spacing": 5.0,
                "subdrill": 1.5,
                "hole_angle": 90.0,
                "hole_azimuth": 0.0
            }
        ],
        "blast_geometry": {
            "total_holes": 24,
            "total_depth": 396.0,
            "blast_area": 1200.0,
            "blast_volume": 18000.0,
            "rock_tonnage": 47700.0,
            "average_burden": 4.5,
            "average_spacing": 5.0,
            "hole_pattern": "rectangular"
        },
        "explosive_summary": {
            "total_explosive": 845.0,
            "powder_factor_kg_t": 0.35,
            "powder_factor_kg_m3": 0.47,
            "explosive_types_used": ["Standard ANFO"],
            "max_charge_per_hole": 45.2,
            "max_charge_per_delay": 180.8
        }
    }
    
    # Mock predicted results
    blast_record.predicted_results = {
        "fragmentation": {
            "mean_fragment_size": 125.0,
            "p10": 45.0,
            "p50": 95.0,
            "p80": 180.0,
            "uniformity_index": 1.25,
            "characteristic_size": 110.0,
            "distribution_type": "rosin_rammler"
        },
        "ppv_predictions": {
            "receptor_predictions": [
                {
                    "receptor_name": "Office Building A",
                    "coordinates": {"x": 1500.0, "y": 2500.0, "z": 200.0},
                    "predicted_ppv": 1.8,
                    "distance_to_blast": 250.0,
                    "safety_margin": 0.9
                }
            ],
            "max_predicted_ppv": 2.1,
            "ppv_model_parameters": {"k": 1.4, "a": 0.333, "b": 1.6}
        }
    }
    
    # Mock safety validation
    blast_record.safety_validation = {
        "validation_timestamp": datetime.utcnow().isoformat(),
        "is_valid": True,
        "safety_checks": [
            {
                "check_name": "Maximum charge per hole",
                "check_type": "charge_limit",
                "status": "PASS",
                "limit_value": 50.0,
                "actual_value": 45.2,
                "safety_margin": 0.096,
                "description": "Charge per hole within regulatory limits"
            }
        ],
        "violations": [],
        "safety_config_used": {
            "max_charge_per_hole": 50.0,
            "max_charge_per_delay": 200.0,
            "ppv_default_limit": 5.0
        }
    }
    
    # Mock methods
    blast_record.can_be_exported.return_value = (True, [])
    blast_record.calculate_fragmentation_accuracy.return_value = None
    
    return blast_record


class TestCSVExporter:
    """Test CSV export functionality."""
    
    def test_export_hole_data(self, sample_blast_record):
        """Test exporting hole data to CSV."""
        exporter = CSVExporter()
        
        content = exporter.export_hole_data(
            sample_blast_record,
            include_predictions=True,
            include_measurements=False,
            include_geometry=True
        )
        
        # Verify content is bytes
        assert isinstance(content, bytes)
        
        # Parse CSV content
        csv_text = content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        
        # Verify header
        assert len(rows) > 0
        header = rows[0]
        assert 'hole_id' in header
        assert 'x_coordinate' in header
        assert 'charge_kg' in header
        assert 'burden' in header  # geometry included
        assert 'predicted_fragment_size' in header  # predictions included
        
        # Verify data rows
        assert len(rows) == 3  # Header + 2 holes
        assert rows[1][header.index('hole_id')] == 'H001'
        assert rows[2][header.index('hole_id')] == 'H002'
    
    def test_export_blast_summary(self, sample_blast_record):
        """Test exporting blast summary to CSV."""
        exporter = CSVExporter()
        
        content = exporter.export_blast_summary(
            [sample_blast_record],
            include_performance=True
        )
        
        # Verify content
        assert isinstance(content, bytes)
        
        # Parse CSV content
        csv_text = content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        
        # Verify structure
        assert len(rows) == 2  # Header + 1 blast
        header = rows[0]
        assert 'blast_id' in header
        assert 'blast_name' in header
        assert 'total_holes' in header
        assert 'predicted_p80' in header  # performance included
    
    def test_export_safety_validation(self, sample_blast_record):
        """Test exporting safety validation to CSV."""
        exporter = CSVExporter()
        
        content = exporter.export_safety_validation(sample_blast_record)
        
        # Verify content
        assert isinstance(content, bytes)
        
        # Parse CSV content
        csv_text = content.decode('utf-8')
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        
        # Verify structure
        assert len(rows) == 2  # Header + 1 safety check
        header = rows[0]
        assert 'check_name' in header
        assert 'status' in header
        assert 'safety_margin' in header


class TestJSONExporter:
    """Test JSON export functionality."""
    
    def test_export_complete_blast_plan(self, sample_blast_record):
        """Test exporting complete blast plan to JSON."""
        exporter = JSONExporter()
        
        content = exporter.export_complete_blast_plan(
            sample_blast_record,
            include_safety_report=True,
            include_hole_details=True,
            include_predictions=True,
            include_measurements=False,
            include_metadata=True
        )
        
        # Verify content is bytes
        assert isinstance(content, bytes)
        
        # Parse JSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify structure
        assert 'export_metadata' in data
        assert 'blast_record' in data
        
        blast_data = data['blast_record']
        assert 'basic_info' in blast_data
        assert 'computed_properties' in blast_data
        assert 'plan_data' in blast_data
        assert 'predicted_results' in blast_data
        assert 'safety_validation' in blast_data
        assert 'metadata' in blast_data
        
        # Verify basic info
        basic_info = blast_data['basic_info']
        assert basic_info['id'] == 1
        assert basic_info['blast_name'] == "Test Blast 001"
        assert basic_info['blast_status'] == "approved"
    
    def test_export_hole_data_only(self, sample_blast_record):
        """Test exporting only hole data to JSON."""
        exporter = JSONExporter()
        
        content = exporter.export_hole_data_only(
            sample_blast_record,
            include_predictions=True
        )
        
        # Parse JSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify structure
        assert 'export_metadata' in data
        assert 'holes' in data
        assert len(data['holes']) == 2
        
        # Verify hole data structure
        hole = data['holes'][0]
        assert 'hole_id' in hole
        assert 'coordinates' in hole
        assert 'geometry' in hole
        assert 'explosive_loading' in hole
        assert 'predictions' in hole  # predictions included
    
    def test_export_multiple_blast_plans(self, sample_blast_record):
        """Test exporting multiple blast plans to JSON."""
        exporter = JSONExporter()
        
        # Create second blast record
        blast_record_2 = Mock(spec=BlastRecord)
        blast_record_2.id = 2
        blast_record_2.blast_name = "Test Blast 002"
        blast_record_2.site_id = 1
        blast_record_2.blast_status = BlastStatus.DRAFT
        blast_record_2.total_holes = 12
        blast_record_2.total_explosive = 400.0
        blast_record_2.powder_factor = 0.30
        blast_record_2.predicted_p80 = 160.0
        blast_record_2.measured_p80 = None
        blast_record_2.safety_status = "VALID"
        blast_record_2.is_signed_off = False
        blast_record_2.created_at = datetime.utcnow()
        blast_record_2.can_be_exported.return_value = (False, ["Not signed off"])
        
        content = exporter.export_multiple_blast_plans(
            [sample_blast_record, blast_record_2],
            include_full_details=False
        )
        
        # Parse JSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify structure
        assert 'export_metadata' in data
        assert 'blast_plans' in data
        assert len(data['blast_plans']) == 2
        assert data['export_metadata']['blast_count'] == 2


class TestGeoJSONExporter:
    """Test GeoJSON export functionality."""
    
    def test_export_drill_holes(self, sample_blast_record):
        """Test exporting drill holes to GeoJSON."""
        exporter = GeoJSONExporter()
        
        content = exporter.export_drill_holes(
            sample_blast_record,
            include_predictions=True,
            include_measurements=False,
            coordinate_system="local"
        )
        
        # Verify content is bytes
        assert isinstance(content, bytes)
        
        # Parse GeoJSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify GeoJSON structure
        assert data['type'] == 'FeatureCollection'
        assert 'crs' in data
        assert 'properties' in data
        assert 'features' in data
        assert len(data['features']) == 2  # 2 holes
        
        # Verify feature structure
        feature = data['features'][0]
        assert feature['type'] == 'Feature'
        assert feature['geometry']['type'] == 'Point'
        assert len(feature['geometry']['coordinates']) == 3  # x, y, z
        assert 'hole_id' in feature['properties']
        assert 'charge_kg' in feature['properties']
        assert 'predicted_fragment_contribution' in feature['properties']  # predictions included
    
    def test_export_delay_sequence(self, sample_blast_record):
        """Test exporting delay sequence to GeoJSON."""
        exporter = GeoJSONExporter()
        
        content = exporter.export_delay_sequence(
            sample_blast_record,
            coordinate_system="local"
        )
        
        # Parse GeoJSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify structure
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert len(data['features']) >= 2  # At least the hole points
        
        # Verify delay information in properties
        properties = data['properties']
        assert 'export_type' in properties
        assert properties['export_type'] == 'delay_sequence'
        assert 'total_delays' in properties
    
    def test_export_ppv_contours(self, sample_blast_record):
        """Test exporting PPV contours to GeoJSON."""
        exporter = GeoJSONExporter()
        
        content = exporter.export_ppv_contours(
            sample_blast_record,
            contour_levels=[1.0, 2.0, 5.0],
            coordinate_system="local"
        )
        
        # Parse GeoJSON content
        data = json.loads(content.decode('utf-8'))
        
        # Verify structure
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        
        # Should have contour polygons and receptor points
        contour_features = [f for f in data['features'] if f['properties']['feature_type'] == 'ppv_contour']
        receptor_features = [f for f in data['features'] if f['properties']['feature_type'] == 'ppv_receptor']
        
        assert len(contour_features) == 3  # 3 contour levels
        assert len(receptor_features) == 1  # 1 receptor


class TestReportManager:
    """Test report manager functionality."""
    
    @patch('src.drill_blast_system.reporting.pdf_generator.REPORTLAB_AVAILABLE', True)
    def test_export_blast_plan_pdf(self, sample_blast_record):
        """Test exporting blast plan as PDF."""
        manager = ReportManager()
        
        with patch.object(manager.pdf_generator, 'generate_blast_plan_report') as mock_pdf:
            mock_pdf.return_value = b'PDF content'
            
            content, filename, media_type = manager.export_blast_plan(
                sample_blast_record,
                ExportFormat.PDF,
                ExportType.COMPLETE_REPORT
            )
            
            assert isinstance(content, bytes)
            assert filename.endswith('.pdf')
            assert media_type == 'application/pdf'
            mock_pdf.assert_called_once()
    
    def test_export_blast_plan_csv(self, sample_blast_record):
        """Test exporting blast plan as CSV."""
        manager = ReportManager()
        
        content, filename, media_type = manager.export_blast_plan(
            sample_blast_record,
            ExportFormat.CSV,
            ExportType.HOLE_DATA
        )
        
        assert isinstance(content, bytes)
        assert filename.endswith('.csv')
        assert media_type == 'text/csv'
    
    def test_export_blast_plan_json(self, sample_blast_record):
        """Test exporting blast plan as JSON."""
        manager = ReportManager()
        
        content, filename, media_type = manager.export_blast_plan(
            sample_blast_record,
            ExportFormat.JSON,
            ExportType.COMPLETE_REPORT
        )
        
        assert isinstance(content, bytes)
        assert filename.endswith('.json')
        assert media_type == 'application/json'
        
        # Verify JSON is valid
        data = json.loads(content.decode('utf-8'))
        assert 'export_metadata' in data
    
    def test_export_blast_plan_geojson(self, sample_blast_record):
        """Test exporting blast plan as GeoJSON."""
        manager = ReportManager()
        
        content, filename, media_type = manager.export_blast_plan(
            sample_blast_record,
            ExportFormat.GEOJSON,
            ExportType.HOLE_DATA
        )
        
        assert isinstance(content, bytes)
        assert filename.endswith('.geojson')
        assert media_type == 'application/geo+json'
        
        # Verify GeoJSON is valid
        data = json.loads(content.decode('utf-8'))
        assert data['type'] == 'FeatureCollection'
    
    def test_export_multiple_blast_plans(self, sample_blast_record):
        """Test exporting multiple blast plans."""
        manager = ReportManager()
        
        # Create second blast record
        blast_record_2 = Mock(spec=sample_blast_record)
        blast_record_2.id = 2
        blast_record_2.blast_name = "Test Blast 002"
        
        content, filename, media_type = manager.export_multiple_blast_plans(
            [sample_blast_record, blast_record_2],
            ExportFormat.CSV,
            ExportType.BLAST_SUMMARY
        )
        
        assert isinstance(content, bytes)
        assert filename.endswith('.csv')
        assert media_type == 'text/csv'
    
    def test_get_supported_formats(self):
        """Test getting supported formats for export types."""
        manager = ReportManager()
        
        # Test complete report formats
        formats = manager.get_supported_formats(ExportType.COMPLETE_REPORT)
        assert ExportFormat.PDF in formats
        assert ExportFormat.JSON in formats
        
        # Test hole data formats
        formats = manager.get_supported_formats(ExportType.HOLE_DATA)
        assert ExportFormat.CSV in formats
        assert ExportFormat.JSON in formats
        assert ExportFormat.GEOJSON in formats
        
        # Test GeoJSON-only formats
        formats = manager.get_supported_formats(ExportType.PPV_CONTOURS)
        assert ExportFormat.GEOJSON in formats
        assert ExportFormat.PDF not in formats
    
    def test_validate_export_combination(self):
        """Test validation of format/type combinations."""
        manager = ReportManager()
        
        # Valid combinations should not raise
        manager._validate_export_combination(ExportFormat.PDF, ExportType.COMPLETE_REPORT)
        manager._validate_export_combination(ExportFormat.CSV, ExportType.HOLE_DATA)
        manager._validate_export_combination(ExportFormat.GEOJSON, ExportType.PPV_CONTOURS)
        
        # Invalid combinations should raise ValueError
        with pytest.raises(ValueError):
            manager._validate_export_combination(ExportFormat.PDF, ExportType.HOLE_DATA)
        
        with pytest.raises(ValueError):
            manager._validate_export_combination(ExportFormat.CSV, ExportType.PPV_CONTOURS)
    
    def test_export_statistics(self, sample_blast_record):
        """Test export statistics tracking."""
        manager = ReportManager()
        
        # Initial statistics
        stats = manager.get_export_statistics()
        assert stats['total_exports'] == 0
        assert stats['total_bytes_exported'] == 0
        
        # Perform export
        manager.export_blast_plan(
            sample_blast_record,
            ExportFormat.JSON,
            ExportType.COMPLETE_REPORT
        )
        
        # Check updated statistics
        stats = manager.get_export_statistics()
        assert stats['total_exports'] == 1
        assert stats['total_bytes_exported'] > 0
        assert 'json' in stats['exports_by_format']
        assert 'complete_report' in stats['exports_by_type']


@pytest.mark.asyncio
class TestExportAPI:
    """Test export API endpoints."""
    
    async def test_export_single_blast_plan_endpoint(self):
        """Test single blast plan export endpoint."""
        # This would require setting up FastAPI test client
        # For now, just verify the endpoint structure is correct
        from src.drill_blast_system.api.routes.exports import router
        
        # Verify router has the expected endpoints
        routes = [route.path for route in router.routes]
        assert "/blast-plans/{blast_id}/export/{format}" in routes
        assert "/blast-plans/export" in routes
        assert "/blast-plans/batch-export" in routes
    
    def test_export_request_validation(self):
        """Test export request validation schemas."""
        from src.drill_blast_system.api.routes.exports import ExportRequest, BatchExportRequest
        
        # Test valid export request
        request = ExportRequest(
            blast_ids=[1, 2, 3],
            format="pdf",
            include_safety_report=True,
            include_hole_details=True,
            include_predictions=True,
            include_measurements=False
        )
        assert request.blast_ids == [1, 2, 3]
        assert request.format == "pdf"
        
        # Test valid batch export request
        batch_request = BatchExportRequest(
            site_id=1,
            blast_status="approved",
            formats=["pdf", "csv"],
            include_templates=False
        )
        assert batch_request.site_id == 1
        assert batch_request.formats == ["pdf", "csv"]


class TestVisualization:
    """Test visualization functionality."""
    
    def test_create_blast_plan_map(self, sample_blast_record):
        """Test creating blast plan map visualization."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        # Test PNG output
        content = viz.create_blast_plan_map(
            sample_blast_record,
            color_by='charge',
            include_labels=True,
            include_legend=True,
            output_format='png'
        )
        
        assert isinstance(content, bytes)
        assert content.startswith(b'\x89PNG')  # PNG header
    
    def test_create_fragmentation_curve(self, sample_blast_record):
        """Test creating fragmentation curve visualization."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        content = viz.create_fragmentation_curve(
            sample_blast_record,
            include_measured=False,
            include_targets=True,
            output_format='png'
        )
        
        assert isinstance(content, bytes)
        assert content.startswith(b'\x89PNG')  # PNG header
    
    def test_create_delay_sequence_visualization(self, sample_blast_record):
        """Test creating delay sequence visualization."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        content = viz.create_delay_sequence_visualization(
            sample_blast_record,
            show_timing=True,
            show_charge_flow=True,
            output_format='png'
        )
        
        assert isinstance(content, bytes)
        assert content.startswith(b'\x89PNG')  # PNG header
    
    def test_create_ppv_contour_map(self, sample_blast_record):
        """Test creating PPV contour map visualization."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        content = viz.create_ppv_contour_map(
            sample_blast_record,
            contour_levels=[1.0, 2.0, 5.0],
            include_receptors=True,
            output_format='png'
        )
        
        assert isinstance(content, bytes)
        assert content.startswith(b'\x89PNG')  # PNG header
    
    def test_create_interactive_visualization_data(self, sample_blast_record):
        """Test creating interactive visualization data."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        data = viz.create_interactive_visualization_data(sample_blast_record)
        
        assert isinstance(data, dict)
        assert 'blast_info' in data
        assert 'holes' in data
        assert 'boundaries' in data
        assert 'statistics' in data
        
        # Verify blast info
        blast_info = data['blast_info']
        assert blast_info['id'] == 1
        assert blast_info['name'] == "Test Blast 001"
        assert blast_info['total_holes'] == 24
        
        # Verify holes data
        assert len(data['holes']) == 2
        hole = data['holes'][0]
        assert 'id' in hole
        assert 'coordinates' in hole
        assert 'properties' in hole
        
        # Verify boundaries
        boundaries = data['boundaries']
        assert 'x_min' in boundaries
        assert 'x_max' in boundaries
        assert 'y_min' in boundaries
        assert 'y_max' in boundaries
    
    def test_visualization_base64_output(self, sample_blast_record):
        """Test base64 output format for visualizations."""
        from src.drill_blast_system.reporting.visualization import BlastVisualization
        
        viz = BlastVisualization()
        
        content = viz.create_blast_plan_map(
            sample_blast_record,
            output_format='base64'
        )
        
        assert isinstance(content, str)
        assert content.startswith('data:image/png;base64,')
    
    def test_report_manager_visualization_integration(self, sample_blast_record):
        """Test visualization integration with report manager."""
        manager = ReportManager()
        
        # Test map visualization
        content = manager.create_visualization(
            sample_blast_record,
            'map',
            {'color_by': 'charge', 'output_format': 'png'}
        )
        assert isinstance(content, bytes)
        
        # Test fragmentation visualization
        content = manager.create_visualization(
            sample_blast_record,
            'fragmentation',
            {'output_format': 'png'}
        )
        assert isinstance(content, bytes)
        
        # Test interactive data
        data = manager.create_visualization(
            sample_blast_record,
            'interactive'
        )
        assert isinstance(data, dict)
        assert 'blast_info' in data


class TestExportValidator:
    """Test export validation functionality."""
    
    def test_validate_csv_export(self, sample_blast_record):
        """Test CSV export validation."""
        from src.drill_blast_system.reporting.export_validator import ExportValidator
        
        validator = ExportValidator()
        
        # Create valid CSV content
        csv_content = b"blast_id,hole_id,x_coordinate,y_coordinate,charge_kg\n1,H001,1000.0,2000.0,35.2\n1,H002,1005.0,2000.0,34.8\n"
        
        is_valid, errors = validator.validate_csv_export(
            csv_content,
            expected_columns=['blast_id', 'hole_id', 'x_coordinate', 'y_coordinate', 'charge_kg'],
            min_rows=1
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_json_export(self, sample_blast_record):
        """Test JSON export validation."""
        from src.drill_blast_system.reporting.export_validator import ExportValidator
        
        validator = ExportValidator()
        
        # Create valid JSON content
        json_data = {
            "export_metadata": {
                "export_timestamp": "2024-01-01T00:00:00",
                "export_version": "1.0",
                "exporter": "test"
            },
            "blast_record": {
                "basic_info": {"id": 1, "blast_name": "Test"}
            }
        }
        json_content = json.dumps(json_data).encode('utf-8')
        
        is_valid, errors = validator.validate_json_export(
            json_content,
            required_fields=['export_metadata', 'blast_record']
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_geojson_export(self, sample_blast_record):
        """Test GeoJSON export validation."""
        from src.drill_blast_system.reporting.export_validator import ExportValidator
        
        validator = ExportValidator()
        
        # Create valid GeoJSON content
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [1000.0, 2000.0]
                    },
                    "properties": {"hole_id": "H001"}
                }
            ]
        }
        geojson_content = json.dumps(geojson_data).encode('utf-8')
        
        is_valid, errors = validator.validate_geojson_export(
            geojson_content,
            expected_feature_count=1
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_pdf_export(self, sample_blast_record):
        """Test PDF export validation."""
        from src.drill_blast_system.reporting.export_validator import ExportValidator
        
        validator = ExportValidator()
        
        # Create minimal valid PDF content
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF'
        
        is_valid, errors = validator.validate_pdf_export(pdf_content)
        
        assert is_valid
        assert len(errors) == 0