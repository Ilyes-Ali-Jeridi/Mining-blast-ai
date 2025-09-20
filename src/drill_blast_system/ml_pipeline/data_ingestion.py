"""
Measurement data ingestion system for post-blast measurements.
Implements requirements 5.1, 5.2, 5.3: Image upload, PPV parsing, and data storage.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from sqlalchemy.orm import Session
from fastapi import UploadFile

from .fragmentation_analyzer import FragmentationAnalyzer, FragmentationResult
from .ppv_parser import PPVDataParser, PPVParsingResult
from .quality_assessment import MeasurementQualityAssessor, QualityAssessment
from .data_structures import FragmentationResult as FragResult
from ..models.measurement_data import MeasurementData, MeasurementType, MeasurementQuality
from ..models.blast_record import BlastRecord
from ..schemas.measurement_data import MeasurementDataCreate
from ..core.database import get_db
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class DataIngestionService:
    """
    Service for ingesting various types of post-blast measurement data.
    
    Handles:
    - Image upload and fragmentation analysis
    - PPV sensor data parsing and validation
    - Batch processing of multiple measurements
    - Quality assessment and scoring
    - Database storage and retrieval
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.fragmentation_analyzer = None
        self.ppv_parser = PPVDataParser()
        self.quality_assessor = MeasurementQualityAssessor()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Storage configuration
        self.storage_base_path = Path(self.settings.storage.measurement_data_path)
        self.storage_base_path.mkdir(parents=True, exist_ok=True)
        
        # Processing limits
        self.max_concurrent_uploads = 5
        self.max_file_size = self.settings.storage.max_upload_size
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
        self.supported_ppv_formats = {'.csv', '.txt', '.dat', '.log'}
    
    def get_fragmentation_analyzer(self) -> FragmentationAnalyzer:
        """Lazy load fragmentation analyzer"""
        if self.fragmentation_analyzer is None:
            ml_settings = self.settings.ml_pipeline
            self.fragmentation_analyzer = FragmentationAnalyzer(
                sam_model_path=ml_settings.sam_model_path,
                device=ml_settings.sam_device,
                enable_preprocessing=ml_settings.enable_preprocessing
            )
        return self.fragmentation_analyzer
    
    async def ingest_fragmentation_images(
        self,
        blast_record_id: int,
        images: List[UploadFile],
        measurement_metadata: Dict[str, Any],
        scale_references: Optional[List[Dict[str, Any]]] = None
    ) -> List[MeasurementData]:
        """
        Ingest multiple fragmentation images and create measurement records.
        
        Args:
            blast_record_id: ID of associated blast record
            images: List of uploaded image files
            measurement_metadata: Common metadata for all measurements
            scale_references: Optional scale reference data for each image
            
        Returns:
            List of created measurement data records
        """
        logger.info(f"Starting fragmentation image ingestion for blast {blast_record_id}, {len(images)} images")
        
        # Validate inputs
        await self._validate_fragmentation_inputs(images, blast_record_id)
        
        # Process images concurrently
        tasks = []
        for i, image in enumerate(images):
            scale_ref = scale_references[i] if scale_references and i < len(scale_references) else None
            task = self._process_single_fragmentation_image(
                blast_record_id, image, measurement_metadata, scale_ref, i
            )
            tasks.append(task)
        
        # Wait for all processing to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results and log errors
        measurement_records = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process image {i}: {result}")
            else:
                measurement_records.append(result)
        
        logger.info(f"Fragmentation ingestion completed: {len(measurement_records)}/{len(images)} successful")
        return measurement_records
    
    async def ingest_ppv_data_files(
        self,
        blast_record_id: int,
        data_files: List[UploadFile],
        measurement_metadata: Dict[str, Any],
        sensor_locations: Optional[List[Dict[str, Any]]] = None
    ) -> List[MeasurementData]:
        """
        Ingest PPV sensor data files and create measurement records.
        
        Args:
            blast_record_id: ID of associated blast record
            data_files: List of uploaded PPV data files
            measurement_metadata: Common metadata for all measurements
            sensor_locations: Optional sensor location data
            
        Returns:
            List of created measurement data records
        """
        logger.info(f"Starting PPV data ingestion for blast {blast_record_id}, {len(data_files)} files")
        
        # Validate inputs
        await self._validate_ppv_inputs(data_files, blast_record_id)
        
        # Process files concurrently
        tasks = []
        for i, data_file in enumerate(data_files):
            sensor_loc = sensor_locations[i] if sensor_locations and i < len(sensor_locations) else None
            task = self._process_single_ppv_file(
                blast_record_id, data_file, measurement_metadata, sensor_loc, i
            )
            tasks.append(task)
        
        # Wait for all processing to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results and log errors
        measurement_records = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process PPV file {i}: {result}")
            else:
                measurement_records.append(result)
        
        logger.info(f"PPV ingestion completed: {len(measurement_records)}/{len(data_files)} successful")
        return measurement_records
    
    async def batch_ingest_measurements(
        self,
        blast_record_id: int,
        measurement_batch: Dict[str, Any]
    ) -> Dict[str, List[MeasurementData]]:
        """
        Batch ingest multiple types of measurements for a blast.
        
        Args:
            blast_record_id: ID of associated blast record
            measurement_batch: Dictionary containing different measurement types
            
        Returns:
            Dictionary with results for each measurement type
        """
        logger.info(f"Starting batch measurement ingestion for blast {blast_record_id}")
        
        results = {
            'fragmentation': [],
            'ppv': [],
            'errors': []
        }
        
        # Process fragmentation images if provided
        if 'fragmentation_images' in measurement_batch:
            try:
                frag_results = await self.ingest_fragmentation_images(
                    blast_record_id,
                    measurement_batch['fragmentation_images'],
                    measurement_batch.get('fragmentation_metadata', {}),
                    measurement_batch.get('scale_references')
                )
                results['fragmentation'] = frag_results
            except Exception as e:
                logger.error(f"Fragmentation batch processing failed: {e}")
                results['errors'].append(f"Fragmentation processing: {str(e)}")
        
        # Process PPV data files if provided
        if 'ppv_files' in measurement_batch:
            try:
                ppv_results = await self.ingest_ppv_data_files(
                    blast_record_id,
                    measurement_batch['ppv_files'],
                    measurement_batch.get('ppv_metadata', {}),
                    measurement_batch.get('sensor_locations')
                )
                results['ppv'] = ppv_results
            except Exception as e:
                logger.error(f"PPV batch processing failed: {e}")
                results['errors'].append(f"PPV processing: {str(e)}")
        
        # Calculate batch statistics
        total_processed = len(results['fragmentation']) + len(results['ppv'])
        logger.info(f"Batch ingestion completed: {total_processed} measurements processed")
        
        return results
    
    async def _process_single_fragmentation_image(
        self,
        blast_record_id: int,
        image: UploadFile,
        metadata: Dict[str, Any],
        scale_reference: Optional[Dict[str, Any]],
        index: int
    ) -> MeasurementData:
        """Process a single fragmentation image"""
        
        # Create temporary file for processing
        temp_path = None
        try:
            # Save uploaded file
            temp_path = await self._save_temp_file(image, f"frag_{index}")
            
            # Perform fragmentation analysis
            analyzer = self.get_fragmentation_analyzer()
            
            # Extract scale marker coordinates if provided
            scale_coords = None
            known_scale = None
            if scale_reference:
                if 'coordinates' in scale_reference:
                    coords = scale_reference['coordinates']
                    scale_coords = (coords['x1'], coords['y1'], coords['x2'], coords['y2'])
                known_scale = scale_reference.get('known_size_mm_per_pixel')
            
            # Run analysis
            frag_result = analyzer.analyze_muckpile_image(
                image_path=temp_path,
                scale_marker_coords=scale_coords,
                known_scale_mm_per_pixel=known_scale
            )
            
            # Store image file permanently
            stored_path = await self._store_measurement_file(
                temp_path, blast_record_id, f"fragmentation_{index}", image.filename
            )
            
            # Assess quality
            quality_assessment = self.quality_assessor.assess_fragmentation_quality(frag_result)
            
            # Create measurement record
            measurement_data = await self._create_fragmentation_measurement_record(
                blast_record_id, frag_result, quality_assessment, stored_path, metadata, image.filename
            )
            
            return measurement_data
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _process_single_ppv_file(
        self,
        blast_record_id: int,
        data_file: UploadFile,
        metadata: Dict[str, Any],
        sensor_location: Optional[Dict[str, Any]],
        index: int
    ) -> MeasurementData:
        """Process a single PPV data file"""
        
        temp_path = None
        try:
            # Save uploaded file
            temp_path = await self._save_temp_file(data_file, f"ppv_{index}")
            
            # Parse PPV data
            ppv_result = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.ppv_parser.parse_ppv_file, temp_path
            )
            
            # Store data file permanently
            stored_path = await self._store_measurement_file(
                temp_path, blast_record_id, f"ppv_{index}", data_file.filename
            )
            
            # Assess quality
            quality_assessment = self.quality_assessor.assess_ppv_quality(ppv_result)
            
            # Create measurement record
            measurement_data = await self._create_ppv_measurement_record(
                blast_record_id, ppv_result, quality_assessment, stored_path, 
                metadata, data_file.filename, sensor_location
            )
            
            return measurement_data
            
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
    
    async def _save_temp_file(self, upload_file: UploadFile, prefix: str) -> str:
        """Save uploaded file to temporary location"""
        suffix = Path(upload_file.filename).suffix if upload_file.filename else '.tmp'
        
        with tempfile.NamedTemporaryFile(delete=False, prefix=prefix, suffix=suffix) as temp_file:
            content = await upload_file.read()
            temp_file.write(content)
            return temp_file.name
    
    async def _store_measurement_file(
        self, 
        temp_path: str, 
        blast_record_id: int, 
        measurement_type: str, 
        original_filename: str
    ) -> str:
        """Store measurement file in permanent storage"""
        
        # Create storage directory structure
        blast_dir = self.storage_base_path / f"blast_{blast_record_id}"
        blast_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(original_filename).suffix
        stored_filename = f"{measurement_type}_{timestamp}{file_ext}"
        stored_path = blast_dir / stored_filename
        
        # Copy file to permanent storage
        shutil.copy2(temp_path, stored_path)
        
        # Return relative path for database storage
        return str(stored_path.relative_to(self.storage_base_path))
    
    async def _create_fragmentation_measurement_record(
        self,
        blast_record_id: int,
        frag_result: FragmentationResult,
        quality_assessment: QualityAssessment,
        stored_path: str,
        metadata: Dict[str, Any],
        filename: str
    ) -> MeasurementData:
        """Create database record for fragmentation measurement"""
        
        # Prepare measured values
        measured_values = {
            "p10": frag_result.p10,
            "p50": frag_result.p50,
            "p80": frag_result.p80,
            "mean_size": frag_result.mean_size,
            "characteristic_size": frag_result.characteristic_size,
            "uniformity_index": frag_result.uniformity_index,
            "fragment_count": frag_result.fragment_count,
            "total_area_analyzed": frag_result.total_analyzed_area,
            "scale_factor": frag_result.scale_factor
        }
        
        # Prepare quality metrics
        quality_metrics = {
            "confidence_score": quality_assessment.overall_quality,
            "data_completeness": 1.0,  # Image analysis provides complete data
            "measurement_accuracy": quality_assessment.reliability_score * 100,
            "environmental_conditions": metadata.get("environmental_conditions", {}),
            "operator_assessment": metadata.get("operator_assessment", {})
        }
        
        # Prepare file references
        file_references = {
            "images": [{
                "file_path": stored_path,
                "file_type": Path(filename).suffix.lower(),
                "description": f"Muckpile fragmentation image",
                "capture_timestamp": metadata.get("capture_timestamp", datetime.utcnow().isoformat()),
                "scale_reference": metadata.get("scale_reference", {})
            }]
        }
        
        # Prepare processing metadata
        processing_metadata = {
            "processing_timestamp": frag_result.processing_timestamp.isoformat(),
            "processing_method": "automated",
            "software_used": {
                "name": "SAM-based FragmentationAnalyzer",
                "version": "1.0.0",
                "parameters": {
                    "sam_model": "segment_anything",
                    "preprocessing_enabled": True
                }
            },
            "processing_time": metadata.get("processing_time", 0),
            "validation_checks": [
                {
                    "check_name": "fragment_count_sufficient",
                    "status": "PASS" if frag_result.fragment_count >= 20 else "WARNING",
                    "details": f"{frag_result.fragment_count} fragments detected"
                },
                {
                    "check_name": "scale_detection_quality",
                    "status": "PASS" if frag_result.scale_detection_quality > 0.7 else "WARNING",
                    "details": f"Scale detection quality: {frag_result.scale_detection_quality:.2f}"
                }
            ]
        }
        
        # Determine measurement quality enum
        if quality_assessment.overall_quality >= 0.9:
            measurement_quality = MeasurementQuality.EXCELLENT
        elif quality_assessment.overall_quality >= 0.8:
            measurement_quality = MeasurementQuality.GOOD
        elif quality_assessment.overall_quality >= 0.6:
            measurement_quality = MeasurementQuality.FAIR
        elif quality_assessment.overall_quality >= 0.4:
            measurement_quality = MeasurementQuality.POOR
        else:
            measurement_quality = MeasurementQuality.INVALID
        
        # Create measurement record
        db = next(get_db())
        try:
            measurement_data = MeasurementData(
                blast_record_id=blast_record_id,
                measurement_name=metadata.get("name", f"Fragmentation Analysis - {filename}"),
                measurement_type=MeasurementType.FRAGMENTATION,
                measurement_quality=measurement_quality,
                measurement_date=metadata.get("measurement_date", datetime.utcnow()),
                measurement_method="image_analysis",
                operator_name=metadata.get("operator_name"),
                equipment_used=metadata.get("equipment_used", "Digital camera + SAM analyzer"),
                measured_values=measured_values,
                quality_metrics=quality_metrics,
                file_references=file_references,
                processing_metadata=processing_metadata,
                notes=metadata.get("notes"),
                use_for_training=quality_assessment.is_suitable_for_training,
                use_for_validation=quality_assessment.passes_quality_check
            )
            
            db.add(measurement_data)
            db.commit()
            db.refresh(measurement_data)
            
            return measurement_data
        finally:
            db.close()
    
    async def _create_ppv_measurement_record(
        self,
        blast_record_id: int,
        ppv_result: 'PPVParsingResult',
        quality_assessment: QualityAssessment,
        stored_path: str,
        metadata: Dict[str, Any],
        filename: str,
        sensor_location: Optional[Dict[str, Any]]
    ) -> MeasurementData:
        """Create database record for PPV measurement"""
        
        # Prepare measured values
        measured_values = {
            "peak_ppv": ppv_result.peak_ppv,
            "dominant_frequency": ppv_result.dominant_frequency,
            "duration": ppv_result.duration,
            "vector_sum": ppv_result.vector_sum,
            "components": ppv_result.components,
            "frequency_spectrum": ppv_result.frequency_spectrum,
            "distance_to_blast": sensor_location.get("distance_to_blast") if sensor_location else None,
            "charge_weight": metadata.get("charge_weight")
        }
        
        # Prepare quality metrics
        quality_metrics = {
            "confidence_score": quality_assessment.overall_quality,
            "data_completeness": ppv_result.data_completeness,
            "measurement_accuracy": quality_assessment.reliability_score * 100,
            "equipment_status": {
                "calibration_date": metadata.get("calibration_date"),
                "signal_quality": ppv_result.signal_quality,
                "interference_detected": ppv_result.interference_detected
            },
            "operator_assessment": metadata.get("operator_assessment", {})
        }
        
        # Prepare file references
        file_references = {
            "sensor_data_files": [{
                "file_path": stored_path,
                "file_format": Path(filename).suffix.lower(),
                "sampling_rate": ppv_result.sampling_rate,
                "duration": ppv_result.duration,
                "channels": ppv_result.channels,
                "preprocessing_applied": ppv_result.preprocessing_applied
            }]
        }
        
        # Prepare processing metadata
        processing_metadata = {
            "processing_timestamp": ppv_result.processing_timestamp.isoformat(),
            "processing_method": "automated",
            "software_used": {
                "name": "PPVDataParser",
                "version": "1.0.0",
                "parameters": ppv_result.parsing_parameters
            },
            "processing_time": ppv_result.processing_time,
            "validation_checks": ppv_result.validation_checks
        }
        
        # Determine measurement quality enum
        if quality_assessment.overall_quality >= 0.9:
            measurement_quality = MeasurementQuality.EXCELLENT
        elif quality_assessment.overall_quality >= 0.8:
            measurement_quality = MeasurementQuality.GOOD
        elif quality_assessment.overall_quality >= 0.6:
            measurement_quality = MeasurementQuality.FAIR
        elif quality_assessment.overall_quality >= 0.4:
            measurement_quality = MeasurementQuality.POOR
        else:
            measurement_quality = MeasurementQuality.INVALID
        
        # Create measurement record
        db = next(get_db())
        try:
            measurement_data = MeasurementData(
                blast_record_id=blast_record_id,
                measurement_name=metadata.get("name", f"PPV Measurement - {filename}"),
                measurement_type=MeasurementType.PPV,
                measurement_quality=measurement_quality,
                measurement_date=metadata.get("measurement_date", datetime.utcnow()),
                measurement_method="sensor_data",
                operator_name=metadata.get("operator_name"),
                equipment_used=metadata.get("equipment_used", "PPV sensor + data logger"),
                measurement_location=sensor_location,
                measured_values=measured_values,
                quality_metrics=quality_metrics,
                file_references=file_references,
                processing_metadata=processing_metadata,
                notes=metadata.get("notes"),
                use_for_training=quality_assessment.is_suitable_for_training,
                use_for_validation=quality_assessment.passes_quality_check
            )
            
            db.add(measurement_data)
            db.commit()
            db.refresh(measurement_data)
            
            return measurement_data
        finally:
            db.close()
    
    async def _validate_fragmentation_inputs(self, images: List[UploadFile], blast_record_id: int):
        """Validate fragmentation image inputs"""
        if not images:
            raise ValueError("No images provided")
        
        if len(images) > self.max_concurrent_uploads:
            raise ValueError(f"Too many images. Maximum: {self.max_concurrent_uploads}")
        
        # Validate blast record exists
        db = next(get_db())
        try:
            blast_record = db.query(BlastRecord).filter(BlastRecord.id == blast_record_id).first()
            if not blast_record:
                raise ValueError(f"Blast record {blast_record_id} not found")
        finally:
            db.close()
        
        # Validate each image
        for i, image in enumerate(images):
            if not image.filename:
                raise ValueError(f"Image {i} has no filename")
            
            file_ext = Path(image.filename).suffix.lower()
            if file_ext not in self.supported_image_formats:
                raise ValueError(f"Unsupported image format: {file_ext}")
            
            if image.size > self.max_file_size:
                raise ValueError(f"Image {i} too large. Maximum: {self.max_file_size / (1024*1024):.1f}MB")
    
    async def _validate_ppv_inputs(self, data_files: List[UploadFile], blast_record_id: int):
        """Validate PPV data file inputs"""
        if not data_files:
            raise ValueError("No data files provided")
        
        if len(data_files) > self.max_concurrent_uploads:
            raise ValueError(f"Too many files. Maximum: {self.max_concurrent_uploads}")
        
        # Validate blast record exists
        db = next(get_db())
        try:
            blast_record = db.query(BlastRecord).filter(BlastRecord.id == blast_record_id).first()
            if not blast_record:
                raise ValueError(f"Blast record {blast_record_id} not found")
        finally:
            db.close()
        
        # Validate each file
        for i, data_file in enumerate(data_files):
            if not data_file.filename:
                raise ValueError(f"Data file {i} has no filename")
            
            file_ext = Path(data_file.filename).suffix.lower()
            if file_ext not in self.supported_ppv_formats:
                raise ValueError(f"Unsupported PPV data format: {file_ext}")
            
            if data_file.size > self.max_file_size:
                raise ValueError(f"Data file {i} too large. Maximum: {self.max_file_size / (1024*1024):.1f}MB")


# Global service instance
_data_ingestion_service: Optional[DataIngestionService] = None


def get_data_ingestion_service() -> DataIngestionService:
    """Get or create data ingestion service instance"""
    global _data_ingestion_service
    
    if _data_ingestion_service is None:
        _data_ingestion_service = DataIngestionService()
    
    return _data_ingestion_service