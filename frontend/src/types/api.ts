// Auth types
export interface LoginResponse {
  access: string;
  refresh: string;
}

// Contract types
export interface Contract {
  id: number;
  start_date: string;
  end_date: string;
  budget_hours_total: string;
  status: 'active' | 'completed' | 'on_hold';
  created_at: string;
  updated_at: string;
  
  // Rollup metrics
  expected_hours_total: string;
  actual_hours_total: string;
  planned_weeks: number;
  elapsed_weeks: number;
  expected_hours_per_week: string;
  actual_hours_per_week: string;
  remaining_budget_hours: string;
  
  // Health flags
  is_over_budget: boolean;
  is_over_expected: boolean;
}

// Deliverable types
export interface Deliverable {
  id: number;
  contract: number;
  name: string;
  start_date: string | null;
  due_date: string | null;
  status: 'not_started' | 'in_progress' | 'completed' | 'on_hold' | 'blocked';
  created_at: string;
  updated_at: string;
  
  // Rollup metrics
  expected_hours_total: string;
  actual_hours_total: string;
  planned_weeks: number;
  elapsed_weeks: number;
  expected_hours_per_week: string;
  actual_hours_per_week: string;
  variance_hours: string;
  
  // Health flags
  is_over_expected: boolean;
  is_missing_estimate: boolean;
  is_missing_lead: boolean;
  
  // Latest status update
  latest_status_update: DeliverableStatusUpdate | null;
}

// Staff types
export interface Staff {
  id: number;
  user: number;
  role: 'admin' | 'manager' | 'staff';
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
}

// Time Entry types
export interface TimeEntry {
  id: number;
  deliverable: number;
  staff: number;
  entry_date: string;
  hours: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

// Status Update types
export interface DeliverableStatusUpdate {
  id: number;
  deliverable: number;
  period_end: string;
  status: 'on_track' | 'at_risk' | 'blocked' | 'completed';
  summary: string;
  created_by: number;
  created_at: string;
}

// Assignment types
export interface DeliverableAssignment {
  id: number;
  deliverable: number;
  staff: number;
  expected_hours: string;
  is_lead: boolean;
  created_at: string;
  updated_at: string;
}

// Filter params types
export interface ContractFilters {
  status?: string;
  start_date_from?: string;
  start_date_to?: string;
  end_date_from?: string;
  end_date_to?: string;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  over_budget?: boolean;
  over_expected?: boolean;
}

export interface DeliverableFilters {
  contract_id?: number;
  status?: string;
  start_date_from?: string;
  start_date_to?: string;
  due_date_from?: string;
  due_date_to?: string;
  staff_id?: number;
  lead_only?: boolean;
  has_assignments?: boolean;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  over_expected?: boolean;
  missing_lead?: boolean;
  missing_estimate?: boolean;
}

export interface TimeEntryFilters {
  contract_id?: number;
  deliverable_id?: number;
  staff_id?: number;
  entry_date_from?: string;
  entry_date_to?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

