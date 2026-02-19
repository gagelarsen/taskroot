import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { contractsApi, deliverablesApi, initiativesApi } from '../api/client';
import type { Contract, Deliverable, Initiative } from '../types/api';

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function daysSince(dateValue: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const date = new Date(dateValue);
  date.setHours(0, 0, 0, 0);
  return Math.floor((today.getTime() - date.getTime()) / MS_PER_DAY);
}

function hasMissingCurrentUpdate(deliverable: Deliverable): boolean {
  if (!deliverable.latest_status_update) {
    return true;
  }
  return daysSince(deliverable.latest_status_update.period_end) > 7;
}

export function MissingUpdatesPage() {
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [initiatives, setInitiatives] = useState<Initiative[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [deliverableData, initiativeData, contractData] = (await Promise.all([
        deliverablesApi.list({ order_by: 'id', order_dir: 'desc' }),
        initiativesApi.list({ stale: true, order_by: 'id', order_dir: 'desc' }),
        contractsApi.list({ order_by: 'id', order_dir: 'desc' }),
      ])) as [Deliverable[], Initiative[], Contract[]];

      setDeliverables(deliverableData.filter((deliverable) => hasMissingCurrentUpdate(deliverable)));
      setInitiatives(initiativeData.filter((initiative) => initiative.is_update_stale));
      setContracts(contractData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load missing updates');
      } else {
        setError('Failed to load missing updates');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const contractNameById = useMemo(() => {
    return contracts.reduce<Record<number, string>>((current, contract) => {
      current[contract.id] = contract.name || `Contract #${contract.id}`;
      return current;
    }, {});
  }, [contracts]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Missing Updates
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Shows only deliverables and initiatives that do not have a current weekly update.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Deliverables Missing Current Update
        </Typography>
        {deliverables.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No deliverables are missing updates.
          </Typography>
        ) : (
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Contract</TableCell>
                  <TableCell>Deliverable</TableCell>
                  <TableCell align="right">% Complete</TableCell>
                  <TableCell>Latest Update</TableCell>
                  <TableCell>Issue</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deliverables.map((deliverable) => {
                  const latest = deliverable.latest_status_update;
                  const staleDays = latest ? daysSince(latest.period_end) : null;

                  return (
                    <TableRow
                      key={deliverable.id}
                      hover
                      onClick={() => navigate(`/deliverables/${deliverable.id}`)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>{contractNameById[deliverable.contract] || `Contract #${deliverable.contract}`}</TableCell>
                      <TableCell>{deliverable.name || `Deliverable #${deliverable.id}`}</TableCell>
                      <TableCell align="right">{Number(deliverable.estimated_percent_complete || '0').toFixed(0)}%</TableCell>
                      <TableCell>
                        {latest ? new Date(latest.period_end).toLocaleDateString() : 'No update'}
                      </TableCell>
                      <TableCell>
                        {latest ? (
                          <Chip size="small" color="warning" variant="outlined" label={`Stale (${staleDays}d)`} />
                        ) : (
                          <Chip size="small" color="warning" variant="outlined" label="No update" />
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      <Box>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Initiatives Missing Current Update
        </Typography>
        {initiatives.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No initiatives are missing updates.
          </Typography>
        ) : (
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Initiative</TableCell>
                  <TableCell>Owner</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">% Complete</TableCell>
                  <TableCell>Latest Update</TableCell>
                  <TableCell>Issue</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {initiatives.map((initiative) => {
                  const latest = initiative.latest_update;
                  const staleDays = latest ? daysSince(latest.period_end) : null;

                  return (
                    <TableRow key={initiative.id}>
                      <TableCell>{initiative.name}</TableCell>
                      <TableCell>{initiative.owner_name || 'Unassigned'}</TableCell>
                      <TableCell>{initiative.status}</TableCell>
                      <TableCell align="right">{Number(initiative.current_percent_complete || '0').toFixed(0)}%</TableCell>
                      <TableCell>
                        {latest ? new Date(latest.period_end).toLocaleDateString() : 'No update'}
                      </TableCell>
                      <TableCell>
                        {latest ? (
                          <Chip size="small" color="warning" variant="outlined" label={`Stale (${staleDays}d)`} />
                        ) : (
                          <Chip size="small" color="warning" variant="outlined" label="No update" />
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Box>
  );
}
