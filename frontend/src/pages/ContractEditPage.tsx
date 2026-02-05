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
import { useParams, useNavigate } from 'react-router-dom';
import { contractsApi } from '../api/client';
import type { Contract } from '../types/api';
import { AxiosError } from 'axios';

export function ContractEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [contract, setContract] = useState<Partial<Contract>>({
    name: '',
    client_name: '',
    budget_hours: '0',
    status: 'draft',
    start_date: '',
    end_date: '',
  });
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      if (!isNew && id) {
        try {
          const contractData = await contractsApi.get(parseInt(id));
          setContract(contractData);
        } catch (err) {
          if (err instanceof AxiosError) {
            setError(err.response?.data?.detail || 'Failed to load contract');
          } else {
            setError('Failed to load contract');
          }
        } finally {
          setLoading(false);
        }
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
        name: contract.name,
        client_name: contract.client_name,
        budget_hours: contract.budget_hours,
        status: contract.status,
        start_date: contract.start_date,
        end_date: contract.end_date,
      };

      if (isNew) {
        const created = await contractsApi.create(payload);
        navigate(`/contracts/${created.id}`);
      } else if (id) {
        await contractsApi.update(parseInt(id), payload);
        navigate(`/contracts/${id}`);
      }
    } catch (err) {
      if (err instanceof AxiosError) {
        setError(err.response?.data?.detail || 'Failed to save contract');
      } else {
        setError('Failed to save contract');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
      navigate('/contracts');
    } else {
      navigate(`/contracts/${id}`);
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
      <Button startIcon={<ArrowBack />} onClick={handleCancel} sx={{ mb: 2 }}>
        Back
      </Button>

      <Typography variant="h4" gutterBottom>
        {isNew ? 'Create Contract' : 'Edit Contract'}
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
              label="Contract Name"
              value={contract.name || ''}
              onChange={(e) => setContract({ ...contract, name: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Client Name"
              value={contract.client_name || ''}
              onChange={(e) => setContract({ ...contract, client_name: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Budget Hours"
              type="number"
              value={contract.budget_hours || '0'}
              onChange={(e) => setContract({ ...contract, budget_hours: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />

            <TextField
              label="Status"
              select
              value={contract.status || 'draft'}
              onChange={(e) => setContract({ ...contract, status: e.target.value as Contract['status'] })}
              required
              fullWidth
            >
              <MenuItem value="draft">Draft</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="closed">Closed</MenuItem>
            </TextField>

            <TextField
              label="Start Date"
              type="date"
              value={contract.start_date || ''}
              onChange={(e) => setContract({ ...contract, start_date: e.target.value })}
              required
              fullWidth
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              label="End Date"
              type="date"
              value={contract.end_date || ''}
              onChange={(e) => setContract({ ...contract, end_date: e.target.value })}
              required
              fullWidth
              InputLabelProps={{ shrink: true }}
            />

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

