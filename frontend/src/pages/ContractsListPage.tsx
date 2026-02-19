import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  Button,
  TextField,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Stack,
  Switch,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { contractsApi } from '../api/client';
import type { Contract, ContractFilters } from '../types/api';
import { FilterBar } from '../components/FilterBar';
import { StatusBadge } from '../components/StatusBadge';
import {
  CONTRACT_TYPE_OPTIONS,
  getContractTypeShortLabel,
} from '../utils/contractTypes';
import {
  CONTRACT_STATUS_OPTIONS,
  formatContractStatusLabel,
  getContractStatusChipColor,
} from '../utils/contractStatus';
import { AxiosError } from 'axios';

export function ContractsListPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<ContractFilters>({
    order_by: 'start_date',
    order_dir: 'desc',
  });
  const [showInactive, setShowInactive] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState({
    name: '',
    client_name: '',
    contract_number: '',
    tags: '',
    contract_type: 'fixed_cost' as Contract['contract_type'],
    budget_hours: '0',
    contract_amount: '',
    status: 'draft' as Contract['status'],
    start_date: '',
    end_date: '',
  });
  const navigate = useNavigate();

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await contractsApi.list({
        ...filters,
        status: showInactive ? undefined : 'active',
      });
      setContracts(data);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load contracts');
      } else {
        setError('Failed to load contracts');
      }
    } finally {
      setLoading(false);
    }
  }, [filters, showInactive]);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  const handleRowClick = (id: number) => {
    navigate(`/contracts/${id}`);
  };

  const orderByOptions = [
    { value: 'start_date', label: 'Start Date' },
    { value: 'end_date', label: 'End Date' },
    { value: 'status', label: 'Status' },
    { value: 'budget_hours', label: 'Budget' },
  ];

  const availableTags = useMemo(() => {
    const tags = contracts.flatMap((contract) => contract.tags || []);
    return Array.from(new Set(tags)).sort((left, right) => left.localeCompare(right));
  }, [contracts]);

  const handleOpenCreateDialog = () => {
    setError('');
    setFormErrors({});
    setFormData({
      name: '',
      client_name: '',
      contract_number: '',
      tags: '',
      contract_type: 'fixed_cost',
      budget_hours: '0',
      contract_amount: '',
      status: 'draft',
      start_date: '',
      end_date: '',
    });
    setDialogOpen(true);
  };

  const handleCloseCreateDialog = () => {
    if (saving) return;
    setDialogOpen(false);
  };

  const handleCreateContract = async () => {
    const nextErrors: Record<string, string> = {};
    if (!formData.name.trim()) nextErrors.name = 'Contract name is required';
    if (!formData.client_name.trim()) nextErrors.client_name = 'Client name is required';
    if (!formData.start_date) nextErrors.start_date = 'Start date is required';
    if (!formData.end_date) nextErrors.end_date = 'End date is required';
    if (
      formData.start_date &&
      formData.end_date &&
      new Date(formData.end_date).getTime() < new Date(formData.start_date).getTime()
    ) {
      nextErrors.end_date = 'End date must be on or after start date';
    }

    if (Object.keys(nextErrors).length > 0) {
      setFormErrors(nextErrors);
      return;
    }

    setSaving(true);
    setError('');
    setFormErrors({});
    try {
      const tags = formData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      await contractsApi.create({
        ...formData,
        contract_amount: formData.contract_amount === '' ? null : formData.contract_amount,
        tags,
      });
      setDialogOpen(false);
      await loadContracts();
    } catch (err) {
      if (err instanceof AxiosError) {
        const errorData = err.response?.data;
        if (typeof errorData === 'object' && errorData !== null) {
          const fieldErrors: Record<string, string> = {};
          for (const [field, value] of Object.entries(errorData as Record<string, unknown>)) {
            if (Array.isArray(value) && typeof value[0] === 'string') {
              fieldErrors[field] = value[0];
            } else if (typeof value === 'string') {
              fieldErrors[field] = value;
            }
          }
          if (Object.keys(fieldErrors).length > 0) {
            setFormErrors(fieldErrors);
          }

          const messages = Object.entries(errorData)
            .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
            .join('; ');
          setError(messages || 'Failed to save contract');
        } else {
          setError(errorData?.detail || 'Failed to save contract');
        }
      } else {
        setError('Failed to save contract');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Contracts</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleOpenCreateDialog}
        >
          Create Contract
        </Button>
      </Box>

      <FilterBar
        searchValue={filters.q || ''}
        onSearchChange={(q) => setFilters({ ...filters, q })}
        orderBy={filters.order_by || ''}
        orderDir={filters.order_dir}
        onOrderByChange={(order_by) => setFilters({ ...filters, order_by })}
        onOrderDirChange={(order_dir) => setFilters({ ...filters, order_dir })}
        orderByOptions={orderByOptions}
      >
        <TextField
          select
          label="Contract Type"
          variant="outlined"
          size="small"
          value={filters.contract_type || ''}
          onChange={(e) =>
            setFilters({
              ...filters,
              contract_type: (e.target.value || undefined) as ContractFilters['contract_type'],
            })
          }
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">All Types</MenuItem>
          {CONTRACT_TYPE_OPTIONS.map((contractTypeOption) => (
            <MenuItem key={contractTypeOption.value} value={contractTypeOption.value}>
              {contractTypeOption.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Tag"
          variant="outlined"
          size="small"
          value={filters.tags || ''}
          onChange={(e) =>
            setFilters({
              ...filters,
              tags: e.target.value || undefined,
            })
          }
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All Tags</MenuItem>
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
      </FilterBar>

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
                <TableCell>Name</TableCell>
                <TableCell>Contract #</TableCell>
                <TableCell>Client</TableCell>
                <TableCell sx={{ width: 110 }}>Contract Type</TableCell>
                <TableCell>Start Date</TableCell>
                <TableCell>End Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Budget Hours</TableCell>
                <TableCell align="right">Amount (USD)</TableCell>
                <TableCell align="right">Assigned/Week</TableCell>
                <TableCell align="right">Spent/Week</TableCell>
                <TableCell align="right">% Complete</TableCell>
                <TableCell align="right">Remaining</TableCell>
                <TableCell>Flags</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {contracts.map((contract) => (
                <TableRow
                  key={contract.id}
                  hover
                  onClick={() => handleRowClick(contract.id)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>{contract.name || `Contract #${contract.id}`}</TableCell>
                  <TableCell>{contract.contract_number || '-'}</TableCell>
                  <TableCell>{contract.client_name}</TableCell>
                  <TableCell sx={{ width: 110 }}>
                    <Chip
                      size="small"
                      variant="outlined"
                      sx={{ borderRadius: 999 }}
                      label={getContractTypeShortLabel(contract.contract_type)}
                    />
                  </TableCell>
                  <TableCell>{contract.start_date}</TableCell>
                  <TableCell>{contract.end_date}</TableCell>
                  <TableCell>
                    <Chip
                      label={formatContractStatusLabel(contract.status)}
                      size="small"
                      color={getContractStatusChipColor(contract.status)}
                    />
                  </TableCell>
                  <TableCell align="right">{parseFloat(contract.budget_hours).toFixed(1)}</TableCell>
                  <TableCell align="right">
                    {contract.contract_amount !== null ? parseFloat(contract.contract_amount).toFixed(2) : '-'}
                  </TableCell>
                  <TableCell align="right">{parseFloat(contract.assigned_budget_hours_per_week).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(contract.spent_hours_per_week).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(contract.estimated_percent_complete).toFixed(0)}%</TableCell>
                  <TableCell align="right">{parseFloat(contract.remaining_budget_hours).toFixed(1)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {contract.is_over_budget && <StatusBadge type="over_budget" />}
                      {contract.is_overassigned && <StatusBadge type="overassigned" />}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
              {contracts.length === 0 && (
                <TableRow>
                    <TableCell colSpan={14} align="center">
                    No contracts found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={dialogOpen} onClose={handleCloseCreateDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Create Contract</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Contract Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              error={!!formErrors.name}
              helperText={formErrors.name}
              fullWidth
            />

            <TextField
              label="Client Name"
              value={formData.client_name}
              onChange={(e) => setFormData({ ...formData, client_name: e.target.value })}
              required
              error={!!formErrors.client_name}
              helperText={formErrors.client_name}
              fullWidth
            />

            <TextField
              label="Tags"
              value={formData.tags}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              helperText="Comma-separated (example: urgent, internal)"
              fullWidth
            />

            <TextField
              label="Contract Number"
              value={formData.contract_number}
              onChange={(e) => setFormData({ ...formData, contract_number: e.target.value })}
              fullWidth
            />

            <TextField
              label="Contract Type"
              select
              value={formData.contract_type}
              onChange={(e) =>
                setFormData({ ...formData, contract_type: e.target.value as Contract['contract_type'] })
              }
              required
              fullWidth
            >
              {CONTRACT_TYPE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Budget Hours"
              type="number"
              value={formData.budget_hours}
              onChange={(e) => setFormData({ ...formData, budget_hours: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />

            <TextField
              label="Contract Amount (USD)"
              type="number"
              value={formData.contract_amount}
              onChange={(e) => setFormData({ ...formData, contract_amount: e.target.value })}
              fullWidth
              inputProps={{ min: 0, step: 0.01 }}
            />

            <TextField
              label="Status"
              select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as Contract['status'] })}
              required
              fullWidth
            >
              {CONTRACT_STATUS_OPTIONS.map((contractStatusOption) => (
                <MenuItem key={contractStatusOption.value} value={contractStatusOption.value}>
                  {contractStatusOption.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Start Date"
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              required
              error={!!formErrors.start_date}
              helperText={formErrors.start_date}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              label="End Date"
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              required
              error={!!formErrors.end_date}
              helperText={formErrors.end_date}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCreateDialog} disabled={saving}>Cancel</Button>
          <Button
            onClick={handleCreateContract}
            variant="contained"
            disabled={
              saving ||
              !formData.name.trim() ||
              !formData.client_name.trim()
            }
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

