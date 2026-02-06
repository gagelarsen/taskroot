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
    // Handle paginated response - DRF returns { results: [...], count, next, previous }
    return response.data.results || response.data;
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/contracts/${id}/`);
    return response.data;
  },

  create: async (data: unknown) => {
    const response = await apiClient.post('/contracts/', data);
    return response.data;
  },

  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/contracts/${id}/`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await apiClient.delete(`/contracts/${id}/`);
  },
};

// Deliverables API
export const deliverablesApi = {
  list: async (params?: DeliverableFilters) => {
    const response = await apiClient.get('/deliverables/', { params });
    // Handle paginated response
    return response.data.results || response.data;
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/deliverables/${id}/`);
    return response.data;
  },

  create: async (data: unknown) => {
    const response = await apiClient.post('/deliverables/', data);
    return response.data;
  },

  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/deliverables/${id}/`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await apiClient.delete(`/deliverables/${id}/`);
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
    // Handle paginated response
    return response.data.results || response.data;
  },
  get: async (id: number): Promise<Staff> => {
    const response = await apiClient.get(`/staff/${id}/`);
    return response.data;
  },
  create: async (data: Partial<Staff>): Promise<Staff> => {
    const response = await apiClient.post('/staff/', data);
    return response.data;
  },
  update: async (id: number, data: Partial<Staff>): Promise<Staff> => {
    const response = await apiClient.put(`/staff/${id}/`, data);
    return response.data;
  },
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/staff/${id}/`);
  },
};

// Time Entries API
export const timeEntriesApi = {
  list: async (params?: TimeEntryFilters) => {
    const response = await apiClient.get('/deliverable-time-entries/', { params });
    // Handle paginated response
    return response.data.results || response.data;
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
    // Handle paginated response
    return response.data.results || response.data;
  },
};

// Tasks API
interface TaskFilters {
  deliverable_id?: number;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export const tasksApi = {
  list: async (params?: TaskFilters) => {
    const response = await apiClient.get('/tasks/', { params });
    // Handle paginated response
    return response.data.results || response.data;
  },
  get: async (id: number) => {
    const response = await apiClient.get(`/tasks/${id}/`);
    return response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/tasks/', data);
    return response.data;
  },
  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/tasks/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/tasks/${id}/`);
  },
};

// Deliverable Assignments API
interface AssignmentFilters {
  deliverable_id?: number;
  staff_id?: number;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export const assignmentsApi = {
  list: async (params?: AssignmentFilters) => {
    const response = await apiClient.get('/deliverable-assignments/', { params });
    // Handle paginated response
    return response.data.results || response.data;
  },
  get: async (id: number) => {
    const response = await apiClient.get(`/deliverable-assignments/${id}/`);
    return response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/deliverable-assignments/', data);
    return response.data;
  },
  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/deliverable-assignments/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/deliverable-assignments/${id}/`);
  },
};
