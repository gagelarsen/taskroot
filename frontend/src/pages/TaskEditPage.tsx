import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  CircularProgress,
  Alert,
  MenuItem,
  Stack,
} from '@mui/material';
import { ArrowBack, Save } from '@mui/icons-material';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { tasksApi, staffApi, deliverablesApi } from '../api/client';
import type { Task, Staff, Deliverable } from '../types/api';
import { TASK_STATUS_OPTIONS } from '../utils/taskStatus';
import { sortStaffByName } from '../utils/staffSort';
import { getApiErrorMessage } from '../utils/apiErrors';

export function TaskEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isNew = id === 'new';

  // Get deliverable from query params if creating new task
  const deliverableParam = searchParams.get('deliverable');

  const [task, setTask] = useState<Partial<Task>>({
    title: '',
    budget_hours: '0',
    percent_complete: '0',
    status: 'todo',
    assignee: null,
    deliverable: deliverableParam ? parseInt(deliverableParam) : 0,
  });
  const [staff, setStaff] = useState<Staff[]>([]);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [staffData, deliverablesData] = await Promise.all([
          staffApi.list(),
          deliverablesApi.list(),
        ]);
        setStaff(sortStaffByName(staffData));
        setDeliverables(deliverablesData);

        if (!isNew && id) {
          const taskData = await tasksApi.get(parseInt(id));
          setTask(taskData);
        }
      } catch (err) {
        setError(getApiErrorMessage(err, 'Failed to load data'));
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, isNew]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      const payload = {
        title: task.title,
        budget_hours: task.budget_hours,
        percent_complete: task.percent_complete,
        status: task.status,
        deliverable: task.deliverable,
        assignee: task.assignee || null,
      };

      if (isNew) {
        await tasksApi.create(payload);
      } else if (id) {
        await tasksApi.update(parseInt(id), payload);
      }

      // Navigate back to the deliverable detail page
      if (task.deliverable) {
        navigate(`/deliverables/${task.deliverable}`);
      } else {
        navigate(-1);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save task'));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate(-1);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Button startIcon={<ArrowBack />} onClick={handleCancel} sx={{ mb: 2 }}>
        Back
      </Button>

      <Typography variant="h4" gutterBottom>
        {isNew ? 'Create Task' : 'Edit Task'}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            <TextField
              label="Title"
              value={task.title || ''}
              onChange={(e) => setTask({ ...task, title: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Deliverable"
              select
              value={task.deliverable || ''}
              onChange={(e) => setTask({ ...task, deliverable: parseInt(e.target.value) })}
              required
              fullWidth
            >
              {deliverables.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Budget Hours"
              type="number"
              value={task.budget_hours || '0'}
              onChange={(e) => setTask({ ...task, budget_hours: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />

            <TextField
              label="% Complete"
              type="number"
              value={task.percent_complete || '0'}
              onChange={(e) => setTask({ ...task, percent_complete: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, max: 100, step: 1 }}
            />

            <TextField
              label="Status"
              select
              value={task.status || 'todo'}
              onChange={(e) => setTask({ ...task, status: e.target.value as Task['status'] })}
              required
              fullWidth
            >
              {TASK_STATUS_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Assignee"
              select
              value={task.assignee || ''}
              onChange={(e) => setTask({ ...task, assignee: e.target.value ? parseInt(e.target.value) : null })}
              fullWidth
            >
              <MenuItem value="">Unassigned</MenuItem>
              {staff.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.first_name} {s.last_name}
                </MenuItem>
              ))}
            </TextField>

            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <Button onClick={handleCancel} disabled={saving}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                startIcon={<Save />}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </Stack>
          </Stack>
        </form>
      </Paper>
    </Box>
  );
}

