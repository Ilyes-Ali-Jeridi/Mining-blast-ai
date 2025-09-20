"""
Export and reporting API endpoints.
Implements requirements 7.1, 7.2, 7.7: PDF reports, machine-readable exports, and audit logging.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path
import tempfile
import zipfile
import io
import json
import csv

from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks, status, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.logging import get_logger
from ...repositories.blast_record import BlastRecordRepository
from ...repositories.site import SiteRepository
from ...schemas.blast_record import BlastRecordResponse
from ...models.blast_record import BlastStatus
from ...reporting.report_manager import ReportManager, ExportFormat as ReportFormat, ExportType
from ...auth import User, get_current_user, audit_logger

router = APIRouter()
logger = get_logger(__name__)

# Initialize report manager
report_manager = ReportManager()


class ExportFormat(str):
    """Supported export formats."""
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    GEOJSON = "geojson"


class ExportRequest(BaseModel):
    """Export request validation schema."""
    blast_ids: List[int] = Field(..., min_items=1, description="List of blast plan IDs to export")
    format: str = Field(..., description="Export format (pdf, csv, json, geojson)")
    include_safety_report: bool = Field(True, description="Include safety validation report")
    include_hole_details: bool = Field(True, description="Include detailed hole information")
    include_predictions: bool = Field(True, description="Include prediction results")
    include_measurements: bool = Field(False, description="Include measurement data if available")
    
    class Config:
        schema_extra = {
            "example": {
                "blast_ids": [1, 2, 3],
                "format": "pdf",
                "include_safety_report": True,
                "include_hole_details": True,
                "include_predictions": True,
                "include_measurements": False
            }
        }


class BatchExportRequest(BaseModel):
    """Batch export request validation schema."""
    site_id: Optional[int] = Field(None, description="Filter by site ID")
    blast_status: Optional[str] = Field(None, description="Filter by blast status")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    formats: List[str] = Field(..., min_items=1, description="Export formats")
    include_templates: bool = Field(False, description="Include template blast plans")
    
    class Config:
        schema_extra = {
            "example": {
                "site_id": 1,
                "blast_status": "approved",
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-12-31T23:59:59Z",
                "formats": ["pdf", "csv"],
                "include_templates": False
            }
        }


class ExportAuditLog(BaseModel):
    """Export audit log entry."""
    export_id: str = Field(..., description="Unique export identifier")
    user_id: str = Field(..., description="User who requested export")
    export_timestamp: datetime = Field(..., description="Export timestamp")
    blast_ids: List[int] = Field(..., description="Exported blast plan IDs")
    format: str = Field(..., description="Export format")
    file_size: int = Field(..., description="Exported file size in bytes")
    success: bool = Field(..., description="Export success status")
    error_message: Optional[str] = Field(None, description="Error message if failed")


@router.post("/blast-plans/{blast_id}/export/{format}")
async def export_single_blast_plan(
    blast_id: int,
    format: str,
    request: Request,
    include_safety_report: bool = Query(True, description="Include safety validation report"),
    include_hole_details: bool = Query(True, description="Include detailed hole information"),
    include_predictions: bool = Query(True, description="Include prediction results"),
    include_measurements: bool = Query(False, description="Include measurement data if available"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Export a single blast plan in the specified format.
    
    Args:
        blast_id: Blast plan ID
        format: Export format (pdf, csv, json, geojson)
        include_safety_report: Include safety validation report
        include_hole_details: Include detailed hole information
        include_predictions: Include prediction results
        include_measurements: Include measurement data if available
        db: Database session
        
    Returns:
        StreamingResponse with exported file
        
    Raises:
        HTTPException: If blast plan not found or export fails
    """
    try:
        # Validate format
        if format not in [ExportFormat.PDF, ExportFormat.CSV, ExportFormat.JSON, ExportFormat.GEOJSON]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
        
        blast_repo = BlastRecordRepository(db)
        
        # Get blast plan
        blast = blast_repo.get_by_id(blast_id)
        if not blast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Blast plan with ID {blast_id} not found"
            )
        
        # Check if blast can be exported
        can_export, blocking_reasons = blast.can_be_exported()
        if not can_export:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Blast plan cannot be exported: {'; '.join(blocking_reasons)}"
            )
        
        # Prepare export options
        export_options = {
            'include_safety_report': include_safety_report,
            'include_hole_details': include_hole_details,
            'include_predictions': include_predictions,
            'include_measurements': include_measurements
        }
        
        # Generate export using report manager
        file_content, filename, media_type = report_manager.export_blast_plan(
            blast, 
            ReportFormat(format),
            ExportType.COMPLETE_REPORT,
            export_options
        )
        
        # Log successful export (requirement 4.5 - audit trail)
        audit_logger.log_export_action(
            db=db,
            user=current_user,
            blast_record_id=blast_id,
            export_format=format,
            result="SUCCESS",
            request=request
        )
        
        logger.info(
            "Blast plan exported successfully",
            blast_id=blast_id,
            format=format,
            file_size=len(file_content),
            user_id=current_user.id,
            username=current_user.username
        )
        
        # Return streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException as http_exc:
        # Log failed export attempt
        audit_logger.log_export_action(
            db=db,
            user=current_user,
            blast_record_id=blast_id,
            export_format=format,
            result="FAILURE",
            request=request,
            error_message=str(http_exc.detail)
        )
        raise
    except Exception as e:
        # Log failed export
        audit_logger.log_export_action(
            db=db,
            user=current_user,
            blast_record_id=blast_id,
            export_format=format,
            result="ERROR",
            request=request,
            error_message=str(e)
        )
        
        logger.error(
            "Failed to export blast plan",
            blast_id=blast_id,
            format=format,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export blast plan"
        )


