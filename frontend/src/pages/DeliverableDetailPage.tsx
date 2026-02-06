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
import { ArrowBack, Add, Edit } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { deliverablesApi, timeEntriesApi, statusUpdatesApi } from '../api/client';
import type { Deliverable, TimeEntry, DeliverableStatusUpdate } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { TargetDateBadge } from '../components/TargetDateBadge';
import { AxiosError } from 'axios';

export function DeliverableDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [statusUpdates, setStatusUpdates] = useState<DeliverableStatusUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const [deliverableData, timeEntriesData, statusUpdatesData] = await Promise.all([
        deliverablesApi.get(parseInt(id)),
        timeEntriesApi.list({ deliverable_id: parseInt(id) }),
        statusUpdatesApi.list({ deliverable_id: parseInt(id), order_by: 'period_end', order_dir: 'desc' }),
      ]);
      setDeliverable(deliverableData);
      setTimeEntries(timeEntriesData);
      setStatusUpdates(statusUpdatesData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load deliverable');
      } else {
        setError('Failed to load deliverable');
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

  if (error || !deliverable) {
    return <Alert severity="error">{error || 'Deliverable not found'}</Alert>;
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Button
          variant="outlined"
          startIcon={<Edit />}
          onClick={() => navigate(`/deliverables/${deliverable.id}/edit`)}
        >
          Edit Deliverable
        </Button>
      </Box>

      <Typography variant="h4" gutterBottom>
        {deliverable.name}
      </Typography>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Assigned Budget Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.assigned_budget_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Spent Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.spent_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Variance
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.variance_hours).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Status
            </Typography>
            <Box sx={{ mt: 1 }}>
              <Chip label={deliverable.status} />
            </Box>
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
                    Target Completion Date
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography>{deliverable.target_completion_date || 'Not set'}</Typography>
                    <TargetDateBadge targetDate={deliverable.target_completion_date} />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Charge Code
                  </Typography>
                  <Typography>{deliverable.charge_code || 'N/A'}</Typography>
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
                <Typography>{parseFloat(deliverable.assigned_budget_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Spent Hours/Week
                </Typography>
                <Typography>{parseFloat(deliverable.spent_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Health Flags
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {deliverable.is_over_budget && <StatusBadge type="over_budget" />}
                  {deliverable.is_missing_lead && <StatusBadge type="missing_lead" />}
                  {deliverable.is_missing_budget && <StatusBadge type="missing_budget" />}
                  {!deliverable.is_over_budget && !deliverable.is_missing_lead && !deliverable.is_missing_budget && (
                    <StatusBadge type="on_track" />
                  )}
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Stack>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Staff Assignments
      </Typography>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Staff Member</TableCell>
              <TableCell align="right">Budget Hours</TableCell>
              <TableCell>Lead</TableCell>
              <TableCell>Assigned At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deliverable.assignments && deliverable.assignments.length > 0 ? (
              deliverable.assignments.map((assignment) => (
                <TableRow key={assignment.id}>
                  <TableCell>{assignment.staff_name}</TableCell>
                  <TableCell align="right">{parseFloat(assignment.budget_hours).toFixed(1)}</TableCell>
                  <TableCell>
                    {assignment.is_lead ? (
                      <Chip label="Lead" color="primary" size="small" />
                    ) : (
                      <Chip label="Member" size="small" />
                    )}
                  </TableCell>
                  <TableCell>{new Date(assignment.created_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography color="text.secondary">No staff assigned</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 4, mb: 2 }}>
        <Typography variant="h5">Tasks</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate(`/tasks/new?deliverable=${deliverable.id}`)}
        >
          Create Task
        </Button>
      </Box>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Assignee</TableCell>
              <TableCell align="right">Budget Hours</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Updated At</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {deliverable.tasks && deliverable.tasks.length > 0 ? (
              deliverable.tasks.map((task) => (
                <TableRow key={task.id} hover>
                  <TableCell>{task.title}</TableCell>
                  <TableCell>{task.assignee_name || 'Unassigned'}</TableCell>
                  <TableCell align="right">{parseFloat(task.budget_hours).toFixed(1)}</TableCell>
                  <TableCell>
                    <Chip label={task.status} size="small" />
                  </TableCell>
                  <TableCell>{new Date(task.updated_at).toLocaleDateString()}</TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      startIcon={<Edit />}
                      onClick={() => navigate(`/tasks/${task.id}`)}
                    >
                      Edit
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">No tasks</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Status Updates
      </Typography>

      <TableContainer component={Paper} sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period End</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Summary</TableCell>
              <TableCell>Created At</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {statusUpdates.map((update) => (
              <TableRow key={update.id}>
                <TableCell>{update.period_end}</TableCell>
                <TableCell>
                  <Chip label={update.status} size="small" />
                </TableCell>
                <TableCell>{update.summary}</TableCell>
                <TableCell>{new Date(update.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
            {statusUpdates.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No status updates found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="h5" gutterBottom>
        Time Entries
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell align="right">Hours</TableCell>
              <TableCell>Notes</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {timeEntries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{entry.entry_date}</TableCell>
                <TableCell align="right">{parseFloat(entry.hours).toFixed(1)}</TableCell>
                <TableCell>{entry.notes || 'N/A'}</TableCell>
              </TableRow>
            ))}
            {timeEntries.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} align="center">
                  No time entries found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}

