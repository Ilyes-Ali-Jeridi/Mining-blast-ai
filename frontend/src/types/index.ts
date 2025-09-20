// Core data types for the drill-blast system

export interface Coordinates {
  x: number;
  y: number;
  z: number;
}

export interface DrillHole {
  hole_id: string;
  coordinates: Coordinates;
  depth: number;
  diameter: number;
  charge_kg: number;
  stemming_m: number;
  delay_ms: number;
  explosive_type: string;
}

export interface BenchGeometry {
  bench_top_elevation: number;
  bench_bottom_elevation: number;
  free_face_orientation: number;
  bench_width: number;
  bench_length: number;
  topography_mesh?: number[][];
}

export interface RockProperties {
  rock_type: string;
  ucs: number; // Unconfined compressive strength (MPa)
  density: number; // kg/m³
  rock_factor_a: number;
  grade?: number;
}

export interface Site {
  id: number;
  name: string;
  bench_geometry: BenchGeometry;
  rock_properties: RockProperties;
  created_at: string;
}

export interface BlastPlan {
  id?: number;
  site_id: number;
  holes: DrillHole[];
  predicted_fragmentation?: FragmentationCurve;
  predicted_ppv?: Record<string, number>;
  safety_status?: SafetyStatus;
  economic_metrics?: EconomicMetrics;
  created_at?: string;
}

export interface FragmentationCurve {
  p10: number;
  p50: number;
  p80: number;
  mean: number;
  uniformity_index: number;
  distribution_type: 'rosin_rammler' | 'swebrec';
}

export interface SafetyStatus {
  is_valid: boolean;
  violations: string[];
  safety_margin: Record<string, number>;
}

export interface EconomicMetrics {
  total_charge: number;
  total_holes: number;
  powder_factor: number;
  estimated_cost: number;
}

// Equipment and Explosives types
export interface DrillRigSpec {
  name: string;
  max_hole_diameter: number; // mm
  max_depth: number; // m
  collar_accuracy: number; // m
  drilling_rate: number; // m/hr
  setup_time: number; // minutes
  operating_cost: number; // $/hour
}

export interface ExplosiveSpec {
  id?: number;
  name: string;
  type: 'ANFO' | 'Emulsion' | 'Slurry';
  density: number; // kg/m³
  rws: number; // Relative Weight Strength (%)
  vod: number; // Velocity of Detonation (m/s)
  energy: number; // MJ/kg
  cost_per_kg: number;
  regulatory_limit_per_hole: number; // kg
  regulatory_limit_per_delay: number; // kg
}

// Constraint and Objective types
export interface Receptor {
  id: string;
  name: string;
  coordinates: Coordinates;
  ppv_limit: number; // mm/s
}

export interface OptimizationConstraints {
  min_burden: number; // m
  max_burden: number; // m
  min_spacing: number; // m
  max_spacing: number; // m
  powder_factor_min: number; // kg/t
  powder_factor_max: number; // kg/t
  excluded_zones: Polygon[];
  sensitive_receptors: Receptor[];
}

export interface OptimizationObjectives {
  target_p80: number; // mm
  weight_fragmentation: number;
  weight_cost: number;
  weight_ppv: number;
  minimize_oversize: boolean;
}

export interface Polygon {
  id: string;
  name: string;
  coordinates: Coordinates[];
}

// Form validation types
export interface ValidationError {
  field: string;
  message: string;
}

export interface FormValidationState {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface OptimizationProgress {
  iteration: number;
  objective_value: number;
  best_objective: number;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  message?: string;
  algorithm?: string;
  progress_percentage?: number;
  elapsed_time?: number;
  function_evaluations?: number;
}

export interface OptimizationResult {
  blast_plan: BlastPlan;
  objective_value: number;
  solver_info: {
    algorithm: string;
    runtime_seconds: number;
    iterations: number;
  };
}

export interface OptimizationSession {
  optimization_id: string;
  blast_id: number;
  status: 'started' | 'running' | 'completed' | 'failed' | 'cancelled';
  websocket_url?: string;
  started_at: string;
  completed_at?: string;
  progress?: OptimizationProgress;
  results?: OptimizationResult[];
  error_message?: string;
}

export interface OptimizationConfig {
  algorithms: string[];
  max_iterations?: number;
  timeout_seconds?: number;
  convergence_tolerance?: number;
  population_size?: number;
  mutation_rate?: number;
  crossover_rate?: number;
}

export interface OptimizationHistory {
  sessions: OptimizationSession[];
  total_count: number;
}

export interface WebSocketMessage {
  type: string;
  optimization_id?: string;
  timestamp: string;
  [key: string]: any;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
/
/ Simulation types
export interface SimulationJob {
  job_id: string;
  simulation_type: 'physics_only' | 'blastfoam' | 'yade';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  blast_plan_id?: string;
  priority: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  runtime_seconds?: number;
  result?: SimulationResult;
}

export interface SimulationResult {
  simulation_type: 'physics_only' | 'blastfoam' | 'yade';
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

export interface SimulationCapabilities {
  available_types: ('physics_only' | 'blastfoam' | 'yade')[];
  blastfoam_available: boolean;
  yade_available: boolean;
  installation_guides: Record<string, string>;
}