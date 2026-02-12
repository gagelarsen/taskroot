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
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { deliverablesApi, contractsApi } from '../api/client';
import type { Deliverable, DeliverableFilters, Contract } from '../types/api';
import { TargetDateBadge } from '../components/TargetDateBadge';
import { AxiosError } from 'axios';

export function DeliverableListPage() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<DeliverableFilters>({
    order_by: 'id',
    order_dir: 'desc',
  });
  const navigate = useNavigate();

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
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load deliverables');
      } else {
        setError('Failed to load deliverables');
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadDeliverables();
  }, [loadDeliverables]);

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
      <Typography variant="h4" gutterBottom>
        Deliverables
      </Typography>

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
              <TableCell>Flags</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deliverables.map((deliverable) => (
              <TableRow
                key={deliverable.id}
                hover
                onClick={() => navigate(`/deliverables/${deliverable.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>{deliverable.name}</TableCell>
                <TableCell>{`Contract #${deliverable.contract}`}</TableCell>
                <TableCell>
                  <Chip label={deliverable.status} size="small" />
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
                <TableCell>
                  <Stack direction="row" spacing={0.5}>
                    {deliverable.is_overassigned && <Chip label="Overassigned" size="small" color="warning" />}
                    {deliverable.is_over_budget && <Chip label="Over Budget" size="small" color="error" />}
                    {deliverable.is_missing_budget && <Chip label="Missing Budget" size="small" color="info" />}
                    {deliverable.is_missing_lead && <Chip label="Missing Lead" size="small" color="info" />}
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
            {deliverables.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  No deliverables found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}


