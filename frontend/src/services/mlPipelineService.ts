/**
 * ML Pipeline Service
 * 
 * Handles API calls for machine learning pipeline functionality including
 * fragmentation analysis, residual learning, and performance monitoring.
 */

import { api } from './api';

// Types for ML Pipeline
export interface FragmentationAnalysisRequest {
  image: File;
  scaleX1?: number;
  scaleY1?: number;
  scaleX2?: number;
  scaleY2?: number;
  knownScaleMmPerPixel?: number;
}

export interface FragmentationAnalysisResult {
  p10_mm: number;
  p50_mm: number;
  p80_mm: number;
  mean_size_mm: number;
  characteristic_size_mm: number;
  uniformity_index: number;
  fragment_count: number;
  total_analyzed_area_mm2: number;
  measurement_quality: number;
  scale_detection_quality: number;
  segmentation_quality: number;
  is_valid: boolean;
  scale_factor_mm_per_pixel: number;
  processing_timestamp: string;
  quality_flags: string[];
}

export interface ResidualLearningPrediction {
  physics_prediction: number;
  ml_correction: number;
  corrected_prediction: number;
  confidence: number;
  prediction_type: string;
  target: string;
}

export interface BlastParameters {
  burden_m: number;
  spacing_m: number;
  bench_height_m: number;
  hole_diameter_mm: number;
  stemming_length_m: number;
  powder_factor_kg_per_t: number;
  powder_factor_kg_per_m3: number;
  rock_density_kg_m3: number;
  explosive_rws: number;
  explosive_density_kg_m3: number;
}

export interface ModelStatus {
  is_trained: boolean;
  model_version: string;
  last_training_date?: string;
  training_samples: number;
  validation_r2: number;
  is_reliable: boolean;
  feature_count: number;
  training_history_count: number;
}

export interface RetrainingRecommendation {
  should_retrain: boolean;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  reasons: string[];
  recommended_action: string;
  estimated_improvement: number;
}

export interface PerformanceMetrics {
  timestamp: string;
  validation_r2: number;
  validation_rmse: number;
  training_samples: number;
  is_reliable: boolean;
  drift_detected: boolean;
}

export interface BatchJobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total_items: number;
  completed_items: number;
  failed_items: number;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

