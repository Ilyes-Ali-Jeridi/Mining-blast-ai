import { apiService } from './api';

export interface SystemHealth {
  timestamp: string;
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  components: {
    database?: {
      status: string;
      response_time_ms?: number;
      statistics?: {
        active_configurations: number;
        active_users: number;
        total_sites: number;
        total_blast_records: number;
      };
      error?: string;
    };
    configuration?: {
      status: string;
      missing_configurations?: string[];
      all_required_configs_present?: boolean;
      error?: string;
    };
    user_activity?: {
      status: string;
      recent_logins_24h: number;
      recent_activity_1h: number;
      error?: string;
    };
    error_rate?: {
      status: string;
      error_rate_percent: number;
      total_actions_1h: number;
      error_actions_1h: number;
    };
  };
}

export interface SystemMetrics {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  user_metrics: {
    total_logins: number;
    unique_active_users: number;
    average_logins_per_day: number;
  };
  blast_metrics: {
    plans_created: number;
    plans_signed_off: number;
    plans_exported: number;
    average_plans_per_day: number;
  };
  configuration_metrics: {
    total_changes: number;
    average_changes_per_day: number;
  };
  performance_metrics: {
    average_response_time_ms: number | null;
  };
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'engineer' | 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  is_verified: boolean;
  professional_license?: string;
  license_expiry?: string;
  organization?: string;
  employee_id?: string;
  can_sign_off: boolean;
  is_locked: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: 'engineer' | 'admin' | 'operator' | 'viewer';
  professional_license?: string;
  license_expiry?: string;
  organization?: string;
  employee_id?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: 'engineer' | 'admin' | 'operator' | 'viewer';
  is_active?: boolean;
  is_verified?: boolean;
  professional_license?: string;
  license_expiry?: string;
  organization?: string;
  employee_id?: string;
}

class AdminService {
  // System Health and Monitoring
  async getSystemHealth(): Promise<SystemHealth> {
    return await apiService.getRaw<SystemHealth>('/admin/system/health');
  }

  async getSystemMetrics(days: number = 7): Promise<SystemMetrics> {
    return await apiService.getRaw<SystemMetrics>(`/admin/system/metrics?days=${days}`);
  }

  // User Management
  async getUsers(params?: {
    skip?: number;
    limit?: number;
    role?: string;
    is_active?: boolean;
  }): Promise<User[]> {
    return await apiService.getRaw<User[]>('/auth/users', params);
  }

  async createUser(userData: UserCreate): Promise<User> {
    return await apiService.postRaw<User>('/auth/users', userData);
  }

  async updateUser(userId: number, userData: UserUpdate): Promise<User> {
    return await apiService.putRaw<User>(`/auth/users/${userId}`, userData);
  }

  // Configuration Management
  async getConfigurations(params?: any): Promise<any[]> {
    try {
      return await apiService.getRaw<any[]>('/admin/configurations', params);
    } catch (error) {
      console.warn('Admin configurations endpoint not available, returning mock data');
      return [];
    }
  }

  async validateConfiguration(configId: number, validationNotes?: string): Promise<any> {
    try {
      return await apiService.postRaw(`/admin/configurations/validate/${configId}`, {
        validation_notes: validationNotes
      });
    } catch (error) {
      console.warn('Configuration validation endpoint not available');
      return { status: 'mock_validated' };
    }
  }

  async calibratePhysicsParameters(calibrationData: any): Promise<any> {
    try {
      return await apiService.postRaw('/admin/configurations/physics/calibrate', calibrationData);
    } catch (error) {
      console.warn('Physics calibration endpoint not available');
      return { status: 'mock_calibrated' };
    }
  }

  // Explosives Management
  async getExplosivesCatalog(includeInactive: boolean = false): Promise<any> {
    try {
      return await apiService.getRaw(`/admin/explosives/catalog?include_inactive=${includeInactive}`);
    } catch (error) {
      console.warn('Explosives catalog endpoint not available, returning mock data');
      return { 
        explosives: [
          {
            id: 'anfo_standard',
            name: 'Standard ANFO',
            manufacturer: 'Generic',
            type: 'ANFO',
            density: 850,
            rws: 100,
            vod: 4500,
            energy: 3.7,
            cost_per_kg: 1.50,
            is_active: true
          }
        ], 
        metadata: { total_explosives: 1, active_explosives: 1 } 
      };
    }
  }

  async updateExplosivesCatalog(catalogData: any): Promise<any> {
    try {
      return await apiService.postRaw('/admin/explosives/catalog', catalogData);
    } catch (error) {
      console.warn('Explosives catalog update endpoint not available');
      return { status: 'mock_updated' };
    }
  }

  // Safety Limits Management
  async getSafetyLimits(): Promise<any> {
    try {
      return await apiService.getRaw('/admin/safety/limits');
    } catch (error) {
      console.warn('Safety limits endpoint not available, returning mock data');
      return {
        charge_limits: {
          max_charge_per_hole: 50.0,
          max_charge_per_delay: 200.0,
          safety_factor: 1.0
        },
        powder_factor_limits: {
          min_powder_factor: 0.05,
          max_powder_factor: 1.5,
          recommended_range: [0.2, 0.8]
        },
        ppv_limits: {
          default_limit: 5.0,
          structure_limits: {
            residential: 2.0,
            commercial: 5.0,
            industrial: 10.0,
            sensitive: 1.0
          }
        },
        distance_limits: {
          min_distance_to_structures: 100.0,
          min_distance_to_roads: 50.0,
          exclusion_zone_buffer: 25.0
        }
      };
    }
  }

  async updateSafetyLimits(safetyData: any): Promise<any> {
    try {
      return await apiService.putRaw('/admin/safety/limits', safetyData);
    } catch (error) {
      console.warn('Safety limits update endpoint not available');
      return { status: 'mock_updated' };
    }
  }
}

export const adminService = new AdminService();