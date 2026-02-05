import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
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
  Stack,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { contractsApi, deliverablesApi } from '../api/client';
import type { Contract, Deliverable } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { AxiosError } from 'axios';

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<Contract | null>(null);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const [contractData, deliverablesData] = await Promise.all([
        contractsApi.get(parseInt(id)),
        deliverablesApi.list({ contract_id: parseInt(id) }),
      ]);
      setContract(contractData);
      setDeliverables(deliverablesData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load contract');
      } else {
        setError('Failed to load contract');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !contract) {
    return <Alert severity="error">{error || 'Contract not found'}</Alert>;
  }

  return (
    <Box>
      <Button startIcon={<ArrowBack />} onClick={() => navigate('/contracts')} sx={{ mb: 2 }}>
        Back to Contracts
      </Button>

      <Typography variant="h4" gutterBottom>
        {contract.name || `Contract #${contract.id}`}
      </Typography>
      {contract.client_name && (
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Client: {contract.client_name}
        </Typography>
      )}

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.budget_hours_total).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Expected Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.expected_hours_total).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Actual Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.actual_hours_total).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Remaining
            </Typography>
            <Typography variant="h5">{parseFloat(contract.remaining_budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
      </Stack>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Status
                  </Typography>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip label={contract.status} size="small" />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Start Date
                  </Typography>
                  <Typography>{contract.start_date}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    End Date
                  </Typography>
                  <Typography>{contract.end_date}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Per-Week Metrics
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Expected Hours/Week
                </Typography>
                <Typography>{parseFloat(contract.expected_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Actual Hours/Week
                </Typography>
                <Typography>{parseFloat(contract.actual_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Health Flags
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {contract.is_over_budget && <StatusBadge type="over_budget" />}
                  {contract.is_over_expected && <StatusBadge type="over_expected" />}
                  {!contract.is_over_budget && !contract.is_over_expected && (
                    <StatusBadge type="on_track" />
                  )}
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Stack>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Deliverables
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Due Date</TableCell>
              <TableCell align="right">Expected</TableCell>
              <TableCell align="right">Actual</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell>Latest Status</TableCell>
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
                <TableCell>
                  <Chip label={deliverable.status} size="small" />
                </TableCell>
                <TableCell>{deliverable.due_date || 'N/A'}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.expected_hours_total).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.actual_hours_total).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.variance_hours).toFixed(1)}</TableCell>
                <TableCell>
                  {deliverable.latest_status_update ? (
                    <Chip label={deliverable.latest_status_update.status} size="small" />
                  ) : (
                    'N/A'
                  )}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {deliverable.is_over_expected && <StatusBadge type="over_expected" />}
                    {deliverable.is_missing_lead && <StatusBadge type="missing_lead" />}
                    {deliverable.is_missing_estimate && <StatusBadge type="missing_estimate" />}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            {deliverables.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
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

