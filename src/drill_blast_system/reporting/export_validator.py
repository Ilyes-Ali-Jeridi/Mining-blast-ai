"""
Export format validation utilities.
Implements requirement 7.2: Add export format validation and testing.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
import json
import csv
import io
from datetime import datetime
from pathlib import Path

from ..core.logging import get_logger

logger = get_logger(__name__)


class ExportValidator:
    """Validates exported data formats and content."""
    
    def __init__(self):
        """Initialize export validator."""
        pass
    
    def validate_csv_export(
        self,
        csv_content: bytes,
        expected_columns: Optional[List[str]] = None,
        min_rows: int = 0,
        max_rows: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate CSV export format and content.
        
        Args:
            csv_content: CSV content as bytes
            expected_columns: Expected column names
            min_rows: Minimum number of data rows (excluding header)
            max_rows: Maximum number of data rows
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        try:
            # Decode content
            csv_text = csv_content.decode('utf-8')
            
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(csv_text))
            rows = list(csv_reader)
            
            if not rows:
                errors.append("CSV file is empty")
                return False, errors
            
            # Validate header
            header = rows[0]
            if expected_columns:
                missing_columns = set(expected_columns) - set(header)
                if missing_columns:
                    errors.append(f"Missing expected columns: {missing_columns}")
                
                extra_columns = set(header) - set(expected_columns)
                if extra_columns:
                    errors.append(f"Unexpected columns found: {extra_columns}")
            
            # Validate row count
            data_rows = len(rows) - 1  # Exclude header
            
            if data_rows < min_rows:
                errors.append(f"Insufficient data rows: {data_rows} < {min_rows}")
            
            if max_rows and data_rows > max_rows:
                errors.append(f"Too many data rows: {data_rows} > {max_rows}")
            
            # Validate data consistency
            expected_columns_count = len(header)
            for i, row in enumerate(rows[1:], 1):  # Skip header
                if len(row) != expected_columns_count:
                    errors.append(f"Row {i} has {len(row)} columns, expected {expected_columns_count}")
            
            # Check for empty critical fields
            if expected_columns:
                critical_fields = ['blast_id', 'hole_id', 'x_coordinate', 'y_coordinate']
                critical_indices = []
                
                for field in critical_fields:
                    if field in header:
                        critical_indices.append(header.index(field))
                
                for i, row in enumerate(rows[1:], 1):
                    for idx in critical_indices:
                        if idx < len(row) and not row[idx].strip():
                            field_name = header[idx]
                            errors.append(f"Row {i}: Critical field '{field_name}' is empty")
            
            logger.info(
                "CSV validation completed",
                is_valid=len(errors) == 0,
                total_rows=len(rows),
                data_rows=data_rows,
                error_count=len(errors)
            )
            
            return len(errors) == 0, errors
            
        except UnicodeDecodeError as e:
            errors.append(f"CSV encoding error: {e}")
            return False, errors
        except csv.Error as e:
            errors.append(f"CSV parsing error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
            return False, errors
    
    def validate_json_export(
        self,
        json_content: bytes,
        required_fields: Optional[List[str]] = None,
        schema_validation: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate JSON export format and content.
        
        Args:
            json_content: JSON content as bytes
            required_fields: Required top-level fields
            schema_validation: Perform schema validation
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        try:
            # Decode and parse JSON
            json_text = json_content.decode('utf-8')
            data = json.loads(json_text)
            
            # Validate required fields
            if required_fields:
                missing_fields = set(required_fields) - set(data.keys())
                if missing_fields:
                    errors.append(f"Missing required fields: {missing_fields}")
            
            # Validate basic structure
            if schema_validation:
                errors.extend(self._validate_json_schema(data))
            
            # Validate data types and ranges
            errors.extend(self._validate_json_data_types(data))
            
            logger.info(
                "JSON validation completed",
                is_valid=len(errors) == 0,
                data_size=len(json_text),
                error_count=len(errors)
            )
            
            return len(errors) == 0, errors
            
        except UnicodeDecodeError as e:
            errors.append(f"JSON encoding error: {e}")
            return False, errors
        except json.JSONDecodeError as e:
            errors.append(f"JSON parsing error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
            return False, errors
    
    def validate_geojson_export(
        self,
        geojson_content: bytes,
        expected_feature_count: Optional[int] = None,
        validate_geometry: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate GeoJSON export format and content.
        
        Args:
            geojson_content: GeoJSON content as bytes
            expected_feature_count: Expected number of features
            validate_geometry: Validate geometry coordinates
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        try:
            # Decode and parse GeoJSON
            geojson_text = geojson_content.decode('utf-8')
            data = json.loads(geojson_text)
            
            # Validate GeoJSON structure
            if data.get('type') != 'FeatureCollection':
                errors.append("GeoJSON must be a FeatureCollection")
                return False, errors
            
            features = data.get('features', [])
            if not isinstance(features, list):
                errors.append("Features must be a list")
                return False, errors
            
            # Validate feature count
            if expected_feature_count is not None:
                if len(features) != expected_feature_count:
                    errors.append(
                        f"Feature count mismatch: {len(features)} != {expected_feature_count}"
                    )
            
            # Validate each feature
            for i, feature in enumerate(features):
                feature_errors = self._validate_geojson_feature(feature, i, validate_geometry)
                errors.extend(feature_errors)
            
            # Validate CRS if present
            if 'crs' in data:
                crs_errors = self._validate_geojson_crs(data['crs'])
                errors.extend(crs_errors)
            
            logger.info(
                "GeoJSON validation completed",
                is_valid=len(errors) == 0,
                feature_count=len(features),
                error_count=len(errors)
            )
            
            return len(errors) == 0, errors
            
        except UnicodeDecodeError as e:
            errors.append(f"GeoJSON encoding error: {e}")
            return False, errors
        except json.JSONDecodeError as e:
            errors.append(f"GeoJSON parsing error: {e}")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
            return False, errors
    
    def validate_pdf_export(
        self,
        pdf_content: bytes,
        min_size_bytes: int = 1000,
        max_size_bytes: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate PDF export format and basic properties.
        
        Args:
            pdf_content: PDF content as bytes
            min_size_bytes: Minimum expected file size
            max_size_bytes: Maximum expected file size
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        try:
            # Check file size
            size = len(pdf_content)
            
            if size < min_size_bytes:
                errors.append(f"PDF file too small: {size} < {min_size_bytes} bytes")
            
            if max_size_bytes and size > max_size_bytes:
                errors.append(f"PDF file too large: {size} > {max_size_bytes} bytes")
            
            # Check PDF header
            if not pdf_content.startswith(b'%PDF-'):
                errors.append("Invalid PDF header")
            
            # Check PDF trailer
            if b'%%EOF' not in pdf_content[-100:]:
                errors.append("Missing PDF trailer")
            
            # Basic structure validation
            if b'/Type /Catalog' not in pdf_content:
                errors.append("Missing PDF catalog")
            
            logger.info(
                "PDF validation completed",
                is_valid=len(errors) == 0,
                file_size=size,
                error_count=len(errors)
            )
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
            return False, errors
    
    def validate_export_completeness(
        self,
        export_content: bytes,
        blast_record_data: Dict[str, Any],
        export_format: str,
        export_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate that export contains expected data from blast record.
        
        Args:
            export_content: Exported content as bytes
            blast_record_data: Original blast record data
            export_format: Export format (csv, json, geojson, pdf)
            export_type: Export type (hole_data, complete_report, etc.)
            
        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []
        
        try:
            if export_format.lower() == 'json':
                # Parse JSON and check data completeness
                data = json.loads(export_content.decode('utf-8'))
                errors.extend(self._validate_json_completeness(data, blast_record_data, export_type))
                
            elif export_format.lower() == 'csv':
                # Parse CSV and check data completeness
                csv_text = export_content.decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(csv_text))
                rows = list(csv_reader)
                errors.extend(self._validate_csv_completeness(rows, blast_record_data, export_type))
                
            elif export_format.lower() == 'geojson':
                # Parse GeoJSON and check spatial data completeness
                data = json.loads(export_content.decode('utf-8'))
                errors.extend(self._validate_geojson_completeness(data, blast_record_data, export_type))
                
            elif export_format.lower() == 'pdf':
                # Basic PDF content validation
                errors.extend(self._validate_pdf_completeness(export_content, blast_record_data))
            
            logger.info(
                "Export completeness validation completed",
                is_valid=len(errors) == 0,
                export_format=export_format,
                export_type=export_type,
                error_count=len(errors)
            )
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Completeness validation error: {e}")
            return False, errors
    
    def _validate_json_schema(self, data: Dict[str, Any]) -> List[str]:
        """Validate JSON schema structure."""
        errors = []
        
        # Check for export metadata
        if 'export_metadata' not in data:
            errors.append("Missing export_metadata section")
        else:
            metadata = data['export_metadata']
            required_metadata = ['export_timestamp', 'export_version', 'exporter']
            for field in required_metadata:
                if field not in metadata:
                    errors.append(f"Missing metadata field: {field}")
        
        # Check blast record structure if present
        if 'blast_record' in data:
            blast_record = data['blast_record']
            if 'basic_info' not in blast_record:
                errors.append("Missing blast_record.basic_info section")
        
        return errors
    
    def _validate_json_data_types(self, data: Dict[str, Any]) -> List[str]:
        """Validate JSON data types and ranges."""
        errors = []
        
        # Validate numeric fields
        numeric_fields = [
            ('total_holes', int, 0, 10000),
            ('total_explosive', (int, float), 0, 1000000),
            ('powder_factor', (int, float), 0, 10)
        ]
        
        def check_nested_field(obj, path):
            keys = path.split('.')
            current = obj
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        
        for field_path, expected_type, min_val, max_val in numeric_fields:
            value = check_nested_field(data, field_path)
            if value is not None:
                if not isinstance(value, expected_type):
                    errors.append(f"Field {field_path} has wrong type: {type(value)} != {expected_type}")
                elif isinstance(value, (int, float)):
                    if value < min_val or value > max_val:
                        errors.append(f"Field {field_path} out of range: {value} not in [{min_val}, {max_val}]")
        
        return errors
    
    def _validate_geojson_feature(
        self,
        feature: Dict[str, Any],
        index: int,
        validate_geometry: bool
    ) -> List[str]:
        """Validate individual GeoJSON feature."""
        errors = []
        
        # Check feature structure
        if feature.get('type') != 'Feature':
            errors.append(f"Feature {index}: Invalid type, expected 'Feature'")
        
        if 'geometry' not in feature:
            errors.append(f"Feature {index}: Missing geometry")
        elif validate_geometry:
            geometry = feature['geometry']
            geom_errors = self._validate_geojson_geometry(geometry, index)
            errors.extend(geom_errors)
        
        if 'properties' not in feature:
            errors.append(f"Feature {index}: Missing properties")
        
        return errors
    
    def _validate_geojson_geometry(self, geometry: Dict[str, Any], feature_index: int) -> List[str]:
        """Validate GeoJSON geometry."""
        errors = []
        
        geom_type = geometry.get('type')
        coordinates = geometry.get('coordinates')
        
        if not geom_type:
            errors.append(f"Feature {feature_index}: Missing geometry type")
            return errors
        
        if coordinates is None:
            errors.append(f"Feature {feature_index}: Missing coordinates")
            return errors
        
        # Validate coordinates based on geometry type
        if geom_type == 'Point':
            if not isinstance(coordinates, list) or len(coordinates) < 2:
                errors.append(f"Feature {feature_index}: Invalid Point coordinates")
        elif geom_type == 'Polygon':
            if not isinstance(coordinates, list) or not coordinates:
                errors.append(f"Feature {feature_index}: Invalid Polygon coordinates")
            else:
                for ring in coordinates:
                    if not isinstance(ring, list) or len(ring) < 4:
                        errors.append(f"Feature {feature_index}: Invalid Polygon ring")
        
        return errors
    
    def _validate_geojson_crs(self, crs: Dict[str, Any]) -> List[str]:
        """Validate GeoJSON CRS definition."""
        errors = []
        
        if 'type' not in crs:
            errors.append("CRS missing type")
        
        if 'properties' not in crs:
            errors.append("CRS missing properties")
        
        return errors
    
    def _validate_json_completeness(
        self,
        data: Dict[str, Any],
        blast_record_data: Dict[str, Any],
        export_type: str
    ) -> List[str]:
        """Validate JSON export completeness."""
        errors = []
        
        # Check blast ID consistency
        exported_id = None
        if 'blast_record' in data and 'basic_info' in data['blast_record']:
            exported_id = data['blast_record']['basic_info'].get('id')
        elif 'blast_id' in data:
            exported_id = data['blast_id']
        
        expected_id = blast_record_data.get('id')
        if exported_id != expected_id:
            errors.append(f"Blast ID mismatch: {exported_id} != {expected_id}")
        
        # Check hole count for hole data exports
        if export_type == 'hole_data':
            exported_holes = 0
            if 'holes' in data:
                exported_holes = len(data['holes'])
            elif 'blast_record' in data and 'plan_data' in data['blast_record']:
                plan_data = data['blast_record']['plan_data']
                if 'holes' in plan_data:
                    exported_holes = len(plan_data['holes'])
            
            expected_holes = blast_record_data.get('total_holes', 0)
            if exported_holes != expected_holes:
                errors.append(f"Hole count mismatch: {exported_holes} != {expected_holes}")
        
        return errors
    
    def _validate_csv_completeness(
        self,
        rows: List[Dict[str, Any]],
        blast_record_data: Dict[str, Any],
        export_type: str
    ) -> List[str]:
        """Validate CSV export completeness."""
        errors = []
        
        if export_type == 'hole_data':
            expected_holes = blast_record_data.get('total_holes', 0)
            if len(rows) != expected_holes:
                errors.append(f"CSV hole count mismatch: {len(rows)} != {expected_holes}")
        
        # Check for consistent blast_id in all rows
        if rows:
            expected_id = blast_record_data.get('id')
            for i, row in enumerate(rows):
                if 'blast_id' in row and str(row['blast_id']) != str(expected_id):
                    errors.append(f"Row {i}: Blast ID mismatch")
        
        return errors
    
    def _validate_geojson_completeness(
        self,
        data: Dict[str, Any],
        blast_record_data: Dict[str, Any],
        export_type: str
    ) -> List[str]:
        """Validate GeoJSON export completeness."""
        errors = []
        
        features = data.get('features', [])
        
        if export_type == 'hole_data':
            expected_holes = blast_record_data.get('total_holes', 0)
            if len(features) != expected_holes:
                errors.append(f"GeoJSON feature count mismatch: {len(features)} != {expected_holes}")
        
        # Check blast_id in properties
        expected_id = blast_record_data.get('id')
        collection_props = data.get('properties', {})
        if 'blast_id' in collection_props and collection_props['blast_id'] != expected_id:
            errors.append("Collection blast_id mismatch")
        
        return errors
    
    def _validate_pdf_completeness(
        self,
        pdf_content: bytes,
        blast_record_data: Dict[str, Any]
    ) -> List[str]:
        """Validate PDF export completeness."""
        errors = []
        
        # Basic content checks
        blast_name = blast_record_data.get('blast_name', '')
        if blast_name and blast_name.encode('utf-8') not in pdf_content:
            errors.append("Blast name not found in PDF content")
        
        # Check for key sections (simplified)
        required_sections = [b'Safety', b'Hole', b'Prediction']
        for section in required_sections:
            if section not in pdf_content:
                errors.append(f"PDF missing section: {section.decode('utf-8')}")
        
        return errors