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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import { assignmentsApi, deliverablesApi, staffApi } from '../api/client';
import type { DeliverableAssignment, Deliverable, Staff } from '../types/api';
import { AxiosError } from 'axios';

interface AssignmentFilters {
  deliverable_id?: number;
  staff_id?: number;
  contract_id?: number;
  lead_only?: boolean;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export function AssignmentsPage() {
  const [assignments, setAssignments] = useState<DeliverableAssignment[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState<AssignmentFilters>({
    order_by: 'id',
    order_dir: 'desc',
  });

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAssignment, setEditingAssignment] = useState<DeliverableAssignment | null>(null);
  const [formData, setFormData] = useState({
    deliverable: 0,
    staff: 0,
    budget_hours: 0,
    is_lead: false,
  });
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [assignmentsData, deliverablesData, staffData] = await Promise.all([
        assignmentsApi.list(filters),
        deliverablesApi.list({}),
        staffApi.list({}),
      ]);
      setAssignments(assignmentsData);
      setDeliverables(deliverablesData);
      setStaff(staffData);
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to load assignments');
      } else {
        setError('Failed to load assignments');
      }
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenDialog = (assignment?: DeliverableAssignment) => {
    if (assignment) {
      setEditingAssignment(assignment);
      setFormData({
        deliverable: assignment.deliverable,
        staff: assignment.staff,
        budget_hours: parseFloat(assignment.budget_hours),
        is_lead: assignment.is_lead,
      });
    } else {
      setEditingAssignment(null);
      setFormData({
        deliverable: 0,
        staff: 0,
        budget_hours: 0,
        is_lead: false,
      });
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingAssignment(null);
    setError('');
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');

    try {
      if (editingAssignment) {
        await assignmentsApi.update(editingAssignment.id, formData);
      } else {
        await assignmentsApi.create(formData);
      }
      handleCloseDialog();
      loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        const errorData = err.response?.data;
        if (typeof errorData === 'object') {
          const messages = Object.entries(errorData)
            .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
            .join('; ');
          setError(messages);
        } else {
          setError(errorData?.detail || 'Failed to save assignment');
        }
      } else {
        setError('Failed to save assignment');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this assignment?')) return;

    setError('');
    try {
      await assignmentsApi.delete(id);
      loadData();
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to delete assignment');
      } else {
        setError('Failed to delete assignment');
      }
    }
  };

  const getDeliverableName = (deliverableId: number) => {
    const deliverable = deliverables.find((d) => d.id === deliverableId);
    return deliverable ? deliverable.name : `Deliverable #${deliverableId}`;
  };

  const getStaffName = (staffId: number) => {
    const staffMember = staff.find((s) => s.id === staffId);
    return staffMember ? `${staffMember.first_name} ${staffMember.last_name}` : `Staff #${staffId}`;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Deliverable Assignments</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Create Assignment
        </Button>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            select
            label="Deliverable"
            value={filters.deliverable_id || ''}
            onChange={(e) => setFilters({ ...filters, deliverable_id: e.target.value ? parseInt(e.target.value) : undefined })}
            size="small"
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">All Deliverables</MenuItem>
            {deliverables.map((d) => (
              <MenuItem key={d.id} value={d.id}>
                {d.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Staff Member"
            value={filters.staff_id || ''}
            onChange={(e) => setFilters({ ...filters, staff_id: e.target.value ? parseInt(e.target.value) : undefined })}
            size="small"
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">All Staff</MenuItem>
            {staff.map((s) => (
              <MenuItem key={s.id} value={s.id}>
                {s.first_name} {s.last_name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Lead Only"
            value={filters.lead_only === undefined ? '' : filters.lead_only.toString()}
            onChange={(e) => setFilters({ ...filters, lead_only: e.target.value === '' ? undefined : e.target.value === 'true' })}
            size="small"
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="true">Lead Only</MenuItem>
            <MenuItem value="false">Non-Lead Only</MenuItem>
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
                <TableCell>Deliverable</TableCell>
                <TableCell>Staff Member</TableCell>
                <TableCell align="right">Budget Hours</TableCell>
                <TableCell>Lead</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {assignments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    No assignments found
                  </TableCell>
                </TableRow>
              ) : (
                assignments.map((assignment) => (
                  <TableRow key={assignment.id} hover>
                    <TableCell>{getDeliverableName(assignment.deliverable)}</TableCell>
                    <TableCell>{getStaffName(assignment.staff)}</TableCell>
                    <TableCell align="right">{assignment.budget_hours}</TableCell>
                    <TableCell>
                      {assignment.is_lead ? (
                        <Chip label="Lead" color="primary" size="small" />
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>{new Date(assignment.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(assignment)}
                        title="Edit"
                      >
                        <Edit fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(assignment.id)}
                        title="Delete"
                        color="error"
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingAssignment ? 'Edit Assignment' : 'Create Assignment'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              select
              label="Deliverable"
              required
              value={formData.deliverable}
              onChange={(e) => setFormData({ ...formData, deliverable: parseInt(e.target.value) })}
              fullWidth
              disabled={!!editingAssignment}
            >
              <MenuItem value={0} disabled>
                Select Deliverable
              </MenuItem>
              {deliverables.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Staff Member"
              required
              value={formData.staff}
              onChange={(e) => setFormData({ ...formData, staff: parseInt(e.target.value) })}
              fullWidth
              disabled={!!editingAssignment}
            >
              <MenuItem value={0} disabled>
                Select Staff Member
              </MenuItem>
              {staff.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.first_name} {s.last_name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Budget Hours"
              type="number"
              required
              value={formData.budget_hours}
              onChange={(e) => setFormData({ ...formData, budget_hours: parseFloat(e.target.value) })}
              inputProps={{ min: 0, step: 0.5 }}
              fullWidth
            />

            <TextField
              select
              label="Lead Assignment"
              required
              value={formData.is_lead.toString()}
              onChange={(e) => setFormData({ ...formData, is_lead: e.target.value === 'true' })}
              fullWidth
            >
              <MenuItem value="false">No</MenuItem>
              <MenuItem value="true">Yes (Lead)</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={saving || formData.deliverable === 0 || formData.staff === 0}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

