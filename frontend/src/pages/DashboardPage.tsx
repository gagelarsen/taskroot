import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  CircularProgress,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
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
import { contractsApi, deliverablesApi, statusUpdatesApi } from '../api/client';
import type { Contract, Deliverable, DeliverableStatusUpdate } from '../types/api';
import { CONTRACT_TYPE_OPTIONS, getContractTypeShortLabel } from '../utils/contractTypes';
import { formatContractStatusLabel } from '../utils/contractStatus';
import { formatDeliverableStatusLabel, getDeliverableStatusChipColor } from '../utils/statusUpdates';

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

export function DashboardPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [deliverablesByContract, setDeliverablesByContract] = useState<Record<number, Deliverable[]>>({});
  const [loadingDeliverablesByContract, setLoadingDeliverablesByContract] = useState<Record<number, boolean>>({});
  const [expandedContractIds, setExpandedContractIds] = useState<number[]>([]);
  const [showStaleOnlyByContract, setShowStaleOnlyByContract] = useState<Record<number, boolean>>({});
  const [quickAddDeliverableId, setQuickAddDeliverableId] = useState<number | null>(null);
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
  const [quickAddErrorByDeliverableId, setQuickAddErrorByDeliverableId] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [contractType, setContractType] = useState<'all' | Contract['contract_type']>('all');
  const [tagFilter, setTagFilter] = useState('all');
  const [showInactive, setShowInactive] = useState(false);
  const [flag, setFlag] = useState<FlagFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('projected_lateness_days');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
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

  const getApiErrorMessage = (err: unknown, fallbackMessage: string): string => {
    if (!(err instanceof AxiosError)) {
      return fallbackMessage;
    }

    const responseData = err.response?.data;
    if (typeof responseData === 'string') {
      return responseData;
    }

    if (responseData?.detail && typeof responseData.detail === 'string') {
      return responseData.detail;
    }

    if (responseData && typeof responseData === 'object') {
      for (const value of Object.values(responseData as Record<string, unknown>)) {
        if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'string') {
          return value[0];
        }
        if (typeof value === 'string') {
          return value;
        }
      }
    }

    return fallbackMessage;
  };

  const startQuickAddStatusUpdate = (deliverableId: number) => {
    setQuickAddDeliverableId(deliverableId);
    setQuickAddStatusUpdate({
      period_end: new Date().toISOString().split('T')[0],
      status: 'on_track',
      summary: '',
    });
    setQuickAddErrorByDeliverableId((current) => ({ ...current, [deliverableId]: '' }));
  };

  const cancelQuickAddStatusUpdate = () => {
    setQuickAddDeliverableId(null);
  };

  const saveQuickAddStatusUpdate = async (contractId: number, deliverableId: number) => {
    setSavingQuickAddDeliverableId(deliverableId);
    setQuickAddErrorByDeliverableId((current) => ({ ...current, [deliverableId]: '' }));

    try {
      await statusUpdatesApi.create({
        deliverable: deliverableId,
        period_end: quickAddStatusUpdate.period_end,
        status: quickAddStatusUpdate.status,
        summary: quickAddStatusUpdate.summary,
      });

      setQuickAddDeliverableId(null);
      await loadContractDeliverables(contractId, true);
    } catch (err) {
      setQuickAddErrorByDeliverableId((current) => ({
        ...current,
        [deliverableId]: getApiErrorMessage(err, 'Failed to save status update'),
      }));
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
  }, [contracts, search, contractType, tagFilter, showInactive, flag]);

  const availableTags = useMemo(() => {
    const allTags = contracts.flatMap((contract) => contract.tags || []);
    return Array.from(new Set(allTags)).sort((left, right) => left.localeCompare(right));
  }, [contracts]);

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
                const visibleDeliverables = showStaleOnly
                  ? contractDeliverables.filter((deliverable) => isStatusUpdateStale(deliverable))
                  : contractDeliverables;
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
                                    const isQuickAddOpen = quickAddDeliverableId === deliverable.id;
                                    const quickAddError = quickAddErrorByDeliverableId[deliverable.id];

                                    return (
                                      <Fragment key={deliverable.id}>
                                        <TableRow
                                          hover
                                          onClick={() => navigate(`/deliverables/${deliverable.id}`)}
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
                                              onClick={() => startQuickAddStatusUpdate(deliverable.id)}
                                            >
                                              Add Update
                                            </Button>
                                          </TableCell>
                                        </TableRow>
                                        {isQuickAddOpen && (
                                          <TableRow>
                                            <TableCell colSpan={6}>
                                              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                                {quickAddError && (
                                                  <Alert severity="error" sx={{ py: 0 }}>
                                                    {quickAddError}
                                                  </Alert>
                                                )}
                                                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
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
                                                    onKeyDown={(event) => {
                                                      if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                                                        event.preventDefault();
                                                        if (savingQuickAddDeliverableId !== deliverable.id) {
                                                          void saveQuickAddStatusUpdate(contract.id, deliverable.id);
                                                        }
                                                      }
                                                    }}
                                                    multiline
                                                    minRows={2}
                                                    sx={{ flex: 1, minWidth: 300 }}
                                                  />
                                                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                                    <Button
                                                      variant="contained"
                                                      size="small"
                                                      onClick={() => saveQuickAddStatusUpdate(contract.id, deliverable.id)}
                                                      disabled={savingQuickAddDeliverableId === deliverable.id}
                                                    >
                                                      {savingQuickAddDeliverableId === deliverable.id ? 'Saving...' : 'Save'}
                                                    </Button>
                                                    <Button size="small" onClick={cancelQuickAddStatusUpdate}>
                                                      Cancel
                                                    </Button>
                                                  </Box>
                                                </Box>
                                              </Box>
                                            </TableCell>
                                          </TableRow>
                                        )}
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
    </Box>
  );
}