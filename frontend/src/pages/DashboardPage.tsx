import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
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
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { contractsApi } from '../api/client';
import type { Contract } from '../types/api';
import { CONTRACT_TYPE_OPTIONS, getContractTypeShortLabel } from '../utils/contractTypes';

type ActivityFilter = 'all' | 'active' | 'inactive';
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

export function DashboardPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [contractType, setContractType] = useState<'all' | Contract['contract_type']>('all');
  const [activity, setActivity] = useState<ActivityFilter>('all');
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

      if (activity === 'active' && contract.status !== 'active') {
        return false;
      }

      if (activity === 'inactive' && contract.status === 'active') {
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
  }, [contracts, search, contractType, activity, flag]);

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
          label="Activity"
          size="small"
          value={activity}
          onChange={(event) => setActivity(event.target.value as ActivityFilter)}
          sx={{ minWidth: 140 }}
        >
          <MenuItem value="all">All</MenuItem>
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="inactive">Inactive</MenuItem>
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
                {renderSortableHeader('name', 'Contract Name')}
                {renderSortableHeader('budget_hours', 'Budget Hours', 'right')}
                {renderSortableHeader('spent_hours', 'Hours Spent', 'right')}
                {renderSortableHeader('assigned_per_week', 'Assigned Hours / Week', 'right')}
                {renderSortableHeader('burn_4wk', 'Burn (4wk avg)', 'right')}
                {renderSortableHeader('variance_per_week', 'Variance Hrs / Week', 'right')}
                {renderSortableHeader('projected_lateness_days', 'Projected Contract Finish')}
                <TableCell>Flags</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedContracts.map((contract) => {
                const assignedPerWeek = toNumber(contract.assigned_budget_hours_per_week);
                const burn4Week = toNumber(contract.actual_burn_rate);
                const variancePerWeek = burn4Week - assignedPerWeek;

                const projectedFinish = getProjectedFinishDate(contract);
                const finishVariance = getFinishVariance(projectedFinish, contract.end_date);
                const projectionPill = getProjectionPill(finishVariance);
                const overHours = isOverHours(contract);

                return (
                  <TableRow
                    key={contract.id}
                    hover
                    onClick={() => navigate(`/contracts/${contract.id}`)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {contract.name || `Contract #${contract.id}`}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {contract.client_name} • {getContractTypeShortLabel(contract.contract_type)} • {contract.status}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">{toNumber(contract.budget_hours).toFixed(1)}</TableCell>
                    <TableCell align="right">{toNumber(contract.spent_hours).toFixed(1)}</TableCell>
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
                );
              })}
              {sortedContracts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
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