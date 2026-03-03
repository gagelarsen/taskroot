import { useState, useEffect, useCallback } from 'react';
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
  TextField,
  MenuItem,
  Stack,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { deliverablesApi, contractsApi } from '../api/client';
import type { Deliverable, DeliverableFilters, Contract } from '../types/api';
import { TargetDateBadge } from '../components/TargetDateBadge';
import {
  formatDeliverableLifecycleStatusLabel,
  getDeliverableLifecycleStatusChipColor,
} from '../utils/deliverableStatus';
import { getApiErrorMessage } from '../utils/apiErrors';

export function DeliverableListPage() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<DeliverableFilters>({
    order_by: 'id',
    order_dir: 'desc',
  });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showComplete, setShowComplete] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    contract: 0,
    budget_hours: '0',
    status: 'planned',
    charge_code: '',
    target_completion_date: '',
  });
  const navigate = useNavigate();

  const visibleDeliverables = showComplete
    ? deliverables
    : deliverables.filter((deliverable) => parseFloat(deliverable.estimated_percent_complete) < 100);

  // Load contracts for the filter dropdown
  useEffect(() => {
    const loadContracts = async () => {
      try {
        const data = await contractsApi.list({ order_by: 'start_date', order_dir: 'desc' });
        setContracts(data);
      } catch (err) {
        console.error('Failed to load contracts for filter:', err);
      }
    };
    loadContracts();
  }, []);

  const loadDeliverables = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await deliverablesApi.list(filters);
      setDeliverables(data);
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load deliverables'));
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDeliverables();
  }, [loadDeliverables]);

  const handleOpenCreateDialog = () => {
    setError('');
    setFormData({
      name: '',
      contract: contracts[0]?.id || 0,
      budget_hours: '0',
      status: 'planned',
      charge_code: '',
      target_completion_date: '',
    });
    setDialogOpen(true);
  };

  const handleCloseCreateDialog = () => {
    if (saving) return;
    setDialogOpen(false);
  };

  const handleCreateDeliverable = async () => {
    setSaving(true);
    setError('');
    try {
      await deliverablesApi.create({
        name: formData.name,
        contract: formData.contract,
        budget_hours: formData.budget_hours,
        status: formData.status,
        charge_code: formData.charge_code,
        target_completion_date: formData.target_completion_date || null,
      });
      setDialogOpen(false);
      await loadDeliverables();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save deliverable'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Deliverables</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={handleOpenCreateDialog}>
          Create Deliverable
        </Button>
      </Box>

      <Stack direction="row" spacing={2} sx={{ mb: 3 }} flexWrap="wrap">
        <TextField
          label="Search"
          variant="outlined"
          size="small"
          value={filters.q || ''}
          onChange={(e) => setFilters({ ...filters, q: e.target.value })}
          sx={{ minWidth: 250 }}
        />
        <TextField
          select
          label="Contract"
          variant="outlined"
          size="small"
          value={filters.contract_id || ''}
          onChange={(e) => setFilters({ ...filters, contract_id: e.target.value ? parseInt(e.target.value) : undefined })}
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">All Contracts</MenuItem>
          {contracts.map((contract) => (
            <MenuItem key={contract.id} value={contract.id}>
              {contract.name || `Contract #${contract.id}`} ({contract.client_name || 'No client'})
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Status"
          variant="outlined"
          size="small"
          value={filters.status || ''}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="">All</MenuItem>
          <MenuItem value="planned">Planned</MenuItem>
          <MenuItem value="in_progress">In Progress</MenuItem>
          <MenuItem value="complete">Complete</MenuItem>
          <MenuItem value="blocked">Blocked</MenuItem>
        </TextField>
        <TextField
          select
          label="Sort By"
          variant="outlined"
          size="small"
          value={filters.order_by || 'id'}
          onChange={(e) => setFilters({ ...filters, order_by: e.target.value })}
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="id">ID</MenuItem>
          <MenuItem value="name">Name</MenuItem>
          <MenuItem value="status">Status</MenuItem>
        </TextField>
        <TextField
          select
          label="Order"
          variant="outlined"
          size="small"
          value={filters.order_dir || 'desc'}
          onChange={(e) => setFilters({ ...filters, order_dir: e.target.value as 'asc' | 'desc' })}
          sx={{ minWidth: 120 }}
        >
          <MenuItem value="asc">Ascending</MenuItem>
          <MenuItem value="desc">Descending</MenuItem>
        </TextField>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={showComplete}
              onChange={(event) => setShowComplete(event.target.checked)}
            />
          }
          label="Show complete"
        />
      </Stack>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Contract</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Target Date</TableCell>
              <TableCell align="right">Budget</TableCell>
              <TableCell align="right">Assigned Budget</TableCell>
              <TableCell align="right">Spent</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="right">% Complete</TableCell>
              <TableCell>Flags</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleDeliverables.map((deliverable) => {
              const isComplete = parseFloat(deliverable.estimated_percent_complete) >= 100;
              return (
              <TableRow
                key={deliverable.id}
                hover
                onClick={() => navigate(`/deliverables/${deliverable.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{deliverable.name}</TableCell>
                <TableCell>{`Contract #${deliverable.contract}`}</TableCell>
                <TableCell>
                  <Chip
                    label={formatDeliverableLifecycleStatusLabel(deliverable.status)}
                    size="small"
                    color={getDeliverableLifecycleStatusChipColor(deliverable.status)}
                  />
                </TableCell>
                <TableCell>
                  {deliverable.target_completion_date ? (
                    <TargetDateBadge targetDate={deliverable.target_completion_date} />
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell align="right">
                  {deliverable.budget_hours ? parseFloat(deliverable.budget_hours).toFixed(1) : '-'}
                </TableCell>
                <TableCell align="right">
                  {parseFloat(deliverable.assigned_budget_hours).toFixed(1)}
                </TableCell>
                <TableCell align="right">{parseFloat(deliverable.spent_hours).toFixed(1)}</TableCell>
                <TableCell align="right">
                  <Box
                    component="span"
                    sx={{
                      color: parseFloat(deliverable.variance_hours) > 0 ? 'error.main' : 'success.main',
                      fontWeight: 'medium',
                    }}
                  >
                    {parseFloat(deliverable.variance_hours).toFixed(1)}
                  </Box>
                </TableCell>
                <TableCell align="right">{parseFloat(deliverable.estimated_percent_complete).toFixed(0)}%</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5}>
                    {deliverable.is_overassigned && <Chip label="Overassigned" size="small" color="warning" />}
                    {deliverable.is_over_budget && <Chip label="Over Budget" size="small" color="error" />}
                    {!isComplete && deliverable.is_missing_budget && <Chip label="Missing Budget" size="small" color="info" />}
                    {deliverable.is_missing_lead && <Chip label="Missing Lead" size="small" color="info" />}
                    {(deliverable.assignments?.length || 0) === 0 && <Chip label="Unassigned" size="small" color="info" variant="outlined" />}
                  </Stack>
                </TableCell>
              </TableRow>
              );
            })}
            {visibleDeliverables.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  No deliverables found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={handleCloseCreateDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Create Deliverable</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Contract"
              select
              value={formData.contract || ''}
              onChange={(e) => setFormData({ ...formData, contract: parseInt(e.target.value) })}
              required
              fullWidth
            >
              {contracts.map((contract) => (
                <MenuItem key={contract.id} value={contract.id}>
                  {contract.name || `Contract #${contract.id}`} ({contract.client_name || 'No client'})
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
              label="Status"
              select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              required
              fullWidth
            >
              <MenuItem value="planned">Planned</MenuItem>
              <MenuItem value="in_progress">In Progress</MenuItem>
              <MenuItem value="complete">Complete</MenuItem>
              <MenuItem value="blocked">Blocked</MenuItem>
            </TextField>

            <TextField
              label="Charge Code"
              value={formData.charge_code}
              onChange={(e) => setFormData({ ...formData, charge_code: e.target.value })}
              fullWidth
            />

            <TextField
              label="Target Completion Date"
              type="date"
              value={formData.target_completion_date}
              onChange={(e) => setFormData({ ...formData, target_completion_date: e.target.value })}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseCreateDialog} disabled={saving}>Cancel</Button>
          <Button
            onClick={handleCreateDeliverable}
            variant="contained"
            disabled={saving || !formData.name.trim() || !formData.contract}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}


