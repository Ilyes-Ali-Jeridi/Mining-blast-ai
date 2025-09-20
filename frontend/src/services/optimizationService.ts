import apiService from './api';
import { 
  OptimizationSession, 
  OptimizationConfig, 
  OptimizationHistory,
  ApiResponse 
} from '../types';

export class OptimizationService {
  /**
   * Start asynchronous optimization for a blast plan
   */
  async startOptimization(
    blastId: number, 
    config?: OptimizationConfig
  ): Promise<ApiResponse<OptimizationSession>> {
    return apiService.post(`/optimization/${blastId}/optimize-async`, config);
  }

  /**
   * Get current optimization status
   */
  async getOptimizationStatus(optimizationId: string): Promise<ApiResponse<OptimizationSession>> {
    return apiService.get(`/optimization/status/${optimizationId}`);
  }

  /**
   * Cancel a running optimization
   */
  async cancelOptimization(optimizationId: string): Promise<ApiResponse<{ status: string }>> {
    return apiService.post(`/optimization/cancel/${optimizationId}`);
  }

  /**
   * List all active optimizations
   */
  async listActiveOptimizations(): Promise<ApiResponse<{ active_optimizations: OptimizationSession[] }>> {
    return apiService.get('/optimization/active');
  }

  /**
   * Get optimization history for a blast plan
   */
  async getOptimizationHistory(blastId: number): Promise<ApiResponse<OptimizationHistory>> {
    return apiService.get(`/blast-plans/${blastId}/optimization-history`);
  }

  /**
   * Get optimization results
   */
  async getOptimizationResults(optimizationId: string): Promise<ApiResponse<any>> {
    return apiService.get(`/optimization/results/${optimizationId}`);
  }

  /**
   * Save optimization configuration as preset
   */
  async saveOptimizationPreset(
    name: string, 
    config: OptimizationConfig
  ): Promise<ApiResponse<{ id: number }>> {
    return apiService.post('/optimization/presets', { name, config });
  }

  /**
   * Get optimization configuration presets
   */
  async getOptimizationPresets(): Promise<ApiResponse<Array<{ id: number; name: string; config: OptimizationConfig }>>> {
    return apiService.get('/optimization/presets');
  }

  /**
   * Delete optimization configuration preset
   */
  async deleteOptimizationPreset(presetId: number): Promise<ApiResponse<{ success: boolean }>> {
    return apiService.delete(`/optimization/presets/${presetId}`);
  }
}

export const optimizationService = new OptimizationService();
export default optimizationService;