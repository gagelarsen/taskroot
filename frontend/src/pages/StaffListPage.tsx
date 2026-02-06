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
  Button,
  TextField,
  MenuItem,
  LinearProgress,
  Tooltip,
} from '@mui/material';
import { Add, Warning, CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { staffApi, assignmentsApi, deliverablesApi } from '../api/client';
import type { Staff, DeliverableAssignment, Deliverable } from '../types/api';
import { AxiosError } from 'axios';

interface StaffFilters {
  q?: string;
  status?: string;
  role?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

interface StaffWithMetrics extends Staff {
  assignedHoursPerWeek: number;
  utilizationPercent: number;
  isOverallocated: boolean;
  isUnderallocated: boolean;
}

export function StaffListPage() {
  const [staff, setStaff] = useState<StaffWithMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<StaffFilters>({
    order_by: 'last_name',
    order_dir: 'asc',
  });
  const navigate = useNavigate();

  const loadStaff = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [staffData, assignmentsData, deliverablesData] = await Promise.all([
        staffApi.list(filters),
        assignmentsApi.list({}),
        deliverablesApi.list({}),
      ]);

      // Create a map of deliverable ID to deliverable for quick lookup
      const deliverableMap = new Map<number, Deliverable>();
      deliverablesData.forEach((d: Deliverable) => {
        deliverableMap.set(d.id, d);
      });

      // Calculate metrics for each staff member
      const staffWithMetrics: StaffWithMetrics[] = staffData.map((staffMember: Staff) => {
        // Get all assignments for this staff member
        const staffAssignments = assignmentsData.filter(
          (a: DeliverableAssignment) => a.staff === staffMember.id
        );

        // Filter to only active deliverables (not completed)
        const activeAssignments = staffAssignments.filter((a: DeliverableAssignment) => {
          const deliverable = deliverableMap.get(a.deliverable);
          return deliverable && deliverable.status !== 'completed';
        });

        // Calculate average hours per week
        let totalWeightedHours = 0;

        activeAssignments.forEach((assignment: DeliverableAssignment) => {
          const deliverable = deliverableMap.get(assignment.deliverable);
          if (deliverable && deliverable.planned_weeks && deliverable.planned_weeks > 0) {
            const assignmentHours = parseFloat(assignment.budget_hours);
            const hoursPerWeek = assignmentHours / deliverable.planned_weeks;
            totalWeightedHours += hoursPerWeek;
          }
        });

        const assignedHoursPerWeek = totalWeightedHours;
        const expectedHoursPerWeek = typeof staffMember.expected_hours_per_week === 'string'
          ? parseFloat(staffMember.expected_hours_per_week)
          : staffMember.expected_hours_per_week;
        const utilizationPercent = expectedHoursPerWeek > 0
          ? (assignedHoursPerWeek / expectedHoursPerWeek) * 100
          : 0;

        return {
          ...staffMember,
          assignedHoursPerWeek,
          utilizationPercent,
          isOverallocated: assignedHoursPerWeek > expectedHoursPerWeek,
          isUnderallocated: assignedHoursPerWeek < expectedHoursPerWeek * 0.7,
        };
      });

      setStaff(staffWithMetrics);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load staff');
      } else {
        setError('Failed to load staff');
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadStaff();
  }, [loadStaff]);

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

  const getHealthIcon = (member: StaffWithMetrics) => {
    if (member.isOverallocated) {
      return <ErrorIcon color="error" fontSize="small" />;
    } else if (member.isUnderallocated) {
      return <Warning color="warning" fontSize="small" />;
    } else {
      return <CheckCircle color="success" fontSize="small" />;
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Staff</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => navigate('/staff/new')}
        >
          Create Staff
        </Button>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            label="Search"
            placeholder="Search by name or email..."
            value={filters.q || ''}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            size="small"
            sx={{ minWidth: 250 }}
          />
          <TextField
            select
            label="Status"
            value={filters.status || ''}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
          </TextField>
          <TextField
            select
            label="Role"
            value={filters.role || ''}
            onChange={(e) => setFilters({ ...filters, role: e.target.value })}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
            <MenuItem value="manager">Manager</MenuItem>
            <MenuItem value="staff">Staff</MenuItem>
          </TextField>
        </Box>
      </Paper>

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
                <TableCell width={40}></TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Expected hrs/wk</TableCell>
                <TableCell align="right">Assigned hrs/wk</TableCell>
                <TableCell align="center" width={200}>Utilization</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {staff.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    No staff members found
                  </TableCell>
                </TableRow>
              ) : (
                staff.map((member) => (
                  <TableRow
                    key={member.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/staff/${member.id}`)}
                  >
                    <TableCell>
                      <Tooltip
                        title={
                          member.isOverallocated
                            ? 'Over-allocated'
                            : member.isUnderallocated
                            ? 'Under-utilized'
                            : 'Healthy'
                        }
                      >
                        {getHealthIcon(member)}
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      {member.first_name} {member.last_name}
                    </TableCell>
                    <TableCell>{member.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                        color={getRoleColor(member.role) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={member.status.charAt(0).toUpperCase() + member.status.slice(1)}
                        color={getStatusColor(member.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">{parseFloat(member.expected_hours_per_week).toFixed(1)}</TableCell>
                    <TableCell align="right">{member.assignedHoursPerWeek.toFixed(1)}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Box sx={{ flex: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={Math.min(member.utilizationPercent, 100)}
                            color={
                              member.isOverallocated
                                ? 'error'
                                : member.isUnderallocated
                                ? 'warning'
                                : 'success'
                            }
                            sx={{ height: 6, borderRadius: 1 }}
                          />
                        </Box>
                        <Typography variant="body2" sx={{ minWidth: 45 }}>
                          {member.utilizationPercent.toFixed(0)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/staff/${member.id}/edit`);
                        }}
                      >
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}

