import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { ApiResponse, PaginatedResponse } from '../types';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth tokens
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic API methods
  async get<T>(url: string, params?: any): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T | ApiResponse<T>> = await this.api.get(url, { params });
    
    // Check if response is already wrapped in ApiResponse format
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data as ApiResponse<T>;
    }
    
    // If not wrapped, create the wrapper
    return {
      success: true,
      data: response.data as T,
      message: 'Success'
    };
  }

  async post<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T | ApiResponse<T>> = await this.api.post(url, data);
    
    // Check if response is already wrapped in ApiResponse format
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data as ApiResponse<T>;
    }
    
    // If not wrapped, create the wrapper
    return {
      success: true,
      data: response.data as T,
      message: 'Success'
    };
  }

  async put<T>(url: string, data?: any): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T | ApiResponse<T>> = await this.api.put(url, data);
    
    // Check if response is already wrapped in ApiResponse format
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data as ApiResponse<T>;
    }
    
    // If not wrapped, create the wrapper
    return {
      success: true,
      data: response.data as T,
      message: 'Success'
    };
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    const response: AxiosResponse<T | ApiResponse<T>> = await this.api.delete(url);
    
    // Check if response is already wrapped in ApiResponse format
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      return response.data as ApiResponse<T>;
    }
    
    // If not wrapped, create the wrapper
    return {
      success: true,
      data: response.data as T,
      message: 'Success'
    };
  }

  async getPaginated<T>(url: string, params?: any): Promise<PaginatedResponse<T>> {
    const response: AxiosResponse<PaginatedResponse<T>> = await this.api.get(url, { params });
    return response.data;
  }

  // Raw API methods (return data directly without ApiResponse wrapper)
  async getRaw<T>(url: string, params?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.api.get(url, { params });
    return response.data;
  }

  async postRaw<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.api.post(url, data);
    return response.data;
  }

  async putRaw<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.api.put(url, data);
    return response.data;
  }

  async deleteRaw<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.api.delete(url);
    return response.data;
  }

  // WebSocket connection for real-time updates
  createWebSocket(endpoint: string): WebSocket {
    const wsUrl = (import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000') + endpoint;
    return new WebSocket(wsUrl);
  }
}

export const apiService = new ApiService();
export const api = apiService; // For backward compatibility
export default apiService;