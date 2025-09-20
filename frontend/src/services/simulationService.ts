/**
 * Service for advanced simulation management API calls
 */

import { api } from './api';

// Types for simulation API
export interface SimulationType {
  PHYSICS_ONLY: 'physics_only';
  BLASTFOAM: 'blastfoam';
  YADE: 'yade';
}

export interface SimulationStatus {
  PENDING: 'pending';
  RUNNING: 'running';
  COMPLETED: 'completed';
  FAILED: 'failed';
  CANCELLED: 'cancelled';
}

export interface BlastFoamConfig {
  enabled: boolean;
  mesh_resolution: number;
  simulation_time: number;
  time_step: number;
  parallel_processes: number;
  explosive_density: number;
  detonation_velocity: number;
  chapman_jouguet_pressure: number;
  timeout_seconds: number;
}

export interface YadeConfig {
  enabled: boolean;
  particle_radius_min: number;
  particle_radius_max: number;
  particle_density: number;
  young_modulus: number;
  poisson_ratio: number;
  friction_angle: number;
  cohesion: number;
  tensile_strength: number;
  max_iterations: number;
  convergence_tolerance: number;
  timeout_seconds: number;
}

export interface MeshGeometry {
  bench_vertices: number[][];
  bench_faces: number[][];
  hole_positions: number[][];
  hole_depths: number[];
  hole_diameters: number[];
  charge_positions: number[][];
  charge_masses: number[];
  charge_types: string[];
}

export interface SimulationResult {
  simulation_type: keyof SimulationType;
  success: boolean;
  runtime_seconds: number;
  ppv_predictions: Record<string, number>;
  ppv_time_series: Record<string, number[][]>;
  fragment_sizes?: number[];
  fragment_size_distribution?: Record<string, number>;
  mesh_quality_metrics: Record<string, number>;
  convergence_metrics: Record<string, number>;
  warnings: string[];
  errors: string[];
}

export interface SimulationJob {
  job_id: string;
  simulation_type: keyof SimulationType;
  status: keyof SimulationStatus;
  blast_plan_id?: string;
  priority: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  runtime_seconds?: number;
  result?: SimulationResult;
}

export interface SimulationJobCreate {
  simulation_type: keyof SimulationType;
  geometry: MeshGeometry;
  blast_plan_id?: string;
  blastfoam_config?: BlastFoamConfig;
  yade_config?: YadeConfig;
  priority?: number;
}

