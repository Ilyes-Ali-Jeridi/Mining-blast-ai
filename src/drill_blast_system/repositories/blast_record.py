"""
Blast record repository for blast-specific database operations.
Implements requirement 1.8 for historical blast plans and results storage.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from .base import BaseRepository
from ..models.blast_record import BlastRecord, BlastStatus
from ..core.logging import get_logger

logger = get_logger(__name__)


class BlastRecordRepository(BaseRepository[BlastRecord]):
    """
    Repository for BlastRecord entity with specialized query methods.
    
    Provides blast record-specific database operations including:
    - Blast plan management and versioning
    - Status-based filtering and workflows
    - Performance analysis and reporting
    - Safety validation tracking
    """
    
    def __init__(self, db: Session):
        """Initialize blast record repository."""
        super().__init__(db, BlastRecord)
    
    def get_by_site_id(self, site_id: int, skip: int = 0, limit: int = 100) -> List[BlastRecord]:
        """
        Get blast records for a specific site.
        
        Args:
            site_id: Site ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of blast records for the site
        """
        return self.find_by_filters(
            filters={"site_id": site_id},
            skip=skip,
            limit=limit,
            order_by="created_at",
            order_desc=True
        )
    
    def get_by_status(self, status: BlastStatus, skip: int = 0, limit: int = 100) -> List[BlastRecord]:
        """
        Get blast records by status.
        
        Args:
            status: Blast status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of blast records with specified status
        """
        return self.find_by_filters(
            filters={"blast_status": status},
            skip=skip,
            limit=limit,
            order_by="created_at",
            order_desc=True
        )
    
    def get_by_name_pattern(self, name_pattern: str) -> List[BlastRecord]:
        """
        Search blast records by name pattern.
        
        Args:
            name_pattern: Name pattern (supports SQL LIKE wildcards)
            
        Returns:
            List of matching blast records
        """
        return self.find_by_filters(
            filters={"blast_name": {"like": name_pattern}},
            order_by="blast_name"
        )
    
    def get_pending_review(self) -> List[BlastRecord]:
        """
        Get blast records pending engineer review.
        
        Returns:
            List of blast records pending review
        """
        return self.get_by_status(BlastStatus.PENDING_REVIEW)
    
    def get_approved_blasts(self, site_id: Optional[int] = None) -> List[BlastRecord]:
        """
        Get approved blast records ready for execution.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            List of approved blast records
        """
        filters = {"blast_status": BlastStatus.APPROVED}
        if site_id:
            filters["site_id"] = site_id
            
        return self.find_by_filters(
            filters=filters,
            order_by="planned_execution_date"
        )
    
    def get_executed_blasts(
        self,
        site_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[BlastRecord]:
        """
        Get executed blast records with optional date filtering.
        
        Args:
            site_id: Optional site ID filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of executed blast records
        """
        try:
            query = self.db.query(BlastRecord).filter(
                BlastRecord.blast_status == BlastStatus.EXECUTED
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            if start_date:
                query = query.filter(BlastRecord.actual_execution_date >= start_date)
            
            if end_date:
                query = query.filter(BlastRecord.actual_execution_date <= end_date)
            
            blasts = query.order_by(desc(BlastRecord.actual_execution_date)).all()
            
            logger.debug(
                "Retrieved executed blasts",
                site_id=site_id,
                start_date=start_date,
                end_date=end_date,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get executed blasts",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def get_blasts_with_measurements(self, site_id: Optional[int] = None) -> List[BlastRecord]:
        """
        Get blast records that have post-blast measurements.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            List of blast records with measurements
        """
        try:
            query = self.db.query(BlastRecord).filter(
                BlastRecord.blast_status == BlastStatus.MEASURED
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            blasts = query.order_by(desc(BlastRecord.actual_execution_date)).all()
            
            logger.debug(
                "Retrieved blasts with measurements",
                site_id=site_id,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get blasts with measurements",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def get_templates(self, site_id: Optional[int] = None) -> List[BlastRecord]:
        """
        Get blast record templates.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            List of blast record templates
        """
        filters = {"is_template": True}
        if site_id:
            filters["site_id"] = site_id
            
        return self.find_by_filters(
            filters=filters,
            order_by="blast_name"
        )
    
    def get_blast_revisions(self, parent_blast_id: int) -> List[BlastRecord]:
        """
        Get all revisions of a blast record.
        
        Args:
            parent_blast_id: Parent blast record ID
            
        Returns:
            List of blast record revisions
        """
        return self.find_by_filters(
            filters={"parent_blast_id": parent_blast_id},
            order_by="plan_version"
        )
    
    def get_latest_version(self, blast_name: str, site_id: int) -> Optional[BlastRecord]:
        """
        Get the latest version of a blast record by name and site.
        
        Args:
            blast_name: Base blast name
            site_id: Site ID
            
        Returns:
            Latest version of the blast record or None
        """
        try:
            blast = self.db.query(BlastRecord).filter(
                and_(
                    BlastRecord.site_id == site_id,
                    or_(
                        BlastRecord.blast_name == blast_name,
                        BlastRecord.blast_name.like(f"{blast_name} (Rev %)")
                    )
                )
            ).order_by(desc(BlastRecord.plan_version)).first()
            
            logger.debug(
                "Retrieved latest blast version",
                blast_name=blast_name,
                site_id=site_id,
                found=blast is not None
            )
            
            return blast
            
        except Exception as e:
            logger.error(
                "Failed to get latest blast version",
                blast_name=blast_name,
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def get_blasts_by_powder_factor_range(
        self,
        min_powder_factor: float,
        max_powder_factor: float,
        site_id: Optional[int] = None
    ) -> List[BlastRecord]:
        """
        Get blast records by powder factor range.
        
        Args:
            min_powder_factor: Minimum powder factor
            max_powder_factor: Maximum powder factor
            site_id: Optional site ID filter
            
        Returns:
            List of blast records within powder factor range
        """
        try:
            query = self.db.query(BlastRecord).filter(
                and_(
                    BlastRecord.plan_data['explosive_summary']['powder_factor_kg_t'].astext.cast(float) >= min_powder_factor,
                    BlastRecord.plan_data['explosive_summary']['powder_factor_kg_t'].astext.cast(float) <= max_powder_factor
                )
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            blasts = query.order_by(desc(BlastRecord.created_at)).all()
            
            logger.debug(
                "Retrieved blasts by powder factor range",
                min_powder_factor=min_powder_factor,
                max_powder_factor=max_powder_factor,
                site_id=site_id,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get blasts by powder factor range",
                error=str(e)
            )
            raise
    
    def get_blasts_by_hole_count_range(
        self,
        min_holes: int,
        max_holes: int,
        site_id: Optional[int] = None
    ) -> List[BlastRecord]:
        """
        Get blast records by hole count range.
        
        Args:
            min_holes: Minimum number of holes
            max_holes: Maximum number of holes
            site_id: Optional site ID filter
            
        Returns:
            List of blast records within hole count range
        """
        try:
            query = self.db.query(BlastRecord).filter(
                and_(
                    BlastRecord.plan_data['blast_geometry']['total_holes'].astext.cast(int) >= min_holes,
                    BlastRecord.plan_data['blast_geometry']['total_holes'].astext.cast(int) <= max_holes
                )
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            blasts = query.order_by(desc(BlastRecord.created_at)).all()
            
            logger.debug(
                "Retrieved blasts by hole count range",
                min_holes=min_holes,
                max_holes=max_holes,
                site_id=site_id,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get blasts by hole count range",
                error=str(e)
            )
            raise
    
    def get_blasts_with_safety_violations(self, site_id: Optional[int] = None) -> List[BlastRecord]:
        """
        Get blast records that have safety violations.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            List of blast records with safety violations
        """
        try:
            query = self.db.query(BlastRecord).filter(
                BlastRecord.safety_validation['is_valid'].astext.cast(bool) == False
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            blasts = query.order_by(desc(BlastRecord.created_at)).all()
            
            logger.debug(
                "Retrieved blasts with safety violations",
                site_id=site_id,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get blasts with safety violations",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def get_blasts_requiring_signoff(self, site_id: Optional[int] = None) -> List[BlastRecord]:
        """
        Get blast records that require engineer sign-off.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            List of blast records requiring sign-off
        """
        try:
            query = self.db.query(BlastRecord).filter(
                and_(
                    BlastRecord.blast_status.in_([BlastStatus.DRAFT, BlastStatus.PENDING_REVIEW]),
                    or_(
                        BlastRecord.engineer_signoff.is_(None),
                        BlastRecord.engineer_signoff['is_valid'].astext.cast(bool) == False
                    )
                )
            )
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            blasts = query.order_by(BlastRecord.created_at).all()
            
            logger.debug(
                "Retrieved blasts requiring signoff",
                site_id=site_id,
                count=len(blasts)
            )
            
            return blasts
            
        except Exception as e:
            logger.error(
                "Failed to get blasts requiring signoff",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def update_blast_status(self, blast_id: int, new_status: BlastStatus) -> Optional[BlastRecord]:
        """
        Update blast record status.
        
        Args:
            blast_id: Blast record ID
            new_status: New blast status
            
        Returns:
            Updated blast record or None if not found
        """
        try:
            update_data = {"blast_status": new_status}
            
            # Set execution date when status changes to EXECUTED
            if new_status == BlastStatus.EXECUTED:
                update_data["actual_execution_date"] = datetime.utcnow()
            
            updated_blast = self.update(blast_id, update_data)
            
            if updated_blast:
                logger.info(
                    "Blast status updated",
                    blast_id=blast_id,
                    new_status=new_status
                )
            
            return updated_blast
            
        except Exception as e:
            logger.error(
                "Failed to update blast status",
                blast_id=blast_id,
                new_status=new_status,
                error=str(e)
            )
            raise
    
    def add_engineer_signoff(
        self,
        blast_id: int,
        signoff_data: Dict[str, Any]
    ) -> Optional[BlastRecord]:
        """
        Add engineer sign-off to blast record.
        
        Args:
            blast_id: Blast record ID
            signoff_data: Engineer sign-off data
            
        Returns:
            Updated blast record or None if not found
        """
        try:
            # Add timestamp if not provided
            if "signoff_timestamp" not in signoff_data:
                signoff_data["signoff_timestamp"] = datetime.utcnow().isoformat()
            
            updated_blast = self.update(blast_id, {
                "engineer_signoff": signoff_data,
                "blast_status": BlastStatus.APPROVED
            })
            
            if updated_blast:
                logger.info(
                    "Engineer signoff added",
                    blast_id=blast_id,
                    engineer=signoff_data.get("engineer_name")
                )
            
            return updated_blast
            
        except Exception as e:
            logger.error(
                "Failed to add engineer signoff",
                blast_id=blast_id,
                error=str(e)
            )
            raise
    
    def get_blast_performance_summary(self, site_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get blast performance summary statistics.
        
        Args:
            site_id: Optional site ID filter
            
        Returns:
            Dictionary with performance statistics
        """
        try:
            query = self.db.query(BlastRecord)
            
            if site_id:
                query = query.filter(BlastRecord.site_id == site_id)
            
            # Count by status
            status_counts = {}
            for status in BlastStatus:
                count = query.filter(BlastRecord.blast_status == status).count()
                status_counts[status.value] = count
            
            # Get executed blasts for performance metrics
            executed_blasts = query.filter(
                BlastRecord.blast_status == BlastStatus.EXECUTED
            ).all()
            
            # Calculate average metrics for executed blasts
            if executed_blasts:
                total_holes = sum(blast.total_holes for blast in executed_blasts)
                total_explosive = sum(blast.total_explosive for blast in executed_blasts)
                avg_holes = total_holes / len(executed_blasts)
                avg_explosive = total_explosive / len(executed_blasts)
                
                # Calculate average powder factor
                powder_factors = [blast.powder_factor for blast in executed_blasts if blast.powder_factor]
                avg_powder_factor = sum(powder_factors) / len(powder_factors) if powder_factors else 0
            else:
                avg_holes = 0
                avg_explosive = 0
                avg_powder_factor = 0
            
            summary = {
                "total_blasts": query.count(),
                "status_counts": status_counts,
                "executed_blasts": len(executed_blasts),
                "average_holes_per_blast": avg_holes,
                "average_explosive_per_blast": avg_explosive,
                "average_powder_factor": avg_powder_factor
            }
            
            logger.debug(
                "Generated blast performance summary",
                site_id=site_id,
                summary=summary
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "Failed to get blast performance summary",
                site_id=site_id,
                error=str(e)
            )
            raise
    
    def archive_old_blasts(self, days_old: int = 365) -> int:
        """
        Archive blast records older than specified days.
        
        Args:
            days_old: Number of days old to consider for archiving
            
        Returns:
            Number of blasts archived
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            archived_count = self.db.query(BlastRecord).filter(
                and_(
                    BlastRecord.blast_status == BlastStatus.MEASURED,
                    BlastRecord.actual_execution_date < cutoff_date
                )
            ).update({"blast_status": BlastStatus.ARCHIVED})
            
            self.db.commit()
            
            logger.info(
                "Archived old blasts",
                days_old=days_old,
                archived_count=archived_count
            )
            
            return archived_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to archive old blasts",
                days_old=days_old,
                error=str(e)
            )
            raise