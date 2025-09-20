"""
Site repository for site-specific database operations.
Implements requirement 1.7 for site data management.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .base import BaseRepository
from ..models.site import Site
from ..core.logging import get_logger

logger = get_logger(__name__)


class SiteRepository(BaseRepository[Site]):
    """
    Repository for Site entity with specialized query methods.
    
    Provides site-specific database operations including:
    - Site search and filtering
    - Geometry and rock property queries
    - Equipment and constraint management
    """
    
    def __init__(self, db: Session):
        """Initialize site repository."""
        super().__init__(db, Site)
    
    def get_active_sites(self, skip: int = 0, limit: int = 100) -> List[Site]:
        """
        Get all active sites.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active site instances
        """
        return self.find_by_filters(
            filters={"is_active": True},
            skip=skip,
            limit=limit,
            order_by="name"
        )
    
    def get_by_name(self, name: str) -> Optional[Site]:
        """
        Get site by name.
        
        Args:
            name: Site name
            
        Returns:
            Site instance or None if not found
        """
        sites = self.find_by_field("name", name)
        return sites[0] if sites else None
    
    def search_by_name(self, name_pattern: str) -> List[Site]:
        """
        Search sites by name pattern.
        
        Args:
            name_pattern: Name pattern (supports SQL LIKE wildcards)
            
        Returns:
            List of matching sites
        """
        return self.find_by_filters(
            filters={"name": {"like": name_pattern}},
            order_by="name"
        )
    
    def get_by_location(self, location_pattern: str) -> List[Site]:
        """
        Get sites by location pattern.
        
        Args:
            location_pattern: Location pattern (supports SQL LIKE wildcards)
            
        Returns:
            List of matching sites
        """
        return self.find_by_filters(
            filters={"location": {"like": location_pattern}},
            order_by="name"
        )
    
    def get_by_site_type(self, site_type: str) -> List[Site]:
        """
        Get sites by type.
        
        Args:
            site_type: Site type (open_pit, underground, quarry)
            
        Returns:
            List of sites of specified type
        """
        return self.find_by_filters(
            filters={"site_type": site_type, "is_active": True},
            order_by="name"
        )
    
    def get_by_regulatory_zone(self, regulatory_zone: str) -> List[Site]:
        """
        Get sites by regulatory zone.
        
        Args:
            regulatory_zone: Regulatory zone identifier
            
        Returns:
            List of sites in specified regulatory zone
        """
        return self.find_by_filters(
            filters={"regulatory_zone": regulatory_zone, "is_active": True},
            order_by="name"
        )
    
    def get_sites_with_uniform_rock_properties(self) -> List[Site]:
        """
        Get sites that use uniform rock properties.
        
        Returns:
            List of sites with uniform rock properties
        """
        try:
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    Site.rock_properties['is_uniform'].astext.cast(bool) == True
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites with uniform rock properties",
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites with uniform rock properties",
                error=str(e)
            )
            raise
    
    def get_sites_with_block_model(self) -> List[Site]:
        """
        Get sites that use block model rock properties.
        
        Returns:
            List of sites with block model rock properties
        """
        try:
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    Site.rock_properties['is_uniform'].astext.cast(bool) == False
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites with block model rock properties",
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites with block model rock properties",
                error=str(e)
            )
            raise
    
    def get_sites_by_bench_height_range(self, min_height: float, max_height: float) -> List[Site]:
        """
        Get sites by bench height range.
        
        Args:
            min_height: Minimum bench height in meters
            max_height: Maximum bench height in meters
            
        Returns:
            List of sites within bench height range
        """
        try:
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    (
                        Site.bench_geometry['bench_top_elevation'].astext.cast(float) -
                        Site.bench_geometry['bench_bottom_elevation'].astext.cast(float)
                    ) >= min_height,
                    (
                        Site.bench_geometry['bench_top_elevation'].astext.cast(float) -
                        Site.bench_geometry['bench_bottom_elevation'].astext.cast(float)
                    ) <= max_height
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites by bench height range",
                min_height=min_height,
                max_height=max_height,
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites by bench height range",
                min_height=min_height,
                max_height=max_height,
                error=str(e)
            )
            raise
    
    def get_sites_with_explosive_type(self, explosive_name: str) -> List[Site]:
        """
        Get sites that have a specific explosive type available.
        
        Args:
            explosive_name: Name of the explosive
            
        Returns:
            List of sites with the specified explosive
        """
        try:
            # This is a complex JSON query - in a real implementation you might want to
            # use a more efficient approach like a separate explosives table
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    Site.equipment_specs['explosives_catalog'].op('@>')([{"name": explosive_name}])
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites with explosive type",
                explosive_name=explosive_name,
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites with explosive type",
                explosive_name=explosive_name,
                error=str(e)
            )
            raise
    
    def get_sites_with_sensitive_receptors(self) -> List[Site]:
        """
        Get sites that have sensitive receptors defined.
        
        Returns:
            List of sites with sensitive receptors
        """
        try:
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    Site.operational_constraints['sensitive_receptors'].isnot(None),
                    func.json_array_length(Site.operational_constraints['sensitive_receptors']) > 0
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites with sensitive receptors",
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites with sensitive receptors",
                error=str(e)
            )
            raise
    
    def get_sites_by_coordinates_range(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float
    ) -> List[Site]:
        """
        Get sites within geographic coordinate range.
        
        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            
        Returns:
            List of sites within coordinate range
        """
        try:
            sites = self.db.query(Site).filter(
                and_(
                    Site.is_active == True,
                    Site.coordinates.isnot(None),
                    Site.coordinates['latitude'].astext.cast(float) >= min_lat,
                    Site.coordinates['latitude'].astext.cast(float) <= max_lat,
                    Site.coordinates['longitude'].astext.cast(float) >= min_lon,
                    Site.coordinates['longitude'].astext.cast(float) <= max_lon
                )
            ).order_by(Site.name).all()
            
            logger.debug(
                "Retrieved sites by coordinate range",
                min_lat=min_lat,
                max_lat=max_lat,
                min_lon=min_lon,
                max_lon=max_lon,
                count=len(sites)
            )
            
            return sites
            
        except Exception as e:
            logger.error(
                "Failed to get sites by coordinate range",
                error=str(e)
            )
            raise
    
    def validate_site_data(self, site_id: int) -> Dict[str, List[str]]:
        """
        Validate site data for completeness and consistency.
        
        Args:
            site_id: Site ID to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            site = self.get_by_id(site_id)
            if not site:
                return {"errors": ["Site not found"]}
            
            validation_results = {
                "errors": [],
                "warnings": [],
                "info": []
            }
            
            # Validate geometry data
            geometry_errors = site.validate_geometry_data()
            validation_results["errors"].extend(geometry_errors)
            
            # Validate rock properties
            rock_errors = site.validate_rock_properties()
            validation_results["errors"].extend(rock_errors)
            
            # Additional validations
            if not site.equipment_specs or 'drill_rigs' not in site.equipment_specs:
                validation_results["warnings"].append("No drill rigs defined")
            
            if not site.equipment_specs or 'explosives_catalog' not in site.equipment_specs:
                validation_results["warnings"].append("No explosives catalog defined")
            
            # Check for sensitive receptors
            if (site.operational_constraints and 
                'sensitive_receptors' in site.operational_constraints and
                site.operational_constraints['sensitive_receptors']):
                validation_results["info"].append(
                    f"Site has {len(site.operational_constraints['sensitive_receptors'])} sensitive receptors"
                )
            
            logger.info(
                "Site validation completed",
                site_id=site_id,
                errors=len(validation_results["errors"]),
                warnings=len(validation_results["warnings"])
            )
            
            return validation_results
            
        except Exception as e:
            logger.error(
                "Failed to validate site data",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def get_site_statistics(self) -> Dict[str, Any]:
        """
        Get site statistics summary.
        
        Returns:
            Dictionary with site statistics
        """
        try:
            total_sites = self.count()
            active_sites = self.count({"is_active": True})
            
            # Count by site type
            site_types = self.db.query(
                Site.site_type,
                func.count(Site.id).label('count')
            ).filter(Site.is_active == True).group_by(Site.site_type).all()
            
            # Count sites with coordinates
            sites_with_coords = self.db.query(func.count(Site.id)).filter(
                and_(Site.is_active == True, Site.coordinates.isnot(None))
            ).scalar()
            
            statistics = {
                "total_sites": total_sites,
                "active_sites": active_sites,
                "inactive_sites": total_sites - active_sites,
                "sites_with_coordinates": sites_with_coords,
                "sites_by_type": {site_type: count for site_type, count in site_types}
            }
            
            logger.debug("Retrieved site statistics", statistics=statistics)
            
            return statistics
            
        except Exception as e:
            logger.error("Failed to get site statistics", error=str(e))
            raise
    
    def deactivate_site(self, site_id: int) -> bool:
        """
        Deactivate a site (soft delete).
        
        Args:
            site_id: Site ID to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        try:
            updated = self.update(site_id, {"is_active": False})
            
            if updated:
                logger.info("Site deactivated", site_id=site_id)
                return True
            else:
                logger.warning("Site not found for deactivation", site_id=site_id)
                return False
                
        except Exception as e:
            logger.error(
                "Failed to deactivate site",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def reactivate_site(self, site_id: int) -> bool:
        """
        Reactivate a site.
        
        Args:
            site_id: Site ID to reactivate
            
        Returns:
            True if reactivated, False if not found
        """
        try:
            updated = self.update(site_id, {"is_active": True})
            
            if updated:
                logger.info("Site reactivated", site_id=site_id)
                return True
            else:
                logger.warning("Site not found for reactivation", site_id=site_id)
                return False
                
        except Exception as e:
            logger.error(
                "Failed to reactivate site",
                site_id=site_id,
                error=str(e)
            )
            raise