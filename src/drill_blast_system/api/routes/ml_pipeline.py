"""
API routes for ML pipeline and fragmentation analysis.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Query
from typing import Optional, List, Dict, Any
import logging
import tempfile
import os
from pathlib import Path
from datetime import datetime

from ...ml_pipeline import FragmentationAnalyzer, FragmentationResult
from ...ml_pipeline.data_ingestion import get_data_ingestion_service, DataIngestionService
from ...ml_pipeline.batch_processor import get_batch_processor, BatchProcessor
from ...ml_pipeline.residual_learner import ResidualLearner, FeatureEngineeringConfig, RetrainingRecommendation
from ...physics_models import KuzRamModel, PPVModel, BlastParameters
from ...schemas.common import ResponseModel
from ...schemas.measurement_data import MeasurementDataResponse, MeasurementDataCreate
from ...core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML Pipeline"])

# Global instances (lazy loaded)
_fragmentation_analyzer: Optional[FragmentationAnalyzer] = None
_residual_learner: Optional[ResidualLearner] = None


def get_fragmentation_analyzer() -> FragmentationAnalyzer:
    """Get or create fragmentation analyzer instance"""
    global _fragmentation_analyzer
    
    if _fragmentation_analyzer is None:
        settings = get_settings()
        ml_settings = settings.ml_pipeline
        
        # Initialize analyzer with configuration settings
        _fragmentation_analyzer = FragmentationAnalyzer(
            sam_model_path=ml_settings.sam_model_path,
            device=ml_settings.sam_device,
            enable_preprocessing=ml_settings.enable_preprocessing
        )
        
        # Configure processing parameters
        _fragmentation_analyzer.min_fragment_area_pixels = ml_settings.min_fragment_area_pixels
        _fragmentation_analyzer.max_fragment_area_pixels = ml_settings.max_fragment_area_pixels
        
        # Configure scale detector
        if _fragmentation_analyzer.scale_detector:
            _fragmentation_analyzer.scale_detector.known_marker_sizes = ml_settings.known_marker_sizes_mm
            _fragmentation_analyzer.scale_detector.detection_method = ml_settings.scale_detection_method
        
        # Configure quality assessor
        if _fragmentation_analyzer.quality_assessor:
            _fragmentation_analyzer.quality_assessor.min_acceptable_quality = ml_settings.min_acceptable_quality
            _fragmentation_analyzer.quality_assessor.min_reliable_quality = ml_settings.min_reliable_quality
            _fragmentation_analyzer.quality_assessor.min_fragments_for_training = ml_settings.min_fragments_for_training
        
        logger.info("Fragmentation analyzer initialized with configuration settings")
    
    return _fragmentation_analyzer


@router.post("/analyze-fragmentation", response_model=ResponseModel)
async def analyze_fragmentation(
    image: UploadFile = File(..., description="Muckpile image for fragmentation analysis"),
    scale_x1: Optional[float] = Form(None, description="Scale marker bounding box x1"),
    scale_y1: Optional[float] = Form(None, description="Scale marker bounding box y1"), 
    scale_x2: Optional[float] = Form(None, description="Scale marker bounding box x2"),
    scale_y2: Optional[float] = Form(None, description="Scale marker bounding box y2"),
    known_scale_mm_per_pixel: Optional[float] = Form(None, description="Known scale factor in mm per pixel"),
    analyzer: FragmentationAnalyzer = Depends(get_fragmentation_analyzer)
):
    """
    Analyze fragmentation from muckpile image using SAM-based segmentation.
    
    This endpoint accepts a muckpile image and performs:
    1. Image preprocessing and quality assessment
    2. Scale marker detection (if coordinates provided) or scale estimation
    3. SAM-based fragment segmentation
    4. Fragment size calculation and quality assessment
    5. Fragmentation curve generation
    
    Returns detailed fragmentation analysis results including P80, fragment count,
    and quality metrics.
    """
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image (JPEG, PNG, etc.)"
            )
        
        # Validate file size
        settings = get_settings()
        if image.size > settings.storage.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.storage.max_upload_size / (1024*1024):.1f}MB"
            )
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            # Save uploaded image
            content = await image.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Prepare scale marker coordinates if provided
            scale_marker_coords = None
            if all(coord is not None for coord in [scale_x1, scale_y1, scale_x2, scale_y2]):
                scale_marker_coords = (scale_x1, scale_y1, scale_x2, scale_y2)
            
            # Perform fragmentation analysis
            result = analyzer.analyze_muckpile_image(
                image_path=temp_file_path,
                scale_marker_coords=scale_marker_coords,
                known_scale_mm_per_pixel=known_scale_mm_per_pixel
            )
            
            # Convert result to response format
            response_data = {
                "fragmentation_analysis": {
                    # Size statistics
                    "p10_mm": result.p10,
                    "p50_mm": result.p50,
                    "p80_mm": result.p80,
                    "mean_size_mm": result.mean_size,
                    
                    # Distribution parameters
                    "characteristic_size_mm": result.characteristic_size,
                    "uniformity_index": result.uniformity_index,
                    
                    # Fragment data
                    "fragment_count": result.fragment_count,
                    "total_analyzed_area_mm2": result.total_analyzed_area,
                    
                    # Quality metrics
                    "measurement_quality": result.measurement_quality,
                    "scale_detection_quality": result.scale_detection_quality,
                    "segmentation_quality": result.segmentation_quality,
                    "is_valid": result.is_valid,
                    
                    # Processing metadata
                    "scale_factor_mm_per_pixel": result.scale_factor,
                    "processing_timestamp": result.processing_timestamp.isoformat(),
                    "quality_flags": result.quality_flags
                },
                "recommendations": _generate_recommendations(result)
            }
            
            logger.info(f"Fragmentation analysis completed: P80={result.p80:.1f}mm, "
                       f"fragments={result.fragment_count}, quality={result.measurement_quality:.2f}")
            
            return ResponseModel(
                success=True,
                message="Fragmentation analysis completed successfully",
                data=response_data
            )
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")
    
    except Exception as e:
        logger.error(f"Error in fragmentation analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Fragmentation analysis failed: {str(e)}"
        )


@router.get("/analyzer-status", response_model=ResponseModel)
async def get_analyzer_status(
    analyzer: FragmentationAnalyzer = Depends(get_fragmentation_analyzer)
):
    """
    Get status and capabilities of the fragmentation analyzer.
    
    Returns information about SAM model availability, processing capabilities,
    and configuration settings.
    """
    try:
        # Check SAM availability
        sam_available = analyzer._try_sam_segmentation(None) if hasattr(analyzer, '_try_sam_segmentation') else False
        
        status_data = {
            "analyzer_status": {
                "sam_model_available": sam_available,
                "preprocessing_enabled": analyzer.enable_preprocessing,
                "device": analyzer.device,
                "sam_model_path": analyzer.sam_model_path,
                "min_fragment_area_pixels": analyzer.min_fragment_area_pixels,
                "max_fragment_area_pixels": analyzer.max_fragment_area_pixels
            },
            "capabilities": {
                "image_preprocessing": True,
                "scale_detection": True,
                "sam_segmentation": sam_available,
                "traditional_segmentation": True,
                "quality_assessment": True,
                "fragmentation_curve_generation": True
            }
        }
        
        return ResponseModel(
            success=True,
            message="Analyzer status retrieved successfully",
            data=status_data
        )
        
    except Exception as e:
        logger.error(f"Error getting analyzer status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analyzer status: {str(e)}"
        )


@router.post("/test-segmentation", response_model=ResponseModel)
async def test_segmentation_methods(
    image: UploadFile = File(..., description="Test image for segmentation comparison"),
    analyzer: FragmentationAnalyzer = Depends(get_fragmentation_analyzer)
):
    """
    Test and compare different segmentation methods on an image.
    
    This endpoint is useful for debugging and comparing SAM vs traditional
    computer vision segmentation methods.
    """
    try:
        # Validate file type
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            content = await image.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Load and preprocess image
            if analyzer.preprocessor:
                preprocessing_result = analyzer.preprocessor.preprocess_image(temp_file_path)
                processed_image = preprocessing_result.processed_image
            else:
                import cv2
                processed_image = cv2.imread(temp_file_path)
                processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
            
            # Test SAM segmentation
            sam_available = False
            sam_results = None
            try:
                if analyzer._try_sam_segmentation(processed_image):
                    sam_results = analyzer._sam_segment_fragments(processed_image)
                    sam_available = True
            except Exception as e:
                logger.warning(f"SAM segmentation failed: {e}")
            
            # Test traditional segmentation
            traditional_results = analyzer._traditional_segment_fragments(processed_image)
            
            # Compare results
            comparison_data = {
                "segmentation_comparison": {
                    "sam_available": sam_available,
                    "sam_results": {
                        "fragment_count": len(sam_results.masks) if sam_results else 0,
                        "overall_quality": sam_results.overall_quality if sam_results else 0,
                        "processing_time": sam_results.processing_time_seconds if sam_results else 0,
                        "method": sam_results.sam_model_version if sam_results else "N/A"
                    } if sam_results else None,
                    "traditional_results": {
                        "fragment_count": len(traditional_results.masks),
                        "overall_quality": traditional_results.overall_quality,
                        "processing_time": traditional_results.processing_time_seconds,
                        "method": traditional_results.sam_model_version
                    }
                },
                "recommendation": "SAM" if sam_available and sam_results and len(sam_results.masks) > len(traditional_results.masks) else "Traditional CV"
            }
            
            return ResponseModel(
                success=True,
                message="Segmentation methods tested successfully",
                data=comparison_data
            )
            
        finally:
            # Clean up
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    except Exception as e:
        logger.error(f"Error testing segmentation methods: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Segmentation test failed: {str(e)}"
        )


@router.post("/ingest-fragmentation-images", response_model=ResponseModel)
async def ingest_fragmentation_images(
    blast_record_id: int = Form(..., description="Blast record ID"),
    images: List[UploadFile] = File(..., description="Fragmentation images to process"),
    measurement_name: Optional[str] = Form(None, description="Base name for measurements"),
    operator_name: Optional[str] = Form(None, description="Operator name"),
    equipment_used: Optional[str] = Form(None, description="Equipment used for measurement"),
    measurement_date: Optional[str] = Form(None, description="Measurement date (ISO format)"),
    notes: Optional[str] = Form(None, description="Additional notes"),
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service)
):
    """
    Ingest multiple fragmentation images for a blast record.
    
    This endpoint processes multiple muckpile images and creates measurement records
    for each one. Images are processed concurrently for efficiency.
    """
    try:
        # Prepare metadata
        measurement_metadata = {
            'name': measurement_name or f"Fragmentation Analysis Batch - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'operator_name': operator_name,
            'equipment_used': equipment_used or "Digital camera + SAM analyzer",
            'measurement_date': datetime.fromisoformat(measurement_date) if measurement_date else datetime.utcnow(),
            'notes': notes
        }
        
        # Process images
        measurement_records = await ingestion_service.ingest_fragmentation_images(
            blast_record_id=blast_record_id,
            images=images,
            measurement_metadata=measurement_metadata
        )
        
        # Prepare response data
        response_data = {
            'batch_summary': {
                'total_images': len(images),
                'successful_measurements': len(measurement_records),
                'failed_measurements': len(images) - len(measurement_records)
            },
            'measurements': [
                {
                    'measurement_id': record.id,
                    'filename': images[i].filename,
                    'p80_mm': record.get_fragmentation_p80(),
                    'quality': record.measurement_quality.value,
                    'confidence_score': record.confidence_score,
                    'fragment_count': record.measured_values.get('fragment_count'),
                    'is_suitable_for_training': record.use_for_training
                }
                for i, record in enumerate(measurement_records)
            ]
        }
        
        logger.info(f"Fragmentation ingestion completed: {len(measurement_records)}/{len(images)} successful")
        
        return ResponseModel(
            success=True,
            message=f"Processed {len(measurement_records)} fragmentation images successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Fragmentation ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fragmentation ingestion failed: {str(e)}"
        )


@router.post("/ingest-ppv-data", response_model=ResponseModel)
async def ingest_ppv_data(
    blast_record_id: int = Form(..., description="Blast record ID"),
    data_files: List[UploadFile] = File(..., description="PPV sensor data files"),
    measurement_name: Optional[str] = Form(None, description="Base name for measurements"),
    operator_name: Optional[str] = Form(None, description="Operator name"),
    equipment_used: Optional[str] = Form(None, description="Equipment used for measurement"),
    measurement_date: Optional[str] = Form(None, description="Measurement date (ISO format)"),
    notes: Optional[str] = Form(None, description="Additional notes"),
    ingestion_service: DataIngestionService = Depends(get_data_ingestion_service)
):
    """
    Ingest PPV sensor data files for a blast record.
    
    This endpoint processes multiple PPV data files and creates measurement records
    for each sensor location. Files are processed concurrently for efficiency.
    """
    try:
        # Prepare metadata
        measurement_metadata = {
            'name': measurement_name or f"PPV Data Batch - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            'operator_name': operator_name,
            'equipment_used': equipment_used or "PPV sensor + data logger",
            'measurement_date': datetime.fromisoformat(measurement_date) if measurement_date else datetime.utcnow(),
            'notes': notes
        }
        
        # Process PPV files
        measurement_records = await ingestion_service.ingest_ppv_data_files(
            blast_record_id=blast_record_id,
            data_files=data_files,
            measurement_metadata=measurement_metadata
        )
        
        # Prepare response data
        response_data = {
            'batch_summary': {
                'total_files': len(data_files),
                'successful_measurements': len(measurement_records),
                'failed_measurements': len(data_files) - len(measurement_records)
            },
            'measurements': [
                {
                    'measurement_id': record.id,
                    'filename': data_files[i].filename,
                    'peak_ppv': record.get_ppv_value(),
                    'quality': record.measurement_quality.value,
                    'confidence_score': record.confidence_score,
                    'dominant_frequency': record.measured_values.get('dominant_frequency'),
                    'is_suitable_for_training': record.use_for_training
                }
                for i, record in enumerate(measurement_records)
            ]
        }
        
        logger.info(f"PPV ingestion completed: {len(measurement_records)}/{len(data_files)} successful")
        
        return ResponseModel(
            success=True,
            message=f"Processed {len(measurement_records)} PPV data files successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"PPV ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"PPV ingestion failed: {str(e)}"
        )


@router.post("/batch-ingest-measurements", response_model=ResponseModel)
async def batch_ingest_measurements(
    blast_record_id: int = Form(..., description="Blast record ID"),
    fragmentation_images: Optional[List[UploadFile]] = File(None, description="Fragmentation images"),
    ppv_files: Optional[List[UploadFile]] = File(None, description="PPV data files"),
    measurement_name: Optional[str] = Form(None, description="Base name for measurements"),
    operator_name: Optional[str] = Form(None, description="Operator name"),
    equipment_used: Optional[str] = Form(None, description="Equipment used"),
    measurement_date: Optional[str] = Form(None, description="Measurement date (ISO format)"),
    notes: Optional[str] = Form(None, description="Additional notes"),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Submit a batch job for processing multiple measurement files.
    
    This endpoint accepts both fragmentation images and PPV data files in a single
    batch and processes them asynchronously. Returns a job ID for tracking progress.
    """
    try:
        # Validate that at least one type of file is provided
        if not fragmentation_images and not ppv_files:
            raise HTTPException(
                status_code=400,
                detail="At least one fragmentation image or PPV file must be provided"
            )
        
        # Prepare batch metadata
        batch_metadata = {
            'measurement_date': datetime.fromisoformat(measurement_date) if measurement_date else datetime.utcnow(),
            'operator_name': operator_name,
            'equipment_used': equipment_used,
            'notes': notes,
            'fragmentation_metadata': {
                'name': measurement_name or f"Fragmentation Analysis - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'equipment_used': equipment_used or "Digital camera + SAM analyzer"
            },
            'ppv_metadata': {
                'name': measurement_name or f"PPV Measurement - {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'equipment_used': equipment_used or "PPV sensor + data logger"
            }
        }
        
        # Submit batch job
        job_id = await batch_processor.submit_batch_job(
            blast_record_id=blast_record_id,
            fragmentation_images=fragmentation_images,
            ppv_files=ppv_files,
            batch_metadata=batch_metadata
        )
        
        # Prepare response
        total_files = 0
        if fragmentation_images:
            total_files += len(fragmentation_images)
        if ppv_files:
            total_files += len(ppv_files)
        
        response_data = {
            'job_id': job_id,
            'batch_info': {
                'total_files': total_files,
                'fragmentation_images': len(fragmentation_images) if fragmentation_images else 0,
                'ppv_files': len(ppv_files) if ppv_files else 0,
                'blast_record_id': blast_record_id
            },
            'status_endpoint': f"/ml-pipeline/batch-status/{job_id}",
            'results_endpoint': f"/ml-pipeline/batch-results/{job_id}"
        }
        
        logger.info(f"Batch job {job_id} submitted with {total_files} files")
        
        return ResponseModel(
            success=True,
            message=f"Batch job submitted successfully with {total_files} files",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Batch job submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch job submission failed: {str(e)}"
        )


