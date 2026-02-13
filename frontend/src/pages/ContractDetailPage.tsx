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
  Tabs,
  Tab,
} from '@mui/material';
import { ArrowBack, Add, Edit } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { contractsApi, deliverablesApi } from '../api/client';
import type { Contract, Deliverable } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { TargetDateBadge } from '../components/TargetDateBadge';
import { BurnDownChart } from '../components/BurnDownChart';
import { getContractTypeShortLabel } from '../utils/contractTypes';
import { AxiosError } from 'axios';
import { formatContractStatusLabel, getContractStatusChipColor } from '../utils/contractStatus';
import { formatDeliverableStatusLabel, getDeliverableStatusChipColor } from '../utils/statusUpdates';
import {
  formatDeliverableLifecycleStatusLabel,
  getDeliverableLifecycleStatusChipColor,
} from '../utils/deliverableStatus';

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<Contract | null>(null);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [activeTab, setActiveTab] = useState(0);
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/contracts')}>
          Back to Contracts
        </Button>
        <Button
          variant="outlined"
          startIcon={<Edit />}
          onClick={() => navigate(`/contracts/${contract.id}/edit`)}
        >
          Edit Contract
        </Button>
      </Box>

      <Typography variant="h4" gutterBottom>
        {contract.name || `Contract #${contract.id}`}
      </Typography>
      {contract.client_name && (
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Client: {contract.client_name}
        </Typography>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, value) => setActiveTab(value)}>
          <Tab label="Basic Info" />
          <Tab label="Burn Down" />
          <Tab label="Staff Assignments" />
          <Tab label="Deliverables" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Assigned Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.assigned_budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Spent Hours
            </Typography>
            <Typography variant="h5">{parseFloat(contract.spent_hours).toFixed(1)}</Typography>
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
                    <Chip
                      label={formatContractStatusLabel(contract.status)}
                      size="small"
                      color={getContractStatusChipColor(contract.status)}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Contract Type
                  </Typography>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip
                      size="small"
                      variant="outlined"
                      sx={{ borderRadius: 999 }}
                      label={getContractTypeShortLabel(contract.contract_type)}
                    />
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
                  Assigned Budget Hours/Week
                </Typography>
                <Typography>{parseFloat(contract.assigned_budget_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Spent Hours/Week
                </Typography>
                <Typography>{parseFloat(contract.spent_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Estimated Burn Rate
                </Typography>
                <Typography>{parseFloat(contract.estimated_burn_rate).toFixed(1)} h/week</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Actual Burn Rate (last 4 weeks)
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography>{parseFloat(contract.actual_burn_rate).toFixed(1)} h/week</Typography>
                  {(() => {
                    const estimated = parseFloat(contract.estimated_burn_rate);
                    const actual = parseFloat(contract.actual_burn_rate);
                    const variance = actual - estimated;
                    const percentDiff = estimated > 0 ? (variance / estimated) * 100 : 0;

                    if (Math.abs(percentDiff) < 5) {
                      return <Chip label="On Pace" size="small" color="success" />;
                    } else if (variance > 0) {
                      return <Chip label={`+${variance.toFixed(1)} h/week`} size="small" color="warning" />;
                    } else if (variance < 0) {
                      return <Chip label={`${variance.toFixed(1)} h/week`} size="small" color="info" />;
                    }
                    return null;
                  })()}
                </Box>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  % Complete
                </Typography>
                <Typography>{parseFloat(contract.estimated_percent_complete).toFixed(1)}%</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Health Flags
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {contract.is_over_budget && <StatusBadge type="over_budget" />}
                  {contract.is_overassigned && <StatusBadge type="overassigned" />}
                  {!contract.is_over_budget && !contract.is_overassigned && (
                    <StatusBadge type="on_track" />
                  )}
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Stack>
        </>
      )}

      {activeTab === 1 && (
        <Box sx={{ mb: 3 }}>
          <BurnDownChart contract={contract} />
        </Box>
      )}

      {activeTab === 2 && (
        <>
      <Typography variant="h5" gutterBottom sx={{ mt: 2 }}>
        Staff Assignments
      </Typography>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Staff Member</TableCell>
              <TableCell align="right">Total Budget Hours</TableCell>
              <TableCell align="right">Deliverables</TableCell>
              <TableCell>Lead Role</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(() => {
              // Aggregate staff across all deliverables
              const staffMap = new Map<number, {
                id: number;
                name: string;
                totalBudgetHours: number;
                deliverableCount: number;
                isLeadAnywhere: boolean;
              }>();

              deliverables.forEach(deliverable => {
                deliverable.assignments?.forEach(assignment => {
                  const existing = staffMap.get(assignment.staff);
                  if (existing) {
                    existing.totalBudgetHours += parseFloat(assignment.budget_hours);
                    existing.deliverableCount += 1;
                    existing.isLeadAnywhere = existing.isLeadAnywhere || assignment.is_lead;
                  } else {
                    staffMap.set(assignment.staff, {
                      id: assignment.staff,
                      name: assignment.staff_name,
                      totalBudgetHours: parseFloat(assignment.budget_hours),
                      deliverableCount: 1,
                      isLeadAnywhere: assignment.is_lead,
                    });
                  }
                });
              });

              const staffList = Array.from(staffMap.values()).sort((a, b) => 
                a.name.localeCompare(b.name)
              );

              if (staffList.length === 0) {
                return (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography color="text.secondary">No staff assigned</Typography>
                    </TableCell>
                  </TableRow>
                );
              }

              return staffList.map(staff => (
                <TableRow key={staff.id}>
                  <TableCell>{staff.name}</TableCell>
                  <TableCell align="right">{staff.totalBudgetHours.toFixed(1)}</TableCell>
                  <TableCell align="right">{staff.deliverableCount}</TableCell>
                  <TableCell>
                    {staff.isLeadAnywhere ? (
                      <Chip label="Lead" color="primary" size="small" />
                    ) : (
                      <Chip label="Member" size="small" />
                    )}
                  </TableCell>
                </TableRow>
              ));
            })()}
          </TableBody>
        </Table>
      </TableContainer>
        </>
      )}

      {activeTab === 3 && (
        <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, mb: 2 }}>
        <Typography variant="h5">Deliverables</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate(`/deliverables/new?contract=${contract.id}`)}
        >
          Create Deliverable
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Target Date</TableCell>
              <TableCell align="right">Budget</TableCell>
              <TableCell align="right">Assigned Budget</TableCell>
              <TableCell align="right">Spent</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="right">% Complete</TableCell>
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
                  <Chip
                    label={formatDeliverableLifecycleStatusLabel(deliverable.status)}
                    size="small"
                    color={getDeliverableLifecycleStatusChipColor(deliverable.status)}
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>{deliverable.target_completion_date || 'Not set'}</span>
                    <TargetDateBadge targetDate={deliverable.target_completion_date} />
                  </Box>
                </TableCell>
                <TableCell align="right">{parseFloat(deliverable.budget_hours).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.assigned_budget_hours).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.spent_hours).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.variance_hours).toFixed(1)}</TableCell>
                <TableCell align="right">{parseFloat(deliverable.estimated_percent_complete).toFixed(0)}%</TableCell>
                <TableCell>
                  {deliverable.latest_status_update ? (
                    <Chip
                      label={formatDeliverableStatusLabel(deliverable.latest_status_update.status)}
                      size="small"
                      color={getDeliverableStatusChipColor(deliverable.latest_status_update.status)}
                    />
                  ) : (
                    'N/A'
                  )}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {deliverable.is_over_budget && <StatusBadge type="over_budget" />}
                    {deliverable.is_missing_lead && <StatusBadge type="missing_lead" />}
                    {deliverable.is_missing_budget && <StatusBadge type="missing_budget" />}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
            {deliverables.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  No deliverables found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
        </>
      )}
    </Box>
  );
}