class MLPipelineService {
  /**
   * Analyze fragmentation from muckpile image
   */
  async analyzeFragmentation(request: FragmentationAnalysisRequest) {
    const formData = new FormData();
    formData.append('image', request.image);
    
    if (request.scaleX1 !== undefined) formData.append('scale_x1', request.scaleX1.toString());
    if (request.scaleY1 !== undefined) formData.append('scale_y1', request.scaleY1.toString());
    if (request.scaleX2 !== undefined) formData.append('scale_x2', request.scaleX2.toString());
    if (request.scaleY2 !== undefined) formData.append('scale_y2', request.scaleY2.toString());
    if (request.knownScaleMmPerPixel !== undefined) {
      formData.append('known_scale_mm_per_pixel', request.knownScaleMmPerPixel.toString());
    }

    const response = await api.post('/ml/analyze-fragmentation', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Get analyzer status and capabilities
   */
  async getAnalyzerStatus() {
    const response = await api.get('/ml/analyzer-status');
    return response.data;
  }

  /**
   * Test segmentation methods comparison
   */
  async testSegmentation(image: File) {
    const formData = new FormData();
    formData.append('image', image);

    const response = await api.post('/ml/test-segmentation', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Train residual learning model
   */
  async trainResidualModel(blastRecordIds: number[], validationSplit = 0.2, cvFolds = 5) {
    const params = new URLSearchParams();
    blastRecordIds.forEach(id => params.append('blast_record_ids', id.toString()));
    params.append('validation_split', validationSplit.toString());
    params.append('cross_validation_folds', cvFolds.toString());

    const response = await api.post(`/ml/residual-learning/train?${params.toString()}`);
    return response.data;
  }

  /**
   * Make prediction with residual correction
   */
  async predictWithCorrection(params: BlastParameters, predictionType = 'fragmentation') {
    const queryParams = new URLSearchParams({
      burden_m: params.burden_m.toString(),
      spacing_m: params.spacing_m.toString(),
      bench_height_m: params.bench_height_m.toString(),
      hole_diameter_mm: params.hole_diameter_mm.toString(),
      stemming_length_m: params.stemming_length_m.toString(),
      powder_factor_kg_per_t: params.powder_factor_kg_per_t.toString(),
      powder_factor_kg_per_m3: params.powder_factor_kg_per_m3.toString(),
      rock_density_kg_m3: params.rock_density_kg_m3.toString(),
      explosive_rws: params.explosive_rws.toString(),
      explosive_density_kg_m3: params.explosive_density_kg_m3.toString(),
      prediction_type: predictionType,
    });

    const response = await api.post(`/ml/residual-learning/predict?${queryParams.toString()}`);
    return response.data;
  }

  /**
   * Get residual learning model status
   */
  async getResidualLearningStatus() {
    const response = await api.get('/ml/residual-learning/status');
    return response.data;
  }

  /**
   * Monitor prediction performance
   */
  async monitorPrediction(predictedValue: number, actualValue: number, timestamp?: string) {
    const params = new URLSearchParams({
      predicted_value: predictedValue.toString(),
      actual_value: actualValue.toString(),
    });

    if (timestamp) {
      params.append('prediction_timestamp', timestamp);
    }

    const response = await api.post(`/ml/residual-learning/monitor-prediction?${params.toString()}`);
    return response.data;
  }

  /**
   * Export model diagnostics
   */
  async exportModelDiagnostics() {
    const response = await api.get('/ml/residual-learning/diagnostics');
    return response.data;
  }

  /**
   * Ingest fragmentation images
   */
  async ingestFragmentationImages(
    blastRecordId: number,
    images: File[],
    metadata: {
      measurementName?: string;
      operatorName?: string;
      equipmentUsed?: string;
      measurementDate?: string;
      notes?: string;
    }
  ) {
    const formData = new FormData();
    formData.append('blast_record_id', blastRecordId.toString());
    
    images.forEach(image => {
      formData.append('images', image);
    });

    if (metadata.measurementName) formData.append('measurement_name', metadata.measurementName);
    if (metadata.operatorName) formData.append('operator_name', metadata.operatorName);
    if (metadata.equipmentUsed) formData.append('equipment_used', metadata.equipmentUsed);
    if (metadata.measurementDate) formData.append('measurement_date', metadata.measurementDate);
    if (metadata.notes) formData.append('notes', metadata.notes);

    const response = await api.post('/ml/ingest-fragmentation-images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Ingest PPV data files
   */
  async ingestPPVData(
    blastRecordId: number,
    dataFiles: File[],
    metadata: {
      measurementName?: string;
      operatorName?: string;
      equipmentUsed?: string;
      measurementDate?: string;
      notes?: string;
    }
  ) {
    const formData = new FormData();
    formData.append('blast_record_id', blastRecordId.toString());
    
    dataFiles.forEach(file => {
      formData.append('data_files', file);
    });

    if (metadata.measurementName) formData.append('measurement_name', metadata.measurementName);
    if (metadata.operatorName) formData.append('operator_name', metadata.operatorName);
    if (metadata.equipmentUsed) formData.append('equipment_used', metadata.equipmentUsed);
    if (metadata.measurementDate) formData.append('measurement_date', metadata.measurementDate);
    if (metadata.notes) formData.append('notes', metadata.notes);

    const response = await api.post('/ml/ingest-ppv-data', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Submit batch processing job
   */
  async submitBatchJob(
    blastRecordId: number,
    fragmentationImages?: File[],
    ppvFiles?: File[],
    metadata?: {
      measurementName?: string;
      operatorName?: string;
      equipmentUsed?: string;
      measurementDate?: string;
      notes?: string;
    }
  ) {
    const formData = new FormData();
    formData.append('blast_record_id', blastRecordId.toString());

    if (fragmentationImages) {
      fragmentationImages.forEach(image => {
        formData.append('fragmentation_images', image);
      });
    }

    if (ppvFiles) {
      ppvFiles.forEach(file => {
        formData.append('ppv_files', file);
      });
    }

    if (metadata) {
      if (metadata.measurementName) formData.append('measurement_name', metadata.measurementName);
      if (metadata.operatorName) formData.append('operator_name', metadata.operatorName);
      if (metadata.equipmentUsed) formData.append('equipment_used', metadata.equipmentUsed);
      if (metadata.measurementDate) formData.append('measurement_date', metadata.measurementDate);
      if (metadata.notes) formData.append('notes', metadata.notes);
    }

    const response = await api.post('/ml/batch-ingest-measurements', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  /**
   * Get batch job status
   */
  async getBatchStatus(jobId: string) {
    const response = await api.get(`/ml/batch-status/${jobId}`);
    return response.data;
  }

  /**
   * Get batch job results
   */
  async getBatchResults(jobId: string) {
    const response = await api.get(`/ml/batch-results/${jobId}`);
    return response.data;
  }

  /**
   * Cancel batch job
   */
  async cancelBatchJob(jobId: string) {
    const response = await api.delete(`/ml/batch-job/${jobId}`);
    return response.data;
  }
}

export const mlPipelineService = new MLPipelineService();
export default mlPipelineService;