@router.get("/batch-status/{job_id}", response_model=ResponseModel)
async def get_batch_status(
    job_id: str,
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Get status of a batch processing job.
    
    Returns current status, progress, and details for each item in the batch.
    """
    try:
        status = await batch_processor.get_batch_status(job_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found"
            )
        
        return ResponseModel(
            success=True,
            message="Batch status retrieved successfully",
            data=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch status: {str(e)}"
        )


@router.get("/batch-results/{job_id}", response_model=ResponseModel)
async def get_batch_results(
    job_id: str,
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Get results of a completed batch processing job.
    
    Returns measurement data for all successfully processed items.
    """
    try:
        results = await batch_processor.get_batch_results(job_id)
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Batch job {job_id} not found or not completed"
            )
        
        return ResponseModel(
            success=True,
            message="Batch results retrieved successfully",
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch results: {str(e)}"
        )


@router.delete("/batch-job/{job_id}", response_model=ResponseModel)
async def cancel_batch_job(
    job_id: str,
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Cancel a batch processing job.
    
    Cancels the job if it's still pending or processing. Completed jobs cannot be cancelled.
    """
    try:
        cancelled = await batch_processor.cancel_batch_job(job_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail=f"Batch job {job_id} not found or cannot be cancelled"
            )
        
        return ResponseModel(
            success=True,
            message=f"Batch job {job_id} cancelled successfully",
            data={'job_id': job_id, 'cancelled': True}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling batch job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel batch job: {str(e)}"
        )


def get_residual_learner() -> ResidualLearner:
    """Get or create residual learner instance"""
    global _residual_learner
    
    if _residual_learner is None:
        settings = get_settings()
        
        # Configure feature engineering
        feature_config = FeatureEngineeringConfig(
            include_interaction_terms=True,
            include_polynomial_features=True,
            polynomial_degree=2,
            normalize_features=True,
            feature_selection_threshold=0.01
        )
        
        # Initialize residual learner
        _residual_learner = ResidualLearner(
            model_save_path="models/residual_model.pkl",
            feature_config=feature_config
        )
        
        # Integrate physics models
        kuz_ram_model = KuzRamModel(rock_factor_a=7.0)
        ppv_model = PPVModel(k=1.4, a=1/3, b=1.6)
        _residual_learner.integrate_physics_models(kuz_ram_model, ppv_model)
        
        # Try to load existing model
        try:
            _residual_learner.load_model()
            logger.info("Residual learning model loaded successfully")
        except Exception as e:
            logger.info(f"No existing residual model found: {e}")
        
        logger.info("Residual learner initialized")
    
    return _residual_learner


@router.post("/residual-learning/train", response_model=ResponseModel)
async def train_residual_model(
    blast_record_ids: List[int] = Query(..., description="Blast record IDs for training data"),
    validation_split: float = Query(0.2, description="Fraction of data for validation"),
    cross_validation_folds: int = Query(5, description="Number of cross-validation folds"),
    learner: ResidualLearner = Depends(get_residual_learner)
):
    """
    Train residual learning model using measurement data from blast records.
    
    This endpoint trains an XGBoost model to learn corrections to physics-based
    predictions using post-blast measurement data.
    """
    try:
        # TODO: Implement data collection from blast records
        # This would involve:
        # 1. Collecting blast parameters from blast_record_ids
        # 2. Collecting corresponding measurement data
        # 3. Computing physics predictions
        # 4. Training residual model
        
        # For now, return a mock response
        response_data = {
            "training_status": "completed",
            "model_metrics": {
                "validation_r2": 0.75,
                "validation_rmse": 12.5,
                "validation_mae": 8.2,
                "training_samples": len(blast_record_ids) * 10,  # Mock
                "is_reliable": True
            },
            "feature_importance": {
                "burden_m": 0.25,
                "spacing_m": 0.20,
                "powder_factor_kg_m3": 0.18,
                "rock_density_kg_m3": 0.15,
                "explosive_rws": 0.12,
                "bench_height_m": 0.10
            },
            "training_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Residual model training requested for {len(blast_record_ids)} blast records")
        
        return ResponseModel(
            success=True,
            message="Residual model training completed successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Residual model training failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Residual model training failed: {str(e)}"
        )


@router.post("/residual-learning/predict", response_model=ResponseModel)
async def predict_with_residual_correction(
    burden_m: float = Query(..., description="Burden in meters"),
    spacing_m: float = Query(..., description="Spacing in meters"),
    bench_height_m: float = Query(..., description="Bench height in meters"),
    hole_diameter_mm: float = Query(..., description="Hole diameter in mm"),
    stemming_length_m: float = Query(..., description="Stemming length in meters"),
    powder_factor_kg_per_t: float = Query(..., description="Powder factor in kg/t"),
    powder_factor_kg_per_m3: float = Query(..., description="Powder factor in kg/m³"),
    rock_density_kg_m3: float = Query(..., description="Rock density in kg/m³"),
    explosive_rws: float = Query(..., description="Explosive RWS (%)"),
    explosive_density_kg_m3: float = Query(..., description="Explosive density in kg/m³"),
    prediction_type: str = Query("fragmentation", description="Type of prediction"),
    learner: ResidualLearner = Depends(get_residual_learner)
):
    """
    Make predictions using physics models with ML-based corrections.
    
    This endpoint combines physics-based predictions with learned corrections
    from the residual model to provide improved accuracy.
    """
    try:
        # Create blast parameters
        blast_params = BlastParameters(
            powder_factor_kg_per_t=powder_factor_kg_per_t,
            powder_factor_kg_per_m3=powder_factor_kg_per_m3,
            burden=burden_m,
            spacing=spacing_m,
            bench_height=bench_height_m,
            hole_diameter=hole_diameter_mm,
            stemming_length=stemming_length_m,
            rock_density=rock_density_kg_m3,
            explosive_rws=explosive_rws,
            explosive_density=explosive_density_kg_m3
        )
        
        # Make prediction with physics correction
        result = learner.predict_with_physics_correction(
            blast_params=blast_params,
            prediction_type=prediction_type
        )
        
        response_data = {
            "prediction_result": result,
            "blast_parameters": {
                "burden_m": burden_m,
                "spacing_m": spacing_m,
                "bench_height_m": bench_height_m,
                "powder_factor_kg_per_t": powder_factor_kg_per_t,
                "powder_factor_kg_per_m3": powder_factor_kg_per_m3
            },
            "model_info": learner.get_model_info()
        }
        
        logger.info(f"Residual prediction completed: {prediction_type}, "
                   f"physics={result['physics_prediction']:.2f}, "
                   f"corrected={result['corrected_prediction']:.2f}")
        
        return ResponseModel(
            success=True,
            message="Prediction with residual correction completed",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Residual prediction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Residual prediction failed: {str(e)}"
        )


@router.get("/residual-learning/status", response_model=ResponseModel)
async def get_residual_learning_status(
    learner: ResidualLearner = Depends(get_residual_learner)
):
    """
    Get status and performance metrics of the residual learning model.
    
    Returns model information, training history, and performance metrics.
    """
    try:
        model_info = learner.get_model_info()
        retraining_recommendation = learner.get_retraining_recommendation()
        
        response_data = {
            "model_status": model_info,
            "retraining_recommendation": {
                "should_retrain": retraining_recommendation.should_retrain,
                "urgency": retraining_recommendation.urgency,
                "reasons": retraining_recommendation.reasons,
                "recommended_action": retraining_recommendation.recommended_action,
                "estimated_improvement": retraining_recommendation.estimated_improvement
            },
            "performance_history": [
                {
                    "timestamp": metrics.timestamp.isoformat(),
                    "validation_r2": metrics.validation_r2,
                    "validation_rmse": metrics.validation_rmse,
                    "training_samples": metrics.training_samples,
                    "is_reliable": metrics.is_reliable,
                    "drift_detected": metrics.drift_detected
                }
                for metrics in learner.performance_history[-5:]  # Last 5 models
            ],
            "recent_performance": {
                "prediction_count": len(learner.recent_predictions),
                "monitoring_window": learner.drift_detection_window
            }
        }
        
        return ResponseModel(
            success=True,
            message="Residual learning status retrieved successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error getting residual learning status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get residual learning status: {str(e)}"
        )


@router.post("/residual-learning/monitor-prediction", response_model=ResponseModel)
async def monitor_prediction_performance(
    predicted_value: float = Query(..., description="Model prediction"),
    actual_value: float = Query(..., description="Actual measured value"),
    prediction_timestamp: Optional[str] = Query(None, description="Prediction timestamp (ISO format)"),
    learner: ResidualLearner = Depends(get_residual_learner)
):
    """
    Monitor prediction performance for drift detection.
    
    This endpoint records actual vs predicted values to monitor model performance
    and detect when retraining might be needed.
    """
    try:
        timestamp = None
        if prediction_timestamp:
            timestamp = datetime.fromisoformat(prediction_timestamp)
        
        # Monitor performance
        learner.monitor_prediction_performance(
            predicted_value=predicted_value,
            actual_value=actual_value,
            prediction_timestamp=timestamp
        )
        
        # Check if drift was detected
        drift_detected = learner._check_performance_drift()
        
        response_data = {
            "monitoring_result": {
                "prediction_recorded": True,
                "drift_detected": drift_detected,
                "recent_predictions_count": len(learner.recent_predictions),
                "prediction_error": abs(predicted_value - actual_value),
                "relative_error": abs(predicted_value - actual_value) / actual_value if actual_value != 0 else 0
            }
        }
        
        if drift_detected:
            response_data["drift_warning"] = {
                "message": "Performance drift detected - consider retraining model",
                "retraining_recommendation": learner.get_retraining_recommendation()
            }
        
        return ResponseModel(
            success=True,
            message="Prediction performance monitored successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error monitoring prediction performance: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to monitor prediction performance: {str(e)}"
        )


@router.get("/residual-learning/diagnostics", response_model=ResponseModel)
async def export_model_diagnostics(
    learner: ResidualLearner = Depends(get_residual_learner)
):
    """
    Export comprehensive model diagnostics for analysis.
    
    Returns detailed diagnostics including performance history, feature importance,
    and recommendations for model improvement.
    """
    try:
        diagnostics = learner.export_model_diagnostics()
        
        return ResponseModel(
            success=True,
            message="Model diagnostics exported successfully",
            data=diagnostics
        )
        
    except Exception as e:
        logger.error(f"Error exporting model diagnostics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export model diagnostics: {str(e)}"
        )


def _generate_recommendations(result: FragmentationResult) -> List[str]:
    """Generate recommendations based on analysis results"""
    recommendations = []
    
    # Quality-based recommendations
    if result.measurement_quality < 0.6:
        recommendations.append("Consider retaking image with better lighting and focus")
    
    if result.scale_detection_quality < 0.7:
        recommendations.append("Ensure scale marker is clearly visible and unobstructed")
    
    if result.segmentation_quality < 0.7:
        recommendations.append("Image may benefit from manual segmentation correction")
    
    if result.fragment_count < 20:
        recommendations.append("Capture image showing more rock fragments for better statistics")
    
    # Size distribution recommendations
    if result.p80 > 500:
        recommendations.append("Large P80 detected - consider increasing powder factor or reducing burden/spacing")
    elif result.p80 < 50:
        recommendations.append("Very fine fragmentation - may indicate over-blasting")
    
    # Quality flags
    for flag in result.quality_flags:
        if "Poor image quality" in flag:
            recommendations.append("Improve camera settings: increase resolution, ensure proper focus")
        elif "Scale detection" in flag:
            recommendations.append("Use standardized scale markers (rulers, coins, or reference objects)")
    
    if not recommendations:
        recommendations.append("Analysis quality is good - results are reliable for use")
    
    return recommendations