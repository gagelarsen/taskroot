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
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { contractsApi } from '../api/client';
import type { Contract, ContractFilters } from '../types/api';
import { FilterBar } from '../components/FilterBar';
import { StatusBadge } from '../components/StatusBadge';
import { AxiosError } from 'axios';

export function ContractsListPage() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<ContractFilters>({
    order_by: 'start_date',
    order_dir: 'desc',
  });
  const navigate = useNavigate();

  const loadContracts = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await contractsApi.list(filters);
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
  }, [filters]);

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
    { value: 'budget_hours_total', label: 'Budget' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Contracts
      </Typography>

      <FilterBar
        searchValue={filters.q || ''}
        onSearchChange={(q) => setFilters({ ...filters, q })}
        orderBy={filters.order_by || ''}
        orderDir={filters.order_dir}
        onOrderByChange={(order_by) => setFilters({ ...filters, order_by })}
        onOrderDirChange={(order_dir) => setFilters({ ...filters, order_dir })}
        orderByOptions={orderByOptions}
      />

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
                <TableCell>ID</TableCell>
                <TableCell>Start Date</TableCell>
                <TableCell>End Date</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Budget Hours</TableCell>
                <TableCell align="right">Expected/Week</TableCell>
                <TableCell align="right">Actual/Week</TableCell>
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
                  <TableCell>{contract.id}</TableCell>
                  <TableCell>{contract.start_date}</TableCell>
                  <TableCell>{contract.end_date}</TableCell>
                  <TableCell>
                    <Chip label={contract.status} size="small" />
                  </TableCell>
                  <TableCell align="right">{parseFloat(contract.budget_hours_total).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(contract.expected_hours_per_week).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(contract.actual_hours_per_week).toFixed(1)}</TableCell>
                  <TableCell align="right">{parseFloat(contract.remaining_budget_hours).toFixed(1)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {contract.is_over_budget && <StatusBadge type="over_budget" />}
                      {contract.is_over_expected && <StatusBadge type="over_expected" />}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
              {contracts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    No contracts found
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