export interface SimulationJobList {
  jobs: SimulationJob[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface SimulationComparison {
  simulation_types: string[];
  success_rates: boolean[];
  runtimes: number[];
  fragmentation_comparison: Record<string, any>;
  ppv_comparison: Record<string, any>;
  performance_metrics: Record<string, any>;
}

export interface SimulationCapabilities {
  available_types: (keyof SimulationType)[];
  blastfoam_available: boolean;
  yade_available: boolean;
  installation_guides: Record<string, string>;
}

export interface SimulationConfigTest {
  simulation_type: keyof SimulationType;
  blastfoam_config?: BlastFoamConfig;
  yade_config?: YadeConfig;
}

export interface SimulationConfigTestResult {
  simulation_type: keyof SimulationType;
  available: boolean;
  version_info?: string;
  test_passed: boolean;
  test_duration_seconds?: number;
  errors: string[];
  warnings: string[];
}

export interface SimulationJobUpdate {
  priority?: number;
  status?: keyof SimulationStatus;
}

class SimulationService {
  /**
   * Get available simulation capabilities
   */
  async getCapabilities(): Promise<SimulationCapabilities> {
    const response = await api.get('/simulations/capabilities');
    return response.data;
  }

  /**
   * Test simulation configuration
   */
  async testConfig(config: SimulationConfigTest): Promise<SimulationConfigTestResult> {
    const response = await api.post('/simulations/test-config', config);
    return response.data;
  }

  /**
   * Create a new simulation job
   */
  async createJob(jobRequest: SimulationJobCreate): Promise<SimulationJob> {
    const response = await api.post('/simulations/jobs', jobRequest);
    return response.data;
  }

  /**
   * List simulation jobs with pagination and filtering
   */
  async listJobs(params: {
    page?: number;
    page_size?: number;
    status?: keyof SimulationStatus;
    simulation_type?: keyof SimulationType;
  } = {}): Promise<SimulationJobList> {
    const response = await api.get('/simulations/jobs', { params });
    return response.data;
  }

  /**
   * Get simulation job details
   */
  async getJob(jobId: string): Promise<SimulationJob> {
    const response = await api.get(`/simulations/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Update simulation job
   */
  async updateJob(jobId: string, update: SimulationJobUpdate): Promise<SimulationJob> {
    const response = await api.patch(`/simulations/jobs/${jobId}`, update);
    return response.data;
  }

  /**
   * Delete simulation job
   */
  async deleteJob(jobId: string): Promise<{ message: string }> {
    const response = await api.delete(`/simulations/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Cancel simulation job
   */
  async cancelJob(jobId: string): Promise<SimulationJob> {
    return this.updateJob(jobId, { status: 'cancelled' });
  }

  /**
   * Compare simulation results
   */
  async compareResults(jobIds: string[]): Promise<SimulationComparison> {
    const response = await api.post('/simulations/compare', jobIds);
    return response.data;
  }

  /**
   * Clean up old completed jobs
   */
  async cleanupJobs(maxAgeHours: number = 24): Promise<{ cleaned_jobs: number }> {
    const response = await api.post('/simulations/cleanup', null, {
      params: { max_age_hours: maxAgeHours }
    });
    return response.data;
  }

  /**
   * Get installation guides
   */
  async getInstallationGuides(): Promise<Record<string, string>> {
    const response = await api.get('/simulations/installation-guides');
    return response.data;
  }

  /**
   * Create default blastFoam configuration
   */
  createDefaultBlastFoamConfig(): BlastFoamConfig {
    return {
      enabled: true,
      mesh_resolution: 1.0,
      simulation_time: 0.05,
      time_step: 1e-6,
      parallel_processes: 4,
      explosive_density: 1200.0,
      detonation_velocity: 6000.0,
      chapman_jouguet_pressure: 21e9,
      timeout_seconds: 3600
    };
  }

  /**
   * Create default YADE configuration
   */
  createDefaultYadeConfig(): YadeConfig {
    return {
      enabled: true,
      particle_radius_min: 0.01,
      particle_radius_max: 0.1,
      particle_density: 2700.0,
      young_modulus: 70e9,
      poisson_ratio: 0.25,
      friction_angle: 30.0,
      cohesion: 1e6,
      tensile_strength: 5e6,
      max_iterations: 100000,
      convergence_tolerance: 1e-6,
      timeout_seconds: 3600
    };
  }

  /**
   * Create example mesh geometry
   */
  createExampleGeometry(): MeshGeometry {
    return {
      bench_vertices: [
        [0, 0, 0], [50, 0, 0], [50, 30, 0], [0, 30, 0],
        [0, 0, 15], [50, 0, 15], [50, 30, 15], [0, 30, 15]
      ],
      bench_faces: [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
        [2, 3, 7, 6], [0, 3, 7, 4], [1, 2, 6, 5]
      ],
      hole_positions: [
        [10, 10, 0], [25, 10, 0], [40, 10, 0],
        [10, 20, 0], [25, 20, 0], [40, 20, 0]
      ],
      hole_depths: [18, 18, 18, 18, 18, 18],
      hole_diameters: [0.15, 0.15, 0.15, 0.15, 0.15, 0.15],
      charge_positions: [
        [10, 10, -15], [25, 10, -15], [40, 10, -15],
        [10, 20, -15], [25, 20, -15], [40, 20, -15]
      ],
      charge_masses: [30, 30, 30, 30, 30, 30],
      charge_types: ['ANFO', 'ANFO', 'ANFO', 'ANFO', 'ANFO', 'ANFO']
    };
  }

  /**
   * Format simulation type for display
   */
  formatSimulationType(type: keyof SimulationType): string {
    const typeMap = {
      physics_only: 'Physics Only',
      blastfoam: 'blastFoam CFD',
      yade: 'YADE DEM'
    };
    return typeMap[type] || type;
  }

  /**
   * Format simulation status for display
   */
  formatSimulationStatus(status: keyof SimulationStatus): string {
    const statusMap = {
      pending: 'Pending',
      running: 'Running',
      completed: 'Completed',
      failed: 'Failed',
      cancelled: 'Cancelled'
    };
    return statusMap[status] || status;
  }

  /**
   * Get status color for UI
   */
  getStatusColor(status: keyof SimulationStatus): string {
    const colorMap = {
      pending: 'orange',
      running: 'blue',
      completed: 'green',
      failed: 'red',
      cancelled: 'gray'
    };
    return colorMap[status] || 'gray';
  }

  /**
   * Calculate simulation progress percentage
   */
  calculateProgress(job: SimulationJob): number {
    if (job.status === 'completed') return 100;
    if (job.status === 'failed' || job.status === 'cancelled') return 0;
    if (job.status === 'running') {
      // Estimate progress based on runtime if available
      if (job.started_at && job.runtime_seconds) {
        const elapsed = (Date.now() - new Date(job.started_at).getTime()) / 1000;
        return Math.min(90, (elapsed / job.runtime_seconds) * 100);
      }
      return 50; // Default for running jobs
    }
    return 0; // Pending
  }

  /**
   * Validate simulation configuration
   */
  validateBlastFoamConfig(config: BlastFoamConfig): string[] {
    const errors: string[] = [];
    
    if (config.mesh_resolution <= 0 || config.mesh_resolution > 10) {
      errors.push('Mesh resolution must be between 0.1 and 10 meters');
    }
    
    if (config.simulation_time <= 0 || config.simulation_time > 1) {
      errors.push('Simulation time must be between 0.001 and 1 seconds');
    }
    
    if (config.parallel_processes < 1 || config.parallel_processes > 16) {
      errors.push('Parallel processes must be between 1 and 16');
    }
    
    return errors;
  }

  /**
   * Validate YADE configuration
   */
  validateYadeConfig(config: YadeConfig): string[] {
    const errors: string[] = [];
    
    if (config.particle_radius_min >= config.particle_radius_max) {
      errors.push('Minimum particle radius must be less than maximum');
    }
    
    if (config.poisson_ratio <= 0 || config.poisson_ratio >= 0.5) {
      errors.push('Poisson ratio must be between 0 and 0.5');
    }
    
    if (config.friction_angle < 0 || config.friction_angle > 90) {
      errors.push('Friction angle must be between 0 and 90 degrees');
    }
    
    return errors;
  }
}

export const simulationService = new SimulationService();