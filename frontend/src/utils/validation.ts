import { ValidationError, FormValidationState } from '../types';

export class FormValidator {
  private errors: ValidationError[] = [];
  private warnings: ValidationError[] = [];

  // Clear all errors and warnings
  clear(): void {
    this.errors = [];
    this.warnings = [];
  }

  // Add validation error
  addError(field: string, message: string): void {
    this.errors.push({ field, message });
  }

  // Add validation warning
  addWarning(field: string, message: string): void {
    this.warnings.push({ field, message });
  }

  // Get validation state
  getState(): FormValidationState {
    return {
      isValid: this.errors.length === 0,
      errors: [...this.errors],
      warnings: [...this.warnings]
    };
  }

  // Validate required field
  validateRequired(value: any, field: string, displayName: string): boolean {
    if (value === null || value === undefined || value === '') {
      this.addError(field, `${displayName} is required`);
      return false;
    }
    return true;
  }

  // Validate numeric range
  validateRange(value: number, field: string, displayName: string, min?: number, max?: number): boolean {
    if (isNaN(value)) {
      this.addError(field, `${displayName} must be a valid number`);
      return false;
    }
    
    if (min !== undefined && value < min) {
      this.addError(field, `${displayName} must be at least ${min}`);
      return false;
    }
    
    if (max !== undefined && value > max) {
      this.addError(field, `${displayName} must be at most ${max}`);
      return false;
    }
    
    return true;
  }

  // Validate positive number
  validatePositive(value: number, field: string, displayName: string): boolean {
    if (!this.validateRange(value, field, displayName, 0.001)) {
      return false;
    }
    return true;
  }

  // Validate coordinates
  validateCoordinates(coordinates: { x: number; y: number; z: number }, field: string): boolean {
    let isValid = true;
    
    if (isNaN(coordinates.x)) {
      this.addError(`${field}.x`, 'X coordinate must be a valid number');
      isValid = false;
    }
    
    if (isNaN(coordinates.y)) {
      this.addError(`${field}.y`, 'Y coordinate must be a valid number');
      isValid = false;
    }
    
    if (isNaN(coordinates.z)) {
      this.addError(`${field}.z`, 'Z coordinate must be a valid number');
      isValid = false;
    }
    
    return isValid;
  }

  // Validate bench geometry
  validateBenchGeometry(geometry: any): boolean {
    let isValid = true;
    
    if (!this.validateRequired(geometry.bench_top_elevation, 'bench_top_elevation', 'Bench Top Elevation')) {
      isValid = false;
    }
    
    if (!this.validateRequired(geometry.bench_bottom_elevation, 'bench_bottom_elevation', 'Bench Bottom Elevation')) {
      isValid = false;
    }
    
    if (geometry.bench_top_elevation <= geometry.bench_bottom_elevation) {
      this.addError('bench_top_elevation', 'Bench top elevation must be higher than bottom elevation');
      isValid = false;
    }
    
    if (!this.validateRange(geometry.free_face_orientation, 'free_face_orientation', 'Free Face Orientation', 0, 360)) {
      isValid = false;
    }
    
    if (!this.validatePositive(geometry.bench_width, 'bench_width', 'Bench Width')) {
      isValid = false;
    }
    
    if (!this.validatePositive(geometry.bench_length, 'bench_length', 'Bench Length')) {
      isValid = false;
    }
    
    return isValid;
  }

  // Validate rock properties
  validateRockProperties(properties: any): boolean {
    let isValid = true;
    
    if (!this.validateRequired(properties.rock_type, 'rock_type', 'Rock Type')) {
      isValid = false;
    }
    
    if (!this.validateRange(properties.ucs, 'ucs', 'UCS', 1, 500)) {
      isValid = false;
    }
    
    if (!this.validateRange(properties.density, 'density', 'Density', 1000, 5000)) {
      isValid = false;
    }
    
    if (!this.validateRange(properties.rock_factor_a, 'rock_factor_a', 'Rock Factor A', 1, 20)) {
      isValid = false;
    }
    
    if (properties.grade !== undefined && properties.grade !== null && properties.grade !== '') {
      if (!this.validateRange(properties.grade, 'grade', 'Grade', 0, 100)) {
        isValid = false;
      }
    }
    
    return isValid;
  }

