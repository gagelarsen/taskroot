import axios from 'axios';
import type {
  ChargeCodeUsageReport,
  ContractFilters,
  ContractInvoiceUpdateFilters,
  ContractTMBurnReport,
  CreateDeliverableStatusUpdatePayload,
  DeliverableFilters,
  FutureWorkFilters,
  InitiativeFilters,
  TimeEntryFilters,
  Staff,
} from '../types/api';

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

export const contractInvoiceUpdatesApi = {
  list: async (params?: ContractInvoiceUpdateFilters) => {
    const response = await apiClient.get('/contract-invoice-updates/', { params });
    return response.data.results || response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/contract-invoice-updates/', data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/contract-invoice-updates/${id}/`);
  },
};

export const reportsApi = {
  getContractTMBurn: async (contractId: number): Promise<ContractTMBurnReport> => {
    const response = await apiClient.get(`/reports/contracts/${contractId}/tm-burn/`);
    return response.data;
  },
  getChargeCodeUsage: async (params: {
    charge_code?: string;
    base_code?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<ChargeCodeUsageReport> => {
    const response = await apiClient.get('/reports/charge-codes/usage/', { params });
    return response.data;
  },
};

export const chargeCodesApi = {
  list: async (params?: {
    code?: string;
    is_active?: boolean;
    deliverable_id?: number;
    start_date_from?: string;
    start_date_to?: string;
    end_date_from?: string;
    end_date_to?: string;
    allotted_hours_from?: number;
    allotted_hours_to?: number;
    page_size?: number;
    q?: string;
    order_by?: string;
    order_dir?: 'asc' | 'desc';
  }) => {
    const firstResponse = await apiClient.get('/charge-codes/', {
      params: {
        ...params,
      },
    });

    if (!firstResponse.data?.results || !firstResponse.data?.next) {
      return firstResponse.data.results || firstResponse.data;
    }

    const allResults = [...firstResponse.data.results];
    let nextUrl: string | null = firstResponse.data.next;

    while (nextUrl) {
      const pageResponse = await apiClient.get(nextUrl);
      allResults.push(...(pageResponse.data?.results || []));
      nextUrl = pageResponse.data?.next || null;
    }

    return allResults;
  },
  update: async (
    id: number,
    data: {
      code?: string;
      description?: string;
      start_date?: string | null;
      end_date?: string | null;
      allotted_hours?: string | null;
      deliverable?: number | null;
      is_active?: boolean;
    }
  ) => {
    const response = await apiClient.patch(`/charge-codes/${id}/`, data);
    return response.data;
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
  create: async (data: unknown) => {
    const response = await apiClient.post('/deliverable-time-entries/', data);
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
    // Handle paginated response
    return response.data.results || response.data;
  },
  create: async (data: CreateDeliverableStatusUpdatePayload) => {
    const response = await apiClient.post('/deliverable-status-updates/', data);
    return response.data;
  },
  update: async (id: number, data: Partial<CreateDeliverableStatusUpdatePayload>) => {
    const response = await apiClient.patch(`/deliverable-status-updates/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/deliverable-status-updates/${id}/`);
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

// Initiatives API
export const initiativesApi = {
  list: async (params?: InitiativeFilters) => {
    const response = await apiClient.get('/initiatives/', { params });
    return response.data.results || response.data;
  },
  get: async (id: number) => {
    const response = await apiClient.get(`/initiatives/${id}/`);
    return response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/initiatives/', data);
    return response.data;
  },
  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/initiatives/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/initiatives/${id}/`);
  },
};

interface InitiativeUpdateFilters {
  initiative_id?: number;
  period_end_from?: string;
  period_end_to?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export const initiativeWeeklyUpdatesApi = {
  list: async (params?: InitiativeUpdateFilters) => {
    const response = await apiClient.get('/initiative-weekly-updates/', { params });
    return response.data.results || response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/initiative-weekly-updates/', data);
    return response.data;
  },
  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/initiative-weekly-updates/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/initiative-weekly-updates/${id}/`);
  },
};

export const futureWorkApi = {
  list: async (params?: FutureWorkFilters) => {
    const response = await apiClient.get('/future-work/', { params });
    return response.data.results || response.data;
  },
  get: async (id: number) => {
    const response = await apiClient.get(`/future-work/${id}/`);
    return response.data;
  },
  create: async (data: unknown) => {
    const response = await apiClient.post('/future-work/', data);
    return response.data;
  },
  update: async (id: number, data: unknown) => {
    const response = await apiClient.patch(`/future-work/${id}/`, data);
    return response.data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/future-work/${id}/`);
  },
  convertToInitiative: async (id: number, data?: unknown) => {
    const response = await apiClient.post(`/future-work/${id}/convert-to-initiative/`, data || {});
    return response.data;
  },
  convertToContract: async (id: number, data: unknown) => {
    const response = await apiClient.post(`/future-work/${id}/convert-to-contract/`, data);
    return response.data;
  },
};
