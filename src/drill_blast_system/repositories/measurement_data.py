"""
Measurement data repository for measurement-specific database operations.
Implements requirements 5.1, 5.2, 5.3 for post-blast measurement storage and learning pipeline.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from .base import BaseRepository
from ..models.measurement_data import MeasurementData, MeasurementType, MeasurementQuality
from ..core.logging import get_logger

logger = get_logger(__name__)


class MeasurementDataRepository(BaseRepository[MeasurementData]):
    """
    Repository for MeasurementData entity with specialized query methods.
    
    Provides measurement data-specific database operations including:
    - Measurement filtering by type and quality
    - Training data management
    - Performance analysis and validation
    - Outlier detection and management
    """
    
    def __init__(self, db: Session):
        """Initialize measurement data repository."""
        super().__init__(db, MeasurementData)
    
    def get_by_blast_record_id(self, blast_record_id: int) -> List[MeasurementData]:
        """
        Get all measurements for a specific blast record.
        
        Args:
            blast_record_id: Blast record ID
            
        Returns:
            List of measurements for the blast record
        """
        return self.find_by_filters(
            filters={"blast_record_id": blast_record_id},
            order_by="measurement_date"
        )
    
    def get_by_measurement_type(
        self,
        measurement_type: MeasurementType,
        skip: int = 0,
        limit: int = 100
    ) -> List[MeasurementData]:
        """
        Get measurements by type.
        
        Args:
            measurement_type: Type of measurement
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of measurements of specified type
        """
        return self.find_by_filters(
            filters={"measurement_type": measurement_type},
            skip=skip,
            limit=limit,
            order_by="measurement_date",
            order_desc=True
        )
    
    def get_by_quality(
        self,
        quality: MeasurementQuality,
        measurement_type: Optional[MeasurementType] = None
    ) -> List[MeasurementData]:
        """
        Get measurements by quality level.
        
        Args:
            quality: Measurement quality level
            measurement_type: Optional measurement type filter
            
        Returns:
            List of measurements with specified quality
        """
        filters = {"measurement_quality": quality}
        if measurement_type:
            filters["measurement_type"] = measurement_type
            
        return self.find_by_filters(
            filters=filters,
            order_by="measurement_date",
            order_desc=True
        )
    
    def get_training_data(
        self,
        measurement_type: Optional[MeasurementType] = None,
        min_quality: MeasurementQuality = MeasurementQuality.FAIR
    ) -> List[MeasurementData]:
        """
        Get measurements suitable for training.
        
        Args:
            measurement_type: Optional measurement type filter
            min_quality: Minimum quality level for training
            
        Returns:
            List of measurements suitable for training
        """
        try:
            # Define quality hierarchy
            quality_hierarchy = {
                MeasurementQuality.EXCELLENT: 4,
                MeasurementQuality.GOOD: 3,
                MeasurementQuality.FAIR: 2,
                MeasurementQuality.POOR: 1,
                MeasurementQuality.INVALID: 0
            }
            
            min_quality_level = quality_hierarchy[min_quality]
            acceptable_qualities = [
                quality for quality, level in quality_hierarchy.items()
                if level >= min_quality_level
            ]
            
            query = self.db.query(MeasurementData).filter(
                and_(
                    MeasurementData.use_for_training == True,
                    MeasurementData.is_outlier == False,
                    MeasurementData.measurement_quality.in_(acceptable_qualities)
                )
            )
            
            if measurement_type:
                query = query.filter(MeasurementData.measurement_type == measurement_type)
            
            measurements = query.order_by(desc(MeasurementData.measurement_date)).all()
            
            logger.debug(
                "Retrieved training data",
                measurement_type=measurement_type,
                min_quality=min_quality,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get training data",
                measurement_type=measurement_type,
                min_quality=min_quality,
                error=str(e)
            )
            raise
    
    def get_validation_data(
        self,
        measurement_type: Optional[MeasurementType] = None,
        exclude_training: bool = True
    ) -> List[MeasurementData]:
        """
        Get measurements suitable for validation.
        
        Args:
            measurement_type: Optional measurement type filter
            exclude_training: Whether to exclude training data
            
        Returns:
            List of measurements suitable for validation
        """
        try:
            query = self.db.query(MeasurementData).filter(
                and_(
                    MeasurementData.use_for_validation == True,
                    MeasurementData.is_outlier == False,
                    MeasurementData.measurement_quality.in_([
                        MeasurementQuality.EXCELLENT,
                        MeasurementQuality.GOOD,
                        MeasurementQuality.FAIR
                    ])
                )
            )
            
            if measurement_type:
                query = query.filter(MeasurementData.measurement_type == measurement_type)
            
            if exclude_training:
                query = query.filter(MeasurementData.use_for_training == False)
            
            measurements = query.order_by(desc(MeasurementData.measurement_date)).all()
            
            logger.debug(
                "Retrieved validation data",
                measurement_type=measurement_type,
                exclude_training=exclude_training,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get validation data",
                measurement_type=measurement_type,
                error=str(e)
            )
            raise
    
    def get_fragmentation_measurements(
        self,
        blast_record_id: Optional[int] = None,
        min_confidence: float = 0.7
    ) -> List[MeasurementData]:
        """
        Get fragmentation measurements with optional filtering.
        
        Args:
            blast_record_id: Optional blast record ID filter
            min_confidence: Minimum confidence score
            
        Returns:
            List of fragmentation measurements
        """
        try:
            query = self.db.query(MeasurementData).filter(
                MeasurementData.measurement_type == MeasurementType.FRAGMENTATION
            )
            
            if blast_record_id:
                query = query.filter(MeasurementData.blast_record_id == blast_record_id)
            
            # Filter by confidence score if quality metrics exist
            if min_confidence > 0:
                query = query.filter(
                    or_(
                        MeasurementData.quality_metrics.is_(None),
                        MeasurementData.quality_metrics['confidence_score'].astext.cast(float) >= min_confidence
                    )
                )
            
            measurements = query.order_by(desc(MeasurementData.measurement_date)).all()
            
            logger.debug(
                "Retrieved fragmentation measurements",
                blast_record_id=blast_record_id,
                min_confidence=min_confidence,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get fragmentation measurements",
                blast_record_id=blast_record_id,
                error=str(e)
            )
            raise
    
    def get_ppv_measurements(
        self,
        blast_record_id: Optional[int] = None,
        min_ppv: Optional[float] = None,
        max_ppv: Optional[float] = None
    ) -> List[MeasurementData]:
        """
        Get PPV measurements with optional filtering.
        
        Args:
            blast_record_id: Optional blast record ID filter
            min_ppv: Minimum PPV value filter
            max_ppv: Maximum PPV value filter
            
        Returns:
            List of PPV measurements
        """
        try:
            query = self.db.query(MeasurementData).filter(
                MeasurementData.measurement_type == MeasurementType.PPV
            )
            
            if blast_record_id:
                query = query.filter(MeasurementData.blast_record_id == blast_record_id)
            
            if min_ppv is not None:
                query = query.filter(
                    MeasurementData.measured_values['peak_ppv'].astext.cast(float) >= min_ppv
                )
            
            if max_ppv is not None:
                query = query.filter(
                    MeasurementData.measured_values['peak_ppv'].astext.cast(float) <= max_ppv
                )
            
            measurements = query.order_by(desc(MeasurementData.measurement_date)).all()
            
            logger.debug(
                "Retrieved PPV measurements",
                blast_record_id=blast_record_id,
                min_ppv=min_ppv,
                max_ppv=max_ppv,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get PPV measurements",
                blast_record_id=blast_record_id,
                error=str(e)
            )
            raise
    
    def get_measurements_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        measurement_type: Optional[MeasurementType] = None
    ) -> List[MeasurementData]:
        """
        Get measurements within date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            measurement_type: Optional measurement type filter
            
        Returns:
            List of measurements within date range
        """
        try:
            query = self.db.query(MeasurementData).filter(
                and_(
                    MeasurementData.measurement_date >= start_date,
                    MeasurementData.measurement_date <= end_date
                )
            )
            
            if measurement_type:
                query = query.filter(MeasurementData.measurement_type == measurement_type)
            
            measurements = query.order_by(MeasurementData.measurement_date).all()
            
            logger.debug(
                "Retrieved measurements by date range",
                start_date=start_date,
                end_date=end_date,
                measurement_type=measurement_type,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get measurements by date range",
                start_date=start_date,
                end_date=end_date,
                error=str(e)
            )
            raise
    
    def get_outliers(self, measurement_type: Optional[MeasurementType] = None) -> List[MeasurementData]:
        """
        Get measurements marked as outliers.
        
        Args:
            measurement_type: Optional measurement type filter
            
        Returns:
            List of outlier measurements
        """
        filters = {"is_outlier": True}
        if measurement_type:
            filters["measurement_type"] = measurement_type
            
        return self.find_by_filters(
            filters=filters,
            order_by="measurement_date",
            order_desc=True
        )
    
    def get_unvalidated_measurements(
        self,
        measurement_type: Optional[MeasurementType] = None,
        older_than_days: Optional[int] = None
    ) -> List[MeasurementData]:
        """
        Get measurements that haven't been validated.
        
        Args:
            measurement_type: Optional measurement type filter
            older_than_days: Optional filter for measurements older than X days
            
        Returns:
            List of unvalidated measurements
        """
        try:
            query = self.db.query(MeasurementData).filter(
                MeasurementData.is_validated == False
            )
            
            if measurement_type:
                query = query.filter(MeasurementData.measurement_type == measurement_type)
            
            if older_than_days:
                cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
                query = query.filter(MeasurementData.measurement_date < cutoff_date)
            
            measurements = query.order_by(MeasurementData.measurement_date).all()
            
            logger.debug(
                "Retrieved unvalidated measurements",
                measurement_type=measurement_type,
                older_than_days=older_than_days,
                count=len(measurements)
            )
            
            return measurements
            
        except Exception as e:
            logger.error(
                "Failed to get unvalidated measurements",
                measurement_type=measurement_type,
                error=str(e)
            )
            raise
    
    def mark_as_outlier(self, measurement_id: int, reason: str) -> Optional[MeasurementData]:
        """
        Mark measurement as outlier.
        
        Args:
            measurement_id: Measurement ID
            reason: Reason for marking as outlier
            
        Returns:
            Updated measurement or None if not found
        """
        try:
            measurement = self.get_by_id(measurement_id)
            if not measurement:
                return None
            
            measurement.mark_as_outlier(reason)
            self.db.commit()
            self.db.refresh(measurement)
            
            logger.info(
                "Measurement marked as outlier",
                measurement_id=measurement_id,
                reason=reason
            )
            
            return measurement
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to mark measurement as outlier",
                measurement_id=measurement_id,
                error=str(e)
            )
            raise
    
    def validate_measurement(
        self,
        measurement_id: int,
        validated_by: str,
        validation_notes: Optional[str] = None
    ) -> Optional[MeasurementData]:
        """
        Validate a measurement.
        
        Args:
            measurement_id: Measurement ID
            validated_by: Validator identifier
            validation_notes: Optional validation notes
            
        Returns:
            Updated measurement or None if not found
        """
        try:
            update_data = {
                "is_validated": True,
                "validated_by": validated_by,
                "validation_date": datetime.utcnow()
            }
            
            if validation_notes:
                update_data["notes"] = validation_notes
            
            updated_measurement = self.update(measurement_id, update_data)
            
            if updated_measurement:
                logger.info(
                    "Measurement validated",
                    measurement_id=measurement_id,
                    validated_by=validated_by
                )
            
            return updated_measurement
            
        except Exception as e:
            logger.error(
                "Failed to validate measurement",
                measurement_id=measurement_id,
                error=str(e)
            )
            raise
    
    def get_measurement_statistics(
        self,
        measurement_type: Optional[MeasurementType] = None
    ) -> Dict[str, Any]:
        """
        Get measurement statistics summary.
        
        Args:
            measurement_type: Optional measurement type filter
            
        Returns:
            Dictionary with measurement statistics
        """
        try:
            query = self.db.query(MeasurementData)
            
            if measurement_type:
                query = query.filter(MeasurementData.measurement_type == measurement_type)
            
            total_measurements = query.count()
            
            # Count by quality
            quality_counts = {}
            for quality in MeasurementQuality:
                count = query.filter(MeasurementData.measurement_quality == quality).count()
                quality_counts[quality.value] = count
            
            # Count by type if not filtered
            type_counts = {}
            if not measurement_type:
                for mtype in MeasurementType:
                    count = self.db.query(MeasurementData).filter(
                        MeasurementData.measurement_type == mtype
                    ).count()
                    type_counts[mtype.value] = count
            
            # Training/validation counts
            training_count = query.filter(MeasurementData.use_for_training == True).count()
            validation_count = query.filter(MeasurementData.use_for_validation == True).count()
            outlier_count = query.filter(MeasurementData.is_outlier == True).count()
            validated_count = query.filter(MeasurementData.is_validated == True).count()
            
            statistics = {
                "total_measurements": total_measurements,
                "quality_counts": quality_counts,
                "training_data_count": training_count,
                "validation_data_count": validation_count,
                "outlier_count": outlier_count,
                "validated_count": validated_count,
                "unvalidated_count": total_measurements - validated_count
            }
            
            if not measurement_type:
                statistics["type_counts"] = type_counts
            
            logger.debug(
                "Generated measurement statistics",
                measurement_type=measurement_type,
                statistics=statistics
            )
            
            return statistics
            
        except Exception as e:
            logger.error(
                "Failed to get measurement statistics",
                measurement_type=measurement_type,
                error=str(e)
            )
            raise
    
    def get_fragmentation_p80_distribution(
        self,
        blast_record_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get P80 distribution for fragmentation measurements.
        
        Args:
            blast_record_ids: Optional list of blast record IDs to filter
            
        Returns:
            List of P80 values with metadata
        """
        try:
            query = self.db.query(MeasurementData).filter(
                and_(
                    MeasurementData.measurement_type == MeasurementType.FRAGMENTATION,
                    MeasurementData.measured_values['p80'].isnot(None)
                )
            )
            
            if blast_record_ids:
                query = query.filter(MeasurementData.blast_record_id.in_(blast_record_ids))
            
            measurements = query.all()
            
            p80_data = []
            for measurement in measurements:
                p80_value = measurement.get_fragmentation_p80()
                if p80_value:
                    p80_data.append({
                        "measurement_id": measurement.id,
                        "blast_record_id": measurement.blast_record_id,
                        "p80": p80_value,
                        "measurement_date": measurement.measurement_date,
                        "quality": measurement.measurement_quality.value,
                        "confidence_score": measurement.confidence_score
                    })
            
            logger.debug(
                "Retrieved P80 distribution",
                blast_record_ids=blast_record_ids,
                count=len(p80_data)
            )
            
            return p80_data
            
        except Exception as e:
            logger.error(
                "Failed to get P80 distribution",
                blast_record_ids=blast_record_ids,
                error=str(e)
            )
            raise
    
    def cleanup_old_measurements(self, days_old: int = 730) -> int:
        """
        Clean up old measurements (soft delete by marking as archived).
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Number of measurements cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Mark old, low-quality measurements as not suitable for training/validation
            cleanup_count = self.db.query(MeasurementData).filter(
                and_(
                    MeasurementData.measurement_date < cutoff_date,
                    MeasurementData.measurement_quality == MeasurementQuality.POOR,
                    MeasurementData.is_validated == False
                )
            ).update({
                "use_for_training": False,
                "use_for_validation": False
            })
            
            self.db.commit()
            
            logger.info(
                "Cleaned up old measurements",
                days_old=days_old,
                cleanup_count=cleanup_count
            )
            
            return cleanup_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to cleanup old measurements",
                days_old=days_old,
                error=str(e)
            )
            raise