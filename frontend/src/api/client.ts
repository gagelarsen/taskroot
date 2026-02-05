import axios from 'axios';
import type { ContractFilters, DeliverableFilters, TimeEntryFilters } from '../types/api';

// API base URL - defaults to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Create axios instance
export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear tokens and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/token/', { username, password });
    return response.data;
  },
  
  refresh: async (refreshToken: string) => {
    const response = await apiClient.post('/auth/token/refresh/', { refresh: refreshToken });
    return response.data;
  },
};

// Contracts API
export const contractsApi = {
  list: async (params?: ContractFilters) => {
    const response = await apiClient.get('/contracts/', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/contracts/${id}/`);
    return response.data;
  },
};

// Deliverables API
export const deliverablesApi = {
  list: async (params?: DeliverableFilters) => {
    const response = await apiClient.get('/deliverables/', { params });
    return response.data;
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/deliverables/${id}/`);
    return response.data;
  },
};

// Staff API
interface StaffFilters {
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export const staffApi = {
  list: async (params?: StaffFilters) => {
    const response = await apiClient.get('/staff/', { params });
    return response.data;
  },
};

// Time Entries API
export const timeEntriesApi = {
  list: async (params?: TimeEntryFilters) => {
    const response = await apiClient.get('/deliverable-time-entries/', { params });
    return response.data;
  },
};

// Status Updates API
interface StatusUpdateFilters {
  deliverable_id?: number;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export const statusUpdatesApi = {
  list: async (params?: StatusUpdateFilters) => {
    const response = await apiClient.get('/deliverable-status-updates/', { params });
    return response.data;
  },
};

