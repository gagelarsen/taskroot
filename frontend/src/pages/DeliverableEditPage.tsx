import { useState, useEffect } from 'react';
import {
  Autocomplete,
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
import { chargeCodesApi, deliverablesApi, contractsApi } from '../api/client';
import type { Deliverable, Contract, ChargeCode } from '../types/api';
import { getApiErrorMessage } from '../utils/apiErrors';
import { coerceToIsoDateOnly } from '../utils/dateHelpers';

export function DeliverableEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isNew = id === 'new';

  // Get contract from query params if creating new deliverable
  const contractParam = searchParams.get('contract');

  const [deliverable, setDeliverable] = useState<Partial<Deliverable>>({
    name: '',
    budget_hours: '0',
    status: 'not_started',
    contract: contractParam ? parseInt(contractParam) : 0,
    charge_code: '',
    target_completion_date: null,
  });
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [chargeCodeOptions, setChargeCodeOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const [contractsData, chargeCodesData] = await Promise.all([
          contractsApi.list(),
          chargeCodesApi.list({ is_active: true, order_by: 'code', order_dir: 'asc' }),
        ]);
        setContracts(contractsData);
        setChargeCodeOptions((chargeCodesData as ChargeCode[]).map((item) => item.code));

        if (!isNew && id) {
          const deliverableData = await deliverablesApi.get(parseInt(id));
          // Ensure dates are in YYYY-MM-DD format for date inputs
          let targetDate = deliverableData.target_completion_date || '';

          // If the date is in a different format, convert it to YYYY-MM-DD
          if (targetDate && !targetDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
            const parsed = new Date(targetDate);
            if (!isNaN(parsed.getTime())) {
              targetDate = coerceToIsoDateOnly(parsed);
            }
          }

          setDeliverable({
            ...deliverableData,
            target_completion_date: targetDate,
          });
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
        name: deliverable.name,
        budget_hours: deliverable.budget_hours,
        status: deliverable.status,
        contract: deliverable.contract,
        charge_code: deliverable.charge_code || '',
        target_completion_date: deliverable.target_completion_date || null,
      };

      if (isNew) {
        const created = await deliverablesApi.create(payload);
        navigate(`/deliverables/${created.id}`);
      } else if (id) {
        await deliverablesApi.update(parseInt(id), payload);
        navigate(`/deliverables/${id}`);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to save deliverable'));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (deliverable.contract) {
      navigate(`/contracts/${deliverable.contract}`);
    } else {
      navigate(-1);
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
        {isNew ? 'Create Deliverable' : 'Edit Deliverable'}
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
              label="Name"
              value={deliverable.name || ''}
              onChange={(e) => setDeliverable({ ...deliverable, name: e.target.value })}
              required
              fullWidth
            />

            <TextField
              label="Contract"
              select
              value={deliverable.contract || ''}
              onChange={(e) => setDeliverable({ ...deliverable, contract: parseInt(e.target.value) })}
              required
              fullWidth
            >
              {contracts.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name} - {c.client_name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label="Budget Hours"
              type="number"
              value={deliverable.budget_hours || '0'}
              onChange={(e) => setDeliverable({ ...deliverable, budget_hours: e.target.value })}
              required
              fullWidth
              inputProps={{ min: 0, step: 0.5 }}
            />

            <TextField
              label="Status"
              select
              value={deliverable.status || 'planned'}
              onChange={(e) => setDeliverable({ ...deliverable, status: e.target.value as Deliverable['status'] })}
              required
              fullWidth
            >
              <MenuItem value="planned">Planned</MenuItem>
              <MenuItem value="in_progress">In Progress</MenuItem>
              <MenuItem value="complete">Complete</MenuItem>
              <MenuItem value="blocked">Blocked</MenuItem>
            </TextField>

            <Autocomplete
              freeSolo
              options={chargeCodeOptions}
              value={deliverable.charge_code || ''}
              onInputChange={(_, value) => setDeliverable({ ...deliverable, charge_code: value })}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Charge Code"
                  fullWidth
                  helperText="Existing charge codes are suggested; you can still type a new one."
                />
              )}
            />

            <TextField
              label="Target Completion Date"
              type="date"
              value={(() => {
                const date = deliverable.target_completion_date;
                if (!date) return '';
                // Ensure format is YYYY-MM-DD
                if (date.match(/^\d{4}-\d{2}-\d{2}$/)) return date;
                // Try to parse and convert
                return coerceToIsoDateOnly(date);
              })()}
              onChange={(e) => setDeliverable({ ...deliverable, target_completion_date: e.target.value || null })}
              fullWidth
              slotProps={{
                inputLabel: { shrink: true },
              }}
              helperText="Optional target date for completion"
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

