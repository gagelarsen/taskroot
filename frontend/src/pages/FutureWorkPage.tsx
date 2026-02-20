import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Edit } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { futureWorkApi, staffApi } from '../api/client';
import type { FutureWork, Staff } from '../types/api';
import { sortStaffByName } from '../utils/staffSort';
import { getApiErrorMessage } from '../utils/apiErrors';

export function FutureWorkPage() {
  const navigate = useNavigate();

  const [items, setItems] = useState<FutureWork[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showConverted, setShowConverted] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createData, setCreateData] = useState({
    name: '',
    owner: '',
    tags: '',
    target_date: '',
    notes: '',
  });

  const [convertingInitiativeId, setConvertingInitiativeId] = useState<number | null>(null);
  const [editDialogItem, setEditDialogItem] = useState<FutureWork | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editData, setEditData] = useState({
    name: '',
    owner: '',
    tags: '',
    target_date: '',
    notes: '',
  });
  const [contractDialogItem, setContractDialogItem] = useState<FutureWork | null>(null);
  const [convertingContract, setConvertingContract] = useState(false);
  const [contractData, setContractData] = useState({
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    budget_hours: '0',
    client_name: '',
    contract_type: 'fixed_cost',
    status: 'draft',
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [futureWork, staffMembers] = await Promise.all([
        futureWorkApi.list({ order_by: 'id', order_dir: 'desc' }),
        staffApi.list({ order_by: 'id', order_dir: 'asc' }),
      ]);
      setItems(futureWork);
      setStaff(sortStaffByName(staffMembers));
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to load future work'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const visibleItems = showConverted ? items : items.filter((item) => !item.is_converted);

  const createFutureWork = async () => {
    if (!createData.name.trim()) {
      return;
    }

    setCreating(true);
    setError('');

    try {
      const tags = createData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      await futureWorkApi.create({
        name: createData.name,
        owner: createData.owner ? Number(createData.owner) : null,
        tags,
        target_date: createData.target_date || null,
        notes: createData.notes,
      });

      setCreateOpen(false);
      setCreateData({ name: '', owner: '', tags: '', target_date: '', notes: '' });
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to create future work'));
    } finally {
      setCreating(false);
    }
  };

  const convertToInitiative = async (item: FutureWork) => {
    const confirmed = window.confirm(`Convert "${item.name}" to an initiative?`);
    if (!confirmed) {
      return;
    }

    setConvertingInitiativeId(item.id);
    setError('');
    try {
      const response = await futureWorkApi.convertToInitiative(item.id);
      await loadData();
      if (response?.initiative?.id) {
        navigate(`/initiatives`);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to convert to initiative'));
    } finally {
      setConvertingInitiativeId(null);
    }
  };

  const openEditDialog = (item: FutureWork) => {
    setEditDialogItem(item);
    setEditData({
      name: item.name,
      owner: item.owner ? String(item.owner) : '',
      tags: (item.tags || []).join(', '),
      target_date: item.target_date || '',
      notes: item.notes || '',
    });
  };

  const saveEditedFutureWork = async () => {
    if (!editDialogItem || !editData.name.trim()) {
      return;
    }

    setSavingEdit(true);
    setError('');

    try {
      const tags = editData.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      await futureWorkApi.update(editDialogItem.id, {
        name: editData.name,
        owner: editData.owner ? Number(editData.owner) : null,
        tags,
        target_date: editData.target_date || null,
        notes: editData.notes,
      });

      setEditDialogItem(null);
      await loadData();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to update future work'));
    } finally {
      setSavingEdit(false);
    }
  };

  const openConvertToContractDialog = (item: FutureWork) => {
    setContractDialogItem(item);
    setContractData({
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0],
      budget_hours: '0',
      client_name: '',
      contract_type: 'fixed_cost',
      status: 'draft',
    });
  };

  const convertToContract = async () => {
    if (!contractDialogItem) {
      return;
    }

    setConvertingContract(true);
    setError('');
    try {
      const response = await futureWorkApi.convertToContract(contractDialogItem.id, contractData);
      setContractDialogItem(null);
      await loadData();
      if (response?.contract?.id) {
        navigate(`/contracts/${response.contract.id}`);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to convert to contract'));
    } finally {
      setConvertingContract(false);
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Future Work</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setCreateOpen(true)}>
          Add Future Work
        </Button>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Capture lightweight ideas now, then convert them to an Initiative or Contract when ready.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <FormControlLabel
        control={<Switch size="small" checked={showConverted} onChange={(event) => setShowConverted(event.target.checked)} />}
        label="Show converted"
        sx={{ mb: 1 }}
      />

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Owner</TableCell>
              <TableCell>Target</TableCell>
              <TableCell>Notes</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleItems.map((item) => (
              <TableRow key={item.id}>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{item.name}</Typography>
                  {!!item.tags?.length && (
                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: 'wrap' }}>
                      {item.tags.map((tag) => (
                        <Chip key={`${item.id}-${tag}`} label={tag} size="small" variant="outlined" />
                      ))}
                    </Stack>
                  )}
                </TableCell>
                <TableCell>{item.owner_name || 'Unassigned'}</TableCell>
                <TableCell>{item.target_date || '—'}</TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                    {item.notes || '—'}
                  </Typography>
                </TableCell>
                <TableCell>
                  {item.is_converted ? (
                    <Chip
                      size="small"
                      color="success"
                      label={`Converted to ${item.converted_to_type === 'initiative' ? 'Initiative' : 'Contract'}`}
                    />
                  ) : (
                    <Chip size="small" label="Pending" />
                  )}
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<Edit />}
                      disabled={item.is_converted}
                      onClick={() => openEditDialog(item)}
                    >
                      Edit
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={item.is_converted || convertingInitiativeId === item.id}
                      onClick={() => void convertToInitiative(item)}
                    >
                      {convertingInitiativeId === item.id ? 'Converting...' : 'To Initiative'}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={item.is_converted}
                      onClick={() => openConvertToContractDialog(item)}
                    >
                      To Contract
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
            {visibleItems.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  No future work items
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={createOpen} onClose={() => !creating && setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Future Work</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={createData.name}
              onChange={(event) => setCreateData((current) => ({ ...current, name: event.target.value }))}
              required
              fullWidth
            />
            <TextField
              select
              label="Owner"
              value={createData.owner}
              onChange={(event) => setCreateData((current) => ({ ...current, owner: event.target.value }))}
              fullWidth
            >
              <MenuItem value="">Unassigned</MenuItem>
              {staff.map((member) => (
                <MenuItem key={member.id} value={String(member.id)}>
                  {member.first_name} {member.last_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Tags"
              value={createData.tags}
              onChange={(event) => setCreateData((current) => ({ ...current, tags: event.target.value }))}
              helperText="Comma-separated"
              fullWidth
            />
            <TextField
              label="Target Date"
              type="date"
              value={createData.target_date}
              onChange={(event) => setCreateData((current) => ({ ...current, target_date: event.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={createData.notes}
              onChange={(event) => setCreateData((current) => ({ ...current, notes: event.target.value }))}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)} disabled={creating}>Cancel</Button>
          <Button variant="contained" onClick={() => void createFutureWork()} disabled={creating || !createData.name.trim()}>
            {creating ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!editDialogItem} onClose={() => !savingEdit && setEditDialogItem(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Future Work</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={editData.name}
              onChange={(event) => setEditData((current) => ({ ...current, name: event.target.value }))}
              required
              fullWidth
            />
            <TextField
              select
              label="Owner"
              value={editData.owner}
              onChange={(event) => setEditData((current) => ({ ...current, owner: event.target.value }))}
              fullWidth
            >
              <MenuItem value="">Unassigned</MenuItem>
              {staff.map((member) => (
                <MenuItem key={member.id} value={String(member.id)}>
                  {member.first_name} {member.last_name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Tags"
              value={editData.tags}
              onChange={(event) => setEditData((current) => ({ ...current, tags: event.target.value }))}
              helperText="Comma-separated"
              fullWidth
            />
            <TextField
              label="Target Date"
              type="date"
              value={editData.target_date}
              onChange={(event) => setEditData((current) => ({ ...current, target_date: event.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
              fullWidth
            />
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={editData.notes}
              onChange={(event) => setEditData((current) => ({ ...current, notes: event.target.value }))}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogItem(null)} disabled={savingEdit}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveEditedFutureWork()} disabled={savingEdit || !editData.name.trim()}>
            {savingEdit ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!contractDialogItem} onClose={() => !convertingContract && setContractDialogItem(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Convert to Contract</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {contractDialogItem?.name}
            </Typography>
            <TextField
              label="Client Name"
              value={contractData.client_name}
              onChange={(event) => setContractData((current) => ({ ...current, client_name: event.target.value }))}
              fullWidth
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <TextField
                label="Start Date"
                type="date"
                value={contractData.start_date}
                onChange={(event) => setContractData((current) => ({ ...current, start_date: event.target.value }))}
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
              />
              <TextField
                label="End Date"
                type="date"
                value={contractData.end_date}
                onChange={(event) => setContractData((current) => ({ ...current, end_date: event.target.value }))}
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
              />
            </Stack>
            <TextField
              label="Budget Hours"
              type="number"
              value={contractData.budget_hours}
              onChange={(event) => setContractData((current) => ({ ...current, budget_hours: event.target.value }))}
              inputProps={{ min: 0, step: 0.5 }}
              fullWidth
            />
            <TextField
              select
              label="Contract Type"
              value={contractData.contract_type}
              onChange={(event) => setContractData((current) => ({ ...current, contract_type: event.target.value }))}
              fullWidth
            >
              <MenuItem value="fixed_cost">Fixed Cost</MenuItem>
              <MenuItem value="time_and_materials">Time and Materials</MenuItem>
            </TextField>
            <TextField
              select
              label="Status"
              value={contractData.status}
              onChange={(event) => setContractData((current) => ({ ...current, status: event.target.value }))}
              fullWidth
            >
              <MenuItem value="draft">Draft</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="closed">Closed</MenuItem>
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setContractDialogItem(null)} disabled={convertingContract}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => void convertToContract()}
            disabled={convertingContract || !contractData.start_date || !contractData.end_date || Number(contractData.budget_hours) < 0}
          >
            {convertingContract ? 'Converting...' : 'Convert'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