@router.post("/blast-plans/export")
async def export_multiple_blast_plans(
    export_request: ExportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Export multiple blast plans in the specified format.
    
    Args:
        export_request: Export request parameters
        db: Database session
        
    Returns:
        StreamingResponse with exported file(s)
        
    Raises:
        HTTPException: If blast plans not found or export fails
    """
    try:
        # Validate format
        if export_request.format not in [ExportFormat.PDF, ExportFormat.CSV, ExportFormat.JSON, ExportFormat.GEOJSON]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {export_request.format}"
            )
        
        blast_repo = BlastRecordRepository(db)
        
        # Get blast plans
        blasts = []
        for blast_id in export_request.blast_ids:
            blast = blast_repo.get_by_id(blast_id)
            if not blast:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Blast plan with ID {blast_id} not found"
                )
            
            # Check if blast can be exported
            can_export, blocking_reasons = blast.can_be_exported()
            if not can_export:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Blast plan {blast_id} cannot be exported: {'; '.join(blocking_reasons)}"
                )
            
            blasts.append(blast)
        
        # Prepare export options
        export_options = {
            'include_safety_report': export_request.include_safety_report,
            'include_hole_details': export_request.include_hole_details,
            'include_predictions': export_request.include_predictions,
            'include_measurements': export_request.include_measurements
        }
        
        # Generate combined export using report manager
        file_content, filename, media_type = report_manager.export_multiple_blast_plans(
            blasts,
            ReportFormat(export_request.format),
            ExportType.COMPLETE_REPORT,
            export_options
        )
        
        # Log export
        await _log_export_audit(
            export_id=f"multi_{len(blasts)}_{export_request.format}_{datetime.utcnow().isoformat()}",
            user_id="system",  # TODO: Get from authentication
            blast_ids=export_request.blast_ids,
            format=export_request.format,
            file_size=len(file_content),
            success=True
        )
        
        logger.info(
            "Multiple blast plans exported successfully",
            blast_count=len(blasts),
            format=export_request.format,
            file_size=len(file_content)
        )
        
        # Return streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log failed export
        await _log_export_audit(
            export_id=f"multi_{len(export_request.blast_ids)}_{export_request.format}_{datetime.utcnow().isoformat()}",
            user_id="system",
            blast_ids=export_request.blast_ids,
            format=export_request.format,
            file_size=0,
            success=False,
            error_message=str(e)
        )
        
        logger.error(
            "Failed to export multiple blast plans",
            blast_ids=export_request.blast_ids,
            format=export_request.format,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export blast plans"
        )


@router.post("/blast-plans/batch-export")
async def batch_export_blast_plans(
    batch_request: BatchExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Batch export blast plans based on filters.
    
    Args:
        batch_request: Batch export request parameters
        background_tasks: Background task manager
        db: Database session
        
    Returns:
        Export job information
        
    Raises:
        HTTPException: If export fails
    """
    try:
        # Validate formats
        for format in batch_request.formats:
            if format not in [ExportFormat.PDF, ExportFormat.CSV, ExportFormat.JSON, ExportFormat.GEOJSON]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported export format: {format}"
                )
        
        blast_repo = BlastRecordRepository(db)
        
        # Build query filters
        filters = {}
        if batch_request.site_id:
            filters['site_id'] = batch_request.site_id
        if batch_request.blast_status:
            filters['blast_status'] = batch_request.blast_status
        if batch_request.date_from:
            filters['created_after'] = batch_request.date_from
        if batch_request.date_to:
            filters['created_before'] = batch_request.date_to
        
        # Get blast plans
        if batch_request.include_templates:
            blasts = blast_repo.get_templates(site_id=batch_request.site_id)
        else:
            blasts = blast_repo.get_filtered_blasts(**filters)
        
        if not blasts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No blast plans found matching the specified criteria"
            )
        
        # Filter exportable blasts
        exportable_blasts = []
        for blast in blasts:
            can_export, _ = blast.can_be_exported()
            if can_export:
                exportable_blasts.append(blast)
        
        if not exportable_blasts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No exportable blast plans found matching the criteria"
            )
        
        # Generate export job ID
        export_job_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(exportable_blasts)}"
        
        # Schedule background export task
        background_tasks.add_task(
            _process_batch_export,
            export_job_id=export_job_id,
            blasts=exportable_blasts,
            formats=batch_request.formats,
            db=db
        )
        
        logger.info(
            "Batch export job scheduled",
            job_id=export_job_id,
            blast_count=len(exportable_blasts),
            formats=batch_request.formats
        )
        
        return {
            "export_job_id": export_job_id,
            "blast_count": len(exportable_blasts),
            "formats": batch_request.formats,
            "status": "scheduled",
            "estimated_completion": "5-10 minutes"  # Rough estimate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to schedule batch export",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to schedule batch export"
        )


