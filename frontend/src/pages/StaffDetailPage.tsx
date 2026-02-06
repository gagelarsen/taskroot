import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  Button,
  Grid,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { Edit, ArrowBack } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { staffApi, assignmentsApi } from '../api/client';
import type { Staff, DeliverableAssignment } from '../types/api';
import { AxiosError } from 'axios';

export function StaffDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [staff, setStaff] = useState<Staff | null>(null);
  const [assignments, setAssignments] = useState<DeliverableAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;

      setLoading(true);
      setError('');
      try {
        const [staffData, assignmentsData] = await Promise.all([
          staffApi.get(parseInt(id)),
          assignmentsApi.list({ staff_id: parseInt(id) }),
        ]);
        setStaff(staffData);
        setAssignments(assignmentsData);
      } catch (err) {
        if (err instanceof AxiosError) {
          setError(err.response?.data?.detail || 'Failed to load staff details');
        } else {
          setError('Failed to load staff details');
        }
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'default';
      default:
        return 'default';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'error';
      case 'manager':
        return 'warning';
      case 'staff':
        return 'info';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !staff) {
    return (
      <Box>
        <Alert severity="error">{error || 'Staff member not found'}</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/staff')} sx={{ mt: 2 }}>
          Back to Staff List
        </Button>
      </Box>
    );
  }

  const totalAssignedHours = assignments.reduce(
    (sum, assignment) => sum + parseFloat(assignment.budget_hours),
    0
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/staff')}>
            Back
          </Button>
          <Typography variant="h4">
            {staff.first_name} {staff.last_name}
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Edit />}
          onClick={() => navigate(`/staff/${id}/edit`)}
        >
          Edit Staff
        </Button>
      </Box>

      {/* Staff Details */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Staff Information
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Email
            </Typography>
            <Typography variant="body1">{staff.email}</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Role
            </Typography>
            <Chip
              label={staff.role.charAt(0).toUpperCase() + staff.role.slice(1)}
              color={getRoleColor(staff.role) as any}
              size="small"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Status
            </Typography>
            <Chip
              label={staff.status.charAt(0).toUpperCase() + staff.status.slice(1)}
              color={getStatusColor(staff.status) as any}
              size="small"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Expected Hours Per Week
            </Typography>
            <Typography variant="body1">{staff.expected_hours_per_week}</Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Summary Metrics */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Summary
        </Typography>
        <Divider sx={{ mb: 2 }} />
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Total Assigned Hours Per Week
            </Typography>
            <Typography variant="h5">{totalAssignedHours.toFixed(2)}</Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              Active Assignments
            </Typography>
            <Typography variant="h5">{assignments.length}</Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Assignments */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Deliverable Assignments
        </Typography>
        <Divider sx={{ mb: 2 }} />
        {assignments.length === 0 ? (
          <Typography color="text.secondary">No assignments</Typography>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Deliverable</TableCell>
                  <TableCell align="right">Budget Hours</TableCell>
                  <TableCell>Lead</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {assignments.map((assignment) => (
                  <TableRow key={assignment.id}>
                    <TableCell>Deliverable #{assignment.deliverable}</TableCell>
                    <TableCell align="right">{assignment.budget_hours}</TableCell>
                    <TableCell>
                      {assignment.is_lead ? (
                        <Chip label="Lead" color="primary" size="small" />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}