  // Validate drill rig specifications
  validateDrillRigSpec(spec: any): boolean {
    let isValid = true;
    
    if (!this.validateRange(spec.max_hole_diameter, 'max_hole_diameter', 'Max Hole Diameter', 50, 500)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.max_depth, 'max_depth', 'Max Depth', 1, 50)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.collar_accuracy, 'collar_accuracy', 'Collar Accuracy', 0.01, 1)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.drilling_rate, 'drilling_rate', 'Drilling Rate', 1, 100)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.setup_time, 'setup_time', 'Setup Time', 1, 120)) {
      isValid = false;
    }
    
    return isValid;
  }

  // Validate explosive specification
  validateExplosiveSpec(spec: any): boolean {
    let isValid = true;
    
    if (!this.validateRequired(spec.name, 'name', 'Name')) {
      isValid = false;
    }
    
    if (!this.validateRequired(spec.type, 'type', 'Type')) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.density, 'density', 'Density', 500, 2000)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.rws, 'rws', 'RWS', 50, 150)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.vod, 'vod', 'VOD', 2000, 8000)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.energy, 'energy', 'Energy', 1, 10)) {
      isValid = false;
    }
    
    if (!this.validatePositive(spec.cost_per_kg, 'cost_per_kg', 'Cost per kg')) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.regulatory_limit_per_hole, 'regulatory_limit_per_hole', 'Regulatory Limit per Hole', 1, 1000)) {
      isValid = false;
    }
    
    if (!this.validateRange(spec.regulatory_limit_per_delay, 'regulatory_limit_per_delay', 'Regulatory Limit per Delay', 1, 5000)) {
      isValid = false;
    }
    
    return isValid;
  }

  // Validate optimization constraints
  validateOptimizationConstraints(constraints: any): boolean {
    let isValid = true;
    
    if (!this.validateRange(constraints.min_burden, 'min_burden', 'Min Burden', 1, 20)) {
      isValid = false;
    }
    
    if (!this.validateRange(constraints.max_burden, 'max_burden', 'Max Burden', 1, 20)) {
      isValid = false;
    }
    
    if (constraints.min_burden >= constraints.max_burden) {
      this.addError('max_burden', 'Max burden must be greater than min burden');
      isValid = false;
    }
    
    if (!this.validateRange(constraints.min_spacing, 'min_spacing', 'Min Spacing', 1, 20)) {
      isValid = false;
    }
    
    if (!this.validateRange(constraints.max_spacing, 'max_spacing', 'Max Spacing', 1, 20)) {
      isValid = false;
    }
    
    if (constraints.min_spacing >= constraints.max_spacing) {
      this.addError('max_spacing', 'Max spacing must be greater than min spacing');
      isValid = false;
    }
    
    if (!this.validateRange(constraints.powder_factor_min, 'powder_factor_min', 'Min Powder Factor', 0.05, 2)) {
      isValid = false;
    }
    
    if (!this.validateRange(constraints.powder_factor_max, 'powder_factor_max', 'Max Powder Factor', 0.05, 2)) {
      isValid = false;
    }
    
    if (constraints.powder_factor_min >= constraints.powder_factor_max) {
      this.addError('powder_factor_max', 'Max powder factor must be greater than min powder factor');
      isValid = false;
    }
    
    return isValid;
  }

  // Validate optimization objectives
  validateOptimizationObjectives(objectives: any): boolean {
    let isValid = true;
    
    if (!this.validateRange(objectives.target_p80, 'target_p80', 'Target P80', 10, 1000)) {
      isValid = false;
    }
    
    if (!this.validateRange(objectives.weight_fragmentation, 'weight_fragmentation', 'Fragmentation Weight', 0, 10)) {
      isValid = false;
    }
    
    if (!this.validateRange(objectives.weight_cost, 'weight_cost', 'Cost Weight', 0, 10)) {
      isValid = false;
    }
    
    if (!this.validateRange(objectives.weight_ppv, 'weight_ppv', 'PPV Weight', 0, 10)) {
      isValid = false;
    }
    
    return isValid;
  }
}

// Utility function to create a new validator
export const createValidator = (): FormValidator => new FormValidator();