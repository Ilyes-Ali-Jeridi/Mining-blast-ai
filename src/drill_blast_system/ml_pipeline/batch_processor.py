"""
Batch processing system for handling multiple measurement uploads.
Implements requirement 5.2, 5.3: Batch processing and measurement storage.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from .data_ingestion import DataIngestionService
from ..models.measurement_data import MeasurementData
from ..core.database import get_db

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some items succeeded, some failed


@dataclass
class BatchItem:
    """Individual item in a batch"""
    item_id: str
    item_type: str  # 'fragmentation_image', 'ppv_file'
    file: UploadFile
    metadata: Dict[str, Any]
    status: BatchStatus = BatchStatus.PENDING
    result: Optional[MeasurementData] = None
    error: Optional[str] = None
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None


@dataclass
class BatchJob:
    """Batch processing job"""
    job_id: str
    blast_record_id: int
    items: List[BatchItem]
    created_at: datetime
    status: BatchStatus = BatchStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    progress_percentage: float = 0.0
    error_summary: Optional[str] = None


class BatchProcessor:
    """
    Handles batch processing of multiple measurement files.
    
    Features:
    - Concurrent processing of multiple files
    - Progress tracking and status updates
    - Error handling and recovery
    - Quality assessment and filtering
    - Database transaction management
    """
    
    def __init__(self, max_concurrent_jobs: int = 3, max_items_per_job: int = 20):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_items_per_job = max_items_per_job
        self.active_jobs: Dict[str, BatchJob] = {}
        self.data_ingestion_service = DataIngestionService()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_jobs * 2)
        
        # Processing limits
        self.max_file_size = 100 * 1024 * 1024  # 100MB per file
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
        self.supported_ppv_formats = {'.csv', '.txt', '.dat', '.log'}
    
    async def submit_batch_job(
        self,
        blast_record_id: int,
        fragmentation_images: Optional[List[UploadFile]] = None,
        ppv_files: Optional[List[UploadFile]] = None,
        batch_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit a new batch processing job.
        
        Args:
            blast_record_id: ID of associated blast record
            fragmentation_images: List of fragmentation images to process
            ppv_files: List of PPV data files to process
            batch_metadata: Common metadata for the batch
            
        Returns:
            Job ID for tracking progress
        """
        
        # Generate job ID
        job_id = f"batch_{blast_record_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate inputs
        await self._validate_batch_inputs(fragmentation_images, ppv_files, blast_record_id)
        
        # Create batch items
        items = []
        item_counter = 0
        
        # Add fragmentation images
        if fragmentation_images:
            for image in fragmentation_images:
                item_metadata = batch_metadata.get('fragmentation_metadata', {}) if batch_metadata else {}
                item_metadata.update({
                    'measurement_date': batch_metadata.get('measurement_date', datetime.utcnow()),
                    'operator_name': batch_metadata.get('operator_name'),
                    'equipment_used': batch_metadata.get('equipment_used')
                })
                
                items.append(BatchItem(
                    item_id=f"{job_id}_frag_{item_counter}",
                    item_type="fragmentation_image",
                    file=image,
                    metadata=item_metadata
                ))
                item_counter += 1
        
        # Add PPV files
        if ppv_files:
            for ppv_file in ppv_files:
                item_metadata = batch_metadata.get('ppv_metadata', {}) if batch_metadata else {}
                item_metadata.update({
                    'measurement_date': batch_metadata.get('measurement_date', datetime.utcnow()),
                    'operator_name': batch_metadata.get('operator_name'),
                    'equipment_used': batch_metadata.get('equipment_used')
                })
                
                items.append(BatchItem(
                    item_id=f"{job_id}_ppv_{item_counter}",
                    item_type="ppv_file",
                    file=ppv_file,
                    metadata=item_metadata
                ))
                item_counter += 1
        
        # Create batch job
        batch_job = BatchJob(
            job_id=job_id,
            blast_record_id=blast_record_id,
            items=items,
            created_at=datetime.utcnow(),
            total_items=len(items)
        )
        
        # Store job
        self.active_jobs[job_id] = batch_job
        
        # Start processing asynchronously
        asyncio.create_task(self._process_batch_job(job_id))
        
        logger.info(f"Batch job {job_id} submitted with {len(items)} items")
        return job_id
    
    async def get_batch_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a batch processing job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Job status information or None if job not found
        """
        
        if job_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[job_id]
        
        # Calculate progress
        if job.total_items > 0:
            job.progress_percentage = (job.processed_items / job.total_items) * 100
        
        return {
            'job_id': job.job_id,
            'blast_record_id': job.blast_record_id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'total_items': job.total_items,
            'processed_items': job.processed_items,
            'successful_items': job.successful_items,
            'failed_items': job.failed_items,
            'progress_percentage': job.progress_percentage,
            'error_summary': job.error_summary,
            'item_details': [
                {
                    'item_id': item.item_id,
                    'item_type': item.item_type,
                    'filename': item.file.filename,
                    'status': item.status,
                    'error': item.error,
                    'processing_start': item.processing_start.isoformat() if item.processing_start else None,
                    'processing_end': item.processing_end.isoformat() if item.processing_end else None
                }
                for item in job.items
            ]
        }
    
    async def get_batch_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get results of a completed batch job.
        
        Args:
            job_id: Job ID to get results for
            
        Returns:
            Job results or None if job not found/not completed
        """
        
        if job_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[job_id]
        
        if job.status not in [BatchStatus.COMPLETED, BatchStatus.PARTIAL]:
            return None
        
        # Collect successful results
        fragmentation_results = []
        ppv_results = []
        errors = []
        
        for item in job.items:
            if item.result:
                if item.item_type == "fragmentation_image":
                    fragmentation_results.append({
                        'measurement_id': item.result.id,
                        'filename': item.file.filename,
                        'p80_mm': item.result.get_fragmentation_p80(),
                        'quality': item.result.measurement_quality.value,
                        'confidence_score': item.result.confidence_score
                    })
                elif item.item_type == "ppv_file":
                    ppv_results.append({
                        'measurement_id': item.result.id,
                        'filename': item.file.filename,
                        'peak_ppv': item.result.get_ppv_value(),
                        'quality': item.result.measurement_quality.value,
                        'confidence_score': item.result.confidence_score
                    })
            elif item.error:
                errors.append({
                    'filename': item.file.filename,
                    'item_type': item.item_type,
                    'error': item.error
                })
        
        return {
            'job_id': job.job_id,
            'blast_record_id': job.blast_record_id,
            'status': job.status,
            'summary': {
                'total_items': job.total_items,
                'successful_items': job.successful_items,
                'failed_items': job.failed_items,
                'fragmentation_measurements': len(fragmentation_results),
                'ppv_measurements': len(ppv_results)
            },
            'results': {
                'fragmentation': fragmentation_results,
                'ppv': ppv_results,
                'errors': errors
            },
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }
    
    async def cancel_batch_job(self, job_id: str) -> bool:
        """
        Cancel a batch processing job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if job was cancelled, False if not found or already completed
        """
        
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        
        if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED]:
            return False
        
        # Mark job as failed (cancelled)
        job.status = BatchStatus.FAILED
        job.error_summary = "Job cancelled by user"
        job.completed_at = datetime.utcnow()
        
        # Mark pending items as failed
        for item in job.items:
            if item.status == BatchStatus.PENDING:
                item.status = BatchStatus.FAILED
                item.error = "Job cancelled"
        
        logger.info(f"Batch job {job_id} cancelled")
        return True
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """
        Clean up completed jobs older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for keeping completed jobs
        """
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        jobs_to_remove = []
        
        for job_id, job in self.active_jobs.items():
            if (job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.PARTIAL] and
                job.completed_at and job.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up completed job {job_id}")
    
    async def _process_batch_job(self, job_id: str):
        """Process a batch job asynchronously"""
        
        job = self.active_jobs[job_id]
        
        try:
            job.status = BatchStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            logger.info(f"Starting batch job {job_id} with {job.total_items} items")
            
            # Process items with limited concurrency
            semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
            tasks = []
            
            for item in job.items:
                task = self._process_batch_item(job_id, item, semaphore)
                tasks.append(task)
            
            # Wait for all items to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update job status
            job.completed_at = datetime.utcnow()
            
            if job.failed_items == 0:
                job.status = BatchStatus.COMPLETED
            elif job.successful_items > 0:
                job.status = BatchStatus.PARTIAL
                job.error_summary = f"{job.failed_items} of {job.total_items} items failed"
            else:
                job.status = BatchStatus.FAILED
                job.error_summary = "All items failed to process"
            
            logger.info(f"Batch job {job_id} completed: {job.successful_items}/{job.total_items} successful")
            
        except Exception as e:
            logger.error(f"Batch job {job_id} failed with exception: {e}")
            job.status = BatchStatus.FAILED
            job.error_summary = f"Job failed with exception: {str(e)}"
            job.completed_at = datetime.utcnow()
    
    async def _process_batch_item(self, job_id: str, item: BatchItem, semaphore: asyncio.Semaphore):
        """Process a single batch item"""
        
        async with semaphore:
            job = self.active_jobs[job_id]
            
            try:
                item.status = BatchStatus.PROCESSING
                item.processing_start = datetime.utcnow()
                
                logger.debug(f"Processing batch item {item.item_id}")
                
                # Process based on item type
                if item.item_type == "fragmentation_image":
                    result = await self.data_ingestion_service._process_single_fragmentation_image(
                        job.blast_record_id, item.file, item.metadata, None, 0
                    )
                elif item.item_type == "ppv_file":
                    result = await self.data_ingestion_service._process_single_ppv_file(
                        job.blast_record_id, item.file, item.metadata, None, 0
                    )
                else:
                    raise ValueError(f"Unknown item type: {item.item_type}")
                
                # Store result
                item.result = result
                item.status = BatchStatus.COMPLETED
                item.processing_end = datetime.utcnow()
                
                # Update job counters
                job.processed_items += 1
                job.successful_items += 1
                
                logger.debug(f"Batch item {item.item_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Batch item {item.item_id} failed: {e}")
                
                item.status = BatchStatus.FAILED
                item.error = str(e)
                item.processing_end = datetime.utcnow()
                
                # Update job counters
                job.processed_items += 1
                job.failed_items += 1
    
    async def _validate_batch_inputs(
        self,
        fragmentation_images: Optional[List[UploadFile]],
        ppv_files: Optional[List[UploadFile]],
        blast_record_id: int
    ):
        """Validate batch processing inputs"""
        
        total_files = 0
        if fragmentation_images:
            total_files += len(fragmentation_images)
        if ppv_files:
            total_files += len(ppv_files)
        
        if total_files == 0:
            raise ValueError("No files provided for batch processing")
        
        if total_files > self.max_items_per_job:
            raise ValueError(f"Too many files. Maximum: {self.max_items_per_job}")
        
        # Validate fragmentation images
        if fragmentation_images:
            for i, image in enumerate(fragmentation_images):
                if not image.filename:
                    raise ValueError(f"Fragmentation image {i} has no filename")
                
                file_ext = Path(image.filename).suffix.lower()
                if file_ext not in self.supported_image_formats:
                    raise ValueError(f"Unsupported image format: {file_ext}")
                
                if image.size > self.max_file_size:
                    raise ValueError(f"Image {i} too large. Maximum: {self.max_file_size / (1024*1024):.1f}MB")
        
        # Validate PPV files
        if ppv_files:
            for i, ppv_file in enumerate(ppv_files):
                if not ppv_file.filename:
                    raise ValueError(f"PPV file {i} has no filename")
                
                file_ext = Path(ppv_file.filename).suffix.lower()
                if file_ext not in self.supported_ppv_formats:
                    raise ValueError(f"Unsupported PPV format: {file_ext}")
                
                if ppv_file.size > self.max_file_size:
                    raise ValueError(f"PPV file {i} too large. Maximum: {self.max_file_size / (1024*1024):.1f}MB")


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get or create batch processor instance"""
    global _batch_processor
    
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    
    return _batch_processor