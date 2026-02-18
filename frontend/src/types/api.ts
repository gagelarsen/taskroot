// Auth types
export interface LoginResponse {
  access: string;
  refresh: string;
}

// Contract types
export interface Contract {
  id: number;
  name: string;
  client_name: string;
  tags: string[];
  contract_type: 'fixed_cost' | 'time_and_materials';
  contract_type_display?: string;
  start_date: string;
  end_date: string;
  budget_hours: string;
  status: 'draft' | 'active' | 'closed';
  created_at: string;
  updated_at: string;

  // Rollup metrics
  assigned_budget_hours: string;
  spent_hours: string;
  planned_weeks: number;
  elapsed_weeks: number;
  assigned_budget_hours_per_week: string;
  spent_hours_per_week: string;
  remaining_budget_hours: string;
  unspent_budget_hours: string;
  estimated_burn_rate: string;
  actual_burn_rate: string;
  estimated_percent_complete: string;

  // Health flags
  is_over_budget: boolean;
  is_overassigned: boolean;
}

// Forward declarations for circular references
export interface DeliverableAssignment {
  id: number;
  deliverable: number;
  staff: number;
  staff_name: string;
  budget_hours: string;
  is_lead: boolean;
  created_at: string;
}

export interface Task {
  id: number;
  deliverable: number;
  assignee: number | null;
  assignee_name: string | null;
  title: string;
  budget_hours: string;
  percent_complete: string;
  status: 'todo' | 'in_progress' | 'done' | 'blocked';
  created_at: string;
  updated_at: string;
}

// Deliverable types
export interface Deliverable {
  id: number;
  contract: number;
  name: string;
  charge_code?: string;
  budget_hours: string;
  target_completion_date?: string | null;
  status: 'planned' | 'in_progress' | 'complete' | 'blocked' | 'not_started' | 'completed' | 'on_hold';
  created_at: string;
  updated_at: string;

  // Rollup metrics
  assigned_budget_hours: string;
  spent_hours: string;
  planned_weeks: number;
  elapsed_weeks: number;
  assigned_budget_hours_per_week: string;
  spent_hours_per_week: string;
  remaining_budget_hours: string;
  unspent_budget_hours: string;
  variance_hours: string;
  estimated_burn_rate: string;
  actual_burn_rate: string;
  estimated_percent_complete: string;

  // Health flags
  is_over_budget: boolean;
  is_overassigned: boolean;
  is_missing_budget: boolean;
  is_missing_lead: boolean;

  // Latest status update
  latest_status_update: DeliverableStatusUpdate | null;

  // Nested related objects
  assignments: DeliverableAssignment[];
  tasks: Task[];
}

// Staff types
export interface Staff {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'manager' | 'staff';
  status: 'active' | 'inactive';
  expected_hours_per_week: string; // DecimalField from Django
  created_at: string;
  updated_at: string;
}

// Time Entry types
export interface TimeEntry {
  id: number;
  deliverable: number;
  entry_date: string;
  hours: string;
  note?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// Status Update types
export interface DeliverableStatusUpdate {
  id: number;
  deliverable: number;
  period_end: string;
  status: 'on_track' | 'at_risk' | 'off_track';
  summary: string;
  created_by: number | null;
  created_at: string;
}

export interface CreateDeliverableStatusUpdatePayload {
  deliverable: number;
  period_end: string;
  status: 'on_track' | 'at_risk' | 'off_track';
  summary: string;
  created_by?: number | null;
}

// Assignment types
export interface DeliverableAssignment {
  id: number;
  deliverable: number;
  staff: number;
  budget_hours: string;
  is_lead: boolean;
  created_at: string;
  updated_at: string;
}

// Filter params types
export interface ContractFilters {
  status?: string;
  contract_type?: 'fixed_cost' | 'time_and_materials';
  tags?: string;
  start_date_from?: string;
  start_date_to?: string;
  end_date_from?: string;
  end_date_to?: string;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  over_budget?: boolean;
  overassigned?: boolean;
}

export interface DeliverableFilters {
  contract_id?: number;
  status?: string;
  target_completion_date_from?: string;
  target_completion_date_to?: string;
  staff_id?: number;
  lead_only?: boolean;
  has_assignments?: boolean;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  over_budget?: boolean;
  overassigned?: boolean;
  missing_lead?: boolean;
  missing_budget?: boolean;
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

export interface InitiativeWeeklyUpdate {
  id: number;
  initiative: number;
  period_end: string;
  percent_complete: string;
  summary: string;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface Initiative {
  id: number;
  name: string;
  tags: string[];
  owner: number | null;
  owner_name: string | null;
  status: 'active' | 'on_hold' | 'completed';
  target_date: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  current_percent_complete: string;
  latest_update: InitiativeWeeklyUpdate | null;
  is_update_stale: boolean;
}

export interface InitiativeFilters {
  status?: 'active' | 'on_hold' | 'completed';
  owner_id?: number;
  tags?: string;
  stale?: boolean;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export interface FutureWork {
  id: number;
  name: string;
  owner: number | null;
  owner_name: string | null;
  tags: string[];
  target_date: string | null;
  notes: string;
  converted_to_type: 'initiative' | 'contract' | null;
  converted_to_id: number | null;
  converted_at: string | null;
  is_converted: boolean;
  created_at: string;
  updated_at: string;
}

export interface FutureWorkFilters {
  owner_id?: number;
  converted?: boolean;
  tags?: string;
  q?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

