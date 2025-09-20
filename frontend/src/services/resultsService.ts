import apiService from './api';
import { 
  OptimizationResult, 
  BlastPlan,
  SafetyStatus,
  ApiResponse 
} from '../types';

export interface SignOffData {
  engineer_name: string;
  engineer_license: string;
  certification_statement: string;
  safety_acknowledgment: boolean;
  regulatory_compliance: boolean;
  technical_review: boolean;
  signature_timestamp: string;
  comments?: string;
}

export interface ExportOptions {
  format: string;
  include_safety_report: boolean;
  include_hole_details: boolean;
  include_predictions: boolean;
  include_measurements: boolean;
  include_engineer_signoff: boolean;
  filename_prefix?: string;
  coordinate_system?: string;
  units?: string;
}

export interface PlanModifications {
  modified_holes: any[];
  global_adjustments: {
    charge_multiplier?: number;
    delay_offset?: number;
    stemming_adjustment?: number;
  };
  validation_required: boolean;
}

export class ResultsService {
  /**
   * Get safety validation for a blast plan
   */
  async validateBlastPlan(blastId: number, revalidate: boolean = false): Promise<ApiResponse<SafetyStatus>> {
    return apiService.get(`/safety/validate/${blastId}?revalidate=${revalidate}`);
  }

  /**
   * Submit engineer sign-off for a blast plan
   */
  async signOffBlastPlan(
    blastId: number, 
    signOffData: SignOffData
  ): Promise<ApiResponse<{ success: boolean; audit_id: string }>> {
    return apiService.post(`/blast-plans/${blastId}/sign-off`, signOffData);
  }

  /**
   * Export blast plan in specified format
   */
  async exportBlastPlan(
    blastId: number,
    format: string,
    options: ExportOptions
  ): Promise<Blob> {
    const params = new URLSearchParams({
      include_safety_report: options.include_safety_report.toString(),
      include_hole_details: options.include_hole_details.toString(),
      include_predictions: options.include_predictions.toString(),
      include_measurements: options.include_measurements.toString()
    });

    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const response = await fetch(
      `${baseURL}/exports/blast-plans/${blastId}/export/${format}?${params}`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Export multiple blast plans
   */
  async exportMultipleBlastPlans(
    blastIds: number[],
    format: string,
    options: ExportOptions
  ): Promise<Blob> {
    const exportRequest = {
      blast_ids: blastIds,
      format: format,
      include_safety_report: options.include_safety_report,
      include_hole_details: options.include_hole_details,
      include_predictions: options.include_predictions,
      include_measurements: options.include_measurements,
      include_engineer_signoff: options.include_engineer_signoff,
      filename_prefix: options.filename_prefix,
      coordinate_system: options.coordinate_system,
      units: options.units
    };

    const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const response = await fetch(
      `${baseURL}/exports/blast-plans/export`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(exportRequest)
      }
    );

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Modify blast plan with new parameters
   */
  async modifyBlastPlan(
    blastId: number,
    modifications: PlanModifications
  ): Promise<ApiResponse<OptimizationResult>> {
    return apiService.put(`/blast-plans/${blastId}/modify`, modifications);
  }

  /**
   * Compare multiple optimization results
   */
  async compareOptimizationResults(
    resultIds: string[]
  ): Promise<ApiResponse<{
    comparison_metrics: any;
    statistical_analysis: any;
    recommendations: string[];
  }>> {
    return apiService.post('/optimization/compare', { result_ids: resultIds });
  }

  /**
   * Get fragmentation curve data for visualization
   */
  async getFragmentationCurveData(
    blastId: number
  ): Promise<ApiResponse<{
    predicted_curve: any;
    measured_curve?: any;
    sieve_analysis: any[];
  }>> {
    return apiService.get(`/blast-plans/${blastId}/fragmentation-curve`);
  }

  /**
   * Get safety validation details
   */
  async getSafetyValidationDetails(
    blastId: number
  ): Promise<ApiResponse<{
    safety_checks: any[];
    violations: any[];
    recommendations: string[];
    safety_margins: any;
  }>> {
    return apiService.get(`/safety/validate/${blastId}/details`);
  }

  /**
   * Download exported file
   */
  downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Generate filename for export
   */
  generateExportFilename(
    format: string,
    prefix: string = 'blast_plan',
    timestamp: boolean = true
  ): string {
    const extensions: Record<string, string> = {
      pdf: '.pdf',
      csv: '.csv',
      json: '.json',
      geojson: '.geojson'
    };

    const extension = extensions[format] || '.txt';
    const timestampStr = timestamp ? `_${new Date().toISOString().split('T')[0]}` : '';
    
    return `${prefix}${timestampStr}${extension}`;
  }

  /**
   * Validate export permissions
   */
  async validateExportPermissions(blastId: number): Promise<ApiResponse<{
    can_export: boolean;
    blocking_reasons: string[];
    requirements: string[];
  }>> {
    return apiService.get(`/blast-plans/${blastId}/export-validation`);
  }

  /**
   * Get export audit log
   */
  async getExportAuditLog(
    blastId?: number,
    limit: number = 50
  ): Promise<ApiResponse<{
    audit_entries: any[];
    total_count: number;
  }>> {
    const params = new URLSearchParams({
      limit: limit.toString()
    });
    
    if (blastId) {
      params.append('blast_id', blastId.toString());
    }

    return apiService.get(`/exports/audit-logs?${params}`);
  }

  /**
   * Get available export formats
   */
  getAvailableExportFormats(): Array<{
    id: string;
    name: string;
    description: string;
    features: string[];
    file_extension: string;
  }> {
    return [
      {
        id: 'pdf',
        name: 'PDF Report',
        description: 'Complete blast plan report with maps and tables',
        features: ['Maps', 'Tables', 'Safety Report', 'Sign-off', 'Visualizations'],
        file_extension: '.pdf'
      },
      {
        id: 'csv',
        name: 'CSV Data',
        description: 'Hole data in comma-separated values format',
        features: ['Hole Coordinates', 'Charge Data', 'Timing', 'Machine Readable'],
        file_extension: '.csv'
      },
      {
        id: 'json',
        name: 'JSON Data',
        description: 'Complete plan data in JSON format',
        features: ['Complete Data', 'API Compatible', 'Structured Format', 'Metadata'],
        file_extension: '.json'
      },
      {
        id: 'geojson',
        name: 'GeoJSON',
        description: 'Geographic data for GIS integration',
        features: ['GIS Compatible', 'Spatial Data', 'Coordinate Systems', 'Mapping'],
        file_extension: '.geojson'
      }
    ];
  }
}

export const resultsService = new ResultsService();
export default resultsService;