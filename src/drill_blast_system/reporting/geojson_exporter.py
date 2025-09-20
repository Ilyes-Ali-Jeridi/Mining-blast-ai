"""
GeoJSON export functionality for blast plan spatial data.
Implements requirement 7.2: GeoJSON export for GIS integration.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime

from ..models.blast_record import BlastRecord
from ..core.logging import get_logger

logger = get_logger(__name__)


class GeoJSONExporter:
    """Exports blast plan spatial data to GeoJSON format."""
    
    def __init__(self):
        """Initialize GeoJSON exporter."""
        pass
    
    def export_drill_holes(
        self,
        blast_record: BlastRecord,
        include_predictions: bool = True,
        include_measurements: bool = False,
        coordinate_system: str = "local"
    ) -> bytes:
        """
        Export drill holes as GeoJSON point features.
        
        Args:
            blast_record: Blast record to export
            include_predictions: Include prediction results in properties
            include_measurements: Include measurement data in properties
            coordinate_system: Coordinate system ("local", "utm", "wgs84")
            
        Returns:
            GeoJSON content as bytes
        """
        try:
            features = []
            
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                holes = blast_record.plan_data['holes']
                
                for hole in holes:
                    feature = self._build_hole_feature(
                        hole, blast_record, include_predictions, 
                        include_measurements, coordinate_system
                    )
                    features.append(feature)
            
            geojson_data = {
                "type": "FeatureCollection",
                "crs": self._build_crs_definition(coordinate_system),
                "properties": self._build_collection_properties(blast_record),
                "features": features
            }
            
            content = json.dumps(geojson_data, indent=2).encode('utf-8')
            
            logger.info(
                "Drill holes exported to GeoJSON",
                blast_id=blast_record.id,
                hole_count=len(features),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export drill holes to GeoJSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_blast_boundary(
        self,
        blast_record: BlastRecord,
        coordinate_system: str = "local"
    ) -> bytes:
        """
        Export blast boundary as GeoJSON polygon feature.
        
        Args:
            blast_record: Blast record to export
            coordinate_system: Coordinate system ("local", "utm", "wgs84")
            
        Returns:
            GeoJSON content as bytes
        """
        try:
            features = []
            
            # Calculate blast boundary from hole positions
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                boundary_coords = self._calculate_blast_boundary(blast_record.plan_data['holes'])
                
                if boundary_coords:
                    boundary_feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [boundary_coords]
                        },
                        "properties": {
                            "feature_type": "blast_boundary",
                            "blast_id": blast_record.id,
                            "blast_name": blast_record.blast_name,
                            "total_holes": blast_record.total_holes,
                            "blast_area_m2": blast_record.plan_data.get('blast_geometry', {}).get('blast_area', 0),
                            "perimeter_m": self._calculate_perimeter(boundary_coords)
                        }
                    }
                    features.append(boundary_feature)
            
            geojson_data = {
                "type": "FeatureCollection",
                "crs": self._build_crs_definition(coordinate_system),
                "properties": self._build_collection_properties(blast_record),
                "features": features
            }
            
            content = json.dumps(geojson_data, indent=2).encode('utf-8')
            
            logger.info(
                "Blast boundary exported to GeoJSON",
                blast_id=blast_record.id,
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export blast boundary to GeoJSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_delay_sequence(
        self,
        blast_record: BlastRecord,
        coordinate_system: str = "local"
    ) -> bytes:
        """
        Export delay sequence as GeoJSON with timing information.
        
        Args:
            blast_record: Blast record to export
            coordinate_system: Coordinate system ("local", "utm", "wgs84")
            
        Returns:
            GeoJSON content as bytes
        """
        try:
            features = []
            
            if blast_record.plan_data and 'holes' in blast_record.plan_data:
                holes = blast_record.plan_data['holes']
                
                # Group holes by delay
                holes_by_delay = {}
                for hole in holes:
                    delay = hole.get('delay_ms', 0)
                    if delay not in holes_by_delay:
                        holes_by_delay[delay] = []
                    holes_by_delay[delay].append(hole)
                
                # Create features for each delay group
                for delay_ms, delay_holes in holes_by_delay.items():
                    # Create point features for holes in this delay
                    for hole in delay_holes:
                        feature = self._build_delay_hole_feature(hole, delay_ms, coordinate_system)
                        features.append(feature)
                    
                    # Create polygon feature for delay group if multiple holes
                    if len(delay_holes) > 2:
                        delay_polygon = self._build_delay_polygon_feature(
                            delay_holes, delay_ms, blast_record
                        )
                        if delay_polygon:
                            features.append(delay_polygon)
            
            geojson_data = {
                "type": "FeatureCollection",
                "crs": self._build_crs_definition(coordinate_system),
                "properties": {
                    **self._build_collection_properties(blast_record),
                    "export_type": "delay_sequence",
                    "total_delays": len(set(hole.get('delay_ms', 0) for hole in blast_record.plan_data.get('holes', [])))
                },
                "features": features
            }
            
            content = json.dumps(geojson_data, indent=2).encode('utf-8')
            
            logger.info(
                "Delay sequence exported to GeoJSON",
                blast_id=blast_record.id,
                feature_count=len(features),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export delay sequence to GeoJSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def export_ppv_contours(
        self,
        blast_record: BlastRecord,
        contour_levels: Optional[List[float]] = None,
        coordinate_system: str = "local"
    ) -> bytes:
        """
        Export PPV contours as GeoJSON polygon features.
        
        Args:
            blast_record: Blast record to export
            contour_levels: PPV levels for contours (mm/s)
            coordinate_system: Coordinate system ("local", "utm", "wgs84")
            
        Returns:
            GeoJSON content as bytes
        """
        try:
            if contour_levels is None:
                contour_levels = [1.0, 2.0, 5.0, 10.0, 20.0]  # Default PPV levels
            
            features = []
            
            # Calculate blast center
            blast_center = self._calculate_blast_center(blast_record)
            if not blast_center:
                raise ValueError("Cannot calculate blast center - no hole data available")
            
            # Create contour features
            for ppv_level in contour_levels:
                contour_feature = self._build_ppv_contour_feature(
                    blast_center, ppv_level, blast_record, coordinate_system
                )
                if contour_feature:
                    features.append(contour_feature)
            
            # Add receptor points if available
            if blast_record.predicted_results and 'ppv_predictions' in blast_record.predicted_results:
                receptors = blast_record.predicted_results['ppv_predictions'].get('receptor_predictions', [])
                for receptor in receptors:
                    receptor_feature = self._build_receptor_feature(receptor, coordinate_system)
                    features.append(receptor_feature)
            
            geojson_data = {
                "type": "FeatureCollection",
                "crs": self._build_crs_definition(coordinate_system),
                "properties": {
                    **self._build_collection_properties(blast_record),
                    "export_type": "ppv_contours",
                    "contour_levels": contour_levels,
                    "blast_center": blast_center
                },
                "features": features
            }
            
            content = json.dumps(geojson_data, indent=2).encode('utf-8')
            
            logger.info(
                "PPV contours exported to GeoJSON",
                blast_id=blast_record.id,
                contour_count=len(contour_levels),
                size_bytes=len(content)
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Failed to export PPV contours to GeoJSON",
                blast_id=blast_record.id,
                error=str(e)
            )
            raise
    
    def _build_hole_feature(
        self,
        hole: Dict[str, Any],
        blast_record: BlastRecord,
        include_predictions: bool,
        include_measurements: bool,
        coordinate_system: str
    ) -> Dict[str, Any]:
        """Build GeoJSON feature for a drill hole."""
        coords = hole.get('coordinates', {})
        
        # Convert coordinates if needed
        geometry_coords = self._convert_coordinates(
            coords.get('x', 0), coords.get('y', 0), coords.get('z', 0), coordinate_system
        )
        
        properties = {
            "feature_type": "drill_hole",
            "blast_id": blast_record.id,
            "blast_name": blast_record.blast_name,
            "hole_id": hole.get('hole_id', ''),
            "depth": hole.get('depth', 0),
            "diameter": hole.get('diameter', 0),
            "charge_kg": hole.get('charge_kg', 0),
            "stemming_m": hole.get('stemming_m', 0),
            "delay_ms": hole.get('delay_ms', 0),
            "explosive_type": hole.get('explosive_type', ''),
            "drill_rig": hole.get('drill_rig', ''),
            "burden": hole.get('burden', 0),
            "spacing": hole.get('spacing', 0),
            "collar_elevation": hole.get('collar_elevation', 0),
            "toe_elevation": hole.get('toe_elevation', 0)
        }
        
        if include_predictions:
            properties.update({
                "predicted_fragment_contribution": blast_record.predicted_p80 or 0,
                "predicted_ppv_contribution": 0  # TODO: Calculate hole-specific PPV
            })
        
        if include_measurements:
            properties.update({
                "measured_fragment_contribution": blast_record.measured_p80 or 0,
                "measured_ppv_contribution": 0  # TODO: Get hole-specific measurements
            })
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": geometry_coords
            },
            "properties": properties
        }
    
    def _build_delay_hole_feature(
        self,
        hole: Dict[str, Any],
        delay_ms: int,
        coordinate_system: str
    ) -> Dict[str, Any]:
        """Build GeoJSON feature for a hole in delay sequence."""
        coords = hole.get('coordinates', {})
        geometry_coords = self._convert_coordinates(
            coords.get('x', 0), coords.get('y', 0), coords.get('z', 0), coordinate_system
        )
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": geometry_coords
            },
            "properties": {
                "feature_type": "delay_hole",
                "hole_id": hole.get('hole_id', ''),
                "delay_ms": delay_ms,
                "delay_sequence": delay_ms // 25 if delay_ms > 0 else 0,  # Approximate sequence number
                "charge_kg": hole.get('charge_kg', 0),
                "explosive_type": hole.get('explosive_type', '')
            }
        }
    
    def _build_delay_polygon_feature(
        self,
        delay_holes: List[Dict[str, Any]],
        delay_ms: int,
        blast_record: BlastRecord
    ) -> Optional[Dict[str, Any]]:
        """Build polygon feature for a delay group."""
        if len(delay_holes) < 3:
            return None
        
        # Calculate convex hull of hole positions
        hole_coords = []
        for hole in delay_holes:
            coords = hole.get('coordinates', {})
            hole_coords.append([coords.get('x', 0), coords.get('y', 0)])
        
        # Simple convex hull calculation (for production, use proper algorithm)
        hull_coords = self._calculate_convex_hull(hole_coords)
        if len(hull_coords) < 3:
            return None
        
        # Close the polygon
        hull_coords.append(hull_coords[0])
        
        total_charge = sum(hole.get('charge_kg', 0) for hole in delay_holes)
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [hull_coords]
            },
            "properties": {
                "feature_type": "delay_polygon",
                "blast_id": blast_record.id,
                "delay_ms": delay_ms,
                "delay_sequence": delay_ms // 25 if delay_ms > 0 else 0,
                "hole_count": len(delay_holes),
                "total_charge_kg": total_charge,
                "area_m2": self._calculate_polygon_area(hull_coords)
            }
        }
    
    def _build_ppv_contour_feature(
        self,
        blast_center: Tuple[float, float],
        ppv_level: float,
        blast_record: BlastRecord,
        coordinate_system: str
    ) -> Optional[Dict[str, Any]]:
        """Build PPV contour feature."""
        # Simplified circular contour calculation
        # In practice, this would use proper PPV modeling
        
        total_charge = blast_record.total_explosive
        if total_charge <= 0:
            return None
        
        # Simple scaled distance calculation for contour radius
        # PPV = k * (W^a / R^b), solve for R
        k, a, b = 1.4, 1/3, 1.6  # Default PPV constants
        
        try:
            radius = ((k * (total_charge ** a)) / ppv_level) ** (1/b)
        except (ZeroDivisionError, ValueError):
            return None
        
        # Create circular contour
        contour_coords = []
        import math
        for angle in range(0, 361, 10):  # 10-degree increments
            rad = math.radians(angle)
            x = blast_center[0] + radius * math.cos(rad)
            y = blast_center[1] + radius * math.sin(rad)
            contour_coords.append([x, y])
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [contour_coords]
            },
            "properties": {
                "feature_type": "ppv_contour",
                "blast_id": blast_record.id,
                "ppv_level": ppv_level,
                "radius_m": radius,
                "total_charge_kg": total_charge,
                "model_parameters": {"k": k, "a": a, "b": b}
            }
        }
    
    def _build_receptor_feature(
        self,
        receptor: Dict[str, Any],
        coordinate_system: str
    ) -> Dict[str, Any]:
        """Build receptor point feature."""
        coords = receptor.get('coordinates', {})
        geometry_coords = self._convert_coordinates(
            coords.get('x', 0), coords.get('y', 0), coords.get('z', 0), coordinate_system
        )
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": geometry_coords
            },
            "properties": {
                "feature_type": "ppv_receptor",
                "receptor_name": receptor.get('receptor_name', ''),
                "predicted_ppv": receptor.get('predicted_ppv', 0),
                "distance_to_blast": receptor.get('distance_to_blast', 0),
                "safety_margin": receptor.get('safety_margin', 0)
            }
        }
    
    def _build_crs_definition(self, coordinate_system: str) -> Dict[str, Any]:
        """Build CRS definition for coordinate system."""
        if coordinate_system == "wgs84":
            return {
                "type": "name",
                "properties": {
                    "name": "EPSG:4326"
                }
            }
        elif coordinate_system == "utm":
            return {
                "type": "name",
                "properties": {
                    "name": "EPSG:32633"  # UTM Zone 33N - adjust as needed
                }
            }
        else:  # local
            return {
                "type": "name",
                "properties": {
                    "name": "LOCAL_GRID"
                }
            }
    
    def _build_collection_properties(self, blast_record: BlastRecord) -> Dict[str, Any]:
        """Build properties for the feature collection."""
        return {
            "blast_id": blast_record.id,
            "blast_name": blast_record.blast_name,
            "site_id": blast_record.site_id,
            "blast_status": blast_record.blast_status.value,
            "total_holes": blast_record.total_holes,
            "total_explosive_kg": blast_record.total_explosive,
            "export_timestamp": datetime.utcnow().isoformat(),
            "coordinate_system": "local"  # Default
        }
    
    def _convert_coordinates(
        self,
        x: float,
        y: float,
        z: float,
        coordinate_system: str
    ) -> List[float]:
        """Convert coordinates to specified system."""
        # For now, just return as-is
        # In production, implement proper coordinate transformations
        if coordinate_system == "local":
            return [x, y, z] if z != 0 else [x, y]
        else:
            # TODO: Implement coordinate transformations
            return [x, y, z] if z != 0 else [x, y]
    
    def _calculate_blast_boundary(self, holes: List[Dict[str, Any]]) -> List[List[float]]:
        """Calculate blast boundary from hole positions."""
        if not holes:
            return []
        
        # Extract coordinates
        coords = []
        for hole in holes:
            hole_coords = hole.get('coordinates', {})
            coords.append([hole_coords.get('x', 0), hole_coords.get('y', 0)])
        
        if len(coords) < 3:
            return []
        
        # Calculate convex hull
        hull = self._calculate_convex_hull(coords)
        
        # Close the polygon
        if hull and hull[0] != hull[-1]:
            hull.append(hull[0])
        
        return hull
    
    def _calculate_convex_hull(self, points: List[List[float]]) -> List[List[float]]:
        """Calculate convex hull of points (simplified implementation)."""
        if len(points) < 3:
            return points
        
        # Sort points lexicographically
        points = sorted(set(tuple(p) for p in points))
        if len(points) <= 1:
            return [list(p) for p in points]
        
        # Build lower hull
        lower = []
        for p in points:
            while len(lower) >= 2 and self._cross_product(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        
        # Build upper hull
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and self._cross_product(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        
        # Remove last point of each half because it's repeated
        return [list(p) for p in lower[:-1] + upper[:-1]]
    
    def _cross_product(self, o: tuple, a: tuple, b: tuple) -> float:
        """Calculate cross product for convex hull."""
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    
    def _calculate_blast_center(self, blast_record: BlastRecord) -> Optional[Tuple[float, float]]:
        """Calculate center point of blast."""
        if not blast_record.plan_data or 'holes' not in blast_record.plan_data:
            return None
        
        holes = blast_record.plan_data['holes']
        if not holes:
            return None
        
        # Calculate weighted center based on charge
        total_charge = 0
        weighted_x = 0
        weighted_y = 0
        
        for hole in holes:
            coords = hole.get('coordinates', {})
            charge = hole.get('charge_kg', 0)
            
            if charge > 0:
                weighted_x += coords.get('x', 0) * charge
                weighted_y += coords.get('y', 0) * charge
                total_charge += charge
        
        if total_charge > 0:
            return (weighted_x / total_charge, weighted_y / total_charge)
        else:
            # Fallback to geometric center
            x_coords = [hole.get('coordinates', {}).get('x', 0) for hole in holes]
            y_coords = [hole.get('coordinates', {}).get('y', 0) for hole in holes]
            return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
    
    def _calculate_perimeter(self, coords: List[List[float]]) -> float:
        """Calculate perimeter of polygon."""
        if len(coords) < 2:
            return 0
        
        perimeter = 0
        for i in range(len(coords)):
            j = (i + 1) % len(coords)
            dx = coords[j][0] - coords[i][0]
            dy = coords[j][1] - coords[i][1]
            perimeter += (dx * dx + dy * dy) ** 0.5
        
        return perimeter
    
    def _calculate_polygon_area(self, coords: List[List[float]]) -> float:
        """Calculate area of polygon using shoelace formula."""
        if len(coords) < 3:
            return 0
        
        area = 0
        n = len(coords)
        
        for i in range(n):
            j = (i + 1) % n
            area += coords[i][0] * coords[j][1]
            area -= coords[j][0] * coords[i][1]
        
        return abs(area) / 2