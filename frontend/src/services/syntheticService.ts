import { api } from './api';

export interface RockType {
  value: string;
  name: string;
  ucs: number;
  density: number;
  rock_factor_a: number;
  description: string;
}

export interface ExplosiveType {
  value: string;
  name: string;
  density: number;
  rws: number;
  vod: number;
  cost_per_kg: number;
  description: string;
}

export interface SyntheticScenario {
  scenario_id: string;
  site: {
    site_id: string;
    name: string;
    rock_type: string;
    bench_height: number;
    bench_width: number;
    bench_length: number;
    ucs: number;
    density: number;
    rock_factor_a: number;
  };
  blast_plan: {
    plan_id: string;
    num_holes: number;
    total_charge: number;
    powder_factor: number;
    holes: Array<{
      hole_id: string;
      x: number;
      y: number;
      z: number;
      depth: number;
      diameter: number;
      charge_kg: number;
      delay_ms: number;
      explosive_type: string;
      burden?: number;
      spacing?: number;
    }>;
  };
  predictions: {
    fragmentation: {
      p10: number;
      p50: number;
      p80: number;
      mean_size: number;
      uniformity_index: number;
    };
    ppv: Record<string, number>;
  };
  measurements: {
    fragmentation: {
      p10?: number;
      p50?: number;
      p80?: number;
      quality?: number;
      is_valid: boolean;
    };
    ppv: Record<string, number>;
  };
  created_at: string;
}

export interface ParameterExplorationScenario {
  scenario_id: string;
  rock_type: string;
  powder_factor: number;
  bench_height: number;
  rock_factor_a: number;
  true_p80: number;
  measured_p80?: number;
  max_ppv: number;
}

export interface BenchmarkDataset {
  dataset_splits: {
    train: number;
    validation: number;
    test: number;
  };
  validation_report: {
    total_scenarios: number;
    valid_scenarios: number;
    missing_measurements: number;
    quality_issues: number;
    data_quality: {
      completeness: number;
      missing_rate: number;
      quality_issue_rate: number;
    };
    statistics?: {
      p80_mm?: {
        min: number;
        max: number;
        mean: number;
        std: number;
      };
      ppv_mm_s?: {
        min: number;
        max: number;
        mean: number;
        std: number;
      };
      powder_factor_kg_t?: {
        min: number;
        max: number;
        mean: number;
        std: number;
      };
    };
  };
  export_path: string;
}

export interface ModelBenchmarkResults {
  benchmark_results: Record<string, {
    mae_mm: number;
    rmse_mm: number;
    mape_percent: number;
    r2_score: number;
    num_predictions: number;
  }>;
  test_scenarios: number;
  models_tested: string[];
}

export interface NoiseAnalysis {
  base_scenario: {
    scenario_id: string;
    true_p80: number;
    rock_type: string;
  };
  noise_analysis: Array<{
    noise_level: number;
    fragmentation: {
      true_p80: number;
      mean_p80: number;
      std_p80: number;
      bias: number;
      measurements: number;
    };
    ppv: {
      measurements: number;
      mean_ppv: number;
      std_ppv: number;
    };
  }>;
}

class SyntheticService {
  /**
   * Generate a single synthetic blast scenario
   */
  async generateScenario(
    rockType?: string,
    noiseLevel: number = 0.15
  ): Promise<SyntheticScenario> {
    const params = new URLSearchParams();
    if (rockType) params.append('rock_type', rockType);
    params.append('noise_level', noiseLevel.toString());

    const response = await api.post(`/synthetic/scenarios/generate?${params}`);
    return response.data.data;
  }

  /**
   * Generate scenarios for parameter space exploration
   */
  async generateParameterExploration(
    numScenarios: number = 50,
    parameterRanges?: Record<string, [number, number]>
  ): Promise<{
    scenarios: ParameterExplorationScenario[];
    statistics: {
      total_scenarios: number;
      parameter_ranges: Record<string, [number, number]> | string;
    };
  }> {
    const params = new URLSearchParams();
    params.append('num_scenarios', numScenarios.toString());

    const body = parameterRanges ? { parameter_ranges: parameterRanges } : {};

    const response = await api.post(`/synthetic/parameter-exploration?${params}`, body);
    return response.data.data;
  }

  /**
   * Generate comprehensive benchmark dataset
   */
  async generateBenchmarkDataset(
    numScenarios: number = 100,
    testSplit: number = 0.2,
    validationSplit: number = 0.1
  ): Promise<BenchmarkDataset> {
    const params = new URLSearchParams();
    params.append('num_scenarios', numScenarios.toString());
    params.append('test_split', testSplit.toString());
    params.append('validation_split', validationSplit.toString());

    const response = await api.post(`/synthetic/benchmark-dataset?${params}`);
    return response.data.data;
  }

  /**
   * Benchmark physics models against synthetic data
   */
  async benchmarkModels(
    numTestScenarios: number = 100,
    modelsToTest: string[] = ['kuz_ram_default', 'kuz_ram_calibrated']
  ): Promise<ModelBenchmarkResults> {
    const params = new URLSearchParams();
    params.append('num_test_scenarios', numTestScenarios.toString());
    modelsToTest.forEach(model => params.append('models_to_test', model));

    const response = await api.post(`/synthetic/benchmark-models?${params}`);
    return response.data.data;
  }

  /**
   * Analyze measurement noise effects
   */
  async analyzeNoise(
    baseScenarioId?: string,
    noiseLevels: number[] = [0.05, 0.10, 0.20, 0.30],
    numSamples: number = 50
  ): Promise<NoiseAnalysis> {
    const params = new URLSearchParams();
    if (baseScenarioId) params.append('base_scenario_id', baseScenarioId);
    noiseLevels.forEach(level => params.append('noise_levels', level.toString()));
    params.append('num_samples', numSamples.toString());

    const response = await api.post(`/synthetic/noise-analysis?${params}`);
    return response.data.data;
  }

  /**
   * Get available rock types
   */
  async getRockTypes(): Promise<RockType[]> {
    const response = await api.get('/synthetic/rock-types');
    return response.data.data.rock_types;
  }

  /**
   * Get available explosive types
   */
  async getExplosiveTypes(): Promise<ExplosiveType[]> {
    const response = await api.get('/synthetic/explosive-types');
    return response.data.data.explosive_types;
  }
}

export const syntheticService = new SyntheticService();