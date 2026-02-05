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
import { deliverablesApi, timeEntriesApi, statusUpdatesApi } from '../api/client';
import type { Deliverable, TimeEntry, DeliverableStatusUpdate } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
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
      <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Back
      </Button>

      <Typography variant="h4" gutterBottom>
        {deliverable.name}
      </Typography>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Expected Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.expected_hours_total).toFixed(1)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography color="text.secondary" gutterBottom>
              Actual Hours
            </Typography>
            <Typography variant="h5">{parseFloat(deliverable.actual_hours_total).toFixed(1)}</Typography>
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
                    Start Date
                  </Typography>
                  <Typography>{deliverable.start_date || 'N/A'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Due Date
                  </Typography>
                  <Typography>{deliverable.due_date || 'N/A'}</Typography>
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
                <Typography>{parseFloat(deliverable.expected_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Actual Hours/Week
                </Typography>
                <Typography>{parseFloat(deliverable.actual_hours_per_week).toFixed(1)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Health Flags
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
                  {deliverable.is_over_expected && <StatusBadge type="over_expected" />}
                  {deliverable.is_missing_lead && <StatusBadge type="missing_lead" />}
                  {deliverable.is_missing_estimate && <StatusBadge type="missing_estimate" />}
                  {!deliverable.is_over_expected && !deliverable.is_missing_lead && !deliverable.is_missing_estimate && (
                    <StatusBadge type="on_track" />
                  )}
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Stack>

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
              <TableCell>Staff ID</TableCell>
              <TableCell align="right">Hours</TableCell>
              <TableCell>Notes</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {timeEntries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{entry.entry_date}</TableCell>
                <TableCell>{entry.staff}</TableCell>
                <TableCell align="right">{parseFloat(entry.hours).toFixed(1)}</TableCell>
                <TableCell>{entry.notes || 'N/A'}</TableCell>
              </TableRow>
            ))}
            {timeEntries.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center">
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

