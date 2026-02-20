import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from '@mui/material';
import { KeyboardArrowDown, KeyboardArrowUp } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { assignmentsApi, contractsApi, deliverablesApi, initiativeWeeklyUpdatesApi, initiativesApi, staffApi, statusUpdatesApi, tasksApi } from '../api/client';
import type { Contract, Deliverable, DeliverableStatusUpdate, Initiative, Staff, Task } from '../types/api';
import { CONTRACT_TYPE_OPTIONS, getContractTypeShortLabel } from '../utils/contractTypes';
import { formatContractStatusLabel } from '../utils/contractStatus';
import { formatDeliverableStatusLabel, getDeliverableStatusChipColor } from '../utils/statusUpdates';
import { getApiErrorMessage } from '../utils/apiErrors';

type FlagFilter = 'all' | 'any' | 'over_budget' | 'overassigned' | 'over_expected';
type SortDirection = 'asc' | 'desc';
type SortKey =
  | 'name'
  | 'budget_hours'
  | 'spent_hours'
  | 'assigned_per_week'
  | 'burn_4wk'
  | 'variance_per_week'
  | 'projected_lateness_days';

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function toNumber(value: string): number {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toDateOnly(dateInput: Date): Date {
  const date = new Date(dateInput);
  date.setHours(0, 0, 0, 0);
  return date;
}

function formatDate(dateInput: Date): string {
  return dateInput.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function getProjectedFinishDate(contract: Contract): Date | null {
  const assignedPerWeek = toNumber(contract.assigned_budget_hours_per_week);
  if (assignedPerWeek <= 0) {
    return null;
  }

  const remainingHours = Math.max(0, toNumber(contract.remaining_budget_hours));
  const today = toDateOnly(new Date());
  if (remainingHours === 0) {
    return today;
  }

  const daysNeeded = Math.ceil((remainingHours / assignedPerWeek) * 7);
  const projected = new Date(today);
  projected.setDate(projected.getDate() + daysNeeded);
  return projected;
}

function getFinishVariance(projectedFinish: Date | null, contractEndDate: string): number | null {
  if (!projectedFinish) {
    return null;
  }

  const endDate = toDateOnly(new Date(contractEndDate));
  const projection = toDateOnly(projectedFinish);
  return Math.round((projection.getTime() - endDate.getTime()) / MS_PER_DAY);
}

function getProjectionPill(varianceDays: number | null) {
  if (varianceDays === null) {
    return { label: 'No rate', color: 'default' as const };
  }

  if (varianceDays === 0) {
    return { label: 'On time', color: 'success' as const };
  }

  if (varianceDays > 0) {
    return { label: `+${varianceDays}d`, color: 'error' as const };
  }

  return { label: `${varianceDays}d`, color: 'success' as const };
}

function hasOverExpectedFlag(contract: Contract): boolean {
  return toNumber(contract.actual_burn_rate) > toNumber(contract.assigned_budget_hours_per_week);
}

function isOverHours(contract: Contract): boolean {
  return toNumber(contract.remaining_budget_hours) < 0;
}

function getDaysSince(dateValue: string): number {
  const today = toDateOnly(new Date());
  const updateDate = toDateOnly(new Date(dateValue));
  return Math.floor((today.getTime() - updateDate.getTime()) / MS_PER_DAY);
}

function isStatusUpdateStale(deliverable: Deliverable): boolean {
  if (!deliverable.latest_status_update) {
    return true;
  }

  return getDaysSince(deliverable.latest_status_update.period_end) > 7;
}

function getAssignedStaffNames(deliverable: Deliverable): string[] {
  return (deliverable.assignments || []).map((assignment) => assignment.staff_name || `Staff #${assignment.staff}`);
}

export function DashboardPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [deliverablesByContract, setDeliverablesByContract] = useState<Record<number, Deliverable[]>>({});
  const [loadingDeliverablesByContract, setLoadingDeliverablesByContract] = useState<Record<number, boolean>>({});
  const [expandedContractIds, setExpandedContractIds] = useState<number[]>([]);
  const [showStaleOnlyByContract, setShowStaleOnlyByContract] = useState<Record<number, boolean>>({});
  const [showCompleteByContract, setShowCompleteByContract] = useState<Record<number, boolean>>({});
  const [quickAddDialogDeliverable, setQuickAddDialogDeliverable] = useState<Deliverable | null>(null);
  const [quickAddDialogContractId, setQuickAddDialogContractId] = useState<number | null>(null);
  const [quickAddTasks, setQuickAddTasks] = useState<Task[]>([]);
  const [loadingQuickAddTasks, setLoadingQuickAddTasks] = useState(false);
  const [taskPercentById, setTaskPercentById] = useState<Record<number, string>>({});
  const [quickAddStatusUpdate, setQuickAddStatusUpdate] = useState<{
    period_end: string;
    status: DeliverableStatusUpdate['status'];
    summary: string;
  }>({
    period_end: new Date().toISOString().split('T')[0],
    status: 'on_track',
    summary: '',
  });
  const [savingQuickAddDeliverableId, setSavingQuickAddDeliverableId] = useState<number | null>(null);
  const [quickAddError, setQuickAddError] = useState('');
  const [unassignedMenuDeliverableId, setUnassignedMenuDeliverableId] = useState<number | null>(null);
  const [unassignedMenuPosition, setUnassignedMenuPosition] = useState<{ mouseX: number; mouseY: number } | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [assigningDeliverableId, setAssigningDeliverableId] = useState<number | null>(null);
  const [assigningStaffId, setAssigningStaffId] = useState('');
  const [assigningBudgetHours, setAssigningBudgetHours] = useState('0');
  const [assigningIsLead, setAssigningIsLead] = useState(false);
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [assignDialogError, setAssignDialogError] = useState('');
  const [loading, setLoading] = useState(true);
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [staffMembers, setStaffMembers] = useState<Staff[]>([]);
  const [loadingInitiatives, setLoadingInitiatives] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [contractType, setContractType] = useState<'all' | Contract['contract_type']>('all');
  const [tagFilter, setTagFilter] = useState('all');
  const [staffFilterId, setStaffFilterId] = useState<'all' | number>('all');
  const [selectedStaffContractIds, setSelectedStaffContractIds] = useState<number[]>([]);
  const [selectedStaffDeliverableIds, setSelectedStaffDeliverableIds] = useState<number[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [flag, setFlag] = useState<FlagFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('projected_lateness_days');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [initiativeQuickUpdateDialogInitiative, setInitiativeQuickUpdateDialogInitiative] = useState<Initiative | null>(null);
  const [initiativeQuickUpdate, setInitiativeQuickUpdate] = useState({
    period_end: new Date().toISOString().split('T')[0],
    percent_complete: '0',
    summary: '',
  });
  const [initiativeContextMenu, setInitiativeContextMenu] = useState<{
    mouseX: number;
    mouseY: number;
    initiative: Initiative;
  } | null>(null);
  const [initiativeEditDialogOpen, setInitiativeEditDialogOpen] = useState(false);
  const [editingInitiativeId, setEditingInitiativeId] = useState<number | null>(null);
  const [savingInitiativeEdit, setSavingInitiativeEdit] = useState(false);
  const [initiativeEditError, setInitiativeEditError] = useState('');
  const [initiativeFormData, setInitiativeFormData] = useState({
    name: '',
    owner: '',
    status: 'active' as Initiative['status'],
    tags: '',
    target_date: '',
    notes: '',
  });
  const [savingInitiativeQuickUpdate, setSavingInitiativeQuickUpdate] = useState(false);
  const [initiativeQuickUpdateError, setInitiativeQuickUpdateError] = useState('');
  const [savingInitiativeStatusId, setSavingInitiativeStatusId] = useState<number | null>(null);
  const navigate = useNavigate();

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await contractsApi.list({ order_by: 'start_date', order_dir: 'desc' });
      setContracts(data);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load dashboard contracts');
      } else {
        setError('Failed to load dashboard contracts');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  const loadInitiatives = useCallback(async () => {
    setLoadingInitiatives(true);
    try {
      const data = await initiativesApi.list({ order_by: 'id', order_dir: 'desc' });
      setInitiatives(data);
    } catch {
      setInitiatives([]);
    } finally {
      setLoadingInitiatives(false);
    }
  }, []);

  useEffect(() => {
    void loadInitiatives();
  }, [loadInitiatives]);

  const loadStaff = useCallback(async () => {
    try {
      const data = await staffApi.list({ order_by: 'id', order_dir: 'asc' });
      setStaffMembers(data);
    } catch {
      setStaffMembers([]);
    }
  }, []);

  useEffect(() => {
    void loadStaff();
  }, [loadStaff]);

  const loadSelectedStaffAssignments = useCallback(async () => {
    if (staffFilterId === 'all') {
      setSelectedStaffContractIds([]);
      setSelectedStaffDeliverableIds([]);
      return;
    }

    try {
      const staffDeliverables: Deliverable[] = await deliverablesApi.list({
        staff_id: staffFilterId,
        order_by: 'id',
        order_dir: 'desc',
      });
      setSelectedStaffContractIds(Array.from(new Set(staffDeliverables.map((deliverable) => deliverable.contract))));
      setSelectedStaffDeliverableIds(staffDeliverables.map((deliverable) => deliverable.id));
    } catch {
      setSelectedStaffContractIds([]);
      setSelectedStaffDeliverableIds([]);
    }
  }, [staffFilterId]);

  useEffect(() => {
    void loadSelectedStaffAssignments();
  }, [loadSelectedStaffAssignments]);

  const loadContractDeliverables = useCallback(async (contractId: number, force = false) => {
    if (!force && deliverablesByContract[contractId]) {
      return;
    }

    setLoadingDeliverablesByContract((current) => ({ ...current, [contractId]: true }));
    try {
      const deliverables = await deliverablesApi.list({ contract_id: contractId, order_by: 'id', order_dir: 'desc' });
      setDeliverablesByContract((current) => ({ ...current, [contractId]: deliverables }));
    } catch {
      setDeliverablesByContract((current) => ({ ...current, [contractId]: [] }));
    } finally {
      setLoadingDeliverablesByContract((current) => ({ ...current, [contractId]: false }));
    }
  }, [deliverablesByContract]);

  const startQuickAddStatusUpdate = async (contractId: number, deliverable: Deliverable) => {
    setQuickAddDialogContractId(contractId);
    setQuickAddDialogDeliverable(deliverable);
    setQuickAddStatusUpdate({
      period_end: new Date().toISOString().split('T')[0],
      status: 'on_track',
      summary: '',
    });
    setQuickAddError('');
    setQuickAddTasks([]);
    setTaskPercentById({});
    setLoadingQuickAddTasks(true);

    try {
      const tasks: Task[] = await tasksApi.list({
        deliverable_id: deliverable.id,
        order_by: 'id',
        order_dir: 'asc',
      });
      setQuickAddTasks(tasks);
      setTaskPercentById(
        tasks.reduce((current: Record<number, string>, task: Task) => {
          current[task.id] = task.percent_complete || '0';
          return current;
        }, {})
      );
    } catch {
      setQuickAddError('Failed to load tasks for this deliverable');
    } finally {
      setLoadingQuickAddTasks(false);
    }
  };

  const cancelQuickAddStatusUpdate = () => {
    setQuickAddDialogContractId(null);
    setQuickAddDialogDeliverable(null);
    setQuickAddTasks([]);
    setTaskPercentById({});
    setQuickAddError('');
  };

  const openUnassignedMenu = (event: React.MouseEvent, deliverableId: number) => {
    event.preventDefault();
    event.stopPropagation();
    setUnassignedMenuDeliverableId(deliverableId);
    setUnassignedMenuPosition({ mouseX: event.clientX + 2, mouseY: event.clientY - 6 });
  };

  const closeUnassignedMenu = () => {
    setUnassignedMenuPosition(null);
  };

  const openEditDeliverableFromMenu = () => {
    if (!unassignedMenuDeliverableId) {
      closeUnassignedMenu();
      return;
    }
    const deliverableId = unassignedMenuDeliverableId;
    closeUnassignedMenu();
    navigate(`/deliverables/${deliverableId}/edit`);
  };

  const openAssignDialogFromMenu = () => {
    if (!unassignedMenuDeliverableId) {
      closeUnassignedMenu();
      return;
    }
    setAssigningDeliverableId(unassignedMenuDeliverableId);
    setAssigningStaffId('');
    setAssigningBudgetHours('0');
    setAssigningIsLead(false);
    setAssignDialogError('');
    setAssignDialogOpen(true);
    closeUnassignedMenu();
  };

  const closeAssignDialog = () => {
    if (savingAssignment) {
      return;
    }
    setAssignDialogOpen(false);
    setAssigningDeliverableId(null);
    setAssignDialogError('');
  };

  const saveAssignment = async () => {
    if (!assigningDeliverableId) {
      return;
    }
    if (!assigningStaffId) {
      setAssignDialogError('Staff member is required');
      return;
    }

    setSavingAssignment(true);
    setAssignDialogError('');
    try {
      await assignmentsApi.create({
        deliverable: assigningDeliverableId,
        staff: Number(assigningStaffId),
        budget_hours: assigningBudgetHours,
        is_lead: assigningIsLead,
      });

      if (quickAddDialogDeliverable?.id === assigningDeliverableId) {
        const selectedStaff = staffMembers.find((staffMember) => staffMember.id === Number(assigningStaffId));
        if (selectedStaff) {
          setQuickAddDialogDeliverable((current) => {
            if (!current || current.id !== assigningDeliverableId) {
              return current;
            }
            return {
              ...current,
              assignments: [
                ...(current.assignments || []),
                {
                  id: -Date.now(),
                  deliverable: assigningDeliverableId,
                  staff: selectedStaff.id,
                  staff_name: `${selectedStaff.first_name} ${selectedStaff.last_name}`,
                  budget_hours: assigningBudgetHours,
                  is_lead: assigningIsLead,
                  created_at: new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                },
              ],
            };
          });
        }
      }

      if (quickAddDialogContractId) {
        await loadContractDeliverables(quickAddDialogContractId, true);
      }
      closeAssignDialog();
    } catch (err) {
      setAssignDialogError(getApiErrorMessage(err, 'Failed to save assignment'));
    } finally {
      setSavingAssignment(false);
    }
  };

  const saveQuickAddStatusUpdate = async (contractId: number, deliverableId: number) => {
    setSavingQuickAddDeliverableId(deliverableId);
    setQuickAddError('');

    try {
      const taskUpdates = quickAddTasks.filter((task) => (taskPercentById[task.id] || '0') !== task.percent_complete);

      if (taskUpdates.length > 0) {
        await Promise.all(
          taskUpdates.map((task) =>
            tasksApi.update(task.id, {
              percent_complete: taskPercentById[task.id] || '0',
            })
          )
        );
      }

      await statusUpdatesApi.create({
        deliverable: deliverableId,
        period_end: quickAddStatusUpdate.period_end,
        status: quickAddStatusUpdate.status,
        summary: quickAddStatusUpdate.summary,
      });

      cancelQuickAddStatusUpdate();
      await loadContractDeliverables(contractId, true);
      await loadContracts();
    } catch (err) {
      setQuickAddError(getApiErrorMessage(err, 'Failed to save status update'));
    } finally {
      setSavingQuickAddDeliverableId(null);
    }
  };

  const handleToggleContractDetails = async (contractId: number) => {
    const isExpanded = expandedContractIds.includes(contractId);
    if (isExpanded) {
      setExpandedContractIds((current) => current.filter((id) => id !== contractId));
      return;
    }

    setExpandedContractIds((current) => [...current, contractId]);
    await loadContractDeliverables(contractId);
  };

  const filteredContracts = useMemo(() => {
    const query = search.trim().toLowerCase();

    return contracts.filter((contract) => {
      if (query) {
        const matchesName = contract.name.toLowerCase().includes(query);
        const matchesClient = contract.client_name.toLowerCase().includes(query);
        const matchesId = String(contract.id).includes(query);
        if (!matchesName && !matchesClient && !matchesId) {
          return false;
        }
      }

      if (contractType !== 'all' && contract.contract_type !== contractType) {
        return false;
      }

      if (staffFilterId !== 'all' && !selectedStaffContractIds.includes(contract.id)) {
        return false;
      }

      if (tagFilter !== 'all') {
        const contractTags = (contract.tags || []).map((tag) => tag.toLowerCase());
        if (!contractTags.includes(tagFilter.toLowerCase())) {
          return false;
        }
      }

      if (!showInactive && contract.status !== 'active') {
        return false;
      }

      const overExpected = hasOverExpectedFlag(contract);
      if (flag === 'any' && !contract.is_over_budget && !contract.is_overassigned && !overExpected) {
        return false;
      }
      if (flag === 'over_budget' && !contract.is_over_budget) {
        return false;
      }
      if (flag === 'overassigned' && !contract.is_overassigned) {
        return false;
      }
      if (flag === 'over_expected' && !overExpected) {
        return false;
      }

      return true;
    });
  }, [contracts, search, contractType, tagFilter, staffFilterId, selectedStaffContractIds, showInactive, flag]);

  const availableTags = useMemo(() => {
    const allTags = contracts.flatMap((contract) => contract.tags || []);
    return Array.from(new Set(allTags)).sort((left, right) => left.localeCompare(right));
  }, [contracts]);

  const sortedStaffMembers = useMemo(() => {
    return [...staffMembers].sort((left, right) => {
      const leftName = `${left.first_name} ${left.last_name}`.trim().toLowerCase();
      const rightName = `${right.first_name} ${right.last_name}`.trim().toLowerCase();
      return leftName.localeCompare(rightName);
    });
  }, [staffMembers]);

  const filteredInitiatives = useMemo(() => {
    return initiatives.filter((initiative) => {
      if (!showInactive && initiative.status !== 'active') {
        return false;
      }

      if (staffFilterId !== 'all' && initiative.owner !== staffFilterId) {
        return false;
      }

      return true;
    });
  }, [initiatives, showInactive, staffFilterId]);

  const sortedContracts = useMemo(() => {
    const valueForSort = (contract: Contract): string | number => {
      const assignedPerWeek = toNumber(contract.assigned_budget_hours_per_week);
      const burn4Week = toNumber(contract.actual_burn_rate);

      switch (sortKey) {
        case 'name':
          return (contract.name || `Contract #${contract.id}`).toLowerCase();
        case 'budget_hours':
          return toNumber(contract.budget_hours);
        case 'spent_hours':
          return toNumber(contract.spent_hours);
        case 'assigned_per_week':
          return assignedPerWeek;
        case 'burn_4wk':
          return burn4Week;
        case 'variance_per_week':
          return burn4Week - assignedPerWeek;
        case 'projected_lateness_days': {
          if (isOverHours(contract)) {
            return Number.POSITIVE_INFINITY;
          }
          const projectedFinish = getProjectedFinishDate(contract);
          const varianceDays = getFinishVariance(projectedFinish, contract.end_date);
          return varianceDays ?? Number.NEGATIVE_INFINITY;
        }
      }
    };

    const sorted = [...filteredContracts];
    sorted.sort((left, right) => {
      const a = valueForSort(left);
      const b = valueForSort(right);

      if (typeof a === 'string' && typeof b === 'string') {
        return sortDirection === 'asc' ? a.localeCompare(b) : b.localeCompare(a);
      }

      const numericA = Number(a);
      const numericB = Number(b);
      return sortDirection === 'asc' ? numericA - numericB : numericB - numericA;
    });

    return sorted;
  }, [filteredContracts, sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((currentDirection) => (currentDirection === 'asc' ? 'desc' : 'asc'));
      return;
    }

    setSortKey(key);
    setSortDirection(key === 'name' ? 'asc' : 'desc');
  };

  const renderSortableHeader = (
    key: SortKey,
    label: string,
    align: 'left' | 'right' = 'left'
  ) => (
    <TableCell align={align} sortDirection={sortKey === key ? sortDirection : false}>
      <TableSortLabel
        active={sortKey === key}
        direction={sortKey === key ? sortDirection : 'asc'}
        onClick={() => handleSort(key)}
      >
        {label}
      </TableSortLabel>
    </TableCell>
  );

  const startInitiativeQuickUpdate = (initiative: Initiative) => {
    setInitiativeQuickUpdateDialogInitiative(initiative);
    setInitiativeQuickUpdateError('');
    setInitiativeQuickUpdate({
      period_end: new Date().toISOString().split('T')[0],
      percent_complete: initiative.current_percent_complete || '0',
      summary: '',
    });
  };

  const openInitiativeContextMenu = (event: React.MouseEvent, initiative: Initiative) => {
    event.preventDefault();
    event.stopPropagation();
    setInitiativeContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
      initiative,
    });
  };

  const closeInitiativeContextMenu = () => {
    setInitiativeContextMenu(null);
  };

  const openEditInitiativeDialogFromMenu = () => {
    if (!initiativeContextMenu) {
      return;
    }

    const initiative = initiativeContextMenu.initiative;
    setEditingInitiativeId(initiative.id);
    setInitiativeFormData({
      name: initiative.name,
      owner: initiative.owner ? String(initiative.owner) : '',
      status: initiative.status,
      tags: (initiative.tags || []).join(', '),
      target_date: initiative.target_date || '',
      notes: initiative.notes || '',
    });
    setInitiativeEditError('');
    setInitiativeEditDialogOpen(true);
    closeInitiativeContextMenu();
  };

  const closeInitiativeEditDialog = () => {
    if (savingInitiativeEdit) {
      return;
    }
    setInitiativeEditDialogOpen(false);
    setEditingInitiativeId(null);
    setInitiativeEditError('');
  };

  const saveInitiativeEdit = async () => {
    if (!editingInitiativeId) {
      return;
    }

    setSavingInitiativeEdit(true);
    setInitiativeEditError('');

    try {
      const tags = initiativeFormData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      await initiativesApi.update(editingInitiativeId, {
        name: initiativeFormData.name,
        owner: initiativeFormData.owner ? Number(initiativeFormData.owner) : null,
        status: initiativeFormData.status,
        tags,
        target_date: initiativeFormData.target_date || null,
        notes: initiativeFormData.notes,
      });

      closeInitiativeEditDialog();
      await loadInitiatives();
    } catch (err) {
      setInitiativeEditError(getApiErrorMessage(err, 'Failed to save initiative'));
    } finally {
      setSavingInitiativeEdit(false);
    }
  };

  const saveInitiativeQuickUpdate = async () => {
    if (!initiativeQuickUpdateDialogInitiative) {
      return;
    }

    setSavingInitiativeQuickUpdate(true);
    setInitiativeQuickUpdateError('');
    try {
      await initiativeWeeklyUpdatesApi.create({
        initiative: initiativeQuickUpdateDialogInitiative.id,
        period_end: initiativeQuickUpdate.period_end,
        percent_complete: initiativeQuickUpdate.percent_complete,
        summary: initiativeQuickUpdate.summary,
      });
      setInitiativeQuickUpdateDialogInitiative(null);
      await loadInitiatives();
    } catch (err) {
      setInitiativeQuickUpdateError(getApiErrorMessage(err, 'Failed to save weekly update'));
    } finally {
      setSavingInitiativeQuickUpdate(false);
    }
  };

  const updateInitiativeStatus = async (initiativeId: number, status: Initiative['status']) => {
    setSavingInitiativeStatusId(initiativeId);
    try {
      await initiativesApi.update(initiativeId, { status });
      setInitiatives((current) =>
        current.map((initiative) =>
          initiative.id === initiativeId
            ? {
                ...initiative,
                status,
              }
            : initiative
        )
      );
    } finally {
      setSavingInitiativeStatusId(null);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        At-a-glance contract health view.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        <TextField
          label="Search"
          size="small"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          sx={{ minWidth: 220 }}
          placeholder="Name, client, or ID"
        />
        <TextField
          select
          label="Contract Type"
          size="small"
          value={contractType}
          onChange={(event) => setContractType(event.target.value as 'all' | Contract['contract_type'])}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All Types</MenuItem>
          {CONTRACT_TYPE_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Flags"
          size="small"
          value={flag}
          onChange={(event) => setFlag(event.target.value as FlagFilter)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All</MenuItem>
          <MenuItem value="any">Any Flag</MenuItem>
          <MenuItem value="over_budget">Over Budget</MenuItem>
          <MenuItem value="overassigned">Overassigned</MenuItem>
          <MenuItem value="over_expected">Over Expected</MenuItem>
        </TextField>
        <TextField
          select
          label="Tag"
          size="small"
          value={tagFilter}
          onChange={(event) => setTagFilter(event.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="all">All Tags</MenuItem>
          {availableTags.map((tag) => (
            <MenuItem key={tag} value={tag}>
              {tag}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Staff"
          size="small"
          value={staffFilterId === 'all' ? 'all' : String(staffFilterId)}
          onChange={(event) =>
            setStaffFilterId(event.target.value === 'all' ? 'all' : Number(event.target.value))
          }
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="all">All Staff</MenuItem>
          {sortedStaffMembers.map((staffMember) => (
            <MenuItem key={staffMember.id} value={String(staffMember.id)}>
              {staffMember.first_name} {staffMember.last_name}
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
          }
          label="Show inactive"
          sx={{ ml: 'auto' }}
        />
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 56 }} />
                {renderSortableHeader('name', 'Contract Name')}
                {renderSortableHeader('budget_hours', 'Budget Hours', 'right')}
                {renderSortableHeader('spent_hours', 'Hours Spent', 'right')}
                {renderSortableHeader('assigned_per_week', 'Assigned Hours / Week', 'right')}
                {renderSortableHeader('burn_4wk', 'Burn (4wk avg)', 'right')}
                {renderSortableHeader('variance_per_week', 'Variance Hrs / Week', 'right')}
                <TableCell align="right">% Complete</TableCell>
                {renderSortableHeader('projected_lateness_days', 'Projected Contract Finish')}
                <TableCell>Flags</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedContracts.map((contract) => {
                const isExpanded = expandedContractIds.includes(contract.id);
                const contractDeliverables = deliverablesByContract[contract.id] || [];
                const loadingContractDeliverables = loadingDeliverablesByContract[contract.id];
                const showStaleOnly = !!showStaleOnlyByContract[contract.id];
                const showComplete = showCompleteByContract[contract.id] ?? true;
                const staffScopedDeliverables = staffFilterId === 'all'
                  ? contractDeliverables
                  : contractDeliverables.filter((deliverable) => selectedStaffDeliverableIds.includes(deliverable.id));
                const activeCompleteFilterDeliverables = showComplete
                  ? staffScopedDeliverables
                  : staffScopedDeliverables.filter((deliverable) => toNumber(deliverable.estimated_percent_complete) < 100);
                const visibleDeliverables = showStaleOnly
                  ? activeCompleteFilterDeliverables.filter((deliverable) => isStatusUpdateStale(deliverable))
                  : activeCompleteFilterDeliverables;
                const assignedPerWeek = toNumber(contract.assigned_budget_hours_per_week);
                const burn4Week = toNumber(contract.actual_burn_rate);
                const variancePerWeek = burn4Week - assignedPerWeek;
                const overBudgetHours = Math.max(0, toNumber(contract.spent_hours) - toNumber(contract.budget_hours));

                const projectedFinish = getProjectedFinishDate(contract);
                const finishVariance = getFinishVariance(projectedFinish, contract.end_date);
                const projectionPill = getProjectionPill(finishVariance);
                const overHours = isOverHours(contract);

                return (
                  <Fragment key={contract.id}>
                    <TableRow
                      hover
                      onClick={() => navigate(`/contracts/${contract.id}`)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell onClick={(event) => event.stopPropagation()}>
                        <IconButton
                          size="small"
                          onClick={(event) => {
                            event.stopPropagation();
                            void handleToggleContractDetails(contract.id);
                          }}
                        >
                          {isExpanded ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                        </IconButton>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {contract.name || `Contract #${contract.id}`}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {contract.client_name} • {getContractTypeShortLabel(contract.contract_type)} • {formatContractStatusLabel(contract.status)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">{toNumber(contract.budget_hours).toFixed(1)}</TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.2 }}>
                          <Typography variant="body2">{toNumber(contract.spent_hours).toFixed(1)}</Typography>
                          {overBudgetHours > 0 && (
                            <Typography variant="caption" sx={{ color: 'error.main' }}>
                              +{overBudgetHours.toFixed(1)}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align="right">{assignedPerWeek.toFixed(1)}</TableCell>
                      <TableCell align="right">{burn4Week.toFixed(1)}</TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          color: variancePerWeek > 0 ? 'error.main' : 'success.main',
                          fontWeight: 500,
                        }}
                      >
                        {variancePerWeek > 0 ? '+' : ''}
                        {variancePerWeek.toFixed(1)}
                      </TableCell>
                      <TableCell align="right">{toNumber(contract.estimated_percent_complete).toFixed(0)}%</TableCell>
                      <TableCell>
                        {overHours ? (
                          <Chip label="Over Hours" color="error" size="small" />
                        ) : projectedFinish ? (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="body2">{formatDate(projectedFinish)}</Typography>
                            <Chip label={projectionPill.label} color={projectionPill.color} size="small" />
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Not enough assignment data
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {contract.is_over_budget && <Chip label="Over Budget" size="small" color="error" />}
                          {contract.is_overassigned && <Chip label="Overassigned" size="small" color="warning" />}
                          {hasOverExpectedFlag(contract) && (
                            <Chip label="Over Expected" size="small" color="warning" variant="outlined" />
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell colSpan={10} sx={{ py: 0, borderBottom: isExpanded ? undefined : 0 }}>
                        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                          <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                              <Typography variant="subtitle2">
                                Deliverables
                              </Typography>
                              <FormControlLabel
                                control={
                                  <Switch
                                    size="small"
                                    checked={showStaleOnly}
                                    onChange={(event) =>
                                      setShowStaleOnlyByContract((current) => ({
                                        ...current,
                                        [contract.id]: event.target.checked,
                                      }))
                                    }
                                  />
                                }
                                label="Show stale only"
                                sx={{ mr: 0 }}
                              />
                              <FormControlLabel
                                control={
                                  <Switch
                                    size="small"
                                    checked={showComplete}
                                    onChange={(event) =>
                                      setShowCompleteByContract((current) => ({
                                        ...current,
                                        [contract.id]: event.target.checked,
                                      }))
                                    }
                                  />
                                }
                                label="Show complete"
                                sx={{ mr: 0 }}
                              />
                            </Box>

                            {loadingContractDeliverables ? (
                              <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                                <CircularProgress size={20} />
                              </Box>
                            ) : visibleDeliverables.length === 0 ? (
                              <Typography variant="body2" color="text.secondary">
                                {showStaleOnly ? 'No stale deliverables found.' : 'No deliverables found.'}
                              </Typography>
                            ) : (
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell sx={{ width: 320 }}>Deliverable</TableCell>
                                    <TableCell align="right" sx={{ width: 90, whiteSpace: 'nowrap' }}>% Complete</TableCell>
                                    <TableCell sx={{ width: 120, whiteSpace: 'nowrap' }}>Latest Status</TableCell>
                                    <TableCell sx={{ width: 260 }}>Latest Summary</TableCell>
                                    <TableCell sx={{ width: 150, whiteSpace: 'nowrap' }}>Update Health</TableCell>
                                    <TableCell align="right" sx={{ width: 110, whiteSpace: 'nowrap' }}>Actions</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {visibleDeliverables.map((deliverable) => {
                                    const latestStatusUpdate = deliverable.latest_status_update;
                                    const isStale = isStatusUpdateStale(deliverable);
                                    const isUnassigned = (deliverable.assignments?.length || 0) === 0;

                                    return (
                                      <Fragment key={deliverable.id}>
                                        <TableRow
                                          hover
                                          onClick={() => navigate(`/deliverables/${deliverable.id}`)}
                                          onContextMenu={(event) => openUnassignedMenu(event, deliverable.id)}
                                          sx={{ cursor: 'pointer' }}
                                        >
                                          <TableCell sx={{ width: 320, maxWidth: 320 }}>
                                            <Typography
                                              variant="body2"
                                              sx={{ whiteSpace: 'normal', wordBreak: 'break-word', overflowWrap: 'anywhere' }}
                                            >
                                              {deliverable.name || `Deliverable #${deliverable.id}`}
                                            </Typography>
                                          </TableCell>
                                          <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                                            {toNumber(deliverable.estimated_percent_complete).toFixed(0)}%
                                          </TableCell>
                                          <TableCell>
                                            {latestStatusUpdate ? (
                                              <Chip
                                                label={formatDeliverableStatusLabel(latestStatusUpdate.status)}
                                                size="small"
                                                color={getDeliverableStatusChipColor(latestStatusUpdate.status)}
                                              />
                                            ) : (
                                              <Typography variant="body2" color="text.secondary">
                                                No status
                                              </Typography>
                                            )}
                                          </TableCell>
                                          <TableCell sx={{ width: 260, maxWidth: 260 }}>
                                            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                                              {latestStatusUpdate?.summary || 'No summary'}
                                            </Typography>
                                          </TableCell>
                                          <TableCell sx={{ whiteSpace: 'nowrap' }}>
                                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                                              {isStale ? (
                                                <Chip
                                                  label={
                                                    latestStatusUpdate
                                                      ? `Stale (${getDaysSince(latestStatusUpdate.period_end)}d)`
                                                      : 'No recent update'
                                                  }
                                                  size="small"
                                                  color="warning"
                                                  variant="outlined"
                                                />
                                              ) : (
                                                <Chip label="Current" size="small" color="success" variant="outlined" />
                                              )}
                                              {isUnassigned && (
                                                <Chip
                                                  label="Unassigned"
                                                  size="small"
                                                  color="info"
                                                  variant="outlined"
                                                />
                                              )}
                                              <Typography variant="caption" color="text.secondary">
                                                {latestStatusUpdate ? formatDate(new Date(latestStatusUpdate.period_end)) : 'No report date'}
                                              </Typography>
                                            </Box>
                                          </TableCell>
                                          <TableCell
                                            align="right"
                                            sx={{ whiteSpace: 'nowrap' }}
                                            onClick={(event) => event.stopPropagation()}
                                          >
                                            <Button
                                              size="small"
                                              variant="outlined"
                                              onClick={() => {
                                                void startQuickAddStatusUpdate(contract.id, deliverable);
                                              }}
                                            >
                                              Add Update
                                            </Button>
                                          </TableCell>
                                        </TableRow>
                                      </Fragment>
                                    );
                                  })}
                                </TableBody>
                              </Table>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </Fragment>
                );
              })}
              {sortedContracts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    No contracts found for current filters
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
          <Typography variant="h6">Initiatives (Non-contract)</Typography>
          <Button size="small" onClick={() => navigate('/initiatives')}>Open Initiatives</Button>
        </Box>

        {loadingInitiatives ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
            <CircularProgress size={20} />
          </Box>
        ) : filteredInitiatives.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {staffFilterId === 'all' ? 'No initiatives yet.' : 'No initiatives assigned to this staff member.'}
          </Typography>
        ) : (
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Initiative</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">% Complete</TableCell>
                  <TableCell>Latest Update</TableCell>
                  <TableCell>Update Health</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredInitiatives.map((initiative) => {
                  const latest = initiative.latest_update;
                  return (
                    <Fragment key={initiative.id}>
                      <TableRow onContextMenu={(event) => openInitiativeContextMenu(event, initiative)}>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{initiative.name}</Typography>
                          <Typography variant="caption" color="text.secondary">{initiative.owner_name || 'Unassigned'}</Typography>
                        </TableCell>
                        <TableCell>
                          <TextField
                            select
                            size="small"
                            value={initiative.status}
                            onChange={(event) =>
                              void updateInitiativeStatus(initiative.id, event.target.value as Initiative['status'])
                            }
                            disabled={savingInitiativeStatusId === initiative.id}
                            sx={{ minWidth: 130 }}
                          >
                            <MenuItem value="active">Active</MenuItem>
                            <MenuItem value="on_hold">On Hold</MenuItem>
                            <MenuItem value="completed">Completed</MenuItem>
                          </TextField>
                        </TableCell>
                        <TableCell align="right">{toNumber(initiative.current_percent_complete).toFixed(0)}%</TableCell>
                        <TableCell>
                          {latest ? (
                            <Typography variant="body2">{formatDate(new Date(latest.period_end))}</Typography>
                          ) : (
                            <Typography variant="body2" color="text.secondary">No updates</Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {initiative.is_update_stale ? (
                            <Chip
                              size="small"
                              color="warning"
                              variant="outlined"
                              label={latest ? `Stale (${getDaysSince(latest.period_end)}d)` : 'No recent update'}
                            />
                          ) : (
                            <Chip size="small" color="success" variant="outlined" label="Current" />
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Button size="small" variant="outlined" onClick={() => startInitiativeQuickUpdate(initiative)}>
                            Add Weekly Update
                          </Button>
                        </TableCell>
                      </TableRow>
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      <Dialog
        open={!!quickAddDialogDeliverable}
        onClose={() => {
          if (savingQuickAddDeliverableId === quickAddDialogDeliverable?.id) {
            return;
          }
          cancelQuickAddStatusUpdate();
        }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Add Deliverable Update
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {quickAddError && (
              <Alert severity="error">{quickAddError}</Alert>
            )}

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Deliverable
              </Typography>
              <Typography variant="body2">
                {quickAddDialogDeliverable?.name || (quickAddDialogDeliverable ? `Deliverable #${quickAddDialogDeliverable.id}` : '')}
              </Typography>
            </Box>

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Assigned to
              </Typography>
              {quickAddDialogDeliverable && getAssignedStaffNames(quickAddDialogDeliverable).length > 0 ? (
                <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', rowGap: 0.5 }}>
                  {getAssignedStaffNames(quickAddDialogDeliverable).map((name) => (
                    <Chip key={name} size="small" variant="outlined" label={name} />
                  ))}
                </Stack>
              ) : (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                  <Chip
                    label="Unassigned"
                    size="small"
                    color="info"
                    variant="outlined"
                    onContextMenu={(event) => {
                      if (quickAddDialogDeliverable) {
                        openUnassignedMenu(event, quickAddDialogDeliverable.id);
                      }
                    }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    No staff assigned
                  </Typography>
                </Box>
              )}
            </Box>

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Previous update
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5 }}>
                {quickAddDialogDeliverable?.latest_status_update ? (
                  <>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      {formatDate(new Date(quickAddDialogDeliverable.latest_status_update.period_end))} • {formatDeliverableStatusLabel(quickAddDialogDeliverable.latest_status_update.status)}
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {quickAddDialogDeliverable.latest_status_update.summary || 'No summary'}
                    </Typography>
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No previous update
                  </Typography>
                )}
              </Paper>
            </Box>

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
              <TextField
                label="Period End"
                type="date"
                size="small"
                value={quickAddStatusUpdate.period_end}
                onChange={(event) =>
                  setQuickAddStatusUpdate((current) => ({
                    ...current,
                    period_end: event.target.value,
                  }))
                }
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                label="Status"
                select
                size="small"
                value={quickAddStatusUpdate.status}
                onChange={(event) =>
                  setQuickAddStatusUpdate((current) => ({
                    ...current,
                    status: event.target.value as DeliverableStatusUpdate['status'],
                  }))
                }
                sx={{ minWidth: 170 }}
              >
                <MenuItem value="on_track">On Track</MenuItem>
                <MenuItem value="at_risk">At Risk</MenuItem>
                <MenuItem value="off_track">Off Track</MenuItem>
              </TextField>
            </Stack>

            <TextField
              label="Summary"
              size="small"
              value={quickAddStatusUpdate.summary}
              onChange={(event) =>
                setQuickAddStatusUpdate((current) => ({
                  ...current,
                  summary: event.target.value,
                }))
              }
              multiline
              minRows={3}
              fullWidth
            />

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Tasks (% complete)
              </Typography>
              {loadingQuickAddTasks ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={20} />
                </Box>
              ) : quickAddTasks.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No tasks for this deliverable.
                </Typography>
              ) : (
                <Stack spacing={1}>
                  {quickAddTasks.map((task) => (
                    <Stack key={task.id} direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ alignItems: { sm: 'center' } }}>
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {task.title}
                      </Typography>
                      <TextField
                        label="% Complete"
                        type="number"
                        size="small"
                        value={taskPercentById[task.id] ?? task.percent_complete}
                        onChange={(event) =>
                          setTaskPercentById((current) => ({
                            ...current,
                            [task.id]: event.target.value,
                          }))
                        }
                        inputProps={{ min: 0, max: 100, step: 1 }}
                        sx={{ width: 140 }}
                      />
                    </Stack>
                  ))}
                </Stack>
              )}
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={cancelQuickAddStatusUpdate}
            disabled={savingQuickAddDeliverableId === quickAddDialogDeliverable?.id}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => {
              if (quickAddDialogContractId && quickAddDialogDeliverable) {
                void saveQuickAddStatusUpdate(quickAddDialogContractId, quickAddDialogDeliverable.id);
              }
            }}
            disabled={
              !!quickAddDialogDeliverable && savingQuickAddDeliverableId === quickAddDialogDeliverable.id
            }
          >
            {!!quickAddDialogDeliverable && savingQuickAddDeliverableId === quickAddDialogDeliverable.id ? 'Saving...' : 'Save Update'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={!!initiativeQuickUpdateDialogInitiative}
        onClose={() => {
          if (savingInitiativeQuickUpdate) {
            return;
          }
          setInitiativeQuickUpdateDialogInitiative(null);
          setInitiativeQuickUpdateError('');
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Initiative Weekly Update</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {initiativeQuickUpdateError && <Alert severity="error">{initiativeQuickUpdateError}</Alert>}

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Initiative
              </Typography>
              <Typography variant="body2">
                {initiativeQuickUpdateDialogInitiative?.name || ''}
              </Typography>
            </Box>

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                Previous update
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5 }}>
                {initiativeQuickUpdateDialogInitiative?.latest_update ? (
                  <>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      {formatDate(new Date(initiativeQuickUpdateDialogInitiative.latest_update.period_end))} • {toNumber(initiativeQuickUpdateDialogInitiative.latest_update.percent_complete).toFixed(0)}%
                    </Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {initiativeQuickUpdateDialogInitiative.latest_update.summary || 'No summary'}
                    </Typography>
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No previous update
                  </Typography>
                )}
              </Paper>
            </Box>

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
              <TextField
                label="Period End"
                type="date"
                size="small"
                value={initiativeQuickUpdate.period_end}
                onChange={(event) =>
                  setInitiativeQuickUpdate((current) => ({ ...current, period_end: event.target.value }))
                }
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                label="% Complete"
                type="number"
                size="small"
                value={initiativeQuickUpdate.percent_complete}
                onChange={(event) =>
                  setInitiativeQuickUpdate((current) => ({ ...current, percent_complete: event.target.value }))
                }
                inputProps={{ min: 0, max: 100, step: 1 }}
                sx={{ width: 160 }}
              />
            </Stack>

            <TextField
              label="Summary"
              size="small"
              value={initiativeQuickUpdate.summary}
              onChange={(event) =>
                setInitiativeQuickUpdate((current) => ({ ...current, summary: event.target.value }))
              }
              multiline
              minRows={3}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setInitiativeQuickUpdateDialogInitiative(null);
              setInitiativeQuickUpdateError('');
            }}
            disabled={savingInitiativeQuickUpdate}
          >
            Cancel
          </Button>
          <Button variant="contained" onClick={() => void saveInitiativeQuickUpdate()} disabled={savingInitiativeQuickUpdate}>
            {savingInitiativeQuickUpdate ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Menu
        open={!!unassignedMenuPosition}
        onClose={closeUnassignedMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          unassignedMenuPosition
            ? { top: unassignedMenuPosition.mouseY, left: unassignedMenuPosition.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={openEditDeliverableFromMenu}>Edit deliverable</MenuItem>
        <MenuItem onClick={openAssignDialogFromMenu}>Assign staff</MenuItem>
      </Menu>

      <Menu
        open={initiativeContextMenu !== null}
        onClose={closeInitiativeContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          initiativeContextMenu !== null
            ? { top: initiativeContextMenu.mouseY, left: initiativeContextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={openEditInitiativeDialogFromMenu}>Edit initiative</MenuItem>
      </Menu>

      <Dialog open={initiativeEditDialogOpen} onClose={closeInitiativeEditDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Initiative</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {initiativeEditError && <Alert severity="error">{initiativeEditError}</Alert>}
            <TextField
              label="Name"
              value={initiativeFormData.name}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              required
              fullWidth
            />
            <TextField
              select
              label="Owner"
              value={initiativeFormData.owner}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  owner: event.target.value,
                }))
              }
              fullWidth
            >
              <MenuItem value="">Unassigned</MenuItem>
              {sortedStaffMembers.map((staffMember) => (
                <MenuItem key={staffMember.id} value={String(staffMember.id)}>
                  {staffMember.first_name} {staffMember.last_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Status"
              value={initiativeFormData.status}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  status: event.target.value as Initiative['status'],
                }))
              }
              fullWidth
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="on_hold">On Hold</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
            </TextField>
            <TextField
              label="Tags"
              value={initiativeFormData.tags}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  tags: event.target.value,
                }))
              }
              helperText="Comma-separated (example: internal, ops)"
              fullWidth
            />
            <TextField
              label="Target Date"
              type="date"
              value={initiativeFormData.target_date}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  target_date: event.target.value,
                }))
              }
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={initiativeFormData.notes}
              onChange={(event) =>
                setInitiativeFormData((current) => ({
                  ...current,
                  notes: event.target.value,
                }))
              }
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeInitiativeEditDialog} disabled={savingInitiativeEdit}>Cancel</Button>
          <Button
            onClick={() => {
              void saveInitiativeEdit();
            }}
            variant="contained"
            disabled={savingInitiativeEdit || !initiativeFormData.name.trim()}
          >
            {savingInitiativeEdit ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={assignDialogOpen} onClose={closeAssignDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Assign Staff</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {assignDialogError && <Alert severity="error">{assignDialogError}</Alert>}
            <TextField
              select
              label="Staff"
              size="small"
              value={assigningStaffId}
              onChange={(event) => setAssigningStaffId(event.target.value)}
              required
              fullWidth
            >
              <MenuItem value="">Select staff</MenuItem>
              {sortedStaffMembers.map((staffMember) => (
                <MenuItem key={staffMember.id} value={String(staffMember.id)}>
                  {staffMember.first_name} {staffMember.last_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Budget Hours"
              type="number"
              size="small"
              value={assigningBudgetHours}
              onChange={(event) => setAssigningBudgetHours(event.target.value)}
              inputProps={{ min: 0, step: 0.5 }}
              fullWidth
            />
            <FormControlLabel
              control={<Switch checked={assigningIsLead} onChange={(event) => setAssigningIsLead(event.target.checked)} />}
              label="Lead assignment"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeAssignDialog} disabled={savingAssignment}>Cancel</Button>
          <Button onClick={saveAssignment} variant="contained" disabled={savingAssignment || !assigningStaffId}>
            {savingAssignment ? 'Saving...' : 'Save Assignment'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}