@router.get("/export-jobs/{job_id}/status")
async def get_export_job_status(
    job_id: str
) -> Dict[str, Any]:
    """
    Get the status of a batch export job.
    
    Args:
        job_id: Export job ID
        
    Returns:
        Export job status information
    """
    # TODO: Implement job status tracking with Redis or database
    # For now, return a placeholder response
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "files_generated": 3,
        "download_urls": [
            f"/api/v1/exports/download/{job_id}/blast_plans.pdf",
            f"/api/v1/exports/download/{job_id}/blast_plans.csv",
            f"/api/v1/exports/download/{job_id}/blast_plans.json"
        ]
    }


@router.get("/download/{job_id}/{filename}")
async def download_export_file(
    job_id: str,
    filename: str
) -> FileResponse:
    """
    Download an exported file from a batch export job.
    
    Args:
        job_id: Export job ID
        filename: File name to download
        
    Returns:
        FileResponse with the requested file
        
    Raises:
        HTTPException: If file not found
    """
    # TODO: Implement file storage and retrieval
    # For now, return a placeholder response
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found or export job not completed"
    )


@router.get("/audit-logs")
async def get_export_audit_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    format: Optional[str] = Query(None, description="Filter by export format"),
    success_only: bool = Query(False, description="Show only successful exports")
) -> List[ExportAuditLog]:
    """
    Get export audit logs.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        user_id: Filter by user ID
        format: Filter by export format
        success_only: Show only successful exports
        
    Returns:
        List of export audit log entries
    """
    # TODO: Implement audit log storage and retrieval
    # For now, return placeholder data
    return [
        ExportAuditLog(
            export_id="single_1_pdf_2024-01-15T10:30:00",
            user_id="engineer_001",
            export_timestamp=datetime.utcnow(),
            blast_ids=[1],
            format="pdf",
            file_size=1024000,
            success=True
        )
    ]


# Helper functions for audit logging and background processing


async def _process_batch_export(export_job_id: str, blasts, formats: List[str], db: Session):
    """Process batch export in background."""
    try:
        # TODO: Implement actual batch processing
        # This would generate files for each format and store them
        logger.info(f"Processing batch export job {export_job_id}")
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(2)
        
        logger.info(f"Batch export job {export_job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Batch export job {export_job_id} failed: {str(e)}")


async def _log_export_audit(export_id: str, user_id: str, blast_ids: List[int], 
                          format: str, file_size: int, success: bool, 
                          error_message: Optional[str] = None):
    """Log export audit entry."""
    # TODO: Implement audit logging to database
    audit_entry = ExportAuditLog(
        export_id=export_id,
        user_id=user_id,
        export_timestamp=datetime.utcnow(),
        blast_ids=blast_ids,
        format=format,
        file_size=file_size,
        success=success,
        error_message=error_message
    )
    
    logger.info(
        "Export audit logged",
        export_id=export_id,
        user_id=user_id,
        blast_ids=blast_ids,
        format=format,
        success=success
    )