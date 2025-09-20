"""
API routes for measurement data management.
Implements requirements 5.1, 5.2, 5.3: Measurement data CRUD operations.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, date
import logging

from ...core.database import get_db
from ...models.measurement_data import MeasurementData, MeasurementType, MeasurementQuality
from ...schemas.measurement_data import (
    MeasurementDataResponse, 
    MeasurementDataCreate, 
    MeasurementDataUpdate
)
from ...schemas.common import ResponseModel, PaginatedResponse
from ...auth.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Measurement Data"])


@router.get("/measurement-data", response_model=ResponseModel)
async def get_measurements(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in measurement names"),
    measurement_type: Optional[str] = Query(None, description="Filter by measurement type"),
    quality: Optional[str] = Query(None, description="Filter by quality"),
    blast_record_id: Optional[int] = Query(None, description="Filter by blast record ID"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    use_for_training: Optional[bool] = Query(None, description="Filter by training use"),
    is_outlier: Optional[bool] = Query(None, description="Filter by outlier status"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get paginated list of measurement data with filtering options.
    """
    try:
        # Build query
        query = db.query(MeasurementData)
        
        # Apply filters
        if search:
            query = query.filter(
                or_(
                    MeasurementData.measurement_name.ilike(f"%{search}%"),
                    MeasurementData.operator_name.ilike(f"%{search}%"),
                    MeasurementData.equipment_used.ilike(f"%{search}%")
                )
            )
        
        if measurement_type:
            try:
                mt = MeasurementType(measurement_type)
                query = query.filter(MeasurementData.measurement_type == mt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid measurement type: {measurement_type}")
        
        if quality:
            try:
                mq = MeasurementQuality(quality)
                query = query.filter(MeasurementData.measurement_quality == mq)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid quality: {quality}")
        
        if blast_record_id:
            query = query.filter(MeasurementData.blast_record_id == blast_record_id)
        
        if date_from:
            query = query.filter(MeasurementData.measurement_date >= date_from)
        
        if date_to:
            query = query.filter(MeasurementData.measurement_date <= date_to)
        
        if use_for_training is not None:
            query = query.filter(MeasurementData.use_for_training == use_for_training)
        
        if is_outlier is not None:
            query = query.filter(MeasurementData.is_outlier == is_outlier)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        measurements = (
            query
            .order_by(desc(MeasurementData.measurement_date))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size
        
        # Convert to response format
        measurement_responses = []
        for measurement in measurements:
            response_data = {
                "id": measurement.id,
                "blast_record_id": measurement.blast_record_id,
                "measurement_name": measurement.measurement_name,
                "measurement_type": measurement.measurement_type.value,
                "measurement_quality": measurement.measurement_quality.value,
                "measurement_date": measurement.measurement_date.isoformat(),
                "measurement_method": measurement.measurement_method,
                "operator_name": measurement.operator_name,
                "equipment_used": measurement.equipment_used,
                "measured_values": measurement.measured_values,
                "quality_metrics": measurement.quality_metrics,
                "confidence_score": measurement.confidence_score,
                "is_high_quality": measurement.is_high_quality,
                "use_for_training": measurement.use_for_training,
                "use_for_validation": measurement.use_for_validation,
                "is_outlier": measurement.is_outlier,
                "created_at": measurement.created_at.isoformat(),
                "updated_at": measurement.updated_at.isoformat(),
            }
            measurement_responses.append(response_data)
        
        return ResponseModel(
            success=True,
            message=f"Retrieved {len(measurements)} measurements",
            data={
                "items": measurement_responses,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving measurements: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve measurements: {str(e)}"
        )


@router.get("/measurement-data/{measurement_id}", response_model=ResponseModel)
async def get_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get a specific measurement by ID.
    """
    try:
        measurement = db.query(MeasurementData).filter(MeasurementData.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        response_data = {
            "id": measurement.id,
            "blast_record_id": measurement.blast_record_id,
            "measurement_name": measurement.measurement_name,
            "measurement_type": measurement.measurement_type.value,
            "measurement_quality": measurement.measurement_quality.value,
            "measurement_date": measurement.measurement_date.isoformat(),
            "measurement_method": measurement.measurement_method,
            "operator_name": measurement.operator_name,
            "equipment_used": measurement.equipment_used,
            "measurement_location": measurement.measurement_location,
            "measured_values": measurement.measured_values,
            "quality_metrics": measurement.quality_metrics,
            "file_references": measurement.file_references,
            "processing_metadata": measurement.processing_metadata,
            "prediction_comparison": measurement.prediction_comparison,
            "notes": measurement.notes,
            "is_validated": measurement.is_validated,
            "validated_by": measurement.validated_by,
            "validation_date": measurement.validation_date.isoformat() if measurement.validation_date else None,
            "confidence_score": measurement.confidence_score,
            "is_high_quality": measurement.is_high_quality,
            "use_for_training": measurement.use_for_training,
            "use_for_validation": measurement.use_for_validation,
            "is_outlier": measurement.is_outlier,
            "created_at": measurement.created_at.isoformat(),
            "updated_at": measurement.updated_at.isoformat(),
        }
        
        return ResponseModel(
            success=True,
            message="Measurement retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving measurement {measurement_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve measurement: {str(e)}"
        )


@router.patch("/measurement-data/{measurement_id}", response_model=ResponseModel)
async def update_measurement(
    measurement_id: int,
    update_data: MeasurementDataUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Update a measurement record.
    """
    try:
        measurement = db.query(MeasurementData).filter(MeasurementData.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(measurement, field):
                setattr(measurement, field, value)
        
        # Update timestamp
        measurement.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(measurement)
        
        return ResponseModel(
            success=True,
            message="Measurement updated successfully",
            data={"id": measurement.id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating measurement {measurement_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update measurement: {str(e)}"
        )


@router.delete("/measurement-data/{measurement_id}", response_model=ResponseModel)
async def delete_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Delete a measurement record.
    """
    try:
        measurement = db.query(MeasurementData).filter(MeasurementData.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        db.delete(measurement)
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Measurement deleted successfully",
            data={"id": measurement_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting measurement {measurement_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete measurement: {str(e)}"
        )


@router.post("/measurement-data/{measurement_id}/validate", response_model=ResponseModel)
async def validate_measurement(
    measurement_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Validate a measurement record.
    """
    try:
        measurement = db.query(MeasurementData).filter(MeasurementData.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        # Perform validation
        validation_errors = measurement.validate_measurement_data()
        
        if validation_errors:
            return ResponseModel(
                success=False,
                message="Measurement validation failed",
                data={
                    "errors": validation_errors,
                    "is_valid": False
                }
            )
        
        # Mark as validated
        measurement.is_validated = True
        measurement.validated_by = current_user.get("username", "system")
        measurement.validation_date = datetime.utcnow()
        measurement.updated_at = datetime.utcnow()
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Measurement validated successfully",
            data={
                "id": measurement.id,
                "is_valid": True,
                "validated_by": measurement.validated_by,
                "validation_date": measurement.validation_date.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating measurement {measurement_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate measurement: {str(e)}"
        )


@router.post("/measurement-data/{measurement_id}/mark-outlier", response_model=ResponseModel)
async def mark_as_outlier(
    measurement_id: int,
    reason: str = Query(..., description="Reason for marking as outlier"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Mark a measurement as an outlier.
    """
    try:
        measurement = db.query(MeasurementData).filter(MeasurementData.id == measurement_id).first()
        
        if not measurement:
            raise HTTPException(status_code=404, detail="Measurement not found")
        
        # Mark as outlier
        measurement.mark_as_outlier(reason)
        measurement.updated_at = datetime.utcnow()
        
        db.commit()
        
        return ResponseModel(
            success=True,
            message="Measurement marked as outlier",
            data={
                "id": measurement.id,
                "is_outlier": measurement.is_outlier,
                "use_for_training": measurement.use_for_training,
                "reason": reason
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking measurement {measurement_id} as outlier: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark measurement as outlier: {str(e)}"
        )


@router.get("/measurement-data/statistics/summary", response_model=ResponseModel)
async def get_measurement_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get summary statistics for measurement data.
    """
    try:
        # Total counts
        total_measurements = db.query(MeasurementData).count()
        
        # By type
        type_counts = {}
        for measurement_type in MeasurementType:
            count = db.query(MeasurementData).filter(
                MeasurementData.measurement_type == measurement_type
            ).count()
            type_counts[measurement_type.value] = count
        
        # By quality
        quality_counts = {}
        for quality in MeasurementQuality:
            count = db.query(MeasurementData).filter(
                MeasurementData.measurement_quality == quality
            ).count()
            quality_counts[quality.value] = count
        
        # Training data
        training_count = db.query(MeasurementData).filter(
            MeasurementData.use_for_training == True
        ).count()
        
        validation_count = db.query(MeasurementData).filter(
            MeasurementData.use_for_validation == True
        ).count()
        
        outlier_count = db.query(MeasurementData).filter(
            MeasurementData.is_outlier == True
        ).count()
        
        high_quality_count = db.query(MeasurementData).filter(
            MeasurementData.is_high_quality == True
        ).count()
        
        # Recent measurements (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = db.query(MeasurementData).filter(
            MeasurementData.created_at >= thirty_days_ago
        ).count()
        
        statistics = {
            "total_measurements": total_measurements,
            "by_type": type_counts,
            "by_quality": quality_counts,
            "training_data": {
                "use_for_training": training_count,
                "use_for_validation": validation_count,
                "high_quality": high_quality_count,
                "outliers": outlier_count,
            },
            "recent_activity": {
                "last_30_days": recent_count,
                "training_ready": high_quality_count - outlier_count,
            }
        }
        
        return ResponseModel(
            success=True,
            message="Statistics retrieved successfully",
            data=statistics
        )
        
    except Exception as e:
        logger.error(f"Error retrieving measurement statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )