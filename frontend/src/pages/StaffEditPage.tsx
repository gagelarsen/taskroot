import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  MenuItem,
} from '@mui/material';
import { ArrowBack, Save } from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { staffApi } from '../api/client';
import type { Staff } from '../types/api';
import { AxiosError } from 'axios';

export function StaffEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    status: 'active' as 'active' | 'inactive',
    role: 'staff' as 'admin' | 'manager' | 'staff',
    expected_hours_per_week: 40.0,
  });

  useEffect(() => {
    if (!isNew && id) {
      const loadStaff = async () => {
        setLoading(true);
        setError('');
        try {
          const data = await staffApi.get(parseInt(id));
          setFormData({
            email: data.email,
            first_name: data.first_name,
            last_name: data.last_name,
            status: data.status,
            role: data.role,
            expected_hours_per_week: parseFloat(data.expected_hours_per_week),
          });
        } catch (err) {
          if (err instanceof AxiosError) {
            setError(err.response?.data?.detail || 'Failed to load staff');
          } else {
            setError('Failed to load staff');
          }
        } finally {
          setLoading(false);
        }
      };
      loadStaff();
    }
  }, [id, isNew]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      if (isNew) {
        const created = await staffApi.create(formData);
        navigate(`/staff/${created.id}`);
      } else {
        const updated = await staffApi.update(parseInt(id!), formData);
        navigate(`/staff/${updated.id}`);
      }
    } catch (err) {
      if (err instanceof AxiosError) {
        const errorData = err.response?.data;
        if (typeof errorData === 'object') {
          const messages = Object.entries(errorData)
            .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
            .join('; ');
          setError(messages);
        } else {
          setError(errorData?.detail || 'Failed to save staff');
        }
      } else {
        setError('Failed to save staff');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/staff');
    } else {
      navigate(`/staff/${id}`);
    }
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
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={handleCancel}>
          Back
        </Button>
        <Typography variant="h4">
          {isNew ? 'Create Staff Member' : 'Edit Staff Member'}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <form onSubmit={handleSubmit}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
            />

            <TextField
              label="First Name"
              required
              value={formData.first_name}
              onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              fullWidth
            />

            <TextField
              label="Last Name"
              required
              value={formData.last_name}
              onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              fullWidth
            />

            <TextField
              select
              label="Role"
              required
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value as any })}
              fullWidth
            >
              <MenuItem value="staff">Staff</MenuItem>
              <MenuItem value="manager">Manager</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </TextField>

            <TextField
              select
              label="Status"
              required
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
              fullWidth
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
            </TextField>

            <TextField
              label="Expected Hours Per Week"
              type="number"
              required
              value={formData.expected_hours_per_week}
              onChange={(e) => setFormData({ ...formData, expected_hours_per_week: parseFloat(e.target.value) })}
              inputProps={{ min: 0, step: 0.5 }}
              fullWidth
            />

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
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
            </Box>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}

